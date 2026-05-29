"""Validate the slide-along-axis primitive and its 3D wiring.

Contracts under test:

* ``slide_lens_along_axis(row_index, +dz)`` shifts the picked lens (single
  row or Tier 3 native group) by ``dz`` mm while preserving overall track
  length — the preceding-row thickness grows by ``dz`` and the last row of
  the group shrinks by ``dz``. Internal group thicknesses are untouched.
* Slides that would push either gap thickness negative are rejected.
* The 3D inspector exposes a toolbar mode + drag state hook
  (``slide_along_axis_mode_var``, ``_axis_slide_drag_state``,
  ``_axis_slide_state_from_current_pick``,
  ``_apply_axis_slide_drag_motion``, ``_finish_axis_slide_drag``).

Run from the repository root:

    python -m KrakenOS.UI.validate_axis_slide
"""

from __future__ import annotations

import inspect
from copy import deepcopy
from dataclasses import asdict

from KrakenOS.UI import layout_editor as le
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
from KrakenOS.UI.open3d_inspector import Kraken3DInspector


def _check_source_contracts() -> list[str]:
    failures: list[str] = []
    if not hasattr(KrakenLayoutEditor, "slide_lens_along_axis"):
        failures.append("KrakenLayoutEditor.slide_lens_along_axis is missing")
    for attr in (
        "_axis_slide_state_from_current_pick",
        "_apply_axis_slide_drag_motion",
        "_finish_axis_slide_drag",
        "_toggle_axis_slide_mode",
    ):
        if not hasattr(Kraken3DInspector, attr):
            failures.append(f"Kraken3DInspector.{attr} is missing")
    init_source = inspect.getsource(Kraken3DInspector.__init__)
    for marker in ("slide_along_axis_mode_var", "_axis_slide_drag_state"):
        if marker not in init_source:
            failures.append(f"Kraken3DInspector.__init__ must declare {marker}")
    bindings_source = inspect.getsource(
        __import__("KrakenOS.UI.services.open3d_mouse_bindings", fromlist=["Open3DMouseBindingsService"])
        .Open3DMouseBindingsService._install_pick_only_left_click_bindings
    )
    apply_source = inspect.getsource(Kraken3DInspector._apply_axis_slide_drag_motion)
    finish_source = inspect.getsource(Kraken3DInspector._finish_axis_slide_drag)
    cancel_source = inspect.getsource(Kraken3DInspector.cancel_active_3d_operation)
    for marker in (
        "_axis_slide_state_from_current_pick",
        "_apply_axis_slide_drag_motion",
        "_finish_axis_slide_drag",
    ):
        if marker not in bindings_source:
            failures.append(f"mouse bindings must dispatch {marker}")
    if "refresh_from_editor()" in apply_source:
        failures.append("axis-slide drag motion must not rebuild/retrace the 3D scene on every mouse step")
    if "record_history=False" not in apply_source or "sync_table=False" not in apply_source:
        failures.append("axis-slide drag motion must batch table/history work until mouse release")
    if "refresh_from_editor()" not in finish_source or "_commit_history_capture()" not in finish_source:
        failures.append("axis-slide release must commit history and redraw once")
    if "self._axis_slide_drag_state" not in cancel_source or "history_started" not in cancel_source:
        failures.append("Esc/cancel must restore an in-progress axis-slide history capture")
    return failures


def _check_slide_behaviour() -> list[str]:
    failures: list[str] = []
    le._load_3d_backends()
    app = KrakenLayoutEditor(headless=True)
    try:
        app.load_layouts()
        app.load_layout_by_name("Machine Vision 150Mm Measured", refresh=False)
        rows = app.rows
        template = next((row for row in rows if row.surface == "Standard"), None)
        if template is None:
            failures.append("MV150 fixture has no Standard row to template the synthetic group from")
            return failures
        synthetic = [
            (28.5, 9.0, "BK7", "Front sphere"),
            (-31.0, 2.58, "F2", "Cemented sphere"),
            (-200.0, 6.0, "AIR", "Back asphere"),
        ]
        achr: list[SurfaceRow] = []
        promotion_meta = {"row_indices": [1, 2, 3]}
        for rc, th, glass, name in synthetic:
            row = SurfaceRow(**asdict(template))
            row.surface = "Standard"
            row.rc = float(rc)
            row.thickness = float(th)
            row.glass = glass
            row.name = name
            row.advanced = {"StepNativePromotion": dict(promotion_meta)}
            achr.append(row)
        rows[1:4] = achr
        app._sync_table()

        leading_before = float(rows[0].thickness)
        internal_a_before = float(rows[1].thickness)
        internal_b_before = float(rows[2].thickness)
        trailing_before = float(rows[3].thickness)

        # Slide forward by +5 mm.
        result = app.slide_lens_along_axis(2, 5.0)
        if abs(float(rows[0].thickness) - (leading_before + 5.0)) > 1.0e-9:
            failures.append(
                f"leading thickness should be {leading_before + 5.0}, got {rows[0].thickness}"
            )
        if abs(float(rows[3].thickness) - (trailing_before - 5.0)) > 1.0e-9:
            failures.append(
                f"trailing thickness should be {trailing_before - 5.0}, got {rows[3].thickness}"
            )
        if abs(float(rows[1].thickness) - internal_a_before) > 1.0e-9:
            failures.append(
                f"internal thickness S1 changed: {internal_a_before} -> {rows[1].thickness}"
            )
        if abs(float(rows[2].thickness) - internal_b_before) > 1.0e-9:
            failures.append(
                f"internal thickness S2 changed: {internal_b_before} -> {rows[2].thickness}"
            )
        if list(result.get("group_indices", [])) != [1, 2, 3]:
            failures.append(f"slide result.group_indices wrong: {result.get('group_indices')}")
        if abs(float(result.get("delta_z_mm", 0.0)) - 5.0) > 1.0e-9:
            failures.append("slide result.delta_z_mm did not echo +5.0")

        # Slide backward by -3 mm — back toward original position.
        app.slide_lens_along_axis(1, -3.0)
        if abs(float(rows[0].thickness) - (leading_before + 2.0)) > 1.0e-9:
            failures.append("net leading after +5/-3 should be leading_before + 2.0")
        if abs(float(rows[3].thickness) - (trailing_before - 2.0)) > 1.0e-9:
            failures.append("net trailing after +5/-3 should be trailing_before - 2.0")

        # Slides that would drive a gap negative must raise.
        excessive_back = -(leading_before + 100.0)
        raised = False
        try:
            app.slide_lens_along_axis(2, excessive_back)
        except RuntimeError:
            raised = True
        if not raised:
            failures.append("slide_lens_along_axis must reject slides that drive the leading gap negative")

        excessive_forward = trailing_before + 100.0
        raised = False
        try:
            app.slide_lens_along_axis(2, excessive_forward)
        except RuntimeError:
            raised = True
        if not raised:
            failures.append("slide_lens_along_axis must reject slides that drive the trailing gap negative")
    finally:
        app.destroy()
    return failures


def main() -> int:
    failures: list[str] = []
    failures.extend(_check_source_contracts())
    failures.extend(_check_slide_behaviour())
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("Axis-slide contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
