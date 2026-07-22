TITLE = "Machine Vision 120 mm Pyrite (Datasheet 0.5X)"

# Schneider-Kreuznach PYRITE 5.6/120/0.5x V38, ID 1097787.
# Source document used for this surrogate:
# attachment/Lens/PYRITE_56_120_05x_V38_1097787/PYRITE_56_120_05x_V38_1097787_datasheet.pdf
#
# This is not the vendor prescription. It is a paraxial blackbox equivalent
# built from the public first-order data:
#   f'eff = 119.75 mm, SF = -95.36 mm, S'F' = 93.90 mm,
#   HH' = -0.54 mm, Sigma d = 49.71 mm.
# Therefore H1 = 24.39 mm behind the first optical vertex and the rear principal
# plane sits 23.86 mm behind the first optical vertex. Two thin-lens groups are
# solved to reproduce those cardinals in air while keeping the same UI workflow
# defaults as the Machine Vision 150Mm Measured preset (shared with the 1X
# Pyrite surrogate).
#
# The bundled vendor STEP is used as a mechanical overlay. OpenCascade
# extraction finds the first and last glass vertices at S001/F189 and
# S001/F188, separated by 49.71000007 mm. That is the rounded Sigma d value
# from the datasheet plus about 0.07 micrometres, so the model keeps the
# datasheet first-order values while placing the STEP glass surfaces on the same
# front and rear optical vertex datums.
#
# The aperture stop sits where the image of the stop through group 1 reproduces
# the datasheet entrance pupil (SEP = 24.33 mm behind the front vertex); the
# group-2 image of that stop lands the exit pupil at S'AP, consistent to ~0.1 mm.

STEP_PATH = "attachment/Lens/PYRITE_56_120_05x_V38_1097787/1097787_00155144_002.stp"
STEP_FRONT_GLASS_FACE_ID = "S001/F189"
STEP_REAR_GLASS_FACE_ID = "S001/F188"
STEP_FRONT_GLASS_VERTEX_Z_MM = 10.45735917625069
STEP_REAR_GLASS_VERTEX_Z_MM = -39.25264089717155
STEP_GLASS_VERTEX_SPAN_MM = STEP_FRONT_GLASS_VERTEX_Z_MM - STEP_REAR_GLASS_VERTEX_Z_MM
STEP_MECHANICAL_FRONT_Z_MM = 13.579584531832525
STEP_GLASS_ALIGNMENT_Z_OFFSET_MM = STEP_FRONT_GLASS_VERTEX_Z_MM - STEP_MECHANICAL_FRONT_Z_MM

EFFECTIVE_FOCAL_LENGTH = 119.75
DATASHEET_FRONT_VERTEX_TO_REAR_VERTEX = 49.71
FRONT_VERTEX_TO_REAR_VERTEX = STEP_GLASS_VERTEX_SPAN_MM
FRONT_FOCAL_DISTANCE = -95.36
BACK_FOCAL_DISTANCE = 93.90
FRONT_PRINCIPAL_PLANE_Z = FRONT_FOCAL_DISTANCE + EFFECTIVE_FOCAL_LENGTH
REAR_PRINCIPAL_PLANE_Z = FRONT_VERTEX_TO_REAR_VERTEX + BACK_FOCAL_DISTANCE - EFFECTIVE_FOCAL_LENGTH

GROUP_1_Z = 21.815253906381912
GROUP_2_Z = FRONT_VERTEX_TO_REAR_VERTEX - 1.2
STOP_Z = 24.379728825723515
GROUP_1_FOCAL_LENGTH = 129.68340176483088
GROUP_2_FOCAL_LENGTH = 1241.5577059915138

GROUP_1_TO_STOP = STOP_Z - GROUP_1_Z
STOP_TO_GROUP_2 = GROUP_2_Z - STOP_Z
GROUP_2_TO_REAR = FRONT_VERTEX_TO_REAR_VERTEX - GROUP_2_Z

MIN_F_NUMBER = 5.6
STOP_DIAMETER = EFFECTIVE_FOCAL_LENGTH / MIN_F_NUMBER
MAX_SENSOR_DIAMETER = 90.0

