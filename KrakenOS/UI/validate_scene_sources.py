from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

import KrakenOS as Kos
import KrakenOS.UI.layout_editor as layout_editor_module
from KrakenOS.UI.layout_editor import SurfaceRow, _build_system_from_specs
from KrakenOS.UI.layout_editor import (
    KrakenLayoutEditor,
    NonSequentialTracePreviewError,
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    SOURCE_MODEL_DEFAULT,
    normalize_optical_solid_face_metadata,
)
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.scene_builder import build_scene_bundle
from KrakenOS.UI.source_trace_helpers import (
    _default_finite_cone_bundle_from_settings,
    build_saved_layout_rays,
    build_scene_source_bundle,
    layout_uses_nonseq,
    scene_sources_from_settings,
)


@dataclass
class SceneSourceCheck:
    check: str
    ok: bool
    detail: str


def _row_specs(rows: list[SurfaceRow]) -> list[dict[str, object]]:
    return [
        {
            "surface": row.surface,
            "name": row.name,
            "rc": row.rc,
            "k": row.k,
            "axicon": row.axicon,
            "diff_ord": row.diff_ord,
            "grating_d": row.grating_d,
            "grating_angle": row.grating_angle,
            "thickness": row.thickness,
            "diameter": row.diameter,
            "in_diameter": row.in_diameter,
            "drawing": row.drawing,
            "extra_data": row.extra_data,
            "uda": row.uda,
            "advanced": row.advanced,
            "tilt_x": row.tilt_x,
            "tilt_y": row.tilt_y,
            "tilt_z": row.tilt_z,
            "desp_x": row.desp_x,
            "desp_y": row.desp_y,
            "desp_z": row.desp_z,
            "axis_move": row.axis_move,
            "glass": row.glass,
        }
        for row in rows
    ]


def _text(seq, index: int = 0) -> str:
    try:
        return str(np.asarray(seq[index], dtype=object).reshape(-1)[0])
    except Exception:
        return ""


