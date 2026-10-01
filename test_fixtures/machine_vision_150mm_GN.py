#!/usr/bin/env python3
TITLE = "Machine Vision 150Mm Gn"

SETTINGS = {'object_mode': 'Finite',
 'display_orientation': 'YZ',
 'projection_display_mode': 'Full 3D',
 'wavelength': '0.546',
 'ray_count': '9',
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
 'inspection_part': {'enabled': False,
                     'width_mm': 60.0,
                     'height_mm': 40.0,
                     'depth_mm': 20.0,
                     'active_face': 'front',
                     'axis_reach_mm': 0.0,
                     'axis_offset_mm': 0.0,
                     'step_path': ''},
 'display_fold_spec': None,
 'camera_focus_stage': None,
 'split_field_arm_offset_mm': None,
 'object_fov_bands': None,
 'launch_pupil_aim_offset': None,
 'analysis_surface': 'Auto',
 'analysis_branch_filter': 'All paths',
 'ray_display_mode': 'All rays',
 'detector_bins': 'Auto',
 'coherent_sum_mode': 'By source ray',
 'branch_field_propagation_mm': '0.0',
 'aperture_type': 'EPD',
 'aperture_value': '26.8',
 'spot_view_mode': 'Grid',
 'wavefront_style': 'Wavefront Function',
 'tolerance_compare_view': 'Spot overlay',
 'show_clipped_rays': False,
 'show_path_labels': True,
 'show_cardinals': True,
 'show_physical_distances': False,
 'field_type': 'Real Image Height',
 'field_value': '9.05096679919',
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
 'trace_mode': 'Non-Sequential Preview',
 'folded_detector_policy': 'Trace events',
 'nonseq_target_surface': 'Auto',
 'nonseq_ns_limit': '200',
 'nonseq_energy_probability': False,
 'camera_model': 'Japan Bopixel BC-GN25M12X4',
 'camera_precouple_stash': {'field_type': 'Real Image Height',
                            'field_value': '18.6800026767',
                            'image_diameter_mode': 'Manual',
                            'image_diameter': 37.3600053533},
 'branch_detector_camera_assignments': {},
 'step_clear_aperture_by_label': {},
 'clear_aperture_edge_rects_by_label': {},
 'optical_led_glued': False,
 'step_glue_reference_offset_xyz': {'camera': [0.0, 0.0, 0.0],
                                    'lens': [0.0, 0.0, 0.0],
                                    'optical': [0.0, 0.0, 0.0],
                                    'led': [22.885559396499687,
                                            -0.02084762020131367,
                                            -2.3135618448558857]},
 'step_glue_reference_datum_mid_xyz': {'lens': [0.0, 0.0, 299.40499999860003],
                                       'led': [0.0, 0.0, 0.0]},
 'camera_step_path': 'attachment/Cameras/BC-GM25M12X4/BC-GM(C)25M12X4.STEP',
 'camera_step_rotation_x_deg': 0.0,
 'camera_step_rotation_y_deg': 0.0,
 'camera_step_rotation_z_deg': 0.0,
 'camera_step_axis_offset_xy': [0.0, 0.0],
 'camera_step_placement_offset_xyz': [0.0, 0.0, 0.0],
 'camera_step_reverse_direction': False,
 'lens_step_path': 'attachment/Lens/15056/15056.STEP',
 'lens_step_largest_component_only': True,
 'lens_step_reverse_direction': False,
 'lens_step_rotation_x_deg': 0.0,
 'lens_step_rotation_y_deg': 0.0,
 'lens_step_rotation_z_deg': 0.0,
 'lens_step_axis_offset_xy': [0.0, 0.0],
 'lens_step_placement_offset_xyz': [0.0, 0.0, 0.0],
 'optical_step_path': '',
 'optical_step_rotation_x_deg': 0.0,
 'optical_step_rotation_y_deg': 0.0,
 'optical_step_rotation_z_deg': 0.0,
 'optical_step_axis_offset_xy': [0.0, 0.0],
 'optical_step_placement_offset_xyz': [0.0, 0.0, 0.0],
 'led_step_path': 'attachment/LED/OPT-CO90-X-V1.6.2-H.STEP',
 'led_step_rotation_x_deg': 180.0,
 'led_step_rotation_y_deg': 7.016709298534876e-15,
 'led_step_rotation_z_deg': 180.0,
 'led_object_edge_distance_mm': 202.31356184485588,
 'led_step_object_edge_local_z': 12.823598023324877,
 'dimension_anchor_overrides': {},
 'hidden_thickness_dimension_rows': [],
 'led_step_axis_offset_xy': [0.0, 0.0],
 'led_step_placement_offset_xyz': [22.885559396499687, -0.02084762020131367, -2.3135618448558857],
 'analysis_mode': 'none',
 'analysis_modes': [],
 'layout_preview_mode': 'none',
 'auto_save_plot': False,
 'external_camera': 'None',
 'camera_overlay_mode': 'Off',
 'metal_catalogs': [],
 'optimization_workers': 'Auto',
 'selected_operands': ['Spot RMS'],
 'operands': {'Thickness penalty': {'weight': '1',
                                    'target': '0.1',
                                    'wavelength': '0.55',
                                    'field': '0',
                                    'surface': 'Auto'},
              'Spot RMS': {'weight': '1',
                           'target': '0',
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
                             'mtf_algorithm': 'Diffraction FFT'},
              'EFFL': {'weight': '1',
                       'target': '100',
                       'wavelength': '0.55',
                       'field': '0',
                       'surface': 'Auto'},
              'Entrance pupil z': {'weight': '1',
                                   'target': '0',
                                   'wavelength': '0.55',
                                   'field': '0',
                                   'surface': 'Auto'},
              'Magnification': {'weight': '1',
                                'target': '1',
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
    s0.Thickness = 215.670815464
    s0.Diameter = 18.1019335986
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
    surfaces.append({'surface': 'Object', 'element': '', 'name': 'Object', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 215.670815464, 'diameter': 18.1019335986, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s1 = Kos.surf()
    s1.Name = 'Promoted OPTICAL STEP optical solid'
    s1.Rc = 0.0
    s1.k = 0.0
    s1.Axicon = 0.0
    s1.Diff_Ord = 0.0
    s1.Grating_D = 0.0
    s1.Grating_Angle = 0.0
    s1.Thickness = 55.0
    s1.Diameter = 78.0
    s1.InDiameter = 0.0
    s1.Drawing = 1.0
    s1.TiltX = 0.0
    s1.TiltY = 0.0
    s1.TiltZ = 0.0
    s1.DespX = 3.5527136788e-15
    s1.DespY = -3.5527136788e-15
    s1.DespZ = 11.9
    s1.AxisMove = 0.0
    s1.Glass = 'BK7'
    s1.Note = ('Promoted from an Open 3D imported STEP overlay. The cached Solid_3d_stl mesh is saved in local '
 'coordinates around the overlay center, while row Desp stores the scene/world center. AxisMove '
 "stays zero so the scene object's placement does not move downstream Object/Image rows; explicit "
 'output ports provide the separate follower-row workflow. Review material and CAD/STL optical '
 'face roles before relying on traced physics.')
    s1.OpticalSolidFaces = {'faces': [{'analytic_parameters': {'axis': [-0.7071067811865476, 0.7071067811865476, 0.0],
                                    'origin': [50.0, 50.0, 50.0]},
            'area_mm2': 6066.976182580578,
            'assignment_source': 'manual',
            'centroid': [1.844012512054388e-15, -1.2443762686260668e-15, 0.0],
            'clear_aperture_mm': 0.0,
            'coating': '',
            'component_face_id': 'S001/F001',
            'duplicate_group': 'I001',
            'face_id': 'S001/F001',
            'fit_reference': 'Auto',
            'flip_normal': False,
            'function': 'Beam Splitter',
            'input_offset_u_mm': 0.0,
            'input_offset_v_mm': 0.0,
            'interior_duplicate': True,
            'loss': 0.0,
            'material': '',
            'normal': [-0.7071067811865475, 4.017094365154572e-16, 0.7071067811865477],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': -1.3039137518664984e-15,
            'port_role': 'Interaction Surface',
            'recovered_coating': True,
            'role': 'Beam Splitter',
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
           {'analytic_parameters': {'axis': [0.0, -1.0, 0.0], 'origin': [0.0, 50.0, 50.0]},
            'area_mm2': 4290.0,
            'assignment_source': 'manual',
            'centroid': [27.5, -1.5103587896028796e-14, -5.684341886080802e-14],
            'clear_aperture_mm': 0.0,
            'coating': '',
            'component_face_id': 'S001/F002',
            'duplicate_group': '',
            'face_id': 'S001/F002',
            'fit_reference': 'Auto',
            'flip_normal': False,
            'function': 'Absorber/Mechanical',
            'input_offset_u_mm': 0.0,
            'input_offset_v_mm': 0.0,
            'interior_duplicate': False,
            'loss': 0.0,
            'material': '',
            'normal': [1.0, -1.8219044506669235e-16, 1.176855429700344e-32],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 27.5,
            'port_role': 'Interaction Surface',
            'recovered_coating': False,
            'role': 'Absorber/Mechanical',
            'side_2d': 'Back',
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
           {'analytic_parameters': {'axis': [1.0, 0.0, 0.0], 'origin': [0.0, 0.0, 50.0]},
            'area_mm2': 4290.0,
            'assignment_source': 'step_analytic_transformed',
            'centroid': [-1.60658847013356e-16, -3.231395984773789e-15, -27.50000000000003],
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
            'normal': [0.0, 0.0, -1.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 27.50000000000003,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Left',
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
           {'analytic_parameters': {'axis': [0.0, 0.0, -1.0], 'origin': [0.0, 0.0, 50.0]},
            'area_mm2': 1512.4999999999993,
            'assignment_source': 'step_analytic_transformed',
            'centroid': [9.166666666666675, 39.0, -9.166666666666686],
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
            'normal': [2.583791766400364e-16, 1.0, -1.2918958832001828e-16],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 39.0,
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
           {'analytic_parameters': {'axis': [0.0, 0.0, -1.0], 'origin': [0.0, 0.0, 0.0]},
            'area_mm2': 1512.500000000001,
            'assignment_source': 'step_analytic_transformed',
            'centroid': [9.16666666666666, -39.0, -9.166666666666714],
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
            'normal': [-2.583791766400364e-16, -1.0, 1.2918958832001816e-16],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 39.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Down',
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
            'triangle_indices': [7]},
           {'analytic_parameters': {'axis': [-7.347880794884117e-17, 1.0, 0.0],
                                    'origin': [50.00000000000001, 3.673940397442059e-15, 50.0]},
            'area_mm2': 4290.0,
            'assignment_source': 'step_analytic_transformed',
            'centroid': [-27.499999999999996, 1.8566862629069285e-15, -2.842170943040401e-14],
            'clear_aperture_mm': 0.0,
            'coating': '',
            'component_face_id': 'S002/F001',
            'duplicate_group': '',
            'face_id': 'S002/F001',
            'fit_reference': 'Auto',
            'flip_normal': False,
            'function': 'Transmit/Port',
            'input_offset_u_mm': 0.0,
            'input_offset_v_mm': 0.0,
            'interior_duplicate': False,
            'loss': 0.0,
            'material': '',
            'normal': [-1.0, 1.821904450666924e-16, 1.291895883200182e-16],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 27.499999999999996,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Front',
            'source_face_id': 'S002/F001',
            'source_face_index': 6,
            'source_solid_index': 2,
            'split_ratio': 0.5,
            'suggested_function': 'Unassigned',
            'suggested_port_role': 'Auto',
            'suggested_side_2d': 'Auto',
            'suggestion_confidence': 0.0,
            'suggestion_reason': '',
            'suggestion_source': '',
            'surface_type': 'plane',
            'triangle_count': 2,
            'triangle_indices': [8, 9]},
           {'analytic_parameters': {'axis': [-1.0, -1.387778780781446e-16, 0.0],
                                    'origin': [50.0, 50.0, 50.0]},
            'area_mm2': 4290.0,
            'assignment_source': 'step_analytic_transformed',
            'centroid': [3.231395984773789e-15, 3.552713678800501e-15, 27.5],
            'clear_aperture_mm': 0.0,
            'coating': '',
            'component_face_id': 'S002/F002',
            'duplicate_group': '',
            'face_id': 'S002/F002',
            'fit_reference': 'Auto',
            'flip_normal': False,
            'function': 'Transmit/Port',
            'input_offset_u_mm': 0.0,
            'input_offset_v_mm': 0.0,
            'interior_duplicate': False,
            'loss': 0.0,
            'material': '',
            'normal': [1.8829686875205503e-31, 7.287617802667694e-16, 1.0],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 27.5,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Right',
            'source_face_id': 'S002/F002',
            'source_face_index': 7,
            'source_solid_index': 2,
            'split_ratio': 0.5,
            'suggested_function': 'Unassigned',
            'suggested_port_role': 'Auto',
            'suggested_side_2d': 'Auto',
            'suggestion_confidence': 0.0,
            'suggestion_reason': '',
            'suggestion_source': '',
            'surface_type': 'plane',
            'triangle_count': 2,
            'triangle_indices': [10, 11]},
           {'analytic_parameters': {'axis': [0.0, 0.0, 1.0], 'origin': [0.0, 0.0, 50.0]},
            'area_mm2': 1512.4999999999993,
            'assignment_source': 'step_analytic_transformed',
            'centroid': [-9.166666666666659, 39.0, 9.1666666666666],
            'clear_aperture_mm': 0.0,
            'coating': '',
            'component_face_id': 'S002/F004',
            'duplicate_group': '',
            'face_id': 'S002/F004',
            'fit_reference': 'Auto',
            'flip_normal': False,
            'function': 'Transmit/Port',
            'input_offset_u_mm': 0.0,
            'input_offset_v_mm': 0.0,
            'interior_duplicate': False,
            'loss': 0.0,
            'material': '',
            'normal': [2.583791766400364e-16, 1.0, -1.291895883200183e-16],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 39.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Up',
            'source_face_id': 'S002/F004',
            'source_face_index': 9,
            'source_solid_index': 2,
            'split_ratio': 0.5,
            'suggested_function': 'Unassigned',
            'suggested_port_role': 'Auto',
            'suggested_side_2d': 'Auto',
            'suggestion_confidence': 0.0,
            'suggestion_reason': '',
            'suggestion_source': '',
            'surface_type': 'plane',
            'triangle_count': 1,
            'triangle_indices': [12]},
           {'analytic_parameters': {'axis': [0.0, 0.0, 1.0], 'origin': [0.0, 0.0, 0.0]},
            'area_mm2': 1512.5000000000007,
            'assignment_source': 'step_analytic_transformed',
            'centroid': [-9.166666666666673, -39.0, 9.166666666666686],
            'clear_aperture_mm': 0.0,
            'coating': '',
            'component_face_id': 'S002/F005',
            'duplicate_group': '',
            'face_id': 'S002/F005',
            'fit_reference': 'Auto',
            'flip_normal': False,
            'function': 'Transmit/Port',
            'input_offset_u_mm': 0.0,
            'input_offset_v_mm': 0.0,
            'interior_duplicate': False,
            'loss': 0.0,
            'material': '',
            'normal': [-2.5837917664003647e-16, -1.0, 1.2918958832001818e-16],
            'notes': 'OpenCascade STEP analytic face',
            'phase_deg': 0.0,
            'plane_offset_mm': 39.0,
            'port_role': 'Auto',
            'recovered_coating': False,
            'role': 'Output',
            'side_2d': 'Auto',
            'source_face_id': 'S002/F005',
            'source_face_index': 10,
            'source_solid_index': 2,
            'split_ratio': 0.5,
            'suggested_function': 'Unassigned',
            'suggested_port_role': 'Auto',
            'suggested_side_2d': 'Auto',
            'suggestion_confidence': 0.0,
            'suggestion_reason': '',
            'suggestion_source': '',
            'surface_type': 'plane',
            'triangle_count': 1,
            'triangle_indices': [13]}],
 'interior_duplicate_count': 2,
 'metadata_coordinates': 'local_centered_promoted_row',
 'outer_face_count': 9,
 'promoted_face_metadata_source': 'open3d_step_overlay',
 'source_backend': 'OpenCascade',
 'source_face_count': 10,
 'source_step': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Beam_Splitter/32704/step_32704.step',
 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/promoted_step_overlays/optical_aae83ad73a8d39d8.stl',
 'version': 1,
 'virtual_planes': []}
    s1.OpticalSolidSourceFormat = 'STEP'
    s1.OpticalSolidSourcePath = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Beam_Splitter/32704/step_32704.step'
    s1.ScenePlacement = {'anchor': 'row_pose',
 'enabled': True,
 'grid_extent_mm': 156.00000000000006,
 'grid_spacing_mm': 7.8000000000000025,
 'grid_visible': True,
 'last_translate_axis': 'xyz',
 'last_translate_delta_mm': [0.0, 0.0, 2.313561844855883],
 'last_translate_mode': 'free_drag',
 'last_translate_step_mm': 2.313561844855883,
 'promotion_mesh_coordinates': 'local_centered_from_open3d_overlay',
 'promotion_source': 'open3d_step_overlay',
 'promotion_source_step_path': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Beam_Splitter/32704/step_32704.step',
 'promotion_step_label': 'optical',
 'snap_deg': 5.0,
 'snap_enabled': True,
 'snap_mm': 3.9000000000000012}
    s1.Solid_3d_stl = '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/promoted_step_overlays/optical_aae83ad73a8d39d8.stl'
    s1.StepOverlayPromotion = {'axial_reserve_mm': 55.00000000000003,
 'axis_offset_xy': [0.0, 0.0],
 'bounds_max_world': [27.500000000000014, 39.00000000000001, 270.6708154643988],
 'bounds_min_world': [-27.500000000000007, -39.000000000000014, 215.67081546439877],
 'center_world': [3.552713678800501e-15, -3.552713678800501e-15, 243.1708154643988],
 'largest_component_only': None,
 'mesh_coordinates': 'local_centered_from_open3d_overlay',
 'placement_offset_xyz': [5.329070518200751e-15, 1.7763568394002505e-15, 204.17081546439877],
 'preserved_face_count': 9,
 'promoted_mesh_path': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/promoted_step_overlays/optical_aae83ad73a8d39d8.stl',
 'row_thickness_mm': 55.00000000000003,
 'source_step_path': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Beam_Splitter/32704/step_32704.step',
 'step_label': 'optical',
 'step_rotation_deg': [0.0, 270.0, 270.0]}
    surfaces.append({'surface': 'Standard', 'element': 'OPTICAL STEP solid', 'name': 'Promoted OPTICAL STEP optical solid', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 55.0, 'diameter': 78.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {'Note': "Promoted from an Open 3D imported STEP overlay. The cached Solid_3d_stl mesh is saved in local coordinates around the overlay center, while row Desp stores the scene/world center. AxisMove stays zero so the scene object's placement does not move downstream Object/Image rows; explicit output ports provide the separate follower-row workflow. Review material and CAD/STL optical face roles before relying on traced physics.", 'OpticalSolidFaces': {'version': 1, 'source_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/promoted_step_overlays/optical_aae83ad73a8d39d8.stl', 'faces': [{'face_id': 'S001/F001', 'role': 'Beam Splitter', 'function': 'Beam Splitter', 'side_2d': 'Auto', 'port_role': 'Interaction Surface', 'fit_reference': 'Auto', 'normal': [-0.7071067811865475, 4.017094365154572e-16, 0.7071067811865477], 'centroid': [1.844012512054388e-15, -1.2443762686260668e-15, 0.0], 'area_mm2': 6066.976182580578, 'triangle_count': 2, 'triangle_indices': [0, 1], 'plane_offset_mm': -1.3039137518664984e-15, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'manual', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F001', 'source_face_id': 'S001/F001', 'source_solid_index': 1, 'source_face_index': 1, 'surface_type': 'plane', 'analytic_parameters': {'origin': [50.0, 50.0, 50.0], 'axis': [-0.7071067811865476, 0.7071067811865476, 0.0]}, 'interior_duplicate': True, 'duplicate_group': 'I001', 'recovered_coating': True}, {'face_id': 'S001/F002', 'role': 'Absorber/Mechanical', 'function': 'Absorber/Mechanical', 'side_2d': 'Back', 'port_role': 'Interaction Surface', 'fit_reference': 'Auto', 'normal': [1.0, -1.8219044506669235e-16, 1.176855429700344e-32], 'centroid': [27.5, -1.5103587896028796e-14, -5.684341886080802e-14], 'area_mm2': 4290.0, 'triangle_count': 2, 'triangle_indices': [2, 3], 'plane_offset_mm': 27.5, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'manual', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F002', 'source_face_id': 'S001/F002', 'source_solid_index': 1, 'source_face_index': 2, 'surface_type': 'plane', 'analytic_parameters': {'origin': [0.0, 50.0, 50.0], 'axis': [0.0, -1.0, 0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F003', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Left', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [0.0, 0.0, -1.0], 'centroid': [-1.60658847013356e-16, -3.231395984773789e-15, -27.50000000000003], 'area_mm2': 4290.0, 'triangle_count': 2, 'triangle_indices': [4, 5], 'plane_offset_mm': 27.50000000000003, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'step_analytic_transformed', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F003', 'source_face_id': 'S001/F003', 'source_solid_index': 1, 'source_face_index': 3, 'surface_type': 'plane', 'analytic_parameters': {'origin': [0.0, 0.0, 50.0], 'axis': [1.0, 0.0, 0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F004', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [2.583791766400364e-16, 1.0, -1.2918958832001828e-16], 'centroid': [9.166666666666675, 39.0, -9.166666666666686], 'area_mm2': 1512.4999999999993, 'triangle_count': 1, 'triangle_indices': [6], 'plane_offset_mm': 39.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'step_analytic_transformed', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F004', 'source_face_id': 'S001/F004', 'source_solid_index': 1, 'source_face_index': 4, 'surface_type': 'plane', 'analytic_parameters': {'origin': [0.0, 0.0, 50.0], 'axis': [0.0, 0.0, -1.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S001/F005', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Down', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [-2.583791766400364e-16, -1.0, 1.2918958832001816e-16], 'centroid': [9.16666666666666, -39.0, -9.166666666666714], 'area_mm2': 1512.500000000001, 'triangle_count': 1, 'triangle_indices': [7], 'plane_offset_mm': 39.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'step_analytic_transformed', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S001/F005', 'source_face_id': 'S001/F005', 'source_solid_index': 1, 'source_face_index': 5, 'surface_type': 'plane', 'analytic_parameters': {'origin': [0.0, 0.0, 0.0], 'axis': [0.0, 0.0, -1.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S002/F001', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Front', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [-1.0, 1.821904450666924e-16, 1.291895883200182e-16], 'centroid': [-27.499999999999996, 1.8566862629069285e-15, -2.842170943040401e-14], 'area_mm2': 4290.0, 'triangle_count': 2, 'triangle_indices': [8, 9], 'plane_offset_mm': 27.499999999999996, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'step_analytic_transformed', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S002/F001', 'source_face_id': 'S002/F001', 'source_solid_index': 2, 'source_face_index': 6, 'surface_type': 'plane', 'analytic_parameters': {'origin': [50.00000000000001, 3.673940397442059e-15, 50.0], 'axis': [-7.347880794884117e-17, 1.0, 0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S002/F002', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Right', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [1.8829686875205503e-31, 7.287617802667694e-16, 1.0], 'centroid': [3.231395984773789e-15, 3.552713678800501e-15, 27.5], 'area_mm2': 4290.0, 'triangle_count': 2, 'triangle_indices': [10, 11], 'plane_offset_mm': 27.5, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'step_analytic_transformed', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S002/F002', 'source_face_id': 'S002/F002', 'source_solid_index': 2, 'source_face_index': 7, 'surface_type': 'plane', 'analytic_parameters': {'origin': [50.0, 50.0, 50.0], 'axis': [-1.0, -1.387778780781446e-16, 0.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S002/F004', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Up', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [2.583791766400364e-16, 1.0, -1.291895883200183e-16], 'centroid': [-9.166666666666659, 39.0, 9.1666666666666], 'area_mm2': 1512.4999999999993, 'triangle_count': 1, 'triangle_indices': [12], 'plane_offset_mm': 39.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'step_analytic_transformed', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S002/F004', 'source_face_id': 'S002/F004', 'source_solid_index': 2, 'source_face_index': 9, 'surface_type': 'plane', 'analytic_parameters': {'origin': [0.0, 0.0, 50.0], 'axis': [0.0, 0.0, 1.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}, {'face_id': 'S002/F005', 'role': 'Output', 'function': 'Transmit/Port', 'side_2d': 'Auto', 'port_role': 'Auto', 'fit_reference': 'Auto', 'normal': [-2.5837917664003647e-16, -1.0, 1.2918958832001818e-16], 'centroid': [-9.166666666666673, -39.0, 9.166666666666686], 'area_mm2': 1512.5000000000007, 'triangle_count': 1, 'triangle_indices': [13], 'plane_offset_mm': 39.0, 'flip_normal': False, 'material': '', 'coating': '', 'split_ratio': 0.5, 'loss': 0.0, 'phase_deg': 0.0, 'clear_aperture_mm': 0.0, 'input_offset_u_mm': 0.0, 'input_offset_v_mm': 0.0, 'suggested_side_2d': 'Auto', 'suggested_function': 'Unassigned', 'suggested_port_role': 'Auto', 'suggestion_confidence': 0.0, 'suggestion_reason': '', 'suggestion_source': '', 'assignment_source': 'step_analytic_transformed', 'notes': 'OpenCascade STEP analytic face', 'component_face_id': 'S002/F005', 'source_face_id': 'S002/F005', 'source_solid_index': 2, 'source_face_index': 10, 'surface_type': 'plane', 'analytic_parameters': {'origin': [0.0, 0.0, 0.0], 'axis': [0.0, 0.0, 1.0]}, 'interior_duplicate': False, 'duplicate_group': '', 'recovered_coating': False}], 'virtual_planes': [], 'source_step': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Beam_Splitter/32704/step_32704.step', 'source_backend': 'OpenCascade', 'source_face_count': 10, 'outer_face_count': 9, 'interior_duplicate_count': 2, 'promoted_face_metadata_source': 'open3d_step_overlay', 'metadata_coordinates': 'local_centered_promoted_row'}, 'OpticalSolidSourceFormat': 'STEP', 'OpticalSolidSourcePath': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Beam_Splitter/32704/step_32704.step', 'ScenePlacement': {'enabled': True, 'anchor': 'row_pose', 'snap_enabled': True, 'snap_mm': 3.9000000000000012, 'snap_deg': 5.0, 'grid_visible': True, 'grid_spacing_mm': 7.8000000000000025, 'grid_extent_mm': 156.00000000000006, 'promotion_source': 'open3d_step_overlay', 'promotion_step_label': 'optical', 'promotion_source_step_path': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Beam_Splitter/32704/step_32704.step', 'promotion_mesh_coordinates': 'local_centered_from_open3d_overlay', 'last_translate_axis': 'xyz', 'last_translate_delta_mm': [0.0, 0.0, 2.313561844855883], 'last_translate_step_mm': 2.313561844855883, 'last_translate_mode': 'free_drag'}, 'Solid_3d_stl': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/promoted_step_overlays/optical_aae83ad73a8d39d8.stl', 'StepOverlayPromotion': {'step_label': 'optical', 'source_step_path': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/prisms/Beam_Splitter/32704/step_32704.step', 'promoted_mesh_path': '/home/thinky/Projects/Kraken-Optical-Simulator/attachment/cad_cache/promoted_step_overlays/optical_aae83ad73a8d39d8.stl', 'mesh_coordinates': 'local_centered_from_open3d_overlay', 'center_world': [3.552713678800501e-15, -3.552713678800501e-15, 243.1708154643988], 'bounds_min_world': [-27.500000000000007, -39.000000000000014, 215.67081546439877], 'bounds_max_world': [27.500000000000014, 39.00000000000001, 270.6708154643988], 'row_thickness_mm': 55.00000000000003, 'axial_reserve_mm': 55.00000000000003, 'step_rotation_deg': [0.0, 270.0, 270.0], 'axis_offset_xy': [0.0, 0.0], 'placement_offset_xyz': [5.329070518200751e-15, 1.7763568394002505e-15, 204.17081546439877], 'largest_component_only': None, 'preserved_face_count': 9}}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 3.5527136788e-15, 'desp_y': -3.5527136788e-15, 'desp_z': 11.9, 'axis_move': 0.0, 'glass': 'BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s2 = Kos.surf()
    s2.Name = 'Promoted OPTICAL STEP optical solid -> next gap (AIR)'
    s2.Rc = 0.0
    s2.k = 0.0
    s2.Axicon = 0.0
    s2.Diff_Ord = 0.0
    s2.Grating_D = 0.0
    s2.Grating_Angle = 0.0
    s2.Thickness = 4.3291845356
    s2.Diameter = 78.0
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
    surfaces.append({'surface': 'Standard', 'element': 'OPTICAL STEP solid', 'name': 'Promoted OPTICAL STEP optical solid -> next gap (AIR)', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 4.3291845356, 'diameter': 78.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {'InPathTrailingSpacer': True}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s3 = Kos.surf()
    s3.Name = 'Lens Front Datum'
    s3.Rc = 0.0
    s3.k = 0.0
    s3.Axicon = 0.0
    s3.Diff_Ord = 0.0
    s3.Grating_D = 0.0
    s3.Grating_Angle = 0.0
    s3.Thickness = 1.45390219
    s3.Diameter = 35.0
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
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'Lens Front Datum', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 1.45390219, 'diameter': 35.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s4 = Kos.surf()
    s4.Name = 'Blackbox Group 1'
    s4.Rc = 258.76640629
    s4.k = 0.0
    s4.Axicon = 0.0
    s4.Diff_Ord = 0.0
    s4.Grating_D = 0.0
    s4.Grating_Angle = 0.0
    s4.Thickness = 24.405
    s4.Diameter = 26.8
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
    s4.Thin_Lens = 258.76640629
    s4.Rc = 0.0
    surfaces.append({'surface': 'Thin Lens', 'element': 'Blackbox Group 1', 'name': 'Blackbox Group 1', 'rc': 258.76640629, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 24.405, 'diameter': 26.8, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s5 = Kos.surf()
    s5.Name = 'Aperture Stop'
    s5.Rc = 0.0
    s5.k = 0.0
    s5.Axicon = 0.0
    s5.Diff_Ord = 0.0
    s5.Grating_D = 0.0
    s5.Grating_Angle = 0.0
    s5.Thickness = 21.64217312
    s5.Diameter = 19.35624
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
    surfaces.append({'surface': 'Aperture', 'element': 'Aperture Stop', 'name': 'Aperture Stop', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 21.64217312, 'diameter': 19.35624, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s6 = Kos.surf()
    s6.Name = 'Blackbox Group 2'
    s6.Rc = 293.3290133
    s6.k = 0.0
    s6.Axicon = 0.0
    s6.Diff_Ord = 0.0
    s6.Grating_D = 0.0
    s6.Grating_Angle = 0.0
    s6.Thickness = 1.308924688
    s6.Diameter = 26.8
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
    s6.Thin_Lens = 293.3290133
    s6.Rc = 0.0
    surfaces.append({'surface': 'Thin Lens', 'element': 'Blackbox Group 2', 'name': 'Blackbox Group 2', 'rc': 293.3290133, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 1.308924688, 'diameter': 26.8, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s7 = Kos.surf()
    s7.Name = 'Lens Rear Datum'
    s7.Rc = 0.0
    s7.k = 0.0
    s7.Axicon = 0.0
    s7.Diff_Ord = 0.0
    s7.Grating_D = 0.0
    s7.Grating_Angle = 0.0
    s7.Thickness = 290.739451477
    s7.Diameter = 35.0
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
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'Lens Rear Datum', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 290.739451477, 'diameter': 35.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s8 = Kos.surf()
    s8.Name = 'Image'
    s8.Rc = 0.0
    s8.k = 0.0
    s8.Axicon = 0.0
    s8.Diff_Ord = 0.0
    s8.Grating_D = 0.0
    s8.Grating_Angle = 0.0
    s8.Thickness = 0.0
    s8.Diameter = 18.1019335984
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
    surfaces.append({'surface': 'Image', 'element': '', 'name': 'Image', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 0.0, 'diameter': 18.1019335984, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

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

