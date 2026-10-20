# Observation method — retained artifacts, no live tracing
Live preload interposition, strace attachment, kernel probes, debugger attachment and
process-memory snapshots are outside this project's constitutional scope.
A tracer forwarding an operation does not make that operation read-only or safe.

Use existing trace files, ordinary pre-existing logs and copied libraries/firmware.
The active sniffer2 module decodes supplied byte arrays only. It has no callback,
interceptor, live pointer access or driver dependency. Historical tracer recipes are
retained in Git/history for static study, not execution.

For each old trace record retain original length/hash, ABI, input and output, syscall
return and RM status. Record truncation. Do not promote a changed byte into a field
meaning without a versioned schema or proven consumer. Missing context stays unknown.
