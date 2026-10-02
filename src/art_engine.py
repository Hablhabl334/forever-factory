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

# ── THE LOCKED COUPLE ─────────────────────────────────────────────────
# One pair, one design, every video, forever. The audience learns
# their faces the way they learn a channel's host. Appearance is
# FIXED — only emotions, poses and idle motion change per video.
LOCKED_COUPLE = {
    "a": {   # her — warm brunette, plum top
        "skin": (242, 212, 178), "hair": (58, 42, 50),
        "top": (150, 84, 118), "pants": (74, 66, 80),
        "hair_style": "long", "iris": (96, 56, 42),
        "blush": (246, 168, 150),
    },
    "b": {   # him — dark short hair, teal top
        "skin": (226, 186, 146), "hair": (44, 36, 42),
        "top": (84, 116, 128), "pants": (58, 62, 78),
        "hair_style": "short", "iris": (90, 108, 130),
        "blush": (240, 158, 138),
    },
}

# emotion → richer peak variants (seeded per video: faces vary too)
_PEAKS = {
    "happy": ["happy", "inlove"],
    "sad": ["sad", "crying"],
    "neutral": ["neutral", "thinking", "shy"],
    "surprised": ["surprised", "hopeful"],
    "smug": ["smug", "thinking"],
    "anxious": ["anxious", "shy"],
    "detached": ["detached", "tired"],
    "annoyed": ["annoyed"],
    "tired": ["tired"],
    "inlove": ["inlove"], "crying": ["crying"], "shy": ["shy"],
    "thinking": ["thinking"], "hopeful": ["hopeful"],
}


def vary_emotion(seed: int, emotion: str, slot: int) -> str:
    """Seeded emotion intensity pass — richer face variety per video."""
    from .rng import FactoryRNG
    opts = _PEAKS.get(emotion, [emotion])
    return FactoryRNG(seed + slot * 977).pick(opts)

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

# emotions whose resting eyes are not wide open
_HALF_EYES = {"tired", "detached", "shy"}
_CLOSED_EYES = {"inlove"}


def _eye_state(emotion: str) -> str:
    if emotion in _CLOSED_EYES:
        return "closed"
    if emotion in _HALF_EYES:
        return "half"
    return "open"


