#!/usr/bin/env python3
"""Pixel Werewolf — Python/pygame entry point."""

from __future__ import annotations

from typing import Optional

import pygame

from scripts.game_engine import GameEngine
from game.game_state import GameState
from game.phases import GamePhase
from game.renderer import VillageRenderer

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
        pass

    @property
    def _is_night(self) -> bool:
        """Whether the current phase is a night phase (darker visuals)."""
        return self.game_state.phase.is_night or self.game_state.phase == GamePhase.SETUP

    def render(self, screen: pygame.Surface):
        state = self.game_state
        is_night = self._is_night

        # ── 1. Render village background ──
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
