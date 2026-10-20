# Revised business case - verified-only features, single-card, software-only

This rewrites 08-field/public-vs-re.md against three facts the verification and
the audit produced: (1) two differentiators (VRM zone temperature, rail voltage)
are unverifiable under the no-live-experimentation constraint and are removed
PERMANENTLY from the product claims; (2) a non-enumerating card cannot be
diagnosed by software at all - the dead-card workflow is out of scope, replaced
by a referral-partner model; (3) the population baseline is pending
crowdsourcing, not pending capital.

## Removed permanently (do not sell, do not promise)

| Removed claim | Why |
|---|---|
| VRM-zone temperature attribution | INFERRED (08-field D1): THERM class exists but the SDK has no therm header, no VRM sensor string in the GSP corpus, and verification requires a wire-capture session the operating constraint forbids. |
| Rail voltage readback | INFERRED: class 0x12 exists, payload never captured, host read path unproven; same constraint. |
| Per-rail power breakdown | REMOVED from v1 for a different reason: it was source-pinned, but it is an RMCTRL/BoardObj path, NOT NVML - and the v1 product constraint is NVML+logs only. It returns if/when a v2 adds read-only RMCONTROL support with a customer waiver. |
| Dead-card bench diagnosis | Not software-diagnosable at all (a non-enumerating card exposes no signal to any API). Replaced by referral (below). |

Note the GPC/MemClk VF-offset reads SURVIVE - but for an unexpected reason found
in the audit: they are PUBLIC NVML on 615.71.09 (nvmlDeviceGetGpcClkVfOffset /
GetMemClkVfOffset both return data). The value is real; the exclusivity is not -
every monitoring tool can read them. They are table stakes, not differentiation.

## The dead-card problem: referral partner model

A card that does not enumerate exposes zero software signals (08-field D2 stages
0/3 are physical). The honest product answer:

- The monitor detects the TRANSITION: a card present in yesterday's series that
  is absent from the bus today (collector logs driver-load failure or absence)
- The product then hands off: a referral to a partner bench lab (the 08-field
  physical tier) with the collected history attached - the longitudinal data is
  exactly what makes the bench diagnosis faster and cheaper
- Revenue model: referral commission / partner-billing, not software billing

## Pending crowdsourcing (not capital)

The population baseline - the only way to say "your 41C is normal" - comes from
opt-in submissions of user baselines (10-monitor/baseline-single-card.md (c)).
n=5 gives LOW-CONFIDENCE bands; n=20 gives full bands. The bottleneck is users,
not hardware purchases. Until a SKU reaches n>=5, verdicts are longitudinal-only
and say so.

## Surviving differentiators (verified, with D1 confidence)

| Differentiator | Confidence | Source | Exclusive? |
|---|---|---|---|
| Longitudinal per-card drift detection (temp creep, fan decay, VF drift, ECC rate, throttle-onset shift) | HIGH | collector, all NVML | YES - vendor tools do not track history; this is the core product |
| Power-oscillation index (VRM-aging proxy from NVML power trace) | HIGH | derived from GetPowerUsage time series | YES - derived metric, not a raw read |
| Clock-stability index (dip rate under the user's real workloads) | HIGH | derived from clock samples | YES - derived |
| High-frequency power telemetry | MEDIUM-HIGH | nvmlDeviceGetPowerSamples ABSENT in 615.71.09 - our PMU path was the differentiator, but it is NOT in the v1 (NVML-only) scope; v1 uses the 1 s power trace as a partial substitute | partial in v1 |
| XID-context correlation (XID events vs the telemetry timeline) | HIGH | kernel-log parsing + series timestamps | YES - vendor tools dump logs but do not correlate with the sampled timeline |
| Version-scoped baseline comparisons (before/after driver updates) | HIGH | collector identity + series | YES |

## The one-sentence product

**A privacy-safe, read-only monitor that learns what YOUR card looks like when
healthy - and tells you, in plain language, when it stops being that (with the
evidence), for less than the cost of one hour of bench labor - with free
tier-1 facts (nvidia-smi's job) clearly separated from the longitudinal
intelligence you are actually paying for.**

Concretely: the free layer is the live readout (nvidia-smi parity - price: zero);
the paid layer is the longitudinal baseline + drift verdict + XID-correlated
incident history + crowdsourced population bands as they form. The customer gets
early warning of cooling aging, ECC-accelerated VRAM decline, VRM-oscillation
growth, and post-update regressions - on a working card, with zero risk to it,
because the product never writes anything.
