"""Diagnose Open 3D CAD hover responsiveness without launching Tk.

The diagnostic is intentionally safe for headless CI. It measures the mesh
cache path that feeds large STEP-derived STL actors and reports the static
interaction contract that keeps ordinary passive mouse motion away from dense
CAD body picking. Explicit click/right-click workflows remain responsible for
full face picking.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from KrakenOS.UI.services.cad_scene_cache import CadSceneCache
from KrakenOS.UI.services.optical_solid_geometry import _read_stl_triangle_vertices


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "krakenos" / "cad"
PASSIVE_HOVER_TARGET_P95_MS = 16.0
EXPLICIT_FACE_PICK_TARGET_P95_MS = 50.0


def _default_stl_candidates() -> list[Path]:
    patterns = (
        "3D_CAD_HR25xCXP_*.stl",
        "3D_CAD_shr*.stl",
        "15056_*.stl",
    )
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(sorted(DEFAULT_CACHE_DIR.glob(pattern)))
    return paths


def _source_contract() -> dict[str, object]:
    interaction = (PROJECT_ROOT / "KrakenOS/UI/services/open3d_interaction.py").read_text(encoding="utf-8")
    inspector = (PROJECT_ROOT / "KrakenOS/UI/open3d_inspector.py").read_text(encoding="utf-8")
    try:
        passive_start = interaction.index("if target_label is None and not axis_pick_any:")
        passive_end = interaction.index("if self._picker is None or self._renderer is None", passive_start)
        passive_source = interaction[passive_start:passive_end]
    except ValueError:
        passive_source = ""
    try:
        right_click_start = inspector.index("def _right_click_pick_context")
        right_click_end = inspector.index("def _ray_event_mesh_face_id", right_click_start)
        right_click_source = inspector[right_click_start:right_click_end]
    except ValueError:
        right_click_source = ""
    return {
        "passive_hover_target_p95_ms": PASSIVE_HOVER_TARGET_P95_MS,
        "explicit_face_pick_target_p95_ms": EXPLICIT_FACE_PICK_TARGET_P95_MS,
        "passive_hover_uses_rotation_handle_pick_list": (
            "_passive_hover_pick_rotation_handle" in passive_source
            and "PickFromListOn" in interaction
            and "AddPickList" in interaction
        ),
        "passive_hover_skips_step_body_actor_lookup": "_actor_step_map.get(actor_key)" not in passive_source,
        "passive_hover_skips_row_body_actor_lookup": "_actor_row_map.get(actor_key)" not in passive_source,
        "passive_hover_skips_feature_scan": "_picked_feature_info_cached" not in passive_source,
        "right_click_defers_feature_scan_for_cad_bodies": (
            "if step_label is None and not persistent_file_backed" in right_click_source
        ),
    }


def _stl_cache_diagnostic(path: Path) -> dict[str, object]:
    cache = CadSceneCache(max_documents=4)
    path = Path(path).expanduser()
    first_start = time.perf_counter()
    first = cache.triangle_array(path, _read_stl_triangle_vertices)
    first_ms = (time.perf_counter() - first_start) * 1000.0
    second_start = time.perf_counter()
    second = cache.triangle_array(path, _read_stl_triangle_vertices)
    second_ms = (time.perf_counter() - second_start) * 1000.0
    return {
        "path": str(path),
        "exists": path.exists(),
        "file_format": first.file_format,
        "triangles": int(first.triangles.shape[0]) if first.valid else 0,
        "first_read_ms": round(float(first_ms), 3),
        "cached_read_ms": round(float(second_ms), 6),
        "cache_reused": first is second,
    }


def build_report(stl_paths: list[Path]) -> dict[str, object]:
    selected_paths = [Path(path).expanduser() for path in stl_paths if Path(path).expanduser().exists()]
    if not selected_paths:
        selected_paths = _default_stl_candidates()[:3]
    return {
        "contract": _source_contract(),
        "mesh_cache": [_stl_cache_diagnostic(path) for path in selected_paths],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnose Open 3D CAD hover responsiveness.")
    parser.add_argument("--stl", action="append", default=[], help="STEP-derived STL cache file to measure.")
    args = parser.parse_args(argv)
    report = build_report([Path(value) for value in args.stl])
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
