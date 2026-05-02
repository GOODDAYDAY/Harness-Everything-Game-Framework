#!/usr/bin/env python3
"""Pixel Werewolf — Python/pygame entry point."""

from __future__ import annotations

import math
from typing import Optional

import pygame

from game.bitmap_font import render_text
from game.role_icons import get_role_icon, ICON_DEAD, ICON_SHERIFF
from scripts.game_engine import GameEngine
from game.game_state import GameState
from game.phases import GamePhase
from game.renderer import VillageRenderer
from game.roles import Role

# NPC AI
from game.npc_ai import (
    choose_hunter_vengeance_target,
    choose_night_action,
    choose_sheriff_vote,
    choose_vote_target,
    decide_witch_action,
)

# Procedural sound effects
from game.sound import (
    day_ambience,
    day_chime,
    night_ambience,
    night_chime,
    kill_sting,
    vote_bell,
    vote_result,
    game_over_victory,
    game_over_defeat,
)

# Pixel font scale for UI overlay (5x7 base, so scale=3 -> 15x21px per char)
FONT_SCALE_TITLE = 4   # ~20x28px per char
FONT_SCALE_PLAYER = 3   # ~15x21px per char
FONT_SCALE_LOG = 2      # ~10x14px per char
FONT_SCALE_SMALL = 1    # ~5x7px per char

# UI overlay positioning
SIDEBAR_X = 1900
SIDEBAR_Y = 20
LIST_START = 80
LIST_SPACING = 28
LOG_START_Y = 1100
LOG_SPACING = 20


