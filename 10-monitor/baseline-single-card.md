# Baseline methodology - single card, zero capital (10-monitor revision)

The 08-field baseline assumed 20+ cards per SKU. The actual constraint: ONE card,
software-only, no synthetic stress. This redesign is honest about what that buys.

## (a) What a single-card longitudinal baseline CAN and CANNOT detect

CAN (longitudinal, same-card):
- **Degradation over time on this card**: ECC counter rate acceleration, thermal
  creep at the same load (cooler aging), fan-response decay (bearing wear), VF
  offset drift (silent factory-OC reversion or silicon aging), clock-stability
  collapse under the same workload, PCIe retry growth (connector oxidation),
  power-oscillation growth (VRM aging proxy)
- **Sudden changes after events**: driver update, dust cleaning, thermal paste
  replacement, case change - the before/after delta is the whole diagnosis
- **Workload-correlated anomalies**: throttle onset at a lower load than the
  card's own historical onset

CANNOT (population, multi-card):
- **Population outliers**: with n=1 there is no distribution - a card that has
  ALWAYS run 8C hotter than the SKU median cannot know it. Detection of a
  factory-lemon requires the crowdsourced extension (c) or vendor data.
- **SKU-normalized verdicts**: "your 41C idle is fine" is unknowable without
  the population. Say "41C, your history: 40-42C, stable" - honest and useful.
- **Silicon-lot variation**: two cards of the same SKU can legitimately differ.

## (b) Minimum observation protocol (user-run, no synthetic stress)

The card's own workloads ARE the load points. The protocol:

1. **Setup (once, 10 minutes)**
   - Install the collector; run `--dry-run` to confirm the surface
   - Record identity (auto): model, vBIOS, driver, GSP fw, UUID (procfs)
   - Record the machine context: case type, ambient season, typical room temp

2. **Baseline capture (2 weeks of normal use, zero user effort)**
   - Collector runs at login (user autostart), 60 s interval (negligible load)
   - The tool tags each sample with an hour-of-day and day-of-week so recurring
     usage patterns become comparable windows
   - No synthetic load EVER: the workload is whatever the user does (gaming,
     inference, browsing). The collector learns the card's NORMAL.

3. **What the two weeks produce**
   - Temperature-vs-power curve family (the card's thermal signature)
   - Fan-response coefficient (RPM per watt) at the user's real operating points
   - Idle baseline: the P8 power/temp band (most stable, most comparable)
   - ECC counter start point + first growth-rate estimate
   - VF offset reference values (and stability thereof)
   - Throttle-onset power/temp for the user's actual workloads

4. **Ongoing monitoring (automatic)**
   - Weekly robust summary: median/MAD of each signal per usage window
   - Alerts (local, opt-in): temp creep > 3C at same power window, fan RPM
     decline > 10% at same thermal load, new ECC uncorrectables, VF offset
     drift, throttle onset at lower load than historical
   - All comparisons are longitudinal (this card vs this card's own history)

5. **Optional 10-minute checkups (user-triggered, still no synthetic load)**
   - "Idle check": machine undisturbed 15 min -> compare to the idle band
   - "Post-update check": after any driver update, flag the version change in
     the series (baselines are version-scoped - see 08-field methodology)

## (c) Crowdsourced extension - how to get 20 cards per SKU without buying them

The users' own baselines ARE the population, if they opt in.

### Submission schema (the minimal safe payload)
```json
{
  "schema_version": 1,
  "sku": "GeForce RTX 3090",                 // from procfs Model
  "board_variant_hash": "h<16hex>",          // HASH of subvendor+subdevice ID
  "vbios": "94.02.42.00.F4",                 // version string (not the ROM)
  "driver": "615.71.09",
  "gsp_fw": "615.71.09",
  "cooling_class": "open_bench|air_case|aio_240|aio_360|custom_loop",  // user-declared
  "ambient_bucket": "18-20C|20-24C|24-28C|28C+",                       // user-declared bucket
  "usage_class": "gaming|inference|render|mixed",                      // user-declared
  "baseline_window_days": 14,
  "features": {                               // robust statistics per signal
    "temp_idle_median_c": 41.0, "temp_idle_mad_c": 0.5,
    "temp_load_p50_c": 71.0, "temp_load_p95_c": 76.0,
    "power_load_p50_w": 320.0, "power_load_p95_w": 348.0,
    "power_oscillation_index": 0.07,
    "fan_rpm_at_p50_load": 1350, "fan_response_coef": 4.2,
    "clock_load_p50_mhz": 1785, "clock_dip_rate_per_hour": 0.2,
    "ecc_correctable_delta_per_week": 0, "ecc_uncorrectable_total": 0,
    "vf_offset_gpc": 0, "vf_offset_mem": 0,
    "pcie_retries_delta_per_week": 12,
    "throttle_onset_w": null, "throttle_onset_c": 78
  },
  "tool_version": "collector-1.0",
  "consent_version": "privacy-1.0"
}
```

### Privacy model (non-negotiable)
- **No serial numbers. No clear UUIDs.** The UUID stays local; submissions carry
  a locally-generated random submission ID. If longitudinal self-comparison on
  the server is desired, it uses a salted hash of the UUID (salt kept on the
  user's machine, never uploaded) - the server sees a stable pseudonym it
  cannot reverse.
- **board_variant_hash**: subvendor/subdevice IDs are hashed so AIB variants
  cluster without exposing the user's exact config.
- **Ambient/usage are user-declared buckets**, not measurements (no location
  inference).
- **Opt-in only, per submission, revocable**: the collector shows exactly what
  will be sent (the schema above) before sending; there is no automatic upload
  without a visible consent action.
- **No workload content**: timings and counters only - never process names,
  never the XID log text (XID lines can embed process info; only the count and
  XID number are shareable).

### Dedup and quality
- One submission per (submission ID, week) - updates replace, not append
- Reject: windows < 7 days, < 100 samples, or > 50% errored samples
- Outlier screening at aggregation (not deletion): robust-z against the
  current distribution; flagged rows still count but are tagged
- Version scoping: distributions are per (SKU, driver-major) - a driver change
  legitimately moves some signals

### How submissions turn into the population baseline
1. Aggregate by (SKU, board_variant_hash, cooling_class, ambient_bucket,
   driver-major) - the comparison key used at diagnostic time
2. A SKU joins the "diagnosable population" set at **n >= 5** usable submissions
   (LOW-CONFIDENCE bands), reaches **n >= 20** (full bands)
3. At diagnostic time the engine picks the narrowest matching aggregate with
   n >= 5 and reports: robust-z per feature + the matching cohort size
4. Every verdict displays the cohort it compared against - no hidden baselines

This is how the 08-field "20 cards per SKU" requirement is met without capital:
the crowd donates the population, one baseline at a time, with the privacy
model making the donation safe.
