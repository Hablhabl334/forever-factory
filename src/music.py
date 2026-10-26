"""Copyright-free calm music, synthesized from scratch with numpy.

MOOD-MATCHED BEDS: the day's topic picks the soundscape — healing
topics (breakups, ghosting, moving on) get minor-leaning progressions,
attachment topics get suspended warmth, warm topics (attraction,
communication) get the major glow. The bed matches the script's
emotional register, and it is seeded by the story seed — an original
soundscape per episode: nothing to license, nothing to expire.

Layers (all calm by design):
  * slow detuned pads — the warm floor, 20-second chords
  * soft plucked arpeggios — gentle movement, like a distant piano
  * sparse bell tones — moonlight accents, quieter and rarer
  * a whisper of filtered noise — air

MIX HELPERS (used by the long-video and shorts renderers):
  * normalize_speech() — one loudness standard across engines
  * duck_envelope() — the bed dips under each spoken sentence and
    breathes back in the pauses (voice-following, not a static level)
"""
from __future__ import annotations

import numpy as np

SR = 44_100

# mood -> chord progression (Hz, ~130-350 register, calm voicings)
MOOD_CHORDS: dict[str, list[tuple[float, ...]]] = {
    # warm glow: major-leaning, open, hopeful
    "warm": [
        (174.61, 220.00, 261.63, 329.63),   # Fmaj7
        (130.81, 196.00, 246.94, 293.66),   # Cmaj9
        (146.83, 220.00, 261.63, 349.23),   # Dm9
        (155.56, 233.08, 293.66, 311.13),   # Ebmaj7
        (164.81, 207.65, 246.94, 311.13),   # Em7
        (130.81, 220.00, 261.63, 329.63),   # Cadd9
        (146.83, 185.00, 220.00, 277.18),   # Dsus
        (174.61, 220.00, 261.63, 329.63),   # Fmaj7 (return)
    ],
    # healing: minor-leaning, tender, a little sad — heartbreak topics
    "healing": [
        (110.00, 164.81, 220.00, 246.94),   # Am(add9)
        (174.61, 220.00, 261.63, 293.66),   # F6/9
        (130.81, 196.00, 246.94, 329.63),   # Cmaj7(9)
        (146.83, 220.00, 261.63, 349.23),   # Dm9
        (98.00, 146.83, 196.00, 246.94),    # G(add9), low
        (164.81, 196.00, 246.94, 293.66),   # Em7
        (110.00, 174.61, 220.00, 261.63),   # Am7
        (130.81, 196.00, 261.63, 329.63),   # C (return)
    ],
    # attachment: suspended, neutral warmth — holding, not resolving
    "attachment": [
        (130.81, 196.00, 220.00, 293.66),   # Csus2
        (146.83, 220.00, 246.94, 293.66),   # Dsus2
        (164.81, 196.00, 246.94, 293.66),   # Em7
        (174.61, 220.00, 261.63, 349.23),   # Fmaj7
        (146.83, 220.00, 261.63, 293.66),   # Dm(add)
        (130.81, 220.00, 246.94, 329.63),   # C6
        (164.81, 233.08, 261.63, 311.13),   # Esus
        (130.81, 196.00, 220.00, 293.66),   # Csus2 (return)
    ],
}

# mood -> bell register (healing sits darker, warm sparkles higher)
MOOD_BELLS: dict[str, list[float]] = {
    "warm": [523.25, 587.33, 659.25, 698.46, 783.99, 880.00, 1046.50],
    "healing": [440.00, 493.88, 523.25, 587.33, 659.25, 698.46, 783.99],
    "attachment": [493.88, 554.37, 587.33, 659.25, 739.99, 830.61, 987.77],
}


def _moving_average(x: np.ndarray, k: int) -> np.ndarray:
    """O(n) smoothing (lesson from v2: never convolve with huge kernels)."""
    if k <= 1:
        return x
    cs = np.cumsum(np.insert(x.astype(np.float32), 0, np.float32(0)),
                   dtype=np.float32)
    out = (cs[k:] - cs[:-k]) / k
    pad = np.full(k - 1, out[0], dtype=np.float32)
    return np.concatenate([pad, out])


