"""Validate the Open 3D toolbar layout contract.

The check is source-based so it can run on machines without an embedded VTK/Tk
viewer. It guards the narrow-window UI contract: direct controls stay compact,
and dense placement/orientation actions live in category menus.
"""

from __future__ import annotations

import inspect
import re

from KrakenOS.UI.layout_editor import Kraken3DInspector
from KrakenOS.UI.panels.open3d_top_controls import Open3DTopControlsPanel
from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService


_MAX_DIRECT_VIEW_CONTROLS = 10
_MAX_DIRECT_SCENE_CONTROLS = 8
_MAX_DIRECT_CARRY_CONTROLS = 7

_MENU_EXPECTATIONS: dict[str, tuple[str, ...]] = {
    "CAD / target": (
        "Import Optical STEP...",
        "Import Lens STEP...",
        "Import Camera STEP...",
        "Import LED STEP...",
        "Clear STEP Imports",
        "Arm Selected STEP Carry",
        "Accept STEP Placement",
        "Promote STEP to Optical Solid Row",
        "Promote STEP to Native Rows",
        "Promote STEP to Analytic Surfaces",
        "Center STEP Axis",
        "Snap STEP Surface-Center Normal->Optical Axis",
        "Snap STEP Pick-Point Normal->Optical Axis",
        "Center STEP Surface->Optical Axis",
        "Glue STEP to Surrogate",
        "Obj->LED",
        "Export STEP",
        "Faces...",
        "Source Target",
    ),
    "Place": (
        "Center Row->Optical Axis",
        "Snap Row->Target",
    ),
    "Orient": (
        "Orient Row->Target",
        "Orient Row->Ray",
        "Orient Row->Source",
        "Orient Row->Path",
        "Orient Row->CAD Axis",
        "Orient Row->Scene Source",
        "Animate Galvo Scan",
        "Stop Galvo Scan",
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
    helper_quoted = f'pack_command_button({container_name}, "{label}"'
    return double_quoted in source or single_quoted in source or helper_quoted in source


def _contains_menu_label(source: str, label: str) -> bool:
    return (
        f'add_command(label="{label}"' in source
        or f"add_command(label='{label}'" in source
        or f'MenuCommand("{label}"' in source
        or f"MenuCommand('{label}'" in source
    )


def main() -> int:
    init_source = inspect.getsource(Kraken3DInspector.__init__)
    top_controls_source = inspect.getsource(Open3DTopControlsPanel)
    normalized_top_controls_source = top_controls_source.replace("self.inspector.", "self.")
    toolbar_source = init_source + "\n" + normalized_top_controls_source
    import_step_source = inspect.getsource(Kraken3DInspector.import_step_overlay)
    import_optical_source = inspect.getsource(Kraken3DInspector.import_optical_step_overlay)
    view_direct = _direct_widget_count(toolbar_source, "view_toolbar")
    scene_direct = _direct_widget_count(toolbar_source, "scene_toolbar")
    carry_direct = _direct_widget_count(toolbar_source, "carry_toolbar")
    checks: list[tuple[str, bool, str]] = [
        (
            "Open 3D toolbar has a top-level container",
            "toolbar_container.grid(row=0" in toolbar_source,
            "toolbar_container must own the top controls",
        ),
        (
            "Open 3D toolbar has a View row",
            "view_toolbar.grid(row=0" in toolbar_source,
            "view_toolbar should be row 0",
        ),
        (
            "Open 3D toolbar has a Scene row",
            "scene_toolbar.grid(row=1" in toolbar_source,
            "scene_toolbar should be row 1",
        ),
        (
            "Open 3D toolbar has a Carry row",
            "carry_toolbar.grid(row=2" in toolbar_source,
            "carry_toolbar should be row 2",
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
            "Carry row direct control count stays narrow-window friendly",
            carry_direct <= _MAX_DIRECT_CARRY_CONTROLS,
            f"carry row has {carry_direct} direct controls; limit is {_MAX_DIRECT_CARRY_CONTROLS}",
        ),
        (
            "Open 3D toolbar no longer spends width on help text",
            "Click a surface or ray in 3D to inspect it" not in toolbar_source,
            "the bottom status row already carries interaction feedback",
        ),
        (
            "Open 3D CAD/target menu has an Import STEP submenu",
            'add_cascade(label="Import STEP"' in toolbar_source,
            "STEP imports should be reachable from the embedded 3D scene toolbar",
        ),
        (
            "Open 3D STEP import keeps dialog parent in the 3D window",
            "importer(dialog_parent=self, refresh_open_3d=False)" in import_step_source,
            "Open 3D import commands should not route through a hidden main-window-only dialog path or double-refresh",
        ),
        (
            "Open 3D STEP import selects imported overlay handles",
            "show_step_rotation_handler(label)" in import_step_source and "refresh_from_editor()" in import_step_source,
            "importing STEP from Open 3D should immediately refresh and select the in-scene handles",
        ),
        (
            "Open 3D optical STEP import does not replace the lens STEP slot",
            "import_optical_step(" in import_optical_source
            and 'label = "optical"' in import_optical_source
            and "import_lens_step(" not in import_optical_source,
            "Import Optical STEP should create a separate optical overlay, not overwrite imported_lens_step_path",
        ),
        (
            "Open 3D carry row uses free movement guidance",
            "Hold-drag STEP to move freely" in toolbar_source and "Snap step" not in toolbar_source,
            "STEP carry should be free movement, with optical-axis alignment handled by a separate command",
        ),
        (
            "Open 3D view row gates passive ray picking behind an explicit toggle",
            '"Pick rays"' in toolbar_source
            and "ray_pick_enabled_var" in toolbar_source
            and "_on_ray_pick_changed" in toolbar_source,
            "ray clicks should not open Ray Inspector unless the user enables the Pick rays toggle",
        ),
        (
            "Open 3D view row exposes a Ray count synced to the 2D ray_count_var",
            '"Ray count"' in toolbar_source
            and '_editor_var("ray_count_var")' in toolbar_source
            and "_commit_live_control_update(sync_fields=True)" in toolbar_source,
            "the always-visible View row should set ray count via the shared 2D ray_count_var so 2D and 3D stay in sync",
        ),
        (
            "Open 3D view row can hide side panels",
            '"Live panel"' in toolbar_source
            and "show_live_controls_panel_var" in toolbar_source
            and '"Components"' in toolbar_source
            and "show_scene_components_panel_var" in toolbar_source
            and "_on_open3d_panel_visibility_changed" in toolbar_source,
            "3D side panels should be hideable from the same always-visible toolbar as 2D sidebars.",
        ),
        (
            "Open 3D carry row avoids explicit Lift/Drop buttons",
            'ttk.Button(carry_toolbar, text="Lift"' not in toolbar_source
            and 'ttk.Button(carry_toolbar, text="Drop"' not in toolbar_source
            and "_arm_step_carry_hold" in inspect.getsource(Open3DMouseBindingsService._install_pick_only_left_click_bindings),
            "STEP carry should use press-hold lift and release drop instead of toolbar Lift/Drop buttons",
        ),
        (
            "Open 3D carry row removes old snap buttons",
            'ttk.Button(carry_toolbar, text="Snap ray"' not in toolbar_source
            and 'ttk.Button(carry_toolbar, text="Snap target"' not in toolbar_source,
            "STEP carry should not expose the old ray/target center snap buttons",
        ),
        (
            "Open 3D galvo scan animation has inspector lifecycle hooks",
            all(
                hasattr(Kraken3DInspector, name)
                for name in (
                    "start_galvo_scan_animation",
                    "stop_galvo_scan_animation",
                    "_show_galvo_scan_frame",
                    "_clear_galvo_scan_animation",
                )
            ),
            "the Animate/Stop Galvo Scan menu items need matching inspector methods",
        ),
    ]

    for menu_label, action_labels in _MENU_EXPECTATIONS.items():
        checks.append(
            (
                f"Open 3D scene toolbar exposes {menu_label} menu",
                f'text="{menu_label}"' in toolbar_source
                or f'pack_menubutton(scene_toolbar, "{menu_label}"' in toolbar_source,
                f"missing {menu_label} Menubutton",
            )
        )
        for action_label in action_labels:
            checks.append(
                (
                    f"{action_label} is reachable from a category menu",
                    _contains_menu_label(toolbar_source, action_label),
                    f"missing menu item {action_label!r}",
                )
            )

    for label in _DENSE_ACTION_LABELS:
        direct_button = _contains_widget_text(
            toolbar_source,
            "Button",
            "view_toolbar",
            label,
        ) or _contains_widget_text(toolbar_source, "Button", "scene_toolbar", label)
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
        f" Carry direct controls={carry_direct}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
