#!/usr/bin/env python3
"""Pixel-art player character sprites for Pixel Werewolf.

Generates small 16x32 pixel character icons with distinct
colour schemes for each player. Dead players are shown as
tombstones with ghostly appearance.
"""

from __future__ import annotations

import pygame

# Sprite dimensions
CHAR_W = 16
CHAR_H = 32

# 12 distinct player colour schemes (body, hair, accent)
PLAYER_COLORS: list[tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]] = [
    # (body colour, hair colour, accent colour)
    ((200, 80, 80), (60, 40, 30), (240, 200, 160)),  # 0: Red shirt, brown hair
    ((80, 140, 200), (80, 60, 40), (230, 190, 150)),  # 1: Blue shirt, dark brown hair
    ((100, 200, 100), (40, 30, 20), (235, 195, 155)),  # 2: Green shirt, black hair
    ((220, 180, 60), (70, 50, 35), (245, 205, 165)),  # 3: Yellow shirt, brown hair
    ((180, 100, 200), (50, 35, 25), (230, 190, 150)),  # 4: Purple shirt, dark hair
    ((80, 200, 180), (90, 70, 50), (240, 200, 160)),  # 5: Teal shirt, light brown hair
    ((220, 140, 60), (60, 40, 30), (235, 195, 155)),  # 6: Orange shirt, brown hair
    ((200, 160, 220), (100, 80, 60), (245, 205, 165)),  # 7: Lavender shirt, grey-brown hair
    ((140, 200, 220), (40, 30, 20), (230, 190, 150)),  # 8: Light blue shirt, black hair
    ((220, 120, 140), (80, 60, 40), (240, 200, 160)),  # 9: Pink shirt, dark brown hair
    ((160, 180, 80), (60, 45, 30), (235, 195, 155)),  # 10: Olive shirt, brown hair
    ((140, 140, 200), (90, 70, 50), (230, 190, 150)),  # 11: Periwinkle, light brown hair
]


def _generate_alive_sprite(body_color, hair_color, skin_color, player_idx: int) -> pygame.Surface:
    """Generate a 16x32 pixel-art character sprite."""
    surf = pygame.Surface((CHAR_W, CHAR_H), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))  # transparent

    # Hair (top)
    for x in range(3, 13):
        for y in range(0, 8):
            if x in (3, 12) and y < 5:
                continue
            if y == 0 and x not in range(5, 11):
                continue
            surf.set_at((x, y), hair_color)

    # Face/skin
    for x in range(4, 12):
        for y in range(7, 12):
            surf.set_at((x, y), skin_color)

    # Eyes
    eye_col = (40, 30, 20)
    surf.set_at((6, 9), eye_col)
    surf.set_at((9, 9), eye_col)

    # Body (shirt)
    for x in range(3, 13):
        for y in range(12, 22):
            surf.set_at((x, y), body_color)

    # Arms (skin colour, small)
    for x in range(1, 3):
        for y in range(12, 18):
            surf.set_at((x, y), skin_color)
    for x in range(13, 15):
        for y in range(12, 18):
            surf.set_at((x, y), skin_color)

    # Legs
    leg_color = (50, 40, 35)
    for x in range(4, 7):
        for y in range(22, 30):
            surf.set_at((x, y), leg_color)
    for x in range(9, 12):
        for y in range(22, 30):
            surf.set_at((x, y), leg_color)

    # Shoes
    shoe_color = (30, 25, 20)
    for x in range(3, 7):
        surf.set_at((x, 30), shoe_color)
        surf.set_at((x, 31), shoe_color)
    for x in range(9, 13):
        surf.set_at((x, 30), shoe_color)
        surf.set_at((x, 31), shoe_color)

    return surf


def _generate_dead_sprite(player_idx: int) -> pygame.Surface:
    """Generate a 16x32 tombstone/ghost sprite for dead players."""
    surf = pygame.Surface((CHAR_W, CHAR_H), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))

    # Ghostly figure (semi-transparent white/grey)
    ghost_col = (200, 200, 210, 160)
    for x in range(3, 13):
        for y in range(4, 22):
            if x in (3, 12) and y < 6:
                continue
            surf.set_at((x, y), ghost_col)

    # Eyes (dark hollows)
    surf.set_at((6, 10), (80, 80, 90))
    surf.set_at((9, 10), (80, 80, 90))

    # Tombstone base
    stone_col = (140, 135, 130)
    for x in range(2, 14):
        for y in range(24, 32):
            surf.set_at((x, y), stone_col)

    # ✝ cross on tombstone
    cross_col = (180, 175, 170)
    for x in range(6, 10):
        surf.set_at((x, 26), cross_col)
        surf.set_at((x, 27), cross_col)
    for y in range(25, 30):
        surf.set_at((7, y), cross_col)
        surf.set_at((8, y), cross_col)

    return surf


# Sprite cache
_sprite_cache: dict[int, pygame.Surface] = {}  # index -> alive sprite
_dead_sprite_cache: dict[int, pygame.Surface] = {}  # index -> dead sprite


def get_character_sprite(player_idx: int, alive: bool) -> pygame.Surface:
    """Get a cached character sprite, generating if needed."""
    if alive:
        if player_idx not in _sprite_cache:
            body, hair, skin = PLAYER_COLORS[player_idx % len(PLAYER_COLORS)]
            _sprite_cache[player_idx] = _generate_alive_sprite(body, hair, skin, player_idx)
        return _sprite_cache[player_idx]
    else:
        if player_idx not in _dead_sprite_cache:
            _dead_sprite_cache[player_idx] = _generate_dead_sprite(player_idx)
        return _dead_sprite_cache[player_idx]


def invalidate_cache() -> None:
    """Clear all generated sprites."""
    _sprite_cache.clear()
    _dead_sprite_cache.clear()
