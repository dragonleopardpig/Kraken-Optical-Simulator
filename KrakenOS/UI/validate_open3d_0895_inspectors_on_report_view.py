"""Display-free guard: the Ray and Trace Path inspectors render their builders (bugs/0895,
docs/design_qt_migration.md phase 4).

0867 and 0868 built these two reports -- a master/detail table and a master TREE -- and Qt has
rendered them ever since, but the Tk dialogs kept 1 078 lines of their own widgets, and with
them two things the report could not express:

* an **export that is not the table**. Each inspector flattens every ray (or path) into one row
  per hit under ~140 columns; `Report.write_csv` writes the table, so Qt exported a different,
  much smaller file for the same report. `Report.csv_writer` now lets the model own the file,
  and `reports/ray_csv.py` writes both. The lift was proven byte for byte against the old
  dialogs' own 3.67 MB and 3.21 MB files before they were deleted (bugs/0895); what a guard can
  still assert is that the report DEFERS to that writer rather than writing its 22-column table.
* **toolbar verbs**. "Export Events CSV" and "Open Ray" were Tk buttons, so Qt simply did not
  have them. `ReportAction` carries a verb the model defines; the view supplies only a file
  chooser and which row is selected.

A third thing the port fixed: a RAY node in the tree carried no detail key, so Qt showed nothing
when one was selected while Tk showed every hit of every path beneath it. The node now carries
``"ray:<index>"`` and the model answers it.

  L  the panel is two `ReportWindow`s -- no Treeview, no Toplevel, no csv writer of its own
  X  Export CSV writes the model's ~140-column per-hit file, not the report's own table
  A  the verbs are the model's: Export Events CSV writes the event records, Open Ray shows the
     selected ray in the Ray Inspector
  D  the master/detail table and the master tree both fill from the builder, including a RAY
     node, which shows every hit of every path beneath it
  S  `_select_ray_inspector_ray` finds a ray by its own `ray_index`, and the service that calls
     it holds no Tk widget any more
"""
from __future__ import annotations

import filecmp
import inspect
from pathlib import Path

