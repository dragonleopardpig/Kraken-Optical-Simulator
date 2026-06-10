#!/usr/bin/env python3
"""Display-free guard for bugs/0053: re-anchorable thickness/distance dimensions.

Ctrl-dragging a thickness arrow's endpoint onto a surface/edge re-anchors what
the dimension MEASURES to (a measurement annotation) without moving any optical
surface. The object/LED row's object-side endpoint instead feeds the existing
object-edge reference so the LED body sits with the chosen face at the object
distance.

No X server needed. Checks:
  1. ``Open3DThicknessDimensionService.reanchored_endpoints`` moves the chosen
     endpoint's axial z and reports the measured distance.
  2. ``apply_dimension_anchor_override`` on a general row stores the override and
     leaves ``rows[i].thickness`` untouched (measurement, not a model edit).
  3. The object/LED row's start endpoint routes to the object-edge reference
     (sets ``led_step_object_edge_local_z``), not the general override map.
  4. Overrides round-trip through ``_collect_layout_settings`` /
     ``_apply_layout_settings``.
  5. Source contract: Ctrl on empty space still orbits (the re-anchor only wins
     when a dimension drag-state is active).
"""
from __future__ import annotations

import inspect
import types

import numpy as np


def _test_reanchored_endpoints() -> None:
    from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService

    svc = Open3DThicknessDimensionService(
        types.SimpleNamespace(editor=None), pv_module=None, billboard_text_actor_cls=None
    )
    p0 = np.array([0.0, 0.0, 10.0])
    p1 = np.array([0.0, 0.0, 30.0])
    q0, q1, measured = svc.reanchored_endpoints(p0, p1, {"endpoint": "end", "ref_z": 42.0})
    if not (abs(q1[2] - 42.0) < 1e-9 and abs(q0[2] - 10.0) < 1e-9 and abs(measured - 32.0) < 1e-9):
        raise AssertionError(f"end re-anchor: q0={q0} q1={q1} measured={measured}")
    q0b, q1b, m2 = svc.reanchored_endpoints(p0, p1, {"endpoint": "start", "ref_z": 5.0})
    if not (abs(q0b[2] - 5.0) < 1e-9 and abs(q1b[2] - 30.0) < 1e-9 and abs(m2 - 25.0) < 1e-9):
        raise AssertionError(f"start re-anchor: q0={q0b} q1={q1b} measured={m2}")
    print("reanchored_endpoints OK")


def _build_editor():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow

    app = KrakenLayoutEditor(headless=True)
    app.rows = [
        SurfaceRow(label="0", surface="Object", element="", name="Object",
                   thickness=275.0, diameter=25.0, glass="AIR"),
        SurfaceRow(label="1", surface="Standard", element="L1", name="L1 front",
                   thickness=8.0, diameter=25.0, glass="N-BK7"),
        SurfaceRow(label="2", surface="Standard", element="", name="L1 back",
                   thickness=24.405, diameter=25.0, glass="AIR"),
        SurfaceRow(label="3", surface="Image", element="", name="Image",
                   thickness=0.0, diameter=25.0, glass="AIR"),
    ]
    try:
        app._sync_table()
    except Exception:
        pass
    return app


def _test_general_override_is_measurement_only() -> None:
    app = _build_editor()
    before = float(app.rows[2].thickness)
    app.apply_dimension_anchor_override(2, "end", np.array([0.0, 0.0, 42.0]))
    ov = app._dimension_anchor_override_for_row(2)
    if not (isinstance(ov, dict) and ov.get("endpoint") == "end" and abs(float(ov.get("ref_z")) - 42.0) < 1e-9):
        raise AssertionError(f"general override not stored: {ov}")
    if abs(float(app.rows[2].thickness) - before) > 1e-9:
        raise AssertionError(
            f"re-anchor must NOT change the model thickness: {before} -> {app.rows[2].thickness}"
        )
    print("general override stored, thickness unchanged OK")


def _test_object_led_routes_to_edge_reference() -> None:
    from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP

    app = _build_editor()
    # Any non-None path makes row 0 the object/LED endpoint (apply does not read it).
    app.imported_led_step_path = PRISM_42779_STEP
    app.led_step_object_edge_local_z = None
    app.apply_dimension_anchor_override(0, "start", np.array([0.0, 0.0, 7.0]))
    if app.led_step_object_edge_local_z is None:
        raise AssertionError("object/LED start re-anchor must set led_step_object_edge_local_z")
    if app._dimension_anchor_override_for_row(0) is not None:
        raise AssertionError("object/LED re-anchor must NOT populate the general override map")
    print("object/LED route -> object-edge reference OK")


def _test_settings_roundtrip() -> None:
    app = _build_editor()
    app.apply_dimension_anchor_override(2, "end", np.array([0.0, 0.0, 42.0]))
    settings = app._collect_layout_settings()
    if "dimension_anchor_overrides" not in settings:
        raise AssertionError("settings missing dimension_anchor_overrides")
    app._dimension_anchor_overrides = {}
    app._apply_layout_settings(settings)
    ov = app._dimension_anchor_override_for_row(2)
    if not (isinstance(ov, dict) and abs(float(ov.get("ref_z")) - 42.0) < 1e-9):
        raise AssertionError(f"override did not round-trip through settings: {ov}")
    print("settings round-trip OK")


def _test_ctrl_empty_still_orbits() -> None:
    from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService

    src = inspect.getsource(Open3DMouseBindingsService._install_pick_only_left_click_bindings)
    # The re-anchor must be checked before the Ctrl orbit branch in left_motion,
    # and the Ctrl orbit branch (rotate on Ctrl with no dimension state) must remain.
    if "self._dimension_anchor_drag_state is not None" not in src:
        raise AssertionError("left_motion does not gate on the re-anchor drag state")
    anchor_pos = src.index("self._dimension_anchor_drag_state is not None")
    orbit_pos = src.index("self._rotate_camera_fixed_drag(dx, dy)")
    if not (anchor_pos < orbit_pos):
        raise AssertionError("re-anchor must be handled before the Ctrl camera-orbit branch")
    if "if ctrl_pressed:" not in src or "self._rotate_camera_fixed_drag(dx, dy)" not in src:
        raise AssertionError("Ctrl camera-orbit branch missing (orbit on empty would break)")
    print("Ctrl-on-empty still orbits (source contract) OK")


def main() -> int:
    _test_reanchored_endpoints()
    _test_general_override_is_measurement_only()
    _test_object_led_routes_to_edge_reference()
    _test_settings_roundtrip()
    _test_ctrl_empty_still_orbits()
    print("dimension re-anchor validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
