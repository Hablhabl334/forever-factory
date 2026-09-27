"""Per-video YouTube metadata — honest titles, parent-focused
descriptions, real chapters, tags, and the required disclosures."""
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

TAG_POOL = [
    "bedtime stories", "bedtime story for kids", "calm bedtime story",
    "sleep story for children", "stories for kids to sleep",
    "kids bedtime stories", "storytime for children", "ages 5 8",
    "relaxing story for sleep", "original bedtime story",
    "gentle story for kids", "bedtime stories for toddlers",
    "moonberry tales", "read aloud bedtime story",
]


def _fmt_ts(t: float) -> str:
    m, s = divmod(int(t), 60)
    return f"{m}:{s:02d}"


def long_metadata(story: dict, narration: dict) -> dict:
    vconf = cfg()["video"]
    title_s = float(vconf.get("title_card_seconds", 6))
    channel = cfg()["channel"]

    # chapters from scene timings
    chapters = [f"{_fmt_ts(0)} Tonight's Story: {story['title']}"]
    t = title_s
    for scene in story["scenes"]:
        label = BEAT_LABELS.get(scene["id"], "The Story Continues").format(name=story["atoms"]["name"])
        chapters.append(f"{_fmt_ts(t)} {label}")
        t += narration["scene_durations"][scene["n"] - 1]
    chapters.append(f"{_fmt_ts(t)} Sleep well")

    atoms = story["atoms"]
    desc = (
        f"{story['hook']}\n\n"
        f"A brand-new original bedtime story, told in one calm voice with soft music "
        f"and gentle pictures — written to help little listeners (ages 5-8) settle down "
        f"and drift off to sleep.\n\n"
        f"Ton\u0121ht's tale: {atoms['hero']} named {atoms['name']} sets out to {atoms['quest']} — "
        f"a gentle adventure about {atoms['moral'].lower()}.\n\n"
        f"Chapters\n{chr(10).join(chapters)}\n\n"
        f"Made for kids. This story, artwork, narration, and music are created "
        f"with AI assistance and reviewed before publishing. No scary parts, "
        f"no loud sounds — just a quiet way to end the day.\n\n"
        f"New original stories every evening. \U0001f319 {channel['display_name']}"
    ).replace("Ton\u0121ht", "Tonight")

    tags = TAG_POOL + [atoms["hero"].split()[-1] + " story", atoms["setting"].lower(),
                       atoms["motif"], " bedtime"]
    tags = [t.strip() for t in tags if t.strip()][:18]

    title = f"{story['title']} | A Calm Bedtime Story for Kids"
    return {"title": title[:99], "description": desc[:4900], "tags": tags,
            "chapters": chapters}


def short_metadata(story: dict, window: dict) -> dict:
    n = window["scene"]
    scene = next(s for s in story["scenes"] if s["n"] == n)
    label = BEAT_LABELS.get(scene["id"], "A Gentle Moment").format(name=story["atoms"]["name"])
    title = f"{story['title']} \u2014 {label} \U0001f319 #shorts"
    desc = (
        f"A calm moment from tonight's bedtime story: {story['title']}.\n"
        f"The full story is on the channel \u2014 a brand-new original tale every evening.\n\n"
        f"Made for kids \u00b7 calm narration \u00b7 no scary parts.\n"
        f"AI-assisted production, human-reviewed before publishing.\n"
        f"\U0001f319 {cfg()['channel']['display_name']} #bedtimestories #shorts"
    )
    tags = ["bedtime story", "calm story", "story for kids", "sleep story",
            "bedtime shorts", "kids story", story["atoms"]["hero"].split()[-1] + " story"]
    return {"title": title[:99], "description": desc[:4900], "tags": tags}
