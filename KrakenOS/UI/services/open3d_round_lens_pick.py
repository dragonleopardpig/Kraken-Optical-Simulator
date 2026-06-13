"""Round lens-specific STEP face picking for the embedded Open 3D view."""

from __future__ import annotations

from typing import Any

import numpy as np

from KrakenOS.UI.services.open3d_face_index_edges import (
    face_indices_for_record,
    face_pick_from_display_cell,
    triangles_for_face_indices,
)
from KrakenOS.UI.services.open3d_face_pick import FaceRayPick
from KrakenOS.UI.services.open3d_timing import open3d_trace_span


def _metadata_round_lens_cap_pick(inspector: Any, label: str, display_xy):
    """Resolve a round optical STEP click to an analytic cap face record.

    Transparent vendor achromats let the user see optical caps through the
    body. VTK still picks the nearest triangle, which is often a side wall or
    rim patch. Prefer the grouped analytic cap records when the display ray
    intersects their projected clear aperture.
    """
    if not inspector._step_label_is_round_lens_like(label):
        return None
    ray = inspector._display_pick_ray(display_xy)
    if ray is None:
        return None
    ray_origin, ray_direction = ray
    try:
        metadata = inspector.editor._step_overlay_face_metadata(label)
        faces = [face for face in list(metadata.get("faces", []) or []) if isinstance(face, dict)]
        display_mesh = inspector.editor._transformed_imported_step_mesh_for_label(label)
    except Exception:
        return None

    best: tuple[float, float, FaceRayPick] | None = None
    for face in faces:
        if not str(face.get("assignment_source", "") or "").startswith("step_analytic_axisymmetric_group"):
            continue
        try:
            center = np.asarray(face.get("centroid_world", face.get("centroid", ())), dtype=float).reshape(-1)[:3]
            normal = np.asarray(face.get("normal_world", face.get("normal", ())), dtype=float).reshape(-1)[:3]
        except Exception:
            continue
        if center.size < 3 or normal.size < 3:
            continue
        if not (np.all(np.isfinite(center[:3])) and np.all(np.isfinite(normal[:3]))):
            continue
        normal_norm = float(np.linalg.norm(normal[:3]))
        if not np.isfinite(normal_norm) or normal_norm <= 1.0e-12:
            continue
        normal = normal[:3] / normal_norm
        denom = float(np.dot(ray_direction[:3], normal[:3]))
        if not np.isfinite(denom) or abs(denom) <= 1.0e-10:
            continue
        distance = float(np.dot(center[:3] - ray_origin[:3], normal[:3]) / denom)
        if not np.isfinite(distance) or distance < -1.0e-5:
            continue
        point = ray_origin[:3] + max(distance, 0.0) * ray_direction[:3]
        face_indices = face_indices_for_record(display_mesh, face)
        selected_triangles = triangles_for_face_indices(display_mesh, face_indices)
        if selected_triangles.size == 0:
            continue
        points = np.asarray(selected_triangles, dtype=float).reshape((-1, 3))
        radial_vectors = points[:, :3] - center.reshape(1, 3)
        radial_vectors = radial_vectors - np.outer(radial_vectors @ normal[:3], normal[:3])
        radial = np.linalg.norm(radial_vectors, axis=1)
        finite_radial = radial[np.isfinite(radial)]
        if finite_radial.size < 8:
            continue
        radius = float(np.percentile(finite_radial, 98))
        if not np.isfinite(radius) or radius <= 1.0e-9:
            continue
        clicked = point[:3] - center[:3]
        clicked = clicked - normal[:3] * float(np.dot(clicked, normal[:3]))
        radial_distance = float(np.linalg.norm(clicked))
        tolerance = max(radius * 0.08, 0.08)
        if radial_distance > radius + tolerance:
            continue
        pick = FaceRayPick(
            face=dict(face),
            point_world=tuple(float(value) for value in point[:3]),
            normal_world=tuple(float(value) for value in normal[:3]),
            distance=max(distance, 0.0),
            internal=False,
        )
        score = (max(distance, 0.0), radial_distance / max(radius, 1.0e-9), pick)
        if best is None or score[:2] < best[:2]:
            best = score
    if best is None:
        return None
    pick = best[2]
    return {
        "feature": inspector._feature_from_face_ray_pick(
            pick,
            inspector._hover_overlay_for_step_face(label, pick.face),
        ),
        "surface_center": inspector._surface_center_from_face_ray_pick(pick),
        "face_id": str(pick.face.get("face_id", "") or "").strip(),
        "through_pick": pick,
    }


