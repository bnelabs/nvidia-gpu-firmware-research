#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
BUILD_DIR=$(mktemp -d)
trap 'rm -rf "$BUILD_DIR"' EXIT
"${CC:-cc}" -std=c11 -O2 -Wall -Wextra -Werror -o "$BUILD_DIR/test_fake" tests/test_fake_rm.c 07-prototype/fake_rm.c
"$BUILD_DIR/test_fake"
echo "synthetic payload checks passed (not hardware emulation)"
