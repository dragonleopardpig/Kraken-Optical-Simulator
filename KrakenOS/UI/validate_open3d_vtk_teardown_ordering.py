"""Validate the VTK render-window teardown on application quit (bug 0294).

The Open-3D inspector (:class:`Kraken3DInspector`), the STL-placement dialog and
the face-role dialog each embed a ``vtkTkRenderWindowInteractor`` over a GLX
render window.  Two things were learned the hard way:

1. **The "TkRenderWidget is being destroyed before it[s] associated
   vtkRenderWindow" warning is benign and unavoidable** -- a minimal repro
   (``bugs/probe_0294_vtk_teardown.py``) shows it fires on *every* teardown
   sequence (with or without ``Finalize()``), yet exits cleanly on llvmpipe.  So
   finalize-before-destroy ordering, while tidy, does NOT prevent the crash.
2. **The real segfault is GL-driver-specific** (NVIDIA GLX on the user's box):
   running the Tk+VTK widget destructors at interpreter shutdown tears the render
   window down against a context that is already going away.

The fix is therefore to *not run* the crashy destructor chain on the interactive
quit path: ``KrakenLayoutEditor.request_quit`` shuts the worker processes down
(so nothing is orphaned) and then ``os._exit(0)`` before any Tk/VTK widget
destructor runs.  The headless / programmatic path still uses the ordinary
``destroy()`` (tests and validators tear down normally), and that ``destroy()``
still finalizes the inspector render window first as a tidy best effort.

This guard is display-free (source contract): it asserts the interactive quit
hard-exits after worker shutdown while the headless path does not, plus the
still-correct finalize-before-destroy ordering in ``_on_close`` and
``destroy()``.  It cannot exercise the real NVIDIA crash (no GLX GPU here; the
Tk-embedded widget needs GLX, not the EGL offscreen path), so an in-app quit
eyeball is owed.
"""

from __future__ import annotations

from pathlib import Path

_UI_DIR = Path(__file__).resolve().parent
LAYOUT_EDITOR_PATH = _UI_DIR / "layout_editor.py"
INSPECTOR_PATH = _UI_DIR / "open3d_inspector.py"


def _method_src(text: str, signature: str) -> str | None:
    """Return the body of a top-level-in-class ``def`` (4-space indent) from its
    signature line up to the next same-indent ``def``/``class``, or ``None``."""
    start = text.find(signature)
    if start < 0:
        return None
    rest = text[start + len(signature):]
    # Next method/class at the same 4-space indent ends this one.
    end = len(rest)
    for marker in ("\n    def ", "\n    @", "\nclass "):
        idx = rest.find(marker)
        if 0 <= idx < end:
            end = idx
    return signature + rest[:end]


