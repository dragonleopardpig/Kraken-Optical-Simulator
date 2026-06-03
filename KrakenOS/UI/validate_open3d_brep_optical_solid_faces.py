"""Regression: a STEP optical solid is meshed by OCC into a few real B-Rep
faces, with the displayed STL and the face metadata sharing triangle indices.

Bug 0003 Issue 3 was "patched" with display-only grouping over the gmsh STL
(160 planar micro-clusters region-grown back into 3 groups). This pins the
*root-cause* path: import a STEP optical solid through OpenCascade so the editor
lists the true B-Rep faces (the aspheric achromat is 7, not 160) and every
triangle-index-based picker stays aligned because the STL is written from the
same OCC tessellation as the metadata.

Display-free -- it never opens a window. It exercises the seams the live face
editor relies on:

  * ``build_step_optical_solid_mesh`` writes a binary STL whose triangle *order*
    matches ``doc.triangles`` (so ``triangle_indices`` index the displayed mesh)
    and a face sidecar beside it;
  * the achromat collapses to 7 outer faces (sphere + cylinder + bspline), every
    face's ``triangle_indices`` are in range and together cover all triangles;
  * ``optical_solid_metadata_is_brep`` recognises the result (and rejects a
    cluster-shaped metadata that has no ``surface_type``);
  * ``optical_solid_face_record_triangles`` pulls exactly one face's triangles
    out of the STL (the same triangles ``doc.triangles`` has at those indices);
  * the import-time default metadata
    (``_default_uncoated_optical_solid_face_metadata``) returns those 7 B-Rep
    faces, not 160 clusters, with uncoated transmit defaults;
  * the ``KRAKENOS_BREP_OPTICAL_SOLID`` flag gates the path.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_brep_optical_solid_faces

Exit: 0 = pass, 1 = regression, 2 = environment can't load OCC / fixture missing.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STEP_FIXTURE = _REPO_ROOT / "attachment/Lens/Aspherized_Achromatic_Lenses/step_49665.step"
_EXPECTED_FACES = 7


def _run() -> int:
    from KrakenOS.UI.services.step_optical_solid_brep import (
        brep_optical_solid_enabled,
        build_step_optical_solid_mesh,
        face_sidecar_path,
        load_face_sidecar,
    )
    from KrakenOS.UI.services.step_analytic_geometry import load_step_analytic_document
    from KrakenOS.UI.stl_geometry import read_stl_triangle_vertices
    from KrakenOS.UI.services.optical_solid_geometry import (
        optical_solid_face_record_triangles,
        optical_solid_metadata_is_brep,
    )

    failures: list[str] = []

    # --- flag gate (pure) ---
    import os

    saved = os.environ.get("KRAKENOS_BREP_OPTICAL_SOLID")
    try:
        os.environ.pop("KRAKENOS_BREP_OPTICAL_SOLID", None)
        if not brep_optical_solid_enabled():
            failures.append("flag should default ON when unset")
        os.environ["KRAKENOS_BREP_OPTICAL_SOLID"] = "0"
        if brep_optical_solid_enabled():
            failures.append("flag should be OFF for '0'")
        os.environ["KRAKENOS_BREP_OPTICAL_SOLID"] = "1"
        if not brep_optical_solid_enabled():
            failures.append("flag should be ON for '1'")
    finally:
        if saved is None:
            os.environ.pop("KRAKENOS_BREP_OPTICAL_SOLID", None)
        else:
            os.environ["KRAKENOS_BREP_OPTICAL_SOLID"] = saved

    # --- B-Rep detector rejects a cluster-shaped metadata (no surface_type) ---
    if optical_solid_metadata_is_brep({"faces": [{"face_id": "F1"}, {"face_id": "F2"}]}):
        failures.append("metadata_is_brep should be False for cluster faces (no surface_type)")

    tmp = Path(tempfile.mkdtemp())
    stl_path = tmp / "achromat_brep.stl"
    metadata = build_step_optical_solid_mesh(_STEP_FIXTURE, stl_path)

    # --- sidecar written and reloadable ---
    if not face_sidecar_path(stl_path).exists():
        failures.append("face sidecar was not written next to the STL")
    reloaded = load_face_sidecar(stl_path)
    if reloaded is None or len(reloaded.get("faces", [])) != _EXPECTED_FACES:
        failures.append(f"sidecar should reload {_EXPECTED_FACES} faces, got {reloaded and len(reloaded.get('faces', []))}")

    faces = list(metadata.get("faces", []))
    if len(faces) != _EXPECTED_FACES:
        failures.append(f"expected {_EXPECTED_FACES} B-Rep faces, got {len(faces)}")
    if not optical_solid_metadata_is_brep(metadata):
        failures.append("metadata_is_brep should be True for the OCC document metadata")
    types = {str(f.get("surface_type") or "") for f in faces}
    for required in ("sphere", "cylinder", "bspline"):
        if required not in types:
            failures.append(f"expected a '{required}' face among {sorted(types)}")

    # --- STL written in doc.triangles order (indices stay aligned) ---
    doc = load_step_analytic_document(_STEP_FIXTURE)
    doc_tris = np.asarray(doc.triangles, dtype=float).reshape(-1, 3, 3)
    _fmt, stl_tris = read_stl_triangle_vertices(stl_path)
    if stl_tris.shape[0] != doc_tris.shape[0]:
        failures.append(f"STL triangle count {stl_tris.shape[0]} != doc {doc_tris.shape[0]}")
    else:
        max_err = float(np.abs(stl_tris - doc_tris).max())
        if max_err > 1e-2:  # float32 STL storage; ~1e-6 in practice
            failures.append(f"STL not written in doc order: max vertex error {max_err:.3e}")

    # --- per-face triangle indices: in range and a full cover ---
    n_tri = int(stl_tris.shape[0])
    covered: set[int] = set()
    for face in faces:
        for raw in face.get("triangle_indices", []) or []:
            idx = int(raw)
            if not 0 <= idx < n_tri:
                failures.append(f"triangle index {idx} out of range [0,{n_tri})")
                break
            covered.add(idx)
    if len(covered) != n_tri:
        failures.append(f"faces cover {len(covered)} of {n_tri} triangles (expected full cover)")

    # --- record triangle puller returns exactly that face's STL triangles ---
    sample = max(faces, key=lambda f: len(f.get("triangle_indices", []) or []))
    pulled = optical_solid_face_record_triangles(stl_path, sample)
    sample_idx = np.asarray([int(i) for i in sample.get("triangle_indices", [])], dtype=int)
    if pulled.shape[0] != sample_idx.size:
        failures.append(f"record puller returned {pulled.shape[0]} tris, face has {sample_idx.size}")
    elif sample_idx.size:
        if float(np.abs(pulled - stl_tris[sample_idx]).max()) > 1e-6:
            failures.append("record puller triangles do not match the STL rows at those indices")

    # --- import-time default metadata uses the sidecar (7 B-Rep faces) ---
    import KrakenOS.UI.layout_editor  # noqa: F401  (wires module globals via _sync_layout_globals)
    from KrakenOS.UI.services.optical_solid_workflow import LayoutOpticalSolidWorkflowMixin

    default_meta = LayoutOpticalSolidWorkflowMixin._default_uncoated_optical_solid_face_metadata(stl_path)
    if default_meta is None or len(default_meta.get("faces", [])) != _EXPECTED_FACES:
        got = None if default_meta is None else len(default_meta.get("faces", []))
        failures.append(f"default metadata should be {_EXPECTED_FACES} B-Rep faces, got {got}")
    elif not optical_solid_metadata_is_brep(default_meta):
        failures.append("default metadata lost its B-Rep surface_type tags")

    if failures:
        for msg in failures:
            print(f"FAIL: {msg}", file=sys.stderr)
        return 1
    print(
        f"PASS: STEP optical solid -> {_EXPECTED_FACES} OCC B-Rep faces "
        f"({', '.join(sorted(types))}); STL written in doc order ({n_tri} tris, "
        "full per-face cover); record puller aligned; default metadata B-Rep."
    )
    return 0


def main() -> int:
    if not _STEP_FIXTURE.exists():
        print(f"SKIP: STEP fixture not found: {_STEP_FIXTURE}", file=sys.stderr)
        return 2
    try:
        return _run()
    except RuntimeError as exc:
        # load_step_analytic_document raises RuntimeError when pythonocc-core is
        # absent -- that is an environment skip, not a regression.
        if "pythonocc" in str(exc).lower() or "OCC" in str(exc):
            print(f"SKIP: OCC backend unavailable ({exc})", file=sys.stderr)
            return 2
        raise


if __name__ == "__main__":
    raise SystemExit(main())
