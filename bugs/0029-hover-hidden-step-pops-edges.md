# 0029 — Hovering a hidden Camera/Lens STEP still pops its face-hover edges

**Status:** Fixed (2026-06-08).
**Component:** Open 3D STEP face-hover pick
(`KrakenOS/UI/open3d_inspector.py`, hover path in
`KrakenOS/UI/services/open3d_interaction.py`).
**Reported via:** the in-app bug recorder — two bundles:
`attachment/recorded_bug_repros/flag_20260608_072712_540/` ("Mouse hover the
hidden Camera and Lens STEP area will pop up selected invisible edges.") and
`attachment/recorded_bug_repros/flag_20260608_072800_860/` ("Lens STEP invisible
edges.").

## Symptom

After hiding a camera/lens STEP (bugs 0026/0027), moving the mouse over the area
where the body used to be still popped up the gold face-hover silhouette outline
plus the `… STEP F00x face` tooltip and pick crosshair — the element responded to
hover even though it was invisible.

## Root cause

VTK's prop picker skips invisible actors, so the hidden body never returns from
`self._picker.GetActor()` and `_actor_step_map` yields no label. The hover handler
then falls back to `_step_feature_pick_any_for_display_xy`, which is a
display-mesh / camera-ray feature pick that works from the cached STEP face
geometry **independently of actor visibility**. That fallback (and the per-label
`_step_feature_pick_for_display_xy` it loops over) had no hidden-state check, so a
hidden label still produced a feature pick → gold outline + face tooltip.

## Fix

* **Choke point** — `_step_feature_pick_for_display_xy` returns `None` when
  `is_step_label_hidden(label)`. Every face hover/pick/axis-snap path routes
  through this one wrapper, so no caller can feature-pick a hidden element.
* **Belt-and-suspenders** — `_step_feature_pick_any_for_display_xy` skips hidden
  labels in its candidate loop, so a hidden element is never even considered for
  the "any STEP under the cursor" fallback.

A hidden STEP is therefore inert to face hover/pick (no outline, no tooltip,
no crosshair); unhiding restores it. This matches bug 0027, where a hidden
element is selected for properties only — no highlight, no handles.

## Result

On the measured machine-vision layout, hovering the hidden camera/lens area now
produces **0** hover-outline actors and no face tooltip (was the gold silhouette
+ `CAMERA STEP F004 face` / `LENS STEP F001 face`). Unhiding restores the hover
highlight.

## Tests

`KrakenOS/UI/validate_open3d_scene_browser_hide_delete.py` (harness Phase 35)
gains contracts that `_step_feature_pick_for_display_xy` and
`_step_feature_pick_any_for_display_xy` consult `is_step_label_hidden`, and a
behavioral check that a hidden label yields no feature pick while a visible one
does.
