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
_IMAGE_PLANE = (1.0, 0.0, 0.6)              # magenta -- best-focus image plane / defocus (item 2)

# Direct 3D label placement. Each label is anchored just outside its element on
# the plane, at a distinct clock angle so the (billboarded) labels never overlap
# each other or the geometry (bug 0033 -- the user could not tell the overlay
# elements apart). ``_LABEL_GAP`` is a small absolute world margin so even a
# tiny element still gets a readable standoff.
_LABEL_GAP = 0.6      # mm standoff beyond the radial placement
_LABEL_MARGIN = 0.10  # fraction of the element radius added before the gap
_LABEL_NORMAL_LIFT_FRACTION = 0.2  # off-plane lift for the image labels (edge-on clearance only)
# Per-label stagger ALONG the detector normal so co-planar image labels read as separate
# rows in an edge-on folded view, where the in-plane clock spread collapses onto a line
# (bugs/0241). A fraction of the sensor half-diagonal, floored so tiny sensors still clear.
_LABEL_STACK_STEP_FRACTION = 0.55
_LABEL_STACK_MIN_MM = 5.0

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
    sensor_is_real: bool = True


def detector_coverage_metrics(
    sensor_width: float,
    sensor_height: float,
    image_circle_radius: float,
    magnification: float | None,
    *,
    sensor_is_real: bool = True,
) -> DetectorCoverageMetrics:
    """Does the real image circle cover the rectangular sensor?

    ``image_circle_radius`` is the field's max real image (semi-)height -- the
    actual ray-traced coverage radius. The sensor is covered when that radius
    reaches the sensor *corner* (half-diagonal). The object FOV box is the sensor
    scaled back by the magnification, ``sensor / |m|``.

    ``sensor_is_real`` is True for a registered camera / explicit sensor (the
    coverage-vs-corners question is meaningful) and False when the "sensor" is
    the largest square *inscribed* in the image circle that the overlay
    recommends for a bare lens (bugs/0163) -- its corners sit on the circle, so
    it always covers and the "short"/required-ring framing is suppressed.
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
        sensor_is_real=bool(sensor_is_real),
    )


def recommended_inscribed_sensor_side(image_circle_radius: float) -> float:
    """Side of the largest square that fits *inside* the image circle.

    The user's rule for a bare lens (no camera): the sensor must lie within the
    image circle (bugs/0163). The largest such square has its corners on the
    circle -- half-diagonal == radius -- so side == ``radius * sqrt(2)``.
    """
    radius = max(float(image_circle_radius), 0.0)
    return float(radius * np.sqrt(2.0))


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

    covering = metrics.covers or not metrics.sensor_is_real

    # Image plane: the real image circle (cyan when it covers the sensor; a
    # recommended inscribed sensor always covers, so it stays cyan).
    if metrics.image_circle_radius > 1e-9:
        specs.append(
            {
                "kind": "image_circle",
                "points": _circle_points(img_pt, iu, iv, metrics.image_circle_radius),
                "color": _IMAGE_CIRCLE_COVERS if covering else _IMAGE_CIRCLE_SHORT,
                "dashed": False,
                "line_width": 2.5,
            }
        )

    # No real sensor (bare lens): draw the largest sensor that fits *inside* the
    # image circle -- a useful recommendation in place of the round aperture
    # fabricated into a square (bugs/0163). Its corners sit on the image circle.
    if not metrics.sensor_is_real and metrics.sensor_half_width > 1e-9 and metrics.sensor_half_height > 1e-9:
        specs.append(
            {
                "kind": "recommended_sensor_rect",
                "points": _rect_points(img_pt, iv, iu, metrics.sensor_half_width, metrics.sensor_half_height),
                "color": _SENSOR_FOOTPRINT,
                "dashed": False,
                "line_width": 2.2,
            }
        )

    # When a real sensor does not cover, a dashed ring at the sensor diagonal
    # shows the image circle the design needs to reach the corners.
    if metrics.sensor_is_real and not metrics.covers and metrics.sensor_half_diagonal > 1e-9:
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
    outside each element, at distinct clock angles, so the labels never overlap
    each other or the drawn geometry. The image-plane labels share a plane and so
    are spread around the circle; both the image labels and the object FOV label
    are lifted off their plane along the normal (away from the optics) so an
    edge-on view -- the -YZ the user works in -- does not project them onto the
    plane + ray bundle. ``object_axis``/``image_axis`` default to
    ``image_point - object_point`` (single axis); a fold passes both.
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
    _lift_dir = _inormal / _nn if _nn > 1e-9 else np.zeros(3)
    # Lift just enough to clear the detector edge-on (a small fraction of the sensor), NOT
    # the full half-diagonal -- a full-diagonal lift PLUS the in-plane radius floated the
    # labels ~1.5x the sensor radius away (user: "Sensor / Image circle labels too far").
    _label_lift = metrics.sensor_half_diagonal * _LABEL_NORMAL_LIFT_FRACTION + _LABEL_GAP
    img_label_center = img_pt + _lift_dir * _label_lift

    # bugs/0241: STACK the co-planar image labels along the detector normal. In an EDGE-ON
    # folded view (the -YZ arm) the in-plane clock spread below collapses onto a line, so the
    # "Sensor" and "Image circle" billboards printed on top of each other ("Sensor 2Ima6g.3e..."
    # -- the user flag). The normal is the one axis still visible when the image plane is seen
    # edge-on, so a per-label step along it reads them as separate rows; face-on it is depth-
    # only, leaving the tuned clock placement below unchanged. Sensor stays at stack 0 (its
    # tuned right-edge anchor is pinned by validate_open3d_fov_label_edge_on_clearance).
    _stack_step = max(metrics.sensor_half_diagonal * _LABEL_STACK_STEP_FRACTION, _LABEL_STACK_MIN_MM)

    def place(center, radius, angle_deg, text, color, u, v, stack=0):
        a = np.radians(float(angle_deg))
        anchor = center + stack * _stack_step * _lift_dir + radius * (np.cos(a) * u + np.sin(a) * v)
        return {"text": str(text), "anchor": anchor, "color": tuple(color)}

    labels: list[dict[str, Any]] = []
    covering = metrics.covers or not metrics.sensor_is_real

    # Image plane (concentric): spread labels to widely separated clock angles.
    # A real sensor is named "Sensor WxH"; a bare lens shows the recommended
    # largest sensor that fits inside the image circle, "Max sensor WxH".
    if metrics.sensor_half_width > 1e-9 and metrics.sensor_half_height > 1e-9:
        sensor_label = "Sensor" if metrics.sensor_is_real else "Max sensor"
        labels.append(
            place(
                img_label_center,
                metrics.sensor_half_width * (1.0 + _LABEL_MARGIN) + _LABEL_GAP,  # hug the RIGHT
                       # EDGE (half-width, the +v extent), not the corner -- the half-diagonal sat
                       # it ~5 mm off the edge (user: "should be JUST beside the orange square").
                90.0,  # +v (= -X) = the sensor's RIGHT vertical edge; 0deg was +u (= +Y) = the top,
                       # which is why it kept landing above the sensor by the spot-map box
                f"{sensor_label} {2 * metrics.sensor_half_width:.1f}×{2 * metrics.sensor_half_height:.1f}",
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
                + ("" if covering else " (short)"),
                _IMAGE_CIRCLE_COVERS if covering else _IMAGE_CIRCLE_SHORT,
                iu, iv, stack=1,
            )
        )
    if metrics.sensor_is_real and not metrics.covers and metrics.sensor_half_diagonal > 1e-9:
        labels.append(
            place(
                img_label_center,
                metrics.sensor_half_diagonal * (1.0 + _LABEL_MARGIN) + _LABEL_GAP,
                275.0,
                f"Needs Ø{2 * metrics.sensor_half_diagonal:.1f}",
                _REQUIRED_RING,
                iu, iv, stack=2,
            )
        )

    # Object plane: the FOV rectangle label (finite object only). Lift it OUTWARD
    # along the object-plane normal, AWAY from the optics -- the same trick the
    # image-plane labels use above. The in-plane offset here is along X, which an
    # edge-on view (the -YZ the user works in) projects to nothing, so without the
    # lift the label sat right on the object plane + ray bundle; the normal lift
    # carries it into the empty space behind the object, and the 0deg angle adds a
    # vertical component so it also clears the dotted optical axis.
    if object_mode_finite and metrics.object_fov_half_width > 1e-9 and metrics.object_fov_half_height > 1e-9:
        fov_diag = float((metrics.object_fov_half_width ** 2 + metrics.object_fov_half_height ** 2) ** 0.5)
        fov_reach = fov_diag * (1.0 + _LABEL_MARGIN) + _LABEL_GAP
        _onormal = np.asarray(object_axis if object_axis is not None else default_axis, dtype=float).reshape(3)
        _on = float(np.linalg.norm(_onormal))
        obj_label_center = obj_pt - (_onormal / _on) * fov_reach if _on > 1e-9 else obj_pt
        labels.append(
            place(
                obj_label_center,
                fov_reach,
                0.0,
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

    def _target_has_real_sensor(self, target) -> bool:
        from KrakenOS.UI.scene_geometry import scene_target_has_explicit_sensor

        return scene_target_has_explicit_sensor(target)

    def _image_circle_radius(self) -> float | None:
        try:
            summary = self.editor._field_metrics_summary()
        except Exception:
            return None
        try:
            # bugs/0168: use the object-mode-aware image radius (EFL*tan(field) for an
            # infinity object) so the "image circle" matches where the rays actually
            # land, not the back-focal-distance underestimate ``max_real_image_height``.
            radius = float(summary.get("field_image_radius", summary.get("max_real_image_height")))
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

    def _arrow_cone(self, tip, outward, color) -> bool:
        # A cone arrowhead with its TIP at ``tip`` pointing along ``outward`` (the line direction
        # away from the other end), so a dimension line reads with proper CAD arrowheads.
        pv = self._pv
        if pv is None:
            return False
        try:
            tip = np.asarray(tip, dtype=float).reshape(3)
            outward = np.asarray(outward, dtype=float).reshape(3)
            length = float(np.linalg.norm(outward))
            if length <= 1e-9 or not np.all(np.isfinite(tip)):
                return False
            d = outward / length
            head = float(min(max(length * 0.14, 1.5), 6.0))
            center = tip - d * (head * 0.5)
            cone = pv.Cone(
                center=tuple(float(v) for v in center),
                direction=tuple(float(v) for v in d),
                height=head,
                radius=head * 0.4,
                resolution=20,
            )
            self.inspector._add_mesh_actor(cone, color=tuple(color), opacity=1.0)
            return True
        except Exception as exc:  # pragma: no cover - defensive
            self.editor.append_debug(f"defocus arrow skipped: {exc}")
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
            meta = getattr(target, "metadata", None) or {}
            mag = meta["two_arm_magnification"] if "two_arm_magnification" in meta else sys_mag
            image_radius = meta.get("two_arm_image_circle_radius") or sys_image_radius
            if image_radius is None:
                continue
            if self._target_has_real_sensor(target):
                sensor = self._sensor_dimensions(target)
                if sensor is None:
                    continue
                metrics = detector_coverage_metrics(
                    sensor[0], sensor[1], float(image_radius), mag if finite else None,
                    sensor_is_real=True,
                )
            else:
                # Bare lens (no camera): recommend the largest sensor that fits
                # inside the image circle instead of fabricating a square from
                # the round aperture (bugs/0163).
                rec_side = recommended_inscribed_sensor_side(float(image_radius))
                if rec_side <= 1e-9:
                    continue
                metrics = detector_coverage_metrics(
                    rec_side, rec_side, float(image_radius), mag if finite else None,
                    sensor_is_real=False,
                )
            # bugs/0188: the table-row detector target is already folded onto the
            # reflected +X branch at the bundle source (LayoutSceneBundleDisplayMixin.
            # _fold_promoted_mirror_table_row_targets), so center_world/normal_world
            # here read the folded sensor pose -- shared with the 3-D footprint actor
            # and the 2-D footprint projection, which draw from the same target.
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

            if metrics.sensor_is_real and not metrics.covers and metrics.image_circle_radius > 0.0:
                self.editor.append_debug(
                    f"Detector coverage ({meta.get('two_arm_selector', 'detector')}): image circle "
                    f"Ø{2 * metrics.image_circle_radius:.4g} mm does not cover the "
                    f"{2 * metrics.sensor_half_width:.4g}×{2 * metrics.sensor_half_height:.4g} mm sensor "
                    f"(needs Ø{2 * metrics.sensor_half_diagonal:.4g})."
                )

        # IMAGE PLANE (best focus) marker + DEFOCUS dimension (item 2): the detector above is the
        # sensor/analysis surface; the image plane is where the optics focus. The gap between them
        # is the simulated defocus. Single-axis only -- two-arm fold detectors already sit on their
        # per-arm convergence.
        try:
            image_plane_z = self.editor._paraxial_image_plane_z()
        except Exception:
            image_plane_z = None
        axis_dets = [
            t for t in detectors
            if abs(float(np.asarray(t.center_world, dtype=float)[0])) < 1e-3
            and abs(float(np.asarray(t.center_world, dtype=float)[1])) < 1e-3
        ]
        if image_plane_z is not None and len(detectors) == 1 and axis_dets:
            det_z = float(np.asarray(axis_dets[0].center_world, dtype=float)[2])
            radius = float(sys_image_radius) if (sys_image_radius and sys_image_radius > 1e-6) else 6.0
            mu, mv = _basis(np.array([0.0, 0.0, 1.0], dtype=float))
            ip = np.array([0.0, 0.0, float(image_plane_z)], dtype=float)
            if self._line_actor(_circle_points(ip, mu, mv, radius), _IMAGE_PLANE, 2.0, False):
                count += 1
            gap = det_z - float(image_plane_z)
            stand = radius * (1.0 + _LABEL_MARGIN) + _LABEL_GAP
            if abs(gap) > 0.5:
                seg = np.array([[0.0, stand, det_z], [0.0, stand, float(image_plane_z)]], dtype=float)
                # solid dimension line + CAD arrowheads (was a bare dashed line)
                if self._line_actor(seg, _IMAGE_PLANE, 2.5, False):
                    count += 1
                self._arrow_cone(seg[0], seg[0] - seg[1], _IMAGE_PLANE)
                self._arrow_cone(seg[1], seg[1] - seg[0], _IMAGE_PLANE)
                # Sit the label just OFF the dimension line (the line is already at the
                # standoff y=stand, clear of the body); radius*0.7 pushed it ~17 mm away
                # from a ~25 mm-radius arrow, so keep it a small fixed nudge instead.
                label_pos = 0.5 * (seg[0] + seg[1]) + np.array([0.0, max(radius * 0.06, 1.2) + _LABEL_GAP, 0.0], dtype=float)
                if self._label_actor(label_pos, f"defocus = {gap:+.4g} mm", _IMAGE_PLANE):
                    count += 1
            elif self._label_actor(ip + np.array([0.0, stand, 0.0]), "image plane (in focus)", _IMAGE_PLANE):
                count += 1
        return count