def _pluck(f: float, dur: float, sr: int) -> np.ndarray:
    """A soft finger-plucked string tone (piano-ish, gentle)."""
    t = np.arange(int(dur * sr), dtype=np.float32) / sr
    tone = np.sin(2 * np.pi * f * t, dtype=np.float32) * np.exp(-t / 0.6)
    tone += 0.32 * np.sin(2 * np.pi * f * 2 * t, dtype=np.float32) \
        * np.exp(-t / 0.30)
    tone += 0.10 * np.sin(2 * np.pi * f * 3.01 * t, dtype=np.float32) \
        * np.exp(-t / 0.16)
    return tone.astype(np.float32)


def synth_music(seed: int, duration: float, sr: int = SR,
                mood: str = "warm", instant_attack: bool = False) -> np.ndarray:
    """Return mono float32 mix, peak-normalized to ~0.5. Calm by design.

    v4 instant_attack=True (shorts): the bed opens at FULL voice from
    frame one — first chord ramp 0.9->1.0 in 0.08 s, master fade-in
    0.06 s, and the first arpeggio pluck lands inside the first half
    second (sound craft: 'enter at the track's strongest bar'). The
    long-video path keeps the gentler 0.5 s settle under the title
    card."""
    rng = np.random.default_rng(seed)
    n = int(duration * sr)

    chords = MOOD_CHORDS.get(mood, MOOD_CHORDS["warm"])
    bells = MOOD_BELLS.get(mood, MOOD_BELLS["warm"])

    # ── pad: slow chord progression, rendered chord by chord ────────
    pad = np.zeros(n, dtype=np.float32)
    chord_len = 20.0
    step = chord_len - 3.0
    i = 0
    pos = 0
    while pos < n:
        chord = chords[i % len(chords)]
        seg_n = min(int(chord_len * sr), n - pos)
        seg_t = (np.arange(seg_n, dtype=np.float32) / sr)
        seg = np.zeros(seg_n, dtype=np.float32)
        for k, f in enumerate(chord):
            ph = float(rng.uniform(0, 2 * np.pi))
            det = 1.0 + 0.0015 * np.sin(2 * np.pi * (0.03 + 0.01 * k) * seg_t + ph)
            w = np.sin(2 * np.pi * f * det * seg_t + ph, dtype=np.float32)
            w += 0.28 * np.sin(2 * np.pi * f * 2 * det * seg_t, dtype=np.float32)
            w *= (0.55 + 0.45 * np.sin(2 * np.pi * 0.05 * seg_t + k, dtype=np.float32))
            seg += w / (k + 2.0)
        # chord edges: 3 s crossfades keep later chord changes smooth
        fade = min(seg_n, int(3.0 * sr))
        env = np.ones(seg_n, dtype=np.float32)
        if i == 0:
            if instant_attack:
                # v4 shorts: full voice inside the first 80 ms
                f0 = min(seg_n, int(0.08 * sr))
                env[:f0] = np.linspace(0.9, 1.0, f0, dtype=np.float32)
            else:
                # 2026-10-21 owner rule: music is audible from second one —
                # the very first chord ramps 0.2 -> 1.0 in 0.6 s (was 3 s)
                f0 = min(seg_n, int(0.6 * sr))
                env[:f0] = np.linspace(0.2, 1.0, f0, dtype=np.float32)
        else:
            env[:fade] = np.linspace(0, 1, fade, dtype=np.float32)
        seg *= env
        pad[pos:pos + seg_n] += seg
        pos += int(step * sr)
        i += 1

    pad = _moving_average(pad, int(0.02 * sr))   # soften highs

    # ── arpeggio: soft plucks following the current chord ───────────
    arp = np.zeros(n, dtype=np.float32)
    chord_edges: list[int] = []
    p = 0
    ci = 0
    while p < n:
        chord_edges.append(p)
        p += int(step * sr)
        ci += 1
    n_plucks = max(3, int(duration / 2.6))
    first_pluck_at = None
    if instant_attack:
        # v4 shorts: one pluck INSIDE the first half second
        first_pluck_at = rng.uniform(0.25, 0.55)
    starts = [first_pluck_at] if first_pluck_at is not None else []
    starts += [rng.uniform(0, max(0.1, duration - 3))
               for _ in range(n_plucks - (1 if first_pluck_at is not None else 0))]
    for start in starts:
        if start is None:
            continue
        s0 = int(start * sr)
        edge = max(e for e in chord_edges if e <= s0) if chord_edges else 0
        chord = chords[(chord_edges.index(edge)) % len(chords)] if edge else chords[0]
        # pick an upper chord tone, one octave up, with a soft touch
        tone_idx = int(rng.integers(1, len(chord)))
        f = float(chord[tone_idx]) * 2.0
        dur = rng.uniform(1.6, 2.6)
        seg_n = min(int(dur * sr), n - s0)
        if seg_n <= 0:
            continue
        arp[s0:s0 + seg_n] += _pluck(f, dur, sr)[:seg_n] * 0.11

    # ── bells: sparse, quiet, decaying ───────────────────────────────
    bells_buf = np.zeros(n, dtype=np.float32)
    n_bells = max(3, int(duration / 12.0))
    for _ in range(n_bells):
        start = rng.uniform(0, max(0.1, duration - 4))
        f = bells[int(rng.integers(0, len(bells)))]
        dur = rng.uniform(4.0, 9.0)
        s0 = int(start * sr)
        seg_n = min(int(dur * sr), n - s0)
        if seg_n <= 0:
            continue
        seg_t = np.arange(seg_n, dtype=np.float32) / sr
        tone = np.sin(2 * np.pi * f * seg_t, dtype=np.float32) \
            * np.exp(-seg_t / (dur / 4)).astype(np.float32)
        tone += 0.3 * np.sin(2 * np.pi * f * 2.01 * seg_t, dtype=np.float32) \
            * np.exp(-seg_t / (dur / 8)).astype(np.float32)
        bells_buf[s0:s0 + seg_n] += tone * 0.22

    # ── noise wash: very quiet filtered air ──────────────────────────
    noise = rng.standard_normal(n).astype(np.float32)
    noise = _moving_average(noise, int(0.8 * sr)) * 6.0
    wash_env = (0.5 + 0.5 * np.sin(2 * np.pi * 0.008
                                   * (np.arange(n, dtype=np.float32) / sr)
                                   + float(rng.uniform(0, 6)))).astype(np.float32)
    noise *= wash_env * 0.04

    # ── master envelope: quick fade in, slow fade out ─────────────────
    # 2026-10-21 fix: was an 8 s fade-in — the bed was effectively
    # silent for the first 3-5 seconds, which read as "the music
    # starts late". 0.5 s from a soft 0.35 floor has the bed fully
    # up well inside second one.
    master_env = np.ones(n, dtype=np.float32)
    if instant_attack:
        fin = min(n, int(0.06 * sr))
        master_env[:fin] = np.linspace(0.85, 1.0, fin, dtype=np.float32)
    else:
        fin = min(n, int(0.5 * sr))
        master_env[:fin] = np.linspace(0.35, 1.0, fin, dtype=np.float32)
    fout = min(n, int(10 * sr))
    master_env[-fout:] = np.linspace(1, 0, fout, dtype=np.float32)

    mono = pad * 0.85
    mono += arp
    mono += bells_buf
    mono += noise
    mono *= master_env

    # v4 level law: RMS-normalize FIRST (a globally-loud pluck or bell
    # must not bury the sustained pad — the bed's job is to be FELT in
    # the first second), then peak-cap at 0.5. Before, peak-only
    # normalization made the pad level swing ~10 dB between seeds:
    # some episodes opened near-silent while the voice was still
    # warming up — exactly the 'music starts late' read we fixed once
    # already on 2026-10-21.
    rms = float(np.sqrt(np.mean(np.square(mono.astype(np.float64)))))
    if rms > 1e-6:
        mono *= np.float32(0.10 / rms)     # consistent bed floor, every seed
    peak = float(np.max(np.abs(mono))) or 1.0
    if peak > 0.5:
        mono *= np.float32(0.5 / peak)
    return mono


