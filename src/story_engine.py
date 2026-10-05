"""The love-psychology story engine — generative grammar, zero repeats.

generate_story(seed, used_hashes, used_short_hashes) builds a complete
daily episode:
  * one long video script: cold open + 8 concept segments (hook ->
    mechanism -> real-life scene -> takeaway) + spoken outro
  * 4 vertical Short scripts derived from 4 of the day's concepts

Surface variation (the forever-bank layer, src/content_variants.py):
every concept renders a RANDOM surface each time it appears — hook,
example scene (slot-filled with names/places/days/times), and takeaway
are drawn from variant pools. The same concept can appear for years
and never produce the same script twice.

Everything is a pure function of the seed: same seed in, same episode
out, forever — which is what makes crash-resume and deterministic
thumbnail rebuilds possible.

No-repeat guarantees (both enforced by the ledger + seed drift):
  * the long script hash (sha1 of the full narration) is new
  * every Short's script hash (sha1 of its text) is new

Content safety gate: no diagnosis, no medical claims, no manipulation
framing — love content that names patterns, never pathologizes people.
"""
from __future__ import annotations

import hashlib
import re

from .content_data import CTA_LINE, CONCEPTS, SERIES_NAME, TOPICS
from .content_variants import (DAYS, NAMES, PLACES, TIMES, TOPIC_MOODS,
                               VARIANTS)
from .rng import FactoryRNG

N_SEGMENTS = 8          # concepts per long video
N_SHORTS = 4            # shorts per day (drawn from the day's segments)
MAX_ATTEMPTS = 8        # audit-gate regeneration attempts

# audit: medical / manipulative framing must never appear.
# word-boundary on cure/cures so words like "secure" never trip it.
_BANNED_RE = re.compile(
    r"diagnos|disorder|medicin|guaranteed|manipulat|narcissist|sociopath"
    r"|mental illness|therapy session|toxic person|you are broken"
    r"|\bcures?\b",
    re.IGNORECASE,
)


def _sentences(text: str) -> list[str]:
    out = [s.strip() for s in text.replace("\n", " ").split(". ")]
    return [s if s.endswith(".") else s + "." for s in out if s]


def _audit(text: str) -> bool:
    return _BANNED_RE.search(text) is None


def _wordcount(*texts: str) -> int:
    return sum(len(t.split()) for t in texts)


# ── the variation layer ─────────────────────────────────────────────

def _pool(key: str, field: str) -> list[str]:
    """A concept field as a variant pool: [original, *new variants]."""
    c = CONCEPTS[key]
    v = VARIANTS.get(key, {})
    pool = [c[field]] if c.get(field) else []
    for extra in v.get(field + "s", []):
        if extra not in pool:
            pool.append(extra)
    return pool or [c.get(field, "")]


def _fill_slots(text: str, rng: FactoryRNG) -> str:
    """Fill {a} {b} {day} {time} {place} with a consistent cast."""
    if "{" not in text:
        return text
    a, b = rng.some(NAMES, 2)
    day = rng.pick(DAYS)
    moment = rng.pick(TIMES)
    place = rng.pick(PLACES)
    return (text
            .replace("{a}", a).replace("{b}", b)
            .replace("{day}", day)
            .replace("{time}", moment)
            .replace("{place}", place))


def _render_surface(key: str, rng: FactoryRNG,
                    slotted_only: bool = False) -> dict:
    """One random surface for the concept (hook / scene / takeaway).

    slotted_only=True (Shorts): the example is drawn ONLY from the
    slot-filled variants — every Short script then contains a fresh
    cast/setting, so the no-repeat space stays in the billions. The
    long video (structural entropy already huge) keeps the full pool.
    """
    if slotted_only:
        slotted = VARIANTS.get(key, {}).get("examples", [])
        example_pool: list[str] = slotted or _pool(key, "example")
    else:
        example_pool = _pool(key, "example")
    hook = rng.pick(_pool(key, "hook"))
    takeaways = _pool(key, "takeaway")
    takeaway = rng.pick(takeaways)
    # echo guard: never let the takeaway repeat the hook's opening
    # metaphor (some variants deliberately rhyme)
    if hook[:25].lower() == takeaway[:25].lower():
        alts = [t for t in takeaways
                if t[:25].lower() != hook[:25].lower()]
        if alts:
            takeaway = rng.pick(alts)
    return {
        "hook": hook,
        "example": _fill_slots(rng.pick(example_pool), rng),
        "takeaway": takeaway,
    }


