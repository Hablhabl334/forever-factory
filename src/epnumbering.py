"""The #epN system — every video on the channel numbered, forever.

Owner decision, 2026-11-01: the identical fixed Shorts title (the
subscription funnel) put the SAME exact string on 130+ videos —
YouTube read them as duplicate titles (wrong for the algorithm) and a
viewer could not reference "that one Short". Every video now carries a
unique #epN in its title and an "Episode #N" line in its description.

Two moving parts:

  * FORWARD numbering — produce_episode claims the next number from
    the ledger counter BEFORE each upload (ledger.allocate_ep_number),
    the number rides in the upload title/description, and it is bound
    to the video id on success (ledger.bind_ep_number). From the first
    numbered upload on, no two videos on the channel share a title.

  * The BACKFILL (renumber_and_rename) — runs at the end of every
    daily cycle. It inventories the channel (uploads playlist, the
    live titles are the truth), gives every un-numbered video — the
    ~170 pre-decision videos plus any crash-orphan the ledger never
    recorded — its chronological number, then RENAMES what the day's
    leftover quota affords (videos.update = 50 units each, newest
    first: recent uploads get algorithmic relief soonest). ~170 legacy
    videos ≈ 6 daily cycles; resumable, self-verifying, never blocking
    the day.

Locked settings are untouched: the publish grid, the CTA text, the
fixed hashtags, the playlist/channel branding, the niche — only the
title/description text gains the number.
"""
from __future__ import annotations

import re
import time
from datetime import date

from . import ledger, metadata, youtube

# "#ep42" in a title (word-bounded: "#ep420x" and "#episode7" never match)
EP_TAG_RE = re.compile(r"#ep(\d+)\b")
# never spend the day's last quota units on renames — the reserve keeps
# heal runs alive (a rename is never worth more than an upload)
RESERVE_UNITS = 100
# a rename that keeps failing for a NON-quota reason (400 bad title...)
# stops retrying after this many attempts so one broken video can never
# burn a slot of the daily budget forever — it waits for a human
MAX_ATTEMPTS = 3


def _ledger_videos(state: dict) -> dict[str, dict]:
    """Every video id the ledger has ever recorded: {vid: {kind, episode}}."""
    out: dict[str, dict] = {}
    for e in state.get("episodes", []):
        eids = e.get("ids") or {}
        if eids.get("long"):
            out[eids["long"]] = {"kind": "long", "episode": e.get("n")}
        for s in eids.get("shorts") or []:
            if s:
                out.setdefault(s, {"kind": "short", "episode": e.get("n")})
    return out


def _is_real(snippet: dict) -> bool:
    """A numberable video is a REAL video: an abandoned resumable-init
    session leaves a zero-duration placeholder (P0D) on the channel —
    numbering trash would put holes in the viewer-facing sequence."""
    return float(snippet.get("_duration", 0) or 0) >= 30.0


def new_title_for(current: str, n: int) -> str:
    """The rename rule for an OLD video, built from what is LIVE today.

      * already numbered      -> unchanged (idempotent)
      * the old fixed Short   -> the #epN is inserted between the CTA
        title                  and the fixed hashtags (the exact shape
                                new Shorts are born with)
      * anything else (longs) -> " #epN" appended, clipped to 100 chars
    """
    tag = f"#ep{n}"
    base = (current or "").strip()
    if EP_TAG_RE.search(base):
        return base                      # never renumber a numbered video
    if base == metadata.SHORT_TITLE:
        cta = metadata.SHORT_TITLE[:-len(metadata.SHORT_HASHTAGS)].rstrip()
        numbered = f"{cta} {tag} {metadata.SHORT_HASHTAGS}"
        return numbered if len(numbered) <= 100 else f"{cta} {tag}"
    suffix = f" {tag}"
    if len(base) + len(suffix) > 100:
        base = base[:100 - len(suffix)].rstrip()
    return base + suffix


def new_description_for(desc: str, n: int, kind: str) -> str:
    """Append the episode line to a live description (idempotent). The
    sentence is the SAME one new videos are born with, so a renamed
    legacy video and a born-numbered video read identically."""
    d = desc or ""
    if f"Episode #{n}" in d:
        return d
    line = (metadata.SHORT_EP_LINE if kind == "short"
            else metadata.LONG_EP_LINE).format(n=n)
    if not d.strip():
        return line
    return d.rstrip() + "\n\n" + line


