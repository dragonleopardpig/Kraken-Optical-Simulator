"""bugs/0797 -- a drawing uses the DRAWN size, not the trace mesh.

flag_20260916_135706 + attachment/freecad.png: "there are oversized Object Plane + Surrogate".
The WWK10 scene draws 28.0045 mm datums and exported 56.009 -- 56 mm of glass inside a 44 mm
barrel -- with the object plane at 112.018 against its own 58.539.

The inflation itself is deliberate. bugs/0623/0624 extends surrogate block rows to 2x their
drawn diameter so a corner pencil that threads the datum and the stop still REFRACTS instead of
striking a wall, and says so: "the trace mesh extends; the DISPLAY keeps the row's drawn size".
bugs/0674 honoured that for the 3D view; the STEP writers build their own geometry from the
BUILT surfaces and never did.

Display-free: a synthetic 2x-inflated scene in a temp dir, exported through the real analytic
writer and measured with OCC. No app window, no rendering, no vendor CAD.
"""

from __future__ import annotations

import contextlib
import inspect
import io
import pprint
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# A surrogate block: Front/Rear Optical Vertex Datum around two groups and a stop. The
# datum naming is what makes _build_system_from_specs apply the bugs/0623/0624 2x extension.
_ROWS = [
    ("Object", "Object at 1X", 0.0, 110.0, 58.5390),
    ("Standard", "Front Optical Vertex Datum", 0.0, 28.0630, 28.0045),
    ("Thin Lens", "Blackbox Group 1", 100000.0, 1.0, 28.0045),
    ("Aperture", "Aperture Stop", 0.0, 1.0, 10.0045),
    ("Thin Lens", "Blackbox Group 2", 70.079176, 42.698468, 28.0045),
    ("Standard", "Rear Optical Vertex Datum", 0.0, 97.3644885834, 28.0045),
    ("Image", "Image / Sensor at 1X", 0.0, 0.0, 17.5161),
]
_EXPECTED = {row[1]: row[4] for row in _ROWS}


def _layout_source() -> str:
    settings = {
        "aperture_type": "EPD", "aperture_value": "10.0", "display_orientation": "YZ",
        "field_count": 3, "field_type": "Real Image Height", "field_value": 8.75,
        "object_mode": "Finite", "projection_display_mode": "Full 3D", "wavelength": 0.55,
    }
    surfaces = [
        {"surface": s, "name": n, "rc": rc, "thickness": t, "diameter": d, "glass": "AIR"}
        for s, n, rc, t, d in _ROWS
    ]
    return (
        '"""bugs/0797 synthetic export scene."""\n\n'
        "TITLE = 'bugs 0797 probe'\n\n"
        f"SETTINGS = {pprint.pformat(settings)}\n\n"
        f"SURFACES = {pprint.pformat(surfaces)}\n"
    )


