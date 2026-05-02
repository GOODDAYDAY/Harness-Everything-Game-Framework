#!/usr/bin/env python3
"""Main game loop — WerewolfGame class.

Contains the primary game controller: setup, event handling, update/render.
This is the largest single module; consider splitting render() further.
"""

from __future__ import annotations

import random
from collections import Counter
from typing import Optional

import pygame

from game.camera import Camera
from scripts.game_engine import GameEngine
from game.game_state import GameState
from game.phases import GamePhase
from game.renderer import VillageRenderer, WeatherState
from game.roles import Role
from game.text import _, LANG
from game.ui_panels import (
    draw_sidebar_background,
    draw_phase_indicator,
    draw_phase_instruction,
    draw_player_list,
    draw_game_log,
    draw_narration_header,
    draw_vote_result_box,
    draw_spectator_mode_banner,
    draw_game_result_panel,
    draw_game_result_panel_wolf_pov,
    draw_election_banner,
    draw_sheriff_result,
    draw_skill_status_panel,
    draw_wolf_vote_display,
    draw_discussion_bubble,
    draw_day_banner,
    draw_witch_potion_display,
    draw_hunter_vengeance_display,
    draw_guard_target_display,
    draw_seer_target_display,
    update_vote_pulses,
    trigger_elimination_highlight,
    update_elimination_timers,
    reset_vote_pulses,
)
from game import ui_panels
from game.npc_ai import (
    choose_night_action,
    choose_vote_target,
    decide_witch_action,
)
from game.npc_discussion import (
    generate_discussion,
    reset_context,
    set_night_victim,
    set_voted_out,
)
from game.player import Player
from game.sound import (
    ambient_day,
    ambient_night,
    button_click,
    vote_cast,
    vote_result,
    kill_sting,
    death_announce,
    day_music,
    night_music,
    victory_jingle,
    defeat_jingle,
    election_music,
)


# ── Convenience boolean for current language ──
LANG_IS_ZH = (LANG == "zh")


