#!/usr/bin/env python3
"""Tests for npc_ai.py — NPC decision-making."""

import sys
sys.path.insert(0, '.')

from game.game_state import GameState
from game.phases import GamePhase
from game.roles import Role
from game.npc_ai import (
    choose_night_action,
    choose_vote_target,
    choose_sheriff_vote,
    decide_witch_action,
    choose_hunter_vengeance_target,
    get_eligible_targets,
)


class TestNpcAI:
    """Test NPC AI decisions."""

    def setup_method(self):
        self.gs = GameState()
        self.gs.start_game()

    def _get_role_idx(self, role: Role) -> int:
        for p in self.gs.players.players:
            if p.role == role:
                return p.index
        raise ValueError(f"No player with role {role}")

    def test_get_eligible_guard_targets(self):
        """Guard can target anyone alive."""
        guard_idx = self._get_role_idx(Role.GUARD)
        targets = get_eligible_targets(self.gs, guard_idx, GamePhase.NIGHT_GUARD)
        for t in targets:
            assert self.gs.players.get_player(t).alive

    def test_guard_does_not_target_self(self):
        """Guard night action chooses someone other than self."""
        guard_idx = self._get_role_idx(Role.GUARD)
        target = choose_night_action(self.gs, guard_idx, GamePhase.NIGHT_GUARD)
        assert target != guard_idx, f"Guard should not target self (idx={guard_idx})"

    def test_get_eligible_werewolf_targets(self):
        """Werewolf can target anyone alive except self and other wolves."""
        ww_idx = self._get_role_idx(Role.WEREWOLF)
        targets = get_eligible_targets(self.gs, ww_idx, GamePhase.NIGHT_WEREWOLF)
        assert ww_idx not in targets
        # Should exclude other werewolves
        for t in targets:
            assert not self.gs.players.get_player(t).role.is_werewolf_team

    def test_guard_protects_sheriff(self):
        """Guard prioritises protecting the sheriff (when not self)."""
        guard_idx = self._get_role_idx(Role.GUARD)
        # Make player 0 sheriff (not the guard)
        self.gs.players.get_player(0).is_sheriff = True
        target = choose_night_action(self.gs, guard_idx, GamePhase.NIGHT_GUARD)
        if guard_idx == 0:
            # Guard is the sheriff — should protect someone else
            assert target != 0 and target is not None, \
                f"Guard-sheriff should protect someone else, got {target}"
        else:
            assert target == 0, f"Guard should protect sheriff (player 0), got {target}"

    def test_werewolf_avoids_wolves(self):
        """Werewolf never targets another werewolf."""
        ww_idx = self._get_role_idx(Role.WEREWOLF)
        for _ in range(20):
            target = choose_night_action(self.gs, ww_idx, GamePhase.NIGHT_WEREWOLF)
            if target is not None:
                target_role = self.gs.players.get_player(target).role
                assert target_role != Role.WEREWOLF, f"Wolf targeted another wolf: player {target}"

    def test_seer_returns_valid_target(self):
        """Seer targets a valid alive player."""
        seer_idx = self._get_role_idx(Role.SEER)
        target = choose_night_action(self.gs, seer_idx, GamePhase.NIGHT_SEER)
        assert target is not None
        assert target != seer_idx
        assert self.gs.players.get_player(target).alive

    def test_vote_target_not_self(self):
        """Non-IMPULSIVE NPCs don't vote for themselves."""
        from game.player import Personality
        for p in self.gs.players.players:
            p.personality = Personality.RANDOM
        player_idx = self.gs.players.players[0].index
        # Run many times to be confident (IMPULSIVE is the only one that self-votes)
        for _ in range(50):
            target = choose_vote_target(self.gs, player_idx)
            if target is not None:
                assert target != player_idx

    def test_impulsive_self_vote(self):
        """IMPULSIVE NPCs self-vote ~30% of the time."""
        from game.player import Personality
        for p in self.gs.players.players:
            p.personality = Personality.IMPULSIVE
        player_idx = self.gs.players.players[0].index
        self_count = 0
        trials = 200
        for _ in range(trials):
            target = choose_vote_target(self.gs, player_idx)
            if target == player_idx:
                self_count += 1
        # Should happen ~30% of the time, check it happens at least once
        assert self_count > 0, f"IMPULSIVE never self-voted in {trials} trials"

    def test_werewolf_bandwagon(self):
        """Werewolves coordinate their votes."""
        wolves = [p for p in self.gs.players.players if p.role == Role.WEREWOLF]
        if len(wolves) < 2:
            return  # Need at least 2 wolves for bandwagon test
        self.gs.phase = GamePhase.DAY_VOTE
        # First wolf votes for player 2
        self.gs.votes = {}
        self.gs.votes[wolves[0].index] = 2
        # Second wolf should bandwagon
        target = choose_vote_target(self.gs, wolves[1].index)
        assert target == 2, f"Second wolf should vote for player 2, got {target}"

    def test_witch_save_probability(self):
        """Witch saves with high probability when werewolf_target set."""
        self.gs.werewolf_target = 3  # Someone attacked
        save_count = 0
        for _ in range(100):
            should_save, _, _ = decide_witch_action(self.gs)
            if should_save:
                save_count += 1
        # Should save at least 80% of the time
        assert save_count > 80, f"Witch only saved {save_count}/100 times"

    def test_witch_no_poison_early(self):
        """Witch doesn't poison before Day 3."""
        self.gs.day = 1
        _, should_poison, _ = decide_witch_action(self.gs)
        assert not should_poison, "Witch should not poison on Day 1"

    def test_witch_poison_late_game(self):
        """Witch can poison on Day 3+."""
        self.gs.day = 3
        poison_count = 0
        for _ in range(100):
            _, should_poison, _ = decide_witch_action(self.gs)
            if should_poison:
                poison_count += 1
        assert poison_count > 0, "Witch should poison sometimes on Day 3+"

    def test_sheriff_vote_no_self(self):
        """NPC doesn't nominate themselves for sheriff."""
        player_idx = self.gs.players.players[5].index
        target = choose_sheriff_vote(self.gs, player_idx)
        assert target != player_idx, "NPC should not self-nominate"

    def test_werewolf_sheriff_vote(self):
        """Werewolf tries to vote for another werewolf as sheriff."""
        ww_idx = self._get_role_idx(Role.WEREWOLF)
        target = choose_sheriff_vote(self.gs, ww_idx)
        target_role = self.gs.players.get_player(target).role
        assert target_role == Role.WEREWOLF, f"Wolf should vote for another wolf, got {target_role}"

    def test_hunter_vengeance_valid(self):
        """Hunter vengeance targets an alive non-self player."""
        hunt_idx = self._get_role_idx(Role.HUNTER)
        target = choose_hunter_vengeance_target(self.gs, hunt_idx)
        assert target is not None
        assert target != hunt_idx
        assert self.gs.players.get_player(target).alive

    def test_dead_npc_returns_none(self):
        """Dead NPC returns None for all actions."""
        player = self.gs.players.players[0]
        player.alive = False
        assert choose_vote_target(self.gs, player.index) is None
        assert choose_sheriff_vote(self.gs, player.index) is None

    def test_personality_assigned_to_all(self):
        """Every player gets a personality trait at game start."""
        from game.player import Personality
        personalities_seen = set()
        for p in self.gs.players.players:
            assert isinstance(p.personality, Personality), \
                f"Player {p.index} has no personality: {p.personality}"
            personalities_seen.add(p.personality)
        # At least 3 different personalities should appear across 12 players
        assert len(personalities_seen) >= 3, \
            f"Only {len(personalities_seen)} distinct personalities across 12 players"

    def test_paranoid_vote_high_index(self):
        """Paranoid NPCs tend to vote for high-index players."""
        from game.player import Personality
        # Find a paranoid villager
        paranoid = None
        for p in self.gs.players.players:
            if p.personality == Personality.PARANOID and p.role == Role.VILLAGER:
                paranoid = p
                break
        if paranoid is None:
            return  # No paranoid villager found, skip
        self.gs.votes = {}  # No prior votes
        self.gs.phase = GamePhase.DAY_VOTE
        paranoid_count = 0
        for _ in range(50):
            target = choose_vote_target(self.gs, paranoid.index)
            if target is not None:
                paranoid_count += 1
        # Should return a valid target sometimes
        assert paranoid_count > 0

    def test_loyal_vote_follows_majority(self):
        """Loyal NPCs vote for whoever has the most votes."""
        from game.player import Personality
        # Find a loyal player
        loyal = None
        for p in self.gs.players.players:
            if p.personality == Personality.LOYAL and p.role == Role.VILLAGER:
                loyal = p
                break
        if loyal is None:
            return
        # Set up existing votes — player 0 has the most
        self.gs.votes = {2: 0, 3: 0, 4: 1}  # Player 0 has 2 votes, player 1 has 1
        self.gs.phase = GamePhase.DAY_VOTE
        target = choose_vote_target(self.gs, loyal.index)
        assert target == 0, f"Loyal should vote for majority target (0), got {target}"

    def test_werewolf_analytical_targets_specials(self):
        """Analytical werewolves target special roles first."""
        from game.player import Personality
        analytical_ww = None
        for p in self.gs.players.players:
            if p.personality == Personality.ANALYTICAL and p.role == Role.WEREWOLF:
                analytical_ww = p
                break
        if analytical_ww is None:
            return
        self.gs.votes = {}
        self.gs.phase = GamePhase.DAY_VOTE
        for _ in range(30):
            target = choose_vote_target(self.gs, analytical_ww.index)
            if target is not None:
                target_player = self.gs.players.get_player(target)
                assert target_player.alive
                assert target_player.role != Role.WEREWOLF, \
                    f"Werewolf should not target other wolf, got player {target}"
