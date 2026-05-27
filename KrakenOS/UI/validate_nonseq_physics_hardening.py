"""Validate numerical hardening for non-sequential physics edge cases."""

from __future__ import annotations

from dataclasses import dataclass
import inspect

import numpy as np

import KrakenOS as Kos
from KrakenOS.PhysicsClass import snell_refraction_vector_physics


@dataclass(frozen=True)
class NonSeqPhysicsHardeningCheck:
    check: str
    ok: bool
    detail: str


def _build_reference_system():
    obj = Kos.surf()
    obj.Name = "Object"
    obj.Thickness = 25.0
    obj.Diameter = 25.0
    obj.Glass = "AIR"

    fold = Kos.surf()
    fold.Name = "Reference fold"
    fold.Thickness = 25.0
    fold.Diameter = 25.0
    fold.Glass = "MIRROR"
    fold.TiltX = 45.0
    fold.AxisMove = 2.0

    image = Kos.surf()
    image.Name = "Image"
    image.Thickness = 0.0
    image.Diameter = 25.0
    image.Glass = "AIR"

    return Kos.system([obj, fold, image], Kos.Setup())


def validate_nonseq_physics_hardening() -> list[NonSeqPhysicsHardeningCheck]:
    checks: list[NonSeqPhysicsHardeningCheck] = []

    physics = snell_refraction_vector_physics()
    vector, index, sign, angle = physics.calculate(
        np.asarray((1.0, 0.0, 0.0), dtype=float),
        np.asarray((0.0, 0.0, 1.0e-9), dtype=float),
        1.5,
        1.0,
        None,
        None,
        None,
        None,
        0,
    )
    vector = np.asarray(vector, dtype=float).reshape(-1)[:3]
    checks.append(
        NonSeqPhysicsHardeningCheck(
            "scalar Snell solver keeps finite vectors when the radicand clips at critical/grazing incidence",
            bool(vector.size == 3 and np.all(np.isfinite(vector)) and np.isfinite(float(index)) and np.isfinite(float(angle))),
            f"vector={vector.tolist()}, n={index}, sign={sign}, angle={angle}",
        )
    )

    system = _build_reference_system()
    policy = system._system__NonSequentialIntersectionPolicy()
    kernel_tolerance = float(policy.near_hit_tolerance)
    same_surface_tolerance = float(policy.same_surface_tolerance)
    method_kernel_tolerance = float(system._system__NonSequentialNearHitTolerance())
    method_same_surface_tolerance = float(system._system__NonSequentialSameSurfaceHitTolerance())
    inter_normal_tolerance = float(system.INORM._InterNormalCalc__RaySelfHitTolerance())
    checks.append(
        NonSeqPhysicsHardeningCheck(
            "non-sequential chooser near-hit tolerance scales below the old fixed 0.05 mm prism skip",
            0.0 < kernel_tolerance < 0.001,
            f"kernel_tolerance_mm={kernel_tolerance:.9g}",
        )
    )
    checks.append(
        NonSeqPhysicsHardeningCheck(
            "same-surface self-hit rejection is tighter than real scene spacing but wider than the generic near-hit epsilon",
            kernel_tolerance < same_surface_tolerance < 0.01,
            f"near_mm={kernel_tolerance:.9g}, same_surface_mm={same_surface_tolerance:.9g}",
        )
    )
    checks.append(
        NonSeqPhysicsHardeningCheck(
            "intersection policy preserves the legacy private tolerance accessors",
            abs(method_kernel_tolerance - kernel_tolerance) <= 1.0e-12
            and abs(method_same_surface_tolerance - same_surface_tolerance) <= 1.0e-12,
            (
                f"policy_near_mm={kernel_tolerance:.9g}, method_near_mm={method_kernel_tolerance:.9g}, "
                f"policy_same_surface_mm={same_surface_tolerance:.9g}, "
                f"method_same_surface_mm={method_same_surface_tolerance:.9g}"
            ),
        )
    )
    checks.append(
        NonSeqPhysicsHardeningCheck(
            "intersection policy widens only the current surface's immediate re-hit window",
            policy.rejection_tolerance(2, 2) == same_surface_tolerance
            and policy.rejection_tolerance(3, 2) == kernel_tolerance
            and policy.rejection_tolerance(2, None) == kernel_tolerance,
            (
                f"same_surface_reject_mm={policy.rejection_tolerance(2, 2):.9g}, "
                f"other_surface_reject_mm={policy.rejection_tolerance(3, 2):.9g}, "
                f"no_current_surface_reject_mm={policy.rejection_tolerance(2, None):.9g}"
            ),
        )
    )
    checks.append(
        NonSeqPhysicsHardeningCheck(
            "intersection-normal solid hit filter uses the same scaled near-hit tolerance",
            abs(inter_normal_tolerance - kernel_tolerance) <= 1.0e-12,
            f"inter_normal_mm={inter_normal_tolerance:.9g}, kernel_mm={kernel_tolerance:.9g}",
        )
    )
    system_source = inspect.getsource(Kos.system)
    inter_normal_source = inspect.getsource(Kos.InterNormalCalc)
    checks.append(
        NonSeqPhysicsHardeningCheck(
            "optical-solid mesh face-id assignment is cached within a built non-sequential system",
            "_optical_solid_mesh_face_id_cache" in system_source
            and "def __OpticalSolidWorldFaceSignature" in system_source
            and "assign_mesh_cell_face_ids(" in system_source
            and "cached is not None" in system_source,
            "Repeated mesh ray queries reuse face-id metadata instead of rescanning all triangles every hit.",
        )
    )
    checks.append(
        NonSeqPhysicsHardeningCheck(
            "non-sequential chooser reuses first-pass hit counts instead of retracing the selected mesh",
            "return distance, int(len(A_SurfHit)), A_pTarget, A_SurfHit" in system_source
            and "hit_counts = []" in system_source
            and "PRR = int(hit_counts[int(jj) - 1])" in system_source
            and "f\"non-sequential chooser surface {int(jj)}\"" not in system_source,
            "The chooser no longer performs a second identical mesh ray-trace just to compute PreSurfHit.",
        )
    )
    checks.append(
        NonSeqPhysicsHardeningCheck(
            "intersection-normal solid hits reuse the chooser mesh-ray result for the same segment",
            "def set_trace_mesh_ray_cache" in inter_normal_source
            and "def __PopTraceMeshRayCache" in inter_normal_source
            and "cached = self.__PopTraceMeshRayCache" in inter_normal_source
            and "set_trace_mesh_ray_cache(" in system_source,
            "The selected mesh is not ray-traced again immediately after the chooser already found its intersections.",
        )
    )
    return checks


def main() -> int:
    checks = validate_nonseq_physics_hardening()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        print(f"{'PASS' if check.ok else 'FAIL'}: {check.check} - {check.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
