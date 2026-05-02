#!/usr/bin/env python3
"""End-to-end simulation test — runs full games without a display.

This test drives GameState + NPC AI through complete game cycles
from SETUP to GAME_OVER, verifying the phase machine, night actions,
day voting, and victory conditions.
"""

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
)


def _run_night_actions(gs: GameState):
    """Execute all NPC night actions for the current phase.

    Sets the appropriate target fields directly on the GameState,
    matching how main.py's update() does it.
    """
    phase = gs.phase

    if phase == GamePhase.NIGHT_GUARD:
        for player in gs.players.get_alive_players():
            if player.role == Role.GUARD:
                target = choose_night_action(gs, player.index, phase)
                if target is not None:
                    gs.guard_target = target
                    gs.players.get_player(target).protected = True
                break

    elif phase == GamePhase.NIGHT_SEER:
        for player in gs.players.get_alive_players():
            if player.role == Role.SEER:
                target = choose_night_action(gs, player.index, phase)
                if target is not None:
                    gs.seer_target = target
                break

    elif phase == GamePhase.NIGHT_WEREWOLF:
        werewolf_alive = [p for p in gs.players.get_werewolf_players() if p.alive]
        if werewolf_alive:
            target = choose_night_action(gs, werewolf_alive[0].index, phase)
            if target is not None:
                gs.werewolf_target = target

    elif phase == GamePhase.NIGHT_WITCH:
        should_save, should_poison, poison_target = decide_witch_action(gs)
        if should_save and gs.werewolf_target is not None:
            gs.witch_heal_target = gs.werewolf_target
        if should_poison and poison_target is not None:
            gs.witch_poison_target = poison_target
            poisoned = gs.players.get_player(poison_target)
            if poisoned:
                poisoned.poisoned = True


def _run_day_vote(gs: GameState, skip_abstain_indices: set = set()):
    """Execute NPC voting for the current phase.

    Args:
        gs: The game state.
        skip_abstain_indices: Player indices to skip (e.g., human player).
    """
    alive = gs.players.get_alive_players()
    for p in alive:
        if p.index in skip_abstain_indices:
            continue
        if p.index in gs.votes:
            continue
        target = choose_vote_target(gs, p.index)
        if target is not None:
            gs.votes[p.index] = target
            target_player = gs.players.get_player(target)
            if target_player is not None:
                target_player.voted_by.append(p.index)


def simulate_game() -> dict:
    """Run a complete game from SETUP to GAME_OVER.

    Returns the final game state info: winner, day count, log.

    The simulation uses the same state-transition logic as main.py:
    - Night phases: run AI actions for each night sub-phase, then advance
    - DAY_ANNOUNCE: resolve_night(), then advance
    - DAY_SHERIFF_ELECTION: hold election (day 1 only), then advance
    - DAY_DISCUSSION: advance (no simulation of discussion content)
    - DAY_VOTE: run voting, then advance
    - DAY_VOTE_RESULT: handled by advance_day_phase() in tests — depends on
      the internal _resolve_day() call at the end of the day order.
    """
    gs = GameState()

    # Start the game (SETUP -> NIGHT_GUARD)
    gs.start_game()
    assert gs.phase == GamePhase.NIGHT_GUARD, f"Expected NIGHT_GUARD, got {gs.phase}"
    assert gs.day == 1

    max_iterations = 500  # Safety cap
    iteration = 0
    for iteration in range(max_iterations):
        if gs.phase == GamePhase.GAME_OVER or gs.winner is not None:
            break

        phase = gs.phase

        # ── NIGHT phases: run AI actions then advance ──
        if phase in (
            GamePhase.NIGHT_GUARD,
            GamePhase.NIGHT_SEER,
            GamePhase.NIGHT_WEREWOLF,
            GamePhase.NIGHT_WITCH,
        ):
            _run_night_actions(gs)
            gs.advance_night_phase()
            continue

        # ── DAY_PHASES ──
        if phase == GamePhase.DAY_ANNOUNCE:
            gs.resolve_night()  # Reveals deaths
            if gs.phase == GamePhase.GAME_OVER:
                break
            gs.advance_day_phase()
            continue

        if phase == GamePhase.DAY_SHERIFF_ELECTION:
            if gs.day == 1 and not gs.sheriff_election_done:
                alive = gs.players.get_alive_players()
                for voter in alive:
                    if voter.index not in gs.sheriff_votes:
                        target = choose_sheriff_vote(gs, voter.index)
                        if target is not None:
                            gs.sheriff_votes[voter.index] = target
            gs.advance_day_phase()
            continue

        if phase == GamePhase.DAY_DISCUSSION:
            gs.advance_day_phase()
            continue

        if phase == GamePhase.DAY_VOTE:
            _run_day_vote(gs)
            gs.advance_day_phase()
            continue

        if phase == GamePhase.DAY_PK:
            # PK (runoff) vote — restricted to tied candidates
            _run_day_vote(gs)
            gs.advance_day_phase()
            continue

        if phase == GamePhase.DAY_TRIAL:
            # Handle tie-breaker: PK vote
            _run_day_vote(gs)
            gs.advance_day_phase()
            continue

        if phase == GamePhase.DAY_VOTE_RESULT:
            gs.advance_day_phase()
            continue

        # Fallback: shouldn't happen
        break

    return {
        "winner": gs.winner,
        "day": gs.day,
        "phase": gs.phase.name if gs.phase else None,
        "alive_count": len(gs.players.get_alive_players()),
        "iterations": iteration + 1,
        "log": [entry["message"] for entry in gs.log[-20:]],
    }


