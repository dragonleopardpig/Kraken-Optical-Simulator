# 0063 — Open 3D: a direct 3D-canvas pick must enable the "Selected Element" buttons like the browser does

## Reported

> when I click the STEP element in the right panel browser, the "Selected
> Element" buttons enabled. However, direct clicking on the element in the 3D
> canvas, those buttons remains grayed out.

Two ways to select an imported STEP solid (or any drawn scene row) in the Open 3D
inspector:

- **Right-panel browser** — clicking a tree row enables the *Selected Element*
  action buttons (Carry / Accept / Promote / Native Rows / Delete / Faces /
  Center Axis / Center Normal→Axis / Pick Normal Axis / Center Surface→Axis).
- **Direct 3D-canvas pick** — clicking the body in the 3D view *visually*
  selects it (rotation gizmo + pink highlight) but leaves all those buttons
  **grayed out**.

## Root cause

The button-enable logic lives in `Open3DStepAdminPanel._update_properties(iid)`
(`panels/open3d_step_admin.py`). It derives the enable state purely from the
**browser tree selection IID** (`overlay:<label>` / `row:<n>` / `scene-row:<n>` /
`element:<a>-<b>`). Nothing reads the editor's *picked* state.

The two selection entry points diverge at exactly that point:

- **Browser path (works).** `_on_tree_select` sets
  `self._selected_item_id = iid`, dispatches to the matching
  `inspector.select_*_from_admin(...)` (which applies the editor selection +
  gizmo and calls `refresh_step_admin_panel()`), then calls
  `_update_properties(iid)`. The buttons light because `_update_properties` sees
  a real `overlay:`/`row:`/`scene-row:` IID.
- **Canvas path (broken).** `services/open3d_interaction.py`
  `_on_left_button_press` does the STEP pick via
  `editor.select_step_component(step_label)` + `show_step_rotation_handler(...)`
  (sets `editor._selected_step_label`, shows the gizmo) and the row pick via
  `editor._select_table_row(row_index)` — but **never touches the admin panel**:
  no `refresh_step_admin_panel()`, no `_selected_item_id`. So the panel's
  `_selected_item_id` stays empty and `_update_properties("")` disables every
  button.

`refresh()`'s restore logic alone can't bridge it: it only *restores* a
previously-selected browser IID (gated on `editor._selected_step_label`), it
doesn't *select* a freshly canvas-picked element that was never in the tree
selection.

## Fix (sync the canvas pick into the browser)

The canvas pick already applied the editor/inspector selection + gizmo; it just
needs to mirror that selection into the admin panel so `_update_properties` sees
a real IID.

- **`Open3DStepAdminPanel.select_from_canvas(iid)`** (new) — sets
  `_selected_item_id = iid`, selects the matching tree row (under the
  `_refreshing` guard so it doesn't re-dispatch `<<TreeviewSelect>>`; the
  deferred event hits the `iid == _selected_item_id` early-return), and calls
  `_update_properties(iid)`. If the IID isn't a browser row, the tree selection
  is cleared but `_update_properties(iid)` still gates the buttons correctly
  (button state is IID-derived, independent of the tree).
- **`Kraken3DInspector.sync_step_admin_canvas_selection(iid)`** (new) — thin
  wrapper that forwards to `panel.select_from_canvas(iid)` (no-op when the panel
  isn't built).
- **`Kraken3DInspector._open3d_browser_iid_for_table_row(row_index)`** (new) —
  maps a canvas-picked editable-table row to its browser IID: a promoted STEP
  optical solid → `row:<n>`, every other drawn row (incl. element-group
  children) → `scene-row:<n>`, matching exactly how `refresh()` builds the leaf
  rows.
- **`_on_left_button_press`** — the STEP pick now calls
  `sync_step_admin_canvas_selection(f"overlay:{label}")` after
  `show_step_rotation_handler`; the row pick calls it with
  `_open3d_browser_iid_for_table_row(row_index)` after `_select_table_row`.

Because both the browser click and the canvas pick now land on the *same* IID,
they light the *same* buttons.

### Supporting refactor (single source of truth)

`_update_properties` previously computed its four gating booleans
(`overlay_selected`, `promoted_row_selected`, `file_backed_row_selected`,
`centerable_row_selected`) inline. Extracted two pure helpers so the gating is
testable display-free and shared:

- **`_selection_flags_for_iid(iid)`** → the four booleans from IID + editor
  state.
- **`_compute_selection_button_states(flags)`** (static) → the per-button
  enable map (`carry/accept/promote/native` = overlay; `delete` = overlay or
  promoted; `faces` = promoted or file-backed; `center` = overlay or promoted or
  centerable; `normal/pick_normal/surface_center` = overlay).

`_update_properties` now consumes both; the displayed property strings are
unchanged. Its property-var writes were hardened to `.get()` (matching the
already-guarded button loop) so the method runs headless without a built Tk
panel.

## Tests

- **`KrakenOS/UI/validate_open3d_canvas_pick_enables_buttons.py`** (new,
  display-free) — Phase 65:
  - **Source contracts:** `_on_left_button_press` syncs both the STEP-overlay
    pick and the row pick into the admin panel; the inspector's sync method
    forwards to `panel.select_from_canvas`; `select_from_canvas` sets
    `_selected_item_id` and calls `_update_properties`.
  - **Behavior (fake editor/inspector, no display):** the button-state map is
    correct per selection kind; `_selection_flags_for_iid` derives overlay /
    promoted-row / file-backed / centerable correctly; `select_from_canvas`
    sets `_selected_item_id` and the resulting button states **match** what the
    browser path produces for the same IID (parity) — and an empty selection
    disables every button (the reported "grayed out" state), proving the fix
    flips it.

## Penta phase

**Phase 65** — `phase_65_open3d_canvas_pick_enables_buttons` wraps the new
guard's `run_checks` (display-free, runs everywhere). Baseline regenerated with
phase 65 = pass (66 phases, 0–65).
