#!/usr/bin/env python3
"""Tests for renderer.py — pixel-art village rendering."""

import sys
sys.path.insert(0, '.')

import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'

import pygame

from game.renderer import (
    VillageRenderer,
    WeatherState,
    TILE_SIZE, GRID_COLS, GRID_ROWS,
    VIEWPORT_W, VIEWPORT_H,
    PLAYER_HOMES, MEETING_POSITIONS,
    Palette,
    _build_village_map,
    get_tile,
)
from game.roles import Role


def _make_player(index, alive=True, name=None, role=None):
    """Create a mock player object for testing."""
    if role is None:
        role = list(Role)[index % len(Role)]
    return type('Player', (), {
        'index': index,
        'alive': alive,
        'name': name or f'P{index}',
        'role': role,
    })()


class TestVillageRenderer:
    """Test the VillageRenderer class."""

    @classmethod
    def setup_class(cls):
        pygame.display.set_mode((VIEWPORT_W, VIEWPORT_H))
        pygame.font.init()

    def setup_method(self):
        self.renderer = VillageRenderer()

    # ── Initialisation ──

    def test_init_creates_tile_map(self):
        """Renderer initialises with a 32x18 tile map."""
        r = self.renderer
        assert len(r._tile_map) == GRID_ROWS
        assert len(r._tile_map[0]) == GRID_COLS
        for row in r._tile_map:
            assert len(row) == GRID_COLS

    def test_init_bg_caches_are_none(self):
        """Day/night backgrounds are lazily generated."""
        assert self.renderer._bg_day is None
        assert self.renderer._bg_night is None

    def test_init_player_list_empty(self):
        """No players set by default."""
        assert self.renderer._players == []

    def test_init_current_positions_empty(self):
        """No interpolated positions until set_players is called."""
        assert self.renderer._current_positions == []

    def test_init_day_mode_false(self):
        """Default mode is night (is_day_mode=False)."""
        assert self.renderer._is_day_mode is False

    # ── get_background ──

    def test_get_background_day_returns_surface(self):
        """get_background(False) returns a day surface."""
        bg = self.renderer.get_background(False)
        assert isinstance(bg, pygame.Surface)
        # Background is now the full world size, larger than viewport
        world_w = GRID_COLS * TILE_SIZE
        world_h = GRID_ROWS * TILE_SIZE
        assert bg.get_size() == (world_w, world_h)

    def test_get_background_night_returns_surface(self):
        """get_background(True) returns a night surface."""
        bg = self.renderer.get_background(True)
        assert isinstance(bg, pygame.Surface)
        # Background is now the full world size, larger than viewport
        world_w = GRID_COLS * TILE_SIZE
        world_h = GRID_ROWS * TILE_SIZE
        assert bg.get_size() == (world_w, world_h)

    def test_get_background_caches_day(self):
        """Day background is cached after first call."""
        self.renderer.get_background(False)
        assert self.renderer._bg_day is not None

    def test_get_background_caches_night(self):
        """Night background is cached after first call."""
        self.renderer.get_background(True)
        assert self.renderer._bg_night is not None

    def test_get_background_reuses_cache(self):
        """Second call returns the same cached surface."""
        bg1 = self.renderer.get_background(False)
        bg2 = self.renderer.get_background(False)
        assert bg1 is bg2

    def test_get_background_day_and_night_differ(self):
        """Day and night surfaces are different objects."""
        day = self.renderer.get_background(False)
        night = self.renderer.get_background(True)
        assert day is not night

    # ── set_players ──

    def test_set_players_with_valid_list(self):
        """set_players stores the player list."""
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        assert len(self.renderer._players) == 12

    def test_set_players_initialises_positions(self):
        """set_players creates home positions for each player."""
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        assert len(self.renderer._current_positions) == 12

    def test_set_players_positions_match_homes(self):
        """Initial positions equal the PLAYER_HOMES entries."""
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        for i, (row, col) in enumerate(self.renderer._current_positions):
            expected = PLAYER_HOMES[i]
            assert row == float(expected[0]) and col == float(expected[1]), \
                f"Player {i}: expected {expected}, got ({row}, {col})"

    def test_set_players_empty_list(self):
        """set_players with empty list clears positions."""
        self.renderer.set_players([])
        assert self.renderer._players == []

    def test_set_players_none_in_list(self):
        """set_players handles None entries."""
        players = [_make_player(i) if i < 6 else None for i in range(12)]
        self.renderer.set_players(players)
        assert len(self.renderer._players) == 12
        # Render with None entries should not crash
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        self.renderer.render(screen, night=False)

    # ── set_day_mode ──

    def test_set_day_mode_day_changes_flag(self):
        """set_day_mode(True) sets is_day_mode to True."""
        self.renderer.set_day_mode(True, 0.0)
        assert self.renderer._is_day_mode is True

    def test_set_day_mode_night_changes_flag(self):
        """set_day_mode(False) sets is_day_mode to False."""
        self.renderer.set_day_mode(True, 0.0)
        self.renderer.set_day_mode(False, 0.0)
        assert self.renderer._is_day_mode is False

    def test_set_day_mode_animates_toward_meeting(self):
        """After set_day_mode(True), players move toward meeting positions."""
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        self.renderer.set_day_mode(True, 10.0)  # Large dt to complete animation
        for i, (row, col) in enumerate(self.renderer._current_positions):
            meet_row, meet_col = MEETING_POSITIONS[i]
            assert abs(row - meet_row) < 0.001, \
                f"Player {i}: expected ({meet_row},{meet_col}), got ({row},{col})"

    def test_set_day_mode_multiple_calls(self):
        """set_day_mode can be called repeatedly without error."""
        for _ in range(5):
            self.renderer.set_day_mode(True, 0.5)
            self.renderer.set_day_mode(False, 0.5)
        # Should not raise

    # ── render ──

    def test_render_day_mode(self):
        """render() works in day mode with players."""
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        self.renderer.render(screen, night=False, time=0.0)

    def test_render_night_mode(self):
        """render() works in night mode with players."""
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        self.renderer.render(screen, night=True, time=0.0)

    def test_render_empty_players(self):
        """render() works with no players set."""
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        self.renderer.render(screen, night=False, time=0.0)

    def test_render_all_dead_players(self):
        """render() works when all players are dead."""
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        players = [_make_player(i, alive=False) for i in range(12)]
        self.renderer.set_players(players)
        self.renderer.render(screen, night=False, time=0.0)

    def test_render_partial_players(self):
        """render() works with fewer than 12 players."""
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        players = [_make_player(i) for i in range(3)]
        self.renderer.set_players(players)
        self.renderer.render(screen, night=False, time=0.0)

    def test_render_with_time_animation(self):
        """render() works with animated time > 0."""
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        self.renderer.render(screen, night=True, time=5.0)

    def test_render_called_twice(self):
        """render() can be called multiple times."""
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        self.renderer.render(screen, night=False, time=0.0)
        self.renderer.render(screen, night=True, time=1.0)

    # ── action_fx tests ──

    def test_action_fx_can_be_appended(self):
        """_action_fx list accepts (player_idx, fx_type, duration) tuples."""
        self.renderer._action_fx.append((0, "seer", 1.5))
        assert len(self.renderer._action_fx) == 1
        idx, fx, dur = self.renderer._action_fx[0]
        assert idx == 0
        assert fx == "seer"
        assert dur == 1.5

    def test_action_fx_renders_with_effects(self):
        """render() handles action_fx entries without crashing."""
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        self.renderer._action_fx.append((0, "seer", 1.5))
        self.renderer._action_fx.append((2, "kill", 1.5))
        self.renderer._action_fx.append((4, "save", 1.5))
        self.renderer._action_fx.append((6, "poison", 1.5))
        self.renderer.render(screen, night=False, time=0.0)

    def test_action_fx_all_types_drawn(self):
        """Each FX type renders without error."""
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        for i, fx_type in enumerate(["seer", "kill", "save", "poison"]):
            self.renderer._action_fx.append((i, fx_type, 1.0))
        self.renderer.render(screen, night=False, time=0.0)

    def test_action_fx_multiple_on_same_player(self):
        """Multiple FX on the same player render without error."""
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        self.renderer._action_fx.append((0, "seer", 1.0))
        self.renderer._action_fx.append((0, "kill", 1.5))
        self.renderer.render(screen, night=False, time=0.0)

    # ── Weather tests ──

    def test_weather_default_is_clear(self):
        """Renderer starts with CLEAR weather."""
        assert self.renderer.get_weather() == WeatherState.CLEAR

    def test_weather_set_and_transition(self):
        """set_weather triggers a smooth transition."""
        self.renderer.set_weather(WeatherState.RAIN)
        assert self.renderer._weather_target == WeatherState.RAIN
        assert self.renderer.get_weather() == WeatherState.CLEAR  # still current
        # Advance past blend speed
        self.renderer.update_fx(0.6)
        assert self.renderer._weather == WeatherState.RAIN
        assert self.renderer.get_weather() == WeatherState.RAIN

    def test_weather_transition_accumulates(self):
        """Partial dt accumulations work correctly."""
        self.renderer.set_weather(WeatherState.FOG)
        self.renderer.update_fx(0.25)  # half of 0.5s blend
        assert self.renderer._weather == WeatherState.CLEAR
        assert self.renderer._weather_blend > 0.0
        self.renderer.update_fx(0.25)  # total = 0.5s, completes transition
        assert self.renderer._weather == WeatherState.FOG
        assert self.renderer._weather_blend == 0.0

    def test_weather_same_state_no_transition(self):
        """Setting same weather does nothing."""
        self.renderer.set_weather(WeatherState.CLEAR)
        assert self.renderer._weather_blend == 0.0
        assert self.renderer._weather == WeatherState.CLEAR

    def test_weather_rain_initializes_particles(self):
        """Rain creates 200 particles eagerly on init."""
        assert len(self.renderer._rain_particles) == 200

    def test_weather_rain_particles_update(self):
        """Rain particles move when updated."""
        self.renderer.set_weather(WeatherState.RAIN)
        self.renderer.update_fx(0.6)  # complete transition + tick
        y_before = self.renderer._rain_particles[0][1]
        self.renderer.update_fx(0.016)  # 16ms frame
        y_after = self.renderer._rain_particles[0][1]
        assert y_after > y_before, "Raindrop should fall downward"

    def test_weather_rain_renders_no_crash(self):
        """Rain weather renders without error."""
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        self.renderer.set_weather(WeatherState.RAIN)
        self.renderer.update_fx(0.6)
        self.renderer.render(screen, night=False, time=0.0)

    def test_weather_fog_renders_no_crash(self):
        """Fog weather renders without error."""
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        self.renderer.set_weather(WeatherState.FOG)
        self.renderer.update_fx(0.6)
        self.renderer.render(screen, night=False, time=0.0)

    def test_weather_clear_renders_no_overlay(self):
        """Clear weather does not draw overlay."""
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        self.renderer.render(screen, night=False, time=0.0)
        # Should just work — no overlay drawn

    def test_weather_cycle_through_all_states(self):
        """Cycling through all weather states works."""
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        for state in [WeatherState.RAIN, WeatherState.FOG, WeatherState.CLEAR,
                      WeatherState.RAIN, WeatherState.CLEAR]:
            self.renderer.set_weather(state)
            self.renderer.update_fx(0.6)
            assert self.renderer._weather == state
            self.renderer.render(screen, night=False, time=0.0)

    def test_weather_render_night_with_rain(self):
        """Night + rain renders without error."""
        screen = pygame.Surface((VIEWPORT_W, VIEWPORT_H))
        players = [_make_player(i) for i in range(12)]
        self.renderer.set_players(players)
        self.renderer.set_weather(WeatherState.RAIN)
        self.renderer.update_fx(0.6)
        self.renderer.render(screen, night=True, time=0.0)


