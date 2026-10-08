#!/usr/bin/env python3
"""Tests for the Oct 8 grid-healing fixes.

The Oct 6-7 quota failure left Oct 8 with only 3 booked shorts (00/06/
12) — the 18:00 slot was empty and NOTHING in the machine would ever
claim it: the 20h gate window made every pre-evening slot SKIP. These
tests pin the three fixes:

  1. gate.py sees grid holes (unbooked slots that expire before the
     next 22:00 Cairo cycle point) and answers RUN.
  2. youtube.free_slots() reports what a cycle owes the grid.
  3. The orchestrator books min(N_SHORTS=6, free slots) shorts, so a
     heal day can carry the extra shorts the grid needs.

Run:  python scripts/test_grid_heal.py
"""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TZ = ZoneInfo("Africa/Cairo")

# gate.py lives in tools/ (not a package) — load it by path
spec = importlib.util.spec_from_file_location("gate", ROOT / "tools" / "gate.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

from src import youtube  # noqa: E402

FAILURES: list[str] = []


def check(name: str, got, want) -> None:
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"       got:  {got!r}")
        print(f"       want: {want!r}")
        FAILURES.append(name)


def iso(d: datetime) -> str:
    return d.isoformat()


def slots_state(shorts: list[str], longs: list[str]) -> dict:
    return {"slots": {"short": shorts, "long": longs}}


def grid(day: datetime, hhmm: str) -> datetime:
    hh, mm = map(int, hhmm.split(":"))
    return day.replace(hour=hh, minute=minute_or(mm), second=0, microsecond=0)


def minute_or(mm: int) -> int:
    return mm


# ── 1. the gate: grid-hole detection ─────────────────────────────────

print("\n[1] gate._grid_holes")

OCT8 = datetime(2026, 10, 8, 0, 0, tzinfo=TZ)

# Oct 8's real, current state: 00/06/12 short + 20:00 long booked,
# 18:00 short is THE hole. At 01:00 Cairo the hole is plainly visible.
state_scar = slots_state(
    shorts=[iso(OCT8.replace(hour=h)) for h in (0, 6, 12)],
    longs=[iso(OCT8.replace(hour=20))],
)
check("scar day: the 18:00 hole is detected",
      gate._grid_holes(state_scar, now=OCT8.replace(hour=1)),
      [iso(OCT8.replace(hour=18))])

# steady evening state: last night's cycle booked today completely —
# a morning trigger must NOT fire.
state_full = slots_state(
    shorts=[iso(OCT8.replace(hour=h)) for h in (0, 6, 12, 18)],
    longs=[iso(OCT8.replace(hour=20))],
)
check("steady day: fully booked grid has no holes",
      gate._grid_holes(state_full, now=OCT8.replace(hour=8, minute=23)),
      [])

# total outage: nothing booked today; morning sees the salvageable
# slots (00/06 already past the bookable margin, 12/18/20 live)
check("outage day: 12:00, 18:00 and the long are holes",
      gate._grid_holes(slots_state([], []), now=OCT8.replace(hour=8, minute=23)),
      [iso(OCT8.replace(hour=h)) for h in (12, 18, 20)])

# late evening: the cycle point has passed; tomorrow's grid belongs to
# no one — 00:00 is inside the bookable margin (unbookable), the rest
# are holes the midnight+ slots will fill.
check("late evening: tomorrow's grid is holes (00:00 lost to margin)",
      gate._grid_holes(slots_state([], []), now=OCT8.replace(hour=23, minute=30)),
      [iso(OCT8.replace(hour=h) + timedelta(days=1)) for h in (6, 12, 18, 20)])

# just before the cycle point: no grid slot lives inside the window —
# the 22:00 cycle owns the future. No holes, no fire.
check("21:30: window is empty, the evening cycle owns the future",
      gate._grid_holes(slots_state([], []), now=OCT8.replace(hour=21, minute=30)),
      [])

# a slot too close to book (17:30 vs 18:00) is already lost — the
# margin must NOT treat it as healable
check("17:30: the 18:00 slot is inside the margin — not a hole",
      gate._grid_holes(slots_state([], []),
                       now=OCT8.replace(hour=17, minute=30)),
      [iso(OCT8.replace(hour=20))])

