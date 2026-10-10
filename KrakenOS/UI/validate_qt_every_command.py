"""Guard for bugs/1002: EVERY command of the Qt shell is triggered, in the shell as it starts.

The Qt shell starts without Tk since bugs/1000: a Tk call that is still made somewhere no longer
reaches a hidden window nobody sees, it raises. A command no guard triggers in the Qt shell is
where such a call can still sit -- and of the shell's 102 commands, 26 were triggered by none of
the gate's 87 guards that build a Qt shell (measured, bugs/1002).

This starts the shell with nothing asked for, the way `qt.app.run` does (the real inspector as the
3D scene, the 2D plot beside it), loads a scene, and goes through `qt.actions.ACTIONS` -- every
command the ribbon and its dropdowns offer -- triggering each one the way a click does. Every
question a command asks is answered "cancel", so what is held is each command's FIRST response:

  T  the shell under test is the default one (no Tk), its 3D scene is the inspector, and the
     table below lists the registry's commands exactly -- a new command has to be entered here
  N  no command raises, and none reaches Tk: not a Tk dialog function, not a Tk root, a Tk
     window, a Tk widget or a Tk variable -- and no Tk root exists at the end
  F  each command's first response is the one the table gives: the question it asks through the
     UI host (with its title), the message it shows, the window it opens, the document it hands
     to the browser, what it reports in the status line, and what it changed -- rows, the layout
     file, a check mark, the 3D toolbar, the panels, the camera
  Q  every command answers: the ones that do nothing one can see on this scene are exactly the
     listed ones, each with its reason
  S  nothing leaves the process: the scene file is the bytes it was (Save wrote a copy), no
     flag bundle and no picture appeared under attachment/, the formula sheet was not written to
     the home folder
  Z  Quit closes the window
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
from pathlib import Path

RESULT_MARK = "QTEVERYCOMMAND_RESULT "
SKIP_MARK = "QTEVERYCOMMAND_SKIP "
SCENE = Path("KrakenOS/common_optical_layouts/native_variable_breadth_example.py")   # in git
LAST = ("quit",)                     # closes the window: after everything else

#: a command that does nothing one can see ON THIS SCENE, and why. May only shrink.
QUIET = {
    "clear_marks": "the scene has no optimization mark to clear (validate_qt_ribbon triggers it on one that has)",
}

#: status texts that are a view catching up with the model, not a command's own answer
VIEW_CATCHING_UP = ("Plot refreshed", "3D inspector updated", "3D scene ready")

#: command -> its first response on SCENE with every question answered "cancel". Recorded with
#: `python bugs/1002_trigger_every_qt_command.py --table`, read through before it was pasted.
FIRST = {
    'open': 'askopenfilename: Open Kraken layout',
    'reload': 'status: Loaded native_variable_breadth_example',
    'save': 'status: Saved native_variable_breadth_example.py',
    'save_as': 'asksaveasfilename: Save Kraken layout',
    'reset': 'status: Reset complete. Table contains only Object and Image; click Update to trace. [file, rows]',
    'import_zemax': 'askopenfilename: Import Zemax prescription or NSC source file',
    'import_zemax_wavefront': 'askopenfilename: Import Zemax Wavefront Map text export',
    'import_cad_solid': 'askopenfilename: Import Optical CAD/STL Solid',
    'import_lens_step': 'askopenfilename: Import lens STEP',
    'import_camera_step': 'askopenfilename: Import camera STEP',
    'import_led_step': 'askopenfilename: Import LED STEP',
    'export_3d_step': 'asksaveasfilename: Export 3D Assembly STEP',
    'export_3d_dxf': 'asksaveasfilename: Export Current 3D View as DXF',
    'export_lens_drawing': 'modal: LensDrawingPropertiesDialog',
    'export_wavefront_csv': ('showinfo: Export Wavefront CSV -- Run Wavefront or Zernike analysis before'
                             ' exporting wavefront samples'),
    'export_zernike_csv': 'showinfo: Export Zernike CSV -- Run Zernike analysis before exporting coefficients',
    'export_path_psf_csv': 'showinfo: Export Path PSF CSV -- No detector hits for All paths',
    'export_path_mtf_csv': 'showinfo: Export Path MTF CSV -- No detector hits for All paths',
    'export_detector_map_csv': 'showinfo: Export Detector Map CSV -- No detector hits for All paths',
    'export_coherent_detector_csv': 'showinfo: Export Coherent Detector CSV -- No detector path hits for All paths',
    'export_branch_field_csv': 'showinfo: Export Branch Field CSV -- No detector path hits for All paths',
    'mtf_from_image': 'window: MtfFromImageDialog: Measure MTF from Image',
    'reset_camera': 'changes [camera]',
    'redraw': 'status: 3D inspector updated',
    'plot_2d': 'changes [panels]',
    'trace_now': 'status: Rays traced.',
    'show_rays': 'bar: Rays shown. [checks]',
    'clean_scene': ("bar: Clean 3D scene -- F11, or the button by the ribbon's fold arrow, puts the"
                    ' toolbars and pan [checks, panels, toolbar]'),
    'hide_panels': 'changes [checks, panels]',
    'toolbar_3d': 'changes [checks, toolbar]',
    'inspector': 'changes [scene, toolbar]',
    'paraxial_matrix': 'window: ReportDialog: Paraxial Matrix Report',
    'branch_gaussian_q': 'window: ReportDialog: Branch Gaussian Q Report',
    'detector_aperture': 'window: ReportDialog: Detector Aperture Report',
    'branch_throughput': 'window: ReportDialog: Path Throughput Report',
    'source_illumination': 'window: ReportDialog: Source Illumination Report',
    'gaussian_beam': 'window: ReportDialog: Gaussian Beam Report',
    'paraxial_calculator': 'window: ParaxialCalculatorDialog: Paraxial Calculator',
    'ray_inspector': 'window: ReportDialog: Ray Inspector',
    'trace_paths': 'window: ReportDialog: Trace Path Inspector',
    'nonseq_scene_graph': 'window: ReportDialog: Non-Sequential Scene Graph',
    'undo': 'status: Undo applied. [file, rows]',
    'redo': 'status: Redo applied. [file, rows]',
    'copy_rows': 'status: Select one or more component surface rows before copying.',
    'paste_rows': 'status: No copied KrakenOS surface rows are available to paste.',
    'beam_splitter': 'showinfo: Beam Splitter -- Select a Beam Splitter row first',
    'diffuse_scatter': 'showinfo: Diffuse / BRDF -- Select a Diffuse Object row first',
    'error_map': 'showinfo: Error Map -- Select a surface row first',
    'coating_material': 'showinfo: Coating / Material -- Select a surface row first',
    'advanced_surface': 'showinfo: Advanced Surface -- Select a surface row first',
    'detector_settings': 'showinfo: Detector Settings -- Select a surface row first',
    'scene_target': 'showinfo: Scene Target -- Select a surface row or scene target first',
    'path_local_pose': 'showinfo: Path-Local Pose -- Select one placed path element or stock-lens block first',
    'element_settings': 'showinfo: Element Settings -- Select a non-Object/non-Image row or element group first',
    'scene_sources': 'window: RowFormDialog: Scene Source Manager',
    'glass_catalog': 'window: RowFormDialog: Glass Catalog Browser',
    'stock_lens': 'window: RowFormDialog: Import Stock Lens',
    'lens_drawing_properties': 'modal: LensDrawingPropertiesDialog',
    'add_path_component': 'showinfo: Path Component -- Choose a traced Path view first',
    'add_path_stock_lens': 'showinfo: Path Stock Lens -- Choose a traced Path view first',
    'inspection_cell': 'window: RowFormDialog: Inspection Cell (6 stations)',
    'source_edit': 'showinfo: Edit Source -- Pick a scene source to edit',
    'inspection_part': 'window: RowFormDialog: Inspection Part (3D object)',
    'surface_shape': 'showinfo: Surface Shape Builder -- Select a surface row first',
    'catalog_matcher': 'window: RowFormDialog: Camera + Lens Matcher',
    'system_selection': 'window: RowFormDialog: System Selection Calculator',
    'optical_solid_diagnostics': 'showerror: Optical CAD/STL Solid Diagnostics -- Could not build the report',
    'missing_assets': 'status: No missing CAD files in this layout.',
    'face_roles': 'showinfo: Assign CAD/STL Optical Faces -- Select an STL solid row first',
    'galvo_scan': 'showinfo: Galvo Scan Overlay -- No mirror row selected',
    'grating_settings': 'showinfo: Grating Settings -- Select a surface row first',
    'tolerance_preset': 'window: RowFormDialog: Save Tolerance Solve Preset',
    'apply_tolerance_preset': ('showinfo: Apply Tolerance Solve Preset -- No saved tolerance solve presets are'
                               ' available in this layout'),
    'tolerance_monte_carlo': 'askinteger: Tolerance Monte Carlo',
    'export_tolerance_monte_carlo_csv': 'showinfo: Export Tolerance Monte Carlo -- Run Tolerance Monte Carlo Report first',
    'tolerance_worst_sample': 'showerror: Tolerance Worst-Sample Comparison -- Run Tolerance Monte Carlo Report first',
    'export_tolerance_comparison_csv': 'showinfo: Export Tolerance Comparison -- Run Tolerance Worst-Sample Comparison first',
    'tolerance_stackup': 'showinfo: Tolerance Stack-Up Dashboard -- Run Tolerance Monte Carlo Report first',
    'export_tolerance_stackup_csv': 'showinfo: Export Tolerance Stack-Up -- Run Tolerance Monte Carlo Report first',
    'tolerance_compensator': 'showinfo: Tolerance Compensator Sweep -- Run Tolerance Monte Carlo Report first',
    'export_tolerance_compensator_csv': 'showinfo: Export Tolerance Compensator -- Run Tolerance Compensator Sweep first',
    'tolerance_multi_compensator': 'showinfo: Tolerance Multi-Compensator Solve -- Run Tolerance Monte Carlo Report first',
    'export_tolerance_multi_compensator_csv': ('showinfo: Export Tolerance Multi-Compensator -- Run Tolerance Multi-Compensator'
                                               ' Solve first'),
    'export_tolerance_overlay_csv': 'showinfo: Export Tolerance Overlay -- Run Tolerance Monte Carlo Report first',
    'about': 'showinfo: KrakenOS -- Qt shell -- The Qt front end of the Tk->Qt migration (docs/design_qt_migration.md)',
    'interface_preference': 'window: RowFormDialog: Interface Preference',
    'flag_bug': 'window: FlagDescriptionDialog: Flag: flag_<stamp>',
    'clear_cad_axis_offsets': 'status: CAD STEP optical-axis offsets cleared.',
    'clear_step_imports': 'status: Camera/lens/optical/LED STEP imports cleared.',
    'place_cad_solid': 'showinfo: Place/Orient Selected CAD/STL Solid -- Select an STL solid row first',
    'refresh_plot': 'status: Plot refreshed',
    'folded_assembly': 'status: This layout carries no display_fold_spec -- the folded view needs the per-arm fold planes',
    'atmosphere_settings': 'window: AtmosphereSettingsDialog: Atmospheric Settings',
    'benchmark_psf_mtf': 'status: Benchmark PSF/MTF completed',
    'copy_phase2_report': 'status: Phase 2 report copied to clipboard',
    'copy_wavefront_fit': 'status: Run Zernike analysis before copying the wavefront fit report.',
    'clear_zemax_wavefront': 'status: Zemax Wavefront Map reference cleared.',
    'clear_marks': 'nothing',
    'formula_sheet': 'opens a document',
    'manual_index': 'opens a document',
    'copy_debug': 'status: All text copied to clipboard',
    'quit': 'changes [panels, toolbar]',
}


def _head(text: str) -> str:
    """The part of a status text that does not depend on the machine: up to a path, a count of
    workers, the clipboard tool."""
    for cut in (": ", " | ", " ("):
        text = text.split(cut, 1)[0]
    return text.strip()[:90]


def _sentence(message: str) -> str:
    line = str(message).strip().splitlines()[0] if str(message).strip() else ""
    return line.split(". ", 1)[0].rstrip(".:")[:90]


def own_text(entry: dict) -> str:
    """What the command itself said: its first status text that is not a view catching up -- in
    the editor's status line, else in the window's status bar -- else the first text there is."""
    lines = [[_head(text) for text in entry[kind]] for kind in ("status_all", "bar_all")]
    for kind, heads in zip(("status", "bar"), lines):
        own = next((head for head in heads if head and head not in VIEW_CATCHING_UP), "")
        if own:
            return f"{kind}: {own}"
    return next((f"{kind}: {heads[0]}" for kind, heads in zip(("status", "bar"), lines) if heads and heads[0]), "")


def first_response(entry: dict) -> str:
    """One line for what a command did first, and what it changed."""
    if entry["raised"]:
        return "RAISED " + entry["raised"][0][0]
    if entry["tk"]:
        return "TK " + entry["tk"][0][0]
    if not entry["enabled"]:
        return "disabled"
    changed = entry["changed"]
    tail = f" [{', '.join(changed)}]" if changed else ""
    if entry["asked"]:
        kind, title, message = entry["asked"][0]
        said = f" -- {_sentence(message)}" if kind.startswith("show") else ""
        return f"{kind}: {title}{said}{tail}"
    if entry["modal"]:
        return f"modal: {entry['modal'][0][0]}{tail}"
    if entry["windows"]:
        kind, title = entry["windows"][0]
        return f"window: {kind}: " + re.sub(r"flag_\d+_\d+_\d+", "flag_<stamp>", title) + tail
    if entry["opened"]:
        return f"opens a document{tail}"
    said = own_text(entry)
    if said:
        return f"{said}{tail}"
    return f"changes{tail}" if changed else "nothing"


def qt_session(scene: str = str(SCENE)) -> dict:
    """Start the Qt shell as the app does, trigger every command, return what each one did."""
    import pathlib
    import shutil
    import tkinter
    import tkinter.filedialog as tk_filedialog
    import tkinter.messagebox as tk_messagebox
    import tkinter.simpledialog as tk_simpledialog
    import webbrowser

    scene_path = Path(scene)
    folder = Path(tempfile.mkdtemp(prefix="every_command_"))
    layout = folder / scene_path.name
    shutil.copy2(scene_path, layout)                 # Save must not reach the real file
    scene_bytes = scene_path.read_bytes()
    # "status" / "bar": every text written to the editor's status line / the window's status bar,
    # in order -- the FIRST is the command's own, a later one is a view catching up
    events: dict = {"raised": [], "asked": [], "tk": [], "modal": [], "opened": [], "status": [], "bar": []}

    def note(kind, *what) -> None:
        events[kind].append([str(item)[:200] for item in what])

    def said(kind, text) -> None:
        if str(text).strip():
            events[kind].append(str(text)[:200])

    # ---- nothing leaves the process, and every Tk object is seen ------------------------------------
    for name in ("open", "open_new", "open_new_tab"):
        setattr(webbrowser, name, (lambda n: lambda url, *_a, **_k: note("opened", f"webbrowser.{n}", url) or True)(name))
    for module, names in ((tk_messagebox, ("showinfo", "showwarning", "showerror", "askyesno", "askokcancel",
                                           "askyesnocancel", "askretrycancel", "askquestion")),
                          (tk_simpledialog, ("askinteger", "askfloat", "askstring")),
                          (tk_filedialog, ("asksaveasfilename", "askopenfilename", "askopenfilenames", "askdirectory"))):
        for name in names:
            setattr(module, name, (lambda m, n: lambda *a, **_k: note("tk", f"{m}.{n}", *a[:1]))(module.__name__, name))
    for owner in (tkinter.Tk, tkinter.BaseWidget, tkinter.Variable):
        def made(self, *args, _made=owner.__init__, **kwargs):
            note("tk", f"tkinter.{type(self).__name__}()", "".join(traceback.format_stack(limit=5)[:-1])[-160:])
            return _made(self, *args, **kwargs)
        owner.__init__ = made
    sys.excepthook = lambda kind, value, tb: note(
        "raised", f"{kind.__name__}: {value}", "".join(traceback.format_tb(tb)[-2:])[-300:])

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QDialog, QDockWidget

    from KrakenOS.UI import open3d_inspector
    from KrakenOS.UI.qt.actions import ACTIONS, CHECKABLE
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.qt.tk_free import tk_free_level
    from KrakenOS.UI.uihost import host_of

    attachment = Path(open3d_inspector.ATTACHMENT_DIR)
    outside = {"flags": attachment / "recorded_bug_repros", "picture": attachment / "2D.png",
               "formula": Path.home() / ".cache" / "krakenos" / "optics_formula_sheet.html"}

    def outside_state() -> dict:
        return {"flags": len(list(outside["flags"].glob("flag_*"))) if outside["flags"].is_dir() else 0,
                "picture": outside["picture"].stat().st_mtime_ns if outside["picture"].exists() else None,
                "formula": outside["formula"].stat().st_mtime_ns if outside["formula"].exists() else None}

    outside_before = outside_state()
    open3d_inspector.ATTACHMENT_DIR = folder         # a flag's bundle goes to the temp folder
    app, window = build(["guard"])
    window.show()
    window.build_scene()                             # as `qt.app.run` starts: the real inspector, central
    app.processEvents()
    editor = window.editor

    from KrakenOS.UI.services import layout_analysis_display

    layout_analysis_display.AUTO_PLOT_PATH = folder / "2D.png"     # after the editor's import (bugs/0999)
    redirected = Path(layout_analysis_display.AUTO_PLOT_PATH).parent == folder
    type(editor)._open_document_with_system_viewer = staticmethod(
        lambda path: note("opened", "system viewer", path) or True)

    host = host_of(window)
    cancel = {"showinfo": None, "showwarning": None, "showerror": None, "askyesno": False, "askokcancel": False,
              "askyesnocancel": None, "askretrycancel": False, "askquestion": "no", "askopenfilename": "",
              "askopenfilenames": (), "asksaveasfilename": "", "askdirectory": "", "askstring": None,
              "askinteger": None, "askfloat": None}
    for name, answer in cancel.items():
        def ask(*args, _n=name, _a=answer, **options):
            title = options.get("title") or (args[0] if args else "")
            message = options.get("message") or (args[1] if len(args) > 1 else "")
            note("asked", _n, title, message)
            return _a
        setattr(host, name, ask)

    def close_modal() -> None:
        widget = app.activeModalWidget()
        if widget is not None:
            note("modal", type(widget).__name__, widget.windowTitle())
            widget.reject() if isinstance(widget, QDialog) else widget.close()

    watchdog = QTimer()
    watchdog.timeout.connect(close_modal)
    watchdog.start(150)

    def settle(idle: float = 0.6, limit: float = 20.0) -> None:
        """Run the event loop until it has been IDLE for `idle` seconds: a busy machine makes a
        handler slow, and slow time is not idle time."""
        quiet, began = 0.0, time.time()
        while quiet < idle and time.time() - began < limit:
            start = time.time()
            app.processEvents()
            spent = time.time() - start
            time.sleep(0.01)
            quiet = quiet + 0.01 + spent if spent < 0.02 else 0.0

    def load() -> None:
        window.load_layout_path(layout)
        settle(0.4)

    editor.status_var.trace_add("write", lambda *_a: said("status", editor.status_var.get()))
    window.statusBar().messageChanged.connect(lambda text: said("bar", text))
    actions = window.action_manager.actions
    inspector = window._scene_inspector()
    camera = inspector._renderer.GetActiveCamera() if inspector is not None else None

    def state() -> dict:
        return {"rows": len(editor.rows), "file": str(getattr(editor, "current_layout_file", "")),
                "checks": {name: actions[name].isChecked() for name in CHECKABLE},
                "toolbar": bool(getattr(getattr(window.inspector_view, "toolbar", None), "isVisible", lambda: False)()),
                # on show: a panel tabbed BEHIND another is "visible" to Qt and has nothing on screen
                "panels": sorted(dock.objectName() for dock in window.findChildren(QDockWidget)
                                 if dock.isVisible() and not dock.visibleRegion().isEmpty()),
                "scene": "inspector" if window.scene_stack.currentWidget() is window.inspector_host else "preview",
                "camera": [round(value, 2) for value in camera.GetFocalPoint()] if camera is not None else []}

    def camera_away() -> None:                       # the scene pushed out of the view
        focal, position = camera.GetFocalPoint(), camera.GetPosition()
        camera.SetFocalPoint(focal[0] + 5000.0, focal[1], focal[2])
        camera.SetPosition(position[0] + 5000.0, position[1], position[2])

    def plot_behind() -> None:                       # another panel of its tab group in front of it
        window.dock_manager["SystemDock"].raise_()

    #: what has to be there for a command to have something to do
    prepare = {
        "undo": lambda: actions["reset"].trigger(),                  # a change to take back
        "reset_camera": camera_away,
        "plot_2d": plot_behind,
        "inspector": lambda: window.scene_stack.setCurrentWidget(window.viewport_host),
    }
    keep_scene = {"redo"}                            # Redo is for the Undo before it: no fresh scene between

    def visible_windows() -> set:
        return {widget for widget in app.topLevelWidgets() if widget.isVisible()}

    load()
    baseline_rows = len(editor.rows)
    commands: dict = {}
    order = [entry for entry in ACTIONS if entry[0] not in LAST] + [entry for entry in ACTIONS if entry[0] in LAST]
    for name, text, _shortcut, target, _tip in order:
        if name not in keep_scene and (len(editor.rows) != baseline_rows
                                       or str(getattr(editor, "current_layout_file", "")) != str(layout)):
            load()                                    # the command before this one changed the scene
        if name in prepare:
            prepare[name]()
            settle(0.4)
        editor.status_var.set("")
        window.statusBar().clearMessage()
        for kind in events:
            events[kind].clear()
        before, shown = state(), visible_windows()
        enabled = bool(actions[name].isEnabled())
        home = pathlib.Path.home
        pathlib.Path.home = classmethod(lambda cls: folder)          # the formula sheet's cache folder
        started = time.time()
        try:
            actions[name].trigger()
            settle()
        except Exception as exc:                      # a slot's exception is printed by Qt; this is the rest
            note("raised", f"{type(exc).__name__}: {exc}", traceback.format_exc()[-300:])
        finally:
            pathlib.Path.home = home
        seconds = time.time() - started
        after = state()
        appeared = list(visible_windows() - shown)
        windows = [[type(widget).__name__, widget.windowTitle()[:80]] for widget in appeared]
        for widget in appeared:
            widget.close()
        changed = sorted(key for key in before if before[key] != after[key])
        commands[name] = {
            "text": text.replace("&", ""), "target": target, "seconds": round(seconds, 2), "enabled": enabled,
            "raised": list(events["raised"]), "asked": list(events["asked"]), "tk": list(events["tk"]),
            "modal": list(events["modal"]), "opened": list(events["opened"]), "windows": windows, "changed": changed,
            "status_all": list(events["status"]), "bar_all": list(events["bar"]),
        }
        if name in CHECKABLE and name not in LAST:    # put a check mark back as it was
            actions[name].trigger()
        settle(0.2)
    return {
        "mode": tk_free_level(), "inspector": inspector is not None, "redirected": redirected,
        "registry": [entry[0] for entry in ACTIONS], "commands": commands,
        "first": {name: first_response(entry) for name, entry in commands.items()},
        "window_visible_after_quit": bool(window.isVisible()),
        "tk_default_root": repr(getattr(tkinter, "_default_root", None)),
        "scene_untouched": scene_path.read_bytes() == scene_bytes,
        "saved_copy": layout.exists() and layout.read_bytes() != b"",
        "outside_before": outside_before, "outside_after": outside_state(),
        "flag_folder_is_temp": (folder / "recorded_bug_repros").is_dir(),
        "formula_in_temp": (folder / ".cache" / "krakenos" / "optics_formula_sheet.html").exists(),
    }


def checks(result: dict) -> list:
    commands, first, registry = result["commands"], result["first"], result["registry"]

    def claim_t():
        missing = [name for name in registry if name not in FIRST]
        gone = [name for name in FIRST if name not in registry]
        return (result["mode"] == "all" and result["inspector"] and result["redirected"] and not missing and not gone
                and len(registry) == len(set(registry)) == len(commands) > 90,
                f"the shell started with nothing asked for is the Tk-free one (level {result['mode']!r}), its 3D scene "
                f"the inspector {result['inspector']}; the registry has {len(registry)} commands and the table lists "
                f"each: not in the table {missing or 'none'}, in the table but gone {gone or 'none'}")

    def claim_n():
        raised = {name: entry["raised"][0][0] for name, entry in commands.items() if entry["raised"]}
        tk = {name: entry["tk"][0][0] for name, entry in commands.items() if entry["tk"]}
        return (not raised and not tk and result["tk_default_root"] == "None" and len(commands) > 90,
                f"of {len(commands)} commands triggered, raised: {raised or 'none'}; reached Tk (a dialog function, "
                f"a root, a window, a widget, a variable): {tk or 'none'}; the Tk root at the end: "
                f"{result['tk_default_root']}")

    def claim_f():
        wrong = [f"{name}: {first.get(name)!r}, the table has {expected!r}" for name, expected in FIRST.items()
                 if first.get(name) != expected]
        kinds: dict = {}
        for response in first.values():
            kind = response.split(":", 1)[0].split(" [", 1)[0]
            kinds[kind] = kinds.get(kind, 0) + 1
        return (not wrong and len(FIRST) > 90,
                f"each of {len(FIRST)} commands answers as the table says -- by kind {dict(sorted(kinds.items()))}"
                + (f"; NOT as the table says ({len(wrong)}): " + " ;; ".join(wrong[:6]) if wrong else ""))

    def claim_q():
        quiet = sorted(name for name, response in first.items() if response in ("nothing", "disabled"))
        return (quiet == sorted(QUIET) and all(QUIET.values()),
                f"{len(first) - len(quiet)} of {len(first)} commands do something one can see on this scene; the ones "
                f"that do not: {quiet} (listed, each with its reason: {sorted(QUIET)})")

    def claim_s():
        before, after = result["outside_before"], result["outside_after"]
        flag_bug = commands.get("flag_bug", {})
        flag = [_head(text) for text in flag_bug.get("status_all", []) + flag_bug.get("bar_all", [])]
        return (result["scene_untouched"] and result["saved_copy"] and before == after and result["flag_folder_is_temp"]
                and result["formula_in_temp"] and first.get("save", "").startswith("status: Saved")
                and "Flagged bug" in flag and flag[-1:] == ["Flag discarded"],
                f"the scene file is the bytes it was {result['scene_untouched']} (Save wrote the copy: "
                f"{first.get('save')!r}); under attachment/ and the home folder nothing changed (flag bundles "
                f"{before['flags']} -> {after['flags']}, the auto-saved picture, the formula sheet: {before == after}) -- "
                f"the flag was written to the temp folder {result['flag_folder_is_temp']} and discarded when its "
                f"dialog closed ({flag}), the formula sheet is in the temp folder {result['formula_in_temp']}")

    def claim_z():
        return (result["window_visible_after_quit"] is False and "quit" in commands and list(commands)[-1] == "quit",
                f"Quit, triggered last, closes the window: visible afterwards {result['window_visible_after_quit']}")

    rows = []
    for key, claim in (("T", claim_t), ("N", claim_n), ("F", claim_f), ("Q", claim_q), ("S", claim_s), ("Z", claim_z)):
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def _run() -> "tuple[list, dict | None]":
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
        "from KrakenOS.UI.validate_qt_every_command import qt_session\n"
        # flushed, then exit WITHOUT interpreter teardown (a VTK/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps(qt_session()), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    for name in ("WAYLAND_DISPLAY", "KRAKEN_UI_SHELL", "KRAKEN_QT_TK_FREE"):     # the shell as it starts
        env.pop(name, None)
    env["QT_QPA_PLATFORM"] = "xcb"
    env["KRAKEN_CONFIG_DIR"] = tempfile.mkdtemp(prefix="every_command_config_")
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=1500,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, "timed out"]], None
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            result = json.loads(line[len(RESULT_MARK):])
            return checks(result), result
        if line.startswith(SKIP_MARK):
            return [["X", True, line[len(SKIP_MARK):]]], None
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return [["X", False, f"exit {proc.returncode}; " + " | ".join(tail)]], None


def run_checks() -> tuple[bool, list[str]]:
    rows, _result = _run()
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
