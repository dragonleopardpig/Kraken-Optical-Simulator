"""Guard for bugs/0998: the hosted 3D inspector can be built with NO Tk window (docs/design_qt_migration.md phase 7f).

In the Qt shell the inspector draws into a Qt widget and takes its input from Qt (bugs/0906), but
it still made a Tk window -- withdrawn, never shown -- and built its Tk panels into it: 247 widgets
and 38 Tk variables nobody sees. `Kraken3DInspector(editor, vtk_host=..., tk_window=False)` builds
neither. The Qt shell asks for it only on request yet (`KRAKEN_QT_TK_FREE=inspector`,
`qt/tk_free.py`); the default is unchanged until the whole shell has been measured that way.

What the model asked of the Tk window, measured on a session in the Qt shell, was one thing:
whether it still exists. The inspector answers that itself now -- with a window, the window's
answer; without, "until it is closed".

And one thing was found that is not about the window: after an interactive lens swap the editor
says "Enter the field you want in the FOV dialog", having asked for that dialog on a Tk timer of
the inspector's window -- and nothing runs Tk timers under the Qt shell, so there the dialog never
opened. It is asked for on the inspector's host.

  W  in the Qt shell, on request: the inspector has no Tk window, and neither building it nor
     the session makes one Tk widget or Tk variable for it (as it always was: 247 widgets, 38
     variables, a withdrawn Toplevel); the 3D scene is up with the same actors
  S  the same inspector: after every step of one session its plain attributes -- about 200,
     the actors' addresses aside -- and the editor's -- the timings in its debug log aside --
     equal the ones of the inspector that has its Tk window; what only that one holds is its
     Tk widgets and two leftovers of its Tk panels, listed exactly
  L  it answers for itself and fails loudly: it exists until it is closed, and then it does not
     and the editor has forgotten it; a Tk call on it raises AttributeError; asked for without a
     shell's VTK widget it is refused; one built with __new__ still raises for `winfo_exists`
  F  the FOV dialog after a lens swap is asked for in the Qt shell, with the inspector's Tk
     window and without, as it is in Tk
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import traceback
from collections import Counter
from pathlib import Path

RESULT_MARK = "WINDOWLESS_RESULT "
SKIP_MARK = "WINDOWLESS_SKIP "
LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
ADDRESS = re.compile(r"Addr=0x[0-9a-f]+")
#: plain attributes only the inspector WITH its Tk window has: what its Tk panels left on it
WINDOW_ONLY_PLAIN = {"_open3d_toolbar_ray_count_entry", "_open3d_variable_thickness_vars"}
#: ... and the Tk objects it holds beside the window itself: its panels and their widgets. EXACT.
WINDOW_ONLY_OBJECTS = {
    "_discard_button", "_flag_bug_button", "_recorder_button", "_open3d_cad_target_menu", "_open3d_import_step_menu",
    "_open3d_iso_up_menu", "_open3d_orientation_menu", "_open3d_overlay_menu", "_open3d_placement_menu",
    "_open3d_left_restore_frame", "_open3d_right_restore_frame", "_open3d_live_panel_host", "_open3d_step_admin_panel_host",
    "_open3d_main_pane", "_open3d_viewport_host", "_open3d_live_controls_panel_instance", "_open3d_top_controls_panel_instance",
}
#: the editor's debug log carries how long things took
TIMED = {"debug_lines"}


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def _normal(value):
    """Plain data with the actors' addresses taken out: they are the process's."""
    if isinstance(value, str):
        return ADDRESS.sub("<actor>", value)
    if isinstance(value, list):
        return [_normal(item) for item in value]
    if isinstance(value, dict):
        items = [(_normal(key), _normal(item)) for key, item in value.items()]
        if items and all(key == "<actor>" for key, _item in items):
            return sorted(json.dumps(item, sort_keys=True) for _key, item in items)
        return dict(items)
    return value


def session(out: str) -> dict:
    """Drive the Qt shell's hosted inspector through one session; record it and the editor."""
    import tkinter as tk

    from KrakenOS.UI.validate_editor_without_tk_root import _canon, _digest

    made = Counter()
    phase = ["the editor"]
    widget_init, variable_init = tk.BaseWidget.__init__, tk.Variable.__init__

    def counted(kind, real):
        def init(self, *args, **options):
            made[f"{kind} for {phase[0]}"] += 1
            return real(self, *args, **options)
        return init

    tk.BaseWidget.__init__ = counted("widgets", widget_init)
    tk.Variable.__init__ = counted("variables", variable_init)

    from PySide6.QtWidgets import QMessageBox

    for name in ("information", "warning", "critical"):
        setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.qt.app import build

    app, window = build(["guard"])
    window.show()

    def settle(seconds: float = 0.6) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    settle(1.5)
    editor = window.editor
    editor.layout_files[LAYOUT.stem] = LAYOUT
    editor.load_layout_by_name(LAYOUT.stem, refresh=False)
    settle(1.0)
    phase[0] = "the inspector"
    inspector = window.build_inspector_view().inspector
    settle(2.5)
    made_building = dict(made)
    # the table overlays of the EDITOR's hidden Tk table are made again at each sync: not the inspector's
    phase[0] = "the session"

    def state(owner) -> dict:
        plain, objects = {}, []
        for key, value in list(owner.__dict__.items()):
            item = _canon(value)
            if item == "<object>":
                objects.append(key)
            else:
                item = _normal(item)
                plain[key] = item if len(json.dumps(item, default=str)) <= 3000 else {"<digest>": _digest(item)}
        return {"plain": plain, "objects": sorted(objects)}

    steps: list = []

    def record(label: str, result: str) -> None:
        steps.append([label, result, state(inspector), state(editor)])

    def step(label: str, call) -> None:
        try:
            call()
            result = "ok"
        except Exception as exc:
            where = " < ".join(frame.name for frame in traceback.extract_tb(exc.__traceback__)[-1:-5:-1])
            result = f"RAISED {type(exc).__name__}: {str(exc)[:140]} @ {where}"
        settle(0.8)
        record(label, result)

    record("built", "ok")
    step("refresh from the editor", inspector.refresh_from_editor)
    step("rays off", lambda: (inspector.show_rays_var.set(False), inspector._on_show_rays_changed()))
    step("rays on", lambda: (inspector.show_rays_var.set(True), inspector._on_show_rays_changed()))
    step("commit a cell", lambda: editor.commit_cell(3, "thickness", "7.25"))
    step("select a row", lambda: editor._select_table_indices([3], focus_index=3))
    step("a thickness is a variable", lambda: inspector._open3d_set_variable_thickness(3, True))
    step("and is not", lambda: inspector._open3d_set_variable_thickness(3, False))
    step("undo", editor.undo)
    step("refresh the plot", editor.refresh_plot)
    actors = len(inspector._actor_by_key)
    available = bool(inspector.available)

    # ---- the FOV dialog the model promises after a lens swap ------------------------------------
    asked: list = []
    inspector._open_quick_estimation_fov_popup = lambda plane: asked.append(plane)      # noted, not opened
    said = editor._prompt_fov_solve_after_swap(True)
    settle(1.5)
    del inspector._open_quick_estimation_fov_popup

    # ---- what it answers for itself ----------------------------------------------------------------
    owned = inspector.__dict__.get("window")
    window_state = "no window" if owned is None else f"{type(owned).__name__}, {owned.state()}"
    loud = {}
    for name in ("title", "after", "winfo_toplevel", "geometry", "tk"):
        try:
            getattr(inspector, name)
            loud[name] = "answered"
        except AttributeError:
            loud[name] = "AttributeError"
    try:
        Kraken3DInspector(editor, tk_window=False)
        refused = "built"
    except ValueError as exc:
        refused = f"ValueError: {exc}"
    try:
        Kraken3DInspector.__new__(Kraken3DInspector).winfo_exists()
        bare = "answered"
    except AttributeError:
        bare = "AttributeError"
    open_before = bool(inspector.winfo_exists())
    try:
        inspector._on_close()
        closed = "ok"
    except Exception as exc:
        closed = f"RAISED {type(exc).__name__}: {exc}"
    settle(0.5)
    try:
        open_after = bool(inspector.winfo_exists())
    except Exception as exc:        # a destroyed Tk application cannot be asked
        open_after = f"cannot be asked ({type(exc).__name__})"
    Path(out).write_text(json.dumps({"steps": steps}), encoding="utf-8")
    return {"made building": {key: count for key, count in made_building.items() if "the inspector" in key},
            "made in the session": {key: count for key, count in made.items() if "the session" in key},
            "window": window_state, "actors": actors, "available": available, "loud": loud, "refused": refused, "bare": bare,
            "open before": open_before, "closed": closed, "open after": open_after,
            "forgotten": editor.__dict__.get("_three_d_inspector") is None, "said": said.strip(), "asked": asked,
            "steps": len(steps), "requested": os.environ.get("KRAKEN_QT_TK_FREE", "")}


