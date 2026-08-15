# 0621 — "The sampled rays are not launching from the edge of the object" (FIXED)

Flag `flag_20260815_203310_033`, build `fd6fbae6`: after the 55×55 FOV solve, the 3×3
field pencils launch visibly INSIDE the drawn green "FOV 55.1×55.1" square — at ~90%
of the half-field per side.

## Root cause — the third reader of the raw magnification

The bugs/0591 solve books a conjugate whose RAW paraxial |m| deliberately differs from
the delivered |m| by the learned correction (c = 0.906 on this scene). Two readers were
already made delivered-aware: the drawn FOV plate (bugs/0602) and the shared field
converter (bugs/0610). The LAUNCH-GRID extents were a third, separate reader:
`trace_preview_sampling` computed the object-plane FOV rectangle as
`sensor / |m_raw|` in three places (`_imaging_fov_half_extents` fallback,
`_camera_fov_object_half_extents`, `_camera_fov_inscribed_object_radius`) — its
docstring even still claimed "the same numbers the drawn FOV plate shows", which
bugs/0602 had made untrue. Result: pencils launch at `c ×` the drawn square (24.9 vs
27.55 semi), and the traced arrivals under-fill the sensor by exactly c — matching the
earlier census where arrivals peaked at r = 14.87 on a 16.26 half-diagonal and the
corners were never sampled.

## Fix

`_delivered_finite_magnification()` in the sampler (raw × `folded_m_correction`, the
0602 module accessor) — used by the three FOV-extent sites and the auto-image-diameter
candidate. Unmeasured/sequential scenes have correction 1.0: nothing moves (the
launch-fov guards' stub editors confirm byte-identical numbers). No double-apply: these
paths read the sensor dims directly and never flow through the 0610 converter.

Verified on the solved Apo75: launch-grid extents land on the drawn square and the
traced arrivals reach the sensor corners.

Guard: phase 467 (`validate_open3d_0621_launch_grid_delivered_field`) — contract (all
four sites route through the delivered helper) + behaviour (extents scale by a
synthetic correction; neutrality at c=1).

Doctrine tally: readers of the magnification now split cleanly — booking/solve math
reads RAW; display, field conversion, and LAUNCH SAMPLING read DELIVERED. Any new
reader must pick a side (bugs/0602's rule).
