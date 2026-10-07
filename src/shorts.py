"""Shorts — NATIVE vertical 9:16 videos (not letterboxed cuts).

Each Short is one psychology concept delivered in the reference
channel's format:
  * hook card: the couple + huge stroked text (the scroll-stopper)
  * body cards: the couple + the current narration line baked in as a
    bold overlay (karaoke-style, chunk by chunk)
  * term card: "psychologists call this — {TERM}" (the signature moment)
  * CTA card: "Subscribe for more tips like this." + subscribe pill

The couple now ANIMATES: subtle sway, breathing bob and blinks at
30 fps (a different movement style every video), rendered from art
layers by the animator. Audio: neural narration + a quiet,
mood-matched music bed that ducks under the voice. Everything
resumable per clip, like the long pipeline.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from . import anim, art_engine, music, tts
from .config import cfg
from .content_data import CTA_LINE
from .render import probe, render_clip_art


def _ffmpeg(args: list[str], timeout: int = 900) -> None:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y"] + args
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          stdin=subprocess.DEVNULL, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.decode()[-800:]}")


_REVEAL_MARKERS = ("call this", "name for this", "is called",
                    "term for this")


def _card_kind(text: str, idx: int, term: str | None = None) -> str:
    if idx == 0:
        return "hook"
    low = text.strip().lower()
    if term and term.lower() in low and any(m in low for m in _REVEAL_MARKERS):
        return "term"
    if low == CTA_LINE.lower().rstrip("."):
        return "cta"
    if "subscribe for more tips" in low:
        return "cta"
    return "scene"


def _build_card_layers(kind: str, text: str, short: dict, seed: int,
                       part: int) -> dict:
    band, sc = short["band"], short["scene"]
    if kind == "hook":
        return art_engine.build_hook_layers(short["hook"], band, part, sc, seed)
    if kind == "term":
        return art_engine.build_term_layers(short["term"], band, sc, seed)
    if kind == "cta":
        return art_engine.build_cta_layers(band, sc, seed)
    return art_engine.build_scene_card_layers(text, band, sc, seed)


def _mix_audio(short_work: Path, narration: dict, seed: int,
               mood: str = "warm") -> Path:
    """narration + mood-matched ducking music bed -> master.wav.
    The bed is exactly as long as the narration: voice, script,
    animation and music all END together (owner rule — never silent
    padding at the end)."""
    import wave

    depth = float(cfg()["music"].get("duck_depth", 0.55))

    narr = tts.read_wav(short_work / "narration.wav")
    narr_np = np.frombuffer(narr.tobytes(), dtype=np.int16).astype(np.float32) / 32768.0
    narr_np = music.normalize_speech(narr_np)
    narr_44 = np.repeat(narr_np, 2)  # 22050 -> 44100

    total = narration["total"]
    n = int(total * music.SR)
    music_bed = music.synth_music(seed + 700, total, mood=mood)
    music_bed *= music.duck_envelope(narr_44, n, music.SR, depth)
    music_bed *= np.float32(0.16)

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
    """Render the episode's native shorts (up to the 6 specs the story
    carries; the orchestrator slices what the grid owes). Idempotent
    per short."""
    from .render import MOTIONS

    work_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    sconf = cfg()["shorts"]

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
        clips_dir = sw / "clips"
        clips_dir.mkdir(exist_ok=True)

        # 1. narration (cached; brisk pace + tighter pauses for shorts).
        # The cache key includes the script hash: if the script ever
        # changes underneath, the narration re-renders (never stale).
        mini = {"hash": f"{story['hash']}-{short['shash'][:10]}",
                "scenes": [{"n": 1, "id": "short", "narration": short["script"]}]}
        rate = cfg()["voice"].get("edge_rate_shorts")
        narration = tts.narrate(mini, sw, sent_pause=0.30, scene_pause=0.30,
                                rate_pct=rate)
        # Owner rule: the VOICE carries the whole video — no silent
        # seconds, the script ends WITH the video. Scripts are built
        # ~150+ words (≈55 s) so this almost never triggers; if the
        # narration still lands under the floor, re-voice it slower
        # with breathing pauses (stretched speech, never padding).
        min_s = float(sconf.get("min_seconds", 45))
        for attempt in range(2):
            if narration["total"] >= min_s:
                break
            stretch = min_s / max(narration["total"], 1.0)
            slow = min(25, max(6, round((stretch - 1.0) * 100) + 5))
            print(f"  [short {n}] narration {narration['total']:.1f}s < "
                  f"{min_s:.0f}s floor — re-voicing slower (-{slow}%), "
                  f"attempt {attempt + 1}")
            mini["hash"] = f"{story['hash']}-{short['shash'][:10]}-r{attempt}"
            narration = tts.narrate(mini, sw, sent_pause=0.45,
                                    scene_pause=0.45, rate_pct=f"-{slow}%")
        chunks = narration["chunks"]
        total = narration["total"]

        # 2. one animated card per caption chunk (karaoke-style)
        seed = story["seed"] + n * 131
        style = anim.pick_style(story["seed"])   # one style per video
        clips: list[Path] = []
        for i, ch in enumerate(chunks):
            start = ch["start"]
            end = chunks[i + 1]["start"] if i + 1 < len(chunks) else total
            dur = max(0.8, end - start)
            kind = _card_kind(ch["text"], i, short.get("term"))
            cp = clips_dir / f"{i:02d}.mp4"
            if not cp.exists() or float(probe(cp).get("format", {}).get("duration", 0)) < dur - 0.4:
                motion = MOTIONS[(seed + i) % 4]
                layers = _build_card_layers(kind, ch["text"], short, seed, n)
                render_clip_art(layers, seed, cp, dur, motion,
                                size=(1080, 1920), anim_style=style,
                                card_idx=i)
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
            master = _mix_audio(sw, narration, seed,
                                mood=story.get("mood", "warm"))

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
