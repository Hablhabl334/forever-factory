"""The factory's memory — data/state.json, committed by every daily run.

Holds the episode ledger (what was produced, what was uploaded, YouTube
ids), the no-repeat story hashes, and the daily quota ledger. Because
the workflow commits this file back to the repo every day, the memory
survives forever on GitHub itself — and the daily commit keeps the
Actions schedule from ever being disabled for inactivity.
"""
from __future__ import annotations

import json
import threading
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import cfg, ROOT

LOCK = threading.Lock()
STATE_PATH = ROOT / "data" / "state.json"
BAK_PATH = ROOT / "data" / "state.json.bak"

# Dry-run protection: when read-only, save() is a no-op so a --dry-run
# can never pollute the real memory (the daily gate reads last_run —
# a dry-run that stamped today would make the real cycle skip).
_READ_ONLY = False

# YouTube's quota window resets at midnight PACIFIC time, not UTC
# midnight. A UTC-date ledger turns "fresh" seven hours early
# (00:00-07:00 UTC): a morning run in that gap happily renders a
# whole episode and only learns the truth from a 403. The ledger
# must roll over exactly when YouTube's real window does.
# (PST/EDT shifts are handled by the zone database automatically.)
_PT = ZoneInfo("America/Los_Angeles")


def _quota_today() -> str:
    """The date YouTube's real quota window is currently in."""
    return datetime.now(_PT).date().isoformat()


def set_read_only(v: bool) -> None:
    global _READ_ONLY
    _READ_ONLY = v

DEFAULT = {
    "version": 1,
    "episodes": [],          # [{n, title, hash, seed, date, status, ids, shashes}]
    "story_hashes": [],      # no-repeat ledger (long scripts)
    "short_hashes": [],      # no-repeat ledger (Short scripts — the forever bank)
    "quota": {"date": None, "units_used": 0},
    "last_run": None,
    "stats": {"videos_published": 0, "days_active": 0},
}


def load() -> dict:
    """Load the memory, never raising, never silently forgetting.

    Five-year durability (2026-10-08 audit): a truncated or corrupted
    state.json (disk blip, git accident, half-written file) previously
    fell back to DEFAULT — TOTAL AMNESIA. The factory would restart
    episode numbering, lose the no-repeat banks, and could duplicate
    content. The recovery ladder is now: state.json -> state.json.bak
    (last known good, rewritten on every save) -> DEFAULT, with a
    loud printed warning either way so the incident is visible in
    factory.log and the run summary.
    """
    with LOCK:
        for path in (STATE_PATH, BAK_PATH):
            if not path.exists():
                continue
            try:
                state = json.loads(path.read_text())
            except json.JSONDecodeError as e:
                print(f"[memory] WARNING: {path.name} is corrupt "
                      f"({e}) — trying the next recovery source")
                continue
            if path is not STATE_PATH:
                print(f"[memory] recovered from {path.name} (state.json "
                      f"was unreadable) — the next save rewrites both")
            for k, v in DEFAULT.items():
                state.setdefault(k, v)
            return state
        print("[memory] WARNING: no readable state — starting from the "
              "empty default (first run, or both files corrupt)")
        return json.loads(json.dumps(DEFAULT))


def save(state: dict) -> None:
    if _READ_ONLY:
        return
    with LOCK:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        # keep the last-known-good copy fresh: if the current state.json
        # still parses, it becomes the .bak BEFORE the new write lands.
        # (The write itself is atomic: tmp + replace — the .bak guards
        # against corruption that happens OUTSIDE this function, e.g. a
        # bad rebase or a runner disk fault.)
        if STATE_PATH.exists():
            try:
                current = STATE_PATH.read_text()
                json.loads(current)          # validates before promoting
                BAK_PATH.write_text(current)
            except (json.JSONDecodeError, OSError):
                pass  # current file already bad — keep the older .bak
        tmp = STATE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=1))
        tmp.replace(STATE_PATH)
        # invariant: a PARSEABLE .bak always exists. If the .bak is
        # missing or itself corrupt (e.g. both files were hit), the
        # freshly-serialized state becomes the new baseline — one
        # save after any double corruption fully repairs the ladder.
        try:
            json.loads(BAK_PATH.read_text())
        except Exception:
            BAK_PATH.write_text(json.dumps(state, indent=1))


def next_episode_number(state: dict) -> int:
    nums = [e["n"] for e in state.get("episodes", [])]
    return (max(nums) + 1) if nums else 1


def used_hashes(state: dict) -> set[str]:
    return set(state.get("story_hashes", []))


def used_short_hashes(state: dict) -> set[str]:
    """Every Short script ever produced — the anti-repeat set that
    keeps the daily Shorts fresh for decades, not days."""
    return set(state.get("short_hashes", []))


def register_story(state: dict, story: dict, episode_n: int, today: str) -> dict:
    """Record the episode BEFORE work begins (crash-safe ordering —
    the story is a pure function of its seed, so it can always be
    rebuilt and completed after an interruption)."""
    ep = {
        "n": episode_n,
        "title": story["title"],
        "hash": story["hash"],
        "seed": story["seed"],
        "date": today,
        "status": "in_progress",
        "ids": {"long": None, "shorts": [], "thumbnail": None},
        "shashes": list(story.get("short_hashes", [])),
    }
    state.setdefault("episodes", []).append(ep)
    state.setdefault("story_hashes", []).append(story["hash"])
    sh = state.setdefault("short_hashes", [])
    for h in story.get("short_hashes", []):
        if h not in sh:
            sh.append(h)
    save(state)
    return ep


def mark_uploaded(state: dict, episode_n: int, kind: str, video_id: str,
                  units: int) -> None:
    for e in state.get("episodes", []):
        if e["n"] == episode_n:
            if kind == "long":
                e["ids"]["long"] = video_id
            elif kind == "short":
                # one record per video — an id can never legitimately
                # appear twice in the same episode's shorts
                if video_id not in e["ids"]["shorts"]:
                    e["ids"]["shorts"].append(video_id)
            # NOTE (Oct 7 hardening): the status is deliberately NOT
            # touched here. Flipping to "uploaded" the moment the long
            # lands silently stranded episodes whose shorts were still
            # pending (quota died mid-shorts): the episode left the
            # in_progress state, so neither the resume window nor the
            # daily gate ever looked at it again — the missing shorts
            # were lost with no trace. The ONLY terminal transition is
            # the orchestrator's completeness flip (long + every short
            # recorded). "uploaded" is kept for legacy records only.
            break
    spend_quota(state, units)
    save(state)


def mark_thumbnail(state: dict, episode_n: int, units: int = 0) -> None:
    """Record that the episode's long video has a custom thumbnail set.
    Idempotent (a re-run never resets it) — this is the flag the daily
    backfill checks, so a thumbnail is attempted exactly once in the
    video's lifetime, forever."""
    for e in state.get("episodes", []):
        if e["n"] == episode_n:
            e.setdefault("ids", {})["thumbnail"] = date.today().isoformat()
            break
    if units:
        spend_quota(state, units)
    save(state)


def spend_quota(state: dict, units: int) -> None:
    q = state["quota"]
    today = _quota_today()
    if q.get("date") != today:
        q["date"] = today
        q["units_used"] = 0
    q["units_used"] = q.get("units_used", 0) + units


def quota_remaining(state: dict) -> int:
    q = state["quota"]
    if q.get("date") != _quota_today():
        return int(cfg()["daily"]["quota_budget"])
    return int(cfg()["daily"]["quota_budget"]) - int(q.get("units_used", 0))
