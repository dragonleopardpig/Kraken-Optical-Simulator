#!/usr/bin/env python3
"""Display-free guard for bugs/0101: a decoration STEP overlay (LED source /
camera body) must never be promoted into an optical mesh-solid or be assigned an
optical surface function.

Root cause it locks down: a beam-splitter cube dragged to overlap the LED made
the right-click pick resolve to the LED; the menu then promoted the 160-face LED
and assigned it a Beam-Splitter face -> minutes-long trace + the cube no longer
split. Decorations are not optical elements, so those actions are blocked.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_decoration_not_promotable

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace


def _build_service():
    """The face-assignment service delegates every attr to ``self._inspector``.
    Hold tracked stubs there so the real guarded methods run end to end."""
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    calls: list[str] = []
    status: list[str] = []

    editor = SimpleNamespace(
        _step_overlay_display_label=lambda lbl: str(lbl),
        select_step_component=lambda lbl: calls.append(f"select:{lbl}"),
        append_debug=lambda *a, **k: None,
        # Promote chokepoints the guarded methods would reach if NOT blocked:
        promote_imported_step_to_optical_solid_row=lambda *a, **k: calls.append("promote_solid") or {"row_index": 1},
        assign_optical_solid_face_function_at_world_point=lambda *a, **k: calls.append("assign_face") or {},
        optical_solid_step_overlay_face_record_at_world_point=lambda *a, **k: {"face_id": "F001"},
    )

    inspector = SimpleNamespace(
        editor=editor,
        status_var=SimpleNamespace(set=lambda msg: status.append(str(msg))),
        _debug_trace=lambda *a, **k: None,
        _debug_actor_counts=lambda *a, **k: {},
        _debug_vector=lambda v: None,
        _active_refresh_sampling_mode=lambda *a, **k: None,
        promote_selected_step_to_optical_solid_row=lambda *a, **k: calls.append("promote_selected"),
        refresh_from_editor=lambda *a, **k: None,
        highlight_row=lambda *a, **k: None,
    )
    svc = Open3DFaceAssignmentService(inspector)
    return svc, calls, status


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # 1) Classification.
    from KrakenOS.UI.services.step_overlay_labels import (
        is_step_overlay_decoration,
        STEP_OVERLAY_DECORATION_LABEL_SET,
    )

    if STEP_OVERLAY_DECORATION_LABEL_SET != {"led", "camera"}:
        failures.append(f"FAIL: decoration set drifted: {STEP_OVERLAY_DECORATION_LABEL_SET}")
    for lbl in ("led", "camera", "LED", "Camera"):
        if not is_step_overlay_decoration(lbl):
            failures.append(f"FAIL: {lbl!r} should be a decoration")
    for lbl in ("optical", "lens"):
        if is_step_overlay_decoration(lbl):
            failures.append(f"FAIL: {lbl!r} must remain a promotable optical overlay")

    # 2) Behavioral: the right-click promote+assign-face path rejects decorations.
    svc, calls, status = _build_service()
    svc._promote_step_and_assign_face_function("led", [0.0, 0.0, 0.0], None, "Beam Splitter")
    if "promote_solid" in calls or "assign_face" in calls:
        failures.append(f"FAIL: LED promote+face-assign was NOT blocked (calls={calls})")
    if not any("decoration" in s.lower() for s in status):
        failures.append(f"FAIL: no 'decoration' status for blocked LED face-assign (status={status})")

    # 3) Behavioral: the right-click "Promote to Optical Element" rejects decorations.
    svc2, calls2, status2 = _build_service()
    svc2._promote_step_from_context("camera")
    if "select:camera" in calls2 or "promote_selected" in calls2:
        failures.append(f"FAIL: camera 'Promote to Optical Element' was NOT blocked (calls={calls2})")
    if not any("decoration" in s.lower() for s in status2):
        failures.append(f"FAIL: no 'decoration' status for blocked camera promote (status={status2})")

    # 4) Guard does NOT over-block: the genuine "optical" overlay still promotes.
    svc3, calls3, _status3 = _build_service()
    svc3._promote_step_from_context("optical")
    if "select:optical" not in calls3 or "promote_selected" not in calls3:
        failures.append(f"FAIL: 'optical' overlay must still be promotable (calls={calls3})")

    # 5) The shared UI promote chokepoint guards decorations too (source check --
    #    instantiating the inspector here is heavy/headless-unfriendly).
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    src = inspect.getsource(Kraken3DInspector._promote_step_overlay_to_optical_solid_row)
    if "is_step_overlay_decoration(label)" not in src:
        failures.append(
            "FAIL: _promote_step_overlay_to_optical_solid_row lost its decoration guard "
            "(top-controls 'Promote to Optical Element' could promote a camera/LED)"
        )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0101 decoration overlay must not be promotable as optics")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] LED/camera decorations cannot be promoted/face-assigned as optics; optical overlay still promotes (bugs/0101)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
