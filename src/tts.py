"""Narration — a voice that sounds like a person, not a machine.

PRIMARY ENGINE: edge-tts — the neural TTS service behind the Edge
browser's read-aloud feature. No API key, no account, no cost. The
default voice (en-US-AriaNeural) is a warm, natural human register —
conversational pacing, real prosody, nothing robotic about it.

Two naturalness tricks on top of the neural voice:
  * per-chunk rate jitter (deterministic, seeded by the text hash):
    every sentence gets a slightly different pace, the way humans
    speak — no metronome cadence;
  * the config's calm base rate (-6%) keeps the delivery intimate.

FALLBACK ENGINE: the vendored offline Piper voice (assets/voice/).
If the neural endpoint is ever unreachable — network hiccup, service
retirement, a runner in a blocked region — the factory automatically
switches mid-run, re-renders the narration with Piper, and the day
still ships. The channel never goes silent because one service did.

Both engines synthesize chunk by chunk (one sentence, or a comma-
split piece of a long one), so the audio duration of every caption
is EXACT — captions can never drift out of sync. Soft pauses are
inserted between sentences and scenes. Each chunk is cached as
work/chunks/chunk_NNN.wav, so runs are resumable.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import subprocess
import wave
from pathlib import Path

import array

from .config import cfg, path as repo_path

SR = 22_050


class EdgeSynthError(RuntimeError):
    """The neural endpoint failed after retries (caller falls back)."""


def split_chunks(text: str, max_words: int = 12) -> list[str]:
    """Split narration into caption chunks: sentences, then long ones at commas."""
    text = re.sub(r"\s+", " ", text).strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    chunks: list[str] = []
    for sent in sentences:
        words = sent.split()
        if len(words) <= max_words:
            chunks.append(sent)
            continue
        # split at commas / em-dashes, grouping to <= max_words
        parts = re.split(r"(?<=[,;—])\s+", sent)
        cur: list[str] = []
        for part in parts:
            pw = part.split()
            if len(cur) + len(pw) <= max_words or not cur:
                cur.extend(pw)
            else:
                chunks.append(" ".join(cur))
                cur = pw
        if cur:
            chunks.append(" ".join(cur))
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
        rate = _fmt_pct(base_rate + _jitter_pct(text, jitter))
        pitch = _fmt_hz(base_pitch + _jitter_pct(text, pitch_jitter))
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


def _edge_probe(vconf: dict, chunks_dir: Path) -> bool:
    """One tiny live request decides the engine — never bet the day."""
    try:
        _edge_synth_all([(999_999, "Ready.")], chunks_dir, vconf)
        (chunks_dir / "chunk_999999.wav").unlink(missing_ok=True)
        return True
    except EdgeSynthError:
        return False


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
            rate_pct: str | None = None) -> dict:
    """Synthesize the whole narration. Idempotent & resumable:
    each chunk is cached as work/chunks/chunk_NNN.wav; a completed run
    writes work/narration.json which short-circuits re-runs.

    Optional pause overrides (shorts use tighter pacing) and an
    optional neural rate override (shorts run slightly brisker).

    Returns {"chunks": [...], "scene_durations": [...], "total": float,
             "engine": "edge"|"piper"}.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    meta_file = work_dir / "narration.json"
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
            if meta.get("story_hash") == story.get("hash"):
                return meta
            # story changed underneath (audit-gate rerun) — stale cache
            chunks_dir = work_dir / "chunks"
            if chunks_dir.exists():
                for f in chunks_dir.glob("chunk_*.wav"):
                    f.unlink()
        except json.JSONDecodeError:
            pass

    vconf = dict(cfg()["voice"])
    if rate_pct is not None:
        vconf["edge_rate"] = rate_pct
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
    for scene in story["scenes"]:
        for text in split_chunks(scene["narration"]):
            idx += 1
            plan.append({"scene": scene["n"], "text": text, "idx": idx})

    # engine choice: config (auto/edge/piper) + live probe
    engine_conf = str(vconf.get("engine", "auto")).lower()
    engine = "piper" if engine_conf == "piper" else "edge"
    if engine == "edge" and not _edge_probe(vconf, chunks_dir):
        print("  [voice] neural endpoint unreachable — using offline Piper")
        engine = "piper"

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
