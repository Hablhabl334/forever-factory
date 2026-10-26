#!/usr/bin/env python3
"""Trend intelligence — what is winning in the niche right now. Free.

Translation of two cloned skills (scraping-youtube-trending-videos +
tracking-youtube-trending-topics-by-niche, originally Apify-actor-based)
onto the factory's own data path: yt-dlp search discovery (0 quota) +
OAuth videos.list enrichment (1 unit per 50 videos). No Apify, no new
API key, nothing paid. Methodology (title-formula taxonomy, momentum
scoring, trend brief) is taken verbatim from the skills.

    python tools/trend_intel.py                     # niche scan (default queries)
    python tools/trend_intel.py --query "green flags relationship"
    python tools/trend_intel.py --shorts-only       # durations under 65 s
    python tools/trend_intel.py --chart --region EG # trending chart (pure OAuth)
    python tools/trend_intel.py --offline           # replay last snapshot

Writes data/trend/trend_<ts>.json (snapshot) and prints a trend brief:
formula table, top videos by momentum, themes, recommended titles.
Additive research tool — never touches the render/publish pipeline.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, ".")
from src.youtube import API_BASE, get_access_token  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SNAP_DIR = ROOT / "data" / "trend"

# Niche defaults mirror channel.yaml niche: love-psychology
DEFAULT_QUERIES = [
    "psychology of love",
    "relationship psychology",
    "love facts",
]
MIN_VIEWS = 5000          # skill edge case: small niche -> lower to 10k->5k floor here
SHORT_MAX_SECONDS = 65

FORMULAS = [  # (name, pattern) — first match wins, order = priority
    ("NUMBER_LIST", r"\b(top\s*\d+|\d+\s+(best|things|signs|ways|facts|reasons|mistakes|habits|rules|tips))\b"),
    ("HOW_TO", r"\bhow\s+to\b|\bstep[- ]by[- ]step\b|complete guide|\bguide\b"),
    ("VS_COMPARISON", r"\bvs\.?\b|\bversus\b|which is better"),
    ("WARNING", r"\b(avoid|mistake[s]?|stop doing|never|don'?t|red flags?|warnings?|toxic)\b"),
    ("STORY", r"\bi\s+(tried|learned|realized)\b|what happened when|my (ex|partner|crush)"),
    ("YEAR_SPECIFIC", r"\b(20[2-3]\d)\b"),
]
STOPWORDS = set("""a an the of in on for to and or but is are was were be been
this that these those you your my me i we they it its his her their with without
why how what when who do does did can will would should if not no yes best top
new video shorts short subscribe like comment watch now get got know from at as
about more most less than then them there here one two three four five has have
had he she just so very really ever never always things thing way ways signs sign
""".split())


def classify(title: str) -> str:
    t = title.lower()
    for name, pat in FORMULAS:
        if re.search(pat, t):
            return name
    return "PLAIN"


def discover(query: str, n: int, shorts_only: bool) -> list[dict]:
    """yt-dlp flat search — 0 quota. Returns raw candidates."""
    url = f"ytsearch{n}:{query}"
    try:
        out = subprocess.run(
            ["yt-dlp", "--flat-playlist", "-j", url,
             "--extractor-args", "youtube:lang=en", "--no-warnings"],
            capture_output=True, text=True, timeout=180, check=True).stdout
    except FileNotFoundError:
        sys.exit("yt-dlp not installed (pip install yt-dlp) — or use --chart "
                 "(pure OAuth) / --offline")
    except subprocess.CalledProcessError as e:
        sys.exit(f"yt-dlp failed (IP-blocked here?): {e.stderr[:300]}")
    items = []
    for line in out.splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("_type") not in (None, "url"):
            continue
        vid = d.get("id", "")
        if not vid or d.get("live_status") == "is_live":
            continue
        dur = d.get("duration") or 0
        if shorts_only and dur and dur >= SHORT_MAX_SECONDS:
            continue
        items.append({
            "id": vid, "title": d.get("title") or "",
            "channel": d.get("channel") or d.get("uploader") or "",
            "channel_id": d.get("channel_id") or "",  # roster fuel for tools/compete.py
            "duration": dur,
            "views_flat": d.get("view_count") or 0,
            "query": query,
        })
    return items


def enrich_oauth(items: list[dict]) -> list[dict]:
    """videos.list batched — 1 quota unit per 50 ids. Exact stats + age."""
    try:
        token = get_access_token()
    except Exception as e:  # no creds in this context — momentum-only mode
        print(f"[enrich] OAuth unavailable ({e}); scoring on flat data only")
        return items
    by_id = {it["id"]: it for it in items}
    for i in range(0, len(items), 50):
        chunk = items[i:i + 50]
        ids = ",".join(it["id"] for it in chunk)
        req = urllib.request.Request(
            f"{API_BASE}/videos?part=snippet,statistics&id={ids}",
            headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                for v in json.loads(resp.read()).get("items", []):
                    st, sn = v.get("statistics", {}), v.get("snippet", {})
                    tgt = by_id.get(v["id"])
                    if not tgt:
                        continue
                    tgt["views"] = int(st.get("viewCount") or 0)
                    tgt["likes"] = int(st.get("likeCount") or 0)
                    tgt["comments"] = int(st.get("commentCount") or 0)
                    tgt["published_at"] = sn.get("publishedAt", "")
        except Exception as e:
            print(f"[enrich] batch {i // 50} failed: {e}")
    return items


def trending_chart(region: str, category: str | None) -> list[dict]:
    """chart=mostPopular — the trending feed itself. Pure OAuth, 1 unit."""
    token = get_access_token()
    params = f"part=snippet,statistics,contentDetails&chart=mostPopular&regionCode={region}&maxResults=50"
    if category:
        params += f"&videoCategoryId={category}"
    req = urllib.request.Request(f"{API_BASE}/videos?{params}",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        items = json.loads(resp.read()).get("items", [])
    out = []
    for v in items:
        st, sn = v.get("statistics", {}), v.get("snippet", {})
        dur = v.get("contentDetails", {}).get("duration", "")
        out.append({
            "id": v["id"], "title": sn.get("title", ""),
            "channel": sn.get("channelTitle", ""),
            "channel_id": sn.get("channelId", ""),
            "views": int(st.get("viewCount") or 0),
            "likes": int(st.get("likeCount") or 0),
            "comments": int(st.get("commentCount") or 0),
            "published_at": sn.get("publishedAt", ""),
            "duration": dur, "query": f"chart:{region}",
        })
    return out


def _age_days(published_at: str) -> float | None:
    if not published_at:
        return None
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max((datetime.now(timezone.utc) - dt).total_seconds() / 86400.0, 0.5)


def score(items: list[dict]) -> list[dict]:
    """Skill formulas verbatim: momentum = views/day; trend_score =
    0.40 momentum + 0.30 like-rate + 0.30 comment-rate (renormalized
    when likes/comments are absent)."""
    for it in items:
        it["formula"] = classify(it["title"])
        views = it.get("views") or it.get("views_flat") or 0
        it["views"] = views
        days = _age_days(it.get("published_at", ""))
        it["age_days"] = round(days, 1) if days else None
        it["momentum"] = round(views / days, 1) if days else None
        m = min((it["momentum"] or 0) / 10000.0, 1.0)
        lr = (it["likes"] / views * 100) if views and "likes" in it else None
        cr = (it["comments"] / views * 100) if views and "comments" in it else None
        it["like_rate"], it["comment_rate"] = lr, cr
        if lr is not None and cr is not None:
            it["trend_score"] = round(
                m * 0.40
                + min((lr / 4.0), 1.0) * 0.30
                + min((cr / 0.3), 1.0) * 0.30, 3)
        else:
            it["trend_score"] = round(m, 3)
    return items


def themes(items: list[dict], k: int = 8) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for it in items:
        for w in re.findall(r"[a-z']{4,}", it["title"].lower()):
            if w in STOPWORDS:
                continue
            counts[w] = counts.get(w, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])[:k]


def brief(items: list[dict], source: str) -> str:
    scored = [i for i in items if i.get("views", 0) >= MIN_VIEWS] or items
    by_mom = sorted((i for i in scored if i.get("momentum")),
                    key=lambda i: -i["momentum"])
    lines = [f"# Trend brief — {source}",
             f"videos analyzed: {len(items)} | above {MIN_VIEWS} views: "
             f"{len(scored)} | {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", ""]
    # Formula table (by avg views)
    lines += ["## Title formulas (by avg views)", "| Formula | # | Avg views | Avg like% | Best example |",
              "|---|---|---|---|---|"]
    groups: dict[str, list[dict]] = {}
    for it in scored:
        groups.setdefault(it["formula"], []).append(it)
    for name, grp in sorted(groups.items(), key=lambda kv: -sum(i["views"] for i in kv[1])):
        avg_v = sum(i["views"] for i in grp) // max(len(grp), 1)
        rates = [i["like_rate"] for i in grp if i.get("like_rate") is not None]
        avg_lr = f"{sum(rates) / len(rates):.1f}" if rates else "—"
        best = max(grp, key=lambda i: i["views"])
        lines.append(f"| {name} | {len(grp)} | {avg_v:,} | {avg_lr} | "
                     f"{best['title'][:48]} |")
    # Top videos by momentum
    lines += ["", "## Top videos by momentum (views/day)",
              "| Title | Views | Mom | Like% | Score | Ch |", "|---|---|---|---|---|---|"]
    for it in by_mom[:15]:
        lr = f"{it['like_rate']:.1f}" if it.get("like_rate") is not None else "—"
        lines.append(f"| {it['title'][:44]} | {it['views']:,} | "
                     f"{it['momentum']:,.0f} | {lr} | {it['trend_score']} | "
                     f"{it.get('channel', '')[:14]} |")
    # Themes + recommendations
    th = themes(scored)
    lines += ["", "## Trending theme words: " + ", ".join(w for w, _ in th)]
    if by_mom:
        top_formula = max(groups.items(), key=lambda kv: len(kv[1]))[0] if groups else "PLAIN"
        w1, w2 = (th[0][0] if th else "love"), (th[1][0] if len(th) > 1 else "psychology")
        lines += ["## Recommended angles (winning formula + hot theme)",
                  f"1. \"{w1.capitalize()} {w2} — the {top_formula.lower().replace('_', ' ')} angle\"",
                  f"2. \"What nobody tells you about {w1}\"",
                  f"3. \"{min(9, max(5, 7))} signs of {w1} everyone misses\""]
    return "\n".join(lines)


def latest_snapshot() -> Path | None:
    if not SNAP_DIR.exists():
        return None
    snaps = sorted(SNAP_DIR.glob("trend_*.json"))
    return snaps[-1] if snaps else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--query", action="append", help="niche search query (repeatable)")
    ap.add_argument("--n", type=int, default=25, help="results per query (default 25)")
    ap.add_argument("--shorts-only", action="store_true", help="duration under 65 s")
    ap.add_argument("--chart", action="store_true", help="trending chart instead of niche search")
    ap.add_argument("--region", default="EG", help="region for --chart (default EG)")
    ap.add_argument("--category", help="optional categoryId for --chart (10=music, 20=gaming)")
    ap.add_argument("--offline", action="store_true", help="replay latest snapshot")
    args = ap.parse_args()

    if args.offline:
        snap = latest_snapshot()
        if not snap:
            sys.exit("no snapshot to replay — run online once (Actions or trusted IP)")
        data = json.loads(snap.read_text())
        print(f"[offline] replaying {snap.name}")
        print(brief(score(data["items"]), data["source"]))
        return 0

    if args.chart:
        source, items = f"chart:{args.region}", trending_chart(args.region, args.category)
    else:
        queries = args.query or DEFAULT_QUERIES
        source = "niche:" + " | ".join(queries)
        items = []
        for q in queries:
            found = discover(q, args.n, args.shorts_only)
            print(f"[discover] {q}: {len(found)} results")
            items += found
        seen, uniq = set(), []
        for it in items:  # dedupe across queries
            if it["id"] not in seen:
                seen.add(it["id"])
                uniq.append(it)
        items = enrich_oauth(uniq)

    if not items:
        sys.exit("nothing collected (YouTube IP-blocked here? try --chart, "
                 "--offline, or run from Actions)")

    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    snap = SNAP_DIR / f"trend_{datetime.now():%Y%m%d_%H%M}.json"
    snap.write_text(json.dumps({"source": source, "ts": datetime.now(timezone.utc).isoformat(),
                                "items": items}, indent=1))
    print(brief(score(items), source))
    print(f"\n[snapshot] {snap.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
