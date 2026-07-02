# 0198 — BUG: drag-rotating the 3D scene suddenly flips the whole assembly

**Status: RESOLVED, then SUPERSEDED by bugs/0206. The original fix clamped the drag's
vertical tilt to ±79° so the view-up axis never discretely swaps from world +Y to +Z near
the pole. bugs/0206 later found that clamp itself stops a sustained vertical drag from
orbiting past the pole, and replaced the whole approach with a true trackball
(`_orbit_camera_pose`) that carries view-up rigidly — no swap AND no clamp. The `±79°
clamp` and `_safe_view_up_for_camera` described below NO LONGER EXIST; the guard
`validate_open3d_drag_orbit_no_flip.py` was rewritten to the 0206 through-the-pole contract
(now penta phase 184). This doc is kept for the flip's root-cause history.**

## Flag

`attachment/recorded_bug_repros/flag_20260701_201224_499` (+ full drag recording
`recording_20260701_201300.json`) on the folded AZ85 RA-mirror scene:

> "I drag the scene, the scene rotate until suddenly the whole assembly flips."

## Symptom — measured from the recording, then reproduced headlessly

The recording is a single sustained left-drag (2 press, 379 move, 2 release). Replaying the
per-event camera trajectory:

- The camera orbits smoothly up until, at **event 321**, its elevation reaches ≈ **80.7°**
  (camera y ≈ 1076, focal y ≈ 0) and `view_up.y` snaps **1.00 → 0.00**, staying horizontal
  for the rest of the drag. That 90° up-vector jump *is* the flip.

A headless harness driving the real `_rotate_camera_fixed_drag(0, +8)` against a standalone
`vtkCamera` reproduces it: view-up flips `(0,1,0) → (0,0,1)` at elevation **80.2°**.

## Root cause — the view-up axis discretely swaps near the pole

`_rotate_camera_fixed_drag` keeps a CAD-turntable feel by forcing the view-up to world **+Y**
before/after each Azimuth+Elevation, via `_safe_view_up_for_camera`. That helper keeps +Y only
while it is not near-parallel to the view direction:

- **sticky** gate: keep the current up while `|cos(up, view_dir)| < 0.966` (≥ 15° off), and
- **fresh** gate: when re-picking, accept +Y while `|cos| < 0.985` (≥ ~10° off).

As the drag tilts the camera up, `|cos(+Y, view_dir)| = sin(elevation)`. Past
`sin(elevation) = 0.985` — i.e. **elevation ≳ 80°** — even the fresh gate rejects +Y and falls
through to the next candidate **+Z**. Setting view-up to +Z is a 90° reorientation of the
world, rendered in one frame: the assembly appears to flip. (Below 80° both gates keep re-picking
+Y, so the orbit is smooth; the flip is purely the boundary crossing.)

## Fix — clamp the drag elevation just short of the swap boundary

In `_rotate_camera_fixed_drag`, before applying `camera.Elevation(...)`, compute the camera's
current elevation from `arcsin((pos.y − focal.y)/|pos − focal|)` and clamp the applied delta so
the result stays within **±79°**. Below 80° `_safe_view_up_for_camera` always returns +Y, so the
up-axis never swaps and the flip cannot occur. World +Y at 79° is still a valid, non-degenerate
up (sin = 0.982, not parallel), so Azimuth keeps orbiting normally. An exact top-/bottom-down
view is still available through the Top preset and the navigation cube (which set their own
view-up), so nothing is lost — the drag simply stops tilting a few degrees short of straight down
instead of flipping.

Contained: only the vertical tilt of the interactive left-drag is clamped. Azimuth, pan, zoom,
preset views and the nav-cube are untouched.

## Verification (done)

`KrakenOS/UI/validate_open3d_drag_orbit_no_flip.py` (standalone, display-free — drives the real
method against a `vtkCamera`):

1. a sustained drag-up clamps at elevation 79° with the view-up staying +Y (never flips);
2. a sustained drag-down clamps at −79°, likewise flip-free;
3. below the clamp a normal drag still tilts (~5° for a 50 px drag) without flipping;
4. a pure horizontal drag orbits (azimuth) without leaking into elevation or flipping.

Standalone (NOT a penta phase) — no penta phase drives the interactive camera. In-app eyeball
still owed (headless cannot drive the live VTK interactor).
