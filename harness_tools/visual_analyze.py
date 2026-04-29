"""Visual analysis tools for Godot screenshots.

Two tools:
- visual_analyze: Pillow-based pixel analysis (free, no API key needed)
- gemini_vision:  Gemini 2.5 Flash vision API (needs GEMINI_API_KEY env var)
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image

from harness.tools.base import Tool, ToolResult
from harness.core.config import HarnessConfig

log = logging.getLogger(__name__)

_EXPECTED_SIZE = (2560, 1440)
_TILE_SIZE = 80
_GRID_COLS = _EXPECTED_SIZE[0] // _TILE_SIZE  # 32
_GRID_ROWS = _EXPECTED_SIZE[1] // _TILE_SIZE  # 18
_MAX_PNG_BYTES = 500 * 1024


def _dominant_color(pixels: list[tuple[int, int, int]]) -> tuple[int, int, int]:
    return Counter(pixels).most_common(1)[0][0] if pixels else (0, 0, 0)


def _brightness(rgb: tuple[int, int, int]) -> float:
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def _is_warm_light(r: int, g: int, b: int) -> bool:
    return r > 200 and g > 150 and b < 130


class VisualAnalyzeTool(Tool):
    """Analyse a Godot screenshot and produce a structured text description."""

    name = "visual_analyze"
    description = (
        "Analyse a Godot screenshot PNG and return a structured text description "
        "of the visual scene: time of day (sky colour), tile-level brightness map "
        "(ASCII art), detected UI edges, character positions, and lit windows. "
        "Essential for understanding what the game actually renders — use after "
        "every game_screenshot."
    )
    requires_path_check = False

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "screenshot_path": {
                    "type": "string",
                    "description": "Path to the PNG screenshot to analyse",
                },
            },
            "required": ["screenshot_path"],
        }

    async def execute(self, config: HarnessConfig, **params: Any) -> ToolResult:
        path_str: str = params["screenshot_path"]

        # Validate path through harness security
        path_result = self._check_path(config, path_str, require_exists=True)
        is_valid, validated = self._validate_path_result(path_result)
        if not is_valid:
            return validated  # type: ignore[return-value]

        p = Path(str(validated))

        # Size cap
        file_size = p.stat().st_size
        if file_size > _MAX_PNG_BYTES:
            return ToolResult(
                error=f"Screenshot too large: {file_size / 1024:.0f} KB (max 500 KB)",
                is_error=True,
            )

        # Open image (offload blocking I/O)
        try:
            img = await asyncio.to_thread(Image.open, p)
            img = await asyncio.to_thread(img.convert, "RGB")
        except Exception as exc:
            return ToolResult(error=f"Failed to open PNG: {exc}", is_error=True)

        w, h = img.size
        size_warn = ""
        if (w, h) != _EXPECTED_SIZE:
            size_warn = (
                f"Warning: image {w}x{h} differs from expected "
                f"{_EXPECTED_SIZE[0]}x{_EXPECTED_SIZE[1]}. Analysis may degrade.\n\n"
            )

        # ---- Sky band analysis (top 240 px) ----
        sky_px = dark_px = total = 0
        for y in range(min(240, h)):
            row_pixels = [img.getpixel((x, y)) for x in range(w)]
            for r, g, b in row_pixels:
                total += 1
                if 100 <= r <= 220 and 140 <= g <= 220 and 200 <= b <= 255:
                    sky_px += 1
                if r < 50 and g < 50 and b < 70:
                    dark_px += 1

        if sky_px / max(total, 1) > 0.25:
            time_of_day = "DAY"
        elif dark_px / max(total, 1) > 0.4:
            time_of_day = "NIGHT"
        else:
            time_of_day = "TWILIGHT/TRANSITION"

        # ---- Tile grid ----
        ui_tiles: list[str] = []
        char_tiles: list[str] = []
        lit_tiles: list[str] = []
        ascii_rows: list[str] = []

        for row in range(_GRID_ROWS):
            chars: list[str] = []
            for col in range(_GRID_COLS):
                left = col * _TILE_SIZE
                upper = row * _TILE_SIZE
                tile_pixels = [
                    img.getpixel((x, y))
                    for y in range(upper, min(upper + _TILE_SIZE, h))
                    for x in range(left, min(left + _TILE_SIZE, w))
                ]
                if not tile_pixels:
                    chars.append("?")
                    continue

                dom = _dominant_color(tile_pixels)
                br = _brightness(dom)
                dr, dg, db = dom

                # Brightness char map
                if br > 210:
                    chars.append(" ")
                elif br > 160:
                    chars.append(".")
                elif br > 110:
                    chars.append("-")
                elif br > 60:
                    chars.append("+")
                else:
                    chars.append("#")

                # Heuristics
                on_edge = col in (0, _GRID_COLS - 1) or row in (0, _GRID_ROWS - 1)
                is_bright = br > 200
                is_dark = br < 35
                if on_edge and (is_bright or is_dark):
                    ui_tiles.append(f"({col},{row})")

                sat = max(dr, dg, db) - min(dr, dg, db)
                if 3 <= row <= 14 and sat > 50 and 40 < br < 220:
                    char_tiles.append(f"({col},{row})")

                if _is_warm_light(dr, dg, db):
                    lit_tiles.append(f"({col},{row})")

            ascii_rows.append("".join(chars))

        # ---- Build output ----
        lines: list[str] = []
        lines.append(f"=== Visual Analysis: {p.name} ===")
        lines.append(f"Size: {w}x{h} | File: {file_size / 1024:.0f} KB")
        lines.append(f"Time of day: {time_of_day}")
        if size_warn:
            lines.append(size_warn.rstrip())
        lines.append("")

        lines.append("--- Brightness Map (32x18 tiles, . = bright, # = dark) ---")
        for i, ascii_row in enumerate(ascii_rows):
            lines.append(f" r{i:2d} {ascii_row}")
        lines.append("")

        if ui_tiles:
            lines.append(f"--- UI Edge Tiles ({len(ui_tiles)}) ---")
            lines.append(f"  {', '.join(ui_tiles[:20])}")
            lines.append("")

        if char_tiles:
            lines.append(f"--- Character-like Tiles ({len(char_tiles)}) ---")
            lines.append(f"  {', '.join(char_tiles[:30])}")
            lines.append("")

        if lit_tiles:
            lines.append(
                f"--- Lit Windows ({len(lit_tiles)}) — warm glow detected ---"
            )
            lines.append(f"  {', '.join(lit_tiles[:30])}")
            lines.append("")

        lines.append("=== End ===")

        return ToolResult(output="\n".join(lines))


# ---------------------------------------------------------------------------
# Gemini Vision tool (Google AI Studio — free tier, 1500 req/day)
# ---------------------------------------------------------------------------

_GEMINI_MODEL = "gemini-flash-latest"
# Resize screenshots to max 1024px on longest side to stay under free-tier
# limits and reduce latency.  1024 px is plenty for UI/text assessment.
_GEMINI_MAX_DIM = 512
_GEMINI_TIMEOUT = 30.0  # seconds


class GeminiVisionTool(Tool):
    """Analyse a Godot screenshot using Google Gemini 2.5 Flash (free tier).

    Sends the PNG as a base64 image to the Gemini API and returns an
    AI-written text description of what's on screen: phase, UI state,
    character positions, any visual bugs, text content, colour scheme.

    Requires ``GEMINI_API_KEY`` environment variable.
    """

    name = "gemini_vision"
    description = (
        "Send a Godot screenshot to Gemini 2.5 Flash for AI vision analysis. "
        "Returns a detailed text description of the game screen: what phase "
        "is shown, UI element states, character positions, text content, "
        "colour scheme, and any visual anomalies.  Much more accurate than "
        "pixel-based visual_analyze.  Requires GEMINI_API_KEY env var. "
        "Free tier: 1500 requests/day."
    )
    requires_path_check = False

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "screenshot_path": {
                    "type": "string",
                    "description": "Path to the PNG screenshot to analyse",
                },
                "question": {
                    "type": "string",
                    "description": (
                        "Specific question about the screenshot. "
                        "Defaults to a general description request. "
                        "Example: 'Is the vote button visible? "
                        "What does the phase label say?'"
                    ),
                    "default": "",
                },
            },
            "required": ["screenshot_path"],
        }

    async def execute(self, config: HarnessConfig, **params: Any) -> ToolResult:
        import urllib.request
        import json as _json

        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return ToolResult(
                error="GEMINI_API_KEY environment variable not set. "
                      "Get a free key at https://aistudio.google.com/apikey",
                is_error=True,
            )

        path_str: str = params["screenshot_path"]
        question: str = params.get("question", "")

        # Validate path
        path_result = self._check_path(config, path_str, require_exists=True)
        is_valid, validated = self._validate_path_result(path_result)
        if not is_valid:
            return validated  # type: ignore[return-value]

        p = Path(str(validated))

        # Size cap
        file_size = p.stat().st_size
        if file_size > _MAX_PNG_BYTES:
            return ToolResult(
                error=f"Screenshot too large: {file_size / 1024:.0f} KB (max 500 KB)",
                is_error=True,
            )

        # Open and optionally resize image, then base64 encode
        try:
            img = await asyncio.to_thread(Image.open, p)
            w, h = img.size
            # Resize if needed to stay under Gemini free-tier limits
            longest = max(w, h)
            if longest > _GEMINI_MAX_DIM:
                scale = _GEMINI_MAX_DIM / longest
                new_size = (int(w * scale), int(h * scale))
                img = await asyncio.to_thread(img.resize, new_size, Image.LANCZOS)
                log.info("gemini_vision: resized %dx%d -> %dx%d", w, h, *new_size)
                w, h = new_size

            # Convert to RGB JPEG bytes (smaller than PNG base64)
            import io
            buf = io.BytesIO()
            rgb = await asyncio.to_thread(img.convert, "RGB")
            await asyncio.to_thread(rgb.save, buf, format="JPEG", quality=75)
            img_bytes = buf.getvalue()
        except Exception as exc:
            return ToolResult(error=f"Failed to read image: {exc}", is_error=True)

        b64 = base64.b64encode(img_bytes).decode("ascii")

        # Build Gemini API request
        prompt = question or (
            "Describe this game screenshot in detail. What phase is shown? "
            "What UI elements are visible and what do they say? "
            "Where are characters positioned? What is the colour scheme? "
            "Any visual bugs or layout issues? Keep it concise."
        )

        request_body = _json.dumps({
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
                ]
            }],
            "generationConfig": {"maxOutputTokens": 600, "temperature": 0.2},
        }).encode("utf-8")

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{_GEMINI_MODEL}:generateContent?key={api_key}"
        )

        try:
            req = urllib.request.Request(
                url, data=request_body,
                headers={"Content-Type": "application/json"},
            )
            resp = await asyncio.to_thread(
                urllib.request.urlopen, req, timeout=_GEMINI_TIMEOUT,
            )
            data = _json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            return ToolResult(
                error=f"Gemini API call failed: {exc}", is_error=True,
            )

        # Extract text from response
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return ToolResult(
                error=f"Unexpected Gemini response: {_json.dumps(data)[:500]}",
                is_error=True,
            )

        return ToolResult(
            output=f"=== Gemini Vision ({w}x{h}, {file_size / 1024:.0f} KB) ===\n{text}",
            metadata={"model": _GEMINI_MODEL, "dimensions": [w, h]},
        )
