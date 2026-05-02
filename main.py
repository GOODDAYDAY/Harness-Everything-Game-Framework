#!/usr/bin/env python3
"""Pixel Werewolf — Python/pygame entry point."""

from scripts.game_engine import GameEngine
import pygame


class WerewolfGame:
    def __init__(self):
        self.engine = GameEngine(
            width=2560, height=1440,
            title="Pixel Werewolf",
            fps=60, pixel_art=True,
        )
        self.phase = "STARTUP"
        self.day = 1

    def init(self):
        if not self.engine.init():
            return False
        self.engine.on_render = self.render
        self.engine.on_update = self.update
        return True

    def update(self, dt: float):
        pass

    def render(self, screen: pygame.Surface):
        screen.fill((25, 25, 40))
        font = pygame.font.Font(None, 36)
        text = font.render(
            f"Pixel Werewolf — {self.phase} Day {self.day}",
            True, (255, 255, 255),
        )
        screen.blit(text, (50, 50))

    def run(self):
        self.engine.run()


if __name__ == "__main__":
    game = WerewolfGame()
    if game.init():
        game.run()
