#!/usr/bin/env python3
"""Verify YouTube credentials (the three repo secrets) in seconds."""
import sys
sys.path.insert(0, ".")

from src.youtube import verify_credentials

out = verify_credentials()
print(out)
sys.exit(0 if out.get("ok") else 1)
