from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

import KrakenOS as Kos


@dataclass
class ObliqueAstigmaticQCheck:
    case: str
    check: str
    ok: bool
    detail: str


def _result(case: str, check: str, ok: bool, detail: str) -> ObliqueAstigmaticQCheck:
    return ObliqueAstigmaticQCheck(case=case, check=check, ok=bool(ok), detail=str(detail))


def _beam() -> Kos.GaussianBeamInput:
    return Kos.GaussianBeamInput(
        wavelength_um=0.6328,
        waist_radius_mm=0.50,
        waist_offset_mm=0.0,
        m2=1.0,
        input_index=1.0,
    )


def _trace(hits: list[dict[str, object]], surfaces: list[dict[str, object]]) -> Kos.BranchGaussianQTrace:
    return Kos.propagate_branch_gaussian_q(
        {
            "ray_index": 0,
            "source_ray_index": 0,
            "branch_id": 0,
            "branch_path": "synthetic-oblique",
            "hits": hits,
        },
        _beam(),
        surfaces=surfaces,
    )


def _finite_step(step) -> bool:
    return (
        step is not None
        and np.isfinite(float(step.tangential_q_real_mm))
        and np.isfinite(float(step.tangential_q_imag_mm))
        and np.isfinite(float(step.sagittal_q_real_mm))
        and np.isfinite(float(step.sagittal_q_imag_mm))
        and bool(step.tangential_stable)
        and bool(step.sagittal_stable)
    )


def _expected_oblique_refraction_c(
    *,
    radius_mm: float,
    n_before: float,
    n_after: float,
    incidence_deg: float,
) -> tuple[float, float]:
    cos_i = float(np.cos(np.deg2rad(abs(incidence_deg))))
    cos_i = max(cos_i, 1e-6)
    sin_i = float(np.sqrt(max(0.0, 1.0 - cos_i * cos_i)))
    sin_r = float(n_before) * sin_i / max(float(n_after), 1e-12)
    if abs(sin_r) >= 1.0:
        return 0.0, 0.0
    cos_r = float(np.sqrt(max(1.0 - sin_r * sin_r, 1e-12)))
    c_t = (float(n_before) * cos_i - float(n_after) * cos_r) / (
        float(radius_mm) * max(float(n_after) * cos_i * cos_r, 1e-12)
    )
    c_s = (float(n_before) * cos_r - float(n_after) * cos_i) / (
        float(radius_mm) * max(float(n_after), 1e-12)
    )
    return float(c_t), float(c_s)


def _validate_flat_fold() -> list[ObliqueAstigmaticQCheck]:
    trace = _trace(
        [
            {
                "step": 0,
                "branch": 0,
                "surface": 0,
                "event": "reflect",
                "distance": 20.0,
                "op": 20.0,
                "n0": 1.0,
                "n1": 1.0,
                "gb_incidence_deg": 45.0,
            }
        ],
        [{"rc": 0.0, "diameter": 50.0}],
    )
    final = trace.final
    return [
        _result(
            "flat folded path",
            "flat mirror/fold stays pure free-space q propagation",
            final is not None
            and _finite_step(final)
            and abs(float(final.tangential_C)) < 1e-12
            and abs(float(final.sagittal_C)) < 1e-12
            and str(final.note) == "flat/free-space"
            and abs(float(final.tangential_q_real_mm) - (trace.input_tangential_q.real + 20.0)) < 1e-10
            and abs(float(final.sagittal_q_real_mm) - (trace.input_sagittal_q.real + 20.0)) < 1e-10,
            f"note={final.note if final else '-'}, Ct={float(final.tangential_C) if final else np.nan:.6g}, Cs={float(final.sagittal_C) if final else np.nan:.6g}",
        )
    ]


