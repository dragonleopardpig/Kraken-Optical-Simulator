"""Guard: the detector active-area overlay uses the vendor sensor size.

When a camera is selected, the detector footprint (the orange square in Open 3D
and the 2D layout) must be drawn at the camera's datasheet sensor dimensions --
not the image-surface clear-aperture diameter, which is only a placeholder. The
old behaviour drew a diameter-sized square that fully circumscribed the
image-plane disk, so the "image circle" looked nested inside the "detector
square" (reported via the in-app bug recorder, bug 0031).

All checks are display-free (no Xvfb needed):

1. ``camera_sensor_active_mm`` returns the datasheet active sensor size
   (hr25MCX = 23.04 x 23.04 mm).
2. With that camera selected, the detector ``SceneTarget3D`` resolves its active
   dimensions to the vendor sensor (not the row diameter), so the drawn
   footprint is smaller than the image-plane disk along the axes instead of
   circumscribing it.
3. With no camera selected, the detector falls back to the row diameter
   (unchanged behaviour).
4. An explicit per-row Detector override still wins over the camera sensor --
   the camera only fills in dimensions the user left unset.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_detector_overlay_vendor_sensor

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUT = PROJECT_ROOT / "KrakenOS" / "common_optical_layouts" / "machine_vision_150mm_measured.py"
CAMERA_NAME = "Allied Vision hr25MCX"
SENSOR_MM = (23.04, 23.04)


def _editor_for_camera(camera_model: str):
    from KrakenOS.UI.render_layout_snapshot import (
        _load_layout_module, _rows_from_layout_info, _snapshot_editor,
    )

    module = _load_layout_module(LAYOUT)
    rows = _rows_from_layout_info({"surfaces": list(getattr(module, "SURFACES", []) or [])})
    settings = dict(getattr(module, "SETTINGS", {}) or {})
    settings["camera_model"] = camera_model
    editor = _snapshot_editor(rows, settings)
    editor._normalize_special_rows()
    return editor, editor.rows


def _detector_target(editor):
    from KrakenOS.UI.scene_builder import build_scene_targets

    overrides = editor._camera_detector_active_dims_overrides()
    targets = build_scene_targets(editor.rows, detector_active_dims_overrides=overrides)
    for target in targets:
        if bool(getattr(target, "is_detector", False)):
            return target, overrides
    return None, overrides


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    # 1. Camera database exposes the vendor active sensor size.
    from KrakenOS.UI.camera_database import camera_sensor_active_mm
    from KrakenOS.UI.scene_geometry import scene_target_active_dimensions
    from KrakenOS.UI.scene_builder import _detector_override_dims

    sensor = camera_sensor_active_mm(CAMERA_NAME)
    if sensor is None or abs(sensor[0] - SENSOR_MM[0]) > 1e-6 or abs(sensor[1] - SENSOR_MM[1]) > 1e-6:
        notes.append(f"FAIL: camera_sensor_active_mm({CAMERA_NAME!r}) = {sensor}, expected {SENSOR_MM}")
        passed = False
    if camera_sensor_active_mm("None") is not None:
        notes.append("FAIL: camera_sensor_active_mm('None') should be None")
        passed = False

    if not LAYOUT.exists():
        notes.append("SKIP: machine-vision measured layout unavailable")
        return passed, notes

    # 2. Camera selected -> detector footprint uses the vendor sensor size.
    editor, rows = _editor_for_camera(CAMERA_NAME)
    last_index = len(rows) - 1
    overrides = editor._camera_detector_active_dims_overrides()
    if overrides != {last_index: SENSOR_MM}:
        notes.append(f"FAIL: detector override = {overrides}, expected {{{last_index}: {SENSOR_MM}}}")
        passed = False

    target, _ = _detector_target(editor)
    if target is None:
        notes.append("FAIL: no detector target built for the machine-vision layout")
        passed = False
    else:
        diameter = float(getattr(target, "diameter", 0.0))
        dims = scene_target_active_dimensions(target)
        if dims is None or abs(dims[0] - SENSOR_MM[0]) > 1e-6 or abs(dims[1] - SENSOR_MM[1]) > 1e-6:
            notes.append(f"FAIL: detector active dims {dims}, expected {SENSOR_MM} (vendor sensor)")
            passed = False
        # The drawn sensor half-width must be smaller than the image-plane disk
        # radius so the image circle extends past the sensor edges (the corrected
        # relationship) instead of the square circumscribing the disk.
        if dims is not None and 0.5 * dims[0] >= 0.5 * diameter:
            notes.append(
                f"FAIL: sensor half-width {0.5 * dims[0]:.4g} not smaller than image "
                f"disk radius {0.5 * diameter:.4g} (still circumscribes the circle)"
            )
            passed = False

    # 3. No camera -> fall back to the row diameter (unchanged behaviour).
    editor_none, rows_none = _editor_for_camera("None")
    if editor_none._camera_detector_active_dims_overrides() is not None:
        notes.append("FAIL: no-camera detector override should be None")
        passed = False
    target_none, _ = _detector_target(editor_none)
    if target_none is not None:
        diameter = float(getattr(target_none, "diameter", 0.0))
        dims = scene_target_active_dimensions(target_none)
        if dims is None or abs(dims[0] - diameter) > 1e-6 or abs(dims[1] - diameter) > 1e-6:
            notes.append(f"FAIL: no-camera detector dims {dims}, expected diameter fallback ({diameter}, {diameter})")
            passed = False

    # 4. Explicit per-row Detector override wins over the camera sensor.
    editor_override, rows_override = _editor_for_camera(CAMERA_NAME)
    detector_row = rows_override[len(rows_override) - 1]
    advanced = dict(getattr(detector_row, "advanced", {}) or {})
    advanced["Detector"] = {"active_width_mm": 10.0, "active_height_mm": 12.0}
    detector_row.advanced = advanced
    target_ov, _ = _detector_target(editor_override)
    if target_ov is not None:
        dims = scene_target_active_dimensions(target_ov)
        if dims is None or abs(dims[0] - 10.0) > 1e-6 or abs(dims[1] - 12.0) > 1e-6:
            notes.append(f"FAIL: explicit per-row Detector override {dims}, expected (10.0, 12.0)")
            passed = False

    # Shared override helper used by both overlay and ray hit/miss classification.
    if _detector_override_dims({last_index: SENSOR_MM}, last_index) != SENSOR_MM:
        notes.append("FAIL: _detector_override_dims did not return the vendor sensor for the keyed row")
        passed = False
    if _detector_override_dims({last_index: SENSOR_MM}, last_index + 99) != (0.0, 0.0):
        notes.append("FAIL: _detector_override_dims must return (0, 0) for a non-overridden row")
        passed = False

    if verbose:
        notes.append(
            f"vendor sensor={sensor}; override={overrides}; "
            f"detector dims match sensor; no-camera falls back to diameter; "
            f"explicit per-row override wins"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] detector overlay uses vendor sensor dimensions")
        return 0
    print("[FAIL] detector overlay vendor-sensor guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
