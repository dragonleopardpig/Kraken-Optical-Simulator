"""Validate Open 3D direct CAD/STL face-function assignment."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np

from KrakenOS.UI import layout_editor as le
from KrakenOS.UI.layout_editor import (
    Kraken3DInspector,
    KrakenLayoutEditor,
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    OPTICAL_SOLID_FACE_PORT_INTERACTION,
    SurfaceRow,
    _optical_solid_face_metadata_extent,
    _optical_solid_face_records_share_plane,
    cluster_optical_solid_planar_faces,
    optical_solid_face_world_records,
)
from KrakenOS.UI.optical_solid_metadata import normalize_optical_solid_face_metadata


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRISM_42779_STEP = PROJECT_ROOT / "attachment" / "prisms" / "42779" / "step_42779.step"
VALIDATION_CACHE_DIR = Path("/tmp/kraken-open3d-face-context-cache")


def _write_mixed_winding_plane_stl(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """solid mixed_winding_plane
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 1 0 0
    vertex 0 1 0
  endloop
endfacet
facet normal 0 0 -1
  outer loop
    vertex 1 1 0
    vertex 0 1 0
    vertex 1 0 0
  endloop
endfacet
endsolid mixed_winding_plane
""",
        encoding="utf-8",
    )


def _validate_mixed_winding_faces_share_physics_assignment() -> None:
    mesh_path = VALIDATION_CACHE_DIR / "mixed_winding_plane.stl"
    _write_mixed_winding_plane_stl(mesh_path)
    candidates = cluster_optical_solid_planar_faces(mesh_path)
    if len(candidates) != 1:
        raise AssertionError(
            "Mixed-winding coplanar STL triangles should form one physical face candidate, "
            f"got {len(candidates)} candidates."
        )
    if int(candidates[0].triangle_count) != 2:
        raise AssertionError(f"Expected both triangles in the same physical face, got {candidates[0].triangle_count}.")


def _first_world_face(app: KrakenLayoutEditor, row_index: int) -> dict[str, object]:
    row = app.rows[int(row_index)]
    _row, _path, metadata = app._optical_solid_face_metadata_for_row(int(row_index))
    temp_row = SurfaceRow(**asdict(row))
    temp_row.advanced = dict(temp_row.advanced or {})
    temp_row.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata
    faces = optical_solid_face_world_records(temp_row, app._stl_row_z_station(int(row_index)), assigned_only=False)
    if not faces:
        raise AssertionError("Expected promoted optical solid to expose assignable faces.")
    return dict(faces[0])


def _first_world_face_with_triangle(faces: list[dict[str, object]]) -> dict[str, object]:
    for face in list(faces or []):
        if not isinstance(face, dict):
            continue
        if list(face.get("triangle_indices", []) or []):
            return dict(face)
    raise AssertionError("Expected optical solid metadata to expose triangle-backed face IDs.")


def _validate_transient_step_face_id_carry_through(app: KrakenLayoutEditor) -> None:
    plan = app._step_overlay_optical_solid_row_plan(
        "optical",
        insert_at=1,
        use_current_selection=False,
        quiet=True,
    )
    if plan is None:
        raise AssertionError("Expected transient optical STEP row plan for face-ID validation.")
    row = plan.get("row")
    if not isinstance(row, SurfaceRow):
        raise AssertionError("Transient optical STEP plan did not return a SurfaceRow.")
    row_index = int(plan.get("row_index", 1))
    z_station = float(sum(float(getattr(existing_row, "thickness", 0.0) or 0.0) for existing_row in app.rows[:row_index]))
    faces = optical_solid_face_world_records(row, z_station, assigned_only=False)
    picked = _first_world_face_with_triangle(faces)
    face_id = str(picked.get("face_id", "") or "").strip()
    triangle_index = int(list(picked.get("triangle_indices", []) or [])[0])
    matched = app.optical_solid_step_overlay_face_record_at_world_point(
        "optical",
        np.asarray(picked.get("centroid_world"), dtype=float),
        normal_world=np.asarray(picked.get("normal_world"), dtype=float),
        cell_id=triangle_index,
    )
    if not isinstance(matched, dict) or str(matched.get("face_id", "") or "").strip() != face_id:
        raise AssertionError(
            "Transient STEP face assignment must carry the clicked mesh-cell face ID through promotion; "
            f"expected={face_id}, matched={matched!r}"
        )


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


def _surface_face_sequence(path: object) -> tuple[str, ...]:
    return tuple(
        face_id
        for event in list(getattr(path, "events", []) or [])
        if str(getattr(event, "event_kind", "") or "") == "surface"
        for face_id in (_event_face_id(event),)
        if face_id
    )


def _validate_promoted_reflecting_prism_image_plane_is_not_intrusive() -> None:
    """Reproduce the Open 3D penta-prism workflow that exposed halfway stops."""

    app = KrakenLayoutEditor(headless=True)
    try:
        app.imported_optical_step_path = PRISM_42779_STEP
        app.optical_step_rotation_x_deg = 0.0
        app.optical_step_rotation_y_deg = 90.0
        app.optical_step_rotation_z_deg = 180.0
        app.optical_step_placement_offset_xyz = (0.0, 5.338434219360337, 35.338052809592156)
        app.select_step_component("optical")

        promoted = app.promote_imported_step_to_optical_solid_row(
            "optical",
            insert_at=1,
            open_face_editor=False,
            clear_overlay=True,
            refresh_open_3d=False,
        )
        if promoted is None:
            raise AssertionError("Exact promoted reflecting-prism repro returned no promoted row.")
        row_index = int(promoted["row_index"])
        row = app.rows[row_index]
        if abs(float(row.axis_move)) > 1e-12:
            raise AssertionError("Exact promoted reflecting-prism repro must use AxisMove=0.")
        for face_id in ("F004", "F003"):
            assigned = app.assign_optical_solid_face_function(
                row_index,
                face_id,
                "Full Reflecting",
                direct_context=True,
            )
            if str(assigned.get("function", "") or "") != "Mirror":
                raise AssertionError(f"Reflecting-prism repro did not assign {face_id} as Mirror: {assigned!r}")

        system, _rays, scene_bundle = app._build_preview_system_rays_bundle(
            sampling_mode="world_envelope",
            update_state=False,
        )
        image_index = row_index + 1
        if image_index < len(app.rows) and app.rows[image_index].surface == "Image":
            image_transform = np.asarray(system.TRANS_2A[image_index], dtype=float).reshape(4, 4)
            expected_center = np.asarray((0.0, 0.0, app._stl_row_z_station(image_index)), dtype=float)
            actual_center = image_transform[:3, 3]
            if not np.allclose(actual_center, expected_center, atol=1e-6):
                raise AssertionError(
                    "Exact promoted reflecting-prism repro moved the Image plane into the scene object: "
                    f"actual={actual_center.tolist()}, expected={expected_center.tolist()}"
                )

        ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
        if len(ray_paths) < 10:
            raise AssertionError(f"Reflecting-prism repro traced too few rays: {len(ray_paths)}")
        sequences = [_surface_face_sequence(path) for path in ray_paths]
        incomplete = [sequence for sequence in sequences if "F006" not in sequence]
        if incomplete:
            raise AssertionError(
                "Exact promoted reflecting-prism repro left rays terminated before the exit face; "
                f"sequence_counts={Counter(sequences)!r}"
            )
    finally:
        app.destroy()


def main() -> int:
    if not PRISM_42779_STEP.exists():
        raise RuntimeError(f"Expected STEP fixture: {PRISM_42779_STEP}")

    le.CAD_CACHE_DIR = VALIDATION_CACHE_DIR / "cad"
    le.CAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _validate_mixed_winding_faces_share_physics_assignment()

    app = KrakenLayoutEditor(headless=True)
    try:
        app.imported_optical_step_path = PRISM_42779_STEP
        app.optical_step_rotation_x_deg = 90.0
        app.optical_step_rotation_z_deg = 90.0
        app.select_step_component("optical")
        _validate_transient_step_face_id_carry_through(app)

        promoted = app.promote_imported_step_to_optical_solid_row(
            "optical",
            insert_at=1,
            open_face_editor=False,
            clear_overlay=True,
        )
        if promoted is None:
            raise AssertionError("STEP promotion returned no result.")
        row_index = int(promoted["row_index"])
        row = app.rows[row_index]
        if abs(float(row.axis_move)) > 1e-12:
            raise AssertionError(
                "Promoted optical STEP solids should be scene objects with AxisMove=0; "
                "otherwise the downstream Image/detector row can be pulled into the prism."
            )
        if app.imported_optical_step_path is not None:
            raise AssertionError("Promotion with clear_overlay=True left the display-only optical STEP overlay active.")
        if getattr(app, "_selected_step_label", None) is not None:
            raise AssertionError("Promotion with clear_overlay=True left a stale selected STEP label.")
        if app._transformed_imported_optical_step_mesh() is not None:
            raise AssertionError("Promotion with clear_overlay=True left display-only optical STEP geometry visible.")

        picked = _first_world_face(app, row_index)
        point = np.asarray(picked.get("centroid_world"), dtype=float)
        normal = np.asarray(picked.get("normal_world"), dtype=float)
        triangle_indices = list(picked.get("triangle_indices", []) or [])
        if triangle_indices:
            matched_by_cell = app.optical_solid_face_record_for_mesh_cell(row_index, int(triangle_indices[0]))
            if not isinstance(matched_by_cell, dict) or str(matched_by_cell.get("face_id", "") or "") != str(picked.get("face_id", "") or ""):
                raise AssertionError(
                    "Row-backed Open 3D face assignment must resolve the picked mesh cell before point/normal fallback: "
                    f"picked={picked!r}, matched_by_cell={matched_by_cell!r}"
                )
        assigned = app.assign_optical_solid_face_function_at_world_point(
            row_index,
            point,
            "Full Reflecting",
            normal_world=normal,
            direct_context=True,
        )
        if assigned.get("function") != "Mirror" or assigned.get("port_role") != OPTICAL_SOLID_FACE_PORT_INTERACTION:
            raise AssertionError(f"Reflecting context assignment did not set mirror interaction metadata: {assigned!r}")

        reassigned = app.assign_optical_solid_face_function_at_world_point(
            row_index,
            point,
            "Uncoated",
            normal_world=normal,
            direct_context=True,
        )
        if reassigned.get("function") != OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT:
            raise AssertionError(f"Uncoated context assignment did not map to transmit physics: {reassigned!r}")
        if reassigned.get("port_role") != OPTICAL_SOLID_FACE_PORT_INTERACTION:
            raise AssertionError(f"Uncoated direct assignment should become a physical interaction surface, not an output port: {reassigned!r}")

        coplanar_metadata = normalize_optical_solid_face_metadata(
            app.rows[row_index].advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
        )
        coplanar_faces = list(coplanar_metadata.get("faces", []) or [])
        coplanar_extent = _optical_solid_face_metadata_extent(coplanar_faces, app.rows[row_index])
        coplanar_pair = None
        for first_index, first_face in enumerate(coplanar_faces):
            for second_face in coplanar_faces[first_index + 1 :]:
                if _optical_solid_face_records_share_plane(first_face, second_face, extent_mm=coplanar_extent):
                    coplanar_pair = (first_face, second_face)
                    break
            if coplanar_pair is not None:
                break
        if coplanar_pair is None:
            raise AssertionError("Expected promoted prism metadata to include a split coplanar face pair.")
        first_face, second_face = coplanar_pair
        first_face_id = str(first_face.get("face_id", "") or "")
        second_face_id = str(second_face.get("face_id", "") or "")
        coplanar_assigned = app.assign_optical_solid_face_function(
            row_index,
            first_face_id,
            "Full Reflecting",
            direct_context=True,
        )
        if second_face_id not in tuple(coplanar_assigned.get("related_face_ids", ()) or ()):
            raise AssertionError(f"Coplanar sibling face was not reported as updated: {coplanar_assigned!r}")
        mirror_metadata = normalize_optical_solid_face_metadata(
            app.rows[row_index].advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
        )
        sibling_saved = next((face for face in mirror_metadata.get("faces", []) if str(face.get("face_id", "")) == second_face_id), None)
        if sibling_saved is None or sibling_saved.get("function") != "Mirror":
            raise AssertionError("Coplanar sibling face did not inherit the Full Reflecting assignment.")

        metadata = normalize_optical_solid_face_metadata(
            app.rows[row_index].advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
        )
        saved = [
            face
            for face in list(metadata.get("faces", []) or [])
            if str(face.get("face_id", "") or "") == str(reassigned.get("face_id", "") or "")
        ]
        if not saved or str(saved[0].get("side_2d")) != "Auto":
            raise AssertionError("Direct Open 3D physics assignment should not require Left/Right/Up/Down side labels.")

        _fmt, triangles = le._read_stl_triangle_vertices(Path(metadata["source_stl"]))
        overlay_triangles = Kraken3DInspector._world_face_triangles_for_record(
            app.rows[row_index],
            triangles,
            saved[0],
            z_station=app._stl_row_z_station(row_index),
        )
        if overlay_triangles.ndim != 3 or overlay_triangles.shape[0] <= 0:
            raise AssertionError("Assigned face overlay geometry was not built for the directly assigned face.")
        if not Kraken3DInspector._assigned_optical_solid_face(saved[0]):
            raise AssertionError("Assigned Uncoated face was not recognized as an assigned face overlay.")

        _row, _path, full_metadata = app._optical_solid_face_metadata_for_row(row_index)
        face_ids = [
            str(face.get("face_id", "") or "").strip()
            for face in list(full_metadata.get("faces", []) or [])
            if str(face.get("face_id", "") or "").strip()
        ]
        if len(face_ids) < 2:
            raise AssertionError("Expected promoted optical solid to expose multiple assignable faces.")
        for face_id in face_ids:
            app.assign_optical_solid_face_function(row_index, face_id, "Uncoated", direct_context=True)
        all_metadata = normalize_optical_solid_face_metadata(
            app.rows[row_index].advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
        )
        assigned_count = sum(
            1
            for face in list(all_metadata.get("faces", []) or [])
            if Kraken3DInspector._assigned_optical_solid_face(face)
        )
        if assigned_count < len(face_ids):
            raise AssertionError("Assigning every picked CAD/STL face did not persist assigned-face metadata.")
        output_count = sum(
            1
            for face in list(all_metadata.get("faces", []) or [])
            if str(face.get("port_role", "") or "") == "Output Port"
        )
        if output_count:
            raise AssertionError("Direct Open 3D Uncoated assignments should not create inferred output-port anchors.")

        system, _rays, scene_bundle = app._build_preview_system_rays_bundle(
            sampling_mode=app._preview_3d_sampling_mode(),
            update_state=False,
        )
        downstream_overrides = {
            int(key): value
            for key, value in dict(getattr(system, "_optical_solid_output_port_pose_overrides", {}) or {}).items()
            if int(key) > row_index
        }
        if downstream_overrides:
            raise AssertionError(
                "Direct Open 3D interaction-surface assignments should not re-anchor downstream rows: "
                f"{sorted(downstream_overrides)}"
            )
        image_index = row_index + 1
        if image_index < len(app.rows) and app.rows[image_index].surface == "Image":
            image_transform = np.asarray(system.TRANS_2A[image_index], dtype=float).reshape(4, 4)
            expected_center = np.asarray((0.0, 0.0, app._stl_row_z_station(image_index)), dtype=float)
            actual_center = image_transform[:3, 3]
            if not np.allclose(actual_center, expected_center, atol=1e-6):
                raise AssertionError(
                    "Direct Open 3D interaction-surface assignments should leave the downstream Image "
                    "plane on its row station unless an explicit output port is authored: "
                    f"actual={actual_center.tolist()}, expected={expected_center.tolist()}"
                )
        mesh_items = app._scene_surface_meshes(system, scene_bundle, include_reference_surfaces=True)
        if not any(int(getattr(item, "row_index", -1)) == row_index for item in mesh_items):
            raise AssertionError("Promoted optical solid disappeared from the rebuilt 3D scene meshes.")
    finally:
        app.destroy()

    _validate_promoted_reflecting_prism_image_plane_is_not_intrusive()

    print("Open 3D face context assignment validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
