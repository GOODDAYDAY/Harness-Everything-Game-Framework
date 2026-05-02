#!/usr/bin/env python3
"""NPC AI decision-making for Pixel Werewolf.

Provides simple random-but-valid decisions for all NPC players
during night and day phases.
"""

from __future__ import annotations

import random

from game.game_state import GameState
from game.phases import GamePhase
from game.roles import Role


def get_eligible_targets(state: GameState, actor_idx: int, phase: GamePhase) -> list[int]:
    """Get valid target indices for the given actor and phase.

    Returns list of player indices the actor can target.
    """
    actor = state.players.get_player(actor_idx)
    if not actor or not actor.alive:
        return []

    alive = state.players.get_alive_players()
    alive_indices = [p.index for p in alive]

    match phase:
        case GamePhase.NIGHT_GUARD:
            # Guard can protect anyone alive (including self)
            return alive_indices
        case GamePhase.NIGHT_SEER:
            # Seer investigates anyone alive except themselves
            return [i for i in alive_indices if i != actor_idx]
        case GamePhase.NIGHT_WEREWOLF:
            # Werewolves target anyone alive except fellow werewolves
            werewolves = state.players.get_werewolf_players()
            ww_indices = {p.index for p in werewolves}
            return [i for i in alive_indices if i not in ww_indices]
        case GamePhase.DAY_VOTE:
            # Vote for anyone alive except self
            return [i for i in alive_indices if i != actor_idx]
        case _:
            return alive_indices


def choose_night_action(state: GameState, player_idx: int, phase: GamePhase) -> int | None:
    """Choose a night action target for an NPC player.

    Strategic logic per role:
    - Guard: protect a player likely to be targeted (sheriff, known villagers)
    - Seer: prioritise investigating suspicious players
    - Werewolf: avoid killing fellow werewolves; prioritise powerful roles
    """
    targets = get_eligible_targets(state, player_idx, phase)
    if not targets:
        return None

    player = state.players.get_player(player_idx)
    if not player:
        return None

    match phase:
        case GamePhase.NIGHT_GUARD if player.role == Role.GUARD:
            # Guard prioritises the sheriff if alive and not self
            alive = state.players.get_alive_players()
            sheriff = [p for p in alive if p.is_sheriff and p.index != player_idx]
            if sheriff:
                return sheriff[0].index
            # Otherwise protect a random alive player (not self)
            non_self = [p.index for p in alive if p.index != player_idx]
            return random.choice(non_self) if non_self else random.choice(targets)

        case GamePhase.NIGHT_SEER if player.role == Role.SEER:
            # Seer: prioritise players who haven't been investigated yet
            # (If we had an investigation history, we'd check it. For now, random.)
            return random.choice(targets)

        case GamePhase.NIGHT_WEREWOLF if player.role == Role.WEREWOLF:
            # Werewolves: never kill fellow werewolves
            non_ww = [t for t in targets
                      if state.players.get_player(t).role != Role.WEREWOLF]
            if non_ww:
                # Weighted random — give higher priority to powerful roles
                weighted = []
                for t in non_ww:
                    p = state.players.get_player(t)
                    weight = 1
                    if p.is_sheriff:
                        weight = 5  # Sheriff is high priority
                    elif p.role == Role.SEER:
                        weight = 4  # Seer is dangerous
                    elif p.role == Role.WITCH:
                        weight = 3  # Witch can heal
                    elif p.role == Role.GUARD:
                        weight = 2  # Guard can protect
                    elif p.role == Role.HUNTER:
                        weight = 2  # Hunter can retaliate
                    weighted.extend([t] * weight)
                return random.choice(weighted) if weighted else random.choice(non_ww)
            return random.choice(targets)

        case _:
            return None


