"""The love-psychology story engine — generative grammar, zero repeats.

generate_story(seed, used_hashes) builds a complete daily episode:
  * one long video script: cold open + 8 concept segments (hook ->
    mechanism -> real-life scene -> takeaway) + spoken outro
  * 4 vertical Short scripts derived from 4 of the day's concepts

Everything is a pure function of the seed: same seed in, same episode
out, forever — which is what makes crash-resume and deterministic
thumbnail rebuilds possible.

The script hash (sha1 of the full narration) is the no-repeat key: the
ledger refuses any script that was ever produced before. The seed
drifts internally on collision, and the FINAL (post-drift) seed is
what gets recorded — same convention the factory has always used.

Content safety gate: no diagnosis, no medical claims, no manipulation
framing — love content that names patterns, never pathologizes people.
"""
from __future__ import annotations

import hashlib

from .content_data import CTA_LINE, CONCEPTS, SERIES_NAME, TOPICS
from .rng import FactoryRNG

N_SEGMENTS = 8          # concepts per long video
N_SHORTS = 4            # shorts per day (drawn from the day's segments)
MAX_ATTEMPTS = 8        # audit-gate regeneration attempts

# audit: phrases that must never appear (medical / manipulative framing)
_BANNED = [
    "diagnos", "disorder", "cure ", "cures", "medicine", "medication",
    "mental illness", "therapy session", "guaranteed", "manipulat",
    "narcissist", "sociopath", "toxic person", "you are broken",
]


def _sentences(text: str) -> list[str]:
    out = [s.strip() for s in text.replace("\n", " ").split(". ")]
    return [s if s.endswith(".") else s + "." for s in out if s]


def _audit(text: str) -> bool:
    low = text.lower()
    return not any(b in low for b in _BANNED)


def _wordcount(*texts: str) -> int:
    return sum(len(t.split()) for t in texts)


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
        ea, pa, eb, pb = c["scene"]

        # scene A: the insight card (hook + mechanism)
        narr_a = f"{c['hook']} {c['explain']}"
        scenes.append({
            "n": len(scenes) + 1, "id": f"tip{i}_card", "narration": narr_a,
            "image": {"kind": "concept_card", "tip": i, "total": len(picked),
                      "term": c["term"], "headline": c["hook"],
                      "accent_word": None},
        })

        # scene B: the couple scene (example + takeaway)
        narr_b = f"{c['example']} {c['takeaway']}"
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

    # -- the 4 Shorts (drawn from the day's concepts) -------------------
    for j, key in enumerate(rng.some(picked, min(N_SHORTS, len(picked))), start=1):
        c = CONCEPTS[key]
        ex = _sentences(c["explain"])
        # pick an explanation sentence that is NOT the "psychologists call
        # this..." opener (we add our own term line — no double reveal)
        body = [s for s in ex if not s.lower().startswith("psychologists call")]
        body = (body or ex)[:1]
        script = (
            f"{c['hook']} "
            f"Psychologists call this {c['term']}. "
            f"{' '.join(body)} "
            f"{_sentences(c['example'])[0]} "
            f"{c['takeaway']} "
            f"{CTA_LINE}"
        )
        shorts.append({
            "n": j, "concept": key, "band": topic["band"],
            "hook": c["hook"], "term": c["term"],
            "script": script,
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
        "series": SERIES_NAME,
        "hook": topic["opener"],
        "words": words,
        "hash": digest,
        "seed": seed,
        "atoms": {"topic": topic["title"],
                  "concepts": [CONCEPTS[k]["term"] for k in picked]},
        "scenes": scenes,
        "shorts": shorts,
    }


def generate_story(seed: int, used_hashes: set[str] | None = None) -> dict:
    """Pure function of the seed. Raises RuntimeError if the audit and
    no-repeat gates cannot be satisfied within MAX_ATTEMPTS drifts."""
    used = used_hashes or set()
    for attempt in range(MAX_ATTEMPTS):
        story = _build(seed + attempt)          # drift on retry
        story["seed"] = seed + attempt          # record post-drift seed
        if story["hash"] in used:
            continue
        full = " ".join(s["narration"] for s in story["scenes"])
        if not _audit(full):
            continue
        return story
    raise RuntimeError(
        f"story engine exhausted {MAX_ATTEMPTS} attempts for seed {seed}")


def combination_space() -> int:
    """Rough lower bound on distinct daily episodes (topic x segment
    subsets x orderings) — before per-concept recombination in shorts."""
    from math import comb, perm
    total = 0
    for topic in TOPICS.values():
        k = min(N_SEGMENTS, len(topic["concepts"]))
        total += perm(len(topic["concepts"]), k)
    return int(total * comb(N_SEGMENTS, N_SHORTS))
