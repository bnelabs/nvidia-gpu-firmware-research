#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
BUILD_DIR=$(mktemp -d)
trap 'rm -rf "$BUILD_DIR"' EXIT
"${CC:-cc}" -std=c11 -O2 -Wall -Wextra -Werror -o "$BUILD_DIR/test_sniff" tests/test_sniff_decode.c 07-prototype/sniffer2.c
"$BUILD_DIR/test_sniff"
