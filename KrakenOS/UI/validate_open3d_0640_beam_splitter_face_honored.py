"""Guard for bugs/0640 — an explicitly-assigned Beam-Splitter face is honored.

User (machine_vision_150mm_standoff/test): the BS cube's diagonal face was assigned
function "Beam Splitter", but the app didn't recognize the coating -- so no BS reflect
axis and the follower logic didn't treat it as a splitter. Cause: the cube also exposes a
"Transmit/Port" interaction face, and `select_optical_solid_interaction_face` picks the
single top-priority interaction face -- Transmit=2.0 out-ranks Beam-Splitter=1.0 -- so the
assigned coating was shadowed. Fix: `beam_splitter_interaction_face` finds the Beam-Splitter
face DIRECTLY, and BS detection + coating geometry use it.

Checks (display-free):
  A  the new selector returns the Beam-Splitter face even when a higher-priority
     Transmit/Port interaction face is present.
  B  `_solid_has_beam_splitter_interaction_face` is True there; False with no BS face.
  C  REGRESSION WITNESS — the generic `select_optical_solid_interaction_face` still picks
     the Transmit/Port face (2.0), i.e. the exact shadowing the fix now bypasses.
  D  CONTRACT — `beam_splitter_coating_world_frames` selects the coating via
     `beam_splitter_interaction_face` (not the generic top-priority face).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0640_beam_splitter_face_honored
"""

from __future__ import annotations

import inspect


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.nonseq_output_ports import (
        beam_splitter_coating_world_records,
        beam_splitter_interaction_face,
        select_optical_solid_interaction_face,
        _solid_has_beam_splitter_interaction_face,
    )

    bs = {
        "face_id": "S001/F001", "function": "Beam Splitter", "port_role": "Interaction Surface",
        "area_mm2": 6067.0, "centroid_world": (0.0, 0.0, 0.0), "normal_world": (-0.707, 0.0, 0.707),
    }
    tp = {
        "face_id": "S001/F002", "function": "Transmit/Port", "port_role": "Interaction Surface",
        "area_mm2": 4290.0, "centroid_world": (27.5, 0.0, 0.0), "normal_world": (1.0, 0.0, 0.0),
    }
    faces = [tp, bs]  # Transmit first: order must not matter

    # ---------------------------------------------------------------- A
    picked = beam_splitter_interaction_face(faces)
    if picked is None or picked.get("face_id") != "S001/F001":
        ok = False
        notes.append(f"FAIL: A (bugs/0640): the Beam-Splitter face was not found ({picked})")
    else:
        notes.append("PASS: A: the assigned Beam-Splitter face is found despite a higher-priority Transmit face")

    # ---------------------------------------------------------------- B
    if _solid_has_beam_splitter_interaction_face(faces) is not True:
        ok = False
        notes.append("FAIL: B (bugs/0640): a solid with a Beam-Splitter face is not recognized")
    elif _solid_has_beam_splitter_interaction_face([tp]) is not False:
        ok = False
        notes.append("FAIL: B (bugs/0640): a solid with NO Beam-Splitter face was wrongly recognized")
    else:
        notes.append("PASS: B: BS recognized with the coating, not without it")

    # ---------------------------------------------------------------- C: shadowing witness
    generic = select_optical_solid_interaction_face(faces)
    if generic is None or generic.get("face_id") != "S001/F002":
        ok = False
        notes.append(
            f"FAIL: C (bugs/0640): the generic selector no longer shadows with Transmit ({generic}) "
            "-- the regression witness changed; re-derive the fix"
        )
    else:
        notes.append("PASS: C: the generic selector still picks Transmit (the shadowing the fix bypasses)")

    # ---------------------------------------------------------------- D: contract
    # bugs/0643: the row walk (and so the face choice) moved into the extent-carrying
    # beam_splitter_coating_world_records; the 2-tuple frames API is now a thin wrapper.
    src = inspect.getsource(beam_splitter_coating_world_records)
    if "beam_splitter_interaction_face(" not in src:
        ok = False
        notes.append("FAIL: D (bugs/0640): the coating builder no longer uses beam_splitter_interaction_face")
    else:
        notes.append("PASS: D: the coating geometry is taken from the assigned Beam-Splitter face")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Beam-splitter-face-honored validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
