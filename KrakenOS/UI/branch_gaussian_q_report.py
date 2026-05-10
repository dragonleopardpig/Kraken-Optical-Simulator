from __future__ import annotations

from collections import Counter
from typing import Callable, Iterable, Sequence

import numpy as np

import KrakenOS as Kos


BRANCH_GAUSSIAN_Q_CSV_COLUMNS: tuple[str, ...] = (
    "ray_index",
    "source_ray_index",
    "source",
    "source_model",
    "branch_id",
    "branch_code",
    "branch_path",
    "step",
    "surface",
    "surface_name",
    "event",
    "note",
    "diagnostic",
    "n_before",
    "n_after",
    "incidence_deg",
    "distance_mm",
    "optical_path_mm",
    "tangential_C",
    "sagittal_C",
    "surface_power_applied",
    "tangential_q_real_mm",
    "tangential_q_imag_mm",
    "sagittal_q_real_mm",
    "sagittal_q_imag_mm",
    "tangential_beam_radius_mm",
    "sagittal_beam_radius_mm",
    "clip_transmission",
    "cumulative_clip_transmission",
    "tangential_stable",
    "sagittal_stable",
    "trace_stable",
    "trace_final",
)


def default_branch_gaussian_q_beam(wavelength_um: float) -> Kos.GaussianBeamInput:
    return Kos.GaussianBeamInput(
        wavelength_um=float(wavelength_um),
        waist_radius_mm=0.50,
        waist_offset_mm=0.0,
        m2=1.0,
        input_index=1.0,
    )


def branch_path_code(branch_path: str) -> str:
    selectors: list[str] = []
    for component in str(branch_path or "").split("->"):
        text = component.strip()
        if "/" not in text:
            continue
        selector = text.rsplit("/", 1)[1].strip().lower()
        selectors.append({"transmit": "T", "reflect": "R"}.get(selector, selector or "?"))
    return "".join(selectors) or "primary"


def _default_error_formatter(exc: Exception, limit: int = 220) -> str:
    text = str(exc).strip()
    if not text:
        return exc.__class__.__name__
    first = text.splitlines()[0].strip()
    if len(first) > limit:
        return first[:limit] + "..."
    return first


