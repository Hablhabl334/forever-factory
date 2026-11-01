#!/usr/bin/env python3
"""Post-publish verification, standalone (batch-3 skills).

    python tools/verify_public.py [--no-api]

The same pass the produce cycle runs at its start (src/verify.py):
probe every recent video via the free oEmbed endpoint, stamp the
confirmed-public ones into the ledger, and print VERIFY-ALERT
markers for completed episodes whose videos are still not public
past the grace window. Exit code is ALWAYS 0 — alerts are marker
lines for the workflow's Issue-filing step, not a failure state.

--no-api: forbid the 1-unit Data API fallback (the noon report and
any diagnostics run strictly zero-quota).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import ledger, verify          # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-api", action="store_true",
                    help="never spend quota: oEmbed only")
    args = ap.parse_args()

    state = ledger.load()
    verify.run(state, no_api=args.no_api)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
