# 0053 — Open 3D: re-anchorable thickness/distance dimension arrows

## Motivating bug (user's words)

> the object to LED distance is wrongly placed at the LED cables, should be at
> the LED bottom surface. This is a good example of having a new feature:
> Ctrl-click at the Arrow → arrow snaps to the mouse → drag to extend the arrow
> to next wanted surface or edge → click to release → new measured location is
> established.

(`attachment/3D.png`.) On LED import `led_step_object_edge_local_z = None`
(`step_overlay_import.py`), so the object→LED distance anchors at a body
extremum — the cable connectors — until the user runs the **Obj→LED** menu pick.
The user asked to generalize that re-pick into a direct in-canvas gesture for
**any** thickness/distance dimension. Confirmed design: re-anchoring is a
**measurement** annotation (the arrow re-points to the picked surface/edge and
reports that distance) — it never moves an optical surface; the object/LED row
additionally feeds the existing object-edge reference.

## Feature

Ctrl+press on a thickness dimension arrow grabs the endpoint nearer the cursor;
dragging snaps it to whatever surface/body sits under the cursor (live preview +
measured-distance readout); releasing sets the measured location. Ctrl on empty
space still orbits the camera (0049's modifier is preserved) — the re-anchor only
takes over when the Ctrl press lands on a dimension actor (the existing thickness
*value* drag already bailed on Ctrl, and the camera-orbit branch is unchanged for
the no-dimension case).

For the object/LED row the gesture reuses `apply_led_object_edge_pick`
(re-seats the LED body so the picked face sits at the object distance — fixing
the cables→bottom-surface case). For any other row it stores a per-row
measured-endpoint override; the dimension then draws to the picked z in a
distinct magenta "measured = …" arrow while `rows[i].thickness` (the optical
model) is untouched.

## Implementation

- **State / persistence** — `_dimension_anchor_overrides: dict[int, dict]` on the
  editor (`layout_editor.py`), `{row: {"endpoint","ref_z","ref_label"}}`. Saved /
  restored in `layout_settings.py` (the restore runs *last* in
  `_apply_layout_settings`, after the table reset that clears it, and writes via
  `self.editor.` because the settings service only proxies non-underscore attrs).
  Reset on a complete layout load (`layout_table_workbench._reset_complete_layout_runtime_state`).
- **Commit** — `scene_placement_commands.apply_dimension_anchor_override(row,
  endpoint, feature_xyz)`: object/LED start endpoint → `apply_led_object_edge_pick`;
  otherwise store the override (measurement-only). `clear_dimension_anchor_override`
  removes it.
- **Interaction** — `open3d_mouse_bindings` left_press/motion/release gain a
  `_dimension_anchor_drag_state` path (Ctrl+arrow → begin; the re-anchor branch is
  checked *before* the Ctrl-orbit branch in left_motion; committed early in
  left_release since it is a Ctrl gesture). Inspector helpers
  `_dimension_anchor_state_from_current_pick` / `_apply_dimension_anchor_drag_motion`
  (snap via the picker's GetPickPosition + live preview line) /
  `_finish_dimension_anchor_drag`.
- **Drawing** — `open3d_thickness_dimensions.add_overlays` draws a single
  re-anchored measurement arrow (`_emit_reanchored_dimension` /
  `reanchored_endpoints`) in `REANCHOR_DIMENSION_COLOR`, labelled
  "S{i} measured = … mm", instead of the gap-split model-thickness arrow.

## Tests

- `KrakenOS/UI/validate_open3d_dimension_reanchor.py` — display-free:
  `reanchored_endpoints` math; a general-row override stores and leaves
  `rows[i].thickness` unchanged; the object/LED row routes to
  `led_step_object_edge_local_z`; overrides round-trip through settings; a source
  contract that Ctrl-on-empty still orbits (re-anchor is gated before the orbit
  branch).
- Phase 58 in the comprehensive validator — boots the inspector, sets an
  override, refreshes, and asserts a re-anchored measurement arrow is drawn in
  the distinct color and the model thickness is unchanged. Added to the baseline.

## Notes / follow-up

- Snapping is to the picked surface/body point's axial z (robust for the LED
  bottom face and lens surfaces); precise CAD-feature-edge snapping for
  display-only tessellations is the bugs/0052 planar-clustering follow-up.
- Scope guard: re-anchoring is a measurement annotation — it never edits
  `rows[i].thickness` (that stays the plain-drag / inline-edit path).
