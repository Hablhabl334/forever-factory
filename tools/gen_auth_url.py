#!/usr/bin/env python3
"""Print the YouTube consent URL (with the full scope set from
tools/auth.py) for the one-click re-consent — RUNBOOK Part 5.

    python tools/gen_auth_url.py <client_id>
"""
from __future__ import annotations

import sys
import urllib.parse

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from auth import SCOPES, REDIRECT_URI  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    params = {
        "client_id": sys.argv[1],
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + \
        urllib.parse.urlencode(params)
    print("\nOpen this link, sign in with the channel's Google account, "
          "click Allow:\n\n" + url + "\n\nThen paste the code from the "
          "callback page back to the assistant (or into tools/auth.py).")


if __name__ == "__main__":
    main()
