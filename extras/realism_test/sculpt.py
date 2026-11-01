#!/usr/bin/env python3
"""The SCULPT pass — volumetric shading for the flat-art couple.

Test-only module (batch-5 realism test). Takes the couple overlay that
art_engine.draw_figure paints (flat colors, production silhouettes and
rig motion untouched) and turns each material region into a lit,
dimensional volume using distance-field normals:

  key light (upper-left) -> form shading with material-specific falloff
  rim light (right)       -> silhouette separation on the shadow side
  ambient occlusion       -> contact darkening at part edges
  subsurface warmth       -> skin translucency on thin lit edges
  hair gloss band         -> specular streak on the hair dome
  hair core depth         -> mass darkening toward the interior

No factory file is touched; this runs on an isolated RGBA overlay.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

# light directions (image coords, y grows DOWN; up = -y)
KEY = np.array([-0.72, -0.62]); KEY /= np.linalg.norm(KEY)
RIM = np.array([0.88, -0.38]);  RIM /= np.linalg.norm(RIM)
HAIR_H = KEY + np.array([0.0, -0.45]); HAIR_H /= np.linalg.norm(HAIR_H)

MATS = {   # ambient, form kd, terminator softness, flatness
    "skin":  (0.90, 0.170, 1.00, 0.30),
    "top":   (0.92, 0.115, 0.85, 0.55),
    "pants": (0.90, 0.135, 0.85, 0.50),
    "hair":  (0.86, 0.210, 0.90, 0.35),
}

def _clean(m: np.ndarray) -> np.ndarray:
    m = ndimage.binary_closing(m, iterations=2)
    return ndimage.binary_fill_holes(m)

def shade_figure_overlay(ov: Image.Image, spec: dict,
                         k: float = 1.0) -> Image.Image:
    """Shade ONE character overlay (RGBA, transparent elsewhere).
    k scales the effect (C: 0.7 subtle, D: 1.25 dramatic)."""
    W, H = ov.size
    a = np.asarray(ov).astype(np.float32)
    alpha = a[..., 3]
    solid = alpha > 140
    if not solid.any():
        return ov
    ys, xs = np.nonzero(solid)
    y0, y1 = max(0, ys.min() - 8), min(H, ys.max() + 9)
    x0, x1 = max(0, xs.min() - 8), min(W, xs.max() + 9)
    crop = a[y0:y1, x0:x1]
    calpha = crop[..., 3] > 140

    rgb = crop[..., :3].copy()
    out = rgb.copy()
    colors = {"skin": spec["skin"], "hair": spec["hair"],
              "top": spec["top"], "pants": spec["pants"]}

    for name, col in colors.items():
        m = _clean(np.all(crop[..., :3] == np.array(col, np.float32), axis=-1) & calpha)
        if not m.any() or m.sum() < 24:
            continue
        amb, kd, soft, flat = MATS[name]
        D = ndimage.distance_transform_edt(m).astype(np.float32)
        sigma = max(3.0, float(np.percentile(D[m], 55)) * 0.55)
        Ds = ndimage.gaussian_filter(D, sigma)
        gy, gx = np.gradient(Ds)
        gl = np.sqrt(gx * gx + gy * gy) + 1e-4
        nx, ny = -gx / gl, -gy / gl            # outward normal
        lam = np.clip(nx * KEY[0] + ny * KEY[1], 0.0, 1.0)
        # material falloff: softer terminator for fabric (flat mix)
        lam_s = lam ** (soft * (1.0 - 0.45 * flat))
        form = (amb + kd * lam_s * 2.0) ** (1.0 + 0.25 * flat)
        # rim light on the shadow-side silhouette (computed first:
        # where rim lands, AO yields — no doubled darkening on necks)
        ao_w = max(2.5, sigma * 0.35)
        edge = np.clip(D / ao_w, 0.0, 1.0)
        rimm = np.clip(nx * RIM[0] + ny * RIM[1], 0.0, 1.0) ** 2
        rimm *= (1.0 - edge * 0.65) * (1.0 - lam * 0.55)
        # ambient occlusion at the silhouette edge (skin softer)
        ao_k = (0.055 if name == "skin" else 0.10) * k
        ao_f = 1.0 - ao_k * (1.0 - edge) * (1.0 - 0.55 * rimm)
        form *= ao_f
        # write base form
        mm = m & (calpha)
        out[mm] = rgb[mm] * np.clip(form[mm], 0.58, 1.18)[..., None]
        if name == "skin":
            # subsurface: thin lit edges glow warm
            sss = ((D < ao_w * 1.9) & (lam > 0.25)).astype(np.float32)
            sss = ndimage.gaussian_filter(sss, 1.2) * 0.55 * k
            add = np.stack([sss * 26.0, sss * 9.0, sss * 2.0], -1)
            out[mm] += add[mm]
        if name == "hair":
            # gloss streak + core depth
            spec_t = np.clip(nx * HAIR_H[0] + ny * HAIR_H[1], 0.0, 1.0) ** 7.0
            core = np.clip(Ds / max(Ds.max(), 1.0), 0.0, 1.0)
            add = np.stack([spec_t * 44.0 * k, spec_t * 42.0 * k, spec_t * 38.0 * k], -1)
            out[mm] = out[mm] * (1.0 - 0.13 * core[mm][..., None]) + add[mm]

    res = np.concatenate([np.clip(out, 0, 255), crop[..., 3:]], -1).astype(np.uint8)
    full = np.zeros_like(a, dtype=np.uint8)
    full[y0:y1, x0:x1] = res
    return Image.fromarray(full, "RGBA")


def grade(img: Image.Image, amount: float = 1.0) -> Image.Image:
    """Cinematic split-tone: cool lift in shadows, warm push in
    highlights, gentle S-curve. Test-only final pass."""
    x = np.asarray(img).astype(np.float32) / 255.0
    lum = x @ np.array([0.299, 0.587, 0.114], np.float32)
    s = (lum - 0.5)
    cool = np.array([0.00, 0.012, 0.035]) * (1.0 - lum)[..., None]
    warm = np.array([0.030, 0.014, 0.000]) * lum[..., None]
    y = x + (cool + warm) * amount
    y = np.clip(0.5 + (y - 0.5) * (1.0 + 0.055 * amount), 0, 1)
    return Image.fromarray((y * 255).astype(np.uint8))


def wall_keyglow(img: Image.Image, cx: float, cy: float, r: float,
                 strength: float = 0.16) -> Image.Image:
    """A soft warm radial glow on the wall where the key light lands —
    reinforces the lighting story of the dramatic variant."""
    W, H = img.size
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r)
    g = np.exp(-d2 * 1.8) * strength
    x = np.asarray(img).astype(np.float32) / 255.0
    warm = np.array([1.0, 0.93, 0.82], np.float32)
    y = 1.0 - (1.0 - x) * (1.0 - g[..., None] * warm[None, None, :])
    return Image.fromarray((np.clip(y, 0, 1) * 255).astype(np.uint8))
