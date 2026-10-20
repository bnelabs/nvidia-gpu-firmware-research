#!/usr/bin/env python3
"""10-monitor collector: read-only NVML poller + kernel-log XID parser.

Read-only guarantees:
- Uses only the vendor-supported NVML library (the same surface nvidia-smi uses)
- Opens NO device nodes directly, no LD_PRELOAD, no SET calls
- Kernel log is read via journalctl/dmesg if permitted, or skipped gracefully
- Writes only its own output file (JSONL)

Usage:
  collector.py --interval 30 --out gpu-series.jsonl
  collector.py --dry-run
"""
import argparse, ctypes, datetime, json, os, subprocess, sys, time

# ---------- NVML binding (ctypes, stdlib only) ----------
class NVML:
    def __init__(self):
        self.lib = ctypes.CDLL('libnvidia-ml.so.1')
        self.lib.nvmlInit_v2()
        self.h = ctypes.c_void_p()
        rc = self.lib.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(self.h))
        if rc != 0:
            raise RuntimeError(f'nvmlDeviceGetHandleByIndex: {rc}')
        self._bind()

    def _bind(self):
        L, cu, ci, cull, cp = self.lib, ctypes.c_uint, ctypes.c_int, ctypes.c_ulonglong, ctypes.c_char_p
        def g(name, argtypes, restype=ctypes.c_int):
            f = getattr(L, name)
            f.argtypes = [ctypes.c_void_p] + argtypes
            f.restype = restype
            return f
        self.get_power   = g('nvmlDeviceGetPowerUsage', [ctypes.POINTER(cu)])
        self.get_plimit  = g('nvmlDeviceGetEnforcedPowerLimit', [ctypes.POINTER(cu)])
        self.get_energy  = g('nvmlDeviceGetTotalEnergyConsumption', [ctypes.POINTER(cull)])
        self.get_temp    = g('nvmlDeviceGetTemperature', [cu, ctypes.POINTER(cu)])
        self.get_tthr    = g('nvmlDeviceGetTemperatureThreshold', [cu, ctypes.POINTER(cu)])
        self.get_fan_v2  = g('nvmlDeviceGetFanSpeed_v2', [cu, ctypes.POINTER(cu)])
        self.get_fan_tgt = g('nvmlDeviceGetTargetFanSpeed', [cu, ctypes.POINTER(cu)])
        self.get_fan_rng = g('nvmlDeviceGetMinMaxFanSpeed', [ctypes.POINTER(cu), ctypes.POINTER(cu)])
        self.get_maxclk  = g('nvmlDeviceGetMaxClockInfo', [cu, ctypes.POINTER(cu)])
        self.get_mmclk_ps = g('nvmlDeviceGetMinMaxClockOfPState', [cu, cu, ctypes.POINTER(cu), ctypes.POINTER(cu)])
        self.get_throttle = g('nvmlDeviceGetCurrentClocksThrottleReasons', [ctypes.POINTER(cull)])
        self.get_throttle_sup = g('nvmlDeviceGetSupportedClocksThrottleReasons', [ctypes.POINTER(cull)])
        self.get_pcie_gen = g('nvmlDeviceGetCurrPcieLinkGeneration', [ctypes.POINTER(cu)])
        self.get_pcie_w   = g('nvmlDeviceGetCurrPcieLinkWidth', [ctypes.POINTER(cu)])
        self.get_gpc_vf   = g('nvmlDeviceGetGpcClkVfOffset', [ctypes.POINTER(ci)])
        self.get_mem_vf   = g('nvmlDeviceGetMemClkVfOffset', [ctypes.POINTER(ci)])
        self.get_pstate   = g('nvmlDeviceGetPerformanceState', [ctypes.POINTER(cu)])
        self.get_vbios    = g('nvmlDeviceGetVbiosVersion', [cp, cu])
        # nvmlDeviceGetGspFirmwareVersion SEGFAULTS under ctypes in 615.71.09
        # (nondeterministic; audited and removed - see nvml-surface-audit.md).
        # GSP fw version is read from procfs instead (see collect_driver_meta).
        self.get_gspfw = None
        self.get_driverv  = L.nvmlSystemGetDriverVersion
        self.get_driverv.argtypes = [cp, cu]
        self.get_mem      = g('nvmlDeviceGetMemoryInfo_v2', [ctypes.c_void_p]) if hasattr(L,'nvmlDeviceGetMemoryInfo_v2') else None

    def close(self):
        self.lib.nvmlShutdown()

    def _u(self, fn, *a):
        v = ctypes.c_uint()
        rc = fn(*a, ctypes.byref(v))
        return (rc, v.value)

    def _i(self, fn, *a):
        v = ctypes.c_int()
        rc = fn(*a, ctypes.byref(v))
        return (rc, v.value)

    def sample(self):
        s = {}
        rc, s['power_w'] = self._u(self.get_power, self.h)     # mW -> W below
        rc, s['power_limit_w'] = self._u(self.get_plimit, self.h)
        ev = ctypes.c_ulonglong()
        rc = self.get_energy(self.h, ctypes.byref(ev))
        s['energy_mj'] = ev.value if rc == 0 else None
        rc, s['temp_gpu_c'] = self._u(self.get_temp, self.h, ctypes.c_uint(0))
        rc, s['temp_shutdown_c'] = self._u(self.get_tthr, self.h, ctypes.c_uint(0))
        rc, s['temp_slowdown_c'] = self._u(self.get_tthr, self.h, ctypes.c_uint(1))
        rc, s['fan_pct'] = self._u(self.get_fan_v2, self.h, ctypes.c_uint(0))
        rc, s['fan_target_pct'] = self._u(self.get_fan_tgt, self.h, ctypes.c_uint(0))
        fa, fb = ctypes.c_uint(), ctypes.c_uint()
        rc = self.get_fan_rng(self.h, ctypes.byref(fa), ctypes.byref(fb))
        s['fan_min_pct'], s['fan_max_pct'] = (fa.value, fb.value) if rc == 0 else (None, None)
        rc, s['clock_max_graphics_mhz'] = self._u(self.get_maxclk, self.h, ctypes.c_uint(0))
        rc, s['clock_max_mem_mhz'] = self._u(self.get_maxclk, self.h, ctypes.c_uint(2))
        a_, b_, c_ = ctypes.c_uint(), ctypes.c_uint(), ctypes.c_uint()
        rc = self.get_mmclk_ps(self.h, ctypes.c_uint(0), ctypes.c_uint(0), ctypes.byref(a_), ctypes.byref(b_))
        s['clock_min_graphics_mhz'] = a_.value if rc == 0 else None
        s['clock_max_pstate_graphics_mhz'] = b_.value if rc == 0 else None
        tv = ctypes.c_ulonglong()
        rc = self.get_throttle(self.h, ctypes.byref(tv))
        s['throttle_bitmask'] = tv.value if rc == 0 else None
        rc, s['pcie_gen'] = self._u(self.get_pcie_gen, self.h)
        rc, s['pcie_width'] = self._u(self.get_pcie_w, self.h)
        rc, s['vf_offset_gpc'] = self._i(self.get_gpc_vf, self.h)
        rc, s['vf_offset_mem'] = self._i(self.get_mem_vf, self.h)
        rc, s['pstate'] = self._u(self.get_pstate, self.h)
        # units: NVML power is milliwatts
        s['power_w'] = s['power_w'] / 1000.0 if s['power_w'] is not None else None
        s['power_limit_w'] = s['power_limit_w'] / 1000.0 if s['power_limit_w'] is not None else None
        return s

    def identity(self):
        idn = {}
        buf = ctypes.create_string_buffer(96)
        rc = self.get_vbios(self.h, buf, 96)
        idn['vbios'] = buf.value.decode(errors='replace') if rc == 0 else None
        # gsp_fw comes from procfs in collect_driver_meta()
        buf3 = ctypes.create_string_buffer(96)
        rc = self.get_driverv(buf3, 96)
        idn['driver'] = buf3.value.decode(errors='replace') if rc == 0 else None
        return idn

