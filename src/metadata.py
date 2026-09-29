"""Per-video YouTube metadata — built for SEARCH, not just branding.

Two hard lessons baked into this module:

1. Nobody searches for an invented story title. "The Wind Flute of
   Sleepy Dunes" is beautiful branding and invisible in search. So the
   SEARCH PHRASE leads the title ("Bedtime Story for Kids 🌙 ...") and
   the story title rides behind it — the exact pattern used by every
   channel that actually ranks in this niche.

2. Each video targets a slightly different long-tail (rotating title
   frames + rotating tag emphasis), so five uploads don't cannibalize
   each other for one phrase — the catalog casts a wider net.

Titles: <=100 codepoints (YouTube's hard limit). Tags: filled toward
the 500-character budget (broad -> long-tail -> story-specific ->
misspelling variants). Descriptions: the first ~150 characters carry
the keywords (search snippet + preview weight), then the story hook,
real chapters, the binge line, the honest AI disclosure, and exactly
three hashtags (more than three and YouTube shows none).
"""
from __future__ import annotations

import json
from pathlib import Path

from .config import cfg

BEAT_LABELS = {
    "hook": "The Story Begins",
    "setup_home": "A Cozy Little Home",
    "setup_problem": "The Night Calls",
    "challenge_1": "First Steps Into the Woods",
    "challenge_2": "The Long Climb",
    "helper_gift": "A Helper's Lesson",
    "challenge_3": "The Bravest Part",
    "turn": "The Magic Wakes",
    "resolve": "The Night Mends",
    "twist": "A Gentle Secret",
    "moral": "What {name} Learned",
    "return": "Walking Home",
    "tuck_in": "Snug in Bed",
    "sleep_a": "Time to Get Sleepy",
    "sleep_b": "Drifting Off",
    "goodnight": "Goodnight",
}

# Rotating (search-phrase, long-tail) pairs for long titles. The head
# is what parents actually type; the tail widens each video's net.
TITLE_FRAMES = [
    ("Bedtime Story for Kids", "Calm Sleep Story"),
    ("Sleep Story for Kids", "Bedtime Story to Fall Asleep"),
    ("Calm Bedtime Story", "Story for Kids to Sleep"),
    ("Kids Bedtime Story", "Gentle Sleep Story"),
    ("Bedtime Story for Children", "Fall Asleep Bedtime Story"),
]

# Broad terms every video should compete for; ordered by priority and
# packed into the 500-char tag budget after the story-specific ones.
TAG_POOL = [
    "bedtime stories for kids",
    "bedtime story for kids",
    "bedtime stories",
    "sleep story for kids",
    "story to fall asleep",
    "calm bedtime story",
    "kids bedtime stories",
    "sleep stories for children",
    "bedtime story to fall asleep",
    "bedtime stories for 5 year olds",
    "bedtime story for 6 year old",
    "stories for kids",
    "kids stories",
    "night story for kids",
    "toddler bedtime story",
    "storytime for kids",
    "read aloud story",
    "relaxing sleep story",
    "original bedtime story",
    "bed time story",
    "moonberry tales",
]

HASHTAGS = ["#BedtimeStories", "#SleepStory", "#StoriesForKids"]


def _fmt_ts(t: float) -> str:
    m, s = divmod(int(t), 60)
    return f"{m}:{s:02d}"


def _frame(story: dict) -> tuple[str, str]:
    """Deterministic per-episode frame rotation (seeded by story hash,
    so a rebuild produces the identical title)."""
    frames = cfg().get("discovery", {}).get("title_frames") or TITLE_FRAMES
    pick = int(story["hash"][:6], 16) % len(frames)
    return frames[pick]


def _clip(text: str, limit: int) -> str:
    """Truncate on a codepoint boundary — never mid-emoji."""
    return text if len(text) <= limit else text[:limit].rstrip(" |—-,·🌙")


def long_title(story: dict) -> str:
    head, tail = _frame(story)
    full = f"{head} 🌙 {story['title']} | {tail}"
    if len(full) <= 100:
        return full
    mid = f"{head} 🌙 {story['title']}"
    if len(mid) <= 100:
        return mid
    return _clip(mid, 100)


