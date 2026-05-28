"""Validate native STEP analytic face extraction for Tier 3 CAD work."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.step_analytic_geometry import load_step_analytic_document


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASPHERIZED_ACHROMAT_STEP = PROJECT_ROOT / "attachment" / "Lens" / "aspherized-achromatic-lenses" / "step_49665.step"


@dataclass(frozen=True)
class StepAnalyticImportCheck:
    check: str
    ok: bool
    detail: str


def validate_step_analytic_import() -> list[StepAnalyticImportCheck]:
    if not ASPHERIZED_ACHROMAT_STEP.exists():
        return [
            StepAnalyticImportCheck(
                "aspherized achromat STEP fixture exists",
                True,
                f"SKIP: missing optional fixture {ASPHERIZED_ACHROMAT_STEP}",
            )
        ]
    try:
        document = load_step_analytic_document(ASPHERIZED_ACHROMAT_STEP)
    except RuntimeError as exc:
        if "pythonocc-core" in str(exc):
            return [
                StepAnalyticImportCheck(
                    "pythonocc-core analytic STEP backend is available",
                    True,
                    f"SKIP: {exc}",
                )
            ]
        raise

    outer_face_ids = [face.face_id for face in document.outer_faces]
    outer_surface_types = {face.surface_type for face in document.outer_faces}
    source_surface_types = {face.surface_type for face in document.faces}
    metadata = document.optical_solid_face_metadata()
    metadata_faces = [face for face in list(metadata.get("faces", []) or []) if isinstance(face, dict)]
    app_metadata: dict[str, object] = {}
    try:
        app = KrakenLayoutEditor(headless=True)
        try:
            app.imported_lens_step_path = ASPHERIZED_ACHROMAT_STEP
            app.lens_step_largest_component_only = True
            app_metadata = app._step_overlay_face_metadata("lens")
        finally:
            try:
                app.destroy()
            except Exception:
                pass
    except Exception as exc:
        app_metadata = {"error": str(exc)}
    app_metadata_faces = [face for face in list(app_metadata.get("faces", []) or []) if isinstance(face, dict)]
    app_grouped_faces = [
        face
        for face in app_metadata_faces
        if len(list(face.get("source_face_ids", []) or [])) > 1
    ]
    axis = np.asarray((0.0, 0.0, 1.0), dtype=float)

    def _face_axis_alignment(face: dict[str, object]) -> float:
        try:
            normal = np.asarray(face.get("normal", (0.0, 0.0, 1.0)), dtype=float).reshape(3)
        except Exception:
            return 0.0
        return abs(float(np.dot(normal, axis)))

    triangle_total = int(document.triangles.shape[0])
    expected_indices = list(range(triangle_total))
    actual_indices: list[int] = []
    for face in document.outer_faces:
        actual_indices.extend(int(index) for index in face.triangle_indices)

    checks = [
        StepAnalyticImportCheck(
            "native STEP import preserves multi-solid B-Rep topology",
            document.backend == "OpenCascade" and document.solid_count == 2 and document.source_face_count >= 9,
            (
                f"backend={document.backend}, solids={document.solid_count}, "
                f"source_faces={document.source_face_count}"
            ),
        ),
        StepAnalyticImportCheck(
            "native STEP face IDs are qualified by solid",
            bool(outer_face_ids) and all("/" in face_id for face_id in outer_face_ids),
            f"outer_face_ids={outer_face_ids[:8]}",
        ),
        StepAnalyticImportCheck(
            "coincident cemented interior faces are detected and skipped from outer picks",
            document.interior_duplicate_count >= 2
            and len(document.outer_faces) < document.source_face_count
            and all(not face.interior_duplicate for face in document.outer_faces),
            (
                f"source_faces={document.source_face_count}, outer_faces={len(document.outer_faces)}, "
                f"interior_duplicates={document.interior_duplicate_count}"
            ),
        ),
        StepAnalyticImportCheck(
            "analytic surface descriptors include curved optical faces",
            "bspline" in source_surface_types and {"sphere", "bspline"}.issubset(source_surface_types),
            f"source_surface_types={sorted(source_surface_types)}, outer_surface_types={sorted(outer_surface_types)}",
        ),
        StepAnalyticImportCheck(
            "face-aware tessellation maps every retained triangle to one native face",
            document.triangles.ndim == 3
            and document.triangles.shape[1:] == (3, 3)
            and triangle_total > 0
            and sorted(actual_indices) == expected_indices
            and np.all(np.isfinite(document.triangles)),
            f"triangles={triangle_total}, face_triangle_counts={[face.triangle_count for face in document.outer_faces]}",
        ),
        StepAnalyticImportCheck(
            "optical-solid metadata preserves analytic face identity",
            len(metadata_faces) == len(document.outer_faces)
            and all(str(face.get("surface_type", "") or "") for face in metadata_faces)
            and all(str(face.get("source_face_id", "") or "") for face in metadata_faces),
            (
                f"metadata_faces={len(metadata_faces)}, "
                f"sample={metadata_faces[0] if metadata_faces else {}}"
            ),
        ),
        StepAnalyticImportCheck(
            "Open 3D STEP overlay metadata groups split analytic optical faces before planar fallback",
            0 < len(app_metadata_faces) <= len(document.outer_faces)
            and int(app_metadata.get("interior_duplicate_count", -1)) == int(document.interior_duplicate_count)
            and all(str(face.get("assignment_source", "") or "").startswith("step_analytic") for face in app_metadata_faces)
            and any("+" in str(face.get("face_id", "") or "") for face in app_grouped_faces)
            and any(_face_axis_alignment(face) > 0.999 for face in app_grouped_faces),
            (
                f"faces={len(app_metadata_faces)}, "
                f"grouped={[(face.get('face_id'), face.get('source_face_ids')) for face in app_grouped_faces]}, "
                f"interior_duplicates={app_metadata.get('interior_duplicate_count')}, "
                f"error={app_metadata.get('error', '')}"
            ),
        ),
    ]
    return checks


def main() -> int:
    checks = validate_step_analytic_import()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        print(f"{'PASS' if check.ok else 'FAIL'}: {check.check} - {check.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
