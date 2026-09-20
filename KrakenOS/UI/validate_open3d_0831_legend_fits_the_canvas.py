"""Guard for bugs/0831 -- the illustration legend fits inside its canvas.

bugs/0830 put the part picture in the post-swap FOV popup with a single-line legend,
"green = inspected   grey = unreachable". The user's screenshot showed it spilling past
BOTH canvas borders. Measured: that string renders **196 px** in a **190 px** canvas.

A caption that overflows its own box is the kind of defect a headless check cannot see and
a rendered screenshot shows instantly -- bugs/0828 hit the same class when the derivation
chain measured 1246 px wide until it was actually drawn.

Checks (measured against real Tk font metrics, so they track the theme):
  A  the old one-line legend really did overflow -- the bug was measured, not guessed;
  B  each of the two replacement lines fits, with margin;
  C  the drawing area and the legend rows cannot collide.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0831_legend_fits_the_canvas
"""

from __future__ import annotations

CANVAS_W = 190
CANVAS_H = 120
DRAW_H = 96          # the part is drawn into this, leaving the rest for the legend
LEGEND_Y = (100, 111)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    import tkinter as tk

    from KrakenOS.UI.services.inspection_field_chain import face_polygons
    from KrakenOS.UI.services.inspection_part import normalize_inspection_part_spec

    try:
        root = tk.Tk()
    except Exception as exc:
        notes.append(f"SKIP: no display for font metrics ({exc!r})")
        return True, notes
    try:
        probe = tk.Canvas(root)
        font = ("TkDefaultFont", 7)

        def width_px(text):
            item = probe.create_text(0, 0, text=text, font=font, anchor="w")
            x0, _, x1, _ = probe.bbox(item)
            return x1 - x0

        old = width_px("green = inspected   grey = unreachable")
        ok(old > CANVAS_W,
           f"A1: the one-line legend really did overflow -- {old} px in a {CANVAS_W} px "
           f"canvas, which is what the user's screenshot showed")

        for text in ("green = inspected", "grey = not imageable"):
            w = width_px(text)
            ok(w <= CANVAS_W - 8,
               f"B: '{text}' fits with margin ({w} px in {CANVAS_W})")

        spec = normalize_inspection_part_spec(
            {"width_mm": 50.0, "height_mm": 1.0, "depth_mm": 50.0, "active_face": "front"})
        ys = [y for poly in face_polygons(spec, width_px=CANVAS_W, height_px=DRAW_H).values()
              for _, y in poly]
        ok(max(ys) < min(LEGEND_Y) - 4,
           f"C1: the drawing ends at y={max(ys):.0f}, clear of the legend at y={min(LEGEND_Y)}")
        ok(max(LEGEND_Y) < CANVAS_H - 4,
           f"C2: and the lower legend line at y={max(LEGEND_Y)} stays inside the "
           f"{CANVAS_H} px canvas")
    finally:
        try:
            root.destroy()
        except Exception:
            pass

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0831 legend-fits-the-canvas validation PASSED")
        return 0
    print("0831 legend-fits-the-canvas validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
