"""The resumable ffmpeg renderer — every lesson from every prior build.

Hard-won rules baked in:
  * ``-nostdin`` + ``stdin=DEVNULL`` — ffmpeg's interactive stdin reader
    blocks forever when run in a foreground pipe (v3 lesson).
  * ``preset veryfast`` + ``tune stillimage`` — 10x faster on weak CPUs
    (v3 lesson).
  * zoompan is fed ONE frame, never a looped stream — a looped PNG fed
    into zoompan multiplies frames catastrophically (v3 lesson).
  * every clip is rendered atomically (tmp file + rename) and skipped
    if already valid — interruptions lose nothing (v1/v2 lesson).
  * captions are burned per clip from sliced ASS events, so the final
    concat is a stream copy — one encode pass, no global re-encode.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np

from .config import cfg, ROOT


def _ffmpeg(args: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    """Run ffmpeg safely: no stdin, generous timeout, loud errors."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y"] + args
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL, timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed ({proc.returncode}): {' '.join(args[:6])}...\n"
            f"{proc.stderr.decode()[-1200:]}"
        )
    return proc


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format",
         "-show_streams", str(path)],
        capture_output=True, text=True, timeout=60,
    )
    return json.loads(out.stdout)


def clip_ok(path: Path, expected_dur: float, fps: int) -> bool:
    """Validate a rendered clip: exists, right duration, right fps."""
    if not path.exists():
        return False
    try:
        info = probe(path)
        dur = float(info.get("format", {}).get("duration", 0))
        if abs(dur - expected_dur) > 0.35:
            return False
        for st in info.get("streams", []):
            if st.get("codec_type") == "video":
                if st.get("avg_frame_rate", "0").split("/")[0] not in (str(fps),):
                    # allow small drift: check against fps directly
                    try:
                        num = int(st.get("avg_frame_rate", "0/1").split("/")[0])
                    except (ValueError, IndexError):
                        return False
                    if abs(num - fps) > 1:
                        return False
        return True
    except (json.JSONDecodeError, subprocess.TimeoutExpired, ValueError, KeyError):
        return False


# ── ASS subtitle generation ──────────────────────────────────────────

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Baloo 2,56,&H00FFFFFF,&H00FFFFFF,&H00181028,&H96000000,-1,0,0,0,100,100,0,0,1,2.8,1.4,2,80,80,64,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _wrap_ass(text: str, max_chars: int = 46) -> str:
    """Wrap caption text to at most two balanced lines with \\N."""
    if len(text) <= max_chars:
        return text
    words = text.split()
    best, best_diff = None, 10 ** 9
    for i in range(1, len(words)):
        l1 = " ".join(words[:i])
        l2 = " ".join(words[i:])
        if len(l1) <= max_chars + 6 and len(l2) <= max_chars + 6:
            diff = abs(len(l1) - len(l2))
            if diff < best_diff:
                best, best_diff = (l1, l2), diff
    if best:
        return best[0] + r"\N" + best[1]
    mid = len(text) // 2
    cut = text.rfind(" ", 0, mid) or mid
    return text[:cut] + r"\N" + text[cut + 1:]


def build_global_ass(chunks: list[dict], offset: float, out_path: Path) -> None:
    """ASS with global times (narration-relative + offset)."""
    lines = [ASS_HEADER]
    for ch in chunks:
        start = ch["start"] + offset
        end = ch["end"] + offset
        text = _wrap_ass(ch["text"])
        lines.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Cap,,0,0,0,,"
            f"{{\\fad(180,180)}}{text}"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def slice_ass(global_ass_path: Path, t0: float, t1: float, out_path: Path) -> None:
    """Clip a global ASS file to the [t0, t1) window, times shifted local."""
    lines = global_ass_path.read_text(encoding="utf-8").splitlines()
    out = [ASS_HEADER]
    for line in lines:
        if not line.startswith("Dialogue:"):
            continue
        try:
            fields = line.split("Dialogue: ")[1]
            parts = fields.split(",", 9)
            start, end = _parse_ass_time(parts[1]), _parse_ass_time(parts[2])
            text = parts[9] if len(parts) > 9 else ""
            new_start = max(0.0, start - t0)
            new_end = min(t1 - t0, end - t0)
            if new_end - new_start < 0.15:
                continue
            out.append(
                f"Dialogue: 0,{_ass_time(new_start)},{_ass_time(new_end)},Cap,,0,0,0,,{text}"
            )
        except (IndexError, ValueError):
            continue
    out_path.write_text("\n".join(out) + "\n", encoding="utf-8")


