"""Phase 5g part 1 guard (docs/design_qt_migration.md, bugs/0933): the CAD/STL face-roles editor is
a toolkit-neutral session (`face_roles_session`) + a VTK preview (`face_roles_preview`) that the Tk
dialog renders. Claims, measured on the Edmund 42779 vendor prism (a real meshed STEP row):

  A  a committed field PERSISTS at once (the row's face metadata changes before any retrace) and
     the Open 3D retrace is DEBOUNCED: three quick edits run no retrace until the host timer
     fires, then exactly one
  S  Save Roles cancels that pending retrace and retraces once itself, and with auto-orient on it
     poses the row from the Input Port face (the input normal ends up along -Z)
  C  a custom per-face coating table round-trips into the face record; choosing a named preset
     afterwards drops it
  I  choosing "Illumination Source" binds a face-anchored source, the "(outward)" variant stores
     the outward aim, and choosing a coating again unbinds it
  N  input snap: arming needs an Input Port face; a pick on ANOTHER face is refused; a pick on
     the face sets U/V to the point's in-plane offsets (projecting them back lands on the point)
  P  a click in the VTK preview selects the face whose actor it hit, and the picked point lies on
     that face's plane
  T  the Tk dialog shows the session: its table cells are `rows()`, and an action's message stays
     visible (the old dialog's table rebuild re-ran load_selected and overwrote every action's
     message within milliseconds -- "Saved roles. Auto-oriented ..." was never seen)
  M  without VTK/Tk the dialog opens on its Matplotlib preview, draws every face, and a click on
     a face's projected centre selects a face (the fallback raised AttributeError on its first
     draw before 0933: it called layout_editor names that never existed)

Each part runs in its own process: the harness already owns a Tk root with a VTK widget, and a
second root in the same process cannot load VTK's Tk package -- the dialog silently took the
fallback there.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

RESULT_MARK = "FACEROLES_RESULT "


def _open_prism_editor():
    from KrakenOS.UI import capture_vendor_prism_case_study_screenshots as cap
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    app.update()
    mesh, *_rest = cap._mesh_vendor_prism(Path("attachment/cad_cache"))
    cap._configure_app(app, mesh, cap._metadata_for_mesh(mesh))
    return app


def _pump(app, n: int = 10) -> None:
    for _ in range(n):
        app.update()


def vtk_checks() -> list:
    from KrakenOS.UI import face_roles_session as frs

    app = _open_prism_editor()
    rows: list[tuple[str, bool, str]] = []
    try:
        le = frs._layout_module()
        attr = le.OPTICAL_SOLID_FACES_ADVANCED_ATTR
        retraces: list[bool] = []
        real_refresh = app._refresh_open_3d_views
        app._refresh_open_3d_views = lambda force_retrace=False, **_kw: retraces.append(bool(force_retrace))

        def row_face(face_id: str) -> dict:
            return next(f for f in app.rows[1].advanced[attr]["faces"] if f["face_id"] == face_id)

        session = frs.FaceRolesSession(app, 1, app.rows[1], Path(app.rows[1].advanced["Solid_3d_stl"]))
        index = {r["face_id"]: i for i, r in enumerate(session.records)}

        # A -- persist now, retrace once later
        session.select([index["F003"]], index["F003"])
        for function in ("Mirror", "Uncoated", "Mirror"):
            session.form["function"] = function
            session.auto_apply()
        persisted = row_face("F003")["function"]
        before_timer = len(retraces)
        _pump(app, 3)
        app.after(400, lambda: None)
        import time
        deadline = time.time() + 2.0
        while time.time() < deadline and len(retraces) == before_timer:
            app.update()
            time.sleep(0.02)
        rows.append(("A", persisted == "Mirror" and before_timer == 0 and len(retraces) == 1,
                     f"row metadata after 3 quick edits: {persisted!r}; retraces before the timer {before_timer}, after {len(retraces)}"))

        # S -- save cancels the pending retrace and retraces once; auto-orient from the Input Port
        retraces.clear()
        session.form["function"] = "Uncoated"
        session.auto_apply()                      # arms a debounced retrace
        session.select([index["F005"]], index["F005"])
        session.form.update(side="Left", port=le.OPTICAL_SOLID_FACE_PORT_INPUT, auto_orient=True)
        saved = session.save_roles()
        _pump(app, 3)
        time.sleep(0.4)
        _pump(app, 5)
        world = {f["face_id"]: f for f in le.optical_solid_face_world_records(app.rows[1], app._stl_row_z_station(1), assigned_only=False)}
        normal = np.asarray(world["F005"].get("normal_world", world["F005"].get("normal", (0, 0, 0))), dtype=float)
        rows.append(("S", saved and retraces == [True] and float(normal[2]) < -0.99,
                     f"saved={saved}; retraces {retraces} (one, the pending one cancelled); F005 world normal "
                     f"{np.round(normal, 4).tolist()} ({session.validation[:60]}...)"))

        # C -- custom coating table round-trip, a preset drops it
        table = [[[0.1, 0.2]], [[0.0, 0.0]], [0.5, 0.6], [0.0]]
        parsed, met, error = frs.parse_face_coating_table(repr(table), "0")
        session.select([index["F003"]], index["F003"])
        session.set_coating_table(parsed, met)
        session.auto_apply()
        stored = row_face("F003").get("coating_table")
        session.choose_coating(frs.coating_choices()[1])
        session.auto_apply()
        dropped = not row_face("F003").get("coating_table")
        rows.append(("C", error is None and bool(stored) and dropped,
                     f"custom table stored={bool(stored)} (parse error {error}); a preset drops it={dropped}"))

        # I -- illumination bind / outward aim / unbind
        meta = le.optical_solid_metadata
        session.select([index["F006"]], index["F006"])
        session.form["function"] = meta.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_ILLUMINATION_OUTWARD
        session.auto_apply()
        bound = app.face_bound_illumination_source_id(1, "F006")
        aim = app.face_bound_illumination_aim(1, "F006")
        session.form["function"] = "Uncoated"
        session.auto_apply()
        unbound = not app.face_bound_illumination_source_id(1, "F006")
        rows.append(("I", bool(bound) and aim == "outward" and unbound,
                     f"bound {bound!r} aimed {aim!r}; coating again unbinds={unbound}"))

        # N -- input snap
        session.select([index["F003"]], index["F003"])
        session.set_input_snap_pick_mode(True)
        refused_arm = not session.input_snap_pick_active
        session.select([index["F005"]], index["F005"])
        session.set_input_snap_pick_mode(True)
        armed = session.input_snap_pick_active
        face = session.world_face(index["F005"])
        centre = np.asarray(face["anchor_world"], dtype=float)
        u_axis, v_axis = (np.asarray(face[k], dtype=float) for k in ("u_axis_world", "v_axis_world"))
        target = centre + 1.5 * u_axis / np.linalg.norm(u_axis) - 0.75 * v_axis / np.linalg.norm(v_axis)
        wrong = session.apply_input_snap_pick(index["F003"], target, source="guard")
        right = session.apply_input_snap_pick(index["F005"], target, source="guard")
        record = session.records[index["F005"]]
        rows.append(("N", refused_arm and armed and not wrong and right and not session.input_snap_pick_active
                     and abs(float(record["input_offset_u_mm"]) - 1.5) < 1e-6 and abs(float(record["input_offset_v_mm"]) + 0.75) < 1e-6,
                     f"arm refused off an Input Port={refused_arm}; armed={armed}; other face refused={not wrong}; "
                     f"U/V = ({record['input_offset_u_mm']:.6g}, {record['input_offset_v_mm']:.6g}) for (1.5, -0.75)"))
        session.clear_input_snap_offsets()

        # P + T -- the Tk dialog over a fresh session
        app._refresh_open_3d_views = real_refresh
        app.open_optical_solid_face_role_editor(1)
        deadline = time.time() + 1.0      # the dialog resets its camera 80 ms after opening
        while time.time() < deadline:
            app.update()
            time.sleep(0.02)
        view = app._main_optical_solid_face_roles_dialog()._view
        s2 = view.session
        picked = []
        renderer = view.preview.renderer
        for i in range(len(s2.records)):
            face = s2.world_face(i)
            if face is None:
                continue
            renderer.SetWorldPoint(*np.asarray(face["centroid_world"], dtype=float), 1.0)
            renderer.WorldToDisplay()
            x, y, _z = renderer.GetDisplayPoint()
            hit, point = view.preview.pick(x, y)
            if hit is None:
                continue
            view.preview.click(x, y)
            _pump(app, 3)
            hit_face = s2.world_face(hit)
            n = np.asarray(hit_face.get("normal_world", (0, 0, 1)), dtype=float)
            off_plane = abs(float(np.dot(np.asarray(point) - np.asarray(hit_face["centroid_world"], dtype=float), n / np.linalg.norm(n))))
            picked.append((i, hit, s2.selection == [hit], off_plane))
        good = [p for p in picked if p[2] and p[3] < 0.2]
        rows.append(("P", len(picked) >= 2 and len(good) == len(picked),
                     f"{len(picked)} preview clicks hit a face; selected the hit face and on its plane: {len(good)} "
                     f"(max off-plane {max([p[3] for p in picked] or [0]):.3g} mm)"))

        cells = [list(view.tree.item(f"face_{i}", "values")) for i in range(len(s2.records))]
        wanted = [[view._wrap_cell_text(c, r[c]) for c in view.columns] for r in s2.rows()]
        view.tree.selection_set(f"face_{index['F005']}")
        view.tree.focus(f"face_{index['F005']}")
        _pump(app, 5)
        next(b for b in _all(view.window) if _text(b) == "Apply Form to Selected").invoke()
        _pump(app, 20)
        shown = str(view.validation_var.get())
        rows.append(("T", cells == wanted and shown.startswith("Applied") and shown == s2.validation,
                     f"table cells == session rows: {cells == wanted}; after Apply the label reads {shown[:60]!r}"))
        view.window.destroy()
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return rows


def fallback_checks() -> list:
    """M: the Matplotlib preview, as the dialog gets it when VTK/Tk is unavailable."""
    import time

    from KrakenOS.UI import layout_editor as le

    app = _open_prism_editor()
    try:
        le._load_3d_backends()
        le.vtkTkRenderWindowInteractor = None       # what an install without the VTK/Tk widget has
        app.open_optical_solid_face_role_editor(1)
        deadline = time.time() + 1.5
        while time.time() < deadline:
            app.update()
            time.sleep(0.02)
        view = app._main_optical_solid_face_roles_dialog()._view
        session = view.session
        axis = view.mpl_axis
        if axis is None:
            return [("M", False, f"VTK/Tk off: no Matplotlib preview ({view.preview_status_var.get()!r})")]
        drawn = len(axis.collections)
        status = str(view.preview_status_var.get())
        # click the projected centre of the LAST face through matplotlib's own event path
        from mpl_toolkits.mplot3d import proj3d
        from matplotlib.backend_bases import MouseEvent

        chosen = len(session.records) - 1
        centre = np.mean(session.to_world(session.face_source_triangles(chosen).reshape((-1, 3))), axis=0)
        px, py, _pz = proj3d.proj_transform(*centre, axis.get_proj())
        x, y = axis.transData.transform((px, py))
        mpl_canvas = axis.figure.canvas
        for name in ("button_press_event", "button_release_event"):
            MouseEvent(name, mpl_canvas, x, y, button=1)._process()
        app.update()
        selected = session.selected_index()
        ok = view.preview is None and drawn >= len(session.records) and selected is not None and "candidates=" in status
        return [("M", ok, f"VTK/Tk off: Matplotlib preview drew {drawn} face collections for {len(session.records)} "
                          f"faces ({status[:50]!r}); a click on F{chosen + 1}'s centre selected face index {selected}")]
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def _run(call: str) -> list:
    driver = (
        "import json, os\n"
        f"from KrakenOS.UI.validate_open3d_face_roles_session import {call.split('(')[0]}\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk/VTK teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=1200,
                              cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [("X", False, f"{call} timed out")]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return [tuple(row) for row in json.loads(line[len(RESULT_MARK):])]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return [("X", False, f"{call}: exit {proc.returncode}; " + " | ".join(tail))]


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP

    if not PRISM_42779_STEP.exists():
        return True, [f"SKIP = {PRISM_42779_STEP} absent"]
    if not os.environ.get("DISPLAY"):
        return True, ["SKIP = no DISPLAY"]
    rows = _run("vtk_checks()") + _run("fallback_checks()")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def _all(widget):
    yield widget
    for child in widget.winfo_children():
        yield from _all(child)


def _text(widget) -> str:
    try:
        return str(widget.cget("text"))
    except Exception:
        return ""


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
