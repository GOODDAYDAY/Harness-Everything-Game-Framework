#!/usr/bin/env python3
"""32x64 pixel-art player character sprites for Pixel Werewolf.

Each sprite is a detailed pixel-art character with role-specific
accessories and colour variety. Dead players show as ghosts/tombstones.
"""

from __future__ import annotations

import pygame

from game.roles import Role

# Sprite dimensions (doubled from original 16x32)
CHAR_W = 32
CHAR_H = 64

# Colour palettes for variety
SKIN_TONES = [
    (255, 224, 189),  # Light
    (241, 194, 150),  # Fair
    (224, 172, 105),  # Olive
    (198, 134, 66),   # Tan
    (141, 85, 36),    # Brown
]

HAIR_COLORS = [
    (40, 30, 20),     # Dark brown
    (60, 45, 30),     # Brown
    (180, 130, 50),   # Blonde
    (30, 25, 20),     # Black
    (160, 80, 40),    # Red / auburn
    (200, 190, 180),  # Grey
    (140, 120, 100),  # Ash
    (90, 70, 50),     # Chestnut
]

SHIRT_COLORS = [
    (60, 120, 200),   # Blue
    (180, 60, 60),    # Red
    (50, 160, 80),    # Green
    (200, 180, 60),   # Yellow
    (140, 80, 180),   # Purple
    (200, 120, 60),   # Orange
    (60, 160, 160),   # Teal
    (180, 100, 140),  # Pink
    (100, 100, 100),  # Grey
    (160, 120, 80),   # Tan
    (40, 100, 140),   # Navy
    (140, 160, 80),   # Olive
]

PANTS_COLORS = [
    (50, 40, 35),     # Brown
    (40, 45, 55),     # Dark blue
    (60, 55, 50),     # Grey
    (30, 30, 30),     # Black
    (55, 45, 35),     # Tan
]

SHOE_COLOR = (30, 25, 20)

# Role-specific accent colours
ROLE_ACCENTS = {
    Role.VILLAGER: None,
    Role.WEREWOLF: (180, 40, 40),    # Red eyes/fur
    Role.SEER: (60, 100, 220),       # Blue mystic
    Role.GUARD: (60, 140, 200),      # Steel blue
    Role.WITCH: (140, 60, 180),      # Purple
    Role.HUNTER: (180, 120, 40),     # Orange-brown
    Role.TOWN_CRIER: (200, 170, 60), # Gold
}

# Hat types per role
HAT_TYPES = {
    Role.VILLAGER: "none",
    Role.WEREWOLF: "ears",
    Role.SEER: "hood",
    Role.GUARD: "helmet",
    Role.WITCH: "witch_hat",
    Role.HUNTER: "cap",
    Role.TOWN_CRIER: "visor",
}


# Cache for generated sprites to avoid regenerating
_sprite_cache: dict[str, pygame.Surface] = {}


def _make_cache_key(role: Role, skin_idx: int, hair_idx: int, shirt_idx: int, pants_idx: int, alive: bool) -> str:
    return f"{role.value}_{skin_idx}_{hair_idx}_{shirt_idx}_{pants_idx}_{alive}"


def set_px(surf: pygame.Surface, x: int, y: int, color: tuple[int, int, int] | tuple[int, int, int, int]) -> None:
    """Set a pixel if within bounds."""
    if 0 <= x < CHAR_W and 0 <= y < CHAR_H:
        surf.set_at((x, y), color)


def _fill_rect(surf: pygame.Surface, x1: int, y1: int, x2: int, y2: int, color) -> None:
    """Fill a rectangular area with a colour."""
    for x in range(x1, x2 + 1):
        for y in range(y1, y2 + 1):
            set_px(surf, x, y, color)


