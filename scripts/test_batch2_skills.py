#!/usr/bin/env python3
"""Regression suite for the batch-2 skill upgrades (2026-10-27):
hook-writer pattern layer, long-video curiosity bridges, Shorts
description SEO (youtube-seo), and the free transcript probe tool.
Every check is offline — no network, no API quota.
"""
import sys
from pathlib import Path

sys.path.insert(0, ".")

from src import metadata, story_engine  # noqa: E402
from src.content_data import CONCEPTS  # noqa: E402
from src.content_variants import BRIDGES, COMMENT_QUESTIONS, VARIANTS  # noqa: E402
from src.hook_patterns import PATTERN_HOOKS  # noqa: E402

PASS = FAIL = 0
def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    tag = "ok  " if cond else "FAIL"
    print(f"  {tag}  {name}" + (f" — {detail}" if detail and not cond else ""))
    PASS += 1 if cond else 0
    FAIL += 0 if cond else 1

print("── 1. the hook-writer pattern layer ──────────────────────")

# 1a. every concept has exactly one pattern hook; keys are real
ok("all pattern keys are real concepts",
   set(PATTERN_HOOKS) <= set(CONCEPTS),
   str(set(PATTERN_HOOKS) - set(CONCEPTS)))
ok("every concept covered (40)",
   set(PATTERN_HOOKS) == set(CONCEPTS),
   f"missing: {set(CONCEPTS) - set(PATTERN_HOOKS)}")

# 1b. writing rules per hook
banned = story_engine._BANNED_RE
pattern_texts = {h for pairs in PATTERN_HOOKS.values() for _, h in pairs}
bad_len, bad_audit, bad_term, bad_slots, dups = [], [], [], [], []
for key, pairs in PATTERN_HOOKS.items():
    term = CONCEPTS[key]["term"].lower()
    # the legacy pool = original + variants, MINUS the merged pattern
    # hooks (the import-time merge already appended them to VARIANTS)
    existing = [CONCEPTS[key].get("hook", "")] + \
        [h for h in VARIANTS.get(key, {}).get("hooks", [])
         if h not in pattern_texts]
    for pat, hook in pairs:
        w = len(hook.split())
        if not 8 <= w <= 30:
            bad_len.append((key, w))
        if banned.search(hook):
            bad_audit.append(key)
        if term and term in hook.lower():
            bad_term.append(key)
        if "{" in hook:
            bad_slots.append(key)
        if hook in existing:
            dups.append(key)
ok("all hooks 8-30 words", not bad_len, str(bad_len))
ok("all hooks pass the safety audit", not bad_audit, str(bad_audit))
ok("no hook leaks its term", not bad_term, str(bad_term))
ok("no slot placeholders in hooks", not bad_slots, str(bad_slots))
ok("no hook duplicates the existing pool", not dups, str(dups))

# 1c. pattern spread (the whole point)
pats = [p for pairs in PATTERN_HOOKS.values() for p, _ in pairs]
ok("at least 7 distinct patterns used", len(set(pats)) >= 7,
   str(sorted(set(pats))))
ok("no pattern owns more than a third of the pool",
   max(pats.count(p) for p in set(pats)) <= len(PATTERN_HOOKS) // 3 + 1,
   str({p: pats.count(p) for p in set(pats)}))

# 1d. the merge grew every hook pool by exactly its pattern hooks
# (legacy pools may dedupe — four concepts carry a variant identical
# to the original hook — so count UNIQUE legacy texts)
growth_ok = all(
    len(story_engine._pool(k, "hook")) ==
    len({CONCEPTS[k].get("hook", "")}
        | {h for h in VARIANTS.get(k, {}).get("hooks", [])
           if h not in pattern_texts})
    + len(PATTERN_HOOKS.get(k, []))
    for k in CONCEPTS)
ok("every hook pool = unique legacy + pattern hooks (merge exact)",
   growth_ok)
ok("every hook pool has 3+ variants (original/legacy/pattern)",
   all(len(story_engine._pool(k, "hook")) >= 3 for k in CONCEPTS))

print("── 2. the long video's curiosity bridges ─────────────────")

story = story_engine.generate_story(20261027)
ok("story generated with bridges active", story["hash"])

# 2a. every tip{i}_scene for i < N ends with a bridge; the LAST does not
n_seg = len(story["atoms"]["concepts"])
scene_by_id = {s["id"]: s for s in story["scenes"]}
mid_with, last_clean, repeats = 0, False, []
for i in range(1, n_seg + 1):
    narr = scene_by_id[f"tip{i}_scene"]["narration"]
    hits = [b for b in BRIDGES if narr.rstrip(". ").endswith(b.rstrip(". "))]
    if i < n_seg:
        mid_with += bool(hits)
        if hits:
            repeats.append(hits[0])
    else:
        last_clean = not hits
ok(f"segments 1..{n_seg - 1} each end on a bridge",
   mid_with == n_seg - 1, f"{mid_with}/{n_seg - 1}")
