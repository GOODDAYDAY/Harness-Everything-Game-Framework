#!/usr/bin/env python3
"""Pixel-art village renderer for Pixel Werewolf.

Generates a 32x18 tile map (80px tiles -> 2560x1440 viewport)
with procedurally drawn pixel-art tiles. No external assets needed.
"""

from __future__ import annotations

from typing import Optional, Any

import pygame

from game.bitmap_font import render_text as _render_text
from game.player_sprites import CHAR_H, CHAR_W, get_character_sprite

# Constants
TILE_SIZE = 80
GRID_COLS = 32
GRID_ROWS = 18
VIEWPORT_W = 2560
VIEWPORT_H = 1440

# ── Palette ────────────────────────────────────────────────────────

class Palette:
    """Colour palette for the village scene.

    Each entry has a day variant and a night variant — night colours
    are darker, cooler, with warm light from windows.
    """
    sky: tuple[tuple[int, int, int], tuple[int, int, int]] = ((185, 215, 245), (12, 16, 42))
    sky_distant: tuple[tuple[int, int, int], tuple[int, int, int]] = ((155, 195, 225), (10, 14, 38))
    grass_light: tuple[tuple[int, int, int], tuple[int, int, int]] = ((150, 210, 90), (32, 62, 32))
    grass_dark: tuple[tuple[int, int, int], tuple[int, int, int]] = ((110, 180, 65), (22, 48, 22))
    path: tuple[tuple[int, int, int], tuple[int, int, int]] = ((190, 170, 130), (55, 48, 38))
    path_dark: tuple[tuple[int, int, int], tuple[int, int, int]] = ((160, 140, 100), (42, 38, 28))
    wood_light: tuple[tuple[int, int, int], tuple[int, int, int]] = ((180, 140, 70), (65, 48, 22))
    wood_dark: tuple[tuple[int, int, int], tuple[int, int, int]] = ((140, 100, 45), (48, 38, 16))
    roof_red: tuple[tuple[int, int, int], tuple[int, int, int]] = ((200, 80, 55), (75, 28, 18))
    roof_dark: tuple[tuple[int, int, int], tuple[int, int, int]] = ((150, 55, 38), (55, 22, 12))
    wall_cream: tuple[tuple[int, int, int], tuple[int, int, int]] = ((235, 215, 178), (85, 75, 55))
    wall_dark: tuple[tuple[int, int, int], tuple[int, int, int]] = ((205, 185, 148), (72, 62, 42))
    window_glow: tuple[int, int, int] = (255, 225, 140)  # warm golden glow
    window_dark: tuple[int, int, int] = (45, 38, 28)
    tree_trunk: tuple[tuple[int, int, int], tuple[int, int, int]] = ((105, 75, 42), (38, 28, 16))
    tree_canopy: tuple[tuple[int, int, int], tuple[int, int, int]] = ((75, 145, 42), (22, 52, 16))
    tree_canopy_light: tuple[tuple[int, int, int], tuple[int, int, int]] = ((105, 175, 65), (32, 62, 22))
    water: tuple[tuple[int, int, int], tuple[int, int, int]] = ((90, 145, 185), (18, 32, 62))
    water_light: tuple[tuple[int, int, int], tuple[int, int, int]] = ((130, 180, 210), (28, 48, 82))
    fence: tuple[tuple[int, int, int], tuple[int, int, int]] = ((170, 130, 65), (58, 42, 22))
    well: tuple[tuple[int, int, int], tuple[int, int, int]] = ((140, 128, 108), (48, 42, 38))
    flower: tuple[tuple[int, int, int], tuple[int, int, int]] = ((250, 110, 130), (105, 35, 42))
    stone: tuple[tuple[int, int, int], tuple[int, int, int]] = ((168, 158, 148), (58, 52, 48))

    @classmethod
    def color(cls, attr: str, night: bool) -> tuple[int, int, int]:
        """Get a palette colour by attribute name.

        If the palette entry is a (day, night) tuple, picks based on `night`.
        If it's a single colour, returns as-is.
        """
        val = getattr(cls, attr)
        if isinstance(val[0], tuple):  # (day_colour, night_colour) pair
            return val[1] if night else val[0]
        return val  # single colour (e.g. window_glow)


# ── Tile map layout ────────────────────────────────────────────────

# Tile types for the village scene
T_GRASS = 0
T_PATH = 1
T_PATH_DARK = 2
T_HOUSE_WALL = 3
T_HOUSE_ROOF = 4
T_DOOR = 5
T_WINDOW = 6
T_TREE_TRUNK = 7
T_TREE_CANOPY = 8
T_WATER = 9
T_WELL = 10
T_FENCE = 11
T_FLOWER = 12
T_STONE = 13
T_SKY = 14
T_SKY_TREE = 15
T_DOOR_CLOSED = 16
T_MEETING = 17  # Town square meeting platform
T_LANTERN = 18  # Lamp post
T_SIGN = 19     # Village signpost