# First-order finite-conjugate distances measured from the model's first and
# last optical vertex datums, not from the mechanical barrel shoulders. The
# datasheet recommends magnification -0.5 across the -0.375 ... -0.675 range
# (working distance 411 ... 269 mm from the first mechanical element).
OBJECT_TO_FRONT_VERTEX_0_375X = 414.6933333333333
REAR_VERTEX_TO_IMAGE_0_375X = 138.80625
OBJECT_TO_FRONT_VERTEX_0_5X = 334.86
REAR_VERTEX_TO_IMAGE_0_5X = 153.775
OBJECT_TO_FRONT_VERTEX_0_675X = 272.7674074074074
REAR_VERTEX_TO_IMAGE_0_675X = 174.73125

SETTINGS = {
    "object_mode": "Finite",
    "display_orientation": "YZ",
    "projection_display_mode": "Full 3D",
    "wavelength": "0.55",
    "ray_count": "31",
    "ray_height_factor": "0.8",
    "full_pupil": False,
    "source_model": "Pupil / field",
    "pupil_pattern": "Meridional fan",
    "source_radius": "5.0",
    "source_cone_angle": "0.0",
    "gaussian_input_mode": "Waist + offset",
    "gaussian_waist_radius": "0.5",
    "gaussian_waist_offset": "0.0",
    "gaussian_beam_diameter": "1.0",
    "gaussian_full_divergence": "1.0",
    "gaussian_waist_side": "Waist before source",
    "gaussian_m2": "1.0",
    "pupil_rad": "0.0",
    "pupil_theta": "0.0",
    "source_power": "1.0",
    "source_seed": "1",
    "source_x": "0.0",
    "source_y": "0.0",
    "source_z": "0.0",
    "source_l": "0.0",
    "source_m": "0.0",
    "source_n": "1.0",
    "source_angular_weight": "Uniform solid angle",
    "scene_sources": [],
    "scene_row_order": "after_object",
    "analysis_surface": "Auto",
    "analysis_branch_filter": "All paths",
    "ray_display_mode": "All rays",
    "detector_bins": "Auto",
    "coherent_sum_mode": "By source ray",
    "branch_field_propagation_mm": "0.0",
    "aperture_type": "FNO",
    "aperture_value": str(MIN_F_NUMBER),
    "spot_view_mode": "Grid",
    "wavefront_style": "Wavefront Function",
    "tolerance_compare_view": "Spot overlay",
    "show_clipped_rays": False,
    "show_path_labels": True,
    "show_cardinals": True,
    "show_physical_distances": False,
    "field_type": "Real Image Height",
    "field_value": "11.52",
    "field_count": "3",
    "atmos_plot_mode": "Refraction / dispersion",
    "atmos_observatory": "Manual",
    "atmos_wavelength_min": "0.45",
    "atmos_wavelength_max": "0.75",
    "atmos_wavelength_count": "11",
    "atmos_zenith_deg": "45.0",
    "atmos_temperature_k": "283.15",
    "atmos_pressure_pa": "101300",
    "atmos_humidity": "0.5",
    "atmos_co2_ppm": "400",
    "atmos_latitude_deg": "31.0",
    "atmos_altitude_m": "2800",
    "image_diameter_mode": "Manual",
    "trace_mode": "Auto",
    "folded_detector_policy": "Trace events",
    "nonseq_target_surface": "Auto",
    "nonseq_ns_limit": "200",
    "nonseq_energy_probability": False,
    "camera_model": "Allied Vision hr25MCX",
    "camera_step_path": "attachment/Cameras/hr25MCX/3D_CAD_HR25xCXP.STEP",
    "camera_step_rotation_x_deg": 0.0,
    "camera_step_rotation_y_deg": 0.0,
    "camera_step_rotation_z_deg": 270.0,
    "camera_step_axis_offset_xy": [0.0, 0.0],
    "camera_step_placement_offset_xyz": [0.0, 0.0, 0.0],
    "lens_step_path": STEP_PATH,
    "lens_step_largest_component_only": True,
    "lens_step_rotation_x_deg": 0.0,
    "lens_step_rotation_y_deg": 0.0,
    "lens_step_rotation_z_deg": 0.0,
    "lens_step_axis_offset_xy": [0.0, 0.0],
    # bugs/0412: this is a NARROW barrel (body_span 54.7 <= 1.6*glass_span 49.7), so the bugs/0374
    # glass-centre pin already lands the glass on the datum span. Adding STEP_GLASS_ALIGNMENT_Z_OFFSET_MM
    # on top double-counts and DETACHES the STEP by its magnitude -> offset 0. (Constant kept as geometry
    # documentation; only a WIDE barrel, body_span > 1.6*glass_span, still needs the body-face nudge.)
    "lens_step_placement_offset_xyz": [0.0, 0.0, 0.0],
    "optical_step_path": "",
    "optical_step_rotation_x_deg": 0.0,
    "optical_step_rotation_y_deg": 0.0,
    "optical_step_rotation_z_deg": 0.0,
    "optical_step_axis_offset_xy": [0.0, 0.0],
    "optical_step_placement_offset_xyz": [0.0, 0.0, 0.0],
    "led_step_path": "",
    "led_step_rotation_x_deg": 0.0,
    "led_step_rotation_y_deg": 0.0,
    "led_step_rotation_z_deg": 0.0,
    "led_object_edge_distance_mm": 0.0,
    "led_step_object_edge_local_z": "",
    "led_step_axis_offset_xy": [0.0, 0.0],
    "led_step_placement_offset_xyz": [0.0, 0.0, 0.0],
    "analysis_mode": "none",
    "analysis_modes": [],
    "layout_preview_mode": "none",
    "auto_save_plot": False,
    "external_camera": "None",
    "camera_overlay_mode": "Off",
    "metal_catalogs": [],
    "optimization_workers": "Auto",
    "selected_operands": ["Spot RMS"],
    "operands": {
        "Entrance pupil z": {
            "weight": "1",
            "target": "0",
            "wavelength": "0.55",
            "field": "0",
            "surface": "Auto",
        },
        "Wavefront RMS": {
            "weight": "1",
            "target": "0",
            "wavelength": "0.55",
            "field": "0",
            "surface": "Auto",
        },
        "EFFL": {
            "weight": "1",
            "target": "100",
            "wavelength": "0.55",
            "field": "0",
            "surface": "Auto",
        },
        "Spot RMS": {
            "weight": "1",
            "target": "0",
            "wavelength": "0.55",
            "field": "0",
            "surface": "Auto",
        },
        "Exit pupil z": {
            "weight": "1",
            "target": "0",
            "wavelength": "0.55",
            "field": "0",
            "surface": "Auto",
        },
        "Thickness penalty": {
            "weight": "1",
            "target": "0.1",
            "wavelength": "0.55",
            "field": "0",
            "surface": "Auto",
        },
        "Magnification": {
            "weight": "1",
            "target": "1",
            "wavelength": "0.55",
            "field": "0",
            "surface": "Auto",
        },
        "MTF @ freq": {
            "weight": "1",
            "target": "0.5",
            "wavelength": "0.55",
            "field": "0",
            "field_x": "0",
            "field_y": "0",
            "surface": "Auto",
            "frequency": "5",
            "mtf_mode": "Average",
            "mtf_algorithm": "PSF FFT",
        },
    },
    "tolerance_solve_presets": [],
    "tolerance_manufacturing_templates": [],
    "active_tolerance_solve_preset": "",
}

