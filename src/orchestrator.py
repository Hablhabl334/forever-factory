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

from . import art_engine, discovery, ledger, render, shorts as shorts_mod, \
    thumbnails, tts, youtube
from .config import cfg, ROOT
from .story_engine import generate_story, combination_space

WORK_ROOT = ROOT / "work"
OUT_ROOT = ROOT / "out"


def _dated_seed(day: str, episode_n: int) -> int:
    """Deterministic per (date, episode) — the seed a fresh episode
    was born with, reconstructible from the ledger record forever."""
    digest = hashlib.sha256(f"psychlove|{day}|ep{episode_n}".encode()).hexdigest()
    return int(digest[:12], 16)


def _daily_seed(episode_n: int) -> int:
    """Deterministic per (date, episode) — rebuildable after a crash."""
    return _dated_seed(date.today().isoformat(), episode_n)


def _load_slots(state: dict) -> dict[str, set[str]]:
    """The publishAt slots already booked by PAST runs, so two cycles
    in one day (a recovery dispatch, a crash-resume) never stack two
    videos onto the same 6-hour grid slot. Anything older than 2 days
    is dead grid — dropped."""
    from datetime import datetime, timedelta, timezone
    horizon = datetime.now(timezone.utc) - timedelta(days=2)
    out: dict[str, set[str]] = {"long": set(), "short": set()}
    for kind in out:
        for s in (state.get("slots") or {}).get(kind, []) or []:
            try:
                when = datetime.fromisoformat(s)
            except (ValueError, TypeError):
                continue
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            if when >= horizon:
                out[kind].add(s)
    return out


def _remember_slot(state: dict, kind: str, slot: str | None) -> None:
    """Persist a booked slot to the ledger (crash-safe: the same save
    that records the video id records its slot). Only slots that a
    video actually took are remembered — a deferred upload (quota)
    leaves the slot free for the next attempt."""
    if not slot:
        return
    from datetime import datetime, timedelta, timezone
    horizon = datetime.now(timezone.utc) - timedelta(days=2)

    def _aware(s: str):
        try:
            d = datetime.fromisoformat(s)
        except (ValueError, TypeError):
            return None
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

    slots = state.setdefault("slots", {"long": [], "short": []})
    kept = [s for s in slots.setdefault(kind, [])
            if (d := _aware(s)) is not None and d >= horizon]
    if slot not in kept:
        kept.append(slot)
    slots[kind] = kept
    ledger.save(state)


def _resume_episode(state: dict) -> tuple[int, int] | None:
    """Return (n, seed) for a recent in-progress episode, if any.
    Window model: an episode from today OR yesterday can be resumed
    (an evening cycle that crashed after midnight still completes)."""
    from datetime import date, timedelta
    recent = {date.today().isoformat(),
              (date.today() - timedelta(days=1)).isoformat()}
    for e in reversed(state.get("episodes", [])):
        if e.get("status") == "in_progress" and e.get("date") in recent:
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


def _rebuild_thumb(record: dict, state: dict) -> Path | None:
    """Deterministically rebuild an episode's thumbnail PNG from its
    ledger record. The story is a pure function of the seed, the art a
    pure function of the story — no stored assets needed, on any
    machine, forever.

    Seed subtlety: generate_story drifts its seed internally on retry
    (safety gate / hash collision), and the record holds the FINAL
    (post-drift) seed — which replays exactly only if the story
    succeeded on attempt 0. The ORIGINAL pre-drift seed is always
    reconstructible from (date, episode number), and replaying from it
    reproduces the drift chain exactly, because story hashes are
    append-only and collision-free across episodes. We try both and
    hash-check the result — a drift can never silently repackage a
    different story."""
    candidates = []
    for cand in (record.get("seed"),
                 _dated_seed(record.get("date", ""), record.get("n", 0))):
        if cand is not None and cand not in candidates:
            candidates.append(cand)
    used = ledger.used_hashes(state) - {record.get("hash")}
    used_short = ledger.used_short_hashes(state) - set(record.get("shashes", []))
    story = None
    for cand in candidates:
        try:
            s = generate_story(cand, used, used_short)
        except RuntimeError:
            continue
        if s["hash"] == record.get("hash") and s["title"] == record.get("title"):
            story = s
            break
    if story is None:
        print(f"  [thumbs] ep{record['n']}: no seed candidate replays the "
              f"recorded story — skipping (ledger safety)")
        return None
    out_dir = OUT_ROOT / f"episode_{record['n']:03d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    thumb = out_dir / "thumbnail.png"
    if thumb.exists():
        return thumb
    return thumbnails.make_thumbnail(story, thumb, story["seed"])


