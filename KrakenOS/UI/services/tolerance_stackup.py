"""Tolerance stack-up dashboard service."""

from __future__ import annotations

import re
from typing import Any

import numpy as np


class ToleranceStackupService:
    """Assemble tolerance stack-up dashboard and export records."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def tolerance_stackup_dashboard(self, summary: dict[str, object] | None = None) -> dict[str, object]:
        summary = dict(summary if summary is not None else self._last_tolerance_monte_carlo_summary)
        if not summary:
            raise RuntimeError("Run Tolerance Monte Carlo Report first.")
        variables = [dict(variable) for variable in list(summary.get("variables", []) or [])]
        records = [dict(record) for record in list(summary.get("records", []) or [])]
        if not variables:
            raise RuntimeError("Tolerance Monte Carlo has no variables for stack-up analysis.")
        nominal_record = next((record for record in records if str(record.get("kind", "")) == "nominal"), records[0] if records else {})
        sample_records = [
            record
            for record in records
            if bool(record.get("valid")) and str(record.get("kind", "")) != "nominal"
        ]
        if not sample_records:
            raise RuntimeError("Tolerance stack-up needs at least one valid perturbed Monte Carlo sample.")
        nominal_total = self._tolerance_record_float(nominal_record, "total_merit")
        total_values = np.asarray(
            [self._tolerance_record_float(record, "total_merit") for record in sample_records],
            dtype=float,
        )
        total_delta = total_values - float(nominal_total)
        worst_record = max(sample_records, key=lambda record: self._tolerance_record_float(record, "total_merit", -np.inf))
        worst_sample = int(worst_record.get("sample", -1) or -1)

        rows: list[dict[str, object]] = []
        for variable in variables:
            key = self._tolerance_variable_key(variable)
            nominal = float(variable.get("nominal", self._tolerance_record_float(nominal_record, key)))
            values = np.asarray(
                [self._tolerance_record_float(record, key, nominal) for record in sample_records],
                dtype=float,
            )
            deltas = values - nominal
            finite = np.isfinite(values) & np.isfinite(deltas) & np.isfinite(total_delta)
            slope = np.nan
            correlation = np.nan
            variance_contribution = np.nan
            sample_mean = np.nan
            sample_std = np.nan
            p95_abs_delta = np.nan
            if np.any(finite):
                x = deltas[finite]
                y = total_delta[finite]
                sample_mean = float(np.mean(values[finite]))
                sample_std = float(np.std(x))
                p95_abs_delta = float(np.percentile(np.abs(x), 95.0))
                x_centered = x - float(np.mean(x))
                y_centered = y - float(np.mean(y))
                x_var = float(np.dot(x_centered, x_centered))
                y_var = float(np.dot(y_centered, y_centered))
                if x.size >= 2 and x_var > 1e-24:
                    slope = float(np.dot(x_centered, y_centered) / x_var)
                    variance_contribution = float((slope * slope) * np.var(x))
                    if y_var > 1e-24:
                        correlation = float(np.dot(x_centered, y_centered) / np.sqrt(x_var * y_var))
            worst_value = self._tolerance_record_float(worst_record, key, nominal)
            lower = float(variable.get("lower", np.nan))
            upper = float(variable.get("upper", np.nan))
            tolerance_width = upper - lower if np.isfinite(lower) and np.isfinite(upper) else np.nan
            merit_span = abs(float(slope)) * abs(float(tolerance_width)) if np.isfinite(slope) and np.isfinite(tolerance_width) else np.nan
            rows.append(
                {
                    "rank": 0,
                    "stackup_type": "variable",
                    "name": str(variable.get("name", key) or key),
                    "surface_index": int(variable.get("surface_index", -1)),
                    "parameter": str(variable.get("parameter", "") or ""),
                    "role": "compensator" if bool(variable.get("compensator", True)) else "tolerance-only",
                    "coupling_group": str(variable.get("coupling_group", "") or ""),
                    "coupling_sign": int(variable.get("coupling_sign", 1) or 1),
                    "manufacturing_source_type": str(variable.get("manufacturing_source_type", "") or ""),
                    "manufacturing_source_id": str(variable.get("manufacturing_source_id", "") or ""),
                    "manufacturing_tags": str(variable.get("manufacturing_tags", "") or ""),
                    "manufacturing_note": str(variable.get("manufacturing_note", "") or ""),
                    "key": key,
                    "nominal": nominal,
                    "lower": lower,
                    "upper": upper,
                    "tolerance_width": tolerance_width,
                    "valid_sample_count": int(np.count_nonzero(finite)),
                    "sample_mean": sample_mean,
                    "sample_std": sample_std,
                    "p95_abs_delta": p95_abs_delta,
                    "worst_sample": worst_sample,
                    "worst_value": worst_value,
                    "worst_delta": worst_value - nominal if np.isfinite(worst_value) and np.isfinite(nominal) else np.nan,
                    "slope_merit_per_unit": slope,
                    "correlation": correlation,
                    "variance_contribution": variance_contribution,
                    "merit_sigma_contribution": np.sqrt(max(variance_contribution, 0.0)) if np.isfinite(variance_contribution) else np.nan,
                    "contribution_fraction": np.nan,
                    "merit_span_estimate": merit_span,
                }
            )

        group_rows: list[dict[str, object]] = []
        group_members: dict[str, list[tuple[dict[str, object], dict[str, object]]]] = {}
        row_by_key = {str(row.get("key", "")): row for row in rows}
        variable_by_key = {self._tolerance_variable_key(variable): variable for variable in variables}
        for key, variable in variable_by_key.items():
            row = row_by_key.get(key)
            if row is None:
                continue
            coupling_group = str(variable.get("coupling_group", "") or "").strip()
            group_key = f"coupling:{coupling_group}" if coupling_group else f"variable:{key}"
            group_members.setdefault(group_key, []).append((variable, row))

        for group_key, members in group_members.items():
            keys = [self._tolerance_variable_key(variable) for variable, _row in members]
            nominal_values = np.asarray(
                [
                    float(variable.get("nominal", self._tolerance_record_float(nominal_record, key)))
                    for key, (variable, _row) in zip(keys, members)
                ],
                dtype=float,
            )
            matrix = np.asarray(
                [
                    [self._tolerance_record_float(record, key, nominal_values[index]) for index, key in enumerate(keys)]
                    for record in sample_records
                ],
                dtype=float,
            )
            deltas = matrix - nominal_values.reshape(1, -1)
            finite_rows = np.isfinite(total_delta)
            if deltas.size:
                finite_rows &= np.all(np.isfinite(deltas), axis=1)
            x = deltas[finite_rows]
            y = total_delta[finite_rows]
            beta = np.full(len(members), np.nan, dtype=float)
            predicted = np.asarray([], dtype=float)
            variance_contribution = np.nan
            correlation = np.nan
            sample_std = np.nan
            p95_abs_delta = np.nan
            slope_norm = np.nan
            if x.size and y.size:
                vector_norm = np.linalg.norm(x, axis=1)
                if x.shape[0] >= 2:
                    covariance = np.atleast_2d(np.cov(x, rowvar=False, bias=True))
                    sample_std = float(np.sqrt(np.trace(covariance)))
                else:
                    sample_std = float(np.std(vector_norm))
                p95_abs_delta = float(np.percentile(vector_norm, 95.0))
                x_centered = x - np.mean(x, axis=0, keepdims=True)
                y_centered = y - float(np.mean(y))
                if x.shape[0] >= 2 and np.any(np.abs(x_centered) > 1e-24):
                    try:
                        beta = np.linalg.lstsq(x_centered, y_centered, rcond=None)[0]
                        predicted = np.asarray(x_centered @ beta, dtype=float).ravel()
                        variance_contribution = float(np.var(predicted))
                        slope_norm = float(np.linalg.norm(beta))
                        pred_var = float(np.dot(predicted - float(np.mean(predicted)), predicted - float(np.mean(predicted))))
                        y_var = float(np.dot(y_centered, y_centered))
                        if pred_var > 1e-24 and y_var > 1e-24:
                            correlation = float(np.dot(predicted - float(np.mean(predicted)), y_centered) / np.sqrt(pred_var * y_var))
                    except Exception:
                        beta = np.full(len(members), np.nan, dtype=float)
            member_rows = [row for _variable, row in members]
            member_names = [str(row.get("name", "")) for row in member_rows]
            member_roles = sorted({str(row.get("role", "") or "") for row in member_rows if str(row.get("role", "") or "").strip()})
            member_source_types = sorted(
                {str(row.get("manufacturing_source_type", "") or "").strip() for row in member_rows if str(row.get("manufacturing_source_type", "") or "").strip()}
            )
            member_source_ids = sorted(
                {str(row.get("manufacturing_source_id", "") or "").strip() for row in member_rows if str(row.get("manufacturing_source_id", "") or "").strip()}
            )
            member_tags = sorted(
                {
                    tag.strip()
                    for row in member_rows
                    for tag in re.split(r"[,;\n]+", str(row.get("manufacturing_tags", "") or ""))
                    if tag.strip()
                }
            )
            member_notes = sorted(
                {str(row.get("manufacturing_note", "") or "").strip() for row in member_rows if str(row.get("manufacturing_note", "") or "").strip()}
            )
            coupling_group = str(members[0][0].get("coupling_group", "") or "").strip()
            coupling_label = coupling_group if coupling_group else str(member_rows[0].get("name", keys[0]) or keys[0])
            worst_values = np.asarray(
                [
                    self._tolerance_record_float(worst_record, key, nominal_values[index])
                    for index, key in enumerate(keys)
                ],
                dtype=float,
            )
            worst_delta_norm = float(np.linalg.norm(worst_values - nominal_values)) if worst_values.size else np.nan
            group_rows.append(
                {
                    "rank": 0,
                    "stackup_type": "coupled_group" if coupling_group else "independent_variable",
                    "name": coupling_label,
                    "group_key": group_key,
                    "coupling_group": coupling_group,
                    "member_count": len(members),
                    "members": "; ".join(member_names),
                    "roles": "mixed" if len(member_roles) > 1 else (member_roles[0] if member_roles else ""),
                    "manufacturing_source_type": "; ".join(member_source_types),
                    "manufacturing_source_id": "; ".join(member_source_ids),
                    "manufacturing_tags": "; ".join(member_tags),
                    "manufacturing_note": "; ".join(member_notes),
                    "keys": "; ".join(keys),
                    "valid_sample_count": int(np.count_nonzero(finite_rows)),
                    "sample_std": sample_std,
                    "p95_abs_delta": p95_abs_delta,
                    "worst_sample": worst_sample,
                    "worst_delta_norm": worst_delta_norm,
                    "slope_norm_merit_per_unit": slope_norm,
                    "correlation": correlation,
                    "variance_contribution": variance_contribution,
                    "merit_sigma_contribution": np.sqrt(max(variance_contribution, 0.0)) if np.isfinite(variance_contribution) else np.nan,
                    "contribution_fraction": np.nan,
                    "member_slopes": "; ".join(
                        f"{key}:{value:.6g}" if np.isfinite(value) else f"{key}:"
                        for key, value in zip(keys, beta)
                    ),
                }
            )

        finite_contributions = [
            float(row["variance_contribution"])
            for row in rows
            if np.isfinite(float(row.get("variance_contribution", np.nan))) and float(row.get("variance_contribution", 0.0)) > 0.0
        ]
        total_contribution = float(sum(finite_contributions))
        for row in rows:
            value = float(row.get("variance_contribution", np.nan))
            if total_contribution > 0.0 and np.isfinite(value) and value >= 0.0:
                row["contribution_fraction"] = value / total_contribution
        rows.sort(
            key=lambda row: (
                -float(row.get("contribution_fraction", -1.0)) if np.isfinite(float(row.get("contribution_fraction", np.nan))) else 1.0,
                -abs(float(row.get("slope_merit_per_unit", 0.0))) if np.isfinite(float(row.get("slope_merit_per_unit", np.nan))) else 0.0,
                str(row.get("name", "")),
            )
        )
        for rank, row in enumerate(rows, start=1):
            row["rank"] = rank

        finite_group_contributions = [
            float(row["variance_contribution"])
            for row in group_rows
            if np.isfinite(float(row.get("variance_contribution", np.nan))) and float(row.get("variance_contribution", 0.0)) > 0.0
        ]
        total_group_contribution = float(sum(finite_group_contributions))
        for row in group_rows:
            value = float(row.get("variance_contribution", np.nan))
            if total_group_contribution > 0.0 and np.isfinite(value) and value >= 0.0:
                row["contribution_fraction"] = value / total_group_contribution
        group_rows.sort(
            key=lambda row: (
                -float(row.get("contribution_fraction", -1.0)) if np.isfinite(float(row.get("contribution_fraction", np.nan))) else 1.0,
                -float(row.get("merit_sigma_contribution", 0.0)) if np.isfinite(float(row.get("merit_sigma_contribution", np.nan))) else 0.0,
                str(row.get("name", "")),
            )
        )
        for rank, row in enumerate(group_rows, start=1):
            row["rank"] = rank

        dashboard = {
            "kind": "tolerance_stackup_dashboard",
            "sample_count": int(summary.get("sample_count", 0) or 0),
            "seed": int(summary.get("seed", 0) or 0),
            "operand_labels": list(summary.get("operand_labels", []) or []),
            "valid_sample_count": len(sample_records),
            "invalid_count": int(summary.get("invalid_count", 0) or 0),
            "nominal_total_merit": nominal_total,
            "worst_sample": worst_sample,
            "worst_total_merit": self._tolerance_record_float(worst_record, "total_merit"),
            "observed_total_merit_stats": self._finite_stats([float(value) for value in total_values]),
            "observed_total_delta_stats": self._finite_stats([float(value) for value in total_delta]),
            "linearized_variance_sum": total_contribution,
            "linearized_sigma_estimate": np.sqrt(total_contribution) if total_contribution > 0.0 else np.nan,
            "group_linearized_variance_sum": total_group_contribution,
            "group_linearized_sigma_estimate": np.sqrt(total_group_contribution) if total_group_contribution > 0.0 else np.nan,
            "records": rows,
            "group_records": group_rows,
        }
        self._last_tolerance_stackup_records = rows
        self._last_tolerance_stackup_summary = dashboard
        return dashboard

    def tolerance_stackup_dashboard_report_text(self, dashboard: dict[str, object] | None = None) -> str:
        dashboard = dict(dashboard if dashboard is not None else self._last_tolerance_stackup_summary)
        if not dashboard:
            return "# KrakenOS Tolerance Stack-Up Dashboard\n\nNo stack-up dashboard has been executed.\n"
        rows = [dict(record) for record in list(dashboard.get("records", []) or [])]
        group_rows = [dict(record) for record in list(dashboard.get("group_records", []) or [])]
        lines = [
            "# KrakenOS Tolerance Stack-Up Dashboard",
            "",
            "Model: linearized variance contribution estimated from valid Monte Carlo samples.",
            f"Samples: {int(dashboard.get('sample_count', 0) or 0)} Monte Carlo + nominal",
            f"Seed: {int(dashboard.get('seed', 0) or 0)}",
            f"Valid perturbed samples: {int(dashboard.get('valid_sample_count', 0) or 0)}",
            f"Invalid evaluations: {int(dashboard.get('invalid_count', 0) or 0)}",
            f"Merit operands: {', '.join(str(label) for label in list(dashboard.get('operand_labels', []) or []))}",
            f"Nominal merit: {float(dashboard.get('nominal_total_merit', np.nan)):.6g}",
            f"Worst sample: {dashboard.get('worst_sample')} (merit={float(dashboard.get('worst_total_merit', np.nan)):.6g})",
            f"Observed total merit: {self._format_stats_line(dict(dashboard.get('observed_total_merit_stats', {}) or {}))}",
            f"Linearized RSS merit sigma estimate: {float(dashboard.get('linearized_sigma_estimate', np.nan)):.6g}",
            f"Group covariance-aware sigma estimate: {float(dashboard.get('group_linearized_sigma_estimate', np.nan)):.6g}",
            "",
            "Manufacturing groups:",
        ]
        for record in group_rows[:12]:
            contribution = self._format_percent_value(record.get("contribution_fraction"))
            group_type = "coupled" if str(record.get("stackup_type", "")) == "coupled_group" else "single"
            manufacturing = self._format_tolerance_manufacturing_inline(record)
            lines.append(
                "- #{rank} {name}: contribution={contribution}, sigma={sigma:.6g}, "
                "corr={corr:.6g}, p95 motion={p95:.6g}, worst motion={worst_delta:.6g}, "
                "members={members}, type={group_type}{manufacturing}".format(
                    rank=int(record.get("rank", 0) or 0),
                    name=record.get("name", ""),
                    contribution=contribution,
                    sigma=float(record.get("merit_sigma_contribution", np.nan)),
                    corr=float(record.get("correlation", np.nan)),
                    p95=float(record.get("p95_abs_delta", np.nan)),
                    worst_delta=float(record.get("worst_delta_norm", np.nan)),
                    members=record.get("member_count", 0),
                    group_type=group_type,
                    manufacturing=manufacturing,
                )
            )
        lines.extend(
            [
                "",
                "Top stack-up contributors:",
            ]
        )
        for record in rows[:12]:
            contribution = self._format_percent_value(record.get("contribution_fraction"))
            coupling = ""
            coupling_group = str(record.get("coupling_group", "") or "").strip()
            if coupling_group:
                coupling = ", coupling={}{}".format(
                    "-" if int(record.get("coupling_sign", 1) or 1) < 0 else "",
                    coupling_group,
                )
            manufacturing = self._format_tolerance_manufacturing_inline(record)
            lines.append(
                "- #{rank} {name}: contribution={contribution}, sigma={sigma:.6g}, slope={slope:.6g}, "
                "corr={corr:.6g}, p95 |delta|={p95:.6g}, worst delta={worst_delta:.6g}, role={role}{coupling}{manufacturing}".format(
                    rank=int(record.get("rank", 0) or 0),
                    name=record.get("name", ""),
                    contribution=contribution,
                    sigma=float(record.get("merit_sigma_contribution", np.nan)),
                    slope=float(record.get("slope_merit_per_unit", np.nan)),
                    corr=float(record.get("correlation", np.nan)),
                    p95=float(record.get("p95_abs_delta", np.nan)),
                    worst_delta=float(record.get("worst_delta", np.nan)),
                    role=record.get("role", ""),
                    coupling=coupling,
                    manufacturing=manufacturing,
                )
            )
        lines.extend(
            [
                "",
                "Interpretation:",
                "- variable contribution is a single-variable linearized proxy, not a full Sobol decomposition.",
                "- manufacturing-group contribution uses covariance of member deltas, so coupled variables are ranked as one shared error source.",
                "- use the worst-sample comparison and compensator reports to inspect the actual traced cases.",
            ]
        )
        return "\n".join(lines).strip() + "\n"

    def tolerance_stackup_csv_rows(
        self,
        dashboard: dict[str, object] | None = None,
    ) -> tuple[list[str], list[dict[str, object]]]:
        dashboard = dict(dashboard if dashboard is not None else self._last_tolerance_stackup_summary)
        rows = [dict(record) for record in list(dashboard.get("records", []) or [])]
        columns = [
            "rank",
            "stackup_type",
            "name",
            "surface_index",
            "parameter",
            "role",
            "coupling_group",
            "coupling_sign",
            "manufacturing_source_type",
            "manufacturing_source_id",
            "manufacturing_tags",
            "manufacturing_note",
            "key",
            "nominal",
            "lower",
            "upper",
            "tolerance_width",
            "valid_sample_count",
            "sample_mean",
            "sample_std",
            "p95_abs_delta",
            "worst_sample",
            "worst_value",
            "worst_delta",
            "slope_merit_per_unit",
            "correlation",
            "variance_contribution",
            "merit_sigma_contribution",
            "contribution_fraction",
            "merit_span_estimate",
        ]
        return columns, rows

    def tolerance_stackup_group_csv_rows(
        self,
        dashboard: dict[str, object] | None = None,
    ) -> tuple[list[str], list[dict[str, object]]]:
        dashboard = dict(dashboard if dashboard is not None else self._last_tolerance_stackup_summary)
        rows = [dict(record) for record in list(dashboard.get("group_records", []) or [])]
        columns = [
            "rank",
            "stackup_type",
            "name",
            "group_key",
            "coupling_group",
            "member_count",
            "members",
            "roles",
            "manufacturing_source_type",
            "manufacturing_source_id",
            "manufacturing_tags",
            "manufacturing_note",
            "keys",
            "valid_sample_count",
            "sample_std",
            "p95_abs_delta",
            "worst_sample",
            "worst_delta_norm",
            "slope_norm_merit_per_unit",
            "correlation",
            "variance_contribution",
            "merit_sigma_contribution",
            "contribution_fraction",
            "member_slopes",
        ]
        return columns, rows

