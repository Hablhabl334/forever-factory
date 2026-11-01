"""Post-publish verification — the verification-before-completion
skill, translated for the factory (batch-3 skills, 2026-11-01).

The skill's Iron Law: "no completion claims without fresh
verification evidence." The ledger's "done" only meant every id
was ACCEPTED by the upload API — never that the video actually
went public at its slot. This pass closes that gap:

* every episode from the last `scan_days` days with recorded ids
  gets its videos probed via YouTube oEmbed — anonymous, free,
  ZERO API quota;
* a video the probe SEES public is stamped in the ledger
  (ep["verified"]) — live evidence only, never blanket-true;
* a video whose episode is older than `grace_days`, is "done", and
  is STILL not public raises a VERIFY-ALERT marker line — the
  workflow's alert step greps the marker and files a dated Issue,
  exactly like the VOICE-ALERT pattern (silence is the failure
  mode this exists to kill);
* oEmbed returns non-200 both for private videos AND for public
  videos with embedding disabled — the rare unclear cases are
  settled by ONE videos.list call (1 quota unit, up to 50 ids,
  only when needed). --no-api forbids that fallback: the noon
  report runs strictly zero-quota.

Fail-open by design: any error (network, JSON, oEmbed outage)
skips quietly and retries next run — verification never starves
the grid. While a quota defer is active the grid is late ON
PURPOSE, so alerts are suppressed (stamps still happen).
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

from . import ledger
from .config import cfg

_OEMBED = "https://www.youtube.com/oembed"


def oembed_public(video_id: str) -> bool | None:
    """The zero-quota probe. True = oEmbed saw it (public).
    False = 4xx (missing, private, or embeds-disabled). None = the
    probe itself could not answer (network/5xx) — never an alert."""
    url = (f"{_OEMBED}?url=https://www.youtube.com/watch?v={video_id}"
           f"&format=json")
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (factory verify)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as exc:
        if exc.code in (400, 401, 403, 404):
            return False
        return None
    except Exception:
        return None


def _api_public(video_ids: list[str]) -> dict[str, bool]:
    """ONE videos.list call (1 unit, <=50 ids) — settles only the
    oEmbed-unclear cases (a public video with embedding disabled
    answers 401 on oEmbed). Returns {videoId: public?}."""
    from . import youtube
    token = youtube.get_access_token()
    req = urllib.request.Request(
        f"{youtube.API_BASE}/videos?part=status&id={','.join(video_ids)}",
        headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        items = json.loads(resp.read()).get("items", [])
    out: dict[str, bool] = {}
    for it in items:
        st = it.get("status", {})
        out[it["id"]] = (st.get("privacyStatus") == "public"
                         and st.get("uploadStatus") in ("processed", "uploaded"))
    return out


def _videos_of(ep: dict) -> list[tuple[str, str]]:
    """[(kind, videoId)] — kind is "long" | "short"."""
    ids = ep.get("ids") or {}
    out: list[tuple[str, str]] = []
    if ids.get("long"):
        out.append(("long", ids["long"]))
    out.extend(("short", s) for s in ids.get("shorts") or [])
    return out


def _is_verified(ep: dict, kind: str, video_id: str) -> bool:
    v = ep.get("verified") or {}
    if kind == "long":
        return bool(v.get("long"))
    return video_id in (v.get("shorts") or {})


def run(state: dict, *, no_api: bool = False,
        today: date | None = None,
        probe=oembed_public) -> dict:
    """The verification pass. Prints its report + any VERIFY-ALERT
    markers; stamps confirmed-public videos into the ledger and
    saves it when anything changed. Returns a summary dict (tests
    assert on it). Never raises.

    Three phases, deliberately ordered:
      1. probe — oEmbed, zero quota, per video;
      2. settle — ONE batched videos.list (1 unit) only for the
         oEmbed-unclear cases;
      3. alert — "late" is declared per-episode (done + older than
         grace_days + still not public + no active defer)."""
    conf = (cfg().get("verify") or {})
    if not conf.get("enabled", True):
        print("[verify] disabled in channel.yaml — skipping")
        return {"confirmed": 0, "late": 0, "unknown": 0, "alerts": []}
    grace_days = int(conf.get("grace_days", 2))
    scan_days = int(conf.get("scan_days", 10))
    today = today or date.today()
    cutoff = today - timedelta(days=scan_days)

    q = state.get("quota") or {}
    defer_active = (q.get("defer_until") or 0) > time.time()

    confirmed = late = unknown = 0
    alerts: list[str] = []
    dirty = False
    # every oEmbed-unclear video, kept with its OWN episode's facts
    not_public: list[tuple[dict, str, str, int]] = []   # (ep, kind, vid, age)

    try:
        recent = [e for e in state.get("episodes", [])
                  if isinstance(e.get("ids"), dict)
                  and (e["ids"].get("long") or e["ids"].get("shorts"))
                  and date.fromisoformat(e.get("date") or "1970-01-01")
                  >= cutoff]
    except (TypeError, ValueError):
        recent = []

    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # ── phase 1: the zero-quota probe ────────────────────────────
    for ep in recent:
        try:
            ep_date = date.fromisoformat(ep.get("date") or "")
        except ValueError:
            continue
        age_days = (today - ep_date).days
        for kind, vid in _videos_of(ep):
            if _is_verified(ep, kind, vid):
                confirmed += 1          # stamped on a previous pass
                continue
            verdict = probe(vid)
            if verdict is True:
                ledger.mark_verified(state, ep["n"], kind, vid, now_iso)
                confirmed += 1
                dirty = True
            elif verdict is False:
                not_public.append((ep, kind, vid, age_days))
            else:
                unknown += 1            # probe blind this run — no alert

    # ── phase 2: settle the unclear cases, ONE API call ──────────
    api_ok: dict[str, bool] = {}
    if not_public and not no_api and conf.get("fallback_api", True) \
            and ledger.quota_remaining(state) > 200:
        try:
            api_ok = _api_public([v for _, _, v, _ in not_public[:50]])
            ledger.spend_quota(state, 1)
            dirty = True
        except Exception as exc:
            print(f"[verify] API fallback skipped ({exc})")

    # ── phase 3: stamp the settled, alert the genuinely late ─────
    for ep, kind, vid, age_days in not_public:
        if api_ok.get(vid):
            ledger.mark_verified(state, ep["n"], kind, vid, now_iso)
            confirmed += 1
            dirty = True
            continue
        if (ep.get("status") == "done" and age_days > grace_days
                and not defer_active):
            late += 1
            line = (f"VERIFY-ALERT: ep{ep['n']} "
                    f"'{(ep.get('title') or '')[:40]}' — {vid} still "
                    f"not public {age_days}d after production (slot "
                    f"missed, stuck private, or removed)")
            alerts.append(line)
            print(line)

    if unknown:
        print(f"[verify] {unknown} video(s) not answerable this pass "
              f"(probe unavailable) — retried next run")
    if defer_active:
        print("[verify] quota defer active — alerts suppressed, "
              "stamps still collected")
    print(f"[verify] {confirmed} video(s) confirmed public, "
          f"{late} late past the {grace_days}-day grace window")

    if dirty:
        try:
            ledger.save(state)
        except Exception as exc:
            print(f"[verify] ledger save skipped ({exc})")
    return {"confirmed": confirmed, "late": late, "unknown": unknown,
            "alerts": alerts}
