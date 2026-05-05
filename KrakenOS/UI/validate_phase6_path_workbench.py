from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import (
    BEAM_SPLITTER_SURFACE,
    ELEMENT_ADVANCED_ATTR,
    LAYOUTS_DIR,
    PATH_COMPONENT_APERTURE,
    PATH_COMPONENT_DETECTOR,
    PATH_COMPONENT_MIRROR,
    PATH_COMPONENT_REFRACTIVE_SURFACE,
    PATH_COMPONENT_THIN_LENS,
    KrakenLayoutEditor,
    _load_python_data,
    _load_python_title,
)
from KrakenOS.UI.render_layout_snapshot import _build_runtime_system, _rows_from_layout_info, _snapshot_editor


DEFAULT_LAYOUT_TITLE = "Beam Splitter 50/50 Example"
NESTED_PATH_LAYOUT_TITLE = "Michelson Interferometer (Interferogram)"


@dataclass
class PathWorkbenchCheck:
    layout: str
    component: str
    path: str
    ok: bool
    detail: str


def _layout_path_by_title(title: str) -> Path:
    for path in sorted(LAYOUTS_DIR.glob("*.py")):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        try:
            if str(_load_python_title(path)).strip() == title:
                return path
        except Exception:
            continue
    raise ValueError(f"Common layout not found: {title}")