THROTTLE_BITS = {
    0x1: 'GPU_IDLE', 0x2: 'GPU_APPLICATION_CLOCKS_SETTING', 0x4: 'SW_POWER_CAP',
    0x8: 'HW_SLOWDOWN', 0x10: 'SYNC_BOOST', 0x20: 'SW_THERMAL_SLOWDOWN',
    0x40: 'HW_THERMAL_SLOWDOWN', 0x80: 'HW_POWER_BRAKE_SLOWDOWN', 0x100: 'SW_PWM_CAP',
}

def decode_throttle(mask):
    return [n for b, n in THROTTLE_BITS.items() if mask & b]

# ---------- XID parsing (kernel log, unprivileged-best-effort) ----------
def parse_xids(lines):
    out = []
    for line in lines:
        if 'Xid' in line and ('NVRM' in line or 'nvidia' in line.lower()):
            # typical: ... NVRM: Xid (PCI:0000:06:00): 13, pid=..., name=...
            try:
                xid = int(line.split('Xid')[1].split(':')[1].split(',')[0].strip())
            except (IndexError, ValueError):
                continue
            out.append({'xid': xid, 'line': line.strip()[:200]})
    return out

def collect_kernel_log(max_lines=500):
    """Try journalctl, then dmesg; return lines or [] if inaccessible (no root)."""
    for cmd in (['journalctl', '-k', '-n', str(max_lines), '--no-pager'],
                ['dmesg', '--', '-t']):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and r.stdout:
                return r.stdout.splitlines()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    # /dev/kmesg requires root; do NOT try to elevate
    return []

