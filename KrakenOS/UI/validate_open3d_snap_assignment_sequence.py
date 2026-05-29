"""Validate STEP snap plus direct face assignment tracing sequence."""

from __future__ import annotations

from collections import Counter
import numpy as np

from KrakenOS.UI.layout_editor import (
    Kraken3DInspector,
    KrakenLayoutEditor,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    optical_solid_face_world_records,
)
from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP


def _event_face_id(event: object) -> str:
    metadata = getattr(event, "metadata", {}) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return str(
        getattr(event, "mesh_face_id", "")
        or getattr(event, "face_id", "")
        or metadata.get("mesh_face_id", "")
        or metadata.get("face_id", "")
        or ""
    ).strip()


def _surface_events(path: object) -> list[object]:
    return [event for event in list(getattr(path, "events", []) or []) if str(getattr(event, "event_kind", "") or "") == "surface"]


def _central_path(scene_bundle) -> object:
    paths = list(getattr(scene_bundle, "ray_paths", []) or [])
    if not paths:
        raise AssertionError("No ray paths were traced.")

    def _score(path: object) -> tuple[float, int]:
        try:
            points = np.asarray(getattr(path, "points_world", ()), dtype=float)
            if points.ndim == 2 and points.shape[0] >= 1 and points.shape[1] >= 2:
                radius = float(np.hypot(points[0, 0], points[0, 1]))
            else:
                radius = float("inf")
        except Exception:
            radius = float("inf")
        try:
            ray_index = int(getattr(path, "ray_index", 0) or 0)
        except Exception:
            ray_index = 0
        return radius, ray_index

    return min(paths, key=_score)


class _FakeRenderer:
    def ComputeVisiblePropBounds(self):
        return (-15.0, 15.0, -15.0, 45.0, -10.0, 70.0)


def _axis_records(scene_bundle) -> list[dict[str, object]]:
    inspector = object.__new__(Kraken3DInspector)
    inspector._renderer = _FakeRenderer()
    return Kraken3DInspector._optical_axis_records_for_3d(inspector, scene_bundle)


def _assert_single_exit_axis(scene_bundle) -> None:
    axis_records = _axis_records(scene_bundle)
    traced = [record for record in axis_records if str(record.get("axis_kind", "") or "") == "traced_chief_ray_segment"]
    if len(traced) != 1:
        raise AssertionError(f"Expected exactly one traced exit optical axis, got {axis_records!r}")
    traced_axis = traced[0]
    if str(traced_axis.get("axis_role", "") or "") != "post_surface":
        raise AssertionError(f"Traced axis should describe only the post-surface exit segment: {traced_axis!r}")
    path = _central_path(scene_bundle)
    points = np.asarray(getattr(path, "points_world", ()), dtype=float)
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
        raise AssertionError("Central path has no usable terminal segment.")
    terminal_direction = points[-1, :3] - points[-2, :3]
    terminal_norm = float(np.linalg.norm(terminal_direction))
    if terminal_norm <= 1e-12:
        raise AssertionError("Central path terminal segment has zero length.")
    terminal_direction /= terminal_norm
    axis_direction = np.asarray(traced_axis.get("segment_direction", ()), dtype=float).reshape(-1)[:3]
    if axis_direction.size < 3:
        raise AssertionError(f"Traced axis has no direction: {traced_axis!r}")
    axis_norm = float(np.linalg.norm(axis_direction))
    if axis_norm <= 1e-12:
        raise AssertionError(f"Traced axis has zero direction: {traced_axis!r}")
    axis_direction /= axis_norm
    if float(np.dot(axis_direction, terminal_direction)) < 0.999:
        raise AssertionError(
            f"Traced exit axis does not follow the central ray exit segment: axis={axis_direction}, ray={terminal_direction}"
        )
    events = _surface_events(path)
    if not events:
        raise AssertionError("Central path has no surface events.")
    last_face = _event_face_id(events[-1])
    if str(traced_axis.get("from_mesh_face_id", "") or "") != last_face:
        raise AssertionError(f"Exit axis starts from the wrong face: axis={traced_axis!r}, last_face={last_face}")


def _trace(app: KrakenLayoutEditor):
    return app._build_preview_system_rays_bundle(sampling_mode="world_envelope", update_state=False)


