# 0964 -- the Qt shell has its 2D plot, with the Tk plot toolbar's controls and Trace Now

Recommended next ("2D-plot toggles (cardinals, thickness)", the last shell-parity gap in the design
doc). The user said "please proceed recommended next."

## What was found

The item turned out bigger than two toggles.

- **The Qt shell had no 2D plot at all.** `qt/plot2d.LayoutPlot2D` was written in bugs/0893, but
  `build_plot2d()` was only ever called by its own guard, never by the running app. So:
  - the user never saw the 2D layout in the Qt shell;
  - every analysis plot (MTF, spot, wavefront, ...) was drawn into the hidden Tk window: an Update
    seemed to do nothing but fill the Results table.
- **None of the Tk plot toolbar's controls had a Qt route:** the 2D layout pane switch, Plane
  (YZ / XZ / XY / All), Show PP / EP / XP, Show labels, Rays (all / detector hits / ...), Physical
  Distance.
- **Trace Now had no Qt route either.** It is the explicit trace after a fast, geometry-only load
  (bugs/0646).

## Change

- **`build_scene` builds the 2D Plot** -- `KrakenQtMainWindow.build_plot2d`:
  - a panel on the right, tabbed behind System, so the start-up layout is unchanged;
  - its own "2D Plot" tab on the right edge;
  - it floats into a window of its own like any panel.

  The editor draws into its figure and canvas, so the layout and the analysis plots appear there.
- **An analysis Update brings it to the front**, from behind its tab or when it was closed, so the
  plots it draws are seen.
- **Its toolbar is the Tk plot toolbar:**
  - the six controls, as data in `KrakenOS/UI/plot2d_toolbar.py` (`PLOT_2D`), built by the 3D
    toolbar's own row builder and bound to the SAME editor variables and commits as the Tk
    checkbuttons;
  - then **Trace Now**, **Update** and **Ray Inspector**, the shell's own actions, shown with their
    names. The Tk plot's "Trace" opens the Tk ray inspector; in Qt it is the shell's.
- **Two new actions:**
  - **Trace Now** (`trace_now`) -> the model's `_trace_now`;
  - **2D Plot** (`plot_2d`) brings the panel to the front.

  Both are on Home > View and in the command palette.
- `qt/inspector_toolbar.py`: the row builder is factored out (`_adder`, `row_toolbar`) so the 3D
  strip and the 2D plot share it. The 3D strip is unchanged (its guard passes).

The Tk app is unchanged.

**Seen by eye** (om05a_folded, a 1916x1034 window): the plot in its panel after Trace Now, with
Show PP / EP / XP switched off; floating at 1100x800, the toolbar named and the layout full size.

## Guard: `validate_qt_plot2d_panel` (phase 733)

- **S:** static -- the Tk plot toolbar still binds each of the six variables to its commit
  (`TK_BINDINGS`), and the Qt row binds the same six pairs.
- **P:** `build_scene` builds the panel: titled "2D Plot", on the right with its tab, tabbed behind
  System (System in front); the editor's figure and canvas are the panel's; after Trace Now the
  layout is drawn (26 lines, 19 collections).
- **C:** each of the six controls writes its variable and runs its commit exactly once; a model
  write repaints the check. Show PP / EP / XP takes the 4 marker artists off and puts them back;
  Physical Distance draws 6 annotations and clears them.
- **U:** an Update brings the plot to the front, from behind the System tab and when it was closed.
- **N:** Trace Now is on the plot's toolbar, and a click runs the model's deferred trace; Trace Now
  and 2D Plot are on the ribbon.

**Mutation-checked:**
- not built: P fails;
- an Update does not raise it: U fails;
- Trace Now missing from its toolbar: N fails;
- a control bound to the wrong commit: S and C fail;
- not tabbed with System: P and U fail.

**Guards updated:**
- `validate_qt_scene_layout` (724): the right edge's tabs now include "2D Plot".
- `validate_qt_shell_flag` (729): a flag bundle now also has `layout_2d.png`, the 2D plot, now that
  the shell has one.

## Gates

By the batch cadence: own guard plus the guards that read this code -- ribbon, scene layout, clean
scene, Qt-hosted inspector, menu parity, the 5f toolbar, shell flag, ribbon window height, and the
0893 plot guard. The full gate is owed since 3265c622 and is due now: 0962, 0963 and 0964 are the
batch.
