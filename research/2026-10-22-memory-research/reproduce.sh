#!/usr/bin/env bash
set -euo pipefail
MEMORY_REVIEW_TMP=$(mktemp -d)
trap 'rm -rf "$MEMORY_REVIEW_TMP"' EXIT
python3 research/2026-10-22-memory-research/review.py > "$MEMORY_REVIEW_TMP/review.json"
cmp "$MEMORY_REVIEW_TMP/review.json" research/2026-10-22-memory-research/review.json
printf '%s\n' 'Pinned file utilities and NVIDIA queue layouts reproduced with synthetic CPU-only inputs.'
