#!/usr/bin/env python3
TITLE = "Test"

SETTINGS = {'object_mode': 'Infinity',
 'display_orientation': 'Vertical',
 'wavelength': '0.4',
 'ray_count': '21',
 'ray_height_factor': '0.8',
 'full_pupil': True,
 'analysis_surface': 'Auto',
 'aperture_type': 'EPD',
 'aperture_value': '33.33',
 'spot_view_mode': 'Grid',
 'show_clipped_rays': True,
 'show_cardinals': True,
 'show_physical_distances': False,
 'field_type': 'Object Height',
 'field_value': '0.0',
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
 'operands': {'MTF @ freq': {'weight': '1',
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
              'EFFL': {'weight': '1',
                       'target': '100',
                       'wavelength': '0.55',
                       'field': '0',
                       'surface': 'Auto'},
              'Exit pupil z': {'weight': '1',
                               'target': '0',
                               'wavelength': '0.55',
                               'field': '0',
                               'surface': 'Auto'},
              'Magnification': {'weight': '1',
                                'target': '1',
                                'wavelength': '0.55',
                                'field': '0',
                                'surface': 'Auto'},
              'Thickness penalty': {'weight': '1',
                                    'target': '0.1',
                                    'wavelength': '0.55',
                                    'field': '0',
                                    'surface': 'Auto'},
              'Spot RMS': {'weight': '1',
                           'target': '0',
                           'wavelength': '0.5876',
                           'field': '0',
                           'surface': 'Auto'},
              'Wavefront RMS': {'weight': '1',
                                'target': '0',
                                'wavelength': '0.55',
                                'field': '0',
                                'surface': 'Auto'}}}

import KrakenOS as Kos


def build_system():
    surfaces = []
    s0 = Kos.surf()
    s0.Name = 'Surface 0'
    s0.Rc = 0.0
    s0.k = 0.0
    s0.Axicon = 0.0
    s0.Diff_Ord = 0.0
    s0.Grating_D = 0.0
    s0.Grating_Angle = 0.0
    s0.Thickness = 10.0
    s0.Diameter = 30.0
    s0.InDiameter = 0.0
    s0.Drawing = 1.0
    s0.TiltX = 0.0
    s0.TiltY = 0.0
    s0.TiltZ = 0.0
    s0.DespX = 0.0
    s0.DespY = 0.0
    s0.DespZ = 0.0
    s0.AxisMove = 1.0
    s0.Glass = 'AIR'
    surfaces.append({'surface': 'Object', 'name': 'Surface 0', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 10.0, 'diameter': 30.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 1.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s1 = Kos.surf()
    s1.Name = 'Surface 1'
    s1.Rc = 0.0
    s1.k = 0.0
    s1.Axicon = 0.0
    s1.Diff_Ord = 0.0
    s1.Grating_D = 0.0
    s1.Grating_Angle = 0.0
    s1.Thickness = 26.0
    s1.Diameter = 30.0
    s1.InDiameter = 0.0
    s1.Drawing = 1.0
    s1.TiltX = 0.0
    s1.TiltY = 0.0
    s1.TiltZ = 0.0
    s1.DespX = 0.0
    s1.DespY = 0.0
    s1.DespZ = 0.0
    s1.AxisMove = 1.0
    s1.Glass = 'BK7'
    surfaces.append({'surface': 'Standard', 'name': 'Surface 1', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 26.0, 'diameter': 30.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 1.0, 'glass': 'BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s2 = Kos.surf()
    s2.Name = 'Surface 2'
    s2.Rc = 0.0
    s2.k = 0.0
    s2.Axicon = -35.0
    s2.Diff_Ord = 0.0
    s2.Grating_D = 0.0
    s2.Grating_Angle = 0.0
    s2.Thickness = 97.3760474291
    s2.Diameter = 30.0
    s2.InDiameter = 0.0
    s2.Drawing = 1.0
    s2.TiltX = 0.0
    s2.TiltY = 0.0
    s2.TiltZ = 0.0
    s2.DespX = 0.0
    s2.DespY = 0.0
    s2.DespZ = 0.0
    s2.AxisMove = 1.0
    s2.Glass = 'AIR'
    surfaces.append({'surface': 'Standard', 'name': 'Surface 2', 'rc': 0.0, 'k': 0.0, 'axicon': -35.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 97.3760474291, 'diameter': 30.0, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 1.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s3 = Kos.surf()
    s3.Name = 'Plano imagen'
    s3.Rc = 0.0
    s3.k = 0.0
    s3.Axicon = 0.0
    s3.Diff_Ord = 0.0
    s3.Grating_D = 0.0
    s3.Grating_Angle = 0.0
    s3.Thickness = 0.0
    s3.Diameter = 46.1063357428
    s3.InDiameter = 0.0
    s3.Drawing = 1.0
    s3.TiltX = 0.0
    s3.TiltY = 0.0
    s3.TiltZ = 0.0
    s3.DespX = 0.0
    s3.DespY = 0.0
    s3.DespZ = 0.0
    s3.AxisMove = 1.0
    s3.Glass = 'AIR'
    surfaces.append({'surface': 'Image', 'name': 'Plano imagen', 'rc': 0.0, 'k': 0.0, 'axicon': 0.0, 'diff_ord': 0.0, 'grating_d': 0.0, 'grating_angle': 0.0, 'thickness': 0.0, 'diameter': 46.1063357428, 'in_diameter': 0.0, 'drawing': 1.0, 'extra_data': 0.0, 'uda': 'None', 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 1.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

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

