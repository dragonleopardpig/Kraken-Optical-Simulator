"""Guard for bugs/0828 -- the device dialog shows the DERIVATION and a picture.

Three numbers confused the user in one session and every one was arithmetically correct:
the device stayed 20 mm after typing 50x50 (they had edited Required FOV); the scene drew
``FOV 21.0x8.3`` while the banner said ``delivering 21 x 21`` (per-FACE field vs
whole-sensor field); and a swap pre-filled ``59.3284`` (sensor 23.04 / |m| 0.3883, stated
nowhere). None is an error. Each is a number shown without its parent.

NO FACE SELECTOR. bugs/0768 removed that dropdown at the user's request -- the split field
images the front face and its mirror on the back, so it was never a choice. This guard
pins that it stays removed.

Checks (display-free, pure):
  A  every chain row names what produced it;
  B  the inspected pair is STATED, not offered, and the unreachable faces are named;
  C  the whole-sensor and per-face rows are SEPARATE, and the per-face one is measured --
     computing it from sensor/|m| is the very conflation this module exists to stop;
  D  a typed FOV is authoritative and drops the margin, matching the solve;
  E  the prefill explains itself as sensor/|m|, reproducing the user's 59.3284;
  F  the illustration is drawn at TRUE proportions, so a 20x20x1 part reads as a wafer;
  G  the dialog wires the picture and the chain, and re-adds NO face selector.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0828_field_chain_and_illustration
"""

from __future__ import annotations

import inspect as _inspect


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.inspection_field_chain import (
        FACE_FOV_MARGIN, chain_text, explain_prefill, face_polygons, field_chain,
        inspected_faces, unreachable_faces,
    )
    from KrakenOS.UI.services.inspection_part import face_dims, normalize_inspection_part_spec

    spec = normalize_inspection_part_spec(
        {"width_mm": 20.0, "height_mm": 1.0, "depth_mm": 20.0, "active_face": "front"})

    # ---- A: every row names its parent ----------------------------------------------------------
    rows = field_chain(spec, face_dims_fn=face_dims, sensor_wh=(23.04, 23.04),
                       magnification=1.097, measured_face_wh=(21.0, 8.3))
    ok(all(r.derived_from for r in rows),
       f"A1: every one of the {len(rows)} rows states what produced it")
    ok(len(rows) == 5, f"A2: the full chain is five rows (got {len(rows)})")

    # ---- B: the pair is stated, not offered -----------------------------------------------------
    ok(inspected_faces(spec, folded=True) == ("front", "back"),
       "B1: a folded bench inspects the front face AND its mirror on the back")
    ok(unreachable_faces(spec, folded=True) == ("top", "bottom"),
       "B2: the L x W top and bottom are named unreachable -- the fold turns sideways")
    ok(unreachable_faces(spec, folded=False) == (),
       "B3: an unfolded bench imposes no such limit, so nothing is greyed there")
    body = chain_text(rows)
    ok("2 x (L x T)" in body and "front + its mirror" in body,
       "B4: the chain STATES the inspected pair rather than offering a choice")

    # ---- C: two rows, two provenances -----------------------------------------------------------
    labels = [r.label for r in rows]
    ok("Across the sensor" in labels and "Reaching one face" in labels,
       f"C1: whole-sensor and per-face are SEPARATE rows (got {labels})")
    per_face = next(r for r in rows if r.label == "Reaching one face")
    ok("MEASURED" in per_face.derived_from,
       "C2: the per-face field is measured, never computed")
    ok("8.3" in per_face.value and "21.0027" not in per_face.value,
       f"C3: it carries the measured 8.3, not the sensor/|m| 21.0 (got {per_face.value!r})")
    no_measure = field_chain(spec, face_dims_fn=face_dims, sensor_wh=(23.04, 23.04),
                             magnification=1.097)
    ok(all(r.label != "Reaching one face" for r in no_measure),
       "C4: with nothing measured the per-face row is ABSENT, not computed from sensor/|m| "
       "-- the first draft of this module made exactly that mistake")

    # ---- D: a typed FOV is authoritative ---------------------------------------------------------
    typed = field_chain(spec, face_dims_fn=face_dims, required_fov=21.0)
    fov = next(r for r in typed if r.label == "Required FOV")
    ok("authoritative" in fov.derived_from and "21 x 21" in fov.value,
       f"D1: a typed number is used as given, no margin (got {fov.value!r})")
    auto = next(r for r in field_chain(spec, face_dims_fn=face_dims) if r.label == "Required FOV")
    ok("margin" in auto.derived_from and "21 x 1.05" in auto.value,
       f"D2: blank derives face + {FACE_FOV_MARGIN} (got {auto.value!r})")

    # ---- E: the prefill explains itself -----------------------------------------------------------
    text = explain_prefill((23.04, 23.04), 0.38835)
    ok("59.3" in text and "sensor" in text and "|m|" in text,
       f"E1: the 59.3284 prefill is explained as sensor/|m| (got {text[:70]!r})")
    ok(explain_prefill((23.04, 23.04), 0.0) == "",
       "E2: an unusable magnification explains nothing rather than dividing by zero")

    # ---- F: true proportions -----------------------------------------------------------------------
    import math

    polys = face_polygons(spec, width_px=210, height_px=150)
    ok(sorted(polys) == ["back", "bottom", "left", "right", "top", "front"][::1] or
       sorted(polys) == ["back", "bottom", "front", "left", "right", "top"],
       "F1: all six faces are drawn")

    def _edges(poly):
        """Length edge and thickness edge. NOT the bounding box: an isometric face is a
        SHEARED parallelogram, so its bbox height is the projection's skew, not the part's
        thickness -- the first version of this check measured exactly that and read 55 px
        of 'thickness' on a 1 mm wafer."""
        return math.dist(poly[0], poly[1]), math.dist(poly[1], poly[2])

    long_e, thin_e = _edges(polys["front"])
    ok(long_e > 10 * thin_e,
       f"F2: a 20x20x1 part draws as a WAFER -- length edge {long_e:.0f} px against a "
       f"thickness edge of {thin_e:.0f} px (ratio {long_e/max(thin_e,1e-9):.0f})")
    cube = face_polygons(
        normalize_inspection_part_spec({"width_mm": 10.0, "height_mm": 10.0, "depth_mm": 10.0}),
        width_px=210, height_px=150)
    c_long, c_thin = _edges(cube["front"])
    ok(abs(c_long - c_thin) < 1.0,
       f"F3: and a cube's two edges are equal ({c_long:.0f} vs {c_thin:.0f} px) -- the "
       f"drawing follows the real shape, it is not a fixed icon")

    # ---- G: the dialog wires both, and no selector came back --------------------------------------
    from KrakenOS.UI.services import inspection_part as ip

    src = _inspect.getsource(ip.open_inspection_part_dialog)
    ok("face_polygons" in src and "field_chain" in src,
       "G1: the dialog draws the picture and renders the chain")
    # Check for a constructed WIDGET, not the phrase: the source mentions "Inspected Face"
    # only inside the note recording that bugs/0768 removed it, and a guard that fails on
    # its own explanation would push the next reader to delete the explanation.
    ok("Combobox(" not in src and "OptionMenu(" not in src,
       "G2: NO face selector widget -- bugs/0768 removed it at the user's request")
    ok("0768" in src,
       "G2b: and the source records WHY it is absent, so it is not re-added by accident")
    ok("wraplength" in src,
       "G3: the chain wraps -- an unwrapped render measured 1246 px wide, unusable")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0828 field-chain-and-illustration validation PASSED")
        return 0
    print("0828 field-chain-and-illustration validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
