# 0432 — Axis-to-axis MOVE (relocate a downstream chain onto a new optical axis)

**Flag `flag_20260724_072712_449`** + clarifications: on the AZ85 BS scene (RA mirrors removed, BS reflect
axis `axis:global:split` runs +X from `(0,0,96.6)`), the user wants to **reposition the imaging lens +
camera from the object axis onto the BS reflect axis**. They will ray-trace + thickness-solve afterward,
so distances need not be exact — only the **reorientation + on-axis placement**.

The user proposed (and chose) an **axis-to-axis MOVE** over per-element glue or duplicate:
> *"user can click an Old Axis and move it to the new axis … Axis-to-axis move."* + *"Downstream of the
> branch point"* (the object/source + the fold element that define the axes stay put).

Move (not duplicate) because duplicate would need to copy rows **and** STEP bodies, but the STEP overlays
live in single fixed slots (`lens`/`optical`/`led`/`camera`) — no clean second "lens" body. Move just
repositions existing rows. This is the **manual, explicit counterpart of the BS Phase-2 auto-fold**;
designating the source + target axes sidesteps the circular-dependency + row-order problems that blocked
the auto version (bugs/0431).

## Command — `move_axis_downstream_to_axis(old_axis_record, new_axis_record)`

(`scene_placement_commands.py`) For each row whose world centre lies on the **OLD** axis line **and past
the NEW axis's branch point** (`new_axis.points[0]` — where the reflect axis leaves the splitter):

```
R          = rotation_matrix_aligning_vectors(old_dir, new_dir)      # e.g. +Z -> +X
new_centre = branch_point + R @ (centre − branch_point)              # rigid about the branch
desp       = new_centre − (0,0,z_i)   ;  tilt = kraken_tilts(R @ current_R)  ;  AxisMove = 1
```

Distances are preserved (the internal axial spacing becomes offsets along the new axis); the user
ray-traces + thickness-solves to finalise. The **object/source** and any element **before** the branch,
plus **off-axis free-placed** solids (perpendicular distance > tol), are left untouched.

## Verification (`bugs/probe_0432_axis_to_axis_move.py`, headless)

On AZ85, old = `axis:global` (+Z), new = `axis:global:split` (+X @ z=96.6):
- moved rows `[S3,S4,S5,S6,S7,S9]` = Front datum, Blackbox 1, Aperture, Blackbox 2, Rear datum, Image
  (the imaging lens + camera) — each new centre on **+X at z=96.6**, optical-axis dir → **exactly +X**,
  internal spacing preserved (x = 34.0, 51.7, 61.5, 71.4, 89.0 …).
- **stayed:** the Object (S0), the upstream mirror surfaces (S1/S2, before the branch), and the off-axis
  free-placed mirror (S8, x≈236). Object never in the moved set.

PASS: moved rows on the +X reflect axis, reoriented +Z→+X, object + upstream untouched.

## UI (two-axis pick) — SHIPPED

**"Move Elements to Optical Axis"** (Place menu) → `start_axis_to_axis_move` arms a two-axis pick →
click the **OLD** axis (stored) → click the **NEW** axis → `_apply_axis_to_axis_move_pick` calls
`move_axis_downstream_to_axis(old, new)`. Reuses the existing optical-axis pick dispatch
(`_actor_optical_axis_map` / `_optical_axis_info_near_display_xy`; the clicked `axis_info` already carries
the axis `points`). STEP bodies follow their surrogate datums. Import + parse verified; core probe still PASS
after wiring.

## Still owed

In-app eyeball of the folded relocation (VTK, headless-untestable): on the AZ85 BS scene, **Move Elements to
Optical Axis → click the object axis → click the BS reflect axis** → the imaging lens + camera should swing
onto the +X reflect leg (object/BS stay); then ray-trace + thickness-solve. Duplicate (both BS legs
populated) is a deferred extension only if needed.

## Files

- `KrakenOS/UI/services/scene_placement_commands.py` — `move_axis_downstream_to_axis` + `_axis_record_endpoints`.
- `KrakenOS/UI/open3d_inspector.py` — `start_axis_to_axis_move` + `_apply_axis_to_axis_move_pick`.
- `KrakenOS/UI/services/open3d_interaction.py` — two-axis pick dispatch branch.
- `KrakenOS/UI/panels/open3d_top_controls.py` — "Move Elements to Optical Axis" menu.
- `bugs/probe_0432_axis_to_axis_move.py` — headless verification.
