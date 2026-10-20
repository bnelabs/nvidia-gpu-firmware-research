#!/usr/bin/env bash
# Fetch individual firmware artifacts, validate ELF magic, retain URL and hash.
# Network/filesystem only; no installer, library, driver or device execution.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$#" -eq 0 ]; then
  echo 'Offline acquisition plan. Usage: fetch_gsp_history.sh CHIP [MAX_VERSIONS]'
  exit 0
fi
CHIP="$1"
MAXV="${2:-10}"
[[ "$CHIP" =~ ^[a-z]{2}[0-9]{3}$ ]] || { echo 'Invalid chip name' >&2; exit 1; }
[[ "$MAXV" =~ ^[0-9]+$ ]] && [ "$MAXV" -ge 1 ] && [ "$MAXV" -le 30 ] || { echo 'MAX_VERSIONS must be 1..30' >&2; exit 1; }
BASE="https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git"
OUT="firmware-store/gsp-history/$CHIP"
mkdir -p "$OUT"
listing=$(mktemp)
trap 'rm -f "$listing"' EXIT
curl -fsSL --proto '=https' --tlsv1.2 "$BASE/tree/nvidia/$CHIP/gsp" > "$listing"
versions=$(grep -oE 'gsp-[0-9]+\.[0-9]+(\.[0-9]+)?\.bin' "$listing" | sort -u | tail -n "$MAXV") || { echo 'No firmware links; refuse HTML/error fallback' >&2; exit 1; }
[ -n "$versions" ] || { echo 'No versions found' >&2; exit 1; }
for version in $versions; do
  file="$OUT/$version"
  url="$BASE/plain/nvidia/$CHIP/gsp/$version"
  tmp=$(mktemp "$OUT/artifact.XXXXXX")
  if ! curl -fsSL --proto '=https' --tlsv1.2 -o "$tmp" "$url"; then rm -f "$tmp"; exit 1; fi
  if ! python3 - "$tmp" <<'ARTIFACT_CHECK'
import pathlib,sys
data=pathlib.Path(sys.argv[1]).read_bytes()
sys.exit(0 if len(data)>=64 and data[:4]==b'\x7fELF' else 1)
ARTIFACT_CHECK
  then rm -f "$tmp"; echo 'Rejected non-ELF/HTML artifact' >&2; exit 1; fi
  if [ -e "$file" ]; then
    cmp -s "$tmp" "$file" || { rm -f "$tmp"; echo 'Existing artifact differs; retain it and investigate provenance' >&2; exit 1; }
    rm -f "$tmp"
  else
    mv "$tmp" "$file"
  fi
  printf '%s\n' "$url" > "$file.source.txt"
  if command -v sha256sum >/dev/null; then sha256sum "$file" > "$file.sha256"; else shasum -a 256 "$file" > "$file.sha256"; fi
done
echo 'Downloaded files only. ELF magic is not full structural or provenance validation.'
