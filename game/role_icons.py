#!/usr/bin/env python3
"""16x16 pixel-art role icons for the sidebar player list."""

from __future__ import annotations

import pygame

from game.roles import Role

ICON_W = 16
ICON_H = 16

# Cache for generated icons
_icon_cache: dict[str, pygame.Surface] = {}


def _new_icon() -> pygame.Surface:
    """Create a new transparent 16x16 icon surface."""
    surf = pygame.Surface((ICON_W, ICON_H), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    return surf


def _set_px(surf: pygame.Surface, x: int, y: int, color: tuple[int, int, int] | tuple[int, int, int, int]) -> None:
    if 0 <= x < ICON_W and 0 <= y < ICON_H:
        surf.set_at((x, y), color)


def _fill(surf: pygame.Surface, x1: int, y1: int, x2: int, y2: int, color) -> None:
    for x in range(x1, x2 + 1):
        for y in range(y1, y2 + 1):
            _set_px(surf, x, y, color)


def _draw_villager_icon() -> pygame.Surface:
    """Generic villager icon - simple person silhouette."""
    s = _new_icon()
    c = (180, 200, 220)
    # Head
    _fill(s, 5, 1, 10, 5, c)
    # Body
    _fill(s, 4, 6, 11, 11, c)
    # Arms
    _fill(s, 2, 6, 3, 9, c)
    _fill(s, 12, 6, 13, 9, c)
    # Legs
    _fill(s, 5, 12, 7, 14, c)
    _fill(s, 8, 12, 10, 14, c)
    return s


def _draw_werewolf_icon() -> pygame.Surface:
    """Werewolf icon - wolf head silhouette."""
    s = _new_icon()
    c = (180, 60, 60)
    # Ears
    _fill(s, 1, 1, 3, 4, c)
    _fill(s, 12, 1, 14, 4, c)
    # Head
    _fill(s, 3, 3, 12, 9, c)
    # Inner face
    _fill(s, 4, 4, 11, 8, (140, 40, 40))
    # Eyes (yellow/green glow)
    _set_px(s, 5, 5, (255, 220, 80))
    _set_px(s, 6, 5, (255, 220, 80))
    _set_px(s, 9, 5, (255, 220, 80))
    _set_px(s, 10, 5, (255, 220, 80))
    # Snout
    _fill(s, 5, 8, 10, 10, c)
    _fill(s, 6, 7, 9, 7, c)
    # Mouth
    _fill(s, 5, 10, 10, 11, (200, 40, 40))
    # Fangs
    _set_px(s, 6, 11, (255, 255, 255))
    _set_px(s, 9, 11, (255, 255, 255))
    return s


def _draw_seer_icon() -> pygame.Surface:
    """Seer icon - all-seeing eye."""
    s = _new_icon()
    c = (100, 160, 255)
    # Outer eye
    _fill(s, 2, 4, 13, 11, (60, 80, 160))
    # Inner eye
    _fill(s, 3, 5, 12, 10, c)
    # Pupil
    _fill(s, 6, 5, 9, 10, (40, 60, 140))
    # Iris glow
    _set_px(s, 7, 7, (200, 230, 255))
    _set_px(s, 8, 7, (200, 230, 255))
    # Sparkle
    _set_px(s, 5, 6, (255, 255, 255))
    _set_px(s, 10, 6, (255, 255, 255))
    return s


def _draw_guard_icon() -> pygame.Surface:
    """Guard icon - shield."""
    s = _new_icon()
    c = (80, 160, 220)
    # Shield shape
    _fill(s, 2, 2, 13, 3, c)
    _fill(s, 1, 3, 14, 5, c)
    _fill(s, 1, 6, 14, 10, c)
    _fill(s, 2, 11, 13, 12, c)
    _fill(s, 3, 13, 12, 14, c)
    # Shield inner
    _fill(s, 4, 4, 11, 11, (60, 100, 180))
    # Cross emblem
    _fill(s, 6, 4, 9, 11, c)
    _fill(s, 4, 6, 11, 9, c)
    return s


def _draw_witch_icon() -> pygame.Surface:
    """Witch icon - potion bottle."""
    s = _new_icon()
    # Bottle neck
    _fill(s, 6, 1, 9, 3, (160, 100, 200))
    # Bottle body
    _fill(s, 4, 3, 11, 9, (160, 100, 200))
    # Bottle bottom
    _fill(s, 3, 9, 12, 12, (160, 100, 200))
    # Liquid inside
    _fill(s, 5, 4, 10, 8, (100, 220, 120))
    # Bubbles
    _set_px(s, 6, 5, (180, 255, 200))
    _set_px(s, 8, 7, (180, 255, 200))
    # Cork
    _fill(s, 6, 0, 9, 1, (180, 150, 100))
    return s


def _draw_hunter_icon() -> pygame.Surface:
    """Hunter icon - bow and arrow."""
    s = _new_icon()
    c = (200, 140, 60)
    # Bow arc
    for i in range(5):
        _set_px(s, 1 + i, 2 + i, c)
        _set_px(s, 1 + i, 12 - i, c)
    _fill(s, 5, 5, 5, 9, c)
    # Bowstring
    _fill(s, 1, 2, 6, 12, (180, 160, 120))
    # Arrow
    _fill(s, 7, 6, 14, 8, (160, 120, 60))
    # Arrowhead
    _set_px(s, 14, 7, (200, 200, 200))
    _set_px(s, 15, 7, (200, 200, 200))
    _set_px(s, 14, 6, (200, 200, 200))
    _set_px(s, 14, 8, (200, 200, 200))
    # Fletching
    _fill(s, 7, 5, 8, 6, (200, 60, 60))
    _fill(s, 7, 8, 8, 9, (200, 60, 60))
    return s


def _draw_town_crier_icon() -> pygame.Surface:
    """Town crier icon - bell."""
    s = _new_icon()
    c = (200, 180, 80)
    # Bell body
    _fill(s, 3, 3, 12, 9, c)
    _fill(s, 4, 2, 11, 2, c)
    # Bell opening
    _fill(s, 2, 9, 13, 11, c)
    # Clapper
    _fill(s, 6, 11, 9, 13, (180, 160, 60))
    # Bell top knob
    _fill(s, 7, 1, 8, 2, c)
    # Sound wave lines
    _set_px(s, 1, 5, (255, 220, 100))
    _set_px(s, 0, 6, (255, 220, 100))
    _set_px(s, 14, 5, (255, 220, 100))
    _set_px(s, 15, 6, (255, 220, 100))
    return s


# Timer icon for night phase
ICON_WATCH = _new_icon()
_fill(ICON_WATCH, 4, 1, 11, 1, (200, 200, 200))
_fill(ICON_WATCH, 3, 2, 12, 2, (200, 200, 200))
_fill(ICON_WATCH, 2, 3, 13, 12, (200, 200, 200))
_fill(ICON_WATCH, 3, 13, 12, 13, (200, 200, 200))
_fill(ICON_WATCH, 4, 14, 11, 14, (200, 200, 200))
# Inner face
_fill(ICON_WATCH, 4, 3, 11, 12, (40, 40, 50))
# Hands
_fill(ICON_WATCH, 7, 3, 8, 8, (200, 200, 200))
_fill(ICON_WATCH, 7, 7, 12, 8, (200, 200, 200))

# Dead icon (skull)
ICON_DEAD = _new_icon()
_fill(ICON_DEAD, 4, 3, 11, 10, (140, 140, 145))
_fill(ICON_DEAD, 3, 5, 12, 10, (140, 140, 145))
# Eyes
_set_px(ICON_DEAD, 5, 6, (30, 30, 35))
_set_px(ICON_DEAD, 6, 6, (30, 30, 35))
_set_px(ICON_DEAD, 9, 6, (30, 30, 35))
_set_px(ICON_DEAD, 10, 6, (30, 30, 35))
# Nose
_set_px(ICON_DEAD, 7, 8, (30, 30, 35))
_set_px(ICON_DEAD, 8, 8, (30, 30, 35))
# Mouth
_fill(ICON_DEAD, 5, 9, 10, 10, (30, 30, 35))

# Sheriff badge
ICON_SHERIFF = _new_icon()
_fill(ICON_SHERIFF, 2, 3, 13, 12, (200, 180, 80))
_fill(ICON_SHERIFF, 3, 4, 12, 11, (180, 160, 60))
# Star shape
_fill(ICON_SHERIFF, 7, 4, 8, 5, (255, 220, 100))
_fill(ICON_SHERIFF, 5, 6, 10, 7, (255, 220, 100))
_fill(ICON_SHERIFF, 7, 8, 8, 9, (255, 220, 100))
_fill(ICON_SHERIFF, 7, 6, 8, 8, (255, 220, 100))


_ROLE_ICON_FUNCS = {
    Role.VILLAGER: _draw_villager_icon,
    Role.WEREWOLF: _draw_werewolf_icon,
    Role.SEER: _draw_seer_icon,
    Role.GUARD: _draw_guard_icon,
    Role.WITCH: _draw_witch_icon,
    Role.HUNTER: _draw_hunter_icon,
    Role.TOWN_CRIER: _draw_town_crier_icon,
}


def get_role_icon(role: Role) -> pygame.Surface:
    """Get the 16x16 pixel icon for a role."""
    key = f"role_icon_{role.value}"
    if key in _icon_cache:
        return _icon_cache[key]
    func = _ROLE_ICON_FUNCS.get(role, _draw_villager_icon)
    icon = func()
    _icon_cache[key] = icon
    return icon


def get_icon_scaled(role: Role, scale: int = 2) -> pygame.Surface:
    """Get a scaled version (32x32) of the role icon for the sidebar."""
    icon = get_role_icon(role)
    return pygame.transform.scale(icon, (ICON_W * scale, ICON_H * scale))