def _build_village_map() -> list[list[int]]:
    """Return a 2D grid (rows x cols) of tile type IDs defining the village."""
    grid: list[list[int]] = [[T_GRASS] * GRID_COLS for _ in range(GRID_ROWS)]

    # Row 0-1: Sky with distant trees
    for r in range(2):
        for c in range(GRID_COLS):
            grid[r][c] = T_SKY
    # Some distant tree silhouettes in sky
    sky_tree_cols = {3, 7, 11, 15, 19, 23, 27}
    for c in sky_tree_cols:
        grid[1][c] = T_SKY_TREE
        if c + 1 < GRID_COLS:
            grid[1][c + 1] = T_SKY_TREE

    # Row 2: Tree line backdrop
    for c in range(GRID_COLS):
        if c % 4 < 2:
            grid[2][c] = T_TREE_CANOPY

    # ── Village area (rows 3-14) ──

    # Main path (vertical, center)
    for r in range(3, 16):
        grid[r][14] = T_PATH
        grid[r][15] = T_PATH
        grid[r][16] = T_PATH
        grid[r][17] = T_PATH

    # Horizontal paths
    for c in range(6, 26):
        grid[7][c] = T_PATH
        grid[12][c] = T_PATH

    # Path intersections
    grid[7][14] = T_PATH_DARK
    grid[7][15] = T_PATH_DARK
    grid[7][16] = T_PATH_DARK
    grid[7][17] = T_PATH_DARK
    grid[12][14] = T_PATH_DARK
    grid[12][15] = T_PATH_DARK
    grid[12][16] = T_PATH_DARK
    grid[12][17] = T_PATH_DARK

    # ── Houses ──

    # House 1: Top-left (rows 3-6, cols 2-6)
    _place_house(grid, 3, 2)
    _place_house(grid, 3, 20)
    _place_house(grid, 8, 3)
    _place_house(grid, 8, 21)
    _place_house(grid, 13, 8)
    _place_house(grid, 13, 18)
    _place_house(grid, 4, 9)
    _place_house(grid, 4, 19)

    # Pond (bottom left)
    for r in range(14, 17):
        for c in range(1, 5):
            grid[r][c] = T_WATER
    grid[14][5] = T_WATER
    grid[15][5] = T_WATER
    grid[16][5] = T_WATER

    # Well (center right)
    grid[9][20] = T_WELL
    grid[9][21] = T_WELL

    # Fence (bottom)
    for c in range(8, 24):
        grid[16][c] = T_FENCE
    grid[16][8] = T_FENCE
    grid[16][23] = T_FENCE

    # Flowers near houses
    grid[7][5] = T_FLOWER
    grid[7][6] = T_FLOWER
    grid[7][22] = T_FLOWER
    grid[7][23] = T_FLOWER
    grid[12][2] = T_FLOWER
    grid[12][3] = T_FLOWER
    grid[12][26] = T_FLOWER
    grid[12][27] = T_FLOWER

    # Lantern posts along the main path
    grid[5][14] = T_LANTERN
    grid[5][17] = T_LANTERN
    grid[9][14] = T_LANTERN
    grid[9][17] = T_LANTERN
    grid[12][14] = T_LANTERN
    grid[12][17] = T_LANTERN

    # Village signpost at entrance
    grid[4][6] = T_SIGN
    grid[13][6] = T_FLOWER
    grid[13][22] = T_FLOWER

    # Stones
    grid[10][5] = T_STONE
    grid[10][6] = T_STONE
    grid[11][22] = T_STONE
    grid[11][23] = T_STONE

    # Town square meeting platform (decorative stone circle at path intersection)
    grid[10][15] = T_MEETING
    grid[10][16] = T_MEETING
    grid[11][15] = T_MEETING
    grid[11][16] = T_MEETING

    return grid


def _place_house(grid: list[list[int]], top_row: int, left_col: int) -> None:
    """Place a 4x5 house (4 rows, 5 cols) on the grid."""
    roof_row = top_row
    wall_row1 = top_row + 1
    wall_row2 = top_row + 2
    wall_row3 = top_row + 3

    for c in range(left_col, left_col + 5):
        # Roof
        if c == left_col or c == left_col + 4:
            grid[roof_row][c] = T_HOUSE_ROOF
        else:
            grid[roof_row][c] = T_HOUSE_ROOF
        # Walls
        for r in range(wall_row1, wall_row3 + 1):
            if c == left_col or c == left_col + 4:
                grid[r][c] = T_HOUSE_WALL
            else:
                grid[r][c] = T_HOUSE_WALL

    # Door at bottom center
    door_col = left_col + 2
    grid[wall_row3][door_col] = T_DOOR

    # Windows
    grid[wall_row1][left_col + 1] = T_WINDOW
    grid[wall_row1][left_col + 3] = T_WINDOW
    grid[wall_row2][left_col + 1] = T_WINDOW
    grid[wall_row2][left_col + 3] = T_WINDOW