def _face(d: ImageDraw.ImageDraw, hx: float, hy: float, s: float,
          emotion: str, facing: int, feature=INK, iris=(96, 56, 42),
          eyes: str = "open", skin=(242, 212, 178),
          blush=(246, 168, 150)) -> None:
    """Face with REAL eyes: white sclera, colored iris, pupil and a
    specular highlight — they look toward the partner, not into the
    void. `eyes` = "open" | "half" | "closed" (blink/lid states)."""
    fx = facing * 12 * s
    eye_y, brow_y, mouth_y = hy - 2 * s, hy - 32 * s, hy + 30 * s
    lx, rx = hx - 24 * s + fx * 0.5, hx + 24 * s + fx * 0.5
    lw = max(3, int(5 * s))

    # gaze: toward the partner; emotional offsets stack on top
    look_x = facing * 4.2 * s
    look_y = 0.0
    if emotion == "shy":
        look_y = 3.2 * s
    elif emotion == "thinking":
        look_x = -facing * 3.0 * s
        look_y = -3.4 * s
    elif emotion == "hopeful":
        look_y = -1.6 * s

    def real_eye(x: float, big: float = 1.0) -> None:
        ew, eh = 15 * s * big, 11.5 * s * big
        if eyes == "closed":
            # soft downward-curved closed lid
            d.arc([x - 13 * s, eye_y - 7 * s, x + 13 * s, eye_y + 8 * s],
                  195, 345, fill=feature, width=lw)
            return
        if eyes == "half":
            # sclera with a heavy upper lid (sleepy / guarded / shy)
            d.ellipse([x - ew, eye_y - eh, x + ew, eye_y + eh],
                      fill=(250, 248, 244))
            d.ellipse([x - ew, eye_y + eh * 0.15, x + ew, eye_y + eh],
                      fill=skin)
            cx, cy = x + look_x * 0.7, eye_y + look_y * 0.7 + eh * 0.25
            r = 7.2 * s
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=iris)
            d.ellipse([cx - 3.2 * s, cy - 3.2 * s, cx + 3.2 * s, cy + 3.2 * s],
                      fill=feature)
            d.ellipse([cx - 3.6 * s, cy - 5.2 * s, cx - 1.0 * s, cy - 2.6 * s],
                      fill=WHITE)
            d.line([x - 12 * s, eye_y - eh * 0.82, x + 12 * s, eye_y - eh * 0.82],
                   fill=feature, width=lw)
            return
        # open: white sclera + iris + pupil + highlight
        d.ellipse([x - ew, eye_y - eh, x + ew, eye_y + eh], fill=(250, 248, 244))
        cx, cy = x + look_x, eye_y + look_y
        r = 7.8 * s * big
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=iris)
        d.ellipse([cx - 3.6 * s, cy - 3.6 * s, cx + 3.6 * s, cy + 3.6 * s],
                  fill=feature)
        # the sparkle that makes it a living eye
        d.ellipse([cx - 3.8 * s, cy - 5.6 * s, cx - 1.0 * s, cy - 2.8 * s],
                  fill=WHITE)
        d.ellipse([cx + 0.6 * s, cy + 1.2 * s, cx + 2.2 * s, cy + 2.8 * s],
                  fill=WHITE)
        # gentle upper-lid line
        d.arc([x - ew - 1 * s, eye_y - eh - 2 * s, x + ew + 1 * s, eye_y + eh],
              205, 335, fill=feature, width=max(2, int(2.6 * s)))

    def dot_eye(x: float, r: float = 6.5) -> None:
        if eyes == "closed":
            d.arc([x - 11 * s, eye_y - 6 * s, x + 11 * s, eye_y + 7 * s],
                  195, 345, fill=feature, width=lw)
        else:
            d.ellipse([x - r * s, eye_y - r * s, x + r * s, eye_y + r * s],
                      fill=feature)

    def lid_line(x: float) -> None:
        d.line([x - 11 * s, eye_y, x + 11 * s, eye_y], fill=feature, width=lw)

    def brow(x, inner_up: float):
        nx = hx + (x - hx) * 0.45 + fx * 0.5
        d.line([x - 14 * s, brow_y - (2 if inner_up > 0 else -2) * s,
                nx, brow_y - inner_up * s], fill=feature, width=lw)

    def blush_pair() -> None:
        d.ellipse([lx - 22 * s, hy + 12 * s, lx - 6 * s, hy + 22 * s], fill=blush)
        d.ellipse([rx + 6 * s, hy + 12 * s, rx + 22 * s, hy + 22 * s], fill=blush)

    mono_eye = iris is None

    if emotion == "happy":
        if mono_eye:
            dot_eye(lx), dot_eye(rx)
        else:
            real_eye(lx), real_eye(rx)
        brow(lx, 6), brow(rx, 6)
        d.arc([hx - 16 * s + fx, mouth_y - 10 * s, hx + 16 * s + fx,
               mouth_y + 10 * s], 15, 165, fill=feature, width=lw)
        blush_pair()
    elif emotion == "inlove":
        # happy closed-arc eyes (∩) — the smitten look
        for x in (lx, rx):
            d.arc([x - 12 * s, eye_y - 6 * s, x + 12 * s, eye_y + 9 * s],
                  15, 165, fill=feature, width=lw)
        brow(lx, 7), brow(rx, 7)
        d.arc([hx - 17 * s + fx, mouth_y - 10 * s, hx + 17 * s + fx,
               mouth_y + 12 * s], 10, 170, fill=feature, width=lw)
        blush_pair()
    elif emotion == "sad":
        if mono_eye:
            dot_eye(lx), dot_eye(rx)
        else:
            real_eye(lx), real_eye(rx)
        brow(lx, -8), brow(rx, -8)
        d.arc([hx - 16 * s + fx, mouth_y - 2 * s, hx + 16 * s + fx,
               mouth_y + 20 * s], 195, 345, fill=feature, width=lw)
    elif emotion == "crying":
        if mono_eye:
            dot_eye(lx), dot_eye(rx)
        else:
            real_eye(lx), real_eye(rx)
        brow(lx, -10), brow(rx, -10)
        d.arc([hx - 16 * s + fx, mouth_y - 2 * s, hx + 16 * s + fx,
               mouth_y + 20 * s], 195, 345, fill=feature, width=lw)
        # tear streaks
        for x in (lx, rx):
            d.polygon([(x - 9 * s, eye_y + 10 * s), (x + 3 * s, eye_y + 10 * s),
                       (x - 5 * s, eye_y + 26 * s)], fill=(126, 168, 208))
            d.polygon([(x - 6 * s, eye_y + 22 * s), (x + 4 * s, eye_y + 22 * s),
                       (x - 2 * s, eye_y + 34 * s)], fill=(150, 188, 222))
    elif emotion == "anxious":
        if mono_eye:
            dot_eye(lx, 9), dot_eye(rx, 9)
        else:
            real_eye(lx, 1.12), real_eye(rx, 1.12)
        brow(lx, 10), brow(rx, 10)
        d.ellipse([hx - 8 * s + fx, mouth_y - 3 * s, hx + 8 * s + fx,
                   mouth_y + 11 * s], fill=feature)
    elif emotion == "detached":
        if mono_eye:
            lid_line(lx), lid_line(rx)
        else:
            real_eye(lx), real_eye(rx)   # eyes="half" from _eye_state
        brow(lx, 0), brow(rx, 0)
        d.line([hx - 11 * s + fx, mouth_y, hx + 11 * s + fx, mouth_y],
               fill=feature, width=lw)
    elif emotion == "annoyed":
        if mono_eye:
            dot_eye(lx), dot_eye(rx)
        else:
            real_eye(lx), real_eye(rx)
        brow(lx, -10), brow(rx, -10)
        d.arc([hx - 13 * s + fx, mouth_y - 5 * s, hx + 13 * s + fx,
               mouth_y + 10 * s], 200, 340, fill=feature, width=lw)
    elif emotion == "surprised":
        if mono_eye:
            dot_eye(lx, 10), dot_eye(rx, 10)
        else:
            real_eye(lx, 1.18), real_eye(rx, 1.18)
        brow(lx, 12), brow(rx, 12)
        d.ellipse([hx - 9 * s + fx, mouth_y - 4 * s, hx + 9 * s + fx,
                   mouth_y + 13 * s], fill=feature)
    elif emotion == "hopeful":
        if mono_eye:
            dot_eye(lx, 9), dot_eye(rx, 9)
        else:
            real_eye(lx, 1.08), real_eye(rx, 1.08)
        brow(lx, 8), brow(rx, 8)
        d.arc([hx - 14 * s + fx, mouth_y - 8 * s, hx + 14 * s + fx,
               mouth_y + 10 * s], 20, 160, fill=feature, width=lw)
    elif emotion == "tired":
        if mono_eye:
            lid_line(lx), lid_line(rx)
        else:
            real_eye(lx), real_eye(rx)   # eyes="half"
        brow(lx, -4), brow(rx, -4)
        d.line([hx - 10 * s + fx, mouth_y, hx + 10 * s + fx, mouth_y],
               fill=feature, width=lw)
    elif emotion == "smug":
        if mono_eye:
            lid_line(lx), lid_line(rx)
        else:
            real_eye(lx), real_eye(rx)
        brow(lx, 5), brow(rx, -5)
        d.arc([hx - 18 * s + fx, mouth_y - 12 * s, hx + 10 * s + fx,
               mouth_y + 8 * s], 20, 160, fill=feature, width=lw)
    elif emotion == "shy":
        if mono_eye:
            lid_line(lx), lid_line(rx)
        else:
            real_eye(lx), real_eye(rx)   # eyes="half", gaze down
        brow(lx, 3), brow(rx, 3)
        d.arc([hx - 12 * s + fx, mouth_y - 6 * s, hx + 12 * s + fx,
               mouth_y + 8 * s], 20, 160, fill=feature, width=lw)
        blush_pair()
    elif emotion == "thinking":
        if mono_eye:
            dot_eye(lx), dot_eye(rx)
        else:
            real_eye(lx), real_eye(rx)   # gaze up-side
        brow(lx, 9), brow(rx, -2)
        d.line([hx - 10 * s + fx, mouth_y + 2 * s, hx + 10 * s + fx,
                mouth_y + 2 * s], fill=feature, width=lw)
    else:  # neutral
        if mono_eye:
            dot_eye(lx), dot_eye(rx)
        else:
            real_eye(lx), real_eye(rx)
        brow(lx, 0), brow(rx, 0)
        d.line([hx - 10 * s + fx, mouth_y, hx + 10 * s + fx, mouth_y],
               fill=feature, width=lw)


