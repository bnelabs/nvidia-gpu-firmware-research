> HISTORICAL / SUPERSEDED. Not an authorized runbook. Claims may be retracted. Read current CONSTITUTION.md and CORRECTIONS.md at the repository root.

# Legal & Safety Notes — Firmware Research on Your Own NVIDIA GPU

*Practical, cited guidance for the owner of this repo studying their own hardware (lab rig: RTX 3090, GA102). Not legal advice. Compiled 2026-10-15; links checked that date. This file complements prior-art.md; the repo's standing rules (no firmware binaries in git; read-only production rig; destructive work on a separate bench) are restated and justified below.*

## TL;DR

- **US:** DMCA §1201 bans circumvention of access controls, but there is a *statutory* security-testing exemption (§1201(j)) and a *rulemade* good-faith security-research exemption, 37 CFR 201.40(b)(16), renewed in the 2021 (eighth) and 2024 (ninth) triennial rulemakings; the 2024 final rule took effect 2024-10-28.
- **Key nuance for us:** GeForce vBIOS and GSP firmware are *distributed openly* (flash tooling ships from vendors; gsp.bin is even in linux-firmware), so owner research rarely involves circumventing an "effective technological measure" at all — the exemptions are a backstop, not a license to attack.
- **EU:** no Europe-wide security-research circumvention carve-out. Software Directive 2009/24/EC gives non-waivable rights to *observe/study/test* a lawfully-acquired program and to *decompile for interoperability*; InfoSoc Directive 2001/29/EC Art. 6 bans TPM circumvention with member-state exceptions.
- **Licenses:** open-gpu-kernel-modules code is MIT, dual MIT/GPLv2 when linked as a kernel module; the .run user-space components and firmware remain under NVIDIA's proprietary "License for Customer Use"; vBIOS binaries carry **no redistribution license at all**.
- That is why this repo stores **URL + version + sha256**, never firmware binaries: copyright infringement exposure, DMCA-takedown risk for the git host, and zero functional need.
- **Safety headline:** vBIOS flashing is the most bricking-prone operation in this whole research program. Never flash: laptops, single-BIOS unique cards, or the production rig. Recovery exists (dual-BIOS switch, blind flash, CH341A/SOIC-8 SPI programmer with a 1.8 V-adapter caveat) but must be planned *before* the first flash.
- Warranty: reflashing stock ROMs is usually recoverable and often tolerated; hardware strap modifications and thermal/power accidents are not. Check the AIB's warranty terms [VERIFY per vendor].
- Do mutating experiments only on a VFIO/QEMU-isolated test bench; the production rig stays read-only.
- Anything that looks like a security bug goes to **NVIDIA PSIRT** (web form, psirt@nvidia.com, PGP key on site); from 2026-10-01 bulletins are published on GitHub in Markdown/CSAF/CVE.

## 1. Legal landscape

### 1.1 United States — DMCA §1201

§1201(a)(1) prohibits circumventing "a technological measure that effectively controls access to a protected work". Two carve-outs matter here:

