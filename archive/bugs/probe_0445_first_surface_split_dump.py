"""bugs/0445 diagnostic: ray-level dump of the plate-BS branched trace for BOTH coating faces.

The user chose the OBJECT-FACING diagonal as the default coating; flagging it collapsed
`_branch_traced_row_frames` to rows [1, 9] with a nonphysical ~38 mm lateral walk. This
probe dumps the raw NS_BRANCH_RESULTS (SURFACE / XYZ / R_LMN, point by point) for the
far-face canon and the object-facing config so the walk is explained at the ray level.

Run: DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0445_first_surface_split_dump.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI import optical_solid_metadata as osm

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def _diagonal_faces(app, row_index):
    """[(face_id, signed_dot, area), ...] for ~45-degree faces of the BS row."""
    _row, _path, metadata = app._optical_solid_face_metadata_for_row(int(row_index))
    out = []
    for face in list(metadata.get("faces", []) or []):
        if not isinstance(face, dict):
            continue
        normal = np.asarray(face.get("normal", (0, 0, 1)), dtype=float).reshape(-1)[:3]
        norm = float(np.linalg.norm(normal))
        if norm < 1e-9:
            continue
        signed = float(np.dot(normal / norm, (0.0, 0.0, 1.0)))
        angle = float(np.degrees(np.arccos(np.clip(abs(signed), 0, 1))))
        if abs(angle - 45.0) <= 20.0:
            out.append((str(face.get("face_id", "")), signed, float(face.get("area_mm2", 0) or 0)))
    return sorted(out, key=lambda t: -t[2])


def _flagged_splitter_faces(app, row_index):
    _row, _path, metadata = app._optical_solid_face_metadata_for_row(int(row_index))
    flagged = []
    for face in list(metadata.get("faces", []) or []):
        fn = str(face.get("function", "") or "")
        if "Splitter" in fn or "Beam" in fn or "Partial" in fn:
            flagged.append((str(face.get("face_id", "")), fn))
    return flagged


def _dump(system, label, max_pts=14):
    try:
        system.NsTrace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
    except Exception as exc:
        print(f"  {label}: NsTrace raised {type(exc).__name__}: {exc}")
        return
    results = list(getattr(system, "NS_BRANCH_RESULTS", []) or [])
    print(f"\n=== {label}: {len(results)} branch(es) ===")
    for r in results:
        surf = [int(s) for s in np.asarray(r.get("SURFACE", ()), dtype=int).ravel()]
        xyz = np.asarray(r.get("XYZ", np.zeros((0, 3))), dtype=float).reshape(-1, 3)
        rlmn = np.asarray(r.get("R_LMN", np.zeros((0, 3))), dtype=float).reshape(-1, 3)
        print(
            f"  branch={r.get('branch_id')} path={str(r.get('branch_path', ''))[:30]:30} "
            f"power={float(r.get('branch_power', 0)):.3f} "
            f"term={str(r.get('branch_termination_reason', ''))[:18]}"
        )
        n = min(len(xyz), max_pts)
        for k in range(n):
            s = surf[k] if k < len(surf) else "?"
            d = rlmn[k].round(4).tolist() if k < len(rlmn) else "?"
            print(f"      [{k:2}] S{s!s:>3} at {xyz[k].round(3).tolist()} dir {d}")
        if len(xyz) > n:
            print(f"      ... {len(xyz) - n} more points")


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        res = app.add_beam_splitter_to_led("plate")
        bs_row = int(res["row_index"]) if res and "row_index" in res else None
        if bs_row is None:
            bs_row = next(
                i
                for i in range(len(app.rows) - 1, -1, -1)
                if "Promoted" in str(getattr(app.rows[i], "name", ""))
            )
        print("BS row:", bs_row)
        print("diagonal faces (face_id, signed n.z, area):")
        for fid, signed, area in _diagonal_faces(app, bs_row):
            print(f"   {fid}  signed={signed:+.3f}  area={area:.0f}")
        print("flagged splitter faces (default add):", _flagged_splitter_faces(app, bs_row))

        sys_a = app.build_system(require_solids=True, force_rebuild=True)
        _dump(sys_a, "CONFIG A: default flag (away-facing canon)")

        # Re-flag onto the OBJECT-FACING diagonal; the old face back to Uncoated.
        diag = _diagonal_faces(app, bs_row)
        object_facing = next((fid for fid, signed, _a in diag if signed < 0), None)
        away_facing = next((fid for fid, signed, _a in diag if signed > 0), None)
        print("\nre-flag:", away_facing, "-> Uncoated;", object_facing, "-> Splitter")
        app.assign_optical_solid_face_function(
            bs_row, away_facing, osm.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_UNCOATED
        )
        app.assign_optical_solid_face_function(
            bs_row, object_facing, osm.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_SPLITTER
        )
        print("flagged splitter faces (object-facing):", _flagged_splitter_faces(app, bs_row))

        sys_b = app.build_system(require_solids=True, force_rebuild=True)
        _dump(sys_b, "CONFIG B: object-facing coating (the 0445 breakage)")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
