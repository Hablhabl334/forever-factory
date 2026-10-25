"""The muse layer regression tests (2026-10-25 LLM upgrade).

Locks in the contract that makes the muse safe to run unattended:
  * dormant without a key -> byte-identical grammar story (no-op
    guarantee: the machine cannot die because of the muse)
  * budget cap enforced inside state.json, shared across cycles
  * sanitizer: unicode punctuation / emoji -> plain ASCII
  * fake-stat guard: "73% of people" style claims never ship
  * shorts gates: term in the reveal (never in micro/facts), word
    band, hook length, opener is not a question
  * JSON extraction survives fenced / chatty model replies
  * cache round-trip: enhanced story replays byte-identical
  * LIVE (OPENROUTER_API_KEY set): a real enhancement of a fresh
    story - structure, audit and word bands against the live API

Run: python3 scripts/test_muse.py   (from repo root)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import muse
from src.story_engine import generate_story

PASS = 0
FAIL = 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {extra}")


print("== 1. dormant-muse no-op (the never-die contract) ==")
live_key = os.environ.get("OPENROUTER_API_KEY")
os.environ.pop("OPENROUTER_API_KEY", None)
os.environ.pop("MUSE", None)
story = generate_story(4242)
before_hash = story["hash"]
state: dict = {}
out = muse.enhance(story, state)
check("no key -> grammar story unchanged",
      out["hash"] == before_hash and out["muse"] == "grammar")
os.environ["MUSE"] = "0"
os.environ["OPENROUTER_API_KEY"] = "x"
check("MUSE=0 forces dormant even with key",
      muse.enhance(story, {})["muse"] == "grammar")
os.environ.pop("MUSE")
os.environ.pop("OPENROUTER_API_KEY")

print("== 2. budget ledger ==")
state = {}
for i in range(muse._DAILY_CAP):
    if not muse._spend(state):
        check("budget cap stops at limit", False, f"stopped early at {i}")
        break
check("budget cap reached exactly", not muse._spend(state),
      "spend past the cap")
check("budget stored in state", state["muse_budget"]["calls"] == muse._DAILY_CAP)
state["muse_budget"] = {"date": "2000-01-01", "calls": 99}
check("stale date resets the budget", muse._spend(state)
      and state["muse_budget"]["calls"] == 1)

print("== 3. sanitizer ==")
dirty = ("She pulls away\u2014not because she stopped caring\u2026 "
         "\u201cmaybe\u201d it\u2019s fear \U0001f5a4 mixed\u00a0spaces")
clean = muse._sanitize(dirty)
check("em-dash -> hyphen", "\u2014" not in clean and "-" in clean)
check("ellipsis expanded", "\u2026" not in clean and "..." in clean)
check("curly quotes -> straight", '"' in clean and "'" in clean)
check("emoji stripped", "\U0001f5a4" not in clean)
check("nbsp -> space", "\u00a0" not in clean)
check("no unicode survives", clean.isascii(), repr(clean))

print("== 4. content gates ==")
check("banned word blocked", not muse._clean_line("this is a toxic person"))
check("fake stat blocked", not muse._clean_line("73% of people feel this"))
check("ratio stat blocked", not muse._clean_line("9 out of 10 couples"))
check("plain line passes", muse._clean_line("The quiet ones feel the most."))

print("== 5. shorts field gates ==")
term = "the distancing dance"
good = {
    "opener": "She pulls away first.",
    "hook": "The one who leaves first is often the one who feels the most.",
    "micro": "He reads her message at midnight, types nothing for an hour, "
             "then puts the phone face-down on the table.",
    "fact1": "When closeness deepens, the nervous system registers it as "
             "pressure, so the body quietly searches for an exit before "
             "anything is even wrong.",
    "fact2": "From the outside it looks like sudden silence, canceled plans "
             "and jokes that keep every conversation safely on the surface.",
    "reveal": "Psychologists call this the distancing dance.",
    "takeaway": "Name the pattern out loud before you chase the silence "
                "for an answer.",
    "question": "Who was the first person to go quiet on you, and what did "
                "you tell yourself it meant?",
}
script = muse._valid_short(dict(good), term)
check("valid short assembles", script is not None,
      "" if script else "rejected a fully valid short")
check("term missing from reveal rejects",
      muse._valid_short({**good, "reveal": "Psychologists call this something."},
                        term) is None)
check("term inside micro rejects",
      muse._valid_short({**good,
                          "micro": "He does the distancing dance at noon."},
                         term) is None)
check("question opener rejects",
      muse._valid_short({**good, "opener": "Did she leave?"}, term) is None)
check("oversized hook rejects",
      muse._valid_short({**good, "hook": "word " * 20}, term) is None)
check("assembled band enforced",
      115 <= len(script.split()) <= 215 if script else False)

print("== 6. JSON extraction ==")
fenced = '```json\n{"scenes": ["a", "b"]}\n```'
check("fenced JSON parsed",
      (muse._extract_json(fenced) or {}).get("scenes") == ["a", "b"])
chatty = 'Here you go:\n{"shorts": [{"opener": "x"}]} hope it helps'
check("chatty reply parsed",
      "shorts" in (muse._extract_json(chatty) or {}))
check("garbage returns None", muse._extract_json("no json at all") is None)

print("== 7. cache round-trip ==")
story2 = generate_story(777)
story2["muse"] = "llm"
story2["muse_model"] = "test"
muse._cache_save(story2)
loaded = muse._cache_load(777)
check("cache saves and loads", loaded is not None)
check("cache is byte-faithful", loaded == story2)
muse._cache_path(777).unlink(missing_ok=True)

print("== 7.5 cache-only replay (thumbnail backfill path) ==")
s9 = generate_story(999)
check("cache_only miss -> grammar, no network",
      muse.enhance(s9, {}, cache_only=True)["muse"] == "grammar")
s9["muse"] = "llm"
muse._cache_save(s9)
back = muse.enhance(generate_story(999), {}, cache_only=True)
check("cache_only replays cached text without a key",
      back["hash"] == s9["hash"])
muse._cache_path(999).unlink(missing_ok=True)

print("== 8. LIVE enhancement (needs OPENROUTER_API_KEY) ==")
if not live_key:
    print("  SKIP  no key in env - offline path fully covered above")
else:
    story3 = generate_story(20261025)
    os.environ["OPENROUTER_API_KEY"] = live_key
    os.environ["MUSE"] = "1"
    live_state: dict = {}
    enhanced = muse.enhance(story3, live_state)
    check("live enhance returns a story", enhanced is not None)
    check("muse flag recorded", enhanced.get("muse") in ("llm", "grammar"))
    check("long hash recomputed", enhanced["hash"] != story3["hash"]
          or enhanced["muse"] == "grammar")
    check("scene count preserved", len(enhanced["scenes"]) == len(story3["scenes"]))
    check("image dicts untouched",
          all(a["image"] == b["image"] for a, b in
              zip(enhanced["scenes"], story3["scenes"])))
    check("shorts keep structure",
          all(set(s) >= {"n", "concept", "hook", "term", "script",
                        "words", "shash", "scene"}
              for s in enhanced["shorts"]))
    full = " ".join(s["narration"] for s in enhanced["scenes"])
    check("live text is ASCII-clean", full.isascii())
    check("live text passes banned-word audit", muse._clean_line(full))
    check("budget spent within contract",
          2 <= live_state["muse_budget"]["calls"] <= muse._DAILY_CAP,
          str(live_state.get("muse_budget")))
    replay = muse.enhance(generate_story(20261025), {"muse_budget": {"date": "x", "calls": 0}})
    check("cache replays byte-identical", replay == enhanced)
    print("  -- sample rewritten scene:")
    print("     ", enhanced["scenes"][2]["narration"][:110])
    print("  -- sample rewritten short script:")
    print("     ", enhanced["shorts"][0]["script"][:110])
    muse._cache_path(20261025).unlink(missing_ok=True)
    muse._cache_path(20261025).unlink(missing_ok=True)

print()
print(f"muse tests: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
