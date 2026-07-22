# 0414 — Sweep the lens-STEP detach fix across all narrow-barrel layouts

**User (after 0412 fixed AZ85):** "Yes, fix all other possible detach files."

0412 fixed the AZ85 RA-mirror scene: a layout's `lens_step_placement_offset_xyz` z was a stale pre-0374
glass-alignment nudge that double-counts the 0374 glass-centre pin and detaches the lens STEP. The same
class of stale offset lives in every other layout authored before 0374. This sweep finds and fixes them
all, data-driven (not by eyeball).

## Which layouts, and why each one

The 0374 glass-centre pin (`_lens_step_display_front_z`) is active **only for a narrow barrel** —
`body_span <= 1.6 * glass_span`. For those, the pin aligns the glass on the datum span and any stored
glass-alignment offset double-counts → detach. For a **wide** barrel (`body_span > 1.6*glass_span`, e.g.
the Edmund 15056 the 0377 comment cites) the pin is NOT used, the body-face pin is intended, and the
offset is legitimate → must be kept.

I enumerated every layout carrying a non-zero `lens_step_placement_offset_xyz` and measured each lens's
real barrel ratio (`_step_optical_glass_axial_metrics` over the STEP via OCC; ELS-85 / Pyrite-85 from the
on-disk glass cache, the two 120 mm Pyrites built fresh):

| layout | lens | body/glass | verdict | offset |
|---|---|---|---|---|
| `machine_vision_AZ85_RA_Mirror.py` (0412) | ELS-85 | 1.076 | narrow | → 0 |
| `machine_vision_85mm_azure_datasheet_05x_20x.py` | ELS-85 | 1.076 | narrow | → 0 |
| `machine_vision_85mm_pyrite_datasheet_05x_20x.py` | Pyrite-85 (1072517) | 1.211 | narrow | → 0 |
| `machine_vision_120mm_pyrite_datasheet_05x.py` | 120 mm (1097787) | 1.101 | narrow | → 0 |
| `machine_vision_120mm_pyrite_datasheet_1x.py` | 120 mm (1097277) | 1.075 | narrow | → 0 |
| `attachment/machine_vision_120mm_65M.py` | 120 mm (1097277) | 1.075 | narrow | → 0 |
| `attachment/machine_vision_Pyrite85_RA_Mirror.py` | Pyrite-85 (1072517) | 1.211 | narrow | → 0 |

**Every one is a narrow barrel** — no wide-barrel layout carries an offset, so nothing had to be kept.
All seven offsets were pure-z glass-alignment nudges (no genuine x/y decenter), so zeroing z is safe. The
four datasheet layouts stored the offset as the named `STEP_GLASS_ALIGNMENT_Z_OFFSET_MM`; the constant is
kept as geometry documentation but no longer applied. (The two `attachment/` copies are the user's
gitignored working files — fixed on disk, not committed.)

## Verification (extends `validate_open3d_lens_step_datum_attached`, penta phase 336)

The 0412 guard's LAYOUT-CLEAN check now iterates **all five committed narrow-barrel layouts** and asserts
each pins `lens_step_placement_offset_xyz` z at 0 — the token check fails on a nonzero literal **or** the
`STEP_GLASS_ALIGNMENT_Z_OFFSET_MM` name being reintroduced. PIN-GEOMETRY + MECHANISM (ELS-85 pin math)
unchanged. 3/3 pass; baseline phase 336 stays pass.

## Files

- `KrakenOS/common_optical_layouts/machine_vision_85mm_azure_datasheet_05x_20x.py`
- `KrakenOS/common_optical_layouts/machine_vision_85mm_pyrite_datasheet_05x_20x.py`
- `KrakenOS/common_optical_layouts/machine_vision_120mm_pyrite_datasheet_05x.py`
- `KrakenOS/common_optical_layouts/machine_vision_120mm_pyrite_datasheet_1x.py`
- `attachment/machine_vision_120mm_65M.py`, `attachment/machine_vision_Pyrite85_RA_Mirror.py` (working copies)
- `KrakenOS/UI/validate_open3d_lens_step_datum_attached.py` — LAYOUT-CLEAN now covers 5 layouts.

## In-app eyeball still owed

Open each datasheet scene (85 mm Azure, 85 mm Pyrite, 120 mm Pyrite 0.5×, 120 mm Pyrite 1×) and the two
attachment scenes → the imaging-lens STEP glass sits inside its surrogate datums, not floating ~3 mm off.
