# Pre-enumeration workflow - the card that does not come up

Ordered escalation for a GPU that is dead, half-dead, or fails under load.
For each step: signal, meaning, what it rules in/out, instrument required.
Steps marked [BENCH] require your own bench; [CUST] run on customer hardware;
[AUTH] requires written customer authorization before proceeding.

## Stage 0 - bus-level presence (no driver)

| Step | Signal | Meaning | Rules in/out | Instrument |
|---|---|---|---|---|
| 0.1 | lspci -nn (device present?) | card enumerates at all | present: config/power OK at bus level; absent: power, slot, or dead card | none |
| 0.2 | lspci -vvv (config space readable?) | vendor/device ID, BARs, link caps | config space readable = PCIe link trained and card responding; all-FF reads = dead card or dead slot | none |
| 0.3 | lspci -vvv link status (LnkSta) | negotiated gen/width | x16 gen expected: degraded = riser/slot/trace | none |
| 0.4 | setpci -s xx:00.0 COMMAND (read-only dump of key config regs) | bus master, memory decode enabled | decode disabled = BIOS/firmware init never ran | none |

Decision: card absent from bus -> skip software entirely; go to Stage 3 (power).
Card present with sane config space -> Stage 1.

## Stage 1 - link training classification

| Step | Signal | Meaning | Rules in/out | Instrument |
|---|---|---|---|---|
| 1.1 | LnkSta gen/width vs LnkCap | trained below capability | degraded gen/width = signal integrity | none |
| 1.2 | AER correctable error counters (OS) | replay/rollover growth | growing correctables = marginal link, reseat first | none |
| 1.3 | lspci -vvv repeated before/after load | stability of training | training drops under load = PSU transient or riser | none |
| 1.4 | second slot / second machine | isolate card vs environment | fails everywhere = card; fails one machine = slot/PSU/BIOS | [BENCH] second slot |

## Stage 2 - driver-attach failure (enumerates, driver fails)

| Step | Signal | Meaning | Rules in/out | Instrument |
|---|---|---|---|---|
| 2.1 | dmesg: BAR mapping errors, "Failed to allocate", GSP init logs | which init stage dies | GSP RPC timeout = firmware/board; BAR fail = memory map issue | none |
| 2.2 | nvidia-bug-report.sh output (read-only collection) | full state capture for later analysis | - | none |
| 2.3 | vBIOS identity readable? (nvmlDeviceGetVbiosVersion on healthy path; or ROM shadow dump via setpci expansion ROM read [AUTH: read-only ROM map]) | vBIOS intact? | ROM unreadable = strap/flash corruption -> physical | none ([AUTH] for ROM read) |
| 2.4 | temperature at idle (if NVML alive) | dead fan / sensor pegged | pegged max = cooler detached (shuts down early); pegged min = sensor dead | none |
| 2.5 | [BENCH] IR camera sweep at power-on, no POST | hot component before driver load | specific rail hot = short on that rail | IR camera [BENCH] |

## Stage 3 - power sequencing observation (card dead at bus level)

| Step | Signal | Meaning | Rules in/out | Instrument |
|---|---|---|---|---|
| 3.1 | external PSU wattage at idle (wall or inline meter) | short-circuit vs open | near-zero = dead card or no power rails; current spike trip = short | inline power meter |
| 3.2 | [BENCH] scope on 12V rail at PCIe connector during insertion | brownout/dip | dip = PSU or board short | oscilloscope [BENCH] |
| 3.3 | [BENCH] IR at power-on (see 2.5) | locate hot short | - | IR camera [BENCH] |
| 3.4 | [BENCH] visual: burned components, corroded pads, cracked PCB | obvious physical damage | - | eyes, loupe |
| 3.5 | [BENCH] diode mode across power rails (unpowered) | short to ground on a rail | identifies dead rail group | multimeter [BENCH] |

Note: this stage has NO software signal at all - it is entirely physical. The
diagnostics service prices it as a bench tier.

## Stage 4 - thermal-camera placement guide (keyed to what each region diagnoses)

| Region | What a hotspot there diagnoses |
|---|---|
| GPU die / cooler base | cooler mounting failure, dried paste, dead vapor chamber |
| VRM cluster (top of card, near 12V input) | MOSFET/driver IC failing, VRM overload |
| VRAM bank row (around GPU package) | failing memory rail or GDDR IC short |
| PCIe connector fingers | connector arcing / slot damage |
| Backplate over VRM area | VRM heat spreading into backplate (secondary sign) |
| Small ICs near the PCIe power plugs | auxiliary power-path failures |

Method: power-on sweep (no load), then load sweep (synthetic load) at fixed
distance/emissivity; compare against a known-good same-SKU card. [BENCH]

## Stage 5 - enumerates but fails under load (MATS/MODS-class memory probing)

MATS/MODS are NVIDIA internal memory test suites (field diagnostics used by
partners). The public equivalents a service can build read-only:

| Step | Signal | Meaning | Rules in/out | Instrument |
|---|---|---|---|---|
| 5.1 | ECC counters before/after a customer-run load (documented NVML) | correctable rate under load | growth = marginal cells | none [CUST] |
| 5.2 | Remapped rows delta after load (FB_GET_REMAPPED_ROWS) | new remaps during stress | new remaps = active VRAM degradation | none [CUST] |
| 5.3 | XID 48/62/63 correlation with load timeline | when corruption strikes | at temp = thermal-related VRAM; at power spike = VRM | none [CUST] |
| 5.4 | GSP-era rail metrics under load (our decoded path) | rail-specific anomaly | one rail spiking = VRM stage | none [CUST] |
| 5.5 | [BENCH] prolonged soak with IR + power logging | time/temperature dependence | fails only hot = thermal; random = marginal silicon | IR + meter [BENCH] |
| 5.6 | [AUTH] dedicated memory stress (customer-run memcheck/OCCT VRAM) | forced error reproduction | reproduces = confirmed failing memory | none, customer runs it |

Important: true MATS/MODS-class full-memory testing is a vendor field tool; a
read-only service approximates it with counters-delta methodology (5.1-5.4) and
never injects faults. Full replacement diagnosis ends at RMA recommendation.

## Escalation summary

| Stage | Reached when | Owner | Cost tier |
|---|---|---|---|
| 0-1 | any card | field tech (remote possible) | lowest |
| 2 | enumerates, driver fails | field tech with logs | low |
| 5 | loads but errors | field tech + customer cooperation | medium |
| 3-4 | dead at bus / thermal | bench technician | high (physical) |
