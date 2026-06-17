# 0083 — Open 3D: switching the source to finite spawned extra unwanted optical axes

## Symptom (user)

> [flag_20260617_102331_373] changing to finite, additional unwanted optical axis.

State: a promoted BK7 beam-splitter cube (row 4), non-sequential trace
(`use_nonseq = true`), Show Rays on. `optical_axis_records` had **four** axes:

- `axis:global` — the +Z guide (wanted)
- `axis:ray:1:segment:7` "Optical Axis 2" — the splitter's reflected +Y arm (wanted)
- `axis:ray:22:segment:4` "Optical Axis 3" — a tilted field ray (unwanted)
- `axis:ray:56:segment:4` "Optical Axis 4" — a tilted field ray (unwanted)

## Root cause

The traced-optical-axis builder (`_optical_axis_records_for_3d` →
`_segment_is_genuine_fold`) decided a traced ray segment "earns" its own optical
axis when the segment deviates from the **global +Z axis** by more than
`fold_collinearity_tol = 0.1` (~5.7°). That works for an on-axis source: only a
genuine fold (splitter reflection, mirror, penta) tilts a segment off +Z.

But a **finite / off-axis source launches each field chief ray tilted**. Those
rays transmit straight through the optics, yet their segments sit several degrees
off +Z (here 0.10 and 0.16 transverse ≈ 6°–9°, just over the 0.1 gate). The
splitter event makes each field-ray path a "non-refractive-steering" physical
path, so it reaches the fold gate — and the +Z test mistook the field tilt for a
fold. Two field rays, 15.5° apart (just over the 15° merge cone), each spawned an
unwanted axis. Tighter field angles hid under the gate; this source's field angle
poked over it.

## Fix (this commit)

Measure the fold against **that ray's own launch direction**, not the global +Z
axis. A straight transmit stays collinear with its launch (deviation ~0 → not a
fold); a genuine reflection still deviates ~90°. New helper `_path_launch_axis`
returns the ray's launch unit vector; `_segment_is_genuine_fold(direction,
reference_axis)` projects against it. For the on-axis chief ray (launch == +Z)
this is byte-identical to the old +Z test, so the beam-splitter second axis and
the penta cascade are unchanged — only off-axis-*launched* field rays change, and
they correctly stop spawning axes.

Result for the recording: axes 3 & 4 vanish; `axis:global` + the reflected +Y arm
(axis 2) remain.

## Regression gate (display-free)

`validate_open3d_optical_axis_guides.py` gains two cases:
- `_finite_field_transmit_path` — tilted-launch field ray transmitting straight
  through a splitter → asserts **no** `traced_chief_ray_segment` axis. (Verified
  this segment scores transverse 0.148 vs +Z (old → fold) but 0.000 vs its launch
  (new → cleared), so it fails on the old code and passes on the new.)
- `_off_axis_launch_fold_path` — tilted-launch ray that reflects 90° → asserts the
  traced axis is still kept (guards against over-suppressing real folds on
  off-axis-launched rays).

## Status: FIXED
