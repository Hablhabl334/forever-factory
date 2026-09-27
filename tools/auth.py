#!/usr/bin/env python3
"""One-time YouTube OAuth connection — prints the link, takes the code,
exchanges it for the forever refresh token.

    python tools/auth.py

Paste your client_id and client_secret (from the Google Cloud
Web-application OAuth client) when asked. Open the printed link in a
browser, sign in with the channel's Google account, click Allow — you
will land on https://hablhabl334.github.io/oauth/callback which shows
your authorization code. Paste that code (or the whole URL) back here.
The refresh token it prints goes into the GitHub secret
YT_REFRESH_TOKEN (see RUNBOOK.md).
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
REDIRECT_URI = "https://hablhabl334.github.io/oauth/callback"


def main() -> None:
    client_id = input("client_id: ").strip()
    client_secret = input("client_secret: ").strip()

    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    print("\n1. Open this link in your browser:\n")
    print(url)
    print("\n2. Sign in with the Google account that owns the channel, click Allow.")
    print("   You will land on the Moonberry Factory page on hablhabl334.github.io")
    print("   which shows your code — use its Copy button.")
    pasted = input("\n3. Paste the code (or the whole callback URL) here: ").strip()

    # The user may paste the bare code OR the full redirect URL containing it.
    m = re.search(r"[?&]code=([^&\s]+)", pasted)
    code = urllib.parse.unquote(m.group(1)) if m else pasted

    data = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        out = json.loads(resp.read())

    print("\nSuccess. Your forever refresh token:\n")
    print(out["refresh_token"])
    print("\nNow set the GitHub repo secrets:")
    print("  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN")
    print("Then run the workflow 'verify-token' to confirm.")


if __name__ == "__main__":
    main()
