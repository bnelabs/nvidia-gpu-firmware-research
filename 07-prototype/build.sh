#!/usr/bin/env bash
# Build rmctl against the vendored open-gpu-kernel-modules public headers.
# Requires: git clone --depth 1 https://github.com/NVIDIA/open-gpu-kernel-modules vendor/open-gpu-kernel-modules
set -euo pipefail
cd "$(dirname "$0")/.."
SRC=vendor/open-gpu-kernel-modules
gcc -O2 -Wall -Wextra -o 07-prototype/rmctl 07-prototype/rmctl.c \
  -I"$SRC/src/common/sdk/nvidia/inc" \
  -I"$SRC/kernel-open/common/inc"
echo "built 07-prototype/rmctl"
