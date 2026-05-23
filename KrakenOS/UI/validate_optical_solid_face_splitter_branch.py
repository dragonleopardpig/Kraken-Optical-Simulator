from __future__ import annotations

from dataclasses import dataclass

import KrakenOS as Kos

from KrakenOS.UI.optical_solid_metadata import (
    normalize_optical_solid_face_record,
)


@dataclass
class FaceSplitterBranchCheck:
    check: str
    ok: bool
    detail: str


def _sample_system(face_record: dict) -> Kos.system:
    obj = Kos.surf()
    obj.Name = "Object"
    obj.Glass = "AIR"
    obj.Thickness = 10.0
    obj.Diameter = 10.0

    solid = Kos.surf()
    solid.Name = "Optical solid"
    solid.Glass = "BK7"
    solid.Thickness = 10.0
    solid.Diameter = 10.0
    solid.OpticalSolidFaces = {"faces": [face_record]}

    image = Kos.surf()
    image.Name = "Image"
    image.Glass = "AIR"
    image.Thickness = 0.0
    image.Diameter = 10.0

    return Kos.system([obj, solid, image], Kos.Setup(), build=0)


def validate_optical_solid_face_splitter_branch() -> list[FaceSplitterBranchCheck]:
    checks: list[FaceSplitterBranchCheck] = []
    splitter_face = normalize_optical_solid_face_record(
        {
            "face_id": "F004",
            "function": "Beam Splitter",
            "split_ratio": 0.35,
            "loss": 0.05,
            "phase_deg": 12.0,
            "port_role": "Interaction Surface",
        }
    )
    system = _sample_system(splitter_face)
    settings = getattr(system, "_system__BeamSplitterSettings")(1, face_override=splitter_face)
    checks.append(
        FaceSplitterBranchCheck(
            "face-level Beam Splitter metadata creates deterministic branch settings",
            isinstance(settings, dict) and bool(settings.get("deterministic")),
            f"settings={settings}",
        )
    )
    checks.append(
        FaceSplitterBranchCheck(
            "face-level split ratio is reflected into reflected/transmitted power",
            (
                isinstance(settings, dict)
                and abs(float(settings.get("reflectance", -1.0)) - 0.35) < 1e-12
                and abs(float(settings.get("transmittance", -1.0)) - 0.60) < 1e-12
                and abs(float(settings.get("absorption", -1.0)) - 0.05) < 1e-12
            ),
            (
                f"R={settings.get('reflectance') if isinstance(settings, dict) else '-'}, "
                f"T={settings.get('transmittance') if isinstance(settings, dict) else '-'}, "
                f"A={settings.get('absorption') if isinstance(settings, dict) else '-'}"
            ),
        )
    )
    checks.append(
        FaceSplitterBranchCheck(
            "face-level splitter metadata forces the non-sequential branch tracer path",
            bool(getattr(system, "_system__NsTraceRequiresBranching")()),
            "branching_required="
            f"{bool(getattr(system, '_system__NsTraceRequiresBranching')())}",
        )
    )

    transmit_face = normalize_optical_solid_face_record(
        {
            "face_id": "F005",
            "function": "Transmit",
            "split_ratio": 0.5,
            "port_role": "Interaction Surface",
        }
    )
    plain_settings = getattr(system, "_system__BeamSplitterSettings")(1, face_override=transmit_face)
    checks.append(
        FaceSplitterBranchCheck(
            "ordinary Uncoated/Transmit faces do not create synthetic branch settings",
            plain_settings is None,
            f"settings={plain_settings}",
        )
    )

    zero_split_face = normalize_optical_solid_face_record(
        {
            "face_id": "F006",
            "function": "Beam Splitter",
            "split_ratio": 0.0,
            "loss": 0.0,
            "phase_deg": 0.0,
            "port_role": "Interaction Surface",
        }
    )
    zero_settings = getattr(system, "_system__BeamSplitterSettings")(1, face_override=zero_split_face)
    checks.append(
        FaceSplitterBranchCheck(
            "zero-valued splitter fields remain valid user input",
            (
                isinstance(zero_settings, dict)
                and abs(float(zero_settings.get("reflectance", -1.0))) < 1e-12
                and abs(float(zero_settings.get("transmittance", -1.0)) - 1.0) < 1e-12
                and abs(float(zero_settings.get("reflect_phase_deg", -1.0))) < 1e-12
            ),
            (
                f"R={zero_settings.get('reflectance') if isinstance(zero_settings, dict) else '-'}, "
                f"T={zero_settings.get('transmittance') if isinstance(zero_settings, dict) else '-'}, "
                f"phase={zero_settings.get('reflect_phase_deg') if isinstance(zero_settings, dict) else '-'}"
            ),
        )
    )
    return checks


def main() -> int:
    checks = validate_optical_solid_face_splitter_branch()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{status}: {check.check} | {check.detail}")
    if failed:
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
