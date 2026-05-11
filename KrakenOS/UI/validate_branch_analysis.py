from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.branch_throughput_analysis import (
    BRANCH_THROUGHPUT_CSV_COLUMNS,
    BRANCH_THROUGHPUT_FILTER_DEFAULT,
    branch_throughput_filter_choices,
    branch_throughput_report_text,
    branch_throughput_summary_text,
    branch_throughput_table_values,
    collect_branch_throughput_records,
    filtered_branch_throughput_records,
    iter_branch_throughput_csv_rows,
)
from KrakenOS.UI.detector_path_analysis import (
    BRANCH_DETECTOR_MTF_CSV_COLUMNS,
    BRANCH_DETECTOR_PSF_CSV_COLUMNS,
    DETECTOR_MAP_CSV_COLUMNS,
    branch_detector_mtf_data_from_psf,
    branch_detector_psf_data_from_samples,
    detector_map_data_from_samples,
    iter_branch_detector_mtf_csv_rows,
    iter_branch_detector_psf_csv_rows,
    iter_detector_map_csv_rows,
)
from KrakenOS.UI.layout_editor import LAYOUTS_DIR, _load_python_data, _load_python_title
from KrakenOS.UI.render_layout_snapshot import _build_runtime_system, _rows_from_layout_info, _snapshot_editor


DEFAULT_LAYOUTS = (
    "Beam Splitter Two Path Doublets",
    "Michelson Interferometer (Interferogram)",
)


@dataclass
class BranchValidationResult:
    layout: str
    filter: str
    check: str
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


def _load_traced_editor(title: str):
    path = _layout_path_by_title(title)
    info = _load_python_data(path)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
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
    return editor, system, rays, wavelength


def _result(layout: str, filter_text: str, check: str, ok: bool, detail: str) -> BranchValidationResult:
    return BranchValidationResult(layout=layout, filter=filter_text, check=check, ok=bool(ok), detail=str(detail))


def _check_finite_positive(value: object, *, minimum: float = 0.0) -> bool:
    try:
        numeric = float(value)
    except Exception:
        return False
    return bool(np.isfinite(numeric) and numeric > minimum)


def _arrays_close(data_a: dict[str, object], data_b: dict[str, object], keys: Iterable[str]) -> bool:
    for key in keys:
        if not np.allclose(np.asarray(data_a[key]), np.asarray(data_b[key])):
            return False
    return True


def _terminal_detector_filters(editor) -> list[str]:
    records = editor._collect_branch_throughput_records()
    choices = editor._branch_throughput_filter_choices(records)
    return [choice for choice in choices if choice.startswith("Terminal:") and "Detector" in choice]


def _preferred_output_or_terminal_filter(editor) -> str:
    records = editor._collect_branch_throughput_records()
    choices = editor._branch_throughput_filter_choices(records)
    preferred = (
        "Output: Detector output port",
        "Output: Cross output detector",
        "Output: Return output detector",
    )
    for value in preferred:
        if value in choices:
            return value
    terminals = [choice for choice in choices if choice.startswith("Terminal:") and "Detector" in choice]
    if terminals:
        return terminals[0]
    raise RuntimeError("No detector output or terminal path filter found")


def _service_branch_throughput_records(editor) -> list[dict[str, object]]:
    return collect_branch_throughput_records(
        editor._collect_ray_inspector_records(),
        terminal_label_for_record=lambda record: editor._terminal_surface_label(
            record.get("last_surface"),
            str(record.get("last_name", "") or ""),
        ),
        is_detector_surface=editor._surface_index_is_detector,
    )