# ── v4 SFX accents (sound craft: 'few and exact — every effect has a
# cause on screen'). Three causes, three sounds, rotated by seed so no
# two cards share the identical take: the hook landing (pop), the term
# reveal (riser into impact — once per short), and the CTA (soft pop).
# Every hit sits 3-6 dB over the ducked bed; nothing synthesized as a
# chime or a ding (banned: they read as templates).


def synth_sfx(kind: str, seed: int, sr: int = SR) -> np.ndarray:
    """Return float32 mono SFX peak-normalized to ~1.0 (the mixer
    scales it). kind: 'pop' (0.16 s landing accent) or 'riser'
    (~0.75 s sweep whose thump lands at the END — start it 0.75 s
    before the beat it accents)."""
    rng = np.random.default_rng(seed)
    if kind == "pop":
        n = int(0.16 * sr)
        t = np.arange(n, dtype=np.float32) / sr
        f0 = float(rng.uniform(170.0, 200.0))
        thump = np.sin(2 * np.pi * (f0 - 80.0 * t) * t, dtype=np.float32) \
            * np.exp(-t / 0.045)
        click = (rng.standard_normal(n).astype(np.float32)
                 * np.exp(-t / 0.008)) * 0.35
        out = thump + click
    elif kind == "riser":
        sweep_n = int(0.62 * sr)
        t = np.arange(sweep_n, dtype=np.float32) / sr
        noise = rng.standard_normal(sweep_n).astype(np.float32)
        noise = _moving_average(noise, max(2, int(0.012 * sr)))
        prog = (t / max(t[-1], 1e-6)) ** 2.2            # accelerating swell
        sweep = noise * prog * 1.6
        thump_n = int(0.13 * sr)
        t2 = np.arange(thump_n, dtype=np.float32) / sr
        fth = float(rng.uniform(52.0, 62.0))
        thump = np.sin(2 * np.pi * fth * t2, dtype=np.float32) \
            * np.exp(-t2 / 0.050)
        out = np.concatenate([sweep, thump])
    else:
        return np.zeros(8, dtype=np.float32)
    peak = float(np.max(np.abs(out))) or 1.0
    return (out / peak).astype(np.float32)


