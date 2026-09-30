# 0935 -- a ribbon with icons + a command palette for the Qt shell

User request: "Please implement palette ribbon menu with icons."

## What it is

- **`qt/ribbon.py`**, four tabs of grouped icon buttons:
  - **Home**: File, View.
  - **Surfaces**: Surface, Special rows, Catalogs.
  - **Scene**: Placement, Sources, CAD, Inspection.
  - **Analysis**: Plots, Paraxial, Rays, Power, Design, Tolerance.

  Large buttons have their label under the icon; small ones stack three to a column. `RIBBON` is
  the whole layout as data.
- **Every button runs the shell's own `QAction`** (`actions.ACTIONS`). A ribbon click, a menu
  click and a shortcut are therefore one call, and Show Rays has one checked state everywhere.
  The menu bar stays for keyboard use, and now shows the same icons.
- **Command palette**: "Search commands" in the ribbon's tab row. **Ctrl+Shift+P** focuses it; it
  completes on any part of a command's title, and Enter runs the one command the text names.
- **The Analysis tab's Plots group** is the analysis picker (0899): the same "Select plots" menu,
  Update and WFront 3D. Its caption follows the model's selection through
  `AnalysisToolbar.caption_listeners`. The picker's own toolbar row is hidden, so the ribbon does
  not stack a second strip on top of it.
- **`qt/icons.py`**: 42 line icons drawn for this project on a 24x24 grid, kept as SVG text in the
  code. They are recoloured from the palette's text colour (plus an orange "light" accent, a
  lighter one on dark themes) and rendered at 2x for HiDPI. Each draws its optics: a
  beam-splitter cube with its diagonal, a Gaussian waist, grating grooves with diffracted orders,
  and so on.
- **Quit is deliberately off the ribbon** (`RIBBON_EXCLUDED`, with the reason): it closes the
  application, so it stays File menu / Ctrl+Q only, never one stray click away.

## Height: the ribbon folds on short screens

An open ribbon is ~114 px tall. On the 1000-px screen the guards use, it took the 3D view from
422 px to 358 px, under phase 707's 400-px floor. So:
- below 1100 px of available screen height it starts **folded** to its tab row (30 px);
- a tab click drops that tab's page over the window as a pop-up, which closes once a command runs
  or on a click elsewhere;
- a double-click on a tab pins the ribbon open, or folds it again.

Folded, the 3D view is 417 px.

## Two bugs its guard caught

- **Show Rays from the ribbon said "hidden" while the rays stayed on.** The button emitted the
  action's `triggered` by hand, and the connected handler received its DEFAULT argument (True).
  The button now calls `action.trigger()`, as the menu does: that toggles the action and hands the
  handler the new state. The button mirrors `action.toggled`.
- **Ctrl+Shift+P unfolded the ribbon**, costing the 3D view its height just to type a command.
  The palette lives in the tab row, which stays visible when folded, so it no longer unfolds.

## Guard

`validate_qt_ribbon`, penta phase **714**. It runs in a real Qt shell on om05a_folded:
- **C**: the ribbon (40) plus its exclusions (1) cover all 41 actions; nothing appears twice;
  every icon draws; no two icons render the same.
- **B**: each of the 39 plain ribbon buttons reaches ITS OWN action. Each action's `trigger` is
  spied, so no dialog opens.
- **R**: a ribbon click unchecks the action AND hides all 106 ray actors; the menu route checks
  the ribbon button again.
- **A**: the picker carries the same menu, and its caption goes "Select plots" -> "Plots: 1" ->
  back, with the model's selection.
- **P**: Ctrl+Shift+P focuses the palette; "gaussian beam" runs the Gaussian Beam action;
  "report", which several commands share, runs nothing.
- **F**: on the 1000-px screen the ribbon starts folded and the 3D view is 417 px; a pop-up opens,
  and running a command closes it.

Checked by eye: the four tab pages as pop-ups, and a 48-px sheet of all 42 icons.
