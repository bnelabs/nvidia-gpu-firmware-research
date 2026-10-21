#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
DEST=${1:?provide a NEW output directory}
MODE=${2:---with-checks}
case "$MODE" in --with-checks|--json-only) ;; *) exit 2 ;; esac
mkdir "$DEST"
PACKET=research/2026-10-21-record-producer
EXPORT=research/2026-10-21-pstate-writers/export_ranges.py
bash scripts/run_cpu_only.sh python3 "$PACKET/extract_layout.py" > "$DEST/layout.json"
bash scripts/run_cpu_only.sh python3 "$EXPORT" \
  0x1688876:0x168893a 0x1767128:0x1767318 0x1779308:0x177936e \
  0x176b2a8:0x176b4b8 0x17678c8:0x1768240 > "$DEST/parser-selection.json"
bash scripts/run_cpu_only.sh python3 "$EXPORT" \
  0x1767c28:0x1767d0a 0x17615d4:0x17616a4 \
  0x1768dd4:0x1768e10 0x1688990:0x168899c > "$DEST/record-pointer.json"
bash scripts/run_cpu_only.sh python3 "$EXPORT" \
  0x176b4b8:0x176b564 0x1b0a0ec:0x1b0a2c0 \
  0x1839700:0x183983c 0x1839598:0x1839700 \
  0x140b7ac:0x140bd80 0x17776c4:0x177790c > "$DEST/descriptor-boundary.json"
bash scripts/run_cpu_only.sh python3 "$EXPORT" \
  0x175fb8c:0x175fbb2 0x175f270:0x175f43c 0x1ba12b4:0x1ba1378 \
  0x1764048:0x17640a8 0x1760c24:0x1760ce4 \
  0x17612a4:0x1761358 > "$DEST/mask-helpers.json"
bash scripts/run_cpu_only.sh python3 "$PACKET/emulate_records.py" > "$DEST/emulation.json"
bash scripts/run_cpu_only.sh python3 "$PACKET/make_manifest.py" > "$DEST/source-manifest.json"
if [[ "$MODE" == --with-checks ]]; then
  bash scripts/run_cpu_only.sh bash tests/check.sh > "$DEST/check.log" 2>&1
fi
