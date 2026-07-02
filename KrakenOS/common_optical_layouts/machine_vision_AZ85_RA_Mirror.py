#!/usr/bin/env python3
TITLE = "Machine Vision Az85 Ra Mirror"

SETTINGS = {'object_mode': 'Finite',
 'display_orientation': 'YZ',
 'projection_display_mode': 'Full 3D',
 'wavelength': '0.55',
 'ray_count': '31',
 'ray_height_factor': '0.8',
 'full_pupil': False,
 'source_model': 'Pupil / field',
 'pupil_pattern': 'Meridional fan',
 'source_radius': '5.0',
 'source_cone_angle': '0.0',
 'gaussian_input_mode': 'Waist + offset',
 'gaussian_waist_radius': '0.5',
 'gaussian_waist_offset': '0.0',
 'gaussian_beam_diameter': '1.0',
 'gaussian_full_divergence': '1.0',
 'gaussian_waist_side': 'Waist before source',
 'gaussian_m2': '1.0',
 'pupil_rad': '0.0',
 'pupil_theta': '0.0',
 'source_power': '1.0',
 'source_seed': '1',
 'source_x': '0.0',
 'source_y': '0.0',
 'source_z': '0.0',
 'source_l': '0.0',
 'source_m': '0.0',
 'source_n': '1.0',
 'source_angular_weight': 'Uniform solid angle',
 'scene_sources': [],
 'scene_row_order': 'after_object',
 'analysis_surface': 'Auto',
 'analysis_branch_filter': 'All paths',
 'ray_display_mode': 'All rays',
 'detector_bins': 'Auto',
 'coherent_sum_mode': 'By source ray',
 'branch_field_propagation_mm': '0.0',
 'aperture_type': 'FNO',
 'aperture_value': '4.5',
 'spot_view_mode': 'Grid',
 'wavefront_style': 'Wavefront Function',
 'tolerance_compare_view': 'Spot overlay',
 'show_clipped_rays': False,
 'show_path_labels': True,
 'show_cardinals': True,
 'show_physical_distances': True,
 'field_type': 'Real Image Height',
 'field_value': '16.2917402385',
 'field_count': '3',
 'atmos_plot_mode': 'Refraction / dispersion',
 'atmos_observatory': 'Manual',
 'atmos_wavelength_min': '0.45',
 'atmos_wavelength_max': '0.75',
 'atmos_wavelength_count': '11',
 'atmos_zenith_deg': '45.0',
 'atmos_temperature_k': '283.15',
 'atmos_pressure_pa': '101300',
 'atmos_humidity': '0.5',
 'atmos_co2_ppm': '400',
 'atmos_latitude_deg': '31.0',
 'atmos_altitude_m': '2800',
 'image_diameter_mode': 'Manual',
 'trace_mode': 'Auto',
 'folded_detector_policy': 'Trace events',
 'nonseq_target_surface': 'Auto',
 'nonseq_ns_limit': '200',
 'nonseq_energy_probability': False,
 'camera_model': 'Allied Vision hr25MCX',
 'branch_detector_camera_assignments': {},
 'step_clear_aperture_by_label': {},
 'optical_led_glued': False,
 'camera_step_path': 'attachment/Cameras/3D_CAD_HR25xCXP.STEP',
 'camera_step_rotation_x_deg': 0.0,
 'camera_step_rotation_y_deg': 0.0,
 'camera_step_rotation_z_deg': 270.0,
 'camera_step_axis_offset_xy': [0.0, 0.0],
 'camera_step_placement_offset_xyz': [0.0, 0.0, 0.0],
 'lens_step_path': 'attachment/Lens/ELS-85-4.5V16K.STEP',
 'lens_step_largest_component_only': False,
 'lens_step_rotation_x_deg': 0.0,
 'lens_step_rotation_y_deg': 0.0,
 'lens_step_rotation_z_deg': 0.0,
 'lens_step_axis_offset_xy': [0.0, 0.0],
 'lens_step_placement_offset_xyz': [0.0, 0.0, -3.8489504874276896],
 'optical_step_path': '',
 'optical_step_rotation_x_deg': 0.0,
 'optical_step_rotation_y_deg': 0.0,
 'optical_step_rotation_z_deg': 0.0,
 'optical_step_axis_offset_xy': [0.0, 0.0],
 'optical_step_placement_offset_xyz': [0.0, 0.0, 0.0],
 'led_step_path': '',
 'led_step_rotation_x_deg': 0.0,
 'led_step_rotation_y_deg': 0.0,
 'led_step_rotation_z_deg': 0.0,
 'led_object_edge_distance_mm': 0.0,
 'led_step_object_edge_local_z': '',
 'dimension_anchor_overrides': {},
 'hidden_thickness_dimension_rows': [],
 'led_step_axis_offset_xy': [0.0, 0.0],
 'led_step_placement_offset_xyz': [0.0, 0.0, 0.0],
 'analysis_mode': 'none',
 'analysis_modes': [],
 'layout_preview_mode': 'none',
 'auto_save_plot': False,
 'external_camera': 'None',
 'camera_overlay_mode': 'Off',
 'metal_catalogs': [],
 'optimization_workers': 'Auto',
 'selected_operands': ['Spot RMS'],
 'operands': {'EFFL': {'weight': '1',
                       'target': '100',
                       'wavelength': '0.55',
                       'field': '0',
                       'surface': 'Auto'},
              'Wavefront RMS': {'weight': '1',
                                'target': '0',
                                'wavelength': '0.55',
                                'field': '0',
                                'surface': 'Auto'},
              'Exit pupil z': {'weight': '1',
                               'target': '0',
                               'wavelength': '0.55',
                               'field': '0',
                               'surface': 'Auto'},
              'MTF @ freq': {'weight': '1',
                             'target': '0.5',
                             'wavelength': '0.55',
                             'field': '0',
                             'field_x': '0',
                             'field_y': '0',
                             'surface': 'Auto',
                             'frequency': '5',
                             'mtf_mode': 'Average',
                             'mtf_algorithm': 'PSF FFT'},
              'Thickness penalty': {'weight': '1',
                                    'target': '0.1',
                                    'wavelength': '0.55',
                                    'field': '0',
                                    'surface': 'Auto'},
              'Magnification': {'weight': '1',
                                'target': '1',
                                'wavelength': '0.55',
                                'field': '0',
                                'surface': 'Auto'},
              'Spot RMS': {'weight': '1',
                           'target': '0',
                           'wavelength': '0.55',
                           'field': '0',
                           'surface': 'Auto'},
              'Entrance pupil z': {'weight': '1',
                                   'target': '0',
                                   'wavelength': '0.55',
                                   'field': '0',
                                   'surface': 'Auto'}},
 'tolerance_solve_presets': [],
 'tolerance_manufacturing_templates': [],
 'active_tolerance_solve_preset': ''}

