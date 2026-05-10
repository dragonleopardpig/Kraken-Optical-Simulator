from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np
from matplotlib.figure import Figure

from KrakenOS.common_optical_layouts.native_variable_breadth_example import SETTINGS, SURFACES, TITLE
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor


@dataclass
class ToleranceMonteCarloCheck:
    check: str
    ok: bool
    detail: str


def _total_merit_series(summary: dict[str, object]) -> list[float]:
    return [
        float(record.get("total_merit", np.nan))
        for record in list(summary.get("records", []) or [])
    ]


def validate_tolerance_monte_carlo() -> list[ToleranceMonteCarloCheck]:
    rows = _rows_from_layout_info({"surfaces": SURFACES, "settings": SETTINGS})
    editor = _snapshot_editor(rows, SETTINGS)
    summary = editor.run_tolerance_monte_carlo(sample_count=5, seed=2026)
    repeat_summary = editor.run_tolerance_monte_carlo(sample_count=5, seed=2026)
    report_text = editor.tolerance_monte_carlo_report_text(summary)
    comparison = editor.tolerance_worst_sample_comparison(summary)
    comparison_text = editor.tolerance_worst_sample_comparison_report_text(comparison)
    stackup = editor.tolerance_stackup_dashboard(summary)
    stackup_text = editor.tolerance_stackup_dashboard_report_text(stackup)
    compensator = editor.run_tolerance_compensator_sweep(summary, steps=5)
    compensator_text = editor.tolerance_compensator_sweep_report_text(compensator)
    multi_compensator = editor.run_tolerance_multi_compensator_solve(summary, steps=3, passes=2)
    multi_compensator_text = editor.tolerance_multi_compensator_report_text(multi_compensator)
    restricted_editor = _snapshot_editor(_rows_from_layout_info({"surfaces": SURFACES, "settings": SETTINGS}), SETTINGS)
    restricted_editor.set_tolerance_compensator_enabled(1, "k", True)
    restricted_editor.set_tolerance_coupling(1, "k", "shared_mount", sign=1)
    restricted_editor.set_tolerance_coupling(1, "TiltX", "shared_mount", sign=-1)
    restricted_summary = restricted_editor.run_tolerance_monte_carlo(sample_count=3, seed=2026)
    restricted_report = restricted_editor.tolerance_monte_carlo_report_text(restricted_summary)
    restricted_sweep = restricted_editor.run_tolerance_compensator_sweep(restricted_summary, steps=3)
    restricted_multi = restricted_editor.run_tolerance_multi_compensator_solve(restricted_summary, steps=3, passes=1)
    solve_preset = restricted_editor.save_tolerance_solve_preset(
        "K-only tolerance solve",
        sample_count=3,
        seed=2026,
        compensator_steps=3,
        multi_steps=3,
        multi_passes=1,
    )
    preset_settings = dict(SETTINGS)
    preset_settings["tolerance_solve_presets"] = list(restricted_editor.tolerance_solve_presets)
    preset_settings["active_tolerance_solve_preset"] = "K-only tolerance solve"
    roundtrip_editor = _snapshot_editor(
        _rows_from_layout_info({"surfaces": SURFACES, "settings": SETTINGS}),
        preset_settings,
    )
    roundtrip_editor.apply_tolerance_solve_preset("K-only tolerance solve")
    roundtrip_summary = roundtrip_editor.run_tolerance_monte_carlo(
        sample_count=int(solve_preset["sample_count"]),
        seed=int(solve_preset["seed"]),
    )
    roundtrip_sweep = roundtrip_editor.run_tolerance_compensator_sweep(
        roundtrip_summary,
        steps=int(solve_preset["compensator_steps"]),
    )
    overlay = editor.tolerance_nominal_worst_spot_overlay(summary, sample_count=8)
    figure = Figure()
    axis = figure.add_subplot(111)
    editor.analysis_mode = "tolerance_compare"
    editor._plot_tolerance_comparison_analysis(axis, editor.build_system(), editor._current_wavelength())
    mtf_overlay = editor.tolerance_nominal_worst_mtf_overlay(summary, sample_count=32)
    mtf_figure = Figure()
    mtf_axis = mtf_figure.add_subplot(111)
    editor.tolerance_compare_view_var.set("MTF overlay")
    editor._plot_tolerance_comparison_analysis(mtf_axis, editor.build_system(), editor._current_wavelength())
    wfe_overlay = editor.tolerance_nominal_worst_wavefront_overlay(summary)
    wfe_figure = Figure()
    wfe_axis = wfe_figure.add_subplot(111)
    editor.tolerance_compare_view_var.set("Wavefront delta")
    editor._plot_tolerance_comparison_analysis(wfe_axis, editor.build_system(), editor._current_wavelength())
    comparison_records = list(comparison.get("records", []) or [])
    stackup_records = list(stackup.get("records", []) or [])
    records = list(summary.get("records", []) or [])
    variables = list(summary.get("variables", []) or [])
    overlay_nominal = dict(overlay.get("nominal", {}) or {})
    overlay_worst = dict(overlay.get("worst", {}) or {})
    mtf_nominal = dict(mtf_overlay.get("nominal", {}) or {})
    mtf_worst = dict(mtf_overlay.get("worst", {}) or {})
    wfe_delta = np.asarray(wfe_overlay.get("delta_centered_waves", []), dtype=float)
    spot_columns, spot_csv_rows = editor.tolerance_overlay_csv_rows("Spot overlay", overlay)
    mtf_columns, mtf_csv_rows = editor.tolerance_overlay_csv_rows("MTF overlay", mtf_overlay)
    wfe_columns, wfe_csv_rows = editor.tolerance_overlay_csv_rows("Wavefront delta", wfe_overlay)
    stackup_columns, stackup_csv_rows = editor.tolerance_stackup_csv_rows(stackup)
    compensator_columns, compensator_csv_rows = editor.tolerance_compensator_csv_rows(compensator)
    multi_columns, multi_csv_rows = editor.tolerance_multi_compensator_csv_rows(multi_compensator)
    variable_names = {str(variable.get("name", "")) for variable in variables}
    compensator_records = list(compensator.get("records", []) or [])
    best_by_compensator = list(compensator.get("best_by_compensator", []) or [])
    best_compensator = dict(compensator.get("best_compensator", {}) or {})
    multi_records = list(multi_compensator.get("records", []) or [])
    multi_solved = list(multi_compensator.get("solved_variables", []) or [])
    restricted_variables = list(restricted_summary.get("variables", []) or [])
    restricted_sweep_records = list(restricted_sweep.get("records", []) or [])
    restricted_multi_solved = list(restricted_multi.get("solved_variables", []) or [])
    preset_roles = list(solve_preset.get("compensators", []) or [])
    roundtrip_variables = list(roundtrip_summary.get("variables", []) or [])
    roundtrip_sweep_records = list(roundtrip_sweep.get("records", []) or [])
    restricted_records = list(restricted_summary.get("records", []) or [])
    coupled_records = [record for record in restricted_records if str(record.get("kind", "")) != "nominal"]
    coupled_groups = list(restricted_summary.get("coupling_groups", []) or [])
    k_variable = next((dict(variable) for variable in restricted_variables if str(variable.get("parameter", "")).lower() == "k"), {})
    tilt_variable = next((dict(variable) for variable in restricted_variables if str(variable.get("parameter", "")).lower() == "tiltx"), {})
    k_key = restricted_editor._tolerance_variable_key(k_variable) if k_variable else ""
    tilt_key = restricted_editor._tolerance_variable_key(tilt_variable) if tilt_variable else ""
    roundtrip_coupled_groups = list(roundtrip_summary.get("coupling_groups", []) or [])
    first_record = records[0] if records else {}
    sample_records = records[1:]
    merit_values = _total_merit_series(summary)
    repeat_values = _total_merit_series(repeat_summary)

    def normalized_quantile(record: dict[str, object], variable: dict[str, object], key: str) -> float:
        lower = float(variable.get("lower", np.nan))
        upper = float(variable.get("upper", np.nan))
        return (float(record.get(key, np.nan)) - lower) / (upper - lower)

    return [
        ToleranceMonteCarloCheck(
            "layout fixture is native variable breadth example",
            TITLE == "Native Variable Breadth Example",
            TITLE,
        ),
        ToleranceMonteCarloCheck(
            "tolerance variables come from marked optimization/native variables",
            len(variables) == 2 and any("Conic" in name for name in variable_names) and any("Tilt" in name for name in variable_names),
            f"variables={sorted(variable_names)}",
        ),
        ToleranceMonteCarloCheck(
            "nominal plus requested Monte Carlo samples are recorded",
            len(records) == 6 and str(first_record.get("kind", "")) == "nominal",
            f"records={len(records)} first={first_record.get('kind')}",
        ),
        ToleranceMonteCarloCheck(
            "sample values stay inside declared variable bounds",
            all(
                float(variable["lower"]) <= float(record[f"var_s{int(variable['surface_index'])}_{str(variable['parameter']).lower()}"]) <= float(variable["upper"])
                for variable in variables
                for record in sample_records
            ),
            "bounds checked for all sampled variable columns",
        ),
        ToleranceMonteCarloCheck(
            "Monte Carlo sequence is deterministic for a fixed seed",
            len(merit_values) == len(repeat_values) and np.allclose(merit_values, repeat_values, equal_nan=True),
            f"merit={merit_values}",
        ),
        ToleranceMonteCarloCheck(
            "report schema includes total merit statistics and worst sample",
            "Total merit:" in report_text and "Worst sample:" in report_text and "Variables:" in report_text,
            report_text.splitlines()[0],
        ),
        ToleranceMonteCarloCheck(
            "tolerance run does not mutate nominal editable rows",
            abs(float(editor.rows[1].k) - float(SURFACES[1]["k"])) < 1e-12
            and abs(float(editor.rows[1].tilt_x) - float(SURFACES[1]["tilt_x"])) < 1e-12,
            f"k={editor.rows[1].k} tilt_x={editor.rows[1].tilt_x}",
        ),
        ToleranceMonteCarloCheck(
            "worst-sample comparison selects a perturbed valid sample",
            int(comparison.get("perturbed_sample", 0) or 0) > 0
            and any(record.get("category") == "summary" for record in comparison_records),
            f"worst={comparison.get('perturbed_sample')} records={len(comparison_records)}",
        ),
        ToleranceMonteCarloCheck(
            "worst-sample comparison includes variable and operand deltas",
            any(record.get("category") == "variable" and abs(float(record.get("delta", 0.0))) > 0.0 for record in comparison_records)
            and any(record.get("category") == "operand" for record in comparison_records),
            f"categories={sorted({str(record.get('category', '')) for record in comparison_records})}",
        ),
        ToleranceMonteCarloCheck(
            "worst-sample comparison report is copy/export ready",
            "Tolerance Worst-Sample Comparison" in comparison_text
            and "Variables:" in comparison_text
            and "Operands:" in comparison_text,
            comparison_text.splitlines()[0],
        ),
        ToleranceMonteCarloCheck(
            "tolerance stack-up dashboard ranks every tolerance variable",
            len(stackup_records) == len(variables)
            and [int(record.get("rank", 0) or 0) for record in stackup_records] == list(range(1, len(stackup_records) + 1))
            and all(np.isfinite(float(record.get("sample_std", np.nan))) for record in stackup_records),
            f"ranks={[record.get('rank') for record in stackup_records]}",
        ),
        ToleranceMonteCarloCheck(
            "tolerance stack-up report and CSV are export ready",
            "Tolerance Stack-Up Dashboard" in stackup_text
            and len(stackup_csv_rows) == len(stackup_records)
            and "coupling_group" in stackup_columns
            and "contribution_fraction" in stackup_columns
            and "slope_merit_per_unit" in stackup_columns,
            f"rows={len(stackup_csv_rows)} columns={len(stackup_columns)}",
        ),
        ToleranceMonteCarloCheck(
            "compensator sweep starts from the worst tolerance sample",
            int(compensator.get("base_sample", -1) or -1) == int(comparison.get("perturbed_sample", -2) or -2)
            and np.isfinite(float(compensator.get("base_total_merit", np.nan))),
            f"base={compensator.get('base_sample')} merit={compensator.get('base_total_merit')}",
        ),
        ToleranceMonteCarloCheck(
            "compensator sweep evaluates every tolerance variable",
            len(best_by_compensator) == len(variables)
            and {str(record.get("compensator", "")) for record in best_by_compensator} == variable_names,
            f"best={sorted(str(record.get('compensator', '')) for record in best_by_compensator)}",
        ),
        ToleranceMonteCarloCheck(
            "compensator sweep can only improve or match the worst merit",
            bool(best_compensator)
            and float(best_compensator.get("total_merit", np.inf)) <= float(compensator.get("base_total_merit", -np.inf)) + 1e-9
            and np.isfinite(float(best_compensator.get("improvement_vs_worst", np.nan))),
            (
                f"best={best_compensator.get('compensator')} "
                f"value={best_compensator.get('value')} "
                f"improvement={best_compensator.get('improvement_vs_worst')}"
            ),
        ),
        ToleranceMonteCarloCheck(
            "compensator sweep report and CSV are export ready",
            "Tolerance Compensator Sweep" in compensator_text
            and len(compensator_csv_rows) == len(compensator_records)
            and "coupling_group" in compensator_columns
            and "improvement_vs_worst" in compensator_columns,
            f"rows={len(compensator_csv_rows)} columns={len(compensator_columns)}",
        ),
        ToleranceMonteCarloCheck(
            "multi-compensator solve starts from the same worst sample",
            int(multi_compensator.get("base_sample", -1) or -1) == int(comparison.get("perturbed_sample", -2) or -2)
            and np.isfinite(float(multi_compensator.get("base_total_merit", np.nan))),
            f"base={multi_compensator.get('base_sample')} merit={multi_compensator.get('base_total_merit')}",
        ),
        ToleranceMonteCarloCheck(
            "multi-compensator solve emits one solved value per tolerance variable",
            len(multi_solved) == len(variables)
            and {str(record.get("name", "")) for record in multi_solved} == variable_names,
            f"solved={sorted(str(record.get('name', '')) for record in multi_solved)}",
        ),
        ToleranceMonteCarloCheck(
            "multi-compensator solve does not worsen the worst merit",
            float(multi_compensator.get("final_total_merit", np.inf)) <= float(multi_compensator.get("base_total_merit", -np.inf)) + 1e-9
            and np.isfinite(float(multi_compensator.get("improvement_vs_worst", np.nan))),
            (
                f"final={multi_compensator.get('final_total_merit')} "
                f"improvement={multi_compensator.get('improvement_vs_worst')}"
            ),
        ),
        ToleranceMonteCarloCheck(
            "multi-compensator solve report and CSV are export ready",
            "Tolerance Multi-Compensator Solve" in multi_compensator_text
            and len(multi_csv_rows) == len(multi_records)
            and "accepted" in multi_columns
            and "coupling_group" in multi_columns
            and "improvement_vs_previous" in multi_columns,
            f"rows={len(multi_csv_rows)} columns={len(multi_columns)}",
        ),
        ToleranceMonteCarloCheck(
            "coupled tolerance variables share one sampled manufacturing DOF",
            bool(k_variable)
            and bool(tilt_variable)
            and any(str(group.get("group", "")) == "shared_mount" and int(group.get("variable_count", 0) or 0) == 2 for group in coupled_groups)
            and str(k_variable.get("coupling_group", "")) == "shared_mount"
            and str(tilt_variable.get("coupling_group", "")) == "shared_mount"
            and int(k_variable.get("coupling_sign", 0) or 0) == 1
            and int(tilt_variable.get("coupling_sign", 0) or 0) == -1
            and all(
                abs(
                    normalized_quantile(record, k_variable, k_key)
                    + normalized_quantile(record, tilt_variable, tilt_key)
                    - 1.0
                )
                <= 1e-12
                for record in coupled_records
            ),
            f"groups={coupled_groups} k={k_variable.get('coupling_sign')} tilt={tilt_variable.get('coupling_sign')}",
        ),
        ToleranceMonteCarloCheck(
            "coupling metadata is reported and exported with tolerance products",
            "coupling=shared_mount" in restricted_report
            and "coupling=-shared_mount" in restricted_report
            and all("coupling_group" in record for record in restricted_sweep_records)
            and all("coupling_group" in record for record in restricted_multi_solved),
            f"report_lines={[line for line in restricted_report.splitlines() if 'coupling=' in line]}",
        ),
        ToleranceMonteCarloCheck(
            "explicit compensator metadata separates tolerance-only variables",
            len(restricted_variables) == 2
            and sum(1 for variable in restricted_variables if bool(variable.get("compensator", True))) == 1
            and any(bool(variable.get("compensator", False)) and str(variable.get("parameter", "")).lower() == "k" for variable in restricted_variables),
            f"roles={[str(variable.get('parameter')) + ':' + str(variable.get('compensator')) for variable in restricted_variables]}",
        ),
        ToleranceMonteCarloCheck(
            "single-compensator sweep respects eligibility metadata",
            len({str(record.get("parameter", "")) for record in restricted_sweep_records}) == 1
            and {str(record.get("parameter", "")).lower() for record in restricted_sweep_records} == {"k"},
            f"parameters={sorted({str(record.get('parameter', '')) for record in restricted_sweep_records})}",
        ),
        ToleranceMonteCarloCheck(
            "multi-compensator solve holds tolerance-only variables fixed",
            any(not bool(record.get("compensator", True)) for record in restricted_multi_solved)
            and all(
                abs(float(record.get("solved", np.nan)) - float(record.get("worst", np.nan))) <= 1e-12
                for record in restricted_multi_solved
                if not bool(record.get("compensator", True))
            ),
            f"solved={[(record.get('parameter'), record.get('compensator')) for record in restricted_multi_solved]}",
        ),
        ToleranceMonteCarloCheck(
            "tolerance solve presets persist run defaults and variable roles",
            str(solve_preset.get("name", "")) == "K-only tolerance solve"
            and int(solve_preset.get("sample_count", 0) or 0) == 3
            and int(solve_preset.get("seed", 0) or 0) == 2026
            and str(solve_preset.get("coupling_policy", "")) == "explicit"
            and len(preset_roles) == 2
            and sum(1 for record in preset_roles if bool(record.get("compensator", True))) == 1
            and sum(1 for record in preset_roles if str(record.get("coupling_group", "")) == "shared_mount") == 2,
            f"preset={solve_preset.get('name')} roles={[(record.get('parameter'), record.get('compensator')) for record in preset_roles]}",
        ),
        ToleranceMonteCarloCheck(
            "applying a saved tolerance solve preset restores compensator eligibility and coupling",
            len(roundtrip_variables) == 2
            and sum(1 for variable in roundtrip_variables if bool(variable.get("compensator", True))) == 1
            and {str(record.get("parameter", "")).lower() for record in roundtrip_sweep_records} == {"k"}
            and any(str(group.get("group", "")) == "shared_mount" and int(group.get("variable_count", 0) or 0) == 2 for group in roundtrip_coupled_groups),
            (
                f"roles={[(variable.get('parameter'), variable.get('compensator')) for variable in roundtrip_variables]} "
                f"sweep={sorted({str(record.get('parameter', '')) for record in roundtrip_sweep_records})} "
                f"groups={roundtrip_coupled_groups}"
            ),
        ),
        ToleranceMonteCarloCheck(
            "nominal-vs-worst spot overlay produces finite spot clouds",
            int(overlay_nominal.get("count", 0) or 0) > 0
            and int(overlay_worst.get("count", 0) or 0) > 0
            and np.isfinite(float(overlay_nominal.get("rms_radius", np.nan)))
            and np.isfinite(float(overlay_worst.get("rms_radius", np.nan)))
            and int(overlay.get("worst_sample", -1) or -1) == int(comparison.get("perturbed_sample", -2) or -2),
            (
                f"worst={overlay.get('worst_sample')} "
                f"rms={overlay_nominal.get('rms_radius')}/{overlay_worst.get('rms_radius')}"
            ),
        ),
        ToleranceMonteCarloCheck(
            "TolCmp analysis button path renders the overlay axes",
            len(axis.collections) >= 2 and axis.axison and "Tolerance" in axis.get_title(),
            f"title={axis.get_title()} collections={len(axis.collections)}",
        ),
        ToleranceMonteCarloCheck(
            "nominal-vs-worst MTF overlay produces finite curves",
            np.asarray(mtf_nominal.get("plot_freq", [])).size >= 2
            and np.asarray(mtf_worst.get("plot_freq", [])).size >= 2
            and np.isfinite(float(mtf_overlay.get("nominal_selected_value", np.nan)))
            and np.isfinite(float(mtf_overlay.get("worst_selected_value", np.nan))),
            (
                f"target={mtf_overlay.get('target_frequency')} "
                f"mtf={mtf_overlay.get('nominal_selected_value')}/{mtf_overlay.get('worst_selected_value')}"
            ),
        ),
        ToleranceMonteCarloCheck(
            "TolCmp MTF selector renders the MTF axes",
            len(mtf_axis.lines) >= 2 and mtf_axis.axison and "MTF" in mtf_axis.get_title(),
            f"title={mtf_axis.get_title()} lines={len(mtf_axis.lines)}",
        ),
        ToleranceMonteCarloCheck(
            "nominal-vs-worst wavefront delta produces finite WFE samples",
            wfe_delta.size >= 4
            and np.isfinite(float(wfe_overlay.get("delta_rms_waves", np.nan)))
            and np.isfinite(float(wfe_overlay.get("delta_pv_waves", np.nan))),
            (
                f"rms={wfe_overlay.get('delta_rms_waves')} "
                f"pv={wfe_overlay.get('delta_pv_waves')} samples={wfe_delta.size}"
            ),
        ),
        ToleranceMonteCarloCheck(
            "TolCmp wavefront selector renders the WFE delta axes",
            wfe_axis.axison and "Wavefront" in wfe_axis.get_title(),
            f"title={wfe_axis.get_title()} collections={len(wfe_axis.collections)}",
        ),
        ToleranceMonteCarloCheck(
            "TolCmp overlay CSV schemas export spot, MTF, and WFE rows",
            len(spot_csv_rows) > 0
            and len(mtf_csv_rows) > 0
            and len(wfe_csv_rows) > 0
            and "nominal_x_mm" in spot_columns
            and "frequency_cy_per_mm" in mtf_columns
            and "delta_centered_waves" in wfe_columns,
            f"rows={len(spot_csv_rows)}/{len(mtf_csv_rows)}/{len(wfe_csv_rows)}",
        ),
    ]


def _print_table(checks: list[ToleranceMonteCarloCheck]) -> None:
    print("KrakenOS tolerance Monte Carlo validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate tolerance Monte Carlo report workflow.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_tolerance_monte_carlo()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
