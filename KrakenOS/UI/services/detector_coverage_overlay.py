"""Detector coverage overlays for Open 3D: real image circle + object FOV box.

Drawn during the scene refresh when the detector overlay ("Det") is enabled and
the system images a finite object. They answer the question "does the lens's
image circle cover the sensor?" -- the thing the in-app bug recorder kept
flagging as "the circular image is inside the square sensor" (bugs 0031, 0032).

* Image plane -- the **real** image circle at the field's max real image height
  (the actual ray-traced coverage), drawn cyan when it covers the rectangular
  sensor (corners included) and amber when it does not. When it does not cover,
  a dashed amber "required" ring is added at the sensor half-diagonal so the gap
  the user must close is visible, and a suggestion is surfaced to the debug log.
* Object plane -- the field-of-view **rectangle** (not a circle) that maps onto
  the sensor, sized ``sensor / |m|``, matching the sensor's shape.

The image-circle radius and coverage are pure geometry (``detector_coverage_metrics``
and ``detector_coverage_overlay_specs``) so they can be validated display-free.
The full refresh calls ``RemoveAllViewProps`` first, so overlays are simply
re-added each refresh; no separate actor lifecycle is needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


# Overlay colours.
_IMAGE_CIRCLE_COVERS = (0.2, 0.7, 1.0)      # cyan -- image circle covers sensor
_IMAGE_CIRCLE_SHORT = (1.0, 0.55, 0.1)      # amber -- image circle too small
_REQUIRED_RING = (1.0, 0.55, 0.1)           # amber dashed -- required image circle
_OBJECT_FOV = (0.2, 0.9, 0.35)              # green -- object-plane FOV rectangle

# Coverage tolerance in mm. 1 micron is physically negligible (under a quarter
# of the 4.5 um sensor pixel) yet wide enough to absorb the 6-significant-figure
# rounding of the Real Image Height shown in the panel, so the "set Real Image
# Height to X" suggestion is self-consistent: setting exactly X then covers.
_COVER_EPS = 1e-3


@dataclass(frozen=True)
class DetectorCoverageMetrics:
    """Coverage relationship between the image circle and the sensor."""

    sensor_half_width: float
    sensor_half_height: float
    sensor_half_diagonal: float
    image_circle_radius: float
    covers: bool
    required_real_image_height: float
    object_fov_half_width: float
    object_fov_half_height: float


def detector_coverage_metrics(
    sensor_width: float,
    sensor_height: float,
    image_circle_radius: float,
    magnification: float | None,
) -> DetectorCoverageMetrics:
    """Does the real image circle cover the rectangular sensor?

    ``image_circle_radius`` is the field's max real image (semi-)height -- the
    actual ray-traced coverage radius. The sensor is covered when that radius
    reaches the sensor *corner* (half-diagonal). The object FOV box is the sensor
    scaled back by the magnification, ``sensor / |m|``.
    """
    half_w = max(float(sensor_width), 0.0) / 2.0
    half_h = max(float(sensor_height), 0.0) / 2.0
    half_diag = float((half_w * half_w + half_h * half_h) ** 0.5)
    radius = max(float(image_circle_radius), 0.0)
    covers = radius >= half_diag - _COVER_EPS
    try:
        mag = abs(float(magnification)) if magnification is not None else 0.0
    except (TypeError, ValueError):
        mag = 0.0
    if mag > 1e-9:
        object_half_w = half_w / mag
        object_half_h = half_h / mag
    else:
        object_half_w = 0.0
        object_half_h = 0.0
    return DetectorCoverageMetrics(
        sensor_half_width=half_w,
        sensor_half_height=half_h,
        sensor_half_diagonal=half_diag,
        image_circle_radius=radius,
        covers=covers,
        required_real_image_height=half_diag,
        object_fov_half_width=object_half_w,
        object_fov_half_height=object_half_h,
    )


def _basis(axis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    norm = float(np.linalg.norm(axis))
    axis = axis / norm if norm > 1e-9 else np.array([0.0, 0.0, 1.0])
    ref = np.array([0.0, 0.0, 1.0]) if abs(axis[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(axis, ref)
    nu = float(np.linalg.norm(u))
    u = u / nu if nu > 1e-9 else np.array([1.0, 0.0, 0.0])
    v = np.cross(axis, u)
    return u, v


def _circle_points(center, u, v, radius, n=72):
    th = np.linspace(0.0, 2.0 * np.pi, n, endpoint=True)
    return center + radius * (np.outer(np.cos(th), u) + np.outer(np.sin(th), v))


def _rect_points(center, u, v, half_w, half_h):
    return np.array([
        center + half_w * u + half_h * v,
        center - half_w * u + half_h * v,
        center - half_w * u - half_h * v,
        center + half_w * u - half_h * v,
        center + half_w * u + half_h * v,
    ])


def detector_coverage_overlay_specs(
    object_point,
    image_point,
    metrics: DetectorCoverageMetrics,
    *,
    object_mode_finite: bool = True,
) -> list[dict[str, Any]]:
    """Build the overlay polyline specs (pure geometry, no pyvista).

    Each spec is ``{"kind", "points", "color", "dashed", "line_width"}``. The
    object-plane FOV rectangle is emitted only for a finite object (it has no
    finite size at infinity).
    """
    obj_pt = np.asarray(object_point, dtype=float).reshape(3)
    img_pt = np.asarray(image_point, dtype=float).reshape(3)
    u, v = _basis(img_pt - obj_pt)
    specs: list[dict[str, Any]] = []

    # Object plane: FOV rectangle sized sensor / |m| (matches the sensor shape).
    if object_mode_finite and metrics.object_fov_half_width > 1e-9 and metrics.object_fov_half_height > 1e-9:
        specs.append(
            {
                "kind": "object_fov_rect",
                "points": _rect_points(obj_pt, u, v, metrics.object_fov_half_width, metrics.object_fov_half_height),
                "color": _OBJECT_FOV,
                "dashed": False,
                "line_width": 2.5,
            }
        )

    # Image plane: the real image circle (cyan when it covers the sensor).
    if metrics.image_circle_radius > 1e-9:
        specs.append(
            {
                "kind": "image_circle",
                "points": _circle_points(img_pt, u, v, metrics.image_circle_radius),
                "color": _IMAGE_CIRCLE_COVERS if metrics.covers else _IMAGE_CIRCLE_SHORT,
                "dashed": False,
                "line_width": 2.5,
            }
        )

    # When it does not cover, a dashed ring at the sensor diagonal shows the
    # image circle the design needs to reach the corners.
    if not metrics.covers and metrics.sensor_half_diagonal > 1e-9:
        specs.append(
            {
                "kind": "required_image_circle",
                "points": _circle_points(img_pt, u, v, metrics.sensor_half_diagonal),
                "color": _REQUIRED_RING,
                "dashed": True,
                "line_width": 2.0,
            }
        )
    return specs


class DetectorCoverageOverlayService:
    """Render the image-circle / object-FOV coverage overlays for Open 3D."""

    def __init__(self, inspector: Any, *, pv_module: Any) -> None:
        self.inspector = inspector
        self.editor = inspector.editor
        self._pv = pv_module

    # ----------------------------------------------------------- data lookups
    def _detector_target(self, scene_bundle: Any):
        for target in list(getattr(scene_bundle, "targets", []) or []):
            if bool(getattr(target, "is_detector", False)):
                return target
        return None

    def _sensor_dimensions(self, target) -> tuple[float, float] | None:
        from KrakenOS.UI.scene_geometry import scene_target_active_dimensions

        dims = scene_target_active_dimensions(target)
        if dims is None:
            return None
        return float(dims[0]), float(dims[1])

    def _image_circle_radius(self) -> float | None:
        try:
            summary = self.editor._field_metrics_summary()
        except Exception:
            return None
        try:
            radius = float(summary.get("max_real_image_height"))
        except (TypeError, ValueError):
            return None
        return radius if np.isfinite(radius) and radius > 0.0 else None

    def _magnification(self) -> float | None:
        try:
            mag = self.editor._current_finite_paraxial_magnification()
        except Exception:
            return None
        if mag is None or not np.isfinite(mag):
            return None
        return float(mag)

    def _is_finite_object(self) -> bool:
        try:
            return str(self.editor._current_object_mode()) == "Finite"
        except Exception:
            return False

    # ---------------------------------------------------------------- render
    def _line_actor(self, points, color, width, dashed: bool) -> bool:
        pv = self._pv
        if pv is None:
            return False
        try:
            pts = np.asarray(points, dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
                return False
            if dashed:
                cells = []
                for i in range(0, len(pts) - 1, 2):
                    cells += [2, i, i + 1]
                if not cells:
                    return False
                mesh = pv.PolyData(pts[:, :3], lines=np.asarray(cells, dtype=np.int64))
                opacity = 0.9
            else:
                mesh = pv.lines_from_points(pts[:, :3])
                opacity = 1.0
            self.inspector._add_mesh_actor(mesh, color=tuple(color), line_width=float(width), opacity=opacity)
            return True
        except Exception as exc:  # pragma: no cover - defensive
            self.editor.append_debug(f"Detector coverage overlay skipped: {exc}")
            return False

    def add_overlays(self, system: Any, scene_bundle: Any = None) -> int:
        if scene_bundle is None:
            return 0
        target = self._detector_target(scene_bundle)
        if target is None:
            return 0
        sensor = self._sensor_dimensions(target)
        image_radius = self._image_circle_radius()
        if sensor is None or image_radius is None:
            return 0
        finite = self._is_finite_object()
        mag = self._magnification() if finite else None
        metrics = detector_coverage_metrics(sensor[0], sensor[1], image_radius, mag)

        rows = getattr(self.editor, "rows", None) or []
        if not rows:
            return 0
        try:
            obj_pt = self.editor._surface_reference_world_point(0, system=system)
            img_pt = self.editor._surface_reference_world_point(len(rows) - 1, system=system)
        except Exception as exc:
            self.editor.append_debug(f"Detector coverage overlay reference points unavailable: {exc}")
            return 0

        specs = detector_coverage_overlay_specs(obj_pt, img_pt, metrics, object_mode_finite=finite)
        count = 0
        for spec in specs:
            if self._line_actor(spec["points"], spec["color"], spec["line_width"], bool(spec["dashed"])):
                count += 1

        if not metrics.covers and metrics.image_circle_radius > 0.0:
            self.editor.append_debug(
                "Detector coverage: image circle "
                f"Ø{2 * metrics.image_circle_radius:.4g} mm does not cover the "
                f"{2 * metrics.sensor_half_width:.4g}×{2 * metrics.sensor_half_height:.4g} mm sensor "
                f"(needs Ø{2 * metrics.sensor_half_diagonal:.4g}). "
                f"Set Field Real Image Height to {metrics.required_real_image_height:.4g} mm."
            )
        return count
