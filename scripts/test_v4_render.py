#!/usr/bin/env python3
"""v4 retention-build smoke test: one full Short through the NEW
pipeline (entrance pops, drift camera, opener hook card, SFX accents,
instant-attack bed, 6-word cards) + QA frames + audio checks."""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")

ROOT = Path("/home/z/my-project/download/forever-factory")
WORK = ROOT / "work" / "test_v4"
OUT = ROOT / "out" / "test_v4"
for p in (WORK, OUT):
    if p.exists():
        shutil.rmtree(p)

from src import shorts, story_engine, tts  # noqa: E402

t0 = time.time()
story = story_engine.generate_story(20261026)
print(f"story: '{story['title']}'  seed={story['seed']}  mood={story.get('mood')}")

s1 = story["shorts"][0]
print(f"short 1: term='{s1['term']}'  hook='{s1['hook'][:60]}...'")
print(f"script head: {s1['script'][:110]}...")

test_story = {"hash": f"{story['hash']}-v4test", "seed": story["seed"],
              "mood": story.get("mood", "warm"), "shorts": [s1]}

# resume-aware: keep clips, force the audio remix (level-law change)
for mw in (WORK / "short_01").glob("master.wav") if (WORK / "short_01").exists() else []:
    mw.unlink()

outs = shorts.render_shorts(test_story, WORK, OUT)
mp4 = outs[0]
dur = float(shorts.probe(mp4)["format"]["duration"])
print(f"\nRENDERED: {mp4.name}  {dur:.1f}s  {mp4.stat().st_size / 1e6:.1f}MB  "
      f"elapsed {time.time() - t0:.0f}s")

# ── QA 1: card inventory (what kinds rendered, durations) ──────────
clips = sorted((WORK / "short_01" / "clips").glob("[0-9][0-9].mp4"))
print(f"cards: {len(clips)}")

# ── QA 2: frames — first frames (pop), settled, term card ─────────
qa = ROOT / "work" / "v4_qa"
qa.mkdir(parents=True, exist_ok=True)
stamps = [0.0, 0.10, 0.28, 1.2, max(0.5, dur - 6)]
for t in stamps:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", str(t), "-i", str(mp4),
                    "-frames:v", "1", str(qa / f"frame_{t:.2f}.png")],
                   check=True)
print(f"QA frames: {[f'frame_{t:.2f}.png' for t in stamps]}")

# ── QA 3: audio — SFX accents present in master.wav? ───────────────
import numpy as np  # noqa: E402
import wave  # noqa: E402

with wave.open(str(WORK / "short_01" / "master.wav")) as w:
    sr = w.getframerate()
    nch = w.getnchannels()
    raw = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16) \
        .astype(np.float32) / 32768.0
    a = raw[0::nch] if nch > 1 else raw   # proper mono downmix
# bed energy in the first 0.5s (instant attack): should NOT be near-zero
first_half = np.abs(a[: int(0.5 * sr)]).mean()
later = np.abs(a[int(5 * sr): int(6 * sr)]).mean()
print(f"audio: mean |x| first 0.5s = {first_half:.4f} (5-6s = {later:.4f})")
assert first_half > 0.015, "bed not audible in first half second!"
# SFX pop near the hook landing (~0.24s): local peak should jump
win = a[int(0.15 * sr): int(0.40 * sr)]
ref = np.abs(a[int(0.05 * sr): int(0.15 * sr)]).mean()
print(f"pop window peak = {np.abs(win).max():.3f} (pre-pop mean {ref:.4f})")
assert np.abs(win).max() > 0.05, "hook SFX pop missing"

# narration chunk map: card kinds + accent times
meta = json.loads((WORK / "short_01" / "narration.json").read_text())
kinds = []
for i, ch in enumerate(meta["chunks"]):
    k = shorts._card_kind(ch["text"], i, s1.get("term"))
    kinds.append((i, round(ch["start"], 1), k, ch["text"][:38]))
for k in kinds[:8]:
    print("  ", k)
print("   ...")
for k in kinds[-4:]:
    print("  ", k)
hook_txt = kinds[0][3]
print(f"\nHOOK CARD TEXT (must be the short OPENER, 2-6 words): '{hook_txt}'")
assert len(hook_txt.split()) <= 7, "hook card shows too many words!"
print("\nSMOKE TEST PASS")
