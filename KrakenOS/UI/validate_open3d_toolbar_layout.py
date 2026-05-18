"""Validate the Open 3D toolbar layout contract.

The check is source-based so it can run on machines without an embedded VTK/Tk
viewer. It guards the narrow-window UI contract: direct controls stay compact,
and dense placement/orientation actions live in category menus.
"""

from __future__ import annotations

import inspect
import re

from KrakenOS.UI.layout_editor import Kraken3DInspector


_MAX_DIRECT_VIEW_CONTROLS = 9
_MAX_DIRECT_SCENE_CONTROLS = 8

_MENU_EXPECTATIONS: dict[str, tuple[str, ...]] = {
    "CAD / target": (
        "Center STEP Axis",
        "Obj->LED",
        "Export STEP",
        "Faces...",
        "Source Target",
    ),
    "Place": (
        "Center Row->Ray",
        "Snap Row->Target",
    ),
    "Orient": (
        "Orient Row->Target",
        "Orient Row->Ray",
        "Orient Row->Source",
        "Orient Row->Path",
        "Orient Row->CAD Axis",
        "Orient Row->Scene Source",
        "Preview Normal",
        "Orient Row->Normal",
    ),
}

_DENSE_ACTION_LABELS = tuple(
    label
    for labels in _MENU_EXPECTATIONS.values()
    for label in labels
)


def _direct_widget_count(source: str, container_name: str) -> int:
    pattern = re.compile(
        rf"ttk\.(?:Label|Button|Checkbutton|Menubutton|Combobox)"
        rf"\(\s*{re.escape(container_name)}\b"
    )
    return len(pattern.findall(source))


def _contains_widget_text(source: str, widget: str, container_name: str, label: str) -> bool:
    double_quoted = f'ttk.{widget}({container_name}, text="{label}"'
    single_quoted = f"ttk.{widget}({container_name}, text='{label}'"
    return double_quoted in source or single_quoted in source


def _contains_menu_label(source: str, label: str) -> bool:
    return f'add_command(label="{label}"' in source or f"add_command(label='{label}'" in source


def main() -> int:
    init_source = inspect.getsource(Kraken3DInspector.__init__)
    view_direct = _direct_widget_count(init_source, "view_toolbar")
    scene_direct = _direct_widget_count(init_source, "scene_toolbar")
    checks: list[tuple[str, bool, str]] = [
        (
            "Open 3D toolbar has a top-level container",
            "toolbar_container.grid(row=0" in init_source,
            "toolbar_container must own the top controls",
        ),
        (
            "Open 3D toolbar has a View row",
            "view_toolbar.grid(row=0" in init_source,
            "view_toolbar should be row 0",
        ),
        (
            "Open 3D toolbar has a Scene row",
            "scene_toolbar.grid(row=1" in init_source,
            "scene_toolbar should be row 1",
        ),
        (
            "View row direct control count stays narrow-window friendly",
            view_direct <= _MAX_DIRECT_VIEW_CONTROLS,
            f"view row has {view_direct} direct controls; limit is {_MAX_DIRECT_VIEW_CONTROLS}",
        ),
        (
            "Scene row direct control count stays narrow-window friendly",
            scene_direct <= _MAX_DIRECT_SCENE_CONTROLS,
            f"scene row has {scene_direct} direct controls; limit is {_MAX_DIRECT_SCENE_CONTROLS}",
        ),
        (
            "Open 3D toolbar no longer spends width on help text",
            "Click a surface or ray in 3D to inspect it" not in init_source,
            "the bottom status row already carries interaction feedback",
        ),
    ]

    for menu_label, action_labels in _MENU_EXPECTATIONS.items():
        checks.append(
            (
                f"Open 3D scene toolbar exposes {menu_label} menu",
                f'text="{menu_label}"' in init_source,
                f"missing {menu_label} Menubutton",
            )
        )
        for action_label in action_labels:
            checks.append(
                (
                    f"{action_label} is reachable from a category menu",
                    _contains_menu_label(init_source, action_label),
                    f"missing menu item {action_label!r}",
                )
            )

    for label in _DENSE_ACTION_LABELS:
        direct_button = _contains_widget_text(
            init_source,
            "Button",
            "view_toolbar",
            label,
        ) or _contains_widget_text(init_source, "Button", "scene_toolbar", label)
        checks.append(
            (
                f"{label} is not a direct narrow-toolbar button",
                not direct_button,
                f"{label!r} should remain inside a menu, not consume toolbar width",
            )
        )

    failed = [(name, detail) for name, ok, detail in checks if not ok]
    if failed:
        print("Open 3D toolbar layout validation failed:")
        for name, detail in failed:
            print(f"- {name}: {detail}")
        return 1

    print(
        "Open 3D toolbar layout validation passed "
        f"(view direct controls={view_direct}, scene direct controls={scene_direct})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
