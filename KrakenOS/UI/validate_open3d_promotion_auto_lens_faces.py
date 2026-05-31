"""Regression: STL lens promotion auto-assigns Transmit/Port + Absorber.

User flag (3D.png after the penta-telescope cascade build): "some
unknown big bending ray" — rays bend erratically at the post-cascade
DCV/Achromat because every promoted face landed with function set
to 'Unassigned' and KrakenOS fell back to per-triangle refraction.

The fix is in ``StepOverlayPromotionService._promoted_local_step_face_metadata``:
when the two largest preserved faces have anti-parallel normals (a
simple lens shape), mark them ``Transmit/Port`` and the rest
``Absorber/Mechanical``. Prisms and other bodies whose two largest
faces aren't anti-parallel stay ``Unassigned`` so the manual
face-assignment dialog still applies.

This test exercises the standalone helper with three synthetic
fixtures so the heuristic is locked in and any future tweak can
prove it still:

* simple lens (two anti-parallel big faces + one tiny side) -> auto
* penta prism (5 mixed-normal faces, none anti-parallel) -> no-op
* lens-shaped but with one face already assigned -> no-op (preserve
  user/upstream intent)
"""

from __future__ import annotations

import sys

from KrakenOS.UI.services.step_overlay_promotion import _auto_assign_lens_face_functions


def _lens_faces() -> list[dict]:
    return [
        {"face_id": "F001", "role": "Unassigned", "function": "Unassigned", "normal": [0.0, 0.0, -1.0], "area_mm2": 285.0},
        {"face_id": "F002", "role": "Unassigned", "function": "Unassigned", "normal": [0.0, 0.0,  1.0], "area_mm2": 285.0},
        {"face_id": "F003", "role": "Unassigned", "function": "Unassigned", "normal": [1.0, 0.0,  0.0], "area_mm2":  60.0},
    ]


def _prism_faces() -> list[dict]:
    # Penta-prism-ish: 5 faces at 36 deg increments. No two have
    # anti-parallel normals.
    import math
    faces: list[dict] = []
    for i in range(5):
        ang = math.radians(36.0 * i)
        faces.append({
            "face_id": f"F{i+1:03d}",
            "role": "Unassigned",
            "function": "Unassigned",
            "normal": [math.cos(ang), math.sin(ang), 0.0],
            "area_mm2": 900.0,
        })
    return faces


def _partially_assigned_lens_faces() -> list[dict]:
    faces = _lens_faces()
    faces[0]["function"] = "Transmit/Port"
    faces[0]["role"] = "Input"
    return faces


def _run() -> int:
    failures: list[str] = []

    # 1. Simple lens -> two big faces become Transmit/Port, side becomes Absorber.
    lens = _lens_faces()
    n = _auto_assign_lens_face_functions(lens)
    if n != 3:
        failures.append(f"simple lens: expected 3 assignments, got {n}")
    funcs = [f.get("function") for f in lens]
    if funcs[0] != "Transmit/Port" or funcs[1] != "Transmit/Port":
        failures.append(f"simple lens: end faces should be Transmit/Port, got {funcs[:2]}")
    if funcs[2] != "Absorber/Mechanical":
        failures.append(f"simple lens: side face should be Absorber/Mechanical, got {funcs[2]}")
    if any(f.get("assignment_origin") != "auto_lens_promotion" for f in lens):
        failures.append("simple lens: assignment_origin not tagged on every face")
    # roles: Input + Output stamped on the two big faces.
    roles = [f.get("role") for f in lens]
    if roles[0] != "Input" or roles[1] != "Output":
        failures.append(f"simple lens: roles should be Input/Output, got {roles[:2]}")

    # 2. Prism-like -> no assignment (no anti-parallel pair).
    prism = _prism_faces()
    n_prism = _auto_assign_lens_face_functions(prism)
    if n_prism != 0:
        failures.append(f"prism: expected 0 (heuristic should not trigger), got {n_prism}")
    if any(f.get("function") != "Unassigned" for f in prism):
        failures.append("prism: function fields were modified")
    if any(f.get("assignment_origin") for f in prism):
        failures.append("prism: assignment_origin tagged on a face that should not have been touched")

    # 3. Lens-shape but one face already assigned -> no-op.
    pre_assigned = _partially_assigned_lens_faces()
    n_partial = _auto_assign_lens_face_functions(pre_assigned)
    if n_partial != 0:
        failures.append(
            f"partially assigned lens: expected no-op to preserve manual assignment, got {n_partial} changes"
        )
    # Confirm the pre-existing assignment didn't get clobbered.
    if pre_assigned[0].get("function") != "Transmit/Port" or pre_assigned[0].get("role") != "Input":
        failures.append("partially assigned lens: existing Input/Transmit got clobbered")
    # And the other faces stayed Unassigned.
    if pre_assigned[1].get("function") != "Unassigned":
        failures.append("partially assigned lens: other faces should still be Unassigned")

    # 4. Empty input -> 0 changes, no crash.
    if _auto_assign_lens_face_functions([]) != 0:
        failures.append("empty faces: heuristic should report 0 changes")

    if failures:
        print("FAIL: STL-lens auto face assignment regressions:", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        return 1

    print(
        "PASS: lens-shaped STL bodies get Transmit/Port on the two anti-parallel "
        "end faces and Absorber/Mechanical on the rest; prisms and pre-assigned "
        "bodies are left alone."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_run())
