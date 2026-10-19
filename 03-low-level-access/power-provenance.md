# Power-limit provenance - constraint-source analysis (packet D continuation)

Per RESEARCH-DIRECTION.md "constraint-source analysis": distinguish requested, default,
enforced and measured power. All values for the lab rig (RTX 3090, UUID 8a9c05b3..., driver
615.71.09) unless noted. Statuses per the discipline.

| Source | Value | Units (status) | When observed | Provenance |
|---|---|---|---|---|
| NVML power.limit (busy, P2) | 420 W | W - cross-validated (nvidia-smi + XML) | 2026-10-15 12:22 | observed-bytes |
| NVML power.max_limit | 450 W | W - cross-validated | 2026-10-15 12:22 | observed-bytes |
| NVML power.default_limit | 420 W | W - cross-validated | 2026-10-16 12:47 | observed-bytes |
| NVML power.min_limit | 100 W | W - observed-bytes | 2026-10-16 12:47 | observed-bytes |
| NVML power.limit (idle, P8) | **370 W** | W - cross-validated (dynamic, P-state-coupled) | 2026-10-16 23:17 | observed-bytes |
| RM control 0x2080a61d @+4 | 370,000 | **mW - hypothesis** | 2026-10-15 21:33 (P2, limit 420) AND 2026-10-16 12:47 (P8, limit 370) | observed-bytes; invariant across states |
| vBIOS PowerPolicyTable +0xc4 | 450,000 / 520,000 | mW - hypothesis (corpus variants 0B/44 vs 0F) | 2026-10-16 | observed-bytes |
| 0x2080a612 / 0x2080a618 | 54,352 B / 20,512 B payloads | unknown (capture-truncated) | 2026-10-16 | observed-bytes |

## Open constraint questions
1. Which source NVML's power.limit reads from at runtime (a61d? a618 table? PowerPolicy?) - blocked on 0x2080a6xx response-struct decode (REA tooling).
2. Is 370,000 a per-rail (NVVDD) limit while 420,000 is total? Requires rail topology (PowerTopologyTable decode) or a paired multi-rail capture.
3. Does the 420->370 idle transition originate in the GSP policy engine (RM one-hot P-state input) or the driver? Distinguisher: paired traces at the transition (bench, or natural transition with sniffer2 attached - read-only, queued).
4. vBIOS PowerPolicy 520,000 in variant 0F vs 450,000 in 0B/44 - board-class difference; requires the variant board names (corpus metadata gap).

## Discipline notes
- Natural state variation only; temporal correlation != causation.
- No setters used; NVML getters are read-only but may wake hardware (documented).


## UPDATE (2026-10-18): limit provenance resolved by disproof - a61d is NOT the live source

Per-selector captures (power.limit / max / default / min, each a separate nvidia-smi run under
sniffer2) show **zero 0x2080a61d calls**. Every limit field rides the **client-level control
0x00000214 (384 B response)** issued once per query session - all limit values arrive in that
one structure. The a61d call fires once during init regardless of which fields are queried.

Revised provenance:
- NVML limit fields (limit/max/default/min) <- client control **0x00000214**, 384 B response
  [observed-bytes; field offsets within the 384 B not yet decoded]
- 0x2080a61d (12 B, u32 mW @+4 = 370,000 invariant) = auxiliary init-time quantity
  [hypothesis: per-rail or policy scalar; NOT the NVML limit source]
- rmctl implication: the decode target for limits is 0x00000214's response, not a61d.

Also decoded from IDA (objdump-verified): the a61d handler takes a SELECTOR byte
(0xFD/0xFC/0xFE per switch case ebx=1/2/0) in the 12-byte request and dispatches through
the TSAPI table (fn at +0x8c) - three limit-type variants of one sub-command.


## UPDATE 2 (2026-10-18): the 0x214 params buffer is NOT the data carrier

