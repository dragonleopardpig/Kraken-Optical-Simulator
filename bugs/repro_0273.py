"""bugs/0273 repro: an illumination-marked face ABSORBS imaging rays so the beam-splitter
reflection branch drops its phantom detector/image plane (flag_20260709_075456_691, part 2).

Verifies the new link the fix adds -- a face carrying a face-bound illumination marker becomes a
force_absorption face in the IMAGING trace -- and that the isolated EMISSION trace still floods out
of the solid (bugs/0272 not regressed) because the emission pass suppresses the absorption.

Run: .devenv/state/venv/bin/python bugs/repro_0273.py
"""
from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")

import numpy as np

from KrakenOS.UI import layout_editor as le
from KrakenOS.UI.layout_editor import (
    KrakenLayoutEditor,
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    SurfaceRow,
    optical_solid_face_world_records,
)
from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP


def main() -> int:
    if not PRISM_42779_STEP.exists():
        print("SKIP: PRISM_42779_STEP fixture not checked out")
        return 0

    le.CAD_CACHE_DIR = Path("/tmp/kraken-0273-cache/cad")
    le.CAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    app = KrakenLayoutEditor(headless=True)
    fails: list[str] = []
    try:
        app.imported_optical_step_path = PRISM_42779_STEP
        app.optical_step_rotation_x_deg = 90.0
        app.optical_step_rotation_z_deg = 90.0
        app.select_step_component("optical")
        promoted = app.promote_imported_step_to_optical_solid_row(
            "optical", insert_at=1, open_face_editor=False, clear_overlay=True
        )
        assert promoted is not None, "promotion failed"
        row_index = int(promoted["row_index"])

        _row, _path, metadata = app._optical_solid_face_metadata_for_row(row_index)
        temp_row = SurfaceRow(**asdict(app.rows[row_index]))
        temp_row.advanced = dict(temp_row.advanced or {})
        temp_row.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata
        faces = optical_solid_face_world_records(temp_row, app._stl_row_z_station(row_index), assigned_only=False)
        assert faces, "no faces"
        for f in faces[:3]:
            app.assign_optical_solid_face_function(row_index, str(f.get("face_id", "") or ""), "Full Reflecting", direct_context=True)
        illum_face_id = str(faces[-1].get("face_id", "") or "").strip()
        other_face_id = str(faces[0].get("face_id", "") or "").strip()
        app.assign_optical_solid_face_function(row_index, illum_face_id, "Uncoated", direct_context=True)
        assert app.create_illumination_source_at_face(row_index, face_id=illum_face_id, aim="inward"), "mark failed"

        # (1) build-side resolver stashes the marked face on the row spec
        specs = app._serializable_row_specs()
        block = specs[row_index].get("illumination_block_face_ids")
        if not block or illum_face_id not in block:
            fails.append(f"(1) row spec missing illumination_block_face_ids: {block!r} (want {illum_face_id})")

        system = app.build_system()

        # (2) build stashes the surface attribute
        surf = system.SDT[row_index]
        illum_block = getattr(surf, "OpticalSolidFaceIlluminationBlock", None)
        if not illum_block or illum_face_id not in illum_block:
            fails.append(f"(2) surface.OpticalSolidFaceIlluminationBlock missing face: {illum_block!r}")

        # (3) __OpticalSolidFaceInteraction forces absorption on the MARKED face
        interact = system._system__OpticalSolidFaceInteraction
        marked = next(f for f in faces if str(f.get("face_id", "")).strip() == illum_face_id)
        pt = np.asarray(marked["centroid_world"], dtype=float)
        nrm = np.asarray(marked.get("normal_world", (0.0, 0.0, 1.0)), dtype=float)
        ov = interact(row_index, pt, nrm, {"face_id": illum_face_id})
        if not (isinstance(ov, dict) and ov.get("force_absorption") is True):
            fails.append(f"(3) marked face did not force_absorption: {ov!r}")

        # (3b) a NON-marked face is NOT absorbed by this hook (it is Full Reflecting here)
        other = next(f for f in faces if str(f.get("face_id", "")).strip() == other_face_id)
        ov_other = interact(row_index, np.asarray(other["centroid_world"], dtype=float),
                            np.asarray(other.get("normal_world", (0, 0, 1)), dtype=float), {"face_id": other_face_id})
        # (only the illumination hook is under test; a reflecting face legitimately sets force_reflection)
        if isinstance(ov_other, dict) and ov_other.get("force_absorption") is True and other_face_id not in illum_block:
            fails.append(f"(3b) an unmarked face wrongly forced absorption: {ov_other!r}")

        # (4) emission suppression: with the system flag set, the marked face does NOT absorb
        system._suppress_illumination_face_absorption = True
        ov_sup = interact(row_index, pt, nrm, {"face_id": illum_face_id})
        if isinstance(ov_sup, dict) and ov_sup.get("force_absorption") is True:
            fails.append(f"(4) suppression flag failed -- marked face still absorbed during emission: {ov_sup!r}")
        system._suppress_illumination_face_absorption = False

        # (5) the isolated EMISSION overlay STILL floods OUT of the solid (bugs/0272 intact)
        spec = app.illumination_marker_rays_overlay_spec(system, None)
        if not spec or int(spec.get("drawn", 0)) < 1:
            fails.append("(5) emission overlay produced no drawable rays -- self-absorbed at launch? (0272 regression)")
        else:
            face_pts = np.asarray([f["centroid_world"] for f in faces], dtype=float)
            solid_diag = float(np.linalg.norm(face_pts.max(axis=0) - face_pts.min(axis=0)))
            drawn_pts = np.asarray(spec.get("points"), dtype=float)
            drawn_diag = float(np.linalg.norm(drawn_pts.max(axis=0) - drawn_pts.min(axis=0))) if drawn_pts.size else 0.0
            if drawn_diag <= solid_diag + 20.0:
                fails.append(f"(5) emission did not exit the solid: drawn {drawn_diag:.1f} vs solid {solid_diag:.1f} (0272 regression)")
            else:
                print(f"OK  (5) emission exits: drawn span {drawn_diag:.0f} mm >> solid {solid_diag:.0f} mm, {spec['drawn']} rays")
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if fails:
        print("\n".join("FAIL " + m for m in fails))
        print("[FAIL] bugs/0273 illumination-face absorb hook")
        return 1
    print("[PASS] illumination-marked face forces absorption (imaging); suppressed for emission; 0272 intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
