#!/usr/bin/env python3
"""Pixel Werewolf — Python/pygame entry point."""

from scripts.game_engine import GameEngine
from game.game_state import GameState
import pygame


class WerewolfGame:
    def __init__(self):
        self.engine = GameEngine(
            width=2560, height=1440,
            title="Pixel Werewolf",
            fps=60, pixel_art=True,
        )
        self.game_state = GameState()

    def init(self):
        if not self.engine.init():
            return False
        self.engine.on_render = self.render
        self.engine.on_update = self.update
        # Register state provider for TCP bridge
        self.engine.get_state = lambda: self.game_state.to_dict()
        return True

    def update(self, dt: float):
        pass

    def render(self, screen: pygame.Surface):
        screen.fill((25, 25, 40))
        font = pygame.font.Font(None, 36)
        state = self.game_state
        text = font.render(
            f"Pixel Werewolf — {state.phase.display_name} Day {state.day}",
            True, (255, 255, 255),
        )
        screen.blit(text, (50, 50))

        # Draw player list
        y = 100
        for p in state.players.players:
            color = (200, 200, 200) if p.alive else (80, 80, 80)
            role_name = p.role.name_zh if p.alive else "???"
            status = "Alive" if p.alive else "Dead"
            sheriff = " [Sheriff]" if p.is_sheriff else ""
            line = font.render(
                f"P{p.index}: {p.name} — {role_name} ({status}){sheriff}",
                True, color,
            )
            screen.blit(line, (50, y))
            y += 30

        # Draw log
        log_font = pygame.font.Font(None, 24)
        y = screen.get_height() - 250
        for entry in state.log[-8:]:
            text = log_font.render(entry["message"], True, (180, 180, 180))
            screen.blit(text, (50, y))
            y += 22

    def run(self):
        self.engine.run()


if __name__ == "__main__":
    game = WerewolfGame()
    if game.init():
        game.run()
