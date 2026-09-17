"""Repo-wide guard against bug-0045-class latent NameErrors.

Bug 0045 was a button whose callback raised ``NameError:
encode_custom_surface_value`` -- the method lived in an extracted service
mixin and referenced an editor-module global that the editor never imported,
so ``_sync_layout_globals`` never bound it. The crash was invisible until a
user clicked that exact button.

This validator generalises the single-dialog AST guard
(``validate_surface_shape_builder_dialog_bindings``) into a sweep over *every*
``KrakenOS.UI`` module the editor actually loads. For each one it asks: does
any function reference a name as a module global that is bound in neither the
module's (post-sync) namespace nor builtins? If so, that call site is a
NameError waiting for the right click.

Why this models the real runtime faithfully:

* Importing ``KrakenOS.UI.layout_editor`` fires every
  ``_sync_layout_globals(globals())`` (7 extracted mixins get the editor's
  globals copied in), so each module's live ``__dict__`` already reflects the
  late-bound names.
* Lazy injectors (``optical_stl_placement_dialog._sync_layout_symbols`` pulls
  editor symbols in at dialog ``__init__`` via ``getattr(le, name)``) are
  fired here too -- which doubles as a check that their getattr lists resolve.
* ``symtable`` does the scope analysis (parameters, locals, comprehension
  targets, closures, ``global`` writes are all handled correctly), so a name
  is only flagged when it genuinely resolves to an unbound module global.

Display-free: only imports modules (no Tk root, no GL), so it needs no Xvfb.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_ui_unbound_global_names

Exit: 0 = no unbound names, 1 = at least one latent NameError.
"""
from __future__ import annotations

import ast
import builtins
import importlib
import symtable
import sys
from pathlib import Path

BUILTIN_NAMES = set(dir(builtins))


def _loaded_ui_modules() -> list[str]:
    """Every ``KrakenOS.UI`` module the editor import pulled in, with a .py file."""
    names: list[str] = []
    for name, module in list(sys.modules.items()):
        if not name.startswith("KrakenOS.UI"):
            continue
        file = getattr(module, "__file__", None)
        if file is None or not str(file).endswith(".py"):
            continue
        names.append(name)
    return sorted(names)


def _global_assigned_names(source: str) -> set[str]:
    """Names a function assigns after ``global X`` -- module globals at runtime."""
    out: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Global):
            out.update(node.names)
    return out


def _free_global_refs(source: str, filename: str) -> dict[str, list[str]]:
    """{name: [function qualnames]} for names referenced as free module globals."""
    found: dict[str, list[str]] = {}

    def visit(table: symtable.SymbolTable, prefix: str) -> None:
        for child in table.get_children():
            name = child.get_name()
            qual = f"{prefix}.{name}" if prefix else name
            if child.get_type() == "function":
                for sym in child.get_symbols():
                    if (
                        sym.is_referenced()
                        and sym.is_global()
                        and not sym.is_assigned()
                        and not sym.is_parameter()
                    ):
                        found.setdefault(sym.get_name(), []).append(qual)
            visit(child, qual)

    visit(symtable.symtable(source, filename, "exec"), "")
    return found


def _scan() -> list[str]:
    failures: list[str] = []

    # Importing the editor fires every _sync_layout_globals(globals()).
    importlib.import_module("KrakenOS.UI.layout_editor")

    for mod_name in _loaded_ui_modules():
        module = importlib.import_module(mod_name)

        # Fire lazy symbol injectors (validates their getattr(le, name) lists too).
        injector = getattr(module, "_sync_layout_symbols", None)
        if callable(injector):
            try:
                injector()
            except Exception as exc:  # a missing editor symbol surfaces here
                failures.append(f"{mod_name}: {type(injector).__name__} injector raised: {exc}")

        path = Path(module.__file__)
        source = path.read_text(encoding="utf-8")
        available = set(vars(module).keys()) | BUILTIN_NAMES | _global_assigned_names(source)

        for name, where in sorted(_free_global_refs(source, path.name).items()):
            if name in available:
                continue
            sites = ", ".join(sorted(set(where))[:4])
            failures.append(f"{mod_name}: unbound global '{name}' (used in: {sites})")
    return failures


def main() -> int:
    try:
        failures = _scan()
    except Exception as exc:
        import traceback

        print(f"FAIL: scan raised: {exc}\n{traceback.format_exc()}")
        return 1

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(
            f"[FAIL] {len(failures)} latent NameError(s): a button/menu callback "
            "references an unbound name (bug-0045 class)"
        )
        return 1
    print("[PASS] no unbound module globals in any editor-loaded UI module")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