def _tag_list(story: dict, frame: tuple[str, str]) -> list[str]:
    atoms = story["atoms"]
    hero = atoms["hero"].split()[-1].lower()
    specific = [
        frame[0].lower(),
        frame[1].lower(),
        f"{hero} story",
        f"{hero} bedtime story",
        f"{hero} story for kids",
        atoms["setting"].lower(),
        atoms["motif"].lower(),
        f"{atoms['moral'].split(',')[0].strip().lower()} story for kids",
    ]
    pool = cfg().get("discovery", {}).get("tag_pool") or TAG_POOL
    out: list[str] = []
    for t in specific + list(pool):
        t = t.strip()
        if t and t not in out:
            out.append(t)
    # pack toward the 500-char budget (comma+space separators)
    packed: list[str] = []
    used = 0
    for t in out:
        cost = len(t) + (2 if packed else 0)
        if used + cost > 480:
            break
        packed.append(t)
        used += cost
    return packed


def long_metadata(story: dict, narration: dict) -> dict:
    vconf = cfg()["video"]
    title_s = float(vconf.get("title_card_seconds", 6))
    channel = cfg()["channel"]

    # chapters from scene timings (first must be 0:00 or YouTube
    # ignores the whole list)
    chapters = [f"{_fmt_ts(0)} Tonight's Story: {story['title']}"]
    t = title_s
    for scene in story["scenes"]:
        label = BEAT_LABELS.get(scene["id"], "The Story Continues").format(name=story["atoms"]["name"])
        chapters.append(f"{_fmt_ts(t)} {label}")
        t += narration["scene_durations"][scene["n"] - 1]
    chapters.append(f"{_fmt_ts(t)} Sleep well")

    atoms = story["atoms"]
    frame = _frame(story)
    story_line = (
        f"{atoms['hero'].title()} named {atoms['name']} sets out to {atoms['quest']} — "
        f"a gentle adventure about {atoms['moral'].lower()}."
    )
    desc = (
        # first ~150 chars: the keywords (search snippet weight)
        f"A calm bedtime story for kids to fall asleep to — soft music, one gentle "
        f"voice, no scary parts. Perfect sleep story for children ages 5-8.\n\n"
        f"\U0001f319 \"{story['hook']}.\"\n\n"
        f"{story_line} A brand-new original {frame[0].lower()}, told once — "
        f"our stories never repeat.\n\n"
        f"\u23f1 Chapters\n{chr(10).join(chapters)}\n\n"
        f"\U0001f319 ABOUT {channel['display_name']}\n"
        f"A new original bedtime story for kids every evening — calm, kind, and "
        f"just long enough for little listeners to drift off. Play our stories in "
        f"a row at bedtime for a full night of gentle tales.\n\n"
        f"\U0001f916 This story, artwork, narration, and music are created with AI "
        f"assistance and reviewed before publishing — disclosed to YouTube per the "
        f"synthetic-media policy. Made for kids.\n\n"
        + " ".join(HASHTAGS)
    )

    tags = _tag_list(story, frame)
    return {"title": long_title(story), "description": desc[:4900],
            "tags": tags, "chapters": chapters}


def short_metadata(story: dict, window: dict) -> dict:
    n = window["scene"]
    scene = next(s for s in story["scenes"] if s["n"] == n)
    label = BEAT_LABELS.get(scene["id"], "A Gentle Moment").format(name=story["atoms"]["name"])
    hero = story["atoms"]["hero"].split()[-1].lower()
    # the shorts feed truncates hard — keyword first, always
    title = _clip(f"Bedtime Story for Kids \U0001f319 {hero.title()} — {story['title']}", 100)
    desc = (
        f"A calm moment from tonight's full bedtime story for kids \U0001f319\n"
        f"\"{story['title']}\" — the complete sleep story is on our channel, "
        f"told in one gentle voice with no scary parts.\n\n"
        f"New original {hero} tales for kids every evening \u00b7 ages 5-8.\n"
        f"AI-assisted, human-reviewed before publishing.\n"
        f"#BedtimeStories #Shorts #SleepStory"
    )
    tags = [
        "bedtime story", "sleep story", "bedtime shorts", "story for kids",
        "calm story", "kids story", "kids shorts", "stories for kids",
        f"{hero} story", "bedtime story for kids", "moonberry tales",
    ]
    return {"title": title, "description": desc[:4900], "tags": tags}
