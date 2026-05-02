#!/usr/bin/env python3
"""Camera system for Pixel Werewolf.

Provides scrollable viewport with drag-to-pan for exploring
maps larger than the screen viewport.
"""

from __future__ import annotations

import pygame

# Default camera speed when using keyboard/auto-scroll
DEFAULT_SCROLL_SPEED = 400  # pixels per second


class Camera:
    """Viewport camera for scrolling game world.

    Manages camera position (world offset), bounds clamping,
    and drag-to-pan interaction.
    """

    # Inertia / momentum constants
    INERTIA_DECAY: float = 4.0       # 1/s — higher = faster deceleration
    INERTIA_MIN_SPEED: float = 8.0   # px/s — below this, stop
    MAX_VELOCITY: float = 2000.0     # px/s — velocity cap for safety

    def __init__(self, world_w: int, world_h: int, viewport_w: int, viewport_h: int):
        """
        Args:
            world_w: Total width of the game world in pixels.
            world_h: Total height of the game world in pixels.
            viewport_w: Width of the visible screen area in pixels.
            viewport_h: Height of the visible screen area in pixels.
        """
        self.world_w = world_w
        self.world_h = world_h
        self.viewport_w = viewport_w
        self.viewport_h = viewport_h

        # Camera position (top-left corner of viewport in world coordinates)
        self.x: float = 0.0
        self.y: float = 0.0

        # Inertia velocity (px/s)
        self._vx: float = 0.0
        self._vy: float = 0.0

        # Drag state
        self._dragging: bool = False
        self._drag_start_mouse: tuple[int, int] = (0, 0)
        self._drag_start_camera: tuple[float, float] = (0.0, 0.0)
        # Rolling history for inertia velocity estimation (last N deltas)
        self._drag_history: list[tuple[float, float]] = []
        self._drag_history_max: int = 4

        # Smooth following (optional target)
        self._target_x: float | None = None
        self._target_y: float | None = None
        self._smooth_speed: float = 8.0  # higher = faster snap

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """Return (min_x, min_y, max_x, max_y) camera bounds."""
        return (0.0, 0.0,
                max(0.0, float(self.world_w - self.viewport_w)),
                max(0.0, float(self.world_h - self.viewport_h)))

    def clamp(self) -> None:
        """Clamp camera position to world bounds."""
        min_x, min_y, max_x, max_y = self.bounds
        self.x = max(min_x, min(self.x, max_x))
        self.y = max(min_y, min(self.y, max_y))

    def pan(self, dx: float, dy: float) -> None:
        """Move camera by delta (world pixels)."""
        self.x += dx
        self.y += dy
        self.clamp()

    def move_to(self, x: float, y: float) -> None:
        """Set camera position directly (clamped)."""
        self.x = x
        self.y = y
        self.clamp()

    def centre_on(self, world_x: float, world_y: float) -> None:
        """Centre the viewport on a world coordinate."""
        self.x = world_x - self.viewport_w / 2
        self.y = world_y - self.viewport_h / 2
        self.clamp()

    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        """Convert world coordinates to screen coordinates."""
        return (wx - self.x, wy - self.y)

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        """Convert screen coordinates to world coordinates."""
        return (sx + self.x, sy + self.y)

    def start_drag(self, mouse_x: int, mouse_y: int) -> None:
        """Begin drag-to-pan at the given mouse position."""
        self._dragging = True
        self._drag_start_mouse = (mouse_x, mouse_y)
        self._drag_start_camera = (self.x, self.y)
        self._drag_history.clear()
        self._vx = 0.0
        self._vy = 0.0

    def update_drag(self, mouse_x: int, mouse_y: int) -> None:
        """Continue drag — update camera position based on mouse delta."""
        if not self._dragging:
            return
        dx = self._drag_start_mouse[0] - mouse_x
        dy = self._drag_start_mouse[1] - mouse_y
        self.x = self._drag_start_camera[0] + dx
        self.y = self._drag_start_camera[1] + dy
        self.clamp()

        # Record delta for velocity estimation (relative to previous position)
        self._drag_history.append((dx, dy))
        if len(self._drag_history) > self._drag_history_max:
            self._drag_history.pop(0)

    def end_drag(self) -> None:
        """End drag-to-pan. Computes inertia velocity from recent drag history."""
        self._dragging = False
        # Estimate final velocity from the rolling delta history
        if len(self._drag_history) >= 2:
            # Use the difference between last and first entry ÷ history length
            first = self._drag_history[0]
            last = self._drag_history[-1]
            dt_approx = len(self._drag_history) * (1.0 / 60.0)  # assume ~60fps
            if dt_approx > 0:
                self._vx = (first[0] - last[0]) / dt_approx  # note: screen coords are inverted
                self._vy = (first[1] - last[1]) / dt_approx
        # Clamp velocity to prevent wild flings
        max_v = self.MAX_VELOCITY
        self._vx = max(-max_v, min(self._vx, max_v))
        self._vy = max(-max_v, min(self._vy, max_v))

    def update(self, dt: float) -> None:
        """Per-frame update for inertia/momentum simulation.

        Call every frame from the main game loop.  When the user has
        released a drag with non-zero velocity, the camera coasts
        to a stop with exponential decay plus bounce at world edges.
        """
        if self._dragging:
            return  # inertia paused while actively dragging

        has_velocity = (
            abs(self._vx) > self.INERTIA_MIN_SPEED or
            abs(self._vy) > self.INERTIA_MIN_SPEED
        )
        if not has_velocity:
            self._vx = 0.0
            self._vy = 0.0
            return

        # Apply velocity
        self.x += self._vx * dt
        self.y += self._vy * dt

        # Bounce off world edges with energy loss
        min_x, min_y, max_x, max_y = self.bounds
        bounced = False
        if self.x < min_x:
            self.x = min_x
            self._vx = -self._vx * 0.4
            bounced = True
        elif self.x > max_x:
            self.x = max_x
            self._vx = -self._vx * 0.4
            bounced = True
        if self.y < min_y:
            self.y = min_y
            self._vy = -self._vy * 0.4
            bounced = True
        elif self.y > max_y:
            self.y = max_y
            self._vy = -self._vy * 0.4
            bounced = True

        # Exponential decay (skip on the frame we bounced, let it settle)
        if not bounced:
            factor = 1.0 / (1.0 + self.INERTIA_DECAY * dt)
            self._vx *= factor
            self._vy *= factor

        # Snap to zero below threshold
        if abs(self._vx) < self.INERTIA_MIN_SPEED:
            self._vx = 0.0
        if abs(self._vy) < self.INERTIA_MIN_SPEED:
            self._vy = 0.0

        self.clamp()

    def is_dragging(self) -> bool:
        """Return True if currently in a drag operation."""
        return self._dragging

    def update_smooth(self, dt: float) -> None:
        """Smoothly interpolate toward target position if set."""
        if self._target_x is not None:
            self.x += (self._target_x - self.x) * min(1.0, self._smooth_speed * dt)
        if self._target_y is not None:
            self.y += (self._target_y - self.y) * min(1.0, self._smooth_speed * dt)
        self.clamp()

    def set_target(self, x: float | None, y: float | None) -> None:
        """Set a target for smooth interpolation (None to cancel)."""
        self._target_x = x
        self._target_y = y

    def set_viewport(self, viewport_w: int, viewport_h: int) -> None:
        """Update viewport dimensions (e.g. on window resize).

        Also clamps the camera position to the new bounds.
        """
        self.viewport_w = viewport_w
        self.viewport_h = viewport_h
        self.clamp()

    def reset(self) -> None:
        """Reset camera to origin (top-left)."""
        self.x = 0.0
        self.y = 0.0
        self._dragging = False
        self._target_x = None
        self._target_y = None

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle a pygame event for drag-to-pan.
        Returns True if the event was consumed.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left button starts drag
                self.start_drag(event.pos[0], event.pos[1])
                return True
            if event.button == 4:  # Scroll up — could zoom in future
                pass
            if event.button == 5:  # Scroll down — could zoom in future
                pass
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self._dragging:
                self.end_drag()
                return True
        elif event.type == pygame.MOUSEMOTION:
            if self._dragging:
                self.update_drag(event.pos[0], event.pos[1])
                return True
        return False

    def __repr__(self) -> str:
        return f"Camera(x={self.x:.0f}, y={self.y:.0f}, view=({self.viewport_w}x{self.viewport_h}), world=({self.world_w}x{self.world_h}))"
