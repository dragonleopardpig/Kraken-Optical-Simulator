# 0433 — Stay-put on fold-element removal + rubber-band select → snap-to-axis

**Flag `flag_20260724_203830_626`** ("Initial layout", `attachment/machine_vision_AZ85_RA_Mirror.py`) +
the user's workflow description. The temporary first RA mirror (overlapping the LED STEP) exists only to
fold the imaging axis; the user will delete it, add a parametric **BS plate** (right-click on the LED),
orient/seat/glue it manually, then re-attach the imaging chain to the BS reflect axis:

> *5) I would like all the elements stay where they are when I change BS (or mirror or any element that
> introduces another optical axis). 6) After BS successfully placed, I can just drag a rubber band to
> select all elements to snap to the new optical axis (which include the second RA mirror with another
> folded optical axis).*

This **supersedes bugs/0431 slice 2c** (trace-driven retain-on-swap): the auto-convergence there was
circular and headless-untestable; the user's manual two-step (freeze → rubber-band snap) is explicit,
robust, and reuses the shipped 0432 machinery. 0431 slice 2a (branch frame map, phase 347) stays as-is.

## Why elements collapse today (root cause)

Downstream rows persist only straight-axis params (desp/tilt ≈ 0); their folded WORLD poses are a
**derived override map** rebuilt on every refresh by `build_optical_solid_output_port_pose_overrides`
(`nonseq_output_ports.py:1493`). Deleting the fold mirror leaves no fold source → the walk emits **no
overrides** → plain station arithmetic stands = collapse. The collapse is the *absence* of overrides,
not an active re-write. The free-placed second mirror survives because promotion baked its world pose
into its own desp fields (+ `StepOverlayPromotion.center_world` pin marker,
`_free_placed_solid_pinned_pose` `nonseq_output_ports.py:85`) — but that pin branch exists only for
optical-solid rows; plain lens/datum/aperture/Image rows cannot be pinned today. Lens/camera STEP CAD
bodies are seated straight-axis at datum/Image z-stations and folded by
`_optical_axis_fold_world_transform_for_row` (`layout_polyline_display.py:503`) reading the same
override map — they too snap back when the map empties.

## Slice A — stay-put freeze on fold-element removal/unpromote

**Mechanism: removal-time world-pose bake**, the proven 0432 recipe (`move_axis_downstream_to_axis`,
`scene_placement_commands.py:4861-4868`), applied with R = identity:

1. **Capture (pre-mutation)**: gate = any removed/unpromoted row satisfies
   `_row_is_promoted_mirror_fold` (`paraxial_tools.py:79`) AND ≥1 surviving downstream row has a
   fold-derived override. Snapshot every surviving downstream row's current world center+rotation
   (override entry if present, else station+desp+tilts) and the lens/camera STEP fold transforms.
