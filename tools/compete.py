#!/usr/bin/env python3
"""Competitive benchmark — us vs the niche, every week. Free forever.

The weekly companion to tools/trend_intel.py. Trend intel answers
"what is winning in the niche?"; this tool answers "who is winning,
how fast are they growing, and how do we compare?" — the numbers the
owner needs to judge whether the machine's week actually moved.

Design contract (same law as trend_intel):
  * READ-ONLY towards the factory. Never writes state.json, never
    touches the render/publish path. Output is research files in
    data/competitive/ plus a report.
  * FREE PATH ONLY: the channel's own OAuth (channels.list /
    playlistItems.list / videos.list — roughly 20 quota units per
    week against the free 10,000/day budget). Discovery of new
    competitors comes from data/trend/ snapshots that trend_intel.py
    writes (yt-dlp search, 0 quota, run from Actions first).
  * SELF-GROWING ROSTER: hand-verified seed handles in
    data/competitive/seeds.json + automatic discovery (channels that
    appear in 2+ niche trend snapshots ARE the niche).
  * OFFLINE REPLAY: --offline rebuilds the report from the last two
    snapshots with zero network (dev machines, IP-blocked sandboxes).

Usage:
    python tools/compete.py                # live weekly run (Actions)
    python tools/compete.py --offline      # replay snapshots, no network
    python tools/compete.py --max-roster 12

Files produced in data/competitive/:
    roster.json        the tracked channels (seeds + auto-discovered)
    snap_<date>.json   this week's raw pull (channel stats + uploads)
    bench_<date>.md    the us-vs-them report (also the issue body)
    steer.json         machine-readable angles for the muse layer
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.youtube import API_BASE, get_access_token  # noqa: E402
from trend_intel import classify, themes  # noqa: E402  (formula taxonomy)

ROOT = Path(__file__).resolve().parent.parent
COMP_DIR = ROOT / "data" / "competitive"
TREND_DIR = ROOT / "data" / "trend"

MAX_ROSTER = 20           # hard cap: weekly quota is ~2 + roster units
FRESH_WINDOW_DAYS = 10    # uploads younger than this get velocity math
FRESH_PER_CHANNEL = 15    # newest-first cap (spammy factories stay bounded)
UPLOADS_SAMPLE = 50       # playlistItems per channel (one 1-unit call)
MISS_LIMIT = 3            # consecutive misses before a channel is dropped
TREND_KEEP = 12           # trend snapshots retained (pruned here)
SNAP_KEEP = 26            # weekly snapshots retained (~6 months)
BENCH_KEEP = 26           # weekly reports retained


# ── small helpers ───────────────────────────────────────────────────

def _get(token: str, url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _iso_date(s: str) -> date | None:
    try:
        return date.fromisoformat((s or "")[:10])
    except ValueError:
        return None


def _age_days(published_at: str) -> float | None:
    if not published_at:
        return None
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max((datetime.now(timezone.utc) - dt).total_seconds() / 86400.0, 0.5)


def _dur_s(iso: str) -> int:
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def _fmt(n: int | float | None) -> str:
    if n is None:
        return "-"
    n = int(n)
    return f"{n:,}" if abs(n) < 10_000_000 else f"{n / 1_000_000:.1f}M"


def _fmt_delta(n: int | None) -> str:
    if n is None:
        return "-"
    return f"+{n:,}" if n >= 0 else f"{n:,}"


# ── roster: seeds + trend auto-discovery ────────────────────────────

def roster_load() -> dict:
    f = COMP_DIR / "roster.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {"channels": {}}


def roster_save(roster: dict) -> None:
    COMP_DIR.mkdir(parents=True, exist_ok=True)
    (COMP_DIR / "roster.json").write_text(json.dumps(roster, indent=1))


def resolve_seeds(token: str, roster: dict) -> list[str]:
    """Add seed handles (data/competitive/seeds.json) to the roster.

    Resolves @handle -> exact channel id via channels.list?forHandle
    (1 unit each, once per channel — the id is then cached forever).
    Returns human-readable notes for the log."""
    notes = []
    f = COMP_DIR / "seeds.json"
    if not f.exists():
        return notes
    try:
        seeds = json.loads(f.read_text())
    except Exception as e:
        return [f"[roster] seeds.json unreadable: {e}"]
    for s in seeds:
        handle = (s.get("handle") or "").lstrip("@")
        if not handle:
            continue
        if any(c.get("handle", "").lstrip("@").lower() == handle.lower()
               for c in roster["channels"].values()):
            continue  # already resolved
        got = None
        for param in (f"forHandle=@{handle}", f"forUsername={handle}"):
            try:
                data = _get(token, f"{API_BASE}/channels?part=snippet"
                                   f"&maxResults=1&{param}")
                items = data.get("items", [])
                if items:
                    got = items[0]
                    break
            except Exception:
                continue
        if not got:
            notes.append(f"[roster] seed @{handle} did not resolve — skipped")
            continue
        cid = got["id"]
        title = got.get("snippet", {}).get("title", handle)
        if cid in roster["channels"]:
            roster["channels"][cid]["handle"] = f"@{handle}"
            notes.append(f"[roster] seed @{handle} already tracked ({title})")
            continue
        roster["channels"][cid] = {
            "title": title, "handle": f"@{handle}", "source": "seed",
            "added": date.today().isoformat(), "appearances": 0, "misses": 0,
        }
        notes.append(f"[roster] seed @{handle} -> {cid} ({title})")
    return notes


def discover_from_trends(roster: dict, our_id: str,
                         max_roster: int = MAX_ROSTER) -> list[str]:
    """Channels appearing in 2+ niche trend snapshots join the roster.

    trend_intel.py writes data/trend/trend_*.json from yt-dlp niche
    search (0 quota). A channel that keeps surfacing across weeks of
    niche queries IS the niche — that is the whole discovery rule.
    Also prunes old trend snapshots and stale roster entries."""
    notes = []
    snaps = sorted(TREND_DIR.glob("trend_*.json"))
    for old in snaps[:-TREND_KEEP]:
        try:
            old.unlink()
        except Exception:
            pass
    counts: dict[str, int] = {}
    names: dict[str, str] = {}
    for sf in snaps[-8:]:
        try:
            data = json.loads(sf.read_text())
        except Exception:
            continue
        seen: set[str] = set()
        for it in data.get("items", []):
            cid = it.get("channel_id") or ""
            if not cid or cid in seen or cid == our_id:
                continue
            seen.add(cid)
            counts[cid] = counts.get(cid, 0) + 1
            names[cid] = it.get("channel") or names.get(cid, "")
    for cid, n in counts.items():
        if n < 2 or cid in roster["channels"]:
            continue
        roster["channels"][cid] = {
            "title": names.get(cid, cid), "handle": "",
            "source": "trend", "added": date.today().isoformat(),
            "appearances": n, "misses": 0,
        }
        notes.append(f"[roster] discovered {names.get(cid, cid)} "
                     f"({cid}) in {n} trend snapshots")
    # cap: seeds stay, trend channels compete by appearances
    trend_chs = {c: v for c, v in roster["channels"].items()
                 if v.get("source") == "trend"}
    overflow = len(roster["channels"]) - max_roster
    if overflow > 0 and trend_chs:
        for cid, _ in sorted(trend_chs.items(),
                             key=lambda kv: kv[1].get("appearances", 0)):
            if overflow <= 0:
                break
            roster["channels"].pop(cid, None)
            notes.append(f"[roster] roster full — dropped {cid} "
                         "(lowest trend appearances)")
            overflow -= 1
    return notes


# ── the weekly pull (live) ──────────────────────────────────────────

def _channel_row(ch: dict) -> dict:
    st = ch.get("statistics", {})
    cd = ch.get("contentDetails", {})
    sn = ch.get("snippet", {})
    return {
        "title": sn.get("title", ""),
        "handle": "@" + sn.get("customUrl", "").lstrip("@") if sn.get("customUrl") else "",
        "subs": int(st.get("subscriberCount") or 0),
        "views": int(st.get("viewCount") or 0),
        "video_count": int(st.get("videoCount") or 0),
        "uploads_playlist": cd.get("relatedPlaylists", {}).get("uploads", ""),
    }


def pull(token: str, roster: dict) -> tuple[dict, int]:
    """One week of ground truth. Returns (snapshot, quota_units)."""
    units = 0
    snap: dict = {"date": date.today().isoformat(),
                  "ts": datetime.now(timezone.utc).isoformat(),
                  "them": {}, "us": None}

    # us — channels.list mine=true (subs/views/videoCount + our id)
    me = _get(token, f"{API_BASE}/channels?part=snippet,statistics"
                     f"&mine=true").get("items", [])
    units += 1
    our_id = ""
    if me:
        our_id = me[0]["id"]
        snap["us"] = _channel_row(me[0])
        snap["us"]["id"] = our_id
    snap["our_id"] = our_id

    # them — one batched channels.list for the whole roster
    ids = [cid for cid in roster["channels"] if cid != our_id]
    missing: list[str] = []
    if ids:
        data = _get(token, f"{API_BASE}/channels?part=snippet,statistics,"
                           f"contentDetails&id={','.join(ids)}")
        units += 1
        found = {}
        for ch in data.get("items", []):
            found[ch["id"]] = _channel_row(ch)
        for cid in ids:
            if cid in found:
                snap["them"][cid] = found[cid]
                roster["channels"][cid]["misses"] = 0
            else:
                missing.append(cid)
    for cid in missing:  # deleted / suspended: count the miss, keep history
        m = roster["channels"][cid].get("misses", 0) + 1
        roster["channels"][cid]["misses"] = m
        snap["them"][cid] = dict(roster["channels"][cid])
        snap["them"][cid]["missing"] = True
        snap["them"][cid]["recent"] = []
        if m >= MISS_LIMIT:
            dropped = roster["channels"].pop(cid, None)
            if dropped:
                print(f"[roster] {cid} ({dropped.get('title', '?')}) missing "
                      f"{MISS_LIMIT} weeks — dropped")

    # their recent uploads — playlistItems per channel (1 unit each)
    fresh_ids: list[str] = []
    for cid, row in snap["them"].items():
        pl = row.get("uploads_playlist", "")
        if not pl or row.get("missing"):
            continue
        try:
            data = _get(token, f"{API_BASE}/playlistItems?part=contentDetails"
                               f"&playlistId={pl}&maxResults={UPLOADS_SAMPLE}")
            units += 1
        except Exception as e:
            print(f"[pull] uploads of {row.get('title', cid)} failed: {e}")
            row["recent"] = []
            continue
        row["recent"] = []
        for it in data.get("items", []):
            cd = it.get("contentDetails", {})
            vid, pub = cd.get("videoId", ""), cd.get("videoPublishedAt", "")
            age = _age_days(pub)
            if not vid or age is None:
                continue
            row["recent"].append({"id": vid, "title": "", "published_at": pub})
            if age <= FRESH_WINDOW_DAYS and len(fresh_ids) < 800:
                fresh_ids.append(vid)

    # exact stats for fresh uploads — videos.list batched (1 unit / 50)
    seen: set[str] = set()
    fresh_ids = [v for v in fresh_ids if not (v in seen or seen.add(v))]
    stats: dict[str, dict] = {}
    for i in range(0, len(fresh_ids), 50):
        chunk = fresh_ids[i:i + 50]
        try:
            data = _get(token, f"{API_BASE}/videos?part=snippet,statistics"
                               f",contentDetails&id={','.join(chunk)}")
            units += 1
        except Exception as e:
            print(f"[pull] videos batch {i // 50} failed: {e}")
            continue
        for v in data.get("items", []):
            stats[v["id"]] = {
                "title": v.get("snippet", {}).get("title", ""),
                "views": int(v.get("statistics", {}).get("viewCount") or 0),
                "duration_s": _dur_s(v.get("contentDetails", {})
                                     .get("duration", "")),
            }
    for cid, row in snap["them"].items():
        for u in row["recent"]:
            st = stats.get(u["id"])
            if st:
                u.update(st)
            u["age_days"] = round(_age_days(u["published_at"]) or 0.0, 1)
            u["velocity"] = round(
                (u.get("views", 0) or 0) / max(u["age_days"], 0.5), 1)
            u["formula"] = classify(u.get("title", ""))
    return snap, units


# ── analysis (works offline from snapshots) ─────────────────────────

def load_state() -> dict:
    f = ROOT / "data" / "state.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def _our_week(state: dict, start: date, end: date) -> dict:
    """Our numbers from the factory's own daily analytics history.
    Read-only: state.json is never written by this tool."""
    out: dict = {"views_gained": None, "uploads": 0, "fresh": [],
                 "total_views": None, "snapshot_date": None}
    ana = state.get("analytics", [])
    if ana:
        latest = ana[-1]
        out["total_views"] = latest.get("total_views")
        out["snapshot_date"] = latest.get("date")
        then = None
        for a in ana:                      # first snapshot at/after start
            if _iso_date(a.get("date", "")) and a["date"] >= start.isoformat():
                then = a
                break
        if then and then is not latest:
            out["views_gained"] = latest.get("total_views", 0) - \
                then.get("total_views", 0)
    vids_now = (ana[-1].get("videos", {}) if ana else {})
    for e in state.get("episodes", []):
        d = _iso_date(e.get("date", ""))
        if not d or not (start <= d <= end):
            continue
        out["uploads"] += 1
        for vid in ([e.get("ids", {}).get("long")] +
                    list(e.get("ids", {}).get("shorts", []))):
            if not vid:
                continue
            age = max((end - d).days, 1)
            v = vids_now.get(vid)
            out["fresh"].append({
                "id": vid, "title": e.get("title", ""), "age_days": age,
                "views": v if v is not None else 0,
                "velocity": round((v or 0) / max(age, 1), 1),
            })
    return out


def analyze(snap: dict, prev: dict | None, state: dict) -> dict:
    end = _iso_date(snap.get("date", "")) or date.today()
    start = _iso_date(prev.get("date", "")) if prev else None
    if not start or start >= end:
        start = date.fromordinal(end.toordinal() - 7)
    a: dict = {"start": start, "end": end, "first": prev is None,
               "us": snap.get("us") or {}, "rows": [], "fresh": []}
    a["our_week"] = _our_week(state, start, end)

    us_prev = (prev or {}).get("us") or {}
    a["us_deltas"] = {
        "subs": (snap["us"].get("subs") - us_prev.get("subs"))
        if snap.get("us") and us_prev.get("subs") is not None else None,
        "views": (snap["us"].get("views") - us_prev.get("views"))
        if snap.get("us") and us_prev.get("views") is not None else None,
    }
    for cid, row in snap.get("them", {}).items():
        p = ((prev or {}).get("them", {}) or {}).get(cid)
        subs = row.get("subs", 0)
        hidden = subs == 0
        uploads = [u for u in row.get("recent", [])
                   if _iso_date(u.get("published_at", ""))
                   and start.isoformat() <= u["published_at"][:10]
                   <= end.isoformat()]
        fresh = [u for u in row.get("recent", [])
                 if (u.get("age_days") or 99) <= FRESH_WINDOW_DAYS
                 and u.get("views")]
        for u in fresh:  # title-derived -> recompute, never trust storage
            u["formula"] = classify(u.get("title", ""))
        a["rows"].append({
            "id": cid, "title": row.get("title", cid),
            "handle": row.get("handle", ""), "missing": row.get("missing"),
            "subs": None if hidden else subs,
            "subs_gained": (subs - p.get("subs", 0))
            if p and not hidden and p.get("subs") else None,
            "views_gained": (row.get("views", 0) - p.get("views", 0))
            if p and p.get("views") else None,
            "uploads": len(uploads), "fresh": fresh,
        })
        a["fresh"] += [dict(u, channel=row.get("title", cid)) for u in fresh]
    a["fresh"].sort(key=lambda u: -(u.get("velocity") or 0))
    niche_v = [u["velocity"] for u in a["fresh"] if u.get("velocity")]
    ours_v = [u["velocity"] for u in a["our_week"]["fresh"]
              if u.get("velocity")]
    a["niche_velocity"] = round(sum(niche_v) / len(niche_v), 1) if niche_v else None
    a["our_velocity"] = round(sum(ours_v) / len(ours_v), 1) if ours_v else None
    return a


# ── outputs: report + steer ─────────────────────────────────────────

def _angles(a: dict) -> list[str]:
    th = themes([{"title": u.get("title", "")} for u in a["fresh"]])
    words = [w for w, _ in th] or ["love", "attachment"]
    counts: dict[str, int] = {}
    for u in a["fresh"]:
        counts[u.get("formula", "PLAIN")] = counts.get(u.get("formula",
                                                 "PLAIN"), 0) + 1
    top = max(counts.items(), key=lambda kv: kv[1])[0] if counts else "PLAIN"
    w = words[0]
    return [
        f"{w.capitalize()} — the {top.lower().replace('_', ' ')} angle "
        "(winning formula x hottest theme this week)",
        f"What nobody tells you about {w}",
        f"{min(9, max(5, 7))} signs of {w} everyone misses",
    ]


def report(a: dict, quota_units: int | None) -> str:
    us, uw = a["us"], a["our_week"]
    L = [f"# Weekly benchmark — week of {a['start']} -> {a['end']}",
         f"roster: {len(a['rows'])} channels | their fresh uploads "
         f"analyzed: {len(a['fresh'])}"
         + (f" | quota spent: ~{quota_units} units" if quota_units else " | "
            "offline replay (no network)") + (" | FIRST BASELINE WEEK — "
            "deltas arrive next week" if a["first"] else ""),
         ""]

    # 1. league table
    L += ["## 1. The league — 7-day growth", "",
          "| Channel | Subs | Subs 7d | Views 7d | Uploads 7d |",
          "|---|---|---|---|---|"]
    our_row = (f"| **{us.get('title', 'US')} (us)** | {_fmt(us.get('subs'))} | "
               f"{_fmt_delta(a['us_deltas']['subs'])} | "
               f"{_fmt_delta(uw.get('views_gained'))} | {uw.get('uploads', 0)} |")
    L.append(our_row)
    for r in sorted(a["rows"], key=lambda r: -(r["views_gained"]
                                                or r["subs"] or 0)):
        tag = " (missing)" if r["missing"] else ""
        L.append(f"| {r['title'][:26]}{tag} | {_fmt(r['subs'])} | "
                 f"{_fmt_delta(r['subs_gained'])} | "
                 f"{_fmt_delta(r['views_gained'])} | {r['uploads']} |")

    # 2. steal list
    L += ["", "## 2. The steal list — their best new videos (views/day)",
          "", "| Title | Channel | Age | Views | V/day | Formula |",
          "|---|---|---|---|---|---|"]
    for u in a["fresh"][:10]:
        L.append(f"| {u.get('title', '')[:44]} | {u['channel'][:16]} | "
                 f"{u.get('age_days', '?')}d | {_fmt(u.get('views'))} | "
                 f"{_fmt(u.get('velocity'))} | {u.get('formula', '-')} |")

    # 3. what the niche shipped
    counts: dict[str, int] = {}
    shorts_n = 0
    for u in a["fresh"]:
        counts[u.get("formula", "PLAIN")] = counts.get(u.get("formula",
                                                     "PLAIN"), 0) + 1
        if (u.get("duration_s") or 999) <= 65:
            shorts_n += 1
    L += ["", "## 3. What the niche shipped this week", ""]
    if counts:
        total_f = sum(counts.values())
        mix = ", ".join(f"{k} {v} ({v * 100 // total_f}%)"
                        for k, v in sorted(counts.items(),
                                           key=lambda kv: -kv[1]))
        L.append(f"- formula mix: {mix}")
        th = themes([{"title": u.get("title", "")} for u in a["fresh"]])
        L.append("- hot theme words: " + ", ".join(w for w, _ in th))
        L.append(f"- shorts share: {shorts_n}/{total_f} "
                 f"({shorts_n * 100 // max(total_f, 1)}%) of fresh uploads "
                 f"under 65 s")
    else:
        L.append("- no fresh niche uploads captured this week")
    cad = [r["uploads"] for r in a["rows"] if not r["missing"]]
    if cad:
        avg = sum(cad) / len(cad)
        L.append(f"- niche cadence: {avg:.0f} uploads/channel/week vs our "
                 f"{uw.get('uploads', 0)} (5/day machine = 35/week)")

    # 4. us vs the field
    L += ["", "## 4. Us vs the field", ""]
    nv, ov = a["niche_velocity"], a["our_velocity"]
    if ov is not None and nv:
        ratio = ov / nv if nv else 0
        pct = "<1%" if 0 < ratio < 0.01 else f"{ratio:.0%}"
        L.append(f"- our fresh uploads average **{ov} views/day**; the niche "
                 f"fresh average is {nv} -> we run at **{pct} of "
                 f"niche pace**")
    elif ov is not None:
        L.append(f"- our fresh uploads average {ov} views/day (no niche "
                 "velocity captured this week)")
    else:
        L.append("- no fresh uploads on our side this window")
    if uw.get("views_gained") is not None:
        L.append(f"- channel views gained this week: "
                 f"{_fmt_delta(uw['views_gained'])} "
                 f"(total {_fmt(uw.get('total_views'))} as of "
                 f"{uw.get('snapshot_date')})")

    # 5. angles
    L += ["", "## 5. Recommended angles for next week", ""]
    L += [f"{i}. {ang}" for i, ang in enumerate(_angles(a), 1)]
    L += ["", "Topics/titles stay in the owner's lock zone — these angles "
          "reach the scripts through data/competitive/steer.json (the muse "
          "layer's weekly steer, vocabulary-level only)."]
    return "\n".join(L)


def steer_write(a: dict) -> None:
    counts: dict[str, int] = {}
    for u in a["fresh"]:
        counts[u.get("formula", "PLAIN")] = counts.get(u.get("formula",
                                                     "PLAIN"), 0) + 1
    hot = sorted(counts.items(), key=lambda kv: -kv[1])[:3]
    th = themes([{"title": u.get("title", "")} for u in a["fresh"]])
    steer = {
        "week": a["end"].isoformat(),
        "generated": datetime.now(timezone.utc).isoformat(),
        "hot_formulas": [
            {"name": k, "videos": v,
             "example": next((u.get("title", "") for u in a["fresh"]
                              if u.get("formula") == k), "")}
            for k, v in hot],
        "hot_themes": [w for w, _ in th],
        "recommended_angles": _angles(a),
        "niche_velocity": a["niche_velocity"],
        "our_velocity": a["our_velocity"],
    }
    COMP_DIR.mkdir(parents=True, exist_ok=True)
    (COMP_DIR / "steer.json").write_text(json.dumps(steer, indent=1))


# ── snapshots on disk ───────────────────────────────────────────────

def _snaps() -> list[Path]:
    return sorted(COMP_DIR.glob("snap_*.json"))


def prune_outputs() -> None:
    for old in _snaps()[:-SNAP_KEEP]:
        old.unlink(missing_ok=True)
    for old in sorted(COMP_DIR.glob("bench_*.md"))[:-BENCH_KEEP]:
        old.unlink(missing_ok=True)


# ── main ────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="Weekly us-vs-niche benchmark")
    ap.add_argument("--offline", action="store_true",
                    help="replay the last two snapshots, no network")
    ap.add_argument("--max-roster", type=int, default=MAX_ROSTER,
                    help=f"roster cap (default {MAX_ROSTER})")
    args = ap.parse_args()

    state = load_state()

    if args.offline:
        snaps = _snaps()
        if not snaps:
            sys.exit("no snapshot to replay — run live once (Actions) "
                     "or synthesize test data")
        snap = json.loads(snaps[-1].read_text())
        prev = json.loads(snaps[-2].read_text()) if len(snaps) > 1 else None
        if prev and prev.get("date") == snap.get("date"):
            prev = None
        print(f"[offline] replaying {snaps[-1].name}"
              + (f" vs {snaps[-2].name}" if prev else " (baseline)"))
        a = analyze(snap, prev, state)
        quota = None
    else:
        try:
            token = get_access_token()
        except Exception as e:
            sys.exit(f"OAuth unavailable ({e}) — live runs belong in "
                     "Actions; here use --offline")
        roster = roster_load()
        for note in resolve_seeds(token, roster):
            print(note)
        our_id = ""
        me = _get(token, f"{API_BASE}/channels?part=snippet&mine=true"
                         ).get("items", [])
        if me:
            our_id = me[0]["id"]
        for note in discover_from_trends(roster, our_id,
                                         args.max_roster):
            print(note)
        snap, quota = pull(token, roster)
        roster_save(roster)
        COMP_DIR.mkdir(parents=True, exist_ok=True)
        (COMP_DIR / f"snap_{snap['date']}.json").write_text(
            json.dumps(snap, indent=1))
        snaps = _snaps()
        prev = None
        for s in reversed(snaps[:-1]):
            d = json.loads(s.read_text()).get("date")
            if d != snap["date"]:
                prev = json.loads(s.read_text())
                break
        a = analyze(snap, prev, state)

    bench = report(a, quota)
    COMP_DIR.mkdir(parents=True, exist_ok=True)
    bench_file = COMP_DIR / f"bench_{a['end']}.md"
    bench_file.write_text(bench)
    steer_write(a)
    (COMP_DIR / "bench_issue_body.md").write_text(
        bench + "\n\n---\n- auto-filed by the weekly benchmark workflow"
        "\n- closes last week's benchmark issue when the new one opens")
    prune_outputs()
    print(bench)
    print(f"\n[bench]  {bench_file.relative_to(ROOT)}")
    print(f"[steer]  {(COMP_DIR / 'steer.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
