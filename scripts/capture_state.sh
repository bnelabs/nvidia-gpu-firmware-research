#!/usr/bin/env bash
# PASSIVE, READ-ONLY capture of NVIDIA GPU + firmware-adjacent state.
# Safe to run while the GPU performs production inference:
#   * NVML queries (nvidia-smi -q / --query-gpu)  — informational only
#   * /proc/driver/nvidia/* reads                 — informational only
#   * lspci config-space reads                    — informational only
#   * hashing of on-disk firmware files           — filesystem only
# NEVER mutates device state: no -pl/-lgc/-r, no sysfs writes, no driver unbind, no rom dump.
set -u
cd "$(dirname "$0")/.."
OUT="06-ground-truth/dumps-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"
echo "capture $(date -Iseconds) host=$(hostname)" > "$OUT/MANIFEST.txt"

# 1) Driver + kernel module facts
{ uname -a; cat /proc/driver/nvidia/version; } > "$OUT/driver.txt" 2>&1
cp /proc/driver/nvidia/params "$OUT/driver-params.txt" 2>/dev/null || true

# 2) Full NVML state (read-only)
nvidia-smi -q -x > "$OUT/nvidia-smi-q.xml" 2>&1
nvidia-smi --query-gpu=name,driver_version,vbios_version,pstate,temperature.gpu,power.draw,power.limit,power.max_limit,clocks.gr,clocks.mem,pcie.link.gen.current,pcie.link.width.current,fan.speed --format=csv > "$OUT/nvidia-smi-query.csv" 2>&1

# 3) GSP firmware images installed on disk (hash them; never commit the binaries)
find /lib/firmware/nvidia /usr/lib/firmware/nvidia /usr/share/nvidia -maxdepth 4 -name 'gsp*.bin' 2>/dev/null | while read -r f; do
  sha256sum "$f" 2>/dev/null; ls -l "$f" 2>/dev/null
done > "$OUT/gsp-firmware-images.txt" 2>&1

# 4) Per-GPU: procfs info + PCI config space (read-only) + sysfs entry inventory
cat /proc/driver/nvidia/gpus/*/information > "$OUT/nvidia-proc-gpu-info.txt" 2>/dev/null
for bdf in $(nvidia-smi --query-gpu=pci.bus_id --format=csv,noheader 2>/dev/null | head -1); do
  bdf="$(echo "$bdf" | cut -c5- | tr 'A-Z' 'a-z')"   # 00000000:01:00.0 -> 0000:01:00.0
  lspci -nn -vvv -s "$bdf" > "$OUT/lspci-vvv.txt" 2>&1
  lspci -xxx -s "$bdf"     > "$OUT/lspci-configspace-4k.txt" 2>&1
  ls -l /sys/bus/pci/devices/"$bdf"/{rom,resource,reset} > "$OUT/sysfs-entry-listing.txt" 2>&1
done

# 5) GSP-related lines from the XML dump (if the field exists on this branch)
grep -ia 'gsp' "$OUT/nvidia-smi-q.xml" | head -40 > "$OUT/gsp-version-lines.txt" 2>/dev/null || true

echo "capture done $(date -Iseconds)" >> "$OUT/MANIFEST.txt"
echo "wrote $OUT"
