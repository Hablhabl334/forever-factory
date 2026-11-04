#!/usr/bin/env python3
"""A/B listening samples for THE HUMAN EDGE (2026-11-05).

Renders the SAME ~35 s script through the SAME engine (vendored
Kokoro af_heart) twice:
  before.mp3 — humanize off  (the voice that shipped until today)
  after.mp3  — humanize on   (breaths, variable pauses, room tone,
               pacing life)

Offline, free, deterministic. Output goes to
/home/z/my-project/download/voice_human_ab/ for the owner's ears.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import config as config_mod  # noqa: E402
from src import tts  # noqa: E402

SCRIPT = (
    "You keep checking your phone, waiting for the reply that decides "
    "your whole day. The moment their name appears, your chest lifts. "
    "But when the screen stays dark, something heavier takes its place. "
    "Why does the quiet hurt more than the words ever did? Psychologists "
    "have a name for this loop, the push and pull that keeps you hooked. "
    "And once you see how it works, you cannot unsee it in almost every "
    "conversation you have."
)

STORY = {"hash": "voice-human-ab-sample",
         "scenes": [{"n": 1, "narration": SCRIPT}]}

OUT_DIR = Path("/home/z/my-project/download/voice_human_ab")


def render(tag: str, humanize: bool) -> dict:
    work = ROOT / "work" / f"ab_{tag}"
    if work.exists():
        shutil.rmtree(work)
    vconf = config_mod.cfg()["voice"]
    vconf["humanize"] = humanize
    meta = tts.narrate(STORY, work, chunk_words=10)
    wav = work / "narration.wav"
    mp3 = OUT_DIR / f"{tag}.mp3"
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
         "-i", str(wav), "-codec:a", "libmp3lame", "-b:a", "128k", str(mp3)],
        stdin=subprocess.DEVNULL, capture_output=True, timeout=300)
    if proc.returncode != 0:
        raise SystemExit(f"mp3 encode failed: {proc.stderr.decode()[-300:]}")
    return {"meta": meta, "mp3": mp3, "chunks": len(meta["chunks"])}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    before = render("before", humanize=False)
    after = render("after", humanize=True)
    for tag, r in (("before", before), ("after", after)):
        m = r["meta"]
        print(f"{tag}.mp3: {m['total']:.1f}s, {r['chunks']} chunks, "
              f"engine={m['engine']}, {r['mp3'].stat().st_size / 1024:.0f} KB")
    # restore the production gate (channel.yaml says humanize: true)
    config_mod.cfg()["voice"]["humanize"] = True


if __name__ == "__main__":
    main()
