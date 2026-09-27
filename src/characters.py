"""Procedural storybook characters — pure Pillow, zero APIs.

Each animal is drawn from geometry (ellipses, rounded polygons) in a flat,
soft storybook style: a warm body color, a lighter belly, dark outline
strokes, dot eyes. Poses are intentionally minimal and iconic so they stay
readable at YouTube sizes and never look uncanny.
"""
from __future__ import annotations

from PIL import ImageDraw

# body / belly / outline per hero base
FUR = {
    "hare":      ("#e8e4dc", "#f6f2ea", "#5a544a"),
    "rabbit":    ("#dcd2c4", "#f0e8dc", "#54483a"),
    "fox":       ("#e08a4a", "#f6dcc0", "#6a3a1a"),
    "owl":       ("#a89a88", "#e0d4c0", "#4a4038"),
    "bear":      ("#a87850", "#dcc0a0", "#4a3018"),
    "mouse":     ("#b0a8a0", "#e0dcd4", "#4a443c"),
    "hedgehog":  ("#c0a078", "#e8d8c0", "#4a3820"),
    "cat":       ("#9aa0ac", "#d8dce4", "#383c48"),
    "duck":      ("#f0d878", "#faf0c8", "#8a7020"),
    "turtle":    ("#7a9a6a", "#d0e0c0", "#2a4020"),
    "deer":      ("#d0b088", "#f0e4d0", "#6a4a28"),
    "squirrel":  ("#c07850", "#f0d0b0", "#5a3018"),
    "wolf":      ("#8a90a0", "#c8ccd8", "#3a4050"),
    "frog":      ("#7ab060", "#d0e8b8", "#2a5020"),
    "snail":     ("#c8a070", "#ead8b0", "#503820"),
    "otter":     ("#8a6848", "#d0b888", "#3a2818"),
    "seal":      ("#d8dce4", "#f4f6f8", "#4a505c"),
    "bird":      ("#7a9ac8", "#d0e0f0", "#283850"),
    "ladybug":   ("#d84848", "#f0c060", "#501818"),
    "beaver":    ("#8a6848", "#cbb090", "#3a2818"),
    "moth":      ("#c0b8d0", "#eee8f8", "#4a4460"),
    "pony":      ("#a89078", "#e0d4c0", "#4a3a28"),
}

# companion nouns -> base shape (fallback: glow)
COMPANION_BASE = {
    "owl": "owl", "turtle": "turtle", "fox": "fox", "mouse": "mouse",
    "badger": "bear", "goose": "duck", "heron": "bird", "cricket": "ladybug",
    "moth": "moth", "star": "star", "cloud": "cloud", "fireflies": "fireflies",
    "wind": "wind", "brok": "duck", "beaver": "beaver", "spider": "ladybug",
    "echo": "wind", "stone giant": "cloud", "lantern-keeper": "moth",
    "frog": "frog", "snail": "snail", "seal": "seal", "cat": "cat",
    "duck": "duck", "bird": "bird", "hare": "hare", "deer": "deer",
}


def _r(draw: ImageDraw.ImageDraw, box, fill, outline=None, width=0):
    draw.ellipse(box, fill=fill, outline=outline, width=max(1, int(width)))


