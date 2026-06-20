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
_SENSOR_FOOTPRINT = (0.98, 0.45, 0.05)      # amber -- vendor sensor square (bug 0031)

# Direct 3D label placement. Each label is anchored just outside its element on
# the plane, at a distinct clock angle so the (billboarded) labels never overlap
# each other or the geometry (bug 0033 -- the user could not tell the overlay
# elements apart). ``_LABEL_GAP`` is a small absolute world margin so even a
# tiny element still gets a readable standoff.
_LABEL_GAP = 0.6      # mm standoff beyond the radial placement
_LABEL_MARGIN = 0.10  # fraction of the element radius added before the gap

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


def pick_fill_rect_points(center, u, v, half_w, half_h):
    """The 4 corners of the faint pickable FOV fill, in the same orientation as
    the green object-FOV edge from ``detector_coverage_overlay_specs``: width
    (``half_w``) spans the horizontal axis ``v`` and height (``half_h``) the
    vertical axis ``u`` (``_basis`` returns u=+Y vertical, v horizontal). Sharing
    this with the edge keeps the shaded fill coincident with its own outline for a
    landscape sensor (bugs/0069 fixed the edge; bugs/0072 the lagging fill)."""
    return _rect_points(center, v, u, half_w, half_h)[:4]


def detector_coverage_overlay_specs(
    object_point,
    image_point,
    metrics: DetectorCoverageMetrics,
    *,
    object_mode_finite: bool = True,
    object_axis=None,
    image_axis=None,
) -> list[dict[str, Any]]:
    """Build the overlay polyline specs (pure geometry, no pyvista).

    Each spec is ``{"kind", "points", "color", "dashed", "line_width"}``. The
    object-plane FOV rectangle is emitted only for a finite object (it has no
    finite size at infinity). ``object_axis``/``image_axis`` let a folded scene
    orient the object FOV by the OBJECT axis and the image circle by the detector
    normal separately; both default to ``image_point - object_point`` (single axis).
    """
    obj_pt = np.asarray(object_point, dtype=float).reshape(3)
    img_pt = np.asarray(image_point, dtype=float).reshape(3)
    default_axis = img_pt - obj_pt
    ou, ov = _basis(default_axis if object_axis is None else np.asarray(object_axis, dtype=float).reshape(3))
    iu, iv = _basis(default_axis if image_axis is None else np.asarray(image_axis, dtype=float).reshape(3))
    specs: list[dict[str, Any]] = []

    # Object plane: FOV rectangle sized sensor / |m| (matches the sensor shape).
    # ``_basis`` returns (vertical, horizontal); a landscape sensor's width must
    # span the horizontal axis, so width->v (horizontal) and height->u (vertical).
    if object_mode_finite and metrics.object_fov_half_width > 1e-9 and metrics.object_fov_half_height > 1e-9:
        specs.append(
            {
                "kind": "object_fov_rect",
                "points": _rect_points(obj_pt, ov, ou, metrics.object_fov_half_width, metrics.object_fov_half_height),
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
                "points": _circle_points(img_pt, iu, iv, metrics.image_circle_radius),
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
                "points": _circle_points(img_pt, iu, iv, metrics.sensor_half_diagonal),
                "color": _REQUIRED_RING,
                "dashed": True,
                "line_width": 2.0,
            }
        )
    return specs


