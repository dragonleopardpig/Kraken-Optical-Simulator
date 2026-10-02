# 0941 -- "Add Component to Current Path View" recursed forever (both shells, since 0888)

Found by the Qt menu-parity probe (every Tk menu-bar command run inside the Qt shell). Two menu
items raised `RecursionError`:
- Actions -> Component to Current Path View...
- Path -> Add Component to Current Path View...

They do the same in the Tk editor; they were not Qt bugs.

## Cause

The panel classes (`MainXxxDialog`) forward any attribute they lack back to the editor through
`__getattr__`. Commit 0f4b158c (bugs/0888, 2026-09-25) moved the Path Component form to
`row_forms/path_component.py` and deleted the panel's `open_current_path_component_placement`.
The editor kept its one-line delegation, `self._main_path_component_placement_dialog()
.open_current_path_component_placement()`, which now reached the editor's own method again,
forever.

## Fix

- Restored the panel method: refresh the Path-view choices, ask for a traced Path view if none is
  chosen, then open the placement form on that branch.
- Its messages, and `open_arm_path_component_placement`'s, go through `host_of`, so they appear
  in whichever shell is running.
- Removed the editor's `_glass_catalog_records`: a dead wrapper (no callers) delegating to a panel
  method that 0882 moved out, i.e. the same recursion waiting for a caller.

## Guard

`validate_editor_panel_delegations`, penta phase **717**:
- **S**: scans all 135 `self._main_<panel>().<method>(` delegations in the editor's mixins and
  requires the panel class to define the method itself, not reach it through `__getattr__`.
  Before the fix it flagged exactly these two.
- **R**: in a real Tk editor and in the real Qt shell on om05a_folded, the command returns
  without error and asks "Choose a traced Path view first...".

Gate: phases 477, 654, 655, 676 and 717 pass; the ungated `validate_phase6_path_workbench` passes
before and after.

## Still open (menu parity)

In the Qt shell the placement form itself still renders through Tk (`render_row_form`). It needs a
Qt action that opens the same form model, like the other row forms.
