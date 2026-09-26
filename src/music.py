"""Copyright-free ambient music, synthesized from scratch with numpy.

A slow seeded pad progression plus sparse bell tones and a whisper of
filtered noise — an original soundscape per episode (seeded by the story
seed), so there is nothing to license and nothing can expire. Generated
as a 44.1 kHz stereo float mix, ready for the final ducking mix.
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
    """O(n) smoothing (lesson from v2: never convolve with 11k-tap kernels)."""
    if k <= 1:
        return x
    cumsum = np.cumsum(np.insert(x, 0, 0.0))
    out = (cumsum[k:] - cumsum[:-k]) / k
    pad = out[:1].repeat(k - 1)
    return np.concatenate([pad, out])


def synth_music(seed: int, duration: float, sr: int = SR) -> np.ndarray:
    """Return stereo float64 mix shaped (n, 2), peak-normalized to ~0.5."""
    rng = np.random.default_rng(seed)
    n = int(duration * sr)
    t = np.arange(n) / sr

    # ── pad: slow chord progression ────────────────────────────────
    chord_len = 18.0  # seconds per chord
    pad = np.zeros(n)
    phases = rng.uniform(0, 2 * np.pi, size=(len(CHORDS), 4))
    i = 0
    pos = 0
    while pos < n:
        chord = CHORDS[i % len(CHORDS)]
        seg_n = min(int(chord_len * sr), n - pos)
        seg_t = np.arange(seg_n) / sr
        seg = np.zeros(seg_n)
        for k, f in enumerate(chord):
            detune = 1.0 + 0.0015 * np.sin(2 * np.pi * (0.03 + 0.01 * k) * seg_t + phases[i % len(CHORDS)][k])
            wave_ = np.sin(2 * np.pi * f * detune * seg_t + phases[i % len(CHORDS)][k])
            wave_ += 0.35 * np.sin(2 * np.pi * f * 2 * detune * seg_t)
            # slow tremolo
            wave_ *= (0.55 + 0.45 * np.sin(2 * np.pi * 0.05 * seg_t + k))
            seg += wave_ / (k + 2.0)
        # crossfade 3s at chord edges
        fade = min(seg_n, int(3.0 * sr))
        if fade > 0:
            env = np.ones(seg_n)
            env[:fade] = np.linspace(0, 1, fade)
            if i > 0:
                seg *= env
            else:
                seg *= np.minimum(1.0, np.linspace(0.2, 1.0, seg_n) ** 0.5)
        pad[pos:pos + seg_n] += seg[: seg_n - pos] if pos + seg_n > n else seg
        pos += max(1, int(chord_len * sr) - int(3.0 * sr))
        i += 1

    pad = _moving_average(pad, int(0.02 * sr))  # soften highs

    # ── bells: sparse decaying tones ───────────────────────────────
    bells = np.zeros(n)
    n_bells = max(4, int(duration / 9.0))
    for _ in range(n_bells):
        start = rng.uniform(0, max(0.1, duration - 4))
        f = BELLS[rng.integers(0, len(BELLS))]
        dur = rng.uniform(4.0, 9.0)
        seg_n = int(dur * sr)
        s0 = int(start * sr)
        seg_n = min(seg_n, n - s0)
        if seg_n <= 0:
            continue
        seg_t = np.arange(seg_n) / sr
        tone = np.sin(2 * np.pi * f * seg_t) * np.exp(-seg_t / (dur / 4))
        tone += 0.3 * np.sin(2 * np.pi * f * 2.01 * seg_t) * np.exp(-seg_t / (dur / 8))
        bells[s0:s0 + seg_n] += tone * 0.35

    # ── noise wash: very quiet filtered noise ──────────────────────
    noise = rng.standard_normal(n).astype(np.float64)
    noise = _moving_average(noise, int(0.8 * sr)) * 6.0  # heavily lowpassed wash
    wash_env = 0.5 + 0.5 * np.sin(2 * np.pi * 0.008 * t + rng.uniform(0, 6))
    noise *= wash_env * 0.05

    # ── master envelope: fade in 6s, fade out 10s ───────────────────
    master_env = np.ones(n)
    fin = min(n, int(6 * sr))
    fout = min(n, int(10 * sr))
    master_env[:fin] = np.linspace(0, 1, fin)
    master_env[-fout:] = np.linspace(1, 0, fout)

    mono = (pad * 0.9 + bells + noise) * master_env

    # ── stereo width: slightly delayed right channel for warmth ─────
    delay = int(0.012 * sr)
    right = np.concatenate([np.zeros(delay), mono[:-delay]])
    stereo = np.stack([mono, right], axis=1)

    peak = np.max(np.abs(stereo)) or 1.0
    stereo = stereo / peak * 0.5
    return stereo
