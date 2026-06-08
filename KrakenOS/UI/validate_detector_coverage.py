"""Guard: the detector coverage overlay shows the sensor inside the image circle.

Reported via the in-app recorder (bug 0032): the cyan disk drawn at the image
plane sat *inside* the square sensor, so the corners fell outside the imaged
field and vignetted. The correct camera relationship is the opposite -- the
sensor must sit inside the image circle (corners included). The overlay now
draws the **real ray-traced image circle** (the field's max real image height),
colours it cyan when it covers the sensor corners and amber when it does not,
and -- when it does not -- adds a dashed "required" ring at the sensor
half-diagonal plus a debug suggestion telling the user which Real Image Height
closes the gap. The object plane gets an FOV **rectangle** (sensor / |m|),
matching the sensor shape rather than a circle.

All checks are display-free (no Xvfb needed):

1. ``camera_image_coverage_mm`` returns the sensor diagonal + half-diagonal
   (hr25MCX = Ø32.58 mm / 16.29 mm), and ``None`` with no camera.
2. ``detector_coverage_metrics`` reports *not covered* at the default real image
   height (11.52 < half-diagonal 16.29) and names 16.29 as the required height;
   it reports *covered* once the radius reaches the half-diagonal. The object
   FOV half-extents are the sensor half-extents divided by |m|.
3. ``detector_coverage_overlay_specs`` emits the object FOV rectangle (finite
   object only), the image circle (amber when short, cyan when covering), and
   the dashed required ring **only** when the circle is short; the polyline
   geometry matches the metric radii / extents.
4. End to end on the machine-vision layout + hr25MCX: the service's own data
   lookups (sensor dims, image-circle radius, magnification, finite object) feed
   a *not covered* result, and simulating the camera-select auto-fill (image
   diameter -> diagonal, Real Image Height -> half-diagonal) re-traces to a
   covering image circle.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_detector_coverage

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUT = PROJECT_ROOT / "KrakenOS" / "common_optical_layouts" / "machine_vision_150mm_measured.py"
CAMERA_NAME = "Allied Vision hr25MCX"
SENSOR_MM = (23.04, 23.04)
MAG = 1.1467050566078587  # finite paraxial |m| for the measured 150 mm layout
DEFAULT_RIH = 11.52       # the layout's stock Real Image Height (does not cover)

_CYAN = (0.2, 0.7, 1.0)
_AMBER = (1.0, 0.55, 0.1)
_GREEN = (0.2, 0.9, 0.35)


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


class _InspectorStub:
    """Minimal inspector for the service's display-free data lookups."""

    def __init__(self, editor):
        self.editor = editor


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    from KrakenOS.UI.camera_database import camera_image_coverage_mm
    from KrakenOS.UI.services.detector_coverage_overlay import (
        DetectorCoverageOverlayService,
        detector_coverage_label_specs,
        detector_coverage_metrics,
        detector_coverage_overlay_specs,
    )

    half_diag = math.hypot(SENSOR_MM[0] / 2.0, SENSOR_MM[1] / 2.0)  # 16.2917
    diagonal = 2.0 * half_diag

    # 1. Camera coverage helper: diagonal + half-diagonal, None without a camera.
    coverage = camera_image_coverage_mm(CAMERA_NAME)
    if coverage is None or abs(coverage[0] - diagonal) > 1e-3 or abs(coverage[1] - half_diag) > 1e-3:
        notes.append(
            f"FAIL: camera_image_coverage_mm({CAMERA_NAME!r}) = {coverage}, "
            f"expected (~{diagonal:.4g}, ~{half_diag:.4g})"
        )
        passed = False
    if camera_image_coverage_mm("None") is not None:
        notes.append("FAIL: camera_image_coverage_mm('None') should be None")
        passed = False

    # 2. Metrics: short at the default height, covering at the half-diagonal.
    short = detector_coverage_metrics(SENSOR_MM[0], SENSOR_MM[1], DEFAULT_RIH, MAG)
    if short.covers:
        notes.append(f"FAIL: radius {DEFAULT_RIH} should NOT cover the {SENSOR_MM} sensor")
        passed = False
    if abs(short.sensor_half_diagonal - half_diag) > 1e-6:
        notes.append(f"FAIL: sensor_half_diagonal {short.sensor_half_diagonal:.6g}, expected {half_diag:.6g}")
        passed = False
    if abs(short.required_real_image_height - half_diag) > 1e-6:
        notes.append(
            f"FAIL: required_real_image_height {short.required_real_image_height:.6g}, "
            f"expected {half_diag:.6g}"
        )
        passed = False
    obj_half_expected = (SENSOR_MM[0] / 2.0) / MAG
    if abs(short.object_fov_half_width - obj_half_expected) > 1e-6 or abs(short.object_fov_half_height - obj_half_expected) > 1e-6:
        notes.append(
            f"FAIL: object FOV half-extent ({short.object_fov_half_width:.6g}, "
            f"{short.object_fov_half_height:.6g}), expected {obj_half_expected:.6g} (= sensor/2 / |m|)"
        )
        passed = False

    covering = detector_coverage_metrics(SENSOR_MM[0], SENSOR_MM[1], half_diag, MAG)
    if not covering.covers:
        notes.append(f"FAIL: radius {half_diag:.6g} (half-diagonal) should cover the sensor")
        passed = False
    # Infinite-conjugate (no magnification) has no finite object FOV.
    no_mag = detector_coverage_metrics(SENSOR_MM[0], SENSOR_MM[1], DEFAULT_RIH, None)
    if no_mag.object_fov_half_width != 0.0 or no_mag.object_fov_half_height != 0.0:
        notes.append("FAIL: object FOV half-extents must be 0 when magnification is unknown")
        passed = False

    # 3. Overlay spec geometry / colours.
    obj_pt = np.array([0.0, 0.0, 0.0])
    img_pt = np.array([0.0, 0.0, 100.0])

    short_specs = detector_coverage_overlay_specs(obj_pt, img_pt, short, object_mode_finite=True)
    kinds = [s["kind"] for s in short_specs]
    if kinds != ["object_fov_rect", "image_circle", "required_image_circle"]:
        notes.append(f"FAIL: short/finite spec kinds {kinds}, expected object_fov_rect, image_circle, required_image_circle")
        passed = False
    by_kind = {s["kind"]: s for s in short_specs}

    if "image_circle" in by_kind:
        spec = by_kind["image_circle"]
        if tuple(spec["color"]) != _AMBER:
            notes.append(f"FAIL: short image circle colour {spec['color']}, expected amber {_AMBER}")
            passed = False
        radii = np.linalg.norm(np.asarray(spec["points"]) - img_pt, axis=1)
        if abs(float(radii.max()) - DEFAULT_RIH) > 1e-6:
            notes.append(f"FAIL: image circle radius {float(radii.max()):.6g}, expected {DEFAULT_RIH}")
            passed = False

    if "required_image_circle" in by_kind:
        spec = by_kind["required_image_circle"]
        if not bool(spec["dashed"]):
            notes.append("FAIL: required image circle must be dashed")
            passed = False
        radii = np.linalg.norm(np.asarray(spec["points"]) - img_pt, axis=1)
        if abs(float(radii.max()) - half_diag) > 1e-6:
            notes.append(f"FAIL: required ring radius {float(radii.max()):.6g}, expected {half_diag:.6g}")
            passed = False

    if "object_fov_rect" in by_kind:
        spec = by_kind["object_fov_rect"]
        if tuple(spec["color"]) != _GREEN:
            notes.append(f"FAIL: object FOV rect colour {spec['color']}, expected green {_GREEN}")
            passed = False
        pts = np.asarray(spec["points"])
        ext_x = 0.5 * (float(pts[:, 0].max()) - float(pts[:, 0].min()))
        ext_y = 0.5 * (float(pts[:, 1].max()) - float(pts[:, 1].min()))
        if abs(ext_x - obj_half_expected) > 1e-6 or abs(ext_y - obj_half_expected) > 1e-6:
            notes.append(
                f"FAIL: object FOV rect half-extents ({ext_x:.6g}, {ext_y:.6g}), expected {obj_half_expected:.6g}"
            )
            passed = False

    # Covering: cyan image circle, NO required ring.
    cover_specs = detector_coverage_overlay_specs(obj_pt, img_pt, covering, object_mode_finite=True)
    cover_kinds = [s["kind"] for s in cover_specs]
    if "required_image_circle" in cover_kinds:
        notes.append("FAIL: covering case must not draw the dashed required ring")
        passed = False
    cover_circle = next((s for s in cover_specs if s["kind"] == "image_circle"), None)
    if cover_circle is None or tuple(cover_circle["color"]) != _CYAN:
        notes.append(f"FAIL: covering image circle must be cyan {_CYAN}, got {cover_circle and cover_circle['color']}")
        passed = False

    # Infinite object: no object FOV rectangle.
    inf_specs = detector_coverage_overlay_specs(obj_pt, img_pt, short, object_mode_finite=False)
    if any(s["kind"] == "object_fov_rect" for s in inf_specs):
        notes.append("FAIL: infinite-object overlay must not draw an object FOV rectangle")
        passed = False

    # 5. Direct 3D label specs (bug 0033 fix b): every coverage element is named,
    #    the texts carry the live dimensions, and the same-plane labels never
    #    overlap (distinct clock angles outside each element).
    def _same_plane_min_sep(specs, plane_pt) -> float:
        on_plane = [np.asarray(s["anchor"], dtype=float) for s in specs
                    if abs(float(np.asarray(s["anchor"], dtype=float)[2]) - float(plane_pt[2])) < 1e-6]
        best = float("inf")
        for i in range(len(on_plane)):
            for j in range(i + 1, len(on_plane)):
                best = min(best, float(np.linalg.norm(on_plane[i] - on_plane[j])))
        return best

    short_labels = detector_coverage_label_specs(obj_pt, img_pt, short, object_mode_finite=True)
    short_texts = [s["text"] for s in short_labels]
    expected_short = [
        f"Sensor {SENSOR_MM[0]:.1f}×{SENSOR_MM[1]:.1f}",
        f"Image circle Ø{2 * DEFAULT_RIH:.1f} (short)",
        f"Needs Ø{diagonal:.1f}",
        f"FOV {2 * obj_half_expected:.1f}×{2 * obj_half_expected:.1f}",
    ]
    if short_texts != expected_short:
        notes.append(f"FAIL: short label texts {short_texts}, expected {expected_short}")
        passed = False
    short_sep = _same_plane_min_sep(short_labels, img_pt)
    if short_sep < 10.0:
        notes.append(f"FAIL: short image-plane labels too close (min sep {short_sep:.3g} mm < 10)")
        passed = False

    cover_labels = detector_coverage_label_specs(obj_pt, img_pt, covering, object_mode_finite=True)
    cover_texts = [s["text"] for s in cover_labels]
    expected_cover = [
        f"Sensor {SENSOR_MM[0]:.1f}×{SENSOR_MM[1]:.1f}",
        f"Image circle Ø{diagonal:.1f}",
        f"FOV {2 * obj_half_expected:.1f}×{2 * obj_half_expected:.1f}",
    ]
    if cover_texts != expected_cover:
        notes.append(f"FAIL: covering label texts {cover_texts}, expected {expected_cover} (no 'Needs' when covering)")
        passed = False
    cover_sep = _same_plane_min_sep(cover_labels, img_pt)
    if cover_sep < 10.0:
        notes.append(f"FAIL: covering image-plane labels too close (min sep {cover_sep:.3g} mm < 10)")
        passed = False

    # Infinite object: no FOV label (the object plane has no rectangle to name).
    inf_labels = detector_coverage_label_specs(obj_pt, img_pt, short, object_mode_finite=False)
    if any(s["text"].startswith("FOV") for s in inf_labels):
        notes.append("FAIL: infinite-object labels must not include an FOV label")
        passed = False

    if not LAYOUT.exists():
        notes.append("SKIP: machine-vision measured layout unavailable")
        return passed, notes

    # 4. End to end on the real layout: the service's data lookups feed a NOT
    #    covered result, and the auto-fill simulation re-traces to a cover.
    from KrakenOS.UI.scene_builder import build_scene_targets

    editor, rows = _editor_for_camera(CAMERA_NAME)
    service = DetectorCoverageOverlayService(_InspectorStub(editor), pv_module=None)

    overrides = editor._camera_detector_active_dims_overrides()
    targets = build_scene_targets(editor.rows, detector_active_dims_overrides=overrides)
    detector = next((t for t in targets if bool(getattr(t, "is_detector", False))), None)
    if detector is None:
        notes.append("FAIL: no detector target built for the machine-vision layout")
        passed = False
    else:
        sensor = service._sensor_dimensions(detector)
        radius = service._image_circle_radius()
        if sensor is None or abs(sensor[0] - SENSOR_MM[0]) > 1e-6 or abs(sensor[1] - SENSOR_MM[1]) > 1e-6:
            notes.append(f"FAIL: service sensor dims {sensor}, expected {SENSOR_MM}")
            passed = False
        if radius is None or abs(radius - DEFAULT_RIH) > 1e-6:
            notes.append(f"FAIL: service image-circle radius {radius}, expected {DEFAULT_RIH}")
            passed = False
        if not service._is_finite_object():
            notes.append("FAIL: machine-vision layout should be a finite object")
            passed = False
        if sensor is not None and radius is not None:
            live = detector_coverage_metrics(sensor[0], sensor[1], radius, service._magnification())
            if live.covers:
                notes.append("FAIL: stock layout should report the image circle does NOT cover the sensor")
                passed = False

        # Simulate the camera-select auto-fill: image diameter -> diagonal,
        # Real Image Height -> half-diagonal; the re-trace must now cover.
        img_diam, rih = camera_image_coverage_mm(CAMERA_NAME)
        editor.rows[-1].diameter = float(img_diam)
        editor.field_type_var.set(editor._field_type_display_label("Real Image Height"))
        editor._last_field_type = "Real Image Height"
        editor.field_value_var.set(f"{float(rih):.6g}")
        new_radius = service._image_circle_radius()
        if new_radius is None:
            notes.append("FAIL: auto-fill simulation produced no image-circle radius")
            passed = False
        else:
            filled = detector_coverage_metrics(SENSOR_MM[0], SENSOR_MM[1], new_radius, MAG)
            if not filled.covers:
                notes.append(
                    f"FAIL: after auto-fill (RIH -> {rih:.6g}) the image circle (r={new_radius:.6g}) "
                    f"still does not cover the sensor (half-diag {half_diag:.6g})"
                )
                passed = False

    # 6. bug 0033 fix a: a layout LOAD that restores a camera now calls
    #    ``_apply_camera_coverage_autofill`` so it lands covered without an
    #    interactive dropdown commit. The method body mutates Tk widgets
    #    (``_sync_field_mode_ui``), so the *end-to-end* load path is exercised
    #    live in the penta harness (Phase 39); here we just guard that the
    #    extracted helper still exists and is callable (a rename / removal would
    #    silently take the load-time auto-fill with it).
    if not callable(getattr(editor, "_apply_camera_coverage_autofill", None)):
        notes.append("FAIL: editor lost the _apply_camera_coverage_autofill helper (load auto-fill would break)")
        passed = False

    if verbose:
        notes.append(
            f"coverage helper={coverage}; default RIH {DEFAULT_RIH} short of half-diag {half_diag:.4g}; "
            f"object FOV {obj_half_expected:.4g} (= sensor/2 / |m|); auto-fill covers; "
            f"labels short={short_texts} cover={cover_texts}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] detector coverage overlay: sensor inside the real image circle")
        return 0
    print("[FAIL] detector coverage guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