from pathlib import Path
import KrakenOS as Kos
import numpy as np
from KrakenOS.UI.custom_surfaces import decode_custom_surface_value
from KrakenOS.UI.nonseq_output_ports import apply_optical_solid_output_port_system_overrides
from KrakenOS.UI.saved_layout_plot import display_saved_layout_2d
from KrakenOS.UI.source_trace_helpers import build_saved_layout_rays


def build_system():
    surfaces = []
    s0 = Kos.surf()
    s0.Name = 'Object at 1X'
    s0.Rc = 0.0
    s0.k = 0.0
    s0.Axicon = 0.0
    s0.Diff_Ord = 0.0
    s0.Grating_D = 0.0
    s0.Grating_Angle = 0.0
    s0.Thickness = 59.3971370586
    s0.Diameter = 32.5834804771
    s0.InDiameter = 0.0
    s0.Drawing = 1.0
    s0.TiltX = 0.0
    s0.TiltY = 0.0
    s0.TiltZ = 0.0
    s0.DespX = 0.0
    s0.DespY = 0.0
    s0.DespZ = 0.0
    s0.AxisMove = 0.0
    s0.Glass = 'AIR'
    surfaces.append({'surface': 'Object', 'element': '', 'name': 'Object at 1X', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 59.3971370586, 'diameter': 32.5834804771, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s1 = Kos.surf()
    s1.Name = 'Promoted OPTICAL STEP optical solid'
    s1.Rc = 0.0
    s1.k = 0.0
    s1.Axicon = 0.0
    s1.Diff_Ord = 0.0
    s1.Grating_D = 0.0
    s1.Grating_Angle = 0.0
    s1.Thickness = 40.0
    s1.Diameter = 25.0
    s1.InDiameter = 0.0
    s1.Drawing = 1.0
    s1.TiltX = 0.0
    s1.TiltY = 0.0
    s1.TiltZ = 0.0
    s1.DespX = -3.5527136788e-15
    s1.DespY = 2.30926389122e-14
    s1.DespZ = 12.5
    s1.AxisMove = 0.0
    s1.Glass = 'BK7'
    s1.Note = ('Promoted from an Open 3D imported STEP overlay. The cached Solid_3d_stl mesh is saved in local '
 'coordinates around the overlay center, while row Desp stores the scene/world center. AxisMove '
 "stays zero so the scene object's placement does not move downstream Object/Image rows; explicit "
 'output ports provide the separate follower-row workflow. Review material and CAD/STL optical '
 'face roles before relying on traced physics.')
    s1.OpticalSolidFaces = {'faces': [{'analytic_parameters': {'axis': [0.7071067811865478, -0.7071067811865474, 0.0],
                                    'origin': [-4.910391898791896e-15, 17.677669529663696, 25.0]},
            'area_mm2': 625.0,
            'assignment_source': 'step_analytic_transformed',
            'centroid': [-12.499999999999993, 1.9042545318370797e-16, 0.0],
            'clear_aperture_mm': 0.0,
            'coating': '',
            'component_face_id': 'S001/F001',
            'duplicate_group': '',
            'face_id': 'S001/F001',
            'fit_reference': 'Auto',
            'flip_normal': False,
            'function': 'Transmit/Port',
            'input_offset_u_mm': 0.0,
            'input_offset_v_mm': 0.0,
            'interior_duplicate': False,
            'loss': 0.0,
            'material': '',
            'normal': [-1.0, 2.48689957516035e-16, -5.329070518200751e-16],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 12.499999999999993,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Front',
            'source_face_id': 'S001/F001',
            'source_face_index': 1,
            'source_solid_index': 1,
            'split_ratio': 0.5,
            'suggested_function': 'Unassigned',
            'suggested_port_role': 'Auto',
            'suggested_side_2d': 'Auto',
            'suggestion_confidence': 0.0,
            'suggestion_reason': '',
            'suggestion_source': '',
            'surface_type': 'plane',
            'triangle_count': 2,
            'triangle_indices': [0, 1]},
           {'analytic_parameters': {'axis': [6.536822994078938e-32, 1.0, -0.0],
                                    'origin': [-17.677669529663685, 4.167311260893123e-15, 25.0]},
            'area_mm2': 883.883476483184,
            'assignment_source': 'manual',
            'centroid': [7.411372905261749e-15, -1.4841472440202734e-15, 0.0],
            'clear_aperture_mm': 0.0,
            'coating': '',
            'component_face_id': 'S001/F002',
            'duplicate_group': '',
            'face_id': 'S001/F002',
            'fit_reference': 'Auto',
            'flip_normal': False,
            'function': 'Mirror',
            'input_offset_u_mm': 0.0,
            'input_offset_v_mm': 0.0,
            'interior_duplicate': False,
            'loss': 0.0,
            'material': '',
            'normal': [0.7071067811865477, -3.044723295879577e-16, -0.7071067811865475],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 5.2406320392128286e-15,
            'port_role': 'Interaction Surface',
            'recovered_coating': False,
            'role': 'Mirror',
            'side_2d': 'Left',
            'source_face_id': 'S001/F002',
            'source_face_index': 2,
            'source_solid_index': 1,
            'split_ratio': 0.5,
            'suggested_function': 'Unassigned',
            'suggested_port_role': 'Auto',
            'suggested_side_2d': 'Auto',
            'suggestion_confidence': 0.0,
            'suggestion_reason': '',
            'suggestion_source': '',
            'surface_type': 'plane',
            'triangle_count': 2,
            'triangle_indices': [2, 3]},
           {'analytic_parameters': {'axis': [-0.7071067811865478, -0.7071067811865474, 0.0],
                                    'origin': [17.67766952966368, 4.167311260893121e-15, 25.0]},
            'area_mm2': 625.0,
            'assignment_source': 'step_analytic_transformed',
            'centroid': [-8.52651282912121e-17, -1.7337242752546428e-16, 12.5],
            'clear_aperture_mm': 0.0,
            'coating': '',
            'component_face_id': 'S001/F003',
            'duplicate_group': '',
            'face_id': 'S001/F003',
            'fit_reference': 'Auto',
            'flip_normal': False,
            'function': 'Transmit/Port',
            'input_offset_u_mm': 0.0,
            'input_offset_v_mm': 0.0,
            'interior_duplicate': False,
            'loss': 0.0,
            'material': '',
            'normal': [0.0, 0.0, 1.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 12.5,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Right',
            'source_face_id': 'S001/F003',
            'source_face_index': 3,
            'source_solid_index': 1,
            'split_ratio': 0.5,
            'suggested_function': 'Unassigned',
            'suggested_port_role': 'Auto',
            'suggested_side_2d': 'Auto',
            'suggestion_confidence': 0.0,
            'suggestion_reason': '',
            'suggestion_source': '',
            'surface_type': 'plane',
            'triangle_count': 2,
            'triangle_indices': [4, 5]},
           {'analytic_parameters': {'axis': [0.0, 0.0, -1.0],
                                    'origin': [-3.469446951953614e-15, 17.677669529663696, 25.0]},
            'area_mm2': 312.4999999999999,
            'assignment_source': 'step_analytic_transformed',
            'centroid': [-4.166666666666665, -12.5, 4.166666666666671],
            'clear_aperture_mm': 0.0,
            'coating': '',
            'component_face_id': 'S001/F004',
            'duplicate_group': '',
            'face_id': 'S001/F004',
            'fit_reference': 'Auto',
            'flip_normal': False,
            'function': 'Transmit/Port',
            'input_offset_u_mm': 0.0,
            'input_offset_v_mm': 0.0,
            'interior_duplicate': False,
            'loss': 0.0,
            'material': '',
            'normal': [-1.4210854715202004e-16, -1.0, 1.4210854715202002e-16],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 12.5,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Down',
            'source_face_id': 'S001/F004',
            'source_face_index': 4,
            'source_solid_index': 1,
            'split_ratio': 0.5,
            'suggested_function': 'Unassigned',
            'suggested_port_role': 'Auto',
            'suggested_side_2d': 'Auto',
            'suggestion_confidence': 0.0,
            'suggestion_reason': '',
            'suggestion_source': '',
            'surface_type': 'plane',
            'triangle_count': 1,
            'triangle_indices': [6]},
           {'analytic_parameters': {'axis': [0.0, 0.0, -1.0],
                                    'origin': [-3.469446951953614e-15, 17.677669529663696, 0.0]},
            'area_mm2': 312.5,
            'assignment_source': 'step_analytic_transformed',
            'centroid': [-4.166666666666659, 12.5, 4.166666666666671],
            'clear_aperture_mm': 0.0,
            'coating': '',
            'component_face_id': 'S001/F005',
            'duplicate_group': '',
            'face_id': 'S001/F005',
            'fit_reference': 'Auto',
            'flip_normal': False,
            'function': 'Transmit/Port',
            'input_offset_u_mm': 0.0,
            'input_offset_v_mm': 0.0,
            'interior_duplicate': False,
            'loss': 0.0,
            'material': '',
            'normal': [1.4210854715202004e-16, 1.0, -1.4210854715201997e-16],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 12.5,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Up',
            'source_face_id': 'S001/F005',
            'source_face_index': 5,
            'source_solid_index': 1,
            'split_ratio': 0.5,
            'suggested_function': 'Unassigned',
            'suggested_port_role': 'Auto',
            'suggested_side_2d': 'Auto',
            'suggestion_confidence': 0.0,
            'suggestion_reason': '',
            'suggestion_source': '',
            'surface_type': 'plane',
            'triangle_count': 1,
            'triangle_indices': [7]}],
 'interior_duplicate_count': 0,
 'metadata_coordinates': 'local_centered_promoted_row',
 'outer_face_count': 5,
 'promoted_face_metadata_source': 'open3d_step_overlay',
 'source_backend': 'OpenCascade',
 'source_face_count': 5,
 'source_step': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Right_Angle_Mirror/87931/step_87391.step',
 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/promoted_step_overlays/optical_3758591d220374fd.stl',
 'version': 1,
 'virtual_planes': []}
    s1.OpticalSolidSourceFormat = 'STEP'
    s1.OpticalSolidSourcePath = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Right_Angle_Mirror/87931/step_87391.step'
    s1.ScenePlacement = {'anchor': 'row_pose',
 'enabled': True,
 'grid_extent_mm': 50.000000000000014,
 'grid_spacing_mm': 2.500000000000001,
 'grid_visible': True,
 'promotion_mesh_coordinates': 'local_centered_from_open3d_overlay',
 'promotion_source': 'open3d_step_overlay',
 'promotion_source_step_path': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Right_Angle_Mirror/87931/step_87391.step',
 'promotion_step_label': 'optical',
 'snap_deg': 5.0,
 'snap_enabled': True,
 'snap_mm': 1.2500000000000004}
    s1.Solid_3d_stl = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/promoted_step_overlays/optical_3758591d220374fd.stl'
    s1.StepOverlayPromotion = {'axial_reserve_mm': 40.0,
 'axis_offset_xy': [0.0, 0.0],
 'bounds_max_world': [12.5, 12.500000000000025, 84.3971370585792],
 'bounds_min_world': [-12.500000000000007, -12.499999999999979, 59.397137058579204],
 'center_world': [-3.552713678800501e-15, 2.3092638912203256e-14, 71.8971370585792],
 'largest_component_only': None,
 'mesh_coordinates': 'local_centered_from_open3d_overlay',
 'placement_offset_xyz': [-6.25, 2.398081733190338e-14, 65.6471370585792],
 'preserved_face_count': 5,
 'promoted_mesh_path': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/promoted_step_overlays/optical_3758591d220374fd.stl',
 'row_thickness_mm': 40.0,
 'source_step_path': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Right_Angle_Mirror/87931/step_87391.step',
 'step_label': 'optical',
 'step_rotation_deg': [89.99999999999999, 315.0, 7.016709298534872e-15]}
    surfaces.append({'surface': 'Standard', 'element': 'OPTICAL STEP solid', 'name': 'Promoted OPTICAL STEP optical solid', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 40.0, 'diameter': 25.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {'Note': "Promoted from an Open 3D imported STEP overlay. The cached Solid_3d_stl mesh is saved in local coordinates around the overlay center, while row Desp stores the scene/world center. AxisMove stays zero so the scene object's placement does not move downstream Object/Image rows; explicit output ports provide the separate follower-row workflow. Review material and CAD/STL optical face roles before relying on traced physics.", 'OpticalSolidFaces': {'version': 1, 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/promoted_step_overlays/optical_3758591d220374fd.stl', 'faces': [{'face_id': 'S001/F001', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Front', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [-1.0, 2.48689957516035e-16, -5.329070518200751e-16], 'centroid': [-12.499999999999993, 1.9042545318370797e-16, 0.0], 'area_mm2': 625.0, 'triangle_count': 2, 'triangle_indices': [0, 1], 'plane_offset_mm': 12.499999999999993, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'step_analytic_transformed', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F001', 'source_face_id': 'S001/F001', 'source_solid_index': 1, 'source_face_index': 1, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-4.910391898791896e-15, 17.677669529663696, 25.0], 'axis': [0.7071067811865478, -0.7071067811865474, 0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F002', 'role': 'Mirror', 'function': 'Mirror', 'side_2d': 'Left', 'port_role': 'Interaction Surface', 'fit_reference': 'Auto', 'normal': [0.7071067811865477, -3.044723295879577e-16, -0.7071067811865475], 'centroid': [7.411372905261749e-15, -1.4841472440202734e-15, 0.0], 'area_mm2': 883.883476483184, 'triangle_count': 2, 'triangle_indices': [2, 3], 'plane_offset_mm': 5.2406320392128286e-15, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'manual', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F002', 'source_face_id': 'S001/F002', 'source_solid_index': 1, 'source_face_index': 2, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-17.677669529663685, 4.167311260893123e-15, 25.0], 'axis': [6.536822994078938e-32, 1.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F003', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Right', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, 0.0, 1.0], 'centroid': [-8.52651282912121e-17, -1.7337242752546428e-16, 12.5], 'area_mm2': 625.0, 'triangle_count': 2, 'triangle_indices': [4, 5], 'plane_offset_mm': 12.5, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'step_analytic_transformed', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F003', 'source_face_id': 'S001/F003', 'source_solid_index': 1, 'source_face_index': 3, 'surface_type': 'plane', 'analytic_parameters': {'origin': [17.67766952966368, 4.167311260893121e-15, 25.0], 'axis': [-0.7071067811865478, -0.7071067811865474, 0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F004', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Down', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [-1.4210854715202004e-16, -1.0, 1.4210854715202002e-16], 'centroid': [-4.166666666666665, -12.5, 4.166666666666671], 'area_mm2': 312.4999999999999, 'triangle_count': 1, 'triangle_indices': [6], 'plane_offset_mm': 12.5, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'step_analytic_transformed', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F004', 'source_face_id': 'S001/F004', 'source_solid_index': 1, 'source_face_index': 4, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-3.469446951953614e-15, 17.677669529663696, 25.0], 'axis': [0.0, 0.0, -1.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F005', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Up', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [1.4210854715202004e-16, 1.0, -1.4210854715201997e-16], 'centroid': [-4.166666666666659, 12.5, 4.166666666666671], 'area_mm2': 312.5, 'triangle_count': 1, 'triangle_indices': [7], 'plane_offset_mm': 12.5, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'step_analytic_transformed', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F005', 'source_face_id': 'S001/F005', 'source_solid_index': 1, 'source_face_index': 5, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-3.469446951953614e-15, 17.677669529663696, 0.0], 'axis': [0.0, 0.0, -1.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}], 'virtual_planes': [], 'source_step': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Right_Angle_Mirror/87931/step_87391.step', 'source_backend': 'OpenCascade', 'source_face_count': 5, 'outer_face_count': 5, 'interior_duplicate_count': 0, 'promoted_face_metadata_source': 'open3d_step_overlay', 'metadata_coordinates': 'local_centered_promoted_row'}, 'OpticalSolidSourceFormat': 'STEP', 'OpticalSolidSourcePath': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Right_Angle_Mirror/87931/step_87391.step', 'ScenePlacement': {'enabled': True, 'anchor': 'row_pose', 'snap_enabled': True, 'snap_mm': 1.2500000000000004, 'snap_deg': 5.0, 'grid_visible': True, 'grid_spacing_mm': 2.500000000000001, 'grid_extent_mm': 50.000000000000014, 'promotion_source': 'open3d_step_overlay', 'promotion_step_label': 'optical', 'promotion_source_step_path': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Right_Angle_Mirror/87931/step_87391.step', 'promotion_mesh_coordinates': 'local_centered_from_open3d_overlay'}, 'Solid_3d_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/promoted_step_overlays/optical_3758591d220374fd.stl', 'StepOverlayPromotion': {'step_label': 'optical', 'source_step_path': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Right_Angle_Mirror/87931/step_87391.step', 'promoted_mesh_path': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/promoted_step_overlays/optical_3758591d220374fd.stl', 'mesh_coordinates': 'local_centered_from_open3d_overlay', 'center_world': [-3.552713678800501e-15, 2.3092638912203256e-14, 71.8971370585792], 'bounds_min_world': [-12.500000000000007, -12.499999999999979, 59.397137058579204], 'bounds_max_world': [12.5, 12.500000000000025, 84.3971370585792], 'row_thickness_mm': 40.0, 'axial_reserve_mm': 40.0, 'step_rotation_deg': [89.99999999999999, 315.0, 7.016709298534872e-15], 'axis_offset_xy': [0.0, 0.0], 'placement_offset_xyz': [-6.25, 2.398081733190338e-14, 65.6471370585792], 'largest_component_only': None, 'preserved_face_count': 5}}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': -3.5527136788e-15, 'desp_y': 2.30926389122e-14, 'desp_z': 12.5, 'axis_move': 0.0, 'glass': 'BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s2 = Kos.surf()
    s2.Name = 'Promoted OPTICAL STEP optical solid -> next gap (AIR)'
    s2.Rc = 0.0
    s2.k = 0.0
    s2.Axicon = 0.0
    s2.Diff_Ord = 0.0
    s2.Grating_D = 0.0
    s2.Grating_Angle = 0.0
    s2.Thickness = 42.4528629414
    s2.Diameter = 25.0
    s2.InDiameter = 0.0
    s2.Drawing = 1.0
    s2.TiltX = 0.0
    s2.TiltY = 0.0
    s2.TiltZ = 0.0
    s2.DespX = 0.0
    s2.DespY = 0.0
    s2.DespZ = 0.0
    s2.AxisMove = 0.0
    s2.Glass = 'AIR'
    s2.InPathTrailingSpacer = True
    surfaces.append({'surface': 'Standard', 'element': 'OPTICAL STEP solid', 'name': 'Promoted OPTICAL STEP optical solid -> next gap (AIR)', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 42.4528629414, 'diameter': 25.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {'InPathTrailingSpacer': True}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s3 = Kos.surf()
    s3.Name = 'Front Optical Vertex Datum'
    s3.Rc = 0.0
    s3.k = 0.0
    s3.Axicon = 0.0
    s3.Diff_Ord = 0.0
    s3.Grating_D = 0.0
    s3.Grating_Angle = 0.0
    s3.Thickness = 17.638524767
    s3.Diameter = 29.0
    s3.InDiameter = 0.0
    s3.Drawing = 1.0
    s3.TiltX = 0.0
    s3.TiltY = 0.0
    s3.TiltZ = 0.0
    s3.DespX = 0.0
    s3.DespY = 0.0
    s3.DespZ = 0.0
    s3.AxisMove = 0.0
    s3.Glass = 'AIR'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'Front Optical Vertex Datum', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 17.638524767, 'diameter': 29.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s4 = Kos.surf()
    s4.Name = 'Blackbox Group 1'
    s4.Rc = 159.488524767
    s4.k = 0.0
    s4.Axicon = 0.0
    s4.Diff_Ord = 0.0
    s4.Grating_D = 0.0
    s4.Grating_Angle = 0.0
    s4.Thickness = 9.86152751788
    s4.Diameter = 29.0
    s4.InDiameter = 0.0
    s4.Drawing = 1.0
    s4.TiltX = 0.0
    s4.TiltY = 0.0
    s4.TiltZ = 0.0
    s4.DespX = 0.0
    s4.DespY = 0.0
    s4.DespZ = 0.0
    s4.AxisMove = 0.0
    s4.Glass = 'AIR'
    s4.Thin_Lens = 159.488524767
    s4.Rc = 0.0
    surfaces.append({'surface': 'Thin Lens', 'element': 'Blackbox Group 1', 'name': 'Blackbox Group 1', 'rc': 159.488524767, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 9.86152751788, 'diameter': 29.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s5 = Kos.surf()
    s5.Name = 'Aperture Stop F/4.5'
    s5.Rc = 0.0
    s5.k = 0.0
    s5.Axicon = 0.0
    s5.Diff_Ord = 0.0
    s5.Grating_D = 0.0
    s5.Grating_Angle = 0.0
    s5.Thickness = 9.86152751788
    s5.Diameter = 18.8888888889
    s5.InDiameter = 0.0
    s5.Drawing = 1.0
    s5.TiltX = 0.0
    s5.TiltY = 0.0
    s5.TiltZ = 0.0
    s5.DespX = 0.0
    s5.DespY = 0.0
    s5.DespZ = 0.0
    s5.AxisMove = 0.0
    s5.Glass = 'AIR'
    surfaces.append({'surface': 'Aperture', 'element': 'Aperture Stop F/4.5', 'name': 'Aperture Stop F/4.5', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 9.86152751788, 'diameter': 18.8888888889, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s6 = Kos.surf()
    s6.Name = 'Blackbox Group 2'
    s6.Rc = 159.488524767
    s6.k = 0.0
    s6.Axicon = 0.0
    s6.Diff_Ord = 0.0
    s6.Grating_D = 0.0
    s6.Grating_Angle = 0.0
    s6.Thickness = 17.638524767
    s6.Diameter = 27.26
    s6.InDiameter = 0.0
    s6.Drawing = 1.0
    s6.TiltX = 0.0
    s6.TiltY = 0.0
    s6.TiltZ = 0.0
    s6.DespX = 0.0
    s6.DespY = 0.0
    s6.DespZ = 0.0
    s6.AxisMove = 0.0
    s6.Glass = 'AIR'
    s6.Thin_Lens = 159.488524767
    s6.Rc = 0.0
    surfaces.append({'surface': 'Thin Lens', 'element': 'Blackbox Group 2', 'name': 'Blackbox Group 2', 'rc': 159.488524767, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 17.638524767, 'diameter': 27.26, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s7 = Kos.surf()
    s7.Name = 'Rear Optical Vertex Datum'
    s7.Rc = 0.0
    s7.k = 0.0
    s7.Axicon = 0.0
    s7.Diff_Ord = 0.0
    s7.Grating_D = 0.0
    s7.Grating_Angle = 0.0
    s7.Thickness = 150.367932489
    s7.Diameter = 27.26
    s7.InDiameter = 0.0
    s7.Drawing = 1.0
    s7.TiltX = 0.0
    s7.TiltY = 0.0
    s7.TiltZ = 0.0
    s7.DespX = 0.0
    s7.DespY = 0.0
    s7.DespZ = 0.0
    s7.AxisMove = 0.0
    s7.Glass = 'AIR'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'Rear Optical Vertex Datum', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 150.367932489, 'diameter': 27.26, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s8 = Kos.surf()
    s8.Name = 'Image / Sensor at 1X'
    s8.Rc = 0.0
    s8.k = 0.0
    s8.Axicon = 0.0
    s8.Diff_Ord = 0.0
    s8.Grating_D = 0.0
    s8.Grating_Angle = 0.0
    s8.Thickness = 0.0
    s8.Diameter = 32.5834804771
    s8.InDiameter = 0.0
    s8.Drawing = 1.0
    s8.TiltX = 0.0
    s8.TiltY = 0.0
    s8.TiltZ = 0.0
    s8.DespX = 0.0
    s8.DespY = 0.0
    s8.DespZ = 0.0
    s8.AxisMove = 0.0
    s8.Glass = 'AIR'
    surfaces.append({'surface': 'Image', 'element': '', 'name': 'Image / Sensor at 1X', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 0.0, 'diameter': 32.5834804771, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    return surfaces


SURFACES = build_system()


def build_runtime_system():
    surface_dicts = SURFACES
    runtime_surfaces = []
    clear_aperture = max((max(float(spec['diameter']), 1.0) for spec in surface_dicts if spec['surface'] not in {'Object', 'Image'}), default=100.0) * 4.0
    for spec in surface_dicts:
        s = Kos.surf()
        s.Name = spec['name']
        s.Rc = spec['rc']
        s.k = spec.get('k', spec.get('K', 0.0))
        s.Axicon = spec.get('axicon', 0.0)
        s.Diff_Ord = spec.get('diff_ord', spec.get('Diff_Ord', 0.0))
        s.Grating_D = spec.get('grating_d', spec.get('Grating_D', 0.0))
        s.Grating_Angle = spec.get('grating_angle', spec.get('Grating_Angle', 0.0))
        s.Thickness = spec['thickness']
        s.Diameter = clear_aperture if spec['surface'] == 'Object' else spec['diameter']
        s.InDiameter = spec.get('in_diameter', spec.get('InDiameter', 0.0))
        s.Drawing = spec.get('drawing', spec.get('Drawing', 1.0))
        if 'ExtraData' in spec or 'extra_data' in spec:
            s.ExtraData = decode_custom_surface_value(spec.get('extra_data', spec.get('ExtraData', s.ExtraData)))
        if 'UDA' in spec or 'uda' in spec:
            s.UDA = decode_custom_surface_value(spec.get('uda', spec.get('UDA', s.UDA)))
        for attr, value in spec.get('advanced', {}).items():
            if attr in {'AspherData', 'ZNK'}:
                value = np.asarray(value, dtype=float).ravel()
                min_len = 200 if attr == 'AspherData' else 36
                if value.size < min_len:
                    value = np.pad(value, (0, min_len - value.size), mode='constant')
            elif attr == 'Error_map':
                x_values, y_values, z_values, space = value
                space_arr = np.asarray(space, dtype=float).ravel()
                spacing = float(space_arr[0]) if space_arr.size else 1.0
                value = [np.asarray(x_values, dtype=float).ravel().tolist(), np.asarray(y_values, dtype=float).ravel().tolist(), np.asarray(z_values, dtype=float).ravel().tolist(), spacing]
            setattr(s, attr, value)
        s.TiltX = spec.get('tilt_x', 0.0)
        s.TiltY = spec.get('tilt_y', 0.0)
        s.TiltZ = spec.get('tilt_z', 0.0)
        s.DespX = spec.get('desp_x', 0.0)
        s.DespY = spec.get('desp_y', 0.0)
        s.DespZ = spec.get('desp_z', 0.0)
        s.AxisMove = spec.get('axis_move', 0.0)
        s.Glass = spec['glass']
        if spec['surface'] in {'Mirror', 'Object Target', 'Diffuse Object'}:
            s.Glass = 'MIRROR'
            if abs(s.AxisMove) < 1e-9:
                s.AxisMove = 2.0
        if spec['surface'] == 'Diffuse Object':
            s.DiffuseScatter = spec.get('advanced', {}).get('DiffuseScatter', {'model': 'Lambertian', 'backend': 'Built-in', 'backend_model': 'Microroughness_BRDF_Model', 'backend_parameters': {}, 'reflectance': 0.8, 'sample_count': 9, 'max_scatter_angle_deg': 90.0, 'lobe_exponent': 20.0, 'roughness_deg': 20.0, 'min_branch_power': 1e-4, 'max_branch_depth': 2, 'polarization': 'Preserve projected Jones'})
        if spec['surface'] == 'Beam Splitter':
            splitter = spec.get('advanced', {}).get('BeamSplitter', {'reflectance': 0.5, 'absorption': 0.0})
            r = min(max(float(splitter.get('reflectance', 0.5)), 0.0), 1.0)
            a = min(max(float(splitter.get('absorption', 0.0)), 0.0), 1.0 - r)
            wl = [0.45, 0.55, 0.65]
            th = [0.0, 45.0, 70.0]
            s.BeamSplitter = splitter
            mode = str(splitter.get('split_mode', '')).lower()
            existing_coating = spec.get('advanced', {}).get('Coating')
            if 'coating table' in mode and existing_coating not in (None, [[], [], [], []]):
                s.Coating = existing_coating
            else:
                s.Coating = [[[r for _w in wl] for _t in th], [[a for _w in wl] for _t in th], wl, th]
            if str(s.Glass).upper() == 'MIRROR':
                s.Glass = 'AIR'
        if spec['surface'] == 'Thin Lens':
            s.Thin_Lens = spec['rc'] if spec['rc'] != 0 else 100.0
            s.Rc = 0.0
        elif spec['surface'] == 'Grating':
            if abs(float(s.Diff_Ord)) < 1e-12:
                s.Diff_Ord = 1.0
            if abs(float(s.Grating_D)) < 1e-12:
                s.Grating_D = 1.0
        runtime_surfaces.append(s)
    setup = Kos.Setup()
    for metal in SETTINGS.get('metal_catalogs', []):
        try:
            path = Path(str(metal.get('path', ''))).expanduser()
            name = str(metal.get('name') or path.stem).strip() or path.stem
            catalog_type = int(metal.get('type', 1))
            if path.exists() and name.lower() not in {str(item).lower() for item in getattr(setup, 'Name_met', [])}:
                setup.LoadMetal(str(path), name, catalog_type)
        except Exception as exc:
            print(f'Could not load metal catalog {metal!r}: {exc}')
    system = Kos.system(runtime_surfaces, setup)
    apply_optical_solid_output_port_system_overrides(system, surface_dicts)
    return system


def build_rays(system):
    return build_saved_layout_rays(system, SURFACES, SETTINGS, Kos)


if __name__ == '__main__':
    system = build_runtime_system()
    rays = build_rays(system)
    display_saved_layout_2d(SURFACES, SETTINGS, system=system, rays=rays, layout_path=Path(__file__))

