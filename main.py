#!/usr/bin/env python3
"""Moonberry Tales — the Forever Factory entrypoint.

    python main.py --dry-run        # produce + upload plan, no upload
    python main.py                  # full daily cycle (2 stories + 3 shorts)
    python main.py --verify-token   # check YouTube credentials
"""
import sys

from src.orchestrator import main

if __name__ == "__main__":
    sys.exit(main())
