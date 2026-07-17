# bugs/0333 — CA "snap to optical axis" must center AND normal, and prompt for the intended axis

**Issue 2 of the two-issue request:** *"After highlighting the CA edge, right
click snap to optical Axis option: the CA should be centered to the optical axis
and Normal to it, just now I tried, it is not. Also, since we might have multiple
Axis now, after right click selection, prompt user to click on the intended
optical axis."*

Two defects, one on each half of the request.

## Issue 2a (BUG) — the old snap was translate-only

The existing right-click "Center Clear Aperture -> Optical Axis" called
`center_clear_aperture_on_optical_axis`, which **translated** the opening centre
to a hard-coded global `x = 0 / y = 0` axis and **never rotated** the opening
normal. A tilted or off-axis opening stayed tilted and off-axis — the user saw it
move sideways but not square up. That is exactly "it is centered... it is not
[normal]".

### Fix 2a — reuse the rotate+translate engine

`snap_step_feature_normal_to_optical_axis(label, feature_center, feature_normal,
*, axis_frame)` (`scene_placement_commands.py`) already does **both**: it rotates
the body so `feature_normal → −axis_direction` **and** translates so
`feature_center → target_point`, and it accepts an arbitrary `axis_frame`. The new
CA path routes through it (see the state machine below), so one action squares the
opening to the axis *and* centres it.

## Issue 2b (FEATURE) — prompt for the intended axis when there are several

Beam-splitter / folded scenes now carry **multiple** optical axes. The old
translate-only path silently assumed the global axis. The fix routes the CA snap
through the existing **axis-pick state machine** so the user is prompted to click
the intended dotted Optical Axis guide, then the snap targets *that* axis's frame.

### Fix 2b — a new `feature_center` anchor mode on the axis-pick machine

`start_step_normal_axis_pick(label, *, anchor_mode="body_center",
feature_center=None, feature_normal=None)` gains a `"feature_center"` mode
(`open3d_inspector.py`). Unlike the other modes it needs **no face selection** —
it validates the supplied centre + normal are finite, stashes them
(`_step_normal_axis_feature_center` / `_normal` / `_label`), skips
`_step_feature_action_selection`, and arms the same `_step_normal_axis_pick_mode`
click machine. The prompt reads *"click the intended dotted Optical Axis guide."*

The click dispatch (`open3d_interaction.py`) already routes
`_step_normal_axis_pick_mode` → `_apply_step_normal_axis_pick`. A new dispatch
branch there delegates the `feature_center` mode to
`_apply_step_feature_center_axis_pick(axis_info)`, which:
- reads the stashed centre / normal / label (validates finite),
- resolves the clicked axis frame `axis_frame =
  self._optical_axis_frame_from_pick(axis_info, self._picker)`,
- calls `self.editor.snap_step_feature_normal_to_optical_axis(label, center,
  normal, axis_frame=axis_frame)` (Fix 2a),
- runs the full axis-pick cleanup tail (clears the pick modes + stashed fields,
  `_clear_selected_step_feature_state`, restores rays, re-highlights the chosen
  axis, drops the rotation handle) and reports
  *"…clear aperture centred + normal on {axis} (error … deg)."*

## The right-click menu quirk — it must use the OPENING geometry, not the hole-behind

The menu builder re-runs `_step_feature_pick_for_display_xy` to know what the
cursor is over. For an opening this returns the opening feature with
`through_pick = None`; the old menu code then fell to a raw ray pick that passes
**through** the see-through hole and lands on a recessed face *behind* it — so a
naive "snap this face" would snap the wrong geometry.

Fix: opening hover builders now stamp `"opening": True`
(`_clear_aperture_opening_edge_feature` + `_opening_loop_hover_feature` in
`open3d_inspector.py`). The menu (`open3d_face_assignment.py`) detects that marker
(`opening_feature = feature_pick if … feature_pick.get("opening") else None`),
extracts the opening's **own** centroid (`surface_center`) and normal
(`feature[2]`), and — only when both are finite — adds
**"Snap Clear Aperture -> Optical Axis (center + normal)"**, wired to
`_snap_clear_aperture_to_optical_axis_from_context(label, center, normal)`, which
arms `start_step_normal_axis_pick(..., anchor_mode="feature_center", …)`.

## Guard & regression

`KrakenOS/UI/validate_open3d_led_ca_axis_snap.py` (penta **Phase 292**),
display-free:
- **Section 2:** arming `feature_center` mode stores the geometry and prompts with
  *"intended … optical axis"*; a non-finite centre/normal does **not** arm.
- **Section 3a:** the dispatch delegates `feature_center` mode to
  `_apply_step_feature_center_axis_pick`.
- **Section 3b:** apply calls `snap_step_feature_normal_to_optical_axis` with the
  stored centre / normal / clicked frame and clears the mode.
- **Section 3c (source contract):** the path uses
  `snap_step_feature_normal_to_optical_axis`, **not** the translate-only
  `center_clear_aperture_on_optical_axis`; both opening builders mark
  `"opening": True`; the menu wires `_snap_clear_aperture_to_optical_axis_from_context`
  behind `feature_pick.get("opening")`; the handler arms
  `anchor_mode="feature_center"`.

## Files touched
- `KrakenOS/UI/open3d_inspector.py` — `feature_center` anchor mode +
  `_apply_step_feature_center_axis_pick` + dispatch branch + stashed state fields
  + `"opening": True` markers.
- `KrakenOS/UI/services/open3d_face_assignment.py` — opening detection in the
  right-click menu + the "Snap Clear Aperture -> Optical Axis (center + normal)"
  item + `_snap_clear_aperture_to_optical_axis_from_context` handler.
- `KrakenOS/UI/validate_open3d_led_ca_axis_snap.py` — new guard (Sections 2–3).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 292.
- `tools/penta_validator_baseline.json` — Phase 292 = pass.
