"""THE VIRAL BRAIN — batch-4 (2026-11-01): score before publish,
learn after.

Free translation of three harvested skills into deterministic,
offline, zero-quota code:

  * short-form-video (hook -> retention -> loop grammar) + 
    hook-writer-sms (attention patterns) -> score_title(): the
    measurable features of a title that earns the click — the
    you-address, the curiosity opener, one power word, an emotional
    word, the question form, the length sweet spot, a formula shape —
    and the tells that LOSE it (AI-tell vocabulary, shouting caps,
    double punctuation, clickbait tricks the channel's honesty moat
    forbids).
  * youtube-seo -> formula_of(): the title-shape taxonomy, shared
    with tools/trend_intel.py (one source of truth — trend_intel
    imports it from here).
  * ab-testing (the measurement doctrine) -> build_feedback(): the
    channel learns from ITSELF. Every finished episode's long title
    joins its actual first-week view gains from the daily analytics
    snapshots already in state.json; the weekly benchmark aggregates
    which shapes / score bands earned above median and writes
    data/competitive/viral_feedback.json; the muse reads it as a
    phrasing-level PATTERN FEEDBACK block (same law as the weekly
    steer: vocabulary and rhythm only, never a new fact or claim).

LOG-ONLY at publish time (note_viral): the score never blocks or
rewrites anything the grammar built — it makes the pattern visible in
the noon report and feeds the loop that reads it back a week later.
"""
from __future__ import annotations

import json
import re
import statistics
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEEDBACK_PATH = ROOT / "data" / "competitive" / "viral_feedback.json"

# ── the title-shape taxonomy (trend_intel imports this — one source) ─
FORMULAS: list[tuple[str, str]] = [
    ("NUMBER_LIST", r"\b(top\s*\d+|\d+\s+(best|things|signs|ways|facts|reasons|mistakes|habits|rules|tips))\b"),
    ("HOW_TO", r"\bhow\s+to\b|\bstep[- ]by[- ]step\b|complete guide|\bguide\b"),
    ("VS_COMPARISON", r"\bvs\.?\b|\bversus\b|which is better"),
    ("WARNING", r"\b(avoid|mistake[s]?|stop doing|never|don'?t|red flags?|warnings?|toxic)\b"),
    ("STORY", r"\bi\s+(tried|learned|realized)\b|what happened when|my (ex|partner|crush)"),
    ("YEAR_SPECIFIC", r"\b(20[2-3]\d)\b"),
]

_POWER_WORDS = {
    "stop", "never", "always", "why", "secret", "truth", "mistake",
    "ignore", "nobody", "everyone", "actually", "quietly", "real",
    "hidden", "signs", "trap", "warning", "red", "flags", "obsessed",
    "addicted", "unloved", "lovebombing", "heal", "unlearn",
}
_EMOTION_WORDS = {
    "love", "hurt", "pain", "heal", "healing", "heart", "breakup",
    "fear", "attach", "crave", "miss", "lonely", "loneliness",
    "jealous", "obsession", "anxious", "avoidant", "heartbreak",
    "grief", "shame", "worthy", "unworthy", "boring", "chemistry",
}


def formula_of(title: str) -> str | None:
    for name, pat in FORMULAS:
        if re.search(pat, title, re.IGNORECASE):
            return name
    return None


