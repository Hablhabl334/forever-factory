#!/usr/bin/env python3
"""One-line suffix for the daily memory-commit message:
' (uploads deferred: <reason>)' when a server-side quota defer is
still active, else ''. Stdlib only — called from the workflow's
memory-commit step so the git log itself tells the deferral story
(a bare 'factory memory: DATE cycle' on a day nothing published
is exactly the trap that hid the Oct 7 deferrals)."""
import json
import time
from pathlib import Path

STATE = Path(__file__).resolve().parent.parent / "data" / "state.json"

try:
    q = (json.loads(STATE.read_text()) or {}).get("quota") or {}
    if (q.get("defer_until") or 0) > time.time():
        print(f" (uploads deferred: {q.get('defer_reason', 'quota')})")
except Exception:
    pass  # no state, unreadable state — plain commit message is fine
