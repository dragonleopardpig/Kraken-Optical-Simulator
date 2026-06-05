"""Regression: STL lens promotion auto-assigns Transmit/Port (Uncoated).

User flag (3D.png after the penta-telescope cascade build): "some
unknown big bending ray" — rays bend erratically at the post-cascade
DCV/Achromat because every promoted face landed with function set
to 'Unassigned' and KrakenOS fell back to per-triangle refraction.

The fix marks every promoted face ``Transmit/Port`` (Uncoated): when
the two largest preserved faces have anti-parallel normals (a simple
lens shape), they are additionally labeled Input/Output, and every
other face defaults to Uncoated as well so Snell/Fresnel decides at
each boundary. The auto pass never condemns a face to a hard
``Absorber/Mechanical`` block (bug 0016) -- a beam-splitter cube whose
real entry/exit faces weren't the largest anti-parallel pair used to
get its optical faces blocked, silently killing the trace. The user
authors only the special faces (Mirror, Beam Splitter, Absorber,
detector). Prisms and bodies whose two largest faces aren't
anti-parallel stay ``Unassigned`` here so the manual face-assignment
dialog (which also defaults Uncoated) still applies.

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
        # Singlet: front face at z=-1.25 (normal -Z), back face at
        # z=+1.25 (normal +Z), side cylinder at x=+12 (normal +X).
        {"face_id": "F001", "role": "Unassigned", "function": "Unassigned",
         "normal": [0.0, 0.0, -1.0], "area_mm2": 285.0, "centroid": [0.0, 0.0, -1.25]},
        {"face_id": "F002", "role": "Unassigned", "function": "Unassigned",
         "normal": [0.0, 0.0,  1.0], "area_mm2": 285.0, "centroid": [0.0, 0.0,  1.25]},
        {"face_id": "F003", "role": "Unassigned", "function": "Unassigned",
         "normal": [1.0, 0.0,  0.0], "area_mm2":  60.0, "centroid": [12.0, 0.0, 0.0]},
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
            "centroid": [12.0 * math.cos(ang), 12.0 * math.sin(ang), 0.0],
        })
    return faces


def _partially_assigned_lens_faces() -> list[dict]:
    faces = _lens_faces()
    faces[0]["function"] = "Transmit/Port"
    faces[0]["role"] = "Input"
    return faces


def _run() -> int:
    failures: list[str] = []

    # 1. Simple lens -> two big faces become Transmit/Port (Input/Output) and
    #    every other face defaults to Uncoated (Transmit/Port) too -- the auto
    #    pass never hard-blocks a face with Absorber/Mechanical (bug 0016).
    lens = _lens_faces()
    n = _auto_assign_lens_face_functions(lens)
    if n != 3:
        failures.append(f"simple lens: expected 3 assignments, got {n}")
    funcs = [f.get("function") for f in lens]
    if funcs[0] != "Transmit/Port" or funcs[1] != "Transmit/Port":
        failures.append(f"simple lens: end faces should be Transmit/Port, got {funcs[:2]}")
    if funcs[2] != "Transmit/Port":
        failures.append(f"simple lens: side face should default to Uncoated (Transmit/Port), got {funcs[2]}")
    if any(f.get("function") == "Absorber/Mechanical" for f in lens):
        failures.append("simple lens: auto pass must never assign Absorber/Mechanical")
    if any(f.get("assignment_origin") != "auto_lens_promotion" for f in lens):
        failures.append("simple lens: assignment_origin not tagged on every face")
    # roles: Input + Output stamped on the two big faces.
    roles = [f.get("role") for f in lens]
    if roles[0] != "Input" or roles[1] != "Output":
        failures.append(f"simple lens: roles should be Input/Output, got {roles[:2]}")
    # optical_axis_surface: only the genuine front/back pair is flagged. The
    # side wall is uncoated (the trace won't absorb a ray) but must NOT be a
    # fitted refractive surface -- selecting every Transmit face for the
    # analytic fit over-counts surfaces and demands a spurious glass per side
    # wall, which broke "Convert to Analytic" (bug 0016 follow-up regression).
    flags = [f.get("optical_axis_surface") for f in lens]
    if flags[0] is not True or flags[1] is not True:
        failures.append(f"simple lens: end faces should be flagged optical_axis_surface, got {flags[:2]}")
    if flags[2] is not False:
        failures.append(f"simple lens: side wall must NOT be an optical-axis surface, got {flags[2]}")
    selected = [f for f in lens if f.get("optical_axis_surface")]
    if len(selected) != 2:
        failures.append(
            f"simple lens: analytic fit must select exactly the 2 optical-axis faces, got {len(selected)}"
        )

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
        "PASS: lens-shaped STL bodies get Transmit/Port (Input/Output) on the two "
        "anti-parallel end faces and default the rest to Uncoated (Transmit/Port) "
        "too -- never Absorber/Mechanical; prisms and pre-assigned bodies are left "
        "alone."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_run())
