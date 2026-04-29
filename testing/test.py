#!/usr/bin/env python3
TITLE = "Test"

SETTINGS = {'object_mode': 'Infinity',
 'display_orientation': 'Vertical',
 'wavelength': '0.5876',
 'ray_count': '21',
 'ray_height_factor': '0.8',
 'full_pupil': False,
 'analysis_surface': 'Auto',
 'aperture_type': 'EPD',
 'aperture_value': '33.33',
 'spot_view_mode': 'Grid',
 'show_clipped_rays': True,
 'show_cardinals': True,
 'show_physical_distances': False,
 'field_type': 'Angle',
 'field_value': '14',
 'field_count': '3',
 'image_diameter_mode': 'Auto',
 'trace_mode': 'Auto',
 'camera_model': 'None',
 'camera_step_path': '',
 'camera_step_rotation_x_deg': 0.0,
 'camera_step_rotation_z_deg': 0.0,
 'camera_step_axis_offset_xy': [0.0, 0.0],
 'lens_step_path': '',
 'lens_step_rotation_x_deg': 0.0,
 'lens_step_rotation_z_deg': 0.0,
 'lens_step_axis_offset_xy': [0.0, 0.0],
 'led_step_path': '',
 'led_step_rotation_x_deg': 0.0,
 'led_step_rotation_z_deg': 0.0,
 'led_object_edge_distance_mm': 0.0,
 'led_step_object_edge_local_z': '',
 'led_step_axis_offset_xy': [0.0, 0.0],
 'analysis_mode': 'none',
 'analysis_modes': [],
 'layout_preview_mode': 'none',
 'auto_save_plot': False,
 'external_camera': 'None',
 'camera_overlay_mode': 'Off',
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
              'Thickness penalty': {'weight': '1',
                                    'target': '0.1',
                                    'wavelength': '0.55',
                                    'field': '0',
                                    'surface': 'Auto'},
              'MTF @ freq': {'weight': '1',
                             'target': '0.5',
                             'wavelength': '0.5876',
                             'field': '0',
                             'field_x': '0',
                             'field_y': '0',
                             'surface': 'Auto',
                             'frequency': '50',
                             'mtf_mode': 'Average',
                             'mtf_algorithm': 'Diffraction FFT'},
              'Entrance pupil z': {'weight': '1',
                                   'target': '0',
                                   'wavelength': '0.55',
                                   'field': '0',
                                   'surface': 'Auto'},
              'Exit pupil z': {'weight': '1',
                               'target': '0',
                               'wavelength': '0.55',
                               'field': '0',
                               'surface': 'Auto'},
              'Spot RMS': {'weight': '1',
                           'target': '0',
                           'wavelength': '0.5876',
                           'field': '0',
                           'surface': 'Auto'},
              'Magnification': {'weight': '1',
                                'target': '1',
                                'wavelength': '0.55',
                                'field': '0',
                                'surface': 'Auto'}}}

