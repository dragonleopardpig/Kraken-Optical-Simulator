from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

from KrakenOS.UI.validate_branch_analysis import _load_traced_editor


@dataclass
class GaussianBranchFrameCheck:
    layout: str
    check: str
    ok: bool
    detail: str


def _result(layout: str, check: str, ok: bool, detail: str) -> GaussianBranchFrameCheck:
    return GaussianBranchFrameCheck(layout=layout, check=check, ok=bool(ok), detail=str(detail))


def _unit(values) -> np.ndarray | None:
    try:
        vector = np.asarray(values, dtype=float).reshape(-1)[:3]
    except Exception:
        return None
    if vector.size < 3 or not np.all(np.isfinite(vector)):
        return None
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm <= 1e-12:
        return None
    return vector / norm


def _hit_frame(hit: dict[str, object]) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    if not bool(hit.get("gb_frame_valid", False)):
        return None
    k_axis = _unit((hit.get("gb_k_l"), hit.get("gb_k_m"), hit.get("gb_k_n")))
    t_axis = _unit((hit.get("gb_t_l"), hit.get("gb_t_m"), hit.get("gb_t_n")))
    s_axis = _unit((hit.get("gb_s_l"), hit.get("gb_s_m"), hit.get("gb_s_n")))
    if k_axis is None or t_axis is None or s_axis is None:
        return None
    return k_axis, t_axis, s_axis


def _flatten_hits(records: list[dict[str, object]]) -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    for record in records:
        for hit in list(record.get("hits", []) or []):
            item = dict(hit)
            item["source_model"] = str(record.get("source_model", "") or "")
            item["branch_path"] = str(record.get("branch_path", "") or "")
            hits.append(item)
    return hits


def _frame_metrics(hits: list[dict[str, object]]) -> dict[str, float]:
    max_norm_error = 0.0
    max_dot_error = 0.0
    min_handedness = 1.0
    count = 0
    for hit in hits:
        frame = _hit_frame(hit)
        if frame is None:
            continue
        k_axis, t_axis, s_axis = frame
        count += 1
        max_norm_error = max(
            max_norm_error,
            abs(float(np.linalg.norm(k_axis)) - 1.0),
            abs(float(np.linalg.norm(t_axis)) - 1.0),
            abs(float(np.linalg.norm(s_axis)) - 1.0),
        )
        max_dot_error = max(
            max_dot_error,
            abs(float(np.dot(k_axis, t_axis))),
            abs(float(np.dot(k_axis, s_axis))),
            abs(float(np.dot(t_axis, s_axis))),
        )
        min_handedness = min(min_handedness, float(np.dot(np.cross(t_axis, s_axis), k_axis)))
    return {
        "count": float(count),
        "max_norm_error": float(max_norm_error),
        "max_dot_error": float(max_dot_error),
        "min_handedness": float(min_handedness),
    }


def _validate_layout(title: str) -> list[GaussianBranchFrameCheck]:
    editor, _system, _rays, _wavelength = _load_traced_editor(title)
    records = editor._collect_ray_inspector_records()
    hits = _flatten_hits(records)
    valid_hits = [hit for hit in hits if _hit_frame(hit) is not None]
    metrics = _frame_metrics(hits)

    checks: list[GaussianBranchFrameCheck] = [
        _result(
            title,
            "ray inspector exposes branch-local Gaussian T/S/K frames",
            len(valid_hits) > 0,
            f"records={len(records)}, hits={len(hits)}, valid_frames={len(valid_hits)}",
        ),
        _result(
            title,
            "Gaussian branch frames are orthonormal and right-handed",
            metrics["count"] > 0
            and metrics["max_norm_error"] < 1e-9
            and metrics["max_dot_error"] < 1e-9
            and metrics["min_handedness"] > 1.0 - 1e-9,
            (
                f"frames={int(metrics['count'])}, norm_err={metrics['max_norm_error']:.3g}, "
                f"dot_err={metrics['max_dot_error']:.3g}, min_handedness={metrics['min_handedness']:.12g}"
            ),
        ),
    ]

    plane_errors: list[float] = []
    k_match_errors: list[float] = []
    for hit in valid_hits:
        frame = _hit_frame(hit)
        if frame is None:
            continue
        k_axis, _t_axis, s_axis = frame
        normal = _unit((hit.get("normal_l"), hit.get("normal_m"), hit.get("normal_n")))
        if normal is not None:
            normal_projection = normal - (float(np.dot(normal, k_axis)) * k_axis)
            if float(np.linalg.norm(normal_projection)) > 1e-8:
                plane_errors.append(abs(float(np.dot(s_axis, normal))))
        outgoing = _unit((hit.get("out_l"), hit.get("out_m"), hit.get("out_n")))
        if outgoing is not None:
            k_match_errors.append(abs(1.0 - abs(float(np.dot(k_axis, outgoing)))))

    checks.extend(
        [
            _result(
                title,
                "sagittal axis is perpendicular to the local plane of incidence",
                bool(plane_errors) and max(plane_errors) < 1e-9,
                f"samples={len(plane_errors)}, max_abs_dot_s_normal={max(plane_errors) if plane_errors else np.nan:.3g}",
            ),
            _result(
                title,
                "Gaussian propagation axis follows the outgoing branch direction",
                bool(k_match_errors) and max(k_match_errors) < 1e-9,
                f"samples={len(k_match_errors)}, max_axis_error={max(k_match_errors) if k_match_errors else np.nan:.3g}",
            ),
        ]
    )

    unique_k = {
        tuple(np.round(_hit_frame(hit)[0], 6))
        for hit in valid_hits
        if _hit_frame(hit) is not None
    }
    folded_layout = any(token in title for token in ("Galvo", "Beam Splitter", "Michelson", "Mach-Zehnder", "Twyman"))
    checks.append(
        _result(
            title,
            "folded/non-sequential layout carries more than one local propagation axis",
            (not folded_layout) or len(unique_k) > 1,
            f"unique_k={len(unique_k)}",
        )
    )

    interaction_hits = [
        hit
        for hit in valid_hits
        if any(token in str(hit.get("event", "")).lower() for token in ("reflect", "split", "refract", "transmit"))
    ]
    checks.append(
        _result(
            title,
            "physical interaction hits carry valid Gaussian frames",
            len(interaction_hits) > 0,
            f"interaction_frames={len(interaction_hits)}",
        )
    )
    if "Galvo" in title:
        gaussian_hits = [hit for hit in valid_hits if str(hit.get("source_model", "")) == "Gaussian beam"]
        checks.append(
            _result(
                title,
                "folded laser scanner traces Gaussian-source hits with local frames",
                len(gaussian_hits) > 0,
                f"gaussian_source_frames={len(gaussian_hits)}",
            )
        )
    return checks


def validate_gaussian_branch_frames() -> list[GaussianBranchFrameCheck]:
    checks: list[GaussianBranchFrameCheck] = []
    for title in (
        "Galvo F-Theta Laser Scanner",
        "Beam Splitter Two Path Doublets",
        "Michelson Interferometer (Interferogram)",
    ):
        checks.extend(_validate_layout(title))
    return checks


def _print_table(checks: list[GaussianBranchFrameCheck]) -> None:
    print("KrakenOS Gaussian branch-frame validation")
    print("layout | check | status | detail")
    print("--- | --- | --- | ---")
    for check in checks:
        print(f"{check.layout} | {check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate branch-local tangential/sagittal frames for future Gaussian q propagation.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_gaussian_branch_frames()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
