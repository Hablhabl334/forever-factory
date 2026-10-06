"""YouTube upload — hand-rolled OAuth2 + resumable upload over urllib.

Zero Google client libraries: nothing to rot, nothing to version-pin,
nothing to break for a decade. The only credentials are three GitHub
secrets (YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN).

Every upload:
  * Made-for-Kids designation (bedtime content is child-directed)
  * honest AI-assistance disclosure (containsSyntheticMedia, with a
    graceful retry if the API ever drops the field)
  * scheduled publish at Cairo peak bedtime slots via publishAt
  * quota-aware (1,600 + 50 units per video, ledgered in state)
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

from . import ledger
from .config import cfg

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
API_BASE = "https://www.googleapis.com/youtube/v3"
# thumbnails.set is a MEDIA UPLOAD: it must go through the /upload/ path.
# The bare /youtube/v3/thumbnails/set endpoint permission-checks fine but
# then rejects the image bytes ("The request does not include the image
# content") — the classic YouTube API trap.
THUMB_SET_URL = "https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
CHUNK = 8 * 1024 * 1024  # 8 MB resumable chunks
UPLOAD_UNITS = 1600
THUMB_UNITS = 50


class AuthError(RuntimeError):
    pass


def _creds() -> dict:
    cid = os.environ.get("YT_CLIENT_ID", "")
    csec = os.environ.get("YT_CLIENT_SECRET", "")
    refresh = os.environ.get("YT_REFRESH_TOKEN", "")
    if not (cid and csec and refresh):
        raise AuthError(
            "YouTube credentials missing. Set YT_CLIENT_ID, YT_CLIENT_SECRET, "
            "YT_REFRESH_TOKEN (GitHub repo secrets). See RUNBOOK.md."
        )
    return {"client_id": cid, "client_secret": csec, "refresh_token": refresh}


def _post(url: str, data: bytes, headers: dict) -> tuple[int, dict, bytes]:
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


def get_access_token() -> str:
    c = _creds()
    body = urlencode({
        "client_id": c["client_id"],
        "client_secret": c["client_secret"],
        "refresh_token": c["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    status, _, raw = _post(TOKEN_URL, body, {"Content-Type": "application/x-www-form-urlencoded"})
    if status != 200:
        raise AuthError(f"token refresh failed ({status}): {raw.decode()[:400]}")
    return json.loads(raw)["access_token"]


def verify_credentials() -> dict:
    """Sanity check: refresh a token and read our own channel."""
    token = get_access_token()
    req = urllib.request.Request(
        f"{API_BASE}/channels?part=snippet&mine=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    items = data.get("items", [])
    if not items:
        return {"ok": False, "error": "token works but no channel found"}
    ch = items[0]["snippet"]
    return {"ok": True, "channel": ch.get("title"), "channel_id": items[0]["id"]}


# ── scheduling ───────────────────────────────────────────────────────

def next_slot(kind: str, used: set[str] | None = None) -> str | None:
    """Next publishAt (ISO) in the configured timezone, skipping used slots.

    The schedule is a repeating grid (shorts every 6h at 00:00/06:00/12:00/
    18:00, the long at 20:00 Cairo), so a slot is ALWAYS findable within
    the next ~24h — we scan today, tomorrow, and the day after. Slipping
    a slot just means the video takes the next one; the grid self-heals.
    """
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(cfg()["schedule"]["timezone"])
    slots = cfg()["schedule"][f"{kind}_slots"]
    used = used or set()
    now = datetime.now(tz)
    for day_offset in (0, 1, 2):
        base = (now + timedelta(days=day_offset)).date()
        for hhmm in slots:
            hh, mm = map(int, hhmm.split(":"))
            slot_dt = datetime(base.year, base.month, base.day, hh, mm, tzinfo=tz)
            if slot_dt > now + timedelta(minutes=25) and \
                    slot_dt.isoformat() not in used:
                return slot_dt.isoformat()
    return None  # grid exhausted (never, with a 3-day scan) — publish now


# ── resumable upload ─────────────────────────────────────────────────

def _upload_video(token: str, filepath: Path, meta: dict, status: dict,
                  max_retries: int = 4) -> str:
    body = {"snippet": meta, "status": status}
    init_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Upload-Content-Length": str(filepath.stat().st_size),
    }
    qs = urlencode({"uploadType": "resumable", "part": "snippet,status"})
    status_code, headers, raw = _post(f"{UPLOAD_URL}?{qs}",
                                      json.dumps(body).encode(), init_headers)
    if status_code not in (200, 201):
        raise RuntimeError(f"upload init failed ({status_code}): {raw.decode()[:400]}")
    location = headers.get("Location") or headers.get("location")
    if not location:
        raise RuntimeError("no resumable session URL returned")

    size = filepath.stat().st_size
    offset = 0
    with open(filepath, "rb") as f:
        while offset < size:
            f.seek(offset)
            block = f.read(CHUNK)
            end = offset + len(block) - 1
            req = urllib.request.Request(location, data=block, method="PUT", headers={
                "Content-Length": str(len(block)),
                "Content-Range": f"bytes {offset}-{end}/{size}",
            })
            body = b""
            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    body = resp.read()
            except urllib.error.HTTPError as e:
                if e.code == 308:
                    rng = e.headers.get("Range", "")
                    try:
                        offset = int(rng.split("-")[-1]) + 1
                    except (ValueError, IndexError):
                        offset = end + 1
                    continue
                raw = e.read()
                if e.code in (500, 502, 503, 429) and max_retries:
                    time.sleep(8 * (5 - max_retries))
                    max_retries -= 1
                    continue
                raise RuntimeError(f"upload failed ({e.code}): {raw.decode()[:400]}")
            # 2xx: the resumable session is complete and the response body
            # IS the video resource. Parse it OUTSIDE the except block so
            # a poll failure can never masquerade as an upload failure.
            vid = json.loads(body or b"{}").get("id")
            if not vid:
                vid = _poll_video_id(token)
            return vid
    raise RuntimeError("upload ended without completion response")


def _poll_video_id(token: str) -> str:
    """Fallback if the final upload response lacks an id: our newest
    video. NOTE: videos.list has no 'mine' filter (valid filters: id,
    chart, myRating) — search.list with forMine is the correct call."""
    req = urllib.request.Request(
        f"{API_BASE}/search?part=snippet&forMine=true&type=video"
        f"&order=date&maxResults=1",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        items = json.loads(resp.read()).get("items", [])
    return items[0]["id"]["videoId"] if items else ""


def _find_video_by_title(token: str, title: str,
                          exclude: set[str] | None = None) -> str | None:
    """Crash-safety reconcile: a previous run may have finished the API
    upload but died before recording the video id (sandbox reset, bug,
    runner eviction...). Exact-title match against our own uploads —
    1 quota unit. Prevents duplicate uploads after any crash.

    `exclude` = video ids the LEDGER has already claimed for OTHER
    episodes. Shorts deliberately all share one fixed title (the
    owner's growth strategy), so a bare title match would "adopt"
    yesterday's short and silently skip every upload after day one.
    A match only counts as a crash orphan if the ledger does not
    already attribute it to a different episode — an unrecorded video
    is a true orphan (this episode's own crashed upload), a recorded
    one belongs to another episode and must never be re-used."""
    exclude = exclude or set()
    try:
        req = urllib.request.Request(
            f"{API_BASE}/channels?part=contentDetails&mine=true",
            headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            ch = json.loads(resp.read())["items"][0]
        uploads_id = ch["contentDetails"]["relatedPlaylists"]["uploads"]
        req = urllib.request.Request(
            f"{API_BASE}/playlistItems?part=snippet&playlistId={uploads_id}"
            f"&maxResults=50",
            headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            items = json.loads(resp.read()).get("items", [])
        for it in items:
            if it["snippet"]["title"] != title:
                continue
            vid = it["snippet"]["resourceId"]["videoId"]
            if vid in exclude:
                continue  # claimed by another episode — not an orphan
            return vid
    except Exception:
        return None
    return None


def _foreign_ids(state: dict, episode_n: int) -> set[str]:
    """Video ids the ledger attributes to episodes OTHER than
    episode_n. Ids recorded for episode_n itself stay adoptable (a
    re-run of the same episode must adopt its own earlier upload,
    never duplicate it)."""
    ids: set[str] = set()
    for e in state.get("episodes", []):
        if e.get("n") == episode_n:
            continue
        eids = e.get("ids") or {}
        if eids.get("long"):
            ids.add(eids["long"])
        for s in eids.get("shorts") or []:
            ids.add(s)
    return ids


def _recorded_short_ids(state: dict, episode_n: int) -> set[str]:
    """Short ids already recorded for THIS episode. A short may adopt
    only an UNCLAIMED video: once this episode has recorded a short id,
    that video is taken — the next short of the same episode must not
    re-adopt it (all shorts share the fixed title, so without this the
    2nd short would grab the 1st one's freshly adopted orphan)."""
    for e in state.get("episodes", []):
        if e.get("n") == episode_n:
            return set((e.get("ids") or {}).get("shorts") or [])
    return set()


def _duration_seconds(iso: str) -> float:
    """ISO-8601 duration (PT1M9S, PT10M9S, P0D, PT59S...) to seconds.
    A placeholder video left behind by an abandoned resumable-init
    session reports P0D / PT0S — zero seconds."""
    import re
    m = re.fullmatch(
        r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?",
        (iso or "").strip())
    if not m:
        return 0.0
    d, h, mi, s = (float(x) if x else 0.0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def _adoptable(token: str, video_id: str, min_seconds: float = 30.0) -> bool:
    """A crash orphan must be a REAL video before it can be adopted.

    Oct 6 lesson (ep16): an abandoned resumable-init session leaves a
    zero-duration placeholder (P0D) on the channel, findable by exact
    title — run #99 adopted one as the day's long and the real upload
    was nearly lost to it. Verify contentDetails.duration first (one
    videos.list, 1 quota unit, rare path). Under 30 s — or anything
    unverifiable — is rejected: a fresh upload is strictly safer than
    a broken adoption, and our real videos are 60 s+ by construction."""
    try:
        req = urllib.request.Request(
            f"{API_BASE}/videos?part=contentDetails&id={video_id}",
            headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            items = json.loads(resp.read()).get("items", [])
        if not items:
            print(f"  [youtube] adoption candidate {video_id} not found "
                  f"— ignoring")
            return False
        dur = _duration_seconds(
            items[0].get("contentDetails", {}).get("duration", ""))
        if dur < min_seconds:
            print(f"  [youtube] title match {video_id} has duration "
                  f"{dur:.0f}s (< {min_seconds:.0f}s) — not a real "
                  f"video, ignoring the match")
            return False
        return True
    except Exception:
        print(f"  [youtube] could not verify {video_id} — not adopting")
        return False


def _set_thumbnail(token: str, video_id: str, thumb: Path) -> bool:
    data = thumb.read_bytes()
    print(f"  [youtube] setting thumbnail {thumb.name} "
          f"({len(data) // 1024} KB) on {video_id}")
    req = urllib.request.Request(
        f"{THUMB_SET_URL}?videoId={video_id}",
        data=data,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "image/png"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status in (200, 201)
    except urllib.error.HTTPError as e:
        # Log the real reason — custom thumbnails are blocked for
        # unverified API projects/channels (403) until phone-verified:
        # https://www.youtube.com/verify
        try:
            detail = e.read().decode()[:200]
        except Exception:
            detail = ""
        print(f"  [youtube] thumbnail set failed: HTTP {e.code} {detail}")
        return False


def set_thumbnail(token: str, video_id: str, thumb: Path) -> bool:
    """Public wrapper: set a custom thumbnail (50 quota units at the
    API). Used by the upload flow and the daily self-healing backfill."""
    return _set_thumbnail(token, video_id, thumb)


def upload_video(filepath: Path, meta: dict, publish_at: str | None,
                 episode_n: int, kind: str, state: dict | None = None) -> str | None:
    """Full upload flow with quota gate + ledger. Returns video id.

    Pass the caller's state (single source of truth) — if omitted a
    local one is loaded (tools, tests)."""
    if state is None:
        state = ledger.load()
    remaining = ledger.quota_remaining(state)
    need = UPLOAD_UNITS + THUMB_UNITS
    if remaining < need:
        print(f"  [quota] {remaining} units left, need {need} — deferring")
        return None

    yconf = cfg()["youtube"]
    token = get_access_token()

    # crash-safety: if this exact title is already on the channel (a past
    # run uploaded it but crashed before recording the id), adopt it —
    # never upload the same video twice. Videos the ledger already
    # claims for a DIFFERENT episode are not orphans (shorts share a
    # fixed title, so every day would match yesterday's) — they must
    # not block today's fresh upload. For shorts, this episode's own
    # recorded ids are also taken (one adoption per video, never two
    # shorts on the same video); a long may always re-adopt its own
    # recorded id — that is exactly the resume path.
    exclude = _foreign_ids(state, episode_n)
    if kind == "short":
        exclude |= _recorded_short_ids(state, episode_n)
    existing = _find_video_by_title(token, meta["title"], exclude=exclude)
    if existing and _adoptable(token, existing):
        print(f"  [youtube] {kind} already on channel ({existing}) — adopting, no re-upload")
        ledger.mark_uploaded(state, episode_n, kind, existing, 1)
        return existing
    if existing:
        print(f"  [youtube] ignoring unverified title match {existing} — "
              f"uploading fresh")

    status = {
        "privacyStatus": "private",
        "madeForKids": bool(yconf.get("made_for_kids", True)),
        "selfDeclaredMadeForKids": bool(yconf.get("made_for_kids", True)),
    }
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    else:
        status["privacyStatus"] = yconf.get("privacy", "public")
    if yconf.get("synthetic_media_disclosure", True):
        status["containsSyntheticMedia"] = True

    meta = dict(meta)
    meta.setdefault("categoryId", str(yconf.get("category_id", "24")))
    meta.setdefault("defaultLanguage", yconf.get("default_language", "en"))
    meta.setdefault("defaultAudioLanguage", yconf.get("default_language", "en"))

    # 2026-10-06 lesson (ep16): YouTube tightened snippet.tags validation
    # mid-flight — a 26-tag/454-char list that had been fine for 15
    # episodes came back 400 invalidTags, while the identical body with
    # the tags field removed passed. Whatever the new rule is, a
    # validation change on their side must never kill the day: fall
    # back to a tags-less upload (hashtags already live in the title
    # and description, so discoverability survives). A rejected init
    # costs zero quota, so this fallback is free.
    meta_variants = [meta]
    if meta.get("tags"):
        meta_variants.append({k: v for k, v in meta.items() if k != "tags"})

    video_id = None
    for variant in meta_variants:
        try:
            video_id = _upload_video(token, filepath, variant, status)
            break
        except RuntimeError as e:
            msg = str(e)
            if "containsSyntheticMedia" in msg:
                status.pop("containsSyntheticMedia", None)
                token = get_access_token()
                try:
                    video_id = _upload_video(token, filepath, variant, status)
                    break
                except RuntimeError as e2:
                    e, msg = e2, str(e2)
            if "quota" in msg.lower() or "exceeded" in msg.lower():
                # YouTube's real (server-side) quota says stop — defer to
                # tomorrow instead of failing the day. The episode stays
                # in_progress and resumes (adopted, never duplicated).
                print(f"  [quota] YouTube quota hit during {kind} upload — deferring")
                return None
            if "invalidTags" in msg and variant is not meta_variants[-1]:
                print("  [youtube] tags rejected (invalidTags) — "
                      "retrying without tags")
                continue
            raise
    print(f"  [youtube] uploaded {kind}: {video_id} "
          f"(publishAt {publish_at or 'now'})")

    # custom thumbnail for longs only — shorts sit in the same output
    # directory as thumbnail.png, but use their auto frame by design
    thumb = filepath.with_name("thumbnail.png") if kind == "long" else None
    if thumb and thumb.exists():
        if set_thumbnail(token, video_id, thumb):
            print("  [youtube] thumbnail set")
            # record it so the daily backfill never retries this video
            ledger.mark_thumbnail(state, episode_n)
        else:
            print("  [youtube] thumbnail set failed (non-fatal — daily "
                  "backfill retries until the channel is verified)")

    ledger.mark_uploaded(state, episode_n, kind, video_id, need)
    state["stats"]["videos_published"] = state["stats"].get("videos_published", 0) + 1
    ledger.save(state)
    return video_id
