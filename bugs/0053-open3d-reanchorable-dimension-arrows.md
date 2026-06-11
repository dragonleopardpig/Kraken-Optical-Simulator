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

Ctrl+**click** on a thickness dimension arrow enters a **modal re-anchor** of the
endpoint nearer the cursor. The user can release Ctrl and the button — the
endpoint then follows the **bare mouse** (no button held). The real magenta arrow
live-updates, the surface/edge under the cursor highlights, and a plain **click**
commits the new measured location and leaves the mode. `Esc` cancels. Ctrl on
empty space still orbits the camera (0049's modifier is preserved) — the modal
re-anchor only starts when the Ctrl click lands on a dimension actor.

> Earlier revision (shipped, then revised on user feedback) used a press-hold-
> drag-release gesture with a bare preview line. See **Revision v2** below.

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
  endpoint, feature_xyz, fixed_z=None)`: object/LED start endpoint →
  `apply_led_object_edge_pick`; otherwise store the override (measurement-only),
  recording `fixed_z` (the un-moved endpoint) so a later value edit knows the
  span. `apply_reanchored_dimension_value(row, value)` **moves** the downstream
  element (see #6 below); `clear_dimension_anchor_override` removes it.
- **Interaction (modal, v2)** — `_dimension_anchor_pick_mode` /
  `_dimension_anchor_pick_state` on the inspector. `open3d_mouse_bindings`:
  Ctrl-click on a dimension → `_begin_dimension_anchor_pick_from_current_pick`;
  the bare mouse (`hover_motion`) and a held Ctrl-drag (`left_motion`) both call
  `_apply_dimension_anchor_pick_motion`; a plain click → `_commit_dimension_anchor_pick`.
  The VTK `_on_mouse_move` early-returns while in pick mode so the two motion
  handlers don't fight. Inspector helpers
  `_dimension_anchor_state_from_current_pick` (nearer endpoint),
  `_apply_dimension_anchor_pick_motion` (snap via GetPickPosition + real-arrow
  preview + snap highlight), `_update_dimension_anchor_preview`,
  `_set_dimension_anchor_snap_highlight`, `_exit_dimension_anchor_pick_mode`.
- **Drawing** — `open3d_thickness_dimensions.add_overlays` draws a single
  re-anchored measurement arrow (`_emit_reanchored_dimension` /
  `reanchored_endpoints`) in `REANCHOR_DIMENSION_COLOR`, labelled
  "S{i} measured = … mm", instead of the gap-split model-thickness arrow.

## Tests

- `KrakenOS/UI/validate_open3d_dimension_reanchor.py` — display-free:
  `reanchored_endpoints` math; a general-row override stores and leaves
  `rows[i].thickness` unchanged (setting the override is measurement-only); the
  object/LED row routes to `led_step_object_edge_local_z`; overrides round-trip
  through settings; the modal source contract (Ctrl-click enters the modal pick,
  bare mouse + held drag both drive the motion, plain click commits, Ctrl-on-empty
  still orbits); and the #6 **move**: editing a re-anchored value edits the single
  upstream gap (`thickness[next_row-1]`) so the span becomes the typed value, leaves
  every other gap unchanged, follows the moved endpoint's `ref_z`, and refuses when
  the downstream end maps to no surface or `fixed_z` is unknown.
- Phase 58 in the comprehensive validator — boots the inspector, sets an override,
  refreshes, asserts a re-anchored measurement arrow is drawn in the distinct color
  and setting the override is model-neutral, then edits the value through the real
  `apply_dimension_value` path and asserts the downstream element moved (its upstream
  gap changed to the typed value, every other gap unchanged, the endpoint followed).
  Added to the baseline.

## Revision v2 — modal re-anchor, live arrow, snap highlight, value-edit, inline editor

The first revision was tested in-app; the user asked for six changes. All are now
implemented:

1. **No-hold modal re-anchor** — Ctrl-click toggles a modal pick instead of a
   press-hold-drag. The endpoint follows the *bare* mouse (driven by the Tk
   `<Motion>` binding `hover_motion` → `_apply_dimension_anchor_pick_motion`, which
   first pushes the cursor into the VTK interactor via `set_event_info` so the
   picker reads the live position). A held Ctrl-drag also drives it (left_motion),
   so it works whether or not the button is down. Modelled on
   `_step_normal_axis_pick_mode`.
2. **The real arrow live-changes** — the preview is now the actual double-headed
   `arrow_mesh` (shaft tube + two cones) offset off-axis exactly like the
   committed overlay, with leader lines and a "measured = …" billboard label, in
   `REANCHOR_DIMENSION_COLOR`. `_update_dimension_anchor_preview` replaced the old
   bare `pv.Line`.
3. **Snap target highlights** — `_set_dimension_anchor_snap_highlight`: a STEP body
   shows its picked-face hover outline (`_step_feature_pick_for_display_xy` +
   `_set_step_hover_outline`); a KrakenOS surface row highlights via
   `_set_row_highlight`.
4. **Plain click commits + ends live** — `_commit_dimension_anchor_pick` refreshes
   the snap at the click point, writes the override, and exits the mode. The
   measured distance is `|Δz|`, i.e. normal to both ends (surfaces are ⊥ the
   optical axis). In modal mode left_press nulls every drag/carry detector and the
   `_*_state_from_current_pick` detectors are gated off, so the commit click never
   selects or carries the surface under it.
5. **Inline value editor no longer vanishes on mouse move** — the embedded VTK
   canvas used to steal focus-follows-mouse focus, firing `<FocusOut>` and closing
   the editor. `edit_dimension` now `grab_set()`s the editor and, on `<FocusOut>`,
   pulls focus back to the entry (`keep_focus_in_window`) rather than committing.
   Commit is Enter / OK only; Esc / window-close cancels.
6. **Editing a re-anchored value moves the *right* element** — editing used to
   write `rows[i].thickness`, which (with the Quick-Estimation conjugate re-solve)
   moved a *different* element (the Imaging Lens instead of the LED↔Object gap).
   `apply_dimension_anchor_override` now records `fixed_z` (the un-moved end), and
   `apply_dimension_value` detects a re-anchor override and routes to
   `apply_reanchored_dimension_value`, which performs the **sequential move**
   below and never runs QE.

**Semantic (revised on user feedback — now move-element):** editing a re-anchored
dimension's value **moves** the *Next* element (the endpoint downstream in
ray-trace order, i.e. larger z) so the Previous→Next span becomes the typed value.
Because `thickness` is a directed gap and element positions are cumulative, the
move adds the delta to the **single gap immediately upstream of that element**
(`thickness[next_row-1]`) and rigidly carries it plus everything downstream;
**every other gap value stays put**. The QE conjugate solve is intentionally
suppressed (running it is what shifted the wrong element before). The edit is
refused — model untouched, a status note shown — when there is no override, when
`fixed_z` is unknown, when the downstream endpoint does not map onto a real
optical surface (within ~2% of track, e.g. re-anchored onto a STEP body face), or
when the move would collapse/invert the chain.

> The first revision shipped this as *measurement-only* (re-point the annotation,
> move nothing); the user then asked for the element to actually move. Confirmed
> rule: move the Next element, keep all other thicknesses unchanged. **The LED↔Object
> dimension is out of scope for this move path** — its object-side endpoint routes
> through `apply_led_object_edge_pick` (object-edge reference) and stores *no*
> general override, so editing its value follows the object-edge/`led_step_object_edge_local_z`
> path, not this sequential move. Wiring a value edit on the LED row to move the LED
> body is a separate follow-up.

## Notes / follow-up

- Snapping is to the picked surface/body point's axial z (robust for the LED
  bottom face and lens surfaces); precise CAD-feature-edge snapping for
  display-only tessellations is the bugs/0052 planar-clustering follow-up.
- Scope guard: *re-anchoring* (the Ctrl-click gesture that re-points where the
  arrow measures) never edits `rows[i].thickness` — it only stores the override.
  *Editing the re-anchored value* is the one path that does move an element, and it
  moves exactly the Next element via its single upstream gap (#6 above); it never
  runs QE and never touches any other gap.
