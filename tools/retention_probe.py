#!/usr/bin/env python3
"""Retention probe — the REAL viral signals, from the YouTube
Analytics API. Free, read-only, best-effort.

The OAuth token already carries yt-analytics.readonly (the reconsent
of 2026-10) but nothing ever used it. This tool does: per-video
averageViewPercentage (retention), estimatedMinutesWatched,
averageViewDuration, impressions and impressionsClickThroughRate for
our own recent uploads — the numbers that actually decide
distribution, which the views-only daily snapshots can never show.

Laws (same as every research tool in this factory):

  * READ-ONLY: never writes state.json, never touches the
    render/publish pipeline. Output is a research file in
    data/competitive/ that src/viral.py merges into the pattern
    feedback for the muse.
  * FREE PATH: the YouTube Analytics API has its own quota pool
    (default 50,000 units/day; a reports.query costs a handful of
    units) — completely separate from the Data API v3 10,000/day the
    factory budgets. Zero new keys, zero new services, zero cost.
  * BEST-EFFORT: any failure (no token in this environment, 401/403,
    network) prints the reason and exits 0 — a research tool may be
    silent, never loud.
  * OFFLINE REPLAY: --offline reprints the last snapshot with zero
    network (dev machines, IP-blocked sandboxes).

Usage:
    python tools/retention_probe.py                 # live (Actions)
    python tools/retention_probe.py --offline
    python tools/retention_probe.py --days 45 --max 60

Writes:
    data/competitive/retention_<date>.json
    data/competitive/retention_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "competitive"
ANALYTICS_API = "https://youtubeanalytics.googleapis.com/v2/reports"

# metrics asked in one batch; the API drops any it cannot serve for
# this filter shape — the parser maps by returned column name, so a
# missing metric is a None column, never a crash
METRICS = ("views,likes,subscribersGained,estimatedMinutesWatched,"
           "averageViewDuration,averageViewPercentage,impressions,"
           "impressionsClickThroughRate")


def _state() -> dict:
    return json.loads((ROOT / "data" / "state.json").read_text())


def _recent_videos(state: dict, days: int, max_n: int) -> list[dict]:
    """The channel's own uploads from the last N days, joined to their
    episode records (title, shape, long/short kind)."""
    cutoff = date.today() - timedelta(days=days)
    out = []
    for ep in state.get("episodes", []):
        try:
            pub = date.fromisoformat(ep.get("date", ""))
        except Exception:
            continue
        if pub < cutoff:
            continue
        ids = ep.get("ids") or {}
        if ids.get("long"):
            out.append({"id": ids["long"], "kind": "long",
                        "title": ep.get("title", ""), "ep": ep.get("n")})
        for sid in ids.get("shorts") or []:
            out.append({"id": sid, "kind": "short",
                        "title": ep.get("title", ""), "ep": ep.get("n")})
        if len(out) >= max_n:
            break
    return out


def _query(token: str, ids: list[str], start: date, end: date) -> list[dict]:
    """One reports.query for up to ~40 video ids; returns row dicts."""
    filters = "video==" + ",".join(ids)
    qs = urllib.parse.urlencode({
        "ids": "channel==MINE",
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "metrics": METRICS,
        "filters": filters,
        "maxResults": 200,
    })
    req = urllib.request.Request(
        f"{ANALYTICS_API}?{qs}",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=45) as r:
        data = json.loads(r.read().decode())
    cols = [c["name"] for c in data.get("columnHeaders", [])]
    rows = []
    for raw in data.get("rows", []):
        row = dict(zip(cols, raw))
        row["id"] = row.pop("video", None)
        rows.append(row)
    return rows


def probe(days: int = 45, max_n: int = 60) -> dict | None:
    from src.youtube import get_access_token
    try:
        token = get_access_token()
    except Exception as exc:
        print(f"[retention] no token in this environment ({exc}) — "
              f"live runs happen on Actions; nothing else to do")
        return None

    state = _state()
    vids = _recent_videos(state, days, max_n)
    if not vids:
        print("[retention] no recent uploads in the window")
        return None
    by_id = {v["id"]: v for v in vids}
    print(f"[retention] querying {len(vids)} videos "
          f"({days}d window, YouTube Analytics API)")

    rows: list[dict] = []
    for i in range(0, len(vids), 40):
        batch = [v["id"] for v in vids[i:i + 40]]
        try:
            rows.extend(_query(token, batch,
                               date.today() - timedelta(days=days),
                               date.today()))
        except Exception as exc:
            print(f"[retention] batch {i // 40} failed ({exc}) — "
                  f"continuing with what we have")
    if not rows:
        print("[retention] no rows returned (token may lack the "
              "analytics scope, or the API returned nothing)")
        return None

    from src.viral import formula_of
    videos = []
    for row in rows:
        meta = by_id.get(row.get("id"), {})
        videos.append({
            "id": row.get("id"), "kind": meta.get("kind", "?"),
            "ep": meta.get("ep"), "title": meta.get("title", ""),
            "formula": formula_of(meta.get("title", "") or "") or "PLAIN",
            "views": row.get("views"),
            "watch_minutes": row.get("estimatedMinutesWatched"),
            "avg_view_pct": round(row["averageViewPercentage"], 1)
            if row.get("averageViewPercentage") is not None else None,
            "avg_view_seconds": round(row["averageViewDuration"], 1)
            if row.get("averageViewDuration") is not None else None,
            "impressions": row.get("impressions"),
            "ctr_pct": round(row["impressionsClickThroughRate"] * 100, 2)
            if row.get("impressionsClickThroughRate") is not None else None,
        })

    def agg(items: list[dict]) -> dict:
        pcts = [v["avg_view_pct"] for v in items
                if v.get("avg_view_pct") is not None]
        return {"n": len(items),
                "avg_view_pct": round(sum(pcts) / len(pcts), 1) if pcts else None}

    longs = [v for v in videos if v["kind"] == "long"]
    shorts = [v for v in videos if v["kind"] == "short"]
    by_formula = {}
    for v in longs:
        by_formula.setdefault(v["formula"], []).append(v)
    out = {
        "date": date.today().isoformat(),
        "window_days": days,
        "videos": sorted(videos, key=lambda v: -(v.get("views") or 0)),
        "by_formula": [
            dict(name=k, **agg(g)) for k, g in
            sorted(by_formula.items(), key=lambda kv: -(kv[1][0].get("views") or 0))
        ],
        "longs": agg(longs),
        "shorts": agg(shorts),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = date.today().isoformat()
    (OUT_DIR / f"retention_{stamp}.json").write_text(json.dumps(out, indent=1))
    (OUT_DIR / "retention_latest.json").write_text(json.dumps(out, indent=1))

    # the brief (stdout — lands in the Actions log and the Issue body)
    print(f"\nRETENTION BRIEF — {len(videos)} videos, {days}d window")
    if out["longs"]["avg_view_pct"] is not None:
        print(f"  longs : avg {out['longs']['avg_view_pct']}% view duration "
              f"({out['longs']['n']} videos)")
    if out["shorts"]["avg_view_pct"] is not None:
        print(f"  shorts: avg {out['shorts']['avg_view_pct']}% view duration "
              f"({out['shorts']['n']} videos)")
    for f in out["by_formula"]:
        if f["avg_view_pct"] is not None:
            print(f"  {f['name']:13s} {f['avg_view_pct']}% avg "
                  f"({f['n']} longs)")
    tops = [v for v in videos if v.get("avg_view_pct") is not None][:5]
    for v in tops:
        print(f"    {v['kind']:5s} ep{v.get('ep')} {v['avg_view_pct']}% | "
              f"{v.get('ctr_pct')}% CTR | {v.get('views')} views | "
              f"{(v.get('title') or '')[:44]}")
    return out


def replay() -> None:
    p = OUT_DIR / "retention_latest.json"
    if not p.exists():
        print("[retention] no snapshot to replay yet")
        return
    d = json.loads(p.read_text())
    print(f"[retention] replay of {d.get('date')} "
          f"({len(d.get('videos', []))} videos)")
    for v in d.get("videos", [])[:8]:
        print(f"  {v['kind']:5s} ep{v.get('ep')} {v.get('avg_view_pct')}% | "
              f"{v.get('ctr_pct')}% CTR | {v.get('views')} views")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=45)
    ap.add_argument("--max", type=int, default=60)
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    try:
        if a.offline:
            replay()
        else:
            probe(a.days, a.max)
    except Exception as exc:                    # best-effort, never loud
        print(f"[retention] probe skipped ({exc})")
    sys.exit(0)
