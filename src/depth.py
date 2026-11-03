"""THE DEPTH ENGINE — batch-4 (2026-11-01): the 2.5D upgrade.

Before this module every card was one flat painting that swayed: the
background, the couple and the floor all sat in the same plane, and
the only depth cues were a vignette and a static shadow ellipse. The
owner unlocked the visual settings and asked for real depth, real
movement, a 3D feel — this module is that answer, built entirely from
free knowledge harvested in the great skills batch:

  * PARALLAX — RETIRED 2026-11-03 (owner directive: "the camera must
    not move — no pan, no zoom, I want normal"). The two-plane split
    STAYS (it carries the depth-of-field blur) but the far plane no
    longer counter-moves: _PARALLAX_X/_PARALLAX_Y are zeroed, so the
    world is a locked tripod and the only motion left is the
    characters themselves. The floor and the text NEVER moved and
    still don't (feet planted, text is sacred).
  * DEPTH OF FIELD (premium / design-taste-frontend craft) — the far
    plane bakes once with a soft Gaussian blur while the couple stays
    razor sharp: the instant 'shot on a real camera' cue.
  * LIVING AIR (algorithmic-art particle doctrine) — seeded dust
    motes in three depth bands: far dim specks BEHIND the couple,
    mid motes around them, a few soft near motes in front. The air
    of the room finally moves.
  * VOLUMETRIC LIGHT (glassmorphism's luminous-border idea, moved
    into the scene) — room scenes get a soft light shaft from a
    seeded upper corner that shimmers on a slow integer cycle.
  * GROUNDED SHADOWS — the contact shadow is no longer a static
    ellipse baked into the floor: it follows the hips (shifts with
    the sway, stretches a touch at the weight-shift extreme), so
    the couple's weight reads as REAL on the ground plane.

SEAM LAW (inherited from anim.py, never broken): every per-frame
term is periodic with an INTEGER cycle count over the loop T, so
frame(T) == frame(0) exactly and encoded loops never jump.

FAIL-OPEN LAW (inherited from the muse): any exception in this
module collapses the frame to the pre-batch-4 composition path —
the machine can never die because of depth.

Gates (channel.yaml -> video):
  depth:  parallax | legacy      (default parallax — but with the
                                 parallax COUNTER-MOVE zeroed: the
                                 two-plane world is static, only its
                                 atmosphere lives)
  motes:  true | false           (default true)
  shaft:  shimmer | static | off (default shimmer, room scenes only)

The couple's APPEARANCE stays untouched — faces, proportions,
palette. Depth changes where the world SITS, not how it looks.
"""
from __future__ import annotations

import math
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter

# ── constants ─────────────────────────────────────────────────────────
_PAD = 10            # overscan margin on the far plane (px)
# 2026-11-03 owner directive — THE CAMERA NEVER MOVES: no pan left/
# right, no zoom, no push-in. The far-plane counter-move (the old
# 0.90/0.22 tracked-shot parallax) is zeroed; the overscan canvas and
# the clamp math below stay intact (harmless at 0, one-line rollback
# if the doctrine is ever reversed).
_PARALLAX_X = 0.0    # far counter-move vs the hip sway — LOCKED
_PARALLAX_Y = 0.0    # far counter-move vs the breathing bob — LOCKED
_MAX_DX, _MAX_DY = 8, 4
_MOTE_COLOR = (250, 244, 226)      # warm dust, matches PAPER
_SHAFT_COLOR = (255, 246, 216)     # warm light
_SHAFT_LEVELS = 5                  # shimmer = paste one of 5 alphas


# ── gates (fail-open, config never required) ─────────────────────────

def enabled() -> bool:
    try:
        from .config import cfg
        return cfg().get("video", {}).get("depth", "parallax") == "parallax"
    except Exception:
        return True


def motes_on() -> bool:
    try:
        from .config import cfg
        return bool(cfg().get("video", {}).get("motes", True))
    except Exception:
        return True


def shaft_mode() -> str:
    try:
        from .config import cfg
        return str(cfg().get("video", {}).get("shaft", "shimmer"))
    except Exception:
        return "shimmer"


# ── the per-card split (lazy, memoized on the layers dict) ───────────

def _floor_y(layers: dict) -> int:
    """The ground plane: the highest sprite feet, minus the shadow
    halo, clamped inside the frame."""
    h = layers["size"][1]
    feet = [sp.get("feet_y", h) for sp in layers.get("sprites", [])]
    y = min(feet) if feet else int(h * 0.885)
    return max(1, min(int(y) + 2, h - 1))