# reveal-line phrasings for Shorts (the signature "name the pattern"
# moment — varied so scripts never carbon-copy each other)
_REVEALS = [
    "Psychologists call this {term}.",
    "Psychologists have a name for this: {term}.",
    "In psychology, this is called {term}.",
    "There is a term for this in psychology: {term}.",
]


def _reveal_line(term: str, rng: FactoryRNG) -> str:
    return rng.pick(_REVEALS).replace("{term}", term)


def _fact_sentence(key: str, rng: FactoryRNG) -> str:
    """A standalone mechanism sentence for Shorts (never the reveal)."""
    body = [s for s in _sentences(CONCEPTS[key]["explain"])
            if not s.lower().startswith("psychologists call")]
    return rng.pick(body or _sentences(CONCEPTS[key]["explain"]))


def _short_hash(script: str) -> str:
    return hashlib.sha1(script.encode()).hexdigest()[:16]


# ── the episode builder ─────────────────────────────────────────────

def _build(seed: int) -> dict:
    rng = FactoryRNG(seed)

    topic_id, topic = rng.pick(list(TOPICS.items()))
    keys = [k for k in topic["concepts"] if k in CONCEPTS]
    picked = rng.some(keys, min(N_SEGMENTS, len(keys)))

    scenes: list[dict] = []
    shorts: list[dict] = []

    # -- scene 1: the opener card -------------------------------------
    intro = (f"{topic['opener']} "
             f"Today: {len(picked)} quiet pieces of psychology about "
             f"{topic['title'].lower()} — stay till the end, because "
             f"the one that hits you will not be the one you expect.")
    scenes.append({
        "n": 1, "id": "open_card", "narration": intro,
        "image": {"kind": "topic_card", "topic": topic["title"],
                  "band": topic["band"], "count": len(picked)},
    })

    # -- the 8 concept segments ----------------------------------------
    for i, key in enumerate(picked, start=1):
        c = CONCEPTS[key]
        surface = _render_surface(key, rng)
        ea, pa, eb, pb = c["scene"]

        # scene A: the insight card (hook + mechanism)
        narr_a = f"{surface['hook']} {c['explain']}"
        scenes.append({
            "n": len(scenes) + 1, "id": f"tip{i}_card", "narration": narr_a,
            "image": {"kind": "concept_card", "tip": i, "total": len(picked),
                      "term": c["term"], "headline": surface["hook"],
                      "accent_word": None},
        })

        # scene B: the couple scene (example + takeaway)
        narr_b = f"{surface['example']} {surface['takeaway']}"
        scenes.append({
            "n": len(scenes) + 1, "id": f"tip{i}_scene", "narration": narr_b,
            "image": {"kind": "couple_scene", "emotion_a": ea, "pose_a": pa,
                      "emotion_b": eb, "pose_b": pb,
                      "overlay": ["psychologists call this", c["term"]]},
        })

    # -- the outro (spoken CTA) ----------------------------------------
    outro = (f"That was {len(picked)} pieces of psychology about "
             f"{topic['title'].lower()}. If even one of them made your own "
             f"love life suddenly make sense, you already got your money's "
             f"worth — this one was free. {CTA_LINE}")
    scenes.append({
        "n": len(scenes) + 1, "id": "outro_card", "narration": outro,
        "image": {"kind": "outro_card", "topic": topic["title"]},
    })

    # -- the 4 Shorts (fresh surface draws, never the long's picks) ----
    for j, key in enumerate(rng.some(picked, min(N_SHORTS, len(picked))),
                            start=1):
        c = CONCEPTS[key]
        surface = _render_surface(key, rng, slotted_only=True)
        fact = _fact_sentence(key, rng)
        script = (
            f"{surface['hook']} "
            f"{_reveal_line(c['term'], rng)} "
            f"{fact} "
            f"{surface['example']} "
            f"{surface['takeaway']} "
            f"{CTA_LINE}"
        )
        # length guard: scripts are written to land 45-52s of speech
        # (owner rule: never under 45s); the renderer also enforces a
        # hard floor, so this only shapes the natural length.
        words = len(script.split())
        if words > 130:                      # drop the fact sentence first
            script = (f"{surface['hook']} "
                      f"{_reveal_line(c['term'], rng)} "
                      f"{surface['example']} "
                      f"{surface['takeaway']} "
                      f"{CTA_LINE}")
            words = len(script.split())
        if words > 134:                      # still long: first scene beat only
            script = (f"{surface['hook']} "
                      f"{_reveal_line(c['term'], rng)} "
                      f"{_sentences(surface['example'])[0]} "
                      f"{surface['takeaway']} "
                      f"{CTA_LINE}")
            words = len(script.split())
        shorts.append({
            "n": j, "concept": key, "band": topic["band"],
            "hook": surface["hook"], "term": c["term"],
            "script": script, "words": words,
            "shash": _short_hash(script),
            "scene": {"emotion_a": c["scene"][0], "pose_a": c["scene"][1],
                      "emotion_b": c["scene"][2], "pose_b": c["scene"][3]},
        })

    words = _wordcount(*[s["narration"] for s in scenes])
    digest = hashlib.sha1(
        "\n".join(s["narration"] for s in scenes).encode()).hexdigest()[:16]

    return {
        "title": topic["title"],
        "topic": topic_id,
        "topic_label": topic["band"],
        "mood": TOPIC_MOODS.get(topic_id, "warm"),
        "series": SERIES_NAME,
        "hook": topic["opener"],
        "words": words,
        "hash": digest,
        "seed": seed,
        "atoms": {"topic": topic["title"],
                  "concepts": [CONCEPTS[k]["term"] for k in picked]},
        "scenes": scenes,
        "shorts": shorts,
        "short_hashes": [s["shash"] for s in shorts],
    }


