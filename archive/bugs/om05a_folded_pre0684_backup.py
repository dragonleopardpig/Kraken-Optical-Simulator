#!/usr/bin/env python3
TITLE = "Om05A Symb Work"

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
 'scene_sources': [{'source_id': 'source:faceB',
                    'name': 'Device face B',
                    'model': 'Random rectangle source',
                    'role': 'illumination',
                    'physical': True,
                    'enabled': True,
                    'additive': True,
                    'source_x': 0.0,
                    'source_y': 0.0,
                    'source_z': -57.8,
                    'source_l': 0.0,
                    'source_m': 0.0,
                    'source_n': -1.0,
                    'radius_x': 25.0,
                    'radius_y': 0.5,
                    'radius': 25.0,
                    'mirror_launch_plane_z': -28.9,
                    'cone_deg': 5.5,
                    'ray_count': 400,
                    'power': 1.0,
                    'wavelength': 0.55,
                    'seed': 7}],
 'scene_row_order': 'after_object',
 'inspection_part': {'enabled': True,
                     'width_mm': 50.0,
                     'height_mm': 1.0,
                     'depth_mm': 50.0,
                     'active_face': 'front',
                     'axis_reach_mm': 0.0,
                     'axis_offset_mm': -3.9,
                     'step_path': ''},
 'display_fold_spec': None,
 'object_fov_bands': [{'name': 'Arm A field',
                       'center': [0.0, 0.0, 0.0],
                       'axis': [0.0, 0.0, 1.0],
                       'half_width': 26.8,
                       'v_lo': -5.0,
                       'v_hi': 1.0},
                      {'name': 'Arm B field',
                       'center': [0.0, 0.0, -57.8],
                       'axis': [0.0, 0.0, 1.0],
                       'half_width': 26.8,
                       'v_lo': -5.0,
                       'v_hi': 1.0}],
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
 'show_clipped_rays': True,
 'show_path_labels': True,
 'show_cardinals': True,
 'show_physical_distances': False,
 'field_type': 'Real Image Height',
 'field_value': '0.25',
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
 'camera_model': 'CAM-SV25MCCXP',
 'camera_precouple_stash': None,
 'branch_detector_camera_assignments': {},
 'step_clear_aperture_by_label': {},
 'clear_aperture_edge_rects_by_label': {},
 'optical_led_glued': False,
 'step_glue_reference_offset_xyz': {'camera': [0.0, 0.0, 0.0],
                                    'lens': [0.0, 0.0, 0.0],
                                    'optical': [0.0, 0.0, 0.0],
                                    'led': [0.0, 0.0, 0.0]},
 'step_glue_reference_datum_mid_xyz': {'lens': [0.0, 0.0, 167.34000000000003],
                                       'led': [0.0, 0.0, 0.0]},
 'camera_step_path': 'attachment/om05a_components/camera_sv25mccxp.step',
 'camera_step_rotation_x_deg': 0.0,
 'camera_step_rotation_y_deg': 0.0,
 'camera_step_rotation_z_deg': 0.0,
 'camera_step_axis_offset_xy': [0.0, 0.0],
 'camera_step_placement_offset_xyz': [0.0, 0.0, 0.0],
 'camera_step_reverse_direction': False,
 'lens_step_path': 'attachment/Lens/PYRITE_45_85_05x-20x_V38_1072517/1072517_00165969_001.stp',
 'lens_step_largest_component_only': False,
 'lens_step_reverse_direction': True,
 'lens_step_rotation_x_deg': 0.0,
 'lens_step_rotation_y_deg': 0.0,
 'lens_step_rotation_z_deg': 0.0,
 'lens_step_axis_offset_xy': [0.0, 0.0],
 'lens_step_placement_offset_xyz': [0.0, 0.0, 0.0],
 'optical_step_path': 'attachment/om05a_components/prism_assembly_chunk_armA.step',
 'optical_step_rotation_x_deg': 0.0,
 'optical_step_rotation_y_deg': 0.0,
 'optical_step_rotation_z_deg': 0.0,
 'optical_step_axis_offset_xy': [-0.05, -27.7665],
 'optical_step_placement_offset_xyz': [0.0, 0.0, -106.79],
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
 'operands': {'Entrance pupil z': {'weight': '1',
                                   'target': '0',
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
              'EFFL': {'weight': '1',
                       'target': '100',
                       'wavelength': '0.55',
                       'field': '0',
                       'surface': 'Auto'},
              'Thickness penalty': {'weight': '1',
                                    'target': '0.1',
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
                             'mtf_algorithm': 'Diffraction FFT'},
              'Wavefront RMS': {'weight': '1',
                                'target': '0',
                                'wavelength': '0.55',
                                'field': '0',
                                'surface': 'Auto'},
              'Exit pupil z': {'weight': '1',
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
    s0.Name = 'Object'
    s0.Rc = 0.0
    s0.k = 0.0
    s0.Axicon = 0.0
    s0.Diff_Ord = 0.0
    s0.Grating_D = 0.0
    s0.Grating_Angle = 0.0
    s0.Thickness = 5.35
    s0.Diameter = 51.0
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
    surfaces.append({'surface': 'Object', 'element': '', 'name': 'Object', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 5.35, 'diameter': 51.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s1 = Kos.surf()
    s1.Name = 'Outer prism A'
    s1.Rc = 0.0
    s1.k = 0.0
    s1.Axicon = 0.0
    s1.Diff_Ord = 0.0
    s1.Grating_D = 0.0
    s1.Grating_Angle = 0.0
    s1.Thickness = 10.5
    s1.Diameter = 77.0
    s1.InDiameter = 0.0
    s1.Drawing = 1.0
    s1.TiltX = 90.0
    s1.TiltY = 0.0
    s1.TiltZ = 180.0
    s1.DespX = 0.0
    s1.DespY = 0.0
    s1.DespZ = 0.0
    s1.AxisMove = 0.0
    s1.Glass = 'BK7'
    s1.Note = ('Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene '
 'mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter '
 'to align the closed mesh in millimetres. Original STEP CAD source: '
 '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/wedge_105.step.')
    s1.OpticalSolidFaces = {'faces': [{'analytic_parameters': {'axis': [0.0, 0.0, 1.0], 'origin': [-35.0, -5.25, 5.25]},
            'area_mm2': 734.9999999999999,
            'assignment_source': 'default_uncoated',
            'centroid': [-2.7068294695622867e-15, -3.816391647148976e-17, 5.25],
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
            'normal': [0.0, -0.0, 1.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 5.25,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, 0.7071067811865476, -0.7071067811865476],
                                    'origin': [-35.0, 5.25, 5.25]},
            'area_mm2': 1039.4469683442248,
            'assignment_source': 'manual',
            'centroid': [-2.3925218418038477e-15, -6.626643678231404e-16, -6.626643678231404e-16],
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
            'normal': [0.0, 0.7071067811865476, -0.7071067811865476],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 0.0,
            'port_role': 'Interaction Surface',
            'recovered_coating': False,
            'role': 'Mirror',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, -1.0, 0.0], 'origin': [-35.0, -5.25, -5.25]},
            'area_mm2': 734.9999999999999,
            'assignment_source': 'default_uncoated',
            'centroid': [-2.7068294695622867e-15, -5.25, -3.816391647148976e-17],
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
            'normal': [0.0, -1.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 5.25,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [-35.0, -1.537689398771, 1.537689398771]},
            'area_mm2': 55.125,
            'assignment_source': 'default_uncoated',
            'centroid': [-35.0, -1.7500000000000007, 1.7499999999999996],
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
            'normal': [-1.0, -0.0, -0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 35.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [35.0, -1.537689398771, 1.537689398771]},
            'area_mm2': 55.125,
            'assignment_source': 'default_uncoated',
            'centroid': [35.0, -1.7500000000000007, 1.7499999999999996],
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
            'normal': [1.0, 0.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 35.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_105_1788223195_12564.stl',
 'version': 1,
 'virtual_planes': []}
    s1.OpticalSolidSourceFormat = 'STEP'
    s1.OpticalSolidSourcePath = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/wedge_105.step'
    s1.Solid_3d_stl = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_105_1788223195_12564.stl'
    s1.StepOverlayPromotion = {'center_world': [0.0, 0.0, 5.35]}
    surfaces.append({'surface': 'Standard', 'element': 'Solid wedge 105', 'name': 'Outer prism A', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 10.5, 'diameter': 77.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {'Note': 'Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter to align the closed mesh in millimetres. Original STEP CAD source: /home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/wedge_105.step.', 'OpticalSolidFaces': {'version': 1, 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_105_1788223195_12564.stl', 'faces': [{'face_id': 'S001/F001', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -0.0, 1.0], 'centroid': [-2.7068294695622867e-15, -3.816391647148976e-17, 5.25], 'area_mm2': 734.9999999999999, 'triangle_count': 2, 'triangle_indices': [0, 1], 'plane_offset_mm': 5.25, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F001', 'source_face_id': 'S001/F001', 'source_solid_index': 1, 'source_face_index': 1, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -5.25, 5.25], 'axis': [0.0, 0.0, 1.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F002', 'role': 'Mirror', 'function': 'Mirror', 'side_2d': 'Auto', 'port_role': 'Interaction Surface', 'fit_reference': 'Auto', 'normal': [0.0, 0.7071067811865476, -0.7071067811865476], 'centroid': [-2.3925218418038477e-15, -6.626643678231404e-16, -6.626643678231404e-16], 'area_mm2': 1039.4469683442248, 'triangle_count': 2, 'triangle_indices': [2, 3], 'plane_offset_mm': 0.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'manual', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F002', 'source_face_id': 'S001/F002', 'source_solid_index': 1, 'source_face_index': 2, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, 5.25, 5.25], 'axis': [0.0, 0.7071067811865476, -0.7071067811865476]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F003', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -1.0, 0.0], 'centroid': [-2.7068294695622867e-15, -5.25, -3.816391647148976e-17], 'area_mm2': 734.9999999999999, 'triangle_count': 2, 'triangle_indices': [4, 5], 'plane_offset_mm': 5.25, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F003', 'source_face_id': 'S001/F003', 'source_solid_index': 1, 'source_face_index': 3, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -5.25, -5.25], 'axis': [0.0, -1.0, 0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F004', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [-1.0, -0.0, -0.0], 'centroid': [-35.0, -1.7500000000000007, 1.7499999999999996], 'area_mm2': 55.125, 'triangle_count': 1, 'triangle_indices': [6], 'plane_offset_mm': 35.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F004', 'source_face_id': 'S001/F004', 'source_solid_index': 1, 'source_face_index': 4, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -1.537689398771, 1.537689398771], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F005', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [1.0, 0.0, 0.0], 'centroid': [35.0, -1.7500000000000007, 1.7499999999999996], 'area_mm2': 55.125, 'triangle_count': 1, 'triangle_indices': [7], 'plane_offset_mm': 35.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F005', 'source_face_id': 'S001/F005', 'source_solid_index': 1, 'source_face_index': 5, 'surface_type': 'plane', 'analytic_parameters': {'origin': [35.0, -1.537689398771, 1.537689398771], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}], 'virtual_planes': []}, 'OpticalSolidSourceFormat': 'STEP', 'OpticalSolidSourcePath': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/wedge_105.step', 'Solid_3d_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_105_1788223195_12564.stl', 'StepOverlayPromotion': {'center_world': [0.0, 0.0, 5.35]}}, 'tilt_x': 90.0, 'tilt_y': 0.0, 'tilt_z': 180.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s2 = Kos.surf()
    s2.Name = 'air'
    s2.Rc = 0.0
    s2.k = 0.0
    s2.Axicon = 0.0
    s2.Diff_Ord = 0.0
    s2.Grating_D = 0.0
    s2.Grating_Angle = 0.0
    s2.Thickness = 1.0
    s2.Diameter = 80.0
    s2.InDiameter = 0.0
    s2.Drawing = 0.0
    s2.TiltX = 0.0
    s2.TiltY = 0.0
    s2.TiltZ = 0.0
    s2.DespX = 0.0
    s2.DespY = 0.0
    s2.DespZ = 0.0
    s2.AxisMove = 0.0
    s2.Glass = 'AIR'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'air', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 1.0, 'diameter': 80.0, 'in_diameter': 0.0, 'drawing': 0.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s3 = Kos.surf()
    s3.Name = 'Lower prism A'
    s3.Rc = 0.0
    s3.k = 0.0
    s3.Axicon = 0.0
    s3.Diff_Ord = 0.0
    s3.Grating_D = 0.0
    s3.Grating_Angle = 0.0
    s3.Thickness = 15.0
    s3.Diameter = 77.0
    s3.InDiameter = 0.0
    s3.Drawing = 1.0
    s3.TiltX = 90.0
    s3.TiltY = 0.0
    s3.TiltZ = 0.0
    s3.DespX = 0.0
    s3.DespY = 11.65
    s3.DespZ = -14.25
    s3.AxisMove = 0.0
    s3.Glass = 'BK7'
    s3.Note = ('Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene '
 'mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter '
 'to align the closed mesh in millimetres. Original STEP CAD source: '
 '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/wedge_150.step.')
    s3.OpticalSolidFaces = {'faces': [{'analytic_parameters': {'axis': [0.0, 0.0, 1.0], 'origin': [-35.0, -7.5, 7.5]},
            'area_mm2': 1050.0,
            'assignment_source': 'default_uncoated',
            'centroid': [-9.473903143468002e-16, -1.6306400674181987e-16, 7.5],
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
            'normal': [0.0, -0.0, 1.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 7.5,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, 0.7071067811865476, -0.7071067811865476],
                                    'origin': [-35.0, 7.5, 7.5]},
            'area_mm2': 1484.92424049175,
            'assignment_source': 'manual',
            'centroid': [-1.5072887603364238e-15, -3.1918911957973236e-16, -3.1918911957973236e-16],
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
            'normal': [0.0, 0.7071067811865476, -0.7071067811865476],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 0.0,
            'port_role': 'Interaction Surface',
            'recovered_coating': False,
            'role': 'Mirror',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, -1.0, 0.0], 'origin': [-35.0, -7.5, -7.5]},
            'area_mm2': 1050.0,
            'assignment_source': 'default_uncoated',
            'centroid': [-9.473903143468002e-16, -7.5, -1.6306400674181987e-16],
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
            'normal': [0.0, -1.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 7.5,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [-35.0, -2.196699141101, 2.196699141101]},
            'area_mm2': 112.50000000000001,
            'assignment_source': 'default_uncoated',
            'centroid': [-35.0, -2.5, 2.5],
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
            'normal': [-1.0, -0.0, -0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 35.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [35.0, -2.196699141101, 2.196699141101]},
            'area_mm2': 112.50000000000001,
            'assignment_source': 'default_uncoated',
            'centroid': [35.0, -2.5, 2.5],
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
            'normal': [1.0, 0.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 35.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_150_1788223195_12526.stl',
 'version': 1,
 'virtual_planes': []}
    s3.OpticalSolidSourceFormat = 'STEP'
    s3.OpticalSolidSourcePath = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/wedge_150.step'
    s3.Solid_3d_stl = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_150_1788223195_12526.stl'
    s3.StepOverlayPromotion = {'center_world': [0.0, 11.65, 2.6]}
    surfaces.append({'surface': 'Standard', 'element': 'Solid wedge 150', 'name': 'Lower prism A', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 15.0, 'diameter': 77.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {'Note': 'Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter to align the closed mesh in millimetres. Original STEP CAD source: /home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/wedge_150.step.', 'OpticalSolidFaces': {'version': 1, 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_150_1788223195_12526.stl', 'faces': [{'face_id': 'S001/F001', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -0.0, 1.0], 'centroid': [-9.473903143468002e-16, -1.6306400674181987e-16, 7.5], 'area_mm2': 1050.0, 'triangle_count': 2, 'triangle_indices': [0, 1], 'plane_offset_mm': 7.5, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F001', 'source_face_id': 'S001/F001', 'source_solid_index': 1, 'source_face_index': 1, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -7.5, 7.5], 'axis': [0.0, 0.0, 1.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F002', 'role': 'Mirror', 'function': 'Mirror', 'side_2d': 'Auto', 'port_role': 'Interaction Surface', 'fit_reference': 'Auto', 'normal': [0.0, 0.7071067811865476, -0.7071067811865476], 'centroid': [-1.5072887603364238e-15, -3.1918911957973236e-16, -3.1918911957973236e-16], 'area_mm2': 1484.92424049175, 'triangle_count': 2, 'triangle_indices': [2, 3], 'plane_offset_mm': 0.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'manual', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F002', 'source_face_id': 'S001/F002', 'source_solid_index': 1, 'source_face_index': 2, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, 7.5, 7.5], 'axis': [0.0, 0.7071067811865476, -0.7071067811865476]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F003', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -1.0, 0.0], 'centroid': [-9.473903143468002e-16, -7.5, -1.6306400674181987e-16], 'area_mm2': 1050.0, 'triangle_count': 2, 'triangle_indices': [4, 5], 'plane_offset_mm': 7.5, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F003', 'source_face_id': 'S001/F003', 'source_solid_index': 1, 'source_face_index': 3, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -7.5, -7.5], 'axis': [0.0, -1.0, 0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F004', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [-1.0, -0.0, -0.0], 'centroid': [-35.0, -2.5, 2.5], 'area_mm2': 112.50000000000001, 'triangle_count': 1, 'triangle_indices': [6], 'plane_offset_mm': 35.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F004', 'source_face_id': 'S001/F004', 'source_solid_index': 1, 'source_face_index': 4, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -2.196699141101, 2.196699141101], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F005', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [1.0, 0.0, 0.0], 'centroid': [35.0, -2.5, 2.5], 'area_mm2': 112.50000000000001, 'triangle_count': 1, 'triangle_indices': [7], 'plane_offset_mm': 35.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F005', 'source_face_id': 'S001/F005', 'source_solid_index': 1, 'source_face_index': 5, 'surface_type': 'plane', 'analytic_parameters': {'origin': [35.0, -2.196699141101, 2.196699141101], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}], 'virtual_planes': []}, 'OpticalSolidSourceFormat': 'STEP', 'OpticalSolidSourcePath': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/wedge_150.step', 'Solid_3d_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_150_1788223195_12526.stl', 'StepOverlayPromotion': {'center_world': [0.0, 11.65, 2.6]}}, 'tilt_x': 90.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 11.65, 'desp_z': -14.25, 'axis_move': 0.0, 'glass': 'BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s4 = Kos.surf()
    s4.Name = 'air'
    s4.Rc = 0.0
    s4.k = 0.0
    s4.Axicon = 0.0
    s4.Diff_Ord = 0.0
    s4.Grating_D = 0.0
    s4.Grating_Angle = 0.0
    s4.Thickness = 12.0
    s4.Diameter = 80.0
    s4.InDiameter = 0.0
    s4.Drawing = 0.0
    s4.TiltX = 0.0
    s4.TiltY = 0.0
    s4.TiltZ = 0.0
    s4.DespX = 0.0
    s4.DespY = 0.0
    s4.DespZ = 0.0
    s4.AxisMove = 0.0
    s4.Glass = 'AIR'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'air', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 12.0, 'diameter': 80.0, 'in_diameter': 0.0, 'drawing': 0.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s5 = Kos.surf()
    s5.Name = 'Centre prism A'
    s5.Rc = 0.0
    s5.k = 0.0
    s5.Axicon = 0.0
    s5.Diff_Ord = 0.0
    s5.Grating_D = 0.0
    s5.Grating_Angle = 0.0
    s5.Thickness = 18.0
    s5.Diameter = 77.0
    s5.InDiameter = 0.0
    s5.Drawing = 1.0
    s5.TiltX = 0.0
    s5.TiltY = 0.0
    s5.TiltZ = 180.0
    s5.DespX = 0.0
    s5.DespY = 13.73
    s5.DespZ = -68.25
    s5.AxisMove = 0.0
    s5.Glass = 'BK7'
    s5.Note = ('Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene '
 'mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter '
 'to align the closed mesh in millimetres. Original STEP CAD source: '
 '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/wedge_120.step.')
    s5.OpticalSolidFaces = {'faces': [{'analytic_parameters': {'axis': [0.0, 0.0, 1.0], 'origin': [-35.0, -6.0, 6.0]},
            'area_mm2': 840.0,
            'assignment_source': 'default_uncoated',
            'centroid': [-2.0724163126336257e-15, 1.5612511283791266e-16, 6.0],
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
            'normal': [0.0, -0.0, 1.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 6.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, 0.7071067811865476, -0.7071067811865476],
                                    'origin': [-35.0, 6.0, 6.0]},
            'area_mm2': 1187.9393923933999,
            'assignment_source': 'manual',
            'centroid': [-8.373826446313467e-16, -1.1136924715771105e-15, -1.1136924715771105e-15],
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
            'normal': [0.0, 0.7071067811865476, -0.7071067811865476],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 0.0,
            'port_role': 'Interaction Surface',
            'recovered_coating': False,
            'role': 'Mirror',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, -1.0, 0.0], 'origin': [-35.0, -6.0, -6.0]},
            'area_mm2': 840.0,
            'assignment_source': 'default_uncoated',
            'centroid': [-2.0724163126336257e-15, -6.0, 1.5612511283791266e-16],
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
            'normal': [0.0, -1.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 6.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [-35.0, -1.757359312881, 1.757359312881]},
            'area_mm2': 72.00000000000001,
            'assignment_source': 'default_uncoated',
            'centroid': [-35.0, -2.0000000000000013, 1.999999999999999],
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
            'normal': [-1.0, -0.0, -0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 35.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [35.0, -1.757359312881, 1.757359312881]},
            'area_mm2': 72.00000000000001,
            'assignment_source': 'default_uncoated',
            'centroid': [35.0, -2.0000000000000013, 1.999999999999999],
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
            'normal': [1.0, 0.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 35.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_120_1788223195_12490.stl',
 'version': 1,
 'virtual_planes': []}
    s5.OpticalSolidSourceFormat = 'STEP'
    s5.OpticalSolidSourcePath = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/wedge_120.step'
    s5.Solid_3d_stl = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_120_1788223195_12490.stl'
    s5.StepOverlayPromotion = {'center_world': [0.0, 13.73, -24.4]}
    surfaces.append({'surface': 'Standard', 'element': 'Solid wedge 120', 'name': 'Centre prism A', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 18.0, 'diameter': 77.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {'Note': 'Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter to align the closed mesh in millimetres. Original STEP CAD source: /home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/wedge_120.step.', 'OpticalSolidFaces': {'version': 1, 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_120_1788223195_12490.stl', 'faces': [{'face_id': 'S001/F001', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -0.0, 1.0], 'centroid': [-2.0724163126336257e-15, 1.5612511283791266e-16, 6.0], 'area_mm2': 840.0, 'triangle_count': 2, 'triangle_indices': [0, 1], 'plane_offset_mm': 6.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F001', 'source_face_id': 'S001/F001', 'source_solid_index': 1, 'source_face_index': 1, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -6.0, 6.0], 'axis': [0.0, 0.0, 1.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F002', 'role': 'Mirror', 'function': 'Mirror', 'side_2d': 'Auto', 'port_role': 'Interaction Surface', 'fit_reference': 'Auto', 'normal': [0.0, 0.7071067811865476, -0.7071067811865476], 'centroid': [-8.373826446313467e-16, -1.1136924715771105e-15, -1.1136924715771105e-15], 'area_mm2': 1187.9393923933999, 'triangle_count': 2, 'triangle_indices': [2, 3], 'plane_offset_mm': 0.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'manual', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F002', 'source_face_id': 'S001/F002', 'source_solid_index': 1, 'source_face_index': 2, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, 6.0, 6.0], 'axis': [0.0, 0.7071067811865476, -0.7071067811865476]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F003', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -1.0, 0.0], 'centroid': [-2.0724163126336257e-15, -6.0, 1.5612511283791266e-16], 'area_mm2': 840.0, 'triangle_count': 2, 'triangle_indices': [4, 5], 'plane_offset_mm': 6.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F003', 'source_face_id': 'S001/F003', 'source_solid_index': 1, 'source_face_index': 3, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -6.0, -6.0], 'axis': [0.0, -1.0, 0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F004', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [-1.0, -0.0, -0.0], 'centroid': [-35.0, -2.0000000000000013, 1.999999999999999], 'area_mm2': 72.00000000000001, 'triangle_count': 1, 'triangle_indices': [6], 'plane_offset_mm': 35.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F004', 'source_face_id': 'S001/F004', 'source_solid_index': 1, 'source_face_index': 4, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -1.757359312881, 1.757359312881], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F005', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [1.0, 0.0, 0.0], 'centroid': [35.0, -2.0000000000000013, 1.999999999999999], 'area_mm2': 72.00000000000001, 'triangle_count': 1, 'triangle_indices': [7], 'plane_offset_mm': 35.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F005', 'source_face_id': 'S001/F005', 'source_solid_index': 1, 'source_face_index': 5, 'surface_type': 'plane', 'analytic_parameters': {'origin': [35.0, -1.757359312881, 1.757359312881], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}], 'virtual_planes': []}, 'OpticalSolidSourceFormat': 'STEP', 'OpticalSolidSourcePath': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/wedge_120.step', 'Solid_3d_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_120_1788223195_12490.stl', 'StepOverlayPromotion': {'center_world': [0.0, 13.73, -24.4]}}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 180.0, 'desp_x': 0.0, 'desp_y': 13.73, 'desp_z': -68.25, 'axis_move': 0.0, 'glass': 'BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s6 = Kos.surf()
    s6.Name = 'to lens (unfolded RA mirror 1)'
    s6.Rc = 0.0
    s6.k = 0.0
    s6.Axicon = 0.0
    s6.Diff_Ord = 0.0
    s6.Grating_D = 0.0
    s6.Grating_Angle = 0.0
    s6.Thickness = 33.08
    s6.Diameter = 80.0
    s6.InDiameter = 0.0
    s6.Drawing = 0.0
    s6.TiltX = 0.0
    s6.TiltY = 0.0
    s6.TiltZ = 0.0
    s6.DespX = 0.0
    s6.DespY = 0.0
    s6.DespZ = 0.0
    s6.AxisMove = 0.0
    s6.Glass = 'AIR'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'to lens (unfolded RA mirror 1)', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 33.08, 'diameter': 80.0, 'in_diameter': 0.0, 'drawing': 0.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s7 = Kos.surf()
    s7.Name = 'RA mirror 1 (50 mm)'
    s7.Rc = 0.0
    s7.k = 0.0
    s7.Axicon = 0.0
    s7.Diff_Ord = 0.0
    s7.Grating_D = 0.0
    s7.Grating_Angle = 0.0
    s7.Thickness = 180.47
    s7.Diameter = 77.0
    s7.InDiameter = 0.0
    s7.Drawing = 1.0
    s7.TiltX = 0.0
    s7.TiltY = 90.0
    s7.TiltZ = -90.0
    s7.DespX = 0.0
    s7.DespY = 52.8
    s7.DespZ = -123.83
    s7.AxisMove = 0.0
    s7.Glass = 'BK7'
    s7.Note = ('Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene '
 'mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter '
 'to align the closed mesh in millimetres. Original STEP CAD source: '
 '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/mirror1_cleanb.step.')
    s7.OpticalSolidFaces = {'faces': [{'analytic_parameters': {'axis': [0.0, 0.0, 1.0], 'origin': [-25.0, -25.0, 25.0]},
            'area_mm2': 2500.0,
            'assignment_source': 'default_uncoated',
            'centroid': [0.0, -4.440892098500626e-16, 25.0],
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
            'normal': [0.0, -0.0, 1.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 25.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, 0.7071067811865476, -0.7071067811865476],
                                    'origin': [-25.0, 25.0, 25.0]},
            'area_mm2': 3535.533905932738,
            'assignment_source': 'manual',
            'centroid': [4.0194366942304637e-16, -1.8735013540549513e-15, -1.8735013540549513e-15],
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
            'normal': [0.0, 0.7071067811865476, -0.7071067811865476],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 0.0,
            'port_role': 'Interaction Surface',
            'recovered_coating': False,
            'role': 'Mirror',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, -1.0, 0.0], 'origin': [-25.0, -25.0, -25.0]},
            'area_mm2': 2500.0,
            'assignment_source': 'default_uncoated',
            'centroid': [0.0, -25.0, -4.440892098500626e-16],
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
            'normal': [0.0, -1.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 25.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [-25.0, -7.322330470336, 7.322330470336]},
            'area_mm2': 1250.0,
            'assignment_source': 'default_uncoated',
            'centroid': [-25.0, -8.333333333333337, 8.333333333333334],
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
            'normal': [-1.0, -0.0, -0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 25.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [25.0, -7.322330470336, 7.322330470336]},
            'area_mm2': 1250.0,
            'assignment_source': 'default_uncoated',
            'centroid': [25.0, -8.333333333333337, 8.333333333333334],
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
            'normal': [1.0, 0.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 25.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/mirror1_cleanb_1788221200_12532.stl',
 'version': 1,
 'virtual_planes': []}
    s7.OpticalSolidSourceFormat = 'STEP'
    s7.OpticalSolidSourcePath = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/mirror1_cleanb.step'
    s7.Solid_3d_stl = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/mirror1_cleanb_1788221200_12532.stl'
    s7.StepOverlayPromotion = {'center_world': [0.0, 52.8, -28.9]}
    surfaces.append({'surface': 'Standard', 'element': 'Solid mirror1 cleanb', 'name': 'RA mirror 1 (50 mm)', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 180.47, 'diameter': 77.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {'Note': 'Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter to align the closed mesh in millimetres. Original STEP CAD source: /home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/mirror1_cleanb.step.', 'OpticalSolidFaces': {'version': 1, 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/mirror1_cleanb_1788221200_12532.stl', 'faces': [{'face_id': 'S001/F001', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -0.0, 1.0], 'centroid': [0.0, -4.440892098500626e-16, 25.0], 'area_mm2': 2500.0, 'triangle_count': 2, 'triangle_indices': [0, 1], 'plane_offset_mm': 25.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F001', 'source_face_id': 'S001/F001', 'source_solid_index': 1, 'source_face_index': 1, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-25.0, -25.0, 25.0], 'axis': [0.0, 0.0, 1.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F002', 'role': 'Mirror', 'function': 'Mirror', 'side_2d': 'Auto', 'port_role': 'Interaction Surface', 'fit_reference': 'Auto', 'normal': [0.0, 0.7071067811865476, -0.7071067811865476], 'centroid': [4.0194366942304637e-16, -1.8735013540549513e-15, -1.8735013540549513e-15], 'area_mm2': 3535.533905932738, 'triangle_count': 2, 'triangle_indices': [2, 3], 'plane_offset_mm': 0.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'manual', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F002', 'source_face_id': 'S001/F002', 'source_solid_index': 1, 'source_face_index': 2, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-25.0, 25.0, 25.0], 'axis': [0.0, 0.7071067811865476, -0.7071067811865476]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F003', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -1.0, 0.0], 'centroid': [0.0, -25.0, -4.440892098500626e-16], 'area_mm2': 2500.0, 'triangle_count': 2, 'triangle_indices': [4, 5], 'plane_offset_mm': 25.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F003', 'source_face_id': 'S001/F003', 'source_solid_index': 1, 'source_face_index': 3, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-25.0, -25.0, -25.0], 'axis': [0.0, -1.0, 0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F004', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [-1.0, -0.0, -0.0], 'centroid': [-25.0, -8.333333333333337, 8.333333333333334], 'area_mm2': 1250.0, 'triangle_count': 1, 'triangle_indices': [6], 'plane_offset_mm': 25.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F004', 'source_face_id': 'S001/F004', 'source_solid_index': 1, 'source_face_index': 4, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-25.0, -7.322330470336, 7.322330470336], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F005', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [1.0, 0.0, 0.0], 'centroid': [25.0, -8.333333333333337, 8.333333333333334], 'area_mm2': 1250.0, 'triangle_count': 1, 'triangle_indices': [7], 'plane_offset_mm': 25.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F005', 'source_face_id': 'S001/F005', 'source_solid_index': 1, 'source_face_index': 5, 'surface_type': 'plane', 'analytic_parameters': {'origin': [25.0, -7.322330470336, 7.322330470336], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}], 'virtual_planes': []}, 'OpticalSolidSourceFormat': 'STEP', 'OpticalSolidSourcePath': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/mirror1_cleanb.step', 'Solid_3d_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/mirror1_cleanb_1788221200_12532.stl', 'StepOverlayPromotion': {'center_world': [0.0, 52.8, -28.9]}}, 'tilt_x': 0.0, 'tilt_y': 90.0, 'tilt_z': -90.0, 'desp_x': 0.0, 'desp_y': 52.8, 'desp_z': -123.83, 'axis_move': 0.0, 'glass': 'BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s8 = Kos.surf()
    s8.Name = 'Front Optical Vertex Datum'
    s8.Rc = 0.0
    s8.k = 0.0
    s8.Axicon = 0.0
    s8.Diff_Ord = 0.0
    s8.Grating_D = 0.0
    s8.Grating_Angle = 0.0
    s8.Thickness = 1.823004
    s8.Diameter = 36.0
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
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'Front Optical Vertex Datum', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 1.823004, 'diameter': 36.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s9 = Kos.surf()
    s9.Name = 'Blackbox Group 1'
    s9.Rc = 149.403004
    s9.k = 0.0
    s9.Axicon = 0.0
    s9.Diff_Ord = 0.0
    s9.Grating_D = 0.0
    s9.Grating_Angle = 0.0
    s9.Thickness = 18.301996
    s9.Diameter = 36.0
    s9.InDiameter = 0.0
    s9.Drawing = 1.0
    s9.TiltX = 0.0
    s9.TiltY = 0.0
    s9.TiltZ = 0.0
    s9.DespX = 0.0
    s9.DespY = 0.0
    s9.DespZ = 0.0
    s9.AxisMove = 0.0
    s9.Glass = 'AIR'
    s9.Thin_Lens = 149.403004
    s9.Rc = 0.0
    surfaces.append({'surface': 'Thin Lens', 'element': 'Blackbox Group 1', 'name': 'Blackbox Group 1', 'rc': 149.403004, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 18.301996, 'diameter': 36.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s10 = Kos.surf()
    s10.Name = 'Aperture Stop'
    s10.Rc = 0.0
    s10.k = 0.0
    s10.Axicon = 0.0
    s10.Diff_Ord = 0.0
    s10.Grating_D = 0.0
    s10.Grating_Angle = 0.0
    s10.Thickness = 18.301996
    s10.Diameter = 18.9178
    s10.InDiameter = 0.0
    s10.Drawing = 1.0
    s10.TiltX = 0.0
    s10.TiltY = 0.0
    s10.TiltZ = 0.0
    s10.DespX = 0.0
    s10.DespY = 0.0
    s10.DespZ = 0.0
    s10.AxisMove = 0.0
    s10.Glass = 'AIR'
    surfaces.append({'surface': 'Aperture', 'element': 'Aperture Stop', 'name': 'Aperture Stop', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 18.301996, 'diameter': 18.9178, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s11 = Kos.surf()
    s11.Name = 'Blackbox Group 2'
    s11.Rc = 149.403004
    s11.k = 0.0
    s11.Axicon = 0.0
    s11.Diff_Ord = 0.0
    s11.Grating_D = 0.0
    s11.Grating_Angle = 0.0
    s11.Thickness = 1.093004
    s11.Diameter = 36.0
    s11.InDiameter = 0.0
    s11.Drawing = 1.0
    s11.TiltX = 0.0
    s11.TiltY = 0.0
    s11.TiltZ = 0.0
    s11.DespX = 0.0
    s11.DespY = 0.0
    s11.DespZ = 0.0
    s11.AxisMove = 0.0
    s11.Glass = 'AIR'
    s11.Thin_Lens = 149.403004
    s11.Rc = 0.0
    surfaces.append({'surface': 'Thin Lens', 'element': 'Blackbox Group 2', 'name': 'Blackbox Group 2', 'rc': 149.403004, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 1.093004, 'diameter': 36.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s12 = Kos.surf()
    s12.Name = 'Rear Optical Vertex Datum'
    s12.Rc = 0.0
    s12.k = 0.0
    s12.Axicon = 0.0
    s12.Diff_Ord = 0.0
    s12.Grating_D = 0.0
    s12.Grating_Angle = 0.0
    s12.Thickness = 21.6
    s12.Diameter = 36.0
    s12.InDiameter = 0.0
    s12.Drawing = 1.0
    s12.TiltX = 0.0
    s12.TiltY = 0.0
    s12.TiltZ = 0.0
    s12.DespX = 0.0
    s12.DespY = 0.0
    s12.DespZ = 0.0
    s12.AxisMove = 0.0
    s12.Glass = 'AIR'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'Rear Optical Vertex Datum', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 21.6, 'diameter': 36.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s13 = Kos.surf()
    s13.Name = 'Filter 48-926'
    s13.Rc = 0.0
    s13.k = 0.0
    s13.Axicon = 0.0
    s13.Diff_Ord = 0.0
    s13.Grating_D = 0.0
    s13.Grating_Angle = 0.0
    s13.Thickness = 1.0
    s13.Diameter = 50.8
    s13.InDiameter = 0.0
    s13.Drawing = 1.0
    s13.TiltX = 0.0
    s13.TiltY = 0.0
    s13.TiltZ = 0.0
    s13.DespX = 0.0
    s13.DespY = 0.0
    s13.DespZ = 0.0
    s13.AxisMove = 0.0
    s13.Glass = 'N-BK7'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'Filter 48-926', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 1.0, 'diameter': 50.8, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'N-BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s14 = Kos.surf()
    s14.Name = 'to camera (unfolded RA mirror 2)'
    s14.Rc = 0.0
    s14.k = 0.0
    s14.Axicon = 0.0
    s14.Diff_Ord = 0.0
    s14.Grating_D = 0.0
    s14.Grating_Angle = 0.0
    s14.Thickness = 31.11
    s14.Diameter = 50.8
    s14.InDiameter = 0.0
    s14.Drawing = 1.0
    s14.TiltX = 0.0
    s14.TiltY = 0.0
    s14.TiltZ = 0.0
    s14.DespX = 0.0
    s14.DespY = 0.0
    s14.DespZ = 0.0
    s14.AxisMove = 0.0
    s14.Glass = 'AIR'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'to camera (unfolded RA mirror 2)', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 31.11, 'diameter': 50.8, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s15 = Kos.surf()
    s15.Name = 'RA mirror 2 (40 mm)'
    s15.Rc = 0.0
    s15.k = 0.0
    s15.Axicon = 0.0
    s15.Diff_Ord = 0.0
    s15.Grating_D = 0.0
    s15.Grating_Angle = 0.0
    s15.Thickness = 45.64
    s15.Diameter = 77.0
    s15.InDiameter = 0.0
    s15.Drawing = 1.0
    s15.TiltX = 0.0
    s15.TiltY = 90.0
    s15.TiltZ = 180.0
    s15.DespX = -272.7
    s15.DespY = 52.75
    s15.DespZ = -397.53
    s15.AxisMove = 0.0
    s15.Glass = 'BK7'
    s15.Note = ('Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene '
 'mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter '
 'to align the closed mesh in millimetres. Original STEP CAD source: '
 '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/mirror2_cleanb.step.')
    s15.OpticalSolidFaces = {'faces': [{'analytic_parameters': {'axis': [0.0, 0.0, 1.0], 'origin': [-20.0, -20.0, 20.0]},
            'area_mm2': 1599.9999999999998,
            'assignment_source': 'default_uncoated',
            'centroid': [8.881784197001254e-17, -2.775557561562892e-17, 20.0],
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
            'normal': [0.0, -0.0, 1.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 20.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, 0.7071067811865476, -0.7071067811865476],
                                    'origin': [-20.0, 20.0, 20.0]},
            'area_mm2': 2262.741699796952,
            'assignment_source': 'manual',
            'centroid': [0.0, -3.1502578323738817e-15, -3.1502578323738817e-15],
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
            'normal': [0.0, 0.7071067811865476, -0.7071067811865476],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 0.0,
            'port_role': 'Interaction Surface',
            'recovered_coating': False,
            'role': 'Mirror',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, -1.0, 0.0], 'origin': [-20.0, -20.0, -20.0]},
            'area_mm2': 1599.9999999999998,
            'assignment_source': 'default_uncoated',
            'centroid': [8.881784197001254e-17, -20.0, -2.775557561562892e-17],
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
            'normal': [0.0, -1.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 20.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [-20.0, -5.857864376269, 5.857864376269]},
            'area_mm2': 800.0000000000002,
            'assignment_source': 'default_uncoated',
            'centroid': [-20.0, -6.666666666666671, 6.666666666666665],
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
            'normal': [-1.0, -0.0, -0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 20.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [20.0, -5.857864376269, 5.857864376269]},
            'area_mm2': 800.0000000000002,
            'assignment_source': 'default_uncoated',
            'centroid': [20.0, -6.666666666666671, 6.666666666666665],
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
            'normal': [1.0, 0.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 20.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/mirror2_cleanb_1788221200_12532.stl',
 'version': 1,
 'virtual_planes': []}
    s15.OpticalSolidSourceFormat = 'STEP'
    s15.OpticalSolidSourcePath = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/mirror2_cleanb.step'
    s15.Solid_3d_stl = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/mirror2_cleanb_1788221200_12532.stl'
    s15.StepOverlayPromotion = {'center_world': [-272.7, 52.75, -28.9]}
    surfaces.append({'surface': 'Standard', 'element': 'Solid mirror2 cleanb', 'name': 'RA mirror 2 (40 mm)', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 45.64, 'diameter': 77.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {'Note': 'Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter to align the closed mesh in millimetres. Original STEP CAD source: /home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/mirror2_cleanb.step.', 'OpticalSolidFaces': {'version': 1, 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/mirror2_cleanb_1788221200_12532.stl', 'faces': [{'face_id': 'S001/F001', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -0.0, 1.0], 'centroid': [8.881784197001254e-17, -2.775557561562892e-17, 20.0], 'area_mm2': 1599.9999999999998, 'triangle_count': 2, 'triangle_indices': [0, 1], 'plane_offset_mm': 20.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F001', 'source_face_id': 'S001/F001', 'source_solid_index': 1, 'source_face_index': 1, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-20.0, -20.0, 20.0], 'axis': [0.0, 0.0, 1.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F002', 'role': 'Mirror', 'function': 'Mirror', 'side_2d': 'Auto', 'port_role': 'Interaction Surface', 'fit_reference': 'Auto', 'normal': [0.0, 0.7071067811865476, -0.7071067811865476], 'centroid': [0.0, -3.1502578323738817e-15, -3.1502578323738817e-15], 'area_mm2': 2262.741699796952, 'triangle_count': 2, 'triangle_indices': [2, 3], 'plane_offset_mm': 0.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'manual', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F002', 'source_face_id': 'S001/F002', 'source_solid_index': 1, 'source_face_index': 2, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-20.0, 20.0, 20.0], 'axis': [0.0, 0.7071067811865476, -0.7071067811865476]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F003', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -1.0, 0.0], 'centroid': [8.881784197001254e-17, -20.0, -2.775557561562892e-17], 'area_mm2': 1599.9999999999998, 'triangle_count': 2, 'triangle_indices': [4, 5], 'plane_offset_mm': 20.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F003', 'source_face_id': 'S001/F003', 'source_solid_index': 1, 'source_face_index': 3, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-20.0, -20.0, -20.0], 'axis': [0.0, -1.0, 0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F004', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [-1.0, -0.0, -0.0], 'centroid': [-20.0, -6.666666666666671, 6.666666666666665], 'area_mm2': 800.0000000000002, 'triangle_count': 1, 'triangle_indices': [6], 'plane_offset_mm': 20.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F004', 'source_face_id': 'S001/F004', 'source_solid_index': 1, 'source_face_index': 4, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-20.0, -5.857864376269, 5.857864376269], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F005', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [1.0, 0.0, 0.0], 'centroid': [20.0, -6.666666666666671, 6.666666666666665], 'area_mm2': 800.0000000000002, 'triangle_count': 1, 'triangle_indices': [7], 'plane_offset_mm': 20.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F005', 'source_face_id': 'S001/F005', 'source_solid_index': 1, 'source_face_index': 5, 'surface_type': 'plane', 'analytic_parameters': {'origin': [20.0, -5.857864376269, 5.857864376269], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}], 'virtual_planes': []}, 'OpticalSolidSourceFormat': 'STEP', 'OpticalSolidSourcePath': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/om05a_components/mirror2_cleanb.step', 'Solid_3d_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/mirror2_cleanb_1788221200_12532.stl', 'StepOverlayPromotion': {'center_world': [-272.7, 52.75, -28.9]}}, 'tilt_x': 0.0, 'tilt_y': 90.0, 'tilt_z': 180.0, 'desp_x': -272.7, 'desp_y': 52.75, 'desp_z': -397.53, 'axis_move': 0.0, 'glass': 'BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s16 = Kos.surf()
    s16.Name = 'Outer prism B'
    s16.Rc = 0.0
    s16.k = 0.0
    s16.Axicon = 0.0
    s16.Diff_Ord = 0.0
    s16.Grating_D = 0.0
    s16.Grating_Angle = 0.0
    s16.Thickness = 0.0
    s16.Diameter = 25.0
    s16.InDiameter = 0.0
    s16.Drawing = 1.0
    s16.TiltX = 0.0
    s16.TiltY = 0.0
    s16.TiltZ = 180.0
    s16.DespX = 0.0
    s16.DespY = 0.0
    s16.DespZ = -477.42
    s16.AxisMove = 0.0
    s16.Glass = 'BK7'
    s16.Note = ('Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene '
 'mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter '
 'to align the closed mesh in millimetres.')
    s16.OpticalSolidFaces = {'faces': [{'analytic_parameters': {'axis': [0.0, 0.0, 1.0], 'origin': [-35.0, -5.25, 5.25]},
            'area_mm2': 734.9999999999999,
            'assignment_source': 'default_uncoated',
            'centroid': [-2.7068294695622867e-15, -3.816391647148976e-17, 5.25],
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
            'normal': [0.0, -0.0, 1.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 5.25,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, 0.7071067811865476, -0.7071067811865476],
                                    'origin': [-35.0, 5.25, 5.25]},
            'area_mm2': 1039.4469683442248,
            'assignment_source': 'manual',
            'centroid': [-2.3925218418038477e-15, -6.626643678231404e-16, -6.626643678231404e-16],
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
            'normal': [0.0, 0.7071067811865476, -0.7071067811865476],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 0.0,
            'port_role': 'Interaction Surface',
            'recovered_coating': False,
            'role': 'Mirror',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, -1.0, 0.0], 'origin': [-35.0, -5.25, -5.25]},
            'area_mm2': 734.9999999999999,
            'assignment_source': 'default_uncoated',
            'centroid': [-2.7068294695622867e-15, -5.25, -3.816391647148976e-17],
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
            'normal': [0.0, -1.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 5.25,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [-35.0, -1.537689398771, 1.537689398771]},
            'area_mm2': 55.125,
            'assignment_source': 'default_uncoated',
            'centroid': [-35.0, -1.7500000000000007, 1.7499999999999996],
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
            'normal': [-1.0, -0.0, -0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 35.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [35.0, -1.537689398771, 1.537689398771]},
            'area_mm2': 55.125,
            'assignment_source': 'default_uncoated',
            'centroid': [35.0, -1.7500000000000007, 1.7499999999999996],
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
            'normal': [1.0, 0.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 35.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_105_1788223195_12564.stl',
 'version': 1,
 'virtual_planes': []}
    s16.Solid_3d_stl = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_105_1788223195_12564.stl'
    s16.StepOverlayPromotion = {'center_world': [0.0, 0.0, -63.15]}
    surfaces.append({'surface': 'Standard', 'element': 'Solid wedge 105 1788223195 12564', 'name': 'Outer prism B', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 0.0, 'diameter': 25.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {'Note': 'Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter to align the closed mesh in millimetres.', 'OpticalSolidFaces': {'version': 1, 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_105_1788223195_12564.stl', 'faces': [{'face_id': 'S001/F001', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -0.0, 1.0], 'centroid': [-2.7068294695622867e-15, -3.816391647148976e-17, 5.25], 'area_mm2': 734.9999999999999, 'triangle_count': 2, 'triangle_indices': [0, 1], 'plane_offset_mm': 5.25, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F001', 'source_face_id': 'S001/F001', 'source_solid_index': 1, 'source_face_index': 1, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -5.25, 5.25], 'axis': [0.0, 0.0, 1.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F002', 'role': 'Mirror', 'function': 'Mirror', 'side_2d': 'Auto', 'port_role': 'Interaction Surface', 'fit_reference': 'Auto', 'normal': [0.0, 0.7071067811865476, -0.7071067811865476], 'centroid': [-2.3925218418038477e-15, -6.626643678231404e-16, -6.626643678231404e-16], 'area_mm2': 1039.4469683442248, 'triangle_count': 2, 'triangle_indices': [2, 3], 'plane_offset_mm': 0.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'manual', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F002', 'source_face_id': 'S001/F002', 'source_solid_index': 1, 'source_face_index': 2, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, 5.25, 5.25], 'axis': [0.0, 0.7071067811865476, -0.7071067811865476]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F003', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -1.0, 0.0], 'centroid': [-2.7068294695622867e-15, -5.25, -3.816391647148976e-17], 'area_mm2': 734.9999999999999, 'triangle_count': 2, 'triangle_indices': [4, 5], 'plane_offset_mm': 5.25, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F003', 'source_face_id': 'S001/F003', 'source_solid_index': 1, 'source_face_index': 3, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -5.25, -5.25], 'axis': [0.0, -1.0, 0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F004', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [-1.0, -0.0, -0.0], 'centroid': [-35.0, -1.7500000000000007, 1.7499999999999996], 'area_mm2': 55.125, 'triangle_count': 1, 'triangle_indices': [6], 'plane_offset_mm': 35.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F004', 'source_face_id': 'S001/F004', 'source_solid_index': 1, 'source_face_index': 4, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -1.537689398771, 1.537689398771], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F005', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [1.0, 0.0, 0.0], 'centroid': [35.0, -1.7500000000000007, 1.7499999999999996], 'area_mm2': 55.125, 'triangle_count': 1, 'triangle_indices': [7], 'plane_offset_mm': 35.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F005', 'source_face_id': 'S001/F005', 'source_solid_index': 1, 'source_face_index': 5, 'surface_type': 'plane', 'analytic_parameters': {'origin': [35.0, -1.537689398771, 1.537689398771], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}], 'virtual_planes': []}, 'Solid_3d_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_105_1788223195_12564.stl', 'StepOverlayPromotion': {'center_world': [0.0, 0.0, -63.15]}}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 180.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': -477.42, 'axis_move': 0.0, 'glass': 'BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s17 = Kos.surf()
    s17.Name = 'Lower prism B'
    s17.Rc = 0.0
    s17.k = 0.0
    s17.Axicon = 0.0
    s17.Diff_Ord = 0.0
    s17.Grating_D = 0.0
    s17.Grating_Angle = 0.0
    s17.Thickness = 0.0
    s17.Diameter = 25.0
    s17.InDiameter = 0.0
    s17.Drawing = 1.0
    s17.TiltX = 0.0
    s17.TiltY = 0.0
    s17.TiltZ = 0.0
    s17.DespX = 0.0
    s17.DespY = 11.65
    s17.DespZ = -474.67
    s17.AxisMove = 0.0
    s17.Glass = 'BK7'
    s17.Note = ('Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene '
 'mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter '
 'to align the closed mesh in millimetres.')
    s17.OpticalSolidFaces = {'faces': [{'analytic_parameters': {'axis': [0.0, 0.0, 1.0], 'origin': [-35.0, -7.5, 7.5]},
            'area_mm2': 1050.0,
            'assignment_source': 'default_uncoated',
            'centroid': [-9.473903143468002e-16, -1.6306400674181987e-16, 7.5],
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
            'normal': [0.0, -0.0, 1.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 7.5,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, 0.7071067811865476, -0.7071067811865476],
                                    'origin': [-35.0, 7.5, 7.5]},
            'area_mm2': 1484.92424049175,
            'assignment_source': 'manual',
            'centroid': [-1.5072887603364238e-15, -3.1918911957973236e-16, -3.1918911957973236e-16],
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
            'normal': [0.0, 0.7071067811865476, -0.7071067811865476],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 0.0,
            'port_role': 'Interaction Surface',
            'recovered_coating': False,
            'role': 'Mirror',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, -1.0, 0.0], 'origin': [-35.0, -7.5, -7.5]},
            'area_mm2': 1050.0,
            'assignment_source': 'default_uncoated',
            'centroid': [-9.473903143468002e-16, -7.5, -1.6306400674181987e-16],
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
            'normal': [0.0, -1.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 7.5,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [-35.0, -2.196699141101, 2.196699141101]},
            'area_mm2': 112.50000000000001,
            'assignment_source': 'default_uncoated',
            'centroid': [-35.0, -2.5, 2.5],
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
            'normal': [-1.0, -0.0, -0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 35.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [35.0, -2.196699141101, 2.196699141101]},
            'area_mm2': 112.50000000000001,
            'assignment_source': 'default_uncoated',
            'centroid': [35.0, -2.5, 2.5],
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
            'normal': [1.0, 0.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 35.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_150_1788223195_12526.stl',
 'version': 1,
 'virtual_planes': []}
    s17.Solid_3d_stl = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_150_1788223195_12526.stl'
    s17.StepOverlayPromotion = {'center_world': [0.0, 11.65, -60.4]}
    surfaces.append({'surface': 'Standard', 'element': 'Solid wedge 150 1788223195 12526', 'name': 'Lower prism B', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 0.0, 'diameter': 25.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {'Note': 'Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter to align the closed mesh in millimetres.', 'OpticalSolidFaces': {'version': 1, 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_150_1788223195_12526.stl', 'faces': [{'face_id': 'S001/F001', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -0.0, 1.0], 'centroid': [-9.473903143468002e-16, -1.6306400674181987e-16, 7.5], 'area_mm2': 1050.0, 'triangle_count': 2, 'triangle_indices': [0, 1], 'plane_offset_mm': 7.5, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F001', 'source_face_id': 'S001/F001', 'source_solid_index': 1, 'source_face_index': 1, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -7.5, 7.5], 'axis': [0.0, 0.0, 1.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F002', 'role': 'Mirror', 'function': 'Mirror', 'side_2d': 'Auto', 'port_role': 'Interaction Surface', 'fit_reference': 'Auto', 'normal': [0.0, 0.7071067811865476, -0.7071067811865476], 'centroid': [-1.5072887603364238e-15, -3.1918911957973236e-16, -3.1918911957973236e-16], 'area_mm2': 1484.92424049175, 'triangle_count': 2, 'triangle_indices': [2, 3], 'plane_offset_mm': 0.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'manual', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F002', 'source_face_id': 'S001/F002', 'source_solid_index': 1, 'source_face_index': 2, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, 7.5, 7.5], 'axis': [0.0, 0.7071067811865476, -0.7071067811865476]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F003', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -1.0, 0.0], 'centroid': [-9.473903143468002e-16, -7.5, -1.6306400674181987e-16], 'area_mm2': 1050.0, 'triangle_count': 2, 'triangle_indices': [4, 5], 'plane_offset_mm': 7.5, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F003', 'source_face_id': 'S001/F003', 'source_solid_index': 1, 'source_face_index': 3, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -7.5, -7.5], 'axis': [0.0, -1.0, 0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F004', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [-1.0, -0.0, -0.0], 'centroid': [-35.0, -2.5, 2.5], 'area_mm2': 112.50000000000001, 'triangle_count': 1, 'triangle_indices': [6], 'plane_offset_mm': 35.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F004', 'source_face_id': 'S001/F004', 'source_solid_index': 1, 'source_face_index': 4, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -2.196699141101, 2.196699141101], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F005', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [1.0, 0.0, 0.0], 'centroid': [35.0, -2.5, 2.5], 'area_mm2': 112.50000000000001, 'triangle_count': 1, 'triangle_indices': [7], 'plane_offset_mm': 35.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F005', 'source_face_id': 'S001/F005', 'source_solid_index': 1, 'source_face_index': 5, 'surface_type': 'plane', 'analytic_parameters': {'origin': [35.0, -2.196699141101, 2.196699141101], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}], 'virtual_planes': []}, 'Solid_3d_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_150_1788223195_12526.stl', 'StepOverlayPromotion': {'center_world': [0.0, 11.65, -60.4]}}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 11.65, 'desp_z': -474.67, 'axis_move': 0.0, 'glass': 'BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s18 = Kos.surf()
    s18.Name = 'Centre prism B'
    s18.Rc = 0.0
    s18.k = 0.0
    s18.Axicon = 0.0
    s18.Diff_Ord = 0.0
    s18.Grating_D = 0.0
    s18.Grating_Angle = 0.0
    s18.Thickness = 0.0
    s18.Diameter = 25.0
    s18.InDiameter = 0.0
    s18.Drawing = 1.0
    s18.TiltX = 90.0
    s18.TiltY = 0.0
    s18.TiltZ = 180.0
    s18.DespX = 0.0
    s18.DespY = 13.73
    s18.DespZ = -448.67
    s18.AxisMove = 0.0
    s18.Glass = 'BK7'
    s18.Note = ('Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene '
 'mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter '
 'to align the closed mesh in millimetres.')
    s18.OpticalSolidFaces = {'faces': [{'analytic_parameters': {'axis': [0.0, 0.0, 1.0], 'origin': [-35.0, -6.0, 6.0]},
            'area_mm2': 840.0,
            'assignment_source': 'default_uncoated',
            'centroid': [-2.0724163126336257e-15, 1.5612511283791266e-16, 6.0],
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
            'normal': [0.0, -0.0, 1.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 6.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, 0.7071067811865476, -0.7071067811865476],
                                    'origin': [-35.0, 6.0, 6.0]},
            'area_mm2': 1187.9393923933999,
            'assignment_source': 'manual',
            'centroid': [-8.373826446313467e-16, -1.1136924715771105e-15, -1.1136924715771105e-15],
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
            'normal': [0.0, 0.7071067811865476, -0.7071067811865476],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 0.0,
            'port_role': 'Interaction Surface',
            'recovered_coating': False,
            'role': 'Mirror',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [0.0, -1.0, 0.0], 'origin': [-35.0, -6.0, -6.0]},
            'area_mm2': 840.0,
            'assignment_source': 'default_uncoated',
            'centroid': [-2.0724163126336257e-15, -6.0, 1.5612511283791266e-16],
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
            'normal': [0.0, -1.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 6.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [-35.0, -1.757359312881, 1.757359312881]},
            'area_mm2': 72.00000000000001,
            'assignment_source': 'default_uncoated',
            'centroid': [-35.0, -2.0000000000000013, 1.999999999999999],
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
            'normal': [-1.0, -0.0, -0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 35.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
           {'analytic_parameters': {'axis': [-1.0, -0.0, -0.0],
                                    'origin': [35.0, -1.757359312881, 1.757359312881]},
            'area_mm2': 72.00000000000001,
            'assignment_source': 'default_uncoated',
            'centroid': [35.0, -2.0000000000000013, 1.999999999999999],
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
            'normal': [1.0, 0.0, 0.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 35.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
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
 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_120_1788223195_12490.stl',
 'version': 1,
 'virtual_planes': []}
    s18.Solid_3d_stl = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_120_1788223195_12490.stl'
    s18.StepOverlayPromotion = {'center_world': [0.0, 13.73, -34.4]}
    surfaces.append({'surface': 'Standard', 'element': 'Solid wedge 120 1788223195 12490', 'name': 'Centre prism B', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 0.0, 'diameter': 25.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {'Note': 'Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in non-sequential scene mode; STEP/IGES sources are meshed to a cached STL. Use Material, Thickness, Tilt, and Decenter to align the closed mesh in millimetres.', 'OpticalSolidFaces': {'version': 1, 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_120_1788223195_12490.stl', 'faces': [{'face_id': 'S001/F001', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -0.0, 1.0], 'centroid': [-2.0724163126336257e-15, 1.5612511283791266e-16, 6.0], 'area_mm2': 840.0, 'triangle_count': 2, 'triangle_indices': [0, 1], 'plane_offset_mm': 6.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F001', 'source_face_id': 'S001/F001', 'source_solid_index': 1, 'source_face_index': 1, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -6.0, 6.0], 'axis': [0.0, 0.0, 1.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F002', 'role': 'Mirror', 'function': 'Mirror', 'side_2d': 'Auto', 'port_role': 'Interaction Surface', 'fit_reference': 'Auto', 'normal': [0.0, 0.7071067811865476, -0.7071067811865476], 'centroid': [-8.373826446313467e-16, -1.1136924715771105e-15, -1.1136924715771105e-15], 'area_mm2': 1187.9393923933999, 'triangle_count': 2, 'triangle_indices': [2, 3], 'plane_offset_mm': 0.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'manual', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F002', 'source_face_id': 'S001/F002', 'source_solid_index': 1, 'source_face_index': 2, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, 6.0, 6.0], 'axis': [0.0, 0.7071067811865476, -0.7071067811865476]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F003', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, -1.0, 0.0], 'centroid': [-2.0724163126336257e-15, -6.0, 1.5612511283791266e-16], 'area_mm2': 840.0, 'triangle_count': 2, 'triangle_indices': [4, 5], 'plane_offset_mm': 6.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F003', 'source_face_id': 'S001/F003', 'source_solid_index': 1, 'source_face_index': 3, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -6.0, -6.0], 'axis': [0.0, -1.0, 0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F004', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [-1.0, -0.0, -0.0], 'centroid': [-35.0, -2.0000000000000013, 1.999999999999999], 'area_mm2': 72.00000000000001, 'triangle_count': 1, 'triangle_indices': [6], 'plane_offset_mm': 35.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F004', 'source_face_id': 'S001/F004', 'source_solid_index': 1, 'source_face_index': 4, 'surface_type': 'plane', 'analytic_parameters': {'origin': [-35.0, -1.757359312881, 1.757359312881], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F005', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [1.0, 0.0, 0.0], 'centroid': [35.0, -2.0000000000000013, 1.999999999999999], 'area_mm2': 72.00000000000001, 'triangle_count': 1, 'triangle_indices': [7], 'plane_offset_mm': 35.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'default_uncoated', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F005', 'source_face_id': 'S001/F005', 'source_solid_index': 1, 'source_face_index': 5, 'surface_type': 'plane', 'analytic_parameters': {'origin': [35.0, -1.757359312881, 1.757359312881], 'axis': [-1.0, -0.0, -0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}], 'virtual_planes': []}, 'Solid_3d_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/wedge_120_1788223195_12490.stl', 'StepOverlayPromotion': {'center_world': [0.0, 13.73, -34.4]}}, 'tilt_x': 90.0, 'tilt_y': 0.0, 'tilt_z': 180.0, 'desp_x': 0.0, 'desp_y': 13.73, 'desp_z': -448.67, 'axis_move': 0.0, 'glass': 'BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s19 = Kos.surf()
    s19.Name = 'Image / Sensor'
    s19.Rc = 0.0
    s19.k = 0.0
    s19.Axicon = 0.0
    s19.Diff_Ord = 0.0
    s19.Grating_D = 0.0
    s19.Grating_Angle = 0.0
    s19.Thickness = 0.0
    s19.Diameter = 32.58
    s19.InDiameter = 0.0
    s19.Drawing = 1.0
    s19.TiltX = 0.0
    s19.TiltY = 0.0
    s19.TiltZ = 0.0
    s19.DespX = 0.0
    s19.DespY = 0.0
    s19.DespZ = 0.0
    s19.AxisMove = 0.0
    s19.Glass = 'AIR'
    surfaces.append({'surface': 'Image', 'element': '', 'name': 'Image / Sensor', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 0.0, 'diameter': 32.58, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

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

