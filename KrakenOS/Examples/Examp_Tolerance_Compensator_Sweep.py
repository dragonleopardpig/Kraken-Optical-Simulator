"""Tolerance Monte Carlo plus compensator sweeps.

This example uses the layout editor's headless workflow helpers so the same
logic matches the UI menu actions:

1. mark variables through the layout's optimization/native variable metadata,
2. run a deterministic tolerance Monte Carlo,
3. identify the worst valid perturbed sample,
4. sweep each marked variable as a possible compensator while holding the other
   variables at the worst-sample values,
5. run a small coordinate-style multi-compensator solve from the same worst
   sample,
6. save/apply the same choices as a tolerance solve preset.

The sweep is diagnostic only. It does not mutate the nominal prescription.
"""

from __future__ import annotations

from KrakenOS.common_optical_layouts.native_variable_breadth_example import SETTINGS, SURFACES
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor


def main() -> None:
    rows = _rows_from_layout_info({"surfaces": SURFACES, "settings": SETTINGS})
    editor = _snapshot_editor(rows, SETTINGS)

    # Restrict compensation to conic k. The row's other marked variable
    # remains a sampled tolerance error but is held fixed during compensation.
    editor.set_tolerance_compensator_enabled(surface_index=1, parameter="k", enabled=True)
    preset = editor.save_tolerance_solve_preset(
        "K-only compensation",
        sample_count=5,
        seed=2026,
        compensator_steps=5,
        multi_steps=3,
        multi_passes=2,
    )
    editor.apply_tolerance_solve_preset("K-only compensation")

    monte_carlo = editor.run_tolerance_monte_carlo(
        sample_count=int(preset["sample_count"]),
        seed=int(preset["seed"]),
    )
    sweep = editor.run_tolerance_compensator_sweep(
        monte_carlo,
        steps=int(preset["compensator_steps"]),
    )
    multi = editor.run_tolerance_multi_compensator_solve(
        monte_carlo,
        steps=int(preset["multi_steps"]),
        passes=int(preset["multi_passes"]),
    )

    print(editor.tolerance_solve_preset_report_text(preset))
    print(editor.tolerance_monte_carlo_report_text(monte_carlo))
    print(editor.tolerance_compensator_sweep_report_text(sweep))
    print(editor.tolerance_multi_compensator_report_text(multi))

    columns, records = editor.tolerance_compensator_csv_rows(sweep)
    print(f"Compensator CSV columns: {', '.join(columns[:8])} ...")
    print(f"Compensator CSV rows: {len(records)}")

    multi_columns, multi_records = editor.tolerance_multi_compensator_csv_rows(multi)
    print(f"Multi-compensator CSV columns: {', '.join(multi_columns[:8])} ...")
    print(f"Multi-compensator CSV rows: {len(multi_records)}")


if __name__ == "__main__":
    main()
