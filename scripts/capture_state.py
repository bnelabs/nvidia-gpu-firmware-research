#!/usr/bin/env python3
"""One-shot documented telemetry collector. Default is an offline plan.

No arbitrary command/field options, broad -q, root, ctypes, raw PCI access,
instrumentation, automatic retries or remediation. See CONSTITUTION.md.
"""
import argparse
import csv
from contextlib import contextmanager
import datetime as dt
import fcntl
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

FIELDS = (
    "uuid", "name", "pci.bus_id", "driver_version", "vbios_version", "pstate",
    "temperature.gpu", "power.draw", "power.limit", "clocks.gr", "clocks.mem",
    "utilization.gpu", "utilization.memory", "fan.speed",
    "pcie.link.gen.current", "pcie.link.width.current",
)
UNITS = {"temperature.gpu": "C", "power.draw": "W", "power.limit": "W",
         "clocks.gr": "MHz", "clocks.mem": "MHz", "utilization.gpu": "%",
         "utilization.memory": "%", "fan.speed": "%"}
UUID_RE = re.compile(r"GPU-[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")
TIMEOUT_SECONDS = 8
MIN_INTERVAL_SECONDS = 10


@contextmanager
def monitoring_slot(path=None, clock=time.time):
    """Refuse concurrent/sub-10-second CLI runs, including after failed attempts."""
    path = path or Path.home() / ".cache/nvidia-firmware-research/monitor.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("another monitoring request is in progress; stop") from exc
        try:
            stream.seek(0)
            previous = stream.read().strip()
            now = clock()
            if previous:
                try:
                    elapsed = now - float(previous)
                except ValueError as exc:
                    raise ValueError("invalid cooldown state; stop rather than bypass it") from exc
                if not 0 <= elapsed or elapsed < MIN_INTERVAL_SECONDS:
                    raise ValueError("monitoring cooldown: at least 10 seconds between attempts")
            stream.seek(0)
            stream.truncate()
            stream.write(str(now))
            stream.flush()
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def command(uuid, executable="/usr/bin/nvidia-smi"):
    if not UUID_RE.fullmatch(uuid):
        raise ValueError("a full, previously known GPU UUID is required")
    return [executable, "--id=" + uuid, "--query-gpu=" + ",".join(FIELDS),
            "--format=csv,noheader,nounits"]


def collect(uuid, *, runner=subprocess.run, euid=os.geteuid, executable=None):
    """Dependency injection is for offline tests; CLI cannot supply a runner/path."""
    if euid() == 0:
        raise ValueError("live collection refuses root; do not elevate permissions")
    if executable is None:
        executable = next((p for p in ("/usr/bin/nvidia-smi", "/bin/nvidia-smi")
                           if Path(p).is_file()), None)
    if executable is None:
        raise ValueError("vendor nvidia-smi is unavailable; no install or fallback attempted")
    argv = command(uuid, executable)
    record = {"schema": 1, "mode": "documented-telemetry-single-query",
              "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "requested_uuid": uuid, "command": argv, "units": UNITS,
              "status": "error", "synthetic": False}
    try:
        # Do not inherit preload, injection or arbitrary driver settings.
        result = runner(argv, capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
                        check=False, env={"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"})
    except subprocess.TimeoutExpired:
        record["error"] = "query timed out; collection stopped without retry or recovery"
        return record
    except OSError as exc:
        record["error"] = str(exc)
        return record
    record.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
    if result.returncode:
        record["error"] = "vendor query failed; no retry or fallback attempted"
        return record
    rows = list(csv.reader(io.StringIO(result.stdout), skipinitialspace=True))
    if len(rows) != 1 or len(rows[0]) != len(FIELDS):
        record["error"] = "unexpected output shape; raw output retained, no values inferred"
        return record
    values = dict(zip(FIELDS, (v.strip() for v in rows[0])))
    if values["uuid"].lower() != uuid.lower():
        record["error"] = "device identity mismatch; collection stopped"
        return record
    record.update(status="observed", values=values)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="one documented query; never an experiment")
    parser.add_argument("--gpu-uuid", help="known full GPU UUID; no device enumeration")
    parser.add_argument("--output", type=Path, help="new JSON capture file; never overwrite")
    args = parser.parse_args(argv)
    if not args.live:
        print(json.dumps({"mode": "offline-plan", "hardware_access": False, "fields": FIELDS,
                          "timeout_seconds": TIMEOUT_SECONDS, "retries": 0,
                          "minimum_interval_seconds": MIN_INTERVAL_SECONDS,
                          "instructions": "For permitted monitoring only: --live --gpu-uuid GPU-... . "
                                          "Run once; do not poll more often than every 10 seconds."}, indent=2))
        return 0
    if not args.gpu_uuid:
        parser.error("--live requires --gpu-uuid; obtain it from an existing inventory")
    if args.output and args.output.exists():
        parser.error("--output already exists; retain captures without overwriting")
    try:
        command(args.gpu_uuid)  # Validate identity before opening even the local lock file.
        if os.geteuid() == 0:
            raise ValueError("live collection refuses root; do not elevate permissions")
        with monitoring_slot():
            record = collect(args.gpu_uuid)
        encoded = json.dumps(record, indent=2) + "\n"
        if args.output:
            with args.output.open("x") as stream:
                stream.write(encoded)
        print(encoded, end="")
        return 0 if record["status"] == "observed" else 1
    except (ValueError, OSError) as exc:
        print("collection refused: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
