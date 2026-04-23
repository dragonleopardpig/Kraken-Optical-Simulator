#!/usr/bin/env python3
TITLE = "Machine Vision 150Mm Measured"

SETTINGS = {'object_mode': 'Finite',
 'display_orientation': 'Vertical',
 'wavelength': '0.55',
 'ray_count': '31',
 'ray_height_factor': '0.8',
 'analysis_surface': 'Auto',
 'aperture_type': 'FNO',
 'aperture_value': '5.6',
 'spot_view_mode': 'Grid',
 'show_clipped_rays': False,
 'show_cardinals': True,
 'show_physical_distances': True,
 'field_type': 'Real Image Height',
 'field_value': '11.52',
 'field_count': '3',
 'image_diameter_mode': 'Manual',
 'camera_model': 'Allied Vision hr25MCX',
 'camera_step_path': '/home/thinky/cameras/3D_CAD_HR25xCXP.STEP',
 'camera_step_rotation_z_deg': 270.0,
 'lens_step_path': '/home/thinky/15056/15056.STEP',
 'analysis_mode': 'none',
 'analysis_modes': [],
 'layout_preview_mode': 'none',
 'auto_save_plot': False,
 'external_camera': 'None',
 'camera_overlay_mode': 'Off',
 'optimization_workers': 'Auto',
 'selected_operands': ['Spot RMS'],
 'operands': {'Magnification': {'weight': '1',
                                'target': '1',
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
              'EFFL': {'weight': '1',
                       'target': '100',
                       'wavelength': '0.55',
                       'field': '0',
                       'surface': 'Auto'},
              'Spot RMS': {'weight': '1',
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
              'Wavefront RMS': {'weight': '1',
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
    s0.Thickness = 268.0
    s0.Diameter = 25.0
    s0.TiltX = 0.0
    s0.TiltY = 0.0
    s0.TiltZ = 0.0
    s0.DespX = 0.0
    s0.DespY = 0.0
    s0.DespZ = 0.0
    s0.AxisMove = 0.0
    s0.Glass = 'AIR'
    surfaces.append({'surface': 'Object', 'name': 'Object', 'rc': 0.0, 'thickness': 268.0, 'diameter': 25.0, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s1 = Kos.surf()
    s1.Name = 'Lens Front Datum'
    s1.Rc = 0.0
    s1.Thickness = 1.45390219
    s1.Diameter = 35.0
    s1.TiltX = 0.0
    s1.TiltY = 0.0
    s1.TiltZ = 0.0
    s1.DespX = 0.0
    s1.DespY = 0.0
    s1.DespZ = 0.0
    s1.AxisMove = 0.0
    s1.Glass = 'AIR'
    surfaces.append({'surface': 'Standard', 'name': 'Lens Front Datum', 'rc': 0.0, 'thickness': 1.45390219, 'diameter': 35.0, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s2 = Kos.surf()
    s2.Name = 'Blackbox Group 1'
    s2.Rc = 272.10667374
    s2.Thickness = 24.405
    s2.Diameter = 26.8
    s2.TiltX = 0.0
    s2.TiltY = 0.0
    s2.TiltZ = 0.0
    s2.DespX = 0.0
    s2.DespY = 0.0
    s2.DespZ = 0.0
    s2.AxisMove = 0.0
    s2.Glass = 'AIR'
    s2.Thin_Lens = 272.10667374
    s2.Rc = 0.0
    surfaces.append({'surface': 'Thin Lens', 'name': 'Blackbox Group 1', 'rc': 272.10667374, 'thickness': 24.405, 'diameter': 26.8, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s3 = Kos.surf()
    s3.Name = 'Aperture'
    s3.Rc = 0.0
    s3.Thickness = 21.64217312
    s3.Diameter = 19.35624
    s3.TiltX = 0.0
    s3.TiltY = 0.0
    s3.TiltZ = 0.0
    s3.DespX = 0.0
    s3.DespY = 0.0
    s3.DespZ = 0.0
    s3.AxisMove = 0.0
    s3.Glass = 'AIR'
    surfaces.append({'surface': 'Aperture', 'name': 'Aperture', 'rc': 0.0, 'thickness': 21.64217312, 'diameter': 19.35624, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s4 = Kos.surf()
    s4.Name = 'Blackbox Group 2'
    s4.Rc = 306.07721324
    s4.Thickness = 1.308924688
    s4.Diameter = 26.8
    s4.TiltX = 0.0
    s4.TiltY = 0.0
    s4.TiltZ = 0.0
    s4.DespX = 0.0
    s4.DespY = 0.0
    s4.DespZ = 0.0
    s4.AxisMove = 0.0
    s4.Glass = 'AIR'
    s4.Thin_Lens = 306.07721324
    s4.Rc = 0.0
    surfaces.append({'surface': 'Thin Lens', 'name': 'Blackbox Group 2', 'rc': 306.07721324, 'thickness': 1.308924688, 'diameter': 26.8, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s5 = Kos.surf()
    s5.Name = 'Lens Rear Datum'
    s5.Rc = 0.0
    s5.Thickness = 308.19
    s5.Diameter = 35.0
    s5.TiltX = 0.0
    s5.TiltY = 0.0
    s5.TiltZ = 0.0
    s5.DespX = 0.0
    s5.DespY = 0.0
    s5.DespZ = 0.0
    s5.AxisMove = 0.0
    s5.Glass = 'AIR'
    surfaces.append({'surface': 'Standard', 'name': 'Lens Rear Datum', 'rc': 0.0, 'thickness': 308.19, 'diameter': 35.0, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

    s6 = Kos.surf()
    s6.Name = 'Image'
    s6.Rc = 0.0
    s6.Thickness = 0.0
    s6.Diameter = 25.0
    s6.TiltX = 0.0
    s6.TiltY = 0.0
    s6.TiltZ = 0.0
    s6.DespX = 0.0
    s6.DespY = 0.0
    s6.DespZ = 0.0
    s6.AxisMove = 0.0
    s6.Glass = 'AIR'
    surfaces.append({'surface': 'Image', 'name': 'Image', 'rc': 0.0, 'thickness': 0.0, 'diameter': 25.0, 'tilt_x': 0.0, 'tilt_y': 0.0, 'tilt_z': 0.0, 'desp_x': 0.0, 'desp_y': 0.0, 'desp_z': 0.0, 'axis_move': 0.0, 'glass': 'AIR', 'optimize_rc': False, 'optimize_rc_bounds': None, 'optimize_thickness': False, 'optimize_thickness_bounds': None})

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