def round_lens_feature_for_display_xy(inspector: Any, label: str, display_xy):
    """Pick the exterior cap of a round lens-like STEP body.

    Vendor lens STEP files often contain cemented interfaces and dense
    tessellation patches. Those patches are useful for display, but they should
    not become the selected face when the user is aligning the visible lens end
    face to an optical axis.
    """
    label = str(label or "").strip().lower()
    if not label or not inspector._step_label_is_round_lens_like(label):
        return None
    with open3d_trace_span("round_lens_metadata_cap_pick", label=label):
        metadata_pick = _metadata_round_lens_cap_pick(inspector, label, display_xy)
    if metadata_pick is not None:
        return metadata_pick
    ray = inspector._display_pick_ray(display_xy)
    if ray is None:
        return None
    ray_origin, ray_direction = ray
    best: tuple[float, tuple[np.ndarray, object | None, np.ndarray], np.ndarray, str] | None = None
    for actor_key in list(inspector._step_actor_map.get(label, []) or []):
        if actor_key in inspector._actor_step_rotate_map or actor_key in inspector._actor_step_rotate_visual_keys:
            continue
        actor = inspector._actor_by_key.get(str(actor_key))
        if actor is None or not bool(getattr(actor, "_kraken_round_lens_like_step_body", False)):
            continue
        try:
            if not bool(actor.GetVisibility()):
                continue
        except Exception:
            pass
        try:
            prop = actor.GetProperty()
            if prop is not None and float(prop.GetOpacity()) <= 0.01:
                continue
        except Exception:
            pass
        try:
            data = actor.GetMapper().GetInput()
        except Exception:
            data = None
        axis_info = inspector._mesh_round_lens_axis(data)
        if axis_info is None:
            continue
        object_center, axis, points = axis_info
        axis = inspector._normalized_vector(axis)
        if axis is None:
            continue
        point_array = np.asarray(points, dtype=float).reshape((-1, 3))
        if point_array.shape[0] < 8 or not np.all(np.isfinite(point_array[:, :3])):
            continue
        projections = (point_array[:, :3] - object_center.reshape(1, 3)) @ axis[:3]
        if projections.size < 8 or not np.all(np.isfinite(projections)):
            continue
        axial_min = float(np.min(projections))
        axial_max = float(np.max(projections))
        thickness = max(axial_max - axial_min, 1e-9)
        radial_vectors = point_array[:, :3] - (
            object_center.reshape(1, 3) + np.outer(projections, axis[:3])
        )
        finite_radial = np.linalg.norm(radial_vectors, axis=1)
        finite_radial = finite_radial[np.isfinite(finite_radial)]
        if finite_radial.size < 8:
            continue
        radius = float(np.percentile(finite_radial, 97))
        if not np.isfinite(radius) or radius <= 1e-9:
            continue
        for face_id, axial, normal in (
            ("outer +axis face", axial_max, axis),
            ("outer -axis face", axial_min, -axis),
        ):
            cap_center = object_center + axis[:3] * float(axial)
            denom = float(np.dot(ray_direction[:3], normal[:3]))
            if not np.isfinite(denom) or abs(denom) <= 1e-10:
                continue
            distance = float(np.dot(cap_center[:3] - ray_origin[:3], normal[:3]) / denom)
            if not np.isfinite(distance) or distance < -1e-6:
                continue
            point = ray_origin[:3] + max(distance, 0.0) * ray_direction[:3]
            radial_offset = point[:3] - cap_center[:3]
            radial_distance = float(
                np.linalg.norm(radial_offset - normal[:3] * float(np.dot(radial_offset, normal[:3])))
            )
            tolerance = max(radius * 0.12, thickness * 0.03, 0.05)
            if radial_distance > radius + tolerance:
                continue
            outline = inspector._planar_outline_from_points(point_array[:, :3], normal_world=normal)
            feature = (
                np.asarray(cap_center[:3], dtype=float),
                outline,
                np.asarray(normal[:3], dtype=float),
            )
            candidate = (max(distance, 0.0), feature, np.asarray(cap_center[:3], dtype=float), face_id)
            if best is None or candidate[0] < best[0]:
                best = candidate
    if best is None:
        return None
    _distance, feature, surface_center, face_id = best
    return {
        "feature": feature,
        "surface_center": surface_center,
        "face_id": face_id,
        "through_pick": None,
    }


