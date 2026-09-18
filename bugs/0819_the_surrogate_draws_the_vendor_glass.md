# 0819 -- the surrogate draws the vendor's glass, not its barrel

User, flag_20260918_134600_929: "lens surrogate oversized."

## Measured on the flagged scene

`attachment/machine_vision_120mm_65M.py`, lens `PYRITE_56_120_10x_V38_1097277/1097277_00155156_002.stp`:

| row | drawn | |
|---|---|---|
| Front Optical Vertex Datum | **46.0 mm** | the STEP's collar, exactly (`_step_barrel_diameter` = 46.0) |
| Blackbox Group 1 / 2 | **38.0 mm** | |
| Aperture Stop F/5.6 | 21.55 mm | right: 120 / 5.6 = 21.4 mm entrance pupil |
| the STEP's visible glass | **30.39 mm** | `_step_glass_aperture` |

The recorded scene bounds say the same: the drawn lens body spans y -23.00..22.97 and the datum
discs -23.00..23.00 -- the surrogate is drawn flush with the outside of the barrel that holds it.

## Why bugs/0703 did not cover it

0703 ("the user's third oversized flag") taught the FOLDER IMPORT to prefer the measured glass over
the barrel, and it still does -- importing the same folder today gives 30.3906 on every block row,
and the library file regenerated this morning carries exactly that. What 0703 could not do is reach
a scene already built. This one descends from
`KrakenOS/common_optical_layouts/machine_vision_120mm_pyrite_datasheet_1x.py` (2026-07-23), a
hand-authored layout with `"diameter": 46.0` on the datums and `38.0` on the groups; the scene's row
names (`Object at 1X`, `Aperture Stop F/5.6`) are that generation's, not today's. Nothing re-derives
a saved scene's discs, so the barrel-sized glass is permanent.

Same shape as bugs/0817: a recorded number that was right once, with no way to bring it up to date.

## Fix

* `LayoutTableWorkbenchMixin.lens_surrogate_glass_aperture_mm()` -- the vendor's measured glass for
  the scene's lens STEP, through the bugs/0703 readers (glass, then barrel, then transverse extent).
* `refit_lens_surrogate_glass_to_step()` -- draws the imaging-lens block at that measurement:
  * only ever SHRINKS -- a disc the user narrowed is theirs;
  * never touches the **aperture stop** row, and never shrinks any row below it;
  * refuses, with a reason and no write, when there is no lens block, no measurement, or nothing
    left to do;
  * captures history and syncs the table (bugs/0815).
* The lens STEP's right-click offers **"Refit Surrogate Glass to Vendor STEP (46 -> 30.39 mm)..."**,
  and only when the discs really are wider. It confirms with both numbers, applies through the
  editor and redraws through `_apply_model_change`.

The prescription does not move: powers, gaps and the stop are untouched. Only how wide the glass is
DRAWN changes -- and with it the vignette the scene shows, which is the vendor's own.

## Measured after

| | before | after |
|---|---|---|
| datum discs | 46.0 mm | **30.3906 mm** |
| group discs | 38.0 mm | **30.3906 mm** |
| aperture stop | 21.55 mm | 21.55 mm |
| ray paths in the preview bundle | 189 | **189** |

Rendered before and after with the same camera (`bugs/0819_glass_refit_after.png`): the discs now sit
inside the barrel instead of standing proud of it.

Applied to the user's scene, which is saved with the refit (backup:
`attachment/machine_vision_120mm_65M.pre0819_backup.py`). Worth knowing: the plain load/save round
trip also rewrites the Object row's diameter, 37.3600 -> 36.0555 (the object field is derived from
the sensor and |m| = 1.0362). Measured on a load-and-save with no refit at all, so it is the
normalisation, not this fix.

## Guard

`validate_open3d_0819_the_surrogate_draws_the_vendor_glass` (penta phase 598), display-free:

* A: the refit on a rows-only fake editor -- the flagged 46/38 shape lands on the glass with the
  stop untouched, a second refit declines, discs already inside are left alone, a measurement below
  the stop cannot shrink past it, and the three refusals write nothing;
* B: the reader returns the glass (30.39) and not the collar (46.0), which is bugs/0703's rule
  pinned at the new entry point;
* C: the user's scene draws inside its vendor glass;
* D: the verb appears only on an oversized surrogate, carries both numbers, and the command
  confirms -> editor -> `_apply_model_change`.

## The sweep across the shipped layouts, and where it stops

Measured per layout: the vendor glass, the widest drawn disc, and what the refit costs in rays that
REACH the sensor (`reaches_image`, 189-ray preview unless noted).

| layout | glass | widest | reach before -> after | done |
|---|---|---|---|---|
| `machine_vision_120mm_pyrite_datasheet_1x` | 30.39 | 46.00 | 189 -> 189 | **refitted** |
| `machine_vision_120mm_pyrite_datasheet_05x` | 30.39 | 46.00 | 189 -> 189 | **refitted** |
| `machine_vision_pyrite_45_85_05x_20x_v38...` | 22.29 | 26.48 | 165 -> 165 | **refitted** (local, untracked) |
| `machine_vision_pyrite_45_90_03x_v38...` | 28.39 | 50.06 | 189 -> 189 | **refitted** (local, untracked) |
| `machine_vision_pyrite_56_80_10x_v38...` | 23.82 | 46.00 | 189 -> 189 | **refitted** (local, untracked) |
| `machine_vision_pyrite_40_45_v38...` | 14.64 | 16.37 | 189 -> 189 | **refitted** (local, untracked) |
| `machine_vision_150mm_datasheet_1x` / `_0_5x` | 18.60 | 35.00 | 147 -> 147 | **held back** -- see below |
| `machine_vision_AZ85_RA_Mirror` | 14.16 | 29.00 | 325/729 -> 325/729 | held back: 95 guards read it |
| `machine_vision_els_85_4_5v16k` | 14.16 | 26.44 | 189 -> **169** | held back: loses 20 |
| `machine_vision_150mm_measured` | 18.60 | 35.00 | 141 -> **129** | held back: loses 12 |

