# 0308 — Imported camera STEP is reversed (lens mount points the wrong way)

Recording `attachment/recorded_bug_repros/flag_20260715_075742_676/` — *"Imported camera is reversed
in direction."* The BC-OM25M12X2 vendor body (imported via **0307**'s camera folder importer) rendered
back-to-front: its C/M58 **lens mount** (the bore that should face the imaging lens, upstream) pointed
**downstream**, away from the beam, so the sensor plane sat on the wrong face of the body.

## Root cause — a fixed `front_face="max"` in two places
The camera overlay was seated with a hardcoded `front_face="max"` in **both** transform paths:

* the **display** transform `_transformed_imported_camera_step_mesh` (layout_polyline_display.py), and
* the **export/snap** params fed to `_step_alignment_affine` (optical_solid_workflow.py).

`_cad_mesh_aligned_to_optical_axis(front_face=<end>)` seats the *named native-z end* toward the beam.
`"max"` happens to be the mount end for the Allied Vision **hr25MCX** (its bore is at native **max-z**),
so the fixed side looked correct for that one vendor — but **BC-OM25M's mount is at native min-z**, so
`"max"` seated the *closed* end toward the lens and flipped the camera. A fixed side can only ever be
right for half the vendor bodies.

## The fix — read the mount geometry (general, no per-vendor hardcoding)
A lens mount (C / F / M58) is a **circular bore**, so that end's **centre is hollow** — there are no
points near the optical axis there, whereas the opposite (electronics/sensor) end is solid. New method
`_camera_step_mount_front_face(mesh, default=…)` (layout_polyline_display.py) measures, for each native-z
end, the **central fraction** = fraction of points inside a 12 %-span end slab that fall within
`r < 0.25·rmax`. The **emptier** end is the mount and is seated toward the beam. It is deliberately
**conservative**: if the two ends are within 3 % of each other, or the "bore" end is not actually hollow
(> 15 % central), it returns the caller's `default` rather than inventing an orientation.

Both paths now resolve the **same** way (bugs/0300 invariant — the export must use the same transform as
the display):
* the **display** build calls `_camera_step_mount_front_face(mesh, default="max")` directly;
* the **export** params emit `"front_face": "auto"`, and `_step_alignment_affine` resolves `"auto"`
  through the **same** detector — so the STEP export orientation matches what the user sees.

## Verified (display-free)
* Real vendor caches: **BC-OM25M → `"min"`** (central frac 0.000 min vs 0.060 max) and
  **hr25MCX → `"max"`** (0.283 min vs 0.000 max) — the reversed body flips, the one the fixed side got
  right is unchanged.
* Synthetic point-cloud bores: a min-z bore reads `"min"`; reflected in z it reads `"max"` (symmetry —
  not hardcoded); a body solid at both ends and a degenerate cloud both keep the default.
* `KrakenOS/UI/validate_open3d_camera_mount_orientation.py` — **PASS** (14 checks). Penta **phase 270**
  delegates to it; baseline updated (`tools/penta_validator_baseline.json` → `"270": "pass"`).

## Files
- `KrakenOS/UI/services/layout_polyline_display.py` — new `_camera_step_mount_front_face`; the camera
  build resolves `front_face` from it (was a fixed `"max"`).
- `KrakenOS/UI/services/optical_solid_workflow.py` — camera export params emit `"front_face": "auto"`;
  `_step_alignment_affine` resolves `"auto"` via `_camera_step_mount_front_face`.
- `KrakenOS/UI/validate_open3d_camera_mount_orientation.py` — new display-free guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_270_camera_mount_orientation`.
- `tools/penta_validator_baseline.json` — phase 270 baseline.

## Notes / remaining
- **Orientation only.** 0308 makes the mount face the beam; the sensor still sits at the mount face
  because BC-OM25M's flange-to-sensor **optical distance (12 mm)** is *not* in the datasheet text or the
  STEP (it is a figure dimension; the STEP models the ~24 mm mount cavity but not the sensor body). That
  value is recovered by **0309** (an import-time dialog that asks the user for it) — the sibling flag
  `flag_20260715_075815_948` (*"the sensor location is not at the camera physical sensor location … the
  optical distance is 12 mm … Is the PDF extraction able to read this information?"* → **no**).
- In-app eyeball owed (needs a GLX display): Open 3D → import `attachment/Cameras/BC-OM25M` and confirm
  the mount faces the imaging lens.
