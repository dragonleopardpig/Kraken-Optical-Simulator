# AZ85 folded layout: beam-splitter direction / missing lens STEP / camera location

Flag bundle: `attachment/recorded_bug_repros/flag_20260630_130926_795/`

Three issues reported against the folded AZURE ELS-85 layout:

1. "Beam Splitter direction is wrong"
2. "Surrogate does not come with LENS STEP"
3. "Camera location is wrong"

## Root cause (old folded layout)

The old folded variant `machine_vision_85mm_azure_datasheet_05x_20x_folded.py`
folded the optical **axis** with a sequential `Mirror` row (`glass="MIRROR"`,
`tilt_x=-45`) so the lens chain re-oriented onto the +Y branch. It deliberately
blanked `lens_step_path` and `camera_step_path` because the CAD overlay aligner
(`layout_polyline_display._cad_mesh_aligned_to_optical_axis`) seats a STEP mesh
along the straight cumulative-thickness +Z axis (`aligned[:, 2] += target_front_z`)
and cannot follow a folded polyline — so the barrel/camera bodies would render
detached on +Z while the optics ran along +Y. That straight-axis overlay is what the
flag saw: lens STEP absent, camera body floating on the wrong axis.

## Resolution

The user rebuilt the fold in-app using a **promoted STEP right-angle mirror solid**
(Edmund 87391) instead of a sequential `Mirror` row, and saved the working layout to
`attachment/machine_vision_AZ85_RA_Mirror.py`. The mirror is now a non-sequential
optical solid whose `S001/F002` face is assigned `function="Mirror"`, so the rays bend
on the physical mirror face — there is only one path the ray can take. Because the fold
is a real CAD body (not an axis re-orientation), the vendor lens barrel STEP and the
camera STEP are kept and placed in the scene with the layout.

Packaged the saved layout as the canonical folded AZ85:

- Added `KrakenOS/common_optical_layouts/machine_vision_AZ85_RA_Mirror.py`
  (title `Machine Vision Az85 Ra Mirror`, in the Machine Vision menu).
- Removed the old `machine_vision_85mm_azure_datasheet_05x_20x_folded.py`,
  its guard, and its docs page (replaced in the menu).
- New standalone guard `validate_machine_vision_azure_85_ra_mirror.py`
  (9 rows, promoted STEP mirror face, EFL=85 mm, lens + camera STEP preloaded).
- New docs `machine_vision_azure_85_ra_mirror.rst` + index entry.

Standalone MV guard, not a penta phase.
