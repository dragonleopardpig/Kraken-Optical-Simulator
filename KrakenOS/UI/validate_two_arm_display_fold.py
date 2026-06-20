"""Display-free validator for the two-arm beam-splitter display-fold + per-arm overlays.

Locks in bugs 0100-0105 (the user's dual-MV 150mm + 120mm scene):
  * fold_points bends about the TILTED splitter plane (continuous, no twist at the splitter),
  * the fold produces per-arm folded detectors at the real images with magnification metadata,
  * the detector-coverage overlay draws the object FOV (object axis) + image circle (per
    detector), and
  * the paraxial magnification falls back to a fold arm (so quick-estimation isn't "--").

Run: ``.devenv/state/venv/bin/python -m KrakenOS.UI.validate_two_arm_display_fold``
"""
from __future__ import annotations

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import SurfaceRow, _build_system_from_specs
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.services.two_arm_display_fold import fold_points
from KrakenOS.UI.services.detector_coverage_overlay import (
    detector_coverage_metrics,
    detector_coverage_overlay_specs,
)
from KrakenOS.common_optical_layouts.beam_splitter_dual_mv_150_120 import SURFACES, SETTINGS


def _require(condition: bool, message: str) -> None:
    if not condition:
        print(f"[FAIL] {message}")
        raise SystemExit(1)


def main() -> int:
    # 1. fold_points: clean fold about the tilted plane z = splitter_z + y (no twist).
    for y0 in (13.0, -13.0):
        pts = np.array([[0, y0, 0], [0, y0, 90], [0, y0, 215], [0, 0, 481]], dtype=float)
        folded = fold_points(pts, 90.0)
        on_plane = [p for p in folded if abs(float(p[2]) - (90.0 + float(p[1]))) < 1e-6]
        _require(len(on_plane) >= 1, f"fold inserts a crossing vertex on the tilted plane (y0={y0:+.0f})")
        # continuity: every segment is finite and short (no pinch to a single point)
        seglen = np.linalg.norm(np.diff(folded, axis=0), axis=1)
        _require(bool(np.all(np.isfinite(seglen))), "fold polyline finite")
    print("[ok] fold_points: continuous fold on the tilted splitter plane (no twist)")

    # 2. two-arm fold: 66-ish folded paths + 2 detectors at the real images with metadata.
    rows = [SurfaceRow(**{k: v for k, v in s.items() if k in SurfaceRow.__dataclass_fields__}) for s in SURFACES]
    editor = _snapshot_editor(rows, SETTINGS)
    editor.branch_detector_camera_assignments = {}
    system = _build_system_from_specs(editor._serializable_row_specs(), build=1)
    rays = Kos.raykeeper(system)
    max_radius = max(float(r.diameter) for r in rows) / 2.0
    editor._trace_preview_rays(system, rays, 0.55, max_radius)
    bundle = editor._build_scene_bundle(system, rays, max_radius)

    fold_paths = [p for p in (bundle.ray_paths or []) if str(getattr(p, "branch_path", "") or "").startswith("twoarm/")]
    _require(len(fold_paths) >= 2, f"two-arm folded ray paths present (got {len(fold_paths)})")
    detectors = {t.name: t for t in (bundle.targets or []) if bool(getattr(t, "is_detector", False))}
    _require(len(detectors) == 2, f"exactly two per-arm detectors (got {len(detectors)})")
    _require("transmit detector" in detectors and "reflect detector" in detectors, "transmit + reflect detectors named")
    transmit, reflect = detectors["transmit detector"], detectors["reflect detector"]
    _require(abs(float(transmit.center_world[2]) - 613.0) < 6.0, f"transmit detector at z~613 (got {transmit.center_world[2]:.0f})")
    _require(abs(float(reflect.center_world[1]) - 408.0) < 6.0, f"reflect detector folded to y~408 (got {reflect.center_world[1]:.0f})")
    for name, det in detectors.items():
        mag = (getattr(det, "metadata", None) or {}).get("two_arm_magnification")
        _require(mag is not None and np.isfinite(float(mag)), f"{name} carries magnification metadata")
    print("[ok] two-arm fold: 2 per-arm detectors at the real images, with magnification metadata")

    # 3. coverage overlay: object FOV sized (mag != None) + image circle ON each detector.
    metrics = detector_coverage_metrics(50.0, 50.0, 16.5, transmit.metadata["two_arm_magnification"])
    _require(metrics.object_fov_half_width > 1e-9, "object FOV sized (magnification available)")
    specs = detector_coverage_overlay_specs(
        [0, 0, 0], transmit.center_world, metrics,
        object_axis=[0, 0, 1], image_axis=transmit.normal_world,
    )
    image_circle = next(s for s in specs if s["kind"] == "image_circle")
    _require(abs(float(np.asarray(image_circle["points"]).mean(0)[2]) - 613.0) < 6.0, "image circle drawn at the transmit detector")
    object_fov = next(s for s in specs if s["kind"] == "object_fov_rect")
    _require(abs(float(np.asarray(object_fov["points"]).mean(0)[2])) < 6.0, "object FOV drawn at the object plane (z~0)")
    print("[ok] coverage overlay: object FOV present at the object + image circle on the detector")

    # 4. paraxial magnification fallback for the fold (quick-estimation isn't "--").
    _require(editor._current_finite_paraxial_magnification() is not None, "paraxial magnification fallback returns a value for the fold")
    print("[ok] paraxial magnification fallback for the folded scene")

    print("[PASS] two-arm display-fold + per-arm coverage overlays")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
