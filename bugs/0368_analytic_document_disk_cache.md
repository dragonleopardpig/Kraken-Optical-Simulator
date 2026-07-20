# 0368 — Disk-cache the analytic STEP document (kill the per-launch 34 s first-hover freeze)

**Report (user, 2026-07-20):** "it is live now, just now there is a long process nearly freeze the
UI." **Status:** SHIPPED 2026-07-20 (guard `validate_open3d_analytic_document_disk_cache`, penta
phase 313).

## Root cause

`load_step_analytic_document` runs a full pythonocc `STEPControl_Reader` + `BRepMesh_IncrementalMesh`
+ face enumeration on the UI thread. For the HR25xCXP camera (13,170 faces / 424 solids / 591k
triangles) that is **34-37 s**. The wrapper `layout_polyline_display._load_step_analytic_document`
cached the `StepAnalyticDocument` only in the in-memory `_external_cad_mesh_cache`, so the cold read
was paid ONCE PER SESSION — on the first hover/pick that resolves the camera's faces — recurring on
every fresh launch. The analytic MESH was disk-cached (`read_step_analytic_mesh_cache`); the DOCUMENT
(B-rep face descriptors + face-tagged tessellation) was not. Not a regression — pre-existing, noted
in `reference_open3d_perf_profiling` ("BS STEP import 11.5 s, LED 10 s still un-optimised").

## Fix

Pickle the `StepAnalyticDocument` to `attachment/cad_cache/<stem>_<mtime>_<size>.analytic_doc.v1.pkl`
(the base path already encodes mtime+size, so an edited STEP auto-invalidates; the document is pure
data — no OCC references, they live only in the transient `_RawFace`). `_load_step_analytic_document`
now: in-memory hit → **disk pickle** (validated, source-path re-stamped) → cold OCC load + atomic
pickle write. A corrupt/incompatible pickle is unlinked and falls through to the OCC load.

**Measured (camera):** cold 36.9 s → warm **0.09 s (401x)**, 49.6 MB pickle, byte-identical
round-trip, corrupt-cache fallback verified. First launch after a STEP edit still pays the cold read
once; every launch after is instant.

Follow-ups (unchanged): the analytic load is still on the UI thread the very first time (off-thread
warming deferred — pythonocc thread-safety); the Measure-E/E hover re-resolves drawn edges per move
on huge bodies (minor).
