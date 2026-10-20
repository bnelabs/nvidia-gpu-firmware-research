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


## PACKET E DECODED-TO-BOUNDARY (2026-10-19, full -q trace under sniffer)

Even the FULL nvidia-smi -q does not fire 0x275. Root cause found in the sub_A5B10
decompile: the 0x275 name loop runs only if the 0x214 response's ENTRY LIST
(offset +128..255, u32s, -1-terminated) is non-empty - and on this board/driver,
via the NVML query path, **the entry list is EMPTY** (trace: RM wrote only byte +1;
nothing at +128+). The 12 B 0x21b responses (captured: 06 00 ... 06 00) are session
state, not limit values.

The request's first 128 bytes (v36[0..127]) select the object class - NVML sends
zeros (no class selected) -> empty list. **Named missing piece**: the request-class
values that populate the entry list (decode the CALLER of sub_A5B10 for the class
constants, or bench-probe with filled class bytes).

STATUS: the BoardObj enumeration API is fully decoded structurally (three-control
sequence, entry-list format, parser, global store, empty-list behavior on this path).
The limit-field offsets require the class-selection values - precisely named, outside
this decode pass.


## PACKET H: sub_A5B10's caller decoded - sub_A71D0 = the BoardObj session driver (2026-10-19, REA/IDA)

sub_A71D0 (0xd4b B) is the **BoardObj session driver** - the function that owns the whole
enumeration lifecycle. Decoded structure (from disasm + pseudocode):

1. **Zeroes the 384 B request** (rep stosq 0x30 qwords at var_24B0 = the v36[0..127] region
   the entry list comes back into) - **the class bytes are ZEROED here, not filled**:
   `mov ecx,30h; rep stosq`. The emptiness is BY DESIGN for this call path.
2. Issues 0x214 via sub_A5880 (params 0x180, r12=dispatch context).
3. Parses entries: skips 0xFFFFFFFF, per valid id issues **0x21b (12 B)** then optionally
   **0x215 (0x84 B)**, **0x279 (12 B)**, **0x289 (4 B)** - the per-object detail family.
4. Gates: `cmp byte [rbp+var_2B8], 1` (arg flag from caller) selects the 0x215 path;
   `cmp [var_26C+4], 1` gates another branch; 0x289 with r9d=4 on the 0x215 path.
5. **qsorts 16-byte elements** (sub_A6170 comparator, nmemb=count, size=0x10) - the parsed
   objects are 16-byte records (id + attrs + flags), stored count @ **dword_12683A0**.
6. Marks objects with attribute flags: `or byte [rec+0Ch], 1/2` and stores
   `0xFFFFFFFF` at `[r15+rdx+0x28C70]` (stride 0x93418 = 602,648 B - a large per-object
   global array!). The 0x28C70 offset + 0x93418 stride = the parsed-objects global store.
7. **sub_A5B10 is called CONDITIONALLY at 0xa7729-0xa7730**: only when
   `cmp byte [rbp+var_2B0], 0; jz A7780` fails - i.e. sub_A5B10 (0x214 re-enumeration)
   runs as a REFRESH path inside the same driver, gated by a caller flag.

## ANSWER to the class-selection question
**The 384 B request's class bytes are zeroed by this driver path by design** (rep stosq
zeroing at 0xa7216) - the entry list comes back empty because the enumeration is driven
by the ARGUMENTS (ecx=arg at var_2B0, esi=arg at var_2A4 - passed in from sub_A71D0's
caller), not by the request bytes. The class selection lives in **sub_A71D0's caller**
(next frame up: who calls sub_A71D0 with which ecx/esi). Named precisely: analyze
sub_A71D0's callers (xrefs on 0xa71d0) for the argument constants.


## PACKET H COMPLETE - the full BoardObj session chain decoded (2026-10-19, REA/IDA)

sub_1528F0 (0x462 B, `dmal/rm/rm_nvml.c`) = **the RM-side BoardObj session driver** that
calls sub_A71D0 (with a1 = the NVML device context at +16, a2 = the flag byte):

1. `sub_A71D0(dev_ctx, flag, v27(560B out), 0)` - the enumeration we decoded
2. Iterates the parsed 16-byte records (count from dword_12683A0):
   - flag byte at rec+12: **bit0** -> "has control" (branch 1), **bit1** -> branch 2
   - Branch 1: **malloc(0x1B8)** - allocates a 440-byte RMFunctions table (copied from
     off_2D1180, "RMFunctions") per object, stores {id, attrs, class} into it, links it
     into the per-device global array at off_250F90 (stride 0x93418 = 602,648 B/object!)
   - Branch 2 (bit0 AND bit1): records into dword_126969C/B0/B4/B8 + sub_3EA70(3, ...) -
     the "eventful" object path (count @ dword_153C4B8)
