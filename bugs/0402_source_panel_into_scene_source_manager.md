# 0402 — the left Source panel folds into the Scene Source Manager

**Request:** "group all the Left Panel 'Source' into the 'Scene Source Manager' and a right-click
shortcut to the Right Panel 'Scene Source', and remove the whole Left Panel → Source. The child from
right panel 'Scene Source' still gets the right-click Edit Source." Chosen approach (via
AskUserQuestion): **Port fully into Manager** — nothing lost.

## What existed (three overlapping source UIs)

- **Left "Source" panel** (2D editor, `MainSourceControlsPanel`) — the single primary/imaging source,
  backed by Tk vars on the editor (`source_x_var`, `pupil_pattern_var`, …). The trace reads these via
  `_current_source_origin/direction/radius/cone`; a `Pupil / field` reference stays synced to them.
- **Scene Source Manager** (`MainSceneSourceManagerDialog`) — the multi-source collection editor
  (`layout_scene_source_specs`): add / delete / reorder / enable, plus aim-target, placement standoff,
  row order. Already a **near**-superset of the panel — but it lacked the panel's imaging-only knobs:
  pupil sampling (pattern / radial / angular) and the full Gaussian inputs (input mode, beam diameter,
  full divergence, waist side).
- **Right-panel "Scene Sources" group** (Open 3D browser) — already had "Add Illumination Source
  (LED)"; child rows already had "Edit Source…".

## Fix

**1. Manager becomes a true superset.** Added a Pupil-sampling section (pattern combobox + radial /
angular entries) and the missing Gaussian inputs (input-mode + waist-side comboboxes, beam-diameter +
full-divergence entries) to the Manager's Selected-Source form. Wired both ways: `load_form` seeds them
(snapping readonly comboboxes to a valid default like `model`/`angular_weight` do) and **`form_spec`
writes all seven keys**. The 0397-class trap: `form_spec` rebuilds the spec from scratch, so any
folded-in field it doesn't write would be silently dropped on every Save — the guard pins this.
`_default_scene_source_spec` seeds the seven keys so a brand-new source starts sane.

**2. Right-click shortcut.** The Open 3D "Scene Sources" group menu gains "Scene Source Manager…"; each
source row gains it too (preselecting that source) alongside the unchanged "Edit Source…".

**3. Left panel retired from view — but kept alive headlessly.** The panel's vars back imaging
source-0 that the trace + `Pupil/field` sync read, so it must still be **built**. It's now built into a
**hidden frame** (the same never-gridded pattern as `atmosphere_hidden_panel`) instead of a visible
`text="Source"` LabelFrame — the vars all exist, the trace is byte-for-byte unchanged, and the left
control stack reclaims the row (Display becomes the top). `_build_source_panel` still runs.

## Verification (`validate_open3d_source_panel_into_manager`, penta phase 330)

Display-free (getsource wiring + pure-logic):

| check | asserts |
|---|---|
| DEFAULT-SPEC | `_default_scene_source_spec` carries the 7 folded-in keys + they survive `normalize_scene_source_specs` |
| MANAGER-VARS | the form declares vars + widgets for all 7 controls |
| FORM-PERSIST | `form_spec` writes all 7 keys (no silent drop on Save) |
| CONSTRUCTOR | `__init__` accepts the 6 config kwargs; the factory passes the real PUPIL_/GAUSSIAN_ tuples |
| WIRING-PANEL | main_window still builds the panel, into a hidden frame; no visible "Source" LabelFrame |
| SHORTCUT | group + per-source "Scene Source Manager…"; per-source keeps "Edit Source…" |

All pass (baseline records phase 330 = pass). Regression check: `validate_3d_interaction_contract`
(17 pre-existing headless failures) and `validate_scene_sources` (pre-existing RecursionError) fail
**identically** on a clean committed worktree vs. this change — zero regressions added.
`validate_scene_row_mapping` passes.

## Files

- `KrakenOS/UI/panels/main_scene_source_manager_dialog.py` — pupil + Gaussian controls (vars, widgets,
  `form_spec`, `load_form` snapping) + 6 config kwargs.
- `KrakenOS/UI/services/source_modeling.py` — 7 folded-in keys in `_default_scene_source_spec`.
- `KrakenOS/UI/services/layout_shell_controls.py` — factory passes the pupil/Gaussian constants.
- `KrakenOS/UI/panels/open3d_step_admin.py` — group + per-source "Scene Source Manager…" shortcut.
- `KrakenOS/UI/panels/main_window.py` — Source panel built into a hidden frame.
- `KrakenOS/UI/validate_open3d_source_panel_into_manager.py` — guard (penta phase 330).

## Scope / next

The panel's **code** (`MainSourceControlsPanel`) is retained as the headless backing store for imaging
source-0 (lowest-risk; it's read by the trace + ~8 guards). A deeper teardown — deleting the class and
rerouting `_current_source_*` to read from a spec — is a possible follow-up if the vestigial code is
unwanted. `capture_manual_ui_screenshots.py` still crops a "gaussian_source_panel" region that no
longer shows the panel (manual utility, not a guard).

## In-app eyeball still owed

The left "Source" panel is gone (Display is now the top of the left column); right-click the Open 3D
"Scene Sources" group → "Scene Source Manager…" opens the full editor, which now has the Pupil-sampling
+ Gaussian sections; a source row still offers "Edit Source…".
