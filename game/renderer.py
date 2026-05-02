#!/usr/bin/env python3
"""Pixel-art village renderer for Pixel Werewolf.

Generates a 32x18 tile map (80px tiles -> 2560x1440 viewport)
with procedurally drawn pixel-art tiles. No external assets needed.
"""

from __future__ import annotations

import math
import random
from enum import Enum
from typing import Optional, Any

import pygame

from game.bitmap_font import render_text as _render_text
from game.player_sprites import CHAR_H, CHAR_W, get_character_sprite

# Constants
TILE_SIZE = 80
GRID_COLS = 48  # Expanded map (was 32)
GRID_ROWS = 27  # Expanded map (was 18)
VIEWPORT_W = 2560
VIEWPORT_H = 1440

# ── Weather ──────────────────────────────────────────────────────────


class WeatherState(Enum):
    CLEAR = "clear"
    RAIN = "rain"
    FOG = "fog"


# Rain settings
RAIN_DROP_COUNT = 200       # max raindrops visible at once
RAIN_DROP_MINSIZE = 8       # min pixel length
RAIN_DROP_MAXSIZE = 18      # max pixel length
RAIN_DROP_SPEED_MIN = 400   # pixels/sec
RAIN_DROP_SPEED_MAX = 700
RAIN_DROP_LAYERS = 3        # parallax layers for depth
RAIN_DROP_WIDTH = 2         # raindrop thickness (pixels)