def _parse_ass_time(s: str) -> float:
    s = s.strip()
    h, m, sec = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)


# ── Ken Burns motions ────────────────────────────────────────────────

def _zoompan_expr(motion: str, frames: int) -> str:
    d = max(2, frames)
    if motion == "zoom_in":
        z = f"1+0.10*on/{d}"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "zoom_out":
        z = f"1.10-0.10*on/{d}"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "pan_right":
        z = "1.08"
        x = f"(iw-iw/zoom)*on/{d}"
        y = "ih/2-(ih/zoom/2)"
    else:  # pan_left
        z = "1.08"
        x = f"(iw-iw/zoom)*(1-on/{d})"
        y = "ih/2-(ih/zoom/2)"
    return f"zoompan=z='{z}':x='{x}':y='{y}':d={d}:s=1920x1080:fps=30"


MOTIONS = ["zoom_in", "pan_right", "zoom_out", "pan_left"]


def render_clip(png: Path, out: Path, dur: float, motion: str,
                ass_file: Path | None = None, crf: int = 21) -> None:
    """Render one scene clip with Ken Burns + burned captions. Atomic."""
    vconf = cfg()["video"]
    fps = int(vconf.get("fps", 30))
    frames = int(round(dur * fps))
    filters = [_zoompan_expr(motion, frames)]
    if ass_file is not None:
        fontsdir = ROOT / "assets" / "fonts"
        filters.append(f"ass=filename='{ass_file}':fontsdir='{fontsdir}'")
    filters.append("format=yuv420p")
    vf = ",".join(filters)

    tmp = out.with_suffix(".tmp.mp4")
    args = [
        "-i", str(png),
        "-vf", vf,
        "-frames:v", str(frames),
        "-c:v", "libx264", "-preset", vconf.get("preset", "veryfast"),
        "-tune", "stillimage", "-crf", str(vconf.get("crf", crf)),
        "-g", "60", "-an", str(tmp),
    ]
    _ffmpeg(args, timeout=max(120, int(frames / 2)))
    tmp.replace(out)


# ── episode render ───────────────────────────────────────────────────

