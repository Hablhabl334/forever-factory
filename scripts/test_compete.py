#!/usr/bin/env python3
"""Offline test suite for tools/compete.py + the muse steer block.

Same method that caught the trend_intel regex bug: synthetic snapshots
with KNOWN numbers, run the real code path (--offline), assert exact
math and structure. No network, no creds, no quota. Cleans up every
synthetic file it creates; proves state.json is never modified.

Run from the repo root:
    python scripts/test_compete.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

COMP = ROOT / "data" / "competitive"
TREND = ROOT / "data" / "trend"

PASS, FAIL = 0, 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok  {name}")
    else:
        FAIL += 1
        print(f" FAIL {name}  {detail}")


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def recent_video(vid: str, title: str, days_ago: float, views: int,
                 dur: int = 52) -> dict:
    pub = datetime.now(timezone.utc) - timedelta(days=days_ago)
    age = max(days_ago, 0.5)
    return {
        "id": vid, "title": title, "published_at": iso(pub),
        "views": views, "duration_s": dur,
        "age_days": round(age, 1),
        "velocity": round(views / max(age, 0.5), 1),
        "formula": "",
    }


def channel_row(title: str, subs: int, views: int, recent: list) -> dict:
    return {"title": title, "handle": "", "subs": subs, "views": views,
            "video_count": 900, "uploads_playlist": "UU" + title[:8],
            "recent": recent}


def build_synthetic() -> list[Path]:
    """Two snapshots 7 days apart: 4 competitor channels with known
    deltas + our row. Fresh uploads with exact velocity math."""
    COMP.mkdir(parents=True, exist_ok=True)
    TREND.mkdir(parents=True, exist_ok=True)
    today = date.today()
    prev_day = today - timedelta(days=7)

    # prev snapshot: week-old stats
    prev = {
        "date": prev_day.isoformat(),
        "ts": iso(datetime.now(timezone.utc) - timedelta(days=7)),
        "our_id": "UCus0000000000000000000",
        "us": {"id": "UCus0000000000000000000", "title": "Psychology of Love",
               "handle": "@PsychologyOfLove", "subs": 100, "views": 1400,
               "video_count": 104, "uploads_playlist": ""},
        "them": {
            "UCaaa000000000000000000": channel_row("Green Flags Daily", 5000, 200000, []),
            "UCbbb000000000000000000": channel_row("Love Lab", 20000, 900000, []),
            "UCccc000000000000000000": channel_row("Attachment Files", 800, 40000, []),
        },
    }
    # this week: +subs/+views per channel + fresh uploads
    now = {
        "date": today.isoformat(),
        "ts": iso(datetime.now(timezone.utc)),
        "our_id": "UCus0000000000000000000",
        "us": {"id": "UCus0000000000000000000", "title": "Psychology of Love",
               "handle": "@PsychologyOfLove", "subs": 118, "views": 1950,
               "video_count": 139, "uploads_playlist": ""},
        "them": {
            "UCaaa000000000000000000": channel_row(
                "Green Flags Daily", 5200, 230000, [
                    # 6000 views in 3 days -> 2000/day, WARNING formula,
                    # plural "Red Flags" regression guard
                    recent_video("v1", "6 Red Flags You Keep Missing", 3.0, 6000),
                    recent_video("v2", "Top 10 Green Flags in a Partner", 6.0, 30000),
                ]),
            "UCbbb000000000000000000": channel_row(
                "Love Lab", 20400, 950000, [
                    recent_video("v3", "How to Fix a Rough Patch", 2.0, 800),
                    recent_video("v4", "Why Silence Feels Loud", 9.0, 45000, dur=520),
                ]),
            "UCccc000000000000000000": channel_row(
                "Attachment Files", 830, 41000, [
                    recent_video("v5", "Anxious vs Avoidant: Who Wins?", 4.0, 2200),
                ]),
            "UCddd000000000000000000": channel_row(
                "Heartbreak 101", 300, 9000, [
                    recent_video("v6", "5 Signs It Was Never Love", 1.0, 150),
                ]),
        },
    }
    p_prev = COMP / f"snap_{prev['date']}.json"
    p_now = COMP / f"snap_{now['date']}.json"
    p_prev.write_text(json.dumps(prev, indent=1))
    p_now.write_text(json.dumps(now, indent=1))

    # two trend snapshots, 7 days apart — the roster discovery fuel
    t1 = {"source": "niche:q", "ts": iso(datetime.now(timezone.utc)
                                         - timedelta(days=14)),
          "items": [
              {"id": "x1", "title": "vid", "channel": "Green Flags Daily",
               "channel_id": "UCaaa000000000000000000"},
              {"id": "x2", "title": "vid", "channel": "New Niche Star",
               "channel_id": "UCnew000000000000000000"},
              {"id": "x3", "title": "vid", "channel": "One Hit Wonder",
               "channel_id": "UCone000000000000000000"},
          ]}
    t2 = {"source": "niche:q", "ts": iso(datetime.now(timezone.utc)
                                         - timedelta(days=7)),
          "items": [
              {"id": "y1", "title": "vid", "channel": "Green Flags Daily",
               "channel_id": "UCaaa000000000000000000"},
              {"id": "y2", "title": "vid", "channel": "New Niche Star",
               "channel_id": "UCnew000000000000000000"},
              {"id": "y3", "title": "vid", "channel": "Us Ourselves",
               "channel_id": "UCus000000000000000000"},   # must be excluded
          ]}
    (TREND / "trend_test1.json").write_text(json.dumps(t1))
    (TREND / "trend_test2.json").write_text(json.dumps(t2))
    return [p_prev, p_now]


def quarantine() -> Path:
    """Move pre-existing competitive/trend data aside so the suite is
    idempotent no matter what state the repo is in; restored at end."""
    import shutil
    backup = ROOT / "scripts" / ".test_quarantine"
    if backup.exists():
        shutil.rmtree(backup)
    backup.mkdir(parents=True)
    for d in (COMP, TREND):
        if d.exists():
            for p in d.iterdir():
                if p.name == "seeds.json":
                    continue
                p.rename(backup / (d.name + "__" + p.name))
    return backup


def restore(backup: Path) -> None:
    import shutil
    for p in backup.iterdir():
        target_dir = COMP if p.name.startswith("competitive__") else TREND
        p.rename(target_dir / p.name.split("__", 1)[1])
    if backup.exists():
        shutil.rmtree(backup)


def cleanup() -> None:
    for p in COMP.glob("*"):
        if p.name != "seeds.json":
            p.unlink()
    for p in TREND.glob("trend_test*.json"):
        p.unlink()


def main() -> int:
    state_file = ROOT / "data" / "state.json"
    state_before = state_file.read_bytes() if state_file.exists() else b""
    backup = quarantine()
    try:
        return _run_tests(state_file, state_before)
    finally:
        cleanup()
        restore(backup)


def _run_tests(state_file: Path, state_before: bytes) -> int:

    # ── 0. muse steer block: missing file -> "" (byte-identical prompts)
    from src import muse
    check("steer: missing steer.json -> empty block",
          muse._steer_block() == "")

    snaps = build_synthetic()

    # ── 1. roster auto-discovery (file-based, no network)
    import compete
    roster = {"channels": {}}
    notes = compete.discover_from_trends(roster, "UCus0000000000000000000")
    check("roster: 2-appearance channel added",
          "UCnew000000000000000000" in roster["channels"])
    check("roster: our own channel excluded",
          "UCus0000000000000000000" not in roster["channels"])
    check("roster: 1-appearance channel NOT added",
          "UCone000000000000000000" not in roster["channels"])
    check("roster: discovery note written", any("New Niche Star" in n
                                                for n in notes))

    # ── 2. offline replay through the real CLI
    r = subprocess.run(
        [sys.executable, "tools/compete.py", "--offline"],
        capture_output=True, text=True, cwd=ROOT)
    check("offline: exits 0", r.returncode == 0, r.stderr[-300:])
    bench_file = COMP / f"bench_{date.today()}.json"  # placeholder below
    bench_file = COMP / f"bench_{date.today()}.md"
    check("offline: bench report written", bench_file.exists())
    bench = bench_file.read_text() if bench_file.exists() else ""
    steer = json.loads((COMP / "steer.json").read_text()) \
        if (COMP / "steer.json").exists() else {}

    # league table deltas — the exact known numbers
    check("report: our subs delta +18", "+18" in bench)
    check("report: Green Flags Daily subs delta +200", "+200" in bench)
    check("report: Love Lab views delta +50,000", "+50,000" in bench)
    check("report: us pinned as (us)", "(us)" in bench)
    check("report: steal list section present",
          "steal list" in bench.lower())
    check("report: v4 section present", "Us vs the field" in bench)

    # velocity math — v1: 6000 views / 3.0 days = 2000/day
    check("math: velocity 6000/3d = 2000/day", "2,000" in bench)
    # niche fresh avg velocity: (2000+5000+400+5000+550+150)/6 = 13100/6
    check("steer: niche_velocity exact",
          steer.get("niche_velocity") == 2183.3,
          f"got {steer.get('niche_velocity')}")

    # formula classification incl. the plural regression guard
    check("formula: 'Red Flags' plural -> WARNING",
          any(f.get("name") == "WARNING" for f in steer.get("hot_formulas", [])))
    check("steer: fresh week = today", steer.get("week") ==
          date.today().isoformat())
    check("steer: hot_themes present", len(steer.get("hot_themes", [])) > 0)
    check("steer: 3 recommended angles",
          len(steer.get("recommended_angles", [])) == 3)

    # ── 3. read-only guarantee: state.json untouched
    check("state.json: NEVER modified by compete",
          state_file.read_bytes() == state_before if state_file.exists()
          else True)

    # ── 3b. topic queue written by the run (steal list -> next topics)
    from src.content_data import TOPICS as ALL_TOPICS
    tq = json.loads((COMP / "topic_queue.json").read_text()) \
        if (COMP / "topic_queue.json").exists() else {}
    check("queue: week is today", tq.get("week") == date.today().isoformat())
    q = tq.get("queue", [])
    check("queue: both flags topics scored into top-2",
          set(q[:2]) == {"red_flags", "green_flags"}, f"got {q[:2]}")
    check("queue: minimum spread to 4 topics", len(q) >= 4, f"got {len(q)}")
    check("queue: every id is a real topic",
          all(t in ALL_TOPICS for t in q))
    check("queue: why cites the winning video",
          "views)" in tq.get("why", {}).get("green_flags", ""),
          tq.get("why", {}).get("green_flags", "")[:60])

    # ── 3c. story engine consumes the queue deterministically
    from src.story_engine import _steered_topics, generate_story
    known = ["green_flags", "red_flags", "long_distance", "trust"]
    (COMP / "topic_queue.json").write_text(
        json.dumps({"week": date.today().isoformat(), "queue": known}))
    steered = _steered_topics()
    check("engine: fresh queue -> exactly those topics",
          [t for t, _ in steered] == known if steered else False)
    (COMP / "topic_queue.json").write_text(
        json.dumps({"week": date.today().isoformat(),
                    "queue": ["bogus_topic"] + known}))
    check("engine: invalid ids filtered, rest kept",
          [t for t, _ in _steered_topics()] == known)
    bands = {ALL_TOPICS[t]["band"] for t in known}
    in_pool = all(
        generate_story(s)["scenes"][0]["image"]["band"] in bands
        for s in range(1, 13))
    check("engine: 12/12 seeds pick from the steered queue", in_pool)
    h1 = generate_story(777)["hash"]
    h2 = generate_story(777)["hash"]
    check("engine: deterministic under steer (same seed = same story)",
          h1 == h2)
    (COMP / "topic_queue.json").write_text(
        json.dumps({"week": (date.today() - timedelta(days=10)).isoformat(),
                    "queue": known}))
    check("engine: 10-day-old queue ignored (freshness gate)",
          _steered_topics() is None)
    outside = any(
        generate_story(s)["scenes"][0]["image"]["band"] not in bands
        for s in range(1, 16))
    check("engine: stale queue -> full 24-topic pool again", outside)
    (COMP / "topic_queue.json").unlink()

    # ── 4. muse steer block: fresh file -> block; stale -> ""
    block = muse._steer_block()
    check("steer: fresh block mentions WEEKLY STEER",
          "WEEKLY STEER" in block)
    check("steer: block guards no-new-claims",
          "never add facts" in block)
    brief = muse._shorts_brief({"shorts": []})
    check("muse: shorts brief embeds steer", "WEEKLY STEER" in brief)
    stale = {"week": (date.today() - timedelta(days=30)).isoformat(),
             "hot_themes": ["love"], "hot_formulas": [{"name": "WARNING"}]}
    (COMP / "steer.json").write_text(json.dumps(stale))
    check("steer: 30-day-old week -> empty block",
          muse._steer_block() == "")
    (COMP / "steer.json").unlink()

    # ── 5. first-run baseline: single snapshot, no deltas crash
    snaps[0].unlink()                       # remove prev, keep today's
    r2 = subprocess.run(
        [sys.executable, "tools/compete.py", "--offline"],
        capture_output=True, text=True, cwd=ROOT)
    check("baseline: exits 0 with one snapshot", r2.returncode == 0,
          r2.stderr[-300:])
    check("baseline: report notes FIRST BASELINE WEEK",
          "FIRST BASELINE WEEK" in r2.stdout)

    # ── 6. no-snapshot failure path
    snaps[1].unlink()
    r3 = subprocess.run([sys.executable, "tools/compete.py", "--offline"],
                        capture_output=True, text=True, cwd=ROOT)
    check("empty: no snapshots -> clean exit != 0 with guidance",
          r3.returncode != 0 and "no snapshot" in (r3.stdout + r3.stderr))

    cleanup()
    print(f"\n{'ALL PASS' if FAIL == 0 else 'FAILURES: ' + str(FAIL)}"
          f"  ({PASS} checks)")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
