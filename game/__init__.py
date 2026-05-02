# Pixel Werewolf — game logic package
"""Pixel Werewolf — game logic package.

Core game state, roles, phases, NPC AI, rendering, and UI.
"""

from __future__ import annotations

from game.game_state import GameState
from game.npc_ai import (
    choose_night_action,
    choose_vote_target,
    choose_sheriff_vote,
    decide_witch_action,
    choose_hunter_vengeance_target,
    get_eligible_targets,
)
from game.npc_discussion import (
    generate_discussion,
)
from game.phases import GamePhase, NIGHT_PHASE_ORDER, DAY_PHASE_ORDER
from game.player import Player, PlayerManager, Personality
from game.renderer import VillageRenderer
from game.roles import Role, Team, ROSTER_12_PLAYER

__all__ = [
    "GameState",
    "GamePhase",
    "NIGHT_PHASE_ORDER",
    "DAY_PHASE_ORDER",
    "Role",
    "Team",
    "ROSTER_12_PLAYER",
    "Player",
    "PlayerManager",
    "Personality",
    "VillageRenderer",
    "choose_night_action",
    "choose_vote_target",
    "choose_sheriff_vote",
    "decide_witch_action",
    "choose_hunter_vengeance_target",
    "get_eligible_targets",
    "generate_discussion",
]
