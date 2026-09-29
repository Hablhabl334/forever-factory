#!/usr/bin/env python3
"""Phase 2 of the one-click re-consent (RUNBOOK Part 3/5).

    python tools/reconsent_exchange.py <code-or-callback-URL> <base64-pubkey>

Exchanges the authorization code for a fresh refresh token with the
extended scope set (youtube.force-ssl + yt-analytics.readonly), proves
it works, and returns it SEALED — a PyNaCl sealed box encrypted to the
operator's public key. Only the ciphertext is printed, never the token.
Run inside the reconsent workflow where YT_CLIENT_ID / YT_CLIENT_SECRET
live as repository secrets.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.parse
import urllib.request

from nacl import public

REDIRECT_URI = "https://hablhabl334.github.io/oauth/callback"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def _post(data: dict) -> dict:
    req = urllib.request.Request(
        TOKEN_URL,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def main() -> None:
    pasted = sys.argv[1].strip()
    client_id = os.environ["YT_CLIENT_ID"]
    client_secret = os.environ["YT_CLIENT_SECRET"]

    # The user may paste the bare code OR the whole callback URL.
    m = re.search(r"[?&]code=([^&\s]+)", pasted)
    code = urllib.parse.unquote(m.group(1)) if m else pasted

    print("[1/4] Exchanging the authorization code ...")
    try:
        tok = _post({
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        })
    except urllib.error.HTTPError as e:
        sys.exit("ERROR: exchange failed: %s %s" % (
            e.code, e.read().decode()[:300]))
    refresh = tok.get("refresh_token")
    if not refresh:
        sys.exit("ERROR: no refresh_token in the response (Google only "
                 "issues one on a consent prompt; resp keys: %s)" %
                 sorted(tok.keys()))

    print("[2/4] Checking the granted scopes ...")
    scopes = tok.get("scope", "")
    need = ("youtube.force-ssl", "yt-analytics.readonly")
    missing = [s for s in need if s not in scopes]
    if missing:
        sys.exit("ERROR: granted scopes are missing %s — the user must "
                 "leave all permissions ticked on the consent screen" %
                 missing)

    print("[3/4] Proving the new token works (live refresh) ...")
    live = _post({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh,
        "grant_type": "refresh_token",
    })
    if "access_token" not in live:
        sys.exit("ERROR: the new refresh token did not return an "
                 "access token — do not deploy it")

    print("[4/4] Sealing the token to the operator's key ...")
    pk = public.PublicKey(base64.b64decode(sys.argv[2].strip()))
    sealed = public.SealedBox(pk).encrypt(refresh.encode())
    print("RECONSENT_OK scope=%s" % scopes)
    print("RECONSENT_CIPHERTEXT:" + base64.b64encode(sealed).decode())


if __name__ == "__main__":
    main()
