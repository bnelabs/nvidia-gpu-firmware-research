#!/usr/bin/env bash
# Default: print the documented monitoring plan; no hardware access.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/scripts/capture_state.py" "$@"
