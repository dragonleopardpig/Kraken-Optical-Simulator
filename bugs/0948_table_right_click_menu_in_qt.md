# 0948 -- the surface table's right-click menu is the model's own, in both shells

Step 2 of "what is left" in `docs/design_qt_migration.md`.

## The gap

The Tk surface table's right-click menu offers over a hundred commands in thirteen submenus:
convert type, insert component, shape, material, coating, geometry, element, path assignment,
diagnostics, advanced, solves. The Qt table's menu had **three** (the optimisation entries, 0904).

## Change: one builder, any menu

`MainContextMenu.show_context_menu` was one 470-line method that did two things: it worked out
which Tk cell was under the pointer, and it built the menu. Only the first part is Tk. The body
used nothing Tk-specific except `menu.index("end")` and the final posting.

- **`build_cell_menu(row_index, field, menu)`** is the builder, lifted out unchanged. It fills
  whatever menu it is handed: a `tk.Menu`, or a recording `MenuModel` (`context_menu.py`, the 0907
  mechanism the 3D inspector's menus already use). Its 14 submenus follow the menu they hang from.
- **`show_context_menu(event)`** keeps the Tk cell lookup and posts the result.
- **`editor.table_cell_menu(row_index, field)`** is the shell's entry. It does what a Tk
  right-click does first (a cell outside the selection becomes the selection; the cell is
  remembered as the "current cell" the Solve verbs act on), then returns the recorded menu.
- **`MenuModel.index("end")`** answers as `tk.Menu` does.
- **Qt:** `_show_cell_menu` draws the model with the existing `build_qmenu`. After any entry runs,
  the table and the 3D view re-read the model.

Nothing was ported twice: the Qt menu is the Tk builder's output.

## What the menu reached that was still Tk

Running **every** entry in a Qt shell (118 distinct commands) found two more Tk-only paths.

1. **Reports.** "Ray Inspector", "Trace Path Inspector", "Detector Aperture Report" and
   "Non-Sequential Scene Graph" opened the Tk report window, although the Qt shell has a Qt
   dialog for each of those reports.
   - The Tk report handle (`panels/report_view.ReportWindow`, one class behind ten report
     commands) is now shell-aware. When the editor has a `show_report` seam, the handle shows its
     report in the shell's dialog.
   - Everything the model asks of the handle goes to that dialog: open, refresh on Update, close,
     the selection.
   - The class's last four direct tkinter dialog calls go through the host, so it left the
     Tk-only list of 0947 (20 calls in 7 windows now).
2. **Group / Ungroup Element** returned silently in Qt: they first asked the hidden Tk table
   whether anything was selected. They now ask the table the user sees (`_table_has_selection`).

**Still Tk, listed in the guard:** "Best Image Solve". On a simple on-axis layout "Paraxial Solve
This Thickness" is too. Both are the un-ported paraxial solve prompts (step 5); in the Qt shell
they currently fail with an error message rather than a dialog.

## Guard: `validate_qt_table_context_menu` (phase 722)

On the two-arm doublets example, for seven cells:
- **B:** the menu the real Tk right-click builds and the model a shell is handed have identical
  outlines (labels, enabled states, nesting): 102-112 commands in 13 submenus.
- **Q:** a Qt right-click shows exactly that outline: the model's, and the Tk shell's.
- **R:** entries run from the Qt menu.
  - Convert Type → Mirror changes the row in the model and the Qt table; Undo restores it.
  - Coating / Material Editor opens a Qt dialog.
  - Select ... for optimization marks the cell.
  - Set bounds waits on its dialog.
- **N:** no Tk window, no tkinter dialog.
- **E:** every distinct entry (118; 103 enabled on this scene) run once in a throwaway Qt shell,
  with the layout reloaded before each and every question cancelled. None raises, calls a tkinter
  dialog or creates a Tk window, except the entries in `KNOWN_TK_ENTRIES`, which may only shrink.

**Proof Tk is unchanged:** before applying, the HEAD builder and the refactored one were each driven
through the real Tk right-click path for the seven cells. All seven outlines are identical.

**Mutation-checked:** without the `show_report` seam, E fails and names the four Diagnostics
entries.

**Other guards touched:**
- 0904 (phase 692) looked the three optimisation entries up by position in a 3-entry menu. It now
  finds them by label in the "Optimization / Solves" submenu.
- 0947 (phase 721): `panels/report_view.py` left `TK_ONLY`.

## Found on the way: the venv was wiped mid-session

At 23:17 a direnv re-entry wiped the KrakenOS venv. It followed an `.envrc` change made while
fixing a devenv CLI update (2.4.0 installed beside the system 2.0.6 this project pins). The
project's bootstrap re-creates the venv empty whenever it decides the Python changed. Restored with
`/run/current-system/sw/bin/devenv shell kraken-install` (209 packages from pip's cache, 8 tooling
packages fetched). **Use the system devenv for this project until its modules are re-pinned.**
