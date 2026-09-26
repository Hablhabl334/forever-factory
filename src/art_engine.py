"""The procedural art engine — every scene painted fresh, zero APIs.

Layered storybook composition at supersampled resolution:
sky gradient -> stars/moon -> far hills -> tree line -> water/ground ->
path -> characters/props -> atmosphere -> vignette.

Scene types come from the story engine; palettes derive from the story's
time-of-day mood, so visuals stay consistent through the whole episode.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import characters as CH
from .rng import FactoryRNG
from .config import cfg, path as repo_path

SS = 2  # supersample factor
W, H = int(1920 * 1.25 * SS), int(1080 * 1.25 * SS)   # 4800 x 2700 (Ken Burns headroom)

# ── palettes per time mood ───────────────────────────────────────────
PALETTES = {
    "summer_dusk":     {"sky": ["#2a3a7d", "#7b5aa6", "#f2a65a"], "hill": ["#3d3a6e", "#2e2a52"], "ground": "#33406e", "glow": "#ffd9a0", "stars": 0.25, "moon": 0.7},
    "autumn_evening":  {"sky": ["#1c2a4a", "#5a4a7d", "#d97b4a"], "hill": ["#3a2a4e", "#29203a"], "ground": "#4a3648", "glow": "#ffc890", "stars": 0.45, "moon": 0.6},
    "winter_night":    {"sky": ["#0a1230", "#1e3a6e", "#4a6aa8"], "hill": ["#22345e", "#1a2745"], "ground": "#b8c8e8", "glow": "#cfe0ff", "stars": 0.9, "moon": 1.0, "snow": True},
    "spring_twilight": {"sky": ["#233a6e", "#6a5a9d", "#f0a8a0"], "hill": ["#3a3a66", "#2c2c50"], "ground": "#3a4a5e", "glow": "#ffd0c0", "stars": 0.5, "moon": 0.8},
    "lavender_dusk":   {"sky": ["#2d2a5e", "#7d6ab8", "#e8c8f0"], "hill": ["#4a3d78", "#382e5c"], "ground": "#46406e", "glow": "#f0e0ff", "stars": 0.3, "moon": 0.7},
    "moonlit_night":   {"sky": ["#0a0f2a", "#1a2a5a", "#3a5a9a"], "hill": ["#1c2c52", "#141f3a"], "ground": "#26304e", "glow": "#dce8ff", "stars": 1.0, "moon": 1.2},
    "golden_afternoon":{"sky": ["#4a7ab5", "#a8c8e8", "#ffd8a0"], "hill": ["#5a7a5e", "#48624c"], "ground": "#5e7a4e", "glow": "#fff0c0", "stars": 0.0, "moon": 0.0},
    "rainy_evening":   {"sky": ["#1a2233", "#3a4a5d", "#6a7a8d"], "hill": ["#2a3448", "#202a3a"], "ground": "#2e3848", "glow": "#b8c8d8", "stars": 0.1, "moon": 0.4, "rain": True},
    "frost_evening":   {"sky": ["#0d1b3d", "#2a4a7d", "#8ab0d8"], "hill": ["#2a3c64", "#1e2c4a"], "ground": "#8ba4c8", "glow": "#d8e8ff", "stars": 0.8, "moon": 0.9},
    "snow_night":      {"sky": ["#0a1030", "#24406e", "#8aa8c8"], "hill": ["#2a3a5e", "#1e2a45"], "ground": "#c8d8ec", "glow": "#e0ecff", "stars": 0.85, "moon": 1.1, "snow": True},
    "misty_eve":       {"sky": ["#2a3245", "#5a6a7d", "#a8b8c0"], "hill": ["#3e485c", "#303a4c"], "ground": "#3c4454", "glow": "#c8d8e0", "stars": 0.3, "moon": 0.6, "mist": True},
    "honey_evening":   {"sky": ["#3a2a1e", "#8a6a3a", "#e8b06a"], "hill": ["#4e3a2c", "#3a2a20"], "ground": "#5e4634", "glow": "#ffe8c0", "stars": 0.5, "moon": 0.8},
}

INTERIOR = {"wall": "#4a3560", "wall2": "#6a4a78", "floor": "#5e4230", "glow": "#ffd9a0", "sky": ["#0a0f2a", "#1a2a5a"]}


def _hex(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _sky_gradient(sky: list, w: int, h: int, horizon: float = 0.72) -> Image.Image:
    """Vertical multi-stop gradient as an RGB image (numpy, fast)."""
    stops = [_hex(c) for c in sky]
    ys = np.linspace(0, 1, h, dtype=np.float32)
    # piecewise interpolation across stops
    n = len(stops) - 1
    t = np.clip(ys / horizon, 0, 1) * n
    i0 = np.clip(np.floor(t).astype(int), 0, n - 1)
    frac = t - i0
    rows = np.empty((h, 3), dtype=np.uint8)
    arr = np.array(stops, dtype=np.float32)
    for i in range(3):
        col = arr[i0, i] * (1 - frac) + arr[i0 + 1, i] * frac
        rows[:, i] = np.clip(col, 0, 255).astype(np.uint8)
    img = np.repeat(rows[:, None, :], w, axis=1)
    return Image.fromarray(img, "RGB")


def _hill_polygon(rng: FactoryRNG, w: int, y_base: float, amp: float, color, roughness=1.6):
    """Smooth rolling hill silhouette as (polygon_points, color)."""
    pts = [(0, y_base + amp * math.sin(0))]
    phase = rng.between(0, math.tau)
    freq = rng.between(0.9, 1.4)
    for x in range(0, w + 1, 48):
        y = y_base - amp * (0.55 + 0.45 * math.sin(freq * x / w * math.tau + phase))
        pts.append((x, y))
    pts.append((w, y_base + amp))
    pts.append((w, w * 9 // 16))
    pts.append((0, w * 9 // 16))
    return pts, color


class ScenePainter:
    def __init__(self, seed: int, time_mood: str):
        self.rng = FactoryRNG(seed)
        self.pal = PALETTES.get(time_mood, PALETTES["moonlit_night"])
        self.w, self.h = W, H

    # ── sky ──────────────────────────────────────────────────────────
    def sky(self) -> Image.Image:
        img = _sky_gradient(self.pal["sky"], self.w, self.h, horizon=0.72)
        d = ImageDraw.Draw(img, "RGBA")
        rng = self.rng
        if self.pal.get("stars", 0) > 0:
            n = int(650 * self.pal["stars"])
            for _ in range(n):
                x = rng.below(self.w)
                y = rng.below(int(self.h * 0.62))
                r = rng.between(1.5, 4.5) * SS * 0.5
                a = int(rng.between(50, 200))
                d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, a))
            # a few 4-point sparkles
            for _ in range(8):
                x = rng.below(self.w)
                y = rng.below(int(self.h * 0.5))
                s = rng.between(8, 16) * SS * 0.6
                a = int(rng.between(120, 220))
                d.line((x - s, y, x + s, y), fill=(255, 255, 255, a), width=2 * SS // 2)
                d.line((x, y - s, x, y + s), fill=(255, 255, 255, a), width=2 * SS // 2)
        # moon
        if self.pal.get("moon", 0) > 0:
            self._moon(d)
        return img

    def _moon(self, d):
        rng = self.rng
        r = self.h * 0.075 * rng.between(0.9, 1.15) * self.pal.get("moon", 1)
        mx = rng.between(self.w * 0.55, self.w * 0.85)
        my = rng.between(self.h * 0.12, self.h * 0.3)
        phase = rng.below(3)  # 0 full, 1 gibbous, 2 crescent
        # glow
        glow = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gr = r * 2.6
        for k in range(3):
            rr = r + gr * k / 3
            gd.ellipse((mx - rr, my - rr, mx + rr, my + rr), fill=(255, 240, 200, 26))
        img_overlay = glow.filter(ImageFilter.GaussianBlur(30 * SS // 2))
        self._overlays.append(img_overlay)
        d.ellipse((mx - r, my - r, mx + r, my + r), fill="#fff4d8")
        if phase == 1:  # gibbous shadow
            d.ellipse((mx - r * 0.35, my - r * 1.05, mx + r * 0.95, my + r * 0.6), fill=self.pal["sky"][1])
        elif phase == 2:  # crescent
            d.ellipse((mx - r * 0.75, my - r * 1.1, mx + r * 0.6, my + r * 0.7), fill=self.pal["sky"][1])
        # craters (subtle)
        for _ in range(4):
            cr = r * rng.between(0.08, 0.18)
            cx = mx + rng.between(-r * 0.5, r * 0.5)
            cy = my + rng.between(-r * 0.5, r * 0.5)
            d.ellipse((cx - cr, cy - cr, cx + cr, cy + cr), fill="#efe0bc")

    _overlays: list

    # ── landscape layers ─────────────────────────────────────────────
    def hills(self, img: Image.Image, n: int = 3) -> Image.Image:
        d = ImageDraw.Draw(img, "RGBA")
        rng = self.rng
        horizon = self.h * 0.62
        for i in range(n):
            y_base = horizon + i * self.h * 0.045
            amp = self.h * (0.09 - i * 0.02)
            color = _hex(self.pal["hill"][min(i, 1)])
            color = _lerp(color, _hex(self.pal["sky"][0]), 0.18 * (n - 1 - i))
            pts, _ = _hill_polygon(rng, self.w, y_base, amp, color)
            d.polygon(pts, fill=color + (255,))
        return img

    def treeline(self, img: Image.Image, y: float, density: float = 0.6, scale: float = 1.0) -> Image.Image:
        d = ImageDraw.Draw(img, "RGBA")
        rng = self.rng
        color = _lerp(_hex(self.pal["hill"][0]), (10, 10, 24), 0.35)
        x = rng.between(-80, 0)
        while x < self.w:
            kind = "pine" if rng.chance(0.62) else "round"
            tw = rng.between(70, 150) * scale * SS * 0.5
            th = tw * rng.between(1.5, 2.4)
            if kind == "pine":
                layers = 3
                for k in range(layers):
                    ly = y - th * (k / layers)
                    lw = tw * (1 - k / (layers + 1))
                    d.polygon([(x - lw, ly), (x + lw, ly), (x, ly - th * 0.55)], fill=color + (255,))
                d.rectangle((x - tw * 0.08, y, x + tw * 0.08, y + th * 0.2), fill=color + (255,))
            else:
                d.ellipse((x - tw, y - th * 1.15, x + tw, y + tw * 0.25), fill=color + (255,))
                d.rectangle((x - tw * 0.1, y, x + tw * 0.1, y + tw * 0.35), fill=color + (255,))
            x += tw * rng.between(1.1, 2.2) / max(density, 0.2)
        return img

    def water(self, img: Image.Image, top: float) -> Image.Image:
        d = ImageDraw.Draw(img, "RGBA")
        rng = self.rng
        hz = _hex(self.pal["sky"][2])
        deep = _lerp(_hex(self.pal["sky"][0]), (8, 12, 30), 0.3)
        for y in range(int(top), self.h, 6):
            t = (y - top) / max(1, self.h - top)
            c = _lerp(hz, deep, min(1, t * 1.4))
            d.line([(0, y), (self.w, y)], fill=c + (235,))
        # moon glitter path
        for _ in range(90):
            gx = self.w * rng.between(0.35, 0.6)
            gy = top + rng.between(0, (self.h - top) * 0.8)
            gw = rng.between(6, 42) * SS * 0.5
            d.line([(gx - gw, gy), (gx + gw, gy)], fill=(255, 245, 210, int(rng.between(20, 70))), width=2 * SS // 2 + 1)
        # ripple lines
        for _ in range(30):
            ry = top + rng.between(0, self.h - top)
            rx = rng.below(self.w)
            rw = rng.between(30, 120) * SS * 0.5
            d.arc((rx, ry - rw // 3, rx + rw, ry + rw // 3), 200, 340, fill=(220, 230, 250, 26), width=SS)
        return img

    def ground(self, img: Image.Image, top: float) -> Image.Image:
        d = ImageDraw.Draw(img, "RGBA")
        rng = self.rng
        base = _hex(self.pal["ground"])
        if self.pal.get("snow"):
            base = _hex(self.pal["ground"])
        pts = [(0, self.h)]
        phase = rng.between(0, math.tau)
        for x in range(0, self.w + 1, 64):
            y = top - self.h * 0.035 * (0.5 + 0.5 * math.sin(x / self.w * math.tau * 1.3 + phase))
            pts.append((x, y))
        pts.append((self.w, self.h))
        d.polygon(pts, fill=base + (255,))
        # grass tufts / snow bumps
        for _ in range(140):
            gx = rng.below(self.w)
            gy = top + rng.between(0, self.h - top - 8)
            if self.pal.get("snow"):
                d.ellipse((gx - 10 * SS // 2, gy - 4 * SS // 2, gx + 10 * SS // 2, gy + 4 * SS // 2), fill=_lerp(base, (255, 255, 255), 0.25) + (180,))
            else:
                for k in range(3):
                    d.line([(gx + k * 4 * SS // 2, gy), (gx + k * 4 * SS // 2 + rng.between(-4, 4) * SS, gy - rng.between(10, 22) * SS // 2)],
                           fill=_lerp(base, (20, 40, 30), 0.4) + (200,), width=SS)
        return img

    def path(self, img: Image.Image, top: float) -> Image.Image:
        d = ImageDraw.Draw(img, "RGBA")
        rng = self.rng
        c0 = _lerp(_hex(self.pal["ground"]), (200, 180, 150), 0.45)
        pts = []
        drift = rng.between(-0.25, 0.25)
        for t in range(11):
            tt = t / 10
            x = self.w * (0.5 + drift * (1 - tt) * 0.8) + math.sin(tt * 5 + rng.between(0, 3)) * self.w * 0.06
            y = self.h - (self.h - top) * tt
            wcurve = 60 * SS * 0.5 * (1 - tt * 0.45)
            pts.append((x, y, wcurve))
        for i in range(len(pts) - 1):
            x1, y1, w1 = pts[i]
            x2, y2, w2 = pts[i + 1]
            d.line([(x1, y1), (x2, y2)], fill=c0 + (215,), width=int(max(w1, w2)))
        # stepping stones hint
        for (x, y, w) in pts[1::2]:
            d.ellipse((x - w * 0.5, y - w * 0.22, x + w * 0.5, y + w * 0.22), fill=_lerp(c0, (255, 255, 255), 0.18) + (160,))
        return img

    def village(self, img: Image.Image, y: float) -> Image.Image:
        """Warm distant houses with lit windows."""
        d = ImageDraw.Draw(img, "RGBA")
        rng = self.rng
        x = rng.between(60, 200)
        while x < self.w - 100:
            hw = rng.between(50, 90) * SS * 0.5
            hh = hw * rng.between(0.7, 1.0)
            roof = _lerp(_hex(self.pal["hill"][0]), (30, 20, 40), 0.3)
            wall = _lerp(_hex(self.pal["ground"]), (60, 45, 50), 0.25)
            d.rectangle((x, y - hh, x + hw, y), fill=wall + (255,))
            d.polygon([(x - hw * 0.12, y - hh), (x + hw * 1.12, y - hh), (x + hw * 0.5, y - hh * 1.7)], fill=roof + (255,))
            # lit window
            if rng.chance(0.75):
                wx = x + hw * rng.between(0.2, 0.6)
                d.rectangle((wx, y - hh * 0.72, wx + hw * 0.22, y - hh * 0.35), fill=_hex(self.pal["glow"]) + (235,))
            x += hw * rng.between(2.0, 3.4)
        return img

    # ── atmosphere ───────────────────────────────────────────────────
    def atmosphere(self, img: Image.Image, motif: str) -> Image.Image:
        d = ImageDraw.Draw(img, "RGBA")
        rng = self.rng
        glow = _hex(self.pal["glow"])
        if "firefl" in motif or motif == "fireflies":
            for _ in range(26):
                x = rng.below(self.w)
                y = rng.between(self.h * 0.35, self.h * 0.9)
                r = rng.between(4, 9) * SS * 0.5
                for k in range(3):
                    rr = r * (1 + k)
                    d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=glow + (18,))
                d.ellipse((x - r * 0.4, y - r * 0.4, x + r * 0.4, y + r * 0.4), fill=glow + (230,))
        elif motif in ("snowflakes", "snow"):
            for _ in range(120):
                x = rng.below(self.w)
                y = rng.below(self.h)
                r = rng.between(3, 8) * SS * 0.5
                d.ellipse((x - r, y - r, x + r, y + r), fill=(240, 246, 255, int(rng.between(90, 200))))
        elif motif in ("drifting leaves", "falling feathers", "moth wings"):
            for _ in range(16):
                x = rng.below(self.w)
                y = rng.below(self.h)
                s = rng.between(10, 22) * SS * 0.5
                c = _lerp(glow, (200, 150, 90), 0.5)
                d.ellipse((x, y - s * 0.35, x + s, y + s * 0.35), fill=c + (int(rng.between(70, 160)),))
        elif "star" in motif:
            for _ in range(14):
                x = rng.below(self.w)
                y = rng.below(self.h * 0.75)
                s = rng.between(6, 14) * SS * 0.5
                d.line((x - s, y, x + s, y), fill=glow + (190,), width=SS)
                d.line((x, y - s, x, y + s), fill=glow + (190,), width=SS)
        elif "dewdrop" in motif or "dew" in motif:
            for _ in range(60):
                x = rng.below(self.w)
                y = rng.between(self.h * 0.5, self.h)
                r = rng.between(3, 7) * SS * 0.5
                d.ellipse((x - r, y - r, x + r, y + r), fill=(210, 240, 255, int(rng.between(60, 150))))
        if self.pal.get("rain"):
            for _ in range(220):
                x = rng.below(self.w + 100) - 50
                y = rng.below(self.h)
                ln = rng.between(18, 42) * SS * 0.5
                d.line([(x, y), (x - ln * 0.25, y + ln)], fill=(180, 200, 230, int(rng.between(28, 70))), width=SS)
        if self.pal.get("mist"):
            mist = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
            md = ImageDraw.Draw(mist)
            for _ in range(7):
                my = rng.between(self.h * 0.45, self.h * 0.85)
                md.ellipse((-self.w * 0.2, my - 40 * SS, self.w * 1.2, my + 40 * SS), fill=(220, 228, 240, 26))
            img = Image.alpha_composite(img.convert("RGBA"), mist.filter(ImageFilter.GaussianBlur(24 * SS)))
        return img

    def vignette(self, img: Image.Image) -> Image.Image:
        arr = np.asarray(img.convert("RGB")).astype(np.float32)
        h, w = arr.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
        dark = np.clip(1.08 - 0.38 * np.clip(r - 0.55, 0, 1) / 0.45, 0, 1.05)
        arr = np.clip(arr * dark[..., None], 0, 255).astype(np.uint8)
        return Image.fromarray(arr)

    _overlays = None  # set per-paint


def _fonts():
    baloo = repo_path("assets", "fonts", "Baloo2.ttf")
    def f(size, weight=700):
        font = ImageFont.truetype(str(baloo), int(size))
        try:
            font.set_variation_by_axes([weight])
        except Exception:
            pass
        return font
    return f


# ── scene composition ────────────────────────────────────────────────

EXTERIOR_TYPES = {"exterior_night", "exterior_path", "forest_path", "hill_climb",
                  "forest_clearing", "high_place", "sky_reach", "valley_view",
                  "water_reflection", "home_path", "path_night", "window_night"}
WATER_TYPES = {"water_reflection"}


def paint_scene(scene: dict, seed: int) -> Image.Image:
    spec = scene["image"]
    painter = ScenePainter(seed, spec.get("time_mood", "moonlit_night"))
    painter._overlays = []
    rng = painter.rng
    stype = spec["type"]

    if stype.startswith("interior") or stype == "window_night":
        img = _paint_interior(painter, spec, seed)
    else:
        img = _paint_exterior(painter, spec, stype, seed)

    img = painter.vignette(img)
    # downscale from supersample
    return img.resize((int(W / SS), int(H / SS)), Image.LANCZOS)


def _paint_exterior(p: ScenePainter, spec, stype: str, seed: int) -> Image.Image:
    rng = p.rng
    img = p.sky()
    img = p.hills(img, n=3)
    horizon = p.h * 0.62
    # distant village for wide/home scenes
    if stype in ("valley_view", "home_path", "path_night", "exterior_night"):
        img = p.village(img, horizon + p.h * 0.02)
    img = p.treeline(img, horizon + p.h * 0.05, density=0.75 if "forest" in stype else 0.5,
                     scale=1.25 if "forest" in stype else 1.0)
    if stype in ("forest_path", "forest_clearing"):
        img = p.treeline(img, horizon + p.h * 0.16, density=1.0, scale=1.9)
    if stype in WATER_TYPES:
        img = p.water(img, horizon + p.h * 0.08)
    else:
        img = p.ground(img, horizon + p.h * 0.13)
        if stype in ("exterior_path", "forest_path", "hill_climb", "home_path", "path_night", "high_place", "sky_reach"):
            img = p.path(img, horizon + p.h * 0.15)

    # moon-glow overlays accumulated during sky()
    for ov in (p._overlays or []):
        img = Image.alpha_composite(img.convert("RGBA"), ov)

    # characters
    d = ImageDraw.Draw(img, "RGBA")
    camera = spec.get("camera", "medium")
    focus = spec.get("focus", "hero")
    base = spec.get("hero_base", "hare")
    hero_size = {"wide": p.h * 0.13, "medium": p.h * 0.24, "close": p.h * 0.38}[camera]
    hy = p.h * ({"wide": 0.87, "medium": 0.84, "close": 0.88}[camera])
    hx = p.w * 0.5
    if focus == "sky":
        hx = p.w * 0.38
        # hero gazing up (medium, left third)
        CH.draw_character(d, base, hx, hy, hero_size * 0.8, pose="sit")
    elif focus == "companion":
        CH.draw_character(d, base, p.w * 0.38, hy, hero_size * 0.8, pose="sit")
        comp = CH.COMPANION_BASE.get(spec.get("companion", "owl"), "owl")
        CH.draw_character(d, comp, p.w * 0.62, hy, hero_size * 1.15 if comp in ("bear", "owl", "stone giant", "cloud") else hero_size * 0.9, pose="sit")
    elif focus == "object":
        CH.draw_character(d, base, p.w * 0.44, hy, hero_size, pose="sit")
        _glow_orb(d, p, p.w * 0.60, hy - hero_size * 0.55, hero_size * 0.5)
    else:
        CH.draw_character(d, base, p.w * 0.5, hy, hero_size, pose="sit")

    img = p.atmosphere(img, spec.get("motif", ""))
    return img


def _glow_orb(d, p: ScenePainter, x: float, y: float, r: float):
    glow = _hex(p.pal["glow"])
    for k in range(5):
        rr = r * (1 + k * 0.55)
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=glow + (16,))
    d.ellipse((x - r, y - r, x + r, y + r), fill=glow + (255,))
    d.ellipse((x - r * 0.45, y - r * 0.5, x - r * 0.05, y - r * 0.1), fill=(255, 255, 255, 200))


def _paint_interior(p: ScenePainter, spec, seed: int) -> Image.Image:
    rng = p.rng
    # walls
    img = _sky_gradient([INTERIOR["wall"], INTERIOR["wall2"], INTERIOR["wall"]], p.w, p.h, horizon=1.0)
    d = ImageDraw.Draw(img, "RGBA")
    # floor
    floor_top = p.h * 0.68
    d.rectangle((0, floor_top, p.w, p.h), fill=_hex(INTERIOR["floor"]))
    for i in range(14):  # floorboards
        y = floor_top + (p.h - floor_top) * i / 14
        d.line([(0, y), (p.w, y)], fill=_lerp(_hex(INTERIOR["floor"]), (20, 12, 8), 0.35) + (255,), width=SS)
    # window with night sky (half-moon shaped, top center-right)
    wx, wy, wr = p.w * 0.62, p.h * 0.32, p.h * 0.17
    sky = _sky_gradient(INTERIOR["sky"], int(wr * 2), int(wr * 2), horizon=1.0)
    mask = Image.new("L", (int(wr * 2), int(wr * 2)), 0)
    md = ImageDraw.Draw(mask)
    md.pieslice((0, 0, wr * 2, wr * 2), 180, 360, fill=255)
    md.rectangle((0, wr, wr * 2, wr * 2), fill=255)
    img.paste(sky, (int(wx - wr), int(wy - wr)), mask)
    d.arc((wx - wr, wy - wr, wx + wr, wy + wr), 180, 360, fill="#2a1a3a", width=6 * SS)
    d.line([(wx - wr, wy), (wx + wr, wy)], fill="#2a1a3a", width=6 * SS)
    # moon in window + stars
    d.ellipse((wx - wr * 0.15, wy - wr * 0.62, wx + wr * 0.45, wy - wr * 0.05), fill="#fff4d8")
    for _ in range(12):
        sx = wx - wr + rng.below(int(wr * 2))
        sy = wy - wr + rng.below(int(wr))
        d.ellipse((sx - 3 * SS, sy - 3 * SS, sx + 3 * SS, sy + 3 * SS), fill=(255, 255, 255, 160))
    # warm lamp glow (left)
    lamp_x, lamp_y = p.w * 0.16, p.h * 0.28
    for k in range(6):
        rr = p.h * 0.05 * (1 + k * 0.8)
        d.ellipse((lamp_x - rr, lamp_y - rr, lamp_x + rr, lamp_y + rr), fill=_hex(INTERIOR["glow"]) + (20,))
    d.ellipse((lamp_x - p.h * 0.035, lamp_y - p.h * 0.05, lamp_x + p.h * 0.035, lamp_y + p.h * 0.03), fill="#ffe8b0")
    # shelf with object-glow (right of window)
    shelf_y = p.h * 0.52
    d.rectangle((p.w * 0.18, shelf_y, p.w * 0.34, shelf_y + 8 * SS), fill=_lerp(_hex(INTERIOR["floor"]), (30, 20, 12), 0.2))
    _glow_orb(d, p, p.w * 0.26, shelf_y - p.h * 0.045, p.h * 0.028)
    # bed (bottom left) — moss bed with dusk quilt
    bx0, by0 = p.w * 0.08, p.h * 0.78
    bw, bh = p.w * 0.42, p.h * 0.16
    d.rounded_rectangle((bx0, by0, bx0 + bw, by0 + bh), radius=20 * SS, fill="#6a4a30", outline="#3a2818", width=3 * SS)
    quilt = ["#5a4a8a", "#7a5a9a", "#4a6a8a", "#8a6a7a"]
    for i, c in enumerate(quilt):
        d.polygon([(bx0 + bw * i / 4, by0 + bh), (bx0 + bw * (i + 1) / 4, by0 + bh),
                   (bx0 + bw * (i + 0.7) / 4, by0 + bh * 0.25), (bx0 + bw * (i + 0.2) / 4, by0 + bh * 0.2)], fill=c)
    # pillow
    d.ellipse((bx0 + bw * 0.04, by0 - bh * 0.25, bx0 + bw * 0.3, by0 + bh * 0.2), fill="#f0e8dc", outline="#c0b8a8", width=2 * SS)
    # hero in bed (sleep pose for sleep scenes)
    camera = spec.get("camera", "medium")
    base = spec.get("hero_base", "hare")
    sleeping = spec["type"] == "interior_night"
    size = p.h * (0.30 if camera == "close" else 0.2 if camera == "medium" else 0.14)
    if spec.get("focus") == "hero" and not sleeping:
        # standing/awake near bed for cozy scenes
        CH.draw_character(d, base, p.w * 0.46, p.h * 0.92, size, pose="sit")
    else:
        CH.draw_character(d, base, bx0 + bw * 0.55, by0 + bh * 0.18, size * 1.15, pose="sleep" if sleeping else "sit")
    # companion watching from floor if focus companion
    if spec.get("focus") == "companion":
        comp = CH.COMPANION_BASE.get(spec.get("companion", "owl"), "owl")
        CH.draw_character(d, comp, p.w * 0.55, p.h * 0.95, size * 0.9, pose="sit")
    # rug
    d.ellipse((p.w * 0.3, p.h * 0.88, p.w * 0.72, p.h * 0.99), fill=_lerp(_hex(INTERIOR["floor"]), (140, 90, 90), 0.35) + (255,))
    # fireflies / motif near ceiling
    d2 = ImageDraw.Draw(img, "RGBA")
    motif = spec.get("motif", "")
    if "firefl" in motif:
        for _ in range(10):
            x = rng.below(p.w)
            y = rng.between(p.h * 0.1, p.h * 0.5)
            r = rng.between(4, 8) * SS * 0.5
            d2.ellipse((x - r, y - r, x + r, y + r), fill=_hex(INTERIOR["glow"]) + (200,))
    return img


# ── cards ────────────────────────────────────────────────────────────

def paint_title_card(title: str, seed: int, time_mood: str = "moonlit_night") -> Image.Image:
    scene = {"image": {"type": "exterior_night", "focus": "sky", "camera": "wide",
                       "hero_base": "hare", "companion": "owl", "motif": "shooting stars",
                       "time_mood": time_mood, "sky": "night"}}
    img = paint_scene(scene, seed)
    f = _fonts()
    d = ImageDraw.Draw(img)
    # moonberry mark: crescent + berry dot
    mx, my = img.width * 0.5, img.height * 0.16
    r = img.height * 0.05
    d.ellipse((mx - r * 1.9, my - r * 1.9, mx + r * 1.9, my + r * 1.9), fill=(255, 236, 200, 40))
    d.ellipse((mx - r, my - r, mx + r, my + r), fill="#fff4d8")
    d.ellipse((mx - r * 0.55, my - r * 1.05, mx + r * 0.75, my + r * 0.5), fill="#1a2a5a")
    d.ellipse((mx + r * 1.05, my + r * 0.25, mx + r * 1.45, my + r * 0.65), fill="#c86a8a")
    # title text — wrapped, warm cream with soft shadow
    font = f(img.height * 0.115, 700)
    words = title.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=font) > img.width * 0.82 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    lines.append(cur)
    y = img.height * 0.34
    for line in lines:
        tw = d.textlength(line, font=font)
        for dx, dy, col in ((0, 6, (20, 16, 40, 180)),):
            d.text((img.width / 2 - tw / 2 + dx, y + dy), line, font=font, fill=col)
        d.text((img.width / 2 - tw / 2, y), line, font=font, fill="#fff6e4")
        y += img.height * 0.14
    # channel mark
    small = f(img.height * 0.045, 600)
    label = "Moonberry Tales"
    tw = d.textlength(label, font=small)
    d.text((img.width / 2 - tw / 2, img.height * 0.86), label, font=small, fill=(255, 236, 200, 220))
    return img


def paint_end_card(seed: int) -> Image.Image:
    p = ScenePainter(seed, "moonlit_night")
    p._overlays = []
    img = p.sky()
    img = p.hills(img, n=3)
    for ov in (p._overlays or []):
        img = Image.alpha_composite(img.convert("RGBA"), ov)
    d = ImageDraw.Draw(img, "RGBA")
    f = _fonts()
    cx, cy = img.width * 0.5, img.height * 0.42
    r = img.height * 0.075
    for k in range(4):
        rr = r * (1 + k * 0.7)
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(255, 236, 200, 22))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill="#fff4d8")
    d.ellipse((cx - r * 0.55, cy - r * 1.05, cx + r * 0.75, cy + r * 0.5), fill="#1a2a5a")
    d.ellipse((cx + r * 1.05, cy + r * 0.25, cx + r * 1.45, cy + r * 0.65), fill="#c86a8a")
    font = f(img.height * 0.08, 700)
    for text, y, col in (("Sleep well, little one.", img.height * 0.58, (255, 246, 228)),
                         ("Moonberry Tales", img.height * 0.72, (255, 236, 200, 225))):
        tw = d.textlength(text, font=font)
        d.text((cx - tw / 2 + 3, y + 5), text, font=font, fill=(20, 16, 40, 170))
        d.text((cx - tw / 2, y), text, font=font, fill=col)
        font = f(img.height * 0.05, 600)
    img = p.vignette(img)
    return img.resize((int(W / SS), int(H / SS)), Image.LANCZOS)


def save_scene(scene: dict, seed: int, out: Path, time_mood: str) -> Path:
    img = paint_scene(scene, seed)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")
    return out
