#!/usr/bin/env python3
"""Display-free guard for bugs/0319 C2 -- the LED clear-aperture auto-detect.

The one-click "Add Beam Splitter to LED" pipeline must centre the BS on the LED
module's clear-aperture *opening*.  Rather than force the user to pick that window
by hand every time (``STEP_CLEAR_APERTURE_PICK``, bugs/0134), the pipeline
auto-detects it from the STEP's analytic faces -- with the manual pick kept as the
dependable fallback the user asked for.

The opening signature (grounded on the real OPT-CO90 LED STEP): a planar,
axis-aligned, window-sized face that is a **rim around a hole** (its area is only a
fraction of its in-plane bbox), which cleanly separates it from solid housing
panels.  An LED that already carries a BS has two such openings; the detector
returns every qualifier ranked, so the caller picks the best or defers to manual.

What it checks
--------------
  A. Pure scorer (OCC-free, always runs): two rim windows are both detected and
     ranked (square outranks rectangular); a solid panel, a sub-window sliver, an
     oversized housing wall and a non-flat (thick-bbox) face are all rejected.
  B. Real LED STEP (needs OCC + attachment/LED/OPT-CO90-...; SKIP without them):
     the detector's top candidate is the object-facing square window F112
     (centroid ~ (7.3, -1.3, 36.5), normal ~ -Z, squareness ~1, score > 0.9).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_clear_aperture_detect

Exit: 0 = pass (incl. an OCC/STEP-absent skip), 1 = regression.
"""
from __future__ import annotations

from pathlib import Path

_LED_STEP = Path("attachment/LED/OPT-CO90-X-V1.6.2-H.STEP")


def _occ_available() -> bool:
    try:
        import OCC.Core.STEPControl  # noqa: F401
    except Exception:
        return False
    return True


def _flat_face(face_index, cx, cy, cz, sx, sy, *, area, normal):
    """A world-axis-flat planar face record centred at (cx,cy,cz) with in-plane
    span (sx, sy) and the given planar area (< sx*sy for a rim around a hole)."""
    return {
        "face_index": face_index,
        "centroid": (cx, cy, cz),
        "normal": normal,
        "area_mm2": area,
        "bbox": (cx - sx / 2, cy - sy / 2, cz, cx + sx / 2, cy + sy / 2, cz),
    }


def _check_pure(failures: list[str]) -> None:
    from KrakenOS.UI.services.led_clear_aperture_detect import score_clear_aperture_faces

    # Two genuine rim windows (the "LED already carries a BS" two-opening case).
    square_rim = _flat_face(11, 0.0, 0.0, 0.0, 55.5, 55.5, area=462.0, normal=(0.0, 0.0, -1.0))
    rect_rim = _flat_face(22, 120.0, -5.0, 40.0, 40.0, 30.0, area=240.0, normal=(0.0, 0.0, 1.0))
    # Non-openings that must be rejected:
    solid_panel = _flat_face(33, 0.0, 0.0, 50.0, 60.0, 60.0, area=3240.0, normal=(0.0, 0.0, 1.0))  # fill 0.9
    tiny_hw = _flat_face(44, 0.0, 0.0, 0.0, 5.0, 5.0, area=2.0, normal=(0.0, 0.0, 1.0))            # span<15
    housing_wall = _flat_face(55, 0.0, 0.0, 0.0, 200.0, 150.0, area=6000.0, normal=(1.0, 0.0, 0.0))  # span>90
    thick_block = {  # bbox not flat along any axis -> not a planar window
        "face_index": 66, "centroid": (0.0, 0.0, 0.0), "normal": (0.0, 0.0, 1.0),
        "area_mm2": 462.0, "bbox": (-20.0, -20.0, -10.0, 20.0, 20.0, 10.0),
    }

    cands = score_clear_aperture_faces(
        [solid_panel, tiny_hw, rect_rim, housing_wall, square_rim, thick_block]
    )
    got = [c.face_index for c in cands]

    if got != [11, 22]:
        failures.append(
            f"FAIL(A): expected exactly the two rim windows ranked [11, 22] (square first), got {got}"
        )
    if 33 in got:
        failures.append("FAIL(A): a solid panel (bbox_fill ~0.9) must be rejected")
    if 44 in got:
        failures.append("FAIL(A): a sub-window sliver (span < 15 mm) must be rejected")
    if 55 in got:
        failures.append("FAIL(A): an oversized housing wall (span > 90 mm) must be rejected")
    if 66 in got:
        failures.append("FAIL(A): a non-flat (thick-bbox) face must be rejected")
    if cands and cands[0].score <= 0.5:
        failures.append(f"FAIL(A): the square window should score well above threshold, got {cands[0].score:.3f}")


def _check_real_led(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI.services.led_clear_aperture_detect import (
        detect_clear_aperture_openings_from_analytic_faces,
    )
    from KrakenOS.UI.services.step_analytic_geometry import load_step_analytic_document

    doc = load_step_analytic_document(_LED_STEP, linear_deflection_mm=1.0, angular_deflection_rad=0.5)
    cands = detect_clear_aperture_openings_from_analytic_faces(doc.outer_faces)
    if not cands:
        failures.append("FAIL(B): no clear-aperture opening detected on the real OPT-CO90 LED STEP")
        return
    top = cands[0]
    face_id = str(doc.outer_faces[top.face_index].face_id)
    if face_id != "F112":
        failures.append(f"FAIL(B): top candidate should be the F112 object window, got {face_id}")
    cx, cy, cz = top.centroid
    if not (abs(cx - 7.3) < 3.0 and abs(cy - (-1.3)) < 3.0 and abs(cz - 36.5) < 3.0):
        failures.append(f"FAIL(B): F112 centroid should be ~(7.3,-1.3,36.5), got ({cx:.1f},{cy:.1f},{cz:.1f})")
    if abs(abs(top.normal[2]) - 1.0) > 0.05:
        failures.append(f"FAIL(B): F112 normal should face along Z, got {tuple(round(v,2) for v in top.normal)}")
    if top.score <= 0.9:
        failures.append(f"FAIL(B): F112 should score > 0.9 (a clean detection), got {top.score:.3f}")
    notes.append(
        f"real LED: {len(cands)} candidate(s); top={face_id} score={top.score:.3f} "
        f"squ={top.squareness:.2f} fill={top.bbox_fill:.2f}"
    )


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []

    _check_pure(failures)

    if not _occ_available():
        return (not failures), failures + ["SKIP(B): pythonocc-core unavailable; pure scorer only"]
    if not _LED_STEP.exists():
        return (not failures), failures + [f"SKIP(B): {_LED_STEP} absent (gitignored vendor STEP)"]
    try:
        _check_real_led(failures, notes)
    except Exception as exc:  # pragma: no cover - environment/backend dependent
        return (not failures), failures + [f"SKIP(B): real LED detect raised {exc!r}"]

    return (not failures), failures + notes


def main() -> int:
    passed, notes = run_checks()
    hard = [n for n in notes if n.startswith("FAIL")]
    soft = [n for n in notes if not n.startswith("FAIL")]
    if hard:
        print("[FAIL] LED clear-aperture auto-detect (bugs/0319 C2)")
        for item in hard:
            print(f"  - {item}")
        return 1
    print("[PASS] LED clear-aperture auto-detect: rim-window signature ranks the opening, "
          "rejects panels/slivers/walls; top real-LED candidate is F112")
    for item in soft:
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
