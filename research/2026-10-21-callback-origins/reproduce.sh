#!/usr/bin/env bash
# Each analysis runs without network/devices/services; only host output files vary.
set -euo pipefail
cd "$(dirname "$0")/../.."
DEST=${1:?provide a NEW output directory}
mkdir "$DEST"
PACKET=research/2026-10-21-callback-origins
EXPORT=research/2026-10-21-pstate-writers/export_ranges.py
bash scripts/run_cpu_only.sh /usr/bin/python3 research/2026-10-21-pstate-writers/scan_stores.py 0x1c0 > "$DEST/control-store-candidates.json"
# Context scanner reads the regenerated candidate bytes through a private file.
bash scripts/run_cpu_only.sh /bin/bash -c '
cat > /tmp/control-candidates.json
/usr/bin/python3 research/2026-10-21-callback-origins/scan_contexts.py /tmp/control-candidates.json
' < "$DEST/control-store-candidates.json" > "$DEST/control-store-contexts.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 "$EXPORT" 0x1426b30:0x1426c10 0x144b3b0:0x144b420 0x1466470:0x14664e0 0x14842e0:0x1484380 0x14845e0:0x1484650 > "$DEST/control-candidates-01.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 "$EXPORT" 0x1aea640:0x1aea850 0x14078cc:0x1407cb0 > "$DEST/control-assignment-01.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 "$EXPORT" 0x18eb54c:0x18eb67c 0x1aea300:0x1aea410 > "$DEST/method-lookup.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 "$EXPORT" 0x166c900:0x166ca10 0x167aef0:0x167b060 0x1688750:0x1688840 > "$DEST/entry-candidates-01.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 "$PACKET/scan_addi.py" 0x320 > "$DEST/table-address-candidates.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 "$PACKET/emulate_dispatch.py" > "$DEST/dispatch-emulation.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 "$PACKET/check_rmapi_layout.py" > "$DEST/rmapi-layout.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 "$PACKET/check_method_lookup.py" > "$DEST/method-lookup-check.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 "$PACKET/make_manifest.py" > "$DEST/source-manifest.json"
bash scripts/run_cpu_only.sh /bin/bash tests/check.sh > "$DEST/check.log" 2>&1