def collect_branch_gaussian_q_records(
    ray_records: Iterable[dict[str, object]],
    *,
    surfaces: Sequence[object],
    beam: Kos.GaussianBeamInput,
    wavelength_um: float,
    source_model: str,
    branch_code_for_path: Callable[[str], str] | None = None,
    error_formatter: Callable[[Exception], str] | None = None,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    records = list(ray_records)
    code_for_path = branch_code_for_path or branch_path_code
    format_error = error_formatter or _default_error_formatter
    rows: list[dict[str, object]] = []
    failures: list[str] = []
    trace_count = 0
    stable_count = 0
    for record in records:
        hits = list(record.get("hits", []) or [])
        if not hits:
            continue
        try:
            trace = Kos.propagate_branch_gaussian_q(record, beam, surfaces=surfaces)
        except Exception as exc:
            failures.append(f"ray {record.get('ray_index', '-')}: {format_error(exc)}")
            continue
        if not trace.steps:
            continue
        trace_count += 1
        if bool(trace.stable):
            stable_count += 1
        final = trace.final
        branch_path = str(record.get("branch_path", "") or "")
        branch_code = code_for_path(branch_path)
        source_text = str(record.get("source_name", "") or record.get("source_id", "") or "").strip()
        for step in trace.steps:
            note = str(step.note)
            rows.append(
                {
                    "ray_index": int(record.get("ray_index", trace.ray_index) or 0),
                    "source_ray_index": int(record.get("source_ray_index", trace.source_ray_index) or 0),
                    "source": source_text,
                    "source_model": str(record.get("source_model", source_model) or ""),
                    "branch_id": int(step.branch_id),
                    "branch_code": branch_code,
                    "branch_path": branch_path or "primary",
                    "step": int(step.step_index),
                    "surface": int(step.surface_index),
                    "surface_name": str(step.surface_name),
                    "event": str(step.event),
                    "note": note,
                    "diagnostic": any(token in note.lower() for token in ("q-only", "deferred", "ignored")),
                    "n_before": float(step.n_before),
                    "n_after": float(step.n_after),
                    "incidence_deg": float(step.incidence_deg),
                    "distance_mm": float(step.distance_mm),
                    "optical_path_mm": float(step.optical_path_mm),
                    "tangential_C": float(step.tangential_C),
                    "sagittal_C": float(step.sagittal_C),
                    "surface_power_applied": bool(step.surface_power_applied),
                    "tangential_q_real_mm": float(step.tangential_q_real_mm),
                    "tangential_q_imag_mm": float(step.tangential_q_imag_mm),
                    "sagittal_q_real_mm": float(step.sagittal_q_real_mm),
                    "sagittal_q_imag_mm": float(step.sagittal_q_imag_mm),
                    "tangential_beam_radius_mm": float(step.tangential_beam_radius_mm),
                    "sagittal_beam_radius_mm": float(step.sagittal_beam_radius_mm),
                    "clip_transmission": float(step.clip_transmission),
                    "cumulative_clip_transmission": float(step.cumulative_clip_transmission),
                    "tangential_stable": bool(step.tangential_stable),
                    "sagittal_stable": bool(step.sagittal_stable),
                    "trace_stable": bool(trace.stable),
                    "trace_final": bool(final is not None and step.step_index == final.step_index),
                }
            )

    note_counts = Counter(str(row.get("note", "")) for row in rows)
    diagnostic_count = sum(1 for row in rows if bool(row.get("diagnostic", False)))
    summary = {
        "wavelength_um": float(wavelength_um),
        "beam_waist_radius_mm": float(getattr(beam, "waist_radius_mm", np.nan)),
        "beam_waist_offset_mm": float(getattr(beam, "waist_offset_mm", np.nan)),
        "beam_m2": float(getattr(beam, "m2", np.nan)),
        "beam_source": "current Gaussian source" if source_model == "Gaussian beam" else "diagnostic default Gaussian beam",
        "ray_records": len(records),
        "trace_count": trace_count,
        "stable_count": stable_count,
        "step_count": len(rows),
        "failure_count": len(failures),
        "failures": failures,
        "note_counts": dict(sorted(note_counts.items())),
        "diagnostic_count": diagnostic_count,
    }
    return rows, summary


def format_branch_gaussian_q_value(value) -> str:
    try:
        numeric = float(value)
    except Exception:
        text = str(value).strip()
        return text if text else "-"
    if not np.isfinite(numeric):
        return "-"
    return f"{numeric:.6g}"


def branch_gaussian_q_summary_text(summary: dict[str, object]) -> str:
    notes = dict(summary.get("note_counts", {}) or {})
    note_text = ", ".join(f"{key}={value}" for key, value in notes.items()) if notes else "none"
    return (
        "Branch Gaussian q | beam={beam} | lambda={wavelength:.6g} um | w0={waist:.6g} mm | "
        "offset={offset:.6g} mm | M2={m2:.6g} | traces={stable}/{traces} stable | "
        "steps={steps} | diagnostics={diagnostics} | failures={failures} | notes: {notes}"
    ).format(
        beam=str(summary.get("beam_source", "")),
        wavelength=float(summary.get("wavelength_um", np.nan)),
        waist=float(summary.get("beam_waist_radius_mm", np.nan)),
        offset=float(summary.get("beam_waist_offset_mm", np.nan)),
        m2=float(summary.get("beam_m2", np.nan)),
        stable=int(summary.get("stable_count", 0) or 0),
        traces=int(summary.get("trace_count", 0) or 0),
        steps=int(summary.get("step_count", 0) or 0),
        diagnostics=int(summary.get("diagnostic_count", 0) or 0),
        failures=int(summary.get("failure_count", 0) or 0),
        notes=note_text,
    )


def branch_gaussian_q_table_values(row: dict[str, object]) -> tuple[object, ...]:
    stable = bool(row.get("tangential_stable", False)) and bool(row.get("sagittal_stable", False))
    surface_text = f"S{int(row.get('surface', -1))}"
    surface_name = str(row.get("surface_name", "") or "")
    if surface_name:
        surface_text = f"{surface_text} {surface_name}"
    return (
        int(row.get("ray_index", 0) or 0),
        str(row.get("branch_code", row.get("branch_path", "")) or ""),
        int(row.get("step", 0) or 0),
        surface_text,
        str(row.get("event", "") or ""),
        str(row.get("note", "") or ""),
        format_branch_gaussian_q_value(row.get("incidence_deg")),
        f"{format_branch_gaussian_q_value(row.get('n_before'))}->{format_branch_gaussian_q_value(row.get('n_after'))}",
        format_branch_gaussian_q_value(row.get("tangential_C")),
        format_branch_gaussian_q_value(row.get("sagittal_C")),
        f"{format_branch_gaussian_q_value(row.get('tangential_q_real_mm'))}+{format_branch_gaussian_q_value(row.get('tangential_q_imag_mm'))}j",
        f"{format_branch_gaussian_q_value(row.get('sagittal_q_real_mm'))}+{format_branch_gaussian_q_value(row.get('sagittal_q_imag_mm'))}j",
        f"{format_branch_gaussian_q_value(row.get('tangential_beam_radius_mm'))}/{format_branch_gaussian_q_value(row.get('sagittal_beam_radius_mm'))}",
        format_branch_gaussian_q_value(row.get("cumulative_clip_transmission")),
        "Y" if stable else "N",
    )


def branch_gaussian_q_report_text(rows: list[dict[str, object]], summary: dict[str, object]) -> str:
    if not rows:
        return "# KrakenOS Branch Gaussian Q Report\n\nNo Gaussian q branch records. Click Update first.\n"
    lines = [
        "# KrakenOS Branch Gaussian Q Report",
        "",
        branch_gaussian_q_summary_text(summary),
        "",
    ]
    for row in rows:
        lines.append(
            "- ray={ray} path={path} step={step} S{surface} {event} | note={note} | "
            "n={n0}->{n1} | inc={inc} deg | Ct={ct} Cs={cs} | "
            "qT={qtr}+{qti}j mm qS={qsr}+{qsi}j mm | clip={clip}".format(
                ray=int(row.get("ray_index", 0) or 0),
                path=str(row.get("branch_path", "") or ""),
                step=int(row.get("step", 0) or 0),
                surface=int(row.get("surface", -1) or -1),
                event=str(row.get("event", "") or ""),
                note=str(row.get("note", "") or ""),
                n0=format_branch_gaussian_q_value(row.get("n_before")),
                n1=format_branch_gaussian_q_value(row.get("n_after")),
                inc=format_branch_gaussian_q_value(row.get("incidence_deg")),
                ct=format_branch_gaussian_q_value(row.get("tangential_C")),
                cs=format_branch_gaussian_q_value(row.get("sagittal_C")),
                qtr=format_branch_gaussian_q_value(row.get("tangential_q_real_mm")),
                qti=format_branch_gaussian_q_value(row.get("tangential_q_imag_mm")),
                qsr=format_branch_gaussian_q_value(row.get("sagittal_q_real_mm")),
                qsi=format_branch_gaussian_q_value(row.get("sagittal_q_imag_mm")),
                clip=format_branch_gaussian_q_value(row.get("cumulative_clip_transmission")),
            )
        )
    return "\n".join(lines).strip() + "\n"
