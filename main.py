#!/usr/bin/env python3
"""Pixel Werewolf — Python/pygame entry point.

This file should stay minimal. The WerewolfGame class lives in
game/game_loop.py.
"""

from __future__ import annotations

from game.game_loop import WerewolfGame


if __name__ == "__main__":
    game = WerewolfGame()
    if game.init():
        game.run()
