#!/usr/bin/env bash
# Run from the host; each computation gets a read-only CPU-only namespace.
set -euo pipefail
cd "$(dirname "$0")/../.."
DEST=${1:?provide a NEW output directory}
mkdir "$DEST"
PACKET=research/2026-10-21-pstate-dispatch
bash scripts/run_cpu_only.sh /usr/bin/python3 "$PACKET/make_manifest.py" > "$DEST/source-manifest.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 scripts/extract_nvoc_exports.py firmware-store/gsp-kernels/615-kernel-10.elf --class-def-va 0x1c64e70 --source-root vendor/open-gpu-kernel-modules-615.71.09 > "$DEST/gsp-subdevice-exports.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 "$PACKET/export_evidence.py" > "$DEST/raw-evidence.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 "$PACKET/emulate_rusd.py" > "$DEST/rusd-emulation.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 "$PACKET/emulate_transport_boundary.py" > "$DEST/transport-emulation.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 "$PACKET/emulate_firmware_poll.py" > "$DEST/firmware-poll-emulation.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 "$PACKET/emulate_firmware_pstate.py" > "$DEST/firmware-pstate-emulation.json"
bash scripts/run_cpu_only.sh /bin/bash -c '
cc -std=c11 -O2 -Wall -Wextra -Werror -isystem vendor/open-gpu-kernel-modules-615.71.09/src/common/sdk/nvidia/inc research/2026-10-21-pstate-dispatch/layout.c -o /tmp/pstate-layout
/tmp/pstate-layout
' > "$DEST/layout.json"
bash scripts/run_cpu_only.sh /bin/bash tests/check.sh > "$DEST/check.log" 2>&1
