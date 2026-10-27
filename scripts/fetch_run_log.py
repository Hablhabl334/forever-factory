#!/usr/bin/env python3
"""Redirect-aware GitHub Actions log fetcher for the factory repo.

The actions/jobs/{id}/logs endpoint 302s to a pre-signed Azure URL;
urllib re-sends the Authorization header there, which breaks the
signature (403). This fetcher follows the redirect MANUALLY and
fetches the signed URL with clean headers (the same lesson as
scripts/voice_audit.py's log fetch, wrapped as a reusable tool).

    python3 scripts/fetch_run_log.py <run_id>
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path("/home/z/my-project/download/forever-factory")


def _tok() -> str:
    return re.search(r"x-access-token:([^@]+)@github.com",
                     (ROOT / ".git" / "config").read_text()).group(1)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never auto-follow: the redirect target is pre-signed and must
    be fetched with CLEAN headers (auto-follow re-sends Authorization
    and breaks the signature — the original 403)."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _get(url: str, headers: dict, timeout: int = 60):
    try:
        return _OPENER.open(urllib.request.Request(url, headers=headers),
                            timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307) and e.headers.get("Location"):
            # pre-signed redirect: fetch with NO auth header
            return urllib.request.urlopen(e.headers["Location"],
                                          timeout=timeout)
        raise


def main() -> int:
    run_id = sys.argv[1]
    h = {"Authorization": f"token {_tok()}",
         "Accept": "application/vnd.github+json"}
    jobs = json.load(_get(
        f"https://api.github.com/repos/Hablhabl334/forever-factory"
        f"/actions/runs/{run_id}/jobs", h))["jobs"]
    out = []
    for j in jobs:
        out.append(f"JOB: {j['name']} -> {j['conclusion']}")
        for s in j.get("steps", []):
            out.append(f"   {s['name']!r:52s} {s['conclusion']}")
        try:
            resp = _get(
                f"https://api.github.com/repos/Hablhabl334/forever-factory"
                f"/actions/jobs/{j['id']}/logs", h, timeout=120)
            log = resp.read().decode("utf-8", "replace")
            path = Path(f"/home/z/my-project/scripts/"
                        f"job_{j['id']}_log.txt")
            path.write_text(log)
            out.append(f"   log -> {path} ({len(log)} chars)")
        except Exception as exc:
            out.append(f"   log fetch failed: {exc}")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