def draw_figure(d: ImageDraw.ImageDraw, x: float, feet_y: float,
                s: float, spec: dict, shadow: bool = True) -> None:
    """One flat character, webtoon-lite proportions (s=1 -> ~430px tall).
    spec["eyes"] = "open"|"half"|"closed" selects the eye state;
    pose "away" turns the back of the head to the partner."""
    emotion, pose = spec["emotion"], spec["pose"]
    facing = spec["facing"]
    skin, hair, top, pants = spec["skin"], spec["hair"], spec["top"], spec["pants"]
    mono = spec.get("mono", False)
    eyes = spec.get("eyes", "open")
    if pose == "away":
        facing = 0            # back of the head — turned away

    head_r = 66 * s
    hx, hy = x, feet_y - 404 * s            # head center
    hips_y = feet_y - 172 * s
    torso_top = hips_y - 150 * s
    torso_half = 52 * s

    # ground shadow (grounds the figure) — omit when baked into bg
    if shadow:
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
              feature=PAPER if mono else INK,
              iris=None if mono else spec.get("iris", (96, 56, 42)),
              eyes=eyes, skin=skin, blush=spec.get("blush", (246, 168, 150)))


def _figure_specs(seed: int, ea: str, pa: str, eb: str, pb: str) -> tuple[dict, dict]:
    """The LOCKED channel couple — appearance never changes between
    videos (the audience learns their faces); emotions/poses do."""
    la, lb = LOCKED_COUPLE["a"], LOCKED_COUPLE["b"]
    a = {"emotion": ea, "pose": pa, "facing": 1, "mono": False,
         "skin": la["skin"], "hair": la["hair"], "top": la["top"],
         "pants": la["pants"], "hair_style": la["hair_style"],
         "iris": la["iris"], "blush": la["blush"],
         "eyes": _eye_state(ea)}
    b = {"emotion": eb, "pose": pb, "facing": -1, "mono": False,
         "skin": lb["skin"], "hair": lb["hair"], "top": lb["top"],
         "pants": lb["pants"], "hair_style": lb["hair_style"],
         "iris": lb["iris"], "blush": lb["blush"],
         "eyes": _eye_state(eb)}
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
        f = font("display", int(w * 0.058))
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


