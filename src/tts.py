"""Narration — a voice that sounds like a person, not a machine.

PRIMARY ENGINE: Kokoro-82M (vendored, assets/voice_kokoro/) — a
local, offline neural TTS that runs on CPU at ~2x realtime. No API,
no key, no account, no network — the flagship open voice (af_heart)
is genuinely human-class (TTS-Arena's top open model; MIT license).
Because the model files live inside this repo, the voice can never
go dark: the machine and its voice share one fate.

BACKUP ENGINE: edge-tts — the neural service behind the Edge
browser's read-aloud (also free, no key). Used if the Kokoro files
are ever missing/broken so quality stays neural.

LAST-RESORT ENGINE: the vendored offline Piper voice (assets/voice/).
Landing here is a VISIBLE quality event (NEURAL_FALLBACK -> the
orchestrator retries the day; the workflow files a Voice-degraded
Issue). The channel never goes silently robotic again (2026-10-13
lesson).

Human-prosody layer (all engines): per-chunk rate jitter +
per-sentence pause jitter, deterministic from the text — every
sentence breathes a little differently, no metronome cadence.

All engines synthesize chunk by chunk (one sentence, or a comma-
split piece of a long one), so the audio duration of every caption
is EXACT — captions can never drift out of sync. Each chunk is
cached as work/chunks/chunk_NNN.wav, so runs are resumable.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import subprocess
import time
import wave
from pathlib import Path

import array

from .config import cfg, path as repo_path

SR = 22_050


class EdgeSynthError(RuntimeError):
    """The neural endpoint failed after retries (caller falls back)."""


class KokoroSynthError(RuntimeError):
    """The local Kokoro engine failed (caller falls back to edge-tts)."""


# Voice-quality telemetry (2026-10-13 lesson): the neural endpoint can
# refuse requests from a runner's IP range (Microsoft throttles
# datacenter ranges intermittently), and the machine used to treat the
# offline fallback as a perfectly successful day — two days of robotic
# narration shipped before anyone noticed. The flag below travels with
# the process; the orchestrator turns it into retries and alerts.
NEURAL_FALLBACK = False            # True once a narration lands on Piper
_EDGE_DECISION: str | None = None  # process-wide: chosen voice, or "DOWN"
_EDGE_ALT_VOICES = ("en-US-AriaNeural", "en-US-GuyNeural", "en-GB-SoniaNeural")


# abbreviation guard: "11 p.m." must never split mid-sentence
# (2026-10-21: produced a 1-second "The 11 p.m." caption card)
_ABBR = re.compile(r"\b(a\.m\.|p\.m\.|Mr\.|Mrs\.|Ms\.|Dr\.|St\.)",
                    re.IGNORECASE)
_DOT_MASK = "·"      # middle dot — never appears in the content banks


def split_chunks(text: str, max_words: int = 12,
                 at_dashes: bool = False) -> list[str]:
    """Split narration into caption chunks: sentences, then long ones at
    commas, then any still-overlong comma-free clause at a word boundary
    (shorts use max_words=9 — a hook like 'The person who chases and
    the person who retreats always find each other' has no comma, but
    the karaoke cards still need the faster rhythm).

    2026-10-21: abbreviated times/titles (a.m./p.m.) never break a
    sentence, and at_dashes=True (Shorts) breaks sentences at em-dashes
    so every beat gets its own caption + hesitation pause — the way a
    person actually breathes mid-line. Longs keep the original chunks.
    """
    text = re.sub(r"\s+", " ", text).strip()
    masked = _ABBR.sub(lambda m: m.group(1).replace(".", _DOT_MASK), text)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", masked)
                 if s.strip()]
    if at_dashes:
        broken: list[str] = []
        for sent in sentences:
            if " — " in sent:
                pieces = sent.split(" — ")
                for i, piece in enumerate(pieces):
                    piece = piece.strip()
                    if not piece:
                        continue
                    if i < len(pieces) - 1:
                        piece += " —"
                    broken.append(piece)
            else:
                broken.append(sent)
        sentences = broken
    sentences = [s.replace(_DOT_MASK, ".") for s in sentences]
    chunks: list[str] = []
    for sent in sentences:
        words = sent.split()
        if len(words) <= max_words:
            chunks.append(sent)
            continue
        # split at commas / em-dashes, grouping to <= max_words
        parts = re.split(r"(?<=[,;—])\s+", sent)
        cur: list[str] = []
        sent_chunks: list[str] = []
        for part in parts:
            pw = part.split()
            if len(pw) > max_words:
                # a comma-free clause longer than the budget: flush the
                # group, then split it at word boundaries so every
                # caption card stays small. 2026-10-21 guards: a
                # trailing em-dash token never strands alone, and a
                # tiny tail piece merges back (never a 1-2 word
                # caption, never a term split across cards).
                if cur:
                    sent_chunks.append(" ".join(cur))
                    cur = []
                tail_dash = ""
                if pw and pw[-1] == "—":
                    tail_dash = pw.pop()
                sub = [" ".join(pw[k:k + max_words])
                       for k in range(0, len(pw), max_words)]
                if len(sub) > 1 and len(sub[-1].split()) <= 3:
                    merged = sub[-2] + " " + sub[-1]
                    sub = sub[:-2] + [merged]
                if tail_dash:
                    sub[-1] += " " + tail_dash
                sent_chunks.extend(sub)
            elif len(cur) + len(pw) <= max_words or not cur:
                cur.extend(pw)
            else:
                sent_chunks.append(" ".join(cur))
                cur = pw
        if cur:
            sent_chunks.append(" ".join(cur))
        # 2026-10-21: a trailing 1-3 word remainder ("up,",
        # "reinforcement.") is a caption card nobody wants — merge it
        # back into its predecessor even if that runs slightly long
        if len(sent_chunks) >= 2 and len(sent_chunks[-1].split()) <= 3:
            last = sent_chunks.pop()
            sent_chunks[-1] += " " + last
        chunks.extend(c for c in sent_chunks if c)
    return [c for c in chunks if c]


# ── human prosody helpers ────────────────────────────────────────────

def _jitter_pct(text: str, jitter: float) -> float:
    """Deterministic per-chunk rate offset in (-jitter, +jitter) percent.
    Seeded by the text itself: same text, same jitter — cache-friendly."""
    digest = hashlib.md5(text.encode()).hexdigest()
    val = (int(digest[:8], 16) % 10_000) / 10_000.0     # [0, 1)
    return (val * 2.0 - 1.0) * jitter


def _pause_for(text: str, idx: int, base: float) -> float:
    """Deterministic per-sentence pause: humans never pause like a
    metronome — every breath is a little different."""
    digest = hashlib.md5(f"{idx}:{text}".encode()).hexdigest()
    val = (int(digest[:8], 16) % 10_000) / 10_000.0     # [0, 1)
    return base * (0.72 + 0.56 * val)


def _parse_pct(s: str) -> float:
    return float(str(s).replace("%", "").strip() or 0)


def _fmt_pct(v: float) -> str:
    return f"{int(round(v)):+d}%"


def _parse_hz(s: str) -> float:
    m = re.match(r"([+-]?\d+(?:\.\d+)?)\s*Hz", str(s).strip())
    return float(m.group(1)) if m else 0.0


def _fmt_hz(v: float) -> str:
    v = int(round(v))
    return f"{v:+d}Hz" if v else "+0Hz"


def _wav_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", str(path)],
        capture_output=True, text=True, timeout=60)
    return float(json.loads(out.stdout)["format"]["duration"])


def _polish_narration(wav_path: Path) -> None:
    """Broadcast-polish pass: lift the rumble, add presence, gently
    even out the dynamics. Every filter is strictly gain-only — the
    duration is verified unchanged (caption sync is sacred). Best
    effort: on any failure the raw narration is kept."""
    tmp = wav_path.with_suffix(".polish.wav")
    af = (
        "highpass=f=85,lowpass=f=11500,"
        "equalizer=f=200:t=q:w=1:g=-1.5,"
        "equalizer=f=3200:t=q:w=1.4:g=2.5,"
        "acompressor=threshold=-20dB:ratio=2:attack=10:release=180:makeup=1.5"
    )
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
         "-i", str(wav_path), "-af", af,
         "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(tmp)],
        stdin=subprocess.DEVNULL, capture_output=True, timeout=300)
    if proc.returncode != 0:
        tmp.unlink(missing_ok=True)
        return
    try:
        d0, d1 = _wav_duration(wav_path), _wav_duration(tmp)
        if abs(d1 - d0) > 0.02:          # paranoid: never drift captions
            tmp.unlink(missing_ok=True)
            return
        tmp.replace(wav_path)
        print("  [voice] polished: presence EQ + gentle compression")
    except (json.JSONDecodeError, subprocess.TimeoutExpired, KeyError, ValueError):
        tmp.unlink(missing_ok=True)


# ── primary engine (Kokoro-82M, local) ───────────────────────────────

def kokoro_model_paths(vconf: dict) -> tuple[Path, Path]:
    """Vendored model locations (config-overridable)."""
    m = Path(vconf.get("kokoro_model") or
             repo_path("assets", "voice_kokoro", "kokoro-v1.0.int8.onnx"))
    v = Path(vconf.get("kokoro_voices") or
             repo_path("assets", "voice_kokoro", "voices-v1.0.bin"))
    return m, v


def kokoro_available(vconf: dict) -> bool:
    """Are the vendored Kokoro files present (and non-empty)?"""
    m, v = kokoro_model_paths(vconf)
    return m.exists() and m.stat().st_size > 10_000_000 \
        and v.exists() and v.stat().st_size > 1_000_000


def _kokoro_speed_for(vconf: dict, rate_pct: str | None) -> float:
    """Config base speed (or an edge-style rate override) -> kokoro
    speed factor. edge '-3%' (slower) maps to kokoro speed 0.97."""
    if rate_pct is not None:
        return max(0.5, min(2.0, 1.0 + _parse_pct(rate_pct) / 100.0))
    base = float(vconf.get("kokoro_speed", 0.96))
    return max(0.5, min(2.0, base))


def _f32_to_wav_22050(samples, sr: int, wav: Path) -> None:
    """float32 samples (any rate) -> 22.05 kHz 16-bit mono wav, via
    ffmpeg (one short process per chunk, ~50 ms — resumable chunks
    stay self-contained)."""
    import numpy as np
    import tempfile
    pcm = (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tmp = Path(tf.name)
    try:
        with wave.open(str(tmp), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(pcm.tobytes())
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
             "-y", "-i", str(tmp), "-ar", str(SR), "-ac", "1",
             "-c:a", "pcm_s16le", str(wav)],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=120)
        if proc.returncode != 0:
            raise KokoroSynthError(
                f"kokoro chunk resample failed: {proc.stderr.decode()[-300:]}")
    finally:
        tmp.unlink(missing_ok=True)


def _kokoro_synth_all(items: list[tuple[int, str]], chunks_dir: Path,
                      vconf: dict, rate_pct: str | None = None) -> None:
    """Synthesize (idx, text) chunks with the local neural voice.
    Per-chunk speed jitter keeps the cadence human. Loads the model
    once per call (~1 s) — chunks are small, so this is fast."""
    from kokoro_onnx import Kokoro

    m, v = kokoro_model_paths(vconf)
    kokoro = Kokoro(str(m), str(v))
    voice = str(vconf.get("kokoro_voice", "af_heart"))
    base_speed = _kokoro_speed_for(vconf, rate_pct)
    jitter = float(vconf.get("kokoro_jitter", 4.5))

    for idx, text in items:
        # question intonation (2026-10-21): real voices lean a touch
        # slower on questions — flat delivery on "why do they do that?"
        # was one of the last robotic tells. Kokoro has no pitch knob,
        # so questions get a gentle speed drop instead.
        speed = base_speed * (1.0 + _jitter_pct(text, jitter) / 100.0)
        if text.rstrip().endswith("?"):
            speed *= 0.97
        speed = max(0.5, min(2.0, speed))
        audio, sr = kokoro.create(
            text, voice=voice, speed=round(speed, 4), lang="en-us")
        _f32_to_wav_22050(audio, sr, chunks_dir / f"chunk_{idx:03d}.wav")


def _kokoro_probe(vconf: dict) -> bool:
    """One tiny local synthesis decides the engine — no network."""
    try:
        probe_dir = repo_path("work") / "_kokoro_probe"
        probe_dir.mkdir(parents=True, exist_ok=True)
        _kokoro_synth_all([(999_998, "Ready.")], probe_dir, vconf)
        (probe_dir / "chunk_999998.wav").unlink(missing_ok=True)
        return True
    except Exception as exc:
        print(f"  [voice] local Kokoro probe failed: {exc}")
        return False


# ── neural engine (edge-tts) ─────────────────────────────────────────

def _mp3_to_wav(mp3: Path, wav: Path) -> None:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
         "-i", str(mp3), "-ar", str(SR), "-ac", "1", str(wav)],
        stdin=subprocess.DEVNULL, capture_output=True, timeout=120,
    )
    if proc.returncode != 0:
        raise EdgeSynthError(
            f"mp3->wav failed: {proc.stderr.decode()[-300:]}")
    mp3.unlink(missing_ok=True)


def _edge_synth_all(items: list[tuple[int, str]], chunks_dir: Path,
                    vconf: dict) -> None:
    """Synthesize (idx, text) items with the neural voice, concurrent.
    Each sentence gets its own subtle rate AND pitch offset — humans
    never say two sentences on exactly the same note."""
    import edge_tts

    voice = vconf.get("edge_name", "en-US-AriaNeural")
    base_rate = _parse_pct(vconf.get("edge_rate", "-6%"))
    jitter = float(vconf.get("edge_jitter", 3.0))
    base_pitch = _parse_hz(vconf.get("edge_pitch", "-1Hz"))
    pitch_jitter = float(vconf.get("edge_pitch_jitter", 3.0))

    async def one(idx: int, text: str) -> None:
        mp3 = chunks_dir / f"edge_{idx:03d}.mp3"
        wav = chunks_dir / f"chunk_{idx:03d}.wav"
        # question intonation (2026-10-21): lift the pitch and slow a
        # touch on questions — flat questions were a robotic tell
        is_question = text.rstrip().endswith("?")
        rate = _fmt_pct(base_rate + _jitter_pct(text, jitter)
                        + (-2.0 if is_question else 0.0))
        pitch = _fmt_hz(base_pitch + _jitter_pct(text, pitch_jitter)
                        + (1.0 if is_question else 0.0))
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
                await asyncio.wait_for(com.save(str(mp3)), timeout=60)
                _mp3_to_wav(mp3, wav)
                return
            except asyncio.CancelledError:
                raise
            except Exception as exc:          # network / timeout / 403
                last_err = exc
                await asyncio.sleep(0.8 * (attempt + 1))
        raise EdgeSynthError(
            f"neural synth failed for chunk {idx} after 3 tries: {last_err}")

    async def runner() -> None:
        sem = asyncio.Semaphore(4)

        async def guarded(idx: int, text: str) -> None:
            async with sem:
                await one(idx, text)

        await asyncio.gather(*(guarded(i, t) for i, t in items))

    asyncio.run(runner())


def _edge_probe_once(vconf: dict, chunks_dir: Path) -> bool:
    """ONE fast live request (single try, 15 s cap): does the endpoint
    answer for this voice right now? Cheap enough to call many times —
    _edge_pick_voice() is the one that decides."""
    import edge_tts

    voice = vconf.get("edge_name", "en-US-AriaNeural")
    mp3 = chunks_dir / "probe.mp3"
    try:
        async def _save() -> None:
            com = edge_tts.Communicate("Ready.", voice)
            await asyncio.wait_for(com.save(str(mp3)), timeout=15)

        asyncio.run(_save())
        return mp3.exists() and mp3.stat().st_size >= 200
    except Exception:            # 403 / timeout / DNS — one bad moment, not a verdict
        return False
    finally:
        mp3.unlink(missing_ok=True)


def _edge_pick_voice(vconf: dict, chunks_dir: Path,
                     delays: tuple[float, ...] = (0.0, 10.0, 25.0)) -> str | None:
    """Choose a WORKING neural voice: the configured voice first, then
    known-good alternates, across a few patient rounds.

    2026-10-13 lesson: the old code asked the endpoint ONCE and let a
    single bad minute (IP throttle, service blip, voice retirement)
    doom the whole day's voice. The picker retries across rounds and
    voices before conceding, and its decision is cached process-wide:
    every narration of one cycle shares ONE voice — the day never
    switches mid-cycle, and the ladder costs its patience only once.

    Returns the voice name to use, or None when the endpoint itself is
    unreachable — the caller then falls back to offline Piper.
    """
    global _EDGE_DECISION
    if _EDGE_DECISION is not None:
        return None if _EDGE_DECISION == "DOWN" else _EDGE_DECISION

    primary = str(vconf.get("edge_name", "en-US-AriaNeural"))
    candidates: list[str] = []
    for v in (primary, *(vconf.get("edge_fallback_voices") or _EDGE_ALT_VOICES)):
        v = str(v)
        if v and v not in candidates:
            candidates.append(v)
    for rnd, delay in enumerate(delays):
        if delay:
            time.sleep(delay)
        for voice in candidates:
            if _edge_probe_once({**vconf, "edge_name": voice}, chunks_dir):
                _EDGE_DECISION = voice
                return voice
        print(f"  [voice] neural probe round {rnd + 1}/{len(delays)} failed "
              f"— endpoint throttled or unreachable")
    _EDGE_DECISION = "DOWN"
    return None


# ── offline engine (Piper) ───────────────────────────────────────────

def _synth_chunk_piper(voice, text: str, length_scale: float) -> array.array:
    from piper import SynthesisConfig
    cfg_ = SynthesisConfig(length_scale=length_scale)
    frames = array.array("h")
    for piece in voice.synthesize(text, syn_config=cfg_):
        frames.extend(piece.audio_int16_array)
    return frames


def write_wav(path: Path, frames: array.array) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(frames.tobytes())


def read_wav(path: Path) -> array.array:
    with wave.open(str(path), "rb") as w:
        raw = w.readframes(w.getnframes())
    frames = array.array("h")
    frames.frombytes(raw)
    return frames


def _wipe_chunks(chunks_dir: Path) -> None:
    for f in chunks_dir.glob("chunk_*.wav"):
        f.unlink()
    for f in chunks_dir.glob("edge_*.mp3"):
        f.unlink()


def narrate(story: dict, work_dir: Path, model_path: Path | None = None,
            sent_pause: float | None = None,
            scene_pause: float | None = None,
            rate_pct: str | None = None,
            chunk_words: int | None = None,
            at_dashes: bool = False) -> dict:
    """Synthesize the whole narration. Idempotent & resumable:
    each chunk is cached as work/chunks/chunk_NNN.wav; a completed run
    writes work/narration.json which short-circuits re-runs.

    Optional pause overrides (shorts use tighter pacing), an optional
    neural rate override (shorts run slightly brisker), an optional
    caption-chunk width (shorts use smaller chunks = faster cards),
    and at_dashes=True (shorts) for em-dash hesitation beats.

    Returns {"chunks": [...], "scene_durations": [...], "total": float,
             "engine": "kokoro"|"edge"|"piper"}.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    meta_file = work_dir / "narration.json"
    vconf = dict(cfg()["voice"])
    if rate_pct is not None:
        vconf["edge_rate"] = rate_pct
    engine_conf = str(vconf.get("engine", "auto")).lower()
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
            if meta.get("story_hash") == story.get("hash"):
                # a resumed robotic narration is still a visible quality
                # event — the flag must survive the cache short-circuit
                if meta.get("engine") == "piper" and engine_conf != "piper":
                    global NEURAL_FALLBACK
                    NEURAL_FALLBACK = True
                return meta
            # story changed underneath (audit-gate rerun) — stale cache
            chunks_dir = work_dir / "chunks"
            if chunks_dir.exists():
                for f in chunks_dir.glob("chunk_*.wav"):
                    f.unlink()
        except json.JSONDecodeError:
            pass

    length_scale = float(vconf.get("length_scale", 1.45))
    sent_pause = float(vconf.get("sentence_pause", 0.4)) if sent_pause is None else sent_pause
    scene_pause = float(vconf.get("paragraph_pause", 0.7)) if scene_pause is None else scene_pause

    model_path = Path(model_path or vconf.get(
        "model", repo_path("assets", "voice", "en_US-lessac-medium.onnx")))
    if not Path(model_path).exists():
        raise FileNotFoundError(f"Piper voice model missing: {model_path}")

    chunks_dir = work_dir / "chunks"
    chunks_dir.mkdir(exist_ok=True)

    # plan: every caption chunk in order
    plan: list[dict] = []
    idx = 0
    cw = int(chunk_words) if chunk_words else 12
    for scene in story["scenes"]:
        for text in split_chunks(scene["narration"], max_words=cw,
                                 at_dashes=at_dashes):
            idx += 1
            plan.append({"scene": scene["n"], "text": text, "idx": idx})

    # engine choice: kokoro (local) -> edge (network) -> piper (last
    # resort, loud). 2026-10-13 lesson: one failed probe used to
    # convert a single bad minute into a whole robotic day. The
    # patient picker retries across rounds AND voices, and its
    # decision is cached for the process so every narration of the
    # cycle shares one consistent voice.
    engine = "piper" if engine_conf == "piper" else "edge"
    if engine == "edge" and engine_conf != "edge" \
            and kokoro_available(vconf):
        engine = "kokoro"
    if engine == "kokoro" and not _kokoro_probe(vconf):
        print("  [voice] local Kokoro unusable — trying edge-tts")
        engine = "edge"
    if engine == "edge":
        voice_ok = _edge_pick_voice(vconf, chunks_dir)
        if voice_ok is None:
            print("  [voice] neural endpoint unreachable — using offline Piper")
            NEURAL_FALLBACK = True
            engine = "piper"
        elif voice_ok != str(vconf.get("edge_name", "en-US-AriaNeural")):
            print(f"  [voice] {vconf.get('edge_name')} unavailable — "
                  f"narrating with {voice_ok}")
            vconf["edge_name"] = voice_ok

    # engine consistency: never mix two voices in one narration
    marker = chunks_dir / "engine.txt"
    cached_engine = marker.read_text().strip() if marker.exists() else engine
    if cached_engine != engine:
        _wipe_chunks(chunks_dir)
    marker.write_text(engine)

    # synthesize missing chunks
    missing = [p for p in plan
               if not (chunks_dir / f"chunk_{p['idx']:03d}.wav").exists()]
    if missing:
        if engine == "kokoro":
            try:
                _kokoro_synth_all([(p["idx"], p["text"]) for p in missing],
                                  chunks_dir, vconf, rate_pct=rate_pct)
                print(f"  [voice] local neural narration: {len(missing)} chunks "
                      f"(Kokoro {vconf.get('kokoro_voice', 'af_heart')})")
            except KokoroSynthError:
                print("  [voice] Kokoro failed mid-run — falling back to "
                      "edge-tts (whole narration, one consistent voice)")
                engine = "edge"
                _wipe_chunks(chunks_dir)
                marker.write_text(engine)
                missing = plan
        if engine == "edge":
            try:
                _edge_synth_all([(p["idx"], p["text"]) for p in missing],
                                chunks_dir, vconf)
                print(f"  [voice] neural narration: {len(missing)} chunks "
                      f"({vconf.get('edge_name', 'en-US-AriaNeural')})")
            except EdgeSynthError:
                if engine_conf != "piper":
                    print("  [voice] neural synth failed mid-run — "
                          "falling back to offline Piper (whole narration)")
                    NEURAL_FALLBACK = True
                    engine = "piper"
                    _wipe_chunks(chunks_dir)
                    marker.write_text(engine)
                    missing = plan  # everything again, one consistent voice
                else:
                    raise
        if engine == "piper":
            from piper import PiperVoice
            voice = PiperVoice.load(str(model_path))
            for p in missing:
                frames = _synth_chunk_piper(voice, p["text"], length_scale)
                write_wav(chunks_dir / f"chunk_{p['idx']:03d}.wav", frames)
            print(f"  [voice] offline Piper narration: {len(missing)} chunks")

    # assemble timing metadata from the exact chunk durations
    chunks_meta: list[dict] = []
    scene_durations: list[float] = []
    t = 0.0
    last_scene = plan[0]["scene"] if plan else 1
    scene_start = 0.0
    for p in plan:
        frames = read_wav(chunks_dir / f"chunk_{p['idx']:03d}.wav")
        dur = len(frames) / SR
        if p["scene"] != last_scene:
            t += _pause_for(p["text"], -p["scene"], scene_pause)
            scene_durations.append(round(t - scene_start, 3))
            scene_start = t
            last_scene = p["scene"]
        chunks_meta.append({
            "scene": p["scene"],
            "text": p["text"],
            "start": round(t, 3),
            "end": round(t + dur, 3),
        })
        t += dur + _pause_for(p["text"], p["idx"], sent_pause)
    if plan:
        t += scene_pause
        scene_durations.append(round(t - scene_start, 3))

    total = t

    # master narration wav: concat cached chunks with pauses
    master = array.array("h")
    pause_frames = lambda secs: array.array("h", b"\x00\x00" * int(secs * SR))
    last_scene = plan[0]["scene"] if plan else 1
    for p in plan:
        master.extend(read_wav(chunks_dir / f"chunk_{p['idx']:03d}.wav"))
        master.extend(pause_frames(_pause_for(p["text"], p["idx"], sent_pause)))
        if p["scene"] != last_scene:
            master.extend(
                pause_frames(_pause_for(p["text"], -p["scene"], scene_pause)))
            last_scene = p["scene"]

    # trim/pad to exact total length
    need = int(total * SR)
    if len(master) > need:
        master = master[:need]
    elif len(master) < need:
        master.extend(array.array("h", b"\x00\x00" * (need - len(master))))
    write_wav(work_dir / "narration.wav", master)
    _polish_narration(work_dir / "narration.wav")

    result = {
        "story_hash": story.get("hash"),
        "chunks": chunks_meta,
        "scene_durations": scene_durations,
        "total": round(total, 3),
        "sample_rate": SR,
        "engine": engine,
    }
    meta_file.write_text(json.dumps(result, indent=1))
    return result
