# 0713/0714 — launch rides the device face; the solve consults the lens slide

(flag_20260903_165937 "I left the FOV blank after resize, seems like the FOV
is not 5% as stated. The rays not launching from the object plane. Recurring
bug." + user directive "to solve for correct FOV, the lens distance should
be adjusted.")

## 1 — the launch rides the device's face A (0713)

The OBJECT row IS the device: on a resize its `desp_z` takes the new face-A
position (hardware rows stay byte-identical, the 0712 directive). Three
engine pieces honour it:

- `_build_world_bundles_from_pupil_points`: the finite-object launch origin z
  was HARDCODED 0.0 — now `origin_z = rows[0].desp_z` (zero on every legacy
  scene). Aim targets are absolute pupil z, so the throw lengthens correctly.
- `_paraxial_reference_rows_for_layout`: the object desp folds into the
  reference object distance (distance = thickness − desp_z), so
  magnification/conjugates see the true throw (object_principal 292.5 → 310).
- The mirrored faceB twin reflects the face-A plane onto face B by
  construction (launch histogram −17.5 / −32.5 exactly).

## 2 — bands draw the REQUIREMENT even on a refused solve (0713)

`solve_fov_to_inspection_face` writes the requested width into both bands on
refusal too — the green planes show what is REQUIRED (face+5% = 15.75 →
"FOV 15.8×8.3"); the refusal message says whether the current lens delivers.

## 3 — the object-side solve gate opens to the lens-leg slide (0714)

`_folded_conjugate_gaps_for_magnification` bailed to the plain "no
real-image conjugate" whenever the station-frame OBJECT gap total went
non-positive — but on a frozen fold the object delta is booked by the
LENS-LEG SLIDE (bugs/0571), never the object gap row. The 0588-symmetric
gate: when `_lens_leg_slide_plan()` exists, proceed; the slide's own
refusal channel reports real room limits. Measured: the 15 mm device's
|m|=1.46 solve now reaches the machinery and refuses honestly with "FOV out
of range on the folded arms (leg room)" — the actionable lens-selection
signal — instead of the dead-end conjugate message.

## End-to-end (om05a, 15x15x1, blank FOV)

Launches {−17.5: 2166, −32.5: 1083} = the device faces exactly; hardware
rows byte-identical; reach 330 → 744; bands 7.875 half. Remaining shortfall
= focus/lens choice (the honest refusal names it).

## Guards

Phase 513 guard: F1 launch-origin pin, F2 paraxial fold-in, F3 object-gate
pin — 13 checks green. Phases 509 + 510 re-run green (paraxial file touched).
