"""Validate the Gaussian beam-expander case-study docs, assets, and physics."""

from __future__ import annotations

from pathlib import Path
import warnings

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import LAYOUTS_DIR, SurfaceRow, _load_python_data, _load_python_title
from KrakenOS.UI.render_layout_snapshot import _build_runtime_system, _rows_from_layout_info, _snapshot_editor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "gaussian_beam_expander.rst"
INDEX_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "index.rst"
CAPTURE_SCRIPT = PROJECT_ROOT / "KrakenOS" / "UI" / "capture_gaussian_beam_expander_case_study_screenshots.py"
STATIC_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "gaussian_beam_expander"
LAYOUT_TITLE = "Gaussian Laser Beam Expander Case Study"
EXPECTED_IMAGES = (
    "01_datasheet_gaussian_source_ui.png",
    "02_free_space_gaussian_layout.png",
    "03_free_space_gaussian_report.png",
    "04_expander_table_ui.png",
    "05_expander_gaussian_layout.png",
    "06_expander_gaussian_report.png",
    "07_expander_bfield_aoi.png",
)


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


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


def _free_space_editor():
    path = _layout_path_by_title(LAYOUT_TITLE)
    info = _load_python_data(path)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(_rows_from_layout_info(info), settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()
    return path, editor


def _expander_editor(settings: dict[str, object], path: Path):
    rows = [
        SurfaceRow(surface="Object", name="Laser output", thickness=80.0, diameter=16.0, glass="AIR"),
        SurfaceRow(surface="Thin Lens", name="Input lens f=50", rc=50.0, thickness=200.0, diameter=20.0, glass="AIR"),
        SurfaceRow(surface="Thin Lens", name="Collimating lens f=150", rc=150.0, thickness=320.0, diameter=45.0, glass="AIR"),
        SurfaceRow(surface="Image", name="Readout plane", thickness=0.0, diameter=50.0, glass="AIR"),
    ]
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()
    return editor


def _gaussian_trace(editor, path: Path):
    wavelength = editor._current_wavelength()
    system = _build_runtime_system(path, editor.rows)
    beam = editor._current_gaussian_beam_input(wavelength)
    trace = Kos.propagate_gaussian_beam(system.ParaxMatrices(wavelength), beam)
    return system, wavelength, beam, trace


def _gaussian_physics_checks() -> list[tuple[str, bool]]:
    path, free_editor = _free_space_editor()
    info = _load_python_data(path)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        _free_system, wavelength, beam, free_trace = _gaussian_trace(free_editor, path)
        expander_editor = _expander_editor(settings, path)
        expander_system, _wavelength, expander_beam, expander_trace = _gaussian_trace(expander_editor, path)

    free_final = free_trace.final
    expander_final = expander_trace.final
    if free_final is None or expander_final is None:
        return [("Gaussian traces have final planes", False)]

    checks = [
        (
            "common layout uses datasheet Gaussian source settings",
            free_editor._current_source_model() == "Gaussian beam"
            and free_editor._current_gaussian_input_mode() == "Diameter + divergence"
            and abs(float(wavelength) - 0.6328) < 1e-12
            and abs(float(expander_beam.wavelength_um) - float(beam.wavelength_um)) < 1e-12,
        ),
        (
            "datasheet input back-calculates expected waist radius",
            abs(float(beam.waist_radius_mm) - 0.402853) < 5e-4,
        ),
        (
            "datasheet input back-calculates expected upstream waist offset",
            abs(float(beam.waist_offset_mm) - 592.316) < 1.0,
        ),
        (
            "free-space report keeps original half divergence",
            abs(float(free_final.divergence_mrad) - 0.5) < 1e-9
            and 1.30 < float(free_final.beam_diameter_mm) < 1.42,
        ),
        (
            "expander report shows about 3x output beam diameter",
            2.9 < float(expander_final.beam_diameter_mm) < 3.3,
        ),
        (
            "expander report shows about 3x lower divergence",
            abs(float(expander_final.divergence_mrad) - (0.5 / 3.0)) < 1e-9,
        ),
    ]

    rays = Kos.raykeeper(expander_system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in expander_editor.rows), default=1.0)
    expander_editor._trace_preview_rays(expander_system, rays, wavelength, max_radius, allow_full_pupil=False)
    expander_editor.last_system = expander_system
    expander_editor.last_rays = rays
    expander_editor._last_preview_trace_signature = expander_editor._preview_trace_signature()
    bundle = expander_editor._build_scene_bundle(expander_system, rays, max_radius)
    thin_lens_rows = {index for index, row in enumerate(expander_editor.rows) if row.surface == "Thin Lens"}
    thin_lens_x_spans: list[float] = []
    for curve in bundle.surface_curves:
        if int(getattr(curve, "row_index", -1)) not in thin_lens_rows:
            continue
        points = np.asarray(getattr(curve, "points_world", np.empty((0, 2))), dtype=float)
        if points.ndim == 2 and points.shape[0] >= 2:
            thin_lens_x_spans.append(float(np.ptp(points[:, 0])))
    field_data = expander_editor._branch_field_analysis_data(expander_system, wavelength, "All paths")
    intensity = np.asarray(field_data.get("branch_field_intensity", np.asarray([])), dtype=float)
    checks.extend(
        [
            (
                "expander 2D layout renders thin lenses as glyphs instead of vertical lines",
                len(thin_lens_x_spans) >= 2 and min(thin_lens_x_spans) > 1.0,
            ),
            (
                "BField analysis produces a finite 64x64 detector field",
                intensity.shape == (64, 64)
                and np.all(np.isfinite(intensity))
                and float(field_data.get("branch_field_total_power", 0.0) or 0.0) > 0.0,
            ),
            (
                "BField analysis reports finite TEM00 overlap diagnostics",
                0.0 <= float(field_data.get("branch_field_tem00_overlap_efficiency", -1.0) or -1.0) <= 1.0
                and float(field_data.get("branch_field_tem00_waist_mm", 0.0) or 0.0) > 0.0,
            ),
        ]
    )
    return checks


def main() -> int:
    doc = _text(DOC_PATH)
    index = _text(INDEX_PATH)
    capture = _text(CAPTURE_SCRIPT)
    checks = [
        ("case-study page exists", DOC_PATH.exists()),
        ("case-study in tutorials toctree", "gaussian_beam_expander" in index),
        ("capture script exists", CAPTURE_SCRIPT.exists() and "DEFAULT_OUTPUT_DIR" in capture),
        ("case-study documents datasheet input", "Diameter + divergence" in doc and "GB full div" in doc),
        ("case-study documents q report", "Gaussian Beam Report" in doc and "q`` propagation" in doc),
        ("case-study documents BField", "BField" in doc and "TEM00" in doc),
        ("case-study explains ideal thin-lens drawing glyph", "lens glyph" in doc and "not a physical center thickness" in doc),
    ]
    for image_name in EXPECTED_IMAGES:
        path = STATIC_DIR / image_name
        checks.append((f"image exists: {image_name}", path.exists() and path.stat().st_size > 2048))
    checks.extend(_gaussian_physics_checks())

    failed = [name for name, ok in checks if not ok]
    if failed:
        print("Gaussian beam-expander case study validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("Gaussian beam-expander case study validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
