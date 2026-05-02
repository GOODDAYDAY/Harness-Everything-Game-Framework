"""Game phase state machine for Pixel Werewolf.

Standard 12-player werewolf game flows through these phases:
  SETUP
  → NIGHT_GUARD
  → NIGHT_WEREWOLF
  → NIGHT_WITCH
  → NIGHT_SEER
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
    NIGHT_WEREWOLF = auto()  # Werewolves choose target
    NIGHT_WITCH = auto()  # Witch decides potions
    NIGHT_SEER = auto()  # Seer investigates
    DAY_ANNOUNCE = auto()  # Night results announced
    DAY_SHERIFF_ELECTION = auto()  # Day 1 only: elect a sheriff
    DAY_DISCUSSION = auto()  # Players discuss
    DAY_VOTE = auto()  # Voting phase
    DAY_TRIAL = auto()  # Accused player defends (PK runoff)
    DAY_PK = auto()  # PK runoff voting (re-run DAY_VOTE with restricted candidates)
    DAY_VOTE_RESULT = auto()  # Vote result announced
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
            GamePhase.DAY_PK,
            GamePhase.DAY_TRIAL,
            GamePhase.DAY_VOTE_RESULT,
        }

    @property
    def display_name(self) -> str:
        """Human-readable phase name for UI and state queries."""
        # Delayed import to avoid circular dependency
        from game.text import _
        names = {
            GamePhase.SETUP: _("phase_setup"),
            GamePhase.NIGHT_GUARD: _("phase_night_guard"),
            GamePhase.NIGHT_SEER: _("phase_night_seer"),
            GamePhase.NIGHT_WEREWOLF: _("phase_night_werewolf"),
            GamePhase.NIGHT_WITCH: _("phase_night_witch"),
            GamePhase.DAY_ANNOUNCE: _("phase_day_announce"),
            GamePhase.DAY_SHERIFF_ELECTION: _("phase_day_sheriff"),
            GamePhase.DAY_DISCUSSION: _("phase_day_discussion"),
            GamePhase.DAY_VOTE: _("phase_day_vote"),
            GamePhase.DAY_TRIAL: _("phase_day_trial"),
            GamePhase.DAY_PK: _("phase_day_pk"),
            GamePhase.DAY_VOTE_RESULT: _("phase_day_result"),
            GamePhase.GAME_OVER: _("phase_game_over"),
        }
        return names[self]


# Order of night phases per the werewolf-rules skill:
# Guard (守卫) → Werewolf (狼人) → Witch (女巫) → Seer (预言家)
NIGHT_PHASE_ORDER: list[GamePhase] = [
    GamePhase.NIGHT_GUARD,
    GamePhase.NIGHT_WEREWOLF,
    GamePhase.NIGHT_WITCH,
    GamePhase.NIGHT_SEER,
]

# Order of day phases
DAY_PHASE_ORDER: list[GamePhase] = [
    GamePhase.DAY_ANNOUNCE,
    GamePhase.DAY_SHERIFF_ELECTION,
    GamePhase.DAY_DISCUSSION,
    GamePhase.DAY_VOTE,
    GamePhase.DAY_PK,
    GamePhase.DAY_TRIAL,
    GamePhase.DAY_VOTE_RESULT,
]
