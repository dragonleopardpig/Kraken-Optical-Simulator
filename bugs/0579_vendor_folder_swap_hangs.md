# 0579 — four vendor lens folders HANG the swap (RESOLVED by bugs/0586 — see the correction)

> **CORRECTION (2026-08-07).** The diagnosis below — "the datasheet-PDF route hangs" — is WRONG.
> Called without a GUI, every one of these folders fails in **0.1–0.3 s** with
> `ValueError: surrogate needs a positive, finite effective focal length`. The 900-second
> timeouts were a **modal error dialog** (`messagebox.showerror`) reporting that failure to
> nobody. Root cause and fix: `bugs/0586_modal_dialog_blocks_api.md`. The signature reasoning
> below (no `.zmx`, no prescription dump → the PDF route) correctly identified *which* folders
> fail and *why they fail to import*; it was the HANG it explained wrongly, because the
> diagnosis was made from a timeout without ever obtaining a stack.

Found while answering the user's objective — "let the user change the imaging lens as will, and
change the camera as will" — by sweeping the vendor folders instead of chasing one flagged
combination. Harness: `bugs/matrix_0578_lens_camera_swap.py`.

**Status: diagnosed to a signature, NOT fixed.** The sweep was stopped part-way (12 of 26 cases)
for an unrelated shutdown; the camera rows and the seeded mixed pairs have not run.

## The sweep, as far as it got

Scene `machine_vision_Pyrite85_BS.py`, each case a fresh process, swap then solve 23×23.
`reseat` = the bugs/0568 transverse re-centre (informational). `attach` = |body motion −
surrogate motion| across the SOLVE, the bugs/0574 invariant. Rays are before / after swap / after
solve, out of 558.

| lens | reseat | attach | rays b/s/a | sensorZ | solve | |
|---|---|---|---|---|---|---|
| 0703-005-000-40-EXC | 5.4253 | **0.0000** | 170/136/27 | 3.03 | ok | PASS |
| 15056 | 2.4444 | **0.0000** | 170/184/184 | 24.30 | ok | PASS |
| Aspherized_Achromatic_Lenses | – | – | – | – | – | **TIMEOUT 900 s** |
| DCV50mm | – | – | – | – | – | **TIMEOUT 900 s** |
| DCX | – | – | – | – | – | **TIMEOUT 900 s** |
| ELS-85-4.5V16K | 1.7881 | **0.0000** | 170/164/54 | 24.30 | ok | PASS |
| PYRITE_45_85_05x-20x | 0.0000 | **0.0000** | 170/144/46 | 47.24 | ok | PASS |
| PYRITE_56_100 | 11.4601 | **0.0000** | 170/159/151 | 25.32 | ok | PASS |
| PYRITE_56_120_05x | 3.8711 | **0.0000** | 170/199/191 | 24.30 | ok | PASS |
| PYRITE_56_120_10x | 4.1430 | **0.0000** | 170/207/199 | 24.30 | ok | PASS |
| PYRITE_56_80_10x | 6.5322 | **0.0000** | 170/123/26 | 44.21 | ok | PASS |
| aspherized-achromatic-lenses | – | – | – | – | – | **TIMEOUT 900 s** |

## Two results worth keeping

**bugs/0574 is general.** `attach = 0.0000` on all eight measurable lenses — every EFL, every
barrel, including an 11.46 mm re-seat. Not a scene-specific fix.

**bugs/0577's guard holds everywhere.** `sensorZ` stays between 3.03 and 47.24 on all eight and
every solve returns ok. No runaway anywhere.

## The hang — signature, not yet a root cause

All four hanging folders share one shape: **no `.zmx` and no System/Prescription Data dump**, so
`machine_vision_folder_import` falls through to the datasheet-PDF route
(`parse_datasheet_cardinals`). Every folder that reaches that route hangs; every folder that does
not, passes.

```
DCX/                       CODV_32624.seq, edrw_32624.eprt, iges_32624.igs, isop/prnt .pdf   -> HANG
DCV50mm/                   zmax_32996.ZAR,  isop/prnt .pdf, iges .igs                        -> HANG
Aspherized_Achromatic/     zmax_49665.ZAR,  curv/prnt .pdf, iges .igs, step .step            -> HANG
15056/                     15056_BB_BB.zar + 15056_System_Presctiption_Data.txt              -> PASS
```

A secondary observation, unconfirmed: the two hanging folders that DO carry a Zemax archive spell
it `.ZAR` in **upper case**, while the passing `15056` uses lower case, and
`_ZAR_SUFFIXES = frozenset({".zar"})` is matched against `path.suffix`. If that comparison is not
case-folded the archive is invisible, which would explain why those two reach the PDF route at
all. That does not by itself explain a hang.

**A hang is worse than a crash here.** "Change lens at will" means picking any folder in the
dialog; four of fourteen currently freeze the app with no message and no way back.

## Next step

Reproduce ONE hanging folder standalone (not under the sweep parent, whose `TimeoutExpired`
discards child stderr) and dump the stack:

```
taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python \
    bugs/matrix_0578_lens_camera_swap.py --case attachment/Lens/DCX
# then, from another shell:
kill -USR1 <child pid>
```

`_child_main` arms `faulthandler.register(SIGUSR1, all_threads=True)` plus a 600 s repeating
backstop, so the hung frame prints itself — py-spy is not installed on this machine. Name the
frame before proposing a fix.

## Also open, from the same sweep

**Ray collapse after the solve, correlated with focal length.** Short lenses collapse
(0703 → 27, PYRITE_56_80_10x/80 mm → 26, PYRITE_45_85/85 mm → 46, ELS-85/85 mm → 54); long ones
keep (100 mm → 151, 120 mm → 191 and 199, 15056 → 184). Clean split at ~85 mm vs ≥100 mm. This is
plausibly honest physics — a short-EFL lens filling 23×23 on this machine works a harder conjugate
and vignettes more, and the scene's own native lens is in the collapsing group. **Decide it by
termination reason, not by the count**: `aperture_stop_vignette` is honest vignetting,
`no_next_intersection` is geometry missing the sensor. Only the second is a defect.

**The camera half is unmeasured.** `replace_camera_from_folder` prompts for the flange-to-sensor
distance when the datasheet lacks it (bugs/0408), which may block headless. The six camera rows
had not run when the sweep was stopped, so "change the camera at will" has no evidence either way.
