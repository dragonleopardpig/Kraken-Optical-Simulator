# 0978 -- the inline thickness editor: out of the thickness-dimension service

Phase 7d of the Qt migration (docs/design_qt_migration.md), second part, fourth service.

## What was there

`services/open3d_thickness_dimensions.py` imported tkinter for the small window that a click on a
thickness dimension opens in the 3D view -- the row's label, one entry, OK -- and for the routine
that places it. 116 lines of Tk inside a method that also decides which row is edited, what value
it is prefilled with, and (since bugs/0950) asks a shell's own prompt instead.

## Change

- The window and its placing are `panels/thickness_inline_editor.py`
  (`open_thickness_inline_editor`, `position_inline_editor`) -- the same code, moved: centred on the
  screen by hand, input grabbed so that the 3D canvas cannot take the focus mid-type (bugs/0053),
  Enter or OK applies, Esc or the close button cancels.
- `edit_dimension` keeps everything else: the row checks, the prefill (the measured distance of a
  re-anchored row, the real gap of a trailing spacer), the shell's prompt, and it asks for the Tk
  window only when no shell draws the inspector.
- The service imports no tkinter. Phase 738's list goes from four services to **three**.

Nothing a user sees changes in either interface.

## Four guards read the old place

They pinned text inside `edit_dimension` that has moved, and now read it where it is:

- the interaction contract (655): the window's entry, its keys, its grab and the apply call are
  checked in the panel module; the service must build no window;
- the re-anchor guard and the same contract inside the comprehensive suite (phase 59): the prefill
  must be decided before EITHER view is asked -- the shell's prompt or the Tk window -- where it used
  to be "before the Tk variable is made";
- the trailing-spacer guard needed no change (the gap offset is still read in `edit_dimension`).

## Guard: `validate_thickness_inline_editor_view` (phase 745)

That the window opens on a real scene and the typed value lands, in both interfaces, is phase
723's (its Q3 and T). This guard holds what that one does not:

- **S:** the service imports and names no tkinter and builds no window; the shell is reached before
  the Tk window is asked for; the panel module defines both functions.
- **M:** under a shell, with no display -- the prompt's text and six-figure prefill; the typed value
  applied; a cancel, infinity and the last row each refused with their message; the two special
  prefills; the Tk window never asked for.
- **T:** the Tk window in a real Tk editor's 3D view -- title, label, prefill, OK, three keys and the
  close button; "abc" and "inf" leave it open with "Thickness must be a finite number."; a number
  closes it and changes the row; opened again there is one window; the close button cancels and
  changes nothing.
