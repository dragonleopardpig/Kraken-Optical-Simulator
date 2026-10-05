"""The action registry for the Qt shell (docs/design_qt_migration.md phase 2).

Structure follows `optiland_gui/action_manager.py` (MIT, (c) 2024 Kramer Harrison) -- a factory
that builds every QAction into one dictionary, so the window stays orchestration and the ribbon, a
shortcut and a test all reach the same action by name.

The shell has no menu bar (bugs/0949): `ribbon.RIBBON` / `ribbon.DROPDOWNS` place every action.
"""
from __future__ import annotations

#: name -> (text, shortcut, main-window method, tooltip). "editor:<method>" runs the editor's own
#: method instead (bugs/0942): a Tk menu-bar command that already works under the Qt shell --
#: measured: it opens no window, or asks through the shell's own dialogs -- and only lacked a route.
ACTIONS = (
    ("open", "&Open Layout...", "Ctrl+O", "open_layout_action",
     "Open a Kraken layout -- the same model code the Tk editor's File menu runs"),
    ("reload", "&Reload Layout", "Ctrl+R", "reload_layout_action",
     "Re-read the current layout file from disk"),
    ("save", "&Save Layout", "Ctrl+S", "editor:save_layout",
     "Write the layout back to its file (asks for a name when it has none)"),
    ("save_as", "Save &As...", "Ctrl+Shift+S", "editor:save_layout_as",
     "Save the layout under a new name"),
    ("reset", "Rese&t Layout", None, "editor:reset_layout",
     "Clear to a blank Object + Image layout (Undo brings it back)"),
    ("import_zemax", "Import Zemax File...", None, "editor:import_zemax_file",
     "Import a Zemax .zmx prescription as the layout"),
    ("import_zemax_wavefront", "Import Zemax Wavefront Map...", None, "editor:import_zemax_wavefront_map",
     "Load a Zemax wavefront map as the reference for comparison"),
    ("import_cad_solid", "Import Optical CAD/STL Solid...", None, "editor:import_optical_stl_solid",
     "Insert a STEP / IGES / STL optical solid as a row"),
    ("import_lens_step", "Import Imaging Lens STEP...", None, "editor:import_lens_step",
     "Load a vendor imaging-lens STEP body into the 3D scene"),
    ("import_camera_step", "Import Camera STEP...", None, "editor:import_camera_step",
     "Load a vendor camera STEP body into the 3D scene"),
    ("import_led_step", "Import LED STEP...", None, "editor:import_led_step",
     "Load a vendor LED STEP body into the 3D scene"),
    ("export_3d_step", "Export 3D STEP...", None, "editor:export_3d_step",
     "Write the 3D scene's solids as one STEP assembly"),
    ("export_3d_dxf", "Export 3D View DXF...", None, "editor:export_3d_view_dxf",
     "Write the current 3D view as a 2D DXF drawing"),
    # bugs/0945: the surface-properties window is a session the Qt shell renders too
    ("export_lens_drawing", "Export Lens &Drawing (PDF)...", None, "editor:export_lens_drawing",
     "An ISO 10110-style fabrication drawing of the lens elements, as PDF"),
    ("export_wavefront_csv", "Export Wavefront CSV...", None, "editor:export_wavefront_csv",
     "Write the last wavefront map as CSV"),
    ("export_zernike_csv", "Export Zernike CSV...", None, "editor:export_zernike_csv",
     "Write the last Zernike fit as CSV"),
    # the path / detector exports ask and report through the UI host since bugs/0943
    ("export_path_psf_csv", "Export Path PSF CSV...", None, "editor:export_branch_psf_csv",
     "Write the analysed path's PSF on its detector as CSV (needs a trace: Update first)"),
    ("export_path_mtf_csv", "Export Path MTF CSV...", None, "editor:export_branch_mtf_csv",
     "Write the analysed path's MTF on its detector as CSV (needs a trace: Update first)"),
    ("export_detector_map_csv", "Export Detector Map CSV...", None, "editor:export_detector_map_csv",
     "Write the detector power map as CSV (needs a trace: Update first)"),
    ("export_coherent_detector_csv", "Export Coherent Detector CSV...", None,
     "editor:export_coherent_detector_csv", "Write the coherent detector field sum as CSV"),
    ("export_branch_field_csv", "Export Branch Field CSV...", None, "editor:export_branch_field_csv",
     "Write the propagated branch field as CSV"),
    ("mtf_from_image", "Measure MTF from &Image...", None, "mtf_from_image_action",
     "Measure a real MTF from a captured image: one box over a slanted edge, or a box per USAF element"),
    ("quit", "&Quit", "Ctrl+Q", "quit_action", "Close the Qt shell"),
    ("reset_camera", "&Fit Scene", "Ctrl+0", "reset_camera_action",
     "Frame every drawn body"),
    ("redraw", "&Redraw", "F5", "redraw_action", "Rebuild the scene from the model"),
    ("show_rays", "Show &Rays", "Ctrl+L", "toggle_rays_action",
     "Show or hide the traced light"),
    # a big clean 3D scene in one click, and the parts of it one at a time (user request, bugs/0961)
    ("clean_scene", "Clean 3D Scene", "F11", "clean_scene_action",
     "Only the 3D scene: fold the ribbon, hide the 3D toolbar and every panel. Again: put them all "
     "back as they were"),
    ("hide_panels", "Hide All Panels", "Ctrl+Shift+H", "hide_panels_action",
     "Put every panel away in one click; again brings back the same ones (also first on each edge's "
     "tab strip)"),
    ("toolbar_3d", "3D Toolbar", None, "toolbar_3d_action",
     "Show or hide the 3D scene's View / Scene / Carry toolbar"),
    ("inspector", "3D &Inspector", "Ctrl+I", "inspector_action",
     "Show the 3D inspector -- the window's 3D scene: pick, orbit, pan, drag (bugs/0906, 0951)"),
    ("paraxial_matrix", "Paraxial &Matrix Report", "Ctrl+M",
     "paraxial_matrix_report_action",
     "The system's paraxial matrices, surface by surface -- the same report the Tk editor shows"),
    ("branch_gaussian_q", "Branch Gaussian &Q Report", None,
     "branch_gaussian_q_report_action",
     "The Gaussian q of every traced branch, from the collector the Tk dialog uses"),
    ("detector_aperture", "&Detector Aperture Report", None,
     "detector_aperture_report_action", "Which rays reach each detector, and which miss"),
    ("branch_throughput", "Path &Throughput Report", None,
     "branch_throughput_report_action", "Power delivered along every traced path"),
    ("source_illumination", "Source &Illumination Report", None,
     "source_illumination_report_action", "What each source puts onto the target surface"),
    ("gaussian_beam", "&Gaussian Beam Report", None,
     "gaussian_beam_report_action",
     "Propagate an input beam through the system's paraxial matrices, step by step"),
    ("paraxial_calculator", "Paraxial &Calculator...", None,
     "paraxial_calculator_action",
     "Solve the conjugate relations and apply the result to the layout"),
    ("ray_inspector", "&Ray Inspector", None, "ray_inspector_action",
     "Every traced ray, and the hits of the one selected"),
    ("trace_paths", "&Trace Path Inspector", None, "trace_paths_action",
     "Every traced path, nested under the ray it came from, with that path's hits"),
    ("nonseq_scene_graph", "&Non-Sequential Scene Graph", None,
     "nonseq_scene_graph_action",
     "The scene the non-sequential trace sees: sources, targets and the SDT object list"),
    ("undo", "&Undo", "Ctrl+Z", "editor:undo", "Undo the last change to the layout"),
    ("redo", "&Redo", "Ctrl+Y;Ctrl+Shift+Z", "editor:redo", "Redo the change last undone"),
    ("copy_rows", "Copy Selected Surfaces/Elements", "Ctrl+C", "editor:copy_selected_rows_to_clipboard",
     "Copy the selected surface rows (whole elements) to the clipboard"),
    ("paste_rows", "Paste Surfaces/Elements", "Ctrl+V", "editor:paste_rows_from_clipboard",
     "Paste surface rows from the clipboard after the selection"),
    ("beam_splitter", "&Beam Splitter Settings...", None, "beam_splitter_action",
     "Edit the selected Beam Splitter row's split settings"),
    ("diffuse_scatter", "&Diffuse / BRDF Settings...", None, "diffuse_scatter_action",
     "Edit the selected Diffuse Object row's scatter settings"),
    ("error_map", "&Error Map...", None, "error_map_action",
     "Import or clear the selected surface's measured error map"),
    ("coating_material", "&Coating / Material...", None, "coating_material_action",
     "Edit the selected surface's coating table and metal index"),
    ("advanced_surface", "&Advanced Surface...", None, "advanced_surface_action",
     "Every KrakenOS attribute of the selected surface, in tabs"),
    ("detector_settings", "Detec&tor Settings...", None, "detector_settings_action",
     "Mark the selected row as a terminal detector and size it"),
    ("scene_target", "&Scene Target...", None, "scene_target_action",
     "Edit the selected row's scene-target role, name and detector metadata"),
    ("path_local_pose", "&Path-Local Pose...", None, "path_local_pose_action",
     "Edit the selected placed element's pose in its own path frame"),
    ("element_settings", "Element Se&ttings...", None, "element_settings_action",
     "Edit the selected element block's path metadata"),
    ("scene_sources", "Scene Source &Manager...", None, "scene_sources_action",
     "Add, edit and apply the scene's source records"),
    ("glass_catalog", "&Glass Catalog Browser...", None, "glass_catalog_action",
     "Pick a catalogue glass and apply it to the selected row"),
    ("stock_lens", "Import &Stock Lens...", None, "stock_lens_action",
     "Search a .ZMF catalog and insert a stock lens as surface rows"),
    # bugs/0944: both refused every chosen Path view since the automatic path graph (a leg names no
    # branch path), in both shells; pick the Path view on the surface table's toolbar
    ("lens_drawing_properties", "Lens Drawing Surface &Properties...", None,
     "editor:_open_lens_drawing_surface_properties_dialog",
     "Tolerances, coatings and finish per lens surface, for the fabrication drawing"),
    ("add_path_component", "Add Component to Current &Path View...", None,
     "editor:open_current_path_component_placement",
     "Insert a component on the traced path the table toolbar's Path view shows"),
    ("add_path_stock_lens", "Add Stock Lens to Current Path View...", None,
     "editor:open_current_path_stock_lens_placement",
     "Insert a catalogue lens on the traced path the table toolbar's Path view shows"),
    ("inspection_cell", "&Inspection Cell...", None, "inspection_cell_action",
     "Slot a station layout on each of the part's six faces"),
    ("source_edit", "Edit Scene Sou&rce...", None, "source_edit_action",
     "Edit the first scene source's origin, direction and emitting size"),
    ("inspection_part", "Inspection &Part...", None, "inspection_part_action",
     "Size the 3D part at the object plane and solve the FOV to its face"),
    ("surface_shape", "Surface S&hape Builder...", None, "surface_shape_action",
     "Asphere, Zernike, ExtraData, UDA and mask, with a live sag plot"),
    ("catalog_matcher", "Camera + Lens &Matcher...", None,
     "catalog_matcher_action",
     "List every registered camera x catalog lens combination that meets a requirement"),
    ("system_selection", "S&ystem Selection Calculator...", None,
     "system_selection_action",
     "FOV + resolution + minimum working distance -> the camera pixels and the lens EFL / magnification"),
    ("optical_solid_diagnostics", "Inspect Optical CAD/STL &Solids", None, "optical_solid_diagnostics_action",
     "Check every CAD/STL solid row can be traced: closed, manifold, outward winding, size, CAD source"),
    ("face_roles", "Assign CAD/STL &Optical Faces...", None, "face_roles_action",
     "Assign 2D sides, coatings and port roles to the faces of the selected CAD/STL solid row"),
    ("galvo_scan", "&Galvo Scan Overlay...", None, "galvo_scan_action",
     "The TiltX angles the selected mirror is drawn at"),
    ("grating_settings", "G&rating Settings...", None, "grating_settings_action",
     "Diffraction order, pitch and line angle for the selected row"),
    ("tolerance_preset", "Save &Tolerance Solve Preset...", None,
     "tolerance_preset_action",
     "Save the Monte Carlo settings, merit operands and tolerance roles as a preset"),
    ("apply_tolerance_preset", "&Apply Tolerance Solve Preset...", None,
     "apply_tolerance_preset_action",
     "Apply one of the layout's saved tolerance solve presets"),
    # the reports write to Debug and the clipboard; they ask and report through the UI host since
    # bugs/0943. Each export needs its report run first.
    ("tolerance_monte_carlo", "Tolerance &Monte Carlo Report...", None,
     "editor:open_tolerance_monte_carlo_report", "Perturb the tolerances N times and report the merit spread"),
    ("export_tolerance_monte_carlo_csv", "Export Tolerance Monte Carlo CSV...", None,
     "editor:export_tolerance_monte_carlo_csv", "Write the last Monte Carlo run's samples as CSV"),
    ("tolerance_worst_sample", "Tolerance &Worst-Sample Comparison...", None,
     "editor:open_tolerance_worst_sample_comparison_report", "Compare the worst Monte Carlo sample with nominal"),
    ("export_tolerance_comparison_csv", "Export Tolerance Comparison CSV...", None,
     "editor:export_tolerance_comparison_csv", "Write the worst-sample comparison as CSV"),
    ("tolerance_stackup", "Tolerance &Stack-Up Dashboard...", None,
     "editor:open_tolerance_stackup_dashboard_report", "Which tolerances drive the merit spread"),
    ("export_tolerance_stackup_csv", "Export Tolerance Stack-Up CSV...", None,
     "editor:export_tolerance_stackup_csv", "Write the stack-up dashboard as CSV"),
    ("tolerance_compensator", "Tolerance &Compensator Sweep...", None,
     "editor:open_tolerance_compensator_sweep_report", "Sweep each compensator over the Monte Carlo samples"),
    ("export_tolerance_compensator_csv", "Export Tolerance Compensator CSV...", None,
     "editor:export_tolerance_compensator_csv", "Write the compensator sweep as CSV"),
    ("tolerance_multi_compensator", "Tolerance Multi-Com&pensator Solve...", None,
     "editor:open_tolerance_multi_compensator_report", "Solve all compensators together, sample by sample"),
    ("export_tolerance_multi_compensator_csv", "Export Tolerance Multi-Compensator CSV...", None,
     "editor:export_tolerance_multi_compensator_csv", "Write the multi-compensator solve as CSV"),
    ("export_tolerance_overlay_csv", "Export Tolerance Overlay CSV...", None,
     "editor:export_tolerance_overlay_csv", "Write the current tolerance overlay view as CSV"),
    ("about", "&About", None, "about_action", "What this window is"),
    # Ctrl+Shift+B is the Tk editor's bug-flag key too
    ("flag_bug", "&Flag Bug", "Ctrl+Shift+B", "flag_bug_action",
     "Record a bug: a picture of this whole window and of every open dialog, the state of the "
     "layout and the panels, then a box to say what went wrong"),
    # ---- menu parity (bugs/0942): more Tk menu-bar commands that already work under the Qt shell
    # and only lacked a Qt route (File and Edit ones sit with their neighbours above)
    ("clear_cad_axis_offsets", "Clear CAD Axis Offsets", None, "editor:clear_step_axis_offsets",
     "Remove every imported STEP body's axis offsets"),
    ("clear_step_imports", "Clear STEP Imports", None, "editor:clear_step_imports",
     "Remove every imported STEP body from the 3D scene"),
    ("place_cad_solid", "3D Place/Orient Selected CAD/STL Solid", None,
     "editor:open_optical_stl_placement_assistant", "Place and orient the selected CAD/STL solid in 3D"),
    ("refresh_plot", "Refresh Plot", None, "editor:refresh_plot", "Re-trace and redraw the 2D plot"),
    ("folded_assembly", "Folded Assembly View...", None, "editor:open_folded_assembly_view",
     "The folded assembly in its own 3D window: per-arm reflections, isometric"),
    ("atmosphere_settings", "Atmospheric &Settings...", None, "editor:open_atmosphere_settings_dialog",
     "Refraction / dispersion inputs for the Atmos analysis: observatory, wavelengths, zenith angle, air"),
    ("benchmark_psf_mtf", "Benchmark PSF/MTF", None, "editor:benchmark_psf_mtf",
     "Time the PSF / MTF computation on this system"),
    ("copy_phase2_report", "Copy Phase 2 Report", None, "editor:copy_phase2_report_to_clipboard",
     "Copy the phase-2 analysis report to the clipboard"),
    ("copy_wavefront_fit", "Copy Wavefront Fit Report", None,
     "editor:copy_wavefront_fit_report_to_clipboard", "Copy the wavefront / Zernike fit report to the clipboard"),
    ("clear_zemax_wavefront", "Clear Zemax Wavefront Reference", None,
     "editor:clear_zemax_wavefront_reference", "Forget the imported Zemax wavefront reference"),
    ("clear_marks", "Clear Marks", None, "editor:clear_optimization_marks",
     "Remove the optimisation marks from the plot"),
    ("formula_sheet", "Optics Formula Sheet", None, "editor:show_formula_help",
     "The optics formula sheet"),
    ("manual_index", "Open Manual Index…", None, "editor:show_manual_index", "The user manual's index"),
    ("copy_debug", "Copy Debug", None, "editor:copy_debug_to_clipboard",
     "Copy the debug log to the clipboard"),
)

