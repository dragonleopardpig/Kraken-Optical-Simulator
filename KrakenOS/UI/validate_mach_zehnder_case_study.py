"""Validate the Mach-Zehnder case-study docs, assets, and two-output analyses."""

from __future__ import annotations

from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.validate_branch_analysis import _load_traced_editor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "mach_zehnder_interferometer.rst"
INDEX_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "index.rst"
CAPTURE_SCRIPT = PROJECT_ROOT / "KrakenOS" / "UI" / "capture_mach_zehnder_case_study_screenshots.py"
STATIC_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "mach_zehnder_interferometer"
LAYOUT_TITLE = "Mach-Zehnder Interferometer (Interferogram)"
CROSS_OUTPUT_FILTER = "Output: Detector output port"
RETURN_OUTPUT_FILTER = "Output: Source return port"
EXPECTED_IMAGES = (
    "01_loaded_mach_zehnder_ui.png",
    "02_mach_zehnder_path_labels.png",
    "03_cross_output_path_view_ui.png",
    "04_return_output_path_view_ui.png",
    "05_cross_detector_map_aoi.png",
    "06_cross_coherent_detector_aoi.png",
    "07_cross_interferogram_aoi.png",
    "08_cross_branch_field_aoi.png",
    "09_return_coherent_detector_aoi.png",
)


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _trace_dense_mach_zehnder():
    editor, system, _rays, wavelength = _load_traced_editor(LAYOUT_TITLE)
    editor.ray_count_var.set("121")
    editor.source_radius_var.set("4.0")
    editor.detector_bins_var.set("128")
    editor.coherent_sum_mode_var.set("Mutual coherent")
    editor.branch_field_propagation_mm_var.set("0.0")
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in editor.rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    editor.last_system = system
    editor.last_rays = rays
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    return editor, system, rays, wavelength


def _output_checks(editor, system, wavelength: float, filter_text: str, expected_codes: set[str], expected_detector: str) -> list[tuple[str, bool]]:
    detmap = editor._branch_detector_map_data(system, filter_text)
    coherent = editor._coherent_detector_field_data(system, wavelength, filter_text)
    branch_field = editor._branch_field_analysis_data(system, wavelength, filter_text)
    hist = np.asarray(detmap.get("hist", np.asarray([])), dtype=float)
    branch_field_intensity = np.asarray(branch_field.get("branch_field_intensity", np.asarray([])), dtype=float)
    return [
        (
            f"{filter_text} detector map receives detector-plane power",
            hist.shape == (128, 128)
            and np.all(np.isfinite(hist))
            and float(detmap.get("total_power", 0.0) or 0.0) > 0.0
            and expected_detector in str(detmap.get("terminal_label", "")),
        ),
        (
            f"{filter_text} coherent detector recombines expected branch pair",
            int(coherent.get("sample_count", 0) or 0) > 100
            and set(str(code) for code in coherent.get("branch_codes", []) or []) == expected_codes
            and float(coherent.get("total_input_power", 0.0) or 0.0) > 0.0
            and float(coherent.get("total_coherent_power", 0.0) or 0.0) > 0.0
            and expected_detector in str(coherent.get("terminal_label", "")),
        ),
        (
            f"{filter_text} branch-field analysis promotes coherent detector samples",
            branch_field_intensity.shape == (128, 128)
            and np.all(np.isfinite(branch_field_intensity))
            and abs(float(branch_field.get("branch_field_total_power", 0.0) or 0.0) - float(coherent.get("total_coherent_power", 0.0) or 0.0)) < 1e-9
            and 0.0 <= float(branch_field.get("branch_field_tem00_overlap_efficiency", -1.0) or -1.0) <= 1.0,
        ),
    ]


def _analysis_checks() -> list[tuple[str, bool]]:
    editor, system, rays, wavelength = _trace_dense_mach_zehnder()
    records = editor._collect_ray_analysis_records()
    filters = set(editor._branch_throughput_filter_choices(editor._collect_branch_throughput_records()))
    arm_labels = {str(entry.get("label", "")) for entry in editor._arm_catalog()}
    interferogram = editor._interferogram_analysis_data(system, rays, wavelength)
    interferogram_intensity = np.asarray(interferogram.get("intensity", np.asarray([])), dtype=float)
    checks = [
        (
            "Mach-Zehnder path catalog exposes five physical path labels",
            {
                "Path 1: Input to BS1",
                "Path 2: BS1 to BS2 transmit path",
                "Path 3: BS1 to BS2 reflect path",
                "Path 4: BS2 to cross output detector",
                "Path 5: BS2 to return output detector",
            }.issubset(arm_labels),
        ),
        (
            "dense Mach-Zehnder trace exposes both output filters",
            len(records) >= 400 and {CROSS_OUTPUT_FILTER, RETURN_OUTPUT_FILTER}.issubset(filters),
        ),
        (
            "cross-output interferogram uses reliable coherent detector-bin data",
            str(interferogram.get("data_source", "")) == "coherent_detector"
            and str(interferogram.get("filter_text", "")) == CROSS_OUTPUT_FILTER
            and bool(interferogram.get("reliable", False))
            and set(str(code) for code in interferogram.get("branch_codes", []) or []) == {"RT", "TR"}
            and interferogram_intensity.shape == (128, 128)
            and np.isfinite(interferogram_intensity).any()
            and float(interferogram.get("pair_interference_peak", 0.0) or 0.0) > 0.0,
        ),
    ]
    checks.extend(_output_checks(editor, system, wavelength, CROSS_OUTPUT_FILTER, {"RT", "TR"}, "detector A"))
    checks.extend(_output_checks(editor, system, wavelength, RETURN_OUTPUT_FILTER, {"RR", "TT"}, "detector B"))
    return checks


def main() -> int:
    doc = _text(DOC_PATH)
    index = _text(INDEX_PATH)
    capture = _text(CAPTURE_SCRIPT)
    checks = [
        ("case-study page exists", DOC_PATH.exists()),
        ("case-study in tutorials toctree", "mach_zehnder_interferometer" in index),
        ("capture script exists", CAPTURE_SCRIPT.exists() and "DEFAULT_OUTPUT_DIR" in capture),
        ("case-study documents cascaded beam splitters", "two deterministic 50/50 beam splitters" in doc),
        ("case-study documents both path views", "Path 4: BS2 to cross output detector" in doc and "Path 5: BS2 to return output detector" in doc),
        ("case-study documents both output filters", CROSS_OUTPUT_FILTER in doc and RETURN_OUTPUT_FILTER in doc),
        ("case-study documents detector analyses", "DetMap" in doc and "CohDet" in doc and "Interf" in doc and "BField" in doc),
    ]
    for image_name in EXPECTED_IMAGES:
        path = STATIC_DIR / image_name
        checks.append((f"image exists: {image_name}", path.exists() and path.stat().st_size > 2048))
    checks.extend(_analysis_checks())

    failed = [name for name, ok in checks if not ok]
    if failed:
        print("Mach-Zehnder case study validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("Mach-Zehnder case study validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
