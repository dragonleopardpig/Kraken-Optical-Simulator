# 0928 -- the 3D inspector's toolbar as one catalogue, in both shells (phase 5f, part 1)

Phase 5f is three Tk panels built inside the inspector's own Tk window:
- the Scene Components tree (`panels/open3d_step_admin.py`, 1 639 lines);
- the top controls (`open3d_top_controls.py`, 374);
- the live controls (`open3d_live_controls.py`, 559).

Under the Qt shell that window is withdrawn, so none of them could be reached from Qt.

This part does the top controls, the View / Scene / Carry rows: 90 controls in all.
- **View**: Refresh, Snapshot, Save, the Iso-up axis, Show/Pick rays, the 17-check Overlays menu,
  Done 2D, Close, and the bug recorder.
- **Scene**: the CAD/target, Place and Orient menus (with the Import STEP cascade), the axis and
  normal choices, and Measure.
- **Carry**: whole-body handles, the rotation step, Snap mm, and placement handles.

## The controls are data

`KrakenOS/UI/open3d_toolbar.py`, following bugs/0900, holds one record per control:
- `Command`, `Button`, `Toggle`, `Check`, `Choice`, `Entry`, `Radio`, `Menu` (with cascades and
  separators), `Text`;
- each names a model target as `"inspector.<attr>"` or `"editor.<attr>"`, resolved when it runs.

`resolve` never makes a stand-in variable. The old `_editor_var` fallback created a
`tk.StringVar`, which the Qt shell must not do. A missing variable leaves its control out.

- **Tk**: `Open3DTopControlsPanel` now renders the catalogue with the same widget helpers and
  stores the same menu/button handles on the inspector. The built menus were compared
  before/after the change: the same entry counts and labels in all six, and the same three
  buttons.
- **Qt**: `qt/inspector_toolbar.build_toolbar` renders the same catalogue above the viewport:
  - QCheckBox / checkable QAction / QComboBox / QLineEdit / QToolButton menus;
  - each writes its variable and then runs the model's commit (as a Tk checkbutton does), and a
    model write repaints it through `trace_add`.

  The rows sit in a horizontal scroll area, so the window still fits the screen (950 on a 1000 px
  screen, viewport 426 px). **Close is Tk-only**: the shell's inspector is a dock, and `_on_close`
  would tear it down.

## Guard

`validate_open3d_qt_5f_toolbar`, penta phase **707**:
- **C-tk / C-qt**: every command and variable the catalogue names resolves on a REAL Tk inspector
  and on the Qt shell's (a renamed method fails here, not on a user's click).
- **T**: the six Tk menus carry exactly the catalogue's entries, in order; the handle buttons exist.
- **Q**: the Qt shell shows every control but Close (87). A checkbox writes the model and runs its
  commit; a model write repaints it; an Overlays menu check, the rotation-step choice and the
  Measure button reach the model.
- **L**: the viewport keeps >= 400 px and the window fits the screen.

## 22 guards re-pointed from the panel's source to the catalogue

The first full gate blocked on **20 phases**: 63, 204, 231, 232, 236, 257, 263, 265, 268, 307, 308,
318, 343, 349, 443, 487, 494, 531, 655 and 656.

- In every one, the behaviour checks still passed (for example 487's DXF export, 531's solve
  escalation and 231's heatmap integration).
- What failed was the wiring claim ("the Overlays menu has a 'Clipped' MenuCheckbutton", "the View
  toolbar packs 'Save Layout' bound to save_layout", "view_toolbar should be row 0"). These checks
  grepped `open3d_top_controls.py` for literal code.

Each claim now asks the catalogue, the single source both shells render. Two helpers do this:
- `open3d_toolbar.find(label, menu=, row=)`;
- `offers(label, target=, var=, menu=, row=)`.

A guard asserts the control is offered, in the right menu or row, wired to the right method and
bound to the right variable. 22 validators changed, two with larger rewrites:

- **validate_open3d_toolbar_layout (656)**: row order, category menus and their entries, and "dense
  actions stay in menus" are read from the catalogue.
  - Its direct-control budgets (10 / 8 / 7) had been measured by a regex over literal
    `ttk.X(row, ...)` calls, which missed every control built by a `pack_*` helper.
  - It saw 4 / 3 / 4 while the rows really held 14 / 11 / 8 widgets, so the View budget was never
    enforced.
  - The limits are now the honest catalogue counts at 0928 (13 / 8 / 4) as a no-growth ratchet.
- **validate_3d_interaction_contract (655)**: 17 toolbar claims moved onto `_tb.offers`; now 259 of
  259 checks pass.

## Next in 5f

- the live controls (559 lines);
- the Scene Components tree (1 639 lines, a Treeview with its own context menus).
