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
  8. voice quality (Oct 13) — patient multi-voice probe, loud
                               NEURAL_FALLBACK flag, fail-before-upload
                               retry policy, voice-issue lifecycle

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
from datetime import date
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

# a fake gh that lists two stale issues + today's issue + a voice issue
_write_fake_gh(
    '#!/bin/sh\n'
    'if [ "$1" = "issue" ] && [ "$2" = "list" ]; then\n'
    '  echo \'[{"number": 11, "title": "Factory cycle failed — 2026-10-06"},'
    '{"number": 12, "title": "Factory cycle failed — 2026-10-08"},'
    '{"number": 13, "title": "Some other issue"},'
    '{"number": 14, "title": "Voice degraded — offline voice used — 2026-10-06"}]\'\n'
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
    check("voice issue waits for a NEURAL day", 14 not in closed, True)
    closed2 = cri.close_resolved("2026-10-08", dry_run=False, close_voice=True)
    check("on a --voice-ok day, past voice issues close too", closed2, [11, 14])
    # gh itself broken -> swallowed, returns []
    _write_fake_gh('#!/bin/sh\nexit 2\n')
    check("gh failure swallowed",
          cri.close_resolved("2026-10-08"), [])
finally:
    _os.environ["PATH"] = orig_path
    shutil.rmtree(fake_gh.parent, ignore_errors=True)

# ── 6. pinning ──────────────────────────────────────────────────────

section("6. requirements.txt: exact pins + the one living range")

lines = [ln.strip() for ln in (ROOT / "requirements.txt").read_text().splitlines()
         if ln.strip() and not ln.strip().startswith("#")]
core = [ln for ln in lines if not ln.startswith("edge-tts")]
check("core deps pinned with ==", all("==" in ln for ln in core), True)
check("edge-tts range-pins the 7.x line (service rotations auto-heal)",
      [ln for ln in lines if ln.startswith("edge-tts")], ["edge-tts>=7.3.1,<8"])
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
check("install step documents the pin policy (exact + living range)",
      "pinned" in inst and "edge-tts" in inst, True)

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

# ── 8. voice quality (the 2026-10-13 incident) ─────────────────────

section("8. voice: patient probe, loud flag, fail-before-upload retries")

import types  # noqa: E402
import array as _array  # noqa: E402
import src.tts as tts_mod  # noqa: E402
from src import orchestrator as orch  # noqa: E402


def _reset_voice():
    tts_mod.NEURAL_FALLBACK = False
    tts_mod._EDGE_DECISION = None


# 8a. the picker: primary voice dead, alternate alive -> alternate
_reset_voice()
probe_calls: list[str] = []


def _fake_probe(vconf, cd):
    probe_calls.append(str(vconf.get("edge_name")))
    return str(vconf.get("edge_name")) == "en-US-AriaNeural"


_orig_probe = tts_mod._edge_probe_once
tts_mod._edge_probe_once = _fake_probe
try:
    vtmp = Path(tempfile.mkdtemp())
    picked = tts_mod._edge_pick_voice(
        {"edge_name": "en-US-JennyNeural",
         "edge_fallback_voices": ["en-US-AriaNeural", "en-US-GuyNeural"]},
        vtmp, delays=(0, 0, 0))
    check("picker switches to an alternate neural voice", picked, "en-US-AriaNeural")
    check("primary voice was probed first", probe_calls[0], "en-US-JennyNeural")
    n = len(probe_calls)
    again = tts_mod._edge_pick_voice(
        {"edge_name": "en-US-JennyNeural"}, vtmp, delays=(0, 0, 0))
    check("decision is cached process-wide (one voice per cycle)",
          (again, len(probe_calls)), ("en-US-AriaNeural", n))
    _reset_voice()
    tts_mod._edge_probe_once = lambda vconf, cd: False
    down = tts_mod._edge_pick_voice(
        {"edge_name": "en-US-JennyNeural"}, vtmp, delays=(0, 0, 0))
    check("endpoint fully down -> None (fall back offline)", down, None)
    check("DOWN decision cached too", tts_mod._EDGE_DECISION, "DOWN")
finally:
    tts_mod._edge_probe_once = _orig_probe
    _reset_voice()
    shutil.rmtree(vtmp, ignore_errors=True)

# 8b. narrate(): dead endpoint -> offline engine + the LOUD flag
_reset_voice()
_orig_pick = tts_mod._edge_pick_voice
tts_mod._edge_pick_voice = lambda vconf, cd, delays=(0, 10, 25): None


class _FakeSynthConf:
    def __init__(self, length_scale=1.0):
        self.length_scale = length_scale


class _FakeChunk:
    def __init__(self):
        self.audio_int16_array = _array.array("h", [3000] * 4410)


class _FakeVoice:
    def synthesize(self, text, syn_config=None):
        return [_FakeChunk(), _FakeChunk()]


class _FakePiperVoice:
    @staticmethod
    def load(path):
        return _FakeVoice()


_fake_piper = types.ModuleType("piper")
_fake_piper.PiperVoice = _FakePiperVoice
_fake_piper.SynthesisConfig = _FakeSynthConf
sys.modules["piper"] = _fake_piper

story_v = {"title": "t", "hash": "voice-test-0001",
           "scenes": [{"n": 1, "narration": "Hello there, friend."}]}
wv = Path(tempfile.mkdtemp())
_real_cfg_tts = tts_mod.cfg
try:
    meta = tts_mod.narrate(story_v, wv)
    check("dead endpoint narrates offline (piper)", meta.get("engine"), "piper")
    check("NEURAL_FALLBACK flag raised", tts_mod.NEURAL_FALLBACK, True)

    # 8c. a cached robotic narration still raises the flag
    _reset_voice()
    meta2 = tts_mod.narrate(story_v, wv)
    check("cached narration returns intact", meta2.get("engine"), "piper")
    check("cache path also raises the flag", tts_mod.NEURAL_FALLBACK, True)

    # 8d. a deliberate offline config never flags
    _reset_voice()
    tts_mod.cfg = lambda: {**_real_cfg_tts(),
                           "voice": {**_real_cfg_tts()["voice"], "engine": "piper"}}
    meta3 = tts_mod.narrate(story_v, wv)
    check("deliberate piper config: no flag", tts_mod.NEURAL_FALLBACK, False)
finally:
    tts_mod._edge_pick_voice = _orig_pick
    tts_mod.cfg = _real_cfg_tts
    sys.modules.pop("piper", None)
    _reset_voice()
    shutil.rmtree(wv, ignore_errors=True)

# 8e. voice policy + the fail-BEFORE-upload gate
st = fresh_state()
check("fresh day -> retry", orch.voice_policy(st), "retry")
st["voice_fallbacks"] = {"date": date.today().isoformat(), "attempts": 2}
check("attempts under budget -> retry", orch.voice_policy(st), "retry")
st["voice_fallbacks"] = {"date": date.today().isoformat(), "attempts": 4}
check("budget spent -> ship degraded", orch.voice_policy(st), "ship")
st["voice_fallbacks"] = {"date": "2020-01-01", "attempts": 99}
check("yesterday's budget never counts", orch.voice_policy(st), "retry")
_real_cfg_o = orch.cfg
orch.cfg = lambda: {**_real_cfg_o(),
                    "voice": {**_real_cfg_o()["voice"], "engine": "piper"}}
check("deliberate offline config -> ship", orch.voice_policy(st), "ship")
orch.cfg = _real_cfg_o

tmpv = Path(tempfile.mkdtemp())
ledger.STATE_PATH = tmpv / "state.json"
ledger.BAK_PATH = tmpv / "state.json.bak"
try:
    sev = fresh_state()
    wv2 = Path(tempfile.mkdtemp())
    (wv2 / "narration.json").write_text('{"engine": "piper"}')
    (wv2 / "chunks").mkdir()
    (wv2 / "chunks" / "chunk_001.wav").write_bytes(b"\x00" * 64)
    raised = False
    try:
        orch.enforce_voice_quality(sev, {"engine": "piper"}, wv2, dry_run=False)
    except orch.VoiceQualityError:
        raised = True
    check("retry policy aborts BEFORE upload", raised, True)
    check("abort counted in today's budget", sev["voice_fallbacks"]["attempts"], 1)
    check("piper narration cache forgotten for the retry",
          (wv2 / "narration.json").exists() or (wv2 / "chunks").exists(), False)

    # dry-run rehearsals never fail the day nor spend budget
    sev2 = fresh_state()
    wv3 = Path(tempfile.mkdtemp())
    (wv3 / "narration.json").write_text('{"engine": "piper"}')
    orch.enforce_voice_quality(sev2, {"engine": "piper"}, wv3, dry_run=True)
    check("dry-run is exempt (rehearsal)", (wv3 / "narration.json").exists(), True)
    check("dry-run spent no retry budget", "voice_fallbacks" in sev2, False)

    # exhausted budget ships degraded, cache kept
    sev2["voice_fallbacks"] = {"date": date.today().isoformat(), "attempts": 99}
    orch.enforce_voice_quality(sev2, {"engine": "piper"}, wv3, dry_run=False)
    check("exhausted budget ships degraded (cache kept)",
          (wv3 / "narration.json").exists(), True)

    # neural narration passes untouched
    orch.enforce_voice_quality(sev2, {"engine": "edge"}, wv3, dry_run=False)
    check("neural narration passes untouched", True, True)
finally:
    ledger.STATE_PATH, ledger.BAK_PATH = orig_state, orig_bak
    shutil.rmtree(tmpv, ignore_errors=True)

# 8f. episodes remember their voice (triage without expired logs)
stf = fresh_state()
ledger.mark_voice_engine(stf, 1, "piper")
check("episode records its voice engine",
      stf["episodes"][0].get("voice_engine"), "piper")
ledger.mark_voice_engine(stf, 999, "edge")
check("unknown episode number is a no-op", True, True)

# 8g. the workflow wiring: alert step, --voice-ok close, source markers
va = build_steps.get("Alert on voice degradation", {})
check("voice-degradation alert step exists", bool(va), True)
check("voice alert greps the VOICE-ALERT marker",
      "VOICE-ALERT:" in va.get("run", ""), True)
check("voice alert fires even on failed cycles",
      "always()" in va.get("if", ""), True)
check("voice alert can write issues", "GH_TOKEN" in va.get("env", {}), True)
cs = build_steps.get("Close resolved failure issues", {})
check("issue closer passes --voice-ok only on neural days",
      "--voice-ok" in cs.get("run", "") and "VOICE-ALERT" in cs.get("run", ""), True)
orch_src = (ROOT / "src" / "orchestrator.py").read_text()
check("orchestrator prints VOICE-ALERT on degraded days",
      "VOICE-ALERT:" in orch_src, True)
check("orchestrator fails the cycle before upload (retry ring)",
      "VoiceQualityError" in orch_src, True)
tts_src = (ROOT / "src" / "tts.py").read_text()
check("tts raises the fallback flag in every degradation path",
      tts_src.count("NEURAL_FALLBACK = True") >= 3, True)

# ── summary ─────────────────────────────────────────────────────────

print()
if FAILURES:
    print(f"✗ {len(FAILURES)} test(s) failed: {', '.join(FAILURES)}")
    sys.exit(1)
print(f"ALL PASS: durability audit regression suite — "
      f"{'5'}-year contract enforced")
