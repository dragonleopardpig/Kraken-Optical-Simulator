#!/usr/bin/env python3
TITLE = "Analytic Telescope Chain"

SETTINGS = {'object_mode': 'Infinity',
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
 'aperture_type': 'EPD',
 'aperture_value': '4.0',
 'spot_view_mode': 'Grid',
 'wavefront_style': 'Wavefront Function',
 'tolerance_compare_view': 'Spot overlay',
 'show_clipped_rays': True,
 'show_path_labels': True,
 'show_cardinals': True,
 'show_physical_distances': False,
 'field_type': 'Angle',
 'field_value': '0.0',
 'field_count': '1',
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
 'image_diameter_mode': 'Auto',
 'trace_mode': 'Auto',
 'folded_detector_policy': 'Trace events',
 'nonseq_target_surface': 'Auto',
 'nonseq_ns_limit': '200',
 'nonseq_energy_probability': False,
 'camera_model': 'None',
 'camera_step_path': '',
 'camera_step_rotation_x_deg': 0.0,
 'camera_step_rotation_y_deg': 0.0,
 'camera_step_rotation_z_deg': 0.0,
 'camera_step_axis_offset_xy': [0.0, 0.0],
 'camera_step_placement_offset_xyz': [0.0, 0.0, 0.0],
 'lens_step_path': '',
 'lens_step_largest_component_only': True,
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
 'led_step_path': '',
 'led_step_rotation_x_deg': 0.0,
 'led_step_rotation_y_deg': 0.0,
 'led_step_rotation_z_deg': 0.0,
 'led_object_edge_distance_mm': 0.0,
 'led_step_object_edge_local_z': '',
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
              'Wavefront RMS': {'weight': '1',
                                'target': '0',
                                'wavelength': '0.55',
                                'field': '0',
                                'surface': 'Auto'},
              'Thickness penalty': {'weight': '1',
                                    'target': '0.1',
                                    'wavelength': '0.55',
                                    'field': '0',
                                    'surface': 'Auto'},
              'EFFL': {'weight': '1',
                       'target': '100',
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
              'Exit pupil z': {'weight': '1',
                               'target': '0',
                               'wavelength': '0.55',
                               'field': '0',
                               'surface': 'Auto'},
              'Spot RMS': {'weight': '1',
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
    s0.Thickness = 0.0
    s0.Diameter = 20.0
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
    surfaces.append({'surface': 'Object', 'element': '', 'name': 'Object', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 0.0, 'diameter': 20.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s1 = Kos.surf()
    s1.Name = 'object_gap'
    s1.Rc = 0.0
    s1.k = 0.0
    s1.Axicon = 0.0
    s1.Diff_Ord = 0.0
    s1.Grating_D = 0.0
    s1.Grating_Angle = 0.0
    s1.Thickness = 50.0
    s1.Diameter = 20.0
    s1.InDiameter = 0.0
    s1.Drawing = 1.0
    s1.TiltX = 0.0
    s1.TiltY = 0.0
    s1.TiltZ = 0.0
    s1.DespX = 0.0
    s1.DespY = 0.0
    s1.DespZ = 0.0
    s1.AxisMove = 0.0
    s1.Glass = 'AIR'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'object_gap', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 50.0, 'diameter': 20.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s2 = Kos.surf()
    s2.Name = 'ball_lens_1_front'
    s2.Rc = 4.7625
    s2.k = 0.0
    s2.Axicon = 0.0
    s2.Diff_Ord = 0.0
    s2.Grating_D = 0.0
    s2.Grating_Angle = 0.0
    s2.Thickness = 9.525
    s2.Diameter = 10.0
    s2.InDiameter = 0.0
    s2.Drawing = 1.0
    s2.TiltX = 0.0
    s2.TiltY = 0.0
    s2.TiltZ = 0.0
    s2.DespX = 0.0
    s2.DespY = 0.0
    s2.DespZ = 0.0
    s2.AxisMove = 0.0
    s2.Glass = 'AL2O3'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'ball_lens_1_front', 'rc': 4.7625, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 9.525, 'diameter': 10.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AL2O3', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s3 = Kos.surf()
    s3.Name = 'ball_lens_1_back'
    s3.Rc = -4.7625
    s3.k = 0.0
    s3.Axicon = 0.0
    s3.Diff_Ord = 0.0
    s3.Grating_D = 0.0
    s3.Grating_Angle = 0.0
    s3.Thickness = 1.435
    s3.Diameter = 10.0
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
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'ball_lens_1_back', 'rc': -4.7625, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 1.435, 'diameter': 10.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s4 = Kos.surf()
    s4.Name = 'ball_lens_2_front'
    s4.Rc = 4.7625
    s4.k = 0.0
    s4.Axicon = 0.0
    s4.Diff_Ord = 0.0
    s4.Grating_D = 0.0
    s4.Grating_Angle = 0.0
    s4.Thickness = 9.525
    s4.Diameter = 10.0
    s4.InDiameter = 0.0
    s4.Drawing = 1.0
    s4.TiltX = 0.0
    s4.TiltY = 0.0
    s4.TiltZ = 0.0
    s4.DespX = 0.0
    s4.DespY = 0.0
    s4.DespZ = 0.0
    s4.AxisMove = 0.0
    s4.Glass = 'AL2O3'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'ball_lens_2_front', 'rc': 4.7625, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 9.525, 'diameter': 10.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AL2O3', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s5 = Kos.surf()
    s5.Name = 'ball_lens_2_back'
    s5.Rc = -4.7625
    s5.k = 0.0
    s5.Axicon = 0.0
    s5.Diff_Ord = 0.0
    s5.Grating_D = 0.0
    s5.Grating_Angle = 0.0
    s5.Thickness = 50.0
    s5.Diameter = 10.0
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
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'ball_lens_2_back', 'rc': -4.7625, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 50.0, 'diameter': 10.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s6 = Kos.surf()
    s6.Name = 'dcv_front'
    s6.Rc = -52.1
    s6.k = 0.0
    s6.Axicon = 0.0
    s6.Diff_Ord = 0.0
    s6.Grating_D = 0.0
    s6.Grating_Angle = 0.0
    s6.Thickness = 2.5
    s6.Diameter = 12.0
    s6.InDiameter = 0.0
    s6.Drawing = 1.0
    s6.TiltX = 0.0
    s6.TiltY = 0.0
    s6.TiltZ = 0.0
    s6.DespX = 0.0
    s6.DespY = 0.0
    s6.DespZ = 0.0
    s6.AxisMove = 0.0
    s6.Glass = 'N-BK7'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'dcv_front', 'rc': -52.1, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 2.5, 'diameter': 12.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'N-BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s7 = Kos.surf()
    s7.Name = 'dcv_back'
    s7.Rc = 52.1
    s7.k = 0.0
    s7.Axicon = 0.0
    s7.Diff_Ord = 0.0
    s7.Grating_D = 0.0
    s7.Grating_Angle = 0.0
    s7.Thickness = 100.0
    s7.Diameter = 12.0
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
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'dcv_back', 'rc': 52.1, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 100.0, 'diameter': 12.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s8 = Kos.surf()
    s8.Name = 'achromat_s1'
    s8.Rc = 34.53
    s8.k = 0.0
    s8.Axicon = 0.0
    s8.Diff_Ord = 0.0
    s8.Grating_D = 0.0
    s8.Grating_Angle = 0.0
    s8.Thickness = 9.0
    s8.Diameter = 12.0
    s8.InDiameter = 0.0
    s8.Drawing = 1.0
    s8.TiltX = 0.0
    s8.TiltY = 0.0
    s8.TiltZ = 0.0
    s8.DespX = 0.0
    s8.DespY = 0.0
    s8.DespZ = 0.0
    s8.AxisMove = 0.0
    s8.Glass = 'N-BAF10'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'achromat_s1', 'rc': 34.53, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 9.0, 'diameter': 12.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'N-BAF10', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s9 = Kos.surf()
    s9.Name = 'achromat_s2'
    s9.Rc = -21.98
    s9.k = 0.0
    s9.Axicon = 0.0
    s9.Diff_Ord = 0.0
    s9.Grating_D = 0.0
    s9.Grating_Angle = 0.0
    s9.Thickness = 2.5
    s9.Diameter = 12.0
    s9.InDiameter = 0.0
    s9.Drawing = 1.0
    s9.TiltX = 0.0
    s9.TiltY = 0.0
    s9.TiltZ = 0.0
    s9.DespX = 0.0
    s9.DespY = 0.0
    s9.DespZ = 0.0
    s9.AxisMove = 0.0
    s9.Glass = 'N-SF10'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'achromat_s2', 'rc': -21.98, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 2.5, 'diameter': 12.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'N-SF10', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s10 = Kos.surf()
    s10.Name = 'achromat_s3'
    s10.Rc = -214.63
    s10.k = 0.0
    s10.Axicon = 0.0
    s10.Diff_Ord = 0.0
    s10.Grating_D = 0.0
    s10.Grating_Angle = 0.0
    s10.Thickness = 100.0
    s10.Diameter = 12.0
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
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'achromat_s3', 'rc': -214.63, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 100.0, 'diameter': 12.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s11 = Kos.surf()
    s11.Name = 'cyl_front'
    s11.Rc = 25.84
    s11.k = 0.0
    s11.Axicon = 0.0
    s11.Diff_Ord = 0.0
    s11.Grating_D = 0.0
    s11.Grating_Angle = 0.0
    s11.Thickness = 4.34
    s11.Diameter = 25.4
    s11.InDiameter = 0.0
    s11.Drawing = 1.0
    s11.TiltX = 0.0
    s11.TiltY = 0.0
    s11.TiltZ = 0.0
    s11.DespX = 0.0
    s11.DespY = 0.0
    s11.DespZ = 0.0
    s11.AxisMove = 0.0
    s11.Glass = 'N-BK7'
    s11.CylindricalAxisHint = 'y'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'cyl_front', 'rc': 25.84, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 4.34, 'diameter': 25.4, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {'CylindricalAxisHint': 'y'}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'N-BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s12 = Kos.surf()
    s12.Name = 'cyl_back'
    s12.Rc = 0.0
    s12.k = 0.0
    s12.Axicon = 0.0
    s12.Diff_Ord = 0.0
    s12.Grating_D = 0.0
    s12.Grating_Angle = 0.0
    s12.Thickness = 50.0
    s12.Diameter = 25.4
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
    s12.CylindricalAxisHint = 'y'
    surfaces.append({'surface': 'Standard', 'element': '', 'name': 'cyl_back', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 50.0, 'diameter': 25.4, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {'CylindricalAxisHint': 'y'}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s13 = Kos.surf()
    s13.Name = 'Image'
    s13.Rc = 0.0
    s13.k = 0.0
    s13.Axicon = 0.0
    s13.Diff_Ord = 0.0
    s13.Grating_D = 0.0
    s13.Grating_Angle = 0.0
    s13.Thickness = 0.0
    s13.Diameter = 2.98562324002
    s13.InDiameter = 0.0
    s13.Drawing = 1.0
    s13.TiltX = 0.0
    s13.TiltY = 0.0
    s13.TiltZ = 0.0
    s13.DespX = 0.0
    s13.DespY = 0.0
    s13.DespZ = 0.0
    s13.AxisMove = 0.0
    s13.Glass = 'AIR'
    surfaces.append({'surface': 'Image', 'element': '', 'name': 'Image', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 0.0, 'diameter': 2.98562324002, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

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