# ── Firefly particles (night ambiance) ────────────────────────────
FIREFLY_COUNT = 30          # max fireflies on screen
FIREFLY_GLOW_RADIUS = 12    # base glow radius (pixels)
FIREFLY_SPEED_MIN = 15      # pixels/sec
FIREFLY_SPEED_MAX = 40
FIREFLY_ALPHA_MAX = 200     # max glow opacity

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
    """Return a 2D grid (rows x cols) of tile type IDs defining the village.

    The map is expanded beyond the viewport (48x27 tiles) to allow camera
    scrolling. The original 32x18 village is centred within the larger grid.
    """
    # Padding: offset to centre the original 32x18 village in a 48x27 grid
    PAD_COL = (GRID_COLS - 32) // 2  # 8
    PAD_ROW = (GRID_ROWS - 18) // 2  # 4

    grid: list[list[int]] = [[T_GRASS] * GRID_COLS for _ in range(GRID_ROWS)]

    # Fill top area with sky (above the village's original row 0)
    for r in range(PAD_ROW):
        for c in range(GRID_COLS):
            grid[r][c] = T_SKY

    # Row PAD_ROW+0 to PAD_ROW+1 (original rows 0-1): Sky with distant trees
    for r in range(2):
        for c in range(32):
            grid[PAD_ROW + r][PAD_COL + c] = T_SKY
    sky_tree_cols = {3, 7, 11, 15, 19, 23, 27}
    for c in sky_tree_cols:
        grid[PAD_ROW + 1][PAD_COL + c] = T_SKY_TREE
        if PAD_COL + c + 1 < GRID_COLS:
            grid[PAD_ROW + 1][PAD_COL + c + 1] = T_SKY_TREE

    # Row PAD_ROW+2 (original row 2): Tree line backdrop
    for c in range(32):
        if c % 4 < 2:
            grid[PAD_ROW + 2][PAD_COL + c] = T_TREE_CANOPY

    # ── Village area (original rows 3-14) ──

    # Main path (vertical, center - original col 14..17)
    for r in range(3, 16):
        for pc in (14, 15, 16, 17):
            grid[PAD_ROW + r][PAD_COL + pc] = T_PATH

    # Horizontal paths (original row 7, 12)
    for c in range(6, 26):
        grid[PAD_ROW + 7][PAD_COL + c] = T_PATH
        grid[PAD_ROW + 12][PAD_COL + c] = T_PATH

    # Path intersections
    for c in (14, 15, 16, 17):
        grid[PAD_ROW + 7][PAD_COL + c] = T_PATH_DARK
        grid[PAD_ROW + 12][PAD_COL + c] = T_PATH_DARK

    # ── Houses ──
    _place_house(grid, PAD_ROW + 3, PAD_COL + 2)
    _place_house(grid, PAD_ROW + 3, PAD_COL + 20)
    _place_house(grid, PAD_ROW + 8, PAD_COL + 3)
    _place_house(grid, PAD_ROW + 8, PAD_COL + 21)
    _place_house(grid, PAD_ROW + 13, PAD_COL + 8)
    _place_house(grid, PAD_ROW + 13, PAD_COL + 18)
    _place_house(grid, PAD_ROW + 4, PAD_COL + 9)
    _place_house(grid, PAD_ROW + 4, PAD_COL + 19)

    # Pond (bottom left)
    for r in range(14, 17):
        for c in range(1, 5):
            grid[PAD_ROW + r][PAD_COL + c] = T_WATER
    grid[PAD_ROW + 14][PAD_COL + 5] = T_WATER
    grid[PAD_ROW + 15][PAD_COL + 5] = T_WATER
    grid[PAD_ROW + 16][PAD_COL + 5] = T_WATER

    # Well (center right)
    grid[PAD_ROW + 9][PAD_COL + 20] = T_WELL
    grid[PAD_ROW + 9][PAD_COL + 21] = T_WELL

    # Fence (bottom)
    for c in range(8, 24):
        grid[PAD_ROW + 16][PAD_COL + c] = T_FENCE

    # Flowers near houses
    for (r, c) in [
        (7, 5), (7, 6), (7, 22), (7, 23),
        (12, 2), (12, 3), (12, 26), (12, 27),
        (13, 6), (13, 22),
    ]:
        grid[PAD_ROW + r][PAD_COL + c] = T_FLOWER

    # Lantern posts along the main path
    for (r, c) in [(5, 14), (5, 17), (9, 14), (9, 17), (12, 14), (12, 17)]:
        grid[PAD_ROW + r][PAD_COL + c] = T_LANTERN

    # Village signpost at entrance
    grid[PAD_ROW + 4][PAD_COL + 6] = T_SIGN

    # Stones
    grid[PAD_ROW + 10][PAD_COL + 5] = T_STONE
    grid[PAD_ROW + 10][PAD_COL + 6] = T_STONE
    grid[PAD_ROW + 11][PAD_COL + 22] = T_STONE
    grid[PAD_ROW + 11][PAD_COL + 23] = T_STONE

    # Town square meeting platform
    for (r, c) in [(10, 15), (10, 16), (11, 15), (11, 16)]:
        grid[PAD_ROW + r][PAD_COL + c] = T_MEETING

    # ── Scatter some trees in the expanded border zones ──
    import random as _rand
    _rand.seed(42)
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            # Skip the village interior area
            if PAD_ROW <= r < PAD_ROW + 18 and PAD_COL <= c < PAD_COL + 32:
                continue
            if r < PAD_ROW:  # top margin — sky already set
                continue
            if _rand.random() < 0.12:
                grid[r][c] = T_TREE_TRUNK if _rand.random() < 0.4 else T_TREE_CANOPY

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


