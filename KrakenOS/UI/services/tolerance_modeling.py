"""Tolerance modeling and report helpers for the Tk layout editor."""

from __future__ import annotations

import io
import re
from contextlib import redirect_stderr, redirect_stdout
from tkinter import messagebox, simpledialog

import numpy as np

import KrakenOS as Kos
from KrakenOS.Optimization import (
    OPERAND_REGISTRY,
    VARIABLE_REGISTRY,
    MeritEvaluator,
    MeritFunction,
    OpticalVariable,
)
from KrakenOS.UI.panels.main_tolerance_report_dialogs import MainToleranceReportDialogs
from KrakenOS.UI.services.surface_value_parsing import _native_variable_matches
from KrakenOS.UI.services.tolerance_analysis import ToleranceAnalysisService
from KrakenOS.UI.services.tolerance_stackup import ToleranceStackupService
from KrakenOS.UI.surface_table_model import SurfaceRow
from KrakenOS.UI.tolerance_constants import (
    TOLERANCE_COMPARE_VIEW_DEFAULT,
    TOLERANCE_COMPARE_VIEW_VALUES,
    TOLERANCE_COMPENSATORS_ADVANCED_ATTR,
    TOLERANCE_COUPLING_ADVANCED_ATTR,
    TOLERANCE_MANUFACTURING_ADVANCED_ATTR,
    TOLERANCE_SOLVE_PRESET_DEFAULTS,
)


