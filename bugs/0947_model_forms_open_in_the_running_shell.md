# 0947 -- a form the model opens shows in the running shell (the sweep)

Step 1 of "what is left" in `docs/design_qt_migration.md`.

## The gap

The Qt shell's own menu actions build their forms themselves, so they have always opened Qt dialogs.
The **editor's** commands are a different route to the same forms. They are what the Tk menus, the
surface table's right-click menu and the 3D inspector's verbs call. They ended in Tk:
- 19 call sites in 18 files called `render_row_form`, the Tk renderer, directly;
- 18 `tkinter.messagebox` / `simpledialog` calls sat in front of them (the "could not read the
  table" and refusal messages of 9 panels, and the STEP admin's materials prompt).

The Qt shell's Tk root is withdrawn, so none of that can be seen there.

**Measured before**, calling 20 of the editor's form commands in a real Qt shell:

| Outcome | Before | After |
|---|---|---|
| Tk window | 14 | 0 |
| Tk message box | 2 | 0 |
| Qt dialog | 1 (stock lens, 0944) | 15 |
| Refusal through the host or the status line | 3 | 5 |

One command was worse than invisible. "Set bounds" opens its form and then waits for it. In the Qt
shell that wait never returned: the guard run against the old code hung until its timeout. Nothing
in the Qt shell reaches that command yet, but the table's right-click menu (the next step) will.

## Change

- **`present_row_form` is the one entry** (`panels/row_form_view.py`, from 0944). It gained
  `geometry=` and `wait=`, which is what callers used to do to the Tk window they got back:
  - six callers set a geometry on it;
  - one waited on it.
  A shell's dialog is not a Tk window, so those callers could not have been moved without this.
- **All 19 call sites use it.** Only `present_row_form` itself still calls `render_row_form`.
- **The Qt hook** (`show_model_row_form`) takes both. `wait` runs the dialog with `exec()`.
  `geometry` resizes it, but never below the dialog's own rule (see Sizes).
- **The 18 dialog calls go through `host_of`.**

## Sizes

- **Qt.** `RowFormDialog` has its own minimums: a record list is at least 1120 x 720, a form with
  a figure 1180 x 760. A smaller Tk hint does not undercut them. The glass catalogue (Tk hint
  900 x 600) opens at 1120 x 720 through the model, exactly as it does through the Qt menu action.
- **Tk is unchanged.** Measured at HEAD and after, the four windows with a geometry open at the
  same size and position:
  - glass catalogue 1085x600;
  - source manager 1520x720;
  - stock lens 1080x660;
  - shape builder 1180x760.

## What stays Tk, on purpose

23 tkinter dialog calls and the renderer itself live inside **Tk-only windows**: code that runs only
inside a Tk window. They are listed in the guard's `TK_ONLY` with exact counts:

| File | Calls | What it is |
|---|---|---|
| `panels/row_form_view.py` | 1 + 1 | the Tk renderer and its fallback call |
| `panels/report_view.py` | 4 | the Tk report window |
| `panels/mtf_from_image_dialog.py` | 4 | Tk view of the MTF session |
| `panels/main_optical_solid_face_roles_dialog.py` | 1 | Tk view of the face-roles session |
| `panels/main_paraxial_analysis_dialogs.py` | 1 | inside the Tk paraxial calculator |
| `panels/optical_stl_placement_dialog.py` | 2 | the Tk visual placement window |
| `panels/inspection_cell_window.py` | 1 | the Tk inspection-cell window |
| `panels/missing_assets_dialog.py` | 9 | no Qt counterpart yet (decision owed) |

## Guard: `validate_qt_model_forms_open_in_qt` (phase 721)

- **S:** outside `TK_ONLY`, no module calls `render_row_form(` or a tkinter dialog function. The
  listed counts are exact, so the list can only shrink.
- **F:** in a Qt shell, 20 editor form commands give 15 Qt dialogs titled as their forms, 3
  refusals through the host and 2 on the status line (as those commands always refused). No Tk
  window is created and no tkinter dialog is called.
- **G:** the glass catalogue is the same size through the model and through the Qt action
  (1120 x 720); the Shape Builder opens at 1180 x 760.
- **W:** "Set bounds" returns only once its dialog is closed.
- **T:** in Tk the same commands open Tk windows. The glass catalogue is its 900x600 hint grown to
  its content, and Set bounds waits on its Tk window.

**Mutation-checked:**
- The whole sweep reverted (the guard run at HEAD): the Qt run hangs in "Set bounds"; with that
  command left out, 14 Tk windows and 2 Tk message boxes.
- The Qt hook ignoring `wait`: W fails.

**Source pins re-pointed.** Four validators required the literal `render_row_form(` in a panel:
- the 3D interaction contract (phase 655, 11 pins);
- `advanced_surface_dialog_scrollable` (171);
- `source_panel_into_manager` (330);
- `0884_shared_tk_row_form_view` (672).

They now accept `present_row_form(`, and the contract still checks that `present_row_form` falls
back to `render_row_form`. The claim is unchanged: the form goes through the shared row-form view,
never a hand-built window.

## Gates

- **Targeted:** 171, 312, 330, 341, 474, 495, 496, 655, 671-673, 679, 680, 692, 718 and 721 pass.
- **Full Tk gate at 7e384fdc: 720 of 720 phases pass.** It ran on M90aPro (14 GB, no swap) as seven
  sequential `--phases` chunks under a 2.5 GB free-memory watchdog: 1 h 45 min, lowest free memory
  3.3 GB. This also covers 0945 and 0946, which had only targeted gates.
