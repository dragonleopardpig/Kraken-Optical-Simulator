# 0976 -- "copy this text": the Tk code out of the analysis service

Phase 7d of the Qt migration (docs/design_qt_migration.md), second part, second service.

## What was there

`services/analysis_compute_workflow.py` imported tkinter for nine methods that are Tk view code: the
copy shortcuts and the right-click menu on the main window's text boxes (the debug log, the progress
log, a report's detail text), and the window-wide Ctrl+C / Ctrl+V that follow the focus. Its
`filedialog` and `messagebox` imports were not used at all.

## Change

- **The view is a panel:** `panels/main_text_copy.py`, class `MainTextCopy`, in the same delegating
  shape as the other `Main*` panels. It reads what a Tk text box has selected, posts the two-entry
  menu, and decides by the focus whether Ctrl+C means "this text" or "these table rows".
- **The model keeps what is not a view's:** `copy_selected_text(text)` and `copy_all_text(text)`
  copy to the system clipboard and say so on the status line -- "Selected text copied to clipboard
  (xclip)", "No text selected", "No text to copy", "Copy failed". The Qt shell can ask for the same.
- The editor's nine method names are unchanged; each is now a one-line delegation to the panel, so
  the main window builder and the report view call them as before.
- The service imports no tkinter. Phase 738's list goes from six services to **five**.

Nothing a user sees changes: the same keys, the same menu, the same status messages.

## Guard: `validate_text_copy_view` (phase 743)

- **P:** the model with no display -- selected and whole text copied; none and empty say so; a
  clipboard that fails says "Copy failed"; one that raises becomes a debug line.
- **S:** the service imports and names no tkinter; the panel defines all nine methods and the editor
  delegates all nine to it.
- **T:** a real Tk editor -- both logs carry the six copy shortcuts and the right-click binding; a
  selection, no selection and the whole log go through the model with the right text; the menu is
  one menu of two entries, re-aimed at the box it was opened on; the window-wide copy takes a log's
  selection, hands a focused table to the row copy and paste to the row paste; a focus Tk can no
  longer name (a transient dialog's widget) reads as no focus.
- **Q:** in the Qt shell the model command works and the window's status line shows what was copied.

One claim I first wrote was wrong and is gone: that the Qt shell's editor never builds this panel.
It does -- the Qt shell's editor still builds its hidden Tk window, which binds its own keys. That
ends with phase 7f, not here.

## Checks

**Mutations: 14 of 14 caught, each by the claims meant to catch it** -- the model copying with no
selection, not catching a clipboard that raises, reporting a failed copy as done, calling "all" a
selection; a text box with no selection raising; the menu rebuilt every time, or not re-aimed; a
focused table not handed to the row copy; a focus Tk cannot name not caught; the right-click
binding, a copy shortcut, or the window-wide paste missing; an editor method no longer delegating;
the service importing tkinter again.

**Neighbouring guards, all pass:** the tkinter-import list (738: five services now), the panel
delegations (145 of them, none targeting a method its panel lacks), the results and debug panels
(686), the sampling-stability contract, the table component workflow, the interaction contract (655).

**Baseline:** phases 743 and 738 recorded (pass; 742 phases). The full Tk gate ran at ff4c2088; it
has not been run again since (0974, 0975 and this came after).

