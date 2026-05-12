"""Validate the Cooke-triplet optimization case-study docs, assets, and optics."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import LAYOUTS_DIR, KrakenLayoutEditor, _load_python_data, _load_python_title
from KrakenOS.UI.render_layout_snapshot import _build_runtime_system, _snapshot_editor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "cooke_triplet_optimization.rst"
INDEX_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "index.rst"
BOSS_DEMO_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "boss_demo_walkthrough.rst"
CHECKLIST_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "presentation_checklist.rst"
BACKLOG_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "optiland_port_backlog.rst"
CAPTURE_SCRIPT = PROJECT_ROOT / "KrakenOS" / "UI" / "capture_cooke_triplet_case_study_screenshots.py"
LAYOUT_TITLE = "Cooke Triplet Optimization Case Study"
STATIC_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "cooke_triplet_optimization"
EXPECTED_IMAGES = (
    "01_starting_cooke_ui.png",
    "01_starting_cooke_layout.png",
    "02_starting_spot_aoi.png",
    "03_starting_mtf_aoi.png",
    "04_optimized_prescription_ui.png",
    "04_optimized_cooke_layout.png",
    "05_optimized_spot_aoi.png",
    "06_optimized_mtf_aoi.png",
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


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load layout module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows_from_items(items: list[dict[str, object]]):
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in items]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    return rows


def _spot_rms_for_rows(path: Path, settings: dict[str, object], items: list[dict[str, object]]) -> dict[float, float]:
    rows = _rows_from_items(items)
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()
    system = _build_runtime_system(path, editor.rows)
    results: dict[float, float] = {}
    for field_y in (0.0, 3.0):
        x_local, y_local, _workers = editor._build_geometric_image_samples(
            system,
            0.55,
            sample_count=17,
            pattern="hexapolar",
            surface_index=-1,
            aperture_type="EPD",
            aperture_value=4.0,
            field_type="Angle",
            field_x=0.0,
            field_y=field_y,
        )
        x_vals = np.asarray(x_local, dtype=float)
        y_vals = np.asarray(y_local, dtype=float)
        finite = np.isfinite(x_vals) & np.isfinite(y_vals)
        if int(np.count_nonzero(finite)) < 20:
            raise AssertionError(f"Too few valid rays for field {field_y:g}: {int(np.count_nonzero(finite))}")
        x_vals = x_vals[finite]
        y_vals = y_vals[finite]
        results[field_y] = float(np.sqrt(np.mean((x_vals - np.mean(x_vals)) ** 2 + (y_vals - np.mean(y_vals)) ** 2)))
    return results


def _physics_checks(path: Path) -> list[tuple[str, bool]]:
    info = _load_python_data(path)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    module = _load_module(path)
    starting = list(getattr(module, "SURFACES"))
    optimized = list(getattr(module, "OPTIMIZED_SURFACES"))
    start_metrics = _spot_rms_for_rows(path, settings, starting)
    opt_metrics = _spot_rms_for_rows(path, settings, optimized)
    return [
        ("layout stores optimized prescription", len(starting) == len(optimized) == 8),
        (
            "starting layout marks six radius variables",
            sum(1 for item in starting if bool(item.get("optimize_rc"))) == 6,
        ),
        (
            "starting layout marks three thickness variables",
            sum(1 for item in starting if bool(item.get("optimize_thickness"))) == 3,
        ),
        ("starting point is deliberately poor on axis", start_metrics[0.0] > 1.0),
        ("starting point is deliberately poor off axis", start_metrics[3.0] > 1.0),
        ("optimized primary on-axis spot is small", opt_metrics[0.0] < 0.01),
        ("optimized primary 3 degree spot is small", opt_metrics[3.0] < 0.01),
        (
            "optimized prescription improves mean spot by more than 50x",
            np.mean(list(start_metrics.values())) / max(np.mean(list(opt_metrics.values())), 1e-12) > 50.0,
        ),
    ]


def main() -> int:
    path = _layout_path_by_title(LAYOUT_TITLE)
    doc = _text(DOC_PATH)
    index = _text(INDEX_PATH)
    boss = _text(BOSS_DEMO_PATH)
    checklist = _text(CHECKLIST_PATH)
    backlog = _text(BACKLOG_PATH)
    capture = _text(CAPTURE_SCRIPT)
    checks = [
        ("case-study page exists", DOC_PATH.exists()),
        ("case-study in tutorials toctree", "cooke_triplet_optimization" in index),
        ("case-study in boss demo walkthrough", "cooke_triplet_optimization" in boss),
        ("case-study in presentation checklist", "cooke_triplet_optimization" in checklist),
        ("optiland backlog marks Cooke port landed", "cooke_triplet_optimization" in backlog),
        ("capture script exists", CAPTURE_SCRIPT.exists() and "DEFAULT_OUTPUT_DIR" in capture),
        ("case-study documents Optiland source", "Optiland" in doc and "Tutorial_5c" in doc),
        ("case-study documents optimization variables", "six radii" in doc and "three air gaps" in doc),
        ("case-study documents final prescription", "22.01359" in doc and "42.20778" in doc),
    ]
    for image_name in EXPECTED_IMAGES:
        image_path = STATIC_DIR / image_name
        checks.append((f"image exists: {image_name}", image_path.exists() and image_path.stat().st_size > 2048))
    checks.extend(_physics_checks(path))

    failed = [name for name, ok in checks if not ok]
    if failed:
        print("Cooke-triplet case study validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("Cooke-triplet case study validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
