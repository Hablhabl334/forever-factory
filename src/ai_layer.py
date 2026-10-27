"""The machine-readable TEXT LAYER — the ai-seo skill, translated.

The skill's YouTube doctrine (references/youtube-ai-citations.md):
models don't watch the video, they read the text around it —
transcript, captions, chapters, description, comments. The factory
already speaks every word (the script IS the narration), prints
chapters into the description and a structured, keyword-first block;
this module ships the two surfaces that were still missing, at
exactly 100 quota units/day:

  * captions.insert  — the narration chunks as a clean English VTT
    track: the exact words at the exact times, no auto-caption drift.
    50 units per video (longs by default; shorts opt-in).
  * commentThreads.insert — the channel's own summary comment on the
    long (the numbered lesson list + the comment-bait question): an
    extra liftable text block that also seeds the comment section —
    comments being the strongest engagement signal a small channel
    earns. 50 units per long. The Data API cannot pin comments; the
    owner can pin each one in Studio (30 seconds, optional — the
    comment is valuable unpinned).

Contract (identical to every other YouTube call in this factory):
  * quota is spent ONLY on success — a refused/failed call costs 0
    units and is honestly logged
  * ONE structural refusal (400/403 — a policy change on Google's
    side) is remembered in state["text_layer_refused"] and never
    retried: it can never kill or spam a day (the 2026-10-06 tags
    lesson, applied here from birth)
  * transient failures (5xx/429) leave no flag — the next cycle
    retries naturally
  * per-episode done-flags in the ledger make everything idempotent
    across crash-resumes (the same contract as mark_uploaded)
  * everything is OFF-line until an upload exists: no video id, no
    text layer — and dry-runs never touch the network
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from . import ledger
from .config import cfg
from .youtube import API_BASE, _post

CAPTIONS_URL = "https://www.googleapis.com/upload/youtube/v3/captions"
COMMENT_URL = f"{API_BASE}/commentThreads"
CAPTION_UNITS = 50
COMMENT_UNITS = 50
_BOUNDARY = "fact0ry-text-layer-7f3a9c"


# ── config ─────────────────────────────────────────────────────────
def _conf() -> dict:
    """youtube.text_layer from channel.yaml (defaults: longs only)."""
    try:
        raw = cfg().get("youtube", {}).get("text_layer") or {}
    except Exception:
        raw = {}
    return {
        "captions": bool(raw.get("captions", True)),
        "captions_shorts": bool(raw.get("captions_shorts", False)),
        "summary_comment": bool(raw.get("summary_comment", True)),
    }


# ── ledger helpers ─────────────────────────────────────────────────
def _rec(state: dict, episode_n: int) -> dict:
    """This episode's ledger record (register_story always created it
    before produce_episode runs; a missing record is created here so a
    done-flag is never silently dropped)."""
    for e in state.get("episodes", []):
        if e.get("n") == episode_n:
            return e
    e = {"n": episode_n}
    state.setdefault("episodes", []).append(e)
    return e


def _done(state: dict, episode_n: int, flag: str) -> bool:
    return flag in (_rec(state, episode_n).get("text_layer") or {})


def _mark_done(state: dict, episode_n: int, flag: str) -> None:
    _rec(state, episode_n).setdefault("text_layer", {})[flag] = True


def _refused(state: dict, what: str) -> bool:
    return what in (state.get("text_layer_refused") or {})


def _refuse_forever(state: dict, what: str, reason: str) -> None:
    """A structural refusal (400/403): remember it, never retry it.
    The text layer is a bonus surface — losing it must never cost the
    factory a day, and hammering a refused endpoint forever would."""
    state.setdefault("text_layer_refused", {})[what] = (
        f"{reason} [remembered {date.today().isoformat()}]")
    ledger.save(state)


# ── VTT ────────────────────────────────────────────────────────────
def _vtt_ts(t: float) -> str:
    ms = max(0, int(round(t * 1000)))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def build_vtt(chunks: list[dict], offset: float, out_path: Path) -> Path:
    """Clean WebVTT from the narration chunks — the transcript with
    millisecond-accurate timings (the same numbers that drove the
    burned-in captions, so the track and the pixels never disagree)."""
    lines = ["WEBVTT", ""]
    n = 0
    for ch in chunks:
        start = float(ch["start"]) + offset
        end = float(ch["end"]) + offset
        if end - start < 0.05:
            continue
        text = (ch["text"] or "").strip()
        if not text:
            continue
        text = text.replace("&", "&amp;").replace("<", "&lt;")
        n += 1
        lines += [str(n), f"{_vtt_ts(start)} --> {_vtt_ts(end)}", text, ""]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


# ── API calls ──────────────────────────────────────────────────────
def _multipart(meta: dict, media: bytes, media_type: str) -> bytes:
    head = (
        f"--{_BOUNDARY}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(meta)}\r\n"
        f"--{_BOUNDARY}\r\n"
        f"Content-Type: {media_type}\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{_BOUNDARY}--".encode("utf-8")
    return head + media + tail


def upload_captions(token: str, video_id: str, vtt_path: Path,
                    state: dict, episode_n: int,
                    flag: str = "captions_long") -> bool:
    """Ship the VTT as the video's English caption track. Idempotent
    per episode (ledger flag), quota-gated, refusal-aware."""
    if _done(state, episode_n, flag):
        return True                      # already shipped (resume)
    if _refused(state, "captions"):
        return False                     # Google said no, once, forever
    if ledger.quota_remaining(state) < CAPTION_UNITS:
        print("  [ai-seo] captions skipped — quota too low (never "
              "sacrifice an upload for a bonus surface)")
        return False
    meta = {"snippet": {"videoId": video_id, "language": "en",
                        "name": "English", "isAutoSynced": False}}
    body = _multipart(meta, vtt_path.read_bytes(),
                      "text/vtt; charset=UTF-8")
    status, _headers, raw = _post(
        f"{CAPTIONS_URL}?part=snippet", body,
        {"Authorization": f"Bearer {token}",
         "Content-Type": f"multipart/related; boundary={_BOUNDARY}"})
    if status in (200, 201):
        ledger.spend_quota(state, CAPTION_UNITS)
        _mark_done(state, episode_n, flag)
        ledger.save(state)
        print(f"  [ai-seo] caption track up ({CAPTION_UNITS} units) — "
              f"the transcript is now machine-readable")
        return True
    reason = raw.decode("utf-8", "replace")[:200]
    if status in (400, 403):
        _refuse_forever(state, "captions", f"HTTP {status} {reason}")
        print(f"  [ai-seo] captions refused ({status}) — remembered, "
              f"never retried. Body: {reason}")
    else:
        print(f"  [ai-seo] captions failed transiently ({status}) — "
              f"next cycle retries. Body: {reason}")
    return False


def post_summary_comment(token: str, video_id: str, text: str,
                         state: dict, episode_n: int) -> bool:
    """Post the channel's summary comment on the long (one liftable
    block + the comment-section seed). Same contract as captions."""
    if _done(state, episode_n, "comment"):
        return True
    if _refused(state, "summary_comment"):
        return False
    if ledger.quota_remaining(state) < COMMENT_UNITS:
        print("  [ai-seo] summary comment skipped — quota too low")
        return False
    data = json.dumps({"snippet": {
        "videoId": video_id,
        "topLevelComment": {"snippet": {"textOriginal": text}},
    }}).encode("utf-8")
    status, _headers, raw = _post(
        f"{COMMENT_URL}?part=snippet", data,
        {"Authorization": f"Bearer {token}",
         "Content-Type": "application/json"})
    if status in (200, 201):
        ledger.spend_quota(state, COMMENT_UNITS)
        _mark_done(state, episode_n, "comment")
        ledger.save(state)
        print(f"  [ai-seo] summary comment up ({COMMENT_UNITS} units) — "
              f"pin it in Studio if you want it on top (optional)")
        return True
    reason = raw.decode("utf-8", "replace")[:200]
    if status in (400, 403):
        # commentsDisabled is 403: structural, remembered forever
        _refuse_forever(state, "summary_comment", f"HTTP {status} {reason}")
        print(f"  [ai-seo] summary comment refused ({status}) — "
              f"remembered, never retried. Body: {reason}")
    else:
        print(f"  [ai-seo] summary comment failed transiently ({status}) "
              f"— next cycle retries. Body: {reason}")
    return False


# ── the orchestrator entry point ───────────────────────────────────
def attach_text_layer(story: dict, episode_n: int, long_id: str | None,
                      long_narration: dict, short_ids: list[str],
                      state: dict, work: Path) -> dict:
    """Everything the text layer does after a successful upload pass.
    Never raises, never defers, never spends a unit it did not earn —
    the day's videos are already safe when this runs."""
    out: dict = {}
    if not long_id:
        return out                      # nothing shipped today
    conf = _conf()
    token = None

    def _token() -> str:
        nonlocal token
        if token is None:
            from .youtube import get_access_token
            token = get_access_token()
        return token

    # 1. long captions — the transcript the models actually read
    if conf["captions"]:
        if _done(state, episode_n, "captions_long"):
            out["captions_long"] = "already"
        elif _refused(state, "captions"):
            out["captions_long"] = "refused"
        else:
            title_s = float(cfg()["video"].get("title_card_seconds", 6))
            vtt = build_vtt(long_narration.get("chunks") or [], title_s,
                            work / "captions_long.vtt")
            out["captions_long"] = (
                "ok" if upload_captions(_token(), long_id, vtt, state,
                                        episode_n, "captions_long")
                else "skipped")

    # 2. the summary comment — the second liftable block
    if conf["summary_comment"]:
        if _done(state, episode_n, "comment"):
            out["comment"] = "already"
        elif _refused(state, "summary_comment"):
            out["comment"] = "refused"
        else:
            from .metadata import summary_comment
            out["comment"] = (
                "ok" if post_summary_comment(_token(), long_id,
                                             summary_comment(story),
                                             state, episode_n)
                else "skipped")

    # 3. shorts captions (opt-in — 4x50 units; off by default)
    if conf["captions_shorts"]:
        shorts_spec = story.get("shorts") or []
        for i, sid in enumerate(short_ids):
            if not sid or i >= len(shorts_spec):
                continue
            flag = f"captions_short_{i}"
            if _done(state, episode_n, flag) or _refused(state, "captions"):
                continue
            narr_path = (work / f"short_{shorts_spec[i].get('n', i + 1):02d}"
                         / "narration.json")
            if not narr_path.exists():
                continue
            try:
                mini = json.loads(narr_path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            vtt = build_vtt(mini.get("chunks") or [], 0.0,
                            narr_path.parent / "captions.vtt")
            upload_captions(_token(), sid, vtt, state, episode_n, flag)
    return out