def _draw_tile_overlay(target: pygame.Surface, tile_type: int, night: bool,
                       col: int, row: int, time: float,
                       offset_x: int = 0, offset_y: int = 0) -> None:
    """Draw per-frame animated overlays on top of a cached tile.

    Currently animates:
      - T_WATER: subtle shimmer / ripple lines
      - T_LANTERN: warm glow pulse (night only)

    Args:
        offset_x, offset_y: Camera offset to convert tile coords to screen coords.
    """
    x = col * TILE_SIZE + offset_x
    y = row * TILE_SIZE + offset_y
    waviness = math.sin(time * 2.0 + col * 0.7 + row * 1.3)

    if tile_type == T_WATER:
        # Animated water shimmer: moving highlight lines
        highlight_y = y + 20 + int(10 * waviness)
        for dx in range(4, TILE_SIZE - 4, 12):
            alpha = max(0, min(255, int(128 + 64 * math.sin(time * 1.5 + dx * 0.3 + col))))
            shimmer_color = (200, 220, 255, alpha) if not night else (100, 140, 200, alpha)
            # Draw shimmer pixels
            for hx in range(dx, min(dx + 6, TILE_SIZE - 1)):
                hy = highlight_y + int(3 * math.sin(time * 0.7 + dx * 0.5))
                if 0 <= hy < TILE_SIZE and 0 <= hx < TILE_SIZE:
                    # Semi-transparent by doing a weighted average with existing
                    existing = target.get_at((x + hx, y + hy))
                    col_blend = (
                        (existing[0] * (255 - alpha) + shimmer_color[0] * alpha) // 256,
                        (existing[1] * (255 - alpha) + shimmer_color[1] * alpha) // 256,
                        (existing[2] * (255 - alpha) + shimmer_color[2] * alpha) // 256,
                    )
                    target.set_at((x + hx, y + hy), col_blend)

    elif tile_type == T_LANTERN and night:
        # Flickering warm glow around the lantern
        glow_strength = max(0.6, 0.8 + 0.2 * math.sin(time * 5.0 + col * 2.1))
        glow_color = (
            int(255 * glow_strength),
            int(180 * glow_strength),
            int(80 * glow_strength),
        )
        glow_radius = int(16 * glow_strength)
        cx, cy = x + 40, y + 27  # lantern center
        # Draw a simple radial glow as concentric circles
        for r in range(glow_radius, 0, -4):
            fade = 1.0 - (r / glow_radius)
            a = int(60 * fade * glow_strength)
            if a <= 0:
                continue
            glow = (glow_color[0], glow_color[1], glow_color[2])
            # Draw circle outline with fade
            pygame.draw.circle(target, glow, (cx, cy), r)
        # Also add a brighter halo at the lantern centre
        center_glow = (255, 220, 150)
        for r2 in range(6, 0, -2):
            a = int(80 * glow_strength * (1.0 - r2 / 6.0))
            if a > 0:
                pygame.draw.circle(target, center_glow, (cx, cy), r2)


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

        # ── Weather state ──
        self._weather: WeatherState = WeatherState.CLEAR
        self._weather_target: WeatherState = WeatherState.CLEAR
        self._weather_blend: float = 0.0  # 0→1 transition progress
        self._weather_blend_speed: float = 0.5  # seconds to fully transition
        self._weather_update_timer: float = 0.0
        # Rain particles: list of (x, y, speed, length, alpha, layer)
        self._rain_particles: list[list] = []
        self._init_rain_particles()

        # ── Firefly particles (night ambiance) ──
        self._fireflies: list[list] = []
        self._init_fireflies()
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
        # Speech bubbles: dict of player_idx -> (text, remaining_time)
        self._speech_bubbles: dict[int, tuple[str, float]] = {}
        # ── Background day/night blend transition ──
        self._bg_blend_active: bool = False       # True during a transition
        self._bg_blend_from_night: bool = False    # True = blending from night→day; False = day→night
        self._bg_blend_progress: float = 0.0       # 0.0 → 1.0 over transition duration
        self._bg_blend_duration: float = 1.2       # seconds for full blend
        self._bg_blend_surface: Optional[pygame.Surface] = None  # pre-mixed blend frame

        # Internal render target (always 2560x1440) for scaling support
        self._render_target: Optional[pygame.Surface] = None

    @property
    def weather(self) -> WeatherState:
        return self._weather

    @weather.setter
    def weather(self, value: WeatherState) -> None:
        self._weather_target = value
        self._weather_blend = 0.0

    def _build_background(self, night: bool) -> pygame.Surface:
        """Build the full background surface from the tile map.

        The background is now the full world size (GRID_COLS x GRID_ROWS tiles),
        larger than the viewport, to support camera scrolling.
        """
        world_w = GRID_COLS * TILE_SIZE
        world_h = GRID_ROWS * TILE_SIZE
        bg = pygame.Surface((world_w, world_h))
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
        Initialises home positions for each player.
        """
        self._players = list(players)
        # Initialise cached positions to home positions
        self._current_positions = []
        self._target_positions = []
        self._position_progress = {}
        for idx in range(len(self._players)):
            pos_idx = idx % len(PLAYER_HOMES)
            row, col = PLAYER_HOMES[pos_idx]
            self._current_positions.append((float(row), float(col)))
            self._target_positions.append((float(row), float(col)))
            self._position_progress[idx] = 1.0

    # ── Weather API ──────────────────────────────────────────────────

    def set_weather(self, state: WeatherState) -> None:
        """Request a weather state transition. Blends smoothly."""
        if state != self._weather_target:
            self._weather_target = state
            self._weather_blend = 0.0

    def get_weather(self) -> WeatherState:
        """Return the current (blended) weather state."""
        if self._weather_blend >= 1.0:
            return self._weather_target
        if self._weather_blend <= 0.0:
            return self._weather
        return self._weather

    def _init_fireflies(self) -> None:
        """Create firefly particles for night ambiance."""
        self._fireflies.clear()
        for _ in range(FIREFLY_COUNT):
            x = random.uniform(0, VIEWPORT_W)
            y = random.uniform(0, VIEWPORT_H * 0.8)  # mostly lower half
            # vx, vy: velocity in pixels/sec
            angle = random.uniform(0, math.tau)
            speed = random.uniform(FIREFLY_SPEED_MIN, FIREFLY_SPEED_MAX)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed * 0.4  # slower vertical
            # phase: random offset for pulsing glow (0..2pi)
            phase = random.uniform(0, math.tau)
            # base_alpha, size: individual variation
            base_alpha = random.randint(100, FIREFLY_ALPHA_MAX)
            size = random.uniform(0.6, 1.4)
            self._fireflies.append([x, y, vx, vy, phase, base_alpha, size])

    def _init_rain_particles(self) -> None:
        """Create initial rain particles scattered across the viewport."""
        self._rain_particles.clear()
        for _ in range(RAIN_DROP_COUNT):
            x = random.uniform(0, VIEWPORT_W)
            y = random.uniform(-VIEWPORT_H * 0.2, VIEWPORT_H)
            speed = random.uniform(RAIN_DROP_SPEED_MIN, RAIN_DROP_SPEED_MAX)
            length = random.randint(RAIN_DROP_MINSIZE, RAIN_DROP_MAXSIZE)
            alpha = random.randint(120, 220)
            layer = random.randint(0, RAIN_DROP_LAYERS - 1)
            self._rain_particles.append([x, y, speed, length, alpha, layer])

    def _update_rain(self, dt: float) -> None:
        """Update raindrop positions. Wrap around and respawn."""
        for p in self._rain_particles:
            x, y, speed, length, alpha, layer = p
            # Rain falls diagonally (down-right)
            y += speed * dt
            x += speed * dt * 0.3
            # Wrap around when below screen
            if y > VIEWPORT_H + length:
                y = -length
                x = random.uniform(0, VIEWPORT_W)
                alpha = random.randint(120, 220)
            p[0] = x
            p[1] = y
            p[4] = alpha

    def _update_fireflies(self, dt: float) -> None:
        """Update firefly positions and wrap around the viewport."""
        for f in self._fireflies:
            x, y, vx, vy, phase, base_alpha, size = f
            # Move with gentle drift
            x += vx * dt
            y += vy * dt
            # Slow drift (velocity changes subtly each frame)
            drift = 0.98  # keep ~98% velocity, add slight randomness
            vx = vx * drift + random.uniform(-5, 5) * dt
            vy = vy * drift + random.uniform(-3, 3) * dt
            # Clamp speed
            max_speed = FIREFLY_SPEED_MAX
            current_speed = math.sqrt(vx * vx + vy * vy)
            if current_speed > max_speed:
                vx = vx / current_speed * max_speed
                vy = vy / current_speed * max_speed
            # Wrap around
            margin = 40
            if x < -margin:
                x = VIEWPORT_W + margin
            elif x > VIEWPORT_W + margin:
                x = -margin
            if y < -margin:
                y = VIEWPORT_H * 0.8 + margin
            elif y > VIEWPORT_H * 0.8 + margin:
                y = -margin
            # Advance phase for pulsing glow
            phase += dt * random.uniform(0.8, 1.5)
            if phase > math.tau:
                phase -= math.tau
            f[0], f[1], f[2], f[3], f[4] = x, y, vx, vy, phase

    def _draw_weather_overlay(self, target: pygame.Surface, night: bool) -> None:
        """Draw weather effects (rain, fog) on top of the village scene."""
        blend = min(self._weather_blend, 1.0)
        if blend <= 0.0:
            return
        current_weather = self._weather if self._weather_blend < 1.0 else self._weather_target
        if current_weather == WeatherState.RAIN:
            self._draw_rain_overlay(target, night, blend)
        elif current_weather == WeatherState.FOG:
            self._draw_fog_overlay(target, night, blend)

    def _draw_rain_overlay(self, target: pygame.Surface, night: bool, blend: float) -> None:
        """Draw raindrops as thin slanted lines."""
        r, g, b = (180, 200, 220) if not night else (140, 160, 190)
        for p in self._rain_particles:
            x, y, speed, length, alpha, layer = p
            effective_alpha = int(alpha * blend)
            if effective_alpha < 10:
                continue
            stroke = max(1, RAIN_DROP_WIDTH - layer)
            p_alpha = effective_alpha - layer * 20
            if p_alpha < 10:
                continue
            color = (r, g, b, p_alpha)
            # Slanted line (down-right angle)
            end_x = int(x + math.sin(math.radians(15)) * length)
            end_y = int(y + math.cos(math.radians(15)) * length)
            pygame.draw.line(target, color[:3], (int(x), int(y)), (end_x, end_y), stroke)

    def _draw_fog_overlay(self, target: pygame.Surface, night: bool, blend: float) -> None:
        """Draw a semi-transparent fog layer over the village."""
        fog_surf = pygame.Surface((VIEWPORT_W, VIEWPORT_H), pygame.SRCALPHA)
        fog_alpha = int(80 * blend) if not night else int(50 * blend)
        fog_color = (200, 200, 210, fog_alpha)
        fog_surf.fill(fog_color)
        target.blit(fog_surf, (0, 0))

    def _draw_fireflies(self, target: pygame.Surface, night: bool, time: float) -> None:
        """Draw glowing firefly particles during night."""
        if not night:
            return
        # Create a separate surface for additive-like glow blending
        glow_surf = pygame.Surface((VIEWPORT_W, VIEWPORT_H), pygame.SRCALPHA)
        for f in self._fireflies:
            x, y, vx, vy, phase, base_alpha, size = f
            # Pulsing glow: sin wave creates smooth fade in/out
            pulse = (math.sin(phase) + 1.0) * 0.5  # 0..1
            alpha = int(base_alpha * (0.4 + 0.6 * pulse))
            if alpha < 5:
                continue
            radius = int(FIREFLY_GLOW_RADIUS * size * (0.8 + 0.4 * pulse))
            cx, cy = int(x), int(y)
            # Outer glow (larger, dimmer)
            glow_color = (220, 255, 180, alpha // 3)
            pygame.draw.circle(glow_surf, glow_color, (cx, cy), radius + 4)
            # Inner glow
            glow_color = (255, 255, 200, alpha)
            pygame.draw.circle(glow_surf, glow_color, (cx, cy), max(1, radius // 2))
            # Bright core (clamp alpha to 255)
            core_alpha = min(255, alpha * 2)
            core_color = (255, 255, 240, core_alpha)
            pygame.draw.circle(glow_surf, core_color, (cx, cy), max(1, radius // 4))
        target.blit(glow_surf, (0, 0))

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
                world_w = GRID_COLS * TILE_SIZE
                world_h = GRID_ROWS * TILE_SIZE
                self._bg_blend_surface = pygame.Surface(
                    (world_w, world_h), pygame.SRCALPHA
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

    def set_speech_bubble(self, player_idx: int, text: str, duration: float = 4.0) -> None:
        """Set a speech bubble above a player character.

        Args:
            player_idx: The player's index.
            text: The speech text to display.
            duration: How long the bubble is visible (seconds).
        """
        self._speech_bubbles[player_idx] = (text, duration)

    def update_fx(self, dt: float) -> None:
        """Update action feedback timers — decrement and remove expired."""
        remaining = []
        for idx, fx_type, timer in self._action_fx:
            new_timer = timer - dt
            if new_timer > 0:
                remaining.append((idx, fx_type, new_timer))
        self._action_fx = remaining

        # Decay speech bubbles
        expired = []
        for idx, (text, timer) in self._speech_bubbles.items():
            new_timer = timer - dt
            if new_timer > 0:
                self._speech_bubbles[idx] = (text, new_timer)
            else:
                expired.append(idx)
        for idx in expired:
            self._speech_bubbles.pop(idx, None)

        # ── Firefly simulation (always runs for smooth phase animation) ──
        self._update_fireflies(dt)

        # ── Weather transitions ──
        if self._weather_target != self._weather:
            self._weather_blend += dt / self._weather_blend_speed
            if self._weather_blend >= 1.0:
                self._weather = self._weather_target
                self._weather_blend = 0.0

        # ── Rain particle simulation ──
        if self._weather == WeatherState.RAIN or self._weather_target == WeatherState.RAIN:
            self._update_rain(dt)

    def _draw_tile_overlays_viewport(self, target: pygame.Surface, night: bool, time: float,
                                       cam_x: float, cam_y: float) -> None:
        """Draw per-frame tile overlays only for tiles visible in the viewport.

        Camera-aware version: only draws overlays for tiles within the visible
        viewport area to avoid wasting CPU cycles on off-screen tiles.
        """
        # Determine visible tile range (with 1-tile buffer for glow effects)
        start_col = max(0, int(cam_x) // TILE_SIZE - 1)
        end_col = min(GRID_COLS, (int(cam_x) + VIEWPORT_W + TILE_SIZE - 1) // TILE_SIZE + 1)
        start_row = max(0, int(cam_y) // TILE_SIZE - 1)
        end_row = min(GRID_ROWS, (int(cam_y) + VIEWPORT_H + TILE_SIZE - 1) // TILE_SIZE + 1)

        # Offset to convert tile coordinates to screen position
        offset_x = -int(cam_x)
        offset_y = -int(cam_y)

        for row_idx in range(start_row, end_row):
            row = self._tile_map[row_idx]
            for col_idx in range(start_col, end_col):
                tile_type = row[col_idx]
                if tile_type == T_WATER or (tile_type == T_LANTERN and night):
                    _draw_tile_overlay(target, tile_type, night,
                                       col_idx, row_idx, time,
                                       offset_x=offset_x, offset_y=offset_y)

    def render(self, screen: pygame.Surface, night: bool, time: float = 0.0,
                human_player_idx: int = 0,
                camera_x: float = 0.0, camera_y: float = 0.0) -> None:
        """Draw the village background and player characters onto the screen.

        Renders the full world and applies camera offset to show the
        visible viewport portion, then scales to match screen dimensions.

        Args:
            screen: The pygame surface to draw onto.
            night: True if night-time palette should be used.
            time: Game time in seconds (for animated tiles like water & lanterns).
                  Pass 0.0 to disable animation (e.g. when paused).
            human_player_idx: Index of the human player, used to draw a
                  visual indicator above their character on the map.
            camera_x: Camera X offset (world pixels from left).
            camera_y: Camera Y offset (world pixels from top).
        """
        # Render to internal 2560x1440 target first
        sw, sh = screen.get_size()
        if self._render_target is None or self._render_target.get_size() != (VIEWPORT_W, VIEWPORT_H):
            self._render_target = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        target = self._render_target

        bg = self.get_background(night)

        # Clamp camera to world bounds
        world_w = GRID_COLS * TILE_SIZE
        world_h = GRID_ROWS * TILE_SIZE
        cam_x = max(0.0, min(camera_x, float(world_w - VIEWPORT_W)))
        cam_y = max(0.0, min(camera_y, float(world_h - VIEWPORT_H)))

        # Blit the visible portion of the background with camera offset
        target.blit(bg, (0, 0), area=(
            int(cam_x), int(cam_y),
            VIEWPORT_W, VIEWPORT_H
        ))

        # Draw per-frame animated tile overlays (with camera offset)
        if time > 0.0:
            self._draw_tile_overlays_viewport(target, night, time, cam_x, cam_y)

        # Render player characters on top of the background
        self._render_players(target, night, human_player_idx, time, camera_x=cam_x, camera_y=cam_y)

        # ── Weather overlay (rain, fog) — screen-space, no camera ──
        self._draw_weather_overlay(target, night)

        # ── Night-time firefly ambiance — screen-space, no camera ──
        self._draw_fireflies(target, night, time)

        # Scale to actual screen dimensions if needed
        if (sw, sh) == (VIEWPORT_W, VIEWPORT_H):
            screen.blit(target, (0, 0))
        else:
            # Use NEAREST neighbour for pixel-art fidelity
            scaled = pygame.transform.scale(target, (sw, sh))
            screen.blit(scaled, (0, 0))

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

    def _render_players(self, screen: pygame.Surface, night: bool,
                         human_player_idx: int = 0, time: float = 0.0,
                         camera_x: float = 0.0, camera_y: float = 0.0) -> None:
        """Draw character sprites for all players at their (interpolated) positions.
        During day phases, players gather at the town square; at night they return home.

        Args:
            screen: The pygame surface to draw onto.
            night: True if night-time palette should be used.
            human_player_idx: Index of the human-controlled player.
            time: Game time in seconds (for pulsing animation of the self-indicator).
            camera_x: Camera offset X (world pixels from left).
            camera_y: Camera offset Y (world pixels from top).
        """
        if not self._players:
            return

        # Convert camera offset to screen-space offset
        off_x = -int(camera_x)
        off_y = -int(camera_y)

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

            # Centre the character sprite in or near the tile (apply camera offset)
            sprite = get_character_sprite(idx, player.role, alive)
            x_pos = int(col * TILE_SIZE + (TILE_SIZE - CHAR_W) // 2) + off_x
            y_pos = int(row * TILE_SIZE + TILE_SIZE - CHAR_H - 4) + off_y

            # Idle bob animation (gentle 3px sine wave — alive only)
            bob = 0
            if alive:
                bob = int(3.0 * math.sin(time * 2.5 + idx * 1.8))

            screen.blit(sprite, (x_pos, y_pos + bob))

            # Draw action feedback effects on top
            self._draw_action_fx(screen, idx, x_pos, y_pos)

            # Draw sheriff badge (star icon) above the character
            if getattr(player, 'is_sheriff', False):
                from game.bitmap_font import render_text
                star = render_text("★", scale=2, color=(255, 215, 0),
                                   shadow=(180, 140, 0))
                star_x = x_pos + (CHAR_W - star.get_width()) // 2
                star_y = y_pos - star.get_height() - 2
                screen.blit(star, (star_x, star_y))

            # Draw golden pulsing self-indicator above the human player
            if idx == human_player_idx:
                cx = x_pos + CHAR_W // 2
                # Pulsing size based on sin(time * 3.0)
                pulse = math.sin(time * 3.0) if time > 0.0 else 1.0
                extra = int(2 * abs(pulse))  # 0-2 extra pixels
                peak_y = y_pos - 10 - extra

                # Golden diamond (two triangles)
                diamond_top = (cx, peak_y - 6)
                diamond_bot = (cx, peak_y + 2)
                diamond_l = (cx - 5, peak_y - 2)
                diamond_r = (cx + 5, peak_y - 2)

                # Outer glow (semi-transparent, larger)
                glow_pts = [(cx, peak_y - 9), (cx + 8, peak_y - 2),
                            (cx, peak_y + 5), (cx - 8, peak_y - 2)]
                pygame.draw.polygon(screen, (255, 220, 60), glow_pts, 0)

                # Main diamond
                main_pts = [diamond_top, diamond_r, diamond_bot, diamond_l]
                pygame.draw.polygon(screen, (255, 215, 0), main_pts, 0)
                pygame.draw.polygon(screen, (255, 255, 200), main_pts, 1)

                # Center pixel highlight
                screen.set_at((cx, peak_y - 2), (255, 255, 255))

                # Small sparkle lines at peak of pulse
                if extra > 1:
                    sparkle_len = 2
                    pygame.draw.line(screen, (255, 240, 150),
                                     (cx - sparkle_len, peak_y - 6),
                                     (cx + sparkle_len, peak_y - 6), 1)
                    pygame.draw.line(screen, (255, 240, 150),
                                     (cx, peak_y - 6 - sparkle_len),
                                     (cx, peak_y - 6 + sparkle_len), 1)

            # Draw name label below using bitmap font
            name = getattr(player, 'name', f'P{idx}')
            if not alive:
                name += " x"
            fg = (255, 255, 255) if not night else (200, 200, 200)
            label = _render_text(name, scale=1, color=fg)
            shadow = _render_text(name, scale=1, color=(0, 0, 0))
            label_x = int(col * TILE_SIZE + (TILE_SIZE - label.get_width()) // 2) + off_x
            label_y = y_pos + CHAR_H + 2
            screen.blit(shadow, (label_x + 1, label_y + 1))
            screen.blit(label, (label_x, label_y))

            # ── Speech bubble ──
            if idx in self._speech_bubbles:
                bubble_text, _ = self._speech_bubbles[idx]
                # Measure text width for bubble sizing
                words = bubble_text.split()
                text_len = sum(len(w) for w in words)
                # Single line if short, wrap if long
                if text_len <= 20:
                    display_line = bubble_text
                else:
                    display_line = bubble_text[:20] + "…"

                bubble_w = _render_text(display_line, scale=1, color=(0, 0, 0)).get_width() + 14
                bubble_h = 20  # fixed height for one-liner bubbles
                bx = int(col * TILE_SIZE + (TILE_SIZE - bubble_w) // 2) + off_x
                by = y_pos - bubble_h - 6

                # Bubble background (white with dark border)
                pygame.draw.rect(screen, (255, 255, 245), (bx, by, bubble_w, bubble_h), border_radius=4)
                pygame.draw.rect(screen, (60, 60, 60), (bx, by, bubble_w, bubble_h), width=1, border_radius=4)

                # Small triangle tail pointing down to character
                tail_x = bx + bubble_w // 2 - 4
                tail_y = by + bubble_h - 1
                pygame.draw.polygon(screen, (255, 255, 245),
                                    [(tail_x, tail_y), (tail_x + 4, tail_y + 5), (tail_x + 8, tail_y)])

                # Bubble text
                bubble_label = _render_text(display_line, scale=1, color=(40, 40, 40))
                screen.blit(bubble_label, (bx + 7, by + 4))

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
