#!/usr/bin/env python3
"""Pixel Werewolf — Python/pygame entry point."""

from __future__ import annotations

from typing import Optional

import pygame

from game.bitmap_font import render_text
from scripts.game_engine import GameEngine
from game.game_state import GameState
from game.phases import GamePhase
from game.renderer import VillageRenderer
from game.roles import Role

# NPC AI
from game.npc_ai import (
    choose_hunter_vengeance_target,
    choose_night_action,
    choose_vote_target,
    decide_witch_action,
)

# Procedural sound effects
from game.sound import (
    day_chime,
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
            GamePhase.DAY_DISCUSSION: 5.0,
            GamePhase.DAY_VOTE: 6.0,
            GamePhase.DAY_RESULT: 3.0,
            GamePhase.GAME_OVER: 6.0,
            GamePhase.SETUP: 0.5,
        }
        self._game_started: bool = False
        # Sound state
        self._prev_phase: GamePhase = GamePhase.SETUP
        self._sound_played_game_over: bool = False
        self._role_revealed: bool = False
        # Human player interaction state
        self._human_player_idx: int = 0
        self._human_voted: bool = False
        self._human_vote_target: Optional[int] = None
        # Track clickable player name rectangles in sidebar
        self._player_click_rects: list[tuple[pygame.Rect, int]] = []

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

    def update(self, dt: float):
        """Update game state — called every frame by GameEngine.

        Drives the game loop: starts the game, runs NPC decisions for each
        night and day phase, advances phases on a timer.
        """
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

        # ── Sound: detect phase transitions ──
        current_phase = self.game_state.phase
        if current_phase != self._prev_phase:
            if current_phase == GamePhase.GAME_OVER:
                # Game over sound played in GAME_OVER handling below
                pass
            elif current_phase.is_night:
                night_chime().play() if night_chime() else None
            elif current_phase.is_day:
                if current_phase != GamePhase.GAME_OVER:
                    day_chime().play() if day_chime() else None
            self._prev_phase = current_phase

        # --- GAME OVER — stop advancing; play sound once ---
        if self.game_state.phase == GamePhase.GAME_OVER:
            if not self._sound_played_game_over:
                self._sound_played_game_over = True
                if self.game_state.winner == "village":
                    game_over_victory().play() if game_over_victory() else None
                elif self.game_state.winner == "werewolf":
                    game_over_defeat().play() if game_over_defeat() else None
            return

        # --- Accumulate phase timer ---
        self._phase_timer += dt
        # Use per-phase duration if available, otherwise fallback
        duration = self._phase_durations.get(self.game_state.phase, self._phase_duration)
        if self._phase_timer < duration:
            return

        phase = self.game_state.phase
        timer_expired = True  # flag: phase handler may use to override human-wait

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
            if should_save and self.game_state.last_night_victim is not None:
                self.game_state.witch_heal_target = self.game_state.last_night_victim
                self.game_state._log("witch", f"Witch saved Player {self.game_state.last_night_victim}.")
                self.renderer.show_action(self.game_state.last_night_victim, self.renderer.FX_SAVE)
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
            if self.game_state.werewolf_target is not None:
                night_result = self.game_state.resolve_night()
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
                # Check game over after night kills
                if self.game_state.players.is_game_over():
                    self.game_state.winner = self.game_state.players.get_winning_team()
                    self.game_state.phase = GamePhase.GAME_OVER
                    self.game_state._log("game_over", f"{self.game_state.winner} team wins!")
                    return
            self.game_state.advance_day_phase()

        elif phase == GamePhase.DAY_DISCUSSION:
            self._phase_timer = 0.0
            # Discussion phase — placeholder, advances after timer
            self.game_state.advance_day_phase()

        elif phase == GamePhase.DAY_VOTE:
            self._phase_timer = 0.0
            alive_players = self.game_state.players.get_alive_players()
            human_player = self.game_state.players.get_player(self._human_player_idx)
            # If human is alive and hasn't voted yet, try to wait for click input.
            # When timer_expired is True, it means this is the FIRST frame the
            # timer has elapsed — auto-abstain the human so NPC voting proceeds.
            if human_player and human_player.alive and not self._human_voted:
                if not timer_expired:
                    return  # wait for human click within the duration
                # Timer expired — human abstains this round
                self._human_voted = True
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
            # Day result already handled by _resolve_day inside advance_day_phase.
            # It may set phase to GAME_OVER — don't duplicate the log.

            # Reset human vote state for next round
            self._human_voted = False
            self._human_vote_target = None
            vote_result().play() if vote_result() else None

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

            self.game_state.advance_day_phase()

    def _handle_event(self, event: pygame.event.Event) -> None:
        """Handle input events — mouse clicks on player names in sidebar."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            phase = self.game_state.phase

            # Role reveal click — advance from SETUP
            if phase == GamePhase.SETUP and not self._role_revealed:
                self._role_revealed = True
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

    def render(self, screen: pygame.Surface):
        state = self.game_state
        is_night = self._is_night

        # ── 0. Update player positions for renderer ──
        self.renderer.set_players(state.players.players)

        # ── 1. Render village background + player characters ──
        self.renderer.render(screen, is_night)

        # ── 2. Semi-transparent overlay for UI readability ──
        overlay = pygame.Surface((640, 1440), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160) if is_night else (0, 0, 0, 100))
        screen.blit(overlay, (SIDEBAR_X - 20, 0))

        # ── ROLE REVEAL CARD (SETUP phase) ──
        if state.phase == GamePhase.SETUP and not self._role_revealed:
            self._draw_role_reveal(screen, state)
            return

        # ── 3. Title / phase info ──
        title_text = render_text(
            "Pixel Werewolf", scale=FONT_SCALE_TITLE, color=(255, 220, 150),
            shadow=(60, 40, 10)
        )
        screen.blit(title_text, (SIDEBAR_X, SIDEBAR_Y))

        phase_label = render_text(
            f"{state.phase.display_name}", scale=FONT_SCALE_PLAYER,
            color=(200, 200, 255) if is_night else (255, 255, 200),
            shadow=(30, 30, 60) if is_night else (60, 60, 30)
        )
        screen.blit(phase_label, (SIDEBAR_X, SIDEBAR_Y + 36))

        day_label = render_text(
            f"Day {state.day}", scale=FONT_SCALE_PLAYER, color=(200, 200, 200),
            shadow=(40, 40, 40)
        )
        screen.blit(day_label, (SIDEBAR_X, SIDEBAR_Y + 68))

        # ── 3b. Click-handling: build player click rects during DAY_VOTE ──
        self._player_click_rects.clear()
        if state.phase == GamePhase.DAY_VOTE and self._human_player_idx < len(state.players.players):
            human = state.players.get_player(self._human_player_idx)
            if human and human.alive:
                yy = SIDEBAR_Y + LIST_START
                for p in state.players.players:
                    if p.alive and p.index != self._human_player_idx:
                        click_rect = pygame.Rect(SIDEBAR_X, yy - 2, 320, LIST_SPACING)
                        self._player_click_rects.append((click_rect, p.index))
                    yy += LIST_SPACING

        # ── 4. Player list (sidebar) ──
        y = SIDEBAR_Y + LIST_START
        for p in state.players.players:
            # Highlight if this player is selected as human vote target
            is_human_target = (self._human_vote_target == p.index)
            
            if p.alive:
                color = (220, 220, 220)
                prefix = ">"
                role_name_label = p.role.name_zh if state.phase.is_day else "???"
            else:
                color = (100, 100, 100)
                prefix = "x"
                role_name_label = p.role.name_zh

            # Draw vote-target highlight background
            if is_human_target:
                highlight_rect = pygame.Rect(SIDEBAR_X - 4, y - 2, 330, LIST_SPACING - 2)
                pygame.draw.rect(screen, (60, 50, 20), highlight_rect)
                pygame.draw.rect(screen, (200, 180, 80), highlight_rect, 2)
                color = (255, 220, 100)
            elif p.index == self._human_player_idx:
                color = (180, 220, 255)  # highlight self in a different colour

            sheriff_mark = "[S]" if p.is_sheriff else ""
            line = render_text(
                f"{prefix} {p.name} {sheriff_mark}[{role_name_label}]",
                scale=FONT_SCALE_PLAYER, color=color
            )
            screen.blit(line, (SIDEBAR_X + 4, y))
            
            # Show vote count during DAY_VOTE
            if state.phase == GamePhase.DAY_VOTE and p.alive:
                votes = sum(1 for v in state.votes.values() if v == p.index)
                if votes > 0:
                    vote_surf = render_text(f"[{votes}]", scale=FONT_SCALE_PLAYER, color=(255, 180, 80))
                    screen.blit(vote_surf, (SIDEBAR_X + 280, y))

            y += LIST_SPACING

        # ── 5. Game log ──
        y = LOG_START_Y
        log_label = render_text("-- Game Log --", scale=FONT_SCALE_LOG, color=(160, 160, 160))
        screen.blit(log_label, (SIDEBAR_X, y))
        y += LOG_SPACING

        for entry in state.log[-8:]:
            text = render_text(entry["message"], scale=FONT_SCALE_LOG, color=(160, 160, 160))
            screen.blit(text, (SIDEBAR_X, y))
            y += LOG_SPACING

        # ── 5b. Instruction text (context-aware) ──
        instr_y = 1400
        if state.phase == GamePhase.DAY_VOTE and self._human_voted:
            instr = render_text("Vote cast - advancing...", scale=FONT_SCALE_LOG, color=(160, 200, 160))
        elif (state.phase == GamePhase.DAY_VOTE and not self._human_voted
              and self._human_player_idx < len(state.players.players)
              and state.players.get_player(self._human_player_idx).alive):
            instr = render_text("Click a name above to cast your vote", scale=FONT_SCALE_LOG, color=(255, 200, 100))
        elif state.phase == GamePhase.GAME_OVER:
            winner = state.winner or "unknown"
            instr = render_text(f"Game Over - {winner} team wins!", scale=FONT_SCALE_PLAYER, color=(255, 220, 150), shadow=(80, 60, 20))
        else:
            instr = render_text("Game auto-plays - Watch the story unfold", scale=FONT_SCALE_LOG, color=(120, 120, 140))
        screen.blit(instr, (SIDEBAR_X, instr_y))

        # ── 6. Night overlay darkness ──
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

    def run(self):
        self.engine.run()


if __name__ == "__main__":
    game = WerewolfGame()
    if game.init():
        game.run()
