from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import (
    BEAM_SPLITTER_SURFACE,
    DETECTOR_ADVANCED_ATTR,
    ELEMENT_ADVANCED_ATTR,
    FIELDS,
    LAYOUTS_DIR,
    PATH_COMPONENT_APERTURE,
    PATH_COMPONENT_DETECTOR,
    PATH_COMPONENT_MIRROR,
    PATH_COMPONENT_REFRACTIVE_SURFACE,
    PATH_COMPONENT_STOCK_LENS,
    PATH_COMPONENT_THIN_LENS,
    KrakenLayoutEditor,
    _available_stock_lens_catalogs,
    _load_python_data,
    _load_python_title,
    _load_stock_lens_catalog,
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


class _FakeTableRows:
    def __init__(self, row_values: dict[int, list[str]]) -> None:
        self._row_values = {int(index): tuple(values) for index, values in row_values.items()}

    def get_children(self):
        return tuple(f"row_{index}" for index in sorted(self._row_values))

    def item(self, item, option=None):
        try:
            row_index = int(str(item).split("_", 1)[1])
        except Exception:
            row_index = -1
        values = self._row_values.get(row_index, ())
        if option == "values":
            return values
        return {"values": values}


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
    if kind == PATH_COMPONENT_DETECTOR:
        detector_settings = row.advanced.get(DETECTOR_ADVANCED_ATTR, {}) if isinstance(row.advanced, dict) else {}
        checks.extend(
            [
                abs(float(detector_settings.get("active_width_mm", 0.0)) - 12.0) < 1e-9,
                abs(float(detector_settings.get("active_height_mm", 0.0)) - 12.0) < 1e-9,
            ]
        )
    ok = all(checks)
    detail = (
        f"surface={row.surface}, rc={float(row.rc):.6g}, glass={row.glass}, "
        f"tilt=({float(row.tilt_x):.6g},{float(row.tilt_y):.6g},{float(row.tilt_z):.6g}), "
        f"decenter=({float(row.desp_x):.6g},{float(row.desp_y):.6g},{float(row.desp_z):.6g}), "
        f"metadata_role={metadata.get('arm_role')}, selector={metadata.get('branch_selector')}"
    )
    return PathWorkbenchCheck(DEFAULT_LAYOUT_TITLE, kind, role, ok, detail)


def _validate_detector_model_settings(editor: KrakenLayoutEditor, splitter_index: int) -> PathWorkbenchCheck:
    insert_at = max(1, len(editor.rows) - 1)
    detector = editor._detector_row_for_arm(splitter_index, "Transmit", 25.0, 8.0, insert_at=insert_at)
    editor.rows.insert(insert_at, detector)
    try:
        editor._set_detector_settings(
            editor.rows[insert_at],
            {
                "active_width_mm": 22.0,
                "active_height_mm": 10.0,
                "bins": "32",
                "pixel_pitch_um": 5.5,
            },
        )
        samples = {
            "terminal_surfaces": [insert_at, insert_at],
            "coord": "local",
        }
        model = editor._detector_model_for_samples(samples)
        extent = editor._detector_map_extent(
            samples,
            np.asarray([-1.0, 1.0], dtype=float),
            np.asarray([-0.5, 0.5], dtype=float),
        )
        bins = editor._current_detector_bin_count(2, detector_model=model)
        coherent_bins = editor._current_detector_bin_count(2, coherent=True, detector_model=model)
        settings = editor.rows[insert_at].advanced.get(DETECTOR_ADVANCED_ATTR, {})
        checks = [
            editor._surface_index_is_detector(insert_at),
            extent == (-11.0, 11.0, -5.0, 5.0),
            bins == 32,
            coherent_bins == 32,
            abs(float(model.get("active_width_mm", 0.0)) - 22.0) < 1e-9,
            abs(float(model.get("active_height_mm", 0.0)) - 10.0) < 1e-9,
            abs(float(model.get("pixel_pitch_um", 0.0)) - 5.5) < 1e-9,
            str(settings.get("bins", "")) == "32",
        ]
        detail = f"extent={extent}, bins={bins}, coherent_bins={coherent_bins}, model={model}"
        return PathWorkbenchCheck(DEFAULT_LAYOUT_TITLE, "Detector model settings", "Transmit", all(checks), detail)
    except Exception as exc:
        return PathWorkbenchCheck(DEFAULT_LAYOUT_TITLE, "Detector model settings", "Transmit", False, str(exc))
    finally:
        if 0 <= insert_at < len(editor.rows):
            del editor.rows[insert_at]


def _validate_local_pose_component(editor: KrakenLayoutEditor, splitter_index: int) -> PathWorkbenchCheck:
    row = editor._path_component_row_for_arm(
        splitter_index,
        "Reflect",
        PATH_COMPONENT_APERTURE,
        42.0,
        10.0,
        local_decenter_x=2.5,
        local_decenter_y=-1.25,
        local_tilt_x=4.0,
        local_tilt_y=-2.0,
        local_tilt_z=7.0,
    )
    baseline = editor._path_component_row_for_arm(
        splitter_index,
        "Reflect",
        PATH_COMPONENT_APERTURE,
        42.0,
        10.0,
    )
    metadata = row.advanced.get(ELEMENT_ADVANCED_ATTR, {}) if isinstance(row.advanced, dict) else {}
    decenter_delta = np.asarray(
        [
            float(row.desp_x) - float(baseline.desp_x),
            float(row.desp_y) - float(baseline.desp_y),
            float(row.desp_z) - float(baseline.desp_z),
        ],
        dtype=float,
    )
    tilt_delta = np.asarray(
        [
            float(row.tilt_x) - float(baseline.tilt_x),
            float(row.tilt_y) - float(baseline.tilt_y),
            float(row.tilt_z) - float(baseline.tilt_z),
        ],
        dtype=float,
    )
    checks = [
        _finite_pose(row),
        abs(float(metadata.get("local_decenter_x", 0.0)) - 2.5) < 1e-9,
        abs(float(metadata.get("local_decenter_y", 0.0)) + 1.25) < 1e-9,
        abs(float(metadata.get("local_tilt_x", 0.0)) - 4.0) < 1e-9,
        abs(float(metadata.get("local_tilt_y", 0.0)) + 2.0) < 1e-9,
        abs(float(metadata.get("local_tilt_z", 0.0)) - 7.0) < 1e-9,
        float(np.linalg.norm(decenter_delta)) > 1.0,
        float(np.linalg.norm(tilt_delta)) > 1.0,
    ]
    detail = (
        f"local=({metadata.get('local_decenter_x')},{metadata.get('local_decenter_y')},"
        f"{metadata.get('local_tilt_x')},{metadata.get('local_tilt_y')},{metadata.get('local_tilt_z')}), "
        f"decenter_delta=({decenter_delta[0]:.6g},{decenter_delta[1]:.6g},{decenter_delta[2]:.6g}), "
        f"tilt_delta=({tilt_delta[0]:.6g},{tilt_delta[1]:.6g},{tilt_delta[2]:.6g})"
    )
    return PathWorkbenchCheck(DEFAULT_LAYOUT_TITLE, "Local offset/tilt component", "Reflect", all(checks), detail)


def _validate_existing_path_pose_edit(editor: KrakenLayoutEditor, splitter_index: int) -> PathWorkbenchCheck:
    insert_at = max(1, len(editor.rows) - 1)
    row = editor._path_component_row_for_arm(
        splitter_index,
        "Reflect",
        PATH_COMPONENT_APERTURE,
        42.0,
        10.0,
        insert_at=insert_at,
    )
    editor.rows.insert(insert_at, row)
    try:
        before = np.asarray(
            [
                float(row.tilt_x),
                float(row.tilt_y),
                float(row.tilt_z),
                float(row.desp_x),
                float(row.desp_y),
                float(row.desp_z),
            ],
            dtype=float,
        )
        metadata = editor._element_metadata(editor.rows[insert_at])
        metadata.update(
            {
                "local_decenter_x": 3.0,
                "local_decenter_y": -2.0,
                "local_tilt_x": 5.0,
                "local_tilt_y": -1.0,
                "local_tilt_z": 4.0,
            }
        )
        updated = editor._apply_path_local_pose_to_indices([insert_at], metadata)
        edited = editor.rows[insert_at]
        after = np.asarray(
            [
                float(edited.tilt_x),
                float(edited.tilt_y),
                float(edited.tilt_z),
                float(edited.desp_x),
                float(edited.desp_y),
                float(edited.desp_z),
            ],
            dtype=float,
        )
        edited_metadata = editor._element_metadata(edited)
        checks = [
            updated == [insert_at],
            _finite_pose(edited),
            float(np.linalg.norm(after - before)) > 1.0,
            abs(float(edited_metadata.get("local_decenter_x", 0.0)) - 3.0) < 1e-9,
            abs(float(edited_metadata.get("local_decenter_y", 0.0)) + 2.0) < 1e-9,
            abs(float(edited_metadata.get("local_tilt_x", 0.0)) - 5.0) < 1e-9,
            abs(float(edited_metadata.get("local_tilt_y", 0.0)) + 1.0) < 1e-9,
            abs(float(edited_metadata.get("local_tilt_z", 0.0)) - 4.0) < 1e-9,
            str(edited_metadata.get("path_component_type", "")) == PATH_COMPONENT_APERTURE,
        ]
        detail = (
            f"row=S{insert_at}, local=({edited_metadata.get('local_decenter_x')},"
            f"{edited_metadata.get('local_decenter_y')},{edited_metadata.get('local_tilt_x')},"
            f"{edited_metadata.get('local_tilt_y')},{edited_metadata.get('local_tilt_z')}), "
            f"pose_delta_norm={float(np.linalg.norm(after - before)):.6g}"
        )
        return PathWorkbenchCheck(DEFAULT_LAYOUT_TITLE, "Edit existing path-local pose", "Reflect", all(checks), detail)
    except Exception as exc:
        return PathWorkbenchCheck(DEFAULT_LAYOUT_TITLE, "Edit existing path-local pose", "Reflect", False, str(exc))
    finally:
        if 0 <= insert_at < len(editor.rows):
            del editor.rows[insert_at]


def _validate_path_view_virtual_table_pose(editor: KrakenLayoutEditor, splitter_index: int) -> PathWorkbenchCheck:
    insert_at = max(1, len(editor.rows) - 1)
    row = editor._path_component_row_for_arm(
        splitter_index,
        "Reflect",
        PATH_COMPONENT_APERTURE,
        42.0,
        10.0,
        insert_at=insert_at,
        local_decenter_x=2.5,
        local_decenter_y=-1.25,
        local_tilt_x=4.0,
        local_tilt_y=-2.0,
        local_tilt_z=7.0,
    )
    editor.rows.insert(insert_at, row)
    try:
        reflect_entry = next(
            (
                entry
                for entry in editor._arm_catalog()
                if str(entry.get("key", "")).endswith("|reflect")
            ),
            None,
        )
        if reflect_entry is None:
            return PathWorkbenchCheck(DEFAULT_LAYOUT_TITLE, "Path-view virtual pose columns", "Reflect", False, "No reflected path view entry")
        editor.arm_view_var.set(str(reflect_entry["label"]))
        values = list(editor._table_values_for_surface_row(insert_at, editor.rows[insert_at]))
        column = {field: index for index, field in enumerate(FIELDS)}
        displayed = {
            "tilt_x": values[column["tilt_x"]],
            "tilt_y": values[column["tilt_y"]],
            "tilt_z": values[column["tilt_z"]],
            "desp_x": values[column["desp_x"]],
            "desp_y": values[column["desp_y"]],
            "desp_z": values[column["desp_z"]],
        }
        before = np.asarray(
            [
                float(editor.rows[insert_at].tilt_x),
                float(editor.rows[insert_at].tilt_y),
                float(editor.rows[insert_at].tilt_z),
                float(editor.rows[insert_at].desp_x),
                float(editor.rows[insert_at].desp_y),
                float(editor.rows[insert_at].desp_z),
            ],
            dtype=float,
        )
        edited_values = list(values)
        edited_values[column["tilt_x"]] = "6"
        edited_values[column["tilt_y"]] = "-3"
        edited_values[column["tilt_z"]] = "8"
        edited_values[column["desp_x"]] = "1.5"
        edited_values[column["desp_y"]] = "2.25"
        edited_values[column["desp_z"]] = "50"
        editor.table = _FakeTableRows({insert_at: edited_values})
        editor._table_path_local_mode_active = True
        editor._read_rows_from_table()
        edited = editor.rows[insert_at]
        after = np.asarray(
            [
                float(edited.tilt_x),
                float(edited.tilt_y),
                float(edited.tilt_z),
                float(edited.desp_x),
                float(edited.desp_y),
                float(edited.desp_z),
            ],
            dtype=float,
        )
        metadata = editor._element_metadata(edited)
        checks = [
            displayed == {
                "tilt_x": "4",
                "tilt_y": "-2",
                "tilt_z": "7",
                "desp_x": "2.5",
                "desp_y": "-1.25",
                "desp_z": "42",
            },
            abs(float(metadata.get("local_tilt_x", 0.0)) - 6.0) < 1e-9,
            abs(float(metadata.get("local_tilt_y", 0.0)) + 3.0) < 1e-9,
            abs(float(metadata.get("local_tilt_z", 0.0)) - 8.0) < 1e-9,
            abs(float(metadata.get("local_decenter_x", 0.0)) - 1.5) < 1e-9,
            abs(float(metadata.get("local_decenter_y", 0.0)) - 2.25) < 1e-9,
            abs(float(metadata.get("arm_distance", 0.0)) - 50.0) < 1e-9,
            float(np.linalg.norm(after - before)) > 1.0,
            _finite_pose(edited),
        ]
        detail = (
            f"display={displayed}, edited_local=({metadata.get('local_decenter_x')},"
            f"{metadata.get('local_decenter_y')},{metadata.get('arm_distance')},"
            f"{metadata.get('local_tilt_x')},{metadata.get('local_tilt_y')},{metadata.get('local_tilt_z')}), "
            f"pose_delta_norm={float(np.linalg.norm(after - before)):.6g}"
        )
        return PathWorkbenchCheck(DEFAULT_LAYOUT_TITLE, "Path-view virtual pose columns", "Reflect", all(checks), detail)
    except Exception as exc:
        return PathWorkbenchCheck(DEFAULT_LAYOUT_TITLE, "Path-view virtual pose columns", "Reflect", False, str(exc))
    finally:
        editor.arm_view_var.set("All paths")
        if 0 <= insert_at < len(editor.rows):
            del editor.rows[insert_at]


def _first_stock_lens_rows(editor: KrakenLayoutEditor) -> tuple[str, list] | None:
    catalogs = _available_stock_lens_catalogs()
    for _label, path in sorted(catalogs.items()):
        try:
            catalog = _load_stock_lens_catalog(path)
        except Exception:
            continue
        for part_number, item in sorted(catalog.items()):
            try:
                rows = editor._stock_lens_rows_from_catalog_item(part_number, item, gap_after=12.0)
            except Exception:
                continue
            if len(rows) >= 2:
                return str(part_number), rows
    return None


def _validate_stock_lens_block(
    editor: KrakenLayoutEditor,
    *,
    context: dict[str, object],
    part_number: str,
    rows: list,
    distance: float,
    layout: str,
    path_label: str,
    local_pose: tuple[float, float, float, float, float] = (0.0, 0.0, 0.0, 0.0, 0.0),
) -> PathWorkbenchCheck:
    try:
        local_dx, local_dy, local_tx, local_ty, local_tz = local_pose
        placed = editor._stock_lens_rows_for_path_context(
            rows,
            part_number=part_number,
            context=context,
            distance_mm=distance,
            local_decenter_x=local_dx,
            local_decenter_y=local_dy,
            local_tilt_x=local_tx,
            local_tilt_y=local_ty,
            local_tilt_z=local_tz,
        )
    except Exception as exc:
        return PathWorkbenchCheck(layout, PATH_COMPONENT_STOCK_LENS, path_label, False, str(exc))
    metadata = [
        row.advanced.get(ELEMENT_ADVANCED_ATTR, {}) if isinstance(row.advanced, dict) else {}
        for row in placed
    ]
    element_names = {str(row.element) for row in placed}
    offsets = [float(item.get("path_component_axial_offset", float("nan"))) for item in metadata]
    expected_path = str(context.get("branch_path", "") or "")
    checks = [
        len(placed) == len(rows),
        len(element_names) == 1,
        all(_finite_pose(row) for row in placed),
        all(str(item.get("path_component_type", "")) == PATH_COMPONENT_STOCK_LENS for item in metadata),
        all(str(item.get("path_component_part", "")) == part_number for item in metadata),
        all(int(item.get("path_component_row_count", 0)) == len(rows) for item in metadata),
        all(str(item.get("branch_path", "")) == expected_path for item in metadata),
        all(abs(float(item.get("local_decenter_x", 0.0)) - local_pose[0]) < 1e-9 for item in metadata),
        all(abs(float(item.get("local_decenter_y", 0.0)) - local_pose[1]) < 1e-9 for item in metadata),
        all(abs(float(item.get("local_tilt_x", 0.0)) - local_pose[2]) < 1e-9 for item in metadata),
        all(abs(float(item.get("local_tilt_y", 0.0)) - local_pose[3]) < 1e-9 for item in metadata),
        all(abs(float(item.get("local_tilt_z", 0.0)) - local_pose[4]) < 1e-9 for item in metadata),
        all(np.isfinite(offset) for offset in offsets),
        offsets == sorted(offsets),
    ]
    if expected_path:
        checks.append(all(str(item.get("path_frame_source", "")) == "traced_branch_path" for item in metadata))
        checks.append(all(int(item.get("path_frame_samples", 0)) > 0 for item in metadata))
    ok = all(checks)
    first = placed[0]
    last = placed[-1]
    detail = (
        f"part={part_number}, rows={len(placed)}, element={next(iter(element_names), '')}, "
        f"first_tilt=({float(first.tilt_x):.6g},{float(first.tilt_y):.6g},{float(first.tilt_z):.6g}), "
        f"last_decenter=({float(last.desp_x):.6g},{float(last.desp_y):.6g},{float(last.desp_z):.6g}), "
        f"offsets=({offsets[0]:.6g}->{offsets[-1]:.6g}), local_pose={local_pose}, branch_path={expected_path or '-'}"
    )
    return PathWorkbenchCheck(layout, PATH_COMPONENT_STOCK_LENS, path_label, ok, detail)


def _validate_existing_stock_block_pose_edit(
    editor: KrakenLayoutEditor,
    *,
    splitter_index: int,
    part_number: str,
    rows: list,
) -> PathWorkbenchCheck:
    try:
        context = editor._path_stock_lens_context(splitter_index=splitter_index, arm_role="Reflect")
        placed = editor._stock_lens_rows_for_path_context(
            rows,
            part_number=part_number,
            context=context,
            distance_mm=35.0,
        )
        insert_at = int(context.get("insert_index", max(1, len(editor.rows) - 1)))
        for offset, placed_row in enumerate(placed):
            editor.rows.insert(insert_at + offset, placed_row)
        indices = list(range(insert_at, insert_at + len(placed)))
        before = np.asarray(
            [
                [
                    float(editor.rows[index].tilt_x),
                    float(editor.rows[index].tilt_y),
                    float(editor.rows[index].tilt_z),
                    float(editor.rows[index].desp_x),
                    float(editor.rows[index].desp_y),
                    float(editor.rows[index].desp_z),
                ]
                for index in indices
            ],
            dtype=float,
        )
        metadata = editor._element_metadata(editor.rows[indices[0]])
        metadata.update(
            {
                "local_decenter_x": -1.5,
                "local_decenter_y": 2.25,
                "local_tilt_x": -3.0,
                "local_tilt_y": 1.25,
                "local_tilt_z": 2.0,
            }
        )
        updated = editor._apply_path_local_pose_to_indices(indices, metadata)
        after = np.asarray(
            [
                [
                    float(editor.rows[index].tilt_x),
                    float(editor.rows[index].tilt_y),
                    float(editor.rows[index].tilt_z),
                    float(editor.rows[index].desp_x),
                    float(editor.rows[index].desp_y),
                    float(editor.rows[index].desp_z),
                ]
                for index in indices
            ],
            dtype=float,
        )
        metadata_after = [editor._element_metadata(editor.rows[index]) for index in indices]
        offsets = [float(item.get("path_component_axial_offset", float("nan"))) for item in metadata_after]
        checks = [
            updated == indices,
            all(_finite_pose(editor.rows[index]) for index in indices),
            float(np.linalg.norm(after - before)) > 1.0,
            all(str(item.get("path_component_type", "")) == PATH_COMPONENT_STOCK_LENS for item in metadata_after),
            all(abs(float(item.get("local_decenter_x", 0.0)) + 1.5) < 1e-9 for item in metadata_after),
            all(abs(float(item.get("local_decenter_y", 0.0)) - 2.25) < 1e-9 for item in metadata_after),
            all(abs(float(item.get("local_tilt_x", 0.0)) + 3.0) < 1e-9 for item in metadata_after),
            all(abs(float(item.get("local_tilt_y", 0.0)) - 1.25) < 1e-9 for item in metadata_after),
            all(abs(float(item.get("local_tilt_z", 0.0)) - 2.0) < 1e-9 for item in metadata_after),
            offsets == sorted(offsets),
        ]
        detail = (
            f"part={part_number}, rows={len(indices)}, indices={indices[0]}-{indices[-1]}, "
            f"offsets=({offsets[0]:.6g}->{offsets[-1]:.6g}), "
            f"pose_delta_norm={float(np.linalg.norm(after - before)):.6g}"
        )
        return PathWorkbenchCheck(DEFAULT_LAYOUT_TITLE, "Edit existing stock-block local pose", "Reflect", all(checks), detail)
    except Exception as exc:
        return PathWorkbenchCheck(DEFAULT_LAYOUT_TITLE, "Edit existing stock-block local pose", "Reflect", False, str(exc))
    finally:
        try:
            for index in reversed(indices):  # type: ignore[name-defined]
                if 0 <= index < len(editor.rows):
                    del editor.rows[index]
        except Exception:
            pass


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
        _validate_detector_model_settings(editor, splitter_index),
        _validate_local_pose_component(editor, splitter_index),
        _validate_existing_path_pose_edit(editor, splitter_index),
        _validate_path_view_virtual_table_pose(editor, splitter_index),
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
    stock = _first_stock_lens_rows(editor)
    if stock is None:
        checks.append(PathWorkbenchCheck(layout, PATH_COMPONENT_STOCK_LENS, "Reflect", False, "No importable stock lens catalog item found"))
    else:
        part_number, stock_rows = stock
        checks.append(
            _validate_stock_lens_block(
                editor,
                context=editor._path_stock_lens_context(splitter_index=splitter_index, arm_role="Reflect"),
                part_number=part_number,
                rows=stock_rows,
                distance=35.0,
                layout=layout,
                path_label="Reflect",
                local_pose=(1.5, -2.0, 3.0, 0.5, -1.0),
            )
        )
        checks.append(
            _validate_existing_stock_block_pose_edit(
                editor,
                splitter_index=splitter_index,
                part_number=part_number,
                rows=stock_rows,
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
            if stock is not None:
                part_number, stock_rows = stock
                checks.append(
                    _validate_stock_lens_block(
                        traced_editor,
                        context=traced_editor._path_stock_lens_context(branch_path=branch_path),
                        part_number=part_number,
                        rows=stock_rows,
                        distance=18.0,
                        layout=NESTED_PATH_LAYOUT_TITLE,
                        path_label=f"Traced {traced_editor._branch_path_compact_detail(branch_path)}",
                        local_pose=(-1.0, 0.75, -2.0, 1.0, 0.5),
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
