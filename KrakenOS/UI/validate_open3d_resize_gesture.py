"""Guard: the drag-a-face-to-resize gesture planner (bugs/0064 step 3).

Step 3 of the resize request is the gesture: "click the highlighted surface ->
drag the arrow -> the thickness measurement grows -> click to confirm -> direct
edit the thickness".  ``open3d_resize_gesture`` is the pure planning core behind
it: it turns a grabbed-face normal + a drag distance into the exact resize spec
(``target_extents`` / ``anchor_axis`` / ``anchor_at_max`` / ``coupled``) the
existing apply path consumes -- so the gesture and the numeric popup land on one
codepath.

This guard is fully DISPLAY-FREE.  It exercises the pure planner (face -> axis,
which end is anchored, splitter coupling vs free depth, drag -> clamped extent)
and then feeds the planner's output through the real geometry kernel
(``open3d_solid_resize``) on a synthetic cube, proving the resulting scale:

* moves the grabbed face and holds the opposite face fixed,
* hits the intended new extents, and
* (the killer check) keeps the 45-deg coating at 45 deg for a coupled
  cross-section drag -- which a single-axis cross-section change would break.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_resize_gesture

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import copy

import numpy as np


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    from KrakenOS.UI.services.open3d_resize_gesture import (
        MIN_EXTENT_MM,
        dominant_axis,
        new_extent_for_drag,
        plan_face_drag,
        readout_label,
        resolve_resize_drag,
        target_extents_for_extent,
    )
    from KrakenOS.UI.services.open3d_solid_resize import (
        ResizeAxes,
        anchor_point_for_fixed_face,
        axis_scales_for_extents,
        extents_of,
        is_coating_preserved,
        resize_points,
    )

    # A cube beam-splitter: 45-deg coating diagonal spans X,Y; Z is the free
    # depth axis (mirrors the real vendor 50 mm cube).
    cube_axes = ResizeAxes(free_axis=2, coupled_axes=(0, 1), coupling_normal=(0.707107, 0.707107, 0.0))
    cube_extents = [50.0, 50.0, 50.0]

    # --- A. plan_face_drag: face -> axis / anchor end / coupling --------------
    plan_px = plan_face_drag((1.0, 0.0, 0.0), cube_axes)
    ok(plan_px.axis == 0 and plan_px.anchor_axis == 0 and plan_px.anchor_at_max is False,
       f"A1: +X cross-section face grows axis 0, anchors the min (opposite) face "
       f"(axis={plan_px.axis}, at_max={plan_px.anchor_at_max})")
    ok(plan_px.coupled_axes == (0, 1) and plan_px.couples_pair and plan_px.is_splitter,
       f"A1b: +X drag couples the X,Y cross-section pair (got {plan_px.coupled_axes})")

    plan_pz = plan_face_drag((0.0, 0.0, 1.0), cube_axes)
    ok(plan_pz.axis == 2 and plan_pz.coupled_axes == (2,) and not plan_pz.couples_pair,
       f"A2: +Z free/depth face grows axis 2 alone (got {plan_pz.coupled_axes})")

    plan_nx = plan_face_drag((-1.0, 0.0, 0.0), cube_axes)
    ok(plan_nx.axis == 0 and plan_nx.anchor_at_max is True,
       f"A3: -X face grabbed -> the max (opposite) face is held fixed (at_max={plan_nx.anchor_at_max})")

    ok(dominant_axis((0.6, 0.5, 0.1)) == 0 and dominant_axis((0.1, 0.2, 0.9)) == 2,
       "A4: dominant_axis picks the largest-magnitude normal component")

    plain_plan = plan_face_drag((0.0, 1.0, 0.0), None)
    ok(plain_plan.axis == 1 and plain_plan.coupled_axes == (1,) and not plain_plan.is_splitter,
       f"A5: a plain solid (no coating) grows only the dragged axis (got {plain_plan.coupled_axes})")

    # --- B. drag distance -> extent + target_extents -------------------------
    ext_px = new_extent_for_drag(cube_extents, plan_px, 5.0)
    ok(abs(ext_px - 55.0) < 1e-9, f"B1: +X face +5 mm -> 55 mm (got {ext_px})")
    ok(target_extents_for_extent(plan_px, ext_px) == [55.0, 55.0, None],
       "B1b: a cross-section drag writes BOTH coupled axes to 55 (square), depth None")

    ext_pz = new_extent_for_drag(cube_extents, plan_pz, 28.0)
    ok(target_extents_for_extent(plan_pz, ext_pz) == [None, None, 78.0],
       f"B2: +Z depth +28 mm -> [None, None, 78] (got extent {ext_pz})")

    ext_clamp = new_extent_for_drag(cube_extents, plan_px, -100.0)
    ok(abs(ext_clamp - MIN_EXTENT_MM) < 1e-9,
       f"B3: a huge inward drag clamps to MIN_EXTENT_MM={MIN_EXTENT_MM}, never collapses (got {ext_clamp})")

    plain_ext = new_extent_for_drag([40.0, 30.0, 20.0], plain_plan, 10.0)
    ok(abs(plain_ext - 40.0) < 1e-9 and target_extents_for_extent(plain_plan, plain_ext) == [None, 40.0, None],
       f"B4: plain [40,30,20] +Y +10 -> [None, 40, None] (got extent {plain_ext})")

    # --- C. resolve_resize_drag: the apply-ready tuple -----------------------
    targets, anchor_axis, anchor_at_max, coupled, new_ext = resolve_resize_drag(
        cube_extents, (1.0, 0.0, 0.0), cube_axes, 5.0
    )
    ok(targets == [55.0, 55.0, None] and anchor_axis == 0 and anchor_at_max is False
       and coupled is True and abs(new_ext - 55.0) < 1e-9,
       "C1: resolve(+X,+5) == ([55,55,None], anchor 0, at_max False, coupled True, 55)")

    targets_nz, axis_nz, atmax_nz, coupled_nz, _ = resolve_resize_drag(
        cube_extents, (0.0, 0.0, -1.0), cube_axes, 28.0
    )
    ok(targets_nz == [None, None, 78.0] and axis_nz == 2 and atmax_nz is True and coupled_nz is True,
       "C2: resolve(-Z,+28) anchors the +Z face (at_max True), depth -> 78")

    targets_pl, axis_pl, atmax_pl, coupled_pl, ext_pl = resolve_resize_drag(
        [40.0, 30.0, 20.0], (0.0, 1.0, 0.0), None, 10.0
    )
    ok(targets_pl == [None, 40.0, None] and axis_pl == 1 and coupled_pl is False,
       "C3: resolve on a plain solid -> single-axis target, coupled False")

    ok(isinstance(targets, list) and len(targets) == 3 and isinstance(anchor_axis, int)
       and isinstance(anchor_at_max, bool) and isinstance(coupled, bool),
       "C4: the resolved tuple matches the _apply_step_overlay_resize_solve signature shape")

    # --- D. live readout label -----------------------------------------------
    ok(readout_label(plan_px, 55.0) == "X×Y = 55 mm",
       f"D1: coupled readout names both axes (got {readout_label(plan_px, 55.0)!r})")
    ok(readout_label(plan_pz, 78.0) == "Z = 78 mm",
       f"D2: single-axis readout names one axis (got {readout_label(plan_pz, 78.0)!r})")

    # --- E. purity ------------------------------------------------------------
    src_ext = [50.0, 50.0, 50.0]
    src_norm = [1.0, 0.0, 0.0]
    src_ext_snap = copy.deepcopy(src_ext)
    src_norm_snap = copy.deepcopy(src_norm)
    resolve_resize_drag(src_ext, src_norm, cube_axes, 5.0)
    ok(src_ext == src_ext_snap and src_norm == src_norm_snap,
       "E1: the planner never mutates the caller's extents / normal")

    # --- F. geometry integration (killer): feed the plan through the real kernel
    # An axis-aligned 50 mm cube point cloud (the 8 corners of [0,50]^3).
    corners = np.array(
        [[x, y, z] for x in (0.0, 50.0) for y in (0.0, 50.0) for z in (0.0, 50.0)],
        dtype=float,
    )

    def _apply_plan(points, targets_, anchor_axis_, anchor_at_max_):
        wanted = np.array([t if t else 0.0 for t in targets_], dtype=float)
        scales = axis_scales_for_extents(extents_of(points), wanted)
        lo = np.min(points, axis=0)
        hi = np.max(points, axis=0)
        anchor = anchor_point_for_fixed_face(lo, hi, int(anchor_axis_), bool(anchor_at_max_))
        return resize_points(points, scales, anchor), scales

    # +X coupled drag of +5 -> 55x55x50, min-X face held fixed, coating still 45.
    t_px, ax_px, am_px, _, _ = resolve_resize_drag(cube_extents, (1.0, 0.0, 0.0), cube_axes, 5.0)
    moved_px, scales_px = _apply_plan(corners, t_px, ax_px, am_px)
    ok(np.allclose(extents_of(moved_px), [55.0, 55.0, 50.0]),
       f"F1: +X coupled drag yields 55x55x50 (got {extents_of(moved_px)})")
    ok(abs(float(np.min(moved_px[:, 0])) - 0.0) < 1e-9,
       f"F1b: the opposite (min-X) face stays put at x=0 (got {float(np.min(moved_px[:, 0]))})")
    ok(is_coating_preserved(cube_axes.coupling_normal, scales_px),
       "F1c (killer): the coupled drag keeps the 45-deg coating at 45 deg")

    # The same cross-section change applied to ONE axis would break the coating
    # -- proving the coupling the planner enforces is load-bearing, not cosmetic.
    one_axis_scales = axis_scales_for_extents([50.0, 50.0, 50.0], [55.0, 0.0, 0.0])
    ok(not is_coating_preserved(cube_axes.coupling_normal, one_axis_scales),
       "F1d: a single-axis cross-section change (which the planner never emits) WOULD break the coating")

    # -X drag holds the max-X face fixed at x=50.
    t_nx, ax_nx, am_nx, _, _ = resolve_resize_drag(cube_extents, (-1.0, 0.0, 0.0), cube_axes, 5.0)
    moved_nx, _ = _apply_plan(corners, t_nx, ax_nx, am_nx)
    ok(abs(float(np.max(moved_nx[:, 0])) - 50.0) < 1e-9 and np.allclose(extents_of(moved_nx), [55.0, 55.0, 50.0]),
       f"F2: -X drag holds the max-X face at x=50, still 55x55x50 (got max-x {float(np.max(moved_nx[:, 0]))})")

    # +Z depth drag -> 50x50x78, coating preserved (free axis is unconstrained).
    t_pz, ax_pz, am_pz, _, _ = resolve_resize_drag(cube_extents, (0.0, 0.0, 1.0), cube_axes, 28.0)
    moved_pz, scales_pz = _apply_plan(corners, t_pz, ax_pz, am_pz)
    ok(np.allclose(extents_of(moved_pz), [50.0, 50.0, 78.0]) and is_coating_preserved(cube_axes.coupling_normal, scales_pz),
       f"F3: +Z depth drag yields 50x50x78 with the coating preserved (got {extents_of(moved_pz)})")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Resize-gesture planner validation passed.")
        return 0
    print("Resize-gesture planner validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
