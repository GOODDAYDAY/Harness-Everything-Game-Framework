#!/usr/bin/env python3
"""Pixel Werewolf — Python/pygame entry point."""

from __future__ import annotations

from typing import Optional

import pygame

from scripts.game_engine import GameEngine
from game.game_state import GameState
from game.phases import GamePhase
from game.renderer import VillageRenderer
from game.roles import Role

# NPC AI
from game.npc_ai import choose_night_action, choose_vote_target, decide_witch_action

# Pixel font size for UI overlay
FONT_SIZE_TITLE = 28
FONT_SIZE_PLAYER = 20
FONT_SIZE_LOG = 16

# UI overlay positioning
SIDEBAR_X = 1900
SIDEBAR_Y = 20
LIST_START = 80
LIST_SPACING = 28
LOG_START_Y = 1100
LOG_SPACING = 20


class WerewolfGame:
    def __init__(self):
        self.engine = GameEngine(
            width=2560, height=1440,
            title="Pixel Werewolf",
            fps=60, pixel_art=True,
        )
        self.game_state = GameState()
        self.renderer = VillageRenderer()
        self._font_title: Optional[pygame.font.Font] = None
        self._font_player: Optional[pygame.font.Font] = None
        self._font_log: Optional[pygame.font.Font] = None
        # Phase timing (seconds to wait in each phase before auto-advancing)
        self._phase_timer: float = 0.0
        self._phase_duration: float = 1.5  # seconds per phase
        self._game_started: bool = False

    def init(self):
        if not self.engine.init():
            return False
        self.engine.on_render = self.render
        self.engine.on_update = self.update
        # Register state provider for TCP bridge
        self.engine.get_state = lambda: self.game_state.to_dict()

        # Load pixel font — fall back to default if unavailable
        try:
            self._font_title = pygame.font.Font("assets/pixel_font.ttf", FONT_SIZE_TITLE)
            self._font_player = pygame.font.Font("assets/pixel_font.ttf", FONT_SIZE_PLAYER)
            self._font_log = pygame.font.Font("assets/pixel_font.ttf", FONT_SIZE_LOG)
        except (FileNotFoundError, pygame.error):
            self._font_title = pygame.font.Font(None, FONT_SIZE_TITLE + 8)
            self._font_player = pygame.font.Font(None, FONT_SIZE_PLAYER + 6)
            self._font_log = pygame.font.Font(None, FONT_SIZE_LOG + 4)

        return True

    def update(self, dt: float):
        """Update game state — called every frame by GameEngine.

        Drives the game loop: starts the game, runs NPC decisions for each
        night and day phase, advances phases on a timer.
        """
        # --- SETUP → start game on first frame ---
        if self.game_state.phase == GamePhase.SETUP and not self._game_started:
            self._game_started = True
            self._phase_timer = 0.0
            return

        if self.game_state.phase == GamePhase.SETUP:
            self._phase_timer += dt
            if self._phase_timer >= 0.5:
                self.game_state.start_game()
                self._phase_timer = 0.0
            return

        # --- GAME OVER — stop advancing ---
        if self.game_state.phase == GamePhase.GAME_OVER:
            return

        # --- Accumulate phase timer ---
        self._phase_timer += dt
        if self._phase_timer < self._phase_duration:
            return
        self._phase_timer = 0.0

        phase = self.game_state.phase

        # ── NIGHT PHASES ─────────────────────────────────────────────
        if phase == GamePhase.NIGHT_GUARD:
            guard_players = [p for p in self.game_state.players.players if p.role == Role.GUARD]
            if guard_players:
                guard = guard_players[0]
                if guard.alive:
                    target = choose_night_action(self.game_state, guard.index, phase)
                    if target is not None:
                        self.game_state.guard_target = target
                        self.game_state.players.get_player(target).protected = True
                        self.game_state._log("guard", f"Guard protected Player {target}.")
            self.game_state.advance_night_phase()

        elif phase == GamePhase.NIGHT_SEER:
            seer_players = [p for p in self.game_state.players.players if p.role == Role.SEER]
            if seer_players:
                seer = seer_players[0]
                if seer.alive:
                    target = choose_night_action(self.game_state, seer.index, phase)
                    if target is not None:
                        self.game_state.seer_target = target
                        target_player = self.game_state.players.get_player(target)
                        self.game_state._log(
                            "seer",
                            f"Seer investigated Player {target} — they are a {target_player.role.name_zh}."
                        )
            self.game_state.advance_night_phase()

        elif phase == GamePhase.NIGHT_WEREWOLF:
            werewolf_players = self.game_state.players.get_werewolf_players()
            alive_ww = [p for p in werewolf_players if p.alive]
            if alive_ww:
                target = choose_night_action(self.game_state, alive_ww[0].index, phase)
                if target is not None:
                    self.game_state.werewolf_target = target
                    self.game_state._log("werewolf", f"Werewolves target Player {target}.")
            self.game_state.advance_night_phase()

        elif phase == GamePhase.NIGHT_WITCH:
            should_save, should_poison, poison_target = decide_witch_action(self.game_state)
            if should_save and self.game_state.last_night_victim is not None:
                self.game_state.witch_heal_target = self.game_state.last_night_victim
                self.game_state._log("witch", f"Witch saved Player {self.game_state.last_night_victim}.")
            if should_poison and poison_target is not None:
                self.game_state.witch_poison_target = poison_target
                # Mark the player as poisoned (will be resolved in resolve_night)
                poisoned_player = self.game_state.players.get_player(poison_target)
                if poisoned_player:
                    poisoned_player.poisoned = True
                self.game_state._log("witch", f"Witch poisoned Player {poison_target}.")
            self.game_state.advance_night_phase()

        # ── DAY PHASES ───────────────────────────────────────────────
        elif phase == GamePhase.DAY_ANNOUNCE:
            if self.game_state.werewolf_target is not None:
                night_result = self.game_state.resolve_night()
                victim = night_result.get("victim")
                saved = night_result.get("saved", False)
                poisoned = night_result.get("poisoned")
                if victim is not None and not saved:
                    victim_player = self.game_state.players.get_player(victim)
                    self.game_state._log(
                        "death",
                        f"Player {victim} ({victim_player.name}) was killed during the night!"
                        f" They were a {victim_player.role.name_zh}."
                    )
                if saved:
                    self.game_state._log("saved", "Someone was saved by the witch's antidote!")
                if poisoned is not None:
                    poisoned_player = self.game_state.players.get_player(poisoned)
                    self.game_state._log(
                        "poison",
                        f"Player {poisoned} ({poisoned_player.name}) was poisoned by the witch!"
                        f" They were a {poisoned_player.role.name_zh}."
                    )
                # Check game over after night kills
                if self.game_state.players.is_game_over():
                    self.game_state.winner = self.game_state.players.get_winning_team()
                    self.game_state.phase = GamePhase.GAME_OVER
                    self.game_state._log("game_over", f"{self.game_state.winner} team wins!")
                    return
            self.game_state.advance_day_phase()

        elif phase == GamePhase.DAY_DISCUSSION:
            # Discussion phase — placeholder, advances after timer
            self.game_state.advance_day_phase()

        elif phase == GamePhase.DAY_VOTE:
            alive_players = self.game_state.players.get_alive_players()
            for player in alive_players:
                target = choose_vote_target(self.game_state, player.index)
                if target is not None:
                    self.game_state.votes[player.index] = target
                    target_player = self.game_state.players.get_player(target)
                    if target_player is not None:
                        target_player.voted_by.append(player.index)
            self.game_state.advance_day_phase()

        elif phase == GamePhase.DAY_RESULT:
            # Day result already handled by _resolve_day inside advance_day_phase.
            # It may set phase to GAME_OVER — don't duplicate the log.
            self.game_state.advance_day_phase()

    @property
    def _is_night(self) -> bool:
        """Whether the current phase is a night phase (darker visuals)."""
        return self.game_state.phase.is_night or self.game_state.phase == GamePhase.SETUP

    def render(self, screen: pygame.Surface):
        state = self.game_state
        is_night = self._is_night

        # ── 0. Update player positions for renderer ──
        self.renderer.set_players(state.players.players)

        # ── 1. Render village background + player characters ──
        self.renderer.render(screen, is_night)

        # ── 2. Semi-transparent overlay for UI readability ──
        overlay = pygame.Surface((640, 1440), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160) if is_night else (0, 0, 0, 100))
        screen.blit(overlay, (SIDEBAR_X - 20, 0))

        # ── 3. Title / phase info ──
        title_font = self._font_title
        player_font = self._font_player
        log_font = self._font_log

        title_text = title_font.render(
            "🎮 Pixel Werewolf", True, (255, 220, 150)
        )
        screen.blit(title_text, (SIDEBAR_X, SIDEBAR_Y))

        phase_label = title_font.render(
            f"{state.phase.display_name}", True, (200, 200, 255) if is_night else (255, 255, 200)
        )
        screen.blit(phase_label, (SIDEBAR_X, SIDEBAR_Y + 36))

        day_label = player_font.render(
            f"Day {state.day}", True, (200, 200, 200)
        )
        screen.blit(day_label, (SIDEBAR_X, SIDEBAR_Y + 68))

        # ── 4. Player list (sidebar) ──
        y = SIDEBAR_Y + LIST_START
        for p in state.players.players:
            if p.alive:
                color = (220, 220, 220)
                prefix = "🟢"
                role_name_label = p.role.name_zh if state.phase.is_day else "???"
            else:
                color = (100, 100, 100)
                prefix = "💀"
                role_name_label = p.role.name_zh

            sheriff = "★" if p.is_sheriff else ""
            line = player_font.render(
                f"{prefix} {p.name} {sheriff}[{role_name_label}]", True, color
            )
            screen.blit(line, (SIDEBAR_X, y))
            y += LIST_SPACING

        # ── 5. Game log ──
        y = LOG_START_Y
        log_label = log_font.render("-- Game Log --", True, (160, 160, 160))
        screen.blit(log_label, (SIDEBAR_X, y))
        y += LOG_SPACING

        for entry in state.log[-8:]:
            text = log_font.render(entry["message"], True, (160, 160, 160))
            screen.blit(text, (SIDEBAR_X, y))
            y += LOG_SPACING

        # ── 6. Night overlay darkness ──
        if is_night:
            # Darken edges for atmosphere (vignette effect — pixel style, no blur)
            vignette = pygame.Surface((2560, 1440), pygame.SRCALPHA)
            for i in range(8):
                alpha = 6 - i
                if alpha < 0:
                    alpha = 0
                pygame.draw.rect(
                    vignette, (0, 0, 20, alpha * 2),
                    (i * 4, i * 4, 2560 - i * 8, 1440 - i * 8),
                    4,
                )
            screen.blit(vignette, (0, 0))

    def run(self):
        self.engine.run()


if __name__ == "__main__":
    game = WerewolfGame()
    if game.init():
        game.run()
