"""The action registry for the Qt shell (docs/design_qt_migration.md phase 2).

Structure follows `optiland_gui/action_manager.py` (MIT, (c) 2024 Kramer Harrison) -- a factory
that builds every QAction into one dictionary, so the window stays orchestration and a menu, a
toolbar and a test all reach the same action by name.
"""
from __future__ import annotations

#: name -> (menu, text, shortcut, main-window method, tooltip)
ACTIONS = (
    ("open", "&File", "&Open Layout...", "Ctrl+O", "open_layout_action",
     "Open a Kraken layout -- the same model code the Tk editor's File menu runs"),
    ("reload", "&File", "&Reload Layout", "Ctrl+R", "reload_layout_action",
     "Re-read the current layout file from disk"),
    ("quit", "&File", "&Quit", "Ctrl+Q", "quit_action", "Close the Qt shell"),
    ("reset_camera", "&View", "&Fit Scene", "Ctrl+0", "reset_camera_action",
     "Frame every drawn body"),
    ("redraw", "&View", "&Redraw", "F5", "redraw_action", "Rebuild the scene from the model"),
    ("show_rays", "&View", "Show &Rays", "Ctrl+L", "toggle_rays_action",
     "Show or hide the traced light"),
    ("paraxial_matrix", "&Analysis", "Paraxial &Matrix Report", "Ctrl+M",
     "paraxial_matrix_report_action",
     "The system's paraxial matrices, surface by surface -- the same report the Tk editor shows"),
    ("branch_gaussian_q", "&Analysis", "Branch Gaussian &Q Report", None,
     "branch_gaussian_q_report_action",
     "The Gaussian q of every traced branch, from the collector the Tk dialog uses"),
    ("detector_aperture", "&Analysis", "&Detector Aperture Report", None,
     "detector_aperture_report_action", "Which rays reach each detector, and which miss"),
    ("branch_throughput", "&Analysis", "Path &Throughput Report", None,
     "branch_throughput_report_action", "Power delivered along every traced path"),
    ("source_illumination", "&Analysis", "Source &Illumination Report", None,
     "source_illumination_report_action", "What each source puts onto the target surface"),
    ("gaussian_beam", "&Analysis", "&Gaussian Beam Report", None,
     "gaussian_beam_report_action",
     "Propagate an input beam through the system's paraxial matrices, step by step"),
    ("paraxial_calculator", "&Analysis", "Paraxial &Calculator...", None,
     "paraxial_calculator_action",
     "Solve the conjugate relations and apply the result to the layout"),
    ("ray_inspector", "&Analysis", "&Ray Inspector", None, "ray_inspector_action",
     "Every traced ray, and the hits of the one selected"),
    ("trace_paths", "&Analysis", "&Trace Path Inspector", None, "trace_paths_action",
     "Every traced path, nested under the ray it came from, with that path's hits"),
    ("beam_splitter", "&Edit", "&Beam Splitter Settings...", None, "beam_splitter_action",
     "Edit the selected Beam Splitter row's split settings"),
    ("diffuse_scatter", "&Edit", "&Diffuse / BRDF Settings...", None, "diffuse_scatter_action",
     "Edit the selected Diffuse Object row's scatter settings"),
    ("error_map", "&Edit", "&Error Map...", None, "error_map_action",
     "Import or clear the selected surface's measured error map"),
    ("coating_material", "&Edit", "&Coating / Material...", None, "coating_material_action",
     "Edit the selected surface's coating table and metal index"),
    ("advanced_surface", "&Edit", "&Advanced Surface...", None, "advanced_surface_action",
     "Every KrakenOS attribute of the selected surface, in tabs"),
    ("detector_settings", "&Edit", "Detec&tor Settings...", None, "detector_settings_action",
     "Mark the selected row as a terminal detector and size it"),
    ("scene_target", "&Edit", "&Scene Target...", None, "scene_target_action",
     "Edit the selected row's scene-target role, name and detector metadata"),
    ("path_local_pose", "&Edit", "&Path-Local Pose...", None, "path_local_pose_action",
     "Edit the selected placed element's pose in its own path frame"),
    ("element_settings", "&Edit", "Element Se&ttings...", None, "element_settings_action",
     "Edit the selected element block's path metadata"),
    ("scene_sources", "&Edit", "Scene Source &Manager...", None, "scene_sources_action",
     "Add, edit and apply the scene's source records"),
    ("glass_catalog", "&Edit", "&Glass Catalog Browser...", None, "glass_catalog_action",
     "Pick a catalogue glass and apply it to the selected row"),
    ("stock_lens", "&Edit", "Import &Stock Lens...", None, "stock_lens_action",
     "Search a .ZMF catalog and insert a stock lens as surface rows"),
    ("inspection_cell", "&Edit", "&Inspection Cell...", None, "inspection_cell_action",
     "Slot a station layout on each of the part's six faces"),
    ("about", "&Help", "&About", None, "about_action", "What this window is"),
)


#: checkable actions -> their state at start-up
CHECKABLE = {"show_rays": True}


class ActionManager:
    """Creates every QAction of the shell and keeps them under their names."""

    def __init__(self, main_window) -> None:
        self.main_window = main_window
        self.actions: dict[str, object] = {}

    def create_all_actions(self) -> dict[str, object]:
        from PySide6.QtGui import QAction, QKeySequence

        for name, _menu, text, shortcut, method, tooltip in ACTIONS:
            action = QAction(text, self.main_window)
            if name in CHECKABLE:
                action.setCheckable(True)
                action.setChecked(bool(CHECKABLE[name]))
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            action.setToolTip(tooltip)
            handler = getattr(self.main_window, method)
            action.triggered.connect(handler)
            self.actions[name] = action
        return self.actions

    def populate_menu_bar(self, menu_bar) -> dict[str, object]:
        """Add every action to its menu, in declaration order. Returns menu title -> QMenu."""
        menus: dict[str, object] = {}
        for name, title, *_rest in ACTIONS:
            menu = menus.get(title)
            if menu is None:
                menu = menus[title] = menu_bar.addMenu(title)
            menu.addAction(self.actions[name])
        return menus

    def __getitem__(self, name):
        return self.actions[name]
