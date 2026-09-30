# 0932 -- the Scene Components Properties / Selected-Element pane in Qt (phase 5f, part 3c)

Under the browser's tree the Tk panel shows four groups:
- **Import** (Optical / Imaging Lens / Camera / LED);
- **Properties** (Name / Kind / File / Pose / Faces for the selection);
- **Selected Element**: ten actions (Carry, Accept, Promote, Delete, Native Rows, Faces, Center
  Axis, Center Normal->Axis, Pick Normal->Axis, Center Surface->Axis), enabled per selection, plus a
  Face-direction choice;
- **STEP Placement**.

The actions dispatch on `_selected_item_id`, so they already worked without Tk. What did not:

- **The pane's content was computed inside `_update_properties` and written straight into Tk**
  labels and buttons. It is now `properties_for(iid)`: the five texts, the action -> enabled map
  and whether the face direction applies. `_update_properties` writes that into Tk as before and
  ends by notifying `inspector.scene_properties_changed`.
  - A canvas pick updates the pane without touching the tree, so the tree's refresh hook (0931)
    alone would miss it.
- **The face direction read a hidden Tk variable.** `_on_face_direction_selected` read the Tk
  combobox's variable. Under the shell that combobox is hidden and Qt never sets it, which is the
  bugs/0929 trap again.
  - `apply_face_direction(direction)` takes the value.
  - The Tk handler passes its variable's value to it, and Qt passes its own.

The rows and actions are class data (`PROPERTY_ROWS`, `SELECTION_ACTIONS`, `FACE_DIRECTIONS`), and
the Qt pane lays them out. `qt/scene_components_dock` now puts the tree over the pane in a
splitter; the tree stays `.widget` for phase 710's guard.

## Measured

On om05a_folded the Qt pane equals the (hidden) Tk pane, both updated by the same
`_update_properties`:

| selection | properties | enabled actions | face direction |
|---|---|---|---|
| scene-row:0 (Object) | equal | none | off |
| overlay:optical | equal | 9 | on |
| overlay:lens | equal | 9 | on |

## Guard

`validate_open3d_qt_5f_properties`, penta phase **711**:
- **P**: the parity above; the overlay case must enable at least 3 actions, so it is not vacuous.
- **F**: choosing "Up" in Qt orients toward "Up" while the hidden Tk variable still reads ''.
- **C**: a canvas pick moves the Qt pane from "Editable table row S0" to "Imported overlay".
- **S**: a clicked tree item is still alive when its own selection signal ends. Measured with
  the fix: [True, True, True]; with the old handler: [False, False, False].

## Two defects the gate found (fixed here)

### A segfault on a tree click (latent since 0931)

A click runs `_selected` → `select_iid` → `select_step_overlay_from_admin`. That calls
`refresh_step_admin_panel` → `refresh` → `scene_components_changed`, which is the dock's
`rebuild()`. `rebuild()` calls `widget.clear()` INSIDE the `itemSelectionChanged` signal, which
deletes the item Qt is still selecting.

- A probe measured all 3 of 3 selections re-entering.
- Whether it crashed depended on reuse of the freed memory. Phase 711 died with exit -11 at
  `setSelected` in about 1 run in 3.
- A user click could do the same.
- Fix: a rebuild requested during `_selected` is deferred with `QTimer.singleShot(0)` until the
  signal returns.

Separately, every Qt guard driver now prints its result with `flush=True` and ends with
`os._exit(0)`. A crash at interpreter teardown can then no longer lose the result line.

### The 3D viewport lost 45 px (phase 707's L)

The tree and pane share a QSplitter, whose minimum height is the SUM of both children's (70 + 70
+ handle = 144). That raised the Scene Components dock's minimum from 86 to 160. With the left
column's docks stacked, the viewport shrank to 377 px, under the guard's 400 px floor.

- Fix: the splitter's minimum height is the tree's alone.
- The viewport is back to 422 px.

The validators that read these methods pass unchanged:
- `step_face_direction`;
- `canvas_pick_enables_buttons`;
- the 3D interaction contract (259 checks);
- `cadquery_readiness`.

`fast_contracts` fails only its known `ui-modular-maintainability` budget, identically with this
change stashed.

**Phase 5f is complete:** the toolbar, the live dock, the constraints / System Selection, the
browser tree and its properties pane.
