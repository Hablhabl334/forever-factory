"""The idle-animation engine — characters that are quietly ALIVE.

Before this module, every card was a still painting: the couple stood
frozen while a Ken Burns drift moved the whole frame. Now each card is
built as LAYERS (see art_engine) and this module breathes life into
the sprites at a true 30 fps:

  * sway — a slow sinusoidal side-to-side weight shift
  * bob  — a gentle vertical breathing rhythm
  * blink — natural eyelid drops, 2-4 s apart, never in unison

Every motion is an INTEGER number of cycles per loop, so the rendered
frame loop is seamless — the animation can cycle forever with no jump.
The couple's APPEARANCE is locked channel-wide (same two people every
video, forever); the ANIMATION STYLE is seeded per video, so every day
moves differently: 6 styles x per-card parameter jitter.

Frames are piped straight into ffmpeg as raw video (no PNG round-trip
on disk) and encoded into a small loop.mp4 that the final clip render
replays with the Ken Burns drift on top.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

from PIL import Image

# name: (sway_px_lo, sway_px_hi, sway_cycles, bob_px_lo, bob_px_hi,
#         bob_cycles, blink_lo_s, blink_hi_s, mirror, sync_bob, lead)
ANIM_STYLES: dict[str, tuple] = {
    # romantic default: both breathe in the same slow rhythm
    "sync_breath":   (3.0, 6.0, 1, 3.5, 5.5, 2, 2.8, 4.6, False, True, 1.0),
    # each sways on their own phase — everyday, lived-in
    "gentle_sway":   (7.0, 11.0, 2, 2.0, 4.0, 3, 2.6, 4.4, False, False, 1.0),
    # mirror-image swaying — feels choreographed, cute
    "counter_sway":  (9.0, 13.0, 2, 2.0, 3.0, 3, 2.4, 4.2, True, False, 1.0),
    # one partner shifts weight big, the other stays almost still
    "weight_shift":  (12.0, 17.0, 1, 1.0, 3.0, 2, 2.8, 4.6, False, False, 1.7),
    # quicker, bouncier, more blinks — high-energy scenes
    "lively":        (8.0, 12.0, 3, 3.0, 5.0, 4, 1.8, 3.2, False, False, 1.0),
    # nearly still, just breathing — for heavy/sad beats
    "calm_bob":      (3.5, 6.5, 1, 3.0, 5.0, 3, 3.2, 5.2, False, True, 1.0),
}

STYLE_NAMES = list(ANIM_STYLES.keys())


def pick_style(seed: int) -> str:
    """One animation style per VIDEO — different movement every day."""
    from .rng import FactoryRNG
    return FactoryRNG(seed).pick(STYLE_NAMES)


def _char_params(seed: int, style: str, idx: int, T: float) -> dict:
    """Sway/bob/blink parameters for one character in one card."""
    from .rng import FactoryRNG
    r = FactoryRNG(seed + idx * 613)
    (slo, shi, scyc, blo, bhi, bcyc, wlo, whi,
     mirror, sync_bob, lead) = ANIM_STYLES[style]

    lead_factor = lead if idx == 0 else 1.0 / lead
    sway_a = r.between(slo, shi) * (lead_factor ** 0.5)
    bob_a = r.between(blo, bhi) * (lead_factor ** 0.5)
    phase = r.between(0.0, 2.0 * math.pi)
    if mirror and idx == 1:
        phase += math.pi
    bob_phase = phase if sync_bob else r.between(0.0, 2.0 * math.pi)

    # blinks: seeded count, never near the loop seam, 100-160 ms long
    avg = (wlo + whi) / 2.0
    n_blinks = max(1, int(round(T / avg)))
    blinks: list[tuple[float, float]] = []
    t = r.between(0.4, min(1.6, T * 0.35))
    while t < T - 0.8 and len(blinks) < n_blinks:
        dur = r.between(0.10, 0.16)
        blinks.append((t, t + dur))
        t += r.between(wlo, whi)
    return {"sway_a": sway_a, "sway_cyc": int(scyc), "phase": phase,
            "bob_a": bob_a, "bob_cyc": int(bcyc), "bob_phase": bob_phase,
            "blinks": blinks}


def _eye_at(prm: dict, t: float) -> str | None:
    """Blink phase: None (resting), 'half' or 'closed'."""
    for t0, t1 in prm["blinks"]:
        if t0 <= t < t1:
            frac = (t - t0) / (t1 - t0)
            return "half" if frac < 0.25 or frac > 0.78 else "closed"
    return None


def compose_frame(layers: dict, params: list[dict], t: float,
                  T: float) -> Image.Image:
    """One frame: bg + swaying/bobbing/blinking sprites (+ text layer)."""
    img = layers["bg"].copy()
    two_pi = 2.0 * math.pi
    for sp, prm in zip(layers.get("sprites", []), params):
        state = _eye_at(prm, t)
        spr = sp[state or sp["default"]]
        dx = prm["sway_a"] * math.sin(
            two_pi * prm["sway_cyc"] * t / T + prm["phase"])
        dy = prm["bob_a"] * math.sin(
            two_pi * prm["bob_cyc"] * t / T + prm["bob_phase"])
        x = int(sp["anchor_x"] - sp["w"] / 2 + dx)
        y = int(sp["feet_y"] - (sp["h"] - 16) + dy)
        img.paste(spr, (x, y), spr)
    tl = layers.get("text_layer")
    if tl is not None:
        img = Image.alpha_composite(img.convert("RGBA"), tl).convert("RGB")
    return img


def encode_loop(layers: dict, seed: int, style: str, fps: int,
                n_unique: int, loop_path: Path) -> None:
    """Render the unique-frame loop and pipe it into loop.mp4 (x264 crf 15).
    Atomic: writes to a tmp file, renames on success."""
    from .rng import FactoryRNG

    if loop_path.exists():
        return  # cached (resumable — frame count is part of the filename)

    T = n_unique / fps
    params = [_char_params(seed, style, i, T)
              for i in range(len(layers.get("sprites", [])))]
    # tiny per-card horizontal jitter so identical emotions never sync
    jit = FactoryRNG(seed).between(0.0, 1.8)
    for i, prm in enumerate(params):
        prm["phase"] += jit * i

    w, h = layers["size"]
    tmp = loop_path.with_suffix(".tmp.mp4")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
         "-r", str(fps), "-i", "-",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "15",
         "-g", str(fps * 2), "-pix_fmt", "yuv420p", str(tmp)],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    try:
        for i in range(n_unique):
            frame = compose_frame(layers, params, i / fps, T)
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        rc = proc.wait(timeout=180)
        if rc != 0:
            raise RuntimeError(
                f"loop encode failed: {proc.stderr.read()[-500:].decode()}")
        tmp.replace(loop_path)
    finally:
        if proc.poll() is None:          # never leave ffmpeg hanging
            proc.kill()