def choose_vote_target(state: GameState, player_idx: int) -> int | None:
    """Choose a player to vote for during the day vote phase.

    Strategy:
    - Werewolves: vote together to eliminate villagers (bandwagon)
    - Village players: random vote (no investigation info shared yet)
    """
    targets = get_eligible_targets(state, player_idx, GamePhase.DAY_VOTE)
    if not targets:
        return None

    player = state.players.get_player(player_idx)
    if not player or not player.alive:
        return None

    # Werewolves: coordinate to eliminate a non-werewolf
    if player.role == Role.WEREWOLF:
        # Find non-werewolf alive players
        alive = state.players.get_alive_players()
        non_ww = [p for p in alive
                  if p.role != Role.WEREWOLF and p.index != player_idx]
        if non_ww:
            # Check if other werewolves have already voted — bandwagon
            ww_alive = [p for p in alive if p.role == Role.WEREWOLF and p.index != player_idx]
            existing_votes: dict[int, int] = {}
            for w in ww_alive:
                if w.index in state.votes:
                    t = state.votes[w.index]
                    existing_votes[t] = existing_votes.get(t, 0) + 1
            if existing_votes:
                # Join the most popular werewolf target
                max_count = max(existing_votes.values())
                top_targets = [t for t, c in existing_votes.items() if c == max_count]
                return random.choice(top_targets)
            # No existing wolf votes: pick a random non-wolf
            return random.choice([p.index for p in non_ww])
        return random.choice(targets)

    # Village players: vote randomly (no shared info)
    return random.choice(targets)


def choose_sheriff_vote(state: GameState, player_idx: int) -> int | None:
    """Choose a player to nominate for sheriff during the sheriff election.

    Cannot vote for self. Prefers non-werewolf candidates (simple heuristic).
    If the voter is a werewolf, they try to vote for another werewolf.
    """
    player = state.players.get_player(player_idx)
    if not player or not player.alive:
        return None
    alive = state.players.get_alive_players()
    # Exclude self
    valid = [p.index for p in alive if p.index != player_idx]
    if not valid:
        return None

    # Werewolves: try to vote for another werewolf
    if player.role == Role.WEREWOLF:
        ww_indices = [p.index for p in alive if p.role == Role.WEREWOLF and p.index != player_idx]
        if ww_indices:
            return random.choice(ww_indices)

    # Village: vote randomly (avoid werewolves if they had information)
    # For now, simple random choice (no metagaming)
    return random.choice(valid)


def choose_hunter_vengeance_target(state: GameState, hunter_idx: int) -> int | None:
    """Choose a vengeance target when the Hunter is eliminated.

    The hunter shoots one other alive player. Returns target index or None.
    """
    # The hunter is already dead — find other alive players
    alive = state.players.get_alive_players()
    valid = [p.index for p in alive if p.index != hunter_idx]
    if not valid:
        return None
    return random.choice(valid)


def decide_witch_action(state: GameState) -> tuple[bool, bool, int | None]:
    """Decide witch NPC actions.

    Returns (should_save, should_poison, poison_target).

    Strategy:
    - 90% chance to save the werewolf target (antidote is precious)
    - 25% chance to poison if it's late game (Day 3+) and haven't used poison
    - Prefer poisoning suspicious players (sheriff knows who's suspicious)
    """
    witch_players = [p for p in state.players.players if p.role == Role.WITCH]
    if not witch_players:
        return False, False, None

    witch = witch_players[0]
    if not witch.alive:
        return False, False, None

    # Save: 90% chance to use antidote if someone was targeted by werewolves
    should_save = False
    if state.werewolf_target is not None and not state.witch_used_heal:
        should_save = random.random() < 0.9

    # Poison: use later in the game
    should_poison = False
    poison_target = None
    if state.day >= 3 and random.random() < 0.25 and not state.witch_used_poison:
        alive = state.players.get_alive_players()
        targets = [p.index for p in alive if p.index != witch.index]
        if targets:
            should_poison = True
            poison_target = random.choice(targets)

    return should_save, should_poison, poison_target
