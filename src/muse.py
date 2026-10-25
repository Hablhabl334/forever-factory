"""The muse — an LLM writing layer above the grammar engine.

The grammar engine (story_engine.py) picks WHAT the day says: the
topic, the eight concepts, the no-repeat ledger, the scene
vocabulary that the renderer and the animator speak. It has produced
every episode so far, and it keeps that job.

The muse rewrites HOW it is said. Every narration line and every
Short script is re-written by a large language model before it ever
reaches the microphone — fresh sentences every single day, no
recycled variant pools, a human writer's variety at machine cadence.

Design contract (the part that matters):

  * NEVER A DEPENDENCY. No key / no network / no budget / any
    failure at any stage -> the grammar text ships unchanged.
    The machine cannot die because of the muse. The worst muse
    day is simply a grammar day, which is the machine we already
    trusted.
  * PIECEWISE ACCEPTANCE. Every LLM line is validated alone
    (banned-word audit, fake-stat guard, word bands, term rules,
    ASCII safety). A bad line keeps its grammar twin; a good line
    replaces it. A half-mused episode is valid and complete.
  * BUDGETED. OpenRouter free models allow 50 requests/day for a
    free-tier key. The muse spends 2 calls per episode (one long,
    one for all four Shorts), hard-capped at MUSE_DAILY_CAP per
    day, counted inside state.json so every cycle of the day sees
    the same number. A normal day never goes above 2-4.
  * DETERMINISTIC REPLAY. Enhanced stories are cached under
    data/muse_cache/<seed>.json the moment they are written, so a
    crashed cycle that re-runs rebuilds the IDENTICAL text (the
    cache returns before any HTTP call). The crash-resume and
    thumbnail-replay contracts of the ledger keep working.
  * TEXT ONLY. The muse touches narration strings and script
    strings. The image dicts, emotions, poses, overlay terms and
    every render code path stay exactly as the grammar built
    them - the renderer never learns the muse exists.

Gating: the layer is live only when OPENROUTER_API_KEY is set and
MUSE is not "0". Local offline runs (no env) see a dormant muse and
behave byte-identically to the pre-muse machine.

Model chain: nvidia/nemotron-3-ultra-550b (the 550B flagship, a
reasoning writer - separate `reasoning` field, clean content),
poolside/laguna-s-2.1 and nemotron-nano-omni as load-shedding
fallbacks for upstream 429 days. All :free endpoints - cost $0,
token usage unmetered, only the 50/day request counter moves.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from .content_data import CTA_LINE
from .story_engine import _BANNED_RE, _short_hash

# ── configuration ───────────────────────────────────────────────────

_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "poolside/laguna-s-2.1:free",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
]
_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
_DAILY_CAP = 10          # of the 50 free requests the key allows
_ATTEMPTS = 4             # worst-case HTTP tries per chat()
_TIMEOUT = 300            # the 550B reasons for minutes; that's fine
_CACHE_DIR = Path("data/muse_cache")
_CACHE_KEEP = 40          # prune: newest 40 enhanced stories stay

# unicode -> ASCII (TTS + text-overlay safety: the channel's fonts
# and the narrator both speak plain ASCII; an em-dash that renders
# as tofu or reads as silence is a quality bug, not a style choice)
_ASCII_MAP = {
    "\u2014": "-", "\u2013": "-", "\u2011": "-", "\u2012": "-",
    "\u2013": "-", "\u2212": "-", "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00a0": " ",
    "\u2022": "-", "\u00b7": "-", "\u2192": "->", "\u25b8": "-",
}
_CTRL_RE = re.compile(
    "[\u200b\u200c\u200d\ufeff\ufe0f\U0001F000-\U0001FAFF"
    "\u2600-\u27bf\U0001F900-\U0001F9FF]")

# fake-statistics guard: "73% of people", "9 out of 10" - invented
# numbers are the classic LLM hallucination and this channel never
# quotes research it cannot cite
_STAT_RE = re.compile(r"\d+\s?(?:%|percent|x\b)|\b\d+\s?out of\s?\d+")


def _key() -> str | None:
    return os.environ.get("OPENROUTER_API_KEY") or None


def _enabled() -> bool:
    if os.environ.get("MUSE", "1") == "0":
        return False
    return _key() is not None


def _sanitize(text: str) -> str:
    for bad, good in _ASCII_MAP.items():
        text = text.replace(bad, good)
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _clean_line(text: str) -> bool:
    """One narration line passes every content gate."""
    if not text or len(text) < 8:
        return False
    if _BANNED_RE.search(text):
        return False
    if _STAT_RE.search(text):
        return False
    return True


# ── the budget ledger (lives inside state.json -> committed daily) ──

def _budget(state: dict) -> tuple[str, int]:
    b = state.get("muse_budget", {})
    today = time.strftime("%Y-%m-%d")
    if b.get("date") != today:
        b = {"date": today, "calls": 0}
    return b.get("date"), int(b.get("calls", 0))


def _spend(state: dict) -> bool:
    """Count one request. False -> cap reached, do not call."""
    date, calls = _budget(state)
    if calls >= _DAILY_CAP:
        return False
    state["muse_budget"] = {"date": date, "calls": calls + 1}
    return True


# ── the HTTP call (stdlib only - no new dependency, ever) ──────────

def _extract_json(text: str):
    """Parse JSON out of a model reply that may be fenced, chatty or
    (the 550B's favorite) preceded by thousands of tokens of drafting.
    Strategy: direct parse, then fenced block, then the LAST object
    that starts with a key we actually want."""
    text = text.strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except (ValueError, TypeError):
            pass
    for anchor in ('{"shorts"', '"shorts"', '{"scenes"', '"scenes"'):
        i = text.rfind(anchor)
        if i == -1:
            continue
        j = text.rfind("{", 0, i + 1)
        cand = text[j: text.rfind("}") + 1]
        try:
            return json.loads(cand)
        except (ValueError, TypeError):
            continue
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e > s:
        try:
            return json.loads(text[s:e + 1])
        except (ValueError, TypeError):
            pass
    return None


def chat(prompt: str, state: dict, max_tokens: int = 6000,
         anchor: str | None = None):
    """One completion through the model chain.

    Returns (content, model) or (None, None) after every path fails.
    Retries 429s once with a pause, then sheds to the next model -
    free endpoints are contended and today's flagship is sometimes
    tomorrow's maintenance window, so no single model is load-
    bearing.

    anchor: when given (e.g. '"shorts":'), a reply that does not
    contain it counts as a failure - the big reasoning models
    sometimes spend their entire token budget drafting out loud and
    never emit the JSON. Anchored requests keep walking the chain
    until a model actually answers the question."""
    if not _spend(state):
        print("  [muse] daily request cap reached - grammar text this cycle")
        return None, None
    api_key = _key()
    chain = []
    for m in _MODELS:
        chain.extend([m, m])            # one retry per model
    for model in chain[:_ATTEMPTS]:
        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.85,
            "max_tokens": max_tokens,
        }).encode()
        req = urllib.request.Request(_ENDPOINT, data=body, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
                d = json.loads(r.read())
            msg = d["choices"][0].get("message", {})
            content = msg.get("content") or ""
            if content.strip() and (anchor is None or anchor in content):
                return content, model
            continue                      # babble / reasoning-only: next
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(25)             # upstream contention, breathe
                continue
            continue                      # 4xx/5xx: next model
        except Exception:
            continue                      # timeout / reset: next model
    return None, None


# ── the story cache (deterministic replay, crash-safe) ─────────────

def _cache_path(seed: int) -> Path:
    return _CACHE_DIR / f"{seed}.json"


def _cache_load(seed: int) -> dict | None:
    p = _cache_path(seed)
    if not p.exists():
        return None
    try:
        cached = json.loads(p.read_text())
        return cached if cached.get("hash") else None
    except Exception:
        return None


def _cache_save(story: dict) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _cache_path(story["seed"]).write_text(
            json.dumps(story, ensure_ascii=True, indent=1))
        files = sorted(_CACHE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
        for old in files[:-_CACHE_KEEP]:
            old.unlink(missing_ok=True)
    except Exception:
        pass                              # cache is an optimization, never a gate


def _recent_surfaces() -> list[str]:
    """Recent hook/term lines the LLM must not echo (anti-repeat)."""
    lines: list[str] = []
    try:
        files = sorted(_CACHE_DIR.glob("*.json"),
                       key=lambda p: p.stat().st_mtime, reverse=True)[:6]
        for f in files:
            try:
                s = json.loads(f.read_text())
            except Exception:
                continue
            lines.extend(
                sc.get("narration", "").split(".")[0] for sc in s.get("scenes", [])
                if sc.get("id", "").startswith("tip")
                and sc.get("id", "").endswith("_card"))
            lines.extend(sh.get("hook", "") for sh in s.get("shorts", []))
    except Exception:
        pass
    return [l[:90] for l in lines if l][:14]


# ── the writing briefs ──────────────────────────────────────────────

_STYLE = """You write narration for a psychology-of-love YouTube channel.
Audience: 18-40, thinking about crushes, distance, heartbreak, self-worth.
Voice: warm, direct, a little wry - a smart friend who happens to know
psychology. Spoken English, second person where natural. Never clinical,
never preachy, never lists. Plain ASCII only."""

_RULES = """HARD RULES:
- plain ASCII characters only (no em-dashes, curly quotes, emoji)
- no invented statistics or numbers (never "73% of people", "9 out of 10")
- never say: disorder, diagnose, narcissist, toxic, manipulative, cure, therapy
- never pathologize; the channel names patterns, it never labels people
- same information as the draft, in fresh words - do not add new claims"""


def _long_brief(story: dict) -> str:
    scenes = []
    for sc in story["scenes"]:
        scenes.append(
            f"- id={sc['id']}  draft: {sc['narration']}")
    avoid = _recent_surfaces()
    avoid_txt = ("\nLines recent episodes already used - open DIFFERENTLY, "
                 "do not echo them:\n" + "\n".join(f"- {a}" for a in avoid)
                 if avoid else "")
    return f"""{_STYLE}

Rewrite every scene narration of today's long video below. Each draft is a
finished beat; keep its role, its facts and its concept, but write it like
a human scriptwriter would say it out loud. Vary sentence rhythm; some
short punchy lines, some flowing ones. Keep each within 70%-150% of the
draft's length.

{_RULES}
- tip1_card..tip8_card are insight beats: open each with a line that lands,
  then the mechanism in one breath
- tip1_scene..tip8_scene are the everyday moment + what to do: keep them
  concrete and visual; do NOT mention the concept term in them (the screen
  shows it)
- open_card is the episode intro: keep the "today you get N pieces" framing
  and the stay-till-the-end promise
- outro_card is the outro: keep the recap feeling, include this exact
  engagement question: "{story['question']}", and end with an invitation
  to subscribe{avoid_txt}

Scenes:
{chr(10).join(scenes)}

Return STRICT JSON only: {{"scenes": ["<rewritten narration 1>",
"<rewritten narration 2>", ...]}} with EXACTLY {len(story['scenes'])} strings in the same order.

OUTPUT DISCIPLINE: your entire reply is one JSON object. The first
character you write must be `{{`. Do not plan out loud - emit the
finished JSON immediately."""


def _shorts_brief(story: dict) -> str:
    items = []
    for sh in story["shorts"][:6]:
        items.append(
            f"SHORT {sh['n']} (concept term: \"{sh['term']}\")\n"
            f"fact basis (do not copy phrasing):\n{sh['script']}")
    return f"""{_STYLE}

Rewrite each of these {len(items)} YouTube Shorts as one fresh 60-second
vertical script. Write them like this EXAMPLE (match its shape, rhythm
and field lengths closely - it is calibrated to the channel's pace):

EXAMPLE (for a different concept, never reuse its lines):
{{
  "opener": "Three texts. No reply.",
  "hook": "The person who answers slowest is often the one listening hardest, and almost nobody believes this.",
  "micro": "She double-texts the question, waits, watches the typing dots appear and vanish, then puts the phone in a drawer and calls it nothing.",
  "fact1": "When someone takes their time replying to you, the delay is often careful word choice happening behind the scenes, not indifference hiding behind a busy schedule.",
  "fact2": "Instant answers feel like real chemistry on the first night, but sustained attention over weeks is the thing that actually predicts whether the care will last past the honeymoon.",
  "reveal": "Psychologists call this responsiveness pacing.",
  "takeaway": "Before you read silence as losing interest, ask one direct question and watch what happens next.",
  "question": "Who in your life replies slowly but always shows up when it actually matters?"
}}

FIELD RULES:
- opener: 3-6 words, pattern interrupt, never a question, never
  starts with "Did you know" or "Psychology"
- hook: one 12-18 word sentence, doubles as the on-screen headline
- micro: one vivid third-person moment, no dialogue, no names, and
  it must NOT contain the concept term
- fact1 / fact2: two distinct WHY-it-happens sentences, plain
  psychology, no numbers, no concept term
- reveal: contains the exact concept term verbatim, phrased like the
  example's reveal
- takeaway: actionable reframe
- question: asks about the viewer's own experience with this pattern
- all fields except opener end with a period

{_RULES}
- each script must run at least 135 words across its fields
  (aim for 145-170: a 55-70 second script - this is a hard
  acceptance gate, so write full, generous sentences)
- the shorts must feel written on different mornings: different
  opener shapes, different rhythms, never the same reveal phrasing

{chr(10).join(items)}

Your reply: one JSON object, exactly like the EXAMPLE's shape but
with one object per short, same order:
{{"shorts": [object_1, object_2, ...]}}

OUTPUT DISCIPLINE: your entire reply is one JSON object. The first
character you write must be `{{`. Do not plan out loud, do not count
words in your reply, do not draft - emit the finished JSON only."""


# ── piecewise validation ────────────────────────────────────────────

def _valid_scene(new: str, old: str) -> bool:
    if not _clean_line(new):
        return False
    lo, hi = max(12, 0.45 * len(old.split())), 2.2 * len(old.split())
    return lo <= len(new.split()) <= hi


def _valid_short(fields: dict, term: str) -> str | None:
    """Return the assembled script, or None if any gate fails."""
    for k in ("opener", "hook", "micro", "fact1", "fact2",
              "reveal", "takeaway", "question"):
        v = _sanitize(str(fields.get(k, ""))).strip().rstrip(";,")
        if not v:
            return None
        # caption chunking splits on sentence ends: a field without
        # terminal punctuation would fuse into the next chunk (the
        # grammar's own openers all end with a period for this reason)
        if not v.endswith((".", "!", "?")):
            v += "."
        fields[k] = v
    all_text = " ".join(fields.values())
    if not _clean_line(all_text):
        return None
    if term.lower() not in fields["reveal"].lower():
        return None
    if term.lower() in (fields["micro"] + " " + fields["fact1"]
                        + " " + fields["fact2"]).lower():
        return None
    if "?" in fields["opener"]:
        return None
    if len(fields["hook"].split()) > 18 or len(fields["hook"].split()) < 5:
        return None
    if len(fields["micro"].split()) > 28:
        return None
    if len(fields["fact1"].split()) > 32 or len(fields["fact2"].split()) > 32:
        return None
    script = " ".join([fields["opener"], fields["hook"], fields["micro"],
                      fields["fact1"], fields["fact2"], fields["reveal"],
                      fields["takeaway"], fields["question"],
                      CTA_LINE])
    words = len(script.split())
    if not 112 <= words <= 215:
        return None
    return script


# ── the entry point ─────────────────────────────────────────────────

def enhance(story: dict, state: dict, cache_only: bool = False) -> dict:
    """Rewrite the story's text through the LLM. Returns the story
    (enhanced or original); NEVER raises. Cache-first so replays are
    byte-identical - even when the key is gone, an episode that was
    rendered from muse text replays from muse text (the cache IS the
    recorded script). cache_only=True never touches the network:
    it serves the cache or the grammar story (thumbnail backfill)."""
    try:
        cached = _cache_load(story["seed"])
        if cached is not None:
            print(f"  [muse] cache hit seed {story['seed']} - replay")
            return cached
        if cache_only or not _enabled():
            story["muse"] = "grammar"
            return story
        if _budget(state)[1] >= _DAILY_CAP:
            print("  [muse] dormant (budget) - grammar text this cycle")
            story["muse"] = "grammar"
            return story

        story = json.loads(json.dumps(story))   # deep copy: original stays pristine
        used: list[str] = []
        shorts_won = 0
        model = model2 = None

        # -- call 1: the long video -------------------------------
        raw, model = chat(_long_brief(story), state, max_tokens=12000,
                          anchor='"scenes":')
        if raw:
            data = _extract_json(raw)
            scenes = data.get("scenes") if isinstance(data, dict) else None
            if isinstance(scenes, list) and len(scenes) == len(story["scenes"]):
                for sc, new in zip(story["scenes"], scenes):
                    new = _sanitize(str(new))
                    if _valid_scene(new, sc["narration"]):
                        sc["narration"] = new
                        used.append(sc["id"])
                print(f"  [muse] long: {len(used)}/{len(story['scenes'])} "
                      f"scenes rewritten ({model.split('/')[0]})")
            else:
                print("  [muse] long: reply shape rejected - keeping drafts")
        else:
            print("  [muse] long: no reply - keeping drafts")

        # -- call 2: all the Shorts in one brief ------------------
        def _try_shorts(indices: list[int]) -> list[int]:
            """One LLM pass over the given shorts; each valid rewrite
            lands in place, each reject keeps its grammar twin.
            Returns the indices actually rewritten."""
            nonlocal shorts_won, model2
            if not indices:
                return []
            sub = [story["shorts"][i] for i in indices]
            raw, m = chat(_shorts_brief({"shorts": sub}), state,
                          max_tokens=12000, anchor='"shorts":')
            if m:
                model2 = m
            if not raw:
                print("  [muse] shorts: no reply - keeping drafts")
                return []
            data = _extract_json(raw)
            shorts = data.get("shorts") if isinstance(data, dict) else None
            if not (isinstance(shorts, list) and shorts):
                print("  [muse] shorts: reply shape rejected - keeping drafts")
                return []
            won_idx: list[int] = []
            for k, (sh, fields) in enumerate(zip(sub, shorts)):
                if not isinstance(fields, dict):
                    continue
                script = _valid_short(fields, sh["term"])
                if script:
                    sh["script"] = script
                    sh["hook"] = fields["hook"]
                    sh["words"] = len(script.split())
                    sh["shash"] = _short_hash(script)
                    shorts_won += 1
                    won_idx.append(indices[k])
            return won_idx

        all_idx = list(range(len(story["shorts"])))
        done = _try_shorts(all_idx)
        story["short_hashes"] = [s["shash"] for s in story["shorts"]]
        # one targeted retry for the rejects, while budget is roomy
        failed = [i for i in all_idx if i not in done]
        if failed and _budget(state)[1] + 2 <= _DAILY_CAP:
            print(f"  [muse] shorts: retrying {len(failed)} reject(s)")
            done += _try_shorts(failed)
            story["short_hashes"] = [s["shash"] for s in story["shorts"]]
        print(f"  [muse] shorts: {shorts_won}/{len(story['shorts'])} "
              f"rewritten ({model2.split('/')[0] if model2 else '?'})")

        # -- recompute the long's identity from final text ---------
        story["words"] = sum(len(s["narration"].split())
                             for s in story["scenes"])
        story["hash"] = _short_hash("\n".join(
            s["narration"] for s in story["scenes"]))
        story["muse"] = "llm" if (used or shorts_won) else "grammar"
        story["muse_model"] = (model or model2 or "") if story["muse"] == "llm" else ""
        _cache_save(story)
        return story
    except Exception as e:
        print(f"  [muse] layer error ({type(e).__name__}) - grammar text")
        story["muse"] = "grammar"
        return story
