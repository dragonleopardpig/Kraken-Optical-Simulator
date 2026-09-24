"""Validate that 2-D views are projections of the Open 3-D display rays."""

from __future__ import annotations

from collections import Counter
import tempfile
from pathlib import Path

import numpy as np
import KrakenOS as Kos

import KrakenOS.UI.layout_editor as le
from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    KrakenLayoutEditor,
    SurfaceRow,
    cluster_optical_solid_planar_faces,
    solve_optical_solid_left_input_pose,
)
from KrakenOS.UI.saved_layout_plot import _snapshot_editor
from KrakenOS.UI.scene_geometry import SceneSource3D, ray_path_terminal_status_from_events
from KrakenOS.UI.scene_projector import SceneProjector2D, scene_display_center_radius
from KrakenOS.UI.source_trace_helpers import build_scene_source_bundle, source_metadata_for_bundle, trace_bundle
from KrakenOS.UI.validate_vendor_prism_42779 import (
    PRISM_42779_STEP,
    _build_vendor_prism_trace_system,
    _metadata_for_candidates,
)


def _penta_settings() -> dict[str, object]:
    return {
        "object_mode": "Finite",
        "display_orientation": "YZ",
        "wavelength": "0.55",
        "ray_count": "31",
        "ray_height_factor": "0.4",
        "full_pupil": False,
        "source_model": "Collimated disk source",
        "pupil_pattern": "Meridional fan",
        "source_radius": "5",
        "source_cone_angle": "0",
        "source_power": "1",
        "source_seed": "1",
        "source_x": "0",
        "source_y": "0",
        "source_z": "0",
        "source_l": "0",
        "source_m": "0",
        "source_n": "1",
        "source_angular_weight": "Uniform solid angle",
        "scene_sources": [
            {
                "source_id": "source:0",
                "name": "Source 1",
                "enabled": True,
                "physical": True,
                "role": "illumination",
                "model": "Collimated disk source",
                "ray_count": 31,
                "power": 1.0,
                "wavelength": 0.55,
                "radius": 5.0,
                "cone_deg": 0.0,
                "seed": 1,
                "source_x": 0.0,
                "source_y": 0.0,
                "source_z": 0.0,
                "source_l": 0.0,
                "source_m": 0.0,
                "source_n": 1.0,
                "angular_weight": "Uniform solid angle",
            }
        ],
        "scene_row_order": "after_object",
        "analysis_surface": "Auto",
        "analysis_branch_filter": "All paths",
        "ray_display_mode": "All rays",
        "detector_bins": "Auto",
        "coherent_sum_mode": "By source ray",
        "branch_field_propagation_mm": "0.0",
        "aperture_type": "EPD",
        "aperture_value": "4.0",
        "trace_mode": "Auto",
        "nonseq_target_surface": "Auto",
        "nonseq_ns_limit": "200",
        "image_diameter_mode": "Manual",
    }


