#!/usr/bin/env python3
"""List the channel's current uploads — the factory's window onto YouTube.

    python tools/channel_check.py

Shows every video on the channel with id, title, privacy status and
publish time. Used to verify uploads landed and to spot orphans.
"""
import json
import sys
import urllib.request

sys.path.insert(0, ".")
from src.youtube import API_BASE, get_access_token


def main() -> int:
    token = get_access_token()
    req = urllib.request.Request(
        f"{API_BASE}/channels?part=snippet,contentDetails&mine=true",
        headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        ch = json.loads(resp.read())["items"][0]
    print(f"channel: {ch['snippet']['title']}  ({ch['id']})")
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]

    req = urllib.request.Request(
        f"{API_BASE}/playlistItems?part=snippet,status&playlistId={uploads}"
        f"&maxResults=50",
        headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        items = json.loads(resp.read()).get("items", [])

    if not items:
        print("no uploads yet")
        return 0
    for it in items:
        s, st = it["snippet"], it.get("status", {})
        print(f"{s['resourceId']['videoId']} | {st.get('privacyStatus', '?'):8} | "
              f"{s['title'][:64]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