def detector_coverage_label_specs(
    object_point,
    image_point,
    metrics: DetectorCoverageMetrics,
    *,
    object_mode_finite: bool = True,
    object_axis=None,
    image_axis=None,
) -> list[dict[str, Any]]:
    """Direct 3D labels for the coverage overlay (pure geometry, no VTK).

    Each spec is ``{"text", "anchor", "color"}``. Anchors are placed just
    outside each element on its plane, at distinct clock angles, so the labels
    never overlap each other or the drawn geometry. The image-plane labels share
    a plane and so are spread around the circle; the object FOV label sits on the
    far object plane and never competes with them. ``object_axis``/``image_axis``
    default to ``image_point - object_point`` (single axis); a fold passes both.
    """
    obj_pt = np.asarray(object_point, dtype=float).reshape(3)
    img_pt = np.asarray(image_point, dtype=float).reshape(3)
    default_axis = img_pt - obj_pt
    ou, ov = _basis(default_axis if object_axis is None else np.asarray(object_axis, dtype=float).reshape(3))
    iu, iv = _basis(default_axis if image_axis is None else np.asarray(image_axis, dtype=float).reshape(3))

    # Lift the image-plane labels OUTWARD along the detector normal (just past the focus, away from
    # the optics) so they clear the detector. In an edge-on view -- the folded reflect arm in -YZ --
    # the in-plane clock placement otherwise projects every label right onto the detector bar (user
    # flag "text overlaps the detector"); a normal offset moves them off it without hiding geometry.
    _inormal = np.asarray(image_axis if image_axis is not None else default_axis, dtype=float).reshape(3)
    _nn = float(np.linalg.norm(_inormal))
    img_label_center = (
        img_pt + (_inormal / _nn) * (metrics.sensor_half_diagonal * (1.0 + _LABEL_MARGIN) + _LABEL_GAP)
        if _nn > 1e-9 else img_pt
    )

    def place(center, radius, angle_deg, text, color, u, v):
        a = np.radians(float(angle_deg))
        anchor = center + radius * (np.cos(a) * u + np.sin(a) * v)
        return {"text": str(text), "anchor": anchor, "color": tuple(color)}

    labels: list[dict[str, Any]] = []

    # Image plane (concentric): spread labels to widely separated clock angles.
    if metrics.sensor_half_diagonal > 1e-9:
        labels.append(
            place(
                img_label_center,
                metrics.sensor_half_diagonal * (1.0 + _LABEL_MARGIN) + _LABEL_GAP,
                35.0,
                f"Sensor {2 * metrics.sensor_half_width:.1f}×{2 * metrics.sensor_half_height:.1f}",
                _SENSOR_FOOTPRINT,
                iu, iv,
            )
        )
    if metrics.image_circle_radius > 1e-9:
        labels.append(
            place(
                img_label_center,
                metrics.image_circle_radius * (1.0 + _LABEL_MARGIN) + _LABEL_GAP,
                150.0,
                f"Image circle Ø{2 * metrics.image_circle_radius:.1f}"
                + ("" if metrics.covers else " (short)"),
                _IMAGE_CIRCLE_COVERS if metrics.covers else _IMAGE_CIRCLE_SHORT,
                iu, iv,
            )
        )
    if not metrics.covers and metrics.sensor_half_diagonal > 1e-9:
        labels.append(
            place(
                img_label_center,
                metrics.sensor_half_diagonal * (1.0 + _LABEL_MARGIN) + _LABEL_GAP,
                275.0,
                f"Needs Ø{2 * metrics.sensor_half_diagonal:.1f}",
                _REQUIRED_RING,
                iu, iv,
            )
        )

    # Object plane: the FOV rectangle label (finite object only).
    if object_mode_finite and metrics.object_fov_half_width > 1e-9 and metrics.object_fov_half_height > 1e-9:
        fov_diag = float((metrics.object_fov_half_width ** 2 + metrics.object_fov_half_height ** 2) ** 0.5)
        labels.append(
            place(
                obj_pt,
                fov_diag * (1.0 + _LABEL_MARGIN) + _LABEL_GAP,
                90.0,
                f"FOV {2 * metrics.object_fov_half_width:.1f}×{2 * metrics.object_fov_half_height:.1f}",
                _OBJECT_FOV,
                ou, ov,
            )
        )
    return labels


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

    def _pick_fill_actor(self, center, u, v, half_w, half_h, color, row_index) -> bool:
        """A faint, filled, *pickable* square at a plane so the Object/Image row
        can be hover-highlighted and double-clicked for the FOV popup (bugs/0055
        follow-up). The coverage overlay's FOV box / image circle are line actors
        with no fill, and with the detector overlay on the Object/Image clear-
        aperture disk is suppressed to opacity 0 -- so when only "Det" is on the
        Object plane had no pickable geometry to click. A filled quad coincides
        with the drawn FOV edge and gives the whole plane a pick target."""
        pv = self._pv
        if pv is None:
            return False
        try:
            c = np.asarray(center, dtype=float).reshape(3)
            hw = float(half_w)
            hh = float(half_h)
            if not (np.isfinite(hw) and np.isfinite(hh)) or hw <= 1e-9 or hh <= 1e-9:
                return False
            corners = pick_fill_rect_points(c, np.asarray(u, dtype=float), np.asarray(v, dtype=float), hw, hh)
            faces = np.asarray([4, 0, 1, 2, 3], dtype=np.int64)
            mesh = pv.PolyData(corners, faces)
            self.inspector._add_mesh_actor(
                mesh,
                color=tuple(color),
                opacity=0.08,
                flat_shading=True,
                backface_culling=False,
                pick_row_index=int(row_index),
            )
            return True
        except Exception as exc:  # pragma: no cover - defensive
            self.editor.append_debug(f"Detector coverage pick fill skipped: {exc}")
            return False

    def _label_actor(self, anchor, text, color) -> bool:
        try:
            import vtk
        except Exception:
            return False
        try:
            actor = vtk.vtkBillboardTextActor3D()
            actor.SetInput(str(text))
            pos = np.asarray(anchor, dtype=float).reshape(3)
            actor.SetPosition(float(pos[0]), float(pos[1]), float(pos[2]))
            tp = actor.GetTextProperty()
            tp.SetFontSize(13)
            tp.SetColor(0.12, 0.12, 0.14)
            tp.SetBackgroundColor(1.0, 1.0, 1.0)
            tp.SetBackgroundOpacity(0.82)
            tp.SetFrame(True)
            tp.SetFrameColor(float(color[0]), float(color[1]), float(color[2]))
            tp.SetJustificationToCentered()
            tp.SetVerticalJustificationToCentered()
            self.inspector._add_renderer_view_prop(actor)
            return True
        except Exception as exc:  # pragma: no cover - defensive
            self.editor.append_debug(f"Detector coverage label skipped: {exc}")
            return False

    def add_overlays(self, system: Any, scene_bundle: Any = None) -> int:
        if scene_bundle is None:
            return 0
        detectors = [t for t in (getattr(scene_bundle, "targets", []) or []) if bool(getattr(t, "is_detector", False))]
        if not detectors:
            return 0
        rows = getattr(self.editor, "rows", None) or []
        if not rows:
            return 0
        finite = self._is_finite_object()
        try:
            obj_pt = np.asarray(self.editor._surface_reference_world_point(0, system=system), dtype=float).reshape(3)
            # The object's optical axis = direction object -> first surface (shared by both arms).
            first_pt = np.asarray(self.editor._surface_reference_world_point(1, system=system), dtype=float).reshape(3)
        except Exception as exc:
            self.editor.append_debug(f"Detector coverage overlay reference points unavailable: {exc}")
            return 0
        object_axis = first_pt - obj_pt
        ou, ov = _basis(object_axis)
        sys_mag = self._magnification() if finite else None
        sys_image_radius = self._image_circle_radius()
        last_row = len(rows) - 1
        count = 0
        # One detector for single-axis scenes; one PER ARM for a two-arm splitter fold, each at
        # its OWN folded position with its OWN magnification (stored in the target metadata).
        for target in detectors:
            sensor = self._sensor_dimensions(target)
            if sensor is None:
                continue
            meta = getattr(target, "metadata", None) or {}
            mag = meta["two_arm_magnification"] if "two_arm_magnification" in meta else sys_mag
            image_radius = meta.get("two_arm_image_circle_radius") or sys_image_radius
            if image_radius is None:
                continue
            metrics = detector_coverage_metrics(sensor[0], sensor[1], float(image_radius), mag if finite else None)
            img_pt = np.asarray(getattr(target, "center_world"), dtype=float).reshape(3)   # the (folded) detector
            image_axis = np.asarray(getattr(target, "normal_world"), dtype=float).reshape(3)
            iu, iv = _basis(image_axis)

            for spec in detector_coverage_overlay_specs(
                obj_pt, img_pt, metrics, object_mode_finite=finite,
                object_axis=object_axis, image_axis=image_axis,
            ):
                if self._line_actor(spec["points"], spec["color"], spec["line_width"], bool(spec["dashed"])):
                    count += 1

            # bugs/0055 follow-up: faint, filled, *pickable* squares for the Object FOV (object
            # axis) and the Image FOV (this detector's axis) so they hover-highlight + accept the
            # double-click FOV popup.
            if finite and metrics.object_fov_half_width > 1e-9 and metrics.object_fov_half_height > 1e-9:
                if self._pick_fill_actor(obj_pt, ou, ov, metrics.object_fov_half_width, metrics.object_fov_half_height, _OBJECT_FOV, 0):
                    count += 1
            img_half = max(metrics.image_circle_radius, metrics.sensor_half_diagonal)
            if img_half > 1e-9:
                row_index = int(getattr(target, "row_index", last_row) if getattr(target, "row_index", None) is not None else last_row)
                if self._pick_fill_actor(img_pt, iu, iv, img_half, img_half, _IMAGE_CIRCLE_COVERS, row_index):
                    count += 1

            for label in detector_coverage_label_specs(
                obj_pt, img_pt, metrics, object_mode_finite=finite,
                object_axis=object_axis, image_axis=image_axis,
            ):
                if self._label_actor(label["anchor"], label["text"], label["color"]):
                    count += 1

            if not metrics.covers and metrics.image_circle_radius > 0.0:
                self.editor.append_debug(
                    f"Detector coverage ({meta.get('two_arm_selector', 'detector')}): image circle "
                    f"Ø{2 * metrics.image_circle_radius:.4g} mm does not cover the "
                    f"{2 * metrics.sensor_half_width:.4g}×{2 * metrics.sensor_half_height:.4g} mm sensor "
                    f"(needs Ø{2 * metrics.sensor_half_diagonal:.4g})."
                )
        return count
