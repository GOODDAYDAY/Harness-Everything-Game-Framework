#!/usr/bin/env python3
"""Procedural sound effects for Pixel Werewolf.

Generates short sound effects using pygame.mixer and sndarray.
No external audio files needed — all sounds are synthesized.
"""

from __future__ import annotations

import math
import struct
from typing import Optional

import pygame

# Default sample rate / bit depth
SAMPLE_RATE = 44100
BITS = -16  # signed 16-bit
CHANNELS = 2  # stereo

# Cache of generated sounds
_sound_cache: dict[str, pygame.mixer.Sound] = {}


def _init_mixer() -> None:
    """Ensure pygame.mixer is initialised (safe to call multiple times)."""
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init(frequency=SAMPLE_RATE, size=BITS, channels=CHANNELS)
        except pygame.error:
            pass  # headless / no audio device — sounds will be silent


def _make_sound(
    buffer: list[float],
    *,
    sample_rate: int = SAMPLE_RATE,
    volume: float = 1.0,
) -> pygame.mixer.Sound:
    """Convert a list of float samples (-1 to 1) to a Sound object."""
    max_amp = 32767
    raw = bytearray()
    for s in buffer:
        clipped = max(-1.0, min(1.0, s * volume))
        packed = struct.pack("<h", int(clipped * max_amp))
        # duplicate for stereo (left = right)
        raw.extend(packed)
        raw.extend(packed)
    sound = pygame.mixer.Sound(bytes(raw))
    return sound


def _ads_envelope(
    duration: float,
    *,
    attack: float = 0.02,
    decay: float = 0.1,
    sustain_level: float = 0.7,
    sample_rate: int = SAMPLE_RATE,
) -> list[float]:
    """Generate a simple Attack-Decay-Sustain (no release) amplitude envelope."""
    n = int(duration * sample_rate)
    out = [0.0] * n
    a_end = int(attack * sample_rate)
    d_end = a_end + int(decay * sample_rate)
    for i in range(n):
        if i < a_end:
            out[i] = i / a_end
        elif i < d_end:
            t = (i - a_end) / (d_end - a_end) if d_end > a_end else 1.0
            out[i] = 1.0 - (1.0 - sustain_level) * t
        else:
            out[i] = sustain_level
    return out


def _sine(duration: float, freq: float, sample_rate: int = SAMPLE_RATE) -> list[float]:
    n = int(duration * sample_rate)
    return [math.sin(2.0 * math.pi * freq * i / sample_rate) for i in range(n)]


def _square(duration: float, freq: float, sample_rate: int = SAMPLE_RATE) -> list[float]:
    n = int(duration * sample_rate)
    return [1.0 if math.sin(2.0 * math.pi * freq * i / sample_rate) >= 0 else -1.0 for i in range(n)]


def _white_noise(duration: float, sample_rate: int = SAMPLE_RATE) -> list[float]:
    import random
    n = int(duration * sample_rate)
    return [random.uniform(-1.0, 1.0) for _ in range(n)]


# ── Public sound generators ────────────────────────────────────────────────


def day_chime() -> Optional[pygame.mixer.Sound]:
    """Gentle ascending chime when day breaks."""
    key = "day_chime"
    if key in _sound_cache:
        return _sound_cache[key]
    _init_mixer()
    dur = 0.4
    a = _sine(dur, 660.0)  # E5
    b = _sine(dur, 880.0)  # A5
    env = _ads_envelope(dur, attack=0.01, decay=0.15, sustain_level=0.4)
    mix = [(a[i] * 0.5 + b[i] * 0.5) * env[i] for i in range(len(a))]
    sound = _make_sound(mix, volume=0.3)
    _sound_cache[key] = sound
    return sound


def night_chime() -> Optional[pygame.mixer.Sound]:
    """Descending chime when night falls."""
    key = "night_chime"
    if key in _sound_cache:
        return _sound_cache[key]
    _init_mixer()
    dur = 0.5
    a = _sine(dur, 440.0)  # A4
    b = _sine(dur, 330.0)  # E4
    env = _ads_envelope(dur, attack=0.01, decay=0.2, sustain_level=0.3)
    mix = [(a[i] * 0.5 + b[i] * 0.5) * env[i] for i in range(len(a))]
    sound = _make_sound(mix, volume=0.3)
    _sound_cache[key] = sound
    return sound