import KrakenOS as Kos
import numpy as np


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
    s0.Thickness = 100.0
    s0.Diameter = 58.4505955402
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
    surfaces.append({'surface': 'Object', 'name': 'Object', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 100.0, 'diameter': 58.4505955402, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s1 = Kos.surf()
    s1.Name = 'S01 SK2'
    s1.Rc = 54.1532461657
    s1.k = 0.0
    s1.Axicon = 0.0
    s1.Diff_Ord = 0.0
    s1.Grating_D = 0.0
    s1.Grating_Angle = 0.0
    s1.Thickness = 8.74665785
    s1.Diameter = 58.4505955402
    s1.InDiameter = 0.0
    s1.Drawing = 1.0
    s1.TiltX = 0.0
    s1.TiltY = 0.0
    s1.TiltZ = 0.0
    s1.DespX = 0.0
    s1.DespY = 0.0
    s1.DespZ = 0.0
    s1.AxisMove = 0.0
    s1.Glass = 'SK2'
    surfaces.append({'surface': 'Standard', 'name': 'S01 SK2', 'rc': 54.1532461657, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 8.74665785, 'diameter': 58.4505955402, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'SK2', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s2 = Kos.surf()
    s2.Name = 'S02 Air Gap'
    s2.Rc = 152.52192094
    s2.k = 0.0
    s2.Axicon = 0.0
    s2.Diff_Ord = 0.0
    s2.Grating_D = 0.0
    s2.Grating_Angle = 0.0
    s2.Thickness = 0.5
    s2.Diameter = 56.2819080613
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
    surfaces.append({'surface': 'Standard', 'name': 'S02 Air Gap', 'rc': 152.52192094, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 0.5, 'diameter': 56.2819080613, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s3 = Kos.surf()
    s3.Name = 'S03 SK16'
    s3.Rc = 35.9506244505
    s3.k = 0.0
    s3.Axicon = 0.0
    s3.Diff_Ord = 0.0
    s3.Grating_D = 0.0
    s3.Grating_Angle = 0.0
    s3.Thickness = 14.0
    s3.Diameter = 48.5916248775
    s3.InDiameter = 0.0
    s3.Drawing = 1.0
    s3.TiltX = 0.0
    s3.TiltY = 0.0
    s3.TiltZ = 0.0
    s3.DespX = 0.0
    s3.DespY = 0.0
    s3.DespZ = 0.0
    s3.AxisMove = 0.0
    s3.Glass = 'SK16'
    surfaces.append({'surface': 'Standard', 'name': 'S03 SK16', 'rc': 35.9506244505, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 14.0, 'diameter': 48.5916248775, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'SK16', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s4 = Kos.surf()
    s4.Name = 'S04 F5'
    s4.Rc = 0.0
    s4.k = 0.0
    s4.Axicon = 0.0
    s4.Diff_Ord = 0.0
    s4.Grating_D = 0.0
    s4.Grating_Angle = 0.0
    s4.Thickness = 3.77696589
    s4.Diameter = 42.594381847
    s4.InDiameter = 0.0
    s4.Drawing = 1.0
    s4.TiltX = 0.0
    s4.TiltY = 0.0
    s4.TiltZ = 0.0
    s4.DespX = 0.0
    s4.DespY = 0.0
    s4.DespZ = 0.0
    s4.AxisMove = 0.0
    s4.Glass = 'F5'
    surfaces.append({'surface': 'Standard', 'name': 'S04 F5', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 3.77696589, 'diameter': 42.594381847, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'F5', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s5 = Kos.surf()
    s5.Name = 'S05 Air Gap'
    s5.Rc = 22.269924618
    s5.k = 0.0
    s5.Axicon = 0.0
    s5.Diff_Ord = 0.0
    s5.Grating_D = 0.0
    s5.Grating_Angle = 0.0
    s5.Thickness = 14.2530593
    s5.Diameter = 29.8387051251
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
    surfaces.append({'surface': 'Standard', 'name': 'S05 Air Gap', 'rc': 22.269924618, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 14.2530593, 'diameter': 29.8387051251, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s6 = Kos.surf()
    s6.Name = 'Aperture'
    s6.Rc = 0.0
    s6.k = 0.0
    s6.Axicon = 0.0
    s6.Diff_Ord = 0.0
    s6.Grating_D = 0.0
    s6.Grating_Angle = 0.0
    s6.Thickness = 12.4281291
    s6.Diameter = 20.457670382
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
    surfaces.append({'surface': 'Aperture', 'name': 'Aperture', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 12.4281291, 'diameter': 20.457670382, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s7 = Kos.surf()
    s7.Name = 'S07 F5'
    s7.Rc = -25.6850330305
    s7.k = 0.0
    s7.Axicon = 0.0
    s7.Diff_Ord = 0.0
    s7.Grating_D = 0.0
    s7.Grating_Angle = 0.0
    s7.Thickness = 3.77696589
    s7.Diameter = 26.3755169712
    s7.InDiameter = 0.0
    s7.Drawing = 1.0
    s7.TiltX = 0.0
    s7.TiltY = 0.0
    s7.TiltZ = 0.0
    s7.DespX = 0.0
    s7.DespY = 0.0
    s7.DespZ = 0.0
    s7.AxisMove = 0.0
    s7.Glass = 'F5'
    surfaces.append({'surface': 'Standard', 'name': 'S07 F5', 'rc': -25.6850330305, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 3.77696589, 'diameter': 26.3755169712, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'F5', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s8 = Kos.surf()
    s8.Name = 'S08 SK16'
    s8.Rc = 0.0
    s8.k = 0.0
    s8.Axicon = 0.0
    s8.Diff_Ord = 0.0
    s8.Grating_D = 0.0
    s8.Grating_Angle = 0.0
    s8.Thickness = 10.8339285
    s8.Diameter = 32.9362447902
    s8.InDiameter = 0.0
    s8.Drawing = 1.0
    s8.TiltX = 0.0
    s8.TiltY = 0.0
    s8.TiltZ = 0.0
    s8.DespX = 0.0
    s8.DespY = 0.0
    s8.DespZ = 0.0
    s8.AxisMove = 0.0
    s8.Glass = 'SK16'
    surfaces.append({'surface': 'Standard', 'name': 'S08 SK16', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 10.8339285, 'diameter': 32.9362447902, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'SK16', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s9 = Kos.surf()
    s9.Name = 'S09 Air Gap'
    s9.Rc = -36.9802207286
    s9.k = 0.0
    s9.Axicon = 0.0
    s9.Diff_Ord = 0.0
    s9.Grating_D = 0.0
    s9.Grating_Angle = 0.0
    s9.Thickness = 0.5
    s9.Diameter = 37.8591350584
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
    surfaces.append({'surface': 'Standard', 'name': 'S09 Air Gap', 'rc': -36.9802207286, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 0.5, 'diameter': 37.8591350584, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s10 = Kos.surf()
    s10.Name = 'S10 SK16'
    s10.Rc = 196.417334097
    s10.k = 0.0
    s10.Axicon = 0.0
    s10.Diff_Ord = 0.0
    s10.Grating_D = 0.0
    s10.Grating_Angle = 0.0
    s10.Thickness = 6.85817491
    s10.Diameter = 42.6215294331
    s10.InDiameter = 0.0
    s10.Drawing = 1.0
    s10.TiltX = 0.0
    s10.TiltY = 0.0
    s10.TiltZ = 0.0
    s10.DespX = 0.0
    s10.DespY = 0.0
    s10.DespZ = 0.0
    s10.AxisMove = 0.0
    s10.Glass = 'SK16'
    surfaces.append({'surface': 'Standard', 'name': 'S10 SK16', 'rc': 196.417334097, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 6.85817491, 'diameter': 42.6215294331, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'SK16', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s11 = Kos.surf()
    s11.Name = 'S11 Air Gap'
    s11.Rc = -67.1475500237
    s11.k = 0.0
    s11.Axicon = 0.0
    s11.Diff_Ord = 0.0
    s11.Grating_D = 0.0
    s11.Grating_Angle = 0.0
    s11.Thickness = 57.314537905
    s11.Diameter = 43.2925168654
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
    surfaces.append({'surface': 'Standard', 'name': 'S11 Air Gap', 'rc': -67.1475500237, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 57.314537905, 'diameter': 43.2925168654, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s12 = Kos.surf()
    s12.Name = 'Image'
    s12.Rc = 0.0
    s12.k = 0.0
    s12.Axicon = 0.0
    s12.Diff_Ord = 0.0
    s12.Grating_D = 0.0
    s12.Grating_Angle = 0.0
    s12.Thickness = 0.0
    s12.Diameter = 49.6165693213
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
    surfaces.append({'surface': 'Image', 'name': 'Image', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 0.0, 'diameter': 49.6165693213, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'advanced': {}, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

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
        s.Diameter = clear_aperture if spec['surface'] in {'Object', 'Image'} else spec['diameter']
        s.InDiameter = spec.get('in_diameter', spec.get('InDiameter', 0.0))
        s.Drawing = spec.get('drawing', spec.get('Drawing', 1.0))
        if 'ExtraData' in spec or 'extra_data' in spec:
            s.ExtraData = spec.get('extra_data', spec.get('ExtraData', s.ExtraData))
        if 'UDA' in spec or 'uda' in spec:
            s.UDA = spec.get('uda', spec.get('UDA', s.UDA))
        for attr, value in spec.get('advanced', {}).items():
            if attr in {'AspherData', 'ZNK'}:
                value = np.asarray(value, dtype=float).ravel()
                min_len = 200 if attr == 'AspherData' else 36
                if value.size < min_len:
                    value = np.pad(value, (0, min_len - value.size), mode='constant')
            setattr(s, attr, value)
        s.TiltX = spec.get('tilt_x', 0.0)
        s.TiltY = spec.get('tilt_y', 0.0)
        s.TiltZ = spec.get('tilt_z', 0.0)
        s.DespX = spec.get('desp_x', 0.0)
        s.DespY = spec.get('desp_y', 0.0)
        s.DespZ = spec.get('desp_z', 0.0)
        s.AxisMove = spec.get('axis_move', 0.0)
        s.Glass = spec['glass']
        if spec['surface'] == 'Mirror':
            s.Glass = 'MIRROR'
            if abs(s.AxisMove) < 1e-9:
                s.AxisMove = 2.0
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
    return Kos.system(runtime_surfaces, setup)


def build_rays(system):
    rays = Kos.raykeeper(system)
    optical_diams = [float(s.Diameter) for s in system.SDT[1:-1]] or [float(s.Diameter) for s in system.SDT]
    max_radius = max(optical_diams, default=2.0) / 2.0
    ray_heights = [(-0.8 * max_radius), (-max_radius / 3.0), 0.0, (max_radius / 3.0), (0.8 * max_radius)]
    for y0 in ray_heights:
        system.Trace([0.0, y0, 0.0], [0.0, 0.0, 1.0], 0.55)
        rays.push()
    return rays


if __name__ == '__main__':
    system = build_runtime_system()
    rays = build_rays(system)
    Kos.display2d(system, rays, 0)

