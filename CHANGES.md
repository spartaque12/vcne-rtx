# VCNE_RTX – changes made while getting VCNE running on GTA IV CE 1.2.0.59 + RTX Remix

All paths relative to `F:\games\VCNE_RTX`. Nothing in the original VCNE install or `E:\games\Grand Theft Auto IV` was touched.

## Root causes
1. **ZolikaPatch 7.6.5 does not support 1.2.0.59** – with it loaded the game exits ~1 s after start (exit code 0x8000FFFF, no window, no crash event).
2. **Weapon model-info store overflow** – VCNE's `update\common\data\default.ide` has 103 `weap` entries; the CE exe's weapon store holds 100
   (static capacities in the exe: base 28000, time 1800, weap 100, veh 205, ped 585). Entry 101+ writes past the array →
   0xC0000374 heap corruption / call through garbage vtable at `GTAIV.exe+0x5DBFFC` (IDE `weap` line parser `+0x5DA090`).
3. **gta4-rtx threw a C++ exception at startup** (exit 0xE06D7363) because `rtx_comp\` had no `map_settings.toml`, `markers\`, `light_tweaks\`.
4. **Broken alpha/cutout textures under Remix** – stray file `common\shaders\db\gta_alpha (2).sps` shifted every shader-preset index by one.
   gta4-rtx identifies shaders by hard-coded preset index (GTA_CUTOUT=2, GTA_TREES=79, ...), so every material was misclassified.

## Changes
| What | Change | Revert |
|---|---|---|
| `plugins\ZolikaPatch.asi` | moved to `_debug\parked\ZolikaPatch.asi` | move back (will not work on 1.2.0.59) |
| `plugins\GTAIV.EFLC.FusionFix.ini` | `[BudgetedIV] ExtendedLimits = 0` → `1` (raises model-info limits) | backup: `_debug\FusionFix.ini.before` |
| `plugins\GTAIV.EFLC.FusionFix.cfg` | `SkipMenu = 0` → `1` during testing; **restored to 0** at the end | backup: `_debug\FusionFix.cfg.before_autoskip` |
| `d3d9.dll`, `a_gta4-rtx.asi` | moved back from `_vcne_1080_files\bisect\` to the root (Remix on) | move back to disable Remix |
| `rtx_comp\addon_settings\`, `rtx_comp\weather_presets\` | copied from E: | delete |
| `rtx_comp\markers\`, `rtx_comp\light_tweaks\` | created empty (E:'s contents are Liberty City specific) | delete |
| `rtx_comp\map_settings.toml` | new, `ANTICULL = []` (LC indices don't apply) | delete |
| `common\shaders\db\gta_alpha (2).sps` | moved to `_vcne_1080_files\shaders_db_stray\` (identical duplicate of gta_alpha.sps) | move back |

## Tools (in `_debug\`)
- `run.ps1 [-Tag x] [-Seconds n] [-ShotEvery n]` – launch, watch, PrintWindow screenshots (`shot_<tag>_<sec>s.png`), dialog text, crash events, kill. Log: `run_<tag>.log`.
- `dbg.py [seconds] [--debugheap]` – minimal debugger (module list, exceptions, registers, stack scan) → `dbg.log`.
- `disasm.py <pe> <rva-hex> [before] [after]` – capstone disassembly around an RVA.

## Round 2 (alpha / grass / lampposts / trainer)
| What | Change | Revert |
|---|---|---|
| `common\shaders\db\deferred_lighting.fxc`, `rage_postfx.fxc`, `visualSettings.dat`, `visualSettings.xls` | stray non-preset files moved to `_vcne_1080_files\shaders_db_stray\` so the folder listing matches stock (preset index order) | move back |
| `update\0_IV_procobj_FusionFix\iv_procobj_fusionfix.img` | **new**: 235 procedural-object models/textures (weeds, bushes, grass, litter) extracted from E:'s `update\GTAIV.EFLC.FusionFix\GTAIV.EFLC.FusionFix.img` with `_debug\imgextract.py`. VCNE's `procobj.img` is byte-identical to stock IV, but E: renders FusionFix's fixed versions (e.g. `ag_deadbush3/4/5`, `ag_bushy02`: `gta_alpha` → `gta_cutout`, `sm_weed*`: `gta_trees` → `gta_cutout`); stock ones show as opaque white cards under Remix | delete the folder |
| `ScriptHook.dll` (root) | copied from E: – `Liberty's Legacy.asi` imports it (ASI loader error 126 dialog without it) | delete |
| `Liberty's Legacy.asi`, `Liberty's Legacy\`, `aCompleteEditionHook.asi` (root) | copied from E: by the coordinator at the user's request | delete |

Findings:
- Glowing white lamppost poles come from the gta4-rtx **Remix API static path** (`api_static_enabled`): with it off the same pole renders normally
  (`_debug\cmp_lamps.png`: left = off, right = on). Clearing `rtx.worldSpaceUiTextures/skyBoxTextures/beamTextures` made no difference (rtx.conf restored, backup `_debug\rtx.conf.before`).
- With Remix the game exits with code 0x42B when its window loses focus (`D3D9SwapChainEx: Failed to recreate swap chain` in `rtx-remix\logs\remix-dxvk.log`).

## Round 3 (trainer, car paint, perf flags)
| What | Change | Revert |
|---|---|---|
| `aCompleteEditionHook.asi` + `ScriptHook.dll` + `Liberty's Legacy.asi` | kept; `ScriptHook.log` shows `Using game version Dynamic (1.2.0.59)` / `[LibertysLegacy] Thread started`; user confirmed the trainer works | delete the three |
| `rtx-remix\mods\VCNE_comp_subset\` | **new** Remix mod: `comp_cars`, `comp_vehicle`, `comp_effects`, `comp_water` layers + their assets copied from E:'s `rtx-remix\mods\A_WARCACORTX` (27 MB). Loads (see `remix-dxvk.log`), but the car-paint overrides are keyed by IV texture hashes and VCNE ships its own `vehshare.wtd`, so VCNE car paint is **not** covered yet | delete the folder |
| `rtx_comp\comp_settings.toml` | test-only edits (`api_static_enabled`, `api_static_entity_skip`, `api_static_skip_pass_setup`) all reverted – file equals `_debug\comp_settings.toml.before2` | – |
| `plugins\GTAIV.EFLC.FusionFix.cfg` | `SkipMenu` back to 0 | – |

Test results (API = gta4-rtx Remix API static path; FPS from the DXVK HUD in the screenshots):
| Config | FPS | Lamppost poles | Lamppost lights | Palm popping |
|---|---|---|---|---|
| all `api_static_*` on (shipped, current) | ~91 | glow white | none seen | yes |
| `entity_skip` + `skip_pass_setup` off | ~45 (user), 63 in `shot_e02_078s.png` | still white (`shot_e02_078s.png`) | none seen | gone (user) |
| `api_static_enabled = false` | ~49 | normal (`shot_e01_195s.png`, `cmp_lamps.png`) | not established (one lit road + pole shadow in `shot_e01_195s.png`, source unclear) | not checked |

## Round 4 (lamppost port)
Root cause of the glowing poles / missing lamp light: VCNE's `update\...\1. VariousMapEdits.img` ships lamp models (its own `vc_stolb_*`, `Streetlamp1/2`,
`bollardlight`, `lampost_coast`, `sub_floodlite` and IV's `bm_nylamp*`, `bm_wall_light_*`, `bm_nytraflite*`, ...) built on FusionFix's
`gta_normal_spec_reflect_emissive` shader preset, which the gta4-rtx Remix API path renders as a fully lit white mesh. E: avoids this with `update\1__remix_light_tweaks.img`.

| What | Change | Revert |
|---|---|---|
| `update\0__rtx_iv_lampposts.img` | **new**: `vc_stolb_1/1b/5` = IV `bm_nylamp1`, `vc_stolb_3/4` = `bm_nylamp1b`, `vc_stolb_2` = `bm_nylamp2b` (models from E:'s `1__remix_light_tweaks.img`), `vc_stolbs.wtd` = IV `ny_lamp_chrome.wtd` (stock `lamppost.img`). Built with `_debug\imgextract.py` + `_debug\lamp_map_*.txt` | delete the img |
| `update\0__remix_light_tweaks.img` | copy of E:'s `update\1__remix_light_tweaks.img` (Remix-friendly IV lamps, wall lights, billboards); named `0__` to sort before VCNE's `1. Various Map Edits` | delete |
| `update\0__vc_lamps_base_shaders.img` | **new**: VCNE's own older `Streetlamp1/2`, `lampost_coast`, `bollardlight`, `sub_floodlite` from `pc\data\maps\vc_generic\vc_generic.img` (plain `gta_default` + `gta_emissive*`), overriding the FusionFix-shader versions | delete |
| `_debug\run.ps1` | waits for a running GTAIV.exe to exit instead of killing it | – |
| `_debug\imgextract.py` | new argument order: `<out.img> <src.img> <map.txt> [...]`, map lines `name[=newname]`, encrypted sources supported | – |

Lamppost port results (night runs, all `api_static_*` flags on): `shot_f01_106s.png` – IV lamp on a `vc_stolb` placement, normal pole, warm light and
pole shadows on the street; `shot_f01_244s.png` – globe lamps (`Streetlamp*`) still white before the last two imgs; `shot_g01_176s.png` – same lamp type
after them: pole normal, only the globe glows. FPS not re-measured in these runs (HUD counter not in the shots). `SkipMenu` restored to 0.

## Round 5 (lamp light position)
| What | Change | Revert |
|---|---|---|
| `update\pc\data\maps\vc_generic\vcDE_generic.ide` | the `2dfx` (light, glass, spark) and `amat` lines of `vc_stolb_1/1b/2/3/4/5` replaced by the lines of the IV model each one now uses (`BM_NYlamp1`, `BM_NYlamp1b`, `BM_NYlamp2b` from stock `lamppost.ide`). The VCNE lines attached the light to bone ids (49713, 49714, 40004) that do not exist in the IV models, so the light did not sit at the bulb | copy `_debug\vcDE_generic.ide.before` back |

## Round 6 (lamp work on hold – state left)
User asked for VCNE's own `vc_stolb_*` lamps back instead of the IV swap.
| What | Change | Revert / re-enable |
|---|---|---|
| `update\0__rtx_iv_lampposts.img` | **parked** in `_debug\parked\` (IV lamp swap off) | move back to `update\` |
| `update\pc\data\maps\vc_generic\vcDE_generic.ide` | **restored** to VCNE's original (`_debug\vcDE_generic.ide.before`); the round 5 edit only makes sense together with the IV swap | – |
| `_debug\parked\0__vc_stolb_plain_pole.img` | attempt, **not installed**: VCNE's `vc_stolb_*.wft` with the shader name/hash patched from `gta_normal_spec_reflect_emissive` to `gta_normal_spec` (`_debug\lamp_patch.py`). With it in `update\` the game hangs during the new-game load (window not responding, one core busy for 6 min, run i02); without it the same setup loads (run j01). A name/hash swap alone is not enough – the shader's parameter block has to be rebuilt too | – |
| `update\0__remix_light_tweaks.img`, `update\0__vc_lamps_base_shaders.img` | kept (tested in run g01) | delete |

Current lamps: `vc_stolb_*` are VCNE's originals again (FusionFix emissive shader → white glowing pole under Remix, as before the port);
`Streetlamp1/2`, `bollardlight`, `lampost_coast`, `sub_floodlite` use VCNE's older plain-shader models; IV-named lamps/wall lights use E:'s Remix versions.
`SkipMenu` = 0. New helpers: `_debug\imglib.py`, `_debug\lamp_patch.py`.

| `plugins\GTAIV.EFLC.FusionFix.ini` | `UnlockFramerateDuringLoadscreens = 0` -> `1` (faster loading, user request) | backup `_debug\FusionFix.ini.before_unlockload` |
| `plugins\GTAIV.EFLC.FusionFix.ini` | `UnlockFramerateDuringLoadscreens` back to `0` (user request) | - |

## Round 7 (Festive Streetlights V on vc_stolb_*)
GTA V mod "Festive Streetlights V" (personal use only, the readme forbids redistribution) put onto VCNE's `vc_stolb_*` lamps as a Remix replacement.
| What | Change | Revert |
|---|---|---|
| `rtx-remix\mods\VCNE_festive_lamps\` | **new** Remix mod: `mod.usda`, `assets\prop_streetlight_*.usda` (geometry + materials), `assets\empty.usda`, `assets	extures\*.dds` (the mod's own DXT textures) | delete the folder |
| `update\pc\data\mapsc_genericcDE_generic.ide` | xyz of the 7 `vc_stolb_*` light lines moved to the festive bulbs (offset is relative to the light's bone) | copy `_debugcDE_generic.ide.before` back |
| `_debug
un.ps1` | new options `-SkipUntil n` (tap Enter from 55 s to n s: skips the new-game intro), `-Hold 't:scancode:secs,...'` (scripted key holds), `-CaptureAt` (Remix capture hotkey; did not work, it reset the swap chain) | - |
| `rtx.conf`, `plugins\GTAIV.EFLC.FusionFix.cfg` | unchanged at the end (`rtx.debugLogGeometryHashes` was on for runs k04-k09 only; `SkipMenu` = 0) | - |

Mapping (festive arm points -Y, VC arm +X: rotated 90 deg about Z, uniform scale to the VC lamp height):
`vc_stolb_1`, `1b` = `prop_streetlight_01` x0.72; `vc_stolb_5` = `prop_streetlight_03` x0.755; `vc_stolb_3` = `prop_streetlight_01b` x0.83;
`vc_stolb_4` = `prop_streetlight_03` x0.78; `vc_stolb_2` (double arm) = `prop_streetlight_04` x1.16 (one amber, one white spiral).

How it works / findings:
- Every vc_stolb is a fragment of 6-9 parts, each its own Remix mesh. The pole part carries the whole festive model, all other parts are replaced
  by a 1 mm triangle (an empty `over` does not hide a mesh here).
- Remix mesh hash = geometry hash XOR material hash, for D3D9 draws and for gta4-rtx API meshes alike. Geometry hash: `meshhash.exe` (positions,
  indices, descriptor - same maths as gta4-rtx `d3d9_asset_hash`). Material hashes: runtime log with `rtx.debugLogGeometryHashes = True`, collected by
  `matscan.py` into `E:\_tools\festive_v\out\stolb_materials.json` (lamp materials: 71B15A72F93700C6 body, 832ADC0A16828418 base,
  D9DBFC7A7209FA27 box, AB61DA7720B5AD81 / D9E9D743F5A94FE6 bulb).
- Replacement geometry is in game units (metres); x100 came out 100 times too big.
- Materials need `use_legacy_alpha_state = 0`, otherwise the pole inherits the emissive pass's blend state and turns into a white ghost.
- `rtx.debugLogGeometryHashes` and Enter taps during the loading screen both crashed the game (0xC000041D) - test rig only, not the mod.
- SkipMenu = 1 prints "Load failed" and starts a new game: the CE exe looks for saves in `Documents\Rockstar Games\GTA IV\savegames` (shared with
  the E: install). Nothing was copied there. IV-SDK .NET does not load on this exe (its log stops on 9 Nov), so no scripted teleport.

Work files in `E:\_tools\festive_v\work\`: `rpf7.py` (RPF7 OPEN extractor), `gta5res.py` (ydr/ytd reader), `ivres.py` (IV wft reader), `build.py`
(rebuilds the mod and the ide: `python -I build.py`; env `EM_SPIRAL`, `EM_BULB`, `FESTIVE_MAP` to tune), `matscan.py`, `wplscan.py`
(1625 vc_stolb placements -> `..\out\stolb_places.txt`), `meshhash.c`. Sollumz/Blender were not used (Sollumz wanted to download szio + PyMateria).

Results: `shot_k12_156s.png` (night: yellow spiral, lit head, warm light and pole shadow on the road), `shot_k08_128s.png` / `shot_k08_119s.png`
(close up, before the original base/pole were hidden), `shot_k10_052s.png` (day, airport intro: dark poles, no white glow).
Not verified: `vc_stolb_2/3/4` on screen (their mesh keys were seen as "replaced" in the log for 2 and 3; 4's pole key is a guess from the shared
material), exact bulb position of the game light, FPS.

## Round 8 (festive traffic lights)
VCNE's junction lights are `vc2_svetafors1/2` (`1. VariousMapEdits.img`): pole `opora_1`, 12 m arm `opora_2`, two signal heads `simofor_1/2`.
They keep their own pole, arm and heads (the game switches the heads, so red/amber/green still work). Added on top, in the same mod
`rtx-remix\mods\VCNE_festive_lamps\`: the two spirals of the festive `prop_traffic_01b` -
`assets\traffic_pole_spiral.usda` (amber, squeezed from 8.5 m to the 5.9 m VC pole) on the pole mesh and `assets\traffic_arm_spiral.usda`
(white; the festive arm rises in a curve, so its axis is subtracted and the spiral stretched to the straight 12 m VC arm) on the arm mesh, both with
`preserveOriginalDrawCall = 1`. Mesh keys: pole 015A7F86F17BD5D2, arms A4ABD1CD6240FBB9 / 733262FC76E31825, XOR material 8DDEE7D11D9E396E
(arm of `vc2_svetafors2` was not in the log: it gets one key per known material). Built by the same `build.py` (`traffic_overs`, constants
`POLE_Z`, `POLE_R`, `ARM_X`, `ARM_R`); `gta5res.py` now also reads .yft. Revert: delete the two assets and rebuild, or delete the mod folder.
Result: `shot_tl02_139s.png` (night, three junction lights with spirals, green / amber / red heads in 139 s / 146 s / 155 s, HUD 94 FPS).
Placements (`wplscan.py`): 535 x `vc2_svetafors1`, 70 x `vc2_svetafors2`; the IV-style `BM_NYtraf*` and `MTraffic1/2` models are not placed
anywhere, so nothing else needed a spiral. Not covered: the damaged arm variant `opora_2_d` (knocked-over light loses the arm spiral).

`_debug\run.ps1` changes of this round (the car-paint runs use the same script):
- one run at a time: named mutex `Global\VCNE_run_ps1` (two runs had collided: "An instance of GTA IV is already running");
- `-NewGame` sets `SkipMenu = 1` and `-ConfAppend 'rtx.x = y'` adds an rtx.conf line, both only for that run and always undone;
- injected keys (`-SkipUntil`, `-Hold`) are only sent while the game is the foreground window (it is brought to the front once at 50 s);
- `-GameArgs` (default empty). A windowed 1280x720 launch was tried and **reverted** at the user's request: runs are full resolution as before,
  FusionFix `Windowed` was never changed. For the record: arguments replace `commandline.txt`; with its switches plus
  `-windowed -width 1280 -height 720` the game does come up as a 1280x720 window.
My runs leave `SkipMenu` and `rtx.conf` as they found them (`rtx.conf` = original). At the time of writing `SkipMenu` reads 1 because a
car-paint run (p07) is in progress; it is 0 between runs.

## Portable saves
| What | Change | Revert |
|---|---|---|
| `PortableSaves.asi` (root) | **new**, source + build in `_debug\portable_saves\`. Patches GTAIV.exe's SHGetFolderPathW/A import: CSIDL_PERSONAL -> `<game>\Profiles\Documents`, so saves/settings live in `Profiles\Documents\Rockstar Games\GTA IV\` instead of the user's Documents (shared with E:). Log: `Profiles\Documents\portable_saves.log` | delete the asi |
| `Profiles\Documents\Rockstar Games\GTA IV\savegames\SGTA412`, `SGTA400` | copies of VCNE's `Profiles\SGTAVC12` / `SGTAVC00` (same save format v0x39, CE naming). Originals untouched | delete |

## Festive colours (spiral colours adjustable in the Remix menu)
Goal: colour + brightness of the four neon spiral groups adjustable live in Alt+X.
| What | Change | Revert |
|---|---|---|
| `.trex\d3d9.dll`, `.trex\d3d9.pdb` | new runtime build from `E:\src\dxvk-remix`, branch `vcne-festive-colors` (commit 11a7e0db on top of `gta4-wind` acbe47ec), installed 21 Nov 13:25 | copy `_debug\runtime_backup\d3d9.dll` / `.pdb` back (the 20 Nov 09:34 build) |
| `rtx-remix\mods\VCNE_festive_lamps\assets\*.usda` | every spiral material got one line `custom string fork:tintGroup = "<group>"` (nothing else changed; an older runtime ignores it) | rebuild with the old `build.py`, or delete the line |
| `E:\_tools\festive_v\work\build.py` | writes that line: streetlight amber spiral = `lamp`, streetlight white spiral = `lamp2`, traffic pole = `trafficPole`, traffic arm = `trafficArm` | - |

Runtime (fork files `src\dxvk\rtx_render\rtx_fork_tint.cpp/.h`; touchpoints in `rtx_mod_usd.cpp` (reads the attribute into `MaterialData::forkTintGroup`),
`rtx_scene_manager.cpp` `createSurfaceMaterial` (colour replaces albedo + emissive colour, intensity scales emissive; both folded into the surface
material cache key), `dxvk_imgui.cpp` (UI header), `meson.build`, `rtx_materials.h`):
- options `rtx.festive.lampColor`, `lamp2Color`, `trafficPoleColor`, `trafficArmColor` (Vector3, defaults 1,0.72,0.08 / 1,1,1 / 1,0.72,0.08 / 1,1,1 = the
  colours the mod had) and `rtx.festive.<group>Intensity` (float, default 1, multiplies the material's `emissive_intensity` = `EM_SPIRAL` 3);
- the options carry `InvalidatesDrawcallTranslation`, so instances on the preserve path are retranslated the frame after a change (no reload);
- UI: Alt+X -> Game Setup -> Parameter Tuning -> **Festive Lights**: colour picker + Intensity per group, "Reset to Defaults". Saved by the normal
  "Save Settings" (rtx.conf). By hand: `rtx.festive.lampColor = 1, 0, 0` in rtx.conf.
- `lamp2` covers the white spiral of the double lamp (`vc_stolb_2`) and the all-white spiral of `vc_stolb_3` (`prop_streetlight_01b`). The double
  lamp's white was 0.976,0.988,0.996 in the texture, it is 1,1,1 now.
- Build note: one transient compiler ICE (C1001 in `dxvk_adapter.cpp`) during the build, the second pass of `_build.cmd` compiled it.
State at this point: built, installed, committed; **not yet verified in game** (run `fc01` was stopped at 28 s because the user started playing; it had
left `SkipMenu = 1`, set back to 0 by hand).

## Car paint
Cause of the matte cars: gta4-rtx draws vehicles through the Remix API with one material per colormap texture (default roughness 0.7, metallic 0.1;
`renderer_api.cpp` `find_or_create_material`), the replacement key is the image hash of that colormap. Every `gta_vehicle_paint1/2/3` body (and alloy
rims) uses `vehicle_generic_smallspecmap` as colormap; the body colour is the draw's texture factor, so it is not part of the material.
E:'s `A_WARCACORTX\comp_cars.usda` makes IV paint glossy with `mat_3F6C008F32FE3D33` (IV's 16x16 white smallspecmap: roughness 0.045, metallic 0).
VCNE's `vehshare.wtd` has a different smallspecmap (32x32, grey 173) = hash `F160FDA4C1DE53AF`, so that override never matched. There is no
per-shader-preset paint setting in gta4-rtx (`comp_settings.toml` is the same as E:'s, untouched).

| What | Change | Revert |
|---|---|---|
| `rtx-remix\mods\VCNE_car_paint\mod.usda` | **new** Remix mod, material overrides only (no assets): 3 smallspecmap variants (`F160FDA4C1DE53AF` vehshare, `FB5732C9CD9118D3` biff, `F11635990B1AE225` df8/noose/vincent/vincent2) + 19 textured paint bodies (coastg, oracle/rebla, tropic, mule, marbella, polpatriot, squalo/vcnmav, rio, perennial, dukes, dilettante, skimmer, vigero, hellfury, sparrow, peyote/willard), comments in the file | delete the folder |
| `_debug\imgscan.py` | `find_key()` cached | - |

Tools in `_debug\carpaint\`: `wtdhash.py <img> <regex>` (textures of WTDs with their Remix hash = XXH3-64 of mip 0; checked against IV: gives
`3F6C008F32FE3D33` for IV's smallspecmap), `wftshaders.py` (shader presets + texture names per WFT), lists `vc_base.txt` (all 1588 vehicle textures
with hashes), `veh_shaders.txt`, `paint_tex.txt` (paint shaders that do not use the generic smallspecmap), `settime.py` (test rig: writes the game
clock of a running game; written, not used yet).
Not covered: paint colormaps that are signs / interiors / rust / camo (steed_signs, marbella_sign_1, yankee_signs, torero_interior, desert_camo, tug,
dinghy ...), and cutscene car models (the airport-intro Admiral stays matte, `shot_p06_115s.png`).