class TestBuildVillageMap:
    """Tests for the village map generation."""

    def test_map_dimensions(self):
        """Village map is 18 rows x 32 columns."""
        grid = _build_village_map()
        assert len(grid) == GRID_ROWS
        assert len(grid[0]) == GRID_COLS

    def test_has_variety(self):
        """The village map uses at least 10 distinct tile type values."""
        grid = _build_village_map()
        all_tiles = {t for row in grid for t in row}
        assert len(all_tiles) >= 10, \
            f"Only {len(all_tiles)} tile types found: {all_tiles}"

    def test_has_building_tiles(self):
        """The village map contains building tiles (type >= 4)."""
        grid = _build_village_map()
        has_buildings = any(t >= 4 for row in grid for t in row)
        assert has_buildings, "No building tiles found in village map"

    def test_deterministic(self):
        """Same seed produces the same map."""
        grid1 = _build_village_map()
        grid2 = _build_village_map()
        assert grid1 == grid2, "Map generation is not deterministic"


class TestPalette:
    """Tests for colour palette."""

    def test_palette_has_required_colors(self):
        """Palette contains all expected colour attributes."""
        required = [
            'sky', 'sky_distant', 'grass_light', 'grass_dark',
            'path', 'path_dark', 'wood_light', 'wood_dark',
            'roof_red', 'roof_dark', 'wall_cream', 'wall_dark',
        ]
        for key in required:
            assert hasattr(Palette, key), f"Palette missing '{key}'"

    def test_palette_colors_are_pairs(self):
        """All palette values are (day, night) tuples of RGB."""
        for name in dir(Palette):
            if name.startswith('_'):
                continue
            val = getattr(Palette, name)
            if isinstance(val, tuple) and len(val) == 2:
                for variant in val:
                    assert isinstance(variant, tuple) and len(variant) == 3, \
                        f"{name}={val}: expected (R,G,B) tuples"
                    assert all(0 <= c <= 255 for c in variant), \
                        f"{name}={val}: out-of-range component"


