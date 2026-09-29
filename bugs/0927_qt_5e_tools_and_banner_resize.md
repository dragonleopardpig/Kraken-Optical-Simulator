# 0927 -- measure, box select, nav cube and banner in the Qt shell (phase 5e); the banner re-wraps on resize

## Phase 5e: measured

**Static audit.** It covered 353 methods: measure, rubber-band select, the navigation cube
widget, the system HUD, the banner, and the selection model/view. The only Tk-bound calls were:
- 2D-table and dialog code (phases 3/4);
- `_delete_selected_step_event`'s entry-focus guard. That guard is harmless under Qt: keys reach
  the viewport only while the 3D widget has focus.

**Dynamic proof** in a real Qt shell on om05a_folded. Each gesture ran with Qt input, the view
was reset, then the Tk bindings' own sequence ran (VTK motion first, then the dispatched
handler):

| tool | Qt input | dispatched |
|---|---|---|
| nav-cube click | camera turned (away from home) | the same pose |
| measure: arm, click two bodies | 207.684 mm segment | identical p0 / p1 / offset |
| rubber-band box over the middle 60% | rows 1-24 | the same rows |

## Found: the solve banner never re-wrapped on a resize

The bugs/0839 banner wraps to the room actually in the viewport (`banner_wrap_chars`), and
bugs/0841 keeps it off the navigation cube.

But the layout ran only in `_update_solve_refusal_banner`, which is called on a scene refresh
or when the banner toggle changes. So after the window was narrowed from 1500 to 1080 px, the
"FOCUS the image forms ..." banner still spanned x = 412..1175:
- past the 1080 px edge;
- over the cube, which starts at x = 960.

Nothing in either toolkit re-ran the layout on a resize. The Tk code has no `<Configure>` hook
for it either; a probe to show it live in Tk did not reach the text actors, so the Tk gap is by
code reading.

**Fix.** `_attach_vtk_core`, which is shared by both shells, adds a render-window `StartEvent`
observer, `_relayout_banner_on_resize`. It re-runs the banner layout only when the window's size
changed since the last layout AND a banner is showing. This is the same per-render pattern the
orientation marker and nav cube use for their corner viewports, so it works identically under
both toolkits.

## A measurement trap

`vtkTextActor.GetBoundingBox` returns the box RELATIVE to the actor's anchor, not in absolute
display pixels (y from -117 to 0 on a top-anchored text). The guard adds
`GetPositionCoordinate().GetComputedDisplayValue(renderer)`.

## Guard

`validate_open3d_qt_5e_tools`, penta phase **706**:
- **N, M, B**: the three tools above, Qt vs dispatched, and non-vacuous: the camera moved, the
  segment is longer than 0, at least one row selected.
- **T**: every visible viewport text lies inside the window and clear of the cube, at the first
  size and after a Qt resize to 72% width. It failed before the fix: the banner reached x = 1175
  of 1080.
