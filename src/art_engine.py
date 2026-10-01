"""The love-psychology art engine — flat webtoon-lite couple illustrations,
bold quote cards, and the reference channel's black-band visual language.

Design system (from the user's reference screenshot, VLM-audited):
  * INK near-black cards, huge bold white type (Archivo Black), purple
    reserved for solid accents; dark-purple silhouettes fill ink cards
  * PAPER warm off-white scenes with two BIG-headed flat characters whose
    poses and faces carry the emotion (worried vs. detached, happy vs. tired)
  * bold text overlays ON the scene with a heavy black stroke
  * persistent black title band on Shorts (topic label, white bold)

Everything drawn procedurally with PIL — zero APIs, zero licenses.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import ROOT

# ── palette ──────────────────────────────────────────────────────────
INK = (13, 13, 19)
INK_SOFT = (26, 26, 38)
PAPER = (240, 236, 228)
PAPER_SHADE = (224, 219, 208)
PAPER_DEEP = (205, 199, 186)
WHITE = (255, 255, 255)
GREY = (168, 168, 178)
PURPLE = (155, 89, 182)
PURPLE_SOFT = (212, 168, 232)
RED = (216, 72, 74)

# monochrome silhouette palette for figures on INK backgrounds
MONO_SKIN = (88, 78, 108)
MONO_HAIR = (44, 40, 60)
MONO_TOP = (62, 54, 82)
MONO_PANTS = (50, 46, 66)

SKINS = [(245, 220, 190), (226, 190, 150), (198, 158, 120), (168, 128, 96)]
HAIRS = [(48, 44, 52), (94, 62, 42), (124, 92, 60), (32, 32, 38), (156, 114, 72)]
TOPS = [(74, 118, 124), (172, 98, 80), (126, 86, 118), (130, 126, 90), (96, 106, 130)]
PANTS = [(72, 68, 78), (88, 80, 70), (62, 66, 86)]

FONT_DIR = ROOT / "assets" / "fonts"


def _try(path: str) -> ImageFont.FreeTypeFont | None:
    p = FONT_DIR / path
    if p.exists():
        return ImageFont.truetype(str(p))
    return None


_DISPLAY = _try("Anton-Regular.ttf")
_CARD = _try("ArchivoBlack-Regular.ttf")
_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    key = (kind, int(size))
    if key in _CACHE:
        return _CACHE[key]
    base = _DISPLAY if kind == "display" else _CARD
    f = base or ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(size))
    _CACHE[key] = f
    return f


def _wrap(d: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont,
          max_w: float) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=f) > max_w and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def _center(d: ImageDraw.ImageDraw, cx: float, y: float, line: str,
            f: ImageFont.FreeTypeFont, fill, stroke: int = 0,
            stroke_fill=None) -> float:
    tw = d.textlength(line, font=f)
    d.text((cx - tw / 2, y), line, font=f, fill=fill,
           stroke_width=stroke, stroke_fill=stroke_fill or INK)
    return y + f.size * 1.22


def _wordmark(d: ImageDraw.ImageDraw, cx: float, y: float, size: int = 42,
              color=PURPLE_SOFT) -> None:
    f = font("card", size)
    text = "PSYCHOLOGY  OF  LOVE"
    tw = d.textlength(text, font=f)
    d.text((cx - tw / 2, y), text, font=f, fill=color)
    d.rectangle([cx - tw / 2, y + size * 1.28, cx + tw / 2,
                 y + size * 1.28 + 5], fill=PURPLE)


def _glow(size: tuple[int, int], center: tuple[float, float],
          radius: float, color, alpha: int = 30) -> Image.Image:
    small = Image.new("RGBA", (size[0] // 8, size[1] // 8), (0, 0, 0, 0))
    sd = ImageDraw.Draw(small)
    c = (center[0] / 8, center[1] / 8)
    r = radius / 8
    sd.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=color + (alpha,))
    return small.resize(size, Image.BILINEAR).filter(
        ImageFilter.GaussianBlur(24))


def _vignette(img: Image.Image) -> Image.Image:
    w, h = img.size
    small = Image.new("L", (w // 16, h // 16), 0)
    sd = ImageDraw.Draw(small)
    sd.rectangle([small.width * 0.08, small.height * 0.08,
                  small.width * 0.92, small.height * 0.92], fill=255)
    mask = small.resize((w, h), Image.BILINEAR).filter(
        ImageFilter.GaussianBlur(w // 18))
    dark = Image.new("RGB", (w, h), (18, 16, 22))
    return Image.composite(img, dark, mask.point(lambda v: 255 - int(v * 0.30)))


# ── the flat couple illustration (webtoon-lite proportions) ──────────
# head:body ~= 1:2.6, thick rounded limbs, arms anchored at shoulders.

def _face(d: ImageDraw.ImageDraw, hx: float, hy: float, s: float,
          emotion: str, facing: int, feature=INK) -> None:
    """Face features; `feature` is the stroke/dot color (light on ink cards)."""
    fx = facing * 12 * s
    eye_y, brow_y, mouth_y = hy - 2 * s, hy - 32 * s, hy + 30 * s
    lx, rx = hx - 24 * s + fx * 0.5, hx + 24 * s + fx * 0.5
    lw = max(3, int(5 * s))

    def dot(x, r=6.5):
        d.ellipse([x - r * s, eye_y - r * s, x + r * s, eye_y + r * s], fill=feature)

    def lid(x):
        d.line([x - 11 * s, eye_y, x + 11 * s, eye_y], fill=feature, width=lw)

    def brow(x, inner_up: float):
        nx = hx + (x - hx) * 0.45 + fx * 0.5
        d.line([x - 14 * s, brow_y - (2 if inner_up > 0 else -2) * s,
                nx, brow_y - inner_up * s], fill=feature, width=lw)

    if emotion == "happy":
        dot(lx), dot(rx), brow(lx, 6), brow(rx, 6)
        d.arc([hx - 16 * s + fx, mouth_y - 10 * s, hx + 16 * s + fx,
               mouth_y + 10 * s], 15, 165, fill=feature, width=lw)
        if feature is INK:
            d.ellipse([lx - 20 * s, hy + 12 * s, lx - 6 * s, hy + 20 * s],
                      fill=(246, 172, 150))
            d.ellipse([rx + 6 * s, hy + 12 * s, rx + 20 * s, hy + 20 * s],
                      fill=(246, 172, 150))
    elif emotion == "sad":
        dot(lx), dot(rx), brow(lx, -8), brow(rx, -8)
        d.arc([hx - 16 * s + fx, mouth_y - 2 * s, hx + 16 * s + fx,
               mouth_y + 20 * s], 195, 345, fill=feature, width=lw)
        if feature is INK:
            d.polygon([(lx - 18 * s, hy + 14 * s), (lx - 12 * s, hy + 14 * s),
                       (lx - 15 * s, hy + 30 * s)], fill=(120, 160, 200))
    elif emotion == "anxious":
        for x in (lx, rx):
            dot(x, 9)
        brow(lx, 10), brow(rx, 10)
        d.ellipse([hx - 8 * s + fx, mouth_y - 3 * s, hx + 8 * s + fx,
                   mouth_y + 11 * s], fill=feature)
    elif emotion == "detached":
        lid(lx), lid(rx), brow(lx, 0), brow(rx, 0)
        d.line([hx - 11 * s + fx, mouth_y, hx + 11 * s + fx, mouth_y],
               fill=feature, width=lw)
    elif emotion == "annoyed":
        dot(lx), dot(rx), brow(lx, -10), brow(rx, -10)
        d.arc([hx - 13 * s + fx, mouth_y - 5 * s, hx + 13 * s + fx,
               mouth_y + 10 * s], 200, 340, fill=feature, width=lw)
    elif emotion == "surprised":
        for x in (lx, rx):
            dot(x, 10)
        brow(lx, 12), brow(rx, 12)
        d.ellipse([hx - 9 * s + fx, mouth_y - 4 * s, hx + 9 * s + fx,
                   mouth_y + 13 * s], fill=feature)
    elif emotion == "tired":
        lid(lx), lid(rx), brow(lx, -4), brow(rx, -4)
        d.line([hx - 10 * s + fx, mouth_y, hx + 10 * s + fx, mouth_y],
               fill=feature, width=lw)
    elif emotion == "smug":
        lid(lx), lid(rx), brow(lx, 5), brow(rx, -5)
        d.arc([hx - 18 * s + fx, mouth_y - 12 * s, hx + 10 * s + fx,
               mouth_y + 8 * s], 20, 160, fill=feature, width=lw)
    else:  # neutral
        dot(lx), dot(rx), brow(lx, 0), brow(rx, 0)
        d.line([hx - 10 * s + fx, mouth_y, hx + 10 * s + fx, mouth_y],
               fill=feature, width=lw)


def draw_figure(d: ImageDraw.ImageDraw, x: float, feet_y: float,
                s: float, spec: dict) -> None:
    """One flat character, webtoon-lite proportions (s=1 -> ~430px tall)."""
    emotion, pose = spec["emotion"], spec["pose"]
    facing = spec["facing"]
    skin, hair, top, pants = spec["skin"], spec["hair"], spec["top"], spec["pants"]
    mono = spec.get("mono", False)

    head_r = 66 * s
    hx, hy = x, feet_y - 404 * s            # head center
    hips_y = feet_y - 172 * s
    torso_top = hips_y - 150 * s
    torso_half = 52 * s

    # ground shadow first (grounds the figure)
    d.ellipse([x - 70 * s, feet_y - 16 * s, x + 70 * s, feet_y + 14 * s],
              fill=(216, 210, 198) if not mono else (22, 22, 32))

    # legs: thick rounded limbs
    leg_w = 20 * s
    for sgn in (-1, 1):
        d.rounded_rectangle(
            [x + sgn * 10 * s - leg_w / 2, hips_y - 8 * s,
             x + sgn * 10 * s + leg_w / 2, feet_y - 8 * s],
            radius=leg_w / 2, fill=pants)
        d.rounded_rectangle(   # shoe
            [x + sgn * 10 * s - 20 * s, feet_y - 14 * s,
             x + sgn * 10 * s + 20 * s, feet_y],
            radius=6 * s, fill=INK)

    # torso
    d.rounded_rectangle([x - torso_half, torso_top, x + torso_half, hips_y + 6 * s],
                        radius=26 * s, fill=top)

    # neck
    d.rectangle([x - 12 * s, torso_top - 14 * s, x + 12 * s, torso_top + 6 * s],
                fill=skin)

    # arms — anchored at the shoulders, per pose
    sh_y = torso_top + 26 * s
    arm_w = 17 * s
    if pose == "arms_crossed":
        d.rounded_rectangle([x - torso_half - 4 * s, sh_y + 26 * s,
                             x + torso_half + 4 * s, sh_y + 52 * s],
                            radius=14 * s, fill=top)
        d.rounded_rectangle([x - 34 * s, sh_y + 32 * s, x + 34 * s, sh_y + 50 * s],
                            radius=11 * s, fill=MONO_SKIN if mono else PAPER_SHADE)
    elif pose == "phone":
        arm_x = torso_half - 4 * s
        for sgn in (-1, 1):   # both arms reach down toward the phone
            d.rounded_rectangle(
                [x + sgn * arm_x - arm_w / 2, sh_y,
                 x + sgn * arm_x + arm_w / 2, sh_y + 66 * s],
                radius=arm_w / 2, fill=top)
        # phone held low-front, with visible hands gripping it
        px, py = x + facing * 8 * s, sh_y + 64 * s
        d.rounded_rectangle([px - 20 * s, py - 30 * s, px + 20 * s, py + 30 * s],
                            radius=8 * s, fill=INK)
        d.rectangle([px - 14 * s, py - 22 * s, px + 14 * s, py + 20 * s],
                    fill=PURPLE_SOFT if not mono else MONO_TOP)
        for hy_off in (-26 * s, 26 * s):     # hands on the phone corners
            d.ellipse([px - 26 * s, py + hy_off - 9 * s,
                       px - 6 * s, py + hy_off + 9 * s], fill=skin)
            d.ellipse([px + 6 * s, py + hy_off - 9 * s,
                       px + 26 * s, py + hy_off + 9 * s], fill=skin)
        # head tilts down a touch
        hy += 6 * s
    elif pose == "hands_face":
        for sgn in (-1, 1):
            d.rounded_rectangle(
                [x + sgn * torso_half - arm_w / 2 + sgn * 6 * s, sh_y,
                 x + sgn * torso_half + arm_w / 2 + sgn * 46 * s, sh_y - 60 * s],
                radius=arm_w / 2, fill=top)
        d.ellipse([hx - 44 * s, hy + 16 * s, hx - 14 * s, hy + 42 * s], fill=skin)
        d.ellipse([hx + 14 * s, hy + 16 * s, hx + 44 * s, hy + 42 * s], fill=skin)
    else:  # relaxed stand
        for sgn in (-1, 1):
            d.rounded_rectangle(
                [x + sgn * torso_half - arm_w / 2, sh_y,
                 x + sgn * torso_half + arm_w / 2, sh_y + 96 * s],
                radius=arm_w / 2, fill=top)

    # hair back layer (long styles) behind the head
    style = spec.get("hair_style", "short")
    if facing == 0:
        d.ellipse([hx - head_r - 4 * s, hy - head_r - 4 * s,
                   hx + head_r + 4 * s, hy + head_r + 4 * s], fill=hair)
    elif style == "long":
        d.rounded_rectangle([hx - head_r - 6 * s, hy - head_r,
                             hx + head_r + 6 * s, hy + head_r + 92 * s],
                            radius=30 * s, fill=hair)
        d.ellipse([hx - head_r, hy - head_r, hx + head_r, hy + head_r], fill=skin)
        d.pieslice([hx - head_r, hy - head_r, hx + head_r, hy + head_r],
                   190, 350, fill=hair)
    elif style == "bun":
        d.ellipse([hx - head_r, hy - head_r, hx + head_r, hy + head_r], fill=skin)
        d.pieslice([hx - head_r, hy - head_r, hx + head_r, hy + head_r],
                   190, 350, fill=hair)
        d.ellipse([hx - 18 * s, hy - head_r - 26 * s,
                   hx + 18 * s, hy - head_r + 6 * s], fill=hair)
    else:  # short
        d.ellipse([hx - head_r, hy - head_r, hx + head_r, hy + head_r], fill=skin)
        d.pieslice([hx - head_r, hy - head_r, hx + head_r, hy + head_r],
                   192, 348, fill=hair)

    # face (light feature color on ink/mono cards)
    if facing != 0:
        _face(d, hx, hy, s, emotion, facing,
              feature=PAPER if mono else INK)


def _figure_specs(seed: int, ea: str, pa: str, eb: str, pb: str) -> tuple[dict, dict]:
    from .rng import FactoryRNG
    r = FactoryRNG(seed)
    skins = r.some(SKINS, 2)
    hairs = r.some(HAIRS, 2)
    tops = r.some(TOPS, 2)
    pants = r.some(PANTS, 2)
    a = {"emotion": ea, "pose": pa, "facing": 1, "mono": False,
         "skin": skins[0], "hair": hairs[0], "top": tops[0], "pants": pants[0],
         "hair_style": r.pick(["long", "bun", "long"])}
    b = {"emotion": eb, "pose": pb, "facing": -1, "mono": False,
         "skin": skins[1], "hair": hairs[1], "top": tops[1], "pants": pants[1],
         "hair_style": "short"}
    return a, b


def _mono_specs(seed: int, ea: str, pa: str, eb: str, pb: str) -> tuple[dict, dict]:
    a, b = _figure_specs(seed, ea, pa, eb, pb)
    for f in (a, b):
        f.update({"mono": True, "skin": MONO_SKIN, "hair": MONO_HAIR,
                  "top": MONO_TOP, "pants": MONO_PANTS})
    return a, b


def _scene_room(d: ImageDraw.ImageDraw, w: int, h: int, floor_y: int,
                seed: int) -> None:
    from .rng import FactoryRNG
    r = FactoryRNG(seed)
    d.rectangle([0, floor_y, w, h], fill=PAPER_SHADE)
    d.line([0, floor_y, w, floor_y], fill=PAPER_DEEP, width=5)
    for i in range(1, 6):
        x = int(w * i / 6)
        d.line([x, floor_y, x - 60, h], fill=PAPER_DEEP, width=3)
    prop = r.pick(["window", "plant", "frame", "door", "lamp"])
    if prop == "window":
        x0, y0 = int(w * 0.66), int(floor_y * 0.16)
        x1, y1 = int(w * 0.9), int(floor_y * 0.5)
        d.rectangle([x0, y0, x1, y1], fill=(206, 224, 228))
        d.rectangle([x0 - 10, y0 - 10, x1 + 10, y1 + 10], fill=PAPER_DEEP)
        d.line([(x0 + x1) // 2, y0, (x0 + x1) // 2, y1], fill=PAPER_DEEP, width=8)
        d.line([x0, (y0 + y1) // 2, x1, (y0 + y1) // 2], fill=PAPER_DEEP, width=8)
    elif prop == "plant":
        import math
        bx, by = int(w * 0.85), floor_y
        d.polygon([(bx - 46, by - 92), (bx + 46, by - 92), (bx + 34, by), (bx - 34, by)],
                  fill=(178, 108, 84))
        for ang in (0.4, 0.9, 1.4, 1.9, 2.4):
            ex, ey = bx + math.cos(ang) * 92, by - 100 + math.sin(-abs(ang - 1.4)) * 80
            d.line([(bx, by - 92), (ex, ey)], fill=(108, 138, 100), width=12)
            d.ellipse([ex - 22, ey - 14, ex + 22, ey + 14], fill=(126, 158, 114))
    elif prop == "frame":
        x0, y0 = int(w * 0.08), int(floor_y * 0.2)
        d.rectangle([x0, y0, x0 + 150, y0 + 112], fill=PAPER_DEEP)
        d.rectangle([x0 + 14, y0 + 14, x0 + 136, y0 + 98], fill=(216, 212, 204))
        d.ellipse([x0 + 46, y0 + 30, x0 + 76, y0 + 60], fill=PURPLE_SOFT)
    elif prop == "door":
        x0 = int(w * 0.06)
        d.rectangle([x0, int(floor_y * 0.1), x0 + 130, floor_y], fill=(232, 228, 219))
        d.rectangle([x0, int(floor_y * 0.1), x0 + 130, floor_y],
                    outline=PAPER_DEEP, width=8)
        d.ellipse([x0 + 100, int(floor_y * 0.52), x0 + 114, int(floor_y * 0.58)],
                  fill=PAPER_DEEP)
    else:  # lamp
        lx = int(w * 0.89)
        d.line([(lx, floor_y), (lx, int(floor_y * 0.3))], fill=PAPER_DEEP, width=10)
        d.polygon([(lx - 70, int(floor_y * 0.3)), (lx + 70, int(floor_y * 0.3)),
                   (lx + 44, int(floor_y * 0.16)), (lx - 44, int(floor_y * 0.16))],
                  fill=(240, 214, 130))


# ── scene composition (shared by long + shorts) ──────────────────────

def paint_couple_scene(spec: dict, seed: int, w: int = 1920, h: int = 1080,
                       overlay: list[str] | None = None,
                       band: str | None = None, zoom: float = 1.0) -> Image.Image:
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    band_h = 0 if band is None else int(h * 0.09)
    floor_y = int(h * 0.885)
    _scene_room(d, w, h, floor_y, seed + 17)

    a_spec, b_spec = _figure_specs(seed, spec["emotion_a"], spec["pose_a"],
                                   spec["emotion_b"], spec["pose_b"])
    s = (1.02 if w >= 1600 else 1.45) * zoom
    draw_figure(d, w * 0.32, floor_y + 6, s, a_spec)
    draw_figure(d, w * 0.68, floor_y + 6, s, b_spec)
    img = _vignette(img)
    d = ImageDraw.Draw(img)

    if overlay:
        f = font("display", int(w * 0.045))
        y = band_h + int(h * 0.03)
        for line in overlay[:2]:
            if not line:
                continue
            for ln in _wrap(d, line, f, w * 0.86):
                y = _center(d, w / 2, y, ln, f, WHITE,
                            stroke=max(4, int(w * 0.005)), stroke_fill=INK)

    if band is not None:
        d.rectangle([0, 0, w, band_h], fill=INK)
        f = font("card", int(band_h * 0.35))
        label = band.upper()
        while d.textlength(label, font=f) > w * 0.9:
            label = label[:-1]
        _center(d, w / 2, band_h * 0.2, label, f, WHITE)
    return img


# ── ink-card helpers ─────────────────────────────────────────────────

def _band(d, w: int, band: str, h: int = 170) -> None:
    d.rectangle([0, 0, w, h], fill=INK_SOFT)
    f = font("card", int(h * 0.32))
    label = band.upper()
    while d.textlength(label, font=f) > w * 0.9:
        label = label[:-1]
    _center(d, w / 2, h * 0.2, label, f, WHITE)


def _mono_pair(d, w: float, floor_y: float, s: float, spec: dict, seed: int) -> None:
    a, b = _mono_specs(seed, spec.get("emotion_a", "neutral"),
                       spec.get("pose_a", "stand"),
                       spec.get("emotion_b", "neutral"),
                       spec.get("pose_b", "stand"))
    draw_figure(d, w * 0.34, floor_y, s, a)
    draw_figure(d, w * 0.66, floor_y, s, b)


def _progress_dots(d, cx: float, y: float, total: int, current: int) -> None:
    gap = 56
    total_w = gap * (total - 1)
    for i in range(total):
        x = cx - total_w / 2 + i * gap
        if i + 1 == current:
            d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=PURPLE)
        else:
            d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=INK_SOFT)


# ── long-video cards (1920x1080) ─────────────────────────────────────

def paint_topic_card(title: str, band: str, count: int, seed: int) -> Image.Image:
    img = Image.new("RGB", (1920, 1080), INK)
    glow = _glow((1920, 1080), (960, 520), 380, PURPLE, 30)
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)

    f_band = font("card", 62)
    label = band.upper()
    while d.textlength(label, font=f_band) > 1500:
        label = label[:-1]
    _center(d, 960, 150, label, f_band, WHITE)
    d.rectangle([810, 250, 1110, 256], fill=PURPLE)

    f = font("card", 112)
    y = 400
    for line in _wrap(d, title.upper(), f, 1620)[:2]:
        y = _center(d, 960, y, line, f, WHITE)
    d.rectangle([880, y + 26, 1040, y + 40], fill=PURPLE)

    chip = font("card", 52)
    text = f"{count} LESSONS, EXPLAINED BY PSYCHOLOGY"
    tw = d.textlength(text, font=chip)
    chip_y = min(y + 90, 770)              # clear of the caption zone
    d.rounded_rectangle([960 - tw / 2 - 40, chip_y, 960 + tw / 2 + 40, chip_y + 100],
                        radius=20, outline=PURPLE, width=5)
    d.text((960 - tw / 2, chip_y + 22), text, font=chip, fill=WHITE)
    return img


def paint_concept_card(tip: int, total: int, term: str, headline: str,
                       seed: int) -> Image.Image:
    img = Image.new("RGB", (1920, 1080), INK)
    glow = _glow((1920, 1080), (960, 480), 330, PURPLE, 26)
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)

    chip = font("card", 58)
    label = f"TIP {tip}"
    tw = d.textlength(label, font=chip)
    d.rounded_rectangle([96, 88, 96 + tw + 64, 88 + 96], radius=20, fill=PURPLE)
    d.text((128, 112), label, font=chip, fill=WHITE)

    # silhouettes anchor the bottom (BEHIND the headline, filling the glow)
    _mono_pair(d, 1920, 1030, 0.66, {"emotion_a": "neutral", "pose_a": "stand",
                                    "emotion_b": "neutral", "pose_b": "stand"},
               seed + 5)

    # headline with the longest word accented
    f = font("card", 100)
    words = headline.split()
    acc = max(words, key=len) if words else ""
    lines, cur, cur_acc = [], [], False
    for wd in words:
        trial = cur + [wd]
        if d.textlength(" ".join(trial), font=f) > 1640 and cur:
            lines.append((" ".join(cur), cur_acc))
            cur, cur_acc = [wd], wd == acc
        else:
            cur = trial
            cur_acc = cur_acc or wd == acc
    if cur:
        lines.append((" ".join(cur), cur_acc))
    lines = lines[:4]

    y = 330
    for text, has_acc in lines:
        tw_line = d.textlength(text, font=f)
        x = 960 - tw_line / 2
        if has_acc and acc in text:
            pre, _, post = text.partition(acc)
            d.text((x, y), pre, font=f, fill=WHITE)
            x2 = x + d.textlength(pre, font=f)
            d.text((x2, y), acc, font=f, fill=PURPLE_SOFT)
            d.text((x2 + d.textlength(acc, font=f), y), post, font=f, fill=WHITE)
        else:
            d.text((x, y), text, font=f, fill=WHITE)
        y += 124

    tf = font("card", 44)
    _center(d, 960, 60, f"PSYCHOLOGISTS CALL THIS:  {term.upper()}", tf, GREY)
    return img


def paint_outro_card(topic: str, seed: int) -> Image.Image:
    img = Image.new("RGB", (1920, 1080), INK)
    glow = _glow((1920, 1080), (960, 430), 360, PURPLE, 30)
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)
    f = font("card", 92)
    y = 260
    for line in _wrap(d, f"THAT'S THE PSYCHOLOGY OF {topic.upper()}",
                      f, 1560)[:3]:
        y = _center(d, 960, y, line, f, WHITE)
    f2 = font("card", 56)
    y += 40
    for line in _wrap(d, "If one of these hit home, it did its job.",
                      f2, 1400)[:2]:
        y = _center(d, 960, y, line, f2, PURPLE_SOFT)
    d.rounded_rectangle([770, y + 56, 1150, y + 156], radius=48, fill=PURPLE)
    sf = font("card", 50)
    _center(d, 960, y + 80, "SUBSCRIBE", sf, WHITE)
    return img


def paint_end_card(seed: int) -> Image.Image:
    img = Image.new("RGB", (1920, 1080), INK)
    glow = _glow((1920, 1080), (960, 470), 360, PURPLE, 34)
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)
    f = font("card", 96)
    y = 350
    for line in _wrap(d, "Subscribe for more", f, 1520)[:2]:
        y = _center(d, 960, y, line, f, WHITE)
    for line in _wrap(d, "tips like this.", f, 1520)[:1]:
        y = _center(d, 960, y, line, f, PURPLE_SOFT)
    d.rounded_rectangle([760, y + 60, 1160, y + 160], radius=48, fill=PURPLE)
    sf = font("card", 48)
    _center(d, 960, y + 84, "SUBSCRIBE", sf, WHITE)
    _wordmark(d, 960, y + 230, 40)
    return img


# ── shorts cards (1080x1920) ─────────────────────────────────────────

def paint_hook_card(hook: str, band: str, part: int, scene: dict,
                    seed: int) -> Image.Image:
    """Hook = scene + huge stroked text (the reference look)."""
    img = paint_couple_scene(scene, seed + 91, 1080, 1920, zoom=1.0)
    d = ImageDraw.Draw(img)
    band_h = 170
    d.rectangle([0, 0, 1080, band_h], fill=INK)
    f_band = font("card", 56)
    label = band.upper()
    while d.textlength(label, font=f_band) > 950:
        label = label[:-1]
    _center(d, 540, 38, label, f_band, WHITE)
    pf = font("card", 40)
    _center(d, 540, 104, f"PART {part}", pf, PURPLE_SOFT)

    f = font("display", 104)
    y = 360
    for line in _wrap(d, hook.lower(), f, 940)[:7]:
        y = _center(d, 540, y, line, f, WHITE,
                    stroke=10, stroke_fill=INK)
    return img


def paint_scene_card(text: str, band: str, scene: dict, seed: int) -> Image.Image:
    """Body chunk: scene + bold stroked overlay + band."""
    img = paint_couple_scene(scene, seed + 91, 1080, 1920, zoom=1.0)
    d = ImageDraw.Draw(img)
    band_h = 170
    d.rectangle([0, 0, 1080, band_h], fill=INK)
    f_band = font("card", 56)
    label = band.upper()
    while d.textlength(label, font=f_band) > 950:
        label = label[:-1]
    _center(d, 540, 38, label, f_band, WHITE)

    f = font("display", 84)
    y = 300
    for line in _wrap(d, text.lower(), f, 950)[:8]:
        y = _center(d, 540, y, line, f, WHITE, stroke=9, stroke_fill=INK)
    return img


def paint_term_card(term: str, band: str, scene: dict, seed: int) -> Image.Image:
    img = Image.new("RGB", (1080, 1920), INK)
    glow = _glow((1080, 1920), (540, 700), 330, PURPLE, 34)
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)
    _band(d, 1080, band)
    _mono_pair(d, 1080, 1780, 1.15, scene, seed + 5)

    f0 = font("card", 52)
    _center(d, 540, 560, "psychologists call this", f0, GREY)
    f = font("display", 148)
    y = 680
    for line in _wrap(d, term.upper(), f, 950)[:3]:
        y = _center(d, 540, y, line, f, PURPLE_SOFT)
    d.rectangle([440, y + 36, 640, y + 52], fill=PURPLE)
    return img


def paint_cta_card(band: str, scene: dict, seed: int) -> Image.Image:
    img = Image.new("RGB", (1080, 1920), INK)
    glow = _glow((1080, 1920), (540, 720), 340, PURPLE, 32)
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)
    _band(d, 1080, band)
    _mono_pair(d, 1080, 1760, 1.0, scene, seed + 5)

    f = font("display", 112)
    y = 620
    for line in _wrap(d, "subscribe for more", f, 950)[:3]:
        y = _center(d, 540, y, line, f, WHITE)
    for line in _wrap(d, "tips like this", f, 950)[:2]:
        y = _center(d, 540, y, line, f, PURPLE_SOFT)
    d.rounded_rectangle([320, y + 60, 760, y + 180], radius=56, fill=PURPLE)
    sf = font("card", 58)
    _center(d, 540, y + 104, "SUBSCRIBE", sf, WHITE)
    return img


# ── dispatcher used by the renderer ──────────────────────────────────

def save_scene(scene: dict, seed: int, out_path: Path) -> None:
    kind = scene.get("image", {}).get("kind", "couple_scene")
    if kind == "topic_card":
        img = paint_topic_card(scene["image"]["topic"],
                               scene["image"].get("band", ""),
                               scene["image"].get("count", 8), seed)
    elif kind == "concept_card":
        img = paint_concept_card(scene["image"]["tip"],
                                 scene["image"].get("total", 8),
                                 scene["image"].get("term", ""),
                                 scene["image"].get("headline", ""), seed)
    elif kind == "outro_card":
        img = paint_outro_card(scene["image"].get("topic", "love"), seed)
    else:  # couple_scene
        img = paint_couple_scene(scene["image"], seed)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
