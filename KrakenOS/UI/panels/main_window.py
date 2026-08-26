"""Main layout editor window and menu construction."""

from __future__ import annotations

from typing import Any
import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from KrakenOS.UI.widgets import (
    grid_command_button,
    pack_command_button,
    pack_commit_checkbutton,
    pack_commit_combobox,
)


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class MainWindowBuilder:
    """Build the main Tk menu and window layout while delegating state."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.editor)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open", command=self.open_layout)
        file_menu.add_command(label="Reset", command=self.reset_layout)
        file_menu.add_separator()
        file_menu.add_command(label="Import Zemax File...", command=self.import_zemax_file)
        file_menu.add_command(label="Import Zemax Wavefront Map...", command=self.import_zemax_wavefront_map)
        file_menu.add_command(label="Import Stock Lens...", command=self.open_stock_lens_importer)
        file_menu.add_command(label="Import Optical CAD/STL Solid...", command=self.import_optical_stl_solid)
        file_menu.add_command(label="Measure MTF from Image...", command=self.open_mtf_from_image_dialog)
        file_menu.add_command(label="Glass Catalog Browser...", command=self.open_glass_catalog_browser)
        file_menu.add_command(label="Save", command=self.save_layout)
        file_menu.add_command(label="Save As", command=self.save_layout_as)
        file_menu.add_separator()
        file_menu.add_command(label="Import Imaging Lens STEP...", command=self.import_lens_step)
        file_menu.add_command(label="Import Camera STEP...", command=self.import_camera_step)
        file_menu.add_command(label="Import LED STEP...", command=self.import_led_step)
        file_menu.add_command(label="Clear CAD Axis Offsets", command=self.clear_step_axis_offsets)
        file_menu.add_command(label="Clear STEP Imports", command=self.clear_step_imports)
        file_menu.add_separator()
        file_menu.add_command(label="Lens Drawing Surface Properties...", command=self._open_lens_drawing_surface_properties_dialog)
        file_menu.add_command(label="Export Lens Drawing...", command=self.export_lens_drawing)
        file_menu.add_command(label="Export 3D STEP...", command=self.export_3d_step)
        file_menu.add_command(label="Export 3D View DXF...", command=self.export_3d_view_dxf)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.request_quit)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(
            label="Copy Selected Surfaces/Elements",
            command=self.copy_selected_rows_to_clipboard,
            accelerator="Ctrl+C",
        )
        edit_menu.add_command(
            label="Paste Surfaces/Elements",
            command=self.paste_rows_from_clipboard,
            accelerator="Ctrl+V",
        )
        self._edit_menu = edit_menu
        menubar.add_cascade(label="Edit", menu=edit_menu)

        insert_menu = tk.Menu(menubar, tearoff=0)
        component_menu = tk.Menu(insert_menu, tearoff=0)
        component_menu.add_command(label="Load layouts first", state="disabled")
        insert_menu.add_cascade(label="Common Component", menu=component_menu)
        insert_menu.add_command(label="Stock Lens Catalog...", command=self.open_stock_lens_importer)
        insert_menu.add_command(label="Optical CAD/STL Solid...", command=self.import_optical_stl_solid)
        insert_menu.add_separator()
        insert_menu.add_command(
            label="Component to Current Path View...",
            command=self.open_current_path_component_placement,
        )
        insert_menu.add_command(
            label="Stock Lens to Current Path View...",
            command=self.open_current_path_stock_lens_placement,
        )
        self.insert_menu = insert_menu
        self._insert_component_menu = component_menu
        menubar.add_cascade(label="Insert", menu=insert_menu)

        action_menu = tk.Menu(menubar, tearoff=0)
        action_menu.add_command(label="Refresh Plot", command=self.refresh_plot)
        action_menu.add_command(label="Inspect Ray / Surface Physics", command=self.open_ray_inspector)
        action_menu.add_command(label="Ray Inspector", command=self.open_ray_inspector)
        action_menu.add_command(label="Trace Path Inspector", command=self.open_branch_tree_inspector)
        action_menu.add_command(label="Path Throughput Report", command=self.open_branch_throughput_report)
        action_menu.add_command(label="Detector Aperture Report", command=self.open_detector_aperture_report)
        action_menu.add_command(label="Source Illumination Report", command=self.open_source_illumination_report)
        action_menu.add_command(label="Add Component to Current Path View...", command=self.open_current_path_component_placement)
        action_menu.add_command(label="Add Stock Lens to Current Path View...", command=self.open_current_path_stock_lens_placement)
        action_menu.add_command(label="Scene Source Manager...", command=self.open_scene_source_manager)
        action_menu.add_command(label="Non-Sequential Scene Graph", command=self.open_nonseq_scene_graph)
        action_menu.add_command(label="Inspect Optical CAD/STL Solids", command=self.open_optical_stl_diagnostics)
        action_menu.add_command(label="Assign CAD/STL Optical Faces", command=self.open_optical_solid_face_role_editor)
        action_menu.add_command(label="3D Place/Orient Selected CAD/STL Solid", command=self.open_optical_stl_placement_assistant)
        action_menu.add_command(label="System Selection Calculator...", command=self.open_system_selection_calculator)
        action_menu.add_command(label="Camera + Lens Matcher...", command=self.open_camera_lens_matcher)
        action_menu.add_command(label="Paraxial Matrix Report", command=self.open_paraxial_matrix_report)
        action_menu.add_command(label="Gaussian Beam Report", command=self.open_gaussian_beam_report)
        action_menu.add_command(label="Branch Gaussian Q Report", command=self.open_branch_gaussian_q_report)
        action_menu.add_command(label="Atmospheric Settings...", command=self.open_atmosphere_settings_dialog)
        action_menu.add_command(label="Save Tolerance Solve Preset...", command=self.open_save_tolerance_solve_preset_dialog)
        action_menu.add_command(label="Apply Tolerance Solve Preset...", command=self.open_apply_tolerance_solve_preset_dialog)
        action_menu.add_command(label="Tolerance Monte Carlo Report...", command=self.open_tolerance_monte_carlo_report)
        action_menu.add_command(label="Export Tolerance Monte Carlo CSV...", command=self.export_tolerance_monte_carlo_csv)
        action_menu.add_command(label="Tolerance Worst-Sample Comparison...", command=self.open_tolerance_worst_sample_comparison_report)
        action_menu.add_command(label="Export Tolerance Comparison CSV...", command=self.export_tolerance_comparison_csv)
        action_menu.add_command(label="Tolerance Stack-Up Dashboard...", command=self.open_tolerance_stackup_dashboard_report)
        action_menu.add_command(label="Export Tolerance Stack-Up CSV...", command=self.export_tolerance_stackup_csv)
        action_menu.add_command(label="Tolerance Compensator Sweep...", command=self.open_tolerance_compensator_sweep_report)
        action_menu.add_command(label="Export Tolerance Compensator CSV...", command=self.export_tolerance_compensator_csv)
        action_menu.add_command(label="Tolerance Multi-Compensator Solve...", command=self.open_tolerance_multi_compensator_report)
        action_menu.add_command(label="Export Tolerance Multi-Compensator CSV...", command=self.export_tolerance_multi_compensator_csv)
        action_menu.add_command(label="Export Tolerance Overlay CSV...", command=self.export_tolerance_overlay_csv)
        action_menu.add_command(label="Benchmark PSF/MTF", command=self.benchmark_psf_mtf)
        action_menu.add_command(label="Copy Phase 2 Report", command=self.copy_phase2_report_to_clipboard)
        action_menu.add_command(label="Copy Wavefront Fit Report", command=self.copy_wavefront_fit_report_to_clipboard)
        action_menu.add_command(label="Export Wavefront CSV...", command=self.export_wavefront_csv)
        action_menu.add_command(label="Export Zernike CSV...", command=self.export_zernike_csv)
        action_menu.add_command(label="Clear Zemax Wavefront Reference", command=self.clear_zemax_wavefront_reference)
        action_menu.add_command(label="Export Path PSF CSV...", command=self.export_branch_psf_csv)
        action_menu.add_command(label="Export Path MTF CSV...", command=self.export_branch_mtf_csv)
        action_menu.add_command(label="Export Detector Map CSV...", command=self.export_detector_map_csv)
        action_menu.add_command(label="Export Coherent Detector CSV...", command=self.export_coherent_detector_csv)
        action_menu.add_command(label="Export Branch Field CSV...", command=self.export_branch_field_csv)
        action_menu.add_command(label="Copy Debug", command=self.copy_debug_to_clipboard)
        action_menu.add_command(label="Clear Marks", command=self.clear_optimization_marks)
        action_menu.add_checkbutton(label="Auto-save 2D PNG", variable=self.auto_save_plot_var)
        menubar.add_cascade(label="Actions", menu=action_menu)

        self.layout_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Layouts", menu=self.layout_menu)

        self.machine_vision_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Machine Vision", menu=self.machine_vision_menu)

        self.example_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Examples", menu=self.example_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Paraxial Calculator", command=self.open_paraxial_calculator)
        help_menu.add_command(label="Optics Formula Sheet", command=self.show_formula_help)
        help_menu.add_separator()

        def _add_doc_group(parent: tk.Menu, label: str, entries: list[tuple[str, str]], section: str) -> None:
            submenu = tk.Menu(parent, tearoff=0)
            for entry_label, page in entries:
                submenu.add_command(
                    label=entry_label,
                    command=lambda p=page, l=entry_label, s=section: self._open_sphinx_docs_page(p, l, section=s),
                )
            parent.add_cascade(label=label, menu=submenu)

        _add_doc_group(help_menu, "Knowledge Base  (Theory)", [
            ("Rules of Thumb  (Optics · Imaging · Laser)", "rules_of_thumb"),
            ("Cardinal Points  (EP / XP / PP)",            "cardinal_points"),
            ("Pupil Sampling  (Fans · Hexapolar · Vogel)", "pupil_sampling"),
            ("Lens Design Families  (Photo / Machine Vision)", "lens_design_intro"),
            ("IR Sub-pixel Hot-Spot Detection",            "ir_subpixel_detection"),
        ], section="knowledge_base")

        _add_doc_group(help_menu, "Tools & Analysis", [
            ("Analysis Tools Reference  (Spot, PSF, MTF, Seidel, …)", "analysis_tools"),
            ("Paraxial Matrix Tool",                         "parax_tool"),
            ("PupilCalc Tool",                               "pupilcalc_tool"),
            ("Pupil Patterns",                               "pupil_patterns"),
            ("Pupil / Paraxial Analysis",                    "pupil_paraxial_analysis"),
            ("Gaussian Beams",                               "gaussian_beams"),
        ], section="manual")

        _add_doc_group(help_menu, "Model & Workflow", [
            ("Core Model",                       "core_model"),
            ("Classes and Attributes",           "classes_and_attributes"),
            ("Working with the Library",         "working_with_library"),
            ("Editable Table",                   "editable_table"),
            ("Tracing and Ray Data",             "tracing_and_ray_data"),
            ("Non-Sequential First Design",      "nonsequential_first_design"),
            ("Zemax Rayfile Sources",            "zemax_rayfile_sources"),
            ("Beam Splitters",                   "beam_splitters"),
            ("Diffuse Scattering",               "diffuse_scattering"),
            ("Lens Fabrication Drawings",        "lens_fabrication_drawings"),
            ("2D Viewers",                       "viewers"),
            ("3D Viewer",                        "viewer_3d"),
        ], section="manual")

        _add_doc_group(help_menu, "Examples & References", [
            ("Examples",                "examples"),
            ("References",              "references"),
            ("Installation Notes",      "installation"),
        ], section="manual")

        help_menu.add_separator()
        help_menu.add_command(label="Open Manual Index…", command=self.show_manual_index)
        help_menu.add_command(
            label="Open Knowledge Base Index…",
            command=lambda: self._open_sphinx_docs_page("index", "Knowledge Base Index", section="knowledge_base"),
        )
        menubar.add_cascade(label="Help", menu=help_menu)

        self._menubar = menubar
        self.config(menu=menubar)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        le = _layout_module()
        ARM_VIEW_DEFAULT = le.ARM_VIEW_DEFAULT
        COLUMN_LABELS = le.COLUMN_LABELS
        FIELDS = le.FIELDS
        RAY_DISPLAY_VALUES = le.RAY_DISPLAY_VALUES

        style = ttk.Style(self.editor)
        style.configure(
            "Excel.Treeview",
            background="white",
            fieldbackground="white",
            bordercolor="#d9dee7",
            borderwidth=1,
            relief="solid",
            rowheight=24,
        )
        style.configure(
            "Excel.Treeview.Heading",
            bordercolor="#d9dee7",
            borderwidth=1,
            relief="solid",
        )
        style.map(
            "Excel.Treeview",
            # Native selection is cleared by the editor so this is only a
            # fallback. The visible selection is the explicit border overlay.
            background=[("selected", "")],
            foreground=[("selected", "black")],
        )

        body = ttk.Frame(self.editor)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        self.body_frame = body

        self.left_restore_frame = ttk.Frame(body, padding=(2, 8, 2, 8))
        grid_command_button(
            self.left_restore_frame,
            0,
            0,
            text="▶",
            width=2,
            command=self.toggle_left_sidebar,
            sticky="n",
        )
        self.left_restore_frame.grid(row=0, column=0, sticky="ns")
        self.left_restore_frame.grid_remove()

        main = ttk.Panedwindow(body, orient=tk.HORIZONTAL)
        main.grid(row=0, column=1, sticky="nsew")
        self.main_pane = main

        self.right_restore_frame = ttk.Frame(body, padding=(2, 8, 2, 8))
        grid_command_button(
            self.right_restore_frame,
            0,
            0,
            text="◀",
            width=2,
            command=self.toggle_right_sidebar,
            sticky="n",
        )
        self.right_restore_frame.grid(row=0, column=2, sticky="ns")
        self.right_restore_frame.grid_remove()

        control_host = ttk.Frame(main, padding=(8, 8, 4, 8))
        control_host.columnconfigure(0, weight=1)
        control_host.rowconfigure(1, weight=1)
        self.left_sidebar_host = control_host
        main.add(control_host, weight=0)

        control_header = ttk.Frame(control_host)
        control_header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        control_header.columnconfigure(0, weight=1)
        ttk.Label(control_header, text="Controls").grid(row=0, column=0, sticky="w")
        grid_command_button(
            control_header,
            0,
            1,
            text="◀",
            width=2,
            command=self.toggle_left_sidebar,
            sticky="e",
        )

        self.control_canvas = tk.Canvas(control_host, highlightthickness=0, borderwidth=0)
        self.control_canvas.grid(row=1, column=0, sticky="nsew")
        control_scroll = ttk.Scrollbar(control_host, orient="vertical", command=self.control_canvas.yview)
        control_scroll.grid(row=1, column=1, sticky="ns", padx=(6, 0))
        self.control_canvas.configure(yscrollcommand=control_scroll.set)

        control_stack = ttk.Frame(self.control_canvas)
        control_stack.columnconfigure(0, weight=1)
        self.control_stack_window = self.control_canvas.create_window((0, 0), window=control_stack, anchor="nw")
        control_stack.bind("<Configure>", self._on_control_stack_configure)
        self.control_canvas.bind("<Configure>", self._on_control_canvas_configure)
        self.bind_all("<MouseWheel>", self._on_left_panel_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_left_panel_mousewheel, add="+")
        self.bind_all("<Button-5>", self._on_left_panel_mousewheel, add="+")

        controls = ttk.LabelFrame(control_stack, text="Display", padding=8)
        controls.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        for column in range(2):
            controls.columnconfigure(column, weight=1, uniform="display_cols")

        field_panel = ttk.LabelFrame(control_stack, text="Field", padding=8)
        self.field_panel = field_panel
        field_panel.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        for column in range(2):
            field_panel.columnconfigure(column, weight=1, uniform="field_cols")

        # bugs/0403: the 2D editor's Source panel STAYS (0402 hid the wrong one). The redundant
        # source editor to retire is the Open 3D inspector's Live-Controls "Source" section, not this.
        source_panel = ttk.LabelFrame(control_stack, text="Source", padding=8)
        source_panel.grid(row=0, column=0, sticky="ew")
        for column in range(2):
            source_panel.columnconfigure(column, weight=1, uniform="source_cols")

        le = _layout_module()
        self.display_orientation_var = tk.StringVar(value="YZ")
        self.projection_display_mode_var = tk.StringVar(value=le.PROJECTION_MODE_FULL_3D)
        self.atmosphere_hidden_panel = ttk.Frame(control_stack)
        self._build_atmosphere_panel(self.atmosphere_hidden_panel)

        center_panel = ttk.Panedwindow(main, orient=tk.VERTICAL)
        self.center_panel = center_panel
        main.add(center_panel, weight=4)

        table_frame = ttk.Frame(center_panel, padding=8)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(1, weight=1)
        center_panel.add(table_frame, weight=2)

        plot_frame = ttk.Frame(center_panel, padding=8)
        plot_frame.columnconfigure(0, weight=1)
        plot_frame.rowconfigure(1, weight=1)
        center_panel.add(plot_frame, weight=4)

        right_host = ttk.Frame(main, padding=(4, 8, 8, 8))
        right_host.columnconfigure(0, weight=1)
        right_host.rowconfigure(1, weight=1)
        self.right_sidebar_host = right_host
        main.add(right_host, weight=1)

        right_header = ttk.Frame(right_host)
        right_header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        right_header.columnconfigure(0, weight=1)
        ttk.Label(right_header, text="Panels").grid(row=0, column=0, sticky="w")
        grid_command_button(
            right_header,
            0,
            1,
            text="▶",
            width=2,
            command=self.toggle_right_sidebar,
            sticky="e",
        )

        right_panel = ttk.Panedwindow(right_host, orient=tk.VERTICAL)
        right_panel.grid(row=1, column=0, sticky="nsew")
        self.right_panel = right_panel

        info_stack = ttk.Panedwindow(right_panel, orient=tk.VERTICAL)
        right_panel.add(info_stack, weight=3)

        results = ttk.LabelFrame(info_stack, text="Information", padding=8)
        results.columnconfigure(0, weight=1)
        results.rowconfigure(0, weight=1)
        info_stack.add(results, weight=3)

        optimization = ttk.LabelFrame(info_stack, text="Optimization", padding=8)
        optimization.columnconfigure(0, weight=1)
        optimization.rowconfigure(2, weight=0)
        info_stack.add(optimization, weight=2)

        bottom = ttk.Panedwindow(right_panel, orient=tk.VERTICAL)
        right_panel.add(bottom, weight=1)

        progress_frame = ttk.LabelFrame(bottom, text="Progress", padding=8)
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(1, weight=1)
        bottom.add(progress_frame, weight=1)

        debug_frame = ttk.LabelFrame(bottom, text="Debug", padding=8)
        debug_frame.columnconfigure(0, weight=1)
        debug_frame.rowconfigure(0, weight=1)
        bottom.add(debug_frame, weight=1)

        table_toolbar = ttk.Frame(table_frame)
        table_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        pack_command_button(table_toolbar, "Add surface", command=self.add_surface)
        pack_command_button(table_toolbar, "Delete", command=self.delete_selected, padx=(6, 0))
        pack_command_button(table_toolbar, "Duplicate", command=self.duplicate_selected, padx=(6, 0))
        pack_command_button(table_toolbar, "Advanced...", command=self.open_advanced_surface_editor, padx=(6, 0))
        pack_command_button(table_toolbar, "Shape...", command=self.open_surface_shape_builder, padx=(6, 0))
        pack_command_button(table_toolbar, "Coating...", command=self.open_coating_material_editor, padx=(6, 0))
        pack_command_button(table_toolbar, "Error Map...", command=self.open_error_map_editor, padx=(6, 0))
        pack_command_button(table_toolbar, "Flip", command=self.flip_selected, padx=(6, 0))
        pack_command_button(table_toolbar, "▲", command=self.move_up, width=3, padx=(10, 0))
        pack_command_button(table_toolbar, "▼", command=self.move_down, width=3, padx=(4, 0))
        arm_view_menu = pack_commit_combobox(
            table_toolbar,
            textvariable=self.arm_view_var,
            values=(ARM_VIEW_DEFAULT,),
            on_commit=self.set_arm_view,
            width=22,
            side="right",
            padx=(10, 0),
        )
        self.arm_view_menu = arm_view_menu
        ttk.Label(table_toolbar, text="Path view").pack(side="right", padx=(12, 4))

        self.table = ttk.Treeview(
            table_frame,
            columns=FIELDS,
            show="headings",
            selectmode="extended",
            style="Excel.Treeview",
        )
        for field in FIELDS:
            self.table.heading(field, text=COLUMN_LABELS[field])
            width = (
                55 if field == "label"
                else 140 if field == "surface"
                else 160 if field == "name"
                else 120 if field == "glass"
                else 105 if field == "in_diameter"
                else 95 if field in {"tilt_x", "tilt_y", "tilt_z"}
                else 95 if field in {"desp_x", "desp_y", "desp_z"}
                else 85 if field == "axis_move"
                else 110
            )
            self.table.column(field, width=width, stretch=True, anchor="center")
        self._install_border_only_table_selection()
        self.table.grid(row=1, column=0, sticky="nsew")
        self.table.bind("<Button-1>", self._on_table_click, add="+")
        self.table.bind("<B1-Motion>", self._on_table_drag, add="+")
        self.table.bind("<ButtonRelease-1>", self._on_table_button_release, add="+")
        self.table.bind("<Double-1>", self.begin_edit)
        self.table.bind("<Button-3>", self.show_context_menu)
        self.table.bind("<<TreeviewSelect>>", self._update_active_cell_border, add="+")
        self.table.bind("<<TreeviewSelect>>", self._on_table_selection_changed, add="+")
        self.table.bind("<Control-c>", self.copy_selected_rows_to_clipboard, add="+")
        self.table.bind("<Control-C>", self.copy_selected_rows_to_clipboard, add="+")
        self.table.bind("<Control-Insert>", self.copy_selected_rows_to_clipboard, add="+")
        self.table.bind("<Control-v>", self.paste_rows_from_clipboard, add="+")
        self.table.bind("<Control-V>", self.paste_rows_from_clipboard, add="+")
        self.table.bind("<Shift-Insert>", self.paste_rows_from_clipboard, add="+")
        self.table.bind("<Configure>", self._update_active_cell_border, add="+")
        self.table.bind("<Configure>", self._schedule_table_grid_update, add="+")
        self.table.bind("<MouseWheel>", self._update_active_cell_border, add="+")
        self.table.bind("<MouseWheel>", self._schedule_table_grid_update, add="+")
        self.table.bind("<Button-4>", self._update_active_cell_border, add="+")
        self.table.bind("<Button-4>", self._schedule_table_grid_update, add="+")
        self.table.bind("<Button-5>", self._update_active_cell_border, add="+")
        self.table.bind("<Button-5>", self._schedule_table_grid_update, add="+")
        self.table.bind("<Left>", self._move_active_cell)
        self.table.bind("<Right>", self._move_active_cell)
        self.table.bind("<Up>", self._move_active_cell)
        self.table.bind("<Down>", self._move_active_cell)
        self.table.bind("<KP_Left>", self._move_active_cell)
        self.table.bind("<KP_Right>", self._move_active_cell)
        self.table.bind("<KP_Up>", self._move_active_cell)
        self.table.bind("<KP_Down>", self._move_active_cell)
        self.table.bind("<Escape>", self._clear_table_selection_event)
        self.bind_all("<Button-1>", self._dismiss_popup_menu_event, add="+")
        self.bind_all("<ButtonRelease-1>", self._dismiss_popup_menu_event, add="+")
        self.bind_all("<Escape>", self._dismiss_popup_menu_event, add="+")
        self.table.tag_configure("scene_source", background="#dff6ff", foreground="#0f4c81")
        for tag, color in self._element_tag_palette():
            self.table.tag_configure(tag, background=color)

        border_color = "#4a89ff"
        self._cell_border_parts = [
            tk.Frame(self.table, bg=border_color, height=2, width=2),
            tk.Frame(self.table, bg=border_color, height=2, width=2),
            tk.Frame(self.table, bg=border_color, height=2, width=2),
            tk.Frame(self.table, bg=border_color, height=2, width=2),
        ]
        self._selection_border_overlays: list[tk.Frame] = []
        self._selection_anchor_row: str | None = None
        self._hide_active_cell_border()

        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        yscroll.grid(row=1, column=1, sticky="ns")
        self.table.configure(yscrollcommand=lambda first, last: self._on_table_scroll(yscroll, first, last))
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self._on_table_xview)
        xscroll.grid(row=2, column=0, sticky="ew")
        self.table.configure(xscrollcommand=lambda first, last: self._on_table_xscroll(xscroll, first, last))

        self._build_controls_panel(controls)
        self._build_field_panel(field_panel)
        self._build_source_panel(source_panel)
        self._build_results_panel(results)
        self._build_optimization_panel(optimization)

        plot_toolbar = ttk.Frame(plot_frame)
        plot_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        plot_toolbar.columnconfigure(0, weight=1)
        plot_toolbar_main = ttk.Frame(plot_toolbar)
        plot_toolbar_main.grid(row=0, column=0, sticky="ew")
        plot_toolbar_analysis = ttk.Frame(plot_toolbar)
        plot_toolbar_analysis.grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.external_camera_var = tk.StringVar(value="None")
        self.camera_overlay_mode_var = tk.StringVar(value="Off")
        open_3d_button = pack_command_button(plot_toolbar_main, "Open 3D", command=self.open_3d_view)
        self._add_widget_tooltip(open_3d_button, "Open 3D optical layout view")
        self.layout_preview_mode_var = tk.StringVar(value=self.layout_preview_mode)
        self.show_layout_2d_var = tk.BooleanVar(value=bool(getattr(self, "show_layout_2d", True)))
        preview_button = pack_commit_checkbutton(
            plot_toolbar_main,
            text="2D",
            variable=self.show_layout_2d_var,
            command=self.toggle_layout_2d,
            padx=(6, 0),
        )
        self._add_widget_tooltip(
            preview_button,
            "Show or hide the 2D optical layout pane (off frees space for analysis plots)",
        )
        ttk.Label(plot_toolbar_main, text="Plane").pack(side="left", padx=(10, 2))
        self.display_orientation_menu = pack_commit_combobox(
            plot_toolbar_main,
            textvariable=self.display_orientation_var,
            width=5,
            values=["YZ", "XZ", "XY", "All"],
            on_commit=self._on_display_plane_changed,
            on_focus_in=self._begin_history_capture,
        )
        self._add_widget_tooltip(
            self.display_orientation_menu,
            "Choose the primary 2D projection plane for the editable layout plot",
        )
        self.projection_display_mode_buttons = []
        self._main_analysis_toolbar_panel().build(plot_toolbar_analysis)
        cardinal_button = pack_commit_checkbutton(
            plot_toolbar_main,
            text="Show PP / EP / XP",
            variable=self.show_cardinals_var,
            command=self._on_toggle_cardinal_markers,
            padx=(12, 0),
        )
        self._add_widget_tooltip(cardinal_button, "Show principal plane, entrance pupil, and exit pupil markers")
        label_button = pack_commit_checkbutton(
            plot_toolbar_main,
            text="Show labels",
            variable=self.show_path_labels_var,
            command=self._on_toggle_path_labels,
            padx=(6, 0),
        )
        self._add_widget_tooltip(
            label_button,
            "Show or hide path, source, and surface labels in the 2D layout plot",
        )
        ttk.Label(plot_toolbar_main, text="Rays").pack(side="left", padx=(8, 2))
        ray_display_menu = pack_commit_combobox(
            plot_toolbar_main,
            textvariable=self.ray_display_mode_var,
            width=18,
            values=RAY_DISPLAY_VALUES,
            on_commit=self._on_ray_display_mode_changed,
        )
        self._add_widget_tooltip(
            ray_display_menu,
            "Choose whether the 2D plot shows every traced ray, detector-hit rays, or representative non-primary beam-splitter paths",
        )
        physical_distance_button = pack_commit_checkbutton(
            plot_toolbar_main,
            text="Physical Distance",
            variable=self.show_physical_distances_var,
            command=self._on_toggle_physical_distances,
            padx=(6, 0),
        )
        self._add_widget_tooltip(physical_distance_button, "Annotate physical distances in the 2D layout and Open 3D views")
        trace_button = pack_command_button(plot_toolbar_main, "Trace", command=self.open_ray_inspector, side="right", padx=(0, 6))
        self._add_widget_tooltip(trace_button, "Inspect ray / surface physics")
        update_button = pack_command_button(plot_toolbar_main, "Update", command=self._manual_update_plot, side="right")
        self._add_widget_tooltip(update_button, "Trace rays and refresh the plot + selected analyses")
        # bugs/0646: loads are fast (geometry only); this is the explicit first trace.
        trace_now_button = pack_command_button(plot_toolbar_main, "Trace Now", command=self._trace_now, side="right", padx=(0, 6))
        self._add_widget_tooltip(trace_now_button, "Trace the rays deferred by the fast load (no analysis panels)")
        flag_bug_button = pack_command_button(
            plot_toolbar_main, "● Flag bug", command=self.flag_bug_2d, side="right", padx=(0, 6)
        )
        self._add_widget_tooltip(
            flag_bug_button,
            "Capture a full-screen shot + layout + prescription state and describe a bug "
            "(records oversized/off-screen dialogs too). Shortcut: Ctrl+Shift+B",
        )

        self.figure = Figure(figsize=(7, 5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        self.canvas.mpl_connect("motion_notify_event", self._on_plot_canvas_motion)
        self.canvas.mpl_connect("figure_leave_event", self._on_plot_canvas_leave)
        self.canvas.get_tk_widget().bind("<Button-1>", self._on_plot_widget_click, add="+")

        self.debug_text = tk.Text(debug_frame, wrap="word", height=8, width=24)
        self.debug_text.grid(row=0, column=0, sticky="nsew")
        debug_scroll = ttk.Scrollbar(debug_frame, orient="vertical", command=self.debug_text.yview)
        debug_scroll.grid(row=0, column=1, sticky="ns")
        self.debug_text.configure(yscrollcommand=debug_scroll.set)
        self._bind_text_copy_shortcuts(self.debug_text)
        debug_actions = ttk.Frame(debug_frame)
        debug_actions.grid(row=1, column=0, sticky="w", pady=(6, 0))
        pack_command_button(
            debug_actions,
            "Copy Selected",
            command=lambda: self._copy_selection_from_text_widget(self.debug_text),
        )
        pack_command_button(
            debug_actions,
            "Copy All",
            command=lambda: self._copy_all_from_text_widget(self.debug_text),
            padx=(6, 0),
        )

        status_bar = ttk.Frame(progress_frame)
        status_bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        status_bar.columnconfigure(1, weight=1)
        self.progress_spinner_var = tk.StringVar(value="idle")
        self.progress_percent_var = tk.StringVar(value="0%")
        self.progress_bar_var = tk.DoubleVar(value=0.0)
        ttk.Label(status_bar, textvariable=self.progress_spinner_var, width=4).grid(row=0, column=0, sticky="w")
        self.progress_bar = ttk.Progressbar(
            status_bar,
            orient="horizontal",
            mode="determinate",
            maximum=100.0,
            variable=self.progress_bar_var,
        )
        self.progress_bar.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Label(status_bar, textvariable=self.progress_percent_var, width=14).grid(
            row=0, column=2, sticky="e"
        )

        self.progress_text = tk.Text(progress_frame, wrap="word", height=8, width=24)
        self.progress_text.grid(row=1, column=0, sticky="nsew")
        progress_scroll = ttk.Scrollbar(progress_frame, orient="vertical", command=self.progress_text.yview)
        progress_scroll.grid(row=1, column=1, sticky="ns")
        self.progress_text.configure(yscrollcommand=progress_scroll.set)
        self._bind_text_copy_shortcuts(self.progress_text)
        self._bind_text_context_menu(self.debug_text)
        self._bind_text_context_menu(self.progress_text)

        status_bar = ttk.Frame(self.editor)
        status_bar.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 2))
        status_bar.columnconfigure(0, weight=0)
        status_bar.columnconfigure(1, weight=1)
        status_bar.columnconfigure(2, weight=0)
        self.status_var = tk.StringVar(value="Ready")
        self.status_hint_var = tk.StringVar(value="")
        self.trace_state_badge_var = tk.StringVar(value="Scene: Auto")
        ttk.Label(status_bar, textvariable=self.status_var, anchor="w").grid(row=0, column=0, sticky="w")
        ttk.Label(
            status_bar,
            textvariable=self.status_hint_var,
            anchor="e",
            justify="right",
            foreground="#475569",
        ).grid(row=0, column=1, sticky="ew", padx=(12, 0))
        ttk.Label(
            status_bar,
            textvariable=self.trace_state_badge_var,
            anchor="e",
            foreground="#0f766e",
        ).grid(row=0, column=2, sticky="e", padx=(12, 0))
        self.after_idle(self._set_initial_pane_layout)
        self.bind("<Configure>", self._maybe_refresh_initial_pane_layout, add="+")
