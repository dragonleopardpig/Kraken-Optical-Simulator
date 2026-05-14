from __future__ import annotations

import numpy as np

from KrakenOS.UI.validate_branch_analysis import _load_traced_editor, _preferred_output_or_terminal_filter


def main() -> int:
    editor, _system, _rays, _wavelength = _load_traced_editor("Beam Splitter Two Path Doublets")
    filter_text = _preferred_output_or_terminal_filter(editor)
    editor.analysis_branch_filter_var.set(filter_text)

    row_index = 9
    target = editor._best_focus_solve_target_for_cell(row_index, "thickness")
    if target != "thickness":
        raise AssertionError(f"Expected row {row_index} thickness to allow Best Image Solve, got {target!r}.")

    metric_mode = editor._best_focus_metric_mode_for_rows(editor.rows)
    if metric_mode != "ray_trace":
        raise AssertionError(f"Expected beam splitter layout to use ray_trace metric, got {metric_mode!r}.")

    result = editor._compute_best_focus_result(row_index)
    solved_distance = float(result.get("solved_distance", np.nan))
    best_rms = float(result.get("best_rms", np.nan))
    if not np.isfinite(solved_distance):
        raise AssertionError("Branch Best Image Solve returned a non-finite solved distance.")
    if not np.isfinite(best_rms):
        raise AssertionError("Branch Best Image Solve returned a non-finite RMS.")
    if str(result.get("metric_mode", "")) != "ray_trace":
        raise AssertionError(f"Expected row {row_index} solve to report ray_trace metric, got {result.get('metric_mode')!r}.")
    if str(result.get("filter_text", "")) != filter_text:
        raise AssertionError(
            f"Expected branch solve to honor active analysis filter {filter_text!r}, got {result.get('filter_text')!r}."
        )
    if str(getattr(editor.progress_spinner_var, "get", lambda: "")()) != "ok":
        raise AssertionError("Branch Best Image Solve did not drive the progress spinner to success state.")
    if str(getattr(editor.progress_percent_var, "get", lambda: "")()) != "100%":
        raise AssertionError("Branch Best Image Solve did not drive the progress percent to completion.")

    print(
        "validate_best_image_branch_solve: "
        f"filter={filter_text}, solved_distance={solved_distance:.6g}, best_rms={best_rms:.6g}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