def step_feature_pick_for_display_xy(
    inspector: Any,
    label: str,
    display_xy,
    *,
    actor=None,
    actor_key: str | None = None,
    cell_id: int = -1,
) -> dict[str, object] | None:
    """Return a display-safe imported STEP feature selection."""
    label = str(label or "").strip().lower()
    if not label:
        return None
    if inspector._step_label_is_round_lens_like(label):
        round_lens_pick = round_lens_feature_for_display_xy(inspector, label, display_xy)
        if round_lens_pick is not None:
            return round_lens_pick
    try:
        metadata = inspector.editor._step_overlay_face_metadata(label)
        faces = [face for face in list(metadata.get("faces", []) or []) if isinstance(face, dict)]
        # A beam splitter's 45deg coating is an INTERNAL face. The VTK cell picker
        # (below) returns the nearest EXTERNAL shell face for a translucent solid
        # and varies pixel-to-pixel, so the user could not reliably (re-)select the
        # diagonal on hover/right-click ("every time I select the 45 degree surface,
        # right click will change to another surface"). For a clean solid (few
        # faces -- a cube/prism, not a tessellated lens) prefer the DETERMINISTIC
        # ray pick when it lands on an internal face; otherwise fall through to the
        # cell pick (keeps tessellated-lens behavior + costs nothing for solids with
        # no internal faces, where the ray pick returns an external hit).
        if 0 < len(faces) < 40:
            internal_ray = inspector._step_face_ray_pick_for_display_xy(label, display_xy)
            if internal_ray is not None and bool(getattr(internal_ray, "internal", False)):
                return {
                    "feature": inspector._feature_from_face_ray_pick(
                        internal_ray,
                        inspector._hover_overlay_for_step_face(label, internal_ray.face),
                    ),
                    "surface_center": inspector._surface_center_from_face_ray_pick(internal_ray),
                    "face_id": str(internal_ray.face.get("face_id", "") or "").strip(),
                    "through_pick": internal_ray,
                }
        pick_point = None
        try:
            pick_point = np.asarray(inspector._picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
        except Exception:
            pick_point = None
        cell_pick = face_pick_from_display_cell(
            inspector.editor,
            label,
            faces,
            int(cell_id),
            pick_point=pick_point,
        )
        if cell_pick is not None:
            return {
                "feature": inspector._feature_from_face_ray_pick(
                    cell_pick,
                    inspector._hover_overlay_for_step_face(label, cell_pick.face),
                ),
                "surface_center": inspector._surface_center_from_face_ray_pick(cell_pick),
                "face_id": str(cell_pick.face.get("face_id", "") or "").strip(),
                "through_pick": cell_pick,
            }
    except Exception:
        pass
    through_pick = inspector._coarse_step_face_ray_pick_for_display_xy(label, display_xy)
    if through_pick is not None:
        return {
            "feature": inspector._feature_from_face_ray_pick(
                through_pick,
                inspector._hover_overlay_for_step_face(label, through_pick.face),
            ),
            "surface_center": inspector._surface_center_from_face_ray_pick(through_pick),
            "face_id": str(through_pick.face.get("face_id", "") or "").strip(),
            "through_pick": through_pick,
        }
    feature = inspector._picked_feature_info_cached(
        actor,
        inspector._picker,
        actor_key=actor_key,
        cell_id=int(cell_id),
    )
    if feature is None:
        return None
    return {
        "feature": feature,
        "surface_center": None,
        "face_id": "",
        "through_pick": None,
    }