def _default_overlay_face(face_id: str) -> tuple[np.ndarray, np.ndarray]:
    app = KrakenLayoutEditor(headless=True)
    try:
        app.imported_optical_step_path = PRISM_42779_STEP
        app.select_step_component("optical")
        promoted = app.promote_imported_step_to_optical_solid_row(
            "optical",
            insert_at=1,
            open_face_editor=False,
            clear_overlay=False,
            refresh_open_3d=False,
        )
        if promoted is None:
            raise AssertionError("Could not create reference promoted STEP metadata.")
        row_index = int(promoted["row_index"])
        row = app.rows[row_index]
        faces = optical_solid_face_world_records(row, app._stl_row_z_station(row_index), assigned_only=False)
        face = next(
            (
                item
                for item in faces
                if str(item.get("face_id", "")) == face_id
                or str(item.get("face_id", "")).endswith("/" + face_id)
            ),
            None,
        )
        if face is None:
            raise AssertionError(f"Reference face {face_id} was not found.")
        center = np.asarray(face.get("centroid_world"), dtype=float).reshape(3)
        normal = np.asarray(face.get("normal_world"), dtype=float).reshape(3)
        return center, normal
    finally:
        app.destroy()


def _first_two_hit_faces(scene_bundle) -> tuple[str, str, tuple[str, ...], tuple[str, ...]]:
    path = _central_path(scene_bundle)
    events = _surface_events(path)
    faces = tuple(_event_face_id(event) for event in events if _event_face_id(event))
    interactions = tuple(str(getattr(event, "event_type", "") or getattr(event, "interaction", "") or "") for event in events)
    if len(faces) < 2:
        raise AssertionError(f"Expected at least two optical-solid hits, got faces={faces}, interactions={interactions}")
    return faces[0], faces[1], faces, interactions


def _validate_snap_face_sequence(snap_face_id: str) -> None:
    feature_center, feature_normal = _default_overlay_face(snap_face_id)
    app = KrakenLayoutEditor(headless=True)
    try:
        app.imported_optical_step_path = PRISM_42779_STEP
        app.select_step_component("optical")
        axis_frame = {
            "target_point": (0.0, 0.0, float(feature_center[2])),
            "direction": (0.0, 0.0, 1.0),
            "axis_label": "global +Z optical axis",
            "ray_index": -1,
            "branch_path": "",
        }
        snap = app.snap_step_feature_normal_to_optical_axis(
            "optical",
            feature_center,
            feature_normal,
            axis_frame=axis_frame,
        )
        if snap is None:
            raise AssertionError(f"Snap returned no result for {snap_face_id}.")
        target_point = np.asarray(snap["target_point"], dtype=float).reshape(3)
        target_normal = np.asarray(snap["target_direction"], dtype=float).reshape(3)
        promoted = app.promote_imported_step_to_optical_solid_row(
            "optical",
            insert_at=1,
            open_face_editor=False,
            clear_overlay=True,
            refresh_open_3d=False,
        )
        if promoted is None:
            raise AssertionError("STEP promotion after snap returned no row.")
        row_index = int(promoted["row_index"])
        first = app.assign_optical_solid_face_function_at_world_point(
            row_index,
            target_point,
            "Uncoated",
            normal_world=target_normal,
            direct_context=True,
        )
        if first.get("function") != OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT:
            raise AssertionError(f"First snapped face did not save as Uncoated: {first!r}")
        _system, _rays, scene_bundle = _trace(app)
        entrance_face, second_face, before_faces, before_interactions = _first_two_hit_faces(scene_bundle)
        if entrance_face != str(first.get("face_id", "") or ""):
            raise AssertionError(
                f"Snapped entrance assignment did not match first traced face for {snap_face_id}: "
                f"assigned={first.get('face_id')}, traced={before_faces}, interactions={before_interactions}"
            )
        second = app.assign_optical_solid_face_function(
            row_index,
            second_face,
            "Full Reflecting",
            direct_context=True,
        )
        if second.get("function") != "Mirror":
            raise AssertionError(f"Second face did not save as Mirror: {second!r}")
        _system, _rays, scene_bundle = _trace(app)
        _entrance_after, mirror_face, after_faces, after_interactions = _first_two_hit_faces(scene_bundle)
        if mirror_face != second_face:
            raise AssertionError(
                f"Second traced face changed after mirror assignment for {snap_face_id}: "
                f"before={second_face}, after={after_faces}, interactions={after_interactions}"
            )
        if len(after_interactions) < 2 or after_interactions[1] not in {"reflect", "reflection", "reflect_mirror"}:
            raise AssertionError(
                f"Assigned second face did not reflect for {snap_face_id}: "
                f"faces={after_faces}, interactions={after_interactions}, counts={Counter(after_faces)!r}"
            )
        _assert_single_exit_axis(scene_bundle)
    finally:
        app.destroy()


def main() -> int:
    if not PRISM_42779_STEP.exists():
        raise RuntimeError(f"Expected STEP fixture: {PRISM_42779_STEP}")
    for face_id in ("F005", "F006"):
        _validate_snap_face_sequence(face_id)
    print("Open 3D snap assignment sequence validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
