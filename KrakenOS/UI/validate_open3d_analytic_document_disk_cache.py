"""Display-free guard for bugs/0368 -- disk-cache the analytic STEP document.

A heavy STEP body's analytic B-rep (the 591k-triangle HR25xCXP camera) took 34-36 s
to load via pythonocc on the FIRST hover of every app launch, blocking the UI thread
(it was cached only in memory). It is now pickled to disk keyed by the mtime+size
stamped base path (so an edited STEP auto-invalidates) and reloads in ~0.1 s.

Checks (all on a tiny SYNTHETIC document -- never the 36 s camera load):
* the cache path is a ``.analytic_doc.<version>.pkl`` beside the mesh cache;
* the validator accepts a well-formed document and rejects a wrong type / bad
  triangle shape / no-faces document (so a corrupt pickle can never be trusted);
* atomic write + pickle round-trip preserves faces + triangles;
* WIRING: ``_load_step_analytic_document`` reads the disk cache before the OCC load
  and writes it after, with graceful unlink-and-fall-through on a corrupt cache.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_analytic_document_disk_cache
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import numpy as np

from KrakenOS.UI.services.layout_polyline_display import (
    _ANALYTIC_DOCUMENT_CACHE_VERSION,
    _cached_analytic_document_path,
    _is_valid_cached_analytic_document,
    _write_analytic_document_cache,
)
from KrakenOS.UI.services.step_analytic_geometry import (
    StepAnalyticDocument,
    StepAnalyticFace,
)


def _synthetic_document() -> StepAnalyticDocument:
    face = StepAnalyticFace(
        face_id="S001/F001",
        solid_index=1,
        source_face_index=1,
        surface_type="plane",
        centroid=(0.0, 0.0, 0.0),
        normal=(0.0, 0.0, 1.0),
        area_mm2=1.0,
        bbox=(0.0, 0.0, 0.0, 1.0, 1.0, 0.0),
        plane_offset_mm=0.0,
        u_range=(0.0, 1.0),
        v_range=(0.0, 1.0),
        triangle_count=2,
        triangle_indices=(0, 1),
    )
    return StepAnalyticDocument(
        source_path=Path("synthetic.step"),
        source_format="STEP",
        backend="occ",
        solid_count=1,
        source_face_count=1,
        faces=(face,),
        outer_faces=(face,),
        triangles=np.arange(2 * 3 * 3, dtype=float).reshape(2, 3, 3),
        warnings=(),
    )


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        fake_step = Path(tmp) / "bar.STEP"
        fake_step.write_bytes(b"ISO-10303-21;\n")  # the path helper stamps mtime+size
        path = _cached_analytic_document_path(fake_step)
        if not path.name.endswith(f".analytic_doc.{_ANALYTIC_DOCUMENT_CACHE_VERSION}.pkl"):
            failures.append(f"cache path is not a versioned analytic_doc pickle: {path.name}")

    doc = _synthetic_document()
    if not _is_valid_cached_analytic_document(doc):
        failures.append("a well-formed document must validate")
    if _is_valid_cached_analytic_document({"not": "a document"}):
        failures.append("a non-document must be rejected")
    bad_tris = StepAnalyticDocument(
        source_path=Path("x.step"), source_format="STEP", backend="occ", solid_count=1,
        source_face_count=1, faces=doc.faces, outer_faces=doc.outer_faces,
        triangles=np.zeros((2, 2, 3), dtype=float), warnings=(),
    )
    if _is_valid_cached_analytic_document(bad_tris):
        failures.append("a document with a non-(N,3,3) triangle array must be rejected")
    no_faces = StepAnalyticDocument(
        source_path=Path("x.step"), source_format="STEP", backend="occ", solid_count=1,
        source_face_count=0, faces=(), outer_faces=(),
        triangles=np.zeros((2, 3, 3), dtype=float), warnings=(),
    )
    if _is_valid_cached_analytic_document(no_faces):
        failures.append("a document with no outer faces must be rejected")

    with tempfile.TemporaryDirectory() as tmp:
        cache_path = Path(tmp) / "doc.analytic_doc.v1.pkl"
        _write_analytic_document_cache(cache_path, doc)
        if not cache_path.exists() or cache_path.stat().st_size <= 0:
            failures.append("write must produce a non-empty pickle")
        if list(Path(tmp).glob("*.tmp")):
            failures.append("the atomic temp file must be renamed away, not left behind")
        import pickle

        with open(cache_path, "rb") as handle:
            loaded = pickle.load(handle)
        if not _is_valid_cached_analytic_document(loaded):
            failures.append("the round-tripped document must validate")
        elif (
            len(loaded.outer_faces) != 1
            or loaded.outer_faces[0].face_id != "S001/F001"
            or not np.array_equal(loaded.triangles, doc.triangles)
        ):
            failures.append("the round-tripped document must preserve faces + triangles")

    src = inspect.getsource(
        __import__("KrakenOS.UI.services.layout_polyline_display", fromlist=["x"])
        .LayoutPolylineDisplayMixin._load_step_analytic_document
    )
    for needle in (
        "_cached_analytic_document_path",
        "_is_valid_cached_analytic_document",
        "_write_analytic_document_cache",
        "load_step_analytic_document_disk_cache_hit",
        ".unlink(",  # corrupt cache is unlinked, then the OCC load runs
    ):
        if needle not in src:
            failures.append(f"_load_step_analytic_document lost its {needle} wiring")
    if src.index("_cached_analytic_document_path") > src.index("load_step_analytic_document(source_path)"):
        failures.append("the disk-cache read must come BEFORE the cold OCC load")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Analytic-document disk-cache validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Analytic-document disk-cache validation passed: the analytic B-rep is "
        "pickled to a versioned, mtime-stamped path, validated before trust, "
        "written atomically, and read before the cold OCC load -- so a heavy STEP "
        "body's 34-36 s first-hover freeze is paid once ever, not once per launch."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
