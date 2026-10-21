# Testing and reproduction

The tests exercise file parsers, recorded driver requests, telemetry decoding and
the monitoring collector's response handling. Collector responses are fixtures;
the suite does not query a GPU.

## Run the tests

Use a CPU-only Linux environment with Python 3, a C compiler, Capstone and
Bubblewrap available:

```sh
bash scripts/run_cpu_only.sh bash tests/check.sh
```

The wrapper gives the process a read-only repository, private `/dev` and `/tmp`,
and no network, sysfs or host service sockets. Build products go into its
temporary directory. The same gate can run directly with `bash tests/check.sh`
on an environment that already has no GPU access.

The latest retained [test log](../research/2026-10-21-record-producer/check.log)
records 41 Python tests, 29 offline-record checks and the C/CLI fixture checks.
Those results test software behavior, not hardware state or driver safety.

[GitHub Actions](../.github/workflows/offline-checks.yml) runs the gate on Ubuntu.
Its [dependency file](../tests/requirements-cpu.txt) pins the Capstone wheel and
hash for the x86-64 runner. It is specific to that CI environment.

## Reproduce a firmware analysis

Each dated directory under `research/` contains its own inputs manifest, scripts,
results and `SHA256SUMS`. The binaries are not included in Git. Supply the exact
copied files and source revisions named in that directory's manifest.

For example, the object/getter analysis uses Capstone 5.0.7 and Unicorn 2.1.4:

```sh
# The output directory must not already exist.
bash research/2026-10-21-object-origin/reproduce.sh /tmp/object-origin-replay

# Regenerate only its JSON results for a byte-for-byte comparison.
bash research/2026-10-21-object-origin/reproduce.sh /tmp/object-origin-json --json-only
```

The analysis scripts run inside the CPU-only wrapper. Emulation uses synthetic
objects and explicit replacements for unresolved services. Each report lists
those replacements and the instruction where execution stops. Keep them visible
when interpreting the result.

Older validation records are retained in the
[workflow archive](../archive/2026-10-21-workflow-notes/VALIDATION.md). Their test
counts and platform details apply to the recorded revision.