def generate_story(seed: int, used_hashes: set[str] | None = None,
                   used_short_hashes: set[str] | None = None) -> dict:
    """Pure function of the seed. Raises RuntimeError if the audit and
    no-repeat gates (long script AND all four Short scripts) cannot be
    satisfied within MAX_ATTEMPTS drifts."""
    used = used_hashes or set()
    used_short = used_short_hashes or set()
    for attempt in range(MAX_ATTEMPTS):
        story = _build(seed + attempt)          # drift on retry
        story["seed"] = seed + attempt          # record post-drift seed
        if story["hash"] in used:
            continue
        if any(sh in used_short for sh in story["short_hashes"]):
            continue
        full = " ".join(s["narration"] for s in story["scenes"])
        if not _audit(full):
            continue
        if not _audit(" ".join(s["script"] for s in story["shorts"])):
            continue
        return story
    raise RuntimeError(
        f"story engine exhausted {MAX_ATTEMPTS} attempts for seed {seed}")


def combination_space() -> int:
    """Honest lower bound on distinct content the factory can produce:
    long-episode structures x per-segment surface variants, plus the
    total distinct-Short space across all concepts (slot-filled)."""
    from math import perm

    # slot draws shared by every slotted example scene
    slot_draws = len(NAMES) * (len(NAMES) - 1) * len(DAYS) * len(TIMES) \
        * len(PLACES)

    shorts_space = 0
    for key in CONCEPTS:
        hooks = len(_pool(key, "hook"))
        facts = max(1, len([s for s in _sentences(CONCEPTS[key]["explain"])
                            if not s.lower().startswith("psychologists call")]))
        takeaways = len(_pool(key, "takeaway"))
        # Shorts draw slot-filled examples only — every script carries
        # a fresh cast/setting (the forever guarantee).
        slotted = len(VARIANTS.get(key, {}).get("examples", [])) or 1
        shorts_space += hooks * facts * takeaways * len(_REVEALS) \
            * slotted * slot_draws

    structural = 0
    for topic in TOPICS.values():
        k = min(N_SEGMENTS, len(topic["concepts"]))
        structural += perm(len(topic["concepts"]), k)

    # per-segment surface variants (>= 3 hooks x 3 examples x 3 takeaways)
    surface_per_segment = 27 ** min(N_SEGMENTS, 8)
    return structural * surface_per_segment + shorts_space