def _draw_hat(surf: pygame.Surface, hat_type: str, color, accent_color) -> None:
    """Draw a hat/head accessory on top of the character (y=0-10)."""
    if hat_type == "none":
        return
    elif hat_type == "ears":
        # Werewolf ears
        ear_col = color
        # Left ear
        surf.set_at((5, 1), ear_col)
        surf.set_at((4, 2), ear_col)
        surf.set_at((5, 2), ear_col)
        surf.set_at((6, 2), ear_col)
        surf.set_at((5, 3), (200, 180, 160))  # inner ear
        # Right ear
        surf.set_at((26, 1), ear_col)
        surf.set_at((25, 2), ear_col)
        surf.set_at((26, 2), ear_col)
        surf.set_at((27, 2), ear_col)
        surf.set_at((26, 3), (200, 180, 160))  # inner ear
        # Fur tufts on top
        for x in range(10, 13):
            surf.set_at((x, 0), ear_col)
        for x in range(19, 22):
            surf.set_at((x, 0), ear_col)
    elif hat_type == "hood":
        # Seer hood - pointed (face drawn first, hood on top)
        hood_col = (40, 60, 140)
        for x in range(8, 24):
            for y in range(1, 8):
                dx = abs(x - 16)
                if dx < 4 + y:
                    # Skip face area so skin shows through
                    if 10 <= x <= 21 and 4 <= y <= 7:
                        continue
                    surf.set_at((x, y), hood_col)
    elif hat_type == "helmet":
        # Guard helmet
        hel_col = (140, 150, 160)
        # Dome
        for x in range(7, 25):
            for y in range(0, 6):
                dx = abs(x - 16)
                if dx < 8 - y:
                    surf.set_at((x, y), hel_col)
        # Visor slit
        _fill_rect(surf, 10, 5, 21, 6, (80, 90, 100))
        # Plume
        plume_col = (200, 50, 50)
        for x in range(14, 18):
            surf.set_at((x, 0), plume_col)
        surf.set_at((15, -1) if False else (15, 0), plume_col)  # nop
        surf.set_at((15, 1), plume_col)
    elif hat_type == "witch_hat":
        # Witch hat - tall pointed
        hat_col = (50, 30, 60)
        band_col = (160, 100, 40)
        # Cone
        for x in range(9, 23):
            for y in range(0, 8):
                dx = abs(x - 16)
                max_dx = max(2, 6 - y)
                if y == 0:
                    if x in (15, 16, 17):
                        surf.set_at((x, y), hat_col)
                elif dx < max_dx:
                    surf.set_at((x, y), hat_col)
        # Brim
        _fill_rect(surf, 5, 7, 26, 9, hat_col)
        # Band
        _fill_rect(surf, 8, 4, 23, 6, band_col)
        # Buckle
        _fill_rect(surf, 14, 4, 17, 6, (200, 180, 100))
    elif hat_type == "cap":
        # Hunter cap
        cap_col = (120, 100, 60)
        # Dome
        for x in range(8, 24):
            for y in range(1, 5):
                dx = abs(x - 16)
                if dx < 7 - y:
                    surf.set_at((x, y), cap_col)
        # Brim front
        _fill_rect(surf, 8, 4, 23, 5, cap_col)
        _fill_rect(surf, 6, 5, 25, 6, cap_col)
        # Feather
        feather_col = (200, 60, 60)
        for x in range(23, 27):
            for y in range(1, 4):
                surf.set_at((x, y), feather_col)
        surf.set_at((26, 3), feather_col)
    elif hat_type == "visor":
        # Town crier visor/hat
        hat_col = (180, 160, 50)
        # Dome
        for x in range(9, 23):
            for y in range(1, 5):
                dx = abs(x - 16)
                if dx < 6:
                    surf.set_at((x, y), hat_col)
        # Visor brim
        _fill_rect(surf, 7, 4, 24, 5, hat_col)
        _fill_rect(surf, 5, 5, 26, 7, hat_col)
        # Bell on top
        bell_col = (200, 180, 100)
        surf.set_at((15, 0), bell_col)
        surf.set_at((16, 0), bell_col)
        surf.set_at((17, 0), bell_col)
        surf.set_at((15, 1), bell_col)
        surf.set_at((17, 1), bell_col)