**Statutory security testing.** 17 USC §1201(j) exempts acts of "security testing" — accessing a computer/network solely to test, investigate or correct a security flaw, carried out with authorization of the owner/operator ([Title 17, Chapter 12](https://www.copyright.gov/title17/92chap12.html)). For your *own* card, you are the owner; this covers probing the driver/GSP interface in place.

**Triennial rulemaking (the rulemade exemption).** The Librarian of Congress adopts three-year circumvention exemptions. Verified status:

- **2021 (eighth triennial):** the final rule re-adopted the security-research exemption as [37 CFR 201.40(b)(16)](https://en.wikisource.org/wiki/2021_Final_1201_Rule): circumvention "on a lawfully acquired device or machine on which the computer program operates... solely for the purpose of good-faith security research", defined as accessing a program "solely for purposes of good-faith testing, investigation, and/or correction of a security flaw or vulnerability, where such activity is carried out in an environment designed to avoid any harm to individuals or the public" and the findings are used to promote the security/safety of that class of devices. The rule text explicitly warns the exemption "is not a defense" to other laws (CFAA, etc.). Background: [Copyright Office 2021 proceeding](https://www.copyright.gov/1201/2021/).
- **2024 (ninth triennial):** the Librarian adopted the [final rule effective 2024-10-28](https://www.federalregister.gov/documents/2024/10/28/2024-24563/exemption-to-prohibition-on-circumvention-of-copyright-protection-systems-for-access-control) ([proceeding page](https://www.copyright.gov/1201/2024/)). Per the [National Law Review summary](https://natlawreview.com/article/final-rule-dmca-grants-circumvention-exemptions): all but one existing exemption were renewed; new exemptions were added for vehicle operational data and food-preparation equipment repair; the proposed "AI trustworthiness research" exemption was **declined**. The security-research class carried forward with its limitations intact.
- **Next cycle:** the Office's [1201 landing page](https://www.copyright.gov/1201/) notes the tenth triennial will use a streamlined renewal process, with renewed exemptions running October 2027–October 2030. **[VERIFY: exact text of the security-research class as amended in the 2024 final rule before relying on it; the FR PDF is the authoritative source.]**

**Why this mostly doesn't bite for GPU firmware research.** §1201 targets *access controls on copyrighted works*. Your RTX 3090's vBIOS is designed to be readable and flashable by the owner (vendor flash tools, GPU-Z dumps); gsp.bin ships in the driver package and even in linux-firmware; the GSP RPC protocol is defined in open source headers. There is no "effective technological measure controlling access" in the DMCA sense for owner-initiated analysis — the legal analysis is ordinary copyright + contract + (for anything network-touching) CFAA/anti-abuse law. The exemptions matter when a research step *does* hit a TPM (e.g., signed falcon microcode verification, secure-debug gating, future attestation schemes).

### 1.2 European Union (owner is in Europe/Istanbul — Turkish implementation noted)

- **Software Directive 2009/24/EC** (codified; [EUR-Lex text](https://eur-lex.europa.eu/LexUriServ/LexUriServ.do?uri=OJ:L:2009:111:0016:0022:EN:PDF)): Art. 5(1) permits observing/studying/testing program functioning while performing permitted acts (loading/displaying/running/transmitting) — expressly *not* waivable by contract (Art. 5(3), and Art. 8 makes contrary clauses "null and void"); Art. 6 permits **decompilation** where indispensable for interoperability of an independently created program, also non-waivable ([Art. 6 text](https://www.legislation.gov.uk/eudr/2009/24/article/6)). This is the strongest EU hook for decompiling gsp.bin or a vBIOS module you lawfully possess.
- **InfoSoc Directive 2001/29/EC** Art. 6 obliges member states to protect TPMs against circumvention, with a member-state-managed exception regime in Art. 6(4) ([text](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:32001L0029); [Art. 6](https://www.ippt.eu/legal-texts/copyright-information-society-directive/article-6)). There is **no EU-level security-research circumvention exemption** equivalent to 37 CFR 201.40(b)(16); member-state implementations diverge. **[VERIFY: your member state / Turkey's implementation — Turkey implements via Law No. 5846 (Law on Intellectual and Artistic Works) and its technical-measures provisions; confirm current text and any 2023+ amendments before any circumvention-adjacent activity.]**
- Practical EU posture for this repo: static analysis, dumping, and interoperability work on owned hardware sits on solid ground (Software Directive); anything that defeats a protection measure should be checked against national law first.

### 1.3 Copyright, GPL, nouveau, and NVIDIA's split licensing

- **nouveau's clean-room tradition.** nouveau is GPL'd and was built by RE *without distributing* NVIDIA binaries; for years users had to supply firmware extracted from NVIDIA's own packages themselves (the same pattern survives in the [extract-firmware-nouveau.py tool in open-gpu-kernel-modules](https://github.com/NVIDIA/open-gpu-kernel-modules), which decodes firmware embedded in the published source). A GPL project cannot generally ship NVIDIA proprietary binaries alongside GPL code — which is precisely why community repos historically pointed at URLs instead of hosting blobs.
- **Open kernel modules.** Per the repo's [COPYING](https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/main/COPYING): individual files are **MIT**; "when linked together to form a Linux kernel module, the resulting Linux kernel module is dual licensed as **MIT/GPLv2**". So the *kernel module source* is genuinely open. Everything else in a driver install is not: user-space libraries, the control panel, and the closed-path components fall under NVIDIA's proprietary ["License For Customer Use of NVIDIA Software"](https://www.nvidia.com/en-us/drivers/nvidia-license/linux/), which grants use, not redistribution rights.
- **GSP firmware binaries.** NVIDIA explicitly fixed this gap in May 2023 (R535 beta): the license was revised "to make it more explicit around permitting the GSP firmware binaries... redistribution" ([Phoronix](https://www.phoronix.com/news/NVIDIA-GSP-Firmware-License)), and in Nov 2023 62 MB of GSP blobs entered linux-firmware.git ([Phoronix](https://www.phoronix.com/news/NVIDIA-Big-GSP-Firmware-Dump)). gsp.bin is thus the *one* NVIDIA firmware you may legally redistribute today. **[VERIFY: the exact license text in linux-firmware WHENCE for `nvidia/gsp` before mirroring it anywhere.]**
- **vBIOS binaries.** No open redistribution license exists. A vBIOS ROM is a copyrighted compilation (vendor init code + NVIDIA IP). Dumping your own card's ROM for private analysis is unproblematic; *publishing the binary* is not licensed. **This is the concrete reason the repo stores URL + version + sha256 only** (see .gitignore): (1) no license to redistribute the binaries; (2) git hosts process DMCA 512 takedowns quickly; (3) hashes + provenance URL are fully sufficient for reproducibility and diffing.

### 1.4 Operating rules for this repo (derived from the above)

1. Never commit `.rom`, `.bin`, or extracted driver files; record source URL, driver/package version, and sha256 in 06-ground-truth/ instead.
2. Analysis products (tables, parsers, notes, disassembly snippets) are fine — RE for interoperability/research; keep verbatim firmware payloads out.
3. Quoting small excerpts of firmware for documentation (hex snippets of a table header) falls under normal research practice; avoid anything that functions as a substitute for the original.
4. Anything network-adjacent or aimed at other people's systems is out of scope — owner hardware only.

## 2. Safety

### 2.1 Bricking risks and recovery paths

A failed vBIOS flash leaves the card POST-less ("bricked") because the GPU executes its ROM before the OS loads. Verified recovery paths, cheapest first:

1. **Dual-BIOS switch.** Many RTX 30-class cards (e.g. ASUS TUF 3070 Ti) carry two ROMs and a physical switch; a botched flash on one image is fixed by flipping to the healthy one and [reflashing the bad side](https://www.techpowerup.com/forums/threads/reflashing-one-bios-on-dual-bios-rtx-card.306891/). *Know your card's switch before ever flashing.*
2. **Blind flash / iGPU host.** The card still enumerates on PCIe without video; with an iGPU driving the display, `nvflash` can reflash "blind" ([recovery guide](https://blog.silverpc.hu/2025/10/18/a-failed-vbios-flash-resulted-in-no-video-from-any-gpu-heres-the-recovery-guide/)).
3. **Hardware programmer.** A CH341A USB SPI programmer with a SOIC-8 clip rewrites the ROM chip off-bus; see the [Tom's Hardware CH341A + SOIC-8 recovery walkthrough](https://forums.tomshardware.com/threads/recovering-a-motherboard-graphics-card-from-a-bad-bios-flash-with-ch341-flasher-1-8v-adapter-and-a-soic-8-clip.3593910/). **Critical caveat from that guide: some modern cards use 1.8 V flash, and a 3.3 V programmer will damage it — use a 1.8 V adapter and verify the chip's Vcc first.** Hot-flashing (swapping chips between boards while running) is the last resort ([step-by-step guide](https://blog.silverpc.hu/2025/10/18/bricked-your-card-a-step-by-step-recovery-guide-for-when-flashing-the-gpu-bios-failed/)).

Standing rules: never write a ROM you haven't verified against a known-good reference (TechPowerUp vBIOS database) *and* a fresh dump of the chip itself; keep the pristine dump in ≥2 places with hashes; use the correct flash tool variant (NVFlash with the right protection flags for NVIDIA, per the [NVFlash overview](https://laptopjudge.com/nvidia-nvflash/)); and remember the production rig is off-limits for any of this (repo README operating rule).

### 2.2 Warranty implications

- Flashing modifies the SPI flash content; most AIB RMAs care about *recoverable state*, so a card flashed back to the stock ROM with matching hashes is usually indistinguishable — but vendor policies differ, and some treat any non-stock image or flash-tool use as voiding. **[VERIFY: the exact warranty terms of the card's AIB (board partner), not NVIDIA's, govern the physical card.]**
- Far more warranty-relevant than flashing: physical work (resistor "crossflash" straps, removed heatsinks, broken clips, ESD damage) leaves visible evidence. Prefer software-path experiments; treat strap mods as irreversible-warranty territory.
- Some vendors ship *official* vBIOS update utilities for specific cards — for those, the supported tool is also the safest one.

### 2.3 Never flash: laptops and single-BIOS unique cards

- **Laptop GPUs:** the "vBIOS" is typically fused into the system BIOS/UEFI image with vendor ACPI tables and power policy; there is no socket, no switch, and flashing the wrong image can kill the whole platform. The rig rule (no flashing) applies doubly. **[VERIFY: none of the planned experiments involve the laptop; if one ever does, it requires a dedicated written runbook first.]**
- **Single-BIOS cards** (many RTX 3090s included — *the rig card is exactly this class*): one image, no switch; a failed flash means programmer-or-bust. Combined with production-inference duty, this is why the rig is read-only and flashing happens only on a sacrificial card on the test bench.
- **Founders Edition / rare SKUs:** identical-image risk is highest where the exact ROM is scarce; always confirm a byte-identical known-good reference exists *before* writing.

### 2.4 ESD and power safety for SPI clip work

- Work powered-off: system unplugged, PSU switch off, hold the power button to drain rails before clipping the SOIC-8.
- Wear an ESD wrist strap bonded to chassis ground; the flash chip and the card's power plane are both vulnerable.
- Verify chip Vcc (3.3 V vs 1.8 V) before connecting any programmer — the classic destruction mode is a 3.3 V CH341A on a 1.8 V chip ([same Tom's Hardware guide](https://forums.tomshardware.com/threads/recovering-a-motherboard-graphics-card-from-a-bad-bios-flash-with-ch341-flasher-1-8v-adapter-and-a-soic-8-clip.3593910/)).
- Clip alignment matters: pin 1 dot toward the chip's pin-1 mark; re-seat rather than force; read the chip *twice* and require identical hashes before trusting a dump, and again after any write.
- Never clip/probe a card installed in the production rig, and never probe while the GPU is under load — transient currents through a mis-seated clip can damage the chip or the board.

### 2.5 Test-bench isolation (VFIO/QEMU)

All mutating experiments (driver unbinds, resets, RPC fuzzing, firmware swaps) run on a separate bench machine or a VM:

- Pass the sacrificial GPU through with **VFIO** to a QEMU guest; a crashed/hung firmware leaves the host clean, and snapshots give instant rollback.
- The production rig (this host) remains strictly read-only per the [README lab rule](../../README.md): NVML queries, `/proc`, `/sys` reads, `lspci` dumps only — no resets, no clock/power mutations, no driver unbinds.
- Network-isolate the bench VM; a firmware experiment that wedges the PCIe link should never take the host's storage or network with it.

### 2.6 Responsible disclosure via NVIDIA PSIRT

If research on your own card surfaces what looks like a security vulnerability (e.g., a GSP RPC handler that can be driven into memory corruption, a falcon auth bypass):

- Report via NVIDIA's [vulnerability report page / web form](https://www.nvidia.com/en-us/product-security/report-vulnerability/) or email **psirt@nvidia.com**, encrypted with NVIDIA's public PGP key ([PGP key page](https://www.nvidia.com/en-us/security/pgp-key/)). Include product/driver version, vulnerability type, reproduction steps, PoC, and impact — per the [open-gpu-kernel-modules SECURITY.md](https://github.com/NVIDIA/open-gpu-kernel-modules) (same intake for open-module issues).
- Policy and lifecycle: [NVIDIA PSIRT policies](https://www.nvidia.com/en-us/product-security/psirt-policies/); past bulletins at [nvidia.com/security](https://www.nvidia.com/en-us/security/). As of **2026-10-01**, NVIDIA publishes bulletins on the [NVIDIA/product-security GitHub repo](https://github.com/NVIDIA/product-security) in Markdown, CSAF, and CVE formats.
- House rules for disclosure: no publishing exploit details before coordinated timelines; keep PoCs on the test bench; the repo's write-ups describe issues at the level needed for the vendor to act. **[VERIFY: NVIDIA's current disclosure timeline/target window in the PSIRT policy page before quoting any specific number of days.]**

## Open questions

- [VERIFY] Exact amended text of the security-research exemption in the 2024 final rule (read the [FR PDF](https://www.federalregister.gov/documents/2024/10/28/2024-24563/exemption-to-prohibition-on-circumvention-of-copyright-protection-systems-for-access-control) rather than summaries).
- [VERIFY] Turkey-specific implementation: Law No. 5846 technical-measures provisions and any recent amendments; whether a security-research-style exception exists in Turkish law.
- [VERIFY] Current linux-firmware WHENCE license text for `nvidia/gsp` blobs (needed before any mirror/redistribution decision).
- [VERIFY] AIB warranty clauses on vBIOS reflashing for the rig's exact board vendor and model.
- [VERIFY] NVIDIA PSIRT's current coordinated-disclosure timeline (days) as published on the PSIRT policies page.
- [VERIFY] Whether any 12VHPWR/OCSP-related firmware on RTX 40/50 cards is user-flashable at all (affects future safety guidance).
- [VERIFY] Whether the rig's GA102 firmware images (vBIOS, gsp.bin for 615.71.09) appear in public hash databases — if yes, add the matching URLs to 06-ground-truth instead of local binaries.
