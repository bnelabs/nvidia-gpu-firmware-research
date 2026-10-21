#!/usr/bin/env bash
# Run through scripts/run_cpu_only.sh; inputs are copied files, never a GPU.
set -euo pipefail
PACKET=research/2026-10-21-gfw-boot
ROM=${1:-firmware-store/gfw-boot/msi-3090-F4-candidate.rom}
GFW_REPLAY_TMP=$(mktemp -d)
trap 'rm -rf "$GFW_REPLAY_TMP"' EXIT
python3 "$PACKET/inspect_fwsec.py" "$ROM" > "$GFW_REPLAY_TMP/parsed.json"
python3 - "$ROM" "$GFW_REPLAY_TMP/parsed.json" "$PACKET/candidate-fwsec-corrected.json" "$GFW_REPLAY_TMP/debug-imem.bin" <<'PY'
import hashlib,json,struct,sys
from pathlib import Path
data=Path(sys.argv[1]).read_bytes()
if hashlib.sha256(data).hexdigest() != '6dd01dee331f4d0faf5dbd8bc58e31dd58eb88c7d403c7f7ae13e412927e8711':
    raise ValueError('Wrong ROM candidate; do not apply pinned offsets to another file')
actual=json.loads(Path(sys.argv[2]).read_text())
expected=json.loads(Path(sys.argv[3]).read_text())
actual.pop('path');expected.pop('path')
if actual!=expected:raise ValueError('Parser evidence changed')
entry=next(e for e in actual['entries'] if e['application_id']==0x45)
offset=actual['falcon_pointer_base_file_offset']+entry['descriptor_pointer_raw']
header,stored,pkc,interface,pa,size=struct.unpack_from('<6I',data,offset)
start=offset+(header>>16)
if start+size>len(data):raise ValueError('IMEM out of bounds')
imem=data[start:start+size]
if hashlib.sha256(imem).hexdigest()!='a84efa34649c843d6075fbbeec3ee958a3a02df25ed8c0a34ba679f1775f6fb1':
    raise ValueError('Debug IMEM hash mismatch')
Path(sys.argv[4]).write_bytes(imem)
print('Candidate ROM, parser offsets and stored debug IMEM match retained evidence.')
PY
openssl enc -d -aes-128-ecb -K 25EFCDAB896745231032547698BADCFE -nopad \
  -in "$GFW_REPLAY_TMP/debug-imem.bin" -out "$GFW_REPLAY_TMP/decoded-imem.bin"
python3 "$PACKET/replay_fwsec_progress.py" "$GFW_REPLAY_TMP/decoded-imem.bin" > "$GFW_REPLAY_TMP/progress.json"
cmp "$GFW_REPLAY_TMP/progress.json" "$PACKET/fwsec-progress-replay.json"
python3 "$PACKET/replay_early_gates.py" "$GFW_REPLAY_TMP/decoded-imem.bin" > "$GFW_REPLAY_TMP/early.json"
cmp "$GFW_REPLAY_TMP/early.json" "$PACKET/early-gates-replay.json"
openssl enc -e -aes-128-ecb -K 25EFCDAB896745231032547698BADCFE -nopad \
  -in "$GFW_REPLAY_TMP/decoded-imem.bin" -out "$GFW_REPLAY_TMP/roundtrip.bin"
cmp "$GFW_REPLAY_TMP/debug-imem.bin" "$GFW_REPLAY_TMP/roundtrip.bin"
cc -std=c11 -O2 -Wall -Wextra -Werror "$PACKET/replay.c" -o "$GFW_REPLAY_TMP/source-gate"
"$GFW_REPLAY_TMP/source-gate" > "$GFW_REPLAY_TMP/source-gate.json"
cmp "$GFW_REPLAY_TMP/source-gate.json" "$PACKET/replay.json"
printf '%s\n' '30 progress-block, 12 early-gate and six NVIDIA source-gate cases reproduced.'
