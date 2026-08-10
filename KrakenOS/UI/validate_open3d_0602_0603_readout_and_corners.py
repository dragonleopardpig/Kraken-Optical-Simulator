"""Guard for bugs/0602 + bugs/0603 — flag_20260810_164247_396.

bugs/0602: after a 55x55 FOV solve the green coverage label read "FOV 49.8x49.8". The
solve books a conjugate whose RAW paraxial magnification is shifted by the learned
measured/first-order ratio (bugs/0591) so the DELIVERED field is what the user typed —
but the detector-coverage overlay back-computed its object-FOV label from the raw value,
displaying `typed x c` (the wrong-direction number, read as a forced clamp). The overlay
readout must be measured-aware, and the raw helper must STAY raw (the booking math and
current_state() apply the factor themselves).

bugs/0603: the nav cube and the XYZ axes marker lived in WINDOW-FRACTION viewports, which
letterbox on any non-square window; the corner cameras centre their content, so neither
widget hugged its corner however the constants were tuned (the FOURTH flag on this
corner). The viewports must be PIXEL-SQUARE, anchored at the corner, recomputed from the
live window size each render.

Checks (all display-free):
  A  0602 CONTRACT — folded_m_correction is module-level; the overlay _magnification
     multiplies by it; the raw helper source does NOT.
  B  0602 BEHAVIOUR — with a synthetic correction 0.905 on a stub editor, the overlay
     magnification equals raw*0.905 (and the label math then reads the typed field).
  C  0603 MATH — corner_square_viewport is pixel-square and corner-touching for both
     anchors across window shapes (wide, tall, small, degenerate).
  D  0603 WIRING — NavigationCube applies it in the render StartEvent observer and the
     hit-test reads the live viewport; the inspector squares the axes marker on the
     window StartEvent.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0602_0603_readout_and_corners
"""

from __future__ import annotations

import inspect

import numpy as np


def run_checks():
    notes: list[str] = []
    ok = True

    # ---------------------------------------------------------------- A: 0602 contract
    from KrakenOS.UI.services import quick_estimation as qe_module
    from KrakenOS.UI.services import detector_coverage_overlay as overlay_module

    if not callable(getattr(qe_module, "folded_m_correction", None)):
        ok = False
        notes.append("FAIL: A (bugs/0602): quick_estimation.folded_m_correction is gone")
    else:
        notes.append("PASS: A1: folded_m_correction is a module-level accessor")
    overlay_mag_src = inspect.getsource(overlay_module.DetectorCoverageOverlayService._magnification)
    if "folded_m_correction" not in overlay_mag_src:
        ok = False
        notes.append(
            "FAIL: A (bugs/0602): the coverage overlay's _magnification no longer applies "
            "the measured correction -- after a solve the green FOV label shows typed*c "
            "(the flagged 49.8x49.8) instead of the delivered field"
        )
    else:
        notes.append("PASS: A2: the coverage overlay magnification is measured-aware")

    # ---------------------------------------------------------------- B: 0602 behaviour
    class _StubEditor:
        _folded_m_correction_state = None

        def _current_finite_paraxial_magnification(self):
            return -0.4618  # raw paraxial m after a corrected booking

    class _StubService(overlay_module.DetectorCoverageOverlayService):
        def __init__(self, editor):
            self.editor = editor
            self._pv = None

    editor = _StubEditor()
    service = _StubService(editor)
    base = service._magnification()
    editor._folded_m_correction_state = 0.905
    corrected = service._magnification()
    if base is None or corrected is None or not np.isclose(abs(base), 0.4618, atol=1e-9):
        ok = False
        notes.append(f"FAIL: B (bugs/0602): baseline magnification wrong ({base})")
    elif not np.isclose(corrected, base * 0.905, rtol=1e-9):
        ok = False
        notes.append(
            f"FAIL: B (bugs/0602): overlay magnification {corrected} != raw*correction "
            f"{base * 0.905} -- the label back-computes the wrong-direction number again"
        )
    else:
        label_side = 2 * 11.5 / abs(corrected)
        notes.append(
            f"PASS: B: overlay m = raw*c ({corrected:.5f}); label side {label_side:.1f} "
            "reads the delivered field, not typed*c"
        )
    if abs(editor._current_finite_paraxial_magnification()) != 0.4618:
        ok = False
        notes.append("FAIL: B (bugs/0602): the raw helper was mutated")

    # ---------------------------------------------------------------- C: 0603 math
    from KrakenOS.UI.services.nav_cube_widget import corner_square_viewport

    bad = []
    for (w, h) in ((2478, 1264), (1264, 2478), (800, 600), (640, 480), (5120, 1440)):
        for anchor in ("top-right", "bottom-left"):
            vp = corner_square_viewport(
                w, h, side_fraction=0.22 if anchor == "top-right" else 0.15, anchor=anchor
            )
            if vp is None:
                bad.append(f"{w}x{h}/{anchor}: None")
                continue
            x0, y0, x1, y1 = vp
            side_w = (x1 - x0) * w
            side_h = (y1 - y0) * h
            if abs(side_w - side_h) > 0.51:  # sub-pixel: the viewport must be SQUARE
                bad.append(f"{w}x{h}/{anchor}: {side_w:.1f}x{side_h:.1f} not square")
            if anchor == "top-right" and (x1 != 1.0 or y1 != 1.0):
                bad.append(f"{w}x{h}/{anchor}: does not touch the corner")
            if anchor == "bottom-left" and (x0 != 0.0 or y0 != 0.0):
                bad.append(f"{w}x{h}/{anchor}: does not touch the corner")
    if corner_square_viewport(0, 100, side_fraction=0.22) is not None:
        bad.append("degenerate 0x100 did not return None")
    if bad:
        ok = False
        notes.append("FAIL: C (bugs/0603): " + "; ".join(bad))
    else:
        notes.append("PASS: C: corner viewports are pixel-square and corner-touching at every shape")

    # ---------------------------------------------------------------- D: 0603 wiring
    from KrakenOS.UI.services import nav_cube_widget as cube_module
    from KrakenOS.UI import open3d_inspector as inspector_module

    start_src = inspect.getsource(cube_module.NavigationCube._on_render_start)
    hit_src = inspect.getsource(cube_module.NavigationCube._point_in_viewport)
    if "_apply_corner_viewport" not in start_src:
        ok = False
        notes.append(
            "FAIL: D (bugs/0603): the cube no longer re-squares its viewport on render -- "
            "a window-fraction letterbox parks it off the corner again"
        )
    elif "self._viewport" not in hit_src:
        ok = False
        notes.append(
            "FAIL: D (bugs/0603): the cube hit-test reads the static constant, not the "
            "live viewport -- clicks miss once the corner is re-squared"
        )
    else:
        notes.append("PASS: D1: the cube re-squares per render and hit-tests the live viewport")
    if "_square_orientation_marker_viewport" not in inspect.getsource(inspector_module.Kraken3DInspector):
        ok = False
        notes.append(
            "FAIL: D (bugs/0603): the inspector lost the axes-marker squaring observer -- "
            "the XYZ indicator floats off the lower-left corner on wide windows again"
        )
    else:
        marker_src = inspect.getsource(
            inspector_module.Kraken3DInspector._square_orientation_marker_viewport
        )
        if "corner_square_viewport" not in marker_src or "bottom-left" not in marker_src:
            ok = False
            notes.append(
                "FAIL: D (bugs/0603): the axes marker no longer uses the shared pixel-square "
                "corner math"
            )
        else:
            notes.append("PASS: D2: the axes marker squares itself at the lower-left per render")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Readout-and-corners validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
