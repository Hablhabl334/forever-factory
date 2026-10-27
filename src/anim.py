"""The idle-animation engine — characters that are quietly ALIVE.

Before this module, every card was a still painting: the couple stood
frozen while a Ken Burns drift moved the whole frame. Then each card
became LAYERS (see art_engine) and this module breathed life into
the sprites at a true 30 fps:

  * sway — a slow sinusoidal side-to-side weight shift
  * bob  — a gentle vertical breathing rhythm
  * blink — natural eyelid drops, 2-4 s apart, never in unison

v2.1 — THE ARTICULATED RIG. The camera is now LOCKED (static
background, no zoom, no pan — motion comes from the characters
themselves) and each character is redrawn per frame through
art_engine.draw_figure(rig=...) with real articulation:

  * planted feet + hip sway  = an actual weight shift, never a float
  * free heel lift at the sway extreme (a half-step, knee bowing)
  * torso lean and breathing compression above the hips
  * arms pivoting at the shoulders, ending in real hands
  * a gentle REACH toward the partner — the couple's signature
    almost-touch, once per loop, never synchronized between them
  * head drift + nods (the hair follows automatically)
  * living eye gaze — slow glances toward and past the partner
  * blinks, exactly as before

Every motion is an INTEGER number of cycles per loop and every
gesture envelope is exactly zero at the loop seam, so the rendered
frame loop stays perfectly seamless — it can cycle forever with no
jump. The couple's APPEARANCE remains locked channel-wide; the
ANIMATION STYLE is still seeded per video (6 styles x per-card
parameter jitter x rig intensity per style).

The TEXT OVERLAY is never touched: it is composited last, on top,
from its own layer — characters live strictly underneath it.

Frames are piped straight into ffmpeg as raw video (no PNG round-trip
on disk) and encoded into a small loop.mp4 that the final clip render
replays — with a static camera (default) or the legacy Ken Burns
drift if `video.camera: kenburns` is ever set.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance

from . import art_engine

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

# v2.1 — how much limb articulation each style gets (multiplier on
# the seeded rig amplitudes). Lively styles gesture bigger; heavy,
# sad beats stay almost still. Purely additive: styles themselves
# are untouched.
RIG_INTENSITY: dict[str, float] = {
    "sync_breath": 0.85,
    "gentle_sway": 1.00,
    "counter_sway": 1.00,
    "weight_shift": 1.15,
    "lively": 1.30,
    "calm_bob": 0.70,
}


def rig_enabled() -> bool:
    """v2.1 master switch — `video.rig` in channel.yaml (default on).
    False restores the classic whole-sprite sway/bob/blink path."""
    try:
        from .config import cfg
        return bool(cfg().get("video", {}).get("rig", True))
    except Exception:
        return True


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

    # ── v2.1 articulated rig (additive — the legacy sprite path above
    # simply ignores these; every cycle count is an integer and every
    # gesture envelope is zero at the seam, so loops stay seamless) ──
    inten = RIG_INTENSITY.get(style, 1.0) * r.between(0.85, 1.15)
    rig = {
        # arms: 2 micro-cycles per loop, each arm on its own phase
        "arm_amp": r.between(0.30, 0.60) * min(1.15, inten),
        "arm_cyc": 2,
        "arm_phase": r.between(0.0, 2.0 * math.pi),
        "arm2_phase": r.between(0.0, 2.0 * math.pi),
        # the partner-reach: a squared-sine bump (exact 0 at the seam);
        # character 0 reaches once mid-loop, character 1 twice — never
        # synchronized. Damped on very short (fast-cut) loops.
        "reach_amp": r.between(0.30, 0.62) * inten
                     * min(1.0, max(0.55, T / 3.5)),
        "reach_k": 1 + idx,
        # hips carry the old sway amplitude (feet now stay planted)
        "hip_amp": sway_a * 0.8,
        "hip_cyc": int(scyc),
        "hip_phase": phase,
        "lean_amp": sway_a * r.between(0.22, 0.40),
        "lean_cyc": int(scyc),
        # head: one slow drift + a quicker nod; eyes glance on top
        "head_amp_x": r.between(3.5, 7.5) * min(1.20, inten),
        "head_cyc": 1,
        "head_phase": r.between(0.0, 2.0 * math.pi),
        "nod_amp": r.between(1.2, 2.8) * min(1.20, inten),
        "nod_cyc": 2,
        "nod_phase": r.between(0.0, 2.0 * math.pi),
        "gaze_amp": r.between(0.45, 0.95),
        "gaze_y_amp": r.between(0.15, 0.45),
        "gaze_cyc": 1,
        "gaze_phase": r.between(0.0, 2.0 * math.pi),
        # free heel lift at the hip-sway extreme (the half-step)
        "lift_max": r.between(0.35, 0.70) * min(1.20, inten),
        # breathing moves the chest, not the feet
        "bob_a": bob_a, "bob_cyc": int(bcyc), "bob_phase": bob_phase,
    }
    return {"sway_a": sway_a, "sway_cyc": int(scyc), "phase": phase,
            "bob_a": bob_a, "bob_cyc": int(bcyc), "bob_phase": bob_phase,
            "blinks": blinks, "rig": rig}


def _eye_at(prm: dict, t: float) -> str | None:
    """Blink phase: None (resting), 'half' or 'closed'."""
    for t0, t1 in prm["blinks"]:
        if t0 <= t < t1:
            frac = (t - t0) / (t1 - t0)
            return "half" if frac < 0.25 or frac > 0.78 else "closed"
    return None


def _rig_at(prm: dict, t: float, T: float) -> dict:
    """The articulated pose for one character at time t.

    Every term is periodic with an INTEGER cycle count over T (and the
    reach bump is a squared sine — exactly zero at u=0 and u=1), so
    frame(T) == frame(0) and the encoded loop never jumps at the seam.
    """
    rg = prm["rig"]
    two_pi = 2.0 * math.pi
    u = t / T

    # weight shift: hips sway, feet planted; the free heel lifts when
    # the hips move away from that leg
    sw = math.sin(two_pi * rg["hip_cyc"] * u + rg["hip_phase"])
    hip_dx = rg["hip_amp"] * sw
    lean_dx = rg["lean_amp"] * math.sin(
        two_pi * rg["lean_cyc"] * u + rg["hip_phase"] + math.pi / 2)
    lift_l = max(0.0, sw) * rg["lift_max"]      # hips right -> left free
    lift_r = max(0.0, -sw) * rg["lift_max"]     # hips left -> right free

    # arms: independent 2-cycle micro-swings (normalized -1..1)
    arm_l = rg["arm_amp"] * math.sin(
        two_pi * rg["arm_cyc"] * u + rg["arm_phase"])
    arm_r = rg["arm_amp"] * math.sin(
        two_pi * rg["arm_cyc"] * u + rg["arm2_phase"])

    # the partner-reach gesture: one soft bump per k-th of the loop
    reach = rg["reach_amp"] * (math.sin(math.pi * rg["reach_k"] * u) ** 2)

    # head: slow drift riding the shoulders + a quicker nod; gaze
    # drifts on its own slow cycle (the eyes look, then look away)
    head_dx = (rg["head_amp_x"] * math.sin(
        two_pi * rg["head_cyc"] * u + rg["head_phase"]) + hip_dx * 0.25)
    head_dy = rg["nod_amp"] * math.sin(
        two_pi * rg["nod_cyc"] * u + rg["nod_phase"])
    bob_dy = rg["bob_a"] * math.sin(
        two_pi * rg["bob_cyc"] * u + rg["bob_phase"])
    gx = rg["gaze_amp"] * math.sin(
        two_pi * rg["gaze_cyc"] * u + rg["gaze_phase"])
    gy = rg["gaze_y_amp"] * math.sin(
        two_pi * rg["gaze_cyc"] * u + rg["gaze_phase"] + 0.9)

    return {"hip_dx": hip_dx, "lean_dx": lean_dx, "bob_dy": bob_dy,
            "head_dx": head_dx, "head_dy": head_dy,
            "arm_l": arm_l, "arm_r": arm_r, "reach": reach,
            "lift_l": lift_l, "lift_r": lift_r, "gaze": (gx, gy)}


def compose_frame(layers: dict, params: list[dict], t: float,
                  T: float, skip_text: bool = False) -> Image.Image:
    """One frame: bg + living characters (+ text layer, ALWAYS last).

    v2.1: when the rig is enabled and the sprite carries its `spec`,
    each character is redrawn through art_engine.draw_figure(rig=...)
    with articulated limbs — feet planted, hips swaying, arms and head
    moving, eyes glancing. Otherwise the classic whole-sprite
    sway/bob/blink path runs, pixel-identical to the pre-rig era.

    THE TEXT OVERLAY IS NEVER TOUCHED in either path: it composites
    last, from its own transparent layer, on top of everything.

    v4: skip_text=True composites the world WITHOUT the text layer —
    used only by render_intro, which lands the text itself (scale+
    alpha entrance) so the words arrive as an event instead of
    existing since forever.
    """
    img = layers["bg"].copy()
    dr = None
    two_pi = 2.0 * math.pi
    rig_on = rig_enabled()
    for sp, prm in zip(layers.get("sprites", []), params):
        state = _eye_at(prm, t)
        if rig_on and prm.get("rig") and "spec" in sp:
            if dr is None:
                dr = ImageDraw.Draw(img)
            art_engine.draw_figure(
                dr, sp["anchor_x"], sp["feet_y"], sp["s"],
                dict(sp["spec"], eyes=state or sp["default"]),
                shadow=False, rig=_rig_at(prm, t, T))
            continue
        spr = sp[state or sp["default"]]
        dx = prm["sway_a"] * math.sin(
            two_pi * prm["sway_cyc"] * t / T + prm["phase"])
        dy = prm["bob_a"] * math.sin(
            two_pi * prm["bob_cyc"] * t / T + prm["bob_phase"])
        x = int(sp["anchor_x"] - sp["w"] / 2 + dx)
        y = int(sp["feet_y"] - (sp["h"] - 16) + dy)
        img.paste(spr, (x, y), spr)
    tl = None if skip_text else layers.get("text_layer")
    if tl is not None:
        img = Image.alpha_composite(img.convert("RGBA"), tl).convert("RGB")
    return img


# v4 entrance craft (hyperframes motion.md): "arrive slow, land
# still" — a long-tailed ease-out scale 1.055 -> 1.000. NOT a loop
# (the banned 'breathing/pulsing' default): the text lands ONCE per
# card, then holds dead still while the world keeps moving underneath
# it. ALPHA stays 1.0 from frame zero: frame 0 is the feed thumbnail
# — "one bold line already on screen", never a washed-out fade-in.
_INTRO_FRAMES = 9          # 0.30 s at 30 fps
_POP_SCALE = 1.055

# 2026-10-27 — Pop in (animation-vocabulary skill) for the CTA card:
# "appears with a slight overshoot, like it bounces into place."
# Applied to the LANDING only (frame 0 stays the full-size feed
# thumbnail): the same ease-out amplitude, damped by a cosine so the
# settle passes through ONE undershoot (~0.994) and lands EXACTLY on
# 1.0 at the seam — algebraically zero at u=1, so the loop never
# jumps. The final beat of every Short gets the peak-end treatment:
# the last thing a viewer feels is motion that ANSWERS, not a still.
_POP_WOBBLE = 2.2 * math.pi


def pop_scale(p: float, pop: bool = True) -> float:
    """Scale at progress p in [0,1]. pop=False is the v4 plain
    ease-out landing (unchanged); pop=True is the Pop-in settle:
    1.055 -> one gentle undershoot -> exactly 1.0."""
    e = 1.0 - (1.0 - p) ** 3               # cubic ease-out tail
    if pop:
        return 1.0 + (_POP_SCALE - 1.0) * (1.0 - e) * math.cos(_POP_WOBBLE * p)
    return _POP_SCALE - (_POP_SCALE - 1.0) * e


def render_intro(layers: dict, seed: int, style: str, fps: int,
                 n_unique: int, out: Path, dip: bool = False,
                 n_intro: int = _INTRO_FRAMES,
                 pop: bool = False) -> None:
    """Render the card's ENTRANCE segment as unique frames and encode
    to out (intro.mp4). n_unique MUST be the same loop length the
    caller hands to encode_loop: the intro is literally the loop's
    first n_intro frames with the text landing on top, so the seam
    intro->loop is frame-exact continuous (the replay then trims the
    loop to start at frame n_intro).

    dip=True (the term reveal and CTA): the first frames darken
    briefly (0.80 / 0.90 / 0.97) — a 'dip cut': the transition reads
    as meant, an accent instead of a swap.

    pop=True (the CTA only): the landing settles with one gentle
    Pop-in undershoot instead of the plain ease-out (peak-end craft:
    the subscribe ask is the final beat of every Short).

    Cached + atomic exactly like the loop."""
    if out.exists():
        return

    from .rng import FactoryRNG

    T = n_unique / fps           # same period encode_loop will use
    params = [_char_params(seed, style, i, T)
              for i in range(len(layers.get("sprites", [])))]
    jit = FactoryRNG(seed).between(0.0, 1.8)
    for i, prm in enumerate(params):
        prm["phase"] += jit * i    # SAME jitter as encode_loop

    w, h = layers["size"]
    tl = layers.get("text_layer")
    bbox = tl.getbbox() if tl is not None else None
    crop = tl.crop(bbox) if (tl is not None and bbox) else None
    cx = (bbox[0] + bbox[2]) / 2 if bbox else w / 2
    cy = (bbox[1] + bbox[3]) / 2 if bbox else h / 2

    dip_curve = (0.80, 0.90, 0.97)
    tmp = out.with_suffix(".tmp.mp4")
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
        for i in range(n_intro):
            frame = compose_frame(layers, params, i / fps, T,
                                  skip_text=crop is not None)
            if dip and i < len(dip_curve):
                frame = ImageEnhance.Brightness(frame).enhance(dip_curve[i])
            if crop is not None:
                p = i / max(1, n_intro - 1)
                scale = pop_scale(p, pop=pop)
                cw, ch = crop.size
                nw = max(1, round(cw * scale))
                nh = max(1, round(ch * scale))
                scaled = crop.resize((nw, nh), Image.BICUBIC)
                fr = frame.convert("RGBA")
                fr.alpha_composite(scaled, (int(cx - nw / 2), int(cy - nh / 2)))
                frame = fr.convert("RGB")
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        rc = proc.wait(timeout=120)
        if rc != 0:
            raise RuntimeError(
                f"intro encode failed: {proc.stderr.read()[-500:].decode()}")
        tmp.replace(out)
    finally:
        if proc.poll() is None:
            proc.kill()


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