def _generate_alive_sprite(body_color, hair_color, skin_color, role: Role) -> pygame.Surface:
    """Generate a 32x64 pixel-art character sprite with role-specific details."""
    surf = pygame.Surface((CHAR_W, CHAR_H), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))  # transparent

    accent = ROLE_ACCENTS.get(role)
    hat_type = HAT_TYPES.get(role, "none")

    # === Head & Hair ===
    # Hair (back/top layer - full head)
    for x in range(5, 27):
        for y in range(0, 18):
            if x in (5, 6, 24, 25) and y < 3:
                continue
            if y == 0 and x not in range(10, 22):
                continue
            if y < 16:
                surf.set_at((x, y), hair_color)

    # Face/skin (over hair for front-facing head)
    for x in range(7, 25):
        for y in range(6, 18):
            if x in (7, 24) and y < 8:
                continue
            if y >= 16:
                continue
            surf.set_at((x, y), skin_color)

    # Eyes
    eye_col = (40, 30, 20)
    surf.set_at((11, 11), eye_col)
    surf.set_at((12, 11), eye_col)
    surf.set_at((19, 11), eye_col)
    surf.set_at((20, 11), eye_col)

    # Eyebrows
    brow_col = hair_color
    for x in range(10, 14):
        surf.set_at((x, 9), brow_col)
    for x in range(18, 22):
        surf.set_at((x, 9), brow_col)

    # Mouth
    mouth_col = (180, 120, 100)
    for x in range(13, 19):
        surf.set_at((x, 14), mouth_col)

    # Nose
    nose_col = (220, 180, 150)
    surf.set_at((15, 12), nose_col)
    surf.set_at((16, 12), nose_col)
    surf.set_at((15, 13), nose_col)
    surf.set_at((16, 13), nose_col)

    # === Neck ===
    neck_col = skin_color
    for x in range(12, 20):
        surf.set_at((x, 17), neck_col)
        surf.set_at((x, 18), neck_col)

    # === Hat (drawn on top of head) ===
    _draw_hat(surf, hat_type, hair_color, accent)

    # === Body / Torso ===
    # Main shirt
    for x in range(5, 27):
        for y in range(19, 38):
            surf.set_at((x, y), body_color)

    # Collar
    collar_col = (min(body_color[0] + 30, 255), min(body_color[1] + 30, 255), min(body_color[2] + 30, 255))
    for x in range(11, 21):
        surf.set_at((x, 19), collar_col)
        surf.set_at((x, 20), collar_col)

    # Role-specific accessory on body
    if role == Role.GUARD:
        # Shield emblem on chest
        shield_col = (180, 180, 200)
        for x in range(13, 19):
            for y in range(24, 31):
                dx = abs(x - 16)
                if dx < 2:
                    surf.set_at((x, y), shield_col)
                elif dx < 3 and y > 25:
                    surf.set_at((x, y), shield_col)
    elif role == Role.SEER:
        # Mystic eye on chest
        eye_col = (100, 150, 255)
        _fill_rect(surf, 15, 27, 16, 28, eye_col)
        surf.set_at((14, 28), eye_col)
        surf.set_at((17, 28), eye_col)
    elif role == Role.WITCH:
        # Potion pocket
        pot_col = (160, 80, 200)
        _fill_rect(surf, 12, 28, 14, 32, pot_col)
        _fill_rect(surf, 13, 27, 14, 28, (200, 180, 100))
    elif role == Role.HUNTER:
        # Quiver strap
        strap_col = (120, 80, 40)
        for x in range(22, 26):
            for y in range(22, 38):
                surf.set_at((x, y), strap_col)
        # Arrow tips visible
        tip_col = (180, 180, 190)
        surf.set_at((24, 22), tip_col)
        surf.set_at((24, 26), tip_col)
        surf.set_at((24, 30), tip_col)
    elif role == Role.TOWN_CRIER:
        # Scroll/badge
        badge_col = (200, 180, 80)
        _fill_rect(surf, 14, 25, 18, 30, badge_col)
        surf.set_at((13, 26), badge_col)
        surf.set_at((19, 26), badge_col)

    # === Arms (skin colour) ===
    # Left arm
    for x in range(2, 6):
        for y in range(20, 32):
            surf.set_at((x, y), skin_color)
    # Right arm
    for x in range(26, 30):
        for y in range(20, 32):
            surf.set_at((x, y), skin_color)

    # Hands
    for x in range(2, 6):
        for y in range(32, 36):
            if x in (2, 5) and y < 33:
                continue
            surf.set_at((x, y), skin_color)
    for x in range(26, 30):
        for y in range(32, 36):
            if x in (26, 29) and y < 33:
                continue
            surf.set_at((x, y), skin_color)

    # === Legs ===
    pants_color = (50, 40, 35)  # default brown pants
    # Left leg
    for x in range(8, 15):
        for y in range(38, 54):
            surf.set_at((x, y), pants_color)
    # Right leg
    for x in range(17, 24):
        for y in range(38, 54):
            surf.set_at((x, y), pants_color)

    # Belt
    belt_col = (40, 30, 20)
    for x in range(7, 25):
        surf.set_at((x, 37), belt_col)
        surf.set_at((x, 38), belt_col)
    # Buckle
    buckle_col = (200, 180, 100)
    surf.set_at((14, 37), buckle_col)
    surf.set_at((15, 37), buckle_col)
    surf.set_at((16, 37), buckle_col)
    surf.set_at((17, 37), buckle_col)
    surf.set_at((14, 38), buckle_col)
    surf.set_at((17, 38), buckle_col)

    # === Shoes ===
    # Left shoe
    for x in range(6, 16):
        for y in range(54, 62):
            surf.set_at((x, y), SHOE_COLOR)
    # Right shoe
    for x in range(17, 26):
        for y in range(54, 62):
            surf.set_at((x, y), SHOE_COLOR)

    # Soul/life indicator - small sparkle dot
    if accent:
        # Small role-coloured badge on shoulder
        for x in range(4, 7):
            for y in range(20, 23):
                surf.set_at((x, y), accent)

    return surf


