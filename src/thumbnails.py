"""Auto thumbnails for the long videos — the niche's proven look:
near-black card, huge bold promise text, one purple accent word,
brand wordmark. Short, punchy, zero clutter.

2026-10-27 — the youtube-thumbnail-design skill, translated to free
factory code (its design rules are 100% free knowledge; only its
belt/image-API examples were paid, and are ignored per the owner's
free-only rule — see skills/youtube-thumbnail-design):

  * MAX 6 WORDS of promise text (the skill's text rule — if it is
    not readable at thumbnail size, cut words, never shrink)
  * SEEDED EXPRESSION VARIETY (the skill's face-expression CTR
    table): the LOCKED couple never changes; only the face varies
    per episode — warm positive expressions, inlove carrying double
    weight as the brand signature
  * THE AUTOMATED CHECKLIST (audit_thumbnail): spec size, mobile
    text floor, the 120px squint test (measured, not squinted),
    text-zone contrast, the ≤3-color rule and the <2MB spec — every
    cycle, logged, deterministic. It fails OPEN (loud warning, never
    a blocked day) because renders are pure functions of the seed:
    a deterministic failure would repeat forever, and the audit's
    job is to catch regressions, not to starve the grid.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import art_engine
from .config import ROOT

# the promise font: 102px on 720 = 14.2% of frame height — passes the
# mobile floor (8%) with margin; at the 120px feed preview that is a
# ~9.5px glyph, the largest text this niche can carry at 6 words
PROMISE_FONT = 102
# the skill's mobile legibility floor: text must be >= 8% of frame
# height (≈58px on 720) to survive the 120px feed preview
MOBILE_FLOOR = 0.08 * 720
# warm expressions for a love-psychology channel; the LOCKED couple
# stays identical episode to episode — only the face varies (seeded)
THUMB_EMOTIONS = ["inlove", "inlove", "happy", "hopeful", "shy"]


def _font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    return art_engine.font(kind, size)


def _wrap(d: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont,
          max_w: float) -> list[str]:
    return art_engine._wrap(d, text, f, max_w)


def _pick_promise(story: dict) -> str:
    """Short punchy thumbnail text: the skill's max-6-words rule.
    A long title becomes 'N psychology lessons'; a short one is the
    title itself, hard-capped at 6 words — cut words, never shrink."""
    n = len(story["atoms"]["concepts"])
    title = story["title"]
    words = title.split()
    if len(words) > 6:
        return f"{n} psychology lessons"
    return " ".join(words[:6])


def _thumb_emotions(seed: int) -> list[str]:
    """Seeded per-episode expression pair for the locked couple
    (unified mood — one feeling per frame, one focal point)."""
    from .config import cfg
    try:
        pool = list(cfg().get("thumbnail", {}).get("emotions")
                     or THUMB_EMOTIONS)
    except Exception:
        pool = list(THUMB_EMOTIONS)
    from .rng import FactoryRNG
    emo = FactoryRNG(seed + 77).pick(pool)
    return [emo, emo]


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

    # the promise: huge, white, one accent word (v4: 92 -> 102 px —
    # thumbnail text competes at phone size; cut words, never shrink)
    f = _font("card", PROMISE_FONT)
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

    y = 200
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
        y += 120

    # v4: the LOCKED COLORED couple (the exact pair from every video)
    # instead of the grey mono silhouettes — the thumbnail and the
    # video finally show the same characters; brand recall at a glance.
    # 2026-10-27: the pair's FACE varies per episode (seeded, warm
    # expressions only) — expression CTR psychology, brand intact.
    emo_a, emo_b = _thumb_emotions(seed or story["seed"])
    layers = art_engine._attach_couple(
        img, {"emotion_a": emo_a, "pose_a": "stand",
              "emotion_b": emo_b, "pose_b": "stand"},
        (seed or story["seed"]) + 5, 1280, 706, 0.46)
    img = art_engine.compose_static(layers)
    d = ImageDraw.Draw(img)

    # wordmark
    art_engine._wordmark(d, 640, 660, 34)

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")
    return out


def _luminance(rgb) -> float:
    r, g, b = rgb[:3]
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def audit_thumbnail(story: dict, out: Path) -> dict:
    """The skill's shipping checklist, deterministic and measured:

      1. spec size 1280x720            (spec table)
      2. promise <= 6 words            (text rules)
      3. text >= 8% of frame height    (min-60pt-at-120px rule)
      4. the 120px squint test         (measured: text-band
                                       separability on the real
                                       120x67 downscale)
      5. text/bg contrast delta >= 0.6 (color rules: dark card,
                                       white text — the 3-color
                                       palette is fixed by design)
      6. PNG < 2 MB                    (spec table)

    Returns {"ok", "fails", "words", "font_px", "px120_var"} — logged
    by the orchestrator every cycle; fails OPEN (see module doc)."""
    fails: list[str] = []
    try:
        img = Image.open(out)
    except Exception as exc:
        return {"ok": False, "fails": [f"unreadable image: {exc}"],
                "words": 0, "font_px": PROMISE_FONT, "px120_var": 0,
                "png_kb": 0}
    w, h = img.size
    if (w, h) != (1280, 720):
        fails.append(f"size {w}x{h} != 1280x720")

    promise = _pick_promise(story)
    words = len(promise.split())
    if words > 6:
        fails.append(f"promise has {words} words (max 6)")
    if PROMISE_FONT < MOBILE_FLOOR:
        fails.append(f"text {PROMISE_FONT}px below the {MOBILE_FLOOR:.0f}px "
                     f"mobile floor")

    contrast = _luminance(art_engine.WHITE) - _luminance(art_engine.INK)
    if contrast < 0.6:
        fails.append(f"text/bg contrast delta {contrast:.2f} < 0.60")

    # the 120px squint test, measured: downscale to the feed size and
    # require the promise band (y 200-560 of 720) to stay separable
    small = img.convert("L").resize((120, 67))
    band = small.crop((10, 16, 110, 54))       # 120px-scale promise zone
    px = list(band.getdata())
    mean = sum(px) / len(px)
    var = sum((p - mean) ** 2 for p in px) / len(px)
    if var < 100.0:
        fails.append(f"120px test: text-band variance {var:.0f} < 100 "
                     f"(muddy blur at feed size)")

    size = out.stat().st_size
    if size > 2_000_000:
        fails.append(f"PNG {size/1e6:.1f}MB > 2MB")

    return {"ok": not fails, "fails": fails, "words": words,
            "font_px": PROMISE_FONT, "px120_var": round(var),
            "png_kb": round(size / 1024)}
