"""Guard for bugs/0716 -- flag 074059: "imported LENS-10F238-V01.stp, it looks
different to attachment/freecad.png" + user directive "thoroughly fix STEP
importing bugs".

A vendor assembly routinely mixes SOLID breps with SHELL-BASED components
(10F238: 25 solids + 10 shell models -- a knurled focus ring and housing
parts). `load_step_analytic_document` enumerated faces per SOLID and dropped
every free shell whenever any solid existed, so whole housing parts vanished
from the mesh while FreeCAD (which draws all products) showed them.

Checks:
  A  source-pin: the loader collects free shells (solids' shells mapped via
     topexp, un-owned shells appended as face sources) and the face-id prefix
     covers the shells-only case.
  B  cache versions bumped (the same input file now produces MORE geometry --
     stale meshes/documents must regenerate).
  C  real file (skip-if-absent): the 10F238 document carries the shell faces
     -- >200 faces lie entirely in the x range the old loader left EMPTY.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0716_step_shell_import
"""

from __future__ import annotations

import inspect
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LENS_10F238 = PROJECT_ROOT / "attachment/temp/TH02A-49-1-R01-0902/LENS-10F238-V01.stp"


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services import step_analytic_geometry as sag

    src = inspect.getsource(sag.load_step_analytic_document)
    ok(
        "free_shells" in src
        and "TopAbs_SHELL" in src
        and "owned.Contains(shell_shape)" in src
        and "(solids + free_shells) if (solids or free_shells) else [shape]" in src,
        "A1: the loader appends free (un-owned) shells as face sources",
    )
    ok(
        "if (solids or free_shells)" in src,
        "A2: face ids keep their S-prefix for shells-only files (no id collisions)",
    )

    from KrakenOS.UI.services import layout_polyline_display as lpd

    ok(
        lpd._ANALYTIC_MESH_CACHE_VERSION == "v3"
        and lpd._ANALYTIC_DOCUMENT_CACHE_VERSION == "v2",
        f"B: analytic mesh/document cache versions bumped "
        f"({lpd._ANALYTIC_MESH_CACHE_VERSION}, {lpd._ANALYTIC_DOCUMENT_CACHE_VERSION})",
    )

    if LENS_10F238.exists():
        try:
            doc = sag.load_step_analytic_document(LENS_10F238)
            in_gap = 0
            for face in doc.faces:
                b = face.bbox
                if b[0] > -23.0 and b[3] < -14.5:
                    in_gap += 1
            ok(
                len(doc.faces) >= 1700 and in_gap > 200,
                f"C: the 10F238 document carries the shell components "
                f"({len(doc.faces)} faces, {in_gap} in the once-empty gap)",
            )
        except Exception as exc:
            notes.append(f"FAIL: C raised {type(exc).__name__}: {exc}")
    else:
        notes.append("SKIP: C: LENS-10F238-V01.stp is not in this checkout")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0716 STEP shell-import validation PASSED")
        return 0
    print("0716 STEP shell-import validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
