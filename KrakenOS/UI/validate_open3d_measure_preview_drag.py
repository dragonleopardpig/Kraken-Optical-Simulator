"""Guard: Measure live rubber-band preview + draggable lane handle (bugs/0115 Commit 2).

Commit 1 (validate_open3d_measure_center_snap_lanes) gave the Measure tool axis
snap + auto-stacked coplanar lanes. Commit 2 adds the two interactive pieces the
user asked for ("arrow on mouse" + adjustable spacing):

* **Live rubber-band preview** -- after the FIRST Measure pick, a dashed dimension
  line + live distance label follows the snapped point under the cursor until the
  second click (``_refresh_measure_preview`` / ``_clear_measure_preview``, driven
  from ``_update_measure_hover_highlight``).
* **Draggable lane handle** -- a pickable grab handle at each dimension midpoint
  (drawn in ``_refresh_measure_overlays`` and registered in
  ``_actor_measure_handle_map``). A left-press on a handle starts a perpendicular
  drag (``_measure_offset_drag_state_from_current_pick`` ->
  ``_apply_measure_offset_drag_motion`` -> ``_finish_measure_offset_drag``, wired
  into the Tk mouse bindings) that sets that segment's explicit ``seg['offset']``
  lane standoff. An explicit offset is kept out of lane numbering, so a dragged
  dimension never shifts the auto-stacked lanes.

``run_checks`` is display-free: the drag standoff math is exact (line-to-line
closest point), and the rest is SimpleNamespace fakes + source-string wiring.
Penta phase 106 runs ``run_checks`` only.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


def run_checks() -> list[tuple[str, bool, str]]:
    import numpy as np

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    results: list[tuple[str, bool, str]] = []

    # 1) the lane-handle drag standoff is the closest approach of the cursor ray to
    #    the segment's perpendicular offset direction (exact for any view), clamped
    #    to a small minimum so the dragged dimension never collapses onto the axis.
    fake = SimpleNamespace()
    fake._display_pick_ray = lambda xy: (
        np.array([-100.0, 70.0, 302.5]), np.array([1.0, 0.0, 0.0])
    )
    state = {"axis_mid": [0.0, 0.0, 302.5], "od": [0.0, 1.0, 0.0]}
    amt = Kraken3DInspector._measure_offset_amount_for_cursor(fake, state, (10, 10))
    # a cursor ray that passes through y=70 in the +Y offset direction -> 70 mm lane
    far_ok = amt is not None and abs(float(amt) - 70.0) < 1e-6
    fake._display_pick_ray = lambda xy: (
        np.array([-100.0, 5.0, 302.5]), np.array([1.0, 0.0, 0.0])
    )
    amt_near = Kraken3DInspector._measure_offset_amount_for_cursor(fake, state, (10, 10))
    clamp_ok = amt_near is not None and abs(float(amt_near) - 12.0) < 1e-6  # 5 mm -> clamp 12
    results.append(
        ("lane-handle drag standoff = closest-approach along +Y, clamped to 12 mm min",
         far_ok and clamp_ok, f"far={amt}, near(clamped)={amt_near}")
    )

    # 2) applying a drag writes the segment's explicit offset (and only that one);
    #    _measure_segment_by_id resolves the stable id.
    seg0 = {"p0": [0.0, 0.0, 275.0], "p1": [0.0, 0.0, 330.0],
            "r0": None, "dz0": 0.0, "r1": None, "dz1": 0.0, "n0": None, "id": 0}
    seg1 = {"p0": [0.0, 0.0, 300.0], "p1": [0.0, 0.0, 430.0],
            "r0": None, "dz0": 0.0, "r1": None, "dz1": 0.0, "n0": None, "id": 1}
    fake2 = SimpleNamespace(
        _measure_segments=[seg0, seg1],
        _measure_offset_drag_state={"seg_id": 0, "axis_mid": [0.0, 0.0, 302.5], "od": [0.0, 1.0, 0.0]},
        _resolve_measure_point=lambda p, r, dz: np.asarray(p, dtype=float).reshape(3),
        _display_pick_ray=lambda xy: (np.array([-100.0, 70.0, 302.5]), np.array([1.0, 0.0, 0.0])),
        _tk_xy_to_vtk_display_xy=lambda xy: xy,  # followup: motion flips Tk->VTK before the ray
        _refresh_measure_overlays=lambda: None,
    )
    fake2._measure_segment_by_id = lambda sid: Kraken3DInspector._measure_segment_by_id(fake2, sid)
    fake2._measure_offset_amount_for_cursor = (
        lambda st, xy: Kraken3DInspector._measure_offset_amount_for_cursor(fake2, st, xy)
    )
    Kraken3DInspector._apply_measure_offset_drag_motion(fake2, (10, 10))
    drag_ok = abs(float(seg0.get("offset", -1)) - 70.0) < 1e-6 and "offset" not in seg1
    results.append(
        ("_apply_measure_offset_drag_motion sets only the dragged segment's explicit offset",
         drag_ok, f"seg0_offset={seg0.get('offset')}, seg1_has_offset={'offset' in seg1}")
    )

    # 3) the dragged (explicit) offset is kept out of lane numbering, so the OTHER
    #    segments keep their auto-stacked lanes (a drag never shifts the rest).
    offs = Kraken3DInspector._measure_segment_offsets(fake2)
    lanes_ok = abs(offs.get(0, -1) - 70.0) < 1e-6 and abs(offs.get(1, -1) - 45.0) < 1e-6
    results.append(
        ("a dragged explicit offset stays out of lane numbering (others keep base lane)",
         lanes_ok, f"offsets={offs}")
    )

    # 4) the live rubber-band preview is wired into the Measure hover, builds a line
    #    from the first anchor to the cursor, and is torn down on commit / clear.
    hover_src = inspect.getsource(Kraken3DInspector._update_measure_hover_highlight)
    prev_src = inspect.getsource(Kraken3DInspector._refresh_measure_preview)
    rec_src = inspect.getsource(Kraken3DInspector._record_measure_point)
    clr_src = inspect.getsource(Kraken3DInspector.clear_measurements)
    preview_ok = (
        "_refresh_measure_preview(" in hover_src
        and "_clear_measure_preview()" in hover_src
        and "_measure_axis_snap_for_pick(" in hover_src       # preview snaps like the click
        and "_measure_p0" in prev_src and "cursor_world" in prev_src
        and "_clear_measure_preview()" in rec_src             # torn down when the 2nd point lands
        and "_clear_measure_preview()" in clr_src             # torn down on Clear
    )
    results.append(
        ("live rubber-band preview wired into the Measure hover (built + torn down)",
         preview_ok, f"wired={preview_ok}")
    )

    # 5) a pickable midpoint grab handle is drawn per visible segment and registered
    #    in _actor_measure_handle_map so a left-press can grab it.
    refresh_src = inspect.getsource(Kraken3DInspector._refresh_measure_overlays)
    handle_ok = (
        "vtkSphereSource" in refresh_src
        and "_actor_measure_handle_map" in refresh_src
        and "PickableOn()" in refresh_src
    )
    results.append(
        ("a pickable lane handle is drawn per segment + mapped to its id",
         handle_ok, f"wired={handle_ok}")
    )

    # 6) the lane-handle drag gesture is wired through the Tk mouse bindings:
    #    press grabs the handle, B1-motion drags it, release commits.
    from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService
    binds = inspect.getsource(Open3DMouseBindingsService._install_pick_only_left_click_bindings)
    bindings_ok = (
        "_measure_offset_drag_state_from_current_pick()" in binds
        and "_apply_measure_offset_drag_motion(current)" in binds
        and "_finish_measure_offset_drag(measure_offset_drag_state)" in binds
    )
    results.append(
        ("lane-handle drag wired into the Tk mouse bindings (press/drag/release)",
         bindings_ok, f"wired={bindings_ok}")
    )

    # 7) the drag motion converts the Tk (top-left) event xy to VTK (bottom-left)
    #    display xy before building the pick ray -- without this y-flip the handle
    #    tracks a mirrored cursor and the lane jumps to the axis (flag 101729).
    apply_src = inspect.getsource(Kraken3DInspector._apply_measure_offset_drag_motion)
    yflip_ok = (
        "_tk_xy_to_vtk_display_xy(" in apply_src
        and "_measure_offset_amount_for_cursor(state, display_xy)" in apply_src
    )
    results.append(
        ("handle drag flips Tk->VTK display xy before the pick ray (no mirrored drag)",
         yflip_ok, f"wired={yflip_ok}")
    )

    # 8) the dimension value label is anchored clear of the midpoint grab sphere so
    #    the "center dot" never covers the number (flag 101653): pushed outward
    #    along the lane offset by radius+margin, staying coplanar (x and z fixed).
    la = Kraken3DInspector._measure_label_anchor(
        [0.0, 50.0, 300.0], [0.0, 0.0, 275.0], [0.0, 0.0, 325.0], 3.0
    )
    la = np.asarray(la, dtype=float).reshape(-1)[:3]
    label_ok = (
        abs(float(la[1]) - (50.0 + 3.0 + 6.0)) < 1e-6   # mid_y + radius + margin
        and abs(float(la[0])) < 1e-6                     # stays in the X=0 plane
        and abs(float(la[2]) - 300.0) < 1e-6             # same axial station
    )
    results.append(
        ("value label anchored clear of the grab sphere (outward, coplanar)",
         label_ok, f"label_anchor={la.tolist()}")
    )

    return results


def main() -> int:
    results = run_checks()
    ok = True
    for name, passed, det in results:
        print(f"{name} | {'PASS' if passed else 'FAIL'} | {det}")
        ok = ok and passed
    print("[PASS] Measure preview + draggable lane handle" if ok
          else "[FAIL] Measure preview / lane-handle drag regressed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