def _generate_dead_sprite(role: Role) -> pygame.Surface:
    """Generate a 32x64 tombstone/ghost sprite for dead players."""
    surf = pygame.Surface((CHAR_W, CHAR_H), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))

    accent = ROLE_ACCENTS.get(role)

    # Ghostly figure (semi-transparent white/grey)
    ghost_col = (200, 200, 210, 140)
    for x in range(5, 27):
        for y in range(4, 38):
            if x in (5, 6, 24, 25) and y < 8:
                continue
            if y < 6 and x not in range(10, 22):
                continue
            surf.set_at((x, y), ghost_col)

    # Ghostly eyes (dark hollows)
    surf.set_at((11, 14), (80, 80, 90))
    surf.set_at((12, 14), (80, 80, 90))
    surf.set_at((19, 14), (80, 80, 90))
    surf.set_at((20, 14), (80, 80, 90))

    # Ghostly mouth
    surf.set_at((14, 18), (80, 80, 90))
    surf.set_at((15, 18), (80, 80, 90))
    surf.set_at((16, 18), (80, 80, 90))
    surf.set_at((17, 18), (80, 80, 90))

    # Role-coloured ghostly glow
    if accent:
        # Ghostly glow overlay
        for x in range(8, 24):
            for y in range(6, 36):
                existing = surf.get_at((x, y))
                if existing[3] > 0:
                    # Preserve existing ghost alpha, role-tinted
                    surf.set_at((x, y), (accent[0], accent[1], accent[2], existing[3]))
        # Ghostly role emblem
        if role == Role.WEREWOLF:
            for x in range(14, 18):
                for y in range(42, 46):
                    surf.set_at((x, y), (180, 40, 40, 120))
        elif role == Role.GUARD:
            for x in range(12, 20):
                for y in range(40, 44):
                    surf.set_at((x, y), (60, 140, 200, 120))
        elif role == Role.SEER:
            for x in range(13, 19):
                surf.set_at((x, 42), (60, 100, 220, 120))

    # Tombstone base (bottom portion)
    stone_col = (140, 135, 130)
    for x in range(4, 28):
        for y in range(48, 64):
            surf.set_at((x, y), stone_col)

    # Tombstone arch
    for x in range(4, 28):
        for y in range(42, 48):
            dx = abs(x - 16)
            if dx < 12:
                surf.set_at((x, y), stone_col)

    # ✝ cross on tombstone
    cross_col = (180, 175, 170)
    for x in range(13, 19):
        surf.set_at((x, 46), cross_col)
        surf.set_at((x, 47), cross_col)
        surf.set_at((x, 48), cross_col)
    for y in range(44, 52):
        surf.set_at((14, y), cross_col)
        surf.set_at((15, y), cross_col)
        surf.set_at((16, y), cross_col)
        surf.set_at((17, y), cross_col)

    # Role initial on tombstone
    if role:
        initials = {
            Role.VILLAGER: "V",
            Role.WEREWOLF: "W",
            Role.SEER: "S",
            Role.GUARD: "G",
            Role.WITCH: "X",
            Role.HUNTER: "H",
            Role.TOWN_CRIER: "C",
        }
        initial = initials.get(role, "?")
        # Simple pixel letter
        letter_map = {
            "V": [(0,0),(1,0),(2,0),(3,0),(4,0),(0,1),(4,1),(0,2),(4,2),(0,3),(4,3),(0,4),(4,4),(1,5),(2,5),(3,5)],
            "W": [(0,0),(4,0),(0,1),(4,1),(0,2),(4,2),(0,3),(1,3),(2,3),(3,3),(4,3),(1,4),(3,4),(1,5),(2,5),(3,5)],
            "S": [(0,0),(1,0),(2,0),(3,0),(4,0),(0,1),(4,1),(0,2),(3,2),(4,2),(0,3),(4,3),(0,4),(4,4),(0,5),(1,5),(2,5),(3,5),(4,5)],
            "G": [(1,0),(2,0),(3,0),(0,1),(4,1),(0,2),(4,2),(0,3),(3,3),(4,3),(4,4),(0,5),(1,5),(2,5),(3,5),(4,5)],
            "X": [(0,0),(4,0),(1,1),(3,1),(2,2),(1,3),(3,3),(0,4),(4,4),(0,5),(4,5)],
            "H": [(0,0),(4,0),(0,1),(4,1),(0,2),(4,2),(0,3),(1,3),(2,3),(3,3),(4,3),(0,4),(4,4),(0,5),(4,5)],
            "C": [(1,0),(2,0),(3,0),(0,1),(4,1),(0,2),(4,2),(0,3),(4,3),(0,4),(4,4),(1,5),(2,5),(3,5)],
        }
        pixels = letter_map.get(initial, [])
        off_x = 12
        off_y = 52
        for (px, py) in pixels:
            surf.set_at((off_x + px, off_y + py), cross_col)

    return surf


