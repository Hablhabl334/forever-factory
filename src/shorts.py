"""Shorts — NATIVE vertical 9:16 videos (not letterboxed cuts).

Each Short is one psychology concept delivered in the reference
channel's format:
  * hook card: the scene + huge stroked text (the scroll-stopper)
  * body cards: the scene + the current narration line baked in as a
    bold overlay (karaoke-style, chunk by chunk)
  * term card: "psychologists call this — {TERM}" (the signature moment)
  * CTA card: "Subscribe for more tips like this." + subscribe pill

Audio: Piper narration (tighter pauses) + a quiet generated music bed.
Everything resumable per clip, like the long pipeline.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from . import art_engine, music, tts
from .config import cfg
from .content_data import CTA_LINE
from .render import probe


def _ffmpeg(args: list[str], timeout: int = 900) -> None:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y"] + args
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          stdin=subprocess.DEVNULL, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.decode()[-800:]}")


def _card_kind(text: str, idx: int) -> str:
    if idx == 0:
        return "hook"
    low = text.strip().lower()
    if low.startswith("psychologists call this"):
        return "term"
    if low == CTA_LINE.lower().rstrip("."):
        return "cta"
    if "subscribe for more tips" in low:
        return "cta"
    return "scene"


def _paint_card(kind: str, text: str, short: dict, seed: int, part: int) -> "Image":
    from PIL import Image
    band, sc = short["band"], short["scene"]
    if kind == "hook":
        return art_engine.paint_hook_card(short["hook"], band, part, sc, seed)
    if kind == "term":
        return art_engine.paint_term_card(short["term"], band, sc, seed)
    if kind == "cta":
        return art_engine.paint_cta_card(band, sc, seed)
    return art_engine.paint_scene_card(text, band, sc, seed)


def _mix_audio(short_work: Path, narration: dict, seed: int) -> Path:
    """narration + low music bed -> master.wav (44.1k stereo)."""
    import wave

    narr = tts.read_wav(short_work / "narration.wav")
    narr_np = np.frombuffer(narr.tobytes(), dtype=np.int16).astype(np.float32) / 32768.0
    narr_44 = np.repeat(narr_np, 2)  # 22050 -> 44100

    total = narration["total"]
    n = int(total * music.SR)
    music_bed = music.synth_music(seed + 700, total) * 0.16

    mix = np.zeros(n, dtype=np.float32)
    end_i = min(n, len(narr_44))
    mix[:end_i] += narr_44[:end_i]
    m = min(n, len(music_bed))
    mix[:m] += music_bed[:m]

    peak = float(np.max(np.abs(mix))) or 1.0
    if peak > 0.89:
        mix *= np.float32(0.89 / peak)

    delay = int(0.012 * music.SR)
    pcm = np.empty((n, 2), dtype=np.int16)
    left = (mix * 32767).astype(np.int16)
    right = np.concatenate([np.zeros(delay, dtype=np.float32), mix])[:n]
    pcm[:, 0] = left
    pcm[:, 1] = (right * 32767).astype(np.int16)
    with wave.open(str(short_work / "master.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(music.SR)
        w.writeframes(pcm.tobytes())
    return short_work / "master.wav"


def render_shorts(story: dict, work_dir: Path, out_dir: Path) -> list[Path]:
    """Render the day's 4 native shorts. Idempotent per short."""
    from .render import render_clip, MOTIONS

    work_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    sconf = cfg()["shorts"]
    max_s = float(sconf.get("max_seconds", 57))

    outputs: list[Path] = []
    for short in story["shorts"]:
        n = short["n"]
        out = out_dir / f"short_{n:02d}.mp4"
        if out.exists():
            info = probe(out)
            if float(info.get("format", {}).get("duration", 0)) > 10:
                outputs.append(out)
                continue

        sw = work_dir / f"short_{n:02d}"
        sw.mkdir(parents=True, exist_ok=True)
        art_dir = sw / "art"
        clips_dir = sw / "clips"
        art_dir.mkdir(exist_ok=True)
        clips_dir.mkdir(exist_ok=True)

        # 1. narration (cached; tighter pauses than the long videos)
        mini = {"hash": f"{story['hash']}-s{n}",
                "scenes": [{"n": 1, "id": "short", "narration": short["script"]}]}
        narration = tts.narrate(mini, sw, sent_pause=0.30, scene_pause=0.30)
        chunks = narration["chunks"]
        total = narration["total"]

        # 2. one card per caption chunk (text baked in, karaoke-style)
        seed = story["seed"] + n * 131
        clips: list[Path] = []
        for i, ch in enumerate(chunks):
            start = ch["start"]
            end = chunks[i + 1]["start"] if i + 1 < len(chunks) else total
            dur = max(0.8, end - start)
            kind = _card_kind(ch["text"], i)
            png = art_dir / f"card_{i:02d}.png"
            if not png.exists():
                img = _paint_card(kind, ch["text"], short, seed, n)
                img.save(png, "PNG")
            cp = clips_dir / f"{i:02d}.mp4"
            if not cp.exists() or float(probe(cp).get("format", {}).get("duration", 0)) < dur - 0.4:
                motion = MOTIONS[(seed + i) % 4]
                render_clip(png, cp, dur, motion, size=(1080, 1920))
            clips.append(cp)

        # 3. concat + audio
        concat_list = sw / "concat.txt"
        with open(concat_list, "w") as f:
            for cp in clips:
                f.write(f"file '{cp.resolve()}'\n")
        silent = sw / "silent.mp4"
        _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat_list),
                 "-c", "copy", str(silent)], timeout=120)

        master = sw / "master.wav"
        if not master.exists():
            master = _mix_audio(sw, narration, seed)

        _ffmpeg(["-i", str(silent), "-i", str(master),
                 "-map", "0:v", "-map", "1:a",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                 "-movflags", "+faststart", "-shortest", str(out)],
                timeout=300)
        silent.unlink(missing_ok=True)
        outputs.append(out)
        print(f"  [short {n}] {total:.0f}s, {len(chunks)} cards, "
              f"{out.stat().st_size / 1e6:.1f}MB")

    return outputs
