"""Display-free guard: a STEP face record is built from ITS OWN displayed triangles, and a hover
outline stays on the face it outlines (bugs/0847).

The user's flag_20260921_163121: a yellow shape floating above the om05a housing while hovering
``OPTICAL STEP S006/F005``. Measured, not guessed:

* the outline was centred on the face's plane but 46 mm deep across it -- a "planar outline"
  drawn perpendicular to the record's NORMAL, and that normal, (-0.206, 0.712, -0.671), belonged
  to no face at all;
* the prism assembly's display mesh carries 32 degenerate VTK_LINE cells (a clean() artifact),
  numbered BEFORE the polygons. The face-metadata builder took the triangles alone (61,698),
  saw 61,730 face tags, rejected them as mismatched, and indexed the triangles with STEP
  tessellation indices instead -- off by up to 32. 583 of 710 face records were built from the
  wrong triangles, normals off by up to 90 degrees;
* separately, the axisymmetric grouper (meant for vendor LENS patches) merged two -z and two +y
  planes into one "face"; its averaged normal drew an outline 29.8 mm outside the housing.

  A  the aligned reader: triangles and per-cell tags 1:1 across stray line cells (synthetic --
     runs anywhere), with the raw array one longer as the CONTROL
  H  the hover's stay-on-face test (pure)
  R  on the real prism assembly: every record's triangles carry its own face tags, every normal
     is its face's true normal, and no hover outline leaves the drawn body -- with CONTROLs
     showing the old indexing (583 wrong) and the unguarded planar outline (29.8 mm out)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

PRISM = Path("attachment/om05a_components/prism_assembly_chunk_armA.step")
SCENE = Path("attachment/om05a_folded.py")


def _synthetic_mesh():
    """Two faces -- face 0 in z=0, face 1 in x=0 -- with ONE degenerate triangle of face 0 turned
    into a line cell, as clean() does. VTK numbers the line cell first."""
    import pyvista as pv

    points = np.array([
        [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [2, 0, 0],           # face 0 (z = 0)
        [0, 0, 1], [0, 1, 1], [0, 1, 2], [0, 0, 2],                      # face 1 (x = 0)
    ], dtype=float)
    # displayed triangles: face 0's three survivors, then face 1's three
    polys = [(0, 1, 2), (0, 2, 3), (1, 4, 2), (0, 5, 6), (0, 6, 3), (5, 8, 7)]
    faces = np.hstack([[3, *tri] for tri in polys])
    mesh = pv.PolyData(points, faces=faces, lines=np.array([2, 1, 4]))
    # cell order: the line, then the six triangles -- tags follow VTK's numbering
    mesh.cell_data["kraken_step_face_index"] = np.array([0, 0, 0, 0, 1, 1, 1], dtype=int)
    return mesh, np.array([0, 0, 0, 1, 1, 1])


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.services.open3d_face_index_edges import triangle_array_and_cell_values
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- A: the aligned reader -----------------------------------------------------------------
    mesh, want = _synthetic_mesh()
    raw = np.asarray(mesh.cell_data["kraken_step_face_index"])
    triangles, tags = triangle_array_and_cell_values(mesh)
    ok(mesh.n_lines == 1 and raw.shape[0] == 7 and triangles.shape == (6, 3, 3) and np.array_equal(tags, want),
       f"A1: across a stray line cell the triangles and their face tags come back 1:1 "
       f"({triangles.shape[0]} triangles, tags {tags.tolist()}) -- the raw array has {raw.shape[0]}, "
       f"which the builder used to reject")
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    face0 = normals[tags == 0].sum(axis=0)
    ok(abs(abs(face0[2]) / np.linalg.norm(face0) - 1.0) < 1e-12,
       "A2: selecting face 0 by its aligned tag gives exactly the z=0 plane's normal")
    # Face 0 had FOUR tessellation triangles, [0, 1, 2, 3]; #2 was the degenerate one clean() turned
    # into the line cell, so the displayed triangles hold tessellation [0, 1, 3, 4, 5, 6]. The old
    # builder used [0, 1, 2, 3] as POSITIONS -- and position 3 is face 1's first triangle.
    shifted = normals[[0, 1, 2, 3]].sum(axis=0)
    ok(abs(shifted[2]) / np.linalg.norm(shifted) < 0.99,
       f"A3: CONTROL -- face 0's tessellation indices used as positions pull in face 1 and tilt the "
       f"normal to {np.round(shifted / np.linalg.norm(shifted), 3).tolist()}")

    # ---- H: the hover's stay-on-face test --------------------------------------------------------
    import pyvista as pv

    face_tris = triangles[tags == 0]
    inside = pv.PolyData(np.array([[0.1, 0.1, 0.0], [1.9, 0.1, 0.0], [0.9, 0.9, 0.0]]))
    outside = pv.PolyData(np.array([[0.1, 0.1, 0.0], [0.5, 0.5, 30.0]]))
    ok(Kraken3DInspector._outline_stays_on_triangles(inside, face_tris)
       and not Kraken3DInspector._outline_stays_on_triangles(outside, face_tris)
       and not Kraken3DInspector._outline_stays_on_triangles(None, face_tris),
       "H: an outline inside its face passes; one 30 mm off it, or none, does not")

    # ---- R: the real prism assembly --------------------------------------------------------------
    if not (PRISM.exists() and SCENE.exists()):
        notes.append("= R: SKIP -- the om05a prism assembly is not checked out here")
        return state["ok"], notes

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.open3d_face_index_edges import (
        face_indices_for_record,
        face_outline_from_face_indices,
        triangles_for_face_indices,
    )

    app = KrakenLayoutEditor()
    try:
        app.layout_files["s"] = SCENE
        app.load_layout_by_name("s")
        mesh = app._transformed_imported_step_mesh_for_label("optical")
        doc = app._load_step_analytic_document(PRISM)
        triangles, tags = triangle_array_and_cell_values(mesh)
        own_index = {str(face.face_id): i for i, face in enumerate(doc.outer_faces)}
        faces = (app._step_overlay_face_metadata("optical") or {}).get("faces") or []
        ok(int(mesh.n_lines) > 0 and triangles.shape[0] + int(mesh.n_lines) == int(mesh.n_cells),
           f"R0: the real mesh still carries the stray cells this guards against "
           f"({int(mesh.n_lines)} line cells, {triangles.shape[0]} triangles)")

        on_own = off_normal = checked = 0
        worst = 0.0
        for rec in faces:
            own = {own_index.get(str(s)) for s in (rec.get("source_face_ids") or [rec.get("face_id")])} - {None}
            idx = np.asarray([int(v) for v in rec.get("triangle_indices") or ()], dtype=int)
            if not own or idx.size == 0:
                continue
            checked += 1
            on_own += int(np.all(np.isin(tags[idx], list(own))))
            sel = triangles[np.isin(tags, list(own))]
            cross = np.cross(sel[:, 1] - sel[:, 0], sel[:, 2] - sel[:, 0]).sum(axis=0)
            if np.linalg.norm(cross) > 1e-9:
                angle = float(np.degrees(np.arccos(np.clip(abs(np.dot(cross / np.linalg.norm(cross), rec["normal"])), 0, 1))))
                worst = max(worst, angle)
                off_normal += int(angle > 1.0)
        ok(checked >= 700 and on_own == checked and off_normal == 0,
           f"R1: all {checked} face records are built from their OWN face's triangles "
           f"({on_own} of {checked}) and every normal is that face's true normal "
           f"({off_normal} off by > 1 deg, worst {worst:.2f} deg)")

        old_wrong = 0
        for face_index, face in enumerate(doc.outer_faces):
            idx = np.asarray([int(v) for v in face.triangle_indices if 0 <= int(v) < triangles.shape[0]], dtype=int)
            if idx.size and not np.all(tags[idx] == face_index):
                old_wrong += 1
        ok(old_wrong > 500,
           f"R2: CONTROL -- the old indexing (tessellation indices into the displayed triangles) "
           f"puts {old_wrong} faces on someone else's triangles")

        body = np.asarray(mesh.bounds, dtype=float)
        worst_out = worst_raw = 0.0
        fell_back = 0
        for rec in faces:
            if not str(rec.get("assignment_source", "")).startswith("step_analytic_axisymmetric_group"):
                continue
            idx = face_indices_for_record(mesh, rec)
            sel = triangles_for_face_indices(mesh, idx)
            if not sel.size:
                continue
            planar = Kraken3DInspector._planar_outline_from_triangles(sel, normal_world=rec.get("normal"))
            outline = planar
            if not Kraken3DInspector._outline_stays_on_triangles(planar, sel):
                outline = face_outline_from_face_indices(mesh, idx)
                fell_back += 1

            def _out(mesh_):
                if mesh_ is None or int(getattr(mesh_, "n_points", 0)) == 0:
                    return 0.0
                b = np.asarray(mesh_.bounds, dtype=float)
                return float(max(body[0] - b[0], b[1] - body[1], body[2] - b[2], b[3] - body[3],
                                 body[4] - b[4], b[5] - body[5], 0.0))

            worst_out = max(worst_out, _out(outline))
            worst_raw = max(worst_raw, _out(planar))
        ok(worst_out < 0.5 and fell_back >= 1,
           f"R3: no hover outline leaves the drawn body (worst {worst_out:.3f} mm); {fell_back} merged "
           f"non-coplanar group(s) draw their true edges instead of an averaged plane")
        ok(worst_raw > 20.0,
           f"R4: CONTROL -- without the stay-on-face test the averaged plane of a merged group "
           f"reaches {worst_raw:.1f} mm outside the housing")
    finally:
        app.destroy()
    return state["ok"], notes


def run() -> int:
    passed, notes = run_checks()
    print()
    for note in notes:
        print(("  " + note[2:]) if note.startswith("= ") else ("! " + note))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