def _validate_oblique_spherical_mirror() -> list[ObliqueAstigmaticQCheck]:
    radius_mm = 200.0
    incidence_deg = 30.0
    trace = _trace(
        [
            {
                "step": 0,
                "branch": 0,
                "surface": 0,
                "event": "reflect",
                "distance": 0.0,
                "op": 0.0,
                "n0": 1.0,
                "n1": 1.0,
                "gb_incidence_deg": incidence_deg,
            }
        ],
        [{"rc": radius_mm, "diameter": 50.0}],
    )
    final = trace.final
    cos_i = float(np.cos(np.deg2rad(incidence_deg)))
    expected_ct = -2.0 / (radius_mm * cos_i)
    expected_cs = -2.0 * cos_i / radius_mm
    q_split = (
        final is not None
        and abs(float(final.tangential_q_real_mm) - float(final.sagittal_q_real_mm)) > 1e-9
    )
    return [
        _result(
            "oblique spherical mirror",
            "oblique reflection uses different tangential and sagittal powers",
            final is not None
            and _finite_step(final)
            and bool(final.surface_power_applied)
            and str(final.note) == "oblique spherical reflection"
            and abs(float(final.tangential_C) - expected_ct) < 1e-12
            and abs(float(final.sagittal_C) - expected_cs) < 1e-12
            and abs(float(final.tangential_C) - float(final.sagittal_C)) > 1e-6
            and q_split,
            (
                f"Ct={float(final.tangential_C) if final else np.nan:.12g}, "
                f"Cs={float(final.sagittal_C) if final else np.nan:.12g}, "
                f"q_split={q_split}"
            ),
        )
    ]


def _validate_near_normal_refraction() -> list[ObliqueAstigmaticQCheck]:
    radius_mm = 120.0
    n_before = 1.0
    n_after = 1.5
    trace = _trace(
        [
            {
                "step": 0,
                "branch": 0,
                "surface": 0,
                "event": "transmit",
                "distance": 0.0,
                "op": 0.0,
                "n0": n_before,
                "n1": n_after,
                "gb_incidence_deg": 0.0,
            }
        ],
        [{"rc": radius_mm, "diameter": 50.0}],
    )
    final = trace.final
    expected_c = (n_before - n_after) / (radius_mm * n_after)
    return [
        _result(
            "near-normal spherical refraction",
            "near-normal refraction keeps symmetric first-order power",
            final is not None
            and _finite_step(final)
            and bool(final.surface_power_applied)
            and str(final.note) == "near-normal spherical refraction"
            and abs(float(final.tangential_C) - expected_c) < 1e-12
            and abs(float(final.sagittal_C) - expected_c) < 1e-12,
            f"C={float(final.tangential_C) if final else np.nan:.12g}, expected={expected_c:.12g}",
        )
    ]


def _validate_oblique_refraction() -> list[ObliqueAstigmaticQCheck]:
    radius_mm = 120.0
    n_before = 1.0
    n_after = 1.5
    incidence_deg = 25.0
    trace = _trace(
        [
            {
                "step": 0,
                "branch": 0,
                "surface": 0,
                "event": "transmit",
                "distance": 0.0,
                "op": 0.0,
                "n0": n_before,
                "n1": n_after,
                "gb_incidence_deg": incidence_deg,
            }
        ],
        [{"rc": radius_mm, "diameter": 50.0}],
    )
    final = trace.final
    expected_ct, expected_cs = _expected_oblique_refraction_c(
        radius_mm=radius_mm,
        n_before=n_before,
        n_after=n_after,
        incidence_deg=incidence_deg,
    )
    q_split = (
        final is not None
        and abs(float(final.tangential_q_real_mm) - float(final.sagittal_q_real_mm)) > 1e-9
    )
    return [
        _result(
            "oblique powered refraction",
            "oblique powered refraction applies split tangential and sagittal powers",
            final is not None
            and _finite_step(final)
            and bool(final.surface_power_applied)
            and str(final.note) == "oblique spherical refraction"
            and abs(float(final.tangential_C) - expected_ct) < 1e-12
            and abs(float(final.sagittal_C) - expected_cs) < 1e-12
            and abs(float(final.tangential_C) - float(final.sagittal_C)) > 1e-6
            and q_split
            and abs(float(final.n_after) - 1.5) < 1e-12,
            (
                f"note={final.note if final else '-'}, "
                f"Ct={float(final.tangential_C) if final else np.nan:.12g}, "
                f"Cs={float(final.sagittal_C) if final else np.nan:.12g}, "
                f"q_split={q_split}"
            ),
        )
    ]


