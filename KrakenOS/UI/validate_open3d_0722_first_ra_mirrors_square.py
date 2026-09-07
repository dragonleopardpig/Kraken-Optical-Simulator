"""Guard for bugs/0722 -- om05a: the first RA mirrors fold EXACTLY 90 degrees.

User: "the ray should bend 90 degree for whatever mirror or BS in this design, so there
shouldn't be 45.29 degree." bugs/0695_build_vendor_prisms.py read the first RA mirror off
the vendor section as 9.8 x 9.9 legs (hypotenuse 45.29 deg); the follower walk reflects
its running frame about that face, so the whole imaging chain dipped 0.58 deg (1.09 mm at
the sensor: the design axis landed off-centre and the two split-field strips were not
mirror images).

Checks (display-free):
  A  the builder's first-RA-mirror profile has EQUAL legs (a right isosceles triangle).
  B  in the om05a 80 mm scene (Filen-synced; skipped when absent) both first RA mirror
     rows carry a Mirror face whose normal is 45.00 deg, and the physics mesh they trace
     (Solid_3d_stl) has that same square hypotenuse -- face record and mesh agree.
  C  the scene's lens chain is seated on the fold prism's symmetry plane: the first
     follower row's frame-desp was re-derived (bugs/0722 --seat), so the seat is not the
     old dip-compensating value.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0722_first_ra_mirrors_square
"""

from __future__ import annotations

import ast
import math
import re
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILDER = PROJECT_ROOT / "bugs/0695_build_vendor_prisms.py"
SCENE = PROJECT_ROOT / "attachment/om05a_folded_80mm.py"
FIRST_RA_ROWS = ("First RA mirror A", "First RA mirror B")


def _scene_rows(path: Path) -> list[dict]:
    src = path.read_text(encoding="utf-8")
    rows, pos = [], 0
    while True:
        i = src.find("surfaces.append({", pos)
        if i < 0:
            break
        j = src.find("})\n", i) + 2
        rows.append(ast.literal_eval(src[i + len("surfaces.append(") : j - 1]))
        pos = j
    return rows


def _hyp_face(faces: list[dict]) -> dict | None:
    best = None
    for rec in faces:
        n = np.asarray(rec.get("normal") or (0, 0, 0), dtype=float)
        if abs(n[0]) < 0.05 and abs(abs(n[1]) - abs(n[2])) < 0.05 and float(rec.get("area_mm2") or 0) > 100:
            best = rec
    return best


def _deg(n) -> float:
    n = np.asarray(n, dtype=float)
    return math.degrees(math.atan2(abs(float(n[1])), abs(float(n[2]))))


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    # ---- A: the builder profile --------------------------------------------------------
    src = BUILDER.read_text(encoding="utf-8") if BUILDER.exists() else ""
    m = re.search(r"^\s*ra = \[(.*)\]\s*$", src, re.M)
    legs = None
    if m:
        pts = re.findall(r"scene_pt\(([-\d.]+),\s*([-\d.]+)\)", m.group(1))
        if len(pts) == 3:
            xs = [float(a) for a, _ in pts]
            ys = [float(b) for _, b in pts]
            legs = (max(xs) - min(xs), max(ys) - min(ys))
    ok(
        legs is not None and abs(legs[0] - legs[1]) < 1e-9,
        f"A1: bugs/0695_build_vendor_prisms.py first-RA-mirror profile has equal legs (legs={legs})",
    )

    # ---- B/C: the scene ----------------------------------------------------------------
    if not SCENE.exists():
        notes.append("SKIP: the om05a 80 mm scene is not on this machine (Filen-synced)")
    else:
        try:
            import trimesh
        except Exception:  # pragma: no cover - environment
            trimesh = None
        rows = _scene_rows(SCENE)
        by_name = {str(r.get("name")): r for r in rows}
        for name in FIRST_RA_ROWS:
            row = by_name.get(name)
            adv = (row or {}).get("advanced") or {}
            faces = ((adv.get("OpticalSolidFaces") or {}).get("faces")) or []
            hyp = _hyp_face(faces)
            role_ok = hyp is not None and str(hyp.get("role")) == "Mirror"
            ang = _deg(hyp.get("normal")) if hyp else float("nan")
            ok(
                role_ok and abs(ang - 45.0) < 0.01,
                f"B1 {name}: Mirror face normal at {ang:.3f} deg (record {np.round(np.asarray(hyp.get('normal'), float), 5).tolist() if hyp else None})",
            )
            stl = adv.get("Solid_3d_stl")
            stl_path = Path(stl) if stl and Path(stl).is_absolute() else PROJECT_ROOT / str(stl)
            if trimesh is None or not stl_path.exists():
                notes.append(f"SKIP: {name}: mesh {stl_path.name} unavailable")
                continue
            mesh = trimesh.load(str(stl_path), force="mesh")
            fn = np.asarray(mesh.face_normals, dtype=float)
            diag = [n for n in fn if abs(n[0]) < 1e-6 and abs(abs(n[1]) - abs(n[2])) < 0.05]
            angs = [_deg(n) for n in diag]
            ok(
                len(diag) == 2 and all(abs(a - 45.0) < 1e-6 for a in angs),
                f"B2 {name}: the physics mesh ({stl_path.name}) hypotenuse is exactly 45 deg ({[round(a, 4) for a in angs]})",
            )
        seat = by_name.get("Front Optical Vertex Datum") or {}
        desp = (float(seat.get("desp_x") or 0), float(seat.get("desp_y") or 0), float(seat.get("desp_z") or 0))
        ok(
            abs(desp[0] + 6.08) > 0.5,
            f"C1: the first follower row's frame-desp was re-seated after squaring (desp={np.round(desp, 4).tolist()}; "
            f"the pre-0722 seat -6.08 embedded the 0.58 deg dip)",
        )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0722 first-RA-mirrors-square validation PASSED")
        return 0
    print("0722 first-RA-mirrors-square validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