class TestConstants:
    """Test that hard invariants are maintained."""

    def test_viewport_dimensions(self):
        """Viewport must be 2560x1440."""
        assert VIEWPORT_W == 2560
        assert VIEWPORT_H == 1440

    def test_tile_size_is_80(self):
        """Tile size must be 80px."""
        assert TILE_SIZE == 80

    def test_grid_dimensions_larger_than_viewport(self):
        """Grid cols/rows are larger than viewport / tile_size (camera support)."""
        # Expanded map for camera scrolling: must be larger than viewport
        assert GRID_COLS > VIEWPORT_W // TILE_SIZE  # was 32, now 48
        assert GRID_ROWS > VIEWPORT_H // TILE_SIZE  # was 18, now 27
        # Must be integers
        assert GRID_COLS * TILE_SIZE == GRID_COLS * 80
        assert GRID_ROWS * TILE_SIZE == GRID_ROWS * 80

    def test_player_homes_count(self):
        """There must be 12 player home positions."""
        assert len(PLAYER_HOMES) == 12

    def test_meeting_positions_count(self):
        """There must be 12 meeting positions."""
        assert len(MEETING_POSITIONS) == 12

    def test_home_positions_in_grid_bounds(self):
        """All home positions must be within the 18x32 grid."""
        for i, (row, col) in enumerate(PLAYER_HOMES):
            assert 0 <= row < GRID_ROWS, f"Home {i}: row {row} out of bounds"
            assert 0 <= col < GRID_COLS, f"Home {i}: col {col} out of bounds"

    def test_meeting_positions_in_grid_bounds(self):
        """All meeting positions must be within the 18x32 grid."""
        for i, (row, col) in enumerate(MEETING_POSITIONS):
            assert 0 <= row < GRID_ROWS, f"Meet {i}: row {row} out of bounds"
            assert 0 <= col < GRID_COLS, f"Meet {i}: col {col} out of bounds"

    def test_home_positions_unique(self):
        """All home positions are unique."""
        assert len(set(PLAYER_HOMES)) == len(PLAYER_HOMES), \
            "Duplicate home positions found"

    def test_meeting_positions_unique(self):
        """All meeting positions are unique."""
        assert len(set(MEETING_POSITIONS)) == len(MEETING_POSITIONS), \
            "Duplicate meeting positions found"