def prepare(layers: dict) -> None:
    """Split the FINAL baked bg (band and all — builders mutate bg
    before the animator ever runs) into two depth planes:

      bg_far   — overscan canvas, Gaussian-blurred between the top
                 crisp strip (band/chip: text never blurs, never
                 moves) and the floor line (pasted crisp under the
                 floor crop anyway)
      bg_floor — the crisp ground strip, composited at a FIXED
                 position every frame

    Plus the seeded motes and (room scenes) the light-shaft alpha
    ladder. Idempotent: runs once per card, memoized as
    layers["depth"]."""
    if layers.get("depth") is not None or "bg" not in layers:
        return
    bg = layers["bg"]
    if bg.mode != "RGB":
        bg = bg.convert("RGB")
    w, h = bg.size
    top = int(layers.get("depth_top", 200 if h > w else 260))
    floor_y = _floor_y(layers)

    # far plane: blurred world on an overscan canvas
    blurred = bg.filter(ImageFilter.GaussianBlur(3.2))
    far = Image.new("RGB", (w + 2 * _PAD, h + 2 * _PAD), tuple(bg.getpixel((2, 2))))
    far.paste(blurred, (_PAD, _PAD))
    # crisp paste-backs: the top strip (band text) and — kept for
    # safety under the floor crop — the bottom strip
    if top > 0:
        far.paste(bg.crop((0, 0, w, top)), (_PAD, _PAD))
    far.paste(bg.crop((0, floor_y, w, h)), (_PAD, _PAD + floor_y))

    from .rng import FactoryRNG
    r = FactoryRNG(layers.get("depth_seed", 0) + 977)

    depth = {
        "far": far,
        "floor": bg.crop((0, floor_y, w, h)),
        "floor_y": floor_y,
        "motes": _build_motes(r, w, h),
        "shaft": _build_shaft(r, layers, w, h) if layers.get("depth_kind") == "room"
                 else None,
    }
    layers["depth"] = depth


# ── motes — the living air ────────────────────────────────────────────
# Three bands. Band 0/1 composite BEFORE the couple (behind / around),
# band 2 after (in front). Every drift is sin(2*pi*INT*u + phase).

def _mote_sprite(radius: int, alpha: int) -> Image.Image:
    s = radius * 6
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([s / 2 - radius, s / 2 - radius, s / 2 + radius, s / 2 + radius],
              fill=_MOTE_COLOR + (alpha,))
    return img.filter(ImageFilter.GaussianBlur(radius * 0.9))


_MOTE_BANDS = (          # (count, r_lo, r_hi, alpha, drift_lo, drift_hi)
    (14, 2, 3, 34, 6, 16),     # far: dim specks, slow
    (10, 4, 5, 42, 10, 24),    # mid: around the couple
    (6, 6, 9, 30, 14, 32),     # near: soft bokeh in front
)


def _build_motes(r, w: int, h: int) -> list[dict]:
    motes: list[dict] = []
    for band, (n, rlo, rhi, alpha, dlo, dhi) in enumerate(_MOTE_BANDS):
        for _ in range(n):
            motes.append({
                "band": band,
                "spr": _mote_sprite(int(r.between(rlo, rhi)), alpha),
                "x": r.between(0.02, 0.98) * w,
                "y": r.between(0.06, 0.94) * h,
                "ax": r.between(dlo, dhi),
                "ay": r.between(dlo * 0.5, dhi * 0.5),
                "cyc": r.pick([1, 1, 2]),          # integer — seam law
                "ph": r.between(0.0, 2.0 * math.pi),
            })
    return motes


def _draw_motes(img: Image.Image, motes: list[dict], band: int,
                t: float, T: float) -> None:
    if not motes:
        return
    two_pi = 2.0 * math.pi
    u = t / T
    for m in motes:
        if m["band"] != band:
            continue
        x = m["x"] + m["ax"] * math.sin(two_pi * m["cyc"] * u + m["ph"])
        y = m["y"] + m["ay"] * math.sin(two_pi * m["cyc"] * u + m["ph"] * 1.7)
        spr = m["spr"]
        img.paste(spr, (int(x - spr.width / 2), int(y - spr.height / 2)), spr)


# ── the light shaft (room scenes only) ────────────────────────────────

def _build_shaft(r, layers: dict, w: int, h: int) -> Optional[list]:
    if shaft_mode() == "off":
        return None
    # seeded presence: not every room needs a shaft (60%)
    if not r.chance(0.60):
        return None
    left = r.chance(0.5)
    x_top = r.between(0.06, 0.22) * w if left else r.between(0.78, 0.94) * w
    x_bot = x_top + (r.between(0.42, 0.62) * w if left else -r.between(0.42, 0.62) * w)
    span = r.between(0.10, 0.16) * w
    poly = [(x_top - span * 0.35, 0), (x_top + span * 0.65, 0),
            (x_bot + span * 0.65, h), (x_bot - span * 0.35, h)]
    one = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(one)
    d.polygon(poly, fill=_SHAFT_COLOR + (48,))
    one = one.filter(ImageFilter.GaussianBlur(span * 0.45))
    if shaft_mode() == "static":
        return [one]
    # shimmer ladder: alpha scaled 0.55x .. 1.45x around the base
    ladder = []
    for i in range(_SHAFT_LEVELS):
        k = 0.55 + (1.45 - 0.55) * i / (_SHAFT_LEVELS - 1)
        a = one.getchannel("A").point(lambda v, k=k: int(v * k))
        var = one.copy()
        var.putalpha(a)
        ladder.append(var)
    return ladder


