# 0925 -- placement drags in the Qt shell (phase 5d)

5d was planned as the risky port: drag, move, rotate, snap, glue -- the densest bug arc (0433
stay-put, 0503 glue, 0693 frames), ~62 inspector methods. Since 0906 the Qt shell hosts the REAL
inspector and feeds it Qt input through the same handlers, so the question was not "port the
drags" but "does every drag, driven by real Qt input, do what the same gesture does through
`dispatch_viewport_event`" (which 0905 proved equal to the Tk bindings).

## Measured

**Static audit.** Across the 195 drag / gizmo / handle / snap / glue / carry / placement methods
of `Kraken3DInspector`, the only Tk-bound calls were:
- the carry-hold timers, already on `host_of(self)` (0906);
- the legacy "Place/Orient CAD/STL Solid" side panel.

The services on the drag path held only dialog code.

**Dynamic proof**, in a real Qt shell on a promoted 42779 pentaprism. Each gesture ran with Qt
events, then dispatched, on the same body, and the **deltas** were compared:

| gesture | Qt input | dispatched |
|---|---|---|
| +Z move-handle drag (press on the handle's pixel, 4 x 20 px along its screen axis) | desp +7.928 mm | +7.928 mm |
| Y rotate-handle click | 90.0 deg | the same rotation matrix |
| STEP-overlay long-press carry (430 ms hold, then 60 px) | +4.32 mm | +4.32 mm |
| promoted-row long-press carry (press on the body away from the gizmo) | +4.32 mm | +4.32 mm |

A carry arms only with "Move/Rotate whole body" ON (bugs/0425). A probe that forgot that saw no
carry in either mode, which confirms the rule is shell-independent.

## The one Tk-only piece: the CAD/STL placement panel

`start_stl_placement` built a `ttk.Frame` inside the inspector's Tk window. Under the shell that
window is withdrawn, so the panel was never seen. Yet `_stl_placement_panel_visible()`
(`winfo_exists`) said it was open, and forced the scene placement handles on.

- **`row_forms/stl_placement.py`**: the same panel as a `RowForm`:
  - the "Fit local axis to +Z" choice, whose `on_change` sets the inspector's `stl_axis_var`;
  - the pose status line;
  - actions for Fit Axis, X/Y/Z -Rot/+Rot (the toolbar rotation step), Center X/Y, Front On Row
    and Done -> 2D.

  Each action calls the same inspector method as the Tk button and re-reads the status. The form
  stays open across actions; Done sets `close_after`.
- **`InspectorView.show_row_form`**: a new shell seam, installed like `show_context_menu`
  (0907). It shows the form as a non-modal `RowFormDialog` and runs `on_close` however the dialog
  goes. Under a shell, `show_stl_placement_handler` routes there. `_stl_placement_panel_visible`
  and `_close_stl_placement_handler` know the dialog. Tk is unchanged.
- **Done -> 2D** ends in `_on_close()`, which tears down the WHOLE inspector. In Tk that closes
  the separate 3D window, which is what "back to 2D" means. In the shell the inspector is a dock
  of the main window, so a shell-hosted inspector now closes only the placement.
- **`RowFormDialog.run_action`** honours `form.state["close_after"]` for every form, not only
  record lists. No non-record form set it before, so nothing else changes.

## Still differs (not 5d)

A non-record form's action closes the Tk view (`panels/row_form_view.run_action`: "a row form's
action is terminal") but leaves the Qt dialog open. The placement form is Qt-only for now, so this
does not bite yet. It would if Tk ever renders it through the shared row-form view.

## Guard

`validate_open3d_qt_5d_placement`, penta phase **704**:
- **M, R, C, W**: the four gestures above, Qt vs dispatched.
- **P**: the assistant opens as a Qt dialog (no Tk frame). Its actions turn, seat and fit the
  solid and refresh the status. The axis choice reaches the inspector. Done closes the dialog and
  keeps the inspector.
- **S** (static): every Tk panel button's method is called by the form.

## Gate

- The full 3-shard gate ran at 702/703. Phase 696 (`validate_step_carry_open3d_smoke`: "STEP
  rotation handles were not present during carry mode with the whole-body toggle ON") failed
  once, in shard 2, which spawns isolated child apps while two other shards load the CPU.
- It then passed 5 of 5 isolated runs: 2 with this change, 2 with it stashed, and 1 through the
  gate harness (`--phases 696`).
- So it is **load-dependent, not 0925**. It is the first flake seen under the parallel shard
  runner. Suspect a render/pump race in the handle check, and watch for it on the next full run.
