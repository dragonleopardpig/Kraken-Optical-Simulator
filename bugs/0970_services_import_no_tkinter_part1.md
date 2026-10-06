# 0970 -- services that import tkinter: fourteen to seven, and a list that can only shrink

Phase 7d of the Qt migration (docs/design_qt_migration.md), first part.

## What was there

`services/` is meant to hold no toolkit code. Measured: 14 of its 151 modules imported tkinter.
Read one by one, they fall into three groups.

**Six did not need to.**

| Module | What it imported | Used |
|---|---|---|
| `tolerance_modeling.py` | `messagebox`, `simpledialog` | never (its dialogs go through the host since 0943) |
| `layout_import_export.py` | `tk`, `filedialog`, `messagebox` | never |
| `three_d_scene_tools.py` | `tk`, `filedialog` | never |
| `open3d_face_assignment.py` | `tk`, and `messagebox` inside two functions | never -- both functions ask through the host on the next line |
| `layout_analysis_display.py` | `messagebox` inside one function | never -- same |
| `step_overlay_import.py` | `tk`, `ttk` | only to annotate `dialog_parent: tk.Misc`, which under the Qt shell is a Qt widget |

**One made Tk variables in model code.** `inspection_cell.load_station` loads a station with no
inspector and seeds the two inspector switches the scene populator reads -- as `tk.BooleanVar`s,
which no other host can make. On an owner that is not Tk the constructor raised, the `except`
swallowed it, and the switches were simply missing.

**Seven hold real Tk windows or menus** and stay for now: the text widgets' copy helpers
(`analysis_compute_workflow`), the Tk editor's flag popup (`layout_bug_recorder`), the Tk menu
bar's submenus (`layout_shell_controls`), the inline thickness editor
(`open3d_thickness_dimensions`), popup and dialog-centring helpers (`paraxial_tools`), the LED
edge-distance prompt (`scene_placement_commands`), the System Selection window
(`system_selection`). Each is Tk view code living in a service; moving them into `panels/` is the
second part of 7d.

## Change

- The six: the imports are gone; `dialog_parent` is annotated `Any`.
- `inspection_cell.seed_inspector_variables(editor)` makes the two switches through the editor's
  UI host. Under Tk they are the same `tk.BooleanVar`s as before.
- No behaviour changes under either shell.

## Guard: `validate_services_import_no_tkinter` (phase 738)

- **S:** an AST scan of `services/`, `reports/`, `row_forms/`, `uihost/` and `qt/` for run-time
  tkinter imports, against an EXACT list of the modules allowed one -- the seven services and
  `uihost/tk_host.py`, each with what it still holds. A new importer fails; a cleaned module must
  be deleted from the list, so it can only shrink.
- **M:** the seven cleaned modules import, and none still refers to a tkinter name.
- **V:** on a toolkit-free owner `seed_inspector_variables` makes both switches, as booleans
  holding False, and leaves an existing one alone.

The guard earned its keep on its first run: it found a second `from tkinter import messagebox`
inside `open3d_face_assignment.py` that my own survey had missed (the survey kept one line per
imported name).
