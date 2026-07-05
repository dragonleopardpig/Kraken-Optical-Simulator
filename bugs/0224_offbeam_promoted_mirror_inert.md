# 0224 — promoting an RA mirror parked OUTSIDE the beam path shifted the existing optics

**Status: FIXED. A promoted full-mirror the folded beam never reaches is now optically INERT:
promoting it moves nothing — every existing row seat, the detector, the axis segments and the
imaging cone stay exactly where they were (0.000 mm), while the parked prism itself stays pinned at
its drop pose. A mirror only folds the beam if the beam actually hits it. In-app confirm owed.**

## The flag

`flag_20260705_101311_092`: "random placement of an imported RA mirror, promoted, but seems random
placement outside the beam path with promotion affect the existing placement of optical component.
Should be another type of bug." The recording shows a third promoted RA prism parked at world
(101.9, 97.4, 209.9) — nowhere near the folded legs (y = 0, z = 71.9) — yet `axis:global:reflected:1`
bends diagonally to (101.9, 44.3, 71.9) (x exactly the parked prism's) and the downstream chain
re-seats. Headless reproduction: the Image row flew **142 mm** and the detector **300+ mm**.

## Root cause

Three layers composed the parked mirror into the fold chain, none checking the beam reaches it:

1. **Pose-override walk** (`nonseq_output_ports.build_optical_solid_output_port_pose_overrides`):
   bugs/0213 made a free-placed solid with an authored Mirror face "a REAL second fold — the
   downstream detector follows onto the reflected leg". `_reflected_frame_from_interaction_face`
   reflected the running frame about the mirror's **infinite plane** wherever it sat, so the
   Image/detector swept onto a fold the beam never makes. (And even with the reflect gated, the
   walk would re-source the frame from the parked cube's *inferred straight-through output face* —
   the 0084 axial preference — sweeping followers onto the parked body instead.)
2. **Display fold planes** (`folded_sequential_fold.free_placed_mirror_world_planes`): enumerated
   every free-placed faced mirror unconditionally — the display ray bend and the reflected-axis
   segments folded about the parked prism (the recording's diagonal axis).
3. **Flat-plate equivalents** (`paraxial_tools._folded_optical_solid_straight_equivalent_rows` +
   `_paraxial_reference_rows_for_layout`): flattened the parked mirror into a plate whose substrate
   thickness shifted the traced stations/waist ~25–90 mm (detector chased the shifted waist via the
   0217 reconcile even after the seats were fixed).

The 0065 off-beam neutralisation intentionally exempts *coated* solids (a folding mirror is
legitimately off the **straight** axis), so it never caught this: "off-beam" for a mirror must be
measured against the **folded** path.

## The fix — a beam-hit gate in each layer

- **`_reflected_frame_from_interaction_face`** folds only when the beam LINE crosses the face's
  transverse extent: `|hit − centroid| ≤ √area + 2 mm` (√area comfortably covers the rectangular
  hypotenuse half-diagonal; the parked prism misses by ~165 mm, genuine folds by ~2 mm). The test is
  deliberately **sign-agnostic in the plane distance**: the walk's `frame_origin` is a sequential
  STATION marker that legitimately sits *past* a genuine fold face (the AZ85 second mirror reads
  `distance = −93.9` — exactly the `pre_hit_run` bookkeeping). **A forward-distance test kills the
  real fold** — it did, during development, until the guards caught it; hence guard check (A).
- **Follower inert-skip** (pose walk): a free-placed full-mirror whose reflect is gated off (and
  with no explicit user-authored output port) is skipped entirely — pinned at its drop pose,
  contributing no fold and no frame re-sourcing; the running frame passes it untouched.
- **`offbeam_free_placed_mirror_row_indices`** (`folded_sequential_fold`): a vertex-chain walk —
  compose the folded legs through the promoted-mirror vertices in station order; a mirror whose
  centre misses the running leg's line (beyond its own footprint radius) is off-beam. Consumed by
  `free_placed_mirror_world_planes` (display bend + axis segments drop it) and by
  `_offbeam_promoted_mirror_rows` in `paraxial_tools`, which flattens the parked row to a
  **zero-thickness AIR** surface in both the straight-equivalent and the paraxial reference —
  matching the pose walk's "contributes nothing". Conservative: scenes with a plain sequential
  `Mirror` row mark nothing off-beam (today's behaviour).

## Verification

`validate_open3d_offbeam_promoted_mirror_inert` (5/5, penta **phase 200**): (A) the genuine
two-mirror fold still lands the detector at (181.37, 0, −13.55) — the gate must never kill a real
fold; (B) the parked promote moves no row seat and no detector (0.0000 mm), the parked row stays
pinned, and the on-detector waist RMS is unchanged (0.00066 mm both); (C) the classification marks
exactly the parked row off-beam and the display planes drop it; (D) wiring. Full folded sweep green
(0215–0222 guards incl. axis segments, working/image distance, external reflection, camera track,
carryover) plus splitter/promote guards (branch detectors, moved-splitter focus, object plane,
first-order reference, overlay toggle, fov solve).

## Known residuals (documented, not fixed here)

- ~300 **field-ray hard-stop endpoints** shift laterally ≤8.5 mm at the truncation plane after the
  parked promote (the raw sequential chain still carries the parked row's 25 mm in launch aiming).
  The imaging cone and every seat are identical; display-only, minor.
- A parked mirror whose *inferred* output is **not** codirectional (a rotated cube) could still
  re-source the primary branch's frame via the 0022-adjacent inferred-output path — the flagged
  case (tilt 0) is covered; noted as an edge.
