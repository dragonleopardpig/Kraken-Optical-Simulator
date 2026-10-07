"""Guard for bugs/0983: showing a form does not import a toolkit until one draws it.

`present_row_form` is what a command that ends in a form calls: a shell that draws its own dialogs
gets the form, otherwise Tk's renderer does. It lived in the Tk form view,
`panels/row_form_view.py`, so every module that only wanted to SHOW a form loaded tkinter with it --
eight dialog panels, and through them two services. It is `row_forms/present.py` now, and imports
the Tk renderer at the moment Tk actually draws.

  S  no module imports the presenter from the Tk view any more; the old name there is the same
     function, so what named it there still finds it
  L  asked of the interpreter, each in a process of its own: importing the presenter loads neither
     tkinter nor Qt; so does handing a form to a shell through it -- the shell gets the form and
     every option, its answer comes back, and the Tk form view is never imported; and the eight
     dialog panels that only show forms load no tkinter when imported
  T  the Tk app, no shell: the form is drawn by the Tk renderer with the options passed on, the
     window is sized as asked, and `wait` returns only after the window is waited on
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "PRESENTFORM_RESULT "
SKIP_MARK = "PRESENTFORM_SKIP "
ROOT = Path("KrakenOS/UI")
#: dialog panels that build a form and hand it to the presenter, and nothing else of Tk
FORM_ONLY_PANELS = ("main_glass_catalog_browser_dialog", "main_path_component_placement_dialog", "main_scene_element_dialogs",
                    "main_scene_source_manager_dialog", "main_stock_lens_importer_dialog", "main_surface_settings_dialogs",
                    "main_surface_shape_builder_dialog", "main_tolerance_report_dialogs")


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def _fresh(code: str) -> str:
    """The last line a fresh interpreter prints for ``code``."""
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300, cwd=str(Path.cwd()))
    return (done.stdout.strip().splitlines() or ["ERROR " + done.stderr.strip()[-160:]])[-1]


def pure_checks() -> list:
    def s():
        from KrakenOS.UI.panels import row_form_view
        from KrakenOS.UI.row_forms import present

        pattern = re.compile(r"panels\.row_form_view import[^\n]*\bpresent_row_form\b")
        from_tk_view = sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*.py")
                              if "archive" not in path.parts and not path.name.startswith("validate_")
                              and pattern.search(path.read_text(encoding="utf-8", errors="replace")))
        from_forms = sum(1 for path in ROOT.rglob("*.py") if "archive" not in path.parts and not path.name.startswith("validate_")
                         and "row_forms.present import present_row_form" in path.read_text(encoding="utf-8", errors="replace"))
        return (from_tk_view == [] and from_forms >= 20 and row_form_view.present_row_form is present.present_row_form,
                f"{from_forms} modules import the presenter from the forms package, {from_tk_view or 'none'} from the Tk view; "
                f"the old name is the same function: {row_form_view.present_row_form is present.present_row_form}")

    def l():
        loaded = "sorted(n for n in ('tkinter', 'PySide6', 'KrakenOS.UI.panels.row_form_view') if n in sys.modules)"
        importing = _fresh(f"import sys\nimport KrakenOS.UI.row_forms.present\nprint({loaded})\n")
        handing = _fresh(
            "import sys\nfrom types import SimpleNamespace\nfrom KrakenOS.UI.row_forms.present import present_row_form\n"
            "got = []\n"
            "editor = SimpleNamespace()\n"
            "editor.show_row_form = lambda form, **options: (got.append((form, sorted(options.items()))), 'the shell dialog')[1]\n"
            "panel = SimpleNamespace(editor=editor)\n"
            "form = SimpleNamespace(title='A form')\n"
            "answers = [present_row_form(editor, form, on_close='closer', modal=True, geometry='640x300', wait=True),\n"
            "           present_row_form(panel, form)]\n"
            f"print(repr((answers, [(f.title, o) for f, o in got], {loaded})))\n")
        panels = {name: _fresh(f"import sys\nimport KrakenOS.UI.panels.{name}\nprint('tkinter' in sys.modules)\n") for name in FORM_ONLY_PANELS}
        expected_options = [("geometry", "640x300"), ("modal", True), ("on_close", "closer"), ("wait", True)]
        default_options = [("geometry", None), ("modal", False), ("on_close", None), ("wait", False)]
        expected = repr((["the shell dialog", "the shell dialog"], [("A form", expected_options), ("A form", default_options)], []))
        return (importing == "[]" and handing == expected and all(answer == "False" for answer in panels.values())
                and len(panels) == 8,
                f"importing the presenter loads {importing}; a form handed to a shell through it: {handing[:150]}...; "
                f"the {len(panels)} form-only panels that load tkinter when imported: "
                f"{sorted(name for name, answer in panels.items() if answer != 'False') or 'none'}")

    return _claims((("S", s), ("L", l)))


def tk_checks() -> list:
    import tkinter as tk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.panels import row_form_view
    from KrakenOS.UI.row_forms.interface_preference import build_interface_preference_form
    from KrakenOS.UI.row_forms.present import present_row_form

    editor = KrakenLayoutEditor()
    for _ in range(3):
        editor.update()

    def claim_t():
        rendered: list = []
        real_render = row_form_view.render_row_form

        def spying(owner, form, **options):
            rendered.append((owner is editor, form, sorted(options.items())))
            return real_render(owner, form, **options)

        waited: list = []
        wait, tk.Misc.wait_window = tk.Misc.wait_window, lambda self, window=None: waited.append(str((window or self).title()))
        row_form_view.render_row_form = spying
        try:
            form = build_interface_preference_form(editor)
            closer = lambda *_a: None
            window = present_row_form(editor, form, wraplength=444, on_close=closer, modal=False, geometry="640x300", wait=True)
            for _ in range(4):
                editor.update()
            shown = (isinstance(window, tk.Toplevel), str(window.title()), str(window.geometry()).split("+")[0])
            plain = present_row_form(editor, build_interface_preference_form(editor))
            for _ in range(2):
                editor.update()
            waited_after_plain = list(waited)
            plain.destroy()
            window.destroy()
        finally:
            row_form_view.render_row_form = real_render
            tk.Misc.wait_window = wait
        first = rendered[0] if rendered else (False, None, [])
        return (len(rendered) == 2 and first[0] and first[1] is form
                and first[2] == [("modal", False), ("on_close", closer), ("wraplength", 444)]
                and shown == (True, form.title, "640x300") and waited_after_plain == [form.title],
                f"with no shell the Tk renderer drew {len(rendered)} forms, the first for the editor with the options "
                f"{[key for key, _v in first[2]]}; the window is a Tk window titled {shown[1]!r} sized {shown[2]}; `wait` "
                f"waited on it and a form shown without `wait` did not: {waited_after_plain}")

    return _claims((("T", claim_t),))


def _run(call: str, claim: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_present_row_form import tk_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=300,
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
    try:
        rows = pure_checks()
    except Exception as exc:
        rows = [["S", False, f"raised {type(exc).__name__}: {exc}"]]
    rows += _run("tk_checks()", "T")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
