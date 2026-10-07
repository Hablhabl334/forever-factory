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
# Shorts SPEC capacity per story. The daily grid needs 4, but a heal
# day (a failed cycle left holes) needs up to 5-6 to refill every
# free slot in the next 24h — the orchestrator slices what the grid
# owes, this is only the ceiling. The extra specs' hashes join the
# no-repeat bank even when unsliced (the shorts space is ~10^15 —
# no practical depletion). NOTE: deterministic replay of PRE-ep17
# stories (thumbnail backfill) uses the 4-spec draw sequence and
# will not replay under 6 — harmless: every existing long already
# has its thumbnail set; future episodes replay consistently.
N_SHORTS = 6
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


def _shorts_script(key: str, c: dict, rng: FactoryRNG) -> tuple[str, int, str]:
    """Assemble a Short script whose NARRATION runs ~60-80 s of speech.

    Owner rule: the VOICE itself must exceed 45 s and END with the
    video — a Short is never padded with silent seconds. Script,
    animation, narration and music all end together. Calibration is
    MEASURED, not estimated: Jenny's effective pace at the shorts
    rate is ~117 wpm (157 words -> 80.8 s in a live test), so the
    word band is 105-160 words (~54-82 s), comfortably inside the
    45 s floor and the 90 s (1:30) cap the owner allows.
    Returns (script, words, hook) — the hook doubles as the Short's
    first-card headline."""
    surface = _render_surface(key, rng, slotted_only=True)
    reveal = _reveal_line(c["term"], rng)

    # mechanism facts: distinct sentences from the explain block
    body = [s for s in _sentences(c["explain"])
            if not s.lower().startswith("psychologists call")]
    facts = rng.some(body, min(2, len(body)))

    # second example beat: a DIFFERENT slot-filled scene (fresh cast)
    pool = list(VARIANTS.get(key, {}).get("examples") or [])
    if not pool:
        pool = _pool(key, "example") or []
    example2 = ""
    for tmpl in rng.shuffle(pool):
        cand = _fill_slots(tmpl, rng)
        if cand != surface["example"]:
            example2 = cand
            break

    # floor: keep appending unused mechanism sentences until the
    # speech comfortably exceeds 45 s (~105 words at the measured
    # 117-wpm effective pace)
    extra: list[str] = []
    words = (len(surface["hook"].split()) + len(reveal.split())
             + sum(len(f.split()) for f in facts)
             + len(surface["example"].split()) + len(example2.split())
             + len(surface["takeaway"].split()) + len(CTA_LINE.split()))
    for s in rng.shuffle([s for s in body if s not in facts]):
        if words >= 105:
            break
        extra.append(s)
        words += len(s.split())

    parts = [surface["hook"], reveal,
             facts[0] if facts else "",
             surface["example"],
             facts[1] if len(facts) > 1 else "",
             *extra,
             example2,
             surface["takeaway"],
             CTA_LINE]
    script = " ".join(p for p in parts if p)

    # ceiling (~82 s at the measured pace): shed weight — extra
    # facts, then the second example's later beats, then the second
    # example entirely
    while len(script.split()) > 160:
        if extra:
            extra.pop()
        elif example2:
            sents = _sentences(example2)
            if len(sents) > 1:
                example2 = " ".join(sents[:len(sents) - 1])
            else:
                example2 = ""
        elif len(facts) > 1:
            facts = facts[:1]
        else:
            break
        parts = [surface["hook"], reveal,
                 facts[0] if facts else "",
                 surface["example"],
                 facts[1] if len(facts) > 1 else "",
                 *extra,
                 example2,
                 surface["takeaway"],
                 CTA_LINE]
        script = " ".join(p for p in parts if p)
    words = len(script.split())
    return script, words, surface["hook"]


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
        script, words, hook = _shorts_script(key, c, rng)
        shorts.append({
            "n": j, "concept": key, "band": topic["band"],
            "hook": hook, "term": c["term"],
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