Full-trace evidence (50-call session log): the 0x214 (384 B) control's params buffer shows
essentially NO RM writes (first_diff@+1 = one byte) - yet NVML prints all five limit fields.
The per-field query runs also show the 0x214 call identical regardless of which field is
queried. Conclusion: **the client-level control family (0x0000xxxx) exchanges data through
an opaque driver-internal channel (NVML RPC protocol), not through the ioctl params buffer**
the way RM_CONTROL (0x2a/NVOS54) does. Param-buffer diffing - the technique that fully
decoded the 0x2080a6xx family - cannot see client-control data by construction.

Provenance state (final for this packet):
- NVML limit fields: transported via the opaque 0x0000xxxx client-control channel
  [observed-bytes: transport; field offsets: UNOBSERVABLE via param diffing]
- 0x2080a61d: decoded structurally (selector + 12 B, u32 mW @+4) but NOT the limit source
- Next decode path if ever needed: IDA analysis of NVML's 0x214/0x215 handler
  (where it parses the opaque response) - offline, REA/IDA session capable.


## PACKET E progress (2026-10-18, offline objdump decode)

The 0x214 call site found (file 0xa5b78, `mov ecx,0x214` + TSAPI dispatch fn 0xa5880,
params 0x180 bytes, on client obj): its response is parsed by a large parser function
that (a) validates the status (`cmp $0x57` = 87 = NV_ERR_INSUFFICIENT_PERMISSION?),
(b) parses entries, (c) **qsorts them** (call 22190 @0xa5e53), and (d) stores
{count @ global+0x1269670, table @ global+0x1268434}.

Status: the opaque channel is now mapped to its parser; remaining work = decode the
entry layout + the limit-field offsets within the 384 B response (next pass, same method).
The qsort implies the entries are per-something sorted (per-domain? per-limit-type?).


## PACKET E FINAL STATUS (2026-10-18, round 11 of goal)

Delivered: the opaque channel mapped end-to-end structurally:
- call site 0xa5b78 (mov ecx,0x214 + TSAPI invoker 0xa5880, 0x180 B params on client obj)
- response = entry list (u32s, 0xFFFFFFFF-terminated), iterated with per-entry follow-up
  12-byte controls (0x21b family)
- parsed entries qsorted and stored {count @ global+0x1269670, table @ global+0x1268434}

Precisely named open item: the FIELD OFFSETS of the limit values within the per-entry
12-byte detail responses (the observed 12B payloads {06 00 ...} did not contain the
370,000-mW values in simple encodings - the per-entry structure needs sustained
disassembly passes or a bench differential). This is the single remaining sub-decode
for complete power provenance.


## PACKET E COMPLETE - BoardObj enumeration API decoded (2026-10-19, REA/IDA sub_A5B10)

sub_A5B10 (0x65b B) = the full client-control enumeration:
1. **0x214 (532)** -> 384 B: entry-ID list (u32s, -1 terminated, <=96 entries), iterated from v36[128]
2. **0x21b (539)** -> 12 B per entry: detail record
3. **0x275 (629)** -> 268 B per entry: {u32 @+4; u16 @+8; u16 @+10; **char name[80] @+8 via strncpy**}
4. Results **qsorted** (comparator sub_A6170, 12 B elements) and stored:
   count @ global+0x1269670, table @ global+0x1268434 (+ per-entry name[80] at +19301428 rel)

This is NVIDIA's **BoardObj enumeration API**: the entries are named board objects
(power rails, limit types) - the 80-byte name string would reveal the object identity
directly (e.g. the limit-type names). Status: mechanism source-decoded; the NAME capture
(one 268 B 0x275 response read) = the single remaining observation to enumerate the
object names, completing power-limit provenance.

- NOTE (capture attempt): the 0x275 per-entry name call does NOT fire during the
  power.limit query path (traced: 0x214 -> 0x21b x1 -> client controls -> end).
  It fires under a different NVML query path - identify which nvidia-smi query
  drives sub_A5B10's second loop (or call it via a direct test harness) to capture
  the 268 B name responses. The BoardObj API structure itself is fully decoded.
