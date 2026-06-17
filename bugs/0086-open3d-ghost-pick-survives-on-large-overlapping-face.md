# 0086 — Open 3D: the on-body fallback-pick gate (0085) missed a stale face that partially overlaps the on-axis body

## Symptom (user)

> [flag_20260617_203945_260] the ghost is gone, but the beam splitter snap back
> to optical axis after snap to optical axis and slide out, ray off.
> [flag_20260617_204110_138] after pivot the scene, one ghost shows up.

Bug 0085's fix worked for the first ghost (203945: `hover_outline_bounds: []`).
But after **orbiting the camera**, the gold ghost selection highlight reappeared
(204110: `hover_outline_bounds` y ∈ [16, 66], centre ≈ 41; body on-axis y ∈
[−25, 25]; key `(None, 'passive', 'S002/F004')`).

## Root cause

The 0085 gate (`_step_fallback_hit_on_live_body`) rejected a fallback pick whose
hit lay outside the live rendered body — but it discriminated on the **ray hit
point** (`through_pick.point_world`). The stale metadata face (the cube's left
face at the dragged-off pose) spans y ∈ [16, 66], which **partially overlaps**
the on-axis body (y ∈ [16, 25]). After a camera pivot the ray hit the overlapping
lower strip (y ≈ 20, inside the body bounds + margin), so the gate **passed** —
yet the highlighted outline still extends to y ≈ 66, floating above the body.
The ray hit point is a poor discriminator for a large face that straddles the
body edge.

## Fix (this commit)

Discriminate on the **face centroid** (`surface_center` =
`face["centroid_world"]`), not the ray hit point. The centroid is the
representative location of the highlighted outline — for the stale face it is at
y ≈ 41 (clearly off the on-axis body) → rejected; for a genuine hover over the
body (including a translucent prism's far/internal face) it sits on the body →
kept. `_step_fallback_hit_on_live_body` now prefers `surface_center`, then the
ray hit point, then the feature point, before testing the body bounds.

## Regression gate (display-free)

`validate_open3d_step_fallback_pick_on_live_body.py` gains case **2c**: a stale
face whose ray hit lands in the overlap (y = 20, inside bounds) but whose
centroid is off-body (y = 41) must be **rejected**. This fails on the 0085
hit-point gate and passes on the 0086 centroid gate. Covered by penta Phase 79
(`run_checks()`), baseline unchanged.

## Not fixed here — snap-back + displaced gizmo (flag_20260617_204228_836)

The third snapshot ("auto promoted... gizmo displaced from the body... right
click not showing face editor") is a **different** issue: the body renders
on-axis (snap pose) while the stored placement / rotation gizmo / pick metadata
sit at the dragged-off pose (y ≈ 41) — a pose desync. **It could not be
reproduced headlessly:** after snap → slide → Show-Rays on/off, the transformed
mesh, the live-trace plan, the traced row decenter, AND the displayed body
**all** correctly follow the slide to y = 41 (the axis anchor is cleared by every
supported slide path: `translate_step_overlay` and the step-carry drag). The
overlay is NOT actually promoted (`promoted_solid_rows: []`); the gizmo came from
clicking the body after the snap, and it only floats *because* of the desync.
The desync is most likely a transient refresh-reuse artifact
(`refresh_scene` "reuse previous meshes" path when a live-trace rebuild looks
sparse). Pending a reproducible trigger (see the note to the user) before a fix.

User design decisions captured for that work: a snapped overlay slid off-axis
should **stay where placed** (body + gizmo + rays follow it; no snap-back), and
snapping should **not** leave it selected with a gizmo (promotion stays an
explicit user action).

## Status: FIXED (post-pivot ghost); snap-back/gizmo desync DEFERRED (not reproducible)
