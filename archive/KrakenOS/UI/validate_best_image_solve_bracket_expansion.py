from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor


def _load_layout_module(path: Path):
    spec = importlib.util.spec_from_file_location("kraken_ui_best_image_bracket_layout", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    layout_path = repo_root / "attachment" / "penta_solve.py"
    module = _load_layout_module(layout_path)
    settings = dict(getattr(module, "SETTINGS", {}) or {})
    info = {"surfaces": list(getattr(module, "SURFACES", []) or []), "settings": settings}
    rows = _rows_from_layout_info(info)
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = layout_path
    editor._normalize_special_rows()

    if editor._best_focus_solve_target_for_cell(6, "thickness") != "thickness":
        raise AssertionError("Expected row 6 thickness to allow Best Image Solve.")
    if editor._best_focus_metric_mode_for_rows(editor.rows) != "ray_trace":
        raise AssertionError("Expected penta_solve layout to use ray-traced Best Image Solve.")

    result = editor._compute_best_focus_result(6)
    solved_distance = float(result.get("solved_distance", np.nan))
    best_rms = float(result.get("best_rms", np.nan))
    if not np.isfinite(solved_distance):
        raise AssertionError("Best Image Solve returned a non-finite solved distance for row 6.")
    if not np.isfinite(best_rms):
        raise AssertionError("Best Image Solve returned a non-finite RMS for row 6.")
    if not (300.0 <= solved_distance <= 420.0):
        raise AssertionError(
            f"Expected bracket expansion to move penta_solve row 6 near its real focus, got {solved_distance:.6g} mm."
        )
    if best_rms >= 0.1:
        raise AssertionError(
            f"Expected penta_solve row 6 best-image RMS to shrink substantially, got {best_rms:.6g} mm."
        )
    if str(result.get("metric_mode", "")) != "ray_trace":
        raise AssertionError(f"Expected ray_trace metric mode, got {result.get('metric_mode')!r}.")
    if str(getattr(editor.progress_spinner_var, "get", lambda: "")()) != "ok":
        raise AssertionError("Best Image Solve did not finish with success progress state.")
    if str(getattr(editor.progress_percent_var, "get", lambda: "")()) != "100%":
        raise AssertionError("Best Image Solve did not drive progress to completion.")

    print(
        "validate_best_image_solve_bracket_expansion: "
        f"solved_distance={solved_distance:.6g}, best_rms={best_rms:.6g}, metric={result.get('metric_label', '')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
