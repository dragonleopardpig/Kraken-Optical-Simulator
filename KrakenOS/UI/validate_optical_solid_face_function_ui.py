from __future__ import annotations

from dataclasses import dataclass

from KrakenOS.UI.optical_solid_metadata import (
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    normalize_optical_solid_face_record,
    optical_solid_face_function_display,
    optical_solid_face_function_from_ui_value,
    optical_solid_face_port_role,
)


@dataclass
class FaceFunctionUiCheck:
    check: str
    ok: bool
    detail: str


def validate_optical_solid_face_function_ui() -> list[FaceFunctionUiCheck]:
    checks: list[FaceFunctionUiCheck] = []
    checks.append(
        FaceFunctionUiCheck(
            "Uncoated UI label maps to the transmit/internal refracting mode",
            optical_solid_face_function_from_ui_value("Uncoated") == OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
            f"mapped={optical_solid_face_function_from_ui_value('Uncoated')}",
        )
    )
    checks.append(
        FaceFunctionUiCheck(
            "legacy TIR metadata displays as Uncoated in the UI",
            optical_solid_face_function_display("TIR") == "Uncoated",
            f"display={optical_solid_face_function_display('TIR')}",
        )
    )
    checks.append(
        FaceFunctionUiCheck(
            "Full Reflecting UI label maps to Mirror",
            optical_solid_face_function_from_ui_value("Full Reflecting") == "Mirror",
            f"mapped={optical_solid_face_function_from_ui_value('Full Reflecting')}",
        )
    )
    checks.append(
        FaceFunctionUiCheck(
            "Partial Reflecting / Transmitting UI label maps to Beam Splitter",
            optical_solid_face_function_from_ui_value("Partial Reflecting / Transmitting") == "Beam Splitter",
            f"mapped={optical_solid_face_function_from_ui_value('Partial Reflecting / Transmitting')}",
        )
    )
    legacy_record = normalize_optical_solid_face_record(
        {
            "face_id": "F003",
            "function": "TIR",
            "side_2d": "Up",
            "port_role": "Interaction Surface",
        }
    )
    checks.append(
        FaceFunctionUiCheck(
            "legacy TIR interaction metadata still normalizes and remains an interaction surface",
            legacy_record.get("function") == "TIR" and optical_solid_face_port_role(legacy_record) == "Interaction Surface",
            f"function={legacy_record.get('function')}, port={optical_solid_face_port_role(legacy_record)}",
        )
    )
    return checks


def main() -> int:
    checks = validate_optical_solid_face_function_ui()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{status}: {check.check} | {check.detail}")
    if failed:
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