def draw_character(draw, base: str, cx: float, cy: float, size: float,
                   pose: str = "sit", tint: tuple | None = None):
    """Draw a storybook animal centered at (cx, cy) — cy is ground contact.

    size = approximate total height in pixels. Supersampled canvas assumed.
    """
    body, belly, line = FUR.get(base, FUR["hare"])
    if tint:
        body = _mix(body, tint, 0.35)
        belly = _mix(belly, tint, 0.25)
    s = size
    draw_ = draw

    if base in ("hare", "rabbit"):
        _hare(draw_, cx, cy, s, body, belly, line, pose)
    elif base == "fox":
        _fox(draw_, cx, cy, s, body, belly, line, pose)
    elif base == "owl":
        _owl(draw_, cx, cy, s, body, belly, line)
    elif base in ("bear", "badger"):
        _bear(draw_, cx, cy, s, body, belly, line, pose)
    elif base in ("mouse", "dormouse"):
        _mouse(draw_, cx, cy, s, body, belly, line, pose)
    elif base == "hedgehog":
        _hedgehog(draw_, cx, cy, s, body, belly, line)
    elif base in ("cat", "wolf"):
        _cat(draw_, cx, cy, s, body, belly, line, pose)
    elif base in ("duck", "goose", "bird", "heron"):
        _birdlike(draw_, cx, cy, s, body, belly, line, base)
    elif base == "turtle":
        _turtle(draw_, cx, cy, s, body, belly, line)
    elif base == "deer":
        _deer(draw_, cx, cy, s, body, belly, line, pose)
    elif base in ("squirrel", "beaver", "otter"):
        _chubby(draw_, cx, cy, s, body, belly, line, pose, tail="paddle" if base == "beaver" else "bushy")
    elif base == "frog":
        _frog(draw_, cx, cy, s, body, belly, line)
    elif base == "snail":
        _snail(draw_, cx, cy, s, body, belly, line)
    elif base == "seal":
        _seal(draw_, cx, cy, s, body, belly, line)
    elif base == "pony":
        _pony(draw_, cx, cy, s, body, belly, line, pose)
    elif base in ("moth", "ladybug"):
        _bug(draw_, cx, cy, s, body, belly, line, base)
    else:
        _hare(draw_, cx, cy, s, body, belly, line, pose)


# ── individual animals ──────────────────────────────────────────────

