# 0980 -- the System Selection Calculator's Tk form: out of the calculator's core

Phase 7d of the Qt migration (docs/design_qt_migration.md), second part, sixth service.

## What was there

`services/system_selection.py` is the calculator's first-order core: pixel count, magnification,
working distance, Nyquist, the diffraction f-number. At its end it also carried 161 lines of Tk --
the live form (seven inputs and a result that recomputes as you type) and the window that holds it
for the Tk menu -- with tkinter imported inside the two functions.

The model's command, `open_system_selection_calculator`, built that Tk window whatever the shell.
The Qt interface never noticed, because its own action opens the calculator's row form instead; the
command itself was listed in phase 723 as a known Tk-only window.

## Change

- The form and its window are `panels/system_selection_view.py`. The 3D view's left panel, which
  embeds the same form compact, takes it from there.
- `open_system_selection_calculator` asks first whether another shell draws the editor, and shows
  the calculator's row form there -- the one that shell's action opens. Otherwise the Tk window.
- The core imports no tkinter. Phase 738's list goes from two services to **one**
  (`paraxial_tools`). Phase 723's list of Tk-only windows in services is now **empty**.

Nothing a user sees changes in either interface.

## Guard: `validate_system_selection_view` (phase 747)

- **S:** the core imports and names no tkinter, not even inside a function, and no longer has the two
  functions; the panel module defines both; the command checks for a shell before it reaches for the
  Tk window; the 3D left panel takes the form from the panel module.
- **T:** the Tk app -- the command opens one resizable window with seven entries and Close; after each
  typed input the form shows exactly what the model computes for it, a value that is no number
  included; Close closes it.
- **Q:** the Qt shell -- the same command opens the calculator's Qt form, makes no Tk window and
  never asks for the Tk view.

Two guards named the old place and now read the new one: the calculator's own (0631, its shared-form
and self-fitting-window checks) and the Qt constraints / selection guard (phase 709).
