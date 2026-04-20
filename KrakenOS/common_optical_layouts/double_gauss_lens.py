#!/usr/bin/env python3
TITLE = "Double Gauss Lens"

SETTINGS = {'object_mode': 'Finite',
 'display_orientation': 'Vertical',
 'wavelength': '0.55',
 'ray_count': '31',
 'ray_height_factor': '0.8',
 'analysis_surface': 'Auto',
 'aperture_type': 'EPD',
 'aperture_value': '4.0',
 'spot_view_mode': 'Grid',
 'show_clipped_rays': True,
 'show_cardinals': True,
 'show_physical_distances': False,
 'field_type': 'Object Height',
 'field_value': '0.0',
 'field_count': '1',
 'image_diameter_mode': 'Auto',
 'analysis_mode': 'none',
 'analysis_modes': [],
 'layout_preview_mode': 'none',
 'auto_save_plot': False,
 'external_camera': 'None',
 'camera_overlay_mode': 'Off',
 'optimization_workers': 'Auto',
 'selected_operands': ['Spot RMS'],
 'operands': {'Wavefront RMS': {'weight': '1',
                                'target': '0',
                                'wavelength': '0.55',
                                'field': '0',
                                'surface': 'Auto'},
              'Magnification': {'weight': '1',
                                'target': '1',
                                'wavelength': '0.55',
                                'field': '0',
                                'surface': 'Auto'},
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
                             'mtf_algorithm': 'PSF FFT'},
              'Exit pupil z': {'weight': '1',
                               'target': '0',
                               'wavelength': '0.55',
                               'field': '0',
                               'surface': 'Auto'},
              'Spot RMS': {'weight': '1',
                           'target': '0',
                           'wavelength': '0.55',
                           'field': '0',
                           'surface': 'Auto'}}}

import KrakenOS as Kos