def _penta_bundle():
    original_cache = le.CAD_CACHE_DIR
    temp_dir = tempfile.TemporaryDirectory(prefix="kraken-projection-sync-")
    le.CAD_CACHE_DIR = Path(temp_dir.name)
    try:
        mesh_path, _source_path, _source_format = le._optical_solid_mesh_path_from_source(PRISM_42779_STEP)
        candidates = cluster_optical_solid_planar_faces(mesh_path)
        metadata = _metadata_for_candidates(candidates, mesh_path)
        solution = solve_optical_solid_left_input_pose(metadata)
        if solution is None:
            raise RuntimeError("Could not solve 42779 penta prism left-input pose")
        system = _build_vendor_prism_trace_system(mesh_path, metadata, solution, image_diameter=1.0)
        source = SceneSource3D(
            source_id="source:0",
            name="Source 1",
            role="illumination",
            model="Collimated disk source",
            enabled=True,
            physical=True,
            origin=np.zeros(3, dtype=float),
            direction=np.asarray((0.0, 0.0, 1.0), dtype=float),
            ray_count=31,
            wavelength=0.55,
            power=1.0,
            weight_per_ray=1.0 / 31.0,
            settings={"radius": 5.0, "cone_deg": 0.0, "seed": 1},
        )
        source_bundle = build_scene_source_bundle(source)
        if source_bundle is None:
            raise RuntimeError("Could not build penta collimated source bundle")
        rays = Kos.raykeeper(system)
        trace_bundle(
            Kos.NsTraceLoop,
            source_bundle,
            0.55,
            rays,
            clean=1,
            metadata=source_metadata_for_bundle(
                source_bundle,
                0.55,
                source,
                launch_metadata={"launch_sampling_mode": "validated_collimated_penta"},
            ),
        )
        rows = [
            SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=25.0, glass="AIR", drawing=0),
            SurfaceRow(
                surface="Solid 3D STL",
                name="Edmund 42779 vendor prism",
                glass="BK7",
                thickness=40.0,
                diameter=25.0,
                axis_move=2.0,
                tilt_x=float(solution["tilts"][0]),
                tilt_y=float(solution["tilts"][1]),
                tilt_z=float(solution["tilts"][2]),
                desp_x=float(solution["desp"][0]),
                desp_y=float(solution["desp"][1]),
                desp_z=float(solution["desp"][2]),
                advanced={OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata, "Solid_3d_stl": str(mesh_path)},
            ),
            SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=1.0, glass="AIR"),
        ]
    finally:
        le.CAD_CACHE_DIR = original_cache
    settings = _penta_settings()
    editor = _snapshot_editor(rows, settings)
    editor._projection_sync_temp_dir = temp_dir
    editor.current_layout_file = PRISM_42779_STEP
    editor._normalize_special_rows()
    editor.last_system = system
    editor.last_rays = rays
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    editor._preview_field_ray_count = 31
    editor._preview_field_bundle_count = 1
    max_radius = max((max(float(row.diameter) / 2.0, 0.5) for row in rows), default=1.0)
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    editor._last_scene_bundle = bundle
    return editor, rays, bundle


def _surface_face_sequence(path: object) -> tuple[str, ...]:
    faces: list[str] = []
    for event in list(getattr(path, "events", []) or []):
        if str(getattr(event, "event_kind", "") or "") != "surface":
            continue
        face = str(getattr(event, "mesh_face_id", "") or "").strip()
        if face:
            faces.append(face)
    return tuple(faces)


def _validate_projection_sync(editor: KrakenLayoutEditor, rays: object, bundle: object) -> list[str]:
    failures: list[str] = []
    paths_by_index = KrakenLayoutEditor._scene_ray_path_by_index(bundle)
    center, radius = scene_display_center_radius(bundle)
    records = list(editor._iter_3d_scene_ray_records(rays, bundle))
    if len(records) != len(getattr(bundle, "ray_paths", []) or []):
        failures.append(f"3D records={len(records)} bundle paths={len(getattr(bundle, 'ray_paths', []) or [])}")
    for plane in ("YZ", "XZ", "XY"):
        projector = SceneProjector2D(plane)
        projected = projector.project_bundle(bundle)
        projected_by_index = {int(ray.ray_index): ray for ray in projected.rays}
        if len(projected_by_index) != len(records):
            failures.append(f"{plane}: projected rays={len(projected_by_index)} 3D records={len(records)}")
        for ray_index, _color, ray_pts, terminal_status in records:
            ray_index = int(ray_index)
            projected_ray = projected_by_index.get(ray_index)
            if projected_ray is None:
                failures.append(f"{plane}: missing projected ray {ray_index}")
                continue
            path = paths_by_index.get(ray_index)
            terminal_target = KrakenLayoutEditor._missed_detector_target_for_path(bundle, path)
            terminal_direction = KrakenLayoutEditor._terminal_display_direction_for_path(path)
            display_3d, _was_bounded = KrakenLayoutEditor._bounded_3d_ray_points_for_display(
                ray_pts,
                center,
                radius,
                terminal_status=terminal_status,
                terminal_target=terminal_target,
                terminal_direction=terminal_direction,
            )
            projected_from_3d = projector.project_xyz_points(display_3d)
            points_2d = np.asarray(projected_ray.points_2d, dtype=float)
            if points_2d.shape != projected_from_3d.shape:
                failures.append(
                    f"{plane}: ray {ray_index} shape mismatch 2D={points_2d.shape} 3D={projected_from_3d.shape}"
                )
                continue
            if not np.allclose(points_2d, projected_from_3d, rtol=0.0, atol=1.0e-9):
                delta = float(np.nanmax(np.abs(points_2d - projected_from_3d)))
                failures.append(f"{plane}: ray {ray_index} projection delta={delta:.3e}")
    return failures


