#!/usr/bin/env bash
# test_fake_rm.sh — run rmctl against the deterministic fake-RM backend (offline, no GPU).
# Acceptance per RESEARCH-DIRECTION: syscall failures, RM failures, changing outputs,
# stale-input rejection.
set -u
cd "$(dirname "$0")/.."
gcc -O2 -Wall -fPIC -shared -o 07-prototype/fake_rm.so 07-prototype/fake_rm.c -ldl || exit 1
gcc -O2 -Wall -o 07-prototype/rmctl 07-prototype/rmctl.c \
  -Ivendor/open-gpu-kernel-modules/src/common/sdk/nvidia/inc \
  -Ivendor/open-gpu-kernel-modules/kernel-open/common/inc || exit 1

fails=0
check() { if echo "$2" | grep -q "$1"; then echo "ok   $3"; else echo "FAIL $3"; fails=$((fails+1)); fi; }

# 1. happy path: full probe sequence against the fixture
OUT=$(LD_PRELOAD=$PWD/07-prototype/fake_rm.so ./07-prototype/rmctl 2>&1); RV=$?
check "615.71.09-fake (reply=1)" "$OUT" "fixture version handshake"
check "gsp.firmwareVersion.*615.71.09-fake" "$OUT" "fixture GSP build string"
check "pmumon.samplesReturned.*250" "$OUT" "PMUMON deterministic count"
check "last gpcClk=210000 KHz" "$OUT" "PMUMON deterministic sample"
check "perf.currPstate.*0x100 = P8" "$OUT" "PSTATE one-hot decode"
check "0x2080014a|pstate" "$OUT" "identity probe tolerated (fixture returns zeros)"
[ $RV -eq 0 ] && echo "ok   exit=0 on fixture" || { echo "FAIL exit=$RV"; fails=$((fails+1)); }

# 2. syscall-failure mode
OUT=$(FAKE_FAIL=1 LD_PRELOAD=$PWD/07-prototype/fake_rm.so ./07-prototype/rmctl 2>&1); RV=$?
[ $RV -ne 0 ] && echo "ok   FAKE_FAIL exit!=0" || { echo "FAIL FAKE_FAIL exit=0"; fails=$((fails+1)); }

# 3. RM-failure mode: every control returns 0x56
OUT=$(FAKE_STATUS=0x56 LD_PRELOAD=$PWD/07-prototype/fake_rm.so ./07-prototype/rmctl 2>&1); RV=$?
check "status=0x56" "$OUT" "RM rejection surfaced"

# 4. changing outputs + stale-input rejection (3 PMUMON calls in one process)
gcc -O2 -Wall -o /tmp/fake_multi tests/fake_rm_multi.c 07-prototype/fake_rm.c -ldl 2>&1 | head -3
OUT=$(LD_PRELOAD=$PWD/07-prototype/fake_rm.so /tmp/fake_multi 2>&1); RV=$?
echo "$OUT"
check "seq: 210000 211000 212000" "$OUT" "PMUMON changing outputs (deterministic)"
check "stale-input rejected with 0x56" "$OUT" "stale super metadata rejected"

echo; [ $fails -eq 0 ] && echo "all fake-RM tests passed" || echo "$fails test(s) FAILED"
exit $fails
