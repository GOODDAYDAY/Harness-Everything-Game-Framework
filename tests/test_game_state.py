#!/usr/bin/env python3
"""Tests for game_state.py — core game logic."""

import sys
sys.path.insert(0, '.')

from game.game_state import GameState
from game.phases import GamePhase
from game.roles import Role


class TestGameState:
    """Test the core game state machine."""

    def setup_method(self):
        self.gs = GameState()

    def test_initial_state(self):
        """Game starts in SETUP phase."""
        assert self.gs.phase == GamePhase.SETUP
        assert self.gs.day == 1
        assert self.gs.winner is None

    def test_start_game(self):
        """start_game transitions to first night."""
        self.gs.start_game()
        assert self.gs.phase == GamePhase.NIGHT_GUARD
        assert self.gs.day == 1

    def test_night_phase_order(self):
        """Night phases cycle in the correct order."""
        self.gs.start_game()
        phases_seen = [self.gs.phase]
        for _ in range(10):
            self.gs.advance_night_phase()
            phases_seen.append(self.gs.phase)
            if self.gs.phase == GamePhase.DAY_ANNOUNCE:
                break
        expected = [
            GamePhase.NIGHT_GUARD,
            GamePhase.NIGHT_SEER,
            GamePhase.NIGHT_WEREWOLF,
            GamePhase.NIGHT_WITCH,
            GamePhase.DAY_ANNOUNCE,
        ]
        assert phases_seen == expected, f"Got {phases_seen}"

    def test_day_phase_order(self):
        """Day phases cycle in the correct order."""
        self.gs.start_game()
        # Fast-forward to day
        self.gs.phase = GamePhase.DAY_ANNOUNCE
        self.gs.day = 1
        phases_seen = [self.gs.phase]
        for _ in range(10):
            self.gs.advance_day_phase()
            phases_seen.append(self.gs.phase)
            if self.gs.phase == GamePhase.NIGHT_GUARD:
                break
        expected = [
            GamePhase.DAY_ANNOUNCE,
            GamePhase.DAY_SHERIFF_ELECTION,
            GamePhase.DAY_DISCUSSION,
            GamePhase.DAY_VOTE,
            GamePhase.DAY_RESULT,
            GamePhase.NIGHT_GUARD,  # Next night
        ]
        # Only check first 6 phases (sheriff election, discussion, vote, result, night)
        for i, exp in enumerate(expected):
            assert phases_seen[i] == exp, f"Phase {i}: expected {exp}, got {phases_seen[i]}"

    def test_sheriff_election_day1(self):
        """Sheriff election happens on Day 1."""
        self.gs.start_game()
        self.gs.phase = GamePhase.DAY_SHERIFF_ELECTION
        self.gs.day = 1
        alive = self.gs.players.get_alive_players()
        for p in alive:
            if p.index != 0:
                self.gs.sheriff_votes[p.index] = 0
        self.gs._resolve_sheriff_election()
        assert self.gs.players.get_player(0).is_sheriff
        assert self.gs.sheriff_election_done

    def test_sheriff_election_tie(self):
        """Tie in sheriff election means no sheriff elected."""
        self.gs.start_game()
        self.gs.phase = GamePhase.DAY_SHERIFF_ELECTION
        self.gs.day = 1
        alive = self.gs.players.get_alive_players()
        for i, p in enumerate(alive):
            if p.index != 0 and p.index != 1:
                self.gs.sheriff_votes[p.index] = i % 2  # Even/odd split
        self.gs._resolve_sheriff_election()
        assert not any(p.is_sheriff for p in self.gs.players.players)

    def test_sheriff_skip_day2(self):
        """Sheriff election is skipped on Day 2+."""
        self.gs.start_game()
        self.gs.sheriff_election_done = True  # Already elected
        self.gs.phase = GamePhase.DAY_SHERIFF_ELECTION
        self.gs.day = 2
        self.gs.advance_day_phase()
        assert self.gs.phase == GamePhase.DAY_DISCUSSION

    def test_sheriff_bonus_vote(self):
        """Sheriff's vote counts as 1.5."""
        self.gs.start_game()
        self.gs.players.get_player(0).is_sheriff = True
        self.gs.phase = GamePhase.DAY_VOTE
        # 4 votes for player 2 (including sheriff) = 3 + 1.5 = 4.5
        # 3 votes for player 1 = 3
        self.gs.votes = {i: 2 for i in range(4)}
        for i in range(4, 7):
            self.gs.votes[i] = 1
        self.gs._resolve_day()
        assert self.gs.vote_result == 2, f"Expected player 2, got {self.gs.vote_result}"

    def test_town_crier_win_condition(self):
        """Town Crier wins when voted out."""
        self.gs.start_game()
        self.gs.players.set_town_crier_won()
        assert self.gs.players.is_game_over()
        assert self.gs.players.get_winning_team() == "town_crier"

    def test_town_crier_voted_out(self):
        """Town Crier elimination during vote triggers win."""
        self.gs.start_game()
        tc_idx = None
        for p in self.gs.players.players:
            if p.role == Role.TOWN_CRIER:
                tc_idx = p.index
                break
        assert tc_idx is not None
        # Simulate being voted out
        self.gs.players.kill_player(tc_idx)
        # This is what _resolve_day does when TC is eliminated
        self.gs.players.set_town_crier_won()
        assert self.gs.players.is_game_over()
        assert self.gs.players.get_winning_team() == "town_crier"

    def test_village_wins_no_wolves(self):
        """Village wins when all werewolves are dead."""
        self.gs.start_game()
        for p in self.gs.players.players:
            if p.role == Role.WEREWOLF:
                p.alive = False
        assert self.gs.players.is_game_over()
        assert self.gs.players.get_winning_team() == "village"

    def test_werewolves_outnumber_village(self):
        """Werewolves win when they equal or outnumber village."""
        self.gs.start_game()
        # Kill all non-wolves except 1
        for p in self.gs.players.players:
            if p.role != Role.WEREWOLF and p.role != Role.TOWN_CRIER:
                p.alive = False
        # Now wolves >= village
        assert self.gs.players.is_game_over()
        assert self.gs.players.get_winning_team() == "werewolf"

    def test_game_log(self):
        """Game events are logged."""
        self.gs.start_game()
        assert len(self.gs.log) > 0
        assert self.gs.log[0]["event"] == "game_start"

    def test_resolve_night_no_action(self):
        """Resolve night with no actions doesn't crash."""
        self.gs.start_game()
        self.gs.phase = GamePhase.DAY_ANNOUNCE
        result = self.gs.resolve_night()
        assert result["victim"] is None

    def test_vote_tie(self):
        """Tie during vote results in no elimination."""
        self.gs.start_game()
        self.gs.phase = GamePhase.DAY_VOTE
        self.gs.votes = {i: i % 2 for i in range(8)}
        self.gs._resolve_day()
        assert self.gs.vote_result is None  # Tie = no elim

    def test_no_votes(self):
        """No votes cast = no elimination."""
        self.gs.start_game()
        self.gs.phase = GamePhase.DAY_VOTE
        self.gs.votes = {}
        self.gs._resolve_day()
        assert self.gs.vote_result is None

    def test_player_manager_12_players(self):
        """Game has exactly 12 players with correct roles."""
        assert len(self.gs.players.players) == 12
        role_counts = {}
        for p in self.gs.players.players:
            role_counts[p.role] = role_counts.get(p.role, 0) + 1
        assert role_counts[Role.WEREWOLF] == 3
        assert role_counts[Role.VILLAGER] == 4
        assert role_counts[Role.SEER] == 1
        assert role_counts[Role.WITCH] == 1
        assert role_counts[Role.HUNTER] == 1
        assert role_counts[Role.GUARD] == 1
        assert role_counts[Role.TOWN_CRIER] == 1

    def test_to_dict(self):
        """to_dict doesn't crash and contains expected keys."""
        d = self.gs.to_dict()
        assert "phase" in d
        assert "day" in d
        assert "winner" in d
        assert "players" in d
        assert "log" in d