# ── sprite + layer system (the animation foundation) ─────────────────
# Cards are now built as LAYERS: a static background (room, band, text,
# vignette — all baked in) plus 1-2 character SPRITES. The animator
# (src/anim.py) offsets the sprites per frame: sway, breathing bob,
# blinks. Characters finally live instead of standing dead still.

def render_character_sprites(spec: dict, s: float) -> dict:
    """One character as three RGBA sprites (eyes open / half / closed),
    feet anchored 16px above the canvas bottom."""
    cw, ch = int(244 * s) + 36, int(505 * s) + 40
    out = {"w": cw, "h": ch, "default": spec.get("eyes", "open"),
           "anchor_x": 0.0, "feet_y": 0.0}
    for state in ("open", "half", "closed"):
        img = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        draw_figure(dr, cw / 2, ch - 16, s, dict(spec, eyes=state),
                    shadow=False)
        out[state] = img
    return out


def _ground_shadow(d, x: float, feet_y: float, s: float,
                   mono: bool = False) -> None:
    d.ellipse([x - 70 * s, feet_y - 16 * s, x + 70 * s, feet_y + 14 * s],
              fill=(22, 22, 32) if mono else (216, 210, 198))


def compose_static(layers: dict) -> Image.Image:
    """Flatten layers into one still image (frame zero — also used by
    thumbnails and any static fallback path)."""
    img = layers["bg"].copy()
    for sp in layers.get("sprites", []):
        spr = sp[sp["default"]]
        img.paste(spr, (int(sp["anchor_x"] - sp["w"] / 2),
                        int(sp["feet_y"] - (sp["h"] - 16))), spr)
    tl = layers.get("text_layer")
    if tl is not None:
        img = Image.alpha_composite(img.convert("RGBA"), tl).convert("RGB")
    return img


