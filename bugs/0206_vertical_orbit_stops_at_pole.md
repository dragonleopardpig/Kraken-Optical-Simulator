# 0206 — BUG: a vertical scene-drag orbit stops at the pole; can't orbit indefinitely

**Status: RESOLVED. `Kraken3DInspector._rotate_camera_fixed_drag` is rewritten as a true
trackball: the pure `_orbit_camera_pose` Rodrigues-rotates the camera offset AND the view-up
by the SAME increments (azimuth about world +Y, elevation about the screen-right axis), so the
view-up is carried RIGIDLY over the pole. That removes the ±79° clamp added by bugs/0198 — a
sustained vertical drag now orbits indefinitely (through the top, upside-down and back) with NO
discrete view-up swap, hence no flip. Guard `validate_open3d_drag_orbit_no_flip.py` (rewritten to
the new contract) is now wired as penta phase 184. The old `_safe_view_up_for_camera` helper is
deleted (dead after the rewrite).**

## Flag

`attachment/recorded_bug_repros/flag_20260702_152020_279` (issue 2 of the same flag whose issue 1
was the bugs/0205 offset), on the folded AZ85 RA-mirror scene:

> "about the scene orbiting, drag from top to bottom, it will stop somewhere, unable to orbit
> indefinitely in this direction."

## Symptom

A sustained vertical drag tilts the camera up (or down) and then **freezes** a few degrees short
of straight-down/-up. The scene can't be rolled over the top; the drag just stops responding in
that direction.

## Root cause — the bugs/0198 anti-flip clamp

bugs/0198 ("the whole assembly suddenly flips") was caused by `_safe_view_up_for_camera`
DISCRETELY swapping the view-up axis from world **+Y** to **+Z** once the tilt brought the view
direction within ~10° of +Y (past ~80° elevation) — a 90° reorientation rendered in one frame.
The 0198 fix dodged the swap by **clamping the drag elevation to ±79°**, just short of the swap
boundary, so `_safe_view_up_for_camera` always returned +Y and the swap could never fire.

That clamp is exactly what stops the orbit here: below the pole it's smooth, but at ±79° the
vertical drag dead-stops. bugs/0198 traded the flip for a wall. The real defect underneath both
symptoms is the same: the orbit **re-derived** view-up from a fixed world axis every step
(`SetViewUp(_safe_view_up_for_camera(camera))`), which is discontinuous near the pole. Whether you
hit the discontinuity (flip, 0198) or stop before it (wall, 0206), the world-axis re-derivation is
the flaw.

## Fix — a true trackball that carries view-up rigidly

Rewrite `_rotate_camera_fixed_drag` to rotate the whole camera frame as a rigid body instead of
re-picking view-up from world axes. A new pure static helper does the geometry
(`Kraken3DInspector._orbit_camera_pose`, with `_rodrigues_rotate`):

```
offset = position - focal_point;  up = normalize(view_up);  world_up = (0,1,0)
az = radians(-dx * 0.10);   offset, up  <- Rodrigues(·, world_up, az)   # turntable horizontal
view_dir = -offset/|offset|;  right = cross(view_dir, up)               # screen-right axis
el = radians(-1.0 * dy * 0.10);  offset, up  <- Rodrigues(·, right, el)  # elevation, sign -1
return  focal_point + offset,  normalize(up)
```

Both the offset and the view-up are rotated by the SAME two increments, so the camera frame stays
orthonormal:

- **orbits indefinitely** — there is no clamp and no degenerate up. The elevation rotates the up
  vector right over the pole; at the top the up is horizontal (⊥ the now-vertical view_dir), and
  past it the up's y-component goes negative (the camera hangs upside-down). The orbit continues
  smoothly all the way around.
- **no flip** — view-up is never re-derived from a world axis, so it never jumps. The step-to-step
  view-up change equals the small drag increment (~0.8°/step), never a 90° swap.
- **radius preserved** — a rigid rotation can't change `|offset|`.
- **below-pole feel unchanged** — azimuth about world +Y (`-dx·dpp`) and elevation about
  screen-right with **sign −1** (`-dy·dpp`), at DPP = 0.10, reproduce the old VTK
  `Azimuth(-dx·dpp)`/`Elevation(dy·dpp)` path exactly. Measured first-step position residual vs a
  reference `vtkCamera` is 2.6e-13 mm.

Crucially the handler sets the carried up with `camera.SetViewUp(*new_up)` and does **NOT**
`OrthogonalizeViewUp()`. The rigid rotation preserves the up↔view-dir angle, so the stored up never
aligns with the view direction (VTK orthogonalises it afresh at render, giving a continuous
rendered orientation). Orthogonalising the STORED up would instead snap it whenever the incoming up
wasn't already perpendicular — a one-off jump on the first step that reads as a flip. Leaving it
un-orthogonalised keeps the very first step continuous too.

`_safe_view_up_for_camera` is deleted — with the rigid carry there is no world-axis re-pick, and
nothing else referenced it.

## Tradeoff (user-approved)

Going OVER the top **inverts the horizontal sense** — a left-drag now orbits the other way while
the camera is upside-down, exactly as a physical trackball rolls. The user was offered (A) this
true trackball vs (B) keeping a +Y-locked turntable that hard-stops at the pole, and **chose A**.
Below the pole the familiar +Y-up turntable feel is unchanged; the inversion only appears once you
deliberately roll past straight-up/-down.

## Verification (display-free)

`KrakenOS/UI/validate_open3d_drag_orbit_no_flip.py` (rewritten; drives the REAL
`_rotate_camera_fixed_drag` against a standalone `vtkCamera`, no renderer → segfault-safe). From
the bugs/0198 flag's prelude pose it asserts:

1. **orbits indefinitely** — a sustained drag-up reaches **+89.8°** and a drag-down **−89.8°**,
   both PAST the old 79° clamp, and both go OVER the pole (`view_up.y` inverts to **−0.998**);
2. **no flip** — the motion is CONTINUOUS: min step-to-step view-up dot **0.9999**, max step
   change **0.800°** (a flip would be a ~90° jump);
3. **rigid** — the orbit radius is preserved to < 1e-4 mm;
4. **below-pole feel** — a moderate below-pole drag is pose-identical to VTK Azimuth/Elevation
   (position residual **2.6e-13 mm**);
5. a pure **horizontal** drag still orbits in azimuth without tilting or flipping.

Wired as **phase 184** (`phase_184_trackball_orbit_through_pole`) in the comprehensive penta
validator; baseline updated `"184": "pass"`. (The bugs/0198 standalone guard this replaces was
never a penta phase.)

In-app eyeball still owed — headless cannot drive the live VTK interactor, only the pure camera
math it calls.
