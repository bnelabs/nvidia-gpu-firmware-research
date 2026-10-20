# Capability gaps — documented, candidate and unknown
The aim is understanding and monitoring, not an unvalidated diagnostic sales claim.

| Capability | Evidence status |
|---|---|
| Standard identity, board power, die temperature, clocks, utilization, P-state, fan percent, PCIe link state | Documented telemetry; availability depends on exact device/version |
| Public power/clock sampling | nvmlDeviceGetSamples is documented; local support/cadence not established by checking a nonexistent separate function |
| Public clock VF offsets | Documented getters exist; configured offset is not measured rail voltage or an aging detector |
| Per-rail power / voltage / VRM-zone temperature | Research candidates; strings/classes do not prove a usable GA102 payload or sensor |
| PMU/clock-margin/MMA methods | Host-symbol/dispatch leads; exact schema, availability, public alternatives and usefulness need offline verification |
| Physical component diagnosis / remaining life | Not established by this repository |

Reading a counter does not prove its cause. Error counts, limits and temperatures are
triage context; they do not uniquely identify VRM aging, bad solder, a power supply or
failed memory. Unsupported values remain unknown, not zero or hardware failure.

Compare the documented API, exact artifact and board support separately. No percentages
of fault coverage, commercial differentiation or diagnostic accuracy have been validated.
Hardware investigation and physical tests are not part of this project.
