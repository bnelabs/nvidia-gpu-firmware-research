#!/usr/bin/env python3
"""Compatibility entry point for the fixed documented collector. Default: no GPU."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from capture_state import main

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--dry-run" in args:
        if "--live" in args:
            raise SystemExit("--dry-run cannot be combined with --live")
        args = [arg for arg in args if arg != "--dry-run"]
    raise SystemExit(main(args))
