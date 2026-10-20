#!/usr/bin/env bash
# Download source archives only. NEVER execute a driver installer or touch a GPU.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$#" -eq 0 ]; then
  echo 'Offline acquisition plan: provide explicit NVIDIA driver versions to download .run archives without executing them.'
  exit 0
fi
BASE_URL="https://us.download.nvidia.com/XFree86/Linux-x86_64"
STORE="firmware-store/source-packages"
for ver in "$@"; do
  [[ "$ver" =~ ^[0-9]{3}(\.[0-9]{1,3}){1,2}$ ]] || { echo 'Invalid driver version' >&2; exit 1; }
  dest="$STORE/$ver"
  mkdir -p "$dest"
  run="NVIDIA-Linux-x86_64-$ver.run"
  url="$BASE_URL/$ver/$run"
  if [ ! -e "$dest/$run" ]; then
    tmp=$(mktemp "$dest/download.XXXXXX")
    if ! curl -fsSL --proto '=https' --tlsv1.2 -o "$tmp" "$url"; then
      rm -f "$tmp"
      exit 1
    fi
    mv "$tmp" "$dest/$run"
  fi
  printf '%s\n' "$url" > "$dest/SOURCE.txt"
  if command -v sha256sum >/dev/null; then
    sha256sum "$dest/$run" > "$dest/SHA256SUMS"
  else
    shasum -a 256 "$dest/$run" > "$dest/SHA256SUMS"
  fi
  echo "Saved $dest/$run. Not executed. Inspect/extract only in a CPU-only offline environment."
done