def backfill_thumbnails(state: dict) -> list[str]:
    """Set custom thumbnails for any uploaded long video missing one.

    Self-healing by design: a channel that was not yet phone-verified
    (youtube.com/verify) rejects thumbnails.set with 403 — this runs
    at the top of EVERY daily cycle and retries cheaply (50 units per
    attempt) until it succeeds once, then never touches that video
    again (flagged in the ledger)."""
    todo = [e for e in state.get("episodes", [])
            if e.get("ids", {}).get("long") and not e.get("ids", {}).get("thumbnail")]
    done: list[str] = []
    if not todo:
        return done
    print(f"[thumbs] {len(todo)} long video(s) missing custom thumbnails")
    token = youtube.get_access_token()
    ch = youtube.verify_credentials()
    print(f"[thumbs] channel: {ch.get('channel')} ({ch.get('channel_id')})")
    for rec in todo:
        if ledger.quota_remaining(state) < youtube.THUMB_UNITS:
            print("  [thumbs] quota low — retrying next cycle")
            break
        png = _rebuild_thumb(rec, state)
        if png is None or not png.exists():
            continue
        if youtube.set_thumbnail(token, rec["ids"]["long"], png):
            ledger.mark_thumbnail(state, rec["n"], youtube.THUMB_UNITS)
            print(f"  [thumbs] ep{rec['n']} thumbnail set "
                  f"({rec['ids']['long']})")
            done.append(rec["ids"]["long"])
        else:
            print("  [thumbs] set rejected — retrying next cycle")
    return done


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

    print(f"[{episode_n}] script: {story['title']} ({story['words']} words, "
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

    # 3. shorts (native vertical, per-chunk text cards)
    short_files = shorts_mod.render_shorts(story, work, out)
    short_files = short_files[:n_shorts]

    # 4. thumbnail (dark bold card, from the story spec)
    thumb = out / "thumbnail.png"
    if not thumb.exists():
        thumbnails.make_thumbnail(story, thumb, story["seed"])
    print(f"[{episode_n}] thumbnail + {len(short_files)} shorts ready")

    # 5. metadata
    from . import metadata as meta_mod
    long_meta = meta_mod.long_metadata(story, narration)

    # 6. upload (or dry-run plan)
    if dry_run:
        long_slot = youtube.next_slot("long", used_slots["long"])
        used_slots["long"].add(long_slot)
        when = long_slot or "now"
        print(f"[{episode_n}] DRY-RUN: would upload long at {when}")
        for i, sf in enumerate(short_files):
            short_slot = youtube.next_slot("short", used_slots["short"])
            used_slots["short"].add(short_slot)
            print(f"[{episode_n}] DRY-RUN: would upload short {i+1} at "
                  f"{short_slot or 'now'}")
        return {"episode": episode_n, "title": story["title"], "dry_run": True,
                "long_seconds": dur, "shorts": len(short_files)}

    # ids the ledger already attributes to THIS episode before the
    # upload pass — a video that comes back adopted (its id was already
    # recorded) already owns a slot in the grid from its original
    # upload. Booking it a second slot would phantom-block the grid and
    # push the next day's long video a day late (Oct 3 lesson).
    rec = next((e for e in state.get("episodes", []) if e.get("n") == episode_n), None)
    rec_ids: set[str] = set()
    if rec:
        eids = rec.get("ids") or {}
        if eids.get("long"):
            rec_ids.add(eids["long"])
        rec_ids.update(eids.get("shorts") or [])

    long_slot = youtube.next_slot("long", used_slots["long"])
    long_id = youtube.upload_video(final, long_meta, long_slot, episode_n, "long", state)
    if long_id is not None and long_id not in rec_ids:
        used_slots["long"].add(long_slot)
        _remember_slot(state, "long", long_slot)

    # upload the 4 shorts into the 6-hour grid (shorts first = the funnel
    # fills before the evening long lands). Idempotent per index: a short
    # whose id is already recorded (a re-run of a finished/resumed
    # episode) is skipped — its video is on the channel with its slot.
    recorded_shorts = list((rec.get("ids") or {}).get("shorts") or []) if rec else []
    for i, sf in enumerate(short_files):
        if i < len(recorded_shorts):
            print(f"  [{episode_n}] short {i+1} already uploaded "
                  f"({recorded_shorts[i]}) — skipping")
            continue
        short_spec = story["shorts"][i] if i < len(story.get("shorts", [])) else {}
        short_meta = meta_mod.short_metadata(story, short_spec)
        short_slot = youtube.next_slot("short", used_slots["short"])
        # thumbnails not set for shorts (auto frame is fine; quota discipline)
        sid = youtube.upload_video(sf, short_meta, short_slot, episode_n, "short", state)
        if sid is None:
            break  # quota exhausted — stop uploading for today
        if sid not in rec_ids:  # fresh upload → its slot is now taken
            used_slots["short"].add(short_slot)
            _remember_slot(state, "short", short_slot)
        recorded_shorts.append(sid)  # a re-run skips this one next time

    return {"episode": episode_n, "title": story["title"], "long_id": long_id,
            "long_seconds": dur, "shorts": len(short_files)}


def run_daily(dry_run: bool = False, longs: int | None = None,
              only_episode: int | None = None) -> list[dict]:
    """The daily cycle. Returns summary dicts for each episode.

    A dry run is fully side-effect-free: the ledger is read-locked
    (nothing persists), last_run is never stamped, and the episode
    bookkeeping stays in memory — a --dry-run must never make the
    gate think the day was produced."""
    if dry_run:
        ledger.set_read_only(True)
    try:
        return _run_daily_inner(dry_run, longs, only_episode)
    finally:
        if dry_run:
            ledger.set_read_only(False)


def _run_daily_inner(dry_run: bool, longs: int | None,
                     only_episode: int | None) -> list[dict]:
    state = ledger.load()

    # self-healing pass first: thumbnails that failed earlier (e.g. the
    # channel was not yet verified) are rebuilt deterministically and
    # retried — a backfill hiccup must never block the day's episodes
    if not dry_run:
        try:
            backfill_thumbnails(state)
        except Exception as e:
            print(f"[thumbs] backfill skipped: {e}")

    # numbers before work: how did yesterday's stories actually do?
    # (read-only scope — works from day one; failures never block)
    if not dry_run:
        discovery.morning_report(state)

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

    used_slots = _load_slots(state)
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

        # when resuming, exclude the episode's own hashes from the no-repeat
        # ledger so the deterministic regeneration reproduces the exact
        # same story instead of colliding with its own record
        record = next((e for e in state["episodes"] if e["n"] == n), None)
        used = ledger.used_hashes(state)
        used_short = ledger.used_short_hashes(state)
        if record:
            used = used - {record.get("hash")}
            used_short = used_short - set(record.get("shashes", []))

        story = generate_story(seed, used, used_short)
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
            if record.get("shashes") != story.get("short_hashes"):
                sh = state.setdefault("short_hashes", [])
                for old in record.get("shashes", []):
                    if old in sh:
                        sh.remove(old)
                for new in story.get("short_hashes", []):
                    if new not in sh:
                        sh.append(new)
                record["shashes"] = list(story.get("short_hashes", []))
            ledger.save(state)

        # distribute the day's shorts: first episode takes the extra one
        n_shorts = (total_shorts + target - 1 - made) // target if target > 1 else total_shorts

        result = produce_episode(story, n, dry_run, n_shorts, used_slots, state)
        results.append(result)
        made += 1

        # flip to done ALWAYS (even dry-run): an episode left
        # in_progress would make the loop resume the SAME episode
        # instead of advancing to the next one
        for e in state["episodes"]:
            if e["n"] == n and e["status"] == "in_progress":
                e["status"] = "done"
        ledger.save(state)

    if not dry_run:
        import time as _time
        state["last_run"] = date.today().isoformat()
        state["last_run_ts"] = int(_time.time())
        state["stats"]["days_active"] += 1 if state.get("_last_days_active") != state["last_run"] else 0
        state["_last_days_active"] = state["last_run"]

        # end-of-day discovery pass: every long (today's + any stragglers)
        # into the love-psychology playlist, channel branding set once —
        # all scope-aware and quota-gated, never blocking, never repeating
        discovery.evening_pass(state)

        ledger.save(state)
    return results


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Psychology of Love — the Forever Factory")
    ap.add_argument("--dry-run", action="store_true", help="produce + plan, no upload")
    ap.add_argument("--longs", type=int, default=None, help="override daily long count")
    ap.add_argument("--episode", type=int, default=None, help="produce only this episode number")
    ap.add_argument("--backfill-thumbs", action="store_true",
                    help="only set missing custom thumbnails, then exit")
    ap.add_argument("--verify-token", action="store_true", help="check YouTube credentials only")
    args = ap.parse_args()

    if args.verify_token:
        out = youtube.verify_credentials()
        print(out)
        return 0 if out.get("ok") else 1

    if args.backfill_thumbs:
        state = ledger.load()
        done = backfill_thumbnails(state)
        print(f"[thumbs] backfill complete: {len(done)} set")
        return 0

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
