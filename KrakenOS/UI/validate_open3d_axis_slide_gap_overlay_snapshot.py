#!/usr/bin/env python3
"""Regression for the slide-along-axis live gap readout (requests #65 + #66).

#66: dragging a row in "Slide along axis" mode used to show NO live gap
dimension -- the body's refresh is debounced, so ``_apply_axis_slide_drag_motion``
mutated the model thickness every frame but drew nothing. The fix wires
``_update_axis_slide_gap_overlay`` into the motion handler: ``_row_slide_axial_gap``
anchors the gap arrow's far end to the previous *visible* component (static
during the drag) and places the near end exactly the live model gap
(``preceding_thickness_after``) along the axis.

#65: that gap readout is drawn THICK and EMERALD GREEN (0.10, 0.90, 0.45),
deliberately distinct from the optical axis (blue 0,0.43,0.88) and the
highlighted optical axis (gold 1.0,0.68,0.05) it used to collide with.

The default run is **display-free and fast**: it exercises the real
``_row_slide_axial_gap`` / ``_scene_component_axial_extents`` /
``_axial_extent_from_actor_keys`` geometry against hand-placed fake bodies (so
no Tk / VTK / Xvfb / optical retrace), proves the emerald colour stays distinct
from the axis colours, and source-couples the styling + the #66 wiring. The
heavy full render (boot inspector, slide a flattened penta cascade, write a PNG
to eyeball) is opt-in via ``--render`` -- the visual was verified once by hand;
this keeps the regression guard cheap.

Run (fast):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_axis_slide_gap_overlay_snapshot
Run (also write a PNG to /tmp for eyeballing):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_axis_slide_gap_overlay_snapshot --render

Exit: 0 = pass, 1 = regression, 2 = (--render only) environment can't render.
"""
from __future__ import annotations

import inspect
import sys

EMERALD = (0.10, 0.90, 0.45)
FORBIDDEN = {
    "optical-axis blue": (0.0, 0.43, 0.88),
    "highlighted-axis gold": (1.0, 0.68, 0.05),
}


class _FakeActor:
    """Minimal stand-in: ``_axial_extent_from_actor_keys`` only calls GetBounds."""

    def __init__(self, zmin, zmax, x=0.0, y=0.0, w=10.0, h=10.0):
        self._bounds = (x - w / 2, x + w / 2, y - h / 2, y + h / 2, zmin, zmax)

    def GetBounds(self):
        return self._bounds


def _bare_inspector():
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    insp = Kraken3DInspector.__new__(Kraken3DInspector)
    insp._actor_by_key = {}
    insp._row_actor_map = {}
    insp._step_actor_map = {}
    return insp


def check_gap_math() -> list[str]:
    """The real anchoring geometry, against fake bodies -- no display."""
    fails: list[str] = []
    insp = _bare_inspector()

    # A lens body at z[40,60] preceded by a body at z[0,10]; live model gap 30.
    insp._actor_by_key = {"r1": _FakeActor(0, 10), "r2": _FakeActor(40, 60)}
    insp._row_actor_map = {1: ["r1"], 2: ["r2"]}
    gap = insp._row_slide_axial_gap([2], 30.0)
    if gap is None:
        fails.append("slide gap returned None even though a preceding body exists")
    else:
        near, far, value = gap
        if abs(float(far[2]) - 10.0) > 1e-6:
            fails.append(f"arrow far end not pinned to the preceding body (z={float(far[2]):.3f}, want 10)")
        if abs(float(near[2]) - 40.0) > 1e-6:
            fails.append(f"arrow near end not far+gap (z={float(near[2]):.3f}, want 40)")
        if abs(value - 30.0) > 1e-6:
            fails.append(f"gap value {value} != live model gap 30")

    # exclude_rows teeth: a sub-row of the dragged GROUP (r3 at z[50,70], whose
    # proj_max 70 would otherwise win) must NOT be picked as the 'previous' body.
    insp._actor_by_key["r3"] = _FakeActor(50, 70)
    insp._row_actor_map = {1: ["r1"], 2: ["r2"], 3: ["r3"]}
    gap2 = insp._row_slide_axial_gap([2, 3], 5.0)
    if gap2 is None or abs(float(gap2[1][2]) - 10.0) > 1e-6:
        got = "None" if gap2 is None else f"{float(gap2[1][2]):.3f}"
        fails.append(f"exclude_rows failed: arrow anchored to the dragged group itself (far z={got}, want 10)")

    # First element (no preceding body) -> no overlay, not a crash.
    insp._row_actor_map = {2: ["r2"]}
    if insp._row_slide_axial_gap([2], 5.0) is not None:
        fails.append("expected None when there is no preceding component")
    return fails


def check_color_distinct() -> list[str]:
    fails: list[str] = []
    for name, color in FORBIDDEN.items():
        dist = sum((a - b) ** 2 for a, b in zip(EMERALD, color)) ** 0.5
        if dist < 0.3:
            fails.append(f"emerald gap colour too close to the {name} ({dist:.3f} < 0.3)")
    return fails


