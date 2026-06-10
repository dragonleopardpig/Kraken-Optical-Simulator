#!/usr/bin/env python3
"""Display-free guard for bugs/0053: re-anchorable thickness/distance dimensions.

Ctrl-CLICKING a thickness arrow's endpoint enters a modal re-anchor: the endpoint
then follows the BARE mouse (no button held), the real magenta arrow live-updates,
the surface/edge under the cursor highlights, and a plain click commits the new
measured location. Re-anchoring re-anchors what the dimension MEASURES (a
measurement annotation) without moving any optical surface. The object/LED row's
object-side endpoint instead feeds the existing object-edge reference so the LED
body sits with the chosen face at the object distance.

No X server needed. Checks:
  1. ``Open3DThicknessDimensionService.reanchored_endpoints`` moves the chosen
     endpoint's axial z and reports the measured distance.
  2. ``apply_dimension_anchor_override`` on a general row stores the override and
     leaves ``rows[i].thickness`` untouched (measurement, not a model edit).
  3. The object/LED row's start endpoint routes to the object-edge reference
     (sets ``led_step_object_edge_local_z``), not the general override map.
  4. Overrides round-trip through ``_collect_layout_settings`` /
     ``_apply_layout_settings``.
  5. Modal source contract (#1-#4): Ctrl-click enters the modal pick, the bare
     mouse + a held drag both drive ``_apply_dimension_anchor_pick_motion``, a
     plain click commits via ``_commit_dimension_anchor_pick``, and Ctrl on empty
     space still orbits. The live preview draws the real ``arrow_mesh`` (not a bare
     line) and highlights the snap target.
  6. Editing a re-anchored dimension's value moves the measured reference only
     (``apply_reanchored_dimension_measured``) and never ``rows[i].thickness`` --
     so the wrong element (e.g. the Imaging Lens) can no longer shift.
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


def _test_modal_pick_source_contract() -> None:
    """#1-#4: the interaction is a modal pick driven by the bare mouse, the live
    preview is the real arrow, the snap target highlights, and Ctrl-on-empty still
    orbits. These are wiring contracts that can't be exercised without an X server,
    so we assert them against the installer/handler source."""
    from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    binds = inspect.getsource(Open3DMouseBindingsService._install_pick_only_left_click_bindings)
    # left_press: a Ctrl-click that lands on a dimension enters the modal pick.
    if "_begin_dimension_anchor_pick_from_current_pick()" not in binds:
        raise AssertionError("left_press does not enter the modal re-anchor on Ctrl-click")
    # The bare mouse (hover_motion) AND a held drag (left_motion) both drive it.
    if binds.count("self._apply_dimension_anchor_pick_motion()") < 2:
        raise AssertionError("bare-mouse + drag motion must both drive _apply_dimension_anchor_pick_motion")
    # A plain click commits.
    if "self._commit_dimension_anchor_pick()" not in binds:
        raise AssertionError("a plain click in modal mode must commit via _commit_dimension_anchor_pick")
    # Ctrl-on-empty orbit branch must remain intact and reachable.
    if "if ctrl_pressed:" not in binds or "self._rotate_camera_fixed_drag(dx, dy)" not in binds:
        raise AssertionError("Ctrl camera-orbit branch missing (orbit on empty would break)")
    # The modal-mode motion branch must short-circuit before the Ctrl orbit branch
    # so a held Ctrl-drag re-anchors instead of orbiting.
    motion_anchor = binds.index("if self._dimension_anchor_pick_mode:")
    orbit_pos = binds.index("self._rotate_camera_fixed_drag(dx, dy)")
    if not (motion_anchor < orbit_pos):
        raise AssertionError("modal re-anchor motion must precede the Ctrl camera-orbit branch")

    # #2: the live preview draws the real double-headed arrow_mesh, not just a line.
    preview = inspect.getsource(Kraken3DInspector._update_dimension_anchor_preview)
    if "arrow_mesh(" not in preview:
        raise AssertionError("live preview must draw the real arrow_mesh (feedback #2)")
    # #3: the snap target highlights (STEP face outline and/or surface row).
    highlight = inspect.getsource(Kraken3DInspector._set_dimension_anchor_snap_highlight)
    if "_set_step_hover_outline" not in highlight and "_set_row_highlight" not in highlight:
        raise AssertionError("snap highlight must outline the surface/edge under the cursor (feedback #3)")
    print("modal pick source contract (#1-#4) OK")


def _test_reanchor_value_edit_is_measurement_only() -> None:
    """#6: editing a re-anchored dimension's value moves the measured reference
    only -- never rows[i].thickness -- so the wrong element can't shift."""
    app = _build_editor()
    # Re-anchor row 2's "end" to z=42, recording the un-moved end (fixed_z) so the
    # value edit can re-solve the measured distance.
    app.apply_dimension_anchor_override(2, "end", np.array([0.0, 0.0, 42.0]), fixed_z=10.0)
    ov = app._dimension_anchor_override_for_row(2)
    if not (isinstance(ov, dict) and abs(float(ov.get("fixed_z")) - 10.0) < 1e-9):
        raise AssertionError(f"override must record fixed_z for value re-solve: {ov}")
    thickness_before = float(app.rows[2].thickness)
    applied = app.apply_reanchored_dimension_measured(2, 5.0)
    if not applied:
        raise AssertionError("apply_reanchored_dimension_measured should apply with a known fixed_z")
    ov2 = app._dimension_anchor_override_for_row(2)
    # ref was 42 (>= fixed 10) so sign +1: new ref_z = 10 + 5 = 15.
    if abs(float(ov2.get("ref_z")) - 15.0) > 1e-9:
        raise AssertionError(f"measured edit must move ref_z to 15.0, got {ov2.get('ref_z')}")
    if abs(float(app.rows[2].thickness) - thickness_before) > 1e-9:
        raise AssertionError(
            f"value edit must NOT change rows[2].thickness: {thickness_before} -> {app.rows[2].thickness}"
        )
    # Without a recorded fixed_z the editor refuses (caller leaves the model alone).
    app.apply_dimension_anchor_override(1, "end", np.array([0.0, 0.0, 60.0]))
    legacy = app._dimension_anchor_override_for_row(1)
    if legacy is not None and legacy.get("fixed_z") is None:
        if app.apply_reanchored_dimension_measured(1, 3.0) is not False:
            raise AssertionError("value edit must refuse when fixed_z is unknown (no wrong-element move)")
    print("re-anchored value edit is measurement-only (#6) OK")


