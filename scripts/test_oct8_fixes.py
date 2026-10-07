#!/usr/bin/env python3
"""Regression tests for the Oct 8 fixes (quota classification, defer
back-off, honest reporting). Runs entirely offline: every network /
disk-touching seam is monkeypatched. Usage:
    python3 scripts/test_oct8_fixes.py
Exit code 0 = all checks pass.
"""
from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import discovery, ledger, orchestrator, youtube  # noqa: E402

PASS = 0
FAIL = 0

# SAFETY: this test must never write the real factory memory — patch
# ledger.save globally for the whole run (individual cases re-patch it
# anyway; this is the belt under the braces).
_REAL_SAVE = ledger.save
ledger.save = lambda state: None


def check(name: str, cond: bool, extra: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok  {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {extra}")


# ── 1. reason parsing ──────────────────────────────────────────────
print("[1] _error_reason parses YouTube bodies")
body403 = ('upload init failed (403): {"error": {"errors": ['
           '{"domain": "youtube.quota", "reason": "quotaExceeded", '
           '"message": "The request cannot be completed because you '
           'have exceeded your quota."}]}')
check("quotaExceeded parsed", youtube._error_reason(body403) == "quotaExceeded")
check("empty on garbage", youtube._error_reason("nope") == "")
check("invalidTags parsed",
      youtube._error_reason('x {"reason": "invalidTags"}') == "invalidTags")

# ── 2. Pacific midnight math ────────────────────────────────────────
print("[2] _hours_to_pacific_midnight sanity")
h = youtube._hours_to_pacific_midnight()
check("0 < h <= 24.1", 0 < h <= 24.1, f"h={h}")

# ── 3. upload_video classification (mocked seams) ──────────────────
print("[3] upload_video classification")


def fake_state() -> dict:
    return {
        "version": 1,
        "episodes": [{"n": 1, "title": "T", "hash": "h", "seed": 1,
                      "date": "2026-10-08", "status": "in_progress",
                      "ids": {"long": None, "shorts": [],
                              "thumbnail": None}}],
        "story_hashes": [], "short_hashes": [],
        "quota": {"date": ledger._quota_today(), "units_used": 0},
        "last_run": None, "stats": {"videos_published": 0,
                                    "days_active": 0},
    }


def run_upload_case(err_body: str, calls: list):
    """Drive upload_video with fully mocked IO.
    Returns (return_value, raised, stdout, state)."""
    st = fake_state()
    stdout = io.StringIO()
    orig = {
        "qr": ledger.quota_remaining, "save": ledger.save,
        "tok": youtube.get_access_token,
        "find": youtube._find_video_by_title,
        "up": youtube._upload_video, "thumb": youtube.set_thumbnail,
    }
    ledger.quota_remaining = lambda state: 10_000
    ledger.save = lambda state: None
    youtube.get_access_token = lambda: "tok"
    youtube._find_video_by_title = lambda *a, **k: None

    def _up(*a, **k):
        calls.append(1)
        raise RuntimeError(err_body)

    youtube._upload_video = _up
    youtube.set_thumbnail = lambda *a, **k: True
    try:
        with contextlib.redirect_stdout(stdout):
            rv, raised = None, None
            try:
                rv = youtube.upload_video(
                    Path("/nonexistent.mp4"), {"title": "X"}, None, 1,
                    "long", state=st)
            except Exception as e:
                raised = e
        return rv, raised, stdout.getvalue(), st
    finally:
        ledger.quota_remaining = orig["qr"]
        ledger.save = orig["save"]
        youtube.get_access_token = orig["tok"]
        youtube._find_video_by_title = orig["find"]
        youtube._upload_video = orig["up"]
        youtube.set_thumbnail = orig["thumb"]


# 3a. daily quota family → defer + stamp + real reason logged
rv, raised, out, st = run_upload_case(
    'upload init failed (403): {"error": {"errors": [{"reason": '
    '"quotaExceeded", "message": "exceeded your quota."}]}}', [])
check("quotaExceeded defers (None)", rv is None and raised is None)
check("reason logged", "quotaExceeded" in out)
check("raw body logged", "raw body" in out)
q = st["quota"]
check("defer stamp present",
      q.get("defer_reason") == "quotaExceeded"
      and q.get("defer_until", 0) > time.time())
check("defer spans to Pacific midnight",
      q.get("defer_until", 0) >= time.time() + (h - 0.2) * 3600,
      f"until={q.get('defer_until')}")

# 3b. rolling upload limit → defer ~2h
rv, raised, out, st = run_upload_case(
    'upload init failed (400): {"error": {"errors": [{"reason": '
    '"uploadLimitExceeded", "message": "The user has exceeded the '
    'number of videos they can upload."}]}}', [])
check("uploadLimitExceeded defers", rv is None and raised is None)
check("rolling reason logged", "uploadLimitExceeded" in out)
q = st["quota"]
check("2h defer stamp",
      abs(q.get("defer_until", 0) - (time.time() + 7200)) < 300)

# 3c. UNKNOWN exceeded-family → must RAISE, never silently defer
rv, raised, out, st = run_upload_case(
    'upload init failed (400): {"error": {"errors": [{"reason": '
    '"fileSizeLimitExceeded", "message": "The document is too large."'
    '}]}}', [])
check("fileSizeLimitExceeded RAISES", raised is not None, f"got {raised}")
check("raise says NOT deferring",
      raised is not None and "NOT" in str(raised))
check("no defer stamp on raise", not st["quota"].get("defer_until"))

# 3d. quota-flavored mystery without a parsable reason → RAISE (loud)
rv, raised, out, st = run_upload_case(
    'upload init failed (403): some quota-flavored mystery', [])
check("mystery quota error RAISES", raised is not None)

# 3e. non-quota error (plain 500 text) → propagates as-is
rv, raised, out, st = run_upload_case(
    'upload failed (500): backend hiccup', [])
check("non-quota error propagates",
      raised is not None and "unrecognized" not in str(raised))

# 3f. rateLimitExceeded → waits 90s + retries once (sleep patched)
slept = []
orig_sleep = youtube.time.sleep
youtube.time.sleep = lambda s: slept.append(s)
try:
    seq = [RuntimeError('upload init failed (403): {"error": {"errors": '
                        '[{"reason": "rateLimitExceeded"}]}}'), "vid123"]

    def _seq_up(*a, **k):
        v = seq.pop(0)
        if isinstance(v, Exception):
            raise v
        return v

    st = fake_state()
    ledger.quota_remaining = lambda state: 10_000
    ledger.save = lambda state: None
    youtube.get_access_token = lambda: "tok"
    youtube._find_video_by_title = lambda *a, **k: None
    youtube._upload_video = _seq_up
    youtube.set_thumbnail = lambda *a, **k: True
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rv = youtube.upload_video(Path("/x.mp4"), {"title": "X"}, None, 1,
                                  "long", state=st)
    check("rateLimit recovers after one wait", rv == "vid123")
    check("waited ~90s once", slept == [90])
    check("no defer stamp after recovery",
          not st["quota"].get("defer_until"))
finally:
    youtube.time.sleep = orig_sleep

# 3g. search costs ledgered (2 units per attempt)
st = fake_state()
ledger.quota_remaining = lambda state: 10_000
ledger.save = lambda state: None
youtube.get_access_token = lambda: "tok"
youtube._find_video_by_title = lambda *a, **k: None
youtube._upload_video = lambda *a, **k: "vid999"
youtube.set_thumbnail = lambda *a, **k: True
with contextlib.redirect_stdout(io.StringIO()):
    youtube.upload_video(Path("/x.mp4"), {"title": "X"}, None, 1, "long",
                         state=st)
check("title search ledgered (2 units)",
      st["quota"]["units_used"] == 2 + 1600 + 50,
      f"used={st['quota']['units_used']}")

# ── 4. defer marker clear on success ───────────────────────────────
print("[4] defer marker lifecycle")
st = fake_state()
st["quota"]["defer_until"] = int(time.time() + 3600)
st["quota"]["defer_reason"] = "quotaExceeded"
youtube._clear_server_defer(st)
check("marker cleared", "defer_until" not in st["quota"]
      and "defer_reason" not in st["quota"])

# ── 5. gate honors the defer stamp ─────────────────────────────────
print("[5] tools/gate.py skips while deferred")
with tempfile.TemporaryDirectory() as td:
    tdp = Path(td)
    (tdp / "tools").mkdir()
    (tdp / "data").mkdir()
    (tdp / "tools" / "gate.py").write_text(
        (ROOT / "tools" / "gate.py").read_text())
    (tdp / "data" / "state.json").write_text(json.dumps({
        "last_run_ts": int(time.time()) - 999999,  # very stale → would RUN
        "episodes": [{"status": "in_progress", "date": "2026-10-08",
                      "n": 16, "title": "x", "hash": "y", "seed": 1,
                      "ids": {"long": None, "shorts": []}}],
        "quota": {"date": "2026-10-08", "units_used": 0,
                  "defer_reason": "uploadLimitExceeded",
                  "defer_until": int(time.time() + 7200)},
    }))
    r = subprocess.run([sys.executable, str(tdp / "tools" / "gate.py"),
                        "--event", "schedule", "--actor", "x"],
                       capture_output=True, text=True, timeout=30)
    first = r.stdout.strip().splitlines()[0] if r.stdout.strip() else ""
    check("gate SKIPs on active defer", first.startswith("SKIP"), first)
    check("gate names the reason", "uploadLimitExceeded" in r.stdout)

    r2 = subprocess.run([sys.executable, str(tdp / "tools" / "gate.py"),
                         "--event", "workflow_dispatch", "--actor", "habl"],
                        capture_output=True, text=True, timeout=30)
    check("human dispatch still RUNs",
          r2.stdout.strip().startswith("RUN"))

    st2 = json.loads((tdp / "data" / "state.json").read_text())
    st2["quota"]["defer_until"] = int(time.time() - 60)
    (tdp / "data" / "state.json").write_text(json.dumps(st2))
    r3 = subprocess.run([sys.executable, str(tdp / "tools" / "gate.py"),
                         "--event", "schedule", "--actor", "x"],
                        capture_output=True, text=True, timeout=30)
    check("expired defer → normal gate logic",
          r3.stdout.strip().startswith("RUN"), r3.stdout.strip())

# ── 6. defer_note.py ───────────────────────────────────────────────
print("[6] tools/defer_note.py commit suffix")
with tempfile.TemporaryDirectory() as td:
    tdp = Path(td)
    (tdp / "tools").mkdir()
    (tdp / "data").mkdir()
    (tdp / "tools" / "defer_note.py").write_text(
        (ROOT / "tools" / "defer_note.py").read_text())
    (tdp / "data" / "state.json").write_text(json.dumps(
        {"quota": {"defer_reason": "quotaExceeded",
                   "defer_until": int(time.time() + 3600)}}))
    out = subprocess.run(
        [sys.executable, str(tdp / "tools" / "defer_note.py")],
        capture_output=True, text=True, timeout=30).stdout.strip()
    check("active defer → suffix",
          out == "(uploads deferred: quotaExceeded)", out)
    (tdp / "data" / "state.json").write_text(json.dumps(
        {"quota": {"defer_reason": "quotaExceeded",
                   "defer_until": int(time.time() - 3600)}}))
    out = subprocess.run(
        [sys.executable, str(tdp / "tools" / "defer_note.py")],
        capture_output=True, text=True, timeout=30).stdout.strip()
    check("expired defer → empty", out == "", out)
    (tdp / "data" / "state.json").write_text("{}")
    out = subprocess.run(
        [sys.executable, str(tdp / "tools" / "defer_note.py")],
        capture_output=True, text=True, timeout=30).stdout.strip()
    check("no state → empty", out == "", out)

# ── 7. honest orchestrator status lines ────────────────────────────
print("[7] orchestrator honest reporting")
orig_run = orchestrator.run_daily
try:
    cases = [
        ({"episode": 16, "title": "Green Flags", "long_id": None,
          "long_seconds": 609, "shorts": 4, "deferred": True},
         "! episode 16: Green Flags — uploads deferred"),
        ({"episode": 17, "title": "Done Day", "long_id": "abc",
          "long_seconds": 500, "shorts": 4, "deferred": False},
         "✓ episode 17: Done Day"),
        ({"episode": 18, "title": "Rehearsal", "dry_run": True,
          "long_seconds": 500, "shorts": 4},
         "- episode 18: Rehearsal (dry-run)"),
    ]
    for fake, expect in cases:
        orchestrator.run_daily = lambda *a, **k: [dict(fake)]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = orchestrator.main()
        check(f"line: {expect[:40]}", expect in buf.getvalue(),
              buf.getvalue()[-120:])
        check("exit 0 on deferred day", code == 0)
    orchestrator.run_daily = lambda *a, **k: [
        {"episode": 19, "title": "OldShape", "long_id": "z",
         "long_seconds": 1, "shorts": 2}]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = orchestrator.main()
    check("legacy result shape OK", "✓ episode 19" in buf.getvalue())
finally:
    orchestrator.run_daily = orig_run

# ── 8. orchestrator defer early-out ────────────────────────────────
print("[8] orchestrator holds production while deferred")
st = fake_state()
st["quota"]["defer_reason"] = "quotaExceeded"
st["quota"]["defer_until"] = int(time.time() + 7200)
touched = {"backfill": 0, "report": 0}
orig = {
    "load": ledger.load,
    "sweep": orchestrator._abandon_stale_episodes,
    "back": orchestrator.backfill_thumbnails,
    "report": discovery.morning_report,
}
try:
    ledger.load = lambda: st
    orchestrator._abandon_stale_episodes = lambda state: 0
    orchestrator.backfill_thumbnails = lambda state: (
        touched.__setitem__("backfill", touched["backfill"] + 1), [])[1]
    discovery.morning_report = lambda state: touched.__setitem__(
        "report", touched["report"] + 1)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        res = orchestrator.run_daily()
    check("returns empty results", res == [])
    check("message logged", "defer active until" in buf.getvalue())
    check("no backfill churn", touched["backfill"] == 0)
    check("no stats churn", touched["report"] == 0)
    check("last_run NOT stamped on hold", st.get("last_run") is None)
finally:
    ledger.load = orig["load"]
    orchestrator._abandon_stale_episodes = orig["sweep"]
    orchestrator.backfill_thumbnails = orig["back"]
    discovery.morning_report = orig["report"]

print()
print(f"{'ALL PASS' if FAIL == 0 else 'FAILURES'}: "
      f"{PASS} passed, {FAIL} failed")
ledger.save = _REAL_SAVE
sys.exit(0 if FAIL == 0 else 1)
