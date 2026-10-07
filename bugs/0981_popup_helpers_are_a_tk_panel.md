# 0981 -- popup-menu dismissal and dialog centring: the last service lets go of tkinter

Phase 7d of the Qt migration (docs/design_qt_migration.md), second part, seventh and last service.

## What was there

`services/paraxial_tools.py` imported tkinter for four small pieces of Tk and one `except`:

- a click elsewhere, or Escape, dismisses the popup menu the surface table posted -- unless the click
  is on the menu itself;
- a dialog centred over the main window, and one centred on the screen;
- the clean-up of that popup menu, which caught `tk.TclError`.

Its `messagebox` import was unused.

## Change

- The four pieces are `panels/main_popup_helpers.py`, class `MainPopupHelpers` -- the same code,
  moved; the editor's method names are one-line delegations.
- **The clean-up stays in the service.** It is the model that forgets which cell the menu was on,
  and 24 commands call it when they finish. It asks whatever made the menu to take it down by its
  own two calls -- a Tk menu, or the recording menu another shell renders -- and passes nothing on
  if those fail, where it used to pass on anything but a Tcl error. Taking a menu down must not be
  what breaks a command.
- **No service imports tkinter now**; only the Tk host does. Phase 738's list started at fourteen.

Nothing a user sees changes.

## What "no service imports tkinter" does not mean -- measured

Two other roads lead to tkinter, and phase 738 now measures both.

**Through what a module imports.** Until now the guard counted imports of `panels/` and `widgets/`
at module level: five services. Followed through every `KrakenOS.UI` import, the answer is **six**:

| Module | Its road to tkinter | What it is for |
|---|---|---|
| `services/analysis_reports.py` | a report panel -> `panels/report_view.py` | builds the report panels; their handle class `ReportWindow` lives in the Tk report view |
| `services/tolerance_modeling.py` | its report panel -> `panels/row_form_view.py` | the panel shows forms through the Tk form view |
| `services/layout_import_export.py` | the glass-catalogue panel -> `panels/row_form_view.py` | three panels; the lens-drawing one is Tk itself |
| `services/layout_shell_controls.py` | `widgets/` | binds Tk entries' commit keys |
| `services/layout_table_workbench.py` | `widgets/` | places the Tk table's in-cell entry |
| `services/three_d_scene_tools.py` | `open3d_inspector.py` | imports the 3D inspector, a Tk window class until phase 7e |

The old count missed the last one, and it counted `panels/main_path_detector_analysis.py`, which
holds no Tk at all (17 of the 50 modules in `panels/` do not import tkinter themselves).

The reading of the source is not what is trusted: a new claim **R** imports each of the 202 modules
of these layers in a process of its own and looks at what got loaded. The interpreter names the
same six.

**Through names nobody imported.** `layout_editor` copies its own globals -- `tk` among them -- into
some service modules, and code there calls `tk.Menu(...)` with no import of its own. One module
does, `services/layout_table_workbench.py`, sixteen times (claim U).

So what is left of 7d is those six modules. Two shared pieces would clear most of it: showing a
form or a report without importing the Tk view first (`present_row_form`, `ReportWindow`), and the
3D inspector imported when it is opened rather than when the service is.

## Guard: `validate_popup_helpers_view` (phase 748)

- **S:** the service imports and names no tkinter; the panel defines the four; the editor delegates
  the three that are called from outside; the clean-up is still the service's.
- **M:** the clean-up with no display -- released, destroyed, forgotten; forgotten all the same when
  those calls raise; only the cell forgotten when no menu is up; a recording menu the same.
- **T:** a real Tk editor -- the three bindings; a click on a real popup menu leaves it, a click
  beside it or on another widget and a dismissal with no event take it down; a 300 x 200 dialog
  lands centred over the main window and on the screen, to the pixel.

## Checks

**Mutations: 10 of 10 caught** -- the clean-up destroying the menu before releasing its grab,
stopping at a take-down that raises, keeping the cell, or not forgetting the menu; the service
importing tkinter again; a click on the menu dismissing it, a click beside it leaving it; a dialog
put at the main window's corner; centring on the screen only across; the editor no longer
delegating the dismissal.

**Neighbouring guards, all pass:** the tkinter-import list (738, with its new claim U), the panel
delegations, the model forms in Qt (721), the surface table's right-click menu (722: 127 entries,
112 run, no Tk window), the interaction contract (655). **Baseline:** phases 748 and 738 recorded.

Phase 738's three new claims were mutation-checked on their own: a clean service importing a Tk
view module (caught by I and R), loading tkinter in a way the source scan cannot see (caught by R
alone), naming `tk` without importing it (caught by U).