def _validate_penta_physics(bundle: object) -> list[str]:
    failures: list[str] = []
    paths = list(getattr(bundle, "ray_paths", []) or [])
    if len(paths) != 31:
        failures.append(f"penta ray count={len(paths)}, expected 31")
    # bugs/0877: this used to pin the exact tuple ("F005", "F003", "F004", "F006"). The two
    # INTERNAL reflection faces swapped labels when the planar-face clustering renumbered them,
    # which says nothing about the light -- a ray must strike them in a fixed geometric order
    # whatever they are called. Pin the SHAPE instead: one path for every ray, in through the
    # entry face, two distinct internal reflections, out through the exit face.
    sequences = Counter(_surface_face_sequence(path) for path in paths)
    if len(sequences) != 1:
        failures.append(f"penta rays take more than one path: {dict(sequences)}")
    else:
        sequence = next(iter(sequences))
        if (len(sequence) != 4 or sequence[0] != "F005" or sequence[-1] != "F006"
                or sequence[1] == sequence[2]):
            failures.append(
                f"penta face sequence={sequence}, expected entry F005, two distinct internal "
                "reflections, exit F006")
    # A 1 mm image diameter cannot catch a 10 mm collimated beam, so only the central ray lands.
    # The other 30 now report missed_detector rather than escaped -- the detector-miss work made
    # a miss VISIBLE instead of silently leaving the scene. What must not happen is a ray being
    # absorbed or stopped inside the prism.
    statuses = Counter(ray_path_terminal_status_from_events(path) for path in paths)
    unexpected_statuses = set(statuses) - {"escaped", "hit_detector", "missed_detector"}
    if unexpected_statuses:
        failures.append(f"unexpected penta terminal statuses={dict(statuses)}")
    if not statuses.get("hit_detector"):
        failures.append(f"no penta ray reached the detector: {dict(statuses)}")
    exit_directions: list[np.ndarray] = []
    for path in paths:
        points = np.asarray(getattr(path, "points_world", []), dtype=float)
        if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
            failures.append(f"penta ray {getattr(path, 'ray_index', '?')} has no final 3D segment")
            continue
        segment = points[-1, :3] - points[-2, :3]
        norm = float(np.linalg.norm(segment))
        if not np.isfinite(norm) or norm <= 1.0e-12:
            failures.append(f"penta ray {getattr(path, 'ray_index', '?')} has degenerate final 3D segment")
            continue
        exit_directions.append(segment / norm)
    if exit_directions:
        # bugs/0877: this used to demand the exit run along -Y. The port-anchored pose solution
        # puts it along +Y, and validate_vendor_prism_42779 independently agrees (its runtime
        # trace lands at y=+52.5), so the old assertion pinned a sign, not the physics. What a
        # penta prism actually guarantees is a CONSTANT 90 deg deviation with collimation
        # preserved, whichever way the solved pose faces -- assert that.
        directions = np.asarray(exit_directions, dtype=float)
        mean_direction = directions[0]
        spread = float(np.nanmax(np.linalg.norm(directions - mean_direction, axis=1)))
        launch = np.asarray((0.0, 0.0, 1.0), dtype=float)
        deviation_cos = float(abs(np.dot(mean_direction, launch)))
        if spread > 1.0e-4:
            failures.append(
                f"penta exit is not collimated: direction spread={spread:.3e}, "
                f"exit={mean_direction.tolist()}"
            )
        if deviation_cos > 1.0e-4:
            failures.append(
                "penta prism must deviate the beam by 90 deg: "
                f"|exit . launch|={deviation_cos:.3e}, exit={mean_direction.tolist()}"
            )
    return failures