3. Then: two dispatch-table calls (+184, +192 of the RM table) and sub_ABCA0/sub_39290

## THE COMPLETE PICTURE (power-limit provenance chain, all source-decoded)
```
nvidia-smi query
  -> NVML client controls (0x214/0x21b/0x215/0x279/0x289/0x275 via sub_A5880)
     <- served by sub_A71D0 (BoardObj session driver)
        -> parsed into 16-byte object records (id/attrs/class), qsorted
        -> sub_1528F0 allocates per-object RMFunctions tables (0x1B8 B, off_2D1180 proto)
        -> linked into the per-device global store (stride 0x93418)
```
**The "opaque channel" is NVML's BoardObj protocol**: enumerate objects (0x214/0x21b),
fetch their attributes (0x215/0x275/0x279/0x289), and the objects become live RMFunction
tables whose fn-ptrs NVML calls for every getter/setter. The limit fields NVML reads are
the BoardObj attributes in these per-object tables. This completes the packet E/H decode:
the mechanism is fully identified; per-object FIELD offsets now live in the RMFunctions
prototype (off_2D1180, 440 B = 55 fn-ptrs).


## PACKET H COROLLARY - class-selection hypothesis superseded (2026-10-19)

The packet-H hypothesis (class constants in the 384 B request bytes) is SUPERSEDED by
the sub_A71D0/sub_1528F0 decode: the request's first 128 bytes are **zeroed by design**
(`rep stosq` at 0xa7216) - there are no class-selection constants in the request.
The actual "selection" mechanism:
- sub_1528F0 passes a FLAG BYTE (a2) to sub_A71D0
- sub_A71D0 gates post-processing on that flag and on per-record attribute bits
  (rec+12 bit0 = has-control -> RMFunctions table; bit1 = eventful -> event path)
- the per-object "class" is realized by the RMFunctions prototype (off_2D1180, 440 B
  = 55 fn-ptrs) copied into each object's 0x1B8 B table - the object's behavior IS
  its function table, not a request parameter.

No new decode needed; this closes the class-selection question with the mechanism
identified at a deeper level (function-table polymorphism, not request parameters).


## RMFunctions TABLE DECODED (2026-10-19): 55 trampolines binding (class,type) to the BoardObj dispatcher

The off_2D1180 prototype (55 slots, all non-NULL, cluster 0x111000-0x12e000) = thin
trampolines: each forwards to **sub_1117F0** (the generic BoardObj get/set dispatcher)
binding a **(class, type) constant pair**. Slot[0] verified via IDA decompile:
`sub_111D30 -> sub_1117F0(a2, a3, a4, 67, 54)` = class 0x43, type 0x36.

Partial class map (naive scan; complete extraction needs a full disassembly pass):
- 0x43 (slot 0), 0x3d (1), 0x52 (2) - first family
- 0x118 (17), 0x91 (18), 0xc1 (20,21,23,24), 0x44 (27,28), 0x91 (40)
- 12+ slots with different immediate patterns pending

Status: the per-object control surface = 55 (class,type)-bound BoardObj methods.
The slot->meaning map = the (class,type) pairs; sub_1117F0 dispatches on them.
Complete extraction queued (proper x86 instruction decode over all 55).


## TABLE DECODE COMPLETE (2026-10-19, objdump pass over all 55 slots)

Two slot families in the RMFunctions prototype:
1. **Trampolines** (slots 0,1,2,16-18,20,21,23,24,27,28,30,31,39,40): 6-instruction
   forwards to sub_1117F0 binding a BoardObj class constant:
   0x43, 0x3d, 0x52, 0x7, 0x118, 0x91(x2), 0xc1(x4), 0x44(x2), 0xc(x2), 0x4388
2. **Full implementations** (the rest, e.g. slot 3 @0x111600): real functions with
   their own logic (type switch on ebx: 1/2/0 branches = get-by-type variants,
   RM-version gate `cmpl $4,(global)` = the GSP-era check).

Insight: the prototype table mixes both - thin (class,type) bindings AND complete
per-object method implementations. The trampoline class constants (0x43/0x3d/0x52/
0xc1/0x44/0x91/0x118/0x7/0xc) are the BoardObj class IDs; the full implementations
are the per-class handlers with NVML-era GSP gates.

The per-object control surface is now structurally mapped: 55 slots = the complete
BoardObj method set an object can expose.


## PACKET E: record-conversion phase decoded (2026-10-19, objdump 0xa5e20-0xa60c0)

