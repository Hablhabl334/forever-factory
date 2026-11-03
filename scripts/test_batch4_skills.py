#!/usr/bin/env python3
"""batch-4 skill tests — THE DEPTH BUILD + THE VIRAL BRAIN.

Covers everything the 2026-11-01 batch added, plus the invariants it
must never break (seam law, text-layer immunity, fail-open, signal
floor, one-formula source of truth). Plain asserts, no pytest — the
factory's standing pattern.
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from src import anim, art_engine  # noqa: E402
from src import depth  # noqa: E402
from src import viral  # noqa: E402

FPS = 30
N_UNIQ = 120
T = N_UNIQ / FPS

SCENE = {"emotion_a": "happy", "pose_a": "stand",
         "emotion_b": "shy", "pose_b": "stand"}
TEXT = "the way you argue shows how you were loved as a child"


def _params(seed: int, style: str = "gentle_sway") -> list[dict]:
    ps = [anim._char_params(seed, style, i, T) for i in range(2)]
    for i, p in enumerate(ps):
        p["phase"] += 0.9 * i
    return ps


def _room_layers(seed: int = 42) -> dict:
    return art_engine.build_scene_card_layers(
        TEXT, "ATTACHMENT STYLES", SCENE, seed)


def _glow_layers(seed: int = 77) -> dict:
    return art_engine.build_concept_layers(
        3, 8, "anxious attachment",
        "calm love can feel boring at first", seed)


# ── 1. the depth engine ──────────────────────────────────────────────

def test_gates_default_on():
    assert depth.enabled() is True
    assert depth.motes_on() is True
    assert depth.shaft_mode() == "shimmer"


def test_split_geometry():
    layers = _room_layers()
    anim.compose_frame(layers, _params(1234), 0.0, T)   # triggers prepare
    dep = layers["depth"]
    w, h = layers["size"]
    assert dep["far"].size == (w + 2 * depth._PAD, h + 2 * depth._PAD)
    assert dep["floor"].size == (w, h - dep["floor_y"])
    assert len(dep["motes"]) == sum(b[0] for b in depth._MOTE_BANDS)
    # every mote: integer cycles (the seam law)
    for m in dep["motes"]:
        assert isinstance(m["cyc"], int) and m["cyc"] >= 1
    # room scenes may carry a shaft ladder of 5 periodic levels
    if dep["shaft"]:
        assert len(dep["shaft"]) in (1, depth._SHAFT_LEVELS)


def test_seam_law_room_and_glow():
    for layers, seed in ((_room_layers(), 1234), (_glow_layers(), 555)):
        ps = _params(seed)
        f0 = np.asarray(anim.compose_frame(layers, ps, 0.0, T))
        fT = np.asarray(anim.compose_frame(layers, ps, T, T))
        assert int(np.abs(f0.astype(int) - fT.astype(int)).max()) == 0, \
            "seam law broken: frame(T) != frame(0)"


def test_world_locked_no_camera_motion():
    """2026-11-03 owner law: THE CAMERA NEVER MOVES. No pan left or
    right, no zoom, no push-in. With the atmosphere stubbed out, the
    world under the couple must be pixel-identical between two
    arbitrary timestamps — a locked tripod. The atmosphere itself
    (motes, shaft) must stay alive, and the depth-of-field blur must
    survive (the far plane stays softer than the baked bg)."""
    for seed in (1234, 777, 2026):
        layers = _room_layers(seed)
        ps = _params(seed, anim.pick_style(seed))
        # stub the atmosphere: with motes + shaft silent, ANY far-plane
        # motion left would be pure camera parallax — there must be none
        orig_motes, orig_shaft = depth._draw_motes, depth._paste_shaft
        depth._draw_motes = lambda *a, **k: None
        depth._paste_shaft = lambda *a, **k: None
        try:
            w0 = np.asarray(
                depth.world_base(layers, ps, 0.0, T)).astype(int)
            w2 = np.asarray(
                depth.world_base(layers, ps, T / 2, T)).astype(int)
        finally:
            depth._draw_motes, depth._paste_shaft = orig_motes, orig_shaft
        floor_y = layers["depth"]["floor_y"]
        band = slice(0, max(1, floor_y - 60))   # above the shadow halo
        assert int(np.abs(w0[band] - w2[band]).max()) == 0, \
            "camera moved: the locked world shifted between frames"
    # the locked world is not a dead painting: the atmosphere keeps
    # the background alive with the camera frozen
    layers = _room_layers(42)
    ps = _params(42, anim.pick_style(42))
    f0 = np.asarray(anim.compose_frame(layers, ps, 0.0, T)).astype(int)
    f2 = np.asarray(anim.compose_frame(layers, ps, T / 2, T)).astype(int)
    bg = slice(0, 260)
    assert float(np.abs(f0[bg] - f2[bg]).mean()) > 0.0, \
        "atmosphere dead: motes/shaft stopped with depth on"
    # depth of field survives the lock: the far plane is softer than
    # the baked background in the same wall region
    dep = layers["depth"]
    box = (depth._PAD + 0, depth._PAD + 960, depth._PAD + 220, depth._PAD + 1660)
    far = np.asarray(dep["far"].crop(box).convert("L")).astype(float)
    ref = np.asarray(layers["bg"].crop((0, 960, 220, 1660)).convert("L")).astype(float)
    energy = lambda a: float(np.abs(np.diff(a, axis=1)).mean())
    assert energy(far) < energy(ref), \
        "depth of field lost: far plane as sharp as the baked bg"


def test_fail_open_legacy_identical():
    layers = _room_layers()
    ps = _params(1234)
    # depth ON frame
    on = anim.compose_frame(layers, ps, 0.7, T)
    # force the depth branch to explode -> must collapse to legacy
    orig = depth.world_base
    depth.world_base = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    fell = anim.compose_frame(layers, ps, 0.7, T)
    depth.world_base = orig
    # legacy reference: same card built with depth disabled
    orig_en = depth.enabled
    depth.enabled = lambda: False
    leg_layers = _room_layers()
    leg = anim.compose_frame(leg_layers, ps, 0.7, T)
    depth.enabled = orig_en
    assert np.asarray(fell).tobytes() == np.asarray(leg).tobytes(), \
        "fail-open frame != legacy frame"
    assert np.asarray(on).tobytes() != np.asarray(leg).tobytes(), \
        "depth frame identical to legacy (engine not running?)"


def test_shadows_recorded_vs_baked():
    # depth on -> recorded, not baked; static path still draws them.
    # Probe INSIDE the would-be ellipse, below the floor line: compare
    # against the floor's own ambient color (the vignette shifts raw
    # palette values by ~1, so reference a far pixel on the same row).
    layers = _room_layers()
    assert layers.get("shadows"), "shadows not recorded with depth on"
    sh = layers["shadows"][0]
    px, py = int(sh["x"]) + 30, int(sh["y"]) + 4
    rx = max(10, int(sh["x"]) - 220)          # same row, far from ellipse
    ref = layers["bg"].getpixel((rx, py))
    assert layers["bg"].getpixel((px, py)) == ref, \
        "shadow still baked into bg with depth on"
    static = art_engine.compose_static(layers)
    assert static.getpixel((px, py)) != ref, \
        "compose_static lost the contact shadows"
    # depth off -> baked into bg exactly as the legacy machine did
    orig = depth.enabled
    depth.enabled = lambda: False
    leg = _room_layers()
    depth.enabled = orig
    assert not leg.get("shadows"), "shadows recorded with depth OFF"
    assert leg["bg"].getpixel((px, py)) != ref, \
        "legacy bake path lost the shadow"


def test_text_layer_immunity():
    layers = _room_layers()
    ps = _params(1234)
    f0 = np.asarray(anim.compose_frame(layers, ps, 0.0, T)).astype(int)
    f2 = np.asarray(anim.compose_frame(layers, ps, T / 2, T)).astype(int)
    # the ink core of the text block never changes between frames
    core0, core2 = f0[500:700, 300:780] < 80, f2[500:700, 300:780] < 80
    assert (core0 == core2).all(), "text pixels mutated by depth layers"


def test_cache_names_mark_depth():
    from src.render import render_clip_art  # noqa: F401  (import check)
    import inspect
    src = inspect.getsource(render_clip_art)
    assert "_d4" in src, "render cache names lack the batch-4 marker"


def test_wall_structure_present():
    # the wainscot rail exists in the room bg (the parallax's rail)
    bg = np.asarray(_room_layers()["bg"]).astype(int)
    h = bg.shape[0]
    floor_y = int(h * 0.885)
    zone = bg[int(floor_y * 0.66):int(floor_y * 0.80), 5:75].mean(axis=2)
    g = np.abs(np.diff(zone, axis=0)).max(axis=1)
    assert g.max() >= 4.0, f"wainscot line missing (max gradient {g.max():.1f})"


# ── 2. the viral brain ───────────────────────────────────────────────

def test_score_title_known_cases():
    s_hi, n_hi = viral.score_title("Why You Push Away People You Love")
    assert s_hi >= 75, f"strong title scored {s_hi}"
    s_click, _ = viral.score_title("This ONE Secret Trick Will Change Your Love Life!!")
    assert s_click < 70, "clickbait tells not penalized"
    s_plain, _ = viral.score_title("relationship dynamics")
    assert s_plain < s_hi, "weak title must score below strong"
    for t in ("x", "", "Why You Push Away People You Love " * 3):
        s, _ = viral.score_title(t)
        assert 5 <= s <= 97, f"score out of bounds for {t[:20]!r}"


def test_formula_of():
    assert viral.formula_of("8 Signs You're In Love") == "NUMBER_LIST"
    assert viral.formula_of("How To Get Over A Breakup") == "HOW_TO"
    assert viral.formula_of("Red Flags People Ignore") == "WARNING"
    assert viral.formula_of("A Quiet Talk About Feelings") is None


def test_first_week_views_synthetic():
    pub = date.today() - timedelta(days=10)
    state = {
        "episodes": [{"n": 99, "title": "Test Long", "date": pub.isoformat(),
                      "status": "done", "ids": {"long": "vid1"}}],
        "analytics": [
            {"date": (pub + timedelta(days=1)).isoformat(),
             "videos": {"vid1": 4}},
            {"date": (pub + timedelta(days=5)).isoformat(),
             "videos": {"vid1": 19}},
            {"date": (pub + timedelta(days=9)).isoformat(),
             "videos": {"vid1": 26}},
        ],
    }
    assert viral.first_week_views(state, state["episodes"][0]) == 22
    state["episodes"][0]["ids"]["long"] = "missing"
    assert viral.first_week_views(state, state["episodes"][0]) is None


def test_build_feedback_signal_floor():
    # strong-signal synthetic state: median >= 5 -> block speaks
    today = date.today()
    eps, ana = [], []
    vid = 0
    for i in range(6):
        pub = today - timedelta(days=20 + i)
        vid += 1
        title = ("How To Heal After A Breakup" if i % 2
                 else "Thoughts About Relationships")
        eps.append({"n": 90 + i, "title": title, "date": pub.isoformat(),
                    "status": "done", "ids": {"long": f"v{vid}"}})
        # two snapshots per video: baseline then week-one value
        ana.append({"date": (pub + timedelta(days=1)).isoformat(),
                    "videos": {f"v{vid}": 2}})
        ana.append({"date": (pub + timedelta(days=6)).isoformat(),
                    "videos": {f"v{vid}": 30 if i % 2 else 5}})
    state = {"episodes": eps, "analytics": ana}
    fb = viral.build_feedback(state, today=today)
    assert fb["episodes"] == 6, fb
    assert fb["median_first_week_views"] >= 5, fb
    assert fb["by_formula"], "formula aggregation empty with signal"
    # feed it to the block reader (point the module at a temp file)
    orig_path = viral.FEEDBACK_PATH
    with tempfile.TemporaryDirectory() as td:
        viral.FEEDBACK_PATH = Path(td) / "viral_feedback.json"
        viral.FEEDBACK_PATH.write_text(json.dumps(fb))
        block = viral.feedback_block()
        assert "PATTERN FEEDBACK" in block
        assert "how to" in block.lower(), "winning shape not surfaced"
        # stale gate: 20 days old -> silent
        fb2 = dict(fb, week=(today - timedelta(days=20)).isoformat())
        viral.FEEDBACK_PATH.write_text(json.dumps(fb2))
        assert viral.feedback_block() == ""
        # signal floor: median 2 -> silent
        fb3 = dict(fb, median_first_week_views=2)
        fb3["week"] = today.isoformat()
        viral.FEEDBACK_PATH.write_text(json.dumps(fb3))
        assert viral.feedback_block() == ""
    viral.FEEDBACK_PATH = orig_path


def test_note_viral():
    state = {"episodes": [{"n": 7, "title": "x"}]}
    viral.note_viral(state, 7, {"score": 80, "formula": "HOW_TO",
                                "notes": ["you-address", "power word: why"]})
    v = state["episodes"][0]["viral"]
    assert v["score"] == 80 and v["formula"] == "HOW_TO"
    assert len(v["notes"]) == 2


def test_muse_feedback_block_wrapper():
    from src import muse
    # no feedback file in a pristine checkout state -> empty string
    orig_path = viral.FEEDBACK_PATH
    viral.FEEDBACK_PATH = Path(tempfile.mkdtemp()) / "nothing.json"
    assert muse._feedback_block() == ""
    viral.FEEDBACK_PATH = orig_path


def test_formulas_single_source():
    import tools.trend_intel as ti
    assert ti.FORMULAS is viral.FORMULAS, \
        "trend_intel defines its own FORMULAS — must import from src.viral"


def test_suggest_probe_parser():
    import tools.trend_intel as ti
    # offline: mock the network via a stub (no key, no net in tests)
    class _Resp:
        def read(self):
            return json.dumps(["why do i", [
                "why do i push people away",
                "why do i feel unwanted",
                "why do i sabotage relationships"]]).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
    orig_urlopen = ti.urllib.request.urlopen
    ti.urllib.request.urlopen = lambda req, timeout=15: _Resp()
    try:
        sug = ti.suggest(["why do i"])
        assert sug["why do i"][0] == "why do i push people away"
        words = ti.suggest_summary(sug, top=5)
        assert "push" in words and "unwanted" in words
    finally:
        ti.urllib.request.urlopen = orig_urlopen


def test_retention_probe_offline_and_graceful():
    import subprocess
    r = subprocess.run([sys.executable, "tools/retention_probe.py"],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, "probe must exit 0 even without a token"
    assert "token" in (r.stdout + r.stderr).lower()
    # offline replay of a synthetic snapshot
    comp = Path("data/competitive")
    comp.mkdir(parents=True, exist_ok=True)
    snap = {"date": date.today().isoformat(), "videos": [
        {"id": "a", "kind": "long", "ep": 40, "avg_view_pct": 41.0,
         "ctr_pct": 2.1, "views": 12, "title": "Red Flags People Ignore"}]}
    (comp / "retention_latest.json").write_text(json.dumps(snap))
    r2 = subprocess.run([sys.executable, "tools/retention_probe.py",
                         "--offline"], capture_output=True, text=True,
                        timeout=120)
    assert r2.returncode == 0 and "ep40" in r2.stdout
    (comp / "retention_latest.json").unlink()


# ── 3. orchestrator wiring (fail-open print path) ────────────────────

def test_orchestrator_wiring_present():
    src = Path("src/orchestrator.py").read_text()
    assert "viral score" in src and "note_viral" in src, \
        "viral pre-flight not wired in produce_episode"
    msrc = Path("src/muse.py").read_text()
    assert "_feedback_block()" in msrc, "muse brief lacks the feedback block"


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
        except Exception as exc:
            failed += 1
            print(f"  FAIL {name}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} batch-4 checks green")
    sys.exit(1 if failed else 0)
