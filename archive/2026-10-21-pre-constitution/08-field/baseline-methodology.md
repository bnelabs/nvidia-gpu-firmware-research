> HISTORICAL / SUPERSEDED. Not an authorized runbook. Claims may be retracted. Read current CONSTITUTION.md and CORRECTIONS.md at the repository root.

# Baseline methodology - the product is what healthy looks like

A diagnostics service's real asset is not the fault map; it is the distribution
of healthy values per SKU per condition, collected under controlled conditions,
against which a customer's card is compared at diagnostic time. This document
defines the method. No data is collected here.

## Principle

Fault diagnosis by absolute thresholds fails because healthy values vary by SKU,
driver version, ambient, and workload. Diagnosis by RELATIVE comparison (card vs
its SKU distribution vs its own history) survives that variance. The product is
the baseline store + comparison engine.

## What to sample (the baseline feature vector)

Per card, per condition (see load points):

Identity (static):
- SKU name, device ID, subvendor/subdevice (AIB variant), vBIOS version, driver
  version, GSP firmware version, UUID (longitudinal key)

Signals (from signal-inventory.md, with layer):
- N: die temp at idle and at load plateau, fan RPM at load plateau, power draw
  average over a fixed window, clock per domain at load plateau, P-state,
  throttle bitmask (should be clean), memory info
- R: ECC volatile counts (snapshot + delta), remapped rows/histogram/banks,
  PEX counters (snapshot + delta over the load window), FB info
- G (our tier): per-rail power average+peak per rail, VF offset values
  (GpcClk, MClk), clock margin, PMU sample statistics (mean/percentiles/max of
  the power trace), rail metrics statistics

Derived (computed at capture):
- Power oscillation index: stddev/mean of the power trace over the window
- Clock stability index: count of clock dips > 5% during the load window
- Rail imbalance index: max/min rail average ratio
- Thermal ramp rate: seconds from idle to load plateau temp
- Fan response: RPM delta per watt delta (cooling effectiveness coefficient)

## Load points (controlled conditions)

| Point | Definition | Purpose |
|---|---|---|
| P0 idle | driver loaded, no compute, 10 min settle | idle temps, fan floor, idle power |
| P1 memory-only | memory bandwidth stress (read/copy mix), 15 min | VRAM thermal + ECC exposure without core load |
| P2 compute-plateau | fixed deterministic compute load, 20 min to thermal steady state | sustained power/clock/temp plateau |
| P3 transient | step load on/off cycles (30 s on, 30 s off, x10) | transient response, rail spikes, fan inertia |
| P4 cool-down | passive after P2, 10 min | thermal mass sanity (abnormally fast/slow = cooler issue) |

Environment controls (must be recorded with every baseline):
- Ambient temperature at card intake (NVA/hygrometer), target 22 +/- 2 C
- Case configuration (open bench vs closed case - baselines must match the
  customer's context or be labeled open-bench)
- Driver + firmware version pinned (baselines are version-scoped)
- Fan curve at default; no user OC (document any pre-existing OC and either
  reset to defaults with permission or tag the baseline non-standard)

## How many cards per SKU

| Purpose | Sample size |
|---|---|
| Initial SKU distribution (mean + std of every feature) | 20+ cards, spread across AIB variants |
| Acceptable interim reference (before 20 collected) | 5 cards + vendor spec sheet limits, marked LOW-CONFIDENCE |
| Per-AIB-variant refinement | 5+ per variant (coolers differ by AIB) |
| Driver/firmware version refresh | 5 cards re-run per major driver release |

Statistics: store median, MAD (robust), and 1st/99th percentiles per feature per
SKU per condition. Flag features that are bimodal (likely two AIB subvariants) -
split the baseline before using it.

## Storage model

- Key: (UUID) for longitudinal; (SKU, variant, driver, fw) for population.
- Record: raw feature vector + derived indices + capture conditions + tool
  version + hash of the capture log (tamper-evidence).
- Comparison at diagnostic time:
  1. Locate the population baseline (SKU+variant+version; fall back one level
     with a confidence penalty if missing)
  2. Compare the card's features vs the distribution: z-score per feature
     (robust z = (x - median)/MAD)
  3. Longitudinal check: card vs its own past (drift detection is often more
     diagnostic than population rank)
  4. Verdict: |robust z| < 3 = within family; 3-5 = watch; > 5 = anomalous
     (feature-specific triage via fault-triage-map.md)
- Versioning: baseline schema versioned; old baselines remain queryable;
  every baseline records which decode/tool version produced it.

## Controlled vs passive measurement

| Measurement | Mode | Why |
|---|---|---|
| Load plateau temps/power/clocks | CONTROLLED (P2/P3 harness) | condition variance must be minimized |
| Idle temps/power | CONTROLLED (P0) | ambient must be known |
| ECC deltas | PASSIVE + controlled delta over P1/P2 | long-term rates need both |
| PEX counters | PASSIVE over the load window | trend is what matters |
| VF offsets | PASSIVE (any condition - they are state, not load-dependent) | |
| Clock margin | PASSIVE (state read) | |
| PMU traces | CONTROLLED (P3 transients are the informative part) | transients are the signal |
| Thermal ramp / cool-down | CONTROLLED (P2/P4) | needs known ambient + load |

## What this is not

- Not a benchmark: no score comparison against other brands.
- Not an endurance test: P2 is 20 minutes, not hours.
- Not a tuning service: nothing is written (see operating-envelope.md).
- Not a substitute for the physical tier: the baseline flags the anomaly; the
  bench finds the component.