def collect_driver_meta():
    meta = {}
    try:
        meta['kernel_module_version'] = open('/proc/driver/nvidia/version').read().splitlines()[0][:160]
    except OSError:
        pass
    # procfs identity: model, vBIOS, GPU (GSP) firmware, UUID, bus location
    import glob as _glob
    for info_path in _glob.glob('/proc/driver/nvidia/gpus/*/information'):
        try:
            for line in open(info_path):
                if ':' not in line:
                    continue
                k, v = line.split(':', 1)
                k, v = k.strip(), v.strip()
                if k in ('Model', 'Video BIOS', 'GPU Firmware', 'GPU UUID', 'Bus Location'):
                    key = {'Model': 'model', 'Video BIOS': 'vbios_procfs',
                           'GPU Firmware': 'gsp_fw', 'GPU UUID': 'uuid_procfs',
                           'Bus Location': 'bus_location'}[k]
                    meta[key] = v
        except OSError:
            continue
    return meta

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description='Read-only GPU monitor (NVML + kernel log)')
    ap.add_argument('--interval', type=float, default=30.0,
                    help='seconds between samples (default 30)')
    ap.add_argument('--out', default='gpu-series.jsonl')
    ap.add_argument('--dry-run', action='store_true',
                    help='print what would be sampled, write nothing')
    ap.add_argument('--duration', type=float, default=0,
                    help='stop after N seconds (0 = until Ctrl-C)')
    args = ap.parse_args()

    # interval rationale: NVML getters are RPCs to GSP-RM; 30 s default keeps
    # the RPC load ~2 calls/min (negligible vs the driver's own telemetry),
    # while 1 s bursts remain safe for short diagnostic windows. Sub-second
    # intervals are allowed but multiply GSP RPC load - not recommended as a
    # default on a working card.

    nv = NVML()
    idn = nv.identity()
    idn.update(collect_driver_meta())

    klog = collect_kernel_log()
    xids = parse_xids(klog)

    if args.dry_run:
        print(json.dumps({'mode': 'dry-run', 'identity': idn,
                          'fields_per_sample': sorted(nv.sample().keys()),
                          'throttle_bits': THROTTLE_BITS,
                          'kernel_log_lines_read': len(klog),
                          'xids_found': len(xids),
                          'interval_s': args.interval,
                          'out_file': args.out,
                          'write': False}, indent=2, default=str))
        nv.close()
        return

    print(f'identity: {json.dumps(idn)}', file=sys.stderr)
    if xids:
        print(f'XIDs in recent kernel log: {[x["xid"] for x in xids]}', file=sys.stderr)
    print(f'writing {args.out} every {args.interval}s (Ctrl-C to stop)', file=sys.stderr)

    start = time.time()
    with open(args.out, 'a') as fh:
        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            rec = {'ts': now.isoformat(timespec='milliseconds')}
            try:
                rec.update(nv.sample())
                rec['throttle_reasons'] = decode_throttle(rec.get('throttle_bitmask', 0) or 0)
            except Exception as e:
                rec['error'] = str(e)[:120]
            fh.write(json.dumps(rec, default=str) + '\n')
            fh.flush()
            if args.duration and (time.time() - start) >= args.duration:
                break
            time.sleep(args.interval)

    nv.close()

if __name__ == '__main__':
    main()
