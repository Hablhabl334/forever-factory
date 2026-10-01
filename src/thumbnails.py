"""Auto thumbnails for the long videos — the niche's proven look:
near-black card, huge bold promise text, one purple accent word,
brand wordmark. Short, punchy, zero clutter.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import art_engine
from .config import ROOT


def _font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    return art_engine.font(kind, size)


def _wrap(d: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont,
          max_w: float) -> list[str]:
    return art_engine._wrap(d, text, f, max_w)


def _pick_promise(story: dict) -> str:
    """Short punchy thumbnail text: the strongest 4-8 words available."""
    n = len(story["atoms"]["concepts"])
    title = story["title"]
    # prefer "N lessons" framing when the title is long
    if len(title.split()) > 6:
        return f"{n} psychology lessons"
    return title


def make_thumbnail(story: dict, out: Path, seed: int | None = None) -> Path:
    """1280x720 dark bold thumbnail from the story spec."""
    img = Image.new("RGB", (1280, 720), art_engine.INK)
    glow = art_engine._glow((1280, 720), (640, 380), 250, art_engine.PURPLE, 30)
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)

    # topic band top
    band_f = _font("card", 40)
    label = story.get("topic_label", "psychology of love").upper()
    while d.textlength(label, font=band_f) > 1050:
        label = label[:-1]
    art_engine._center(d, 640, 52, label, band_f, art_engine.WHITE)
    d.rectangle([560, 112, 720, 118], fill=art_engine.PURPLE)

    # the promise: huge, white, one accent word
    f = _font("card", 92)
    text = _pick_promise(story).upper()
    words = text.split()
    acc = max(words, key=len) if words else ""
    lines, cur, cur_acc = [], [], False
    for wd in words:
        trial = cur + [wd]
        if d.textlength(" ".join(trial), font=f) > 1120 and cur:
            lines.append((" ".join(cur), cur_acc))
            cur, cur_acc = [wd], wd == acc
        else:
            cur = trial
            cur_acc = cur_acc or wd == acc
    if cur:
        lines.append((" ".join(cur), cur_acc))
    lines = lines[:3]

    y = 210
    for text, has_acc in lines:
        tw_line = d.textlength(text, font=f)
        x = 640 - tw_line / 2
        if has_acc and acc in text:
            pre, _, post = text.partition(acc)
            d.text((x, y), pre, font=f, fill=art_engine.WHITE)
            x2 = x + d.textlength(pre, font=f)
            d.text((x2, y), acc, font=f, fill=art_engine.PURPLE_SOFT)
            d.text((x2 + d.textlength(acc, font=f), y), post, font=f, fill=art_engine.WHITE)
        else:
            d.text((x, y), text, font=f, fill=art_engine.WHITE)
        y += 112

    # silhouettes bottom (subtle depth)
    art_engine._mono_pair(d, 1280, 700, 0.5,
                          {"emotion_a": "neutral", "pose_a": "stand",
                           "emotion_b": "neutral", "pose_b": "stand"},
                          (seed or story["seed"]) + 5)

    # wordmark
    art_engine._wordmark(d, 640, 660, 34)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")
    return out
