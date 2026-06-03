"""OCC B-Rep meshing for STEP-sourced optical solids (bug 0003 Issue 3, real fix).

The legacy optical-solid import goes STEP -> gmsh -> STL -> re-cluster triangles
by plane, which shatters one curved optical surface into ~160 planar
micro-faces. OpenCascade already knows the true face topology (the aspheric
achromat is 7 outer faces, not 160), so this module meshes the STEP *in
process* with OCC and emits two artifacts that the rest of the pipeline already
knows how to consume:

  * a binary STL written from ``doc.triangles`` **in order**, so every
    triangle-index-based picker / highlighter (which indexes into the displayed
    STL) stays aligned with the face metadata; and
  * a sidecar JSON of the per-face metadata (``surface_type`` +
    ``triangle_indices``) from the *same* document, so the face editor lists the
    real B-Rep faces instead of re-clustering the STL.

Because both artifacts come from one tessellation, the displayed mesh and the
face metadata share triangle indices -- no rewrite of the existing index-based
picking/highlight machinery is needed.

Gated by ``KRAKENOS_BREP_OPTICAL_SOLID`` (default on). When off, or when OCC
cannot load the file, callers fall back to the gmsh STL path. All OCC imports
are lazy (inside functions) so importing this module never pulls in the CAD
backend.
"""
from __future__ import annotations

import json
import os
import struct
from pathlib import Path

import numpy as np

FACE_SIDECAR_SUFFIX = ".kraken_brep_faces.json"

_DISABLED_VALUES = {"0", "false", "no", "off", ""}


def brep_optical_solid_enabled() -> bool:
    """True unless ``KRAKENOS_BREP_OPTICAL_SOLID`` is explicitly disabled."""

    raw = os.environ.get("KRAKENOS_BREP_OPTICAL_SOLID")
    if raw is None:
        return True
    return raw.strip().lower() not in _DISABLED_VALUES


def face_sidecar_path(stl_path: Path | str) -> Path:
    """Path of the face-metadata sidecar that sits next to the cached STL."""

    stl = Path(stl_path)
    return stl.with_name(stl.name + FACE_SIDECAR_SUFFIX)


def write_triangles_binary_stl(triangles: np.ndarray, path: Path | str) -> int:
    """Write ``triangles`` (N,3,3) to a binary STL, preserving triangle order.

    Returns the triangle count written. The per-facet normal is computed from
    the vertices (STL stores one, but every reader recomputes from geometry);
    what matters here is that triangle *i* in ``triangles`` is facet *i* in the
    file, so ``read_stl_triangle_vertices`` round-trips the indexing that the
    face metadata's ``triangle_indices`` rely on.
    """

    tris = np.asarray(triangles, dtype=np.float64).reshape(-1, 3, 3)
    n = int(tris.shape[0])
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    v0 = tris[:, 0, :]
    v1 = tris[:, 1, :]
    v2 = tris[:, 2, :]
    normals = np.cross(v1 - v0, v2 - v0)
    lengths = np.linalg.norm(normals, axis=1)
    safe = lengths > 1.0e-12
    normals[safe] /= lengths[safe, None]
    normals[~safe] = 0.0

    # Vectorized write: a packed 50-byte record per facet (normal + 3 verts +
    # uint16 attr), built once and dumped with tofile -- no per-triangle Python
    # loop, so a large STEP (hundreds of thousands of facets) writes responsively.
    stl_record = np.dtype(
        [("normal", "<f4", (3,)), ("v0", "<f4", (3,)), ("v1", "<f4", (3,)), ("v2", "<f4", (3,)), ("attr", "<u2")]
    )
    facets = np.zeros(n, dtype=stl_record)
    facets["normal"] = normals
    facets["v0"] = v0
    facets["v1"] = v1
    facets["v2"] = v2  # attr stays 0

    with out.open("wb") as fh:
        fh.write(b"KrakenOS OCC B-Rep optical solid".ljust(80, b"\0")[:80])
        fh.write(struct.pack("<I", n))
        facets.tofile(fh)
    return n


def build_step_optical_solid_mesh(
    step_path: Path | str,
    stl_out_path: Path | str,
    *,
    linear_deflection_mm: float = 0.2,
    angular_deflection_rad: float = 0.2,
) -> dict:
    """Mesh a STEP optical solid with OCC; write STL + face sidecar, aligned.

    Loads the analytic document once, writes ``doc.triangles`` to
    ``stl_out_path`` in order, and writes the per-face metadata (from the same
    document) to the sidecar beside it. Returns the metadata dict (with
    ``source_stl`` pointing at the written STL).

    Raises if OCC cannot load the file or the tessellation is empty, so the
    caller can fall back to the gmsh STL path.
    """

    from KrakenOS.UI.services.step_analytic_geometry import load_step_analytic_document

    step = Path(step_path)
    stl_out = Path(stl_out_path)

    doc = load_step_analytic_document(
        step,
        linear_deflection_mm=linear_deflection_mm,
        angular_deflection_rad=angular_deflection_rad,
    )
    if int(np.asarray(doc.triangles).reshape(-1, 3, 3).shape[0]) == 0:
        raise RuntimeError(f"OCC tessellated no triangles for STEP: {step}")

    write_triangles_binary_stl(doc.triangles, stl_out)

    metadata = doc.optical_solid_face_metadata()
    metadata["source_stl"] = str(stl_out)

    sidecar = face_sidecar_path(stl_out)
    sidecar.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def load_face_sidecar(stl_path: Path | str) -> dict | None:
    """Return the B-Rep face metadata written next to ``stl_path``, else None."""

    sidecar = face_sidecar_path(stl_path)
    if not sidecar.exists():
        return None
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict) or not data.get("faces"):
        return None
    return data