def score_title(title: str) -> tuple[int, list[str]]:
    """Deterministic 0-100 click-craft score for one title, with the
    notes that fired (logged per episode, read by the feedback loop).

    Doctrine: this is a LENS, never a gate — the grammar pools and
    the muse keep their voice; the score makes the craft measurable
    so drift is visible in the noon report."""
    t = (title or "").strip()
    notes: list[str] = []
    s = 50
    n = len(t)

    if 30 <= n <= 60:
        s += 8; notes.append("length sweet spot")
    elif n > 70:
        s -= 10; notes.append("too long")
    elif n < 20:
        s -= 4; notes.append("very short")

    words = re.findall(r"[A-Za-z']+", t)
    low = {w.lower() for w in words}

    if low & {"you", "your", "you're"}:
        s += 8; notes.append("you-address")
    if re.match(r"^(why|how|what)\b", t, re.IGNORECASE):
        s += 6; notes.append("curiosity opener")
    if any(ch.isdigit() for ch in t):
        s += 5; notes.append("number")
    pw = sorted(low & _POWER_WORDS)
    if pw:
        s += 6; notes.append(f"power word: {pw[0]}")
    em = sorted(low & _EMOTION_WORDS)
    if em:
        s += 5; notes.append(f"emotion word: {em[0]}")
    if t.endswith("?"):
        s += 4; notes.append("question form")
    f = formula_of(t)
    if f:
        s += 4; notes.append(f"shape: {f.lower()}")

    caps = [w for w in words if len(w) >= 3 and w.isupper()]
    if len(caps) >= 2:
        s -= 6; notes.append("shouting caps")
    if re.search(r"[!?]{2,}", t):
        s -= 6; notes.append("double punctuation")
    # the honesty moat: fabricated-certainty clickbait
    if re.search(r"\bthis one (trick|tip|secret)\b", t, re.IGNORECASE):
        s -= 12; notes.append("clickbait tell")

    # AI-tell vocabulary (batch-3 layer, reused): soft penalty — a
    # title the scrubber would flag reads machine-made
    try:
        from . import ai_tells
        rep = ai_tells.audit(t)
        bad = sum(v for k, v in rep.items() if k != "total")
        if bad:
            s -= min(12, 4 * bad)
            notes.append("ai-tell vocabulary")
    except Exception:
        pass

    return max(5, min(97, s)), notes


# ── the feedback loop (our own channel's reality) ────────────────────

def _snap_view(analytics: list[dict], vid: str, d0: date, d1: date):
    """Cumulative views of vid at the first and last snapshot inside
    [d0, d1]; None when the video never appears in the window."""
    seen = [(a["date"], a.get("videos", {}).get(vid))
            for a in analytics
            if d0.isoformat() <= a.get("date", "") <= d1.isoformat()
            and vid in a.get("videos", {})]
    if not seen:
        return None
    first, last = seen[0][1] or 0, seen[-1][1] or 0
    return first, last


def first_week_views(state: dict, ep: dict, days: int = 21) -> int | None:
    """First-days view GAIN for the episode's long video, from the
    daily snapshots already in state.json (zero quota — pure math on
    data we collect anyway). 21-day window: at this channel's scale
    a 7-day window is 0-2 views (the shorts carry distribution;
    longs are still earning theirs) — three weeks gives the pattern
    room to speak."""
    try:
        vid = (ep.get("ids") or {}).get("long")
        pub = date.fromisoformat(ep.get("date", ""))
        if not vid:
            return None
        w = _snap_view(state.get("analytics", []), vid, pub,
                       pub + timedelta(days=days))
        if w is None:
            return None
        return max(0, w[1] - w[0])
    except Exception:
        return None


def build_feedback(state: dict, today: date | None = None) -> dict:
    """Aggregate which title shapes and score bands earned above the
    channel's own median first-week views. Episodes 8-45 days old
    (a full first week of data, still this season's audience).
    Writes data/competitive/viral_feedback.json and returns it."""
    today = today or date.today()
    rows = []
    for ep in state.get("episodes", []):
        try:
            pub = date.fromisoformat(ep.get("date", ""))
        except Exception:
            continue
        age = (today - pub).days
        if not (8 <= age <= 45) or ep.get("status") != "done":
            continue
        v = first_week_views(state, ep)
        if v is None:
            continue
        title = (ep.get("title") or "").strip()
        sc, _ = score_title(title)
        rows.append({"title": title, "views": v, "score": sc,
                     "formula": formula_of(title) or "PLAIN",
                     "n": ep.get("n")})

    out = {"week": today.isoformat(), "episodes": len(rows), "generated": "src/viral.py"}
    if len(rows) >= 4:
        med = statistics.median(r["views"] for r in rows)
        out["median_first_week_views"] = med

        def agg(key: str) -> list[dict]:
            groups: dict[str, list] = {}
            for r in rows:
                groups.setdefault(str(r[key]), []).append(r)
            res = []
            for name, g in groups.items():
                if len(g) < 2:
                    continue
                res.append({"name": name, "n": len(g),
                            "mean_views": round(statistics.mean(x["views"] for x in g), 1),
                            "ratio": round(statistics.mean(x["views"] for x in g) / med, 2)
                            if med else None})
            return sorted(res, key=lambda x: -(x["mean_views"] or 0))

        out["by_formula"] = agg("formula")
        bands = {"high(75+)": [], "mid(60-74)": [], "low(<60)": []}
        for r in rows:
            k = "high(75+)" if r["score"] >= 75 else ("mid(60-74)" if r["score"] >= 60 else "low(<60)")
            bands[k].append(r)
        out["by_band"] = [
            {"name": k, "n": len(g),
             "mean_views": round(statistics.mean(x["views"] for x in g), 1) if g else 0,
             "ratio": round(statistics.mean(x["views"] for x in g) / med, 2) if g and med else None}
            for k, g in bands.items() if g]
        srt = sorted(rows, key=lambda r: -r["views"])
        out["best"] = [{"title": r["title"], "views": r["views"],
                        "score": r["score"], "formula": r["formula"]}
                       for r in srt[:3]]
        out["worst"] = [{"title": r["title"], "views": r["views"],
                         "score": r["score"], "formula": r["formula"]}
                        for r in srt[-2:]]
    # merge retention intel if the probe ran (retention_probe.py)
    try:
        ret = json.loads((ROOT / "data" / "competitive" /
                          "retention_latest.json").read_text())
        if 0 <= (today - date.fromisoformat(ret.get("date", ""))).days <= 13:
            out["retention"] = ret.get("by_formula", [])
    except Exception:
        pass

    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    FEEDBACK_PATH.write_text(json.dumps(out, indent=1))
    return out


