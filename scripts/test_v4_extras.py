#!/usr/bin/env python3
"""Targeted checks: (1) long-path clip with ASS captions after drift,
(2) v4 thumbnail with the locked colored couple, (3) muse v4 gates."""
import sys
import shutil
from pathlib import Path

sys.path.insert(0, ".")

from src import art_engine, render, story_engine, thumbnails, muse  # noqa: E402

ROOT = Path("/home/z/my-project/download/forever-factory")
TMP = ROOT / "work" / "v4_checks"
if TMP.exists():
    shutil.rmtree(TMP)
TMP.mkdir(parents=True)

story = story_engine.generate_story(20261026)

# ── 1. long-path animated clip + ASS captions after drift ──────────
scene = next(s for s in story["scenes"]
             if s.get("image", {}).get("kind") == "couple_scene")
layers = art_engine.build_scene_layers(scene, story["seed"] + scene["n"] * 13)
ass = TMP / "cap.ass"
render.build_global_ass(
    [{"start": 0.0, "end": 3.0, "text": "psychologists call this attachment"},
     {"start": 3.2, "end": 6.0, "text": "the pattern is the person"}], 0.0, ass)
clip = TMP / "scene.mp4"
render.render_clip_art(layers, story["seed"], clip, 6.0, "zoom_in",
                       ass_file=ass, card_idx=3)
info = render.probe(clip)
dur = float(info["format"]["duration"])
fps = info["streams"][0]["avg_frame_rate"]
print(f"1. long clip: {dur:.2f}s @ {fps}  ({clip.stat().st_size/1e6:.2f}MB)")
assert 5.6 < dur < 6.4, "duration off"

# caption burned + drift: extract a mid frame, look for white text rows
import subprocess  # noqa: E402
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", "1.0", "-i", str(clip), "-frames:v", "1",
                str(TMP / "long_frame.png")], check=True)
from PIL import Image  # noqa: E402
import numpy as np  # noqa: E402
img = np.asarray(Image.open(TMP / "long_frame.png").convert("RGB"), dtype=np.int16)
bottom = img[950:1030, 300:1620]     # caption band (MarginV 92)
white = (bottom.min(axis=2) > 220).mean()
print(f"   caption band white-pixel share: {white:.4f}")
assert white > 0.005, "ASS captions missing after drift!"

# ── 2. v4 thumbnail: locked colored couple ─────────────────────────
thumb = TMP / "thumb.png"
thumbnails.make_thumbnail(story, thumb, story["seed"])
t = np.asarray(Image.open(thumb).convert("RGB"), dtype=np.int16)
h, w = t.shape[:2]
couple_band = t[430:700, 380:900]    # where the couple stands
# colored couple => saturated non-grey pixels (plum top 150,84,118 / teal 84,116,128)
sat = (couple_band.max(axis=2) - couple_band.min(axis=2))
colored = (sat > 40).mean()
print(f"2. thumbnail: {w}x{h}, colored-couple px share in band: {colored:.4f}")
assert colored > 0.01, "locked colored couple missing from thumbnail!"

# ── 3. muse v4 gates: opener/hook overlap + micro sentence cap ─────
good = {"opener": "Three texts. No reply.",
        "hook": "The person who answers slowest is often the one listening hardest, and almost nobody believes this.",
        "micro": "She double-texts the question, waits, watches the typing dots appear and vanish, then puts the phone in a drawer and calls it nothing.",
        "fact1": "When someone takes their time replying to you, the delay is often careful word choice happening behind the scenes, not indifference hiding behind a busy schedule.",
        "fact2": "Instant answers feel like real chemistry on the first night, but sustained attention over weeks is the thing that actually predicts whether the care will last past the honeymoon.",
        "reveal": "Psychologists call this responsiveness pacing.",
        "takeaway": "Before you read silence as losing interest, ask one direct question and watch what happens next.",
        "question": "Who in your life replies slowly but always shows up when it actually matters?"}
ok = muse._valid_short(dict(good), "responsiveness pacing")
print(f"3a. valid script accepted: {ok is not None}")
assert ok is not None

bad = dict(good)
bad["hook"] = "Three texts tell you who actually listens around here."  # 'texts' repeat
rej = muse._valid_short(dict(bad), "responsiveness pacing")
print(f"3b. opener-word-in-hook rejected: {rej is None}")
assert rej is None

bad2 = dict(good)
bad2["micro"] = "She waits. He types. She waits again. He stops. Nothing."
rej2 = muse._valid_short(dict(bad2), "responsiveness pacing")
print(f"3c. 5-sentence micro rejected: {rej2 is None}")
assert rej2 is None

print("\nALL V4 CHECKS PASS")
