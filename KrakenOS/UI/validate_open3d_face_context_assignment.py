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
from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP


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


def _surface_event_counts(scene_bundle: object) -> Counter[str]:
    counts: Counter[str] = Counter()
    for path in list(getattr(scene_bundle, "ray_paths", []) or []):
        for event in list(getattr(path, "events", []) or []):
            if str(getattr(event, "event_kind", "") or "") != "surface":
                continue
            face_id = _event_face_id(event)
            interaction = str(getattr(event, "event_type", "") or getattr(event, "interaction", "") or "hit").strip().lower()
            if face_id:
                counts[f"{face_id}:{interaction}"] += 1
    return counts


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
        roles = _row_penta_roles(app, row_index)
        for face_id in roles["mirrors"]:
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
            # bugs/0919: this assumed the Image never moves -- true only while the old face
            # names put the "mirrors" on the wrong faces and nothing folded. With the true penta
            # mirrors the beam turns 90 deg and the image reference follows the output port (the
            # vendor-prism guard asserts exactly that). The bug guarded here was the Image landing
            # INSIDE the prism: so its centre must sit ON the central ray's exit leg, BEYOND the
            # exit face.
            image_transform = np.asarray(system.TRANS_2A[image_index], dtype=float).reshape(4, 4)
            actual_center = image_transform[:3, 3]
            paths = list(getattr(scene_bundle, "ray_paths", []) or [])
            central = min(paths, key=lambda path: float(np.hypot(
                *np.asarray(getattr(path, "points_world"), dtype=float)[0, :2]))) if paths else None
            pts = np.asarray(getattr(central, "points_world", np.empty((0, 3))), dtype=float)
            if pts.shape[0] < 3:
                raise AssertionError("Reflecting-prism repro traced no central exit leg.")
            leg_start, leg_end = pts[-2, :3], pts[-1, :3]
            leg = leg_end - leg_start
            leg_len = float(np.linalg.norm(leg))
            along = float(np.dot(actual_center - leg_start, leg / leg_len)) if leg_len > 0 else -1.0
            off_leg = float(np.linalg.norm(np.cross(actual_center - leg_start, leg / leg_len))) \
                if leg_len > 0 else float("inf")
            # the image is port-anchored: centred on the prism's OUTPUT axis, which an off-centre
            # input beam leaves parallel but offset (measured 3.6 mm) -- so "on the ray" is not
            # the claim; "beyond the exit face, facing along the exit" is
            image_axis = image_transform[:3, 2] / max(float(np.linalg.norm(image_transform[:3, 2])), 1e-12)
            facing = abs(float(np.dot(image_axis, leg / leg_len))) if leg_len > 0 else 0.0
            if not (along > 0.0 and facing > 0.999):
                raise AssertionError(
                    "Exact promoted reflecting-prism repro moved the Image plane into the scene object: "
                    f"centre {actual_center.tolist()} is {along:.3f} mm beyond the exit face "
                    f"(off the leg {off_leg:.3f} mm), axis . exit direction = {facing:.4f}"
                )

        ray_paths = list(getattr(scene_bundle, "ray_paths", []) or [])
        if len(ray_paths) < 10:
            raise AssertionError(f"Reflecting-prism repro traced too few rays: {len(ray_paths)}")
        sequences = [_surface_face_sequence(path) for path in ray_paths]
        entrance = _first_hit_face(scene_bundle)
        exit_face = next((face for face in roles["through"] if face != entrance), "")
        if entrance not in roles["through"] or not exit_face:
            raise AssertionError(f"Reflecting-prism repro entered at {entrance!r}, not a through face "
                                 f"{roles['through']!r}")
        incomplete = [sequence for sequence in sequences if exit_face not in sequence]
        if incomplete:
            raise AssertionError(
                "Exact promoted reflecting-prism repro left rays terminated before the exit face; "
                f"sequence_counts={Counter(sequences)!r}"
            )
    finally:
        app.destroy()


