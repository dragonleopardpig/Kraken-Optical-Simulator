# 0074 — Open 3D: an off-beam promoted solid's thickness pushes the detector past best focus

## Symptom (user's words)

`attachment/recorded_bug_repros/flag_20260612_202125_747` (layout
`machine_vision_120mm_65M`):

> it did not snap now after promotion, but Object Plane missing, Image plane
> wrong position, one wrong thickness overlay, ray continue tracing pass the
> detector.

The user parked a beam-splitter cube off the beam and promoted it. After the
bugs/0066/0067/0073 fixes it no longer **snaps** onto the axis (the body stays
off to the side — `row_actor_bounds["6"]` is centred on `(48, 41, 295)`). But the
optical chain is now wrong: the rays focus through the lens stack and then
**diverge past the detector** (the optical-axis guide runs to `Z ≈ 1422`, far
past the camera at `Z ≈ 520`), the Image plane is at the wrong Z, the Object disk
is gone, and a stray thickness overlay floats off to the side.

## Root cause — an off-beam solid still occupies axial space

The cube sits at a **moderate** decenter: centre `(48.05, 40.70)`, 50.45 mm
footprint → lateral decenter `≈ 62.97`, transverse half-extent `≈ 25.22`, so its
nearest edge clears the optical axis by **inner edge ≈ 37.75 mm**. The beam radius
(widest clear aperture, bugs/0073) is **23 mm**, so the cube clears the beam by
~15 mm — it is genuinely outside the beam.

But the off-beam classifier required the inner edge to clear the beam by a
**2×** factor (`max(2·r, r+1) = 46`). At `37.75 < 46` the cube fell in the
`23..46` *gray zone*: clear of the beam, yet **not** classified off-beam, so it
was left in the sequential surface chain as an `N-BK7` glass solid.

In the non-sequential trace the on-axis rays **miss** the off-axis cube (no
refraction), and `AxisMove = 0` stops its lateral `desp` from propagating
(`SDT[image].DespX = 0`). The only leak is **axial**: the cube's 50.45 mm
thickness is added to the track, so the Image/detector is shoved from its no-cube
station `Z = 481.08` out to `Z = 531.53`. The lens stack still focuses at ~481, so
best focus now lands ~50 mm **short** of the detector → the rays converge, then
diverge past it (`rays trace past the detector`), the detector reads as
mispositioned, the stray 50 mm dimension is the `wrong thickness overlay`, and the
disturbed chain drops the Object disk.

This is the **unresolved axial half of bugs/0065**. That fix neutralised the
lateral coordinate break ("rays chase the cube") but **deliberately preserved the
solid's thickness** ("so the surface count and axial chain are intact"), so the
parked solid still acted as a real air gap — the "focus short of the detector"
part of the original 0065 report never went away.

## Fix (non-sequential — an off-beam solid is fully inert)

`KrakenOS/UI/services/offbeam_optical_solid.py`:

1. **Relaxed the clearance threshold** `_OFFBEAM_BEAM_CLEARANCE_FACTOR` **2.0 →
   1.25**. The beam never exceeds the widest clear aperture, so a solid whose
   inner edge clears that radius by ~25 % is safely outside the beam. The 2×
   factor was too strict and created the gray zone. (Neutralising an uncoated
   off-beam solid is always safe — it is optically inert anyway; a coated
   splitter that *folds* the beam is on-beam, `inner_edge < r`, never neutralised.)

2. **An off-beam solid is now axially inert.** `neutralized_offbeam_solid_spec`
   zeroes the chain **thickness** as well as the decenter/tilt/glass, so the
   parked solid contributes **nothing** to the Object→Image chain — the detector
   stays exactly where it is with no cube. The 3-D body still draws at its world
   station from the live row + `offbeam_neutralized_body_transform` (bugs/0067),
   so display is unchanged.

3. **A coated off-beam splitter is axially inert too.** bugs/0066 keeps a coated
   splitter in the non-sequential trace (body off-axis), so it is exempt from
   *optical* neutralisation — but a splitter parked off the beam must not push the
   detector either. New `axially_inert_offbeam_solid_spec` zeroes only its chain
   thickness, preserving its coating and decenter. The geometry test was split
   out as `is_offbeam_solid_spec` (ignores coating); `is_offbeam_inert_solid_spec`
   (full neutralisation) is now `is_offbeam_solid_spec AND not coated`.

With the fix the recorded cube (inner edge 37.75) classifies off-beam and the
built Image returns to `Z = 481.08` — byte-for-byte the no-cube track — for both
the uncoated and the coated splitter.

## Test (fails before, passes after)

`KrakenOS/UI/validate_open3d_offbeam_solid_display_only.py`:

* **B4** flipped: the neutralised spec now has **thickness 0** (axially inert),
  diameter + surface kind kept.
* **C3** now compares the off-beam-cube prescription to a **zero-thickness** AIR
  spacer (not a 50 mm one), and new **C3b** asserts the total track equals the
  no-cube baseline (`125.00 == 125.00` on the fixture) — the detector is not
  pushed.
* New **Section E** reproduces the real recording: E0 the cube sits in the old
  `23 < 37.75 < 46` gray zone; E1 it is now off-beam; E2 the uncoated cube is
  axially inert (track == no-cube, thickness 0); E3 a coated splitter is axially
  inert too (track == no-cube, thickness 0) yet keeps `DespX = 48.05` (body
  off-axis). All fail before the fix (cube not neutralised, track pushed +50) and
  pass after.

`KrakenOS/UI/validate_open3d_coated_solid_schema_exempt.py` gained **B2c**: the
off-beam coated splitter is axially inert (built `Thickness = 0`) while keeping
its decenter.

## Integrated

Phase 66 wraps the bugs/0065 guard (`detail["checks"]` now 27, was 22) and Phase
71 the bugs/0066 guard (13, was 12); both record `len(notes)` dynamically, so the
baseline `"66"/"71": "pass"` is unchanged. Phases 66/71/72 stay green; the
other promoted-solid validators (saved-STEP-native, direct-mirror-faces, vendor
prism) are unaffected (the Dove exit-pose, penta-mirror snap and
snap-assignment-sequence failures are pre-existing branch debt — confirmed via
`git stash`).

## Verification note

The build-level fix (detector restored to 481, both coated and uncoated) is
proven by the display-free Sections C/E against the real `_build_system_from_specs`.
The live render of this machine-vision layout SIGSEGVs the offscreen Xvfb llvmpipe
renderer, so the on-screen detector position, the restored Object disk, and the
cleared stray overlay are the user's in-app confirmation.
