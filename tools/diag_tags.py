"""Round 2: is the invalidTags trigger the tag COUNT or the total LENGTH?

Cheap videos.update probes on ep15's long (y_9VDnn9-7k):
  control:  the video's own original 24 tags  (expect 200 — path sanity)
  +1:       25 tags                            (boundary)
  +2 long:  26 tags, ~+30 chars                (count > 25 AND length +30)
  +2 short: 26 tags, ~+10 chars                (count > 25, length +10)
  truncated: 26 tags, all cut to 6 chars       (count > 25, tiny length)

If every 26-tag probe fails regardless of length -> COUNT limit.
If short/truncated pass -> LENGTH limit.
Failures are free; successes cost 50 units; originals restored in finally.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.youtube import _post, get_access_token, API_BASE  # noqa: E402

TARGET_VIDEO = "y_9VDnn9-7k"


def get(url: str, token: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def full_error(raw: bytes) -> str:
    try:
        d = json.loads(raw)
        e = d.get("error", {})
        parts = [f"code={e.get('code')}"]
        for err in e.get("errors", []):
            parts.append(f"{err.get('reason')}@{err.get('location')}"
                         f"[{err.get('message', '')[:50]}]")
        return " ".join(parts) if parts else str(d)[:200]
    except Exception:
        return raw.decode(errors="replace")[:200]


def main() -> None:
    token = get_access_token()
    code, raw = get(f"{API_BASE}/videos?part=snippet&id={TARGET_VIDEO}", token)
    if code != 200:
        print(f"!! cannot read target video: {code}")
        return
    snip = json.loads(raw)["items"][0]["snippet"]
    orig = {
        "title": snip["title"],
        "description": snip.get("description", ""),
        "categoryId": snip.get("categoryId", "24"),
    }
    orig_tags: list = snip.get("tags", [])
    print(f"orig: {len(orig_tags)} tags, joined={len(','.join(orig_tags))} chars")

    plus_long = orig_tags + ["psychology relationship advice tips extra"]
    plus_short = orig_tags + ["love tips", "dating"]
    truncated = [t[:6].strip() or "tag" for t in orig_tags] + ["love", "date"]

    probes = [
        ("control: orig 24", orig_tags),
        ("orig +1 = 25", orig_tags + ["crush psychology"]),
        ("orig +2 long = 26", plus_long),
        ("orig +2 short = 26", plus_short),
        ("26 truncated short", truncated),
    ]
    changed = False
    try:
        for name, tset in probes:
            body = {"id": TARGET_VIDEO, "snippet": {**orig, "tags": tset}}
            qs = urllib.parse.urlencode({"part": "snippet"})
            c, _, r = _post(f"{API_BASE}/videos?{qs}",
                            json.dumps(body).encode(),
                            {"Authorization": f"Bearer {token}",
                             "Content-Type": "application/json"})
            ok = c in (200, 201)
            if ok:
                changed = True
            print(f"  [{'OK ' if ok else 'FAIL'}] {name:<22} n={len(tset):>2} "
                  f"joined={len(','.join(tset)):>3} -> {c} "
                  f"{'' if ok else full_error(r)}")
    finally:
        if changed:
            body = {"id": TARGET_VIDEO, "snippet": {**orig, "tags": orig_tags}}
            qs = urllib.parse.urlencode({"part": "snippet"})
            c, _, r = _post(f"{API_BASE}/videos?{qs}",
                            json.dumps(body).encode(),
                            {"Authorization": f"Bearer {token}",
                             "Content-Type": "application/json"})
            print(f"  restore -> {c} {'' if c in (200, 201) else full_error(r)}")


if __name__ == "__main__":
    main()
