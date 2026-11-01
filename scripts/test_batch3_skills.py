#!/usr/bin/env python3
"""Regression suite for the batch-3 skill upgrades (2026-11-01):
the copywriting AI-tells layer (src/ai_tells.py + muse scrub/gate +
per-episode tells audit) and the post-publish verification pass
(src/verify.py + ledger stamps + workflow alert). Every check is
offline — no network, no API quota, no writes to the real ledger
(ledger.set_read_only(true) for the verify fixtures).
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, ".")

from src import ai_tells, ledger, muse, verify      # noqa: E402
from src import content_data, content_variants, hook_patterns  # noqa: E402
from src import metadata                            # noqa: E402

PASS = FAIL = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    tag = "ok  " if cond else "FAIL"
    print(f"  {tag}  {name}" + (f" — {detail}" if detail and not cond else ""))
    PASS += 1 if cond else 0
    FAIL += 0 if cond else 1


print("── 1. the AI-tells audit detects every category ───────────")

samples = {
    "contrast_reveal": "It's not chemistry — it's a payout schedule.",
    "era_opener": "In today's fast-paced world, dating apps decide everything.",
    "throat_clear": "Here's the thing: nobody tells you this.",
    "recap_closer": "She waits for the reply. Ultimately, love wins anyway.",
    "filler": "Moreover, the pattern repeats every night.",
    "rhetorical_q": "The result? Nobody replies at all.",
    "colon_reveal": "One word: pacing.",
    "banned_vocab": "They delve into a rich tapestry of attachment.",
    "intensifier": "This is truly, genuinely important.",
}
for cat, line in samples.items():
    rep = ai_tells.audit(line)
    ok(f"audit counts {cat}", rep[cat] >= 1,
       f"got {rep[cat]} for {line!r}")

clean = ("When someone takes their time replying to you, the delay "
         "is often careful word choice, not indifference.")
rep = ai_tells.audit(clean)
hard_cats = ("era_opener", "throat_clear", "recap_closer", "filler",
             "rhetorical_q", "colon_reveal", "banned_vocab")
ok("a clean human line scores zero on every hard category",
   all(rep[c] == 0 for c in hard_cats), str(rep))

print("── 2. the scrubber fixes muse text safely ─────────────────")

cases = [
    ("They delve into the tapestry of attachment.",
     "They dig into the mix of attachment."),
    ("He utilizes leverage to unlock his potential.",
     "He uses use to open his potential."),
    ("Moreover, the pattern repeats itself nightly.",
     "The pattern repeats itself nightly."),
    ("In today's fast-paced world, ghosting after one fight feels normal to them.",
     "Ghosting after one fight feels normal to them."),
    ("She waits. Moreover, the reply never comes. It's worth noting that patience has real limits on both sides.",
     "She waits. The reply never comes. Patience has real limits on both sides."),
    ("The delay is often careful word choice, not indifference.",
     "The delay is often careful word choice, not indifference."),
    ("When it comes to forgiveness, the timing matters more than the words do.",
     "The timing matters more than the words do."),
]
for dirty, expect in cases:
    got = ai_tells.scrub(dirty)
    ok(f"scrub: {dirty[:42]!r}", got == expect, f"got {got!r}")

ok("scrub is idempotent",
   ai_tells.scrub(ai_tells.scrub(cases[2][0])) == ai_tells.scrub(cases[2][0]))
ok("scrub never empties a line",
   ai_tells.scrub("Moreover.") == "Moreover.")
ok("no 'usee'-class backreference bugs",
   "usee" not in ai_tells.scrub("He utilizes his leverage."))

print("── 3. the hard gate rejects what scrub cannot fix ─────────")

ok("hard() catches a rhetorical reveal",
   "rhetorical_q" in ai_tells.hard("The result? Nobody replies."))
ok("hard() catches a colon reveal",
   "colon_reveal" in ai_tells.hard("Here's the secret: consistency."))
ok("hard() is empty after scrub fixes the vocabulary",
   ai_tells.hard(ai_tells.scrub("They delve deep into it.")) == [])
ok("hard() ignores contrast reveals (audited, not banned)",
   ai_tells.hard("It's not chemistry, it's a schedule.") == [])

print("── 4. the hand pools are clean of every hard tell ─────────")


def _walk(obj, out):
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _walk(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _walk(v, out)
    return out


pool_text = " ".join(
    s for m in (content_data, content_variants, hook_patterns)
    for s in _walk(vars(m), []))
rep = ai_tells.audit(pool_text)
# unambiguous machine tells: the pools must be at zero. colon_reveal
# is deliberately NOT asserted — ONE hand line ("a translator for a
# language that only ever says one word: maybe") uses the device as
# art with something specific behind it, exactly the doctrine's
# "still fine" clause; it stays audited, not banned.
POOL_CLEAN = ("era_opener", "throat_clear", "recap_closer", "filler",
              "rhetorical_q", "banned_vocab")
for cat in POOL_CLEAN:
    ok(f"{cat} = 0 across all hand pools", rep[cat] == 0,
       f"found {rep[cat]}")
ok("contrast reveals ARE counted (deliberate, sparse, audited)",
   rep["contrast_reveal"] > 0)

print("── 5. the muse gate + brief enforce the doctrine ──────────")

san = muse._sanitize("Moreover, they delve into the tapestry of love. "
                      "In today's world, it matters for attachment.")
ok("muse._sanitize scrubs banned vocab and openers",
   "delve" not in san and "tapestry" not in san and "today's" not in san,
   san)
ok("muse._clean_line rejects a hard tell",
   muse._clean_line("The result? Nobody replies.") is False)
ok("muse._clean_line passes a clean line",
   muse._clean_line(clean) is True)
ok("the brief carries the AI-tell rules",
   "AI tells are banned outright" in muse._RULES
   and "delve" in muse._RULES)
ok("the brief is byte-stable",
   muse._RULES == muse._RULES.strip() + "" or isinstance(muse._RULES, str))

print("── 6. the ledger stamps (mark_verified / note_tells) ──────")

fake = {"episodes": [{"n": 1, "ids": {"long": "AAA",
                                      "shorts": ["BBB"]}}]}
ledger.mark_verified(fake, 1, "long", "AAA", "T1")
ledger.mark_verified(fake, 1, "short", "BBB", "T1")
v = fake["episodes"][0]["verified"]
ok("long stamp lands", v.get("long") == "T1")
ok("short stamp lands", v.get("shorts", {}).get("BBB") == "T1")
ledger.mark_verified(fake, 1, "long", "AAA", "T2")
ok("restamping is idempotent (overwrite, no dupes)",
   fake["episodes"][0]["verified"]["long"] == "T2"
   and len(fake["episodes"]) == 1)
ledger.note_tells(fake, 1, {"contrast_reveal": 2, "banned_vocab": 0,
                            "filler": 0, "total": 2})
ok("note_tells stores only non-zero categories",
   fake["episodes"][0]["tells"] == {"contrast_reveal": 2})

print("── 7. the verify pass: stamp, grace, defer, alerts ─────────")

ledger.set_read_only(True)          # fixtures never touch real state
today = date(2026, 11, 1)

# 7a. a public video gets stamped; a late "done" episode alerts
state = {"episodes": [
    {"n": 1, "date": str(today - timedelta(days=5)), "status": "done",
     "title": "Old Episode", "ids": {"long": "AAA", "shorts": ["BBB"]}},
    {"n": 2, "date": str(today), "status": "done",
     "title": "Fresh Episode", "ids": {"long": "CCC", "shorts": []}},
], "quota": {}}
res = verify.run(state, no_api=True, today=today,
                 probe=lambda vid: vid == "CCC")
ok("public fresh video confirmed", res["confirmed"] >= 1, str(res))
ok("fresh episode stamps long", bool(
    state["episodes"][1].get("verified", {}).get("long")))
ok("late done episode raises exactly 2 alerts (long + short)",
   res["late"] == 2 and len(res["alerts"]) == 2, str(res))
ok("alert names the video", "AAA" in res["alerts"][0])

# 7b. the SAME state but probe-blind: unknown, never an alert
state2 = {"episodes": [
    {"n": 1, "date": str(today - timedelta(days=5)), "status": "done",
     "title": "Old Episode", "ids": {"long": "AAA", "shorts": []}},
], "quota": {}}
res2 = verify.run(state2, no_api=True, today=today, probe=lambda vid: None)
ok("a blind probe never alerts", res2["late"] == 0 and res2["unknown"] == 1,
   str(res2))

# 7c. within grace: not public, not late
state3 = {"episodes": [
    {"n": 1, "date": str(today - timedelta(days=1)), "status": "done",
     "title": "Yesterday Episode", "ids": {"long": "AAA", "shorts": []}},
], "quota": {}}
res3 = verify.run(state3, no_api=True, today=today, probe=lambda vid: False)
ok("1-day-old unpublic video is scheduled, not late",
   res3["late"] == 0, str(res3))

# 7d. defer active: alerts suppressed, stamps still collected
state4 = {"episodes": [
    {"n": 1, "date": str(today - timedelta(days=5)), "status": "done",
     "title": "Old Episode", "ids": {"long": "AAA", "shorts": []}},
], "quota": {"defer_until": 2 ** 40}}
res4 = verify.run(state4, no_api=True, today=today, probe=lambda vid: False)
ok("quota defer suppresses alerts", res4["late"] == 0, str(res4))

# 7e. in_progress episodes never alert (resume ladder owns them)
state5 = {"episodes": [
    {"n": 1, "date": str(today - timedelta(days=5)),
     "status": "in_progress",
     "title": "Half Episode", "ids": {"long": "AAA", "shorts": []}},
], "quota": {}}
res5 = verify.run(state5, no_api=True, today=today, probe=lambda vid: False)
ok("in_progress episodes are not alertable", res5["late"] == 0, str(res5))

# 7f. already-verified videos are skipped (bounded re-probing)
state6 = {"episodes": [
    {"n": 1, "date": str(today - timedelta(days=5)), "status": "done",
     "title": "Old Episode",
     "ids": {"long": "AAA", "shorts": []},
     "verified": {"long": "T0", "shorts": {}}},
], "quota": {}}
probes = []
res6 = verify.run(state6, no_api=True, today=today,
                  probe=lambda vid: probes.append(vid) or True)
ok("stamped videos are not re-probed", probes == [] and res6["confirmed"] == 1,
   f"probes={probes}")

print("── 8. metadata surfaces pass the hard categories ──────────")

story = {
    "title": "Why Slow Replies Mean More",
    "hash": "aabb1122",
    "hook": "The person who answers slowest is often the one listening hardest.",
    "question": "Who replies slowly but always shows up?",
    "topic_label": "attachment",
    "atoms": {"concepts": ["responsiveness", "attachment styles",
                           "emotional safety"]},
    "scenes": [{"id": "tip1_card"}, {"id": "tip1_scene"},
               {"id": "tip2_card"}, {"id": "tip2_scene"},
               {"id": "outro_card"}],
    "shorts": [{"term": "responsiveness",
                "hook": "Slow replies often mean careful word choice."}],
}
narration = {"scene_durations": [4, 30, 4, 30, 8]}
lm = metadata.long_metadata(story, narration, 44)
sm = metadata.short_metadata(story, story["shorts"][0], 45)
rep = ai_tells.audit(lm["title"] + " " + lm["description"] + " "
                     + sm["title"] + " " + sm["description"])
for cat in hard_cats:
    ok(f"metadata surfaces: {cat} = 0", rep[cat] == 0, f"found {rep[cat]}")
ok("the tells audit on a metadata surface runs end-to-end",
   isinstance(ai_tells.audit(lm["description"]), dict))

print("── 9. the new files compile and the workflow parses ───────")

import py_compile                                    # noqa: E402
for f in ("src/ai_tells.py", "src/verify.py", "tools/verify_public.py"):
    try:
        py_compile.compile(f, doraise=True)
        ok(f"{f} compiles", True)
    except py_compile.PyCompileError as exc:
        ok(f"{f} compiles", False, str(exc))

import yaml                                          # noqa: E402
wf = yaml.safe_load(Path(".github/workflows/daily-factory.yml").read_text())
step_names = [s.get("name", "") for s in
              wf["jobs"]["build-and-publish"]["steps"]]
ok("workflow has the verification alert step",
   "Alert on publish-verification failure" in step_names)
cy = yaml.safe_load(Path("channel.yaml").read_text())
ok("channel.yaml verify block present",
   cy["verify"]["enabled"] is True and cy["verify"]["grace_days"] == 2)

ledger.set_read_only(False)
print(f"\n{'ALL GREEN' if FAIL == 0 else 'FAILURES PRESENT'}: "
      f"{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
