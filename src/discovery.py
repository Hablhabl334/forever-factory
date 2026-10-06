"""The discovery layer — what makes the catalog findable.

Three jobs, in order of impact:

1. GROWTH SNAPSHOT (works today, read-only scope): pull view counts
   for every video we ever uploaded, store the daily history in the
   factory memory, and print a growth report into factory.log. This
   is the "research" half of the guide's research->create->improve
   loop — without numbers, improvement is guessing.

2. THE BEDTIME PLAYLIST (needs one re-consent): a public playlist
   with every long story. Bedtime is a binge niche — a parent starts
   the playlist and the autoplay queue quietly racks up watch time
   while the little one drifts off. Playlists also rank in YouTube
   search as their own results. Self-healing: until the channel's
   OAuth token carries the broader scope, these calls 403 and the
   factory just notes it in the log and moves on — never blocking
   an upload.

3. CHANNEL KEYWORDS + DESCRIPTION (same re-consent): YouTube search
   indexes the channel's own keywords; a new channel has none until
   we set them.

Every quota unit is ledgered, every call is defensive: discovery
failures must never cost the day an episode.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from . import ledger, youtube
from .config import cfg

API_BASE = "https://www.googleapis.com/youtube/v3"
UNITS_STATS = 1            # videos.list
UNITS_BRANDING = 50        # channels.update
UNITS_PLAYLIST = 50        # playlists.insert
UNITS_PLAYLIST_ITEM = 50   # playlistItems.insert

# ~60 daily snapshots = two months of growth history in git
MAX_SNAPSHOTS = 60


class ScopeBlocked(RuntimeError):
    """The refresh token lacks write scopes (playlists / branding).
    Needs the one-click re-consent described in RUNBOOK Part 3."""


def _get(token: str, url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _send(token: str, url: str, body: dict, method: str = "POST") -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode()[:300]
        except Exception:
            pass
        if e.code == 403 and ("insufficient" in detail.lower()
                              or "forbidden" in detail.lower()):
            raise ScopeBlocked(detail)
        raise RuntimeError(f"HTTP {e.code}: {detail}")


def _all_video_ids(state: dict) -> list[tuple[str, str]]:
    """[(video_id, episode label)] for every uploaded long and short."""
    out = []
    for e in state.get("episodes", []):
        ids = e.get("ids", {})
        if ids.get("long"):
            out.append((ids["long"], f"ep{e['n']} long"))
        for s in ids.get("shorts", []):
            out.append((s, f"ep{e['n']} short"))
    return out


# ── 1. growth snapshot ─────────────────────────────────────────────

def snapshot_views(token: str, state: dict) -> dict | None:
    """Pull statistics for every video we have (1 unit per 50 videos),
    store the day's snapshot, and print the growth report."""
    vids = _all_video_ids(state)
    if not vids:
        return None
    if ledger.quota_remaining(state) < UNITS_STATS:
        print("[stats] quota too low for the snapshot — skipping")
        return None

    per_video: dict[str, int] = {}
    titles: dict[str, str] = {}
    for i in range(0, len(vids), 50):
        chunk = vids[i:i + 50]
        ids_q = ",".join(v for v, _ in chunk)
        data = _get(token, f"{API_BASE}/videos?part=snippet,statistics"
                           f"&id={ids_q}&maxResults=50")
        for it in data.get("items", []):
            per_video[it["id"]] = int(
                it.get("statistics", {}).get("viewCount", 0))
            titles[it["id"]] = it.get("snippet", {}).get("title", "")
    ledger.spend_quota(state, UNITS_STATS)

    today = date.today().isoformat()
    history = state.setdefault("analytics", [])
    prev = history[-1] if history else None
    total = sum(per_video.values())
    delta = total - prev["total_views"] if prev else None

    history.append({
        "date": today,
        "total_views": total,
        "videos": per_video,
    })
    del history[:-MAX_SNAPSHOTS]

    print(f"[stats] growth report {today}")
    if delta is None:
        print(f"[stats]   baseline: {total} view(s) across "
              f"{len(per_video)} video(s)")
    else:
        print(f"[stats]   total: {total} views  ({'+' if delta >= 0 else ''}{delta} since last report)")
    movers = sorted(per_video.items(), key=lambda kv: -kv[1])[:3]
    for vid, views in movers:
        if views > 0:
            t = titles.get(vid, "?")[:60]
            print(f"[stats]   {views:>6} views  ·  {t}")
    if total == 0:
        print("[stats]   no views yet — normal for the first days; "
              "search indexing takes time. The SEO overhaul "
              "(titles, tags, playlists) is doing its work quietly.")
    ledger.save(state)
    return history[-1]