def _validate_2d_ray_renderer_segments() -> list[str]:
    """Ensure event vertices are rendered as true segment stops.

    A single polyline can draw a projecting cap or miter join through a sharp
    mirror-hit vertex, which looks like a false transmitted ray in prism plots.
    The 2-D renderer should instead draw the ray as physical path segments with
    butt caps.
    """
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    from KrakenOS.UI.scene_geometry import ProjectedRay2D, ProjectedScene2D
    from KrakenOS.UI.scene_renderer_2d import render_scene_2d

    failures: list[str] = []
    ray = ProjectedRay2D(
        ray_index=0,
        color="#39FF14",
        points_2d=np.asarray(
            (
                (0.0, 0.0),
                (1.0, 0.0),
                (0.2, 0.8),
            ),
            dtype=float,
        ),
    )
    fig, ax = plt.subplots()
    try:
        render_scene_2d(ProjectedScene2D(rays=[ray]), ax, ray_count_hint=3)
        ray_collections = [
            collection
            for collection in list(ax.collections)
            if isinstance(collection, LineCollection)
        ]
        if len(ray_collections) != 1:
            failures.append(f"ray renderer collection count={len(ray_collections)}, expected 1")
            return failures
        collection = ray_collections[0]
        segment_count = len(collection.get_segments())
        if segment_count != 2:
            failures.append(f"ray renderer segment count={segment_count}, expected 2")
        if collection.get_capstyle() != "butt":
            failures.append(f"ray renderer capstyle={collection.get_capstyle()!r}, expected 'butt'")
        if collection.get_joinstyle() != "round":
            failures.append(f"ray renderer joinstyle={collection.get_joinstyle()!r}, expected 'round'")
        if ax.lines:
            failures.append(f"ray renderer left {len(ax.lines)} Line2D ray artifacts; expected segment collection only")
    finally:
        plt.close(fig)
    return failures


def _validate_3d_ray_renderer_segments() -> list[str]:
    """Ensure Open 3D rays are rendered as event-bounded segments."""
    failures: list[str] = []
    event_vertex = np.asarray((10.0, 0.0, 0.0), dtype=float)
    mesh = KrakenLayoutEditor._ray_segment_mesh_for_3d_display(
        np.asarray(
            (
                (0.0, 0.0, 0.0),
                event_vertex,
                (10.0, 5.0, 0.0),
            ),
            dtype=float,
        ),
        vertex_inset=0.5,
    )
    if mesh is None:
        failures.append("3D ray renderer returned no segment mesh")
        return failures
    if int(getattr(mesh, "n_points", 0)) != 4:
        failures.append(f"3D ray renderer points={int(getattr(mesh, 'n_points', 0))}, expected 4")
    lines = np.asarray(getattr(mesh, "lines", []), dtype=int)
    if lines.size != 6 or not np.array_equal(lines.reshape(-1, 3)[:, 0], np.asarray((2, 2), dtype=int)):
        failures.append(f"3D ray renderer line encoding={lines.tolist()}, expected two disconnected segments")
    points = np.asarray(getattr(mesh, "points", []), dtype=float)
    if points.shape == (4, 3):
        if not np.allclose(points[0], (0.0, 0.0, 0.0), rtol=0.0, atol=1.0e-12):
            failures.append(f"3D ray first endpoint moved to {points[0].tolist()}")
        if not np.allclose(points[-1], (10.0, 5.0, 0.0), rtol=0.0, atol=1.0e-12):
            failures.append(f"3D ray final endpoint moved to {points[-1].tolist()}")
        if np.any(np.all(np.isclose(points, event_vertex, rtol=0.0, atol=1.0e-12), axis=1)):
            failures.append("3D ray segment mesh keeps an exact interior event vertex")
    return failures


def run_checks() -> tuple[bool, list[str]]:
    """Penta-harness entry point (bugs/0877): this guard is a registered phase now."""
    editor, rays, bundle = _penta_bundle()
    groups = (
        ("2D views are projections of the Open 3D display rays",
         _validate_projection_sync(editor, rays, bundle)),
        ("the penta prism deviates the collimated beam by 90 deg",
         _validate_penta_physics(bundle)),
        ("the 2D renderer stops segments at event vertices",
         _validate_2d_ray_renderer_segments()),
        ("the 3D renderer stops segments at event vertices",
         _validate_3d_ray_renderer_segments()),
    )
    notes = []
    for title, failures in groups:
        if failures:
            notes.extend("FAIL " + str(failure) for failure in failures)
        else:
            notes.append("= " + title)
    return not any(failures for _title, failures in groups), notes


def main() -> int:
    editor, rays, bundle = _penta_bundle()
    failures = []
    failures.extend(_validate_projection_sync(editor, rays, bundle))
    failures.extend(_validate_penta_physics(bundle))
    failures.extend(_validate_2d_ray_renderer_segments())
    failures.extend(_validate_3d_ray_renderer_segments())
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("2D/Open 3D projection sync validator passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
