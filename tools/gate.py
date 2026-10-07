#!/usr/bin/env python3
"""The daily gate — answers ONE question: should the factory run right now?

Stdlib only (no pip install): it must cost the runner ~15 seconds, not
the 3 minutes of a dependency install. Used by daily-factory.yml (as a
gate job) and watchdog.yml (to decide whether to kick the factory).

Prints RUN or SKIP (a single line) and exits 0 either way — a SKIP is a
healthy, cheap outcome, not a failure.

Window logic (evening cycle model):
  The cycle runs ~22:00 Cairo and fills tomorrow's 6-hour slot grid,
  so "the day is produced" is NOT a calendar-date question — a
  morning-after trigger must NOT double-produce. SKIP if the last
  successful cycle finished less than WINDOW_HOURS ago (20h: enough
  tolerance to catch a missed evening slot same-day via the backup
  triggers, without letting the next evening fire twice).

Grid-hole logic (Oct 8 lesson):
  A booked cycle is NOT the same as a full grid. Oct 6-7: quota died
  mid-episode, the resume landed ep16's remaining shorts into Oct 8
  00/06/12 — and Oct 8's 18:00 slot stayed empty, because the only run
  that could claim it must fire BEFORE 18:00, and the 20h window made
  every pre-evening slot SKIP. The channel published 3 shorts that day
  instead of 4 and nothing in the machine even noticed. So the gate
  now ALSO looks at the grid itself: a publish slot (short 00/06/12/18
  or long 20:00 Cairo) that is still in the future, still unbooked,
  and falls BEFORE the next 22:00 Cairo cycle point is a HOLE — the
  evening cycle can only book slots after itself, so no future run
  will ever claim it. RUN now and heal it.

  * A human workflow_dispatch (gated=false) always RUNS (force).
  * RUN if a grid hole exists before the next cycle point.
  * RUN if the window has elapsed (last cycle too old).
  * RUN if an episode is in_progress (resume a crash).
  * SKIP if last success is inside the window AND the grid is full.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

STATE = Path(__file__).resolve().parent.parent / "data" / "state.json"
WINDOW_HOURS = 20.0

# Keep in sync with channel.yaml `schedule` (the gate job runs before
# pip install, so it cannot read YAML — the values are frozen here).
GRID_TZ = ZoneInfo("Africa/Cairo")
GRID_SHORT = ("00:00", "06:00", "12:00", "18:00")
GRID_LONG = ("20:00",)
CYCLE_HOUR = 22             # the primary evening cycle starts 22:00 Cairo
BOOKABLE_MARGIN = 40        # minutes: render time before an upload lands


def _grid_holes(state: dict, now: datetime | None = None) -> list[str]:
    """Publish slots nobody will ever book if we don't run now.

    A slot counts as a hole when it is: (1) in the future but inside
    the bookable margin (a run starting now uploads ~25-40 minutes in,
    so a slot closer than that is already lost), (2) before the next
    22:00 Cairo cycle point (slots after it belong to that cycle),
    and (3) not already booked in state.slots. Booked slots are
    compared as INSTANTS (parsed), not strings — Egypt's DST flip
    changes the UTC offset inside otherwise identical ISO strings,
    and a string compare would see a booked slot as a hole."""
    now = now or datetime.now(tz=GRID_TZ)
    holes: list[str] = []
    booked: set[datetime] = set()
    for kind in ("short", "long"):
        for s in (state.get("slots") or {}).get(kind, []) or []:
            try:
                when = datetime.fromisoformat(s)
            except (ValueError, TypeError):
                continue
            if when.tzinfo is None:
                when = when.replace(tzinfo=GRID_TZ)
            booked.add(when)

    # the next 22:00 Cairo strictly after now (the cycle point)
    point = now.replace(hour=CYCLE_HOUR, minute=0, second=0, microsecond=0)
    if now >= point:
        point += timedelta(days=1)

    probe = now + timedelta(minutes=BOOKABLE_MARGIN)
    day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    for _ in range(3):  # today + tomorrow + margin is plenty
        for hhmm in GRID_SHORT + GRID_LONG:
            hh, mm = map(int, hhmm.split(":"))
            slot_dt = day.replace(hour=hh, minute=mm)
            if probe < slot_dt <= point and slot_dt not in booked:
                holes.append(slot_dt.isoformat())
        day += timedelta(days=1)
    return holes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", default="schedule",
                    help="github.event_name of the calling workflow")
    ap.add_argument("--actor", default="",
                    help="github.actor of the calling workflow")
    args = ap.parse_args()

    human = args.event == "workflow_dispatch" and \
        not args.actor.startswith("github-actions")
    if human:
        print("RUN")
        return 0

    state = {"last_run": None, "episodes": [], "quota": {}}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text())
        except json.JSONDecodeError:
            pass

    # server-side quota back-off (stamped by the upload layer when
    # YouTube itself refused an upload, with the real reason). Retry
    # slots before the window clears would just re-render the whole
    # episode against the same dead wall — skip them cheaply.
    q = state.get("quota") or {}
    defer_until = q.get("defer_until") or 0
    if defer_until > time.time():
        print(f"SKIP  # server-side {q.get('defer_reason', 'quota')} defer "
              f"until {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(defer_until))}")
        return 0

    # grid holes: unbooked slots that expire before the next cycle
    # could ever claim them — the strongest possible reason to run.
    holes = _grid_holes(state)
    if holes:
        print(f"RUN   # {len(holes)} grid hole(s) before the next cycle "
              f"point: {', '.join(holes[:3])}"
              f"{' …' if len(holes) > 3 else ''}")
        return 0

    # last successful cycle -> epoch seconds. Records written by the
    # window system carry last_run_ts; legacy date-only records are
    # pre-window (treat as STALE so the first deployed cycle runs —
    # the concurrency group + a fresh stamp keep duplicates cheap).
    last_ts = state.get("last_run_ts")
    age_h = (time.time() - last_ts) / 3600.0 if last_ts else None
    resuming = any(e.get("status") == "in_progress"
                   for e in state.get("episodes", []))

    if last_ts and age_h < WINDOW_HOURS and not resuming:
        print(f"SKIP  # last cycle {age_h:.1f}h ago (< {WINDOW_HOURS:.0f}h window)")
    else:
        why = "no successful cycle yet" if not last_ts else f"last cycle {age_h:.1f}h ago"
        if resuming:
            why += " + in-progress episode to resume"
        print(f"RUN   # {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