def build_couple_layers(spec: dict, seed: int, w: int = 1920, h: int = 1080,
                        zoom: float = 1.0) -> dict:
    """Scene room + the locked couple as movable sprites. Faces get a
    seeded emotion-intensity pass so expressions differ per video."""
    ea = vary_emotion(seed, spec["emotion_a"], 1)
    eb = vary_emotion(seed, spec["emotion_b"], 2)
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    floor_y = int(h * 0.885)
    _scene_room(d, w, h, floor_y, seed + 17)
    s = (1.02 if w >= 1600 else 1.45) * zoom
    ax, bx = w * 0.32, w * 0.68
    feet = floor_y + 6
    _ground_shadow(d, ax, feet, s)
    _ground_shadow(d, bx, feet, s)
    img = _vignette(img)

    a_spec, b_spec = _figure_specs(seed, ea, spec["pose_a"], eb, spec["pose_b"])
    sa = render_character_sprites(a_spec, s)
    sb = render_character_sprites(b_spec, s)
    sa.update({"anchor_x": ax, "feet_y": feet})
    sb.update({"anchor_x": bx, "feet_y": feet})
    return {"bg": img, "sprites": [sa, sb], "text_layer": None,
            "size": (w, h)}


def build_mono_pair_layers(bg: Image.Image, spec: dict, seed: int,
                           w: float, floor_y: float, s: float) -> dict:
    """Attach the mono silhouette couple (ink cards) as sprites."""
    ea = vary_emotion(seed, spec.get("emotion_a", "neutral"), 3)
    eb = vary_emotion(seed, spec.get("emotion_b", "neutral"), 4)
    a, b = _mono_specs(seed, ea, spec.get("pose_a", "stand"),
                       eb, spec.get("pose_b", "stand"))
    d = ImageDraw.Draw(bg)
    ax, bx = w * 0.34, w * 0.66
    _ground_shadow(d, ax, floor_y, s, mono=True)
    _ground_shadow(d, bx, floor_y, s, mono=True)
    sa, sb = render_character_sprites(a, s), render_character_sprites(b, s)
    sa.update({"anchor_x": ax, "feet_y": floor_y})
    sb.update({"anchor_x": bx, "feet_y": floor_y})
    return {"bg": bg, "sprites": [sa, sb], "text_layer": None,
            "size": bg.size}


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


def build_concept_layers(tip: int, total: int, term: str, headline: str,
                         seed: int) -> dict:
    """Long-video concept card: ink bg + glow + mono couple sprites,
    with the headline on a text layer ABOVE them."""
    img = Image.new("RGB", (1920, 1080), INK)
    glow = _glow((1920, 1080), (960, 480), 330, PURPLE, 26)
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)

    chip = font("card", 58)
    label = f"TIP {tip}"
    tw = d.textlength(label, font=chip)
    d.rounded_rectangle([96, 88, 96 + tw + 64, 88 + 96], radius=20, fill=PURPLE)
    d.text((128, 112), label, font=chip, fill=WHITE)

    tf = font("card", 46)
    _center(d, 960, 62, f"PSYCHOLOGISTS CALL THIS:  {term.upper()}", tf, GREY)

    layers = build_mono_pair_layers(
        img, {"emotion_a": "neutral", "pose_a": "stand",
              "emotion_b": "neutral", "pose_b": "stand"},
        seed + 5, 1920, 1030, 0.66)

    # headline on its own transparent layer (drawn OVER the silhouettes)
    tl = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    td = ImageDraw.Draw(tl)
    f = font("card", 100)
    words = headline.split()
    acc = max(words, key=len) if words else ""
    lines, cur, cur_acc = [], [], False
    for wd in words:
        trial = cur + [wd]
        if td.textlength(" ".join(trial), font=f) > 1640 and cur:
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
        tw_line = td.textlength(text, font=f)
        x = 960 - tw_line / 2
        if has_acc and acc in text:
            pre, _, post = text.partition(acc)
            td.text((x, y), pre, font=f, fill=WHITE)
            x2 = x + td.textlength(pre, font=f)
            td.text((x2, y), acc, font=f, fill=PURPLE_SOFT)
            td.text((x2 + td.textlength(acc, font=f), y), post, font=f, fill=WHITE)
        else:
            td.text((x, y), text, font=f, fill=WHITE)
        y += 124
    layers["text_layer"] = tl
    return layers


def paint_concept_card(tip: int, total: int, term: str, headline: str,
                       seed: int) -> Image.Image:
    return compose_static(build_concept_layers(tip, total, term, headline, seed))


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

def _shorts_band(d: ImageDraw.ImageDraw, band: str,
                 part: int | None = None) -> None:
    band_h = 170
    d.rectangle([0, 0, 1080, band_h], fill=INK)
    f_band = font("card", 56)
    label = band.upper()
    while d.textlength(label, font=f_band) > 950:
        label = label[:-1]
    _center(d, 540, 38, label, f_band, WHITE)
    if part is not None:
        pf = font("card", 40)
        _center(d, 540, 104, f"PART {part}", pf, PURPLE_SOFT)