def tk_prompt() -> dict:
    """The same promise in the Tk interface: is the FOV dialog asked for there?"""
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()

    def settle(seconds: float) -> None:
        end = time.time() + seconds
        while time.time() < end:
            editor.update()
            time.sleep(0.02)

    settle(0.8)
    editor.layout_files[LAYOUT.stem] = LAYOUT
    editor.load_layout_by_name(LAYOUT.stem, refresh=False)
    settle(0.5)
    editor.open_3d_view()
    settle(2.5)
    inspector = editor._three_d_inspector
    asked: list = []
    inspector._open_quick_estimation_fov_popup = lambda plane: asked.append(plane)
    said = editor._prompt_fov_solve_after_swap(True)
    settle(1.5)
    return {"said": said.strip(), "asked": asked, "window": type(inspector.window).__name__}


def compare(window_path: str, free_path: str) -> dict:
    with_window = json.loads(Path(window_path).read_text(encoding="utf-8"))["steps"]
    without = json.loads(Path(free_path).read_text(encoding="utf-8"))["steps"]
    differ: dict = {}
    results, only_plain, only_objects, compared = [], set(), set(), 0
    for (label, result_a, inspector_a, editor_a), (label_b, result_b, inspector_b, editor_b) in zip(with_window, without):
        if label != label_b or result_a != "ok" or result_b != "ok":
            results.append((label, result_a, label_b, result_b))
        for which, a, b in (("inspector", inspector_a, inspector_b), ("editor", editor_a, editor_b)):
            plain_a, plain_b = a["plain"], b["plain"]
            for key in sorted(set(plain_a) | set(plain_b)):
                if key in plain_a and key in plain_b:
                    compared += 1
                    if plain_a[key] != plain_b[key] and not (which == "editor" and key in TIMED):
                        differ.setdefault(f"{which}.{key}", []).append(label)
                elif which == "inspector" and key in plain_a and key not in b["objects"]:
                    only_plain.add(key)
                elif key in plain_b and key not in a["objects"]:
                    differ.setdefault(f"{which}.{key}: only without the window", []).append(label)
            if which == "inspector":
                only_objects |= set(a["objects"]) - set(b["objects"]) - set(plain_b)
                for key in set(b["objects"]) - set(a["objects"]) - set(plain_a):
                    differ.setdefault(f"{which}.{key}: an object only without the window", []).append(label)
    return {"differ": differ, "results": results, "only_plain": sorted(only_plain), "only_objects": sorted(only_objects),
            "steps": [len(with_window), len(without)], "compared_per_step": compared // max(len(without), 1)}


def checks(window_meta: dict, free_meta: dict, result: dict, tk_meta: dict) -> list:
    def claim_w():
        return (free_meta["window"] == "no window" and free_meta["made building"] == {} and free_meta["available"]
                and free_meta["requested"] == "inspector" and window_meta["requested"] == ""
                and window_meta["window"] == "Kraken3DInspectorWindow, withdrawn"
                and window_meta["made building"] == {"widgets for the inspector": 247, "variables for the inspector": 38}
                and free_meta["actors"] == window_meta["actors"] > 20 and window_meta["available"],
                f"on request the Qt shell's inspector has {free_meta['window']} and building it made Tk objects "
                f"{free_meta['made building'] or 'none'} (as it always was: {window_meta['window']}, "
                f"{window_meta['made building']}); the 3D scene is up in both with {free_meta['actors']} actors")

    def claim_s():
        return (not result["differ"] and not result["results"] and result["steps"][0] == result["steps"][1] >= 10
                and set(result["only_plain"]) == WINDOW_ONLY_PLAIN and set(result["only_objects"]) == WINDOW_ONLY_OBJECTS
                and result["compared_per_step"] >= 450,
                f"{result['steps'][1]} steps, every one without an error in both ({result['results'] or 'none raised'}); about "
                f"{result['compared_per_step']} plain attributes of the inspector and the editor compared at each; they differ "
                f"in {sorted(result['differ']) or 'none'}; only the inspector with its Tk window holds: the plain "
                f"{result['only_plain']} and {len(result['only_objects'])} Tk objects"
                + ("" if set(result["only_objects"]) == WINDOW_ONLY_OBJECTS else
                   f" -- NOT the listed ones: {sorted(set(result['only_objects']) ^ WINDOW_ONLY_OBJECTS)}"))

    def claim_l():
        loud = free_meta["loud"]
        return (free_meta["open before"] is True and free_meta["closed"] == "ok" and free_meta["open after"] is False
                and free_meta["forgotten"] and set(loud.values()) == {"AttributeError"} and len(loud) == 5
                and free_meta["refused"].startswith("ValueError") and free_meta["bare"] == "AttributeError"
                and window_meta["open before"] is True and window_meta["closed"] == "ok" and window_meta["forgotten"]
                and set(window_meta["loud"].values()) == {"answered"} and window_meta["bare"] == "AttributeError",
                f"without a Tk window the inspector says it exists ({free_meta['open before']}) until it is closed "
                f"({free_meta['closed']}), then that it does not ({free_meta['open after']} -- with the window: "
                f"{window_meta['open after']}), and the editor has forgotten it ({free_meta['forgotten']}); Tk calls on it: "
                f"{loud}; without a shell's VTK widget: {free_meta['refused']}; one built with __new__: {free_meta['bare']}")

    def claim_f():
        promise = "Enter the field you want in the FOV dialog and Solve for Thickness."
        got = {"Tk": (tk_meta["said"], tk_meta["asked"]), "Qt": (window_meta["said"], window_meta["asked"]),
               "Qt, no Tk window": (free_meta["said"], free_meta["asked"])}
        return (all(value == (promise, ["object"]) for value in got.values()),
                f"after a lens swap the model says {promise!r} and the object-plane FOV dialog is asked for: "
                + "; ".join(f"{shell}: {asked or 'never'}" for shell, (_said, asked) in got.items()))

    return _claims((("W", claim_w), ("S", claim_s), ("L", claim_l), ("F", claim_f)))


def _run(call: str, claim: str, tk_free: str) -> dict | list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        + ("import PySide6\n" if "session" in call else "")
        + "from KrakenOS.UI.validate_inspector_without_tk_window import session, tk_prompt\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk/Qt/VTK teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    env["PYTHONHASHSEED"] = "1"
    # ONE analysis worker, whatever memory is free. How many the model starts is capped by the
    # machine's free memory at that moment, and the parallel trace agrees with the single one only
    # to the last bits (0.4442048847402281 / ...22785): in a loaded gate on a 14 GB machine the two
    # sessions were given different counts and five trace results "differed" (the full gate of
    # 2026-10-10, in the editor's guard). The comparison is about Tk, not about the machine.
    env["KRAKEN_ANALYSIS_WORKER_MB"] = "1000000"
    env.pop("KRAKEN_QT_TK_FREE", None)
    if tk_free:
        env["KRAKEN_QT_TK_FREE"] = tk_free
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [[claim, False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-8:]
    return [[claim, False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    rows: list = []
    with tempfile.TemporaryDirectory() as folder:
        window_path, free_path = str(Path(folder) / "window.json"), str(Path(folder) / "free.json")
        metas = [_run(f"session({window_path!r})", "S", ""), _run(f"session({free_path!r})", "W", "inspector"),
                 _run("tk_prompt()", "F", "")]
        if any(isinstance(meta, list) for meta in metas):
            for meta in metas:
                rows += meta if isinstance(meta, list) else []
        else:
            try:
                rows += checks(metas[0], metas[1], compare(window_path, free_path), metas[2])
            except Exception as exc:
                rows.append(["S", False, f"comparing the two sessions raised {type(exc).__name__}: {exc}"])
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