class WerewolfGame:
    """Main game controller: setup, event handling, update/render."""

    def __init__(self) -> None:
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
        self._phase_duration: float = 1.5  # fallback; per-phase durations in _phase_durations

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
            GamePhase.DAY_TRIAL: 4.0,
            GamePhase.DAY_VOTE_RESULT: 3.0,

            GamePhase.GAME_OVER: 5.0,
        }

        # Phase transition smoothing
        self._phase_blend: float = 0.0  # 0→1 transition progress
        self._in_transition: bool = False

        # NPC AI timers
        self._ai_action_delay: float = 0.0
        self._ai_thinking: bool = False
        self._ai_current_action: str = ""

        # Discussion state
        self._discussion_active: bool = False
        self._discussion_timer: float = 0.0
        self._discussion_interval: float = 3.0
        self._current_speaker: Optional[Player] = None
        self._discussion_text: str = ""
        self._last_discussion_time: float = 0.0

        # Death announcement state
        self._death_announce_active: bool = False
        self._death_announce_timer: float = 0.0
        self._death_announce_text: str = ""
        self._death_announce_role: str = ""
        self._death_announce_done: bool = False

        # Vote result display
        self._vote_result_active: bool = False
        self._vote_result_timer: float = 0.0
        self._vote_result_text: str = ""
        self._vote_result_plural: bool = False

        # Sheriff vote result display
        self._sheriff_vote_result_active: bool = False
        self._sheriff_vote_result_timer: float = 0.0
        self._sheriff_vote_result_text: str = ""

        # Flash effect (e.g. lightning, wolf howl)
        self._flash_active: bool = False
        self._flash_color: tuple[int, int, int] = (255, 255, 255)
        self._flash_duration: float = 0.3
        self._flash_timer: float = 0.0

        # Game over banner timer
        self._game_over_timer: float = 0.0

        # Eye/screen shake
        self._shake_intensity: float = 0.0
        self._shake_timer: float = 0.0
        self._shake_offset: tuple[int, int] = (0, 0)
        self._shake_style: str = "normal"  # 'normal' | 'hard' | 'quake'

        # Sound cooldowns to avoid stacking
        self._last_ambient_play: float = 0.0

        # NPC night-action confirmations (lazy: store once per night)
        self._night_actions_confirmed: bool = False

        # Track night action icons shown
        self._night_action_icons_shown: set[int] = set()

        # Human player index (default: player 0)
        self._human_player_idx: int = 0

        # Witch action mode: False = heal, True = poison
        self._witch_mode_is_poison: bool = False

        # Voting UI
        self._voting_player_idx: int = 0
        self._vote_scroll_offset: int = 0

        # Wolves in night phase
        self._wolf_votes: dict[int, int] = {}  # wolf_idx → target_idx

        # Witch UI
        self._witch_save_used: bool = False
        self._witch_kill_used: bool = False

        # Guard UI
        self._guard_last_target: Optional[int] = None

        # Hunter UI
        self._hunter_vengeance_target: Optional[int] = None

        # AI state tracking
        self._ai_votes_cast: bool = False

        # Transition to discussion scene
        self._discussion_phase_active: bool = False

        # Death animation state
        self._death_animation_active: bool = False
        self._death_animation_data: dict = {}

        # Night action feedback display
        self._night_feedback_state: dict[str, bool] = {
            "seer": False,
            "werewolf": False,
            "witch": False,
            "guard": False,
        }
        self._night_feedback_timer: float = 0.0

        # Player selection for night actions
        self._selected_night_target: Optional[int] = None

        # Mouse hover state
        self._hovered_player: Optional[int] = None

        # Main menu state
        self._main_menu: bool = True
        self._menu_option: int = 0
        self._menu_fade_in: float = 0.0
        self._menu_particles: list = []

        # Settings screen state
        self._settings_active: bool = False
        self._settings_option: int = 0  # 0=language toggle, 1=back to menu
        self._settings_fade_in: float = 0.0

        # Role reveal state
        self._role_reveal_active: bool = False
        self._role_reveal_timer: float = 0.0
        self._role_reveal_player_idx: int = 0

        # Night action selection state
        self._night_selection_active: bool = False
        self._night_selection_targets: list[Player] = []

        # Player card hovers
        self._player_card_hover: Optional[int] = None

        # Text animation / typing
        self._typing_active: bool = False
        self._typing_text: str = ""
        self._typing_progress: float = 0.0
        self._typing_speed: float = 20.0
        self._typing_full_text: str = ""

        # Ambient weather effects
        self._weather_transition_timer: float = 0.0

        # NPC discussion active flag
        self._npc_discussion_active: bool = False

        # Camera for scrollable world viewport
        from game.renderer import GRID_COLS, GRID_ROWS, TILE_SIZE
        world_w = GRID_COLS * TILE_SIZE
        world_h = GRID_ROWS * TILE_SIZE
        self.camera = Camera(world_w, world_h, 2560, 1440)

        # Stored for lazy wiring in init()
        self._engine_initialised = False

        # Kick layout recalculation
        WerewolfGame._recalc_layout()

    # ──────────────────────────────────────────────
    # Layout
    # ──────────────────────────────────────────────

    @staticmethod
    def _recalc_layout(win_w: int | None = None, win_h: int | None = None) -> None:
        """Recompute layout constants proportional to actual screen size.

        The game is designed for 2560x1440. On smaller/larger screens,
        the sidebar overlay and font scales are adjusted proportionally.
        The tile map always renders at 0,0 with TILE_SIZE=80px.
        Delegates to game/ui_panels.recalc_layout() which updates
        the layout variables in that module. All rendering code
        accesses ui_panels.SIDEBAR_X etc. directly, so no copy-back
        of module-level globals is needed.

        Args:
            win_w: Actual window width (from VIDEORESIZE event or surface).
            win_h: Actual window height.
                   If None, attempts to read from the pygame display surface,
                   falling back to the designed 2560x1440.
        """
        if win_w is None or win_h is None:
            try:
                surface = pygame.display.get_surface()
                if surface:
                    win_w, win_h = surface.get_size()
                else:
                    win_w, win_h = 2560, 1440
            except Exception:
                win_w, win_h = 2560, 1440
        ui_panels.recalc_layout(win_w, win_h)

    def init(self) -> bool:
        """Initialise the engine and wire up callbacks."""
        if not self.engine.init():
            return False

        # Wire engine callbacks to game methods
        self.engine.on_render = self._render
        self.engine.on_update = self._update
        self.engine.on_event = self._handle_event

        # Register state provider for TCP bridge
        self.engine.get_state = lambda: self.game_state.to_dict()

        # Recalculate layout now that screen dimensions are known
        WerewolfGame._recalc_layout()

        # Update camera viewport to match actual screen dimensions
        sw, sh = self.engine.screen.get_size()
        self.camera.set_viewport(sw, sh)

        # Initialise audio mixer (gracefully handles no audio device)
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
        except pygame.error:
            pass  # headless / no audio — sounds will be silent

        self._engine_initialised = True
        return True

    def run(self) -> None:
        """Run the main game loop."""
        self.engine.run()



    # ──────────────────────────────────────────────
    # Update
    # ──────────────────────────────────────────────

    def _update(self, dt: float) -> None:
        """Main update loop — called by GameEngine each frame."""
        if self._main_menu:
            self._update_menu(dt)
            return

        if self._role_reveal_active:
            self._role_reveal_timer -= dt
            if self._role_reveal_timer <= 0:
                self._role_reveal_active = False
            return

        if self.game_state.game_over:
            self._game_over_timer -= dt
            return

        if self._vote_result_active:
            self._vote_result_timer -= dt
            if self._vote_result_timer <= 0:
                self._vote_result_active = False
            return

        if self._sheriff_vote_result_active:
            self._sheriff_vote_result_timer -= dt
            if self._sheriff_vote_result_timer <= 0:
                self._sheriff_vote_result_active = False
            return

        if self._death_announce_active:
            self._death_announce_timer -= dt
            if self._death_announce_timer <= 0:
                self._death_announce_active = False
            return

        # Update camera inertia (runs every frame regardless of phase)
        self.camera.update(dt)

        # Update continuous animations (runs every frame regardless of phase)
        update_elimination_timers(dt)

        if self._night_feedback_timer > 0:
            self._night_feedback_timer -= dt
            if self._night_feedback_timer <= 0:
                self._night_feedback_state = {k: False for k in self._night_feedback_state}
            return

        # Phase transition update
        if self._in_transition:
            self._phase_blend += dt * 2.0
            # Drive the day/night blend animation during transitions
            self.renderer.set_day_mode(is_day=not self.game_state.phase.is_night, dt=dt)
            if self._phase_blend >= 1.0:
                self._phase_blend = 0.0
                self._in_transition = False
            return

        # Timer advance
        self._phase_timer += dt

        # Logic phase — animate discussions etc.
        if self.game_state.phase in (GamePhase.NIGHT_GUARD, GamePhase.NIGHT_SEER,
                                     GamePhase.NIGHT_WEREWOLF, GamePhase.NIGHT_WITCH):
            self._update_night_phase(dt)
        elif self.game_state.phase == GamePhase.DAY_DISCUSSION:
            self._update_discussion_phase(dt)
        elif self.game_state.phase in (GamePhase.DAY_VOTE, GamePhase.DAY_PK):
            self._update_vote_phase(dt)
            # Update vote pulse animation
            state = self.game_state
            vote_counts: dict[int, list[int]] = {}
            for voter, target in state.votes.items():
                if target not in vote_counts:
                    vote_counts[target] = []
                vote_counts[target].append(voter)
            update_vote_pulses(dt, vote_counts)

        # Auto-advance phase if duration elapsed
        if self._phase_timer >= self._get_phase_duration():
            self._advance_phase()

        # Refresh ambient periodically
        self._last_ambient_play += dt
        if self._last_ambient_play > 5.0:
            self._last_ambient_play = 0.0
            self._play_ambient()

        # Update shake — applies random displacement that decays exponentially
        if self._shake_timer > 0:
            self._shake_timer -= dt
            decay = 0.85 if self._shake_style == "quake" else 0.90
            self._shake_intensity *= decay
            ox = int(random.gauss(0, self._shake_intensity))
            oy = int(random.gauss(0, self._shake_intensity))
            # For 'quake' style, add directional bias (more vertical shake)
            if self._shake_style == "quake":
                oy = int(random.gauss(0, self._shake_intensity * 1.5))
            self._shake_offset = (ox, oy)
        else:
            self._shake_offset = (0, 0)

        # Update flash
        if self._flash_active:
            self._flash_timer -= dt
            if self._flash_timer <= 0:
                self._flash_active = False

    # ──────────────────────────────────────────────
    # Phase sub-updates
    # ──────────────────────────────────────────────

    def _update_night_phase(self, dt: float) -> None:
        """Handle NPC AI actions during night phases."""
        if not self._night_actions_confirmed:
            self._resolve_npc_night_actions()
            self._night_actions_confirmed = True

    def _update_discussion_phase(self, dt: float) -> None:
        """Handle discussion phase AI speech."""
        if not self._npc_discussion_active:
            return
        self._discussion_timer += dt
        if self._discussion_timer >= self._discussion_interval:
            self._discussion_timer = 0.0
            self._trigger_npc_discussion()

    def _update_vote_phase(self, dt: float) -> None:
        """Cast NPC votes after a short delay."""
        if not self._ai_votes_cast:
            self._ai_votes_cast = True
            self._cast_npc_votes()

    # ──────────────────────────────────────────────
    # NPC helpers
    # ──────────────────────────────────────────────

    def _resolve_npc_night_actions(self) -> None:
        """Let NPCs (non-human) perform their night actions."""
        state = self.game_state
        players = state.players

        # Guard
        guard_list = players.get_players_by_role(Role.GUARD)
        if guard_list:
            guard_p = guard_list[0]
            if guard_p.alive and state.guard_target is None:
                target = choose_night_action(state, guard_p.index, GamePhase.NIGHT_GUARD)
                if target is not None:
                    state.guard_target = target
                    state.players.get_player(target).protected = True

        # Werewolves — first living wolf picks
        wolves = players.get_players_by_role(Role.WEREWOLF)
        alive_wolves = [w for w in wolves if w.alive]
        if alive_wolves:
            lead_wolf = alive_wolves[0]
            if state.werewolf_target is None:
                target = choose_night_action(state, lead_wolf.index, GamePhase.NIGHT_WEREWOLF)
                if target is not None:
                    state.werewolf_target = target

        # Witch
        witch_list = players.get_players_by_role(Role.WITCH)
        if witch_list:
            witch_p = witch_list[0]
            if witch_p.alive:
                should_save, should_poison, poison_target = decide_witch_action(state)
                if should_save and state.werewolf_target is not None:
                    state.witch_heal_target = state.werewolf_target
                if should_poison and poison_target is not None:
                    state.witch_poison_target = poison_target

        # Seer
        seer_list = players.get_players_by_role(Role.SEER)
        if seer_list:
            seer_p = seer_list[0]
            if seer_p.alive and state.seer_target is None:
                target = choose_night_action(state, seer_p.index, GamePhase.NIGHT_SEER)
                if target is not None:
                    state.seer_target = target

    def _cast_npc_votes(self) -> None:
        """Let NPCs cast their votes during the DAY_VOTE phase."""
        state = self.game_state
        players = state.players
        for p in players.players:
            if not p.alive:
                continue
            if p.is_human:
                continue
            target = choose_vote_target(state, p.idx)
            if target is not None:
                state.votes[p.idx] = target

    def _trigger_npc_discussion(self) -> None:
        """Pick a random NPC to speak during discussion phase."""
        state = self.game_state
        players = state.players.players
        alive_players = [p for p in players if p.alive and not p.is_human]
        if not alive_players:
            return
        speaker = random.choice(alive_players)
        self._current_speaker = speaker
        self._discussion_text = generate_discussion(state, speaker.idx)

    # ──────────────────────────────────────────────
    # Sound helpers
    # ──────────────────────────────────────────────

    def _play_ambient(self) -> None:
        """Play ambient sound for current phase."""
        if self.game_state.phase in (GamePhase.NIGHT_GUARD, GamePhase.NIGHT_SEER,
                                     GamePhase.NIGHT_WEREWOLF, GamePhase.NIGHT_WITCH):
            fn = ambient_night()
        else:
            fn = ambient_day()
        if fn:
            fn.play()

    # ──────────────────────────────────────────────
    # Event handling
    # ──────────────────────────────────────────────

    def _handle_event(self, event: pygame.event.Event) -> None:
        """Handle pygame events (input)."""
        if event.type == pygame.VIDEORESIZE:
            self._recalc_layout(event.w, event.h)
            # Update camera viewport to match new window dimensions
            self.camera.set_viewport(event.w, event.h)
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
                # After fullscreen toggle, query the surface for new size
                self._recalc_layout()
                return
            if self._main_menu:
                self._handle_menu_key(event)
                return
            if self.game_state.game_over:
                if event.key == pygame.K_r:
                    self._restart_game()
                elif event.key == pygame.K_q:
                    self.engine.running = False
                return
            if self._role_reveal_active:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self._role_reveal_active = False
                return
            if event.key == pygame.K_n:
                self._advance_phase()
                return
            if self.game_state.phase in (GamePhase.DAY_VOTE, GamePhase.DAY_PK):
                self._handle_vote_key(event)
                return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # left click
                if self._settings_active:
                    self._handle_settings_click(event.pos)
                    return
                if self._main_menu:
                    self._handle_menu_click(event.pos)
                    return
                if self.game_state.game_over:
                    return
                # Click is on sidebar area? Handle UI there.
                if event.pos[0] >= ui_panels.SIDEBAR_X:
                    self._handle_sidebar_click(event)
                    return
                # Otherwise, start camera drag on the game world
                if not self._main_menu and not self._role_reveal_active:
                    self.camera.start_drag(event.pos[0], event.pos[1])
                    return

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.camera.is_dragging():
                    self.camera.end_drag()
                    return

        if event.type == pygame.MOUSEMOTION:
            # Update hover state (for highlighting) in sidebar
            if event.pos[0] >= ui_panels.SIDEBAR_X:
                self._update_hover_state(event.pos)
            # Camera drag
            if self.camera.is_dragging():
                self.camera.update_drag(event.pos[0], event.pos[1])
                return

    def _handle_menu_key(self, event: pygame.event.Event) -> None:
        """Handle keyboard on the main menu."""
        if self._settings_active:
            self._handle_settings_key(event)
            return
        if event.key == pygame.K_UP:
            self._menu_option = (self._menu_option - 1) % 3
            click = button_click()
            if click:
                click()
        elif event.key == pygame.K_DOWN:
            self._menu_option = (self._menu_option + 1) % 3
            click = button_click()
            if click:
                click()
        elif event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
            if self._menu_option == 0:
                self._start_from_menu()
            elif self._menu_option == 1:
                # Open settings screen
                self._settings_active = True
                self._settings_option = 0
                self._settings_fade_in = 0.0
                click = button_click()
                if click:
                    click()
            elif self._menu_option == 2:
                self.engine.running = False

    def _handle_settings_key(self, event: pygame.event.Event) -> None:
        """Handle keyboard on the settings screen."""
        if event.key == pygame.K_UP:
            self._settings_option = (self._settings_option - 1) % 2
            click = button_click()
            if click:
                click()
        elif event.key == pygame.K_DOWN:
            self._settings_option = (self._settings_option + 1) % 2
            click = button_click()
            if click:
                click()
        elif event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
            if self._settings_option == 0:
                # Toggle language
                import game.text as text_mod
                text_mod.LANG = "en" if text_mod.LANG == "zh" else "zh"
                click = button_click()
                if click:
                    click()
            elif self._settings_option == 1:
                # Back to main menu
                self._settings_active = False
                click = button_click()
                if click:
                    click()
        elif event.key == pygame.K_ESCAPE:
            self._settings_active = False

    def _handle_settings_click(self, pos: tuple[int, int]) -> None:
        """Handle mouse click on settings overlay buttons."""
        sw = ui_panels.SCREEN_W
        sh = ui_panels.SCREEN_H
        cx = sw // 2
        cy = sh // 2
        pw = int(500 * sw / 2560)
        ph = int(350 * sh / 1440)
        px = cx - pw // 2
        py = cy - ph // 2 - int(60 * sh / 1440)
        sep_y = py + int(30 * sh / 1440) + (max(2, int(4 * sh / 1440)) * 8) + int(20 * sh / 1440)
        opt_start_y = sep_y + int(40 * sh / 1440)

        for i in range(2):
            ox = px + int(40 * sw / 2560)
            ow = pw - int(80 * sw / 2560)
            oh = int(50 * sh / 1440)
            oy = opt_start_y + i * int(70 * sh / 1440)
            if ox <= pos[0] <= ox + ow and oy <= pos[1] <= oy + oh:
                self._settings_option = i
                from game.sound import button_click
                if i == 0:
                    # Toggle language
                    import game.text as text_mod
                    text_mod.LANG = "en" if text_mod.LANG == "zh" else "zh"
                elif i == 1:
                    # Back to main menu
                    self._settings_active = False
                click = button_click()
                if click:
                    click()
                return

    def _handle_menu_click(self, pos: tuple[int, int]) -> None:
        """Handle mouse click on main menu."""
        sw = ui_panels.SCREEN_W
        sh = ui_panels.SCREEN_H
        cx = sw // 2
        center_y = sh // 2 + int(80 * sh / 1440)
        for i in range(3):
            by = center_y + i * int(80 * sh / 1440)
            bx = cx - int(200 * sw / 2560)
            bw = int(400 * sw / 2560)
            bh = int(60 * sh / 1440)
            if bx <= pos[0] <= bx + bw and by <= pos[1] <= by + bh:
                self._menu_option = i
                if i == 0:
                    self._start_from_menu()
                elif i == 1:
                    self._settings_active = True
                    self._settings_option = 0
                    self._settings_fade_in = 0.0
                elif i == 2:
                    self.engine.running = False
                click = button_click()
                if click:
                    click()
                return

    def _handle_vote_key(self, event: pygame.event.Event) -> None:
        """Handle keyboard during voting."""
        if event.key == pygame.K_UP:
            self._voting_player_idx = max(0, self._voting_player_idx - 1)
        elif event.key == pygame.K_DOWN:
            self._voting_player_idx = min(11, self._voting_player_idx + 1)
        elif event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
            state = self.game_state
            target = self._voting_player_idx
            if state.players.get_player(target).alive:
                state.cast_vote(0, target)  # Human = idx 0
                vc = vote_cast()
                if vc:
                    vc()

    def _handle_sidebar_click(self, event: pygame.event.Event) -> None:
        """Handle mouse click on the sidebar."""
        state = self.game_state
        players = state.players
        # Map y-coord to player
        list_y = ui_panels.LIST_START
        sp = ui_panels.LIST_SPACING
        for p in players.players:
            if not p.alive:
                list_y += sp
                continue
            if list_y <= event.pos[1] <= list_y + sp:
                # Target this player
                if state.phase in (GamePhase.DAY_VOTE, GamePhase.DAY_PK) and players.get_player(0).alive:
                    # Hunter vengeance: if human is eliminated hunter, click to shoot
                    if state.hunter_needs_vengeance:
                        hunter_idx = state._hunter_vengeance_idx
                        if hunter_idx == 0:
                            state.resolve_hunter_vengeance(p.idx)
                            ks = kill_sting()
                            if ks:
                                ks.play()
                            return
                    state.cast_vote(0, p.idx)
                    vc = vote_cast()
                    if vc:
                        vc()
                # Night actions for human player
                elif state.phase == GamePhase.NIGHT_WEREWOLF:
                    if players.get_player(0).alive and players.get_player(0).role == Role.WEREWOLF:
                        state.set_night_action("werewolf", 0, p.idx)
                elif state.phase == GamePhase.NIGHT_SEER:
                    if players.get_player(0).alive and players.get_player(0).role == Role.SEER:
                        state.set_night_action("seer", 0, p.idx)
                elif state.phase == GamePhase.NIGHT_GUARD:
                    if players.get_player(0).alive and players.get_player(0).role == Role.GUARD:
                        state.set_night_action("guard", 0, p.idx)
                elif state.phase == GamePhase.NIGHT_WITCH:
                    if players.get_player(0).alive and players.get_player(0).role == Role.WITCH:
                        action = "witch_poison" if self._witch_mode_is_poison else "witch_save"
                        state.set_night_action(action, 0, p.idx)

        # Handle witch potion mode-toggle clicks
        if self.game_state.phase == GamePhase.NIGHT_WITCH:
            from game.ui_panels import _WITCH_BUTTON_RECTS
            click_pos = event.pos
            if "heal" in _WITCH_BUTTON_RECTS and _WITCH_BUTTON_RECTS["heal"].collidepoint(click_pos):
                self._witch_mode_is_poison = False
                return
            if "poison" in _WITCH_BUTTON_RECTS and _WITCH_BUTTON_RECTS["poison"].collidepoint(click_pos):
                self._witch_mode_is_poison = True
                return

    def _update_hover_state(self, pos: tuple[int, int]) -> None:
        """Update which player the mouse is hovering over."""
        state = self.game_state
        players = state.players
        list_y = ui_panels.LIST_START
        sp = ui_panels.LIST_SPACING
        for p in players.players:
            if not p.alive:
                list_y += sp
                continue
            if list_y <= pos[1] <= list_y + sp:
                self._hovered_player = p.idx
                return
            list_y += sp
        self._hovered_player = None

    # ──────────────────────────────────────────────
    # Phase advancement
    # ──────────────────────────────────────────────

    def _get_phase_duration(self) -> float:
        """Return duration for the current phase."""
        return self._phase_durations.get(self.game_state.phase, 2.0)

    def _advance_phase(self) -> None:
        """Advance to the next game phase."""
        state = self.game_state
        old_phase = state.phase

        # Reset per-phase flags
        self._phase_timer = 0.0
        self._discussion_timer = 0.0
        self._ai_action_delay = 0.0
        self._ai_thinking = False
        self._ai_current_action = ""

        # Start transition
        self._in_transition = True
        self._phase_blend = 0.0

        # Phase-specific reset
        if state.phase in (GamePhase.NIGHT_GUARD, GamePhase.NIGHT_SEER,
                           GamePhase.NIGHT_WEREWOLF, GamePhase.NIGHT_WITCH):
            self._night_actions_confirmed = False
            self._selected_night_target = None

        if state.phase in (GamePhase.DAY_VOTE, GamePhase.DAY_PK):
            self._ai_votes_cast = False
        elif state.phase == GamePhase.DAY_DISCUSSION:
            self._npc_discussion_active = True
            # Reset NPC discussion context for the new discussion round
            reset_context()
        elif state.phase in (GamePhase.DAY_ANNOUNCE, GamePhase.DAY_SHERIFF_ELECTION):
            self._npc_discussion_active = False

        if old_phase in (GamePhase.DAY_VOTE, GamePhase.DAY_PK):
            self._vote_result_active = True
            self._vote_result_timer = 3.0
            votes = state.votes
            if votes:
                # Count votes per target player (correctly)
                vote_counts = Counter(votes.values())
                max_count = max(vote_counts.values())
                targets = [t for t, c in vote_counts.items() if c == max_count]
                if len(targets) == 1:
                    pname = state.players.get_player(targets[0]).display_name
                    self._vote_result_text = f"{pname} {_('was_voted_out')}"
                    self._vote_result_plural = False
                    trigger_elimination_highlight(targets[0])
                    # ── Shake on vote elimination ──
                    self._shake_intensity = 8.0
                    self._shake_timer = 0.4
                    self._shake_style = "normal"
                else:
                    names = [state.players.get_player(t).display_name for t in targets]
                    self._vote_result_text = f"{' '.join(names)} {_('are_tied')}"
                    self._vote_result_plural = True
            # Sound
            vr = vote_result()
            if vr:
                vr.play()

        if state.phase == GamePhase.DAY_SHERIFF_ELECTION and state.phase != old_phase:
            em = election_music()
            if em:
                em.play()

        # Advance core state (use correct method based on current phase)
        if state.phase in (GamePhase.DAY_ANNOUNCE, GamePhase.DAY_SHERIFF_ELECTION,
                           GamePhase.DAY_DISCUSSION, GamePhase.DAY_VOTE,
                           GamePhase.DAY_PK, GamePhase.DAY_TRIAL,
                           GamePhase.DAY_VOTE_RESULT):
            state.advance_day_phase()
        elif state.phase in (GamePhase.NIGHT_GUARD, GamePhase.NIGHT_WEREWOLF,
                             GamePhase.NIGHT_WITCH, GamePhase.NIGHT_SEER):
            state.advance_night_phase()

        new_phase = state.phase

        # Initiate day/night background blend when phase flips
        self.renderer.set_day_mode(is_day=not new_phase.is_night, dt=0.0)

        # Wire up NPC discussion context: record eliminations
        if state.vote_result is not None and old_phase in (GamePhase.DAY_VOTE, GamePhase.DAY_PK):
            set_voted_out(state.vote_result)

        # Death announcements on night→day transition
        if (old_phase in (GamePhase.NIGHT_GUARD, GamePhase.NIGHT_SEER,
                          GamePhase.NIGHT_WEREWOLF, GamePhase.NIGHT_WITCH)
                and new_phase == GamePhase.DAY_ANNOUNCE):
            night_result = state.resolve_night()
            killed = night_result.get("victim")
            poisoned = night_result.get("poisoned")
            saved = night_result.get("saved")
            saved_idx = night_result.get("saved_index")
            # killed is an int; saved is a bool. Use saved_idx for the actual player index.
            if killed is not None and (not saved or saved_idx != killed):
                ks = kill_sting()
                if ks:
                    ks.play()
                killed_player = state.players.get_player(killed)
                self._death_announce_text = f"{killed_player.display_name} {_('was_killed')}!"
                self._death_announce_role = f"{_('they_were')} {killed_player.role.name_zh}"
                self._death_announce_active = True
                self._death_announce_timer = 3.5
                self._death_announce_done = False
                # Record victim for NPC discussion context
                set_night_victim(killed)
                # ── Shake on kill ──
                self._shake_intensity = 12.0
                self._shake_timer = 0.5
                self._shake_style = "normal"
            if poisoned is not None:
                ks = kill_sting()
                if ks:
                    ks.play()
                poisoned_player = state.players.get_player(poisoned)
                self._death_announce_text = f"{poisoned_player.display_name} {_('was_poisoned')}!"
                self._death_announce_role = f"{_('they_were')} {poisoned_player.role.name_zh}"
                self._death_announce_active = True
                self._death_announce_timer = 3.5
                self._death_announce_done = False
                # Also record poison victim
                set_night_victim(poisoned)
                # ── Shake on poison ──
                self._shake_intensity = 10.0
                self._shake_timer = 0.4
                self._shake_style = "normal"
            if saved and saved_idx is not None:
                saved_player = state.players.get_player(saved_idx)
                self._death_announce_text = f"{_('someone_was_attacked')} {_('but_was_saved')}!"
                self._death_announce_role = f"{_('it_was')} {saved_player.display_name}"
                self._death_announce_active = True
                self._death_announce_timer = 3.0
                self._death_announce_done = False

            # Apply night kills (already applied in resolve_night() above)
            pass
            da = death_announce()
            if da:
                da.play()

        # Sheriff election result display
        if old_phase == GamePhase.DAY_SHERIFF_ELECTION and state.sheriff_election_result is not None:
            self._sheriff_vote_result_active = True
            self._sheriff_vote_result_timer = 3.0

        # Music transitions
        if new_phase == GamePhase.GAME_OVER:
            if state.winner == "werewolf":
                self._flash_active = True
                self._flash_color = (180, 0, 0)
                self._flash_duration = 1.5
                self._flash_timer = 1.5
                wj = victory_jingle()
                if wj:
                    wj.play()
            else:
                self._flash_active = True
                self._flash_color = (200, 180, 100)
                self._flash_duration = 1.5
                self._flash_timer = 1.5
                dj = defeat_jingle()
                if dj:
                    dj.play()
            # ── Shake on game over ──
            self._shake_intensity = 16.0
            self._shake_timer = 1.0
            self._shake_style = "quake"
            self._game_over_timer = 0.5
        elif new_phase in (GamePhase.NIGHT_GUARD, GamePhase.NIGHT_SEER,
                           GamePhase.NIGHT_WEREWOLF, GamePhase.NIGHT_WITCH):
            nm = night_music()
            if nm:
                nm.play()
        elif new_phase == GamePhase.DAY_ANNOUNCE:
            dm = day_music()
            if dm:
                dm.play()

    # ──────────────────────────────────────────────
    # Game flow
    # ──────────────────────────────────────────────

    def _start_from_menu(self) -> None:
        """Transition from main menu to game."""
        self._main_menu = False
        self.game_state.start_game()
        self._role_reveal_active = True
        self._role_reveal_timer = 0.5
        self._role_reveal_player_idx = 0

        # Initialize weather
        self.renderer.weather = random.choice(list(WeatherState))

    def _restart_game(self) -> None:
        """Restart the game with fresh state."""
        self.game_state = GameState()
        self.renderer = VillageRenderer()
        self._phase_timer = 0.0
        self._main_menu = True
        self._menu_option = 0
        self._menu_fade_in = 0.0
        self._menu_particles = []
        self._role_reveal_active = False
        self._death_announce_active = False
        self._vote_result_active = False
        self._discussion_active = False
        self._night_actions_confirmed = False
        self._ai_votes_cast = False
        self._wolf_votes = {}
        reset_vote_pulses()

    # ──────────────────────────────────────────────
    # Render
    # ──────────────────────────────────────────────

    def _render(self, screen: pygame.Surface) -> None:
        """Main render call — called by GameEngine each frame."""
        sw, sh = screen.get_size()

        # ── Main menu ──
        if self._main_menu:
            import game.ui_panels as panels
            panels.draw_main_menu(
                screen, sw, sh,
                self._menu_option, self._menu_fade_in,
                particles=self._menu_particles,
            )
            if self._settings_active:
                # Dim overlay for settings
                overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 160))
                screen.blit(overlay, (0, 0))
                panels.draw_settings_overlay(
                    screen, sw, sh,
                    self._settings_option,
                    self._settings_fade_in,
                )
            return

        # ── Role reveal ──
        if self._role_reveal_active:
            import game.ui_panels as panels
            human = self.game_state.players.get_player(0)
            panels.draw_role_reveal(screen, sw, sh, human)
            return

        # ── Game over ──
        if self.game_state.game_over and self._game_over_timer <= 0:
            import game.ui_panels as panels
            panels.draw_game_over(
                screen, sw, sh,
                self.game_state.winner,
                self._flash_color, self._flash_timer,
                self._flash_duration, self._flash_active,
            )
            return

        # ── Normal game render ──
        state = self.game_state
        # Ensure day/night mode is synced to renderer every frame
        self.renderer.set_day_mode(is_day=not state.phase.is_night, dt=0.0)
        players = state.players

        # Village background (tile map)
        sw, sh = screen.get_size()
        time = 0.0
        if hasattr(self, '_phase_blend'):
            time = self._phase_blend

        # Ensure player sprites are set on the map
        self.renderer.set_players(players.players)

        # Apply shake offset to camera for village map only (UI stays in place)
        shake_x = self._shake_offset[0]
        shake_y = self._shake_offset[1]

        self.renderer.render(
            screen,
            night=state.phase.is_night,
            time=time,
            human_player_idx=self._human_player_idx,
            camera_x=self.camera.x + shake_x,
            camera_y=self.camera.y + shake_y,
        )

        # ── Sidebar background ──
        draw_sidebar_background(screen, ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_Y, ui_panels.SIDEBAR_W, ui_panels.SCREEN_H)

        # ── Phase indicator with countdown ──
        dur = self._get_phase_duration()
        remain = max(0.0, dur - self._phase_timer)
        draw_phase_indicator(screen, state.phase, state.day, ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_Y, ui_panels.SIDEBAR_W,
                             remain=remain, total=dur)

        # ── Phase instruction ──
        draw_phase_instruction(screen, state, ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_Y)

        # ── Player list ──
        selected = self._hovered_player
        draw_player_list(screen, players, ui_panels.SIDEBAR_X, ui_panels.LIST_START, ui_panels.LIST_SPACING,
                         selected=selected, phase=state.phase,
                         votes=state.votes if state.phase == GamePhase.DAY_VOTE else None)

        # ── Game log ──
        draw_game_log(screen, state.log, ui_panels.SIDEBAR_X, ui_panels.LOG_START_Y, ui_panels.LOG_SPACING)

        # ── Narration header ──
        if state.phase == GamePhase.DAY_ANNOUNCE:
            draw_narration_header(screen, state.phase, ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_Y)

        # ── Additional UI during specific phases ──
        if state.phase == GamePhase.DAY_DISCUSSION and self._current_speaker:
            draw_discussion_bubble(screen, self._current_speaker.idx, self._discussion_text,
                                   ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_W, ui_panels.SCREEN_H)

        if self._death_announce_active:
            draw_narration_header(screen, state.phase, ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_Y)

        if self._vote_result_active:
            draw_vote_result_box(screen, self._vote_result_text, self._vote_result_plural,
                                 ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_W)



        if state.phase in (GamePhase.NIGHT_GUARD, GamePhase.NIGHT_SEER,
                           GamePhase.NIGHT_WEREWOLF, GamePhase.NIGHT_WITCH):
            draw_skill_status_panel(screen, state, ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_W, ui_panels.SCREEN_H)

        if state.phase == GamePhase.NIGHT_WEREWOLF:
            draw_wolf_vote_display(screen, self._wolf_votes, ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_W)

        if state.phase == GamePhase.NIGHT_WITCH:
            draw_witch_potion_display(screen, state, ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_W, self._witch_mode_is_poison)

        if hasattr(state, '_hunter_needs_vengeance') and state._hunter_needs_vengeance:
            draw_hunter_vengeance_display(screen, state, ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_W, ui_panels.SCREEN_H)

        if state.phase in (GamePhase.NIGHT_GUARD,) and self._selected_night_target is not None:
            draw_guard_target_display(screen, self._selected_night_target, players,
                                      ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_W, ui_panels.SCREEN_H)

        if state.phase in (GamePhase.NIGHT_SEER,) and self._selected_night_target is not None:
            draw_seer_target_display(screen, self._selected_night_target, players,
                                      ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_W, ui_panels.SCREEN_H)

        # Spectator mode banner if applicable
        human = players.get_player(0)
        if not human.alive:
            draw_spectator_mode_banner(screen, ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_W)

        # Day banner
        if state.phase in (GamePhase.DAY_DISCUSSION, GamePhase.DAY_VOTE,
                           GamePhase.DAY_SHERIFF_ELECTION,
                           GamePhase.DAY_ANNOUNCE):
            draw_day_banner(screen, state.day)

        # Election banner
        if state.phase == GamePhase.DAY_SHERIFF_ELECTION:
            draw_election_banner(screen, ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_W)

        # Sheriff vote result (displayed briefly after election resolves)
        if self._sheriff_vote_result_active and state.sheriff_election_result is not None:
            draw_sheriff_result(
                screen,
                state.sheriff_election_result,
                ui_panels.SIDEBAR_X,
                ui_panels.SIDEBAR_W,
            )

        # Flash effect
        if self._flash_active:
            alpha = int(255 * (self._flash_timer / max(self._flash_duration, 0.001)))
            flash_surf = pygame.Surface((sw, sh))
            flash_surf.set_alpha(alpha)
            flash_surf.fill(self._flash_color)
            screen.blit(flash_surf, (0, 0))

        # Game result panel if game is over (with timer)
        if self.game_state.game_over:
            if state.winner == "werewolf":
                draw_game_result_panel_wolf_pov(screen, state, ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_W, ui_panels.SCREEN_H)
            else:
                draw_game_result_panel(screen, state, ui_panels.SIDEBAR_X, ui_panels.SIDEBAR_W, ui_panels.SCREEN_H)

    # ──────────────────────────────────────────────
    # Menu update
    # ──────────────────────────────────────────────

    def _update_menu(self, dt: float) -> None:
        """Update main menu animation — fade-in + ambient particles."""
        self._menu_fade_in = min(1.0, self._menu_fade_in + 0.5 * dt)

        # Lazy-init particles on first update
        if not self._menu_particles:
            rng = random.Random(42)
            self._menu_particles.clear()
            for _ in range(30):
                self._menu_particles.append({
                    "x": rng.random(),
                    "y": rng.random() * 0.7 + 0.3,  # mostly upper half
                    "vx": (rng.random() - 0.5) * 0.02,
                    "vy": -(rng.random() * 0.03 + 0.01),
                    "size": rng.random() * 1.5 + 0.5,
                    "alpha": rng.random() * 0.5 + 0.3,
                    "phase": rng.random() * 6.28,
                    "freq": rng.random() * 2.0 + 1.0,
                    "color": (
                        int(rng.randint(200, 255)),
                        int(rng.randint(140, 200)),
                        int(rng.randint(60, 120)),
                    ),
                })

        # Update particles
        for p in self._menu_particles:
            p["phase"] += dt * p["freq"]
            p["x"] += p["vx"] * dt + 0.002 * dt * __import__("math").sin(p["phase"])
            p["y"] += p["vy"] * dt
            # Alpha oscillation for gentle breathing
            p["alpha"] = 0.4 + 0.3 * __import__("math").sin(p["phase"] * 0.5)
            # Wrap around
            if p["y"] < -0.05:
                p["y"] = 1.0 + 0.05
                p["x"] = __import__("random").random()
            if p["x"] < -0.05:
                p["x"] = 1.05
            elif p["x"] > 1.05:
                p["x"] = -0.05
