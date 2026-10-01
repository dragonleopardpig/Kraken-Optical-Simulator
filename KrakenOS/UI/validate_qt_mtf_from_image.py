"""Phase 5g guard (docs/design_qt_migration.md, bugs/0938): "Measure MTF from Image" is ONE session
rendered by Tk and by Qt. On synthetic captures -- a 5° slanted edge and two three-bar elements:

  O  File -> "Measure MTF from Image..." in the Qt shell opens the Qt dialog (the model hands off
     through `show_mtf_from_image_dialog`), and the ribbon carries it
  E  a REAL mouse drag over the edge -- a capture shown at 0.5x -- stores the box in IMAGE pixels
     (twice the display box); Compute gives the same MTF
     curve as calling `measure_slanted_edge_mtf` on that box directly (edge angle ≈ 5°)
  U  in USAF mode two real drags add G2E1 and G2E2 (the element field advances by itself); Compute
     fills each box's MTF and R²
  T  the same drags in the Tk dialog store the same ROIs, and the two shells save BYTE-identical
     edge and USAF CSV files
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RESULT_MARK = "QTMTF_RESULT "
SKIP_MARK = "QTMTF_SKIP "
EDGE_BOX = (150, 120, 260, 240)                      # display coordinates: the edge capture shows at 0.5x
EDGE_SCALE = 0.5                                     # 1320x1120 px fitted into 660x560
USAF_BOXES = ((30, 50, 90, 190), (170, 50, 215, 190))


def _images(folder: Path) -> tuple[Path, Path]:
    import numpy as np
    from PIL import Image

    # the edge capture is LARGER than the display, so a box must be stored at 1/scale (a view that
    # skipped the scale would store display pixels and still "work" on an image shown 1:1)
    yy, xx = np.mgrid[0:1120, 0:1320]
    edge = 40 + 180 / (1 + np.exp(-((xx - 410) - np.tan(np.radians(5)) * (yy - 360)) / 1.2))
    bars = np.full((300, 400), 220.0)
    for x0, period in ((40, 12), (180, 8)):
        for k in range(3):
            bars[60:180, x0 + k * period: x0 + k * period + period // 2] = 30
    paths = folder / "edge.png", folder / "bars.png"
    Image.fromarray(edge.astype(np.uint8)).save(paths[0])
    Image.fromarray(bars.astype(np.uint8)).save(paths[1])
    return paths


def qt_runtime_checks(folder: str) -> list:
    import numpy as np
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    from KrakenOS.EdgeMTF import measure_slanted_edge_mtf
    from KrakenOS.UI.qt.app import build

    folder = Path(folder)
    edge_png, bars_png = _images(folder)
    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.action_manager["mtf_from_image"].trigger()
    app.processEvents()
    dialog = window.last_mtf_from_image_dialog
    on_ribbon = "mtf_from_image" in window.ribbon.buttons
    rows = [["O", dialog is not None and dialog.isVisible() and on_ribbon,
             f"Qt dialog open: {dialog is not None and dialog.isVisible()}; on the ribbon: {on_ribbon}"]]
    if dialog is None:
        return rows
    session = dialog.session
    answers = {"open": str(edge_png), "save": ""}
    dialog.host.askopenfilename = lambda **_k: answers["open"]
    dialog.host.asksaveasfilename = lambda **_k: answers["save"]

    def drag(box) -> None:
        x0, y0, x1, y1 = box
        QTest.mousePress(dialog.image, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(x0, y0))
        for step in range(1, 5):
            QTest.mouseMove(dialog.image, QPoint(x0 + (x1 - x0) * step // 4, y0 + (y1 - y0) * step // 4))
        QTest.mouseRelease(dialog.image, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(x1, y1))
        app.processEvents()

    QTest.mouseClick(dialog.import_button, Qt.MouseButton.LeftButton)
    drag(EDGE_BOX)
    stored = session.rois[0]["roi"] if session.rois else None
    QTest.mouseClick(dialog.buttons["Compute MTF"], Qt.MouseButton.LeftButton)
    app.processEvents()
    direct = measure_slanted_edge_mtf(session.gray, stored, pixel_pitch_um=None) if stored else None
    same = (direct is not None and session.result is not None
            and np.allclose(np.asarray(session.result.mtf), np.asarray(direct.mtf)))
    angle = float(session.result.edge_angle_deg) if session.result is not None else float("nan")
    expected = tuple(round(v / EDGE_SCALE, 1) for v in EDGE_BOX)
    rows.append(["E", abs(session.display_scale() - EDGE_SCALE) < 1e-9 and stored == expected and same and abs(abs(angle) - 5.0) < 0.5
                 and session.status.startswith("Edge MTF"),
                 f"display scale {session.display_scale():g}: the box dragged at {EDGE_BOX} is stored as {stored} "
                 f"image px (expected {expected}); the curve equals the direct fit: {same}; "
                 f"angle {angle:.2f}°; status {session.status[:50]!r}"])
    answers["save"] = str(folder / "qt_edge.csv")
    QTest.mouseClick(dialog.buttons["Save CSV..."], Qt.MouseButton.LeftButton)

    dialog.mode_buttons["usaf"].click()
    answers["open"] = str(bars_png)
    QTest.mouseClick(dialog.import_button, Qt.MouseButton.LeftButton)
    for box in USAF_BOXES:
        drag(box)
    labels = [roi["label"] for roi in session.rois]
    QTest.mouseClick(dialog.buttons["Compute MTF"], Qt.MouseButton.LeftButton)
    app.processEvents()
    table = [[dialog.table.item(r, c).text() for c in range(dialog.table.columnCount())]
             for r in range(dialog.table.rowCount())]
    filled = all(row[4] and row[5] for row in table) and len(table) == 2
    rows.append(["U", labels == ["G2E1", "G2E2"] and filled,
                 f"two drags added {labels}; the table's MTF/R² after Compute: {[(r[4], r[5]) for r in table]}"])
    answers["save"] = str(folder / "qt_usaf.csv")
    QTest.mouseClick(dialog.buttons["Save CSV..."], Qt.MouseButton.LeftButton)
    app.processEvents()
    return rows + [["_rois", True, json.dumps({"edge": list(stored or ()), "usaf": [list(r["roi"]) for r in session.rois]})]]


def tk_runtime_checks(folder: str) -> list:
    import tkinter as tk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.panels import mtf_from_image_dialog as mod

    folder = Path(folder)
    edge_png, bars_png = folder / "edge.png", folder / "bars.png"
    editor = KrakenLayoutEditor()
    editor.update()
    view = mod.open_mtf_from_image_dialog(editor)
    session = view.session
    answers = {"open": str(edge_png), "save": ""}
    mod.filedialog.askopenfilename = lambda **_k: answers["open"]
    mod.filedialog.asksaveasfilename = lambda **_k: answers["save"]

    def drag(box) -> None:
        x0, y0, x1, y1 = box
        view.canvas.event_generate("<ButtonPress-1>", x=x0, y=y0)
        view.canvas.event_generate("<B1-Motion>", x=x1, y=y1)
        view.canvas.event_generate("<ButtonRelease-1>", x=x1, y=y1)
        editor.update()

    view.import_image()
    drag(EDGE_BOX)
    edge_roi = list(session.rois[0]["roi"])
    view._act(session.compute)
    answers["save"] = str(folder / "tk_edge.csv")
    view.save_csv()
    view.mode_var.set("usaf")
    session.set_mode("usaf")
    answers["open"] = str(bars_png)
    view.import_image()
    for box in USAF_BOXES:
        drag(box)
    view._act(session.compute)
    answers["save"] = str(folder / "tk_usaf.csv")
    view.save_csv()
    editor.update()
    assert isinstance(view.window, tk.Toplevel)
    return [["_rois", True, json.dumps({"edge": edge_roi, "usaf": [list(r["roi"]) for r in session.rois]})]]


def _run(call: str) -> list:
    driver = (
        "import json, os\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_qt_mtf_from_image import tk_runtime_checks, qt_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Qt/Tk teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return [["X", False, f"{call}: exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    folder = tempfile.mkdtemp(prefix="qt_mtf_")
    qt_rows = _run(f"qt_runtime_checks({folder!r})")
    tk_rows = _run(f"tk_runtime_checks({folder!r})")
    qt_rois = next((json.loads(d) for k, _o, d in qt_rows if k == "_rois"), None)
    tk_rois = next((json.loads(d) for k, _o, d in tk_rows if k == "_rois"), None)
    rows = [r for r in qt_rows + tk_rows if r[0] != "_rois"]
    csv_same = {}
    for name in ("edge", "usaf"):
        qt_file, tk_file = Path(folder) / f"qt_{name}.csv", Path(folder) / f"tk_{name}.csv"
        csv_same[name] = qt_file.exists() and tk_file.exists() and qt_file.read_bytes() == tk_file.read_bytes()
    rows.append(["T", qt_rois is not None and qt_rois == tk_rois and all(csv_same.values()),
                 f"Tk and Qt drags stored the same ROIs: {qt_rois == tk_rois} ({qt_rois}); byte-identical CSVs: {csv_same}"])
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
