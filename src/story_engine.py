"""The generative story engine — every episode is brand new, forever.

This is NOT a story bank. The engine draws one atom per grammar dimension
(hero, name, trait, setting, time, object, companion, problem, quest,
moral, twist, motif), then weaves them through sixteen beat templates.
The combination space is counted in quadrillions; a ledger of used hashes
guarantees the machine never tells the same story twice.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from . import story_data as D
from .rng import FactoryRNG

WORDS_PER_TARGET = 1500
MIN_WORDS = 1450


def combination_space() -> int:
    """Exact size of the story-level combination space."""
    dims = [
        len(D.HEROES), len(D.NAMES), len(D.TRAITS), len(D.SETTINGS),
        len(D.TIMES), len(D.OBJECTS), len(D.COMPANIONS), len(D.PROBLEMS),
        len(D.QUESTS), len(D.MORALS), len(D.TWISTS), len(D.MOTIFS),
    ]
    n = 1
    for d in dims:
        n *= d
    return n


def _verbing(verb: str) -> str:
    """'drifted' -> 'drifting' (light morphology for the motif verbs)."""
    if verb == "rose":
        return "rising"
    if verb.endswith("ed"):
        stem = verb[:-2]
        if stem and stem[-1] not in "aeiou" and stem[-2:-1] in "aeiou" and len(stem) > 2:
            # CVC doubling: 'slipp' -> 'slipping'
            stem = stem + stem[-1]
        return stem + "ing"
    if verb.endswith("e") and verb not in ("be",):
        return verb[:-1] + "ing"
    return verb + "ing"


def _cap_first(s: str) -> str:
    return s[0].upper() + s[1:] if s else s


class SlotMap(dict):
    """Format map that also provides *_cap / *_lower variants."""

    def __init__(self, base: dict):
        super().__init__(base)
        # derived capitalized / lowered forms
        for key in ("hero_tiny", "companion_short", "object_warm", "moral",
                    "hero_short", "setting_full", "name", "object_short",
                    "problem_full", "problem_short", "quest_full",
                    "companion_full", "object_full", "trait_adj"):
            val = base.get(key)
            if val:
                self[f"{key}_cap"] = _cap_first(str(val))
        for key in ("object_noun", "motif_title", "setting_title"):
            val = base.get(key)
            if val:
                self[f"{key}_lower"] = str(val).lower()

    def __missing__(self, key):  # keep template crashes loud but readable
        raise KeyError(f"unknown story slot: {{{key}}}")


def draw_atoms(rng: FactoryRNG) -> dict:
    hero = rng.pick(D.HEROES)
    setting = rng.pick(D.SETTINGS)
    time_ = rng.pick(D.TIMES)
    obj = rng.pick(D.OBJECTS)
    comp = rng.pick(D.COMPANIONS)
    problem = rng.pick(D.PROBLEMS)
    quest = rng.pick(D.QUESTS)
    moral = rng.pick(D.MORALS)
    twist = rng.pick(D.TWISTS)
    motif = rng.pick(D.MOTIFS)

    name = rng.pick(D.NAMES)
    trait = rng.pick(D.TRAITS)

    slots = {
        # raw atoms (for the image engine + ledger)
        "_hero": hero, "_setting": setting, "_time": time_, "_object": obj,
        "_companion": comp, "_problem": problem, "_quest": quest,
        "_moral": moral, "_twist": twist, "_motif": motif,
        "_name": name, "_trait": trait,
        # prose slots
        "name": name,
        "hero_full": hero["full"], "hero_short": hero["short"],
        "hero_tiny": hero["tiny"], "hero_paws": hero["paws"],
        "hero_base": hero["base"],
        "trait_adj": trait["adj"], "trait_phrase": trait["phrase"],
        "setting_full": setting["full"], "setting_short": setting["short"],
        "setting_title": setting["title"],
        "setting_word": setting["title"].split()[-1],
        "time_full": time_["full"],
        "object_full": obj["full"], "object_short": obj["short"],
        "object_noun": obj["noun"], "object_warm": obj["warm"],
        "companion_full": comp["full"], "companion_short": comp["short"],
        "companion_noun": comp["noun"],
        "problem_full": problem["full"], "problem_short": problem["short"],
        "problem_noun": problem["noun"],
        "quest_full": quest["full"].format(name=name),
        "quest_short": quest["short"], "quest_noun": quest["noun"],
        "moral_full": moral["full"], "moral": moral["full"],
        "twist_full": twist["full"].format(name=name),
        "motif_thing": motif["thing"], "motif_one": motif["one"],
        "motif_verb": motif["verb"], "motif_verbing": _verbing(motif["verb"]),
        "motif_title": motif["thing"].title(),
    }
    return slots


def _title(rng: FactoryRNG, slots: dict) -> str:
    pattern = rng.pick(D.TITLE_PATTERNS)
    raw = pattern.format(
        name=slots["name"],
        object_noun=slots["object_noun"],
        setting_title=slots["setting_title"],
        problem_noun=slots["problem_noun"],
        quest_noun=slots["quest_noun"],
        companion_noun=slots["companion_noun"],
        motif_title=slots["motif_title"],
        setting_word=slots["setting_word"].title(),
    )
    # tidy: title-case except small words
    small = {"a", "an", "the", "and", "of", "in", "on", "to", "for"}
    words = []
    for i, w in enumerate(raw.split()):
        if w.lower() in small and i not in (0, len(raw.split()) - 1):
            words.append(w.lower())
        elif w.isupper() or w.istitle():
            words.append(w)
        else:
            words.append(w.capitalize())
    return " ".join(words)


def safety_audit(text: str) -> list[str]:
    """Return list of violations (empty list = pass). Word-boundary regex."""
    problems = []
    low = " " + text.lower() + " "
    for word in D.BLOCKED:
        if " " in word:  # phrase
            if word in low:
                problems.append(word)
        else:
            if re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", low):
                problems.append(word)
    return problems


def _expand(rng: FactoryRNG, slots: dict, scenes: list[dict], deficit: int) -> None:
    """Sprinkle calm sensory sentences until we reach the word target."""
    pool = rng.shuffle(D.EXPANSIONS)
    i = 0
    added = 0
    while added < deficit and pool:
        sent = pool[i % len(pool)].format_map(SlotMap(slots))
        scene = scenes[2 + (added * 5) % max(1, len(scenes) - 4)]
        scene["narration"] = scene["narration"].rstrip() + " " + sent
        added += len(sent.split())
        i += 1
        if i > 40:
            break


def generate_story(seed: int, used_hashes: set[str] | None = None,
                   max_attempts: int = 6) -> dict:
    """Generate one complete, audited, ledger-safe story.

    Regenerates (new seed each time) if the safety gate trips or the
    combination hash was ever used before. Raises RuntimeError after
    ``max_attempts`` exhausted failures.
    """
    used_hashes = used_hashes or set()
    last_fail = "unknown"
    for attempt in range(max_attempts):
        rng = FactoryRNG(seed + attempt * 7919)
        slots = draw_atoms(rng)

        # ledger hash over the story-level atom choices
        atom_repr = json.dumps(
            {
                "hero": slots["_hero"]["base"], "name": slots["_name"],
                "trait": slots["_trait"]["adj"],
                "setting": slots["_setting"]["title"],
                "time": slots["_time"]["mood"],
                "object": slots["_object"]["noun"],
                "companion": slots["_companion"]["noun"],
                "problem": slots["_problem"]["noun"],
                "quest": slots["_quest"]["noun"],
                "moral": slots["_moral"]["short"],
                "twist": slots["_twist"]["noun"],
                "motif": slots["_motif"]["thing"],
            },
            sort_keys=True,
        )
        story_hash = hashlib.sha256(atom_repr.encode()).hexdigest()[:24]

        if story_hash in used_hashes:
            last_fail = "combination already used (ledger)"
            seed += 104_729  # drift and retry
            continue

        scenes = []
        for idx, beat in enumerate(D.BEATS, start=1):
            template = rng.pick(beat["templates"])
            narration = template.format_map(SlotMap(slots)).strip()
            # clean double spaces
            narration = re.sub(r"[ \t]{2,}", " ", narration)
            scenes.append({
                "n": idx,
                "id": beat["id"],
                "narration": narration,
                "image": {
                    "type": beat["type"],
                    "focus": beat["focus"],
                    "camera": beat["camera"],
                    "hero_base": slots["_hero"]["base"],
                    "companion": slots["_companion"]["noun"].lower(),
                    "motif": slots["_motif"]["thing"],
                    "time_mood": slots["_time"]["mood"],
                    "sky": slots["_time"]["sky"],
                    "setting_title": slots["_setting"]["title"],
                },
            })

        # safety gate over the full narration (beat 1 to end)
        full_text = " ".join(s["narration"] for s in scenes)
        violations = safety_audit(full_text)
        if violations:
            last_fail = f"safety gate: {violations}"
            seed += 104_729
            continue

        words = len(full_text.split())
        if words < MIN_WORDS:
            _expand(rng, slots, scenes, MIN_WORDS - words)
            full_text = " ".join(s["narration"] for s in scenes)
            words = len(full_text.split())

        title = _title(rng, slots)
        hook = scenes[0]["narration"].split(".")[0].strip(" ,\"")

        return {
            "title": title,
            "hook": hook,
            "seed": seed,
            "hash": story_hash,
            "words": words,
            "atoms": {
                "hero": slots["_hero"]["full"],
                "name": slots["_name"],
                "setting": slots["_setting"]["full"],
                "time": slots["_time"]["full"],
                "object": slots["_object"]["full"],
                "companion": slots["_companion"]["full"],
                "problem": slots["_problem"]["full"],
                "quest": slots["_quest"]["full"],
                "moral": slots["_moral"]["full"],
                "twist": slots["_twist"]["full"],
                "motif": slots["_motif"]["thing"],
            },
            "scenes": scenes,
        }

    raise RuntimeError(f"story generation failed {max_attempts} times: {last_fail}")


def load_ledger(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("story_hashes", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_ledger(path: Path, hashes: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"story_hashes": sorted(hashes)}, indent=1),
        encoding="utf-8",
    )
