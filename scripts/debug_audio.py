#!/usr/bin/env python3
"""Debug the quiet first 0.5s in the v4 short master."""
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, ".")
ROOT = Path("/home/z/my-project/download/forever-factory")
SW = ROOT / "work" / "test_v4" / "short_01"


def load(p):
    with wave.open(str(p)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16) \
            .astype(np.float32) / 32768.0
    return sr, x


sr, master = load(SW / "master.wav")
print(f"master sr={sr}  len={len(master) / sr:.2f}s")
for i in range(10):
    seg = master[int(i * 0.1 * sr): int((i + 1) * 0.1 * sr)]
    print(f"  t={i * 0.1:.1f}-{(i + 1) * 0.1:.1f}s  mean={np.abs(seg).mean():.4f}  peak={np.abs(seg).max():.4f}")

srn, narr = load(SW / "narration.wav")
print(f"\nnarration sr={srn}")
for i in range(6):
    seg = narr[int(i * 0.1 * srn): int((i + 1) * 0.1 * srn)]
    print(f"  t={i * 0.1:.1f}-{(i + 1) * 0.1:.1f}s  mean={np.abs(seg).mean():.4f}")

# bed alone with the exact v4 params
from src import music  # noqa: E402
bed = music.synth_music(1 + 700, 66.5, mood="healing", instant_attack=True)
print(f"\nbed(instant) first 0.5s mean={np.abs(bed[: int(0.5 * music.SR)]).mean():.4f}")
