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
    camera_image_coverage_mm,
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
from KrakenOS.UI.custom_surfaces import decode_custom_surface_value
from KrakenOS.UI.lens_drawing_export import export_lens_drawing, identify_elements
from KrakenOS.UI.lens_drawing_properties import (
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
from KrakenOS.UI.modern_ttk_theme import apply_modern_ttk_theme
from KrakenOS.UI import optical_solid_metadata
from KrakenOS.UI.services import layout_analysis_display as _layout_analysis_display_module
from KrakenOS.UI.services import layout_plot_interaction as _layout_plot_interaction_module
from KrakenOS.UI.services import layout_scene_bundle_display as _layout_scene_bundle_display_module
from KrakenOS.UI.services import layout_scene_projection as _layout_scene_projection_module
from KrakenOS.UI.services import layout_shell_controls as _layout_shell_controls_module
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
from KrakenOS.UI.services.layout_analysis_display import LayoutAnalysisDisplayMixin
from KrakenOS.UI.services.layout_plot_interaction import LayoutPlotInteractionMixin
from KrakenOS.UI.services.layout_scene_bundle_display import LayoutSceneBundleDisplayMixin
from KrakenOS.UI.services.legacy_3d_scene import Legacy3DSceneService
from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin
from KrakenOS.UI.services.layout_file_writer import LayoutFileWriterService
from KrakenOS.UI.services.layout_import_export import LayoutImportExportMixin
from KrakenOS.UI.services.layout_literals import _UNSERIALIZABLE_LAYOUT_VALUE, _layout_literal_value
from KrakenOS.UI.services.layout_scene_projection import LayoutSceneProjectionMixin
from KrakenOS.UI.services.layout_shell_controls import LayoutShellControlsMixin
from KrakenOS.UI.services.layout_settings import LayoutSettingsService
from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin
from KrakenOS.UI.services.layout_bug_recorder import LayoutBugRecorderMixin
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
from KrakenOS.UI.trace_intent import (
    BEAM_SPLITTER_SURFACE,
    DIFFUSE_OBJECT_SURFACE,
    OBJECT_TARGET_SURFACE,
    resolve_trace_intent,
)
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
vtkCameraOrientationWidget = None
vtkAxesActor = None
vtkActor = None
vtkCellPicker = None
vtkPropPicker = None
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
    return PROJECTION_MODE_FULL_3D


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
from KrakenOS.UI.services.advanced_surface_attrs import (
    ADVANCED_SURFACE_ATTR_NAMES,
    ADVANCED_SURFACE_FIELD_GROUPS,
    DETECTOR_ADVANCED_ATTR,
    DRAWING_PROPERTIES_ADVANCED_ATTR,
    EXAMPLE_SUPPORTED_SURFACE_ATTRS,
    REFLECTIVE_PROXY_SURFACES,
    SCENE_TARGET_ADVANCED_ATTR,
    _advanced_surface_attrs_from_spec,
)
from KrakenOS.UI.services.cad_cache_paths import CAD_CACHE_DIR
from KrakenOS.UI.services.offbeam_optical_solid import neutralize_offbeam_inert_solids
from KrakenOS.UI.services.row_spec_contracts import (
    _requires_scalar_trace,
    _row_specs_signature,
)
from KrakenOS.UI.services.step_overlay_labels import (
    STEP_OVERLAY_LABELS,
    STEP_OVERLAY_LABEL_SET,
    STEP_OVERLAY_DECORATION_LABEL_SET,
    is_step_overlay_decoration,
)
# Project-side scratch directory for ad-hoc screenshots and exports. Not used by
# auto-save (which stays in ~/.cache); only as the *initial* directory for
# user-triggered Save dialogs.
SCREENSHOT_DIR = ATTACHMENT_DIR
DEFAULT_LAYOUT_TITLE = "Doublet Lens"
FOLDED_STARTER_LAYOUT_TITLE = "Double Mirror Fold"
DETECTOR_BINS_DEFAULT = "Auto"
BRANCH_FIELD_PROPAGATION_MM_DEFAULT = "0.0"
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
PROJECTION_MODE_FULL_3D = "Full 3D"
PROJECTION_MODE_AXIS_FIELD = PROJECTION_MODE_FULL_3D
PROJECTION_MODE_VALUES = (PROJECTION_MODE_FULL_3D,)
INSERTABLE_COMMON_LAYOUT_TITLES = {
    "Single Lens",
    "Doublet Lens",
    "Ideal 2F Lens",
    "Flat Mirror 45 Deg",
}
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


def resolve_optical_solid_face_coating(coating_name):
    """Resolve a promoted-solid face's coating NAME (a shared ``COATING_PRESETS`` key, the same
    library the 2D "Coating..." editor uses) into the KrakenOS ``(Coating table, CoatingMet)``
    the non-sequential trace applies through ``CoatingFun`` -- so a face coating means the same
    thing as a sequential-surface coating. Returns None for an empty / "Clear" / free-text
    coating, i.e. NO per-face coating, leaving the trace unchanged (the additive contract)."""
    name = str(coating_name or "").strip()
    if not name:
        return None
    table = COATING_PRESETS.get(name)
    if not table or table == [[], [], [], []]:
        return None
    return (table, 0)

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
    group_optical_solid_face_candidates,
    group_brep_optical_solid_faces,
    optical_solid_face_candidate_triangles,
    optical_solid_face_record_triangles,
    optical_solid_metadata_is_brep,
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
    _normalize_native_variable_name,
    _native_variable_names,
    _parse_float_sequence_text,
    _dedupe_float_values,
    _format_float_sequence,
    _dedupe_preserve_order,
    _native_variable_matches,
)


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
        projection_display_mode=PROJECTION_MODE_FULL_3D,
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
    global pv, vtkTkRenderWindowInteractor, vtkTubeFilter, vtkOrientationMarkerWidget, vtkCameraOrientationWidget
    global vtkAxesActor, vtkActor, vtkCellPicker, vtkPropPicker, vtkDataSetMapper, vtkRenderer, vtkTextActor, vtkBillboardTextActor3D
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
        try:
            from vtkmodules.vtkInteractionWidgets import vtkCameraOrientationWidget as _vtk_camera_orient
        except Exception:
            _vtk_camera_orient = None
        from vtkmodules.vtkRenderingAnnotation import vtkAxesActor as _vtk_axes
        from vtkmodules.vtkRenderingCore import (
            vtkActor as _vtk_actor,
            vtkCellPicker as _vtk_picker,
            vtkDataSetMapper as _vtk_mapper,
            vtkPropPicker as _vtk_prop_picker,
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
        vtkCameraOrientationWidget = _vtk_camera_orient
        vtkAxesActor = _vtk_axes
        vtkActor = _vtk_actor
        vtkCellPicker = _vtk_picker
        vtkPropPicker = _vtk_prop_picker
        vtkDataSetMapper = _vtk_mapper
        vtkRenderer = _vtk_renderer
        vtkTextActor = _vtk_text_actor
        vtkBillboardTextActor3D = _vtk_billboard_text_actor_3d
    except Exception:
        vtkTkRenderWindowInteractor = None
        vtkTubeFilter = None
        vtkOrientationMarkerWidget = None
        vtkCameraOrientationWidget = None
        vtkAxesActor = None
        vtkActor = None
        vtkCellPicker = None
        vtkPropPicker = None
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


def _build_system_from_specs(
    row_specs: list[dict],
    *,
    build: int = 0,
    setup=None,
    apply_optical_solid_output_ports: bool = True,
) -> object:
    # bugs/0065: a promoted optical SOLID parked clear of the beam is a
    # display-only scene body, not an optical element. Its lateral decenter
    # would otherwise propagate as a surface.DespX/DespY coordinate break and
    # corrupt the centered paraxial / best-focus / image-circle solve (the
    # off-beam cube "chasing" the rays). Replace each off-beam inert solid with
    # a flat zero-power AIR surface BEFORE both the surface loop and the
    # output-port overrides below, preserving the surface count and axial chain.
    # The 3-D body still draws -- the inspector keys on the row overlay, not on
    # these transient build specs (cf. the bugs/0021 missing-mesh neutralisation).
    row_specs = neutralize_offbeam_inert_solids(row_specs)
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
        # Per-face coating: resolve each promoted-solid face's coating NAME (a shared
        # COATING_PRESETS key, the same library the 2D "Coating..." editor uses) into the
        # KrakenOS (Coating table, CoatingMet) and stash it on the built surface keyed by
        # face_id, so the non-sequential trace applies it through CoatingFun -- the same physics
        # as a sequential-surface coating. Transient (never persisted); absent for non-solid
        # surfaces or clear/free-text faces, so those traces are unchanged (the additive contract).
        solid_faces = getattr(surface, "OpticalSolidFaces", None)
        if solid_faces:
            face_coatings: dict[str, tuple] = {}
            for face in normalize_optical_solid_face_metadata(solid_faces).get("faces", []) or []:
                face_id = str(face.get("face_id", "") or "").strip()
                resolved = resolve_optical_solid_face_coating(face.get("coating"))
                if face_id and resolved is not None:
                    face_coatings[face_id] = resolved
            if face_coatings:
                surface.OpticalSolidFaceCoatingTables = face_coatings
        # bugs/0021: a file-backed Solid_3d_stl whose cached mesh is missing on
        # this machine (a layout opened on another box without the CAD cache,
        # or one the user Skipped in the missing-assets dialog) must NOT reach
        # Prerequisites3D's pv.read -- that raises FileNotFoundError and aborts
        # the ENTIRE system build, collapsing every surface so the whole Open
        # 3D view goes blank. Neutralise it to "None" on the built Surf so the
        # analytic single-face fallback runs and the rest of the system builds.
        # The row's stored path is left untouched (the relocate dialog can
        # still find it), and the 3D view still draws its red missing-asset
        # placeholder, which keys on the row's MissingResourceState, not here.
        solid_stl = getattr(surface, "Solid_3d_stl", "None")
        if isinstance(solid_stl, str) and solid_stl.strip() and solid_stl != "None":
            if not _resolve_project_file_path(solid_stl).exists():
                surface.Solid_3d_stl = "None"
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
        if spec["surface"] == "Aperture":
            # bugs/0093: mark the aperture stop so the non-seq trace VIGNETTES rays
            # landing outside its clear aperture, instead of skipping the finite stop
            # and shooting them straight through (the cube-before-lens diverging rays).
            surface.IsApertureStop = True
        surfaces.append(surface)
    metal_catalogs = _metal_catalogs_from_row_specs(row_specs)
    _build_t0 = time.perf_counter()
    system = Kos.system(surfaces, _shared_setup(metal_catalogs) if setup is None else setup, build=int(build))
    # Timing: the build=1 path runs Prerequisites3D ("Creating solid objects"), the slow
    # one. Logged so summarize_open3d_timing surfaces it (it is NOT inside refresh_scene).
    try:
        from KrakenOS.UI.services.open3d_timing import open3d_timing_event

        open3d_timing_event(
            "build_system_from_specs",
            build=int(build),
            surfaces=len(surfaces),
            duration_ms=round(float((time.perf_counter() - _build_t0) * 1000.0), 3),
        )
    except Exception:
        pass
    # bugs/0166: the output-port overrides force a full build=1 pyVista solid mesh
    # when the system has none (the ``needs_build`` path in nonseq_output_ports) so
    # the non-seq trace can intersect the solids. A paraxial-only consumer (the
    # per-branch pupil / first-order reference built with build=0) never NS-traces
    # through the meshes -- it only runs PupilCalc -- so applying the overrides
    # there force-meshes the beam-splitter solid once PER BRANCH for nothing. Such
    # callers pass ``apply_optical_solid_output_ports=False`` to skip the force build.
    if apply_optical_solid_output_ports:
        apply_optical_solid_output_port_system_overrides(system, row_specs)
    return system


def _build_cached_system_from_specs(row_specs: list[dict]) -> object:
    global _WORKER_SYSTEM_CACHE_SIGNATURE, _WORKER_SYSTEM_CACHE_SYSTEM
    signature = _row_specs_signature(row_specs)
    if _WORKER_SYSTEM_CACHE_SYSTEM is None or _WORKER_SYSTEM_CACHE_SIGNATURE != signature:
        _WORKER_SYSTEM_CACHE_SYSTEM = _build_system_from_specs(row_specs, build=0)
        _WORKER_SYSTEM_CACHE_SIGNATURE = signature
    return _WORKER_SYSTEM_CACHE_SYSTEM


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
_layout_shell_controls_module._sync_layout_globals(globals())
_layout_analysis_display_module._sync_layout_globals(globals())
_layout_plot_interaction_module._sync_layout_globals(globals())
_layout_scene_bundle_display_module._sync_layout_globals(globals())


class KrakenLayoutEditor(SourceModelingMixin, ToleranceModelingMixin, ScenePlacementMixin, LayoutOpticalSolidWorkflowMixin, LayoutShellControlsMixin, LayoutPlotInteractionMixin, GeometricAnalysisMixin, LayoutAnalysisDisplayMixin, LayoutSceneBundleDisplayMixin, LayoutPolylineDisplayMixin, LayoutSceneProjectionMixin, ParaxialToolsMixin, AnalysisReportsMixin, ThreeDSceneToolsMixin, LayoutImportExportMixin, TracePreviewSamplingMixin, AnalysisComputeWorkflowMixin, LayoutTableWorkbenchMixin, LayoutBugRecorderMixin, tk.Tk):
    def report_callback_exception(self, exc, val, tb) -> None:
        """Surface uncaught callback errors instead of failing silently.

        Tkinter's default handler prints the traceback to the console only,
        so a button whose callback raises looks like it did nothing at all
        (e.g. the surface-shape-builder ``NameError``). Keep the full
        traceback in the console / Debug log, but also show a short,
        dismissible dialog so no UI action fails silently. Suppressed in
        headless mode so automated runs never block on a modal dialog.
        """
        import traceback

        traceback.print_exception(exc, val, tb)
        try:
            self.append_debug("".join(traceback.format_exception(exc, val, tb)))
        except Exception:
            pass
        if getattr(self, "headless", False):
            return
        try:
            messagebox.showerror(
                "KrakenOS — action could not complete",
                f"{val.__class__.__name__}: {val}\n\n"
                "This action stopped before finishing. The full details are "
                "in the console / Debug log.",
            )
        except Exception:
            pass

    def __init__(self, *, headless: bool = False) -> None:
        super().__init__()
        self._kraken_ttk_style = apply_modern_ttk_theme(self)
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
        self.show_layout_2d = True
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
        # bugs/0053: per-row thickness-dimension measurement re-anchor overrides.
        # row index -> {"endpoint": "start"|"end", "ref_z": float, "ref_label": str}.
        # A re-anchored dimension reports the distance to the picked surface/edge z
        # instead of the adjacent surface; it never moves an optical surface. The
        # LED/object row uses led_step_object_edge_local_z instead of this map.
        self._dimension_anchor_overrides: dict[int, dict] = {}
        # Per-row Thickness dimension visibility: row indices whose blue thickness
        # overlay arrow is turned off individually (the global toggle is
        # show_physical_distances_var). Persisted in layout_settings.
        self._hidden_thickness_dimension_rows: set[int] = set()
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
        self.bind_all("<Control-Shift-B>", self._flag_bug_2d_event, add="+")
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
















def main() -> None:
    app = KrakenLayoutEditor()
    app.mainloop()


if __name__ == "__main__":
    main()
