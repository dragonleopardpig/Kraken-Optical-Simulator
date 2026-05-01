#!/usr/bin/env python3
"""Audit KrakenOS core surface attrs against the UI coverage registry.

This is intentionally source-based and does not import KrakenOS, so it can run
even when optional GUI/scientific dependencies are missing from the shell.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SURF_CLASS = ROOT / "KrakenOS" / "SurfClass.py"
LAYOUT_EDITOR = ROOT / "KrakenOS" / "UI" / "layout_editor.py"
EXAMPLES_DIR = ROOT / "KrakenOS" / "Examples"

INTENTIONAL_INTERNAL_SURF_ATTRS = {
    "General_Status",
    "PresicionPrecal",
    "SURF_FUNC",
    "UDA_Obj",
}


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _assignment_node(tree: ast.Module, name: str) -> ast.AST | None:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return node.value
    return None


def _surface_core_attrs() -> set[str]:
    tree = _parse(SURF_CLASS)
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "surf":
            continue
        for item in node.body:
            if not isinstance(item, ast.FunctionDef) or item.name != "__init__":
                continue
            attrs: set[str] = set()
            for child in ast.walk(item):
                targets: list[ast.AST] = []
                if isinstance(child, ast.Assign):
                    targets = list(child.targets)
                elif isinstance(child, ast.AnnAssign):
                    targets = [child.target]
                for target in targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        attrs.add(target.attr)
            return attrs
    raise RuntimeError(f"Could not find surf.__init__ in {SURF_CLASS}")


def _advanced_surface_attrs() -> set[str]:
    node = _assignment_node(_parse(LAYOUT_EDITOR), "ADVANCED_SURFACE_FIELD_GROUPS")
    if node is None:
        raise RuntimeError("Could not find ADVANCED_SURFACE_FIELD_GROUPS")
    groups = ast.literal_eval(node)
    attrs: set[str] = set()
    for _group_name, fields in groups:
        for attr, _label in fields:
            attrs.add(str(attr))
    return attrs


def _ui_supported_surface_attrs() -> set[str]:
    tree = _parse(LAYOUT_EDITOR)
    node = _assignment_node(tree, "EXAMPLE_SUPPORTED_SURFACE_ATTRS")
    if node is None or not isinstance(node, ast.Set):
        raise RuntimeError("Could not find EXAMPLE_SUPPORTED_SURFACE_ATTRS")
    attrs = {
        str(element.value)
        for element in node.elts
        if isinstance(element, ast.Constant) and isinstance(element.value, str)
    }
    attrs.update(_advanced_surface_attrs())
    return attrs


def _is_kos_surf_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "surf"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "Kos"
    )


def _example_surface_attrs(path: Path) -> set[str]:
    tree = _parse(path)
    surf_vars: set[str] = set()
    attrs: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _is_kos_surf_call(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    surf_vars.add(target.id)
            for keyword in node.value.keywords:
                if keyword.arg:
                    attrs.add(keyword.arg)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id in surf_vars
            ):
                attrs.add(target.attr)
    return attrs


def _example_unknown_attrs(supported: set[str]) -> dict[str, list[str]]:
    unknown: dict[str, list[str]] = {}
    for path in sorted(EXAMPLES_DIR.glob("*.py")):
        attrs = _example_surface_attrs(path)
        missing = sorted(attrs - supported)
        if missing:
            unknown[path.name] = missing
    return unknown


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict-examples",
        action="store_true",
        help="Return nonzero if examples use attrs outside the UI/core registry.",
    )
    args = parser.parse_args()

    core_attrs = _surface_core_attrs()
    supported_attrs = _ui_supported_surface_attrs()
    expected_public = core_attrs - INTENTIONAL_INTERNAL_SURF_ATTRS
    missing_core = sorted(expected_public - supported_attrs)
    unknown_examples = _example_unknown_attrs(supported_attrs | core_attrs)

    print(f"Core surf attrs: {len(core_attrs)}")
    print(f"UI-supported attrs: {len(supported_attrs)}")
    if missing_core:
        print("Missing public core attrs from UI registry:")
        for attr in missing_core:
            print(f"  - {attr}")
    else:
        print("Missing public core attrs from UI registry: none")

    if unknown_examples:
        print("Example attrs outside core/UI registry:")
        for name, attrs in unknown_examples.items():
            print(f"  - {name}: {', '.join(attrs)}")
    else:
        print("Example attrs outside core/UI registry: none")

    if missing_core:
        return 1
    if args.strict_examples and unknown_examples:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
