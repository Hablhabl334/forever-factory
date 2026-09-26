"""Auto thumbnails — truthful packaging per the guide: clear character
emotion, a bedtime cue, short text, zero clickbait."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from .config import ROOT


def _font(size: float, weight=700):
    font = ImageFont.truetype(str(ROOT / "assets/fonts/Baloo2.ttf"), int(size))
    try:
        font.set_variation_by_axes([weight])
    except Exception:
        pass
    return font


def make_thumbnail(scene_png: Path, title: str, out: Path) -> Path:
    """1280x720 thumbnail from a scene image + short title text."""
    img = Image.open(scene_png).convert("RGB")
    img = img.resize((1280, 720), Image.LANCZOS)

    # gentle pop: +saturation, +contrast
    img = ImageEnhance.Color(img).enhance(1.18)
    img = ImageEnhance.Contrast(img).enhance(1.06)

    # bottom gradient for text legibility
    overlay = Image.new("L", (1, 340))
    for y in range(340):
        overlay.putpixel((0, y), int(235 * (y / 340) ** 1.35))
    overlay = overlay.resize((1280, 340))
    black = Image.new("RGB", (1280, 340), (12, 8, 28))
    img = Image.composite(black, img, overlay.point(lambda v: v))

    d = ImageDraw.Draw(img)
    # title text: short words, max 2 lines, chunky
    words = [w for w in title.split() if w.lower() not in ("a", "an", "the", "of", "and")]
    text = " ".join(words)
    font = _font(110, 700)
    lines, cur = [], ""
    for w in text.split():
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=font) > 1100 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    lines.append(cur)
    lines = lines[:2]
    if lines:
        font = _font(110 if len(lines) == 1 else 92, 700)
        y = 720 - 120 - (len(lines) - 1) * (110 if len(lines) == 1 else 98)
        for line in lines:
            tw = d.textlength(line, font=font)
            # soft shadow stack then cream text
            for dx, dy, a in ((0, 8, 90), (0, 4, 120)):
                d.text((640 - tw / 2 + dx, y + dy), line, font=font, fill=(14, 10, 32, a))
            d.text((640 - tw / 2, y), line, font=font, fill=(255, 248, 232))
            y += 112 if len(lines) == 1 else 100

    # moonberry mark top-left: crescent + berry
    mx, my, r = 74, 64, 30
    d.ellipse((mx - r - 12, my - r - 12, mx + r + 12, my + r + 12), fill=(255, 236, 200))
    d.ellipse((mx - r, my - r, mx + r, my + r), fill=(16, 20, 44))
    d.ellipse((mx - r * 0.55, my - r * 1.05, mx + r * 0.75, my + r * 0.5), fill=(255, 244, 216))
    d.ellipse((mx + r * 1.05, my + r * 0.25, mx + r * 1.45, my + r * 0.65), fill=(200, 106, 138))
    tag = _font(34, 600)
    d.text((mx + 52, my - 20), "Moonberry Tales", font=tag, fill=(255, 236, 200))

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")
    return out
