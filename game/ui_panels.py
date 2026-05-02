#!/usr/bin/env python3
"""Sidebar and HUD panel rendering for Pixel Werewolf.

Renders the information sidebar, player list, game log, phase indicators,
banners, instruction text, and other overlay UI elements for the game loop.

All functions take explicit screen/position parameters so the caller
controls where things go (no global state dependency for layout).
"""

from __future__ import annotations

import math
from collections import Counter

import pygame

from game.bitmap_font import render_text
from game.phases import GamePhase
from game.roles import Role
from game.text import _

# ── Default screen dimensions (will be overridden by recalc_layout) ──
SCREEN_W: int = 2560
SCREEN_H: int = 1440

# ── Layout constants (set by recalc_layout) ──
WIN_SCALE: float = 1.0
SIDEBAR_X: int = 1900
SIDEBAR_Y: int = 10
SIDEBAR_W: int = 660
SIDEBAR_RIGHT: int = 2560
LIST_START: int = 80
LIST_SPACING: int = 50
LOG_START_Y: int = 1100
LOG_SPACING: int = 20

# ── Font scaling ──
FONT_SCALE_BANNER: int = 3
FONT_SCALE_INDICATOR: int = 2
FONT_SCALE_PLAYER: int = 2
FONT_SCALE_LOG: int = 1
FONT_SCALE_SMALL: int = 1


def recalc_layout(sw: int, sh: int) -> None:
    """Recalculate layout constants for the given screen size.

    Call this whenever the window is resized, before any draw calls.
    """
    global SCREEN_W, SCREEN_H, WIN_SCALE
    global SIDEBAR_X, SIDEBAR_Y, SIDEBAR_W, SIDEBAR_RIGHT
    global LIST_START, LIST_SPACING, LOG_START_Y, LOG_SPACING
    global FONT_SCALE_BANNER, FONT_SCALE_INDICATOR, FONT_SCALE_PLAYER, FONT_SCALE_LOG, FONT_SCALE_SMALL

    SCREEN_W = sw
    SCREEN_H = sh

    # Scale based on height relative to 1440
    base = sh / 1440.0
    WIN_SCALE = base

    # Sidebar always occupies the right ~25% of the screen
    SIDEBAR_W = int(sw * 0.258)  # ~660 at 2560
    SIDEBAR_X = sw - SIDEBAR_W
    SIDEBAR_Y = max(8, int(15 * base))
    SIDEBAR_RIGHT = sw

    LIST_START = max(60, int(80 * base))
    LIST_SPACING = max(32, int(50 * base))
    LOG_START_Y = int(sh * 0.76)
    LOG_SPACING = max(14, int(20 * base))

    # Font scales reduce slightly at small resolutions
    if base < 0.8:
        FONT_SCALE_BANNER = 2
        FONT_SCALE_INDICATOR = 1
        FONT_SCALE_PLAYER = 1
        FONT_SCALE_LOG = 1
        FONT_SCALE_SMALL = 1
    elif base < 1.0:
        FONT_SCALE_BANNER = 3
        FONT_SCALE_INDICATOR = 2
        FONT_SCALE_PLAYER = 2
        FONT_SCALE_LOG = 1
        FONT_SCALE_SMALL = 1
    else:
        FONT_SCALE_BANNER = 3
        FONT_SCALE_INDICATOR = 2
        FONT_SCALE_PLAYER = 2
        FONT_SCALE_LOG = 1
        FONT_SCALE_SMALL = 1


# ── Colour palette ──
COLOR_SIDEBAR_BG = (15, 12, 8)
COLOR_SIDEBAR_BORDER = (60, 45, 30)
COLOR_ALIVE = (200, 220, 200)
COLOR_DEAD = (120, 100, 100)
COLOR_WEREWOLF = (220, 80, 80)
COLOR_VILLAGER = (120, 200, 120)
COLOR_SPECIAL = (200, 180, 100)
COLOR_SHERIFF = (255, 215, 0)
COLOR_PHASE_PILL_BG = (30, 25, 15)
COLOR_PHASE_PILL_BORDER = (120, 90, 40)
COLOR_PHASE_TEXT = (235, 210, 160)
COLOR_DAY_TEXT = (180, 200, 220)
COLOR_NIGHT_TEXT = (200, 160, 200)
COLOR_VOTE_HIGHLIGHT = (200, 150, 50)
COLOR_DEATH = (200, 60, 60)
COLOR_INSTRUCTION = (180, 200, 150)
COLOR_TEXT_DIM = (140, 130, 120)
COLOR_WARN = (220, 180, 60)
COLOR_TEXT = (200, 190, 170)

# ── Torn-paper edge effect pixels (repeating pattern) ──
_TORN_EDGE: list[int] = [0, -1, 0, 1, -1, 0, 2, -1, 0, 1, 0, -1, -2, 0, 1, 0]


