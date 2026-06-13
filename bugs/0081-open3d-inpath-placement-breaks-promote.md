# 0081 — Open 3D: in-path placement raised during live promote → "can't promote at all" (regression, hotfixed by kill-switch)

## Symptom (user)

> [flag_20260613_223352_483] direct assign partial reflecting surface also not working now.

State: the cube is still an `optical` STEP overlay, **no promoted row**
(`promoted_solid_rows = []`) — the promote **raised and aborted**.

## Root cause (my regression)

The bugs/0079 "in-path axial placement" (gap-split + trailing AIR spacer at the
solid's true Z) raised somewhere in the **live promote** wiring of
`promote_imported_step_to_optical_solid_row`, aborting the whole promote. bugs/0080
extended that placement to the **direct face-assign** right-click — the user's only
working promote path — so after 0080 *neither* promote worked. (The earlier
"Promote to Optical Element → no Face Editor" was the same raise on the other
path.)

The placement **planner** (`optical_chain_insert.plan_inpath_insertion`) is
unit-tested and does not raise, so the fault is in the live wiring (the gap-split
row mutation + spacer insert + the downstream `_normalize_special_rows` /
`_sync_table`, or the row build using the overridden `z_station`) — not reproduced
headlessly yet.

## Hotfix (this commit) — restore the promote

Module kill-switch `_INPATH_AXIAL_PLACEMENT_ENABLED = False` in
`step_overlay_promotion.py` gates the in-path block, so every promote falls back to
the historic (working) append path. The placement code + the `inpath_axial_placement`
callers stay in place (so the guard still verifies the capability); only the
runtime is disabled. **Trade-off:** the bugs/0079 focus/detector placement is inert
again (the cube's thickness shifts the detector) — but the user can promote.

## Next

Reproduce the raise with a **headless promote** (construct the editor, import a
STEP, promote with `inpath_axial_placement=True`, capture the traceback) — the gap
in 0079/0080 was testing only the planner, not the full live promote. Once the
exact raise is fixed and covered by a headless promote test, flip the kill-switch
back to True.

## Status: HOTFIXED (promote restored); placement re-enable pending the headless repro
