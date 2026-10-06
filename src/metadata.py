"""Per-video YouTube metadata for the love-psychology channel.

The Short rules come straight from the channel owner and are FIXED:
  * every Short title  = "Subscribe for more tips like this
    #psychology #relationship #love #relationshipgoals"
    (same locked title every time; the fixed tags the owner specified
    are appended at the END of the title)
  * every Short tags   = #psychology #relationship #love #relationshipgoals
  (fixed titles are a deliberate growth strategy in this niche — the
  Shorts feed sells the hook, not the title; the identical title turns
  every Short into a subscription funnel.)

Long videos stay SEO-driven (search-first heads, rotating long-tails,
keyword-loaded first 150 description chars, chapter lists from the
script's concept structure, ~500-char tag budgets).
"""
from __future__ import annotations

from .config import cfg
from .content_data import CTA_LINE

SHORT_TAGS = ["#psychology", "#relationship", "#love", "#relationshipgoals"]
SHORT_HASHTAGS = "#psychology #relationship #love #relationshipgoals"
# Owner's rule: the SAME locked title every time, with the fixed tags
# appended at the end (84 chars — well under YouTube's 100-char limit).
SHORT_TITLE = f"{CTA_LINE.rstrip('.')} {SHORT_HASHTAGS}"

TITLE_FRAMES = [
    ("Psychology of Love", "Love Psychology Tips"),
    ("Relationship Psychology", "Love Tips That Work"),
    ("Love Psychology", "Relationship Advice"),
    ("Psychology Facts About Love", "Dating Psychology"),
    ("Relationship Tips", "Psychology of Love"),
]

TAG_POOL = [
    "psychology of love",
    "love psychology",
    "relationship psychology",
    "relationship tips",
    "love tips",
    "psychology facts",
    "relationship advice",
    "breakup advice",
    "how to get over a breakup",
    "love advice",
    "dating psychology",
    "attachment styles",
    "self love",
    "relationship goals",
    "psychology facts about love",
    "why we fall in love",
    "signs of love",
    "emotional intelligence",
    "green flags relationship",
    "red flags relationship",
    "love brain science",
    "relationship psychology facts",
]


def _fmt_ts(t: float) -> str:
    m, s = divmod(int(t), 60)
    return f"{m}:{s:02d}"


def _frame(story: dict) -> tuple[str, str]:
    """Deterministic per-episode rotation (seeded by script hash)."""
    frames = cfg().get("discovery", {}).get("title_frames") or TITLE_FRAMES
    pick = int(story["hash"][:6], 16) % len(frames)
    return frames[pick]


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit].rstrip(" |—-,·")


def long_title(story: dict) -> str:
    head, tail = _frame(story)
    n = len(story["atoms"]["concepts"])
    full = f"{head}: {story['title']} | {tail}"
    if len(full) <= 100:
        return full
    mid = f"{head}: {story['title']}"
    if len(mid) <= 100:
        return mid
    return _clip(mid, 100)


def _tag_list(story: dict) -> list[str]:
    specific = [t.lower() for t in story["atoms"]["concepts"]]
    pool = cfg().get("discovery", {}).get("tag_pool") or TAG_POOL
    out: list[str] = []
    for t in specific + list(pool):
        t = t.strip()
        if t and t not in out:
            out.append(t)
    # 2026-10-06: YouTube tightened tag validation — 454 packed chars
    # (26 tags) came back invalidTags while 436 had passed the day
    # before. Budget 350 chars / 20 tags: comfortably under both the
    # old 500-char rule and the new, tighter one; concepts are kept
    # first (episode-specific long-tails), pool tags fill the rest.
    packed: list[str] = []
    used = 0
    for t in out:
        if len(packed) >= 20:
            break
        cost = len(t) + (2 if packed else 0)
        if used + cost > 350:
            break
        packed.append(t)
        used += cost
    return packed


def long_metadata(story: dict, narration: dict) -> dict:
    vconf = cfg()["video"]
    title_s = float(vconf.get("title_card_seconds", 6))
    channel = cfg()["channel"]
    n = len(story["atoms"]["concepts"])

    # chapters: title card at 0:00, then each concept's card scene
    chapters = [f"{_fmt_ts(0)} {story['title']} — {n} psychology lessons"]
    t = title_s
    tip = 0
    for i, scene in enumerate(story["scenes"]):
        if scene["id"].startswith("tip") and scene["id"].endswith("_card"):
            tip += 1
            term = story["atoms"]["concepts"][tip - 1]
            chapters.append(f"{_fmt_ts(t)} Tip {tip}: {term}")
        t += narration["scene_durations"][i]

    desc = (
        # first ~150 chars carry the search keywords
        f"Psychology of love explained in plain words — {n} lessons on "
        f"{story['title'].lower()}. Relationship tips that actually change "
        f"how you love.\n\n"
        f"\"{story['hook']}\"\n\n"
        f"What you'll learn:\n"
        + "\n".join(f"  {i+1}. {term}" for i, term in enumerate(story["atoms"]["concepts"]))
        + "\n\n"
        f"New love psychology videos every day — attraction, attachment, "
        f"breakups, self-worth and the science behind how we love.\n\n"
        f"\U0001f9ea ABOUT {channel['display_name'].upper()}\n"
        f"Real psychology, plain language. One new video every day about "
        f"love, relationships and the mind behind them.\n\n"
        f"\U0001f916 Narration, artwork and music are AI-assisted and "
        f"reviewed before publishing — disclosed per YouTube's synthetic "
        f"media policy. Not made for kids.\n\n"
        f"#psychology #love #relationship"
    )
    return {"title": long_title(story), "description": desc[:4900],
            "tags": _tag_list(story), "chapters": chapters}


def short_metadata(story: dict, short: dict) -> dict:
    """FIXED title + FIXED tags (the owner's growth strategy)."""
    desc = (
        f"{SHORT_HASHTAGS}\n\n"
        f"New love psychology shorts every day — {story['topic_label']}.\n"
        f"The full video is on the channel.\n\n"
        f"{SHORT_HASHTAGS}"
    )
    return {"title": SHORT_TITLE, "description": desc[:4900],
            "tags": list(SHORT_TAGS)}
