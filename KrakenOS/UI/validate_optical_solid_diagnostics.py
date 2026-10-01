"""Guard for "Inspect Optical CAD/STL Solids" as one report in both shells (phase 5g, bugs/0936).

  D  the report, built on the Edmund 42779 vendor prism layout plus three more solid rows:
     - the meshed prism reads READY (16 triangles, closed), its detail is exactly the mesh's own
       diagnostics text with the CAD source line;
     - the same mesh with one triangle cut out reads CHECK with the open edges counted;
     - an in-memory Solid_3d_stl object reads CHECK, "diagnostics are unavailable";
     - a layout with no solid refuses with "No rows contain Solid_3d_stl."
  K  the Tk command opens a report window whose table rows are the report's records
  Q  in a real Qt shell the action (also on the ribbon) opens the report dialog with the same rows,
     and selecting a solid shows its diagnostics in the detail pane
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RESULT_MARK = "STLDIAG_RESULT "
SKIP_MARK = "STLDIAG_SKIP "


def _prism_layout(editor) -> Path:
    """The capture script's prism layout, plus a torn copy of the mesh and an in-memory solid."""
    import numpy as np

    from KrakenOS.UI import capture_vendor_prism_case_study_screenshots as cap
    from KrakenOS.UI.layout_editor import SurfaceRow
    from KrakenOS.UI.stl_geometry import read_stl_triangle_vertices

    mesh, *_rest = cap._mesh_vendor_prism(Path("attachment/cad_cache"))
    cap._configure_app(editor, mesh, cap._metadata_for_mesh(mesh))
    _fmt, triangles = read_stl_triangle_vertices(mesh)
    torn = Path(tempfile.mkdtemp(prefix="stldiag_")) / "prism_torn.stl"
    lines = ["solid torn"]
    for triangle in np.asarray(triangles, dtype=float)[:-1]:     # one face triangle cut out
        lines += ["facet normal 0 0 0", "outer loop"] + [f"vertex {x:.9g} {y:.9g} {z:.9g}" for x, y, z in triangle]
        lines += ["endloop", "endfacet"]
    torn.write_text("\n".join(lines + ["endsolid torn"]) + "\n", encoding="utf-8")
    editor.rows.insert(2, SurfaceRow(surface="Solid 3D STL", name="Torn prism", thickness=10.0, diameter=45.0,
                                     glass="BK7", advanced={"Solid_3d_stl": str(torn)}))
    editor.rows.insert(3, SurfaceRow(surface="Solid 3D STL", name="In-memory solid", thickness=10.0, diameter=20.0,
                                     glass="BK7", advanced={"Solid_3d_stl": object()}))
    editor._sync_table()
    return mesh


def tk_checks() -> list:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.reports.base import ReportFailed
    from KrakenOS.UI.reports.optical_solid_diagnostics import NO_SOLIDS, build_optical_solid_diagnostics_report
    from KrakenOS.UI.stl_geometry import format_stl_mesh_diagnostics, inspect_stl_mesh

    editor = KrakenLayoutEditor()
    editor.update()
    rows = []
    try:
        mesh = _prism_layout(editor)
        report = build_optical_solid_diagnostics_report(editor)
        by_name = {record["name"]: record for record in report.rows}
        prism = by_name.get("Edmund 42779 vendor prism", {})
        torn = by_name.get("Torn prism", {})
        memory = by_name.get("In-memory solid", {})
        own_text = format_stl_mesh_diagnostics(inspect_stl_mesh(mesh))
        prism_ok = (prism.get("status") == "READY" and prism.get("triangles") == 16 and prism.get("boundary_edges") == 0
                    and prism.get("text", "").startswith("S1: Edmund 42779 vendor prism\n" + own_text)
                    and "Original CAD source (STEP):" in prism.get("text", ""))
        torn_ok = torn.get("status") == "CHECK" and int(torn.get("boundary_edges") or 0) > 0 and torn.get("triangles") == 15
        memory_ok = memory.get("status") == "CHECK" and "diagnostics are unavailable" in memory.get("text", "")
        detail_ok = report.detail_text.text(0) == report.rows[0]["text"]
        editor.rows = [row for row in editor.rows if not isinstance((row.advanced or {}), dict)
                       or "Solid_3d_stl" not in (row.advanced or {})]
        editor._sync_table()
        try:
            build_optical_solid_diagnostics_report(editor)
            refused = ""
        except ReportFailed as exc:
            refused = str(exc)
        rows.append(["D", prism_ok and torn_ok and memory_ok and detail_ok and refused == NO_SOLIDS,
                     f"prism {prism.get('status')} {prism.get('triangles')} tri / {prism.get('boundary_edges')} open "
                     f"(own text + CAD source: {prism_ok}); torn {torn.get('status')} {torn.get('triangles')} tri / "
                     f"{torn.get('boundary_edges')} open; in-memory {memory.get('status')}; no solids -> {refused!r}"])

        # K -- the Tk command
        _prism_layout(editor)
        editor.open_optical_stl_diagnostics()
        editor.update()
        window = editor._main_optical_solid_dialogs()._diagnostics_window
        table = window.table
        shown = [table.item(iid, "values")[0] for iid in table.get_children("")]
        rows.append(["K", window.is_open() and shown == [r["row"] for r in report.rows],
                     f"Tk report window open: {window.is_open()}; its rows {shown}"])
        window.close()
    finally:
        try:
            editor.destroy()
        except Exception:
            pass
    return rows


def qt_runtime_checks() -> list:
    import time

    from KrakenOS.UI.qt.app import build

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    _prism_layout(window.editor)
    window.refresh_from_model()
    window.action_manager["optical_solid_diagnostics"].trigger()
    end = time.time() + 0.5
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)
    dialog = window._open_dialogs[-1] if window._open_dialogs else None
    if dialog is None or getattr(dialog, "report", None) is None:
        return [["Q", False, "the action opened no report dialog"]]
    model = dialog.model
    shown = [model.data(model.index(r, 0)) for r in range(model.rowCount())]
    dialog.select_master_row(1)
    app.processEvents()
    detail = dialog.detail_text.toPlainText() if dialog.detail_text is not None else ""
    on_ribbon = "optical_solid_diagnostics" in window.ribbon.buttons
    return [["Q", shown == ["S1", "S2", "S3"] and detail.startswith("S2: Torn prism") and on_ribbon,
             f"Qt report rows {shown}; selecting the second shows {detail.splitlines()[0] if detail else ''!r}; "
             f"on the ribbon: {on_ribbon}"]]


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
        "from KrakenOS.UI.validate_optical_solid_diagnostics import tk_checks, qt_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a VTK/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=1200,
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
    from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP

    if not PRISM_42779_STEP.exists():
        return True, [f"SKIP = {PRISM_42779_STEP} absent"]
    rows = _run("tk_checks()") + _run("qt_runtime_checks()")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