class TestGetTile:
    """Tests for the get_tile function."""

    def test_get_tile_day_returns_surface(self):
        """get_tile returns a valid Surface for any tile type in day mode."""
        for tile_type in range(20):
            surf = get_tile(tile_type, night=False)
            assert isinstance(surf, pygame.Surface)
            assert surf.get_size() == (TILE_SIZE, TILE_SIZE)

    def test_get_tile_night_returns_surface(self):
        """get_tile returns a valid Surface for any tile type in night mode."""
        for tile_type in range(20):
            surf = get_tile(tile_type, night=True)
            assert isinstance(surf, pygame.Surface)
            assert surf.get_size() == (TILE_SIZE, TILE_SIZE)

    def test_get_tile_caches(self):
        """get_tile caches results for (tile_type, night) pairs."""
        surf1 = get_tile(0, False)
        surf2 = get_tile(0, False)
        assert surf1 is surf2, "get_tile should cache and return same object"

    def test_get_tile_day_and_night_differ(self):
        """get_tile returns different surfaces for day vs night."""
        surf_day = get_tile(3, False)
        surf_night = get_tile(3, True)
        assert surf_day is not surf_night

    def test_get_tile_same_type_same_size(self):
        """All tiles of the same type have the same size."""
        for tile_type in range(20):
            day = get_tile(tile_type, False)
            night = get_tile(tile_type, True)
            assert day.get_size() == night.get_size()
