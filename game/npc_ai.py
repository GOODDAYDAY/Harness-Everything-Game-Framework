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
            # Seer investigates anyone alive
            return alive_indices
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

    Returns the index of the target player, or None if no valid target.
    """
    targets = get_eligible_targets(state, player_idx, phase)
    if not targets:
        return None

    player = state.players.get_player(player_idx)
    if not player:
        return None

    match phase:
        case GamePhase.NIGHT_GUARD if player.role == Role.GUARD:
            return random.choice(targets)
        case GamePhase.NIGHT_SEER if player.role == Role.SEER:
            return random.choice(targets)
        case GamePhase.NIGHT_WEREWOLF if player.role == Role.WEREWOLF:
            return random.choice(targets)
        case _:
            return None


def choose_vote_target(state: GameState, player_idx: int) -> int | None:
    """Choose a player to vote for during the day vote phase.

    Simple strategy: vote for a random alive player (not self).
    """
    targets = get_eligible_targets(state, player_idx, GamePhase.DAY_VOTE)
    if not targets:
        return None
    return random.choice(targets)


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
    """
    witch_players = [p for p in state.players.players if p.role == Role.WITCH]
    if not witch_players:
        return False, False, None

    witch = witch_players[0]
    if not witch.alive:
        return False, False, None

    # Save: 50% chance to use antidote if someone was targeted by werewolves
    # Use werewolf_target (set during NIGHT_WEREWOLF phase) rather than
    # last_night_victim (which is only set later in resolve_night)
    should_save = False
    if state.werewolf_target is not None and not state.witch_used_heal:
        should_save = random.random() < 0.5

    # Poison: 30% chance to poison a random alive player
    should_poison = False
    poison_target = None
    if random.random() < 0.3 and not state.witch_used_poison:
        alive = state.players.get_alive_players()
        targets = [p.index for p in alive if p.index != witch.index]
        if targets:
            should_poison = True
            poison_target = random.choice(targets)

    return should_save, should_poison, poison_target
