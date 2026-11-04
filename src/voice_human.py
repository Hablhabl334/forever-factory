"""THE HUMAN EDGE (2026-11-05) — the layer that stops the narration
sounding synthetic.

Owner diagnosis, in their own words: "videos and shorts is flagged as
ai video generated, that's what kills the views". The machine cannot
(and must not) try to dodge YouTube's classifiers — the fix is to make
the narration genuinely FEEL human, so real listeners stay past the
8-second judgment window. Retention is the algorithm; a voice that
breathes is the retention.

What this layer adds, on top of the proven engine ladder (kokoro ->
edge-tts -> piper):

  (a) VARIABLE PAUSES   mood-aware seeded gaps: within-sentence
                        ~120-220 ms, sentence-end ~260-420 ms, and a
                        dramatic ~500-700 ms beat before hook/key
                        lines — instead of one metronomic constant.
  (b) BREATHS           procedurally synthesized soft inhales
                        (band-passed noise, shaped envelope, low
                        level) before ~15-25% of chunks, seeded so
                        they are never rhythmic.
  (c) JOIN JITTER       micro timing variance on every boundary —
                        concatenation is never sample-grid regular.
  (d) ROOM TONE         a very quiet pink-noise bed (~-58..-62 dB)
                        under the whole narration, so pauses sound
                        like a room, not dead digital silence.
  (e) LOUDNESS MICRO-VARIATION  ±1-1.5 dB seeded per chunk.
  (f) PACING VARIATION  per-chunk speed multiplier passed to the
                        engine API (kokoro speed=, edge-tts rate=):
                        hooks slightly faster, reflective lines
                        slower.
  (g) PROSODY PUNCTUATION  strategic ellipses/dashes at the TTS
                        INPUT layer only. The displayed caption text
                        is LOCKED and is never touched.

LAWS:
  * FAIL-OPEN — every public function swallows every exception and
    collapses to the pre-humanizer behavior (identity text, 1.0
    speed, None schedule). A humanizer bug can never kill a voice.
  * DETERMINISTIC — all randomness flows through FactoryRNG, seeded
    from the story hash: the same story renders the same voice
    bytes forever (the five-year durability law).
  * SYNC-SACRED — the schedule only shapes the SILENCE between
    chunks; chunk start/end metadata and the master wav are built
    from the same numbers, so captions can never drift (the polish
    pass's duration law still applies downstream). A breath is only
    ever scheduled inside a gap wide enough to hold it.
  * ZERO NEW DEPENDENCIES — pure numpy + stdlib; numpy is already a
    pinned production dependency.
"""
from __future__ import annotations

import hashlib
import math
from array import array

import numpy as np

from .rng import FactoryRNG

# ── tuning constants (calibrated to sentence_pause = 0.42 s) ─────────
WITHIN_SPAN = (0.29, 0.52)    # × sent_pause -> ~120-220 ms
SENT_SPAN = (0.62, 1.00)      # × sent_pause -> ~260-420 ms
DRAMA_SPAN = (1.19, 1.67)     # × sent_pause -> ~500-700 ms
DRAMA_CHANCE = 0.65           # a hook line earns its beat most, not all, of the time
SCENE_JITTER_SPAN = (0.72, 1.28)   # mirrors the legacy paragraph-pause jitter
BREATH_CHANCE = 0.42          # before ~15-25% of chunks (gated by gap size)
BREATH_MIN_SPACING = 2        # never breathe on (nearly) consecutive chunks
BREATH_SPAN = (0.16, 0.24)    # seconds of soft inhale (shrinks to fit the gap)
BREATH_PEAK_DB = (-44.0, -37.0)
PRE_SPEECH_S = 0.025          # tiny silence between a breath's end and the words
BREATH_MIN_GAP_S = 0.22       # a breath needs a gap that can actually hold it
GAIN_DB_SPAN = (-1.2, 1.2)    # loudness micro-variation
ROOM_DB_SPAN = (-62.0, -58.0)
ROOM_SEED_SALT = "room-tone"
PROSODY_ELLIPSIS_CHANCE = 0.30
PROSODY_DASH_CHANCE = 0.18
CLAMP_PEAK = 32_500           # per-chunk clip guard

_HOOK_CUES = ("what if", "here's", "here is", "the truth", "imagine",
              "picture this", "why do", "why does", "stop ", "nobody",
              "everyone", "never ", "always ")
_REFLECT_CUES = ("sometimes", "maybe", "perhaps", "remember", "years ago",
                 "quietly", "alone", "later", "eventually", "slowly",
                 "one day", "grew up", "old ")

_PINK_SECONDS = 3.7           # room-tone loop length (non-round on purpose)
_PINK_XFADE = 512             # samples of loop-seam crossfade


