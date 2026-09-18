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
