"""Tolerance Monte Carlo and compensator analysis service."""

from __future__ import annotations

from typing import Any

import re

import numpy as np


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class ToleranceAnalysisService:
    """Run tolerance Monte Carlo, compensator solves, and worst-sample comparisons."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def run_tolerance_monte_carlo(
        self,
        *,
        sample_count: int = 25,
        seed: int = 12345,
    ) -> dict[str, object]:
        le = _layout_module()
        MeritEvaluator = le.MeritEvaluator
        MTFAtFrequencyOperand = le.MTFAtFrequencyOperand
        TOLERANCE_COMPARE_VIEW_VALUES = le.TOLERANCE_COMPARE_VIEW_VALUES
        TOLERANCE_COMPENSATORS_ADVANCED_ATTR = le.TOLERANCE_COMPENSATORS_ADVANCED_ATTR
        TOLERANCE_COUPLING_ADVANCED_ATTR = le.TOLERANCE_COUPLING_ADVANCED_ATTR
        TOLERANCE_MANUFACTURING_ADVANCED_ATTR = le.TOLERANCE_MANUFACTURING_ADVANCED_ATTR
        VARIABLE_REGISTRY = le.VARIABLE_REGISTRY
        _native_variable_matches = le._native_variable_matches
        sample_count = max(1, int(sample_count))
        seed = int(seed)
        variables = self._build_optimization_variables()
        if not variables:
            raise RuntimeError("No tolerance variables are marked. Mark variable cells or set native Var/VarBounds first.")
        merit_function, operand_labels = self._build_tolerance_merit_function()
        if not merit_function.operands:
            raise RuntimeError("No merit operands are available for tolerance reporting.")

        system = self.build_system()
        has_mtf_operand = any(isinstance(operand, MTFAtFrequencyOperand) for operand in merit_function.operands)
        evaluator = MeritEvaluator(
            system.SDT,
            setup=system.SETUP,
            merit_function=merit_function,
            mtf_worker_count=self._mtf_worker_count(self._current_ray_count()) if has_mtf_operand else 1,
        )
        nominal = [
            float(self._optimization_value_from_row(self.rows[variable.surface_index], variable))
            for variable in variables
        ]
        couplings = [self._tolerance_variable_coupling(variable) for variable in variables]
        manufacturing = [self._tolerance_variable_manufacturing(variable) for variable in variables]
        rng = np.random.default_rng(seed)
        sample_vectors = [np.asarray(nominal, dtype=float)]
        for _sample_index in range(sample_count):
            group_quantiles: dict[str, float] = {}
            values: list[float] = []
            for variable, coupling in zip(variables, couplings):
                lower = float(variable.lower_bound)
                upper = float(variable.upper_bound)
                if lower > upper:
                    lower, upper = upper, lower
                group = str(coupling.get("group", "") or "").strip()
                if group:
                    quantile = group_quantiles.setdefault(group, float(rng.uniform(0.0, 1.0)))
                    if int(coupling.get("sign", 1) or 1) < 0:
                        quantile = 1.0 - quantile
                    values.append(float(lower + quantile * (upper - lower)))
                else:
                    values.append(float(rng.uniform(lower, upper)))
            sample_vectors.append(np.asarray(values, dtype=float))

        records: list[dict[str, object]] = []
        for sample_index, values in enumerate(sample_vectors):
            result = evaluator.evaluate(variables, values)
            record: dict[str, object] = {
                "sample": sample_index,
                "kind": "nominal" if sample_index == 0 else "monte_carlo",
                "valid": bool(result.valid),
                "total_merit": float(result.total),
                "message": str(result.message),
            }
            for variable, value in zip(variables, values):
                key = f"var_s{int(variable.surface_index)}_{str(variable.parameter).lower()}"
                record[key] = float(value)
            for operand in result.operands:
                key = re.sub(r"[^a-z0-9]+", "_", str(operand.name).strip().lower()).strip("_") or "operand"
                record[f"{key}_value"] = float(operand.value)
                record[f"{key}_weighted"] = float(operand.weighted)
                record[f"{key}_residual"] = float(operand.residual)
            records.append(record)

        valid_records = [record for record in records if bool(record.get("valid"))]
        variable_records = [
            {
                "name": variable.normalized_name(),
                "surface_index": int(variable.surface_index),
                "parameter": str(variable.parameter),
                "nominal": float(nominal[index]),
                "lower": float(variable.lower_bound),
                "upper": float(variable.upper_bound),
                "compensator": self._tolerance_variable_compensator_enabled(variable),
                **(
                    {
                        "coupling_group": str(couplings[index].get("group", "")),
                        "coupling_sign": int(couplings[index].get("sign", 1) or 1),
                    }
                    if couplings[index]
                    else {}
                ),
                **self._tolerance_manufacturing_record_fields(manufacturing[index]),
            }
            for index, variable in enumerate(variables)
        ]
        coupling_groups = sorted(
            {
                str(record.get("coupling_group", "") or "")
                for record in variable_records
                if str(record.get("coupling_group", "") or "").strip()
            }
        )
        total_values = [float(record.get("total_merit", np.nan)) for record in records if bool(record.get("valid"))]
        worst_record = max(valid_records, key=lambda record: float(record.get("total_merit", -np.inf)), default=None)
        summary = {
            "sample_count": sample_count,
            "seed": seed,
            "variables": variable_records,
            "coupling_groups": [
                {
                    "group": group,
                    "variable_count": sum(1 for record in variable_records if str(record.get("coupling_group", "")) == group),
                }
                for group in coupling_groups
            ],
            "operand_labels": operand_labels,
            "records": records,
            "valid_count": len(valid_records),
            "invalid_count": len(records) - len(valid_records),
            "total_merit_stats": self._finite_stats(total_values),
            "worst_sample": None if worst_record is None else int(worst_record.get("sample", -1)),
            "worst_total_merit": np.nan if worst_record is None else float(worst_record.get("total_merit", np.nan)),
        }
        self._last_tolerance_monte_carlo_records = records
        self._last_tolerance_monte_carlo_summary = summary
        return summary

    def apply_tolerance_solve_preset(self, preset_or_name: str | dict[str, object]) -> dict[str, object]:
        le = _layout_module()
        MeritEvaluator = le.MeritEvaluator
        MTFAtFrequencyOperand = le.MTFAtFrequencyOperand
        TOLERANCE_COMPARE_VIEW_VALUES = le.TOLERANCE_COMPARE_VIEW_VALUES
        TOLERANCE_COMPENSATORS_ADVANCED_ATTR = le.TOLERANCE_COMPENSATORS_ADVANCED_ATTR
        TOLERANCE_COUPLING_ADVANCED_ATTR = le.TOLERANCE_COUPLING_ADVANCED_ATTR
        TOLERANCE_MANUFACTURING_ADVANCED_ATTR = le.TOLERANCE_MANUFACTURING_ADVANCED_ATTR
        VARIABLE_REGISTRY = le.VARIABLE_REGISTRY
        _native_variable_matches = le._native_variable_matches
        if isinstance(preset_or_name, dict):
            preset = self._normalize_tolerance_solve_preset(preset_or_name)
        else:
            preset = self._tolerance_solve_preset_by_name(str(preset_or_name)) or {}
        if not preset:
            raise ValueError("Tolerance solve preset was not found.")
        self.active_tolerance_solve_preset_name = str(preset.get("name", ""))
        compare_view = str(preset.get("tolerance_compare_view", "") or "").strip()
        if compare_view in TOLERANCE_COMPARE_VIEW_VALUES and "tolerance_compare_view_var" in self.__dict__:
            self.tolerance_compare_view_var.set(compare_view)
        selected_operands = [str(label) for label in list(preset.get("selected_operands", []) or [])]
        self._set_selected_operand_labels(selected_operands)
        operand_settings = preset.get("operands", {})
        if isinstance(operand_settings, dict):
            for label, payload in operand_settings.items():
                if not isinstance(payload, dict):
                    continue
                for key, attr_name in (
                    ("weight", "operand_weight_vars"),
                    ("target", "operand_target_vars"),
                    ("wavelength", "operand_wavelength_vars"),
                    ("field", "operand_field_vars"),
                    ("field_x", "operand_field_x_vars"),
                    ("field_y", "operand_field_y_vars"),
                    ("surface", "operand_surface_vars"),
                    ("aperture_type", "operand_aperture_type_vars"),
                    ("aperture_value", "operand_aperture_value_vars"),
                    ("frequency", "operand_frequency_vars"),
                    ("mtf_mode", "operand_mtf_mode_vars"),
                    ("mtf_algorithm", "operand_mtf_algorithm_vars"),
                ):
                    mapping = getattr(self, attr_name, {}) or {}
                    var = mapping.get(label)
                    if var is not None and key in payload:
                        var.set(str(payload[key]).strip())
        compensator_records = list(preset.get("compensators", []) or [])
        if str(preset.get("compensator_policy", "explicit")) == "explicit" or compensator_records:
            roles: dict[tuple[int, str], bool] = {}
            for record in compensator_records:
                if not isinstance(record, dict):
                    continue
                try:
                    surface_index = int(record.get("surface_index", -1))
                except Exception:
                    continue
                parameter = str(record.get("parameter", "") or "").strip()
                if surface_index < 0 or not parameter:
                    continue
                roles[(surface_index, parameter.lower())] = self._tolerance_preset_bool(
                    record.get("compensator", record.get("enabled", True)),
                    True,
                )
            for surface_index, row in enumerate(self.rows):
                enabled_names: list[str] = []
                touched = False
                for spec in VARIABLE_REGISTRY.values():
                    if not spec.is_supported(row) or not self._variable_enabled_for_row(row, spec):
                        continue
                    key = (surface_index, str(spec.parameter).lower())
                    if key not in roles:
                        continue
                    touched = True
                    if roles[key]:
                        enabled_names.append(str(spec.parameter))
                if touched:
                    row.advanced = dict(row.advanced or {})
                    row.advanced[TOLERANCE_COMPENSATORS_ADVANCED_ATTR] = enabled_names
        if str(preset.get("coupling_policy", "preserve")) == "explicit":
            couplings: dict[tuple[int, str], tuple[str, int]] = {}
            for record in compensator_records:
                if not isinstance(record, dict):
                    continue
                try:
                    surface_index = int(record.get("surface_index", -1))
                except Exception:
                    continue
                parameter = str(record.get("parameter", "") or "").strip()
                if surface_index < 0 or not parameter:
                    continue
                group = str(record.get("coupling_group", "") or "").strip()
                sign = self._tolerance_coupling_sign(record.get("coupling_sign", 1))
                couplings[(surface_index, parameter.lower())] = (group, sign)
            for surface_index, row in enumerate(self.rows):
                row_couplings = self._row_tolerance_couplings(row)
                touched = False
                for spec in VARIABLE_REGISTRY.values():
                    if not spec.is_supported(row) or not self._variable_enabled_for_row(row, spec):
                        continue
                    key = (surface_index, str(spec.parameter).lower())
                    if key not in couplings:
                        continue
                    touched = True
                    for candidate in list(row_couplings):
                        if _native_variable_matches(candidate, spec.parameter):
                            row_couplings.pop(candidate, None)
                    group, sign = couplings[key]
                    if group:
                        row_couplings[str(spec.parameter)] = {"group": group, "sign": sign}
                if touched:
                    row.advanced = dict(row.advanced or {})
                    if row_couplings:
                        row.advanced[TOLERANCE_COUPLING_ADVANCED_ATTR] = row_couplings
                    else:
                        row.advanced.pop(TOLERANCE_COUPLING_ADVANCED_ATTR, None)
        if str(preset.get("manufacturing_policy", "preserve")) == "explicit":
            manufacturing_records: dict[tuple[int, str], dict[str, object]] = {}
            for record in compensator_records:
                if not isinstance(record, dict):
                    continue
                try:
                    surface_index = int(record.get("surface_index", -1))
                except Exception:
                    continue
                parameter = str(record.get("parameter", "") or "").strip()
                if surface_index < 0 or not parameter:
                    continue
                metadata = self._tolerance_manufacturing_record_fields(record)
                manufacturing_records[(surface_index, parameter.lower())] = metadata
            for surface_index, row in enumerate(self.rows):
                row_records = self._normalize_tolerance_manufacturing_payload(
                    (row.advanced or {}).get(TOLERANCE_MANUFACTURING_ADVANCED_ATTR)
                )
                touched = False
                for spec in VARIABLE_REGISTRY.values():
                    if not spec.is_supported(row) or not self._variable_enabled_for_row(row, spec):
                        continue
                    key = (surface_index, str(spec.parameter).lower())
                    if key not in manufacturing_records:
                        continue
                    touched = True
                    for candidate in list(row_records):
                        if _native_variable_matches(candidate, spec.parameter):
                            row_records.pop(candidate, None)
                    metadata = manufacturing_records[key]
                    if metadata:
                        row_records[str(spec.parameter)] = {
                            "source_type": str(metadata.get("manufacturing_source_type", "") or ""),
                            "source_id": str(metadata.get("manufacturing_source_id", "") or ""),
                            "tags": self._tolerance_manufacturing_tags(metadata.get("manufacturing_tags", "")),
                            "note": str(metadata.get("manufacturing_note", "") or ""),
                        }
                if touched:
                    row.advanced = dict(row.advanced or {})
                    if row_records:
                        row.advanced[TOLERANCE_MANUFACTURING_ADVANCED_ATTR] = row_records
                    else:
                        row.advanced.pop(TOLERANCE_MANUFACTURING_ADVANCED_ATTR, None)
        return dict(preset)

    def run_tolerance_compensator_sweep(
        self,
        summary: dict[str, object] | None = None,
        *,
        steps: int = 9,
    ) -> dict[str, object]:
        le = _layout_module()
        MeritEvaluator = le.MeritEvaluator
        MTFAtFrequencyOperand = le.MTFAtFrequencyOperand
        TOLERANCE_COMPARE_VIEW_VALUES = le.TOLERANCE_COMPARE_VIEW_VALUES
        TOLERANCE_COMPENSATORS_ADVANCED_ATTR = le.TOLERANCE_COMPENSATORS_ADVANCED_ATTR
        TOLERANCE_COUPLING_ADVANCED_ATTR = le.TOLERANCE_COUPLING_ADVANCED_ATTR
        TOLERANCE_MANUFACTURING_ADVANCED_ATTR = le.TOLERANCE_MANUFACTURING_ADVANCED_ATTR
        VARIABLE_REGISTRY = le.VARIABLE_REGISTRY
        _native_variable_matches = le._native_variable_matches
        steps = max(3, min(101, int(steps)))
        context = self._tolerance_nominal_worst_context(summary)
        variable_records = [dict(item) for item in list(context["variable_records"])]
        if not variable_records:
            raise RuntimeError("Tolerance Monte Carlo has no variables to sweep.")
        base_system = context["base_system"]
        variables = self._tolerance_optical_variables_from_records(variable_records)
        compensator_indices = self._tolerance_compensator_indices_from_records(variable_records)
        if not compensator_indices:
            raise RuntimeError("No tolerance compensators are enabled. Add ToleranceCompensators metadata to at least one marked variable.")
        nominal_values = np.asarray(
            self._tolerance_sample_values_from_record(dict(context["nominal_record"]), variable_records),
            dtype=float,
        )
        worst_record = dict(context["worst_record"])
        worst_values = np.asarray(self._tolerance_sample_values_from_record(worst_record, variable_records), dtype=float)
        worst_total = self._tolerance_record_float(worst_record, "total_merit")
        merit_function, operand_labels = self._build_tolerance_merit_function()
        if not merit_function.operands:
            raise RuntimeError("No merit operands are available for tolerance compensator sweep.")
        has_mtf_operand = any(isinstance(operand, MTFAtFrequencyOperand) for operand in merit_function.operands)
        evaluator = MeritEvaluator(
            base_system.SDT,
            setup=base_system.SETUP,
            merit_function=merit_function,
            mtf_worker_count=self._mtf_worker_count(self._current_ray_count()) if has_mtf_operand else 1,
        )

        records: list[dict[str, object]] = []
        for variable_index in compensator_indices:
            variable = variables[variable_index]
            variable_record = variable_records[variable_index]
            lower = float(variable.lower_bound)
            upper = float(variable.upper_bound)
            if not np.isfinite(lower) or not np.isfinite(upper):
                continue
            if lower > upper:
                lower, upper = upper, lower
            if abs(upper - lower) <= 1e-18:
                candidate_values = [float(lower)]
            else:
                candidate_values = self._tolerance_unique_sweep_values(
                    np.linspace(lower, upper, steps),
                    [nominal_values[variable_index], worst_values[variable_index]],
                )
            key = self._tolerance_variable_key(variable_record)
            for step_index, value in enumerate(candidate_values):
                test_values = worst_values.copy()
                test_values[variable_index] = float(value)
                result = evaluator.evaluate(variables, test_values)
                total_merit = float(result.total)
                record: dict[str, object] = {
                    "compensator": variable.normalized_name(),
                    "compensator_key": key,
                    "surface_index": int(variable.surface_index),
                    "parameter": str(variable.parameter),
                    "coupling_group": str(variable_record.get("coupling_group", "") or ""),
                    "coupling_sign": int(variable_record.get("coupling_sign", 1) or 1),
                    "manufacturing_source_type": str(variable_record.get("manufacturing_source_type", "") or ""),
                    "manufacturing_source_id": str(variable_record.get("manufacturing_source_id", "") or ""),
                    "manufacturing_tags": str(variable_record.get("manufacturing_tags", "") or ""),
                    "manufacturing_note": str(variable_record.get("manufacturing_note", "") or ""),
                    "step": int(step_index),
                    "value": float(value),
                    "nominal_value": float(nominal_values[variable_index]),
                    "worst_value": float(worst_values[variable_index]),
                    "lower": lower,
                    "upper": upper,
                    "base_sample": int(context["worst_sample"]),
                    "valid": bool(result.valid),
                    "total_merit": total_merit,
                    "worst_total_merit": worst_total,
                    "delta_vs_worst": total_merit - worst_total if np.isfinite(total_merit) and np.isfinite(worst_total) else np.nan,
                    "improvement_vs_worst": worst_total - total_merit if np.isfinite(total_merit) and np.isfinite(worst_total) else np.nan,
                    "is_nominal_value": abs(float(value) - float(nominal_values[variable_index])) <= 1e-12,
                    "is_worst_value": abs(float(value) - float(worst_values[variable_index])) <= 1e-12,
                    "message": str(result.message),
                }
                for operand in result.operands:
                    operand_key = re.sub(r"[^a-z0-9]+", "_", str(operand.name).strip().lower()).strip("_") or "operand"
                    record[f"{operand_key}_value"] = float(operand.value)
                    record[f"{operand_key}_weighted"] = float(operand.weighted)
                    record[f"{operand_key}_residual"] = float(operand.residual)
                records.append(record)

        valid_records = [record for record in records if bool(record.get("valid"))]
        best_record = min(valid_records, key=lambda record: self._tolerance_record_float(record, "total_merit", np.inf), default=None)
        best_by_compensator: list[dict[str, object]] = []
        for key in sorted({str(record.get("compensator_key", "")) for record in records}):
            candidates = [record for record in valid_records if str(record.get("compensator_key", "")) == key]
            if candidates:
                best_by_compensator.append(min(candidates, key=lambda record: self._tolerance_record_float(record, "total_merit", np.inf)))
        summary_out = {
            "kind": "worst_sample_compensator_sweep",
            "steps": steps,
            "variables": variable_records,
            "operand_labels": operand_labels,
            "records": records,
            "best_by_compensator": best_by_compensator,
            "compensator_count": len(compensator_indices),
            "valid_count": len(valid_records),
            "invalid_count": len(records) - len(valid_records),
            "base_sample": int(context["worst_sample"]),
            "base_total_merit": worst_total,
            "best_compensator": None if best_record is None else dict(best_record),
            "best_total_merit": np.nan if best_record is None else self._tolerance_record_float(best_record, "total_merit"),
            "best_improvement_vs_worst": np.nan if best_record is None else self._tolerance_record_float(best_record, "improvement_vs_worst"),
            "comparison": context["comparison"],
        }
        self._last_tolerance_compensator_records = records
        self._last_tolerance_compensator_summary = summary_out
        return summary_out

    def run_tolerance_multi_compensator_solve(
        self,
        summary: dict[str, object] | None = None,
        *,
        steps: int = 5,
        passes: int = 2,
    ) -> dict[str, object]:
        le = _layout_module()
        MeritEvaluator = le.MeritEvaluator
        MTFAtFrequencyOperand = le.MTFAtFrequencyOperand
        TOLERANCE_COMPARE_VIEW_VALUES = le.TOLERANCE_COMPARE_VIEW_VALUES
        TOLERANCE_COMPENSATORS_ADVANCED_ATTR = le.TOLERANCE_COMPENSATORS_ADVANCED_ATTR
        TOLERANCE_COUPLING_ADVANCED_ATTR = le.TOLERANCE_COUPLING_ADVANCED_ATTR
        TOLERANCE_MANUFACTURING_ADVANCED_ATTR = le.TOLERANCE_MANUFACTURING_ADVANCED_ATTR
        VARIABLE_REGISTRY = le.VARIABLE_REGISTRY
        _native_variable_matches = le._native_variable_matches
        steps = max(3, min(51, int(steps)))
        passes = max(1, min(20, int(passes)))
        context = self._tolerance_nominal_worst_context(summary)
        variable_records = [dict(item) for item in list(context["variable_records"])]
        if not variable_records:
            raise RuntimeError("Tolerance Monte Carlo has no variables to solve.")
        base_system = context["base_system"]
        variables = self._tolerance_optical_variables_from_records(variable_records)
        compensator_indices = self._tolerance_compensator_indices_from_records(variable_records)
        if not compensator_indices:
            raise RuntimeError("No tolerance compensators are enabled. Add ToleranceCompensators metadata to at least one marked variable.")
        nominal_values = np.asarray(
            self._tolerance_sample_values_from_record(dict(context["nominal_record"]), variable_records),
            dtype=float,
        )
        worst_record = dict(context["worst_record"])
        worst_values = np.asarray(self._tolerance_sample_values_from_record(worst_record, variable_records), dtype=float)
        base_total = self._tolerance_record_float(worst_record, "total_merit")
        merit_function, operand_labels = self._build_tolerance_merit_function()
        if not merit_function.operands:
            raise RuntimeError("No merit operands are available for tolerance multi-compensator solve.")
        has_mtf_operand = any(isinstance(operand, MTFAtFrequencyOperand) for operand in merit_function.operands)
        evaluator = MeritEvaluator(
            base_system.SDT,
            setup=base_system.SETUP,
            merit_function=merit_function,
            mtf_worker_count=self._mtf_worker_count(self._current_ray_count()) if has_mtf_operand else 1,
        )

        current_values = worst_values.copy()
        current_result = evaluator.evaluate(variables, current_values)
        current_total = float(current_result.total)
        records: list[dict[str, object]] = []
        accepted_records: list[dict[str, object]] = []
        pass_summaries: list[dict[str, object]] = []

        for pass_index in range(1, passes + 1):
            pass_start_total = float(current_total)
            improved_this_pass = False
            accepted_this_pass = 0
            for variable_index in compensator_indices:
                variable = variables[variable_index]
                variable_record = variable_records[variable_index]
                lower = float(variable.lower_bound)
                upper = float(variable.upper_bound)
                if not np.isfinite(lower) or not np.isfinite(upper):
                    continue
                if lower > upper:
                    lower, upper = upper, lower
                if abs(upper - lower) <= 1e-18:
                    candidate_values = [float(lower)]
                else:
                    candidate_values = self._tolerance_unique_sweep_values(
                        np.linspace(lower, upper, steps),
                        [nominal_values[variable_index], worst_values[variable_index], current_values[variable_index]],
                    )
                key = self._tolerance_variable_key(variable_record)
                previous_value = float(current_values[variable_index])
                best_record: dict[str, object] | None = None
                best_values = current_values.copy()
                best_total = float(current_total)
                for step_index, value in enumerate(candidate_values):
                    test_values = current_values.copy()
                    test_values[variable_index] = float(value)
                    result = evaluator.evaluate(variables, test_values)
                    total_merit = float(result.total)
                    record: dict[str, object] = {
                        "pass": int(pass_index),
                        "compensator": variable.normalized_name(),
                        "compensator_key": key,
                        "surface_index": int(variable.surface_index),
                        "parameter": str(variable.parameter),
                        "coupling_group": str(variable_record.get("coupling_group", "") or ""),
                        "coupling_sign": int(variable_record.get("coupling_sign", 1) or 1),
                        "manufacturing_source_type": str(variable_record.get("manufacturing_source_type", "") or ""),
                        "manufacturing_source_id": str(variable_record.get("manufacturing_source_id", "") or ""),
                        "manufacturing_tags": str(variable_record.get("manufacturing_tags", "") or ""),
                        "manufacturing_note": str(variable_record.get("manufacturing_note", "") or ""),
                        "step": int(step_index),
                        "value": float(value),
                        "previous_value": previous_value,
                        "nominal_value": float(nominal_values[variable_index]),
                        "worst_value": float(worst_values[variable_index]),
                        "lower": lower,
                        "upper": upper,
                        "base_sample": int(context["worst_sample"]),
                        "valid": bool(result.valid),
                        "accepted": False,
                        "total_merit": total_merit,
                        "previous_total_merit": float(current_total),
                        "base_total_merit": base_total,
                        "delta_vs_previous": total_merit - current_total if np.isfinite(total_merit) and np.isfinite(current_total) else np.nan,
                        "improvement_vs_previous": current_total - total_merit if np.isfinite(total_merit) and np.isfinite(current_total) else np.nan,
                        "improvement_vs_worst": base_total - total_merit if np.isfinite(total_merit) and np.isfinite(base_total) else np.nan,
                        "is_nominal_value": abs(float(value) - float(nominal_values[variable_index])) <= 1e-12,
                        "is_worst_value": abs(float(value) - float(worst_values[variable_index])) <= 1e-12,
                        "message": str(result.message),
                    }
                    for value_index, solve_variable in enumerate(variables):
                        record[f"solve_s{int(solve_variable.surface_index)}_{str(solve_variable.parameter).lower()}"] = float(test_values[value_index])
                    for operand in result.operands:
                        operand_key = re.sub(r"[^a-z0-9]+", "_", str(operand.name).strip().lower()).strip("_") or "operand"
                        record[f"{operand_key}_value"] = float(operand.value)
                        record[f"{operand_key}_weighted"] = float(operand.weighted)
                        record[f"{operand_key}_residual"] = float(operand.residual)
                    records.append(record)
                    if bool(result.valid) and total_merit < best_total - 1e-12:
                        best_total = total_merit
                        best_values = test_values
                        best_record = record
                if best_record is not None:
                    best_record["accepted"] = True
                    accepted_records.append(dict(best_record))
                    current_values = best_values
                    current_total = best_total
                    improved_this_pass = True
                    accepted_this_pass += 1
            pass_summaries.append(
                {
                    "pass": int(pass_index),
                    "start_total_merit": pass_start_total,
                    "end_total_merit": float(current_total),
                    "improvement": pass_start_total - float(current_total) if np.isfinite(pass_start_total) and np.isfinite(current_total) else np.nan,
                    "accepted_steps": accepted_this_pass,
                }
            )
            if not improved_this_pass:
                break

        solved_variables = []
        for index, (variable, variable_record) in enumerate(zip(variables, variable_records)):
            solved_variables.append(
                {
                    "name": variable.normalized_name(),
                    "key": self._tolerance_variable_key(variable_record),
                    "compensator": bool(index in compensator_indices),
                    "surface_index": int(variable.surface_index),
                    "parameter": str(variable.parameter),
                    "coupling_group": str(variable_record.get("coupling_group", "") or ""),
                    "coupling_sign": int(variable_record.get("coupling_sign", 1) or 1),
                    "manufacturing_source_type": str(variable_record.get("manufacturing_source_type", "") or ""),
                    "manufacturing_source_id": str(variable_record.get("manufacturing_source_id", "") or ""),
                    "manufacturing_tags": str(variable_record.get("manufacturing_tags", "") or ""),
                    "manufacturing_note": str(variable_record.get("manufacturing_note", "") or ""),
                    "nominal": float(nominal_values[index]),
                    "worst": float(worst_values[index]),
                    "solved": float(current_values[index]),
                    "delta_vs_worst": float(current_values[index] - worst_values[index]),
                    "delta_vs_nominal": float(current_values[index] - nominal_values[index]),
                    "lower": float(variable.lower_bound),
                    "upper": float(variable.upper_bound),
                }
            )
        summary_out = {
            "kind": "worst_sample_multi_compensator_solve",
            "steps": steps,
            "passes_requested": passes,
            "passes_completed": len(pass_summaries),
            "variables": variable_records,
            "operand_labels": operand_labels,
            "records": records,
            "accepted_records": accepted_records,
            "pass_summaries": pass_summaries,
            "solved_variables": solved_variables,
            "compensator_count": len(compensator_indices),
            "valid_count": len([record for record in records if bool(record.get("valid"))]),
            "invalid_count": len([record for record in records if not bool(record.get("valid"))]),
            "base_sample": int(context["worst_sample"]),
            "base_total_merit": base_total,
            "final_total_merit": float(current_total),
            "improvement_vs_worst": base_total - float(current_total) if np.isfinite(base_total) and np.isfinite(current_total) else np.nan,
            "comparison": context["comparison"],
        }
        self._last_tolerance_multi_compensator_records = records
        self._last_tolerance_multi_compensator_summary = summary_out
        return summary_out

    def tolerance_worst_sample_comparison(self, summary: dict[str, object] | None = None) -> dict[str, object]:
        le = _layout_module()
        MeritEvaluator = le.MeritEvaluator
        MTFAtFrequencyOperand = le.MTFAtFrequencyOperand
        TOLERANCE_COMPARE_VIEW_VALUES = le.TOLERANCE_COMPARE_VIEW_VALUES
        TOLERANCE_COMPENSATORS_ADVANCED_ATTR = le.TOLERANCE_COMPENSATORS_ADVANCED_ATTR
        TOLERANCE_COUPLING_ADVANCED_ATTR = le.TOLERANCE_COUPLING_ADVANCED_ATTR
        TOLERANCE_MANUFACTURING_ADVANCED_ATTR = le.TOLERANCE_MANUFACTURING_ADVANCED_ATTR
        VARIABLE_REGISTRY = le.VARIABLE_REGISTRY
        _native_variable_matches = le._native_variable_matches
        summary = dict(summary if summary is not None else self._last_tolerance_monte_carlo_summary)
        if not summary:
            raise RuntimeError("Run Tolerance Monte Carlo Report first.")
        records = list(summary.get("records", []) or [])
        if not records:
            raise RuntimeError("Tolerance Monte Carlo has no sample records.")
        nominal = next((record for record in records if str(record.get("kind", "")) == "nominal"), records[0])
        valid_candidates = [
            record
            for record in records
            if bool(record.get("valid")) and str(record.get("kind", "")) != "nominal"
        ]
        if not valid_candidates:
            valid_candidates = [record for record in records if bool(record.get("valid"))]
        if not valid_candidates:
            raise RuntimeError("Tolerance Monte Carlo has no valid samples to compare.")
        perturbed = max(valid_candidates, key=lambda record: self._tolerance_record_float(record, "total_merit", -np.inf))

        comparison_records: list[dict[str, object]] = []

        def append_metric(category: str, name: str, metric: str, nominal_value: float, perturbed_value: float, **extra) -> None:
            delta = float(perturbed_value) - float(nominal_value)
            comparison_records.append(
                {
                    "category": category,
                    "name": name,
                    "metric": metric,
                    "nominal": float(nominal_value),
                    "perturbed": float(perturbed_value),
                    "delta": delta,
                    "relative_delta": self._tolerance_relative_delta(float(nominal_value), float(perturbed_value)),
                    "nominal_sample": int(nominal.get("sample", 0) or 0),
                    "perturbed_sample": int(perturbed.get("sample", 0) or 0),
                    **extra,
                }
            )

        append_metric(
            "summary",
            "Total merit",
            "total_merit",
            self._tolerance_record_float(nominal, "total_merit"),
            self._tolerance_record_float(perturbed, "total_merit"),
        )

        for variable in list(summary.get("variables", []) or []):
            try:
                surface_index = int(variable.get("surface_index", -1))
            except Exception:
                surface_index = -1
            parameter = str(variable.get("parameter", "") or "")
            key = f"var_s{surface_index}_{parameter.lower()}"
            if key not in nominal or key not in perturbed:
                continue
            append_metric(
                "variable",
                str(variable.get("name", key) or key),
                parameter or key,
                self._tolerance_record_float(nominal, key),
                self._tolerance_record_float(perturbed, key),
                lower=float(variable.get("lower", np.nan)),
                upper=float(variable.get("upper", np.nan)),
                coupling_group=str(variable.get("coupling_group", "") or ""),
                coupling_sign=int(variable.get("coupling_sign", 1) or 1),
                manufacturing_source_type=str(variable.get("manufacturing_source_type", "") or ""),
                manufacturing_source_id=str(variable.get("manufacturing_source_id", "") or ""),
                manufacturing_tags=str(variable.get("manufacturing_tags", "") or ""),
                manufacturing_note=str(variable.get("manufacturing_note", "") or ""),
            )

        suffixes = ("_value", "_residual", "_weighted")
        operand_bases: set[str] = set()
        for record in (nominal, perturbed):
            for key in record:
                text = str(key)
                for suffix in suffixes:
                    if text.endswith(suffix):
                        operand_bases.add(text[: -len(suffix)])
        for base in sorted(operand_bases):
            for suffix in suffixes:
                metric_key = f"{base}{suffix}"
                if metric_key not in nominal or metric_key not in perturbed:
                    continue
                append_metric(
                    "operand",
                    self._tolerance_metric_label(base),
                    suffix.strip("_"),
                    self._tolerance_record_float(nominal, metric_key),
                    self._tolerance_record_float(perturbed, metric_key),
                )

        comparison = {
            "nominal_sample": int(nominal.get("sample", 0) or 0),
            "perturbed_sample": int(perturbed.get("sample", 0) or 0),
            "records": comparison_records,
            "nominal_total_merit": self._tolerance_record_float(nominal, "total_merit"),
            "perturbed_total_merit": self._tolerance_record_float(perturbed, "total_merit"),
            "perturbed_message": str(perturbed.get("message", "") or ""),
        }
        self._last_tolerance_comparison_records = comparison_records
        self._last_tolerance_comparison_summary = comparison
        return comparison

    def tolerance_worst_sample_comparison_report_text(self, comparison: dict[str, object] | None = None) -> str:
        le = _layout_module()
        MeritEvaluator = le.MeritEvaluator
        MTFAtFrequencyOperand = le.MTFAtFrequencyOperand
        TOLERANCE_COMPARE_VIEW_VALUES = le.TOLERANCE_COMPARE_VIEW_VALUES
        TOLERANCE_COMPENSATORS_ADVANCED_ATTR = le.TOLERANCE_COMPENSATORS_ADVANCED_ATTR
        TOLERANCE_COUPLING_ADVANCED_ATTR = le.TOLERANCE_COUPLING_ADVANCED_ATTR
        TOLERANCE_MANUFACTURING_ADVANCED_ATTR = le.TOLERANCE_MANUFACTURING_ADVANCED_ATTR
        VARIABLE_REGISTRY = le.VARIABLE_REGISTRY
        _native_variable_matches = le._native_variable_matches
        comparison = dict(comparison if comparison is not None else self._last_tolerance_comparison_summary)
        if not comparison:
            return "# KrakenOS Tolerance Worst-Sample Comparison\n\nNo comparison has been executed.\n"
        records = list(comparison.get("records", []) or [])
        summary_rows = [record for record in records if str(record.get("category", "")) == "summary"]
        variable_rows = [record for record in records if str(record.get("category", "")) == "variable"]
        operand_rows = [record for record in records if str(record.get("category", "")) == "operand"]

        def format_row(record: dict[str, object]) -> str:
            rel = self._format_percent_value(record.get("relative_delta"))
            manufacturing = self._format_tolerance_manufacturing_inline(record)
            return (
                "- {name} [{metric}]: nominal={nominal:.6g}, worst={perturbed:.6g}, "
                "delta={delta:.6g}, relative={relative}{manufacturing}".format(
                    name=record.get("name", ""),
                    metric=record.get("metric", ""),
                    nominal=float(record.get("nominal", np.nan)),
                    perturbed=float(record.get("perturbed", np.nan)),
                    delta=float(record.get("delta", np.nan)),
                    relative=rel,
                    manufacturing=manufacturing,
                )
            )

        lines = [
            "# KrakenOS Tolerance Worst-Sample Comparison",
            "",
            f"Nominal sample: {comparison.get('nominal_sample')}",
            f"Worst sample: {comparison.get('perturbed_sample')}",
            f"Worst sample message: {comparison.get('perturbed_message', '')}",
            "",
            "Summary:",
        ]
        lines.extend(format_row(record) for record in summary_rows)
        lines.append("")
        lines.append("Variables:")
        lines.extend(format_row(record) for record in variable_rows)
        lines.append("")
        lines.append("Operands:")
        lines.extend(format_row(record) for record in operand_rows)
        return "\n".join(lines).strip() + "\n"