def build_hook_layers(hook: str, band: str, part: int, scene: dict,
                      seed: int) -> dict:
    """Hook = couple scene + huge stroked text (the reference look)."""
    layers = build_couple_layers(scene, seed + 91, 1080, 1920, zoom=1.0)
    d = ImageDraw.Draw(layers["bg"])
    _shorts_band(d, band, part)
    f = font("display", 124)          # was 104 — readable from across the room
    y = 330
    for line in _wrap(d, hook.lower(), f, 930)[:7]:
        y = _center(d, 540, y, line, f, WHITE, stroke=14, stroke_fill=INK)
    return layers


def paint_hook_card(hook: str, band: str, part: int, scene: dict,
                    seed: int) -> Image.Image:
    return compose_static(build_hook_layers(hook, band, part, scene, seed))


def build_scene_card_layers(text: str, band: str, scene: dict,
                            seed: int) -> dict:
    """Body chunk: couple scene + bold stroked overlay + band."""
    layers = build_couple_layers(scene, seed + 91, 1080, 1920, zoom=1.0)
    d = ImageDraw.Draw(layers["bg"])
    _shorts_band(d, band)
    f = font("display", 104)          # was 84 — the karaoke text must POP
    y = 290
    for line in _wrap(d, text.lower(), f, 930)[:9]:
        y = _center(d, 540, y, line, f, WHITE, stroke=12, stroke_fill=INK)
    return layers


def paint_scene_card(text: str, band: str, scene: dict, seed: int) -> Image.Image:
    return compose_static(build_scene_card_layers(text, band, scene, seed))


def build_term_layers(term: str, band: str, scene: dict, seed: int) -> dict:
    img = Image.new("RGB", (1080, 1920), INK)
    glow = _glow((1080, 1920), (540, 700), 330, PURPLE, 34)
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)
    _band(d, 1080, band)

    f0 = font("card", 52)
    _center(d, 540, 560, "psychologists call this", f0, GREY)
    f = font("display", 148)
    y = 680
    for line in _wrap(d, term.upper(), f, 950)[:3]:
        y = _center(d, 540, y, line, f, PURPLE_SOFT)
    d.rectangle([440, y + 36, 640, y + 52], fill=PURPLE)
    return build_mono_pair_layers(img, scene, seed + 5, 1080, 1780, 1.15)


def paint_term_card(term: str, band: str, scene: dict, seed: int) -> Image.Image:
    return compose_static(build_term_layers(term, band, scene, seed))


def build_cta_layers(band: str, scene: dict, seed: int) -> dict:
    img = Image.new("RGB", (1080, 1920), INK)
    glow = _glow((1080, 1920), (540, 720), 340, PURPLE, 32)
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)
    _band(d, 1080, band)

    f = font("display", 112)
    y = 620
    for line in _wrap(d, "subscribe for more", f, 950)[:3]:
        y = _center(d, 540, y, line, f, WHITE)
    for line in _wrap(d, "tips like this", f, 950)[:2]:
        y = _center(d, 540, y, line, f, PURPLE_SOFT)
    d.rounded_rectangle([320, y + 60, 760, y + 180], radius=56, fill=PURPLE)
    sf = font("card", 58)
    _center(d, 540, y + 104, "SUBSCRIBE", sf, WHITE)
    return build_mono_pair_layers(img, scene, seed + 5, 1080, 1760, 1.0)


def paint_cta_card(band: str, scene: dict, seed: int) -> Image.Image:
    return compose_static(build_cta_layers(band, scene, seed))


# ── dispatcher used by the renderer ──────────────────────────────────

def build_scene_layers(scene: dict, seed: int) -> dict:
    """Layer dispatcher for the long-video renderer: animated kinds get
    sprites, static kinds fall back to the PNG path."""
    im = scene.get("image", {})
    kind = im.get("kind", "couple_scene")
    if kind == "concept_card":
        return build_concept_layers(im["tip"], im.get("total", 8),
                                    im.get("term", ""),
                                    im.get("headline", ""), seed)
    if kind == "couple_scene":
        return build_couple_layers(im, seed, 1920, 1080)
    return None   # static card (topic/outro/end) — use the PNG path


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
