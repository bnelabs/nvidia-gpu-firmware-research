# rmctl prototype notes — calling RM controls from userspace (source-grounded)

All paths verified against `vendor/open-gpu-kernel-modules` (default branch, commit `ca2d03e`,
version 615.78.08 — same r615 branch as the rig's 615.71.09; tag `v615.71.09` does not exist
upstream). Vendor tree is gitignored; re-fetch with:
`git clone --depth 1 https://github.com/NVIDIA/open-gpu-kernel-modules vendor/open-gpu-kernel-modules`

## The recipe (verified in source)

1. **Device nodes**: `/dev/nvidiactl` (global), `/dev/nvidia0` (device). Created by the driver,
   access-gated by `/dev/nvidia-caps/nvidia-cap*` (see `kernel-open/common/inc/nv-ioctl.h`).
2. **Escape number**: `NV_ESC_RM_CONTROL = 0x2A`
   → `src/nvidia/arch/nvalloc/unix/include/nv_escape.h:34`
   (allocation is `NV_ESC_RM_ALLOC` in the same header).
3. **Argument struct**: `NVOS54_PARAMETERS` → `src/common/sdk/nvidia/inc/nvos.h`
   (fields: `hClient`, `hObject`, `cmd`, `pParams`, `paramsSize`, status…).
4. **Command codes**: `0x2080xxxx` classes → `src/common/sdk/nvidia/inc/ctrl/ctrl2080/`
   with per-topic headers, including:
   - `ctrl2080fan.h` — fan control
   - `ctrl2080perf.h` / `ctrl2080perf_cf.h` — performance/clock policies
   - `ctrl2080power.h` — power limits/draw
   - `ctrl2080thermal.h` — thermal policy/limits
   - `ctrl2080volt.h` — voltage
   - `ctrl2080clk.h` (clock domains), `ctrl2080gsp.h` — GSP interface itself
5. **GSP interface example** (from `ctrl2080gsp.h`): `NV2080_CTRL_CMD_GSP_GET_FEATURES`
   = `0x20803601` — command IDs follow a "finn" scheme:
   `(FINN interface id << 8) | message id` — same numbering family as GSP RPC message IDs.

## What this enables

A small C tool that opens `/dev/nvidiactl`, allocates a client/subdevice via `NV_ESC_RM_ALLOC`,
then issues any *documented* `0x2080xxxx` control — the same surface NVML uses internally.
That yields NVML-equivalent-or-better control (fan curves, clock locks, thermal policy,
infoROM reads) with **zero patching** and full visibility of what each command does.

Key open items (P3):
- [ ] Pin the exact client/subdevice handle-allocation sequence (`NV_ESC_RM_ALLOC` + object
      classes in `src/common/sdk/nvidia/inc/class/cl0080.h`).
- [ ] Determine which controls require elevated *abilities* (see `nvidia-cap` devices /
      `src/nvidia/arch/nvalloc/unix/src/osapi.c` ability checks) vs plain user access.
- [ ] Prototype: `GET_FEATURES` (read-only, harmless) as the smoke test on the rig —
      it reads a capability bitmask and mutates nothing.

## Related source landmarks (mined 2026-10-15)

- GSP RPC transport: `src/nvidia/inc/libraries/msgq/msgq.h` + `msgq.c` (shared-memory queues).
- GSP kernel-side core: `src/nvidia/inc/kernel/gpu/gsp/kernel_gsp.h`, `gsp_fw_heap.h`,
  `gsp_init_args.h`, `gsp_static_config.h`.
- **Per-arch GSP register manuals** (public!): `src/common/inc/swref/published/{turing/tu102,
  ampere/ga102, hopper/gh100, blackwell/gb100,blackwell/gb10b,blackwell/gb20b, rubin/gr100}/dev_gsp.h`
  — **including `rubin/gr100`**: next-gen GSP register definitions are already in the tree.
- UVM UAPI (separate): `kernel-open/nvidia-uvm/uvm_ioctl.h`.

## Rig facts tied to this (from 06-ground-truth dumps)

- `nvidia-smi -q -x` exposes `<gsp_firmware_version>615.71.09</gsp_firmware_version>`.
- GSP images on disk: `gsp_ga10x.bin` (27,043,992 B, sha256 c420726d…),
  `gsp_tu10x.bin` (22,897,536 B, sha256 78e0a2c8…).
- Unprivileged `lspci -vvv` shows `Capabilities: <access denied>`; **root** read-only dump
  captured full cap list (Resizable BAR @0xbb0, Secondary PCIe @0x900, 16 GT/s PHY @0xc1c…).