def _face_spans(step_path: Path) -> list[tuple[float, float]]:
    """(max transverse span, z) for every face in the STEP, sorted by z."""
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.TopExp import TopExp_Explorer

    reader = STEPControl_Reader()
    reader.ReadFile(str(step_path))
    reader.TransferRoots()
    shape = reader.OneShape()
    out: list[tuple[float, float]] = []
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        box = Bnd_Box()
        brepbndlib.Add(exp.Current(), box)
        if not box.IsVoid():
            xm, ym, zm, xM, yM, zM = box.Get()
            out.append((max(xM - xm, yM - ym), zm))
        exp.Next()
    return sorted(out, key=lambda q: q[1])


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    # ---- A: the contract, at its source ---------------------------------------------------
    from KrakenOS.UI import layout_editor as le
    from KrakenOS.UI.services import cad_step_export as cse
    from KrakenOS.UI.services import optical_solid_workflow as osw

    build_src = inspect.getsource(le._build_system_from_specs)
    ok("surface.Diameter = 2.0 * _spec_diam" in build_src,
       "A: the BUILD still extends surrogate rows to 2x -- bugs/0623/0624 needs that for the "
       "trace, so the export compensates rather than the build being 'fixed'")

    ok("display_diameter" in inspect.getsource(cse._make_occ_revolution_face),
       "A: the revolution face accepts a DRAWN diameter override")
    for writer in ("_write_step_with_analytic_surfaces", "_write_step_with_cad_shapes_and_rays"):
        src = inspect.getsource(getattr(cse, writer))
        ok("_drawn_surface_diameter" in src, f"A: {writer} passes the drawn diameter")
    ok("bugs/0797" in inspect.getsource(osw.LayoutOpticalSolidWorkflowMixin._collect_3d_step_export_meshes),
       "A: the faceted fallback rescales its AAA meshes too")

    # a row with no usable diameter must not override anything
    ok(cse._drawn_surface_diameter(None) is None,
       "A: no row -> keep the built diameter")

    class _Row:
        def __init__(self, d):
            self.diameter = d

    ok(cse._drawn_surface_diameter(_Row(0.0)) is None,
       "A: a zero diameter -> keep the built diameter")
    ok(cse._drawn_surface_diameter(_Row("nonsense")) is None,
       "A: an unparseable diameter -> keep the built diameter")
    ok(abs((cse._drawn_surface_diameter(_Row(28.0045)) or 0.0) - 28.0045) < 1e-9,
       "A: a real diameter is used")

    # ---- B: end to end, through the real writer -------------------------------------------
    with tempfile.TemporaryDirectory(prefix="kraken0797_") as tmp:
        tmpdir = Path(tmp)
        path = tmpdir / "probe_export.py"
        path.write_text(_layout_source(), encoding="utf-8")

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data

        app = KrakenLayoutEditor(headless=True)
        app._prompt_for_missing_cad_assets = lambda: None
        try:
            info = _load_python_data(path)
            app._reset_complete_layout_runtime_state(close_viewers=True)
            app.current_layout_file = path.resolve()
            app.rows = app._normalized_rows_copy(
                [app._row_from_layout_item(i) for i in info["surfaces"]])
            app._auto_assign_missing_elements(app.rows)
            app._apply_layout_settings(info.get("settings", {}))
            app._normalize_special_rows()
            app._sync_table()
            app._select_table_row(0)
            app._invalidate_preview_scene_trace()
            app.auto_save_plot_var.set(False)
            app.update_idletasks()

            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                system = app.build_system()

            # the build really is inflated -- otherwise this guard proves nothing
            sdt = system.SDT
            inflated = [
                (app.rows[i].name, float(sdt[i].Diameter), float(app.rows[i].diameter))
                for i in range(len(app.rows))
                if abs(float(sdt[i].Diameter) - float(app.rows[i].diameter)) > 1e-6
            ]
            ok(len(inflated) >= 5,
               f"B: the built system inflates {len(inflated)} of {len(app.rows)} rows "
               f"(e.g. {inflated[0][0]}: {inflated[0][2]:.4f} -> {inflated[0][1]:.4f})")

            out = tmpdir / "probe.step"
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                analytic, _faceted, _tris = cse._write_step_with_analytic_surfaces(
                    system, app.rows, [], out)
            ok(analytic == len(app.rows),
               f"B: the writer emitted one analytic face per row ({analytic})")

            spans = _face_spans(out)
            ok(len(spans) == len(app.rows), f"B: {len(spans)} faces in the STEP")
            # Match as a MULTISET, not by z order: a curved row (group 2, rc 70.08) has a
            # bounding box whose zmin sits off its vertex, and OCC's bound on a revolved
            # b-spline runs a micron or two wide, so pair each face with its nearest expected
            # diameter and require every row to be claimed exactly once.
            TOL = 0.01
            # Against the LIVE rows, not the authored literals: _normalize_special_rows
            # resizes the Image row to the conjugate of the object (at 1x it becomes the
            # object's own 58.539, not the 17.5161 the file was written with). The contract
            # is "the export equals row.diameter", whatever the scene has settled on.
            remaining = [float(r.diameter) for r in app.rows]
            worst = 0.0
            unmatched: list[float] = []
            for span, _z in spans:
                if not remaining:
                    unmatched.append(span)
                    continue
                best = min(range(len(remaining)), key=lambda i: abs(remaining[i] - span))
                error = abs(remaining[best] - span)
                if error <= TOL:
                    worst = max(worst, error)
                    remaining.pop(best)
                else:
                    unmatched.append(span)
            ok(not unmatched and not remaining,
               f"B: every exported face equals a ROW diameter (worst error {worst:.2e} mm; "
               f"unmatched faces {[f'{s:.4f}' for s in unmatched]}, "
               f"rows never drawn {[f'{d:.4f}' for d in remaining]})")
            widest = max(span for span, _z in spans)
            widest_row = max(float(r.diameter) for r in app.rows)
            ok(abs(widest - widest_row) < TOL,
               f"B: the widest face is {widest:.4f} mm -- the widest ROW ({widest_row:.4f}), "
               "not the 112.018 the build carries for it")
            datums = [s for s, _z in spans if abs(s - 28.0045) < 1e-3]
            ok(len(datums) == 4,
               f"B: all four 28.0045 mm block rows exported at their drawn size "
               f"({len(datums)}/4), none at 56.009")
        finally:
            with contextlib.suppress(Exception):
                app.destroy()

    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0797 drawn-size export validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