def _test_apply_dimension_value_routes_override() -> None:
    """#6 source contract: apply_dimension_value must detect a re-anchor override
    and route to apply_reanchored_dimension_measured BEFORE writing the model
    thickness, otherwise editing the value would move the wrong row."""
    from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService

    src = inspect.getsource(Open3DThicknessDimensionService.apply_dimension_value)
    if "_dimension_anchor_override_for_row" not in src or "apply_reanchored_dimension_measured" not in src:
        raise AssertionError("apply_dimension_value must route re-anchored rows to the measurement edit")
    override_pos = src.index("_dimension_anchor_override_for_row")
    # The actual model write (not the explanatory comment) is the assignment form.
    thickness_pos = src.index("rows[row_index].thickness = ")
    if not (override_pos < thickness_pos):
        raise AssertionError("override routing must run before rows[row_index].thickness is written")
    print("apply_dimension_value routes re-anchored rows (#6 source contract) OK")


def main() -> int:
    _test_reanchored_endpoints()
    _test_general_override_is_measurement_only()
    _test_object_led_routes_to_edge_reference()
    _test_settings_roundtrip()
    _test_modal_pick_source_contract()
    _test_reanchor_value_edit_is_measurement_only()
    _test_apply_dimension_value_routes_override()
    print("dimension re-anchor validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