#: editor commands that change the model: the shell's views re-read it afterwards (bugs/0942)
EDITOR_REFRESH = {"undo", "redo", "reset_layout", "paste_rows_from_clipboard", "import_zemax_file",
                  "import_optical_stl_solid", "import_lens_step", "import_camera_step", "import_led_step",
                  "clear_step_axis_offsets", "clear_step_imports", "refresh_plot", "clear_zemax_wavefront_reference",
                  "clear_optimization_marks", "import_zemax_wavefront_map"}


#: shortcuts that act only while the surface table has focus -- the Tk editor binds Ctrl+C / Ctrl+V
#: on its table, and window-wide they would take copy away from every other view (bugs/0942)
TABLE_SHORTCUTS = {"copy_rows", "paste_rows"}


def editor_command(method: str) -> str | None:
    """The editor method an `ACTIONS` entry runs, or None when it is a main-window method."""
    return method.split(":", 1)[1] if method.startswith("editor:") else None


#: checkable actions -> their state at start-up
CHECKABLE = {"show_rays": True, "clean_scene": False, "hide_panels": False, "toolbar_3d": True}


class ActionManager:
    """Creates every QAction of the shell and keeps them under their names."""

    def __init__(self, main_window) -> None:
        self.main_window = main_window
        self.actions: dict[str, object] = {}

    def create_all_actions(self) -> dict[str, object]:
        from PySide6.QtGui import QAction, QKeySequence

        for name, text, shortcut, method, tooltip in ACTIONS:
            action = QAction(text, self.main_window)
            if name in CHECKABLE:
                action.setCheckable(True)
                action.setChecked(bool(CHECKABLE[name]))
            if shortcut:
                # "Ctrl+Y;Ctrl+Shift+Z": more than one key, as the Tk editor binds them
                action.setShortcuts([QKeySequence(key) for key in shortcut.split(";")])
            action.setToolTip(tooltip)
            command = editor_command(method)
            if command is not None:
                handler = (lambda _checked=False, c=command: self.main_window.run_editor_command(c))
            else:
                handler = getattr(self.main_window, method)
            action.triggered.connect(handler)
            self.actions[name] = action
        return self.actions

    def __getitem__(self, name):
        return self.actions[name]