def feedback_block() -> str:
    """The muse's PATTERN FEEDBACK block — our own channel's evidence
    about which title shapes earned views. Same law as the weekly
    steer: phrasing-level only, never a new fact or claim. Stale
    (older than 13 days) / missing / unreadable -> empty string."""
    try:
        d = json.loads(FEEDBACK_PATH.read_text())
        week = date.fromisoformat(d.get("week", ""))
    except Exception:
        return ""
    if not (0 <= (date.today() - week).days <= 13):
        return ""
    if d.get("episodes", 0) < 4:
        return ""
    # SIGNAL FLOOR: below ~5 median first-window views the ratios
    # are noise (a 2-vs-1 view difference would read as 2.0x) — the
    # block stays silent and the muse flies on craft alone until
    # the channel's numbers can actually speak
    if (d.get("median_first_week_views") or 0) < 5:
        return ""
    lines = [f"PATTERN FEEDBACK (our own channel's first-week views, "
             f"{d['episodes']} recent episodes — phrasing-level only):"]
    for f in d.get("by_formula", [])[:4]:
        if f.get("ratio") is None:
            continue
        if f["ratio"] >= 1.25:
            lines.append(f"- {f['name'].lower().replace('_', ' ')} shaped titles "
                         f"earned ~{f['ratio']}x the channel median — when a draft "
                         f"naturally allows that shape, take it")
        elif f["ratio"] <= 0.75:
            lines.append(f"- {f['name'].lower().replace('_', ' ')} shaped titles "
                         f"underperformed (~{f['ratio']}x median) — prefer a "
                         f"different shape when one fits")
    for f in d.get("by_band", []):
        if f.get("ratio") and f["ratio"] >= 1.2 and f["name"].startswith("high"):
            lines.append(f"- higher craft scores correlated with views "
                         f"({f['name']} band ~{f['ratio']}x median) — lean into the "
                         f"you-address, the curiosity opener, one power word")
    for f in (d.get("retention") or [])[:3]:
        if f.get("avg_view_pct") and f.get("n", 0) >= 2:
            if (f.get("avg_view_pct") or 0) >= 55:
                lines.append(f"- {f['name'].lower().replace('_', ' ')} shaped "
                             f"videos hold viewers best ({f['avg_view_pct']:.0f}% "
                             f"average view duration) — that shape keeps earning")
            elif (f.get("avg_view_pct") or 0) <= 35:
                lines.append(f"- {f['name'].lower().replace('_', ' ')} shaped "
                             f"videos lose viewers early ({f['avg_view_pct']:.0f}% "
                             f"average view duration) — tighten that shape's openers")
    lines.append("- the feedback changes vocabulary and shape ONLY — "
                 "never add facts or claims the draft does not contain")
    return "\n".join(lines) + "\n\n" if len(lines) > 2 else ""


def note_viral(state: dict, episode_n: int, info: dict) -> None:
    """Ledger note (the note_tells pattern): the per-episode title
    score next to the tells count — pattern telemetry for the noon
    report and the weekly feedback loop. In-memory; rides the next
    ledger.save()."""
    for e in state.get("episodes", []):
        if e.get("n") == episode_n:
            e["viral"] = {"score": info.get("score"),
                          "formula": info.get("formula"),
                          "notes": (info.get("notes") or [])[:4]}
            break
