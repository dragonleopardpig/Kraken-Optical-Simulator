"""Validate the Michelson interferometer case-study docs, assets, and analyses."""

from __future__ import annotations

from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.validate_branch_analysis import _load_traced_editor, _preferred_output_or_terminal_filter


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "michelson_interferometer.rst"
INDEX_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "index.rst"
CAPTURE_SCRIPT = PROJECT_ROOT / "KrakenOS" / "UI" / "capture_michelson_case_study_screenshots.py"
STATIC_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "michelson_interferometer"
LAYOUT_TITLE = "Michelson Interferometer (Interferogram)"
EXPECTED_IMAGES = (
    "01_loaded_michelson_ui.png",
    "02_michelson_path_labels.png",
    "03_detector_path_view_ui.png",
    "04_detector_map_aoi.png",
    "05_coherent_detector_aoi.png",
    "06_interferogram_aoi.png",
    "07_branch_field_aoi.png",
)


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _trace_dense_michelson():
    editor, system, _rays, wavelength = _load_traced_editor(LAYOUT_TITLE)
    editor.ray_count_var.set("121")
    editor.source_radius_var.set("8.0")
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


def _analysis_checks() -> list[tuple[str, bool]]:
    editor, system, rays, wavelength = _trace_dense_michelson()
    records = editor._ray_analysis_records_for_trace(system=system, rays=rays)
    filter_text = _preferred_output_or_terminal_filter(editor, ray_records=records)
    arm_labels = {str(entry.get("label", "")) for entry in editor._arm_catalog()}
    detmap = editor._branch_detector_map_data(system, filter_text, ray_records=records)
    coherent = editor._coherent_detector_field_data(system, wavelength, filter_text, ray_records=records)
    interferogram = editor._interferogram_analysis_data(system, rays, wavelength)
    branch_field = editor._branch_field_analysis_data(system, wavelength, filter_text, ray_records=records)
    hist = np.asarray(detmap.get("hist", np.asarray([])), dtype=float)
    intensity = np.asarray(interferogram.get("intensity", np.asarray([])), dtype=float)
    branch_field_intensity = np.asarray(branch_field.get("branch_field_intensity", np.asarray([])), dtype=float)
    return [
        (
            "Michelson path catalog exposes four user-facing path labels",
            {
                "Path 1: Input / source return",
                "Path 2: Transmit mirror path",
                "Path 3: Reflect mirror path",
                "Path 4: Detector output path",
            }.issubset(arm_labels),
        ),
        (
            "dense Michelson trace produces deterministic branch records",
            len(records) >= 400 and filter_text == "Output: Detector output port",
        ),
        (
            "detector map receives detector-plane power",
            hist.shape == (128, 128)
            and np.all(np.isfinite(hist))
            and float(detmap.get("total_power", 0.0) or 0.0) > 0.0
            and "Detector" in str(detmap.get("terminal_label", "")),
        ),
        (
            "coherent detector recombines RT and TR branches",
            int(coherent.get("sample_count", 0) or 0) > 100
            and set(str(code) for code in coherent.get("branch_codes", []) or []) == {"RT", "TR"}
            and float(coherent.get("total_input_power", 0.0) or 0.0) > 0.0
            and float(coherent.get("total_coherent_power", 0.0) or 0.0) > 0.0,
        ),
        (
            "interferogram uses reliable coherent detector-bin data",
            str(interferogram.get("data_source", "")) == "coherent_detector"
            and bool(interferogram.get("reliable", False))
            and intensity.shape == (128, 128)
            and np.isfinite(intensity).any()
            and float(interferogram.get("pair_interference_peak", 0.0) or 0.0) > 0.0,
        ),
        (
            "branch-field analysis promotes coherent detector samples",
            branch_field_intensity.shape == (128, 128)
            and np.all(np.isfinite(branch_field_intensity))
            and abs(float(branch_field.get("branch_field_total_power", 0.0) or 0.0) - float(coherent.get("total_coherent_power", 0.0) or 0.0)) < 1e-9
            and 0.0 <= float(branch_field.get("branch_field_tem00_overlap_efficiency", -1.0) or -1.0) <= 1.0,
        ),
    ]


def main() -> int:
    doc = _text(DOC_PATH)
    index = _text(INDEX_PATH)
    capture = _text(CAPTURE_SCRIPT)
    checks = [
        ("case-study page exists", DOC_PATH.exists()),
        ("case-study in tutorials toctree", "michelson_interferometer" in index),
        ("capture script exists", CAPTURE_SCRIPT.exists() and "DEFAULT_OUTPUT_DIR" in capture),
        ("case-study documents source/object split", "Object`` and ``Source`` are separate" in doc),
        ("case-study documents path view", "Path view" in doc and "Path 4: Detector output path" in doc),
        ("case-study documents detector analyses", "DetMap" in doc and "CohDet" in doc and "Interf" in doc and "BField" in doc),
    ]
    for image_name in EXPECTED_IMAGES:
        path = STATIC_DIR / image_name
        checks.append((f"image exists: {image_name}", path.exists() and path.stat().st_size > 2048))
    checks.extend(_analysis_checks())

    failed = [name for name, ok in checks if not ok]
    if failed:
        print("Michelson case study validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("Michelson case study validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
