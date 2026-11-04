#!/usr/bin/env python3
"""Realism test — THE SAME scene in four visual engines, side by side.

A  legacy flat     (the pre-batch-4 machine — the "before")
B  depth engine    (production TODAY — parallax + DOF + motes + shaft)
C  sculpted        (B + volumetric couple shading, subtle)
D  sculpted cine   (B + stronger shading + key glow + film grade)

ZERO factory files are modified; production code is imported read-only
and variant A flips the depth gate in-process only (the documented
fail-open path). Output: download/realism_test/
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

FF = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FF))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from src import anim, art_engine, depth  # noqa: E402
from sculpt import grade, shade_figure_overlay, wall_keyglow  # noqa: E402

OUT = Path("/home/z/my-project/download/realism_test")
OUT.mkdir(parents=True, exist_ok=True)

FPS = 30
T = 4.0
N_FRAMES = 120                      # the full seamless loop
TEXT = "the way you argue shows how you were loved as a child"
BAND = "ATTACHMENT STYLES"
SCENE = {"emotion_a": "happy", "pose_a": "stand",
         "emotion_b": "shy", "pose_b": "stand"}
SEED = 42
STYLE = "gentle_sway"


def params() -> list[dict]:
    ps = [anim._char_params(SEED, STYLE, i, T) for i in range(2)]
    for i, p in enumerate(ps):
        p["phase"] += 0.9 * i
    return ps


def compose_sculpted(layers, ps, t, k, grade_amt, glow):
    """B's world + the couple redrawn on a 2x supersampled overlay,
    then SCULPT-shaded, then composited. Same rig/eyes/blinks as
    production (anim._rig_at / anim._eye_at)."""
    img = depth.world_base(layers, ps, t, T)
    if glow:
        w, h = layers["size"]
        img = wall_keyglow(img, w * 0.24, h * 0.30, w * 0.55, 0.16)
    for sp, prm in zip(layers["sprites"], ps):
        state = anim._eye_at(prm, t)
        cw, ch = int(sp["w"]), int(sp["h"])
        ov = Image.new("RGBA", (cw * 2, ch * 2), (0, 0, 0, 0))
        dr = ImageDraw.Draw(ov)
        art_engine.draw_figure(
            dr, cw, ch * 2 - 32, sp["s"] * 2.0,
            dict(sp["spec"], eyes=state or sp["default"]),
            shadow=False, rig=anim._rig_at(prm, t, T))
        ov = ov.resize((cw, ch), Image.LANCZOS)
        ov = shade_figure_overlay(ov, sp["spec"], k)
        img.paste(ov, (int(sp["anchor_x"] - cw / 2),
                       int(sp["feet_y"] - (ch - 16))), ov)
    depth.foreground(img, layers, t, T)
    tl = layers.get("text_layer")
    if tl is not None:
        img = Image.alpha_composite(img.convert("RGBA"), tl).convert("RGB")
    if grade_amt:
        img = grade(img, grade_amt)
    return img


def frame_variant(layers, ps, t, variant, cache={}):
    if variant == "A":
        real = depth.enabled
        depth.enabled = lambda: False          # in-process only
        try:
            img = anim.compose_frame(layers, ps, t, T)
        finally:
            depth.enabled = real
        return img
    if variant == "B":
        return anim.compose_frame(layers, ps, t, T)
    if variant == "C":
        return compose_sculpted(layers, ps, t, k=0.7, grade_amt=0.0, glow=False)
    if variant == "D":
        return compose_sculpted(layers, ps, t, k=1.25, grade_amt=1.0, glow=True)
    raise ValueError(variant)


def main():
    t0 = time.time()
    layers = art_engine.build_scene_card_layers(TEXT, BAND, SCENE, SEED)
    ps = params()
    variants = "ABCD"
    small = (540, 960)
    labels = {"A": "A  legacy flat (before)",
              "B": "B  depth engine (live now)",
              "C": "C  + sculpted shading",
              "D": "D  + sculpted cine (shading+grade)"}

    # ── hero stills at t = 0.8T (a lively mid-sway pose) ──
    hero_t = 0.8 * T
    heroes = {}
    for v in variants:
        img = frame_variant(layers, ps, hero_t, v)
        heroes[v] = img
        img.save(OUT / f"variant_{v}.png")
        print(f"[hero] {v} done ({time.time()-t0:.0f}s)", flush=True)

    # comparison sheet 2x2 (downscaled) with labels
    sheet = Image.new("RGB", (1080, 1920 + 150), (245, 242, 235))
    dd = ImageDraw.Draw(sheet)
    from PIL import ImageFont
    try:
        lf = ImageFont.truetype(
            "/usr/share/fonts/truetype/archivo/ArchivoBlack-Regular.ttf", 30)
    except Exception:
        try:
            lf = ImageFont.truetype(
                str(FF / "assets/fonts/ArchivoBlack-Regular.ttf"), 30)
        except Exception:
            lf = ImageFont.load_default()
    for i, v in enumerate(variants):
        im = heroes[v].resize(small, Image.LANCZOS)
        x, y = (i % 2) * 540, (i // 2) * 960 + 150
        sheet.paste(im, (x, y))
        dd.rectangle([x, y, x + 540, y + 46], fill=(24, 24, 36))
        dd.text((x + 14, y + 8), labels[v], fill=(245, 242, 235), font=lf)
    sheet.save(OUT / "comparison_2x2.jpg", quality=90)

    # face-detail strip (crop of the two heads, 2x zoom) C vs B
    def head_crop(img):
        w, h = img.size
        sp = layers["sprites"][0]
        cx, top = sp["anchor_x"], sp["feet_y"] - 404 * sp["s"] - 90 * sp["s"]
        box = (int(cx - 300), int(top), int(cx + 300), int(top + 460))
        return img.crop(box).resize((600, 460), Image.LANCZOS)
    strip = Image.new("RGB", (1210, 470), (245, 242, 235))
    strip.paste(head_crop(heroes["B"]), (5, 5))
    strip.paste(head_crop(heroes["C"]), (605, 5))
    dd = ImageDraw.Draw(strip)
    dd.text((16, 8), "B today (flat)", fill=(120, 40, 40), font=lf)
    dd.text((616, 8), "C sculpted (lit form)", fill=(20, 90, 40), font=lf)
    strip.save(OUT / "detail_faces.jpg", quality=92)

    # ── the 2x2 grid loop video (full 4s seamless) ──
    import subprocess
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", "1080x1920", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
           "-pix_fmt", "yuv420p", str(OUT / "comparison_loop.mp4")]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for fi in range(N_FRAMES):
        t = fi / FPS
        grid = Image.new("RGB", (1080, 1920), (245, 242, 235))
        for i, v in enumerate(variants):
            im = frame_variant(layers, ps, t, v).resize(small, Image.LANCZOS)
            grid.paste(im, ((i % 2) * 540, (i // 2) * 960))
        proc.stdin.write(np.asarray(grid, dtype=np.uint8).tobytes())
        if fi % 15 == 0:
            print(f"[frame {fi}/{N_FRAMES} ({time.time()-t0:.0f}s)]", flush=True)
    proc.stdin.close(); proc.wait()
    print(f"DONE in {time.time()-t0:.0f}s -> {OUT}", flush=True)


if __name__ == "__main__":
    main()