class ToleranceModelingMixin:
    @staticmethod
    def _finite_stats(values: list[float]) -> dict[str, float]:
        arr = np.asarray(values, dtype=float).reshape(-1)
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            return {"mean": np.nan, "std": np.nan, "min": np.nan, "p95": np.nan, "max": np.nan}
        return {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "p95": float(np.percentile(arr, 95.0)),
            "max": float(np.max(arr)),
        }

    def run_tolerance_monte_carlo(
        self,
        *,
        sample_count: int = 25,
        seed: int = 12345,
    ) -> dict[str, object]:
        return self._tolerance_analysis_service().run_tolerance_monte_carlo(
            sample_count=sample_count,
            seed=seed,
        )

    @staticmethod
    def _format_stats_line(stats: dict[str, float]) -> str:
        return (
            f"mean={float(stats.get('mean', np.nan)):.6g}, "
            f"std={float(stats.get('std', np.nan)):.6g}, "
            f"min={float(stats.get('min', np.nan)):.6g}, "
            f"p95={float(stats.get('p95', np.nan)):.6g}, "
            f"max={float(stats.get('max', np.nan)):.6g}"
        )

    def tolerance_monte_carlo_report_text(self, summary: dict[str, object] | None = None) -> str:
        summary = dict(summary if summary is not None else self._last_tolerance_monte_carlo_summary)
        if not summary:
            return "# KrakenOS Tolerance Monte Carlo Report\n\nNo tolerance run has been executed.\n"
        variables = list(summary.get("variables", []) or [])
        records = list(summary.get("records", []) or [])
        lines = [
            "# KrakenOS Tolerance Monte Carlo Report",
            "",
            f"Samples: {int(summary.get('sample_count', 0) or 0)} Monte Carlo + nominal",
            f"Seed: {int(summary.get('seed', 0) or 0)}",
            f"Valid/invalid evaluations: {int(summary.get('valid_count', 0) or 0)}/{int(summary.get('invalid_count', 0) or 0)}",
            f"Merit operands: {', '.join(str(label) for label in list(summary.get('operand_labels', []) or []))}",
            "",
            "Variables:",
        ]
        for variable in variables:
            role = "compensator" if bool(variable.get("compensator", True)) else "tolerance-only"
            coupling_group = str(variable.get("coupling_group", "") or "").strip()
            coupling = ""
            if coupling_group:
                coupling = ", coupling={}{}".format(
                    "-" if int(variable.get("coupling_sign", 1) or 1) < 0 else "",
                    coupling_group,
                )
            manufacturing = self._format_tolerance_manufacturing_inline(dict(variable))
            lines.append(
                "- {name}: nominal={nominal:.6g}, bounds=[{lower:.6g}, {upper:.6g}], role={role}{coupling}{manufacturing}".format(
                    name=variable.get("name", ""),
                    nominal=float(variable.get("nominal", np.nan)),
                    lower=float(variable.get("lower", np.nan)),
                    upper=float(variable.get("upper", np.nan)),
                    role=role,
                    coupling=coupling,
                    manufacturing=manufacturing,
                )
            )
        lines.extend(
            [
                "",
                f"Total merit: {self._format_stats_line(dict(summary.get('total_merit_stats', {}) or {}))}",
                (
                    f"Worst sample: {summary.get('worst_sample')} "
                    f"(total merit={float(summary.get('worst_total_merit', np.nan)):.6g})"
                ),
                "",
                "Top samples by total merit:",
            ]
        )
        top_records = sorted(
            [record for record in records if bool(record.get("valid"))],
            key=lambda record: float(record.get("total_merit", -np.inf)),
            reverse=True,
        )[:5]
        for record in top_records:
            lines.append(
                "- sample={sample} kind={kind} merit={merit:.6g} message={message}".format(
                    sample=int(record.get("sample", 0) or 0),
                    kind=record.get("kind", ""),
                    merit=float(record.get("total_merit", np.nan)),
                    message=record.get("message", ""),
                )
            )
        return "\n".join(lines).strip() + "\n"

    def _main_tolerance_report_dialogs(self) -> MainToleranceReportDialogs:
        dialog = self.__dict__.get("_main_tolerance_report_dialogs_instance")
        if dialog is None:
            dialog = MainToleranceReportDialogs(
                self,
                tolerance_compare_view_values=TOLERANCE_COMPARE_VIEW_VALUES,
            )
            self._main_tolerance_report_dialogs_instance = dialog
        return dialog

    def open_tolerance_monte_carlo_report(self) -> None:
        self._main_tolerance_report_dialogs().open_tolerance_monte_carlo_report()

    def export_tolerance_monte_carlo_csv(self) -> None:
        self._main_tolerance_report_dialogs().export_tolerance_monte_carlo_csv()

    @staticmethod
    def _tolerance_record_float(record: dict[str, object], key: str, default: float = np.nan) -> float:
        try:
            value = float(record.get(key, default))
        except Exception:
            return float(default)
        return value if np.isfinite(value) else float(default)

    @staticmethod
    def _tolerance_relative_delta(nominal: float, perturbed: float) -> float:
        if not np.isfinite(nominal) or abs(float(nominal)) <= 1e-18:
            return np.nan
        return (float(perturbed) - float(nominal)) / abs(float(nominal))

    @staticmethod
    def _tolerance_metric_label(key: str) -> str:
        text = str(key or "").replace("_", " ").strip()
        return text.title() if text else "Metric"

    @staticmethod
    def _tolerance_variable_key(variable: dict[str, object] | OpticalVariable) -> str:
        if isinstance(variable, OpticalVariable):
            surface_index = int(variable.surface_index)
            parameter = str(variable.parameter)
        else:
            surface_index = int(variable.get("surface_index", -1))
            parameter = str(variable.get("parameter", "") or "")
        return f"var_s{surface_index}_{parameter.lower()}"

    @staticmethod
    def _row_tolerance_compensator_names(row: SurfaceRow) -> tuple[str, ...]:
        advanced = dict(getattr(row, "advanced", {}) or {})
        value = advanced.get(TOLERANCE_COMPENSATORS_ADVANCED_ATTR)
        if isinstance(value, dict):
            return tuple(str(key).strip() for key, enabled in value.items() if enabled and str(key).strip())
        if isinstance(value, str):
            return tuple(part.strip() for part in re.split(r"[,;\n]+", value) if part.strip())
        if isinstance(value, (list, tuple, set)):
            return tuple(str(item).strip() for item in value if str(item).strip())
        return ()

    @staticmethod
    def _row_has_tolerance_compensator_metadata(row: SurfaceRow) -> bool:
        return TOLERANCE_COMPENSATORS_ADVANCED_ATTR in dict(getattr(row, "advanced", {}) or {})

    @classmethod
    def _row_tolerance_compensator_enabled(cls, row: SurfaceRow, parameter: str) -> bool:
        return any(_native_variable_matches(candidate, parameter) for candidate in cls._row_tolerance_compensator_names(row))

    def _has_explicit_tolerance_compensators(self) -> bool:
        return any(self._row_has_tolerance_compensator_metadata(row) for row in self.rows)

    def _tolerance_variable_compensator_enabled(self, variable: OpticalVariable) -> bool:
        if not self._has_explicit_tolerance_compensators():
            return True
        surface_index = int(variable.surface_index)
        if surface_index < 0 or surface_index >= len(self.rows):
            return False
        return self._row_tolerance_compensator_enabled(self.rows[surface_index], str(variable.parameter))

    def set_tolerance_compensator_enabled(self, surface_index: int, parameter: str, enabled: bool) -> None:
        if surface_index < 0 or surface_index >= len(self.rows):
            raise IndexError(f"Surface index out of range: {surface_index}")
        if not enabled and not self._has_explicit_tolerance_compensators():
            for candidate_row in self.rows:
                names = []
                for spec in VARIABLE_REGISTRY.values():
                    if spec.is_supported(candidate_row) and self._variable_enabled_for_row(candidate_row, spec):
                        names.append(str(spec.parameter))
                if names:
                    candidate_row.advanced = dict(candidate_row.advanced or {})
                    candidate_row.advanced[TOLERANCE_COMPENSATORS_ADVANCED_ATTR] = names
        row = self.rows[int(surface_index)]
        advanced = dict(row.advanced or {})
        names = [
            candidate
            for candidate in self._row_tolerance_compensator_names(row)
            if not _native_variable_matches(candidate, parameter)
        ]
        if enabled:
            names.append(str(parameter))
        if names:
            advanced[TOLERANCE_COMPENSATORS_ADVANCED_ATTR] = names
        elif not enabled:
            advanced[TOLERANCE_COMPENSATORS_ADVANCED_ATTR] = []
        else:
            advanced.pop(TOLERANCE_COMPENSATORS_ADVANCED_ATTR, None)
        row.advanced = advanced

    @staticmethod
    def _tolerance_coupling_sign(value: object) -> int:
        if isinstance(value, str):
            text = value.strip().lower()
            if text in {"-1", "-", "opposite", "opposed", "inverse", "inverted", "anti"}:
                return -1
            if text in {"1", "+", "+1", "same", "linked", "common"}:
                return 1
        try:
            numeric = float(value)
        except Exception:
            return 1
        return -1 if numeric < 0.0 else 1

    @classmethod
    def _normalize_tolerance_coupling_payload(cls, value: object) -> dict[str, dict[str, object]]:
        couplings: dict[str, dict[str, object]] = {}

        def add(parameter: object, group: object, sign: object = 1) -> None:
            parameter_text = str(parameter or "").strip()
            group_text = str(group or "").strip()
            if not parameter_text or not group_text:
                return
            couplings[parameter_text] = {
                "group": group_text,
                "sign": cls._tolerance_coupling_sign(sign),
            }

        if isinstance(value, dict):
            if "parameter" in value and "group" in value:
                add(value.get("parameter"), value.get("group"), value.get("sign", value.get("direction", 1)))
            else:
                for parameter, payload in value.items():
                    if isinstance(payload, dict):
                        add(parameter, payload.get("group", payload.get("name", "")), payload.get("sign", payload.get("direction", 1)))
                    elif isinstance(payload, (list, tuple)) and payload:
                        add(parameter, payload[0], payload[1] if len(payload) > 1 else 1)
                    else:
                        text = str(payload or "").strip()
                        sign = -1 if text.startswith("-") else 1
                        add(parameter, text[1:].strip() if sign < 0 else text, sign)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, dict):
                    add(item.get("parameter"), item.get("group", item.get("name", "")), item.get("sign", item.get("direction", 1)))
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    add(item[0], item[1], item[2] if len(item) > 2 else 1)
        return couplings

    @classmethod
    def _row_tolerance_couplings(cls, row: SurfaceRow) -> dict[str, dict[str, object]]:
        advanced = dict(getattr(row, "advanced", {}) or {})
        return cls._normalize_tolerance_coupling_payload(advanced.get(TOLERANCE_COUPLING_ADVANCED_ATTR))

    @classmethod
    def _row_tolerance_coupling(cls, row: SurfaceRow, parameter: str) -> dict[str, object]:
        for candidate, payload in cls._row_tolerance_couplings(row).items():
            if _native_variable_matches(candidate, parameter):
                group = str(payload.get("group", "") or "").strip()
                if group:
                    return {"group": group, "sign": cls._tolerance_coupling_sign(payload.get("sign", 1))}
        return {}

    def _tolerance_variable_coupling(self, variable: OpticalVariable) -> dict[str, object]:
        surface_index = int(variable.surface_index)
        if surface_index < 0 or surface_index >= len(self.rows):
            return {}
        return self._row_tolerance_coupling(self.rows[surface_index], str(variable.parameter))

    def set_tolerance_coupling(self, surface_index: int, parameter: str, group: str, *, sign: int = 1) -> None:
        if surface_index < 0 or surface_index >= len(self.rows):
            raise IndexError(f"Surface index out of range: {surface_index}")
        group_text = str(group or "").strip()
        if not group_text:
            self.clear_tolerance_coupling(surface_index, parameter)
            return
        row = self.rows[int(surface_index)]
        advanced = dict(row.advanced or {})
        couplings = self._row_tolerance_couplings(row)
        for candidate in list(couplings):
            if _native_variable_matches(candidate, parameter):
                couplings.pop(candidate, None)
        couplings[str(parameter)] = {
            "group": group_text,
            "sign": self._tolerance_coupling_sign(sign),
        }
        advanced[TOLERANCE_COUPLING_ADVANCED_ATTR] = couplings
        row.advanced = advanced

    def clear_tolerance_coupling(self, surface_index: int, parameter: str) -> None:
        if surface_index < 0 or surface_index >= len(self.rows):
            raise IndexError(f"Surface index out of range: {surface_index}")
        row = self.rows[int(surface_index)]
        advanced = dict(row.advanced or {})
        couplings = self._row_tolerance_couplings(row)
        for candidate in list(couplings):
            if _native_variable_matches(candidate, parameter):
                couplings.pop(candidate, None)
        if couplings:
            advanced[TOLERANCE_COUPLING_ADVANCED_ATTR] = couplings
        else:
            advanced.pop(TOLERANCE_COUPLING_ADVANCED_ATTR, None)
        row.advanced = advanced

    def edit_current_tolerance_coupling(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        index = self._table_item_row_index(self.current_menu_row_id)
        if index is None:
            return
        row = self.rows[index]
        spec = self._variable_spec_for_field(self.current_menu_field)
        if spec is None or not self._variable_enabled_for_row(row, spec):
            return
        current = self._row_tolerance_coupling(row, spec.parameter)
        initial = ""
        if current:
            sign_prefix = "-" if int(current.get("sign", 1) or 1) < 0 else ""
            initial = f"{sign_prefix}{current.get('group', '')}"
        value = simpledialog.askstring(
            "Tolerance Coupling",
            "Group name for shared random quantile. Prefix with '-' for inverted/opposite motion. Blank clears coupling.",
            initialvalue=initial,
            parent=self,
        )
        if value is None:
            return
        text = str(value).strip()
        self._begin_history_capture()
        if not text:
            self.clear_tolerance_coupling(index, spec.parameter)
            message = f"Cleared tolerance coupling for row {index} {spec.label}."
        else:
            sign = -1 if text.startswith("-") else 1
            group = text[1:].strip() if sign < 0 else text
            self.set_tolerance_coupling(index, spec.parameter, group, sign=sign)
            message = f"Row {index} {spec.label} tolerance coupling: {'-' if sign < 0 else ''}{group}."
        self._sync_table()
        self._commit_history_capture()
        self.append_progress(message)
        self.status_var.set(message)
        self._cleanup_current_popup_menu()

    def clear_current_tolerance_coupling(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        index = self._table_item_row_index(self.current_menu_row_id)
        if index is None:
            return
        row = self.rows[index]
        spec = self._variable_spec_for_field(self.current_menu_field)
        if spec is None:
            return
        self._begin_history_capture()
        self.clear_tolerance_coupling(index, spec.parameter)
        self._sync_table()
        self._commit_history_capture()
        message = f"Cleared tolerance coupling for row {index} {spec.label}."
        self.append_progress(message)
        self.status_var.set(message)
        self._cleanup_current_popup_menu()

    @staticmethod
    def _tolerance_manufacturing_tags(value: object) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            return tuple(part.strip() for part in re.split(r"[,;\n]+", value) if part.strip())
        if isinstance(value, (list, tuple, set)):
            return tuple(str(item).strip() for item in value if str(item).strip())
        return (str(value).strip(),) if str(value).strip() else ()

    @classmethod
    def _normalize_tolerance_manufacturing_payload(cls, value: object) -> dict[str, dict[str, object]]:
        records: dict[str, dict[str, object]] = {}

        def add(
            parameter: object,
            *,
            source_type: object = "",
            source_id: object = "",
            note: object = "",
            tags: object = (),
        ) -> None:
            parameter_text = str(parameter or "").strip()
            payload = {
                "source_type": str(source_type or "").strip(),
                "source_id": str(source_id or "").strip(),
                "note": str(note or "").strip(),
                "tags": list(cls._tolerance_manufacturing_tags(tags)),
            }
            if parameter_text and (
                any(payload[key] for key in ("source_type", "source_id", "note")) or payload["tags"]
            ):
                records[parameter_text] = payload

        def source_type_from(payload: dict[str, object]) -> object:
            return payload.get(
                "manufacturing_source_type",
                payload.get("source_type", payload.get("type", payload.get("process", ""))),
            )

        def source_id_from(payload: dict[str, object]) -> object:
            return payload.get(
                "manufacturing_source_id",
                payload.get("source_id", payload.get("id", payload.get("spec_id", payload.get("vendor_spec", "")))),
            )

        def note_from(payload: dict[str, object]) -> object:
            return payload.get("manufacturing_note", payload.get("note", payload.get("notes", "")))

        def tags_from(payload: dict[str, object]) -> object:
            return payload.get("manufacturing_tags", payload.get("tags", payload.get("tag", ())))

        if isinstance(value, dict):
            if "parameter" in value:
                add(
                    value.get("parameter"),
                    source_type=source_type_from(value),
                    source_id=source_id_from(value),
                    note=note_from(value),
                    tags=tags_from(value),
                )
            else:
                for parameter, payload in value.items():
                    if isinstance(payload, dict):
                        add(
                            parameter,
                            source_type=source_type_from(payload),
                            source_id=source_id_from(payload),
                            note=note_from(payload),
                            tags=tags_from(payload),
                        )
                    elif isinstance(payload, (list, tuple)):
                        add(
                            parameter,
                            source_type=payload[0] if len(payload) > 0 else "",
                            source_id=payload[1] if len(payload) > 1 else "",
                            tags=payload[2] if len(payload) > 2 else (),
                            note=payload[3] if len(payload) > 3 else "",
                        )
                    else:
                        add(parameter, source_type=payload)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, dict):
                    add(
                        item.get("parameter"),
                        source_type=source_type_from(item),
                        source_id=source_id_from(item),
                        note=note_from(item),
                        tags=tags_from(item),
                    )
                elif isinstance(item, (list, tuple)) and item:
                    add(
                        item[0],
                        source_type=item[1] if len(item) > 1 else "",
                        source_id=item[2] if len(item) > 2 else "",
                        tags=item[3] if len(item) > 3 else (),
                        note=item[4] if len(item) > 4 else "",
                    )
        return records

    @classmethod
    def _row_tolerance_manufacturing(cls, row: SurfaceRow, parameter: str) -> dict[str, object]:
        advanced = dict(getattr(row, "advanced", {}) or {})
        for candidate, payload in cls._normalize_tolerance_manufacturing_payload(
            advanced.get(TOLERANCE_MANUFACTURING_ADVANCED_ATTR)
        ).items():
            if _native_variable_matches(candidate, parameter):
                return dict(payload)
        return {}

    def _tolerance_variable_manufacturing(self, variable: OpticalVariable) -> dict[str, object]:
        surface_index = int(variable.surface_index)
        if surface_index < 0 or surface_index >= len(self.rows):
            return {}
        return self._row_tolerance_manufacturing(self.rows[surface_index], str(variable.parameter))

    @staticmethod
    def _tolerance_manufacturing_record_fields(metadata: dict[str, object]) -> dict[str, object]:
        if not metadata:
            return {}
        tags_value = metadata.get("manufacturing_tags", metadata.get("tags", []))
        tags = "; ".join(
            str(tag).strip()
            for tag in ToleranceModelingMixin._tolerance_manufacturing_tags(tags_value)
            if str(tag).strip()
        )
        fields = {
            "manufacturing_source_type": str(
                metadata.get("manufacturing_source_type", metadata.get("source_type", "")) or ""
            ).strip(),
            "manufacturing_source_id": str(
                metadata.get("manufacturing_source_id", metadata.get("source_id", "")) or ""
            ).strip(),
            "manufacturing_note": str(metadata.get("manufacturing_note", metadata.get("note", "")) or "").strip(),
            "manufacturing_tags": tags,
        }
        return {key: value for key, value in fields.items() if str(value).strip()}

    @staticmethod
    def _format_tolerance_manufacturing_inline(record: dict[str, object]) -> str:
        source_type = str(record.get("manufacturing_source_type", "") or "").strip()
        source_id = str(record.get("manufacturing_source_id", "") or "").strip()
        tags = str(record.get("manufacturing_tags", "") or "").strip()
        note = str(record.get("manufacturing_note", "") or "").strip()
        parts: list[str] = []
        if source_type or source_id:
            if source_type and source_id:
                parts.append(f"source={source_type}:{source_id}")
            else:
                parts.append(f"source={source_type or source_id}")
        if tags:
            parts.append(f"tags={tags}")
        if note:
            parts.append(f"note={note}")
        return "" if not parts else ", " + ", ".join(parts)

    def set_tolerance_manufacturing_metadata(
        self,
        surface_index: int,
        parameter: str,
        *,
        source_type: str = "",
        source_id: str = "",
        tags: object = (),
        note: str = "",
    ) -> None:
        if surface_index < 0 or surface_index >= len(self.rows):
            raise IndexError(f"Surface index out of range: {surface_index}")
        metadata = self._tolerance_manufacturing_record_fields(
            {
                "source_type": source_type,
                "source_id": source_id,
                "tags": self._tolerance_manufacturing_tags(tags),
                "note": note,
            }
        )
        if not metadata:
            self.clear_tolerance_manufacturing_metadata(surface_index, parameter)
            return
        row = self.rows[int(surface_index)]
        advanced = dict(row.advanced or {})
        records = self._normalize_tolerance_manufacturing_payload(advanced.get(TOLERANCE_MANUFACTURING_ADVANCED_ATTR))
        for candidate in list(records):
            if _native_variable_matches(candidate, parameter):
                records.pop(candidate, None)
        records[str(parameter)] = {
            "source_type": str(metadata.get("manufacturing_source_type", "") or ""),
            "source_id": str(metadata.get("manufacturing_source_id", "") or ""),
            "note": str(metadata.get("manufacturing_note", "") or ""),
            "tags": self._tolerance_manufacturing_tags(metadata.get("manufacturing_tags", "")),
        }
        advanced[TOLERANCE_MANUFACTURING_ADVANCED_ATTR] = records
        row.advanced = advanced

    def clear_tolerance_manufacturing_metadata(self, surface_index: int, parameter: str) -> None:
        if surface_index < 0 or surface_index >= len(self.rows):
            raise IndexError(f"Surface index out of range: {surface_index}")
        row = self.rows[int(surface_index)]
        advanced = dict(row.advanced or {})
        records = self._normalize_tolerance_manufacturing_payload(advanced.get(TOLERANCE_MANUFACTURING_ADVANCED_ATTR))
        for candidate in list(records):
            if _native_variable_matches(candidate, parameter):
                records.pop(candidate, None)
        if records:
            advanced[TOLERANCE_MANUFACTURING_ADVANCED_ATTR] = records
        else:
            advanced.pop(TOLERANCE_MANUFACTURING_ADVANCED_ATTR, None)
        row.advanced = advanced

    def edit_current_tolerance_manufacturing(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        index = self._table_item_row_index(self.current_menu_row_id)
        if index is None:
            return
        row = self.rows[index]
        spec = self._variable_spec_for_field(self.current_menu_field)
        if spec is None or not self._variable_enabled_for_row(row, spec):
            return
        current = self._row_tolerance_manufacturing(row, spec.parameter)
        initial = " | ".join(
            [
                str(current.get("source_type", "") or ""),
                str(current.get("source_id", "") or ""),
                "; ".join(str(tag) for tag in list(current.get("tags", []) or [])),
                str(current.get("note", "") or ""),
            ]
        ).strip()
        value = simpledialog.askstring(
            "Tolerance Manufacturing Metadata",
            "Enter: source type | source/spec ID | tags | note. Blank clears metadata.",
            initialvalue=initial,
            parent=self,
        )
        if value is None:
            return
        text = str(value).strip()
        self._begin_history_capture()
        if not text:
            self.clear_tolerance_manufacturing_metadata(index, spec.parameter)
            message = f"Cleared manufacturing metadata for row {index} {spec.label}."
        else:
            parts = [part.strip() for part in text.split("|")]
            while len(parts) < 4:
                parts.append("")
            self.set_tolerance_manufacturing_metadata(
                index,
                spec.parameter,
                source_type=parts[0],
                source_id=parts[1],
                tags=parts[2],
                note=parts[3],
            )
            message = f"Row {index} {spec.label} manufacturing metadata: {parts[0] or parts[1] or parts[2] or 'set'}."
        self._sync_table()
        self._commit_history_capture()
        self.append_progress(message)
        self.status_var.set(message)
        self._cleanup_current_popup_menu()

    def clear_current_tolerance_manufacturing(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        index = self._table_item_row_index(self.current_menu_row_id)
        if index is None:
            return
        row = self.rows[index]
        spec = self._variable_spec_for_field(self.current_menu_field)
        if spec is None:
            return
        self._begin_history_capture()
        self.clear_tolerance_manufacturing_metadata(index, spec.parameter)
        self._sync_table()
        self._commit_history_capture()
        message = f"Cleared manufacturing metadata for row {index} {spec.label}."
        self.append_progress(message)
        self.status_var.set(message)
        self._cleanup_current_popup_menu()

    @classmethod
    def _normalize_tolerance_manufacturing_template(
        cls,
        value: object,
        *,
        fallback_name: str = "Manufacturing source",
    ) -> dict[str, object]:
        if not isinstance(value, dict):
            return {}
        fields = cls._tolerance_manufacturing_record_fields(value)
        if not fields:
            return {}
        name = str(
            value.get(
                "name",
                value.get(
                    "label",
                    fields.get("manufacturing_source_id", fields.get("manufacturing_source_type", fallback_name)),
                ),
            )
            or fallback_name
        ).strip()
        if not name:
            return {}
        return {
            "name": name,
            "source_type": str(fields.get("manufacturing_source_type", "") or ""),
            "source_id": str(fields.get("manufacturing_source_id", "") or ""),
            "tags": list(cls._tolerance_manufacturing_tags(fields.get("manufacturing_tags", ""))),
            "note": str(fields.get("manufacturing_note", "") or ""),
        }

    @classmethod
    def _normalize_tolerance_manufacturing_templates(cls, value: object) -> list[dict[str, object]]:
        raw_items: list[object]
        if isinstance(value, dict):
            if isinstance(value.get("templates"), (list, tuple)):
                raw_items = list(value.get("templates", []) or [])
            elif "name" in value:
                raw_items = [value]
            else:
                raw_items = [
                    dict(payload, name=str(name))
                    for name, payload in value.items()
                    if isinstance(payload, dict)
                ]
        elif isinstance(value, (list, tuple)):
            raw_items = list(value)
        else:
            raw_items = []
        templates: list[dict[str, object]] = []
        seen_names: set[str] = set()
        for index, item in enumerate(raw_items, start=1):
            template = cls._normalize_tolerance_manufacturing_template(item, fallback_name=f"Template {index}")
            name = str(template.get("name", "") or "")
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            templates.append(template)
        return templates

    def _tolerance_manufacturing_template_by_name(self, name: str) -> dict[str, object] | None:
        wanted = str(name or "").strip()
        for template in self._normalize_tolerance_manufacturing_templates(
            self.__dict__.get("tolerance_manufacturing_templates", [])
        ):
            if str(template.get("name", "")) == wanted:
                return dict(template)
        wanted_lower = wanted.lower()
        for template in self._normalize_tolerance_manufacturing_templates(
            self.__dict__.get("tolerance_manufacturing_templates", [])
        ):
            if str(template.get("name", "")).lower() == wanted_lower:
                return dict(template)
        return None

    def add_tolerance_manufacturing_template(
        self,
        name: str,
        *,
        source_type: str = "",
        source_id: str = "",
        tags: object = (),
        note: str = "",
    ) -> dict[str, object]:
        template = self._normalize_tolerance_manufacturing_template(
            {
                "name": name,
                "source_type": source_type,
                "source_id": source_id,
                "tags": tags,
                "note": note,
            }
        )
        if not template:
            raise ValueError("Manufacturing template requires a name and at least one metadata field.")
        templates = [
            existing
            for existing in self._normalize_tolerance_manufacturing_templates(
                self.__dict__.get("tolerance_manufacturing_templates", [])
            )
            if str(existing.get("name", "")) != str(template.get("name", ""))
        ]
        templates.append(template)
        self.tolerance_manufacturing_templates = templates
        return dict(template)

    def apply_tolerance_manufacturing_template(
        self,
        surface_index: int,
        parameter: str,
        template_or_name: str | dict[str, object],
    ) -> dict[str, object]:
        if isinstance(template_or_name, dict):
            template = self._normalize_tolerance_manufacturing_template(template_or_name)
        else:
            template = self._tolerance_manufacturing_template_by_name(str(template_or_name)) or {}
        if not template:
            raise ValueError("Manufacturing template was not found.")
        self.set_tolerance_manufacturing_metadata(
            surface_index,
            parameter,
            source_type=str(template.get("source_type", "") or ""),
            source_id=str(template.get("source_id", "") or ""),
            tags=template.get("tags", ()),
            note=str(template.get("note", "") or ""),
        )
        return dict(template)

    def save_current_tolerance_manufacturing_template(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        index = self._table_item_row_index(self.current_menu_row_id)
        if index is None:
            return
        row = self.rows[index]
        spec = self._variable_spec_for_field(self.current_menu_field)
        if spec is None:
            return
        metadata = self._row_tolerance_manufacturing(row, spec.parameter)
        if not metadata:
            self._cleanup_current_popup_menu()
            return
        default_name = str(metadata.get("source_id", "") or metadata.get("source_type", "") or f"{row.name} {spec.label}")
        name = simpledialog.askstring(
            "Save Manufacturing Template",
            "Template name:",
            initialvalue=default_name,
            parent=self,
        )
        if name is None:
            return
        name_text = str(name).strip()
        if not name_text:
            self._cleanup_current_popup_menu()
            return
        self._begin_history_capture()
        template = self.add_tolerance_manufacturing_template(
            name_text,
            source_type=str(metadata.get("source_type", "") or ""),
            source_id=str(metadata.get("source_id", "") or ""),
            tags=metadata.get("tags", ()),
            note=str(metadata.get("note", "") or ""),
        )
        self._commit_history_capture()
        message = f"Saved manufacturing template: {template.get('name', '')}."
        self.append_progress(message)
        self.status_var.set(message)
        self._cleanup_current_popup_menu()

    def apply_current_tolerance_manufacturing_template(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        index = self._table_item_row_index(self.current_menu_row_id)
        if index is None:
            return
        row = self.rows[index]
        spec = self._variable_spec_for_field(self.current_menu_field)
        if spec is None or not self._variable_enabled_for_row(row, spec):
            return
        templates = self._normalize_tolerance_manufacturing_templates(
            self.__dict__.get("tolerance_manufacturing_templates", [])
        )
        if not templates:
            self._cleanup_current_popup_menu()
            return
        names = [str(template.get("name", "") or "") for template in templates if str(template.get("name", "") or "")]
        value = simpledialog.askstring(
            "Apply Manufacturing Template",
            "Enter template name.\nAvailable: " + ", ".join(names),
            initialvalue=names[0] if names else "",
            parent=self,
        )
        if value is None:
            return
        template_name = str(value).strip()
        if not template_name:
            self._cleanup_current_popup_menu()
            return
        template = self._tolerance_manufacturing_template_by_name(template_name)
        if template is None:
            messagebox.showerror(
                "Manufacturing Template",
                f"Template not found: {template_name}",
                parent=self,
            )
            self._cleanup_current_popup_menu()
            return
        self._begin_history_capture()
        self.apply_tolerance_manufacturing_template(index, spec.parameter, template)
        self._sync_table()
        self._commit_history_capture()
        message = f"Applied manufacturing template {template.get('name', '')} to row {index} {spec.label}."
        self.append_progress(message)
        self.status_var.set(message)
        self._cleanup_current_popup_menu()

    @staticmethod
    def _tolerance_preset_int(value: object, default: int, min_value: int, max_value: int) -> int:
        try:
            parsed = int(value)
        except Exception:
            parsed = int(default)
        return max(int(min_value), min(int(max_value), int(parsed)))

    @staticmethod
    def _tolerance_preset_bool(value: object, default: bool = True) -> bool:
        if isinstance(value, str):
            text = value.strip().lower()
            if text in {"1", "true", "yes", "on", "compensator", "enabled"}:
                return True
            if text in {"0", "false", "no", "off", "tolerance-only", "disabled"}:
                return False
        if value is None:
            return bool(default)
        return bool(value)

    @classmethod
    def _normalize_tolerance_solve_preset(
        cls,
        value: object,
        *,
        fallback_name: str = "Tolerance solve",
    ) -> dict[str, object]:
        if not isinstance(value, dict):
            return {}
        name = str(value.get("name", fallback_name) or fallback_name).strip()
        if not name:
            return {}
        compare_view = str(value.get("tolerance_compare_view", TOLERANCE_COMPARE_VIEW_DEFAULT) or "").strip()
        if compare_view not in TOLERANCE_COMPARE_VIEW_VALUES:
            compare_view = TOLERANCE_COMPARE_VIEW_DEFAULT
        selected_operands = [
            str(label).strip()
            for label in list(value.get("selected_operands", []) or [])
            if str(label).strip()
        ]
        operands: dict[str, dict[str, object]] = {}
        raw_operands = value.get("operands", {})
        if isinstance(raw_operands, dict):
            for label, payload in raw_operands.items():
                if not isinstance(payload, dict):
                    continue
                clean_payload: dict[str, object] = {}
                for key, item in payload.items():
                    if isinstance(item, (str, int, float, bool)) or item is None:
                        clean_payload[str(key)] = item
                    else:
                        clean_payload[str(key)] = str(item)
                if clean_payload:
                    operands[str(label)] = clean_payload
        compensators: list[dict[str, object]] = []
        seen_compensators: set[tuple[int, str]] = set()
        for item in list(value.get("compensators", []) or []):
            if not isinstance(item, dict):
                continue
            try:
                surface_index = int(item.get("surface_index", -1))
            except Exception:
                surface_index = -1
            parameter = str(item.get("parameter", "") or "").strip()
            if surface_index < 0 or not parameter:
                continue
            key = (surface_index, parameter.lower())
            if key in seen_compensators:
                continue
            seen_compensators.add(key)
            enabled_value = item.get("compensator", item.get("enabled", True))
            coupling_group = str(item.get("coupling_group", "") or "").strip()
            if not coupling_group and "coupling" in item:
                coupling_text = str(item.get("coupling", "") or "").strip()
                coupling_group = coupling_text[1:].strip() if coupling_text.startswith("-") else coupling_text
                item = dict(item)
                item.setdefault("coupling_sign", -1 if coupling_text.startswith("-") else 1)
            manufacturing = cls._tolerance_manufacturing_record_fields(
                {
                    "source_type": item.get("manufacturing_source_type", item.get("source_type", item.get("process", ""))),
                    "source_id": item.get("manufacturing_source_id", item.get("source_id", item.get("spec_id", ""))),
                    "tags": item.get("manufacturing_tags", item.get("tags", ())),
                    "note": item.get("manufacturing_note", item.get("note", "")),
                }
            )
            compensators.append(
                {
                    "surface_index": surface_index,
                    "surface_name": str(item.get("surface_name", "") or ""),
                    "parameter": parameter,
                    "name": str(item.get("name", "") or ""),
                    "nominal": item.get("nominal", ""),
                    "lower": item.get("lower", ""),
                    "upper": item.get("upper", ""),
                    "compensator": cls._tolerance_preset_bool(enabled_value, True),
                    **(
                        {
                            "coupling_group": coupling_group,
                            "coupling_sign": cls._tolerance_coupling_sign(
                                item.get("coupling_sign", item.get("coupling_direction", 1))
                            ),
                        }
                        if coupling_group or "coupling_group" in item or "coupling_sign" in item or "coupling" in item
                        else {}
                    ),
                    **manufacturing,
                }
            )
        return {
            "name": name,
            "sample_count": cls._tolerance_preset_int(
                value.get("sample_count", TOLERANCE_SOLVE_PRESET_DEFAULTS["sample_count"]), 25, 1, 1000
            ),
            "seed": cls._tolerance_preset_int(
                value.get("seed", TOLERANCE_SOLVE_PRESET_DEFAULTS["seed"]), 12345, 0, 2**31 - 1
            ),
            "compensator_steps": cls._tolerance_preset_int(
                value.get("compensator_steps", TOLERANCE_SOLVE_PRESET_DEFAULTS["compensator_steps"]), 9, 3, 101
            ),
            "multi_steps": cls._tolerance_preset_int(
                value.get("multi_steps", TOLERANCE_SOLVE_PRESET_DEFAULTS["multi_steps"]), 5, 3, 51
            ),
            "multi_passes": cls._tolerance_preset_int(
                value.get("multi_passes", TOLERANCE_SOLVE_PRESET_DEFAULTS["multi_passes"]), 2, 1, 20
            ),
            "tolerance_compare_view": compare_view,
            "selected_operands": selected_operands,
            "operands": operands,
            "compensator_policy": str(value.get("compensator_policy", "explicit") or "explicit"),
            "coupling_policy": str(value.get("coupling_policy", "preserve") or "preserve"),
            "manufacturing_policy": str(value.get("manufacturing_policy", "preserve") or "preserve"),
            "compensators": compensators,
        }

    @classmethod
    def _normalize_tolerance_solve_presets(cls, value: object) -> list[dict[str, object]]:
        raw_items: list[object]
        if isinstance(value, dict):
            if isinstance(value.get("presets"), (list, tuple)):
                raw_items = list(value.get("presets", []) or [])
            elif "name" in value:
                raw_items = [value]
            else:
                raw_items = [
                    dict(payload, name=str(name))
                    for name, payload in value.items()
                    if isinstance(payload, dict)
                ]
        elif isinstance(value, (list, tuple)):
            raw_items = list(value)
        else:
            raw_items = []
        presets: list[dict[str, object]] = []
        seen_names: set[str] = set()
        for index, item in enumerate(raw_items, start=1):
            preset = cls._normalize_tolerance_solve_preset(item, fallback_name=f"Preset {index}")
            name = str(preset.get("name", "") or "")
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            presets.append(preset)
        return presets

    def _active_tolerance_solve_preset(self) -> dict[str, object]:
        presets = self._normalize_tolerance_solve_presets(getattr(self, "tolerance_solve_presets", []))
        active_name = str(getattr(self, "active_tolerance_solve_preset_name", "") or "").strip()
        for preset in presets:
            if str(preset.get("name", "")) == active_name:
                return dict(preset)
        return dict(presets[0]) if presets else {}

    def _tolerance_solve_preset_by_name(self, name: str) -> dict[str, object] | None:
        wanted = str(name or "").strip()
        for preset in self._normalize_tolerance_solve_presets(getattr(self, "tolerance_solve_presets", [])):
            if str(preset.get("name", "")) == wanted:
                return dict(preset)
        return None

    def _current_tolerance_preset_operands(self) -> tuple[list[str], dict[str, dict[str, object]]]:
        selected = self._selected_operand_labels()
        operands: dict[str, dict[str, object]] = {}
        var_maps = (
            ("weight", getattr(self, "operand_weight_vars", {}) or {}),
            ("target", getattr(self, "operand_target_vars", {}) or {}),
            ("wavelength", getattr(self, "operand_wavelength_vars", {}) or {}),
            ("field", getattr(self, "operand_field_vars", {}) or {}),
            ("field_x", getattr(self, "operand_field_x_vars", {}) or {}),
            ("field_y", getattr(self, "operand_field_y_vars", {}) or {}),
            ("surface", getattr(self, "operand_surface_vars", {}) or {}),
            ("aperture_type", getattr(self, "operand_aperture_type_vars", {}) or {}),
            ("aperture_value", getattr(self, "operand_aperture_value_vars", {}) or {}),
            ("frequency", getattr(self, "operand_frequency_vars", {}) or {}),
            ("mtf_mode", getattr(self, "operand_mtf_mode_vars", {}) or {}),
            ("mtf_algorithm", getattr(self, "operand_mtf_algorithm_vars", {}) or {}),
        )
        labels = {spec.label for spec in OPERAND_REGISTRY.values()}
        labels.update(selected)
        for _key, mapping in var_maps:
            labels.update(str(label) for label in mapping)
        for label in labels:
            payload: dict[str, object] = {}
            for key, mapping in var_maps:
                var = mapping.get(label)
                if var is not None:
                    try:
                        payload[key] = var.get()
                    except Exception:
                        pass
            if payload:
                operands[str(label)] = payload
        return selected, operands

    def _current_tolerance_compensator_preset_payload(self) -> list[dict[str, object]]:
        payload: list[dict[str, object]] = []
        for variable in self._build_optimization_variables():
            surface_index = int(variable.surface_index)
            row = self.rows[surface_index]
            coupling = self._tolerance_variable_coupling(variable)
            manufacturing = self._tolerance_variable_manufacturing(variable)
            try:
                nominal = float(self._optimization_value_from_row(row, variable))
            except Exception:
                nominal = float("nan")
            payload.append(
                {
                    "surface_index": surface_index,
                    "surface_name": str(row.name or ""),
                    "parameter": str(variable.parameter),
                    "name": variable.normalized_name(),
                    "nominal": nominal,
                    "lower": float(variable.lower_bound),
                    "upper": float(variable.upper_bound),
                    "compensator": self._tolerance_variable_compensator_enabled(variable),
                    **(
                        {
                            "coupling_group": str(coupling.get("group", "") or ""),
                            "coupling_sign": int(coupling.get("sign", 1) or 1),
                        }
                        if coupling
                        else {}
                    ),
                    **self._tolerance_manufacturing_record_fields(manufacturing),
                }
            )
        return payload

    def save_tolerance_solve_preset(
        self,
        name: str,
        *,
        sample_count: int | None = None,
        seed: int | None = None,
        compensator_steps: int | None = None,
        multi_steps: int | None = None,
        multi_passes: int | None = None,
        tolerance_compare_view: str | None = None,
    ) -> dict[str, object]:
        active = self._active_tolerance_solve_preset()
        selected_operands, operands = self._current_tolerance_preset_operands()
        compare_view = tolerance_compare_view or self._current_tolerance_compare_view()
        preset = self._normalize_tolerance_solve_preset(
            {
                "name": name,
                "sample_count": sample_count if sample_count is not None else active.get("sample_count", 25),
                "seed": seed if seed is not None else active.get("seed", 12345),
                "compensator_steps": (
                    compensator_steps if compensator_steps is not None else active.get("compensator_steps", 9)
                ),
                "multi_steps": multi_steps if multi_steps is not None else active.get("multi_steps", 5),
                "multi_passes": multi_passes if multi_passes is not None else active.get("multi_passes", 2),
                "tolerance_compare_view": compare_view,
                "selected_operands": selected_operands,
                "operands": operands,
                "compensator_policy": "explicit",
                "coupling_policy": "explicit",
                "manufacturing_policy": "explicit",
                "compensators": self._current_tolerance_compensator_preset_payload(),
            }
        )
        if not preset:
            raise ValueError("Tolerance solve preset name is required.")
        presets = [
            existing
            for existing in self._normalize_tolerance_solve_presets(getattr(self, "tolerance_solve_presets", []))
            if str(existing.get("name", "")) != str(preset.get("name", ""))
        ]
        presets.append(preset)
        self.tolerance_solve_presets = presets
        self.active_tolerance_solve_preset_name = str(preset.get("name", ""))
        return dict(preset)

    def apply_tolerance_solve_preset(self, preset_or_name: str | dict[str, object]) -> dict[str, object]:
        return self._tolerance_analysis_service().apply_tolerance_solve_preset(preset_or_name)

    def tolerance_solve_preset_report_text(self, preset: dict[str, object] | None = None) -> str:
        resolved = dict(preset if preset is not None else self._active_tolerance_solve_preset())
        if not resolved:
            return "# KrakenOS Tolerance Solve Preset\n\nNo active preset.\n"
        compensators = list(resolved.get("compensators", []) or [])
        enabled = [record for record in compensators if bool(dict(record).get("compensator", True))]
        lines = [
            "# KrakenOS Tolerance Solve Preset",
            "",
            f"Name: {resolved.get('name', '')}",
            f"Monte Carlo samples: {int(resolved.get('sample_count', 0) or 0)}",
            f"Seed: {int(resolved.get('seed', 0) or 0)}",
            f"Compensator sweep steps: {int(resolved.get('compensator_steps', 0) or 0)}",
            f"Multi-compensator steps/passes: {int(resolved.get('multi_steps', 0) or 0)}/{int(resolved.get('multi_passes', 0) or 0)}",
            f"Tolerance compare view: {resolved.get('tolerance_compare_view', TOLERANCE_COMPARE_VIEW_DEFAULT)}",
            f"Merit operands: {', '.join(str(label) for label in list(resolved.get('selected_operands', []) or [])) or 'default Spot RMS'}",
            f"Compensators: {len(enabled)} enabled / {len(compensators)} marked tolerance variable(s)",
            "",
            "Tolerance variable roles:",
        ]
        if compensators:
            for record in compensators:
                item = dict(record)
                role = "compensator" if bool(item.get("compensator", True)) else "tolerance-only"
                coupling_group = str(item.get("coupling_group", "") or "").strip()
                coupling = ""
                if coupling_group:
                    coupling = " coupling={}{}".format(
                        "-" if int(item.get("coupling_sign", 1) or 1) < 0 else "",
                        coupling_group,
                    )
                manufacturing = self._format_tolerance_manufacturing_inline(item)
                lines.append(f"- S{item.get('surface_index')} {item.get('parameter')}: {role}{coupling}{manufacturing}")
        else:
            lines.append("- none marked at save time")
        return "\n".join(lines).strip() + "\n"

    def open_save_tolerance_solve_preset_dialog(self) -> None:
        self._main_tolerance_report_dialogs().open_save_tolerance_solve_preset_dialog()

    def open_apply_tolerance_solve_preset_dialog(self) -> None:
        self._main_tolerance_report_dialogs().open_apply_tolerance_solve_preset_dialog()

    @classmethod
    def _tolerance_compensator_indices_from_records(cls, variable_records: list[dict[str, object]]) -> list[int]:
        if not variable_records:
            return []
        if any("compensator" in record for record in variable_records):
            return [
                index
                for index, record in enumerate(variable_records)
                if bool(record.get("compensator", True))
            ]
        return list(range(len(variable_records)))

    @staticmethod
    def _tolerance_optical_variables_from_records(variable_records: list[dict[str, object]]) -> list[OpticalVariable]:
        variables: list[OpticalVariable] = []
        for record in variable_records:
            surface_index = int(record.get("surface_index", -1))
            parameter = str(record.get("parameter", "") or "")
            if surface_index < 0 or not parameter:
                raise RuntimeError("Tolerance summary contains an invalid variable record.")
            variables.append(
                OpticalVariable(
                    surface_index,
                    parameter,
                    float(record.get("lower", np.nan)),
                    float(record.get("upper", np.nan)),
                    name=str(record.get("name", "") or ""),
                )
            )
        return variables

    def _tolerance_sample_values_from_record(
        self,
        record: dict[str, object],
        variable_records: list[dict[str, object]],
    ) -> list[float]:
        values: list[float] = []
        for variable in variable_records:
            key = self._tolerance_variable_key(variable)
            default = float(variable.get("nominal", np.nan))
            value = self._tolerance_record_float(record, key, default)
            if not np.isfinite(value):
                raise RuntimeError(f"Tolerance sample is missing finite value for {key}.")
            values.append(float(value))
        return values

    def _tolerance_system_for_record(
        self,
        base_system,
        variable_records: list[dict[str, object]],
        record: dict[str, object],
    ):
        variables = self._tolerance_optical_variables_from_records(variable_records)
        values = self._tolerance_sample_values_from_record(record, variable_records)
        evaluator = MeritEvaluator(base_system.SDT, setup=base_system.SETUP, merit_function=MeritFunction([]))
        surfaces = evaluator.apply_variables(variables, values)
        sink = io.StringIO()
        with redirect_stdout(sink), redirect_stderr(sink):
            return Kos.system(surfaces, base_system.SETUP, build=1)

    @staticmethod
    def _tolerance_unique_sweep_values(*value_sets: object) -> list[float]:
        values: dict[float, float] = {}
        for value_set in value_sets:
            arr = np.asarray(value_set, dtype=float).ravel()
            for value in arr:
                if not np.isfinite(value):
                    continue
                values[round(float(value), 12)] = float(value)
        return [values[key] for key in sorted(values)]

    def run_tolerance_compensator_sweep(
        self,
        summary: dict[str, object] | None = None,
        *,
        steps: int = 9,
    ) -> dict[str, object]:
        return self._tolerance_analysis_service().run_tolerance_compensator_sweep(
            summary,
            steps=steps,
        )

    def tolerance_compensator_sweep_report_text(self, summary: dict[str, object] | None = None) -> str:
        summary = dict(summary if summary is not None else self._last_tolerance_compensator_summary)
        if not summary:
            return "# KrakenOS Tolerance Compensator Sweep\n\nNo compensator sweep has been executed.\n"
        best = dict(summary.get("best_compensator", {}) or {})
        lines = [
            "# KrakenOS Tolerance Compensator Sweep",
            "",
            f"Base worst sample: {summary.get('base_sample')}",
            f"Base worst merit: {float(summary.get('base_total_merit', np.nan)):.6g}",
            f"Sweep steps per compensator: {int(summary.get('steps', 0) or 0)} plus nominal/worst values",
            f"Eligible compensators: {int(summary.get('compensator_count', 0) or 0)}",
            f"Valid/invalid evaluations: {int(summary.get('valid_count', 0) or 0)}/{int(summary.get('invalid_count', 0) or 0)}",
            f"Merit operands: {', '.join(str(label) for label in list(summary.get('operand_labels', []) or []))}",
            "",
            "Best compensation:",
        ]
        if best:
            coupling_group = str(best.get("coupling_group", "") or "").strip()
            coupling = ""
            if coupling_group:
                coupling = ", coupling={}{}".format(
                    "-" if int(best.get("coupling_sign", 1) or 1) < 0 else "",
                    coupling_group,
                )
            manufacturing = self._format_tolerance_manufacturing_inline(best)
            lines.append(
                "- {name}: value={value:.6g}, merit={merit:.6g}, improvement={improvement:.6g}{coupling}{manufacturing}".format(
                    name=best.get("compensator", ""),
                    value=float(best.get("value", np.nan)),
                    merit=float(best.get("total_merit", np.nan)),
                    improvement=float(best.get("improvement_vs_worst", np.nan)),
                    coupling=coupling,
                    manufacturing=manufacturing,
                )
            )
        else:
            lines.append("- none")
        lines.extend(["", "Best per compensator:"])
        for record in list(summary.get("best_by_compensator", []) or []):
            coupling_group = str(record.get("coupling_group", "") or "").strip()
            coupling = ""
            if coupling_group:
                coupling = ", coupling={}{}".format(
                    "-" if int(record.get("coupling_sign", 1) or 1) < 0 else "",
                    coupling_group,
                )
            manufacturing = self._format_tolerance_manufacturing_inline(record)
            lines.append(
                "- {name}: value={value:.6g}, merit={merit:.6g}, improvement={improvement:.6g}{coupling}{manufacturing}".format(
                    name=record.get("compensator", ""),
                    value=float(record.get("value", np.nan)),
                    merit=float(record.get("total_merit", np.nan)),
                    improvement=float(record.get("improvement_vs_worst", np.nan)),
                    coupling=coupling,
                    manufacturing=manufacturing,
                )
            )
        return "\n".join(lines).strip() + "\n"

    def tolerance_compensator_csv_rows(
        self,
        summary: dict[str, object] | None = None,
    ) -> tuple[list[str], list[dict[str, object]]]:
        summary = dict(summary if summary is not None else self._last_tolerance_compensator_summary)
        rows = [dict(record) for record in list(summary.get("records", []) or [])]
        columns: list[str] = []
        for preferred in (
            "compensator",
            "compensator_key",
            "surface_index",
            "parameter",
            "coupling_group",
            "coupling_sign",
            "manufacturing_source_type",
            "manufacturing_source_id",
            "manufacturing_tags",
            "manufacturing_note",
            "step",
            "value",
            "nominal_value",
            "worst_value",
            "lower",
            "upper",
            "base_sample",
            "valid",
            "total_merit",
            "worst_total_merit",
            "delta_vs_worst",
            "improvement_vs_worst",
            "is_nominal_value",
            "is_worst_value",
            "message",
        ):
            if any(preferred in row for row in rows):
                columns.append(preferred)
        for row in rows:
            for key in row:
                if key not in columns:
                    columns.append(str(key))
        return columns, rows

    def run_tolerance_multi_compensator_solve(
        self,
        summary: dict[str, object] | None = None,
        *,
        steps: int = 5,
        passes: int = 2,
    ) -> dict[str, object]:
        return self._tolerance_analysis_service().run_tolerance_multi_compensator_solve(
            summary,
            steps=steps,
            passes=passes,
        )

    def tolerance_multi_compensator_report_text(self, summary: dict[str, object] | None = None) -> str:
        summary = dict(summary if summary is not None else self._last_tolerance_multi_compensator_summary)
        if not summary:
            return "# KrakenOS Tolerance Multi-Compensator Solve\n\nNo multi-compensator solve has been executed.\n"
        lines = [
            "# KrakenOS Tolerance Multi-Compensator Solve",
            "",
            f"Base worst sample: {summary.get('base_sample')}",
            f"Base worst merit: {float(summary.get('base_total_merit', np.nan)):.6g}",
            f"Final merit: {float(summary.get('final_total_merit', np.nan)):.6g}",
            f"Improvement vs worst: {float(summary.get('improvement_vs_worst', np.nan)):.6g}",
            f"Passes completed/requested: {int(summary.get('passes_completed', 0) or 0)}/{int(summary.get('passes_requested', 0) or 0)}",
            f"Sweep steps per variable: {int(summary.get('steps', 0) or 0)} plus nominal/current/worst values",
            f"Eligible compensators: {int(summary.get('compensator_count', 0) or 0)}",
            f"Accepted steps: {len(list(summary.get('accepted_records', []) or []))}",
            f"Valid/invalid evaluations: {int(summary.get('valid_count', 0) or 0)}/{int(summary.get('invalid_count', 0) or 0)}",
            f"Merit operands: {', '.join(str(label) for label in list(summary.get('operand_labels', []) or []))}",
            "",
            "Solved compensator values:",
        ]
        for record in list(summary.get("solved_variables", []) or []):
            role = "compensator" if bool(record.get("compensator", True)) else "held tolerance"
            coupling_group = str(record.get("coupling_group", "") or "").strip()
            coupling = ""
            if coupling_group:
                coupling = ", coupling={}{}".format(
                    "-" if int(record.get("coupling_sign", 1) or 1) < 0 else "",
                    coupling_group,
                )
            manufacturing = self._format_tolerance_manufacturing_inline(record)
            lines.append(
                "- {name}: worst={worst:.6g}, solved={solved:.6g}, nominal={nominal:.6g}, role={role}{coupling}{manufacturing}".format(
                    name=record.get("name", ""),
                    worst=float(record.get("worst", np.nan)),
                    solved=float(record.get("solved", np.nan)),
                    nominal=float(record.get("nominal", np.nan)),
                    role=role,
                    coupling=coupling,
                    manufacturing=manufacturing,
                )
            )
        lines.extend(["", "Accepted coordinate steps:"])
        accepted = list(summary.get("accepted_records", []) or [])
        if accepted:
            for record in accepted[:12]:
                lines.append(
                    "- pass {pass_no} {name}: {previous:.6g} -> {value:.6g}, merit {old:.6g} -> {new:.6g}".format(
                        pass_no=int(record.get("pass", 0) or 0),
                        name=record.get("compensator", ""),
                        previous=float(record.get("previous_value", np.nan)),
                        value=float(record.get("value", np.nan)),
                        old=float(record.get("previous_total_merit", np.nan)),
                        new=float(record.get("total_merit", np.nan)),
                    )
                )
        else:
            lines.append("- none")
        return "\n".join(lines).strip() + "\n"

    def tolerance_multi_compensator_csv_rows(
        self,
        summary: dict[str, object] | None = None,
    ) -> tuple[list[str], list[dict[str, object]]]:
        summary = dict(summary if summary is not None else self._last_tolerance_multi_compensator_summary)
        rows = [dict(record) for record in list(summary.get("records", []) or [])]
        columns: list[str] = []
        for preferred in (
            "pass",
            "compensator",
            "compensator_key",
            "surface_index",
            "parameter",
            "coupling_group",
            "coupling_sign",
            "manufacturing_source_type",
            "manufacturing_source_id",
            "manufacturing_tags",
            "manufacturing_note",
            "step",
            "value",
            "previous_value",
            "nominal_value",
            "worst_value",
            "lower",
            "upper",
            "base_sample",
            "valid",
            "accepted",
            "total_merit",
            "previous_total_merit",
            "base_total_merit",
            "delta_vs_previous",
            "improvement_vs_previous",
            "improvement_vs_worst",
            "is_nominal_value",
            "is_worst_value",
            "message",
        ):
            if any(preferred in row for row in rows):
                columns.append(preferred)
        for row in rows:
            for key in row:
                if key not in columns:
                    columns.append(str(key))
        return columns, rows

    @staticmethod
    def _tolerance_spot_cloud(x_values, y_values) -> dict[str, object]:
        x = np.asarray(x_values, dtype=float).ravel()
        y = np.asarray(y_values, dtype=float).ravel()
        finite = np.isfinite(x) & np.isfinite(y)
        x = x[finite]
        y = y[finite]
        if x.size == 0:
            return {
                "x": x,
                "y": y,
                "count": 0,
                "centroid_x": np.nan,
                "centroid_y": np.nan,
                "rms_radius": np.nan,
            }
        centroid_x = float(np.mean(x))
        centroid_y = float(np.mean(y))
        radius = np.sqrt((x - centroid_x) * (x - centroid_x) + (y - centroid_y) * (y - centroid_y))
        return {
            "x": x,
            "y": y,
            "count": int(x.size),
            "centroid_x": centroid_x,
            "centroid_y": centroid_y,
            "rms_radius": float(np.sqrt(np.mean(radius * radius))),
        }

    def _tolerance_spot_cloud_for_system(self, system, wavelength: float, sample_count: int) -> dict[str, object]:
        rays = self._build_analysis_rays(
            system,
            float(wavelength),
            sample_count=max(2, int(sample_count)),
            pattern="hexapolar",
        )
        x_values, y_values, _z_values, _l_values, _m_values, _n_values = self._pick_image_plane_data(rays)
        return self._tolerance_spot_cloud(x_values, y_values)

    def _tolerance_nominal_worst_context(
        self,
        summary: dict[str, object] | None = None,
        *,
        base_system=None,
    ) -> dict[str, object]:
        summary = dict(summary if summary is not None else self._last_tolerance_monte_carlo_summary)
        if not summary:
            raise RuntimeError("Run Tolerance Monte Carlo Report first.")
        records = list(summary.get("records", []) or [])
        if not records:
            raise RuntimeError("Tolerance Monte Carlo has no sample records.")
        variable_records = [dict(item) for item in list(summary.get("variables", []) or [])]
        if not variable_records:
            raise RuntimeError("Tolerance Monte Carlo has no variable records.")
        nominal_record = next((record for record in records if str(record.get("kind", "")) == "nominal"), records[0])
        comparison = self.tolerance_worst_sample_comparison(summary)
        worst_sample = int(comparison.get("perturbed_sample", 0) or 0)
        worst_record = next((record for record in records if int(record.get("sample", -1) or -1) == worst_sample), None)
        if worst_record is None:
            raise RuntimeError(f"Worst tolerance sample {worst_sample} is not available in the Monte Carlo records.")
        resolved_system = base_system if base_system is not None else self.build_system()
        nominal_system = self._tolerance_system_for_record(resolved_system, variable_records, nominal_record)
        worst_system = self._tolerance_system_for_record(resolved_system, variable_records, worst_record)
        return {
            "summary": summary,
            "records": records,
            "variable_records": variable_records,
            "nominal_record": nominal_record,
            "worst_record": worst_record,
            "worst_sample": worst_sample,
            "comparison": comparison,
            "base_system": resolved_system,
            "nominal_system": nominal_system,
            "worst_system": worst_system,
        }

    def tolerance_nominal_worst_spot_overlay(
        self,
        summary: dict[str, object] | None = None,
        *,
        base_system=None,
        sample_count: int | None = None,
        wavelength: float | None = None,
    ) -> dict[str, object]:
        context = self._tolerance_nominal_worst_context(summary, base_system=base_system)
        nominal_record = dict(context["nominal_record"])
        worst_record = dict(context["worst_record"])
        resolved_wavelength = float(self._current_wavelength() if wavelength is None else wavelength)
        resolved_sample_count = int(
            max(
                12,
                min(96, int(sample_count) if sample_count is not None else max(24, self._current_ray_count() * 6)),
            )
        )

        nominal_cloud = self._tolerance_spot_cloud_for_system(context["nominal_system"], resolved_wavelength, resolved_sample_count)
        worst_cloud = self._tolerance_spot_cloud_for_system(context["worst_system"], resolved_wavelength, resolved_sample_count)

        overlay = {
            "sample_count": resolved_sample_count,
            "wavelength": resolved_wavelength,
            "nominal_sample": int(nominal_record.get("sample", 0) or 0),
            "worst_sample": int(context["worst_sample"]),
            "nominal_total_merit": self._tolerance_record_float(nominal_record, "total_merit"),
            "worst_total_merit": self._tolerance_record_float(worst_record, "total_merit"),
            "nominal": nominal_cloud,
            "worst": worst_cloud,
            "comparison": context["comparison"],
        }
        nominal_rms = float(nominal_cloud.get("rms_radius", np.nan))
        worst_rms = float(worst_cloud.get("rms_radius", np.nan))
        overlay["delta_rms_radius"] = worst_rms - nominal_rms if np.isfinite(nominal_rms) and np.isfinite(worst_rms) else np.nan
        self._last_tolerance_spot_overlay = overlay
        return overlay

    def _tolerance_mtf_curve_for_system(
        self,
        system,
        wavelength: float,
        sample_count: int,
        mtf_settings: dict[str, float | int | str],
        field_sample: dict[str, float | str],
    ) -> dict[str, object]:
        rays = self._build_analysis_rays(
            system,
            float(wavelength),
            sample_count=max(4, int(sample_count)),
            pattern="hexapolar",
            surface_index=int(mtf_settings["surface_index"]),
            aperture_type=str(mtf_settings["aperture_type"]),
            aperture_value=float(mtf_settings["aperture_value"]),
            field_type=str(field_sample["field_type"]),
            field_x=float(field_sample["field_x"]),
            field_y=float(field_sample["field_y"]),
        )
        x_values, y_values, _z_values, _l_values, _m_values, _n_values = self._pick_image_plane_data(rays)
        result = self._geometric_mtf_result_from_image_samples(
            np.asarray(x_values, dtype=float),
            np.asarray(y_values, dtype=float),
            worker_count=1,
            sample_count=int(sample_count),
            algorithm=str(mtf_settings.get("algorithm", "psf_fft")),
        )
        plot_freq = np.asarray(result["plot_freq"], dtype=float)
        plot_tan = np.asarray(result["plot_tan"], dtype=float)
        plot_sag = np.asarray(result["plot_sag"], dtype=float)
        count = min(plot_freq.size, plot_tan.size, plot_sag.size)
        if count < 2:
            raise RuntimeError("Tolerance MTF overlay has too few frequency samples.")
        result["plot_freq"] = plot_freq[:count]
        result["plot_tan"] = plot_tan[:count]
        result["plot_sag"] = plot_sag[:count]
        result["plot_avg"] = 0.5 * (plot_tan[:count] + plot_sag[:count])
        return result

    @staticmethod
    def _tolerance_selected_mtf_curve(result: dict[str, object], mtf_mode: str) -> tuple[np.ndarray, np.ndarray, str]:
        freq = np.asarray(result.get("plot_freq", []), dtype=float).ravel()
        if str(mtf_mode).strip().lower() == "tangential":
            return freq, np.asarray(result.get("plot_tan", []), dtype=float).ravel(), "Tangential"
        if str(mtf_mode).strip().lower() == "sagittal":
            return freq, np.asarray(result.get("plot_sag", []), dtype=float).ravel(), "Sagittal"
        return freq, np.asarray(result.get("plot_avg", []), dtype=float).ravel(), "Average"

    def tolerance_nominal_worst_mtf_overlay(
        self,
        summary: dict[str, object] | None = None,
        *,
        base_system=None,
        sample_count: int | None = None,
        wavelength: float | None = None,
    ) -> dict[str, object]:
        context = self._tolerance_nominal_worst_context(summary, base_system=base_system)
        nominal_record = dict(context["nominal_record"])
        worst_record = dict(context["worst_record"])
        mtf_settings = self._mtf_analysis_settings()
        resolved_wavelength = float(mtf_settings["wavelength"] if wavelength is None else wavelength)
        resolved_sample_count = int(
            max(
                32,
                min(160, int(sample_count) if sample_count is not None else max(48, self._current_ray_count() * 8)),
            )
        )
        field_samples = self._resolved_mtf_field_samples("MTF @ freq")
        if not field_samples:
            raise RuntimeError("Tolerance MTF overlay has no valid field sample.")
        field_sample = max(field_samples, key=lambda sample: abs(float(sample.get("display_y", 0.0))))
        nominal_curve = self._tolerance_mtf_curve_for_system(
            context["nominal_system"],
            resolved_wavelength,
            resolved_sample_count,
            mtf_settings,
            field_sample,
        )
        worst_curve = self._tolerance_mtf_curve_for_system(
            context["worst_system"],
            resolved_wavelength,
            resolved_sample_count,
            mtf_settings,
            field_sample,
        )
        mtf_mode = self._operand_mtf_mode("MTF @ freq")
        target_freq = float(self._current_mtf_frequency())
        nominal_freq, nominal_selected, selected_label = self._tolerance_selected_mtf_curve(nominal_curve, mtf_mode)
        worst_freq, worst_selected, _selected_label = self._tolerance_selected_mtf_curve(worst_curve, mtf_mode)
        nominal_value = float(np.interp(target_freq, nominal_freq, nominal_selected, left=nominal_selected[0], right=nominal_selected[-1]))
        worst_value = float(np.interp(target_freq, worst_freq, worst_selected, left=worst_selected[0], right=worst_selected[-1]))
        overlay = {
            "sample_count": resolved_sample_count,
            "wavelength": resolved_wavelength,
            "target_frequency": target_freq,
            "selected_label": selected_label,
            "field_sample": dict(field_sample),
            "nominal_sample": int(nominal_record.get("sample", 0) or 0),
            "worst_sample": int(context["worst_sample"]),
            "nominal_total_merit": self._tolerance_record_float(nominal_record, "total_merit"),
            "worst_total_merit": self._tolerance_record_float(worst_record, "total_merit"),
            "nominal": nominal_curve,
            "worst": worst_curve,
            "nominal_selected_value": nominal_value,
            "worst_selected_value": worst_value,
            "delta_selected_value": worst_value - nominal_value,
            "comparison": context["comparison"],
        }
        self._last_tolerance_mtf_overlay = overlay
        return overlay

    def _plot_tolerance_mtf_comparison_analysis(self, analysis_ax, system, wavelength: float) -> None:
        self._set_analysis_parallel_status("TolCmp MTF", 1, False)
        self._begin_analysis_progress("Tolerance MTF overlay")
        try:
            self._update_analysis_progress("Building tolerance MTF curves", 1, 3)
            overlay = self.tolerance_nominal_worst_mtf_overlay(base_system=system, wavelength=wavelength)
            mtf_mode = self._operand_mtf_mode("MTF @ freq")
            nominal_freq, nominal_selected, selected_label = self._tolerance_selected_mtf_curve(dict(overlay["nominal"]), mtf_mode)
            worst_freq, worst_selected, _selected_label = self._tolerance_selected_mtf_curve(dict(overlay["worst"]), mtf_mode)
            if nominal_freq.size < 2 or worst_freq.size < 2:
                raise RuntimeError("Tolerance MTF overlay has no finite curves.")
            self._update_analysis_progress("Rendering MTF overlay", 2, 3)
            analysis_ax.plot(
                nominal_freq,
                nominal_selected,
                color="#2563eb",
                linewidth=1.7,
                label=f"Nominal {selected_label}",
            )
            analysis_ax.plot(
                worst_freq,
                worst_selected,
                color="#dc2626",
                linewidth=1.5,
                linestyle=(0, (5, 3)),
                label=f"Worst sample {int(overlay.get('worst_sample', 0) or 0)}",
            )
            target_freq = float(overlay.get("target_frequency", np.nan))
            if np.isfinite(target_freq):
                analysis_ax.axvline(target_freq, color="#334155", linewidth=0.9, alpha=0.75)
                analysis_ax.text(
                    target_freq,
                    0.04,
                    f"ref {target_freq:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                    color="#334155",
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.55, "pad": 0.2},
                )
            max_freq = max(float(np.nanmax(nominal_freq)), float(np.nanmax(worst_freq)), target_freq * 1.1 if np.isfinite(target_freq) else 0.0)
            field_sample = dict(overlay.get("field_sample", {}) or {})
            legend = str(field_sample.get("legend", "") or "field")
            analysis_ax.set_title(f"Tolerance MTF Overlay | {legend} | {float(overlay.get('wavelength', wavelength)):.4g} um")
            analysis_ax.set_xlabel("Spatial frequency [cycles/mm]")
            analysis_ax.set_ylabel("MTF")
            analysis_ax.set_xlim(0.0, max(max_freq, 1.0))
            analysis_ax.set_ylim(0.0, 1.05)
            analysis_ax.grid(True, alpha=0.22)
            analysis_ax.legend(loc="best", fontsize=8)
            analysis_ax.text(
                0.02,
                0.02,
                "{label} @ {freq:.4g} cy/mm\n"
                "MTF {nom:.4g} -> {worst:.4g}\n"
                "Delta {delta:.4g}\n"
                "Merit {nmerit:.4g} -> {wmerit:.4g}".format(
                    label=selected_label,
                    freq=target_freq,
                    nom=float(overlay.get("nominal_selected_value", np.nan)),
                    worst=float(overlay.get("worst_selected_value", np.nan)),
                    delta=float(overlay.get("delta_selected_value", np.nan)),
                    nmerit=float(overlay.get("nominal_total_merit", np.nan)),
                    wmerit=float(overlay.get("worst_total_merit", np.nan)),
                ),
                transform=analysis_ax.transAxes,
                ha="left",
                va="bottom",
                fontsize=7.5,
                color="#111827",
                bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.84, "pad": 3},
            )
            self._update_analysis_progress("Finalizing", 3, 3)
            self.append_debug(
                "Tolerance MTF overlay ok: worst_sample={sample}, target={freq:.6g}, nominal={nom:.6g}, worst={worst:.6g}".format(
                    sample=int(overlay.get("worst_sample", 0) or 0),
                    freq=target_freq,
                    nom=float(overlay.get("nominal_selected_value", np.nan)),
                    worst=float(overlay.get("worst_selected_value", np.nan)),
                )
            )
            self._finish_analysis_progress("Tolerance MTF overlay", success=True)
        except Exception as exc:
            self.append_debug(f"Tolerance MTF overlay error: {exc}")
            analysis_ax.text(
                0.5,
                0.5,
                "Tolerance MTF overlay unavailable\nRun Tolerance Monte Carlo Report first",
                ha="center",
                va="center",
            )
            analysis_ax.set_axis_off()
            self._finish_analysis_progress("Tolerance MTF overlay", success=False)

    def _tolerance_wavefront_sample_for_system(self, system, wavelength: float) -> dict[str, object]:
        pupil = Kos.PupilCalc(
            system,
            self._analysis_surface_index(),
            float(wavelength),
            self._current_aperture_type(),
            self._current_aperture_value(),
        )
        pupil.Samp = max(8, min(22, int(np.sqrt(max(1, self._current_ray_count())) * 4)))
        pupil.Ptype = self._current_analysis_pupil_pattern("hexapolar")
        field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
        pupil.FieldType = field_type
        pupil.FieldX = 0.0
        pupil.FieldY = self._current_field_angle_deg() if field_type == "angle" else self._current_field_height()

        phase_method = "Phase"
        numpy_state = None
        try:
            if str(getattr(pupil, "Ptype", "")).strip().lower() == "rand":
                numpy_state = np.random.get_state()
                np.random.seed(self._current_source_seed())
            try:
                px, py, phase, _p2v = Kos.Phase(pupil)
            finally:
                if numpy_state is not None:
                    np.random.set_state(numpy_state)
        except Exception:
            capture = io.StringIO()
            with redirect_stdout(capture), redirect_stderr(capture):
                px, py, phase, _p2v = Kos.Phase2(pupil)
            phase_method = "Phase2"
            phase2_log = capture.getvalue().strip()
            if phase2_log:
                self.append_debug(phase2_log)

        px = np.asarray(px, dtype=float).ravel()
        py = np.asarray(py, dtype=float).ravel()
        phase = np.asarray(phase, dtype=float).ravel()
        finite = np.isfinite(px) & np.isfinite(py) & np.isfinite(phase)
        x = py[finite]
        y = px[finite]
        phase = phase[finite]
        if phase.size < 4:
            raise RuntimeError("Not enough finite wavefront samples for tolerance comparison.")
        phase_centered = phase - float(np.mean(phase))
        display_values = self._remove_wavefront_reference_plane(x, y, phase_centered)
        display_values = np.asarray(display_values, dtype=float).ravel()
        finite_display = np.isfinite(x) & np.isfinite(y) & np.isfinite(display_values)
        x = x[finite_display]
        y = y[finite_display]
        display_values = display_values[finite_display]
        if display_values.size < 4:
            raise RuntimeError("Not enough finite wavefront display samples for tolerance comparison.")
        return {
            "x": x,
            "y": y,
            "phase_waves": phase_centered[finite_display],
            "wfe_waves": display_values,
            "count": int(display_values.size),
            "phase_method": phase_method,
            "field_type": field_type,
            "rms_waves": float(np.sqrt(np.mean(display_values * display_values))),
            "pv_waves": float(np.max(display_values) - np.min(display_values)),
        }

    @staticmethod
    def _tolerance_interpolate_wavefront_to(
        source: dict[str, object],
        target_x: np.ndarray,
        target_y: np.ndarray,
    ) -> np.ndarray:
        sx = np.asarray(source.get("x", []), dtype=float).ravel()
        sy = np.asarray(source.get("y", []), dtype=float).ravel()
        sv = np.asarray(source.get("wfe_waves", []), dtype=float).ravel()
        tx = np.asarray(target_x, dtype=float).ravel()
        ty = np.asarray(target_y, dtype=float).ravel()
        if sx.shape == tx.shape and sy.shape == ty.shape and np.allclose(sx, tx, rtol=1e-9, atol=1e-9) and np.allclose(sy, ty, rtol=1e-9, atol=1e-9):
            return sv
        from matplotlib.tri import LinearTriInterpolator, Triangulation

        finite = np.isfinite(sx) & np.isfinite(sy) & np.isfinite(sv)
        if int(np.sum(finite)) < 4:
            return np.full_like(tx, np.nan, dtype=float)
        triangulation = Triangulation(sx[finite], sy[finite])
        interpolator = LinearTriInterpolator(triangulation, sv[finite])
        interpolated = interpolator(tx, ty)
        try:
            return np.asarray(interpolated.filled(np.nan), dtype=float).ravel()
        except AttributeError:
            return np.asarray(interpolated, dtype=float).ravel()

    def tolerance_nominal_worst_wavefront_overlay(
        self,
        summary: dict[str, object] | None = None,
        *,
        base_system=None,
        wavelength: float | None = None,
    ) -> dict[str, object]:
        context = self._tolerance_nominal_worst_context(summary, base_system=base_system)
        nominal_record = dict(context["nominal_record"])
        worst_record = dict(context["worst_record"])
        resolved_wavelength = float(self._current_wavelength() if wavelength is None else wavelength)
        nominal = self._tolerance_wavefront_sample_for_system(context["nominal_system"], resolved_wavelength)
        worst = self._tolerance_wavefront_sample_for_system(context["worst_system"], resolved_wavelength)
        x = np.asarray(nominal["x"], dtype=float).ravel()
        y = np.asarray(nominal["y"], dtype=float).ravel()
        nominal_wfe = np.asarray(nominal["wfe_waves"], dtype=float).ravel()
        worst_wfe = self._tolerance_interpolate_wavefront_to(worst, x, y)
        finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(nominal_wfe) & np.isfinite(worst_wfe)
        if int(np.sum(finite)) < 4:
            raise RuntimeError("Wavefront nominal/worst samples do not overlap enough for a delta map.")
        delta = worst_wfe[finite] - nominal_wfe[finite]
        delta_centered = delta - float(np.mean(delta))
        overlay = {
            "wavelength": resolved_wavelength,
            "nominal_sample": int(nominal_record.get("sample", 0) or 0),
            "worst_sample": int(context["worst_sample"]),
            "nominal_total_merit": self._tolerance_record_float(nominal_record, "total_merit"),
            "worst_total_merit": self._tolerance_record_float(worst_record, "total_merit"),
            "nominal": nominal,
            "worst": worst,
            "x": x[finite],
            "y": y[finite],
            "nominal_wfe_waves": nominal_wfe[finite],
            "worst_wfe_waves": worst_wfe[finite],
            "delta_wfe_waves": delta,
            "delta_centered_waves": delta_centered,
            "delta_rms_waves": float(np.sqrt(np.mean(delta_centered * delta_centered))),
            "delta_pv_waves": float(np.max(delta) - np.min(delta)),
            "delta_mean_waves": float(np.mean(delta)),
            "delta_nominal_rms_waves": float(worst.get("rms_waves", np.nan)) - float(nominal.get("rms_waves", np.nan)),
            "comparison": context["comparison"],
        }
        self._last_tolerance_wavefront_overlay = overlay
        return overlay

    def _plot_tolerance_wavefront_comparison_analysis(self, analysis_ax, system, wavelength: float) -> None:
        self._set_analysis_parallel_status("TolCmp WFE", 1, False)
        self._begin_analysis_progress("Tolerance wavefront delta")
        try:
            self._update_analysis_progress("Building wavefront delta", 1, 3)
            overlay = self.tolerance_nominal_worst_wavefront_overlay(base_system=system, wavelength=wavelength)
            x = np.asarray(overlay.get("x", []), dtype=float).ravel()
            y = np.asarray(overlay.get("y", []), dtype=float).ravel()
            delta = np.asarray(overlay.get("delta_centered_waves", []), dtype=float).ravel()
            finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(delta)
            x = x[finite]
            y = y[finite]
            delta = delta[finite]
            if delta.size < 4:
                raise RuntimeError("Tolerance wavefront delta has no finite samples.")
            self._update_analysis_progress("Rendering WFE delta", 2, 3)
            vmax = float(np.nanmax(np.abs(delta))) if delta.size else 1.0
            vmax = max(vmax, 1e-12)
            try:
                image = analysis_ax.tricontourf(x, y, delta, levels=48, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
            except Exception:
                image = analysis_ax.scatter(x, y, c=delta, cmap="RdBu_r", s=24, vmin=-vmax, vmax=vmax)
            analysis_ax.set_title("Tolerance Wavefront Delta")
            analysis_ax.set_xlabel("X pupil")
            analysis_ax.set_ylabel("Y pupil")
            analysis_ax.set_aspect("equal", adjustable="box")
            analysis_ax.set_box_aspect(0.72)
            analysis_ax.grid(True, alpha=0.2)
            analysis_ax.figure.colorbar(image, ax=analysis_ax, fraction=0.046, pad=0.04, label="Worst - nominal [waves]")
            nominal = dict(overlay.get("nominal", {}) or {})
            worst = dict(overlay.get("worst", {}) or {})
            analysis_ax.text(
                0.02,
                0.02,
                "Worst sample {sample}\n"
                "WFE RMS {nrms:.4g} -> {wrms:.4g} waves\n"
                "Delta RMS {drms:.4g} waves, P-V {dpv:.4g}\n"
                "Merit {nmerit:.4g} -> {wmerit:.4g}".format(
                    sample=int(overlay.get("worst_sample", 0) or 0),
                    nrms=float(nominal.get("rms_waves", np.nan)),
                    wrms=float(worst.get("rms_waves", np.nan)),
                    drms=float(overlay.get("delta_rms_waves", np.nan)),
                    dpv=float(overlay.get("delta_pv_waves", np.nan)),
                    nmerit=float(overlay.get("nominal_total_merit", np.nan)),
                    wmerit=float(overlay.get("worst_total_merit", np.nan)),
                ),
                transform=analysis_ax.transAxes,
                ha="left",
                va="bottom",
                fontsize=7.5,
                color="#111827",
                bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.84, "pad": 3},
            )
            self._update_analysis_progress("Finalizing", 3, 3)
            self.append_debug(
                "Tolerance WFE overlay ok: worst_sample={sample}, delta_rms={rms:.6g}, delta_pv={pv:.6g}".format(
                    sample=int(overlay.get("worst_sample", 0) or 0),
                    rms=float(overlay.get("delta_rms_waves", np.nan)),
                    pv=float(overlay.get("delta_pv_waves", np.nan)),
                )
            )
            self._finish_analysis_progress("Tolerance wavefront delta", success=True)
        except Exception as exc:
            self.append_debug(f"Tolerance wavefront delta error: {exc}")
            analysis_ax.text(
                0.5,
                0.5,
                "Tolerance wavefront delta unavailable\nRun Tolerance Monte Carlo Report first",
                ha="center",
                va="center",
            )
            analysis_ax.set_axis_off()
            self._finish_analysis_progress("Tolerance wavefront delta", success=False)

    def _plot_tolerance_stackup_analysis(self, analysis_ax) -> None:
        self._set_analysis_parallel_status("TolCmp Stack", 1, False)
        self._begin_analysis_progress("Tolerance stack-up bars")
        try:
            self._update_analysis_progress("Building stack-up dashboard", 1, 3)
            dashboard = self.tolerance_stackup_dashboard()
            group_rows = [dict(record) for record in list(dashboard.get("group_records", []) or [])]
            group_rows = [
                record
                for record in group_rows
                if np.isfinite(float(record.get("contribution_fraction", np.nan)))
            ]
            if not group_rows:
                raise RuntimeError("Tolerance stack-up has no finite group contributions.")
            top_rows = group_rows[: min(10, len(group_rows))]
            labels = [
                str(record.get("name", "") or record.get("group_key", "Group"))[:42]
                for record in top_rows
            ]
            values = np.asarray(
                [100.0 * float(record.get("contribution_fraction", 0.0) or 0.0) for record in top_rows],
                dtype=float,
            )
            sigmas = np.asarray(
                [float(record.get("merit_sigma_contribution", np.nan)) for record in top_rows],
                dtype=float,
            )
            colors = [
                "#0f766e" if str(record.get("stackup_type", "")) == "coupled_group" else "#2563eb"
                for record in top_rows
            ]
            self._update_analysis_progress("Rendering stack-up bars", 2, 3)
            y_positions = np.arange(len(top_rows), dtype=float)
            analysis_ax.barh(y_positions, values, color=colors, alpha=0.86)
            analysis_ax.set_yticks(y_positions)
            analysis_ax.set_yticklabels(labels, fontsize=8)
            analysis_ax.invert_yaxis()
            analysis_ax.set_xlabel("Linearized variance contribution [%]")
            analysis_ax.set_title("Tolerance Stack-Up | Manufacturing Groups")
            analysis_ax.grid(True, axis="x", alpha=0.22)
            analysis_ax.set_xlim(0.0, max(float(np.nanmax(values)) * 1.18, 5.0))
            analysis_ax.set_box_aspect(0.68)
            for index, (value, sigma, record) in enumerate(zip(values, sigmas, top_rows)):
                suffix = " coupled" if str(record.get("stackup_type", "")) == "coupled_group" else ""
                analysis_ax.text(
                    value + max(float(np.nanmax(values)) * 0.015, 0.15),
                    index,
                    f"{value:.1f}%  sigma {sigma:.3g}{suffix}",
                    va="center",
                    ha="left",
                    fontsize=7.5,
                    color="#111827",
                )
            coupled_count = sum(1 for record in group_rows if str(record.get("stackup_type", "")) == "coupled_group")
            analysis_ax.text(
                0.02,
                0.02,
                "Groups {groups}, coupled {coupled}\n"
                "Group sigma {sigma:.4g}\n"
                "Worst sample {sample}".format(
                    groups=len(group_rows),
                    coupled=coupled_count,
                    sigma=float(dashboard.get("group_linearized_sigma_estimate", np.nan)),
                    sample=int(dashboard.get("worst_sample", 0) or 0),
                ),
                transform=analysis_ax.transAxes,
                ha="left",
                va="bottom",
                fontsize=7.5,
                color="#111827",
                bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.84, "pad": 3},
            )
            self._last_tolerance_stackup_summary = dashboard
            self._update_analysis_progress("Finalizing", 3, 3)
            self.append_debug(
                "Tolerance stack-up bars ok: groups={groups}, coupled={coupled}, sigma={sigma:.6g}".format(
                    groups=len(group_rows),
                    coupled=coupled_count,
                    sigma=float(dashboard.get("group_linearized_sigma_estimate", np.nan)),
                )
            )
            self._finish_analysis_progress("Tolerance stack-up bars", success=True)
        except Exception as exc:
            self.append_debug(f"Tolerance stack-up bars error: {exc}")
            analysis_ax.text(
                0.5,
                0.5,
                "Tolerance stack-up unavailable\nRun Actions > Tolerance Monte Carlo Report first",
                ha="center",
                va="center",
            )
            analysis_ax.set_axis_off()
            self._finish_analysis_progress("Tolerance stack-up bars", success=False)

    def _plot_tolerance_comparison_analysis(self, analysis_ax, system, wavelength: float) -> None:
        if self._current_tolerance_compare_view() == "Wavefront delta":
            self._plot_tolerance_wavefront_comparison_analysis(analysis_ax, system, wavelength)
            return
        if self._current_tolerance_compare_view() == "MTF overlay":
            self._plot_tolerance_mtf_comparison_analysis(analysis_ax, system, wavelength)
            return
        if self._current_tolerance_compare_view() == "Stack-up bars":
            self._plot_tolerance_stackup_analysis(analysis_ax)
            return
        self._set_analysis_parallel_status("TolCmp", 1, False)
        self._begin_analysis_progress("Tolerance spot overlay")
        try:
            self._update_analysis_progress("Building tolerance systems", 1, 3)
            overlay = self.tolerance_nominal_worst_spot_overlay(base_system=system, wavelength=wavelength)
            nominal = dict(overlay.get("nominal", {}) or {})
            worst = dict(overlay.get("worst", {}) or {})
            nominal_x = np.asarray(nominal.get("x", []), dtype=float).ravel()
            nominal_y = np.asarray(nominal.get("y", []), dtype=float).ravel()
            worst_x = np.asarray(worst.get("x", []), dtype=float).ravel()
            worst_y = np.asarray(worst.get("y", []), dtype=float).ravel()
            if nominal_x.size == 0 or worst_x.size == 0:
                raise RuntimeError("Tolerance overlay has no finite image-plane spot samples.")

            self._update_analysis_progress("Rendering spot overlay", 2, 3)
            analysis_ax.scatter(
                nominal_x,
                nominal_y,
                s=16,
                color="#2563eb",
                alpha=0.62,
                edgecolors="none",
                label=f"Nominal ({int(nominal.get('count', nominal_x.size))})",
            )
            analysis_ax.scatter(
                worst_x,
                worst_y,
                s=18,
                marker="x",
                color="#dc2626",
                alpha=0.78,
                linewidths=0.9,
                label=f"Worst sample {int(overlay.get('worst_sample', 0) or 0)}",
            )
            for cloud, color, marker in ((nominal, "#1d4ed8", "+"), (worst, "#b91c1c", "x")):
                cx = float(cloud.get("centroid_x", np.nan))
                cy = float(cloud.get("centroid_y", np.nan))
                if np.isfinite(cx) and np.isfinite(cy):
                    analysis_ax.scatter([cx], [cy], s=56, marker=marker, color=color, linewidths=1.4, zorder=5)
            analysis_ax.set_title("Tolerance Nominal vs Worst Spot")
            analysis_ax.set_xlabel("Image X [mm]")
            analysis_ax.set_ylabel("Image Y [mm]")
            analysis_ax.set_aspect("equal", adjustable="box")
            analysis_ax.set_box_aspect(0.82)
            analysis_ax.grid(True, alpha=0.22)
            analysis_ax.legend(loc="best", fontsize=8)
            nominal_rms = float(nominal.get("rms_radius", np.nan))
            worst_rms = float(worst.get("rms_radius", np.nan))
            delta_rms = float(overlay.get("delta_rms_radius", np.nan))
            analysis_ax.text(
                0.02,
                0.02,
                "Worst sample {sample}\n"
                "Merit {nmerit:.4g} -> {wmerit:.4g}\n"
                "RMS {nrms:.4g} -> {wrms:.4g} mm\n"
                "Delta RMS {drms:.4g} mm".format(
                    sample=int(overlay.get("worst_sample", 0) or 0),
                    nmerit=float(overlay.get("nominal_total_merit", np.nan)),
                    wmerit=float(overlay.get("worst_total_merit", np.nan)),
                    nrms=nominal_rms,
                    wrms=worst_rms,
                    drms=delta_rms,
                ),
                transform=analysis_ax.transAxes,
                ha="left",
                va="bottom",
                fontsize=7.5,
                color="#111827",
                bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.84, "pad": 3},
            )
            self._update_analysis_progress("Finalizing", 3, 3)
            self.append_debug(
                "Tolerance overlay ok: worst_sample={sample}, nominal_rms={nrms:.6g}, "
                "worst_rms={wrms:.6g}, samples={count}".format(
                    sample=int(overlay.get("worst_sample", 0) or 0),
                    nrms=nominal_rms,
                    wrms=worst_rms,
                    count=int(overlay.get("sample_count", 0) or 0),
                )
            )
            self._finish_analysis_progress("Tolerance spot overlay", success=True)
        except Exception as exc:
            self.append_debug(f"Tolerance spot overlay error: {exc}")
            analysis_ax.text(
                0.5,
                0.5,
                "Tolerance overlay unavailable\nRun Actions > Tolerance Monte Carlo Report first",
                ha="center",
                va="center",
            )
            analysis_ax.set_axis_off()
            self._finish_analysis_progress("Tolerance spot overlay", success=False)

    @staticmethod
    def _csv_optional_float(value) -> float | str:
        try:
            numeric = float(value)
        except Exception:
            return ""
        return numeric if np.isfinite(numeric) else ""

    @staticmethod
    def _array_value_or_blank(values, index: int):
        array = np.asarray(values, dtype=float).ravel()
        if 0 <= int(index) < array.size:
            value = float(array[int(index)])
            return value if np.isfinite(value) else ""
        return ""

    def _tolerance_spot_overlay_csv_rows(self, overlay: dict[str, object]) -> tuple[list[str], list[dict[str, object]]]:
        nominal = dict(overlay.get("nominal", {}) or {})
        worst = dict(overlay.get("worst", {}) or {})
        nominal_x = np.asarray(nominal.get("x", []), dtype=float).ravel()
        nominal_y = np.asarray(nominal.get("y", []), dtype=float).ravel()
        worst_x = np.asarray(worst.get("x", []), dtype=float).ravel()
        worst_y = np.asarray(worst.get("y", []), dtype=float).ravel()
        count = max(nominal_x.size, nominal_y.size, worst_x.size, worst_y.size)
        columns = [
            "view",
            "wavelength_um",
            "worst_sample",
            "point_index",
            "nominal_x_mm",
            "nominal_y_mm",
            "worst_x_mm",
            "worst_y_mm",
            "delta_x_mm",
            "delta_y_mm",
            "nominal_centroid_x_mm",
            "nominal_centroid_y_mm",
            "worst_centroid_x_mm",
            "worst_centroid_y_mm",
            "nominal_rms_radius_mm",
            "worst_rms_radius_mm",
            "delta_rms_radius_mm",
            "nominal_total_merit",
            "worst_total_merit",
        ]
        rows: list[dict[str, object]] = []
        for index in range(int(count)):
            nx = self._array_value_or_blank(nominal_x, index)
            ny = self._array_value_or_blank(nominal_y, index)
            wx = self._array_value_or_blank(worst_x, index)
            wy = self._array_value_or_blank(worst_y, index)
            dx = (float(wx) - float(nx)) if nx != "" and wx != "" else ""
            dy = (float(wy) - float(ny)) if ny != "" and wy != "" else ""
            rows.append(
                {
                    "view": TOLERANCE_COMPARE_VIEW_DEFAULT,
                    "wavelength_um": self._csv_optional_float(overlay.get("wavelength")),
                    "worst_sample": int(overlay.get("worst_sample", 0) or 0),
                    "point_index": index,
                    "nominal_x_mm": nx,
                    "nominal_y_mm": ny,
                    "worst_x_mm": wx,
                    "worst_y_mm": wy,
                    "delta_x_mm": dx,
                    "delta_y_mm": dy,
                    "nominal_centroid_x_mm": self._csv_optional_float(nominal.get("centroid_x")),
                    "nominal_centroid_y_mm": self._csv_optional_float(nominal.get("centroid_y")),
                    "worst_centroid_x_mm": self._csv_optional_float(worst.get("centroid_x")),
                    "worst_centroid_y_mm": self._csv_optional_float(worst.get("centroid_y")),
                    "nominal_rms_radius_mm": self._csv_optional_float(nominal.get("rms_radius")),
                    "worst_rms_radius_mm": self._csv_optional_float(worst.get("rms_radius")),
                    "delta_rms_radius_mm": self._csv_optional_float(overlay.get("delta_rms_radius")),
                    "nominal_total_merit": self._csv_optional_float(overlay.get("nominal_total_merit")),
                    "worst_total_merit": self._csv_optional_float(overlay.get("worst_total_merit")),
                }
            )
        return columns, rows

    def _tolerance_mtf_overlay_csv_rows(self, overlay: dict[str, object]) -> tuple[list[str], list[dict[str, object]]]:
        nominal = dict(overlay.get("nominal", {}) or {})
        worst = dict(overlay.get("worst", {}) or {})
        freq = np.asarray(nominal.get("plot_freq", []), dtype=float).ravel()
        worst_freq = np.asarray(worst.get("plot_freq", []), dtype=float).ravel()
        mtf_mode = self._operand_mtf_mode("MTF @ freq")
        _nominal_freq, nominal_selected, selected_label = self._tolerance_selected_mtf_curve(nominal, mtf_mode)
        _worst_freq, worst_selected_native, _selected_label = self._tolerance_selected_mtf_curve(worst, mtf_mode)

        def interp_worst(key: str) -> np.ndarray:
            values = np.asarray(worst.get(key, []), dtype=float).ravel()
            if freq.size == 0 or worst_freq.size == 0 or values.size == 0:
                return np.asarray([], dtype=float)
            count = min(worst_freq.size, values.size)
            return np.interp(freq, worst_freq[:count], values[:count], left=values[0], right=values[count - 1])

        worst_tan = interp_worst("plot_tan")
        worst_sag = interp_worst("plot_sag")
        worst_avg = interp_worst("plot_avg")
        worst_selected = np.interp(
            freq,
            worst_freq[: min(worst_freq.size, worst_selected_native.size)],
            worst_selected_native[: min(worst_freq.size, worst_selected_native.size)],
            left=worst_selected_native[0],
            right=worst_selected_native[min(worst_freq.size, worst_selected_native.size) - 1],
        ) if freq.size and worst_freq.size and worst_selected_native.size else np.asarray([], dtype=float)

        columns = [
            "view",
            "wavelength_um",
            "worst_sample",
            "field_legend",
            "selected_label",
            "target_frequency_cy_per_mm",
            "frequency_cy_per_mm",
            "nominal_tangential_mtf",
            "nominal_sagittal_mtf",
            "nominal_average_mtf",
            "nominal_selected_mtf",
            "worst_tangential_mtf",
            "worst_sagittal_mtf",
            "worst_average_mtf",
            "worst_selected_mtf",
            "delta_selected_mtf",
            "nominal_selected_at_target",
            "worst_selected_at_target",
            "delta_selected_at_target",
            "nominal_total_merit",
            "worst_total_merit",
        ]
        field_sample = dict(overlay.get("field_sample", {}) or {})
        rows: list[dict[str, object]] = []
        for index in range(int(freq.size)):
            ns = self._array_value_or_blank(nominal_selected, index)
            ws = self._array_value_or_blank(worst_selected, index)
            delta = (float(ws) - float(ns)) if ns != "" and ws != "" else ""
            rows.append(
                {
                    "view": "MTF overlay",
                    "wavelength_um": self._csv_optional_float(overlay.get("wavelength")),
                    "worst_sample": int(overlay.get("worst_sample", 0) or 0),
                    "field_legend": str(field_sample.get("legend", "") or ""),
                    "selected_label": selected_label,
                    "target_frequency_cy_per_mm": self._csv_optional_float(overlay.get("target_frequency")),
                    "frequency_cy_per_mm": self._array_value_or_blank(freq, index),
                    "nominal_tangential_mtf": self._array_value_or_blank(nominal.get("plot_tan", []), index),
                    "nominal_sagittal_mtf": self._array_value_or_blank(nominal.get("plot_sag", []), index),
                    "nominal_average_mtf": self._array_value_or_blank(nominal.get("plot_avg", []), index),
                    "nominal_selected_mtf": ns,
                    "worst_tangential_mtf": self._array_value_or_blank(worst_tan, index),
                    "worst_sagittal_mtf": self._array_value_or_blank(worst_sag, index),
                    "worst_average_mtf": self._array_value_or_blank(worst_avg, index),
                    "worst_selected_mtf": ws,
                    "delta_selected_mtf": delta,
                    "nominal_selected_at_target": self._csv_optional_float(overlay.get("nominal_selected_value")),
                    "worst_selected_at_target": self._csv_optional_float(overlay.get("worst_selected_value")),
                    "delta_selected_at_target": self._csv_optional_float(overlay.get("delta_selected_value")),
                    "nominal_total_merit": self._csv_optional_float(overlay.get("nominal_total_merit")),
                    "worst_total_merit": self._csv_optional_float(overlay.get("worst_total_merit")),
                }
            )
        return columns, rows

    def _tolerance_wavefront_overlay_csv_rows(self, overlay: dict[str, object]) -> tuple[list[str], list[dict[str, object]]]:
        x = np.asarray(overlay.get("x", []), dtype=float).ravel()
        y = np.asarray(overlay.get("y", []), dtype=float).ravel()
        count = x.size
        nominal = dict(overlay.get("nominal", {}) or {})
        worst = dict(overlay.get("worst", {}) or {})
        columns = [
            "view",
            "wavelength_um",
            "worst_sample",
            "sample_index",
            "x_pupil",
            "y_pupil",
            "nominal_wfe_waves",
            "worst_wfe_waves",
            "delta_wfe_waves",
            "delta_centered_waves",
            "delta_rms_waves",
            "delta_pv_waves",
            "nominal_rms_waves",
            "worst_rms_waves",
            "nominal_total_merit",
            "worst_total_merit",
        ]
        rows: list[dict[str, object]] = []
        for index in range(int(count)):
            rows.append(
                {
                    "view": "Wavefront delta",
                    "wavelength_um": self._csv_optional_float(overlay.get("wavelength")),
                    "worst_sample": int(overlay.get("worst_sample", 0) or 0),
                    "sample_index": index,
                    "x_pupil": self._array_value_or_blank(x, index),
                    "y_pupil": self._array_value_or_blank(y, index),
                    "nominal_wfe_waves": self._array_value_or_blank(overlay.get("nominal_wfe_waves", []), index),
                    "worst_wfe_waves": self._array_value_or_blank(overlay.get("worst_wfe_waves", []), index),
                    "delta_wfe_waves": self._array_value_or_blank(overlay.get("delta_wfe_waves", []), index),
                    "delta_centered_waves": self._array_value_or_blank(overlay.get("delta_centered_waves", []), index),
                    "delta_rms_waves": self._csv_optional_float(overlay.get("delta_rms_waves")),
                    "delta_pv_waves": self._csv_optional_float(overlay.get("delta_pv_waves")),
                    "nominal_rms_waves": self._csv_optional_float(nominal.get("rms_waves")),
                    "worst_rms_waves": self._csv_optional_float(worst.get("rms_waves")),
                    "nominal_total_merit": self._csv_optional_float(overlay.get("nominal_total_merit")),
                    "worst_total_merit": self._csv_optional_float(overlay.get("worst_total_merit")),
                }
            )
        return columns, rows

    def tolerance_overlay_csv_rows(
        self,
        view: str | None = None,
        overlay: dict[str, object] | None = None,
    ) -> tuple[list[str], list[dict[str, object]]]:
        selected_view = str(view or self._current_tolerance_compare_view()).strip()
        if selected_view not in TOLERANCE_COMPARE_VIEW_VALUES:
            selected_view = TOLERANCE_COMPARE_VIEW_DEFAULT
        if selected_view == "Stack-up bars":
            dashboard = overlay if overlay is not None else self.tolerance_stackup_dashboard()
            columns, rows = self.tolerance_stackup_group_csv_rows(dict(dashboard))
            for row in rows:
                row["view"] = "Stack-up bars"
            return ["view", *columns], rows
        if selected_view == "MTF overlay":
            resolved_overlay = overlay if overlay is not None else self.tolerance_nominal_worst_mtf_overlay()
            return self._tolerance_mtf_overlay_csv_rows(dict(resolved_overlay))
        if selected_view == "Wavefront delta":
            resolved_overlay = overlay if overlay is not None else self.tolerance_nominal_worst_wavefront_overlay()
            return self._tolerance_wavefront_overlay_csv_rows(dict(resolved_overlay))
        resolved_overlay = overlay if overlay is not None else self.tolerance_nominal_worst_spot_overlay()
        return self._tolerance_spot_overlay_csv_rows(dict(resolved_overlay))

    def tolerance_worst_sample_comparison(self, summary: dict[str, object] | None = None) -> dict[str, object]:
        return self._tolerance_analysis_service().tolerance_worst_sample_comparison(summary)

    def tolerance_worst_sample_comparison_report_text(self, comparison: dict[str, object] | None = None) -> str:
        return self._tolerance_analysis_service().tolerance_worst_sample_comparison_report_text(comparison)

    def open_tolerance_worst_sample_comparison_report(self) -> None:
        self._main_tolerance_report_dialogs().open_tolerance_worst_sample_comparison_report()

    def export_tolerance_comparison_csv(self) -> None:
        self._main_tolerance_report_dialogs().export_tolerance_comparison_csv()

    def _tolerance_analysis_service(self) -> ToleranceAnalysisService:
        service = self.__dict__.get("_tolerance_analysis_service_instance")
        if service is None:
            service = ToleranceAnalysisService(self)
            self._tolerance_analysis_service_instance = service
        return service

    def _tolerance_stackup_service(self) -> ToleranceStackupService:
        service = self.__dict__.get("_tolerance_stackup_service_instance")
        if service is None:
            service = ToleranceStackupService(self)
            self._tolerance_stackup_service_instance = service
        return service

    def tolerance_stackup_dashboard(self, summary: dict[str, object] | None = None) -> dict[str, object]:
        return self._tolerance_stackup_service().tolerance_stackup_dashboard(summary)

    def tolerance_stackup_dashboard_report_text(self, dashboard: dict[str, object] | None = None) -> str:
        return self._tolerance_stackup_service().tolerance_stackup_dashboard_report_text(dashboard)

    def tolerance_stackup_csv_rows(
        self,
        dashboard: dict[str, object] | None = None,
    ) -> tuple[list[str], list[dict[str, object]]]:
        return self._tolerance_stackup_service().tolerance_stackup_csv_rows(dashboard)

    def tolerance_stackup_group_csv_rows(
        self,
        dashboard: dict[str, object] | None = None,
    ) -> tuple[list[str], list[dict[str, object]]]:
        return self._tolerance_stackup_service().tolerance_stackup_group_csv_rows(dashboard)

    def open_tolerance_stackup_dashboard_report(self) -> None:
        self._main_tolerance_report_dialogs().open_tolerance_stackup_dashboard_report()

    def export_tolerance_stackup_csv(self) -> None:
        self._main_tolerance_report_dialogs().export_tolerance_stackup_csv()

    def open_tolerance_compensator_sweep_report(self) -> None:
        self._main_tolerance_report_dialogs().open_tolerance_compensator_sweep_report()

    def export_tolerance_compensator_csv(self) -> None:
        self._main_tolerance_report_dialogs().export_tolerance_compensator_csv()

    def open_tolerance_multi_compensator_report(self) -> None:
        self._main_tolerance_report_dialogs().open_tolerance_multi_compensator_report()

    def export_tolerance_multi_compensator_csv(self) -> None:
        self._main_tolerance_report_dialogs().export_tolerance_multi_compensator_csv()

    def export_tolerance_overlay_csv(self) -> None:
        self._main_tolerance_report_dialogs().export_tolerance_overlay_csv()
