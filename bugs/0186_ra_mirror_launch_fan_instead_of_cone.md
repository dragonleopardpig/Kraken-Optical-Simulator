# 0186 — BUG: a promoted RA-mirror fold launches the rays as a flat FAN, not a revolved CONE

## Flag

`attachment/recorded_bug_repros/flag_20260630_142846_722/` on the folded AZURE ELS-85 layout
(`KrakenOS/common_optical_layouts/machine_vision_AZ85_RA_Mirror.py`), recorded right after the
bugs/0185 fold-follows-reflection fix:

> "Also, the rays launching in Fan instead of Cone, old bug resurfaced."

The recording's `sampling_diagnostics` confirms it: `prefers_meridional_fan: true`,
`is_full_pupil_mode: false`, `use_nonseq: true`, `use_folded: false`, `ray_count: 31`. This is a
recurrence of the bugs/0161 symptom (a non-branching non-seq scene collapsing the launch to a
flat meridional fan) — but for the **promoted right-angle mirror** layout, which 0161 never saw.

## Root cause — the mirror fold is invisible to `_scene_breaks_rotational_symmetry`

`_launch_pupil_prefers_meridional_fan` (`services/trace_preview_sampling.py`) collapses the launch
to a flat fan only for the bug-0126 carve-out: a **non-branching, rotationally-symmetric**
non-sequential scene (an in-line refractive mesh solid slid along the axis, whose revolved mesh
traces are too slow). It branches (keeps the area-filling disk → cone) when the scene has a beam
splitter / probabilistic split / diffuse scatter, or when `_scene_breaks_rotational_symmetry()` is
True (a tilt, a transverse decentre, or a reflective fold).

`_scene_breaks_rotational_symmetry` only recognised a fold from a **sequential** `surface ==
"Mirror"` row. The RA-mirror layout folds with a **PROMOTED STEP mirror cube** instead: row 1 is
`surface == "Standard"` with the reflection carried on an `OpticalSolidFaces` face whose
`function == "Mirror"` (the bugs/0185 architecture). Its row sits at `desp = (≈0, ≈0, 12.5)` — an
**axial slide only**, no tilt, no transverse decentre. So every test in
`_scene_breaks_rotational_symmetry` missed it, the function returned False, and the folded scene
was misclassified as the rotationally-symmetric inline-solid carve-out. With
`has_optical_stl_solid` True the launch then fell through to `return True` (flat fan):

- `_launch_pupil_prefers_meridional_fan()` → True (flat fan), then
- `_launch_cone_prefers_flat_fan()` → `bool(use_nonseq)` → True (the 3D cone stays a flat fan).

A 90° fold manifestly destroys rotational symmetry about the original axis (the whole downstream
path swings onto +X), so the launch must keep the area-filling disk and revolve a cone — exactly
what the flag asked for.

## Fix — recognise a promoted mirror fold as a symmetry-breaker

`KrakenOS/UI/trace_intent.py`:
- New `_optical_solid_faces_have_mirror_fold(metadata)` — the mirror-fold sibling of
  `_optical_solid_faces_have_beam_splitter`. True iff `normalize_optical_solid_face_metadata`
  yields a face with `function == "Mirror"`. A `"Beam Splitter"` face is intentionally **excluded**
  (a promoted beam-splitter keeps its real straight-through and branches via `has_beam_splitter`;
  bugs/0185 reflects the downstream chain only for a FULL mirror).

`KrakenOS/UI/services/trace_preview_sampling.py`:
- `_scene_breaks_rotational_symmetry` now also returns True when a row's
  `advanced["OpticalSolidFaces"]` carries a mirror-fold face. The existing sequential-`Mirror` and
  tilt/desp tests are unchanged, so a tilt, a transverse decentre, or a sequential mirror still
  trips it exactly as before.

Result on the RA-mirror layout: `_scene_breaks_rotational_symmetry()` → True →
`_launch_pupil_prefers_meridional_fan()` → False → `_launch_cone_prefers_flat_fan()` → False → the
launch revolves into a real 3D cone (`_sample_ray_count_cone_points` draws `1 + (N//2)·n_az`
samples with genuine off-meridian spokes, X=0 slice still the even N-ray fan).

## Verification

- Guard `KrakenOS/UI/validate_open3d_ra_mirror_launch_is_cone.py` (display-free, `run_checks()`):
  binds the REAL `_scene_breaks_rotational_symmetry`, `_launch_pupil_prefers_meridional_fan`,
  `_launch_cone_prefers_flat_fan`, `_sample_ray_count_cone_points` against the RA-mirror rows.
  Asserts the fold is detected **purely** by the OpticalSolidFaces mirror face (the mirror row's
  tilt/desp are all < 1e-9, so the old test would have missed it), the launch revolves a cone with
  off-meridian spokes, a Beam-Splitter face is **not** read as a mirror fold, and an unfolded
  layout (`machine_vision_85mm_azure_datasheet_05x_20x.py`) still keeps the bug-0126 flat fan.
  **PASS.** Standalone, mirroring the sibling AZ85 guards (not a penta phase).
- Sibling guards still **PASS**: `validate_open3d_sequential_cone_is_cone` (0161, the cone
  geometry + the carve-out) and `validate_open3d_ra_mirror_fold_follows_reflection` (0185).
- Non-folded scenes untouched: the new check fires only on a promoted mirror cube; a normal scene
  has `advanced["OpticalSolidFaces"]` absent → `_optical_solid_faces_have_mirror_fold(None)`
  short-circuits to False with negligible overhead.

## Note

In-app eyeball still owed (headless can't drive the live VTK render). The cone revolve sends more
rays through the mesh-mirror cube than the flat fan did; the cube is a coarse solid (fast
intersection), so this is the same accepted cost as a promoted beam-splitter scene (bugs/0161).
NOTE: the rays still do not reach the sensor in this layout — that is the **separate** thin-lens
reversal documented in bugs/0187 ("ray diverges"), not a launch-sampling defect.
