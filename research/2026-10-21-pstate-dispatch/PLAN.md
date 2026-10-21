# P-state dispatcher packet

Question: how does the copied 615.71.09 library route a public P-state query, and
can retained log behavior be explained without inventing a hidden power channel?

Competing explanations: direct control 0x20802068, RM User Shared Data (RUSD),
alternate callback, clock remap, or missing capture coverage. Cheapest offline
discriminators: IDA decompilation checked against raw instructions/relocations,
constructor base arithmetic, RUSD schema layout, controlled synthetic memory,
exact-release source and copied GSP strings/code. Stop at unsupported dispatch
or mappings and report the next missing consumer. No new live observation.

Preservation checkpoint before this packet:
`../nvidia-offline-pstate-preserve-20261021T070430Z/workspace.tar.gz`, SHA-256
`c0a89dcc80539daa27b1fd834f19948077865c93e7ad93d915617ceaab67e6bc`.
Original uncommitted packet files remain in place. A new evidence directory
retains this packet separately.

REA now opens the pre-existing copied `/build/libnvidia-ml-615.71.09.so` in the
ida94 analysis container, with the exact expected hash. Read-only Docker
configuration inspection reported privileged=false, Devices=[], DeviceRequests=null,
CapAdd=null, PidMode="", Mounts=[] and network mode bridge. No Docker configuration
was changed. Static IDA queries only; no target execution, debugger or GPU service
connection. Local experiments execute through scripts/run_cpu_only.sh, without
network or GPU device passthrough. The adapter reports its own version, not a
verified IDA engine version; its database limitations are retained verbatim.
