# 0984 -- a report window's handle no longer loads tkinter

Phase 7d of the Qt migration (docs/design_qt_migration.md), third part: the modules that load
tkinter through what they import. Four were left after 0983.

## What was there

`ReportWindow` is what a report panel keeps. It opens, refreshes and closes the report, answers
for the selection, copies, exports and runs the report's verbs; under a shell that draws its own
dialogs it hands all of that to the shell's dialog (bugs/0948). It was ALSO the Tk view: one class
of 510 lines in `panels/report_view.py`, the handle's logic and the widget code interleaved method
by method. So every panel that wanted a handle loaded tkinter with it -- and through the panels,
`services/analysis_reports.py` did.

## Change

Two modules:

- **`reports/window.py`: the handle**, with no toolkit in it. The same class, the same 26 method
  names, the same attributes (`window`, `table`, `detail_table`, `detail_widget`, `summary_var`,
  `controls`, `control_widgets` -- what the panels and the guards read). Every method first deals
  with a shell's dialog, then with "no Tk window is up", and only then asks the Tk view.
- **`panels/report_view.py`: the Tk view**, thirteen functions over the handle -- make the window,
  the table and the detail table; render; follow the controls; the selection; the detail pane. The
  handle imports it at the moment Tk actually draws a report, and never under another shell.

The bodies were moved by a script from the class's own source, not retyped: a method that was all
widget code became a function with `self` renamed; the seven methods that mixed the two were cut
where the widget code begins.

Nothing a user sees changes in either interface.

## What it clears, measured by the interpreter

| | Before | After |
|---|---|---|
| Modules of the toolkit-free layers that load tkinter when imported | 4 | **3** |
| Dialog panel modules that load tkinter when imported | 31 of 50 | 32 of 50 do; 18 do not (was 11) |
| Tk view classes named in services | 45 uses of 40 classes, 7 modules | 38 uses of 32 classes, 6 modules |

`services/analysis_reports.py` is clear. The three left: `layout_import_export` (its lens-drawing
panel is Tk itself), `layout_shell_controls` and `layout_table_workbench` (`widgets/`).

## Guard: `validate_report_window_handle` (phase 750)

What the Tk windows and the Qt dialogs DO is held by the guards that already drive them (phases
682-685 and 638-645). This one holds what the split added:

- **S:** the handle names no tkinter; the Tk view has no class; the old name is the same class; all
  26 methods are still there; no module takes the handle from the Tk view.
- **L:** by the interpreter -- importing the handle loads neither tkinter nor Qt; the six report-only
  panels load no tkinter.
- **N:** a handle never opened, used in every way in a fresh process, loads no tkinter and does
  nothing.
- **Q:** a handle under a shell with a stand-in dialog, in a fresh process -- open, open again,
  refresh, the selection, a verb, export, close all go to the dialog as they should, and neither
  tkinter nor the Tk view is ever imported.

## Checks

**Mutations: 10 of 10 caught.** Nine at once: the handle importing the Tk view when imported; a
handle with no Tk window asking the Tk view whether it is open, or on close; under a shell, open
building a Tk window as well, refresh not giving the dialog the new report, the selection or the
controls not asked of the dialog; a method of the class gone; a panel taking the handle from the Tk
view again.

The tenth survived the first run: a shell's dialog that the USER closed still counting as open.
The guard only ever closed the dialog through the handle. It now closes it as a user does and
requires the handle to notice -- not open, nothing rebuilt on Update, a new dialog on the next open.

**Passing after the change:** the four guards that drive the Tk report windows (0894-0897), the
interaction contract (655), phase 738 at three modules, the panel delegations, and 17 gate phases
about reports and their panels (638-645, 663, 682-685, 715, 718, 721, 722).

**Baseline:** phases 750 and 738 recorded (pass; 749 phases). The full Tk gate was last run at
ff4c2088.