# ── 2. the bedtime playlist ────────────────────────────────────────

def _discovery_cfg() -> dict:
    return cfg().get("discovery", {})


def ensure_playlist(token: str, state: dict) -> str | None:
    """Find (or create once) the canonical bedtime playlist. Returns
    its id, or None when the scope is not yet granted."""
    d = state.setdefault("discovery", {})
    want_title = _discovery_cfg().get("playlist_title",
                                      "Bedtime Stories for Kids to Fall Asleep")
    if d.get("playlist_id"):
        return d["playlist_id"]

    # playlists.list (mine) is read-only: works with today's scopes
    data = _get(token, f"{API_BASE}/playlists?part=snippet&mine=true"
                       f"&maxResults=25")
    for pl in data.get("items", []):
        if pl["snippet"]["title"] == want_title:
            d["playlist_id"] = pl["id"]
            ledger.save(state)
            print(f"[playlist] found existing: {want_title} ({pl['id']})")
            return pl["id"]

    if ledger.quota_remaining(state) < UNITS_PLAYLIST:
        print("[playlist] not enough quota to create — retrying next cycle")
        return None
    body = {
        "snippet": {
            "title": want_title,
            "description": _discovery_cfg().get(
                "playlist_description",
                "Calm original bedtime stories for kids — one gentle voice, "
                "soft music, no scary parts. A new sleep story every evening. "
                "Press play and let the queue do the rest. 🌙"),
        },
        "status": {"privacyStatus": "public"},
    }
    try:
        made = _send(token, f"{API_BASE}/playlists?part=snippet,status", body)
    except ScopeBlocked:
        print("[playlist] needs the one-click re-consent (RUNBOOK Part 3) "
              "— playlists skipped for now, uploads unaffected")
        return None
    except RuntimeError as e:
        print(f"[playlist] create failed: {e}")
        return None
    pid = made.get("id")
    if pid:
        d["playlist_id"] = pid
        ledger.spend_quota(state, UNITS_PLAYLIST)
        ledger.save(state)
        print(f"[playlist] created: {want_title} ({pid})")
    return pid


def _mark_playlist(state: dict, episode_n: int) -> None:
    for e in state.get("episodes", []):
        if e["n"] == episode_n:
            e.setdefault("ids", {})["playlist"] = date.today().isoformat()
            break


def add_video_to_playlist(token: str, state: dict, playlist_id: str,
                          video_id: str, episode_n: int) -> bool:
    """Idempotent add (the ledger flag is the gate, exactly like
    thumbnails). One call, 50 units, one retry."""
    if ledger.quota_remaining(state) < UNITS_PLAYLIST_ITEM:
        print("[playlist] quota low — remaining videos added next cycle")
        return False
    body = {"snippet": {"playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video",
                                       "videoId": video_id}}}
    for attempt in (1, 2):
        try:
            _send(token, f"{API_BASE}/playlistItems?part=snippet", body)
            ledger.spend_quota(state, UNITS_PLAYLIST_ITEM)
            _mark_playlist(state, episode_n)
            ledger.save(state)
            print(f"[playlist] ep{episode_n} long added ({video_id})")
            return True
        except ScopeBlocked:
            print("[playlist] needs the one-click re-consent (RUNBOOK Part 3) "
                  "— videos added automatically once granted")
            return False
        except RuntimeError as e:
            if "already" in str(e).lower() or "duplicate" in str(e).lower():
                _mark_playlist(state, episode_n)
                ledger.save(state)
                return True
            if attempt == 2:
                print(f"[playlist] add failed for ep{episode_n}: {e}")
                return False
            time.sleep(3)
    return False


