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


def _pink_noise(duration: float, sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Pink noise (1/f) — softer, more natural than white noise."""
    import random
    n = int(duration * sample_rate)
    b = [0.0] * 7
    out = [0.0] * n
    for i in range(n):
        w = random.uniform(-1.0, 1.0)
        b[0] = 0.99886 * b[0] + w * 0.0555179
        b[1] = 0.99332 * b[1] + w * 0.0750759
        b[2] = 0.96900 * b[2] + w * 0.1538520
        b[3] = 0.86650 * b[3] + w * 0.3104856
        b[4] = 0.55000 * b[4] + w * 0.5329522
        b[5] = -0.7616 * b[5] - w * 0.0168980
        out[i] = b[0] + b[1] + b[2] + b[3] + b[4] + b[5] + b[6] + w * 0.5362
        b[6] = w * 0.115926
        out[i] *= 0.11  # normalize
    return out


def _low_pass(samples: list[float], cutoff_ratio: float = 0.3) -> list[float]:
    """Simple one-pole low-pass filter (cutoff_ratio 0-1)."""
    out = [0.0] * len(samples)
    prev = 0.0
    for i, s in enumerate(samples):
        prev += cutoff_ratio * (s - prev)
        out[i] = prev
    return out


def _sawtooth(duration: float, freq: float, sample_rate: int = SAMPLE_RATE) -> list[float]:
    """Sawtooth wave."""
    n = int(duration * sample_rate)
    period = sample_rate / freq
    return [(2.0 * (i % period) / period - 1.0) for i in range(n)]


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


def night_ambience() -> Optional[pygame.mixer.Sound]:
    """Low wind ambience for night phase.
    Looping wind with subtle cricket chirps.
    """
    key = "night_ambience"
    if key in _sound_cache:
        return _sound_cache[key]
    _init_mixer()
    if not pygame.mixer.get_init():
        return None
    duration = 4.0
    sr = SAMPLE_RATE
    n = int(duration * sr)
    # Wind: low-passed pink noise
    wind = _low_pass(_pink_noise(duration, sr), 0.08)
    # Scale wind to gentle volume
    wind = [w * 0.3 for w in wind]
    # Cricket chirps: short high-frequency pulses
    import random
    crickets = [0.0] * n
    chirp_interval = int(0.5 * sr)  # every 0.5s
    for i in range(0, n, chirp_interval):
        if random.random() < 0.4:
            for j in range(int(0.04 * sr)):
                if i + j < n:
                    chirp = 0.15 * (_sawtooth(0.04, 4000 + random.uniform(-1000, 1000), sr)[j] if j < int(0.04 * sr) else 0)
                    if random.random() < 0.5 and i + j < n:
                        crickets[i + j] = chirp
    # Combine
    combined = [min(1.0, max(-1.0, wind[i] + crickets[i])) for i in range(n)]
    buf = bytearray()
    for s in combined:
        val = max(-32768, min(32767, int(s * 32767)))
        buf.extend([val & 0xFF, (val >> 8) & 0xFF])
        buf.extend([val & 0xFF, (val >> 8) & 0xFF])
    sound = pygame.mixer.Sound(buffer=bytes(buf))
    _sound_cache[key] = sound
    return sound


def day_ambience() -> Optional[pygame.mixer.Sound]:
    """Daytime village ambience: gentle birdsong and rustle."""
    key = "day_ambience"
    if key in _sound_cache:
        return _sound_cache[key]
    _init_mixer()
    if not pygame.mixer.get_init():
        return None
    duration = 4.0
    sr = SAMPLE_RATE
    n = int(duration * sr)
    # Background: soft pink noise (wind / rustle)
    bg = _low_pass(_pink_noise(duration, sr), 0.15)
    bg = [b * 0.15 for b in bg]
    # Bird chirps: short high-pitched melodic notes
    import random
    birds = [0.0] * n
    note_freqs = [2000, 2500, 3000, 3500, 2800, 2200, 3200]
    for i in range(0, n, int(0.8 * sr)):
        if random.random() < 0.5:
            freq = random.choice(note_freqs)
            note_len = int(0.08 * sr)
            saw = _sawtooth(0.08, freq, sr)
            for j in range(min(note_len, n - i)):
                birds[i + j] = 0.08 * saw[j]
    # Combine
    combined = [min(1.0, max(-1.0, bg[i] + birds[i])) for i in range(n)]
    buf = bytearray()
    for s in combined:
        val = max(-32768, min(32767, int(s * 32767)))
        buf.extend([val & 0xFF, (val >> 8) & 0xFF])
        buf.extend([val & 0xFF, (val >> 8) & 0xFF])
    sound = pygame.mixer.Sound(buffer=bytes(buf))
    _sound_cache[key] = sound
    return sound


def clear_cache() -> None:
    """Clear the sound cache (e.g., when shutting down)."""
    _sound_cache.clear()