# ── seeded randomness plumbing ───────────────────────────────────────

def _seed(*parts) -> int:
    """Stable integer seed from any pieces of identity."""
    digest = hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(digest[:12], 16)


def _rng(*parts) -> FactoryRNG:
    return FactoryRNG(_seed(*parts))


# ── gate ─────────────────────────────────────────────────────────────

def enabled(vconf: dict) -> bool:
    """Is the human edge switched on? Fail-open: any surprise = off."""
    try:
        return bool(vconf.get("humanize", False))
    except Exception:
        return False


# ── (f) mood detection & pacing ──────────────────────────────────────

def is_hookish(text: str) -> bool:
    t = " " + str(text).strip().lower()
    if t.rstrip().endswith("?"):
        return True
    return any(cue in t for cue in _HOOK_CUES) or t.lstrip().startswith(("you ", "your "))


def is_reflective(text: str) -> bool:
    t = " " + str(text).strip().lower()
    return any(cue in t for cue in _REFLECT_CUES)


def _mood_speed(text: str, story_hash) -> float:
    """Seeded per-chunk speed multiplier: hooks a touch faster,
    reflective lines a touch slower, neutral barely moves."""
    r = _rng("speed", story_hash, text)
    if is_hookish(text):
        return 1.0 + r.between(0.015, 0.035)
    if is_reflective(text):
        return 1.0 - r.between(0.015, 0.035)
    return 1.0 + r.between(-0.006, 0.006)


def speed_multiplier(vconf: dict, idx: int, text: str) -> float:
    """Public seam for the engines (kokoro speed=, edge rate=).
    Fail-open: any surprise = 1.0 (the pre-humanizer behavior)."""
    try:
        if not enabled(vconf):
            return 1.0
        table = vconf.get("_human_speed")
        if isinstance(table, dict) and idx in table:
            return float(table[idx])
        return _mood_speed(text, vconf.get("_human_story", ""))
    except Exception:
        return 1.0


# ── (g) prosody punctuation — TTS INPUT ONLY ─────────────────────────

def tts_text(vconf: dict, text: str) -> str:
    """Prosody hints for the engine. The caption/displayed text is
    LOCKED — this is applied only to the string handed to the TTS
    engine, per chunk, seeded, and conservatively. Fail-open:
    any surprise = the text unchanged."""
    try:
        if not enabled(vconf):
            return text
        t = str(text)
        words = len(t.split())
        if words <= 3:                 # tiny fragments: keep delivery clean
            return t
        r = _rng("prosody", vconf.get("_human_story", ""), t)
        stripped = t.rstrip()
        if stripped.endswith((".", "!")) and words >= 4:
            if r.chance(PROSODY_ELLIPSIS_CHANCE):
                return t[:-1] + "..."   # trailing fade -> reflective prosody
        elif stripped.endswith(","):
            if r.chance(PROSODY_DASH_CHANCE):
                return t[:-1] + " —"    # hesitation beat mid-thought
        elif not stripped.endswith((".", "!", "?", ",", ";", "—")):
            if r.chance(PROSODY_DASH_CHANCE * 0.7):
                return t + "..."        # clause continues: let it trail
        return t
    except Exception:
        return text


# ── (b) breath synthesis ─────────────────────────────────────────────

def _bandpassed_noise(n: int, sr: int, rng: FactoryRNG,
                      lo_hz: float, hi_hz: float) -> np.ndarray:
    """White -> gaussian band-pass in the FFT domain -> real noise.
    Pure numpy; a few thousand samples, trivially cheap."""
    white = np.array([rng.between(-1.0, 1.0) for _ in range(n)],
                     dtype=np.float64)
    spec = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n, d=1.0 / sr)
    sig = 0.35 * (hi_hz - lo_hz) / 2.0 + 1e-9
    center = (hi_hz + lo_hz) / 2.0
    gain = np.exp(-0.5 * ((freqs - center) / sig) ** 2)
    gain[freqs < lo_hz * 0.5] *= 0.05     # soften the skirt below the band
    gain[freqs > hi_hz * 2.0] *= 0.05
    shaped = np.fft.irfft(spec * gain, n=n)
    peak = float(np.max(np.abs(shaped))) or 1.0
    return shaped / peak


