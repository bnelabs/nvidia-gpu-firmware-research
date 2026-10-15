# Tracing the RM/GSP path — empirical results on the rig (2026-10-15)

Answers the "RPC tracer recipe" item of ROADMAP P3 for THIS driver build (615.71.09, stock
Ubuntu kernel). All tests read-only; kprobes attached for ≤3 s during active inference with no
observable impact (as expected — probes only observe).

## Result: the RM core path is NOT kprobe/ftrace-traceable on this build

| Attempt | Result |
|---|---|
| `kprobe:rm_ioctl` | bpftrace: "not traceable (non-existing, inlined, or notrace)" — symbol exists in kallsyms (`t rm_ioctl [nvidia]`) but is **absent from `/sys/kernel/tracing/available_filter_functions`** |
| `kprobe:nvidia_ioctl` | same — not attachable |
| `kprobe:__nv_drm_*` (71 symbols) | ✅ attachable — DRM/modeset layer only |
| total attachable probes | 80,386 (whole kernel), nvidia-relevant ≈ 71 DRM symbols |
| `grep nvidia /sys/kernel/tracing/available_filter_functions` | 3,307 lines — but ALL are `nvidia*`/`nv*` substring hits (e.g. `devm_pci_remap_cfgspace` matches 'gsp'!) + drm/uvm functions; **no RM core symbols** |

Lesson: kallsyms visibility ≠ traceability. The prebuilt nvidia.ko's RM functions are local
(`t`) and excluded from the ftrace filter set (module built without `-pg` instrumentation or
marked notrace). Kernel symbols whose names merely contain nvidia/nv/gsp pollute naive greps —
always anchor regexes (`^name$`).

## What still works (ordered by fidelity)

1. **strace on the official client** — proven in 07-prototype/rmctl-notes.md; captures every
   RM ioctl (escape number + payload size) NVML issues. The practical RM tracer.
2. **rmctl as the instrument** — since we can issue RM controls ourselves, logging IS the
   trace. Extend with a query mode + payload hexdump (P3).
3. **GSP RPC logging** — kernel module param `EnableGpuFirmwareLogs=2` is SET on this rig
   (/proc/driver/nvidia/params, captured in 06-ground-truth). GSP logs land in the kernel log
   via the RATS/event-buffer path (kallsyms shows `gspRats*` symbols). Extract recipe pending:
   check `dmesg | grep -i gsp` after a driver reload on the BENCH (production rig stays untouched).
4. **nouveau/nvkm RPC logs** — full RPC printing is a nouveau feature; run on the P4 bench
   (or VFIO VM) with the same GPU generation, not on the production host.
5. **kprobes on the DRM layer** — works today if display-path tracing is ever needed.

## Rig note (2026-10-15 afternoon)

The host rebooted between captures: the RTX 3090 enumerated at **01:00.0** in the 12:22 dumps
and at **06:00.0** in later sessions (dmesg boot events at +5.8 s on 06:00.0). One GPU only
(nvidia-smi -L). Consequences:
- Never hardcode bus ids — `scripts/capture_state.sh` already resolves them dynamically ✓.
- Cross-boot comparisons must key on UUID (`GPU-8a9c05b3-…`), not PCI address.
- `/dev/nvidia*` device-node access worked identically in both enumerations (rmctl probe ran
  post-rename without change) — the UAPI is bus-address independent.