ok("the LAST segment has no bridge (outro follows it)", last_clean)
ok("no bridge repeats within an episode",
   len(repeats) == len(set(repeats)))

# 2b. bridges never leak a concept term or reveal marker
leak = [b for b in BRIDGES
        if any(c["term"].lower() in b.lower() for c in CONCEPTS.values())
        or any(m in b.lower() for m in
               ("call this", "is called", "term for"))]
ok("no bridge leaks a term or reveal marker", not leak, str(leak))

# 2c. bridge word budget (a breath, not a paragraph)
ok("every bridge is 8-18 words",
   all(8 <= len(b.split()) <= 18 for b in BRIDGES))

# 2d. safety audit over the whole episode (bridges included)
full = " ".join(s["narration"] for s in story["scenes"])
ok("full long narration passes the safety audit",
   story_engine._audit(full))

# 2e. determinism: same seed, same episode (bridges drawn in-stream)
story2 = story_engine.generate_story(20261027)
ok("same seed -> identical episode (determinism)",
   story["hash"] == story2["hash"]
   and story["scenes"] == story2["scenes"])

# 2f. the rollback flag: bridges off -> zero bridges anywhere
from src.config import cfg  # noqa: E402
cfg()["story"]["bridges"] = False
try:
    story_nb = story_engine.generate_story(20261027)
    any_bridge = any(
        b in s["narration"]
        for s in story_nb["scenes"] for b in BRIDGES)
    ok("story.bridges: false -> no bridge in any scene", not any_bridge)
finally:
    cfg()["story"]["bridges"] = True

# 2g. the outro still carries question + CTA (untouched)
outro = scene_by_id["outro_card"]["narration"]
ok("outro still ends with the CTA line", outro.rstrip().endswith(
    __import__("src.content_data", fromlist=["CTA_LINE"]).CTA_LINE))

print("── 3. Shorts description SEO (youtube-seo) ───────────────")

for short in story["shorts"][:2]:
    meta = metadata.short_metadata(story, short)
    ok(f"[short {short['n']}] title BYTE-identical to the locked line",
       meta["title"] == metadata.SHORT_TITLE)
    ok(f"[short {short['n']}] tags BYTE-identical to the locked list",
       meta["tags"] == list(metadata.SHORT_TAGS))
    d = meta["description"]
    ok(f"[short {short['n']}] description carries the concept term",
       short["term"].lower() in d.lower())
    ok(f"[short {short['n']}] description carries the hook line",
       short["hook"] in d)
    ok(f"[short {short['n']}] description opens with the question",
       d.startswith(story["question"]))
    ok(f"[short {short['n']}] description has the fixed hashtags",
       d.count(metadata.SHORT_HASHTAGS) >= 2)
    ok(f"[short {short['n']}] description carries the SEO keywords",
       "love psychology" in d.lower() and "relationship tips" in d.lower())
    ok(f"[short {short['n']}] description under 4900 chars",
       len(d) <= 4900)

print("── 4. the free transcript probe (offline parse) ──────────")

from tools import transcript_probe as tp  # noqa: E402

VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:03.000
the reason your ex keeps

00:00:00.500 --> 00:00:03.500
the reason your ex keeps

00:00:03.000 --> 00:00:06.000
coming back isn't love. It's a

00:00:06.000 --> 00:00:09.000
<c>loop</c> your brain never closed.
"""
text = tp.parse_vtt(VTT)
ok("vtt parsed to plain text",
   text == "the reason your ex keeps coming back isn't love. "
           "It's a loop your brain never closed.", repr(text))
hb = tp.hook_block(text, seconds=15)
ok("hook block returns the opening sentences",
   " ".join(hb).startswith("the reason your ex keeps"))
long_text = ("attachment is the blueprint. " * 4
             + "secure attachment grows with safety. " * 3
             + "anxious attachment scans for danger. " * 2)
phr = tp.top_phrases(long_text)
ok("top_phrases surfaces the repeated vocabulary",
   any("attachment" in p for p, _ in phr), str(phr))
ok("top_phrases ignores single stopwords",
   all(len(p.split()) >= 2 for p, _ in phr))

print("── 5. the whole machine still generates ──────────────────")

ok("shorts still carry v2 arc fields (hook/term/shash)",
   all({"hook", "term", "shash", "script"} <= set(s)
       for s in story["shorts"]))
ok("short scripts inside the 125-205 word band",
   all(125 <= len(s["script"].split()) <= 205 for s in story["shorts"]),
   str([len(s["script"].split()) for s in story["shorts"]]))
ok("short scripts unique within the episode",
   len({s["shash"] for s in story["shorts"]}) == len(story["shorts"]))
ok("long metadata still builds (title/desc/tags/chapters)",
   set(metadata.long_metadata(story, {
       "scene_durations": [10.0] * len(story["scenes"])})) ==
   {"title", "description", "tags", "chapters"})

print()
if FAIL:
    print(f"FAILED {FAIL} of {PASS + FAIL} checks")
    sys.exit(1)
print(f"ALL {PASS} CHECKS PASS — batch-2 skill upgrades are "
      f"regression-locked.")
