"""Validate physics-derived exit placement for chained CAD/STL solids."""

from __future__ import annotations

import copy
import importlib.util
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import _build_system_from_specs
from KrakenOS.UI.nonseq_output_ports import (
    build_optical_solid_output_port_pose_overrides,
)
from KrakenOS.UI.optical_solid_metadata import OPTICAL_SOLID_FACES_ADVANCED_ATTR, normalize_optical_solid_face_metadata


@dataclass
class PhysicsExitPoseCheck:
    check: str
    ok: bool
    detail: str


def _load_dove_module():
    repo_root = Path(__file__).resolve().parents[2]
    layout_path = repo_root / "attachment" / "dove.py"
    spec = importlib.util.spec_from_file_location("kraken_ui_dove_layout", layout_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {layout_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows_without_explicit_output(module) -> list[dict[str, object]]:
    rows = copy.deepcopy(module.SURFACES)
    target = rows[7]
    advanced = dict(target.get("advanced", {}) or {})
    metadata = normalize_optical_solid_face_metadata(advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))
    updated_faces: list[dict[str, object]] = []
    for face in list(metadata.get("faces", []) or []):
        record = dict(face)
        if str(record.get("port_role", "") or "").strip() == "Output Port":
            record["port_role"] = "Auto"
        updated_faces.append(record)
    metadata["faces"] = updated_faces
    advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata
    target["advanced"] = advanced
    return rows


def _runtime_spec(row: dict[str, object]) -> dict[str, object]:
    spec = dict(row)
    spec.setdefault("rc", 0.0)
    spec.setdefault("k", 0.0)
    spec.setdefault("axicon", 0.0)
    spec.setdefault("diff_ord", 0.0)
    spec.setdefault("grating_d", 0.0)
    spec.setdefault("grating_angle", 0.0)
    spec.setdefault("in_diameter", 0.0)
    spec.setdefault("drawing", 1.0)
    spec.setdefault("extra_data", 0.0)
    spec.setdefault("uda", "None")
    spec.setdefault("tilt_x", 0.0)
    spec.setdefault("tilt_y", 0.0)
    spec.setdefault("tilt_z", 0.0)
    spec.setdefault("desp_x", 0.0)
    spec.setdefault("desp_y", 0.0)
    spec.setdefault("desp_z", 0.0)
    spec.setdefault("axis_move", 0.0)
    spec.setdefault("glass", "AIR")
    return spec


def _distance(a, b) -> float:
    return float(np.linalg.norm(np.asarray(a, dtype=float) - np.asarray(b, dtype=float)))


def validate_optical_solid_physics_exit_pose() -> list[PhysicsExitPoseCheck]:
    module = _load_dove_module()
    rows = _rows_without_explicit_output(module)
    static_overrides = build_optical_solid_output_port_pose_overrides(rows)
    system = _build_system_from_specs([_runtime_spec(row) for row in rows])
    runtime_overrides = getattr(system, "_optical_solid_output_port_pose_overrides", {}) or {}
    fresh_overrides = build_optical_solid_output_port_pose_overrides(rows, system=system)
    image_pose = dict(runtime_overrides.get(8, {}) or {})
    fresh_image_pose = dict(fresh_overrides.get(8, {}) or {})
    static_image_pose = dict(static_overrides.get(8, {}) or {})
    runtime_center = np.asarray(image_pose.get("center", (np.nan, np.nan, np.nan)), dtype=float)
    runtime_normal = np.asarray(image_pose.get("normal", (np.nan, np.nan, np.nan)), dtype=float)
    fresh_center = np.asarray(fresh_image_pose.get("center", (np.nan, np.nan, np.nan)), dtype=float)
    fresh_normal = np.asarray(fresh_image_pose.get("normal", (np.nan, np.nan, np.nan)), dtype=float)
    static_center = np.asarray(static_image_pose.get("center", (np.nan, np.nan, np.nan)), dtype=float)
    return [
        PhysicsExitPoseCheck(
            "dove image follower uses traced exit when no explicit output port is authored",
            str(image_pose.get("frame_source", "") or "").strip() == "physics_exit_trace",
            f"frame_source={image_pose.get('frame_source')!r}",
        ),
        PhysicsExitPoseCheck(
            "stored runtime image pose matches a fresh settled recomputation",
            bool(
                np.allclose(runtime_center, fresh_center, atol=1e-6)
                and np.allclose(runtime_normal, fresh_normal, atol=1e-6)
            ),
            (
                f"runtime_center={runtime_center.tolist()}, fresh_center={fresh_center.tolist()}, "
                f"runtime_normal={runtime_normal.tolist()}, fresh_normal={fresh_normal.tolist()}"
            ),
        ),
        PhysicsExitPoseCheck(
            "runtime image pose diverges from the old static inferred-output fallback",
            _distance(runtime_center, static_center) > 1.0,
            (
                f"runtime_center={runtime_center.tolist()}, static_center={static_center.tolist()}, "
                f"distance_mm={_distance(runtime_center, static_center):.6g}"
            ),
        ),
    ]


def _print_table(checks: list[PhysicsExitPoseCheck]) -> None:
    print("KrakenOS optical-solid physics-exit placement validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    checks = validate_optical_solid_physics_exit_pose()
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