def _validate_detector_terminal(layout: str, editor, system, filter_text: str) -> list[BranchValidationResult]:
    results: list[BranchValidationResult] = []
    detmap = editor._branch_detector_map_data(system, filter_text)
    service_detmap = detector_map_data_from_samples(
        detmap["samples"],
        filter_text,
        bins=int(detmap["bins"]),
        detector_model=dict(detmap.get("detector_model", {}) or {}),
    )
    detmap_service_ok = (
        int(detmap["bins"]) == int(service_detmap["bins"])
        and _arrays_close(detmap, service_detmap, ("hist", "x_edges", "y_edges", "weights"))
        and abs(float(detmap["total_power"]) - float(service_detmap["total_power"])) < 1e-12
        and abs(float(detmap["peak_power"]) - float(service_detmap["peak_power"])) < 1e-12
    )
    results.append(
        _result(
            layout,
            filter_text,
            "DetMap",
            _check_finite_positive(detmap.get("total_power")),
            f"rays={len(detmap['x_values'])}, bins={detmap['bins']}, power={float(detmap['total_power']):.6g}",
        )
    )
    results.append(
        _result(
            layout,
            filter_text,
            "DetMap service",
            detmap_service_ok,
            f"bins={detmap['bins']}, power={float(detmap['total_power']):.6g}",
        )
    )
    psf = editor._branch_detector_psf_data(system, filter_text)
    service_psf = branch_detector_psf_data_from_samples(
        psf["samples"],
        filter_text,
        bins=int(psf["bins"]),
        detector_model=dict(psf.get("detector_model", {}) or {}),
    )
    psf_service_ok = (
        int(psf["bins"]) == int(service_psf["bins"])
        and _arrays_close(psf, service_psf, ("hist", "x_edges", "y_edges", "centered_x", "centered_y", "weights"))
        and abs(float(psf["centroid_x"]) - float(service_psf["centroid_x"])) < 1e-12
        and abs(float(psf["centroid_y"]) - float(service_psf["centroid_y"])) < 1e-12
        and abs(float(psf["peak_power"]) - float(service_psf["peak_power"])) < 1e-12
    )
    psf_rows = editor._branch_detector_psf_csv_rows(psf)
    service_psf_rows = list(iter_branch_detector_psf_csv_rows(psf))
    detmap_rows = list(iter_detector_map_csv_rows(detmap))
    expected_detmap_rows = int(detmap.get("bins", 0)) ** 2
    detmap_export_ok = (
        len(detmap_rows) > 0
        and len(detmap_rows) == expected_detmap_rows
        and tuple(detmap_rows[0].keys()) == DETECTOR_MAP_CSV_COLUMNS
        and all(np.isfinite(float(row["power"])) for row in detmap_rows)
        and any(float(row["power"]) > 0.0 for row in detmap_rows)
    )
    results.append(
        _result(
            layout,
            filter_text,
            "DetMap CSV",
            detmap_export_ok,
            f"rows={len(detmap_rows)}, expected={expected_detmap_rows}",
        )
    )
    expected_psf_rows = int(psf.get("bins", 0)) ** 2
    results.append(
        _result(
            layout,
            filter_text,
            "Path PSF",
            _check_finite_positive(psf.get("peak_power")) and int(psf.get("bins", 0)) >= 4,
            f"rays={len(psf['x_values'])}, bins={psf['bins']}, peak={float(psf['peak_power']):.6g}",
        )
    )
    results.append(
        _result(
            layout,
            filter_text,
            "Path PSF service",
            psf_service_ok,
            f"centroid=({float(psf['centroid_x']):.6g},{float(psf['centroid_y']):.6g}), bins={psf['bins']}",
        )
    )
    psf_export_ok = (
        len(psf_rows) > 0
        and len(psf_rows) == expected_psf_rows
        and psf_rows == service_psf_rows
        and tuple(psf_rows[0].keys()) == BRANCH_DETECTOR_PSF_CSV_COLUMNS
        and all(np.isfinite(float(row["power"])) for row in psf_rows)
        and any(float(row["power"]) > 0.0 for row in psf_rows)
    )
    results.append(
        _result(
            layout,
            filter_text,
            "Path PSF CSV",
            psf_export_ok,
            f"rows={len(psf_rows)}, expected={expected_psf_rows}",
        )
    )
    mtf = editor._branch_detector_mtf_data(system, filter_text)
    plot_freq = np.asarray(mtf["plot_freq"], dtype=float)
    plot_tan = np.asarray(mtf["plot_tan"], dtype=float)
    plot_sag = np.asarray(mtf["plot_sag"], dtype=float)
    service_mtf = branch_detector_mtf_data_from_psf(psf)
    mtf_service_ok = _arrays_close(mtf, service_mtf, ("plot_freq", "plot_tan", "plot_sag", "plot_avg"))
    mtf_rows = editor._branch_detector_mtf_csv_rows(mtf)
    service_mtf_rows = list(
        iter_branch_detector_mtf_csv_rows(
            mtf,
            target_freq=editor._current_mtf_frequency(),
            mtf_mode=editor._operand_mtf_mode("MTF @ freq"),
        )
    )
    mtf_ok = (
        plot_freq.size > 1
        and np.all(np.isfinite(plot_freq))
        and np.all(np.isfinite(plot_tan))
        and np.all(np.isfinite(plot_sag))
        and abs(float(plot_tan[0]) - 1.0) < 1e-9
        and abs(float(plot_sag[0]) - 1.0) < 1e-9
    )
    results.append(
        _result(
            layout,
            filter_text,
            "Path MTF",
            mtf_ok,
            f"samples={plot_freq.size}, fmax={float(plot_freq[-1]):.6g}, tan0={float(plot_tan[0]):.6g}, sag0={float(plot_sag[0]):.6g}",
        )
    )
    results.append(
        _result(
            layout,
            filter_text,
            "Path MTF service",
            mtf_service_ok,
            f"samples={plot_freq.size}, fmax={float(plot_freq[-1]):.6g}",
        )
    )
    mtf_export_ok = (
        len(mtf_rows) > 0
        and len(mtf_rows) == plot_freq.size
        and mtf_rows == service_mtf_rows
        and tuple(mtf_rows[0].keys()) == BRANCH_DETECTOR_MTF_CSV_COLUMNS
        and all(np.isfinite(float(row["frequency_cy_per_mm"])) for row in mtf_rows)
        and all(np.isfinite(float(row["average_mtf"])) for row in mtf_rows)
    )
    results.append(
        _result(
            layout,
            filter_text,
            "Path MTF CSV",
            mtf_export_ok,
            f"rows={len(mtf_rows)}, expected={plot_freq.size}",
        )
    )
    return results


