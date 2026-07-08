"""Display-free guard for the "Diffuse / Scatter Object" promoted-CAD-face role (bugs/0271).

The non-sequential diffuse-scatter engine (Lambertian / Oren-Nayar / Cosine-Lobe / BSDF) existed only at the
row/surface level ("Diffuse Object" surface); an in-code tooltip said it was "not wired on imported CAD faces
yet". This role wires it to a promoted-solid FACE: marking a face "Diffuse / Scatter Object" (a REAL internal
function, unlike the illumination sentinels) resolves at BUILD into `surface.OpticalSolidFaceDiffuseScatter`
(keyed by face_id), which `KrakenSys.__OpticalSolidFaceInteraction` carries onto the face override and the
non-seq scatter loop spawns Lambertian/BRDF child rays off -- exactly like a Diffuse Object surface.

Five display-free parts:

* METADATA -- "Diffuse Scatter" is a real internal function value + UI label "Diffuse / Scatter Object" in the
  dropdown/combobox alias with a two-way UI<->internal mapping (so the dropdown selects it via the NORMAL apply
  path, no sentinel interception).
* RESOLVER -- `resolve_optical_solid_face_diffuse_scatter_for_face`: a scatter face -> normalized settings
  (default Lambertian when unauthored); a non-scatter face -> None (trace unchanged, additive contract).
* BUILD (real promoted-prism STEP fixture; SKIPs without it) -- marking a face scatter lands its normalized
  settings on `surface.OpticalSolidFaceDiffuseScatter[face_id]`.
* PHYSICS (STEP) -- a ray aimed at the scatter face spawns exactly `sample_count` `/scatter` branches, each with
  power == reflectance/sample_count.
* ADDITIVE (STEP) -- an Uncoated (non-scatter) face spawns NO scatter branches.
"""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path

import numpy as np

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")


def _check_metadata(failures: list[str]) -> None:
    from KrakenOS.UI import optical_solid_metadata as M
    from KrakenOS.UI.services import optical_solid_geometry as G

    ui = M.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_SCATTER
    internal = M.OPTICAL_SOLID_FACE_FUNCTION_SCATTER
    if internal not in M.OPTICAL_SOLID_FACE_FUNCTION_VALUES:
        failures.append("METADATA: 'Diffuse Scatter' is not a real internal function value")
    if ui not in M.OPTICAL_SOLID_FACE_FUNCTION_UI_VALUES or ui not in G.OPTICAL_SOLID_FACE_FUNCTION_VALUES:
        failures.append("METADATA: 'Diffuse / Scatter Object' is not in the dropdown / combobox alias")
    if M.normalize_optical_solid_face_function(ui) != internal:
        failures.append("METADATA: the scatter UI label does not map to the 'Diffuse Scatter' internal value")
    if M.optical_solid_face_function_display(internal) != ui:
        failures.append("METADATA: 'Diffuse Scatter' does not display as 'Diffuse / Scatter Object'")


def _check_resolver(failures: list[str]) -> None:
    from KrakenOS.UI.layout_editor import resolve_optical_solid_face_diffuse_scatter_for_face as resolve

    s = resolve({"function": "Diffuse Scatter"})
    if not isinstance(s, dict) or s.get("model") != "Lambertian" or int(s.get("sample_count", 0)) <= 0:
        failures.append(f"RESOLVER: a scatter face did not resolve to default Lambertian settings ({s})")
    if float(s.get("reflectance", 0.0)) <= 0.0:
        failures.append("RESOLVER: default scatter reflectance must be > 0")
    if resolve({"function": "Mirror"}) is not None:
        failures.append("RESOLVER: a non-scatter face must resolve to None (additive contract)")
    if resolve({"function": "Diffuse Scatter", "diffuse_scatter": {"reflectance": 0.0}}) is not None:
        failures.append("RESOLVER: reflectance 0 must resolve to None (matches the engine gate)")
    custom = resolve({"function": "Diffuse Scatter", "diffuse_scatter": {"model": "Oren-Nayar", "sample_count": 5, "reflectance": 0.6}})
    if not custom or custom.get("model") != "Oren-Nayar" or int(custom.get("sample_count")) != 5:
        failures.append(f"RESOLVER: authored scatter params were not honoured ({custom})")


