#!/usr/bin/env python3
"""Close resolved failure Issues — the alert queue must stay clean.

Every failed cycle auto-opens "Factory cycle failed — YYYY-MM-DD".
The machine self-heals the next day, but the Issue stayed open
forever — after years of operation that queue would bury the ONE
open issue that actually needs a human. This tool runs after every
SUCCESSFUL cycle and closes failure issues whose date is strictly
in the past (today's issue, if any, stays open — a same-day
failure-recovery is still worth a glance; a clean day is the close
signal). Pure best-effort: any gh/network error prints and exits 0
so it can never fail the run that hosted it.

Usage (from the repo root, GH_TOKEN in the environment):
    python3 tools/close_resolved_issues.py [--today 2026-10-08] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date

TITLE_RE = re.compile(r"Factory cycle failed — (\d{4}-\d{2}-\d{2})")


def _gh(args: list[str]) -> str:
    r = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)}: {r.stderr.strip()[:200]}")
    return r.stdout


def _open_failure_issues() -> list[dict]:
    out = _gh(["issue", "list", "--state", "open",
               "--search", 'in:title "Factory cycle failed"',
               "--json", "number,title", "--limit", "100"])
    return json.loads(out or "[]")


def close_resolved(today: str, dry_run: bool = False) -> list[int]:
    """Close every open failure issue dated before `today`.

    Returns the issue numbers it closed (empty list = nothing to do,
    or gh was unavailable — both are non-events)."""
    try:
        issues = _open_failure_issues()
    except Exception as e:  # gh missing / no network / no perms
        print(f"[issues] could not list failure issues: {e}")
        return []
    closed: list[int] = []
    for it in issues:
        m = TITLE_RE.search(it.get("title", ""))
        if not m:
            continue
        issue_day = m.group(1)
        if issue_day >= today:
            continue  # today's (or malformed) — leave it for a human
        num = it["number"]
        print(f"[issues] closing #{num} '{it['title']}' — the machine "
              f"recovered (today {today})")
        if dry_run:
            closed.append(num)
            continue
        try:
            _gh(["issue", "close", str(num), "--comment",
                 "Auto-closed: a later cycle completed successfully — "
                 "this failure was self-healed. (factory housekeeping)"])
            closed.append(num)
        except Exception as e:
            print(f"[issues] failed to close #{num}: {e}")
    if not closed:
        print("[issues] no resolved failure issues to close")
    return closed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=date.today().isoformat(),
                    help="reference date (for tests); default = today")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    close_resolved(args.today, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
