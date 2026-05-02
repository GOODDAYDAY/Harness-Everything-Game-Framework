"""Game phase state machine for Pixel Werewolf.

Standard 12-player werewolf game flows through these phases:
  SETUP
  → NIGHT_GUARD
  → NIGHT_SEER
  → NIGHT_WEREWOLF
  → NIGHT_WITCH
  → DAY_ANNOUNCE
  → DAY_DISCUSSION
  → DAY_VOTE
  → DAY_RESULT
  → (back to NIGHT_GUARD or GAME_OVER)
"""

from __future__ import annotations

from enum import Enum, auto


class GamePhase(Enum):
    """All game phases in sequence."""
    SETUP = auto()
    NIGHT_GUARD = auto()  # Guard chooses who to protect
    NIGHT_SEER = auto()  # Seer investigates
    NIGHT_WEREWOLF = auto()  # Werewolves choose target
    NIGHT_WITCH = auto()  # Witch decides potions
    DAY_ANNOUNCE = auto()  # Night results announced
    DAY_SHERIFF_ELECTION = auto()  # Day 1 only: elect a sheriff
    DAY_DISCUSSION = auto()  # Players discuss
    DAY_VOTE = auto()  # Voting phase
    DAY_RESULT = auto()  # Vote result announced
    GAME_OVER = auto()  # Game ended

    @property
    def is_night(self) -> bool:
        return self in {
            GamePhase.NIGHT_GUARD,
            GamePhase.NIGHT_SEER,
            GamePhase.NIGHT_WEREWOLF,
            GamePhase.NIGHT_WITCH,
        }

    @property
    def is_day(self) -> bool:
        return self in {
            GamePhase.DAY_ANNOUNCE,
            GamePhase.DAY_SHERIFF_ELECTION,
            GamePhase.DAY_DISCUSSION,
            GamePhase.DAY_VOTE,
            GamePhase.DAY_RESULT,
        }

    @property
    def display_name(self) -> str:
        """Human-readable phase name for UI and state queries."""
        names = {
            GamePhase.SETUP: "Setup",
            GamePhase.NIGHT_GUARD: "Night — Guard",
            GamePhase.NIGHT_SEER: "Night — Seer",
            GamePhase.NIGHT_WEREWOLF: "Night — Werewolves",
            GamePhase.NIGHT_WITCH: "Night — Witch",
            GamePhase.DAY_ANNOUNCE: "Day — Announcement",
            GamePhase.DAY_SHERIFF_ELECTION: "Day — Sheriff Election",
            GamePhase.DAY_DISCUSSION: "Day — Discussion",
            GamePhase.DAY_VOTE: "Day — Voting",
            GamePhase.DAY_RESULT: "Day — Result",
            GamePhase.GAME_OVER: "Game Over",
        }
        return names[self]


# Order of night phases
NIGHT_PHASE_ORDER: list[GamePhase] = [
    GamePhase.NIGHT_GUARD,
    GamePhase.NIGHT_SEER,
    GamePhase.NIGHT_WEREWOLF,
    GamePhase.NIGHT_WITCH,
]

# Order of day phases
DAY_PHASE_ORDER: list[GamePhase] = [
    GamePhase.DAY_ANNOUNCE,
    GamePhase.DAY_SHERIFF_ELECTION,
    GamePhase.DAY_DISCUSSION,
    GamePhase.DAY_VOTE,
    GamePhase.DAY_RESULT,
]
