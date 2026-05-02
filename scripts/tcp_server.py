#!/usr/bin/env python3
"""TCP bridge server for harness game tools.

Replaces Godot's test_harness.gd. Runs in a background thread alongside
the pygame game loop. Listens on 127.0.0.1:19840 for JSON commands.

Protocol: newline-delimited JSON.
Commands: ping, screenshot, input_click, input_key, state, quit,
          record_start, record_stop, record_frame
"""

from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from typing import Any, Callable


class TcpBridge:
    """TCP server that handles harness commands for a pygame game."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 19840,
        *,
        on_screenshot: Callable[[str], bool] | None = None,
        on_input_click: Callable[[float, float, str], None] | None = None,
        on_input_key: Callable[[str, bool], None] | None = None,
        on_state: Callable[[], dict[str, Any]] | None = None,
        on_quit: Callable[[], None] | None = None,
        on_record_start: Callable[[int, str], dict[str, Any]] | None = None,
        on_record_stop: Callable[[], dict[str, Any]] | None = None,
        on_record_frame: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._on_screenshot = on_screenshot
        self._on_input_click = on_input_click
        self._on_input_key = on_input_key
        self._on_state = on_state
        self._on_quit = on_quit
        self._on_record_start = on_record_start
        self._on_record_stop = on_record_stop
        self._on_record_frame = on_record_frame
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> bool:
        """Start listening. Returns True on success."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._sock.bind((self._host, self._port))
            self._sock.listen(1)
            self._sock.settimeout(1.0)
        except OSError as exc:
            print(f"[TcpBridge] Failed to bind {self._host}:{self._port}: {exc}")
            return False
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        print(f"[TcpBridge] Listening on {self._host}:{self._port}")
        return True

    def stop(self) -> None:
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    # ------------------------------------------------------------------
    # Serve loop
    # ------------------------------------------------------------------

    def _serve(self) -> None:
        buf = b""
        conn: socket.socket | None = None
        while self._running:
            try:
                if conn is None:
                    conn, _addr = self._sock.accept()  # type: ignore[union-attr]
                    conn.settimeout(1.0)
                    buf = b""
                    continue

                data = conn.recv(4096)
                if not data:
                    conn.close()
                    conn = None
                    continue

                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    response = self._handle(line.decode("utf-8").strip())
                    if response is not None:
                        conn.sendall((json.dumps(response) + "\n").encode())

            except socket.timeout:
                continue
            except (ConnectionResetError, BrokenPipeError, OSError):
                if conn:
                    conn.close()
                conn = None
                buf = b""

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def _handle(self, raw: str) -> dict[str, Any] | None:
        try:
            msg: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            return {"ok": False, "error": "Invalid JSON"}

        cmd: str = msg.get("cmd", "")

        if cmd == "ping":
            return {"ok": True, "engine": "pygame", "version": "python"}

        if cmd == "screenshot":
            path = msg.get("path", "/tmp/game_screenshot.png")
            if self._on_screenshot:
                ok = self._on_screenshot(path)
                return {"ok": ok, "path": path}
            return {"ok": False, "error": "screenshot not implemented"}

        if cmd == "input_click":
            x = float(msg.get("x", 0))
            y = float(msg.get("y", 0))
            btn = msg.get("button", "left")
            if self._on_input_click:
                self._on_input_click(x, y, btn)
                return {"ok": True}
            return {"ok": False, "error": "input not implemented"}

        if cmd == "input_key":
            key = msg.get("key", "")
            pressed = msg.get("pressed", True)
            if self._on_input_key:
                self._on_input_key(key, bool(pressed))
                return {"ok": True}
            return {"ok": False, "error": "input not implemented"}

        if cmd == "state":
            if self._on_state:
                return {"ok": True, "state": self._on_state()}
            return {"ok": True, "state": {}}

        if cmd == "quit":
            if self._on_quit:
                self._on_quit()
            return {"ok": True}

        if cmd == "record_start":
            fps = int(msg.get("fps", 6))
            out_dir = msg.get("output_dir", "")
            if self._on_record_start:
                return self._on_record_start(fps, out_dir)
            return {"ok": False, "error": "recording not implemented"}

        if cmd == "record_stop":
            if self._on_record_stop:
                return self._on_record_stop()
            return {"ok": False, "error": "recording not implemented"}

        if cmd == "record_frame":
            if self._on_record_frame:
                return self._on_record_frame()
            return {"ok": False, "error": "recording not implemented"}

        return {"ok": False, "error": f"unknown command: {cmd}"}
