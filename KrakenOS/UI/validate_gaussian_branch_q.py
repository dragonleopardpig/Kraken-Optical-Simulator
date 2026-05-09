from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.validate_branch_analysis import _load_traced_editor


@dataclass
class GaussianBranchQCheck:
    layout: str
    check: str
    ok: bool
    detail: str


def _result(layout: str, check: str, ok: bool, detail: str) -> GaussianBranchQCheck:
    return GaussianBranchQCheck(layout=layout, check=check, ok=bool(ok), detail=str(detail))


def _records_with_hits(editor) -> list[dict[str, object]]:
    return [
        record
        for record in editor._collect_ray_inspector_records()
        if list(record.get("hits", []) or [])
    ]


def _flat_trace_expected_distance(trace: Kos.BranchGaussianQTrace) -> float | None:
    for step in trace.steps:
        if abs(float(step.tangential_C)) > 1e-12 or abs(float(step.sagittal_C)) > 1e-12:
            return None
        if abs(float(step.n_after) - float(trace.input_index)) > 1e-9:
            return None
    return float(sum(float(step.distance_mm) for step in trace.steps))


def _validate_layout(title: str) -> list[GaussianBranchQCheck]:
    editor, _system, _rays, wavelength = _load_traced_editor(title)
    records = _records_with_hits(editor)
    circular_beam = Kos.GaussianBeamInput(
        wavelength_um=float(wavelength),
        waist_radius_mm=0.50,
        waist_offset_mm=0.0,
        m2=1.0,
        input_index=1.0,
    )
    astigmatic_beam = Kos.AstigmaticGaussianBeamInput(
        tangential=Kos.GaussianBeamInput(
            wavelength_um=float(wavelength),
            waist_radius_mm=0.45,
            waist_offset_mm=0.0,
            m2=1.0,
            input_index=1.0,
        ),
        sagittal=Kos.GaussianBeamInput(
            wavelength_um=float(wavelength),
            waist_radius_mm=0.75,
            waist_offset_mm=0.0,
            m2=1.0,
            input_index=1.0,
        ),
    )
    traces: list[Kos.BranchGaussianQTrace] = []
    failures: list[str] = []
    for record in records:
        try:
            trace = Kos.propagate_branch_gaussian_q(record, circular_beam, surfaces=editor.rows)
        except Exception as exc:
            failures.append(str(exc))
            continue
        if trace.steps:
            traces.append(trace)

    checks: list[GaussianBranchQCheck] = [
        _result(
            title,
            "branch records produce Gaussian q traces",
            len(traces) > 0 and not failures,
            f"records={len(records)}, traces={len(traces)}, failures={len(failures)}",
        )
    ]

    finals = [trace.final for trace in traces if trace.final is not None]
    finite_finals = [
        final
        for final in finals
        if np.isfinite(float(final.tangential_q_real_mm))
        and np.isfinite(float(final.tangential_q_imag_mm))
        and np.isfinite(float(final.sagittal_q_real_mm))
        and np.isfinite(float(final.sagittal_q_imag_mm))
    ]
    checks.append(
        _result(
            title,
            "final branch q states are finite and stable",
            len(finite_finals) == len(finals) and len(finals) > 0 and all(bool(trace.stable) for trace in traces),
            f"finals={len(finals)}, finite={len(finite_finals)}, stable={sum(1 for trace in traces if trace.stable)}",
        )
    )

    flat_errors: list[float] = []
    for trace in traces:
        expected_distance = _flat_trace_expected_distance(trace)
        if expected_distance is None:
            continue
        final = trace.final
        if final is None:
            continue
        flat_errors.append(abs(float(final.tangential_q_real_mm) - (trace.input_tangential_q.real + expected_distance)))
        flat_errors.append(abs(float(final.tangential_q_imag_mm) - trace.input_tangential_q.imag))
        flat_errors.append(abs(float(final.sagittal_q_real_mm) - (trace.input_sagittal_q.real + expected_distance)))
        flat_errors.append(abs(float(final.sagittal_q_imag_mm) - trace.input_sagittal_q.imag))
    checks.append(
        _result(
            title,
            "flat branch propagation matches q plus physical path length",
            (not flat_errors) or max(flat_errors) < 1e-8,
            (
                "no flat-only branches in this layout"
                if not flat_errors
                else f"samples={len(flat_errors)}, max_error={max(flat_errors):.3g}"
            ),
        )
    )

    branch_paths = {str(trace.branch_path or "") for trace in traces if str(trace.branch_path or "").strip()}
    branched_layout = any(token in title for token in ("Beam Splitter", "Michelson", "Mach-Zehnder", "Twyman"))
    checks.append(
        _result(
            title,
            "deterministic branch paths carry independent q traces",
            (not branched_layout) or len(branch_paths) >= 2,
            f"branch_paths={len(branch_paths)}",
        )
    )

    astigmatic_trace = None
    for record in records:
        candidate = Kos.propagate_branch_gaussian_q(record, astigmatic_beam, surfaces=editor.rows)
        if candidate.final is not None and candidate.stable:
            astigmatic_trace = candidate
            break
    final = astigmatic_trace.final if astigmatic_trace is not None else None
    radius_delta = (
        abs(float(final.tangential_beam_radius_mm) - float(final.sagittal_beam_radius_mm))
        if final is not None
        else np.nan
    )
    checks.append(
        _result(
            title,
            "tangential and sagittal q states remain independently propagated",
            final is not None and np.isfinite(radius_delta) and radius_delta > 1e-6,
            f"radius_delta={radius_delta:.6g}",
        )
    )
    clip_values = [
        float(step.clip_transmission)
        for trace in traces
        for step in trace.steps
        if np.isfinite(float(step.clip_transmission))
    ]
    cumulative_values = [
        [float(step.cumulative_clip_transmission) for step in trace.steps if np.isfinite(float(step.cumulative_clip_transmission))]
        for trace in traces
    ]
    cumulative_monotonic = all(
        all(values[index] <= values[index - 1] + 1e-12 for index in range(1, len(values)))
        for values in cumulative_values
        if values
    )
    checks.append(
        _result(
            title,
            "Gaussian clipping transmission is bounded and cumulative",
            bool(clip_values)
            and all(-1e-12 <= value <= 1.0 + 1e-12 for value in clip_values)
            and cumulative_monotonic,
            f"clip_samples={len(clip_values)}, min_clip={min(clip_values) if clip_values else np.nan:.6g}",
        )
    )
    return checks


