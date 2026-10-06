# 0967 -- the Inspection Cell view is a Qt window in the Qt shell

Phase 7a of the Qt migration (docs/design_qt_migration.md): the last window a Qt user could reach
that was a `tk.Toplevel`.

## What was wrong -- measured, not read

The design doc said the cell view "is a Tk window on the hidden root (read from the code, not
run)". Run in the Qt shell, with two stations, through the form's own "Open Cell View":

- the action composed the cell (26.5 s) and returned its summary -- it looked like it had worked;
- a Tk `InspectionCellWindow` existed, **mapped and viewable, 1100 x 783 at the screen's corner**;
- no Qt window was opened;
- **a 200 ms Tk timer armed on that window did not fire in 3 s of the Qt event loop.**

So the window was on screen and dead. Nothing pumps Tk under the Qt shell: it never repainted,
its buttons and its double-click did nothing, and its file watch -- the thing that makes the view
"iterative" -- never ran.

## Change

One session, two views, as for the face-roles editor, MTF from Image and the missing-files window.

- **`services/inspection_cell_session.py`** -- `InspectionCellSession` holds everything the window
  did: the off-screen composition and the transplant of its actors into the renderer a view hands
  over, the geometric pick that maps a double-click to a station, opening a station's layout, the
  file watch, and the STEP export.
  - The watch is a timer on the **UI host** (`host.after`), so it fires under either toolkit.
  - The export's file question is asked through the host, with the view as its parent.
  - A station opens through the shell's own layout loader when the shell gave one
    (`session.open_layout`), else through the editor's -- the Qt window's table and scene have to
    follow the load.
- **`panels/inspection_cell_window.py`** is the Tk view of it (326 -> 175 lines): the Toplevel, the
  VTK/Tk widget, the session's buttons and status line. Its public names are unchanged.
- **`qt/dialogs/inspection_cell_dialog.py`** is the Qt view: a non-modal dialog with the session's
  buttons, a `QVTKRenderWindowInteractor` built once the dialog is shown, the status line. The first
  composition is left to the event loop, so the window is on screen saying "Composing..." while the
  stations load. Close, Escape and the window's own button end the session, then finalize the
  render window.
- **The seam:** `open_inspection_cell_view(owner, cell)` asks the shell's `show_inspection_cell`
  first (the Qt main window installs it) and falls back to the Tk window, which keeps its pyvista
  fallback. The form's "Open Cell View" calls it.

The Qt view uses the shell's gradient backdrop (bugs/0966). The stations themselves are drawn by the
off-screen composer as before.

## Guard: `validate_qt_inspection_cell_view` (phase 736)

- **P1-P5:** the session with no display, on a scripted clock, the composition stubbed: the
  transplant and the face map; the previous plotter closed only once its actors are replaced; a
  failed composition leaves the scene; a station opened through the shell's loader or the editor's;
  one timer at 2000 ms that composes only when a file changed and is cancelled by close; the export
  asked through the host; the opener choosing the shell or Tk.
- **Q:** in the real Qt shell with two real stations (fixtures in git): the form's own action opens
  a non-modal Qt dialog and makes **no Tk window**; the view is a real OpenGL render window holding
  169 actors, both stations reachable; **a real double-click** on the top station loads its layout
  through the shell (the editor's file, the table's 7 rows); touching that file re-composes the cell
  **on Qt's clock**; the Export button asks the host with the dialog as parent; Close ends the
  session and the shell's scene still draws.
- **T:** the Tk window is a view of the session it is handed: the session's buttons, its status
  line, and destroying it closes the session.

**Seen by eye:** the Qt window after composing two stations -- the part, both stations on their
axes, the summary under the view.

## Guards re-pointed

- `validate_open3d_0664_inspection_cell_window` (phase 497) pinned the SOURCE of the Tk window for
  "station files are watched" (`_poll_station_files`). The watch lives in the session now, so that
  claim is measured on a scripted clock instead. Its window checks A1-A5 are untouched and pass
  against the new view -- that is the old-against-new proof for the Tk side.
- `validate_qt_model_forms_open_in_qt` (phase 721): `panels/inspection_cell_window.py` leaves the
  Tk-only list -- it has no tkinter dialog call any more. The list is 16 calls in 6 windows (was 17 in 7).
