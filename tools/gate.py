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

  * A human workflow_dispatch (gated=false) always RUNS (force).
  * RUN if the window has elapsed (last cycle too old).
  * RUN if an episode is in_progress (resume a crash).
  * SKIP if last success is inside the window.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

STATE = Path(__file__).resolve().parent.parent / "data" / "state.json"
WINDOW_HOURS = 20.0


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

    state = {"last_run": None, "episodes": []}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text())
        except json.JSONDecodeError:
            pass

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
