#!/usr/bin/env python3
"""Five-year durability audit tests (2026-10-08).

Every fix from the audit gets a regression check:

  1. ledger .bak lifecycle   — save keeps a last-known-good copy;
                               a corrupted state.json is recovered
                               from .bak; both corrupt -> safe default
  2. gate bulletproofing     — poisoned state content never crashes
                               gate.py; it always exits 0 with a
                               RUN/SKIP verdict; corrupt state falls
                               back to the .bak stamp
  3. analytics bounding      — _cap_videos bounds the persisted
                               per-video detail (recent + top), the
                               total is computed from everything
  4. auth visibility         — a dead refresh token prints the LOUD
                               [auth] banner from morning_report and
                               never blocks the run
  5. issue lifecycle         — close_resolved_issues closes only
                               PAST-day failure issues; gh failures
                               are swallowed
  6. pinning                 — requirements.txt pins exact versions
  7. workflow hardening     — gate alert exists, .bak is committed,
                               watchdog can write issues, python3 used

Run: python3 scripts/test_durability.py   (from the repo root)
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FAILURES: list[str] = []


def check(name: str, got, want=True):
    ok = got == want
    if isinstance(want, bool) or isinstance(got, bool):
        # avoid 1 == True masking a type error
        ok = isinstance(got, bool) == isinstance(want, bool) and got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {name}" + ("" if ok else f"  (got {got!r}, want {want!r})"))
    if not ok:
        FAILURES.append(name)


def section(title: str):
    print(f"\n[{title}]")


# ── helpers ──────────────────────────────────────────────────────────

def fresh_state() -> dict:
    return {
        "version": 1,
        "episodes": [{"n": 1, "title": "t", "hash": "h1", "seed": 1,
                      "date": "2026-10-08", "status": "done",
                      "ids": {"long": "aaa", "shorts": ["bbb", "ccc"]},
                      "shashes": []}],
        "story_hashes": ["h1"],
        "short_hashes": [],
        "quota": {"date": "2026-10-08", "units_used": 100},
        "last_run": "2026-10-08",
        "last_run_ts": 1791000000,
        "stats": {"videos_published": 3, "days_active": 1},
        "slots": {"short": [], "long": []},
    }


# ── 1. ledger .bak lifecycle ────────────────────────────────────────

section("1. ledger last-known-good (.bak) lifecycle")

import src.ledger as ledger  # noqa: E402

tmp = Path(tempfile.mkdtemp())
orig_state, orig_bak = ledger.STATE_PATH, ledger.BAK_PATH
ledger.STATE_PATH = tmp / "state.json"
ledger.BAK_PATH = tmp / "state.json.bak"
try:
    st = fresh_state()
    ledger.save(st)                      # first save: no .bak yet
    check("first save writes state.json", ledger.STATE_PATH.exists(), True)

    st["stats"]["videos_published"] = 4
    ledger.save(st)                      # second save: .bak = version 1
    check("save keeps a .bak copy", ledger.BAK_PATH.exists(), True)
    bak = json.loads(ledger.BAK_PATH.read_text())
    check(".bak holds the PREVIOUS good version",
          bak["stats"]["videos_published"], 3)

    # corrupt the live file -> load recovers from .bak
    ledger.STATE_PATH.write_text('{"version": 1, "epis')
    recovered = ledger.load()
    check("corrupt state.json recovers from .bak",
          recovered["stats"]["videos_published"], 3)

    # both corrupt -> safe empty default, no exception
    ledger.BAK_PATH.write_text("][ not json at all")
    emptied = ledger.load()
    check("both corrupt -> safe default",
          emptied["episodes"], [])

    # save after corruption: the good .bak is preserved (not
    # overwritten by the corrupt live file)
    ledger.STATE_PATH.write_text('{"version": 1, "epis')
    st2 = fresh_state()
    ledger.save(st2)
    check("save does not clobber .bak with corrupt bytes",
          json.loads(ledger.BAK_PATH.read_text())["stats"]["videos_published"], 3)
    check("live state rewritten cleanly",
          json.loads(ledger.STATE_PATH.read_text())["stats"]["videos_published"], 3)

    # double corruption + one save -> the whole ladder self-repairs
    ledger.STATE_PATH.write_text("{corrupt")
    ledger.BAK_PATH.write_text("also corrupt")
    ledger.save(fresh_state())
    check("one save fully repairs a double corruption",
          (json.loads(ledger.STATE_PATH.read_text())["version"],
           json.loads(ledger.BAK_PATH.read_text())["version"]), (1, 1))
finally:
    ledger.STATE_PATH, ledger.BAK_PATH = orig_state, orig_bak
    shutil.rmtree(tmp, ignore_errors=True)

# the real repo state still loads and is intact (not the synthetic)
real = ledger.load()
check("real state.json loads with episodes",
      len(real.get("episodes", [])) >= 17, True)

# ── 2. gate bulletproofing ───────────────────────────────────────────

section("2. gate.py never crashes, never silently skips")


def gate_with_state(state_obj, event="schedule", actor="watchdog"):
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / "data").mkdir()
        if state_obj is not None:
            (tdp / "data" / "state.json").write_text(
                state_obj if isinstance(state_obj, str) else json.dumps(state_obj))
        # run gate.py from a copy so its ROOT-relative STATE path
        # resolves inside the sandbox
        gate_src = ROOT / "tools" / "gate.py"
        r = subprocess.run(
            [sys.executable, str(gate_src), "--event", event, "--actor", actor],
            capture_output=True, text=True, cwd=tdp,
            env={**os.environ, "PYTHONPATH": str(ROOT)})
        # gate.py resolves STATE relative to ITS OWN file, so a cwd
        # trick alone does not redirect it — instead verify against
        # the repo copy for crash-freedom and use in-proc for state.
        return r


# in-process: poison the loader by monkeypatching gate's STATE paths
gate_mod = importlib.import_module  # noqa: F841
import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location("gate_under_test", ROOT / "tools" / "gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

poisons = [
    ("slots is a string", {"slots": "garbage", "last_run_ts": 1}),
    ("slots values are ints", {"slots": {"short": [17, 42], "long": None}}),
    ("episodes is a dict", {"episodes": {"a": 1}, "last_run_ts": 1}),
    ("quota is a list", {"quota": [1, 2, 3]}),
    ("last_run_ts is a string", {"last_run_ts": "yesterday"}),
    ("state is a bare string", "<<<not json>>>"),
    ("state is empty file", ""),
]
for label, payload in poisons:
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / "data").mkdir()
        if isinstance(payload, str):
            (tdp / "data" / "state.json").write_text(payload)
        else:
            (tdp / "data" / "state.json").write_text(json.dumps(payload))
        gate.STATE = tdp / "data" / "state.json"
        gate.STATE_BAK = tdp / "data" / "state.json.bak"
        try:
            import io, contextlib  # noqa: E402
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = gate.main()  # argv has no --event: defaults schedule
            out = buf.getvalue().strip()
            check(f"poisoned state ({label}) -> verdict, exit 0",
                  (out.startswith(("RUN", "SKIP")), rc), (True, 0))
        except SystemExit as e:
            check(f"poisoned state ({label}) -> verdict, exit 0",
                  False, True)

# corrupt state + good .bak -> the .bak stamp governs (no double RUN)
with tempfile.TemporaryDirectory() as td:
    tdp = Path(td)
    (tdp / "data").mkdir()
    (tdp / "data" / "state.json").write_text("{corrupt")
    (tdp / "data" / "state.json.bak").write_text(json.dumps(
        {"last_run_ts": __import__("time").time() - 60}))  # 1 min ago
    gate.STATE = tdp / "data" / "state.json"
    gate.STATE_BAK = tdp / "data" / "state.json.bak"
    # isolate the window branch (the grid-hole branch legitimately
    # overrides a fresh stamp on an unbooked grid): with no holes and
    # a fresh stamp, the .bak is what makes this SKIP — proving the
    # fallback is actually READ, not defaulted.
    gate._grid_holes = lambda state: []
    import io, contextlib  # noqa: E402
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = gate.main()
    check("corrupt state + fresh .bak -> SKIP (no double produce)",
          (buf.getvalue().strip().startswith("SKIP"), rc), (True, 0))

# subprocess: the REAL repo state never crashes the real gate.py
r = subprocess.run([sys.executable, str(ROOT / "tools" / "gate.py"),
                    "--event", "schedule", "--actor", "watchdog"],
                   capture_output=True, text=True, cwd=ROOT)
check("real gate.py on real state: exit 0, RUN/SKIP verdict",
      (r.returncode, r.stdout.strip().startswith(("RUN", "SKIP"))), (0, True))

# ── 3. analytics bounding ───────────────────────────────────────────

section("3. analytics: bounded memory, honest totals")

from src.discovery import _cap_videos, RECENT_TRACK, TOP_TRACK  # noqa: E402

N = 5000
vids = [(f"vid{i:05d}", "label") for i in range(N)]          # upload order
per_video = {f"vid{i:05d}": (i % 97) for i in range(N)}       # views
per_video["vid00001"] = 999_999                                # an old breakout

capped = _cap_videos(per_video, vids)
check(f"capped size <= recent+top ({RECENT_TRACK + TOP_TRACK})",
      len(capped) <= RECENT_TRACK + TOP_TRACK, True)
check("most recent videos are kept", "vid04999" in capped, True)
check("oldest non-breakout is dropped", "vid01000" in capped, False)
check("breakout old-timer is kept (top-N)", "vid00001" in capped, True)
small = {f"v{i}": i for i in range(10)}
small_vids = [(f"v{i}", "") for i in range(10)]
check("small channels are untouched by the cap",
      _cap_videos(small, small_vids), small)

# 5-year projection: 60 snapshots of the capped size stay < 1 MB
proj = 60 * (RECENT_TRACK + TOP_TRACK) * 26
check("60-snapshot projection under 1 MB", proj < 1_048_576, True)

# ── 4. auth visibility ──────────────────────────────────────────────

section("4. dead refresh token -> loud [auth] banner, no block")

from src import discovery, youtube  # noqa: E402
import io, contextlib  # noqa: E402


class _Boom(youtube.AuthError):
    pass


def _dead_token():
    raise _Boom("token refresh failed (400): invalid_grant")


orig_get = youtube.get_access_token
youtube.get_access_token = _dead_token
try:
    discovery.youtube.get_access_token = _dead_token
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        discovery.morning_report({"quota": {"date": "x", "units_used": 0}})
    out = buf.getvalue()
    check("morning_report does not raise on AuthError", True, True)
    check("[auth] banner printed", "[auth] CREDENTIALS REJECTED" in out, True)
    check("recovery hint points at the RUNBOOK", "RUNBOOK" in out, True)
finally:
    youtube.get_access_token = orig_get
    discovery.youtube.get_access_token = orig_get

# ── 5. issue lifecycle ──────────────────────────────────────────────

section("5. failure issues close themselves once healed")

import tools.close_resolved_issues as cri  # noqa: E402

calls: list[str] = []
fake_gh = Path(tempfile.mkdtemp()) / "gh"


def _write_fake_gh(script_body: str):
    fake_gh.write_text(script_body)
    fake_gh.chmod(fake_gh.stat().st_mode | stat.S_IEXEC)


import os as _os  # noqa: E402
orig_path = _os.environ["PATH"]

# a fake gh that lists two stale issues + today's issue
_write_fake_gh(
    '#!/bin/sh\n'
    'if [ "$1" = "issue" ] && [ "$2" = "list" ]; then\n'
    '  echo \'[{"number": 11, "title": "Factory cycle failed — 2026-10-06"},'
    '{"number": 12, "title": "Factory cycle failed — 2026-10-08"},'
    '{"number": 13, "title": "Some other issue"}]\'\n'
    '  exit 0\n'
    'fi\n'
    'echo "closed: $*" >> "' + str(fake_gh.parent / 'gh.log') + '"\n'
    'exit 0\n')
_os.environ["PATH"] = f"{fake_gh.parent}:{orig_path}"
try:
    log = fake_gh.parent / "gh.log"
    closed = cri.close_resolved("2026-10-08", dry_run=False)
    check("closes only the PAST-day issue", closed, [11])
    check("today's issue stays open", 12 not in closed, True)
    check("non-failure issues untouched", 13 not in closed, True)
    # gh itself broken -> swallowed, returns []
    _write_fake_gh('#!/bin/sh\nexit 2\n')
    check("gh failure swallowed",
          cri.close_resolved("2026-10-08"), [])
finally:
    _os.environ["PATH"] = orig_path
    shutil.rmtree(fake_gh.parent, ignore_errors=True)

# ── 6. pinning ──────────────────────────────────────────────────────

section("6. requirements.txt is exactly pinned")

lines = [ln.strip() for ln in (ROOT / "requirements.txt").read_text().splitlines()
         if ln.strip() and not ln.strip().startswith("#")]
check("every requirement pinned with ==", all("==" in ln for ln in lines), True)
check("the five core deps present",
      all(any(dep in ln for ln in lines)
          for dep in ("numpy", "Pillow", "PyYAML", "piper-tts", "edge-tts")), True)

# ── 7. workflow hardening ───────────────────────────────────────────

section("7. workflows: gate alerts, .bak commit, python3, issues:write")

import yaml  # noqa: E402

wf = yaml.safe_load((ROOT / ".github/workflows/daily-factory.yml").read_text())
gate_job = wf["jobs"]["gate"]
gate_steps = [s.get("name", "") for s in gate_job["steps"]]
build_job = wf["jobs"]["build-and-publish"]
build_steps = {s.get("name", ""): s for s in build_job["steps"]}
check("gate job has an Alert on gate failure step",
      "Alert on gate failure" in gate_steps, True)
gate_alert = next(s for s in gate_job["steps"] if s.get("name") == "Alert on gate failure")
check("gate alert covers timeouts too",
      "cancelled()" in gate_alert.get("if", ""), True)
commit_step = build_steps.get("Commit the factory memory", {})
check("memory commit includes state.json.bak",
      "data/state.json.bak" in commit_step.get("run", ""), True)
close_step = build_steps.get("Close resolved failure issues", {})
check("issue cleanup step exists on success",
      "success()" in close_step.get("if", "") and
      "close_resolved_issues.py" in close_step.get("run", ""), True)
verdict_cmd = next(s for s in gate_job["steps"]
                   if s.get("name") == "Has today's cycle already run?")["run"]
check("gate verdict uses python3", "python3 tools/gate.py" in verdict_cmd, True)
check("gate verdict has a crash fallback",
      "gate.py did not even run" in verdict_cmd, True)
inst = " ".join(build_steps.get("Install dependencies", {}).get("run", "").split())
check("install step mentions the exact pins", "EXACTLY pinned" in inst, True)

wd = yaml.safe_load((ROOT / ".github/workflows/watchdog.yml").read_text())
hb = wd["jobs"]["heartbeat"]
check("watchdog can write issues", wd["permissions"].get("issues"), "write")
check("watchdog has its own failure alert",
      any("Alert on watchdog failure" in s.get("name", "") for s in hb["steps"]), True)
wd_gate = next(s for s in hb["steps"] if s.get("name") == "Does today still need a cycle?")["run"]
check("watchdog gate uses python3 + crash fallback",
      "python3 tools/gate.py" in wd_gate and "did not even run" in wd_gate, True)
check("watchdog timeout raised to 10", wd["jobs"]["heartbeat"]["timeout-minutes"], 10)
check("gate timeout raised to 10", gate_job["timeout-minutes"], 10)

# ── summary ─────────────────────────────────────────────────────────

print()
if FAILURES:
    print(f"✗ {len(FAILURES)} test(s) failed: {', '.join(FAILURES)}")
    sys.exit(1)
print(f"ALL PASS: durability audit regression suite — "
      f"{'5'}-year contract enforced")
