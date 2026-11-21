# VCNE RTX

Notes, tools and sources for running **GTA Vice City Nextgen Edition** (VCNE, a GTA IV total conversion by Revolution Team) with **RTX Remix** and xoxor4d's [gta4-rtx](https://github.com/xoxor4d/gta4-rtx) compatibility mod.

No game files, executables, third-party mods or Rockstar assets are in this repo. You need your own legitimately owned copies of everything below.

## Requirements
- GTA IV: The Complete Edition **1.2.0.59**. gta4-rtx only supports this exe; VCNE ships for 1.0.8.0.
- VCNE installed into a separate copy of that game folder.
- gta4-rtx release (Remix runtime in `.trex\`, `a_gta4-rtx.asi`, Ultimate ASI Loader, RTX FusionFix fork).

## What it took (summary; full log with reasons in [CHANGES.md](CHANGES.md))
| Problem | Fix |
|---|---|
| ZolikaPatch 7.6.5 exits on 1.2.0.59 | leave it out |
| IV-SDK .NET has no 1.2.0.59 offsets | leave it out (VCNE's .NET scripts don't run) |
| Load crash (heap corruption) | VCNE has 103 weapon models, the CE exe holds 100: FusionFix `[BudgetedIV] ExtendedLimits = 1` |
| gta4-rtx exception at start | complete `rtx_comp\` (empty `markers\`, `light_tweaks\`, [map_settings.toml](config/rtx_comp/map_settings.toml)) |
| Broken alpha | remove the stray duplicate `common\shaders\db\gta_alpha (2).sps` (gta4-rtx identifies shaders by preset index) |
| White grass cards | use FusionFix's fixed procedural-object models |
| Glowing white lamp poles | lamps use FusionFix's `gta_normal_spec_reflect_emissive` shader; replaced via a Remix mod (see below) |
| ASIs that crash on 1.2.0.59 | IVLodLights, XLivelessAddon, VolumetricLights and others; see CHANGES.md |

## Contents
- [`portable_saves/`](portable_saves/): `PortableSaves.asi` source. Patches GTAIV.exe's `SHGetFolderPath` import so `CSIDL_PERSONAL` resolves to `<game>\Profiles\Documents`; saves and settings stay separate from other GTA IV installs. Build: `build.cmd` (MSVC x86). Only useful when the game saves to Documents; the setup this was written for keeps saves elsewhere, so it is not installed there.
- [`tools/festive/`](tools/festive/): converts the GTA V mod *Festive Streetlights V* (by Yash Kanojia, not included; get it from its author) into an RTX Remix replacement mod for VCNE's street lamps (`vc_stolb_*`) and traffic lights (`vc2_svetafors*`). Includes a reader for unencrypted RPF7 archives, a Gen8 ydr/ytd reader, a GTA IV resource reader, and `meshhash.c` (Remix mesh hash, the same maths as gta4-rtx). Run `python -I build.py`; paths at the top of the script.
- [`tools/debug/`](tools/debug/): `run.ps1` launches the game, takes screenshots and collects dialogs and crash events; `dbg.py` is a minimal debugger; `img*.py` handle GTA IV `.img` archives; `disasm.py` does disassembly.
- [`config/`](config/): files written for VCNE.

Paths in the scripts are those of the original setup (`F:\games\VCNE_RTX`, `E:\_tools\...`); adjust them for your machine.

## Related
- Remix runtime fork with foliage wind: [spartaque12/dxvk-remix](https://github.com/spartaque12/dxvk-remix) (branch `gta4-wind`).
