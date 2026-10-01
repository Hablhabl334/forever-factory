#!/usr/bin/env python3
"""Psychology of Love — the Forever Factory entrypoint.

    python main.py --dry-run        # produce videos + print the upload plan
    python main.py                  # full daily cycle (1 long + 4 shorts)
    python main.py --verify-token   # check YouTube credentials
"""
import sys

from src.orchestrator import main

if __name__ == "__main__":
    sys.exit(main())