def _row_penta_roles(app, row_index: int) -> dict:
    """bugs/0919: the promoted prism's faces by GEOMETRY -- the names F003/F004/F006 were the
    old planar clustering's and the native STEP import renumbers them (see penta_face_roles)."""
    from KrakenOS.UI.validate_penta_mirror_3d_cascade import penta_face_roles

    _row, _path, metadata = app._optical_solid_face_metadata_for_row(row_index)
    return penta_face_roles(list(metadata.get("faces", []) or []))


def _first_hit_face(bundle) -> str:
    """The face the traced rays meet first (most common first surface event)."""
    firsts = []
    for path in list(getattr(bundle, "ray_paths", []) or []):
        sequence = _surface_face_sequence(path)
        if sequence:
            firsts.append(sequence[0])
    return Counter(firsts).most_common(1)[0][0] if firsts else ""


def _validate_face_assignment_drops_stale_trace_cache() -> None:
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
            raise AssertionError("Stale-cache validation could not promote the STEP prism.")
        row_index = int(promoted["row_index"])
        _system, _rays, before_bundle = app._build_preview_system_rays_bundle(
            sampling_mode="world_envelope",
            update_state=True,
        )
        if app._current_preview_scene_trace() is None:
            raise AssertionError("Expected a cached preview trace before assigning the mirror face.")
        before_counts = _surface_event_counts(before_bundle)
        first_face = _first_hit_face(before_bundle)
        if not before_counts.get(f"{first_face}:refraction", 0):
            raise AssertionError(f"Expected the unassigned prism to refract at the first-hit face "
                                 f"{first_face!r}; counts={before_counts!r}.")

        app.assign_optical_solid_face_function(row_index, first_face, "Full Reflecting", direct_context=True)
        if app._current_preview_scene_trace() is not None:
            raise AssertionError("CAD/STL face assignment left a stale current preview trace available.")
        if app.last_system is not None or app.last_rays is not None or app._last_scene_bundle is not None:
            raise AssertionError("CAD/STL face assignment did not clear stale traced system/ray/bundle state.")

        _system, _rays, after_bundle = app._build_preview_system_rays_bundle(
            sampling_mode="world_envelope",
            update_state=False,
        )
        ray_paths = list(getattr(after_bundle, "ray_paths", []) or [])
        after_counts = _surface_event_counts(after_bundle)
        if len(ray_paths) <= 0 or after_counts.get(f"{first_face}:reflection", 0) != len(ray_paths):
            raise AssertionError(
                f"Rebuilt trace after {first_face} Full Reflecting assignment did not reflect every ray: "
                f"rays={len(ray_paths)}, counts={after_counts!r}."
            )
        if after_counts.get(f"{first_face}:refraction", 0):
            raise AssertionError(f"Stale {first_face} refraction survived mirror assignment: counts={after_counts!r}.")
    finally:
        app.destroy()


