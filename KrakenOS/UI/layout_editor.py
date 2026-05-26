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
from KrakenOS.UI.services import layout_scene_projection as _layout_scene_projection_module
from KrakenOS.UI.services import layout_table_workbench as _layout_table_workbench_module
from KrakenOS.UI.services import optical_solid_workflow as _optical_solid_workflow_module
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
from KrakenOS.UI.services.analysis_compute_workflow import AnalysisComputeWorkflowMixin
from KrakenOS.UI.services.analysis_reports import AnalysisReportsMixin
from KrakenOS.UI.services.editable_table_rows import EditableTableRowService
from KrakenOS.UI.services.formula_help import FormulaHelpService
from KrakenOS.UI.services.geometric_analysis import GeometricAnalysisMixin
from KrakenOS.UI.services.legacy_3d_scene import Legacy3DSceneService
from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin
from KrakenOS.UI.services.layout_file_writer import LayoutFileWriterService
from KrakenOS.UI.services.layout_import_export import LayoutImportExportMixin
from KrakenOS.UI.services.layout_scene_projection import LayoutSceneProjectionMixin
from KrakenOS.UI.services.layout_settings import LayoutSettingsService
from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin
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
from KrakenOS.UI.services.optical_solid_workflow import LayoutOpticalSolidWorkflowMixin
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
from KrakenOS.UI.services.trace_preview_sampling import TracePreviewSamplingMixin
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


_layout_table_workbench_module._sync_layout_globals(globals())
_layout_scene_projection_module._sync_layout_globals(globals())
_optical_solid_workflow_module._sync_layout_globals(globals())


class KrakenLayoutEditor(SourceModelingMixin, ToleranceModelingMixin, ScenePlacementMixin, LayoutOpticalSolidWorkflowMixin, GeometricAnalysisMixin, LayoutPolylineDisplayMixin, LayoutSceneProjectionMixin, ParaxialToolsMixin, AnalysisReportsMixin, ThreeDSceneToolsMixin, LayoutImportExportMixin, TracePreviewSamplingMixin, AnalysisComputeWorkflowMixin, LayoutTableWorkbenchMixin, tk.Tk):
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



def main() -> None:
    app = KrakenLayoutEditor()
    app.mainloop()


if __name__ == "__main__":
    main()