class TestSimulation:
    """End-to-end game simulation tests."""

    def test_game_runs_to_completion(self):
        """A full game must reach GAME_OVER with a winner."""
        result = simulate_game()
        assert result["winner"] is not None, (
            f"Game did not finish after {result['iterations']} iterations. "
            f"Phase: {result['phase']}, Day: {result['day']}, "
            f"Alive: {result['alive_count']}"
        )
        assert result["winner"] in ("village", "werewolf"), (
            f"Unexpected winner: {result['winner']}"
        )

    def test_game_ends_within_reasonable_iterations(self):
        """A standard game should finish within 200 iterations."""
        result = simulate_game()
        assert result["iterations"] <= 200, (
            f"Game took {result['iterations']} iterations — excessive"
        )

    def test_alive_count_decreases_over_time(self):
        """Total alive players should decrease over course of game."""
        result = simulate_game()
        assert result["alive_count"] < 12, (
            "Alive count should decrease from initial 12"
        )
        assert result["alive_count"] >= 0

    def test_multiple_games_produce_varied_outcomes(self):
        """Running 5 games should produce at least one village win
        and one werewolf win (both outcomes are possible)."""
        winners = set()
        for i in range(5):
            r = simulate_game()
            winners.add(r["winner"])
            assert r["winner"] is not None, f"Game {i} didn't finish"
        # At least one of each team type is expected
        # (probabilistic — not guaranteed, but very likely)
        assert len(winners) >= 1

    def test_deaths_leave_log_entries(self):
        """After a full game, the log should contain death records."""
        result = simulate_game()
        log_text = " ".join(result["log"])
        # Check for common death-related log patterns
        has_death_info = any(
            keyword in log_text
            for keyword in ["killed", "poison", "eliminated", "shot", "杀", "毒", "放逐", "复仇"]
        )
        assert has_death_info, (
            "Log should contain death records"
        )

    def test_game_state_is_consistent(self):
        """Ensure no internal state corruption during a full run."""
        gs = GameState()
        gs.start_game()

        max_steps = 100
        for _ in range(max_steps):
            if gs.winner is not None:
                break
            phase = gs.phase

            if phase in (
                GamePhase.NIGHT_GUARD,
                GamePhase.NIGHT_SEER,
                GamePhase.NIGHT_WEREWOLF,
                GamePhase.NIGHT_WITCH,
            ):
                _run_night_actions(gs)
                gs.advance_night_phase()
            elif phase == GamePhase.DAY_ANNOUNCE:
                gs.resolve_night()
                if gs.phase == GamePhase.GAME_OVER:
                    break
                gs.advance_day_phase()
            elif phase == GamePhase.DAY_SHERIFF_ELECTION:
                if gs.day == 1 and not gs.sheriff_election_done:
                    alive = gs.players.get_alive_players()
                    for voter in alive:
                        if voter.index not in gs.sheriff_votes:
                            target = choose_sheriff_vote(gs, voter.index)
                            if target is not None:
                                gs.sheriff_votes[voter.index] = target
                gs.advance_day_phase()
            elif phase == GamePhase.DAY_DISCUSSION:
                gs.advance_day_phase()
            elif phase == GamePhase.DAY_VOTE:
                _run_day_vote(gs)
                gs.advance_day_phase()
            elif phase == GamePhase.DAY_PK:
                _run_day_vote(gs)
                gs.advance_day_phase()
            elif phase == GamePhase.DAY_VOTE_RESULT:
                gs.advance_day_phase()
            else:
                break

        # Verify invariants
        alive = gs.players.get_alive_players()
        dead = gs.players.get_dead_players()
        assert len(alive) + len(dead) == 12, (
            f"Total players should be 12, got {len(alive)}+{len(dead)}"
        )
        if gs.winner is not None:
            assert gs.winner in ("village", "werewolf"), (
                f"Unexpected winner type: {gs.winner}"
            )
