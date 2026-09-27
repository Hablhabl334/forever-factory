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
from datetime import date
from pathlib import Path

from .config import cfg, ROOT

LOCK = threading.Lock()
STATE_PATH = ROOT / "data" / "state.json"

DEFAULT = {
    "version": 1,
    "episodes": [],          # [{n, title, hash, seed, date, status, ids}]
    "story_hashes": [],      # no-repeat ledger
    "quota": {"date": None, "units_used": 0},
    "last_run": None,
    "stats": {"videos_published": 0, "days_active": 0},
}


def load() -> dict:
    with LOCK:
        if not STATE_PATH.exists():
            return json.loads(json.dumps(DEFAULT))
        try:
            state = json.loads(STATE_PATH.read_text())
        except json.JSONDecodeError:
            return json.loads(json.dumps(DEFAULT))
        for k, v in DEFAULT.items():
            state.setdefault(k, v)
        return state


def save(state: dict) -> None:
    with LOCK:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=1))
        tmp.replace(STATE_PATH)


def next_episode_number(state: dict) -> int:
    nums = [e["n"] for e in state.get("episodes", [])]
    return (max(nums) + 1) if nums else 1


def used_hashes(state: dict) -> set[str]:
    return set(state.get("story_hashes", []))


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
    }
    state.setdefault("episodes", []).append(ep)
    state.setdefault("story_hashes", []).append(story["hash"])
    save(state)
    return ep


def mark_uploaded(state: dict, episode_n: int, kind: str, video_id: str,
                  units: int) -> None:
    for e in state.get("episodes", []):
        if e["n"] == episode_n:
            if kind == "long":
                e["ids"]["long"] = video_id
            elif kind == "short":
                e["ids"]["shorts"].append(video_id)
            e["status"] = "uploaded" if e["ids"]["long"] else e["status"]
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
    today = date.today().isoformat()
    if q.get("date") != today:
        q["date"] = today
        q["units_used"] = 0
    q["units_used"] = q.get("units_used", 0) + units


def quota_remaining(state: dict) -> int:
    q = state["quota"]
    today = date.today().isoformat()
    if q.get("date") != today:
        return int(cfg()["daily"]["quota_budget"])
    return int(cfg()["daily"]["quota_budget"]) - int(q.get("units_used", 0))
