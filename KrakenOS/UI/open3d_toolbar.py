"""The 3D inspector's top controls as data (docs/design_qt_migration.md phase 5f).

The View / Scene / Carry rows above the 3D view were widgets written straight into
`panels/open3d_top_controls.py`, so under the Qt shell -- where the inspector's Tk window is
withdrawn -- none of them could be reached. Like the system inputs (bugs/0900), each control is
now a record naming the MODEL variable it edits and the MODEL method it calls; a view is layout
and binding only. Tk renders this catalogue in `Open3DTopControlsPanel`, Qt in
`qt/inspector_toolbar.py`, and both bind to the same variables, which carry `trace_add` whichever
host made them.

A target is written ``"inspector.<attr>"`` or ``"editor.<attr>"`` and resolved against the live
objects, so the catalogue holds no references and imports nothing heavy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: `normal_target_var`'s choices: the scene's named normal targets
NORMAL_TARGETS = "module:KrakenOS.UI.services.element_scene_metadata.SCENE_NORMAL_TARGET_CHOICES"


@dataclass(frozen=True)
class Command:
    label: str
    target: str
    args: tuple = ()
    #: Tk only: the shell's inspector is a dock, which it closes itself (Close would tear it down)
    tk_only: bool = False


@dataclass(frozen=True)
class Check:
    label: str
    var: str
    target: str


@dataclass(frozen=True)
class Choice:
    label: str
    var: str
    choices: "tuple[str, ...] | str"
    target: str = ""
    width: int = 4


@dataclass(frozen=True)
class Entry:
    label: str
    var: str
    width: int = 6


@dataclass(frozen=True)
class Radio:
    """A menu of mutually exclusive values for one variable."""
    label: str
    var: str
    options: tuple
    target: str
    handle: str = ""


@dataclass(frozen=True)
class Menu:
    label: str
    #: Command, Check, Menu (a cascade) or None (a separator)
    entries: tuple
    #: the inspector attribute a Tk view stores the built menu on (validators read them)
    handle: str = ""


@dataclass(frozen=True)
class Text:
    text: str


@dataclass(frozen=True)
class Toggle:
    """A button whose caption is a variable (the bug recorder's Start/Stop)."""
    textvar: str
    target: str
    handle: str = ""


@dataclass(frozen=True)
class Button:
    """A plain command button the inspector keeps a handle to."""
    label: str
    target: str
    handle: str = ""


@dataclass(frozen=True)
class Row:
    title: str
    left: tuple
    right: tuple = field(default_factory=tuple)


OVERLAYS = Menu("Overlays", (
    Check("Obj/Img planes (Refs)", "inspector.show_reference_surfaces_var", "inspector._on_scene_visibility_changed"),
    Check("FOV planes (QE)", "inspector.quick_estimation_var", "inspector._toggle_quick_estimation"),
    Check("Det", "inspector.show_detector_overlays_var", "inspector._on_scene_visibility_changed"),
    Check("Miss", "inspector.show_terminal_diagnostics_var", "inspector._on_scene_visibility_changed"),
    Check("Clipped", "editor.show_clipped_rays_var", "inspector._on_clipped_rays_changed"),
    Check("Thickness", "editor.show_physical_distances_var", "inspector._on_scene_visibility_changed"),
    Check("Solve banner", "inspector.show_solve_banner_var", "inspector._on_solve_banner_toggled"),
    Check("Focus surf", "inspector.show_best_focus_surface_var", "inspector._on_scene_visibility_changed"),
    Check("Distortion", "inspector.show_distortion_grid_var", "inspector._on_scene_visibility_changed"),
    Check("Astigmatism", "inspector.show_astigmatism_var", "inspector._on_scene_visibility_changed"),
    Check("Spot map", "inspector.show_spot_field_map_var", "inspector._on_scene_visibility_changed"),
    Check("Pixel grid", "inspector.show_pixel_grid_var", "inspector._on_scene_visibility_changed"),
    Check("Illumination", "inspector.show_source_illumination_var", "inspector._on_scene_visibility_changed"),
    Check("Illum rays", "inspector.show_source_illumination_rays_var", "inspector._on_illumination_rays_toggled"),
    Check("Illum emission", "inspector.show_illumination_marker_rays_var", "inspector._on_scene_visibility_changed"),
    Check("Accept cone", "inspector.show_receiving_cone_var", "inspector._on_scene_visibility_changed"),
    Check("Illum volume", "inspector.show_illumination_volume_var", "inspector._on_scene_visibility_changed"),
    # bugs/0958: how imported STEP hardware is drawn -- display only
    Check("Soft STEP bodies", "inspector.soft_step_bodies_var", "inspector._on_step_body_style_changed"),
    # bugs/0966: how the table's elements and the rays are drawn -- display only
    Check("Modern look", "inspector.modern_look_var", "inspector._on_scene_look_changed"),
    None,
    Command("Normal to Sensor", "inspector.view_normal_to_sensor"),
    Command("Clear selection / hide handles (Esc)", "inspector.cancel_active_3d_operation"),
), handle="_open3d_overlay_menu")

IMPORT_STEP = Menu("Import STEP", (
    Command("Import Optical STEP...", "inspector.import_optical_step_overlay"),
    Command("Import Imaging Lens STEP...", "inspector.import_step_overlay", ("lens",)),
    Command("Import Camera STEP...", "inspector.import_step_overlay", ("camera",)),
    Command("Import LED STEP...", "inspector.import_step_overlay", ("led",)),
), handle="_open3d_import_step_menu")

CAD_TARGET = Menu("CAD / target", (
    IMPORT_STEP,
    Command("Import Lens from Folder (replaces scene)...", "inspector.import_machine_vision_lens_from_folder"),
    Command("Swap Imaging Lens from Folder (keeps scene)...", "inspector.swap_imaging_lens_from_folder"),
    Command("Import Camera from Folder...", "inspector.import_vendor_camera_from_folder"),
    None,
    Command("Delete Selected STEP", "inspector.delete_selected_step"),
    Command("Clear STEP Imports", "inspector.clear_step_imports"),
    None,
    Command("Arm Selected STEP Carry", "inspector.start_selected_step_carry"),
    Command("Promote to Optical Element", "inspector.promote_selected_step_to_optical_solid_row"),
    None,
    Command("Center STEP Axis", "editor.start_any_step_axis_pick"),
    Command("Snap STEP Surface-Center Normal->Optical Axis", "inspector.snap_selected_step_normal_to_optical_axis"),
    Command("Snap STEP Pick-Point Normal->Optical Axis", "inspector.snap_selected_step_pick_point_normal_to_optical_axis"),
    Command("Center STEP Surface->Optical Axis", "inspector.center_selected_step_surface_to_optical_axis"),
    Command("Center Lens Body->Surrogate Axis (no axial shift)", "inspector.center_lens_body_on_surrogate_axis"),
    Command("Glue STEP to Surrogate", "inspector.glue_selected_step_to_surrogate"),
    Command("Obj->LED", "editor.start_led_object_edge_pick"),
    Command("Export STEP", "editor.export_3d_step"),
    Command("Export View DXF", "editor.export_3d_view_dxf"),
    None,
    Command("Faces...", "inspector.open_selected_optical_faces"),
    Command("Source Target", "inspector.start_source_target_pick"),
), handle="_open3d_cad_target_menu")

PLACE = Menu("Place", (
    Command("Center Row->Optical Axis", "inspector.start_center_row_to_ray"),
    Command("Snap Row->Target", "inspector.start_placement_target_pick"),
    None,
    Command("Move Elements to Optical Axis", "inspector.start_axis_to_axis_move"),
    Command("Select Elements (Rubber Band)", "inspector.start_rubber_band_select"),
    Command("Rubber-Band Select + Snap to Axis...", "inspector.start_rubber_band_select_and_snap"),
    Command("Snap Selected to Optical Axis", "inspector.start_snap_selected_to_axis"),
    Command("Add Selected to Assembly", "inspector.group_selected_as_assembly"),
    Command("Snap Assembly to Optical Axis", "inspector.start_snap_assembly_to_axis"),
    Command("Clear Assembly", "inspector.clear_assembly"),
), handle="_open3d_placement_menu")

ORIENT = Menu("Orient", (
    Command("Orient Row->Target", "inspector.start_placement_orient_pick"),
    Command("Orient Row->Ray", "inspector.start_placement_orient_ray_pick"),
    Command("Orient Row->Source", "inspector.orient_selected_row_to_source_direction"),
    Command("Orient Row->Path", "inspector.orient_selected_row_to_path_frame"),
    None,
    Command("Orient Row->CAD Axis", "inspector.orient_selected_row_to_local_axis"),
    Command("Orient Row->Scene Source", "inspector.orient_selected_row_to_scene_source"),
    None,
    Command("Animate Galvo Scan", "inspector.start_galvo_scan_animation"),
    Command("Stop Galvo Scan", "inspector.stop_galvo_scan_animation"),
    None,
    Command("Preview Normal", "inspector.preview_selected_row_normal_target"),
    Command("Orient Row->Normal", "inspector.orient_selected_row_to_named_normal_target"),
), handle="_open3d_orientation_menu")

ROWS = (
    Row("View", (
        Command("Refresh", "inspector.refresh_from_editor"),
        Command("Snapshot", "inspector.save_snapshot"),
        # Save the current prescription (a solve done entirely in 3D included) back to the
        # layout .py; both write the <layout>.open3d.json session sidecar
        Command("Save Layout", "inspector.save_layout"),
        Command("Save As", "inspector.save_layout_as"),
        # the Nav Cube is the camera-navigation control; what stays is the Iso-up axis (bugs/0231)
        Radio("Iso up ▾", "inspector.iso_up_axis_var",
              (("Y up (default)", "y"), ("Z up", "z"), ("X up", "x")), "inspector._on_iso_up_axis_changed",
              handle="_open3d_iso_up_menu"),
        Check("Show rays", "inspector.show_rays_var", "inspector._on_show_rays_changed"),
        Check("Pick rays", "inspector.ray_pick_enabled_var", "inspector._on_ray_pick_changed"),
        OVERLAYS,
    ), (
        Command("Done 2D", "inspector.finish_stl_placement"),
        Command("Close", "inspector._on_close", tk_only=True),
        Toggle("inspector.recorder_button_var", "inspector.toggle_bug_recording", handle="_recorder_button"),
        Button("Discard rec", "inspector.discard_bug_recording", handle="_discard_button"),
        Button("⚑ Flag bug (s)", "inspector.flag_bug", handle="_flag_bug_button"),
    )),
    Row("Scene", (
        CAD_TARGET,
        PLACE,
        ORIENT,
        Choice("Axis", "inspector.orient_axis_var", ("+X", "-X", "+Y", "-Y", "+Z", "-Z")),
        Choice("Normal", "inspector.normal_target_var", NORMAL_TARGETS, width=12),
        Command("Measure", "inspector.start_measure_pick"),
        Command("Measure E/E", "inspector.start_measure_entity_pick"),
        Command("Clear meas.", "inspector.clear_measurements"),
    )),
    Row("Carry", (
        Text("Hold-drag STEP to move freely; drag rotates view; Ctrl+drag box-selects."),
        Check("Move/Rotate whole body", "inspector.show_rotation_handles_var", "inspector._toggle_rotation_handles"),
        Choice("Rot", "inspector.rotation_step_deg_var", ("15", "30", "45", "90", "180"),
               "inspector._on_rotation_step_changed"),
        Entry("Snap mm", "inspector.carry_snap_mm_var"),
        Check("Placement handles", "inspector.show_placement_handles_var", "inspector._on_scene_visibility_changed"),
    )),
)


def resolve(inspector, target: str) -> Any:
    """The live attribute a ``"inspector.x"`` / ``"editor.x"`` target names."""
    owner_name, _, attr = str(target).partition(".")
    owner = inspector if owner_name == "inspector" else getattr(inspector, "editor")
    # a variable the owner lacks is None -- the view leaves that control out (never creates a
    # stand-in variable: under the Qt shell there is no Tk to make one with)
    if attr.endswith("_var"):
        return getattr(owner, attr, None)
    return getattr(owner, attr)


def callback(inspector, target: str, args: tuple = ()):
    """A zero-argument callable for a catalogue target, resolved when it RUNS (a test may
    replace the method after the toolbar was built)."""
    def run(*_ignored):
        return resolve(inspector, target)(*args)
    return run


def choices_for(inspector, choice: Choice) -> tuple:
    if isinstance(choice.choices, str):
        if choice.choices.startswith("module:"):
            import importlib

            module_name, _, name = choice.choices[len("module:"):].rpartition(".")
            return tuple(getattr(importlib.import_module(module_name), name))
        return tuple(resolve(inspector, choice.choices))
    return tuple(choice.choices)


def walk(entries):
    """Every control in ``entries``, descending into menus."""
    for entry in entries:
        if entry is None:
            continue
        yield entry
        if isinstance(entry, Menu):
            yield from walk(entry.entries)
        elif isinstance(entry, Row):
            yield from walk(entry.left + entry.right)


def find(label: str, *, menu: str = "", row: str = ""):
    """The control labelled ``label`` -- inside the menu labelled ``menu`` (cascades included) or
    the row titled ``row`` when given -- or None. Guards ask the catalogue what the toolbar offers
    instead of reading a panel's source (0928)."""
    scope = ROWS
    if row:
        scope = tuple(r for r in ROWS if r.title == row)
    if menu:
        menus = [m for m in walk(scope) if isinstance(m, (Menu, Radio)) and m.label == menu]
        if not menus:
            return None
        scope = tuple(e for m in menus for e in (m.entries if isinstance(m, Menu) else ()))
        if isinstance(menus[0], Radio):
            return menus[0] if label in (lbl for lbl, _v in menus[0].options) else None
    for item in walk(scope):
        if getattr(item, "label", None) == label or getattr(item, "text", None) == label:
            return item
    return None


def offers(label: str, *, target: str = "", var: str = "", menu: str = "", row: str = "") -> bool:
    """True when the catalogue offers ``label`` (in ``menu`` / ``row``) wired to ``target`` and/or
    bound to ``var`` -- the method / variable given by attribute name or as "inspector.x"."""
    item = find(label, menu=menu, row=row)
    if item is None:
        return False

    def same(named: str, wanted: str) -> bool:
        return named == wanted or named.split(".", 1)[-1] == wanted

    if target and not same(str(getattr(item, "target", "")), target):
        return False
    if var and not same(str(getattr(item, "var", getattr(item, "textvar", ""))), var):
        return False
    return True