def _breath(sr: int, rng: FactoryRNG) -> np.ndarray:
    """One soft inhale: band-passed noise under an inhale-shaped
    envelope (quick rise, long taper), quiet enough to feel felt,
    not heard as an effect."""
    dur = rng.between(*BREATH_SPAN)
    n = max(64, int(dur * sr))
    air = _bandpassed_noise(n, sr, rng, lo_hz=280.0, hi_hz=2400.0)
    t = np.linspace(0.0, 1.0, n, endpoint=False)
    attack = np.clip(t / 0.22, 0.0, 1.0)          # lungs open fast
    decay = np.power(1.0 - t, 1.35)               # then the taper
    wobble = 1.0 + 0.08 * np.sin(2 * math.pi * rng.between(4.0, 7.0) * t)
    env = attack * decay * wobble
    breath = air * env
    peak_db = rng.between(*BREATH_PEAK_DB)
    # int16-unit space: peak_db is dBFS relative to 32767
    breath *= 10.0 ** (peak_db / 20.0) * 32767.0
    return breath                                  # float, peak ~ -40 dBFS


# ── (d) room tone ────────────────────────────────────────────────────

def _pink_buffer(sr: int, seed: int) -> np.ndarray:
    """One seeded pink-noise loop (1/sqrt(f) tilt), seam-crossfaded so
    it can tile forever without a click. ~3.7 s — generated once per
    narration, O(1) memory."""
    rng = FactoryRNG(seed)
    n = int(_PINK_SECONDS * sr)
    white = np.array([rng.between(-1.0, 1.0) for _ in range(n + _PINK_XFADE)],
                     dtype=np.float64)
    spec = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n + _PINK_XFADE, d=1.0 / sr)
    tilt = 1.0 / np.sqrt(np.maximum(freqs, 20.0))  # pink-ish; kill DC rumble
    pink = np.fft.irfft(spec * tilt, n=n + _PINK_XFADE)
    peak = float(np.max(np.abs(pink))) or 1.0
    pink = pink / peak
    # make the loop seamless: fold the tail into the head
    ramp = np.linspace(0.0, 1.0, _PINK_XFADE)
    pink[:_PINK_XFADE] = (pink[:_PINK_XFADE] * ramp
                          + pink[n:n + _PINK_XFADE] * (1.0 - ramp))
    return pink[:n]


def _room_bed(n: int, sr: int, room_db: float, seed: int) -> np.ndarray:
    """Tile the pink loop to n samples at the target RMS (dBFS)."""
    buf = _pink_buffer(sr, seed)
    reps = int(math.ceil(n / len(buf)))
    bed = np.tile(buf, reps)[:n]
    rms = float(np.sqrt(np.mean(bed ** 2))) or 1.0
    target = 10.0 ** (room_db / 20.0) * 32767.0    # int16-unit space
    return bed * (target / rms)


# ── the schedule (a) + (c) + breath plan + gains + speeds ────────────

def _boundary_kind(prev_text: str) -> str:
    """'sent' when the previous chunk ended a sentence, 'within' when
    the thought continues (comma, dash, or a bare clause split)."""
    t = str(prev_text).rstrip()
    if t.endswith((".", "!", "?")):
        return "sent"
    return "within"


