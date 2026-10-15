#!/usr/bin/env bash
# fetch_gsp_history.sh — build a version series of GSP firmware images for binary-diffing.
# Source: linux-firmware's per-chip nouveau copies (nvidia/<chip>/gsp/gsp-<driverver>.bin),
# fetched as individual files from kernel.org cgit — no multi-hundred-MB driver packages needed.
#
# READ-ONLY wrt the GPU: network + filesystem only.
# Output: firmware-store/gsp-history/<chip>/gsp-<ver>.bin   (binaries gitignored)
#         firmware-store/gsp-history/<chip>/SHA256SUMS       (committed)
#
# Usage: scripts/fetch_gsp_history.sh [chip] [max_versions]
#        chip = ga102 (Ampere/RTX 3090-class) | gb202 (Blackwell) | tu102 ... default ga102
set -uo pipefail
CHIP="${1:-ga102}"
MAXV="${2:-10}"
BASE="https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git"
OUT="firmware-store/gsp-history/$CHIP"
mkdir -p "$OUT"

echo "# GSP history for $CHIP — $(date -Iseconds)" > "$OUT/README.txt"
echo "source: $BASE/tree/nvidia/$CHIP/gsp" >> "$OUT/README.txt"

# 1) enumerate available versions from the cgit directory listing
mapfile -t versions < <(curl -fsSL "$BASE/tree/nvidia/$CHIP/gsp" 2>/dev/null |
  grep -oE 'gsp-[0-9]+\.[0-9]+(\.[0-9]+)?\.bin' | sort -u -V | tail -n "$MAXV")

if [ "${#versions[@]}" -eq 0 ]; then
  echo "ERROR: could not enumerate versions (listing fetch failed?)" >&2
  exit 1
fi
echo "versions: ${versions[*]}" | tee -a "$OUT/README.txt"

# 2) download each + hash
for v in "${versions[@]}"; do
  f="$OUT/$v"
  if [ ! -s "$f" ]; then
    echo "fetching $v ..." >&2
    curl -fsSL -o "$f" "$BASE/plain/nvidia/$CHIP/gsp/$v" || { echo "download failed: $v" >&2; rm -f "$f"; continue; }
  fi
done

# 3) hash inventory (committed; binaries gitignored)
find "$OUT" -maxdepth 1 -name 'gsp-*.bin' -size +0 -exec sha256sum {} \; |
  sort -k2 > "$OUT/SHA256SUMS"
ls -l "$OUT"/gsp-*.bin 2>/dev/null | awk '{print $5, $9}' | tee -a "$OUT/README.txt"
echo "done -> $OUT"
