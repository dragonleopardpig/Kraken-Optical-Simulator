from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

import KrakenOS as Kos
from KrakenOS.common_optical_layouts.right_angle_beam_splitter_illumination import SETTINGS, SURFACES, TITLE
from KrakenOS.UI.layout_editor import _build_system_from_specs
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
from KrakenOS.UI.scene_builder import build_scene_bundle


@dataclass
class SourceObjectSplitCheck:
    check: str
    ok: bool
    detail: str


def _last_text(rays, name: str, index: int, default: str = "") -> str:
    try:
        return str(np.asarray(getattr(rays, name)[index], dtype=object).reshape(-1)[-1])
    except Exception:
        return default


def _last_float(rays, name: str, index: int, default: float = 0.0) -> float:
    try:
        return float(np.asarray(getattr(rays, name)[index], dtype=float).reshape(-1)[-1])
    except Exception:
        return float(default)


def _row_z_positions(rows: list) -> list[float]:
    z_pos = 0.0
    positions: list[float] = []
    for row in rows:
        positions.append(float(z_pos))
        z_pos += float(getattr(row, "thickness", 0.0))
    return positions


def validate_source_object_split() -> list[SourceObjectSplitCheck]:
    rows = _rows_from_layout_info({"surfaces": SURFACES, "settings": SETTINGS})
    editor = _snapshot_editor(rows, SETTINGS)
    sources = editor._collect_scene_sources()
    source = sources[0] if sources else None
    wavelength = float(SETTINGS["wavelength"])

    system = _build_system_from_specs(SURFACES)
    source_bundle = editor._build_random_source_bundle(sample_count=int(SETTINGS["ray_count"]))
    source_metadata = editor._source_metadata_for_bundle(source_bundle, wavelength)
    rays = Kos.raykeeper(system)
    Kos.NsTraceLoop(*source_bundle, wavelength, rays, clean=1, source_metadata=source_metadata)
    bundle = build_scene_bundle(
        rows=rows,
        system=system,
        rays=rays,
        sources=sources,
        field_count=1,
        ray_count_per_field=int(SETTINGS["ray_count"]),
        source_row_order=str(SETTINGS.get("scene_row_order", "after_object")),
    )

    source_direction = np.asarray(source.direction if source is not None else (np.nan, np.nan, np.nan), dtype=float)
    object_axis = np.asarray((0.0, 0.0, 1.0), dtype=float)
    object_surface = 3
    camera_surface = len(rows) - 1
    z_positions = _row_z_positions(rows)
    splitter_z = float(z_positions[1]) if len(z_positions) > 1 else float("nan")
    object_z = float(z_positions[object_surface]) if object_surface < len(z_positions) else float("nan")
    camera_z = float(z_positions[camera_surface]) if camera_surface < len(z_positions) else float("nan")
    first_reflect_hits_object = []
    camera_hits = []
    side_transmitted_camera_hits = []
    rejected_return_hits = []
    source_marker_count = sum(1 for curve in bundle.surface_curves if getattr(curve, "kind", "") == "source")
    source_label_present = any(str(getattr(label, "text", "")) == "Source 1" for label in bundle.labels)
    for ray_index, surfaces in enumerate(getattr(rays, "SURFACE", [])):
        surface_ids = np.asarray(surfaces, dtype=int).ravel()
        branch_path = _last_text(rays, "BRANCH_PATH", ray_index)
        reaches_camera = bool(surface_ids.size and int(surface_ids[-1]) == camera_surface)
        hits_object = bool(object_surface in surface_ids.tolist())
        if branch_path.endswith("/reflect"):
            first_reflect_hits_object.append(hits_object)
        if "reflect ->" in branch_path and branch_path.endswith("/transmit"):
            camera_hits.append(reaches_camera)
        if branch_path.endswith("/transmit") and "->" not in branch_path:
            side_transmitted_camera_hits.append(reaches_camera)
        if "reflect ->" in branch_path and branch_path.endswith("/reflect"):
            rejected_return_hits.append(reaches_camera)

    camera_power = sum(
        _last_float(rays, "BRANCH_POWER", index)
        for index, branch_path in enumerate(getattr(rays, "BRANCH_PATH", []))
        if "reflect ->" in str(np.asarray(branch_path, dtype=object).reshape(-1)[-1])
        and str(np.asarray(branch_path, dtype=object).reshape(-1)[-1]).endswith("/transmit")
    )
    rejected_side_power = sum(
        _last_float(rays, "BRANCH_POWER", index)
        for index, branch_path in enumerate(getattr(rays, "BRANCH_PATH", []))
        if str(np.asarray(branch_path, dtype=object).reshape(-1)[-1]).endswith("/transmit")
        and "->" not in str(np.asarray(branch_path, dtype=object).reshape(-1)[-1])
    )
    rejected_return_power = sum(
        _last_float(rays, "BRANCH_POWER", index)
        for index, branch_path in enumerate(getattr(rays, "BRANCH_PATH", []))
        if "reflect ->" in str(np.asarray(branch_path, dtype=object).reshape(-1)[-1])
        and str(np.asarray(branch_path, dtype=object).reshape(-1)[-1]).endswith("/reflect")
    )

    checks = [
        SourceObjectSplitCheck(
            "layout is the right-angle source/object split preset",
            TITLE == "Right-Angle Beam-Splitter Illumination",
            TITLE,
        ),
        SourceObjectSplitCheck(
            "source is physical illumination, not the Object row",
            bool(source and source.role == "illumination" and source.physical),
            f"role={getattr(source, 'role', '')} physical={getattr(source, 'physical', None)}",
        ),
        SourceObjectSplitCheck(
            "source direction is 90 degrees to object axis",
            bool(np.isfinite(source_direction).all() and abs(float(np.dot(source_direction, object_axis))) < 1e-9),
            f"source_direction={source_direction.tolist()} object_axis={object_axis.tolist()}",
        ),
        SourceObjectSplitCheck(
            "first reflected splitter branch reaches specular object proxy",
            bool(first_reflect_hits_object and all(first_reflect_hits_object)),
            f"object_hits={sum(first_reflect_hits_object)}/{len(first_reflect_hits_object)} object=S{object_surface}",
        ),
        SourceObjectSplitCheck(
            "object is on the left side and camera is on the transmitted right side",
            bool(np.isfinite([object_z, splitter_z, camera_z]).all() and object_z < splitter_z < camera_z),
            f"object_z={object_z:.6g} splitter_z={splitter_z:.6g} camera_z={camera_z:.6g}",
        ),
        SourceObjectSplitCheck(
            "object-return transmitted branch reaches camera sensor",
            bool(camera_hits and all(camera_hits)),
            f"camera_hits={sum(camera_hits)}/{len(camera_hits)} camera=S{camera_surface}",
        ),
        SourceObjectSplitCheck(
            "side transmitted illumination branch remains separate from camera path",
            bool(side_transmitted_camera_hits and not any(side_transmitted_camera_hits)),
            f"side_camera_hits={sum(side_transmitted_camera_hits)}/{len(side_transmitted_camera_hits)}",
        ),
        SourceObjectSplitCheck(
            "object-return reflected branch is rejected from camera path",
            bool(rejected_return_hits and not any(rejected_return_hits)),
            f"rejected_camera_hits={sum(rejected_return_hits)}/{len(rejected_return_hits)}",
        ),
        SourceObjectSplitCheck(
            "SceneBundle preserves source and traced ray source identity",
            bool(bundle.sources and bundle.sources[0].source_id == "source:0" and all(path.source_id == "source:0" for path in bundle.ray_paths)),
            f"sources={len(bundle.sources)} paths={len(bundle.ray_paths)}",
        ),
        SourceObjectSplitCheck(
            "future scene row order can put Source before Object",
            bool(
                bundle.scene_row_mapping is not None
                and bundle.scene_row_mapping.source_row_order == "before_object"
                and bundle.scene_row_mapping.source_id_to_scene == {"source:0": 0}
                and bundle.scene_row_mapping.trace_surface_to_scene.get(0) == 1
            ),
            bundle.scene_row_mapping.to_jsonable() if bundle.scene_row_mapping is not None else "missing mapping",
        ),
        SourceObjectSplitCheck(
            "SceneBundle exposes the physical source marker for 2-D display",
            bool(source_marker_count >= 1 and source_label_present),
            f"source_curves={source_marker_count} source_label={source_label_present}",
        ),
        SourceObjectSplitCheck(
            "camera path carries positive bounded object-return power",
            bool(
                camera_power > 0.0
                and rejected_return_power > 0.0
                and camera_power + rejected_return_power <= rejected_side_power + max(rejected_side_power, 1.0) * 1e-9
            ),
            f"camera={camera_power:.6g} return_reject={rejected_return_power:.6g} first_side={rejected_side_power:.6g}",
        ),
    ]
    return checks


def _print_table(checks: list[SourceObjectSplitCheck]) -> None:
    print("KrakenOS source/object split validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the right-angle illumination source/object split example.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_source_object_split()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