def _validate_promote_step_assignment_remaps_overlay_face_id_by_world_pick() -> None:
    app = KrakenLayoutEditor(headless=True)
    try:
        app.imported_optical_step_path = PRISM_42779_STEP
        app.optical_step_rotation_x_deg = 0.0
        app.optical_step_rotation_y_deg = 90.0
        app.optical_step_rotation_z_deg = 180.0
        app.optical_step_placement_offset_xyz = (0.0, 5.338434311662937, 49.581543467386936)
        app.select_step_component("optical")

        inspector = object.__new__(Kraken3DInspector)
        inspector.editor = app
        inspector.status_var = app.status_var
        inspector._stl_placement_dirty = False
        inspector._active_refresh_sampling_mode = lambda: "world_envelope"
        inspector._debug_trace = lambda *args, **kwargs: None
        inspector._debug_actor_counts = lambda: {}
        inspector._clear_step_overlay_interaction_state = lambda label=None: None
        inspector.refresh_from_editor = lambda **kwargs: None
        inspector.highlight_row = lambda row_index: None

        picked_point = np.asarray((2.294262, 6.130541, 76.960132), dtype=float)
        picked_normal = np.asarray((0.0, -0.382684, 0.923879), dtype=float)
        Kraken3DInspector._promote_step_and_assign_face_function(
            inspector,
            "optical",
            picked_point,
            picked_normal,
            "Full Reflecting",
            face_id="F006",
        )
        if len(app.rows) < 3:
            raise AssertionError("Promote-and-assign did not insert the optical STEP row.")
        row_index = 1
        metadata = normalize_optical_solid_face_metadata(
            app.rows[row_index].advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
        )
        functions = {
            str(face.get("face_id", "") or ""): str(face.get("function", "") or "")
            for face in list(metadata.get("faces", []) or [])
            if isinstance(face, dict)
        }
        # bugs/0919: the face that must end up Mirror is the ROW face at the picked world point
        # and normal -- named by geometry, since the face numbering drifted -- and it must be
        # the only one: the temporary overlay label ("F006" here) is never trusted
        at_pick = app.optical_solid_face_record_at_world_point(
            row_index, picked_point, normal_world=picked_normal, assigned_only=False)
        expected = str((at_pick or {}).get("face_id", "") or "")
        mirrored = sorted(face for face, function in functions.items() if function == "Mirror")
        if not expected or mirrored != [expected]:
            raise AssertionError(
                "Imported STEP promote-and-assign must remap the temporary overlay face label by "
                f"picked world point/normal: expected only {expected!r} mirrored, got {mirrored!r}; "
                f"functions={functions!r}."
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
        # bugs/0919: promotion now DERIVES a 2D side label per face (Right/Down/...); remember
        # them, so the check below can tell "kept its label" from "the assignment invented one"
        sides_before = {
            str(face.get("face_id", "") or ""): str(face.get("side_2d", "Auto") or "Auto")
            for face in list(normalize_optical_solid_face_metadata(
                app.rows[row_index].advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
            ).get("faces", []) or [])
        }
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
            # bugs/0919: the native STEP import (58f0e215, after this guard) keeps B-rep faces
            # whole, so this prism no longer ARRIVES with a split plane. The claim -- assigning
            # one record of a split plane updates its coplanar siblings -- still matters (a
            # clustered STL or an old save can be split), so make the split: clone a face
            # record under a new id into the row's own metadata, and assign as before.
            import copy

            raw = dict(app.rows[row_index].advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}) or {})
            raw_faces = [dict(face) for face in list(raw.get("faces", []) or [])]
            # not the face assigned directly above -- that one's saved state is checked below
            direct_id = str(reassigned.get("face_id", "") or "")
            template = next((face for face in raw_faces
                             if str(face.get("face_id", "")).strip()
                             and str(face.get("face_id", "")) != direct_id), None)
            if template is None:
                raise AssertionError("Promoted prism metadata has no face record to split.")
            sibling = copy.deepcopy(template)
            sibling["face_id"] = f"{template['face_id']}_split"
            raw["faces"] = raw_faces + [sibling]
            app.rows[row_index].advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = raw
            coplanar_metadata = normalize_optical_solid_face_metadata(raw)
            coplanar_faces = list(coplanar_metadata.get("faces", []) or [])
            coplanar_extent = _optical_solid_face_metadata_extent(coplanar_faces, app.rows[row_index])
            by_id = {str(face.get("face_id", "")): face for face in coplanar_faces}
            first, second = by_id.get(str(template["face_id"])), by_id.get(sibling["face_id"])
            if first is None or second is None or not _optical_solid_face_records_share_plane(
                    first, second, extent_mm=coplanar_extent):
                raise AssertionError("A cloned face record is not recognised as coplanar with its source.")
            coplanar_pair = (first, second)
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
        # the claim: a direct assignment neither REQUIRES nor INVENTS a side label -- the face
        # ends with the label it arrived with (promotion may have derived one), or Auto
        if not saved or str(saved[0].get("side_2d")) not in {
                "Auto", sides_before.get(str(saved[0].get("face_id", "")), "Auto")}:
            raise AssertionError(
                "Direct Open 3D physics assignment should not require Left/Right/Up/Down side labels "
                f"(side {saved[0].get('side_2d') if saved else None!r}, arrived "
                f"{sides_before.get(str(saved[0].get('face_id', '')) if saved else '', None)!r}).")

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
    _validate_face_assignment_drops_stale_trace_cache()
    _validate_promote_step_assignment_remaps_overlay_face_id_by_world_pick()

    print("Open 3D face context assignment validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