# ── Pre-rendered tile cache ─────────────────────────────────────────

_tile_cache: dict[tuple[int, bool], pygame.Surface] = {}


def _draw_tile(tile_type: int, night: bool) -> pygame.Surface:
    """Draw a single 80x80 pixel-art tile."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    P = Palette  # shorthand

    def c(attr: str) -> tuple[int, int, int]:
        return P.color(attr, night)

    if tile_type == T_GRASS:
        surf.fill(c("grass_light"))
        # Rich grass texture with variation
        import random as _r
        # Use a fixed deterministic seed based on tile type and day/night
        # Avoid hash() which is randomized per-Python-run
        _r.seed(tile_type * 17 + (7 if night else 31))
        for x in range(0, TILE_SIZE, 4):
            for y in range(0, TILE_SIZE, 4):
                if (x + y) % 8 == 0:
                    surf.set_at((x + 1, y + 1), c("grass_dark"))
                    surf.set_at((x + 3, y + 1), c("grass_dark"))
        # Occasional tiny flowers in grass
        for _ in range(3):
            fx = _r.randint(8, TILE_SIZE - 8)
            fy = _r.randint(8, TILE_SIZE - 8)
            flower_colors = [(255, 225, 130), (250, 210, 245), (210, 230, 255), (255, 215, 170)]
            fc = flower_colors[_r.randint(0, 3)]
            surf.set_at((fx, fy), fc)
            surf.set_at((fx + 1, fy), fc)
            surf.set_at((fx, fy + 1), fc)

    elif tile_type == T_PATH:
        surf.fill(c("path"))
        # Dirt texture with more variation
        for _ in range(30):
            px = (_ * 37 + 13) % TILE_SIZE
            py = (_ * 23 + 7) % TILE_SIZE
            surf.set_at((px, py), c("path_dark"))
            surf.set_at((px + 1, py), c("path_dark"))
        # Small stones / gravel
        for _ in range(5):
            sx = (_ * 19 + 31) % TILE_SIZE
            sy = (_ * 41 + 17) % TILE_SIZE
            surf.set_at((sx, sy), (160, 150, 130))
            surf.set_at((sx, sy + 1), (150, 140, 120))

    elif tile_type == T_PATH_DARK:
        surf.fill(c("path_dark"))
        for _ in range(20):
            px = (_ * 31 + 11) % TILE_SIZE
            py = (_ * 17 + 5) % TILE_SIZE
            surf.set_at((px, py), c("path"))
            surf.set_at((px + 1, py), c("path"))

    elif tile_type == T_HOUSE_WALL:
        surf.fill(c("wall_cream"))
        # Brick lines
        for y in range(0, TILE_SIZE, 16):
            pygame.draw.line(surf, c("wall_dark"), (0, y), (TILE_SIZE, y), 1)
        for x in range(0, TILE_SIZE, 20):
            pygame.draw.line(surf, c("wall_dark"), (x, 0), (x, TILE_SIZE), 1)

    elif tile_type == T_HOUSE_ROOF:
        surf.fill(c("roof_red"))
        # Roof tiles pattern
        for y in range(0, TILE_SIZE, 12):
            offset = (y // 12) % 2 * 8
            for x in range(offset, TILE_SIZE, 16):
                pygame.draw.rect(surf, c("roof_dark"), (x, y, 14, 10))

    elif tile_type == T_DOOR:
        surf.fill(c("wood_dark"))
        # Door frame
        pygame.draw.rect(surf, c("wood_light"), (0, 0, TILE_SIZE, TILE_SIZE), 3)
        # Door handle
        color = (255, 200, 50) if not night else (200, 150, 30)
        surf.set_at((TILE_SIZE - 15, TILE_SIZE // 2), color)
        surf.set_at((TILE_SIZE - 15, TILE_SIZE // 2 + 1), color)

    elif tile_type == T_DOOR_CLOSED:
        surf.fill(c("wood_dark"))
        pygame.draw.rect(surf, c("wood_light"), (0, 0, TILE_SIZE, TILE_SIZE), 3)

    elif tile_type == T_WINDOW:
        surf.fill(c("wall_cream"))
        # Window frame
        pygame.draw.rect(surf, c("wood_dark"), (15, 15, 50, 50), 4)
        # Cross
        pygame.draw.line(surf, c("wood_dark"), (40, 15), (40, 65), 3)
        pygame.draw.line(surf, c("wood_dark"), (15, 40), (65, 40), 3)
        # Glow or dark
        if night:
            # Warm glow from inside
            inner = pygame.Surface((42, 42))
            inner.fill(c("window_glow"))
            surf.blit(inner, (19, 19))
            # Cross on top
            pygame.draw.line(surf, c("wood_dark"), (40, 19), (40, 61), 3)
            pygame.draw.line(surf, c("wood_dark"), (19, 40), (61, 40), 3)
        else:
            # Light blue window panes
            pane = pygame.Surface((20, 20))
            pane.fill(c("sky"))
            surf.blit(pane, (19, 19))
            surf.blit(pane, (41, 19))
            surf.blit(pane, (19, 41))
            surf.blit(pane, (41, 41))
            # Cross on top
            pygame.draw.line(surf, c("wood_dark"), (40, 19), (40, 61), 3)
            pygame.draw.line(surf, c("wood_dark"), (19, 40), (61, 40), 3)

    elif tile_type == T_TREE_TRUNK:
        surf.fill(c("grass_light"))
        # Trunk
        pygame.draw.rect(surf, c("tree_trunk"), (30, 20, 20, 60))
        # Texture
        for _ in range(5):
            px = 30 + (_ * 7) % 16
            py = 25 + (_ * 13) % 50
            surf.set_at((px, py), c("tree_canopy"))

    elif tile_type == T_TREE_CANOPY:
        surf.fill(c("sky"))
        # Round canopy
        for dx in range(-35, 40, 4):
            for dy in range(-30, 35, 4):
                if dx * dx + dy * dy < 1300:
                    cx, cy = TILE_SIZE // 2 + dx, TILE_SIZE // 2 + dy
                    if 0 <= cx < TILE_SIZE and 0 <= cy < TILE_SIZE:
                        color = c("tree_canopy_light") if (dx + dy) % 8 == 0 else c("tree_canopy")
                        surf.set_at((cx, cy), color)
                        surf.set_at((cx + 1, cy), color)

    elif tile_type == T_SKY:
        surf.fill(c("sky"))
        # Some clouds during day
        if not night:
            for cloud_x in range(10, TILE_SIZE, 30):
                for dy in range(0, 12, 4):
                    for dx in range(0, 20, 4):
                        cx, cy = cloud_x + dx, 20 + dy
                        if cx < TILE_SIZE:
                            surf.set_at((cx, cy), (220, 230, 245))
                            surf.set_at((cx + 1, cy), (220, 230, 245))
        else:
            # Stars
            for i in range(12):
                sx = (i * 47 + 13) % TILE_SIZE
                sy = (i * 31 + 7) % TILE_SIZE
                brightness = 180 + (i * 13) % 75
                b = min(brightness + 20, 255)
                surf.set_at((sx, sy), (brightness, brightness, b))

    elif tile_type == T_SKY_TREE:
        surf.fill(c("sky"))
        # Distant tree silhouette
        for x in range(0, TILE_SIZE, 4):
            for y in range(TILE_SIZE - 20, TILE_SIZE, 4):
                dx = x - TILE_SIZE // 2
                h = 30 - abs(dx) // 4
                if y > TILE_SIZE - h:
                    surf.set_at((x, y), c("tree_canopy"))
                    surf.set_at((x + 1, y), c("tree_canopy"))

    elif tile_type == T_WATER:
        surf.fill(c("water"))
        # Ripple highlights
        for x in range(0, TILE_SIZE, 8):
            for y in range(4, TILE_SIZE, 12):
                if (x + y) % 16 == 0:
                    surf.set_at((x, y), c("water_light"))
                    surf.set_at((x + 1, y), c("water_light"))

    elif tile_type == T_WELL:
        surf.fill(c("grass_light"))
        # Stone well
        pygame.draw.circle(surf, c("stone"), (40, 45), 25)
        pygame.draw.circle(surf, c("grass_dark"), (40, 45), 15)
        # Stone texture
        for angle in range(0, 360, 45):
            import math
            sx = 40 + int(20 * math.cos(math.radians(angle)))
            sy = 45 + int(20 * math.sin(math.radians(angle)))
            surf.set_at((sx, sy), c("well"))
        # Roof post
        pygame.draw.rect(surf, c("wood_dark"), (35, 5, 10, 10))
        # Roof
        pygame.draw.rect(surf, c("roof_red"), (20, 0, 40, 8))

    elif tile_type == T_FENCE:
        surf.fill(c("grass_light"))
        # Horizontal bar
        pygame.draw.rect(surf, c("fence"), (0, 25, TILE_SIZE, 6))
        pygame.draw.rect(surf, c("fence"), (0, 50, TILE_SIZE, 6))
        # Vertical posts
        for px in range(8, TILE_SIZE, 20):
            pygame.draw.rect(surf, c("wood_dark"), (px, 15, 6, 50))
            # Pointed top
            surf.set_at((px + 1, 14), c("wood_dark"))
            surf.set_at((px + 2, 13), c("wood_dark"))
            surf.set_at((px + 3, 13), c("wood_dark"))
            surf.set_at((px + 4, 14), c("wood_dark"))

    elif tile_type == T_FLOWER:
        surf.fill(c("grass_light"))
        # Stem
        surf.set_at((40, 50), c("tree_canopy"))
        surf.set_at((40, 54), c("tree_canopy"))
        surf.set_at((40, 58), c("tree_canopy"))
        # Flower head
        for dx in range(-6, 7, 3):
            for dy in range(-6, 7, 3):
                if abs(dx) + abs(dy) <= 6:
                    px, py = 40 + dx, 40 + dy
                    if 0 <= px < TILE_SIZE and 0 <= py < TILE_SIZE:
                        surf.set_at((px, py), c("flower"))
                        surf.set_at((px + 1, py), c("flower"))
        # Center
        surf.set_at((40, 40), (255, 220, 50))

    elif tile_type == T_STONE:
        surf.fill(c("grass_light"))
        pygame.draw.circle(surf, c("stone"), (35, 50), 12)
        pygame.draw.circle(surf, c("stone"), (50, 55), 8)
        pygame.draw.circle(surf, c("well"), (42, 48), 6)

    elif tile_type == T_MEETING:
        """Town square meeting platform — a raised stone circle."""
        # Base — slightly lighter than path to stand out
        surf.fill(c("path"))
        # Stone circle (outer ring)
        pygame.draw.circle(surf, c("stone"), (40, 40), 28, 4)
        # Inner compass lines — cross pattern
        pygame.draw.line(surf, c("stone"), (40, 14), (40, 66), 2)
        pygame.draw.line(surf, c("stone"), (14, 40), (66, 40), 2)
        # Diagonal lines for compass rose
        d = 18  # diagonal offset
        pygame.draw.line(surf, c("stone"), (40 - d, 40 - d), (40 + d, 40 + d), 1)
        pygame.draw.line(surf, c("stone"), (40 + d, 40 - d), (40 - d, 40 + d), 1)
        # Centre dot — warm glow
        dot_color = (255, 200, 100) if not night else (180, 140, 60)
        surf.set_at((40, 40), dot_color)
        surf.set_at((39, 39), dot_color)
        surf.set_at((41, 41), dot_color)
        surf.set_at((39, 41), dot_color)
        surf.set_at((41, 39), dot_color)
        # Small decorative stones around edge
        import math as _m
        for i in range(8):
            ang = i * _m.pi / 4
            sx = int(40 + 26 * _m.cos(ang))
            sy = int(40 + 26 * _m.sin(ang))
            if 0 <= sx < TILE_SIZE and 0 <= sy < TILE_SIZE:
                surf.set_at((sx, sy), c("stone"))
                surf.set_at((sx + 1, sy), c("stone"))
        # Night glow
        if night:
            s = pygame.Surface((24, 24), pygame.SRCALPHA)
            s.fill((255, 200, 100, 25))
            surf.blit(s, (28, 28))

    elif tile_type == T_LANTERN:
        """Lantern post — wooden pole with glowing lantern."""
        surf.fill(c("grass_dark"))
        # Post
        pygame.draw.rect(surf, c("wood_dark"), (36, 30, 8, 50))
        # Cross arm
        pygame.draw.rect(surf, c("wood_dark"), (28, 34, 24, 4))
        # Lantern body
        lantern_color = c("window_glow") if night else (220, 200, 100)
        pygame.draw.rect(surf, lantern_color, (34, 20, 12, 14))
        # Lantern top cap
        pygame.draw.rect(surf, c("wood_dark"), (32, 18, 16, 4))
        # Night glow effect
        if night:
            glow_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
            glow_surf.fill((255, 200, 100, 20))
            surf.blit(glow_surf, (20, 12))
            # Extra warm light on ground
            ground_glow = pygame.Surface((28, 12), pygame.SRCALPHA)
            ground_glow.fill((255, 200, 100, 15))
            surf.blit(ground_glow, (26, 68))

    elif tile_type == T_SIGN:
        """Village signpost — welcome sign with pointing arms."""
        surf.fill(c("grass_light"))
        # Post
        pygame.draw.rect(surf, c("wood_dark"), (37, 30, 6, 50))
        # Sign board
        pygame.draw.rect(surf, c("wood_light"), (22, 24, 36, 18))
        # Sign border
        pygame.draw.rect(surf, c("wood_dark"), (22, 24, 36, 18), 2)
        # Text placeholder lines (wood grain scars)
        pygame.draw.line(surf, c("wood_dark"), (26, 30), (54, 30), 1)
        pygame.draw.line(surf, c("wood_dark"), (26, 35), (50, 35), 1)
        # Pointing arrows
        arm_color = c("wood_dark")
        pygame.draw.line(surf, arm_color, (20, 30), (10, 26), 2)
        pygame.draw.line(surf, arm_color, (10, 26), (10, 34), 2)
        pygame.draw.line(surf, arm_color, (60, 30), (70, 26), 2)
        pygame.draw.line(surf, arm_color, (70, 26), (70, 34), 2)
        # Post base
        pygame.draw.rect(surf, c("stone"), (33, 72, 14, 8))

    return surf


def get_tile(tile_type: int, night: bool) -> pygame.Surface:
    """Get a cached tile surface, generating if needed."""
    key = (tile_type, night)
    if key not in _tile_cache:
        _tile_cache[key] = _draw_tile(tile_type, night)
    return _tile_cache[key]


# ── Village renderer ───────────────────────────────────────────────

# Player home positions on the village grid (row, col)
# Each player stands adjacent to their house door
PLAYER_HOMES: list[tuple[int, int]] = [
    (6, 3),   # Player 0  - near house 1 (top-left)
    (6, 4),   # Player 1
    (6, 22),  # Player 2  - near house 2 (top-right)
    (6, 23),  # Player 3
    (11, 5),  # Player 4  - near house 3 (mid-left)
    (11, 6),  # Player 5
    (11, 23), # Player 6  - near house 4 (mid-right)
    (11, 24), # Player 7
    (16, 10), # Player 8  - near house 5 (bottom-left)
    (16, 11), # Player 9
    (16, 20), # Player 10 - near house 6 (bottom-right)
    (16, 21), # Player 11
]

# Town square meeting positions — players gather here during day phases
# Arranged in a semi-circle around the village centre (row 10, col 14)
# Each position is (row, col) near the central path intersection
MEETING_POSITIONS: list[tuple[float, float]] = [
    (9.5, 15.5),   # Player 0  - centre front
    (9.0, 17.0),   # Player 1  - centre right
    (9.0, 13.0),   # Player 2  - centre left
    (9.5, 12.0),   # Player 3  - far left
    (10.5, 17.5),  # Player 4  - back right
    (11.0, 16.0),  # Player 5  - back centre
    (11.0, 13.0),  # Player 6  - back centre-left
    (10.5, 11.5),  # Player 7  - back left
    (12.0, 17.0),  # Player 8  - far back right
    (12.0, 14.0),  # Player 9  - far back centre
    (12.0, 12.0),  # Player 10 - far back centre-left
    (12.5, 15.0),  # Player 11 - far back
]


class VillageRenderer:
    """Renders the pixel-art village background with player characters."""

    # Action feedback types and their visual colours
    FX_SEER = "seer"       # Blue eye / investigation glow
    FX_KILL = "kill"       # Red slash / werewolf attack
    FX_SAVE = "save"       # Green shield / guard or witch protection
    FX_POISON = "poison"   # Purple skull / witch poison

    def __init__(self) -> None:
        self._tile_map = _build_village_map()
        # Pre-generate night and day background surfaces
        self._bg_day: Optional[pygame.Surface] = None
        self._bg_night: Optional[pygame.Surface] = None
        self._players: list[Optional[Any]] = []  # list of player dicts or None
        self._font: Optional[pygame.font.Font] = None  # kept for .get_height() only
        # Player position interpolation for day/night gathering
        self._is_day_mode: bool = False
        self._anim_progress: float = 0.0  # 0=all at home, 1=all at meeting
        # Current interpolated positions cache (sub-tile precision)
        self._current_positions: list[tuple[float, float]] = []
        # Action feedback overlays (player_idx, fx_type, remaining_time)
        self._action_fx: list[tuple[int, str, float]] = []
        # ── Background day/night blend transition ──
        self._bg_blend_active: bool = False       # True during a transition
        self._bg_blend_from_night: bool = False    # True = blending from night→day; False = day→night
        self._bg_blend_progress: float = 0.0       # 0.0 → 1.0 over transition duration
        self._bg_blend_duration: float = 1.2       # seconds for full blend
        self._bg_blend_surface: Optional[pygame.Surface] = None  # pre-mixed blend frame

    def _build_background(self, night: bool) -> pygame.Surface:
        """Build the full background surface from the tile map."""
        bg = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        for row_idx, row in enumerate(self._tile_map):
            for col_idx, tile_type in enumerate(row):
                tile_surf = get_tile(tile_type, night)
                bg.blit(tile_surf, (col_idx * TILE_SIZE, row_idx * TILE_SIZE))
        return bg

    def get_background(self, night: bool) -> pygame.Surface:
        """Get cached background surface for day or night.

        During a transition, returns a blended surface between day and night.
        """
        # Ensure both caches exist
        if self._bg_day is None:
            self._bg_day = self._build_background(False)
        if self._bg_night is None:
            self._bg_night = self._build_background(True)

        # During an active background blend, return the blended surface
        if self._bg_blend_active and self._bg_blend_surface is not None:
            return self._bg_blend_surface

        # Normal static background
        return self._bg_night if night else self._bg_day

    def set_players(self, players: list[Any]) -> None:
        """Set the player list for rendering. Each item should have:
        .index, .alive, .name, .role attributes.
        """
        self._players = list(players)
        # Initialise cached positions to home positions
        if not self._current_positions:
            for idx in range(len(self._players)):
                pos_idx = idx % len(PLAYER_HOMES)
                row, col = PLAYER_HOMES[pos_idx]
                self._current_positions.append((float(row), float(col)))

    def set_day_mode(self, is_day: bool, dt: float) -> None:
        """Set whether it's day (gathering) or night (returning home).
        Smoothly animates the transition over GATHER_SPEED seconds.
        Also blends the background between day/night caches.
        """
        last_mode = self._is_day_mode
        self._is_day_mode = is_day

        # ── Background blend transition ──
        # Detect actual flip in day/night mode and start a background blend
        # Only trigger if we've been initialised (bg cache exists) and the mode flips
        if self._bg_day is not None and last_mode != is_day:
            self._bg_blend_active = True
            # blending *from* the previous state: night→day, or day→night
            self._bg_blend_from_night = not last_mode
            self._bg_blend_progress = 0.0
            self._bg_blend_surface = None

        # ── Player position animation ──
        target = 1.0 if is_day else 0.0
        GATHER_SPEED = 1.5  # seconds to fully transition
        if self._anim_progress < target:
            self._anim_progress = min(self._anim_progress + dt / GATHER_SPEED, target)
        elif self._anim_progress > target:
            self._anim_progress = max(self._anim_progress - dt / GATHER_SPEED, target)
        # Update interpolated positions
        for idx in range(len(self._players)):
            pos_idx = idx % len(PLAYER_HOMES)
            home_row, home_col = PLAYER_HOMES[pos_idx]
            if idx < len(MEETING_POSITIONS):
                meet_row, meet_col = MEETING_POSITIONS[idx]
                t = self._anim_progress
                # Smooth step easing
                t = t * t * (3.0 - 2.0 * t)  # smoothstep
                row = home_row + (meet_row - home_row) * t
                col = home_col + (meet_col - home_col) * t
            else:
                row, col = float(home_row), float(home_col)
            if idx < len(self._current_positions):
                self._current_positions[idx] = (row, col)
            else:
                self._current_positions.append((row, col))

        # ── Update background blend progress ──
        if self._bg_blend_active:
            self._bg_blend_progress = min(
                self._bg_blend_progress + dt / self._bg_blend_duration, 1.0
            )
            # Calculate the blended frame
            t = self._bg_blend_progress
            # Ease-in-out
            t = t * t * (3.0 - 2.0 * t)  # smoothstep
            if self._bg_blend_surface is None:
                self._bg_blend_surface = pygame.Surface(
                    (VIEWPORT_W, VIEWPORT_H), pygame.SRCALPHA
                )
            # Ensure both background caches exist
            if self._bg_day is None:
                self._bg_day = self._build_background(False)
            if self._bg_night is None:
                self._bg_night = self._build_background(True)
            # Blend: if blending from night→day, blend_night = 1-t, else blend_night = t
            if self._bg_blend_from_night:
                # night at t=0, day at t=1
                blend_night = 1.0 - t
            else:
                # day at t=0, night at t=1
                blend_night = t
            # Proper alpha blend: blit day, then blit night with alpha
            self._bg_blend_surface.fill((0, 0, 0))
            self._bg_blend_surface.blit(self._bg_day, (0, 0))
            if int(blend_night * 255) > 0:
                night_overlay = self._bg_night.copy()
                night_overlay.set_alpha(int(blend_night * 255))
                self._bg_blend_surface.blit(night_overlay, (0, 0))
            # If blend complete, snap to final
            if self._bg_blend_progress >= 1.0:
                self._bg_blend_active = False
                self._bg_blend_surface = None

    def show_action(self, player_idx: int, fx_type: str, duration: float = 1.0) -> None:
        """Show a visual feedback effect on a player character.

        Args:
            player_idx: The player's index.
            fx_type: One of FX_SEER, FX_KILL, FX_SAVE, FX_POISON.
            duration: How long the effect is visible (seconds).
        """
        self._action_fx.append((player_idx, fx_type, duration))

    def update_fx(self, dt: float) -> None:
        """Update action feedback timers — decrement and remove expired."""
        remaining = []
        for idx, fx_type, timer in self._action_fx:
            new_timer = timer - dt
            if new_timer > 0:
                remaining.append((idx, fx_type, new_timer))
        self._action_fx = remaining

    def render(self, screen: pygame.Surface, night: bool) -> None:
        """Draw the village background and player characters onto the screen."""
        bg = self.get_background(night)
        screen.blit(bg, (0, 0))

        # Render player characters on top of the background
        self._render_players(screen, night)

    def _draw_action_fx(self, screen: pygame.Surface, player_idx: int, x_pos: int, y_pos: int) -> None:
        """Draw action feedback effects on top of a character sprite."""
        for fx_idx, fx_type, _ in self._action_fx:
            if fx_idx != player_idx:
                continue
            # Effect icon drawn above the character head
            cx = x_pos + CHAR_W // 2
            cy = y_pos - 8
            if fx_type == self.FX_SEER:
                # Blue glowing eye (diamond shape)
                pygame.draw.circle(screen, (100, 180, 255), (cx, cy), 6)
                pygame.draw.circle(screen, (200, 230, 255), (cx, cy), 3)
                pygame.draw.circle(screen, (255, 255, 255), (cx - 1, cy - 1), 1)
            elif fx_type == self.FX_KILL:
                # Red slash marks
                pygame.draw.line(screen, (255, 60, 60), (cx - 6, cy - 4), (cx + 6, cy + 4), 3)
                pygame.draw.line(screen, (200, 30, 30), (cx - 5, cy), (cx + 5, cy), 2)
                # Small red particles
                for angle in range(0, 360, 45):
                    import math
                    px = cx + int(10 * math.cos(math.radians(angle)))
                    py = cy + int(10 * math.sin(math.radians(angle)))
                    screen.set_at((px, py), (255, 100, 80))
            elif fx_type == self.FX_SAVE:
                # Green shield
                shield_pts = [(cx, cy - 8), (cx + 6, cy - 4), (cx + 6, cy + 4),
                              (cx, cy + 8), (cx - 6, cy + 4), (cx - 6, cy - 4)]
                pygame.draw.polygon(screen, (80, 220, 100), shield_pts)
                pygame.draw.polygon(screen, (160, 255, 180), shield_pts, 2)
                # Cross on shield
                pygame.draw.line(screen, (255, 255, 255), (cx, cy - 4), (cx, cy + 4), 2)
                pygame.draw.line(screen, (255, 255, 255), (cx - 3, cy), (cx + 3, cy), 2)
            elif fx_type == self.FX_POISON:
                # Purple skull
                pygame.draw.circle(screen, (160, 80, 200), (cx, cy), 5)
                pygame.draw.circle(screen, (200, 120, 240), (cx, cy), 3)
                # Eyes
                screen.set_at((cx - 2, cy - 1), (60, 20, 80))
                screen.set_at((cx + 2, cy - 1), (60, 20, 80))

    def _render_players(self, screen: pygame.Surface, night: bool) -> None:
        """Draw character sprites for all players at their (interpolated) positions.
        During day phases, players gather at the town square; at night they return home.
        """
        if not self._players:
            return

        for player in self._players:
            if player is None:
                continue

            idx = player.index
            alive = player.alive

            # Get interpolated position (sub-tile precision)
            if idx < len(self._current_positions):
                row, col = self._current_positions[idx]
            else:
                pos_idx = idx % len(PLAYER_HOMES)
                row, col = PLAYER_HOMES[pos_idx]

            # Centre the character sprite in or near the tile
            sprite = get_character_sprite(idx, player.role, alive)
            x_pos = int(col * TILE_SIZE + (TILE_SIZE - CHAR_W) // 2)
            y_pos = int(row * TILE_SIZE + TILE_SIZE - CHAR_H - 4)

            screen.blit(sprite, (x_pos, y_pos))

            # Draw action feedback effects on top
            self._draw_action_fx(screen, idx, x_pos, y_pos)

            # Draw name label below using bitmap font
            name = getattr(player, 'name', f'P{idx}')
            if not alive:
                name += " x"
            fg = (255, 255, 255) if not night else (200, 200, 200)
            label = _render_text(name, scale=1, color=fg)
            shadow = _render_text(name, scale=1, color=(0, 0, 0))
            label_x = int(col * TILE_SIZE + (TILE_SIZE - label.get_width()) // 2)
            label_y = y_pos + CHAR_H + 2
            screen.blit(shadow, (label_x + 1, label_y + 1))
            screen.blit(label, (label_x, label_y))

    def invalidate_cache(self) -> None:
        """Clear cached backgrounds (e.g. on day/night transition)."""
        self._bg_day = None
        self._bg_night = None
        _tile_cache.clear()


# ── Quick test ─────────────────────────────────────────────────────

if __name__ == "__main__":
    pygame.init()
    screen = pygame.display.set_mode((2560, 1440))
    pygame.display.set_caption("Village test")
    clock = pygame.time.Clock()

    renderer = VillageRenderer()
    night = False
    running = True

    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_n:
                    night = not night
                    print(f"Night = {night}")

        renderer.render(screen, night)
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