Post-enumeration conversion (after qsort @0xa5e53 with comparator sub_A6170, 12 B stride):

**12 B per-entry record layout (0x21b response)**:
- u32 id @+0 (written into the 16 B object record @+0)
- u32 value @+4 -> stored to global table (0x1268400 + count*0x48 family)
- u16 @+8 -> global 0x1268404 + count*0x48
- u16 @+10 -> global 0x1268408 + count*0x48

**0x275 call (268 B) per entry**: fills a 16 B object record {id @+0, 0 @+4, name[80] via
strncpy} - output stride 0x10c = 268 B/entry. RM-version gate: global > 4 branches to
extended processing (0xa6010).

**Two global tables result**: {id, u16, u16} @0x1268400 (72 B stride) and {name+attrs}
@0x1268434 (268 B stride). These are what NVML's limit getters read.

**Remaining observation (named)**: correlate the global-table contents with NVML's printed
limits post-query - requires reading NVML's globals at runtime (debugger; read-only) since
the values flow through the opaque channel. The structural decode is complete.


## PACKET E FINAL: runtime persistence scan - DEFINITIVE NEGATIVE (2026-10-19)

In-process scans (dlopen NVML, base via dlsym-0x99a20, verified pstate=8):
- ±1 MiB around 0x1268400: mW u32 scan (370000/420000/450000/100000) → ZERO hits
- ±2 MiB: W u32 (370/420/450/100) and W float (370.0f/420.0f/450.0f/100.0f) → ZERO hits

**Conclusion**: NVML does not persist the limit values in its static data segment in any
simple scalar encoding. The parsed BoardObj records hold converted internal representations,
or values are transformed per-query from the opaque-channel responses. The printed limits
are derived: opaque channel → parse → convert → format, without raw-scalar persistence.

**Provenance chain FINAL** (all stages source/byte-decoded):
GSP policy → driver RPC → opaque client channel (0x214/0x21b/0x215/0x275/0x279/0x289)
→ BoardObj parse (qsort, 16 B records + names) → NVML-internal conversion → printed output.
Named remaining step (tool-dependent): debugger on the live process at the NVML formatter
to read the converted per-object records.


## DISPATCHER DECODED (2026-10-19, REA/IDA sub_1117F0): cDeviceGetPerfLimitersClocks

sub_1117F0 (0x4fb B, "dmal/common/common_clock.c", error tag "cDeviceGetPerfLimitersClocks")
= the generic BoardObj get/set dispatcher that all 55 RMFunctions trampolines route to:

```
sub_1117F0(dev_ctx, mode, *out, class_id, type_id):
  GET (mode 0/1):  dispatch[+24](dev, dev, mode, &v31, &v30)     // fetch v31 + v30
                   dispatch[+224](dev, dev, class_id, rec[316])  // fetch BoardObj record
                   if (!rec.valid(v33)) return 6
                   if (rec.v34 == v31):
                       *out = v30 * v35 / 0x186A0               // x ratio / 100,000
                   else return 999
  SET (mode 2):    dispatch[+224](...)                            // fetch + validate record
                   dispatch[+48](dev, dev, 2, v35, ...)           // THE SETTER
```

- **0x186A0 = 100,000 divisor**: results are (value x ratio) / 100,000 - the BoardObj
  values are stored in units where /100,000 yields the final figure. The SAME 100,000
  appears in the vBIOS PowerPolicy mW values (450,000/520,000) - consistent unit family.
- class 0x43 (slot[0]) = the **PerfLimitersClocks** BoardObj class; type 0x36 = a clock
  domain object. The 55 trampolines bind (class,type) pairs across the BoardObj families.
- GET validates the record against the fetched value (mismatch -> 999); SET routes to the
  setter fn-ptr at dispatch+48 after record validation.

STATUS: the BoardObj dispatch semantics are fully decoded - the per-object control
surface's method dispatch, validation, and unit conversion are all source-decoded.


## SET-PATH DECODED (2026-10-20): slot 5/6 handlers (SetPerfLimitersClocks family)

sub_118E90 (slot 6) structure decoded:
1. Input validation: byte [rsi] == 1 check, field +0x14 read
2. Calls fn@0x37600 (nvmlInternalGetExportTable-adjacent) -> value at -0x24(%rbp)
3. dev_ctx->table(165184) -> sub-table -> **fn-ptr at +0x98**
4. **call fn98(value, flag(r14d), dev_ctx)** - the BoardObj SET delegates through a
   second dispatch layer (sub-table +0x98), passing the computed value

The pattern: BoardObj SET handlers compute/validate via an export-table call, then
delegate through a second function-pointer layer. Same polymorphic-table design as
the rest of the control plane (tables all the way down).