def check_source_coupling() -> list[str]:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as K
    from KrakenOS.UI.services.open3d_thickness_dimensions import (
        Open3DThicknessDimensionService as S,
    )

    fails: list[str] = []
    draw = inspect.getsource(K._draw_step_translate_gap_overlay)
    if "(0.10, 0.90, 0.45)" not in draw:
        fails.append("emerald (0.10, 0.90, 0.45) no longer the gap colour in _draw_step_translate_gap_overlay (#65)")
    if "thickness_scale" not in draw or "DIMENSION_LEADER_LINE_WIDTH" not in draw:
        fails.append("gap overlay no longer thickens the arrow/leader (#65)")
    if "thickness_scale" not in inspect.getsource(S.arrow_mesh):
        fails.append("arrow_mesh dropped the thickness_scale knob (#65)")
    if "_update_axis_slide_gap_overlay" not in inspect.getsource(K._apply_axis_slide_drag_motion):
        fails.append("slide-along-axis motion no longer draws the gap overlay (#66 wiring lost)")
    if "_clear_step_translate_drag_overlay" not in inspect.getsource(K._finish_axis_slide_drag):
        fails.append("slide finish no longer clears the gap overlay")
    if "_clear_step_translate_drag_overlay" not in inspect.getsource(K.cancel_active_3d_operation):
        fails.append("cancel no longer clears the gap overlay")
    return fails


def render_png() -> int:
    """Opt-in heavy path: boot the inspector, slide a flattened penta-cascade
    row, and write a PNG so a human can eyeball the thick emerald gap. Needs a
    display (own Xvfb) and a full retrace -- slow, hence not the default."""
    import tempfile
    from pathlib import Path

    import numpy as np

    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import (
        _ensure_display,
        render_window_to_png,
    )
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import (
        PENTA_CASCADE_PATH,
        _open_inspector,
    )
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.render_layout_snapshot import _load_layout_module, _rows_from_layout_info

    if not PENTA_CASCADE_PATH.exists():
        print(f"SKIP --render: cascade fixture missing: {PENTA_CASCADE_PATH}")
        return 2
    if not _ensure_display():
        print("SKIP --render: no usable display (Xvfb)")
        return 2

    app = KrakenLayoutEditor()
    try:
        insp = _open_inspector(app)
        module = _load_layout_module(PENTA_CASCADE_PATH)
        app.rows = _rows_from_layout_info({"surfaces": list(getattr(module, "SURFACES", []) or [])})
        app._apply_layout_settings(dict(getattr(module, "SETTINGS", {}) or {}))
        # Flatten the fold so bodies lie along +Z in optical order, with gaps.
        for index, row in enumerate(app.rows):
            row.tilt_x = row.tilt_y = row.tilt_z = 0.0
            row.desp_x = row.desp_y = row.desp_z = 0.0
            row.axis_move = 0.0
            if index < len(app.rows) - 1:
                row.thickness = 25.0
        app._sync_table()
        insp.refresh_from_editor(force_retrace=True)
        insp.update_idletasks()
        insp.slide_along_axis_mode_var.set(True)
        insp.update_idletasks()

        ppx = insp._placement_drag_pixels_per_step()
        for target in sorted((insp._row_actor_map or {}).keys()):
            group = app._lens_row_group_for_row(target)
            if not group or group[0] - 1 < 0 or group[-1] + 1 >= len(app.rows):
                continue
            actor = next(
                (insp._actor_by_key.get(k) for k in dict.fromkeys(insp._row_actor_map.get(target, []) or [])
                 if insp._actor_by_key.get(k) is not None),
                None,
            )
            if actor is None:
                continue
            direction = np.asarray(
                insp._placement_drag_display_direction("translate", "z", 1.0, actor), dtype=float
            ).reshape(-1)[:2]
            insp._clear_step_translate_drag_overlay(render=False)
            insp._axis_slide_drag_state = {
                "row_index": target,
                "group_indices": list(group),
                "snap_mm": float(insp._axis_slide_snap_step_for_row(target)),
                "display_direction": direction,
                "pixel_accumulator": 0.0,
                "applied_delta_mm": 0.0,
                "history_started": False,
                "last_result": None,
            }
            insp._apply_axis_slide_drag_motion(float(direction[0]) * 4.0 * ppx, -float(direction[1]) * 4.0 * ppx)
            insp.update_idletasks()
            if insp._step_translate_gap_actors:
                png_path = Path(tempfile.gettempdir()) / "krakenos_axis_slide_gap_overlay.png"
                render_window_to_png(insp, png_path)
                print(f"--render: slid S{target}, {len(insp._step_translate_gap_actors)} gap actors -> {png_path}")
                return 0
            insp._axis_slide_drag_state = None
        print("--render: no slide produced a gap overlay")
        return 1
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def main() -> int:
    fails = check_gap_math() + check_color_distinct() + check_source_coupling()
    if fails:
        print("FAIL: axis-slide gap overlay (#65/#66)")
        for item in fails:
            print(f"  ! {item}")
        return 1
    print("PASS: gap anchoring math + exclude_rows + emerald distinctness + #66 wiring (display-free).")
    if "--render" in sys.argv:
        return render_png()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
