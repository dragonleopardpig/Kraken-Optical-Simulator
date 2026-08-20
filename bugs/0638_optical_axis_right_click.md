# 0638 — right-click on the Optical Axis: add-element + axis verbs (user request)

User: *"almost all the items can be found under dynamic handling under mouse cursor
(please check). Can also add right click to Optical Axis, add relevant action, for
example: add elements or some kind?"*

## What shipped

The optical axis had NO right-click menu. A right-click on a (pickable) optical-axis actor
now opens `_maybe_show_optical_axis_menu`, wired into the shared right-click dispatch
(`_show_surface_function_context_menu`) before the empty-space fallback. Entries:

- **Add Stock Lens on this axis…** — `open_stock_lens_importer`; on a branched/folded scene
  it passes `path_placement={"branch_path": <this axis>}` so the lens lands on THIS axis
  (plain importer on a single-axis scene).
- **Import Optical CAD/STL Solid…**
- **Add Component to Current Path…**
- **Move Elements Axis → Axis…**

The axis actor is pickable in normal mode (open3d_inspector only `PickableOff`s fully-inert
actors), and `_actor_optical_axis_map` resolves the picked actor → its axis record — the
same mechanism as the bugs/0537 source-glyph menu.

## Contextual-coverage review (the "please check")

Right-click verbs now cover: movable rows (Place/Orient family, bugs/0619), STEP bodies
(move/rotate/center-feature/replace/swap/flip/glue/promote), faces (face→axis in one step),
2+ selection (snap/group), empty space (select/snap/move), source glyphs (seat/select),
measure/thickness/QE-role/opening overlays, the Scene Components tree, and now the optical
axis. Deliberately toolbar/Actions-menu only: scene-level imports/export/clear/galvo/measure
start and the analysis reports.

Verified: guard phase 477 (`validate_open3d_0638_optical_axis_menu`) — the menu builds its
add-element/axis entries, the stock-lens routes onto this axis's branch, a no-axis pick
falls through to the empty-space menu, and the dispatch offers it.