def schedule_for(plan: list[dict], sent_pause: float, scene_pause: float,
                 story_hash, sr: int = 22_050) -> dict | None:
    """Build the full humanized timing/level plan for one narration.
    NEVER raises: any exception returns None and tts.py falls back to
    the proven pipeline untouched.

    Returns {"gap_before": [s, ...] silence BEFORE each chunk (sent +
    scene components merged, a breath lives inside it, j=0 is 0.0),
    "sent_after_last": s (trailing gap legacy totals include),
    "breath_before": {j: float32 array}, "gains": {idx: linear},
    "speeds": {idx: mult}, "room_db": float, "room_seed": int} —
    or None.
    """
    try:
        n = len(plan)
        if n == 0:                        # gate (voice.humanize) is the caller's
            return None
        sp = float(sent_pause)
        if sp <= 0.02:                    # absurd config -> keep it sane
            sp = 0.42
        pp = max(0.05, float(scene_pause))
        rng = _rng("schedule", story_hash)

        gaps = [0.0] * n                  # gap before chunk j (j=0: none)
        breaths: dict[int, np.ndarray] = {}
        last_breath_j = -99
        gains: dict[int, float] = {}
        speeds: dict[int, float] = {}

        for j, p in enumerate(plan):
            idx = p.get("idx", j + 1)
            text = str(p.get("text", ""))
            prev_text = str(plan[j - 1].get("text", "")) if j > 0 else ""

            if j > 0:
                kind = _boundary_kind(prev_text)
                r = _rng("gap", story_hash, j, text)
                lo, hi = WITHIN_SPAN if kind == "within" else SENT_SPAN
                gap = sp * r.between(lo, hi)          # (a)+(c): mood span + join jitter
                # dramatic beat before hook/key lines
                if kind == "sent" and is_hookish(text) and r.chance(DRAMA_CHANCE):
                    lo, hi = DRAMA_SPAN
                    gap = sp * r.between(lo, hi)
                if p.get("scene") is not None \
                        and plan[j - 1].get("scene") != p.get("scene"):
                    # paragraph boundary: the scene pause stacks on top
                    # (mirrors the legacy jitter span exactly)
                    gap += pp * r.between(*SCENE_JITTER_SPAN)
                gaps[j] = gap

            # (b) breath before this chunk — irregular by construction,
            # shrunk to fit the gap it lives in (sync law), never where
            # there is no room for it
            if j > 0 and (j - last_breath_j) > BREATH_MIN_SPACING \
                    and gaps[j] >= BREATH_MIN_GAP_S \
                    and rng.chance(BREATH_CHANCE):
                brng = _rng("breath", story_hash, idx, text)
                b = _breath(sr, brng).astype(np.float32)
                room = int(gaps[j] * sr) - int(PRE_SPEECH_S * sr) - 16
                if room > int(0.12 * sr):
                    breaths[j] = b[:room]
                    last_breath_j = j

            # (e) loudness micro-variation
            grng = _rng("gain", story_hash, idx, text)
            gains[idx] = 10.0 ** (grng.between(*GAIN_DB_SPAN) / 20.0)

            # (f) pacing map for the engines
            speeds[idx] = _mood_speed(text, story_hash)

        # trailing gap after the last chunk (legacy totals include it)
        lr = _rng("gap", story_hash, n, str(plan[-1].get("text", "")) + "#tail")
        sent_after_last = sp * lr.between(*SENT_SPAN)

        return {
            "gap_before": gaps,
            "sent_after_last": sent_after_last,
            "breath_before": breaths,
            "gains": gains,
            "speeds": speeds,
            "room_db": float(rng.between(*ROOM_DB_SPAN)),
            "room_seed": _seed(story_hash, ROOM_SEED_SALT),
        }
    except Exception as exc:
        print(f"  [voice] humanizer unavailable — plain pipeline "
              f"({type(exc).__name__}: {exc})")
        return None


# ── (e) per-chunk gain (applied at master build, cache untouched) ────

def apply_gain(frames: array, gain: float) -> array:
    """Loudness micro-variation on one chunk's int16 frames, with a
    clip guard. Fail-open: any surprise = frames unchanged."""
    try:
        if gain == 1.0:
            return frames
        a = np.frombuffer(frames.tobytes(), dtype=np.int16).astype(np.float32)
        peak = float(np.max(np.abs(a))) if a.size else 0.0
        g = float(gain)
        if peak > 0 and peak * g > CLAMP_PEAK:
            g = CLAMP_PEAK / peak
        out = np.clip(a * g, -32767, 32767).astype(np.int16)
        return array("h", out.tobytes())
    except Exception:
        return frames


# ── master assembly (humanized branch) ───────────────────────────────

def assemble(frames_list: list, gaps: list[float], breaths: dict,
             total: float, sr: int, room_db: float, room_seed: int) -> array:
    """Build the master int16 track when the human edge is on.

    frames_list : one int16 array.array per chunk, plan order
    gaps        : silence (seconds) BEFORE each chunk — gaps[0]=0
    breaths     : {j: float32 array} breath at the very tail of the
                  gap before chunk j (right before the words)
    total       : exact target duration in seconds (sync-sacred)

    Layout per boundary: [quiet: gap - breath - pre-speech] +
    [breath] + [pre-speech] + [chunk]. The trailing silence (last
    sentence gap + paragraph tail) is padded with zeros exactly like
    the legacy builder, then the room-tone bed is mixed under
    everything. Returns int16 array.array('h') of exactly
    int(total*sr) frames.
    """
    need = int(total * sr)
    out = np.zeros(need, dtype=np.float32)
    pos = 0
    for j, frames in enumerate(frames_list):
        if j > 0:
            gap_frames = max(0, int(gaps[j] * sr))
            breath = breaths.get(j)
            b_frames = 0 if breath is None else len(breath)
            quiet = max(0, gap_frames - b_frames - int(PRE_SPEECH_S * sr))
            pos += quiet
            if breath is not None:
                end = min(need, pos + b_frames)
                out[pos:end] += breath[:end - pos]
                pos = end
            pos = min(pos + int(PRE_SPEECH_S * sr), need)
        a = np.frombuffer(frames.tobytes(), dtype=np.int16).astype(np.float32)
        end = min(need, pos + len(a))
        out[pos:end] += a[:end - pos]
        pos = end
    # room tone under everything (d) — pauses become a room, not a void
    out += _room_bed(need, sr, room_db, room_seed)
    return array("h", np.clip(out, -32767, 32767).astype(np.int16).tobytes())
