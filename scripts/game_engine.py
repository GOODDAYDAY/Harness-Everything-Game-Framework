#!/usr/bin/env python3
"""Pygame game engine wrapper with harness TCP bridge integration.

Provides a minimal game loop with:
- Window management (resizable, 2K default)
- Screenshot capture (PNG via pygame.image.save)
- Input injection (mouse click, keyboard)
- Frame recording (PNG sequence)
- TCP bridge auto-start

To start a game: inherit from this or instantiate with callbacks.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

import pygame

from scripts.tcp_server import TcpBridge


class GameEngine:
    """Pygame wrapper with built-in TCP bridge for harness tools."""

    def __init__(
        self,
        *,
        width: int = 2560,
        height: int = 1440,
        title: str = "Game",
        fps: int = 60,
        pixel_art: bool = True,
    ) -> None:
        self.width = width
        self.height = height
        self.title = title
        self.fps = fps
        self.pixel_art = pixel_art

        self.screen: pygame.Surface | None = None
        self.clock: pygame.time.Clock | None = None
        self.running = False

        # Recording state
        self._recording = False
        self._record_fps = 6
        self._record_dir = ""
        self._record_frame_count = 0
        self._record_timer = 0.0

        # Callbacks
        self.on_update: Callable[[float], None] | None = None  # (dt)
        self.on_render: Callable[[pygame.Surface], None] | None = None  # (screen)
        self.on_event: Callable[[pygame.event.Event], None] | None = None

        # TCP bridge
        self._bridge: TcpBridge | None = None

        # Injected input queue (for harness input commands)
        self._input_queue: list[pygame.event.Event] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init(self) -> bool:
        """Initialise pygame and create the window. Returns True on success."""
        pygame.init()
        flags = pygame.RESIZABLE
        self.screen = pygame.display.set_mode(
            (self.width, self.height), flags,
        )
        pygame.display.set_caption(self.title)
        self.clock = pygame.time.Clock()
        print(f"[GameEngine] {self.width}x{self.height} window created")

        # Start TCP bridge
        self._bridge = TcpBridge(
            on_screenshot=self._take_screenshot,
            on_input_click=self._inject_click,
            on_input_key=self._inject_key,
            on_state=self._get_state,
            on_quit=lambda: setattr(self, "running", False),
            on_record_start=self._start_recording,
            on_record_stop=self._stop_recording,
            on_record_frame=self._capture_frame,
        )
        self._bridge.start()
        return True

    def run(self) -> None:
        """Main game loop. Blocks until quit."""
        if self.screen is None or self.clock is None:
            raise RuntimeError("Call init() before run()")
        self.running = True
        while self.running:
            dt = self.clock.tick(self.fps) / 1000.0

            # Process injected input from harness
            while self._input_queue:
                ev = self._input_queue.pop(0)
                if self.on_event:
                    self.on_event(ev)
                self._process_event(ev)

            # Process native events
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                elif self.on_event:
                    self.on_event(ev)
                self._process_event(ev)

            # Update
            if self.on_update:
                self.on_update(dt)

            # Render
            if self.on_render:
                self.on_render(self.screen)

            # Recording
            if self._recording:
                self._record_timer += dt
                interval = 1.0 / self._record_fps
                while self._record_timer >= interval:
                    self._record_timer -= interval
                    self._capture_frame_impl()

            pygame.display.flip()

        self.quit()

    def quit(self) -> None:
        if self._bridge:
            self._bridge.stop()
        self.running = False
        pygame.quit()

    # ------------------------------------------------------------------
    # Harness bridge callbacks
    # ------------------------------------------------------------------

    def _take_screenshot(self, path: str) -> bool:
        if self.screen is None:
            return False
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            pygame.image.save(self.screen, str(p))
            return True
        except Exception:
            return False

    def _inject_click(self, x: float, y: float, button: str = "left") -> None:
        btn_map = {"left": 1, "middle": 2, "right": 3}
        b = btn_map.get(button, 1)
        # Pygame needs events in main thread, so queue them
        self._input_queue.append(
            pygame.event.Event(pygame.MOUSEMOTION, pos=(x, y))
        )
        self._input_queue.append(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=b)
        )
        self._input_queue.append(
            pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(x, y), button=b)
        )

    def _inject_key(self, key_name: str, pressed: bool) -> None:
        key_id = self._key_name_to_id(key_name)
        if key_id != 0:
            ev_type = pygame.KEYDOWN if pressed else pygame.KEYUP
            self._input_queue.append(
                pygame.event.Event(ev_type, key=key_id)
            )

    def _get_state(self) -> dict[str, Any]:
        # Allow game to inject its own state provider
        if hasattr(self, 'get_state') and self.get_state is not None:
            return self.get_state()
        return {
            "window": [self.width, self.height],
            "fps": self.fps,
            "title": self.title,
        }

    def _start_recording(self, fps: int, output_dir: str) -> dict[str, Any]:
        self._recording = True
        self._record_fps = fps
        self._record_dir = output_dir or "output/recordings"
        self._record_frame_count = 0
        self._record_timer = 0.0
        os.makedirs(self._record_dir, exist_ok=True)
        return {"ok": True, "fps": fps, "output_dir": self._record_dir}

    def _stop_recording(self) -> dict[str, Any]:
        self._recording = False
        return {
            "ok": True,
            "frames": self._record_frame_count,
            "output_dir": self._record_dir,
        }

    def _capture_frame(self) -> dict[str, Any]:
        ok = self._capture_frame_impl()
        return {"ok": ok, "frame": self._record_frame_count - 1 if ok else -1}

    def _capture_frame_impl(self) -> bool:
        if self.screen is None:
            return False
        path = os.path.join(
            self._record_dir,
            f"frame_{self._record_frame_count:04d}.png",
        )
        try:
            pygame.image.save(self.screen, path)
            self._record_frame_count += 1
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def _process_event(self, ev: pygame.event.Event) -> None:
        """Handle resize events."""
        if ev.type == pygame.VIDEORESIZE:
            self.width = ev.w
            self.height = ev.h
            self.screen = pygame.display.set_mode(
                (ev.w, ev.h), pygame.RESIZABLE,
            )

    @staticmethod
    def _key_name_to_id(name: str) -> int:
        _map: dict[str, int] = {
            "space": pygame.K_SPACE, "enter": pygame.K_RETURN,
            "return": pygame.K_RETURN, "escape": pygame.K_ESCAPE,
            "tab": pygame.K_TAB, "backspace": pygame.K_BACKSPACE,
            "up": pygame.K_UP, "down": pygame.K_DOWN,
            "left": pygame.K_LEFT, "right": pygame.K_RIGHT,
            "shift": pygame.K_LSHIFT, "ctrl": pygame.K_LCTRL,
            "alt": pygame.K_LALT,
            "a": pygame.K_a, "b": pygame.K_b, "c": pygame.K_c,
            "d": pygame.K_d, "e": pygame.K_e, "f": pygame.K_f,
            "g": pygame.K_g, "h": pygame.K_h, "i": pygame.K_i,
            "j": pygame.K_j, "k": pygame.K_k, "l": pygame.K_l,
            "m": pygame.K_m, "n": pygame.K_n, "o": pygame.K_o,
            "p": pygame.K_p, "q": pygame.K_q, "r": pygame.K_r,
            "s": pygame.K_s, "t": pygame.K_t, "u": pygame.K_u,
            "v": pygame.K_v, "w": pygame.K_w, "x": pygame.K_x,
            "y": pygame.K_y, "z": pygame.K_z,
            "0": pygame.K_0, "1": pygame.K_1, "2": pygame.K_2,
            "3": pygame.K_3, "4": pygame.K_4, "5": pygame.K_5,
            "6": pygame.K_6, "7": pygame.K_7, "8": pygame.K_8,
            "9": pygame.K_9,
            "f1": pygame.K_F1, "f2": pygame.K_F2, "f3": pygame.K_F3,
            "f4": pygame.K_F4, "f5": pygame.K_F5, "f6": pygame.K_F6,
            "f7": pygame.K_F7, "f8": pygame.K_F8, "f9": pygame.K_F9,
            "f10": pygame.K_F10, "f11": pygame.K_F11, "f12": pygame.K_F12,
        }
        return _map.get(name.lower(), 0)


# ------------------------------------------------------------------
# Standalone entry point
# ------------------------------------------------------------------

def main() -> None:
    """Default entry point — a blank window with harness bridge active."""
    engine = GameEngine(title="Game Framework (Python)")
    if not engine.init():
        return

    # Simple render: draw the engine state
    def render(screen: pygame.Surface) -> None:
        screen.fill((25, 25, 35))
        font = pygame.font.Font(None, 36)
        text = font.render("Harness TCP Bridge Active :19840", True, (255, 255, 255))
        screen.blit(text, (50, 50))

    engine.on_render = render
    engine.run()


if __name__ == "__main__":
    main()
