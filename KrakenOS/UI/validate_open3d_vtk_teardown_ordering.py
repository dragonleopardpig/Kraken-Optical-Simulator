"""Validate the VTK render-window teardown order on application quit.

The Open-3D inspector (:class:`Kraken3DInspector`) embeds a
``vtkTkRenderWindowInteractor``.  A Tk+VTK widget MUST finalize its
``vtkRenderWindow`` before the Tk widget itself is destroyed -- destroying the
``vtkTkRenderWidget`` while the render window is still live segfaults on quit
("A TkRenderWidget is being destroyed before it[s] associated vtkRenderWindow
is destroyed").

The inspector's own X-button close (``_on_close``) already does the right thing:
``_destroy_vtk_render_window()`` (which calls ``render_window.Finalize()``)
*before* ``self.destroy()``.  But quitting the whole app via the root
``KrakenLayoutEditor`` window runs ``KrakenLayoutEditor.destroy()``, which used
to tear the inspector down with a bare ``self._three_d_inspector.destroy()`` --
skipping the finalize and segfaulting (bug 0294).

This guard is display-free: it reads the two source files and asserts the
finalize-before-destroy order in both teardown paths by textual position, plus
that the finalize actually calls ``Finalize()`` and the inspector binds
``WM_DELETE_WINDOW`` to ``_on_close``.  It cannot exercise the real crash (a live
X server is required; Xvfb/llvmpipe segfaults the full renderer), so an in-app
quit eyeball is owed.
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

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("VTK teardown-ordering validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "VTK teardown-ordering validation passed: both the inspector's own close "
        "and the root editor quit finalize the embedded vtkRenderWindow before the "
        "Tk widget is destroyed (no segfault-on-quit); in-app quit eyeball owed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
