"""Validate Tier 3 STEP-to-native surface reconstruction contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from KrakenOS.UI.services.step_native_reconstruction import (
    STEP_NATIVE_RECONSTRUCTION_ADVANCED_ATTR,
    reconstruct_step_native_surfaces,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASPHERIZED_ACHROMAT_STEP = PROJECT_ROOT / "attachment" / "Lens" / "Aspherized_Achromatic_Lenses" / "step_49665.step"


@dataclass(frozen=True)
class StepNativeReconstructionCheck:
    check: str
    ok: bool
    detail: str


def validate_step_native_reconstruction() -> list[StepNativeReconstructionCheck]:
    if not ASPHERIZED_ACHROMAT_STEP.exists():
        return [
            StepNativeReconstructionCheck(
                "aspherized achromat STEP fixture exists",
                True,
                f"SKIP: missing optional fixture {ASPHERIZED_ACHROMAT_STEP}",
            )
        ]
    try:
        materialless = reconstruct_step_native_surfaces(ASPHERIZED_ACHROMAT_STEP)
        reconstruction = reconstruct_step_native_surfaces(ASPHERIZED_ACHROMAT_STEP, glass_sequence=("BK7", "F2", "AIR"))
    except RuntimeError as exc:
        if "pythonocc-core" in str(exc):
            return [
                StepNativeReconstructionCheck(
                    "pythonocc-core analytic STEP backend is available",
                    True,
                    f"SKIP: {exc}",
                )
            ]
        raise

    fits = list(reconstruction.surface_fits)
    rows = list(reconstruction.rows)
    material_diagnostics = {diagnostic.code for diagnostic in materialless.diagnostics}
    interface_fits = [fit for fit in fits if len(fit.face_ids) >= 2 and any(face_id.startswith("S001/") for face_id in fit.face_ids)]
    asphere_fits = [fit for fit in fits if fit.native_kind == "asphere_polynomial_fit"]
    layout_rows = reconstruction.layout_rows(object_distance_mm=25.0, image_distance_mm=50.0)
    row_summary = [
        {
            "rc": row.rc,
            "thickness": row.thickness,
            "glass": row.glass,
            "advanced": sorted(row.advanced),
        }
        for row in rows
    ]

    checks = [
        StepNativeReconstructionCheck(
            "STEP geometry alone is not treated as trace-ready material data",
            not materialless.trace_ready and "material_sequence_required" in material_diagnostics and len(materialless.rows) == 3,
            f"trace_ready={materialless.trace_ready}, diagnostics={sorted(material_diagnostics)}, rows={len(materialless.rows)}",
        ),
        StepNativeReconstructionCheck(
            "native reconstruction emits a trace-ready KrakenOS row stack when materials are supplied",
            reconstruction.trace_ready and len(fits) == 3 and len(rows) == 3,
            f"trace_ready={reconstruction.trace_ready}, fits={len(fits)}, rows={len(rows)}",
        ),
        StepNativeReconstructionCheck(
            "cemented duplicate STEP faces become one native interface surface",
            bool(interface_fits)
            and any(fit.native_kind == "sphere_exact" and fit.rc_mm < 0.0 and fit.supported for fit in interface_fits),
            f"interfaces={[fit.as_record() for fit in interface_fits]}",
        ),
        StepNativeReconstructionCheck(
            "split vendor B-spline patches become one fitted native asphere",
            len(asphere_fits) == 1
            and len(asphere_fits[0].face_ids) == 2
            and asphere_fits[0].supported
            and asphere_fits[0].rms_error_mm < 0.001
            and asphere_fits[0].max_error_mm < 0.01,
            f"asphere={[fit.as_record() for fit in asphere_fits]}",
        ),
        StepNativeReconstructionCheck(
            "native rows preserve sphere radii, internal spacing, glass sequence, and asphere coefficients",
            len(rows) == 3
            and rows[0].rc > 0.0
            and rows[1].rc < 0.0
            and rows[0].glass == "BK7"
            and rows[1].glass == "F2"
            and rows[2].glass == "AIR"
            and abs(rows[0].thickness - 9.0) < 0.05
            and 2.0 < rows[1].thickness < 3.2
            and STEP_NATIVE_RECONSTRUCTION_ADVANCED_ATTR in rows[2].advanced
            and len(rows[2].advanced.get("AspherData", [])) == 200,
            f"rows={row_summary}",
        ),
        StepNativeReconstructionCheck(
            "native reconstruction can be wrapped as a normal Object/surfaces/Image layout",
            len(layout_rows) == 5
            and layout_rows[0].surface == "Object"
            and layout_rows[-1].surface == "Image"
            and layout_rows[-2].thickness == 50.0,
            f"layout={[row.surface for row in layout_rows]}, last_spacing={layout_rows[-2].thickness if len(layout_rows) >= 2 else None}",
        ),
    ]
    return checks


def main() -> int:
    checks = validate_step_native_reconstruction()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        print(f"{'PASS' if check.ok else 'FAIL'}: {check.check} - {check.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
