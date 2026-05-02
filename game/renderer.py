#!/usr/bin/env python3
"""Pixel-art village renderer for Pixel Werewolf.

Generates a 32x18 tile map (80px tiles -> 2560x1440 viewport)
with procedurally drawn pixel-art tiles. No external assets needed.
"""

from __future__ import annotations

from typing import Optional

import pygame

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
    sky: tuple[tuple[int, int, int], tuple[int, int, int]] = ((180, 210, 240), (10, 15, 40))
    sky_distant: tuple[tuple[int, int, int], tuple[int, int, int]] = ((150, 190, 220), (8, 12, 35))
    grass_light: tuple[tuple[int, int, int], tuple[int, int, int]] = ((140, 200, 80), (30, 60, 30))
    grass_dark: tuple[tuple[int, int, int], tuple[int, int, int]] = ((100, 170, 60), (20, 45, 20))
    path: tuple[tuple[int, int, int], tuple[int, int, int]] = ((180, 160, 120), (50, 45, 35))
    path_dark: tuple[tuple[int, int, int], tuple[int, int, int]] = ((150, 130, 90), (40, 35, 25))
    wood_light: tuple[tuple[int, int, int], tuple[int, int, int]] = ((170, 130, 60), (60, 45, 20))
    wood_dark: tuple[tuple[int, int, int], tuple[int, int, int]] = ((130, 90, 40), (45, 35, 15))
    roof_red: tuple[tuple[int, int, int], tuple[int, int, int]] = ((190, 70, 50), (70, 25, 15))
    roof_dark: tuple[tuple[int, int, int], tuple[int, int, int]] = ((140, 50, 35), (50, 18, 10))
    wall_cream: tuple[tuple[int, int, int], tuple[int, int, int]] = ((230, 210, 170), (80, 70, 50))
    wall_dark: tuple[tuple[int, int, int], tuple[int, int, int]] = ((200, 180, 140), (70, 60, 40))
    window_glow: tuple[int, int, int] = (255, 220, 130)  # same day/night, always warm
    window_dark: tuple[int, int, int] = (40, 35, 25)
    tree_trunk: tuple[tuple[int, int, int], tuple[int, int, int]] = ((100, 70, 40), (35, 25, 15))
    tree_canopy: tuple[tuple[int, int, int], tuple[int, int, int]] = ((70, 140, 40), (20, 50, 15))
    tree_canopy_light: tuple[tuple[int, int, int], tuple[int, int, int]] = ((100, 170, 60), (30, 60, 20))
    water: tuple[tuple[int, int, int], tuple[int, int, int]] = ((80, 140, 180), (15, 30, 60))
    water_light: tuple[tuple[int, int, int], tuple[int, int, int]] = ((120, 170, 200), (25, 45, 80))
    fence: tuple[tuple[int, int, int], tuple[int, int, int]] = ((160, 120, 60), (55, 40, 20))
    well: tuple[tuple[int, int, int], tuple[int, int, int]] = ((130, 120, 100), (45, 40, 35))
    flower: tuple[tuple[int, int, int], tuple[int, int, int]] = ((240, 100, 120), (100, 30, 40))
    stone: tuple[tuple[int, int, int], tuple[int, int, int]] = ((160, 150, 140), (55, 50, 45))

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
    grid[13][6] = T_FLOWER
    grid[13][22] = T_FLOWER

    # Stones
    grid[10][5] = T_STONE
    grid[10][6] = T_STONE
    grid[11][22] = T_STONE
    grid[11][23] = T_STONE

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
        # Subtle grass texture
        for x in range(0, TILE_SIZE, 4):
            for y in range(0, TILE_SIZE, 4):
                if (x + y) % 8 == 0:
                    surf.set_at((x + 1, y + 1), c("grass_dark"))
                    surf.set_at((x + 3, y + 1), c("grass_dark"))

    elif tile_type == T_PATH:
        surf.fill(c("path"))
        # Dirt texture
        for _ in range(20):
            px = (_ * 37 + 13) % TILE_SIZE
            py = (_ * 23 + 7) % TILE_SIZE
            surf.set_at((px, py), c("path_dark"))

    elif tile_type == T_PATH_DARK:
        surf.fill(c("path_dark"))
        for _ in range(15):
            px = (_ * 31 + 11) % TILE_SIZE
            py = (_ * 17 + 5) % TILE_SIZE
            surf.set_at((px, py), c("path"))

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
                surf.set_at((sx, sy), (brightness, brightness, brightness + 20))

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

    return surf


def get_tile(tile_type: int, night: bool) -> pygame.Surface:
    """Get a cached tile surface, generating if needed."""
    key = (tile_type, night)
    if key not in _tile_cache:
        _tile_cache[key] = _draw_tile(tile_type, night)
    return _tile_cache[key]


# ── Village renderer ───────────────────────────────────────────────

class VillageRenderer:
    """Renders the pixel-art village background."""

    def __init__(self) -> None:
        self._tile_map = _build_village_map()
        # Pre-generate night and day background surfaces
        self._bg_day: Optional[pygame.Surface] = None
        self._bg_night: Optional[pygame.Surface] = None

    def _build_background(self, night: bool) -> pygame.Surface:
        """Build the full background surface from the tile map."""
        bg = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        for row_idx, row in enumerate(self._tile_map):
            for col_idx, tile_type in enumerate(row):
                tile_surf = get_tile(tile_type, night)
                bg.blit(tile_surf, (col_idx * TILE_SIZE, row_idx * TILE_SIZE))
        return bg

    def get_background(self, night: bool) -> pygame.Surface:
        """Get cached background surface for day or night."""
        if night:
            if self._bg_night is None:
                self._bg_night = self._build_background(True)
            return self._bg_night
        else:
            if self._bg_day is None:
                self._bg_day = self._build_background(False)
            return self._bg_day

    def render(self, screen: pygame.Surface, night: bool) -> None:
        """Draw the village background onto the screen."""
        bg = self.get_background(night)
        screen.blit(bg, (0, 0))

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
