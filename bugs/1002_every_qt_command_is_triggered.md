# 1002 -- every command of the Qt shell is triggered in the gate

Phase 7g of the Qt migration (docs/design_qt_migration.md): "both interfaces gated". bugs/1001
made one command run both suites. This asks what the suites hold of the Qt shell's own commands.

Since bugs/1000 the Qt shell starts without Tk: a Tk call that is still made somewhere no longer
reaches a hidden window nobody sees, it raises. Such a call can only still sit where no guard goes.

## Measured: which commands does a guard trigger?

Reading the guards does not answer it -- a guard can loop over names, click a ribbon button, send a
shortcut (two ways of reading them gave 50 and 71). So it was measured,
`bugs/1002_measure_triggered_commands.py`: each of the gate's 87 guards that build a Qt shell was
run, one at a time, from a scratch copy of the tree whose `ActionManager` logs every triggered
command (78 minutes; all 87 PASS, none skipped anything, 47 of them trigger a command).

Of the registry's 102 commands, 76 are triggered by at least one guard -- 62 of them by exactly
one -- and **26 by none**:

    import_zemax  import_zemax_wavefront  import_cad_solid  import_lens_step  import_camera_step
    import_led_step  export_3d_step  export_3d_dxf  export_wavefront_csv  export_zernike_csv
    quit  plot_2d  inspector  system_selection  about  clear_cad_axis_offsets  clear_step_imports
    place_cad_solid  folded_assembly  benchmark_psf_mtf  copy_phase2_report  copy_wavefront_fit
    clear_zemax_wavefront  formula_sheet  manual_index  copy_debug

## Surveyed: what does each command do in the shell as it starts?

`bugs/1002_trigger_every_qt_command.py <out.json>` starts the Qt shell the way `qt.app.run` does
(nothing asked for: no Tk; the real inspector as the 3D scene, the 2D plot beside it), loads
`common_optical_layouts/native_variable_breadth_example.py`, and triggers every command of
`qt.actions.ACTIONS` the way a click does, every question answered "cancel".

**No command raises, and none reaches Tk** -- not a Tk dialog function, a root, a window, a widget
or a variable. What they do first:

| first response | commands |
|---|---|
| asks for a file to open | 7 |
| asks for a file to save | 3 |
| asks for a number | 1 |
| shows a message (mostly "select a row first" / "run ... first") | 37 |
| opens a window | 22 |
| opens a modal dialog of its own | 2 |
| hands a document to the browser | 2 |
| reports in the status line | 21 |
| changes the view only (a check mark, the panels, the 3D toolbar, the camera) | 6 |
| nothing one can see | 1 -- Clear Marks, on a scene with no mark |

## Guard: `validate_qt_every_command` (phase 763)

One Qt shell in its own process, 164 s through the gate.

- **T:** the shell under test is the default one (no Tk), its 3D scene is the inspector, and the
  guard's table lists the registry's commands exactly -- a new command has to be entered there.
- **N:** no command raises, none reaches Tk, and no Tk root exists at the end.
- **F:** each command's first response is the table's: the question it asks through the UI host
  (with its title), the message it shows, the window it opens, its own status text, and what it
  changed (rows, the layout file, a check mark, the 3D toolbar, the panels, the camera).
- **Q:** every command answers; the ones that do nothing one can see are exactly the listed ones.
- **S:** nothing leaves the process: the scene file is the bytes it was (Save wrote a copy), no
  flag bundle and no picture appeared under attachment/, the formula sheet was written to the temp
  folder and not to the home folder.
- **Z:** Quit closes the window.

Eleven mutations of the product, all caught: About asks through a Tk dialog function (N); Copy
Debug raises (N); the 3D Toolbar switch does nothing (F); a new command not in the table (T); Quit
does not close (Z); the DXF export asks under another title (F); the shell starts with its hidden
Tk application (T); Folded Assembly makes a Tk window (N); Reset does nothing (F); Reload does
nothing (F); Clear Marks raises (N).

No product code is touched.

## What the survey had to get right (its first version was wrong three times)

- **Start as the app starts** -- `window.build_scene()`, not `build_viewport()`. With the bare
  preview the 3D Toolbar switch is disabled and Export 3D View DXF answers "Open the 3D view
  first": two findings that were the probe's, not the product's.
- **A command's own status text is the first one, not the last.** Read after the event loop
  settles, the status line holds whichever view caught up last ("3D inspector updated", "Plot
  refreshed"). The session records every text written and takes the first that is not a view
  catching up.
- **A panel tabbed behind another is `isVisible()`.** What is on screen is
  `not dock.visibleRegion().isEmpty()`; and `rails.toggle(dock)` on a panel that is behind brings
  it forward, it does not put it away.
- `QWidget.grab()` does not capture the VTK scene (noise under Xvfb): `vtkWindowToImageFilter`.
- A session that takes over `sys.excepthook` swallows its own crash; the recorder prints it.

## Found on the way -- measured, NOT changed, for the user to decide

**Trace Now traces, and the 3D scene draws no rays.** `bugs/1002_trace_now_probe.py`, picture
`bugs/1002_trace_now_draws_no_rays.png` (after load / after Trace Now / after Show Rays):

| step | status line | Show Rays | rays in the 3D scene |
|---|---|---|---|
| load | "Loaded ... (rays not traced -- fast load). Click Trace Now for rays, Update for analysis." | unticked (the bugs/0801 / 0818 rule) | none |
| the ribbon's Trace Now | "Rays traced." | still unticked | **none** -- the FOCUS banner appears, the rays are in the 2D plot, a tab behind System |
| Show Rays | "Rays shown." | ticked | drawn |

In the Tk interface Trace Now sits on the 2D plot's toolbar, where the rays appear. In the Qt
shell the view in front is the 3D scene, and "Click Trace Now for rays" gives it none.

Ways to settle it: (a) Trace Now ticks Show Rays again when it was the fast load that unticked it
-- a tick the user took off stays off; (b) the load message names Show Rays; (c) leave it.

## What is left of phase 7g

- The first full run of both suites, for the user to start: 762 phases on Tk and 352 hosted in
  the Qt shell.
- The six import and four export commands of the list above are held up to their file dialog. With
  real files they are driven by no guard in the Qt shell.
