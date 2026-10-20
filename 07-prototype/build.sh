#!/usr/bin/env bash
# Build only offline file/enum tools. No driver linking or vendor checkout needed.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build
"${CC:-cc}" -std=c11 -O2 -Wall -Wextra -Werror -o build/rmctl 07-prototype/rmctl.c
echo "built build/rmctl (offline only; no device or ioctl transport)"
