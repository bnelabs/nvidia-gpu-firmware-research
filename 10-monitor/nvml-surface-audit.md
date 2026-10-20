# NVML surface audit — corrected evidence scope, 2026-10-21
The prior worker report described export enumeration and live ctypes calls against
615.71.09. It did not retain enough exact signatures, statuses and raw call outputs in
this document to independently reproduce every support claim. Wrong-signature calls
cannot establish a device capability or that the public header is incompatible.

## Corrections
- Public NVML P-states are ordinal, not RM one-hot masks.
- nvmlDeviceGetApplicationsClock (singular) is documented; a plural lookup is not evidence
  of a driver rename.
- GetPowerSamples is not the public comparison to use. nvmlDeviceGetSamples documents
  power sampling, with device/version support to be established separately.
- Fan v1/v2 have distinct contracts; INVALID_ARGUMENT does not establish signature
  migration or deprecation. Never guess arguments and retry live.
- Clock-offset getters are public. An offset is not measured rail voltage or aging.
- Temperature margin is not clock-frequency margin.
- NOT_SUPPORTED on one call/version/path cannot establish a whole GeForce capability
  class or prove an alternative raw RM read works.

Sources: [NVIDIA device queries](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceQueries.html)
and [device enums](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceEnums.html).

## Current collector contract
Use only scripts/capture_state.py's fixed nvidia-smi field list for permitted ordinary
monitoring. Its default is an offline plan. No ctypes, symbol-probing loop, automatic API
fallback or arbitrary struct call is included. Existing UUID identity is required.

Further surface auditing is offline: hash the exact library/header, export symbols and
recover contracts from the correct version. Retain per-function ABI evidence and separate
documented, symbol-present, historical-reported-success and independently reproduced.
No new GPU calls were performed for this correction.
