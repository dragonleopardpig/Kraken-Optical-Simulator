# 0061 — Open 3D: "Show clipped rays" toggle, synced both ways with 2D

## Reported (recorder bundle `flag_20260611_150118_648`)

> after enabling and disabling Miss ray, the miss ray still show up.

and, in follow-up:

> I also noticed the 3D display "clipped rays" by default, and there is no
> toggle in 3D. It should follow the 2D setting anyway (and vice versa since
> they should sync).

The recorded scene is a machine-vision LED → lens → camera layout: rays fan out
from the LED, and a wide spread of them misses the lens entirely and escapes the
system. Those stray rays render in 3D no matter what the user does with the
"Miss" overlay toggle.

## Root cause

Two independent display gates, easy to conflate:

- **Ray LINES** are filtered by the editor's `show_clipped_rays_var` in
  `ThreeDSceneToolsMixin._iter_3d_scene_ray_records` (three_d_scene_tools.py:1876).
  When OFF it hides `escaped` rays that were *not* deliberately folded
  (`ray_path_visible_without_clipping_from_events`, scene_geometry.py:540) — i.e.
  the LED fan that vignettes past the optics. Beam-splitter "second path"
  branches are folded escapes and stay visible (bugs/0018), and the bug-0022
  fallback keeps the trace from blanking when *every* ray would be hidden.
- **Diagnostic markers** — terminal-endpoint disks and missed-detector
  crosshairs — are gated by the inspector's `show_terminal_diagnostics_var`,
  which is the "Miss" checkbutton in the 3D Overlays menu.

So the "Miss" toggle only ever added/removed the crosshairs + endpoint disks; it
never touched the ray lines. And the 3D inspector had **no** control bound to
`show_clipped_rays_var` at all — even though the 3D ray filter already reads it.
The 2D editor's "Show clipped rays" checkbox flips that var (default True), but
with no 3D mirror the stray rays were always drawn in 3D and the user had no way
to hide them there.

This is the same shape as bugs/0059 (3D ray count): the underlying shared `tk`
var and the 3D filter already existed; only the 3D UI control + a refresh hook
were missing.

## Fix

`show_clipped_rays_var` lives on `KrakenLayoutEditor` (layout_editor.py:2600) and
is the *one* var the 2D checkbox and the 3D ray filter both read. Surface it in
3D bound to that same object, so the toggle is bidirectional by construction.

- `KrakenOS/UI/panels/open3d_top_controls.py` (`build_view_toolbar`) — add a
  **Clipped** `MenuCheckbutton` to the Overlays menu (next to **Miss**), its
  `variable` = `inspector._editor_var("show_clipped_rays_var")` (the editor's own
  `tk.BooleanVar`, via the live-controls panel's `editor_var`), command =
  `inspector._on_clipped_rays_changed`.
- `KrakenOS/UI/open3d_inspector.py` — new `_on_clipped_rays_changed`
  (open3d_inspector.py, next to `_on_scene_visibility_changed`): marks the 2D
  plot pending (`editor._mark_plot_update_pending()`) so the main window redraws
  to match, then calls `_on_scene_visibility_changed()` to refresh the 3D scene
  and apply the filter immediately.

Because the 3D widget binds the *same* `tk.BooleanVar` as the 2D checkbox,
flipping it in either view updates the other's control state; the per-view
redraw hooks (2D `_mark_plot_update_pending`, 3D `refresh_from_editor`) then
repaint each side. No new state, no change to the filter semantics — the "Miss"
terminal-diagnostics toggle is left exactly as-is (a separate, legitimate
overlay).

## Tests

`KrakenOS/UI/validate_open3d_clipped_rays_sync.py` (new, display-free):
- **A** — the Overlays menu wires a `"Clipped"` `MenuCheckbutton` to
  `_editor_var("show_clipped_rays_var")` with command `_on_clipped_rays_changed`.
- **B** — the inspector defines `_on_clipped_rays_changed` and its body both
  marks the 2D plot pending and refreshes the 3D scene.
- **C** — the 2D trace-display panel still binds `show_clipped_rays_var`.
- **D** — calling `_on_clipped_rays_changed` on a stub fires
  `editor._mark_plot_update_pending` and the scene refresh exactly once each.
- **E** — `Open3DLiveControlsPanel.editor_var("show_clipped_rays_var")` returns
  the *identical* object the editor holds (proves one shared var → real
  bidirectional sync).
- **F** — engine: a snapshot editor + five synthetic `RayPath3D` records (one per
  terminal class). With the var ON the 3D filter renders all five; with it OFF it
  drops *only* the escaped-non-folded stray (index 0) while keeping the folded
  escape, the detector miss, the detector hit, and the aperture stop. Real
  default layouts don't produce escaped-non-folded rays (their escapes are all
  folded beam-splitter branches), so synthetic paths exercise the gate honestly.

The substantive visual effect (which stray rays draw) is asserted on the rendered
ray records in F; the change exposes an existing filter via a new menu item +
refresh hook, so no new VTK render path is introduced.

## Penta phase

**Phase 63** — `phase_63_open3d_clipped_rays_sync` wraps the guard's `run_checks`
(display-free, runs everywhere). Baseline regenerated with phase 63 = pass
(64 phases, 0–63).
