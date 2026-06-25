# 0150 — Right-click "Re-anchor" always moves the RIGHT (end) endpoint, ignoring which arrowhead was clicked

## Status

FIXED — penta phase **141**, guard `validate_open3d_reanchor_menu_endpoint`. Found
while eyeballing bugs/0149. In-app eyeball still owed (the embedded-VTK right-click +
modal pick can't be driven headless).

## Symptom

There are **two** ways to start a dimension re-anchor and they behave differently:

> *"I use right click pop up menu then select reanchor, it behave differently. I
> point to the Left Arrow, right click, select reanchor — the right arrow will
> reposition itself to the end of the left arrow first, effectively zero length,
> then slide. The left arrow follows. Ctrl-left click works as expected however."*

- **Ctrl-left-click** a dimension arrow → re-anchors the endpoint **nearest the
  cursor** (correct — bugs/0149 verified this path).
- **Right-click → "Re-anchor to a surface/edge…"** → **always re-anchors the RIGHT
  (`end`) endpoint**, no matter which arrowhead you pointed at. Right-clicking the
  LEFT arrow still grabs the RIGHT end; that end then snaps toward the cursor (which
  is sitting on the left arrow) → the dimension collapses to ~zero length, then the
  whole arrow tracks the mouse. Looks broken / "left arrow can't be re-anchored from
  the menu".

## Root cause

The menu command hardcodes the endpoint. `_show_thickness_dimension_menu`
(`KrakenOS/UI/open3d_inspector.py:13639`) wires:

```python
menu.add_command(
    label="Re-anchor to a surface/edge…",
    command=lambda idx=int(row_index): self._begin_dimension_anchor_pick_for_row(idx),
)
```

`_begin_dimension_anchor_pick_for_row(self, row_index, endpoint="end")`
(`open3d_inspector.py:13672`) **defaults `endpoint="end"`**, and the menu never
passes one — so the menu path **always** picks `moving=end`, `fixed=start`.

The Ctrl-click path does **not** have this bug: `_dimension_anchor_state_from_
current_pick` (`open3d_inspector.py:3596–3604`) projects both endpoints to display
space and chooses `endpoint = "start" if d_start <= d_end else "end"` from the
**cursor proximity**. The two entry points disagree because only one consults the
click location.

The "zero length first" artifact is a direct consequence: `_begin_dimension_anchor_
pick_for_row` immediately calls `_apply_dimension_anchor_pick_motion()`
(`open3d_inspector.py:13713`), which slides the **moving** (wrongly: right) endpoint
toward the cursor — and the cursor is on the LEFT arrow — so the right end jumps left
and the span collapses before the user moves the mouse.

## Fix

The menu path now matches the Ctrl-click path: it derives the endpoint from the
right-click position instead of defaulting to `"end"`.

New `Kraken3DInspector._nearer_dimension_endpoint_for_event(event, row_index)`
(`open3d_inspector.py`) maps the right-click to VTK display coords the SAME way
`_thickness_dimension_row_under_cursor` does (`_vtk_interactor.SetEventInformationFlipY`
→ `GetEventPosition`), looks up the row's drag record
(`_thickness_dimension_actor_map` → `_thickness_dimension_drag_map`), projects
`start`/`end` with `_world_to_display_2d`, and returns `"start" if d_start <= d_end
else "end"` — the **same** proximity rule as `_dimension_anchor_state_from_current_pick`,
including the `"start"` default when the cursor or a projection is unavailable.

`_show_thickness_dimension_menu` computes that endpoint at menu-build time and
forwards it:

```python
reanchor_endpoint = self._nearer_dimension_endpoint_for_event(event, int(row_index))
menu.add_command(
    label="Re-anchor to a surface/edge…",
    command=lambda idx=int(row_index), ep=reanchor_endpoint: (
        self._begin_dimension_anchor_pick_for_row(idx, endpoint=ep)
    ),
)
```

`_begin_dimension_anchor_pick_for_row` is unchanged — it already honours the passed
endpoint and feeds the bugs/0149 per-endpoint store, so independent per-endpoint
anchoring + feature tracking come for free.

## Guard

`KrakenOS/UI/validate_open3d_reanchor_menu_endpoint.py` (display-free `run_checks`):
binds the REAL `_nearer_dimension_endpoint_for_event` onto a fake inspector with a
stubbed interactor + projection. **A** a click near the start projection returns
`"start"`; **B** near the end returns `"end"`; **C** an equidistant click ties to
`"start"`; **D** a row with no drag record falls back; **E** an unavailable
projection falls back; **F** an interactor that can't report the cursor falls back;
**G** source contract — `_show_thickness_dimension_menu` derives the endpoint via
`_nearer_dimension_endpoint_for_event` and forwards `endpoint=` (no longer the bare
`self._begin_dimension_anchor_pick_for_row(idx)` form; proven non-vacuous — a revert
trips G). Penta phase **141**; baseline hand-edited.

## Note

Both entry points share the downstream store/draw/persist chain from bugs/0149, so
once the menu forwards the right endpoint, independent per-endpoint anchoring +
feature tracking come for free. This is purely the **entry-point endpoint
selection** disagreeing — no change to the 0149 data model.
