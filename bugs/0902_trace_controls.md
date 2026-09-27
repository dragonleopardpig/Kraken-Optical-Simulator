# 0902 -- the trace/display inputs in Qt, and whose rules they are

The last 15 inputs of the Tk trace/display panel -- pupil factor, analysis surface, spot view,
scene trace, NS target and hit limit, folded reach, NS probabilistic split, wavefront style,
tolerance compare, show clipped rays, analysis path, detector bins, coherent sum and BField z --
are the third `system_controls` group, with a new `kind="bool"` for the two checkboxes. The Qt
shell gets a **Trace** dock from the same `SystemPanel` class.

That part was planned. Two things came with it that were not, and both were **model logic
living in Tk layout code**.

## Which inputs apply

45 `_register_left_mode_control(key, widget, lambda: ...)` calls carried the enable rules:

- **20 in the trace panel** -- object mode and the pupil factor only for the pupil/field source,
  tolerance compare only with that plot ticked, detector bins only with a detector plot,
  coherent sum only with a coherent one, BField z only with the branch-field plot, folded reach
  only when the scene can fold
- **25 in `_register_source_mode_controls`**, a *model service* -- the three field inputs and
  the pupil pattern only for the pupil/field source, the Gaussian fields split by input mode
  (waist + offset vs diameter + divergence), radius/seed/angular weight only for the random
  sources, position/direction/power only for a physical source, pupil r/θ only for the R-theta
  pattern

Because the rules were lambdas bound to Tk widgets, only the Tk panel knew them, and **the Qt
System and Source docks from 0900/0901 offered every input regardless.** The rules are named model
methods now (`_default_source_selected`, `_gaussian_waist_inputs_apply`,
`_detector_plot_selected`, …); `SystemControl.relevant` names one per input; both shells ask it.
The model tells a shell to re-read through a `show_control_state` seam, called at the end of every
`_sync_left_mode_controls` -- including when no Tk panel registered anything, which is exactly the
case a Tk-free shell will be in. `_register_source_mode_controls` became one table, keeping the
registration order that `_reflow_left_mode_controls` lays the panel out by.

## Lists the model fills

The analysis-surface and NS-target choices existed **only** as a Tk combobox's `"values"` --
and loading saved settings (`layout_settings`) and the scene-bundle display read them back *out of
that widget* to validate a surface name. They are `analysis_surface_options()` and
`analysis_branch_options()` now; the Tk menus are one consumer, and `SystemControl.choices_from`
points the Qt combos at the same lists.

## Constants

Eight names -- the folded detector policy and the wavefront styles -- were literals in
`layout_editor.py`. They moved into `system_controls.py` (which cannot import the editor) and the
editor re-exports them as the **same objects**, so `le.WAVEFRONT_PHASE_STYLE` still works.

## Two guard traps

- **A helper that built the whole list before returning.** `rule_states` ran through every state,
  then handed back the list, so the caller compared each state's rules with the views *as the
  last state left them* -- four "disagreements" that were the guard's, not the product's. It is a
  generator now, and says why.
- **0901 pinned the catalogue to exactly two groups.** This bug's third group broke that; the
  check now says "at least System and Source", which is the claim it was making.

## Guard

`KrakenOS/UI/validate_open3d_0902_trace_controls.py` (penta phase 690):

- **C** -- 15 trace inputs (2 checkboxes); all 46 inputs of the three groups are registered or
  made by the editor's constructor, so a shell without Tk panels has every one
- **K** -- every label and fixed list comes from the catalogue; the 8 moved constants are declared
  once and re-exported as the same objects
- **R1** -- no enable rule is a lambda in a layout any more, in either registration site
- **R2** -- over 25 states (5 source states × 5 plot selections) the Tk panel and the catalogue
  rule agree on every registered input, and **31 of the 32 ruled inputs were seen both on and
  off**. The one exception is waived by name: folded reach applies whenever the scene *can* fold,
  and `om05a_folded` always can
- **L** -- the surface list is model state, the Tk menu shows exactly it, and neither settings
  loading nor the scene-bundle display reads a widget to find it
- **Q1–Q3** -- the Qt Trace dock offers the model's live list; relevance follows the same rules in
  all three docks over the same 25 states; the checkboxes bind both ways

## Noted, not changed

`validate_penta_mirror_3d_cascade` calls the rewired sync and fails with *"OPTICAL STEP face F005
is not available for optical-axis snap"*. That is recorded pre-existing debt (known-failures
memory, bug 0074, `git stash`-confirmed in June), unrelated to this change, and in no penta phase.
