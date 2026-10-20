# Passive comparison methodology
Compare existing observations under naturally occurring workloads. Do not generate load
points, stress the GPU, change settings or force thermal/power transitions for a baseline.

A comparable sample identifies chip/board, driver/firmware, power configuration, workload,
ambient context if known, time window and API units/status. Keep unsupported readings
missing. Compare like versions/configurations before broadening across boards or generations.

Use descriptive distributions only when samples are sufficient and comparable. Do not
translate an arbitrary z-score, clock offset or rail-candidate value into remaining life
or a confirmed hardware fault. Temperature margin and clock margin are different metrics.
No SKU sample count or diagnostic accuracy is established by this planning note.

The source of detailed signals remains an offline research question. Existing API output
can be monitored; private reads and workload manipulation cannot be used to fill gaps.
