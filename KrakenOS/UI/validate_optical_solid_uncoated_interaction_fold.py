from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.nonseq_output_ports import (
    _frame_rotation_from_normal,
    _reflected_frame_from_interaction_face,
    select_optical_solid_output_face,
    select_optical_solid_interaction_face,
)
from KrakenOS.UI.optical_solid_metadata import OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT


@dataclass
class UncoatedInteractionFoldCheck:
    check: str
    ok: bool
    detail: str


def _interaction_face(
    *,
    face_id: str,
    function: str,
    area_mm2: float,
    normal_world: tuple[float, float, float],
) -> dict[str, object]:
    return {
        "face_id": face_id,
        "function": function,
        "port_role": "Interaction Surface",
        "side_2d": "Up",
        "area_mm2": float(area_mm2),
        "centroid_world": (0.0, 0.0, 0.0),
        "normal_world": normal_world,
    }


def validate_optical_solid_uncoated_interaction_fold() -> list[UncoatedInteractionFoldCheck]:
    checks: list[UncoatedInteractionFoldCheck] = []
    uncoated_face = _interaction_face(
        face_id="F003",
        function=OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
        area_mm2=100.0,
        normal_world=(0.0, -0.7071067811865476, 0.7071067811865476),
    )
    legacy_tir_face = _interaction_face(
        face_id="F004",
        function="TIR",
        area_mm2=90.0,
        normal_world=(0.0, -0.7071067811865476, 0.7071067811865476),
    )
    mirror_face = _interaction_face(
        face_id="F005",
        function="Mirror",
        area_mm2=120.0,
        normal_world=(0.0, -0.7071067811865476, 0.7071067811865476),
    )

    selected_uncoated = select_optical_solid_interaction_face([uncoated_face])
    checks.append(
        UncoatedInteractionFoldCheck(
            "uncoated interaction face is eligible for folded-path selection",
            isinstance(selected_uncoated, dict) and str(selected_uncoated.get("face_id")) == "F003",
            f"selected={selected_uncoated.get('face_id') if isinstance(selected_uncoated, dict) else None}",
        )
    )

    reflected = _reflected_frame_from_interaction_face(
        [uncoated_face],
        np.asarray((0.0, 0.0, -10.0), dtype=float),
        _frame_rotation_from_normal((0.0, 0.0, 1.0)),
        12.0,
    )
    if reflected is None:
        checks.append(
            UncoatedInteractionFoldCheck(
                "uncoated interaction face generates a reflected downstream frame",
                False,
                "reflected frame was None",
            )
        )
    else:
        center, rotation = reflected
        outgoing = np.asarray(rotation[:, 2], dtype=float).reshape(3)
        checks.append(
            UncoatedInteractionFoldCheck(
                "uncoated interaction face generates a reflected downstream frame",
                np.allclose(outgoing, np.asarray((0.0, 1.0, 0.0), dtype=float), atol=1e-6)
                and np.allclose(center, np.asarray((0.0, 12.0, 0.0), dtype=float), atol=1e-6),
                f"center={tuple(np.round(center, 6).tolist())}, outgoing={tuple(np.round(outgoing, 6).tolist())}",
            )
        )

    selected_legacy = select_optical_solid_interaction_face([legacy_tir_face])
    checks.append(
        UncoatedInteractionFoldCheck(
            "legacy TIR interaction metadata still behaves like uncoated fold metadata",
            isinstance(selected_legacy, dict) and str(selected_legacy.get("face_id")) == "F004",
            f"selected={selected_legacy.get('face_id') if isinstance(selected_legacy, dict) else None}",
        )
    )

    selected_mixed = select_optical_solid_interaction_face([uncoated_face, mirror_face])
    checks.append(
        UncoatedInteractionFoldCheck(
            "explicit full-reflecting faces still outrank uncoated interaction faces",
            isinstance(selected_mixed, dict) and str(selected_mixed.get("face_id")) == "F005",
            f"selected={selected_mixed.get('face_id') if isinstance(selected_mixed, dict) else None}",
        )
    )
    explicit_output_face = {
        "face_id": "F006",
        "function": OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
        "port_role": "Output Port",
        "side_2d": "Right",
        "area_mm2": 80.0,
        "centroid_world": (0.0, 0.0, 5.0),
        "normal_world": (0.0, 0.0, 1.0),
    }
    selected_output = select_optical_solid_output_face([uncoated_face, explicit_output_face])
    checks.append(
        UncoatedInteractionFoldCheck(
            "uncoated interaction face is not misread as an inferred output face",
            isinstance(selected_output, dict) and str(selected_output.get("face_id")) == "F006",
            f"selected={selected_output.get('face_id') if isinstance(selected_output, dict) else None}",
        )
    )
    return checks


def main() -> int:
    checks = validate_optical_solid_uncoated_interaction_fold()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{status}: {check.check} | {check.detail}")
    if failed:
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
