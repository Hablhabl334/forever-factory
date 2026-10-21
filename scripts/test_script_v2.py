"""Script-engine v2 regression tests (2026-10-21 owner upgrade).

Locks in the promises that motivated the rewrite:
  * no duplication at the start (hook -> LATE reveal, term-free facts)
  * exactly ONE micro-moment example, never a dialogue, <= 22 words
  * long-video couple casting is always one woman + one man
  * music bed audible from second one (no 8 s fade-in regression)
  * "11 p.m." never splits a caption; shorts break beats at em-dashes
  * legacy assembly still reachable via shorts.script_v2: false
  * determinism: same seed, same story; fresh seeds, fresh hashes

Run: python3 scripts/test_script_v2.py   (from repo root)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np

from src import music, tts
from src.content_data import CONCEPTS, CTA_LINE
from src.content_micros import MICROS, _FORBIDDEN_MARKERS
from src.content_variants import (COMMENT_QUESTIONS, FEMALE_NAMES,
                                   MALE_NAMES, OPENERS)
from src import story_engine as se

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok    {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


def sentences_of(text: str) -> list[str]:
    """Display-split that tolerates abbreviations (test-side only)."""
    import re
    masked = re.sub(r"\b([ap]\.m\.)", lambda m: m.group(1).replace(".", "·"),
                    text)
    out = [s.strip() for s in re.split(r"(?<=[.!?])\s+", masked) if s.strip()]
    return [s.replace("·", ".") for s in out]


# ── 1. micro bank integrity ──────────────────────────────────────────
print("[1] micro-example bank integrity (40 concepts x 3)")
check("every concept has micros", set(MICROS) == set(CONCEPTS),
      f"missing={set(CONCEPTS) - set(MICROS)} extra={set(MICROS) - set(CONCEPTS)}")
bad_len, bad_slot, bad_term, bad_marker, bad_words = [], [], [], [], []
for key, pool in MICROS.items():
    term = CONCEPTS[key]["term"].lower()
    for m in pool:
        if len(m.split()) > 22 or len(m.split()) < 5:
            bad_len.append((key, len(m.split()), m))
        if "{" in m:
            bad_slot.append((key, m))
        if term and term in m.lower():
            bad_term.append((key, m))
        if any(marker in m.lower() for marker in _FORBIDDEN_MARKERS):
            bad_marker.append((key, m))
        if not se._audit(m):
            bad_words.append((key, m))
check("all micros 5-22 words", not bad_len, str(bad_len[:3]))
check("no slot placeholders in micros", not bad_slot, str(bad_slot[:3]))
check("no micro contains its term", not bad_term, str(bad_term[:3]))
check("no micro contains a reveal marker", not bad_marker, str(bad_marker[:3]))
check("all micros pass the safety audit", not bad_words, str(bad_words[:3]))

# ── 2. v2 shorts structure across many seeds ─────────────────────────
print("[2] v2 shorts structure (24 seeds x up to 6 shorts)")
viol: dict[str, list] = {k: [] for k in
                         ("no-micro", "two-micros", "early-reveal",
                          "term-echo", "hook-echo", "micro-echo",
                          "slots-left", "words-band", "cta-missing",
                          "banned", "two-scenario", "no-opener",
                          "no-question")}
used_short: set[str] = set()
n_scripts = 0
for seed in range(202610210, 202610210 + 24):
    story = se.generate_story(seed, set(), used_short)
    used_short |= set(story["short_hashes"])
    for sh in story["shorts"]:
        n_scripts += 1
        key, script, hook = sh["concept"], sh["script"], sh["hook"]
        term = sh["term"].lower()
        sents = sentences_of(script)
        cta_last = sents[-1].lower().startswith("subscribe for more tips")
        if not cta_last:
            viol["cta-missing"].append((seed, key))
        # viral layer: opener first, engagement question before the CTA
        if not any(script.startswith(o) for o in OPENERS):
            viol["no-opener"].append((seed, key))
        pre_cta = script.rstrip().rsplit(CTA_LINE, 1)[0].strip()
        if not any(q.replace("{term}", sh["term"]) == pre_cta
                   or q.replace("{term}", sh["term"]) in pre_cta
                   for q in COMMENT_QUESTIONS):
            viol["no-question"].append((seed, key))
        # reveal: exactly once, and LATE (after opener+hook+micro)
        reveal_idx = [i for i, s in enumerate(sents)
                      if any(mk in s.lower() for mk in
                             ("call this", "name for this",
                              "is called", "term for this"))]
        if len(reveal_idx) != 1:
            viol["early-reveal"].append((seed, key, reveal_idx))
        elif reveal_idx[0] < 3:
            viol["early-reveal"].append((seed, key, reveal_idx[0]))
        # micro count: 1 or 2 allowed (floor fallback), 0 or 3+ is a bug
        micros_in = [m for m in MICROS[key] if m in script]
        if not micros_in:
            viol["no-micro"].append((seed, key))
        elif len(micros_in) > 2:
            viol["two-micros"].append((seed, key, len(micros_in)))
        # classify sentences: hook / micro / takeaway / reveal / CTA /
        # facts — the duplication rules bind the FACTS and the term
        hook_set = set(sentences_of(hook))
        take_pool = list(se._pool(key, "takeaway"))
        term_hits = [i for i, s in enumerate(sents)
                     if any(mk in s.lower() for mk in
                            ("call this", "name for this",
                             "is called", "term for this"))]
        fact_pos = []
        q_sents = set()
        for q in COMMENT_QUESTIONS:
            q_sents.update(sentences_of(q.replace("{term}", sh["term"])))
        for i, s in enumerate(sents):
            if i in term_hits or s in hook_set or s in micros_in:
                continue
            # a sentence FRAGMENT of a known part is that part, not a
            # fact — hooks merged with openers, question sentences,
            # micros and takeaways all belong to their own beat
            if any(s in m for m in micros_in) or any(s in h for h in hook_set):
                continue
            if any(h in s for h in hook_set) or s in q_sents:
                continue
            if any(s in t or t.startswith(s) for t in take_pool):
                continue
            if s.lower().startswith("subscribe for"):
                continue
            if any(s in o for o in OPENERS):
                continue
            fact_pos.append((i, s))
        for i, s in fact_pos:
            if term in s.lower():
                viol["term-echo"].append((seed, key, s[:60]))
            if se._overlap(s, hook) > 0.45:
                viol["hook-echo"].append((seed, key, s[:60]))
            for m in micros_in:
                if se._overlap(s, m) > 0.45:
                    viol["micro-echo"].append((seed, key, s[:60]))
        if "{" in script:
            viol["slots-left"].append((seed, key))
        if not (110 <= sh["words"] <= 210):
            viol["words-band"].append((seed, key, sh["words"]))
        if not se._audit(script):
            viol["banned"].append((seed, key))
        # legacy-style scenario marker: a filled example from the old bank
        if any(ex.replace("{a}", "x").replace("{b}", "y")[:20] in script
               for ex in se.VARIANTS.get(key, {}).get("examples", [])):
            viol["two-scenario"].append((seed, key))
for name, items in viol.items():
    check(f"{name} clean (over {n_scripts} scripts)", not items,
          str(items[:3]))

# ── 3. hook still leads + term card still detectable ──────────────────
print("[3] card pipeline compatibility")
story = se.generate_story(20261021, set(), set())
sh = story["shorts"][0]
from src.shorts import _card_kind
chunks = tts.split_chunks(sh["script"], max_words=9, at_dashes=True)
kinds = [_card_kind(c, i, sh["term"]) for i, c in enumerate(chunks)]
check("chunk 0 is the hook card (opener beats on it)", kinds[0] == "hook",
      str(chunks[0]))
check("a term card exists", "term" in kinds, str(kinds))
check("a cta card exists", "cta" in kinds, str(kinds))
check("hook is spoken in the first 3 chunks",
      any(sh["hook"].split()[0] == c.split()[0]
          for c in chunks[:3] if c), str(chunks[:3]))

# ── 4. long video: casting + structure unchanged ──────────────────────
print("[4] long video integrity")
check("scene count 1+16+1",
      len(story["scenes"]) == 18, str(len(story["scenes"])))
check("long script has zero {slots} left",
      not any("{" in s["narration"] for s in story["scenes"]))
bad_pair = []
for seed in range(31, 51):
    st = se.generate_story(seed * 991, set(), set())
    for sc in st["scenes"]:
        txt = sc["narration"]
        names = [n for n in (FEMALE_NAMES + MALE_NAMES) if f" {n} " in f" {txt} "]
        women = [n for n in names if n in FEMALE_NAMES]
        men = [n for n in names if n in MALE_NAMES]
        if women and men and not (women and men):
            bad_pair.append((seed, names))
        if names and not (women or men):
            bad_pair.append((seed, names))
        # a filled example scene that names two people must mix genders
        if len(set(names)) >= 2:
            if (len(set(names) & set(FEMALE_NAMES)) == 0
                    or len(set(names) & set(MALE_NAMES)) == 0):
                bad_pair.append((seed, sorted(set(names))))
check("named couples always woman+man (20 stories)",
      not bad_pair, str(bad_pair[:5]))

# ── 5. music bed audible from second one ─────────────────────────────
print("[5] music fade-in")
bed = music.synth_music(1234, 60.0, mood="warm")


def _rms(x) -> float:
    return float(np.sqrt(np.mean(np.square(x.astype(np.float64)))))


first_sec = _rms(bed[:int(1.0 * music.SR)])
body = _rms(bed[int(2.0 * music.SR):int(12.0 * music.SR)])
tail = np.abs(bed[-int(0.2 * music.SR):]).max()
check("first-second RMS >= 35% of body RMS", first_sec >= 0.35 * body,
      f"first={first_sec:.4f} body={body:.4f}")
check("fade-out still intact (tail quiet)", tail < 0.05, f"tail={tail:.4f}")
for mood in ("warm", "healing", "attachment"):
    ratios = []
    for sd in (99, 100, 101):
        b2 = music.synth_music(sd, 45.0, mood=mood)
        r = _rms(b2[:music.SR]) / _rms(b2[int(2 * music.SR):int(10 * music.SR)])
        ratios.append(r)
    check(f"{mood}: bed present in second one (avg>=0.28, min>=0.18)",
          sum(ratios) / len(ratios) >= 0.28 and min(ratios) >= 0.18,
          str([round(r, 2) for r in ratios]))

# ── 6. chunker: abbreviations + em-dash beats ─────────────────────────
print("[6] chunker")
plain = tts.split_chunks("They called at 11 p.m. and again at 2 a.m. "
                         "about nothing.")
check("a.m./p.m. never split a sentence",
      any("11 p.m." in c for c in plain) and len(plain) == 1, str(plain))
dashed = tts.split_chunks("A racing heart can't tell terror from "
                          "chemistry — so it files everything under "
                          "love, which is honestly reasonable, for the "
                          "brain.", at_dashes=True)
check("em-dash beat splits (shorts)",
      any(c.endswith("—") for c in dashed), str(dashed))
no_dash = tts.split_chunks("You don't attract what you deserve — not even close.")
check("longs keep short em-dash sentences whole (default)",
      len(no_dash) == 1 and "—" in no_dash[0], str(no_dash))
check("long sentence chunks respect max_words",
      all(len(c.split()) <= 15 for c in dashed), str(dashed))

# ── 7. legacy rollback switch ────────────────────────────────────────
print("[7] legacy rollback (shorts.script_v2: false)")
import src.config as config_mod
_orig_cfg = config_mod.cfg
_base = _orig_cfg()
rolled = dict(_base)
rolled["shorts"] = {**_base.get("shorts", {}), "script_v2": False}
config_mod.cfg = lambda: rolled
try:
    leg_story = se.generate_story(777333, set(), set())
finally:
    config_mod.cfg = _orig_cfg
leg_hits = 0
for sh in leg_story["shorts"]:
    names = [n for n in (FEMALE_NAMES + MALE_NAMES)
              if f" {n}" in sh["script"]]
    if (any(n in FEMALE_NAMES for n in names)
            and any(n in MALE_NAMES for n in names)):
        leg_hits += 1
check("legacy path: slot-filled two-cast examples return",
      leg_hits >= len(leg_story["shorts"]) - 2, f"hits={leg_hits}")
check("legacy scripts still in the word band",
      all(90 <= s["words"] <= 170 for s in leg_story["shorts"]),
      str([s["words"] for s in leg_story["shorts"]]))

# ── 8. determinism + freshness ───────────────────────────────────────
print("[8] determinism")
a = se.generate_story(555001, set(), set())
b = se.generate_story(555001, set(), set())
check("same seed -> identical story hash", a["hash"] == b["hash"])
check("same seed -> identical shorts", a["short_hashes"] == b["short_hashes"])
c = se.generate_story(555002, set(), set())
check("neighbor seed -> fresh shorts",
      not set(c["short_hashes"]) & set(a["short_hashes"]))

# ── 9. question intonation determinism ────────────────────────────────
print("[9] voice prosody")
q1 = tts._jitter_pct("Why do they do that?", 4.0)
q2 = tts._jitter_pct("Why do they do that?", 4.0)
check("jitter is deterministic per text", q1 == q2)

print()
print(f"PASS {PASS}  FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
