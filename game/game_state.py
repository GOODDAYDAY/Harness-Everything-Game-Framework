"""Game state machine managing the full werewolf game flow."""

from __future__ import annotations

from typing import Optional
from game.roles import ROSTER_12_PLAYER, Role
from game.player import PlayerManager
from game.phases import (
    GamePhase,
    NIGHT_PHASE_ORDER,
    DAY_PHASE_ORDER,
)


class GameState:
    """Central game state for Pixel Werewolf.

    Tracks:
    - Current phase
    - Day/night cycle
    - All players and their roles
    - Night actions (guard target, seer target, werewolf target, witch actions)
    - Vote counts
    - Game log
    """

    def __init__(self):
        self.phase: GamePhase = GamePhase.SETUP
        self.day: int = 1
        self.players: PlayerManager = PlayerManager(ROSTER_12_PLAYER)

        # Night action tracking
        self.guard_target: Optional[int] = None
        self.seer_target: Optional[int] = None
        self.werewolf_target: Optional[int] = None
        self.witch_heal_target: Optional[int] = None
        self.witch_poison_target: Optional[int] = None
        self.witch_used_heal: bool = False
        self.witch_used_poison: bool = False

        # Night result tracking
        self.last_night_victim: Optional[int] = None
        self.last_night_saved: bool = False

        # Hunter vengeance tracking
        self.hunter_vengeance_target: Optional[int] = None
        self._hunter_vengeance_idx: Optional[int] = None  # Index of the hunter who needs to shoot
        self._hunter_needs_vengeance: bool = False  # True when a hunter is eliminated and needs to choose a target

        # Vote tracking
        self.votes: dict[int, int] = {}  # voter_index -> target_index
        self.vote_result: Optional[int] = None  # eliminated player index

        # Game log
        self.log: list[dict] = []

        # Winner
        self.winner: Optional[str] = None

    def start_game(self) -> None:
        """Begin the game: advance from SETUP to first night."""
        self.phase = GamePhase.NIGHT_GUARD
        self.day = 1
        self._log("game_start", "Game started! Day 1 Night — Guard phase.")

    def advance_night_phase(self) -> None:
        """Advance to the next night sub-phase."""
        current_idx = NIGHT_PHASE_ORDER.index(self.phase) if self.phase in NIGHT_PHASE_ORDER else -1
        if current_idx < 0 or current_idx >= len(NIGHT_PHASE_ORDER) - 1:
            # Move to day
            self.phase = GamePhase.DAY_ANNOUNCE
            self._log("day_start", f"Day {self.day} — Night results announced.")
        else:
            self.phase = NIGHT_PHASE_ORDER[current_idx + 1]
            self._log("phase", f"Phase changed to {self.phase.display_name}")

    def advance_day_phase(self) -> None:
        """Advance to the next day sub-phase."""
        current_idx = DAY_PHASE_ORDER.index(self.phase) if self.phase in DAY_PHASE_ORDER else -1
        if current_idx < 0 or current_idx >= len(DAY_PHASE_ORDER) - 1:
            # End of day — resolve, check game over, go to next night
            self._resolve_day()
            if self.players.is_game_over():
                self.winner = self.players.get_winning_team()
                self.phase = GamePhase.GAME_OVER
                self._log("game_over", f"{self.winner} team wins!")
            else:
                self.day += 1
                self.phase = GamePhase.NIGHT_GUARD
                self._reset_night_actions()
                self._log("night_start", f"Day {self.day} Night begins.")
        else:
            self.phase = DAY_PHASE_ORDER[current_idx + 1]
            self._log("phase", f"Phase changed to {self.phase.display_name}")

    def _resolve_day(self) -> None:
        """Resolve day vote — eliminate the most-voted player."""
        if not self.votes:
            self._log("vote", "No votes cast. No one was eliminated.")
            return
        # Count votes
        vote_counts: dict[int, int] = {}
        for target in self.votes.values():
            vote_counts[target] = vote_counts.get(target, 0) + 1
        # Find max
        max_votes = max(vote_counts.values())
        top_targets = [p for p, v in vote_counts.items() if v == max_votes]
        if len(top_targets) == 1:
            eliminated = top_targets[0]
            self.players.kill_player(eliminated)
            self.vote_result = eliminated
            eliminated_player = self.players.get_player(eliminated)
            self._log(
                "elimination",
                f"{eliminated_player.name} (Player {eliminated}) was eliminated by vote."
                f" They were a {eliminated_player.role.name_zh}."
            )
            # Hunter vengeance: if the eliminated player is a hunter, trigger their shot
            if eliminated_player.role == Role.HUNTER:
                self._log("hunter", f"{eliminated_player.name} (Hunter) is taking vengeance!")
                self._hunter_needs_vengeance = True
                self._hunter_vengeance_idx = eliminated
        else:
            self._log("vote", "Tie vote — no one was eliminated.")

    def resolve_hunter_vengeance(self, target_idx: Optional[int]) -> None:
        """Resolve hunter's vengeance — kill the target player.

        If target_idx is None, the hunter has no valid target (e.g. no other alive players).
        """
        if target_idx is not None:
            self.players.kill_player(target_idx)
            target_player = self.players.get_player(target_idx)
            self._log(
                "elimination",
                f"{target_player.name} (Player {target_idx}) was shot by the Hunter's vengeance!"
            )
        else:
            self._log("hunter", "The Hunter has no valid vengeance target.")
        self._hunter_needs_vengeance = False
        self._hunter_vengeance_idx = None

    @property
    def hunter_needs_vengeance(self) -> bool:
        """Check if a hunter has been eliminated and needs to choose a target."""
        return self._hunter_needs_vengeance

    def _reset_night_actions(self) -> None:
        """Reset all night action tracking for a new night."""
        self.guard_target = None
        self.seer_target = None
        self.werewolf_target = None
        self.witch_heal_target = None
        self.witch_poison_target = None
        self.last_night_victim = None
        self.last_night_saved = False
        self.hunter_vengeance_target = None
        self.votes = {}
        self.vote_result = None
        # Reset per-night flags on all alive players
        for p in self.players.players:
            p.protected = False
            p.poisoned = False

    def _log(self, event: str, message: str) -> None:
        """Add an entry to the game log."""
        self.log.append({
            "day": self.day,
            "phase": self.phase.display_name,
            "event": event,
            "message": message,
        })

    def resolve_night(self) -> dict:
        """Resolve all night actions at the end of night phases.
        Returns a dict with night result info for UI display.
        """
        result = {
            "guard_target": self.guard_target,
            "werewolf_target": self.werewolf_target,
            "saved": False,
            "victim": None,
            "poisoned": None,
            "hunter_vengeance": False,
            "hunter_victim": None,
        }

        # Determine if the werewolf target is protected by guard
        saved = False
        if self.werewolf_target is not None:
            target_player = self.players.get_player(self.werewolf_target)
            if target_player and target_player.protected:
                saved = True
            elif target_player:
                # Werewolf kills the target
                self.players.kill_player(self.werewolf_target)
                self.last_night_victim = self.werewolf_target
                result["victim"] = self.werewolf_target
                # Check if the victim was a hunter
                if target_player.role == Role.HUNTER:
                    self._hunter_needs_vengeance = True
                    self._hunter_vengeance_idx = self.werewolf_target
                    self._log("hunter", f"{target_player.name} (Hunter) was killed — taking vengeance!")

        # Witch heal
        if self.witch_heal_target is not None and not self.witch_used_heal:
            # Witch heals the victim
            victim = self.players.get_player(self.witch_heal_target)
            if victim and not victim.alive:
                victim.alive = True
                self.last_night_saved = True
                result["saved"] = True
            self.witch_used_heal = True

        # Witch poison
        if self.witch_poison_target is not None and not self.witch_used_poison:
            self.players.kill_player(self.witch_poison_target)
            result["poisoned"] = self.witch_poison_target
            self.witch_used_poison = True
            # Check if the poisoned player was a hunter
            poisoned_player = self.players.get_player(self.witch_poison_target)
            if poisoned_player and poisoned_player.role == Role.HUNTER:
                self._hunter_needs_vengeance = True
                self._hunter_vengeance_idx = self.witch_poison_target
                self._log("hunter", f"{poisoned_player.name} (Hunter) was poisoned — taking vengeance!")

        result["saved"] = saved or result["saved"]

        # Resolve hunter vengeance if needed (hunter killed at night)
        if self.hunter_needs_vengeance and (result["victim"] is not None or result["poisoned"] is not None):
            # Hunter vengeance is resolved in DAY_ANNOUNCE phase in main.py
            result["hunter_vengeance"] = True

        self._log("night_resolve", f"Night resolved. Victim: {result.get('victim')}, Saved: {result.get('saved')}")

        # Check game over after night
        if self.players.is_game_over():
            self.winner = self.players.get_winning_team()
            self.phase = GamePhase.GAME_OVER
            self._log("game_over", f"{self.winner} team wins!")

        return result

    def to_dict(self) -> dict:
        """Export full state for TCP bridge / state query."""
        return {
            "phase": self.phase.display_name,
            "phase_key": self.phase.name,
            "day": self.day,
            "is_night": self.phase.is_night,
            "is_day": self.phase.is_day,
            "game_over": self.phase == GamePhase.GAME_OVER,
            "winner": self.winner,
            **self.players.to_dict(),
            "log": self.log[-10:],  # Last 10 log entries
        }
