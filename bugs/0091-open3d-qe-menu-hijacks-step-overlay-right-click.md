# 0091 — Open 3D: right-clicking a beam-splitter overlay popped the Quick-Estimation menu instead of Promote / face-assign

## Symptom (user)

> [flag_20260617_234638_107] right click no promotion option.
> [flag_20260617_234533_786] detector is missing before promotion.

After a **full app restart** (so 0089/0090 were loaded), right-clicking the
imported beam-splitter cube still showed no Promote / "Promote and set Partial
Reflecting" / face-assign options. Because the cube can't be promoted, it never
becomes a beam splitter, so it traces sequentially (`use_nonseq: False`) with no
split and therefore no branch detectors ("detector is missing before promotion").

## Root cause

The session debug log had **no `right_click_context` event at all** — only
left-clicks (which resolved `step=optical` on the cube fine). So the right-click
handler `_show_surface_function_context_menu` was returning *before* its log line.
The only such early return is the Quick-Estimation intercept
(`_maybe_show_quick_estimation_role_menu`).

That intercept's plane branch calls `_surface_row_under_cursor`, which returns the
picked actor's **SCENE** row index (from `_actor_row_map`). A physics-preview-ready
STEP overlay is drawn as a transient **live-trace row inserted into the traced
rows**, so the cube's actor lands at **scene row 4** — but `editor.rows[4]` is the
**Image** plane (the editor table has no inserted row). `_maybe_show_quick_
estimation_role_menu` then read `editor.rows[4].surface == "Image"`, popped the QE
role menu, and returned `True` ("break") before logging — so the cube's right-click
showed a menu with no Promote/assign.

## Fix (this commit)

New `_optical_surface_row_for_actor(actor_key)` returns **None** when the picked
actor is a STEP overlay (`_actor_step_map`) or a transient live-trace overlay row
(`_live_trace_step_overlay_label_by_row()`), and otherwise the row index.
`_surface_row_under_cursor` now routes through it, so the Quick-Estimation plane
menu only claims genuine Object/Image surfaces. A right-click on the cube falls
through to `_right_click_pick_context` → (with bugs/0089) the STEP-overlay menu,
restoring Promote / "Promote and set <face>" / Snap / Face Editor.

## Regression gate (display-free)

`validate_open3d_qe_menu_skips_step_overlay.py` (`run_checks()`) drives the real
`_optical_surface_row_for_actor`: a STEP-overlay actor and a live-trace overlay
row → None (QE menu skips them); genuine Image/lens surface actors → their row;
None/unknown → None. Penta **Phase 84**; baseline → 85.

## Notes

- "Detector before promotion" is by design: B1 detectors come from the traced
  split, which exists only once the beam-splitter face is assigned. With the
  right-click menu restored, assign the 45° face (Promote and set Partial
  Reflecting / Face Editor) → the cube splits → a detector on both arms (0090).
- Pre-existing, separate: a *genuine* Object/Image-plane right-click while a
  live-trace row is inserted can still mis-index `editor.rows` (scene≠editor index)
  — the QE plane menu just won't fire there. Not addressed here.
- Confirm in-app (VTK screen picks can't be driven headlessly).

## Status: FIXED (pending in-app confirmation)
