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

## What "no service imports tkinter" does not mean

Importing is not the only way to use it. `layout_editor` copies its own globals -- `tk` among them --
into some service modules, and code there calls `tk.Menu(...)` with no import of its own. Measured
now: **one module does, `services/layout_table_workbench.py`, sixteen times.** Phase 738 counts that
against a third exact list (claim U), next to the five services that import a Tk view package.
So what is left of 7d is those five, of which the table workbench is the large one.

## Guard: `validate_popup_helpers_view` (phase 748)

- **S:** the service imports and names no tkinter; the panel defines the four; the editor delegates
  the three that are called from outside; the clean-up is still the service's.
- **M:** the clean-up with no display -- released, destroyed, forgotten; forgotten all the same when
  those calls raise; only the cell forgotten when no menu is up; a recording menu the same.
- **T:** a real Tk editor -- the three bindings; a click on a real popup menu leaves it, a click
  beside it or on another widget and a dismissal with no event take it down; a 300 x 200 dialog
  lands centred over the main window and on the screen, to the pixel.
