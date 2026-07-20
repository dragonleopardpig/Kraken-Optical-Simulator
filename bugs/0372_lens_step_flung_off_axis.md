# 0372 — Imported lens shows nothing in 3D: STEP flung ~243 m off-axis

**Flag:** 20260720_135640_281 (build b8b0a3f8) — "after importing lens from folder, I can see the
right panels with Imaging Lens and surrogate, but nothing shown in 3D scene." (The 0371 fix newly
enabled this Apo-Rodagon folder to import, exposing a pre-existing placement bug.)
**Status:** FIXED 2026-07-20 (guard `validate_open3d_lens_step_centered_on_axis` B3/B4, phase for it).

## Root cause

The surrogate discs render correctly at the origin, but the lens STEP overlay body was placed at
**X ≈ −243,834, Y ≈ +162,988** — ~243 m off-axis. That blew the scene bounds up so the camera
auto-framed to 85,820× parallel scale; the real geometry became sub-pixel and only the huge
optical-axis guide showed.

`_step_primary_cylinder_axis[_point]` (layout_polyline_display) derives the barrel's optical axis by
a **radius-weighted mean over ALL cylindrical faces**. The Apo-Rodagon-D 1x 4/75 STEP has 144
cylinders: **141 real barrel cylinders along X** (the native optical axis, sane radii, near the
body) plus **3 near-planar faces misclassified as cylinders of radius ~77,000 mm** along a tilted
axis. Their radius weight (232,904) buried the barrel's (3,298), so the "axis" came out tilted
~60° with a point millions of mm away; `_cad_mesh_aligned_to_optical_axis` then centred the barrel
on that bogus point → the fling.

## Fix (three layers)

1. **Reject absurd-radius cylinders:** a physical cylinder inside the body cannot exceed its size;
   drop `radius > 1.5 × body_diagonal` (the 77,000 mm faces) before aggregating.
2. **Cluster by collinear axis line, pick the dominant group** (by total radius) instead of averaging
   all cylinders — the barrel's many concentric surfaces win; a lone tilted mount bore can't corrupt
   the result. Each cylinder's axis point is the point on ITS line nearest the body centre (not OCC's
   arbitrary `Axis().Location()`, which some CAD authors far away).
3. **Cache-independent guard in `_cad_mesh_aligned_to_optical_axis`:** the optical-axis centre must
   lie within the body's transverse footprint (1.5× half-extent); otherwise fall back to the bbox
   midpoint. Belt-and-braces for any future bad axis or stale cache. The axis cache filename bumped
   to `.axis.v2.json` so v1 garbage regenerates.

## Verified

Apo-Rodagon: axis → **(1,0,0)** (barrel is X in native frame), point **(21.55, 0, 0)** on the body;
aligned overlay transverse half-extent **27 mm** (front at target Z), not 243 m. All three real lens
fixtures (1072517, 15056, Apo-Rodagon) pass B3/B4; the 0077 asymmetric-mount centring (A) preserved.

## Answering the user's aside

No — you do NOT need to import a camera. The folder import wires only the lens; the empty scene was
this placement bug, not the missing camera. The surrogate optics were present at the origin the whole
time, just sub-pixel at the blown-up zoom.
