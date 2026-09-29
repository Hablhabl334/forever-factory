#!/usr/bin/env python3
"""The daily gate — answers ONE question: should the factory run right now?

Stdlib only (no pip install): it must cost the runner ~15 seconds, not
the 3 minutes of a dependency install. Used by daily-factory.yml (as a
gate job) and watchdog.yml (to decide whether to kick the factory).

Prints RUN or SKIP (a single line) and exits 0 either way — a SKIP is a
healthy, cheap outcome, not a failure.

Rules:
  * A human workflow_dispatch always RUNS (explicit intent).
  * A dispatch by github-actions[bot] (the watchdog kicking us) is
    treated like a schedule: subject to the gate.
  * RUN if today's cycle has not completed yet (last_run != today).
  * RUN if an episode from today is in_progress (resume a crash).
  * SKIP if last_run == today (the work is done; a later trigger
    would only burn runner minutes — quota stays untouched).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

STATE = Path(__file__).resolve().parent.parent / "data" / "state.json"


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

    today = date.today().isoformat()
    already_done = state.get("last_run") == today
    resuming = any(
        e.get("status") == "in_progress" and e.get("date") == today
        for e in state.get("episodes", [])
    )

    if already_done and not resuming:
        print(f"SKIP  # last_run={today}, nothing to do")
    else:
        print("RUN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
