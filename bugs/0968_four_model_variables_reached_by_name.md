# 0968 -- four model variables a Tk panel made, reached only by name

Phase 7c of the Qt migration (docs/design_qt_migration.md), first half.

## What was wrong

`model_variables.MODEL_VARIABLES` declares the variables Tk panels create and model code uses, so
that a shell with no Tk panel still has them (bugs/0852). Its guard keeps the table complete by
scanning model code for ATTRIBUTE uses of each panel-made name.

Model code also reaches a variable by NAME: `self.__dict__.get("x_var")` (written that way so a
stripped snapshot editor does not recurse through Tk's `__getattr__`, bugs/0041),
`getattr(editor, "x_var", None)`, and a catalogue's `"editor.x_var"`. The scan never saw those.
bugs/0901 found one by accident (`source_direction_preset_var`). Teaching the scan to see them
found four more:

| Variable | Made by | Reached from |
|---|---|---|
| `atmosphere_summary_var` | `panels/main_atmosphere_panel.py` | the model's `_update_atmosphere_summary`; the Qt Atmospheric Settings dialog |
| `source_summary_var` | `panels/main_source_controls.py` | the model's `_update_source_summary` |
| `trace_state_badge_var` | `panels/main_window.py` | the model's `_sync_trace_state_badge` |
| `show_layout_2d_var` | `panels/main_window.py` | the model's `_show_layout_2d` and `toggle_layout_2d`; the Qt 2D plot toolbar's "Layout pane" check |

Each reader returns quietly when the variable is missing. So with no Tk panel the two summaries
and the trace badge would be computed and dropped, and the Qt shell's own views -- the atmosphere
dialog's summary line, the 2D toolbar's check -- would have nothing to bind to. Nothing shows this
today only because the Qt shell still builds every Tk panel, hidden (phase 7f removes that).

The design doc said seven. Three of those are made by the editor or the inspector through the UI
host (`emit_full_ray_var`, `nonseq_energy_probability_var`, `show_terminal_diagnostics_var`), so
they exist whatever the shell and were never part of this.

## Change

- **`model_variables.py`:** the four are declared, with the values a real editor holds after
  start-up (measured). The registry is 69 variables.
- **The guard's scan** (`validate_open3d_0852_model_variables`, phase 631) counts a panel-made
  name used as a STRING outside the panels as a use. With the four not yet declared it failed on
  exactly those four.

Under Tk nothing changes: the panels make these variables first, and the registry never replaces
an existing one.

## Guard: phase 631, two claims changed

- **C** (completeness) now includes reaching a variable by name.
- **D** (new): on an owner with NO Tk panel, the real `_update_atmosphere_summary`,
  `_update_source_summary` and `_sync_trace_state_badge` write into the registry's variables, and
  `_show_layout_2d` follows the switch; on an owner without the four, the same three writes go
  nowhere.
- R1 / R3: 69 variables, and a real editor holds exactly the registry's value for each.

## Checks (2026-10-06, X299-SSD; every run alone, at low priority)

**Mutations: 7 of 7 caught**, each restored from a copy, the tree clean afterwards.

| Mutation | Caught by |
|---|---|
| one of the four is not declared | R1, C, D |
| one is not declared AND the count in the guard is adjusted to hide it | C, D -- the scan by name is what catches it |
| a declared start-up value is wrong | R3 |
| the source summary is not written; the atmosphere summary is not written | D (and R3: the real editor's value drifts) |
| the trace badge is not written | D |
| the 2D-layout switch is not read from its variable | D |

**Neighbouring guards, all pass, none skipped:** the UI host seam (0851) and the three guards that
build an editor on a scripted host (0871, 0872, 0904 -- they now get the four variables too), the
interaction contract (655), and the two Qt views that read these variables: Atmospheric Settings
(726) and the 2D plot panel (733).

Phase 631 was already in the baseline and stays a pass. The full Tk gate is owed since 8403abde.

