# 0854 -- the Qt implementation of the UI host (Qt migration, phase 2)

docs/design_qt_migration.md. 0851 cut the seam and 0852/0853 freed the model from Tk ownership;
this is the third implementation behind that interface. Model and controller code does not change:
the same `host_of(self).askyesno(...)` / `.after(...)` calls are served by QMessageBox and QTimer.

## What changed

- `KrakenOS/UI/uihost/qt_host.py` -- `QtUiHost`, all 25 `UiHost` methods. PySide6 is imported
  inside the methods, never at module level, so importing the package (and therefore a Tk run and
  every display-free guard) still loads no Qt binding.
- `qt_filter` converts tkinter's `[("STEP", "*.step *.stp"), ...]` into Qt's
  `"STEP (*.step *.stp);;..."`. The repository passes 47 such literals; a bare extension
  (`".py"`, which tkinter accepts and Qt does not) grows its star.
- State variables come back as `ObservableValue` -- a Qt view binds through `trace_add` the way a
  Tk view binds `textvariable=`.
- devenv: `ps.pyside6` from nixpkgs (so it matches the Qt libraries, and the venv sees it through
  `--system-site-packages` like vtk and pythonocc-core), the nine X/xcb libraries Qt 6's xcb
  platform plugin loads beyond what VTK and Tk already needed, and `QT_PLUGIN_PATH` -- a bare
  `import PySide6` has no wrapper to set it. Proved: `xcb` under Xvfb and `offscreen` with no
  display at all.

## Two things that had to be built, not mapped

**A fired timer frees itself.** The obvious `after` pops its timer from the pending dict and calls
the callback -- which drops the QTimer's last reference *inside its own `timeout` signal*, deleting
the C++ object mid-emission. `fire()` therefore holds the timer in a local and `deleteLater()`s it.
Guard section Q1 runs 25 timers whose callbacks force a GC.

**`update_idletasks` must not run scheduled callbacks.** The natural mapping,
`processEvents(ExcludeUserInputEvents)`, runs pending `after` callbacks -- measured: a `host.after(0, ...)`
fires during it. Tk's `update_idletasks` runs idle work only, and this codebase calls it
mid-operation (autosave, redraw flushes) counting on exactly that; a callback re-entering model
code there is the shape of half the interaction bugs in the 0300s. It now delivers the POSTED
event queue (`sendPostedEvents`, plus deferred deletes), which repaints the widgets that asked to
be repainted and leaves both re-entrancy sources alone: `after` callbacks are real QTimers
dispatched by the event loop, and user input is read from the window system, which this never
asks.

## Guard

`validate_open3d_0854_qt_ui_host.py`, penta phase 633. Its Qt half runs in a SUBPROCESS on the
offscreen platform: a QApplication must never be created inside the penta harness, which already
holds a Tk interpreter and a live VTK render window. Without PySide6 those sections SKIP and the
rest still runs.

A/B/C interface completeness, no Qt binding imported by the package, `qt_filter` over the 47 real
filetypes literals. Q1-Q8 against a real QApplication: timers (args, distinct handles, cancel,
scheduling from a callback, self-freeing), the blocking `after(ms)` Tk also has, the idle flush
(repaints, runs no callback), every message button mapped to the value tkinter returns, the
arguments Qt actually receives from the file and input dialogs, the clipboard, and REAL model code
on a Qt host -- the 64 declared model variables come up working, and
`layout_analysis_display._autosave_plot` reads one, cancels its previous timer and schedules the
next, firing exactly once.


## The viewport spike

`bugs/spike_0854_qt_viewport.py` answers the other half of phase 2: a PySide6 window whose
`QVTKRenderWindowInteractor` draws the real `om05a_folded.py` bodies from a headless editor, and a
Qt mouse drag that rotates VTK's camera. Its docstring lists the four traps that cost a round each
(missing `vtkRenderingOpenGL2` import -> an abstract render window that draws nothing and
segfaults on capture; Qt on Wayland while VTK is on Xvfb; a viewport built before its parent chain
is live; and the STEP bodies' active `kraken_step_selection_face_index` cell scalars hiding them
unless the mapper has `ScalarVisibilityOff()`), plus the joystick-by-default interactor style that
makes a drag do nothing. docs/design_qt_migration.md keeps the same list for phase 5.