def build_system():
    surfaces = []
    s0 = Kos.surf()
    s0.Name = 'Object'
    s0.Rc = 0.0
    s0.Thickness = 90.0
    s0.Diameter = 25.0
    s0.TiltX = 0.0
    s0.TiltY = 0.0
    s0.TiltZ = 0.0
    s0.DespX = 0.0
    s0.DespY = 0.0
    s0.DespZ = 0.0
    s0.AxisMove = 0.0
    s0.Glass = 'AIR'
    surfaces.append({'surface': 'Object', 'name': 'Object', 'rc': 0.0, 'thickness': 90.0, 'diameter': 25.0, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s1 = Kos.surf()
    s1.Name = 'Front Crown Front'
    s1.Rc = -55.0
    s1.Thickness = 7.0
    s1.Diameter = 34.0
    s1.TiltX = 0.0
    s1.TiltY = 0.0
    s1.TiltZ = 0.0
    s1.DespX = 0.0
    s1.DespY = 0.0
    s1.DespZ = 0.0
    s1.AxisMove = 0.0
    s1.Glass = 'BK7'
    surfaces.append({'surface': 'Standard', 'name': 'Front Crown Front', 'rc': -55.0, 'thickness': 7.0, 'diameter': 34.0, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s2 = Kos.surf()
    s2.Name = 'Front Crown Back'
    s2.Rc = 90.0
    s2.Thickness = 4.0
    s2.Diameter = 32.0
    s2.TiltX = 0.0
    s2.TiltY = 0.0
    s2.TiltZ = 0.0
    s2.DespX = 0.0
    s2.DespY = 0.0
    s2.DespZ = 0.0
    s2.AxisMove = 0.0
    s2.Glass = 'AIR'
    surfaces.append({'surface': 'Standard', 'name': 'Front Crown Back', 'rc': 90.0, 'thickness': 4.0, 'diameter': 32.0, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s3 = Kos.surf()
    s3.Name = 'Front Flint Front'
    s3.Rc = 38.0
    s3.Thickness = 5.0
    s3.Diameter = 28.0
    s3.TiltX = 0.0
    s3.TiltY = 0.0
    s3.TiltZ = 0.0
    s3.DespX = 0.0
    s3.DespY = 0.0
    s3.DespZ = 0.0
    s3.AxisMove = 0.0
    s3.Glass = 'F2'
    surfaces.append({'surface': 'Standard', 'name': 'Front Flint Front', 'rc': 38.0, 'thickness': 5.0, 'diameter': 28.0, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'F2', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s4 = Kos.surf()
    s4.Name = 'Front Flint Back'
    s4.Rc = -70.0
    s4.Thickness = 18.0
    s4.Diameter = 26.0
    s4.TiltX = 0.0
    s4.TiltY = 0.0
    s4.TiltZ = 0.0
    s4.DespX = 0.0
    s4.DespY = 0.0
    s4.DespZ = 0.0
    s4.AxisMove = 0.0
    s4.Glass = 'AIR'
    surfaces.append({'surface': 'Standard', 'name': 'Front Flint Back', 'rc': -70.0, 'thickness': 18.0, 'diameter': 26.0, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s5 = Kos.surf()
    s5.Name = 'Rear Flint Front'
    s5.Rc = 70.0
    s5.Thickness = 5.0
    s5.Diameter = 26.0
    s5.TiltX = 0.0
    s5.TiltY = 0.0
    s5.TiltZ = 0.0
    s5.DespX = 0.0
    s5.DespY = 0.0
    s5.DespZ = 0.0
    s5.AxisMove = 0.0
    s5.Glass = 'F2'
    surfaces.append({'surface': 'Standard', 'name': 'Rear Flint Front', 'rc': 70.0, 'thickness': 5.0, 'diameter': 26.0, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'F2', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s6 = Kos.surf()
    s6.Name = 'Rear Flint Back'
    s6.Rc = -38.0
    s6.Thickness = 4.0
    s6.Diameter = 28.0
    s6.TiltX = 0.0
    s6.TiltY = 0.0
    s6.TiltZ = 0.0
    s6.DespX = 0.0
    s6.DespY = 0.0
    s6.DespZ = 0.0
    s6.AxisMove = 0.0
    s6.Glass = 'AIR'
    surfaces.append({'surface': 'Standard', 'name': 'Rear Flint Back', 'rc': -38.0, 'thickness': 4.0, 'diameter': 28.0, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s7 = Kos.surf()
    s7.Name = 'Rear Crown Front'
    s7.Rc = -90.0
    s7.Thickness = 7.0
    s7.Diameter = 32.0
    s7.TiltX = 0.0
    s7.TiltY = 0.0
    s7.TiltZ = 0.0
    s7.DespX = 0.0
    s7.DespY = 0.0
    s7.DespZ = 0.0
    s7.AxisMove = 0.0
    s7.Glass = 'BK7'
    surfaces.append({'surface': 'Standard', 'name': 'Rear Crown Front', 'rc': -90.0, 'thickness': 7.0, 'diameter': 32.0, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'BK7', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s8 = Kos.surf()
    s8.Name = 'Rear Crown Back'
    s8.Rc = 55.0
    s8.Thickness = 46.316201691
    s8.Diameter = 34.0
    s8.TiltX = 0.0
    s8.TiltY = 0.0
    s8.TiltZ = 0.0
    s8.DespX = 0.0
    s8.DespY = 0.0
    s8.DespZ = 0.0
    s8.AxisMove = 0.0
    s8.Glass = 'AIR'
    surfaces.append({'surface': 'Standard', 'name': 'Rear Crown Back', 'rc': 55.0, 'thickness': 46.316201691, 'diameter': 34.0, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s9 = Kos.surf()
    s9.Name = 'Image'
    s9.Rc = 0.0
    s9.Thickness = 0.0
    s9.Diameter = 1.0
    s9.TiltX = 0.0
    s9.TiltY = 0.0
    s9.TiltZ = 0.0
    s9.DespX = 0.0
    s9.DespY = 0.0
    s9.DespZ = 0.0
    s9.AxisMove = 0.0
    s9.Glass = 'AIR'
    surfaces.append({'surface': 'Image', 'name': 'Image', 'rc': 0.0, 'thickness': 0.0, 'diameter': 1.0, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

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
        s.Thickness = spec['thickness']
        s.Diameter = clear_aperture if spec['surface'] in {'Object', 'Image'} else spec['diameter']
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
        s.Drawing = 0.0 if spec['surface'] in {'Object', 'Image'} else 1.0
        if spec['surface'] == 'Thin Lens':
            s.Thin_Lens = spec['rc'] if spec['rc'] != 0 else 100.0
            s.Rc = 0.0
        elif spec['surface'] == 'Grating':
            s.Diff_Ord = 1.0
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

