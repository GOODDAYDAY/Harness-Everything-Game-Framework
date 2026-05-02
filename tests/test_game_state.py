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
            GamePhase.NIGHT_WEREWOLF,
            GamePhase.NIGHT_WITCH,
            GamePhase.NIGHT_SEER,
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
            GamePhase.DAY_PK,      # Runoff vote between tied candidates
            GamePhase.DAY_TRIAL,   # Accused player defends
            GamePhase.DAY_VOTE_RESULT,
            GamePhase.NIGHT_GUARD,  # Next night
        ]
        # Only check first 8 phases
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
            if p.role != Role.WEREWOLF:
                p.alive = False
        # Now wolves >= village (4 wolves vs 0 villagers)
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

    def test_vote_tie_triggers_pk(self):
        """Tie during vote triggers PK runoff mode."""
        self.gs.start_game()
        self.gs.phase = GamePhase.DAY_VOTE
        self.gs.votes = {i: i % 2 for i in range(8)}
        self.gs._resolve_day()
        assert self.gs.pk_mode is True  # Tie triggers PK
        assert len(self.gs.pk_candidates) == 2
        assert self.gs.vote_result is None  # Not resolved yet

    def test_vote_pk_runoff_resolved(self):
        """PK runoff revotes and eliminates the top candidate."""
        self.gs.start_game()
        self.gs.phase = GamePhase.DAY_VOTE
        # Set up a tie
        self.gs.votes = {i: i % 2 for i in range(8)}
        self.gs._resolve_day()
        assert self.gs.pk_mode is True
        # Now simulate runoff: all revote for candidate 0 (index 0)
        self.gs.votes = {i: 0 for i in range(8)}
        self.gs._resolve_day()  # This calls _resolve_runoff internally
        assert self.gs.pk_mode is False
        assert self.gs.vote_result == 0

    def test_vote_pk_runoff_still_tied(self):
        """If PK runoff is also tied, no elimination."""
        self.gs.start_game()
        self.gs.phase = GamePhase.DAY_VOTE
        self.gs.votes = {i: i % 2 for i in range(8)}
        self.gs._resolve_day()
        assert self.gs.pk_mode is True
        # Still tied in runoff
        self.gs.votes = {i: i % 2 for i in range(8)}
        self.gs._resolve_day()
        assert self.gs.pk_mode is False
        assert self.gs.vote_result is None  # Still tie = no elim

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
        assert role_counts[Role.WEREWOLF] == 4
        assert role_counts[Role.VILLAGER] == 4
        assert role_counts[Role.SEER] == 1
        assert role_counts[Role.WITCH] == 1
        assert role_counts[Role.HUNTER] == 1
        assert role_counts[Role.GUARD] == 1

    def test_to_dict(self):
        """to_dict doesn't crash and contains expected keys."""
        d = self.gs.to_dict()
        assert "phase" in d
        assert "day" in d
        assert "winner" in d
        assert "players" in d
        assert "log" in d

    def test_no_consecutive_guard_game_state(self):
        """Guard cannot protect the same player two nights in a row.

        The _reset_night_actions method saves last_guard_target,
        and the guard must choose a different target the next night.
        """
        self.gs.start_game()
        guard_idx = None
        for p in self.gs.players.players:
            if p.role == Role.GUARD:
                guard_idx = p.index
                break
        assert guard_idx is not None

        # Night 1: simulate guard protecting player 0
        self.gs.guard_target = 0
        self.gs.last_night_victim = None
        self.gs.last_night_saved = False

        # End of night — save last guard target
        self.gs._reset_night_actions()
        assert self.gs.last_guard_target == 0, f"Expected 0, got {self.gs.last_guard_target}"
        assert self.gs.guard_target is None, "Guard target should be reset"

        # Night 2: eligible guard targets should NOT include player 0
        from game.npc_ai import get_eligible_targets
        eligible = get_eligible_targets(self.gs, guard_idx, GamePhase.NIGHT_GUARD)
        assert 0 not in eligible, f"Player 0 should not be eligible (last_guard_target), got: {eligible}"

    def test_no_consecutive_guard_self_allowed(self):
        """Guard should be able to self-protect after protecting someone else.

        Self-target is allowed by the eligibility rules;
        only the previous night's target is excluded.
        """
        self.gs.start_game()
        guard_idx = None
        for p in self.gs.players.players:
            if p.role == Role.GUARD:
                guard_idx = p.index
                break
        assert guard_idx is not None

        # Night 1: guard protects someone else
        other_idx = 1 if guard_idx != 1 else 2
        self.gs.guard_target = other_idx
        self.gs._reset_night_actions()
        assert self.gs.last_guard_target == other_idx

        # Night 2: guard can still protect themselves
        from game.npc_ai import get_eligible_targets
        eligible = get_eligible_targets(self.gs, guard_idx, GamePhase.NIGHT_GUARD)
        assert guard_idx in eligible, (
            f"Guard should be eligible to self-protect, eligible: {eligible}"
        )

    def test_witch_heal_cancels_hunter_vengeance(self):
        """When witch heals the werewolf's hunter victim, no vengeance."""
        self.gs.start_game()

        # Find hunter and a werewolf
        hunter_idx = None
        wolf_idx = None
        for p in self.gs.players.players:
            if p.role == Role.HUNTER:
                hunter_idx = p.index
            if p.role == Role.WEREWOLF:
                wolf_idx = p.index
        assert hunter_idx is not None
        assert wolf_idx is not None

        # Simulate night: werewolf targets hunter, witch heals same target
        self.gs.phase = GamePhase.NIGHT_WITCH
        self.gs.werewolf_target = hunter_idx
        self.gs.witch_heal_target = hunter_idx
        self.gs.witch_used_heal = False

        # Advance to day and resolve
        self.gs.phase = GamePhase.DAY_ANNOUNCE
        result = self.gs.resolve_night()

        # Hunter should be alive (healed) and no vengeance
        hunter = self.gs.players.get_player(hunter_idx)
        assert hunter.alive, "Hunter should be alive after witch heal"
        assert result["saved"] is True, "Night should be marked as saved"
        assert result["hunter_vengeance"] is False, "No vengeance when hunter is saved"

    def test_witch_poison_hunter_triggers_vengeance(self):
        """When witch poisons a hunter (separate from werewolf target), hunter takes vengeance."""
        self.gs.start_game()

        # Find hunter and some other player (not the wolf's target)
        hunter_idx = None
        other_idx = None
        for p in self.gs.players.players:
            if p.role == Role.HUNTER:
                hunter_idx = p.index
            if p.role == Role.WEREWOLF:
                pass  # skip wolves; find a non-wolf target below
        # Find a non-hunter, non-wolf target for the werewolf
        for p in self.gs.players.players:
            if p.index != hunter_idx and p.role != Role.WEREWOLF:
                other_idx = p.index
                break
        assert hunter_idx is not None
        assert other_idx is not None

        # Simulate night: werewolf kills someone else, witch poisons the hunter
        self.gs.phase = GamePhase.NIGHT_WITCH
        self.gs.werewolf_target = other_idx
        self.gs.witch_poison_target = hunter_idx
        self.gs.witch_used_poison = False

        # Resolve night
        self.gs.phase = GamePhase.DAY_ANNOUNCE
        result = self.gs.resolve_night()

        # Hunter should be dead and vengeance triggered
        hunter = self.gs.players.get_player(hunter_idx)
        assert not hunter.alive, "Hunter should be dead from poison"
        assert result["hunter_vengeance"] is True, "Hunter should take vengeance"

    def test_standard_setup_has_exactly_one_hunter(self):
        """Only one hunter in standard 12-player setup."""
        self.gs.start_game()
        hunter_count = sum(1 for p in self.gs.players.players if p.role == Role.HUNTER)
        assert hunter_count == 1, f"Standard setup must have exactly 1 hunter, got {hunter_count}"
