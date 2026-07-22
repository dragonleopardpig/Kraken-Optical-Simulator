"""Guard: the "Measure MTF from Image" feature (interactive USAF-1951 MTF).

The physics is KrakenOS.USAFMTF (each three-bar element -> 1D profile -> Fourier fundamental -> pi/4
square-wave factor -> MTF); the dialog (panels/mtf_from_image_dialog.py) is the UI -- load a captured
raster, drag a rectangle over each element, Compute to fit + plot, Save CSV.

Display-free: exercises the ANALYSIS end to end through the exact ROI-dict shape the dialog builds
(no Tk / no renderer), plus getsource wiring + the dialog's ROI-drawing contract.

Checks
------
* ANALYZE  -- a synthetic high-contrast 3-bar image through ``analyze_usaf_image`` (the dialog's call)
  gives MTF ~1 unblurred and a LOWER MTF once blurred, and a non-empty curve.
* WIRING   -- the File menu has "Measure MTF from Image..." -> ``open_mtf_from_image_dialog``; the editor
  method delegates to the dialog function.
* CONTRACT -- the dialog binds canvas ROI drawing (press/motion/release), stores ROIs in IMAGE pixels
  (canvas coord / scale), computes via ``analyze_usaf_image``, and saves via ``save_csv``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_mtf_from_image

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np


def _bars(width=60, height=40, cycles=3, amplitude=255.0):
    x = np.arange(width)
    square = np.sign(np.sin(2.0 * np.pi * cycles * x / width)) * 0.5 + 0.5  # 0..1
    return np.tile(square, (height, 1)) * amplitude


def _check_analyze(failures, notes):
    from KrakenOS.USAFMTF import analyze_usaf_image

    img = _bars()
    roi = {"group": 2, "element": 1, "roi": (0, 0, 60, 40), "orientation": "vertical", "cycles": 3.0}
    res = analyze_usaf_image(img, [roi], target_contrast=1.0)
    m = res.measurements[0]
    if not (m.mtf > 0.9):
        failures.append(f"ANALYZE: unblurred high-contrast bars should give MTF ~1, got {m.mtf:.3f}")
    freq, mtf = res.curve("x", "object")
    if freq.size == 0:
        failures.append("ANALYZE: the object-space curve is empty")
    try:
        from scipy.ndimage import gaussian_filter1d
        blur = gaussian_filter1d(img.astype(float), 3.0, axis=1)
        mb = analyze_usaf_image(blur, [roi], target_contrast=1.0).measurements[0]
        if not (mb.mtf < m.mtf):
            failures.append(f"ANALYZE: blur must reduce MTF ({mb.mtf:.3f} !< {m.mtf:.3f})")
    except Exception as exc:
        failures.append(f"ANALYZE: blur check raised {exc}")
    if not [f for f in failures if f.startswith("ANALYZE")]:
        notes.append(f"analyze = unblurred MTF {m.mtf:.3f} (~1); blur reduces it; curve non-empty")


def _check_edge_analyze(failures, notes):
    from KrakenOS.EdgeMTF import measure_slanted_edge_mtf

    def slanted_edge(w, h, angle_deg=5.0, blur=0.0):
        yy, xx = np.mgrid[0:h, 0:w].astype(float)
        edge = xx - (w / 2 + np.tan(np.radians(angle_deg)) * (yy - h / 2))
        img = np.where(edge > 0, 240.0, 15.0)
        if blur > 0:
            from scipy.ndimage import gaussian_filter
            img = gaussian_filter(img, blur)
        return img

    sharp = measure_slanted_edge_mtf(slanted_edge(80, 120, 5, 0.0))
    if not (sharp.mtf[0] > 0.99):
        failures.append(f"EDGE: MTF must start at 1 (DC), got {sharp.mtf[0]:.3f}")
    if sharp.frequency_cycles_per_px[-1] > 0.51:
        failures.append("EDGE: frequency must be capped at the native Nyquist (0.5 cyc/px)")
    blur = measure_slanted_edge_mtf(slanted_edge(80, 120, 5, 2.5))
    fs, fb = sharp.frequency_cycles_per_px, blur.frequency_cycles_per_px
    if not (np.interp(0.25, fb, blur.mtf) < np.interp(0.25, fs, sharp.mtf)):
        failures.append("EDGE: blur must reduce the slanted-edge MTF")
    if not [f for f in failures if f.startswith("EDGE")]:
        notes.append("edge = slanted-edge MTF starts at 1, capped at Nyquist, blur reduces it")


def _check_wiring(failures, notes):
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.panels import main_window

    if not hasattr(KrakenLayoutEditor, "open_mtf_from_image_dialog"):
        failures.append("WIRING: the editor has no open_mtf_from_image_dialog")
        return
    mw = inspect.getsource(main_window)
    if "Measure MTF from Image..." not in mw or "self.open_mtf_from_image_dialog" not in mw:
        failures.append("WIRING: the File menu has no 'Measure MTF from Image...' -> open_mtf_from_image_dialog")
    op = inspect.getsource(KrakenLayoutEditor.open_mtf_from_image_dialog)
    if "open_mtf_from_image_dialog(self)" not in op:
        failures.append("WIRING: the editor method does not delegate to the dialog function")
    if not [f for f in failures if f.startswith("WIRING")]:
        notes.append("wiring = File menu -> editor.open_mtf_from_image_dialog -> dialog function")


def _check_contract(failures, notes):
    from KrakenOS.UI.panels import mtf_from_image_dialog as mod

    src = inspect.getsource(mod.open_mtf_from_image_dialog)
    for token, msg in (
        ("measure_slanted_edge_mtf", "the dialog does not offer the slanted-edge mode"),
        ("analyze_usaf_image", "the dialog does not call analyze_usaf_image (USAF mode)"),
        ("mode_var", "no target-type (edge vs USAF) mode selector"),
        ("load_grayscale_image", "the dialog does not load the full-res grayscale for the fit"),
        ("<ButtonPress-1>", "no ROI drag-start bind"),
        ("<B1-Motion>", "no ROI drag-motion bind"),
        ("<ButtonRelease-1>", "no ROI drag-release bind"),
        ('/ s', "ROIs must be stored in IMAGE pixels (canvas coord / scale)"),
        ("save_csv", "no Save CSV path"),
        ("result.plot", "the dialog does not plot the MTF curve"),
    ):
        if token not in src:
            failures.append(f"CONTRACT: {msg}")
    if not [f for f in failures if f.startswith("CONTRACT")]:
        notes.append("contract = edge + USAF modes; draw ROI in image px; analyze; plot; save CSV")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_analyze, _check_edge_analyze, _check_wiring, _check_contract):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_mtf_from_image (Measure MTF from Image) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll MTF-from-image checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
