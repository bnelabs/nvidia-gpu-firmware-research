#!/usr/bin/env bash
# run_sniff_tests.sh — build + run packet-A tracer acceptance tests (no GPU needed).
# Rebuilds from source; never trusts tracked binaries.
set -euo pipefail
cd "$(dirname "$0")/.."
gcc -O2 -Wall -Wextra -o /tmp/t_sniff tests/test_sniff_decode.c 07-prototype/sniffer2.c -ldl
/tmp/t_sniff