def _draw_torn_edge(screen: pygame.Surface, x: int, y: int, w: int,
                    edge_color: tuple[int, int, int],
                    side: str = "bottom") -> None:
    """Draw a torn-paper edge effect along the bottom or top of a rect."""
    for dx in range(w):
        offset = _TORN_EDGE[(dx // 4) % len(_TORN_EDGE)]
        if side == "bottom":
            px, py = x + dx, y + offset
        else:
            px, py = x + dx, y - offset
        if 0 <= px < SCREEN_W and 0 <= py < SCREEN_H:
            screen.set_at((px, py), edge_color)


# ═══════════════════════════════════════════════════════════════
#   SIDEBAR BACKGROUND
# ═══════════════════════════════════════════════════════════════

def draw_sidebar_background(screen: pygame.Surface, x: int, y: int, w: int, h: int) -> None:
    """Draw the semi-transparent sidebar panel background."""
    # Main background
    bg = pygame.Surface((w, h), pygame.SRCALPHA)
    bg.fill((*COLOR_SIDEBAR_BG, 200))
    screen.blit(bg, (x, 0))

    # Left border line
    for i in range(h):
        brightness = max(0, min(255, 60 + int(math.sin(i * 0.05) * 10)))
        border_col = (brightness // 2, brightness // 3 - 5, brightness // 4 - 10)
        border_col = tuple(max(0, min(255, c)) for c in border_col)
        screen.set_at((x, i), border_col)

    # Bottom torn edge
    _draw_torn_edge(screen, x, h - 1, w, COLOR_SIDEBAR_BORDER, "bottom")


# ═══════════════════════════════════════════════════════════════
#   PHASE INDICATOR
# ═══════════════════════════════════════════════════════════════

def draw_phase_indicator(
    screen: pygame.Surface,
    phase: GamePhase,
    day: int,
    x: int,
    y: int,
    w: int,
    remain: float = -1.0,
    total: float = 1.0,
) -> None:
    """Draw a phase indicator badge (top of sidebar).

    Args:
        screen: Surface to draw on.
        phase: Current game phase.
        day: Current day number.
        x, y, w: Position in the sidebar.
        remain: Seconds remaining in this phase (negative = no timer shown).
        total: Total duration of this phase (for percentage calculation).
    """
    if phase == GamePhase.SETUP:
        text = _("setup")
    elif phase == GamePhase.GAME_OVER:
        text = _("game_over_short")
    else:
        prefix = _("phase_day_prefix") if phase.is_day else _("phase_night_prefix")
        raw = phase.display_name
        # Strip extra prefix from display name
        for pfx in ("Day \u2014 ", "Night \u2014 ", "\u767d\u5929 \u2014 ", "\u591c\u665a \u2014 "):
            if raw.startswith(pfx):
                raw = raw[len(pfx):]
                break
        text = f"{prefix} {day} \u00b7 {raw}"

    text_surf = render_text(text, scale=FONT_SCALE_INDICATOR, color=COLOR_PHASE_TEXT,
                             shadow=(20, 18, 10))
    tw, th = text_surf.get_size()

    # Build timer indicator string if remain >= 0
    timer_surf = None
    if remain >= 0.0 and phase not in (GamePhase.SETUP, GamePhase.GAME_OVER):
        ratio = remain / max(total, 0.1)
        # Colour shift from green → yellow → red as timer runs out
        if ratio > 0.5:
            # green → yellow (ratio 1.0→0.5)
            t = (ratio - 0.5) * 2.0  # 0→1
            tr = int(80 + 140 * t)
            tg = int(220 - 40 * t)
            tb = int(80 - 40 * t)
        else:
            # yellow → red (ratio 0.5→0.0)
            t = ratio * 2.0  # 0→1
            tr = int(220 + 35 * (1.0 - t))
            tg = int(180 * t)
            tb = int(40 * t)
        timer_color = (max(0, min(255, tr)), max(0, min(255, tg)), max(0, min(255, tb)))
        timer_text = f"{remain:.0f}s"
        timer_surf = render_text(timer_text, scale=FONT_SCALE_SMALL, color=timer_color,
                                  shadow=(10, 8, 5))

    # Pill width: accommodate main text + optional timer
    pill_pad_x = 16
    pill_pad_y = 6
    timer_gap = 0
    if timer_surf is not None:
        timer_gap = timer_surf.get_width() + 10
    pill_w = tw + pill_pad_x * 2 + timer_gap
    pill_h = th + pill_pad_y * 2
    pill = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
    pill.fill(COLOR_PHASE_PILL_BG + (200,))
    pygame.draw.rect(pill, COLOR_PHASE_PILL_BORDER, (0, 0, pill_w, pill_h), 2)
    pill.blit(text_surf, (pill_pad_x, pill_pad_y))

    if timer_surf is not None:
        timer_x = pill_pad_x + tw + 10
        timer_y = (pill_h - timer_surf.get_height()) // 2
        pill.blit(timer_surf, (timer_x, timer_y))

    # Position in sidebar (top center)
    bx = x + (w - pill_w) // 2
    screen.blit(pill, (bx, y))


# ═══════════════════════════════════════════════════════════════
#   PHASE INSTRUCTION TEXT
# ═══════════════════════════════════════════════════════════════

def draw_phase_instruction(
    screen: pygame.Surface,
    state,
    x: int,
    y: int,
) -> None:
    """Draw context-aware instruction text for the current phase."""
    phase = state.phase
    if phase == GamePhase.DAY_DISCUSSION:
        msg = _("phase_instruction_discussion")
    elif phase == GamePhase.DAY_VOTE:
        msg = _("phase_instruction_vote")
    elif phase == GamePhase.DAY_SHERIFF_ELECTION:
        msg = _("phase_instruction_sheriff")
    elif phase == GamePhase.NIGHT_GUARD:
        msg = _("phase_instruction_guard")
    elif phase == GamePhase.NIGHT_WEREWOLF:
        msg = _("phase_instruction_werewolf")
    elif phase == GamePhase.NIGHT_WITCH:
        msg = _("phase_instruction_witch")
    elif phase == GamePhase.NIGHT_SEER:
        msg = _("phase_instruction_seer")
    elif phase == GamePhase.DAY_TRIAL:
        msg = _("phase_instruction_trial")
    else:
        msg = ""

    if not msg:
        return

    text_surf = render_text(msg, scale=FONT_SCALE_SMALL, color=COLOR_INSTRUCTION,
                             shadow=(10, 15, 10))
    text_y = y + 55
    screen.blit(text_surf, (x + 10, text_y))


# ═══════════════════════════════════════════════════════════════
#   PLAYER LIST
# ═══════════════════════════════════════════════════════════════

def draw_player_list(
    screen: pygame.Surface,
    players,
    x: int,
    start_y: int,
    spacing: int,
    selected: int | None = None,
    phase: GamePhase | None = None,
    votes: dict | None = None,
) -> None:
    """Draw the player list in the sidebar."""
    y = start_y
    for p in players.players:
        # Determine color
        if not p.alive:
            name_color = COLOR_DEAD
            prefix = "[X] "
        elif selected is not None and p.index == selected:
            name_color = COLOR_VOTE_HIGHLIGHT
            prefix = "> "
        else:
            name_color = COLOR_ALIVE
            prefix = "  "

        # Sheriff badge
        sheriff_mark = "\u2605 " if p.is_sheriff else ""

        # Vote count — count how many votes this player received
        vote_suffix = ""
        if votes:
            _vote_counts = Counter(votes.values())
            if p.index in _vote_counts:
                vote_suffix = f" ({_vote_counts[p.index]})"

        name_str = f"{prefix}{sheriff_mark}{p.display_name}{vote_suffix}"
        text_surf = render_text(name_str, scale=FONT_SCALE_PLAYER, color=name_color,
                                 shadow=(5, 5, 5))
        screen.blit(text_surf, (x + 8, y))
        y += spacing


# ═══════════════════════════════════════════════════════════════
#   GAME LOG
# ═══════════════════════════════════════════════════════════════

def draw_game_log(
    screen: pygame.Surface,
    log_entries: list,
    x: int,
    start_y: int,
    spacing: int,
) -> None:
    """Draw the game log in the sidebar, most recent entries at the bottom."""
    max_lines = (SCREEN_H - start_y) // spacing - 1
    entries = log_entries[-max_lines:] if len(log_entries) > max_lines else log_entries

    y = start_y
    for entry in entries:
        if isinstance(entry, dict):
            msg = entry.get("message", "")
        else:
            msg = str(entry)

        text_surf = render_text(msg, scale=FONT_SCALE_LOG, color=(160, 150, 130),
                                 shadow=(5, 5, 5))
        screen.blit(text_surf, (x + 8, y))
        y += spacing


# ═══════════════════════════════════════════════════════════════
#   NARRATION HEADER
# ═══════════════════════════════════════════════════════════════

def draw_narration_header(
    screen: pygame.Surface,
    phase: GamePhase,
    x: int,
    y: int,
) -> None:
    """Draw a narration header (announcement style) in the sidebar."""
    if phase == GamePhase.DAY_ANNOUNCE:
        text = _("narration_day_announce")
    elif phase == GamePhase.GAME_OVER:
        text = _("narration_game_over")
    else:
        text = _("narration_generic")

    text_surf = render_text(text, scale=FONT_SCALE_BANNER, color=COLOR_PHASE_TEXT,
                             shadow=(30, 20, 10))
    screen.blit(text_surf, (x + 10, y + 40))


# ═══════════════════════════════════════════════════════════════
#   VOTE RESULT BOX
# ═══════════════════════════════════════════════════════════════

def draw_vote_result_box(
    screen: pygame.Surface,
    text: str,
    is_plural: bool,
    x: int,
    w: int,
) -> None:
    """Draw a vote result announcement in the sidebar."""
    lines = text.split("\\n") if "\\n" in text else [text]
    y_off = 300
    for line in lines:
        surf = render_text(line, scale=FONT_SCALE_INDICATOR, color=COLOR_VOTE_HIGHLIGHT,
                           shadow=(20, 15, 5))
        bx = x + (w - surf.get_width()) // 2
        screen.blit(surf, (bx, y_off))
        y_off += 40

    # Draw a small emphasis border
    box = pygame.Surface((w - 20, y_off - 300 + 15), pygame.SRCALPHA)
    box.fill((*COLOR_VOTE_HIGHLIGHT, 20))
    pygame.draw.rect(box, (*COLOR_VOTE_HIGHLIGHT, 100), (0, 0, box.get_width(), box.get_height()), 1)
    screen.blit(box, (x + 10, 295))


def draw_sheriff_vote_result(
    screen: pygame.Surface,
    text: str,
    x: int,
    w: int,
) -> None:
    """Draw sheriff election result text in the sidebar."""
    lines = text.split("\\n") if "\\n" in text else [text]
    y_off = 400
    for line in lines:
        surf = render_text(line, scale=FONT_SCALE_INDICATOR, color=COLOR_SHERIFF,
                           shadow=(20, 15, 5))
        bx = x + (w - surf.get_width()) // 2
        screen.blit(surf, (bx, y_off))
        y_off += 35


# ═══════════════════════════════════════════════════════════════
#   DAY BANNER
# ═══════════════════════════════════════════════════════════════

def draw_day_banner(
    screen: pygame.Surface,
    day: int,
) -> None:
    """Draw a "Day N" banner at the top of the village view (not sidebar)."""
    day_text = _("day_banner", day)
    text_surf = render_text(day_text, scale=FONT_SCALE_BANNER, color=COLOR_DAY_TEXT,
                             shadow=(10, 10, 20))
    bx = (SCREEN_W - SIDEBAR_W - text_surf.get_width()) // 2
    screen.blit(text_surf, (bx, 8))


# ═══════════════════════════════════════════════════════════════
#   ELECTION BANNER
# ═══════════════════════════════════════════════════════════════

def draw_election_banner(
    screen: pygame.Surface,
    x: int,
    w: int,
) -> None:
    """Draw sheriff election banner at top of sidebar."""
    text = _("election_banner")
    text_surf = render_text(text, scale=FONT_SCALE_INDICATOR, color=COLOR_SHERIFF,
                             shadow=(30, 20, 5))
    bx = x + (w - text_surf.get_width()) // 2
    screen.blit(text_surf, (bx, 35))


def draw_sheriff_result(
    screen: pygame.Surface,
    result: dict,
    x: int,
    w: int,
) -> None:
    """Draw the sheriff election result (who won, vote counts).

    Args:
        result: Dict with keys 'votes', 'winner', 'tie', 'no_votes', 'top_candidates'
                as set by GameState._resolve_sheriff_election().
    """
    # Background panel
    pw = w - 20
    ph = 120
    px = x + 10
    py = 60

    panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
    panel.fill((*COLOR_PHASE_PILL_BG, 200))
    pygame.draw.rect(panel, (*COLOR_SHERIFF, 180), (0, 0, pw, ph), 1)
    screen.blit(panel, (px, py))

    # Header
    header_surf = render_text(_("sheriff_vote_header"), scale=FONT_SCALE_LOG, color=COLOR_SHERIFF,
                               shadow=(5, 5, 10))
    screen.blit(header_surf, (px + 5, py + 5))

    # Content
    cy = py + 25

    # Vote tallies
    sorted_votes = sorted(result.get("votes", {}).items(), key=lambda kv: -kv[1]["count"])
    for pidx, vinfo in sorted_votes:
        line = f"#{pidx} {vinfo['name']}: {vinfo['count']}"
        color = COLOR_SHERIFF if result.get("winner") and result["winner"]["idx"] == pidx else COLOR_TEXT
        line_surf = render_text(line, scale=FONT_SCALE_SMALL, color=color, shadow=(3, 3, 5))
        screen.blit(line_surf, (px + 10, cy))
        cy += 16

    # Outcome message
    if result.get("no_votes"):
        msg = render_text(_("sheriff_result_none"), scale=FONT_SCALE_SMALL, color=COLOR_TEXT_DIM,
                          shadow=(3, 3, 5))
        screen.blit(msg, (px + 10, cy + 2))
    elif result.get("tie"):
        tops = result.get("top_candidates", [])
        if len(tops) >= 2:
            msg = render_text(_("sheriff_result_tie", tops[0]["name"], tops[1]["name"]),
                              scale=FONT_SCALE_SMALL, color=COLOR_WARN, shadow=(3, 3, 5))
            screen.blit(msg, (px + 10, cy + 2))
    elif result.get("winner"):
        w_info = result["winner"]
        msg = render_text(_("sheriff_result_winner", w_info["name"], str(w_info["votes"])),
                          scale=FONT_SCALE_SMALL, color=COLOR_SHERIFF, shadow=(3, 3, 5))
        screen.blit(msg, (px + 10, cy + 2))

    # Blit again on top of the outcome line to avoid overlap issues
    # (content already drawn above — re-blit panel border on top)
    pygame.draw.rect(screen, (*COLOR_SHERIFF, 150), (px, py, pw, ph), 1)


# ═══════════════════════════════════════════════════════════════
#   DISCUSSION BUBBLE
# ═══════════════════════════════════════════════════════════════

def draw_discussion_bubble(
    screen: pygame.Surface,
    speaker_idx: int,
    text: str,
    x: int,
    w: int,
    sh: int,
) -> None:
    """Draw a speech bubble showing the current speaker's dialogue."""
    # Speaker label
    label = _("speaker_label", speaker_idx)
    label_surf = render_text(label, scale=FONT_SCALE_LOG, color=(200, 200, 255),
                              shadow=(5, 5, 10))
    screen.blit(label_surf, (x + 10, sh - 100))

    # Speech text
    text_surf = render_text(text, scale=FONT_SCALE_SMALL, color=(220, 220, 200),
                             shadow=(5, 5, 5))
    screen.blit(text_surf, (x + 10, sh - 75))

    # Bubble background
    bubble_h = 65 + text_surf.get_height()
    bubble = pygame.Surface((w - 20, bubble_h), pygame.SRCALPHA)
    bubble.fill((*COLOR_PHASE_PILL_BG, 180))
    pygame.draw.rect(bubble, (*COLOR_PHASE_PILL_BORDER, 150), (0, 0, w - 20, bubble_h), 1)
    screen.blit(bubble, (x + 10, sh - 105))


# ═══════════════════════════════════════════════════════════════
#   SKILL STATUS PANEL
# ═══════════════════════════════════════════════════════════════

def draw_skill_status_panel(
    screen: pygame.Surface,
    state,
    x: int,
    w: int,
    sh: int,
) -> None:
    """Draw a panel showing NPC skill status during night phases."""
    panel_y = sh - 250
    panel_h = 240

    panel = pygame.Surface((w - 20, panel_h), pygame.SRCALPHA)
    panel.fill((*COLOR_PHASE_PILL_BG, 180))
    pygame.draw.rect(panel, (*COLOR_PHASE_PILL_BORDER, 100), (0, 0, w - 20, panel_h), 1)
    screen.blit(panel, (x + 10, panel_y))

    # Phase name
    phase = state.phase
    phase_label = render_text(phase.display_name, scale=FONT_SCALE_LOG,
                               color=COLOR_PHASE_TEXT, shadow=(5, 5, 5))
    screen.blit(phase_label, (x + 15, panel_y + 5))

    # Show which roles are acting
    y_off = panel_y + 30
    acting_roles = {
        GamePhase.NIGHT_GUARD: _("skill_guard"),
        GamePhase.NIGHT_WEREWOLF: _("skill_werewolf"),
        GamePhase.NIGHT_WITCH: _("skill_witch"),
        GamePhase.NIGHT_SEER: _("skill_seer"),
    }
    if phase in acting_roles:
        info = render_text(acting_roles[phase], scale=FONT_SCALE_LOG,
                           color=(200, 200, 180), shadow=(5, 5, 5))
        screen.blit(info, (x + 15, y_off))


# ═══════════════════════════════════════════════════════════════
#   WOLF VOTE DISPLAY
# ═══════════════════════════════════════════════════════════════

def draw_wolf_vote_display(
    screen: pygame.Surface,
    wolf_votes: dict,
    x: int,
    w: int,
) -> None:
    """Show which player each wolf is voting to kill (for debugging/human)."""
    if not wolf_votes:
        return

    text = _("wolf_votes_header")
    surf = render_text(text, scale=FONT_SCALE_LOG, color=COLOR_WEREWOLF, shadow=(10, 5, 5))
    screen.blit(surf, (x + 15, 140))

    y_off = 165
    for wolf_idx, target_idx in wolf_votes.items():
        line = _("wolf_vote_line", wolf_idx, target_idx)
        line_surf = render_text(line, scale=FONT_SCALE_SMALL, color=(200, 140, 140),
                                 shadow=(5, 5, 5))
        screen.blit(line_surf, (x + 20, y_off))
        y_off += 22


# ═══════════════════════════════════════════════════════════════
#   WITCH POTION DISPLAY
# ═══════════════════════════════════════════════════════════════

def draw_witch_potion_display(
    screen: pygame.Surface,
    state,
    x: int,
    w: int,
    poison_mode: bool = False,
) -> None:
    """Show witch's remaining potions in the sidebar, with mode toggle.

    Renders two clickable areas: heal (save) and poison (kill).
    The active mode is highlighted. Caller should detect clicks
    on the heal/poison labels to toggle mode using module-level
    _WITCH_BUTTON_RECTS dict.
    """
    global _WITCH_BUTTON_RECTS
    has_heal = not state.witch_used_heal
    has_poison = not state.witch_used_poison

    # ── Heal button ──
    heal_label = _("witch_heal_ready") if has_heal else _("witch_heal_used")
    heal_color = (255, 220, 180) if (not poison_mode and has_heal) else (120, 100, 80)
    heal_bg = (60, 50, 35) if (not poison_mode and has_heal) else (35, 30, 25)

    # ── Poison button ──
    poison_label = _("witch_poison_ready") if has_poison else _("witch_poison_used")
    poison_color = (255, 150, 150) if (poison_mode and has_poison) else (120, 80, 80)
    poison_bg = (60, 30, 30) if (poison_mode and has_poison) else (35, 25, 25)

    # Draw heal button
    btn_h = 28
    btn_y = 170
    pygame.draw.rect(screen, heal_bg, (x + 10, btn_y, w - 20, btn_h))
    surf = render_text(heal_label, scale=FONT_SCALE_LOG, color=heal_color,
                       shadow=(5, 10, 5) if not poison_mode else None)
    screen.blit(surf, (x + 18, btn_y + 6))
    _WITCH_BUTTON_RECTS["heal"] = pygame.Rect(x + 10, btn_y, w - 20, btn_h)

    # Draw poison button
    btn_y2 = btn_y + btn_h + 4
    pygame.draw.rect(screen, poison_bg, (x + 10, btn_y2, w - 20, btn_h))
    surf = render_text(poison_label, scale=FONT_SCALE_LOG, color=poison_color,
                       shadow=(5, 10, 5) if poison_mode else None)
    screen.blit(surf, (x + 18, btn_y2 + 6))
    _WITCH_BUTTON_RECTS["poison"] = pygame.Rect(x + 10, btn_y2, w - 20, btn_h)

    # Hint text
    hint = _("witch_toggle_hint") if hasattr(state, 'witch_used_heal') else ""
    if hint:
        hint_surf = render_text(hint, scale=FONT_SCALE_LOG - 1, color=(150, 150, 150))
        screen.blit(hint_surf, (x + 18, btn_y2 + btn_h + 6))


# ═══════════════════════════════════════════════════════════════
#   HUNTER VENGEANCE DISPLAY
# ═══════════════════════════════════════════════════════════════

def draw_hunter_vengeance_display(
    screen: pygame.Surface,
    state,
    x: int,
    w: int,
    sh: int,
) -> None:
    """Show hunter vengeance target prompt (when hunter is eliminated)."""
    if not state.hunter_needs_vengeance:
        return

    text = _("hunter_vengeance")
    surf = render_text(text, scale=FONT_SCALE_BANNER, color=COLOR_DEATH, shadow=(20, 5, 5))
    bx = x + (w - surf.get_width()) // 2
    by = sh // 2 - 50
    screen.blit(surf, (bx, by))


# ═══════════════════════════════════════════════════════════════
#   GUARD TARGET DISPLAY
# ═══════════════════════════════════════════════════════════════

def draw_guard_target_display(
    screen: pygame.Surface,
    target_idx: int,
    players,
    x: int,
    w: int,
    sh: int,
) -> None:
    """Show the current guard target (which player is being protected)."""
    target = players.get_player(target_idx)
    if not target:
        return

    text = _("guard_target", target.display_name)
    surf = render_text(text, scale=FONT_SCALE_INDICATOR, color=(180, 200, 255),
                       shadow=(10, 10, 30))
    bx = x + (w - surf.get_width()) // 2
    screen.blit(surf, (bx, sh - 320))


# ═══════════════════════════════════════════════════════════════
#   SEER TARGET DISPLAY
# ═══════════════════════════════════════════════════════════════

def draw_seer_target_display(
    screen: pygame.Surface,
    target_idx: int,
    players,
    x: int,
    w: int,
    sh: int,
) -> None:
    """Show the current seer investigation target."""
    target = players.get_player(target_idx)
    if not target:
        return

    text = _("seer_target", target.display_name)
    surf = render_text(text, scale=FONT_SCALE_INDICATOR, color=(220, 180, 255),
                       shadow=(10, 10, 30))
    bx = x + (w - surf.get_width()) // 2
    screen.blit(surf, (bx, sh - 340))


# ═══════════════════════════════════════════════════════════════
#   SPECTATOR MODE BANNER
# ═══════════════════════════════════════════════════════════════

def draw_spectator_mode_banner(
    screen: pygame.Surface,
    x: int,
    w: int,
) -> None:
    """Draw a banner indicating the human is dead and spectating."""
    text = _("spectator_mode")
    surf = render_text(text, scale=FONT_SCALE_INDICATOR, color=COLOR_DEATH, shadow=(20, 5, 10))
    bx = x + (w - surf.get_width()) // 2
    screen.blit(surf, (bx, 130))


# ═══════════════════════════════════════════════════════════════
#   GAME RESULT PANEL
# ═══════════════════════════════════════════════════════════════

def draw_game_result_panel(
    screen: pygame.Surface,
    state,
    x: int,
    w: int,
    sh: int,
) -> None:
    """Draw the game result panel (village POV)."""
    # state.winner is a string "village" or "werewolf" (from PlayerManager.get_winning_team())
    winner_str = state.winner
    if winner_str not in ("village", "werewolf"):
        return

    # Full overlay
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    # Winner text
    if winner_str == "werewolf":
        result = _("game_over_wolf_win")
        color = COLOR_WEREWOLF
    else:
        result = _("game_over_village_win")
        color = COLOR_VILLAGER

    result_surf = render_text(result, scale=4, color=color, shadow=(0, 0, 0))
    bx = (SCREEN_W - result_surf.get_width()) // 2
    screen.blit(result_surf, (bx, sh // 2 - 60))

    # Sub text
    sub = _("game_over_sub")
    sub_surf = render_text(sub, scale=FONT_SCALE_INDICATOR, color=(200, 200, 180),
                            shadow=(0, 0, 0))
    sbx = (SCREEN_W - sub_surf.get_width()) // 2
    screen.blit(sub_surf, (sbx, sh // 2))


def draw_game_result_panel_wolf_pov(
    screen: pygame.Surface,
    state,
    x: int,
    w: int,
    sh: int,
) -> None:
    """Draw the game result panel from the werewolf perspective."""
    draw_game_result_panel(screen, state, x, w, sh)

    # Extra wolf-specific info: reveal all wolves
    wolves = [p for p in state.players.players if p.role == Role.WEREWOLF]
    wolf_names = ", ".join(p.display_name for p in wolves)
    wolf_text = _("wolf_reveal", wolf_names)
    wolf_surf = render_text(wolf_text, scale=FONT_SCALE_LOG, color=COLOR_WEREWOLF,
                             shadow=(0, 0, 0))
    wbx = (SCREEN_W - wolf_surf.get_width()) // 2
    screen.blit(wolf_surf, (wbx, sh // 2 + 40))


# ═══════════════════════════════════════════════════════════════
#   ICON BUTTON (placeholder)
# ═══════════════════════════════════════════════════════════════

def draw_icon_button(
    screen: pygame.Surface,
    x: int,
    y: int,
    w: int,
    h: int,
    label: str,
    icon: str = "",
    enabled: bool = True,
) -> None:
    """Draw an icon button (placeholder for interactive buttons)."""
    button = pygame.Surface((w, h), pygame.SRCALPHA)
    if enabled:
        button.fill((*COLOR_PHASE_PILL_BORDER, 150))
        pygame.draw.rect(button, (*COLOR_PHASE_PILL_BORDER, 200), (0, 0, w, h), 2)
        text_color = COLOR_PHASE_TEXT
    else:
        button.fill((60, 50, 40, 120))
        pygame.draw.rect(button, (60, 50, 40, 150), (0, 0, w, h), 2)
        text_color = COLOR_DEAD

    screen.blit(button, (x, y))

    text_surf = render_text(label, scale=FONT_SCALE_LOG, color=text_color, shadow=(5, 5, 5))
    tx = x + (w - text_surf.get_width()) // 2
    ty = y + (h - text_surf.get_height()) // 2
    screen.blit(text_surf, (tx, ty))


# ═══════════════════════════════════════════════════════════════
#   TAG PLAYER BUTTONS (placeholder for clickable player tags)
# ═══════════════════════════════════════════════════════════════

def draw_tag_player_buttons(
    screen: pygame.Surface,
    players,
    x: int,
    y: int,
    w: int,
    alive_only: bool = True,
) -> None:
    """Draw clickable player tag buttons (placeholder — no input handling)."""
    yy = y
    for p in players.players:
        if alive_only and not p.alive:
            continue
        tag = p.display_name
        surf = render_text(tag, scale=FONT_SCALE_LOG, color=COLOR_ALIVE, shadow=(5, 5, 5))
        screen.blit(surf, (x + 5, yy))
        yy += 24


# ═══════════════════════════════════════════════════════════════
#   NIGHT OVERLAY (vignette)
# ═══════════════════════════════════════════════════════════════

def draw_night_overlay(screen: pygame.Surface, is_night: bool) -> None:
    """Draw night overlay darkness and vignette effect."""
    if not is_night:
        return
    vw = min(SCREEN_W, 2560)
    vh = min(SCREEN_H, 1440)
    vignette = pygame.Surface((vw, vh), pygame.SRCALPHA)
    step = max(2, int(4 * WIN_SCALE))
    for i in range(max(4, int(8 * WIN_SCALE))):
        alpha = max(0, 6 - i)
        inset = i * step
        pygame.draw.rect(
            vignette, (0, 0, 20, alpha * 2),
            (inset, inset, vw - inset * 2, vh - inset * 2),
            max(1, int(4 * WIN_SCALE)),
        )
    screen.blit(vignette, (0, 0))


# ═══════════════════════════════════════════════════════════════
#   WOODEN FRAME (decorative border around village view)
# ═══════════════════════════════════════════════════════════════

def draw_wooden_frame(screen: pygame.Surface) -> None:
    """Draw a decorative wooden frame around the village viewport."""
    frame_color = (45, 30, 20)
    dark_edge = (30, 20, 12)
    highlight = (60, 40, 25)
    frame_w = max(2, int(4 * WIN_SCALE))

    # Top bar
    pygame.draw.rect(screen, frame_color, (0, 0, SCREEN_W, frame_w))
    pygame.draw.rect(screen, highlight, (0, 0, SCREEN_W, 1))
    # Bottom bar
    pygame.draw.rect(screen, frame_color, (0, SCREEN_H - frame_w, SCREEN_W, frame_w))
    pygame.draw.rect(screen, dark_edge, (0, SCREEN_H - 1, SCREEN_W, 1))


# ═══════════════════════════════════════════════════════════════
#   VOTE PULSE HELPERS (animation state for vote highlights)
# ═══════════════════════════════════════════════════════════════

_VOTE_PULSE_TIMERS: dict[int, float] = {}
_PREV_VOTE_COUNTS: dict[int, int] = {}
_ELIMINATION_TIMERS: dict[int, float] = {}

# Witch potion mode-toggle button rects (populated by draw_witch_potion_display)
_WITCH_BUTTON_RECTS: dict[str, pygame.Rect] = {}


def update_vote_pulses(dt: float, votes: dict) -> None:
    """Update vote pulse animation timers based on vote count changes."""
    for pidx, voters in votes.items():
        count = len(voters)
        prev = _PREV_VOTE_COUNTS.get(pidx, 0)
        if count > prev:
            _VOTE_PULSE_TIMERS[pidx] = 0.4
        _PREV_VOTE_COUNTS[pidx] = count
    # Tick down pulse timers
    for pidx in list(_VOTE_PULSE_TIMERS.keys()):
        _VOTE_PULSE_TIMERS[pidx] -= dt
        if _VOTE_PULSE_TIMERS[pidx] <= 0:
            del _VOTE_PULSE_TIMERS[pidx]


def trigger_elimination_highlight(pidx: int) -> None:
    """Trigger elimination highlight animation for a player."""
    _ELIMINATION_TIMERS[pidx] = 1.0


def update_elimination_timers(dt: float) -> None:
    """Tick down elimination highlight timers."""
    for pidx in list(_ELIMINATION_TIMERS.keys()):
        _ELIMINATION_TIMERS[pidx] -= dt
        if _ELIMINATION_TIMERS[pidx] <= 0:
            del _ELIMINATION_TIMERS[pidx]


def reset_vote_pulses() -> None:
    """Reset all vote pulse state (e.g., at the start of a new vote)."""
    _VOTE_PULSE_TIMERS.clear()
    _PREV_VOTE_COUNTS.clear()


def get_vote_pulse_alpha(pidx: int) -> float:
    """Get the vote pulse alpha value for a player (0.0 = no pulse)."""
    return _VOTE_PULSE_TIMERS.get(pidx, 0.0) / 0.4


# ──────────────────────────────────────────────
# Menu / overlay rendering (extracted from game_loop.py)
# ──────────────────────────────────────────────


def draw_main_menu(screen: pygame.Surface, sw: int, sh: int,
                    menu_option: int, menu_fade_in: float,
                    particles: list | None = None) -> None:
    """Draw the main menu screen."""
    from game.bitmap_font import render_text
    from game.text import _

    # ── Particles layer (behind vignette but above gradient) ──
    if particles:
        particle_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for p in particles:
            px = int(p["x"] * sw)
            py = int(p["y"] * sh)
            size = p["size"]
            alpha = int(p["alpha"] * 180)
            # Outer glow
            glow_radius = size * 6
            color = p["color"]
            pygame.draw.circle(particle_surf, (*color, alpha // 3),
                               (px, py), glow_radius + 4)
            # Inner glow
            pygame.draw.circle(particle_surf, (*color, alpha // 2),
                               (px, py), glow_radius)
            # Core
            pygame.draw.circle(particle_surf, (255, 255, 255, alpha),
                               (px, py), max(2, size * 2))
        screen.blit(particle_surf, (0, 0))

    # Background — minimal dark gradient
    for y in range(sh):
        t = y / sh
        r = int(20 * (1 - t) + 10 * t)
        g = int(15 * (1 - t) + 8 * t)
        b = int(30 * (1 - t) + 15 * t)
        pygame.draw.line(screen, (r, g, b), (0, y), (sw, y))

    # Vignette overlay
    vignette = pygame.Surface((sw, sh), pygame.SRCALPHA)
    steps = max(10, int(20 * sh / 1440))
    for i in range(steps):
        alpha = max(0, int(140 - i * (140 / steps)))
        spread = int(i * (40 * sw / 2560))
        pygame.draw.rect(
            vignette, (0, 0, 0, alpha),
            (spread, spread, sw - spread * 2, sh - spread * 2),
        )
    screen.blit(vignette, (0, 0))

    # Gentle dark overlay on top
    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 100))
    screen.blit(overlay, (0, 0))

    # ── Title Block ──
    title_scale = max(2, int(5 * sh / 1440))
    subtitle_scale = max(1, int(2 * sh / 1440))
    cx = sw // 2
    title_y = sh // 4

    # Title text
    title_str = "Pixel Werewolf"
    title_text = render_text(
        title_str,
        scale=title_scale, color=(200, 180, 140), shadow=(40, 30, 10)
    )
    tw = title_text.get_width()
    screen.blit(title_text, (cx - tw // 2, title_y))

    # Subtitle
    subtitle_str = _("tagline")
    sub_text = render_text(
        subtitle_str,
        scale=subtitle_scale, color=(160, 140, 100), shadow=(30, 20, 5)
    )
    sub_tw = sub_text.get_width()
    screen.blit(sub_text, (cx - sub_tw // 2, title_y + title_text.get_height() + 20))

    # ── Menu Options ──
    options = [_("start_game"), _("settings"), _("quit")]
    center_y = sh // 2 + int(80 * sh / 1440)
    for i, opt in enumerate(options):
        by = center_y + i * int(80 * sh / 1440)
        # Button background
        bx = cx - int(200 * sw / 2560)
        bw = int(400 * sw / 2560)
        bh = int(60 * sh / 1440)

        if menu_option == i:
            color = (140, 110, 60)
            inner = (180, 150, 90)
        else:
            color = (80, 70, 50)
            inner = (120, 100, 70)

        pygame.draw.rect(screen, color, (bx, by, bw, bh), border_radius=4)
        pygame.draw.rect(screen, inner, (bx + 2, by + 2, bw - 4, bh - 4), border_radius=3)

        opt_scale = max(1, int(2 * sh / 1440))
        opt_text = render_text(
            opt, scale=opt_scale,
            color=(220, 210, 190) if menu_option == i else (180, 170, 150),
        )
        otw = opt_text.get_width()
        screen.blit(opt_text, (cx - otw // 2, by + (bh - opt_text.get_height()) // 2))

    # ── Footer ──
    footer_scale = max(1, int(1 * sh / 1440))
    footer = render_text(
        _("footer_tip"),
        scale=footer_scale, color=(100, 90, 70)
    )
    fw = footer.get_width()
    screen.blit(footer, (cx - fw // 2, sh - int(60 * sh / 1440)))

    # Fade in
    if menu_fade_in < 1.0:
        fade = pygame.Surface((sw, sh))
        fade.set_alpha(int(255 * (1.0 - menu_fade_in)))
        fade.fill((0, 0, 0))
        screen.blit(fade, (0, 0))


def draw_settings_overlay(screen: pygame.Surface, sw: int, sh: int,
                           settings_option: int, settings_fade_in: float) -> None:
    """Draw the settings overlay on top of the main menu."""
    from game.bitmap_font import render_text
    from game.text import _, LANG

    cx = sw // 2
    cy = sh // 2

    # Settings panel background
    pw = int(500 * sw / 2560)
    ph = int(350 * sh / 1440)
    px = cx - pw // 2
    py = cy - ph // 2 - int(60 * sh / 1440)
    pygame.draw.rect(screen, (40, 35, 25), (px, py, pw, ph), border_radius=8)
    pygame.draw.rect(screen, (80, 70, 50), (px + 2, py + 2, pw - 4, ph - 4), border_radius=7)
    pygame.draw.rect(screen, (60, 50, 35), (px + 4, py + 4, pw - 8, ph - 8), border_radius=6)

    # Title
    title_scale = max(2, int(4 * sh / 1440))
    title = render_text(_("settings_title"), scale=title_scale, color=(220, 210, 180), shadow=(40, 30, 15))
    title_y = py + int(30 * sh / 1440)
    screen.blit(title, (cx - title.get_width() // 2, title_y))

    # Separator line
    sep_y = title_y + title.get_height() + int(20 * sh / 1440)
    pygame.draw.line(screen, (100, 90, 70), (px + 40, sep_y), (px + pw - 40, sep_y), 2)

    # Settings options
    lang_label = _("settings_current_lang") if LANG == "zh" else _("settings_current_lang")
    options = [lang_label, _("settings_back")]

    opt_scale = max(1, int(2 * sh / 1440))
    opt_start_y = sep_y + int(40 * sh / 1440)

    for i, opt_text_str in enumerate(options):
        oy = opt_start_y + i * int(70 * sh / 1440)

        ox = px + int(40 * sw / 2560)
        ow = pw - int(80 * sw / 2560)
        oh = int(50 * sh / 1440)

        if settings_option == i:
            color = (120, 95, 55)
            inner = (160, 130, 80)
        else:
            color = (70, 60, 40)
            inner = (100, 85, 60)

        pygame.draw.rect(screen, color, (ox, oy, ow, oh), border_radius=4)
        pygame.draw.rect(screen, inner, (ox + 2, oy + 2, ow - 4, oh - 4), border_radius=3)

        opt_text = render_text(opt_text_str, scale=opt_scale,
                               color=(220, 210, 190) if settings_option == i else (180, 170, 150))
        screen.blit(opt_text, (ox + (ow - opt_text.get_width()) // 2,
                               oy + (oh - opt_text.get_height()) // 2))

    # Hint text at bottom
    hint_scale = max(1, int(1 * sh / 1440))
    hint = render_text(_("settings_hint") if LANG == "zh" else _("settings_hint"),
                       scale=hint_scale, color=(120, 110, 90))
    hint_y = py + ph - int(30 * sh / 1440) - hint.get_height()
    screen.blit(hint, (cx - hint.get_width() // 2, hint_y))


def draw_role_reveal(screen: pygame.Surface, sw: int, sh: int,
                     human_player) -> None:
    """Draw the role reveal card for the human player."""
    from game.bitmap_font import render_text
    from game.text import _
    from game.roles import Team
    from game.role_icons import get_role_icon

    if not human_player:
        return

    # Darken background
    overlay = pygame.Surface((sw, sh))
    overlay.set_alpha(200)
    overlay.fill((0, 0, 0))
    screen.blit(overlay, (0, 0))

    # Card
    card_w = int(600 * sw / 2560)
    card_h = int(400 * sh / 1440)
    card_x = (sw - card_w) // 2
    card_y = (sh - card_h) // 2

    # Shadow
    pygame.draw.rect(screen, (10, 10, 10), (card_x + 4, card_y + 4, card_w, card_h),
                     border_radius=12)
    # Card background
    pygame.draw.rect(screen, (40, 35, 50), (card_x, card_y, card_w, card_h),
                     border_radius=12)
    pygame.draw.rect(screen, (80, 70, 90), (card_x + 2, card_y + 2, card_w - 4, card_h - 4),
                     border_radius=10)

    # Role title
    title_scale = max(2, int(4 * sh / 1440))
    title_text = render_text(
        _("your_role"),
        scale=title_scale, color=(200, 180, 140), shadow=(40, 30, 10)
    )
    text_margin = int(200 * sw / 2560)
    screen.blit(title_text, (card_x + text_margin, card_y + int(50 * sh / 1440)))

    # Role description
    desc_scale = max(1, int(2 * sh / 1440))
    desc = human_player.role.description
    desc_text = render_text(
        desc,
        scale=desc_scale, color=(200, 200, 200), shadow=(20, 20, 20)
    )
    screen.blit(desc_text, (card_x + text_margin, card_y + int(110 * sh / 1440)))

    # Team info
    team_scale = max(1, int(2 * sh / 1440))
    team_str = _("team") + ": "
    if human_player.role.team == Team.WEREWOLF:
        team_str += _("werewolf_team")
        team_color = (200, 80, 80)
    elif human_player.role.team == Team.VILLAGE:
        team_str += _("village_team")
        team_color = (100, 180, 100)
    else:
        team_str += _("neutral_team")
        team_color = (180, 180, 100)
    team_text = render_text(team_str, scale=team_scale, color=team_color)
    screen.blit(team_text, (card_x + text_margin, card_y + int(170 * sh / 1440)))

    # Role icon
    icon = get_role_icon(human_player.role)
    if icon:
        icon_size = int(64 * min(sw / 2560, sh / 1440))
        icon_scaled = pygame.transform.scale(icon, (icon_size, icon_size))
        screen.blit(icon_scaled, (card_x + card_w - icon_size - int(40 * sw / 2560),
                                   card_y + int(50 * sh / 1440)))

    # Press space to continue
    cont_scale = max(1, int(2 * sh / 1440))
    continue_text = render_text(
        _("press_space"),
        scale=cont_scale, color=(140, 140, 140), shadow=(10, 10, 10)
    )
    ctw = continue_text.get_width()
    screen.blit(continue_text, ((sw - ctw) // 2, card_y + card_h - int(50 * sh / 1440)))


def draw_game_over(screen: pygame.Surface, sw: int, sh: int,
                   winner: str | None, flash_color: tuple[int, int, int],
                   flash_timer: float, flash_duration: float,
                   flash_active: bool) -> None:
    """Draw the game over screen."""
    from game.bitmap_font import render_text
    from game.text import _

    # Darken
    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    cx = sw // 2
    cy = sh // 2

    # Winner text
    if winner:
        if winner == "werewolf":
            winner_title = _("werewolf_wins")
            color = (200, 60, 60)
        else:
            winner_title = _("village_wins")
            color = (200, 180, 80)
    else:
        winner_title = _("game_over")
        color = (180, 180, 180)

    title_scale = max(2, int(5 * sh / 1440))
    title_text = render_text(
        winner_title, scale=title_scale, color=color, shadow=(40, 30, 10)
    )
    tw = title_text.get_width()
    screen.blit(title_text, (cx - tw // 2, cy - int(120 * sh / 1440)))

    # Restart / Quit
    restart_txt = _("restart_prompt")
    quit_txt = _("quit_prompt")
    opt_scale = max(1, int(2 * sh / 1440))
    restart_render = render_text(restart_txt, scale=opt_scale, color=(180, 180, 180))
    quit_render = render_text(quit_txt, scale=opt_scale, color=(180, 180, 180))
    rw = restart_render.get_width()
    qw = quit_render.get_width()
    screen.blit(restart_render, (cx - rw // 2, cy + int(40 * sh / 1440)))
    screen.blit(quit_render, (cx - qw // 2, cy + int(80 * sh / 1440)))

    # Flash
    if flash_active:
        alpha = int(255 * (flash_timer / max(flash_duration, 0.001)))
        flash_surf = pygame.Surface((sw, sh))
        flash_surf.set_alpha(alpha)
        flash_surf.fill(flash_color)
        screen.blit(flash_surf, (0, 0))

def is_elimination_highlighted(pidx: int) -> bool:
    """Check if a player is currently in elimination highlight animation."""
    return pidx in _ELIMINATION_TIMERS
