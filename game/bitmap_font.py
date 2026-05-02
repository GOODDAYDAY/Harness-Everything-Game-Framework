#!/usr/bin/env python3
"""Pixel bitmap font renderer for Pixel Werewolf.

Generates pixel-perfect text using a 5\u00d77 bitmap font definition,
then scales it up with NEAREST-neighbour interpolation.
No external font files needed.
"""

from __future__ import annotations

from typing import Optional

import pygame

# ── 5x7 bitmap font data ────────────────────────────────────────────
# Each character is a 5-wide x 7-high bitmap stored as a tuple of 7 ints.
# Bit 0 (LSB) = leftmost pixel.  Bits 0-4 used (5 bits per row).
# Inspired by Chicago / classic system bitmap fonts.

FONT_5X7: dict[int, tuple[int, ...]] = {
    # Uppercase letters
    ord('A'): (0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    ord('B'): (0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    ord('C'): (0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110),
    ord('D'): (0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110),
    ord('E'): (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    ord('F'): (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    ord('G'): (0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01110),
    ord('H'): (0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    ord('I'): (0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    ord('J'): (0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100),
    ord('K'): (0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    ord('L'): (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    ord('M'): (0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    ord('N'): (0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001),
    ord('O'): (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    ord('P'): (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    ord('Q'): (0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    ord('R'): (0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    ord('S'): (0b01110, 0b10001, 0b10000, 0b01110, 0b00001, 0b10001, 0b01110),
    ord('T'): (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    ord('U'): (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    ord('V'): (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    ord('W'): (0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001),
    ord('X'): (0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    ord('Y'): (0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100),
    ord('Z'): (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),

    # Lowercase letters
    ord('a'): (0b00000, 0b00000, 0b01110, 0b00001, 0b01111, 0b10001, 0b01111),
    ord('b'): (0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b10001, 0b11110),
    ord('c'): (0b00000, 0b00000, 0b01110, 0b10001, 0b10000, 0b10001, 0b01110),
    ord('d'): (0b00001, 0b00001, 0b01111, 0b10001, 0b10001, 0b10001, 0b01111),
    ord('e'): (0b00000, 0b00000, 0b01110, 0b10001, 0b11111, 0b10000, 0b01110),
    ord('f'): (0b00110, 0b01001, 0b01000, 0b11100, 0b01000, 0b01000, 0b01000),
    ord('g'): (0b00000, 0b01111, 0b10001, 0b10001, 0b01111, 0b00001, 0b01110),
    ord('h'): (0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b10001, 0b10001),
    ord('i'): (0b00100, 0b00000, 0b01100, 0b00100, 0b00100, 0b00100, 0b01110),
    ord('j'): (0b00010, 0b00000, 0b00110, 0b00010, 0b00010, 0b10010, 0b01100),
    ord('k'): (0b10000, 0b10000, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010),
    ord('l'): (0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    ord('m'): (0b00000, 0b00000, 0b11010, 0b10101, 0b10101, 0b10001, 0b10001),
    ord('n'): (0b00000, 0b00000, 0b11110, 0b10001, 0b10001, 0b10001, 0b10001),
    ord('o'): (0b00000, 0b00000, 0b01110, 0b10001, 0b10001, 0b10001, 0b01110),
    ord('p'): (0b00000, 0b00000, 0b11110, 0b10001, 0b10001, 0b11110, 0b10000),
    ord('q'): (0b00000, 0b00000, 0b01111, 0b10001, 0b10001, 0b01111, 0b00001),
    ord('r'): (0b00000, 0b00000, 0b10110, 0b11001, 0b10000, 0b10000, 0b10000),
    ord('s'): (0b00000, 0b00000, 0b01110, 0b10000, 0b01110, 0b00001, 0b11110),
    ord('t'): (0b01000, 0b01000, 0b11100, 0b01000, 0b01000, 0b01001, 0b00110),
    ord('u'): (0b00000, 0b00000, 0b10001, 0b10001, 0b10001, 0b10001, 0b01111),
    ord('v'): (0b00000, 0b00000, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    ord('w'): (0b00000, 0b00000, 0b10001, 0b10001, 0b10101, 0b10101, 0b01010),
    ord('x'): (0b00000, 0b00000, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001),
    ord('y'): (0b00000, 0b00000, 0b10001, 0b10001, 0b01111, 0b00001, 0b01110),
    ord('z'): (0b00000, 0b00000, 0b11111, 0b00010, 0b00100, 0b01000, 0b11111),

    # Digits
    ord('0'): (0b01110, 0b10011, 0b10101, 0b10101, 0b10101, 0b11001, 0b01110),
    ord('1'): (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    ord('2'): (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111),
    ord('3'): (0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110),
    ord('4'): (0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    ord('5'): (0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110),
    ord('6'): (0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    ord('7'): (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    ord('8'): (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    ord('9'): (0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100),

    # Punctuation & symbols
    ord(' '): (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000),
    ord('.'): (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100),
    ord(','): (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100, 0b01000),
    ord('!'): (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100),
    ord('?'): (0b01110, 0b10001, 0b00001, 0b00110, 0b00100, 0b00000, 0b00100),
    ord(':'): (0b00000, 0b00100, 0b00000, 0b00000, 0b00000, 0b00100, 0b00000),
    ord(';'): (0b00000, 0b00100, 0b00000, 0b00000, 0b00000, 0b00100, 0b01000),
    ord("'"): (0b00100, 0b00100, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000),
    ord('"'): (0b01010, 0b01010, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000),
    ord('-'): (0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000),
    ord('_'): (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b11111),
    ord('+'): (0b00000, 0b00000, 0b00100, 0b01110, 0b00100, 0b00000, 0b00000),
    ord('='): (0b00000, 0b00000, 0b11111, 0b00000, 0b11111, 0b00000, 0b00000),
    ord('/'): (0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000),
    ord('\\'): (0b10000, 0b01000, 0b01000, 0b00100, 0b00010, 0b00010, 0b00001),
    ord('('): (0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010),
    ord(')'): (0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000),
    ord('['): (0b01110, 0b01000, 0b01000, 0b01000, 0b01000, 0b01000, 0b01110),
    ord(']'): (0b01110, 0b00010, 0b00010, 0b00010, 0b00010, 0b00010, 0b01110),
    ord('{'): (0b00010, 0b00100, 0b00100, 0b01000, 0b00100, 0b00100, 0b00010),
    ord('}'): (0b01000, 0b00100, 0b00100, 0b00010, 0b00100, 0b00100, 0b01000),
    ord('<'): (0b00000, 0b00010, 0b00100, 0b01000, 0b00100, 0b00010, 0b00000),
    ord('>'): (0b00000, 0b01000, 0b00100, 0b00010, 0b00100, 0b01000, 0b00000),
    ord('|'): (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    ord('~'): (0b00000, 0b00000, 0b01010, 0b10101, 0b00000, 0b00000, 0b00000),
    ord('`'): (0b01000, 0b00100, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000),
    ord('@'): (0b01110, 0b10001, 0b10111, 0b10101, 0b10111, 0b10000, 0b01110),
    ord('#'): (0b01010, 0b01010, 0b11111, 0b01010, 0b11111, 0b01010, 0b01010),
    ord('$'): (0b00100, 0b01111, 0b10100, 0b01110, 0b00101, 0b11110, 0b00100),
    ord('%'): (0b11001, 0b11010, 0b00010, 0b00100, 0b01000, 0b01011, 0b10011),
    ord('&'): (0b01100, 0b10010, 0b10100, 0b01100, 0b10101, 0b10010, 0b01101),
    ord('*'): (0b00000, 0b00100, 0b10101, 0b01110, 0b10101, 0b00100, 0b00000),
    ord('^'): (0b00100, 0b01010, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000),
}

# Character metrics
CHAR_W = 5
CHAR_H = 7
CHAR_SPACING = 1  # pixels between characters
LINE_SPACING = 2  # pixels between lines

# Cached per-font-size surfaces
_cache: dict[tuple[int, tuple[int, int, int]], pygame.Surface] = {}


def _render_char(code: int, scale: int, color: tuple[int, int, int]) -> pygame.Surface:
    """Render a single character at the given scale."""
    bitmap = FONT_5X7.get(code)
    if bitmap is None:
        # Render a transparent placeholder for unknown chars
        surf = pygame.Surface((CHAR_W * scale, CHAR_H * scale), pygame.SRCALPHA)
        # Draw a faint outline so the missing glyph is visible during development
        if scale >= 3:
            for x in range(CHAR_W * scale):
                for y in range(CHAR_H * scale):
                    if x == 0 or x == CHAR_W * scale - 1 or y == 0 or y == CHAR_H * scale - 1:
                        surf.set_at((x, y), color)
        return surf

    # Create small surface and scale up
    small = pygame.Surface((CHAR_W, CHAR_H), pygame.SRCALPHA)
    small.fill((0, 0, 0, 0))
    for row in range(CHAR_H):
        bits = bitmap[row]
        for col in range(CHAR_W):
            if bits & (1 << (CHAR_W - 1 - col)):
                small.set_at((col, row), color)

    if scale == 1:
        return small
    return pygame.transform.scale(small, (CHAR_W * scale, CHAR_H * scale))


def _measure_text(text: str, scale: int) -> tuple[int, int]:
    """Return (width, height) of the rendered text at given scale."""
    lines = text.split("\n")
    max_line_w = 0
    for line in lines:
        w = sum(
            CHAR_W * scale + CHAR_SPACING * scale
            for ch in line
        )
        if line:
            w -= CHAR_SPACING * scale  # no spacing after last char
        max_line_w = max(max_line_w, w)
    h = len(lines) * (CHAR_H * scale + LINE_SPACING * scale) - (LINE_SPACING * scale if lines else 0)
    return (max_line_w, max(h, CHAR_H * scale))


def render_text(
    text: str,
    scale: int = 1,
    color: tuple[int, int, int] = (255, 255, 255),
    shadow: Optional[tuple[int, int, int]] = None,
) -> pygame.Surface:
    """Render pixel text at given scale.  scale=1 -> ~5x7 px per char.

    Args:
        text: String to render. Supports \\n for newlines.
        scale: Integer multiplier for each pixel (1=5x7, 2=10x14, 3=15x21, etc.)
        color: RGB color for the text.
        shadow: If set, renders a dark shadow offset by 1px (scaled).

    Returns:
        A pygame Surface with transparent background.
    """
    if not text:
        surf = pygame.Surface((0, 0), pygame.SRCALPHA)
        return surf

    # Normalize known non-ASCII chars
    text = (
        text.replace("\u2605", "*")   # star → *
        .replace("\u2713", "v")        # checkmark → v
        .replace("\u2717", "x")        # X mark → x
        .replace("\u2660", "S")        # spade → S
        .replace("\u2665", "H")        # heart → H
        .replace("\u2666", "D")        # diamond → D
        .replace("\u2663", "C")        # club → C
        # Map common game emoji to ASCII symbols
        .replace("\U0001f3ae", "[G]")  # video game
        .replace("\U0001f6e1", "[.]")  # shield
        .replace("\U0001f52e", "<>")   # crystal ball
        .replace("\U0001f3f0", "[C]")  # castle
        .replace("\U0001f4a5", "!!")   # explosion
        .replace("\U0001f4aa", "=>")   # flex
        .replace("\U0001f44d", "[y]")  # thumbs up
        .replace("\U0001f525", "^^")   # fire
        .replace("\U0001f480", "%]")   # skull
        .replace("\u2603", "[*]")      # snowman
        .replace("\u2600", "(S)")      # sun
        .replace("\u2601", "~" )       # cloud
        .replace("\u2615", "(c)")      # coffee
        .replace("\U0001f319", "(C)")  # crescent moon
        .replace("\U0001f308", "<->")  # rainbow
        .replace("\ufe0f", "")         # remove variation selector
        .replace("\u200d", "")         # remove zero-width joiner
    )
    # Strip any remaining non-ASCII
    text = "".join(ch if ord(ch) < 128 else "?" for ch in text)

    if shadow:
        # Render shadow first, offset by 1 pixel
        shadow_surf = render_text(text, scale, shadow, shadow=None)
        text_surf = render_text(text, scale, color, shadow=None)
        w = max(shadow_surf.get_width(), text_surf.get_width()) + scale
        h = max(shadow_surf.get_height(), text_surf.get_height()) + scale
        result = pygame.Surface((w, h), pygame.SRCALPHA)
        result.blit(shadow_surf, (scale, scale))
        result.blit(text_surf, (0, 0))
        return result

    lines = text.split("\n")
    total_w, total_h = _measure_text(text, scale)
    if total_w == 0 or total_h == 0:
        return pygame.Surface((1, 1), pygame.SRCALPHA)

    surf = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))

    y_offset = 0
    for line in lines:
        x_offset = 0
        for ch in line:
            char_surf = _render_char(ord(ch), scale, color)
            surf.blit(char_surf, (x_offset, y_offset))
            x_offset += CHAR_W * scale + CHAR_SPACING * scale
        y_offset += CHAR_H * scale + LINE_SPACING * scale

    return surf


def preload_text(text: str, scale: int, color: tuple[int, int, int]) -> pygame.Surface:
    """Render and cache text for reuse (e.g., static labels)."""
    key = (scale, color, text)
    if key not in _cache:
        _cache[key] = render_text(text, scale, color)
    return _cache[key]


def clear_cache() -> None:
    """Clear the render cache."""
    _cache.clear()
