"""The orchestrator — one command that runs the whole factory.

Idempotent and crash-safe: episode seeds are recorded in state BEFORE
work begins, and every stage (story, art, narration, clips, shorts,
metadata, upload) skips whatever is already done. A run that dies
mid-render loses nothing; the next run completes the same episode.

Daily output (default): 2 brand-new original bedtime stories (~12 min
each) + 3 Shorts auto-cut from them, uploaded once and publishAt-
scheduled into Cairo peak slots. Total YouTube quota: 8,100 of 10,000.
"""
from __future__ import annotations

import hashlib
import sys
import traceback
from datetime import date
from pathlib import Path

from . import ledger, render, shorts as shorts_mod, thumbnails, tts, youtube
from .config import cfg, ROOT
from .story_engine import generate_story, combination_space

WORK_ROOT = ROOT / "work"
OUT_ROOT = ROOT / "out"


def _daily_seed(episode_n: int) -> int:
    """Deterministic per (date, episode) — rebuildable after a crash."""
    today = date.today().isoformat()
    digest = hashlib.sha256(f"moonberry|{today}|ep{episode_n}".encode()).hexdigest()
    return int(digest[:12], 16)


def _resume_episode(state: dict) -> tuple[int, int] | None:
    """Return (n, seed) for an in-progress episode from today, if any."""
    today = date.today().isoformat()
    for e in reversed(state.get("episodes", [])):
        if e.get("status") == "in_progress" and e.get("date") == today:
            return e["n"], e["seed"]
    return None


def _ensure_clean(work: Path, out: Path, story: dict) -> None:
    """If the story changed underneath (regeneration after a crash),
    wipe the episode's caches so no stale art/clips/shorts survive."""
    import shutil
    marker = work / "story_hash.txt"
    current = marker.read_text().strip() if marker.exists() else None
    if current != story["hash"]:
        if work.exists():
            shutil.rmtree(work)
        if out.exists():
            shutil.rmtree(out)
        work.mkdir(parents=True, exist_ok=True)
        out.mkdir(parents=True, exist_ok=True)
        marker.write_text(story["hash"])


def produce_episode(story: dict, episode_n: int, dry_run: bool,
                     n_shorts: int, used_slots: dict,
                     state: dict | None = None) -> dict:
    """Art -> narration -> render -> shorts -> thumbs -> metadata -> upload.
    state is passed through so uploads mark the SAME ledger the
    orchestrator saves (single source of truth — ids never lost)."""
    if state is None:
        state = ledger.load()
    work = WORK_ROOT / f"episode_{episode_n:03d}"
    out = OUT_ROOT / f"episode_{episode_n:03d}"
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    _ensure_clean(work, out, story)

    print(f"[{episode_n}] story: {story['title']} ({story['words']} words, "
          f"hash {story['hash'][:10]})")

    # 1. narration (idempotent, exact caption timings)
    narration = tts.narrate(story, work)
    print(f"[{episode_n}] narration: {narration['total']:.0f}s, "
          f"{len(narration['chunks'])} caption chunks")

    # 2. long video (resumable clips)
    final = render.render_episode(story, narration, work, out, story["seed"])
    info = render.probe(final)
    dur = float(info["format"]["duration"])
    print(f"[{episode_n}] long video: {dur:.0f}s, "
          f"{final.stat().st_size / 1e6:.1f}MB")

    # 3. shorts (auto-cut)
    short_files = shorts_mod.render_shorts(final, story, narration, work, out)
    short_files = short_files[:n_shorts]

    # 4. thumbnail from the "turn" scene (magic moment)
    turn_scene = next((s for s in story["scenes"] if s["id"] == "turn"),
                      story["scenes"][7])
    thumb = out / "thumbnail.png"
    if not thumb.exists():
        scene_png = work / "art" / f"scene_{turn_scene['n']:02d}.png"
        thumbnails.make_thumbnail(scene_png, story["title"], thumb)
    print(f"[{episode_n}] thumbnail + {len(short_files)} shorts ready")

    # 5. metadata
    from . import metadata as meta_mod
    long_meta = meta_mod.long_metadata(story, narration)

    # 6. upload (or dry-run plan)
    if dry_run:
        long_slot = youtube.next_slot("long", used_slots["long"])
        used_slots["long"].add(long_slot)
        print(f"[{episode_n}] DRY-RUN: would upload long at {long_slot}")
        for i, sf in enumerate(short_files):
            short_slot = youtube.next_slot("short", used_slots["short"])
            used_slots["short"].add(short_slot)
            print(f"[{episode_n}] DRY-RUN: would upload short {i+1} at {short_slot}")
        return {"episode": episode_n, "title": story["title"], "dry_run": True,
                "long_seconds": dur, "shorts": len(short_files)}

    long_slot = youtube.next_slot("long", used_slots["long"])
    used_slots["long"].add(long_slot)
    long_id = youtube.upload_video(final, long_meta, long_slot, episode_n, "long", state)

    for sf in short_files:
        n = int(sf.stem.split("scene")[-1])
        window = {"scene": n, "id": "short"}
        short_meta = meta_mod.short_metadata(story, window)
        short_slot = youtube.next_slot("short", used_slots["short"])
        used_slots["short"].add(short_slot)
        # thumbnails not set for shorts (auto frame is fine; quota discipline)
        sid = youtube.upload_video(sf, short_meta, short_slot, episode_n, "short", state)
        if sid is None:
            break  # quota exhausted — stop uploading for today

    return {"episode": episode_n, "title": story["title"], "long_id": long_id,
            "long_seconds": dur, "shorts": len(short_files)}