def _validate_tilted_powered_plate_refraction() -> list[ObliqueAstigmaticQCheck]:
    trace = _trace(
        [
            {
                "step": 0,
                "branch": 0,
                "surface": 0,
                "event": "transmit",
                "distance": 0.0,
                "op": 0.0,
                "n0": 1.0,
                "n1": 1.5,
                "gb_incidence_deg": 35.0,
            },
            {
                "step": 1,
                "branch": 0,
                "surface": 1,
                "event": "transmit",
                "distance": 5.0,
                "op": 7.5,
                "n0": 1.5,
                "n1": 1.0,
                "gb_incidence_deg": 35.0,
            },
        ],
        [
            {"rc": 150.0, "diameter": 50.0},
            {"rc": -150.0, "diameter": 50.0},
        ],
    )
    notes = [str(step.note) for step in trace.steps]
    final = trace.final
    return [
        _result(
            "tilted powered plate",
            "multi-surface oblique refraction applies split powers per surface",
            len(trace.steps) == 2
            and _finite_step(final)
            and notes == ["oblique spherical refraction", "oblique spherical refraction"]
            and all(bool(step.surface_power_applied) for step in trace.steps)
            and all(abs(float(step.tangential_C) - float(step.sagittal_C)) > 1e-6 for step in trace.steps)
            and abs(float(final.n_after) - 1.0) < 1e-12,
            f"notes={notes}, stable={trace.stable}, final_n={float(final.n_after) if final else np.nan:.6g}",
        )
    ]


def _validate_flat_tilted_plate_diagnostic() -> list[ObliqueAstigmaticQCheck]:
    trace = _trace(
        [
            {
                "step": 0,
                "branch": 0,
                "surface": 0,
                "event": "transmit",
                "distance": 0.0,
                "op": 0.0,
                "n0": 1.0,
                "n1": 1.5,
                "gb_incidence_deg": 35.0,
            },
            {
                "step": 1,
                "branch": 0,
                "surface": 1,
                "event": "transmit",
                "distance": 8.0,
                "op": 12.0,
                "n0": 1.5,
                "n1": 1.0,
                "gb_incidence_deg": 35.0,
            },
        ],
        [
            {"rc": 0.0, "diameter": 50.0},
            {"rc": 0.0, "diameter": 50.0},
        ],
    )
    notes = [str(step.note) for step in trace.steps]
    final = trace.final
    return [
        _result(
            "flat tilted plate",
            "flat oblique refractive faces are diagnosed as q-only index steps",
            len(trace.steps) == 2
            and _finite_step(final)
            and notes == [
                "flat oblique refraction q-only index step",
                "flat oblique refraction q-only index step",
            ]
            and all(abs(float(step.tangential_C)) < 1e-12 for step in trace.steps)
            and all(abs(float(step.sagittal_C)) < 1e-12 for step in trace.steps)
            and not any(bool(step.surface_power_applied) for step in trace.steps)
            and abs(float(final.n_after) - 1.0) < 1e-12,
            f"notes={notes}, stable={trace.stable}, final_n={float(final.n_after) if final else np.nan:.6g}",
        )
    ]


def _validate_tir_diagnostic() -> list[ObliqueAstigmaticQCheck]:
    trace = _trace(
        [
            {
                "step": 0,
                "branch": 0,
                "surface": 0,
                "event": "transmit",
                "distance": 0.0,
                "op": 0.0,
                "n0": 1.5,
                "n1": 1.0,
                "gb_incidence_deg": 50.0,
            }
        ],
        [{"rc": 120.0, "diameter": 50.0}],
    )
    final = trace.final
    return [
        _result(
            "TIR diagnostic",
            "above-critical transmit hits are explicitly marked as deferred",
            final is not None
            and _finite_step(final)
            and str(final.note) == "oblique powered refraction TIR deferred"
            and abs(float(final.tangential_C)) < 1e-12
            and abs(float(final.sagittal_C)) < 1e-12
            and not bool(final.surface_power_applied),
            (
                f"note={final.note if final else '-'}, "
                f"Ct={float(final.tangential_C) if final else np.nan:.6g}, "
                f"Cs={float(final.sagittal_C) if final else np.nan:.6g}"
            ),
        )
    ]


