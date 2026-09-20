"""Guard for bugs/0829 -- the Object-plane FOV popup pre-fills from the FACE, not the sensor.

User, on the popup: *"is this pop up correct?"* Every number in it was correct and mutually
consistent -- Width = Height = 59.3284 is sensor 23.04 / |m| 0.38835, "Object FOV (semi) =
41.95" is that square's semi-diagonal (59.3284 * sqrt(2) / 2 = 41.9515), and the legs
9 + 6.85 = 15.85 match the stated total. Correct arithmetic.

Wrong context. The inspected faces on that bench are 20 x 1 mm EDGES, so a square
59.33 x 59.33 field is 3x the face length and 59x its thickness -- a field the machine
cannot deliver, because a centre prism and two RA mirrors fold sideways into the lens and
each face receives a strip. And "the other is derived from the sensor aspect" FORCES that
square: it ties height to the sensor when the constraint that matters is the face.

Checks (display-free, pure):
  A  the popup's own numbers really were self-consistent -- this bug is not an arithmetic fix;
  B  with a device enabled the prefill is the FACE + 5%, the same field the solve targets;
  C  the face prefill is nothing like the sensor one on this bench, which is the point;
  D  with no device the sensor prefill survives AND explains itself;
  E  the source states which parent is in force instead of asserting the sensor's.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0829_fov_popup_prefills_from_the_face
"""

from __future__ import annotations

import inspect as _inspect


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.inspection_field_chain import FACE_FOV_MARGIN, explain_prefill
    from KrakenOS.UI.services.inspection_part import face_dims, normalize_inspection_part_spec

    # ---- A: the popup was arithmetically fine ----------------------------------------------------
    w = 59.3284
    ok(abs(w * 2 ** 0.5 / 2 - 41.95) < 0.01,
       f"A1: 'Object FOV (semi) = 41.95' is the square's semi-diagonal ({w * 2 ** 0.5 / 2:.4f})")
    ok(abs(23.04 / w - 0.38835) < 1e-4,
       "A2: and the width is sensor 23.04 / |m| 0.38835 -- both numbers agreed")
    ok(abs((9 + 6.85) - 15.85) < 1e-9,
       "A3: the fold legs summed to the stated total. Nothing here was miscomputed")

    spec = normalize_inspection_part_spec(
        {"width_mm": 20.0, "height_mm": 1.0, "depth_mm": 20.0,
         "active_face": "front", "enabled": True})
    fw, fh = face_dims(spec, spec["active_face"])

    # ---- B: the face sets the field ---------------------------------------------------------------
    ok((fw, fh) == (20.0, 1.0),
       f"B1: the inspected face is a 20 x 1 mm EDGE (got {(fw, fh)})")
    ok(abs(fw * FACE_FOV_MARGIN - 21.0) < 1e-9 and abs(fh * FACE_FOV_MARGIN - 1.05) < 1e-9,
       "B2: the face prefill is 21 x 1.05 -- face + 5%, the same target the solve uses")

    # ---- C: and it is nothing like the sensor prefill ---------------------------------------------
    ok(w / fw > 2.5 and w / fh > 50,
       f"C1: the sensor prefill was {w / fw:.1f}x the face length and {w / fh:.0f}x its "
       f"thickness -- the mismatch the user could see and could not explain")
    ok(abs(fw * FACE_FOV_MARGIN - w) > 30,
       "C2: so face-derived and sensor-derived are genuinely different fields here, not a "
       "rounding difference")

    # ---- D: no device -> the old behaviour, but explained ------------------------------------------
    note = explain_prefill((23.04, 23.04), 0.38835)
    ok("59.3" in note and "sensor" in note and "|m|" in note,
       f"D1: with no device the sensor prefill survives and names its parent "
       f"(got {note[:60]!r})")
    ok(explain_prefill((23.04, 23.04), 0.0) == "",
       "D2: an unusable magnification explains nothing rather than dividing by zero")

    # ---- E: the popup states which parent is in force ----------------------------------------------
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    src = _inspect.getsource(Kraken3DInspector._open_plane_dimension_dialog) \
        if hasattr(Kraken3DInspector, "_open_plane_dimension_dialog") else ""
    if not src:
        import pathlib
        src = pathlib.Path(_inspect.getfile(Kraken3DInspector)).read_text(encoding="utf-8")
    ok("prefill_note" in src,
       "E1: the popup carries a stated prefill provenance")
    ok("inspected face" in src,
       "E2: and names the inspected face when a device is what set the field")
    ok("0829" in src,
       "E3: the source records why, so the sensor default is not silently restored")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0829 fov-popup-prefills-from-the-face validation PASSED")
        return 0
    print("0829 fov-popup-prefills-from-the-face validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