def kill_sting() -> Optional[pygame.mixer.Sound]:
    """Short dramatic sting for a death announcement."""
    key = "kill_sting"
    if key in _sound_cache:
        return _sound_cache[key]
    _init_mixer()
    dur = 0.6
    a = _square(dur, 110.0)  # A2
    b = _sine(dur, 55.0)     # A1
    noise = _white_noise(dur)
    env = _ads_envelope(dur, attack=0.005, decay=0.3, sustain_level=0.2)
    mix = [(a[i] * 0.3 + b[i] * 0.4 + noise[i] * 0.3) * env[i] for i in range(len(a))]
    sound = _make_sound(mix, volume=0.35)
    _sound_cache[key] = sound
    return sound


def vote_bell() -> Optional[pygame.mixer.Sound]:
    """Bell sound when votes are being cast."""
    key = "vote_bell"
    if key in _sound_cache:
        return _sound_cache[key]
    _init_mixer()
    dur = 0.3
    a = _sine(dur, 523.0)  # C5
    env = _ads_envelope(dur, attack=0.002, decay=0.15, sustain_level=0.1)
    mix = [a[i] * env[i] for i in range(len(a))]
    sound = _make_sound(mix, volume=0.25)
    _sound_cache[key] = sound
    return sound


def vote_result() -> Optional[pygame.mixer.Sound]:
    """Triumphant or tense sound when vote result is announced."""
    key = "vote_result"
    if key in _sound_cache:
        return _sound_cache[key]
    _init_mixer()
    dur = 0.5
    a = _sine(dur, 392.0)  # G4
    b = _sine(dur, 523.0)  # C5
    env = _ads_envelope(dur, attack=0.01, decay=0.2, sustain_level=0.3)
    mix = [(a[i] * 0.4 + b[i] * 0.6) * env[i] for i in range(len(a))]
    sound = _make_sound(mix, volume=0.3)
    _sound_cache[key] = sound
    return sound


def game_over_victory() -> Optional[pygame.mixer.Sound]:
    """Dramatic fanfare for victory."""
    key = "game_over_victory"
    if key in _sound_cache:
        return _sound_cache[key]
    _init_mixer()
    dur = 1.2
    # Three-note ascending fanfare
    notes = [(523, 0.0), (659, 0.3), (784, 0.6)]  # C5, E5, G5
    n = int(dur * SAMPLE_RATE)
    mix = [0.0] * n
    env = _ads_envelope(dur, attack=0.01, decay=0.4, sustain_level=0.3)
    for freq, start in notes:
        off = int(start * SAMPLE_RATE)
        note_dur = min(dur - start, 0.6)
        note = _sine(note_dur, freq)
        for i, val in enumerate(note):
            idx = off + i
            if idx < n:
                mix[idx] += val * 0.4
    mix = [mix[i] * env[i] for i in range(n)]
    sound = _make_sound(mix, volume=0.4)
    _sound_cache[key] = sound
    return sound


def game_over_defeat() -> Optional[pygame.mixer.Sound]:
    """Sombre descending notes for defeat."""
    key = "game_over_defeat"
    if key in _sound_cache:
        return _sound_cache[key]
    _init_mixer()
    dur = 1.0
    notes = [(392, 0.0), (349, 0.3), (330, 0.6)]  # G4, F4, E4
    n = int(dur * SAMPLE_RATE)
    mix = [0.0] * n
    env = _ads_envelope(dur, attack=0.02, decay=0.3, sustain_level=0.2)
    for freq, start in notes:
        off = int(start * SAMPLE_RATE)
        note_dur = min(dur - start, 0.4)
        note = _sine(note_dur, freq)
        for i, val in enumerate(note):
            idx = off + i
            if idx < n:
                mix[idx] += val * 0.35
    mix = [mix[i] * env[i] for i in range(n)]
    sound = _make_sound(mix, volume=0.35)
    _sound_cache[key] = sound
    return sound


def clear_cache() -> None:
    """Clear the sound cache (e.g., when shutting down)."""
    _sound_cache.clear()
