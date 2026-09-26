"""Deterministic seeded randomness — the machine's imagination dice.

Every story, artwork and soundtrack is a pure function of its integer seed.
The same seed always rebuilds the same episode byte-for-byte, which makes
rendering resumable and the whole factory reproducible for a decade.
"""
from __future__ import annotations

import random


class FactoryRNG:
    """Thin wrapper that keeps named sub-streams independent."""

    def __init__(self, seed: int):
        self.seed = int(seed)
        self._rng = random.Random(self.seed)

    # -- primitive draws ------------------------------------------------
    def pick(self, seq):
        return self._rng.choice(seq)

    def some(self, seq, k: int):
        seq = list(seq)
        k = min(k, len(seq))
        return self._rng.sample(seq, k)

    def below(self, n: int) -> int:
        return self._rng.randrange(max(1, n))

    def chance(self, p: float) -> bool:
        return self._rng.random() < p

    def between(self, lo: float, hi: float) -> float:
        return self._rng.uniform(lo, hi)

    def shuffle(self, seq):
        seq = list(seq)
        self._rng.shuffle(seq)
        return seq
