# 0119 — Right-click "Snap Picked Face → Optical Axis" rotates the window instead of centering it

## Symptom

Two recorded flags, one action, in sequence:

- `flag_20260623_151043_358` — "I want to center this window to the optical axis."
  The LED enclosure (a camera-housing "window") sits upright at offset `[0, 0, 0]`,
  off to one side of the optical axis. The user hovers a planar front face
  (`hover_step_cell_key: "(None, 'passive', 'F011')"`, outline planar at z=274.4 —
  its normal already along the optical axis z).
- `flag_20260623_151115_363` — "after Snap Picked Face → Optical Axis, it is not what
  I wanted." The box is now **tilted**: `step_overlay_poses.led` shows
  `placement_offset_xyz: [32.64, -28.92, 72.05]` with
  `axis_anchor.source: "feature_normal_axis_snap"`, and the LED bounds went from a
  clean upright box to a skewed `x[-25, 84] y[-88, 36] z[269, 351]`. It was
  **rotated**, not centered.

The user wanted to slide the window sideways so its centre lands on the axis. The
command instead reoriented the whole body.

## Root cause

Not a math bug — a **wrong-tool / menu-gap** problem.

"Snap Picked Face → Optical Axis" is a **normal-align** command. Its editor handler
`snap_step_feature_normal_to_optical_axis` (`scene_placement_commands.py`) computes
`delta_matrix = _rotation_matrix_between_vectors(feature_normal, -axis_direction)`
and **rotates** the STEP so the picked face's normal becomes anti-parallel to the
axis, *then* translates the (rotated) face centre onto the axis. Rotation is the
whole point of that command (it is the beam-splitter-on-LED glue alignment).

A translate-only command already exists — **"Center STEP Surface → Optical Axis"**
(`center_selected_step_surface_to_optical_axis`; its apply
`_apply_step_surface_center_axis_pick` does `delta = target − center;
translate_step_overlay(label, delta)`, no rotation). But it lived **only** in the
top STEP menu and the STEP-admin panel, as a multi-click flow (pick face → click the
dotted optical-axis guide). The **right-click face menu** offered only the
normal-align snap, so a user who right-clicked a face and reached for "the axis one"
got the rotate.

## Fix

Replace the right-click "Snap Picked Face → Optical Axis" item with a one-click,
**translate-only** "Center Picked Face → Optical Axis":

- New editor method `center_step_feature_on_optical_axis(label, feature_center_xyz)`
  (`scene_placement_commands.py`), the translate-only sibling of the normal snap:
  resolve the nearest-axis frame, `placement_delta = target_point − feature_center`,
  `next_offset = current_offset + placement_delta`, set the offset, **no rotation**.
  With no traced rays the nearest-axis target is `(0, 0, z)`, so x/y go to the axis
  and the along-axis z is preserved — exactly "center this window on the axis".
- New right-click handler `_center_step_face_to_optical_axis_from_context`
  (`open3d_face_assignment.py`) delegating to it.
- The menu item now reads "Center Picked Face → Optical Axis"; the dead
  `_snap_step_face_to_optical_axis_from_context` handler is removed.

The normal-align snap is **not** lost: it stays in the top STEP menu
("Snap STEP Surface-Center / Pick-Point Normal → Optical Axis"), which still use the
retained `snap_step_feature_normal_to_optical_axis` editor method.

## Test

`KrakenOS/UI/validate_open3d_center_picked_face_to_axis.py::run_checks`
(display-free; drives the real `ScenePlacementMixin.center_step_feature_on_optical_axis`
against a fake editor):

1. behavioral — an off-axis face centre `(21.4, 0, 274.4)` is moved so the resulting
   placement offset puts the centre on the axis line `(0, 0, 274.4)` (x/y zeroed,
   z preserved), with **no rotation** call;
2. source contract — `center_step_feature_on_optical_axis` does not call
   `_set_step_rotation_deg_tuple` (translate-only);
3. source contract — the right-click menu wires
   `_center_step_face_to_optical_axis_from_context` (which calls
   `center_step_feature_on_optical_axis`), not the removed normal snap.

Penta phase 111 runs this guard.

## Note — in-app eyeball owed

Headless Xvfb cannot drive the embedded-VTK right-click face pick, so the menu
click → center is verified in-app. The guard pins the translate-only math and the
menu wiring.