class WerewolfGame:
    def __init__(self):
        self.engine = GameEngine(
            width=2560, height=1440,
            title="Pixel Werewolf",
            fps=60, pixel_art=True,
        )
        self.game_state = GameState()
        self.renderer = VillageRenderer()
        # Using bitmap font scales instead of pygame.font.Font objects
        # Phase timing (seconds to wait in each phase before auto-advancing)
        self._phase_timer: float = 0.0
        self._phase_duration: float = 1.5  # fallback seconds per phase
        # Per-phase durations for readable pacing
        self._phase_durations: dict[GamePhase, float] = {
            GamePhase.NIGHT_GUARD: 2.0,
            GamePhase.NIGHT_SEER: 2.5,
            GamePhase.NIGHT_WEREWOLF: 3.0,
            GamePhase.NIGHT_WITCH: 2.0,
            GamePhase.DAY_ANNOUNCE: 3.0,
            GamePhase.DAY_SHERIFF_ELECTION: 1.5,
            GamePhase.DAY_DISCUSSION: 5.0,
            GamePhase.DAY_VOTE: 6.0,
            GamePhase.DAY_RESULT: 3.0,
            GamePhase.GAME_OVER: 6.0,
            GamePhase.SETUP: 2.0,
        }
        self._game_started: bool = False
        # Sound state
        self._prev_phase: GamePhase = GamePhase.SETUP
        self._sound_played_game_over: bool = False
        self._role_revealed: bool = False
        # Ambience state
        self._ambience_channel: Optional[pygame.mixer.Channel] = None
        self._current_ambience: str = ""  # "night", "day", or ""
        # Phase transition banner state
        self._banner_text: str = ""
        self._banner_timer: float = 0.0
        self._banner_duration: float = 2.5
        # Human player interaction state
        self._human_player_idx: int = 0
        self._human_voted: bool = False
        self._human_vote_target: Optional[int] = None
        self._human_sheriff_voted: bool = False
        self._human_sheriff_target: Optional[int] = None
        # Track clickable player name rectangles in sidebar
        self._player_click_rects: list[tuple[pygame.Rect, int]] = []
        # Restart state
        self._restart_clicked: bool = False
        # Main menu state
        self._main_menu: bool = True
        self._menu_phase_timer: float = 0.0
        # Title animation: pulsing glow offset
        self._title_glow: float = 0.0

    def _restart_game(self) -> None:
        """Reset the game state for a new match."""
        self.game_state = GameState()
        self.game_state.start_game()
        self._role_revealed = False
        self._human_voted = False
        self._human_vote_target = None
        self._human_sheriff_voted = False
        self._human_sheriff_target = None
        self._sound_played_game_over = False
        self._restart_clicked = False
        self._prev_phase = GamePhase.SETUP
        if self.game_state.phase != GamePhase.GAME_OVER:
            self.game_state.advance_night_phase()

    def init(self):
        if not self.engine.init():
            return False
        self.engine.on_render = self.render
        self.engine.on_update = self.update
        self.engine.on_event = self._handle_event
        # Register state provider for TCP bridge
        self.engine.get_state = lambda: self.game_state.to_dict()

        # Initialise audio mixer (gracefully handles no audio device)
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
        except pygame.error:
            pass  # headless / no audio — sounds will be silent

        # Using procedural bitmap font — no external font files needed

        return True

    def _draw_main_menu(self, screen: pygame.Surface) -> None:
        """Draw the main title screen with atmospheric village background."""
        # Render the village background in twilight mode (halfway between day/night)
        # Use a gentle night scene with warm windows
        is_night_bg = True
        self.renderer.set_players(self.game_state.players.players)
        self.renderer.render(screen, is_night_bg, time=self._menu_phase_timer)

        # Dark vignette overlay for readability
        vignette = pygame.Surface((2560, 1440), pygame.SRCALPHA)
        # Center radial fade
        for i in range(20):
            alpha = max(0, 140 - i * 6)
            spread = i * 40
            pygame.draw.rect(
                vignette, (0, 0, 0, alpha),
                (spread, spread, 2560 - spread * 2, 1440 - spread * 2),
            )
        screen.blit(vignette, (0, 0))

        # Gentle dark overlay on top
        overlay = pygame.Surface((2560, 1440), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        screen.blit(overlay, (0, 0))

        # ── Title Block ──
        # Decorative line above title
        line_color = (200, 160, 80)
        pygame.draw.line(screen, line_color, (400, 200), (2560 - 400, 200), 3)
        pygame.draw.line(screen, (140, 100, 40), (400, 204), (2560 - 400, 204), 1)

        # Animated title glow
        glow_intensity = 0.7 + 0.3 * math.sin(self._title_glow * 2.0)
        glow_r = int(255 * glow_intensity)
        glow_g = int(200 * glow_intensity)
        glow_b = int(100 * glow_intensity * 0.6)

        title_text = render_text(
            "Pixel Werewolf", scale=8,
            color=(glow_r, glow_g, glow_b),
            shadow=(80, 50, 10),
        )
        tx = (2560 - title_text.get_width()) // 2
        ty = 280
        screen.blit(title_text, (tx, ty))

        # Subtitle
        subtitle = render_text(
            "A Village of Secrets", scale=3,
            color=(180, 160, 120),
            shadow=(40, 30, 10),
        )
        sx = (2560 - subtitle.get_width()) // 2
        screen.blit(subtitle, (sx, ty + title_text.get_height() + 20))

        # Decorative line below subtitle
        pygame.draw.line(screen, line_color, (600, ty + title_text.get_height() + 60),
                        (2560 - 600, ty + title_text.get_height() + 60), 2)

        # ── Start Button ──
        btn_w, btn_h = 360, 64
        btn_x = (2560 - btn_w) // 2
        btn_y = 680

        # Button background with pulsing border
        pulse = 0.85 + 0.15 * math.sin(self._title_glow * 3.0)
        btn_border = (int(200 * pulse), int(170 * pulse), int(80 * pulse))
        btn_fill = (50, 40, 25)
        pygame.draw.rect(screen, btn_fill, (btn_x, btn_y, btn_w, btn_h))
        pygame.draw.rect(screen, btn_border, (btn_x, btn_y, btn_w, btn_h), 3)

        # Inner highlight
        pygame.draw.rect(screen, (60, 50, 30), (btn_x + 4, btn_y + 4, btn_w - 8, btn_h - 8))

        btn_text = render_text(
            "START GAME", scale=4,
            color=(255, 220, 150),
            shadow=(60, 40, 10),
        )
        bx = btn_x + (btn_w - btn_text.get_width()) // 2
        by = btn_y + (btn_h - btn_text.get_height()) // 2
        screen.blit(btn_text, (bx, by))

        # Store button rect for click detection
        self._menu_start_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        # ── Version / Credits ──
        credits = render_text(
            "v1.0  |  12 Players  |  Pixel Art", scale=2,
            color=(120, 120, 140),
        )
        cx = (2560 - credits.get_width()) // 2
        screen.blit(credits, (cx, 860))

        # ── How to Play hint ──
        hint = render_text(
            "Vote during the day to eliminate werewolves. Find them before they find you.", scale=2,
            color=(140, 140, 160),
        )
        hx = (2560 - hint.get_width()) // 2
        screen.blit(hint, (hx, 920))

        # ── Decorative bottom line ──
        pygame.draw.line(screen, line_color, (400, 1000), (2560 - 400, 1000), 2)
        pygame.draw.line(screen, (140, 100, 40), (400, 1004), (2560 - 400, 1004), 1)

        # ── Keyboard hint ──
        kb_hint = render_text(
            "[ Press ENTER or click START to begin ]", scale=2,
            color=(100, 100, 120),
        )
        kx = (2560 - kb_hint.get_width()) // 2
        screen.blit(kb_hint, (kx, 1050))

    def update(self, dt: float):
        """Update game state — called every frame by GameEngine.

        Drives the game loop: starts the game, runs NPC decisions for each
        night and day phase, advances phases on a timer.
        """
        # ── Main menu animation ──
        if self._main_menu:
            self._menu_phase_timer += dt
            self._title_glow += dt
            # Use the renderer to show the village background
            self.renderer.set_players(self.game_state.players.players)
            return

        # ── Update renderer day/night animation and action FX ──
        if self.game_state.phase != GamePhase.SETUP:
            is_day_phase = self.game_state.phase.is_day
            self.renderer.set_day_mode(is_day_phase, dt)
            self.renderer.update_fx(dt)
        # --- SETUP → wait for role reveal click then start game ---
        if self.game_state.phase == GamePhase.SETUP:
            if not self._role_revealed:
                return  # wait for human to click the role card
            if not self._game_started:
                self._game_started = True
                self.game_state.start_game()
                self._phase_timer = 0.0
            return

        # ── Sound + Banner: detect phase transitions ──
        current_phase = self.game_state.phase
        if current_phase != self._prev_phase:
            if current_phase == GamePhase.GAME_OVER:
                # Game over sound played in GAME_OVER handling below
                pass
            elif current_phase.is_night:
                night_chime().play() if night_chime() else None
                self._show_banner("NIGHT FALLS")
            elif current_phase.is_day:
                if current_phase != GamePhase.GAME_OVER:
                    day_chime().play() if day_chime() else None
                    self._show_banner("DAY BREAKS")
            # Update ambience on night↔day transitions
            self._update_ambience()
            self._prev_phase = current_phase

        # --- GAME OVER — wait for restart click ---
        if self.game_state.phase == GamePhase.GAME_OVER:
            if not self._sound_played_game_over:
                self._sound_played_game_over = True
                if self.game_state.winner == "village":
                    game_over_victory().play() if game_over_victory() else None
                elif self.game_state.winner == "werewolf":
                    game_over_defeat().play() if game_over_defeat() else None
                elif self.game_state.winner == "town_crier":
                    # Use a playful chime for the independent winner
                    town_crier_chime = night_chime() if night_chime() else None
                    if town_crier_chime:
                        town_crier_chime.play()
            if self._restart_clicked:
                self._restart_game()
            return

        # --- Banner timer ---
        if self._banner_timer > 0:
            self._banner_timer -= dt

        # --- Accumulate phase timer ---
        self._phase_timer += dt
        # Use per-phase duration if available, otherwise fallback
        duration = self._phase_durations.get(self.game_state.phase, self._phase_duration)
        if self._phase_timer < duration:
            return

        phase = self.game_state.phase

        # ── NIGHT PHASES ─────────────────────────────────────────────
        if phase == GamePhase.NIGHT_GUARD:
            self._phase_timer = 0.0
            guard_players = [p for p in self.game_state.players.players if p.role == Role.GUARD]
            if guard_players:
                guard = guard_players[0]
                if guard.alive:
                    target = choose_night_action(self.game_state, guard.index, phase)
                    if target is not None:
                        self.game_state.guard_target = target
                        self.game_state.players.get_player(target).protected = True
                        self.game_state._log("guard", f"Guard protected Player {target}.")
                        self.renderer.show_action(target, self.renderer.FX_SAVE)
            self.game_state.advance_night_phase()

        elif phase == GamePhase.NIGHT_SEER:
            self._phase_timer = 0.0
            seer_players = [p for p in self.game_state.players.players if p.role == Role.SEER]
            if seer_players:
                seer = seer_players[0]
                if seer.alive:
                    target = choose_night_action(self.game_state, seer.index, phase)
                    if target is not None:
                        self.game_state.seer_target = target
                        target_player = self.game_state.players.get_player(target)
                        self.game_state._log(
                            "seer",
                            f"Seer investigated Player {target} — they are a {target_player.role.name_zh}."
                        )
                        self.renderer.show_action(target, self.renderer.FX_SEER)
            self.game_state.advance_night_phase()

        elif phase == GamePhase.NIGHT_WEREWOLF:
            self._phase_timer = 0.0
            werewolf_players = self.game_state.players.get_werewolf_players()
            alive_ww = [p for p in werewolf_players if p.alive]
            if alive_ww:
                target = choose_night_action(self.game_state, alive_ww[0].index, phase)
                if target is not None:
                    self.game_state.werewolf_target = target
                    self.game_state._log("werewolf", f"Werewolves target Player {target}.")
                    self.renderer.show_action(target, self.renderer.FX_KILL)
            self.game_state.advance_night_phase()

        elif phase == GamePhase.NIGHT_WITCH:
            self._phase_timer = 0.0
            should_save, should_poison, poison_target = decide_witch_action(self.game_state)
            if should_save and self.game_state.werewolf_target is not None:
                self.game_state.witch_heal_target = self.game_state.werewolf_target
                self.game_state._log("witch", f"Witch saved Player {self.game_state.werewolf_target}.")
                self.renderer.show_action(self.game_state.werewolf_target, self.renderer.FX_SAVE)
            if should_poison and poison_target is not None:
                self.game_state.witch_poison_target = poison_target
                self.renderer.show_action(poison_target, self.renderer.FX_POISON)
                # Mark the player as poisoned (will be resolved in resolve_night)
                poisoned_player = self.game_state.players.get_player(poison_target)
                if poisoned_player:
                    poisoned_player.poisoned = True
                self.game_state._log("witch", f"Witch poisoned Player {poison_target}.")
            self.game_state.advance_night_phase()

        # ── DAY PHASES ───────────────────────────────────────────────
        elif phase == GamePhase.DAY_ANNOUNCE:
            self._phase_timer = 0.0
            night_result = self.game_state.resolve_night()
            # resolve_night already checks game over — stop if game ended
            if self.game_state.phase == GamePhase.GAME_OVER:
                return
            victim = night_result.get("victim")
            saved = night_result.get("saved", False)
            poisoned = night_result.get("poisoned")
            if victim is not None and not saved:
                victim_player = self.game_state.players.get_player(victim)
                self.game_state._log(
                    "death",
                    f"Player {victim} ({victim_player.name}) was killed during the night!"
                    f" They were a {victim_player.role.name_zh}."
                )
                kill_sting().play() if kill_sting() else None
            if poisoned is not None:
                kill_sting().play() if kill_sting() else None
            if saved:
                self.game_state._log("saved", "Someone was saved by the witch's antidote!")
            if poisoned is not None:
                poisoned_player = self.game_state.players.get_player(poisoned)
                self.game_state._log(
                    "poison",
                    f"Player {poisoned} ({poisoned_player.name}) was poisoned by the witch!"
                    f" They were a {poisoned_player.role.name_zh}."
                )
            # Hunter vengeance for night kills
            if self.game_state.hunter_needs_vengeance:
                hunter_idx = self.game_state._hunter_vengeance_idx
                hunter_target = choose_hunter_vengeance_target(
                    self.game_state, hunter_idx
                )
                if hunter_target is not None:
                    self.game_state.resolve_hunter_vengeance(hunter_target)
                    hunter_victim = self.game_state.players.get_player(hunter_target)
                    self.game_state._log(
                        "elimination",
                        f"Player {hunter_target} ({hunter_victim.name}) was shot by the Hunter's vengeance!"
                    )
                    kill_sting().play() if kill_sting() else None
            # Check if hunter vengeance ended the game
            if self.game_state.players.is_game_over():
                self.game_state.winner = self.game_state.players.get_winning_team()
                self.game_state.phase = GamePhase.GAME_OVER
                winner_display = {
                    "village": "Village",
                    "werewolf": "Werewolf",
                    "town_crier": "Town Crier",
                }.get(self.game_state.winner, self.game_state.winner)
                self.game_state._log("game_over", f"{winner_display} team wins!")

                return
            # resolve_night already checked game over — no need to double-check
            self.game_state.advance_day_phase()

        elif phase == GamePhase.DAY_SHERIFF_ELECTION:
            self._phase_timer = 0.0
            # Sheriff election — each alive NPC nominates someone
            alive_players = self.game_state.players.get_alive_players()
            # Handle human player's sheriff vote
            human_player = self.game_state.players.get_player(self._human_player_idx)
            if human_player and human_player.alive and not self._human_sheriff_voted:
                # Wait for human to click a name (handled in _handle_event)
                # Don't advance yet
                return
            # Auto-abstain for dead human
            if human_player and human_player.alive and self._human_sheriff_voted:
                pass  # Vote already recorded in _handle_event
            elif human_player and not human_player.alive:
                self._human_sheriff_voted = True

            # NPCs vote
            for player in alive_players:
                if player.index == self._human_player_idx and self._human_sheriff_voted:
                    continue  # human already voted
                if player.index in self.game_state.sheriff_votes:
                    continue  # already voted via click
                target = choose_sheriff_vote(self.game_state, player.index)
                if target is not None:
                    self.game_state.sheriff_votes[player.index] = target
                    vote_bell().play() if vote_bell() else None

            # Reset for next time and advance
            self._human_sheriff_voted = False
            self._human_sheriff_target = None
            self.game_state.advance_day_phase()

        elif phase == GamePhase.DAY_DISCUSSION:
            self._phase_timer = 0.0
            # Discussion phase — timer provides pause for player to think
            # Auto-advance to DAY_VOTE after discussion time
            self.game_state.advance_day_phase()

        elif phase == GamePhase.DAY_VOTE:
            self._phase_timer = 0.0
            alive_players = self.game_state.players.get_alive_players()
            human_player = self.game_state.players.get_player(self._human_player_idx)
            # If human is alive and hasn't voted yet, auto-abstain so NPC voting proceeds.
            # Human votes are handled via mouse click in _handle_event.
            if human_player and human_player.alive and not self._human_voted:
                self._human_voted = True
                self.game_state._log("vote", f"Human player {self._human_player_idx} abstained.")
            for player in alive_players:
                if player.index == self._human_player_idx and self._human_voted:
                    continue  # already voted
                if player.index in self.game_state.votes:
                    continue  # already voted
                target = choose_vote_target(self.game_state, player.index)
                if target is not None:
                    self.game_state.votes[player.index] = target
                    target_player = self.game_state.players.get_player(target)
                    if target_player is not None:
                        target_player.voted_by.append(player.index)
                    vote_bell().play() if vote_bell() else None
            self.game_state.advance_day_phase()

        elif phase == GamePhase.DAY_RESULT:
            # Resolve the day vote and advance the game state.
            # We call _resolve_day directly, then check hunter vengeance,
            # then advance to the next phase manually.

            # Reset human vote state for next round
            self._human_voted = False
            self._human_vote_target = None
            vote_result().play() if vote_result() else None

            # Resolve the vote
            self.game_state._resolve_day()

            # Hunter vengeance for vote elimination
            if self.game_state.hunter_needs_vengeance:
                hunter_idx = self.game_state._hunter_vengeance_idx
                hunter_target = choose_hunter_vengeance_target(
                    self.game_state, hunter_idx
                )
                if hunter_target is not None:
                    self.game_state.resolve_hunter_vengeance(hunter_target)
                    hunter_victim = self.game_state.players.get_player(hunter_target)
                    self.game_state._log(
                        "elimination",
                        f"Player {hunter_target} ({hunter_victim.name}) was shot by the Hunter's vengeance!"
                    )
                    kill_sting().play() if kill_sting() else None

            # Check game over after vote elimination AND hunter vengeance
            if self.game_state.players.is_game_over():
                self.game_state.winner = self.game_state.players.get_winning_team()
                self.game_state.phase = GamePhase.GAME_OVER
                winner_display = {
                    "village": "Village",
                    "werewolf": "Werewolf",
                    "town_crier": "Town Crier",
                }.get(self.game_state.winner, self.game_state.winner)
                self.game_state._log("game_over", f"{winner_display} team wins!")

            else:
                # Advance to night
                self.game_state.day += 1
                self.game_state.phase = GamePhase.NIGHT_GUARD
                self.game_state._reset_night_actions()
                self.game_state._log("night_start", f"Day {self.game_state.day} Night begins.")

    def _handle_event(self, event: pygame.event.Event) -> None:
        """Handle input events — mouse clicks on player names in sidebar."""
        # ── Global keyboard shortcuts ──
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                if self._main_menu:
                    self._start_from_menu()
                    return
            # Escape to return to main menu from certain states
            if event.key == pygame.K_ESCAPE:
                if self.game_state.phase == GamePhase.GAME_OVER:
                    self._main_menu = True
                    self.game_state = GameState()
                    self._restart_clicked = False
                    return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            phase = self.game_state.phase

            # ── Main menu click: start game ──
            if self._main_menu:
                if hasattr(self, '_menu_start_rect') and self._menu_start_rect.collidepoint(mx, my):
                    self._start_from_menu()
                return

            # Role reveal click — advance from SETUP
            if phase == GamePhase.SETUP and not self._role_revealed:
                self._role_revealed = True
                return

            # Game over — restart click on the right side of the screen
            if phase == GamePhase.GAME_OVER:
                if SIDEBAR_X <= mx <= 2560 and 1300 <= my <= 1420:
                    self._restart_clicked = True
                return

            # Handle sheriff election phase
            if phase == GamePhase.DAY_SHERIFF_ELECTION and not self._human_sheriff_voted:
                human = self.game_state.players.get_player(self._human_player_idx)
                if human and human.alive:
                    for rect, pidx in self._player_click_rects:
                        if rect.collidepoint(mx, my):
                            # Can't vote for self
                            if pidx == self._human_player_idx:
                                return
                            target_player = self.game_state.players.get_player(pidx)
                            if target_player and target_player.alive:
                                self._human_sheriff_target = pidx
                                self._human_sheriff_voted = True
                                self.game_state.sheriff_votes[self._human_player_idx] = pidx
                                self.game_state._log(
                                    "sheriff_election",
                                    f"{human.name} nominated {target_player.name} for sheriff."
                                )
                            return
                return

            # Only during DAY_VOTE, and only if human hasn't voted yet
            if phase != GamePhase.DAY_VOTE or self._human_voted:
                return
            human = self.game_state.players.get_player(self._human_player_idx)
            if not human or not human.alive:
                return
            for rect, pidx in self._player_click_rects:
                if rect.collidepoint(mx, my):
                    # Can't vote for self
                    if pidx == self._human_player_idx:
                        return
                    target_player = self.game_state.players.get_player(pidx)
                    if target_player and target_player.alive:
                        self._human_vote_target = pidx
                        self._human_voted = True
                        self.game_state.votes[self._human_player_idx] = pidx
                        target_player.voted_by.append(self._human_player_idx)
                        # Add log entry
                        self.game_state._log(
                            "vote",
                            f"Player {self._human_player_idx} voted for Player {pidx}."
                        )
                    return

    def _show_banner(self, text: str) -> None:
        """Show a dramatic banner announcement."""
        self._banner_text = text
        self._banner_timer = self._banner_duration

    def _update_ambience(self) -> None:
        """Start/stop ambient sound based on current phase."""
        phase = self.game_state.phase
        if phase == GamePhase.SETUP:
            return
        is_night = phase.is_night
        desired = "night" if is_night else "day"
        if desired == self._current_ambience:
            return
        # Stop current ambience
        if self._ambience_channel is not None:
            self._ambience_channel.stop()
            self._ambience_channel = None
        self._current_ambience = ""
        # Start new ambience
        try:
            if is_night:
                amb = night_ambience()
            else:
                amb = day_ambience()
            if amb:
                ch = pygame.mixer.find_channel(True)
                if ch:
                    ch.play(amb, loops=-1)
                    self._ambience_channel = ch
                    self._current_ambience = desired
        except pygame.error:
            pass

    @property
    def _is_night(self) -> bool:
        """Whether the current phase is a night phase (darker visuals)."""
        return self.game_state.phase.is_night or self.game_state.phase == GamePhase.SETUP

    def _draw_role_reveal(self, screen: pygame.Surface, state):
        """Draw the role-reveal card at game start."""
        human = state.players.get_player(self._human_player_idx)
        if human is None:
            return

        # Large centered card
        card_w = 800
        card_h = 500
        card_x = (2560 - card_w) // 2
        card_y = (1440 - card_h) // 2

        # Card background with border
        card = pygame.Surface((card_w, card_h))
        card.fill((40, 30, 20))
        # Border glow
        pygame.draw.rect(card, (200, 160, 80), (0, 0, card_w, card_h), 4)
        screen.blit(card, (card_x, card_y))

        # Role icon area (decorative)
        icon_x = card_x + 40
        icon_y = card_y + 40
        icon_w = 120
        icon_h = 120
        pygame.draw.rect(screen, (80, 60, 40), (icon_x, icon_y, icon_w, icon_h))
        pygame.draw.rect(screen, (160, 120, 60), (icon_x, icon_y, icon_w, icon_h), 2)

        # Role name
        role_text = render_text(
            human.role.name.capitalize(),
            scale=5, color=(255, 200, 100), shadow=(80, 50, 10)
        )
        rx = icon_x + (icon_w - role_text.get_width()) // 2
        ry = icon_y + (icon_h - role_text.get_height()) // 2
        screen.blit(role_text, (rx, ry))

        # Role title
        title_text = render_text(
            "Your Role",
            scale=4, color=(200, 180, 140), shadow=(40, 30, 10)
        )
        screen.blit(title_text, (card_x + 200, card_y + 50))

        # Role description
        desc = human.role.description
        desc_text = render_text(
            desc,
            scale=2, color=(200, 200, 200), shadow=(20, 20, 20)
        )
        screen.blit(desc_text, (card_x + 200, card_y + 110))

        # Team info
        team_colors = {}
        try:
            from game.roles import Team
            team_colors = {
                Team.VILLAGE: (140, 200, 140),
                Team.WEREWOLF: (200, 100, 100),
                Team.INDEPENDENT: (200, 180, 100),
            }
        except ImportError:
            pass
        team_color = team_colors.get(human.role.team, (200, 200, 200)) if hasattr(human.role, 'team') else (200, 200, 200)
        team_text = render_text(
            f"Team: {human.role.team.name.capitalize()}" if hasattr(human.role, 'team') and human.role.team else "",
            scale=2, color=team_color, shadow=(20, 20, 20)
        )
        screen.blit(team_text, (card_x + 200, card_y + 170))

        # Instruction
        instr_text = render_text(
            "[ Click anywhere to start ]",
            scale=2, color=(160, 160, 200), shadow=(20, 20, 40)
        )
        ix = card_x + (card_w - instr_text.get_width()) // 2
        screen.blit(instr_text, (ix, card_y + card_h - 60))

    def _start_from_menu(self) -> None:
        """Transition from main menu to game."""
        self._main_menu = False
        self._menu_phase_timer = 0.0
        self._title_glow = 0.0
        self._phase_timer = 0.0
        self._role_revealed = False
        self._game_started = False
        self.game_state = GameState()
        self.renderer.invalidate_cache()
        # Reset human state
        self._human_voted = False
        self._human_vote_target = None
        self._human_sheriff_voted = False
        self._human_sheriff_target = None
        self._sound_played_game_over = False
        self._prev_phase = GamePhase.SETUP

    def render(self, screen: pygame.Surface):
        state = self.game_state

        # ── MAIN MENU ──
        if self._main_menu:
            self._draw_main_menu(screen)
            return

        is_night = self._is_night

        # ── 0. Update player positions for renderer ──
        self.renderer.set_players(state.players.players)

        # ── 1. Render village background + player characters ──
        self.renderer.render(screen, is_night, time=self._phase_timer)

        # ── 2. Persistent phase indicator badge (top-left of village view) ──
        # Build a concise phase+day label
        if state.phase == GamePhase.SETUP:
            indicator_text = "🌙 Setup"
        elif state.phase == GamePhase.GAME_OVER:
            indicator_text = "Game Over"
        else:
            # Format: "Day 1 · Voting" or "Night 1 · Werewolves"
            day_prefix = "Day" if state.phase.is_day else "Night"
            # Strip the leading "Day — " or "Night — " prefix from display_name
            raw_short = state.phase.display_name
            for strip_prefix in ("Day — ", "Night — "):
                if raw_short.startswith(strip_prefix):
                    raw_short = raw_short[len(strip_prefix):]
                    break
            indicator_text = f"{day_prefix} {state.day} · {raw_short}"
        indicator_surf = render_text(
            indicator_text, scale=3,
            color=(255, 220, 150) if not is_night else (150, 180, 220),
            shadow=(30, 20, 10) if not is_night else (20, 30, 60),
        )
        # Dark background pill
        padding_x, padding_y = 16, 8
        pill_w = indicator_surf.get_width() + padding_x * 2
        pill_h = indicator_surf.get_height() + padding_y * 2
        pill = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
        pill_bg = (20, 15, 10, 200) if is_night else (30, 25, 15, 200)
        pill.fill(pill_bg)
        # Draw rounded-rect corners manually (pixel style)
        pygame.draw.rect(pill, pill_bg, (0, 0, pill_w, pill_h), border_radius=0)
        # Thin border
        border_col = (120, 90, 40) if not is_night else (80, 80, 120)
        pygame.draw.rect(pill, border_col, (0, 0, pill_w, pill_h), 2)
        screen.blit(pill, (12, 12))
        screen.blit(indicator_surf, (12 + padding_x, 12 + padding_y))

        # ── 2b. Phase transition banner ──
        if self._banner_timer > 0:
            banner_text = self._banner_text
            banner_scale = 5
            banner_color = (200, 200, 100) if "DAY" in banner_text else (100, 130, 200)
            banner_surf = render_text(
                banner_text, scale=banner_scale, color=banner_color,
                shadow=(20, 20, 60),
            )
            # Centre banner in the village area
            bx = (SIDEBAR_X - banner_surf.get_width()) // 2
            by = 1440 // 3
            # Dark background bar
            bar_surf = pygame.Surface((banner_surf.get_width() + 60, banner_surf.get_height() + 24), pygame.SRCALPHA)
            bar_surf.fill((0, 0, 0, 180))
            screen.blit(bar_surf, (bx - 30, by - 12))
            screen.blit(banner_surf, (bx, by))

        # ── 3. Semi-transparent overlay for UI readability ──
        overlay = pygame.Surface((640, 1440), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160) if is_night else (0, 0, 0, 100))
        screen.blit(overlay, (SIDEBAR_X - 20, 0))

        # ── ROLE REVEAL CARD (SETUP phase) ──
        if state.phase == GamePhase.SETUP and not self._role_revealed:
            self._draw_role_reveal(screen, state)
            return

        # ── 3. Title / phase info ──
        # Decorative top banner background
        banner_rect = pygame.Rect(SIDEBAR_X - 20, 0, 680, 100)
        banner_color = (40, 30, 15) if is_night else (55, 45, 25)
        pygame.draw.rect(screen, banner_color, banner_rect)
        pygame.draw.rect(screen, (120, 90, 40), banner_rect, 2)

        title_text = render_text(
            "Pixel Werewolf", scale=FONT_SCALE_TITLE, color=(255, 220, 150),
            shadow=(60, 40, 10)
        )
        screen.blit(title_text, (SIDEBAR_X + 10, SIDEBAR_Y))

        phase_label = render_text(
            f"{state.phase.display_name}", scale=FONT_SCALE_PLAYER,
            color=(200, 200, 255) if is_night else (255, 255, 200),
            shadow=(30, 30, 60) if is_night else (60, 60, 30)
        )
        screen.blit(phase_label, (SIDEBAR_X + 10, SIDEBAR_Y + 40))

        day_label = render_text(
            f"Day {state.day}", scale=FONT_SCALE_PLAYER, color=(200, 200, 200),
            shadow=(40, 40, 40)
        )
        screen.blit(day_label, (SIDEBAR_X + 200, SIDEBAR_Y + 40))

        # ── 3a. Alive / Total counter with faction balance ──
        alive_count = sum(1 for p in state.players.players if p.alive)
        total_count = len(state.players.players)
        alive_label = render_text(
            f"Alive: {alive_count}/{total_count}", scale=FONT_SCALE_PLAYER,
            color=(180, 255, 180) if alive_count > total_count // 2 else (255, 200, 150),
            shadow=(20, 40, 20) if alive_count > total_count // 2 else (40, 30, 15)
        )
        screen.blit(alive_label, (SIDEBAR_X + 340, SIDEBAR_Y + 40))

        # Faction balance
        from game.roles import Team
        werewolf_count = sum(1 for p in state.players.players if p.alive and p.role.team == Team.WEREWOLF)
        village_count = sum(1 for p in state.players.players if p.alive and p.role.team == Team.VILLAGE)
        balance_text = f"W{werewolf_count}:V{village_count}"
        balance_label = render_text(
            balance_text, scale=FONT_SCALE_LOG,
            color=(255, 150, 150) if is_night else (200, 180, 100),
        )
        screen.blit(balance_label, (SIDEBAR_X + 500, SIDEBAR_Y + 48))

        # Instruction text for current phase
        human = state.players.get_player(self._human_player_idx)
        instr_y = SIDEBAR_Y + 80
        if state.phase == GamePhase.DAY_SHERIFF_ELECTION:
            if human and human.alive:
                if self._human_sheriff_voted:
                    vote_inst = render_text(
                        "Nomination recorded — others voting...", scale=FONT_SCALE_LOG,
                        color=(180, 200, 220)
                    )
                else:
                    vote_inst = render_text(
                        "Click a player's name to nominate them for Sheriff",
                        scale=FONT_SCALE_LOG, color=(255, 200, 100)
                    )
                screen.blit(vote_inst, (SIDEBAR_X + 10, instr_y))
        elif state.phase == GamePhase.DAY_VOTE and human and human.alive:
            if not self._human_voted:
                vote_inst = render_text(
                    "Click a player to vote them out",
                    scale=FONT_SCALE_LOG, color=(255, 200, 100)
                )
                screen.blit(vote_inst, (SIDEBAR_X + 10, instr_y))

        # ── 3b. Click-handling: build player click rects during DAY_VOTE or DAY_SHERIFF_ELECTION ──
        self._player_click_rects.clear()
        clickable_phases = (GamePhase.DAY_VOTE, GamePhase.DAY_SHERIFF_ELECTION)
        if state.phase in clickable_phases and self._human_player_idx < len(state.players.players):
            human = state.players.get_player(self._human_player_idx)
            if human and human.alive:
                yy = SIDEBAR_Y + LIST_START
                for p in state.players.players:
                    if p.alive and p.index != self._human_player_idx:
                        click_rect = pygame.Rect(SIDEBAR_X, yy - 2, 320, LIST_SPACING)
                        self._player_click_rects.append((click_rect, p.index))
                    yy += LIST_SPACING

        # ── 3c. Decorative section separator ──
        sep_y = SIDEBAR_Y + 88
        pygame.draw.line(screen, (80, 60, 30), (SIDEBAR_X + 10, sep_y), (SIDEBAR_X + 650, sep_y), 1)
        pygame.draw.line(screen, (55, 50, 30), (SIDEBAR_X + 10, sep_y + 1), (SIDEBAR_X + 650, sep_y + 1), 1)
        # Section header
        header_text = render_text("Players", scale=FONT_SCALE_SMALL, color=(180, 180, 140))
        screen.blit(header_text, (SIDEBAR_X + 10, sep_y + 4))

        # ── 4. Player list (sidebar) ──
        y = SIDEBAR_Y + LIST_START
        from game.roles import Team
        for p in state.players.players:
            is_human_target = (self._human_vote_target == p.index)

            # Determine team colour and faction bar colour
            if p.alive:
                if state.phase.is_day or state.phase == GamePhase.GAME_OVER:
                    if p.role.team == Team.WEREWOLF:
                        team_color = (255, 160, 160)
                        faction_bar_col = (200, 50, 50)
                    elif p.role.team == Team.INDEPENDENT:
                        team_color = (255, 220, 100)
                        faction_bar_col = (200, 180, 60)
                    else:
                        team_color = (200, 220, 240)
                        faction_bar_col = (60, 140, 200)
                else:
                    team_color = (220, 220, 220)
                    faction_bar_col = (100, 100, 100)
            else:
                team_color = (80, 80, 80)
                faction_bar_col = (50, 50, 50)

            show_role = (p.alive and state.phase.is_day) or state.phase == GamePhase.GAME_OVER or not p.alive

            # Faction colour bar on left edge
            bar_rect = pygame.Rect(SIDEBAR_X, y - 2, 4, LIST_SPACING - 2)
            pygame.draw.rect(screen, faction_bar_col, bar_rect)

            # Vote-target highlight
            if is_human_target:
                highlight_rect = pygame.Rect(SIDEBAR_X + 4, y - 2, 400, LIST_SPACING - 2)
                pygame.draw.rect(screen, (60, 50, 20), highlight_rect)
                pygame.draw.rect(screen, (200, 180, 80), highlight_rect, 2)
                team_color = (255, 220, 100)
            elif p.index == self._human_player_idx:
                self_highlight = pygame.Rect(SIDEBAR_X + 4, y - 2, 400, LIST_SPACING - 2)
                pygame.draw.rect(screen, (30, 40, 60), self_highlight)
                team_color = (180, 220, 255)

            # Pixel-art role icon (or skull for dead)
            if p.alive:
                screen.blit(get_role_icon(p.role), (SIDEBAR_X + 8, y + 4))
            else:
                screen.blit(ICON_DEAD, (SIDEBAR_X + 8, y + 4))

            # Player name
            name_part = p.name[:12]
            name_x = SIDEBAR_X + 30
            line = render_text(name_part, scale=FONT_SCALE_PLAYER, color=team_color)
            screen.blit(line, (name_x, y))

            # Sheriff badge (pixel art)
            if p.is_sheriff:
                screen.blit(ICON_SHERIFF, (name_x + len(name_part) * 10 + 4, y + 1))

            # Role label (right side)
            if show_role and not p.alive:
                role_label = render_text(p.role.name_zh, scale=FONT_SCALE_SMALL, color=(100, 100, 100))
            elif show_role:
                role_label = render_text(p.role.name_zh, scale=FONT_SCALE_SMALL, color=(140, 180, 140))
            else:
                role_label = render_text("???", scale=FONT_SCALE_SMALL, color=(100, 100, 100))
            screen.blit(role_label, (SIDEBAR_X + 170, y + 4))

            # Vote count during DAY_VOTE
            if state.phase == GamePhase.DAY_VOTE and p.alive:
                votes = sum(1 for v in state.votes.values() if v == p.index)
                if votes > 0:
                    vote_surf = render_text(f"[{votes}]", scale=FONT_SCALE_PLAYER, color=(255, 180, 80))
                    screen.blit(vote_surf, (SIDEBAR_X + 300, y))

            # Sheriff nomination target highlight during election
            if (state.phase == GamePhase.DAY_SHERIFF_ELECTION
                    and p.alive
                    and p.index == self._human_sheriff_target):
                nom_surf = render_text("[★]", scale=FONT_SCALE_PLAYER, color=(255, 215, 0))
                screen.blit(nom_surf, (SIDEBAR_X + 300, y))

            y += LIST_SPACING

        # ── 5. Game log ──
        y = LOG_START_Y - 24
        # Section separator (double line for decoration)
        pygame.draw.line(screen, (80, 60, 30), (SIDEBAR_X + 10, y), (SIDEBAR_X + 650, y), 1)
        pygame.draw.line(screen, (55, 50, 30), (SIDEBAR_X + 10, y + 1), (SIDEBAR_X + 650, y + 1), 1)
        y += 8
        log_label = render_text("Game Log", scale=FONT_SCALE_SMALL, color=(180, 180, 140))
        screen.blit(log_label, (SIDEBAR_X + 10, y))
        y += 22

        for entry in state.log[-8:]:
            # Determine log entry colour and prefix icon
            msg = entry["message"]
            prefix = None
            if any(w in msg for w in ["werewolf", "Wolf", "wolf"]):
                color = (200, 160, 160)
                prefix = get_role_icon(Role.WEREWOLF)
            elif any(w in msg for w in ["witch", "Witch"]):
                color = (200, 170, 200)
                prefix = get_role_icon(Role.WITCH)
            elif any(w in msg for w in ["seer", "Seer"]):
                color = (160, 180, 220)
                prefix = get_role_icon(Role.SEER)
            elif any(w in msg for w in ["guard", "Guard"]):
                color = (160, 200, 220)
                prefix = get_role_icon(Role.GUARD)
            elif any(w in msg for w in ["hunter", "Hunter", "shot"]):
                color = (220, 180, 120)
                prefix = get_role_icon(Role.HUNTER)
            elif any(w in msg for w in ["vote", "lynched", "hanged", "accused"]):
                color = (200, 190, 150)
            elif any(w in msg for w in ["night", "Night"]):
                color = (150, 150, 200)
            else:
                color = (200, 200, 200)
            # Draw role icon prefix if applicable
            if prefix:
                screen.blit(prefix, (SIDEBAR_X + 10, y))
                text = render_text(msg, scale=FONT_SCALE_LOG, color=color)
                screen.blit(text, (SIDEBAR_X + 28, y))
            else:
                text = render_text(msg, scale=FONT_SCALE_LOG, color=color)
                screen.blit(text, (SIDEBAR_X + 10, y))
            y += LOG_SPACING

        # ── 5b. Instruction text (context-aware) ──
        instr_y = 1400
        if state.phase == GamePhase.DAY_VOTE and self._human_voted:
            instr = render_text("Vote cast - awaiting resolution...", scale=FONT_SCALE_LOG, color=(160, 200, 160))
        elif (state.phase == GamePhase.DAY_VOTE and not self._human_voted
              and self._human_player_idx < len(state.players.players)
              and state.players.get_player(self._human_player_idx).alive):
            instr = render_text("Click a villager name above to cast your vote", scale=FONT_SCALE_LOG, color=(255, 200, 100))
        elif state.phase == GamePhase.GAME_OVER:
            winner = state.winner or "unknown"
            winner_display = {
                "village": "Village",
                "werewolf": "Werewolf",
                "town_crier": "Town Crier",
            }.get(winner, winner)
            instr = render_text(f"Game Over - {winner_display} wins!", scale=FONT_SCALE_PLAYER, color=(255, 220, 150), shadow=(80, 60, 20))
            restart_instr = render_text("[ Click bottom-right to restart ]", scale=FONT_SCALE_LOG, color=(180, 180, 160))
            screen.blit(restart_instr, (SIDEBAR_X + 10, instr_y + 40))
            # Draw a visible restart button area
            pygame.draw.rect(screen, (80, 55, 30), (SIDEBAR_X, 1300, 660, 120))
            pygame.draw.rect(screen, (110, 75, 40), (SIDEBAR_X, 1300, 660, 120), 2)
            restart_btn = render_text("RESTART GAME", scale=FONT_SCALE_PLAYER, color=(220, 200, 160), shadow=(60, 40, 20))
            screen.blit(restart_btn, (SIDEBAR_X + 200, 1330))
        else:
            instr = render_text("Game auto-plays - Watch the story unfold...", scale=FONT_SCALE_LOG, color=(120, 120, 140))
        screen.blit(instr, (SIDEBAR_X + 10, instr_y))

        # ── 6. Night overlay darkness & vignette ──
        if is_night:
            # Darken edges for atmosphere (vignette effect — pixel style, no blur)
            vignette = pygame.Surface((2560, 1440), pygame.SRCALPHA)
            for i in range(8):
                alpha = 6 - i
                if alpha < 0:
                    alpha = 0
                pygame.draw.rect(
                    vignette, (0, 0, 20, alpha * 2),
                    (i * 4, i * 4, 2560 - i * 8, 1440 - i * 8),
                    4,
                )
            screen.blit(vignette, (0, 0))

        # ── 7. Decorative wooden frame around village view ──
        # Left side border (village view area: 0..1900)
        border_color = (65, 45, 25)
        border_light = (85, 60, 35)
        # Bottom border strip (at the bottom of village view)
        pygame.draw.rect(screen, border_color, (0, 1440 - 16, SIDEBAR_X, 16))
        pygame.draw.rect(screen, border_light, (0, 1440 - 16, SIDEBAR_X, 2))
        # Top border strip
        pygame.draw.rect(screen, border_color, (0, 0, SIDEBAR_X, 8))
        pygame.draw.rect(screen, border_light, (0, 6, SIDEBAR_X, 2))

    def run(self):
        self.engine.run()


if __name__ == "__main__":
    game = WerewolfGame()
    if game.init():
        game.run()