def render_episode(story: dict, narration: dict, work_dir: Path,
                   out_dir: Path, seed: int) -> Path:
    """Full video: title card + 16 scenes + end card, resumable per clip.

    Returns the final mp4 path (out_dir/final.mp4).
    """
    from . import art_engine
    from . import music as music_mod

    vconf = cfg()["video"]
    mconf = cfg()["music"]
    fps = int(vconf.get("fps", 30))
    title_s = float(vconf.get("title_card_seconds", 6))
    end_s = float(vconf.get("end_card_seconds", 12))

    work_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    clips_dir = work_dir / "clips"
    clips_dir.mkdir(exist_ok=True)
    art_dir = work_dir / "art"
    art_dir.mkdir(exist_ok=True)

    chunks = narration["chunks"]
    scene_durs = narration["scene_durations"]
    narr_total = narration["total"]
    total = title_s + narr_total + end_s

    # 1. art
    title_png = art_dir / "title.png"
    if not title_png.exists():
        img = art_engine.paint_title_card(story["title"], seed, story["scenes"][0]["image"].get("time_mood", "moonlit_night"))
        img.save(title_png, "PNG")
    end_png = art_dir / "end.png"
    if not end_png.exists():
        art_engine.paint_end_card(seed + 5).save(end_png, "PNG")
    for scene in story["scenes"]:
        png = art_dir / f"scene_{scene['n']:02d}.png"
        if not png.exists():
            art_engine.save_scene(scene, seed + scene["n"] * 13, png,
                                  story["scenes"][0]["image"].get("time_mood"))
            # per-scene time mood from the story's chosen mood
    # repaint with the story's actual mood for scene 1 (title uses it already)

    # 2. global captions
    global_ass = work_dir / "captions.ass"
    if not global_ass.exists():
        build_global_ass(chunks, title_s, global_ass)

    # 3. clips (resumable)
    motions = [MOTIONS[(seed + i) % 4] for i in range(20)]

    def clip_path(name: str) -> Path:
        return clips_dir / f"{name}.mp4"

    # title card: no captions
    tc = clip_path("00_title")
    if not clip_ok(tc, title_s, fps):
        render_clip(title_png, tc, title_s, "zoom_in")

    # scene clips
    t = title_s
    for i, scene in enumerate(story["scenes"]):
        dur = scene_durs[i]
        cp = clip_path(f"{scene['n']:02d}_scene")
        if not clip_ok(cp, dur, fps):
            cass = clips_dir / f"{scene['n']:02d}.ass"
            slice_ass(global_ass, t, t + dur, cass)
            png = art_dir / f"scene_{scene['n']:02d}.png"
            render_clip(png, cp, dur, motions[i], ass_file=cass)
        t += dur

    # end card: no captions
    ec = clip_path("99_end")
    if not clip_ok(ec, end_s, fps):
        render_clip(end_png, ec, end_s, "zoom_out")

    # 4. concat (stream copy — instant)
    final = out_dir / "final.mp4"
    concat_list = work_dir / "concat.txt"
    with open(concat_list, "w") as f:
        f.write(f"file '{tc.resolve()}'\n")
        for scene in story["scenes"]:
            f.write(f"file '{clips_dir / f'{scene['n']:02d}_scene.mp4'}'\n")
        f.write(f"file '{ec.resolve()}'\n")
    silent = work_dir / "silent.mp4"
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat_list),
             "-c", "copy", str(silent)], timeout=120)

    # 5. master audio (narration + music bed with ducking envelope)
    master_wav = work_dir / "master.wav"
    if not master_wav.exists():
        master_wav = _build_master_audio(work_dir, narration, title_s, end_s,
                                         total, seed, float(mconf.get("volume_db", -21)))

    # 6. mux
    _ffmpeg(["-i", str(silent), "-i", str(master_wav),
             "-map", "0:v", "-map", "1:a",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-movflags", "+faststart", "-shortest", str(final)], timeout=300)

    # 7. cleanup partial
    silent.unlink(missing_ok=True)
    return final


def _build_master_audio(work_dir: Path, narration: dict, title_s: float,
                        end_s: float, total: float, seed: int,
                        music_db: float) -> Path:
    """Mix narration + music into master.wav (44.1 kHz stereo int16)."""
    from . import music as music_mod
    from .tts import read_wav, SR as NARR_SR

    narr = read_wav(work_dir / "narration.wav")
    narr_np = np.frombuffer(narr.tobytes(), dtype=np.int16).astype(np.float64) / 32768.0
    # resample 22050 -> 44100 (exactly 2x)
    narr_44 = np.repeat(narr_np, 2)

    from . import music as M
    music = M.synth_music(seed, total)

    n = music.shape[0]
    voice = np.zeros(n)
    start_i = int(title_s * M.SR)
    end_i = min(n, start_i + len(narr_44))
    voice[start_i:end_i] = narr_44[: end_i - start_i]
    voice = np.stack([voice, voice], axis=1)

    # ducking envelope: full music in title/end, music_db under narration
    gain_loud = 0.9
    gain_quiet = 10 ** (music_db / 20)  # e.g. -21 dB -> 0.089
    env = np.full(n, gain_quiet)
    voice_end = start_i + int(narration["total"] * M.SR)
    env[:start_i] = gain_loud
    env[voice_end:] = gain_loud
    # 1.5 s smooth ramps
    ramp = int(1.5 * M.SR)
    for k in range(ramp):
        if k < n:
            env[start_i - ramp + k] = gain_loud + (gain_quiet - gain_loud) * k / ramp if start_i - ramp + k >= 0 else gain_quiet
            if voice_end + k < n:
                env[voice_end + k] = gain_quiet + (gain_loud - gain_quiet) * k / ramp

    stereo = voice + music * env[:, None]
    peak = np.max(np.abs(stereo)) or 1.0
    if peak > 0.89:
        stereo = stereo / peak * 0.89

    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    import wave
    with wave.open(str(work_dir / "master.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(M.SR)
        w.writeframes(pcm.tobytes())
    return work_dir / "master.wav"