def run_checks():
    """Return (passed, failures) without printing -- usable as a phase body."""
    failures: list[str] = []

    editor_src = LAYOUT_EDITOR_PATH.read_text(encoding="utf-8") if LAYOUT_EDITOR_PATH.exists() else ""
    inspector_src = INSPECTOR_PATH.read_text(encoding="utf-8") if INSPECTOR_PATH.exists() else ""

    if not editor_src:
        failures.append("layout_editor.py not found")
    if not inspector_src:
        failures.append("open3d_inspector.py not found")
    if failures:
        return (False, failures)

    # --- inspector: _destroy_vtk_render_window actually finalizes ----------
    destroy_rw = _method_src(inspector_src, "    def _destroy_vtk_render_window(self) -> None:")
    if destroy_rw is None:
        failures.append("inspector has no _destroy_vtk_render_window method")
    elif ".Finalize()" not in destroy_rw:
        failures.append("_destroy_vtk_render_window does not call render_window.Finalize()")

    # --- inspector: _on_close finalizes BEFORE it destroys (reference order)
    on_close = _method_src(inspector_src, "    def _on_close(self) -> None:")
    if on_close is None:
        failures.append("inspector has no _on_close method")
    else:
        fin = on_close.find("_destroy_vtk_render_window()")
        dep = on_close.find("self.destroy()")
        if fin < 0:
            failures.append("_on_close does not finalize the VTK render window")
        elif dep < 0:
            failures.append("_on_close does not destroy the inspector window")
        elif fin > dep:
            failures.append("_on_close destroys the widget before finalizing the render window")

    # --- inspector binds the window-manager close to _on_close -------------
    if 'protocol("WM_DELETE_WINDOW", self._on_close)' not in inspector_src:
        failures.append("inspector does not route WM_DELETE_WINDOW through _on_close")

    # --- ROOT quit path: KrakenLayoutEditor.destroy finalizes first (0294) --
    editor_destroy = _method_src(editor_src, "    def destroy(self) -> None:")
    if editor_destroy is None:
        failures.append("KrakenLayoutEditor has no destroy method")
    else:
        fin = editor_destroy.find("self._three_d_inspector._destroy_vtk_render_window()")
        dep = editor_destroy.find("self._three_d_inspector.destroy()")
        if dep < 0:
            failures.append("editor.destroy does not tear down the 3D inspector")
        elif fin < 0:
            failures.append(
                "editor.destroy destroys the 3D inspector without finalizing its VTK "
                "render window first (0294 segfault-on-quit regression)"
            )
        elif fin > dep:
            failures.append(
                "editor.destroy finalizes the render window AFTER destroying the "
                "inspector widget (0294 ordering regression)"
            )

    # --- INTERACTIVE quit hard-exits before the Tk/VTK destructors (0294) ---
    # The real NVIDIA-GLX segfault is not fixable by teardown ordering (the
    # warning is benign); the interactive quit must skip the destructor chain by
    # hard-exiting after the worker processes are shut down.
    request_quit = _method_src(editor_src, "    def request_quit(self) -> None:")
    if request_quit is None:
        failures.append("KrakenLayoutEditor has no request_quit method")
    else:
        if "self._hard_exit_after_cleanup()" not in request_quit:
            failures.append(
                "request_quit does not hard-exit the interactive quit path via "
                "_hard_exit_after_cleanup (0294 NVIDIA-GLX segfault-on-quit)"
            )
        # Headless/programmatic quit must still tear down normally (destroy()),
        # or the validators/tests that create a headless editor get os._exit'd.
        head = request_quit.find("if self.headless:")
        dep = request_quit.find("self.destroy()")
        if head < 0 or dep < 0 or dep < head:
            failures.append(
                "request_quit does not keep the ordinary destroy() teardown on the "
                "headless path (hard-exit would kill test/validator processes)"
            )

    hard_exit = _method_src(editor_src, "    def _hard_exit_after_cleanup(self) -> None:")
    if hard_exit is None:
        failures.append("KrakenLayoutEditor has no _hard_exit_after_cleanup method")
    else:
        exit_pos = hard_exit.find("os._exit(")
        analysis_pos = hard_exit.find("self._shutdown_analysis_executor()")
        worker_pos = hard_exit.find("self._shutdown_optimization_worker(")
        if exit_pos < 0:
            failures.append(
                "_hard_exit_after_cleanup does not call os._exit (interactive quit "
                "would run the crashy Tk/VTK destructor chain)"
            )
        if analysis_pos < 0 or worker_pos < 0:
            failures.append(
                "_hard_exit_after_cleanup hard-exits without shutting down the "
                "analysis/optimization workers first (orphaned child processes)"
            )
        elif exit_pos >= 0 and (analysis_pos > exit_pos or worker_pos > exit_pos):
            failures.append(
                "_hard_exit_after_cleanup calls os._exit BEFORE shutting the workers "
                "down (orphaned child processes on quit)"
            )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("VTK teardown-ordering validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "VTK teardown-ordering validation passed: the interactive quit hard-exits "
        "after worker shutdown (skips the NVIDIA-GLX-crashy Tk/VTK destructor "
        "chain), the headless path still destroy()s normally, and both in-app close "
        "paths finalize the embedded vtkRenderWindow before the Tk widget; in-app "
        "quit eyeball owed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
