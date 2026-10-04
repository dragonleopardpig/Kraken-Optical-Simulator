# 0954 -- Atmospheric Settings opens in the Qt shell: menu parity 75 of 75

Step 4 of "what is left" in `docs/design_qt_migration.md`. It was the Tk editor's last menu-bar
command without a Qt route, and the menu-parity guard's one known gap.

## Before

The Qt shell had no action for it, and the model's own command (`open_atmosphere_settings_dialog`)
opened a Tk window that the shell never shows.

## Change

The window is twelve of the model's own variables, a summary line the model writes, and three
buttons. The Qt shell already draws such a thing for the System, Source and Trace docks: a
catalogue says which variable each input edits and what to call after a change, and one class
(`SystemPanel`) renders any group.

- **A fourth group**, `ATMOSPHERE_CONTROLS` (`system_controls.py`): the observatory preset (the
  model's live list), the Atmos plot choice, and the ten numbers.
- **One list of the ten numbers.** `ATMOSPHERE_CONTROL_SPECS` moved from the Tk panel to the
  catalogue; the Tk panel imports it. The two windows cannot name a different set.
- **`apply_atmosphere_settings(show_plot=)`** on the editor is what Apply and "Apply + Atmos" do.
  They were lambdas inside the Tk window.
- **The Qt window** (`qt/dialogs/atmosphere_dialog.py`): the note, the form, the model's summary
  line, Apply / Apply + Atmos / Close. Not modal, and one instance: asked for again it comes back
  to the front, as the Tk one does.
- **A seam**, `show_atmosphere_settings`: the model's command opens the shell's window, so the Qt
  action is simply that command (`editor:open_atmosphere_settings_dialog`). It sits in the
  ribbon's Analysis > More list.

## Found on the way: the preset never named itself

Choosing an observatory preset set the status line to "Atmosphere preset set to CERRO_PARANAL.
Click Update." and then called the plot-stale mark, whose own line ("Display settings changed.
Click Update.") replaced it at once. Nobody ever saw the preset's message, in either shell. The
mark now comes first.

## Guards

**`validate_qt_atmosphere_settings` (phase 726):**
- **A:** the action is in Analysis > More; it opens one non-modal window; the ribbon again and the
  model's command both bring back the same window.
- **F:** twelve inputs in the catalogue's order, showing the model's values.
- **O:** a preset fills temperature, pressure, humidity, CO2, latitude and altitude from the site's
  record, in the model and in the window; the status line names the preset.
- **E:** a typed zenith angle lands in the model; the summary is the model's own line.
- **P:** Apply marks the plot stale and leaves the analyses alone; Apply + Atmos switches Atmos on,
  once.
- **N:** no Tk window.
- **T:** in the Tk app the Tk window still opens (2 lists, 10 entries, the same three buttons), and
  its title, note, labels and buttons equal the Qt window's.

**`validate_qt_menu_parity` (phase 718):** 75 Tk menu-bar commands, 75 routed in Qt, 0 known gaps.

**Mutation-checked:**
- no seam (the model's command opens the Tk window): the Qt half fails;
- a label reworded in the Qt catalogue only, Apply + Atmos not switching the analysis on, and the
  old status order: F, O, P and T fail.

**Other guards run:** the ribbon guard (94 of 94 actions reached) and the 3D interaction contract
(259 checks; it pins the Tk panel's source) pass.

**Seen by eye:** the Qt window rendered to PNG with a preset chosen.

## Gates

- **Full Tk gate at c45e41f6: 726 of 726 phases pass**, run in parallel with
  `tools/penta_parallel_gate.py --jobs 4` (bugs/0956): 44.5 min on M90aPro.
