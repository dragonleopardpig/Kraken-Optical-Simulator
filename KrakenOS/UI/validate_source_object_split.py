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
    )

    source_direction = np.asarray(source.direction if source is not None else (np.nan, np.nan, np.nan), dtype=float)
    object_axis = np.asarray((0.0, 0.0, 1.0), dtype=float)
    target_surface = len(rows) - 1
    reflected_hits = []
    transmitted_hits = []
    for ray_index, surfaces in enumerate(getattr(rays, "SURFACE", [])):
        surface_ids = np.asarray(surfaces, dtype=int).ravel()
        branch_path = _last_text(rays, "BRANCH_PATH", ray_index)
        reaches_target = bool(surface_ids.size and int(surface_ids[-1]) == target_surface)
        if "/reflect" in branch_path:
            reflected_hits.append(reaches_target)
        if "/transmit" in branch_path:
            transmitted_hits.append(reaches_target)

    reflected_power = sum(
        _last_float(rays, "BRANCH_POWER", index)
        for index, branch_path in enumerate(getattr(rays, "BRANCH_PATH", []))
        if "/reflect" in str(np.asarray(branch_path, dtype=object).reshape(-1)[-1])
    )
    transmitted_power = sum(
        _last_float(rays, "BRANCH_POWER", index)
        for index, branch_path in enumerate(getattr(rays, "BRANCH_PATH", []))
        if "/transmit" in str(np.asarray(branch_path, dtype=object).reshape(-1)[-1])
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
            "reflected splitter branch reaches illuminated object plane",
            bool(reflected_hits and all(reflected_hits)),
            f"reflected_hits={sum(reflected_hits)}/{len(reflected_hits)} target=S{target_surface}",
        ),
        SourceObjectSplitCheck(
            "side transmitted branch remains separate from object plane",
            bool(transmitted_hits and not any(transmitted_hits)),
            f"transmitted_hits={sum(transmitted_hits)}/{len(transmitted_hits)}",
        ),
        SourceObjectSplitCheck(
            "SceneBundle preserves source and traced ray source identity",
            bool(bundle.sources and bundle.sources[0].source_id == "source:0" and all(path.source_id == "source:0" for path in bundle.ray_paths)),
            f"sources={len(bundle.sources)} paths={len(bundle.ray_paths)}",
        ),
        SourceObjectSplitCheck(
            "split powers remain balanced",
            abs(reflected_power - transmitted_power) <= max(reflected_power, transmitted_power, 1.0) * 1e-9,
            f"reflected={reflected_power:.6g} transmitted={transmitted_power:.6g}",
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
