#!/usr/bin/env bash
# Entire gate is CPU-only. No vendor driver, device node or hardware is needed.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v
bash tests/run_sniff_tests.sh
bash tests/test_fake_rm.sh
BUILD_DIR=$(mktemp -d)
trap 'rm -rf "$BUILD_DIR"' EXIT
"${CC:-cc}" -std=c11 -O2 -Wall -Wextra -Werror -o "$BUILD_DIR/pstate" tests/test_pstate_decode.c
"$BUILD_DIR/pstate"
"${CC:-cc}" -std=c11 -O2 -Wall -Wextra -Werror -o "$BUILD_DIR/rmctl" 07-prototype/rmctl.c
"$BUILD_DIR/rmctl" --offline-pstate 4
if "$BUILD_DIR/rmctl" --live >/dev/null 2>&1; then echo 'FAIL: live mode accepted'; exit 1; fi
if "$BUILD_DIR/rmctl" --offline-raw /dev/null >/dev/null 2>&1; then echo 'FAIL: device input accepted'; exit 1; fi
"${CC:-cc}" -std=c11 -O2 -Wall -Wextra -Werror -o "$BUILD_DIR/retired" 07-prototype/nvml_pstate_probe.c
if "$BUILD_DIR/retired" >/dev/null 2>&1; then echo 'FAIL: retired probe accepted'; exit 1; fi
for script in scripts/*.sh tests/*.sh 07-prototype/build.sh; do bash -n "$script"; done
echo 'CPU-only gate passed; no GPU validation performed'
