#!/usr/bin/env bash
# Output paths are host regular files; all analysis executes in CPU-only namespaces.
set -euo pipefail
cd "$(dirname "$0")/../.."
DEST=${1:?provide a NEW output directory outside existing evidence}
mkdir "$DEST"
bash scripts/run_cpu_only.sh /usr/bin/python3 research/2026-10-21-offline/export_host.py > "$DEST/host-evidence.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 scripts/emulate_pstate_conversion.py firmware-store/gsp-kernels/libnvidia-ml-615.71.09.so > "$DEST/pstate-emulation.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 scripts/compare_ga102_boot.py vendor/research-sources/61dcc93722ecb418bb5f2e00923f05b4b8051dd1/g_bindata_kgspGetBinArchiveGspRmBoot_GA102.c vendor/open-gpu-kernel-modules/src/nvidia/generated/g_bindata_kgspGetBinArchiveGspRmBoot_GA102.c > "$DEST/ga102-boot-comparison.json"
bash scripts/run_cpu_only.sh /usr/bin/python3 research/2026-10-21-offline/disassemble_boot.py > "$DEST/ga102-boot-disassembly.json"
bash scripts/run_cpu_only.sh /bin/bash tests/check.sh > "$DEST/check.log" 2>&1