SCENE = Path("attachment/om05a_folded.py")


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.filedialog as tk_filedialog
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.panels import main_ray_trace_inspectors
    from KrakenOS.UI.reports import ray_csv
    from KrakenOS.UI.services import layout_plot_interaction

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- L the panel is two windows over two builders ---------------------------------------
    panel_source = inspect.getsource(main_ray_trace_inspectors)
    lines = len(panel_source.splitlines())
    ok("ttk.Treeview(" not in panel_source and "tk.Toplevel(" not in panel_source
       and "csv.DictWriter(" not in panel_source and panel_source.count("ReportWindow(") == 2
       and lines < 160,
       f"L: the panel is two ReportWindows over build_ray_inspector_report and "
       f"build_trace_path_report -- {lines} lines, no table, no window, no CSV writer of its own")

    service = inspect.getsource(
        layout_plot_interaction.LayoutPlotInteractionMixin._select_ray_inspector_ray)
    ok("_ray_inspector_ray_table" not in service and "table.selection_set(" not in service
       and "select_ray_inspector_row(" in service,
       "S1: the service that opens a ray on a plot click holds no Tk table -- it asks the panel")

    saved_info = tk_messagebox.showinfo
    saved_save = tk_filedialog.asksaveasfilename
    tk_messagebox.showinfo = lambda *a, **k: "ok"
    out = Path("/tmp/claude-1000")

    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        editor.refresh_plot()
        panel = editor._main_ray_trace_inspector_dialogs()

        editor.open_ray_inspector()
        editor.open_branch_tree_inspector()
        rays = panel._ray_window
        paths = panel._path_window

        # ---- X the CSVs the model writes are the ones the dialogs wrote ---------------------
        # written here from the SAME records, through the two paths that must agree: the
        # report's own write_csv (what a view calls) and the module function (what it defers to)
        report_ray = out / "guard_report_ray.csv"
        module_ray = out / "guard_module_ray.csv"
        rays.report.write_csv(report_ray)
        ray_csv.write_ray_inspector_csv(editor, list(rays.report.rows), module_ray)
        report_tree = out / "guard_report_tree.csv"
        module_tree = out / "guard_module_tree.csv"
        paths.report.write_csv(report_tree)
        ray_csv.write_trace_path_csv(editor, list(paths.report.rows), module_tree)
        same_ray = filecmp.cmp(report_ray, module_ray, shallow=False)
        same_tree = filecmp.cmp(report_tree, module_tree, shallow=False)
        ok(same_ray and same_tree and report_ray.stat().st_size > 1_000_000
           and len(ray_csv.RAY_INSPECTOR_CSV_COLUMNS) > 150
           and rays.report.csv_writer is not None and paths.report.csv_writer is not None,
           f"X: the report's Export CSV defers to the model's writer -- "
           f"{len(ray_csv.RAY_INSPECTOR_CSV_COLUMNS)} ray columns over "
           f"{report_ray.stat().st_size} bytes and {len(ray_csv.TRACE_PATH_CSV_COLUMNS)} path "
           f"columns over {report_tree.stat().st_size}, not the {len(rays.report.columns)}-column "
           f"table" if same_ray and same_tree else
           f"X: report/module CSVs differ (ray={same_ray}, tree={same_tree})")

        # the one field that separates the two per-hit blocks
        ok("hit_branch" in ray_csv.hit_fields({})
           and "hit_branch" not in ray_csv.hit_fields({}, include_branch=False),
           "X2: one per-hit block writes both files -- the trace-path CSV drops hit_branch, "
           "which is already a master column there")

        # ---- A the verbs are the model's ---------------------------------------------------
        events = out / "guard_events.csv"
        tk_filedialog.asksaveasfilename = lambda *a, **k: str(events)
        panel.export_ray_events_csv()
        header = events.read_text(encoding="utf-8").splitlines()[0] if events.exists() else ""
        ok(events.exists() and events.stat().st_size > 100_000 and "event_kind" in header,
           f"A1: Export Events CSV wrote the canonical event records "
           f"({events.stat().st_size if events.exists() else 0} bytes), which are not this "
           f"report's table at all")

        top_nodes = paths.table.get_children("")
        paths.table.selection_set(top_nodes[0])
        ray_key = paths.selected_key()
        ray_detail = len(paths.detail_table.get_children())
        panel._open_branch_tree_selected_ray()
        opened = rays.selected_key()
        expected_ray = panel._branch_tree_selected_ray_index()
        shown = (rays.report.rows[opened].get("ray_index") if opened is not None else None)
        ok(opened is not None and int(shown) == int(expected_ray),
           f"A2: Open Ray showed ray {expected_ray} in the Ray Inspector (row {opened})"
           if opened is not None else "A2: Open Ray selected nothing")

        # ---- D both masters fill from the builder ------------------------------------------
        rays.select_row(3)
        ray_row_detail = len(rays.detail_table.get_children())
        expected_hits = len(rays.report.rows[3].get("hits", []) or [])
        child = paths.table.get_children(top_nodes[0])[0]
        paths.table.selection_set(child)
        path_key = paths.selected_key()
        path_detail = len(paths.detail_table.get_children())
        expected_path_hits = len(paths.report.rows[int(path_key)].get("hits", []) or [])
        ok(ray_row_detail == expected_hits and path_detail == expected_path_hits
           and str(ray_key).startswith("ray:") and ray_detail >= path_detail,
           f"D: the ray table's row 3 showed its {expected_hits} hits, the tree's path node its "
           f"{expected_path_hits}, and the RAY node {ray_key!r} showed every hit of every path "
           f"beneath it ({ray_detail})"
           if ray_row_detail == expected_hits and path_detail == expected_path_hits else
           f"D: ray detail {ray_row_detail}/{expected_hits}, path detail "
           f"{path_detail}/{expected_path_hits}, ray node {ray_key!r} -> {ray_detail}")

        # ---- S a ray is found by its own index, not by position ----------------------------
        last = len(rays.report.rows) - 1
        ray_index = int(rays.report.rows[last].get("ray_index"))
        found = panel.select_ray_inspector_row(ray_index)
        landed = rays.selected_key()
        missing = panel.select_ray_inspector_row(10 ** 6)
        ok(found and landed == last and not missing,
           f"S2: ray {ray_index} was found at row {landed} by its own ray_index, and a ray the "
           f"trace does not have is refused rather than landing on a wrong row"
           if found and landed == last else
           f"S2: select_ray_inspector_row({ray_index}) -> {found}, landed {landed}, wanted {last}")
    finally:
        tk_messagebox.showinfo = saved_info
        tk_filedialog.asksaveasfilename = saved_save
        editor.destroy()

    return state["ok"], notes


def run() -> int:
    passed, notes = run_checks()
    print()
    for note in notes:
        print(("  " + note[2:]) if note.startswith("= ") else ("! " + note))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