def _validate_synthetic_clipping() -> list[GaussianBranchQCheck]:
    beam = Kos.GaussianBeamInput(
        wavelength_um=0.6328,
        waist_radius_mm=1.0,
        waist_offset_mm=0.0,
        m2=1.0,
        input_index=1.0,
    )
    record = {
        "ray_index": 0,
        "source_ray_index": 0,
        "branch_id": 0,
        "branch_path": "synthetic",
        "hits": [
            {"step": 0, "branch": 0, "surface": 0, "event": "aperture", "distance": 0.0, "op": 0.0, "n0": 1.0, "n1": 1.0},
            {"step": 1, "branch": 0, "surface": 1, "event": "aperture", "distance": 0.0, "op": 0.0, "n0": 1.0, "n1": 1.0},
        ],
    }
    surfaces = [
        {"diameter": 1.0, "in_diameter": 0.0, "rc": 0.0},
        {"diameter": 2.0, "in_diameter": 0.4, "rc": 0.0},
    ]
    trace = Kos.propagate_branch_gaussian_q(record, beam, surfaces=surfaces)
    transmissions = [float(step.clip_transmission) for step in trace.steps]
    expected_first = 1.0 - float(np.exp(-0.5))
    expected_second = (1.0 - float(np.exp(-2.0))) - (1.0 - float(np.exp(-2.0 * 0.2**2)))
    expected_cumulative = expected_first * expected_second
    final = trace.final
    return [
        _result(
            "Synthetic Gaussian aperture",
            "single-hit Gaussian aperture fraction matches analytic centered circular estimate",
            len(transmissions) == 2 and abs(transmissions[0] - expected_first) < 1e-12,
            f"clip={transmissions[0] if transmissions else np.nan:.12g}, expected={expected_first:.12g}",
        ),
        _result(
            "Synthetic Gaussian aperture",
            "annular aperture fraction and cumulative loss are propagated",
            final is not None
            and abs(transmissions[1] - expected_second) < 1e-12
            and abs(float(final.cumulative_clip_transmission) - expected_cumulative) < 1e-12
            and abs(float(trace.cumulative_clip_transmission) - expected_cumulative) < 1e-12,
            (
                f"annular={transmissions[1] if len(transmissions) > 1 else np.nan:.12g}, "
                f"cum={float(final.cumulative_clip_transmission) if final is not None else np.nan:.12g}, "
                f"expected={expected_cumulative:.12g}"
            ),
        ),
    ]


def validate_gaussian_branch_q() -> list[GaussianBranchQCheck]:
    checks: list[GaussianBranchQCheck] = []
    for title in (
        "Galvo F-Theta Laser Scanner",
        "Beam Splitter Two Path Doublets",
        "Michelson Interferometer (Interferogram)",
    ):
        checks.extend(_validate_layout(title))
    checks.extend(_validate_synthetic_clipping())
    return checks


def _print_table(checks: list[GaussianBranchQCheck]) -> None:
    print("KrakenOS Gaussian branch-q validation")
    print("layout | check | status | detail")
    print("--- | --- | --- | ---")
    for check in checks:
        print(f"{check.layout} | {check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate branch-carried tangential/sagittal Gaussian q propagation.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_gaussian_branch_q()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
