# 0944 -- "Add Component / Stock Lens to Current Path View" refused every Path view, in both shells

Found while routing the last menu-parity gaps (0942/0943) that end in a form. In the Tk editor, on
`beam_splitter_two_arm_doublets.py`, after a trace, with "Path 2: 50/50 splitter front to Reflect
path detector ..." chosen, both commands answered:

> Choose a traced Path view first, then run Actions -> Add Component to Current Path View.

The same happened on `beam_splitter_50_50_example.py`.

## Root cause

Since the automatic path graph, the Path view lists **legs** (`leg|auto_<hash>`). `_arm_catalog`
returns the leg catalogue whenever one exists, and every traced splitter scene has one. Both
commands asked `_branch_path_for_arm_key`, which only understands the older `path|<branch>` keys,
so every chosen view read as "no view".
- `_current_path_view_branch_path` had the same blind spot.
- The legs could not answer either. `build_auto_leg_entries_from_projected` walks the rays, each
  of which knows its `branch_path`, but it merged their segments without keeping which branches
  ran each leg.

## Fix

- **`auto_leg_graph`:** each leg now records the `branch_paths` of the rays that ran it.
- **`_placement_branch_path_for_arm_key(key) -> (branch, reason)`:**
  - a `path|` key resolves as before;
  - a leg resolves to the ONE non-primary traced branch running it;
  - otherwise it says why. For example: "This Path view is shared by 2 traced branches
    (S1:S1/reflect, S1:S1/transmit); choose a path that leaves a splitter." That is the input leg.
    The placement measures from the last splitter, so a shared leg has no single answer.
  - Both commands and `_current_path_view_branch_path` use it.

## The Qt shell

- **Path view selector.** The Qt shell had none, so these commands could never have worked there.
  The surface table toolbar now carries it, right-aligned as on the Tk toolbar. It offers the
  model's views (new `arm_view_options()`, which Tk's combobox refresh also uses), refreshes after
  every trace or model change, and a pick commits through the model's own `set_arm_view`.
- **Forms.** Both commands end in a toolkit-neutral form. `row_form_view.present_row_form` shows
  it wherever the running shell shows forms. The Qt main window installs the editor's
  `show_row_form` seam (a `RowFormDialog`); without that seam it is Tk's `render_row_form` as
  before.
  - The stock-lens importer takes the same path, and its last direct `messagebox` call goes
    through the host.
  - 17 other panels still call `render_row_form` directly. Those reached from a Qt action already
    have Qt routes, and the inspector-side ones are an audit for later.
- **Actions.** Edit → "Add Component to Current Path View..." and "Add Stock Lens to Current Path
  View...". They are menu + palette only: they act on the toolbar's Path view.

Menu parity is now 72 of 75. Left: the lens-drawing modal Tk window (2 commands) and Atmospheric
Settings.

## Guard: `validate_qt_menu_parity` (phase 718) gains V, L, W

Run on the two-arm doublets example:
- **V:** after Refresh Plot the toolbar offers exactly the model's 4 views. Picking Path 2 sets
  the model's view and selects that path's rows 7-10 in the Qt table.
- **L:** "Add Component..." opens a Qt dialog ("Add Traced Path Component"), and no Tk window is
  created. Apply inserts "Path R detector" on `S1:S1/reflect`, Path 2's branch, in the model and
  the Qt table. "Add Stock Lens..." opens its Qt dialog. Path 1 (the input leg) refuses through
  the host, naming the two branches.
- **W:** in the Tk editor, Path 2 opens both Tk forms.

**Mutation-checked:**
- The commands back on `_branch_path_for_arm_key`: L and W fail.
- The component panel back on Tk's `render_row_form`: L fails, with a Tk window created.
- Legs recording no branch paths: L and W fail.

**Also re-run, all pass:**
- The ungated validators that read the leg graph or Path views: auto_leg_graph, the Michelson and
  Mach-Zehnder case studies, phase6_path_workbench, optical_solid_path_fit, menu_smoke,
  folded_scanner_display_contract, layout_plot_controller, phase8_complete.
- The window's minimum width is unchanged (1117 px).

**Phase 655 (the 3D interaction contract).** It pinned the literal `render_row_form(` in both panels.
It now accepts `present_row_form(`, and additionally asserts that `present_row_form` itself falls back
to `render_row_form`. The claim is still "shown through the shared row-form view, never a hand-built
window".

**Gated:** phases 477, 634, 655, 670, 676, 691, 707, 714, 717, 718 pass.
