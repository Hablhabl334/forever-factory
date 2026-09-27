"""Copyright-free ambient music, synthesized from scratch with numpy.

A slow seeded pad progression plus sparse bell tones and a whisper of
filtered noise — an original soundscape per episode (seeded by the
story seed), so there is nothing to license and nothing can expire.

Memory-lean: returns a float32 MONO array (the stereo widening happens
at mix time) — a 13-minute bed is ~140 MB, not gigabytes.
"""
from __future__ import annotations

import numpy as np

SR = 44_100

# gentle pentatonic-ish chord sets (Hz built from A3=220)
CHORDS = [
    (174.6, 220.0, 261.6, 329.6),    # Fmaj7-ish
    (146.8, 220.0, 293.7, 349.2),    # Dmin add
    (130.8, 196.0, 261.6, 329.6),    # C add9
    (155.6, 233.1, 311.1, 389.9),    # Eb maj7-ish
    (164.8, 220.0, 277.2, 329.6),    # E-ish soft
    (146.8, 220.0, 246.9, 311.1),    # Dmin9-ish
]
BELLS = [523.3, 587.3, 659.3, 784.0, 880.0, 1046.5, 1174.7]


def _moving_average(x: np.ndarray, k: int) -> np.ndarray:
    """O(n) smoothing (lesson from v2: never convolve with huge kernels)."""
    if k <= 1:
        return x
    cs = np.cumsum(np.insert(x.astype(np.float32), 0, np.float32(0)), dtype=np.float32)
    out = (cs[k:] - cs[:-k]) / k
    pad = np.full(k - 1, out[0], dtype=np.float32)
    return np.concatenate([pad, out])


def synth_music(seed: int, duration: float, sr: int = SR) -> np.ndarray:
    """Return mono float32 mix, peak-normalized to ~0.5."""
    rng = np.random.default_rng(seed)
    n = int(duration * sr)

    # ── pad: slow chord progression, rendered chord by chord ────────
    pad = np.zeros(n, dtype=np.float32)
    chord_len = 18.0
    step = chord_len - 3.0
    i = 0
    pos = 0
    while pos < n:
        chord = CHORDS[i % len(CHORDS)]
        seg_n = min(int(chord_len * sr), n - pos)
        seg_t = (np.arange(seg_n, dtype=np.float32) / sr)
        seg = np.zeros(seg_n, dtype=np.float32)
        for k, f in enumerate(chord):
            ph = float(rng.uniform(0, 2 * np.pi))
            det = 1.0 + 0.0015 * np.sin(2 * np.pi * (0.03 + 0.01 * k) * seg_t + ph)
            w = np.sin(2 * np.pi * f * det * seg_t + ph, dtype=np.float32)
            w += 0.35 * np.sin(2 * np.pi * f * 2 * det * seg_t, dtype=np.float32)
            w *= (0.55 + 0.45 * np.sin(2 * np.pi * 0.05 * seg_t + k, dtype=np.float32))
            seg += w / (k + 2.0)
        # edges: fade in 3s (except at t=0 for the very first chord)
        fade = min(seg_n, int(3.0 * sr))
        env = np.ones(seg_n, dtype=np.float32)
        env[:fade] = np.linspace(0, 1, fade, dtype=np.float32)
        if i == 0:
            env[:fade] = np.linspace(0.2, 1.0, fade, dtype=np.float32)
        seg *= env
        pad[pos:pos + seg_n] += seg
        pos += int(step * sr)
        i += 1

    pad = _moving_average(pad, int(0.02 * sr))  # soften highs

    # ── bells: sparse decaying tones ───────────────────────────────
    bells = np.zeros(n, dtype=np.float32)
    n_bells = max(4, int(duration / 9.0))
    for _ in range(n_bells):
        start = rng.uniform(0, max(0.1, duration - 4))
        f = BELLS[rng.integers(0, len(BELLS))]
        dur = rng.uniform(4.0, 9.0)
        s0 = int(start * sr)
        seg_n = min(int(dur * sr), n - s0)
        if seg_n <= 0:
            continue
        seg_t = np.arange(seg_n, dtype=np.float32) / sr
        tone = np.sin(2 * np.pi * f * seg_t, dtype=np.float32) * np.exp(-seg_t / (dur / 4)).astype(np.float32)
        tone += 0.3 * np.sin(2 * np.pi * f * 2.01 * seg_t, dtype=np.float32) * np.exp(-seg_t / (dur / 8)).astype(np.float32)
        bells[s0:s0 + seg_n] += tone * 0.35

    # ── noise wash: very quiet filtered noise ──────────────────────
    noise = rng.standard_normal(n).astype(np.float32)
    noise = _moving_average(noise, int(0.8 * sr)) * 6.0
    wash_env = (0.5 + 0.5 * np.sin(2 * np.pi * 0.008 * (np.arange(n, dtype=np.float32) / sr)
                                    + float(rng.uniform(0, 6)))).astype(np.float32)
    noise *= wash_env * 0.05

    # ── master envelope: fade in 6s, fade out 10s ───────────────────
    master_env = np.ones(n, dtype=np.float32)
    fin = min(n, int(6 * sr))
    fout = min(n, int(10 * sr))
    master_env[:fin] = np.linspace(0, 1, fin, dtype=np.float32)
    master_env[-fout:] = np.linspace(1, 0, fout, dtype=np.float32)

    mono = pad * 0.9
    mono += bells
    mono += noise
    mono *= master_env

    peak = float(np.max(np.abs(mono))) or 1.0
    mono *= (0.5 / peak)
    return mono
