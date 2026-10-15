#!/usr/bin/env bash
# fetch_gsp.sh — collect NVIDIA GSP firmware images across driver versions.
# READ-ONLY wrt the GPU: network + filesystem operations only, never touches /dev/nvidia*.
#
# Sources:
#   1) already-installed images under /lib/firmware/nvidia/<version>/gsp_*.bin
#   2) NVIDIA .run driver packages (downloaded from download.nvidia.com), extracted with -x
#
# Output: firmware-store/gsp/<version>/gsp_<arch>.bin   (binaries are gitignored)
#         firmware-store/gsp/SHA256SUMS.all              (hash inventory — this IS committed)
#
# Usage: scripts/fetch_gsp.sh 550.54.15 570.153.02 ...   (no args = local images only)
set -uo pipefail
BASE_URL="https://us.download.nvidia.com/XFree86/Linux-x86_64"
STORE="firmware-store/gsp"
mkdir -p "$STORE"

# 1) locally installed images (installed by the driver itself)
find /lib/firmware/nvidia /usr/lib/firmware/nvidia -name 'gsp_*.bin' 2>/dev/null | sort -u |
while read -r f; do
  ver="$(basename "$(dirname "$f")")"
  mkdir -p "$STORE/$ver"
  cp -n "$f" "$STORE/$ver/" 2>/dev/null || true
done

# 2) .run packages for requested versions (network; tolerate failures)
for ver in "$@"; do
  dest="$STORE/$ver"; mkdir -p "$dest"
  run="NVIDIA-Linux-x86_64-$ver.run"
  if [ ! -s "$dest/gsp_ga10x.bin" ]; then
    echo "fetching $ver ..." >&2
    curl -fL --retry 2 -o "$dest/$run" "$BASE_URL/$ver/$run" || { echo "download failed: $ver" >&2; continue; }
    (cd "$dest" && sh "$run" -x >/dev/null 2>&1 && mv NVIDIA-Linux-x86_64-*/gsp_*.bin . 2>/dev/null)
    rm -rf "$dest/NVIDIA-Linux-x86_64-$ver" "$dest/$run"
  fi
done

# 3) hash inventory (committed; binaries gitignored)
find "$STORE" -name 'gsp_*.bin' -exec sha256sum {} \; | sort -k2 > "$STORE/SHA256SUMS.all"
cat "$STORE/SHA256SUMS.all"
echo "done -> $STORE"