SURFACES = [
    {
        "surface": "Object",
        "name": "Object at 0.5X",
        "rc": 0.0,
        "thickness": OBJECT_TO_FRONT_VERTEX_0_5X,
        "diameter": MAX_SENSOR_DIAMETER,
        "glass": "AIR",
    },
    {
        "surface": "Standard",
        "name": "Front Optical Vertex Datum",
        "rc": 0.0,
        "thickness": GROUP_1_Z,
        "diameter": 46.0,
        "glass": "AIR",
    },
    {
        "surface": "Thin Lens",
        "name": "Blackbox Group 1",
        "rc": GROUP_1_FOCAL_LENGTH,
        "thickness": GROUP_1_TO_STOP,
        "diameter": 38.0,
        "glass": "AIR",
    },
    {
        "surface": "Aperture",
        "name": "Aperture Stop F/5.6",
        "rc": 0.0,
        "thickness": STOP_TO_GROUP_2,
        "diameter": STOP_DIAMETER,
        "glass": "AIR",
    },
    {
        "surface": "Thin Lens",
        "name": "Blackbox Group 2",
        "rc": GROUP_2_FOCAL_LENGTH,
        "thickness": GROUP_2_TO_REAR,
        "diameter": 38.0,
        "glass": "AIR",
    },
    {
        "surface": "Standard",
        "name": "Rear Optical Vertex Datum",
        "rc": 0.0,
        "thickness": REAR_VERTEX_TO_IMAGE_0_5X,
        "diameter": 46.0,
        "glass": "AIR",
    },
    {
        "surface": "Image",
        "name": "Image / Sensor at 0.5X",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": MAX_SENSOR_DIAMETER,
        "glass": "AIR",
    },
]