# ── mix helpers shared by the long and shorts renderers ─────────────

def normalize_speech(x: np.ndarray, target_rms: float = 0.085) -> np.ndarray:
    """One loudness standard for the narration, whatever the engine
    (neural and offline voices ship at different levels). Peak-safe."""
    if x.size == 0:
        return x.astype(np.float32)
    rms = float(np.sqrt(np.mean(np.square(x.astype(np.float64)))))
    if rms < 1e-6:
        return x.astype(np.float32)
    out = (x * (target_rms / rms)).astype(np.float32)
    peak = float(np.max(np.abs(out)))
    if peak > 0.92:
        out *= np.float32(0.92 / peak)
    return out


def duck_envelope(voice: np.ndarray, n: int, sr: int,
                  depth: float = 0.55) -> np.ndarray:
    """Envelope in [1 - depth, 1]: the music bed dips while a sentence
    is being spoken and breathes back in the pauses. Fast attack,
    slow release — like a gentle hand on the fader."""
    env = np.zeros(n, dtype=np.float32)
    m = min(n, voice.size)
    env[:m] = np.abs(voice[:m])
    fast = _moving_average(env, max(2, int(0.05 * sr)))
    slow = _moving_average(fast, max(2, int(0.30 * sr)))   # release
    # speech is normalized to ~0.085 RMS -> mean |x| ~0.055
    norm = np.clip(slow * (1.0 / 0.05), 0.0, 1.0)
    duck = (1.0 - depth * norm).astype(np.float32)
    return duck
