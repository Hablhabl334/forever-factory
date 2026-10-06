"""Round 3: inspect the adopted 'long' video YDaZ_dRb5_8 — is it a real
609s video or an empty artifact from the abandoned init session?"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.youtube import get_access_token, API_BASE  # noqa: E402


def get(url: str, token: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main() -> None:
    token = get_access_token()

    # 1. the adopted long — full state
    code, raw = get(f"{API_BASE}/videos?part=snippet,status,contentDetails"
                    f"&id=YDaZ_dRb5_8", token)
    print(f"== YDaZ_dRb5_8 (adopted ep16 long) -> {code} ==")
    if code == 200:
        v = json.loads(raw)["items"][0]
        sn, st, cd = v["snippet"], v["status"], v["contentDetails"]
        print("  title:", sn["title"])
        print("  desc len:", len(sn.get("description", "")),
              "| first 90:", sn.get("description", "")[:90].replace("\n", " / "))
        print("  tags:", sn.get("tags", "NONE"))
        print("  duration:", cd.get("duration"), "| dimension:", cd.get("dimension"))
        print("  privacy:", st.get("privacyStatus"), "| publishAt:", st.get("publishAt"))
        print("  uploadStatus:", st.get("uploadStatus"), "| madeForKids:", st.get("madeForKids"))
    else:
        print("  raw:", raw.decode()[:300])

    # 2. the one uploaded short
    code, raw = get(f"{API_BASE}/videos?part=snippet,status,contentDetails"
                    f"&id=EYP4N0ZEMNo", token)
    print(f"== EYP4N0ZEMNo (ep16 short 1) -> {code} ==")
    if code == 200:
        v = json.loads(raw)["items"][0]
        sn, st, cd = v["snippet"], v["status"], v["contentDetails"]
        print("  title:", sn["title"])
        print("  duration:", cd.get("duration"))
        print("  privacy:", st.get("privacyStatus"), "| publishAt:", st.get("publishAt"))
        print("  uploadStatus:", st.get("uploadStatus"))

    # 3. recent uploads (last 12) — ids + titles + publishAt
    code, raw = get(f"{API_BASE}/channels?part=contentDetails&mine=true", token)
    up = json.loads(raw)["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    code, raw = get(f"{API_BASE}/playlistItems?part=snippet,contentDetails"
                    f"&playlistId={up}&maxResults=12", token)
    print(f"== latest uploads -> {code} ==")
    for it in json.loads(raw).get("items", []):
        s = it["snippet"]
        print(f"  {s['resourceId']['videoId']} | {s['title'][:55]!r} "
              f"| published {s['publishedAt']}")


if __name__ == "__main__":
    main()
