"""Shorts — auto-cut 9:16 verticals from the finished long video.

Lesson from the previous build: never crop the 16:9 frame (subtitles
clip mid-line). Instead the industry-standard blurred-background
letterbox: the full 16:9 frame sits centered, readable subtitles and
all, over a blurred, zoomed copy of itself.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import cfg, ROOT
from .render import probe

SHORTS_BEATS = ["challenge_3", "turn", "twist"]


def _ffmpeg(args: list[str], timeout: int = 900) -> None:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y"] + args
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          stdin=subprocess.DEVNULL, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.decode()[-800:]}")


def _font(size: float, weight=700):
    font = ImageFont.truetype(str(ROOT / "assets/fonts/Baloo2.ttf"), int(size))
    try:
        font.set_variation_by_axes([weight])
    except Exception:
        pass
    return font


def _title_overlay(title: str, out: Path) -> None:
    """1080x1920 alpha PNG: story title top, gentle glow."""
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # soft dark gradient top for contrast
    grad = Image.new("L", (1, 500))
    for y in range(500):
        grad.putpixel((0, y), int(160 * (1 - y / 500)))
    grad = grad.resize((1080, 500))
    black = Image.new("RGBA", (1080, 500), (8, 6, 20, 255))
    black.putalpha(grad)
    img.alpha_composite(black, (0, 0))

    font = _font(76, 700)
    words = title.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=font) > 940 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    lines.append(cur)
    y = 120
    for line in lines[:3]:
        tw = d.textlength(line, font=font)
        d.text((540 - tw / 2 + 3, y + 5), line, font=font, fill=(10, 8, 30, 200))
        d.text((540 - tw / 2, y), line, font=font, fill=(255, 246, 228, 255))
        y += 100

    tag = _font(40, 600)
    label = "Moonberry Tales"
    tw = d.textlength(label, font=tag)
    d.text((540 - tw / 2, y + 26), label, font=tag, fill=(255, 226, 170, 235))
    img.save(out, "PNG")


def _end_tag(out: Path) -> None:
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    grad = Image.new("L", (1, 420))
    for y in range(420):
        grad.putpixel((0, y), int(170 * (y / 420)))
    grad = grad.resize((1080, 420))
    black = Image.new("RGBA", (1080, 420), (8, 6, 20, 255))
    black.putalpha(grad)
    img.alpha_composite(black, (0, 1500))
    font = _font(56, 700)
    text = "The full story is on the channel"
    tw = d.textlength(text, font=font)
    d.text((540 - tw / 2 + 2, 1620), text, font=font, fill=(10, 8, 30, 190))
    d.text((540 - tw / 2, 1618), text, font=font, fill=(255, 246, 228, 255))
    tag = _font(38, 600)
    label = "Moonberry Tales"
    tw = d.textlength(label, font=tag)
    d.text((540 - tw / 2, 1710), label, font=tag, fill=(255, 226, 170, 235))
    img.save(out, "PNG")


def pick_windows(story: dict, narration: dict) -> list[dict]:
    """Choose Short windows at beat boundaries, trimmed to chunk ends."""
    vconf = cfg()["video"]
    title_s = float(vconf.get("title_card_seconds", 6))
    max_s = float(cfg()["shorts"]["max_seconds"])
    durs = narration["scene_durations"]
    chunks = narration["chunks"]

    windows = []
    for scene in story["scenes"]:
        if scene["id"] not in SHORTS_BEATS:
            continue
        i = scene["n"] - 1
        start = title_s + sum(durs[:i])
        dur = durs[i]
        if dur > max_s:
            # trim at the latest chunk end inside the window
            rel_end = max_s
            for ch in chunks:
                if ch["scene"] == scene["n"] and ch["end"] <= max_s:
                    rel_end = ch["end"]
            dur = max(20.0, rel_end)
        windows.append({"scene": scene["n"], "id": scene["id"], "start": round(start, 2), "dur": round(dur, 2)})
        if len(windows) >= int(cfg()["shorts"]["count"]):
            break
    return windows


def render_shorts(final_mp4: Path, story: dict, narration: dict,
                  work_dir: Path, out_dir: Path) -> list[Path]:
    work_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    overlay = work_dir / "short_title.png"
    _title_overlay(story["title"], overlay)
    endtag = work_dir / "short_end.png"
    _end_tag(endtag)

    outputs: list[Path] = []
    for w in pick_windows(story, narration):
        out = out_dir / f"short_scene{w['scene']:02d}.mp4"
        if out.exists():
            info = probe(out)
            if float(info["format"]["duration"]) > 10:
                outputs.append(out)
                continue
        fade_out_st = max(0.0, w["dur"] - 3.2)
        vf = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,boxblur=28:2,eq=brightness=-0.06[bg];"
            f"[0:v]scale=1080:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v0];"
            f"[v0][1:v]overlay=0:0:enable='between(t,0,3.2)'[v1];"
            f"[v1][2:v]overlay=0:0:enable='gte(t,{fade_out_st:.2f})'[vout]"
        )
        _ffmpeg([
            "-ss", f"{w['start']:.2f}", "-t", f"{w['dur']:.2f}",
            "-i", str(final_mp4),
            "-i", str(overlay), "-i", str(endtag),
            "-filter_complex", vf,
            "-map", "[vout]", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k", "-r", "30",
            "-movflags", "+faststart", str(out),
        ])
        outputs.append(out)
    return outputs