2. **Bake (post-mutation)**: recompute stations (the removed rows' thickness shifts them — even the
   pinned mirror-2 must be re-baked in z); per row: `desp = world_center − station`, tilts from
   rotation, **AxisMove left at 0** (as-built deviation from "the 0432 recipe": the engine applies an
   upstream row's desp/tilt to followers only when that row has AxisMove=1 — consecutive absolutely
   baked rows with AxisMove=1 would COMPOUND in the built system; proven by the probe's built-system
   assertions. Flag: 0432's `move_axis_downstream_to_axis` sets 1.0 — slice C probes that). Rows a
   SURVIVING upstream fold still sweeps are skipped (**partial-removal stand-down**: deleting only
   mirror-2 leaves fold-follow in charge; an absolute bake there would double-transform). Then the
   **explicit STEP carry** (0432 `:4894-4930` pattern): compose the anchor row's fold rotation into the
   per-label rotation settings and re-derive the placement offset from the re-seated mesh, because
   baked rows alone leave `_optical_axis_fold_world_transform_for_row` = None and the CAD bodies would
   detach. Known transient divergences (probe-asserted): TRANS vs drawn-mesh rotation conventions
   differ for the folded tilt family, and rows behind the parked mirror-2 sit its thickness short in
   the BUILT chain (off-beam neutralization, 0065/0226) — display/snap poses are exact; the user
   re-solves after the snap.

**Hook points** (all already open with `_begin_history_capture`, so freeze+delete = one undo):
`delete_optical_step_rows` (`layout_table_workbench.py:4147`, browser Delete / Delete key — the likely
user path), `delete_selected` (`:4135`, canvas Row Actions / 2D table), and
`unpromote_optical_solid_to_overlay` (`step_overlay_promotion.py:1489`).

**Scope decisions**: freeze fires ONLY on removal/unpromote of a fold element. Re-aiming/dragging a
mirror keeps the shipped fold-follow behavior (penta-encoded 0185–0242); BS resize/replace/re-aim never
re-placed downstream anyway (BS is never a fold source, 0398). The frozen chain draws **no folded axis
guide** (guides are derived from overrides) — acceptable transient state; the snap does not need one
(slice C infers the entry leg from row centers). Synthetic frozen-leg guides deferred.

**Verification must use the BUILT system** (surface world transforms), not station+desp arithmetic —
this also proves the AxisMove propagation semantics of the bake (s1 gotcha: promotion keeps AxisMove=0,
0432 sets 1.0).

## Slice B — rubber-band select in the 3D view

Plain-left drag is camera orbit and Shift+left is pan, so this is an **armed pick mode** (the 0432
template): Place menu → **"Select Elements (Rubber Band)"** → left-drag a screen rectangle → on release
the rows whose (fold-aware) world centers project inside the rect fill `_picked_row_indices` via
`_set_row_highlights` — after which the existing "Snap Selected to Optical Axis" / "Add Selected to
Assembly" flows work unchanged. A chained "Select + Snap" variant arms the axis pick immediately on
release (the user's exact gesture sequence). Note: the 0432 3D Shift-click accumulate path is
**unreachable from real mouse input** (`<Shift-B1>` is rebound to pan; `set_event_info` hard-codes
shift=0) — the rubber band is the first working bulk multi-select; the inspector comment at `:7987`
already names it the proper next build.

Details: rectangle drawn from `left_motion` (during B1 drag only `<B1-Motion>` fires), measure-preview
clear/redraw lifecycle (`_refresh_measure_preview` pattern); containment = per-row world center
(fold-override-aware, NOT bare station+desp) → `_world_to_display_2d`, Tk y-flip via
`_tk_xy_to_vtk_display_xy`; Object row excluded (never movable, 0432 convention); spacer/datum rows
with no actors follow their chain via the snap, lens/camera STEP bodies get `_set_step_highlight_set`
when their anchor rows are selected. Sub-threshold (< 8 px) release degrades to the normal click pick.
New mode registered in **all four**: `cancel_active_3d_operation`, `_active_3d_operation_labels`,
`_active_mode_badge_text`, `derive_interaction_mode` — and the 0432 omission (snap/axis-move modes
missing from those four, so Esc could not cancel them) is backfilled here. New bindings call
`record_mouse` for flag replay.

## Slice C — snap must survive a fold INSIDE the selection

`snap_rows_to_axis` (`scene_placement_commands.py:4757`) infers the selection's current axis from the
first→last **along-axis** members. A selection spanning two legs (lens rows on the old fold leg +
mirror-2 + camera on mirror-2's exit leg — exactly the user's step 6) gets a **skewed** inferred axis:
fold solids are excluded from the fit but the second-leg followers are ordinary rows and DO enter it →
the rigid move lands misrotated. Fix: when the selection contains a promoted fold solid, fit the old
axis over along-axis members **upstream of the first fold solid in the selection** (row order = optical
order); fallback to current behavior when fewer than 2 such members. Also verify (probe) the suspected
STEP-follow pivot mismatch in the explicit-rows path: rows pivot on the selection origin (`:4856`) but
the STEP carry pivots on the branch point (`:4909`) — if real, carry with the same pivot as rows.

## Verification

- `bugs/probe_0433_stay_put_removal.py` — load AZ85, record built-system world poses (rows + STEP fold
  transforms), `delete_optical_step_rows` on mirror-1, assert every downstream pose unchanged (incl.
  pinned mirror-2 z and camera/lens bodies); unpromote variant. Display-free where possible; Tk parts
  headless via `xvfb-run -a .devenv/state/venv/bin/python`.
- `bugs/probe_0433_rubber_band_core.py` — pure containment core + selection-fill wiring.
- `bugs/probe_0433_snap_fold_in_selection.py` — freeze → synthetic `axis:global:split` record → select
  S3…S9 (incl. mirror-2) → snap → entry members on the new axis, mirror-2 fold + camera leg rigidly
  preserved, STEP bodies consistent with their rows.
- Penta phases (348–350) via standalone `validate_open3d_0433_*.py` validators (SKIP-on-env), then
  `python3 tools/penta_validator_gate.py --update-baseline` (kill stray Xvfb after).
- In-app eyeball owed: frozen visuals after delete, rubber-band rectangle, chained select+snap on the
  real BS scene.

## Files

- `KrakenOS/UI/services/scene_placement_commands.py` — capture/bake helpers (A), entry-leg fit (C).
- `KrakenOS/UI/services/layout_table_workbench.py`, `step_overlay_promotion.py` — removal hooks (A).
- `KrakenOS/UI/services/open3d_mouse_bindings.py`, `open3d_interaction.py`,
  `open3d_interaction_mode.py`, `KrakenOS/UI/open3d_inspector.py`,
  `KrakenOS/UI/panels/open3d_top_controls.py` — rubber band + mode registration (B).
- `bugs/probe_0433_*.py`, `KrakenOS/UI/validate_open3d_0433_*.py` — verification.
