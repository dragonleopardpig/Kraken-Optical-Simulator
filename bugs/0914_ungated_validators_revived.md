# 0914 -- four ungated validators revived (and one measured as machine-dependent)

These failed identically at HEAD. Each failure was a stale expectation, not a product bug. The
product bugs found along the way are bugs/0909.

## `validate_open3d_ray_toggle_scene_retention`

- **The "opacity 0.75" was the SELECTED-row pink highlight.** Promotion selects the new row, which
  is the right UX. The check now asserts the highlight while the row is selected, then clears the
  selection (`_clear_table_selection`; `_select_table_indices([])` is a no-op by design) and
  checks the glass is 0.20-0.38.
- **The status line.** The STEP display-cache warm-up writes its progress into the same status
  line, so the check waits, up to 180 s, for the scene report.

## `validate_open3d_interaction_workflows`

- **Step 5.** It now turns the whole-body toggle on, as a user must since bugs/0338.
- **Step 9's timing budgets are MACHINE-DEPENDENT.** On M90aPro, the harness AS OF the commit
  that set the budgets (5f3040b7, 2026-05-30), run on THAT code, took 5513 / 7280 / 12141 ms: it
  blows its own 8000 ms budget. The budgets were calibrated on the desktop.
- **This change is not the cause.** An A/B with only `open3d_scene_refresh.py` reverted to HEAD
  measured 8924 / 13086 / 16020 ms, against 8350 / 12293 ms with it.
- **Where the time goes.** A profile puts it in the non-sequential trace (`NsTrace`: 64 s of the
  113 s spent in the main process). The budgets are left alone: raising them would hide a real
  regression. Settle it with a desktop run.

## `validate_open3d_penta_cascade_prism_by_prism`

It read the chief ray AFTER switching rays off. A rays-off refresh is bodies-only by design, so
every step looked truncated. It now reads the chief ray while rays are on, and the exit direction
turns at every fold.

## `validate_penta_mirror_3d_cascade` (known failing since June)

- **The names.** The guard named faces in the numbering of the old planar clustering. The native
  STEP import (58f0e215) numbers faces its own way and qualifies them (`S001/F005`). So the names
  first did not resolve, and once qualified they pointed at the wrong physical faces: the snap
  guided by a side face, the bevel and exit got the mirror coating, and every ray refracted
  straight through.
- **Faces are now found by GEOMETRY**, invariant under pose:
  - the two side faces are the parallel pair (dot -1);
  - entrance and exit are the one perpendicular pair in the section (dot 0);
  - the mirrors are the pair 135 degrees apart among the remaining three.
- **Result.** All 10 rays go F005 refraction -> F002 reflection -> F004 reflection -> F001
  refraction, and exit along +X as requested.
