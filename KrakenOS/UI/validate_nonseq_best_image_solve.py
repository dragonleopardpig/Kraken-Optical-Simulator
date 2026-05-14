from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor


def _load_penta_module():
    repo_root = Path(__file__).resolve().parents[2]
    layout_path = repo_root / "attachment" / "penta.py"
    spec = importlib.util.spec_from_file_location("kraken_ui_penta_layout", layout_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {layout_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = _load_penta_module()
    settings = dict(getattr(module, "SETTINGS", {}) or {})
    info = {"surfaces": list(getattr(module, "SURFACES", []) or []), "settings": settings}
    rows = _rows_from_layout_info(info)
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = Path(__file__).resolve().parents[2] / "attachment" / "penta.py"
    editor._normalize_special_rows()

    for row_index in (5, 6):
        target = editor._best_focus_solve_target_for_cell(row_index, "thickness")
        if target != "thickness":
            raise AssertionError(f"Expected row {row_index} thickness to allow Best Image Solve, got {target!r}.")

    metric_mode = editor._best_focus_metric_mode_for_rows(editor.rows)
    if metric_mode != "ray_trace":
        raise AssertionError(f"Expected penta layout to use ray-traced best-image metric, got {metric_mode!r}.")

    result = editor._compute_best_focus_result(5)
    solved_distance = float(result.get("solved_distance", np.nan))
    best_rms = float(result.get("best_rms", np.nan))
    if not np.isfinite(solved_distance):
        raise AssertionError("Best Image Solve returned a non-finite solved distance for row 5.")
    if solved_distance < 0.0:
        raise AssertionError(f"Best Image Solve returned a negative solved distance for row 5: {solved_distance}.")
    if not np.isfinite(best_rms):
        raise AssertionError("Best Image Solve returned a non-finite RMS for row 5.")
    if str(result.get("metric_mode", "")) != "ray_trace":
        raise AssertionError(f"Expected row 5 solve to report ray_trace metric, got {result.get('metric_mode')!r}.")
    if str(getattr(editor.progress_spinner_var, "get", lambda: "")()) != "ok":
        raise AssertionError("Best Image Solve did not drive the progress spinner to success state.")
    if str(getattr(editor.progress_percent_var, "get", lambda: "")()) != "100%":
        raise AssertionError("Best Image Solve did not drive the progress percent to completion.")

    print(
        "validate_nonseq_best_image_solve: "
        f"metric={result.get('metric_label', '')}, solved_distance={solved_distance:.6g}, best_rms={best_rms:.6g}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
