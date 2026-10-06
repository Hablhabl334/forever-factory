"""Bisect today's invalidTags 400 (ep16 long upload) against the live API.

Phase 1 — cheap probes via videos.update (50 units only on success,
           failures are free) on yesterday's long video y_9VDnn9-7k:
           send different tag subsets, watch which ones 400.
           Original tags are restored in a finally block.

Phase 2 — exact resumable-upload INIT probes (the failing call itself).
           A failed init is free; we stop at the first success so at
           most one session is ever created (and then abandoned —
           no video is ever PUT, so nothing lands on the channel).

Run from the repo root:  python tools/diag_tags.py
Needs YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN in env.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.youtube import _post, get_access_token, API_BASE, UPLOAD_URL  # noqa: E402
from src.story_engine import generate_story  # noqa: E402
from src.metadata import _tag_list  # noqa: E402
from src import ledger  # noqa: E402

TARGET_VIDEO = "y_9VDnn9-7k"      # ep15's long — public, owned by the app
EP16_SEED = 50248005129956
EP16_HASH = "c287cabb25fc2366"


def get(url: str, token: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def reason_of(raw: bytes) -> str:
    try:
        d = json.loads(raw)
        errs = d.get("error", {}).get("errors", [])
        if errs:
            return f"{d['error'].get('code')} {errs[0].get('reason')} | {errs[0].get('message', '')[:60]}"
        return str(d)[:80]
    except Exception:
        return raw.decode(errors="replace")[:80]


def ep16_tags() -> list[str]:
    state = ledger.load()
    used = set(state.get("story_hashes", [])) - {EP16_HASH}
    story = generate_story(EP16_SEED, used, set())
    assert story["hash"] == EP16_HASH, f"story drifted: {story['hash']}"
    return _tag_list(story)


def phase1_update_probes(token: str) -> None:
    print("=" * 70)
    print("PHASE 1 — videos.update probes (failures free, success = 50 units)")
    print("=" * 70)
    code, raw = get(f"{API_BASE}/videos?part=snippet&id={TARGET_VIDEO}", token)
    if code != 200:
        print(f"  !! cannot read target video: {code} {reason_of(raw)}")
        return
    snip = json.loads(raw)["items"][0]["snippet"]
    orig = {
        "title": snip["title"],
        "description": snip.get("description", ""),
        "categoryId": snip.get("categoryId", "24"),
    }
    orig_tags = snip.get("tags", [])
    print(f"  target: {TARGET_VIDEO} | orig title: {orig['title'][:60]!r}")
    print(f"  orig tags ({len(orig_tags)}): {orig_tags}")

    tags = ep16_tags()
    concepts, pool = tags[:8], tags[8:]
    probes = [
        ("ep16 all 26", tags),
        ("ep16 concepts (8)", concepts),
        ("ep16 pool (18)", pool),
        ("ep16 first 13", tags[:13]),
        ("ep16 last 13", tags[13:]),
        ("single tag", ["psychology of love"]),
        ("empty list", []),
    ]
    changed = False
    try:
        for name, tset in probes:
            body = {"id": TARGET_VIDEO, "snippet": {**orig, "tags": tset}}
            qs = urllib.parse.urlencode({"part": "snippet"})
            code, _, raw = _post(f"{API_BASE}/videos?{qs}",
                                 json.dumps(body).encode(),
                                 {"Authorization": f"Bearer {token}",
                                  "Content-Type": "application/json"})
            mark = "OK " if code in (200, 201) else "FAIL"
            print(f"  [{mark}] {name:<20} -> {code} {reason_of(raw) if code not in (200, 201) else ''}")
            if code in (200, 201):
                changed = True
    finally:
        if changed:
            body = {"id": TARGET_VIDEO, "snippet": {**orig, "tags": orig_tags}}
            qs = urllib.parse.urlencode({"part": "snippet"})
            code, _, raw = _post(f"{API_BASE}/videos?{qs}",
                                 json.dumps(body).encode(),
                                 {"Authorization": f"Bearer {token}",
                                  "Content-Type": "application/json"})
            print(f"  restore original tags -> {code} {reason_of(raw) if code not in (200, 201) else 'done'}")


def phase2_init_probes(token: str, tags: list[str]) -> None:
    print()
    print("=" * 70)
    print("PHASE 2 — resumable INIT probes (exact failing call; stop at first 200)")
    print("=" * 70)
    base_snip = {
        "title": "Relationship Psychology: Green Flags Everyone Misses | Love Tips That Work",
        "description": ("Psychology of love explained in plain words — 8 lessons on "
                        "green flags everyone misses. Relationship tips that actually "
                        "change how you love.\n\n#psychology #love #relationship"),
        "categoryId": "24",
        "defaultLanguage": "en",
        "defaultAudioLanguage": "en",
    }
    status = {
        "privacyStatus": "private",
        "madeForKids": False,
        "selfDeclaredMadeForKids": False,
        "publishAt": "2026-10-07T20:00:00+03:00",
        "containsSyntheticMedia": True,
    }
    chapters = [f"{m}:{s:02d} Tip {i+1}: green flags lesson" for i, (m, s)
                in enumerate([(0, 0), (0, 6), (1, 12), (2, 18), (3, 24),
                              (4, 30), (5, 36), (6, 42), (7, 48)])]
    variants = [
        ("A: exact body (tags+chapters)", {**base_snip, "tags": tags, "chapters": chapters}),
        ("B: body MINUS tags",           {**base_snip, "chapters": chapters}),
        ("C: body MINUS chapters",       {**base_snip, "tags": tags}),
        ("D: minimal (no tags/chapters)", dict(base_snip)),
    ]
    qs = urllib.parse.urlencode({"uploadType": "resumable", "part": "snippet,status"})
    for name, snip in variants:
        body = {"snippet": snip, "status": status}
        code, headers, raw = _post(f"{UPLOAD_URL}?{qs}",
                                   json.dumps(body).encode(),
                                   {"Authorization": f"Bearer {token}",
                                    "Content-Type": "application/json",
                                    "X-Upload-Content-Length": "1000"})
        ok = code in (200, 201)
        print(f"  [{'OK ' if ok else 'FAIL'}] {name:<32} -> {code} {'' if ok else reason_of(raw)}")
        if ok:
            print("      session created and abandoned (no bytes PUT) — stopping probes")
            break


def main() -> None:
    token = get_access_token()
    tags = ep16_tags()
    print(f"ep16 tags ({len(tags)}, {sum(len(t) for t in tags)} chars): {tags}")
    print()
    phase1_update_probes(token)
    phase2_init_probes(token, tags)
    print()
    print("DIAG DONE")


if __name__ == "__main__":
    main()
