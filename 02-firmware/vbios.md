# NVIDIA vBIOS: Anatomy, Extraction, Flashing, and Power-Table Modding

> Research notes for studying **my own** hardware (lab rig: RTX 3090, GA102, open kernel module 615.71.09, CUDA 13.4, production inference). Compiled 2026-10-15 from web sources only — no commands were run against the rig. A bad flash **voids your warranty and can destroy a card**; read the cautions before touching anything.

## TL;DR

- A vBIOS is a PCI option ROM (55AA + PCIR) wrapped around NVIDIA's BIT-directory firmware: init scripts, display, clock, memory, and power tables, plus a UEFI/GOP image — NVIDIA's own [BIOS Information Table spec](https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html) documents the token layout.
- nvflash enforces Device-ID / Subsystem-ID / Board-ID / Hierarchy checks; the current go-to fork for bypassing them is [nvflashk](https://github.com/notfromstatefarm/nvflashk), which force-enables NVIDIA's own internal bypass — it flashes "almost any signed BIOS to almost any card."
- **Always dump before flashing** (`nvflash -b factory.rom`); the installed ROM is the only ground-truth identity of your card.
- Power-table edits are safest done by **diffing partner BIOSes of the same chip** via a BIT parser, not by blind hex search; community 30-series edits used partner/XOC ROMs (e.g., Kingpin 1000 W onto a Strix 3090 with a dual-BIOS switch).
- On Blackwell the flash-free path is winning: mVolt+ v0.36 reportedly bypasses stock power limits (5090 → 700 W reports) without shunt mods or reflashing.
- Dual-BIOS switches, an iGPU, and a CH341A + SOIC-8 clip with flashrom are the three recovery layers; "bricked" NVIDIA cards are almost always reflashable because the GPU itself can reject bad images and fall back.
- The 2025 RTX 50 "black screen saga" was fixed by drivers (572.75 hotfix) **plus vBIOS updates distributed by AIBs** (MSI Center etc.), confirmed by NVIDIA staff.
- Laptop vBIOSes are OEM-fused territory (MXM data, GC6 power scripts); flashing desktop ROMs into laptops is the classic brick scenario.
- On a production rig, **do not** use the sysfs `rom` trick — it touches the PCI device while the driver is bound; use nvflash in a maintenance session or existing dumps instead.
- Open items: exact GDDR7 training persistence, InfoROM/training interplay, and Blackwell secure-image behavior are still [VERIFY]-grade.

## 1. vBIOS anatomy: option ROM wrapper + BIT directory

### Option ROM wrapper

A `.rom` file is (usually) a PCI Expansion ROM: on 512-byte boundaries you find the `55 AA` signature, and the pointer at offset 0x18 leads to a `PCIR` PCI data structure. NVIDIA's spec adds a wrinkle: a GPU firmware file may carry hardware-consumed data *before* the ROM, and a UEFI image (Code Type 03h) may follow the PC-compatible (Code Type 00h) image, in which case BIT pointers past the legacy image's end must be adjusted (`adjusted_pointer = pointer + UEFI image length`) ([NVIDIA BIT spec](https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html)). This is why you sometimes see more than one `PCIR` string in a dump but only one `55 AA` leader ([Win-Raid thread on splitting UEFI from vBIOS](https://winraid.level1techs.com/t/guide-remove-uefi-image-from-nvidia-vbios/34363?page=4)).

### The BIT directory

The modern NVIDIA vBIOS is indexed by the **BIOS Information Table (BIT)**: a 12-byte header (ID `0xB8FF`, signature `"BIT\0"`, BCD version 1.00, header size 12, token size 6, token count, zero-checksum) followed by 6-byte tokens, each = (ASCII-letter ID, data version, 16-bit size, 16-bit pointer). The header checksum rule: the byte-sum over the header must be 00h. Tokens include ([BIT spec](https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html)):

- `'B'` BIOSDATA — version, OEM version, **Board ID**, the "BIOS 0 checksum" inserted at build time.
- `'I'` NVINIT — init-script tables: devinit script pointers, condition/I-O-condition tables, macro tables, PCIe settings script, boot scripts, and **separate non-GC6 boot scripts** (GC6 = runtime low-power state, laptop territory).
- `'P'` PERF — the money token: performance table, **Power Control Table**, thermal/coolers/policy tables, voltage-frequency, power topology/leakage/sensors, **Overclocking Table**, fan tables, and ~25 LowPower sub-tables (PCIe, GC6, PSI, NVLink).
- `'M'` MEMORY — memory strap count, **strap translation table**, memory info table, partition info, and a script list of devinit scripts that program the FB (framebuffer) register set.
- `'C'` clocks, `'U'` display, `'D'`/`'d'` DFP/DP, `'L'` LVDS, `'S'` strings (sign-on, version `ww.xx.yy.zz`, OEM strings), `'p'` Falcon/PMU ucode (PMU init-from-ROM images), `'u'` UEFI driver data, `'x'` MXM configuration, `'R'` bridge firmware.

Pre-BIT legacy ROMs (older than roughly Fermi-era cleanups) used fixed-offset tables; the envytools parser documents the historical validation path — check `0xAA55` and the 8-bit checksum over the init portion, whose byte-sum must be zero ([envytools nvbios parser docs](https://deepwiki.com/freedreno-zz/envytools/4.1-vbios-core-parser-and-print-engine)). BIT is "the modern standard for NVIDIA VBIOS table discovery" and the same token framework is still in force today.

### UEFI/GOP driver

The `'u'` UEFI token carries the minimum UEFI driver version, a **UEFI compatibility level** (used to prevent merging an incompatible legacy image), and flags for display switch / LCD diagnostics / glitchless boot ([BIT spec](https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html)). nvflash's identification output shows the real-world result: `UEFI Version: 0x70007 (x64)`, `UEFI Signer(s): Microsoft Corporation UEFI CA 2011` ([nvflashk README example output](https://github.com/notfromstatefarm/nvflashk)). Cards without a GOP image can't drive a UEFI-native console — a common reason people splice GOP into old ROMs on the Win-Raid forums.

### Evolution Pascal → Blackwell

The format is remarkably stable: Pascal-era ROMs already use BIT with v1/v2 data structures; the spec (last updated 2018) still describes current cards. What changed across generations:

- **Table volume grew**: PERF v2's pointer list (power topology, leakage, sensors, overclocking, dozens of LowPower tables) far exceeds what a Pascal card needed, matching the runtime power-management ambitions of Turing+.
- **Memory scripts and straps**: `'M'` v2 moved from raw reset/VREF/DQS scripts (v1, deprecated) to strap translation + memory info + partition tables + a script list, tracking the jump to GDDR6/GDDR6X/GDDR7 (Pascal GDDR5X → Blackwell GDDR7).
- **Falcon/PMU**: `'p'` token carries PMU init-from-ROM code/data (IMEM/DMEM images), the on-GPU microcontroller firmware that the vBIOS loads at boot; v2 renamed PMU pointers to generic Falcon data ([BIT spec](https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html)).
- **Boot split**: the vBIOS still owns cold-boot devinit and display init on GeForce, while the open kernel module loads GSP firmware for runtime management (our rig's `gsp-firmware-images.txt` dump shows the separate GSP blobs). The exact vBIOS/GSP split per generation is [VERIFY].
- **Code Type 03h UEFI images** became standard from Pascal on, and image-hash/signed-blob fields in nvflash output show increasing signature requirements into Ampere/Ada/Blackwell ([nvflashk output](https://github.com/notfromstatefarm/nvflashk)).

### Laptop / MXM differences

Laptop ROMs carry the `'x'` MXM token (form factors Type-I…IV, DCB modification status, MXM digital connector and DDC/Aux→CCB maps) and GC6-aware boot scripts; subsystem IDs are OEM-specific and interact with Optimus muxes ([BIT spec](https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html)). Practical consequence: a Legion owner who flashed an MSI desktop-style 3070 140 W ROM bricked the machine and had to hunt for the vBIOS SPI chip with a USB flasher ([r/LenovoLegion case](https://www.reddit.com/r/LenovoLegion/comments/z1t5pu/bricked_my_laptop_after_flashing_msi_vbios/)). Never treat laptop and desktop ROM pools as interchangeable.

## 2. Extraction

**On the production rig: assume NO.** The sysfs method requires writing to the PCI device's sysfs attributes while the NVIDIA driver is bound; unbinding the driver to make `rom` readable would kill running inference. Documented for completeness and for future maintenance windows:

```bash
# Maintenance window only, NOT on a production GPU:
GPU=0000:65:00.0                                # your card's PCI address
echo 1 | sudo tee /sys/bus/pci/devices/$GPU/rom >/dev/null
sudo cat /sys/bus/pci/devices/$GPU/rom > ga102.rom
echo 0 | sudo tee /sys/bus/pci/devices/$GPU/rom >/dev/null
```

Caveats widely reported: the file is single-open, may return stale/zero content if read twice without toggling, and older setups misbehave when a driver is bound. The legacy alternative — copying the shadowed BIOS from `C0000` via `dd if=/dev/mem` — can produce **damaged dumps** because the system BIOS may have modified it while copying into shadow RAM ([nouveau wiki, DumpingVideoBios](https://people.freedesktop.org/~mslusarz/nouveau-wiki-dump/DumpingVideoBios.html)).

**GPU-Z (Windows)**: the "Save BIOS" button is the standard route and is the same mechanism the [TechPowerUp VGA BIOS Collection](https://www.techpowerup.com/vgabios/) uses for submissions — the database explicitly asks users to "Submit it using GPU-Z to extract and upload your BIOS," making it the de-facto cross-platform corpus for Pascal→Blackwell partner ROMs.

**nvflash** (Linux build exists): `-b` reads the EEPROM to a file and `--version` fingerprints card or file:

```
nvflash --version                     # what's on the card right now
nvflash -b factory.rom                # dump it
nvflash --version factory.rom         # verify the dump's self-description
```

If the card has a dual-BIOS switch, **dump both chips** while flipping the switch between runs — no reboot needed, since the chip is only read at POST ([nvflashk README](https://github.com/notfromstatefarm/nvflashk)).

**Virtualized hosts**: the [SpaceinvaderOne/Dump_GPU_vBIOS](https://github.com/SpaceinvaderOne/Dump_GPU_vBIOS) script dumps any GPU, including a primary, on Unraid-style VFIO setups — a good pattern for lab machines where the GPU is passed through.

## 3. Flashing

### What stock nvflash checks

During a `-6` flash, official nvflash compares the image against the adapter: GPU PCI Device ID, PCI Subsystem ID, internal **Board ID** (PCB+GPU combo), "Hierarchy" (generation family), plus minor metadata ([nvflashk README](https://github.com/notfromstatefarm/nvflashk)). `-6` relaxes some checks; Board-ID-level mismatches are refused outright. The official tool is still maintained — 5.867 landed February 2025 and supports "Blackwell, Ada, Ampere, Turing, Pascal and all older NVIDIA cards" ([TechPowerUp nvflash download](https://www.techpowerup.com/download/nvidia-nvflash/)).

### nvflashk — the current community fork (VERIFY-fresh as of 2026)

The best-known active fork is [nvflashk](https://github.com/notfromstatefarm/nvflashk) by `notfromstatefarm` (kefinator), a patched nvflash that **force-enables NVIDIA's own internal mismatch bypass** while keeping explicit `YES` confirmations per bypass:

```
WARNING: Firmware image PCI Subsystem ID (1043.88E2) does not match adapter (1043.889C).
WARNING: None of the firmware image compatible Board ID's match the Board ID of the adapter.
PCI Subsystem ID mismatch bypassed!  ...  Type "YES" to continue sending it:
```

Documented test cases include 4090 TUF ← Strix XOC 1.1 V BIOS ("the 1.07 V limitation appears to have been a BIOS change, not a physical change"), FE←AIB cross-flashes on 30/40 series, and rejection of cross-generation or workstation cross-flashes (the GPU itself refuses: `ERROR: Invalid firmware image detected. Nothing changed!`). An older fork with the same goal is [B47741/nvflash](https://github.com/B47741/nvflash). Typical session:

```
nvflashk --protectoff        # clear EEPROM write-protect (first flash on a card)
nvflashk -b factory.rom      # DUMP FIRST. Then copy the dump off the machine.
nvflashk -6 partner.rom      # flash; confirm each bypass with YES; reboot
```

`--protectoff` is required on many cards before the first write ([nvflashk README](https://github.com/notfromstatefarm/nvflashk)).

### Multi-BIOS switches on 30-series

Many 30-series cards (EVGA FTW3, ASUS TUF/Strix, etc.) carry two SPI chips with a toggle. The switch is the community's favorite safety: "A 3090 Strix can be flashed with the 1000 W KINGPIN BIOS … Strix even has a BIOS switch so you can literally flip a switch to run stock again" ([r/overclocking](https://www.reddit.com/r/overclocking/comments/s6e8f3/shunt_modding_asus_strix_3090/)). Workflows use the switch both for recovery and to keep a known-good ROM resident on the second chip. OEMs also ship their own flashers — ASUS's VBIOS Flash Tool (WinFlash + "E-Mode" efficiency-mode flasher) warns never to shut down mid-update ([ASUS FAQ](https://www.asus.com/support/faq/1042847/)).

### Warranty and danger framing

Flashing with a fork voids warranty immediately — nvflashk's own text: "Your warranty will be null and void the second you so much as think about using this tool," with the added warning that some XOC ROMs "have absolutely no thermal protections and will let the card melt itself to death" ([nvflashk README](https://github.com/notfromstatefarm/nvflashk)). And laptops: see the Legion brick above; laptop vBIOSes are fused/muxed to OEM boards and are the single most common "I cannot recover this" scenario.

## 4. Power/clock table editing

### The community technique on 30-series

The 2020–2021 Ampere wave worked like this: pick a partner/XOC ROM with a higher power target for the **same chip and board class**, flash with checks bypassed, done. The [EVGA 3090 FTW power-limit bypass thread](https://www.overclock.net/threads/evga-3090-ftw-power-limit-bypass.1774611/) on Overclock.net is the canonical example (Gigabyte 3090 or EVGA XC3 ROMs used to escape FTW throttling). True *hex edits* followed: locating the power-table bytes inside the PERF structures and raising default/max limits, guided by partner diffs.

### Diffing instead of blind hex edits

Because BIT gives every table a tokenized pointer, the reliable workflow is structural, not search-and-hope:

1. Download 3–5 partner BIOSes for your exact chip from the [TPU vBIOS database](https://www.techpowerup.com/vgabios/) (e.g., several RTX 3090 ROMs with different power limits).
2. Parse each with a BIT-aware tool ([nvidia_rom_parser](https://github.com/hdlcodelab/nvidia_rom_parser) is a C++ parser built directly on the NVIDIA BIT spec; envytools' `nvbios` is the historical reference; [VBios-Editor](https://github.com/evw88/VBios-Editor) and [Nvidia-vBIOS-Clock-Power-Tweaker](https://github.com/JadeRover/Nvidia-vBIOS-Clock-Power-Tweaker) are newer editing-oriented tools).
3. Dump the Power Control Table / clock tables per ROM and **diff**: bytes that differ consistently across cards with known different power limits (350 W vs 420 W, say) are your limit fields. Values that stay identical are board-ID/version noise.
4. Patch only fields confirmed by the diff, then re-verify checksums (below).

### Shunt-mod + vBIOS combos

The power stage measures current through board shunt resistors; XOC practice is to lower shunt resistance (raising the wattage the firmware believes flows) and/or flash an XOC ROM. The [RTX 3090 FE shunt-mod thread](https://www.overclock.net/threads/rtx-3090-founders-edition-working-shunt-mod.1773780/) documents the hardware side. Combining both multiplies risk: the ROM's power tables assume the board's stock shunt values, so a mismatched combo can misreport and mis-limit power. Treat combined mods as unvalidated territory and expect fire-grade consequences at 2× power ([VERIFY] on exact shunt↔table calibration interactions).

### Checksums

Three layers to keep consistent after an edit: the PCI ROM 8-bit checksum (byte-sum of the init region must be 0 — what envytools' parser validates), the BIT header zero-checksum, and the "BIOS 0 checksum" recorded in BIOSDATA ([BIT spec](https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html), [envytools parser docs](https://deepwiki.com/freedreno-zz/envytools/4.1-vbios-core-parser-and-print-engine)). Editor tools recompute these; if nvflash rejects your edited image ("Invalid firmware image detected"), suspect a checksum first. Note nvflashk's releases have only been proven with **signed** images — unsigned/modified ROMs are listed as "not yet tested" ([README](https://github.com/notfromstatefarm/nvflashk)), so hex-edited ROMs may additionally face signature rejection on newer generations.

## 5. Memory: GDDR6/GDDR6X/GDDR7 init

The `'M'` MEMORY token is the vBIOS's memory playbook: strap data count + **memory strap translation table** (selecting timing/voltage programming per strapped configuration), the memory information table, partition information, and the script list of devinit scripts that program the FB registers ([BIT spec, BIT_MEMORY_PTRS v2](https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html)). In practice the vBIOS applies memory-reset, VREF/DQS-on, and DLCELL scripts before the OS driver ever loads; memory OC "straps" of the old days map onto these tables.

Two adjacent systems matter:

- **InfoROM**: a separate non-volatile store on the card — "Fermi™ and higher parts have non-volatile on-board memory for persisting device info, such as aggregate ECC counts…" ([cuda.core InforomInfo docs](https://nvidia.github.io/cuda-python/cuda-core/latest/generated/cuda.core.system.InforomInfo.html)). nvflash reports `InfoROM Version` and `InfoROM Backup: Present` — the card maintains a backup copy of this calibration/config store ([nvflashk output](https://github.com/notfromstatefarm/nvflashk)).
- **Firmware-driven memory training**: GDDR6X (Ampere) and especially GDDR7 (Blackwell, PAM3 signaling with link/ECC features) do nontrivial per-part training at boot. Community sources report Blackwell cards with lengthy first-boot training and memory-stability-driven black screens ([GDDR7 OC guide](https://digitalgamerhub.com/how-to-overclock-gddr7-memory-guide/), [gpusolutions repair guide](https://gpusolutions.net/rtx-5080-5090-black-screen-fans-100-repair-guide/)) — but the **persistence model** (whether/where training results are stored: InfoROM vs SPI flash vs retrained-every-boot) is not publicly documented and stays [VERIFY]. This also means a memory-adjacent vBIOS edit can interact with training in ways the hex editor can't see.

## 6. Bricking & recovery

nvflashk's author (with the largest recent dataset of intentional cross-flashes) argues you "cannot permanently damage an NVIDIA GPU from a BIOS flash in and of itself" — the card either falls back, rejects the image, or is reflashable; what *does* kill cards is running load on hardware the ROM doesn't protect ([README](https://github.com/notfromstatefarm/nvflashk)). Observed failure modes and recovery ladder, easiest first:

1. **Fallback / rejection**: bad image often → `ERROR: Invalid firmware image detected. Nothing changed!` or a fallback with generic display output; a mid-flash power cut yields `WARNING: Broken image found` and a simple reflash ([README](https://github.com/notfromstatefarm/nvflashk)).
2. **iGPU boot**: motherboard video output leaves the dGPU free to reflash normally.
3. **Dual-BIOS switch**: flip, boot, disable the GPU device, flip back, flash, reboot.
4. **Second GPU + riser/slot**: flash the dead card from a working one (nvflash supports selecting the adapter).
5. **No-POST corner case**: enabling CSM in UEFI setup usually gets the machine to POST with a mismatched chip ([README](https://github.com/notfromstatefarm/nvflashk)).
6. **SPI reflashing (card appears fully dead)**: the vBIOS lives on a discrete SPI flash chip (typically an 8-pin SOIC W25Q-class part) on the card. A CH341A programmer with a SOIC-8 clip plus flashrom is the standard toolchain: identify, read twice and compare, then write ([MrChromebox unbricking guide](https://docs.mrchromebox.tech/docs/support/unbricking/unbrick-ch341a); [silverpc 2025 walkthrough](https://blog.silverpc.hu/2025/10/18/bricked-your-card-a-step-by-step-recovery-guide-for-when-flashing-the-gpu-bios-failed/)):

```bash
sudo flashrom -p ch341a_spi            # should identify the SPI part
sudo flashrom -p ch341a_spi -r r1.rom  # read...
sudo flashrom -p ch341a_spi -r r2.rom  # ...twice, and only trust a stable read
sudo flashrom -p ch341a_spi -w known_good.rom -N
```

**Discipline**: dump-before-flash is non-negotiable — the installed ROM is the authoritative identity of your card, and "you may never find a replacement that you are certain matches perfectly" ([nvflashk README](https://github.com/notfromstatefarm/nvflashk)). Keep `--protectoff` only when writing; keep factory dumps in at least two places, including both chips on dual-BIOS cards.

## 7. Blackwell (RTX 50) specifics

- **Power targets**: RTX 5090 stock TDP is 575 W ([TPU GPU database](https://www.techpowerup.com/gpu-specs/geforce-rtx-5090.c4216)); the Gigabyte Gaming OC 5090 ships at a 600 W default ([TPU review](https://www.techpowerup.com/review/gigabyte-geforce-rtx-5090-gaming-oc/41.html)). RTX 5080 FE sits at 360 W, with the ASUS Astral shipping 400 W and officially extendable to 450 W via vendor tooling, and Gigabyte's 5080 Gaming OC also reaching 450 W, the highest in its roundup ([TPU mVolt article](https://www.techpowerup.com/351867/nvidia-power-limit-bypass-rtx-5090-oc-hits-700-w-rtx-5080-up-to-680-w-no-shunt-mod-needed), [TPU Gigabyte 5080 review](https://www.techpowerup.com/review/gigabyte-geforce-rtx-5080-gaming-oc/41.html)).
- **12V-2x6**: the 50-series standardized the revised 600 W connector (12V-2x6, specified in the ATX 3.1/PCIe 5.1 era, with shortened sense pins and stiffer conductor housings vs 12VHPWR — [pinout reference](https://www.hardwarebook.info/PCIe_12V-2x6)). The melting problem did **not** die with the rename: unofficial-connector melts ([TPU](https://www.techpowerup.com/332334/unofficial-12v-2x6v-power-connector-melts-nvidia-geforce-rtx-5090)), a 175 °C cable failure in 2026 ([TPU](https://www.techpowerup.com/352273/hardware-unboxed-falls-victim-to-melted-rtx-5090-power-connector-as-cable-reaches-175-c)), and a warranty claim reportedly denied over non-native cables ([TPU](https://www.techpowerup.com/353113/pny-reportedly-denies-melted-rtx-5090-warranty-claim-says-native-psu-cables-not-covered)). Any vBIOS/power-target work on Blackwell must treat connector thermals as the hard ceiling.
- **2025 vBIOS update waves (the "black screen saga")**: launch-window RTX 5080/5090 black screens were addressed first by the [572.75 hotfix driver](https://www.nvidia.com/en-us/geforce/forums/game-ready-drivers/13/559436/announcing-geforce-hotfix-driver-57275-released-38/), then by **vBIOS updates**: NVIDIA staff confirmed a BIOS-level fix, with MSI shipping updated vBIOS through MSI Center and other AIBs following ([club386](https://www.club386.com/nvidia-will-fix-geforce-rtx-50-black-screens-with-a-bios-update/), [NVIDIA forum thread](https://www.nvidia.com/en-us/geforce/forums/game-ready-drivers/13/558263/a-vbios-update-for-50xx-is-fixing-the-black-screen/)); FE owners asked how vBIOS updates would reach Founders cards ([NVIDIA forum](https://www.nvidia.com/en-us/geforce/forums/geforce-graphics-cards/5/558250/nvidia-fe-5090-vbios-update-to-fix-black-screen-et/)). VideoCardz reported the fix riding both a driver and "the latest optional VBIOS update" from partners ([VideoCardz](https://videocardz.com/pixel/nvidia-releases-gpu-driver-fixing-several-black-screen-issues-on-geforce-rtx-50-series)).
- **Flash-free limit bypass**: in August 2026, mVolt+ v0.36 ([GitHub](https://github.com/b00nz/mVolt)) reportedly pushed a 5090 to ~700 W and an Astral 5080 to 680 W **without shunt mods or reflashing**, working around vBIOS power limits at runtime ([TPU](https://www.techpowerup.com/351867/nvidia-power-limit-bypass-rtx-5090-oc-hits-700-w-rtx-5080-up-to-680-w-no-shunt-mod-needed)). For firmware research this hints Blackwell's power controllers are runtime-programmable well beyond vBIOS tables — with zero margin on the connector.

## Creative techniques

- **BIT parser project**: build/extend a parser against the [official BIT spec](https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html) — scan for `0xB8FF "BIT\0"`, validate the header checksum, walk 6-byte tokens, and emit JSON per token. Prior art to study: [hdlcodelab/nvidia_rom_parser](https://github.com/hdlcodelab/nvidia_rom_parser) (C++, spec-based), envytools' `nvbios` ([repo](https://github.com/envytools/envytools/), [annotated docs](https://deepwiki.com/freedreno-zz/envytools/4-nvidia-vbios-parsing-(nvbios))), and [theopolis/uefi-firmware-parser](https://github.com/theopolis/uefi-firmware-parser) for the Code Type 03h UEFI sub-images.
- **Automated partner-BIOS diff pipeline**: fetch N same-chip ROMs from the [TPU database](https://www.techpowerup.com/vgabios/), parse each to JSON, then diff token-by-token; cluster differing fields against known spec deltas (power limits, fan curves, memory straps). This turns "which bytes are the power limit?" from archaeology into a one-command answer.
- **QEMU/VFIO sandbox**: keep all flash experiments off the production rig. Two safe uses: (a) test *parsing/analysis* tooling in a disposable VM against corpus ROMs; (b) on a lab machine, boot the card with a candidate ROM via OVMF/QEMU `romfile=` to exercise GOP-level parsing in isolation — noting honestly that **a real SPI flash cannot be sandboxed**: the write hits the chip regardless of VM.
- **Local vBIOS corpus with hashes**: mirror TPU downloads plus your own dumps; hash everything and record provenance, exactly like TPU publishes per-release SHA256s for nvflash ([example: 5.867](https://www.techpowerup.com/download/nvidia-nvflash/)):

```bash
sha256sum *.rom | tee SHA256SUMS
# provenance: TPU page URL, submitter, board, date downloaded, source of the dump
```

- **Watchlist (Rubin / "RTX 60")**: NVIDIA is reported to be readying Rubin-based GeForce RTX 60-series with big RT gains ([TPU, Mar 2026](https://www.techpowerup.com/347848/nvidia-readies-rubin-based-geforce-rtx-60-series-with-massive-rt-performance-gains)). Expect the same option-ROM/BIT skeleton, more runtime offload, and — given mVolt+ — more firmware-signed power control; watch whether nvflash-style EEPROM flashing survives another generation.

## Open questions

- [VERIFY] Where do Ampere GDDR6X and Blackwell GDDR7 **memory-training results** persist across boots — InfoROM, the SPI vBIOS chip's spare regions, or nowhere (retrain every cold boot)? No public documentation found as of 2026-10.
- [VERIFY] Exact current-best community fork status for 2026: nvflashk's GUI/auto-recovery roadmap was announced for late 2023-era releases; confirm whether it (or a successor) is still the maintained choice, and whether unsigned/modified ROMs can now be flashed on 40/50-series.
- [VERIFY] Whether Blackwell ROMs enforce signature checks on the SPI image itself (nvflashk's releases are signed-image proven; "unsigned/modified" was untested in its README).
- [VERIFY] The precise vBIOS↔GSP boot-time split per generation (what devinit remains in vBIOS vs what GSP re-does) for Pascal and Turing with the open kernel module.
- [VERIFY] Shunt-resistance↔power-table calibration coupling: whether the Power Control Table encodes board shunt values or only limits, i.e., how wrong a flashed XOC ROM's power telemetry is on a shunt-modded board.
- [VERIFY] Laptop vBIOS update channels for RTX 40/50 laptops (OEM WinFlash vs EC-integrated updaters) and whether GC6 scripts make laptop SPI reflashing categorically more dangerous than desktop.
- [VERIFY] RTX 50 FE vBIOS distribution mechanism (NVIDIA App? manual flasher?) — raised but unanswered in the FE owners' thread.
- [VERIFY] GDDR7 strap model: whether Blackwell still uses vBIOS strap tables (`'M'` token) or has moved memory config largely to fuses/training firmware.
