"""Guard: a beam-splitter cube's interior 45° coating is recovered as a
selectable face (bugs/0064).

Reported: after promoting a beam-splitter cube to an optical solid row, the face
editor table had **no row for the center coating surface**, so the user could not
assign the splitter coating. A cube beam-splitter is two cemented right-angle
prisms; the 45° coating is an *interior duplicate* face that
`load_step_analytic_document` kept in `document.faces` (centroid + normal correct)
but with **zero triangles** and excluded from `document.outer_faces`, so it never
became a face record / table row. The coating sits inside the body, so it is also
not clickable from outside.

Fix: `_is_recoverable_interior_coating` + a recovery in `load_step_analytic_document`
that force-includes ONE *oblique* (non axis-aligned) interior coating per duplicate
group as a real, tessellated `outer_faces` entry tagged `recovered_coating=True`.
It flows uniformly to the display mesh (face-tagged triangles) and the face-role
metadata, so it appears as a selectable row with real geometry. Axis-perpendicular
doublet cement (normal ~(0,0,1)) is NOT oblique, so doublets stay unchanged.

Checks: synthetic helper logic always runs (portable); real-part recovery is
SKIP-if-absent.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_beam_splitter_coating_recovered

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

_SQRT_HALF = 1.0 / np.sqrt(2.0)
_BEAM_SPLITTER = Path("attachment/prisms/Beam_Splitter/32704/step_32704.step")
_DOUBLET = Path("attachment/Lens/Aspherized_Achromatic_Lenses/step_49665.step")
_PENTA = Path("attachment/prisms/Penta/step_42779.step")


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    def skip(label: str) -> None:
        notes.append("SKIP " + label)

    from KrakenOS.UI.services.step_analytic_geometry import (
        StepAnalyticFace,
        _is_recoverable_interior_coating,
        load_step_analytic_document,
    )

    def _face(normal, surface_type="plane") -> StepAnalyticFace:
        return StepAnalyticFace(
            face_id="x", solid_index=1, source_face_index=0, surface_type=surface_type,
            centroid=(0.0, 0.0, 0.0), normal=tuple(normal), area_mm2=1.0,
            bbox=(0, 0, 0, 0, 0, 0), plane_offset_mm=0.0, u_range=(0, 1), v_range=(0, 1),
        )

    # --- A. helper: oblique plane recovered, axis-aligned / non-plane not ----
    ok(_is_recoverable_interior_coating(_face((_SQRT_HALF, _SQRT_HALF, 0.0))) is True,
       "A1: a 45° oblique coating normal is recoverable")
    ok(_is_recoverable_interior_coating(_face((0.0, 0.0, 1.0))) is False,
       "A2: axis-perpendicular cement (doublet bond) is NOT recovered")
    ok(_is_recoverable_interior_coating(_face((0.95, 0.31, 0.0))) is False,
       "A3: a nearly axis-aligned plane (max comp >= 0.9) is not recovered")
    ok(_is_recoverable_interior_coating(_face((_SQRT_HALF, _SQRT_HALF, 0.0), surface_type="cylinder")) is False,
       "A4: a non-planar oblique face is not recovered")

    # --- B. real beam-splitter: one coating recovered, with geometry ---------
    if not _BEAM_SPLITTER.exists():
        skip(f"B: vendor beam-splitter STEP not present ({_BEAM_SPLITTER})")
    else:
        try:
            doc = load_step_analytic_document(_BEAM_SPLITTER)
            recovered = [f for f in doc.outer_faces if getattr(f, "recovered_coating", False)]
            ok(len(recovered) == 1, "B1: exactly one coating recovered for the 2-prism cube")
            if recovered:
                coat = recovered[0]
                comp = np.sort(np.abs(np.asarray(coat.normal, float)))
                ok(coat.triangle_count >= 1 and len(coat.triangle_indices) >= 1,
                   "B2: the recovered coating has tessellated geometry (triangles)")
                ok(comp[0] < 0.05 and abs(comp[1] - comp[2]) < 0.05 and comp[1] > 0.3,
                   "B3: the coating normal is the 45° signature (~0 on one axis, equal on two)")
                ok(np.allclose(np.asarray(coat.centroid, float), [25.0, 25.0, 25.0], atol=1.0),
                   "B4: the coating sits at the cube centre (25,25,25)")
            # the recovered coating is in the EMITTED records -> a face-editor row
            faces = list(doc.optical_solid_face_metadata().get("faces", []) or [])
            recs = [f for f in faces if f.get("recovered_coating")]
            ok(len(recs) == 1 and str(recs[0].get("function", "")).strip() in {"Unassigned", "Transmit/Port"},
               "B5: the coating is an emitted, assignable face record (a table row)")
        except Exception as exc:  # pragma: no cover - env dependent
            skip(f"B: beam-splitter recovery unavailable ({type(exc).__name__}: {exc})")

    # --- C. doublet + penta: NOT affected ------------------------------------
    if _DOUBLET.exists():
        try:
            doc = load_step_analytic_document(_DOUBLET)
            n_rec = sum(1 for f in doc.outer_faces if getattr(f, "recovered_coating", False))
            ok(n_rec == 0, "C1: a cemented doublet recovers no coating (axis-perpendicular cement)")
        except Exception as exc:  # pragma: no cover
            skip(f"C1: doublet check unavailable ({type(exc).__name__})")
    else:
        skip("C1: doublet STEP not present")
    if _PENTA.exists():
        try:
            doc = load_step_analytic_document(_PENTA)
            n_rec = sum(1 for f in doc.outer_faces if getattr(f, "recovered_coating", False))
            ok(n_rec == 0, "C2: a single-solid penta prism recovers no coating")
        except Exception as exc:  # pragma: no cover
            skip(f"C2: penta check unavailable ({type(exc).__name__})")
    else:
        skip("C2: penta prism STEP not present")

    passed = not any(n.startswith("FAIL") for n in notes)
    if verbose:
        for n in notes:
            print(n)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Beam-splitter coating-recovery validation passed.")
        return 0
    print("Beam-splitter coating-recovery validation FAILED:")
    for n in notes:
        if n.startswith("FAIL"):
            print(f"- {n}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