def playlist_pass(token: str, state: dict) -> None:
    """Once a day, after the uploads: make sure every long video ever
    published is in the bedtime playlist."""
    # invariant first: a playlist flag without a long id is stale —
    # it was left behind when a bad adoption was undone by state
    # surgery (Oct 6: ep16's placeholder long was deleted, the flag
    # survived). Left in place, the flag would silently skip the
    # episode's REAL long when it finally uploads.
    healed = False
    for e in state.get("episodes", []):
        ids = e.get("ids") or {}
        if ids.get("playlist") and not ids.get("long"):
            ids.pop("playlist", None)
            healed = True
            print(f"[playlist] ep{e['n']}: stale playlist flag with no "
                  f"long id — cleared (the real long will be added)")
    if healed:
        ledger.save(state)
    pid = ensure_playlist(token, state)
    if not pid:
        return
    todo = [e for e in state.get("episodes", [])
            if e.get("ids", {}).get("long")
            and not e.get("ids", {}).get("playlist")]
    if not todo:
        return
    print(f"[playlist] {len(todo)} long video(s) not in the playlist yet")
    for e in todo:
        if ledger.quota_remaining(state) < UNITS_PLAYLIST_ITEM:
            print("[playlist] quota low — finishing next cycle")
            return
        add_video_to_playlist(token, state, pid, e["ids"]["long"], e["n"])


# ── 3. channel keywords ────────────────────────────────────────────

def ensure_channel_branding(token: str, state: dict) -> bool:
    """Set the channel's search keywords + description (once). Read
    current branding first (read-only scope), only rewrite what
    differs — the PUT is what needs the broader scope."""
    d = state.setdefault("discovery", {})
    if d.get("channel_branding"):
        return True

    conf = _discovery_cfg()
    keywords = conf.get("channel_keywords", [])
    kw = " ".join(f'"{k}"' for k in keywords)
    description = conf.get("channel_description", "")

    current = _get(token, f"{API_BASE}/channels?part=brandingSettings"
                          f"&mine=true")
    items = current.get("items", [])
    if not items:
        print("[branding] no channel item returned — skipping")
        return False
    branding = items[0].get("brandingSettings", {}).get("channel", {})
    if branding.get("keywords") == kw and description in branding.get("description", ""):
        d["channel_branding"] = date.today().isoformat()
        ledger.save(state)
        print("[branding] channel keywords already set — done")
        return True

    if ledger.quota_remaining(state) < UNITS_BRANDING:
        print("[branding] quota low — retrying next cycle")
        return False
    channel_id = items[0].get("id")
    new_branding = {"channel": dict(branding)}  # preserve everything else
    new_branding["channel"]["keywords"] = kw
    if description:
        new_branding["channel"]["description"] = description
    # retitle the channel to the new niche (once, with the branding pass)
    new_branding["channel"]["title"] = cfg()["channel"]["display_name"]
    try:
        # channels.update REQUIRES the channel id in the body — the
        # GET above used mine=true, but the PUT does not accept it
        # ("Id required.", HTTP 400) — learned on the first live run.
        _send(token, f"{API_BASE}/channels?part=brandingSettings",
              {"id": channel_id, "brandingSettings": new_branding},
              method="PUT")
    except ScopeBlocked:
        print("[branding] needs the one-click re-consent (RUNBOOK Part 3) "
              "— channel keywords skipped for now, uploads unaffected")
        return False
    except RuntimeError as e:
        print(f"[branding] update failed: {e}")
        return False
    ledger.spend_quota(state, UNITS_BRANDING)
    d["channel_branding"] = date.today().isoformat()
    ledger.save(state)
    print("[branding] channel keywords + description set")
    return True


# ── the daily pass, wired into the orchestrator ────────────────────

def morning_report(state: dict) -> None:
    """Start-of-day: numbers first. Failures never block production."""
    try:
        token = youtube.get_access_token()
        snapshot_views(token, state)
    except Exception as e:
        print(f"[stats] snapshot skipped: {e}")


def evening_pass(state: dict) -> None:
    """End-of-day (after uploads): playlist membership + branding."""
    try:
        token = youtube.get_access_token()
        playlist_pass(token, state)
        ensure_channel_branding(token, state)
    except Exception as e:
        print(f"[discovery] pass skipped: {e}")