def _paste_shaft(img: Image.Image, shaft, t: float, T: float) -> None:
    if not shaft:
        return
    if len(shaft) == 1:
        ov = shaft[0]
    else:
        u = t / T
        idx = int(round((_SHAFT_LEVELS - 1) / 2
                        * (1.0 + math.sin(2.0 * math.pi * u))))
        ov = shaft[max(0, min(_SHAFT_LEVELS - 1, idx))]
    img.paste(ov, (0, 0), ov)


# ── the grounded, rig-aware contact shadow ────────────────────────────

def draw_shadow(dr: ImageDraw.ImageDraw, x: float, feet_y: float,
                s: float, mono: bool, hip_dx: float = 0.0,
                sway: float = 0.0) -> None:
    """The old static ellipse, now ALIVE: shifts with the hips and
    stretches ~16% at the weight-shift extreme. sway is the raw
    normalized hip sinusoid (-1..1); hip_dx its pixel amplitude."""
    dx = hip_dx * 0.9
    stretch = 1.0 + 0.16 * abs(sway)
    w = 70 * s * stretch
    col = (24, 24, 36) if mono else (216, 210, 198)
    dr.ellipse([x + dx - w, feet_y - 16 * s,
                x + dx + w, feet_y + 14 * s], fill=col)


# ── the frame assembly (called from anim.compose_frame) ───────────────

def world_base(layers: dict, params: list[dict], t: float,
               T: float) -> Image.Image:
    """The world UNDER the couple: parallax far plane + fixed floor +
    far motes + shaft + dynamic contact shadows. Characters, near
    motes and the text layer land on top (anim.compose_frame)."""
    prepare(layers)
    dep = layers["depth"]
    w, h = layers["size"]

    # parallax driver: the couple's average hip sway / breathing bob
    hip_dx = bob_dy = 0.0
    sway = 0.0
    n = 0
    for prm in params:
        rg = prm.get("rig")
        if rg:
            u = t / T
            sw = math.sin(2.0 * math.pi * rg["hip_cyc"] * u + rg["hip_phase"])
            hip_dx += rg["hip_amp"] * sw
            sway += sw
            bob_dy += rg["bob_a"] * math.sin(
                2.0 * math.pi * rg["bob_cyc"] * u + rg["bob_phase"])
            n += 1
        else:                      # legacy sprite params
            hip_dx += prm["sway_a"] * math.sin(
                2.0 * math.pi * prm["sway_cyc"] * t / T + prm["phase"])
            bob_dy += prm["bob_a"] * math.sin(
                2.0 * math.pi * prm["bob_cyc"] * t / T + prm["bob_phase"])
            n += 1
    if n:
        hip_dx /= n
        bob_dy /= n
        sway /= n
    px = max(-_MAX_DX, min(_MAX_DX, -round(_PARALLAX_X * hip_dx)))
    py = max(-_MAX_DY, min(_MAX_DY, -round(_PARALLAX_Y * bob_dy)))

    img = Image.new("RGB", (w, h))
    # far is an overscan canvas (w+2P, h+2P); pasting at (px-P, py-P)
    # keeps the whole frame covered for |px| <= P while the content
    # counter-moves by exactly (px, py) against the couple's sway.
    img.paste(dep["far"], (px - _PAD, py - _PAD))
    img.paste(dep["floor"], (0, dep["floor_y"]))

    dr = None
    if motes_on():
        _draw_motes(img, dep["motes"], 0, t, T)
    _paste_shaft(img, dep.get("shaft"), t, T)

    # rig-aware contact shadows (only where builders recorded them)
    shadows = layers.get("shadows")
    if shadows:
        if dr is None:
            dr = ImageDraw.Draw(img)
        for i, sh in enumerate(shadows):
            hip = hip_dx * (1.0 if i == 0 else 0.92)
            draw_shadow(dr, sh["x"], sh["y"], sh["s"], sh.get("mono", False),
                        hip_dx=hip, sway=sway)
    return img


def foreground(img: Image.Image, layers: dict, t: float, T: float) -> None:
    """Everything that sits IN FRONT OF or AROUND the couple: the mid
    and near mote bands (alpha stays low — atmosphere, never noise)."""
    dep = layers.get("depth")
    if dep is None:
        return
    if motes_on():
        _draw_motes(img, dep["motes"], 1, t, T)
        _draw_motes(img, dep["motes"], 2, t, T)