def run_daily(dry_run: bool = False, longs: int | None = None,
              only_episode: int | None = None) -> list[dict]:
    """The daily cycle. Returns summary dicts for each episode."""
    state = ledger.load()
    target = int(longs or cfg()["daily"]["long_videos"])
    total_shorts = int(cfg()["shorts"]["count"])
    results: list[dict] = []

    # quota gate for the whole day
    if not dry_run:
        remaining = ledger.quota_remaining(state)
        need = target * (youtube.UPLOAD_UNITS + youtube.THUMB_UNITS) + \
               total_shorts * youtube.UPLOAD_UNITS
        if remaining < need:
            print(f"[quota] only {remaining} units left (need {need}) — "
                  f"deferring today's uploads")
            return results

    used_slots = {"long": set(), "short": set()}
    made = 0
    while made < target:
        # resume an interrupted episode from today, else start a fresh one
        resumed = _resume_episode(state)
        if resumed and only_episode is None:
            n, seed = resumed
        elif only_episode is not None:
            n = only_episode
            seed = _daily_seed(n)
        else:
            n = ledger.next_episode_number(state)
            seed = _daily_seed(n)

        # when resuming, exclude the episode's own hash from the no-repeat
        # ledger so the deterministic regeneration reproduces the exact
        # same story instead of colliding with its own record
        record = next((e for e in state["episodes"] if e["n"] == n), None)
        used = ledger.used_hashes(state)
        if record:
            used = used - {record.get("hash")}

        story = generate_story(seed, used)
        if record is None:
            ledger.register_story(state, story, n, date.today().isoformat())
        else:
            # keep the record in lockstep with what is actually produced
            if record.get("hash") != story["hash"]:
                hashes = state.setdefault("story_hashes", [])
                if record.get("hash") in hashes:
                    hashes.remove(record["hash"])
                if story["hash"] not in hashes:
                    hashes.append(story["hash"])
                record["hash"] = story["hash"]
                record["title"] = story["title"]
                record["seed"] = story["seed"]
            ledger.save(state)

        # distribute the day's shorts: first episode takes the extra one
        n_shorts = (total_shorts + target - 1 - made) // target if target > 1 else total_shorts

        result = produce_episode(story, n, dry_run, n_shorts, used_slots, state)
        results.append(result)
        made += 1

        if not dry_run:
            for e in state["episodes"]:
                if e["n"] == n and e["status"] == "in_progress":
                    e["status"] = "done"
            ledger.save(state)

    state["last_run"] = date.today().isoformat()
    state["stats"]["days_active"] += 1 if state.get("_last_days_active") != state["last_run"] else 0
    state["_last_days_active"] = state["last_run"]
    ledger.save(state)
    return results


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Moonberry Tales — the Forever Factory")
    ap.add_argument("--dry-run", action="store_true", help="produce + plan, no upload")
    ap.add_argument("--longs", type=int, default=None, help="override daily long count")
    ap.add_argument("--episode", type=int, default=None, help="produce only this episode number")
    ap.add_argument("--verify-token", action="store_true", help="check YouTube credentials only")
    args = ap.parse_args()

    if args.verify_token:
        out = youtube.verify_credentials()
        print(out)
        return 0 if out.get("ok") else 1

    try:
        results = run_daily(dry_run=args.dry_run, longs=args.longs,
                            only_episode=args.episode)
        for r in results:
            print(f"  ✓ episode {r['episode']}: {r['title']}")
        print(f"combination space: {combination_space():,} stories — "
              f"the factory never repeats")
        return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