def renumber_and_rename(state: dict) -> dict:
    """The daily #epN pass: number everything, rename what quota allows.

    Phase A (assign, ~5-9 read units): inventory the channel, give
    every un-numbered real video its chronological number, mark live
    numbered titles as done. Phase B (rename, 50 units per video,
    newest first, inside leftover quota minus the reserve): rewrite
    titles/descriptions until the budget or the backlog runs out.
    Idempotent and crash-safe at every step: the LIVE title is the
    truth, so a crash between update and bookkeeping self-heals on the
    next pass without spending a unit.
    """
    summary = {"assigned": 0, "renamed": 0, "verified": 0,
               "pending": 0, "skipped": 0, "placeholders": 0}
    box = state.setdefault("ep_numbering", {})
    vids = box.setdefault("videos", {})

    # server-side quota back-off: if YouTube itself already refused this
    # window, renames would refuse too — and each blind retry would burn
    # a video's attempt budget. Hold the whole pass (same contract as
    # production deferrals); the marker self-expires at the reset.
    q = state.get("quota") or {}
    if (q.get("defer_until") or 0) > time.time():
        print(f"[epnum] server-side {q.get('defer_reason', 'quota')} defer "
              f"active — numbering pass held (resumes after the reset)")
        return summary

    token = youtube.get_access_token()
    ledger_map = _ledger_videos(state)
    channel = youtube.list_channel_videos(token, state)
    today = date.today().isoformat()

    # ── Phase A1: the LIVE titles are the truth ─────────────────────
    # anything whose live title carries a number IS numbered and IS
    # renamed (title+description change atomically in one update), no
    # matter what the local map forgot — crash-safety for free.
    for vid, title in channel.items():
        m = EP_TAG_RE.search(title or "")
        if not m:
            continue
        rec = vids.setdefault(vid, {})
        rec["n"] = int(m.group(1))
        if not rec.get("kind"):
            info = ledger_map.get(vid) or {"kind": "orphan", "episode": None}
            rec["kind"] = info["kind"]
            rec["episode"] = info["episode"]
        if not rec.get("renamed"):
            rec["renamed"] = today
            summary["verified"] += 1

    # what needs numbers: channel/ledger videos with no number yet
    candidates = [vid for vid in dict.fromkeys(list(ledger_map) + list(channel))
                  if vid not in vids]
    pending = [vid for vid, rec in vids.items()
               if rec.get("n") and not rec.get("renamed")]

    # ── Phase A2: fetch what we need (batched, 1 unit per 50) ───────
    want = sorted(set(candidates) | set(pending))
    snips: dict[str, dict] = {}
    if want:
        snips = youtube.fetch_video_snippets(token, want, state)

    # placeholders are remembered so they are never re-fetched forever
    for vid, sn in snips.items():
        if vid not in vids and not _is_real(sn):
            vids[vid] = {"placeholder": True}
            summary["placeholders"] += 1
            print(f"  [epnum] {vid} is a zero-duration placeholder — "
                  f"never numbered (abandoned upload session; delete it "
                  f"in YouTube Studio if you want it gone)")

    # ── Phase A3: chronological assignment ─────────────────────────
    # The block starts at #1 — the OLD videos were published before
    # any born-numbered one, so they own the low numbers by age. A new
    # video that already claimed a high number (allocation seeds the
    # counter from the ledger, so it can never take a low one) is
    # simply skipped; the sequence stays dense, unique and roughly
    # chronological even when production ran before the first sync.
    fresh = sorted((sn.get("publishedAt") or "", vid)
                   for vid, sn in snips.items()
                   if vid not in vids and _is_real(sn))
    used = {rec.get("n") for rec in vids.values() if rec.get("n")}
    seq = 1
    for _, vid in fresh:
        # a number already taken (a born-numbered video claimed it after
        # this pass seeded its counter) is skipped — sequence integrity
        # beats chronology perfection on the rare collision
        while seq in used:
            seq += 1
        info = ledger_map.get(vid) or {"kind": "orphan", "episode": None}
        vids[vid] = {"n": seq, "kind": info["kind"], "episode": info["episode"]}
        used.add(seq)
        seq += 1
        summary["assigned"] += 1
    # the counter must stay AHEAD of every number ever handed out
    box["seq_next"] = max(int(box.get("seq_next", 1)), seq)
    box["channel_synced"] = True      # allocate_ep_number stops seeding
    ledger.save(state)

    if summary["assigned"]:
        print(f"[epnum] assigned {summary['assigned']} number(s); "
              f"next new video is #{box['seq_next']}")

    # ── Phase B: rename, newest first, inside the leftover quota ────
    todo = sorted(((rec["n"], vid) for vid, rec in vids.items()
                   if rec.get("n") and not rec.get("renamed")),
                  reverse=True)
    if todo:
        print(f"[epnum] {len(todo)} video(s) still to rename — "
              f"{ledger.quota_remaining(state)} units left, "
              f"{youtube.UPDATE_UNITS}+{RESERVE_UNITS} per rename")
    for n, vid in todo:
        if ledger.quota_remaining(state) < youtube.UPDATE_UNITS + RESERVE_UNITS:
            print("  [epnum] rename budget spent — resuming next cycle")
            break
        sn = snips.get(vid)
        if sn is None:
            continue                     # not fetched this pass — next cycle
        kind = vids[vid].get("kind", "long")
        title = new_title_for(sn.get("title") or channel.get(vid) or "", n)
        desc = new_description_for(sn.get("description") or "", n, kind)
        if title == (sn.get("title") or "") and f"Episode #{n}" in (sn.get("description") or ""):
            vids[vid]["renamed"] = today  # already carries both — verified
            summary["verified"] += 1
            continue
        attempts = int(vids[vid].get("attempts", 0))
        if attempts >= MAX_ATTEMPTS:
            vids[vid]["renamed"] = "failed"
            summary["skipped"] += 1
            print(f"  [epnum] #{n} {vid} gave up after {MAX_ATTEMPTS} "
                  f"attempts — needs a human (see factory.log history)")
            ledger.save(state)
            continue
        vids[vid]["attempts"] = attempts + 1
        ledger.save(state)               # the attempt survives a crash
        res = youtube.update_video_snippet(token, vid, sn, title, desc, state)
        if res["ok"]:
            vids[vid]["renamed"] = today
            vids[vid].pop("attempts", None)
            summary["renamed"] += 1
            print(f"  [epnum] #{n} {vid} renamed → “{title[:70]}”")
        elif res["reason"] in (youtube.QUOTA_DAY_REASONS
                               + youtube.QUOTA_ROLLING_REASONS
                               + ("rateLimitExceeded",)):
            # the server said no for quota reasons: stop spending the
            # day, do NOT count this as an attempt, defer like uploads
            hours = (youtube._hours_to_pacific_midnight()
                     if res["reason"] in youtube.QUOTA_DAY_REASONS else 2.0)
            print(f"  [epnum] rename refused ({res['reason']}) — "
                  f"deferring {hours:.1f}h; the pass resumes next cycle")
            youtube._mark_server_defer(state, res["reason"], hours)
            vids[vid]["attempts"] = attempts   # not burned by quota
            break
        elif res["reason"] == "forbidden":
            # 403 forbidden is GLOBAL (auth/scope/request shape), not
            # this video's fault — retrying the next 170 videos would
            # burn their attempt budgets against the same wall. Stop
            # the whole pass loudly without counting the attempt;
            # the same classification the playlist layer uses.
            vids[vid]["attempts"] = attempts   # not burned by a global 403
            print("  [epnum] rename FORBIDDEN (403) — a global "
                  "authorization/request problem, not this video. "
                  "Stopping the pass; check the request shape and the "
                  "token's scopes (RUNBOOK Part 3 re-consent) before "
                  "the next cycle")
            break
        else:
            summary["skipped"] += 1     # permanent-ish: retry ≤ MAX_ATTEMPTS
    ledger.save(state)
    summary["pending"] = sum(1 for r in vids.values()
                             if r.get("n") and not r.get("renamed"))
    return summary
