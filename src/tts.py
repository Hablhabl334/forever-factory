"""Offline neural narration — Piper TTS with exact caption timings.

Each caption chunk (one sentence, or a comma-split piece of a long
sentence) is synthesized separately, so the audio duration of every
caption is EXACT — captions can never drift out of sync. Soft pauses
are inserted between sentences and scenes, matching the guide's
"gentle sentence endings and natural pauses" direction.

Fully offline: the voice model is vendored in assets/voice/ — no API,
no key, nothing to expire for a decade.
"""
from __future__ import annotations

import json
import re
import wave
from pathlib import Path

import array

from .config import cfg, path as repo_path

SR = 22_050


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


def _synth_chunk(voice, text: str, length_scale: float) -> array.array:
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


def narrate(story: dict, work_dir: Path, model_path: Path | None = None,
            sent_pause: float | None = None,
            scene_pause: float | None = None) -> dict:
    """Synthesize the whole narration. Idempotent & resumable:
    each chunk is cached as work/chunks/chunk_NNN.wav; a completed run
    writes work/narration.json which short-circuits re-runs.

    Optional pause overrides (shorts use tighter pacing).

    Returns {"chunks": [...], "scene_durations": [...], "total": float}.
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

    vconf = cfg()["voice"]
    length_scale = float(vconf.get("length_scale", 1.45))
    sent_pause = float(vconf.get("sentence_pause", 0.4)) if sent_pause is None else sent_pause
    scene_pause = float(vconf.get("paragraph_pause", 0.7)) if scene_pause is None else scene_pause

    model_path = Path(model_path or repo_path("assets", "voice", "en_US-lessac-medium.onnx"))
    if not model_path.exists():
        raise FileNotFoundError(f"Piper voice model missing: {model_path}")

    from piper import PiperVoice
    voice = PiperVoice.load(str(model_path))

    chunks_dir = work_dir / "chunks"
    chunks_dir.mkdir(exist_ok=True)

    silence = array.array("h", bytes(0))
    pause_frames = lambda secs: array.array("h", b"\x00\x00" * int(secs * SR))

    chunks_meta: list[dict] = []
    scene_durations: list[float] = []
    t = 0.0
    idx = 0
    for scene in story["scenes"]:
        scene_start = t
        pieces = split_chunks(scene["narration"])
        for text in pieces:
            idx += 1
            wav_path = chunks_dir / f"chunk_{idx:03d}.wav"
            if not wav_path.exists():
                frames = _synth_chunk(voice, text, length_scale)
                write_wav(wav_path, frames)
            frames = read_wav(wav_path)
            dur = len(frames) / SR
            chunks_meta.append({
                "scene": scene["n"],
                "text": text,
                "start": round(t, 3),
                "end": round(t + dur, 3),
            })
            t += dur + sent_pause
        t += scene_pause
        # video scene duration == exact audio built for the scene
        scene_durations.append(round(t - scene_start, 3))

    total = t

    # master narration wav: concat cached chunks with pauses
    master = array.array("h")
    cursor = 0.0
    ci = 0
    for scene in story["scenes"]:
        pieces = split_chunks(scene["narration"])
        for text in pieces:
            ci += 1
            frames = read_wav(chunks_dir / f"chunk_{ci:03d}.wav")
            master.extend(frames)
            master.extend(pause_frames(sent_pause))
        master.extend(pause_frames(scene_pause))

    # trim to exact total length
    need = int(total * SR)
    if len(master) > need:
        master = master[:need]
    elif len(master) < need:
        master.extend(array.array("h", b"\x00\x00" * (need - len(master))))
    write_wav(work_dir / "narration.wav", master)

    result = {
        "story_hash": story.get("hash"),
        "chunks": chunks_meta,
        "scene_durations": scene_durations,
        "total": round(total, 3),
        "sample_rate": SR,
    }
    meta_file.write_text(json.dumps(result, indent=1))
    return result
