# 0453 — BS cube detaches from the LED after a FOV thickness solve

**Flag `flag_20260726_132644` "BS Cube detached from the LED STEP after changing FOV"** (recording
`recording_20260727_132712.json`), on the coaxial 150 mm scene: Object → promoted BS cube on the LED
→ imaging lens → sensor, all straight on +Z. The user flagged it as a regression from the recent
fixes and asked for a guard — correctly.

## What the recording shows

The one command was `fov_solve {plane: object, mode: thickness, width: 23, height: 23}` — the
straight "Solve for Thickness", no fold-leg pins. State delta across it:

| body | before | after | Δ |
|---|---|---|---|
| BS row (S1) | z=229.6 | z=125.5 | **−104** |
| lens datums (S3–S7) | ~397–446 | ~293–342 | −104 |
| lens STEP barrel | 425.8 | 321.7 | −104 |
| Image (S8) / camera | 657 / 682 | 615 / 640 | −42 / −42 |
| **LED STEP body** | **225.1** | **225.1** | **0** |

Everything on the imaging chain slid toward the object (object distance shrank), and the lens/camera
STEP bodies followed — but the LED STEP body is anchored separately and stayed put, so the promoted
BS cube slid out of its LED housing.

## Root cause (the regression the user suspected)

`_apply_conjugate_pair` writes the OBJECT gap for a thickness solve *unless*
`_object_locked_redirect_row` says the object side is a fixed illumination unit — in which case it
holds the object gap and moves the lens gap instead (flag_20260628_212404: "the glued LED+BS is a
FIXED illumination constraint, exclude it from QE"). That redirect gated **only** on the
`_optical_led_glued` bool.

That bool was True *by accident*: before **bugs/0449**, the settings service could not write the
editor's `_optical_led_glued` (the `__setattr__` delegation trap of 0306/0312), so a stale runtime
`True` lingered and kept the redirect firing. bugs/0449 fixed the write — the flag now restores to
the scene's saved `False` — and the redirect stopped, the object gap started moving, and the BS
detached. The saved scene has the BS *on* the LED but `optical_led_glued: False` and no beam-splitter
mark, so neither the bool nor a mark identifies the unit.

## Fix

The LED+BS illumination unit is defined by **topology**, not the glue bool:
`_object_locked_redirect_row` now fires when `_optical_led_glued` is True **or** an LED STEP is
imported (`_step_path_for_label("led")`), given the structural checks it already makes — a promoted
solid immediately after the object gap, followed by a non-terminal air gap. So the thickness solve
holds the object gap (BS stays on the LED) and moves the lens instead, the same conjugate/focus/FOV
result. A scene with no LED and no glue is untouched (the object gap remains free to move).

## Verification

`bugs/probe_0453_bs_led_fov_solve.py` (reconstructs the flag config — LED present, glue False —
asserts the redirect fires, the object gap is held, the lens gap absorbs the change; negative control
with no LED). Guard `validate_open3d_0453_bs_led_fov_solve` (penta 368). The one battery FAIL
(`illumination_footprint_projection`, penta 253) is a pre-existing 0434 env failure — stash A/B
confirmed it fails at HEAD without this change.

## Files

- `KrakenOS/UI/services/quick_estimation.py` — `_object_locked_redirect_row` topology broadening.
- `bugs/probe_0453_bs_led_fov_solve.py`, `KrakenOS/UI/validate_open3d_0453_bs_led_fov_solve.py`.