def _promote_prism(app, le):
    from KrakenOS.UI.layout_editor import OPTICAL_SOLID_FACES_ADVANCED_ATTR, SurfaceRow, optical_solid_face_world_records
    from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP

    le.CAD_CACHE_DIR = Path("/tmp/kraken-open3d-face-scatter-cache/cad")
    le.CAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    app.imported_optical_step_path = PRISM_42779_STEP
    app.optical_step_rotation_x_deg = 90.0
    app.optical_step_rotation_z_deg = 90.0
    app.select_step_component("optical")
    promoted = app.promote_imported_step_to_optical_solid_row("optical", insert_at=1, open_face_editor=False, clear_overlay=True)
    row = int(promoted["row_index"])
    _r, _p, md = app._optical_solid_face_metadata_for_row(row)
    tr = SurfaceRow(**asdict(app.rows[row]))
    tr.advanced = dict(tr.advanced or {})
    tr.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = md
    faces = optical_solid_face_world_records(tr, app._stl_row_z_station(row), assigned_only=False)
    return row, faces


def _scatter_branches(app, system, face):
    import KrakenOS as Kos

    c = np.asarray(face["centroid_world"], dtype=float)
    nrm = np.asarray(face["normal_world"], dtype=float)
    nrm = nrm / (np.linalg.norm(nrm) or 1.0)
    origin = c + nrm * 80.0
    d = -nrm
    rays = Kos.raykeeper(system)
    restore = app._apply_nonseq_trace_settings(system)
    try:
        arr = lambda v: np.array([float(v)])
        Kos.NsTraceLoop(arr(origin[0]), arr(origin[1]), arr(origin[2]), arr(d[0]), arr(d[1]), arr(d[2]), 0.55, rays)
    finally:
        restore()
    paths = [str(np.asarray(p, dtype=object).ravel()[0]) for p in getattr(rays, "BRANCH_PATH", [])]
    scatter = [p for p in paths if "/scatter" in p]
    powers = [float(np.asarray(pw, dtype=float).ravel()[0]) for pw in getattr(rays, "BRANCH_POWER", [])]
    return scatter, powers


def _check_build_and_physics(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI import layout_editor as le
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP

    if not PRISM_42779_STEP.exists():
        notes.append("SKIP build/physics: PRISM_42779_STEP fixture not checked out")
        return

    app = KrakenLayoutEditor(headless=True)
    try:
        row, faces = _promote_prism(app, le)
        if not faces:
            failures.append("BUILD: promoted solid exposed no faces")
            return
        face = max(faces, key=lambda f: float(f.get("area_mm2", 0.0) or 0.0))
        fid = str(face["face_id"])
        app.assign_optical_solid_face_function(row, fid, "Diffuse / Scatter Object", direct_context=True)

        system = app.build_system()
        mapped = None
        for j in range(len(getattr(system, "SDT", []) or [])):
            m = getattr(system.SDT[j], "OpticalSolidFaceDiffuseScatter", None)
            if isinstance(m, dict) and fid in m:
                mapped = m[fid]
                break
        if not isinstance(mapped, dict) or int(mapped.get("sample_count", 0)) <= 0:
            failures.append("BUILD: marking a face scatter did not land surface.OpticalSolidFaceDiffuseScatter")
            return

        scatter, powers = _scatter_branches(app, system, face)
        want = int(mapped["sample_count"])
        if len(scatter) != want:
            failures.append(f"PHYSICS: expected {want} /scatter branches off the marked face, got {len(scatter)}")
        expected_power = float(mapped["reflectance"]) / float(want)
        if not powers or not all(abs(p - expected_power) < 1e-6 for p in powers):
            failures.append(f"PHYSICS: scatter branch powers should be {expected_power:.5f}, got {powers[:3]}")

        # ADDITIVE: an Uncoated face spawns NO scatter branches.
        app.assign_optical_solid_face_function(row, fid, "Uncoated", direct_context=True)
        system2 = app.build_system()
        if any(getattr(system2.SDT[j], "OpticalSolidFaceDiffuseScatter", None) for j in range(len(getattr(system2, "SDT", []) or []))):
            failures.append("ADDITIVE: an Uncoated face still carries a scatter map")
        s2, _ = _scatter_branches(app, system2, face)
        if s2:
            failures.append(f"ADDITIVE: an Uncoated face still spawned {len(s2)} scatter branches")

        if not failures:
            notes.append(f"build/physics OK: face {fid} scatters {want} Lambertian branches (power {expected_power:.4f}); Uncoated -> none")
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_metadata(failures)
    _check_resolver(failures)
    _check_build_and_physics(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "NOTE ") + message)
    if not passed:
        print("[FAIL] Diffuse / Scatter Object face role")
        return 1
    print("[PASS] a promoted CAD face marked Diffuse / Scatter Object scatters like a Diffuse Object surface")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
