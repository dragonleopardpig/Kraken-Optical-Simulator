"""Row forms -- dialogs that edit one surface row (docs/design_qt_migration.md phase 3)."""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import (FormAction, FormField, FormFigure, FormPreview,
                                        FormRefused, RecordList, RowForm)
from KrakenOS.UI.row_forms.advanced_surface import build_advanced_surface_form
from KrakenOS.UI.row_forms.beam_splitter import build_beam_splitter_form
from KrakenOS.UI.row_forms.catalog_matcher import build_catalog_matcher_form
from KrakenOS.UI.row_forms.coating_material import build_coating_material_form
from KrakenOS.UI.row_forms.detector_settings import build_detector_settings_form
from KrakenOS.UI.row_forms.diffuse_scatter import build_diffuse_scatter_form
from KrakenOS.UI.row_forms.element_forms import (build_element_settings_form,
                                                 build_path_local_pose_form)
from KrakenOS.UI.row_forms.error_map import build_error_map_form
from KrakenOS.UI.row_forms.glass_catalog import build_glass_catalog_form
from KrakenOS.UI.row_forms.inspection_cell import build_inspection_cell_form
from KrakenOS.UI.row_forms.inspection_part import build_inspection_part_form
from KrakenOS.UI.row_forms.stock_lens import build_stock_lens_form
from KrakenOS.UI.row_forms.path_component import build_path_component_form
from KrakenOS.UI.row_forms.presets import (build_apply_tolerance_preset_form,
                                           build_optimization_bounds_form,
                                           build_save_tolerance_preset_form)
from KrakenOS.UI.row_forms.resize_beam_splitter import build_resize_beam_splitter_form
from KrakenOS.UI.row_forms.scene_sources import build_scene_source_manager_form
from KrakenOS.UI.row_forms.scene_target import build_scene_target_form
from KrakenOS.UI.row_forms.source_edit import build_scene_source_edit_form
from KrakenOS.UI.row_forms.surface_settings import (build_galvo_scan_form,
                                                    build_grating_settings_form)
from KrakenOS.UI.row_forms.surface_shape import build_surface_shape_form

#: name -> builder, for a shell that opens row forms by name
ROW_FORM_BUILDERS = {
    "beam_splitter": build_beam_splitter_form,
    "diffuse_scatter": build_diffuse_scatter_form,
    "error_map": build_error_map_form,
    "coating_material": build_coating_material_form,
    "advanced_surface": build_advanced_surface_form,
    "detector_settings": build_detector_settings_form,
    "scene_target": build_scene_target_form,
    "scene_sources": build_scene_source_manager_form,
    "glass_catalog": build_glass_catalog_form,
    "stock_lens": build_stock_lens_form,
    "inspection_cell": build_inspection_cell_form,
    "source_edit": build_scene_source_edit_form,
    "inspection_part": build_inspection_part_form,
    "surface_shape": build_surface_shape_form,
    "path_component": build_path_component_form,
    "catalog_matcher": build_catalog_matcher_form,
    "galvo_scan": build_galvo_scan_form,
    "grating_settings": build_grating_settings_form,
    "tolerance_preset": build_save_tolerance_preset_form,
    "optimization_bounds": build_optimization_bounds_form,
    "apply_tolerance_preset": build_apply_tolerance_preset_form,
    "resize_beam_splitter": build_resize_beam_splitter_form,
    "path_local_pose": build_path_local_pose_form,
    "element_settings": build_element_settings_form,
}

__all__ = ["FormAction", "FormField", "FormFigure", "FormPreview", "FormRefused",
           "RecordList", "RowForm", "build_beam_splitter_form",
           "build_diffuse_scatter_form", "build_error_map_form",
           "build_coating_material_form", "build_advanced_surface_form",
           "build_detector_settings_form", "build_scene_target_form",
           "build_path_local_pose_form", "build_element_settings_form",
           "build_scene_source_manager_form", "build_glass_catalog_form",
           "build_stock_lens_form", "build_inspection_cell_form",
           "build_scene_source_edit_form", "build_inspection_part_form",
           "build_surface_shape_form", "build_path_component_form",
           "build_catalog_matcher_form", "build_galvo_scan_form",
           "build_grating_settings_form",
           "build_save_tolerance_preset_form", "build_optimization_bounds_form",
           "build_apply_tolerance_preset_form", "build_resize_beam_splitter_form",
           "ROW_FORM_BUILDERS"]