def _eyes(draw, x, y, r, line, sleep=False):
    r = max(1, int(r))
    x, y = int(x), int(y)
    if sleep:
        draw.arc((x - r, y - r // 2, x + r, y + r), 200, 340, fill=line, width=max(2, r // 3))
    else:
        _r(draw, (x - r, y - r, x + r, y + r), "#2a2622", None)
        _r(draw, (x - r // 2 - r // 4, y - r // 2 - r // 4, x - r // 2 + r // 4, y - r // 2 + r // 4), "#ffffff", None)


def _hare(draw, cx, cy, s, body, belly, line, pose):
    sleeping = pose == "sleep"
    bw = s * 0.62
    bh = s * 0.48
    body_top = cy - bh if not sleeping else cy - bh * 0.55
    # body
    _r(draw, (cx - bw, body_top, cx + bw, body_top + bh * 2 * (0.6 if sleeping else 1)), body, line, s * 0.02)
    # belly
    _r(draw, (cx - bw * 0.55, body_top + bh * 0.6, cx + bw * 0.55, body_top + bh * (1.5 if sleeping else 1.9)), belly)
    # head
    hr = s * 0.22
    hy = body_top - hr * 0.9 if not sleeping else body_top - hr * 0.2
    _r(draw, (cx - hr, hy - hr, cx + hr, hy + hr), body, line, s * 0.018)
    # long ears
    for ex in (-0.55, 0.45):
        ear = (cx + hr * ex - hr * 0.32, hy - hr * 2.1, cx + hr * ex + hr * 0.32, hy - hr * 0.3)
        _r(draw, ear, body, line, s * 0.015)
        inner = (ear[0] + hr * 0.12, ear[1] + hr * 0.25, ear[2] - hr * 0.12, ear[3] - hr * 0.1)
        _r(draw, inner, "#f2b8c0")
    # face
    _eyes(draw, cx - hr * 0.45, hy, hr * 0.16, line, sleeping)
    _eyes(draw, cx + hr * 0.45, hy, hr * 0.16, line, sleeping)
    _r(draw, (cx - hr * 0.09, hy + hr * 0.28, cx + hr * 0.09, hy + hr * 0.46), line)
    # tail
    _r(draw, (cx + bw * 0.92, body_top + bh * 0.75, cx + bw * 1.25, body_top + bh * 1.05), "#ffffff", line, s * 0.01)
    # paws
    if not sleeping:
        for px in (-bw * 0.55, bw * 0.55):
            _r(draw, (cx + px - s * 0.06, cy - s * 0.12, cx + px + s * 0.06, cy), belly, line, s * 0.008)


def _fox(draw, cx, cy, s, body, belly, line, pose):
    sleeping = pose == "sleep"
    bw, bh = s * 0.60, s * 0.42
    body_top = cy - bh if not sleeping else cy - bh * 0.5
    _r(draw, (cx - bw, body_top, cx + bw, body_top + bh * 2 * (0.62 if sleeping else 1)), body, line, s * 0.02)
    _r(draw, (cx - bw * 0.5, body_top + bh * 0.55, cx + bw * 0.5, body_top + bh * 1.8), belly)
    # bushy tail with white tip
    tw = s * 0.30
    tail_x = cx + bw * 0.95
    _r(draw, (tail_x - tw * 0.4, body_top + bh * 0.1, tail_x + tw, body_top + bh * 1.5), body, line, s * 0.015)
    _r(draw, (tail_x + tw * 0.25, body_top + bh * 0.1, tail_x + tw, body_top + bh * 0.7), "#ffffff")
    # head
    hr = s * 0.21
    hy = body_top - hr * 0.8 if not sleeping else body_top - hr * 0.15
    _r(draw, (cx - hr, hy - hr * 0.85, cx + hr, hy + hr * 1.05), body, line, s * 0.018)
    # pointed ears
    for ex in (-0.8, 0.8):
        tri = [(cx + hr * ex - hr * 0.35, hy - hr * 0.5), (cx + hr * ex, hy - hr * 1.8), (cx + hr * ex + hr * 0.35, hy - hr * 0.5)]
        draw.polygon(tri, fill=body, outline=line, width=max(1, int(s * 0.012)))
    # snout
    draw.polygon([(cx - hr * 0.45, hy + hr * 0.2), (cx + hr * 0.45, hy + hr * 0.2), (cx, hy + hr * 1.0)], fill=belly)
    _r(draw, (cx - hr * 0.1, hy + hr * 0.55, cx + hr * 0.1, hy + hr * 0.75), line)
    _eyes(draw, cx - hr * 0.5, hy, hr * 0.14, line, sleeping)
    _eyes(draw, cx + hr * 0.5, hy, hr * 0.14, line, sleeping)
    if not sleeping:
        for px in (-bw * 0.5, bw * 0.5):
            _r(draw, (cx + px - s * 0.06, cy - s * 0.12, cx + px + s * 0.06, cy), belly, line, s * 0.008)


def _owl(draw, cx, cy, s, body, belly, line):
    bw, bh = s * 0.52, s * 0.62
    body_top = cy - bh * 2 * 0.92
    _r(draw, (cx - bw, body_top, cx + bw, cy), body, line, s * 0.022)
    _r(draw, (cx - bw * 0.62, body_top + bh * 1.0, cx + bw * 0.62, cy - s * 0.04), belly)
    # ear tufts
    for ex in (-0.6, 0.6):
        tri = [(cx + bw * ex - s * 0.05, body_top + s * 0.06), (cx + bw * ex, body_top - s * 0.12), (cx + bw * ex + s * 0.05, body_top + s * 0.06)]
        draw.polygon(tri, fill=body, outline=line, width=max(1, int(s * 0.012)))
    # big eyes
    er = s * 0.13
    for ex in (-0.32, 0.32):
        _r(draw, (cx + bw * ex - er, body_top + s * 0.24 - er, cx + bw * ex + er, body_top + s * 0.24 + er), belly, line, s * 0.01)
        _r(draw, (cx + bw * ex - er * 0.45, body_top + s * 0.24 - er * 0.45, cx + bw * ex + er * 0.45, body_top + s * 0.24 + er * 0.45), "#2a2622")
        _r(draw, (cx + bw * ex - er * 0.12, body_top + s * 0.24 - er * 0.12, cx + bw * ex + er * 0.12, body_top + s * 0.24 + er * 0.12), "#ffffff")
    # beak
    draw.polygon([(cx - s * 0.05, body_top + s * 0.42), (cx + s * 0.05, body_top + s * 0.42), (cx, body_top + s * 0.56)], fill="#e8a83a")
    # wings
    _r(draw, (cx - bw * 1.15, body_top + s * 0.2, cx - bw * 0.7, cy - s * 0.1), _mix(body, "#000000", 0.15), line, s * 0.012)
    _r(draw, (cx + bw * 0.7, body_top + s * 0.2, cx + bw * 1.15, cy - s * 0.1), _mix(body, "#000000", 0.15), line, s * 0.012)
    # feet
    for px in (-0.3, 0.3):
        _r(draw, (cx + bw * px - s * 0.06, cy - s * 0.06, cx + bw * px + s * 0.06, cy), "#e8a83a", line, s * 0.008)


def _bear(draw, cx, cy, s, body, belly, line, pose):
    sleeping = pose == "sleep"
    bw, bh = s * 0.66, s * 0.5
    body_top = cy - bh * 2 * (0.55 if sleeping else 1)
    _r(draw, (cx - bw, body_top, cx + bw, cy), body, line, s * 0.025)
    _r(draw, (cx - bw * 0.55, body_top + bh, cx + bw * 0.55, cy - s * 0.03), belly)
    hr = s * 0.24
    hy = body_top - hr * 0.7 if not sleeping else body_top - hr * 0.1
    _r(draw, (cx - hr, hy - hr * 0.85, cx + hr, hy + hr * 0.95), body, line, s * 0.02)
    # round ears
    for ex in (-0.72, 0.72):
        _r(draw, (cx + hr * ex - hr * 0.4, hy - hr * 1.25, cx + hr * ex + hr * 0.4, hy - hr * 0.45), body, line, s * 0.014)
        _r(draw, (cx + hr * ex - hr * 0.2, hy - hr * 1.05, cx + hr * ex + hr * 0.2, hy - hr * 0.65), belly)
    _r(draw, (cx - hr * 0.3, hy + hr * 0.35, cx + hr * 0.3, hy + hr * 0.75), belly)
    _eyes(draw, cx - hr * 0.45, hy + hr * 0.05, hr * 0.13, line, sleeping)
    _eyes(draw, cx + hr * 0.45, hy + hr * 0.05, hr * 0.13, line, sleeping)
    _r(draw, (cx - hr * 0.1, hy + hr * 0.62, cx + hr * 0.1, hy + hr * 0.78), line)


def _mouse(draw, cx, cy, s, body, belly, line, pose):
    sleeping = pose == "sleep"
    bw, bh = s * 0.42, s * 0.32
    body_top = cy - bh * 2 * (0.6 if sleeping else 1)
    _r(draw, (cx - bw, body_top, cx + bw, cy), body, line, s * 0.018)
    _r(draw, (cx - bw * 0.5, body_top + bh, cx + bw * 0.5, cy - s * 0.02), belly)
    # thin tail
    draw.arc((cx + bw * 0.6, cy - s * 0.30, cx + bw * 2.0, cy + s * 0.1), 200, 330, fill=line, width=max(2, int(s * 0.02)))
    hr = s * 0.2
    hy = body_top - hr * 0.8 if not sleeping else body_top - hr * 0.2
    _r(draw, (cx - hr, hy - hr * 0.9, cx + hr, hy + hr * 0.9), body, line, s * 0.016)
    # big round ears
    for ex in (-0.85, 0.85):
        _r(draw, (cx + hr * ex - hr * 0.55, hy - hr * 1.5, cx + hr * ex + hr * 0.55, hy - hr * 0.4), body, line, s * 0.012)
        _r(draw, (cx + hr * ex - hr * 0.3, hy - hr * 1.25, cx + hr * ex + hr * 0.3, hy - hr * 0.65), "#f2c0c0")
    _eyes(draw, cx - hr * 0.4, hy, hr * 0.14, line, sleeping)
    _eyes(draw, cx + hr * 0.4, hy, hr * 0.14, line, sleeping)
    _r(draw, (cx - hr * 0.08, hy + hr * 0.3, cx + hr * 0.08, hy + hr * 0.44), line)


def _hedgehog(draw, cx, cy, s, body, belly, line):
    bw, bh = s * 0.55, s * 0.38
    body_top = cy - bh * 2 * 0.85
    # spikes: fan of triangles
    import math
    n = 9
    for i in range(n):
        ang = math.pi * (0.15 + 0.7 * i / (n - 1))
        x0 = cx - bw * 0.9 + bw * 1.8 * i / (n - 1)
        y0 = body_top + bh * 0.8
        tipx = x0 + math.cos(ang + math.pi / 2) * 0
        tipy = y0 - s * 0.38 * math.sin(ang * 0.5 + 0.4)
        draw.polygon([(x0 - s * 0.09, y0), (x0 + s * 0.09, y0), (x0, y0 - s * 0.34)], fill=_mix(body, "#3a2a18", 0.4))
    _r(draw, (cx - bw, body_top + bh * 0.4, cx + bw, cy), body, line, s * 0.018)
    _r(draw, (cx - bw * 0.5, body_top + bh * 1.2, cx + bw * 0.5, cy - s * 0.03), belly)
    hr = s * 0.2
    hy = body_top + bh * 0.55
    _r(draw, (cx - bw - hr * 0.9, hy - hr * 0.85, cx - bw + hr * 0.9, hy + hr * 0.9), body, line, s * 0.015)
    _eyes(draw, cx - bw - hr * 0.25, hy - hr * 0.1, hr * 0.15, line)
    _r(draw, (cx - bw - hr * 0.12, hy + hr * 0.3, cx - bw + hr * 0.12, hy + hr * 0.46), line)


def _cat(draw, cx, cy, s, body, belly, line, pose):
    sleeping = pose == "sleep"
    bw, bh = s * 0.56, s * 0.4
    body_top = cy - bh * 2 * (0.55 if sleeping else 1)
    _r(draw, (cx - bw, body_top, cx + bw, cy), body, line, s * 0.022)
    _r(draw, (cx - bw * 0.5, body_top + bh, cx + bw * 0.5, cy - s * 0.03), belly)
    # curved tail
    draw.arc((cx + bw * 0.5, body_top - s * 0.1, cx + bw * 2.2, cy + s * 0.2), 150, 320, fill=body, width=max(3, int(s * 0.07)))
    hr = s * 0.22
    hy = body_top - hr * 0.75 if not sleeping else body_top - hr * 0.1
    _r(draw, (cx - hr, hy - hr * 0.85, cx + hr, hy + hr * 0.9), body, line, s * 0.018)
    for ex in (-0.75, 0.75):
        draw.polygon([(cx + hr * ex - hr * 0.4, hy - hr * 0.35), (cx + hr * ex, hy - hr * 1.5), (cx + hr * ex + hr * 0.4, hy - hr * 0.35)], fill=body, outline=line, width=max(1, int(s * 0.012)))
    _eyes(draw, cx - hr * 0.45, hy + hr * 0.05, hr * 0.15, line, sleeping)
    _eyes(draw, cx + hr * 0.45, hy + hr * 0.05, hr * 0.15, line, sleeping)
    _r(draw, (cx - hr * 0.1, hy + hr * 0.45, cx + hr * 0.1, hy + hr * 0.6), line)


def _birdlike(draw, cx, cy, s, body, belly, line, kind):
    bw, bh = s * 0.5, s * 0.42
    body_top = cy - bh * 2 * 0.9
    _r(draw, (cx - bw, body_top, cx + bw, cy - s * 0.06), body, line, s * 0.02)
    _r(draw, (cx - bw * 0.55, body_top + bh * 0.9, cx + bw * 0.55, cy - s * 0.08), belly)
    hr = s * 0.2
    hy = body_top - hr * 0.35
    _r(draw, (cx - hr, hy - hr, cx + hr, hy + hr), body, line, s * 0.016)
    if kind in ("duck", "goose"):
        draw.polygon([(cx + hr * 0.6, hy), (cx + hr * 1.7, hy + hr * 0.25), (cx + hr * 0.6, hy + hr * 0.5)], fill="#e8a83a")
    elif kind == "heron":
        draw.polygon([(cx + hr * 0.7, hy - hr * 0.1), (cx + hr * 2.2, hy + hr * 0.15), (cx + hr * 0.7, hy + hr * 0.3)], fill="#d8b05a", outline=line, width=1)
    else:
        draw.polygon([(cx + hr * 0.6, hy), (cx + hr * 1.5, hy + hr * 0.2), (cx + hr * 0.6, hr * 0.4 + hy)], fill="#e8a83a")
    _eyes(draw, cx - hr * 0.3, hy - hr * 0.15, hr * 0.14, line)
    _eyes(draw, cx + hr * 0.35, hy - hr * 0.15, hr * 0.14, line)
    # legs
    for px in (-0.3, 0.3):
        draw.line([(cx + bw * px, cy - s * 0.06), (cx + bw * px, cy)], fill=line, width=max(2, int(s * 0.025)))
    # wing
    _r(draw, (cx - bw * 0.95, body_top + bh * 0.3, cx - bw * 0.1, body_top + bh * 1.6), _mix(body, "#000000", 0.12), line, s * 0.01)


def _turtle(draw, cx, cy, s, body, belly, line):
    bw, bh = s * 0.55, s * 0.35
    body_top = cy - bh * 2 * 0.8
    _r(draw, (cx - bw, body_top, cx + bw, cy - s * 0.02), _mix(body, "#4a6a3a", 0.5), line, s * 0.022)
    # shell pattern
    draw.line([(cx - bw * 0.6, body_top + bh), (cx + bw * 0.6, body_top + bh)], fill=line, width=max(2, int(s * 0.015)))
    draw.line([(cx, body_top), (cx, cy - s * 0.02)], fill=line, width=max(2, int(s * 0.015)))
    hr = s * 0.17
    _r(draw, (cx + bw * 0.75 - hr, body_top + bh * 0.2 - hr, cx + bw * 0.75 + hr, body_top + bh * 0.2 + hr), body, line, s * 0.012)
    _eyes(draw, cx + bw * 0.95, body_top + bh * 0.05, hr * 0.2, line)
    for px in (-0.5, 0.35):
        _r(draw, (cx + bw * px - s * 0.08, cy - s * 0.14, cx + bw * px + s * 0.08, cy), body, line, s * 0.01)


def _deer(draw, cx, cy, s, body, belly, line, pose):
    sleeping = pose == "sleep"
    bw, bh = s * 0.5, s * 0.4
    body_top = cy - bh * 2 - s * 0.18 if not sleeping else cy - bh * 1.1
    if not sleeping:
        for px in (-0.55, -0.2, 0.25, 0.6):
            draw.line([(cx + bw * px, body_top + bh * 1.6), (cx + bw * px, cy)], fill=_mix(body, "#000000", 0.25), width=max(3, int(s * 0.05)))
    _r(draw, (cx - bw, body_top, cx + bw, body_top + bh * 2 * (0.75 if sleeping else 1)), body, line, s * 0.02)
    _r(draw, (cx - bw * 0.5, body_top + bh, cx + bw * 0.5, body_top + bh * 1.9), belly)
    # spots
    for i, (sx, sy) in enumerate([(-0.3, 1.25), (0.1, 1.4), (0.4, 1.15), (-0.05, 1.1)]):
        _r(draw, (cx + bw * sx - s * 0.03, body_top + bh * sy - s * 0.03, cx + bw * sx + s * 0.03, body_top + bh * sy + s * 0.03), belly)
    hr = s * 0.18
    hy = body_top - hr * 0.6 if not sleeping else body_top - hr * 0.2
    nx = cx + bw * 0.75
    _r(draw, (nx - hr, hy - hr, nx + hr, hy + hr), body, line, s * 0.014)
    _r(draw, (nx + hr * 0.5, hy - hr * 0.5, nx + hr * 1.4, hy + hr * 0.3), body, line, s * 0.01)  # snout
    # ears
    _r(draw, (nx - hr * 1.2, hy - hr * 0.7, nx - hr * 0.3, hy + hr * 0.1), body, line, s * 0.01)
    _eyes(draw, nx + hr * 0.1, hy - hr * 0.15, hr * 0.15, line, sleeping)


def _chubby(draw, cx, cy, s, body, belly, line, pose, tail="bushy"):
    sleeping = pose == "sleep"
    bw, bh = s * 0.58, s * 0.42
    body_top = cy - bh * 2 * (0.55 if sleeping else 0.95)
    _r(draw, (cx - bw, body_top, cx + bw, cy), body, line, s * 0.022)
    _r(draw, (cx - bw * 0.52, body_top + bh, cx + bw * 0.52, cy - s * 0.03), belly)
    if tail == "paddle":
        draw.rounded_rectangle((cx + bw * 0.9, cy - s * 0.28, cx + bw * 1.9, cy), radius=s * 0.1, fill=_mix(body, "#5a4028", 0.35), outline=line, width=max(1, int(s * 0.012)))
    else:  # bushy squirrel tail
        _r(draw, (cx + bw * 0.8, body_top - s * 0.25, cx + bw * 1.7, body_top + bh * 1.4), body, line, s * 0.015)
    hr = s * 0.2
    hy = body_top - hr * 0.7 if not sleeping else body_top - hr * 0.1
    _r(draw, (cx - hr, hy - hr * 0.9, cx + hr, hy + hr * 0.9), body, line, s * 0.016)
    _r(draw, (cx - hr * 0.4, hy + hr * 0.1, cx + hr * 0.4, hy + hr * 0.55), belly)
    _eyes(draw, cx - hr * 0.35, hy - hr * 0.05, hr * 0.14, line, sleeping)
    _eyes(draw, cx + hr * 0.35, hy - hr * 0.05, hr * 0.14, line, sleeping)
    _r(draw, (cx - hr * 0.08, hy + hr * 0.5, cx + hr * 0.08, hy + hr * 0.62), line)
    _r(draw, (cx - hr * 0.12, hy + hr * 0.68, cx, hy + hr * 0.84), line)
    _r(draw, (cx, hy + hr * 0.68, cx + hr * 0.12, hy + hr * 0.84), line)


def _frog(draw, cx, cy, s, body, belly, line):
    bw, bh = s * 0.6, s * 0.3
    body_top = cy - bh * 2 * 0.9
    _r(draw, (cx - bw, body_top, cx + bw, cy), body, line, s * 0.022)
    _r(draw, (cx - bw * 0.55, body_top + bh * 0.9, cx + bw * 0.55, cy - s * 0.02), belly)
    hr = s * 0.22
    hy = body_top + hr * 0.1
    _r(draw, (cx - hr, hy - hr * 0.9, cx + hr, hy + hr * 0.5), body, line, s * 0.016)
    # eyes on top
    for ex in (-0.55, 0.55):
        _r(draw, (cx + hr * ex - hr * 0.3, hy - hr * 1.35, cx + hr * ex + hr * 0.3, hy - hr * 0.75), body, line, s * 0.012)
        _r(draw, (cx + hr * ex - hr * 0.16, hy - hr * 1.2, cx + hr * ex + hr * 0.16, hy - hr * 0.9), "#2a2622")
    _r(draw, (cx - hr * 0.28, hy + hr * 0.25, cx + hr * 0.28, hy + hr * 0.4), line)


def _snail(draw, cx, cy, s, body, belly, line):
    # shell spiral
    import math
    shell_r = s * 0.42
    scx, scy = cx, cy - shell_r
    draw.ellipse((scx - shell_r, scy - shell_r, scx + shell_r, scy + shell_r), fill=_mix(body, "#8a6038", 0.4), outline=line, width=max(2, int(s * 0.018)))
    for k in range(3):
        rr = shell_r * (0.75 - k * 0.22)
        draw.arc((scx - rr, scy - rr, scx + rr, scy + rr), 90 - k * 120, 330 - k * 120, fill=line, width=max(2, int(s * 0.012)))
    # body
    draw.rounded_rectangle((cx + shell_r * 0.4, cy - s * 0.3, cx + s * 0.85, cy), radius=s * 0.14, fill=body, outline=line, width=max(1, int(s * 0.014)))
    hr = s * 0.13
    _r(draw, (cx + s * 0.72, cy - s * 0.5, cx + s * 0.95, cy - s * 0.28), body, line, s * 0.01)
    # stalk eyes
    for k in (0, 1):
        ex = cx + s * (0.74 + k * 0.12)
        draw.line([(ex, cy - s * 0.45), (ex - s * 0.02, cy - s * 0.66)], fill=line, width=max(2, int(s * 0.02)))
        _r(draw, (ex - s * 0.06, cy - s * 0.72, ex + s * 0.02, cy - s * 0.64), body, line, 1)


def _seal(draw, cx, cy, s, body, belly, line):
    bw, bh = s * 0.72, s * 0.34
    body_top = cy - bh * 2 * 0.7
    draw.rounded_rectangle((cx - bw, body_top, cx + bw, cy), radius=s * 0.2, fill=body, outline=line, width=max(2, int(s * 0.02)))
    _r(draw, (cx - bw * 0.5, body_top + bh * 0.8, cx + bw * 0.5, cy - s * 0.03), belly)
    # tail flippers
    draw.polygon([(cx + bw * 0.9, cy - s * 0.16), (cx + bw * 1.5, cy), (cx + bw * 0.9, cy)], fill=_mix(body, "#000000", 0.12))
    hr = s * 0.19
    hy = body_top + hr * 0.35
    _r(draw, (cx - bw - hr, hy - hr, cx - bw + hr, hy + hr), body, line, s * 0.016)
    _eyes(draw, cx - bw - hr * 0.3, hy - hr * 0.1, hr * 0.16, line)
    _r(draw, (cx - bw - hr * 0.5, hy + hr * 0.35, cx - bw + hr * 0.1, hy + hr * 0.55), line)
    # whiskers
    for k in (0, 1):
        draw.line([(cx - bw - hr * 0.6, hy + hr * 0.2), (cx - bw - hr * 1.3, hy + hr * (0.1 + 0.2 * k))], fill=line, width=1)


def _pony(draw, cx, cy, s, body, belly, line, pose):
    bw, bh = s * 0.58, s * 0.36
    body_top = cy - bh * 2 - s * 0.25
    for px in (-0.55, -0.25, 0.3, 0.6):
        draw.line([(cx + bw * px, body_top + bh * 1.7), (cx + bw * px, cy)], fill=_mix(body, "#000000", 0.25), width=max(3, int(s * 0.055)))
    _r(draw, (cx - bw, body_top, cx + bw, body_top + bh * 2), body, line, s * 0.022)
    _r(draw, (cx - bw * 0.5, body_top + bh * 0.6, cx + bw * 0.5, body_top + bh * 1.7), belly)
    hr = s * 0.2
    nx = cx + bw * 0.85
    ny = body_top - hr * 0.3
    _r(draw, (nx - hr, ny - hr * 0.9, nx + hr, ny + hr * 0.9), body, line, s * 0.016)
    _r(draw, (nx + hr * 0.5, ny - hr * 0.3, nx + hr * 1.4, ny + hr * 0.3), body, line, s * 0.012)
    # shaggy mane
    for k in range(5):
        my = body_top - k * s * 0.02
        _r(draw, (cx + bw * 0.45 - s * 0.07, my - s * 0.16, cx + bw * 0.45 + s * 0.07, my + s * 0.02), _mix(body, "#5a4838", 0.3))
    _eyes(draw, nx + hr * 0.2, ny - hr * 0.2, hr * 0.15, line)


def _bug(draw, cx, cy, s, body, belly, line, kind):
    bw = s * 0.5
    if kind == "moth":
        # wings
        for ex in (-1, 1):
            _r(draw, (cx + bw * ex * 0.4 - bw, cy - s * 0.75, cx + bw * ex * 0.4 + bw * 0.4, cy - s * 0.05), body, line, s * 0.012)
            _r(draw, (cx + bw * ex * 0.5 - bw * 0.7, cy - s * 0.5, cx + bw * ex * 0.5 + bw * 0.2, cy - s * 0.1), belly)
        _r(draw, (cx - s * 0.1, cy - s * 0.8, cx + s * 0.1, cy - s * 0.05), _mix(body, "#8a80a8", 0.4), line, s * 0.01)
        _eyes(draw, cx - s * 0.05, cy - s * 0.72, s * 0.03, line)
        _eyes(draw, cx + s * 0.05, cy - s * 0.72, s * 0.03, line)
    else:  # ladybug
        _r(draw, (cx - s * 0.45, cy - s * 0.5, cx + s * 0.45, cy + s * 0.1), body, line, s * 0.015)
        draw.line([(cx, cy - s * 0.5), (cx, cy + s * 0.1)], fill=line, width=max(2, int(s * 0.015)))
        for (dx, dy) in [(-0.2, -0.2), (0.22, -0.25), (-0.15, 0.02), (0.2, 0.0)]:
            _r(draw, (cx + s * dx - s * 0.05, cy + s * dy - s * 0.05, cx + s * dx + s * 0.05, cy + s * dy + s * 0.05), line)
        _r(draw, (cx - s * 0.5, cy - s * 0.62, cx + s * 0.5, cy - s * 0.4), line)
        _eyes(draw, cx - s * 0.18, cy - s * 0.55, s * 0.03, "#ffffff")
        _eyes(draw, cx + s * 0.18, cy - s * 0.55, s * 0.03, "#ffffff")


# ── helpers ─────────────────────────────────────────────────────────

def _mix(hex_a: str, hex_b: str, t: float) -> tuple:
    a = _hex(hex_a)
    b = _hex(hex_b)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _hex(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