def _validate_traced_layout_oblique_refraction(title: str) -> list[ObliqueAstigmaticQCheck]:
    from KrakenOS.UI.validate_branch_analysis import _load_traced_editor

    editor, _system, _rays, wavelength = _load_traced_editor(title)
    beam = Kos.GaussianBeamInput(
        wavelength_um=float(wavelength),
        waist_radius_mm=0.50,
        waist_offset_mm=0.0,
        m2=1.0,
        input_index=1.0,
    )
    records = [
        record
        for record in editor._collect_ray_inspector_records()
        if list(record.get("hits", []) or [])
    ]
    failures: list[str] = []
    oblique_steps = []
    for record in records:
        try:
            trace = Kos.propagate_branch_gaussian_q(record, beam, surfaces=editor.rows)
        except Exception as exc:
            failures.append(str(exc))
            continue
        for step in trace.steps:
            if str(step.note) == "oblique spherical refraction":
                oblique_steps.append(step)

    max_ct_error = 0.0
    max_cs_error = 0.0
    matching_steps = 0
    split_steps = 0
    q_split_steps = 0
    stable_steps = 0
    for step in oblique_steps:
        surface_index = int(step.surface_index)
        if not (0 <= surface_index < len(editor.rows)):
            continue
        radius_mm = float(editor.rows[surface_index].rc)
        expected_ct, expected_cs = _expected_oblique_refraction_c(
            radius_mm=radius_mm,
            n_before=float(step.n_before),
            n_after=float(step.n_after),
            incidence_deg=float(step.incidence_deg),
        )
        max_ct_error = max(max_ct_error, abs(float(step.tangential_C) - expected_ct))
        max_cs_error = max(max_cs_error, abs(float(step.sagittal_C) - expected_cs))
        matching_steps += 1
        if abs(float(step.tangential_C) - float(step.sagittal_C)) > 1e-9:
            split_steps += 1
        if (
            abs(float(step.tangential_q_real_mm) - float(step.sagittal_q_real_mm)) > 1e-9
            or abs(float(step.tangential_q_imag_mm) - float(step.sagittal_q_imag_mm)) > 1e-9
        ):
            q_split_steps += 1
        if _finite_step(step):
            stable_steps += 1

    return [
        _result(
            title,
            "real UI trace records contain oblique refractive q steps",
            len(records) > 0 and not failures and len(oblique_steps) > 0,
            f"records={len(records)}, oblique_steps={len(oblique_steps)}, failures={len(failures)}",
        ),
        _result(
            title,
            "real UI trace oblique refraction matches first-order Coddington powers",
            (
                matching_steps == len(oblique_steps)
                and matching_steps > 0
                and max_ct_error < 1e-12
                and max_cs_error < 1e-12
            ),
            f"matched={matching_steps}/{len(oblique_steps)}, max_Ct_err={max_ct_error:.3g}, max_Cs_err={max_cs_error:.3g}",
        ),
        _result(
            title,
            "real UI trace exposes branch-local astigmatic q split",
            stable_steps == len(oblique_steps) and split_steps > 0 and q_split_steps > 0,
            f"stable={stable_steps}/{len(oblique_steps)}, C_split={split_steps}, q_split={q_split_steps}",
        ),
    ]


def validate_oblique_astigmatic_q() -> list[ObliqueAstigmaticQCheck]:
    checks: list[ObliqueAstigmaticQCheck] = []
    checks.extend(_validate_flat_fold())
    checks.extend(_validate_oblique_spherical_mirror())
    checks.extend(_validate_near_normal_refraction())
    checks.extend(_validate_oblique_refraction())
    checks.extend(_validate_tilted_powered_plate_refraction())
    checks.extend(_validate_flat_tilted_plate_diagnostic())
    checks.extend(_validate_tir_diagnostic())
    checks.extend(_validate_traced_layout_oblique_refraction("Galvo F-Theta Laser Scanner"))
    return checks


def _print_table(checks: list[ObliqueAstigmaticQCheck]) -> None:
    print("KrakenOS Phase 8B oblique astigmatic q validation")
    print("case | check | status | detail")
    print("--- | --- | --- | ---")
    for check in checks:
        print(f"{check.case} | {check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 8B oblique astigmatic Gaussian-q contracts.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_oblique_astigmatic_q()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
