"""Validate the Open 3D toolbar layout contract.

The check is source-based so it can run on machines without an embedded VTK/Tk
viewer. It guards the narrow-window UI contract: direct controls stay compact,
and dense placement/orientation actions live in category menus.
"""

from __future__ import annotations

from KrakenOS.UI.services.open3d_mouse_bindings import viewport_wiring_source

import inspect
import re

from KrakenOS.UI.layout_editor import Kraken3DInspector
from KrakenOS.UI.panels.open3d_top_controls import Open3DTopControlsPanel
from KrakenOS.UI.panels.open3d_live_controls import Open3DLiveControlsPanel
from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel
from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService


# bugs/0928: the rows are a catalogue now (open3d_toolbar.ROWS), counted as TOP-LEVEL controls
# (menus count once; their entries do not). The old budgets (10 / 8 / 7) were measured by a regex
# over literal ``ttk.X(row, ...)`` calls, which missed every control built through a pack_* helper:
# it saw 4 / 3 / 4 while the rows really held 14 / 11 / 8 widgets, so the View budget was never
# enforced. These limits are the honest counts at 0928 -- a no-growth ratchet: a new direct
# control belongs in a category menu, or it raises this number on purpose.
_MAX_DIRECT_VIEW_CONTROLS = 13
_MAX_DIRECT_SCENE_CONTROLS = 8
_MAX_DIRECT_CARRY_CONTROLS = 4

