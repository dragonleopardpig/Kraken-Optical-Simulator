from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import SurfaceRow, _build_system_from_specs
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.scene_builder import build_scene_bundle


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
