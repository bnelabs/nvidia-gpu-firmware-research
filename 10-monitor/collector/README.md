# collector - read-only GPU monitor (v1)

## What it does
Polls the vendor-supported NVML surface at a fixed interval and appends one JSON
object per sample to a JSONL file. Also parses the recent kernel log for XID
error lines and records driver/vBIOS/GSP identity.

## Hard constraints honored (see operating-envelope in 07-diagnostics)
- READ-ONLY: every NVML call is a getter; no SET functions are bound, compiled,
  or reachable from this file (grep attestation: no nvmlDeviceSet* symbol in source)
- No LD_PRELOAD, no injection
- No direct device-node access: NVML is the vendor's supported library (the same
  one nvidia-smi uses); kernel log read via journalctl/dmesg if permitted, skipped
  gracefully when the host restricts dmesg (kernel.dmesg_restrict=1)
- No synthetic stress: the collector observes whatever the machine is doing

## Usage
```
python3 collector.py --dry-run                      # print plan, write nothing
python3 collector.py --interval 30 --out gpu-series.jsonl
python3 collector.py --interval 1 --duration 60 --out burst.jsonl   # short window
```
No root required (NVML device-node access is granted to the video group by the
vendor driver, same as nvidia-smi; dmesg may be restricted - handled).

## Sampled fields (all verified live on 615.71.09, see ../nvml-surface-audit.md)
power_w, power_limit_w, energy_mj, temp_gpu_c, temp_shutdown_c, temp_slowdown_c,
fan_pct, fan_target_pct, fan_min/max_pct, clock_max_graphics_mhz,
clock_max_mem_mhz, clock_min_graphics_mhz, clock_max_pstate_graphics_mhz,
throttle_bitmask + decoded reasons, pcie_gen, pcie_width, vf_offset_gpc,
vf_offset_mem, pstate. Identity once per run: model, vbios (NVML + procfs),
driver, gsp_fw (procfs), uuid (procfs), bus location, kernel module version.

## Storage format: JSONL (justified)
Chosen over SQLite for v1 because: (a) append-only streaming is crash-safe with
no WAL/recovery logic; (b) the analysis path is pandas/jq over the whole series,
not random access; (c) diffing two monitoring periods is a text diff. SQLite
becomes the right choice at the crowdsourced-aggregation stage (D3), where
random access and dedup queries matter.

## Sampling-interval / overhead rationale
- Default 30 s: ~2 NVML RPC round-trips/sec total across ~20 fields = negligible
  against the driver's own telemetry load; safe to run 24/7 on a working card.
- 1 s bursts: safe for short diagnostic windows (minutes), multiplies GSP RPC
  load 30x - not recommended as the default.
- Sub-second: allowed but discouraged - the GSP RPC queue is shared with the
  customer's workload; a monitor must never be the load.
- The collector sleeps between samples (no busy loop) and flushes per line.

## Known-good run (2026-10-20, host's own RTX 3090)
4 samples at 2 s: P8 idle, 23.2 W, 41 C, fan 0 % (passive), PCIe gen1/x4 idle
downshift (normal - link powers up under load), throttle = GPU_IDLE (expected
at idle). XIDs found in 500 log lines: 0.

## The GspFirmwareVersion lesson
nvmlDeviceGetGspFirmwareVersion SEGFAULTS under ctypes in 615.71.09
(nondeterministically - it survived in one audit run and crashed in another).
The collector does not bind it: GSP fw version comes from procfs
(/proc/driver/nvidia/gpus/*/information). Lesson recorded in
nvml-surface-audit.md: the published header is not a contract; every binding
must be call-verified, and a function that crashes must be dropped, not wrapped
in try/except (ctypes cannot catch a segfault).
