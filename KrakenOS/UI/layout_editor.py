"""Simple KrakenOS layout editor.

This is an initial editor scaffold that mirrors the RayTracing workflow:
- file-backed starter layouts
- editable surface table
- embedded axial sketch with a small traced ray fan
"""

from __future__ import annotations

import importlib.util
import io
import json
import ast
import atexit
import csv
import hashlib
from itertools import product
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
import ctypes
from dataclasses import asdict
import multiprocessing as mp
import os
from pathlib import Path
from pprint import pformat
from queue import Empty, Queue
import random
import re
import signal
import shutil
import subprocess
import sys
import textwrap
import threading
import time
import traceback
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, simpledialog, ttk
import warnings
import webbrowser

from matplotlib import colormaps
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import MaxNLocator
from matplotlib.transforms import Bbox
import numpy as np

import KrakenOS as Kos
from KrakenOS.Optimization import (
    OPERAND_REGISTRY,
    VARIABLE_REGISTRY,
    MeritEvaluator,
    MeritFunction,
    MTFAtFrequencyOperand,
    OpticalVariable,
)
from KrakenOS.Optimization.adapters.pygmo2_adapter import Pygmo2MeritProblem
from KrakenOS.Optimization.pygmo_backend import import_pygmo, probe_pygmo_backend
from KrakenOS.UI.camera_database import (
    CAMERA_NONE_LABEL,
    camera_image_diameter_mm,
    camera_names,
    camera_record,
    camera_short_summary,
)
from KrakenOS.UI import cad_import_service
from KrakenOS.UI.auto_leg_graph import (
    auto_leg_candidate_key,
    auto_leg_direction_from_node,
    auto_leg_hit_point_index,
    auto_leg_midpoint,
    auto_leg_node_for_hit,
    auto_leg_node_label,
    auto_leg_point_key,
    auto_leg_representative_polyline,
    build_auto_leg_entries_from_projected,
    leg_geometry_from_points,
    ordered_auto_leg_keys,
)
from KrakenOS.UI.branch_gaussian_q_report import (
    BRANCH_GAUSSIAN_Q_CSV_COLUMNS,
    branch_gaussian_q_report_text,
    branch_gaussian_q_summary_text,
    branch_gaussian_q_table_values,
    collect_branch_gaussian_q_records,
    default_branch_gaussian_q_beam,
)
from KrakenOS.UI.branch_throughput_analysis import (
    BRANCH_THROUGHPUT_TABLE_COLUMNS,
    BRANCH_THROUGHPUT_TABLE_HEADINGS,
    BRANCH_THROUGHPUT_TABLE_LAYOUT,
    branch_output_label,
    branch_path_selector_sequence,
    branch_throughput_filter_choices,
    branch_throughput_filter_matches,
    branch_throughput_report_text,
    branch_throughput_summary_text,
    branch_throughput_table_values,
    collect_branch_throughput_records,
    filtered_branch_throughput_records,
    normalize_branch_throughput_filter_label,
    write_branch_throughput_csv,
)
from KrakenOS.UI.coherent_detector_analysis import (
    COHERENT_SUM_MODE_DEFAULT,
    COHERENT_SUM_MODE_VALUES,
    normalize_coherent_sum_mode,
)
from KrakenOS.UI.detector_aperture_analysis import (
    DETECTOR_APERTURE_TABLE_COLUMNS,
    DETECTOR_APERTURE_TABLE_HEADINGS,
    DETECTOR_APERTURE_TABLE_LAYOUT,
    DETECTOR_APERTURE_RECORD_STATUS_COLUMNS,
    collect_detector_aperture_records,
    detector_aperture_record_status,
    detector_aperture_report_text,
    detector_aperture_summary_text,
    detector_aperture_table_values,
    write_detector_aperture_csv,
)
from KrakenOS.UI.custom_surfaces import decode_custom_surface_value, encode_custom_surface_value
from KrakenOS.UI.lens_drawing_export import export_lens_drawing, identify_elements
from KrakenOS.UI.lens_drawing_properties import (
    DRAWING_PROPERTIES_ATTR,
    DRAWING_PROPERTY_FIELDS,
    apply_surface_properties_payload,
    drawing_properties,
    format_property_value,
    normalize_drawing_properties,
    surface_properties_payload,
    validate_drawing_properties,
)
from KrakenOS.UI.layout_plot_controller import (
    active_plot_modes,
    analysis_mode_label,
    arm_ray_label_plan,
    arm_ray_label_targets,
    build_preview_trace_signature,
    distance_to_polyline,
    find_nearest_pick_region,
    find_nearest_ray_region,
    filter_projected_labels_for_rows_and_sources,
    filter_projected_labels_for_visible_ray_set,
    folded_optics_marker_plan,
    folded_path_plane_at_distance,
    folded_fallback_source_start_specs,
    folded_scan_incoming_states,
    folded_scan_overlay_plan,
    leg_geometry_point_at_fraction,
    leg_label_text,
    max_surface_radius,
    physical_leg_label_plan,
    plot_status_label,
    project_scene_bundle,
    projected_ray_events_for_segment,
    projected_ray_event_label_items,
    projected_ray_terminal_surface_ids,
    projected_scene_for_layout_render,
    projected_pick_state,
    preview_trace_signature_matches,
    ray_event_display_label,
    representative_projected_rays_by_branch,
    scene_bundle_launch_sampling_mode,
    sequential_focus_diagnostic,
    thin_lens_glyph_polyline,
    trace_mode_summary_from_bundle,
    trace_preview_summary,
)
from KrakenOS.UI.layout_library import (
    EXAMPLE_CATEGORY_ORDER,
    LAYOUT_CATEGORY_ORDER,
    discover_examples as _discover_examples,
    discover_layouts as _discover_layouts,
    discover_zemax_prescriptions,
    example_file_has_import_side_effects,
    example_file_is_menu_loadable,
    example_menu_category,
    layout_menu_category,
    load_python_data as _load_python_data,
    load_python_title as _load_python_title,
    python_code_defines_layout_data,
)
from KrakenOS.UI.nonseq_output_ports import (
    apply_optical_solid_output_port_system_overrides,
    build_optical_solid_output_port_pose_overrides,
    optical_solid_output_port_pose_overrides,
    optical_solid_output_port_runtime_transform_override,
    select_optical_solid_output_face,
)
from KrakenOS.UI import optical_solid_metadata
from KrakenOS.UI.scene_builder import (
    FOLDED_TERMINAL_POLICY_DISPLAY_COMPATIBILITY,
    FOLDED_TERMINAL_POLICY_TRACE_EVENTS,
    RAY_ANALYSIS_CONTRACT_COLUMNS,
    RAY_EVENT_RECORD_COLUMNS,
    build_scene_boundary_faces,
    build_scene_bundle,
    build_scene_optical_volumes,
    build_scene_placements,
    build_scene_targets,
    scene_bundle_ray_analysis_records,
    scene_bundle_ray_event_records,
    scene_placement_to_runtime_record,
    scene_target_to_runtime_record,
)
from KrakenOS.UI.scene_geometry import (
    BoundsRect,
    PlaneMarker,
    ProjectedRay2D,
    ProjectedScene2D,
    RayBranch3D,
    RayEvent3D,
    SceneBundle,
    ScenePlacement3D,
    SceneSource3D,
    SceneTarget3D,
    SurfaceMesh3D,
    projected_ray_hits_detector,
    projected_ray_terminal_status,
    ray_path_reaches_image_from_events,
    ray_path_terminal_diagnostic_text,
    ray_path_terminal_event,
    ray_path_terminal_metadata,
    ray_path_terminal_status_from_events,
    scene_target_active_footprint_polylines,
    scene_target_detector_miss_crosshair_polylines,
)
from KrakenOS.UI.scene_projector import (
    auxiliary_projection_planes,
    bounded_ray_points_for_scene_display,
    normalize_projection_plane,
    projection_axis_labels,
    scene_display_center_radius,
)
from KrakenOS.UI.scene_renderer_2d import render_optics_markers, render_scene_2d, set_plot_limits
from KrakenOS.UI.panels.main_advanced_surface_dialog import MainAdvancedSurfaceDialog
from KrakenOS.UI.panels.main_analysis_controls import MainAnalysisToolbarPanel, MainInformationPanel
from KrakenOS.UI.panels.main_branch_gaussian_q_dialog import MainBranchGaussianQDialog
from KrakenOS.UI.panels.main_branch_throughput_report_dialog import MainBranchThroughputReportDialog
from KrakenOS.UI.panels.main_atmosphere_panel import MainAtmospherePanel
from KrakenOS.UI.panels.main_beam_splitter_dialog import MainBeamSplitterDialog
from KrakenOS.UI.panels.main_coating_material_dialog import MainCoatingMaterialDialog
from KrakenOS.UI.panels.main_context_menu import MainContextMenu
from KrakenOS.UI.panels.main_detector_aperture_report_dialog import MainDetectorApertureReportDialog
from KrakenOS.UI.panels.main_diffuse_scatter_dialog import MainDiffuseScatterDialog
from KrakenOS.UI.panels.main_error_map_dialog import MainErrorMapDialog
from KrakenOS.UI.panels.main_field_controls import MainFieldControlsPanel
from KrakenOS.UI.panels.main_glass_catalog_browser_dialog import MainGlassCatalogBrowserDialog
from KrakenOS.UI.panels.main_lens_drawing_dialogs import MainLensDrawingDialogs
from KrakenOS.UI.panels.main_nonseq_scene_graph_dialog import MainNonSequentialSceneGraphDialog
from KrakenOS.UI.panels.main_optimization_panel import MainOptimizationPanel
from KrakenOS.UI.panels.main_window import MainWindowBuilder
from KrakenOS.UI.panels.main_optical_solid_face_roles_dialog import MainOpticalSolidFaceRolesDialog
from KrakenOS.UI.panels.main_optical_solid_dialogs import MainOpticalSolidDialogs
from KrakenOS.UI.panels.main_path_component_placement_dialog import MainPathComponentPlacementDialog
from KrakenOS.UI.panels.main_path_detector_analysis import MainPathDetectorAnalysis
from KrakenOS.UI.panels.main_ray_trace_inspectors import MainRayTraceInspectorDialogs
from KrakenOS.UI.panels.main_paraxial_analysis_dialogs import MainParaxialAnalysisDialogs
from KrakenOS.UI.panels.main_scene_element_dialogs import MainSceneElementDialogs
from KrakenOS.UI.panels.main_scene_source_manager_dialog import MainSceneSourceManagerDialog
from KrakenOS.UI.panels.main_stock_lens_importer_dialog import MainStockLensImporterDialog
from KrakenOS.UI.panels.main_source_controls import MainSourceControlsPanel
from KrakenOS.UI.panels.main_source_illumination_report_dialog import MainSourceIlluminationReportDialog
from KrakenOS.UI.panels.main_surface_settings_dialogs import MainSurfaceSettingsDialogs
from KrakenOS.UI.panels.main_surface_shape_builder_dialog import MainSurfaceShapeBuilderDialog
from KrakenOS.UI.panels.main_tolerance_report_dialogs import MainToleranceReportDialogs
from KrakenOS.UI.panels.main_trace_display_controls import MainTraceDisplayControlsPanel
from KrakenOS.UI.panels.open3d_live_controls import Open3DLiveControlsPanel
from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel
from KrakenOS.UI.panels.open3d_top_controls import Open3DTopControlsPanel
from KrakenOS.UI.panels.optical_stl_placement_dialog import OpticalStlPlacementDialog
from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.services.analysis_plot import AnalysisPlotService
from KrakenOS.UI.services.analysis_reports import AnalysisReportsMixin
from KrakenOS.UI.services.editable_table_rows import EditableTableRowService
from KrakenOS.UI.services.formula_help import FormulaHelpService
from KrakenOS.UI.services.geometric_analysis import GeometricAnalysisMixin
from KrakenOS.UI.services.legacy_3d_scene import Legacy3DSceneService
from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin
from KrakenOS.UI.services.layout_file_writer import LayoutFileWriterService
from KrakenOS.UI.services.layout_settings import LayoutSettingsService
from KrakenOS.UI.services.nonseq_scene_graph_records import NonSequentialSceneGraphRecordService
from KrakenOS.UI.services.paraxial_tools import ParaxialToolsMixin
from KrakenOS.UI.services.open3d_carry_grip import Open3DCarryGripService
from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService
from KrakenOS.UI.services.open3d_face_pick import FaceRayPick, pick_face_from_ray
from KrakenOS.UI.services.open3d_interaction import Open3DInteractionService
from KrakenOS.UI.services.open3d_live_refresh import Open3DLiveRefreshService
from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService
from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService
from KrakenOS.UI.services.open3d_step_state import Open3DStepStateService, StepFeatureSelection
from KrakenOS.UI.services.open3d_step_rotation_handles import Open3DStepRotationHandleService
from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService
from KrakenOS.UI.services.open3d_trace_refresh import Open3DTraceRefreshService
from KrakenOS.UI.services.plot_refresh import PlotRefreshService
from KrakenOS.UI.services.ray_inspector_records import RayInspectorRecordService
from KrakenOS.UI.services.results_display import ResultsDisplayService
from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin
from KrakenOS.UI.services.source_modeling import SourceModelingMixin
from KrakenOS.UI.services.step_face_direction import StepFaceDirectionService
from KrakenOS.UI.services.step_overlay_import import StepOverlayImportService
from KrakenOS.UI.services.step_overlay_promotion import StepOverlayPromotionService
from KrakenOS.UI.services.tolerance_analysis import ToleranceAnalysisService
from KrakenOS.UI.services.tolerance_modeling import ToleranceModelingMixin
from KrakenOS.UI.services.tolerance_stackup import ToleranceStackupService
from KrakenOS.UI.services.trace_preview import TracePreviewService
from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin
from KrakenOS.UI.widgets.tooltips import WidgetTooltip
from KrakenOS.UI.scene_row_mapping import (
    SCENE_ROW_SOURCE,
    SCENE_ROW_SURFACE,
    SOURCE_ROW_ORDER_AFTER_OBJECT,
    SOURCE_ROW_ORDER_BEFORE_OBJECT,
    SOURCE_ROW_ORDER_DEFAULT,
    build_scene_row_mapping,
    normalize_source_row_order,
)
from KrakenOS.UI.scene_placement import (
    SCENE_PLACEMENT_ADVANCED_ATTR,
    normalize_scene_placement_settings,
    scene_placement_settings_is_default,
)
from KrakenOS.UI.scene_source_analysis import (
    dedupe_scene_source_ids,
    normalize_scene_source_specs,
    scene_source_detail_text,
    scene_source_feature_text,
    scene_source_from_spec,
    scene_source_setting_value,
    scene_sources_summary_text,
    source_panel_summary_text,
    source_spec_bool,
    source_spec_float,
    source_spec_vector,
)
from KrakenOS.UI.trace_intent import resolve_trace_intent
from KrakenOS.UI.tolerance_constants import (
    TOLERANCE_COMPARE_VIEW_DEFAULT,
    TOLERANCE_COMPARE_VIEW_VALUES,
    TOLERANCE_COMPENSATORS_ADVANCED_ATTR,
    TOLERANCE_COUPLING_ADVANCED_ATTR,
    TOLERANCE_MANUFACTURING_ADVANCED_ATTR,
    TOLERANCE_MANUFACTURING_TEMPLATES_SETTINGS,
    TOLERANCE_SOLVE_PRESET_DEFAULTS,
)
from KrakenOS.UI.source_trace_helpers import (
    ATMOS_PLOT_MODE_DEFAULT,
    ATMOS_PLOT_MODE_VALUES,
    GAUSSIAN_INPUT_MODE_DEFAULT,
    GAUSSIAN_INPUT_MODE_VALUES,
    GAUSSIAN_WAIST_SIDE_DEFAULT,
    GAUSSIAN_WAIST_SIDE_VALUES,
    PUPIL_PATTERN_DEFAULT,
    PUPIL_PATTERN_TO_KRAKEN,
    PUPIL_PATTERN_VALUES,
    SOURCE_ANGULAR_WEIGHT_DEFAULT,
    SOURCE_ANGULAR_WEIGHT_VALUES,
    SOURCE_DIRECTION_PRESETS,
    SOURCE_DIRECTION_PRESET_CUSTOM,
    SOURCE_DIRECTION_PRESET_VALUES,
    SOURCE_MERIDIONAL_PREVIEW_MAX_RADIUS_FRACTION,
    SOURCE_MODEL_DEFAULT,
    SOURCE_MODEL_VALUES,
    SOURCE_MODEL_ZEMAX_RAYFILE,
)
from KrakenOS.UI.source_illumination_analysis import (
    SOURCE_ILLUMINATION_TABLE_COLUMNS,
    SOURCE_ILLUMINATION_TABLE_HEADINGS,
    SOURCE_ILLUMINATION_TABLE_WIDTHS,
    collect_source_illumination_records,
    empty_source_illumination_samples,
    source_illumination_hit_samples_from_records,
    source_illumination_record_detail_text,
    source_illumination_report_text,
    source_illumination_summary_text,
    source_illumination_table_values,
    source_illumination_map_data_from_samples,
    source_illumination_map_extent,
    write_source_illumination_csv,
)
from KrakenOS.UI.surface_table_model import (
    SURFACE_ROW_CLIPBOARD_FORMAT,
    SurfaceRow,
    append_layout_rows as _surface_table_append_layout_rows,
    component_rows_from_layout,
    duplicate_rows_for_indices,
    inserted_layout_row_indices,
    insert_surface_rows as _surface_table_insert_surface_rows,
    normalized_rows_copy as _surface_table_normalized_rows_copy,
    pasteable_component_rows,
    surface_rows_from_clipboard_text,
    surface_rows_from_records,
    surface_rows_to_clipboard_text,
    surface_rows_to_records,
    surface_rows_to_specs,
)
from KrakenOS.scatter_backend import (
    format_pyscatmech_parameters,
    normalize_pyscatmech_parameters,
    pyscatmech_status,
)
from KrakenOS.UI.zemax_wavefront import (
    ZemaxWavefrontMap,
    load_zemax_wavefront_map,
    normalized_pupil_coordinates,
    sample_wavefront_grid,
)
from KrakenOS.UI.zemax_rayfile import (
    find_zemax_nsc_source_files,
    sample_zemax_rayfile,
    summarize_zemax_rayfile,
)

pv = None
vtkTkRenderWindowInteractor = None
vtkTubeFilter = None
vtkOrientationMarkerWidget = None
vtkAxesActor = None
vtkActor = None
vtkCellPicker = None
vtkDataSetMapper = None
vtkRenderer = None
vtkTextActor = None
vtkBillboardTextActor3D = None
_3D_BACKENDS_ATTEMPTED = False
_VTK_TK_UNAVAILABLE_REASON = ""
_x_error_handler_ref = None
_DISPLAY_EDGE_3D = None
_DISPLAY_FILTER_FACE_2DPLOT = None
_DISPLAY_WAVELENGTH_TO_RGB = None
_DISPLAY_HELPERS_ATTEMPTED = False


LAYOUTS_DIR = Path(__file__).resolve().parent.parent / "common_optical_layouts"
EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "Examples"
METAL_CATALOG_DIR = Path(__file__).resolve().parent.parent / "Cat"
LENSCAT_DIR = Path(__file__).resolve().parent.parent / "LensCat"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ATTACHMENT_DIR = PROJECT_ROOT / "attachment"
LEGACY_TESTING_DIR = PROJECT_ROOT / "testing"
DOCS_HTML_DIR = PROJECT_ROOT / "docs" / "build" / "html"
DOCS_SOURCE_DIR = PROJECT_ROOT / "docs" / "source"


def _preferred_existing_path(*candidates: Path | str) -> Path:
    paths = [Path(candidate).expanduser() for candidate in candidates]
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def _preferred_existing_dir(*candidates: Path | str) -> Path:
    paths = [Path(candidate).expanduser() for candidate in candidates]
    for path in paths:
        if path.is_dir():
            return path
    return paths[0]


def normalize_projection_display_mode(value: object) -> str:
    text = str(value or "").strip()
    key = text.lower().replace("-", " ").replace("_", " ")
    if key in {"full", "full 3d", "full 3 d", "full projection", "full 3d projection", "all fields"}:
        return PROJECTION_MODE_FULL_3D
    if key in {"axis", "axis field", "axis fields", "section", "plane", "field plane"}:
        return PROJECTION_MODE_AXIS_FIELD
    if text in PROJECTION_MODE_VALUES:
        return text
    return PROJECTION_MODE_AXIS_FIELD


# Backward-compatible symbol names: the user-facing project scratch/import
# directory was renamed from testing/ to attachment/.
TESTING_DIR = ATTACHMENT_DIR
ZEMAX_ATTACHMENT_DIR = ATTACHMENT_DIR / "zemax"
ZEMAX_TESTING_DIR = ZEMAX_ATTACHMENT_DIR
OPTICAL_SOLID_CAD_SUFFIXES = {".step", ".stp", ".iges", ".igs"}
OPTICAL_SOLID_STL_SUFFIXES = {".stl"}
OPTICAL_SOLID_FILETYPES = [
    ("Optical solid CAD/STL", "*.stl *.STL *.step *.STEP *.stp *.STP *.iges *.IGES *.igs *.IGS"),
    ("STL mesh", "*.stl *.STL"),
    ("STEP CAD", "*.step *.STEP *.stp *.STP"),
    ("IGES CAD", "*.iges *.IGES *.igs *.IGS"),
    ("All files", "*"),
]
from KrakenOS.UI.services.catalog_metadata import (
    DEFAULT_METAL_CATALOG_NAME,
    DEFAULT_METAL_CATALOG_PATH,
    STOCK_LENS_CATALOG_SPECS,
    _metal_catalog_type_for_path,
    _normalize_metal_catalog_specs,
    _metal_catalog_entries,
    _metal_catalog_signature,
    _metal_catalogs_from_row_specs,
    _load_metal_catalogs_into_setup,
    _available_stock_lens_catalogs,
    _load_stock_lens_catalog,
    _catalog_surface_keys,
    _stock_lens_summary,
)
# Project-side scratch directory for ad-hoc screenshots and exports. Not used by
# auto-save (which stays in ~/.cache); only as the *initial* directory for
# user-triggered Save dialogs.
SCREENSHOT_DIR = ATTACHMENT_DIR
DEFAULT_LAYOUT_TITLE = "Doublet Lens"
FOLDED_STARTER_LAYOUT_TITLE = "Double Mirror Fold"
DETECTOR_BINS_DEFAULT = "Auto"
BRANCH_FIELD_PROPAGATION_MM_DEFAULT = "0.0"
DETECTOR_ADVANCED_ATTR = "Detector"
SCENE_TARGET_ADVANCED_ATTR = "SceneTarget"
DRAWING_PROPERTIES_ADVANCED_ATTR = DRAWING_PROPERTIES_ATTR
from KrakenOS.UI.services.element_scene_metadata import (
    DETECTOR_DEFAULT_SETTINGS,
    SCENE_TARGET_DEFAULT_SETTINGS,
    SCENE_TARGET_ROLE_VALUES,
    SCENE_TARGET_EDITOR_KIND_LABELS,
    SCENE_TARGET_EDITOR_KIND_CHOICES,
    SCENE_NORMAL_TARGET_LABELS,
    SCENE_NORMAL_TARGET_CHOICES,
    ELEMENT_ARM_ROLE_DEFAULT,
    ELEMENT_ARM_ROLE_VALUES,
    ELEMENT_BRANCH_SELECTOR_VALUES,
    ELEMENT_METADATA_NUMERIC_FIELDS,
    _normalize_element_metadata,
    _element_metadata_is_default,
    _normalize_detector_settings,
    _normalize_scene_target_role,
    _normalize_scene_target_settings,
    _scene_target_settings_is_default,
    _normalize_scene_target_editor_kind,
    _scene_target_role_for_editor_kind,
    _normalize_scene_normal_target_kind,
    _detector_settings_is_default,
)
STEP_CARRY_GRID_FREE = "Free"
STEP_CARRY_GRID_CHOICES = (
    STEP_CARRY_GRID_FREE,
)
STEP_OVERLAY_LABELS = ("lens", "optical", "led", "camera")
STEP_OVERLAY_LABEL_SET = set(STEP_OVERLAY_LABELS)
PROJECTION_MODE_AXIS_FIELD = "Axis field"
PROJECTION_MODE_FULL_3D = "Full 3D"
PROJECTION_MODE_VALUES = (PROJECTION_MODE_AXIS_FIELD, PROJECTION_MODE_FULL_3D)
INSERTABLE_COMMON_LAYOUT_TITLES = {
    "Single Lens",
    "Doublet Lens",
    "Ideal 2F Lens",
    "Flat Mirror 45 Deg",
}
CAD_CACHE_DIR = Path.home() / ".cache" / "krakenos" / "cad"
VIEWER_EXPORT_DIR = Path.home() / ".cache" / "krakenos" / "viewer"
AUTO_PLOT_PATH = TESTING_DIR / "2D.png"
DEBUG_LOG_PATH = Path.home() / ".cache" / "krakenos" / "logs" / "kraken_debug_latest.log"
ATTACHMENT_CAMERA_DIR = _preferred_existing_dir(
    ATTACHMENT_DIR / "camera",
    ATTACHMENT_DIR / "Camera",
    ATTACHMENT_DIR / "Cameras",
)
ATTACHMENT_LENS_DIR = _preferred_existing_dir(
    ATTACHMENT_DIR / "Lens",
    ATTACHMENT_DIR / "lens",
)
ATTACHMENT_LED_DIR = _preferred_existing_dir(ATTACHMENT_DIR / "LED", ATTACHMENT_DIR / "led")
DEFAULT_CAMERA_STEP_PATH = _preferred_existing_path(
    ATTACHMENT_CAMERA_DIR / "3D_CAD_HR25xCXP.STEP",
    ATTACHMENT_CAMERA_DIR / "3D_CAD_shr661MCX.STEP",
    Path.home() / "cameras" / "3D_CAD_HR25xCXP.STEP",
)
DEFAULT_LENS_STEP_PATH = _preferred_existing_path(
    ATTACHMENT_LENS_DIR / "15056" / "15056.STEP",
    ATTACHMENT_LENS_DIR / "15056.STEP",
    Path.home() / "15056" / "15056.STEP",
)
DEFAULT_LED_STEP_PATH = _preferred_existing_path(
    ATTACHMENT_LED_DIR / "OPT-CO90-X-V1.6.2-H.STEP",
    ATTACHMENT_LED_DIR,
)
GALVO_SCAN_OVERLAY_KEY = "tilt_x_overlay_deg"
POSE_TOLERANCE_OVERLAY_KEY = "pose_tolerance_overlay"
POSE_TOLERANCE_FIELDS = ("tilt_x", "tilt_y", "tilt_z", "desp_x", "desp_y", "desp_z")
POSE_TOLERANCE_MAX_VARIANTS = 25
ZEMAX_PRESCRIPTION_SUFFIXES = {".zmx"}
EXTERNAL_CAMERA_MODELS = {
    "None": None,
    "SHR461xCX": {
        "label": "SHR461xCX",
        "path": Path.home() / "Pictures" / "3D_CAD_shr461xCX.STEP",
        "kind": "step",
        "outer_solids": (0, 1, 2),
        "align_axis": "z",
        "front_face": "min",
        "rotate_xyz_deg": (0.0, 180.0, 0.0),
        "color": (0.62, 0.66, 0.72),
        "opacity_3d": 0.94,
        "line_color_2d": "#6b7280",
    },
}
FIELDS = (
    "label",
    "surface",
    "name",
    "glass",
    "rc",
    "thickness",
    "diameter",
    "in_diameter",
    "tilt_x",
    "tilt_y",
    "tilt_z",
    "desp_x",
    "desp_y",
    "desp_z",
    "axis_move",
)
GRATING_SETTING_FIELDS = ("diff_ord", "grating_d", "grating_angle")
DISABLED_TABLE_CELL_TEXT = "NA"
OPTIMIZATION_CELL_MARKER_TEXT = "V"
OPTIMIZATION_CELL_MARKER_BG = "#fff0a6"
OPTIMIZATION_CELL_MARKER_FG = "#6b4a00"
COLUMN_LABELS = {
    "label": "#",
    "surface": "Surface",
    "name": "Name",
    "glass": "Material",
    "rc": "Rc [mm]",
    "k": "k",
    "axicon": "Axicon [deg]",
    "diff_ord": "Order",
    "grating_d": "Pitch [um]",
    "grating_angle": "Lines [deg]",
    "thickness": "Thickness [mm]",
    "diameter": "Diameter [mm]",
    "in_diameter": "InDia [mm]",
    "tilt_x": "TiltX [deg]",
    "tilt_y": "TiltY [deg]",
    "tilt_z": "TiltZ [deg]",
    "desp_x": "DespX [mm]",
    "desp_y": "DespY [mm]",
    "desp_z": "DespZ [mm]",
    "axis_move": "AxisMove",
}
PATH_LOCAL_TABLE_FIELD_MAP = {
    "tilt_x": "local_tilt_x",
    "tilt_y": "local_tilt_y",
    "tilt_z": "local_tilt_z",
    "desp_x": "local_decenter_x",
    "desp_y": "local_decenter_y",
    "desp_z": "arm_distance",
}
PATH_LOCAL_COLUMN_LABELS = {
    "tilt_x": "Local TiltX [deg]",
    "tilt_y": "Local TiltY [deg]",
    "tilt_z": "Local TiltZ [deg]",
    "desp_x": "Local X [mm]",
    "desp_y": "Local Y [mm]",
    "desp_z": "Path Dist [mm]",
}
FIELD_TYPE_CANONICAL_VALUES = (
    "Angle",
    "Object Height",
    "Paraxial Image Height",
    "Real Image Height",
)
FIELD_TYPE_DISPLAY_LABELS = {
    "Angle": "Field Half-Angle",
    "Object Height": "Object Semi-Height",
    "Paraxial Image Height": "Paraxial Image Semi-Height",
    "Real Image Height": "Real Image Semi-Height",
}
FIELD_TYPE_ALIASES = {
    "Angle": "Angle",
    "Field Angle": "Angle",
    "Field Half-Angle": "Angle",
    "Object Height": "Object Height",
    "Object Semi-Height": "Object Height",
    "Paraxial Image Height": "Paraxial Image Height",
    "Paraxial Image Semi-Height": "Paraxial Image Height",
    "Real Image Height": "Real Image Height",
    "Real Image Semi-Height": "Real Image Height",
}
ADVANCED_SURFACE_FIELD_GROUPS = (
    (
        "Shape",
        (
            ("AspherData", "Asphere coefficients"),
            ("ZNK", "Zernike coefficients"),
            ("Cylinder_Rxy_Ratio", "Cylinder Rxy ratio"),
            ("ShiftX", "Shape shift X"),
            ("ShiftY", "Shape shift Y"),
            ("Surface_type", "Surface type"),
            ("Res", "Resolution"),
        ),
    ),
    (
        "Aperture/Mask",
        (
            ("SubAperture", "Sub-aperture [scale, y, x]"),
            ("Mask_Type", "Mask type"),
            ("Mask_Shape", "Mask shape"),
            ("Solid_3d_stl", "STL solid path/data"),
        ),
    ),
    (
        "Coating/Material",
        (
            ("Coating", "Coating table"),
            ("CoatingMet", "Metal coating mode"),
            ("BeamSplitter", "Beam splitter settings"),
            ("DiffuseScatter", "Diffuse/BRDF scatter settings"),
            ("Color", "Display color"),
            ("Nm_Pos", "Name position"),
        ),
    ),
    (
        "Diagnostics/Native",
        (
            ("Element", "Element/path metadata"),
            (DETECTOR_ADVANCED_ATTR, "Detector model settings"),
            (SCENE_TARGET_ADVANCED_ATTR, "Scene target metadata"),
            (SCENE_PLACEMENT_ADVANCED_ATTR, "3-D placement metadata"),
            (DRAWING_PROPERTIES_ADVANCED_ATTR, "2-D drawing surface properties"),
            ("Display2D", "2-D display settings"),
            ("Interferogram", "Interferogram detector settings"),
            ("OpticalSolidFaces", "CAD/STL optical face roles"),
            ("OpticalSolidSourcePath", "Original CAD/STL source path"),
            ("OpticalSolidSourceFormat", "Original CAD/STL source format"),
            ("StepOverlayPromotion", "Open 3D STEP promotion metadata"),
            ("LiveStepOverlayTrace", "Open 3D live STEP trace metadata"),
            ("Note", "Note"),
            ("Order", "Native order"),
            ("Var", "Native optimization vars"),
            ("VarBounds", "Native variable bounds"),
            (TOLERANCE_COMPENSATORS_ADVANCED_ATTR, "Tolerance compensator variable names"),
            (TOLERANCE_COUPLING_ADVANCED_ATTR, "Tolerance coupling groups"),
            (TOLERANCE_MANUFACTURING_ADVANCED_ATTR, "Tolerance manufacturing metadata"),
            ("Error_map", "Measured error map"),
            ("DerPres", "Derivative precision"),
            ("NumLabel", "Draw numeric label"),
            ("SPECIAL_SURF_FUNC", "Special surface function"),
            ("Const", "Native constants"),
        ),
    ),
)
ADVANCED_SURFACE_ATTR_NAMES = tuple(
    attr for _group, fields in ADVANCED_SURFACE_FIELD_GROUPS for attr, _label in fields
)
ADVANCED_ROW_SHAPE_FIELDS = (
    (
        "k",
        "Conic constant k",
        "0=sphere, -1=parabola; used for conic/aspheric base surfaces.",
    ),
    (
        "axicon",
        "Axicon angle [deg]",
        "Adds conical sag for axicon/Bessel-beam style surfaces; uncommon for ordinary lenses.",
    ),
)
COATING_PRESETS = {
    "Clear / no coating": [[], [], [], []],
    "Broadband AR 1%": [
        [[0.012, 0.008, 0.011], [0.018, 0.014, 0.020], [0.028, 0.022, 0.030]],
        [[0.000, 0.000, 0.000], [0.000, 0.000, 0.000], [0.000, 0.000, 0.000]],
        [0.45, 0.55, 0.65],
        [0.0, 45.0, 70.0],
    ],
    "Protected mirror 94%": [
        [[0.940, 0.960, 0.950], [0.920, 0.940, 0.930], [0.860, 0.900, 0.880]],
        [[0.010, 0.010, 0.010], [0.015, 0.015, 0.015], [0.025, 0.025, 0.025]],
        [0.45, 0.55, 0.65],
        [0.0, 45.0, 70.0],
    ],
}
COATING_PRESET_NAMES = tuple(COATING_PRESETS.keys())
BEAM_SPLITTER_SURFACE = "Beam Splitter"
OBJECT_TARGET_SURFACE = "Object Target"
DIFFUSE_OBJECT_SURFACE = "Diffuse Object"
REFLECTIVE_PROXY_SURFACES = {"Mirror", OBJECT_TARGET_SURFACE, DIFFUSE_OBJECT_SURFACE}

from KrakenOS.UI.services.beam_scatter_metadata import (
    BEAM_SPLITTER_ADVANCED_ATTR,
    DIFFUSE_SCATTER_ADVANCED_ATTR,
    BEAM_SPLITTER_SPLIT_MODES,
    BEAM_SPLITTER_DEFAULT_SETTINGS,
    DIFFUSE_SCATTER_DEFAULT_SETTINGS,
    _normalize_diffuse_scatter_settings,
    _validate_diffuse_scatter_settings,
    _diffuse_scatter_summary,
    _normalize_beam_splitter_settings,
    _beam_splitter_uses_coating_table,
    _beam_splitter_uses_fresnel_polarization,
    _coating_table_has_data,
    _beam_splitter_coating_for_settings,
    _validate_beam_splitter_settings,
    _beam_splitter_coating_from_settings,
    _beam_splitter_summary,
)

ELEMENT_ADVANCED_ATTR = "Element"
ANALYSIS_PATH_FILTER_DEFAULT = "All paths"
ANALYSIS_PATH_FILTER_LEGACY_DEFAULTS = {"All branches", "All arms", "Common"}
RAY_DISPLAY_ALL = "All rays"
RAY_DISPLAY_DETECTOR = "Detector hits"
RAY_DISPLAY_MISSED_DETECTOR = "Missed detector"
RAY_DISPLAY_ABSORBED = "Absorbed"
RAY_DISPLAY_ESCAPED = "Escaped"
RAY_DISPLAY_STOPPED = "Stopped / diagnostic"
RAY_DISPLAY_SPLITTER = "Beam-splitter paths"
RAY_DISPLAY_VALUES = (
    RAY_DISPLAY_ALL,
    RAY_DISPLAY_DETECTOR,
    RAY_DISPLAY_MISSED_DETECTOR,
    RAY_DISPLAY_ABSORBED,
    RAY_DISPLAY_ESCAPED,
    RAY_DISPLAY_STOPPED,
    RAY_DISPLAY_SPLITTER,
)
RAY_DISPLAY_DEFAULT = RAY_DISPLAY_ALL
FOLDED_DETECTOR_POLICY_TRACE = "Trace events"
FOLDED_DETECTOR_POLICY_DISPLAY = "Display compatibility"
FOLDED_DETECTOR_POLICY_VALUES = (
    FOLDED_DETECTOR_POLICY_TRACE,
    FOLDED_DETECTOR_POLICY_DISPLAY,
)
FOLDED_DETECTOR_POLICY_DEFAULT = FOLDED_DETECTOR_POLICY_TRACE
ARM_VIEW_DEFAULT = ANALYSIS_PATH_FILTER_DEFAULT
MICHELSON_LEG_DEFINITIONS = (
    ("input", "Path 1", "Input / source return"),
    ("transmit", "Path 2", "Transmit mirror path"),
    ("reflect", "Path 3", "Reflect mirror path"),
    ("detector", "Path 4", "Detector output path"),
)
MACH_ZEHNDER_LEG_DEFINITIONS = (
    ("input", "Path 1", "Input to BS1"),
    ("transmit", "Path 2", "BS1 to BS2 transmit path"),
    ("reflect", "Path 3", "BS1 to BS2 reflect path"),
    ("cross", "Path 4", "BS2 to cross output detector"),
    ("return", "Path 5", "BS2 to return output detector"),
)
ELEMENT_ARM_BADGES = {
    "Common": "C",
    "Transmit": "T",
    "Reflect": "R",
    "Return": "RET",
    "Detector": "D",
}
PATH_COMPONENT_DETECTOR = "Detector plane"
PATH_COMPONENT_APERTURE = "Aperture stop"
PATH_COMPONENT_THIN_LENS = "Thin lens"
PATH_COMPONENT_REFRACTIVE_SURFACE = "Refractive surface"
PATH_COMPONENT_MIRROR = "Mirror"
PATH_COMPONENT_OBJECT_TARGET = "Object Target"
PATH_COMPONENT_STOCK_LENS = "Stock lens block"
PATH_COMPONENT_TYPES = (
    PATH_COMPONENT_DETECTOR,
    PATH_COMPONENT_APERTURE,
    PATH_COMPONENT_THIN_LENS,
    PATH_COMPONENT_REFRACTIVE_SURFACE,
    PATH_COMPONENT_MIRROR,
    PATH_COMPONENT_OBJECT_TARGET,
)
PATH_COMPONENT_LABEL_SUFFIXES = {
    PATH_COMPONENT_DETECTOR: "detector",
    PATH_COMPONENT_APERTURE: "aperture",
    PATH_COMPONENT_THIN_LENS: "thin lens",
    PATH_COMPONENT_REFRACTIVE_SURFACE: "surface",
    PATH_COMPONENT_MIRROR: "mirror",
    PATH_COMPONENT_OBJECT_TARGET: "object target",
    PATH_COMPONENT_STOCK_LENS: "stock lens",
}
ADVANCED_SURFACE_ATTR_ALIASES = {
    re.sub(r"[^a-z0-9]", "", attr.lower()): attr for attr in ADVANCED_SURFACE_ATTR_NAMES
}
ADVANCED_SURFACE_ATTR_ALIASES.update(
    {
        "aspherdata": "AspherData",
        "aspherics": "AspherData",
        "aspher": "AspherData",
        "zernike": "ZNK",
        "znk": "ZNK",
        "subaperture": "SubAperture",
        "masktype": "Mask_Type",
        "maskshape": "Mask_Shape",
        "coatingmet": "CoatingMet",
        "beamsplitter": "BeamSplitter",
        "beam splitter": "BeamSplitter",
        "diffusescatter": "DiffuseScatter",
        "diffuse scatter": "DiffuseScatter",
        "brdf": "DiffuseScatter",
        "bsdf": "DiffuseScatter",
        "elementmetadata": "Element",
        "element metadata": "Element",
        "pathmetadata": "Element",
        "path metadata": "Element",
        "armmetadata": "Element",
        "arm metadata": "Element",
        "error map": "Error_map",
        "errormap": "Error_map",
        "solid3dstl": "Solid_3d_stl",
        "cylinderrxyratio": "Cylinder_Rxy_Ratio",
        "surfacetype": "Surface_type",
        "specialsurffunc": "SPECIAL_SURF_FUNC",
    }
)
EXAMPLE_SUPPORTED_SURFACE_ATTRS = {
    "Name",
    "Rc",
    "InDiameter",
    "k",
    "Axicon",
    "ExtraData",
    "Diff_Ord",
    "Grating_D",
    "Grating_Angle",
    "Thickness",
    "Diameter",
    "TiltX",
    "TiltY",
    "TiltZ",
    "DespX",
    "DespY",
    "DespZ",
    "AxisMove",
    "Drawing",
    "Glass",
    "Thin_Lens",
    "UDA",
    *ADVANCED_SURFACE_ATTR_NAMES,
}
NUMERIC_FIELDS = {
    "rc",
    "k",
    "axicon",
    "diff_ord",
    "grating_d",
    "grating_angle",
    "thickness",
    "diameter",
    "in_diameter",
    "tilt_x",
    "tilt_y",
    "tilt_z",
    "desp_x",
    "desp_y",
    "desp_z",
    "axis_move",
}
SURFACE_TYPES = (
    "Object",
    "Standard",
    "Aperture",
    "Mirror",
    OBJECT_TARGET_SURFACE,
    DIFFUSE_OBJECT_SURFACE,
    BEAM_SPLITTER_SURFACE,
    "Thin Lens",
    "Grating",
    "Image",
)
SURFACE_TYPE_ENABLED_FIELDS = {
    "Object": {"label", "surface", "name", "thickness", "diameter"},
    "Standard": {
        "label",
        "surface",
        "name",
        "glass",
        "rc",
        "k",
        "axicon",
        "thickness",
        "diameter",
        "in_diameter",
        "tilt_x",
        "tilt_y",
        "tilt_z",
        "desp_x",
        "desp_y",
        "desp_z",
        "axis_move",
    },
    "Aperture": {
        "label",
        "surface",
        "name",
        "thickness",
        "diameter",
        "in_diameter",
        "tilt_x",
        "desp_x",
        "desp_y",
        "desp_z",
        "axis_move",
    },
    "Mirror": {
        "label",
        "surface",
        "name",
        "rc",
        "k",
        "thickness",
        "diameter",
        "in_diameter",
        "tilt_x",
        "tilt_y",
        "tilt_z",
        "desp_x",
        "desp_y",
        "desp_z",
        "axis_move",
    },
    OBJECT_TARGET_SURFACE: {
        "label",
        "surface",
        "name",
        "rc",
        "k",
        "thickness",
        "diameter",
        "in_diameter",
        "tilt_x",
        "tilt_y",
        "tilt_z",
        "desp_x",
        "desp_y",
        "desp_z",
        "axis_move",
    },
    DIFFUSE_OBJECT_SURFACE: {
        "label",
        "surface",
        "name",
        "rc",
        "k",
        "thickness",
        "diameter",
        "in_diameter",
        "tilt_x",
        "tilt_y",
        "tilt_z",
        "desp_x",
        "desp_y",
        "desp_z",
        "axis_move",
    },
    BEAM_SPLITTER_SURFACE: {
        "label",
        "surface",
        "name",
        "glass",
        "rc",
        "k",
        "thickness",
        "diameter",
        "in_diameter",
        "tilt_x",
        "tilt_y",
        "tilt_z",
        "desp_x",
        "desp_y",
        "desp_z",
        "axis_move",
    },
    "Thin Lens": {
        "label",
        "surface",
        "name",
        "rc",
        "thickness",
        "diameter",
        "tilt_x",
        "tilt_y",
        "tilt_z",
        "desp_x",
        "desp_y",
        "desp_z",
        "axis_move",
    },
    "Grating": {
        "label",
        "surface",
        "name",
        "glass",
        "diff_ord",
        "grating_d",
        "grating_angle",
        "thickness",
        "diameter",
        "in_diameter",
        "tilt_x",
        "tilt_y",
        "tilt_z",
        "desp_x",
        "desp_y",
        "desp_z",
        "axis_move",
    },
    "Image": {
        "label",
        "surface",
        "name",
        "diameter",
        "tilt_x",
        "tilt_y",
        "tilt_z",
        "desp_x",
        "desp_y",
        "desp_z",
        "axis_move",
    },
}
WAVEFRONT_FUNCTION_STYLE = "Wavefront Function"
WAVEFRONT_PHASE_STYLE = "Phase (unwrapped)"
WAVEFRONT_STYLE_DEFAULT = WAVEFRONT_FUNCTION_STYLE
WAVEFRONT_STYLE_VALUES = (
    WAVEFRONT_STYLE_DEFAULT,
    WAVEFRONT_PHASE_STYLE,
    "Wrapped phase",
    "Interferogram",
    "Slope X",
    "Slope Y",
    "Slope magnitude",
)


class _CapturedExample(Exception):
    def __init__(self, surfaces):
        super().__init__("Captured example system")
        self.surfaces = surfaces


class NonSequentialTracePreviewError(RuntimeError):
    def __init__(self, message: str, *, trace_state: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.trace_state = dict(trace_state or {})


from KrakenOS.UI.services.optical_solid_geometry import (
    StlMeshDiagnostics,
    OpticalSolidFaceCandidate,
    OpticalSolidFaceMarker,
    OpticalSolidVirtualPlaneMarker,
    _read_stl_triangle_vertices,
    inspect_stl_mesh,
    format_stl_mesh_diagnostics,
    short_stl_mesh_diagnostics,
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_VIRTUAL_PLANE_KIND_SPLITTER,
    OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y,
    OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_NEG_Y,
    OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_VALUES,
    OPTICAL_SOLID_FACE_ROLE_DEFAULT,
    OPTICAL_SOLID_FACE_ROLE_VALUES,
    OPTICAL_SOLID_FACE_SIDE_DEFAULT,
    OPTICAL_SOLID_FACE_SIDE_VALUES,
    OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    OPTICAL_SOLID_FACE_FUNCTION_VALUES,
    OPTICAL_SOLID_FACE_PORT_DEFAULT,
    OPTICAL_SOLID_FACE_PORT_INPUT,
    OPTICAL_SOLID_FACE_PORT_OUTPUT,
    OPTICAL_SOLID_FACE_PORT_INTERACTION,
    OPTICAL_SOLID_FACE_PORT_VALUES,
    OPTICAL_SOLID_FACE_ASSIGNMENT_DEFAULT_UNCOATED,
    OPTICAL_SOLID_FACE_ASSIGNMENT_MANUAL,
    OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT,
    OPTICAL_SOLID_FACE_FIT_ROLL_NONE,
    OPTICAL_SOLID_FACE_FIT_ROLL_VALUES,
    OPTICAL_SOLID_FACE_FIT_REFERENCE_DEFAULT,
    OPTICAL_SOLID_FACE_FIT_REFERENCE_VALUES,
    OPTICAL_SOLID_FACE_ROLE_COLORS,
    OPTICAL_SOLID_VIRTUAL_PLANE_KIND_VALUES,
    OPTICAL_SOLID_VIRTUAL_PLANE_KIND_COLORS,
    _normalize_optical_solid_face_side,
    _normalize_optical_solid_face_function,
    _optical_solid_face_function_from_ui_value,
    _optical_solid_face_function_display,
    _normalize_optical_solid_face_port_role,
    _normalize_optical_solid_face_fit_reference,
    _optical_solid_face_port_role,
    _optical_solid_face_authored_port_role,
    _legacy_role_from_optical_solid_face_function,
    _normalize_optical_solid_virtual_plane_kind,
    _normalize_optical_solid_virtual_plane_diagonal,
    optical_solid_virtual_plane_color,
    _optical_solid_face_marker_label,
    optical_solid_face_role_color,
    _float_or_default,
    _unit_vector_tuple,
    _point3_tuple,
    _canonical_optical_solid_plane,
    _optical_solid_face_records_share_plane,
    _optical_solid_face_metadata_extent,
    cluster_optical_solid_planar_faces,
    optical_solid_face_candidate_triangles,
    optical_solid_face_record_from_candidate,
    normalize_optical_solid_face_record,
    normalize_optical_solid_virtual_plane_record,
    normalize_optical_solid_face_metadata,
    auto_assign_optical_solid_face_roles,
    suggest_optical_solid_face_roles,
    apply_optical_solid_face_suggestions,
    _optical_solid_face_suggestion_label,
    _optical_solid_face_by_side,
    _optical_solid_virtual_plane_center_from_faces,
    build_optical_solid_cube_splitter_virtual_plane,
    optical_solid_has_virtual_splitter_plane,
    STL_AXIS_TO_LAYOUT_Z_TILTS,
    _rotation_matrix_from_kraken_tilts,
    optical_solid_face_world_markers,
    optical_solid_face_world_records,
    optical_solid_virtual_plane_world_markers,
    optical_solid_virtual_plane_world_records,
    _optical_solid_face_effective_radius_mm,
    match_optical_solid_world_face,
    _optical_solid_plane_basis,
    optical_solid_virtual_plane_segment_events,
    optical_solid_trace_sequence_records,
    _rotation_matrix_about_axis,
    _rotation_matrix_aligning_vectors,
    _optical_solid_face_local_normal,
    _optical_solid_face_fit_priority,
    select_optical_solid_anchor_face,
    _select_optical_solid_roll_reference_face,
    solve_optical_solid_face_fit,
    solve_optical_solid_two_face_fit,
    solve_optical_solid_left_input_pose,
    rotated_stl_bounds,
    transformed_stl_points,
    transformed_stl_bounds,
    convex_hull_2d,
)
from KrakenOS.UI.services.surface_value_parsing import (
    _coerce_opt_flag,
    _coerce_bounds,
    _compact_surface_attr_name,
    _normalize_native_variable_name,
    _native_variable_names,
    _parse_float_sequence_text,
    _dedupe_float_values,
    _format_float_sequence,
    _dedupe_preserve_order,
    _native_variable_matches,
)


def _canonical_advanced_surface_attr(value: object) -> str | None:
    return ADVANCED_SURFACE_ATTR_ALIASES.get(_compact_surface_attr_name(value))


def _advanced_surface_attrs_from_spec(spec: dict) -> dict[str, object]:
    attrs: dict[str, object] = {}
    for source_key in ("advanced", "advanced_attrs", "surface_attrs"):
        source = spec.get(source_key)
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            attr = _canonical_advanced_surface_attr(key)
            if attr is not None:
                attrs[attr] = value
    for key, value in spec.items():
        if str(key).strip().lower() == "element":
            continue
        attr = _canonical_advanced_surface_attr(key)
        if attr is not None:
            attrs[attr] = value
    return attrs


def _normalize_advanced_surface_value(attr: str, value):
    if attr in {"AspherData", "ZNK"}:
        try:
            array = np.asarray(value, dtype=float).ravel()
        except Exception:
            return value
        minimum = 200 if attr == "AspherData" else 36
        if array.size < minimum:
            array = np.pad(array, (0, minimum - array.size), mode="constant")
        return array
    if attr == "Error_map":
        try:
            return _error_map_literal(value)
        except Exception:
            return value
    if attr == "Mask_Shape":
        try:
            return _decode_mask_shape_value(value)
        except Exception:
            return value
    if attr == BEAM_SPLITTER_ADVANCED_ATTR:
        return _normalize_beam_splitter_settings(value)
    if attr == DIFFUSE_SCATTER_ADVANCED_ATTR:
        return _normalize_diffuse_scatter_settings(value)
    if attr == ELEMENT_ADVANCED_ATTR:
        return _normalize_element_metadata(value)
    if attr == SCENE_TARGET_ADVANCED_ATTR:
        return _normalize_scene_target_settings(value)
    if attr == SCENE_PLACEMENT_ADVANCED_ATTR:
        return normalize_scene_placement_settings(value)
    if attr == "Solid_3d_stl":
        return _normalize_optical_solid_path_value(value)
    if attr == "OpticalSolidFaces":
        return normalize_optical_solid_face_metadata(value)
    if attr == DRAWING_PROPERTIES_ADVANCED_ATTR:
        return normalize_drawing_properties(value)
    return value


def _decode_mask_shape_value(value):
    if not isinstance(value, dict):
        return value
    kind = str(value.get("kind", "")).strip().lower()
    if kind not in {"mask_shape", "mask", "mask_preset"}:
        return value
    preset = str(value.get("preset", value.get("name", ""))).strip().lower()
    _load_3d_backends()
    if pv is None:
        return value
    extent = max(float(value.get("extent", value.get("diameter", 50.0))), 1.0)
    block = pv.MultiBlock()
    if preset == "ronchi":
        period = max(float(value.get("period", extent / 20.0)), 1e-6)
        duty_cycle = min(max(float(value.get("duty_cycle", 0.5)), 0.02), 0.98)
        line_width = period * duty_cycle
        start = -0.5 * extent
        stop = 0.5 * extent
        positions = np.arange(start, stop + period, period)
        for position in positions:
            block.append(
                pv.Plane(
                    center=[float(position), 0.0, 0.0],
                    direction=[0.0, 0.0, 1.0],
                    i_size=float(line_width),
                    j_size=float(extent),
                    i_resolution=1,
                    j_resolution=1,
                )
            )
        return block
    if preset == "spider":
        arms = max(int(value.get("arms", 4)), 1)
        arm_width = max(float(value.get("arm_width", extent * 0.035)), 1e-6)
        hub_radius = max(float(value.get("hub_radius", extent * 0.08)), 0.0)
        for index in range(arms):
            angle = float(index) * 360.0 / float(arms)
            plane = pv.Plane(
                center=[0.0, 0.0, 0.0],
                direction=[0.0, 0.0, 1.0],
                i_size=float(extent),
                j_size=float(arm_width),
                i_resolution=1,
                j_resolution=1,
            )
            try:
                plane.rotate_z(angle, point=(0.0, 0.0, 0.0), inplace=True)
            except Exception:
                pass
            block.append(plane)
        if hub_radius > 0.0:
            try:
                block.append(
                    pv.Disc(
                        center=(0.0, 0.0, 0.0),
                        inner=0.0,
                        outer=float(hub_radius),
                        normal=(0.0, 0.0, 1.0),
                        r_res=2,
                        c_res=48,
                    )
                )
            except Exception:
                pass
        return block
    return value


def _native_variable_names_from_spec(spec: dict) -> list[str]:
    attrs = _advanced_surface_attrs_from_spec(spec)
    names = _native_variable_names(attrs.get("Var"))
    if _coerce_opt_flag(spec.get("optimize_rc", spec.get("opt_rc", ""))):
        names.append("Rc")
    if _coerce_opt_flag(spec.get("optimize_thickness", spec.get("opt_thickness", ""))):
        names.append("Thickness")
    return _dedupe_preserve_order(names)


def _row_native_variable_names(row: SurfaceRow) -> list[str]:
    return _native_variable_names((row.advanced or {}).get("Var"))


def _literal_editor_text(value) -> tuple[str, bool]:
    literal = _layout_literal_value(value)
    if literal is _UNSERIALIZABLE_LAYOUT_VALUE:
        return f"<non-literal {type(value).__module__}.{type(value).__qualname__}>", False
    return pformat(literal, width=100), True


def _parse_literal_editor_text(text: str):
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return ast.literal_eval(stripped)
    except Exception:
        return stripped


def _element_metadata_summary(value) -> str:
    metadata = _normalize_element_metadata(value)
    role = str(metadata["arm_role"])
    selector = str(metadata.get("branch_selector", "") or "").strip()
    leg_id = str(metadata.get("leg_id", "") or "").strip()
    parent = str(metadata.get("parent_splitter", "") or "").strip()
    branch_path = str(metadata.get("branch_path", "") or "").strip()
    distance = float(metadata.get("arm_distance", 0.0))
    parts = [role]
    if leg_id:
        parts.append(f"path={leg_id}")
    if parent:
        parts.append(f"parent={parent}")
    if selector:
        parts.append(f"selector={selector}")
    if branch_path:
        parts.append(f"branch={KrakenLayoutEditor._branch_path_compact_detail(branch_path)}")
    if abs(distance) > 1e-12:
        parts.append(f"d={distance:.6g} mm")
    return ", ".join(parts)


def _normalize_path_filter_label(value: object) -> str:
    return normalize_branch_throughput_filter_label(value)


def _is_all_path_filter(value: object) -> bool:
    return _normalize_path_filter_label(value) == ANALYSIS_PATH_FILTER_DEFAULT


def _normalize_coherent_sum_mode(value: object) -> str:
    return normalize_coherent_sum_mode(value)


def _known_glass_names() -> set[str]:
    global _KNOWN_GLASS_NAMES_CACHE
    if _KNOWN_GLASS_NAMES_CACHE is None:
        try:
            setup = _shared_setup()
            _KNOWN_GLASS_NAMES_CACHE = {str(name).strip().upper() for name in getattr(setup, "NAMES", [])}
        except Exception:
            _KNOWN_GLASS_NAMES_CACHE = set()
    return _KNOWN_GLASS_NAMES_CACHE


def _glass_nd_vd_from_setup(glass: str) -> tuple[float, float] | None:
    try:
        setup = _shared_setup()
        names = np.asarray(getattr(setup, "NAMES", []))
        wanted = str(glass).strip().upper()
        for index, name in enumerate(names):
            if str(name).strip().upper() != wanted:
                continue
            nm = list(getattr(setup, "NM", [])[index])
            if len(nm) >= 4:
                return float(nm[2]), float(nm[3])
    except Exception:
        return None
    return None


def _stock_lens_trace_glass(glass: str, catalog_surface: dict) -> tuple[str, str | None]:
    glass_text = str(glass or "AIR").strip()
    if not glass_text:
        return "AIR", None
    compact = glass_text.split(",", 1)[0].strip().upper()
    if compact in {"AIR", "MIRROR", "GRIN", "NVK", "___BLANK"}:
        return glass_text, None
    if compact in _known_glass_names():
        nd_vd = _glass_nd_vd_from_setup(compact)
        if nd_vd is not None:
            nd, vd = nd_vd
            return (
                f"nvk,{nd:.12g},{vd:.12g},0",
                f"Catalog glass {glass_text} was converted to n/V data from KrakenOS catalogs for robust stock-lens tracing.",
            )
        return glass_text, None
    refractive_index = catalog_surface.get("Refractive_index")
    abbe_num = catalog_surface.get("Abbe_num")
    if refractive_index is not None and abbe_num is not None:
        fallback = f"___BLANK,1,0,{float(refractive_index):.12g},{float(abbe_num):.12g},0,0,0,0,0,0"
        return fallback, f"Catalog glass {glass_text} was converted to embedded ___BLANK n/V data."
    fallback = "nvk,1.5,50,0"
    return fallback, f"Catalog glass {glass_text} is not in KrakenOS glass catalogs; using approximate n=1.5, V=50."


from KrakenOS.UI.services.error_map_metadata import (
    _finite_numeric_array,
    _error_map_space_scalar,
    _error_map_arrays,
    _error_map_literal,
    _positive_unique_steps,
    _infer_error_map_spacing,
    _error_map_from_xyz_columns,
    _error_map_from_z_matrix,
    _npz_value,
    _load_error_map_npz,
    _load_error_map_npy,
    _first_data_line,
    _load_error_map_text,
    _load_error_map_file,
    _error_map_summary,
    _validate_error_map,
)



from KrakenOS.UI.services.advanced_surface_validation import (
    _validate_coating_table,
    _validate_coating_met,
    _validate_drawing_properties,
    _validate_custom_extra_data,
    _validate_uda,
    _validate_optical_solid_virtual_planes,
    _validate_advanced_surface_inputs,
)


from KrakenOS.UI.services.zemax_prescription_import import (
    ZemaxImportDefaults,
    _read_zemax_text,
    _zemax_float,
    _zemax_round,
    _zemax_glass_from_tokens as _zemax_glass_from_tokens_for_import,
    load_zemax_zmx_data as _load_zemax_zmx_data_with_defaults,
)


def _zemax_glass_from_tokens(tokens: list[str]) -> tuple[str, str | None]:
    return _zemax_glass_from_tokens_for_import(tokens, known_glass_names=_known_glass_names)


def _zemax_import_defaults() -> ZemaxImportDefaults:
    return ZemaxImportDefaults(
        projection_display_mode=PROJECTION_MODE_AXIS_FIELD,
        source_model=SOURCE_MODEL_DEFAULT,
        pupil_pattern=PUPIL_PATTERN_DEFAULT,
        gaussian_input_mode=GAUSSIAN_INPUT_MODE_DEFAULT,
        gaussian_waist_side=GAUSSIAN_WAIST_SIDE_DEFAULT,
        source_angular_weight=SOURCE_ANGULAR_WEIGHT_DEFAULT,
        wavefront_style=WAVEFRONT_STYLE_DEFAULT,
        tolerance_compare_view=TOLERANCE_COMPARE_VIEW_DEFAULT,
        atmos_plot_mode=ATMOS_PLOT_MODE_DEFAULT,
        folded_detector_policy=FOLDED_DETECTOR_POLICY_DEFAULT,
    )


def _load_zemax_zmx_data(path: Path) -> dict:
    return _load_zemax_zmx_data_with_defaults(
        path,
        known_glass_names=_known_glass_names,
        defaults=_zemax_import_defaults(),
    )


_CUPY_IMPORT_ATTEMPTED = False
_CUPY_MODULE = None
_TORCH_IMPORT_ATTEMPTED = False
_TORCH_MODULE = None
_CUDA_LIBS_PRELOADED = False
_WORKER_SYSTEM_CACHE_SIGNATURE = None
_WORKER_SYSTEM_CACHE_SYSTEM = None
_SETUP_CACHE_BY_METAL_SIGNATURE = {}
_KNOWN_GLASS_NAMES_CACHE: set[str] | None = None
_PREVIEW_GLASS_INDEX_CACHE: dict[str, float] = {}


def _available_testing_zemax_prescriptions(root: Path = ZEMAX_TESTING_DIR) -> dict[str, Path]:
    return discover_zemax_prescriptions(root)


def _preload_cuda_libraries():
    global _CUDA_LIBS_PRELOADED
    if _CUDA_LIBS_PRELOADED:
        return
    _CUDA_LIBS_PRELOADED = True

    driver_candidates = (
        "/run/opengl-driver/lib/libcuda.so.1",
        "/run/opengl-driver/lib/libcuda.so",
        "/run/opengl-driver-32/lib/libcuda.so.1",
        "/run/opengl-driver-32/lib/libcuda.so",
    )
    for candidate in driver_candidates:
        if not os.path.exists(candidate):
            continue
        try:
            ctypes.CDLL(candidate, mode=ctypes.RTLD_GLOBAL)
            break
        except Exception:
            continue

    # Best-effort preload of CUDA runtime/NVRTC from pip wheels.
    package_libs = (
        ("nvidia.cuda_nvrtc", ("libnvrtc.so",)),
        ("nvidia.cuda_runtime", ("libcudart.so",)),
        ("nvidia.cu13", ("libnvrtc-builtins.so", "libnvrtc.so", "libcudart.so", "libcufft.so")),
    )
    for module_name, lib_prefixes in package_libs:
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None or not spec.submodule_search_locations:
                continue
            for search_path in spec.submodule_search_locations:
                lib_dir = Path(search_path) / "lib"
                if not lib_dir.exists():
                    continue
                for prefix in lib_prefixes:
                    for lib_path in sorted(lib_dir.glob(f"{prefix}*")):
                        try:
                            ctypes.CDLL(str(lib_path), mode=ctypes.RTLD_GLOBAL)
                            break
                        except Exception:
                            continue
        except Exception:
            continue


def _short_error_message(exc: Exception, limit: int = 220) -> str:
    text = str(exc).strip()
    if not text:
        return exc.__class__.__name__
    first = text.splitlines()[0].strip()
    if len(first) > limit:
        return first[:limit] + "..."
    return first


def _install_nonfatal_x_error_handler() -> None:
    """Install a non-fatal X11 error handler to prevent VTK GLX BadAccess crashes."""
    global _x_error_handler_ref
    if _x_error_handler_ref is not None:
        return
    try:
        import ctypes
        import ctypes.util
        x11_path = ctypes.util.find_library("X11")
        if not x11_path:
            return
        x11 = ctypes.cdll.LoadLibrary(x11_path)
        HANDLER = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)
        def _handler(display, event):
            return 0
        _x_error_handler_ref = HANDLER(_handler)
        x11.XSetErrorHandler(_x_error_handler_ref)
    except Exception:
        pass


def _load_3d_backends() -> None:
    """Load PyVista/VTK only when the user opens 3D or CAD overlays."""
    global _3D_BACKENDS_ATTEMPTED
    global pv, vtkTkRenderWindowInteractor, vtkTubeFilter, vtkOrientationMarkerWidget
    global vtkAxesActor, vtkActor, vtkCellPicker, vtkDataSetMapper, vtkRenderer, vtkTextActor, vtkBillboardTextActor3D
    global _VTK_TK_UNAVAILABLE_REASON
    if _3D_BACKENDS_ATTEMPTED:
        return
    _3D_BACKENDS_ATTEMPTED = True
    _VTK_TK_UNAVAILABLE_REASON = ""
    _install_nonfatal_x_error_handler()
    try:
        import pyvista as _pv  # type: ignore

        pv = _pv
    except Exception:
        pv = None
    try:
        from vtkmodules.vtkFiltersCore import vtkTubeFilter as _vtk_tube
        from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget as _vtk_marker
        from vtkmodules.vtkRenderingAnnotation import vtkAxesActor as _vtk_axes
        from vtkmodules.vtkRenderingCore import (
            vtkActor as _vtk_actor,
            vtkCellPicker as _vtk_picker,
            vtkDataSetMapper as _vtk_mapper,
            vtkRenderer as _vtk_renderer,
            vtkTextActor as _vtk_text_actor,
        )
        try:
            from vtkmodules.vtkRenderingCore import vtkBillboardTextActor3D as _vtk_billboard_text_actor_3d
        except Exception:
            _vtk_billboard_text_actor_3d = None

        vtk_tk_library = _active_vtk_tk_widget_library()
        if vtk_tk_library is None:
            _vtk_tk = None
            _VTK_TK_UNAVAILABLE_REASON = (
                "VTK/Tk native widget library libvtkRenderingTk.so is not installed; "
                "using the Matplotlib/Tk picker."
            )
        else:
            try:
                from vtkmodules.tk.vtkTkRenderWindowInteractor import vtkTkRenderWindowInteractor as _vtk_tk
                _VTK_TK_UNAVAILABLE_REASON = ""
            except Exception as exc:
                _vtk_tk = None
                _VTK_TK_UNAVAILABLE_REASON = f"VTK/Tk Python widget wrapper is not importable: {exc}"

        vtkTkRenderWindowInteractor = _vtk_tk
        vtkTubeFilter = _vtk_tube
        vtkOrientationMarkerWidget = _vtk_marker
        vtkAxesActor = _vtk_axes
        vtkActor = _vtk_actor
        vtkCellPicker = _vtk_picker
        vtkDataSetMapper = _vtk_mapper
        vtkRenderer = _vtk_renderer
        vtkTextActor = _vtk_text_actor
        vtkBillboardTextActor3D = _vtk_billboard_text_actor_3d
    except Exception:
        vtkTkRenderWindowInteractor = None
        vtkTubeFilter = None
        vtkOrientationMarkerWidget = None
        vtkAxesActor = None
        vtkActor = None
        vtkCellPicker = None
        vtkDataSetMapper = None
        vtkRenderer = None
        vtkTextActor = None
        vtkBillboardTextActor3D = None
        if not _VTK_TK_UNAVAILABLE_REASON:
            _VTK_TK_UNAVAILABLE_REASON = "VTK rendering modules are not importable."


def _active_vtk_tk_widget_library() -> Path | None:
    candidate_dirs: list[Path] = []
    for env_name in ("KRAKEN_VTK_TK_LIB_DIR", "VTK_TK_LIB_DIR", "TCLLIBPATH", "LD_LIBRARY_PATH"):
        env_value = os.environ.get(env_name, "")
        for item in env_value.split(os.pathsep):
            if not item:
                continue
            candidate = Path(item).expanduser()
            candidate_dirs.append(candidate.parent if candidate.name == "libvtkRenderingTk.so" else candidate)
    try:
        import vtkmodules  # type: ignore
    except Exception:
        vtkmodules = None
    if vtkmodules is not None:
        vtkmodules_dir = Path(vtkmodules.__file__).resolve().parent
        candidate_dirs.append(vtkmodules_dir)
        package_dir = vtkmodules_dir.parent
        python_dir = package_dir.parent
        if python_dir.name.startswith("python") and python_dir.parent.name.startswith("lib"):
            candidate_dirs.append(python_dir.parent)
    candidate_dirs.append(Path("/usr/local/lib"))
    seen: set[Path] = set()
    for directory in candidate_dirs:
        try:
            directory = directory.resolve()
        except Exception:
            continue
        if directory in seen:
            continue
        seen.add(directory)
        library_path = directory / "libvtkRenderingTk.so"
        if library_path.exists():
            return library_path
    return None


def _prepare_vtk_tk_widget(master: tk.Misc) -> None:
    """Expose an externally installed libvtkRenderingTk.so to VTK's Tcl loader."""
    library_path = _active_vtk_tk_widget_library()
    if library_path is None:
        return
    try:
        master.tk.call("lappend", "auto_path", str(library_path.parent))
    except Exception:
        pass


def _load_display_helpers() -> tuple[object | None, object | None, object | None]:
    """Import legacy Display helpers lazily because Display imports PyVista."""
    global _DISPLAY_HELPERS_ATTEMPTED
    global _DISPLAY_EDGE_3D, _DISPLAY_FILTER_FACE_2DPLOT, _DISPLAY_WAVELENGTH_TO_RGB
    if not _DISPLAY_HELPERS_ATTEMPTED:
        _DISPLAY_HELPERS_ATTEMPTED = True
        try:
            from KrakenOS.Display import edge_3d, filter_face_2dplot, wavelength_to_rgb

            _DISPLAY_EDGE_3D = edge_3d
            _DISPLAY_FILTER_FACE_2DPLOT = filter_face_2dplot
            _DISPLAY_WAVELENGTH_TO_RGB = wavelength_to_rgb
        except Exception:
            _DISPLAY_EDGE_3D = None
            _DISPLAY_FILTER_FACE_2DPLOT = None
            _DISPLAY_WAVELENGTH_TO_RGB = None
    return _DISPLAY_EDGE_3D, _DISPLAY_FILTER_FACE_2DPLOT, _DISPLAY_WAVELENGTH_TO_RGB


def _wavelength_to_rgb(wavelength_nm: float) -> tuple[float, float, float]:
    _edge, _filter, color_func = _load_display_helpers()
    if color_func is not None:
        try:
            return tuple(color_func(wavelength_nm))
        except Exception:
            pass
    return (0.0, 0.55, 1.0)


def _color_to_rgb_tuple(color: object) -> tuple[float, float, float]:
    if isinstance(color, str):
        text = color.strip()
        if text.startswith("#") and len(text) == 7:
            try:
                return (
                    int(text[1:3], 16) / 255.0,
                    int(text[3:5], 16) / 255.0,
                    int(text[5:7], 16) / 255.0,
                )
            except ValueError:
                pass
    try:
        values = tuple(float(value) for value in color)  # type: ignore[arg-type]
        if len(values) >= 3:
            return values[:3]
    except Exception:
        pass
    return (0.0, 0.55, 1.0)


def _external_camera_spec(name: str) -> dict[str, object] | None:
    spec = EXTERNAL_CAMERA_MODELS.get(name)
    return dict(spec) if isinstance(spec, dict) else None


def _cached_cad_mesh_path(path: Path) -> Path:
    return cad_import_service.cached_cad_mesh_path(path, CAD_CACHE_DIR)


def _cached_outer_cad_mesh_path(path: Path, solid_indices: tuple[int, ...]) -> Path:
    return cad_import_service.cached_outer_cad_mesh_path(path, solid_indices, CAD_CACHE_DIR)


def _cached_cad_reference_path(path: Path, solid_indices: tuple[int, ...]) -> Path:
    return cad_import_service.cached_cad_reference_path(path, solid_indices, CAD_CACHE_DIR)


def _cached_cad_section_path(path: Path, solid_indices: tuple[int, ...]) -> Path:
    return cad_import_service.cached_cad_section_path(path, solid_indices, CAD_CACHE_DIR)


def _python_with_import(module_name: str) -> str:
    return cad_import_service.python_with_import(module_name)


def _convert_step_to_stl(source_path: Path, target_path: Path) -> None:
    cad_import_service.convert_step_to_stl(source_path, target_path)


def _optical_solid_mesh_path_from_source(source_path: Path) -> tuple[Path, Path | None, str]:
    return cad_import_service.optical_solid_mesh_path_from_source(
        source_path,
        cache_dir=CAD_CACHE_DIR,
        stl_suffixes=OPTICAL_SOLID_STL_SUFFIXES,
        cad_suffixes=OPTICAL_SOLID_CAD_SUFFIXES,
    )


def _resolve_project_file_path(path_text: str) -> Path:
    candidate = Path(path_text).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return candidate
    for root in (PROJECT_ROOT, EXAMPLES_DIR, LAYOUTS_DIR, Path.cwd()):
        resolved = root / candidate
        if resolved.exists():
            return resolved
    return candidate


def _normalize_optical_solid_path_value(value):
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text == "None":
        return value
    suffix = Path(text).suffix.lower()
    if suffix not in OPTICAL_SOLID_STL_SUFFIXES | OPTICAL_SOLID_CAD_SUFFIXES:
        return value
    source_path = _resolve_project_file_path(text)
    if not source_path.exists():
        return value
    mesh_path, _cad_source_path, _source_format = _optical_solid_mesh_path_from_source(source_path)
    return str(mesh_path)


def _extract_step_outer_subset_to_stl(source_path: Path, target_path: Path, solid_indices: tuple[int, ...]) -> None:
    cad_import_service.extract_step_outer_subset_to_stl(
        source_path,
        target_path,
        solid_indices,
        tools_dir=Path(__file__).resolve().parents[2] / "tools",
    )


def _extract_step_reference(source_path: Path, target_path: Path, solid_indices: tuple[int, ...]) -> dict[str, object]:
    return cad_import_service.extract_step_reference(
        source_path,
        target_path,
        solid_indices,
        tools_dir=Path(__file__).resolve().parents[2] / "tools",
    )


def _extract_step_section_profile(source_path: Path, target_path: Path, solid_indices: tuple[int, ...]) -> dict[str, object]:
    return cad_import_service.extract_step_section_profile(
        source_path,
        target_path,
        solid_indices,
        tools_dir=Path(__file__).resolve().parents[2] / "tools",
    )


from KrakenOS.UI.services.cad_step_export import (
    _rotation_matrix_xyz,
    _convex_hull_2d,
    _profile_from_section_points,
    _is_surface_revolution_compatible,
    _compute_revolution_sag,
    _make_occ_flat_disc,
    _make_occ_revolution_face,
    _numpy_mat_to_occ_trsf,
    _numpy_mat_to_occ_gtrsf,
    _affine_from_point_sets,
    _read_step_shape,
    _shape_with_affine,
    _write_meshes_to_faceted_step,
    _mesh_points_and_triangles_for_step,
    _write_step_with_analytic_surfaces,
    _write_step_with_cad_shapes_and_rays,
)


from KrakenOS.UI.services.ray_display_geometry import (
    _finite_polyline_points,
    _convex_hull_indices_2d,
    _ray_group_envelope_indices,
    _ray_bundle_envelope_polylines,
    _raykeeper_branch_path_strings,
    _raykeeper_has_non_primary_branch_paths,
    _finite_bounds_array,
    _bounds_span,
    _optical_axis_z_span,
    _extended_axis_points,
    _clean_polyline_points,
    _dotted_axis_records_from_ray_path,
)



def _dotted_axis_mesh_from_points(points, *, dash_count: int = 96) -> object | None:
    """Build a dashed pickable guide along one 3D polyline."""
    if pv is None:
        return None
    try:
        pts = np.asarray(points, dtype=float)
    except Exception:
        return None
    if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
        return None
    pts = np.asarray(pts[:, :3], dtype=float)
    if not np.all(np.isfinite(pts)):
        return None
    parts = []
    total_length = 0.0
    lengths: list[float] = []
    for start, end in zip(pts[:-1], pts[1:]):
        length = float(np.linalg.norm(end - start))
        if np.isfinite(length) and length > 1e-9:
            total_length += length
        lengths.append(length)
    if total_length <= 1e-9:
        return None
    dash_count = max(8, int(dash_count))
    for start, end, length in zip(pts[:-1], pts[1:], lengths):
        if not np.isfinite(length) or length <= 1e-9:
            continue
        segment_count = max(2, int(round(dash_count * length / total_length)))
        direction = (end - start) / length
        step = length / float(segment_count)
        for index in range(segment_count):
            if index % 2:
                continue
            dash_start = start + direction * (index * step)
            dash_end = start + direction * min((index + 0.58) * step, length)
            try:
                parts.append(pv.Line(tuple(dash_start), tuple(dash_end)))
            except Exception:
                pass
    if not parts:
        return None
    merged = parts[0]
    for part in parts[1:]:
        try:
            merged = merged.merge(part)
        except Exception:
            pass
    return merged


def _dotted_optical_axis_mesh(bounds) -> object | None:
    """Build a long dashed guide on the KrakenOS optical axis (X=Y=0)."""
    z0, z1 = _optical_axis_z_span(bounds)
    return _dotted_axis_mesh_from_points(np.asarray(((0.0, 0.0, z0), (0.0, 0.0, z1)), dtype=float))






def _optional_cupy():
    global _CUPY_IMPORT_ATTEMPTED, _CUPY_MODULE
    if not _CUPY_IMPORT_ATTEMPTED:
        _CUPY_IMPORT_ATTEMPTED = True
        _preload_cuda_libraries()
        try:
            import cupy as cp  # type: ignore
            _CUPY_MODULE = cp
        except Exception:
            _CUPY_MODULE = None
    return _CUPY_MODULE


def _optional_torch():
    global _TORCH_IMPORT_ATTEMPTED, _TORCH_MODULE
    if not _TORCH_IMPORT_ATTEMPTED:
        _TORCH_IMPORT_ATTEMPTED = True
        _preload_cuda_libraries()
        try:
            import torch  # type: ignore
            _TORCH_MODULE = torch
        except Exception:
            _TORCH_MODULE = None
    return _TORCH_MODULE


def _shared_setup(metal_catalogs=None):
    signature = _metal_catalog_signature(metal_catalogs or [])
    setup = _SETUP_CACHE_BY_METAL_SIGNATURE.get(signature)
    if setup is None:
        with io.StringIO() as stdout_buf, io.StringIO() as stderr_buf:
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                setup = Kos.Setup()
                _load_metal_catalogs_into_setup(setup, metal_catalogs or [])
        _SETUP_CACHE_BY_METAL_SIGNATURE[signature] = setup
    return setup


def _build_system_from_specs(row_specs: list[dict], *, build: int = 0, setup=None) -> object:
    surfaces = []
    clear_aperture = max(
        [max(float(spec["diameter"]), 1.0) for spec in row_specs if spec["surface"] not in {"Object", "Image"}] or [100.0]
    ) * 4.0
    for spec in row_specs:
        surface = Kos.surf()
        surface.Name = ""
        surface.Rc = float(spec["rc"])
        surface.k = float(spec.get("k", spec.get("K", 0.0)))
        surface.Axicon = float(spec.get("axicon", 0.0))
        surface.Diff_Ord = float(spec.get("diff_ord", spec.get("Diff_Ord", 0.0)))
        surface.Grating_D = float(spec.get("grating_d", spec.get("Grating_D", 0.0)))
        surface.Grating_Angle = float(spec.get("grating_angle", spec.get("Grating_Angle", 0.0)))
        surface.Thickness = float(spec["thickness"])
        surface.Diameter = clear_aperture if spec["surface"] == "Object" else float(spec["diameter"])
        surface.InDiameter = float(spec.get("in_diameter", spec.get("InDiameter", 0.0)))
        if "extra_data" in spec or "ExtraData" in spec:
            surface.ExtraData = decode_custom_surface_value(spec.get("extra_data", spec.get("ExtraData", surface.ExtraData)))
        if "uda" in spec or "UDA" in spec:
            surface.UDA = decode_custom_surface_value(spec.get("uda", spec.get("UDA", surface.UDA)))
        for attr, value in _advanced_surface_attrs_from_spec(spec).items():
            setattr(surface, attr, _normalize_advanced_surface_value(attr, value))
        native_vars = _native_variable_names_from_spec(spec)
        if native_vars:
            surface.Var = native_vars
        surface.Glass = str(spec["glass"])
        surface.TiltX = float(spec.get("tilt_x", 0.0))
        surface.TiltY = float(spec.get("tilt_y", 0.0))
        surface.TiltZ = float(spec.get("tilt_z", 0.0))
        surface.DespX = float(spec.get("desp_x", 0.0))
        surface.DespY = float(spec.get("desp_y", 0.0))
        surface.DespZ = float(spec.get("desp_z", 0.0))
        surface.AxisMove = float(spec.get("axis_move", 0.0))
        surface.Drawing = float(
            spec.get(
                "drawing",
                spec.get(
                    "Drawing",
                    0.0 if spec["surface"] in {"Object", "Image", *REFLECTIVE_PROXY_SURFACES} else 1.0,
                ),
            )
        )
        if spec["surface"] in REFLECTIVE_PROXY_SURFACES:
            surface.Glass = "MIRROR"
            if abs(surface.AxisMove) < 1e-9:
                surface.AxisMove = 2.0
        if spec["surface"] == DIFFUSE_OBJECT_SURFACE:
            advanced = _advanced_surface_attrs_from_spec(spec)
            surface.DiffuseScatter = _normalize_diffuse_scatter_settings(
                advanced.get(DIFFUSE_SCATTER_ADVANCED_ATTR, DIFFUSE_SCATTER_DEFAULT_SETTINGS)
            )
        if spec["surface"] == BEAM_SPLITTER_SURFACE:
            advanced = _advanced_surface_attrs_from_spec(spec)
            splitter_settings = _normalize_beam_splitter_settings(advanced.get(BEAM_SPLITTER_ADVANCED_ATTR))
            surface.BeamSplitter = splitter_settings
            surface.Coating = _beam_splitter_coating_for_settings(splitter_settings, advanced.get("Coating"))
            if str(surface.Glass).upper() == "MIRROR":
                surface.Glass = "AIR"
        if spec["surface"] == "Thin Lens":
            focal = float(spec["rc"])
            surface.Thin_Lens = focal if focal != 0.0 else 100.0
            surface.Rc = 0.0
        elif spec["surface"] == "Grating":
            if abs(float(surface.Diff_Ord)) < 1e-12:
                surface.Diff_Ord = 1.0
            if abs(float(surface.Grating_D)) < 1e-12:
                surface.Grating_D = 1.0
        surfaces.append(surface)
    metal_catalogs = _metal_catalogs_from_row_specs(row_specs)
    system = Kos.system(surfaces, _shared_setup(metal_catalogs) if setup is None else setup, build=int(build))
    apply_optical_solid_output_port_system_overrides(system, row_specs)
    return system


def _surface_signature_token(value):
    if value is None or isinstance(value, (str, int, float, bool, np.floating, np.integer)):
        return value
    if isinstance(value, np.ndarray):
        array = np.asarray(value)
        return (
            "ndarray",
            array.shape,
            str(array.dtype),
            hashlib.sha1(array.tobytes()).hexdigest(),
        )
    if isinstance(value, dict):
        return tuple(sorted((str(key), _surface_signature_token(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_surface_signature_token(item) for item in value)
    if callable(value):
        return (
            "callable",
            getattr(value, "__module__", type(value).__module__),
            getattr(value, "__qualname__", getattr(value, "__name__", type(value).__qualname__)),
            id(value),
        )
    return (
        type(value).__module__,
        type(value).__qualname__,
        id(value),
    )


def _layout_literal_value(value):
    encoded_custom = encode_custom_surface_value(value)
    if encoded_custom is not None and encoded_custom is not value:
        return _layout_literal_value(encoded_custom)
    if value is None or isinstance(value, (str, int, float, bool, np.floating, np.integer)):
        return value
    if isinstance(value, np.ndarray):
        return np.asarray(value).tolist()
    if isinstance(value, (list, tuple)):
        converted = []
        for item in value:
            literal = _layout_literal_value(item)
            if literal is _UNSERIALIZABLE_LAYOUT_VALUE:
                return _UNSERIALIZABLE_LAYOUT_VALUE
            converted.append(literal)
        return converted
    if isinstance(value, dict):
        converted = {}
        for key, item in value.items():
            literal = _layout_literal_value(item)
            if literal is _UNSERIALIZABLE_LAYOUT_VALUE:
                return _UNSERIALIZABLE_LAYOUT_VALUE
            converted[str(key)] = literal
        return converted
    return _UNSERIALIZABLE_LAYOUT_VALUE


_UNSERIALIZABLE_LAYOUT_VALUE = object()


def _row_specs_signature(row_specs: list[dict]):
    metal_signature = _metal_catalog_signature(_metal_catalogs_from_row_specs(row_specs))
    signature = []
    for spec in row_specs:
        signature.append(
            (
                str(spec.get("surface", "")),
                str(spec.get("name", "")),
                float(spec.get("rc", 0.0)),
                float(spec.get("k", spec.get("K", 0.0))),
                float(spec.get("axicon", 0.0)),
                float(spec.get("diff_ord", spec.get("Diff_Ord", 0.0))),
                float(spec.get("grating_d", spec.get("Grating_D", 0.0))),
                float(spec.get("grating_angle", spec.get("Grating_Angle", 0.0))),
                float(spec.get("thickness", 0.0)),
                float(spec.get("diameter", 0.0)),
                float(spec.get("in_diameter", spec.get("InDiameter", 0.0))),
                float(spec.get("drawing", spec.get("Drawing", 1.0))),
                _surface_signature_token(spec.get("extra_data", spec.get("ExtraData", 0.0))),
                _surface_signature_token(spec.get("uda", spec.get("UDA", "None"))),
                _surface_signature_token(_advanced_surface_attrs_from_spec(spec)),
                str(spec.get("glass", "AIR")),
                float(spec.get("tilt_x", 0.0)),
                float(spec.get("tilt_y", 0.0)),
                float(spec.get("tilt_z", 0.0)),
                float(spec.get("desp_x", 0.0)),
                float(spec.get("desp_y", 0.0)),
                float(spec.get("desp_z", 0.0)),
                float(spec.get("axis_move", 0.0)),
            )
        )
    return metal_signature, tuple(signature)


def _build_cached_system_from_specs(row_specs: list[dict]) -> object:
    global _WORKER_SYSTEM_CACHE_SIGNATURE, _WORKER_SYSTEM_CACHE_SYSTEM
    signature = _row_specs_signature(row_specs)
    if _WORKER_SYSTEM_CACHE_SYSTEM is None or _WORKER_SYSTEM_CACHE_SIGNATURE != signature:
        _WORKER_SYSTEM_CACHE_SYSTEM = _build_system_from_specs(row_specs, build=0)
        _WORKER_SYSTEM_CACHE_SIGNATURE = signature
    return _WORKER_SYSTEM_CACHE_SYSTEM


def _requires_scalar_trace(row_specs: list[dict]) -> bool:
    # Kraken's current batch path is fast, but it does not reproduce all
    # scalar Trace() physics for thin-lens and tilted/folded elements.
    for spec in row_specs:
        if str(spec.get("surface", "")) in {"Thin Lens", "Mirror", "Grating", BEAM_SPLITTER_SURFACE}:
            return True
        if abs(float(spec.get("axicon", 0.0))) > 1e-12:
            return True
        if any(
            abs(float(spec.get(field, 0.0))) > 1e-12
            for field in ("tilt_x", "tilt_y", "tilt_z", "desp_x", "desp_y", "desp_z", "axis_move")
        ):
            return True
    return False


def _pick_image_plane_data_static(rays):
    try:
        X, Y, Z, L, M, N = rays.pick(-1, coordinates="local")
        if np.asarray(X).size:
            return X, Y, Z, L, M, N
    except Exception:
        pass
    return rays.pick(-1)


def _trace_analysis_chunk(
    row_specs: list[dict],
    wavelength: float,
    x_bundle,
    y_bundle,
    z_bundle,
    l_bundle,
    m_bundle,
    n_bundle,
):
    system = _build_cached_system_from_specs(row_specs)
    x_vals = np.asarray(x_bundle, dtype=float)
    y_vals = np.asarray(y_bundle, dtype=float)
    z_vals = np.asarray(z_bundle, dtype=float)
    l_vals = np.asarray(l_bundle, dtype=float)
    m_vals = np.asarray(m_bundle, dtype=float)
    n_vals = np.asarray(n_bundle, dtype=float)
    rays = Kos.raykeeper(system)
    trace_loop = getattr(Kos, "BatchTraceLoop", None)
    try:
        if trace_loop is None or _requires_scalar_trace(row_specs):
            raise RuntimeError("BatchTraceLoop unavailable")
        trace_loop(
            x_vals,
            y_vals,
            z_vals,
            l_vals,
            m_vals,
            n_vals,
            float(wavelength),
            rays,
            clean=1,
        )
    except Exception:
        rays = Kos.raykeeper(system)
        Kos.TraceLoop(
            x_vals,
            y_vals,
            z_vals,
            l_vals,
            m_vals,
            n_vals,
            float(wavelength),
            rays,
            clean=1,
        )
    x_local, y_local, _z_local, _l_local, _m_local, _n_local = _pick_image_plane_data_static(rays)
    return np.asarray(x_local, dtype=float), np.asarray(y_local, dtype=float)


def _trace_analysis_chunk_full(
    row_specs: list[dict],
    wavelength: float,
    x_bundle,
    y_bundle,
    z_bundle,
    l_bundle,
    m_bundle,
    n_bundle,
):
    system = _build_cached_system_from_specs(row_specs)
    x_vals = np.asarray(x_bundle, dtype=float)
    y_vals = np.asarray(y_bundle, dtype=float)
    z_vals = np.asarray(z_bundle, dtype=float)
    l_vals = np.asarray(l_bundle, dtype=float)
    m_vals = np.asarray(m_bundle, dtype=float)
    n_vals = np.asarray(n_bundle, dtype=float)
    rays = Kos.raykeeper(system)
    trace_loop = getattr(Kos, "BatchTraceLoop", None)
    try:
        if trace_loop is None or _requires_scalar_trace(row_specs):
            raise RuntimeError("BatchTraceLoop unavailable")
        trace_loop(
            x_vals,
            y_vals,
            z_vals,
            l_vals,
            m_vals,
            n_vals,
            float(wavelength),
            rays,
            clean=1,
        )
    except Exception:
        rays = Kos.raykeeper(system)
        Kos.TraceLoop(
            x_vals,
            y_vals,
            z_vals,
            l_vals,
            m_vals,
            n_vals,
            float(wavelength),
            rays,
            clean=1,
        )
    x_local, y_local, z_local, l_local, m_local, n_local = _pick_image_plane_data_static(rays)
    return (
        np.asarray(x_local, dtype=float),
        np.asarray(y_local, dtype=float),
        np.asarray(z_local, dtype=float),
        np.asarray(l_local, dtype=float),
        np.asarray(m_local, dtype=float),
        np.asarray(n_local, dtype=float),
    )


def _build_pupil_bundle_static(
    row_specs: list[dict],
    wavelength: float,
    sample_count: int,
    pattern: str,
    *,
    surface_index: int,
    aperture_type: str,
    aperture_value: float,
    field_type: str,
    field_x: float,
    field_y: float,
    pupil_rad: float = 0.0,
    pupil_theta: float = 0.0,
):
    system = _build_cached_system_from_specs(row_specs)
    pupil = Kos.PupilCalc(
        system,
        int(surface_index),
        float(wavelength),
        str(aperture_type),
        float(aperture_value),
    )
    pupil.Samp = max(2, int(sample_count))
    pupil.Ptype = str(pattern)
    pupil.rad = float(np.clip(float(pupil_rad), 0.0, 1.0))
    pupil.theta = float(pupil_theta)
    pupil.FieldType = str(field_type)
    pupil.FieldX = float(field_x)
    pupil.FieldY = float(field_y)
    return tuple(np.asarray(values, dtype=float) for values in pupil.Pattern2Field())


def _trace_preview_chunk_batch(
    row_specs: list[dict],
    wavelength: float,
    x_bundle,
    y_bundle,
    z_bundle,
    l_bundle,
    m_bundle,
    n_bundle,
):
    system = _build_cached_system_from_specs(row_specs)
    p_sources = np.column_stack(
        (
            np.asarray(x_bundle, dtype=float),
            np.asarray(y_bundle, dtype=float),
            np.asarray(z_bundle, dtype=float),
        )
    )
    d_cosines = np.column_stack(
        (
            np.asarray(l_bundle, dtype=float),
            np.asarray(m_bundle, dtype=float),
            np.asarray(n_bundle, dtype=float),
        )
    )
    try:
        if _requires_scalar_trace(row_specs):
            raise RuntimeError("BatchTrace unsupported for this surface set")
        system.BatchTrace(p_sources, d_cosines, float(wavelength))
        return system._batch_results, np.asarray(system._batch_active, dtype=bool)
    except Exception:
        batch_results: list[dict[str, object]] = []
        batch_active: list[bool] = []
        for source, direction in zip(np.asarray(p_sources, dtype=float), np.asarray(d_cosines, dtype=float)):
            system.Trace(source.tolist(), direction.tolist(), float(wavelength))
            batch_results.append(_serialize_trace_state(system))
            batch_active.append(bool(getattr(system, "val", 0) == 1))
        return batch_results, np.asarray(batch_active, dtype=bool)


def _serialize_trace_state(system) -> dict[str, object]:
    def _as_list(values) -> list:
        if values is None:
            return []
        if isinstance(values, np.ndarray):
            return values.tolist()
        if isinstance(values, (list, tuple)):
            return np.asarray(values, dtype=object).tolist()
        return [values]

    def _numeric_list(values, *, cast=float) -> list:
        items: list = []
        for value in _as_list(values):
            if value is None:
                continue
            try:
                arr = np.asarray(value, dtype=float).reshape(-1)
            except Exception:
                continue
            for item in arr:
                items.append(cast(item))
        return items

    def _point_list(values) -> list[list[float]]:
        points: list[list[float]] = []
        iterable = [] if values is None else values
        for value in iterable:
            if value is None:
                continue
            arr = np.asarray(value, dtype=float).reshape(-1)
            if arr.size >= 3:
                points.append([float(arr[0]), float(arr[1]), float(arr[2])])
        return points

    top_value = getattr(system, "TOP", 0.0)
    if isinstance(top_value, np.ndarray):
        try:
            top_value = float(np.asarray(top_value, dtype=float).reshape(-1)[-1])
        except Exception:
            top_value = 0.0
    return {
        "SURFACE": _numeric_list(getattr(system, "SURFACE", []), cast=int),
        "NAME": [str(v) for v in _as_list(getattr(system, "NAME", []))],
        "GLASS": [str(v) for v in _as_list(getattr(system, "GLASS", []))],
        "S_XYZ": _point_list(getattr(system, "S_XYZ", [])),
        "T_XYZ": _point_list(getattr(system, "T_XYZ", [])),
        "XYZ": _point_list(getattr(system, "XYZ", [])),
        "OST_XYZ": _point_list(getattr(system, "OST_XYZ", [])),
        "OST_LMN": _point_list(getattr(system, "OST_LMN", [])),
        "S_LMN": _point_list(getattr(system, "S_LMN", [])),
        "LMN": _point_list(getattr(system, "LMN", [])),
        "R_LMN": _point_list(getattr(system, "R_LMN", [])),
        "N0": _numeric_list(getattr(system, "N0", [])),
        "N1": _numeric_list(getattr(system, "N1", [])),
        "DISTANCE": _numeric_list(getattr(system, "DISTANCE", [])),
        "OP": _numeric_list(getattr(system, "OP", [])),
        "TOP_S": _numeric_list(getattr(system, "TOP_S", [])),
        "TOP": float(top_value),
        "val": int(getattr(system, "val", 0)),
        "RAY": _point_list(getattr(system, "ray_SurfHits", [])),
    }


def _serialize_operand_results(operands) -> list[dict]:
    serialized = []
    for operand in operands:
        serialized.append(
            {
                "name": str(getattr(operand, "name", "")),
                "value": float(getattr(operand, "value", 0.0)),
                "weighted": float(getattr(operand, "weighted", 0.0)),
                "target": float(getattr(operand, "target", 0.0)),
            }
        )
    return serialized


def _run_optimization_job(
    progress_queue,
    stop_event,
    row_specs: list[dict],
    merit_function: MeritFunction,
    variables: list[OpticalVariable],
    x0: list[float],
    generations_total: int,
    verbosity_every: int,
    population_size: int,
    optimization_workers: int,
    parallel_enabled: bool,
):
    try:
        if os.name == "posix":
            try:
                os.setsid()
            except Exception:
                pass
        pg = import_pygmo()

        system = _build_system_from_specs(row_specs)
        has_mtf_operand = any(isinstance(operand, MTFAtFrequencyOperand) for operand in merit_function.operands)
        evaluator = MeritEvaluator(
            system.SDT,
            setup=system.SETUP,
            merit_function=merit_function,
            mtf_worker_count=max(1, int(optimization_workers)) if has_mtf_operand else 1,
        )
        try:
            initial = evaluator.evaluate(variables, x0)

            udp = Pygmo2MeritProblem(evaluator=evaluator, variables=variables)
            problem = pg.problem(udp)
            workers = 1
            backend = "sequential"
            population_kwargs: dict[str, object] = {"size": int(population_size), "seed": 42}
            debug_messages: list[str] = []
            if has_mtf_operand and int(optimization_workers) > 1:
                workers = max(1, int(optimization_workers))
                backend = f"mtf_chunks ({workers} workers)"
                debug_messages.append("Optimization uses internal MTF chunk tracing instead of pygmo mp_bfe.")
            elif parallel_enabled and int(optimization_workers) > 1:
                workers = max(1, int(optimization_workers))
                try:
                    pg.mp_bfe.resize_pool(workers)
                    population_kwargs["b"] = pg.bfe(pg.mp_bfe())
                    backend = f"mp_bfe ({workers} workers)"
                except Exception as exc:
                    workers = 1
                    backend = "sequential"
                    debug_messages.append(f"Optimization parallel backend disabled: {exc}")

            progress_queue.put(
                {
                    "type": "bootstrap",
                    "initial_total": float(initial.total),
                    "compute_backend": backend,
                    "workers": workers,
                    "debug_messages": debug_messages,
                }
            )

            try:
                population = pg.population(problem, **population_kwargs)
            except Exception as exc:
                if "b" not in population_kwargs:
                    raise RuntimeError(f"failed to initialize population: {exc}") from exc
                debug_messages.append(f"Optimization population batch evaluator failed: {exc}")
                workers = 1
                backend = "sequential"
                progress_queue.put(
                    {
                        "type": "bootstrap",
                        "initial_total": float(initial.total),
                        "compute_backend": backend,
                        "workers": workers,
                        "debug_messages": [debug_messages[-1]],
                    }
                )
                population = pg.population(problem, size=int(population_size), seed=42)
            population.push_back(x0)

            for generation_done in range(int(generations_total)):
                if stop_event.is_set():
                    break
                algorithm = pg.algorithm(pg.de(gen=1, seed=42 + int(generation_done)))
                algorithm.set_verbosity(max(0, int(verbosity_every)))
                capture = io.StringIO()
                with redirect_stdout(capture), redirect_stderr(capture):
                    population = algorithm.evolve(population)
                logs = algorithm.extract(pg.de).get_log()
                payload = {
                    "type": "generation",
                    "generation_done": int(generation_done) + 1,
                    "debug": capture.getvalue(),
                    "champion_x": [float(value) for value in population.champion_x],
                }
                if logs:
                    gen, fevals, best, dx, df = logs[-1]
                    payload.update(
                        {
                            "log_gen": int(gen),
                            "log_fevals": int(fevals),
                            "log_best": float(best),
                            "log_dx": float(dx),
                            "log_df": float(df),
                            "verbosity_every": int(verbosity_every),
                            "generations_total": int(generations_total),
                        }
                    )
                progress_queue.put(payload)

            champion_x = [float(value) for value in population.champion_x]
            champion = evaluator.evaluate(variables, champion_x)
            progress_queue.put(
                {
                    "type": "complete",
                    "cancelled": bool(stop_event.is_set()),
                    "champion_x": champion_x,
                    "initial_total": float(initial.total),
                    "final_total": float(champion.total),
                    "compute_backend": backend,
                    "workers": workers,
                    "operands": _serialize_operand_results(champion.operands),
                }
            )
        finally:
            try:
                evaluator._shutdown_mtf_executor()
            except Exception:
                pass
    except Exception as exc:
        progress_queue.put(
            {
                "type": "error",
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
        )


class KrakenLayoutEditor(SourceModelingMixin, ToleranceModelingMixin, ScenePlacementMixin, GeometricAnalysisMixin, LayoutPolylineDisplayMixin, ParaxialToolsMixin, AnalysisReportsMixin, ThreeDSceneToolsMixin, tk.Tk):
    def __init__(self, *, headless: bool = False) -> None:
        super().__init__()
        self.headless = headless
        self.title("KrakenOS Layout Editor")
        self.geometry("1400x850")
        self.minsize(1100, 720)
        self.protocol("WM_DELETE_WINDOW", self.request_quit)
        if not self.headless:
            self.after(50, self._maximize_window)

        self.current_layout_file: Path | None = None
        self._last_saved_state: dict[str, object] | None = None
        self.metal_catalogs: list[dict[str, object]] = []
        self.layout_scene_source_specs: list[dict[str, object]] = []
        self.layout_scene_row_order: str = SOURCE_ROW_ORDER_DEFAULT
        self.layout_files: dict[str, Path] = {}
        self.layout_names: list[str] = []
        self.machine_vision_files: dict[str, Path] = {}
        self.machine_vision_names: list[str] = []
        self.example_files: dict[str, Path] = {}
        self.example_names: list[str] = []
        self.zemax_example_files: dict[str, Path] = {}
        self.rows: list[SurfaceRow] = []
        self.editor: tk.Widget | None = None
        self._editor_row_id: str | None = None
        self._editor_field: str | None = None
        self.popup_menu: tk.Menu | None = None
        self.current_menu_row_id: str | None = None
        self.current_menu_field: str | None = None
        self._text_popup_menu: tk.Menu | None = None
        self._surface_row_clipboard: list[dict[str, object]] = []
        self._formula_help_path: Path | None = None
        self._widget_tooltips: list[WidgetTooltip] = []
        self._menubar: tk.Menu | None = None
        self._edit_menu: tk.Menu | None = None
        self.insert_menu: tk.Menu | None = None
        self._insert_component_menu: tk.Menu | None = None
        self._undo_button: ttk.Button | None = None
        self._redo_button: ttk.Button | None = None
        self.layout_var = tk.StringVar(value="Common Optical Layout")
        self.machine_vision_var = tk.StringVar(value="Machine Vision Lens")
        self.example_var = tk.StringVar(value="Examples")
        self.arm_view_var = tk.StringVar(value=ARM_VIEW_DEFAULT)
        self.ray_display_mode_var = tk.StringVar(value=RAY_DISPLAY_DEFAULT)
        self.layout_menu: tk.Menu | None = None
        self._layout_category_menus: list[tk.Menu] = []
        self.machine_vision_menu: tk.Menu | None = None
        self.example_menu: tk.Menu | None = None
        self._example_category_menus: list[tk.Menu] = []
        self._zemax_example_category_menus: list[tk.Menu] = []
        self.layout_preview_mode = "none"
        self.trace_mode = "Auto"
        self.analysis_mode = "none"
        self.secondary_analysis_mode: str | None = None
        self.selected_analysis_modes: list[str] = []
        self.last_system = None
        self.last_rays = None
        self._last_preview_trace_signature = None
        self._last_preview_trace_backend = "none"
        self._last_preview_trace_note = ""
        self.show_path_labels = True
        self.optimization_running = False
        self.optimization_cancel_requested = False
        self.optimization_context: dict | None = None
        self.operand_weight_vars: dict[str, tk.StringVar] = {}
        self.operand_target_vars: dict[str, tk.StringVar] = {}
        self.operand_wavelength_vars: dict[str, tk.StringVar] = {}
        self.operand_field_vars: dict[str, tk.StringVar] = {}
        self.operand_field_x_vars: dict[str, tk.StringVar] = {}
        self.operand_field_y_vars: dict[str, tk.StringVar] = {}
        self.operand_surface_vars: dict[str, tk.StringVar] = {}
        self.operand_aperture_type_vars: dict[str, tk.StringVar] = {}
        self.operand_aperture_value_vars: dict[str, tk.StringVar] = {}
        self.operand_frequency_vars: dict[str, tk.StringVar] = {}
        self.operand_mtf_mode_vars: dict[str, tk.StringVar] = {}
        self.operand_mtf_algorithm_vars: dict[str, tk.StringVar] = {}
        self.operand_control_widgets: dict[str, dict[str, tuple[tk.Widget, ...]]] = {}
        self.operand_setup_frames: dict[str, tk.Widget] = {}
        self._spinner_phase = 0
        self._spinner_after_id: str | None = None
        self._refresh_after_id: str | None = None
        self._preview_field_ray_count = 1
        self._preview_field_bundle_count = 1
        self._active_cell: tuple[str, str] | None = None
        self._cell_border_parts: list[tk.Frame] = []
        self._grid_overlays: list[tk.Widget] = []
        self._grid_after_id: str | None = None
        self._active_cell_border_after_id: str | None = None
        self._table_selected_items: list[str] = []
        self._table_selection_after_id: str | None = None
        self._native_table_selection = None
        self._native_table_selection_set = None
        self._native_table_selection_remove = None
        self._table_visible_row_indices: list[int] = []
        self._table_iid_to_row_index: dict[str, int | None] = {}
        self._table_iid_to_scene_record: dict[str, object] = {}
        self._table_column_resize_active = False
        self._autosave_after_id: str | None = None
        self._initial_layout_passes = 0
        self._last_field_type = "Angle"
        self._field_defaults_initialized = False
        self._field_type_defaults = {
            "Angle": "0.0",
            "Object Height": "0.0",
            "Paraxial Image Height": "0.0",
            "Real Image Height": "0.0",
        }
        self._left_mode_controls: list[dict[str, object]] = []
        self._left_mode_saved_values: dict[str, str] = {}
        auto_save_default = os.getenv("KRAKEN_AUTO_SAVE_PLOT", "0").strip().lower() in {"1", "true", "yes", "on"}
        self.auto_save_plot_var = tk.BooleanVar(value=(auto_save_default and not self.headless))
        self.show_clipped_rays_var = tk.BooleanVar(value=True)
        self.show_path_labels_var = tk.BooleanVar(value=True)
        self.emit_full_ray_var = tk.BooleanVar(value=False)
        self.nonseq_energy_probability_var = tk.BooleanVar(value=False)
        self._last_analysis_label = "2D"
        self._last_analysis_workers = 1
        self._last_analysis_parallel_capable = False
        self._last_analysis_accelerator = "CPU"
        self._gpu_backend_reported = False
        self._analysis_executor: ProcessPoolExecutor | None = None
        self._analysis_executor_workers = 0
        self._analysis_executor_atexit = self._shutdown_analysis_executor
        atexit.register(self._analysis_executor_atexit)
        self._optimization_process = None
        self._optimization_queue = None
        self._optimization_stop_event = None
        self._last_optics_info: dict | None = None
        self._last_scene_bundle: SceneBundle | None = None
        self._preview_scene_trace_dirty = False
        self._last_auto_leg_entries: list[dict[str, object]] = []
        self._cardinal_marker_artists: list = []
        self._physical_distance_artists: list = []
        self._analysis_ax = None
        self._analysis_axes: list = []
        self._left_sidebar_collapsed = False
        self._right_sidebar_collapsed = False
        self._last_wavefront_fit_report = ""
        self._last_wavefront_samples: list[dict[str, object]] = []
        self._last_zernike_coefficients: list[dict[str, object]] = []
        self._zemax_wavefront_reference: ZemaxWavefrontMap | None = None
        self._last_zemax_wavefront_comparison: dict[str, object] | None = None
        self._hover_hint_artists: dict = {}
        self._hover_axis = None
        self._last_viewer_open_time = 0.0
        self._three_d_inspector: Kraken3DInspector | None = None
        self._ray_inspector_window: tk.Toplevel | None = None
        self._ray_inspector_summary_var: tk.StringVar | None = None
        self._ray_inspector_ray_table: ttk.Treeview | None = None
        self._ray_inspector_hit_table: ttk.Treeview | None = None
        self._ray_inspector_records: list[dict[str, object]] = []
        self._branch_gaussian_q_window: tk.Toplevel | None = None
        self._branch_gaussian_q_summary_var: tk.StringVar | None = None
        self._branch_gaussian_q_table: ttk.Treeview | None = None
        self._branch_gaussian_q_records: list[dict[str, object]] = []
        self._branch_gaussian_q_summary: dict[str, object] = {}
        self._branch_tree_window: tk.Toplevel | None = None
        self._branch_tree_summary_var: tk.StringVar | None = None
        self._branch_tree_table: ttk.Treeview | None = None
        self._branch_tree_hit_table: ttk.Treeview | None = None
        self._branch_tree_records: list[dict[str, object]] = []
        self._branch_throughput_window: tk.Toplevel | None = None
        self._branch_throughput_summary_var: tk.StringVar | None = None
        self._branch_throughput_filter_var: tk.StringVar | None = None
        self._branch_throughput_filter_menu: ttk.Combobox | None = None
        self._branch_throughput_table: ttk.Treeview | None = None
        self._branch_throughput_records: list[dict[str, object]] = []
        self._detector_aperture_window: tk.Toplevel | None = None
        self._detector_aperture_summary_var: tk.StringVar | None = None
        self._detector_aperture_table: ttk.Treeview | None = None
        self._detector_aperture_records: list[dict[str, object]] = []
        self._source_illumination_window: tk.Toplevel | None = None
        self._source_illumination_summary_var: tk.StringVar | None = None
        self._source_illumination_target_var: tk.StringVar | None = None
        self._source_illumination_target_menu: ttk.Combobox | None = None
        self._source_illumination_table: ttk.Treeview | None = None
        self._source_illumination_detail_text: tk.Text | None = None
        self._source_illumination_records: list[dict[str, object]] = []
        self._last_tolerance_monte_carlo_records: list[dict[str, object]] = []
        self._last_tolerance_monte_carlo_summary: dict[str, object] = {}
        self._last_tolerance_comparison_records: list[dict[str, object]] = []
        self._last_tolerance_comparison_summary: dict[str, object] = {}
        self._last_tolerance_stackup_records: list[dict[str, object]] = []
        self._last_tolerance_stackup_summary: dict[str, object] = {}
        self._last_tolerance_compensator_records: list[dict[str, object]] = []
        self._last_tolerance_compensator_summary: dict[str, object] = {}
        self._last_tolerance_multi_compensator_records: list[dict[str, object]] = []
        self._last_tolerance_multi_compensator_summary: dict[str, object] = {}
        self._last_tolerance_spot_overlay: dict[str, object] = {}
        self._last_tolerance_mtf_overlay: dict[str, object] = {}
        self._last_tolerance_wavefront_overlay: dict[str, object] = {}
        self.tolerance_solve_presets: list[dict[str, object]] = []
        self.tolerance_manufacturing_templates: list[dict[str, object]] = []
        self.active_tolerance_solve_preset_name = ""
        self._nonseq_scene_window: tk.Toplevel | None = None
        self._nonseq_scene_summary_var: tk.StringVar | None = None
        self._nonseq_scene_table: ttk.Treeview | None = None
        self._nonseq_scene_records: list[dict[str, object]] = []
        self._legacy_3d_plotter = None
        self._legacy_3d_after_id = None
        self.imported_camera_step_path: Path | None = None
        self.imported_lens_step_path: Path | None = None
        self.imported_optical_step_path: Path | None = None
        self.imported_led_step_path: Path | None = None
        self._live_step_overlay_trace_plan_cache: dict[object, dict[str, object]] = {}
        self.lens_step_largest_component_only = True
        self.camera_step_rotation_x_deg = 0.0
        self.lens_step_rotation_x_deg = 0.0
        self.optical_step_rotation_x_deg = 0.0
        self.led_step_rotation_x_deg = 0.0
        self.camera_step_rotation_y_deg = 0.0
        self.lens_step_rotation_y_deg = 0.0
        self.optical_step_rotation_y_deg = 0.0
        self.led_step_rotation_y_deg = 0.0
        self.camera_step_rotation_z_deg = 0.0
        self.lens_step_rotation_z_deg = 0.0
        self.optical_step_rotation_z_deg = 0.0
        self.led_step_rotation_z_deg = 0.0
        self.led_object_edge_distance_mm = 0.0
        self.led_step_object_edge_local_z: float | None = None
        self.lens_step_axis_offset_xy = (0.0, 0.0)
        self.optical_step_axis_offset_xy = (0.0, 0.0)
        self.camera_step_axis_offset_xy = (0.0, 0.0)
        self.led_step_axis_offset_xy = (0.0, 0.0)
        self.lens_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.optical_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.camera_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.led_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self._cad_axis_pick_label: str | None = None
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._selected_step_label: str | None = None
        self._layout_pick_regions: dict[int, np.ndarray] = {}
        self._layout_ray_pick_regions: list[tuple[int, np.ndarray]] = []
        self._layout_projected_rays_by_index: dict[int, ProjectedRay2D] = {}
        self._layout_selected_ray_index: int | None = None
        self._layout_selection_artists: list = []
        self._last_plot_hover_message = ""
        self._external_cad_mesh_cache: dict[str, pv.DataSet] = {}
        self._external_cad_reference_cache: dict[str, dict[str, object]] = {}
        self._external_cad_section_cache: dict[str, dict[str, object]] = {}
        self._undo_stack: list[dict[str, object]] = []
        self._redo_stack: list[dict[str, object]] = []
        self._history_pending_state: dict[str, object] | None = None
        self._history_restoring = False
        self._history_limit = 80

        self._build_menu()
        self._build_ui()
        self._bind_global_copy_shortcuts()
        self.bind_all("<Control-z>", self._undo_event, add="+")
        self.bind_all("<Control-y>", self._redo_event, add="+")
        self.bind_all("<Control-Shift-Z>", self._redo_event, add="+")
        self._reset_debug_log()
        self.load_layouts()
        self.load_examples()
        # Start in the same fast reset state as the Reset button: Object +
        # Image only, no system build, no ray trace.
        self._load_reset_system()
        if not self.headless:
            self._clear_preview_after_reset()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._history_pending_state = None
        self._mark_saved_state()
        self._update_undo_redo_buttons()
        # Backend probing imports Torch/CuPy and may initialise CUDA; do it lazily.

    def _maximize_window(self) -> None:
        # Prefer maximize/zoom over fullscreen so copy/paste and WM behavior remain normal.
        try:
            self.state("zoomed")
            return
        except Exception:
            pass
        try:
            self.attributes("-zoomed", True)
            return
        except Exception:
            pass
        try:
            width = max(1200, int(self.winfo_screenwidth() * 0.96))
            height = max(800, int(self.winfo_screenheight() * 0.95))
            self.geometry(f"{width}x{height}+0+0")
        except Exception:
            pass

    def _main_window_builder(self) -> MainWindowBuilder:
        builder = self.__dict__.get("_main_window_builder_instance")
        if builder is None:
            builder = MainWindowBuilder(self)
            self._main_window_builder_instance = builder
        return builder

    def _build_menu(self) -> None:
        self._main_window_builder()._build_menu()

    def _build_ui(self) -> None:
        self._main_window_builder()._build_ui()

    def _add_widget_tooltip(self, widget: tk.Widget, text: str) -> tk.Widget:
        self._widget_tooltips.append(WidgetTooltip(widget, text))
        return widget

    def _cancel_after_callback_attr(self, attr_name: str) -> None:
        after_id = self.__dict__.get(attr_name)
        if after_id is None:
            return
        self.__dict__[attr_name] = None
        try:
            self.after_cancel(after_id)
        except Exception:
            pass

    def destroy(self) -> None:
        for attr_name in (
            "_active_cell_border_after_id",
            "_grid_after_id",
            "_table_selection_after_id",
            "_autosave_after_id",
            "_refresh_after_id",
            "_spinner_after_id",
            "_legacy_3d_after_id",
        ):
            self._cancel_after_callback_attr(attr_name)
        try:
            self.update_idletasks()
        except Exception:
            pass
        if self._three_d_inspector is not None:
            try:
                self._three_d_inspector.destroy()
            except Exception:
                pass
            self._three_d_inspector = None
        if self._ray_inspector_window is not None:
            try:
                self._ray_inspector_window.destroy()
            except Exception:
                pass
            self._ray_inspector_window = None
        if self._branch_gaussian_q_window is not None:
            try:
                self._branch_gaussian_q_window.destroy()
            except Exception:
                pass
            self._branch_gaussian_q_window = None
        if self._branch_tree_window is not None:
            try:
                self._branch_tree_window.destroy()
            except Exception:
                pass
            self._branch_tree_window = None
        if self._branch_throughput_window is not None:
            try:
                self._branch_throughput_window.destroy()
            except Exception:
                pass
            self._branch_throughput_window = None
        if self._detector_aperture_window is not None:
            try:
                self._detector_aperture_window.destroy()
            except Exception:
                pass
            self._detector_aperture_window = None
        if self._nonseq_scene_window is not None:
            try:
                self._nonseq_scene_window.destroy()
            except Exception:
                pass
            self._nonseq_scene_window = None
        self._close_atmosphere_settings_dialog()
        self._close_legacy_3d_plotter()
        analysis_executor_atexit = self.__dict__.get("_analysis_executor_atexit")
        if analysis_executor_atexit is not None:
            try:
                atexit.unregister(analysis_executor_atexit)
            except Exception:
                pass
            self._analysis_executor_atexit = None
        self._shutdown_analysis_executor()
        self._shutdown_optimization_worker(force=True)
        super().destroy()

    def request_quit(self) -> None:
        if self.headless or self._confirm_close_with_optional_save():
            self.destroy()

    def _confirm_close_with_optional_save(self) -> bool:
        if not self._layout_has_unsaved_changes():
            return True
        choice = messagebox.askyesnocancel(
            "Save layout before quitting?",
            "The current KrakenOS layout has unsaved changes.\n\nSave before quitting?",
            parent=self,
        )
        if choice is None:
            return False
        if choice is False:
            return True
        try:
            return bool(self.save_layout())
        except Exception as exc:
            messagebox.showerror(
                "Save failed",
                f"The layout could not be saved:\n\n{_short_error_message(exc)}",
                parent=self,
            )
            return False

    def _capture_saved_layout_state(self) -> dict[str, object]:
        return {
            "rows": [asdict(row) for row in self.rows],
            "settings": self._collect_layout_settings(),
        }

    def _mark_saved_state(self) -> None:
        self._last_saved_state = self._capture_saved_layout_state()

    def _layout_has_unsaved_changes(self) -> bool:
        self._commit_pending_table_edit()
        self._commit_history_capture()
        if self._last_saved_state is None:
            return bool(self.rows)
        return self._capture_saved_layout_state() != self._last_saved_state

    def _optical_stl_solid_row(
        self,
        path: Path,
        *,
        source_path: Path | None = None,
        source_format: str = "STL",
    ) -> SurfaceRow:
        display_path = Path(source_path) if source_path is not None else Path(path)
        stem = display_path.stem.replace("_", " ").strip() or "Optical solid"
        source_label = str(source_format).upper() if source_format else "STL"
        source_note = (
            f" Original {source_label} CAD source: {source_path}."
            if source_path is not None
            else ""
        )
        note = (
            "Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in "
            "non-sequential scene mode; STEP/IGES sources are meshed to a cached STL. "
            "Use Material, Thickness, Tilt, and Decenter to align the closed mesh "
            f"in millimetres.{source_note}"
        )
        advanced = {
            "Solid_3d_stl": str(path),
            "Note": note,
        }
        if source_path is not None:
            advanced["OpticalSolidSourcePath"] = str(source_path)
            advanced["OpticalSolidSourceFormat"] = source_label
        default_metadata = self._default_uncoated_optical_solid_face_metadata(path)
        if default_metadata is not None:
            advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = default_metadata
        return SurfaceRow(
            surface="Standard",
            element=f"Solid {stem}",
            name=f"Optical solid: {stem}",
            glass="BK7",
            thickness=40.0,
            diameter=25.0,
            axis_move=0.0,
            advanced=advanced,
        )

    @staticmethod
    def _default_uncoated_optical_solid_face_metadata(
        path: Path,
        existing: object | None = None,
    ) -> dict[str, object] | None:
        try:
            candidates = cluster_optical_solid_planar_faces(Path(path))
        except Exception:
            return None
        if not candidates:
            return None
        metadata = normalize_optical_solid_face_metadata(existing or {}, candidates, source_stl=str(path))
        faces: list[dict[str, object]] = []
        for face in list(metadata.get("faces", []) or []):
            if not isinstance(face, dict):
                continue
            record = normalize_optical_solid_face_record(face)
            source = str(record.get("assignment_source", "") or "").strip()
            function = _normalize_optical_solid_face_function(record.get("function"), legacy_role=record.get("role"))
            if source == OPTICAL_SOLID_FACE_ASSIGNMENT_MANUAL:
                faces.append(record)
                continue
            if function == OPTICAL_SOLID_FACE_FUNCTION_DEFAULT or source == OPTICAL_SOLID_FACE_ASSIGNMENT_DEFAULT_UNCOATED:
                record["function"] = OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT
                record["role"] = _legacy_role_from_optical_solid_face_function(OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT)
                record["port_role"] = OPTICAL_SOLID_FACE_PORT_INTERACTION
                record["assignment_source"] = OPTICAL_SOLID_FACE_ASSIGNMENT_DEFAULT_UNCOATED
            faces.append(record)
        return normalize_optical_solid_face_metadata(
            {
                "faces": faces,
                "virtual_planes": metadata.get("virtual_planes", []),
                "source_stl": str(path),
            },
            source_stl=str(path),
        )

    def import_optical_stl_solid(self) -> None:
        initial_dir = ATTACHMENT_DIR if ATTACHMENT_DIR.exists() else EXAMPLES_DIR if EXAMPLES_DIR.exists() else PROJECT_ROOT
        path_text = filedialog.askopenfilename(
            title="Import Optical CAD/STL Solid",
            initialdir=str(initial_dir),
            filetypes=OPTICAL_SOLID_FILETYPES,
            parent=self,
        )
        if not path_text:
            return
        source_path = Path(path_text).expanduser()
        try:
            mesh_path, cad_source_path, source_format = _optical_solid_mesh_path_from_source(source_path)
        except Exception as exc:
            messagebox.showerror("Import Optical CAD/STL Solid", f"Could not prepare optical solid:\n\n{exc}", parent=self)
            return
        diagnostics = inspect_stl_mesh(mesh_path)
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Import Optical CAD/STL Solid", f"Could not read the surface table:\n\n{exc}", parent=self)
            return

        selected_indices = self._selected_table_indices()
        arm_key = self._current_arm_view_key()
        if selected_indices:
            insert_at = max(selected_indices) + 1
        elif arm_key:
            insert_at = self._default_insert_index_for_arm_key(arm_key)
        else:
            insert_at = len(self.rows)
            if self.rows and self.rows[-1].surface == "Image":
                insert_at -= 1
        insert_at = max(1, min(insert_at, len(self.rows) - (1 if self.rows and self.rows[-1].surface == "Image" else 0)))

        row = self._optical_stl_solid_row(
            mesh_path.resolve(),
            source_path=cad_source_path.resolve() if cad_source_path is not None else None,
            source_format=source_format,
        )
        if arm_key:
            self._apply_arm_key_metadata_to_row(row, arm_key)
        self._begin_history_capture()
        self.rows.insert(insert_at, row)
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices([insert_at], focus_index=insert_at)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(
            f"Imported optical solid {source_path.name} at S{insert_at}; {short_stl_mesh_diagnostics(diagnostics)}. Click Update."
        )
        report_text = f"S{insert_at}: {row.name}\n{format_stl_mesh_diagnostics(diagnostics)}"
        if cad_source_path is not None:
            report_text += f"\n\nOriginal CAD source: {cad_source_path}\nCached STL mesh: {mesh_path}"
        self.append_debug(report_text)
        if diagnostics.errors or diagnostics.warnings:
            self.status_var.set(
                f"Imported {source_path.name} at S{insert_at}; mesh diagnostics need review ({short_stl_mesh_diagnostics(diagnostics)})."
            )
        else:
            self.status_var.set(
                f"Imported {source_path.name} at S{insert_at}. Opening CAD/STL face assignment."
            )
        self.after(120, lambda idx=insert_at: self.open_optical_solid_face_role_editor(idx))

    def convert_row_to_optical_stl_solid(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        if self.rows[row_index].surface in {"Object", "Image"}:
            messagebox.showinfo("Optical CAD/STL Solid", "Object/Image rows cannot be converted to optical CAD/STL solids.", parent=self)
            return
        initial_dir = ATTACHMENT_DIR if ATTACHMENT_DIR.exists() else EXAMPLES_DIR if EXAMPLES_DIR.exists() else PROJECT_ROOT
        path_text = filedialog.askopenfilename(
            title="Convert Row to Optical CAD/STL Solid",
            initialdir=str(initial_dir),
            filetypes=OPTICAL_SOLID_FILETYPES,
            parent=self,
        )
        if not path_text:
            return
        source_path = Path(path_text).expanduser()
        try:
            mesh_path, cad_source_path, source_format = _optical_solid_mesh_path_from_source(source_path)
        except Exception as exc:
            messagebox.showerror("Optical CAD/STL Solid", f"Could not prepare optical solid:\n\n{exc}", parent=self)
            return
        diagnostics = inspect_stl_mesh(mesh_path)
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Optical CAD/STL Solid", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        previous = self.rows[row_index]
        replacement = self._optical_stl_solid_row(
            mesh_path.resolve(),
            source_path=cad_source_path.resolve() if cad_source_path is not None else None,
            source_format=source_format,
        )
        replacement.element = previous.element or replacement.element
        replacement.thickness = max(float(previous.thickness), replacement.thickness)
        replacement.diameter = max(float(previous.diameter), replacement.diameter)
        replacement.tilt_x = float(previous.tilt_x)
        replacement.tilt_y = float(previous.tilt_y)
        replacement.tilt_z = float(previous.tilt_z)
        replacement.desp_x = float(previous.desp_x)
        replacement.desp_y = float(previous.desp_y)
        replacement.desp_z = float(previous.desp_z)
        self._begin_history_capture()
        self.rows[row_index] = replacement
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_row(row_index)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        report_text = f"S{row_index}: {replacement.name}\n{format_stl_mesh_diagnostics(diagnostics)}"
        if cad_source_path is not None:
            report_text += f"\n\nOriginal CAD source: {cad_source_path}\nCached STL mesh: {mesh_path}"
        self.append_debug(report_text)
        self.status_var.set(
            f"Converted S{row_index} to optical solid {source_path.name}; opening CAD/STL face assignment."
        )
        self.after(120, lambda idx=row_index: self.open_optical_solid_face_role_editor(idx))

    def _stl_path_from_row(self, row: SurfaceRow) -> Path | None:
        advanced = row.advanced or {}
        if not isinstance(advanced, dict):
            return None
        value = advanced.get("Solid_3d_stl")
        if not self._scene_graph_value_present(value):
            return None
        if isinstance(value, (str, Path)):
            text = str(value).strip()
            if text and text.lower() != "none":
                return Path(text).expanduser()
        return None

    def _main_optical_solid_dialogs(self) -> MainOpticalSolidDialogs:
        dialog = self.__dict__.get("_main_optical_solid_dialogs_instance")
        if dialog is None:
            dialog = MainOpticalSolidDialogs(
                self,
                short_error_message=_short_error_message,
                axis_to_layout_z_tilts=STL_AXIS_TO_LAYOUT_Z_TILTS,
            )
            self._main_optical_solid_dialogs_instance = dialog
        return dialog

    def _optical_stl_diagnostics_text(self) -> str:
        return self._main_optical_solid_dialogs()._optical_stl_diagnostics_text()

    def open_optical_stl_diagnostics(self) -> None:
        self._main_optical_solid_dialogs().open_optical_stl_diagnostics()

    @staticmethod
    def _optical_solid_faces_summary(row_index: int, row: SurfaceRow) -> str:
        metadata = normalize_optical_solid_face_metadata((row.advanced or {}).get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))
        return optical_solid_metadata.optical_solid_faces_summary_text(row_index, row.name, row.surface, metadata)

    def _main_optical_solid_face_roles_dialog(self) -> MainOpticalSolidFaceRolesDialog:
        dialog = self.__dict__.get("_main_optical_solid_face_roles_dialog_instance")
        if dialog is None:
            dialog = MainOpticalSolidFaceRolesDialog(self)
            self._main_optical_solid_face_roles_dialog_instance = dialog
        return dialog

    def _open_optical_solid_faces_for_row(self, row_index: int, row: SurfaceRow, path: Path) -> None:
        self._main_optical_solid_face_roles_dialog()._open_optical_solid_faces_for_row(row_index, row, path)

    def open_optical_solid_face_role_editor(self, row_index: int | None = None) -> None:
        title = "Assign CAD/STL Optical Faces"
        if row_index is None:
            selected = self._selected_file_backed_stl_row(title)
            if selected is None:
                return
            row_index, row, path = selected
        else:
            self._commit_pending_table_edit()
            try:
                self._read_rows_from_table()
            except Exception as exc:
                messagebox.showerror(title, f"Could not read the surface table:\n\n{exc}", parent=self)
                return
            item = self._file_backed_stl_row_at(row_index)
            if item is None:
                messagebox.showinfo(title, "The selected row does not contain a file-backed Solid_3d_stl value.", parent=self)
                return
            row, path = item
        self._open_optical_solid_faces_for_row(int(row_index), row, path)

    def _selected_file_backed_stl_row(self, title: str) -> tuple[int, SurfaceRow, Path] | None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror(title, f"Could not read the surface table:\n\n{exc}", parent=self)
            return None
        row_index = self._selected_surface_row_index()
        if row_index is None or row_index < 0 or row_index >= len(self.rows):
            messagebox.showinfo(title, "Select an STL solid row first.", parent=self)
            return None
        row = self.rows[row_index]
        path = self._stl_path_from_row(row)
        if path is None:
            messagebox.showinfo(title, "The selected row does not contain a file-backed Solid_3d_stl value.", parent=self)
            return None
        if not path.exists():
            messagebox.showerror(title, f"STL file does not exist:\n\n{path}", parent=self)
            return None
        return row_index, row, path

    def _file_backed_stl_row_at(self, row_index: int) -> tuple[SurfaceRow, Path] | None:
        try:
            row_index = int(row_index)
        except Exception:
            return None
        if not (0 <= row_index < len(self.rows)):
            return None
        row = self.rows[row_index]
        path = self._stl_path_from_row(row)
        if path is None or not path.exists():
            return None
        return row, path

    def _optical_solid_face_metadata_for_row(self, row_index: int) -> tuple[SurfaceRow, Path, dict[str, object]]:
        item = self._file_backed_stl_row_at(int(row_index))
        if item is None:
            raise RuntimeError(f"S{int(row_index)} is not a file-backed optical CAD/STL solid.")
        row, path = item
        candidates = cluster_optical_solid_planar_faces(path)
        if not candidates:
            raise RuntimeError(f"S{int(row_index)} has no planar CAD/STL face candidates.")
        metadata = normalize_optical_solid_face_metadata(
            (row.advanced or {}).get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}),
            candidates,
            source_stl=str(path),
        )
        return row, path, metadata

    def optical_solid_face_record_at_world_point(
        self,
        row_index: int,
        point_world,
        *,
        normal_world=None,
        assigned_only: bool = False,
    ) -> dict[str, object] | None:
        row, _path, metadata = self._optical_solid_face_metadata_for_row(int(row_index))
        temp_row = SurfaceRow(**asdict(row))
        temp_row.advanced = dict(temp_row.advanced or {})
        temp_row.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata
        faces = optical_solid_face_world_records(
            temp_row,
            self._stl_row_z_station(int(row_index)),
            assigned_only=bool(assigned_only),
        )
        return match_optical_solid_world_face(faces, point_world, normal_world)

    @staticmethod
    def _optical_solid_face_record_for_triangle_index(
        faces: list[dict[str, object]],
        triangle_index: int,
    ) -> dict[str, object] | None:
        try:
            triangle_index = int(triangle_index)
        except Exception:
            return None
        if triangle_index < 0:
            return None
        for face in list(faces or []):
            if not isinstance(face, dict):
                continue
            try:
                triangle_indices = optical_solid_metadata.nonnegative_int_list(
                    face.get("triangle_indices", face.get("cell_indices"))
                )
            except Exception:
                triangle_indices = []
            if triangle_index in set(int(value) for value in triangle_indices):
                return dict(face)
        return None

    def _optical_solid_face_records_for_temp_row(
        self,
        row: SurfaceRow,
        row_index: int,
        metadata: dict[str, object],
    ) -> list[dict[str, object]]:
        temp_row = SurfaceRow(**asdict(row))
        temp_row.advanced = dict(temp_row.advanced or {})
        temp_row.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata
        z_station = float(
            sum(
                float(getattr(existing_row, "thickness", 0.0) or 0.0)
                for existing_row in self.rows[: max(int(row_index), 0)]
            )
        )
        return optical_solid_face_world_records(
            temp_row,
            z_station,
            assigned_only=False,
        )

    def optical_solid_face_record_for_mesh_cell(
        self,
        row_index: int,
        cell_id: int,
    ) -> dict[str, object] | None:
        row, _path, metadata = self._optical_solid_face_metadata_for_row(int(row_index))
        faces = self._optical_solid_face_records_for_temp_row(row, int(row_index), metadata)
        return self._optical_solid_face_record_for_triangle_index(faces, int(cell_id))

    def optical_solid_step_overlay_face_record_at_world_point(
        self,
        label: str,
        point_world,
        *,
        normal_world=None,
        cell_id: int = -1,
    ) -> dict[str, object] | None:
        plan = self._step_overlay_optical_solid_row_plan(
            label,
            use_current_selection=False,
            quiet=True,
        )
        if plan is None:
            return None
        row = plan.get("row")
        if not isinstance(row, SurfaceRow):
            return None
        try:
            row_index = int(plan.get("row_index", 0))
        except Exception:
            row_index = 0
        metadata = normalize_optical_solid_face_metadata(
            (row.advanced or {}).get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
        )
        faces = self._optical_solid_face_records_for_temp_row(row, row_index, metadata)
        face = self._optical_solid_face_record_for_triangle_index(faces, int(cell_id))
        if face is not None:
            return face
        return match_optical_solid_world_face(faces, point_world, normal_world)

    def _default_port_role_for_face_function(self, function: str, existing: object = OPTICAL_SOLID_FACE_PORT_DEFAULT) -> str:
        existing_role = _normalize_optical_solid_face_port_role(existing)
        normalized = _normalize_optical_solid_face_function(function)
        if normalized == OPTICAL_SOLID_FACE_FUNCTION_DEFAULT:
            return OPTICAL_SOLID_FACE_PORT_DEFAULT
        if existing_role in {OPTICAL_SOLID_FACE_PORT_INPUT, OPTICAL_SOLID_FACE_PORT_OUTPUT}:
            return existing_role
        if normalized in {"Mirror", "Beam Splitter", "Absorber/Mechanical"}:
            return OPTICAL_SOLID_FACE_PORT_INTERACTION
        return OPTICAL_SOLID_FACE_PORT_DEFAULT

    def _direct_context_port_role_for_face_function(self, function: str, existing: object = OPTICAL_SOLID_FACE_PORT_DEFAULT) -> str:
        existing_role = _normalize_optical_solid_face_port_role(existing)
        normalized = _normalize_optical_solid_face_function(function)
        if normalized == OPTICAL_SOLID_FACE_FUNCTION_DEFAULT:
            return OPTICAL_SOLID_FACE_PORT_DEFAULT
        if existing_role == OPTICAL_SOLID_FACE_PORT_INPUT:
            return OPTICAL_SOLID_FACE_PORT_INPUT
        if normalized in {
            OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
            "TIR",
            "Mirror",
            "Beam Splitter",
            "Absorber/Mechanical",
        }:
            return OPTICAL_SOLID_FACE_PORT_INTERACTION
        return OPTICAL_SOLID_FACE_PORT_DEFAULT

    def assign_optical_solid_face_function(
        self,
        row_index: int,
        face_id: str,
        function_label: str,
        *,
        port_role: str | None = None,
        direct_context: bool = False,
    ) -> dict[str, object]:
        row_index = int(row_index)
        face_id = str(face_id or "").strip()
        if not face_id:
            raise RuntimeError("No CAD/STL face ID was selected.")
        row, path, metadata = self._optical_solid_face_metadata_for_row(row_index)
        function = _optical_solid_face_function_from_ui_value(function_label)
        role = _legacy_role_from_optical_solid_face_function(function)
        normalized_faces = [
            normalize_optical_solid_face_record(face)
            for face in list(metadata.get("faces", []) or [])
            if isinstance(face, dict)
        ]
        target_record = next(
            (
                record
                for record in normalized_faces
                if str(record.get("face_id", "") or "").strip() == face_id
            ),
            None,
        )
        if target_record is None:
            raise RuntimeError(f"CAD/STL face {face_id} is not available on S{row_index}.")
        extent_mm = _optical_solid_face_metadata_extent(normalized_faces, row)
        updated_faces: list[dict[str, object]] = []
        matched: dict[str, object] | None = None
        related_face_ids: list[str] = []
        for face in list(metadata.get("faces", []) or []):
            if not isinstance(face, dict):
                continue
            record = normalize_optical_solid_face_record(face)
            record_face_id = str(record.get("face_id", "") or "").strip()
            same_physical_face = (
                record_face_id == face_id
                or _optical_solid_face_records_share_plane(record, target_record, extent_mm=extent_mm)
            )
            if same_physical_face:
                record["function"] = function
                record["role"] = role
                record["port_role"] = (
                    _normalize_optical_solid_face_port_role(port_role)
                    if port_role is not None
                    else (
                        self._direct_context_port_role_for_face_function(function, record.get("port_role"))
                        if direct_context
                        else self._default_port_role_for_face_function(function, record.get("port_role"))
                    )
                )
                record["assignment_source"] = OPTICAL_SOLID_FACE_ASSIGNMENT_MANUAL
                updated = normalize_optical_solid_face_record(record)
                if record_face_id == face_id:
                    matched = updated
                elif record_face_id:
                    related_face_ids.append(record_face_id)
                record = updated
            updated_faces.append(record)
        metadata_to_save = normalize_optical_solid_face_metadata(
            {"faces": updated_faces, "virtual_planes": metadata.get("virtual_planes", []), "source_stl": str(path)},
            source_stl=str(path),
        )
        self._begin_history_capture()
        target = self.rows[row_index]
        target.advanced = dict(target.advanced or {})
        target.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata_to_save
        self._sync_table()
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self._invalidate_optical_solid_face_assignment_trace(row_index, face_id, function)
        display = _optical_solid_face_function_display(function)
        summary = self._optical_solid_faces_summary(row_index, target)
        if related_face_ids:
            summary += "\n" + (
                f"Direct Open 3D assignment also updated coplanar face records: "
                f"{', '.join(related_face_ids)}"
            )
        self.append_debug(summary)
        related_suffix = f" (+{len(related_face_ids)} coplanar)" if related_face_ids else ""
        self.status_var.set(f"S{row_index} {face_id}: set CAD/STL face function to {display}{related_suffix}.")
        return {
            "row_index": row_index,
            "face_id": face_id,
            "function": function,
            "function_display": display,
            "port_role": matched.get("port_role", OPTICAL_SOLID_FACE_PORT_DEFAULT),
            "related_face_ids": tuple(related_face_ids),
            "metadata": metadata_to_save,
        }

    def assign_optical_solid_face_function_at_world_point(
        self,
        row_index: int,
        point_world,
        function_label: str,
        *,
        normal_world=None,
        port_role: str | None = None,
        direct_context: bool = False,
    ) -> dict[str, object]:
        face = self.optical_solid_face_record_at_world_point(
            int(row_index),
            point_world,
            normal_world=normal_world,
            assigned_only=False,
        )
        if face is None:
            raise RuntimeError(f"Could not match the picked point to a CAD/STL face on S{int(row_index)}.")
        face_id = str(face.get("face_id", "") or "").strip()
        result = self.assign_optical_solid_face_function(
            int(row_index),
            face_id,
            function_label,
            port_role=port_role,
            direct_context=direct_context,
        )
        result["matched_face"] = face
        return result

    def _stl_row_z_station(self, row_index: int) -> float:
        z_positions = self._row_z_positions()
        if 0 <= int(row_index) < len(z_positions):
            return float(z_positions[int(row_index)])
        return 0.0

    def _apply_stl_row_pose(
        self,
        row_index: int,
        *,
        tilts: tuple[float, float, float] | None = None,
        desp: tuple[float, float, float] | None = None,
        action: str,
    ) -> None:
        selected = self._file_backed_stl_row_at(row_index)
        if selected is None:
            raise RuntimeError("Selected row is not a file-backed optical STL solid")
        row, _path = selected
        self._begin_history_capture()
        if tilts is not None:
            row.tilt_x, row.tilt_y, row.tilt_z = (float(value) for value in tilts)
        if desp is not None:
            row.desp_x, row.desp_y, row.desp_z = (float(value) for value in desp)
        self._sync_table()
        self._select_table_row(int(row_index))
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.append_debug(
            "STL 3D placement {action} S{idx}: Tilt=({tx:.6g},{ty:.6g},{tz:.6g}) "
            "Desp=({dx:.6g},{dy:.6g},{dz:.6g})".format(
                action=action,
                idx=int(row_index),
                tx=float(row.tilt_x),
                ty=float(row.tilt_y),
                tz=float(row.tilt_z),
                dx=float(row.desp_x),
                dy=float(row.desp_y),
                dz=float(row.desp_z),
            )
        )

    def apply_stl_axis_fit(self, row_index: int, axis: str) -> None:
        selected = self._file_backed_stl_row_at(row_index)
        if selected is None:
            raise RuntimeError("Selected row is not a file-backed optical STL solid")
        _row, path = selected
        axis = str(axis or "+Z").strip()
        tilts = STL_AXIS_TO_LAYOUT_Z_TILTS.get(axis, STL_AXIS_TO_LAYOUT_Z_TILTS["+Z"])
        bounds_min, _bounds_max, center = rotated_stl_bounds(path, tilts)
        desp = (-float(center[0]), -float(center[1]), -float(bounds_min[2]))
        self._apply_stl_row_pose(row_index, tilts=tilts, desp=desp, action=f"fit {axis}->+Z")

    def rotate_stl_row_pose(self, row_index: int, axis: str, delta_deg: float) -> None:
        selected = self._file_backed_stl_row_at(row_index)
        if selected is None:
            raise RuntimeError("Selected row is not a file-backed optical STL solid")
        row, _path = selected
        tilts = [float(row.tilt_x), float(row.tilt_y), float(row.tilt_z)]
        axis_index = {"x": 0, "y": 1, "z": 2}.get(str(axis).strip().lower())
        if axis_index is None:
            raise RuntimeError(f"Unknown STL rotation axis: {axis}")
        tilts[axis_index] += float(delta_deg)
        self._apply_stl_row_pose(row_index, tilts=tuple(tilts), action=f"rotate {axis.upper()} {float(delta_deg):+.0f} deg")

    def center_stl_row_xy(self, row_index: int) -> None:
        selected = self._file_backed_stl_row_at(row_index)
        if selected is None:
            raise RuntimeError("Selected row is not a file-backed optical STL solid")
        row, path = selected
        tilts = (float(row.tilt_x), float(row.tilt_y), float(row.tilt_z))
        _bounds_min, _bounds_max, center = rotated_stl_bounds(path, tilts)
        desp = (-float(center[0]), -float(center[1]), float(row.desp_z))
        self._apply_stl_row_pose(row_index, desp=desp, action="center X/Y")

    def place_stl_row_front_on_station(self, row_index: int) -> None:
        selected = self._file_backed_stl_row_at(row_index)
        if selected is None:
            raise RuntimeError("Selected row is not a file-backed optical STL solid")
        row, path = selected
        tilts = (float(row.tilt_x), float(row.tilt_y), float(row.tilt_z))
        bounds_min, _bounds_max, _center = rotated_stl_bounds(path, tilts)
        desp = (float(row.desp_x), float(row.desp_y), -float(bounds_min[2]))
        self._apply_stl_row_pose(row_index, desp=desp, action="front on row")

    def translate_scene_row_pose(self, row_index: int, axis: str, delta_mm: float) -> dict[str, object]:
        try:
            row_index = int(row_index)
        except Exception as exc:
            raise RuntimeError("Invalid row index for 3D placement translation") from exc
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError("3D placement translation row is outside the table")
        axis_key = str(axis or "").strip().lower()
        attr = {"x": "desp_x", "y": "desp_y", "z": "desp_z"}.get(axis_key)
        if attr is None:
            raise RuntimeError(f"Unknown 3D placement translation axis: {axis}")
        try:
            delta = float(delta_mm)
        except Exception as exc:
            raise RuntimeError("Invalid 3D placement translation step") from exc
        if not np.isfinite(delta) or abs(delta) <= 1e-12:
            raise RuntimeError("3D placement translation step is zero or non-finite")
        row = self.rows[row_index]
        before = float(getattr(row, attr))
        history_started = False
        if "_history_restoring" in self.__dict__ and "_history_pending_state" in self.__dict__:
            try:
                self._begin_history_capture()
                history_started = True
            except Exception:
                history_started = False
        setattr(row, attr, before + delta)
        row.advanced = dict(row.advanced or {})
        settings = normalize_scene_placement_settings(row.advanced.get(SCENE_PLACEMENT_ADVANCED_ATTR, {}))
        settings["last_translate_axis"] = axis_key
        settings["last_translate_delta_mm"] = float(delta)
        settings["last_translate_step_mm"] = abs(float(delta))
        row.advanced[SCENE_PLACEMENT_ADVANCED_ATTR] = settings
        if "table" in self.__dict__:
            try:
                self._sync_table()
                self._select_table_row(row_index)
            except Exception:
                pass
        if history_started:
            self._commit_history_capture()
        try:
            self._mark_plot_update_pending()
        except Exception:
            pass
        self.append_debug(
            "3D placement translate S{row}: axis={axis} delta={delta:.6g} mm "
            "Desp=({x:.6g},{y:.6g},{z:.6g})".format(
                row=row_index,
                axis=axis_key.upper(),
                delta=float(delta),
                x=float(row.desp_x),
                y=float(row.desp_y),
                z=float(row.desp_z),
            )
        )
        return {
            "row_index": row_index,
            "axis": axis_key,
            "delta_mm": float(delta),
            "before_mm": before,
            "after_mm": float(getattr(row, attr)),
            "scene_placement_settings": settings,
        }


    def _step_roll_deg(self, label: str) -> float:
        if label == "lens":
            return float(getattr(self, "lens_step_rotation_z_deg", 0.0))
        if label == "optical":
            return float(getattr(self, "optical_step_rotation_z_deg", 0.0))
        if label == "camera":
            return float(getattr(self, "camera_step_rotation_z_deg", 0.0))
        if label == "led":
            return float(getattr(self, "led_step_rotation_z_deg", 0.0))
        return 0.0

    def _step_x_rotation_deg(self, label: str) -> float:
        if label == "lens":
            return float(getattr(self, "lens_step_rotation_x_deg", 0.0))
        if label == "optical":
            return float(getattr(self, "optical_step_rotation_x_deg", 0.0))
        if label == "camera":
            return float(getattr(self, "camera_step_rotation_x_deg", 0.0))
        if label == "led":
            return float(getattr(self, "led_step_rotation_x_deg", 0.0))
        return 0.0

    def _step_y_rotation_deg(self, label: str) -> float:
        if label == "lens":
            return float(getattr(self, "lens_step_rotation_y_deg", 0.0))
        if label == "optical":
            return float(getattr(self, "optical_step_rotation_y_deg", 0.0))
        if label == "camera":
            return float(getattr(self, "camera_step_rotation_y_deg", 0.0))
        if label == "led":
            return float(getattr(self, "led_step_rotation_y_deg", 0.0))
        return 0.0

    def _step_target_front_z(self, label: str) -> float:
        if label == "lens":
            return float(self._lens_front_datum_z())
        if label == "camera":
            return float(self._current_image_plane_z() - self._current_camera_front_to_sensor_mm())
        if label == "led":
            return float(self._led_step_z_translation())
        return 0.0

    def apply_step_axis_pick(self, label: str, feature_center_xyz: np.ndarray) -> None:
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return
        feature_center = np.asarray(feature_center_xyz, dtype=float)
        if feature_center.size < 2 or not np.all(np.isfinite(feature_center[:2])):
            self.status_var.set(f"Invalid {label} CAD feature center.")
            return
        current = np.asarray(self._step_axis_offset_xy(label), dtype=float)
        # Offsets translate the whole aligned STEP in the transverse frame. To
        # make the picked feature center land on the optical axis, cancel its
        # current world-space X/Y residual after undoing only the final Z roll.
        delta = np.asarray(self._step_offset_delta_for_world_xy(label, feature_center[:2]), dtype=float)
        new_offset = current + delta
        self._begin_history_capture()
        self._set_step_axis_offset_xy(label, (float(new_offset[0]), float(new_offset[1])))
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._selected_step_label = label
        self._commit_history_capture()
        self.status_var.set(
            f"{label.upper()} STEP feature center moved to optical axis "
            f"(picked X/Y={feature_center[0]:.3g}, {feature_center[1]:.3g} mm; "
            f"offset={new_offset[0]:.3g}, {new_offset[1]:.3g} mm)."
        )
        self._refresh_open_3d_views(step_label=label)

    def clear_step_axis_offsets(self) -> None:
        self._begin_history_capture()
        self.lens_step_axis_offset_xy = (0.0, 0.0)
        self.optical_step_axis_offset_xy = (0.0, 0.0)
        self.camera_step_axis_offset_xy = (0.0, 0.0)
        self.led_step_axis_offset_xy = (0.0, 0.0)
        self.lens_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.optical_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.camera_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.led_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self._live_step_overlay_trace_plan_cache = {}
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._commit_history_capture()
        self._invalidate_preview_scene_trace()
        self.status_var.set("CAD STEP optical-axis offsets cleared.")
        self._refresh_open_3d_views()

    def clear_step_imports(self) -> None:
        self._begin_history_capture()
        self.imported_camera_step_path = None
        self.imported_lens_step_path = None
        self.imported_optical_step_path = None
        self.imported_led_step_path = None
        self.lens_step_largest_component_only = True
        self.camera_step_rotation_x_deg = 0.0
        self.lens_step_rotation_x_deg = 0.0
        self.optical_step_rotation_x_deg = 0.0
        self.led_step_rotation_x_deg = 0.0
        self.camera_step_rotation_y_deg = 0.0
        self.lens_step_rotation_y_deg = 0.0
        self.optical_step_rotation_y_deg = 0.0
        self.led_step_rotation_y_deg = 0.0
        self.camera_step_rotation_z_deg = 0.0
        self.lens_step_rotation_z_deg = 0.0
        self.optical_step_rotation_z_deg = 0.0
        self.led_step_rotation_z_deg = 0.0
        self.led_object_edge_distance_mm = 0.0
        self.led_step_object_edge_local_z = None
        self.lens_step_axis_offset_xy = (0.0, 0.0)
        self.optical_step_axis_offset_xy = (0.0, 0.0)
        self.camera_step_axis_offset_xy = (0.0, 0.0)
        self.led_step_axis_offset_xy = (0.0, 0.0)
        self.lens_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.optical_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.camera_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.led_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._selected_step_label = None
        self._commit_history_capture()
        self._live_step_overlay_trace_plan_cache = {}
        self._invalidate_preview_scene_trace()
        self.status_var.set("Camera/lens/optical/LED STEP imports cleared.")
        self._refresh_open_3d_views()

    def _has_imported_step_cad(self) -> bool:
        return any(
            path is not None
            for path in (
                self.imported_lens_step_path,
                self.imported_optical_step_path,
                self.imported_led_step_path,
                self.imported_camera_step_path,
            )
        )

    def _step_export_alignment_params(self, label: str) -> dict[str, object] | None:
        label = str(label).strip().lower()
        if label == "lens":
            if self.imported_lens_step_path is None:
                return None
            cylinder_axis = self._step_primary_cylinder_axis(self.imported_lens_step_path)
            return {
                "path": self.imported_lens_step_path,
                "largest_component": bool(getattr(self, "lens_step_largest_component_only", True)),
                "source_axis": cylinder_axis if cylinder_axis is not None else "pca0",
                "front_face": "max",
                "target_front_z": self._lens_front_datum_z(),
                "label": "Lens STEP",
                "roll_deg": float(getattr(self, "lens_step_rotation_z_deg", 0.0)),
                "x_rotation_deg": float(getattr(self, "lens_step_rotation_x_deg", 0.0)),
                "y_rotation_deg": float(getattr(self, "lens_step_rotation_y_deg", 0.0)),
                "axis_offset_xy": self._step_axis_offset_xy("lens"),
                "placement_offset_xyz": self._step_placement_offset_xyz("lens"),
            }
        if label == "camera":
            if self.imported_camera_step_path is None:
                return None
            camera_front_z = self._current_image_plane_z() - self._current_camera_front_to_sensor_mm()
            return {
                "path": self.imported_camera_step_path,
                "largest_component": True,
                "source_axis": "z",
                "front_face": "max",
                "target_front_z": camera_front_z,
                "label": "Camera STEP",
                "roll_deg": float(getattr(self, "camera_step_rotation_z_deg", 0.0)),
                "x_rotation_deg": float(getattr(self, "camera_step_rotation_x_deg", 0.0)),
                "y_rotation_deg": float(getattr(self, "camera_step_rotation_y_deg", 0.0)),
                "axis_offset_xy": self._step_axis_offset_xy("camera"),
                "placement_offset_xyz": self._step_placement_offset_xyz("camera"),
            }
        if label == "optical":
            if self.imported_optical_step_path is None:
                return None
            return {
                "path": self.imported_optical_step_path,
                "largest_component": False,
                "source_axis": "z",
                "front_face": "min",
                "target_front_z": 0.0,
                "label": "Optical STEP",
                "roll_deg": float(getattr(self, "optical_step_rotation_z_deg", 0.0)),
                "x_rotation_deg": float(getattr(self, "optical_step_rotation_x_deg", 0.0)),
                "y_rotation_deg": float(getattr(self, "optical_step_rotation_y_deg", 0.0)),
                "axis_offset_xy": self._step_axis_offset_xy("optical"),
                "placement_offset_xyz": self._step_placement_offset_xyz("optical"),
            }
        if label == "led":
            if self.imported_led_step_path is None:
                return None
            return {
                "path": self.imported_led_step_path,
                "largest_component": False,
                "source_axis": "z",
                "front_face": "min",
                "target_front_z": self._led_step_z_translation(),
                "label": "LED STEP",
                "roll_deg": float(getattr(self, "led_step_rotation_z_deg", 0.0)),
                "x_rotation_deg": float(getattr(self, "led_step_rotation_x_deg", 0.0)),
                "y_rotation_deg": float(getattr(self, "led_step_rotation_y_deg", 0.0)),
                "axis_offset_xy": self._step_axis_offset_xy("led"),
                "placement_offset_xyz": self._step_placement_offset_xyz("led"),
            }
        return None

    def _step_alignment_affine(self, params: dict[str, object]) -> np.ndarray | None:
        path = Path(params["path"])
        source_mesh = self._load_step_mesh(
            path,
            largest_component=bool(params.get("largest_component", False)),
        )
        aligned_mesh = self._cad_mesh_aligned_to_optical_axis(
            source_mesh,
            source_axis=params.get("source_axis", "z"),
            front_face=str(params.get("front_face", "min")),
            target_front_z=float(params.get("target_front_z", 0.0)),
            label=str(params.get("label", "STEP")),
            roll_deg=float(params.get("roll_deg", 0.0)),
            x_rotation_deg=float(params.get("x_rotation_deg", 0.0)),
            y_rotation_deg=float(params.get("y_rotation_deg", 0.0)),
            axis_offset_xy=params.get("axis_offset_xy"),
            placement_offset_xyz=params.get("placement_offset_xyz"),
        )
        if aligned_mesh is None:
            return None
        matrix = _affine_from_point_sets(
            np.asarray(source_mesh.points, dtype=float),
            np.asarray(aligned_mesh.points, dtype=float),
        )
        return matrix

    def _collect_native_step_export_shapes(self, progress_callback=None) -> list[tuple[str, object]]:
        shape_items: list[tuple[str, object]] = []
        labels = STEP_OVERLAY_LABELS
        for index, label in enumerate(labels, start=1):
            params = self._step_export_alignment_params(label)
            if params is None:
                continue
            if progress_callback is not None:
                progress_callback(
                    f"Preparing {params.get('label', label)} native STEP",
                    index,
                    len(labels),
                )
            try:
                matrix = self._step_alignment_affine(params)
                if matrix is None:
                    raise RuntimeError("could not compute CAD placement affine")
                shape = _read_step_shape(Path(params["path"]))
                shape_items.append((str(params.get("label", label)), _shape_with_affine(shape, matrix)))
            except Exception as exc:
                self.append_debug(f"3D STEP native {label} export skipped: {exc}")
        return shape_items

    def _step_export_ray_polylines(self, system) -> list[np.ndarray]:
        previous_ray_count = getattr(self, "_preview_field_ray_count", None)
        previous_bundle_count = getattr(self, "_preview_field_bundle_count", None)
        rays_per_group = previous_ray_count
        try:
            wavelength = self._current_wavelength()
            max_radius = max((max(float(row.diameter) / 2.0, 0.5) for row in self.rows), default=1.0)
            rays = Kos.raykeeper(system)
            self._trace_preview_rays(
                system,
                rays,
                wavelength,
                max_radius,
                allow_full_pupil=True,
                sampling_mode="world_envelope",
            )
            rays_per_group = getattr(self, "_preview_field_ray_count", previous_ray_count)
        except Exception as exc:
            self.append_debug(f"3D STEP ray export skipped: {exc}")
            rays = self.last_rays
        finally:
            if previous_ray_count is not None:
                self._preview_field_ray_count = previous_ray_count
            if previous_bundle_count is not None:
                self._preview_field_bundle_count = previous_bundle_count
        polylines: list[np.ndarray] = []
        for ray in getattr(rays, "CC", ()) if rays is not None else ():
            pts = np.asarray(ray, dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
                continue
            if not np.any(np.all(np.isfinite(pts[:, :3]), axis=1)):
                continue
            polylines.append(pts[:, :3].copy())
        envelope = _ray_bundle_envelope_polylines(
            polylines,
            rays_per_group,
        )
        if len(envelope) < len(polylines):
            self.append_progress(
                f"STEP ray export reduced to envelope: {len(envelope)}/{len(polylines)} traced rays"
            )
        return envelope

    def _collect_3d_step_export_meshes(self, system) -> list[tuple[str, object]]:
        _load_3d_backends()
        if pv is None:
            raise RuntimeError("PyVista is required to collect 3D export geometry")

        mesh_items: list[tuple[str, object]] = []

        def add_mesh(label: str, mesh) -> None:
            if mesh is None:
                return
            try:
                surface = mesh.extract_surface(algorithm="dataset_surface").copy(deep=True)
            except Exception:
                try:
                    surface = mesh.copy(deep=True)
                except Exception:
                    return
            try:
                if int(getattr(surface, "n_points", 0)) > 0:
                    mesh_items.append((label, surface))
            except Exception:
                pass

        transforms = getattr(system, "TRANS_2A", None)
        surfaces = getattr(system, "AAA", None)
        if transforms is not None and surfaces is not None:
            block_count = min(len(self.rows), getattr(surfaces, "n_blocks", 0), len(transforms))
            for index in range(block_count):
                row = self.rows[index]
                if row.surface in {"Object", "Image"}:
                    continue
                add_mesh(
                    f"surface_{index}_{row.name or row.surface}",
                    Kraken3DInspector._mesh_with_transform(surfaces[index], transforms[index]),
                )

        side_index = 0
        for row_index in getattr(system, "side_number", []):
            try:
                body = pv.wrap(system.BBB[side_index]).extract_surface(algorithm="dataset_surface").copy(deep=True)
            except Exception:
                side_index += 1
                continue
            side_index += 1
            if 0 <= int(row_index) < len(self.rows):
                row = self.rows[int(row_index)]
                add_mesh(f"edge_{int(row_index)}_{row.name or row.surface}", body)
            else:
                add_mesh(f"edge_{int(row_index)}", body)

        try:
            add_mesh("external_camera", self._transformed_external_camera_mesh())
        except Exception as exc:
            self.append_debug(f"3D STEP export external camera skipped: {exc}")

        for label, builder in (
            ("lens_step", self._transformed_imported_lens_step_mesh),
            ("optical_step", self._transformed_imported_optical_step_mesh),
            ("led_step", self._transformed_imported_led_step_mesh),
            ("camera_step", self._transformed_imported_camera_step_mesh),
        ):
            try:
                add_mesh(label, builder())
            except Exception as exc:
                self.append_debug(f"3D STEP export {label} skipped: {exc}")

        return mesh_items

    def _collect_step_edge_and_extra_meshes(self, system) -> list[tuple[str, object]]:
        """Collect edge geometry and imported meshes, excluding optical surface
        faces (which are handled analytically)."""
        _load_3d_backends()
        if pv is None:
            return []

        mesh_items: list[tuple[str, object]] = []

        def add_mesh(label: str, mesh) -> None:
            if mesh is None:
                return
            try:
                surface = mesh.extract_surface(algorithm="dataset_surface").copy(deep=True)
            except Exception:
                try:
                    surface = mesh.copy(deep=True)
                except Exception:
                    return
            try:
                if int(getattr(surface, "n_points", 0)) > 0:
                    mesh_items.append((label, surface))
            except Exception:
                pass

        side_index = 0
        for row_index in getattr(system, "side_number", []):
            try:
                body = pv.wrap(system.BBB[side_index]).extract_surface(
                    algorithm="dataset_surface"
                ).copy(deep=True)
            except Exception:
                side_index += 1
                continue
            side_index += 1
            if 0 <= int(row_index) < len(self.rows):
                row = self.rows[int(row_index)]
                add_mesh(f"edge_{int(row_index)}_{row.name or row.surface}", body)
            else:
                add_mesh(f"edge_{int(row_index)}", body)

        try:
            add_mesh("external_camera", self._transformed_external_camera_mesh())
        except Exception:
            pass

        for label, builder in (
            ("lens_step", self._transformed_imported_lens_step_mesh),
            ("optical_step", self._transformed_imported_optical_step_mesh),
            ("led_step", self._transformed_imported_led_step_mesh),
            ("camera_step", self._transformed_imported_camera_step_mesh),
        ):
            try:
                add_mesh(label, builder())
            except Exception:
                pass

        return mesh_items

    def _ask_step_file(self, title: str, initial_dir: Path, *, parent: tk.Misc | None = None) -> Path | None:
        path = filedialog.askopenfilename(
            title=title,
            initialdir=str(initial_dir if initial_dir.exists() else Path.home()),
            filetypes=[
                ("STEP files", "*.step *.stp *.ste *.STEP *.STP *.STE"),
                ("All files", "*"),
            ],
            parent=parent or self,
        )
        if not path:
            return None
        selected = Path(path).expanduser()
        if not selected.exists():
            messagebox.showerror("STEP file not found", f"File does not exist:\n\n{selected}", parent=parent or self)
            return None
        return selected

    def _refresh_open_3d_views(
        self,
        *,
        camera_only: bool = False,
        step_label: str | None = None,
        force_retrace: bool = False,
    ) -> None:
        if camera_only:
            step_label = "camera"
        if self._three_d_inspector is not None:
            try:
                if self._three_d_inspector.winfo_exists():
                    self._three_d_inspector.refresh_from_editor(force_retrace=force_retrace)
            except Exception:
                pass
        if self._legacy_3d_plotter is not None:
            labels = [step_label] if step_label else list(STEP_OVERLAY_LABELS)
            refreshed = False
            for label in labels:
                if label and self._refresh_legacy_step_actor(self._legacy_3d_plotter, label):
                    refreshed = True
            if refreshed:
                return
            self.status_var.set("STEP change saved. Close and reopen legacy 3D view to redraw.")

    def _clear_open3d_face_metadata_hover_state(self, row_index: int | None = None) -> None:
        inspector = getattr(self, "_three_d_inspector", None)
        if inspector is None:
            return
        try:
            if not inspector.winfo_exists():
                return
        except Exception:
            return
        try:
            inspector.clear_face_metadata_hover_state(row_index)
        except Exception as exc:
            self.append_debug(f"Open 3D face metadata hover clear failed: {exc}")

    def _refresh_legacy_camera_step_actor(self, plotter) -> bool:
        return self._refresh_legacy_step_actor(plotter, "camera")

    def _refresh_legacy_step_actor(self, plotter, label: str) -> bool:
        if plotter is None:
            return False
        scene = dict(getattr(plotter, "_kraken_scene", {}) or {})
        cad_step_actors = dict(scene.get("cad_step_actors", {}) or {})
        cad_step_actor_map = dict(scene.get("cad_step_actor_map", {}) or {})
        step_actors = list(cad_step_actors.get(label, []) or [])
        visibility = dict(getattr(plotter, "_kraken_visibility", {}) or {})
        visible = bool(visibility.get(f"step_{label}", True))
        try:
            builders = {
                "camera": self._transformed_imported_camera_step_mesh,
                "led": self._transformed_imported_led_step_mesh,
                "lens": self._transformed_imported_lens_step_mesh,
                "optical": self._transformed_imported_optical_step_mesh,
            }
            builder = builders.get(label)
            if builder is None:
                return False
            cad_mesh = builder()
        except Exception as exc:
            self.append_debug(f"Legacy 3D {label} STEP refresh failed: {exc}")
            return False
        if cad_mesh is None or int(getattr(cad_mesh, "n_points", 0)) <= 0:
            if not step_actors:
                return False
            hidden = False
            for _kind, actor in step_actors:
                try:
                    actor.SetVisibility(False)
                    hidden = True
                except Exception:
                    pass
            if hidden:
                try:
                    plotter.render()
                except Exception:
                    pass
            return hidden
        try:
            edges = cad_mesh.extract_feature_edges(
                feature_angle=20,
                boundary_edges=True,
                feature_edges=True,
                manifold_edges=False,
            )
        except Exception:
            edges = None
        if not step_actors:
            try:
                color, opacity = {
                    "lens": ("#4b5563", 0.22),
                    "optical": ("#0891b2", 0.30),
                    "led": ("#f59e0b", 0.35),
                    "camera": ("#6b7280", 0.32),
                }.get(label, ("#6b7280", 0.32))
                helper_actors = list(scene.get("helper_actors", []) or [])
                cad_step_actors.setdefault(label, [])
                actor = plotter.add_mesh(
                    cad_mesh,
                    color=color,
                    opacity=opacity,
                    smooth_shading=False,
                    show_edges=False,
                    pickable=True,
                )
                try:
                    actor.SetPickable(True)
                except Exception:
                    pass
                actor_key = Kraken3DInspector._actor_key(actor)
                if actor_key is not None:
                    cad_step_actor_map[actor_key] = label
                try:
                    actor.SetVisibility(visible)
                except Exception:
                    pass
                cad_step_actors[label].append(("mesh", actor))
                if edges is not None and int(getattr(edges, "n_points", 0)) > 0:
                    edge_actor = plotter.add_mesh(edges, color="#111827", line_width=0.8, pickable=False)
                    try:
                        edge_actor.SetVisibility(visible)
                    except Exception:
                        pass
                    cad_step_actors[label].append(("edges", edge_actor))
                scene["helper_actors"] = helper_actors
                scene["cad_step_actors"] = cad_step_actors
                scene["cad_step_actor_map"] = cad_step_actor_map
                setattr(plotter, "_kraken_scene", scene)
                try:
                    plotter.render()
                except Exception:
                    pass
                return True
            except Exception as exc:
                self.append_debug(f"Legacy 3D {label} STEP add failed: {exc}")
                return False
        refreshed = False
        for kind, actor in step_actors:
            try:
                mapper = actor.GetMapper()
                if mapper is None:
                    continue
                if kind == "edges":
                    if edges is None or int(getattr(edges, "n_points", 0)) <= 0:
                        actor.SetVisibility(False)
                        continue
                    mapper.SetInputData(edges)
                    actor.SetVisibility(visible)
                else:
                    mapper.SetInputData(cad_mesh)
                    actor.SetVisibility(visible)
                mapper.Modified()
                refreshed = True
            except Exception as exc:
                self.append_debug(f"Legacy 3D {label} actor update failed: {exc}")
        if refreshed:
            try:
                plotter.render()
            except Exception:
                pass
            if label == "camera":
                self.status_var.set(
                    f"Camera STEP rotation: X={self.camera_step_rotation_x_deg:.0f}, "
                    f"Y={self.camera_step_rotation_y_deg:.0f}, "
                    f"Z={self.camera_step_rotation_z_deg:.0f} deg"
                )
            elif label == "lens":
                self.status_var.set(
                    f"Lens STEP rotation: X={self.lens_step_rotation_x_deg:.0f}, "
                    f"Y={self.lens_step_rotation_y_deg:.0f}, "
                    f"Z={self.lens_step_rotation_z_deg:.0f} deg"
                )
            elif label == "optical":
                self.status_var.set(
                    f"Optical STEP rotation: X={self.optical_step_rotation_x_deg:.0f}, "
                    f"Y={self.optical_step_rotation_y_deg:.0f}, "
                    f"Z={self.optical_step_rotation_z_deg:.0f} deg"
                )
            elif label == "led":
                reference_text = (
                    "unset"
                    if getattr(self, "led_step_object_edge_local_z", None) is None
                    else f"{float(self.led_step_object_edge_local_z):.3g} mm"
                )
                self.status_var.set(
                    f"LED STEP: x rotation={self.led_step_rotation_x_deg:.0f} deg, "
                    f"y rotation={self.led_step_rotation_y_deg:.0f} deg, "
                    f"z rotation={self.led_step_rotation_z_deg:.0f} deg, "
                    f"edge distance={self.led_object_edge_distance_mm:.3g} mm, "
                    f"edge ref={reference_text}"
                )
        return refreshed


    def _main_trace_display_controls_panel(self) -> MainTraceDisplayControlsPanel:
        panel = self.__dict__.get("_main_trace_display_controls_panel_instance")
        if panel is None:
            panel = MainTraceDisplayControlsPanel(
                self,
                source_model_default=SOURCE_MODEL_DEFAULT,
                folded_detector_policy_default=FOLDED_DETECTOR_POLICY_DEFAULT,
                folded_detector_policy_values=FOLDED_DETECTOR_POLICY_VALUES,
                wavefront_style_default=WAVEFRONT_STYLE_DEFAULT,
                wavefront_style_values=WAVEFRONT_STYLE_VALUES,
                tolerance_compare_view_default=TOLERANCE_COMPARE_VIEW_DEFAULT,
                tolerance_compare_view_values=TOLERANCE_COMPARE_VIEW_VALUES,
                analysis_path_filter_default=ANALYSIS_PATH_FILTER_DEFAULT,
                detector_bins_default=DETECTOR_BINS_DEFAULT,
                coherent_sum_mode_default=COHERENT_SUM_MODE_DEFAULT,
                coherent_sum_mode_values=COHERENT_SUM_MODE_VALUES,
                branch_field_propagation_mm_default=BRANCH_FIELD_PROPAGATION_MM_DEFAULT,
            )
            self._main_trace_display_controls_panel_instance = panel
        return panel

    def _build_controls_panel(self, parent) -> None:
        self._main_trace_display_controls_panel().build(parent)

    def _main_field_controls_panel(self) -> MainFieldControlsPanel:
        panel = self.__dict__.get("_main_field_controls_panel_instance")
        if panel is None:
            panel = MainFieldControlsPanel(
                self,
                field_type_values=FIELD_TYPE_CANONICAL_VALUES,
                camera_none_label=CAMERA_NONE_LABEL,
                camera_names=camera_names,
            )
            self._main_field_controls_panel_instance = panel
        return panel

    def _build_field_panel(self, parent) -> None:
        self._main_field_controls_panel().build(parent)

    def _main_source_controls_panel(self) -> MainSourceControlsPanel:
        panel = self.__dict__.get("_main_source_controls_panel_instance")
        if panel is None:
            panel = MainSourceControlsPanel(
                self,
                source_model_default=SOURCE_MODEL_DEFAULT,
                source_model_values=SOURCE_MODEL_VALUES,
                pupil_pattern_default=PUPIL_PATTERN_DEFAULT,
                pupil_pattern_values=PUPIL_PATTERN_VALUES,
                gaussian_input_mode_default=GAUSSIAN_INPUT_MODE_DEFAULT,
                gaussian_input_mode_values=GAUSSIAN_INPUT_MODE_VALUES,
                gaussian_waist_side_default=GAUSSIAN_WAIST_SIDE_DEFAULT,
                gaussian_waist_side_values=GAUSSIAN_WAIST_SIDE_VALUES,
                source_direction_preset_values=SOURCE_DIRECTION_PRESET_VALUES,
                source_angular_weight_default=SOURCE_ANGULAR_WEIGHT_DEFAULT,
                source_angular_weight_values=SOURCE_ANGULAR_WEIGHT_VALUES,
            )
            self._main_source_controls_panel_instance = panel
        return panel

    def _build_source_panel(self, parent) -> None:
        self._main_source_controls_panel().build(parent)

    def _main_analysis_toolbar_panel(self) -> MainAnalysisToolbarPanel:
        panel = self.__dict__.get("_main_analysis_toolbar_panel_instance")
        if panel is None:
            panel = MainAnalysisToolbarPanel(self)
            self._main_analysis_toolbar_panel_instance = panel
        return panel

    def _main_information_panel(self) -> MainInformationPanel:
        panel = self.__dict__.get("_main_information_panel_instance")
        if panel is None:
            panel = MainInformationPanel(self)
            self._main_information_panel_instance = panel
        return panel

    def _register_left_mode_control(
        self,
        var_name: str,
        widget,
        relevant,
        *,
        normal_state: str = "normal",
        extra_widgets=(),
        include_label: bool = True,
    ) -> None:
        if not hasattr(self, "_left_mode_controls"):
            self._left_mode_controls = []
        managed_widgets = self._left_mode_control_grid_widgets(
            widget,
            extra_widgets=extra_widgets,
            include_label=include_label,
        )
        var = getattr(self, var_name, None)
        try:
            fallback = str(var.get()) if var is not None else ""
        except Exception:
            fallback = ""
        grid_records = []
        for managed_widget in managed_widgets:
            try:
                grid_records.append((managed_widget, dict(managed_widget.grid_info())))
            except Exception:
                pass
        self._left_mode_controls.append(
            {
                "var_name": var_name,
                "widget": widget,
                "managed_widgets": managed_widgets,
                "grid_records": grid_records,
                "relevant": relevant,
                "normal_state": normal_state,
                "fallback": fallback,
            }
        )

    @staticmethod
    def _left_mode_control_grid_widgets(widget, *, extra_widgets=(), include_label: bool = True) -> list:
        managed = []

        def add(candidate) -> None:
            if candidate is not None and candidate not in managed:
                managed.append(candidate)

        add(widget)
        try:
            grid_info = widget.grid_info()
            parent = widget.master
            row = int(grid_info.get("row", 0))
            column = int(grid_info.get("column", 0))
            columnspan = int(grid_info.get("columnspan", 1))
            label_row = row - 1
        except Exception:
            row = column = label_row = -1
            columnspan = 1
            parent = None
        if include_label and parent is not None and label_row >= 0:
            wanted = set(range(column, column + max(columnspan, 1)))
            try:
                for candidate in parent.grid_slaves(row=label_row):
                    if candidate is widget:
                        continue
                    info = candidate.grid_info()
                    candidate_column = int(info.get("column", 0))
                    candidate_span = int(info.get("columnspan", 1))
                    candidate_columns = set(range(candidate_column, candidate_column + max(candidate_span, 1)))
                    if wanted & candidate_columns:
                        add(candidate)
            except Exception:
                pass
        for candidate in extra_widgets or ():
            add(candidate)
        return managed

    def _register_source_mode_controls(self, **widgets) -> None:
        if hasattr(self, "field_type_menu"):
            self._register_left_mode_control(
                "field_type_var",
                self.field_type_menu,
                lambda: self._current_source_model() == SOURCE_MODEL_DEFAULT,
                normal_state="readonly",
            )
        if hasattr(self, "field_value_entry"):
            self._register_left_mode_control(
                "field_value_var",
                self.field_value_entry,
                lambda: self._current_source_model() == SOURCE_MODEL_DEFAULT,
            )
        if hasattr(self, "field_count_entry"):
            self._register_left_mode_control(
                "field_count_var",
                self.field_count_entry,
                lambda: self._current_source_model() == SOURCE_MODEL_DEFAULT,
            )
        self._register_left_mode_control(
            "pupil_pattern_var",
            self.pupil_pattern_menu,
            lambda: self._current_source_model() == SOURCE_MODEL_DEFAULT,
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "source_radius_var",
            widgets["source_radius_entry"],
            lambda: self._current_source_model() in {
                "Collimated disk source",
                "Random circle source",
                "Random square source",
                "Random line source",
            },
        )
        self._register_left_mode_control(
            "source_cone_angle_var",
            widgets["source_cone_angle_entry"],
            lambda: self._current_source_model() in {
                SOURCE_MODEL_DEFAULT,
                "Collimated disk source",
                "Random circle source",
                "Random square source",
                "Random line source",
                "Random point cone",
            },
        )
        self._register_left_mode_control(
            "gaussian_input_mode_var",
            widgets["gaussian_input_mode_menu"],
            lambda: self._current_source_model() == "Gaussian beam",
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "gaussian_waist_radius_var",
            widgets["gaussian_waist_entry"],
            lambda: self._current_source_model() == "Gaussian beam" and self._current_gaussian_input_mode() == GAUSSIAN_INPUT_MODE_DEFAULT,
        )
        self._register_left_mode_control(
            "gaussian_waist_offset_var",
            widgets["gaussian_offset_entry"],
            lambda: self._current_source_model() == "Gaussian beam" and self._current_gaussian_input_mode() == GAUSSIAN_INPUT_MODE_DEFAULT,
        )
        self._register_left_mode_control(
            "gaussian_beam_diameter_var",
            widgets["gaussian_diameter_entry"],
            lambda: self._current_source_model() == "Gaussian beam" and self._current_gaussian_input_mode() == "Diameter + divergence",
        )
        self._register_left_mode_control(
            "gaussian_full_divergence_var",
            widgets["gaussian_divergence_entry"],
            lambda: self._current_source_model() == "Gaussian beam" and self._current_gaussian_input_mode() == "Diameter + divergence",
        )
        self._register_left_mode_control(
            "gaussian_m2_var",
            widgets["gaussian_m2_entry"],
            lambda: self._current_source_model() == "Gaussian beam",
        )
        self._register_left_mode_control(
            "gaussian_waist_side_var",
            widgets["gaussian_waist_side_menu"],
            lambda: self._current_source_model() == "Gaussian beam" and self._current_gaussian_input_mode() == "Diameter + divergence",
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "pupil_rad_var",
            widgets["pupil_rad_entry"],
            lambda: self._current_source_model() == SOURCE_MODEL_DEFAULT and self._current_pupil_pattern_label() == "R-theta",
        )
        self._register_left_mode_control(
            "pupil_theta_var",
            widgets["pupil_theta_entry"],
            lambda: self._current_source_model() == SOURCE_MODEL_DEFAULT and self._current_pupil_pattern_label() == "R-theta",
        )
        self._register_left_mode_control(
            "source_power_var",
            widgets["source_power_entry"],
            lambda: self._current_source_model() != SOURCE_MODEL_DEFAULT,
        )
        self._register_left_mode_control(
            "source_seed_var",
            widgets["source_seed_entry"],
            lambda: self._current_source_model() in {
                "Random circle source",
                "Random square source",
                "Random line source",
                "Random point cone",
            } or (self._current_source_model() == SOURCE_MODEL_DEFAULT and self._current_pupil_pattern_label() == "Random disk"),
        )
        for var_name, widget_name in (
            ("source_x_var", "source_x_entry"),
            ("source_y_var", "source_y_entry"),
            ("source_z_var", "source_z_entry"),
            ("source_l_var", "source_l_entry"),
            ("source_m_var", "source_m_entry"),
            ("source_n_var", "source_n_entry"),
        ):
            self._register_left_mode_control(
                var_name,
                widgets[widget_name],
                lambda: self._current_source_model() != SOURCE_MODEL_DEFAULT,
            )
        self._register_left_mode_control(
            "source_direction_preset_var",
            widgets["source_direction_preset_menu"],
            lambda: self._current_source_model() != SOURCE_MODEL_DEFAULT,
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "source_angular_weight_var",
            widgets["source_angular_weight_menu"],
            lambda: self._current_source_model() in {"Random circle source", "Random square source"},
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "",
            widgets["source_physical_note"],
            lambda: self._current_source_model() != SOURCE_MODEL_DEFAULT,
            include_label=False,
        )
        self._register_left_mode_control(
            "",
            widgets["source_summary_label"],
            lambda: True,
            include_label=False,
        )
        self._register_left_mode_control(
            "",
            widgets["source_manager_button"],
            lambda: True,
            include_label=False,
        )

    def _sync_left_mode_controls(self) -> None:
        controls = list(getattr(self, "_left_mode_controls", []) or [])
        if not controls:
            return
        saved = getattr(self, "_left_mode_saved_values", None)
        if saved is None:
            saved = {}
            self._left_mode_saved_values = saved
        for control in controls:
            var_name = str(control.get("var_name", ""))
            var = getattr(self, var_name, None)
            widget = control.get("widget")
            relevant = control.get("relevant")
            normal_state = str(control.get("normal_state", "normal"))
            if widget is None or not callable(relevant):
                continue
            try:
                is_relevant = bool(relevant())
            except Exception:
                is_relevant = True
            try:
                current = str(var.get())
            except Exception:
                current = ""
            if is_relevant:
                if current == "NA":
                    restored = saved.pop(var_name, str(control.get("fallback", "")))
                    if restored:
                        try:
                            var.set(restored)
                        except Exception:
                            pass
                try:
                    widget.configure(state=normal_state)
                except Exception:
                    pass
            else:
                if var is not None and current not in {"", "NA"}:
                    saved.setdefault(var_name, current)
                try:
                    widget.configure(state="disabled")
                except Exception:
                    pass
            control["visible"] = is_relevant
        self._sync_left_source_panel_layout()
        self._sync_left_field_panel_visibility()
        self._reflow_left_mode_controls()
        self._sync_field_sample_count_state()

    def _sync_left_source_panel_layout(self) -> None:
        is_default_source = self._current_source_model() == SOURCE_MODEL_DEFAULT
        span = 1 if is_default_source else 2
        for widget in (getattr(self, "source_model_label", None), getattr(self, "source_model_menu", None)):
            if widget is None:
                continue
            try:
                widget.grid_configure(columnspan=span)
            except Exception:
                pass

    def _sync_left_field_panel_visibility(self) -> None:
        field_panel = getattr(self, "field_panel", None)
        if field_panel is None:
            return
        try:
            if self._current_source_model() == SOURCE_MODEL_DEFAULT:
                field_panel.grid()
            else:
                field_panel.grid_remove()
        except Exception:
            pass

    def _reflow_left_mode_controls(self) -> None:
        controls = list(getattr(self, "_left_mode_controls", []) or [])
        if not controls:
            return
        managed_widgets = {
            widget
            for control in controls
            for widget in (control.get("managed_widgets") or ())
            if widget is not None
        }
        parent_controls: dict[tk.Widget, list[dict[str, object]]] = {}
        for index, control in enumerate(controls):
            visible = bool(control.get("visible", True))
            records = []
            parent = None
            for widget, original_info in control.get("grid_records", []) or []:
                if widget is None or not isinstance(original_info, dict) or not original_info:
                    continue
                widget_parent = getattr(widget, "master", None)
                if widget_parent is None:
                    continue
                if parent is None:
                    parent = widget_parent
                if widget_parent is not parent:
                    continue
                records.append((widget, dict(original_info)))
            if parent is not None and records:
                parent_controls.setdefault(parent, []).append(
                    {
                        "index": index,
                        "records": records,
                        "visible": visible,
                    }
                )

        for parent, panel_controls in parent_controls.items():
            fixed_cells: set[tuple[int, int]] = set()
            try:
                children = list(parent.grid_slaves())
            except Exception:
                children = []
            for child in children:
                if child in managed_widgets:
                    continue
                try:
                    info = child.grid_info()
                    row = int(info.get("row", 0))
                    column = int(info.get("column", 0))
                    rowspan = max(int(info.get("rowspan", 1)), 1)
                    columnspan = max(int(info.get("columnspan", 1)), 1)
                except Exception:
                    continue
                for rr in range(row, row + rowspan):
                    for cc in range(column, column + columnspan):
                        fixed_cells.add((rr, cc))

            items = []
            for control in panel_controls:
                records = list(control.get("records") or [])
                if not bool(control.get("visible", True)):
                    for widget, _info in records:
                        try:
                            widget.grid_remove()
                        except Exception:
                            pass
                    continue

                parsed = []
                for widget, info in records:
                    try:
                        row = int(info.get("row", 0))
                        column = int(info.get("column", 0))
                        rowspan = max(int(info.get("rowspan", 1)), 1)
                        columnspan = max(int(info.get("columnspan", 1)), 1)
                    except Exception:
                        row = column = 0
                        rowspan = columnspan = 1
                    parsed.append(
                        {
                            "widget": widget,
                            "info": info,
                            "row": row,
                            "column": column,
                            "rowspan": rowspan,
                            "columnspan": columnspan,
                        }
                    )
                if not parsed:
                    continue

                base_row = min(int(record["row"]) for record in parsed)
                base_column = min(int(record["column"]) for record in parsed)
                max_column = max(int(record["column"]) + int(record["columnspan"]) for record in parsed)
                if any(int(record["columnspan"]) > 1 for record in parsed):
                    kind = "wide"
                elif max_column - base_column > 1:
                    kind = "multi"
                else:
                    kind = "single"
                height = max(
                    int(record["row"]) - base_row + int(record["rowspan"])
                    for record in parsed
                )
                items.append(
                    {
                        "index": int(control.get("index", 0)),
                        "records": parsed,
                        "base_row": base_row,
                        "base_column": base_column,
                        "kind": kind,
                        "height": max(height, 1),
                    }
                )

            if not items:
                continue

            items.sort(key=lambda item: (int(item["base_row"]), int(item["base_column"]), int(item["index"])))
            occupied = set(fixed_cells)
            first_row = min(int(item["base_row"]) for item in items)
            cursor_row = first_row

            def cells_for_item(item: dict[str, object], target_row: int, target_column: int) -> list[tuple[int, int]]:
                kind = str(item["kind"])
                cells: list[tuple[int, int]] = []
                for record in item["records"]:
                    row_delta = int(record["row"]) - int(item["base_row"])
                    rowspan = int(record["rowspan"])
                    if kind == "wide":
                        column = 0
                        columnspan = 2
                    elif kind == "multi":
                        column = int(record["column"]) - int(item["base_column"])
                        columnspan = int(record["columnspan"])
                    else:
                        column = target_column
                        columnspan = 1
                    for rr in range(target_row + row_delta, target_row + row_delta + rowspan):
                        for cc in range(column, column + columnspan):
                            cells.append((rr, cc))
                return cells

            def first_available_slot(item: dict[str, object], start_row: int) -> tuple[int, int]:
                columns = (0, 1) if str(item["kind"]) == "single" else (0,)
                target_row = max(start_row, first_row)
                while target_row < first_row + 200:
                    for target_column in columns:
                        cells = cells_for_item(item, target_row, target_column)
                        if not any(cell in occupied for cell in cells):
                            return target_row, target_column
                    target_row += 1
                return target_row, 0

            for item in items:
                target_row, target_column = first_available_slot(item, cursor_row)
                occupied.update(cells_for_item(item, target_row, target_column))
                for record in item["records"]:
                    info = dict(record["info"])
                    row_delta = int(record["row"]) - int(item["base_row"])
                    info["row"] = target_row + row_delta
                    kind = str(item["kind"])
                    if kind == "wide":
                        info["column"] = 0
                        info["columnspan"] = 2
                    elif kind == "multi":
                        info["column"] = int(record["column"]) - int(item["base_column"])
                    else:
                        info["column"] = target_column
                        info["columnspan"] = 1
                        info["padx"] = (8, 0) if target_column else (0, 0)
                    try:
                        record["widget"].grid(**info)
                    except Exception:
                        pass
                if str(item["kind"]) != "single":
                    cursor_row = max(cursor_row, target_row + int(item["height"]))

    def _left_mode_text(self, var_name: str, fallback: str = "") -> str:
        var = getattr(self, var_name, None)
        try:
            text = str(var.get()).strip() if var is not None else str(fallback)
        except Exception:
            text = str(fallback)
        if text == "NA":
            saved = getattr(self, "_left_mode_saved_values", {}) or {}
            text = str(saved.get(var_name, fallback)).strip()
        return text

    def _main_atmosphere_panel(self) -> MainAtmospherePanel:
        panel = self.__dict__.get("_main_atmosphere_panel_instance")
        if panel is None:
            panel = MainAtmospherePanel(
                self,
                atmos_plot_mode_default=ATMOS_PLOT_MODE_DEFAULT,
                atmos_plot_mode_values=ATMOS_PLOT_MODE_VALUES,
            )
            self._main_atmosphere_panel_instance = panel
        return panel

    def _build_atmosphere_panel(self, parent) -> None:
        self._main_atmosphere_panel().build_hidden_panel(parent)

    def open_atmosphere_settings_dialog(self) -> None:
        self._main_atmosphere_panel().open_settings_dialog()

    def _close_atmosphere_settings_dialog(self) -> None:
        self._main_atmosphere_panel().close_settings_dialog()

    def _on_control_stack_configure(self, _event=None) -> None:
        if not hasattr(self, "control_canvas"):
            return
        self.control_canvas.configure(scrollregion=self.control_canvas.bbox("all"))

    def _on_control_canvas_configure(self, event=None) -> None:
        if not hasattr(self, "control_canvas") or not hasattr(self, "control_stack_window"):
            return
        width = self.control_canvas.winfo_width() if event is None else int(event.width)
        self.control_canvas.itemconfigure(self.control_stack_window, width=max(width, 1))

    def _on_left_panel_mousewheel(self, event=None):
        canvas = getattr(self, "control_canvas", None)
        if canvas is None or event is None:
            return None
        try:
            pointer_x = canvas.winfo_pointerx()
            pointer_y = canvas.winfo_pointery()
            canvas_x = canvas.winfo_rootx()
            canvas_y = canvas.winfo_rooty()
            inside_canvas = (
                canvas_x <= pointer_x < canvas_x + canvas.winfo_width()
                and canvas_y <= pointer_y < canvas_y + canvas.winfo_height()
            )
        except Exception:
            return None
        if not inside_canvas:
            return None
        try:
            bbox = canvas.bbox("all")
            if not bbox or int(bbox[3] - bbox[1]) <= canvas.winfo_height():
                return "break"
        except Exception:
            pass

        delta = 0
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            wheel_delta = int(getattr(event, "delta", 0) or 0)
            if wheel_delta:
                delta = -max(1, abs(wheel_delta) // 120) if wheel_delta > 0 else max(1, abs(wheel_delta) // 120)
        if delta:
            try:
                canvas.yview_scroll(delta, "units")
            except Exception:
                return None
            return "break"
        return None

    def _update_field_status_hint(self) -> None:
        if not hasattr(self, "status_hint_var"):
            return
        note = self.field_mode_note_var.get().strip() if hasattr(self, "field_mode_note_var") else ""
        warning = self.field_warning_var.get().strip() if hasattr(self, "field_warning_var") else ""
        summary = self.field_summary_var.get().strip() if hasattr(self, "field_summary_var") else ""
        summary = summary.replace("\n", " | ")
        sampling_note = ""
        try:
            if self._current_source_model() == SOURCE_MODEL_DEFAULT and not self._field_sampling_is_active():
                basis, unit, _span = self._field_sampling_basis_span()
                sampling_note = f"Field samples: NA while {basis} span is 0 {unit}."
        except Exception:
            sampling_note = ""
        parts = [part for part in (note, sampling_note, warning, summary) if part]
        self.status_hint_var.set("  ||  ".join(parts))

    def _main_optimization_panel(self) -> MainOptimizationPanel:
        panel = self.__dict__.get("_main_optimization_panel_instance")
        if panel is None:
            panel = MainOptimizationPanel(self, operand_specs=OPERAND_REGISTRY.values())
            self._main_optimization_panel_instance = panel
        return panel

    def _build_optimization_panel(self, parent) -> None:
        self._main_optimization_panel().build(parent)

    def _build_results_panel(self, parent) -> None:
        self._main_information_panel().build(parent)

    def _bind_deferred_refresh(self, widget: tk.Widget) -> None:
        widget.bind("<FocusIn>", self._begin_history_capture, add="+")
        widget.bind("<FocusOut>", self._mark_plot_update_pending, add="+")
        widget.bind("<Return>", self._mark_plot_update_pending, add="+")
        widget.bind("<KP_Enter>", self._mark_plot_update_pending, add="+")

    def _bind_deferred_manual_update(self, widget: tk.Widget, *, sync_fields: bool = False) -> None:
        def _on_commit(_event=None):
            if sync_fields:
                self._sync_object_controls()
            else:
                self._sync_left_mode_controls()
            self._mark_plot_update_pending()

        widget.bind("<FocusIn>", self._begin_history_capture, add="+")
        widget.bind("<FocusOut>", _on_commit, add="+")
        widget.bind("<Return>", _on_commit, add="+")
        widget.bind("<KP_Enter>", _on_commit, add="+")

    def _invalidate_preview_scene_trace(self, reason: str = "") -> None:
        self._preview_scene_trace_dirty = True
        self._last_preview_trace_signature = None
        if reason:
            try:
                self.append_debug(f"Preview trace invalidated: {reason}")
            except Exception:
                pass

    def _invalidate_optical_solid_face_assignment_trace(
        self,
        row_index: int | None = None,
        face_id: str = "",
        function: str = "",
    ) -> None:
        reason_bits = ["CAD/STL face assignment"]
        if row_index is not None:
            try:
                reason_bits.append(f"S{int(row_index)}")
            except Exception:
                pass
        face_text = str(face_id or "").strip()
        if face_text:
            reason_bits.append(face_text)
        function_text = _optical_solid_face_function_display(function) if function else ""
        if function_text:
            reason_bits.append(function_text)
        self._invalidate_preview_scene_trace(" ".join(reason_bits))
        self.last_system = None
        self.last_rays = None
        self._last_scene_bundle = None
        self._last_live_step_overlay_trace_rows = None
        self._last_live_step_overlay_trace_records = []
        self._last_live_step_overlay_scene_bundle = None
        self._live_step_overlay_trace_plan_cache = {}

    def _mark_plot_update_pending(self, _event=None) -> None:
        self._commit_history_capture()
        self._invalidate_preview_scene_trace()
        self._sync_trace_state_badge()
        if hasattr(self, "status_var"):
            self.status_var.set("Display settings changed. Click Update.")
        self._schedule_open3d_live_refresh("left panel edit")

    def _schedule_open3d_live_refresh(self, reason: str, *, delay_ms: int = 220) -> bool:
        inspector = getattr(self, "_three_d_inspector", None)
        if inspector is None:
            return False
        try:
            if not inspector.winfo_exists():
                self._three_d_inspector = None
                return False
        except Exception:
            self._three_d_inspector = None
            return False
        try:
            return bool(inspector.schedule_live_refresh(reason, delay_ms=delay_ms))
        except Exception as exc:
            self.append_debug(f"Open 3D live refresh scheduling failed: {exc}")
            return False

    def _on_display_plane_changed(self, _event=None) -> None:
        self._commit_history_capture()
        if hasattr(self, "display_orientation_var"):
            self.display_orientation_var.set(normalize_projection_plane(self.display_orientation_var.get()))
        self._sync_trace_state_badge()
        if hasattr(self, "status_var"):
            self.status_var.set("2D plane changed. Refreshing layout.")
        try:
            self.after_idle(self.refresh_plot)
        except Exception:
            self._mark_plot_update_pending()

    def _on_projection_display_mode_changed(self, _event=None) -> None:
        self._commit_history_capture()
        if hasattr(self, "projection_display_mode_var"):
            self.projection_display_mode_var.set(
                normalize_projection_display_mode(self.projection_display_mode_var.get())
            )
        self._sync_trace_state_badge()
        if hasattr(self, "status_var"):
            self.status_var.set(f"2D projection set to {self._current_projection_display_mode()}. Refreshing layout.")
        try:
            self.after_idle(self.refresh_plot)
        except Exception:
            self._mark_plot_update_pending()

    def _apply_operand_control_visibility(self, label: str) -> None:
        spec = self._merit_spec_for_label(label)
        if spec is None:
            return
        visible_controls = set(spec.controls)
        widget_groups = self.operand_control_widgets.get(label, {})
        for control_name, widgets in widget_groups.items():
            for widget in widgets:
                if control_name in visible_controls:
                    widget.grid()
                else:
                    widget.grid_remove()

    def _update_operand_setup_visibility(self) -> None:
        if not hasattr(self, "merit_mode_list"):
            return
        self._commit_history_capture()
        selected = {self.merit_mode_list.get(i) for i in self.merit_mode_list.curselection()}
        for label, frame in self.operand_setup_frames.items():
            visible = label in selected
            if visible:
                frame.grid()
            else:
                frame.grid_remove()

    def _pane_present(self, widget: tk.Widget) -> bool:
        if not hasattr(self, "main_pane"):
            return False
        widget_name = str(widget)
        return widget_name in {str(pane) for pane in self.main_pane.panes()}

    def toggle_left_sidebar(self) -> None:
        if not hasattr(self, "left_sidebar_host"):
            return
        if self._pane_present(self.left_sidebar_host):
            self.main_pane.forget(self.left_sidebar_host)
            self.left_restore_frame.grid()
            self._left_sidebar_collapsed = True
            message = "Left controls hidden."
        else:
            self.left_restore_frame.grid_remove()
            self.main_pane.insert(0, self.left_sidebar_host, weight=0)
            self._left_sidebar_collapsed = False
            message = "Left controls shown."
        self._initial_layout_passes = 40
        self._set_initial_pane_layout(force=True)
        if hasattr(self, "status_var"):
            self.status_var.set(message)

    def toggle_right_sidebar(self) -> None:
        if not hasattr(self, "right_sidebar_host"):
            return
        if self._pane_present(self.right_sidebar_host):
            self.main_pane.forget(self.right_sidebar_host)
            self.right_restore_frame.grid()
            self._right_sidebar_collapsed = True
            message = "Right panels hidden."
        else:
            self.right_restore_frame.grid_remove()
            self.main_pane.add(self.right_sidebar_host, weight=1)
            self._right_sidebar_collapsed = False
            message = "Right panels shown."
        self._initial_layout_passes = 40
        self._set_initial_pane_layout(force=True)
        if hasattr(self, "status_var"):
            self.status_var.set(message)

    def _set_initial_pane_layout(self, force: bool = False) -> None:
        self.update_idletasks()
        total_width = self.main_pane.winfo_width()
        if total_width < 500:
            self.after(100, self._set_initial_pane_layout)
            return
        try:
            left_visible = hasattr(self, "left_sidebar_host") and self._pane_present(self.left_sidebar_host)
            right_visible = hasattr(self, "right_sidebar_host") and self._pane_present(self.right_sidebar_host)
            left_width = max(240, min(360, int(total_width * 0.20)))
            right_width = max(300, min(460, int(total_width * 0.23)))
            if left_visible and right_visible:
                center_min = max(360, int(total_width * 0.42))
                side_total = left_width + right_width
                side_limit = max(240, total_width - center_min)
                if side_total > side_limit:
                    scale = max(0.35, side_limit / max(side_total, 1))
                    left_width = max(180, int(left_width * scale))
                    right_width = max(220, int(right_width * scale))
                self.main_pane.sashpos(0, left_width)
                self.main_pane.sashpos(1, max(left_width + 250, total_width - right_width))
            elif left_visible:
                self.main_pane.sashpos(0, left_width)
            elif right_visible:
                self.main_pane.sashpos(0, max(250, total_width - right_width))

            if hasattr(self, "center_panel"):
                total_height = self.center_panel.winfo_height()
                if total_height >= 360:
                    self.center_panel.sashpos(0, int(total_height * 0.36))
            if not force:
                self._initial_layout_passes += 1
        except Exception:
            self.after(100, self._set_initial_pane_layout)

    def _maybe_refresh_initial_pane_layout(self, _event=None) -> None:
        if self._initial_layout_passes >= 40:
            return
        self.after(100, self._set_initial_pane_layout)

    def _layout_menu_category(self, name: str) -> str:
        return layout_menu_category(name, self.layout_files.get(name))

    def _example_menu_category(self, name: str) -> str:
        return example_menu_category(name, self.example_files.get(name))

    def _refresh_selector_menus(self) -> None:
        if self.layout_menu is not None:
            self.layout_menu.delete(0, "end")
            self._layout_category_menus = []
            if self.layout_names:
                categories = {category: [] for category in LAYOUT_CATEGORY_ORDER}
                for name in self.layout_names:
                    category = self._layout_menu_category(name)
                    categories.setdefault(category, []).append(name)
                for category, names in categories.items():
                    if not names:
                        continue
                    submenu = tk.Menu(self.layout_menu, tearoff=0)
                    self._layout_category_menus.append(submenu)
                    for name in names:
                        submenu.add_command(
                            label=name,
                            command=lambda value=name: self.load_layout_by_name(value),
                        )
                    self.layout_menu.add_cascade(label=category, menu=submenu)
            else:
                self.layout_menu.add_command(label="No common layouts found", state="disabled")

        self._refresh_insert_component_menu()

        if self.machine_vision_menu is not None:
            self.machine_vision_menu.delete(0, "end")
            if self.machine_vision_names:
                for name in self.machine_vision_names:
                    self.machine_vision_menu.add_command(
                        label=name,
                        command=lambda value=name: self.load_layout_by_name(value),
                    )
            else:
                self.machine_vision_menu.add_command(label="No machine-vision layouts found", state="disabled")

        if self.example_menu is not None:
            self.example_menu.delete(0, "end")
            self._example_category_menus = []
            self._zemax_example_category_menus = []
            if self.example_names:
                categories = {category: [] for category in EXAMPLE_CATEGORY_ORDER}
                for name in self.example_names:
                    category = self._example_menu_category(name)
                    categories.setdefault(category, []).append(name)
                for category, names in categories.items():
                    if not names:
                        continue
                    submenu = tk.Menu(self.example_menu, tearoff=0)
                    self._example_category_menus.append(submenu)
                    for name in names:
                        submenu.add_command(
                            label=name,
                            command=lambda value=name: self.load_example_by_name(value),
                        )
                    self.example_menu.add_cascade(label=category, menu=submenu)
            if self.example_names and self.zemax_example_files:
                self.example_menu.add_separator()
            if self.zemax_example_files:
                self._refresh_zemax_example_menu(self.example_menu)
            elif not self.example_names:
                self.example_menu.add_command(label="No examples found", state="disabled")

    def _insertable_common_layout_names(self) -> list[str]:
        names: list[str] = []
        for name in self.layout_names:
            path = self.layout_files.get(name)
            if path is None:
                continue
            info: dict[str, object] = {}
            try:
                info = _load_python_data(path)
            except Exception:
                info = {}
            if self._is_insertable_common_layout(name, [], info):
                names.append(name)
        return sorted(names, key=str.lower)

    def _refresh_insert_component_menu(self) -> None:
        menu = self._insert_component_menu
        if menu is None:
            return
        menu.delete(0, "end")
        names = self._insertable_common_layout_names()
        if not names:
            menu.add_command(label="No insertable common components found", state="disabled")
            return
        for name in names:
            menu.add_command(
                label=name,
                command=lambda value=name: self.insert_layout_component_by_name(value),
            )

    def _refresh_zemax_example_menu(self, parent_menu: tk.Menu) -> None:
        zemax_menu = tk.Menu(parent_menu, tearoff=0)
        self._zemax_example_category_menus.append(zemax_menu)
        if not self.zemax_example_files:
            zemax_menu.add_command(label=f"No .zmx files found in {ZEMAX_ATTACHMENT_DIR}", state="disabled")
            parent_menu.add_cascade(label="Zemax Prescriptions (attachment)", menu=zemax_menu)
            return

        grouped: dict[str, list[tuple[str, Path]]] = {}
        for label, path in self.zemax_example_files.items():
            try:
                relative = path.relative_to(ZEMAX_ATTACHMENT_DIR)
            except ValueError:
                relative = Path(label)
            group = relative.parent.as_posix() if relative.parent != Path(".") else "Top Level"
            grouped.setdefault(group, []).append((relative.name, path))

        for group in sorted(grouped, key=lambda value: (value != "Top Level", value.lower())):
            submenu = tk.Menu(zemax_menu, tearoff=0)
            self._zemax_example_category_menus.append(submenu)
            for item_label, path in sorted(grouped[group], key=lambda item: item[0].lower()):
                submenu.add_command(
                    label=item_label,
                    command=lambda value=path: self.load_zemax_example_file(value),
                )
            zemax_menu.add_cascade(label=group, menu=submenu)
        parent_menu.add_cascade(label="Zemax Prescriptions (attachment)", menu=zemax_menu)

    def load_layouts(self) -> None:
        discovered = _discover_layouts(LAYOUTS_DIR, default_layout_title=DEFAULT_LAYOUT_TITLE)
        self.layout_files = dict(discovered.layout_files)
        self.machine_vision_files = dict(discovered.machine_vision_files)
        self.layout_names = list(discovered.layout_names)
        self.machine_vision_names = list(discovered.machine_vision_names)
        self.layout_var.set("Common Optical Layout")
        self.machine_vision_var.set("Machine Vision Lens")
        self._refresh_selector_menus()

    def load_examples(self) -> None:
        discovered = _discover_examples(EXAMPLES_DIR, ZEMAX_TESTING_DIR)
        self.example_files = dict(discovered.example_files)
        self.example_names = list(discovered.example_names)
        self.zemax_example_files = dict(discovered.zemax_example_files)
        self.example_var.set("Examples")
        self._refresh_selector_menus()

    def set_analysis_mode(self, mode: str) -> None:
        self.selected_analysis_modes = [] if mode == "none" else [mode]
        self.analysis_mode = self.selected_analysis_modes[0] if self.selected_analysis_modes else "none"
        self.secondary_analysis_mode = None
        self._sync_analysis_mode_buttons()
        mode_label_map = {
            "none": "2D",
            "spot": "Spot",
            "psf": "PSF",
            "psf_map": "PSFMap",
            "rms": "RMS",
            "field_curvature": "FC/Dist",
            "relative_illumination": "Illum",
            "polarization": "Polarization",
            "lateral_color": "LatClr",
            "detector_map": "DetMap",
            "coherent_detector": "CohDet",
            "branch_field": "BField",
            "diffraction_detector": "Diffr",
            "field_map": "FieldMap",
            "illum_map": "IllumMap",
            "wavefront_map": "WfeMap",
            "atmosphere": "Atmos",
            "pupil": "Pupil",
            "seidel": "Seidel",
            "wavefront": "Wavefront",
            "zernike": "Zernike",
            "interferogram": "Interferogram",
            "tolerance_compare": "TolCmp",
            "mtf": "MTF",
        }
        mode_label = mode_label_map.get(mode, mode or "2D")
        if hasattr(self, "status_var"):
            self.status_var.set(f"Analysis mode set to {mode_label}. Click Update.")
        self.append_progress(f"Mode selected: {mode_label} (pending update).")

    def set_layout_preview_mode(self, mode: str) -> None:
        self.layout_preview_mode = "none"
        if hasattr(self, "layout_preview_mode_var"):
            self.layout_preview_mode_var.set(self.layout_preview_mode)
        mode_label = "2D"
        if hasattr(self, "status_var"):
            self.status_var.set(f"Layout mode set to {mode_label}. Click Update.")
        self.append_progress(f"Layout mode selected: {mode_label} (pending update).")

    def _requested_trace_mode(self) -> str:
        trace_mode_var = self.__dict__.get("trace_mode_var")
        if trace_mode_var is None:
            value = str(self.__dict__.get("trace_mode", "Auto")).strip()
        else:
            value = str(trace_mode_var.get()).strip()
        if value in {"Auto", "Sequential", "Folded Preview", "Non-Sequential Preview"}:
            return value
        return "Auto"

    def _resolved_trace_mode(self, *, system=None) -> dict[str, object]:
        requested = self._requested_trace_mode()
        can_folded = self._can_build_folded_layout() and bool(self.rows)
        intent = resolve_trace_intent(
            self.rows,
            {
                "source_model": self._current_source_model(),
                "scene_sources": getattr(self, "layout_scene_source_specs", []),
            },
            requested=requested,
            can_folded=can_folded,
            ns_trace_available=system is None or hasattr(system, "NsTrace"),
            has_physical_source=self._current_source_model() != SOURCE_MODEL_DEFAULT,
            nonseq_energy_probability=self._current_nonseq_energy_probability(),
            nonseq_target_surface_index=self._current_nonseq_target_surface_index(),
        )
        return intent.as_dict()

    def _sync_trace_state_badge(self, trace_state: dict[str, object] | None = None) -> None:
        badge_var = self.__dict__.get("trace_state_badge_var")
        if badge_var is None:
            return
        if trace_state is None:
            try:
                trace_state = self._resolved_trace_mode(system=self.last_system)
            except Exception:
                trace_state = {"requested": self._requested_trace_mode(), "active": "Unknown"}
        requested = str(trace_state.get("requested", "Auto") or "Auto")
        active = str(trace_state.get("active", "") or "")
        if active and requested != active:
            label = f"{requested} -> {active}"
        else:
            label = active or requested
        try:
            badge_var.set(f"Scene: {label}")
        except Exception:
            pass

    def _on_trace_mode_changed(self, _event=None) -> None:
        self.trace_mode = self._requested_trace_mode()
        trace_state = self._resolved_trace_mode()
        active = str(trace_state.get("active", "Sequential"))
        self._sync_trace_state_badge(trace_state)
        if hasattr(self, "status_var"):
            self.status_var.set(f"Trace mode set to {self.trace_mode} -> {active}. Click Update.")
        self.append_progress(f"Trace mode selected: {self.trace_mode} -> {active} (pending update).")

    def _current_nonseq_ns_limit(self) -> int:
        var = self.__dict__.get("nonseq_ns_limit_var")
        try:
            value = int(float(var.get())) if var is not None else 200
        except Exception:
            value = 200
        return max(1, min(int(value), 100000))

    def _current_nonseq_energy_probability(self) -> bool:
        var = self.__dict__.get("nonseq_energy_probability_var")
        try:
            return bool(var.get()) if var is not None else False
        except Exception:
            return False

    @staticmethod
    def _normalize_folded_detector_policy_label(value: object) -> str:
        text = str(value or "").strip()
        if text in FOLDED_DETECTOR_POLICY_VALUES:
            return text
        normalized = text.lower().replace("-", " ").replace("_", " ")
        if normalized in {"display", "display path", "display compatibility", "compatibility", "legacy", "authoritative"}:
            return FOLDED_DETECTOR_POLICY_DISPLAY
        return FOLDED_DETECTOR_POLICY_DEFAULT

    def _current_folded_detector_policy_label(self) -> str:
        var = self.__dict__.get("folded_detector_policy_var")
        value = str(var.get()).strip() if var is not None else FOLDED_DETECTOR_POLICY_DEFAULT
        return self._normalize_folded_detector_policy_label(value)

    def _current_folded_detector_policy(self) -> str:
        if self._current_folded_detector_policy_label() == FOLDED_DETECTOR_POLICY_DISPLAY:
            return FOLDED_TERMINAL_POLICY_DISPLAY_COMPATIBILITY
        return FOLDED_TERMINAL_POLICY_TRACE_EVENTS

    def _folded_detector_policy_control_enabled(self) -> bool:
        try:
            trace_state = self._resolved_trace_mode()
            return bool(trace_state.get("use_folded")) or self._can_build_folded_layout()
        except Exception:
            return False

    def _current_nonseq_target_surface_index(self) -> int | None:
        var = self.__dict__.get("nonseq_target_surface_var")
        value = str(var.get()).strip() if var is not None else "Auto"
        if not value or value == "Auto":
            return None
        try:
            index = int(value.split(":", 1)[0].strip())
        except Exception:
            return None
        if 0 <= index < len(self.rows):
            return index
        return None

    def _apply_nonseq_trace_settings(self, system):
        old_energy = getattr(system, "energy_probability", 0)
        old_limit = getattr(system, "NsLimit", 200)
        old_target = getattr(system, "Targ_Surf", len(self.rows))
        try:
            system.energy_probability = 1 if self._current_nonseq_energy_probability() else 0
            system.NsLimit = self._current_nonseq_ns_limit()
            target_index = self._current_nonseq_target_surface_index()
            if target_index is None:
                if hasattr(system, "TargSurfRest"):
                    system.TargSurfRest()
                else:
                    system.Targ_Surf = getattr(system, "n", len(self.rows))
            elif hasattr(system, "TargSurf"):
                system.TargSurf(int(target_index))
            else:
                system.Targ_Surf = int(target_index) + 1
        except Exception as exc:
            self.append_debug(f"Non-sequential trace settings ignored: {_short_error_message(exc)}")

        def restore() -> None:
            try:
                system.energy_probability = old_energy
                system.NsLimit = old_limit
                system.Targ_Surf = old_target
            except Exception:
                pass

        return restore

    def _on_source_model_changed(self, _event=None) -> None:
        source_model = self._current_source_model()
        if source_model == SOURCE_MODEL_DEFAULT:
            pattern = self._current_pupil_pattern_label()
            detail = f"pupil pattern {pattern}"
            if pattern == "R-theta":
                detail = f"{detail}, r {self._current_pupil_rad():.6g}, theta {self._current_pupil_theta():.6g} deg"
        elif source_model == "Gaussian beam":
            try:
                beam = self._current_gaussian_beam_input()
                detail = (
                    f"Gaussian beam, w0 {float(beam.waist_radius_mm):.6g} mm, "
                    f"waist offset {float(beam.waist_offset_mm):.6g} mm, "
                    f"M2 {float(beam.m2):.6g}"
                )
            except Exception as exc:
                detail = f"Gaussian beam input invalid: {_short_error_message(exc)}"
        elif source_model == "Collimated disk source":
            ox, oy, oz = self._current_source_origin()
            cone_deg = self._current_source_cone_angle()
            cone_note = f", cone {cone_deg:.6g} deg" if cone_deg > 1e-12 else ""
            detail = (
                f"Collimated disk source, radius {self._current_source_radius():.6g} mm, "
                f"origin ({ox:.6g}, {oy:.6g}, {oz:.6g}) mm{cone_note}"
            )
        elif source_model == "Random point cone":
            ox, oy, oz = self._current_source_origin()
            detail = (
                f"Random point cone, cone {self._current_source_cone_angle():.6g} deg, "
                f"origin ({ox:.6g}, {oy:.6g}, {oz:.6g}) mm"
            )
        else:
            ox, oy, oz = self._current_source_origin()
            weight_note = ""
            weight = self._current_source_angular_weight()
            if source_model in {"Random circle source", "Random square source"} and weight != SOURCE_ANGULAR_WEIGHT_DEFAULT:
                weight_note = f", {weight}"
            detail = (
                f"{source_model}, radius {self._current_source_radius():.6g} mm, "
                f"cone {self._current_source_cone_angle():.6g} deg{weight_note}, "
                f"origin ({ox:.6g}, {oy:.6g}, {oz:.6g}) mm"
            )
        if hasattr(self, "status_var"):
            self.status_var.set(f"Source model set to {detail}. Click Update.")
        self._update_source_summary()
        self._sync_left_mode_controls()
        self.append_progress(f"Source model selected: {detail} (pending update).")
        self._mark_plot_update_pending()

    def _main_scene_source_manager_dialog(self) -> MainSceneSourceManagerDialog:
        dialog = self.__dict__.get("_main_scene_source_manager_dialog_instance")
        if dialog is None:
            dialog = MainSceneSourceManagerDialog(
                self,
                source_model_values=SOURCE_MODEL_VALUES,
                source_model_default=SOURCE_MODEL_DEFAULT,
                source_direction_preset_values=SOURCE_DIRECTION_PRESET_VALUES,
                source_angular_weight_default=SOURCE_ANGULAR_WEIGHT_DEFAULT,
                source_angular_weight_values=SOURCE_ANGULAR_WEIGHT_VALUES,
                source_row_order_default=SOURCE_ROW_ORDER_DEFAULT,
                source_row_order_before_object=SOURCE_ROW_ORDER_BEFORE_OBJECT,
                source_row_order_after_object=SOURCE_ROW_ORDER_AFTER_OBJECT,
                normalize_source_row_order=normalize_source_row_order,
            )
            self._main_scene_source_manager_dialog_instance = dialog
        return dialog

    def open_scene_source_manager(
        self,
        selected_source_id: str | None = None,
        *,
        aim_row_index: int | None = None,
        aim_face_id: str = "",
    ) -> None:
        self._main_scene_source_manager_dialog().open_scene_source_manager(
            selected_source_id=selected_source_id,
            aim_row_index=aim_row_index,
            aim_face_id=aim_face_id,
        )


    def toggle_analysis_mode(self, mode: str) -> None:
        current = list(self.selected_analysis_modes)
        if mode in current:
            current.remove(mode)
        else:
            current.append(mode)
            if len(current) > 2:
                current = current[-2:]
        self.selected_analysis_modes = current
        self.analysis_mode = current[0] if current else "none"
        self.secondary_analysis_mode = current[1] if len(current) > 1 else None
        self._sync_analysis_mode_buttons()
        self._sync_left_mode_controls()
        label = " + ".join(self._analysis_mode_label(m) for m in current) if current else "2D"
        if hasattr(self, "status_var"):
            self.status_var.set(f"Analysis selection set to {label}. Click Update.")
        self.append_progress(f"Analysis selection updated: {label} (pending update).")

    def _sync_analysis_mode_buttons(self) -> None:
        if hasattr(self, "layout_preview_mode_var"):
            self.layout_preview_mode_var.set(self.layout_preview_mode)
        for mode, var in getattr(self, "analysis_mode_vars", {}).items():
            var.set(mode in self.selected_analysis_modes)

    def _analysis_mode_label(self, mode: str) -> str:
        return analysis_mode_label(mode)

    def _manual_update_plot(self) -> None:
        # Commit any pending inline table edit before refreshing.
        if self.editor is not None:
            row_id = self._editor_row_id
            field = self._editor_field
            if row_id is not None and field is not None:
                self._finish_edit(row_id, field, quiet=True)
        self._sync_object_controls()
        mode = (self.layout_preview_mode or "none").strip()
        if self.selected_analysis_modes:
            mode_label = " + ".join(self._analysis_mode_label(item) for item in self.selected_analysis_modes)
        else:
            mode_label = self._analysis_mode_label(mode)
        modes_with_internal_progress = {
            "psf",
            "psf_map",
            "pupil",
            "seidel",
            "wavefront",
            "zernike",
            "field_curvature",
            "relative_illumination",
            "lateral_color",
            "field_map",
            "illum_map",
            "wavefront_map",
            "atmosphere",
            "interferogram",
            "tolerance_compare",
            "mtf",
        }
        if any(item in modes_with_internal_progress for item in self.selected_analysis_modes):
            self.append_progress(f"Display update requested ({mode_label}).")
            self.refresh_plot()
            self.append_progress(f"Display update completed ({mode_label}).")
            return
        self._begin_analysis_progress("Display update")
        self._update_analysis_progress(f"Refreshing {mode_label}", 1, 2)
        self.refresh_plot()
        self._update_analysis_progress("Rendering", 2, 2)
        self._finish_analysis_progress("Display update", success=True)

    def _open_plot_axis_once(self, target_ax) -> None:
        if target_ax not in {self.ax, self._analysis_ax, *self._analysis_axes}:
            return
        now = time.monotonic()
        if now - self._last_viewer_open_time < 0.4:
            return
        self._last_viewer_open_time = now
        self._open_high_res_plot_in_system_viewer(target_ax)

    def _plot_hover_hint_text(self, target_ax, x_display: float | None = None, y_display: float | None = None) -> str:
        if target_ax is self.ax:
            if x_display is not None and y_display is not None:
                ray_index = self._find_layout_pick_ray(float(x_display), float(y_display))
                if ray_index is not None:
                    return self._ray_terminal_hint_text(ray_index)
                row_index = self._find_layout_pick_row(float(x_display), float(y_display))
                if row_index is not None and 0 <= int(row_index) < len(self.rows):
                    row = self.rows[int(row_index)]
                    name = str(getattr(row, "name", "") or getattr(row, "surface", "") or "").strip()
                    return f"S{int(row_index)} {name}: click to select"
            return "Click surface to select, ray to inspect; empty area opens viewer"
        if target_ax is not None:
            return "Click to open in viewer"
        return ""

    def _on_plot_canvas_motion(self, event) -> None:
        target_ax = getattr(event, "inaxes", None)
        if target_ax not in self._hover_hint_artists:
            target_ax = None
        x_display = getattr(event, "x", None)
        y_display = getattr(event, "y", None)
        message = self._plot_hover_hint_text(target_ax, x_display, y_display)
        if target_ax is not None:
            self._set_hover_hint_text(target_ax, message)
        if target_ax is self.ax and message and message != self._last_plot_hover_message:
            self._last_plot_hover_message = message
            if message.startswith("Ray "):
                self.status_var.set(message)
        if target_ax is self._hover_axis:
            if hasattr(self, "canvas"):
                self.canvas.draw_idle()
            return
        self._set_hover_axis(target_ax)

    def _on_plot_canvas_leave(self, _event=None) -> None:
        self._last_plot_hover_message = ""
        self._set_hover_axis(None)

    def _on_plot_widget_click(self, event) -> str | None:
        try:
            self.canvas.draw()
            renderer = self.figure.canvas.get_renderer()
            widget = self.canvas.get_tk_widget()
            x_display = float(event.x)
            y_display = float(widget.winfo_height() - event.y)
            if self.ax is not None and self.ax in self.figure.axes:
                if self.ax.get_window_extent(renderer).contains(x_display, y_display):
                    ray_index = self._find_layout_pick_ray(x_display, y_display)
                    if ray_index is not None:
                        self._select_ray_inspector_ray(ray_index)
                        return "break"
                    row_index = self._find_layout_pick_row(x_display, y_display)
                    if row_index is not None:
                        self._select_table_row(row_index)
                        return "break"
                    self._open_plot_axis_once(self.ax)
                    return "break"
            for axis in self._analysis_axes or ([self._analysis_ax] if self._analysis_ax is not None else []):
                if axis is not None and axis in self.figure.axes:
                    if axis.get_window_extent(renderer).contains(x_display, y_display):
                        self._open_plot_axis_once(axis)
                        return "break"
        except Exception as exc:
            self.append_debug(f"Plot viewer dispatch failed: {exc}")
        return None

    @staticmethod

    def _find_layout_pick_row(self, x_display: float, y_display: float) -> int | None:
        if self.ax is None or not self._layout_pick_regions:
            return None
        return find_nearest_pick_region(
            (x_display, y_display),
            self._layout_pick_regions,
            transform_points=self.ax.transData.transform,
        )

    def _find_layout_pick_ray(self, x_display: float, y_display: float) -> int | None:
        if self.ax is None or not self._layout_ray_pick_regions:
            return None
        return find_nearest_ray_region(
            (x_display, y_display),
            self._layout_ray_pick_regions,
            transform_points=self.ax.transData.transform,
        )

    def _select_ray_inspector_ray(self, ray_index: int) -> None:
        try:
            index = int(ray_index)
        except Exception:
            return
        if self._ray_inspector_window is None or not self._ray_inspector_window.winfo_exists():
            self.open_ray_inspector()
        else:
            self._refresh_ray_inspector()
        table = self._ray_inspector_ray_table
        if table is None:
            return
        iid = str(index)
        if not table.exists(iid):
            self.status_var.set(f"Ray {index} is not available in the current Ray Inspector data.")
            return
        self._layout_selected_ray_index = index
        table.selection_set(iid)
        table.focus(iid)
        table.see(iid)
        self._populate_ray_inspector_hits()
        self._update_layout_selection_overlay()
        self.status_var.set(self._ray_terminal_hint_text(index, label=f"Selected ray {index} in Ray Inspector"))

    def _draw_layout_selected_ray_overlay(self, ray_index: int) -> bool:
        ray = self._layout_projected_rays_by_index.get(int(ray_index))
        if ray is None or self.ax is None:
            return False
        pts = np.asarray(getattr(ray, "points_2d", []), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 1 or pts.shape[1] < 2:
            return False
        pts = pts[np.all(np.isfinite(pts[:, :2]), axis=1)]
        if pts.shape[0] < 1:
            return False
        artists: list = []
        if pts.shape[0] == 1:
            artists.append(
                self.ax.scatter(
                    pts[:, 0],
                    pts[:, 1],
                    s=58,
                    c="#f97316",
                    edgecolors="white",
                    linewidths=1.4,
                    zorder=982,
                )
            )
        else:
            underlay, = self.ax.plot(
                pts[:, 0],
                pts[:, 1],
                color="white",
                linewidth=6.0,
                alpha=0.94,
                zorder=980,
            )
            overlay, = self.ax.plot(
                pts[:, 0],
                pts[:, 1],
                color="#f97316",
                linewidth=2.8,
                alpha=1.0,
                zorder=981,
            )
            artists.extend([underlay, overlay])
        for ordinal, (label, point, event_kind) in enumerate(projected_ray_event_label_items(ray, limit=14)):
            marker_size = 42 if event_kind == "terminal" else 34
            artists.append(
                self.ax.scatter(
                    [point[0]],
                    [point[1]],
                    s=marker_size,
                    c="#f97316",
                    edgecolors="white",
                    linewidths=1.0,
                    zorder=984,
                )
            )
            offset_y = 7 if ordinal % 2 == 0 else -15
            artists.append(
                self.ax.annotate(
                    label,
                    xy=(float(point[0]), float(point[1])),
                    xytext=(8, offset_y),
                    textcoords="offset points",
                    fontsize=8,
                    color="#111827",
                    zorder=985,
                    clip_on=True,
                    bbox={
                        "boxstyle": "round,pad=0.24",
                        "facecolor": "white",
                        "edgecolor": "#f97316",
                        "linewidth": 0.8,
                        "alpha": 0.84,
                    },
                )
            )
        self._layout_selection_artists = artists
        return True

    def _update_layout_selection_overlay(self, row_index: int | None = None) -> None:
        self._clear_layout_selection_overlay()
        if self.ax is None:
            if hasattr(self, "canvas"):
                self.canvas.draw_idle()
            return
        if row_index is None:
            if self._layout_selected_ray_index is not None:
                if self._draw_layout_selected_ray_overlay(int(self._layout_selected_ray_index)):
                    self.canvas.draw_idle()
                    return
                self._layout_selected_ray_index = None
            row_index = self._current_selected_row_index()
        if row_index is None:
            if hasattr(self, "canvas"):
                self.canvas.draw_idle()
            return
        polylines = self._layout_pick_regions.get(int(row_index))
        if not polylines:
            if hasattr(self, "canvas"):
                self.canvas.draw_idle()
            return
        artists: list = []
        for polyline in polylines:
            pts = np.asarray(polyline, dtype=float)
            if pts.ndim != 2 or pts.shape[0] == 0:
                continue
            if pts.shape[0] == 1:
                artists.append(
                    self.ax.scatter(
                        pts[:, 0],
                        pts[:, 1],
                        s=55,
                        c="#f97316",
                        edgecolors="white",
                        linewidths=1.4,
                        zorder=950,
                    )
                )
                continue
            underlay, = self.ax.plot(
                pts[:, 0],
                pts[:, 1],
                color="white",
                linewidth=5.0,
                alpha=0.92,
                zorder=940,
            )
            overlay, = self.ax.plot(
                pts[:, 0],
                pts[:, 1],
                color="#f97316",
                linewidth=2.2,
                alpha=0.98,
                zorder=941,
            )
            artists.extend([underlay, overlay])
        self._layout_selection_artists = artists
        self.canvas.draw_idle()

    def _configure_plot_hover_hints(self) -> None:
        self._hover_hint_artists = {}
        self._hover_axis = None
        if hasattr(self, "canvas"):
            self.canvas.get_tk_widget().configure(cursor="")
        candidate_axes = [self.ax]
        candidate_axes.extend([axis for axis in self._analysis_axes if axis is not None])
        if self._analysis_ax is not None and self._analysis_ax not in candidate_axes:
            candidate_axes.append(self._analysis_ax)
        for axis in candidate_axes:
            if axis is None:
                continue
            highlight = Rectangle(
                (0.0, 0.0),
                1.0,
                1.0,
                transform=axis.transAxes,
                facecolor="#60a5fa",
                edgecolor="#2563eb",
                linewidth=1.0,
                alpha=0.06,
                visible=False,
                zorder=1000,
            )
            axis.add_patch(highlight)
            hint_text = (
                "Click surface to select, ray to inspect; empty area opens viewer"
                if axis is self.ax
                else "Click to open in viewer"
            )
            hint = axis.text(
                0.5,
                0.985,
                hint_text,
                transform=axis.transAxes,
                ha="center",
                va="top",
                fontsize=8,
                color="#334155",
                visible=False,
                zorder=1001,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.8},
            )
            self._hover_hint_artists[axis] = (highlight, hint)

    def _set_hover_hint_text(self, axis, text: str) -> None:
        artists = self._hover_hint_artists.get(axis)
        if not artists:
            return
        _highlight, hint = artists
        try:
            hint.set_text(str(text or ""))
        except Exception:
            pass

    def _set_hover_axis(self, axis) -> None:
        self._hover_axis = axis
        for current_ax, artists in self._hover_hint_artists.items():
            active = current_ax is axis
            for artist in artists:
                artist.set_visible(active)
        if hasattr(self, "canvas"):
            cursor = "hand2" if axis is not None else ""
            self.canvas.get_tk_widget().configure(cursor=cursor)
            self.canvas.draw_idle()

    @staticmethod
    def _viewer_open_command(image_path: Path) -> list[str] | None:
        preferred = os.getenv("KRAKEN_IMAGE_VIEWER", "").strip()
        if preferred:
            parts = preferred.split()
            binary = parts[0]
            if shutil.which(binary):
                return [*parts, str(image_path)]
        for binary in ("nomacs-x11", "nomacs"):
            if shutil.which(binary):
                return [binary, str(image_path)]
        if sys.platform == "darwin":
            return ["open", str(image_path)]
        if os.name == "nt":
            return None
        if shutil.which("xdg-open"):
            return ["xdg-open", str(image_path)]
        if shutil.which("gio"):
            return ["gio", "open", str(image_path)]
        for binary in ("imv", "feh", "eog", "gwenview", "ristretto", "pqiv", "sxiv", "nsxiv"):
            if shutil.which(binary):
                return [binary, str(image_path)]
        return None

    def _open_image_with_system_viewer(self, image_path: Path) -> None:
        if os.name == "nt":
            os.startfile(str(image_path))  # type: ignore[attr-defined]
            return
        command = self._viewer_open_command(image_path)
        if command is None:
            raise RuntimeError("No system image viewer command found.")
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

    def _open_high_res_plot_in_system_viewer(self, target_ax=None) -> None:
        previous_hover_axis = self._hover_axis if self._hover_axis in self._hover_hint_artists else None
        hidden_axes: list[tuple[object, bool]] = []
        try:
            # Hide hover hint overlays so exported images only contain plot content.
            self._set_hover_axis(None)
            out_dir = SCREENSHOT_DIR
            try:
                out_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                out_dir = VIEWER_EXPORT_DIR
                out_dir.mkdir(parents=True, exist_ok=True)
            if target_ax is self.ax:
                axis_label = "layout"
            elif target_ax in self._analysis_axes:
                axis_index = self._analysis_axes.index(target_ax) + 1
                axis_label = f"analysis{axis_index}"
            else:
                axis_label = "analysis"
            image_path = out_dir / ("2D.png" if axis_label == "layout" else f"kraken_plot_{axis_label}.png")

            self.canvas.draw()
            if target_ax is not None and target_ax in self.figure.axes:
                renderer = self.figure.canvas.get_renderer()
                tight_bbox = target_ax.get_tightbbox(renderer)
                if tight_bbox is not None:
                    # savefig expects bbox_inches in inches, convert from display pixels
                    bbox = tight_bbox.transformed(self.figure.dpi_scale_trans.inverted()).padded(0.08)
                else:
                    fig_w, fig_h = self.figure.get_size_inches()
                    pos = target_ax.get_position()
                    bbox = Bbox.from_extents(
                        float(pos.x0) * fig_w,
                        float(pos.y0) * fig_h,
                        float(pos.x1) * fig_w,
                        float(pos.y1) * fig_h,
                    ).expanded(1.08, 1.12)
                for axis in self.figure.axes:
                    if axis is target_ax:
                        continue
                    hidden_axes.append((axis, bool(axis.get_visible())))
                    axis.set_visible(False)
                self.figure.savefig(image_path, dpi=320, bbox_inches=bbox)
            else:
                self.figure.savefig(image_path, dpi=320)

            self._open_image_with_system_viewer(image_path)
            self.status_var.set(f"Opened image in system viewer: {image_path.name}")
            self.append_progress(f"Opened high-res image: {image_path}")
        except Exception as exc:
            self.append_debug(f"High-resolution viewer launch failed: {exc}")
        finally:
            if hidden_axes:
                for axis, visible in hidden_axes:
                    try:
                        axis.set_visible(visible)
                    except Exception:
                        pass
                try:
                    self.canvas.draw_idle()
                except Exception:
                    pass
            if previous_hover_axis is not None:
                self._set_hover_axis(previous_hover_axis)


    @staticmethod
    def _flatten_table_item_args(*items: object) -> list[str]:
        flattened: list[str] = []
        for item in items:
            if item is None:
                continue
            if isinstance(item, str):
                if item:
                    flattened.append(item)
                continue
            if isinstance(item, (list, tuple, set)):
                flattened.extend(KrakenLayoutEditor._flatten_table_item_args(*item))
                continue
            text = str(item)
            if text:
                flattened.append(text)
        return flattened

    def _install_border_only_table_selection(self) -> None:
        self._native_table_selection = self.table.selection
        self._native_table_selection_set = self.table.selection_set
        self._native_table_selection_remove = self.table.selection_remove

        def selection() -> tuple[str, ...]:
            selected = tuple(item for item in self._table_selected_items if self.table.exists(item))
            if len(selected) != len(self._table_selected_items):
                self._table_selected_items = list(selected)
            return selected

        def selection_set(*items: object) -> None:
            ordered: list[str] = []
            seen: set[str] = set()
            for item in self._flatten_table_item_args(*items):
                if self.table.exists(item) and item not in seen:
                    ordered.append(item)
                    seen.add(item)
            self._table_selected_items = ordered
            self._clear_native_table_selection()
            self._schedule_custom_table_selection_changed()

        def selection_remove(*items: object) -> None:
            remove = set(self._flatten_table_item_args(*items))
            if remove:
                self._table_selected_items = [item for item in self._table_selected_items if item not in remove]
            self._clear_native_table_selection()
            self._schedule_custom_table_selection_changed()

        def selection_add(*items: object) -> None:
            selected = list(selection())
            seen = set(selected)
            for item in self._flatten_table_item_args(*items):
                if self.table.exists(item) and item not in seen:
                    selected.append(item)
                    seen.add(item)
            self._table_selected_items = selected
            self._clear_native_table_selection()
            self._schedule_custom_table_selection_changed()

        def selection_toggle(*items: object) -> None:
            selected = list(selection())
            selected_set = set(selected)
            for item in self._flatten_table_item_args(*items):
                if not self.table.exists(item):
                    continue
                if item in selected_set:
                    selected_set.remove(item)
                    selected = [candidate for candidate in selected if candidate != item]
                else:
                    selected.append(item)
                    selected_set.add(item)
            self._table_selected_items = selected
            self._clear_native_table_selection()
            self._schedule_custom_table_selection_changed()

        self.table.selection = selection  # type: ignore[method-assign]
        self.table.selection_set = selection_set  # type: ignore[method-assign]
        self.table.selection_remove = selection_remove  # type: ignore[method-assign]
        self.table.selection_add = selection_add  # type: ignore[method-assign]
        self.table.selection_toggle = selection_toggle  # type: ignore[method-assign]

    def _clear_native_table_selection(self) -> None:
        native_selection = self._native_table_selection
        native_remove = self._native_table_selection_remove
        if native_selection is None or native_remove is None:
            return
        try:
            selected = tuple(native_selection())
        except Exception:
            selected = ()
        if selected:
            try:
                native_remove(*selected)
            except Exception:
                pass

    def _schedule_custom_table_selection_changed(self) -> None:
        if self._table_selection_after_id is not None:
            return
        try:
            self._table_selection_after_id = self.after_idle(self._emit_custom_table_selection_changed)
        except tk.TclError:
            self._table_selection_after_id = None

    def _emit_custom_table_selection_changed(self) -> None:
        self._table_selection_after_id = None
        self._on_table_selection_changed()

    def _current_selected_row_index(self) -> int | None:
        items = self.table.selection()
        if not items:
            return None
        return self._table_item_row_index(items[0])

    def _on_table_selection_changed(self, _event: tk.Event | None = None) -> None:
        self._update_selection_row_borders()
        selected = self.table.selection()
        if selected:
            source_record = self._table_item_scene_record(selected[0])
            if source_record is not None and getattr(source_record, "kind", "") == SCENE_ROW_SOURCE:
                metadata = dict(getattr(source_record, "metadata", {}) or {})
                model = str(metadata.get("model", "") or "Source")
                rays = metadata.get("ray_count", "-")
                self._sync_surface_selection(None, from_table=False)
                self.status_var.set(
                    f"Selected {getattr(source_record, 'label', 'Src')}: {getattr(source_record, 'name', 'Source')} "
                    f"({model}, rays={rays}). Edit source parameters in the Source panel; this row does not consume a KrakenOS surface index."
                )
                return
        self._sync_surface_selection(self._current_selected_row_index(), from_table=True)

    def _clear_table_selection(self) -> None:
        items = list(self.table.get_children())
        if items:
            self.table.selection_remove(*items)
        self.table.focus("")
        self._active_cell = None
        self._hide_active_cell_border()
        self._clear_selection_row_borders()
        self._selection_anchor_row = None
        self._sync_surface_selection(None, from_table=True)
        self.status_var.set("No surface selected")

    def _select_table_indices(self, indices: list[int], *, focus_index: int | None = None) -> None:
        selected_items = [
            item
            for index in indices
            for item in [self._table_item_for_row_index(index)]
            if item is not None
        ]
        if not selected_items:
            return
        self.table.selection_set(selected_items)
        focus_item = self._table_item_for_row_index(focus_index) if focus_index is not None else None
        if focus_item is None:
            focus_item = selected_items[0]
        self.table.focus(focus_item)
        self.table.see(focus_item)
        self._selection_anchor_row = focus_item
        self._schedule_active_cell_border_update()

    def _clear_table_selection_event(self, _event: tk.Event | None = None) -> str:
        self._clear_table_selection()
        return "break"

    def _sync_surface_selection(self, row_index: int | None, *, from_table: bool = False) -> None:
        self._layout_selected_ray_index = None
        if self._three_d_inspector is not None:
            try:
                if self._three_d_inspector.winfo_exists() and self._three_d_inspector.available:
                    self._three_d_inspector.highlight_row(row_index)
            except Exception:
                pass
        if self._legacy_3d_plotter is not None:
            try:
                self._legacy_3d_set_selected_row(self._legacy_3d_plotter, row_index)
            except Exception:
                pass
        self._update_layout_selection_overlay(row_index)
        if from_table and row_index is not None and 0 <= row_index < len(self.rows):
            self.status_var.set(f"Selected row {row_index}: {self.rows[row_index].name}")

    def _select_table_row(self, index: int) -> None:
        row_id = self._table_item_for_row_index(index)
        if row_id is None:
            return
        self.table.selection_set(row_id)
        self.table.focus(row_id)
        self.table.see(row_id)
        self._active_cell = (row_id, "#1")
        self._update_active_cell_border()
        self._sync_surface_selection(index)

    def _startup_refresh_plot(self) -> None:
        if not self.rows:
            return
        self.refresh_plot(suppress_analysis=True)

    def _set_optional_var(self, attr_name: str, value: object) -> None:
        var = self.__dict__.get(attr_name)
        if var is None:
            return
        try:
            var.set(value)
        except Exception:
            pass

    def _clear_imported_step_runtime_state(self) -> None:
        self.imported_camera_step_path = None
        self.imported_lens_step_path = None
        self.imported_optical_step_path = None
        self.imported_led_step_path = None
        self.lens_step_largest_component_only = True
        self.camera_step_rotation_x_deg = 0.0
        self.lens_step_rotation_x_deg = 0.0
        self.optical_step_rotation_x_deg = 0.0
        self.led_step_rotation_x_deg = 0.0
        self.camera_step_rotation_y_deg = 0.0
        self.lens_step_rotation_y_deg = 0.0
        self.optical_step_rotation_y_deg = 0.0
        self.led_step_rotation_y_deg = 0.0
        self.camera_step_rotation_z_deg = 0.0
        self.lens_step_rotation_z_deg = 0.0
        self.optical_step_rotation_z_deg = 0.0
        self.led_step_rotation_z_deg = 0.0
        self.led_object_edge_distance_mm = 0.0
        self.led_step_object_edge_local_z = None
        self.lens_step_axis_offset_xy = (0.0, 0.0)
        self.optical_step_axis_offset_xy = (0.0, 0.0)
        self.camera_step_axis_offset_xy = (0.0, 0.0)
        self.led_step_axis_offset_xy = (0.0, 0.0)
        self.lens_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.optical_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.camera_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.led_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._selected_step_label = None

    def _close_scene_viewers_for_layout_replacement(self) -> None:
        inspector = self.__dict__.get("_three_d_inspector")
        if inspector is not None:
            try:
                inspector.destroy()
            except Exception:
                pass
            self._three_d_inspector = None
        try:
            self._close_legacy_3d_plotter()
        except Exception:
            self._legacy_3d_plotter = None
            self._legacy_3d_after_id = None

    def _reset_complete_layout_runtime_state(self, *, close_viewers: bool = True) -> None:
        """Clear scene state that must not leak between complete preset loads."""
        self.metal_catalogs = []
        self.layout_scene_source_specs = []
        self.layout_scene_row_order = SOURCE_ROW_ORDER_DEFAULT
        self.tolerance_solve_presets = []
        self.tolerance_manufacturing_templates = []
        self.active_tolerance_solve_preset_name = ""
        self._clear_imported_step_runtime_state()
        for cache_name in (
            "_external_cad_mesh_cache",
            "_external_cad_reference_cache",
            "_external_cad_section_cache",
        ):
            cache = self.__dict__.get(cache_name)
            if isinstance(cache, dict):
                cache.clear()
        self._last_scene_bundle = None
        self._last_auto_leg_entries = []
        self._layout_pick_regions = {}
        self._layout_ray_pick_regions = []
        self._set_optional_var("trace_mode_var", "Auto")
        self.trace_mode = "Auto"
        self._set_optional_var("folded_detector_policy_var", FOLDED_DETECTOR_POLICY_DEFAULT)
        self._set_optional_var("nonseq_target_surface_var", "Auto")
        self._set_optional_var("nonseq_ns_limit_var", "200")
        self._set_optional_var("nonseq_energy_probability_var", False)
        self._set_optional_var("arm_view_var", ARM_VIEW_DEFAULT)
        self._set_optional_var("ray_display_mode_var", RAY_DISPLAY_DEFAULT)
        self._set_optional_var("analysis_branch_filter_var", ANALYSIS_PATH_FILTER_DEFAULT)
        self.show_path_labels = True
        self._set_optional_var("show_path_labels_var", True)
        self._set_optional_var("source_model_var", SOURCE_MODEL_DEFAULT)
        self._set_optional_var("pupil_pattern_var", PUPIL_PATTERN_DEFAULT)
        self._set_optional_var("source_radius_var", "5.0")
        self._set_optional_var("source_cone_angle_var", "0.0")
        self._set_optional_var("gaussian_input_mode_var", GAUSSIAN_INPUT_MODE_DEFAULT)
        self._set_optional_var("gaussian_waist_radius_var", "0.5")
        self._set_optional_var("gaussian_waist_offset_var", "0.0")
        self._set_optional_var("gaussian_beam_diameter_var", "1.0")
        self._set_optional_var("gaussian_full_divergence_var", "1.0")
        self._set_optional_var("gaussian_waist_side_var", GAUSSIAN_WAIST_SIDE_DEFAULT)
        self._set_optional_var("gaussian_m2_var", "1.0")
        self._set_optional_var("pupil_rad_var", "0.0")
        self._set_optional_var("pupil_theta_var", "0.0")
        self._set_optional_var("source_power_var", "1.0")
        self._set_optional_var("source_seed_var", "1")
        self._set_optional_var("source_x_var", "0.0")
        self._set_optional_var("source_y_var", "0.0")
        self._set_optional_var("source_z_var", "0.0")
        self._set_optional_var("source_l_var", "0.0")
        self._set_optional_var("source_m_var", "0.0")
        self._set_optional_var("source_n_var", "1.0")
        self._set_optional_var("source_direction_preset_var", "Horizontal +Z (right)")
        self._set_optional_var("source_angular_weight_var", SOURCE_ANGULAR_WEIGHT_DEFAULT)
        self._set_optional_var("detector_bins_var", DETECTOR_BINS_DEFAULT)
        self._set_optional_var("coherent_sum_mode_var", COHERENT_SUM_MODE_DEFAULT)
        self._set_optional_var("branch_field_propagation_mm_var", BRANCH_FIELD_PROPAGATION_MM_DEFAULT)
        self._set_optional_var("wavefront_style_var", WAVEFRONT_STYLE_DEFAULT)
        self._set_optional_var("camera_model_var", CAMERA_NONE_LABEL)
        self._set_optional_var("external_camera_var", "None")
        self._set_optional_var("camera_overlay_mode_var", "Off")
        self._set_optional_var("projection_display_mode_var", PROJECTION_MODE_AXIS_FIELD)
        self.layout_preview_mode = "none"
        self._set_optional_var("layout_preview_mode_var", "none")
        self.selected_analysis_modes = []
        self.analysis_mode = "none"
        self.secondary_analysis_mode = None
        try:
            self._sync_analysis_mode_buttons()
        except Exception:
            pass
        if close_viewers:
            self._close_scene_viewers_for_layout_replacement()

    def _load_reset_system(self) -> None:
        """Reset to a minimal Object + Image system."""
        self._reset_complete_layout_runtime_state(close_viewers=True)
        self.rows = [
            SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
            SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=25.0, glass="AIR"),
        ]
        self.current_layout_file = None
        self._sync_table()
        self.layout_var.set("Common Optical Layout")
        self.machine_vision_var.set("Machine Vision Lens")
        self.example_var.set("Examples")
        self._apply_initial_layout_view_defaults("Reset")

    def reset_layout(self) -> None:
        """Fast UI reset: clear prescription and preview without ray tracing."""
        self._begin_history_capture()
        self._load_reset_system()
        self._commit_history_capture()
        self._clear_preview_after_reset()

    def load_layout_by_name(self, name: str, *, refresh: bool = True) -> None:
        path = self.layout_files.get(name)
        if path is None:
            return
        if self.rows:
            self._begin_history_capture()
        self.current_layout_file = path
        had_existing_rows = bool(self.rows)
        info: dict[str, object] = {"surfaces": [], "settings": {}}
        try:
            info = _load_python_data(path)
            loaded_rows = [self._row_from_layout_item(item) for item in info["surfaces"]]
        except Exception:
            surfaces = self._extract_surfaces_from_example(path)
            loaded_rows = [self._row_from_surface(surface, index, len(surfaces)) for index, surface in enumerate(surfaces)]

        loaded_rows = self._normalized_rows_copy(loaded_rows)
        self._auto_assign_missing_elements(loaded_rows)
        replace_existing = self._is_empty_starter_rows(self.rows)
        append_to_existing = (
            had_existing_rows
            and not replace_existing
            and self._is_insertable_common_layout(name, loaded_rows, info)
        )
        insert_after = self._selected_insert_index() if append_to_existing else None
        if append_to_existing:
            self.rows = self._append_layout_rows(
                self.rows,
                loaded_rows,
                insert_after=insert_after,
                element_name=name,
            )
        else:
            self._reset_complete_layout_runtime_state(close_viewers=True)
            self.rows = loaded_rows
            self._apply_initial_field_defaults()
            self._apply_initial_layout_view_defaults(name)
            self._apply_layout_settings(info.get("settings", {}))

        self._normalize_special_rows()
        self._sync_table()
        if append_to_existing:
            self._select_inserted_layout_rows(loaded_rows, insert_after=insert_after)
        if had_existing_rows:
            self._commit_history_capture()
        if refresh:
            self.refresh_plot(suppress_analysis=True)
        if path.stem.startswith("machine_vision_"):
            self.layout_var.set("Common Optical Layout")
            self.machine_vision_var.set(name)
        else:
            self.layout_var.set(name)
            self.machine_vision_var.set("Machine Vision Lens")
        self.example_var.set("Examples")
        action = "Appended" if append_to_existing else "Loaded"
        self.status_var.set(f"{action} {name}. Click Update to run analysis.")

    @staticmethod
    def _is_insertable_common_layout(name: str, _loaded_rows: list[SurfaceRow], info: dict[str, object]) -> bool:
        settings = info.get("settings", {}) if isinstance(info, dict) else {}
        role = ""
        if isinstance(settings, dict):
            role = str(settings.get("layout_role", settings.get("load_mode", ""))).strip().lower()
        if role in {"component", "insert", "insertable"}:
            return True
        if role in {"layout", "replace", "example", "system"}:
            return False
        if name in INSERTABLE_COMMON_LAYOUT_TITLES:
            return True
        return False

    def _layout_component_rows_for_insert(self, layout_rows: list[SurfaceRow], element_name: str = "") -> list[SurfaceRow]:
        additions = component_rows_from_layout(layout_rows, element_name=element_name)
        if not additions:
            return []
        self._remap_inserted_element_labels(additions)
        return additions

    def insert_layout_component_by_name(self, name: str, *, refresh: bool = True) -> None:
        """Insert a component-style common layout without applying its global settings."""
        path = self.layout_files.get(name)
        if path is None:
            messagebox.showerror("Insert Component", f"Common layout not found:\n\n{name}", parent=self)
            return
        info: dict[str, object] = {"surfaces": [], "settings": {}}
        try:
            info = _load_python_data(path)
            loaded_rows = [self._row_from_layout_item(item) for item in info["surfaces"]]
        except Exception:
            try:
                surfaces = self._extract_surfaces_from_example(path)
                loaded_rows = [self._row_from_surface(surface, index, len(surfaces)) for index, surface in enumerate(surfaces)]
            except Exception as exc:
                messagebox.showerror("Insert Component", f"Could not load {name}:\n\n{exc}", parent=self)
                return

        loaded_rows = self._normalized_rows_copy(loaded_rows)
        self._auto_assign_missing_elements(loaded_rows)
        additions = self._layout_component_rows_for_insert(loaded_rows, element_name=name)
        if not additions:
            messagebox.showinfo("Insert Component", f"{name} has no component rows between Object and Image.", parent=self)
            return

        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Insert Component", f"Could not read the surface table:\n\n{exc}", parent=self)
            return

        insert_after = self._selected_insert_index()
        self._begin_history_capture()
        insert_at = self._insert_surface_rows(additions, insert_after=insert_after)
        self._commit_history_capture()
        self.current_layout_file = None
        self.layout_var.set("Common Optical Layout")
        self.machine_vision_var.set("Machine Vision Lens")
        self.example_var.set("Examples")
        message = (
            f"Inserted {name} as {len(additions)} surface row(s) at S{insert_at}; "
            "source, field, pupil, and analysis settings were not changed."
        )
        self.status_var.set(message)
        self.append_progress(message)
        if refresh:
            self.refresh_plot(suppress_analysis=True)

    def _selected_operand_labels(self) -> list[str]:
        if "merit_mode_list" not in self.__dict__:
            return [str(label) for label in getattr(self, "_headless_selected_operand_labels", [])]
        return [self.merit_mode_list.get(i) for i in self.merit_mode_list.curselection()]

    def _set_selected_operand_labels(self, labels: list[str]) -> None:
        if "merit_mode_list" not in self.__dict__:
            self._headless_selected_operand_labels = [str(label) for label in labels]
            return
        self.merit_mode_list.selection_clear(0, "end")
        wanted = {str(label) for label in labels}
        for index in range(self.merit_mode_list.size()):
            label = self.merit_mode_list.get(index)
            if label in wanted:
                self.merit_mode_list.selection_set(index)
        self._update_operand_setup_visibility()

    def _capture_editor_state(self) -> dict[str, object]:
        selected_indices = []
        if hasattr(self, "table"):
            try:
                selected_indices = self._selected_table_indices()
            except Exception:
                selected_indices = []
        active_cell = None
        if self._active_cell is not None:
            row_id, field = self._active_cell
            try:
                row_index = self._table_item_row_index(row_id)
                active_cell = None if row_index is None else {"row": int(row_index), "field": str(field)}
            except Exception:
                active_cell = None
        layout_path = str(self.current_layout_file) if self.current_layout_file is not None else None
        return {
            "rows": [asdict(row) for row in self.rows],
            "settings": self._collect_layout_settings(),
            "selected_indices": selected_indices,
            "active_cell": active_cell,
            "current_layout_file": layout_path,
        }

    def _begin_history_capture(self, _event: tk.Event | None = None) -> None:
        if self._history_restoring or self._history_pending_state is not None:
            return
        self._history_pending_state = self._capture_editor_state()

    def _commit_history_capture(self) -> None:
        if self._history_restoring:
            self._history_pending_state = None
            return
        snapshot = self._history_pending_state
        self._history_pending_state = None
        if snapshot is None:
            return
        current = self._capture_editor_state()
        if snapshot == current:
            return
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._history_limit:
            self._undo_stack = self._undo_stack[-self._history_limit :]
        self._redo_stack.clear()
        self._update_undo_redo_buttons()

    def _push_history_snapshot(self) -> None:
        if self._history_restoring:
            return
        self._history_pending_state = self._capture_editor_state()
        self._commit_history_capture()

    def _restore_history_state(self, state: dict[str, object]) -> None:
        self._history_restoring = True
        try:
            rows = state.get("rows", [])
            restored_rows = [SurfaceRow(**dict(item)) for item in rows if isinstance(item, dict)]
            self.rows = self._normalized_rows_copy(restored_rows)
            layout_path = state.get("current_layout_file")
            self.current_layout_file = Path(layout_path) if isinstance(layout_path, str) and layout_path else None
            self._sync_table()
            self._apply_layout_settings(state.get("settings", {}))
            self._normalize_special_rows()
            self._sync_table()
            selected_indices = [int(index) for index in state.get("selected_indices", []) if isinstance(index, int)]
            items = list(self.table.get_children())
            selected_items = [items[index] for index in selected_indices if 0 <= index < len(items)]
            if selected_items:
                self.table.selection_set(selected_items)
                self.table.focus(selected_items[0])
                self.table.see(selected_items[0])
            else:
                self.table.selection_remove(*items)
            active_cell = state.get("active_cell")
            self._active_cell = None
            if isinstance(active_cell, dict):
                row_index = int(active_cell.get("row", -1))
                field = str(active_cell.get("field", ""))
                if 0 <= row_index < len(items) and field in FIELDS:
                    self._active_cell = (items[row_index], field)
            self._update_active_cell_border()
            self._refresh_analysis_surface_choices()
            self._refresh_operand_surface_choices()
        finally:
            self._history_restoring = False
            self._history_pending_state = None
        self.refresh_plot()
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self) -> None:
        undo_state = "normal" if self._undo_stack else "disabled"
        redo_state = "normal" if self._redo_stack else "disabled"
        if self._edit_menu is not None:
            try:
                self._edit_menu.entryconfigure("Undo", state=undo_state)
                self._edit_menu.entryconfigure("Redo", state=redo_state)
            except tk.TclError:
                pass
        if self._undo_button is not None:
            self._undo_button.configure(state=undo_state)
        if self._redo_button is not None:
            self._redo_button.configure(state=redo_state)

    def undo(self) -> None:
        if not self._undo_stack:
            return
        current = self._capture_editor_state()
        state = self._undo_stack.pop()
        self._redo_stack.append(current)
        self._restore_history_state(state)
        self.status_var.set("Undo applied.")

    def redo(self) -> None:
        if not self._redo_stack:
            return
        current = self._capture_editor_state()
        state = self._redo_stack.pop()
        self._undo_stack.append(current)
        self._restore_history_state(state)
        self.status_var.set("Redo applied.")

    def _undo_event(self, _event=None) -> str:
        self.undo()
        return "break"

    def _redo_event(self, _event=None) -> str:
        self.redo()
        return "break"

    def _layout_settings_service(self) -> LayoutSettingsService:
        service = self.__dict__.get("_layout_settings_service_instance")
        if service is None:
            service = LayoutSettingsService(self)
            self._layout_settings_service_instance = service
        return service

    def _collect_layout_settings(self) -> dict[str, object]:
        return self._layout_settings_service()._collect_layout_settings()

    def _apply_layout_settings(self, settings: object) -> None:
        self._layout_settings_service()._apply_layout_settings(settings)

    def load_example_by_name(self, name: str) -> None:
        path = self.example_files.get(name)
        if path is None:
            return
        if self.rows:
            self._begin_history_capture()
        info: dict[str, object] | None = None
        try:
            code = path.read_text(encoding="utf-8", errors="ignore")
            if python_code_defines_layout_data(code):
                info = _load_python_data(path)
                self.rows = [self._row_from_layout_item(item) for item in info["surfaces"]]
                self.rows = self._normalized_rows_copy(self.rows)
            else:
                surfaces = self._extract_surfaces_from_example(path)
                self.rows = [self._row_from_surface(surface, index, len(surfaces)) for index, surface in enumerate(surfaces)]
        except Exception as exc:
            self._history_pending_state = None
            self.status_var.set(f"Failed to load example {name}: {exc}")
            return
        self.current_layout_file = None
        self._reset_complete_layout_runtime_state(close_viewers=True)
        self._normalize_special_rows()
        self._apply_example_display_defaults(path)
        if info is not None:
            self._apply_layout_settings(info.get("settings", {}))
        self._sync_table()
        self._commit_history_capture()
        self.refresh_plot(suppress_analysis=True)
        self.layout_var.set("Common Optical Layout")
        self.machine_vision_var.set("Machine Vision Lens")
        self.example_var.set(name)
        warned = False if info is not None else self._report_example_feature_gaps(name, path, surfaces)
        if not warned:
            self.status_var.set(f"Loaded example {name}. Click Update to run analysis.")

    def _on_layout_selected(self, _event: tk.Event | None = None) -> None:
        selected = self.layout_var.get().strip()
        if selected == "Common Optical Layout":
            return
        self.load_layout_by_name(selected)

    def _on_machine_vision_selected(self, _event: tk.Event | None = None) -> None:
        selected = self.machine_vision_var.get().strip()
        if selected == "Machine Vision Lens":
            return
        self.load_layout_by_name(selected)

    def _on_example_selected(self, _event: tk.Event | None = None) -> None:
        selected = self.example_var.get().strip()
        if selected == "Examples":
            return
        self.load_example_by_name(selected)

    @staticmethod
    def _element_tag_palette() -> tuple[tuple[str, str], ...]:
        return (
            ("element_group_0", "#e8f5e9"),
            ("element_group_1", "#e3f2fd"),
            ("element_group_2", "#fff3e0"),
            ("element_group_3", "#f3e5f5"),
            ("element_group_4", "#e0f7fa"),
            ("element_group_5", "#fce4ec"),
        )

    @staticmethod
    def _element_key(row: SurfaceRow) -> str:
        return str(getattr(row, "element", "") or "").strip()

    @staticmethod
    def _element_metadata(row: SurfaceRow) -> dict[str, object]:
        return _normalize_element_metadata((row.advanced or {}).get(ELEMENT_ADVANCED_ATTR))

    @staticmethod
    def _detector_settings(row: SurfaceRow) -> dict[str, object]:
        advanced = getattr(row, "advanced", {}) or {}
        value = advanced.get(DETECTOR_ADVANCED_ATTR) if isinstance(advanced, dict) else None
        return _normalize_detector_settings(value)

    @staticmethod
    def _scene_target_settings(row: SurfaceRow) -> dict[str, object]:
        advanced = getattr(row, "advanced", {}) or {}
        value = advanced.get(SCENE_TARGET_ADVANCED_ATTR) if isinstance(advanced, dict) else None
        return _normalize_scene_target_settings(value)

    @staticmethod
    def _scene_placement_settings(row: SurfaceRow) -> dict[str, object]:
        advanced = getattr(row, "advanced", {}) or {}
        value = advanced.get(SCENE_PLACEMENT_ADVANCED_ATTR) if isinstance(advanced, dict) else None
        return normalize_scene_placement_settings(value)

    @staticmethod
    def _set_detector_settings(row: SurfaceRow, settings: dict[str, object]) -> None:
        normalized = _normalize_detector_settings(settings)
        row.advanced = dict(row.advanced or {})
        if _detector_settings_is_default(normalized):
            row.advanced.pop(DETECTOR_ADVANCED_ATTR, None)
        else:
            row.advanced[DETECTOR_ADVANCED_ATTR] = normalized

    @staticmethod
    def _set_scene_target_settings(row: SurfaceRow, settings: dict[str, object]) -> None:
        normalized = _normalize_scene_target_settings(settings)
        row.advanced = dict(row.advanced or {})
        if _scene_target_settings_is_default(normalized):
            row.advanced.pop(SCENE_TARGET_ADVANCED_ATTR, None)
        else:
            row.advanced[SCENE_TARGET_ADVANCED_ATTR] = normalized

    @staticmethod
    def _set_scene_placement_settings(row: SurfaceRow, settings: dict[str, object]) -> None:
        normalized = normalize_scene_placement_settings(settings)
        row.advanced = dict(row.advanced or {})
        if scene_placement_settings_is_default(normalized):
            row.advanced.pop(SCENE_PLACEMENT_ADVANCED_ATTR, None)
        else:
            row.advanced[SCENE_PLACEMENT_ADVANCED_ATTR] = normalized

    @staticmethod
    def _row_has_detector_output_metadata(row: SurfaceRow) -> bool:
        advanced = getattr(row, "advanced", {}) or {}
        if not isinstance(advanced, dict):
            return False
        if DETECTOR_ADVANCED_ATTR in advanced:
            return True
        metadata = _normalize_element_metadata(advanced.get(ELEMENT_ADVANCED_ATTR))
        if str(metadata.get("arm_role", "") or "") == "Detector":
            return True
        display_settings = advanced.get("Display2D")
        if isinstance(display_settings, dict) and isinstance(display_settings.get("branch_output_targets"), dict):
            return True
        return isinstance(advanced.get("Interferogram"), dict)

    @staticmethod
    def _set_element_metadata(row: SurfaceRow, metadata: dict[str, object]) -> None:
        normalized = _normalize_element_metadata(metadata)
        row.advanced = dict(row.advanced or {})
        if _element_metadata_is_default(normalized):
            row.advanced.pop(ELEMENT_ADVANCED_ATTR, None)
        else:
            row.advanced[ELEMENT_ADVANCED_ATTR] = normalized

    @classmethod
    def _element_arm_role_for_index(cls, rows: list[SurfaceRow], index: int) -> str:
        if not (0 <= index < len(rows)):
            return ELEMENT_ARM_ROLE_DEFAULT
        start, _end = cls._element_block_for_index(rows, index)
        return str(cls._element_metadata(rows[start]).get("arm_role", ELEMENT_ARM_ROLE_DEFAULT))

    @classmethod
    def _element_arm_badge_for_index(cls, rows: list[SurfaceRow], index: int) -> str:
        if not (0 <= index < len(rows)):
            return ""
        start, _end = cls._element_block_for_index(rows, index)
        if index != start:
            return ""
        role = cls._element_arm_role_for_index(rows, index)
        return ELEMENT_ARM_BADGES.get(role, "")

    @staticmethod
    def _leg_badge_text(short_label: str) -> str:
        text = str(short_label or "").strip()
        match = re.fullmatch(r"(?:Leg|Path)\s+(\d+)", text, flags=re.IGNORECASE)
        return f"P{match.group(1)}" if match else text

    def _layout_interferometer_hint(self) -> str:
        texts: list[str] = []
        for row in getattr(self, "rows", []) or []:
            texts.extend(
                [
                    str(getattr(row, "element", "") or ""),
                    str(getattr(row, "name", "") or ""),
                    str(getattr(row, "surface", "") or ""),
                ]
            )
            advanced = getattr(row, "advanced", {}) or {}
            if isinstance(advanced, dict):
                for key in ("Note", "Interferogram", "Display2D"):
                    value = advanced.get(key)
                    if isinstance(value, dict):
                        texts.extend(str(item) for item in value.values())
                    elif value is not None:
                        texts.append(str(value))
        return " ".join(texts).lower()

    def _auto_leg_entries(self) -> list[dict[str, object]]:
        return list(getattr(self, "_last_auto_leg_entries", []) or [])

    def _auto_leg_entry_for_id(self, leg_id: str) -> dict[str, object] | None:
        target = str(leg_id or "").strip().lower()
        if not target:
            return None
        for entry in self._auto_leg_entries():
            if str(entry.get("leg_id", "") or "").strip().lower() == target:
                return entry
        return None

    @staticmethod
    def _auto_leg_point_key(point: np.ndarray, tolerance: float = 0.25) -> str:
        return auto_leg_point_key(point, tolerance)

    @staticmethod
    def _auto_leg_node_label(node: dict[str, object]) -> str:
        return auto_leg_node_label(node)

    def _auto_leg_node_for_hit(
        self,
        point: np.ndarray,
        surface_id: int | None,
        *,
        branch_path: str = "",
        branch_label: str = "",
    ) -> dict[str, object]:
        return auto_leg_node_for_hit(
            point,
            surface_id,
            self.rows,
            branch_path=branch_path,
            branch_label=branch_label,
            beam_splitter_surface=BEAM_SPLITTER_SURFACE,
        )

    @staticmethod
    def _auto_leg_hit_point_index(points: np.ndarray, surface_ids: np.ndarray, hit_index: int) -> int:
        return auto_leg_hit_point_index(points, surface_ids, hit_index)

    def _auto_leg_candidate_key(
        self,
        start_node: dict[str, object],
        end_node: dict[str, object],
        non_branch_surface_ids: tuple[int, ...],
    ) -> tuple[tuple[str, str], tuple[int, ...]]:
        return auto_leg_candidate_key(start_node, end_node, non_branch_surface_ids)

    @staticmethod
    def _auto_leg_midpoint(polyline: np.ndarray) -> np.ndarray:
        return auto_leg_midpoint(polyline)

    def _auto_leg_representative_polyline(self, polylines: list[np.ndarray]) -> np.ndarray:
        return auto_leg_representative_polyline(polylines)

    def _auto_leg_direction_from_node(self, entry: dict[str, object], node_key: str) -> np.ndarray:
        return auto_leg_direction_from_node(entry, node_key)

    def _ordered_auto_leg_keys(self, legs: dict[tuple[tuple[str, str], tuple[int, ...]], dict[str, object]]) -> list[tuple[tuple[str, str], tuple[int, ...]]]:
        return ordered_auto_leg_keys(legs)

    def _build_auto_leg_entries_from_projected(self, projected: ProjectedScene2D) -> list[dict[str, object]]:
        return build_auto_leg_entries_from_projected(
            projected,
            self.rows,
            beam_splitter_surface=BEAM_SPLITTER_SURFACE,
        )

    def _refresh_auto_leg_graph(self, projected: ProjectedScene2D | None) -> None:
        if projected is None:
            self._last_auto_leg_entries = []
            return
        try:
            self._last_auto_leg_entries = self._build_auto_leg_entries_from_projected(projected)
        except Exception as exc:
            self._last_auto_leg_entries = []
            self.append_debug(f"Automatic path graph skipped: {_short_error_message(exc)}")

    def _physical_leg_workflow(self) -> str:
        if not getattr(self, "rows", None):
            return ""
        hint = self._layout_interferometer_hint()
        if "mach" in hint and "zehnder" in hint:
            return "mach_zehnder"
        if "michelson" in hint or "twyman" in hint:
            return "michelson"
        target_codes = set(self._branch_output_display_targets())
        if {"TT", "TR", "RT", "RR"}.issubset(target_codes):
            return "michelson"
        return ""

    def _physical_leg_definitions(self) -> tuple[tuple[str, str, str], ...]:
        workflow = self._physical_leg_workflow()
        if workflow == "mach_zehnder":
            return MACH_ZEHNDER_LEG_DEFINITIONS
        if workflow == "michelson":
            return MICHELSON_LEG_DEFINITIONS
        auto_entries = self._auto_leg_entries()
        if auto_entries:
            return tuple(
                (
                    str(entry.get("leg_id", "") or "").strip().lower(),
                    str(entry.get("short_label", "") or "").strip(),
                    str(entry.get("detail", "") or "").strip(),
                )
                for entry in auto_entries
                if str(entry.get("leg_id", "") or "").strip()
            )
        return ()

    def _physical_leg_ids(self) -> set[str]:
        ids = {leg_id for leg_id, _short_label, _detail in self._physical_leg_definitions()}
        for row in getattr(self, "rows", []) or []:
            leg_id = str(self._element_metadata(row).get("leg_id", "") or "").strip().lower()
            if leg_id:
                ids.add(leg_id)
        return ids

    def _leg_short_label(self, leg_id: str) -> str:
        leg_id = str(leg_id or "").strip().lower()
        for defined_id, short_label, _detail in self._physical_leg_definitions():
            if leg_id == defined_id:
                return short_label
        return ""

    def _leg_id_from_element_metadata(
        self,
        metadata: dict[str, object],
        *,
        row: SurfaceRow | None = None,
        row_index: int | None = None,
    ) -> str:
        valid_leg_ids = self._physical_leg_ids()
        explicit = str(metadata.get("leg_id", "") or "").strip().lower()
        if explicit in valid_leg_ids:
            return explicit
        workflow = self._physical_leg_workflow()
        role = str(metadata.get("arm_role", ELEMENT_ARM_ROLE_DEFAULT) or ELEMENT_ARM_ROLE_DEFAULT).strip()
        selector = str(metadata.get("branch_selector", "") or "").strip().lower()
        parent = str(metadata.get("parent_splitter", "") or "").strip().lower()
        row_text = ""
        if row is not None:
            row_text = " ".join(
                [
                    str(getattr(row, "element", "") or ""),
                    str(getattr(row, "name", "") or ""),
                    str(getattr(row, "surface", "") or ""),
                    str(metadata.get("element_id", "") or ""),
                    str(metadata.get("element_name", "") or ""),
                ]
            ).lower()
        if workflow == "mach_zehnder":
            if row_index == 0:
                return "input"
            if role == "Common":
                if selector == "primary" or "bs1" in row_text or "input splitter" in row_text:
                    return "input"
                return ""
            if selector == "transmit" and role in {"Transmit", "Return"}:
                return "transmit"
            if selector == "reflect" and role in {"Reflect", "Return"}:
                return "reflect"
            if role == "Detector":
                if selector == "transmit" or "cross" in row_text:
                    return "cross"
                if selector == "reflect" or "return" in row_text:
                    return "return"
            if parent == "bs2" and selector == "transmit":
                return "cross"
            if parent == "bs2" and selector == "reflect":
                return "return"
            return ""
        if workflow == "michelson":
            if row_index == 0:
                return "input"
            if role == "Common" or selector == "primary":
                return "input"
            if row is not None and self._row_has_detector_output_metadata(row):
                return "detector"
            if role == "Detector":
                return "detector"
            if role == "Reflect" or selector == "reflect":
                return "reflect"
            if role == "Transmit" or selector == "transmit":
                return "transmit"
        return ""

    def _michelson_leg_badge_for_index(self, index: int) -> str:
        if not self._uses_michelson_leg_workflow() or not (0 <= index < len(self.rows)):
            return ""
        row = self.rows[index]
        metadata = self._element_metadata(row)
        leg_id = self._leg_id_from_element_metadata(metadata, row=row, row_index=index)
        return self._leg_badge_text(self._leg_short_label(leg_id)) if leg_id else ""

    @staticmethod
    def _branch_selector_for_arm_role(role: str) -> str:
        if role == "Transmit":
            return "transmit"
        if role == "Reflect":
            return "reflect"
        return ""

    @staticmethod
    def _arm_key_from_metadata(metadata: dict[str, object]) -> str:
        branch_path = str(metadata.get("branch_path", "") or "").strip()
        if branch_path and branch_path != "primary":
            return KrakenLayoutEditor._arm_key_from_branch_path(branch_path)
        leg_id = str(metadata.get("leg_id", "") or "").strip().lower()
        if leg_id:
            return f"leg|{leg_id}"
        role = str(metadata.get("arm_role", ELEMENT_ARM_ROLE_DEFAULT) or ELEMENT_ARM_ROLE_DEFAULT).strip()
        if role in {"", ELEMENT_ARM_ROLE_DEFAULT, "Common"}:
            return ""
        selector = str(metadata.get("branch_selector", "") or "").strip().lower()
        parent = str(metadata.get("parent_splitter", "") or "").strip()
        if selector in {"primary", "transmit", "reflect", "return"}:
            return f"branch|{parent}|{selector}"
        return f"role|{role}"

    @staticmethod
    def _arm_key_from_branch_path(branch_path: str) -> str:
        path = str(branch_path or "").strip()
        if not path or path == "primary":
            return ""
        return f"path|{path}"

    @staticmethod
    def _leg_key(leg_id: str) -> str:
        return f"leg|{str(leg_id or '').strip().lower()}"

    @staticmethod
    def _leg_id_from_arm_key(key: str) -> str:
        text = str(key or "").strip()
        if not text.startswith("leg|"):
            return ""
        return text.split("|", 1)[1].strip().lower()

    @staticmethod
    def _branch_path_for_arm_key(key: str) -> str:
        text = str(key or "").strip()
        if text.startswith("path|"):
            return text.split("|", 1)[1].strip()
        return ""

    @staticmethod
    def _branch_path_leaf_selector(branch_path: str) -> str:
        leaf = str(branch_path or "").split("->")[-1].strip()
        if "/" not in leaf:
            return ""
        return leaf.rsplit("/", 1)[1].strip().lower()

    @staticmethod
    def _branch_path_surface_indices(branch_path: str) -> set[int]:
        return set(KrakenLayoutEditor._branch_path_surface_sequence(branch_path))

    @staticmethod
    def _branch_path_surface_sequence(branch_path: str) -> list[int]:
        indices: list[int] = []
        for match in re.finditer(r"(?:^|\s)S(\d+):", str(branch_path or "")):
            try:
                indices.append(int(match.group(1)))
            except ValueError:
                continue
        return indices

    @staticmethod
    def _branch_path_detail(branch_path: str) -> str:
        parts: list[str] = []
        for component in str(branch_path or "").split("->"):
            text = component.strip()
            if not text:
                continue
            surface_text, _, selector = text.rpartition("/")
            if not surface_text:
                surface_text = text
            if ":" in surface_text:
                surface_text = surface_text.split(":", 1)[1].strip()
            surface_text = surface_text.strip()
            selector = selector.strip()
            if surface_text and selector:
                parts.append(f"{surface_text} {selector}")
            elif selector:
                parts.append(selector)
            elif surface_text:
                parts.append(surface_text)
        return " -> ".join(parts) if parts else str(branch_path or "").strip()

    @staticmethod
    def _branch_path_depth(branch_path: str) -> int:
        return sum(1 for component in str(branch_path or "").split("->") if component.strip())

    @staticmethod
    def _branch_path_selector_sequence(branch_path: str) -> list[str]:
        return branch_path_selector_sequence(branch_path)

    @staticmethod
    def _branch_path_compact_detail(branch_path: str) -> str:
        selectors = KrakenLayoutEditor._branch_path_selector_sequence(branch_path)
        if selectors:
            return " -> ".join(selectors)
        return KrakenLayoutEditor._branch_path_detail(branch_path)

    def _arm_key_detail(self, key: str) -> str:
        parts = str(key or "").split("|")
        if len(parts) >= 2 and parts[0] == "leg":
            leg_id = parts[1].strip().lower()
            for defined_id, _short_label, detail in self._physical_leg_definitions():
                if leg_id == defined_id:
                    return detail
            return leg_id
        if len(parts) >= 2 and parts[0] == "path":
            path = "|".join(parts[1:])
            if KrakenLayoutEditor._branch_path_depth(path) > 1:
                return KrakenLayoutEditor._branch_path_compact_detail(path)
            return KrakenLayoutEditor._branch_path_detail(path)
        if len(parts) >= 3 and parts[0] == "branch":
            parent = parts[1].strip()
            selector = parts[2].strip()
            return f"{parent} {selector}".strip() if parent else selector
        if len(parts) >= 2 and parts[0] == "role":
            return parts[1].strip()
        return str(key or "").strip()

    def _traced_branch_paths(self) -> list[str]:
        bundle = getattr(self, "_last_scene_bundle", None)
        paths: list[str] = []
        seen: set[str] = set()
        for path in getattr(bundle, "ray_paths", []) or []:
            branch_path = str(getattr(path, "branch_path", "") or "").strip()
            if not branch_path or branch_path == "primary" or branch_path in seen:
                continue
            seen.add(branch_path)
            paths.append(branch_path)
        return paths

    @classmethod
    def _metadata_arm_key_matches_branch_path(cls, arm_key: str, branch_path: str) -> bool:
        parts = str(arm_key or "").split("|")
        target_path = cls._branch_path_for_arm_key(arm_key)
        if target_path:
            return str(branch_path or "").strip() == target_path
        if len(parts) < 3 or parts[0] != "branch":
            return False
        parent = parts[1].strip().lower()
        selector = parts[2].strip().lower()
        if selector and selector != cls._branch_path_leaf_selector(branch_path):
            return False
        if not parent:
            return True
        path_text = str(branch_path or "").lower()
        if parent in path_text:
            return True
        # Saved Element metadata often uses a stable splitter id such as BS1,
        # while traced paths use the KrakenOS surface label. A matching leaf
        # selector is still the same logical path and should not create a
        # duplicate metadata label beside the traced branch/path label.
        return bool(selector)

    def _uses_michelson_leg_workflow(self) -> bool:
        return bool(self._physical_leg_definitions())

    def _leg_catalog(self) -> list[dict[str, str]]:
        definitions = self._physical_leg_definitions()
        if not definitions:
            return []
        catalog: list[dict[str, str]] = []
        for leg_id, short_label, detail in definitions:
            catalog.append(
                {
                    "key": self._leg_key(leg_id),
                    "short_label": short_label,
                    "label": f"{short_label}: {detail}",
                    "detail": detail,
                    "kind": "leg",
                }
            )
        return catalog

    def _arm_catalog(self) -> list[dict[str, str]]:
        catalog: list[dict[str, str]] = []
        seen: set[str] = set()
        if not self.rows:
            return catalog
        leg_catalog = self._leg_catalog()
        if leg_catalog:
            return leg_catalog

        def add_entry(key: str, detail: str, prefix: str = "Path") -> None:
            if not key or key in seen:
                return
            seen.add(key)
            arm_number = len(catalog) + 1
            label = f"{prefix} {arm_number}: {detail}" if detail else f"{prefix} {arm_number}"
            catalog.append(
                {
                    "key": key,
                    "short_label": f"{prefix} {arm_number}",
                    "label": label,
                    "detail": detail,
                    "kind": prefix.lower(),
                }
            )

        traced_paths = self._traced_branch_paths()
        for branch_path in traced_paths:
            depth = self._branch_path_depth(branch_path)
            detail = (
                self._branch_path_compact_detail(branch_path)
                if depth > 1
                else self._branch_path_detail(branch_path)
            )
            add_entry(self._arm_key_from_branch_path(branch_path), detail, prefix="Path")

        index = 1
        while index < len(self.rows) - 1:
            start, end = self._element_block_for_index(self.rows, index)
            metadata = self._element_metadata(self.rows[start])
            key = self._arm_key_from_metadata(metadata)
            if key and not any(self._metadata_arm_key_matches_branch_path(key, path) for path in traced_paths):
                add_entry(key, self._arm_key_detail(key))
            index = max(end + 1, index + 1)
        return catalog

    @classmethod
    def _element_block_for_index(cls, rows: list[SurfaceRow], index: int) -> tuple[int, int]:
        if not (0 <= index < len(rows)):
            return index, index
        key = cls._element_key(rows[index])
        if not key:
            return index, index
        start = index
        end = index
        while start > 0 and cls._element_key(rows[start - 1]) == key:
            start -= 1
        while end + 1 < len(rows) and cls._element_key(rows[end + 1]) == key:
            end += 1
        return start, end

    @classmethod
    def _swap_element_block_same_arm(
        cls,
        rows: list[SurfaceRow],
        selected_index: int,
        direction: str,
    ) -> tuple[list[SurfaceRow], int, int, bool]:
        start, end = cls._element_block_for_index(rows, selected_index)
        role = cls._element_arm_role_for_index(rows, selected_index)
        if role == ELEMENT_ARM_ROLE_DEFAULT:
            return rows, start, end, False
        current = rows[start : end + 1]
        if direction == "up":
            scan = start - 1
            while scan > 0:
                previous_start, previous_end = cls._element_block_for_index(rows, scan)
                if cls._element_arm_role_for_index(rows, previous_start) == role:
                    previous = rows[previous_start : previous_end + 1]
                    middle = rows[previous_end + 1 : start]
                    new_rows = rows[:previous_start] + current + middle + previous + rows[end + 1 :]
                    new_start = previous_start
                    return new_rows, new_start, new_start + len(current) - 1, True
                scan = previous_start - 1
            return rows, start, end, False
        if direction == "down":
            scan = end + 1
            while scan < len(rows) - 1:
                next_start, next_end = cls._element_block_for_index(rows, scan)
                if cls._element_arm_role_for_index(rows, next_start) == role:
                    next_block = rows[next_start : next_end + 1]
                    middle = rows[end + 1 : next_start]
                    new_rows = rows[:start] + next_block + middle + current + rows[next_end + 1 :]
                    new_start = start + len(next_block) + len(middle)
                    return new_rows, new_start, new_start + len(current) - 1, True
                scan = next_end + 1
            return rows, start, end, False
        return rows, start, end, False

    @classmethod
    def _swap_element_block(
        cls,
        rows: list[SurfaceRow],
        selected_index: int,
        direction: str,
        *,
        same_arm_only: bool = False,
    ) -> tuple[list[SurfaceRow], int, int, bool]:
        if not rows or not (0 <= selected_index < len(rows)):
            return rows, selected_index, selected_index, False
        start, end = cls._element_block_for_index(rows, selected_index)
        if same_arm_only:
            arm_rows, arm_start, arm_end, arm_moved = cls._swap_element_block_same_arm(rows, selected_index, direction)
            if arm_moved:
                return arm_rows, arm_start, arm_end, True
            if cls._element_arm_role_for_index(rows, selected_index) != ELEMENT_ARM_ROLE_DEFAULT:
                return rows, start, end, False
        if direction == "up":
            if start <= 1:
                return rows, start, end, False
            previous_start, previous_end = cls._element_block_for_index(rows, start - 1)
            if previous_start <= 0:
                return rows, start, end, False
            current = rows[start : end + 1]
            previous = rows[previous_start : previous_end + 1]
            new_rows = rows[:previous_start] + current + previous + rows[end + 1 :]
            new_start = previous_start
            return new_rows, new_start, new_start + len(current) - 1, True
        if direction == "down":
            if end >= len(rows) - 2:
                return rows, start, end, False
            next_start, next_end = cls._element_block_for_index(rows, end + 1)
            if next_end >= len(rows) - 1:
                return rows, start, end, False
            current = rows[start : end + 1]
            next_block = rows[next_start : next_end + 1]
            new_rows = rows[:start] + next_block + current + rows[next_end + 1 :]
            new_start = start + len(next_block)
            return new_rows, new_start, new_start + len(current) - 1, True
        return rows, start, end, False

    @classmethod
    def _element_indices_for_index(cls, rows: list[SurfaceRow], index: int) -> list[int]:
        if not (0 <= index < len(rows)):
            return []
        start, end = cls._element_block_for_index(rows, index)
        return list(range(start, end + 1))

    @staticmethod
    def _table_iid_for_row_index(index: int) -> str:
        return f"row_{int(index)}"

    def _table_item_row_index(self, item: str | None) -> int | None:
        if not item:
            return None
        text = str(item)
        mapping = self.__dict__.get("_table_iid_to_row_index", {})
        if text in mapping:
            mapped = mapping.get(text)
            if mapped is None:
                return None
            return int(mapped)
        if text.startswith("scene_source_"):
            return None
        if text.startswith("row_"):
            try:
                return int(text.split("_", 1)[1])
            except ValueError:
                return None
        try:
            return int(self.table.index(text))
        except Exception:
            return None

    def _table_item_for_row_index(self, row_index: int) -> str | None:
        item = self._table_iid_for_row_index(row_index)
        try:
            return item if self.table.exists(item) else None
        except Exception:
            return None

    @staticmethod
    def _table_iid_for_scene_source_record(record) -> str:
        source_id = str(getattr(record, "source_id", "") or getattr(record, "scene_row_index", ""))
        safe_source_id = "".join(ch if ch.isalnum() else "_" for ch in source_id).strip("_") or "source"
        return f"scene_source_{int(getattr(record, 'scene_row_index', 0))}_{safe_source_id}"

    def _table_item_scene_record(self, item: str | None):
        if not item:
            return None
        return self.__dict__.get("_table_iid_to_scene_record", {}).get(str(item))

    def _current_arm_view_key(self) -> str:
        return self._arm_key_for_view_label(str(self.arm_view_var.get() or ARM_VIEW_DEFAULT))

    def _path_local_table_mode_enabled(self) -> bool:
        return bool(self._current_arm_view_key())

    def _row_uses_path_local_table_pose(self, row: SurfaceRow) -> bool:
        return self._path_local_table_mode_enabled() and self._metadata_has_path_pose(self._element_metadata(row))

    def _path_local_pose_cell_enabled(self, row_index: int, field: str) -> bool:
        if field not in PATH_LOCAL_TABLE_FIELD_MAP:
            return False
        if not (0 <= row_index < len(self.rows)):
            return False
        return self._row_uses_path_local_table_pose(self.rows[row_index])

    def _format_path_local_table_pose_cell(self, row: SurfaceRow, field: str) -> str:
        metadata_key = PATH_LOCAL_TABLE_FIELD_MAP.get(field, "")
        if not metadata_key:
            return ""
        metadata = self._element_metadata(row)
        return self._format_table_float(float(metadata.get(metadata_key, 0.0)))

    def _sync_table_headings(self) -> None:
        table = self.__dict__.get("table")
        if table is None:
            return
        local_mode = self._path_local_table_mode_enabled()
        self._table_path_local_mode_active = local_mode
        for field in FIELDS:
            label = PATH_LOCAL_COLUMN_LABELS.get(field, COLUMN_LABELS[field]) if local_mode else COLUMN_LABELS[field]
            try:
                table.heading(field, text=label)
            except Exception:
                continue

    def _default_insert_index_for_arm_key(self, arm_key: str) -> int:
        leg_id = self._leg_id_from_arm_key(arm_key)
        arm_indices = self._indices_for_arm_key(arm_key)
        if leg_id == "input":
            for index in range(1, max(len(self.rows) - 1, 1)):
                if self.rows[index].surface == BEAM_SPLITTER_SURFACE:
                    return index
            return 1
        if leg_id in {"reflect", "transmit", "detector", "cross", "return"} and arm_indices:
            return min(arm_indices)
        return (max(arm_indices) + 1) if arm_indices else max(1, len(self.rows) - 1)

    def _visible_row_indices_for_current_arm_view(self) -> list[int]:
        if not self.rows:
            return []
        arm_key = self._current_arm_view_key()
        if not arm_key:
            return list(range(len(self.rows)))
        allowed = self._context_surface_indices_for_arm_key(arm_key) | self._surface_indices_for_arm_key(arm_key)
        return [index for index in range(len(self.rows)) if index in allowed]

    def _visible_table_scene_sources(self) -> list[SceneSource3D]:
        sources = self._collect_scene_sources()
        explicit_scene_sources = bool(getattr(self, "layout_scene_source_specs", []) or [])
        return [source for source in sources if explicit_scene_sources or bool(source.physical)]

    def _visible_scene_row_records_for_table(self, visible_indices: list[int]):
        source_records = self._visible_table_scene_sources()
        if not source_records:
            mapping = build_scene_row_mapping(
                self.rows,
                [],
                include_sources=False,
            )
            return [mapping.record_for_table_row(index) for index in visible_indices]
        visible_set = {int(index) for index in visible_indices}
        mapping = build_scene_row_mapping(
            self.rows,
            source_records,
            include_sources=True,
            source_row_order=normalize_source_row_order(
                getattr(self, "layout_scene_row_order", SOURCE_ROW_ORDER_DEFAULT)
            ),
        )
        return [
            record
            for record in mapping.records
            if record is not None
            and (
                record.kind == SCENE_ROW_SOURCE
                or (record.table_row_index is not None and int(record.table_row_index) in visible_set)
            )
        ]

    def _table_values_for_surface_row(self, index: int, row: SurfaceRow) -> list[str]:
        arm_badge = self._michelson_leg_badge_for_index(index) or self._element_arm_badge_for_index(self.rows, index)
        label_text = f"{index} {arm_badge}" if arm_badge else str(index)
        use_path_local_pose = self._row_uses_path_local_table_pose(row)
        raw_values = {
            "label": label_text,
            "surface": row.surface,
            "name": row.name,
            "glass": row.glass,
            "rc": self._format_numeric_cell("rc", row),
            "k": self._format_numeric_cell("k", row),
            "axicon": self._format_table_float(row.axicon),
            "diff_ord": self._format_table_float(row.diff_ord),
            "grating_d": self._format_numeric_cell("grating_d", row),
            "grating_angle": self._format_numeric_cell("grating_angle", row),
            "thickness": self._format_numeric_cell("thickness", row),
            "diameter": self._format_table_float(row.diameter),
            "in_diameter": self._format_table_float(row.in_diameter),
            "tilt_x": self._format_pose_cell(self.rows, index, "tilt_x"),
            "tilt_y": self._format_pose_cell(self.rows, index, "tilt_y"),
            "tilt_z": self._format_pose_cell(self.rows, index, "tilt_z"),
            "desp_x": self._format_pose_cell(self.rows, index, "desp_x"),
            "desp_y": self._format_pose_cell(self.rows, index, "desp_y"),
            "desp_z": self._format_pose_cell(self.rows, index, "desp_z"),
            "axis_move": self._format_numeric_cell("axis_move", row),
        }
        if use_path_local_pose:
            for field in PATH_LOCAL_TABLE_FIELD_MAP:
                raw_values[field] = self._format_path_local_table_pose_cell(row, field)
        return [self._table_display_value_for_row(index, row, field, raw_values[field]) for field in FIELDS]

    @staticmethod
    def _table_values_for_source_scene_row(record) -> list[str]:
        metadata = dict(getattr(record, "metadata", {}) or {})
        model = str(metadata.get("model", "") or "Source")
        ray_count = metadata.get("ray_count", "")
        name = str(getattr(record, "name", "") or "Source")
        if ray_count not in ("", None):
            name = f"{name} ({ray_count} rays)"
        surface_text = "Illumination Source" if bool(getattr(record, "physical", True)) else "Source Reference"
        raw_values = {
            "label": str(getattr(record, "label", "Src")),
            "surface": surface_text,
            "name": name,
            "glass": model,
        }
        for field in FIELDS:
            raw_values.setdefault(field, DISABLED_TABLE_CELL_TEXT)
        return [str(raw_values.get(field, DISABLED_TABLE_CELL_TEXT)) for field in FIELDS]

    def _sync_table(self) -> None:
        self._apply_image_diameter_mode()
        self._sync_table_headings()
        self.table.delete(*self.table.get_children())
        self._table_iid_to_row_index = {}
        self._table_iid_to_scene_record = {}
        self._refresh_arm_view_choices()
        visible_indices = self._visible_row_indices_for_current_arm_view()
        self._table_visible_row_indices = list(visible_indices)
        visible_records = [
            record for record in self._visible_scene_row_records_for_table(visible_indices) if record is not None
        ]
        palette = self._element_tag_palette()
        element_tags: dict[str, str] = {}
        for record in visible_records:
            if record.kind == SCENE_ROW_SOURCE:
                iid = self._table_iid_for_scene_source_record(record)
                self._table_iid_to_row_index[iid] = None
                self._table_iid_to_scene_record[iid] = record
                self.table.insert("", "end", iid=iid, values=self._table_values_for_source_scene_row(record), tags=("scene_source",))
                continue
            if record.table_row_index is None:
                continue
            index = int(record.table_row_index)
            if not (0 <= index < len(self.rows)):
                continue
            row = self.rows[index]
            row.label = str(index)
            tags: list[str] = []
            element_key = self._element_key(row)
            if element_key:
                tag = element_tags.get(element_key)
                if tag is None:
                    tag = palette[len(element_tags) % len(palette)][0]
                    element_tags[element_key] = tag
                tags.append(tag)
            iid = self._table_iid_for_row_index(index)
            self._table_iid_to_row_index[iid] = index
            self._table_iid_to_scene_record[iid] = record
            self.table.insert("", "end", iid=iid, values=self._table_values_for_surface_row(index, row), tags=tags)
        self._refresh_analysis_surface_choices()
        self._refresh_operand_surface_choices()
        self._schedule_table_grid_update(delay=1)

    def _sync_image_row_table_value(self) -> None:
        table = self.__dict__.get("table")
        if table is None or not self.rows:
            return
        items = table.get_children()
        if not items:
            return
        image_item = self._table_item_for_row_index(len(self.rows) - 1)
        if image_item is None:
            return
        values = list(table.item(image_item, "values"))
        diameter_index = FIELDS.index("diameter")
        if len(values) <= diameter_index:
            return
        values[diameter_index] = self._table_display_value(
            self.rows[-1],
            "diameter",
            self._format_table_float(self.rows[-1].diameter),
        )
        table.item(image_item, values=values)

    def _refresh_analysis_surface_choices(self) -> None:
        options = ["Auto"]
        for index, row in enumerate(self.rows):
            options.append(f"{index}: {row.name}")
        current = self.analysis_surface_var.get()
        self.analysis_surface_menu["values"] = options
        if current not in options:
            self.analysis_surface_var.set("Auto")
        if hasattr(self, "nonseq_target_surface_menu") and hasattr(self, "nonseq_target_surface_var"):
            target_current = self.nonseq_target_surface_var.get()
            self.nonseq_target_surface_menu["values"] = options
            if target_current not in options:
                self.nonseq_target_surface_var.set("Auto")
        self._schedule_table_grid_update()
        self._schedule_active_cell_border_update()

    @staticmethod
    def _parse_numeric_display(value: str) -> float:
        return float(value.replace("*", "").strip())

    @staticmethod
    def _normalized_rows_copy(rows: list[SurfaceRow]) -> list[SurfaceRow]:
        return _surface_table_normalized_rows_copy(rows, element_advanced_attr=ELEMENT_ADVANCED_ATTR)

    @staticmethod
    def _is_air_like_glass(glass: str) -> bool:
        value = str(glass or "").strip().upper()
        return value in {"", "AIR", "VACUUM", "NONE", "NULL"} or value.startswith("AIR")

    @classmethod
    def _auto_element_label_for_group(
        cls,
        rows: list[SurfaceRow],
        group: list[int],
        element_number: int,
    ) -> tuple[str, bool]:
        if len(group) == 1:
            row = rows[group[0]]
            if row.surface == "Aperture":
                return (str(row.name or "Stop").strip() or "Stop"), False
            if row.surface in {"Mirror", BEAM_SPLITTER_SURFACE, "Thin Lens", "Grating"}:
                return (str(row.name or row.surface).strip() or row.surface), True
        materials: list[str] = []
        for index in group:
            glass = str(rows[index].glass or "").strip()
            if not cls._is_air_like_glass(glass) and glass.upper() != "MIRROR" and glass not in materials:
                materials.append(glass)
        suffix = f" {'/'.join(materials)}" if materials else ""
        return f"E{element_number}{suffix}", True

    @classmethod
    def _auto_assign_missing_elements(cls, rows: list[SurfaceRow]) -> None:
        """Infer Element groups for legacy sequential layouts with no metadata."""
        if not rows or any(cls._element_key(row) for row in rows[1:-1]):
            return
        groups: list[list[int]] = []
        current_group: list[int] = []
        for index, row in enumerate(rows[1:-1], start=1):
            if row.surface in {"Object", "Image"}:
                continue
            if row.surface == "Aperture":
                if current_group:
                    groups.append(current_group)
                    current_group = []
                groups.append([index])
                continue
            if row.surface in {"Mirror", BEAM_SPLITTER_SURFACE, "Thin Lens", "Grating"}:
                if current_group:
                    groups.append(current_group)
                    current_group = []
                groups.append([index])
                continue
            if cls._is_air_like_glass(row.glass):
                if current_group:
                    current_group.append(index)
                    groups.append(current_group)
                    current_group = []
                continue
            current_group.append(index)
        if current_group:
            groups.append(current_group)

        element_number = 1
        for group in groups:
            label, consumes_number = cls._auto_element_label_for_group(rows, group, element_number)
            for index in group:
                rows[index].element = label
            if consumes_number:
                element_number += 1

    @staticmethod
    def _is_empty_starter_rows(rows: list[SurfaceRow]) -> bool:
        return (
            len(rows) == 2
            and rows[0].surface == "Object"
            and rows[-1].surface == "Image"
            and rows[0].glass == "AIR"
            and rows[-1].glass == "AIR"
        )

    def _selected_insert_index(self) -> int | None:
        selected = self.table.selection()
        if not selected:
            return None
        element_blocks = self._selected_element_blocks()
        if element_blocks:
            return max(index for block in element_blocks for index in block)
        indices = self._selected_table_indices()
        if not indices:
            return None
        return indices[-1]

    def _select_inserted_layout_rows(self, layout_rows: list[SurfaceRow], insert_after: int | None) -> None:
        indices = inserted_layout_row_indices(
            len(self.rows),
            layout_rows,
            insert_after=insert_after,
            final_row_is_image=bool(self.rows and self.rows[-1].surface == "Image"),
        )
        if not indices:
            return
        self._select_table_indices(indices, focus_index=indices[0])

    @staticmethod
    def _append_layout_rows(
        existing_rows: list[SurfaceRow],
        layout_rows: list[SurfaceRow],
        insert_after: int | None = None,
        element_name: str = "",
    ) -> list[SurfaceRow]:
        return _surface_table_append_layout_rows(
            existing_rows,
            layout_rows,
            insert_after=insert_after,
            element_name=element_name,
        )

    @classmethod
    def _format_numeric_cell(cls, field: str, row: SurfaceRow, *, display_value: float | None = None) -> str:
        spec = VARIABLE_REGISTRY.get(field)
        value = getattr(row, spec.field if spec is not None else field, 0.0)
        if display_value is not None:
            value = display_value
        text = KrakenLayoutEditor._format_table_float(value)
        return text

    @classmethod
    def _format_sequence_cell(cls, field: str, row: SurfaceRow, values: list[float]) -> str:
        return _format_float_sequence(values)

    @classmethod
    def _format_pose_cell(cls, rows: list[SurfaceRow], row_index: int, field: str) -> str:
        row = rows[row_index]
        values = cls._pose_field_display_values_for_row(rows, row_index, field)
        if len(values) > 1:
            return cls._format_sequence_cell(field, row, values)
        if field == "tilt_x" and row.surface == "Mirror":
            return cls._format_numeric_cell(
                field,
                row,
                display_value=cls._mirror_display_slant_deg_for_rows(rows, row_index),
            )
        return cls._format_numeric_cell(field, row)

    @staticmethod
    def _format_table_float(value: float) -> str:
        return f"{float(value):.12g}"

    @staticmethod
    def _surface_type_enabled_fields(surface_type: str) -> set[str]:
        return set(SURFACE_TYPE_ENABLED_FIELDS.get(str(surface_type), SURFACE_TYPE_ENABLED_FIELDS["Standard"]))

    @classmethod
    def _surface_type_field_enabled(cls, row: SurfaceRow, field: str) -> bool:
        return field in cls._surface_type_enabled_fields(row.surface)

    @classmethod
    def _table_display_value(cls, row: SurfaceRow, field: str, value: object) -> str:
        if not cls._surface_type_field_enabled(row, field):
            return DISABLED_TABLE_CELL_TEXT
        return str(value)

    def _table_display_value_for_row(self, row_index: int, row: SurfaceRow, field: str, value: object) -> str:
        if field in PATH_LOCAL_TABLE_FIELD_MAP and 0 <= row_index < len(self.rows) and self._row_uses_path_local_table_pose(row):
            return str(value)
        return self._table_display_value(row, field, value)

    def _table_cell_enabled(self, row_index: int, field: str) -> bool:
        if not (0 <= row_index < len(self.rows)):
            return True
        if self._path_local_pose_cell_enabled(row_index, field):
            return True
        return self._surface_type_field_enabled(self.rows[row_index], field)

    def _surface_type_disabled_message(self, row_index: int, field: str) -> str:
        row = self.rows[row_index]
        return (
            f"{COLUMN_LABELS.get(field, field)} is not used by {row.surface} rows. "
            "Use Advanced... for KrakenOS-native attributes outside this template."
        )

    @staticmethod
    def _normalize_mirror_slant_deg(angle_deg: float) -> float:
        angle = float(angle_deg)
        while angle <= -90.0:
            angle += 180.0
        while angle > 90.0:
            angle -= 180.0
        if abs(angle) < 1e-12:
            return 0.0
        return angle

    @classmethod
    def _mirror_branch_after_slant_deg(cls, branch_angle_deg: float, slant_angle_deg: float) -> float:
        direction = np.array(
            [np.cos(np.deg2rad(float(branch_angle_deg))), np.sin(np.deg2rad(float(branch_angle_deg)))],
            dtype=float,
        )
        reflected = cls._reflect_2d(direction, float(slant_angle_deg))
        return float(np.rad2deg(np.arctan2(reflected[1], reflected[0])))

    @classmethod
    def _mirror_display_slant_deg_for_rows(cls, rows: list[SurfaceRow], row_index: int) -> float:
        branch_angle = 0.0
        for index, row in enumerate(rows):
            if row.surface != "Mirror":
                continue
            slant_angle = cls._normalize_mirror_slant_deg(branch_angle - 90.0 + float(row.tilt_x))
            if index == row_index:
                return slant_angle
            branch_angle = cls._mirror_branch_after_slant_deg(branch_angle, slant_angle)
        return float(rows[row_index].tilt_x)

    @classmethod
    def _mirror_local_tilt_deg_from_display(
        cls,
        branch_angle_deg: float,
        display_slant_deg: float,
    ) -> float:
        return cls._normalize_mirror_slant_deg(float(display_slant_deg) - branch_angle_deg + 90.0)

    @classmethod
    def _mirror_branch_angle_before_index(cls, rows: list[SurfaceRow], row_index: int) -> float:
        branch_angle = 0.0
        for index, row in enumerate(rows):
            if index >= row_index:
                break
            if row.surface != "Mirror":
                continue
            slant_angle = cls._normalize_mirror_slant_deg(branch_angle - 90.0 + float(row.tilt_x))
            branch_angle = cls._mirror_branch_after_slant_deg(branch_angle, slant_angle)
        return branch_angle

    @staticmethod
    def _advanced_with_galvo_scan_overlay(advanced: dict | None, values: list[float]) -> dict:
        updated = dict(advanced or {})
        display = dict(updated.get("Display2D", {}) or {})
        if values:
            display[GALVO_SCAN_OVERLAY_KEY] = [float(value) for value in values]
            updated["Display2D"] = display
        else:
            display.pop(GALVO_SCAN_OVERLAY_KEY, None)
            if display:
                updated["Display2D"] = display
            else:
                updated.pop("Display2D", None)
        return updated

    @staticmethod
    def _advanced_with_pose_tolerance_overlay(advanced: dict | None, field: str, values: list[float]) -> dict:
        updated = dict(advanced or {})
        display = dict(updated.get("Display2D", {}) or {})
        overlay = dict(display.get(POSE_TOLERANCE_OVERLAY_KEY, {}) or {})
        if field in POSE_TOLERANCE_FIELDS and len(values) > 1:
            overlay[field] = [float(value) for value in values]
        else:
            overlay.pop(field, None)
        if overlay:
            display[POSE_TOLERANCE_OVERLAY_KEY] = overlay
            updated["Display2D"] = display
        else:
            display.pop(POSE_TOLERANCE_OVERLAY_KEY, None)
            if display:
                updated["Display2D"] = display
            else:
                updated.pop("Display2D", None)
        return updated

    @staticmethod
    def _pose_tolerance_overlay_values(row: SurfaceRow, field: str) -> list[float]:
        if field not in POSE_TOLERANCE_FIELDS:
            return []
        advanced = getattr(row, "advanced", {}) or {}
        if not isinstance(advanced, dict):
            return []
        display_settings = advanced.get("Display2D", {})
        if not isinstance(display_settings, dict):
            return []
        overlay = display_settings.get(POSE_TOLERANCE_OVERLAY_KEY, {})
        if not isinstance(overlay, dict):
            return []
        raw_values = overlay.get(field)
        if raw_values in (None, "", "None"):
            return []
        try:
            if isinstance(raw_values, str):
                values = _parse_float_sequence_text(raw_values)
            elif isinstance(raw_values, (int, float)):
                values = [float(raw_values)]
            else:
                values = _dedupe_float_values([float(value) for value in raw_values])
        except Exception:
            return []
        return values if len(values) > 1 else []

    @classmethod
    def _pose_field_display_values_for_row(cls, rows: list[SurfaceRow], row_index: int, field: str) -> list[float]:
        if not (0 <= row_index < len(rows)) or field not in POSE_TOLERANCE_FIELDS:
            return []
        row = rows[row_index]
        if field == "tilt_x" and row.surface == "Mirror":
            return cls._mirror_overlay_display_slants_for_rows(rows, row_index)
        return cls._pose_tolerance_overlay_values(row, field)

    @classmethod
    def _mirror_overlay_display_slants_for_rows(cls, rows: list[SurfaceRow], row_index: int) -> list[float]:
        if not (0 <= row_index < len(rows)) or rows[row_index].surface != "Mirror":
            return []
        local_values = cls._galvo_scan_overlay_values(rows[row_index])
        if not local_values:
            return []
        branch_angle = cls._mirror_branch_angle_before_index(rows, row_index)
        return [
            cls._normalize_mirror_slant_deg(branch_angle - 90.0 + float(local_tilt))
            for local_tilt in local_values
        ]

    def _editable_table_row_service(self) -> EditableTableRowService:
        service = self.__dict__.get("_editable_table_row_service_instance")
        if service is None:
            service = EditableTableRowService(self)
            self._editable_table_row_service_instance = service
        return service

    def _read_rows_from_table(self) -> None:
        self._editable_table_row_service()._read_rows_from_table()

    @classmethod
    def _propagate_element_pose_tolerances(cls, rows: list[SurfaceRow], previous_rows: list[SurfaceRow]) -> None:
        """Treat pose lists on grouped elements as rigid element tolerances.

        A user should not have to enter the same DespY/TiltY list on every
        surface of a doublet. When any grouped row has a pose tolerance list,
        the list is converted into deltas about that row's nominal value and
        applied to every row in the contiguous element block.
        """
        visited: set[tuple[int, int, str]] = set()
        index = 1
        while index < len(rows) - 1:
            element_key = cls._element_key(rows[index])
            if not element_key:
                index += 1
                continue
            start, end = cls._element_block_for_index(rows, index)
            block = list(range(max(start, 1), min(end, len(rows) - 2) + 1))
            if not block:
                index = end + 1
                continue
            for field in POSE_TOLERANCE_FIELDS:
                if field == "tilt_x" and any(rows[row_index].surface == "Mirror" for row_index in block):
                    continue
                key = (start, end, field)
                if key in visited:
                    continue
                visited.add(key)
                source_index = next(
                    (
                        row_index
                        for row_index in block
                        if field in cls._surface_type_enabled_fields(rows[row_index].surface)
                        and len(cls._pose_tolerance_overlay_values(rows[row_index], field)) > 1
                    ),
                    None,
                )
                if source_index is None:
                    continue
                source_values = cls._pose_tolerance_overlay_values(rows[source_index], field)
                if len(source_values) <= 1:
                    continue
                source_nominal = float(getattr(rows[source_index], field))
                previous_source_nominal = (
                    float(getattr(previous_rows[source_index], field))
                    if 0 <= source_index < len(previous_rows)
                    else source_nominal
                )
                nominal_delta = source_nominal - previous_source_nominal
                value_deltas = [float(value) - source_nominal for value in source_values]
                for row_index in block:
                    row = rows[row_index]
                    if field not in cls._surface_type_enabled_fields(row.surface):
                        continue
                    if row_index == source_index:
                        row_nominal = source_nominal
                    else:
                        base_nominal = (
                            float(getattr(previous_rows[row_index], field))
                            if 0 <= row_index < len(previous_rows)
                            else float(getattr(row, field))
                        )
                        row_nominal = base_nominal + nominal_delta
                        setattr(row, field, float(row_nominal))
                    row_values = [float(row_nominal) + delta for delta in value_deltas]
                    row.advanced = cls._advanced_with_pose_tolerance_overlay(row.advanced, field, row_values)
            index = end + 1

    def _on_table_click(self, event: tk.Event) -> str | None:
        region = self.table.identify_region(event.x, event.y)
        if region == "separator":
            self._table_column_resize_active = True
            self._clear_table_grid()
            self._hide_active_cell_border()
            self._schedule_table_grid_update(delay=1)
            return None
        if region == "heading":
            return None
        self._table_column_resize_active = False
        row_id = self.table.identify_row(event.y)
        column_id = self.table.identify_column(event.x)
        self.table.focus_set()
        if not row_id or not column_id:
            self._clear_table_selection()
            return "break"
        self._active_cell = (row_id, column_id)
        children = list(self.table.get_children())
        shift_pressed = bool(event.state & 0x0001)
        control_pressed = bool(event.state & 0x0004)
        if column_id == "#1" and children and not shift_pressed:
            row_index = self._table_item_row_index(row_id)
            if row_index is None:
                if control_pressed:
                    selected = set(self.table.selection())
                    if row_id in selected:
                        selected.remove(row_id)
                    else:
                        selected.add(row_id)
                    ordered = [item for item in children if item in selected]
                    if ordered:
                        self.table.selection_set(ordered)
                    else:
                        self.table.selection_remove(*children)
                else:
                    self.table.selection_set(row_id)
                self._selection_anchor_row = row_id
                self.table.focus(row_id)
                self._schedule_active_cell_border_update()
                return "break"
            block_indices = self._element_indices_for_index(self.rows, row_index)
            block_items = [
                item
                for index in block_indices
                for item in [self._table_item_for_row_index(index)]
                if item is not None
            ]
            self._active_cell = None
            if control_pressed:
                selected = set(self.table.selection())
                if block_items and all(item in selected for item in block_items):
                    selected.difference_update(block_items)
                else:
                    selected.update(block_items or [row_id])
                ordered = [item for item in children if item in selected]
                if ordered:
                    self.table.selection_set(ordered)
                else:
                    self.table.selection_remove(*children)
                self._selection_anchor_row = row_id
                self.table.focus(row_id)
            else:
                self.table.selection_set(block_items or [row_id])
                self._selection_anchor_row = row_id
                self.table.focus(row_id)
            self._schedule_active_cell_border_update()
            return "break"
        if shift_pressed and children:
            anchor = self._selection_anchor_row
            if anchor not in children:
                anchor = self.table.focus() or row_id
            if anchor not in children:
                anchor = row_id
            start = children.index(anchor)
            end = children.index(row_id)
            if start <= end:
                selected_range = children[start : end + 1]
            else:
                selected_range = children[end : start + 1]
            if control_pressed:
                selected = set(self.table.selection())
                selected.update(selected_range)
                ordered = [item for item in children if item in selected]
                self.table.selection_set(ordered)
            else:
                self.table.selection_set(selected_range)
            self.table.focus(row_id)
            self._schedule_active_cell_border_update()
            return "break"
        elif control_pressed:
            selected = set(self.table.selection())
            if row_id in selected:
                selected.remove(row_id)
            else:
                selected.add(row_id)
            ordered = [item for item in children if item in selected]
            self.table.selection_set(ordered)
            self._selection_anchor_row = row_id
            self.table.focus(row_id)
            self._schedule_active_cell_border_update()
            return "break"
        else:
            self.table.selection_set(row_id)
            self._selection_anchor_row = row_id
        self.table.focus(row_id)
        self._schedule_active_cell_border_update()
        return "break"

    def _on_table_drag(self, event: tk.Event) -> str | None:
        if self._table_column_resize_active:
            self._schedule_table_grid_update(delay=1)
            self._schedule_active_cell_border_update(delay=1)
        return None

    def _on_table_button_release(self, event: tk.Event) -> str | None:
        if self._table_column_resize_active:
            self._table_column_resize_active = False
            self._schedule_table_grid_update(delay=1)
            self._schedule_active_cell_border_update(delay=1)
        return None

    def _move_active_cell(self, event: tk.Event) -> str:
        self.table.focus_set()
        children = list(self.table.get_children())
        if not children:
            return "break"
        if self._active_cell is None:
            row_id = children[0]
            column_id = "#2"
        else:
            row_id, column_id = self._active_cell
            if row_id not in children:
                row_id = children[0]
            column_index = int(column_id.replace("#", ""))
            row_index = children.index(row_id)
            if event.keysym == "Left":
                column_index = max(2, column_index - 1)
            elif event.keysym == "Right":
                column_index = min(len(FIELDS), column_index + 1)
            elif event.keysym == "Up":
                row_index = max(0, row_index - 1)
            elif event.keysym == "Down":
                row_index = min(len(children) - 1, row_index + 1)
            row_id = children[row_index]
            column_id = f"#{column_index}"
        self._active_cell = (row_id, column_id)
        self.table.focus(row_id)
        self.table.selection_set(row_id)
        self._ensure_active_cell_visible(row_id, column_id)
        self._schedule_active_cell_border_update()
        self._schedule_table_grid_update(delay=1)
        return "break"

    def _ensure_active_cell_visible(self, row_id: str, column_id: str) -> None:
        self.table.see(row_id)
        self.update_idletasks()
        columns = list(self.table["columns"])
        if column_id == "#2":
            self.table.xview_moveto(0.0)
            self.update_idletasks()
        target_bbox = self.table.bbox(row_id, column_id)
        if target_bbox:
            x, _y, width, _height = target_bbox
            visible_width = max(self.table.winfo_width(), 1)
            if x >= 0 and (x + width) <= visible_width:
                self._schedule_active_cell_border_update()
                self._schedule_table_grid_update(delay=1)
                return

        total_width = 0
        target_left = 0
        target_width = 0
        target_field = FIELDS[int(column_id.replace("#", "")) - 1]
        for field in columns:
            width = int(self.table.column(field, "width"))
            if field == target_field:
                target_left = total_width
                target_width = width
            total_width += width
        if total_width <= 0:
            return
        visible_width = max(self.table.winfo_width(), 1)
        view_left, _view_right = self.table.xview()
        visible_left = view_left * total_width
        visible_right = visible_left + visible_width
        if target_left < visible_left:
            desired_left = max(0.0, target_left - 16.0)
            self.table.xview_moveto(desired_left / total_width)
        elif target_left + target_width > visible_right:
            desired_left = max(0.0, target_left + target_width - visible_width + 16.0)
            self.table.xview_moveto(min(1.0, desired_left / total_width))
        self.update_idletasks()
        self._schedule_active_cell_border_update()
        self._schedule_table_grid_update(delay=1)

    def _hide_active_cell_border(self) -> None:
        for part in self._cell_border_parts:
            part.place_forget()

    def _clear_selection_row_borders(self) -> None:
        overlays = self.__dict__.get("_selection_border_overlays", [])
        for part in overlays:
            try:
                part.destroy()
            except Exception:
                pass
        self._selection_border_overlays = []

    def _update_selection_row_borders(self) -> None:
        if "table" not in self.__dict__:
            return
        self._clear_selection_row_borders()
        selected = list(self.table.selection())
        if not selected:
            return
        border_color = "#2563eb"
        table_width = max(int(self.table.winfo_width()), 1)
        columns = list(self.table["columns"])
        children = list(self.table.get_children())
        selected_indices = sorted(children.index(item) for item in selected if item in children)
        if not selected_indices:
            return

        blocks: list[list[int]] = []
        for index in selected_indices:
            if not blocks or index != blocks[-1][-1] + 1:
                blocks.append([index])
            else:
                blocks[-1].append(index)

        def row_bbox(item: str) -> tuple[int, int, int, int] | None:
            for column_index in range(1, len(columns) + 1):
                bbox = self.table.bbox(item, f"#{column_index}")
                if bbox and len(bbox) == 4:
                    return bbox
            return None

        for block in blocks:
            visible_ranges: list[tuple[int, int]] = []
            for index in block:
                item = children[index]
                if not self.table.exists(item):
                    continue
                bbox = row_bbox(item)
                if not bbox:
                    continue
                _x, y, _width, height = bbox
                if height <= 0:
                    continue
                visible_ranges.append((y, y + height))
            if not visible_ranges:
                continue
            y_top = min(start for start, _end in visible_ranges)
            y_bottom = max(end for _start, end in visible_ranges)
            height = max(0, y_bottom - y_top)
            if height <= 0:
                continue
            top = tk.Frame(self.table, bg=border_color, height=2)
            bottom = tk.Frame(self.table, bg=border_color, height=2)
            left = tk.Frame(self.table, bg=border_color, width=2)
            right = tk.Frame(self.table, bg=border_color, width=2)
            top.place(x=0, y=y_top, width=table_width, height=2)
            bottom.place(x=0, y=y_bottom - 2, width=table_width, height=2)
            left.place(x=0, y=y_top, width=2, height=height)
            right.place(x=table_width - 2, y=y_top, width=2, height=height)
            self._selection_border_overlays.extend([top, bottom, left, right])

    def _update_active_cell_border(self, _event: tk.Event | None = None) -> None:
        self._active_cell_border_after_id = None
        if self._active_cell is None:
            self._hide_active_cell_border()
            self._update_selection_row_borders()
            return
        row_id, column_id = self._active_cell
        if not self.table.exists(row_id):
            self._active_cell = None
            self._hide_active_cell_border()
            self._update_selection_row_borders()
            return
        try:
            bbox = self.table.bbox(row_id, column_id)
        except tk.TclError:
            self._hide_active_cell_border()
            self._update_selection_row_borders()
            return
        if not bbox or len(bbox) != 4:
            self._hide_active_cell_border()
            self._update_selection_row_borders()
            return
        x, y, width, height = bbox
        if width <= 0 or height <= 0:
            self._hide_active_cell_border()
            self._update_selection_row_borders()
            return
        self._update_selection_row_borders()
        top, bottom, left, right = self._cell_border_parts
        top.place(x=x, y=y, width=width, height=2)
        bottom.place(x=x, y=y + height - 2, width=width, height=2)
        left.place(x=x, y=y, width=2, height=height)
        right.place(x=x + width - 2, y=y, width=2, height=height)

    def _schedule_active_cell_border_update(self, *, delay: int | None = None) -> None:
        if self._active_cell_border_after_id is not None:
            return
        try:
            if delay is None:
                self._active_cell_border_after_id = self.after_idle(self._update_active_cell_border)
            else:
                self._active_cell_border_after_id = self.after(max(0, int(delay)), self._update_active_cell_border)
        except tk.TclError:
            self._active_cell_border_after_id = None

    def _on_table_scroll(self, scrollbar: ttk.Scrollbar, first: str, last: str) -> None:
        scrollbar.set(first, last)
        self._schedule_table_grid_update()
        self._schedule_active_cell_border_update()

    def _on_table_xview(self, *args: object) -> None:
        self.table.xview(*args)
        self._schedule_table_grid_update(delay=16)
        self._update_active_cell_border()

    def _on_table_xscroll(self, scrollbar: ttk.Scrollbar, first: str, last: str) -> None:
        scrollbar.set(first, last)
        self._update_active_cell_border()

    def _clear_table_grid(self) -> None:
        for part in self._grid_overlays:
            part.destroy()
        self._grid_overlays.clear()

    def _table_grid_context(self) -> tuple[list[str], tuple[str, ...], list[tuple[str, tuple[int, int, int, int]]]]:
        columns = list(self.table["columns"])
        items = tuple(self.table.get_children())
        visible_bboxes = []
        if columns and items:
            column_ids = [f"#{column_index}" for column_index in range(1, len(columns) + 1)]
            for item in items:
                for column_id in column_ids:
                    bbox = self.table.bbox(item, column_id)
                    if bbox:
                        visible_bboxes.append((item, bbox))
                        break
        return columns, items, visible_bboxes

    def _schedule_table_grid_update(self, _event: tk.Event | None = None, delay: int = 30) -> None:
        if self._grid_after_id is not None:
            try:
                self.after_cancel(self._grid_after_id)
            except tk.TclError:
                pass
            self._grid_after_id = None
        try:
            self._grid_after_id = self.after(max(0, int(delay)), self._update_table_grid)
        except tk.TclError:
            self._grid_after_id = None

    def _update_table_grid(self, _event: tk.Event | None = None) -> None:
        self._grid_after_id = None
        self._clear_table_grid()
        columns, items, visible_bboxes = self._table_grid_context()
        grid_color = "#e2e7ef"
        if not columns or not items or not visible_bboxes:
            return
        data_top = min(bbox[1] for _, bbox in visible_bboxes)
        data_bottom = max(bbox[1] + bbox[3] for _, bbox in visible_bboxes)
        data_height = max(0, data_bottom - data_top)
        if data_height <= 0:
            return

        first_item = visible_bboxes[0][0]
        for column_index in range(1, len(columns)):
            bbox = self.table.bbox(first_item, f"#{column_index}")
            if not bbox:
                continue
            x, _y, width, _height = bbox
            separator = tk.Frame(self.table, bg=grid_color, width=1)
            separator.place(x=x + width - 1, y=data_top, width=1, height=data_height)
            self._grid_overlays.append(separator)

        for item, bbox in visible_bboxes:
            _x, y, width, height = bbox
            row_line = tk.Frame(self.table, bg=grid_color, height=1)
            row_line.place(x=0, y=y + height - 1, relwidth=1.0, height=1)
            self._grid_overlays.append(row_line)

        self._draw_optimization_cell_markers(items, columns)
        self._schedule_active_cell_border_update()

    def _draw_optimization_cell_markers(self, items: tuple[str, ...], columns: list[str]) -> None:
        if not items or not columns:
            return
        field_to_column = {field: f"#{index + 1}" for index, field in enumerate(columns)}
        for item in items:
            row_index = self._table_item_row_index(item)
            if row_index is None or not (0 <= row_index < len(self.rows)):
                continue
            row = self.rows[row_index]
            for field in self._optimization_marker_fields_for_row(row):
                column_id = field_to_column.get(field)
                if not column_id:
                    continue
                bbox = self.table.bbox(item, column_id)
                if not bbox or len(bbox) != 4:
                    continue
                x, y, width, height = bbox
                if width <= 24 or height <= 8:
                    continue
                marker_width = min(max(16, int(width * 0.22)), 24)
                marker = tk.Label(
                    self.table,
                    text=OPTIMIZATION_CELL_MARKER_TEXT,
                    bg=OPTIMIZATION_CELL_MARKER_BG,
                    fg=OPTIMIZATION_CELL_MARKER_FG,
                    bd=1,
                    relief="solid",
                    padx=0,
                    pady=0,
                    font=("TkDefaultFont", 8, "bold"),
                )
                marker.place(
                    x=x + width - marker_width - 1,
                    y=y + 2,
                    width=marker_width,
                    height=max(1, height - 4),
                )
                marker.bind(
                    "<Button-1>",
                    lambda event, selected_item=item, selected_field=field: self._on_optimization_marker_click(
                        event,
                        selected_item,
                        selected_field,
                    ),
                )
                marker.bind(
                    "<Button-3>",
                    lambda event, selected_item=item, selected_field=field: self._on_optimization_marker_click(
                        event,
                        selected_item,
                        selected_field,
                    ),
                )
                self._grid_overlays.append(marker)

    def _on_optimization_marker_click(self, event: tk.Event, row_id: str, field: str) -> str:
        if not self.table.exists(row_id) or field not in FIELDS:
            return "break"
        column_id = f"#{FIELDS.index(field) + 1}"
        self._active_cell = (row_id, column_id)
        self.table.focus(row_id)
        self.table.selection_set(row_id)
        self._schedule_active_cell_border_update()
        return "break"

    def _refresh_operand_surface_choices(self) -> None:
        values = ["Auto"]
        for index, row in enumerate(self.rows):
            if row.surface in {"Object", "Image"}:
                continue
            values.append(f"{index}: {row.name}")
        for label, var in self.operand_surface_vars.items():
            current = var.get().strip() if var.get() else "Auto"
            if current not in values:
                var.set("Auto")
        for widget in self.winfo_children():
            self._apply_surface_values_to_descendants(widget, values)

    def _apply_surface_values_to_descendants(self, widget, values) -> None:
        if isinstance(widget, ttk.Combobox):
            textvar = widget.cget("textvariable")
            for var in self.operand_surface_vars.values():
                if str(var) == textvar:
                    widget["values"] = values
                    break
        for child in widget.winfo_children():
            self._apply_surface_values_to_descendants(child, values)

    def _sync_object_controls(self) -> None:
        if not hasattr(self, "field_summary_var"):
            return
        self._apply_image_diameter_mode()
        self._sync_field_mode_ui()
        metrics = self._field_metrics()
        self.field_summary_var.set(
            "Field half-angle: {angle:.3g} deg\nObject semi-height: {obj:.3g} mm\nParaxial image semi-height: {parax:.3g} mm\nReal image semi-height: {real:.3g} mm".format(
                angle=metrics["angle_deg"],
                obj=metrics["object_height"],
                parax=metrics["paraxial_image_height"],
                real=metrics["real_image_height"],
            )
        )
        warning = ""
        if self.rows and self._current_object_mode() == "Finite":
            object_half_size = max(float(self.rows[0].diameter) / 2.0, 0.0)
            if abs(metrics["object_height"]) > object_half_size + 1e-9:
                warning = f"Field semi-height exceeds object half-size ({object_half_size:.3g} mm)."
        self.field_warning_var.set(warning)
        self._update_field_status_hint()

    def _on_object_mode_changed(self, _event=None) -> None:
        self._sync_field_default_from_current_type()
        self._sync_field_mode_ui()
        self._sync_left_mode_controls()
        self._sync_object_controls()
        self._mark_plot_update_pending()

    def _on_image_diameter_mode_changed(self, _event=None) -> None:
        self._apply_image_diameter_mode()
        self._sync_table()
        self._sync_object_controls()
        self._mark_plot_update_pending()

    def _on_camera_model_changed(self, _event=None) -> None:
        self._begin_history_capture()
        camera_name = self._current_camera_model()
        if camera_name == CAMERA_NONE_LABEL:
            self._commit_history_capture()
            self._mark_plot_update_pending()
            return
        diameter = camera_image_diameter_mm(camera_name)
        if diameter is None or not self.rows or self.rows[-1].surface != "Image":
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self.status_var.set(f"Camera selected: {camera_name}; no sensor size available.")
            return
        self._set_image_diameter_mode("Manual")
        self.rows[-1].diameter = float(diameter)
        camera_info = self._current_camera_record() or {}
        step_path = camera_info.get("step_path")
        if self.imported_camera_step_path is None and step_path:
            candidate = Path(step_path).expanduser()
            if candidate.exists():
                self.imported_camera_step_path = candidate
        self._sync_object_diameter_from_manual_image()
        self._sync_table()
        self._sync_object_controls()
        self._commit_history_capture()
        self._mark_plot_update_pending()
        summary = camera_short_summary(camera_name)
        detail = f" ({summary})" if summary else ""
        self.status_var.set(
            f"Camera selected: {camera_name}{detail}; image diameter set to {float(diameter):.6g} mm. Click Update."
        )

    def _apply_initial_field_defaults(self) -> None:
        if self._field_defaults_initialized or not hasattr(self, "field_type_var"):
            return
        if self._current_object_mode() == "Infinity":
            self.field_type_var.set(self._field_type_display_label("Angle"))
            self._last_field_type = "Angle"
            self._field_type_defaults["Angle"] = "0.0"
            self.field_value_var.set("0.0")
        else:
            self.field_type_var.set(self._field_type_display_label("Object Height"))
            self._last_field_type = "Object Height"
            self._field_type_defaults["Object Height"] = "0.0"
            self.field_value_var.set("0.0")
        self._field_defaults_initialized = True
        self._sync_field_mode_ui()

    def _apply_initial_layout_view_defaults(self, name: str) -> None:
        if not hasattr(self, "display_orientation_var"):
            return
        if hasattr(self, "projection_display_mode_var"):
            self.projection_display_mode_var.set(PROJECTION_MODE_AXIS_FIELD)
        if name == FOLDED_STARTER_LAYOUT_TITLE:
            self.display_orientation_var.set("YZ")
            self.object_mode_var.set("Finite")
            self.field_type_var.set(self._field_type_display_label("Object Height"))
            self._last_field_type = "Object Height"
            self._field_type_defaults["Object Height"] = "0.0"
            self.field_value_var.set("0.0")
            self._sync_field_mode_ui()
        elif name == "Reset":
            self.display_orientation_var.set("YZ")
            self.object_mode_var.set("Infinity")
            self.field_type_var.set(self._field_type_display_label("Angle"))
            self._last_field_type = "Angle"
            self._field_type_defaults["Angle"] = "0.0"
            self.field_value_var.set("0.0")
            self._sync_field_mode_ui()
        elif name == "Doublet Lens":
            self.display_orientation_var.set("YZ")
            self.object_mode_var.set("Infinity")
            self.field_type_var.set(self._field_type_display_label("Angle"))
            self._last_field_type = "Angle"
            self._field_type_defaults["Angle"] = "0.0"
            self.field_value_var.set("0.0")
            self._sync_field_mode_ui()
        else:
            self.display_orientation_var.set("YZ")
            self.object_mode_var.set("Finite")
            self.field_type_var.set(self._field_type_display_label("Object Height"))
            self._last_field_type = "Object Height"
            self._field_type_defaults["Object Height"] = "0.0"
            self.field_value_var.set("0.0")
            self._sync_field_mode_ui()

    def _on_field_type_changed(self, _event=None) -> None:
        self._sync_field_default_from_current_type()
        self._sync_field_mode_ui()
        self._sync_object_controls()
        self._mark_plot_update_pending()

    def _sync_field_default_from_current_type(self) -> None:
        if not hasattr(self, "field_value_var"):
            return
        previous_type = getattr(self, "_last_field_type", self._current_field_type())
        field_type = self._current_field_type()
        current_text = self.field_value_var.get().strip()
        if current_text:
            self._field_type_defaults[previous_type] = current_text
        default_text = self._field_type_defaults.get(field_type, "0.0")
        self._last_field_type = field_type
        if current_text != default_text:
            self.field_value_var.set(default_text)

    def _sync_field_mode_ui(self) -> None:
        if not hasattr(self, "field_type_menu"):
            return
        current_type = self._current_field_type()
        if self._current_object_mode() == "Infinity":
            values = [
                "Angle",
                "Paraxial Image Height",
                "Real Image Height",
                "Object Height",
            ]
            note = "Preferred: Field half-angle for infinity object. Image semi-height modes are derived targets."
        else:
            values = [
                "Object Height",
                "Paraxial Image Height",
                "Real Image Height",
                "Angle",
            ]
            note = "Preferred: Object semi-height for finite object. Field half-angle remains available as a derived field."
        self.field_type_menu["values"] = [self._field_type_display_label(value) for value in values]
        self.field_type_var.set(self._field_type_display_label(current_type))
        if hasattr(self, "field_mode_note_var"):
            self.field_mode_note_var.set(note)
        if hasattr(self, "field_value_label_var"):
            self.field_value_label_var.set(self._field_type_value_label(current_type))
        self._sync_field_sample_count_state()
        self._update_field_status_hint()

    def _sync_field_sample_count_state(self) -> None:
        field_count_var = self.__dict__.get("field_count_var")
        field_count_entry = self.__dict__.get("field_count_entry")
        if field_count_var is None or field_count_entry is None:
            return
        if self._current_source_model() != SOURCE_MODEL_DEFAULT:
            return

        saved = self.__dict__.get("_left_mode_saved_values")
        if saved is None:
            saved = {}
            self._left_mode_saved_values = saved

        active = self._field_sampling_is_active()
        try:
            current = str(field_count_var.get()).strip()
        except Exception:
            current = ""

        if active:
            if current == "NA":
                restored = str(saved.pop("field_count_var", "1")).strip()
                if not restored or restored == "NA":
                    restored = "1"
                try:
                    field_count_var.set(restored)
                except Exception:
                    pass
            state = "normal"
        else:
            if current not in {"", "NA"}:
                saved["field_count_var"] = current
            if current != "NA":
                try:
                    field_count_var.set("NA")
                except Exception:
                    pass
            state = "disabled"

        for widget in (field_count_entry, self.__dict__.get("field_count_label")):
            if widget is None:
                continue
            try:
                widget.configure(state=state)
            except Exception:
                pass

    def add_surface(self) -> None:
        self._begin_history_capture()
        arm_key = self._current_arm_view_key()
        selected_indices = self._selected_table_indices()
        if selected_indices:
            insert_at = max(selected_indices) + 1
        elif arm_key:
            insert_at = self._default_insert_index_for_arm_key(arm_key)
        else:
            insert_at = len(self.rows)
            if self.rows and self.rows[-1].surface == "Image":
                insert_at -= 1
        insert_at = max(1, min(insert_at, len(self.rows) - (1 if self.rows and self.rows[-1].surface == "Image" else 0)))
        row = SurfaceRow()
        if arm_key:
            self._apply_arm_key_metadata_to_row(row, arm_key)
        self.rows.insert(insert_at, row)
        self._sync_table()
        self._select_table_indices([insert_at], focus_index=insert_at)
        self._commit_history_capture()
        self.refresh_plot()

    def delete_selected(self) -> None:
        selected = self.table.selection()
        if not selected:
            return
        self._begin_history_capture()
        indices = self._selected_table_indices()
        for index in reversed(indices):
            del self.rows[index]
        self._sync_table()
        self._commit_history_capture()
        self.refresh_plot()

    def delete_optical_step_rows(self, indices) -> int:
        """Delete the promoted optical-solid STEP rows among *indices*.

        Only rows carrying ``StepOverlayPromotion`` metadata are removed, so a
        plain prescription row that happens to be selected is never deleted.
        Returns the number of rows removed.
        """
        targets = sorted(
            {
                int(index)
                for index in indices
                if 0 <= int(index) < len(self.rows)
                and self._is_open3d_promoted_optical_solid_row(self.rows[int(index)])
            },
            reverse=True,
        )
        if not targets:
            return 0
        self._commit_pending_table_edit()
        self._begin_history_capture()
        for index in targets:
            del self.rows[index]
        self._normalize_special_rows()
        self._sync_table()
        self._commit_history_capture()
        self._mark_plot_update_pending()
        return len(targets)

    def duplicate_selected(self) -> None:
        selected = self.table.selection()
        if not selected:
            return
        self._begin_history_capture()
        indices = self._selected_table_indices()
        insert_at = indices[-1] + 1
        duplicates = duplicate_rows_for_indices(self.rows, indices)
        for offset, row in enumerate(duplicates):
            self.rows.insert(insert_at + offset, row)
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices(list(range(insert_at, insert_at + len(duplicates))), focus_index=insert_at)
        self._commit_history_capture()
        self.refresh_plot()

    def _selected_copy_indices(self) -> list[int]:
        indices: list[int] = []
        seen: set[int] = set()
        for block in self._selected_element_blocks():
            for index in block:
                if index <= 0 or index >= len(self.rows) - 1 or index in seen:
                    continue
                seen.add(index)
                indices.append(index)
        return sorted(indices)

    @staticmethod
    def _surface_rows_from_clipboard_records(records: object) -> list[SurfaceRow]:
        return surface_rows_from_records(records)

    @classmethod
    def _surface_rows_from_clipboard_text(cls, text: str) -> list[SurfaceRow]:
        return surface_rows_from_clipboard_text(text)

    def copy_selected_rows_to_clipboard(self, _event: tk.Event | None = None) -> str:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Copy Surfaces", f"Could not read the surface table:\n\n{exc}", parent=self)
            return "break"
        indices = self._selected_copy_indices()
        if not indices:
            self.status_var.set("Select one or more component surface rows before copying.")
            return "break"
        rows = [SurfaceRow(**asdict(self.rows[index])) for index in indices]
        records = surface_rows_to_records(rows)
        self._surface_row_clipboard = records
        text = surface_rows_to_clipboard_text(rows)
        try:
            ok, backend = self._copy_text_to_clipboard(text)
        except Exception as exc:
            self.append_debug(f"Copy surface rows failed: {exc}")
            ok, backend = False, "none"
        suffix = f" ({backend})" if ok else " (internal clipboard only)"
        self.status_var.set(f"Copied {len(rows)} surface row(s){suffix}.")
        return "break"

    def _pasted_surface_rows(self) -> list[SurfaceRow]:
        try:
            text = self.clipboard_get()
        except Exception:
            text = ""
        rows = self._surface_rows_from_clipboard_text(text) if text else []
        if rows:
            return rows
        return self._surface_rows_from_clipboard_records(self._surface_row_clipboard)

    def paste_rows_from_clipboard(self, _event: tk.Event | None = None) -> str:
        rows = self._pasted_surface_rows()
        if not rows:
            self.status_var.set("No copied KrakenOS surface rows are available to paste.")
            return "break"
        rows = pasteable_component_rows(rows)
        if not rows:
            self.status_var.set("Clipboard contains no pasteable component surface rows.")
            return "break"
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Paste Surfaces", f"Could not read the surface table:\n\n{exc}", parent=self)
            return "break"
        self._remap_inserted_element_labels(rows)
        insert_after = self._selected_insert_index()
        self._begin_history_capture()
        insert_at = self._insert_surface_rows(rows, insert_after=insert_after)
        self._commit_history_capture()
        self.current_layout_file = None
        self.status_var.set(f"Pasted {len(rows)} surface row(s) at S{insert_at}. Click Update to trace.")
        self.refresh_plot(suppress_analysis=True)
        return "break"

    def _selected_table_indices(self) -> list[int]:
        indices = [
            index
            for item in self.table.selection()
            for index in [self._table_item_row_index(item)]
            if index is not None
        ]
        return sorted(indices)

    @staticmethod
    def _indices_are_contiguous(indices: list[int]) -> bool:
        return bool(indices) and indices == list(range(indices[0], indices[-1] + 1))

    def _next_manual_element_label(self) -> str:
        used = {self._element_key(row) for row in self.rows if self._element_key(row)}
        counter = 1
        while f"Element {counter}" in used:
            counter += 1
        return f"Element {counter}"

    def group_selected_as_element(self) -> None:
        selected = self.table.selection()
        if not selected:
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Group Element", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        indices = self._selected_table_indices()
        if len(indices) < 2:
            messagebox.showinfo("Group Element", "Select two or more contiguous surface rows first.", parent=self)
            return
        if indices[0] <= 0 or indices[-1] >= len(self.rows) - 1:
            messagebox.showinfo("Group Element", "Object and Image rows cannot be grouped into an element.", parent=self)
            return
        if not self._indices_are_contiguous(indices):
            messagebox.showinfo("Group Element", "Select a contiguous block of rows before grouping.", parent=self)
            return

        self._begin_history_capture()
        label = self._next_manual_element_label()
        for index in indices:
            self.rows[index].element = label
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices(indices, focus_index=indices[0])
        self._commit_history_capture()
        self.status_var.set(f"Grouped rows {indices[0]}-{indices[-1]} as one element.")

    def ungroup_selected_elements(self) -> None:
        selected = self.table.selection()
        if not selected:
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Ungroup Element", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        selected_keys = {
            self._element_key(self.rows[index])
            for index in self._selected_table_indices()
            if 0 <= index < len(self.rows)
        }
        selected_keys.discard("")
        if not selected_keys:
            messagebox.showinfo("Ungroup Element", "The selected rows are not part of an element.", parent=self)
            return

        self._begin_history_capture()
        ungrouped_indices = []
        for index, row in enumerate(self.rows):
            if self._element_key(row) in selected_keys:
                row.element = ""
                row.advanced = dict(row.advanced or {})
                row.advanced.pop(ELEMENT_ADVANCED_ATTR, None)
                ungrouped_indices.append(index)
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices(ungrouped_indices, focus_index=ungrouped_indices[0] if ungrouped_indices else None)
        self._commit_history_capture()
        self.status_var.set(f"Ungrouped {len(ungrouped_indices)} surface row(s).")

    @staticmethod
    def _element_id_from_label(label: str) -> str:
        text = re.sub(r"[^A-Za-z0-9]+", "_", str(label or "").strip()).strip("_")
        return text or "Element"

    @staticmethod
    def _unique_element_label(base: str, used: set[str]) -> str:
        stem = str(base or "Element").strip() or "Element"
        if stem not in used:
            used.add(stem)
            return stem
        counter = 2
        while True:
            candidate = f"{stem} {counter}"
            if candidate not in used:
                used.add(candidate)
                return candidate
            counter += 1

    def _remap_inserted_element_labels(self, rows: list[SurfaceRow]) -> None:
        """Keep inserted/copied element blocks independent from existing blocks."""
        used = {self._element_key(row) for row in self.rows if self._element_key(row)}
        mapping: dict[str, str] = {}
        for row in rows:
            old_label = self._element_key(row)
            if not old_label:
                continue
            new_label = mapping.get(old_label)
            if new_label is None:
                new_label = self._unique_element_label(old_label, used)
                mapping[old_label] = new_label
            row.element = new_label
            metadata = self._element_metadata(row)
            if _element_metadata_is_default(metadata):
                continue
            metadata["element_name"] = new_label
            metadata["element_id"] = self._element_id_from_label(new_label)
            self._set_element_metadata(row, metadata)

    def _selected_element_blocks(self) -> list[list[int]]:
        blocks: list[list[int]] = []
        seen: set[tuple[int, int]] = set()
        for index in self._selected_table_indices():
            if index <= 0 or index >= len(self.rows) - 1:
                continue
            if self._element_key(self.rows[index]):
                start, end = self._element_block_for_index(self.rows, index)
            else:
                start, end = index, index
            key = (start, end)
            if key in seen:
                continue
            seen.add(key)
            blocks.append(list(range(start, end + 1)))
        return blocks

    def _ensure_element_for_block(self, indices: list[int]) -> str:
        existing = next((self._element_key(self.rows[index]) for index in indices if self._element_key(self.rows[index])), "")
        label = existing or str(self.rows[indices[0]].name or self._next_manual_element_label()).strip()
        if not label:
            label = self._next_manual_element_label()
        for index in indices:
            self.rows[index].element = label
        return label

    def _beam_splitter_element_choices(self) -> list[str]:
        choices = [""]
        for index, row in enumerate(self.rows):
            if row.surface != BEAM_SPLITTER_SURFACE:
                continue
            label = self._element_key(row) or str(row.name or f"S{index}").strip() or f"S{index}"
            if label not in choices:
                choices.append(label)
        return choices

    def _metadata_matches_leg_id(
        self,
        metadata: dict[str, object],
        leg_id: str,
        *,
        row: SurfaceRow | None = None,
        row_index: int | None = None,
    ) -> bool:
        return self._leg_id_from_element_metadata(metadata, row=row, row_index=row_index) == str(leg_id or "").strip().lower()

    def _indices_for_leg_key(self, arm_key: str) -> list[int]:
        leg_id = self._leg_id_from_arm_key(arm_key)
        if not leg_id or not self.rows:
            return []
        indices: list[int] = []
        auto_entry = self._auto_leg_entry_for_id(leg_id)
        if auto_entry is not None:
            for index in sorted(set(auto_entry.get("surface_indices", set()) or set())):
                if 0 <= int(index) < len(self.rows):
                    indices.append(int(index))
        seen_blocks: set[tuple[int, int]] = set()
        index = 0 if leg_id == "input" else 1
        last_inclusive = len(self.rows) if leg_id in {"detector", "cross", "return"} or auto_entry is not None else max(len(self.rows) - 1, 0)
        while index < last_inclusive:
            start, end = self._element_block_for_index(self.rows, index)
            block_key = (start, end)
            metadata = self._element_metadata(self.rows[start])
            if block_key not in seen_blocks and self._metadata_matches_leg_id(
                metadata,
                leg_id,
                row=self.rows[start],
                row_index=start,
            ):
                indices.extend(candidate for candidate in range(start, end + 1) if candidate not in indices)
                seen_blocks.add(block_key)
            index = max(end + 1, index + 1)
        return indices

    def _indices_for_arm_key(self, arm_key: str) -> list[int]:
        key = str(arm_key or "").strip()
        if not key or not self.rows:
            return []
        if self._leg_id_from_arm_key(key):
            return self._indices_for_leg_key(key)
        indices: list[int] = []
        seen_blocks: set[tuple[int, int]] = set()
        index = 1
        while index < len(self.rows) - 1:
            start, end = self._element_block_for_index(self.rows, index)
            block_key = (start, end)
            metadata = self._element_metadata(self.rows[start])
            metadata_key = self._arm_key_from_metadata(metadata)
            path = self._branch_path_for_arm_key(key)
            matches_key = metadata_key == key
            if path and self._metadata_arm_key_matches_branch_path(metadata_key, path):
                matches_key = True
            if block_key not in seen_blocks and matches_key:
                indices.extend(range(start, end + 1))
                seen_blocks.add(block_key)
            index = max(end + 1, index + 1)
        return indices

    def _move_blocks_to_physical_leg_position(
        self,
        blocks: list[list[int]],
        leg_id: str,
    ) -> list[int]:
        leg_id = str(leg_id or "").strip().lower()
        leg_order = {
            defined_id: order
            for order, (defined_id, _short_label, _detail) in enumerate(self._physical_leg_definitions())
        }
        target_order = leg_order.get(leg_id)
        if target_order is None or not blocks:
            return []

        selected_positions: set[int] = set()
        for block in blocks:
            for index in block:
                if 0 < index < len(self.rows) - 1:
                    selected_positions.add(int(index))
        if not selected_positions:
            return []

        selected_rows = [row for index, row in enumerate(self.rows) if index in selected_positions]
        remaining_rows = [row for index, row in enumerate(self.rows) if index not in selected_positions]
        if not selected_rows or len(remaining_rows) < 2:
            return []

        def block_leg_id(rows: list[SurfaceRow], start: int) -> str:
            if not (0 <= start < len(rows)):
                return ""
            metadata = self._element_metadata(rows[start])
            return self._leg_id_from_element_metadata(metadata, row=rows[start], row_index=start)

        insert_at = max(1, len(remaining_rows) - 1)
        index = 1
        while index < len(remaining_rows):
            start, end = self._element_block_for_index(remaining_rows, index)
            if remaining_rows[start].surface == "Image":
                insert_at = start
                break
            existing_order = leg_order.get(block_leg_id(remaining_rows, start))
            if existing_order is not None and existing_order > target_order:
                insert_at = start
                break
            index = max(end + 1, index + 1)

        self.rows = remaining_rows[:insert_at] + selected_rows + remaining_rows[insert_at:]
        return list(range(insert_at, insert_at + len(selected_rows)))

    def _surface_indices_for_arm_key(self, arm_key: str) -> set[int]:
        indices = set(self._indices_for_arm_key(arm_key))
        path = self._branch_path_for_arm_key(arm_key)
        if path:
            indices.update(self._branch_path_surface_indices(path))
        return indices

    def _refresh_arm_view_choices(self) -> None:
        menu = self.__dict__.get("arm_view_menu")
        if menu is None:
            return
        choices = [ARM_VIEW_DEFAULT]
        for entry in self._arm_catalog():
            label = entry["label"]
            if label not in choices:
                choices.append(label)
        menu["values"] = choices
        current = str(self.arm_view_var.get() or ARM_VIEW_DEFAULT).strip()
        if current not in choices:
            self.arm_view_var.set(ARM_VIEW_DEFAULT)

    def _arm_key_for_view_label(self, label: str) -> str:
        text = str(label or ARM_VIEW_DEFAULT).strip()
        if text == ARM_VIEW_DEFAULT:
            return ""
        for entry in self._arm_catalog():
            if entry["label"] == text:
                return entry["key"]
        return ""

    def set_arm_view(self, _event: tk.Event | None = None) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Path View", f"Could not read the surface table:\n\n{exc}", parent=self)
            self.arm_view_var.set(ARM_VIEW_DEFAULT)
            return
        self._refresh_arm_view_choices()
        focus_label = str(self.arm_view_var.get() or ARM_VIEW_DEFAULT).strip()
        self._sync_table()
        if focus_label == ARM_VIEW_DEFAULT:
            self.status_var.set("Path view set to All paths; all components, table rows, and traced paths are shown.")
        else:
            key = self._arm_key_for_view_label(focus_label)
            indices = self._indices_for_arm_key(key)
            if indices and self.__dict__.get("table") is not None:
                self._select_table_indices(indices, focus_index=indices[0])
            self.status_var.set(
                f"Path view set to {focus_label}; table and 2-D plot show common path plus this path."
            )
        self.refresh_plot()

    @staticmethod
    def _normalized_vector(values) -> np.ndarray:
        vector = np.asarray(values, dtype=float).reshape(3)
        norm = float(np.linalg.norm(vector))
        if norm <= 1e-12:
            raise ValueError("Cannot normalize a zero vector.")
        return vector / norm

    @staticmethod
    def _surface_tilts_for_normal(direction) -> tuple[float, float, float]:
        unit = KrakenLayoutEditor._normalized_vector(direction)
        dx, dy, dz = (float(value) for value in unit)
        tilt_y = float(np.rad2deg(np.arcsin(np.clip(dx, -1.0, 1.0))))
        tilt_x = float(np.rad2deg(np.arctan2(-dy, dz)))
        return (tilt_x, tilt_y, 0.0)

    @staticmethod
    def _kraken_tilts_from_rotation_matrix(rotation) -> tuple[float, float, float]:
        return optical_solid_metadata.kraken_tilts_from_rotation_matrix(rotation)

    @staticmethod
    def _path_local_pose(
        frame: dict[str, object],
        *,
        local_decenter_x: float = 0.0,
        local_decenter_y: float = 0.0,
        local_tilt_x: float = 0.0,
        local_tilt_y: float = 0.0,
        local_tilt_z: float = 0.0,
    ) -> tuple[np.ndarray, tuple[float, float, float]]:
        base_tilts = tuple(float(value) for value in frame["tilts"])  # type: ignore[index]
        base_rotation = _rotation_matrix_from_kraken_tilts(*base_tilts)
        local_rotation = _rotation_matrix_from_kraken_tilts(local_tilt_x, local_tilt_y, local_tilt_z)
        combined = base_rotation @ local_rotation
        local_offset = (
            base_rotation[:, 0] * float(local_decenter_x)
            + base_rotation[:, 1] * float(local_decenter_y)
        )
        tilts = KrakenLayoutEditor._kraken_tilts_from_rotation_matrix(combined)
        return np.asarray(local_offset, dtype=float), tilts

    def _surface_transform_for_rows(self, rows: list[SurfaceRow], row_index: int) -> np.ndarray:
        system = _build_system_from_specs(self._serializable_specs_for_rows(rows))
        transforms = self._system_transform_list(system)
        if transforms is None or not (0 <= row_index < len(transforms)):
            raise RuntimeError("KrakenOS did not provide surface transforms for path placement.")
        return np.asarray(transforms[row_index], dtype=float)

    def _arm_frame_for_splitter(self, splitter_index: int, arm_role: str) -> dict[str, np.ndarray | tuple[float, float, float]]:
        if not (0 <= splitter_index < len(self.rows)):
            raise RuntimeError("Selected splitter row is out of range.")
        row = self.rows[splitter_index]
        if row.surface != BEAM_SPLITTER_SURFACE:
            raise RuntimeError("Path placement starts from a Beam Splitter row.")
        transform = self._surface_transform_for_rows(self.rows, splitter_index)
        origin = np.asarray(transform[:3, 3], dtype=float)
        normal = self._normalized_vector(transform[:3, 2])
        incoming = np.asarray([0.0, 0.0, 1.0], dtype=float)
        role = str(arm_role).strip()
        if role == "Transmit":
            direction = incoming
        elif role == "Reflect":
            direction = incoming - 2.0 * float(np.dot(incoming, normal)) * normal
        else:
            raise RuntimeError(f"Unsupported path role for placement: {arm_role}")
        direction = self._normalized_vector(direction)
        return {
            "origin": origin,
            "direction": direction,
            "tilts": self._surface_tilts_for_normal(direction),
        }

    def _branch_path_frame(self, branch_path: str) -> dict[str, np.ndarray | tuple[float, float, float] | int]:
        path = str(branch_path or "").strip()
        if not path or path == "primary":
            raise RuntimeError("Choose a traced non-primary Path view first.")
        surface_indices = self._branch_path_surface_sequence(path)
        if not surface_indices:
            raise RuntimeError(f"Could not identify splitter surfaces in traced path: {path}")
        origin_surface = int(surface_indices[-1])
        bundle = getattr(self, "_last_scene_bundle", None)
        candidates = []
        for ray in getattr(bundle, "ray_paths", []) or []:
            if str(getattr(ray, "branch_path", "") or "").strip() != path:
                continue
            surface_ids = np.asarray(getattr(ray, "surface_ids", []), dtype=int).ravel()
            points = np.asarray(getattr(ray, "points_world", []), dtype=float)
            if points.ndim != 2 or points.shape[1] != 3 or points.shape[0] < 2:
                continue
            hit_positions = np.flatnonzero(surface_ids == origin_surface)
            if hit_positions.size == 0:
                continue
            hit_index = int(hit_positions[-1])
            point_index = min(hit_index + 1, points.shape[0] - 1)
            origin = np.asarray(points[point_index], dtype=float)
            if point_index + 1 < points.shape[0]:
                direction = np.asarray(points[point_index + 1], dtype=float) - origin
            elif point_index > 0:
                direction = origin - np.asarray(points[point_index - 1], dtype=float)
            else:
                continue
            norm = float(np.linalg.norm(direction))
            if not np.isfinite(norm) or norm <= 1e-9:
                continue
            candidates.append((origin, direction / norm))
        if not candidates:
            raise RuntimeError(
                "No traced ray segment is available for this BRANCH_PATH. Click Update, choose a traced Path view, then retry."
            )
        origins = np.vstack([origin for origin, _direction in candidates])
        directions = np.vstack([direction for _origin, direction in candidates])
        origin = np.nanmedian(origins, axis=0)
        direction = np.nanmean(directions, axis=0)
        direction = self._normalized_vector(direction)
        return {
            "origin": np.asarray(origin, dtype=float),
            "direction": direction,
            "tilts": self._surface_tilts_for_normal(direction),
            "origin_surface": origin_surface,
            "sample_count": len(candidates),
        }

    @staticmethod
    def _line_frame_near_point(origin, direction, reference_point) -> dict[str, object]:
        base_origin = np.asarray(origin, dtype=float).reshape(3)
        base_direction = KrakenLayoutEditor._normalized_vector(direction)
        reference = np.asarray(reference_point, dtype=float).reshape(3)
        projection = float(np.dot(reference - base_origin, base_direction))
        target = base_origin + base_direction * projection
        return {
            "origin": base_origin,
            "direction": base_direction,
            "target_point": target,
        }

    @staticmethod
    def _row_local_point_from_world(target_point, z_station: float) -> tuple[float, float, float]:
        point = np.asarray(target_point, dtype=float).reshape(3)
        if not np.all(np.isfinite(point)):
            raise ValueError("Target point must be finite.")
        return (float(point[0]), float(point[1]), float(point[2]) - float(z_station))

    def _optical_solid_face_reference_point(
        self,
        row_index: int,
        metadata: dict[str, object],
        *,
        face_id: str = "",
    ) -> np.ndarray:
        z_positions = self._row_z_positions()
        z_station = float(z_positions[row_index]) if 0 <= row_index < len(z_positions) else 0.0
        row = SurfaceRow(**asdict(self.rows[row_index]))
        row.advanced = dict(row.advanced or {})
        row.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata
        selected_id = str(face_id or "").strip()
        for face in optical_solid_face_world_records(row, z_station, assigned_only=False):
            if selected_id and str(face.get("face_id", "") or "").strip() != selected_id:
                continue
            anchor = np.asarray(
                face.get("anchor_world", face.get("centroid_world", (np.nan, np.nan, np.nan))),
                dtype=float,
            ).reshape(-1)[:3]
            if anchor.size == 3 and np.all(np.isfinite(anchor)):
                return anchor
        return np.asarray((float(row.desp_x), float(row.desp_y), z_station + float(row.desp_z)), dtype=float)

    def _nearest_traced_ray_frame_near_point(self, reference_point, *, branch_path: str = "") -> dict[str, object]:
        reference = np.asarray(reference_point, dtype=float).reshape(3)
        if not np.all(np.isfinite(reference)):
            raise RuntimeError("Reference point is not finite.")
        target_branch = str(branch_path or "").strip()
        bundle = getattr(self, "_last_scene_bundle", None)
        candidates: list[dict[str, object]] = []
        for path in getattr(bundle, "ray_paths", []) or []:
            path_branch = str(getattr(path, "branch_path", "") or "").strip()
            if target_branch and path_branch != target_branch:
                continue
            points = np.asarray(getattr(path, "points_world", []), dtype=float)
            if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
                continue
            try:
                target_point, direction = self._closest_polyline_point_and_direction(points[:, :3], reference)
                distance = float(np.linalg.norm(np.asarray(target_point, dtype=float)[:3] - reference))
            except Exception:
                continue
            if not np.isfinite(distance):
                continue
            candidates.append(
                {
                    "distance": distance,
                    "target_point": np.asarray(target_point, dtype=float).reshape(3),
                    "direction": np.asarray(direction, dtype=float).reshape(3),
                    "branch_path": path_branch,
                    "source_id": str(getattr(path, "source_id", "") or "").strip(),
                    "ray_index": int(getattr(path, "ray_index", -1)),
                }
            )
        if not candidates:
            detail = f" for path {target_branch}" if target_branch else ""
            raise RuntimeError(f"No traced 3D ray path is available{detail}. Click Update first.")
        closest = min(candidates, key=lambda item: float(item["distance"]))
        closest_branch = str(closest.get("branch_path", "") or "")
        branch_candidates = [item for item in candidates if str(item.get("branch_path", "") or "") == closest_branch]
        branch_candidates.sort(key=lambda item: float(item["distance"]))
        sample_limit = min(len(branch_candidates), 25)
        samples = branch_candidates[:sample_limit]
        points = np.vstack([np.asarray(item["target_point"], dtype=float).reshape(3) for item in samples])
        directions = np.vstack([np.asarray(item["direction"], dtype=float).reshape(3) for item in samples])
        target_point = np.nanmedian(points, axis=0)
        direction = np.nanmean(directions, axis=0)
        try:
            direction = self._normalized_vector(direction)
        except Exception:
            direction = self._normalized_vector(closest["direction"])
        return {
            "origin": np.asarray(target_point, dtype=float),
            "direction": np.asarray(direction, dtype=float),
            "target_point": np.asarray(target_point, dtype=float),
            "branch_path": closest_branch,
            "sample_count": int(len(samples)),
            "distance_mm": float(closest["distance"]),
            "ray_index": int(closest.get("ray_index", -1)),
            "source_id": str(closest.get("source_id", "") or ""),
        }

    def _traced_frame_after_table_surface(self, row_index: int, reference_point) -> dict[str, object]:
        reference = np.asarray(reference_point, dtype=float).reshape(3)
        if not np.all(np.isfinite(reference)):
            raise RuntimeError("Reference point is not finite.")
        bundle = getattr(self, "_last_scene_bundle", None)
        for surface_index in range(int(row_index) - 1, 0, -1):
            candidates: list[dict[str, object]] = []
            for path in getattr(bundle, "ray_paths", []) or []:
                surface_ids = np.asarray(getattr(path, "surface_ids", []), dtype=int).ravel()
                points = np.asarray(getattr(path, "points_world", []), dtype=float)
                if surface_ids.size == 0 or points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
                    continue
                hit_positions = np.flatnonzero(surface_ids == int(surface_index))
                if hit_positions.size == 0:
                    continue
                hit_index = int(hit_positions[-1])
                point_index = min(hit_index + 1, points.shape[0] - 1)
                if point_index + 1 < points.shape[0]:
                    origin = np.asarray(points[point_index], dtype=float)
                    direction = np.asarray(points[point_index + 1], dtype=float) - origin
                elif point_index > 0:
                    origin = np.asarray(points[point_index], dtype=float)
                    direction = origin - np.asarray(points[point_index - 1], dtype=float)
                else:
                    continue
                norm = float(np.linalg.norm(direction))
                if not np.isfinite(norm) or norm <= 1e-9:
                    continue
                line_frame = self._line_frame_near_point(origin, direction, reference)
                distance = float(np.linalg.norm(np.asarray(line_frame["target_point"], dtype=float) - reference))
                if not np.isfinite(distance):
                    continue
                candidates.append(
                    {
                        "distance": distance,
                        "target_point": np.asarray(line_frame["target_point"], dtype=float).reshape(3),
                        "direction": np.asarray(line_frame["direction"], dtype=float).reshape(3),
                        "branch_path": str(getattr(path, "branch_path", "") or "").strip(),
                        "source_id": str(getattr(path, "source_id", "") or "").strip(),
                        "ray_index": int(getattr(path, "ray_index", -1)),
                    }
                )
            if not candidates:
                continue
            candidates.sort(key=lambda item: float(item["distance"]))
            sample_limit = min(len(candidates), 25)
            samples = candidates[:sample_limit]
            points = np.vstack([np.asarray(item["target_point"], dtype=float).reshape(3) for item in samples])
            directions = np.vstack([np.asarray(item["direction"], dtype=float).reshape(3) for item in samples])
            target_point = np.nanmedian(points, axis=0)
            direction = np.nanmean(directions, axis=0)
            try:
                direction = self._normalized_vector(direction)
            except Exception:
                direction = self._normalized_vector(samples[0]["direction"])
            return {
                "origin": np.asarray(target_point, dtype=float),
                "direction": np.asarray(direction, dtype=float),
                "target_point": np.asarray(target_point, dtype=float),
                "branch_path": str(samples[0].get("branch_path", "") or ""),
                "sample_count": int(len(samples)),
                "distance_mm": float(samples[0]["distance"]),
                "ray_index": int(samples[0].get("ray_index", -1)),
                "source_id": str(samples[0].get("source_id", "") or ""),
                "source_surface_index": int(surface_index),
            }
        raise RuntimeError("No traced outgoing segment is available before this row. Click Update first.")

    def _solve_optical_solid_path_input_pose(self, row_index: int, metadata: dict[str, object]) -> dict[str, object] | None:
        if not (0 <= row_index < len(self.rows)):
            return None
        normalized = normalize_optical_solid_face_metadata(metadata)
        input_face = optical_solid_metadata.optical_solid_input_anchor_face(normalized)
        if input_face is None:
            return None
        face_id = str(input_face.get("face_id", "") or "").strip()
        z_positions = self._row_z_positions()
        z_station = float(z_positions[row_index]) if 0 <= row_index < len(z_positions) else 0.0
        reference = self._optical_solid_face_reference_point(row_index, normalized, face_id=face_id)
        frame_source = "nearest traced ray"
        branch_path = self._current_path_view_branch_path()
        if branch_path:
            try:
                frame = self._current_path_view_frame_near_point(reference)
                frame_source = "current Path view"
            except Exception:
                frame = self._traced_frame_after_table_surface(row_index, reference)
                frame_source = "previous table surface"
        else:
            try:
                frame = self._traced_frame_after_table_surface(row_index, reference)
                frame_source = "previous table surface"
            except Exception:
                frame = self._nearest_traced_ray_frame_near_point(reference)
        direction = self._normalized_vector(frame["direction"])
        target_world = np.asarray(frame["target_point"], dtype=float).reshape(3)
        solution = solve_optical_solid_face_fit(
            normalized,
            face_id=face_id,
            target_normal=tuple(float(value) for value in -direction),
            target_point=self._row_local_point_from_world(target_world, z_station),
            roll_mode=OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT,
        )
        if solution is not None:
            solution["fit_source"] = frame_source
            solution["target_world_point"] = tuple(float(value) for value in target_world)
            solution["path_direction"] = tuple(float(value) for value in direction)
            solution["branch_path"] = str(frame.get("branch_path", "") or "")
            solution["sample_count"] = int(frame.get("sample_count", 0))
            solution["distance_mm"] = float(frame.get("distance_mm", 0.0) or 0.0)
        return solution

    def _selected_ray_index_from_ui(self) -> int | None:
        table = self._ray_inspector_ray_table
        if table is not None:
            selected = table.selection()
            if selected:
                try:
                    return int(selected[0])
                except Exception:
                    pass
        inspector = getattr(self, "_three_d_inspector", None)
        picked = getattr(inspector, "_picked_ray_index", None) if inspector is not None else None
        if picked is not None:
            try:
                return int(picked)
            except Exception:
                pass
        plotter = getattr(self, "_legacy_3d_plotter", None)
        if plotter is not None:
            try:
                picked = getattr(plotter, "_kraken_selected_ray", None)
                if picked is not None:
                    return int(picked)
            except Exception:
                pass
        return None

    def _ray_path_by_index(self, ray_index: int):
        bundle = getattr(self, "_last_scene_bundle", None)
        for path in getattr(bundle, "ray_paths", []) or []:
            try:
                if int(getattr(path, "ray_index", -1)) == int(ray_index):
                    return path
            except Exception:
                continue
        return None

    def _ray_terminal_hint_text(self, ray_index: int, *, label: str | None = None) -> str:
        try:
            index = int(ray_index)
        except Exception:
            return ""
        text = str(label or f"Ray {index}")
        path = self._ray_path_by_index(index)
        if path is None:
            return text
        detail = ray_path_terminal_diagnostic_text(path)
        return f"{text}: {detail}" if detail else text

    def _ray_frame_near_point(self, ray_index: int, reference_point) -> dict[str, object]:
        ray_index = int(ray_index)
        path = self._ray_path_by_index(ray_index)
        if path is None:
            raise RuntimeError(f"Ray {ray_index} is not available in the current preview.")
        points = np.asarray(getattr(path, "points_world", []), dtype=float)
        if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
            raise RuntimeError("Selected ray does not contain a valid 3D polyline.")
        target_point, direction = self._closest_polyline_point_and_direction(points[:, :3], np.asarray(reference_point, dtype=float))
        return {
            "ray_index": int(ray_index),
            "origin": np.asarray(target_point, dtype=float),
            "direction": np.asarray(direction, dtype=float),
            "target_point": np.asarray(target_point, dtype=float),
            "branch_path": str(getattr(path, "branch_path", "") or ""),
            "source_id": str(getattr(path, "source_id", "") or ""),
        }

    def _selected_ray_frame_near_point(self, reference_point) -> dict[str, object]:
        ray_index = self._selected_ray_index_from_ui()
        if ray_index is None:
            raise RuntimeError("Select a traced ray first in the 2D plot, 3D view, or Ray Inspector.")
        return self._ray_frame_near_point(ray_index, reference_point)

    def _current_path_view_branch_path(self) -> str:
        focus_label = str(self.arm_view_var.get() or ARM_VIEW_DEFAULT).strip()
        if not focus_label or focus_label == ARM_VIEW_DEFAULT:
            return ""
        key = self._arm_key_for_view_label(focus_label)
        return self._branch_path_for_arm_key(key)

    def _current_path_view_frame_near_point(self, reference_point) -> dict[str, object]:
        branch_path = self._current_path_view_branch_path()
        if not branch_path:
            raise RuntimeError("Choose a traced Path view first.")
        frame = self._branch_path_frame(branch_path)
        line_frame = self._line_frame_near_point(frame["origin"], frame["direction"], reference_point)
        line_frame["branch_path"] = branch_path
        line_frame["sample_count"] = int(frame.get("sample_count", 0))
        line_frame["origin_surface"] = int(frame.get("origin_surface", -1))
        return line_frame

    @staticmethod
    def _normalize_path_component_type(component_type: object) -> str:
        text = str(component_type or "").strip()
        lookup = {re.sub(r"[^a-z0-9]", "", value.lower()): value for value in PATH_COMPONENT_TYPES}
        return lookup.get(re.sub(r"[^a-z0-9]", "", text.lower()), PATH_COMPONENT_DETECTOR)

    def _next_path_component_element_label(self, arm_role: str, component_type: object) -> str:
        kind = self._normalize_path_component_type(component_type)
        suffix = PATH_COMPONENT_LABEL_SUFFIXES.get(kind, "component")
        base = f"{arm_role} {suffix}"
        used = {self._element_key(row) for row in self.rows if self._element_key(row)}
        if base not in used:
            return base
        counter = 2
        while f"{base} {counter}" in used:
            counter += 1
        return f"{base} {counter}"

    def _next_branch_path_component_element_label(self, branch_path: str, component_type: object) -> str:
        selectors = "".join(self._branch_path_selector_sequence(branch_path)) or "Path"
        return self._next_path_component_element_label(f"Path {selectors}", component_type)

    def _next_detector_element_label(self, arm_role: str) -> str:
        return self._next_path_component_element_label(arm_role, PATH_COMPONENT_DETECTOR)

    def _path_component_row_for_arm(
        self,
        splitter_index: int,
        arm_role: str,
        component_type: object,
        distance_mm: float,
        diameter_mm: float,
        *,
        parameter_mm: float | None = None,
        glass: str = "AIR",
        insert_at: int | None = None,
        local_decenter_x: float = 0.0,
        local_decenter_y: float = 0.0,
        local_tilt_x: float = 0.0,
        local_tilt_y: float = 0.0,
        local_tilt_z: float = 0.0,
    ) -> SurfaceRow:
        distance = float(distance_mm)
        diameter = float(diameter_mm)
        if not np.isfinite(distance) or distance <= 0.0:
            raise RuntimeError("Path component distance must be positive.")
        if not np.isfinite(diameter) or diameter <= 0.0:
            raise RuntimeError("Path component diameter must be positive.")
        role = str(arm_role).strip()
        if role not in {"Transmit", "Reflect"}:
            raise RuntimeError("Path placement supports Transmit or Reflect paths.")
        kind = self._normalize_path_component_type(component_type)
        insert_index = len(self.rows) - 1 if insert_at is None else int(insert_at)
        insert_index = max(1, min(insert_index, len(self.rows) - 1))
        frame = self._arm_frame_for_splitter(splitter_index, role)
        origin = np.asarray(frame["origin"], dtype=float)
        direction = np.asarray(frame["direction"], dtype=float)
        local_offset, tilts = self._path_local_pose(
            frame,
            local_decenter_x=local_decenter_x,
            local_decenter_y=local_decenter_y,
            local_tilt_x=local_tilt_x,
            local_tilt_y=local_tilt_y,
            local_tilt_z=local_tilt_z,
        )
        tilt_x, tilt_y, tilt_z = tilts
        center = origin + direction * distance + local_offset
        splitter_row = self.rows[splitter_index]
        splitter_metadata = self._element_metadata(splitter_row)
        parent = (
            str(splitter_metadata.get("element_id", "") or "").strip()
            or self._element_key(splitter_row)
            or str(splitter_row.name or f"S{splitter_index}").strip()
        )

        rc = 0.0
        surface = "Standard"
        row_glass = "AIR"
        axis_move = 0.0
        if kind == PATH_COMPONENT_APERTURE:
            surface = "Aperture"
        elif kind == PATH_COMPONENT_THIN_LENS:
            try:
                focal = float(parameter_mm)
            except Exception:
                focal = float("nan")
            if not np.isfinite(focal) or abs(focal) <= 1e-12:
                raise RuntimeError("Thin lens focal length must be a non-zero number.")
            surface = "Thin Lens"
            rc = focal
        elif kind == PATH_COMPONENT_REFRACTIVE_SURFACE:
            try:
                radius = float(parameter_mm)
            except Exception:
                radius = float("nan")
            if not np.isfinite(radius):
                raise RuntimeError("Refractive surface radius must be a finite number.")
            surface = "Standard"
            rc = radius
            row_glass = str(glass or "BK7").strip() or "BK7"
        elif kind in {PATH_COMPONENT_MIRROR, PATH_COMPONENT_OBJECT_TARGET}:
            try:
                radius = 0.0 if parameter_mm is None else float(parameter_mm)
            except Exception:
                radius = float("nan")
            if not np.isfinite(radius):
                raise RuntimeError(f"{kind} radius must be a finite number.")
            surface = OBJECT_TARGET_SURFACE if kind == PATH_COMPONENT_OBJECT_TARGET else "Mirror"
            rc = radius
            row_glass = "MIRROR"
            axis_move = 2.0

        element_label = self._next_path_component_element_label(role, kind)
        metadata_role = "Detector" if kind == PATH_COMPONENT_DETECTOR else role
        component = SurfaceRow(
            element=element_label,
            surface=surface,
            name=element_label,
            rc=rc,
            k=0.0,
            thickness=0.0,
            diameter=diameter,
            glass=row_glass,
            tilt_x=float(tilt_x),
            tilt_y=float(tilt_y),
            tilt_z=float(tilt_z),
            axis_move=axis_move,
            advanced={
                ELEMENT_ADVANCED_ATTR: {
                    "element_id": self._element_id_from_label(element_label),
                    "element_name": element_label,
                    "arm_role": metadata_role,
                    "parent_splitter": parent,
                    "branch_selector": self._branch_selector_for_arm_role(role),
                    "arm_distance": distance,
                    "local_decenter_x": float(local_decenter_x),
                    "local_decenter_y": float(local_decenter_y),
                    "local_tilt_x": float(local_tilt_x),
                    "local_tilt_y": float(local_tilt_y),
                    "local_tilt_z": float(local_tilt_z),
                    "path_component_type": kind,
                },
                **(
                    {DETECTOR_ADVANCED_ATTR: _normalize_detector_settings({"active_width_mm": diameter, "active_height_mm": diameter})}
                    if kind == PATH_COMPONENT_DETECTOR
                    else {}
                ),
                **(
                    {
                        "Display2D": {"label": "Object target"},
                        "Note": (
                            "Object Target traces as a specular reflective proxy. "
                            "Use a Diffuse Object row for Lambertian, Oren-Nayar, Cosine Lobe, or pySCATMECH BRDF scattering."
                        ),
                    }
                    if kind == PATH_COMPONENT_OBJECT_TARGET
                    else {}
                ),
            },
        )
        temp_rows = [SurfaceRow(**asdict(row)) for row in self.rows]
        temp_rows.insert(insert_index, SurfaceRow(**asdict(component)))
        baseline = self._surface_transform_for_rows(temp_rows, insert_index)[:3, 3]
        decenter = center - np.asarray(baseline, dtype=float)
        component.desp_x = float(decenter[0])
        component.desp_y = float(decenter[1])
        component.desp_z = float(decenter[2])
        return component

    def _path_component_row_for_branch_path(
        self,
        branch_path: str,
        component_type: object,
        distance_mm: float,
        diameter_mm: float,
        *,
        parameter_mm: float | None = None,
        glass: str = "AIR",
        insert_at: int | None = None,
        local_decenter_x: float = 0.0,
        local_decenter_y: float = 0.0,
        local_tilt_x: float = 0.0,
        local_tilt_y: float = 0.0,
        local_tilt_z: float = 0.0,
    ) -> SurfaceRow:
        distance = float(distance_mm)
        diameter = float(diameter_mm)
        if not np.isfinite(distance) or distance <= 0.0:
            raise RuntimeError("Path component distance must be positive.")
        if not np.isfinite(diameter) or diameter <= 0.0:
            raise RuntimeError("Path component diameter must be positive.")
        path = str(branch_path or "").strip()
        frame = self._branch_path_frame(path)
        origin = np.asarray(frame["origin"], dtype=float)
        direction = np.asarray(frame["direction"], dtype=float)
        local_offset, tilts = self._path_local_pose(
            frame,
            local_decenter_x=local_decenter_x,
            local_decenter_y=local_decenter_y,
            local_tilt_x=local_tilt_x,
            local_tilt_y=local_tilt_y,
            local_tilt_z=local_tilt_z,
        )
        tilt_x, tilt_y, tilt_z = tilts
        center = origin + direction * distance + local_offset
        kind = self._normalize_path_component_type(component_type)
        insert_index = len(self.rows) - 1 if insert_at is None else int(insert_at)
        insert_index = max(1, min(insert_index, len(self.rows) - 1))
        selector = self._branch_path_leaf_selector(path)
        role = {
            "transmit": "Transmit",
            "reflect": "Reflect",
            "return": "Return",
        }.get(selector, ELEMENT_ARM_ROLE_DEFAULT)

        rc = 0.0
        surface = "Standard"
        row_glass = "AIR"
        axis_move = 0.0
        if kind == PATH_COMPONENT_APERTURE:
            surface = "Aperture"
        elif kind == PATH_COMPONENT_THIN_LENS:
            try:
                focal = float(parameter_mm)
            except Exception:
                focal = float("nan")
            if not np.isfinite(focal) or abs(focal) <= 1e-12:
                raise RuntimeError("Thin lens focal length must be a non-zero number.")
            surface = "Thin Lens"
            rc = focal
        elif kind == PATH_COMPONENT_REFRACTIVE_SURFACE:
            try:
                radius = float(parameter_mm)
            except Exception:
                radius = float("nan")
            if not np.isfinite(radius):
                raise RuntimeError("Refractive surface radius must be a finite number.")
            surface = "Standard"
            rc = radius
            row_glass = str(glass or "BK7").strip() or "BK7"
        elif kind in {PATH_COMPONENT_MIRROR, PATH_COMPONENT_OBJECT_TARGET}:
            try:
                radius = 0.0 if parameter_mm is None else float(parameter_mm)
            except Exception:
                radius = float("nan")
            if not np.isfinite(radius):
                raise RuntimeError(f"{kind} radius must be a finite number.")
            surface = OBJECT_TARGET_SURFACE if kind == PATH_COMPONENT_OBJECT_TARGET else "Mirror"
            rc = radius
            row_glass = "MIRROR"
            axis_move = 2.0

        element_label = self._next_branch_path_component_element_label(path, kind)
        metadata_role = "Detector" if kind == PATH_COMPONENT_DETECTOR else role
        component = SurfaceRow(
            element=element_label,
            surface=surface,
            name=element_label,
            rc=rc,
            k=0.0,
            thickness=0.0,
            diameter=diameter,
            glass=row_glass,
            tilt_x=float(tilt_x),
            tilt_y=float(tilt_y),
            tilt_z=float(tilt_z),
            axis_move=axis_move,
            advanced={
                ELEMENT_ADVANCED_ATTR: {
                    "element_id": self._element_id_from_label(element_label),
                    "element_name": element_label,
                    "arm_role": metadata_role,
                    "parent_splitter": self._branch_path_detail(path),
                    "branch_selector": selector,
                    "branch_path": path,
                    "arm_distance": distance,
                    "local_decenter_x": float(local_decenter_x),
                    "local_decenter_y": float(local_decenter_y),
                    "local_tilt_x": float(local_tilt_x),
                    "local_tilt_y": float(local_tilt_y),
                    "local_tilt_z": float(local_tilt_z),
                    "path_component_type": kind,
                    "path_frame_source": "traced_branch_path",
                    "path_frame_surface": int(frame.get("origin_surface", -1)),
                    "path_frame_samples": int(frame.get("sample_count", 0)),
                },
                **(
                    {DETECTOR_ADVANCED_ATTR: _normalize_detector_settings({"active_width_mm": diameter, "active_height_mm": diameter})}
                    if kind == PATH_COMPONENT_DETECTOR
                    else {}
                ),
                **(
                    {
                        "Display2D": {"label": "Object target"},
                        "Note": (
                            "Object Target traces as a specular reflective proxy. "
                            "Use a Diffuse Object row for Lambertian, Oren-Nayar, Cosine Lobe, or pySCATMECH BRDF scattering."
                        ),
                    }
                    if kind == PATH_COMPONENT_OBJECT_TARGET
                    else {}
                ),
            },
        )
        temp_rows = [SurfaceRow(**asdict(row)) for row in self.rows]
        temp_rows.insert(insert_index, SurfaceRow(**asdict(component)))
        baseline = self._surface_transform_for_rows(temp_rows, insert_index)[:3, 3]
        decenter = center - np.asarray(baseline, dtype=float)
        component.desp_x = float(decenter[0])
        component.desp_y = float(decenter[1])
        component.desp_z = float(decenter[2])
        return component

    @staticmethod
    def _block_axial_offsets(rows: list[SurfaceRow]) -> list[float]:
        offsets: list[float] = []
        axial = 0.0
        for row in rows:
            offsets.append(float(axial))
            try:
                thickness = float(row.thickness)
            except Exception:
                thickness = 0.0
            axial += thickness if np.isfinite(thickness) else 0.0
        return offsets

    def _path_stock_lens_context(
        self,
        *,
        splitter_index: int = -1,
        arm_role: str = "",
        branch_path: str = "",
    ) -> dict[str, object]:
        path = str(branch_path or "").strip()
        if path:
            frame = self._branch_path_frame(path)
            selector = self._branch_path_leaf_selector(path)
            role = {
                "transmit": "Transmit",
                "reflect": "Reflect",
                "return": "Return",
            }.get(selector, ELEMENT_ARM_ROLE_DEFAULT)
            return {
                **frame,
                "arm_role": role,
                "metadata_role": role,
                "branch_selector": selector,
                "branch_path": path,
                "parent_splitter": self._branch_path_detail(path),
                "path_frame_source": "traced_branch_path",
                "path_frame_surface": int(frame.get("origin_surface", -1)),
                "path_frame_samples": int(frame.get("sample_count", 0)),
                "insert_index": self._default_insert_index_for_arm_key(self._arm_key_from_branch_path(path)),
                "placement_label": f"traced path {self._branch_path_compact_detail(path)}",
            }
        role = str(arm_role or "").strip()
        if role not in {"Transmit", "Reflect"}:
            raise RuntimeError("Stock-lens path placement supports Transmit, Reflect, or a traced Path view.")
        frame = self._arm_frame_for_splitter(int(splitter_index), role)
        splitter_row = self.rows[int(splitter_index)]
        splitter_metadata = self._element_metadata(splitter_row)
        parent = (
            str(splitter_metadata.get("element_id", "") or "").strip()
            or self._element_key(splitter_row)
            or str(splitter_row.name or f"S{int(splitter_index)}").strip()
        )
        return {
            **frame,
            "arm_role": role,
            "metadata_role": role,
            "branch_selector": self._branch_selector_for_arm_role(role),
            "branch_path": "",
            "parent_splitter": parent,
            "path_frame_source": "splitter_row",
            "path_frame_surface": int(splitter_index),
            "path_frame_samples": 0,
            "insert_index": max(1, len(self.rows) - 1),
            "placement_label": f"{role.lower()} path",
        }

    def _stock_lens_rows_for_path_context(
        self,
        rows: list[SurfaceRow],
        *,
        part_number: str,
        context: dict[str, object],
        distance_mm: float,
        local_decenter_x: float = 0.0,
        local_decenter_y: float = 0.0,
        local_tilt_x: float = 0.0,
        local_tilt_y: float = 0.0,
        local_tilt_z: float = 0.0,
    ) -> list[SurfaceRow]:
        if not rows:
            raise RuntimeError("Stock lens has no rows to place.")
        distance = float(distance_mm)
        if not np.isfinite(distance) or distance <= 0.0:
            raise RuntimeError("Path distance must be positive.")
        insert_index = max(1, min(int(context.get("insert_index", len(self.rows) - 1)), len(self.rows) - 1))
        origin = np.asarray(context["origin"], dtype=float)
        direction = self._normalized_vector(context["direction"])
        local_offset, tilts = self._path_local_pose(
            context,
            local_decenter_x=local_decenter_x,
            local_decenter_y=local_decenter_y,
            local_tilt_x=local_tilt_x,
            local_tilt_y=local_tilt_y,
            local_tilt_z=local_tilt_z,
        )
        tilt_x, tilt_y, tilt_z = tilts
        role = str(context.get("arm_role", ELEMENT_ARM_ROLE_DEFAULT) or ELEMENT_ARM_ROLE_DEFAULT)
        selector = str(context.get("branch_selector", "") or "").strip()
        branch_path = str(context.get("branch_path", "") or "").strip()
        parent = str(context.get("parent_splitter", "") or "").strip()
        path_source = str(context.get("path_frame_source", "") or "").strip()
        base_label = f"{role} {part_number}".strip() if role else str(part_number).strip()
        if branch_path:
            selectors = "".join(self._branch_path_selector_sequence(branch_path)) or "Path"
            base_label = f"Path {selectors} {part_number}".strip()
        used = {self._element_key(row) for row in self.rows if self._element_key(row)}
        element_label = self._unique_element_label(base_label or "Path stock lens", used)
        offsets = self._block_axial_offsets(rows)
        additions = [SurfaceRow(**asdict(row)) for row in rows]
        row_count = len(additions)
        for offset, row in zip(offsets, additions):
            row.element = element_label
            row.tilt_x = float(tilt_x)
            row.tilt_y = float(tilt_y)
            row.tilt_z = float(tilt_z)
            row.desp_x = float(getattr(row, "desp_x", 0.0) or 0.0)
            row.desp_y = float(getattr(row, "desp_y", 0.0) or 0.0)
            row.desp_z = float(getattr(row, "desp_z", 0.0) or 0.0)
            metadata = {
                "element_id": self._element_id_from_label(element_label),
                "element_name": element_label,
                "arm_role": role,
                "parent_splitter": parent,
                "branch_selector": selector,
                "branch_path": branch_path,
                "arm_distance": distance,
                "local_decenter_x": float(local_decenter_x),
                "local_decenter_y": float(local_decenter_y),
                "local_tilt_x": float(local_tilt_x),
                "local_tilt_y": float(local_tilt_y),
                "local_tilt_z": float(local_tilt_z),
                "path_component_type": PATH_COMPONENT_STOCK_LENS,
                "path_component_part": str(part_number).strip(),
                "path_component_row_count": row_count,
                "path_component_axial_offset": float(offset),
                "path_frame_source": path_source,
                "path_frame_surface": int(context.get("path_frame_surface", -1)),
                "path_frame_samples": int(context.get("path_frame_samples", 0)),
            }
            row.advanced = dict(row.advanced or {})
            row.advanced[ELEMENT_ADVANCED_ATTR] = metadata

        temp_rows = [SurfaceRow(**asdict(row)) for row in self.rows]
        for offset, row in enumerate(additions):
            temp_rows.insert(insert_index + offset, SurfaceRow(**asdict(row)))
        for offset, row in enumerate(additions):
            row_index = insert_index + offset
            baseline = self._surface_transform_for_rows(temp_rows, row_index)[:3, 3]
            target = origin + direction * (distance + offsets[offset]) + local_offset
            decenter = np.asarray(target, dtype=float) - np.asarray(baseline, dtype=float)
            row.desp_x = float(row.desp_x) + float(decenter[0])
            row.desp_y = float(row.desp_y) + float(decenter[1])
            row.desp_z = float(row.desp_z) + float(decenter[2])
            temp_rows[row_index] = SurfaceRow(**asdict(row))
        return additions

    @staticmethod
    def _normalized_metadata_key(value: object) -> str:
        return re.sub(r"[^a-z0-9]", "", str(value or "").strip().lower())

    def _splitter_index_for_path_parent(self, parent: object) -> int | None:
        parent_key = self._normalized_metadata_key(parent)
        candidates: list[tuple[int, set[str]]] = []
        for index, row in enumerate(self.rows):
            if row.surface != BEAM_SPLITTER_SURFACE:
                continue
            metadata = self._element_metadata(row)
            labels = {
                f"S{index}",
                str(row.name or ""),
                self._element_key(row),
                str(metadata.get("element_id", "") or ""),
                str(metadata.get("element_name", "") or ""),
            }
            candidates.append((index, {self._normalized_metadata_key(label) for label in labels if str(label or "").strip()}))
        if parent_key:
            for index, keys in candidates:
                if parent_key in keys:
                    return index
        if not parent_key and len(candidates) == 1:
            return candidates[0][0]
        return None

    def _path_frame_for_element_metadata(self, metadata: dict[str, object]) -> dict[str, object]:
        data = _normalize_element_metadata(metadata)
        branch_path = str(data.get("branch_path", "") or "").strip()
        if branch_path:
            return dict(self._branch_path_frame(branch_path))
        selector = str(data.get("branch_selector", "") or "").strip().lower()
        if not selector:
            selector = self._branch_selector_for_arm_role(str(data.get("arm_role", "") or ""))
        role = {"transmit": "Transmit", "reflect": "Reflect"}.get(selector)
        if role is None:
            raise RuntimeError("This element is not tied to a transmitted/reflected path frame.")
        splitter_index = self._splitter_index_for_path_parent(data.get("parent_splitter", ""))
        if splitter_index is None:
            raise RuntimeError("Could not find the parent Beam Splitter row for this path element.")
        return dict(self._arm_frame_for_splitter(splitter_index, role))

    def _metadata_has_path_pose(self, metadata: dict[str, object]) -> bool:
        data = _normalize_element_metadata(metadata)
        component_type = str(data.get("path_component_type", "") or "").strip()
        frame_source = str(data.get("path_frame_source", "") or "").strip()
        return bool(component_type or frame_source)

    def _apply_path_local_pose_to_indices(
        self,
        indices: list[int],
        metadata: dict[str, object],
    ) -> list[int]:
        selected = sorted(int(index) for index in indices if 0 < int(index) < len(self.rows) - 1)
        if not selected:
            raise RuntimeError("Select one placed path element first.")
        data = _normalize_element_metadata(metadata)
        if not self._metadata_has_path_pose(data):
            raise RuntimeError("Selected element does not contain path-placement metadata.")
        distance = float(data.get("arm_distance", 0.0))
        if not np.isfinite(distance):
            raise RuntimeError("Path distance must be finite.")
        frame = self._path_frame_for_element_metadata(data)
        origin = np.asarray(frame["origin"], dtype=float)
        direction = self._normalized_vector(frame["direction"])
        local_dx = float(data.get("local_decenter_x", 0.0))
        local_dy = float(data.get("local_decenter_y", 0.0))
        local_tx = float(data.get("local_tilt_x", 0.0))
        local_ty = float(data.get("local_tilt_y", 0.0))
        local_tz = float(data.get("local_tilt_z", 0.0))
        local_offset, tilts = self._path_local_pose(
            frame,
            local_decenter_x=local_dx,
            local_decenter_y=local_dy,
            local_tilt_x=local_tx,
            local_tilt_y=local_ty,
            local_tilt_z=local_tz,
        )
        tilt_x, tilt_y, tilt_z = tilts
        fallback_offsets = dict(zip(selected, self._block_axial_offsets([self.rows[index] for index in selected])))
        temp_rows = [SurfaceRow(**asdict(row)) for row in self.rows]
        for index in selected:
            temp_rows[index].tilt_x = float(tilt_x)
            temp_rows[index].tilt_y = float(tilt_y)
            temp_rows[index].tilt_z = float(tilt_z)
            temp_rows[index].desp_x = 0.0
            temp_rows[index].desp_y = 0.0
            temp_rows[index].desp_z = 0.0

        label = str(data.get("element_name", "") or self._element_key(self.rows[selected[0]])).strip()
        for index in selected:
            row = self.rows[index]
            row_metadata = self._element_metadata(row)
            row_data = dict(row_metadata)
            row_data.update(data)
            for key in (
                "path_component_axial_offset",
                "path_component_row_count",
                "path_component_part",
                "path_frame_source",
                "path_frame_surface",
                "path_frame_samples",
            ):
                if key in row_metadata:
                    row_data[key] = row_metadata[key]
            axial_offset = float(row_data.get("path_component_axial_offset", fallback_offsets.get(index, 0.0)) or 0.0)
            row.tilt_x = float(tilt_x)
            row.tilt_y = float(tilt_y)
            row.tilt_z = float(tilt_z)
            baseline = self._surface_transform_for_rows(temp_rows, index)[:3, 3]
            target = origin + direction * (distance + axial_offset) + local_offset
            decenter = np.asarray(target, dtype=float) - np.asarray(baseline, dtype=float)
            row.desp_x = float(decenter[0])
            row.desp_y = float(decenter[1])
            row.desp_z = float(decenter[2])
            if label:
                row.element = label
                row_data["element_name"] = label
                row_data["element_id"] = str(row_data.get("element_id", "") or self._element_id_from_label(label))
            row_data["local_decenter_x"] = local_dx
            row_data["local_decenter_y"] = local_dy
            row_data["local_tilt_x"] = local_tx
            row_data["local_tilt_y"] = local_ty
            row_data["local_tilt_z"] = local_tz
            self._set_element_metadata(row, row_data)
            temp_rows[index] = SurfaceRow(**asdict(row))
        return selected

    def _detector_row_for_arm(
        self,
        splitter_index: int,
        arm_role: str,
        distance_mm: float,
        diameter_mm: float,
        *,
        insert_at: int | None = None,
    ) -> SurfaceRow:
        return self._path_component_row_for_arm(
            splitter_index,
            arm_role,
            PATH_COMPONENT_DETECTOR,
            distance_mm,
            diameter_mm,
            insert_at=insert_at,
        )

    def open_arm_detector_placement(self, splitter_index: int, arm_role: str) -> None:
        self.open_arm_path_component_placement(splitter_index, arm_role, default_component=PATH_COMPONENT_DETECTOR)

    def _main_path_component_placement_dialog(self) -> MainPathComponentPlacementDialog:
        dialog = self.__dict__.get("_main_path_component_placement_dialog_instance")
        if dialog is None:
            dialog = MainPathComponentPlacementDialog(self, short_error_message=_short_error_message)
            self._main_path_component_placement_dialog_instance = dialog
        return dialog

    def open_arm_path_component_placement(
        self,
        splitter_index: int,
        arm_role: str,
        *,
        default_component: object = PATH_COMPONENT_DETECTOR,
        branch_path: str = "",
    ) -> None:
        self._main_path_component_placement_dialog().open_arm_path_component_placement(
            splitter_index,
            arm_role,
            default_component=default_component,
            branch_path=branch_path,
        )

    def open_current_path_component_placement(self) -> None:
        self._main_path_component_placement_dialog().open_current_path_component_placement()

    def open_arm_stock_lens_placement(self, splitter_index: int, arm_role: str) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Path Stock Lens", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        if not (0 <= int(splitter_index) < len(self.rows)) or self.rows[int(splitter_index)].surface != BEAM_SPLITTER_SURFACE:
            messagebox.showinfo("Path Stock Lens", "Right-click a Beam Splitter row first.", parent=self)
            return
        role = str(arm_role or "").strip()
        if role not in {"Transmit", "Reflect"}:
            messagebox.showerror("Path Stock Lens", f"Unsupported path: {arm_role}", parent=self)
            return
        self.open_stock_lens_importer(path_placement={"splitter_index": int(splitter_index), "arm_role": role})

    def open_current_path_stock_lens_placement(self) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Path Stock Lens", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        self._refresh_arm_view_choices()
        label = str(self.arm_view_var.get() or ARM_VIEW_DEFAULT).strip()
        arm_key = self._arm_key_for_view_label(label)
        branch_path = self._branch_path_for_arm_key(arm_key)
        if not branch_path:
            messagebox.showinfo(
                "Path Stock Lens",
                "Choose a traced Path view first, then run Insert/Actions -> Stock Lens to Current Path View.",
                parent=self,
            )
            return
        self.open_stock_lens_importer(path_placement={"branch_path": branch_path})

    def assign_selected_elements_to_arm(self, role: str) -> None:
        role = _normalize_element_metadata({"arm_role": role})["arm_role"]
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Assign Path", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        blocks = self._selected_element_blocks()
        if not blocks:
            messagebox.showinfo("Assign Path", "Select one or more non-Object/non-Image rows or element groups first.", parent=self)
            return

        self._begin_history_capture()
        selected_indices: list[int] = []
        for indices in blocks:
            if role == ELEMENT_ARM_ROLE_DEFAULT:
                for index in indices:
                    self._set_element_metadata(self.rows[index], {})
                selected_indices.extend(indices)
                continue
            label = self._ensure_element_for_block(indices)
            metadata = self._element_metadata(self.rows[indices[0]])
            metadata["element_name"] = label
            if not str(metadata.get("element_id", "") or "").strip():
                metadata["element_id"] = self._element_id_from_label(label)
            previous_role = str(metadata.get("arm_role", ELEMENT_ARM_ROLE_DEFAULT))
            previous_selector = str(metadata.get("branch_selector", "") or "").strip()
            metadata["arm_role"] = role
            if previous_selector in {"", self._branch_selector_for_arm_role(previous_role)}:
                metadata["branch_selector"] = self._branch_selector_for_arm_role(role)
            metadata["leg_id"] = ""
            for index in indices:
                self._set_element_metadata(self.rows[index], metadata)
            selected_indices.extend(indices)
        self._normalize_special_rows()
        self._sync_table()
        if selected_indices:
            self._select_table_indices(selected_indices, focus_index=selected_indices[0])
        self._commit_history_capture()
        self._mark_plot_update_pending()
        role_text = role if role != ELEMENT_ARM_ROLE_DEFAULT else "Unassigned"
        self.status_var.set(f"Assigned {len(blocks)} element(s) to {role_text} path metadata.")
        self._cleanup_current_popup_menu()

    def _element_metadata_for_arm_key(self, arm_key: str, label: str) -> dict[str, object] | None:
        parts = str(arm_key or "").split("|")
        leg_id = self._leg_id_from_arm_key(arm_key)
        selector = self._branch_selector_for_arm_key(arm_key)
        branch_path = self._branch_path_for_arm_key(arm_key)
        if branch_path:
            role = {
                "transmit": "Transmit",
                "reflect": "Reflect",
                "return": "Return",
            }.get(selector, ELEMENT_ARM_ROLE_DEFAULT)
            parent = self._branch_path_detail(branch_path)
        elif leg_id:
            workflow = self._physical_leg_workflow()
            if workflow == "mach_zehnder":
                bs1_parent = self._splitter_id_by_ordinal(0)
                bs2_parent = self._splitter_id_by_ordinal(1)
                role, selector, parent = {
                    "input": ("Common", "primary", bs1_parent),
                    "transmit": ("Return", "transmit", bs1_parent),
                    "reflect": ("Return", "reflect", bs1_parent),
                    "cross": ("Detector", "transmit", bs2_parent),
                    "return": ("Detector", "reflect", bs2_parent),
                }.get(leg_id, (ELEMENT_ARM_ROLE_DEFAULT, "", ""))
            else:
                parent_default = self._default_parent_splitter_id()
                role, selector, parent = {
                    "input": ("Common", "primary", parent_default),
                    "reflect": ("Return", "reflect", parent_default),
                    "transmit": ("Return", "transmit", parent_default),
                    "detector": ("Detector", "reflect", parent_default),
                }.get(leg_id, (ELEMENT_ARM_ROLE_DEFAULT, "", ""))
        else:
            if not selector:
                return None
            role = {
                "transmit": "Transmit",
                "reflect": "Reflect",
                "return": "Return",
            }.get(selector, ELEMENT_ARM_ROLE_DEFAULT)
            parent = parts[1].strip() if len(parts) >= 3 and parts[0] == "branch" else ""
        return _normalize_element_metadata(
            {
                "element_id": self._element_id_from_label(label),
                "element_name": label,
                "leg_id": leg_id,
                "arm_role": role,
                "parent_splitter": parent,
                "branch_selector": selector,
                "branch_path": branch_path,
                "arm_distance": 0.0,
                "local_decenter_x": 0.0,
                "local_decenter_y": 0.0,
                "local_tilt_x": 0.0,
                "local_tilt_y": 0.0,
                "local_tilt_z": 0.0,
            }
        )

    def assign_selected_elements_to_arm_key(self, arm_key: str) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Assign Path", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        blocks = self._selected_element_blocks()
        if not blocks:
            messagebox.showinfo("Assign Path", "Select one or more non-Object/non-Image rows or element groups first.", parent=self)
            return

        self._begin_history_capture()
        selected_indices: list[int] = []
        detail = self._arm_key_detail(arm_key)
        for indices in blocks:
            label = self._ensure_element_for_block(indices)
            metadata = self._element_metadata_for_arm_key(arm_key, label)
            if metadata is None:
                continue
            for index in indices:
                self.rows[index].element = label
                self._set_element_metadata(self.rows[index], metadata)
            selected_indices.extend(indices)
        if not selected_indices:
            self._history_pending_state = None
            messagebox.showinfo("Assign Path", "The selected path is not assignable for these rows.", parent=self)
            return
        self._normalize_special_rows()
        leg_id = self._leg_id_from_arm_key(arm_key)
        moved_indices = self._move_blocks_to_physical_leg_position(blocks, leg_id) if leg_id else []
        if moved_indices:
            selected_indices = moved_indices
        self._sync_table()
        self._select_table_indices(selected_indices, focus_index=selected_indices[0])
        self._commit_history_capture()
        self._mark_plot_update_pending()
        move_note = " and moved into path order" if moved_indices else ""
        self.status_var.set(f"Assigned {len(blocks)} element(s) to {detail} path metadata{move_note}.")
        self._cleanup_current_popup_menu()

    def _main_scene_element_dialogs(self) -> MainSceneElementDialogs:
        dialogs = self.__dict__.get("_main_scene_element_dialogs_instance")
        if dialogs is None:
            dialogs = MainSceneElementDialogs(
                self,
                normalize_detector_settings=_normalize_detector_settings,
                scene_target_editor_kind_labels=SCENE_TARGET_EDITOR_KIND_LABELS,
                scene_target_editor_kind_choices=SCENE_TARGET_EDITOR_KIND_CHOICES,
                normalize_scene_target_editor_kind=_normalize_scene_target_editor_kind,
                element_metadata_numeric_fields=ELEMENT_METADATA_NUMERIC_FIELDS,
                normalize_element_metadata=_normalize_element_metadata,
                element_metadata_summary=_element_metadata_summary,
                short_error_message=_short_error_message,
                element_arm_role_default=ELEMENT_ARM_ROLE_DEFAULT,
                element_arm_role_values=ELEMENT_ARM_ROLE_VALUES,
                element_branch_selector_values=ELEMENT_BRANCH_SELECTOR_VALUES,
            )
            self._main_scene_element_dialogs_instance = dialogs
        return dialogs

    def open_detector_settings(self, row_index: int) -> None:
        self._main_scene_element_dialogs().open_detector_settings(row_index)


    def _scene_target_editor_kind_for_row(self, row_index: int) -> str:
        if not (0 <= int(row_index) < len(self.rows)):
            return "auto"
        row = self.rows[int(row_index)]
        surface = str(getattr(row, "surface", "") or "")
        if surface == OBJECT_TARGET_SURFACE:
            return "object_target"
        if surface == DIFFUSE_OBJECT_SURFACE:
            return "diffuse_object"
        if surface == "Aperture":
            return "aperture"
        role = str(self._scene_target_settings(row).get("role", "") or "")
        if role == "object_target":
            return "object_target"
        if role in {"analysis_target", "aperture", "detector"}:
            return role
        if surface != "Object" and (surface == "Image" or self._row_has_detector_output_metadata(row)):
            return "detector"
        return "auto"

    def _default_detector_settings_for_target_row(self, row_index: int) -> dict[str, object]:
        row = self.rows[int(row_index)]
        settings = self._detector_settings(row)
        diameter = self._safe_positive_float(getattr(row, "diameter", 0.0), 0.0)
        active_width = float(settings.get("active_width_mm", 0.0) or 0.0) or diameter or 1.0
        active_height = float(settings.get("active_height_mm", 0.0) or 0.0) or diameter or 1.0
        return _normalize_detector_settings(
            {
                "active_width_mm": active_width,
                "active_height_mm": active_height,
                "bins": settings.get("bins", ""),
                "pixel_pitch_um": settings.get("pixel_pitch_um", 0.0),
            }
        )

    def _set_nonseq_target_surface_index(self, row_index: int | None) -> None:
        self._refresh_analysis_surface_choices()
        var = self.__dict__.get("nonseq_target_surface_var")
        if var is None:
            return
        if row_index is None:
            var.set("Auto")
            return
        index = int(row_index)
        if 0 <= index < len(self.rows):
            var.set(f"{index}: {self.rows[index].name}")

    def _apply_scene_target_editor_update(
        self,
        row_index: int,
        *,
        target_kind: object,
        detector_settings: dict[str, object] | None = None,
        active_target: bool | None = None,
        row_name: str | None = None,
        clear_detector: bool = False,
    ) -> dict[str, object]:
        if not (0 <= int(row_index) < len(self.rows)):
            raise ValueError(f"Invalid target row index: {row_index}")
        index = int(row_index)
        row = self.rows[index]
        kind = _normalize_scene_target_editor_kind(target_kind)
        role = _scene_target_role_for_editor_kind(kind)
        if row_name is not None:
            name = str(row_name or "").strip()
            if name:
                row.name = name

        if kind == "detector":
            if row.surface == "Object":
                raise ValueError("Object rows cannot be detector planes.")
            data = _normalize_detector_settings(detector_settings or self._default_detector_settings_for_target_row(index))
            if _detector_settings_is_default(data):
                data = self._default_detector_settings_for_target_row(index)
            self._set_detector_settings(row, data)
        elif kind == "object_target":
            row.surface = OBJECT_TARGET_SURFACE
            self._apply_surface_type_defaults(index, row, OBJECT_TARGET_SURFACE)
            self._set_detector_settings(row, {})
        elif kind == "diffuse_object":
            row.surface = DIFFUSE_OBJECT_SURFACE
            self._apply_surface_type_defaults(index, row, DIFFUSE_OBJECT_SURFACE)
            self._set_detector_settings(row, {})
        elif kind == "aperture":
            row.surface = "Aperture"
            self._apply_surface_type_defaults(index, row, "Aperture")
            self._set_detector_settings(row, {})
        elif kind == "analysis_target":
            self._set_detector_settings(row, {})
        elif clear_detector:
            self._set_detector_settings(row, {})

        self._set_scene_target_settings(row, {"role": role})
        if active_target is not None:
            if bool(active_target):
                self._set_nonseq_target_surface_index(index)
                trace_mode_var = self.__dict__.get("trace_mode_var")
                if trace_mode_var is not None:
                    trace_mode_var.set("Non-Sequential Preview")
            elif self._current_nonseq_target_surface_index() == index:
                self._set_nonseq_target_surface_index(None)
        self._normalize_special_rows()
        return {
            "row_index": index,
            "target_kind": kind,
            "target_role": role,
            "surface": row.surface,
            "detector_settings": self._detector_settings(row),
            "scene_target_settings": self._scene_target_settings(row),
            "active_target": self._current_nonseq_target_surface_index() == index,
        }

    def _clear_scene_target_editor_metadata(self, row_index: int) -> dict[str, object]:
        if not (0 <= int(row_index) < len(self.rows)):
            raise ValueError(f"Invalid target row index: {row_index}")
        index = int(row_index)
        row = self.rows[index]
        self._set_scene_target_settings(row, {})
        self._set_detector_settings(row, {})
        if self._current_nonseq_target_surface_index() == index:
            self._set_nonseq_target_surface_index(None)
        self._normalize_special_rows()
        return {
            "row_index": index,
            "surface": row.surface,
            "detector_settings": self._detector_settings(row),
            "scene_target_settings": self._scene_target_settings(row),
            "active_target": self._current_nonseq_target_surface_index() == index,
        }

    def open_scene_target_editor(self, row_index: int | None = None) -> None:
        self._main_scene_element_dialogs().open_scene_target_editor(row_index)


    def open_selected_path_local_pose_editor(self) -> None:
        self._main_scene_element_dialogs().open_selected_path_local_pose_editor()


    def open_element_settings(self) -> None:
        self._main_scene_element_dialogs().open_element_settings()


    def flip_selected(self) -> None:
        selected = self.table.selection()
        if not selected:
            return
        self._begin_history_capture()
        indices = self._selected_table_indices()
        if len(indices) < 2:
            self._history_pending_state = None
            return
        selected_rows = [SurfaceRow(**asdict(self.rows[index])) for index in indices]
        selected_thicknesses = [row.thickness for row in selected_rows]
        selected_glasses = [row.glass for row in selected_rows]
        flipped_rows = list(reversed(selected_rows))

        for row in flipped_rows:
            if row.surface == "Standard" and row.rc != 0.0:
                row.rc = -row.rc
            row.name = self._flipped_name(row.name)

        if len(flipped_rows) >= 2:
            remapped_thicknesses = list(reversed(selected_thicknesses[:-1])) + [selected_thicknesses[-1]]
            remapped_glasses = list(reversed(selected_glasses[:-1])) + [selected_glasses[-1]]
        else:
            remapped_thicknesses = selected_thicknesses
            remapped_glasses = selected_glasses

        for row, thickness, glass in zip(flipped_rows, remapped_thicknesses, remapped_glasses):
            row.thickness = thickness
            row.glass = glass

        for index, row in zip(indices, flipped_rows):
            self.rows[index] = row
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices(indices, focus_index=indices[0])
        self._commit_history_capture()
        self.refresh_plot()

    def move_up(self) -> None:
        selected = self.table.selection()
        if not selected:
            return
        self._begin_history_capture()
        selected_indices = self._selected_table_indices()
        if not selected_indices:
            self._history_pending_state = None
            return
        index = min(selected_indices)
        new_rows, new_start, new_end, moved = self._swap_element_block(self.rows, index, "up", same_arm_only=True)
        if not moved:
            if self._element_arm_role_for_index(self.rows, index) != ELEMENT_ARM_ROLE_DEFAULT:
                self.status_var.set("No previous element in the same path to move above.")
            self._history_pending_state = None
            return
        self.rows = new_rows
        self._sync_table()
        self._select_table_indices(list(range(new_start, new_end + 1)), focus_index=new_start)
        self._commit_history_capture()
        self.refresh_plot()

    def move_down(self) -> None:
        selected = self.table.selection()
        if not selected:
            return
        self._begin_history_capture()
        selected_indices = self._selected_table_indices()
        if not selected_indices:
            self._history_pending_state = None
            return
        index = max(selected_indices)
        new_rows, new_start, new_end, moved = self._swap_element_block(self.rows, index, "down", same_arm_only=True)
        if not moved:
            if self._element_arm_role_for_index(self.rows, index) != ELEMENT_ARM_ROLE_DEFAULT:
                self.status_var.set("No next element in the same path to move below.")
            self._history_pending_state = None
            return
        self.rows = new_rows
        self._sync_table()
        self._select_table_indices(list(range(new_start, new_end + 1)), focus_index=new_start)
        self._commit_history_capture()
        self.refresh_plot()

    def begin_edit(self, event: tk.Event) -> None:
        row_id = self.table.identify_row(event.y)
        column_id = self.table.identify_column(event.x)
        if not row_id or not column_id:
            return
        column_index = int(column_id.replace("#", "")) - 1
        field = FIELDS[column_index]
        if field == "label":
            return
        row_index = self._table_item_row_index(row_id)
        if row_index is None:
            source_record = self._table_item_scene_record(row_id)
            if source_record is not None and getattr(source_record, "kind", "") == SCENE_ROW_SOURCE:
                self.open_scene_source_manager(selected_source_id=str(getattr(source_record, "source_id", "") or ""))
            return
        if not self._table_cell_enabled(row_index, field):
            self.status_var.set(self._surface_type_disabled_message(row_index, field))
            self._schedule_active_cell_border_update()
            return
        bbox = self.table.bbox(row_id, column_id)
        if not bbox or len(bbox) != 4:
            return
        x, y, width, height = bbox
        current_value = self.table.set(row_id, field)
        if field in {"rc", "thickness"}:
            current_value = current_value.replace("*", "").strip()

        if self.editor is not None:
            self.editor.destroy()
            self.editor = None
            self._editor_row_id = None
            self._editor_field = None

        if field == "surface":
            self._show_choice_menu(row_id, field, SURFACE_TYPES, event.x_root, event.y_root)
            return
        elif field == "glass":
            self._show_choice_menu(
                row_id,
                field,
                ("AIR", "BK7", "F2", "MIRROR"),
                event.x_root,
                event.y_root,
            )
            return
        else:
            editor = ttk.Entry(self.table)
            editor.insert(0, current_value)
            editor.bind("<FocusOut>", lambda e: self._finish_edit(row_id, field), add="+")
            editor.bind("<Return>", lambda e: self._finish_edit(row_id, field), add="+")
            editor.bind("<KP_Enter>", lambda e: self._finish_edit(row_id, field), add="+")

        editor.place(x=x, y=y, width=width, height=height)
        editor.focus_set()
        editor.bind("<Escape>", lambda e: self._cancel_edit(), add="+")
        self.editor = editor
        self._editor_row_id = row_id
        self._editor_field = field

    def _selected_surface_row_index(self) -> int | None:
        selected = self.table.selection()
        if selected:
            return self._table_item_row_index(selected[0])
        focused = self.table.focus()
        if focused:
            return self._table_item_row_index(focused)
        return None

    def convert_surface_type(self, row_index: int, surface_type: str) -> None:
        if not (0 <= row_index < len(self.rows)) or surface_type not in SURFACE_TYPES:
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Convert Surface Type", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        self._begin_history_capture()
        row = self.rows[row_index]
        row.surface = surface_type
        self._apply_surface_type_defaults(row_index, row, surface_type)
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_row(row_index)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"Converted S{row_index} to {surface_type}. Click Update to trace.")

    def _context_insert_after_index(self, row_index: int) -> int | None:
        if not (0 <= row_index < len(self.rows)):
            return self._selected_insert_index()
        block = self._element_indices_for_index(self.rows, row_index)
        return max(block) if block else row_index

    def _insert_quick_component_rows(
        self,
        rows: list[SurfaceRow],
        *,
        insert_after: int | None,
        element_name: str,
        status_label: str,
    ) -> None:
        if not rows:
            return
        for row in rows:
            row.element = element_name
        self._remap_inserted_element_labels(rows)
        self._begin_history_capture()
        insert_at = self._insert_surface_rows(rows, insert_after=insert_after)
        self._commit_history_capture()
        self.current_layout_file = None
        self.refresh_plot(suppress_analysis=True)
        self.status_var.set(f"Inserted {status_label} at S{insert_at}. Click Update to trace.")

    def insert_surface_context_component(self, row_index: int, kind: str) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Insert Component", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        insert_after = self._context_insert_after_index(row_index)
        common_layouts = {
            "singlet": "Single Lens",
            "doublet": "Doublet Lens",
            "flat_mirror": "Flat Mirror 45 Deg",
        }
        if kind in common_layouts:
            if insert_after is not None:
                self._select_table_indices([insert_after], focus_index=insert_after)
            self.insert_layout_component_by_name(common_layouts[kind])
            return

        diameter = 25.0
        if 0 <= row_index < len(self.rows):
            diameter = max(float(self.rows[row_index].diameter), 1.0)

        if kind == "object_target":
            rows = [
                SurfaceRow(
                    surface=OBJECT_TARGET_SURFACE,
                    name="Object target",
                    glass="MIRROR",
                    thickness=50.0,
                    diameter=max(diameter, 25.0),
                    axis_move=2.0,
                    advanced={
                        "Display2D": {"label": "Object target"},
                        "Note": (
                            "Specular proxy object: current tracing reflects rays from this target. "
                            "Replace with a Diffuse Object row when rough/diffuse scattering is required."
                        ),
                    },
                ),
            ]
            self._insert_quick_component_rows(
                rows,
                insert_after=insert_after,
                element_name="Object target",
                status_label="object target proxy",
            )
            return

        if kind == "diffuse_object":
            settings = _normalize_diffuse_scatter_settings(DIFFUSE_SCATTER_DEFAULT_SETTINGS)
            rows = [
                SurfaceRow(
                    surface=DIFFUSE_OBJECT_SURFACE,
                    name="Diffuse object",
                    glass="MIRROR",
                    thickness=50.0,
                    diameter=max(diameter, 25.0),
                    axis_move=2.0,
                    advanced={
                        DIFFUSE_SCATTER_ADVANCED_ATTR: settings,
                        "Display2D": {"label": "Diffuse object"},
                        "Note": (
                            "Built-in diffuse scatter target. Use Diffuse / BRDF Settings to choose Lambertian, "
                            "Oren-Nayar, Cosine Lobe, or pySCATMECH BRDF behavior and adjust reflectance, samples, "
                            "cone, backend model, and target guidance."
                        ),
                    },
                ),
            ]
            self._insert_quick_component_rows(
                rows,
                insert_after=insert_after,
                element_name="Diffuse object",
                status_label="diffuse object",
            )
            return

        if kind == "plate":
            rows = [
                SurfaceRow(surface="Standard", name="Window front", glass="BK7", thickness=10.0, diameter=diameter),
                SurfaceRow(surface="Standard", name="Window rear", glass="AIR", thickness=25.0, diameter=diameter),
            ]
            self._insert_quick_component_rows(
                rows,
                insert_after=insert_after,
                element_name="Plate / Window",
                status_label="plate/window",
            )
            return

        if kind == "wedge_prism":
            rows = [
                SurfaceRow(surface="Standard", name="Wedge entrance", glass="BK7", thickness=20.0, diameter=diameter, tilt_x=20.0),
                SurfaceRow(surface="Standard", name="Wedge exit", glass="AIR", thickness=30.0, diameter=diameter, tilt_x=-20.0),
            ]
            self._insert_quick_component_rows(
                rows,
                insert_after=insert_after,
                element_name="Wedge Prism",
                status_label="wedge prism",
            )
            return

        if kind == "right_angle_prism":
            rows = [
                SurfaceRow(surface="Standard", name="Right-angle entrance", glass="BK7", thickness=20.0, diameter=diameter),
                SurfaceRow(surface="Mirror", name="Hypotenuse fold mirror", glass="MIRROR", thickness=20.0, diameter=diameter, tilt_x=45.0, axis_move=2.0),
                SurfaceRow(surface="Standard", name="Right-angle exit", glass="AIR", thickness=30.0, diameter=diameter, tilt_x=90.0),
            ]
            rows[1].advanced = {
                "Note": (
                    "Right-angle prism table primitive: hypotenuse is modeled as a fold mirror. "
                    "Use Optical CAD/STL Solid for arbitrary prism boundary tracing."
                )
            }
            self._insert_quick_component_rows(
                rows,
                insert_after=insert_after,
                element_name="Right-Angle Prism",
                status_label="right-angle prism primitive",
            )
            return

        if kind == "cube_beam_splitter":
            settings = _normalize_beam_splitter_settings(
                {
                    "split_mode": "Deterministic Fresnel P/S",
                    "reflectance": 0.5,
                    "absorption": 0.0,
                    "polarization_p_fraction": 0.5,
                    "max_branch_depth": 4,
                }
            )
            splitter_advanced = {
                BEAM_SPLITTER_ADVANCED_ATTR: settings,
                "Coating": _beam_splitter_coating_for_settings(settings, None),
                "Note": (
                    "Cube beam splitter primitive: entrance face, internal 45 degree splitter, and transmit exit face. "
                    "Reflected-path exit geometry is handled by non-sequential branch tracing/path components; "
                    "use an optical STL solid for a closed cube with all side faces."
                ),
            }
            rows = [
                SurfaceRow(surface="Standard", name="Cube BS entrance", glass="BK7", thickness=10.0, diameter=diameter),
                SurfaceRow(
                    surface=BEAM_SPLITTER_SURFACE,
                    name="Cube BS coated diagonal",
                    glass="BK7",
                    thickness=10.0,
                    diameter=diameter,
                    tilt_x=45.0,
                    advanced=splitter_advanced,
                ),
                SurfaceRow(surface="Standard", name="Cube BS transmit exit", glass="AIR", thickness=30.0, diameter=diameter),
            ]
            self._insert_quick_component_rows(
                rows,
                insert_after=insert_after,
                element_name="Cube Beam Splitter",
                status_label="cube beam splitter primitive",
            )
            return

    @staticmethod
    def _rectangle_uda(width: float, height: float) -> list[list[float]]:
        half_w = max(float(width) * 0.5, 1e-6)
        half_h = max(float(height) * 0.5, 1e-6)
        return [[-half_w, half_w, half_w, -half_w, -half_w], [-half_h, -half_h, half_h, half_h, -half_h]]

    def apply_shape_aperture_preset(self, row_index: int, preset: str) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        if self.rows[row_index].surface in {"Object", "Image"}:
            messagebox.showinfo("Shape / Aperture", "Shape presets apply to physical surfaces, not Object/Image rows.", parent=self)
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Shape / Aperture", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        self._begin_history_capture()
        row = self.rows[row_index]
        advanced = dict(row.advanced or {})
        diameter = max(float(row.diameter), 1.0)
        if preset != "spider":
            advanced.pop("Mask_Shape", None)
            advanced.pop("Mask_Type", None)
        if preset == "circular":
            row.uda = "None"
            row.in_diameter = 0.0
            status = "Set circular clear aperture."
        elif preset == "rectangular":
            row.uda = self._rectangle_uda(diameter, diameter * 0.7)
            row.in_diameter = 0.0
            status = "Set rectangular UDA aperture."
        elif preset == "annulus":
            if row.surface == "Standard":
                row.surface = "Aperture"
                self._apply_surface_type_defaults(row_index, row, "Aperture")
            row.in_diameter = max(diameter * 0.45, 0.1)
            row.uda = "None"
            status = "Set annular aperture using InDia."
        elif preset == "spider":
            advanced["Mask_Shape"] = {
                "kind": "mask_shape",
                "preset": "spider",
                "arms": 4,
                "arm_width": max(diameter / 30.0, 0.2),
                "hub_radius": max(diameter / 20.0, 0.3),
                "extent": diameter * 1.1,
            }
            advanced["Mask_Type"] = 2
            status = "Set spider mask preset."
        elif preset == "rectangular_clear":
            if row.surface == "Standard":
                row.surface = "Aperture"
                self._apply_surface_type_defaults(row_index, row, "Aperture")
            row.uda = self._rectangle_uda(diameter, diameter * 0.7)
            status = "Set rectangular clear-aperture UDA."
        else:
            self._history_pending_state = None
            return
        row.advanced = advanced
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_row(row_index)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"{status} Click Update to trace.")

    def apply_material_to_selected(self, glass: str, *, mirror_surface: bool = False) -> None:
        indices = [index for index in self._selected_table_indices() if 0 < index < len(self.rows) - 1]
        if not indices:
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Material", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        self._begin_history_capture()
        for index in indices:
            row = self.rows[index]
            row.glass = glass
            if mirror_surface:
                row.surface = "Mirror"
                self._apply_surface_type_defaults(index, row, "Mirror")
            elif row.surface in REFLECTIVE_PROXY_SURFACES and glass.upper() != "MIRROR":
                row.surface = "Standard"
                self._apply_surface_type_defaults(index, row, "Standard")
                row.glass = glass
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices(indices, focus_index=indices[0])
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"Applied material {glass} to {len(indices)} selected row(s). Click Update.")

    def apply_coating_preset_to_selected(self, preset_name: str) -> None:
        indices = [index for index in self._selected_table_indices() if 0 < index < len(self.rows) - 1]
        if not indices:
            return
        if preset_name not in COATING_PRESETS:
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Coating / Polarization", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        self._begin_history_capture()
        preset = COATING_PRESETS[preset_name]
        for index in indices:
            row = self.rows[index]
            advanced = dict(row.advanced or {})
            if preset == [[], [], [], []]:
                advanced.pop("Coating", None)
                advanced.pop("CoatingMet", None)
            else:
                advanced["Coating"] = preset
            if preset_name == "Protected mirror 94%":
                row.surface = "Mirror"
                row.glass = "MIRROR"
            row.advanced = advanced
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices(indices, focus_index=indices[0])
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"Applied coating preset {preset_name} to {len(indices)} row(s). Click Update.")

    def apply_metal_fresnel_mode_to_selected(self) -> None:
        indices = [index for index in self._selected_table_indices() if 0 < index < len(self.rows) - 1]
        if not indices:
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Coating / Polarization", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        self._begin_history_capture()
        for index in indices:
            row = self.rows[index]
            advanced = dict(row.advanced or {})
            try:
                coating_met = int(float(advanced.get("CoatingMet", 0) or 0))
            except Exception:
                coating_met = 0
            advanced.pop("Coating", None)
            advanced["CoatingMet"] = max(coating_met, 0)
            row.advanced = advanced
            row.surface = "Mirror"
            row.glass = "MIRROR"
            self._apply_surface_type_defaults(index, row, "Mirror")
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices(indices, focus_index=indices[0])
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"Enabled metal Fresnel mirror mode on {len(indices)} selected row(s). Click Update.")

    def apply_beam_splitter_fresnel_ps(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        self.convert_surface_type(row_index, BEAM_SPLITTER_SURFACE)
        self._begin_history_capture()
        row = self.rows[row_index]
        advanced = dict(row.advanced or {})
        settings = _normalize_beam_splitter_settings(advanced.get(BEAM_SPLITTER_ADVANCED_ATTR))
        settings["split_mode"] = "Deterministic Fresnel P/S"
        advanced[BEAM_SPLITTER_ADVANCED_ATTR] = settings
        advanced["Coating"] = _beam_splitter_coating_for_settings(settings, advanced.get("Coating"))
        row.advanced = advanced
        self._sync_table()
        self._select_table_row(row_index)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"Enabled Fresnel P/S deterministic splitting on S{row_index}. Click Update.")

    def align_surface_normal_to_previous(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        previous = next(
            (
                self.rows[index]
                for index in range(row_index - 1, 0, -1)
                if self.rows[index].surface not in {"Object", "Image"}
            ),
            None,
        )
        self._begin_history_capture()
        row = self.rows[row_index]
        if previous is None:
            row.tilt_x = row.tilt_y = row.tilt_z = 0.0
        else:
            row.tilt_x = float(previous.tilt_x)
            row.tilt_y = float(previous.tilt_y)
            row.tilt_z = float(previous.tilt_z)
        self._sync_table()
        self._select_table_row(row_index)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"Aligned S{row_index} to the previous local table orientation. Click Update.")

    def set_surface_incidence_angle(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        value = simpledialog.askfloat(
            "Set Incidence Angle",
            "Set TiltX/display incidence angle [deg]:",
            initialvalue=float(self.rows[row_index].tilt_x),
            parent=self,
        )
        if value is None:
            return
        self._begin_history_capture()
        self.rows[row_index].tilt_x = float(value)
        self._sync_table()
        self._select_table_row(row_index)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"Set S{row_index} TiltX to {float(value):.6g} deg. Click Update.")

    def assign_selected_to_current_path_view(self) -> None:
        arm_key = self._current_arm_view_key()
        if not arm_key:
            self.status_var.set("Choose a Path view before assigning selected rows to the current path.")
            return
        self.assign_selected_elements_to_arm_key(arm_key)

    def reverse_element_for_row(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        indices = self._element_indices_for_index(self.rows, row_index)
        if len(indices) < 2:
            indices = self._selected_table_indices()
        if len(indices) < 2:
            self.status_var.set("Select at least two rows, or a grouped element, before reversing.")
            return
        self._select_table_indices(indices, focus_index=indices[0])
        self.flip_selected()

    def set_analysis_surface_to_row(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        self._refresh_analysis_surface_choices()
        self.analysis_surface_var.set(f"{row_index}: {self.rows[row_index].name}")
        self._mark_plot_update_pending()
        self.status_var.set(f"Analysis surface set to S{row_index}: {self.rows[row_index].name}. Click Update.")

    def set_nonseq_target_to_row(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)) or not hasattr(self, "nonseq_target_surface_var"):
            return
        self._refresh_analysis_surface_choices()
        self.nonseq_target_surface_var.set(f"{row_index}: {self.rows[row_index].name}")
        if hasattr(self, "trace_mode_var"):
            self.trace_mode_var.set("Non-Sequential Preview")
            self.trace_mode = "Non-Sequential Preview"
        self._mark_plot_update_pending()
        self.status_var.set(f"Non-sequential target set to S{row_index}: {self.rows[row_index].name}. Click Update.")

    def validate_surface_row_physics(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        row = self.rows[row_index]
        errors: list[str] = []
        warnings_out: list[str] = []
        if row.surface not in SURFACE_TYPES:
            errors.append(f"Unsupported surface type: {row.surface}")
        for attr in ("rc", "k", "thickness", "diameter", "in_diameter", "tilt_x", "tilt_y", "tilt_z", "desp_x", "desp_y", "desp_z"):
            try:
                value = float(getattr(row, attr))
            except Exception:
                errors.append(f"{attr} is not numeric")
                continue
            if not np.isfinite(value):
                errors.append(f"{attr} is not finite")
        if float(row.diameter) <= 0.0:
            errors.append("Diameter must be positive.")
        if row.surface in REFLECTIVE_PROXY_SURFACES and str(row.glass).upper() != "MIRROR":
            warnings_out.append(f"{row.surface} rows normally use Material=MIRROR internally.")
        if row.surface == BEAM_SPLITTER_SURFACE and not isinstance((row.advanced or {}).get(BEAM_SPLITTER_ADVANCED_ATTR), dict):
            warnings_out.append("Beam Splitter row has no explicit BeamSplitter settings; defaults will be used.")
        if row.surface == DIFFUSE_OBJECT_SURFACE and not isinstance((row.advanced or {}).get(DIFFUSE_SCATTER_ADVANCED_ATTR), dict):
            warnings_out.append("Diffuse Object row has no explicit DiffuseScatter settings; defaults will be used.")
        advanced = row.advanced or {}
        if isinstance(advanced, dict) and row.surface != BEAM_SPLITTER_SURFACE:
            solid_source_text = " ".join(
                str(value or "")
                for value in (
                    row.name,
                    advanced.get("Solid_3d_stl"),
                    advanced.get("OpticalSolidSourcePath"),
                    advanced.get("OpticalSolidSourceFormat"),
                )
            ).lower()
            if self._scene_graph_value_present(advanced.get("Solid_3d_stl")) and any(
                token in solid_source_text for token in ("beam splitter", "beamsplitter", "cube bs", " 68551", "/68551", "step_68551")
            ):
                metadata = normalize_optical_solid_face_metadata(advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))
                if not optical_solid_has_virtual_splitter_plane(metadata):
                    warnings_out.append(
                        "This looks like passive beam-splitter CAD. A CAD/STEP solid does not encode the internal coated diagonal; "
                        "use a Beam Splitter row or the validated cube beam-splitter primitive for branch physics."
                    )
        advanced_errors, advanced_warnings = _validate_advanced_surface_inputs(dict(row.advanced or {}), row.extra_data, row.uda)
        errors.extend(advanced_errors)
        warnings_out.extend(advanced_warnings)
        detail = [f"S{row_index}: {row.surface} / {row.name}"]
        detail.extend(f"ERROR: {item}" for item in errors)
        detail.extend(f"Warning: {item}" for item in warnings_out)
        if not errors and not warnings_out:
            detail.append("Validation passed.")
        message = "\n".join(detail)
        if errors:
            messagebox.showerror("Validate Surface Row", message, parent=self)
        elif warnings_out:
            messagebox.showwarning("Validate Surface Row", message, parent=self)
        else:
            messagebox.showinfo("Validate Surface Row", message, parent=self)

    @staticmethod
    def _advanced_surface_default_text(attr: str) -> str:
        try:
            default = getattr(Kos.surf(), attr)
        except Exception:
            return ""
        literal = _layout_literal_value(default)
        if literal is _UNSERIALIZABLE_LAYOUT_VALUE:
            return "<native object>"
        text = " ".join(repr(literal).split())
        return text if len(text) <= 72 else text[:69] + "..."

    @staticmethod
    def _is_default_extra_data(value) -> bool:
        try:
            return bool(np.all(np.asarray(value, dtype=object) == 0))
        except Exception:
            return value in (0, 0.0, "None", None)

    @staticmethod
    def _is_default_uda(value) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value == "None"
        return False

    @staticmethod
    def _short_numeric_list(value, limit: int = 12) -> str:
        try:
            arr = np.asarray(value, dtype=float).ravel()
        except Exception:
            return ""
        if arr.size == 0:
            return ""
        significant = arr[:limit]
        while significant.size and abs(float(significant[-1])) <= 1e-15:
            significant = significant[:-1]
        return pformat(significant.tolist(), width=100) if significant.size else ""

    @staticmethod
    def _decoded_uda_polygon(value) -> tuple[np.ndarray, np.ndarray] | None:
        try:
            decoded = decode_custom_surface_value(value)
        except Exception:
            decoded = value
        if decoded is None or (isinstance(decoded, str) and decoded == "None"):
            return None
        if not isinstance(decoded, (list, tuple)) or len(decoded) != 2:
            return None
        try:
            px = np.asarray(decoded[0], dtype=float).ravel()
            py = np.asarray(decoded[1], dtype=float).ravel()
        except Exception:
            return None
        if px.size != py.size or px.size < 3:
            return None
        return px, py

    @staticmethod
    def _mask_preset_summary(value) -> str:
        if not isinstance(value, dict):
            return ""
        if str(value.get("kind", "")).strip().lower() not in {"mask_shape", "mask", "mask_preset"}:
            return ""
        preset = str(value.get("preset", "")).strip().lower()
        if preset == "ronchi":
            return "Ronchi mask"
        if preset == "spider":
            return "Spider mask"
        return str(value.get("preset", "Mask preset"))

    def _surface_preview_grid(
        self,
        row: SurfaceRow,
        advanced: dict[str, object],
        extra_data,
        *,
        samples: int = 121,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        radius = max(float(row.diameter) * 0.5, 1.0)
        axis = np.linspace(-radius, radius, int(samples))
        x_grid, y_grid = np.meshgrid(axis, axis)
        r_grid = np.hypot(x_grid, y_grid)
        inside = r_grid <= radius
        sag = np.full_like(x_grid, np.nan, dtype=float)
        c = 1.0 / float(row.rc) if abs(float(row.rc)) > 1e-12 else 0.0
        if abs(c) > 0.0:
            k = float(getattr(row, "k", 0.0))
            root = 1.0 - (1.0 + k) * c * c * r_grid * r_grid
            safe_root = np.maximum(root, 0.0)
            denom = 1.0 + np.sqrt(safe_root)
            base = np.divide(c * r_grid * r_grid, denom, out=np.zeros_like(r_grid), where=np.abs(denom) > 1e-15)
        else:
            base = np.zeros_like(r_grid)
        sag[inside] = base[inside]
        aspher = np.asarray(advanced.get("AspherData", []), dtype=float).ravel() if "AspherData" in advanced else np.empty(0)
        for index, coeff in enumerate(aspher[:12], start=1):
            if abs(float(coeff)) <= 0.0:
                continue
            sag[inside] += float(coeff) * np.power(r_grid[inside], 2 * index)
        znk = np.asarray(advanced.get("ZNK", []), dtype=float).ravel() if "ZNK" in advanced else np.empty(0)
        if znk.size:
            rho = np.divide(r_grid, radius, out=np.zeros_like(r_grid), where=radius > 0.0)
            theta = np.arctan2(y_grid, x_grid)
            z_terms = [
                np.ones_like(rho),
                rho * np.cos(theta),
                rho * np.sin(theta),
                2.0 * rho * rho - 1.0,
                rho * rho * np.cos(2.0 * theta),
                rho * rho * np.sin(2.0 * theta),
                (3.0 * rho**3 - 2.0 * rho) * np.cos(theta),
                (3.0 * rho**3 - 2.0 * rho) * np.sin(theta),
                6.0 * rho**4 - 6.0 * rho * rho + 1.0,
            ]
            for coeff, basis in zip(znk[: len(z_terms)], z_terms):
                if abs(float(coeff)) > 0.0:
                    sag[inside] += float(coeff) * basis[inside]
        try:
            decoded_extra = decode_custom_surface_value(extra_data)
            if isinstance(decoded_extra, (list, tuple)) and len(decoded_extra) == 2 and callable(decoded_extra[0]):
                extra = np.asarray(decoded_extra[0](x_grid, y_grid, decoded_extra[1]), dtype=float)
                if extra.shape == sag.shape:
                    sag[inside] += extra[inside]
        except Exception:
            pass
        return x_grid, y_grid, sag, inside

    def _main_surface_shape_builder_dialog(self) -> MainSurfaceShapeBuilderDialog:
        dialog = self.__dict__.get("_main_surface_shape_builder_dialog_instance")
        if dialog is None:
            dialog = MainSurfaceShapeBuilderDialog(
                self,
                attachment_dir=ATTACHMENT_DIR,
                project_root=PROJECT_ROOT,
                optical_solid_filetypes=OPTICAL_SOLID_FILETYPES,
                encode_custom_surface_value=encode_custom_surface_value,
                parse_literal_editor_text=_parse_literal_editor_text,
                validate_advanced_surface_inputs=_validate_advanced_surface_inputs,
                optical_solid_mesh_path_from_source=_optical_solid_mesh_path_from_source,
                short_error_message=_short_error_message,
            )
            self._main_surface_shape_builder_dialog_instance = dialog
        return dialog

    def open_surface_shape_builder(self, row_index: int | None = None) -> None:
        self._main_surface_shape_builder_dialog().open(row_index)

    @staticmethod
    def _coating_preset_for_value(value) -> str:
        literal = _layout_literal_value(value)
        if literal is _UNSERIALIZABLE_LAYOUT_VALUE:
            return "Custom"
        for name, preset in COATING_PRESETS.items():
            if literal == _layout_literal_value(preset):
                return name
        return "Custom"

    def _main_coating_material_dialog(self) -> MainCoatingMaterialDialog:
        dialog = self.__dict__.get("_main_coating_material_dialog_instance")
        if dialog is None:
            dialog = MainCoatingMaterialDialog(
                self,
                coating_presets=COATING_PRESETS,
                coating_preset_names=COATING_PRESET_NAMES,
                metal_catalog_dir=METAL_CATALOG_DIR,
                literal_editor_text=_literal_editor_text,
                parse_literal_editor_text=_parse_literal_editor_text,
                normalize_metal_catalog_specs=_normalize_metal_catalog_specs,
                metal_catalog_entries=_metal_catalog_entries,
                metal_catalog_type_for_path=_metal_catalog_type_for_path,
                validate_advanced_surface_inputs=_validate_advanced_surface_inputs,
            )
            self._main_coating_material_dialog_instance = dialog
        return dialog

    def open_coating_material_editor(self, row_index: int | None = None) -> None:
        self._main_coating_material_dialog().open(row_index)

    def _main_diffuse_scatter_dialog(self) -> MainDiffuseScatterDialog:
        dialog = self.__dict__.get("_main_diffuse_scatter_dialog_instance")
        if dialog is None:
            dialog = MainDiffuseScatterDialog(
                self,
                diffuse_object_surface=DIFFUSE_OBJECT_SURFACE,
                diffuse_scatter_advanced_attr=DIFFUSE_SCATTER_ADVANCED_ATTR,
                diffuse_scatter_default_settings=DIFFUSE_SCATTER_DEFAULT_SETTINGS,
                normalize_diffuse_scatter_settings=_normalize_diffuse_scatter_settings,
                validate_diffuse_scatter_settings=_validate_diffuse_scatter_settings,
                pyscatmech_status=pyscatmech_status,
                format_pyscatmech_parameters=format_pyscatmech_parameters,
            )
            self._main_diffuse_scatter_dialog_instance = dialog
        return dialog

    def open_diffuse_scatter_settings(self, row_index: int | None = None) -> None:
        self._main_diffuse_scatter_dialog().open(row_index)

    def _main_beam_splitter_dialog(self) -> MainBeamSplitterDialog:
        dialog = self.__dict__.get("_main_beam_splitter_dialog_instance")
        if dialog is None:
            dialog = MainBeamSplitterDialog(
                self,
                beam_splitter_surface=BEAM_SPLITTER_SURFACE,
                beam_splitter_advanced_attr=BEAM_SPLITTER_ADVANCED_ATTR,
                beam_splitter_split_modes=BEAM_SPLITTER_SPLIT_MODES,
                normalize_beam_splitter_settings=_normalize_beam_splitter_settings,
                validate_beam_splitter_settings=_validate_beam_splitter_settings,
                beam_splitter_coating_for_settings=_beam_splitter_coating_for_settings,
                beam_splitter_summary=_beam_splitter_summary,
                short_error_message=_short_error_message,
            )
            self._main_beam_splitter_dialog_instance = dialog
        return dialog

    def open_beam_splitter_settings(self, row_index: int | None = None) -> None:
        self._main_beam_splitter_dialog().open(row_index)

    def _main_error_map_dialog(self) -> MainErrorMapDialog:
        dialog = self.__dict__.get("_main_error_map_dialog_instance")
        if dialog is None:
            dialog = MainErrorMapDialog(
                self,
                attachment_dir=ATTACHMENT_DIR,
                project_root=PROJECT_ROOT,
                error_map_literal=_error_map_literal,
                error_map_summary=_error_map_summary,
                load_error_map_file=_load_error_map_file,
                validate_error_map=_validate_error_map,
            )
            self._main_error_map_dialog_instance = dialog
        return dialog

    def open_error_map_editor(self, row_index: int | None = None) -> None:
        self._main_error_map_dialog().open(row_index)

    def _main_advanced_surface_dialog(self) -> MainAdvancedSurfaceDialog:
        dialog = self.__dict__.get("_main_advanced_surface_dialog_instance")
        if dialog is None:
            dialog = MainAdvancedSurfaceDialog(
                self,
                advanced_row_shape_fields=ADVANCED_ROW_SHAPE_FIELDS,
                advanced_surface_field_groups=ADVANCED_SURFACE_FIELD_GROUPS,
                advanced_surface_attr_names=ADVANCED_SURFACE_ATTR_NAMES,
                variable_registry=VARIABLE_REGISTRY,
                column_labels=COLUMN_LABELS,
                literal_editor_text=_literal_editor_text,
                parse_literal_editor_text=_parse_literal_editor_text,
                format_float_sequence=_format_float_sequence,
                parse_float_sequence_text=_parse_float_sequence_text,
                validate_advanced_surface_inputs=_validate_advanced_surface_inputs,
            )
            self._main_advanced_surface_dialog_instance = dialog
        return dialog

    def open_advanced_surface_editor(self, row_index: int | None = None) -> None:
        self._main_advanced_surface_dialog().open(row_index)

    def _main_surface_settings_dialogs(self) -> MainSurfaceSettingsDialogs:
        dialogs = self.__dict__.get("_main_surface_settings_dialogs_instance")
        if dialogs is None:
            dialogs = MainSurfaceSettingsDialogs(
                self,
                galvo_scan_overlay_key=GALVO_SCAN_OVERLAY_KEY,
                format_float_sequence=_format_float_sequence,
                parse_float_sequence_text=_parse_float_sequence_text,
                short_error_message=_short_error_message,
            )
            self._main_surface_settings_dialogs_instance = dialogs
        return dialogs

    def open_galvo_scan_overlay_settings(self, index: int | None = None) -> None:
        self._main_surface_settings_dialogs().open_galvo_scan_overlay_settings(index)

    def open_surface_additional_settings(self, index: int | None = None) -> None:
        self._main_surface_settings_dialogs().open_surface_additional_settings(index)

    def _open_grating_settings_editor(self, row_index: int) -> None:
        self._main_surface_settings_dialogs().open_grating_settings_editor(row_index)

    def _main_context_menu(self) -> MainContextMenu:
        builder = self.__dict__.get("_main_context_menu_instance")
        if builder is None:
            builder = MainContextMenu(
                self,
                fields=FIELDS,
                scene_row_source=SCENE_ROW_SOURCE,
                object_target_surface=OBJECT_TARGET_SURFACE,
                diffuse_object_surface=DIFFUSE_OBJECT_SURFACE,
                beam_splitter_surface=BEAM_SPLITTER_SURFACE,
                coating_preset_names=COATING_PRESET_NAMES,
                element_arm_role_default=ELEMENT_ARM_ROLE_DEFAULT,
                element_arm_role_values=ELEMENT_ARM_ROLE_VALUES,
            )
            self._main_context_menu_instance = builder
        return builder

    def show_context_menu(self, event: tk.Event) -> None:
        self._main_context_menu().show_context_menu(event)


    def _finish_edit(self, row_id: str, field: str, quiet: bool = False) -> None:
        if self.editor is None:
            return
        value = self.editor.get().strip()
        self.editor.destroy()
        self.editor = None
        self._editor_row_id = None
        self._editor_field = None
        if not value:
            return
        row_index = self._table_item_row_index(row_id)
        if row_index is None:
            return
        if field in NUMERIC_FIELDS:
            accepts_pose_sequence = False
            path_local_pose_cell = self._path_local_pose_cell_enabled(row_index, field)
            if field in POSE_TOLERANCE_FIELDS and 0 <= row_index < len(self.rows) and not path_local_pose_cell:
                try:
                    pose_values = _parse_float_sequence_text(value.replace("*", "").strip())
                    if len(pose_values) > POSE_TOLERANCE_MAX_VARIANTS:
                        raise ValueError(f"Use {POSE_TOLERANCE_MAX_VARIANTS} or fewer overlay values.")
                    accepts_pose_sequence = bool(pose_values)
                except Exception:
                    accepts_pose_sequence = False
            if not accepts_pose_sequence:
                try:
                    float(value)
                except ValueError:
                    if not quiet:
                        messagebox.showerror(
                            "Invalid value",
                            f"{COLUMN_LABELS[field]} expects a number"
                            + (" or comma/range tolerance values." if field in POSE_TOLERANCE_FIELDS and not path_local_pose_cell else "."),
                        )
                    return
        if not self._table_cell_enabled(row_index, field):
            if not quiet:
                self.status_var.set(self._surface_type_disabled_message(row_index, field))
            return
        self._begin_history_capture()
        if field == "diameter" and row_index == len(self.rows) - 1:
            self._set_image_diameter_mode("Manual")
        self.table.set(row_id, field, value)
        self._read_rows_from_table()
        self._normalize_special_rows()
        self._couple_object_image_diameter_after_edit(row_index, field)
        self._sync_table()
        self._commit_history_capture()
        self._mark_plot_update_pending()

    def _couple_object_image_diameter_after_edit(self, row_index: int, field: str) -> None:
        if field != "diameter" or len(self.rows) < 2:
            return
        if row_index not in {0, len(self.rows) - 1}:
            return
        if self._current_object_mode() != "Finite":
            return
        magnification = self._current_finite_paraxial_magnification()
        if magnification is None or not np.isfinite(magnification) or abs(float(magnification)) <= 1e-12:
            return
        mag = abs(float(magnification))
        self._set_image_diameter_mode("Manual")
        if row_index == 0 and self.rows[0].surface == "Object":
            object_diameter = max(float(self.rows[0].diameter), 0.0)
            self.rows[-1].diameter = max(object_diameter * mag, 1e-6)
            source = "Object"
        elif row_index == len(self.rows) - 1 and self.rows[-1].surface == "Image":
            image_diameter = max(float(self.rows[-1].diameter), 0.0)
            self.rows[0].diameter = max(image_diameter / mag, 1e-6)
            source = "Image"
        else:
            return
        self._sync_field_value_from_diameter_pair()
        status_var = self.__dict__.get("status_var")
        if status_var is not None:
            status_var.set(
                f"{source} diameter applied; paired diameter updated with |m|={mag:.6g}. Click Update to redraw."
            )

    def _sync_object_diameter_from_manual_image(self) -> bool:
        if len(self.rows) < 2 or self.rows[0].surface != "Object" or self.rows[-1].surface != "Image":
            return False
        if self._current_object_mode() != "Finite" or self._current_image_diameter_mode() != "Manual":
            return False
        magnification = self._current_finite_paraxial_magnification()
        if magnification is None or not np.isfinite(magnification) or abs(float(magnification)) <= 1e-12:
            return False
        image_diameter = max(float(self.rows[-1].diameter), 0.0)
        self.rows[0].diameter = max(image_diameter / abs(float(magnification)), 1e-6)
        self._sync_field_value_from_diameter_pair()
        return True

    def _sync_field_value_from_diameter_pair(self) -> None:
        if self.__dict__.get("field_value_var") is None or self.__dict__.get("field_type_var") is None or not self.rows:
            return
        field_type = self._current_field_type()
        object_half = max(float(self.rows[0].diameter) * 0.5, 0.0)
        image_half = max(float(self.rows[-1].diameter) * 0.5, 0.0)
        if field_type == "Object Height":
            value = object_half
        elif field_type in {"Paraxial Image Height", "Real Image Height"}:
            value = image_half
        elif field_type == "Angle":
            value = float(np.rad2deg(np.arctan2(object_half, max(self._current_object_distance(), 1e-9))))
        else:
            return
        self.field_value_var.set(self._format_table_float(value))

    def _set_image_diameter_mode(self, mode: str) -> None:
        image_diameter_mode_var = self.__dict__.get("image_diameter_mode_var")
        if image_diameter_mode_var is not None and mode in {"Auto", "Manual"}:
            image_diameter_mode_var.set(mode)

    def _cancel_edit(self) -> None:
        if self.editor is None:
            return
        self.editor.destroy()
        self.editor = None
        self._editor_row_id = None
        self._editor_field = None

    def _commit_pending_table_edit(self) -> None:
        if self.editor is None or self._editor_row_id is None or self._editor_field is None:
            return
        self._finish_edit(self._editor_row_id, self._editor_field, quiet=True)

    def _show_choice_menu(
        self,
        row_id: str,
        field: str,
        values: tuple[str, ...],
        x_root: int,
        y_root: int,
    ) -> None:
        self._cleanup_current_popup_menu()
        menu = tk.Menu(self, tearoff=0)
        for value in values:
            menu.add_command(
                label=value,
                command=lambda selected=value: self._apply_choice(row_id, field, selected),
            )
        self._post_popup_menu(menu, x_root, y_root)

    def _post_popup_menu(self, menu: tk.Menu, x_root: int, y_root: int) -> None:
        self.popup_menu = menu
        try:
            menu.tk_popup(x_root, y_root)
        finally:
            try:
                menu.grab_release()
            except tk.TclError:
                pass

    def _apply_choice(self, row_id: str, field: str, value: str) -> None:
        self._begin_history_capture()
        self.table.set(row_id, field, value)
        self._read_rows_from_table()
        if field == "surface":
            index = self._table_item_row_index(row_id)
            if index is None:
                return
            row = self.rows[index]
            self._apply_surface_type_defaults(index, row, value)
        self._normalize_special_rows()
        self._sync_table()
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self._cleanup_current_popup_menu()

    def _apply_surface_type_defaults(self, index: int, row: SurfaceRow, surface_type: str) -> None:
        prev_row = self.rows[index - 1] if index > 0 else None
        next_row = self.rows[index + 1] if index + 1 < len(self.rows) else None
        neighbor_diameters = [
            float(candidate.diameter)
            for candidate in (prev_row, next_row)
            if candidate is not None and candidate.surface not in {"Object", "Image"}
        ]
        fallback_diameter = min(neighbor_diameters) if neighbor_diameters else max(float(row.diameter), 10.0)

        if surface_type in REFLECTIVE_PROXY_SURFACES:
            default_name = (
                "Object target"
                if surface_type == OBJECT_TARGET_SURFACE
                else "Diffuse object"
                if surface_type == DIFFUSE_OBJECT_SURFACE
                else "Mirror"
            )
            row.name = default_name if row.name in {"", "Surface", "Standard", "Aperture", "Mirror", "Object target", "Diffuse object"} else row.name
            row.glass = "MIRROR"
            row.rc = 0.0
            if surface_type == "Mirror" and abs(row.tilt_x) < 1e-9 and abs(row.tilt_y) < 1e-9 and abs(row.tilt_z) < 1e-9:
                row.tilt_x = 45.0
            if abs(row.axis_move) < 1e-9:
                row.axis_move = 2.0
            advanced = dict(row.advanced or {})
            if surface_type == OBJECT_TARGET_SURFACE:
                display = dict(advanced.get("Display2D", {}) or {})
                display.setdefault("label", "Object target")
                advanced["Display2D"] = display
                note = (
                    "Object Target currently traces as a specular reflective proxy so source/object split "
                    "fixtures can return rays. Use a Diffuse Object row when rough/diffuse BRDF scattering is needed."
                )
                existing_note = str(advanced.get("Note", "") or "").strip()
                if note not in existing_note:
                    advanced["Note"] = f"{note} {existing_note}".strip()
                row.element = row.element or "Object target"
            elif surface_type == DIFFUSE_OBJECT_SURFACE:
                display = dict(advanced.get("Display2D", {}) or {})
                display.setdefault("label", "Diffuse object")
                advanced["Display2D"] = display
                advanced[DIFFUSE_SCATTER_ADVANCED_ATTR] = _normalize_diffuse_scatter_settings(
                    advanced.get(DIFFUSE_SCATTER_ADVANCED_ATTR, DIFFUSE_SCATTER_DEFAULT_SETTINGS)
                )
                note = (
                    "Diffuse Object spawns deterministic built-in scatter branches in Non-Sequential Preview. "
                    "Use Diffuse/BRDF settings to control model, reflectance, samples, scatter cone, and target guidance."
                )
                existing_note = str(advanced.get("Note", "") or "").strip()
                if note not in existing_note:
                    advanced["Note"] = f"{note} {existing_note}".strip()
                row.element = row.element or "Diffuse object"
            else:
                display = dict(advanced.get("Display2D", {}) or {})
                if display.get("label") in {"Object target", "Diffuse object"}:
                    display.pop("label", None)
                if display:
                    advanced["Display2D"] = display
                else:
                    advanced.pop("Display2D", None)
                advanced.pop(DIFFUSE_SCATTER_ADVANCED_ATTR, None)
            row.advanced = advanced
            self._clear_disabled_surface_type_fields(row)
            return

        if surface_type == BEAM_SPLITTER_SURFACE:
            row.name = "50/50 Beam Splitter" if row.name in {"", "Surface", "Standard", "Aperture", "Mirror", "Object target"} else row.name
            if row.glass == "MIRROR":
                row.glass = "AIR"
            row.rc = 0.0
            if abs(row.tilt_x) < 1e-9 and abs(row.tilt_y) < 1e-9 and abs(row.tilt_z) < 1e-9:
                row.tilt_x = 45.0
            advanced = dict(row.advanced or {})
            splitter_settings = _normalize_beam_splitter_settings(advanced.get(BEAM_SPLITTER_ADVANCED_ATTR))
            advanced[BEAM_SPLITTER_ADVANCED_ATTR] = splitter_settings
            advanced["Coating"] = _beam_splitter_coating_for_settings(splitter_settings, advanced.get("Coating"))
            note = (
                "Beam Splitter rows spawn deterministic reflected/transmitted paths in Non-Sequential Preview. "
                "Use Glass + Thickness plus a following rear AIR surface for finite plate deviation; "
                "use the same rear TiltX for a parallel plate."
            )
            existing_note = str(advanced.get("Note", "") or "").strip()
            if note not in existing_note:
                advanced["Note"] = f"{note} {existing_note}".strip()
            row.advanced = advanced
            self._clear_disabled_surface_type_fields(row)
            return

        if surface_type == "Aperture":
            row.name = "Aperture"
            row.glass = "AIR"
            row.rc = 0.0
            row.diameter = max(0.1, min(float(self._current_aperture_value()), fallback_diameter))
            self._clear_disabled_surface_type_fields(row)
            return

        if surface_type == "Thin Lens":
            row.name = "Thin Lens" if row.name in {"", "Surface", "Standard"} else row.name
            if row.glass == "MIRROR":
                row.glass = "AIR"
            if abs(row.rc) < 1e-9:
                row.rc = 100.0
            self._clear_disabled_surface_type_fields(row)
            return

        if surface_type == "Grating":
            row.name = "Grating" if row.name in {"", "Surface", "Standard"} else row.name
            row.rc = 0.0
            if abs(row.diff_ord) < 1e-9:
                row.diff_ord = 1.0
            if abs(row.grating_d) < 1e-9:
                row.grating_d = 1.0
            self._clear_disabled_surface_type_fields(row)
            return

        if surface_type == "Standard":
            row.name = "Surface" if row.name in {"", "Mirror", "Object target", "Diffuse object", "Aperture", "Thin Lens", "Grating", "50/50 Beam Splitter"} else row.name
            if row.glass == "MIRROR":
                row.glass = "AIR"
            row.advanced = dict(row.advanced or {})
            row.advanced.pop(BEAM_SPLITTER_ADVANCED_ATTR, None)
            row.advanced.pop(DIFFUSE_SCATTER_ADVANCED_ATTR, None)
        self._clear_disabled_surface_type_fields(row)

    def _clear_disabled_surface_type_fields(self, row: SurfaceRow) -> None:
        disabled = (set(FIELDS) | set(GRATING_SETTING_FIELDS)) - self._surface_type_enabled_fields(row.surface)
        if "glass" in disabled:
            row.glass = "MIRROR" if row.surface in REFLECTIVE_PROXY_SURFACES else "AIR"
        numeric_attrs = {
            "rc": "rc",
            "k": "k",
            "axicon": "axicon",
            "diff_ord": "diff_ord",
            "grating_d": "grating_d",
            "grating_angle": "grating_angle",
            "thickness": "thickness",
            "in_diameter": "in_diameter",
            "tilt_x": "tilt_x",
            "tilt_y": "tilt_y",
            "tilt_z": "tilt_z",
            "desp_x": "desp_x",
            "desp_y": "desp_y",
            "desp_z": "desp_z",
            "axis_move": "axis_move",
        }
        for field, attr in numeric_attrs.items():
            if field in disabled:
                setattr(row, attr, 0.0)

    @staticmethod
    def _row_has_optimization(row: SurfaceRow) -> bool:
        return row.optimize_rc or row.optimize_thickness or bool(_row_native_variable_names(row))

    @staticmethod
    def _row_native_variable_enabled(row: SurfaceRow, parameter: str) -> bool:
        return any(
            _native_variable_matches(candidate, parameter)
            for candidate in _row_native_variable_names(row)
        )

    @classmethod
    def _variable_enabled_for_row(cls, row: SurfaceRow, spec) -> bool:
        return bool(spec.is_enabled(row) or cls._row_native_variable_enabled(row, spec.parameter))

    @classmethod
    def _optimization_marker_fields_for_row(cls, row: SurfaceRow) -> tuple[str, ...]:
        marker_fields: list[str] = []
        for field in FIELDS:
            spec = VARIABLE_REGISTRY.get(field)
            if spec is None or not spec.is_supported(row):
                continue
            if cls._variable_enabled_for_row(row, spec):
                marker_fields.append(field)
        return tuple(marker_fields)

    @staticmethod
    def _remove_native_variable_from_row(row: SurfaceRow, parameter: str) -> None:
        names = [
            candidate
            for candidate in _row_native_variable_names(row)
            if not _native_variable_matches(candidate, parameter)
        ]
        row.advanced = dict(row.advanced or {})
        if names:
            row.advanced["Var"] = names
        else:
            row.advanced.pop("Var", None)
        bounds = row.advanced.get("VarBounds")
        if isinstance(bounds, dict):
            for key in list(bounds):
                if _native_variable_matches(key, parameter):
                    bounds.pop(key, None)
            if bounds:
                row.advanced["VarBounds"] = bounds
            else:
                row.advanced.pop("VarBounds", None)

    def toggle_current_optimization_cell(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        index = self._table_item_row_index(self.current_menu_row_id)
        if index is None:
            return
        row = self.rows[index]
        spec = self._variable_spec_for_field(self.current_menu_field)
        if spec is None:
            return
        self._begin_history_capture()
        enabled = self._variable_enabled_for_row(row, spec)
        spec.set_enabled(row, not enabled)
        if enabled:
            self._remove_native_variable_from_row(row, spec.parameter)
        self._sync_table()
        self._commit_history_capture()
        self.refresh_plot()
        self._cleanup_current_popup_menu()

    def toggle_current_tolerance_compensator(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        index = self._table_item_row_index(self.current_menu_row_id)
        if index is None:
            return
        row = self.rows[index]
        spec = self._variable_spec_for_field(self.current_menu_field)
        if spec is None or not self._variable_enabled_for_row(row, spec):
            return
        enabled = self._tolerance_variable_compensator_enabled(
            OpticalVariable(index, spec.parameter, 0.0, 1.0, name=f"{row.name} {spec.label}")
        )
        self._begin_history_capture()
        self.set_tolerance_compensator_enabled(index, spec.parameter, not enabled)
        self._commit_history_capture()
        role = "compensator" if not enabled else "tolerance-only"
        self.append_progress(f"Row {index} {spec.label} set to {role}.")
        self._cleanup_current_popup_menu()

    def edit_current_bounds(self) -> None:
        self._main_optimization_panel().edit_current_bounds()

    def _show_centered_dialog(self, dialog: tk.Toplevel) -> None:
        def place_dialog() -> None:
            if not dialog.winfo_exists():
                return
            dialog.update_idletasks()
            dialog_width = max(dialog.winfo_reqwidth(), dialog.winfo_width(), 1)
            dialog_height = max(dialog.winfo_reqheight(), dialog.winfo_height(), 1)
            screen_width = max(dialog.winfo_screenwidth(), 1)
            screen_height = max(dialog.winfo_screenheight(), 1)
            pos_x = max((screen_width - dialog_width) // 2, 0)
            pos_y = max((screen_height - dialog_height) // 2, 0)
            dialog.geometry(f"{dialog_width}x{dialog_height}+{pos_x}+{pos_y}")

        place_dialog()
        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()
        dialog.after_idle(place_dialog)
        dialog.after(80, place_dialog)

    @staticmethod

    def open_paraxial_matrix_report(self) -> None:
        self._main_paraxial_analysis_dialogs().open_paraxial_matrix_report()

    def _main_paraxial_analysis_dialogs(self) -> MainParaxialAnalysisDialogs:
        dialog = self.__dict__.get("_main_paraxial_analysis_dialogs_instance")
        if dialog is None:
            dialog = MainParaxialAnalysisDialogs(self, short_error_message=_short_error_message)
            self._main_paraxial_analysis_dialogs_instance = dialog
        return dialog

    def open_gaussian_beam_report(self) -> None:
        self._main_paraxial_analysis_dialogs().open_gaussian_beam_report()

    def clear_current_bounds(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        index = self._table_item_row_index(self.current_menu_row_id)
        if index is None:
            return
        row = self.rows[index]
        spec = self._variable_spec_for_field(self.current_menu_field)
        if spec is None:
            return
        self._begin_history_capture()
        spec.set_bounds(row, None)
        self._commit_history_capture()
        self.append_progress(f"Bounds cleared for row {index} {spec.label}.")
        self._cleanup_current_popup_menu()


    def clear_optimization_marks(self) -> None:
        for row in self.rows:
            row.optimize_rc = False
            row.optimize_thickness = False
            row.advanced = dict(row.advanced or {})
            row.advanced.pop("Var", None)
            row.advanced.pop("VarBounds", None)
        self._sync_table()

    def benchmark_psf_mtf(self) -> None:
        self.append_progress("Benchmark PSF/MTF started.")
        try:
            self._report_compute_backends()
            self._read_rows_from_table()
            system = self.build_system()
            wavelength = self._current_wavelength()
            field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
            field_y = self._current_field_angle_deg() if field_type == "angle" else self._current_field_height()
            sample_count = max(64, self._current_ray_count() * 12)
            self.append_progress(f"Tracing benchmark rays: sample_count={sample_count}")
            x_local, y_local, workers = self._build_geometric_image_samples(
                system,
                wavelength,
                sample_count=sample_count,
                pattern="hexapolar",
                surface_index=self._analysis_surface_index(),
                aperture_type=self._current_aperture_type(),
                aperture_value=self._current_aperture_value(),
                field_type=field_type,
                field_x=0.0,
                field_y=field_y,
            )
            if x_local.size < 4:
                raise RuntimeError("Not enough traced image-plane samples for benchmark")

            span_x = max(float(np.ptp(x_local)), 1e-3)
            span_y = max(float(np.ptp(y_local)), 1e-3)
            span = max(span_x, span_y) * 1.25
            bins = 256

            t0 = time.perf_counter()
            hist_cpu, xedges_cpu, _yedges_cpu = np.histogram2d(
                x_local,
                y_local,
                bins=bins,
                range=[[-span / 2.0, span / 2.0], [-span / 2.0, span / 2.0]],
            )
            psf_cpu = hist_cpu / max(np.sum(hist_cpu), 1.0)
            otf_cpu = np.fft.fftshift(np.fft.fft2(psf_cpu))
            mtf_cpu = np.abs(otf_cpu)
            mtf_cpu /= max(float(np.max(mtf_cpu)), 1e-12)
            _freq_cpu = np.fft.fftshift(np.fft.fftfreq(bins, d=float(xedges_cpu[1] - xedges_cpu[0])))
            cpu_sec = time.perf_counter() - t0

            gpu_results: list[tuple[str, float]] = []

            cp = _optional_cupy()
            if cp is not None:
                try:
                    if int(cp.cuda.runtime.getDeviceCount()) > 0:
                        _ = cp.zeros((1,), dtype=cp.float32)
                        cp.cuda.Stream.null.synchronize()
                        t1 = time.perf_counter()
                        x_gpu = cp.asarray(x_local, dtype=cp.float64)
                        y_gpu = cp.asarray(y_local, dtype=cp.float64)
                        hist_gpu, xedges_gpu, _yedges_gpu = cp.histogram2d(
                            x_gpu,
                            y_gpu,
                            bins=bins,
                            range=[[-span / 2.0, span / 2.0], [-span / 2.0, span / 2.0]],
                        )
                        psf_gpu = hist_gpu / cp.maximum(cp.sum(hist_gpu), 1.0)
                        otf_gpu = cp.fft.fftshift(cp.fft.fft2(psf_gpu))
                        mtf_gpu = cp.abs(otf_gpu)
                        mtf_gpu /= cp.maximum(cp.max(mtf_gpu), 1e-12)
                        _freq_gpu = cp.fft.fftshift(
                            cp.fft.fftfreq(bins, d=float(cp.asnumpy(xedges_gpu[1] - xedges_gpu[0])))
                        )
                        cp.cuda.Stream.null.synchronize()
                        gpu_results.append(("CuPy", time.perf_counter() - t1))
                except Exception as exc:
                    self.append_debug(f"Benchmark CuPy path failed: {_short_error_message(exc)}")

            torch = _optional_torch()
            if torch is not None:
                try:
                    if bool(torch.cuda.is_available()):
                        device = torch.device("cuda")
                        _ = torch.zeros((1,), dtype=torch.float32, device=device)
                        if hasattr(torch.cuda, "synchronize"):
                            torch.cuda.synchronize()
                        t2 = time.perf_counter()
                        lower = -span / 2.0
                        upper = span / 2.0
                        step = (upper - lower) / float(bins)
                        x_t = torch.as_tensor(x_local, dtype=torch.float64, device=device)
                        y_t = torch.as_tensor(y_local, dtype=torch.float64, device=device)
                        ix = torch.floor((x_t - lower) / step).to(torch.int64)
                        iy = torch.floor((y_t - lower) / step).to(torch.int64)
                        valid = (ix >= 0) & (ix < bins) & (iy >= 0) & (iy < bins)
                        ix = ix[valid]
                        iy = iy[valid]
                        lin = ix * bins + iy
                        hist_t = torch.zeros(bins * bins, dtype=torch.float64, device=device)
                        hist_t.scatter_add_(0, lin, torch.ones_like(lin, dtype=torch.float64))
                        hist_t = hist_t.view(bins, bins)
                        psf_t = hist_t / torch.clamp(torch.sum(hist_t), min=1.0)
                        otf_t = torch.fft.fftshift(torch.fft.fft2(psf_t))
                        mtf_t = torch.abs(otf_t)
                        mtf_t = mtf_t / torch.clamp(torch.max(mtf_t), min=1e-12)
                        _freq_t = torch.fft.fftshift(torch.fft.fftfreq(bins, d=step, device=device))
                        if hasattr(torch.cuda, "synchronize"):
                            torch.cuda.synchronize()
                        gpu_results.append(("Torch", time.perf_counter() - t2))
                except Exception as exc:
                    self.append_debug(f"Benchmark Torch path failed: {_short_error_message(exc)}")

            self.append_progress(
                f"Benchmark traced rays={x_local.size} | trace workers={workers} | bins={bins} | CPU post={cpu_sec:.6f}s"
            )
            if gpu_results:
                gpu_results.sort(key=lambda item: item[1])
                best_name, best_sec = gpu_results[0]
                speedup = cpu_sec / max(best_sec, 1e-12)
                for name, timing in gpu_results:
                    self.append_progress(f"Benchmark {name} post={timing:.6f}s")
                self.append_progress(
                    f"Benchmark best GPU={best_name} {best_sec:.6f}s | speedup={speedup:.2f}x"
                )
                gpu_summary = ", ".join(f"{name}={timing:.6f}s" for name, timing in gpu_results)
                self.append_debug(
                    f"PSF/MTF benchmark: rays={x_local.size}, workers={workers}, cpu={cpu_sec:.6f}s, {gpu_summary}, best={best_name}, speedup={speedup:.2f}x"
                )
            else:
                self.append_progress("Benchmark GPU post=unavailable")
                self.append_debug(
                    f"PSF/MTF benchmark: rays={x_local.size}, workers={workers}, cpu={cpu_sec:.6f}s, gpu=unavailable"
                )
            self.status_var.set("Benchmark PSF/MTF completed")
        except Exception as exc:
            self.append_progress(f"Benchmark PSF/MTF failed: {exc}")
            self.append_debug(f"Benchmark PSF/MTF failed: {exc}")
            self.status_var.set("Benchmark PSF/MTF failed")

    def build_system(self, *, require_solids: bool = False, force_rebuild: bool = False):
        row_specs = self._serializable_row_specs()
        signature = _row_specs_signature(row_specs)
        require_geometry = bool(require_solids or self._rows_require_geometry_build(self.rows))
        cached_signature = self.__dict__.get("_system_cache_signature")
        cached_system = self.__dict__.get("_system_cache_system")
        cached_has_solids = bool(self.__dict__.get("_system_cache_has_solids", False))
        cached_geometry_ready = bool(self.__dict__.get("_system_cache_geometry_ready", False))
        if not force_rebuild and cached_system is not None and cached_signature == signature:
            if (not require_geometry or cached_geometry_ready) and (not require_solids or cached_has_solids):
                return cached_system
            try:
                original_build = int(getattr(cached_system, "BUILD", 0))
                cached_system.BUILD = 1
                cached_system.build()
                cached_system.BUILD = original_build
                self._system_cache_has_solids = True
                self._system_cache_geometry_ready = True
                return cached_system
            except Exception:
                pass

        system = _build_system_from_specs(
            row_specs,
            build=1 if require_geometry else 0,
        )
        self._system_cache_signature = signature
        self._system_cache_system = system
        self._system_cache_has_solids = bool(getattr(system.Pr3D, "ExistSolid", 0))
        self._system_cache_geometry_ready = bool(require_geometry)
        return system

    @staticmethod
    def _rows_require_geometry_build(rows: list[SurfaceRow]) -> bool:
        for row in rows:
            if KrakenLayoutEditor._geometry_value_present(row.uda):
                return True
            advanced = row.advanced if isinstance(row.advanced, dict) else {}
            if KrakenLayoutEditor._geometry_value_present(advanced.get("Mask_Shape")):
                return True
            if KrakenLayoutEditor._geometry_value_present(advanced.get("Solid_3d_stl")):
                return True
        return False

    @staticmethod
    def _open3d_step_label_for_optical_solid_row(row) -> str:
        advanced = row.get("advanced", {}) if isinstance(row, dict) else getattr(row, "advanced", {})
        if not isinstance(advanced, dict):
            return ""
        if not KrakenLayoutEditor._geometry_value_present(advanced.get("Solid_3d_stl")):
            return ""
        promotion = advanced.get("StepOverlayPromotion")
        if isinstance(promotion, dict):
            label = str(promotion.get("step_label", "optical") or "optical").strip().lower()
            return label or "optical"
        source_format = str(advanced.get("OpticalSolidSourceFormat", "") or "").strip().upper()
        source_path_text = str(advanced.get("OpticalSolidSourcePath", "") or "").strip()
        source_suffix = ""
        if source_path_text:
            try:
                source_suffix = Path(source_path_text).suffix.lower()
            except Exception:
                source_suffix = ""
        if source_format in {"STEP", "STP"} or source_suffix in {".step", ".stp"}:
            return "optical"
        return ""

    @staticmethod
    def _is_open3d_promoted_optical_solid_row(row) -> bool:
        return bool(KrakenLayoutEditor._open3d_step_label_for_optical_solid_row(row))

    @staticmethod
    def _geometry_value_present(value) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip().lower() not in {"", "none", "0", "0.0"}
        if isinstance(value, (int, float, np.integer, np.floating)):
            return abs(float(value)) > 1e-12
        return True

    def _current_wavelength(self) -> float:
        try:
            return float(self.wavelength_var.get())
        except ValueError:
            return 0.55

    def _current_aperture_type(self) -> str:
        value = self.aperture_type_var.get().strip().upper()
        if value == "FNO":
            return "EPD"
        if value in {"STOP", "EPD"}:
            return value
        return "STOP"

    def _current_aperture_type_label(self) -> str:
        value = self.aperture_type_var.get().strip().upper()
        if value in {"STOP", "EPD", "FNO"}:
            return value
        return "STOP"

    def _current_aperture_value(self) -> float:
        try:
            value = float(self.aperture_value_var.get())
        except ValueError:
            return 1.0
        if value == 0.0:
            return 1.0
        if self._current_aperture_type_label() == "FNO":
            f_number = max(abs(value), 1e-9)
            effl = max(abs(float(self._current_effl_estimate())), 1e-9)
            return effl / f_number
        return value

    def _current_mtf_frequency(self) -> float:
        var = self.__dict__.get("operand_frequency_vars", {}).get("MTF @ freq")
        if var is None:
            return 5.0
        try:
            value = float(var.get())
        except ValueError:
            return 5.0
        return max(0.0, value)

    def _operand_mtf_mode(self, label: str) -> str:
        var = self.__dict__.get("operand_mtf_mode_vars", {}).get(label)
        if var is None:
            return "average"
        value = var.get().strip().lower()
        if value in {"tangential", "sagittal", "average"}:
            return value
        return "average"

    def _operand_mtf_algorithm(self, label: str) -> str:
        var = self.__dict__.get("operand_mtf_algorithm_vars", {}).get(label)
        if var is None:
            return "diffraction_fft"
        value = var.get().strip().lower()
        if value == "diffraction fft":
            return "diffraction_fft"
        if value == "lsf fft":
            return "lsf_fft"
        return "psf_fft"

    def _mtf_analysis_settings(self) -> dict[str, float | int | str]:
        return {
            "wavelength": self._current_wavelength(),
            "surface_index": self._analysis_surface_index(),
            "aperture_type": self._current_aperture_type(),
            "aperture_value": self._current_aperture_value(),
            "field_type": ("angle" if self._current_object_mode() == "Infinity" else "height"),
            "field_x": 0.0,
            "field_y": (self._current_field_angle_deg() if self._current_object_mode() == "Infinity" else self._current_field_height()),
            "algorithm": self._operand_mtf_algorithm("MTF @ freq"),
        }

    @staticmethod
    def _normalize_field_type(field_type: str) -> str:
        return FIELD_TYPE_ALIASES.get(str(field_type).strip(), "Angle")

    @staticmethod
    def _field_type_display_label(field_type: str) -> str:
        return FIELD_TYPE_DISPLAY_LABELS.get(KrakenLayoutEditor._normalize_field_type(field_type), "Field")

    @staticmethod
    def _field_type_value_label(field_type: str) -> str:
        labels = {
            "Angle": "Field Half-Angle [deg]",
            "Object Height": "Object Semi-Height [mm]",
            "Paraxial Image Height": "Paraxial Image Semi-Height [mm]",
            "Real Image Height": "Real Image Semi-Height [mm]",
        }
        return labels.get(KrakenLayoutEditor._normalize_field_type(field_type), "Field value")

    @staticmethod
    def _field_type_unit(field_type: str) -> str:
        units = {
            "Angle": "deg",
            "Object Height": "mm",
            "Paraxial Image Height": "mm",
            "Real Image Height": "mm",
        }
        return units.get(KrakenLayoutEditor._normalize_field_type(field_type), "")

    @staticmethod
    def _format_field_sample_value(value: float) -> str:
        return f"{float(value):.3f}".rstrip("0").rstrip(".")

    def _parse_numeric_series(self, value: str) -> list[float]:
        text = str(value or "").strip()
        if not text:
            return []
        samples: list[float] = []
        invalid: list[str] = []
        for token in re.split(r"[\s,;]+", text):
            if not token:
                continue
            try:
                samples.append(float(token))
            except ValueError:
                invalid.append(token)
        if invalid:
            self.append_debug(f"Ignoring invalid numeric samples: {', '.join(invalid)}")
        return samples

    @staticmethod
    def _name_offset(row: SurfaceRow) -> tuple[float, float]:
        if row.surface not in {"Object", "Image"}:
            return (0.0, 0.0)
        name = row.name.lower()
        base_y = max(row.diameter * 0.08, 0.0)
        if "front" in name:
            return (-max(row.diameter * 0.35, 8.0), base_y)
        if "back" in name:
            return (max(row.diameter * 0.15, 2.0), base_y)
        return (0.0, base_y)

    def _render_auxiliary_projection_axes(self, bundle: SceneBundle, max_radius: float) -> None:
        for plane, axis in dict(getattr(self, "_layout_projection_axes", {}) or {}).items():
            projected = project_scene_bundle(
                bundle,
                str(plane),
                filter_projection_axis_fields=self._should_filter_projection_axis_fields(bundle),
                filter_projection_slice=self._should_filter_projection_slice(bundle),
                filter_arm_view=self._filter_projected_scene_for_arm_view,
                filter_ray_display=self._filter_projected_scene_for_ray_display,
            )
            render_projected = self._projected_scene_for_layout_render(projected, suppress_scene_labels=True)
            render_scene_2d(
                render_projected,
                axis,
                show_clipped_rays=self.show_clipped_rays_var.get(),
                show_labels=False,
                ray_count_hint=max(1, self._preview_field_ray_count),
            )
            set_plot_limits(
                axis,
                projected.bounds,
                max_radius=max_radius,
                has_off_axis=True,
                orientation=str(plane),
                use_drawn_data=True,
            )
            x_label, y_label, _title = projection_axis_labels(str(plane))
            axis.set_xlabel(x_label, fontsize=8)
            axis.set_ylabel(y_label, fontsize=8)
            axis.set_title(self._projection_display_title(str(plane), bundle), fontsize=9)
            axis.tick_params(axis="both", which="major", labelsize=8)
            axis.grid(True, alpha=0.2)

    def _plot_refresh_service(self) -> PlotRefreshService:
        service = self.__dict__.get("_plot_refresh_service_instance")
        if service is None:
            service = PlotRefreshService(self)
            self._plot_refresh_service_instance = service
        return service

    def refresh_plot(self, *, suppress_analysis: bool = False, sampling_mode: str | None = None) -> None:
        self._plot_refresh_service().refresh_plot(
            suppress_analysis=suppress_analysis,
            sampling_mode=sampling_mode,
        )


    def _clear_preview_after_reset(self) -> None:
        """Clear UI trace products after Reset without building/tracing."""
        self.last_system = None
        self.last_rays = None
        self._last_preview_trace_signature = None
        self._last_preview_trace_backend = "none"
        self._last_preview_trace_note = ""
        self._last_scene_bundle = None
        self._last_optics_info = None
        self._last_wavefront_samples = []
        self._last_zernike_coefficients = []
        self._preview_field_ray_count = 1
        self._preview_field_bundle_count = 1
        self._system_cache_signature = None
        self._system_cache_system = None
        self._system_cache_has_solids = False
        self._layout_pick_regions = {}
        self._layout_ray_pick_regions = []
        self._layout_projected_rays_by_index = {}
        self._layout_selected_ray_index = None
        self._analysis_axes = []
        self._analysis_ax = None
        self._layout_projection_axes = {}
        self._clear_cardinal_marker_artists()
        self._clear_physical_distance_artists()
        self._clear_layout_selection_overlay()
        if getattr(self, "results_table", None) is not None:
            self.results_table.delete(*self.results_table.get_children())
        self._refresh_ray_inspector_if_open()
        self._refresh_branch_gaussian_q_report_if_open()
        self._refresh_branch_tree_if_open()
        self._refresh_branch_throughput_report_if_open()
        self._refresh_detector_aperture_report_if_open()
        self._refresh_source_illumination_report_if_open()
        self._refresh_analysis_branch_choices()
        self._refresh_nonseq_scene_graph_if_open()
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("")
        self.ax.set_xlabel("")
        self.ax.set_ylabel("")
        self.ax.grid(False)
        self.figure.subplots_adjust(left=0.07, right=0.98, bottom=0.15, top=0.92, wspace=0.28)
        self._sync_object_controls()
        self._configure_plot_hover_hints()
        self.canvas.draw_idle()
        self.progress_spinner_var.set("idle")
        self.progress_percent_var.set("")
        self.progress_bar_var.set(0.0)
        self.status_var.set("Reset complete. Table contains only Object and Image; click Update to trace.")
        self.append_progress("Reset completed without tracing.")
        if self._initial_layout_passes < 40:
            self.after(50, self._set_initial_pane_layout)

    def _autosave_plot(self) -> None:
        if not self.auto_save_plot_var.get():
            return
        if self._autosave_after_id is not None:
            try:
                self.after_cancel(self._autosave_after_id)
            except Exception:
                pass
        self._autosave_after_id = self.after(400, self._do_autosave_plot)

    def _do_autosave_plot(self) -> None:
        self._autosave_after_id = None
        if not self.auto_save_plot_var.get():
            return
        if self.winfo_width() < 1200 or self.winfo_height() < 700:
            self._autosave_after_id = self.after(400, self._do_autosave_plot)
            return
        try:
            AUTO_PLOT_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.update_idletasks()
            self.canvas.draw()
            self.figure.savefig(AUTO_PLOT_PATH, dpi=150)
        except Exception as exc:
            self.append_debug(f"Auto-save plot failed: {exc}")

    def _plot_atmosphere_image_residual(
        self,
        analysis_ax,
        system,
        reference_wavelength: float,
        settings: dict[str, float | int],
        wavelengths: np.ndarray,
    ) -> None:
        self._update_analysis_progress("Tracing atmospheric residual", 1, 3)
        reference_wavelength = float(np.clip(float(reference_wavelength), float(wavelengths[0]), float(wavelengths[-1])))
        pupil = Kos.PupilCalc(
            system,
            self._analysis_surface_index(),
            reference_wavelength,
            self._current_aperture_type(),
            self._current_aperture_value(),
        )
        pupil.Samp = max(4, min(12, int(np.sqrt(max(1, self._current_ray_count())) * 2)))
        pupil.Ptype = self._current_analysis_pupil_pattern("hexapolar")
        pupil.FieldType = "angle"
        pupil.FieldX = 0.0
        pupil.FieldY = self._current_field_angle_deg() if self._current_object_mode() == "Infinity" else 0.0
        pupil.AtmosRef = 1
        pupil.T = float(settings["temperature_k"])
        pupil.P = float(settings["pressure_pa"])
        pupil.H = float(settings["humidity"])
        pupil.xc = float(settings["co2_ppm"])
        pupil.lat = float(settings["latitude_deg"])
        pupil.h = float(settings["altitude_m"])
        pupil.l1 = reference_wavelength
        pupil.z0 = float(settings["zenith_deg"])

        centroids: list[tuple[float, float, float, float]] = []
        total = max(1, int(wavelengths.size))
        for index, sample_wavelength in enumerate(wavelengths, start=1):
            self._update_analysis_progress(f"ADC residual {index}/{total}", index, total)
            pupil.l2 = float(sample_wavelength)
            x, y, z, l, m, n = pupil.Pattern2Field()
            rays_for_wavelength = Kos.raykeeper(system)
            Kos.TraceLoop(x, y, z, l, m, n, float(sample_wavelength), rays_for_wavelength, clean=1)
            x_img, y_img, _z_img, _l_img, _m_img, _n_img = self._pick_image_plane_data(rays_for_wavelength)
            x_img = np.asarray(x_img, dtype=float).ravel()
            y_img = np.asarray(y_img, dtype=float).ravel()
            finite = np.isfinite(x_img) & np.isfinite(y_img)
            x_img = x_img[finite]
            y_img = y_img[finite]
            if x_img.size == 0:
                continue
            cx = float(np.mean(x_img))
            cy = float(np.mean(y_img))
            radius = np.sqrt((x_img - cx) * (x_img - cx) + (y_img - cy) * (y_img - cy))
            rms = float(np.sqrt(np.mean(radius * radius)))
            centroids.append((float(sample_wavelength), cx, cy, rms))

        if len(centroids) < 2:
            raise RuntimeError("Not enough finite atmospheric image residual samples")

        self._update_analysis_progress("Rendering residual", 3, 3)
        centroid_array = np.asarray(centroids, dtype=float)
        valid_wavelengths = centroid_array[:, 0]
        centroid_x = centroid_array[:, 1]
        centroid_y = centroid_array[:, 2]
        spot_rms_um = centroid_array[:, 3] * 1000.0
        reference_x = float(np.interp(reference_wavelength, valid_wavelengths, centroid_x))
        reference_y = float(np.interp(reference_wavelength, valid_wavelengths, centroid_y))
        residual_x_um = (centroid_x - reference_x) * 1000.0
        residual_y_um = (centroid_y - reference_y) * 1000.0
        residual_mag_um = np.sqrt(residual_x_um * residual_x_um + residual_y_um * residual_y_um)
        blue_red_um = float(
            np.sqrt(
                (residual_x_um[-1] - residual_x_um[0]) * (residual_x_um[-1] - residual_x_um[0])
                + (residual_y_um[-1] - residual_y_um[0]) * (residual_y_um[-1] - residual_y_um[0])
            )
        )
        max_residual_um = float(np.max(residual_mag_um))
        max_spot_rms_um = float(np.max(spot_rms_um))

        line_x, = analysis_ax.plot(valid_wavelengths, residual_x_um, color="#2563eb", marker="o", markersize=3.0)
        line_y, = analysis_ax.plot(valid_wavelengths, residual_y_um, color="#dc2626", marker="s", markersize=3.0)
        line_mag, = analysis_ax.plot(valid_wavelengths, residual_mag_um, color="#111827", linewidth=2.0)
        analysis_ax.axvline(reference_wavelength, color="#64748b", linewidth=0.8, alpha=0.65)
        analysis_ax.axhline(0.0, color="#64748b", linewidth=0.8, alpha=0.45)
        analysis_ax.set_title("Atmospheric Image Residual")
        analysis_ax.set_xlabel("Wavelength [um]")
        analysis_ax.set_ylabel(f"Image residual vs {reference_wavelength:.4g} um [um]")
        analysis_ax.set_box_aspect(0.62)
        analysis_ax.grid(True, alpha=0.2)
        analysis_ax.legend([line_x, line_y, line_mag], ["X", "Y", "Magnitude"], loc="best", fontsize=8)
        analysis_ax.text(
            0.02,
            0.03,
            f"blue-red residual: {blue_red_um:.4g} um\n"
            f"max residual: {max_residual_um:.4g} um\n"
            f"max spot RMS: {max_spot_rms_um:.4g} um",
            transform=analysis_ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=7.5,
            bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.78, "pad": 3},
        )
        result_items = [
            ("Mode", "Atmos image residual"),
            ("Reference wavelength [um]", f"{reference_wavelength:.6g}"),
            ("Samples", str(int(valid_wavelengths.size))),
            ("Zenith angle [deg]", f"{float(settings['zenith_deg']):.6g}"),
            ("Blue-red residual [um]", f"{blue_red_um:.6g}"),
            ("Max residual [um]", f"{max_residual_um:.6g}"),
            ("Max spot RMS [um]", f"{max_spot_rms_um:.6g}"),
        ]
        if getattr(self, "results_table", None) is not None:
            self._set_results(result_items)
        self.append_debug(
            f"Atmos image residual ok: samples={valid_wavelengths.size}, reference_um={reference_wavelength:.6g}, "
            f"blue_red_um={blue_red_um:.6g}, max_residual_um={max_residual_um:.6g}"
        )
        self._finish_analysis_progress("Atmosphere analysis", success=True)

    def _current_interferogram_settings(self) -> dict[str, object]:
        settings: dict[str, object] = {
            "analysis_title": "Interferogram",
            "detector_port": "cross",
            "detector_size_mm": 12.0,
            "pixels": 256,
            "fringe_tilt_x_mrad": 1.5,
            "fringe_tilt_y_mrad": 0.0,
            "opd_offset_um": 0.0,
            "visibility": 1.0,
            "coherence_mode": COHERENT_SUM_MODE_DEFAULT,
            "gaussian_q_weighting": "auto",
        }
        for row in getattr(self, "rows", []) or []:
            advanced = getattr(row, "advanced", {}) or {}
            if not isinstance(advanced, dict):
                continue
            row_settings = advanced.get("Interferogram")
            if isinstance(row_settings, dict):
                settings.update(row_settings)
        return settings

    @staticmethod
    def _raykeeper_value(rays, name: str, index: int, default=None):
        values = getattr(rays, name, None)
        if values is None or index >= len(values):
            return default
        arr = np.asarray(values[index]).ravel()
        if arr.size == 0:
            return default
        return arr[-1]

    def _interferogram_output_pair(self, settings: dict[str, object]) -> tuple[str, str, str]:
        port = str(settings.get("detector_port", "cross") or "cross").strip().lower()
        if port in {"return", "source", "source return", "output port 1", "port 1", "tt/rr"}:
            return "TT", "RR", "Output port 1"
        return "TR", "RT", "Detector output port"

    def _interferogram_branch_samples(
        self,
        rays,
        settings: dict[str, object],
        records: list[dict[str, object]] | None = None,
    ) -> tuple[dict, dict, str]:
        code_a, code_b, port_label = self._interferogram_output_pair(settings)
        grouped: dict[str, list[dict[str, float | str]]] = {code_a: [], code_b: []}

        def append_sample(
            *,
            branch_path: str,
            power: float,
            source_weight: float,
            source_power: float,
            top_mm: float,
            phase_deg: float,
            analysis_source: str,
        ) -> None:
            selectors = self._branch_path_selector_sequence(branch_path)
            if len(selectors) < 2:
                return
            code = "".join("T" if item in {"T", "transmit"} else "R" for item in selectors[-2:])
            if code not in grouped:
                return
            weight = max(power * max(source_weight, 0.0) * max(source_power, 0.0), 0.0)
            if weight <= 0.0:
                return
            grouped[code].append(
                {
                    "code": code,
                    "path": branch_path,
                    "power": weight,
                    "top_mm": top_mm,
                    "phase_deg": phase_deg,
                    "analysis_source": analysis_source,
                }
            )

        analysis_source = "raykeeper"
        ray_records: list[dict[str, object]] = []
        if records is not None:
            ray_records = list(records)
        else:
            try:
                ray_records = self._collect_ray_inspector_records(rays=rays)
            except Exception:
                ray_records = []

        event_records = [
            record
            for record in ray_records
            if str(record.get("analysis_source", "") or "") == "ray_events"
            and str(record.get("branch_path", "") or "").strip()
        ]
        if event_records:
            analysis_source = "ray_events"
            for record in event_records:
                branch_path = str(record.get("branch_path", "") or "")
                power = self._safe_positive_float(record.get("branch_power"), np.nan)
                if not np.isfinite(power):
                    power = self._safe_positive_float(record.get("transmission"), 1.0)
                source_weight = self._safe_positive_float(record.get("source_weight"), 1.0)
                source_power = self._safe_positive_float(record.get("source_power"), 1.0)
                top_mm = self._safe_float(record.get("top"), self._safe_float(record.get("op"), 0.0))
                phase_deg = self._safe_float(record.get("branch_phase", record.get("branch_phase_deg", 0.0)), 0.0)
                append_sample(
                    branch_path=branch_path,
                    power=power,
                    source_weight=source_weight,
                    source_power=source_power,
                    top_mm=top_mm,
                    phase_deg=phase_deg,
                    analysis_source=analysis_source,
                )
        else:
            branch_paths = list(getattr(rays, "BRANCH_PATH", []) or [])
            for ray_index in range(len(branch_paths)):
                branch_path = str(self._raykeeper_value(rays, "BRANCH_PATH", ray_index, "") or "")
                try:
                    power = float(self._raykeeper_value(rays, "BRANCH_POWER", ray_index, 0.0) or 0.0)
                except Exception:
                    power = 0.0
                try:
                    source_weight = float(self._raykeeper_value(rays, "SOURCE_WEIGHT", ray_index, 1.0) or 1.0)
                except Exception:
                    source_weight = 1.0
                try:
                    top_mm = float(self._raykeeper_value(rays, "TOP", ray_index, 0.0) or 0.0)
                except Exception:
                    top_mm = 0.0
                try:
                    phase_deg = float(self._raykeeper_value(rays, "BRANCH_PHASE", ray_index, 0.0) or 0.0)
                except Exception:
                    phase_deg = 0.0
                append_sample(
                    branch_path=branch_path,
                    power=power,
                    source_weight=source_weight,
                    source_power=1.0,
                    top_mm=top_mm,
                    phase_deg=phase_deg,
                    analysis_source=analysis_source,
                )
        if not grouped[code_a] or not grouped[code_b]:
            raise RuntimeError(f"Need both {code_a} and {code_b} Michelson paths at the detector port")

        def summarize(samples: list[dict[str, float | str]]) -> dict[str, float | str]:
            powers = np.asarray([float(sample["power"]) for sample in samples], dtype=float)
            total = float(np.sum(powers))
            if total <= 0.0:
                raise RuntimeError("Zero path power")
            tops = np.asarray([float(sample["top_mm"]) for sample in samples], dtype=float)
            phases = np.asarray([float(sample["phase_deg"]) for sample in samples], dtype=float)
            return {
                "code": str(samples[0]["code"]),
                "path": str(samples[0]["path"]),
                "power": total,
                "top_mm": float(np.average(tops, weights=powers)),
                "phase_deg": float(np.average(phases, weights=powers)),
                "count": float(len(samples)),
                "analysis_source": str(samples[0]["analysis_source"]),
            }

        return summarize(grouped[code_a]), summarize(grouped[code_b]), port_label

    def _preferred_interferogram_filter(
        self,
        settings: dict[str, object],
        ray_records: list[dict[str, object]] | None = None,
    ) -> str:
        current = self._current_analysis_branch_filter()
        records = self._collect_branch_throughput_records(ray_records=ray_records)
        choices = self._branch_throughput_filter_choices(records)
        if current in choices and current.startswith(("Output:", "Terminal:")) and not _is_all_path_filter(current):
            return current
        port = str(settings.get("detector_port", "cross") or "cross").strip().lower()
        preferred_output = (
            "Output: Source return port"
            if port in {"return", "source", "source return", "output port 1", "port 1", "tt/rr"}
            else "Output: Detector output port"
        )
        if preferred_output in choices:
            return preferred_output
        detector_terminals = [choice for choice in choices if choice.startswith("Terminal:") and "Detector" in choice]
        if detector_terminals:
            return detector_terminals[0]
        if current in choices:
            return current
        return ANALYSIS_PATH_FILTER_DEFAULT

    def _interferogram_detector_field_data(
        self,
        system,
        wavelength: float,
        settings: dict[str, object],
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        code_a, code_b, port_label = self._interferogram_output_pair(settings)
        filter_text = self._preferred_interferogram_filter(settings, ray_records=ray_records)
        coherence_mode = _normalize_coherent_sum_mode(settings.get("coherence_mode", COHERENT_SUM_MODE_DEFAULT))
        gaussian_setting = str(settings.get("gaussian_q_weighting", "auto") or "auto").strip().lower()
        gaussian_q_weighting = (
            self._should_use_gaussian_q_detector_weighting()
            if gaussian_setting in {"", "auto"}
            else gaussian_setting in {"1", "true", "yes", "on", "enabled"}
        )
        data = self._coherent_detector_field_data(
            system,
            wavelength,
            filter_text,
            coherence_mode=coherence_mode,
            opd_offset_um=float(settings.get("opd_offset_um", 0.0)),
            phase_ramp_x_mrad=float(settings.get("fringe_tilt_x_mrad", 0.0)),
            phase_ramp_y_mrad=float(settings.get("fringe_tilt_y_mrad", 0.0)),
            visibility_scale=float(settings.get("visibility", 1.0)),
            gaussian_q_weighting=gaussian_q_weighting,
            ray_records=ray_records,
        )
        available_codes = {str(code) for code in list(data.get("branch_codes", []) or [])}
        pair_key = self._coherent_detector_pair_key(code_a, code_b)
        pair_maps = dict(data.get("pair_interference_by_codepair", {}) or {})
        pair_map = np.asarray(
            pair_maps.get(pair_key, np.zeros_like(np.asarray(data.get("intensity", np.asarray([])), dtype=float))),
            dtype=float,
        )
        occupied_bins = int(data.get("occupied_bins", 0) or 0)
        pair_peak = float(np.max(np.abs(pair_map))) if pair_map.size else 0.0
        reliable = (
            {code_a, code_b}.issubset(available_codes)
            and int(data.get("sample_count", 0) or 0) >= 8
            and occupied_bins >= 4
            and pair_peak > 1e-12
        )
        result = dict(data)
        result.update(
            {
                "data_source": "coherent_detector",
                "analysis_title": str(settings.get("analysis_title", "Interferogram") or "Interferogram").strip(),
                "port_label": port_label,
                "filter_text": filter_text,
                "expected_branch_codes": [code_a, code_b],
                "pair_key": pair_key,
                "pair_interference_peak": pair_peak,
                "reliable": reliable,
                "extent": [
                    float(np.asarray(data["x_edges"], dtype=float)[0]),
                    float(np.asarray(data["x_edges"], dtype=float)[-1]),
                    float(np.asarray(data["y_edges"], dtype=float)[0]),
                    float(np.asarray(data["y_edges"], dtype=float)[-1]),
                ],
            }
        )
        return result

    def _interferogram_analysis_data(self, system, rays, wavelength: float) -> dict[str, object]:
        settings = self._current_interferogram_settings()
        ray_records: list[dict[str, object]] | None = None
        try:
            ray_records = self._ray_analysis_records_for_trace(system=system, rays=rays)
        except Exception:
            ray_records = []
        coherent_reason = ""
        try:
            coherent = self._interferogram_detector_field_data(system, wavelength, settings, ray_records=ray_records)
            if bool(coherent.get("reliable")):
                coherent["fallback_reason"] = ""
                return coherent
            coherent_reason = (
                "coherent detector fallback: "
                f"samples={int(coherent.get('sample_count', 0) or 0)}, "
                f"occupied_bins={int(coherent.get('occupied_bins', 0) or 0)}, "
                f"pair_peak={float(coherent.get('pair_interference_peak', 0.0) or 0.0):.6g}, "
                f"codes={','.join(str(code) for code in coherent.get('branch_codes', []) or []) or '-'}"
            )
        except Exception as exc:
            coherent_reason = f"coherent detector unavailable: {_short_error_message(exc)}"

        beam_a, beam_b, port_label = self._interferogram_branch_samples(rays, settings, records=ray_records)
        wavelength_um = max(float(wavelength), 1e-12)
        wavelength_mm = wavelength_um * 1e-3
        detector_size = max(float(settings.get("detector_size_mm", 12.0)), 1e-6)
        pixels = max(32, min(int(float(settings.get("pixels", 256))), 1024))
        tilt_x = float(settings.get("fringe_tilt_x_mrad", 1.5)) * 1e-3
        tilt_y = float(settings.get("fringe_tilt_y_mrad", 0.0)) * 1e-3
        opd_um = (float(beam_b["top_mm"]) - float(beam_a["top_mm"])) * 1000.0 + float(settings.get("opd_offset_um", 0.0))
        branch_phase_deg = float(beam_b["phase_deg"]) - float(beam_a["phase_deg"])
        phase0 = (2.0 * np.pi * opd_um / wavelength_um) + np.deg2rad(branch_phase_deg)
        axis = np.linspace(-0.5 * detector_size, 0.5 * detector_size, pixels)
        grid_x, grid_y = np.meshgrid(axis, axis)
        spatial_phase = (2.0 * np.pi / wavelength_mm) * (tilt_x * grid_x + tilt_y * grid_y)
        coherent_term = 2.0 * np.sqrt(max(float(beam_a["power"]), 0.0) * max(float(beam_b["power"]), 0.0)) * min(max(float(settings.get("visibility", 1.0)), 0.0), 1.0)
        intensity = (
            max(float(beam_a["power"]), 0.0)
            + max(float(beam_b["power"]), 0.0)
            + coherent_term * np.cos(phase0 + spatial_phase)
        )
        intensity = np.asarray(intensity, dtype=float)
        intensity = np.where(intensity > 0.0, intensity, 0.0)
        detector_radius = 0.5 * detector_size
        radius = np.sqrt(grid_x * grid_x + grid_y * grid_y)
        intensity = np.where(radius <= detector_radius, intensity, np.nan)
        visibility = coherent_term / max(float(beam_a["power"]) + float(beam_b["power"]), 1e-15)
        return {
            "data_source": "analytic_path_average",
            "analysis_title": str(settings.get("analysis_title", "Interferogram") or "Interferogram").strip(),
            "port_label": port_label,
            "intensity": intensity,
            "extent": [-0.5 * detector_size, 0.5 * detector_size, -0.5 * detector_size, 0.5 * detector_size],
            "coordinate_label": "detector synthetic",
            "branch_codes": [str(beam_a["code"]), str(beam_b["code"])],
            "sample_count": int(float(beam_a.get("count", 0.0)) + float(beam_b.get("count", 0.0))),
            "bins": pixels,
            "total_input_power": float(beam_a["power"]) + float(beam_b["power"]),
            "total_coherent_power": float(np.nansum(intensity)),
            "peak_intensity": float(np.nanmax(intensity)) if intensity.size else 0.0,
            "coherence_mode": str(settings.get("coherence_mode", COHERENT_SUM_MODE_DEFAULT)),
            "coherence_group_count": 2,
            "polarization_model": "Analytic path-average branch sum",
            "filter_text": self._preferred_interferogram_filter(settings, ray_records=ray_records),
            "beam_a": beam_a,
            "beam_b": beam_b,
            "opd_um": opd_um,
            "branch_phase_deg": branch_phase_deg,
            "visibility": visibility,
            "fallback_reason": coherent_reason,
            "analysis_sources": sorted(
                {
                    str(beam_a.get("analysis_source", "") or ""),
                    str(beam_b.get("analysis_source", "") or ""),
                }
            ),
        }

    def _plot_interferogram_analysis(self, analysis_ax, system, rays, wavelength: float) -> None:
        self._set_analysis_parallel_status("Interferogram", 1, False)
        self._begin_analysis_progress("Interferogram analysis")
        try:
            self._update_analysis_progress("Building detector interferogram", 1, 3)
            data = self._interferogram_analysis_data(system, rays, wavelength)
            intensity = np.asarray(data["intensity"], dtype=float)
            peak = float(np.nanmax(intensity)) if intensity.size else 0.0
            if peak <= 0.0 or not np.isfinite(peak):
                raise RuntimeError("Interferogram has zero finite intensity")
            display = intensity / peak
            extent = [float(value) for value in list(data.get("extent", (-1.0, 1.0, -1.0, 1.0)))]
            self._update_analysis_progress("Rendering", 2, 3)
            cmap = colormaps.get_cmap("magma").copy()
            cmap.set_bad("#f8fafc")
            image = analysis_ax.imshow(
                display,
                origin="lower",
                extent=extent,
                cmap=cmap,
                vmin=0.0,
                vmax=1.0,
                interpolation="bilinear",
            )
            title = str(data.get("analysis_title", "Interferogram") or "Interferogram").strip()
            analysis_ax.set_title(f"{title}  |  {data.get('port_label', 'Detector output')}")
            if str(data.get("data_source")) == "coherent_detector":
                coordinate_label = str(data.get("coordinate_label", "detector local"))
                analysis_ax.set_xlabel(f"X [{coordinate_label}, mm]")
                analysis_ax.set_ylabel(f"Y [{coordinate_label}, mm]")
            else:
                analysis_ax.set_xlabel("Detector X [mm]")
                analysis_ax.set_ylabel("Detector Y [mm]")
            analysis_ax.set_aspect("equal", adjustable="box")
            analysis_ax.set_box_aspect(0.82)
            analysis_ax.grid(False)
            self.figure.colorbar(image, ax=analysis_ax, fraction=0.046, pad=0.04, label="Normalized intensity")
            self._update_analysis_progress("Annotating", 3, 3)
            if str(data.get("data_source")) == "coherent_detector":
                pair_peak = float(data.get("pair_interference_peak", 0.0) or 0.0)
                branch_codes = ", ".join(str(code) for code in data.get("branch_codes", []) or [])
                gaussian_note = (
                    f"\nGaussian q: traces={int(data.get('gaussian_q_trace_count', 0) or 0)}, "
                    f"stable={int(data.get('gaussian_q_stable_count', 0) or 0)}, "
                    f"mean clip={float(data.get('gaussian_q_mean_clip', 1.0) or 1.0):.4g}"
                    if bool(data.get("gaussian_q_weighted", False))
                    else ""
                )
                detector_sum_label = (
                    "Gaussian-q detector-bin coherent sum"
                    if bool(data.get("gaussian_q_weighted", False))
                    else "Detector-bin coherent sum"
                )
                analysis_ax.text(
                    0.02,
                    0.02,
                    f"{detector_sum_label}\n"
                    f"{data.get('filter_text', ANALYSIS_PATH_FILTER_DEFAULT)}\n"
                    f"{data.get('terminal_label', 'Detector')} | codes={branch_codes or '-'}\n"
                    f"samples={int(data.get('sample_count', 0) or 0)}, bins={int(data.get('bins', 0) or 0)}, occupied={int(data.get('occupied_bins', 0) or 0)}\n"
                    f"input={float(data.get('total_input_power', 0.0) or 0.0):.6g}, displayed={float(data.get('total_coherent_power', 0.0) or 0.0):.6g}\n"
                    f"mode={data.get('coherence_mode', COHERENT_SUM_MODE_DEFAULT)} | groups={int(data.get('coherence_group_count', 0) or 0)}\n"
                    f"pair peak={pair_peak:.4g}, visibility={float(data.get('visibility_scale', 1.0) or 1.0):.3g}"
                    f"{gaussian_note}",
                    transform=analysis_ax.transAxes,
                    ha="left",
                    va="bottom",
                    fontsize=7.5,
                    color="#111827",
                    bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.82, "pad": 3},
                )
                self.append_debug(
                    f"Interferogram ok: source=coherent_detector, filter={data.get('filter_text')}, "
                    f"terminal={data.get('terminal_label')}, codes={branch_codes}, "
                    f"samples={int(data.get('sample_count', 0) or 0)}, occupied={int(data.get('occupied_bins', 0) or 0)}, "
                    f"pair_peak={pair_peak:.6g}, mode={data.get('coherence_mode', COHERENT_SUM_MODE_DEFAULT)}, "
                    f"gaussian_q={bool(data.get('gaussian_q_weighted', False))}"
                )
            else:
                beam_a = dict(data.get("beam_a", {}) or {})
                beam_b = dict(data.get("beam_b", {}) or {})
                opd_um = float(data.get("opd_um", 0.0) or 0.0)
                branch_phase_deg = float(data.get("branch_phase_deg", 0.0) or 0.0)
                visibility = float(data.get("visibility", 0.0) or 0.0)
                analysis_ax.text(
                    0.02,
                    0.02,
                    f"{beam_a.get('code', 'A')} vs {beam_b.get('code', 'B')}\n"
                    f"OPD {opd_um:.4g} um, phase {branch_phase_deg:.4g} deg\n"
                    f"analytic fallback | {str(data.get('fallback_reason', '') or '-').strip()}",
                    transform=analysis_ax.transAxes,
                    ha="left",
                    va="bottom",
                    fontsize=7.5,
                    color="#111827",
                    bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.82, "pad": 3},
                )
                self.append_debug(
                    f"Interferogram ok: source=analytic_fallback, codes={beam_a.get('code')}:{beam_b.get('code')}, "
                    f"opd_um={opd_um:.6g}, phase_deg={branch_phase_deg:.6g}, visibility={visibility:.6g}, "
                    f"reason={data.get('fallback_reason', '-')}"
                )
            self._finish_analysis_progress("Interferogram analysis", success=True)
        except Exception as exc:
            self.append_debug(f"Interferogram analysis error: {exc}")
            analysis_ax.text(
                0.5,
                0.5,
                "Interferogram unavailable\nNeed a beam-splitter layout with recombined paths",
                ha="center",
                va="center",
            )
            analysis_ax.set_axis_off()
            self._finish_analysis_progress("Interferogram analysis", success=False)

    def _analysis_plot_service(self) -> AnalysisPlotService:
        service = self.__dict__.get("_analysis_plot_service_instance")
        if service is None:
            service = AnalysisPlotService(self)
            self._analysis_plot_service_instance = service
        return service

    def _plot_analysis(self, analysis_ax, system, rays, wavelength: float) -> None:
        self._analysis_plot_service().plot_analysis(analysis_ax, system, rays, wavelength)

    def _plot_analysis_for_mode(self, analysis_ax, system, rays, wavelength: float, mode: str) -> None:
        previous_mode = self.analysis_mode
        try:
            self.analysis_mode = str(mode)
            self._plot_analysis(analysis_ax, system, rays, wavelength)
        finally:
            self.analysis_mode = previous_mode

    def _analysis_surface_index(self) -> int:
        selected = self.analysis_surface_var.get().strip()
        if selected and selected != "Auto":
            try:
                return int(selected.split(":", 1)[0])
            except ValueError:
                pass
        if len(self.rows) <= 2:
            return max(0, len(self.rows) - 1)
        candidate_indices = [i for i, row in enumerate(self.rows[1:-1], start=1)]
        if not candidate_indices:
            return 1
        return min(candidate_indices, key=lambda i: max(self.rows[i].diameter, 1e-9))

    def _current_object_mode(self) -> str:
        mode = self._left_mode_text("object_mode_var", "Finite")
        return mode if mode in {"Finite", "Infinity"} else "Finite"

    def _current_object_distance(self) -> float:
        if self.rows:
            try:
                if any(row.surface == "Mirror" for row in self.rows):
                    distance, _first_source_index = self._paraxial_total_object_gap(self.rows)
                else:
                    distance = float(self.rows[0].thickness)
            except Exception:
                distance = float(self.rows[0].thickness)
        else:
            distance = 100.0
        return max(distance, 1e-6)

    def _requested_field_count(self) -> int:
        text = self._left_mode_text("field_count_var", "1")
        try:
            return max(1, int(float(str(text).strip())))
        except Exception:
            return 1

    def _field_sampling_basis_span(self) -> tuple[str, str, float]:
        if self._current_object_mode() == "Infinity":
            return "angle", "deg", abs(float(self._current_field_angle_deg()))
        return "object height", "mm", abs(float(self._current_field_height()))

    def _field_sampling_is_active(self) -> bool:
        try:
            _basis, _unit, span = self._field_sampling_basis_span()
        except Exception:
            return True
        return bool(np.isfinite(span) and abs(float(span)) > 1e-12)

    def _infinity_field_launch_reference_point(self, system=None) -> np.ndarray:
        try:
            reference_index = int(self._analysis_surface_index())
            reference = np.asarray(
                self._surface_reference_world_point(reference_index, system=system),
                dtype=float,
            ).reshape(-1)[:3]
        except Exception:
            reference = np.asarray((0.0, 0.0, self._current_object_distance()), dtype=float)
        if reference.size < 3 or not np.all(np.isfinite(reference[:3])):
            reference = np.asarray((0.0, 0.0, self._current_object_distance()), dtype=float)
        return reference.astype(float)

    def _center_infinity_bundle_on_launch_reference(self, bundle, *, system=None):
        arrays = tuple(np.asarray(values, dtype=float).reshape(-1).copy() for values in bundle)
        if len(arrays) != 6 or len(arrays[0]) == 0:
            return bundle
        reference = self._infinity_field_launch_reference_point(system=system)
        origins = np.column_stack(arrays[:3])
        directions = np.column_stack(arrays[3:])
        dz = directions[:, 2]
        valid = np.isfinite(dz) & (np.abs(dz) > 1.0e-12)
        if not np.any(valid):
            return arrays
        t = (float(reference[2]) - origins[valid, 2]) / dz[valid]
        hits_xy = origins[valid, :2] + directions[valid, :2] * t[:, None]
        finite = np.all(np.isfinite(hits_xy), axis=1)
        if not np.any(finite):
            return arrays
        center_xy = np.median(hits_xy[finite], axis=0)
        shift_xy = np.asarray(reference[:2], dtype=float) - center_xy
        if not np.all(np.isfinite(shift_xy)):
            return arrays
        arrays = list(arrays)
        arrays[0] = arrays[0] + float(shift_xy[0])
        arrays[1] = arrays[1] + float(shift_xy[1])
        return tuple(arrays)

    def _current_field_count(self) -> int:
        if not self._field_sampling_is_active():
            return 1
        return self._requested_field_count()

    def _current_field_type(self) -> str:
        return self._normalize_field_type(self.field_type_var.get().strip())

    def _current_spot_view_mode(self) -> str:
        value = getattr(self, "spot_view_mode_var", None)
        if value is None:
            return "Grid"
        mode = value.get().strip()
        if mode in {"Grid", "Absolute", "Centroid"}:
            return mode
        return "Grid"

    @staticmethod
    def _apply_equal_spot_axis_scaling(
        analysis_ax,
        x_values: np.ndarray | Sequence[float],
        y_values: np.ndarray | Sequence[float],
        *,
        minimum_half_span: float = 1e-3,
        pad_fraction: float = 0.08,
    ) -> None:
        """Keep spot-diagram X/Y units physically equal so round spots stay round."""
        x_array = np.asarray(x_values, dtype=float).ravel()
        y_array = np.asarray(y_values, dtype=float).ravel()
        finite = np.isfinite(x_array) & np.isfinite(y_array)
        if np.any(finite):
            x_valid = x_array[finite]
            y_valid = y_array[finite]
            x_min = float(np.min(x_valid))
            x_max = float(np.max(x_valid))
            y_min = float(np.min(y_valid))
            y_max = float(np.max(y_valid))
            center_x = 0.5 * (x_min + x_max)
            center_y = 0.5 * (y_min + y_max)
            half_span = max(
                minimum_half_span,
                0.5 * max(x_max - x_min, y_max - y_min, 1e-12) * (1.0 + 2.0 * pad_fraction),
            )
            analysis_ax.set_xlim(center_x - half_span, center_x + half_span)
            analysis_ax.set_ylim(center_y - half_span, center_y + half_span)
        analysis_ax.set_aspect("equal", adjustable="box")
        analysis_ax.set_box_aspect(1.0)

    def _current_detector_bin_count(
        self,
        sample_count: int,
        *,
        coherent: bool = False,
        detector_model: dict[str, object] | None = None,
    ) -> int:
        sample_count = max(1, int(sample_count or 1))
        auto_min = 24 if coherent else 16
        auto_max = 128 if coherent else 96
        auto_scale = 5 if coherent else 4
        auto_bins = int(np.clip(max(auto_min, round(np.sqrt(sample_count) * auto_scale)), auto_min, auto_max))
        if detector_model:
            detector_bins = str(detector_model.get("bins", "") or "").strip()
            if detector_bins:
                try:
                    return int(np.clip(int(float(detector_bins)), 4, 512))
                except Exception:
                    pass
        text = self._left_mode_text("detector_bins_var", DETECTOR_BINS_DEFAULT).strip()
        if not text or text.lower() in {"auto", "default"}:
            return auto_bins
        try:
            bins = int(float(text))
        except Exception:
            return auto_bins
        return int(np.clip(bins, 4, 512))

    def _current_branch_field_propagation_mm(self) -> float:
        text = self._left_mode_text(
            "branch_field_propagation_mm_var",
            BRANCH_FIELD_PROPAGATION_MM_DEFAULT,
        ).strip()
        try:
            value = float(text)
        except Exception:
            return 0.0
        if not np.isfinite(value):
            return 0.0
        return float(np.clip(value, -1.0e6, 1.0e6))

    def _current_wavefront_style(self) -> str:
        value = getattr(self, "wavefront_style_var", None)
        if value is None:
            return WAVEFRONT_STYLE_DEFAULT
        style = value.get().strip()
        if style in WAVEFRONT_STYLE_VALUES:
            return style
        return WAVEFRONT_STYLE_DEFAULT

    def _current_tolerance_compare_view(self) -> str:
        value = getattr(self, "tolerance_compare_view_var", None)
        if value is None:
            return TOLERANCE_COMPARE_VIEW_DEFAULT
        view = value.get().strip()
        if view in TOLERANCE_COMPARE_VIEW_VALUES:
            return view
        return TOLERANCE_COMPARE_VIEW_DEFAULT

    @staticmethod
    def _convex_hull_area(points: np.ndarray) -> float:
        points = np.asarray(points, dtype=float)
        if points.ndim != 2 or points.shape[0] < 3 or points.shape[1] != 2:
            return 0.0
        sorted_points = sorted((float(x), float(y)) for x, y in points)

        def cross(origin: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
            return (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (b[0] - origin[0])

        lower: list[tuple[float, float]] = []
        for point in sorted_points:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0.0:
                lower.pop()
            lower.append(point)
        upper: list[tuple[float, float]] = []
        for point in reversed(sorted_points):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0.0:
                upper.pop()
            upper.append(point)
        hull = lower[:-1] + upper[:-1]
        if len(hull) < 3:
            return 0.0
        area = 0.0
        for index, point in enumerate(hull):
            next_point = hull[(index + 1) % len(hull)]
            area += point[0] * next_point[1] - next_point[0] * point[1]
        return abs(area) * 0.5

    @classmethod
    def _wavefront_pupil_quality(
        cls,
        x_pupil: np.ndarray,
        y_pupil: np.ndarray,
        *,
        min_samples: int = 8,
    ) -> tuple[bool, str]:
        x = np.asarray(x_pupil, dtype=float).ravel()
        y = np.asarray(y_pupil, dtype=float).ravel()
        finite = np.isfinite(x) & np.isfinite(y)
        x = x[finite]
        y = y[finite]
        if x.size < min_samples:
            return False, f"only {int(x.size)} finite pupil samples"

        x_span = float(np.ptp(x))
        y_span = float(np.ptp(y))
        max_span = max(x_span, y_span)
        if not np.isfinite(max_span) or max_span <= 1e-10:
            return False, "all pupil coordinates collapsed to one point"
        if min(x_span, y_span) <= max(max_span * 1e-4, 1e-10):
            return False, "pupil coordinates are line-like, not a filled 2-D pupil"

        normalized = np.column_stack([(x - float(np.mean(x))) / max_span, (y - float(np.mean(y))) / max_span])
        unique_points = np.unique(np.round(normalized, decimals=7), axis=0)
        if unique_points.shape[0] < min_samples:
            return False, f"only {int(unique_points.shape[0])} unique pupil coordinates"
        try:
            if np.linalg.matrix_rank(normalized, tol=1e-7) < 2:
                return False, "pupil coordinates are rank-deficient"
        except Exception:
            pass

        hull_area = cls._convex_hull_area(unique_points)
        bbox_area = max(float(np.ptp(unique_points[:, 0]) * np.ptp(unique_points[:, 1])), 1e-12)
        if hull_area <= 1e-7 or hull_area / bbox_area < 0.02:
            return False, "pupil samples do not cover a usable 2-D aperture"
        return True, "filled 2-D pupil"

    def _compare_zemax_wavefront_reference(
        self,
        x_pupil: np.ndarray,
        y_pupil: np.ndarray,
        kraken_waves: np.ndarray,
        wavelength_um: float,
    ) -> dict[str, object] | None:
        reference = self.__dict__.get("_zemax_wavefront_reference", None)
        if reference is None:
            return None
        x = np.asarray(x_pupil, dtype=float).ravel()
        y = np.asarray(y_pupil, dtype=float).ravel()
        kraken = np.asarray(kraken_waves, dtype=float).ravel()
        finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(kraken)
        if np.count_nonzero(finite) < 4:
            return {
                "ok": False,
                "reason": "not enough finite KrakenOS wavefront samples for Zemax comparison",
                "reference_file": reference.path,
            }
        x_norm, y_norm = normalized_pupil_coordinates(x, y)
        candidates = (
            ("as exported", reference.values_waves),
            ("flip Y", np.flipud(reference.values_waves)),
            ("flip X", np.fliplr(reference.values_waves)),
            ("flip X/Y", np.flipud(np.fliplr(reference.values_waves))),
            ("transpose", reference.values_waves.T),
        )
        best: dict[str, object] | None = None
        for orientation, values in candidates:
            sampled = sample_wavefront_grid(values, x_norm, y_norm)
            sampled_corrected = self._remove_wavefront_reference_plane(x_norm, y_norm, sampled)
            kraken_corrected = self._remove_wavefront_reference_plane(x_norm, y_norm, kraken)
            comparison_finite = finite & np.isfinite(sampled_corrected) & np.isfinite(kraken_corrected)
            sample_count = int(np.count_nonzero(comparison_finite))
            if sample_count < 4:
                continue
            residual = np.full_like(kraken, np.nan, dtype=float)
            residual[comparison_finite] = kraken_corrected[comparison_finite] - sampled_corrected[comparison_finite]
            residual_values = residual[comparison_finite]
            residual_rms = float(np.sqrt(np.nanmean(residual_values * residual_values)))
            residual_pv = float(np.nanmax(residual_values) - np.nanmin(residual_values))
            candidate = {
                "ok": True,
                "orientation": orientation,
                "sample_count": sample_count,
                "residual_rms_waves": residual_rms,
                "residual_pv_waves": residual_pv,
                "residual_rms_nm": residual_rms * float(wavelength_um) * 1000.0,
                "residual_pv_nm": residual_pv * float(wavelength_um) * 1000.0,
                "wavelength_um": float(wavelength_um),
                "reference_wavelength_um": float(reference.wavelength_um),
                "reference_file": reference.path,
                "reference_shape": reference.shape,
                "reference_samples_waves": sampled_corrected,
                "residual_samples_waves": residual,
            }
            if best is None or residual_rms < float(best.get("residual_rms_waves", np.inf)):
                best = candidate
        if best is None:
            return {
                "ok": False,
                "reason": "Zemax reference could not be sampled on the KrakenOS pupil coordinates",
                "reference_file": reference.path,
                "reference_shape": reference.shape,
            }
        if abs(float(reference.wavelength_um) - float(wavelength_um)) > max(1e-6, abs(float(wavelength_um)) * 1e-4):
            best["wavelength_note"] = (
                f"reference lambda {reference.wavelength_um:.6g} um differs from UI lambda {float(wavelength_um):.6g} um"
            )
        return best

    @staticmethod
    def _annotate_zemax_wavefront_comparison(axis, comparison: dict[str, object] | None) -> None:
        if axis is None or not comparison or not bool(comparison.get("ok", False)):
            return
        axis.text(
            0.69,
            0.165,
            "Zemax residual RMS {rms:.4g} waves ({rms_nm:.4g} nm)".format(
                rms=float(comparison.get("residual_rms_waves", 0.0)),
                rms_nm=float(comparison.get("residual_rms_nm", 0.0)),
            ),
            ha="left",
            va="center",
            fontsize=5.9,
            color="#1d4ed8",
        )

    def _wavefront_pattern_coordinates(self, pupil) -> tuple[np.ndarray, np.ndarray]:
        previous_rad = getattr(pupil, "rad", 0.0)
        previous_theta = getattr(pupil, "theta", 0.0)
        pupil.rad = self._current_pupil_rad()
        pupil.theta = self._current_pupil_theta()
        numpy_state = None
        try:
            if str(getattr(pupil, "Ptype", "")).strip().lower() == "rand":
                numpy_state = np.random.get_state()
                np.random.seed(self._current_source_seed())
            pupil.Pattern()
            return (
                np.asarray(getattr(pupil, "Cordx", []), dtype=float).ravel(),
                np.asarray(getattr(pupil, "Cordy", []), dtype=float).ravel(),
            )
        finally:
            pupil.rad = previous_rad
            pupil.theta = previous_theta
            if numpy_state is not None:
                np.random.set_state(numpy_state)

    def _wavefront_function_grid(
        self,
        x_pupil: np.ndarray,
        y_pupil: np.ndarray,
        phase_waves: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        x = np.asarray(x_pupil, dtype=float).ravel()
        y = np.asarray(y_pupil, dtype=float).ravel()
        values = np.asarray(phase_waves, dtype=float).ravel()
        finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(values)
        x = x[finite]
        y = y[finite]
        values = values[finite]
        if values.size < 4:
            raise RuntimeError("Not enough finite wavefront samples for Wavefront Function plot")
        quality_ok, quality_note = self._wavefront_pupil_quality(x, y)
        if not quality_ok:
            raise RuntimeError(f"Wavefront Function unavailable: {quality_note}")

        x_scale = float(np.nanmax(np.abs(x)))
        y_scale = float(np.nanmax(np.abs(y)))
        if not np.isfinite(x_scale) or x_scale <= 1e-12:
            x_scale = 1.0
        if not np.isfinite(y_scale) or y_scale <= 1e-12:
            y_scale = 1.0
        x_norm = np.clip(x / x_scale, -1.0, 1.0)
        y_norm = np.clip(y / y_scale, -1.0, 1.0)
        grid_count = max(35, min(90, int(np.sqrt(max(values.size, 1)) * 6)))
        grid_axis = np.linspace(-1.0, 1.0, grid_count)
        xx, yy = np.meshgrid(grid_axis, grid_axis)
        pupil_mask = (xx * xx + yy * yy) <= 1.0
        zz = np.full_like(xx, np.nan, dtype=float)
        if np.ptp(x_norm) > 1e-6 and np.ptp(y_norm) > 1e-6 and values.size >= 10:
            for term_count in (min(28, max(10, values.size // 2)), 21, 15, 10, 6):
                if term_count < 4 or term_count > values.size:
                    continue
                try:
                    active_terms = np.ones(int(term_count), dtype=float)
                    coefficients, *_ = Kos.Zernike_Fitting(x_norm, y_norm, values, active_terms)
                    reconstructed = np.asarray(
                        Kos.Wavefront_Zernike_Phase(xx[pupil_mask], yy[pupil_mask], coefficients),
                        dtype=float,
                    ).ravel()
                    if reconstructed.size == int(np.count_nonzero(pupil_mask)) and np.any(np.isfinite(reconstructed)):
                        zz[pupil_mask] = reconstructed
                        break
                except Exception:
                    continue
        try:
            if not np.any(np.isfinite(zz)):
                from matplotlib.tri import LinearTriInterpolator, Triangulation

                triangulation = Triangulation(x_norm, y_norm)
                interpolator = LinearTriInterpolator(triangulation, values)
                zz = np.ma.asarray(interpolator(xx, yy)).filled(np.nan).astype(float)
        except Exception:
            # Keep the plot usable with sparse/degenerate pupil sets by using a
            # nearest-neighbour surface only inside the normalized pupil.
            sample_xy = np.column_stack([x_norm, y_norm])
            grid_xy = np.column_stack([xx[pupil_mask], yy[pupil_mask]])
            if grid_xy.size:
                diff = grid_xy[:, None, :] - sample_xy[None, :, :]
                nearest = np.argmin(np.sum(diff * diff, axis=2), axis=1)
                zz[pupil_mask] = values[nearest]
        zz[~pupil_mask] = np.nan
        if np.count_nonzero(np.isfinite(zz)) < 8:
            raise RuntimeError("Wavefront Function interpolation produced no finite surface")
        return xx, yy, zz

    def _remove_wavefront_reference_plane(
        self,
        x_pupil: np.ndarray,
        y_pupil: np.ndarray,
        values: np.ndarray,
    ) -> np.ndarray:
        x = np.asarray(x_pupil, dtype=float).ravel()
        y = np.asarray(y_pupil, dtype=float).ravel()
        wavefront = np.asarray(values, dtype=float).ravel()
        finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(wavefront)
        corrected = np.full_like(wavefront, np.nan, dtype=float)
        if np.count_nonzero(finite) < 4:
            return wavefront - float(np.nanmean(wavefront))
        design = np.column_stack([np.ones(np.count_nonzero(finite)), x[finite], y[finite]])
        coeffs, *_ = np.linalg.lstsq(design, wavefront[finite], rcond=None)
        corrected[finite] = wavefront[finite] - (coeffs[0] + coeffs[1] * x[finite] + coeffs[2] * y[finite])
        return corrected

    @staticmethod
    def _plot_axes_nan_segments(axis, x_values: np.ndarray, y_values: np.ndarray, **kwargs) -> None:
        x_values = np.asarray(x_values, dtype=float).ravel()
        y_values = np.asarray(y_values, dtype=float).ravel()
        finite = np.isfinite(x_values) & np.isfinite(y_values)
        start: int | None = None
        for index, is_finite in enumerate(finite):
            if is_finite and start is None:
                start = index
            if (not is_finite or index == finite.size - 1) and start is not None:
                end = index + 1 if is_finite and index == finite.size - 1 else index
                if end - start >= 2:
                    axis.plot(x_values[start:end], y_values[start:end], **kwargs)
                start = None

    def _wavefront_projected_axes_coordinates(
        self,
        xx: np.ndarray,
        yy: np.ndarray,
        zz: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        finite_z = zz[np.isfinite(zz)]
        z_scale = float(np.nanpercentile(np.abs(finite_z), 95.0)) if finite_z.size else 1.0
        if not np.isfinite(z_scale) or z_scale <= 1e-12:
            z_scale = float(np.nanmax(np.abs(finite_z))) if finite_z.size else 1.0
        if not np.isfinite(z_scale) or z_scale <= 1e-12:
            z_scale = 1.0
        z_norm = np.clip(zz / z_scale, -1.6, 1.6)

        # Orthographic projection tuned to resemble Zemax's Wavefront Function
        # printout: waterfall slices with strong OPD relief, no 3D axes.
        projected_x = 1.04 * xx + 0.08 * yy
        projected_y = 0.20 * yy + 0.82 * z_norm
        finite = np.isfinite(projected_x) & np.isfinite(projected_y)
        if not np.any(finite):
            raise RuntimeError("Wavefront Function projection produced no finite samples")

        plot_left, plot_right = 0.065, 0.945
        plot_bottom, plot_top = 0.265, 0.925
        x_min = float(np.nanmin(projected_x[finite]))
        x_max = float(np.nanmax(projected_x[finite]))
        y_min = float(np.nanmin(projected_y[finite]))
        y_max = float(np.nanmax(projected_y[finite]))
        x_span = max(x_max - x_min, 1e-12)
        y_span = max(y_max - y_min, 1e-12)
        scale = min((plot_right - plot_left) / x_span, (plot_top - plot_bottom) / y_span)
        x_mid = 0.5 * (x_min + x_max)
        y_mid = 0.5 * (y_min + y_max)
        plot_x_mid = 0.5 * (plot_left + plot_right)
        plot_y_mid = 0.5 * (plot_bottom + plot_top)
        axis_x = plot_x_mid + (projected_x - x_mid) * scale
        axis_y = plot_y_mid + (projected_y - y_mid) * scale
        axis_x[~finite] = np.nan
        axis_y[~finite] = np.nan
        return axis_x, axis_y

    @staticmethod
    def _wavefront_slice_curvature(values: np.ndarray) -> float:
        values = np.asarray(values, dtype=float)
        if values.ndim != 2 or min(values.shape) < 3:
            return 0.0
        curvatures: list[float] = []
        for line in values:
            finite = np.isfinite(line)
            if np.count_nonzero(finite) < 5:
                continue
            segment = line[finite]
            second = np.diff(segment, n=2)
            if second.size:
                curvatures.append(float(np.nanmean(np.abs(second))))
        return float(np.nanmedian(curvatures)) if curvatures else 0.0

    def _orient_wavefront_waterfall_grid(
        self,
        xx: np.ndarray,
        yy: np.ndarray,
        zz: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        row_curvature = self._wavefront_slice_curvature(zz)
        column_curvature = self._wavefront_slice_curvature(zz.T)
        if column_curvature > row_curvature * 1.15:
            return yy.T, xx.T, zz.T
        return xx, yy, zz

    def _plot_wavefront_function_unavailable(
        self,
        analysis_ax,
        *,
        reason: str,
        sample_count: int,
        phase_pv: float,
        phase_rms: float,
        phase_method: str,
        reference_note: str,
    ):
        analysis_ax.clear()
        analysis_ax.set_xlim(0.0, 1.0)
        analysis_ax.set_ylim(0.0, 1.0)
        analysis_ax.set_axis_off()

        border_color = "#111111"
        analysis_ax.add_patch(Rectangle((0.03, 0.03), 0.94, 0.92, fill=False, linewidth=0.85, edgecolor=border_color))
        analysis_ax.plot([0.03, 0.97], [0.235, 0.235], color=border_color, linewidth=0.7)
        analysis_ax.plot([0.03, 0.97], [0.195, 0.195], color=border_color, linewidth=0.7)
        analysis_ax.plot([0.68, 0.68], [0.03, 0.195], color=border_color, linewidth=0.7)
        analysis_ax.text(0.5, 0.214, "WAVEFRONT FUNCTION", ha="center", va="center", fontsize=9.2)

        analysis_ax.text(
            0.5,
            0.74,
            "Wavefront Function unavailable",
            ha="center",
            va="center",
            fontsize=7.8,
            color="#7f1d1d",
        )
        diagnostic = (
            f"KrakenOS returned {sample_count} phase samples, but their pupil coordinates are not a filled "
            f"2-D aperture: {reason}. Use Phase (unwrapped) to inspect the raw samples, or run Wavefront "
            "Function on an image surface with a valid sequential pupil."
        )
        wrapped_lines = textwrap.wrap(diagnostic, width=58)
        for line_index, line in enumerate(wrapped_lines[:7]):
            analysis_ax.text(
                0.5,
                0.64 - line_index * 0.04,
                line,
                ha="center",
                va="center",
                fontsize=5.6,
                color="#1f2937",
            )

        analysis_ax.text(
            0.045,
            0.118,
            f"P-V: {phase_pv:.4g} waves   RMS: {phase_rms:.4g} waves",
            ha="left",
            va="center",
            fontsize=7.2,
        )
        analysis_ax.text(0.045, 0.072, "SURFACE: IMAGE", ha="left", va="center", fontsize=7.2)
        analysis_ax.text(0.69, 0.118, "KRAKENOS UI", ha="left", va="center", fontsize=7.2)
        analysis_ax.text(0.69, 0.072, f"{phase_method}; invalid pupil", ha="left", va="center", fontsize=5.7)
        analysis_ax.set_box_aspect(0.78)
        return analysis_ax

    def _plot_wavefront_function_analysis(
        self,
        analysis_ax,
        x_pupil: np.ndarray,
        y_pupil: np.ndarray,
        phase_waves_centered: np.ndarray,
        *,
        phase_pv: float,
        phase_rms: float,
        phase_method: str,
        reference_note: str,
        pupil_quality: tuple[bool, str] | None = None,
        coordinate_note: str = "Phase pupil coordinates",
    ):
        quality_ok, quality_note = pupil_quality or self._wavefront_pupil_quality(x_pupil, y_pupil)
        if not quality_ok:
            sample_count = int(np.count_nonzero(np.isfinite(x_pupil) & np.isfinite(y_pupil)))
            return self._plot_wavefront_function_unavailable(
                analysis_ax,
                reason=quality_note,
                sample_count=sample_count,
                phase_pv=phase_pv,
                phase_rms=phase_rms,
                phase_method=phase_method,
                reference_note=reference_note,
            )
        xx, yy, zz = self._wavefront_function_grid(
            x_pupil,
            y_pupil,
            phase_waves_centered,
        )
        finite_z = zz[np.isfinite(zz)]
        z_span = float(np.nanmax(finite_z) - np.nanmin(finite_z)) if finite_z.size else 0.0
        max_slice_curvature = max(
            self._wavefront_slice_curvature(zz),
            self._wavefront_slice_curvature(zz.T),
        )
        shape_note = ""
        if z_span > 1e-12 and max_slice_curvature / z_span < 1e-5:
            shape_note = "near-flat/cylindrical samples"
        xx, yy, zz = self._orient_wavefront_waterfall_grid(xx, yy, zz)
        axis_x, axis_y = self._wavefront_projected_axes_coordinates(xx, yy, zz)
        analysis_ax.clear()
        analysis_ax.set_xlim(0.0, 1.0)
        analysis_ax.set_ylim(0.0, 1.0)
        analysis_ax.set_axis_off()

        border_color = "#111111"
        # Outer Zemax-style frame and bottom report/title table.
        analysis_ax.add_patch(Rectangle((0.03, 0.03), 0.94, 0.92, fill=False, linewidth=0.85, edgecolor=border_color))
        analysis_ax.plot([0.03, 0.97], [0.235, 0.235], color=border_color, linewidth=0.7)
        analysis_ax.plot([0.03, 0.97], [0.195, 0.195], color=border_color, linewidth=0.7)
        analysis_ax.plot([0.68, 0.68], [0.03, 0.195], color=border_color, linewidth=0.7)
        analysis_ax.text(0.5, 0.214, "WAVEFRONT FUNCTION", ha="center", va="center", fontsize=9.2)

        row_step = 1 if axis_x.shape[0] <= 58 else 2
        for row_index in range(0, axis_x.shape[0], row_step):
            self._plot_axes_nan_segments(
                analysis_ax,
                axis_x[row_index, :],
                axis_y[row_index, :],
                color="#111827",
                linewidth=0.42,
                alpha=0.96,
            )

        analysis_ax.text(
            0.045,
            0.118,
            f"P-V: {phase_pv:.4g} waves   RMS: {phase_rms:.4g} waves",
            ha="left",
            va="center",
            fontsize=7.2,
        )
        analysis_ax.text(0.045, 0.072, "SURFACE: IMAGE", ha="left", va="center", fontsize=7.2)
        analysis_ax.text(0.69, 0.118, "KRAKENOS UI", ha="left", va="center", fontsize=7.2)
        footer_note = "pattern coords" if coordinate_note != "Phase pupil coordinates" else "piston/tilt removed"
        analysis_ax.text(0.69, 0.072, f"{phase_method}; {footer_note}", ha="left", va="center", fontsize=6.4)
        if shape_note:
            analysis_ax.text(0.045, 0.165, shape_note, ha="left", va="center", fontsize=6.4, color="#7f1d1d")
        analysis_ax.set_box_aspect(0.78)
        return analysis_ax

    def _current_field_value(self) -> float:
        try:
            return float(self.field_value_var.get())
        except ValueError:
            return 0.0

    def _current_field_angle_deg(self) -> float:
        return float(self._field_metrics().get("angle_deg", 0.0))

    def _current_field_height(self) -> float:
        return float(self._field_metrics().get("object_height", 0.0))

    def _field_metrics_for_value(self, field_type: str, raw_value: float) -> dict[str, float]:
        object_distance = self._current_object_distance()
        effl = self._current_effl_estimate()
        image_distance = self._current_image_distance()
        finite_magnification = self._current_finite_paraxial_magnification()

        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            if finite_magnification is not None:
                mag = max(abs(float(finite_magnification)), 1e-9)
                if field_type == "Angle":
                    angle_deg = raw_value
                    object_height = object_distance * np.tan(np.deg2rad(angle_deg))
                elif field_type == "Object Height":
                    object_height = raw_value
                    angle_deg = np.rad2deg(np.arctan2(object_height, object_distance))
                else:
                    object_height = raw_value / mag
                    angle_deg = np.rad2deg(np.arctan2(object_height, object_distance))
                paraxial_image_height = mag * object_height
                real_image_height = paraxial_image_height
            else:
                if field_type == "Angle":
                    angle_deg = raw_value
                    object_height = object_distance * np.tan(np.deg2rad(angle_deg))
                elif field_type == "Object Height":
                    object_height = raw_value
                    angle_deg = np.rad2deg(np.arctan2(object_height, object_distance))
                elif field_type == "Paraxial Image Height":
                    paraxial_image_height = raw_value
                    angle_deg = np.rad2deg(np.arctan2(paraxial_image_height, max(effl, 1e-6)))
                    object_height = object_distance * np.tan(np.deg2rad(angle_deg))
                else:
                    real_image_height = raw_value
                    angle_deg = np.rad2deg(np.arctan2(real_image_height, max(image_distance, 1e-6)))
                    object_height = object_distance * np.tan(np.deg2rad(angle_deg))

                paraxial_image_height = effl * np.tan(np.deg2rad(angle_deg))
                real_image_height = image_distance * np.tan(np.deg2rad(angle_deg))

        if not np.isfinite(angle_deg):
            angle_deg = 0.0
        if not np.isfinite(object_height):
            object_height = 0.0
        if not np.isfinite(paraxial_image_height):
            paraxial_image_height = 0.0
        if not np.isfinite(real_image_height):
            real_image_height = 0.0
        return {
            "angle_deg": float(angle_deg),
            "object_height": float(object_height),
            "paraxial_image_height": float(paraxial_image_height),
            "real_image_height": float(real_image_height),
        }

    def _field_metrics(self) -> dict[str, float]:
        return self._field_metrics_for_value(self._current_field_type(), self._current_field_value())

    def _field_metrics_summary(self) -> dict[str, float]:
        field_type = self._current_field_type()
        sample_values = self._sample_field_values(self._current_field_value())
        if not sample_values:
            sample_values = [self._current_field_value()]
        metrics = [self._field_metrics_for_value(field_type, value) for value in sample_values]
        current_metrics = self._field_metrics()
        max_paraxial = max(abs(float(item.get("paraxial_image_height", 0.0))) for item in metrics) if metrics else 0.0
        max_real = max(abs(float(item.get("real_image_height", 0.0))) for item in metrics) if metrics else 0.0
        traced_image_diameter = self._traced_image_diameter_value()
        field_image_radius = max_paraxial if self._current_object_mode() == "Infinity" else max_real
        required_image_diameter = max(
            2.0 * field_image_radius,
            float(traced_image_diameter) if traced_image_diameter is not None else 0.0,
            1.0,
        )
        return {
            "current_angle_deg": float(current_metrics.get("angle_deg", 0.0)),
            "current_object_height": float(current_metrics.get("object_height", 0.0)),
            "current_paraxial_image_height": float(current_metrics.get("paraxial_image_height", 0.0)),
            "current_real_image_height": float(current_metrics.get("real_image_height", 0.0)),
            "max_paraxial_image_height": float(max_paraxial),
            "max_real_image_height": float(max_real),
            "image_diameter": float(required_image_diameter),
        }

    def _current_effl_estimate(self) -> float:
        try:
            effl, _ppa, _ppp = self._exact_paraxial_cardinals(self._current_wavelength())
            return max(abs(float(effl)), 1e-6)
        except Exception:
            pass
        if self.last_system is not None:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    _a, _b, _c, _d, effl, *_rest = self.last_system.EFL(self._current_wavelength())  # type: ignore[misc]
                return max(abs(float(effl)), 1e-6)
            except Exception:
                pass
        return 100.0

    def _current_image_distance(self) -> float:
        if len(self.rows) >= 2:
            try:
                if any(row.surface == "Mirror" for row in self.rows):
                    distance, _last_source_index, _reference_rows = self._paraxial_total_image_gap(self.rows)
                else:
                    distance = float(self.rows[-2].thickness)
            except Exception:
                distance = float(self.rows[-2].thickness)
            return max(float(distance), 1e-6)
        return 100.0

    def _current_finite_paraxial_magnification(self) -> float | None:
        if self._current_object_mode() != "Finite" or len(self.rows) < 3:
            return None
        try:
            solve_rows = self.rows
            if any(row.surface == "Mirror" for row in self.rows):
                solve_rows, _last_source_index = self._paraxial_reference_rows_for_layout(self.rows)
            _a, _b, _c, _d, _effl, ppa, ppp = self._exact_paraxial_solution_for_rows(solve_rows)
            h1_vertex_z, h2_vertex_z = self._paraxial_vertex_zs(solve_rows)
            h1_z = h1_vertex_z + float(ppa)
            h2_z = h2_vertex_z + float(ppp)
            image_z = sum(float(row.thickness) for row in solve_rows[:-1])
            object_principal = float(h1_z)
            image_principal = float(image_z - h2_z)
            if (
                np.isfinite(object_principal)
                and np.isfinite(image_principal)
                and abs(object_principal) > 1e-9
            ):
                return float(image_principal / object_principal)
        except Exception:
            return None
        return None

    def _schedule_refresh_plot(self, *_args) -> None:
        if not self.winfo_exists():
            return
        if hasattr(self, "_refresh_after_id") and self._refresh_after_id is not None:
            self.after_cancel(self._refresh_after_id)
        self._refresh_after_id = self.after(120, self._refresh_plot_from_controls)

    def _refresh_plot_from_controls(self) -> None:
        self._refresh_after_id = None
        if self.optimization_running:
            return
        self.refresh_plot()

    # _style_embedded_plot removed — now in scene_renderer_2d._style_surface_lines

    def _field_colors(self, count: int) -> list[str]:
        if count <= 1:
            return ["#39FF14"]
        cmap = [
            "#39FF14",
            "#00E5FF",
            "#FF9F1C",
            "#FF4D6D",
            "#9B5DE5",
            "#FFD166",
            "#2EC4B6",
            "#E71D36",
        ]
        return [cmap[i % len(cmap)] for i in range(count)]

    # _build_world_ray_paths, _build_display_ray_paths, _render_display_surface_paths
    # removed — now in scene_builder and scene_renderer_2d

    def _current_folded_surface_geometry(
        self,
        *,
        system=None,
    ) -> tuple[np.ndarray, np.ndarray, float, list[np.ndarray], list[tuple[str, np.ndarray, SurfaceRow, np.ndarray]]] | None:
        trace_state = self._resolved_trace_mode(system=system)
        if not bool(trace_state.get("use_folded")) or not self.rows:
            return None
        return self._compute_folded_layout_geometry()

    @staticmethod
    def _select_optical_solid_output_face(world_faces: list[dict[str, object]]) -> dict[str, object] | None:
        return select_optical_solid_output_face(world_faces)

    def _optical_solid_image_plane_overrides(self, *, system=None) -> dict[int, tuple[np.ndarray, np.ndarray]]:
        overrides: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        if len(self.rows) < 2:
            return overrides
        if system is not None:
            pose_overrides = optical_solid_output_port_pose_overrides(system, self.rows)
        else:
            pose_overrides = build_optical_solid_output_port_pose_overrides(self.rows)
        for row_index, row in enumerate(self.rows):
            if row.surface != "Image":
                continue
            pose = pose_overrides.get(row_index)
            if not isinstance(pose, dict):
                continue
            center_world = np.asarray(pose.get("center", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)
            normal_world = np.asarray(pose.get("normal", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)
            if center_world.size < 3 or normal_world.size < 3:
                continue
            if not (np.all(np.isfinite(center_world[:3])) and np.all(np.isfinite(normal_world[:3]))):
                continue
            x0, y0 = self._project_xy([float(center_world[2])], [float(center_world[1])])
            x1, y1 = self._project_xy(
                [float(center_world[2] + normal_world[2])],
                [float(center_world[1] + normal_world[1])],
            )
            center = np.asarray((float(x0[0]), float(y0[0])), dtype=float)
            along = np.asarray((float(x1[0] - x0[0]), float(y1[0] - y0[0])), dtype=float)
            along_norm = float(np.linalg.norm(along))
            if along_norm <= 1e-12:
                along = np.asarray((0.0, 1.0), dtype=float)
                along_norm = 1.0
            overrides[row_index] = (center, along / max(along_norm, 1e-12))
        return overrides

    def _reference_plane_overrides(self, *, system=None) -> dict[int, tuple[np.ndarray, np.ndarray]]:
        trace_state = self._resolved_trace_mode(system=system)
        if bool(trace_state.get("use_folded")):
            return self._folded_plane_overrides()
        optical_solid_overrides = self._optical_solid_image_plane_overrides(system=system) if bool(trace_state.get("use_nonseq")) else {}
        if system is not None and self._has_off_axis_geometry():
            overrides = self._transform_reference_plane_overrides(system)
            if bool(trace_state.get("use_nonseq")):
                # KrakenOS TRANS_2A can place Object/Image reference rows at
                # internal solver stations for non-sequential scenes (notably
                # STL optical solids). The UI table still defines those
                # reference planes by row semantics instead. Preserve
                # transform-based aperture orientation only, and let Image use
                # the optical-solid output port pose when available.
                for row_index, row in enumerate(self.rows):
                    if row.surface in {"Object", "Image"}:
                        overrides.pop(row_index, None)
                overrides.update(optical_solid_overrides)
            if overrides:
                return overrides
        if optical_solid_overrides:
            return optical_solid_overrides
        return {}

    def _transform_reference_plane_overrides(self, system) -> dict[int, tuple[np.ndarray, np.ndarray]]:
        transforms = self._system_transform_list(system)
        if transforms is None:
            return {}
        overrides: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        for row_index, row in enumerate(self.rows):
            if row.surface not in {"Object", "Image", "Aperture"} or row_index >= len(transforms):
                continue
            try:
                transform = np.asarray(transforms[row_index], dtype=float)
                center_z = float(transform[2, 3])
                center_y = float(transform[1, 3])
                axis_z = float(transform[2, 2])
                axis_y = float(transform[1, 2])
                axis_norm = float(np.hypot(axis_z, axis_y))
                if axis_norm <= 1e-12:
                    continue
                x0, y0 = self._project_xy([center_z], [center_y])
                x1, y1 = self._project_xy([center_z + axis_z / axis_norm], [center_y + axis_y / axis_norm])
                center = np.array([float(x0[0]), float(y0[0])], dtype=float)
                along = np.array([float(x1[0] - x0[0]), float(y1[0] - y0[0])], dtype=float)
                along_norm = float(np.linalg.norm(along))
                if along_norm <= 1e-12:
                    continue
                overrides[row_index] = (center, along / along_norm)
            except Exception:
                continue
        return overrides

    # _reference_plane_display_points, _build_reference_plane_surface_paths
    # removed — now in scene_builder

    @staticmethod
    def _unit_display_vector(vector, fallback: np.ndarray | None = None) -> np.ndarray:
        try:
            arr = np.asarray(vector, dtype=float).ravel()
        except Exception:
            arr = np.empty(0, dtype=float)
        if arr.size >= 2 and np.all(np.isfinite(arr[:2])):
            candidate = np.asarray(arr[:2], dtype=float)
        elif fallback is not None:
            candidate = np.asarray(fallback, dtype=float).ravel()[:2]
        else:
            candidate = np.asarray((1.0, 0.0), dtype=float)
        norm = float(np.linalg.norm(candidate))
        if norm <= 1e-12:
            candidate = np.asarray((1.0, 0.0), dtype=float)
            norm = 1.0
        return candidate / norm

    def _source_display_frame(self) -> tuple[np.ndarray, np.ndarray, float]:
        try:
            source_x, source_y, source_z = self._current_source_origin()
            del source_x
        except Exception:
            source_y, source_z = 0.0, 0.0
        x_vals, y_vals = self._project_xy([source_z], [source_y])
        center = np.asarray((float(x_vals[0]), float(y_vals[0])), dtype=float)
        try:
            _source_l, source_m, source_n = self._current_source_direction()
        except Exception:
            source_m, source_n = 0.0, 1.0
        axis_x, axis_y = self._project_xy([source_n], [source_m])
        axis = np.asarray((float(axis_x[0]), float(axis_y[0])), dtype=float)
        axis = self._unit_display_vector(axis, np.asarray((1.0, 0.0), dtype=float))
        tangent = self._unit_display_vector(np.asarray((-axis[1], axis[0]), dtype=float), np.asarray((0.0, 1.0)))
        source_radius = self._current_source_radius()
        if getattr(self, "rows", None):
            try:
                source_radius = max(source_radius, 0.5 * abs(float(self.rows[0].diameter)))
            except Exception:
                pass
        return center, tangent, float(max(source_radius, 0.0))

    def _branch_output_display_targets(self) -> dict[str, np.ndarray]:
        targets: dict[str, np.ndarray] = {}
        for row in getattr(self, "rows", []) or []:
            advanced = getattr(row, "advanced", {}) or {}
            if not isinstance(advanced, dict):
                continue
            display_settings = advanced.get("Display2D", {})
            if not isinstance(display_settings, dict):
                continue
            raw_targets = display_settings.get("branch_output_targets")
            if not isinstance(raw_targets, dict):
                continue
            for raw_code, raw_point in raw_targets.items():
                code = str(raw_code or "").strip().upper()
                if not code:
                    continue
                try:
                    point = np.asarray(raw_point, dtype=float).ravel()
                except Exception:
                    continue
                if point.size < 2 or not np.all(np.isfinite(point[:2])):
                    continue
                targets[code] = np.asarray(point[:2], dtype=float)
        return targets

    def _branch_output_display_target_frames(self) -> dict[str, tuple[np.ndarray, np.ndarray, float]]:
        source_center, source_tangent, source_radius = self._source_display_frame()
        frames: dict[str, tuple[np.ndarray, np.ndarray, float]] = {}
        for row in getattr(self, "rows", []) or []:
            advanced = getattr(row, "advanced", {}) or {}
            if not isinstance(advanced, dict):
                continue
            display_settings = advanced.get("Display2D", {})
            if not isinstance(display_settings, dict):
                continue
            raw_targets = display_settings.get("branch_output_targets")
            if not isinstance(raw_targets, dict):
                continue
            try:
                row_radius = 0.5 * abs(float(row.diameter))
            except Exception:
                row_radius = 0.0
            raw_tangent = display_settings.get("plane_tangent")
            for raw_code, raw_point in raw_targets.items():
                code = str(raw_code or "").strip().upper()
                if not code:
                    continue
                try:
                    point = np.asarray(raw_point, dtype=float).ravel()
                except Exception:
                    continue
                if point.size < 2 or not np.all(np.isfinite(point[:2])):
                    continue
                target = np.asarray(point[:2], dtype=float)
                if code in {"TT", "RR"}:
                    frames[code] = (target, source_tangent, source_radius)
                    continue
                fallback_axis = target - source_center
                fallback_tangent = np.asarray((-fallback_axis[1], fallback_axis[0]), dtype=float)
                tangent = self._unit_display_vector(raw_tangent, fallback_tangent)
                frames[code] = (target, tangent, max(row_radius, source_radius))
        return frames

    def _branch_output_display_path_overrides(self, rays) -> list[np.ndarray] | None:
        target_frames = self._branch_output_display_target_frames()
        if not target_frames or rays is None:
            return None
        source_center, source_tangent, _source_radius = self._source_display_frame()
        overrides: list[np.ndarray] = []
        used_override = False
        ray_paths = getattr(rays, "CC", ())
        if ray_paths is None:
            return None
        for ray_index, ray in enumerate(ray_paths):
            points_world = np.asarray(ray, dtype=float)
            if points_world.ndim != 2 or points_world.shape[0] < 2 or points_world.shape[1] < 3:
                overrides.append(np.empty((0, 2), dtype=float))
                continue
            x_vals, y_vals = self._project_xy(points_world[:, 2], points_world[:, 1])
            points_2d = np.column_stack((x_vals, y_vals)).astype(float)
            branch_path = str(self._raykeeper_value(rays, "BRANCH_PATH", ray_index, "") or "")
            code = "".join(self._branch_path_selector_sequence(branch_path))[-2:]
            target_frame = target_frames.get(code)
            if target_frame is not None and points_2d.shape[0] >= 2:
                target, target_tangent, max_offset = target_frame
                source_offset = float(np.dot(points_2d[0] - source_center, source_tangent))
                if abs(source_offset) <= 1e-12:
                    raw_offset = float(np.dot(points_2d[-1] - target, target_tangent))
                    if np.isfinite(raw_offset):
                        source_offset = raw_offset
                if np.isfinite(max_offset) and max_offset > 1e-9:
                    source_offset = float(np.clip(source_offset, -max_offset, max_offset))
                points_2d = np.asarray(points_2d, dtype=float).copy()
                points_2d[-1] = target + target_tangent * source_offset
                used_override = True
            overrides.append(points_2d)
        return overrides if used_override else None

    def _build_scene_bundle(self, system, rays, max_radius: float) -> SceneBundle:
        """Build a SceneBundle using the new Phase 3 pipeline."""
        orientation = self._current_display_orientation()
        trace_state = self._resolved_trace_mode(system=system)
        trace_note = str(trace_state.get("note", ""))
        trace_runtime_note = str(getattr(self, "_last_preview_trace_note", "") or "").strip()
        if trace_runtime_note:
            trace_note = f"{trace_note} {trace_runtime_note}".strip()
        folded_geometry = self._current_folded_surface_geometry(system=system)


        # Compute folded ray display overrides (pre-projected paths for folded layouts)
        folded_ray_display_paths = None
        folded_elements = None
        if folded_geometry is not None:
            _point, _direction, _mh, _ep, folded_elements = folded_geometry
            folded_ray_display_paths = self._display_path_overrides_for_current_layout(
                rays, max_radius,
                folded_elements=folded_elements,
                folded_orientation=orientation,
                system=system,
            )
        elif bool(trace_state.get("use_folded")) and orientation == "YZ":
            folded_ray_display_paths = self._display_path_overrides_for_current_layout(
                rays, max_radius,
                system=system,
            )
        if folded_ray_display_paths is None and not bool(trace_state.get("use_nonseq")):
            folded_ray_display_paths = self._branch_output_display_path_overrides(rays)

        field_count = max(
            1,
            int(getattr(self, "_preview_field_bundle_count", self._current_field_count())),
        )

        return build_scene_bundle(
            rows=self.rows,
            system=system,
            rays=rays,
            sources=self._collect_scene_sources(wavelength=self._current_wavelength()),
            display_orientation=orientation,
            show_clipped_rays=self.show_clipped_rays_var.get(),
            field_count=field_count,
            ray_count_per_field=max(1, self._preview_field_ray_count),
            field_colors=self._field_colors(field_count),
            folded_geometry=folded_geometry,
            row_polylines_fn=self._row_layout_polylines,
            surface_meshes_fn=(
                (lambda current_system: self._iter_3d_surface_meshes(current_system, include_reference_surfaces=True))
                if pv is not None
                else None
            ),
            project_fn=self._project_xy,
            reference_plane_overrides=self._reference_plane_overrides(system=system),
            folded_ray_display_paths=folded_ray_display_paths,
            folded_terminal_policy=self._current_folded_detector_policy(),
            trace_mode_requested=str(trace_state.get("requested", "Auto")),
            trace_mode_active=str(trace_state.get("active", "Sequential")),
            trace_mode_note=trace_note,
            target_surface=(
                self._current_nonseq_target_surface_index()
                if bool(trace_state.get("use_nonseq"))
                else None
            ),
            detector_surface_indices=self._scene_detector_surface_indices(trace_state),
            allow_target_plane_contact=True,
            source_row_order=normalize_source_row_order(getattr(self, "layout_scene_row_order", SOURCE_ROW_ORDER_DEFAULT)),
        )

    # _current_surface_scene, _render_current_layout_surfaces removed —
    # now in scene_builder.build_scene_bundle()

    # _build_folded_surface_paths, _surface_style_for_row, _polyline_vertical_extents,
    # _polyline_endpoints, _build_row_surface_groups, _build_curve_group_edge_paths,
    # _build_sequential_lens_edge_paths, _build_sequential_surface_paths
    # removed — now in scene_builder.py
    # _draw_colored_rays removed — now in scene_renderer_2d._draw_rays

    def _current_display_orientation(self) -> str:
        value = getattr(self, "display_orientation_var", None)
        if value is None:
            return "YZ"
        mode = value.get().strip() if hasattr(value, "get") else str(value).strip()
        return normalize_projection_plane(mode)

    def _current_display_slice_axis(self) -> str:
        return "x" if self._current_display_orientation() == "XZ" else "y"

    def _current_projection_display_mode(self) -> str:
        value = getattr(self, "projection_display_mode_var", None)
        if value is None:
            return PROJECTION_MODE_AXIS_FIELD
        mode = value.get() if hasattr(value, "get") else str(value)
        return normalize_projection_display_mode(mode)

    @staticmethod
    def _scene_bundle_launch_sampling_mode(bundle: SceneBundle | None) -> str:
        return scene_bundle_launch_sampling_mode(bundle)

    def _should_filter_projection_axis_fields(self, bundle: SceneBundle | None) -> bool:
        return (
            self._current_projection_display_mode() == PROJECTION_MODE_AXIS_FIELD
            and self._scene_bundle_launch_sampling_mode(bundle) == "world_envelope"
        )

    def _should_filter_projection_slice(self, bundle: SceneBundle | None) -> bool:
        return self._scene_bundle_launch_sampling_mode(bundle) == "world_sections"

    def _projection_display_title(self, orientation: str, bundle: SceneBundle | None = None) -> str:
        plane = normalize_projection_plane(orientation)
        _x_label, _y_label, title = projection_axis_labels(plane)
        if self._scene_bundle_launch_sampling_mode(bundle) != "world_envelope":
            return title
        mode = self._current_projection_display_mode()
        if mode == PROJECTION_MODE_FULL_3D:
            return f"{title} full 3D"
        if plane == "XY":
            return f"{title} full footprint"
        return f"{title} axis field"

    def _project_xy(self, z, y):
        z_arr = np.asarray(z, dtype=float)
        y_arr = np.asarray(y, dtype=float)
        return z_arr, y_arr

    def _apply_display_orientation_to_lines(self, start_index: int = 0) -> None:
        if self._current_display_orientation() == "YZ":
            return
        for line in self.ax.lines[start_index:]:
            xdata = np.asarray(line.get_xdata(orig=False), dtype=float)
            ydata = np.asarray(line.get_ydata(orig=False), dtype=float)
            if xdata.size == 0 or ydata.size == 0:
                continue
            proj_x, proj_y = self._project_xy(xdata, ydata)
            line.set_xdata(proj_x)
            line.set_ydata(proj_y)

    def _has_off_axis_geometry(self) -> bool:
        # AxisMove=1 is the default for sequential surfaces and only takes effect
        # in the presence of a real tilt/decenter, so it is not by itself a sign
        # of off-axis geometry. Mirrors and explicit tilts/decenters are.
        for row in self.rows:
            if row.surface == "Mirror":
                return True
            if any(
                abs(value) > 1e-9
                for value in (row.tilt_x, row.tilt_y, row.tilt_z, row.desp_x, row.desp_y, row.desp_z)
            ):
                return True
        return False

    def _has_beam_splitter_surface(self) -> bool:
        for row in self.rows:
            advanced = row.advanced or {}
            if row.surface == BEAM_SPLITTER_SURFACE or BEAM_SPLITTER_ADVANCED_ATTR in advanced:
                return True
        return False

    def _has_diffuse_scatter_surface(self) -> bool:
        for row in self.rows:
            advanced = row.advanced or {}
            if row.surface == DIFFUSE_OBJECT_SURFACE or DIFFUSE_SCATTER_ADVANCED_ATTR in advanced:
                return True
        return False

    def _has_optical_stl_solid(self) -> bool:
        for row in self.rows:
            advanced = row.advanced or {}
            if isinstance(advanced, dict) and self._scene_graph_value_present(advanced.get("Solid_3d_stl")):
                return True
        return False

    def _can_build_folded_layout(self) -> bool:
        mirror_count = 0
        for row in self.rows:
            if row.surface == "Mirror":
                mirror_count += 1
            elif row.surface not in {"Object", "Image", "Standard", "Aperture"}:
                return False
        return mirror_count >= 1

    @staticmethod
    def _reflect_2d(direction: np.ndarray, line_angle_deg: float) -> np.ndarray:
        theta = np.deg2rad(float(line_angle_deg))
        tangent = np.array([np.cos(theta), np.sin(theta)], dtype=float)
        tangent_norm = np.linalg.norm(tangent)
        if tangent_norm <= 1e-12:
            return direction
        tangent /= tangent_norm
        normal = np.array([-tangent[1], tangent[0]], dtype=float)
        reflected = direction - 2.0 * np.dot(direction, normal) * normal
        norm = np.linalg.norm(reflected)
        if norm <= 1e-12:
            return direction
        return reflected / norm

    @staticmethod
    def _display_mirror_angle_deg(row: SurfaceRow) -> float:
        # KrakenOS TiltX projects with the opposite sign in the Z-Y folded
        # cross-section used by the 2D layout preview.
        return -float(row.tilt_x)

    @staticmethod
    def _mirror_line_angle_deg(
        row: SurfaceRow,
        mirror_tangent: np.ndarray | None = None,
    ) -> float:
        if mirror_tangent is not None:
            tangent = np.asarray(mirror_tangent, dtype=float)
            if tangent.shape == (2,) and np.linalg.norm(tangent) > 1e-12:
                return float(np.rad2deg(np.arctan2(tangent[1], tangent[0])))
        return KrakenLayoutEditor._display_mirror_angle_deg(row)

    @staticmethod
    def _snap_display_direction(direction: np.ndarray, tolerance: float = 0.03) -> np.ndarray:
        d = np.asarray(direction, dtype=float)
        norm = np.linalg.norm(d)
        if norm <= 1e-12:
            return np.array([0.0, 1.0], dtype=float)
        d /= norm
        if abs(d[0]) <= tolerance:
            return np.array([0.0, 1.0 if d[1] >= 0.0 else -1.0], dtype=float)
        if abs(d[1]) <= tolerance:
            return np.array([1.0 if d[0] >= 0.0 else -1.0, 0.0], dtype=float)
        return d

    def _folded_initial_frame(self, orientation: str | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return display-space object point, chief direction, and transverse axis."""
        mode = orientation or self._current_display_orientation()
        point = np.array([0.0, 0.0], dtype=float)
        if mode == "Horizontal":
            direction = np.array([0.0, -1.0], dtype=float)
        else:
            direction = np.array([1.0, 0.0], dtype=float)
        tangent = np.array([-direction[1], direction[0]], dtype=float)
        return point, direction, tangent

    @classmethod
    def _folded_mirror_slant_deg_for_branch(
        cls,
        row: SurfaceRow,
        branch_dir: np.ndarray,
        *,
        orientation: str | None = None,
    ) -> float:
        branch = np.asarray(branch_dir, dtype=float)
        branch /= max(np.linalg.norm(branch), 1e-12)
        branch_angle = float(np.rad2deg(np.arctan2(branch[1], branch[0])))
        if orientation == "Horizontal":
            # Horizontal display is read left-to-right.  Flip the display slant
            # convention so a positive 45 deg mirror sends the folded path to
            # the right instead of back toward negative display X.
            return cls._normalize_mirror_slant_deg(branch_angle + 90.0 - float(row.tilt_x))
        return cls._normalize_mirror_slant_deg(branch_angle - 90.0 + float(row.tilt_x))

    @staticmethod
    def _intersect_ray_with_line(
        origin: np.ndarray,
        direction: np.ndarray,
        center: np.ndarray,
        line_angle_deg: float,
    ) -> tuple[np.ndarray | None, float | None]:
        theta = np.deg2rad(float(line_angle_deg))
        tangent = np.array([np.cos(theta), np.sin(theta)], dtype=float)
        matrix = np.column_stack((direction, -tangent))
        try:
            t_ray, t_line = np.linalg.solve(matrix, center - origin)
        except np.linalg.LinAlgError:
            return None, None
        if t_ray < 0:
            return None, None
        point = origin + direction * t_ray
        return point, float(t_line)

    @staticmethod
    def _glass_index_for_preview(name: str) -> float:
        glass = str(name).strip()
        key = glass.upper()
        if key in _PREVIEW_GLASS_INDEX_CACHE:
            return _PREVIEW_GLASS_INDEX_CACHE[key]
        parts = [part.strip() for part in glass.split(",")]
        compact = parts[0].upper() if parts else key
        if glass in {"", "AIR", "NULL"}:
            return 1.0
        if compact in {"", "AIR", "NULL"}:
            return 1.0
        if compact == "MIRROR":
            return 1.0
        if compact == "NVK" and len(parts) >= 2:
            try:
                value = float(parts[1])
                _PREVIEW_GLASS_INDEX_CACHE[key] = value
                return value
            except Exception:
                pass
        if compact == "___BLANK" and len(parts) >= 4:
            try:
                value = float(parts[3])
                _PREVIEW_GLASS_INDEX_CACHE[key] = value
                return value
            except Exception:
                pass
        alias = {
            "BK7": "H-K9L",
            "K9": "H-K9L",
            "FS": "F_SILICA",
            "SILICA": "F_SILICA",
        }.get(compact, compact)
        catalog_value = _glass_nd_vd_from_setup(alias)
        if catalog_value is not None:
            value = float(catalog_value[0])
            _PREVIEW_GLASS_INDEX_CACHE[key] = value
            return value
        fallback = {
            "BK7": 1.5168,
            "H-K9L": 1.5168,
            "F2": 1.6200,
            "FS": 1.4585,
            "F_SILICA": 1.4585,
            "SILICA": 1.4585,
            "ZF13": 1.78472,
            "H-ZF13": 1.78472,
        }.get(alias, 1.5)
        _PREVIEW_GLASS_INDEX_CACHE[key] = float(fallback)
        return float(fallback)

    @staticmethod
    def _intersect_ray_with_spherical_surface(
        origin: np.ndarray,
        direction: np.ndarray,
        vertex: np.ndarray,
        axis_dir: np.ndarray,
        radius: float,
    ) -> tuple[np.ndarray | None, float | None]:
        if abs(radius) <= 1e-9:
            return None, None
        axis = np.asarray(axis_dir, dtype=float)
        axis /= max(np.linalg.norm(axis), 1e-12)
        tangent = np.array([-axis[1], axis[0]], dtype=float)
        center = vertex + axis * float(radius)
        oc = origin - center
        a = float(np.dot(direction, direction))
        b = 2.0 * float(np.dot(direction, oc))
        c = float(np.dot(oc, oc) - radius * radius)
        disc = b * b - 4.0 * a * c
        if disc < 0.0:
            return None, None
        root = np.sqrt(disc)
        candidates = [(-b - root) / (2.0 * a), (-b + root) / (2.0 * a)]
        candidates = [t for t in candidates if t >= 1e-9]
        if not candidates:
            return None, None
        t_ray = min(candidates)
        point = origin + direction * t_ray
        local = point - vertex
        return point, float(np.dot(local, tangent))

    @staticmethod
    def _intersect_ray_with_plane(
        origin: np.ndarray,
        direction: np.ndarray,
        center: np.ndarray,
        axis_dir: np.ndarray,
    ) -> tuple[np.ndarray | None, float | None]:
        axis = np.asarray(axis_dir, dtype=float)
        axis /= max(np.linalg.norm(axis), 1e-12)
        tangent = np.array([-axis[1], axis[0]], dtype=float)
        angle = np.rad2deg(np.arctan2(tangent[1], tangent[0]))
        return KrakenLayoutEditor._intersect_ray_with_line(origin, direction, center, angle)

    @staticmethod
    def _refract_ray_2d(direction: np.ndarray, normal: np.ndarray, n_before: float, n_after: float) -> np.ndarray:
        d = np.asarray(direction, dtype=float)
        d /= max(np.linalg.norm(d), 1e-12)
        n = np.asarray(normal, dtype=float)
        n /= max(np.linalg.norm(n), 1e-12)
        if np.dot(d, n) > 0.0:
            n = -n
        eta = float(n_before) / float(n_after)
        cos_i = -float(np.dot(n, d))
        k = 1.0 - eta * eta * (1.0 - cos_i * cos_i)
        if k < 0.0:
            reflected = d + 2.0 * cos_i * n
            return reflected / max(np.linalg.norm(reflected), 1e-12)
        refracted = eta * d + (eta * cos_i - np.sqrt(k)) * n
        return refracted / max(np.linalg.norm(refracted), 1e-12)

    def _compute_folded_layout_geometry(self):
        return self._compute_folded_layout_geometry_for_rows(self.rows, orientation=self._current_display_orientation())

    def _compute_folded_layout_geometry_for_rows(
        self,
        rows: list[SurfaceRow],
        *,
        orientation: str | None = None,
    ):
        point, direction, tangent0 = self._folded_initial_frame(orientation)
        max_half = max((max(row.diameter / 2.0, 0.5) for row in rows), default=1.0)
        extent_points = [point.copy()]
        elements: list[tuple[str, np.ndarray, SurfaceRow, np.ndarray]] = []
        if not rows:
            return point, direction, max_half, extent_points, elements
        display_orientation = orientation or self._current_display_orientation()

        current_dir = direction.copy()
        current_point = point + current_dir * max(float(rows[0].thickness), 0.0)
        extent_points.append(current_point.copy())

        for row_index, row in enumerate(rows[1:], start=1):
            travel = max(float(row.thickness), 0.0)
            branch_dir = current_dir / max(np.linalg.norm(current_dir), 1e-12)
            branch_tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
            center_point = current_point + branch_dir * float(row.desp_z) + branch_tangent * float(row.desp_y)
            if row.surface == "Image" and travel > 0.0:
                center_point = center_point + branch_dir * travel
                travel = 0.0

            mirror_tangent = None
            if row.surface == "Mirror":
                slant_angle = self._folded_mirror_slant_deg_for_branch(
                    row,
                    branch_dir,
                    orientation=display_orientation,
                )
                mirror_tangent = np.array(
                    [np.cos(np.deg2rad(slant_angle)), np.sin(np.deg2rad(slant_angle))],
                    dtype=float,
                )

            elements.append((row.surface, center_point.copy(), row, branch_dir.copy(), mirror_tangent, False))
            extent_points.append(center_point.copy())

            if row.surface == "Mirror":
                slant_angle = self._folded_mirror_slant_deg_for_branch(
                    row,
                    branch_dir,
                    orientation=display_orientation,
                )
                current_dir = self._snap_display_direction(self._reflect_2d(branch_dir, slant_angle))
            else:
                current_dir = branch_dir
            current_point = center_point + current_dir * travel
            extent_points.append(current_point.copy())

        _unused = tangent0
        return point, direction, max_half, extent_points, elements

    def _compute_world_folded_layout_geometry(self, *, system=None):
        return self._compute_world_folded_layout_geometry_for_rows(self.rows, system=system)

    def _compute_world_folded_layout_geometry_for_rows(self, rows: list[SurfaceRow], *, system=None):
        _unused = system
        return self._compute_folded_layout_geometry_for_rows(rows, orientation=self._current_display_orientation())

    def _world_folded_geometry_from_transforms(
        self,
        rows: list[SurfaceRow],
        trans: list,
        max_half: float,
    ):
        """Build folded geometry using the system's actual TRANS_2A transforms."""
        point = np.array([0.0, 0.0], dtype=float)
        direction = np.array([1.0, 0.0], dtype=float)
        extent_points: list[np.ndarray] = [point.copy()]
        elements: list[tuple[str, np.ndarray, SurfaceRow, np.ndarray]] = []

        for row_index, row in enumerate(rows):
            t = np.asarray(trans[row_index], dtype=float)
            # TRANS_2A is a 4×4 matrix; translation is in the last column.
            # World-space position in (Z, Y) for Vertical display:
            z_world = float(t[2, 3])
            y_world = float(t[1, 3])
            center = np.array([z_world, y_world], dtype=float)
            extent_points.append(center.copy())
            if row_index == 0:
                # Object row — skip (not in elements list)
                continue

            # Always compute t_prev for row_index >= 1 (used for both
            # last-surface branch_dir and mirror tangent computation).
            t_prev = np.asarray(trans[row_index - 1], dtype=float)

            # Determine the local propagation direction from consecutive
            # surface positions (finite difference).
            if row_index + 1 < len(rows):
                t_next = np.asarray(trans[row_index + 1], dtype=float)
                dz = float(t_next[2, 3]) - z_world
                dy = float(t_next[1, 3]) - y_world
                branch_dir = np.array([dz, dy], dtype=float)
                norm = np.linalg.norm(branch_dir)
                if norm > 1e-9:
                    branch_dir /= norm
                else:
                    branch_dir = direction.copy()
            else:
                # Last surface — use direction from previous surface
                dz = z_world - float(t_prev[2, 3])
                dy = y_world - float(t_prev[1, 3])
                branch_dir = np.array([dz, dy], dtype=float)
                norm = np.linalg.norm(branch_dir)
                branch_dir = branch_dir / norm if norm > 1e-9 else direction.copy()
            branch_dir = self._snap_display_direction(branch_dir)

            mirror_tangent = None
            if row.surface == "Mirror":
                slant_angle = self._mirror_display_slant_deg_for_rows(rows, row_index)
                mirror_tangent = np.array(
                    [np.cos(np.deg2rad(slant_angle)), np.sin(np.deg2rad(slant_angle))],
                    dtype=float,
                )

            elements.append((row.surface, center.copy(), row, branch_dir.copy(), mirror_tangent, False))

        return point, direction, max_half, extent_points, elements

    def _world_folded_preview_ray_paths(self, max_half: float) -> list[np.ndarray]:
        return self._world_folded_preview_ray_paths_for_rows(self.rows, max_half)

    def _world_folded_preview_ray_paths_for_rows(self, rows: list[SurfaceRow], max_half: float) -> list[np.ndarray]:
        if not rows or not any(row.surface == "Mirror" for row in rows):
            return []
        point, direction, _max_half, _extent_points, elements = self._compute_world_folded_layout_geometry_for_rows(rows)
        tangent0 = np.array([-direction[1], direction[0]], dtype=float)
        paths: list[np.ndarray] = []
        field_values = self._sample_field_values(
            self._current_field_angle_deg() if self._current_object_mode() == "Infinity" else self._current_field_height()
        )
        pupil_samples = self._sample_ray_heights(self._resolved_preview_pupil_radius(max_half))
        if self._current_object_mode() == "Infinity":
            for field_value in field_values:
                angle = np.deg2rad(float(field_value))
                d = np.cos(angle) * direction + np.sin(angle) * tangent0
                d /= max(np.linalg.norm(d), 1e-12)
                for pupil_y in pupil_samples:
                    origin = point + tangent0 * float(pupil_y)
                    path, _reached_image = self._trace_folded_preview_ray(origin, d, elements)
                    paths.append(np.asarray(path, dtype=float))
        else:
            object_distance = max(float(rows[0].thickness), 1e-9) if rows else 1.0
            for field_value in field_values:
                origin = point + tangent0 * float(field_value)
                for pupil_y in pupil_samples:
                    target = point + direction * object_distance + tangent0 * float(pupil_y)
                    d = target - origin
                    d /= max(np.linalg.norm(d), 1e-12)
                    path, _reached_image = self._trace_folded_preview_ray(origin, d, elements)
                    paths.append(np.asarray(path, dtype=float))
        return paths

    def _folded_preview_spot_rms_for_rows(self, rows: list[SurfaceRow]) -> float:
        point, direction, max_half, _extent_points, elements = self._compute_world_folded_layout_geometry_for_rows(rows)
        _unused = (point, direction)
        if not elements or elements[-1][0] != "Image":
            raise RuntimeError("Folded best-focus solve requires an Image row after the mirror")
        _surface_type, image_center, image_row, branch_dir, *_rest = elements[-1]
        tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
        tangent /= max(np.linalg.norm(tangent), 1e-12)
        half = max(float(image_row.diameter) / 2.0, 0.5)
        hits: list[float] = []
        for path in self._world_folded_preview_ray_paths_for_rows(rows, max_half):
            if path.shape[0] < 2:
                continue
            hit = np.asarray(path[-1], dtype=float)
            along = float(np.dot(hit - image_center, tangent))
            if abs(along) <= half + 1e-9:
                hits.append(along)
        if not hits:
            raise RuntimeError("No folded image-plane ray hits")
        values = np.asarray(hits, dtype=float)
        centered = values - float(np.mean(values))
        return float(np.sqrt(np.mean(centered * centered)))

    def _folded_plane_overrides(self) -> dict[int, tuple[np.ndarray, np.ndarray]]:
        if not self._can_build_folded_layout() or not self.rows:
            return {}
        point, direction, _max_half, _extent_points, elements = self._compute_folded_layout_geometry()
        overrides: dict[int, tuple[np.ndarray, np.ndarray]] = {0: (point.copy(), direction.copy())}
        for index, (surface_type, center, _row, branch_dir, *_rest) in enumerate(elements, start=1):
            if surface_type in {"Image", "Aperture"}:
                overrides[index] = (np.asarray(center, dtype=float).copy(), np.asarray(branch_dir, dtype=float).copy())
        return overrides

    def _world_folded_plane_overrides(self, *, system=None) -> dict[int, tuple[np.ndarray, np.ndarray]]:
        if not self.rows:
            return {}
        if not any(row.surface == "Mirror" for row in self.rows):
            return {}
        # Reuse the folded geometry (which uses TRANS_2A when available)
        try:
            geom = self._compute_world_folded_layout_geometry(system=system)
        except Exception:
            return {}
        if geom is None:
            return {}
        point, direction, _mh, _ep, elements = geom
        overrides: dict[int, tuple[np.ndarray, np.ndarray]] = {0: (point.copy(), direction.copy())}
        for index, (surface_type, center, _row, branch_dir, *_rest) in enumerate(elements, start=1):
            if surface_type in {"Image", "Aperture"}:
                overrides[index] = (np.asarray(center, dtype=float).copy(), np.asarray(branch_dir, dtype=float).copy())
        return overrides

    def _trace_folded_preview_ray(
        self,
        origin: np.ndarray,
        initial_dir: np.ndarray,
        elements: list,
    ) -> tuple[list[np.ndarray], bool]:
        p = np.asarray(origin, dtype=float).copy()
        path = [p.copy()]
        current_dir = np.asarray(initial_dir, dtype=float).copy()
        current_medium = 1.0
        reached_image = False
        for surface_type, center, row, branch_dir, *_rest in elements:
            if surface_type == "Mirror":
                mirror_tangent = _rest[0] if _rest else None
                reverse_reflection = bool(_rest[1]) if len(_rest) > 1 else False
                mirror_angle = self._mirror_line_angle_deg(row, mirror_tangent)
                hit, along = self._intersect_ray_with_line(p, current_dir, center, mirror_angle)
                if hit is None:
                    break
                half = max(row.diameter / 2.0, 0.5)
                if along is not None and abs(along) > half:
                    break
                if np.linalg.norm(hit - path[-1]) > 1e-9:
                    path.append(hit.copy())
                p = hit
                current_dir = self._reflect_2d(current_dir, mirror_angle)
                if reverse_reflection:
                    current_dir = -current_dir
            elif surface_type == "Standard":
                if abs(float(row.rc)) <= 1e-9:
                    hit, along = self._intersect_ray_with_plane(p, current_dir, center, branch_dir)
                    normal = np.asarray(branch_dir, dtype=float)
                else:
                    hit, along = self._intersect_ray_with_spherical_surface(
                        p, current_dir, center, branch_dir, float(row.rc)
                    )
                    if hit is not None:
                        axis = branch_dir / max(np.linalg.norm(branch_dir), 1e-12)
                        sphere_center = center + axis * float(row.rc)
                        normal = hit - sphere_center
                    else:
                        normal = np.asarray(branch_dir, dtype=float)
                if hit is None:
                    break
                half = max(row.diameter / 2.0, 0.5)
                if along is not None and abs(along) > half:
                    break
                if np.linalg.norm(hit - path[-1]) > 1e-9:
                    path.append(hit.copy())
                next_medium = self._glass_index_for_preview(row.glass)
                current_dir = self._refract_ray_2d(current_dir, normal, current_medium, next_medium)
                current_medium = next_medium
                p = hit
            elif surface_type in {"Image", "Aperture"}:
                tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
                angle = np.rad2deg(np.arctan2(tangent[1], tangent[0]))
                hit, along = self._intersect_ray_with_line(p, current_dir, center, angle)
                if hit is None:
                    break
                half = max(row.diameter / 2.0, 0.5)
                if surface_type != "Image" and along is not None and abs(along) > half:
                    break
                if np.linalg.norm(hit - path[-1]) > 1e-9:
                    path.append(hit.copy())
                p = hit
                if surface_type == "Image":
                    reached_image = True
                    break
        return path, reached_image

    def _preview_ray_start_specs(self, max_half: float, *, system=None) -> list[tuple[np.ndarray, np.ndarray]]:
        point, direction, tangent0 = self._folded_initial_frame("Horizontal")
        starts: list[tuple[np.ndarray, np.ndarray]] = []
        field_values = self._sample_field_values(
            self._current_field_angle_deg() if self._current_object_mode() == "Infinity" else self._current_field_height()
        )
        pupil_samples = self._sample_ray_heights(
            self._resolved_preview_pupil_radius(
                max_half,
                system=system,
            )
        )
        if self._current_object_mode() == "Infinity":
            for field_value in field_values:
                angle = np.deg2rad(float(field_value))
                d = np.cos(angle) * direction + np.sin(angle) * tangent0
                d /= max(np.linalg.norm(d), 1e-12)
                for pupil_y in pupil_samples:
                    origin = point + tangent0 * float(pupil_y)
                    starts.append((origin, d.copy()))
        else:
            object_distance = max(float(self.rows[0].thickness), 1e-9) if self.rows else 1.0
            for field_value in field_values:
                origin = point + tangent0 * float(field_value)
                for pupil_y in pupil_samples:
                    target = point + direction * object_distance + tangent0 * float(pupil_y)
                    d = target - origin
                    d /= max(np.linalg.norm(d), 1e-12)
                    starts.append((origin.copy(), d))
        return starts

    def _world_preview_ray_start_specs(self, max_half: float, *, system=None) -> list[tuple[np.ndarray, np.ndarray]]:
        point, direction, tangent0 = self._folded_initial_frame("Vertical")
        starts: list[tuple[np.ndarray, np.ndarray]] = []
        field_values = self._sample_field_values(
            self._current_field_angle_deg() if self._current_object_mode() == "Infinity" else self._current_field_height()
        )
        pupil_samples = self._sample_ray_heights(
            self._resolved_preview_pupil_radius(
                max_half,
                system=system,
            )
        )
        if self._current_object_mode() == "Infinity":
            for field_value in field_values:
                angle = np.deg2rad(float(field_value))
                d = np.cos(angle) * direction + np.sin(angle) * tangent0
                d /= max(np.linalg.norm(d), 1e-12)
                for pupil_y in pupil_samples:
                    origin = point + tangent0 * float(pupil_y)
                    starts.append((origin, d.copy()))
        else:
            object_distance = max(float(self.rows[0].thickness), 1e-9) if self.rows else 1.0
            for field_value in field_values:
                origin = point + tangent0 * float(field_value)
                for pupil_y in pupil_samples:
                    target = point + direction * object_distance + tangent0 * float(pupil_y)
                    d = target - origin
                    d /= max(np.linalg.norm(d), 1e-12)
                    starts.append((origin.copy(), d))
        return starts

    def _folded_display_ray_paths_for_elements(
        self,
        max_half: float,
        elements,
        *,
        orientation: str | None = None,
        system=None,
    ) -> list[np.ndarray]:
        if elements is None:
            return []
        point, direction, tangent0 = self._folded_initial_frame(orientation)
        source_starts = self._folded_source_display_start_specs(orientation=orientation)
        if source_starts is not None:
            paths = []
            for origin, ray_dir in source_starts:
                path, _reached_image = self._trace_folded_preview_ray(origin, ray_dir, elements)
                paths.append(np.asarray(path, dtype=float))
            return paths
        pupil_radius = self._resolved_preview_pupil_radius(max_half, system=system)
        pupil_samples = self._sample_ray_heights(pupil_radius)
        field_values = self._sample_field_values(
            self._current_field_angle_deg() if self._current_object_mode() == "Infinity" else self._current_field_height()
        )
        paths: list[np.ndarray] = []
        if self._current_object_mode() == "Infinity":
            for field_value in field_values:
                angle = np.deg2rad(float(field_value))
                chief_dir = np.cos(angle) * direction + np.sin(angle) * tangent0
                chief_dir /= max(np.linalg.norm(chief_dir), 1e-12)
                for pupil_y in pupil_samples:
                    origin = point + tangent0 * float(pupil_y)
                    path, _reached_image = self._trace_folded_preview_ray(origin, chief_dir, elements)
                    paths.append(np.asarray(path, dtype=float))
                # Keep parity with the native off-axis preview, which traces a
                # second orthogonal fan.  In this 2-D section that fan projects
                # to the chief ray, so it intentionally overlays the center path.
                for _pupil_x in pupil_samples:
                    path, _reached_image = self._trace_folded_preview_ray(point.copy(), chief_dir, elements)
                    paths.append(np.asarray(path, dtype=float))
        else:
            object_distance = max(float(self.rows[0].thickness), 1e-9) if self.rows else 1.0
            for field_value in field_values:
                origin_base = point + tangent0 * float(field_value)
                for pupil_y in pupil_samples:
                    target = point + direction * object_distance + tangent0 * float(pupil_y)
                    ray_dir = target - origin_base
                    ray_dir /= max(np.linalg.norm(ray_dir), 1e-12)
                    path, _reached_image = self._trace_folded_preview_ray(origin_base, ray_dir, elements)
                    paths.append(np.asarray(path, dtype=float))
                for _pupil_x in pupil_samples:
                    target = point + direction * object_distance
                    ray_dir = target - origin_base
                    ray_dir /= max(np.linalg.norm(ray_dir), 1e-12)
                    path, _reached_image = self._trace_folded_preview_ray(origin_base, ray_dir, elements)
                    paths.append(np.asarray(path, dtype=float))
        return paths

    def _build_element_display_paths(
        self,
        rays,
        elements,
        starts: list[tuple[np.ndarray, np.ndarray]],
    ) -> list[np.ndarray]:
        if elements is None:
            return []
        element_map = {index + 1: item for index, item in enumerate(elements)}
        paths: list[np.ndarray] = []
        for ray_index, surface_ids_raw in enumerate(rays.SURFACE):
            if ray_index >= len(starts):
                break
            origin, current_dir = starts[ray_index]
            current_point = np.asarray(origin, dtype=float).copy()
            current_medium = 1.0
            path = [current_point.copy()]
            surface_ids = [int(v) for v in np.asarray(surface_ids_raw, dtype=int).ravel().tolist()]
            last_id: int | None = None
            for surface_index in surface_ids:
                if surface_index == last_id:
                    continue
                element = element_map.get(surface_index)
                if element is None:
                    continue
                surface_type, center, row, branch_dir, *_rest = element
                success = False
                if surface_type == "Mirror":
                    mirror_tangent = _rest[0] if _rest else None
                    reverse_reflection = bool(_rest[1]) if len(_rest) > 1 else False
                    mirror_angle = self._mirror_line_angle_deg(row, mirror_tangent)
                    hit, along = self._intersect_ray_with_line(current_point, current_dir, center, mirror_angle)
                    if hit is None:
                        break
                    half = max(row.diameter / 2.0, 0.5)
                    if along is not None and abs(along) > half:
                        break
                    if np.linalg.norm(hit - path[-1]) > 1e-9:
                        path.append(hit.copy())
                    current_point = hit
                    current_dir = self._reflect_2d(current_dir, mirror_angle)
                    if reverse_reflection:
                        current_dir = -current_dir
                    success = True
                elif surface_type == "Standard":
                    if abs(float(row.rc)) <= 1e-9:
                        hit, along = self._intersect_ray_with_plane(current_point, current_dir, center, branch_dir)
                        normal = np.asarray(branch_dir, dtype=float)
                    else:
                        hit, along = self._intersect_ray_with_spherical_surface(
                            current_point, current_dir, center, branch_dir, float(row.rc)
                        )
                        if hit is not None:
                            axis = branch_dir / max(np.linalg.norm(branch_dir), 1e-12)
                            sphere_center = center + axis * float(row.rc)
                            normal = hit - sphere_center
                        else:
                            normal = np.asarray(branch_dir, dtype=float)
                    if hit is None:
                        break
                    half = max(row.diameter / 2.0, 0.5)
                    if along is not None and abs(along) > half:
                        break
                    if np.linalg.norm(hit - path[-1]) > 1e-9:
                        path.append(hit.copy())
                    next_medium = self._glass_index_for_preview(row.glass)
                    current_dir = self._refract_ray_2d(current_dir, normal, current_medium, next_medium)
                    current_medium = next_medium
                    current_point = hit
                    success = True
                elif surface_type in {"Image", "Aperture"}:
                    tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
                    angle = np.rad2deg(np.arctan2(tangent[1], tangent[0]))
                    hit, along = self._intersect_ray_with_line(current_point, current_dir, center, angle)
                    if hit is None:
                        break
                    half = max(row.diameter / 2.0, 0.5)
                    if surface_type != "Image" and along is not None and abs(along) > half:
                        break
                    if np.linalg.norm(hit - path[-1]) > 1e-9:
                        path.append(hit.copy())
                    current_point = hit
                    success = True
                    if surface_type == "Image":
                        last_id = surface_index
                        break
                if not success:
                    break
                last_id = surface_index
            if last_id is not None and 0 < last_id < len(elements):
                trailing = list(range(last_id + 1, len(elements) + 1))
                if trailing and all(elements[idx - 1][0] in {"Image", "Aperture"} for idx in trailing):
                    for surface_index in trailing:
                        surface_type, center, row, branch_dir, *_rest = element_map[surface_index]
                        tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
                        angle = np.rad2deg(np.arctan2(tangent[1], tangent[0]))
                        hit, along = self._intersect_ray_with_line(current_point, current_dir, center, angle)
                        if hit is None:
                            break
                        half = max(row.diameter / 2.0, 0.5)
                        if surface_type != "Image" and along is not None and abs(along) > half:
                            break
                        if np.linalg.norm(hit - path[-1]) > 1e-9:
                            path.append(hit.copy())
                        current_point = hit
                        if surface_type == "Image":
                            break
            paths.append(np.asarray(path, dtype=float))
        return paths

    def _folded_source_display_start_specs(
        self,
        *,
        orientation: str | None = None,
    ) -> list[tuple[np.ndarray, np.ndarray]] | None:
        if self._current_source_model() == SOURCE_MODEL_DEFAULT:
            return None
        try:
            source_bundle = self._build_random_source_bundle()
        except Exception as exc:
            self.append_debug(f"Folded source display fallback: {_short_error_message(exc)}")
            return None
        if source_bundle is None:
            return None
        _x_values, y_values, z_values, _l_values, m_values, n_values = (
            np.asarray(values, dtype=float).reshape(-1) for values in source_bundle
        )
        count = min(len(y_values), len(z_values), len(m_values), len(n_values))
        if count <= 0:
            return None
        mode = orientation or self._current_display_orientation()
        starts: list[tuple[np.ndarray, np.ndarray]] = []
        for index in range(count):
            if mode == "Horizontal":
                origin = np.array([-float(y_values[index]), -float(z_values[index])], dtype=float)
                direction = np.array([-float(m_values[index]), -float(n_values[index])], dtype=float)
            else:
                origin = np.array([float(z_values[index]), float(y_values[index])], dtype=float)
                direction = np.array([float(n_values[index]), float(m_values[index])], dtype=float)
            norm = float(np.linalg.norm(direction))
            if norm <= 1e-12:
                continue
            starts.append((origin, direction / norm))
        return starts or None

    def _build_mapped_display_paths_from_actual_hits(
        self,
        rays,
        elements,
        starts: list[tuple[np.ndarray, np.ndarray]],
        system,
    ) -> list[np.ndarray]:
        trans = getattr(system, "TRANS_2A", None)
        if trans is None:
            return self._build_element_display_paths(rays, elements, starts)
        element_map = {index + 1: item for index, item in enumerate(elements)}
        paths: list[np.ndarray] = []
        for ray_index, surface_ids_raw in enumerate(rays.SURFACE):
            if ray_index >= len(starts):
                break
            path = [np.asarray(starts[ray_index][0], dtype=float).copy()]
            previous_actual = path[-1].copy()
            surface_ids = [int(v) for v in np.asarray(surface_ids_raw, dtype=int).ravel().tolist()]
            hit_points = np.asarray(rays.CC[ray_index], dtype=float)
            if hit_points.ndim != 2 or hit_points.shape[0] < 2:
                paths.append(np.asarray(path, dtype=float))
                continue
            for surface_index, hit_world in zip(surface_ids, hit_points[1:]):
                element = element_map.get(surface_index)
                if element is None:
                    continue
                surface_type, center, _row, branch_dir, *_rest = element
                hit_actual = np.array([float(hit_world[2]), float(hit_world[1])], dtype=float)
                hit_display = hit_actual.copy()
                if surface_type in {"Mirror", "Image", "Aperture"} and surface_index < len(trans):
                    t = np.asarray(trans[surface_index], dtype=float)
                    actual_center = np.array([float(t[2, 3]), float(t[1, 3])], dtype=float)
                    actual_tangent = np.array([float(t[2, 1]), float(t[1, 1])], dtype=float)
                    actual_norm = np.linalg.norm(actual_tangent)
                    if actual_norm > 1e-12:
                        actual_tangent /= actual_norm
                        if surface_type == "Mirror" and _rest:
                            display_tangent = np.asarray(_rest[0], dtype=float).copy()
                        else:
                            display_tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
                        display_norm = np.linalg.norm(display_tangent)
                        if display_norm > 1e-12:
                            display_tangent /= display_norm
                            if np.dot(actual_tangent, display_tangent) < 0.0:
                                display_tangent = -display_tangent
                            along = float(np.dot(hit_display - actual_center, actual_tangent))
                            candidate_a = np.asarray(center, dtype=float) + display_tangent * along
                            candidate_b = np.asarray(center, dtype=float) - display_tangent * along
                            actual_dir = hit_actual - previous_actual
                            actual_dir_norm = np.linalg.norm(actual_dir)
                            if actual_dir_norm > 1e-12:
                                actual_dir /= actual_dir_norm
                                candidate_dirs = []
                                for candidate in (candidate_a, candidate_b):
                                    disp_dir = candidate - path[-1]
                                    disp_norm = np.linalg.norm(disp_dir)
                                    if disp_norm > 1e-12:
                                        disp_dir /= disp_norm
                                        candidate_dirs.append((float(np.dot(disp_dir, actual_dir)), candidate))
                                    else:
                                        candidate_dirs.append((-np.inf, candidate))
                                hit_display = max(candidate_dirs, key=lambda item: item[0])[1]
                            else:
                                hit_display = candidate_a
                if np.linalg.norm(hit_display - path[-1]) > 1e-9:
                    path.append(hit_display)
                previous_actual = hit_actual
                if surface_type == "Image":
                    break
            paths.append(np.asarray(path, dtype=float))
        return paths

    def _project_world_ray_paths_for_display(self, rays) -> list[np.ndarray]:
        paths: list[np.ndarray] = []
        for ray in getattr(rays, "CC", ()):
            pts = np.asarray(ray, dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 2:
                paths.append(np.empty((0, 2), dtype=float))
                continue
            proj_x, proj_y = self._project_xy(pts[:, 2], pts[:, 1])
            paths.append(np.column_stack((proj_x, proj_y)))
        return paths

    def _display_path_overrides_for_current_layout(
        self,
        rays,
        max_half: float,
        *,
        folded_elements=None,
        folded_orientation: str | None = None,
        system=None,
    ) -> list[np.ndarray] | None:
        if folded_elements is not None:
            orientation = folded_orientation or self._current_display_orientation()
            return self._folded_display_ray_paths_for_elements(
                max_half,
                folded_elements,
                orientation=orientation,
                system=system,
            )
        if self._can_build_folded_layout():
            geom = self._compute_world_folded_layout_geometry(system=system)
            if geom is not None:
                return self._folded_display_ray_paths_for_elements(
                    max_half,
                    geom[-1],
                    orientation=self._current_display_orientation(),
                    system=system,
                )
        return None

    @staticmethod
    def _galvo_scan_overlay_values(row: SurfaceRow) -> list[float]:
        advanced = getattr(row, "advanced", {}) or {}
        if not isinstance(advanced, dict):
            return []
        display_settings = advanced.get("Display2D", {})
        if not isinstance(display_settings, dict):
            return []
        raw_values = display_settings.get(GALVO_SCAN_OVERLAY_KEY)
        if raw_values in (None, "", "None"):
            return []
        try:
            if isinstance(raw_values, str):
                return _parse_float_sequence_text(raw_values)
            if isinstance(raw_values, (int, float)):
                return [float(raw_values)]
            return _dedupe_float_values([float(value) for value in raw_values])
        except Exception:
            return []

    def _pose_tolerance_entries(self) -> list[dict[str, object]]:
        entries: list[dict[str, object]] = []
        for row_index, row in enumerate(self.rows):
            if row.surface == "Object":
                continue
            enabled_fields = self._surface_type_enabled_fields(row.surface)
            for field in POSE_TOLERANCE_FIELDS:
                if field not in enabled_fields:
                    continue
                # Mirror TiltX keeps the dedicated galvo/folded-scan overlay.
                if field == "tilt_x" and row.surface == "Mirror":
                    continue
                values = self._pose_tolerance_overlay_values(row, field)
                if len(values) <= 1:
                    continue
                entries.append(
                    {
                        "row_index": int(row_index),
                        "field": field,
                        "values": values[:POSE_TOLERANCE_MAX_VARIANTS],
                        "nominal": float(getattr(row, field)),
                    }
                )
        return entries

    def _pose_tolerance_variant_assignments(self) -> list[list[tuple[int, str, float]]]:
        entries = self._pose_tolerance_entries()
        if not entries:
            return []
        lengths = [len(entry["values"]) for entry in entries]
        if len(set(lengths)) == 1:
            variants = [
                [
                    (int(entry["row_index"]), str(entry["field"]), float(entry["values"][value_index]))
                    for entry in entries
                ]
                for value_index in range(lengths[0])
            ]
        else:
            pools = [
                [
                    (int(entry["row_index"]), str(entry["field"]), float(value))
                    for value in entry["values"]
                ]
                for entry in entries
            ]
            variants = [list(combo) for combo in product(*pools)]
            if len(variants) > POSE_TOLERANCE_MAX_VARIANTS:
                self.append_debug(
                    f"Pose tolerance overlay truncated from {len(variants)} to {POSE_TOLERANCE_MAX_VARIANTS} variants."
                )
                variants = variants[:POSE_TOLERANCE_MAX_VARIANTS]

        nominal_by_key = {
            (int(entry["row_index"]), str(entry["field"])): float(entry["nominal"])
            for entry in entries
        }
        filtered: list[list[tuple[int, str, float]]] = []
        for variant in variants:
            if any(abs(float(value) - nominal_by_key.get((row_index, field), float("nan"))) > 1e-12 for row_index, field, value in variant):
                filtered.append(variant)
        return filtered[:POSE_TOLERANCE_MAX_VARIANTS]

    def _rows_with_pose_tolerance_assignment(self, assignment: list[tuple[int, str, float]]) -> list[SurfaceRow]:
        rows = [SurfaceRow(**asdict(row)) for row in self.rows]
        for row_index, field, value in assignment:
            if 0 <= row_index < len(rows) and field in POSE_TOLERANCE_FIELDS:
                setattr(rows[row_index], field, float(value))
        return rows

    @staticmethod
    def _pose_tolerance_assignment_label(assignment: list[tuple[int, str, float]]) -> str:
        labels = []
        for row_index, field, value in assignment:
            labels.append(f"S{row_index} {COLUMN_LABELS.get(field, field).split()[0]}={float(value):g}")
        return "; ".join(labels)

    def _project_pose_tolerance_rows(
        self,
        rows: list[SurfaceRow],
        *,
        max_radius: float,
        wavelength: float,
        orientation: str,
    ) -> ProjectedScene2D:
        original_rows = self.rows
        original_note = str(getattr(self, "_last_preview_trace_note", "") or "")
        original_backend = str(getattr(self, "_last_preview_trace_backend", "") or "")
        original_ray_count = int(getattr(self, "_preview_field_ray_count", 1) or 1)
        original_field_count = int(getattr(self, "_preview_field_bundle_count", 1) or 1)
        try:
            self.rows = rows
            system = _build_system_from_specs(self._serializable_specs_for_rows(rows), build=1)
            rays = Kos.raykeeper(system)
            self._trace_preview_rays(
                system,
                rays,
                wavelength,
                max_radius,
                allow_full_pupil=False,
                sampling_mode="display_slice",
            )
            bundle = self._build_scene_bundle(system, rays, max_radius)
            return project_scene_bundle(
                bundle,
                orientation,
                filter_arm_view=self._filter_projected_scene_for_arm_view,
            )
        finally:
            self.rows = original_rows
            self._last_preview_trace_note = original_note
            self._last_preview_trace_backend = original_backend
            self._preview_field_ray_count = original_ray_count
            self._preview_field_bundle_count = original_field_count

    def _draw_projected_pose_tolerance_overlay(
        self,
        projected: ProjectedScene2D,
        *,
        assignment: list[tuple[int, str, float]],
        color: str,
        alpha: float,
        linewidth: float,
    ) -> BoundsRect:
        bounds_points: list[np.ndarray] = []
        affected_rows = {row_index for row_index, _field, _value in assignment}
        for ray in projected.rays:
            if not self.show_clipped_rays_var.get() and not projected_ray_hits_detector(ray):
                continue
            pts = np.asarray(ray.points_2d, dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 2:
                continue
            bounds_points.append(pts)
            self.ax.plot(
                pts[:, 0],
                pts[:, 1],
                color=color,
                linewidth=linewidth,
                alpha=alpha,
                linestyle=(0, (3, 2)),
                zorder=26.0,
            )
        for curve in projected.curves:
            if int(curve.row_index) not in affected_rows:
                continue
            pts = np.asarray(curve.points_2d, dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 2:
                continue
            bounds_points.append(pts)
            self.ax.plot(
                pts[:, 0],
                pts[:, 1],
                color=color,
                linewidth=max(linewidth * 1.35, 0.9),
                alpha=min(alpha + 0.18, 0.9),
                linestyle=(0, (5, 2)),
                zorder=52.0,
            )
        return BoundsRect.from_points(bounds_points)

    def _draw_pose_tolerance_overlay(self, max_radius: float, *, wavelength: float) -> BoundsRect:
        assignments = self._pose_tolerance_variant_assignments()
        if not assignments:
            return BoundsRect()
        orientation = self._current_display_orientation()
        palette = ("#f97316", "#0ea5e9", "#e11d48", "#8b5cf6", "#14b8a6", "#84cc16")
        ray_count_hint = max(1, int(getattr(self, "_preview_field_ray_count", 5) or 5))
        linewidth = 0.95 if ray_count_hint <= 9 else 0.58
        alpha = 0.52 if ray_count_hint <= 9 else 0.34
        bounds: list[BoundsRect] = []
        for variant_index, assignment in enumerate(assignments):
            rows = self._rows_with_pose_tolerance_assignment(assignment)
            try:
                projected = self._project_pose_tolerance_rows(
                    rows,
                    max_radius=max_radius,
                    wavelength=wavelength,
                    orientation=orientation,
                )
            except Exception as exc:
                self.append_debug(
                    f"Pose tolerance overlay failed for {self._pose_tolerance_assignment_label(assignment)}: {_short_error_message(exc)}"
                )
                continue
            color = palette[variant_index % len(palette)]
            bounds.append(
                self._draw_projected_pose_tolerance_overlay(
                    projected,
                    assignment=assignment,
                    color=color,
                    alpha=alpha,
                    linewidth=linewidth,
                )
            )
        if bounds:
            self.status_var.set(f"Pose tolerance overlay: {len(bounds)} variant ray trace(s).")
        return self._combined_plot_bounds(*bounds)

    @staticmethod
    def _combined_plot_bounds(*bounds_items: BoundsRect | None) -> BoundsRect:
        points: list[np.ndarray] = []
        for bounds in bounds_items:
            if bounds is None or bounds.is_empty:
                continue
            points.append(
                np.asarray(
                    [
                        [float(bounds.x_min), float(bounds.y_min)],
                        [float(bounds.x_max), float(bounds.y_max)],
                    ],
                    dtype=float,
                )
            )
        return BoundsRect.from_points(points)

    def _folded_scan_overlay_plans(self, max_half: float, *, system=None) -> list[dict[str, object]]:
        if not self.rows or not self._can_build_folded_layout():
            return []
        scan_rows = [
            (index, self._galvo_scan_overlay_values(row))
            for index, row in enumerate(self.rows)
            if row.surface == "Mirror"
        ]
        scan_rows = [(index, values) for index, values in scan_rows if values]
        if not scan_rows:
            return []
        orientation = self._current_display_orientation()
        palette = ("#f97316", "#0ea5e9", "#e11d48", "#8b5cf6", "#14b8a6")
        ray_count_hint = max(1, int(getattr(self, "_preview_field_ray_count", 5) or 5))
        plans: list[dict[str, object]] = []
        try:
            # A galvo scan changes the reflected ray direction, not the fixed
            # downstream F-theta lens and detector geometry.
            _point, _direction, _mh, _extent_points, fixed_elements = self._compute_folded_layout_geometry_for_rows(
                self.rows,
                orientation=orientation,
            )
        except Exception as exc:
            self.append_debug(f"Galvo scan overlay geometry failed: {_short_error_message(exc)}")
            return []
        for mirror_index, values in scan_rows:
            display_values = self._mirror_overlay_display_slants_for_rows(self.rows, mirror_index)
            nominal_display_tilt = self._mirror_display_slant_deg_for_rows(self.rows, mirror_index)
            if not (0 < mirror_index <= len(fixed_elements)):
                continue
            mirror_surface, mirror_center, mirror_row, _incoming_dir, *_mirror_rest = fixed_elements[mirror_index - 1]
            if mirror_surface != "Mirror":
                continue
            downstream_elements = fixed_elements[mirror_index:]
            upstream_elements = fixed_elements[:mirror_index]
            pupil_radius = self._resolved_preview_pupil_radius(max_half, system=system)
            pupil_samples = self._sample_ray_heights(pupil_radius)
            source_starts = self._folded_source_display_start_specs(orientation=orientation)
            if source_starts is None:
                point, direction, tangent0 = self._folded_initial_frame(orientation)
                field_values = self._sample_field_values(
                    self._current_field_angle_deg()
                    if self._current_object_mode() == "Infinity"
                    else self._current_field_height()
                )
                source_starts = folded_fallback_source_start_specs(
                    point,
                    direction,
                    tangent0,
                    field_values,
                    pupil_samples,
                    object_mode=self._current_object_mode(),
                    object_distance=max(float(self.rows[0].thickness), 1e-9) if self.rows else 1.0,
                )
            nominal_paths = []
            for start_point, start_dir in source_starts:
                nominal_path, _reached = self._trace_folded_preview_ray(start_point, start_dir, upstream_elements)
                nominal_paths.append(nominal_path)
            incoming_states = folded_scan_incoming_states(nominal_paths)
            for value_index, tilt_x in enumerate(values[:25]):
                display_tilt = display_values[value_index] if value_index < len(display_values) else float(tilt_x)
                field_theta = 2.0 * (float(display_tilt) - float(nominal_display_tilt))
                paths = []
                try:
                    for previous, ray_dir in incoming_states:
                        hit, along = self._intersect_ray_with_line(
                            previous,
                            ray_dir,
                            np.asarray(mirror_center, dtype=float),
                            float(display_tilt),
                        )
                        if hit is None:
                            continue
                        half = max(float(mirror_row.diameter) / 2.0, 0.5)
                        if along is not None and abs(along) > half:
                            continue
                        scan_dir = self._reflect_2d(ray_dir, float(display_tilt))
                        path, _reached_image = self._trace_folded_preview_ray(hit, scan_dir, downstream_elements)
                        paths.append(np.asarray(path, dtype=float))
                except Exception as exc:
                    self.append_debug(f"Galvo scan overlay failed for TiltX={tilt_x:g}: {_short_error_message(exc)}")
                    continue
                color = palette[value_index % len(palette)]
                plan = folded_scan_overlay_plan(
                    paths,
                    field_theta=float(field_theta),
                    display_tilt=float(display_tilt),
                    mirror_center=mirror_center,
                    mirror_diameter=float(mirror_row.diameter),
                    color=color,
                    ray_count_hint=ray_count_hint,
                )
                enriched_plan = dict(plan)
                enriched_plan.update(
                    {
                        "mirror_row_index": int(mirror_index),
                        "tilt_x": float(tilt_x),
                        "display_tilt": float(display_tilt),
                        "field_theta": float(field_theta),
                        "orientation": orientation,
                    }
                )
                plans.append(enriched_plan)
        return plans

    def _draw_folded_scan_overlay(self, max_half: float, *, system=None) -> BoundsRect:
        plans = self._folded_scan_overlay_plans(max_half, system=system)
        bounds_points: list[np.ndarray] = []
        for plan in plans:
            color = str(plan.get("color", "#f97316") or "#f97316")
            bounds_points.extend(np.asarray(points, dtype=float) for points in list(plan.get("bounds_points", []) or []))
            for path in list(plan.get("paths", []) or []):
                pts = np.asarray(path, dtype=float)
                self.ax.plot(
                    pts[:, 0],
                    pts[:, 1],
                    color=color,
                    linewidth=float(plan.get("linewidth", 1.1) or 1.1),
                    alpha=float(plan.get("alpha", 0.92) or 0.92),
                    zorder=24.0,
                )
            line = plan.get("mirror_line")
            if line is not None:
                line = np.asarray(line, dtype=float)
                self.ax.plot(
                    line[:, 0],
                    line[:, 1],
                    color=color,
                    linewidth=1.5,
                    linestyle=(0, (4, 2)),
                    alpha=0.78,
                    zorder=58.0,
                )
            label_point = plan.get("label_point")
            if label_point is not None:
                label_point = np.asarray(label_point, dtype=float)
                self.ax.text(
                    float(label_point[0]),
                    float(label_point[1]),
                    str(plan.get("label", f"theta={float(plan.get('field_theta', 0.0)):g} deg")),
                    fontsize=7,
                    color=color,
                    ha="center",
                    va="center",
                    zorder=62.0,
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.72, "pad": 0.25},
                )
        return BoundsRect.from_points(bounds_points)

    # _build_current_display_ray_paths removed — now in scene_builder + scene_projector
    # _draw_reference_plane_labels removed — now in scene_builder + scene_renderer_2d

    def _clear_cardinal_marker_artists(self) -> None:
        for artist in self._cardinal_marker_artists:
            try:
                artist.remove()
            except Exception:
                pass
        self._cardinal_marker_artists.clear()

    def _on_toggle_cardinal_markers(self) -> None:
        self._clear_cardinal_marker_artists()
        if not self.show_cardinals_var.get():
            self.canvas.draw_idle()
            self.status_var.set("PP / EP / XP hidden")
            return

        if self._last_optics_info is None and self.last_system is not None and self.last_rays is not None:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    self._last_optics_info = self._collect_optics_info(
                        self.last_system,
                        self.last_rays,
                        self._current_wavelength(),
                    )
            except Exception:
                self._last_optics_info = None

        if self._last_optics_info is None:
            self.canvas.draw_idle()
            self.status_var.set("PP / EP / XP unavailable for current view")
            return

        self._draw_optics_markers(self._last_optics_info)
        self.canvas.draw_idle()
        self.status_var.set("PP / EP / XP updated")
        self._autosave_plot()

    def _current_show_path_labels(self) -> bool:
        var = getattr(self, "show_path_labels_var", None)
        if var is not None:
            try:
                return bool(var.get())
            except Exception:
                pass
        return bool(getattr(self, "show_path_labels", True))

    def _on_toggle_path_labels(self) -> None:
        self.show_path_labels = self._current_show_path_labels()
        if getattr(self, "last_system", None) is None or getattr(self, "last_rays", None) is None:
            self._mark_plot_update_pending()
            return
        try:
            self.refresh_plot(suppress_analysis=True)
            self.status_var.set("2D labels shown" if self.show_path_labels else "2D labels hidden")
        except Exception:
            self._mark_plot_update_pending()

    def _on_ray_display_mode_changed(self, _event=None) -> None:
        mode = self._current_ray_display_mode()
        self._set_optional_var("ray_display_mode_var", mode)
        if getattr(self, "last_system", None) is None or getattr(self, "last_rays", None) is None:
            self._mark_plot_update_pending()
            return
        try:
            self.refresh_plot(suppress_analysis=True)
            self.status_var.set(f"2D ray display: {mode}")
        except Exception:
            self._mark_plot_update_pending()

    def _draw_optics_markers(self, optics_info: dict) -> None:
        self._clear_cardinal_marker_artists()
        if not self.show_cardinals_var.get():
            return
        if bool(self._resolved_trace_mode().get("use_folded")) and self._draw_folded_optics_markers(optics_info):
            return
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        x_min, x_max = min(x0, x1), max(x0, x1)
        y_min, y_max = min(y0, y1), max(y0, y1)
        span_x = max(x_max - x_min, 1e-9)
        span_y = max(y_max - y_min, 1e-9)
        marker_specs = [
            ("Front PP", optics_info.get("h1_z"), None, "#ff9f1c"),
            ("Back PP", optics_info.get("h2_z"), None, "#ff9f1c"),
            ("EP", optics_info.get("ep_z"), optics_info.get("ep_radius"), "#00bcd4"),
            ("XP", optics_info.get("xp_z"), optics_info.get("xp_radius"), "#e91e63"),
        ]

        visible_markers = []
        for label, z_pos, half_length, color in marker_specs:
            if z_pos is None:
                continue
            z_val = float(z_pos)
            if z_val < x_min or z_val > x_max:
                continue
            visible_markers.append((label, z_val, half_length, color))

        cap_half = max(0.8, min(0.025 * span_x, 0.035 * span_y))
        for index, (label, marker_pos, half_length, color) in enumerate(visible_markers):
            use_extent = (
                label in {"EP", "XP"}
                and half_length is not None
                and np.isfinite(float(half_length))
                and float(half_length) > 1e-9
            )
            z_val = float(marker_pos)
            if use_extent:
                seg_x, seg_y = self._project_xy(
                    [z_val, z_val],
                    [-float(half_length), float(half_length)],
                )
                p0 = np.array([float(seg_x[0]), float(seg_y[0])], dtype=float)
                p1 = np.array([float(seg_x[1]), float(seg_y[1])], dtype=float)
                artists = self._draw_cardinal_extent_marker(
                    p0,
                    p1,
                    color,
                    cap_half=cap_half,
                )
            else:
                artists = [
                    self.ax.axvline(z_val, color=color, linewidth=1.0, linestyle=":", alpha=0.9, zorder=70.0)
                ]
            y_label = y_max - (0.10 + 0.065 * (index % 4)) * span_y
            text = self.ax.text(
                z_val,
                y_label,
                label,
                color=color,
                fontsize=8,
                ha="center",
                va="top",
                zorder=71.0,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.6},
            )
            self._cardinal_marker_artists.extend((*artists, text))

    def _draw_arm_labels(self, projected) -> None:
        if not self._current_show_path_labels():
            return
        if self._draw_physical_ray_segment_labels(projected):
            return
        catalog = self._arm_catalog()
        if not catalog:
            return
        view_key = self._arm_key_for_view_label(str(self.arm_view_var.get() or ARM_VIEW_DEFAULT))
        palette = ("#0f766e", "#b45309", "#2563eb", "#be123c", "#6d28d9", "#047857")
        labeled_keys = self._draw_arm_ray_labels(projected, catalog, view_key, palette)
        key_to_entry = {entry["key"]: entry for entry in catalog}
        row_to_key: dict[int, str] = {}
        index = 1
        while index < len(self.rows) - 1:
            start, end = self._element_block_for_index(self.rows, index)
            key = self._arm_key_from_metadata(self._element_metadata(self.rows[start]))
            if key in key_to_entry:
                for row_index in range(start, end + 1):
                    row_to_key[row_index] = key
            index = max(end + 1, index + 1)
        if not row_to_key:
            return

        y0, y1 = self.ax.get_ylim()
        span_y = max(abs(float(y1) - float(y0)), 1.0)
        arm_points: dict[str, list[np.ndarray]] = {entry["key"]: [] for entry in catalog}
        for curve in getattr(projected, "curves", []):
            key = row_to_key.get(int(curve.row_index))
            if not key:
                continue
            pts = np.asarray(curve.points_2d, dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 2:
                continue
            finite = np.isfinite(pts[:, 0]) & np.isfinite(pts[:, 1])
            if np.any(finite):
                arm_points[key].append(np.mean(pts[finite], axis=0))

        for index, entry in enumerate(catalog):
            if view_key and entry["key"] != view_key:
                continue
            if entry["key"] in labeled_keys:
                continue
            points = arm_points.get(entry["key"]) or []
            if not points:
                continue
            center = np.mean(np.vstack(points), axis=0)
            detail = entry["detail"]
            label = entry["short_label"] if not detail else f"{entry['short_label']}\n{detail}"
            y_offset = (0.035 + 0.018 * (index % 3)) * span_y
            color = palette[index % len(palette)]
            self.ax.text(
                float(center[0]),
                float(center[1]) + y_offset,
                label,
                color=color,
                fontsize=8,
                ha="center",
                va="bottom",
                zorder=72.0,
                clip_on=True,
                bbox={
                    "facecolor": "white",
                    "edgecolor": color,
                    "alpha": 0.78,
                    "boxstyle": "round,pad=0.25",
                    "linewidth": 0.8,
                },
            )

    def _projected_scene_for_layout_render(
        self,
        projected: ProjectedScene2D,
        *,
        suppress_scene_labels: bool | None = None,
    ) -> ProjectedScene2D:
        if suppress_scene_labels is None:
            suppress_scene_labels = self._uses_michelson_leg_workflow()
        return projected_scene_for_layout_render(
            projected,
            suppress_scene_labels=bool(suppress_scene_labels),
        )

    def _plot_leg_label_text(self, leg_id: str, short_label: str, detail: str) -> str:
        return leg_label_text(self._physical_leg_workflow(), leg_id, short_label, detail)

    def _projected_center_for_row(self, projected, row_index: int) -> np.ndarray | None:
        if 0 <= row_index < len(self.rows):
            display_settings = (self.rows[row_index].advanced or {}).get("Display2D", {})
            if isinstance(display_settings, dict):
                center_value = display_settings.get("plane_center")
                try:
                    center = np.asarray(center_value, dtype=float).ravel()
                except Exception:
                    center = np.empty(0, dtype=float)
                if center.size >= 2 and np.all(np.isfinite(center[:2])):
                    return np.asarray(center[:2], dtype=float)
        points: list[np.ndarray] = []
        for curve in getattr(projected, "curves", []) or []:
            if int(getattr(curve, "row_index", -1)) != int(row_index):
                continue
            curve_points = np.asarray(getattr(curve, "points_2d", []), dtype=float)
            if curve_points.ndim != 2 or curve_points.shape[0] < 1:
                continue
            finite = np.isfinite(curve_points[:, 0]) & np.isfinite(curve_points[:, 1])
            if np.any(finite):
                points.append(curve_points[finite])
        if points:
            return np.mean(np.vstack(points), axis=0)
        return None

    def _first_row_index_matching(self, predicate) -> int | None:
        for index, row in enumerate(self.rows):
            try:
                if predicate(index, row):
                    return index
            except Exception:
                continue
        return None

    @staticmethod
    def _leg_geometry_from_points(points: list[np.ndarray]) -> dict[str, object] | None:
        return leg_geometry_from_points(points)

    @staticmethod
    def _leg_geometry_point_at_fraction(leg: dict[str, object], fraction: float) -> np.ndarray | None:
        return leg_geometry_point_at_fraction(leg, fraction)

    def _first_beam_splitter_indices(self) -> list[int]:
        return [index for index, row in enumerate(self.rows) if row.surface == BEAM_SPLITTER_SURFACE]

    def _first_detector_index_matching(self, predicate) -> int | None:
        return self._first_row_index_matching(
            lambda index, row: row.surface in {"Aperture", "Image", "Standard"} and predicate(index, row)
        )

    def _auto_leg_geometry(self) -> dict[str, dict[str, object]]:
        geometry: dict[str, dict[str, object]] = {}
        for entry in self._auto_leg_entries():
            leg_id = str(entry.get("leg_id", "") or "").strip().lower()
            polyline = np.asarray(entry.get("polyline", []), dtype=float)
            if not leg_id or polyline.ndim != 2 or polyline.shape[0] < 2:
                continue
            leg = self._leg_geometry_from_points([point for point in polyline])
            if leg is not None:
                geometry[leg_id] = leg
        return geometry

    def _michelson_leg_geometry(self, projected) -> dict[str, dict[str, object]]:
        if not self._uses_michelson_leg_workflow() or not self.rows:
            return {}
        workflow = self._physical_leg_workflow()
        if workflow not in {"mach_zehnder", "michelson"}:
            return self._auto_leg_geometry()
        splitter_indices = self._first_beam_splitter_indices()
        splitter_index = splitter_indices[0] if splitter_indices else None
        if splitter_index is None:
            return {}
        hub = self._projected_center_for_row(projected, splitter_index)
        if hub is None:
            return {}

        def row_selector(row: SurfaceRow) -> str:
            return str(self._element_metadata(row).get("branch_selector", "") or "").strip().lower()

        def row_role(row: SurfaceRow) -> str:
            return str(self._element_metadata(row).get("arm_role", ELEMENT_ARM_ROLE_DEFAULT) or ELEMENT_ARM_ROLE_DEFAULT)

        if workflow == "mach_zehnder":
            bs2_index = splitter_indices[1] if len(splitter_indices) >= 2 else None
            bs2 = self._projected_center_for_row(projected, bs2_index) if bs2_index is not None else None
            if bs2 is None:
                return {}
            transmit_mirror_index = self._first_row_index_matching(
                lambda _index, row: row.surface == "Mirror"
                and (
                    row_selector(row) == "transmit"
                    or "transmit" in str(getattr(row, "name", "") or "").lower()
                    or "transmit" in str(getattr(row, "element", "") or "").lower()
                )
            )
            reflect_mirror_index = self._first_row_index_matching(
                lambda _index, row: row.surface == "Mirror"
                and (
                    row_selector(row) == "reflect"
                    or "reflect" in str(getattr(row, "name", "") or "").lower()
                    or "reflect" in str(getattr(row, "element", "") or "").lower()
                )
            )
            cross_detector_index = self._first_detector_index_matching(
                lambda _index, row: (
                    "cross" in str(getattr(row, "name", "") or "").lower()
                    or (
                        row_role(row) == "Detector"
                        and row_selector(row) == "transmit"
                    )
                )
            )
            return_detector_index = self._first_detector_index_matching(
                lambda _index, row: (
                    "return" in str(getattr(row, "name", "") or "").lower()
                    or (
                        row_role(row) == "Detector"
                        and row_selector(row) == "reflect"
                    )
                )
            )
            target_points: dict[str, list[np.ndarray]] = {
                "input": [self._projected_center_for_row(projected, 0), hub],
                "transmit": [
                    hub,
                    self._projected_center_for_row(projected, transmit_mirror_index)
                    if transmit_mirror_index is not None
                    else None,
                    bs2,
                ],
                "reflect": [
                    hub,
                    self._projected_center_for_row(projected, reflect_mirror_index)
                    if reflect_mirror_index is not None
                    else None,
                    bs2,
                ],
                "cross": [
                    bs2,
                    self._projected_center_for_row(projected, cross_detector_index)
                    if cross_detector_index is not None
                    else None,
                ],
                "return": [
                    bs2,
                    self._projected_center_for_row(projected, return_detector_index)
                    if return_detector_index is not None
                    else None,
                ],
            }
            geometry: dict[str, dict[str, object]] = {}
            for leg_id, points in target_points.items():
                leg = self._leg_geometry_from_points([point for point in points if point is not None])
                if leg is not None:
                    geometry[leg_id] = leg
            return geometry

        detector_index = self._first_row_index_matching(
            lambda _index, row: row.surface == "Image" and row_role(row) == "Detector"
        )
        if detector_index is None:
            detector_index = self._first_row_index_matching(
                lambda _index, row: row_role(row) == "Detector"
            )
        if detector_index is None:
            detector_index = self._first_row_index_matching(
                lambda _index, row: row.surface == "Image" and self._row_has_detector_output_metadata(row)
            )

        target_indices: dict[str, int | None] = {
            "input": 0,
            "reflect": self._first_row_index_matching(
                lambda _index, row: row.surface == "Mirror"
                and (
                    row_selector(row) == "reflect"
                    or "reflect" in str(getattr(row, "name", "") or "").lower()
                    or "reference" in str(getattr(row, "name", "") or "").lower()
                    or "reference" in str(getattr(row, "element", "") or "").lower()
                )
                and (row_role(row) in {"Reflect", "Return"} or row_selector(row) == "")
            ),
            "transmit": self._first_row_index_matching(
                lambda _index, row: row.surface == "Mirror"
                and (
                    row_selector(row) == "transmit"
                    or "transmit" in str(getattr(row, "name", "") or "").lower()
                    or "test optic" in str(getattr(row, "name", "") or "").lower()
                    or "test optic" in str(getattr(row, "element", "") or "").lower()
                )
                and (row_role(row) in {"Transmit", "Return"} or row_selector(row) == "")
            ),
            "detector": detector_index,
        }
        geometry: dict[str, dict[str, object]] = {}
        for leg_id, target_index in target_indices.items():
            if target_index is None:
                continue
            endpoint = self._projected_center_for_row(projected, target_index)
            if endpoint is None:
                continue
            leg = self._leg_geometry_from_points([hub, endpoint])
            if leg is not None:
                geometry[leg_id] = leg
        return geometry

    def _physical_ray_leg_segments(self, projected) -> tuple[dict[str, list[dict[str, object]]], np.ndarray] | None:
        if not self._uses_michelson_leg_workflow():
            return None
        rays = list(getattr(projected, "rays", []) or [])
        if not rays:
            return None
        geometry = self._michelson_leg_geometry(projected)
        if not geometry:
            return None

        finite_points: list[np.ndarray] = []
        for ray in rays:
            points = np.asarray(getattr(ray, "points_2d", []), dtype=float)
            if points.ndim == 2 and points.shape[0] >= 2:
                finite = np.isfinite(points[:, 0]) & np.isfinite(points[:, 1])
                if np.any(finite):
                    finite_points.append(points[finite])
        if not finite_points:
            return None
        all_points = np.vstack(finite_points)
        x_min, x_max = float(np.min(all_points[:, 0])), float(np.max(all_points[:, 0]))
        y_min, y_max = float(np.min(all_points[:, 1])), float(np.max(all_points[:, 1]))
        span_x = max(x_max - x_min, 1.0)
        span_y = max(y_max - y_min, 1.0)
        min_segment = max(0.25, 0.003 * min(span_x, span_y))
        raw_segments: list[dict[str, object]] = []
        for ray in rays:
            points = np.asarray(getattr(ray, "points_2d", []), dtype=float)
            if points.ndim != 2 or points.shape[0] < 2:
                continue
            finite = np.isfinite(points[:, 0]) & np.isfinite(points[:, 1])
            if not np.all(finite):
                original_indices = np.flatnonzero(finite)
                points = points[finite]
            else:
                original_indices = np.arange(points.shape[0], dtype=int)
            if points.shape[0] < 2:
                continue
            for index in range(points.shape[0] - 1):
                p0 = np.asarray(points[index], dtype=float)
                p1 = np.asarray(points[index + 1], dtype=float)
                length = float(np.linalg.norm(p1 - p0))
                if length <= min_segment:
                    continue
                raw_segments.append(
                    {
                        "ray": ray,
                        "p0": p0,
                        "p1": p1,
                        "start_index": int(original_indices[index]),
                        "end_index": int(original_indices[index + 1]),
                        "length": length,
                    }
                )
        if not raw_segments:
            return None

        groups: dict[str, list[dict[str, object]]] = {leg_id: [] for leg_id, _short, _detail in self._physical_leg_definitions()}
        for segment in raw_segments:
            p0 = np.asarray(segment["p0"], dtype=float)
            p1 = np.asarray(segment["p1"], dtype=float)
            tangent = p1 - p0
            tangent_norm = float(np.linalg.norm(tangent))
            if tangent_norm <= min_segment:
                continue
            tangent = tangent / tangent_norm
            midpoint = 0.5 * (p0 + p1)
            best: tuple[float, str] | None = None
            for leg_id, leg in geometry.items():
                for seg0, seg1 in list(leg.get("segments", []) or []):
                    seg0 = np.asarray(seg0, dtype=float)
                    seg1 = np.asarray(seg1, dtype=float)
                    axis = seg1 - seg0
                    length = float(np.linalg.norm(axis))
                    if length <= 1e-9:
                        continue
                    unit = axis / length
                    offset = midpoint - seg0
                    projection = float(np.dot(offset, unit))
                    t = projection / max(length, 1e-12)
                    if t < -0.10 or t > 1.12:
                        continue
                    alignment = abs(float(np.dot(tangent, unit)))
                    if alignment < 0.45:
                        continue
                    perpendicular = float(np.linalg.norm(offset - unit * projection))
                    tolerance = max(3.0, 0.24 * min(length, 90.0))
                    if perpendicular > tolerance:
                        continue
                    score = perpendicular / tolerance + 0.25 * (1.0 - alignment)
                    if best is None or score < best[0]:
                        best = (score, leg_id)
            if best is None:
                continue
            leg_id = best[1]
            segment_with_leg = dict(segment)
            segment_with_leg["leg_id"] = leg_id
            groups[leg_id].append(segment_with_leg)

        groups = {leg_id: segments for leg_id, segments in groups.items() if segments}
        if not groups:
            return None
        first_leg = next(iter(geometry.values()))
        return groups, np.asarray(first_leg["hub"], dtype=float)

    def _draw_physical_ray_segment_labels(self, projected) -> bool:
        geometry = self._michelson_leg_geometry(projected)
        if not geometry:
            return False
        definitions = self._physical_leg_definitions()
        workflow = self._physical_leg_workflow()
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        view_leg_id = self._leg_id_from_arm_key(self._current_arm_view_key())
        label_plan = physical_leg_label_plan(
            definitions=definitions,
            geometry=geometry,
            workflow=workflow,
            axis_limits=(x0, x1, y0, y1),
            view_leg_id=view_leg_id,
        )
        for item in label_plan:
            point = np.asarray(item["point"], dtype=float)
            text_point = np.asarray(item["text_point"], dtype=float)
            self.ax.annotate(
                str(item["label"]),
                xy=(float(point[0]), float(point[1])),
                xytext=(float(text_point[0]), float(text_point[1])),
                color="#334155",
                fontsize=7.8,
                ha="center",
                va="center",
                zorder=82.0,
                clip_on=True,
                arrowprops={
                    "arrowstyle": "-|>",
                    "color": "#334155",
                    "linewidth": 0.85,
                    "alpha": 0.9,
                    "shrinkA": 3,
                    "shrinkB": 2,
                },
                bbox={
                    "facecolor": "white",
                    "edgecolor": "#334155",
                    "alpha": 0.86,
                    "boxstyle": "round,pad=0.22",
                    "linewidth": 0.75,
                },
            )
            self.ax.plot(
                [float(point[0])],
                [float(point[1])],
                marker="o",
                markersize=3.2,
                color="#111827",
                alpha=0.95,
                zorder=81.0,
            )
        return bool(label_plan)

    def _arm_ray_label_targets(self, projected, catalog: list[dict[str, str]], view_key: str = "") -> list[dict[str, object]]:
        return arm_ray_label_targets(
            projected,
            catalog,
            view_key,
            indices_for_arm_key=self._indices_for_arm_key,
            branch_path_for_arm_key=self._branch_path_for_arm_key,
            ray_matches_arm_key=self._ray_matches_arm_key,
            branch_path_selector_sequence=self._branch_path_selector_sequence,
        )

    def _draw_arm_ray_labels(
        self,
        projected,
        catalog: list[dict[str, str]],
        view_key: str,
        palette: tuple[str, ...],
    ) -> set[str]:
        targets = self._arm_ray_label_targets(projected, catalog, view_key)
        if not targets:
            return set()
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        labeled: set[str] = set()
        for item in arm_ray_label_plan(targets, axis_limits=(x0, x1, y0, y1), palette=palette):
            point = np.asarray(item["point"], dtype=float)
            text_point = np.asarray(item["text_point"], dtype=float)
            color = str(item["color"])
            self.ax.annotate(
                str(item["label"]),
                xy=(float(point[0]), float(point[1])),
                xytext=(float(text_point[0]), float(text_point[1])),
                color=color,
                fontsize=8,
                ha="center",
                va="center",
                zorder=82.0,
                clip_on=True,
                arrowprops={
                    "arrowstyle": "-|>",
                    "color": color,
                    "linewidth": 0.9,
                    "alpha": 0.9,
                    "shrinkA": 3,
                    "shrinkB": 2,
                },
                bbox={
                    "facecolor": "white",
                    "edgecolor": color,
                    "alpha": 0.86,
                    "boxstyle": "round,pad=0.25",
                    "linewidth": 0.8,
                },
            )
            for key in list(item.get("entry_keys", []) or []):
                labeled.add(str(key))
            self.ax.plot(
                [float(point[0])],
                [float(point[1])],
                marker="o",
                markersize=3.2,
                color=str(item.get("marker_color", color) or color),
                alpha=0.95,
                zorder=81.0,
            )
        return labeled

    def _common_arm_surface_indices(self) -> set[int]:
        indices = {0} if self.rows else set()
        if not self.rows:
            return indices
        index = 1
        while index < len(self.rows) - 1:
            start, end = self._element_block_for_index(self.rows, index)
            role = self._element_arm_role_for_index(self.rows, start)
            if role == "Common":
                indices.update(range(start, end + 1))
            index = max(end + 1, index + 1)
        return indices

    def _context_surface_indices_for_arm_key(self, arm_key: str) -> set[int]:
        leg_id = self._leg_id_from_arm_key(arm_key)
        if not leg_id:
            return self._common_arm_surface_indices()
        indices = {0} if self.rows else set()
        auto_entry = self._auto_leg_entry_for_id(leg_id)
        if auto_entry is not None:
            return indices | {
                int(index)
                for index in set(auto_entry.get("context_indices", set()) or set())
                if 0 <= int(index) < len(self.rows)
            }
        if self._physical_leg_workflow() != "mach_zehnder":
            return indices | self._common_arm_surface_indices()
        splitters = self._first_beam_splitter_indices()
        bs1 = splitters[0] if len(splitters) >= 1 else None
        bs2 = splitters[1] if len(splitters) >= 2 else None
        if leg_id in {"input", "transmit", "reflect"} and bs1 is not None:
            indices.add(bs1)
        if leg_id in {"transmit", "reflect", "cross", "return"} and bs2 is not None:
            indices.add(bs2)
        return indices

    def _default_parent_splitter_id(self) -> str:
        for index, row in enumerate(self.rows):
            if row.surface != BEAM_SPLITTER_SURFACE:
                continue
            metadata = self._element_metadata(row)
            return (
                str(metadata.get("element_id", "") or "").strip()
                or self._element_key(row)
                or str(row.name or f"S{index}").strip()
            )
        return ""

    def _splitter_id_by_ordinal(self, ordinal: int) -> str:
        target = int(ordinal)
        seen = 0
        for index, row in enumerate(self.rows):
            if row.surface != BEAM_SPLITTER_SURFACE:
                continue
            if seen != target:
                seen += 1
                continue
            metadata = self._element_metadata(row)
            return (
                str(metadata.get("element_id", "") or "").strip()
                or self._element_key(row)
                or str(row.name or f"S{index}").strip()
            )
        return self._default_parent_splitter_id()

    def _branch_selector_for_arm_key(self, arm_key: str) -> str:
        path = self._branch_path_for_arm_key(arm_key)
        if path:
            return self._branch_path_leaf_selector(path)
        leg_id = self._leg_id_from_arm_key(arm_key)
        if leg_id:
            workflow = self._physical_leg_workflow()
            if workflow == "mach_zehnder":
                return {
                    "input": "primary",
                    "transmit": "transmit",
                    "reflect": "reflect",
                    "cross": "transmit",
                    "return": "reflect",
                }.get(leg_id, "")
            if leg_id == "input":
                return "primary"
            if leg_id in {"reflect", "transmit"}:
                return leg_id
            if leg_id == "detector":
                return "reflect"
        parts = str(arm_key or "").split("|")
        if len(parts) >= 3 and parts[0] == "branch":
            selector = parts[2].strip().lower()
            if selector in {"transmit", "reflect", "primary", "return"}:
                return selector
        return ""

    def _ray_matches_arm_key(self, ray, arm_key: str) -> bool:
        key = str(arm_key or "").strip()
        if not key:
            return False
        if self._leg_id_from_arm_key(key):
            return False
        branch_path = str(getattr(ray, "branch_path", "") or "").strip()
        target_path = self._branch_path_for_arm_key(key)
        if target_path:
            return branch_path == target_path
        if branch_path and self._metadata_arm_key_matches_branch_path(key, branch_path):
            return True
        selector = self._branch_selector_for_arm_key(key)
        branch_label = str(getattr(ray, "branch_label", "") or "").strip().lower()
        return bool(selector and branch_label == selector)

    def _apply_arm_key_metadata_to_row(self, row: SurfaceRow, arm_key: str) -> None:
        label = self._next_manual_element_label()
        metadata = self._element_metadata_for_arm_key(arm_key, label)
        if metadata is None:
            return
        row.element = label
        self._set_element_metadata(row, metadata)

    def _projected_rays_for_leg_view(self, projected: ProjectedScene2D, arm_key: str) -> list[ProjectedRay2D]:
        leg_id = self._leg_id_from_arm_key(arm_key)
        if not leg_id:
            return []
        segment_data = self._physical_ray_leg_segments(projected)
        if segment_data is None:
            return []
        groups, _hub = segment_data
        rays: list[ProjectedRay2D] = []
        for segment_index, segment in enumerate(groups.get(leg_id, []) or []):
            ray = segment.get("ray")
            if ray is None:
                continue
            p0 = np.asarray(segment.get("p0"), dtype=float)
            p1 = np.asarray(segment.get("p1"), dtype=float)
            if p0.shape[0] < 2 or p1.shape[0] < 2:
                continue
            segment_points = np.vstack([p0[:2], p1[:2]])
            segment_events = projected_ray_events_for_segment(
                ray,
                int(segment.get("start_index", 0)),
                int(segment.get("end_index", 1)),
                segment_points,
            )
            segment_surface_ids = [
                int(getattr(event, "surface_id"))
                for event in segment_events
                if str(getattr(event, "event_kind", "") or "") == "surface"
                and getattr(event, "surface_id", None) is not None
            ]
            segment_terminal_surface_ids = [
                int(getattr(event, "surface_id"))
                for event in segment_events
                if str(getattr(event, "event_kind", "") or "") == "terminal"
                and getattr(event, "surface_id", None) is not None
            ]
            rays.append(
                ProjectedRay2D(
                    ray_index=int(getattr(ray, "ray_index", segment_index)),
                    field_index=int(getattr(ray, "field_index", 0)),
                    color=str(getattr(ray, "color", "#39FF14") or "#39FF14"),
                    points_2d=segment_points,
                    reaches_image=bool(getattr(ray, "reaches_image", False)),
                    terminal_status=str(getattr(ray, "terminal_status", "") or ""),
                    surface_ids=np.asarray(segment_surface_ids, dtype=int),
                    branch_label=str(getattr(ray, "branch_label", "") or ""),
                    branch_path=str(getattr(ray, "branch_path", "") or ""),
                    source_id=str(getattr(ray, "source_id", "") or ""),
                    source_name=str(getattr(ray, "source_name", "") or ""),
                    terminal_surface_ids=np.asarray(segment_terminal_surface_ids, dtype=int),
                    events_2d=segment_events,
                )
            )
        return rays

    def _filter_projected_scene_for_arm_view(self, projected: ProjectedScene2D) -> ProjectedScene2D:
        arm_key = self._arm_key_for_view_label(str(self.arm_view_var.get() or ARM_VIEW_DEFAULT))
        if not arm_key:
            return projected
        arm_indices = set(self._indices_for_arm_key(arm_key))
        allowed_indices = self._context_surface_indices_for_arm_key(arm_key) | self._surface_indices_for_arm_key(arm_key)

        curves = [
            curve
            for curve in projected.curves
            if int(curve.row_index) in allowed_indices
        ]
        pick_regions = [
            region
            for region in projected.pick_regions
            if int(region.row_index) in allowed_indices
        ]
        rays = self._projected_rays_for_leg_view(projected, arm_key)
        if not rays:
            for ray in projected.rays:
                surface_ids = set(np.asarray(getattr(ray, "surface_ids", []), dtype=int).ravel().tolist())
                if self._ray_matches_arm_key(ray, arm_key):
                    rays.append(ray)
                elif arm_indices and surface_ids & arm_indices:
                    rays.append(ray)
        visible_source_ids = {
            str(getattr(ray, "source_id", "") or "").strip()
            for ray in rays
            if str(getattr(ray, "source_id", "") or "").strip()
        }
        terminal_indices = projected_ray_terminal_surface_ids(rays)
        labels = filter_projected_labels_for_rows_and_sources(projected.labels, allowed_indices, visible_source_ids, terminal_indices)

        bound_points: list[np.ndarray] = []
        for curve in curves:
            points = np.asarray(curve.points_2d, dtype=float)
            if points.ndim == 2 and points.shape[0]:
                bound_points.append(points)
        for ray in rays:
            points = np.asarray(ray.points_2d, dtype=float)
            if points.ndim == 2 and points.shape[0]:
                bound_points.append(points)
        bounds = BoundsRect.from_points(bound_points)
        return ProjectedScene2D(
            curves=curves,
            rays=rays,
            planes=list(projected.planes),
            labels=labels,
            pick_regions=pick_regions,
            bounds=bounds,
        )

    @staticmethod
    def _projected_ray_is_direct_source_path(ray) -> bool:
        branch_path = str(getattr(ray, "branch_path", "") or "").strip().lower()
        branch_label = str(getattr(ray, "branch_label", "") or "").strip().lower()
        return branch_path in {"", "primary"} and branch_label in {"", "primary"}

    @staticmethod
    def _representative_projected_rays_by_branch(rays: list[ProjectedRay2D]) -> list[ProjectedRay2D]:
        return representative_projected_rays_by_branch(rays)

    def _filter_projected_scene_for_ray_display(self, projected: ProjectedScene2D) -> ProjectedScene2D:
        mode = self._current_ray_display_mode()
        hide_stopped = not bool(self.show_clipped_rays_var.get())
        explicit_terminal_modes = {
            RAY_DISPLAY_MISSED_DETECTOR: "missed_detector",
            RAY_DISPLAY_ABSORBED: "absorbed",
            RAY_DISPLAY_ESCAPED: "escaped",
            RAY_DISPLAY_STOPPED: "stopped",
        }
        rays = []
        for ray in list(getattr(projected, "rays", []) or []):
            terminal_status = projected_ray_terminal_status(ray)
            if mode in explicit_terminal_modes:
                if terminal_status != explicit_terminal_modes[mode]:
                    continue
            elif hide_stopped and not projected_ray_hits_detector(ray):
                continue
            elif mode == RAY_DISPLAY_DETECTOR and not projected_ray_hits_detector(ray):
                continue
            elif mode == RAY_DISPLAY_SPLITTER and self._projected_ray_is_direct_source_path(ray):
                continue
            rays.append(ray)
        if mode == RAY_DISPLAY_SPLITTER:
            rays = self._representative_projected_rays_by_branch(rays)
        if mode == RAY_DISPLAY_ALL and not hide_stopped:
            return projected
        visible_source_ids = {
            str(getattr(ray, "source_id", "") or "").strip()
            for ray in rays
            if str(getattr(ray, "source_id", "") or "").strip()
        }
        visible_terminal_indices = projected_ray_terminal_surface_ids(rays)
        all_terminal_indices = projected_ray_terminal_surface_ids(getattr(projected, "rays", []) or [])
        labels = filter_projected_labels_for_visible_ray_set(
            projected.labels,
            visible_source_ids,
            visible_terminal_indices,
            all_terminal_indices,
        )

        bound_points: list[np.ndarray] = []
        for curve in projected.curves:
            points = np.asarray(curve.points_2d, dtype=float)
            if points.ndim == 2 and points.shape[0]:
                bound_points.append(points)
        for ray in rays:
            points = np.asarray(ray.points_2d, dtype=float)
            if points.ndim == 2 and points.shape[0]:
                bound_points.append(points)
        bounds = BoundsRect.from_points(bound_points)
        return ProjectedScene2D(
            curves=list(projected.curves),
            rays=rays,
            planes=list(projected.planes),
            labels=labels,
            pick_regions=list(projected.pick_regions),
            bounds=bounds,
        )

    def _draw_cardinal_extent_marker(
        self,
        p0: np.ndarray,
        p1: np.ndarray,
        color: str,
        *,
        cap_half: float,
    ) -> list:
        tangent = np.asarray(p1, dtype=float) - np.asarray(p0, dtype=float)
        norm = np.linalg.norm(tangent)
        if norm <= 1e-12:
            return []
        tangent /= norm
        normal = np.array([-tangent[1], tangent[0]], dtype=float)
        normal /= max(np.linalg.norm(normal), 1e-12)
        artists = [
            self.ax.plot(
                [float(p0[0]), float(p1[0])],
                [float(p0[1]), float(p1[1])],
                color=color,
                linewidth=1.35,
                linestyle="-",
                alpha=0.95,
                zorder=70.0,
            )[0]
        ]
        for point in (np.asarray(p0, dtype=float), np.asarray(p1, dtype=float)):
            c0 = point - normal * cap_half
            c1 = point + normal * cap_half
            artists.append(
                self.ax.plot(
                    [float(c0[0]), float(c1[0])],
                    [float(c0[1]), float(c1[1])],
                    color=color,
                    linewidth=1.1,
                    linestyle="-",
                    alpha=0.95,
                    zorder=70.0,
                )[0]
            )
        return artists

    def _folded_path_plane_at_distance(self, path_distance: float) -> tuple[np.ndarray, np.ndarray] | None:
        try:
            point, direction, _max_half, _extent_points, elements = self._compute_folded_layout_geometry()
        except Exception:
            return None
        if not elements:
            return None
        vertices: list[tuple[float, np.ndarray]] = [(0.0, np.asarray(point, dtype=float).copy())]
        distance = 0.0
        for row_index, element in enumerate(elements, start=1):
            center = np.asarray(element[1], dtype=float)
            distance += max(float(self.rows[row_index - 1].thickness), 0.0)
            vertices.append((float(distance), center.copy()))
        return folded_path_plane_at_distance(path_distance, vertices, direction)

    def _draw_folded_optics_markers(self, optics_info: dict) -> bool:
        marker_specs = [
            ("Front PP", optics_info.get("h1_z"), None, "#ff9f1c"),
            ("Back PP", optics_info.get("h2_z"), None, "#ff9f1c"),
            ("EP", optics_info.get("ep_z"), optics_info.get("ep_radius"), "#00bcd4"),
            ("XP", optics_info.get("xp_z"), optics_info.get("xp_radius"), "#e91e63"),
        ]
        drawn = 0
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        plans = folded_optics_marker_plan(
            marker_specs,
            axis_limits=(x0, x1, y0, y1),
            path_plane_at_distance=self._folded_path_plane_at_distance,
        )
        for item in plans:
            p0 = np.asarray(item["p0"], dtype=float)
            p1 = np.asarray(item["p1"], dtype=float)
            color = str(item["color"])
            if bool(item["use_extent"]):
                artists = self._draw_cardinal_extent_marker(
                    p0,
                    p1,
                    color,
                    cap_half=float(item["cap_half"]),
                )
            else:
                artists = [
                    self.ax.plot(
                        [p0[0], p1[0]],
                        [p0[1], p1[1]],
                        color=color,
                        linewidth=1.15,
                        linestyle=":",
                        alpha=0.95,
                        zorder=70.0,
                    )[0]
                ]
            label_pos = np.asarray(item["label_pos"], dtype=float)
            text = self.ax.text(
                float(label_pos[0]),
                float(label_pos[1]),
                str(item["label"]),
                color=color,
                fontsize=8,
                ha="center",
                va="bottom",
                zorder=71.0,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.6},
            )
            self._cardinal_marker_artists.extend((*artists, text))
            drawn += 1
        return drawn > 0

    # --- Physical Distance overlay -------------------------------------------

    def _results_display_service(self) -> ResultsDisplayService:
        service = self.__dict__.get("_results_display_service_instance")
        if service is None:
            service = ResultsDisplayService(self)
            self._results_display_service_instance = service
        return service

    def _clear_physical_distance_artists(self) -> None:
        self._results_display_service()._clear_physical_distance_artists()

    def _on_toggle_physical_distances(self) -> None:
        self._results_display_service()._on_toggle_physical_distances()

    def _draw_physical_distances(self) -> None:
        self._results_display_service()._draw_physical_distances()

    def _update_results(self, system, rays, wavelength: float, optics_info: dict | None = None) -> None:
        self._results_display_service()._update_results(system, rays, wavelength, optics_info)

    # _set_plot_limits_from_layout removed — now in scene_renderer_2d.set_plot_limits

    def _set_plot_limits_from_drawn_data(self) -> None:
        x_values: list[float] = []
        y_values: list[float] = []
        for line in self.ax.lines:
            xdata = np.asarray(line.get_xdata(orig=False), dtype=float)
            ydata = np.asarray(line.get_ydata(orig=False), dtype=float)
            finite = np.isfinite(xdata) & np.isfinite(ydata)
            if np.any(finite):
                x_values.extend(xdata[finite].tolist())
                y_values.extend(ydata[finite].tolist())
        if not x_values or not y_values:
            return
        x_min = min(x_values)
        x_max = max(x_values)
        y_min = min(y_values)
        y_max = max(y_values)
        span_x = max(x_max - x_min, 1.0)
        span_y = max(y_max - y_min, 1.0)
        self.ax.set_xlim(x_min - 0.08 * span_x, x_max + 0.08 * span_x)
        self.ax.set_ylim(y_min - 0.12 * span_y, y_max + 0.12 * span_y)

    def _draw_input_ray_overlay(self, max_radius: float) -> None:
        if not self.rows:
            return
        if self._current_object_mode() == "Infinity":
            return
        object_distance = self._current_object_distance()
        if object_distance <= 1e-9:
            return
        field_samples = self._sample_field_values(self._current_field_height())
        angle_samples = self._sample_fan_angles_deg()
        colors = self._field_colors(len(field_samples))
        for field_index, field_height in enumerate(field_samples):
            color = colors[field_index]
            for angle_deg in angle_samples:
                angle_rad = np.deg2rad(angle_deg)
                pupil_y = float(field_height) + float(np.tan(angle_rad) * object_distance)
                x_vals, y_vals = self._project_xy([0.0, object_distance], [float(field_height), float(pupil_y)])
                self.ax.plot(
                    x_vals,
                    y_vals,
                    color=color,
                    linewidth=1.8,
                    alpha=0.95,
                )

    @staticmethod
    def _gaussian_radius_from_q(q_value: complex, wavelength_mm: float, m2: float, refractive_index: float) -> float:
        if not (np.isfinite(q_value.real) and np.isfinite(q_value.imag)) or abs(q_value) <= 1e-18:
            return np.nan
        inverse_q = 1.0 / q_value
        imag_inverse = float(np.imag(inverse_q))
        if imag_inverse >= 0.0:
            return np.nan
        return float(np.sqrt(-(wavelength_mm * m2) / (np.pi * max(float(refractive_index), 1e-12) * imag_inverse)))

    def _draw_gaussian_beam_overlay(self, system, wavelength: float) -> float | None:
        if self._current_source_model() != "Gaussian beam":
            return None
        source_direction = np.asarray(self._current_source_direction(), dtype=float)
        if np.linalg.norm(source_direction - np.asarray((0.0, 0.0, 1.0), dtype=float)) > 1e-9:
            self.append_debug(
                "Gaussian beam envelope skipped for non-+Z source direction; "
                "use traced source rays and Gaussian Beam Report data."
            )
            return None
        if any(row.surface == "Mirror" for row in self.rows) or self._has_off_axis_geometry():
            self.append_debug("Gaussian beam envelope skipped for folded/off-axis geometry; use Gaussian Beam Report for ABCD data.")
            return None
        try:
            paraxial_trace = system.ParaxMatrices(float(wavelength))
            input_beam = self._current_gaussian_beam_input(wavelength)
            beam_trace = Kos.propagate_gaussian_beam(paraxial_trace, input_beam)
        except Exception as exc:
            self.append_debug(f"Gaussian beam overlay unavailable: {_short_error_message(exc)}")
            return None

        wavelength_mm = float(beam_trace.wavelength_mm)
        m2 = float(input_beam.m2)
        current_z = 0.0
        source_x, source_y, source_z = self._current_source_origin()
        _unused_source_x = source_x
        q_before = complex(beam_trace.input_q)
        n_current = float(beam_trace.input_index)
        z_values: list[float] = [float(source_z)]
        radius_values: list[float] = [
            self._gaussian_radius_from_q(q_before, wavelength_mm, m2, n_current)
        ]

        for parax_step, beam_step in zip(paraxial_trace.steps, beam_trace.steps):
            q_after = complex(float(beam_step.q_real_mm), float(beam_step.q_imag_mm))
            n_after = max(float(beam_step.n_after), 1e-12)
            if str(getattr(parax_step, "kind", "")) == "translation":
                thickness = float(getattr(parax_step, "thickness", 0.0))
                sample_count = max(2, min(32, int(abs(thickness) / 5.0) + 2))
                for offset in np.linspace(0.0, thickness, sample_count)[1:]:
                    q_sample = q_before + float(offset)
                    z_values.append(float(source_z + current_z + float(offset)))
                    radius_values.append(self._gaussian_radius_from_q(q_sample, wavelength_mm, m2, n_after))
                current_z += thickness
            else:
                z_values.append(float(source_z + current_z))
                radius_values.append(self._gaussian_radius_from_q(q_after, wavelength_mm, m2, n_after))
            q_before = q_after
            n_current = n_after

        z_arr = np.asarray(z_values, dtype=float)
        r_arr = np.asarray(radius_values, dtype=float)
        finite = np.isfinite(z_arr) & np.isfinite(r_arr) & (r_arr >= 0.0)
        if np.count_nonzero(finite) < 2:
            return None
        z_arr = z_arr[finite]
        r_arr = r_arr[finite]
        y_center = float(source_y)
        upper_x, upper_y = self._project_xy(z_arr, y_center + r_arr)
        lower_x, lower_y = self._project_xy(z_arr, y_center - r_arr)
        center_x, center_y = self._project_xy(z_arr, np.full_like(z_arr, y_center))
        color = "#f59e0b"
        self.ax.plot(upper_x, upper_y, color=color, linewidth=1.8, linestyle="-", alpha=0.92, zorder=31.0)
        self.ax.plot(lower_x, lower_y, color=color, linewidth=1.8, linestyle="-", alpha=0.92, zorder=31.0)
        self.ax.plot(center_x, center_y, color=color, linewidth=0.85, linestyle=":", alpha=0.75, zorder=30.0)
        if self._current_display_orientation() == "YZ":
            self.ax.fill_between(
                z_arr,
                y_center - r_arr,
                y_center + r_arr,
                color=color,
                alpha=0.08,
                linewidth=0.0,
                zorder=29.0,
            )
        label_index = min(max(int(len(z_arr) * 0.12), 0), len(z_arr) - 1)
        self.ax.text(
            float(upper_x[label_index]),
            float(upper_y[label_index]),
            "Gaussian 1/e^2",
            color=color,
            fontsize=8,
            ha="left",
            va="bottom",
            zorder=61.0,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.7, "pad": 0.4},
        )
        return float(np.max(np.abs(y_center) + r_arr))

    def _apply_example_display_defaults(self, path: Path) -> None:
        code = path.read_text(encoding="utf-8", errors="ignore")
        self._apply_interferometer_example_defaults(path)

        wavelength_match = re.search(r"\bW\s*=\s*([0-9]*\.?[0-9]+)", code)
        if wavelength_match:
            self.wavelength_var.set(wavelength_match.group(1))

        aperture_type_match = re.search(r"\b(?:AperType|ApType)\s*=\s*['\"](STOP|EPD|FNO)['\"]", code)
        if aperture_type_match:
            self.aperture_type_var.set(aperture_type_match.group(1))

        aperture_value_match = re.search(r"\b(?:AperVal|ApVal)\s*=\s*([0-9]*\.?[0-9]+)", code)
        if aperture_value_match:
            self.aperture_value_var.set(aperture_value_match.group(1))

        surf_match = re.search(r"\b(?:Surf|sup)\s*=\s*([0-9]+)", code)
        if surf_match:
            surf_index = surf_match.group(1)
            label = None
            for option in self.analysis_surface_menu["values"]:
                if option.startswith(f"{surf_index}:"):
                    label = option
                    break
            if label is not None:
                self.analysis_surface_var.set(label)
            else:
                self.analysis_surface_var.set("Auto")
        else:
            self.analysis_surface_var.set("Auto")

        if self._example_requests_nonsequential(code) and hasattr(self, "trace_mode_var"):
            self.trace_mode_var.set("Non-Sequential Preview")
            self.trace_mode = "Non-Sequential Preview"

    def _apply_interferometer_example_defaults(self, path: Path) -> None:
        stem = path.stem.lower()
        is_michelson = stem == "examp_michelson_interferometer"
        is_twyman = stem == "examp_twyman_green_interferometer"
        is_mach_zehnder = stem == "examp_mach_zehnder_interferometer"
        if not (is_michelson or is_twyman or is_mach_zehnder):
            return

        def _set_text_var(name: str, value: str) -> None:
            var = getattr(self, name, None)
            if var is not None:
                try:
                    var.set(value)
                except Exception:
                    pass

        _set_text_var("object_mode_var", "Infinity")
        _set_text_var("display_orientation_var", "YZ")
        _set_text_var("wavelength_var", "0.6328")
        _set_text_var("ray_count_var", "1")
        _set_text_var("source_model_var", "Collimated disk source")
        _set_text_var("source_radius_var", "0.5")
        _set_text_var("source_cone_angle_var", "0.0")
        _set_text_var("source_power_var", "1.0")
        _set_text_var("source_seed_var", "1")
        _set_text_var("source_x_var", "0.0")
        _set_text_var("source_y_var", "0.0")
        _set_text_var("source_z_var", "0.0")
        _set_text_var("source_l_var", "0.0")
        _set_text_var("source_m_var", "0.0")
        _set_text_var("source_n_var", "1.0")
        _set_text_var("field_type_var", "Angle")
        _set_text_var("field_value_var", "0.0")
        _set_text_var("field_count_var", "1")
        _set_text_var("aperture_type_var", "EPD")
        _set_text_var("aperture_value_var", "1.0")
        _set_text_var("trace_mode_var", "Non-Sequential Preview")
        _set_text_var("nonseq_ns_limit_var", "140" if is_mach_zehnder else "80")
        self.trace_mode = "Non-Sequential Preview"
        self.selected_analysis_modes = []
        self.analysis_mode = "none"
        self.secondary_analysis_mode = None
        try:
            self._sync_analysis_mode_buttons()
        except Exception:
            pass

        if is_mach_zehnder:
            return
        self._apply_michelson_family_example_metadata(is_twyman=is_twyman)

    def _apply_michelson_family_example_metadata(self, *, is_twyman: bool = False) -> None:
        title = "Twyman-Green" if is_twyman else "Michelson"
        splitter_name = "Twyman-Green splitter" if is_twyman else "Michelson splitter"
        interferogram_settings = {
            "analysis_title": f"{title} Interferogram",
            "detector_port": "cross",
            "detector_size_mm": 12.0,
            "pixels": 256,
            "fringe_tilt_x_mrad": 2.0 if is_twyman else 1.5,
            "fringe_tilt_y_mrad": 0.0,
            "opd_offset_um": 0.0,
            "visibility": 1.0,
            "coherence_mode": COHERENT_SUM_MODE_DEFAULT,
        }
        for row in self.rows:
            text = f"{getattr(row, 'name', '')} {getattr(row, 'element', '')}".strip().lower()
            advanced = dict(getattr(row, "advanced", {}) or {})
            if row.surface == BEAM_SPLITTER_SURFACE or "splitter" in text:
                row.surface = BEAM_SPLITTER_SURFACE
                row.element = splitter_name
                advanced[BEAM_SPLITTER_ADVANCED_ATTR] = _normalize_beam_splitter_settings(
                    advanced.get(BEAM_SPLITTER_ADVANCED_ATTR, BEAM_SPLITTER_DEFAULT_SETTINGS)
                )
                row.advanced = advanced
                self._set_element_metadata(
                    row,
                    {
                        "element_id": "BS1",
                        "element_name": splitter_name,
                        "arm_role": "Common",
                        "parent_splitter": "",
                    },
                )
                continue
            if row.surface == "Mirror" and ("transmit" in text or "test optic" in text):
                row.element = "Test optic" if is_twyman else "Transmit return mirror"
                row.advanced = advanced
                self._set_element_metadata(
                    row,
                    {
                        "element_id": "M_TX",
                        "element_name": row.element,
                        "arm_role": "Return",
                        "parent_splitter": "BS1",
                        "branch_selector": "transmit",
                        "arm_distance": 80.0,
                    },
                )
                continue
            if row.surface == "Mirror" and ("reflect" in text or "reference" in text):
                row.element = "Reference flat" if is_twyman else "Reflect return mirror"
                row.advanced = advanced
                self._set_element_metadata(
                    row,
                    {
                        "element_id": "M_RX",
                        "element_name": row.element,
                        "arm_role": "Return",
                        "parent_splitter": "BS1",
                        "branch_selector": "reflect",
                        "arm_distance": 80.0,
                    },
                )
                continue
            if row.surface == "Image" or "detector" in text or "output port" in text:
                row.element = "Detector path"
                advanced["Display2D"] = {
                    "plane_center": [50.0, -70.0],
                    "plane_tangent": [1.0, 0.0],
                    "branch_output_targets": {
                        "TT": [0.0, 0.0],
                        "TR": [50.0, -70.0],
                        "RT": [50.0, -70.0],
                        "RR": [0.0, 0.0],
                    },
                }
                advanced["Interferogram"] = interferogram_settings
                row.advanced = advanced
                self._set_element_metadata(
                    row,
                    {
                        "element_id": "DET_1",
                        "element_name": "Detector path",
                        "arm_role": "Detector",
                        "parent_splitter": "BS1",
                        "branch_selector": "reflect",
                        "arm_distance": 70.0,
                    },
                )

    @staticmethod
    def _example_requests_nonsequential(code: str) -> bool:
        return bool(re.search(r"\bNsTraceLoop\s*\(|\.\s*NsTrace\s*\(", code))

    def _set_results(self, items) -> None:
        self.results_table.delete(*self.results_table.get_children())
        measure = tkfont.nametofont("TkDefaultFont").measure
        property_width = measure("Property") + 18
        for key, value in items:
            self.results_table.insert("", "end", values=(key, value))
            property_width = max(property_width, measure(str(key)) + 18)
        self.results_table.column("property", width=min(property_width, 150), anchor="w", stretch=False)

    def append_debug(self, message: str) -> None:
        if not message:
            return
        line = message.rstrip()
        self.debug_text.insert("end", line + "\n")
        self.debug_text.see("end")
        self._append_debug_log(line)
        self.update_idletasks()

    def _bind_text_copy_shortcuts(self, widget: tk.Text) -> None:
        for sequence in ("<Control-c>", "<Control-C>", "<Control-Insert>", "<<Copy>>", "<Control-KeyPress-c>", "<Control-KeyPress-C>"):
            widget.bind(sequence, lambda _e, w=widget: self._copy_selection_from_text_widget(w), add="+")

    def _bind_text_context_menu(self, widget: tk.Text) -> None:
        widget.bind("<Button-3>", lambda e, w=widget: self._show_text_context_menu(e, w), add="+")

    def _bind_global_copy_shortcuts(self) -> None:
        for sequence in ("<Control-c>", "<Control-C>", "<Control-Insert>"):
            self.bind_all(sequence, self._copy_selection_from_focus, add="+")
        for sequence in ("<Control-v>", "<Control-V>", "<Shift-Insert>"):
            self.bind_all(sequence, self._paste_rows_from_focus, add="+")

    def _show_text_context_menu(self, event, widget: tk.Text):
        if self._text_popup_menu is None:
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Copy Selected", command=lambda: self._copy_selection_from_text_widget(widget))
            menu.add_command(label="Copy All", command=lambda: self._copy_all_from_text_widget(widget))
            self._text_popup_menu = menu
        else:
            self._text_popup_menu.entryconfigure(0, command=lambda: self._copy_selection_from_text_widget(widget))
            self._text_popup_menu.entryconfigure(1, command=lambda: self._copy_all_from_text_widget(widget))
        self._text_popup_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def _safe_focus_get(self):
        try:
            return self.focus_get()
        except (KeyError, tk.TclError):
            return None

    def _copy_selection_from_focus(self, _event=None):
        candidates = []
        focused = self._safe_focus_get()
        if focused is getattr(self, "table", None):
            return self.copy_selected_rows_to_clipboard(_event)
        if isinstance(focused, tk.Text):
            candidates.append(focused)
        for widget in (getattr(self, "debug_text", None), getattr(self, "progress_text", None)):
            if isinstance(widget, tk.Text) and widget not in candidates:
                candidates.append(widget)
        for widget in candidates:
            try:
                text = widget.get("sel.first", "sel.last")
            except tk.TclError:
                continue
            if not text:
                continue
            try:
                ok, backend = self._copy_text_to_clipboard(text)
                if ok:
                    self.status_var.set(f"Selected text copied to clipboard ({backend})")
                else:
                    self.status_var.set("Copy failed")
                return "break"
            except Exception as exc:
                self.append_debug(f"Copy selected text failed: {exc}")
                return "break"
        return None

    def _paste_rows_from_focus(self, _event=None):
        focused = self._safe_focus_get()
        if focused is getattr(self, "table", None):
            return self.paste_rows_from_clipboard(_event)
        return None

    def _copy_selection_from_text_widget(self, widget: tk.Text) -> str:
        try:
            text = widget.get("sel.first", "sel.last")
        except tk.TclError:
            self.status_var.set("No text selected")
            return "break"
        if not text:
            self.status_var.set("No text selected")
            return "break"
        try:
            ok, backend = self._copy_text_to_clipboard(text)
            if ok:
                self.status_var.set(f"Selected text copied to clipboard ({backend})")
            else:
                self.status_var.set("Copy failed")
        except Exception as exc:
            self.append_debug(f"Copy selected text failed: {exc}")
        return "break"

    def _copy_all_from_text_widget(self, widget: tk.Text) -> str:
        text = widget.get("1.0", "end-1c")
        if not text:
            self.status_var.set("No text to copy")
            return "break"
        try:
            ok, backend = self._copy_text_to_clipboard(text)
            if ok:
                self.status_var.set(f"All text copied to clipboard ({backend})")
            else:
                self.status_var.set("Copy failed")
        except Exception as exc:
            self.append_debug(f"Copy all text failed: {exc}")
        return "break"

    def _copy_text_to_clipboard(self, text: str) -> tuple[bool, str]:
        tools = (
            ("wl-copy", ["wl-copy"]),
            ("xclip", ["xclip", "-selection", "clipboard"]),
            ("xsel", ["xsel", "--clipboard", "--input"]),
        )
        encoded = text.encode("utf-8", errors="replace")
        for label, cmd in tools:
            if shutil.which(cmd[0]) is None:
                continue
            try:
                subprocess.run(cmd, input=encoded, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, label
            except Exception:
                continue
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
            return True, "Tk"
        except Exception:
            return False, "none"

    def copy_debug_to_clipboard(self) -> None:
        try:
            self._copy_all_from_text_widget(self.debug_text)
        except Exception as exc:
            self.append_debug(f"Copy debug failed: {exc}")

    def _phase2_report_text(self) -> str:
        summary = self._phase2_feature_summary()
        lines = [
            "# KrakenOS UI Phase 2 Report",
            "",
            f"Source: {summary['source_summary']}",
            f"Error-map surfaces: {summary['error_map_count']}",
        ]
        for row_text in summary["error_map_rows"]:
            lines.append(f"- {row_text}")
        if summary["max_error_pv"] is not None:
            lines.append(f"Max error PV: {float(summary['max_error_pv']):.6g}")
            lines.append(f"Max error RMS: {float(summary['max_error_rms']):.6g}")
        lines.extend(
            [
                f"Coating surfaces: {summary['coating_count']}",
            ]
        )
        for row_text in summary["coating_rows"]:
            lines.append(f"- {row_text}")
        lines.append(f"Metal catalogs: {summary['metal_catalog_count']}")
        for index, metal in enumerate(getattr(self, "metal_catalogs", []) or []):
            name = str(metal.get("name", f"Metal {index}")) if isinstance(metal, dict) else str(metal)
            lines.append(f"- {index}: {name}")
        return "\n".join(lines).strip() + "\n"

    def copy_phase2_report_to_clipboard(self) -> None:
        try:
            text = self._phase2_report_text()
            ok, backend = self._copy_text_to_clipboard(text)
            self.append_debug(text)
            if ok:
                self.status_var.set(f"Phase 2 report copied to clipboard ({backend}).")
            else:
                self.status_var.set("Phase 2 report written to Debug; clipboard unavailable.")
        except Exception as exc:
            self.append_debug(f"Phase 2 report failed: {exc}")

    def copy_wavefront_fit_report_to_clipboard(self) -> None:
        try:
            text = str(getattr(self, "_last_wavefront_fit_report", "")).strip()
            if not text:
                self.status_var.set("Run Zernike analysis before copying the wavefront fit report.")
                return
            text = "# KrakenOS UI Wavefront Fit Report\n\n" + text + "\n"
            ok, backend = self._copy_text_to_clipboard(text)
            self.append_debug(text)
            if ok:
                self.status_var.set(f"Wavefront fit report copied to clipboard ({backend}).")
            else:
                self.status_var.set("Wavefront fit report written to Debug; clipboard unavailable.")
        except Exception as exc:
            self.append_debug(f"Wavefront fit report failed: {exc}")

    def export_wavefront_csv(self) -> None:
        rows = list(getattr(self, "_last_wavefront_samples", []) or [])
        if not rows:
            messagebox.showinfo("Export Wavefront CSV", "Run Wavefront or Zernike analysis before exporting wavefront samples.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            title="Export Wavefront Samples CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self,
        )
        if not path:
            return
        columns = (
            "sample",
            "x_pupil",
            "y_pupil",
            "phase_waves",
            "display_value",
            "zemax_reference_waves",
            "zemax_residual_waves",
            "zemax_reference_file",
            "reconstructed_waves",
            "residual_waves",
            "style",
            "phase_method",
            "wavelength_um",
        )
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        self.status_var.set(f"Wavefront samples CSV exported: {Path(path).name}")

    def export_zernike_csv(self) -> None:
        rows = list(getattr(self, "_last_zernike_coefficients", []) or [])
        if not rows:
            messagebox.showinfo("Export Zernike CSV", "Run Zernike analysis before exporting coefficients.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            title="Export Zernike Coefficients CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self,
        )
        if not path:
            return
        columns = (
            "index",
            "label",
            "coefficient_waves",
            "terms",
            "samples",
            "phase_method",
            "phase_pv_waves",
            "phase_rms_waves",
            "residual_rms_waves",
            "residual_pv_waves",
            "rms_chief_waves",
            "rms_centroid_waves",
            "fitting_error_waves",
            "wavelength_um",
        )
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        self.status_var.set(f"Zernike coefficients CSV exported: {Path(path).name}")

    def _reset_debug_log(self) -> None:
        try:
            DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            DEBUG_LOG_PATH.write_text("", encoding="utf-8")
        except Exception:
            pass

    def _append_debug_log(self, line: str) -> None:
        try:
            with DEBUG_LOG_PATH.open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except Exception:
            pass

    def append_progress(self, message: str) -> None:
        if not message:
            return
        self.progress_text.insert("end", message.rstrip() + "\n")
        self.progress_text.see("end")
        self.update_idletasks()

    def _begin_analysis_progress(self, label: str) -> None:
        if self.optimization_running:
            return
        self.progress_spinner_var.set("...")
        self.progress_percent_var.set("working")
        self.progress_bar_var.set(0.0)
        self.append_progress(f"{label} started.")

    def _update_analysis_progress(self, label: str, done: int | None = None, total: int | None = None) -> None:
        if self.optimization_running:
            return
        frames = ("|", "/", "-", "\\")
        self.progress_spinner_var.set(frames[self._spinner_phase % len(frames)])
        self._spinner_phase += 1
        if done is not None and total is not None and total > 0:
            percent = max(0.0, min(100.0, (done / total) * 100.0))
            self.progress_percent_var.set(f"{int(percent)}% ({done}/{total})")
            self.progress_bar_var.set(percent)
        else:
            self.progress_percent_var.set(label)
        self.update_idletasks()

    def _finish_analysis_progress(self, label: str, success: bool = True) -> None:
        if self.optimization_running:
            return
        self.progress_spinner_var.set("ok" if success else "err")
        self.progress_percent_var.set("100%" if success else "failed")
        self.progress_bar_var.set(100.0 if success else 0.0)
        self.append_progress(f"{label} {'completed' if success else 'failed'}.")

    def _set_analysis_parallel_status(self, label: str, workers: int = 1, parallel_capable: bool = False) -> None:
        self._last_analysis_label = str(label)
        self._last_analysis_workers = max(1, int(workers))
        self._last_analysis_parallel_capable = bool(parallel_capable)
        self._last_analysis_accelerator = "CPU"

    def _set_analysis_accelerator(self, label: str) -> None:
        self._last_analysis_accelerator = str(label)

    def _analysis_parallel_summary(self) -> str:
        workers = max(1, int(self._last_analysis_workers))
        if workers <= 1:
            return "workers: 1"
        if self._last_analysis_parallel_capable:
            return f"workers: {workers} (parallel)"
        return f"workers: {workers}"

    def _analysis_compute_summary(self) -> str:
        return f"{self._analysis_parallel_summary()} | {self._last_analysis_accelerator}"

    def _report_compute_backends(self) -> None:
        if self._gpu_backend_reported:
            return
        self._gpu_backend_reported = True
        backend_pref = os.getenv("KRAKEN_POSTPROC_BACKEND", "auto").strip().lower()
        if backend_pref not in {"auto", "torch", "cupy", "cpu"}:
            backend_pref = "auto"
        self.append_debug(f"Post-processing backend preference: {backend_pref}")

        torch = _optional_torch()
        if torch is None:
            self.append_debug("Torch backend: unavailable.")
        else:
            try:
                if bool(torch.cuda.is_available()):
                    self.append_debug(f"Torch backend: CUDA available ({torch.cuda.device_count()} device(s)).")
                else:
                    self.append_debug("Torch backend: installed, CUDA not available.")
            except Exception as exc:
                self.append_debug(f"Torch backend: probe failed: {exc}")

        cp = _optional_cupy()
        if cp is None:
            self.append_debug("GPU backend: CuPy unavailable, PSF/MTF post-processing will use CPU.")
            return
        try:
            device_count = int(cp.cuda.runtime.getDeviceCount())
        except Exception:
            device_count = 0
        if device_count > 0:
            self.append_debug(f"GPU backend: CuPy available, detected {device_count} CUDA device(s).")
        else:
            self.append_debug("GPU backend: CuPy import succeeded, but no CUDA devices were detected.")

    def _update_progress_indicators(self) -> None:
        if not self.optimization_running or self.optimization_context is None:
            self.progress_spinner_var.set("idle")
            self.progress_percent_var.set("0%")
            self.progress_bar_var.set(0.0)
            return
        done = int(self.optimization_context.get("generation_done", 0))
        total = max(1, int(self.optimization_context.get("generations_total", 1)))
        percent = max(0.0, min(100.0, (done / total) * 100.0))
        self.progress_percent_var.set(f"{int(percent)}% ({done}/{total})")
        self.progress_bar_var.set(percent)

    @staticmethod
    def _pick_image_plane_data(rays):
        try:
            X, Y, Z, L, M, N = rays.pick(-1, coordinates="local")
            if np.asarray(X).size:
                return X, Y, Z, L, M, N
        except Exception:
            pass
        return rays.pick(-1)

    def _build_analysis_rays(
        self,
        system,
        wavelength: float,
        sample_count: int | None = None,
        pattern: str = "hexapolar",
        *,
        surface_index: int | None = None,
        aperture_type: str | None = None,
        aperture_value: float | None = None,
        field_type: str | None = None,
        field_x: float | None = None,
        field_y: float | None = None,
    ):
        rays = Kos.raykeeper(system)
        random_source_bundle = self._build_random_source_bundle(sample_count)
        if random_source_bundle is not None:
            Kos.TraceLoop(*random_source_bundle, wavelength, rays, clean=1)
            return rays
        pupil = Kos.PupilCalc(
            system,
            self._analysis_surface_index() if surface_index is None else int(surface_index),
            wavelength,
            self._current_aperture_type() if aperture_type is None else str(aperture_type),
            self._current_aperture_value() if aperture_value is None else float(aperture_value),
        )
        pupil.Samp = max(2, int(sample_count if sample_count is not None else self._current_ray_count()))
        pupil.Ptype = self._current_analysis_pupil_pattern(pattern) if pattern == "hexapolar" else pattern

        clean = 1
        resolved_field_type = field_type or ("angle" if self._current_object_mode() == "Infinity" else "height")
        resolved_field_x = 0.0 if field_x is None else float(field_x)
        resolved_field_y = field_y
        if resolved_field_type == "angle":
            pupil.FieldType = "angle"
            field_values = (
                [float(resolved_field_y)]
                if resolved_field_y is not None
                else self._sample_field_values(self._current_field_angle_deg())
            )
            for value in field_values:
                pupil.FieldX = resolved_field_x
                pupil.FieldY = float(value)
                x, y, z, L, M, N = self._pupil_pattern_bundle(pupil)
                Kos.TraceLoop(x, y, z, L, M, N, wavelength, rays, clean=clean)
                clean = 0
        else:
            pupil.FieldType = "height"
            field_values = (
                [float(resolved_field_y)]
                if resolved_field_y is not None
                else self._sample_field_values(self._current_field_height())
            )
            for value in field_values:
                pupil.FieldX = resolved_field_x
                pupil.FieldY = float(value)
                x, y, z, L, M, N = self._pupil_pattern_bundle(pupil)
                Kos.TraceLoop(x, y, z, L, M, N, wavelength, rays, clean=clean)
                clean = 0
        return rays

    def _serializable_row_specs(self) -> list[dict]:
        return self._serializable_specs_for_rows(self.rows)

    def _serializable_specs_for_rows(self, rows: list[SurfaceRow]) -> list[dict]:
        metal_catalogs = _normalize_metal_catalog_specs(getattr(self, "metal_catalogs", []))
        specs = surface_rows_to_specs(rows, metal_catalogs=metal_catalogs)
        for row, spec in zip(rows, specs):
            if KrakenLayoutEditor._is_open3d_promoted_optical_solid_row(row):
                spec["axis_move"] = 0.0
        return specs

    def _mtf_worker_count(self, ray_count: int) -> int:
        cpu_total = max(1, int(os.cpu_count() or 1))
        if ray_count <= 1 or cpu_total <= 1:
            return 1
        optimization_workers_var = self.__dict__.get("optimization_workers_var")
        if optimization_workers_var is not None:
            selected = optimization_workers_var.get().strip()
            if selected and selected.lower() != "auto":
                try:
                    parsed = int(selected)
                    if parsed > 0:
                        return self._cap_analysis_worker_count(max(1, min(parsed, cpu_total, ray_count)))
                except ValueError:
                    pass
        if ray_count < 2048:
            return 1
        auto_workers = self._optimization_worker_count()
        requested = max(1, min(auto_workers, cpu_total, ray_count, max(1, ray_count // 2048)))
        return self._cap_analysis_worker_count(requested)

    def _optimization_worker_count(self) -> int:
        cpu_total = max(1, int(os.cpu_count() or 1))
        optimization_workers_var = self.__dict__.get("optimization_workers_var")
        if optimization_workers_var is not None:
            selected = optimization_workers_var.get().strip()
            if selected and selected.lower() != "auto":
                try:
                    parsed = int(selected)
                    if parsed > 0:
                        return self._cap_analysis_worker_count(max(1, min(parsed, cpu_total)))
                except ValueError:
                    pass
        configured = os.getenv("KRAKEN_OPT_WORKERS", "").strip()
        if configured:
            try:
                parsed = int(configured)
                if parsed > 0:
                    return self._cap_analysis_worker_count(max(1, min(parsed, cpu_total)))
            except ValueError:
                pass
        requested = 1 if cpu_total <= 1 else max(2, cpu_total - 1)
        return self._cap_analysis_worker_count(requested)

    def _optimization_parallel_enabled(self) -> bool:
        parallel_pref = os.getenv("KRAKEN_OPT_PARALLEL", "1").strip().lower()
        return parallel_pref not in {"0", "false", "off", "no"}

    def _optimization_preflight_messages(
        self,
        merit: MeritFunction | None,
        variables: list[OpticalVariable] | None,
        optimization_workers: int,
        parallel_enabled: bool,
    ) -> tuple[bool, list[str]]:
        backend_ok, backend_message = probe_pygmo_backend()
        messages = [
            ("Optimization backend available: " if backend_ok else "Optimization backend unavailable: ")
            + backend_message
        ]
        if merit is not None and variables is not None:
            messages.append(
                "Optimization preflight: "
                f"variables={len(variables)}, operands={len(merit.operands)}, "
                f"workers={max(1, int(optimization_workers))}."
            )
            has_mtf_operand = any(isinstance(operand, MTFAtFrequencyOperand) for operand in merit.operands)
            if has_mtf_operand and int(optimization_workers) > 1:
                messages.append(
                    "Optimization preflight: MTF operands use internal MTF chunk workers "
                    "instead of pygmo mp_bfe."
                )
            elif parallel_enabled and int(optimization_workers) > 1:
                messages.append("Optimization preflight: pygmo mp_bfe parallel population evaluation is enabled.")
            elif not parallel_enabled:
                messages.append(
                    "Optimization preflight: KRAKEN_OPT_PARALLEL disables "
                    "pygmo mp_bfe parallel evaluation."
                )
        return backend_ok, messages

    def check_optimization_backend(self) -> None:
        parallel_enabled = self._optimization_parallel_enabled()
        optimization_workers = self._optimization_worker_count() if parallel_enabled else 1
        ok, messages = self._optimization_preflight_messages(None, None, optimization_workers, parallel_enabled)
        for message in messages:
            self.append_progress(message)
        if ok:
            self.status_var.set("Optimization backend available.")
        else:
            self.status_var.set("Optimization backend unavailable.")

    @staticmethod
    def _available_memory_bytes() -> int:
        if os.name == "posix":
            try:
                with open("/proc/meminfo", "r", encoding="utf-8") as handle:
                    for line in handle:
                        if line.startswith("MemAvailable:"):
                            parts = line.split()
                            if len(parts) >= 2:
                                return max(0, int(parts[1])) * 1024
            except Exception:
                pass
        return 0

    def _cap_analysis_worker_count(self, requested: int) -> int:
        requested = max(1, int(requested))
        available = self._available_memory_bytes()
        if available <= 0:
            return requested
        reserve_mb = max(1024, int(os.getenv("KRAKEN_ANALYSIS_RESERVE_MB", "2048") or 2048))
        per_worker_mb = max(128, int(os.getenv("KRAKEN_ANALYSIS_WORKER_MB", "768") or 768))
        usable = max(0, available - reserve_mb * 1024 * 1024)
        memory_limited = max(1, usable // (per_worker_mb * 1024 * 1024)) if usable > 0 else 1
        return max(1, min(requested, int(memory_limited)))

    def _ensure_analysis_executor(self, worker_count: int) -> ProcessPoolExecutor | None:
        worker_count = self._cap_analysis_worker_count(max(1, int(worker_count)))
        if worker_count <= 1:
            return None
        analysis_executor = self.__dict__.get("_analysis_executor")
        analysis_executor_workers = int(self.__dict__.get("_analysis_executor_workers", 0) or 0)
        if analysis_executor is not None and analysis_executor_workers == worker_count:
            return analysis_executor
        self._shutdown_analysis_executor()
        mp_context = None
        if os.name == "posix":
            try:
                mp_context = mp.get_context("spawn")
            except Exception:
                mp_context = None
        if mp_context is not None:
            self._analysis_executor = ProcessPoolExecutor(max_workers=worker_count, mp_context=mp_context)
        else:
            self._analysis_executor = ProcessPoolExecutor(max_workers=worker_count)
        self._analysis_executor_workers = worker_count
        return self._analysis_executor

    def _shutdown_analysis_executor(self) -> None:
        analysis_executor = self.__dict__.get("_analysis_executor")
        if analysis_executor is not None:
            processes = list(getattr(analysis_executor, "_processes", {}).values())
            try:
                analysis_executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            for process in processes:
                if process is None:
                    continue
                try:
                    if process.is_alive():
                        process.terminate()
                except Exception:
                    pass
            deadline = time.monotonic() + 0.5
            for process in processes:
                if process is None:
                    continue
                try:
                    remaining = max(0.0, deadline - time.monotonic())
                    process.join(timeout=remaining)
                except Exception:
                    pass
            for process in processes:
                if process is None:
                    continue
                try:
                    if process.is_alive():
                        process.kill()
                except Exception:
                    pass
                try:
                    process.join(timeout=0.1)
                except Exception:
                    pass
            self._analysis_executor = None
            self._analysis_executor_workers = 0

    @staticmethod
    def _terminate_process_group(pid: int, *, force: bool = False) -> None:
        if pid <= 0 or os.name != "posix":
            return
        signals = (signal.SIGTERM, signal.SIGKILL) if force else (signal.SIGTERM,)
        for sig in signals:
            try:
                os.killpg(pid, sig)
            except ProcessLookupError:
                return
            except Exception:
                break
            if sig == signal.SIGTERM:
                time.sleep(0.05)

    def _shutdown_optimization_worker(self, force: bool = False) -> None:
        if self._optimization_stop_event is not None:
            try:
                self._optimization_stop_event.set()
            except Exception:
                pass
        process = self._optimization_process
        if process is not None:
            try:
                process.join(timeout=0.15)
            except Exception:
                pass
            try:
                if force and process.is_alive():
                    self._terminate_process_group(int(process.pid or 0), force=True)
            except Exception:
                pass
            try:
                if process.is_alive():
                    process.join(timeout=0.15)
            except Exception:
                pass
            try:
                if not process.is_alive():
                    process.close()
            except Exception:
                pass
        queue = self._optimization_queue
        if queue is not None:
            try:
                queue.close()
            except Exception:
                pass
        self._optimization_process = None
        self._optimization_queue = None
        self._optimization_stop_event = None


    def _pupil_model_inputs(
        self,
        system,
        *,
        build_reference: bool,
    ) -> tuple[object, list[SurfaceRow], int]:
        pupil_system = system
        pupil_rows = self.rows
        if build_reference and any(row.surface == "Mirror" for row in self.rows):
            pupil_rows, _last_source_index = self._paraxial_reference_rows_for_layout(self.rows)
            pupil_system = _build_system_from_specs(self._serializable_specs_for_rows(pupil_rows), build=0)
        pupil_surface_index = self._pupil_surface_index_for_rows(pupil_rows)
        return pupil_system, pupil_rows, pupil_surface_index

    def _start_progress_spinner(self) -> None:
        if self._spinner_after_id is not None:
            self.after_cancel(self._spinner_after_id)
            self._spinner_after_id = None
        self._spinner_phase = 0
        self._animate_progress_spinner()

    def _stop_progress_spinner(self) -> None:
        if self._spinner_after_id is not None:
            self.after_cancel(self._spinner_after_id)
            self._spinner_after_id = None
        if not self.optimization_running:
            self.progress_spinner_var.set("idle")

    def _animate_progress_spinner(self) -> None:
        if not self.optimization_running:
            self._spinner_after_id = None
            self.progress_spinner_var.set("idle")
            return
        frames = ("|", "/", "-", "\\")
        self.progress_spinner_var.set(frames[self._spinner_phase % len(frames)])
        self._spinner_phase += 1
        self._spinner_after_id = self.after(120, self._animate_progress_spinner)

    @staticmethod
    def _optional_finite_float(value) -> float | None:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if not np.isfinite(numeric):
            return None
        return float(numeric)

    @classmethod
    def _format_optional_float(cls, value, fmt: str = ".4g", *, scale: float = 1.0, suffix: str = "") -> str:
        numeric = cls._optional_finite_float(value)
        if numeric is None:
            return "Unavailable"
        return f"{numeric * float(scale):{fmt}}{suffix}"

    def _field_launch_sample_summary(self) -> dict[str, object]:
        requested = max(1, int(self._requested_field_count()))
        basis, unit, span = self._field_sampling_basis_span()
        sign = -1.0 if basis == "angle" and float(self._current_field_angle_deg()) < 0.0 else 1.0
        if basis == "object height":
            sign = -1.0 if float(self._current_field_height()) < 0.0 else 1.0
        maximum = float(span) * sign
        active = self._field_sampling_is_active()
        values = [float(value) for value in self._sample_field_values(maximum)] if active else [0.0]
        if not values:
            values = [0.0]
        unique_values = sorted({round(float(value), 12) for value in values})
        effective = max(1, len(unique_values))
        return {
            "requested": requested,
            "effective": effective,
            "basis": basis,
            "unit": unit,
            "min": float(min(values)),
            "max": float(max(values)),
            "overlap": requested > 1 and effective == 1,
            "active": active,
        }

    def _source_sampling_diagnostics(self, trace_summary: dict | None = None) -> list[tuple[str, str]]:
        diagnostics: list[tuple[str, str]] = []
        if self._current_source_model() != SOURCE_MODEL_DEFAULT:
            return diagnostics

        field_summary = self._field_launch_sample_summary()
        if bool(field_summary.get("overlap")):
            diagnostics.append(
                (
                    "Field sampling note",
                    (
                        f"{field_summary['requested']} requested field samples collapse to "
                        f"{field_summary['effective']} effective on-axis field because the "
                        f"{field_summary['basis']} span is 0 {field_summary['unit']}; "
                        "use a nonzero field value to launch distinct field bundles."
                    ),
                )
            )

        if not self._is_full_pupil_mode():
            pattern = self._current_pupil_pattern_label()
            if pattern in {PUPIL_PATTERN_DEFAULT, "Fan X", "Fan Y"}:
                diagnostics.append(
                    (
                        "Projection sampling note",
                        (
                            f"{pattern} uses the shared 3D envelope for layout projections; "
                            "use Full Pupil for denser pupil fills or explicit section diagnostics for dense YZ/XZ slices."
                        ),
                    )
                )

        active = ""
        if trace_summary:
            active = str(trace_summary.get("active", "") or "")
        if (
            self._current_object_mode() == "Finite"
            and float(self._current_source_cone_angle()) > 1e-12
            and active.lower().startswith("sequential")
        ):
            diagnostics.append(
                (
                    "Source cone note",
                    "Sequential Pupil / field ignores Source cone angle; finite-object cone angle comes from object distance and the entrance pupil. Use a physical source or non-sequential scene for explicit source half-angle.",
                )
            )
        return diagnostics


    @staticmethod
    def _optimization_bounds(parameter: str, value: float) -> tuple[float, float]:
        for spec in VARIABLE_REGISTRY.values():
            if spec.parameter == parameter:
                return spec.default_bounds(value)
        raise ValueError(f"Unsupported optimization parameter: {parameter}")

    @staticmethod
    def _variable_spec_for_field(field: str):
        return VARIABLE_REGISTRY.get(field)

    @staticmethod
    def _variable_spec_for_parameter(parameter: str):
        for spec in VARIABLE_REGISTRY.values():
            if _native_variable_matches(spec.parameter, parameter):
                return spec
        return None

    @classmethod
    def _optimization_value_from_row(cls, row: SurfaceRow, variable: OpticalVariable) -> float:
        spec = cls._variable_spec_for_parameter(variable.parameter)
        if spec is not None:
            return spec.value_from_row(row)
        if hasattr(row, str(variable.parameter)):
            return float(getattr(row, str(variable.parameter)))
        raise ValueError(f"Unsupported optimization parameter: {variable.parameter}")

    @classmethod
    def _apply_optimization_value_to_row(cls, row: SurfaceRow, variable: OpticalVariable, value: float) -> None:
        spec = cls._variable_spec_for_parameter(variable.parameter)
        if spec is not None:
            setattr(row, spec.field, float(value))
            return
        if hasattr(row, str(variable.parameter)):
            setattr(row, str(variable.parameter), float(value))
            return
        raise ValueError(f"Unsupported optimization parameter: {variable.parameter}")

    @staticmethod
    def _merit_spec_for_label(label: str):
        for spec in OPERAND_REGISTRY.values():
            if spec.label == label:
                return spec
        return None

    def _selected_operand_specs(self) -> list:
        if "merit_mode_list" in self.__dict__:
            labels = [self.merit_mode_list.get(i) for i in self.merit_mode_list.curselection()]
        else:
            labels = [str(label) for label in getattr(self, "_headless_selected_operand_labels", [])]
        specs = []
        for label in labels:
            spec = self._merit_spec_for_label(label)
            if spec is not None:
                specs.append(spec)
        return specs

    def _operand_weight(self, label: str) -> float:
        var = self.operand_weight_vars.get(label)
        if var is None:
            spec = self._merit_spec_for_label(label)
            return 1.0 if spec is None else spec.default_weight
        try:
            return float(var.get())
        except ValueError:
            spec = self._merit_spec_for_label(label)
            return 1.0 if spec is None else spec.default_weight

    def _operand_target(self, label: str) -> float:
        var = self.operand_target_vars.get(label)
        if var is None:
            spec = self._merit_spec_for_label(label)
            return 0.0 if spec is None else spec.default_target
        try:
            return float(var.get())
        except ValueError:
            spec = self._merit_spec_for_label(label)
            return 0.0 if spec is None else spec.default_target

    def _operand_wavelength(self, label: str) -> float:
        var = self.operand_wavelength_vars.get(label)
        if var is None:
            return self._current_wavelength()
        try:
            return float(var.get())
        except ValueError:
            return self._current_wavelength()

    def _operand_field(self, label: str) -> float:
        var = self.operand_field_vars.get(label)
        if var is None:
            return 0.0
        try:
            return float(var.get())
        except ValueError:
            return 0.0

    def _operand_field_x(self, label: str) -> float:
        var = self.operand_field_x_vars.get(label)
        if var is None:
            return 0.0
        try:
            return float(var.get())
        except ValueError:
            return 0.0

    def _operand_field_y(self, label: str) -> float:
        var = self.operand_field_y_vars.get(label)
        if var is not None:
            try:
                return float(var.get())
            except ValueError:
                return 0.0
        return self._operand_field(label)

    def _operand_field_type(self, label: str) -> str:
        if self._current_object_mode() == "Infinity":
            return "angle"
        return "height"

    def _resolved_field_coordinate(self, field_basis: str, raw_value: float, resolved_field_type: str) -> float:
        metrics = self._field_metrics_for_value(field_basis, raw_value)
        if resolved_field_type == "angle":
            return float(metrics["angle_deg"])
        return float(metrics["object_height"])

    def _resolved_mtf_field_samples(self, label: str) -> list[dict[str, float | str]]:
        field_basis = self._current_field_type()
        resolved_field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
        basis_label = self._field_type_display_label(field_basis)
        if field_basis == "Angle" and resolved_field_type == "height":
            basis_label = "Field Half-Angle -> Object Semi-Height"
        unit = self._field_type_unit(field_basis)
        raw_x = 0.0
        resolved_x = 0.0
        raw_limit = abs(float(self._current_field_value()))
        count = max(1, self._current_field_count())
        if raw_limit <= 1e-9:
            raw_values = [0.0]
        elif count == 1:
            raw_values = [float(raw_limit)]
        else:
            raw_values = list(np.linspace(0.0, float(raw_limit), count))

        samples: list[dict[str, float | str]] = []
        for raw_value in raw_values:
            resolved_y = self._resolved_field_coordinate(field_basis, raw_value, resolved_field_type)
            samples.append(
                {
                    "basis": basis_label,
                    "unit": unit,
                    "display_x": float(raw_x),
                    "display_y": float(raw_value),
                    "field_type": resolved_field_type,
                    "field_x": float(resolved_x),
                    "field_y": float(resolved_y),
                    "legend": f"{self._format_field_sample_value(raw_value)} {unit}".strip(),
                }
            )
        return samples

    def _resolved_positive_field_samples(self) -> list[dict[str, float | str]]:
        field_basis = self._current_field_type()
        resolved_field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
        unit = self._field_type_unit(field_basis)
        raw_limit = abs(float(self._current_field_value()))
        count = max(1, self._current_field_count())
        if count == 1:
            raw_values = [raw_limit]
        else:
            raw_values = list(np.linspace(0.0, raw_limit, count))
        samples: list[dict[str, float | str]] = []
        for raw_value in raw_values:
            resolved_y = self._resolved_field_coordinate(field_basis, raw_value, resolved_field_type)
            samples.append(
                {
                    "basis": self._field_type_display_label(field_basis),
                    "unit": unit,
                    "display_y": float(raw_value),
                    "field_type": resolved_field_type,
                    "field_x": 0.0,
                    "field_y": float(resolved_y),
                    "legend": f"{self._format_field_sample_value(raw_value)} {unit}".strip(),
                }
            )
        return samples

    def _resolved_field_grid_samples(self) -> list[dict[str, float | str]]:
        field_basis = self._current_field_type()
        resolved_field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
        basis_label = self._field_type_display_label(field_basis)
        unit = self._field_type_unit(field_basis)
        raw_limit = abs(float(self._current_field_value()))
        count = max(3, self._current_field_count())
        if raw_limit <= 1e-9:
            raw_values = [0.0]
        else:
            raw_values = list(np.linspace(-raw_limit, raw_limit, count))
        samples: list[dict[str, float | str]] = []
        seen: set[tuple[float, float]] = set()
        for raw_y in raw_values:
            for raw_x in raw_values:
                key = (round(float(raw_x), 12), round(float(raw_y), 12))
                if key in seen:
                    continue
                seen.add(key)
                resolved_x = self._resolved_field_coordinate(field_basis, float(raw_x), resolved_field_type)
                resolved_y = self._resolved_field_coordinate(field_basis, float(raw_y), resolved_field_type)
                samples.append(
                    {
                        "basis": basis_label,
                        "unit": unit,
                        "display_x": float(raw_x),
                        "display_y": float(raw_y),
                        "field_type": resolved_field_type,
                        "field_x": float(resolved_x),
                        "field_y": float(resolved_y),
                    }
                )
        return samples

    def _operand_surface_index(self, label: str) -> int:
        var = self.operand_surface_vars.get(label)
        if var is None:
            return self._analysis_surface_index()
        value = var.get().strip()
        if not value or value == "Auto":
            return self._analysis_surface_index()
        try:
            return int(value.split(":", 1)[0].strip())
        except ValueError:
            return self._analysis_surface_index()

    def _operand_aperture_type(self, label: str) -> str:
        var = self.operand_aperture_type_vars.get(label)
        if var is None:
            return self._current_aperture_type()
        value = var.get().strip().upper()
        if value == "FNO":
            return "EPD"
        return value if value in {"STOP", "EPD"} else self._current_aperture_type()

    def _operand_aperture_value(self, label: str) -> float:
        var = self.operand_aperture_value_vars.get(label)
        if var is None:
            return self._current_aperture_value()
        try:
            value = float(var.get())
        except ValueError:
            return self._current_aperture_value()
        return value if value != 0.0 else self._current_aperture_value()

    def _build_optimization_variables(self) -> list[OpticalVariable]:
        variables: list[OpticalVariable] = []
        for index, row in enumerate(self.rows):
            if row.surface == "Image":
                continue
            for spec in VARIABLE_REGISTRY.values():
                if not spec.is_supported(row) or not self._variable_enabled_for_row(row, spec):
                    continue
                value = spec.value_from_row(row)
                lower, upper = spec.get_bounds(row) or spec.default_bounds(value)
                variables.append(
                    OpticalVariable(
                        index,
                        spec.parameter,
                        lower,
                        upper,
                        name=f"{row.name} {spec.label}",
                    )
                )
        return variables

    def _build_merit_function(self) -> MeritFunction:
        selected_specs = self._selected_operand_specs()
        if not selected_specs:
            return MeritFunction(operands=[])
        operands = []
        for spec in selected_specs:
            operands.extend(spec.build_merit_function(self).operands)
        return MeritFunction(operands=operands)

    def _build_tolerance_merit_function(self) -> tuple[MeritFunction, list[str]]:
        for attr_name in (
            "operand_weight_vars",
            "operand_target_vars",
            "operand_wavelength_vars",
            "operand_field_vars",
            "operand_field_x_vars",
            "operand_field_y_vars",
            "operand_surface_vars",
            "operand_aperture_type_vars",
            "operand_aperture_value_vars",
            "operand_frequency_vars",
            "operand_mtf_mode_vars",
            "operand_mtf_algorithm_vars",
        ):
            self.__dict__.setdefault(attr_name, {})
        selected_specs = self._selected_operand_specs()
        if selected_specs:
            operands = []
            labels = []
            for spec in selected_specs:
                labels.append(str(spec.label))
                operands.extend(spec.build_merit_function(self).operands)
            return MeritFunction(operands=operands), labels
        default_spec = self._merit_spec_for_label("Spot RMS")
        if default_spec is None:
            return MeritFunction(operands=[]), []
        return default_spec.build_merit_function(self), [str(default_spec.label)]

    @staticmethod

    def start_optimization(self) -> None:
        if self.optimization_running:
            return
        self._read_rows_from_table()
        variables = self._build_optimization_variables()
        if not variables:
            self.append_progress("Optimization skipped: no optimization variables marked.")
            return

        try:
            system = self.build_system()
        except Exception as exc:
            self.append_progress(f"Optimization aborted: system build failed: {exc}")
            return

        merit_specs = self._selected_operand_specs()
        merit = self._build_merit_function()
        if not merit.operands:
            self.append_progress("Optimization aborted: no merit operands selected.")
            return

        x0 = []
        for variable in variables:
            row = self.rows[variable.surface_index]
            x0.append(self._optimization_value_from_row(row, variable))

        population_size = 12
        optimization_workers = 1
        parallel_enabled = self._optimization_parallel_enabled()
        if parallel_enabled:
            optimization_workers = self._optimization_worker_count()
        preflight_ok, preflight_messages = self._optimization_preflight_messages(
            merit,
            variables,
            optimization_workers,
            parallel_enabled,
        )
        for message in preflight_messages:
            self.append_progress(message)
        if not preflight_ok:
            self.status_var.set("Optimization backend unavailable.")
            return
        self.append_progress(
            "Optimization start | operands: "
            + ", ".join(spec.label for spec in merit_specs)
        )
        self.append_progress(f"Variables: {', '.join(v.normalized_name() for v in variables)}")
        self.status_var.set("Optimization starting...")
        self.append_progress("Preparing optimization worker...")
        self.optimization_running = True
        self.optimization_cancel_requested = False
        self.optimization_context = {
            "variables": variables,
            "champion_x": list(x0),
            "generations_total": 12,
            "generation_done": 0,
            "verbosity_every": 1,
            "workers": optimization_workers,
            "compute_backend": "pending",
            "initial_total": None,
            "last_best": None,
        }
        self._update_progress_indicators()
        self._start_progress_spinner()
        ctx = mp.get_context("spawn")
        self._optimization_queue = ctx.Queue()
        self._optimization_stop_event = ctx.Event()
        self._optimization_process = ctx.Process(
            target=_run_optimization_job,
            args=(
                self._optimization_queue,
                self._optimization_stop_event,
                self._serializable_row_specs(),
                merit,
                variables,
                list(map(float, x0)),
                int(self.optimization_context["generations_total"]),
                int(self.optimization_context["verbosity_every"]),
                int(population_size),
                int(optimization_workers),
                bool(parallel_enabled),
            ),
        )
        self._optimization_process.start()
        self.after(75, self._poll_optimization_worker)

    def stop_optimization(self) -> None:
        if not self.optimization_running:
            self.append_progress("Stop ignored: no optimization is running.")
            return
        self.optimization_cancel_requested = True
        if self._optimization_stop_event is not None:
            try:
                self._optimization_stop_event.set()
            except Exception:
                pass
        self.append_progress("Stop requested. Applying the latest completed generation and terminating the worker.")
        partial_result = None
        if self.optimization_context is not None:
            partial_result = {
                "champion_x": list(self.optimization_context.get("champion_x", [])),
                "initial_total": self.optimization_context.get("initial_total"),
                "final_total": self.optimization_context.get("last_best", self.optimization_context.get("initial_total")),
                "compute_backend": self.optimization_context.get("compute_backend", "pending"),
                "workers": self.optimization_context.get("workers", 1),
                "operands": [],
            }
        self._finish_optimization(cancelled=True, result=partial_result)

    def _poll_optimization_worker(self) -> None:
        if not self.optimization_running or self.optimization_context is None:
            return

        ctx = self.optimization_context
        queue = self._optimization_queue
        process = self._optimization_process
        if queue is None or process is None:
            self.append_progress("Optimization failed: worker process not available.")
            self._finish_optimization(cancelled=True)
            return

        completed = False
        while True:
            try:
                payload = queue.get_nowait()
            except Empty:
                break

            message_type = str(payload.get("type", ""))
            if message_type == "bootstrap":
                for line in payload.get("debug_messages", []) or []:
                    self.append_debug(str(line))
                initial_total = float(payload.get("initial_total", 0.0))
                ctx["initial_total"] = initial_total
                ctx["compute_backend"] = str(payload.get("compute_backend", "sequential"))
                ctx["workers"] = max(1, int(payload.get("workers", 1)))
                self.status_var.set(f"Optimization running: initial merit = {initial_total:.6g}")
                self.append_progress(f"Initial merit: {initial_total:.6g}")
                self.append_progress(f"Optimization compute: {ctx['compute_backend']}")
            elif message_type == "generation":
                capture_text = str(payload.get("debug", ""))
                if capture_text:
                    self.append_debug(capture_text)
                ctx["generation_done"] = max(ctx["generation_done"], int(payload.get("generation_done", 0)))
                champion_x = list(payload.get("champion_x", []))
                if champion_x:
                    ctx["champion_x"] = champion_x
                self._update_progress_indicators()
                if "log_best" in payload:
                    ctx["last_best"] = float(payload.get("log_best", 0.0))
                    if (
                        ctx["generation_done"] == 1
                        or ctx["generation_done"] == ctx["generations_total"]
                        or ctx["generation_done"] % ctx["verbosity_every"] == 0
                    ):
                        self.append_progress(
                            "Gen {gen:>3} | fevals {fevals:>4} | best {best:.6g} | dx {dx:.6g} | df {df:.6g}".format(
                                gen=int(ctx["generation_done"]),
                                fevals=int(payload.get("log_fevals", 0)),
                                best=float(payload.get("log_best", 0.0)),
                                dx=float(payload.get("log_dx", 0.0)),
                                df=float(payload.get("log_df", 0.0)),
                            )
                        )
                    if champion_x:
                        for variable, value in zip(ctx["variables"], champion_x):
                            row = self.rows[variable.surface_index]
                            self._apply_optimization_value_to_row(row, variable, float(value))
                        self._sync_table()
                        self.status_var.set(
                            f"Optimization running: generation {ctx['generation_done']}/{ctx['generations_total']} | best merit = {ctx['last_best']:.6g}"
                        )
            elif message_type == "complete":
                self._finish_optimization(cancelled=bool(payload.get("cancelled", False)), result=payload)
                completed = True
                break
            elif message_type == "error":
                tb = str(payload.get("traceback", ""))
                if tb:
                    self.append_debug(tb)
                self.append_progress(f"Optimization failed: {payload.get('message', 'unknown error')}")
                self._finish_optimization(cancelled=True)
                completed = True
                break

        if completed:
            return
        if process.is_alive():
            self.after(75, self._poll_optimization_worker)
            return
        self.append_progress("Optimization worker exited unexpectedly.")
        self._finish_optimization(cancelled=True)

    def _finish_optimization(self, cancelled: bool, result: dict | None = None) -> None:
        self._shutdown_optimization_worker(force=bool(cancelled))
        if self.optimization_context is None:
            self.optimization_running = False
            self.optimization_cancel_requested = False
            self._stop_progress_spinner()
            return

        ctx = self.optimization_context
        if result is not None:
            champion_x = list(result.get("champion_x", []))
            ctx["champion_x"] = champion_x
            ctx["compute_backend"] = str(result.get("compute_backend", ctx.get("compute_backend", "sequential")))
            ctx["workers"] = max(1, int(result.get("workers", ctx.get("workers", 1))))
            if result.get("initial_total") is not None:
                ctx["initial_total"] = float(result["initial_total"])

        champion_x = list(ctx.get("champion_x", []))
        for variable, value in zip(ctx["variables"], champion_x):
            row = self.rows[variable.surface_index]
            self._apply_optimization_value_to_row(row, variable, float(value))

        self._sync_table()
        self.refresh_plot()
        initial_total = float(ctx.get("initial_total") or 0.0)
        final_total_value = initial_total
        if result is not None:
            candidate_final = result.get("final_total", initial_total)
            if candidate_final is not None:
                final_total_value = float(candidate_final)
        final_total = float(final_total_value)
        compute_backend = str(ctx.get("compute_backend", "sequential"))
        compute_workers = max(1, int(ctx.get("workers", 1)))
        if cancelled:
            self.status_var.set(
                f"Optimization stopped: {initial_total:.6g} -> {final_total:.6g}"
            )
            self.append_progress(
                f"Optimization stopped | merit {initial_total:.6g} -> {final_total:.6g}"
            )
        else:
            self.status_var.set(
                f"Optimization finished: {initial_total:.6g} -> {final_total:.6g}"
            )
            self.append_progress(
                f"Optimization finished | merit {initial_total:.6g} -> {final_total:.6g}"
            )
        self.append_progress(f"Optimization compute: {compute_backend} | workers={compute_workers}")
        for operand in (result.get("operands", []) if result is not None else []):
            self.append_progress(
                f"  {operand['name']}: value={float(operand['value']):.6g} weighted={float(operand['weighted']):.6g}"
            )

        self.optimization_context = None
        self.optimization_running = False
        self.optimization_cancel_requested = False
        self._stop_progress_spinner()
        self._update_progress_indicators()

    def _sample_ray_heights(self, max_radius: float) -> list[float]:
        if max_radius <= 1e-9:
            return [0.0]
        count = self._current_ray_count()
        span = max_radius * self._current_ray_height_factor()
        if count == 1:
            return [0.0]
        return list(np.linspace(-span, span, count))

    def _sample_field_values(self, maximum: float) -> list[float]:
        count = self._current_field_count()
        if count == 1:
            return [float(maximum)]
        span = abs(float(maximum))
        if span <= 1e-9:
            # User explicitly requested an on-axis field. Honour it instead of
            # silently inventing a synthetic ±span (the previous behaviour
            # generated phantom off-axis bundles for field_value=0).
            return [0.0] * count
        return list(np.linspace(-span, span, count))

    def _sample_field_grid_pairs(self, maximum: float) -> list[tuple[float, float]]:
        """Sample full-field preview points as an X/Y grid.

        The 2D layout remains a meridional slice, but 3D Full Pupil should
        show the full field grid: field_count=3 -> 3x3 field points.
        """
        count = self._current_field_count()
        field_values = [float(value) for value in self._sample_field_values(maximum)]
        if count <= 1:
            value = field_values[0] if field_values else float(maximum)
            axis = self._current_display_slice_axis()
            return [(value, 0.0)] if axis == "x" else [(0.0, value)]
        pairs: list[tuple[float, float]] = []
        seen: set[tuple[float, float]] = set()
        for field_y in field_values:
            for field_x in field_values:
                key = (round(float(field_x), 12), round(float(field_y), 12))
                if key in seen:
                    continue
                seen.add(key)
                pairs.append((float(field_x), float(field_y)))
        return pairs

    def _should_use_default_finite_cone_source(self, *, system=None) -> bool:
        """Return whether Pupil/field should become a physical point source.

        It should not. Under the North Star architecture, Pupil/field remains
        the conventional prescription-analysis sampler. Non-sequential scenes
        use a 3D aperture/envelope reference by default, while physical point
        cones are launched only by explicit source models such as Random point
        cone or authored scene sources.
        """
        return False

    def _should_show_open3d_launch_reference_surface(self, *, system=None) -> bool:
        return False

    def _current_image_diameter_mode(self) -> str:
        if not hasattr(self, "image_diameter_mode_var"):
            return "Auto"
        value = self.image_diameter_mode_var.get().strip()
        return value if value in {"Auto", "Manual"} else "Auto"

    def _preview_trace_signature(self):
        return build_preview_trace_signature(
            row_specs_signature=_row_specs_signature(self._serializable_row_specs()),
            object_mode=self._current_object_mode(),
            field_type=self._current_field_type(),
            field_value=self._current_field_value(),
            field_count=self._current_field_count(),
            requested_trace_mode=self._requested_trace_mode(),
            aperture_type_label=self._current_aperture_type_label(),
            aperture_value=self._current_aperture_value(),
            wavelength=self._current_wavelength(),
            ray_count=self._current_ray_count(),
            ray_height_factor=self._current_ray_height_factor(),
            source_model=self._current_source_model(),
            pupil_pattern_label=self._current_pupil_pattern_label(),
            source_radius=self._current_source_radius(),
            source_cone_angle=self._current_source_cone_angle(),
            gaussian_input_mode=self._current_gaussian_input_mode(),
            gaussian_waist_radius=self._current_gaussian_waist_radius(),
            gaussian_waist_offset=self._current_gaussian_waist_offset(),
            gaussian_beam_diameter=self._current_gaussian_beam_diameter(),
            gaussian_full_divergence=self._current_gaussian_full_divergence(),
            gaussian_waist_after_input=self._current_gaussian_waist_after_input(),
            gaussian_m2=self._current_gaussian_m2(),
            pupil_rad=self._current_pupil_rad(),
            pupil_theta=self._current_pupil_theta(),
            source_power=self._current_source_power(),
            source_seed=self._current_source_seed(),
            source_origin=self._current_source_origin(),
            source_direction=self._current_source_direction(),
            source_angular_weight=self._current_source_angular_weight(),
            nonseq_energy_probability=self._current_nonseq_energy_probability(),
            nonseq_ns_limit=self._current_nonseq_ns_limit(),
            nonseq_target_surface_index=self._current_nonseq_target_surface_index(),
            full_pupil_mode=self._is_full_pupil_mode(),
        )

    def _build_temporary_preview_trace(self):
        wavelength = self._current_wavelength()
        max_radius = max_surface_radius(self.rows)
        previous_count = getattr(self, "_preview_field_ray_count", 1)
        previous_bundle_count = getattr(self, "_preview_field_bundle_count", 1)
        capture = io.StringIO()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                with redirect_stdout(capture), redirect_stderr(capture):
                    system = self.build_system()
                    rays = Kos.raykeeper(system)
                    self._trace_preview_rays(
                        system,
                        rays,
                        wavelength,
                        max_radius,
                        allow_full_pupil=False,
                        sampling_mode="display_slice",
                    )
            captured = capture.getvalue()
            if captured:
                append_debug = self.__dict__.get("append_debug")
                if callable(append_debug):
                    append_debug(captured)
                elif "debug_text" in self.__dict__:
                    self.append_debug(captured)
            return system, rays
        finally:
            self._preview_field_ray_count = previous_count
            self._preview_field_bundle_count = previous_bundle_count

    def _traced_image_diameter_value(self) -> float | None:
        if not self.rows or self.rows[-1].surface != "Image":
            return None
        system = self.last_system
        rays = self.last_rays
        last_signature = self.__dict__.get("_last_preview_trace_signature")
        if system is None or rays is None or not preview_trace_signature_matches(last_signature, self._preview_trace_signature()):
            try:
                system, rays = self._build_temporary_preview_trace()
            except Exception:
                return None
        try:
            x_local, y_local, _z_local, _l_local, _m_local, _n_local = self._pick_image_plane_data(rays)
            x_local = np.asarray(x_local, dtype=float)
            y_local = np.asarray(y_local, dtype=float)
            final_surface = max(0, len(self.rows) - 1)
            reached_image = []
            for surfaces in getattr(rays, "SURFACE", ()):
                surface_arr = np.asarray(surfaces, dtype=int).ravel()
                reached_image.append(bool(surface_arr.size and int(surface_arr[-1]) == final_surface))
            if reached_image:
                reached_mask = np.asarray(reached_image, dtype=bool)
                if reached_mask.size != x_local.size:
                    return None
                x_local = x_local[reached_mask]
                y_local = y_local[reached_mask]
                if not x_local.size:
                    return None
            finite = np.isfinite(x_local) & np.isfinite(y_local)
            if not np.any(finite):
                return None
            x_local = x_local[finite]
            y_local = y_local[finite]
            diameter = max(
                float(np.ptp(x_local)),
                float(np.ptp(y_local)),
                2.0 * float(np.max(np.abs(x_local))),
                2.0 * float(np.max(np.abs(y_local))),
            )
            return max(diameter, 1.0)
        except Exception:
            return None

    def _auto_image_diameter_value(self) -> float:
        if not self.rows:
            return 3.0
        current_diameter = max(float(self.rows[-1].diameter), 1.0)
        sample_values = self._sample_field_values(self._current_field_value())
        if not sample_values:
            sample_values = [self._current_field_value()]
        height_key = "paraxial_image_height" if self._current_object_mode() == "Infinity" else "real_image_height"
        image_heights = [
            abs(float(self._field_metrics_for_value(self._current_field_type(), value).get(height_key, 0.0)))
            for value in sample_values
        ]
        traced_diameter = self._traced_image_diameter_value()
        candidates = [2.0 * max(image_heights) if image_heights else 0.0]
        finite_magnification = self._current_finite_paraxial_magnification()
        if (
            self._current_object_mode() == "Finite"
            and finite_magnification is not None
            and np.isfinite(finite_magnification)
            and self.rows
        ):
            candidates.append(abs(float(finite_magnification)) * max(float(self.rows[0].diameter), 0.0))
        if traced_diameter is not None:
            candidates.append(float(traced_diameter))
        diameter = max(candidates, default=0.0)
        if self._has_off_axis_geometry():
            diameter = min(diameter, self._auto_image_diameter_off_axis_limit())
        if diameter <= 1e-9:
            if self._has_off_axis_geometry():
                return min(current_diameter, self._auto_image_diameter_off_axis_limit())
            return current_diameter
        return max(float(diameter), 1.0)

    def _auto_image_diameter_off_axis_limit(self) -> float:
        optical_diameters = [
            max(float(row.diameter), 0.0)
            for row in self.rows[1:-1]
            if row.surface not in {"Object", "Image"}
        ]
        reference = max(optical_diameters or [1.0])
        try:
            reference = max(reference, abs(float(self._current_aperture_value())))
        except Exception:
            pass
        return max(4.0 * reference, 25.0)

    def _apply_image_diameter_mode(self) -> bool:
        if not self.rows or self.rows[-1].surface != "Image":
            return False
        if self._current_image_diameter_mode() != "Auto":
            return False
        new_diameter = self._auto_image_diameter_value()
        if abs(float(self.rows[-1].diameter) - float(new_diameter)) <= 1e-9:
            return False
        self.rows[-1].diameter = float(new_diameter)
        return True

    def _sample_fan_angles_deg(self) -> list[float]:
        maximum = self._current_field_angle_deg()
        count = self._current_ray_count()
        if count == 1 or maximum <= 1e-9:
            return [0.0]
        return list(np.linspace(-maximum, maximum, count))

    def _build_default_finite_cone_preview_bundles(self) -> tuple[
        list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
        int,
    ]:
        if self._current_source_model() != SOURCE_MODEL_DEFAULT:
            return [], 0
        cone_deg = float(self._current_source_cone_angle())
        if cone_deg <= 1e-12:
            return [], 0
        ray_count = max(1, int(self._current_ray_count()))
        angles_deg = np.asarray([0.0] if ray_count == 1 else np.linspace(-cone_deg, cone_deg, ray_count), dtype=float)
        angles_rad = np.deg2rad(angles_deg)
        axis_index = 0 if self._current_display_slice_axis() == "x" else 1
        field_values = self._sample_field_values(self._current_field_height())
        bundles: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
        for field_value in field_values:
            x_values = np.zeros(ray_count, dtype=float)
            y_values = np.zeros(ray_count, dtype=float)
            if axis_index == 0:
                x_values.fill(float(field_value))
            else:
                y_values.fill(float(field_value))
            l_values = np.zeros(ray_count, dtype=float)
            m_values = np.zeros(ray_count, dtype=float)
            if axis_index == 0:
                l_values = np.sin(angles_rad).astype(float)
            else:
                m_values = np.sin(angles_rad).astype(float)
            n_values = np.cos(angles_rad).astype(float)
            bundles.append(
                (
                    x_values,
                    y_values,
                    np.zeros(ray_count, dtype=float),
                    l_values,
                    m_values,
                    n_values,
                )
            )
        return bundles, ray_count

    def _build_default_finite_cone_world_bundles(self) -> tuple[
        list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
        int,
    ]:
        if self._current_source_model() != SOURCE_MODEL_DEFAULT:
            return [], 0
        cone_deg = float(self._current_source_cone_angle())
        if cone_deg <= 1e-12:
            return [], 0
        ray_count = max(1, int(self._current_ray_count()))
        from KrakenOS.UI.source_trace_helpers import finite_cone_direction_samples

        l_values, m_values, n_values = finite_cone_direction_samples(
            cone_deg,
            ray_count,
            pupil_pattern=self._current_pupil_pattern_label(),
            display_orientation=self._current_display_orientation(),
            pupil_rad=self._current_pupil_rad(),
            pupil_theta=self._current_pupil_theta(),
            seed=self._current_source_seed(),
        )
        ray_count = int(len(l_values))
        field_pairs = (
            [(0.0, 0.0)]
            if self._current_object_mode() == "Infinity"
            else self._sample_field_grid_pairs(self._current_field_height())
        )
        bundles: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
        for field_x, field_y in field_pairs:
            bundles.append(
                self._orient_source_points_and_dirs(
                    np.full(ray_count, float(field_x), dtype=float),
                    np.full(ray_count, float(field_y), dtype=float),
                    np.zeros(ray_count, dtype=float),
                    l_values.copy(),
                    m_values.copy(),
                    n_values.copy(),
                )
            )
        return bundles, ray_count

    def _build_default_nonseq_reference_world_bundles(
        self,
        pupil_radius: float,
    ) -> tuple[
        list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
        int,
    ]:
        if self._current_source_model() != SOURCE_MODEL_DEFAULT:
            return [], 0
        ray_count = max(1, int(self._current_ray_count()))
        cone_deg = float(self._current_source_cone_angle())
        from KrakenOS.UI.source_trace_helpers import finite_cone_direction_samples

        cone_l, cone_m, cone_n = finite_cone_direction_samples(
            cone_deg,
            ray_count,
            pupil_pattern=self._current_pupil_pattern_label(),
            display_orientation=self._current_display_orientation(),
            pupil_rad=self._current_pupil_rad(),
            pupil_theta=self._current_pupil_theta(),
            seed=self._current_source_seed(),
        )
        ray_count = max(1, int(len(cone_l)))
        radius = max(float(self._current_source_radius()), 0.0)
        if radius <= 1e-9:
            radius = float(pupil_radius) if np.isfinite(float(pupil_radius)) else 0.0
        if radius <= 1e-9:
            radius = 1.0
        disk_pts = self._sample_reference_disk_points_3d(radius, ray_count)
        bundles: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = []
        if self._current_object_mode() == "Infinity" or self._current_field_type() == "Angle":
            pairs = self._sample_field_grid_pairs(self._current_field_angle_deg())
            for field_x, field_y in pairs:
                tan_x = np.tan(np.deg2rad(float(field_x)))
                tan_y = np.tan(np.deg2rad(float(field_y)))
                direction = np.array([tan_x, tan_y, 1.0], dtype=float)
                norm = float(np.linalg.norm(direction))
                if norm <= 1e-12:
                    continue
                direction /= norm
                l_values, m_values, n_values = self._cone_directions_about_local_base(
                    direction,
                    cone_l,
                    cone_m,
                    cone_n,
                )
                bundles.append(
                    self._orient_source_points_and_dirs(
                        np.asarray(disk_pts[:, 0], dtype=float),
                        np.asarray(disk_pts[:, 1], dtype=float),
                        np.zeros(len(disk_pts), dtype=float),
                        l_values,
                        m_values,
                        n_values,
                    )
                )
        else:
            pairs = self._sample_field_grid_pairs(self._current_field_height())
            for field_x, field_y in pairs:
                bundles.append(
                    self._orient_source_points_and_dirs(
                        np.asarray(disk_pts[:, 0], dtype=float) + float(field_x),
                        np.asarray(disk_pts[:, 1], dtype=float) + float(field_y),
                        np.zeros(len(disk_pts), dtype=float),
                        cone_l,
                        cone_m,
                        cone_n,
                    )
                )
        return bundles, int(len(disk_pts))

    def _entrance_radius(self, fallback_radius: float) -> float:
        object_radius = None
        if self.rows:
            object_radius = max(float(self.rows[0].diameter) / 2.0, 0.5)
        for row in self.rows[1:]:
            if row.surface not in {"Object", "Image"}:
                radius = max(row.diameter / 2.0, 0.5)
                if object_radius is not None:
                    return min(radius, object_radius)
                return radius
        if object_radius is not None:
            return min(fallback_radius, object_radius)
        return fallback_radius

    def _resolved_preview_pupil_radius(
        self,
        fallback_radius: float,
        *,
        system=None,
        wavelength: float | None = None,
    ) -> float:
        radius = max(self._entrance_radius(fallback_radius), 1e-6)
        aperture_radius = None
        aperture_value = abs(float(self._current_aperture_value()))
        if aperture_value > 1e-9:
            aperture_radius = aperture_value * 0.5
        if system is not None:
            try:
                pupil_system, _pupil_rows, pupil_surface_index = self._pupil_model_inputs(
                    system,
                    build_reference=True,
                )
                pupil = Kos.PupilCalc(
                    pupil_system,
                    pupil_surface_index,
                    self._current_wavelength() if wavelength is None else float(wavelength),
                    self._current_aperture_type(),
                    self._current_aperture_value(),
                )
                pupil_radius = float(getattr(pupil, "RadPupInp", 0.0))
                if np.isfinite(pupil_radius) and pupil_radius > 1e-9:
                    aperture_radius = pupil_radius
            except Exception:
                pass
        if aperture_radius is None or not np.isfinite(aperture_radius) or aperture_radius <= 1e-9:
            return radius
        return max(min(radius, float(aperture_radius)), 1e-6)

    def _trace_preview_service(self) -> TracePreviewService:
        service = self.__dict__.get("_trace_preview_service_instance")
        if service is None:
            service = TracePreviewService(self)
            self._trace_preview_service_instance = service
        return service

    def _trace_preview_rays(
        self,
        system,
        rays,
        wavelength: float,
        max_radius: float,
        *,
        allow_full_pupil: bool = True,
        sampling_mode: str = "display_slice",
    ) -> None:
        self._trace_preview_service()._trace_preview_rays(
            system,
            rays,
            wavelength,
            max_radius,
            allow_full_pupil=allow_full_pupil,
            sampling_mode=sampling_mode,
        )

    def _trace_preview_bundles(
        self,
        system,
        rays,
        wavelength: float,
        bundles: list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]],
        *,
        bundle_sources: list[SceneSource3D | None] | None = None,
    ) -> None:
        self._trace_preview_service()._trace_preview_bundles(
            system,
            rays,
            wavelength,
            bundles,
            bundle_sources=bundle_sources,
        )

    def _build_pupilcalc_preview_bundles(self, system, wavelength: float, pattern: str):
        return self._trace_preview_service()._build_pupilcalc_preview_bundles(system, wavelength, pattern)

    def _build_meridional_preview_bundles(self, pupil_radius: float, *, system=None, wavelength: float | None = None):
        return self._trace_preview_service()._build_meridional_preview_bundles(
            pupil_radius,
            system=system,
            wavelength=wavelength,
        )

    def _sequential_preview_image_catch_diameter(self, trace_state: dict[str, object] | None = None) -> float | None:
        if trace_state is not None and bool(trace_state.get("use_nonseq")):
            return None
        if not self.rows or str(self.rows[-1].surface) != "Image":
            return None
        try:
            current = max(float(self.rows[-1].diameter), 1.0)
        except Exception:
            current = 1.0
        axial_span = 0.0
        max_clear = current
        for row in self.rows:
            try:
                axial_span += abs(float(row.thickness))
            except Exception:
                pass
            try:
                max_clear = max(max_clear, abs(float(row.diameter)))
            except Exception:
                pass
        catch = max(current, 4.0 * axial_span, 20.0 * max_clear, 1000.0)
        return float(catch) if catch > current + 1e-9 else None

    @staticmethod
    def _temporarily_set_system_surface_diameter(system, surface_index: int, diameter: float):
        edits: list[tuple[object, float]] = []
        seen_surfaces: set[int] = set()
        if system is None or surface_index < 0:
            return lambda: None
        for attr in ("SDT", "SDT_0"):
            surfaces = getattr(system, attr, None)
            try:
                surface = surfaces[surface_index]
            except Exception:
                continue
            surface_id = id(surface)
            if surface_id in seen_surfaces:
                continue
            seen_surfaces.add(surface_id)
            if not hasattr(surface, "Diameter"):
                continue
            try:
                previous = float(surface.Diameter)
                surface.Diameter = float(diameter)
                edits.append((surface, previous))
            except Exception:
                continue

        def restore() -> None:
            for surface, previous in edits:
                try:
                    surface.Diameter = previous
                except Exception:
                    pass

        return restore

    def _is_full_pupil_mode(self) -> bool:
        emit_full_ray_var = self.__dict__.get("emit_full_ray_var")
        return bool(emit_full_ray_var and emit_full_ray_var.get())

    def _sample_pupil_disk(self, max_radius: float, rings: int | None = None) -> np.ndarray:
        """Generate a hexapolar grid of (x, y) points filling the full circular pupil.

        ``rings`` defaults to ``max(3, ray_count)``. Pass an explicit value for
        a coarser sampling — e.g. when sampling the field axis as well as the
        pupil axis, you typically want fewer field samples than pupil samples.
        """
        if max_radius <= 1e-9:
            return np.array([[0.0, 0.0]])
        if rings is None:
            rings = max(3, self._current_ray_count())
        rings = max(1, int(rings))
        pts = [[0.0, 0.0]]
        for j in range(1, rings + 1):
            r = max_radius * j / rings
            n_pts = max(6, j * 6)
            for k in range(n_pts):
                angle = 2.0 * np.pi * k / n_pts
                pts.append([r * np.cos(angle), r * np.sin(angle)])
        return np.array(pts, dtype=float)

    def _sample_pupil_rim(self, max_radius: float, samples: int | None = None) -> np.ndarray:
        """Generate center plus boundary pupil samples for source-driven 3D envelope views."""
        radius = float(max_radius) if np.isfinite(float(max_radius)) else 0.0
        if radius <= 1e-9:
            return np.array([[0.0, 0.0]], dtype=float)
        if samples is None:
            samples = max(8, min(12, self._current_ray_count()))
        samples = max(4, int(samples))
        angles = np.linspace(0.0, 2.0 * np.pi, samples, endpoint=False)
        rim = np.column_stack((radius * np.cos(angles), radius * np.sin(angles))).astype(float)
        return np.vstack((np.asarray([[0.0, 0.0]], dtype=float), rim))

    def _sample_ray_count_pupil_points(self, max_radius: float) -> np.ndarray:
        """Generate exactly ``Ray Count`` deterministic 3D pupil samples."""
        radius = float(max_radius) if np.isfinite(float(max_radius)) else 0.0
        if radius <= 1e-9 and self.rows:
            try:
                radius = max(float(self.rows[0].diameter) * 0.5, 0.0)
            except Exception:
                radius = 0.0
        if radius <= 1e-9:
            radius = 1.0
        count = max(1, int(self._current_ray_count()))
        if count == 1:
            return np.asarray([[0.0, 0.0]], dtype=float)
        points: list[list[float]] = [[0.0, 0.0]]
        golden_angle = np.pi * (3.0 - np.sqrt(5.0))
        denominator = max(1, count - 1)
        for index in range(1, count):
            fraction = float(index) / float(denominator)
            r = radius * np.sqrt(fraction)
            angle = float(index) * golden_angle
            points.append([float(r * np.cos(angle)), float(r * np.sin(angle))])
        return np.asarray(points[:count], dtype=float)

    def _sample_sparse_pupil_disk(self, max_radius: float) -> np.ndarray:
        """Sparse filled pupil used only to discover the through-going 3D envelope."""
        radius = float(max_radius) if np.isfinite(float(max_radius)) else 0.0
        if radius <= 1e-9:
            return np.array([[0.0, 0.0]], dtype=float)
        samples = max(8, min(12, self._current_ray_count()))
        pts: list[list[float]] = [[0.0, 0.0]]
        for fraction in (0.25, 0.5, 0.75, 1.0):
            r = radius * fraction
            for angle in np.linspace(0.0, 2.0 * np.pi, samples, endpoint=False):
                pts.append([float(r * np.cos(angle)), float(r * np.sin(angle))])
        unique = np.unique(np.round(np.asarray(pts, dtype=float), decimals=12), axis=0)
        return np.asarray(unique, dtype=float)

    def _build_world_envelope_bundles(self, pupil_radius: float, *, system=None):
        """Build source-driven 3D pupil bundles for 2D/Open 3D preview.

        This is trace sampling, not display decimation: the bundle contains
        exactly ``Ray Count`` pupil samples for each effective field point.
        """
        radius = float(pupil_radius) if np.isfinite(float(pupil_radius)) else 0.0
        if radius <= 1e-9 and self.rows:
            try:
                radius = max(float(self.rows[0].diameter) * 0.5, 0.0)
            except Exception:
                radius = 0.0
        if radius <= 1e-9:
            radius = 1.0
        pupil_pts = self._sample_ray_count_pupil_points(radius)
        return self._build_world_bundles_from_pupil_points(pupil_pts, system=system)

    def _build_world_sparse_pupil_bundles(self, pupil_radius: float, *, system=None):
        radius = float(pupil_radius) if np.isfinite(float(pupil_radius)) else 0.0
        if radius <= 1e-9 and self.rows:
            try:
                radius = max(float(self.rows[0].diameter) * 0.5, 0.0)
            except Exception:
                radius = 0.0
        if radius <= 1e-9:
            radius = 1.0
        return self._build_world_bundles_from_pupil_points(self._sample_sparse_pupil_disk(radius), system=system)

    def _sample_world_section_pupil_points(self, max_radius: float) -> np.ndarray:
        radius = float(max_radius) if np.isfinite(float(max_radius)) else 0.0
        if radius <= 1e-9 and self.rows:
            try:
                radius = max(float(self.rows[0].diameter) * 0.5, 0.0)
            except Exception:
                radius = 0.0
        if radius <= 1e-9:
            radius = 1.0
        axis_samples = np.asarray(self._sample_ray_heights(radius), dtype=float)
        points: list[list[float]] = []
        for y_value in axis_samples:
            points.append([0.0, float(y_value)])
        for x_value in axis_samples:
            points.append([float(x_value), 0.0])
        for x_value, y_value in self._sample_pupil_rim(radius):
            points.append([float(x_value), float(y_value)])
        if not points:
            return np.asarray([[0.0, 0.0]], dtype=float)
        unique = np.unique(np.round(np.asarray(points, dtype=float), decimals=12), axis=0)
        return np.asarray(unique, dtype=float)

    def _field_cross_pairs_for_world_sections(self, maximum: float) -> list[tuple[float, float]]:
        values = [float(value) for value in self._sample_field_values(maximum)]
        if not values:
            values = [0.0]
        pairs: list[tuple[float, float]] = []
        seen: set[tuple[float, float]] = set()
        for value in values:
            for pair in ((float(value), 0.0), (0.0, float(value))):
                key = (round(pair[0], 12), round(pair[1], 12))
                if key in seen:
                    continue
                seen.add(key)
                pairs.append(pair)
        return pairs

    def _build_world_section_bundles(self, pupil_radius: float, *, system=None):
        pupil_points = self._sample_world_section_pupil_points(pupil_radius)
        if self._current_object_mode() == "Infinity":
            field_pairs = self._field_cross_pairs_for_world_sections(self._current_field_angle_deg())
        else:
            field_pairs = self._field_cross_pairs_for_world_sections(self._current_field_height())
        return self._build_world_bundles_from_pupil_points(pupil_points, field_pairs=field_pairs, system=system)

    def _build_world_bundles_from_pupil_points(
        self,
        pupil_points: np.ndarray,
        *,
        field_pairs: list[tuple[float, float]] | None = None,
        system=None,
    ):
        pupil_points = np.asarray(pupil_points, dtype=float)
        if pupil_points.ndim != 2 or pupil_points.shape[0] == 0 or pupil_points.shape[1] < 2:
            pupil_points = np.array([[0.0, 0.0]], dtype=float)
        bundles = []
        if self._current_object_mode() == "Infinity":
            pairs = field_pairs if field_pairs is not None else self._sample_field_grid_pairs(self._current_field_angle_deg())
            for field_x, field_y in pairs:
                tan_x = np.tan(np.deg2rad(float(field_x)))
                tan_y = np.tan(np.deg2rad(float(field_y)))
                direction = np.array([tan_x, tan_y, 1.0], dtype=float)
                norm = float(np.linalg.norm(direction))
                if norm <= 1e-12:
                    continue
                direction /= norm
                n_pts = len(pupil_points)
                bundle = (
                    np.asarray(pupil_points[:, 0], dtype=float),
                    np.asarray(pupil_points[:, 1], dtype=float),
                    np.zeros(n_pts, dtype=float),
                    np.full(n_pts, float(direction[0]), dtype=float),
                    np.full(n_pts, float(direction[1]), dtype=float),
                    np.full(n_pts, float(direction[2]), dtype=float),
                )
                bundle = self._center_infinity_bundle_on_launch_reference(bundle, system=system)
                bundles.append(bundle)
        else:
            object_distance = self._current_object_distance()
            pairs = field_pairs if field_pairs is not None else self._sample_field_grid_pairs(self._current_field_height())
            for field_x, field_y in pairs:
                origin = np.array([-float(field_x), -float(field_y), 0.0], dtype=float)
                x_vals: list[float] = []
                y_vals: list[float] = []
                z_vals: list[float] = []
                l_vals: list[float] = []
                m_vals: list[float] = []
                n_vals: list[float] = []
                for pupil_x, pupil_y in pupil_points[:, :2]:
                    target = np.array([float(pupil_x), float(pupil_y), object_distance], dtype=float)
                    direction = target - origin
                    norm = float(np.linalg.norm(direction))
                    if norm <= 1e-12:
                        continue
                    direction /= norm
                    x_vals.append(float(origin[0]))
                    y_vals.append(float(origin[1]))
                    z_vals.append(float(origin[2]))
                    l_vals.append(float(direction[0]))
                    m_vals.append(float(direction[1]))
                    n_vals.append(float(direction[2]))
                if x_vals:
                    bundles.append(
                        (
                            np.asarray(x_vals, dtype=float),
                            np.asarray(y_vals, dtype=float),
                            np.asarray(z_vals, dtype=float),
                            np.asarray(l_vals, dtype=float),
                            np.asarray(m_vals, dtype=float),
                            np.asarray(n_vals, dtype=float),
                        )
                    )
        return bundles, int(len(pupil_points))

    def _trace_world_envelope_rays(self, system, rays, wavelength: float, pupil_radius: float) -> bool:
        boundary_bundles, _boundary_count = self._build_world_envelope_bundles(pupil_radius, system=system)
        if not boundary_bundles:
            return False
        if self._trace_selected_through_envelope(system, rays, wavelength, boundary_bundles):
            return True

        sparse_bundles, _sparse_count = self._build_world_sparse_pupil_bundles(pupil_radius, system=system)
        if sparse_bundles and self._trace_selected_through_envelope(system, rays, wavelength, sparse_bundles):
            return True

        # If every sampled envelope is clipped, still show the physical
        # boundary rather than returning no rays; the status/debug output makes
        # the clipping explicit for diagnostics.
        rays.clean()
        self._trace_preview_bundles(system, rays, wavelength, boundary_bundles)
        self._preview_field_ray_count = max(1, int(_boundary_count))
        self._preview_field_bundle_count = int(len(boundary_bundles))
        self.append_debug("3D source envelope: no through-going boundary rays found; showing clipped launch boundary.")
        return True

    def _trace_selected_through_envelope(self, system, rays, wavelength: float, bundles: list[tuple[np.ndarray, ...]]) -> bool:
        candidate_rays = Kos.raykeeper(system)
        self._trace_preview_bundles(system, candidate_rays, wavelength, bundles)
        total_launches = 0
        max_group_count = 0
        for bundle in bundles:
            try:
                group_count = len(np.asarray(bundle[0], dtype=float).reshape(-1))
            except Exception:
                group_count = 0
            total_launches += int(max(group_count, 0))
            max_group_count = max(max_group_count, int(max(group_count, 0)))
        if _raykeeper_has_non_primary_branch_paths(candidate_rays, expected_launch_count=total_launches):
            rays.clean()
            self._trace_preview_bundles(system, rays, wavelength, bundles)
            self._preview_field_ray_count = max(1, int(max_group_count))
            self._preview_field_bundle_count = int(len(bundles))
            try:
                raw_paths = getattr(rays, "CC", [])
                traced_count = len(raw_paths) if raw_paths is not None else 0
            except Exception:
                traced_count = 0
            self.append_debug(
                "3D source envelope: splitter/branch paths detected; "
                f"kept full {total_launches}-ray launch bundle ({traced_count} displayed branch paths)."
            )
            return True
        final_surface = max(0, len(self.rows) - 1)
        surfaces = [np.asarray(seq, dtype=int).ravel() for seq in getattr(candidate_rays, "SURFACE", ())]
        through_total = 0
        for surface_ids in surfaces:
            if surface_ids.size and int(surface_ids[-1]) == final_surface:
                through_total += 1

        if through_total <= 0:
            return False

        rays.clean()
        self._trace_preview_bundles(system, rays, wavelength, bundles)
        self._preview_field_ray_count = max(1, int(max_group_count))
        self._preview_field_bundle_count = int(len(bundles))
        self.append_debug(
            f"3D source envelope: kept full {total_launches}-ray launch bundle "
            f"({through_total} through-going paths)."
        )
        return True

    def _full_pupil_grid_xy(self, half_extent: float, max_n: int | None = None):
        """N×N square grid in [-half_extent, +half_extent], where N = ray_count.

        ``max_n`` caps the per-axis grid size. Useful when each grid sample
        carries its own ray bundle (Infinity field axis: each field gets a
        full pupil bundle, so N² × pupil_samp can balloon at large ray_count).
        """
        n = max(1, self._current_ray_count())
        if max_n is not None:
            n = min(n, int(max_n))
        if n == 1:
            return np.array([0.0]), np.array([0.0])
        coords = np.linspace(-half_extent, half_extent, n)
        xx, yy = np.meshgrid(coords, coords, indexing="xy")
        return xx.flatten(), yy.flatten()

    def _build_grid_parallel_bundle(self, pupil_radius: float):
        """N×N grid of parallel rays from the object plane, all going +Z.

        Grid extent = entrance pupil radius if PupilCalc resolved one, else
        the first surface's half-diameter, else 1 mm.
        """
        radius = float(pupil_radius) if np.isfinite(pupil_radius) else 0.0
        if radius <= 1e-9 and self.rows:
            try:
                radius = max(float(self.rows[0].diameter) * 0.5, 0.0)
            except Exception:
                radius = 0.0
        if radius <= 1e-9:
            radius = 1.0
        x_values, y_values = self._full_pupil_grid_xy(radius)
        n_pts = len(x_values)
        if n_pts == 0:
            return None
        z_values = np.zeros(n_pts, dtype=float)
        l_values = np.zeros(n_pts, dtype=float)
        m_values = np.zeros(n_pts, dtype=float)
        n_values = np.ones(n_pts, dtype=float)
        return (x_values, y_values, z_values, l_values, m_values, n_values)

    def _build_grid_angular_bundles(self, system, wavelength: float, pupil_radius: float):
        """Filled pupil bundles for infinity-object preview.

        Each field sample is represented by a parallel bundle spanning the
        entrance pupil. This avoids drawing artificial pre-focus cones before
        the first surface for on-axis collimated beams.
        """
        try:
            pupil = Kos.PupilCalc(
                system,
                self._analysis_surface_index(),
                float(wavelength),
                self._current_aperture_type(),
                self._current_aperture_value(),
            )
            pupil.Samp = max(3, self._current_ray_count())
            pupil.Ptype = self._current_analysis_pupil_pattern()
            pupil.FieldType = "angle"
            bundles = []
            for field_x, field_y in self._sample_field_grid_pairs(self._current_field_angle_deg()):
                pupil.FieldX = float(field_x)
                pupil.FieldY = float(field_y)
                bundle = self._pupil_pattern_bundle(pupil)
                if bundle and len(np.asarray(bundle[0])) > 0:
                    bundle = self._center_infinity_bundle_on_launch_reference(bundle, system=system)
                    bundles.append(bundle)
            if bundles:
                return bundles
        except Exception:
            pass

        radius = float(pupil_radius) if np.isfinite(pupil_radius) else 0.0
        if radius <= 1e-9 and self.rows:
            try:
                radius = max(float(self.rows[0].diameter) * 0.5, 0.0)
            except Exception:
                radius = 0.0
        if radius <= 1e-9:
            radius = 1.0
        disk_pts = self._sample_pupil_disk(radius)
        bundles = []
        for field_x, field_y in self._sample_field_grid_pairs(self._current_field_angle_deg()):
            tan_x = np.tan(np.deg2rad(float(field_x)))
            tan_y = np.tan(np.deg2rad(float(field_y)))
            direction = np.array([tan_x, tan_y, 1.0], dtype=float)
            norm = np.linalg.norm(direction)
            if norm <= 1e-12:
                continue
            direction /= norm
            n_pts = len(disk_pts)
            bundle = (
                np.asarray(disk_pts[:, 0], dtype=float),
                np.asarray(disk_pts[:, 1], dtype=float),
                np.zeros(n_pts, dtype=float),
                np.full(n_pts, float(direction[0]), dtype=float),
                np.full(n_pts, float(direction[1]), dtype=float),
                np.full(n_pts, float(direction[2]), dtype=float),
            )
            bundle = self._center_infinity_bundle_on_launch_reference(bundle, system=system)
            bundles.append(bundle)
        return bundles

    def _build_grid_finite_object_bundles(self, system, wavelength: float, pupil_radius: float):
        """Filled pupil bundles for finite-object full-pupil preview."""
        try:
            pupil = Kos.PupilCalc(
                system,
                self._analysis_surface_index(),
                float(wavelength),
                self._current_aperture_type(),
                self._current_aperture_value(),
            )
            pupil.Samp = max(3, self._current_ray_count())
            pupil.Ptype = self._current_analysis_pupil_pattern()
            pupil.FieldType = "height"
            bundles = []
            for field_x, field_y in self._sample_field_grid_pairs(self._current_field_height()):
                pupil.FieldX = float(field_x)
                pupil.FieldY = float(field_y)
                bundle = self._pupil_pattern_bundle(pupil)
                if bundle and len(np.asarray(bundle[0])) > 0:
                    bundles.append(bundle)
            if bundles:
                return bundles
        except Exception:
            pass

        radius = float(pupil_radius) if np.isfinite(pupil_radius) else 0.0
        if radius <= 1e-9:
            radius = 1.0
        disk_pts = self._sample_pupil_disk(radius)
        object_distance = self._current_object_distance()
        bundles = []
        for field_x, field_y in self._sample_field_grid_pairs(self._current_field_height()):
            origin = np.array([-float(field_x), -float(field_y), 0.0], dtype=float)
            x_vals: list[float] = []
            y_vals: list[float] = []
            z_vals: list[float] = []
            l_vals: list[float] = []
            m_vals: list[float] = []
            n_vals: list[float] = []
            for pupil_x, pupil_y in disk_pts:
                target = np.array([float(pupil_x), float(pupil_y), object_distance], dtype=float)
                direction = target - origin
                norm = np.linalg.norm(direction)
                if norm <= 1e-12:
                    continue
                direction /= norm
                x_vals.append(float(origin[0]))
                y_vals.append(float(origin[1]))
                z_vals.append(float(origin[2]))
                l_vals.append(float(direction[0]))
                m_vals.append(float(direction[1]))
                n_vals.append(float(direction[2]))
            if x_vals:
                bundles.append(
                    (
                        np.asarray(x_vals, dtype=float),
                        np.asarray(y_vals, dtype=float),
                        np.asarray(z_vals, dtype=float),
                        np.asarray(l_vals, dtype=float),
                        np.asarray(m_vals, dtype=float),
                        np.asarray(n_vals, dtype=float),
                    )
                )
        return bundles



    def _current_ray_count(self) -> int:
        try:
            return max(1, int(self.ray_count_var.get()))
        except ValueError:
            return 5

    def _current_source_model(self) -> str:
        source_model_var = self.__dict__.get("source_model_var")
        value = str(source_model_var.get()).strip() if source_model_var is not None else SOURCE_MODEL_DEFAULT
        return value if value in SOURCE_MODEL_VALUES else SOURCE_MODEL_DEFAULT

    def _current_pupil_pattern_label(self) -> str:
        pupil_pattern_var = self.__dict__.get("pupil_pattern_var")
        value = str(pupil_pattern_var.get()).strip() if pupil_pattern_var is not None else PUPIL_PATTERN_DEFAULT
        return value if value in PUPIL_PATTERN_VALUES else PUPIL_PATTERN_DEFAULT

    def _current_kraken_pupil_pattern(self) -> str | None:
        return PUPIL_PATTERN_TO_KRAKEN.get(self._current_pupil_pattern_label())

    def _current_analysis_pupil_pattern(self, fallback: str = "hexapolar") -> str:
        return self._current_kraken_pupil_pattern() or fallback

    def _current_source_radius(self) -> float:
        source_radius_var = self.__dict__.get("source_radius_var")
        try:
            value = float(source_radius_var.get()) if source_radius_var is not None else 5.0
        except Exception:
            value = 5.0
        return max(float(value), 0.0)

    def _current_source_cone_angle(self) -> float:
        source_cone_angle_var = self.__dict__.get("source_cone_angle_var")
        try:
            value = float(source_cone_angle_var.get()) if source_cone_angle_var is not None else 0.0
        except Exception:
            value = 0.0
        return max(min(float(value), 89.9), 0.0)

    def _current_gaussian_input_mode(self) -> str:
        var = self.__dict__.get("gaussian_input_mode_var")
        value = str(var.get()).strip() if var is not None else GAUSSIAN_INPUT_MODE_DEFAULT
        return value if value in GAUSSIAN_INPUT_MODE_VALUES else GAUSSIAN_INPUT_MODE_DEFAULT


    def _plot_fallback_preview(self, max_radius: float) -> None:
        positions = []
        z = 0.0
        last_index = len(self.rows) - 1
        for row_index, row in enumerate(self.rows):
            positions.append(z)
            radius = max(row.diameter / 2.0, 0.5)
            color = "#4f81bd" if row.glass.upper() != "AIR" else "#7f8c8d"
            x_vals, y_vals = self._project_xy([z, z], [-radius, radius])
            self.ax.plot(x_vals, y_vals, color=color, linewidth=2)
            if row.surface in {"Object", "Image", "Aperture"} or row_index in {0, last_index}:
                self.ax.text(
                    float(x_vals[0]),
                    float(np.max(y_vals) + max_radius * 0.08),
                    row.name,
                    rotation=0,
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )
            z += row.thickness

        total_length = max(z, 1.0)
        margin = max(total_length * 0.05, 5.0)
        if self._current_display_orientation() in {"XZ", "XY"}:
            self._set_plot_limits_from_drawn_data()
        else:
            self.ax.set_xlim(-margin, total_length + margin)
            self.ax.set_ylim(-(max_radius * 1.4), max_radius * 1.4)
        axis_x, axis_y = self._project_xy([0.0, total_length], [0.0, 0.0])
        self.ax.plot(axis_x, axis_y, color="#2c3e50", linewidth=0.8)
        self.ax.text(
            0.01,
            0.99,
            "Fallback sequential preview",
            transform=self.ax.transAxes,
            ha="left",
            va="top",
            fontsize=8,
            color="#7f1d1d",
            bbox={"facecolor": "white", "edgecolor": "#7f1d1d", "alpha": 0.75, "pad": 2.0},
        )

    def _plot_trace_failure_diagnostic(self, exc: NonSequentialTracePreviewError) -> None:
        trace_state = dict(getattr(exc, "trace_state", {}) or {})
        reasons = ", ".join(str(reason) for reason in trace_state.get("reasons", ()) or ())
        lines = [
            "Non-sequential trace failed",
            _short_error_message(exc, limit=320),
            "Sequential fallback was not drawn.",
        ]
        if reasons:
            lines.append(f"Scene trigger: {reasons}")
        self.ax.set_axis_off()
        self.ax.text(
            0.5,
            0.58,
            "\n".join(lines),
            transform=self.ax.transAxes,
            ha="center",
            va="center",
            fontsize=10,
            color="#7f1d1d",
            bbox={"facecolor": "white", "edgecolor": "#7f1d1d", "alpha": 0.88, "pad": 8.0},
            wrap=True,
        )

    def _main_glass_catalog_browser_dialog(self) -> MainGlassCatalogBrowserDialog:
        dialog = self.__dict__.get("_main_glass_catalog_browser_dialog_instance")
        if dialog is None:
            dialog = MainGlassCatalogBrowserDialog(
                self,
                shared_setup=_shared_setup,
                short_error_message=_short_error_message,
            )
            self._main_glass_catalog_browser_dialog_instance = dialog
        return dialog

    def _glass_catalog_records(self) -> list[dict[str, object]]:
        return self._main_glass_catalog_browser_dialog()._glass_catalog_records()

    def open_glass_catalog_browser(self) -> None:
        self._main_glass_catalog_browser_dialog().open_glass_catalog_browser()

    @staticmethod
    def _available_zemax_rayfile_path(path: Path) -> Path:
        path = Path(path).expanduser()
        if path.exists():
            return path
        name = path.name
        for old, new in (("_5M_", "_500k_"), ("_5M_", "_100k_"), ("_500k_", "_100k_")):
            if old in name:
                candidate = path.with_name(name.replace(old, new))
                if candidate.exists():
                    return candidate
        return path

    def _load_zemax_rayfile_source_path(self, path: Path, refs, *, source: str = "file") -> None:
        path = Path(path)
        source_specs: list[dict[str, object]] = []
        missing: list[Path] = []
        sample_count = max(1, int(self._current_ray_count() if hasattr(self, "ray_count_var") else 201))
        sample_count = max(sample_count, 201)
        first_wavelength = None
        for ref in refs:
            rayfile_path = self._available_zemax_rayfile_path(Path(ref.rayfile_path))
            if not rayfile_path.exists():
                missing.append(rayfile_path)
                continue
            summary = summarize_zemax_rayfile(rayfile_path)
            wavelength = float(ref.wavelength_um) if ref.wavelength_um is not None else float(self._current_wavelength())
            if first_wavelength is None:
                first_wavelength = wavelength
            name = rayfile_path.stem.replace("_", " ")
            source_specs.append(
                {
                    "source_id": f"source:zemax-rayfile:{len(source_specs) + 1}",
                    "name": f"Zemax Rayfile {len(source_specs) + 1}: {name}",
                    "role": "illumination",
                    "model": SOURCE_MODEL_ZEMAX_RAYFILE,
                    "enabled": True,
                    "physical": True,
                    "origin": [0.0, 0.0, 0.0],
                    "direction": [0.0, 0.0, 1.0],
                    "ray_count": sample_count,
                    "power": 1.0,
                    "wavelength": wavelength,
                    "rayfile_path": str(rayfile_path),
                    "source_zmx_path": str(path),
                    "spectrum_path": "" if ref.spectrum_path is None else str(ref.spectrum_path),
                    "record_count": int(summary.record_count),
                    "header_record_count": int(summary.header_record_count or summary.record_count),
                    "rayfile_label": summary.source_label,
                    "wavelength_min_um": ref.wavelength_min_um,
                    "wavelength_max_um": ref.wavelength_max_um,
                }
            )
        if missing or not source_specs:
            message = "\n".join(str(item) for item in missing[:4])
            if len(missing) > 4:
                message += f"\n... and {len(missing) - 4} more"
            messagebox.showerror(
                "Zemax rayfile source import failed",
                f"The Zemax non-sequential file references missing ray database file(s):\n\n{message}",
                parent=self,
            )
            self.status_var.set("Zemax rayfile import failed: missing .DAT ray database.")
            return

        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception:
            pass
        self._begin_history_capture()
        self._reset_complete_layout_runtime_state(close_viewers=True)
        self.current_layout_file = None
        self.rows = [
            SurfaceRow(surface="Object", name="Object", thickness=25.0, diameter=250.0, glass="AIR"),
            SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=250.0, glass="AIR"),
        ]
        settings = {
            "object_mode": "Finite",
            "display_orientation": "YZ",
            "wavelength": f"{float(first_wavelength or self._current_wavelength()):g}",
            "ray_count": str(sample_count),
            "source_model": SOURCE_MODEL_ZEMAX_RAYFILE,
            "source_power": "1.0",
            "source_x": "0.0",
            "source_y": "0.0",
            "source_z": "0.0",
            "source_l": "0.0",
            "source_m": "0.0",
            "source_n": "1.0",
            "scene_sources": source_specs,
            "scene_row_order": SOURCE_ROW_ORDER_AFTER_OBJECT,
            "trace_mode": "Auto",
            "nonseq_target_surface": "Auto",
            "analysis_surface": "Auto",
            "aperture_type": "EPD",
            "aperture_value": "250",
            "field_type": "Object Height",
            "field_value": "0.0",
            "field_count": "1",
        }
        self._apply_layout_settings(settings)
        self._normalize_special_rows()
        self._sync_table()
        self.layout_var.set("Common Optical Layout")
        self.machine_vision_var.set("Machine Vision Lens")
        self.example_var.set("Examples")
        self._commit_history_capture()
        self.refresh_plot(suppress_analysis=True)
        source_label = "example" if source == "example" else "file"
        total_records = sum(int(spec.get("record_count", 0) or 0) for spec in source_specs)
        self.status_var.set(
            f"Imported Zemax NSC rayfile {source_label} {path.name}: "
            f"{len(source_specs)} illumination source(s), {total_records:,} source rays available, "
            f"{sample_count} sampled rays per source."
        )

    def _load_zemax_prescription_path(self, path: Path, *, source: str = "file") -> None:
        path = Path(path)
        try:
            source_refs = find_zemax_nsc_source_files(path)
        except Exception:
            source_refs = []
        if source_refs:
            self._load_zemax_rayfile_source_path(path, source_refs, source=source)
            return
        try:
            info = _load_zemax_zmx_data(path)
        except Exception as exc:
            messagebox.showerror(
                "Zemax import failed",
                f"Could not import {path.name}.\n\n{_short_error_message(exc)}",
                parent=self,
            )
            self.status_var.set(f"Zemax import failed: {_short_error_message(exc)}")
            return

        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception:
            pass
        self._begin_history_capture()
        self.current_layout_file = None
        self.rows = self._normalized_rows_copy([self._row_from_layout_item(item) for item in info["surfaces"]])
        self._auto_assign_missing_elements(self.rows)
        self._apply_layout_settings(info.get("settings", {}))
        self._normalize_special_rows()
        self._sync_table()
        self.layout_var.set("Common Optical Layout")
        self.machine_vision_var.set("Machine Vision Lens")
        self.example_var.set("Examples")
        self._commit_history_capture()
        self.refresh_plot(suppress_analysis=True)
        source_label = "example" if source == "example" else "file"
        self.status_var.set(
            f"Imported Zemax {source_label} {path.name} ({len(self.rows)} surfaces). Save As to store a Kraken layout."
        )

    def load_zemax_example_file(self, path: Path) -> None:
        self._load_zemax_prescription_path(Path(path), source="example")

    def import_zemax_file(self) -> None:
        initial_dirs = [
            ZEMAX_ATTACHMENT_DIR,
            ATTACHMENT_LENS_DIR,
            LEGACY_TESTING_DIR / "zemax",
            Path.home() / "Lens",
            Path.home(),
        ]
        initial_dir = next((candidate for candidate in initial_dirs if candidate.exists()), Path.home())
        path = filedialog.askopenfilename(
            title="Import Zemax prescription or NSC source file",
            initialdir=str(initial_dir),
            filetypes=[
                ("Zemax prescription/source", "*.zmx *.ZMX"),
                ("All files", "*"),
            ],
            parent=self,
        )
        if not path:
            return
        self._load_zemax_prescription_path(Path(path), source="file")

    def import_zemax_wavefront_map(self) -> None:
        initial_dirs = [
            ATTACHMENT_DIR,
            ATTACHMENT_LENS_DIR,
            LEGACY_TESTING_DIR,
            Path.home() / "Lens",
            Path.home(),
        ]
        initial_dir = next((path for path in initial_dirs if path.exists()), Path.home())
        path = filedialog.askopenfilename(
            title="Import Zemax Wavefront Map text export",
            initialdir=str(initial_dir),
            filetypes=[
                ("Zemax Wavefront Map text", "*.txt *.TXT"),
                ("All files", "*"),
            ],
            parent=self,
        )
        if not path:
            return
        try:
            reference = load_zemax_wavefront_map(path)
        except Exception as exc:
            messagebox.showerror(
                "Zemax Wavefront Map import failed",
                f"Could not import {Path(path).name}.\n\n{_short_error_message(exc)}",
                parent=self,
            )
            self.status_var.set(f"Zemax Wavefront Map import failed: {_short_error_message(exc)}")
            return
        self._zemax_wavefront_reference = reference
        self._last_zemax_wavefront_comparison = None
        message = (
            f"Imported Zemax Wavefront Map {Path(reference.path).name}: "
            f"{reference.shape[1]}x{reference.shape[0]}, lambda={reference.wavelength_um:.6g} um, "
            f"PV={reference.pv_waves:.6g} waves, RMS={reference.rms_waves:.6g} waves."
        )
        self.append_debug(message)
        self.status_var.set(message + " Run WFront/Update to compare.")
        self._mark_plot_update_pending()

    def clear_zemax_wavefront_reference(self) -> None:
        self._zemax_wavefront_reference = None
        self._last_zemax_wavefront_comparison = None
        self.status_var.set("Zemax Wavefront Map reference cleared.")
        self._mark_plot_update_pending()

    @staticmethod
    def _stock_lens_rows_from_catalog_item(
        part_number: str,
        catalog_item: dict,
        *,
        inverse: bool = False,
        gap_after: float = 25.0,
    ) -> list[SurfaceRow]:
        surfaces = Kos.cat2surf(catalog_item, inverse=bool(inverse), Glass="AIR")
        if not surfaces:
            raise ValueError(f"{part_number} does not contain importable optical surfaces.")
        surface_keys = [
            key
            for key in _catalog_surface_keys(catalog_item)
            if catalog_item[key].get("Diameter") not in (None, 0)
        ]
        if inverse:
            surface_keys = list(reversed(surface_keys))
        rows: list[SurfaceRow] = []
        for index, surface in enumerate(surfaces, start=1):
            surface.Name = f"{part_number} S{index}"
            row = KrakenLayoutEditor._row_from_surface(surface, 1, 3)
            row.element = str(part_number).strip()
            if row.surface in {"Object", "Image"}:
                row.surface = "Standard"
            row.name = str(surface.Name)
            source_surface = catalog_item.get(surface_keys[index - 1], {}) if index <= len(surface_keys) else {}
            trace_glass, glass_note = _stock_lens_trace_glass(row.glass, source_surface)
            if glass_note:
                row.advanced = dict(row.advanced or {})
                row.advanced["Note"] = glass_note
            row.glass = trace_glass
            rows.append(row)
        rows[-1].thickness = float(gap_after)
        rows[-1].glass = "AIR"
        note = f"Imported from stock lens catalog part {part_number}."
        if inverse:
            note += " Reversed orientation."
        rows[0].advanced = dict(rows[0].advanced or {})
        existing_note = str(rows[0].advanced.get("Note", "") or "").strip()
        rows[0].advanced["Note"] = f"{note} {existing_note}".strip()
        return rows

    def _insert_surface_rows(self, new_rows: list[SurfaceRow], insert_after: int | None = None) -> int:
        if not new_rows:
            return -1
        self.rows, insert_at = _surface_table_insert_surface_rows(
            self.rows,
            new_rows,
            insert_after=insert_after,
        )
        self._normalize_special_rows()
        self._sync_table()
        items = self.table.get_children()
        selected_items = items[insert_at : insert_at + len(new_rows)]
        if selected_items:
            self.table.selection_set(selected_items)
            self.table.focus(selected_items[0])
            self.table.see(selected_items[0])
        return insert_at

    def _main_stock_lens_importer_dialog(self) -> MainStockLensImporterDialog:
        dialog = self.__dict__.get("_main_stock_lens_importer_dialog_instance")
        if dialog is None:
            dialog = MainStockLensImporterDialog(
                self,
                available_stock_lens_catalogs=_available_stock_lens_catalogs,
                load_stock_lens_catalog=_load_stock_lens_catalog,
                stock_lens_summary=_stock_lens_summary,
                short_error_message=_short_error_message,
            )
            self._main_stock_lens_importer_dialog_instance = dialog
        return dialog

    def open_stock_lens_importer(self, *, path_placement: dict[str, object] | None = None) -> None:
        self._main_stock_lens_importer_dialog().open_stock_lens_importer(path_placement=path_placement)

    def open_layout(self) -> None:
        if ATTACHMENT_DIR.exists():
            initial_dir = ATTACHMENT_DIR
        elif LAYOUTS_DIR.exists():
            initial_dir = LAYOUTS_DIR
        else:
            initial_dir = PROJECT_ROOT
        path = filedialog.askopenfilename(
            title="Open Kraken layout",
            initialdir=str(initial_dir),
            filetypes=[("Python layout", "*.py")],
        )
        if not path:
            return
        self.current_layout_file = Path(path)
        info: dict[str, object] = {"surfaces": [], "settings": {}}
        try:
            info = _load_python_data(Path(path))
            self.rows = self._normalized_rows_copy([self._row_from_layout_item(item) for item in info["surfaces"]])
        except Exception:
            surfaces = self._extract_surfaces_from_example(Path(path))
            self.rows = self._normalized_rows_copy(
                [self._row_from_surface(surface, index, len(surfaces)) for index, surface in enumerate(surfaces)]
            )
        self._auto_assign_missing_elements(self.rows)
        self._apply_layout_settings(info.get("settings", {}))
        self._normalize_special_rows()
        self._sync_table()
        self.refresh_plot(suppress_analysis=True)
        self._mark_saved_state()
        self.status_var.set(f"Opened {Path(path).name}. Click Update to run analysis.")

    def save_layout(self) -> bool:
        self._commit_pending_table_edit()
        if self.current_layout_file is None:
            return self.save_layout_as()
        self._write_layout_file(self.current_layout_file)
        return True

    def save_layout_as(self) -> bool:
        self._commit_pending_table_edit()
        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        path = filedialog.asksaveasfilename(
            title="Save Kraken layout",
            initialdir=str(SCREENSHOT_DIR),
            defaultextension=".py",
            filetypes=[("Python layout", "*.py")],
        )
        if not path:
            return False
        self.current_layout_file = Path(path)
        self._write_layout_file(self.current_layout_file)
        self.load_layouts()
        return True

    def export_3d_step(self) -> None:
        """Export the current 3D viewer geometry as a STEP assembly."""
        worker = getattr(self, "_step_export_thread", None)
        if worker is not None and worker.is_alive():
            messagebox.showinfo(
                "3D STEP Export",
                "A STEP export is already running. Wait for it to finish before starting another export.",
                parent=self,
            )
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
            self._normalize_special_rows()
        except Exception:
            pass
        stem = "kraken_3d_assembly"
        if self.current_layout_file is not None:
            stem = f"{self.current_layout_file.stem}_3d"
        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        path = filedialog.asksaveasfilename(
            title="Export 3D Assembly STEP",
            initialdir=str(SCREENSHOT_DIR),
            initialfile=f"{stem}.step",
            defaultextension=".step",
            filetypes=[
                ("STEP", "*.step"),
                ("STEP", "*.stp"),
                ("All files", "*"),
            ],
            parent=self,
        )
        if not path:
            return
        output_path = Path(path).expanduser()
        try:
            self._begin_analysis_progress("3D STEP export")
            self.status_var.set("Exporting 3D STEP...")
            self._update_analysis_progress("Building optical system", 1, 8)
            self.update_idletasks()
            capture = io.StringIO()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                with redirect_stdout(capture), redirect_stderr(capture):
                    system = self.build_system()
            captured = capture.getvalue()
            if captured:
                self.append_debug(captured)
            if self._has_imported_step_cad():
                def cad_progress(label, done, total):
                    self._update_analysis_progress(label, 1 + int(done), 8)

                cad_shapes = self._collect_native_step_export_shapes(progress_callback=cad_progress)
                self._update_analysis_progress("Tracing ray envelope", 5, 8)
                ray_polylines = self._step_export_ray_polylines(system)
                rows_snapshot = [SurfaceRow(**asdict(row)) for row in self.rows]
                self._start_native_step_export_worker(
                    system,
                    rows_snapshot,
                    cad_shapes,
                    ray_polylines,
                    output_path,
                )
                return
            else:
                # Try analytic export (revolution surfaces) first — much smaller files
                try:
                    self._update_analysis_progress("Collecting edge geometry", 2, 5)
                    edge_extras = self._collect_step_edge_and_extra_meshes(system)
                    self._update_analysis_progress("Writing analytic STEP", 4, 5)
                    analytic, faceted, tris = _write_step_with_analytic_surfaces(
                        system, self.rows, edge_extras, output_path,
                    )
                    message = (
                        f"3D STEP exported: {output_path.name} | "
                        f"analytic_surfaces={analytic}, edge_meshes={faceted}, "
                        f"edge_facets={tris}"
                    )
                except Exception as analytic_exc:
                    import traceback as _tb
                    _tb_text = ''.join(_tb.format_exception(analytic_exc))
                    print(f"[STEP] Analytic export failed:\n{_tb_text}", file=sys.stderr, flush=True)
                    self.append_debug(
                        f"Analytic STEP export failed:\n{_tb_text}\n"
                        f"Using shell-based faceted fallback."
                    )
                    self._update_analysis_progress("Collecting faceted geometry", 3, 5)
                    mesh_items = self._collect_3d_step_export_meshes(system)
                    self._update_analysis_progress("Writing faceted STEP", 4, 5)
                    mesh_count, triangle_count = _write_meshes_to_faceted_step(
                        mesh_items,
                        output_path,
                    )
                    message = (
                        f"3D STEP exported (faceted shell): {output_path.name} | "
                        f"meshes={mesh_count}, facets={triangle_count}"
                    )
            self.status_var.set(message)
            self.append_progress(message)
            self._finish_analysis_progress("3D STEP export", success=True)
        except Exception as exc:
            error = _short_error_message(exc)
            self.status_var.set(f"3D STEP export failed: {error}")
            self.append_debug(f"3D STEP export failed: {exc}")
            self._finish_analysis_progress("3D STEP export", success=False)
            messagebox.showerror(
                "3D STEP Export Error",
                f"Failed to export 3D STEP:\n\n{error}",
                parent=self,
            )

    def _start_native_step_export_worker(
        self,
        system,
        rows_snapshot: list[SurfaceRow],
        cad_shapes: list[tuple[str, object]],
        ray_polylines: list[np.ndarray],
        output_path: Path,
    ) -> None:
        progress_queue: Queue = Queue()

        def worker() -> None:
            try:
                counts = _write_step_with_cad_shapes_and_rays(
                    system,
                    rows_snapshot,
                    cad_shapes,
                    ray_polylines,
                    output_path,
                    progress_callback=lambda label, done, total: progress_queue.put(
                        ("progress", str(label), int(done), int(total))
                    ),
                )
                progress_queue.put(("done", counts))
            except Exception as exc:
                progress_queue.put(("error", _short_error_message(exc), traceback.format_exc()))

        thread = threading.Thread(target=worker, name="kraken-step-export", daemon=True)
        self._step_export_thread = thread
        self._step_export_queue = progress_queue
        self._step_export_output_path = output_path
        self._step_export_ray_count = len(ray_polylines)
        self.status_var.set("Writing 3D STEP in background...")
        self.append_progress(
            f"3D STEP writer started: {output_path.name} | ray_envelopes={len(ray_polylines)}"
        )
        try:
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start(80)
        except Exception:
            pass
        self.progress_spinner_var.set("...")
        self.progress_percent_var.set("writing")
        thread.start()
        self.after(120, self._poll_native_step_export_worker)

    def _poll_native_step_export_worker(self) -> None:
        queue = getattr(self, "_step_export_queue", None)
        thread = getattr(self, "_step_export_thread", None)
        if queue is None or thread is None:
            return
        terminal_payload = None
        while True:
            try:
                payload = queue.get_nowait()
            except Empty:
                break
            if not payload:
                continue
            kind = payload[0]
            if kind == "progress":
                _kind, label, done, total = payload
                self.progress_spinner_var.set("...")
                self.progress_percent_var.set(str(label))
                if str(label) != "Writing STEP file":
                    self.append_progress(f"3D STEP export: {label} ({done}/{total})")
            elif kind in {"done", "error"}:
                terminal_payload = payload

        if terminal_payload is None:
            if thread.is_alive():
                self.after(160, self._poll_native_step_export_worker)
                return
            terminal_payload = ("error", "STEP writer exited without reporting a result", "")

        try:
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
        except Exception:
            pass
        self._step_export_thread = None
        self._step_export_queue = None

        if terminal_payload[0] == "done":
            _kind, counts = terminal_payload
            analytic_count, cad_count, ray_count = counts
            output_path = Path(getattr(self, "_step_export_output_path", ""))
            message = (
                f"3D STEP exported (native CAD + ray envelope): {output_path.name} | "
                f"analytic_surfaces={analytic_count}, native_steps={cad_count}, ray_envelopes={ray_count}"
            )
            self.status_var.set(message)
            self.append_progress(message)
            self._finish_analysis_progress("3D STEP export", success=True)
            return

        _kind, error, tb_text = terminal_payload
        self.status_var.set(f"3D STEP export failed: {error}")
        if tb_text:
            self.append_debug(f"3D STEP export failed:\n{tb_text}")
        self._finish_analysis_progress("3D STEP export", success=False)
        messagebox.showerror(
            "3D STEP Export Error",
            f"Failed to export 3D STEP:\n\n{error}",
            parent=self,
        )

    def _main_lens_drawing_dialogs(self) -> MainLensDrawingDialogs:
        dialog = self.__dict__.get("_main_lens_drawing_dialogs_instance")
        if dialog is None:
            dialog = MainLensDrawingDialogs(self, screenshot_dir=SCREENSHOT_DIR)
            self._main_lens_drawing_dialogs_instance = dialog
        return dialog

    def _open_lens_drawing_surface_properties_dialog(self, *, for_export: bool = False) -> bool:
        return self._main_lens_drawing_dialogs()._open_lens_drawing_surface_properties_dialog(for_export=for_export)

    def export_lens_drawing(self) -> None:
        self._main_lens_drawing_dialogs().export_lens_drawing()

    def _layout_file_writer_service(self) -> LayoutFileWriterService:
        service = self.__dict__.get("_layout_file_writer_service_instance")
        if service is None:
            service = LayoutFileWriterService(self)
            self._layout_file_writer_service_instance = service
        return service

    def _write_layout_file(self, path: Path) -> None:
        self._layout_file_writer_service()._write_layout_file(path)

    def _extract_surfaces_from_example(self, path: Path):
        original_system = Kos.system
        original_display2d = getattr(Kos, "display2d", None)
        original_display3d = getattr(Kos, "display3d", None)
        original_display2d_colab = getattr(Kos, "display2d_colab", None)
        example_dir = str(path.parent)
        previous_sys_path = list(sys.path)
        try:
            package_name = "KrakenOS.Examples" if path.parent.resolve() == EXAMPLES_DIR.resolve() else None
        except Exception:
            package_name = None

        def capture_system(surf_data, setup, build=1):
            raise _CapturedExample(list(surf_data))

        try:
            Kos.system = capture_system
            if original_display2d is not None:
                Kos.display2d = lambda *args, **kwargs: None
            if original_display3d is not None:
                Kos.display3d = lambda *args, **kwargs: None
            if original_display2d_colab is not None:
                Kos.display2d_colab = lambda *args, **kwargs: None

            namespace = {
                "__name__": "__main__",
                "__file__": str(path),
                "__package__": package_name,
            }
            code = path.read_text(encoding="utf-8", errors="ignore")
            try:
                previous_cwd = os.getcwd()
                os.chdir(path.parent)
                if example_dir not in sys.path:
                    sys.path.insert(0, example_dir)
                exec(compile(code, str(path), "exec"), namespace, namespace)
            except _CapturedExample as captured:
                return captured.surfaces
            except SystemExit as exc:
                raise ValueError(
                    f"Example {path.name} exited before defining a UI-loadable KrakenOS system."
                ) from exc
            finally:
                os.chdir(previous_cwd)
                sys.path[:] = previous_sys_path
        finally:
            Kos.system = original_system
            if original_display2d is not None:
                Kos.display2d = original_display2d
            if original_display3d is not None:
                Kos.display3d = original_display3d
            if original_display2d_colab is not None:
                Kos.display2d_colab = original_display2d_colab

        raise ValueError("No KrakenOS system definition was captured from the example.")

    @staticmethod
    def _example_file_is_menu_loadable(path: Path) -> bool:
        return example_file_is_menu_loadable(path)

    @staticmethod
    def _example_file_has_import_side_effects(code: str) -> bool:
        return example_file_has_import_side_effects(code)

    @staticmethod
    def _surface_attrs_used_in_example(path: Path) -> list[str]:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []
        surf_vars = set(re.findall(r"^(\w+)\s*=\s*Kos\.surf\(\)", text, flags=re.M))
        if not surf_vars:
            return []
        attrs = {
            attr
            for var, attr in re.findall(r"^(\w+)\.(\w+)\s*=.*$", text, flags=re.M)
            if var in surf_vars
        }
        return sorted(attrs)

    @classmethod
    def _unsupported_example_surface_attrs(cls, path: Path) -> list[str]:
        attrs = cls._surface_attrs_used_in_example(path)
        return [attr for attr in attrs if attr not in EXAMPLE_SUPPORTED_SURFACE_ATTRS]

    @staticmethod
    def _surface_attr_differs_from_default(surface, default_surface, attr: str) -> bool:
        value = getattr(surface, attr, None)
        default = getattr(default_surface, attr, None)
        if isinstance(value, (int, float, np.floating)) or isinstance(default, (int, float, np.floating)):
            try:
                return abs(float(value) - float(default)) > 1e-12
            except Exception:
                return str(value) != str(default)
        if isinstance(value, (list, tuple, np.ndarray)) or isinstance(default, (list, tuple, np.ndarray)):
            try:
                left = np.asarray(value, dtype=float)
                right = np.asarray(default, dtype=float)
                if left.shape != right.shape:
                    return True
                return not np.allclose(left, right, atol=1e-12, rtol=0.0)
            except Exception:
                return repr(value) != repr(default)
        return value != default

    def _active_unsupported_example_surface_attrs(self, path: Path, surfaces: list[object]) -> list[str]:
        unsupported = self._unsupported_example_surface_attrs(path)
        if not unsupported or not surfaces:
            return unsupported
        default_surface = Kos.surf()
        active = []
        for attr in unsupported:
            if any(self._surface_attr_differs_from_default(surface, default_surface, attr) for surface in surfaces):
                active.append(attr)
        return active

    def _report_example_feature_gaps(self, example_name: str, path: Path, surfaces: list[object]) -> bool:
        unsupported = self._active_unsupported_example_surface_attrs(path, surfaces)
        if not unsupported:
            self.append_debug(f"Example {example_name}: UI supports all explicit surface attributes used in the source.")
            return False
        preview = ", ".join(unsupported[:6])
        if len(unsupported) > 6:
            preview += f", +{len(unsupported) - 6} more"
        self.append_debug(
            f"Example {example_name}: unsupported or partially supported surface attributes in UI: "
            + ", ".join(unsupported)
        )
        self.status_var.set(
            f"Loaded example {example_name}. UI does not fully support: {preview}. Click Update to run analysis."
        )
        return True

    @staticmethod
    def _row_from_surface(surface, index: int, total: int) -> SurfaceRow:
        surface_type = "Standard"
        if index == 0:
            surface_type = "Object"
        elif index == total - 1:
            surface_type = "Image"
        elif getattr(surface, "Thin_Lens", 0.0) != 0:
            surface_type = "Thin Lens"
        elif getattr(surface, "Diff_Ord", 0.0) != 0:
            surface_type = "Grating"
        elif isinstance(getattr(surface, DIFFUSE_SCATTER_ADVANCED_ATTR, None), dict) and getattr(surface, DIFFUSE_SCATTER_ADVANCED_ATTR):
            surface_type = DIFFUSE_OBJECT_SURFACE
        elif hasattr(surface, BEAM_SPLITTER_ADVANCED_ATTR):
            surface_type = BEAM_SPLITTER_SURFACE
        elif str(getattr(surface, "Glass", "AIR")).upper() == "MIRROR":
            surface_type = "Mirror"

        rc_value = float(getattr(surface, "Rc", 0.0))
        if surface_type == "Thin Lens":
            rc_value = float(getattr(surface, "Thin_Lens", 0.0))
        extra_data_value = getattr(surface, "ExtraData", 0.0)
        encoded_extra_data = encode_custom_surface_value(extra_data_value)
        if encoded_extra_data is not None:
            extra_data_value = encoded_extra_data
        try:
            if np.all(np.asarray(extra_data_value, dtype=object) == 0):
                extra_data_value = 0.0
        except Exception:
            pass
        uda_value = getattr(surface, "UDA", "None")
        if uda_value is None:
            uda_value = "None"

        return SurfaceRow(
            surface=surface_type,
            name=str(getattr(surface, "Name", "") or f"Surface {index}"),
            rc=rc_value,
            k=float(getattr(surface, "k", 0.0)),
            axicon=float(getattr(surface, "Axicon", 0.0)),
            diff_ord=float(getattr(surface, "Diff_Ord", 0.0)),
            grating_d=float(getattr(surface, "Grating_D", 0.0)),
            grating_angle=float(getattr(surface, "Grating_Angle", 0.0)),
            thickness=float(getattr(surface, "Thickness", 0.0)),
            diameter=float(getattr(surface, "Diameter", 25.0)),
            in_diameter=float(getattr(surface, "InDiameter", 0.0)),
            drawing=float(getattr(surface, "Drawing", 1.0)),
            extra_data=extra_data_value,
            uda=uda_value,
            tilt_x=float(getattr(surface, "TiltX", 0.0)),
            tilt_y=float(getattr(surface, "TiltY", 0.0)),
            tilt_z=float(getattr(surface, "TiltZ", 0.0)),
            desp_x=float(getattr(surface, "DespX", 0.0)),
            desp_y=float(getattr(surface, "DespY", 0.0)),
            desp_z=float(getattr(surface, "DespZ", 0.0)),
            axis_move=float(getattr(surface, "AxisMove", 0.0)),
            glass=str(getattr(surface, "Glass", "AIR")),
            advanced={
                attr: getattr(surface, attr)
                for attr in ADVANCED_SURFACE_ATTR_NAMES
                if hasattr(surface, attr)
                and KrakenLayoutEditor._surface_attr_differs_from_default(surface, Kos.surf(), attr)
            },
        )

    @classmethod
    def _row_from_layout_item(cls, item: dict) -> SurfaceRow:
        return SurfaceRow(
            surface=str(item.get("surface", cls._infer_surface_type(item))),
            element=str(item.get("element", "")),
            name=str(item.get("name", "Surface")),
            optimize_rc=_coerce_opt_flag(item.get("optimize_rc", item.get("opt_rc", ""))),
            optimize_rc_bounds=_coerce_bounds(item.get("optimize_rc_bounds")),
            rc=float(item.get("rc", 0.0)),
            k=float(item.get("k", item.get("K", 0.0))),
            axicon=float(item.get("axicon", 0.0)),
            diff_ord=float(item.get("diff_ord", item.get("Diff_Ord", 0.0))),
            grating_d=float(item.get("grating_d", item.get("Grating_D", 0.0))),
            grating_angle=float(item.get("grating_angle", item.get("Grating_Angle", 0.0))),
            optimize_thickness=_coerce_opt_flag(item.get("optimize_thickness", item.get("opt_thickness", ""))),
            optimize_thickness_bounds=_coerce_bounds(item.get("optimize_thickness_bounds")),
            thickness=float(item.get("thickness", 0.0)),
            diameter=float(item.get("diameter", 25.0)),
            in_diameter=float(item.get("in_diameter", item.get("InDiameter", 0.0))),
            drawing=float(item.get("drawing", item.get("Drawing", 1.0))),
            extra_data=item.get("extra_data", item.get("ExtraData", 0.0)),
            uda=item.get("uda", item.get("UDA", "None")),
            advanced=_advanced_surface_attrs_from_spec(item),
            tilt_x=float(item.get("tilt_x", 0.0)),
            tilt_y=float(item.get("tilt_y", 0.0)),
            tilt_z=float(item.get("tilt_z", 0.0)),
            desp_x=float(item.get("desp_x", 0.0)),
            desp_y=float(item.get("desp_y", 0.0)),
            desp_z=float(item.get("desp_z", 0.0)),
            axis_move=float(item.get("axis_move", 0.0)),
            glass=str(item.get("glass", "AIR")),
        )

    @staticmethod
    def _infer_surface_type(item: dict) -> str:
        if "surface" in item:
            return str(item["surface"])
        name = str(item.get("name", "")).strip().lower()
        if name == "object":
            return "Object"
        if name == "image":
            return "Image"
        glass = str(item.get("glass", "AIR")).strip().upper()
        if abs(float(item.get("diff_ord", item.get("Diff_Ord", 0.0)))) > 1e-12:
            return "Grating"
        if glass == "MIRROR" and "object" in name and "target" in name:
            return OBJECT_TARGET_SURFACE
        advanced = item.get("advanced", item.get("advanced_attrs", item.get("surface_attrs", {})))
        if isinstance(advanced, dict) and any(_canonical_advanced_surface_attr(key) == DIFFUSE_SCATTER_ADVANCED_ATTR for key in advanced):
            return DIFFUSE_OBJECT_SURFACE
        if glass == "MIRROR":
            return "Mirror"
        if isinstance(advanced, dict) and any(_canonical_advanced_surface_attr(key) == BEAM_SPLITTER_ADVANCED_ATTR for key in advanced):
            return BEAM_SPLITTER_SURFACE
        return "Standard"

    def _normalize_special_rows(self) -> None:
        if not self.rows:
            return
        self.rows[0].element = ""
        self.rows[0].advanced = dict(self.rows[0].advanced or {})
        self.rows[0].advanced.pop(ELEMENT_ADVANCED_ATTR, None)
        self.rows[0].surface = "Object"
        if not self.rows[0].name or self.rows[0].name == "Surface":
            self.rows[0].name = "Object"
        self._clear_disabled_surface_type_fields(self.rows[0])
        final_image_is_detector = self._row_has_detector_output_metadata(self.rows[-1])
        if not final_image_is_detector:
            self.rows[-1].element = ""
        self.rows[-1].advanced = dict(self.rows[-1].advanced or {})
        if not final_image_is_detector:
            self.rows[-1].advanced.pop(ELEMENT_ADVANCED_ATTR, None)
        self.rows[-1].surface = "Image"
        if not self.rows[-1].name or self.rows[-1].name == "Surface":
            self.rows[-1].name = "Image"
        self._clear_disabled_surface_type_fields(self.rows[-1])
        for index, row in enumerate(self.rows[1:-1], start=1):
            if self._is_open3d_promoted_optical_solid_row(row):
                row.axis_move = 0.0
            if row.surface == "Aperture":
                if not row.name or row.name in {"Surface", "Standard"}:
                    row.name = "Aperture"
                row.glass = "AIR"
                row.rc = 0.0
                row.tilt_y = 0.0
                row.tilt_z = 0.0
            elif row.surface in REFLECTIVE_PROXY_SURFACES:
                row.glass = "MIRROR"
                if row.surface == DIFFUSE_OBJECT_SURFACE:
                    advanced = dict(row.advanced or {})
                    advanced[DIFFUSE_SCATTER_ADVANCED_ATTR] = _normalize_diffuse_scatter_settings(
                        advanced.get(DIFFUSE_SCATTER_ADVANCED_ATTR, DIFFUSE_SCATTER_DEFAULT_SETTINGS)
                    )
                    row.advanced = advanced
            elif row.surface == BEAM_SPLITTER_SURFACE:
                if str(row.glass).upper() == "MIRROR":
                    row.glass = "AIR"
                advanced = dict(row.advanced or {})
                splitter_settings = _normalize_beam_splitter_settings(advanced.get(BEAM_SPLITTER_ADVANCED_ATTR))
                advanced[BEAM_SPLITTER_ADVANCED_ATTR] = splitter_settings
                advanced["Coating"] = _beam_splitter_coating_for_settings(splitter_settings, advanced.get("Coating"))
                row.advanced = advanced
            elif row.glass == "MIRROR":
                row.glass = "AIR"
            self._clear_disabled_surface_type_fields(row)
        self._apply_image_diameter_mode()

    @staticmethod
    def _flipped_name(name: str) -> str:
        placeholder_front = "__KR_FRONT__"
        placeholder_back = "__KR_BACK__"
        placeholder_left = "__KR_LEFT__"
        placeholder_right = "__KR_RIGHT__"
        placeholder_entry = "__KR_ENTRY__"
        placeholder_exit = "__KR_EXIT__"
        value = name
        value = re.sub(r"\bFront\b", placeholder_front, value, flags=re.IGNORECASE)
        value = re.sub(r"\bBack\b", placeholder_back, value, flags=re.IGNORECASE)
        value = re.sub(r"\bLeft\b", placeholder_left, value, flags=re.IGNORECASE)
        value = re.sub(r"\bRight\b", placeholder_right, value, flags=re.IGNORECASE)
        value = re.sub(r"\bEntry\b", placeholder_entry, value, flags=re.IGNORECASE)
        value = re.sub(r"\bExit\b", placeholder_exit, value, flags=re.IGNORECASE)
        value = value.replace(placeholder_front, "Back")
        value = value.replace(placeholder_back, "Front")
        value = value.replace(placeholder_left, "Right")
        value = value.replace(placeholder_right, "Left")
        value = value.replace(placeholder_entry, "Exit")
        value = value.replace(placeholder_exit, "Entry")
        return value


def main() -> None:
    app = KrakenLayoutEditor()
    app.mainloop()


if __name__ == "__main__":
    main()