def validate_scene_sources() -> list[SceneSourceCheck]:
    rows = [
        SurfaceRow(label="0", surface="Object", name="Object", thickness=50.0, diameter=20.0, drawing=0.0, glass="AIR"),
        SurfaceRow(label="1", surface="Image", name="Image", thickness=0.0, diameter=20.0, drawing=0.0, glass="AIR"),
    ]
    settings = {
        "wavelength": "0.532",
        "ray_count": "5",
        "source_model": "Collimated disk source",
        "source_radius": "2.0",
        "source_cone_angle": "0.0",
        "source_power": "2.5",
        "source_x": "1.0",
        "source_y": "2.0",
        "source_z": "0.0",
        "source_l": "0.0",
        "source_m": "0.0",
        "source_n": "2.0",
    }
    editor = _snapshot_editor(rows, settings)
    sources = editor._collect_scene_sources()
    source = sources[0] if sources else None
    bundle = build_scene_bundle(rows=rows, system=None, rays=None, sources=sources)
    target_choices = editor._scene_source_aim_target_choices()
    source_origin = editor._surface_reference_world_point(0)
    image_target = editor._surface_reference_world_point(1)
    expected_aim = image_target - source_origin
    expected_aim = expected_aim / float(np.linalg.norm(expected_aim))
    aim_result = editor.scene_source_direction_to_row(
        {
            "source_x": float(source_origin[0]),
            "source_y": float(source_origin[1]),
            "source_z": float(source_origin[2]),
        },
        1,
    )
    aimed_source = editor._scene_source_from_spec(
        {
            **editor._default_scene_source_spec(0),
            "source_x": float(source_origin[0]),
            "source_y": float(source_origin[1]),
            "source_z": float(source_origin[2]),
            "source_l": float(aim_result["source_l"]),
            "source_m": float(aim_result["source_m"]),
            "source_n": float(aim_result["source_n"]),
        },
        0,
        wavelength=0.532,
    )
    placed_result = editor.scene_source_place_at_row_standoff(
        {
            "source_l": 0.0,
            "source_m": 0.0,
            "source_n": 1.0,
        },
        1,
        25.0,
    )
    placed_origin = np.asarray(
        [placed_result["source_x"], placed_result["source_y"], placed_result["source_z"]],
        dtype=float,
    )
    placed_direction = np.asarray(
        [placed_result["source_l"], placed_result["source_m"], placed_result["source_n"]],
        dtype=float,
    )
    face_metadata = normalize_optical_solid_face_metadata(
        {
            "faces": [
                {
                    "face_id": "F001",
                    "side_2d": "Left",
                    "function": OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
                    "normal": [0.0, 0.0, 1.0],
                    "centroid": [0.0, 5.0, 10.0],
                    "area_mm2": 100.0,
                }
            ]
        }
    )
    face_rows = [
        SurfaceRow(label="0", surface="Object", name="Object", thickness=20.0, diameter=20.0, drawing=0.0, glass="AIR"),
        SurfaceRow(
            label="1",
            surface="Solid 3D STL",
            name="CAD target",
            thickness=0.0,
            diameter=20.0,
            drawing=0.0,
            glass="AIR",
            desp_x=1.0,
            desp_y=2.0,
            desp_z=3.0,
            advanced={OPTICAL_SOLID_FACES_ADVANCED_ATTR: face_metadata},
        ),
        SurfaceRow(label="2", surface="Image", name="Image", thickness=0.0, diameter=20.0, drawing=0.0, glass="AIR"),
    ]
    face_editor = _snapshot_editor(face_rows, settings)
    face_choices = face_editor._scene_source_aim_target_choices()
    face_choice = face_editor._scene_source_target_choice_for(1, "F001")
    face_target = face_editor._surface_reference_world_point(1, face_id="F001")
    face_pick = face_editor.scene_source_face_anchor_at_world_point(1, face_target)
    expected_face_target = np.asarray((1.0, 7.0, 33.0), dtype=float)
    face_place = face_editor.scene_source_place_at_row_standoff(
        {"source_l": 0.0, "source_m": 0.0, "source_n": 1.0},
        1,
        8.0,
        face_id="F001",
    )
    face_place_origin = np.asarray(
        [face_place["source_x"], face_place["source_y"], face_place["source_z"]],
        dtype=float,
    )

    checks: list[SceneSourceCheck] = [
        SceneSourceCheck(
            "single Source panel becomes one SceneSource3D",
            source is not None and len(sources) == 1 and source.source_id == "source:0",
            f"count={len(sources)} id={getattr(source, 'source_id', '')}",
        ),
        SceneSourceCheck(
            "physical source role is illumination",
            bool(source and source.physical and source.role == "illumination"),
            f"role={getattr(source, 'role', '')} physical={getattr(source, 'physical', None)}",
        ),
        SceneSourceCheck(
            "source direction is normalized",
            bool(source and np.allclose(source.direction, np.asarray((0.0, 0.0, 1.0), dtype=float))),
            f"direction={getattr(source, 'direction', None)}",
        ),
        SceneSourceCheck(
            "source direction preset maps horizontal +Z",
            editor._source_direction_preset_vector("Horizontal +Z (right)") == (0.0, 0.0, 1.0)
            and editor._source_direction_preset_label((0.0, 0.0, 1.0)) == "Horizontal +Z (right)",
            (
                f"vector={editor._source_direction_preset_vector('Horizontal +Z (right)')} "
                f"label={editor._source_direction_preset_label((0.0, 0.0, 1.0))}"
            ),
        ),
        SceneSourceCheck(
            "source direction preset maps vertical -Y",
            editor._source_direction_preset_vector("Vertical -Y (down)") == (0.0, -1.0, 0.0)
            and editor._source_direction_preset_label((0.0, -1.0, 0.0)) == "Vertical -Y (down)",
            (
                f"vector={editor._source_direction_preset_vector('Vertical -Y (down)')} "
                f"label={editor._source_direction_preset_label((0.0, -1.0, 0.0))}"
            ),
        ),
        SceneSourceCheck(
            "source aim target choices include surface rows",
            len(target_choices) == 2 and target_choices[0].startswith("0:") and target_choices[1].startswith("1:"),
            ", ".join(target_choices),
        ),
        SceneSourceCheck(
            "source-to-row aim helper normalizes LMN",
            np.allclose(
                np.asarray([aim_result["source_l"], aim_result["source_m"], aim_result["source_n"]], dtype=float),
                expected_aim,
            ),
            f"aim={aim_result}",
        ),
        SceneSourceCheck(
            "aimed scene source preserves target direction",
            np.allclose(np.asarray(aimed_source.direction, dtype=float), expected_aim),
            f"direction={aimed_source.direction} expected={expected_aim}",
        ),
        SceneSourceCheck(
            "source standoff placement positions origin upstream of target",
            np.allclose(placed_origin, image_target - np.asarray((0.0, 0.0, 25.0), dtype=float))
            and np.allclose(placed_direction, np.asarray((0.0, 0.0, 1.0), dtype=float)),
            f"origin={placed_origin} direction={placed_direction} target={image_target}",
        ),
        SceneSourceCheck(
            "CAD/STL face anchors appear as source aim targets",
            any("1/F001:" in choice for choice in face_choices),
            ", ".join(face_choices),
        ),
        SceneSourceCheck(
            "CAD/STL face anchor can preselect Scene Source Manager target",
            face_choice.startswith("1/F001:"),
            face_choice or "<empty>",
        ),
        SceneSourceCheck(
            "source aiming can target a CAD/STL face centroid",
            np.allclose(face_target, expected_face_target),
            f"target={face_target} expected={expected_face_target}",
        ),
        SceneSourceCheck(
            "3D source-target pick resolves nearest CAD/STL face anchor",
            face_pick is not None and str(face_pick.get("face_id", "") or "") == "F001",
            f"picked={face_pick.get('face_id') if face_pick is not None else '-'}",
        ),
        SceneSourceCheck(
            "source standoff placement supports CAD/STL face anchors",
            np.allclose(face_place_origin, expected_face_target - np.asarray((0.0, 0.0, 8.0), dtype=float))
            and str(face_place.get("face_id", "")) == "F001",
            f"origin={face_place_origin} face={face_place.get('face_id')} label={face_place.get('target_label')}",
        ),
        SceneSourceCheck(
            "SceneBundle carries source records",
            len(bundle.sources) == 1 and bundle.sources[0].source_id == "source:0",
            f"bundle_sources={len(bundle.sources)}",
        ),
    ]

    system = _build_system_from_specs(_row_specs(rows))
    rays = Kos.raykeeper(system)
    source_bundle = editor._build_random_source_bundle(sample_count=5)
    metadata = editor._source_metadata_for_bundle(source_bundle, 0.532)
    Kos.TraceLoop(*source_bundle, 0.532, rays, clean=1, source_metadata=metadata)
    traced_bundle = build_scene_bundle(
        rows=rows,
        system=system,
        rays=rays,
        sources=sources,
        field_count=1,
        ray_count_per_field=5,
    )
    checks.extend(
        [
            SceneSourceCheck(
                "source metadata includes source id/name/role",
                bool(
                    metadata
                    and metadata[0].get("source_id") == "source:0"
                    and metadata[0].get("source_name") == "Source 1"
                    and metadata[0].get("source_role") == "illumination"
                ),
                str(metadata[0] if metadata else {}),
            ),
            SceneSourceCheck(
                "raykeeper preserves source id/name/role",
                _text(getattr(rays, "SOURCE_ID", [])) == "source:0"
                and _text(getattr(rays, "SOURCE_NAME", [])) == "Source 1"
                and _text(getattr(rays, "SOURCE_ROLE", [])) == "illumination",
                (
                    f"id={_text(getattr(rays, 'SOURCE_ID', []))} "
                    f"name={_text(getattr(rays, 'SOURCE_NAME', []))} "
                    f"role={_text(getattr(rays, 'SOURCE_ROLE', []))}"
                ),
            ),
            SceneSourceCheck(
                "RayPath3D carries source identity",
                bool(traced_bundle.ray_paths and traced_bundle.ray_paths[0].source_id == "source:0"),
                (
                    f"paths={len(traced_bundle.ray_paths)} "
                    f"id={traced_bundle.ray_paths[0].source_id if traced_bundle.ray_paths else ''}"
                ),
            ),
        ]
    )

    graph_records = editor._collect_nonseq_scene_graph_records()
    graph_ids = {str(record.get("id", "")) for record in graph_records}
    checks.append(
        SceneSourceCheck(
            "non-sequential scene graph exposes source object",
            "sources" in graph_ids and "source:0" in graph_ids,
            ", ".join(sorted(graph_ids)[:8]),
        )
    )

    cone_settings = {
        **settings,
        "source_model": "Random point cone",
        "ray_count": "11",
        "source_radius": "0.0",
        "source_cone_angle": "8.0",
        "source_seed": "12",
    }
    cone_sources = scene_sources_from_settings(cone_settings, wavelength=0.532)
    cone_bundle = build_scene_source_bundle(cone_sources[0]) if cone_sources else None
    cone_dirs = None
    cone_angles = np.asarray([], dtype=float)
    if cone_bundle is not None:
        cone_dirs = np.column_stack([np.asarray(cone_bundle[index], dtype=float) for index in (3, 4, 5)])
        axis = np.asarray(cone_sources[0].direction, dtype=float)
        axis = axis / max(float(np.linalg.norm(axis)), 1e-12)
        cone_angles = np.rad2deg(np.arccos(np.clip(cone_dirs @ axis, -1.0, 1.0)))
    checks.append(
        SceneSourceCheck(
            "source helper applies random-point cone half angle",
            cone_bundle is not None
            and cone_dirs is not None
            and len(cone_dirs) == 11
            and float(np.max(cone_angles)) > 0.25
            and float(np.max(cone_angles)) <= 8.0 + 1e-9,
            f"angles_deg={np.round(cone_angles, 4).tolist()}",
        )
    )
    disk_cone_settings = {
        **settings,
        "source_model": "Collimated disk source",
        "ray_count": "9",
        "source_radius": "2.0",
        "source_cone_angle": "6.0",
        "source_seed": "7",
    }
    disk_cone_sources = scene_sources_from_settings(disk_cone_settings, wavelength=0.532)
    disk_cone_bundle = build_scene_source_bundle(disk_cone_sources[0]) if disk_cone_sources else None
    disk_cone_angles = np.asarray([], dtype=float)
    if disk_cone_bundle is not None:
        disk_cone_dirs = np.column_stack([np.asarray(disk_cone_bundle[index], dtype=float) for index in (3, 4, 5)])
        disk_cone_axis = np.asarray(disk_cone_sources[0].direction, dtype=float)
        disk_cone_axis = disk_cone_axis / max(float(np.linalg.norm(disk_cone_axis)), 1e-12)
        disk_cone_angles = np.rad2deg(np.arccos(np.clip(disk_cone_dirs @ disk_cone_axis, -1.0, 1.0)))
    checks.append(
        SceneSourceCheck(
            "collimated disk source honors nonzero manager half cone",
            disk_cone_bundle is not None
            and len(np.asarray(disk_cone_bundle[0])) == 9
            and float(np.max(disk_cone_angles)) > 0.25
            and float(np.max(disk_cone_angles)) <= 6.0 + 1e-9,
            f"angles_deg={np.round(disk_cone_angles, 4).tolist()}",
        )
    )
    live_disk_source = editor._scene_source_from_spec(
        {
            **editor._default_scene_source_spec(0),
            "model": "Collimated disk source",
            "ray_count": 9,
            "radius": 2.0,
            "cone_deg": 6.0,
            "seed": 7,
        },
        0,
        wavelength=0.532,
    )
    live_disk_bundle = editor._build_scene_source_bundle(live_disk_source)
    live_disk_angles = np.asarray([], dtype=float)
    if live_disk_bundle is not None:
        live_disk_dirs = np.column_stack([np.asarray(live_disk_bundle[index], dtype=float) for index in (3, 4, 5)])
        live_disk_axis = np.asarray(live_disk_source.direction, dtype=float)
        live_disk_axis = live_disk_axis / max(float(np.linalg.norm(live_disk_axis)), 1e-12)
        live_disk_angles = np.rad2deg(np.arccos(np.clip(live_disk_dirs @ live_disk_axis, -1.0, 1.0)))
    checks.append(
        SceneSourceCheck(
            "live UI scene-source bundle honors collimated disk half cone",
            live_disk_bundle is not None
            and len(np.asarray(live_disk_bundle[0])) == 9
            and float(np.max(live_disk_angles)) > 0.25
            and float(np.max(live_disk_angles)) <= 6.0 + 1e-9,
            f"angles_deg={np.round(live_disk_angles, 4).tolist()}",
        )
    )
    editor.source_model_var.set("Collimated disk source")
    editor.source_radius_var.set("2.0")
    editor.source_cone_angle_var.set("6.0")
    editor.source_seed_var.set("7")
    live_panel_bundle = editor._build_random_source_bundle(sample_count=9)
    live_panel_angles = np.asarray([], dtype=float)
    if live_panel_bundle is not None:
        live_panel_dirs = np.column_stack([np.asarray(live_panel_bundle[index], dtype=float) for index in (3, 4, 5)])
        live_panel_angles = np.rad2deg(np.arccos(np.clip(live_panel_dirs[:, 2], -1.0, 1.0)))
    checks.append(
        SceneSourceCheck(
            "live Source panel collimated disk honors nonzero half cone",
            live_panel_bundle is not None
            and len(np.asarray(live_panel_bundle[0])) == 9
            and float(np.max(live_panel_angles)) > 0.25
            and float(np.max(live_panel_angles)) <= 6.0 + 1e-9,
            f"angles_deg={np.round(live_panel_angles, 4).tolist()}",
        )
    )
    finite_cone_settings = {
        **settings,
        "object_mode": "Finite",
        "source_model": "Pupil / field",
        "ray_count": "5",
        "source_cone_angle": "7.0",
        "field_value": "0.0",
        "display_orientation": "Vertical",
    }
    finite_cone_editor = _snapshot_editor(rows, finite_cone_settings)
    finite_cone_bundles, finite_cone_count = finite_cone_editor._build_default_finite_cone_preview_bundles()
    finite_cone_bundle = finite_cone_bundles[0] if finite_cone_bundles else None
    finite_cone_angles = np.asarray([], dtype=float)
    finite_cone_origins = np.empty((0, 3), dtype=float)
    if finite_cone_bundle is not None:
        finite_cone_dirs = np.column_stack([np.asarray(finite_cone_bundle[index], dtype=float) for index in (3, 4, 5)])
        finite_cone_angles = np.rad2deg(np.arctan2(finite_cone_dirs[:, 1], finite_cone_dirs[:, 2]))
        finite_cone_origins = np.column_stack(
            [np.asarray(finite_cone_bundle[index], dtype=float) for index in (0, 1, 2)]
        )
    checks.append(
        SceneSourceCheck(
            "default finite pupil/field source launches a cone from object center",
            finite_cone_bundle is not None
            and finite_cone_count == 5
            and finite_cone_origins.shape == (5, 3)
            and np.allclose(finite_cone_origins, 0.0, atol=1e-12)
            and np.allclose([finite_cone_angles[0], finite_cone_angles[-1]], [-7.0, 7.0], atol=1e-9),
            f"origins={np.round(finite_cone_origins, 6).tolist()}, angles_deg={np.round(finite_cone_angles, 4).tolist()}",
        )
    )
    finite_world_cone_bundles, finite_world_cone_count = finite_cone_editor._build_default_finite_cone_world_bundles()
    finite_world_cone_bundle = finite_world_cone_bundles[0] if finite_world_cone_bundles else None
    finite_world_cone_origins = np.empty((0, 3), dtype=float)
    finite_world_cone_angles = np.asarray([], dtype=float)
    finite_world_cone_lm_span = np.asarray((0.0, 0.0), dtype=float)
    if finite_world_cone_bundle is not None:
        finite_world_cone_origins = np.column_stack(
            [np.asarray(finite_world_cone_bundle[index], dtype=float) for index in (0, 1, 2)]
        )
        finite_world_cone_dirs = np.column_stack(
            [np.asarray(finite_world_cone_bundle[index], dtype=float) for index in (3, 4, 5)]
        )
        finite_world_cone_norms = np.linalg.norm(finite_world_cone_dirs, axis=1)
        finite_world_cone_norms = np.where(finite_world_cone_norms > 1e-12, finite_world_cone_norms, 1.0)
        finite_world_cone_angles = np.rad2deg(
            np.arccos(np.clip(finite_world_cone_dirs[:, 2] / finite_world_cone_norms, -1.0, 1.0))
        )
        finite_world_cone_lm_span = np.ptp(finite_world_cone_dirs[:, :2], axis=0)
    checks.append(
        SceneSourceCheck(
            "Open 3D finite pupil/field source samples an azimuthal cone",
            finite_world_cone_bundle is not None
            and finite_world_cone_count == 5
            and finite_world_cone_origins.shape == (5, 3)
            and np.allclose(finite_world_cone_origins, 0.0, atol=1e-12)
            and np.allclose(finite_world_cone_angles[1:], 7.0, atol=1e-9)
            and np.all(finite_world_cone_lm_span > 0.0),
            (
                f"origins={np.round(finite_world_cone_origins, 6).tolist()}, "
                f"angles_deg={np.round(finite_world_cone_angles, 4).tolist()}, "
                f"lm_span={np.round(finite_world_cone_lm_span, 6).tolist()}"
            ),
        )
    )
    finite_cone_var = finite_cone_editor.__dict__.get("source_cone_angle_var")
    try:
        finite_cone_value = str(finite_cone_var.get()) if finite_cone_var is not None else ""
    except Exception:
        finite_cone_value = ""
    checks.append(
        SceneSourceCheck(
            "default finite pupil/field source keeps cone state for manager",
            finite_cone_value not in {"", "NA"},
            f"cone_half_angle={finite_cone_value}",
        )
    )
    finite_cone_panel_spec = finite_cone_editor._scene_source_spec_from_current_panel()
    checks.append(
        SceneSourceCheck(
            "Scene Source Manager seed spec preserves Pupil/field cone",
            str(finite_cone_panel_spec.get("model", "")) == SOURCE_MODEL_DEFAULT
            and not bool(finite_cone_panel_spec.get("physical", True))
            and float(finite_cone_panel_spec.get("cone_deg", 0.0) or 0.0) == 7.0,
            (
                f"model={finite_cone_panel_spec.get('model')}, "
                f"physical={finite_cone_panel_spec.get('physical')}, "
                f"cone={finite_cone_panel_spec.get('cone_deg')}"
            ),
        )
    )
    finite_cone_editor._set_scene_source_specs(
        [
            {
                **finite_cone_panel_spec,
                "cone_deg": 11.0,
                "radius": 3.0,
                "ray_count": 9,
                "physical": False,
                "role": "pupil_field_reference",
            }
        ]
    )
    checks.append(
        SceneSourceCheck(
            "Pupil/field Scene Source Manager apply syncs left Source panel cone",
            str(finite_cone_editor.source_model_var.get()) == SOURCE_MODEL_DEFAULT
            and float(finite_cone_editor.source_cone_angle_var.get()) == 11.0
            and float(finite_cone_editor.source_radius_var.get()) == 3.0
            and int(float(finite_cone_editor.ray_count_var.get())) == 9,
            (
                f"model={finite_cone_editor.source_model_var.get()}, "
                f"cone={finite_cone_editor.source_cone_angle_var.get()}, "
                f"radius={finite_cone_editor.source_radius_var.get()}, "
                f"rays={finite_cone_editor.ray_count_var.get()}"
            ),
        )
    )
    saved_finite_cone_bundle = _default_finite_cone_bundle_from_settings(finite_cone_settings)
    saved_finite_cone_angles = np.asarray([], dtype=float)
    if saved_finite_cone_bundle is not None:
        saved_finite_cone_dirs = np.column_stack(
            [np.asarray(saved_finite_cone_bundle[index], dtype=float) for index in (3, 4, 5)]
        )
        saved_finite_cone_angles = np.rad2deg(np.arctan2(saved_finite_cone_dirs[:, 1], saved_finite_cone_dirs[:, 2]))
    checks.append(
        SceneSourceCheck(
            "saved layout default finite pupil/field source preserves cone half angle",
            saved_finite_cone_bundle is not None
            and len(np.asarray(saved_finite_cone_bundle[0])) == 5
            and np.allclose([saved_finite_cone_angles[0], saved_finite_cone_angles[-1]], [-7.0, 7.0], atol=1e-9),
            f"angles_deg={np.round(saved_finite_cone_angles, 4).tolist()}",
        )
    )
    legacy_nonphysical_settings = {
        **settings,
        "source_model": "Pupil / field",
        "scene_sources": [
            {
                "source_id": "source:0",
                "name": "Legacy cone source",
                "enabled": True,
                "physical": False,
                "role": "pupil_field_reference",
                "model": "Pupil / field",
                "ray_count": 7,
                "radius": 1.0,
                "cone_deg": 9.0,
                "seed": 3,
            }
        ],
    }
    legacy_sources = scene_sources_from_settings(legacy_nonphysical_settings, wavelength=0.532)
    checks.append(
        SceneSourceCheck(
            "legacy nonphysical manager source falls back to ideal pupil/field launch",
            legacy_sources == [],
            f"sources={[(source.model, source.physical) for source in legacy_sources]}",
        )
    )
    override_settings = {
        **legacy_nonphysical_settings,
        "source_model": "Collimated disk source",
        "source_cone_angle": "4.0",
    }
    override_sources = scene_sources_from_settings(override_settings, wavelength=0.532)
    override_source = override_sources[0] if override_sources else None
    override_bundle = build_scene_source_bundle(override_source) if override_source is not None else None
    override_angles = np.asarray([], dtype=float)
    if override_bundle is not None:
        override_dirs = np.column_stack([np.asarray(override_bundle[index], dtype=float) for index in (3, 4, 5)])
        override_angles = np.rad2deg(np.arccos(np.clip(override_dirs[:, 2], -1.0, 1.0)))
    checks.append(
        SceneSourceCheck(
            "physical Source panel overrides nonphysical manager source",
            override_source is not None
            and bool(override_source.physical)
            and override_source.model == "Collimated disk source"
            and float(override_source.settings.get("cone_deg", 0.0) or 0.0) == 4.0
            and override_bundle is not None
            and float(np.max(override_angles)) <= 4.0 + 1e-9,
            (
                f"model={getattr(override_source, 'model', None)} "
                f"cone={getattr(override_source, 'settings', {}).get('cone_deg') if override_source is not None else None} "
                f"angles_deg={np.round(override_angles, 4).tolist()}"
            ),
        )
    )
    editor.layout_scene_source_specs = legacy_nonphysical_settings["scene_sources"]
    editor.source_model_var.set("Pupil / field")
    editor.source_radius_var.set("1.0")
    editor.source_cone_angle_var.set("4.0")
    editor.source_seed_var.set("3")
    ui_override_sources = editor._collect_scene_sources(wavelength=0.532)
    checks.append(
        SceneSourceCheck(
            "UI trace ignores nonphysical manager source in pupil/field mode",
            ui_override_sources
            and ui_override_sources[0].model == "Pupil / field"
            and not bool(ui_override_sources[0].physical),
            f"sources={[(source.model, source.physical) for source in ui_override_sources]}",
        )
    )
    editor.layout_scene_source_specs = []
    saved_system = _build_system_from_specs(_row_specs(rows))
    saved_rays = build_saved_layout_rays(saved_system, _row_specs(rows), cone_settings, Kos)
    checks.append(
        SceneSourceCheck(
            "saved layout ray builder honors source ray count",
            len(getattr(saved_rays, "SURFACE", [])) == 11,
            f"records={len(getattr(saved_rays, 'SURFACE', []))}",
        )
    )
    checks.append(
        SceneSourceCheck(
            "saved trace intent treats physical sources as non-sequential scene requests",
            layout_uses_nonseq(_row_specs(rows), {"source_model": "Collimated disk source", "trace_mode": "Auto"}),
            "physical source exported from SETTINGS should choose NsTraceLoop in Auto",
        )
    )
    checks.append(
        SceneSourceCheck(
            "saved trace intent treats off-axis rows as non-sequential scene requests",
            layout_uses_nonseq(
                _row_specs(
                    [
                        rows[0],
                        SurfaceRow(label="1", surface="Standard", name="Tilted", thickness=10.0, diameter=20.0, tilt_x=5.0, glass="AIR"),
                        rows[1],
                    ]
                ),
                {"source_model": SOURCE_MODEL_DEFAULT, "trace_mode": "Auto"},
            ),
            "tilt/decenter scene geometry should choose NsTraceLoop in Auto",
        )
    )
    checks.append(
        SceneSourceCheck(
            "saved trace intent treats object target rows as non-sequential scene requests",
            layout_uses_nonseq(
                _row_specs(
                    [
                        rows[0],
                        SurfaceRow(label="1", surface="Object Target", name="Target", thickness=10.0, diameter=20.0, glass="MIRROR"),
                        rows[1],
                    ]
                ),
                {"source_model": SOURCE_MODEL_DEFAULT, "trace_mode": "Auto"},
            ),
            "object target workflow should choose NsTraceLoop in Auto",
        )
    )
    app = KrakenLayoutEditor.__new__(KrakenLayoutEditor)
    app.rows = [
        SurfaceRow(label="0", surface="Object", name="Object", thickness=10.0, diameter=20.0, glass="AIR"),
        SurfaceRow(label="1", surface="Object Target", name="Target", thickness=0.0, diameter=20.0, glass="MIRROR"),
    ]
    app._serializable_row_specs = lambda: _row_specs(app.rows)
    app._resolved_trace_mode = lambda system=None: {
        "use_nonseq": True,
        "active": "Non-Sequential Preview",
        "reasons": ("object target",),
    }
    app._apply_nonseq_trace_settings = lambda system: (lambda: None)
    app._source_metadata_for_bundle = lambda bundle, wavelength, source=None: []

    class FakeRays:
        def __init__(self) -> None:
            self.clean_count = 0

        def clean(self) -> None:
            self.clean_count += 1

    fake_bundle = tuple(np.asarray([value], dtype=float) for value in (0.0, 0.0, 0.0, 0.0, 0.0, 1.0))
    fake_rays = FakeRays()
    trace_loop_calls: list[str] = []
    original_ns_trace_loop = layout_editor_module.Kos.NsTraceLoop
    original_trace_loop = layout_editor_module.Kos.TraceLoop

    def failing_ns_trace_loop(*_args, **_kwargs):
        raise RuntimeError("synthetic NsTraceLoop failure")

    def forbidden_trace_loop(*_args, **_kwargs):
        trace_loop_calls.append("TraceLoop")

    try:
        layout_editor_module.Kos.NsTraceLoop = failing_ns_trace_loop
        layout_editor_module.Kos.TraceLoop = forbidden_trace_loop
        raised = False
        try:
            KrakenLayoutEditor._trace_preview_bundles(app, object(), fake_rays, 0.532, [fake_bundle])
        except NonSequentialTracePreviewError:
            raised = True
    finally:
        layout_editor_module.Kos.NsTraceLoop = original_ns_trace_loop
        layout_editor_module.Kos.TraceLoop = original_trace_loop
    checks.append(
        SceneSourceCheck(
            "non-sequential preview failure does not fall back to sequential TraceLoop",
            raised and not trace_loop_calls and getattr(fake_rays, "clean_count", 0) >= 1,
            f"raised={raised}, trace_loop_calls={trace_loop_calls}, clean_count={getattr(fake_rays, 'clean_count', 0)}",
        )
    )
    return checks


def _print_table(checks: list[SceneSourceCheck]) -> None:
    print("KrakenOS scene-source validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate first-class scene source plumbing.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_scene_sources()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
