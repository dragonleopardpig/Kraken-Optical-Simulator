TITLE = "Machine Vision 120 mm Pyrite (Datasheet 1X)"

# Schneider-Kreuznach PYRITE 5.6/120/1.0x V38, ID 1097277.
# Source document used for this surrogate:
# attachment/Lens/PYRITE_56_120_10x_V38_1097277_datasheet.pdf
#
# This is not the vendor prescription. It is a paraxial blackbox equivalent
# built from the public first-order data:
#   f'eff = 120.68 mm, SF = -94.33 mm, S'F' = 94.33 mm,
#   HH' = -1.78 mm, Sigma d = 50.91 mm.
# Therefore H1 = 26.35 mm behind the first optical vertex and H2 = 24.56 mm
# behind the first optical vertex. Two thin-lens groups are solved to reproduce
# those cardinals in air while keeping the same UI workflow defaults as the
# Machine Vision 150Mm Measured preset.
#
# The bundled vendor STEP is used as a mechanical overlay. OpenCascade
# extraction finds the first and last glass vertices at S001/F193 and
# S001/F155, separated by 50.91000429 mm. That is the rounded Sigma d value
# from the datasheet plus about 4 nanometres, so the model keeps the datasheet
# first-order values while placing the STEP glass surfaces on the same front and
# rear optical vertex datums.

STEP_PATH = "attachment/Lens/1097277_00155156_002.stp"
STEP_FRONT_GLASS_FACE_ID = "S001/F193"
STEP_REAR_GLASS_FACE_ID = "S001/F155"
STEP_FRONT_GLASS_VERTEX_Z_MM = 8.832740625508794
STEP_REAR_GLASS_VERTEX_Z_MM = -42.077263664772836
STEP_GLASS_VERTEX_SPAN_MM = STEP_FRONT_GLASS_VERTEX_Z_MM - STEP_REAR_GLASS_VERTEX_Z_MM
STEP_MECHANICAL_FRONT_Z_MM = 11.970527779132407
STEP_GLASS_ALIGNMENT_Z_OFFSET_MM = STEP_FRONT_GLASS_VERTEX_Z_MM - STEP_MECHANICAL_FRONT_Z_MM

EFFECTIVE_FOCAL_LENGTH = 120.68
DATASHEET_FRONT_VERTEX_TO_REAR_VERTEX = 50.91
FRONT_VERTEX_TO_REAR_VERTEX = STEP_GLASS_VERTEX_SPAN_MM
FRONT_FOCAL_DISTANCE = -94.33
BACK_FOCAL_DISTANCE = 94.33
FRONT_PRINCIPAL_PLANE_Z = FRONT_FOCAL_DISTANCE + EFFECTIVE_FOCAL_LENGTH
REAR_PRINCIPAL_PLANE_Z = FRONT_VERTEX_TO_REAR_VERTEX + BACK_FOCAL_DISTANCE - EFFECTIVE_FOCAL_LENGTH

GROUP_1_Z = 17.760867505017475
GROUP_2_Z = FRONT_VERTEX_TO_REAR_VERTEX - 1.2
STOP_Z = 26.21
GROUP_1_FOCAL_LENGTH = 153.30504283282798
GROUP_2_FOCAL_LENGTH = 448.8953720876923

GROUP_1_TO_STOP = STOP_Z - GROUP_1_Z
STOP_TO_GROUP_2 = GROUP_2_Z - STOP_Z
GROUP_2_TO_REAR = FRONT_VERTEX_TO_REAR_VERTEX - GROUP_2_Z

MIN_F_NUMBER = 5.6
STOP_DIAMETER = EFFECTIVE_FOCAL_LENGTH / MIN_F_NUMBER
MAX_SENSOR_DIAMETER = 90.0

# First-order finite-conjugate distances measured from the model's first and
# last optical vertex datums, not from the mechanical barrel shoulders.
OBJECT_TO_FRONT_VERTEX_0_875X = 232.25
REAR_VERTEX_TO_IMAGE_0_875X = 199.925
OBJECT_TO_FRONT_VERTEX_1X = 215.01
REAR_VERTEX_TO_IMAGE_1X = 215.01
OBJECT_TO_FRONT_VERTEX_1_125X = 201.6011111111111
REAR_VERTEX_TO_IMAGE_1_125X = 230.095

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
    "camera_step_path": "attachment/Cameras/3D_CAD_HR25xCXP.STEP",
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
    "lens_step_placement_offset_xyz": [0.0, 0.0, STEP_GLASS_ALIGNMENT_Z_OFFSET_MM],
    "optical_step_path": "attachment/Lens/aspherized-achromatic-lenses/step_49665.step",
    "optical_step_rotation_x_deg": 0.0,
    "optical_step_rotation_y_deg": 0.0,
    "optical_step_rotation_z_deg": 0.0,
    "optical_step_axis_offset_xy": [0.0, 0.0],
    "optical_step_placement_offset_xyz": [-7.643807211221997, 99.08622523293911, 235.30119908802823],
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
        "name": "Object at 1X",
        "rc": 0.0,
        "thickness": OBJECT_TO_FRONT_VERTEX_1X,
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
        "thickness": REAR_VERTEX_TO_IMAGE_1X,
        "diameter": 46.0,
        "glass": "AIR",
    },
    {
        "surface": "Image",
        "name": "Image / Sensor at 1X",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": MAX_SENSOR_DIAMETER,
        "glass": "AIR",
    },
]