def get_character_sprite(player_idx: int, role: Role, alive: bool) -> pygame.Surface:
    """Get or generate a character sprite for the given player index and role.

    Uses cached sprites colour-selected by player index for variety.
    """
    skin_idx = player_idx % len(SKIN_TONES)
    hair_idx = (player_idx * 3) % len(HAIR_COLORS)
    shirt_idx = player_idx % len(SHIRT_COLORS)
    pants_idx = (player_idx * 2) % len(PANTS_COLORS)

    # Dead players use a simpler cache key (role only + index for variety)
    if not alive:
        key = f"dead_{role.value}_{player_idx % 4}"
    else:
        key = _make_cache_key(role, skin_idx, hair_idx, shirt_idx, pants_idx, alive)

    if key in _sprite_cache:
        return _sprite_cache[key]

    if not alive:
        sprite = _generate_dead_sprite(role)
    else:
        body_color = SHIRT_COLORS[shirt_idx]
        hair_color = HAIR_COLORS[hair_idx]
        skin_color = SKIN_TONES[skin_idx]
        sprite = _generate_alive_sprite(body_color, hair_color, skin_color, role)

    _sprite_cache[key] = sprite
    return sprite


# Backward compatibility alias
def generate_player_sprite(player_idx: int, role: Role, alive: bool) -> pygame.Surface:
    """Backward-compatible wrapper."""
    return get_character_sprite(player_idx, role, alive)