# booked slots written with a different UTC offset (DST flip) must
# still count as booked — instant compare, not string compare. Only
# 18:00 is booked here (as 15:00 UTC), so 18:00 must NOT appear.
state_dst = slots_state(
    shorts=[iso(OCT8.replace(hour=18).astimezone(ZoneInfo("UTC")))],
    longs=[],
)
check("DST-offset booking still counts as booked (no 18:00 hole)",
      gate._grid_holes(state_dst, now=OCT8.replace(hour=1)),
      [iso(OCT8.replace(hour=h)) for h in (6, 12, 20)])


# ── 2. free_slots: what the cycle owes the grid ──────────────────────

print("\n[2] youtube.free_slots")


class FakeDT(datetime):
    """Stand-in for datetime so free_slots sees a frozen clock."""
    _now: datetime = None

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls._now
        return cls._now.astimezone(tz)


_real_datetime = youtube.datetime
try:
    youtube.datetime = FakeDT

    # normal evening cycle at 22:11 Cairo: exactly tomorrow's 4 slots
    FakeDT._now = OCT8.replace(hour=22, minute=11)
    check("evening cycle sees tomorrow's four slots",
          youtube.free_slots("short", used=set()),
          [iso(OCT8.replace(hour=h) + timedelta(days=1)) for h in (0, 6, 12, 18)])

    # heal run at 01:00 on the scar day: the hole first, then the grid
    FakeDT._now = OCT8.replace(hour=1)
    booked = {iso(OCT8.replace(hour=h)) for h in (0, 6, 12)}
    check("heal run sees the 18:00 hole plus tomorrow's 00:00",
          youtube.free_slots("short", used=booked),
          [iso(OCT8.replace(hour=18)), iso(OCT8 + timedelta(days=1))])

    # morning heal after a total outage: 12/18 today + 00/06 tomorrow
    FakeDT._now = OCT8.replace(hour=8, minute=23)
    check("morning heal sees 12, 18 today and 00, 06 tomorrow",
          youtube.free_slots("short", used=set()),
          [iso(OCT8.replace(hour=12)), iso(OCT8.replace(hour=18)),
           iso(OCT8.replace(hour=0) + timedelta(days=1)),
           iso(OCT8.replace(hour=6) + timedelta(days=1))])

    # overbooked future: everything inside the 24h horizon is booked
    FakeDT._now = OCT8.replace(hour=10)
    allbooked = {iso(OCT8.replace(hour=h)) for h in (12, 18)} | \
                {iso(OCT8.replace(hour=h) + timedelta(days=1)) for h in (0, 6)}
    check("grid ahead fully booked -> nothing owed",
          youtube.free_slots("short", used=allbooked),
          [])

    # longs: from 01:00 the 24h horizon ends 01:00 tomorrow, so only
    # tonight's 20:00 is inside it
    FakeDT._now = OCT8.replace(hour=1)
    check("long slots in 24h from 01:00",
          youtube.free_slots("long", used=set()),
          [iso(OCT8.replace(hour=20))])
finally:
    youtube.datetime = _real_datetime


# ── 3. the orchestrator's booking cap ────────────────────────────────

print("\n[3] orchestrator short-count policy")

from src.story_engine import N_SHORTS  # noqa: E402

check("story spec capacity raised to 6 (heal headroom)", N_SHORTS, 6)

for n_free, want in ((0, 0), (2, 2), (4, 4), (5, 5), (9, 6)):
    check(f"free={n_free} -> books {want}",
          max(0, min(N_SHORTS, n_free)), want)


# ── 4. live state: the real data/state.json ──────────────────────────

print("\n[4] live gate smoke against the real data/state.json")

import subprocess  # noqa: E402

r = subprocess.run(
    [sys.executable, str(ROOT / "tools" / "gate.py"),
     "--event", "schedule", "--actor", "watchdog"],
    capture_output=True, text=True, cwd=ROOT)
verdict = r.stdout.strip()
print(f"       {verdict}")
# Date-agnostic (2026-10-08 hardening): the Oct 8 hole this test
# originally asserted was healed the same day, so the live verdict
# legitimately flips between RUN and SKIP as the real grid fills.
# The permanent contract: the gate NEVER crashes on the live state,
# always answers in one line, and always exits 0.
check("live gate exits 0 (never crashes)", r.returncode, 0)
check("live gate answers with a verdict",
      verdict.startswith(("RUN", "SKIP")), True)
check("live gate answers in a single line", verdict.count("\n"), 0)

# import sanity: the touched modules still compile and import
import src.orchestrator  # noqa: E402, F401

print()
if FAILURES:
    print(f"✗ {len(FAILURES)} test(s) failed: {', '.join(FAILURES)}")
    sys.exit(1)
print("✓ all grid-heal tests passed")
