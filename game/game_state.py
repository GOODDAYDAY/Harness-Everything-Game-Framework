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
from game.text import _


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
        self.last_guard_target: Optional[int] = None  # For no-consecutive-guard rule
        self.seer_target: Optional[int] = None

        # Sheriff election tracking
        self.sheriff_votes: dict[int, int] = {}  # voter_index -> candidate_index
        self.sheriff_election_done: bool = False  # Only once per game
        self.sheriff_election_result: Optional[dict] = None  # Filled after resolution
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

        # Night resolution storage (for game_loop death announcement flow)
        self._night_kills: Optional[int] = None
        self._night_poison: Optional[int] = None
        self._night_saved: bool = False
        self._night_resolved: bool = False

        # Vote tracking
        self.votes: dict[int, int] = {}  # voter_index -> target_index
        self.vote_result: Optional[int] = None  # eliminated player index

        # PK / Runoff tracking
        self.pk_mode: bool = False  # True when we're in a runoff round
        self.pk_candidates: set[int] = set()  # player indices tied and needing runoff
        self._phase_vote_reset: bool = False  # Signal to main loop to clear vote state

        # Game log
        self.log: list[dict] = []

        # Winner
        self.winner: Optional[str] = None

    @property
    def game_over(self) -> bool:
        """Check if the game has ended."""
        return self.phase == GamePhase.GAME_OVER

    def start_game(self) -> None:
        """Begin the game: advance from SETUP to first night."""
        self.phase = GamePhase.NIGHT_GUARD
        self.day = 1
        self._log("game_start", _("log_game_start"))

    def advance_night_phase(self) -> None:
        """Advance to the next night sub-phase."""
        current_idx = NIGHT_PHASE_ORDER.index(self.phase) if self.phase in NIGHT_PHASE_ORDER else -1
        if current_idx < 0 or current_idx >= len(NIGHT_PHASE_ORDER) - 1:
            # Moving from night to day — resolve night actions
            self.resolve_night()
            self.phase = GamePhase.DAY_ANNOUNCE
            self._log("day_start", _("log_night_results_announced", self.day))
        else:
            self.phase = NIGHT_PHASE_ORDER[current_idx + 1]
            self._log("phase", _("log_phase_changed", self.phase.display_name))

    def advance_day_phase(self) -> None:
        """Advance to the next day sub-phase.

        Skips DAY_SHERIFF_ELECTION after the first day (sheriff_election_done).
        """
        # Build effective phase order, skipping sheriff election after day 1
        effective_order = list(DAY_PHASE_ORDER)
        if self.sheriff_election_done and GamePhase.DAY_SHERIFF_ELECTION in effective_order:
            effective_order.remove(GamePhase.DAY_SHERIFF_ELECTION)

        # When leaving sheriff election phase, resolve it
        if self.phase == GamePhase.DAY_SHERIFF_ELECTION:
            if not self.sheriff_election_done:
                self._resolve_sheriff_election()
            # After election (or if already done), go to DAY_DISCUSSION
            # In the normal flow this is the correct next phase.
            # If election was already done (edge case), we still go to discussion
            # rather than treating it as DAY_ANNOUNCE position.
            self.phase = GamePhase.DAY_DISCUSSION
            self._log("phase", _("log_phase_changed", self.phase.display_name))
            return

        current_idx = effective_order.index(self.phase) if self.phase in effective_order else -1

        # Resolve votes when leaving DAY_VOTE or DAY_PK (vote-collection phases)
        if self.phase in (GamePhase.DAY_VOTE, GamePhase.DAY_PK):
            self._resolve_day()

            # PK (runoff) mode: rewind to DAY_VOTE for another round
            if self.pk_mode:
                self.phase = GamePhase.DAY_VOTE
                self._log("phase", _("log_pk_phase_changed", self.phase.display_name))
                self._phase_vote_reset = True
                return

        # If we just resolved a vote (VOTE or PK) and are NOT in pk_mode,
        # or we are at the end of the day phase list, handle end-of-day logic.
        if current_idx < 0 or current_idx >= len(effective_order) - 1:
            # At end of day phase list — check game over, go to next night
            if self.players.is_game_over():
                self.winner = self.players.get_winning_team()
                self.phase = GamePhase.GAME_OVER
                winner_display = {
                    "village": _("team_village"),
                    "werewolf": _("team_werewolf"),
                }.get(self.winner, self.winner)
                self._log("game_over", _("log_team_wins", winner_display))
            else:
                self.day += 1
                self.phase = GamePhase.NIGHT_GUARD
                self._reset_night_actions()
                self._log("night_start", _("log_night_begins", self.day))
            return

        # Normal advance to next phase
        self.phase = effective_order[current_idx + 1]
        self._log("phase", _("log_phase_changed", self.phase.display_name))

    def _resolve_sheriff_election(self) -> None:
        """Resolve the sheriff election — the candidate with the most votes becomes sheriff."""
        result: dict = {"votes": {}, "winner": None, "tie": False, "no_votes": False}
        if not self.sheriff_votes:
            self._log("sheriff_election", _("log_no_sheriff"))
            result["no_votes"] = True
            result["votes"] = {}
            self.sheriff_election_result = result
            self.sheriff_election_done = True
            return
        # Count votes
        vote_counts: dict[int, int] = {}
        for candidate in self.sheriff_votes.values():
            vote_counts[candidate] = vote_counts.get(candidate, 0) + 1
        # Build result dict with player names
        for pidx, vcount in vote_counts.items():
            pname = self.players.get_player(pidx).display_name
            result["votes"][pidx] = {"name": pname, "count": vcount}
        # Find max
        max_votes = max(vote_counts.values())
        top_candidates = [p for p, v in vote_counts.items() if v == max_votes]
        if len(top_candidates) == 1:
            sheriff_idx = top_candidates[0]
            self.players.get_player(sheriff_idx).is_sheriff = True
            sheriff_name = self.players.get_player(sheriff_idx).display_name
            self._log("sheriff_election", _("log_sheriff_elected", sheriff_name, sheriff_idx))
            result["winner"] = {"idx": sheriff_idx, "name": sheriff_name, "votes": max_votes}
        else:
            self._log("sheriff_election", _("log_sheriff_tie"))
            result["tie"] = True
            result["top_candidates"] = [
                {"idx": p, "name": self.players.get_player(p).display_name}
                for p in top_candidates
            ]
        self.sheriff_election_result = result
        self.sheriff_election_done = True

    def _resolve_day(self) -> None:
        """Resolve day vote — eliminate the most-voted player.

        If there is a tie, trigger a PK (runoff) round.
        """
        if not self.votes:
            self._log("vote", _("log_no_votes"))
            return

        # If we are in PK mode, use the runoff logic
        if self.pk_mode:
            self._resolve_runoff()
            return

        # Normal vote resolution
        eliminated, tie = self._tally_votes()

        if tie:
            # Trigger PK runoff
            self.pk_mode = True
            self.pk_candidates = set(eliminated)
            names = [self.players.get_player(t).display_name for t in eliminated]
            if len(eliminated) == 2:
                self._log("vote_tie", _("vote_runoff", names[0], names[1]))
            else:
                self._log("vote_tie", _("vote_tie", names[0], names[1]))
            # Clear votes for the runoff round — NPCs will re-vote next frame
            self.votes = {}
            return

        # Single winner — eliminate
        self.vote_result = eliminated
        eliminated_player = self.players.get_player(eliminated)
        if eliminated_player:
            self.players.kill_player(eliminated)
            self._log(
                "elimination",
                _("log_eliminated_by_vote", eliminated_player.display_name, eliminated, eliminated_player.role.name_zh)
            )
            # Hunter vengeance: if the eliminated player is a hunter, trigger their shot
            if eliminated_player.role == Role.HUNTER:
                self._log("hunter", _("log_hunter_vengeance", eliminated_player.display_name))
                self._hunter_needs_vengeance = True
                self._hunter_vengeance_idx = eliminated

        if self.players.is_game_over():
            self.winner = self.players.get_winning_team()

    def _tally_votes(self) -> tuple[int | list[int] | None, bool]:
        """Count votes and return (winner_or_candidates, is_tie).

        Returns:
            (eliminated_index, False) — single majority winner
            ([candidates], True)      — tie between multiple candidates
            (None, False)             — no votes cast
        """
        if not self.votes:
            return None, False

        # Count votes (sheriff's vote counts as 1.5)
        sheriff_idx = None
        for p in self.players.players:
            if p.is_sheriff and p.alive:
                sheriff_idx = p.index
                break

        vote_counts: dict[int, float] = {}
        for voter_idx, target in self.votes.items():
            weight = 1.5 if voter_idx == sheriff_idx else 1.0
            vote_counts[target] = vote_counts.get(target, 0.0) + weight

        if not vote_counts:
            return None, False

        max_votes = max(vote_counts.values())
        top_candidates = [p for p, v in vote_counts.items() if v == max_votes]

        if len(top_candidates) > 1:
            return top_candidates, True

        return top_candidates[0], False

    def _resolve_runoff(self) -> None:
        """Resolve a PK (runoff) round.

        Only votes for the tied candidates count. If still tied, no elimination.
        """
        eliminated, tie = self._tally_votes()

        if tie:
            self._log("vote_no_one", _("vote_runoff_tie"))
            self.pk_mode = False
            self.pk_candidates = set()
            return

        if eliminated is None:
            self._log("vote_no_one", _("vote_no_one"))
            self.pk_mode = False
            self.pk_candidates = set()
            return

        # Elimination from runoff
        self.vote_result = eliminated
        self.pk_mode = False
        self.pk_candidates = set()
        eliminated_player = self.players.get_player(eliminated)
        if eliminated_player:
            self.players.kill_player(eliminated)
            self._log(
                "elimination",
                _("log_eliminated_by_pk", eliminated_player.display_name, eliminated, eliminated_player.role.name_zh)
            )
            if eliminated_player.role == Role.HUNTER:
                self._log("hunter", _("log_hunter_vengeance", eliminated_player.display_name))
                self._hunter_needs_vengeance = True
                self._hunter_vengeance_idx = eliminated

        if self.players.is_game_over():
            self.winner = self.players.get_winning_team()

    def resolve_hunter_vengeance(self, target_idx: Optional[int]) -> None:
        """Resolve hunter's vengeance — kill the target player.

        If target_idx is None, the hunter has no valid target (e.g. no other alive players).
        """
        if target_idx is not None:
            self.players.kill_player(target_idx)
            target_player = self.players.get_player(target_idx)
            self._log(
                "elimination",
                _("log_hunter_shot", target_player.display_name, target_idx)
            )
        else:
            self._log("hunter", _("log_no_hunter_target"))
        self._hunter_needs_vengeance = False
        self._hunter_vengeance_idx = None

    @property
    def hunter_needs_vengeance(self) -> bool:
        """Check if a hunter has been eliminated and needs to choose a target."""
        return self._hunter_needs_vengeance

    def _reset_night_actions(self) -> None:
        """Reset all night action tracking for a new night."""
        # Save last guard target before clearing for no-consecutive-guard rule
        self.last_guard_target = self.guard_target
        self.guard_target = None
        self.seer_target = None
        self.werewolf_target = None
        self.witch_heal_target = None
        self.witch_poison_target = None
        self.last_night_victim = None
        self.last_night_saved = False
        self.hunter_vengeance_target = None
        self.votes = {}
        self.sheriff_votes = {}
        self.vote_result = None
        self.pk_mode = False
        self.pk_candidates = set()
        self._phase_vote_reset = False
        self._night_resolved = False
        # Reset per-night flags on all alive players
        for p in self.players.players:
            p.protected = False
            p.poisoned = False

    @property
    def night_actions(self) -> dict:
        """Return a dict of current night actions by role."""
        actions = {}
        if self.guard_target is not None:
            actions["guard"] = self.guard_target
        if self.werewolf_target is not None:
            actions["werewolf"] = self.werewolf_target
        if self.seer_target is not None:
            actions["seer"] = self.seer_target
        if self.witch_heal_target is not None:
            actions["witch_heal"] = self.witch_heal_target
        if self.witch_poison_target is not None:
            actions["witch_poison"] = self.witch_poison_target
        return actions

    def set_night_action(self, action_name: str, actor_idx: int, target: int) -> None:
        """Record a night action by role name."""
        if action_name == "guard":
            self.guard_target = target
        elif action_name == "werewolf":
            self.werewolf_target = target
        elif action_name == "seer":
            self.seer_target = target
        elif action_name == "witch_heal" or action_name == "witch_save":
            self.witch_heal_target = target
        elif action_name == "witch_poison" or action_name == "witch_kill":
            self.witch_poison_target = target

    def cast_vote(self, voter_idx: int, target_idx: int) -> None:
        """Record a vote from a player."""
        self.votes[voter_idx] = target_idx

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
        if self._night_resolved:
            # Return cached result if already resolved this night
            return {
                "guard_target": self.guard_target,
                "werewolf_target": self.werewolf_target,
                "saved": self._night_saved,
                "victim": self._night_kills,
                "poisoned": self._night_poison,
                "hunter_vengeance": self._hunter_needs_vengeance,
                "hunter_victim": None,
            }

        self._night_kills = None
        self._night_poison = None
        self._night_saved = False

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
        saved_index = None
        if self.werewolf_target is not None:
            target_player = self.players.get_player(self.werewolf_target)
            if target_player and target_player.protected:
                saved = True
                saved_index = self.werewolf_target
            elif target_player:
                # Werewolf kills the target
                self.players.kill_player(self.werewolf_target)
                self.last_night_victim = self.werewolf_target
                self._night_kills = self.werewolf_target
                result["victim"] = self.werewolf_target
                # Check if the victim was a hunter
                if target_player.role == Role.HUNTER:
                    self._hunter_needs_vengeance = True
                    self._hunter_vengeance_idx = self.werewolf_target
                    self._log("hunter", _("log_hunter_killed_night", target_player.display_name))

        # Witch heal
        if self.witch_heal_target is not None and not self.witch_used_heal:
            # Witch heals the victim
            victim = self.players.get_player(self.witch_heal_target)
            if victim and not victim.alive:
                victim.alive = True
                self._night_kills = None  # Victim was saved
                self.last_night_saved = True
                result["saved"] = True
                saved_index = self.witch_heal_target
            self.witch_used_heal = True

        # Witch poison
        if self.witch_poison_target is not None and not self.witch_used_poison:
            self.players.kill_player(self.witch_poison_target)
            self._night_poison = self.witch_poison_target
            result["poisoned"] = self.witch_poison_target
            self.witch_used_poison = True
            # Check if the poisoned player was a hunter
            poisoned_player = self.players.get_player(self.witch_poison_target)
            if poisoned_player and poisoned_player.role == Role.HUNTER:
                self._hunter_needs_vengeance = True
                self._hunter_vengeance_idx = self.witch_poison_target
                self._log("hunter", _("log_hunter_poisoned", poisoned_player.display_name))

        self._night_saved = saved or result["saved"]
        result["saved"] = self._night_saved
        result["saved_index"] = saved_index if saved_index is not None else self._night_saved

        # If the witch healed the werewolf's victim, cancel hunter vengeance
        # (the hunter was revived and shouldn't take vengeance)
        if result["saved"] and result["victim"] is not None and self.witch_heal_target == result["victim"]:
            # The night victim was saved by the witch — no vengeance
            self._hunter_needs_vengeance = False
            self._hunter_vengeance_idx = None
            result["hunter_vengeance"] = False
        else:
            # Resolve hunter vengeance if needed (hunter killed at night)
            if self.hunter_needs_vengeance and (result["victim"] is not None or result["poisoned"] is not None):
                # Hunter vengeance is resolved in DAY_ANNOUNCE phase in main.py
                result["hunter_vengeance"] = True

        self._night_resolved = True
        self._log("night_resolve", _("log_night_resolved", result.get('victim'), result.get('saved')))

        # Check game over after night
        if self.players.is_game_over():
            self.winner = self.players.get_winning_team()
            self.phase = GamePhase.GAME_OVER
            self._log("game_over", _("log_team_wins", _("team_" + self.winner)))

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
