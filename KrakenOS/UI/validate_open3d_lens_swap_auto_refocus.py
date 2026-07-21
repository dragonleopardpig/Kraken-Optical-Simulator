"""Display-free guard for bugs/0388 -- constraint-aware auto-refocus after a lens swap.

A swapped imaging lens focuses at a new plane, but bugs/0383 keeps the camera/mounts at
their absolute positions, so the image lands defocused on the fixed sensor. The swap now
re-solves best focus by moving ONLY the final gap (image distance) via
snap_detector_to_image_plane -- never the beam geometry -- then CLAMPS that gap to a
mechanical minimum so the sensor can't be solved INTO the upstream element (the RA mirror).

This guard pins the clamp/flag/no-op behaviour with a stub editor (no VTK, no trace):
  - snap can't compute (returns False)      -> no-op, no flag, no row mutation
  - snap moves the gap below the floor       -> gap clamped to the floor, user flagged
  - snap moves the gap to a safe distance     -> gap left exactly as solved, no flag
  - a thin fold-mirror reserve below the floor -> min-gap follows the reserve (never over-demands)
  - a layout with no terminal Image row       -> auto-refocus refuses to touch it

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_lens_swap_auto_refocus
"""

from __future__ import annotations

from types import SimpleNamespace


def _editor(rows):
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    ed = LayoutTableWorkbenchMixin.__new__(LayoutTableWorkbenchMixin)
    ed.rows = rows
    ed._status_messages = []
    ed.status_var = SimpleNamespace(set=ed._status_messages.append)
    return ed


def _lens_image_rows(gap):
    return [
        SimpleNamespace(surface="Object", thickness=10.0, name="Object"),
        SimpleNamespace(surface="Standard", thickness=gap, name="Rear Datum"),
        SimpleNamespace(surface="Image", thickness=0.0, name="Image"),
    ]


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    # 1. snap can't compute -> no-op (no mutation, no flag)
    ed = _editor(_lens_image_rows(100.0))
    ed.snap_detector_to_image_plane = lambda: False
    ed._swap_auto_refocus_to_best_focus()
    if ed.rows[-2].thickness != 100.0:
        failures.append("no-op: a snap that can't compute must not move the gap")
    if ed._status_messages:
        failures.append("no-op: a snap that can't compute must not flag the user")

    # 2. snap moves BELOW the floor -> clamp to floor + flag
    ed = _editor(_lens_image_rows(100.0))
    floor = ed._swap_refocus_min_gap()
    ed.snap_detector_to_image_plane = lambda: (
        setattr(ed.rows[-2], "thickness", 0.5) or True
    )
    ed._swap_auto_refocus_to_best_focus()
    if abs(ed.rows[-2].thickness - floor) > 1e-9:
        failures.append(f"clamp: a sub-floor solve must clamp to {floor} (got {ed.rows[-2].thickness})")
    if not any("focus limited" in m for m in ed._status_messages):
        failures.append("clamp: a clamped refocus must flag the user")

    # 3. snap moves to a SAFE distance -> left as solved, no flag
    ed = _editor(_lens_image_rows(100.0))
    ed.snap_detector_to_image_plane = lambda: (
        setattr(ed.rows[-2], "thickness", 47.0) or True
    )
    ed._swap_auto_refocus_to_best_focus()
    if abs(ed.rows[-2].thickness - 47.0) > 1e-9:
        failures.append("safe: a safe solve must be left exactly as computed")
    if any("focus limited" in m for m in ed._status_messages):
        failures.append("safe: a safe refocus must NOT flag the user")

    # 4. thin fold-mirror reserve below the floor -> min-gap follows the reserve
    rows = [
        SimpleNamespace(surface="Object", thickness=10.0, name="Object"),
        SimpleNamespace(surface="Standard", thickness=120.0, name="Front Datum"),
        SimpleNamespace(surface="Standard", thickness=0.8, name="Promoted RA Mirror"),
        SimpleNamespace(surface="Image", thickness=0.0, name="Image"),
    ]
    ed = _editor(rows)
    if abs(ed._swap_refocus_min_gap() - 0.8) > 1e-9:
        failures.append("reserve: a thin promoted mirror's reserve must cap the min-gap (never over-demand)")

    # 5. no terminal Image row -> refuse
    rows = [
        SimpleNamespace(surface="Object", thickness=10.0, name="Object"),
        SimpleNamespace(surface="Standard", thickness=100.0, name="Rear Datum"),
        SimpleNamespace(surface="Standard", thickness=5.0, name="Detector"),
    ]
    ed = _editor(rows)
    ed.snap_detector_to_image_plane = lambda: (_ for _ in ()).throw(AssertionError("snap must not run"))
    try:
        ed._swap_auto_refocus_to_best_focus()
    except AssertionError as exc:
        failures.append(f"guard: {exc}")

    # 6. bugs/0391: a GLUED CAMERA reserves its whole body -- min-gap = clearance + the
    # flange-to-sensor depth, so the body (not just the sensor plane) clears the upstream
    # element. The camera-body depth must WIN over a thin fold-mirror reserve (the 0388 bug).
    STANDOFF = 11.48  # hr25MCX flange-to-sensor
    clearance = float(_editor(_lens_image_rows(100.0))._SWAP_REFOCUS_MIN_CLEARANCE_MM)
    cam_rows = [
        SimpleNamespace(surface="Object", thickness=10.0, name="Object"),
        SimpleNamespace(surface="Standard", thickness=120.0, name="Front Datum"),
        SimpleNamespace(surface="Standard", thickness=0.8, name="Promoted RA Mirror"),
        SimpleNamespace(surface="Image", thickness=0.0, name="Image"),
    ]
    ed = _editor(cam_rows)
    ed._current_camera_front_to_sensor_mm = lambda: STANDOFF
    want = clearance + STANDOFF
    got = ed._swap_refocus_min_gap()
    if abs(got - want) > 1e-9:
        failures.append(
            f"camera-body: min-gap must reserve the flange depth ({want} = {clearance}+{STANDOFF}); "
            f"got {got} (thin-mirror reserve wrongly capped the camera body)"
        )
    # the clamp must actually pull a too-close best-focus back to the body-clearance gap
    ed2 = _editor(_lens_image_rows(100.0))
    ed2._current_camera_front_to_sensor_mm = lambda: STANDOFF
    ed2.snap_detector_to_image_plane = lambda: (setattr(ed2.rows[-2], "thickness", 3.0) or True)
    ed2._swap_auto_refocus_to_best_focus()
    if abs(ed2.rows[-2].thickness - want) > 1e-9:
        failures.append(
            f"camera-body: a 3mm best-focus (sensor-safe but body-colliding) must clamp to {want}; "
            f"got {ed2.rows[-2].thickness}"
        )
    if not any("camera body" in m for m in ed2._status_messages):
        failures.append("camera-body: the clamp must flag that the camera body limited focus")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Lens-swap auto-refocus validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Lens-swap auto-refocus validation passed: snap-can't-compute no-ops, a sub-floor "
        "solve clamps + flags, a safe solve is untouched, a thin fold-mirror reserve caps the "
        "min-gap, an Image-less layout is refused, and a glued camera reserves its whole body "
        "depth (bugs/0391)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
