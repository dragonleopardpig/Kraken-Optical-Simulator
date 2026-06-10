"""Guard: the Surface Shape Builder dialog factory has no unbound names.

Bug 0045: clicking the surface-shape ("..." advanced surface) button crashed
with ``NameError: name 'encode_custom_surface_value' is not defined``. The
workbench methods were extracted out of ``layout_editor.py`` and rely on
``_sync_layout_globals`` to late-bind the editor's module globals into
``KrakenOS.UI.services.layout_table_workbench``. ``decode_custom_surface_value``
was imported in ``layout_editor`` (and therefore synced) but
``encode_custom_surface_value`` was not, so the name was unbound in the
workbench module even though the dialog factory referenced it.

This check is display-free (no Tk root, no GPU/Xvfb). It imports
``KrakenOS.UI.layout_editor`` -- which runs the globals sync at import time --
then statically parses ``_main_surface_shape_builder_dialog`` and asserts every
free (module-global) name its *body* loads is actually bound in the workbench
module namespace. That catches this whole class of "extracted method references
a name the editor never imported" regression, not just the one symbol.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_surface_shape_builder_dialog_bindings

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import ast
import builtins
import inspect
import textwrap


def _free_global_names(func) -> "set[str]":
    """Names the function *body* loads that are neither locals nor builtins."""
    source = textwrap.dedent(inspect.getsource(func))
    tree = ast.parse(source)
    func_def = tree.body[0]
    assert isinstance(func_def, (ast.FunctionDef, ast.AsyncFunctionDef))

    bound_local: set[str] = set()
    for arg in list(func_def.args.args) + list(func_def.args.kwonlyargs):
        bound_local.add(arg.arg)
    if func_def.args.vararg:
        bound_local.add(func_def.args.vararg.arg)
    if func_def.args.kwarg:
        bound_local.add(func_def.args.kwarg.arg)

    loaded: set[str] = set()
    # Walk only the body so the return annotation (a string under
    # ``from __future__ import annotations``) is not counted.
    for stmt in func_def.body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    bound_local.add(node.id)
                elif isinstance(node.ctx, ast.Load):
                    loaded.add(node.id)

    return {
        name
        for name in loaded
        if name not in bound_local and not hasattr(builtins, name)
    }


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    # Importing layout_editor runs _sync_layout_globals(globals()) at module
    # load, the same path the live app takes before any button is clicked.
    import KrakenOS.UI.layout_editor  # noqa: F401
    from KrakenOS.UI.services import layout_table_workbench as workbench
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    factory = LayoutTableWorkbenchMixin._main_surface_shape_builder_dialog
    free_names = _free_global_names(factory)
    module_ns = vars(workbench)

    missing = sorted(name for name in free_names if name not in module_ns)
    passed = not missing
    if missing:
        notes.append(
            "FAIL: _main_surface_shape_builder_dialog references names unbound in "
            f"the workbench module (would NameError on click): {missing}"
        )

    if verbose:
        notes.append(
            f"checked {len(free_names)} free names, all bound; "
            f"encode_custom_surface_value bound={'encode_custom_surface_value' in module_ns}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] Surface Shape Builder dialog factory has no unbound names")
        return 0
    print("[FAIL] Surface Shape Builder dialog factory binding guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
