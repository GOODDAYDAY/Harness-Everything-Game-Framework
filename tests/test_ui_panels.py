#!/usr/bin/env python3
"""Tests for ui_panels.py — multi-resolution layout, colours, and rendering helpers."""

import sys
sys.path.insert(0, '.')

import game.ui_panels as ui


class TestRecalcLayout:
    """Test that recalc_layout produces sensible values for various resolutions.

    NOTE: we must read module attributes via 'ui.SIDEBAR_X' every time because
    integers are immutable — importing them as local names would give stale copies
    after recalc_layout updates the module globals.
    """

    def teardown_method(self):
        """Restore default 2560x1440 after each test so other tests aren't affected."""
        ui.recalc_layout(2560, 1440)

    def _check_layout_invariants(self, sw, sh):
        """Assert invariants that must hold for any resolution."""
        # Sidebar must be fully on-screen
        assert ui.SIDEBAR_X >= 0, f"SIDEBAR_X={ui.SIDEBAR_X} < 0"
        assert ui.SIDEBAR_Y >= 0, f"SIDEBAR_Y={ui.SIDEBAR_Y} < 0"
        assert ui.SIDEBAR_W > 0, f"SIDEBAR_W={ui.SIDEBAR_W} <= 0"
        assert ui.SIDEBAR_RIGHT == sw, f"SIDEBAR_RIGHT={ui.SIDEBAR_RIGHT} != sw={sw}"
        assert ui.SIDEBAR_X + ui.SIDEBAR_W <= sw, (
            f"Sidebar overflows: {ui.SIDEBAR_X} + {ui.SIDEBAR_W} = {ui.SIDEBAR_X + ui.SIDEBAR_W} > {sw}"
        )

        # Player list parameters must be positive and within screen
        assert ui.LIST_START > 0, f"LIST_START={ui.LIST_START} <= 0"
        assert ui.LIST_SPACING > 0, f"LIST_SPACING={ui.LIST_SPACING} <= 0"
        assert ui.LOG_START_Y > 0, f"LOG_START_Y={ui.LOG_START_Y} <= 0"
        assert ui.LOG_SPACING > 0, f"LOG_SPACING={ui.LOG_SPACING} <= 0"

        # Log section must fit within the screen
        assert ui.LOG_START_Y < sh, f"LOG_START_Y={ui.LOG_START_Y} >= sh={sh}"

        # Screen dimensions must be stored
        assert ui.SCREEN_W == sw, f"SCREEN_W={ui.SCREEN_W} != sw={sw}"
        assert ui.SCREEN_H == sh, f"SCREEN_H={ui.SCREEN_H} != sh={sh}"

        # Font scales must be reasonable (at least 1, at most 5)
        for name, val in [
            ("FONT_SCALE_BANNER", ui.FONT_SCALE_BANNER),
            ("FONT_SCALE_INDICATOR", ui.FONT_SCALE_INDICATOR),
            ("FONT_SCALE_PLAYER", ui.FONT_SCALE_PLAYER),
            ("FONT_SCALE_LOG", ui.FONT_SCALE_LOG),
            ("FONT_SCALE_SMALL", ui.FONT_SCALE_SMALL),
        ]:
            assert 1 <= val <= 5, f"{name}={val} out of range [1, 5]"

        # Sidebar must be a reasonable proportion of screen (10%-40%)
        sidebar_ratio = ui.SIDEBAR_W / sw
        assert 0.10 <= sidebar_ratio <= 0.40, (
            f"Sidebar ratio={sidebar_ratio:.3f} outside [0.10, 0.40]"
        )

        # Player list must have room for all 12 players
        max_players_in_area = (ui.LOG_START_Y - ui.LIST_START) // ui.LIST_SPACING
        assert max_players_in_area >= 12, (
            f"Only room for {max_players_in_area} players in list area "
            f"(need 12, LIST_START={ui.LIST_START}, LOG_START_Y={ui.LOG_START_Y}, "
            f"LIST_SPACING={ui.LIST_SPACING})"
        )

    def test_default_2560x1440(self):
        """Default resolution must give the standard design values."""
        ui.recalc_layout(2560, 1440)
        assert ui.SCREEN_W == 2560
        assert ui.SCREEN_H == 1440
        assert ui.WIN_SCALE == 1.0
        assert ui.SIDEBAR_W == 660, f"SIDEBAR_W={ui.SIDEBAR_W}"
        assert ui.SIDEBAR_X == 1900, f"SIDEBAR_X={ui.SIDEBAR_X}"
        assert ui.SIDEBAR_Y == 15, f"SIDEBAR_Y={ui.SIDEBAR_Y}"  # max(8, 15 * 1.0)
        assert ui.LIST_START == 80
        self._check_layout_invariants(2560, 1440)

    def test_hd_1920x1080(self):
        """Minimum supported resolution: 1920x1080."""
        ui.recalc_layout(1920, 1080)
        assert ui.SCREEN_W == 1920
        assert ui.SCREEN_H == 1080
        # base = 1080/1440 = 0.75 -> < 0.8, so font scales reduce
        assert ui.FONT_SCALE_BANNER == 2
        assert ui.FONT_SCALE_INDICATOR == 1
        assert ui.FONT_SCALE_PLAYER == 1
        # Sidebar should be proportionally smaller
        self._check_layout_invariants(1920, 1080)

    def test_ultrawide_3440x1440(self):
        """Ultrawide monitor: wider but same height."""
        ui.recalc_layout(3440, 1440)
        assert ui.WIN_SCALE == 1.0  # height unchanged
        self._check_layout_invariants(3440, 1440)

    def test_medium_1600x900(self):
        """Medium resolution: base ≈ 0.625 -> < 0.8, small fonts."""
        ui.recalc_layout(1600, 900)
        assert ui.FONT_SCALE_BANNER == 2
        assert ui.FONT_SCALE_INDICATOR == 1
        assert ui.FONT_SCALE_PLAYER == 1
        assert ui.FONT_SCALE_LOG == 1
        assert ui.FONT_SCALE_SMALL == 1
        self._check_layout_invariants(1600, 900)

    def test_edge_case_very_small(self):
        """Small window (~1024x768) must not produce invalid values."""
        ui.recalc_layout(1024, 768)
        assert ui.WIN_SCALE < 0.6
        assert ui.FONT_SCALE_BANNER == 2  # minimum
        self._check_layout_invariants(1024, 768)

    def test_large_4k_3840x2160(self):
        """4K: base ≈ 1.5, all layout values must scale up."""
        ui.recalc_layout(3840, 2160)
        assert ui.WIN_SCALE == 1.5
        self._check_layout_invariants(3840, 2160)

    def test_call_twice(self):
        """Calling recalc_layout twice must work gracefully (idempotent-like)."""
        ui.recalc_layout(1920, 1080)
        w1, h1, ws1 = ui.SCREEN_W, ui.SCREEN_H, ui.WIN_SCALE
        sx1, sw1 = ui.SIDEBAR_X, ui.SIDEBAR_W
        ui.recalc_layout(1920, 1080)
        # Results should be identical (same inputs -> same outputs)
        assert ui.SCREEN_W == w1
        assert ui.SCREEN_H == h1
        assert ui.WIN_SCALE == ws1
        assert ui.SIDEBAR_X == sx1
        assert ui.SIDEBAR_W == sw1
        self._check_layout_invariants(1920, 1080)

    def test_tall_narrow_screen(self):
        """Portrait orientation (1080x1920) must produce valid layout."""
        ui.recalc_layout(1080, 1920)
        assert ui.WIN_SCALE > 1.0
        assert ui.SIDEBAR_RIGHT == 1080
        self._check_layout_invariants(1080, 1920)
