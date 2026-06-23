"""Guard: Measure auto offset-adjust after the 2nd click (bugs/0115 CAD-flow step 3).

The CAD measure gesture the user asked for is click / click / move-the-offset /
click. Commit 1 gave axis snap + coplanar lanes, Commit 2 gave the live preview +
a draggable midpoint handle. This step removes the "hunt for the handle" step:
after the SECOND Measure pick, control transfers straight to that dimension's
offset -- the bare mouse moves the standoff (resize cursor) and a plain click
finishes.

* ``_begin_measure_offset_adjust`` -- entered from ``_record_measure_point`` once
  the second point lands; seeds the segment's explicit ``seg['offset']`` from its
  current lane (so the dimension starts where it was drawn) and arms the modal.
* ``_apply_measure_offset_adjust_motion`` -- driven by the Tk ``<Motion>`` binding
  (``hover_motion``) while the modal owns the bare mouse; the standoff follows the
  cursor (closest approach along the +Y lane direction). The interactor position is
  already flipped to VTK display coords by ``set_event_info``, so -- unlike the
  midpoint-handle drag -- it reads ``GetEventPosition()`` directly (no extra flip).
* ``_finish_measure_offset_adjust`` -- a plain click (``left_release``) leaves the
  modal and keeps the explicit offset, which stays out of lane numbering so the
  other auto-stacked dimensions never shift.

``run_checks`` is display-free: the begin/motion/finish state transitions run on
SimpleNamespace fakes (the offset math is the same exact closest-point used by the
Commit-2 handle drag), and the rest is source-string wiring. Penta phase 107 runs
``run_checks`` only.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


def run_checks() -> list[tuple[str, bool, str]]:
    import numpy as np

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    results: list[tuple[str, bool, str]] = []

    # Shared fake: two axial segments (dimension lines run along z, so the lane
    # offset direction resolves to +Y in the X=0 plane).
    seg0 = {"p0": [0.0, 0.0, 275.0], "p1": [0.0, 0.0, 330.0],
            "r0": None, "dz0": 0.0, "r1": None, "dz1": 0.0, "n0": None, "id": 0}
    seg1 = {"p0": [0.0, 0.0, 300.0], "p1": [0.0, 0.0, 430.0],
            "r0": None, "dz0": 0.0, "r1": None, "dz1": 0.0, "n0": None, "id": 1}
    fake = SimpleNamespace(
        _measure_segments=[seg0, seg1],
        _hidden_measure_segments=set(),
        _measure_offset_adjust_mode=False,
        _measure_offset_adjust_state=None,
        _vtk_widget=None,
        _resolve_measure_point=lambda p, r, dz: np.asarray(p, dtype=float).reshape(3),
        _refresh_measure_overlays=lambda: None,
        _set_axis_pick_cursor=lambda hand: None,
        _update_mode_badge=lambda: None,
        status_var=SimpleNamespace(set=lambda *a, **k: None),
    )
    fake._measure_offset_direction = lambda seg: Kraken3DInspector._measure_offset_direction(fake, seg)
    fake._measure_segment_offsets = lambda: Kraken3DInspector._measure_segment_offsets(fake)
    fake._measure_segment_by_id = lambda sid: Kraken3DInspector._measure_segment_by_id(fake, sid)
    fake._set_measure_offset_adjust_cursor = (
        lambda: Kraken3DInspector._set_measure_offset_adjust_cursor(fake)
    )

    # 1) the second Measure pick hands control to the offset-adjust modal: mode on,
    #    state carries the segment id + the +Y lane direction, and the segment's
    #    explicit standoff is seeded from its current auto lane (45 mm) so the
    #    dimension starts where it was just drawn.
    entered = Kraken3DInspector._begin_measure_offset_adjust(fake, seg0)
    begin_ok = (
        entered is True
        and fake._measure_offset_adjust_mode is True
        and fake._measure_offset_adjust_state is not None
        and int(fake._measure_offset_adjust_state["seg_id"]) == 0
        and abs(float(seg0.get("offset", -1)) - 45.0) < 1e-6
        and abs(float(fake._measure_offset_adjust_state["od"][1]) - 1.0) < 1e-6
    )
    results.append(
        ("2nd Measure pick enters offset-adjust (mode on, state seeded from the lane)",
         begin_ok, f"entered={entered}, mode={fake._measure_offset_adjust_mode}, "
                   f"seg0_offset={seg0.get('offset')}")
    )

    # 2) the bare mouse moves the standoff: the motion reads the VTK interactor
    #    position directly (already flipped by set_event_info) and sets the dragged
    #    segment's explicit offset (closest approach along +Y -> 70 mm here).
    fake._vtk_interactor = SimpleNamespace(GetEventPosition=lambda: (123, 456))
    fake._display_pick_ray = lambda xy: (
        np.array([-100.0, 70.0, 302.5]), np.array([1.0, 0.0, 0.0])
    )
    fake._measure_offset_amount_for_cursor = (
        lambda st, xy: Kraken3DInspector._measure_offset_amount_for_cursor(fake, st, xy)
    )
    Kraken3DInspector._apply_measure_offset_adjust_motion(fake)
    motion_ok = abs(float(seg0.get("offset", -1)) - 70.0) < 1e-6
    results.append(
        ("bare-mouse motion sets the segment's standoff (closest approach along +Y)",
         motion_ok, f"seg0_offset={seg0.get('offset')}")
    )

    # 3) a click finishes the modal: mode cleared, state dropped, and the explicit
    #    offset is kept OUT of lane numbering so the other segment keeps its base
    #    lane (the just-set dimension never shifts the rest).
    Kraken3DInspector._finish_measure_offset_adjust(fake)
    offs = Kraken3DInspector._measure_segment_offsets(fake)
    finish_ok = (
        fake._measure_offset_adjust_mode is False
        and fake._measure_offset_adjust_state is None
        and abs(offs.get(0, -1) - 70.0) < 1e-6   # explicit standoff kept
        and abs(offs.get(1, -1) - 45.0) < 1e-6   # other segment keeps its base lane
    )
    results.append(
        ("click finishes the modal; explicit offset kept out of lane numbering",
         finish_ok, f"mode={fake._measure_offset_adjust_mode}, offsets={offs}")
    )

    # 4) the modal returns False (mode NOT entered) when the segment geometry can't
    #    resolve a perpendicular (here _resolve_measure_point throws) -- a degenerate
    #    measure falls straight through to the plain live status instead of getting
    #    stuck in a modal that can't be driven. seg=None is also rejected.
    fake._measure_offset_adjust_mode = False
    fake._measure_offset_adjust_state = None
    _saved_resolve = fake._resolve_measure_point

    def _boom(*_a, **_k):
        raise ValueError("unresolvable")

    fake._resolve_measure_point = _boom
    seg_bad = {"p0": [0.0, 0.0, 275.0], "p1": [0.0, 0.0, 330.0],
               "r0": None, "dz0": 0.0, "r1": None, "dz1": 0.0, "n0": None, "id": 9}
    entered_bad = Kraken3DInspector._begin_measure_offset_adjust(fake, seg_bad)
    entered_none = Kraken3DInspector._begin_measure_offset_adjust(fake, None)
    fake._resolve_measure_point = _saved_resolve
    degenerate_ok = (
        entered_bad is False and entered_none is False
        and fake._measure_offset_adjust_mode is False
    )
    results.append(
        ("unresolvable / None segment does not enter offset-adjust",
         degenerate_ok, f"entered_bad={entered_bad}, entered_none={entered_none}, "
                        f"mode={fake._measure_offset_adjust_mode}")
    )

    # 5) the offset-adjust motion reads the interactor position DIRECTLY -- it must
    #    NOT flip Tk->VTK like the midpoint-handle drag (the bare-mouse position is
    #    already VTK display coords via set_event_info; a double flip would mirror).
    motion_src = inspect.getsource(Kraken3DInspector._apply_measure_offset_adjust_motion)
    noflip_ok = (
        "GetEventPosition()" in motion_src
        and "_tk_xy_to_vtk_display_xy" not in motion_src
        and "_measure_offset_amount_for_cursor(" in motion_src
    )
    results.append(
        ("bare-mouse motion uses VTK GetEventPosition directly (no Tk->VTK flip)",
         noflip_ok, f"wired={noflip_ok}")
    )

    # 6) the cursor becomes a vertical resize arrow while adjusting ("mouse pointer
    #    change to resize pointer").
    cur_src = inspect.getsource(Kraken3DInspector._set_measure_offset_adjust_cursor)
    cursor_ok = "sb_v_double_arrow" in cur_src
    results.append(
        ("offset-adjust shows the resize cursor (sb_v_double_arrow)",
         cursor_ok, f"wired={cursor_ok}")
    )

    # 7) the 2nd Measure pick is what arms the modal: _record_measure_point calls
    #    _begin_measure_offset_adjust right after it lands the second point.
    rec_src = inspect.getsource(Kraken3DInspector._record_measure_point)
    record_ok = "_begin_measure_offset_adjust(" in rec_src
    results.append(
        ("the 2nd Measure pick arms the offset-adjust (wired in _record_measure_point)",
         record_ok, f"wired={record_ok}")
    )

    # 8) the modal is wired through the Tk mouse bindings (bare-mouse <Motion> drives
    #    it, a release finishes it, a press while active arms no drag detector) and
    #    the VTK-side hover is suppressed so the two don't fight.
    from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService
    binds = inspect.getsource(Open3DMouseBindingsService._install_pick_only_left_click_bindings)
    from KrakenOS.UI.services.open3d_interaction import Open3DInteractionService
    move_src = inspect.getsource(Open3DInteractionService._on_mouse_move)
    bindings_ok = (
        "_apply_measure_offset_adjust_motion()" in binds
        and "_finish_measure_offset_adjust()" in binds
        and "_measure_offset_adjust_mode" in binds
        and "_measure_offset_adjust_mode" in move_src
    )
    results.append(
        ("offset-adjust modal wired into the Tk bindings + VTK hover suppressed",
         bindings_ok, f"wired={bindings_ok}")
    )

    return results


def main() -> int:
    results = run_checks()
    ok = True
    for name, passed, det in results:
        print(f"{name} | {'PASS' if passed else 'FAIL'} | {det}")
        ok = ok and passed
    print("[PASS] Measure auto offset-adjust after the 2nd click" if ok
          else "[FAIL] Measure auto offset-adjust regressed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
