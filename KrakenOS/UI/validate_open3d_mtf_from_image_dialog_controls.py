"""Guard: the Measure-MTF-from-Image dialog has a close path and a click-to-enlarge plot (bugs/0415).

User: "The measure MTF from image pop up, need close mechanism. The MTF image can it be made clickable,
enlarge just like other Analysis curve behaviour?"

* CLOSE   -- an explicit "Close" button + a ``WM_DELETE_WINDOW`` protocol + an ``<Escape>`` binding all
  tear the dialog down (a plain Toplevel gives no reliable title-bar X on the user's WM / centered
  dialog), and ``_close`` clears the standalone Figure and destroys the window.
* ENLARGE -- the embedded plot widget binds ``<Button-1>`` to ``_enlarge_plot`` and shows a hand cursor;
  ``_enlarge_plot`` renders the figure to a high-res PNG and opens it in the system image viewer via the
  editor's ``_open_image_with_system_viewer`` -- the same behaviour as the main-window Analysis curves.

Display-free: a getsource check of the dialog factory (the dialog needs Tk + matplotlib + an editor to
instantiate, so the wiring is pinned by inspection, like the other UI-mechanism guards).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_mtf_from_image_dialog_controls

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


def _dialog_source() -> str:
    from KrakenOS.UI.panels.mtf_from_image_dialog import open_mtf_from_image_dialog
    return inspect.getsource(open_mtf_from_image_dialog)


def _check_close(failures, notes):
    src = _dialog_source()
    need = {
        "a Close button": 'text="Close", command=lambda: _close()',
        "the WM_DELETE_WINDOW protocol": 'window.protocol("WM_DELETE_WINDOW", _close)',
        "an <Escape> binding": 'window.bind("<Escape>"',
        "window.destroy in _close": "window.destroy()",
    }
    missing = [label for label, token in need.items() if token not in src]
    if "def _close(" not in src:
        missing.append("a _close teardown helper")
    if missing:
        failures.append("CLOSE: dialog is missing " + ", ".join(missing))
    else:
        notes.append("close = Close button + WM_DELETE + Escape all call _close (destroys the window)")


def _check_enlarge(failures, notes):
    src = _dialog_source()
    need = {
        "the plot click binding": 'plot_widget.bind("<Button-1>", lambda _e: _enlarge_plot())',
        "the hand cursor": 'cursor="hand2"',
        "a high-res savefig": "figure.savefig(image_path, dpi=300",
        "the system-viewer open": "_open_image_with_system_viewer(image_path)",
    }
    missing = [label for label, token in need.items() if token not in src]
    if "def _enlarge_plot(" not in src:
        missing.append("an _enlarge_plot helper")
    if missing:
        failures.append("ENLARGE: dialog is missing " + ", ".join(missing))
    else:
        notes.append("enlarge = click the plot -> high-res PNG -> system image viewer (Analysis-curve parity)")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_close, _check_enlarge):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_mtf_from_image_dialog_controls (bugs/0415) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll MTF-from-image dialog control checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