_MENU_EXPECTATIONS: dict[str, tuple[str, ...]] = {
    "CAD / target": (
        "Import Optical STEP...",
        "Import Imaging Lens STEP...",
        "Import Camera STEP...",
        "Import LED STEP...",
        "Clear STEP Imports",
        "Arm Selected STEP Carry",
        "Promote to Optical Element",
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


def run_checks() -> tuple[bool, list[str]]:
    """Penta-harness entry point (bugs/0877): this guard is a registered phase now."""
    import contextlib
    import io

    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = main()
    lines = [line for line in stream.getvalue().splitlines() if line.strip()]
    notes = [("FAIL " + line.lstrip("- ")) if line.startswith("- ") else ("= " + line)
             for line in lines]
    return code == 0, notes


def main() -> int:
    init_source = inspect.getsource(Kraken3DInspector.__init__)
    top_controls_source = inspect.getsource(Open3DTopControlsPanel)
    normalized_top_controls_source = top_controls_source.replace("self.inspector.", "self.")
    toolbar_source = init_source + "\n" + normalized_top_controls_source
    # bugs/0877: three of this file's claims were pinned to the TOP strip after the
    # controls moved into the two side panels, so inspect those too.
    live_controls_source = inspect.getsource(Open3DLiveControlsPanel)
    step_admin_source = inspect.getsource(Open3DStepAdminPanel)
    panel_toggle_source = (
        inspect.getsource(Kraken3DInspector._set_open3d_side_panel_visible)
        + inspect.getsource(Kraken3DInspector.toggle_live_controls_panel)
        + inspect.getsource(Kraken3DInspector.toggle_scene_components_panel))
    import_step_source = inspect.getsource(Kraken3DInspector.import_step_overlay)
    import_optical_source = inspect.getsource(Kraken3DInspector.import_optical_step_overlay)
    # bugs/0928: the rows are data both shells render -- the claims read the catalogue
    from KrakenOS.UI import open3d_toolbar as catalogue

    rows = {row.title: row for row in catalogue.ROWS}

    def direct(title: str) -> int:
        row = rows.get(title)
        return 0 if row is None else len([i for i in row.left + row.right if not isinstance(i, catalogue.Text)])

    def row_items(title: str) -> list:
        row = rows.get(title)
        return [] if row is None else list(row.left + row.right)

    def menu_labels(label: str) -> list:
        menu = next((m for m in catalogue.walk(catalogue.ROWS) if isinstance(m, catalogue.Menu) and m.label == label), None)
        return [] if menu is None else [e.label for e in catalogue.walk(menu.entries) if hasattr(e, "label")]

    texts = " ".join(i.text for r in catalogue.ROWS for i in r.left + r.right if isinstance(i, catalogue.Text))
    view_direct = direct("View")
    scene_direct = direct("Scene")
    carry_direct = direct("Carry")
    checks: list[tuple[str, bool, str]] = [
        (
            "Open 3D toolbar has a top-level container",
            "toolbar_container.grid(row=0" in toolbar_source,
            "toolbar_container must own the top controls",
        ),
        (
            "Open 3D toolbar has a View row",
            [r.title for r in catalogue.ROWS][:1] == ["View"],
            "the View row should be row 0",
        ),
        (
            "Open 3D toolbar has a Scene row",
            [r.title for r in catalogue.ROWS][1:2] == ["Scene"],
            "the Scene row should be row 1",
        ),
        (
            "Open 3D toolbar has a Carry row",
            [r.title for r in catalogue.ROWS][2:3] == ["Carry"],
            "the Carry row should be row 2",
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
            "Click a surface or ray in 3D to inspect it" not in texts,
            "the bottom status row already carries interaction feedback",
        ),
        (
            "Open 3D CAD/target menu has an Import STEP submenu",
            "Import STEP" in menu_labels("CAD / target") and bool(menu_labels("Import STEP")),
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
            "Hold-drag STEP to move freely" in texts and catalogue.find("Snap step") is None,
            "STEP carry should be free movement, with optical-axis alignment handled by a separate command",
        ),
        (
            "Open 3D view row gates passive ray picking behind an explicit toggle",
            catalogue.offers("Pick rays", row="View", var="ray_pick_enabled_var",
                             target="_on_ray_pick_changed"),
            "ray clicks should not open Ray Inspector unless the user enables the Pick rays toggle",
        ),
        (
            # bugs/0093 REMOVED the toolbar's Ray count entry on purpose -- it duplicated the
            # Live Controls one and both bound ray_count_var. One source, still the shared 2D
            # variable, so 2D and 3D stay in sync.
            "Open 3D Live Controls own the Ray count, synced to the 2D ray_count_var",
            '"Ray count", "ray_count_var"' in live_controls_source
            and "sync_fields=True" in live_controls_source
            and catalogue.find("Ray count") is None,
            "Ray count belongs to the Live Controls panel, bound to the shared 2D ray_count_var",
        ),
        (
            # they are collapsed from the panels' own headers now, with an edge arrow to bring
            # each one back -- the toolbar no longer carries the two checkbuttons
            "Open 3D side panels collapse and restore from the 3D window",
            "show_live_controls_panel_var" in toolbar_source
            and "show_scene_components_panel_var" in toolbar_source
            and "toggle_live_controls_panel" in live_controls_source
            and "toggle_scene_components_panel" in step_admin_source
            and "_open3d_live_panel_host" in panel_toggle_source
            and "_open3d_step_admin_panel_host" in panel_toggle_source
            and "paned.forget(widget)" in panel_toggle_source,
            "3D side panels must be collapsible, with an edge control that restores them.",
        ),
        (
            "Open 3D carry row avoids explicit Lift/Drop buttons",
            catalogue.find("Lift", row="Carry") is None
            and catalogue.find("Drop", row="Carry") is None
            and "_arm_step_carry_hold" in viewport_wiring_source(),
            "STEP carry should use press-hold lift and release drop instead of toolbar Lift/Drop buttons",
        ),
        (
            "Open 3D carry row removes old snap buttons",
            catalogue.find("Snap ray", row="Carry") is None
            and catalogue.find("Snap target", row="Carry") is None,
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
                any(isinstance(i, catalogue.Menu) and i.label == menu_label for i in row_items("Scene")),
                f"missing {menu_label} Menubutton",
            )
        )
        for action_label in action_labels:
            checks.append(
                (
                    f"{action_label} is reachable from a category menu",
                    action_label in menu_labels(menu_label),
                    f"missing menu item {action_label!r}",
                )
            )

    checks.append(
        (
            "Accept STEP Placement is reachable from the Scene Components panel",
            "Accept STEP Placement" in step_admin_source
            and "accept_selected_step_placement" in step_admin_source,
            "missing 'Accept STEP Placement' in the STEP admin panel",
        )
    )

    for label in _DENSE_ACTION_LABELS:
        direct_button = any(
            isinstance(i, (catalogue.Command, catalogue.Button)) and i.label == label
            for i in row_items("View") + row_items("Scene")
        )
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
