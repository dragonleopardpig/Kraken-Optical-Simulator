# 0983 -- showing a form no longer imports tkinter

Phase 7d of the Qt migration (docs/design_qt_migration.md), third part: the modules that load
tkinter through what they import. Five were left after 0982; this is the shared piece behind most
of them.

## What was there

`present_row_form` is what a command that ends in a form calls: a shell that draws its own dialogs
gets the form, otherwise Tk's renderer draws it. It lived in the Tk form view,
`panels/row_form_view.py`. So every module that only wanted to SHOW a form imported tkinter with
it -- eight dialog panels whose whole job is to build a form and hand it over, and through them the
services that build those panels.

## Change

- `present_row_form` is `row_forms/present.py`, in the forms package, which has no toolkit in it. It
  imports the Tk renderer at the moment Tk actually draws a form.
- All 22 modules that imported it from the Tk view import it from there. The old name in the Tk
  view is kept, as the same function, for the guards that read it there.

Nothing a user sees changes in either interface.

## What it clears, measured by the interpreter

| | Before | After |
|---|---|---|
| Modules of the toolkit-free layers that load tkinter when imported | 5 | **4** |
| Dialog panel modules that load tkinter when imported | 39 of 50 | 31 of 50 |
| Tk view classes named in services | 53 uses of 48 classes, 8 modules | 45 uses of 40 classes, 7 modules |

`services/tolerance_modeling.py` is clear. `services/layout_import_export.py` now reaches tkinter
only through its lens-drawing panel, which is Tk itself. The four left: `analysis_reports` (the
report window), `layout_import_export` (lens drawing), `layout_shell_controls` and
`layout_table_workbench` (`widgets/`).

## Guard: `validate_present_row_form` (phase 749)

- **S:** no module imports the presenter from the Tk view; the old name is the same function.
- **L:** asked of the interpreter, each in a fresh process -- importing the presenter loads neither
  tkinter nor Qt; a form handed to a shell through it reaches the shell with all four options, the
  shell's answer comes back, and the Tk form view is never imported; the eight form-only panels
  load no tkinter.
- **T:** the Tk app with no shell -- the Tk renderer draws the form with the options passed on; the
  window is sized as asked; `wait` waits on it and a form shown without `wait` does not.

Phase 738's exact lists follow: four modules load tkinter (I and R), 45 uses of Tk view classes (C).
Phase 721 counts the one remaining call of the Tk renderer in the presenter's new file.