def _load_editor(title: str) -> KrakenLayoutEditor:
    path = _layout_path_by_title(title)
    info = _load_python_data(path)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(_rows_from_layout_info(info), settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()
    return editor


def _load_traced_editor(title: str) -> KrakenLayoutEditor:
    path = _layout_path_by_title(title)
    info = _load_python_data(path)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(_rows_from_layout_info(info), settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()
    system = _build_runtime_system(path, editor.rows)
    wavelength = editor._current_wavelength()
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in editor.rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    editor.last_system = system
    editor.last_rays = rays
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    editor._last_scene_bundle = editor._build_scene_bundle(system, rays, max_radius)
    return editor


def _finite_pose(row) -> bool:
    values = (
        row.tilt_x,
        row.tilt_y,
        row.tilt_z,
        row.desp_x,
        row.desp_y,
        row.desp_z,
        row.diameter,
    )
    return all(np.isfinite(float(value)) for value in values)


def _validate_component(editor: KrakenLayoutEditor, splitter_index: int, kind: str, role: str) -> PathWorkbenchCheck:
    parameter = {
        PATH_COMPONENT_THIN_LENS: 125.0,
        PATH_COMPONENT_REFRACTIVE_SURFACE: 80.0,
        PATH_COMPONENT_MIRROR: 0.0,
    }.get(kind)
    row = editor._path_component_row_for_arm(
        splitter_index,
        role,
        kind,
        40.0,
        12.0,
        parameter_mm=parameter,
        glass="BK7",
    )
    metadata = row.advanced.get(ELEMENT_ADVANCED_ATTR, {}) if isinstance(row.advanced, dict) else {}
    expected_surface = {
        PATH_COMPONENT_DETECTOR: "Standard",
        PATH_COMPONENT_APERTURE: "Aperture",
        PATH_COMPONENT_THIN_LENS: "Thin Lens",
        PATH_COMPONENT_REFRACTIVE_SURFACE: "Standard",
        PATH_COMPONENT_MIRROR: "Mirror",
    }[kind]
    expected_role = "Detector" if kind == PATH_COMPONENT_DETECTOR else role
    checks = [
        row.surface == expected_surface,
        _finite_pose(row),
        str(metadata.get("arm_role", "")) == expected_role,
        str(metadata.get("branch_selector", "")) == role.lower(),
        str(metadata.get("path_component_type", "")) == kind,
        abs(float(metadata.get("arm_distance", 0.0)) - 40.0) < 1e-9,
    ]
    if kind == PATH_COMPONENT_THIN_LENS:
        checks.append(abs(float(row.rc) - 125.0) < 1e-9)
    if kind == PATH_COMPONENT_REFRACTIVE_SURFACE:
        checks.append(str(row.glass).strip() == "BK7")
    if kind == PATH_COMPONENT_MIRROR:
        checks.append(str(row.glass).strip().upper() == "MIRROR")
    ok = all(checks)
    detail = (
        f"surface={row.surface}, rc={float(row.rc):.6g}, glass={row.glass}, "
        f"tilt=({float(row.tilt_x):.6g},{float(row.tilt_y):.6g},{float(row.tilt_z):.6g}), "
        f"decenter=({float(row.desp_x):.6g},{float(row.desp_y):.6g},{float(row.desp_z):.6g}), "
        f"metadata_role={metadata.get('arm_role')}, selector={metadata.get('branch_selector')}"
    )
    return PathWorkbenchCheck(DEFAULT_LAYOUT_TITLE, kind, role, ok, detail)


def validate_path_workbench(layout: str = DEFAULT_LAYOUT_TITLE) -> list[PathWorkbenchCheck]:
    editor = _load_editor(layout)
    splitter_indices = [index for index, row in enumerate(editor.rows) if row.surface == BEAM_SPLITTER_SURFACE]
    if not splitter_indices:
        return [PathWorkbenchCheck(layout, "-", "-", False, "No Beam Splitter row found")]
    splitter_index = splitter_indices[0]
    checks = [
        _validate_component(editor, splitter_index, PATH_COMPONENT_DETECTOR, "Transmit"),
        _validate_component(editor, splitter_index, PATH_COMPONENT_APERTURE, "Reflect"),
        _validate_component(editor, splitter_index, PATH_COMPONENT_THIN_LENS, "Transmit"),
        _validate_component(editor, splitter_index, PATH_COMPONENT_REFRACTIVE_SURFACE, "Transmit"),
        _validate_component(editor, splitter_index, PATH_COMPONENT_MIRROR, "Reflect"),
    ]
    detector = editor._detector_row_for_arm(splitter_index, "Transmit", 25.0, 8.0)
    metadata = detector.advanced.get(ELEMENT_ADVANCED_ATTR, {}) if isinstance(detector.advanced, dict) else {}
    checks.append(
        PathWorkbenchCheck(
            layout,
            "Detector compatibility wrapper",
            "Transmit",
            detector.surface == "Standard"
            and str(metadata.get("arm_role", "")) == "Detector"
            and str(metadata.get("branch_selector", "")) == "transmit"
            and _finite_pose(detector),
            f"surface={detector.surface}, selector={metadata.get('branch_selector')}, role={metadata.get('arm_role')}",
        )
    )
    try:
        traced_editor = _load_traced_editor(NESTED_PATH_LAYOUT_TITLE)
        traced_paths = [
            path
            for path in traced_editor._traced_branch_paths()
            if traced_editor._branch_path_depth(path) >= 2
        ]
        if not traced_paths:
            checks.append(
                PathWorkbenchCheck(
                    NESTED_PATH_LAYOUT_TITLE,
                    "Traced BRANCH_PATH detector",
                    "-",
                    False,
                    "No depth>=2 traced BRANCH_PATH found",
                )
            )
        else:
            branch_path = traced_paths[0]
            branch_detector = traced_editor._path_component_row_for_branch_path(
                branch_path,
                PATH_COMPONENT_DETECTOR,
                20.0,
                8.0,
            )
            branch_metadata = (
                branch_detector.advanced.get(ELEMENT_ADVANCED_ATTR, {})
                if isinstance(branch_detector.advanced, dict)
                else {}
            )
            checks.append(
                PathWorkbenchCheck(
                    NESTED_PATH_LAYOUT_TITLE,
                    "Traced BRANCH_PATH detector",
                    traced_editor._branch_path_compact_detail(branch_path),
                    branch_detector.surface == "Standard"
                    and _finite_pose(branch_detector)
                    and str(branch_metadata.get("branch_path", "")) == branch_path
                    and str(branch_metadata.get("path_frame_source", "")) == "traced_branch_path"
                    and int(branch_metadata.get("path_frame_samples", 0)) > 0,
                    (
                        f"branch_path={branch_path}, "
                        f"tilt=({float(branch_detector.tilt_x):.6g},{float(branch_detector.tilt_y):.6g},{float(branch_detector.tilt_z):.6g}), "
                        f"decenter=({float(branch_detector.desp_x):.6g},{float(branch_detector.desp_y):.6g},{float(branch_detector.desp_z):.6g}), "
                        f"samples={branch_metadata.get('path_frame_samples')}"
                    ),
                )
            )
    except Exception as exc:
        checks.append(
            PathWorkbenchCheck(
                NESTED_PATH_LAYOUT_TITLE,
                "Traced BRANCH_PATH detector",
                "-",
                False,
                str(exc),
            )
        )
    return checks


def _print_table(checks: list[PathWorkbenchCheck]) -> None:
    print("KrakenOS Phase 6 path-workbench validation")
    print("layout | component | path | status | detail")
    print("--- | --- | --- | --- | ---")
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{check.layout} | {check.component} | {check.path} | {status} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 6 beam-splitter path-local component placement.")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT_TITLE, help="Common layout title to validate.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_path_workbench(args.layout)
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