Each refit was applied as a MINIMAL text edit -- the command decides the numbers (load, refit, read
back) and only those literals are written, in whichever of the two layout styles the file uses --
then the file is re-loaded and every row field compared, so nothing but the intended diameters moves.

### The rule that decides it: a glass narrower than the pupil is not the front element

The AZ85 sweep was the one that produced the rule. `ELS-85-4.5V16K.STEP` reads **14.16 mm** of
"glass" against a scene whose stop is **18.89 mm** (85 / 4.5). A front element narrower than the
pupil it must pass cannot exist, so 14.16 mm is not the front element -- the reader found an inner
element or a mount ring. With `target = max(glass, stop)` the refit would have quietly drawn that
lens at exactly its pupil, on a measurement already known to be wrong.

So the command REFUSES when the measured glass is narrower than the pupil the scene passes, naming
both numbers, and the right-click does not offer a verb that cannot run. Measured, live:

```
machine_vision_AZ85_RA_Mirror.py       the lens STEP measures 14.16 mm of glass, narrower than
machine_vision_els_85_4_5v16k.py       the 18.89 mm pupil this scene passes -- that cannot be the
                                       front element, so nothing was refitted
machine_vision_150mm_measured.py       ... 18.6 mm of glass, narrower than the 19.36 mm pupil ...
machine_vision_150mm_datasheet_1x.py   ... 18.6 mm of glass, narrower than the 19.36 mm pupil ...
```

That single rule accounts for all four layouts held back below, which had shown three different
symptoms -- a parity fixture losing its vignetted strays, and two scenes losing 20 and 12 reaching
rays. They were all the same defect: the refit falling back to the stop on a bad measurement and
squeezing the lens onto its own pupil.

### Why the 150 mm pair is held back: the drawn disc is load-bearing

Refitting them turned `validate_open3d_clipped_vignetting_parity` red on its premise:

```
before:  PASS parity layout produces vignetted strays to hide (total=45 hit=27)
after:   FAIL parity layout produces vignetted strays to hide (total=45 hit=45)
```

The launch samples the DRAWN aperture, so narrowing the discs narrowed the bundle and every ray
landed on the detector: the 18 vignetted strays that fixture is built on stopped existing. The disc
is not decoration -- on a scene whose aperture is not stop-pinned it sets what is launched. That is
exactly why bugs/0819 makes the refit a user-invoked verb that says what it will do, rather than
something the app does on its own, and why the two layouts that LOSE reaching rays (els_85, 150 mm
measured) are the user's call and not mine: the loss is the vendor's real vignette appearing, and
whether a fixture should show it is a decision about the fixture.

`machine_vision_AZ85_RA_Mirror` loses nothing measurable but is read by 95 guards -- a sweep of it
belongs in a run of its own.

### Guards run after the sweep

`validate_open3d_lens_step_datum_attached`, `validate_open3d_aperture_stop_vignette`,
`validate_open3d_ray_fan_count`, `validate_ray_launch_center_uniform_fan`,
`validate_open3d_clipped_rays_sync`, `validate_open3d_launch_cone_geometry`,
`validate_open3d_object_plane_after_promote`, `validate_open3d_thickness_solve`,
`validate_open3d_quick_estimation_conjugate` -- all pass, as does penta phase 598 with its new
check E pinning the two swept layouts.

`validate_machine_vision_pyrite_120_surrogate` fails, and failed identically with the file restored
from git: it is about the STEP's glass-vertex Z offsets, not the diameters, and predates this work.

## Still open -- the shipped layouts of that vintage

Measured across `KrakenOS/common_optical_layouts/machine_vision_*.py` with a bundled lens STEP, the
widest drawn disc against the STEP's measured glass:

| layout | glass | widest disc | |
|---|---|---|---|
| `machine_vision_150mm_datasheet_0_5x` / `_1x` / `_measured` | 18.60 | 35.00 | 1.88x |
| `machine_vision_AZ85_RA_Mirror` | 14.16 | 29.00 | 2.05x |
| `machine_vision_els_85_4_5v16k` | 14.16 | 26.44 | 1.87x |
| `machine_vision_pyrite_45_90_03x_v38...` | 28.39 | 50.06 | 1.76x |
| `machine_vision_pyrite_56_80_10x_v38...` | 23.82 | 46.00 | 1.93x |
| `machine_vision_pyrite_45_85_05x_20x_v38...` | 22.29 | 26.48 | 1.19x |
| `machine_vision_pyrite_40_45_v38...` | 14.64 | 16.37 | 1.12x |

Every scene started from one of those inherits the oversized discs. The refit above is the mechanism
to correct them, but several are loaded by penta phases whose expectations would move with them, so
that sweep is its own step.
