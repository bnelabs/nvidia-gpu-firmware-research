#!/usr/bin/env bash
# Host writes only new output files; analysis is isolated by run_cpu_only.sh.
set -euo pipefail
cd "$(dirname "$0")/../.."
DEST=${1:?provide a NEW output directory}
MODE=${2:---with-checks}
case "$MODE" in --with-checks|--json-only) ;; *) exit 2 ;; esac
mkdir "$DEST"
PACKET=research/2026-10-21-object-origin
EXPORT=research/2026-10-21-pstate-writers/export_ranges.py
bash scripts/run_cpu_only.sh python3 "$PACKET/extract_metadata.py" > "$DEST/metadata.json"
bash scripts/run_cpu_only.sh python3 "$EXPORT" \
  0x140dc08:0x140dc8a 0x140df90:0x140e030 0x1407d4c:0x1407ec0 \
  0x1a0fedc:0x1a0ffd2 0x1a032e4:0x1a03314 \
  0x1667db8:0x1667e54 0x1668500:0x1668590 > "$DEST/object-route.json"
bash scripts/run_cpu_only.sh python3 "$EXPORT" \
  0x1be9250:0x1beae88 \
  0x1765820:0x1765f10 \
  0x1688714:0x1689110 > "$DEST/table-factory.json"
bash scripts/run_cpu_only.sh python3 "$EXPORT" \
  0x1b0a2c0:0x1b0a38a 0x1b0a460:0x1b0a52c \
  0x175fb8c:0x175fbb2 0x167e4e0:0x167e506 \
  0x1757ea0:0x1757f38 0x167de40:0x167de9e 0x16be978:0x16be9c6 > "$DEST/table-getter.json"
bash scripts/run_cpu_only.sh python3 "$EXPORT" \
  0x1767128:0x1767236 0x1768dd4:0x1768e10 \
  0x16870d4:0x1687c70 0x1680c20:0x1680d94 \
  0x17610dc:0x1761154 0x1760fd0:0x1761006 \
  0x17655b0:0x1765634 > "$DEST/entry-writer.json"
bash scripts/run_cpu_only.sh python3 "$PACKET/emulate_origin.py" > "$DEST/emulation.json"
bash scripts/run_cpu_only.sh python3 "$PACKET/make_manifest.py" > "$DEST/source-manifest.json"
if [[ "$MODE" == --with-checks ]]; then
  bash scripts/run_cpu_only.sh /bin/bash tests/check.sh > "$DEST/check.log" 2>&1
fi
