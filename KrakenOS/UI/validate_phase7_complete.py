from __future__ import annotations

import argparse
import contextlib
import io
import json
from dataclasses import asdict, dataclass
from typing import Callable

from KrakenOS.UI.validate_detector_sampling_stability import validate_detector_sampling_stability
from KrakenOS.UI.validate_diffraction_detector import validate_diffraction_detector
from KrakenOS.UI.validate_gaussian_branch_frames import validate_gaussian_branch_frames
from KrakenOS.UI.validate_gaussian_branch_q import validate_gaussian_branch_q
from KrakenOS.UI.validate_gaussian_detector_recombination import validate_gaussian_detector_recombination
from KrakenOS.UI.validate_interferogram_detector_accumulation import (
    validate_interferogram_detector_accumulation,
)
from KrakenOS.UI.validate_mixed_source_object_template import validate_mixed_source_object_template
from KrakenOS.UI.validate_multi_scene_sources import validate_multi_scene_sources
from KrakenOS.UI.validate_optical_solid_face_fit import validate_optical_solid_face_fit
from KrakenOS.UI.validate_optical_solid_hit_sequence import validate_optical_solid_hit_sequence
from KrakenOS.UI.validate_optical_solid_path_fit import validate_optical_solid_path_fit
from KrakenOS.UI.validate_optical_solid_snap_to_ray import validate_optical_solid_snap_to_ray
from KrakenOS.UI.validate_optical_solid_virtual_plane import validate_optical_solid_virtual_plane
from KrakenOS.UI.validate_scene_source_row_contract import validate_scene_source_row_contract
from KrakenOS.UI.validate_source_object_split import validate_source_object_split
from KrakenOS.UI.validate_tolerance_monte_carlo import validate_tolerance_monte_carlo


@dataclass
class Phase7ValidationCheck:
    area: str
    check: str
    ok: bool
    detail: str


Validator = Callable[[], list[object]]


VALIDATION_SUITES: tuple[tuple[str, Validator], ...] = (
    ("7A CAD/STL anchors", validate_optical_solid_snap_to_ray),
    ("7A CAD/STL anchors", validate_optical_solid_face_fit),
    ("7A CAD/STL anchors", validate_optical_solid_path_fit),
    ("7A CAD/STL anchors", validate_optical_solid_virtual_plane),
    ("7A CAD/STL anchors", validate_optical_solid_hit_sequence),
    ("7B coherent/diffraction detectors", validate_interferogram_detector_accumulation),
    ("7B coherent/diffraction detectors", validate_diffraction_detector),
    ("7B coherent/diffraction detectors", validate_detector_sampling_stability),
    ("7C Gaussian branch propagation", validate_gaussian_branch_frames),
    ("7C Gaussian branch propagation", validate_gaussian_branch_q),
    ("7C Gaussian branch propagation", validate_gaussian_detector_recombination),
    ("7D source/object scene editing", validate_multi_scene_sources),
    ("7D source/object scene editing", validate_scene_source_row_contract),
    ("7D source/object scene editing", validate_source_object_split),
    ("7D source/object scene editing", validate_mixed_source_object_template),
    ("7E tolerance/manufacturing", validate_tolerance_monte_carlo),
)


def _check_name(raw_check: object) -> str:
    parts: list[str] = []
    for attr in ("layout", "component", "path"):
        value = getattr(raw_check, attr, "")
        text = str(value or "").strip()
        if text:
            parts.append(text)
    check = str(getattr(raw_check, "check", "") or "").strip()
    if check:
        parts.append(check)
    return ": ".join(parts) if parts else raw_check.__class__.__name__


def _run_validator(area: str, validator: Validator) -> list[Phase7ValidationCheck]:
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            raw_checks = validator()
    except Exception as exc:
        output = buffer.getvalue().strip()
        detail = str(exc)
        if output:
            detail = f"{detail}; output={output}"
        return [Phase7ValidationCheck(area, validator.__name__, False, detail)]
    checks: list[Phase7ValidationCheck] = []
    for raw_check in raw_checks:
        checks.append(
            Phase7ValidationCheck(
                area=area,
                check=_check_name(raw_check),
                ok=bool(getattr(raw_check, "ok", False)),
                detail=str(getattr(raw_check, "detail", "")),
            )
        )
    return checks


def validate_phase7_complete() -> list[Phase7ValidationCheck]:
    checks: list[Phase7ValidationCheck] = []
    for area, validator in VALIDATION_SUITES:
        checks.extend(_run_validator(area, validator))
    return checks


def _print_table(checks: list[Phase7ValidationCheck]) -> None:
    print("KrakenOS Phase 7 completion validation")
    print("area | check | status | detail")
    print("--- | --- | --- | ---")
    for check in checks:
        print(f"{check.area} | {check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the Phase 7 non-sequential refinement closure validation suite."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_phase7_complete()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