def validate_layout(title: str) -> list[BranchValidationResult]:
    editor, system, _rays, wavelength = _load_traced_editor(title)
    results: list[BranchValidationResult] = []
    records = editor._collect_branch_throughput_records()
    service_records = _service_branch_throughput_records(editor)
    filtered_records = filtered_branch_throughput_records(service_records, BRANCH_THROUGHPUT_FILTER_DEFAULT)
    service_report = branch_throughput_report_text(filtered_records, service_records, BRANCH_THROUGHPUT_FILTER_DEFAULT)
    service_csv_rows = list(iter_branch_throughput_csv_rows(filtered_records))
    results.append(
        _result(
            title,
            BRANCH_THROUGHPUT_FILTER_DEFAULT,
            "Path throughput service",
            records == service_records
            and editor._branch_throughput_filter_choices(records) == branch_throughput_filter_choices(service_records)
            and editor._branch_throughput_report_text() == service_report
            and "Total throughput:" in service_report
            and branch_throughput_summary_text(filtered_records, service_records, BRANCH_THROUGHPUT_FILTER_DEFAULT).startswith(
                f"{len(filtered_records)}/{len(service_records)}"
            )
            and bool(filtered_records)
            and len(branch_throughput_table_values(filtered_records[0])) == 11
            and len(service_csv_rows) == len(filtered_records)
            and tuple(service_csv_rows[0].keys()) == BRANCH_THROUGHPUT_CSV_COLUMNS,
            f"records={len(service_records)}, csv_columns={len(BRANCH_THROUGHPUT_CSV_COLUMNS)}, report_chars={len(service_report)}",
        )
    )
    terminal_filters = _terminal_detector_filters(editor)
    results.append(
        _result(
            title,
            "All detector terminals",
            "Detector terminals",
            len(terminal_filters) > 0,
            f"count={len(terminal_filters)}",
        )
    )
    for filter_text in terminal_filters[:2]:
        try:
            results.extend(_validate_detector_terminal(title, editor, system, filter_text))
        except Exception as exc:
            results.append(_result(title, filter_text, "Detector path diagnostics", False, str(exc)))

    try:
        coherent_filter = _preferred_output_or_terminal_filter(editor)
        coherent = editor._coherent_detector_field_data(system, wavelength, coherent_filter)
        branch_codes = list(coherent.get("branch_codes", []) or [])
        coherent_ok = (
            int(coherent.get("sample_count", 0)) > 0
            and _check_finite_positive(coherent.get("peak_intensity"))
            and _check_finite_positive(coherent.get("total_input_power"))
            and "Jones" in str(coherent.get("polarization_model", ""))
        )
        if "Interferometer" in title:
            coherent_ok = coherent_ok and len(branch_codes) >= 2
        results.append(
            _result(
                title,
                coherent_filter,
                "CohDet",
                coherent_ok,
                "rays={rays}, bins={bins}, codes={codes}, input={input_power:.6g}, peak={peak:.6g}, pol={pol}".format(
                    rays=int(coherent.get("sample_count", 0)),
                    bins=int(coherent.get("bins", 0)),
                    codes=",".join(str(code) for code in branch_codes),
                    input_power=float(coherent.get("total_input_power", 0.0)),
                    peak=float(coherent.get("peak_intensity", 0.0)),
                    pol=str(coherent.get("polarization_model", "")),
                ),
            )
        )
    except Exception as exc:
        results.append(_result(title, "Detector output", "CohDet", False, str(exc)))
    return results


def validate_branch_analysis(layouts: Iterable[str] = DEFAULT_LAYOUTS) -> list[BranchValidationResult]:
    results: list[BranchValidationResult] = []
    for title in layouts:
        try:
            results.extend(validate_layout(str(title)))
        except Exception as exc:
            results.append(_result(str(title), "-", "Layout trace", False, str(exc)))
    return results


def _print_table(results: list[BranchValidationResult]) -> None:
    print("KrakenOS path-analysis validation")
    print("layout | filter | check | status | detail")
    print("--- | --- | --- | --- | ---")
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"{result.layout} | {result.filter} | {result.check} | {status} | {result.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate path-filtered detector analyses on known layouts.")
    parser.add_argument("--layout", action="append", dest="layouts", help="Common layout title to validate. May be repeated.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    results = validate_branch_analysis(args.layouts or DEFAULT_LAYOUTS)
    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        _print_table(results)
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
