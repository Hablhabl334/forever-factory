"""Round 4: CLEANUP — inspect and delete the 9 placeholder videos my
diagnostic rounds accidentally created (POST to /videos = insert, not
update; plus the abandoned resumable init). All are zero-duration
private-or-unknown artifacts that must never reach the public grid.

Reads statuses first (1 unit), then deletes each (50 units/video).
Stops gracefully if the real daily quota is exhausted.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.youtube import _post, get_access_token, API_BASE  # noqa: E402

# every accidental artifact, newest first
PLACEHOLDERS = [
    "ah_WeI-XV-A",   # round-2 probe
    "vjddf9uhF7I",   # round-2 probe
    "YDaZ_dRb5_8",   # init-B artifact, WRONGLY adopted as ep16 long
    "O1j-fTfvBtM",   # round-1 probe
    "WomK0DK3DNY",   # round-1 probe
    "LD2-vRa6Ax8",   # round-1 probe
    "YuduIwMGfC4",   # round-1 probe
    "bS7_kGc8mEI",   # round-1 probe
    "iTEdarEGo64",   # round-1 probe
]
KEEP = {"EYP4N0ZEMNo"}  # the real ep16 short 1


def get(url: str, token: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def delete(vid: str, token: str) -> tuple[int, bytes]:
    """videos.delete — a real HTTP DELETE (the POST-vs-PUT-vs-DELETE
    confusion is exactly what created these placeholders)."""
    import urllib.parse
    qs = urllib.parse.urlencode({"id": vid})
    req = urllib.request.Request(f"{API_BASE}/videos?{qs}",
                                 headers={"Authorization": f"Bearer {token}"},
                                 method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main() -> None:
    token = get_access_token()

    ids = ",".join(PLACEHOLDERS)
    code, raw = get(f"{API_BASE}/videos?part=status,contentDetails,snippet&id={ids}",
                    token)
    print(f"== status check -> {code} ==")
    if code == 200:
        found = {v["id"]: v for v in json.loads(raw).get("items", [])}
        for vid in PLACEHOLDERS:
            v = found.get(vid)
            if not v:
                print(f"  {vid}: NOT FOUND (already gone?)")
                continue
            st, cd, sn = v["status"], v["contentDetails"], v["snippet"]
            print(f"  {vid}: privacy={st.get('privacyStatus')} "
                  f"publishAt={st.get('publishAt', '-')} "
                  f"duration={cd.get('duration')} "
                  f"uploadStatus={st.get('uploadStatus')} "
                  f"title={sn['title'][:40]!r}")
    else:
        print("  raw:", raw.decode()[:300])

    print("== deleting ==")
    for vid in PLACEHOLDERS:
        if vid in KEEP:
            continue
        c, r = delete(vid, token)
        ok = c in (200, 201, 204)
        print(f"  delete {vid} -> {c} {'OK' if ok else r.decode()[:150]}")
        if c == 403 and b"quota" in r.lower():
            print("  !! real daily quota exhausted — stopping; retry after "
                  "the 07:00 UTC reset")
            break


if __name__ == "__main__":
    main()
