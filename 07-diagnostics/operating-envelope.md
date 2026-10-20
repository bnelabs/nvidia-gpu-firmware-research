# Operating envelope
[CONSTITUTION.md](../CONSTITUTION.md) is binding. The old waiver/tier/bench framework is
withdrawn: consent labels do not establish that an operation is non-intrusive.

Allowed: deep offline RE and file analysis; existing logs/captures; one fixed documented
UUID-selected telemetry query when explicitly requested for ordinary monitoring.
Run it unprivileged, without instrumentation, at no more than one query per 10 seconds.
Default collector invocation does not contact hardware. Stop on errors; do not recover.

Excluded: custom RM/GSP, undocumented getters, broad config or raw register/ROM/fuse reads,
live debugger/tracer/injection, firmware/driver changes, settings changes, resets,
suspend/GC6, fault/stress/thermal tests, physical intervention or permission bypass.
There is no test-bench exception. Statically understanding those operations is allowed.

Do not equate no persistent change with no write: transient actions and reads may have
effects. Do not promise zero risk, negligible overhead or a guaranteed diagnosis.
The worker's permission boundary is external to this repository; no file here revokes
permissions from a process already running elsewhere.
