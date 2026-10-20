# Pre-enumeration observations — no hardware intervention
If a GPU does not enumerate or the driver cannot report it, the fixed documented monitor
may have no data. Record the failure and stop. This project does not repair or reinitialize
the card to obtain more information.

Use already available inventories, OS logs and prior captures to note the last known UUID,
BDF, firmware/driver version and observed error. Compare applicable public init/loader
paths offline. Bus presence does not prove all rails, firmware or memory are healthy;
absence does not uniquely identify a bad GPU.

Withdrawn from the earlier workflow: setpci/config sweeps, ROM mapping, bug-report or
debugger escalation, slot changes, insertion/power sequencing, probes, synthetic loads,
soaks and memory stress. In particular, never treat physical insertion as an energized
test procedure. No such action is authorized here, on this GPU or through passthrough.

A useful deliverable is an evidence-bounded failure-stage hypothesis with competing causes
and missing information. Obtain deeper software understanding through offline RE instead.
