# 0723 — split field: the axis guides draw BOTH beams (traced chief rays), no jog; arm B was dead to imaging rays

Step 2 of the 0721/0722 arc (flag `flag_20260906_135342_027`: "unknown 90 degree bending of
optical axis at the big inverted RA mirror"; user's design truth: "Beam A and B … reaching the
big inverted RA mirror are independent, both offset from the center"). Agreed scope: the
optical-axis guide draws both imaging beams at their own offsets, parallel to the lens axis,
with no 0692 jog.

## What the guide showed and why

The multi-fold guide (`_folded_multifold_axis_guide_records`) reconstructs the axis from the
walk-posed row anchors: straight branches, closest-approach feet at the folds. On om05a the
arm's +y approach leg (arm A's field line, z −16…−19) and the seated lens leg (the split line,
z −25) are SKEW by the beam offset; bugs/0692 bridged such a junction with a lateral jog —
right for a vendor-seat error, wrong here: the offset IS the design. That jog was the
"unknown 90° bend".

## Fix 1 — the guides (display follows the physics engine)

* `_multifold_guide_segments(branches, junctions, corners, *, split_field)` (factored out of
  the guide builder, pure): without bands the jog stays (byte-identical); with
  `layout_object_fov_bands` there is no jog and the "Optical Axis" guide starts at the LAST
  skew junction's foot on the seated leg — om05a: the big prism's centre on the split line
  (0, 52.8, −25) → RA mirror 2's corner → down through the sensor.
* `detector_coverage_overlay.split_field_beam_axis_records(bands, trace_fn, image_surface,
  stop_surface, stop_center, stop_axis)`: one traced beam centreline per device-face band.
  Launch at the band centre along its face normal (the sign is not in the record: both are
  traced, the one reaching the image wins, else the NEARER arm by `_first_fold_distance` —
  the distance to the first direction change, because a chain row's air plane crossed inside
  the device body is a vertex too and fooled a first-vertex rule). Then
  `aim_launch_through_stop` steers the launch so the ray passes the aperture stop's CENTRE
  (numeric 2×2 Jacobian, Newton): the face-normal ray of om05a rides 8.8 mm off the lens
  axis and dies on the Ø14.7 stop — the physical beam axis is the face centre's CHIEF ray.
  The record is the full vertex list the trace returns (arm folds, the inverted prism's
  internal reflection, lens, RA2, sensor), `axis:beam:face-a` / `…face-b`, labelled
  "Face A beam axis", pickable like every other guide.
* `Kraken3DInspector._split_field_beam_axis_records`: real `NsTrace` on the live system
  (`energy_probability` 0, restored); on a beam-splitter scene picks the branch that reaches
  the image, else the stop, else the longest; the stop pose is the FIRST `Aperture` row's
  `_runtime_transform_for_row`. Wired into `_optical_axis_records_for_3d` after the fold
  guides.

Measured on om05a (0.39×): face A's chief ray 0 → … → stop centre (210.43, 52.8, −25.00) →
sensor (272.63, −1.76, −28.58); face B's → the same stop centre → (272.63, −1.76, −21.49):
mirror images about the sensor centre z −25.0 to 0.07 mm. No jog records.

## Fix 2 — arm B was dead to imaging rays (found on the way)

The face-B chief ray died on leaving BS cube B. Instrumenting the non-sequential loop: the
+z leg face `S001/F002` of BS cube B carried `OpticalSolidFaceIlluminationBlock` — the 0357
coverage rule (a free physical source panel plane-parallel to a promoted face, ≤ 3 mm off,
centre on the board ⇒ that face is an opaque LED plate ⇒ imaging rays are ABSORBED) had
matched the additive 'Device face B' source: a 50 × 1 mm strip 0.5 mm from that face. So
every imaging-role ray leaving BS cube B toward the centre mirror was killed (the chain's
0696 mirrored twins included); only the source's own illumination-role flood was exempt at
trace time. Arm A had no such source and passed. The two arms' physics differed.

An ADDITIVE source is, by 0680's definition, the imaging chain's own object-side emitter
(the device's second face), never hardware on the optics. `_coverage_illumination_block_face_ids`
now skips `scene_source_spec_is_additive_to_imaging` sources. The 0357 LED-plate case is
unchanged (its validator and 0680's still pass).

## Verified

* validate_open3d_0723 (penta 522): A nearer-arm + first-fold rule; B aimed chief rays through
  the stop, mirror-image landings; C the aimer on a skew stop / never-reached stop; D the
  segments with/without bands (jog kept vs. none; guide starts at the prism centre;
  default byte-identical); E wiring pins; F the additive exemption + 0357 preserved.
* Real scene: both beams reach; 0.37× strips ±3.6 (midpoint 0.008 mm) unchanged; FOV-20 solve
  unchanged; snapshots `verify_0723_off_*.png` (rays off: the two dotted beam axes through the
  arms and the lens-axis guide on the split line).

## Follow-ups

* The beam guides are drawn in the same blue dotted style as the axis; a distinct colour
  per beam would read faster.
* Limiting-case sweep (FOV 20/54) now that arm B traces for imaging rays.
