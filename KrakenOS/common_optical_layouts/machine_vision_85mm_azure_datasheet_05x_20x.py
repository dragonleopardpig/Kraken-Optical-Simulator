TITLE = "Machine Vision 85 mm Azure (Datasheet 0.5X-2.0X)"

# AZURE Photonics ELS-85/4.5V16K (material code 3.A01.018545V16K-A): a large-format
# 16K/12K line-scan machine-vision lens.  Source document used for this surrogate:
#   attachment/Lens/ELS-85 4.5V16K_specification.pdf
#
# This is NOT the vendor prescription.  It is a paraxial blackbox equivalent built
# from the public datasheet first-order data:
#   f' = 85 mm, F/# = 4.5, back focus (rear glass vertex -> image @1X) = 141.85 mm,
#   optical total length TTL = 196.8 mm, max image circle 68 mm, magnifications
#   0.5X / 1.0X / 2.0X at object working distances 225 / 142 / 99 mm.
#
# The datasheet does not publish the Gaussian cardinals (SF, S'F', HH'); two facts
# pin them:
#   (1) TTL - back focus = 196.8 - 141.85 = 54.95 mm == the front-to-rear glass
#       vertex span, which OpenCascade extraction of the bundled STEP confirms at
#       55.0001 mm (glass faces F062 front / F064 rear).  So "back focus" is the
#       rear-glass-vertex-to-image distance and Sigma d = 55.0 mm.
#   (2) At 1X the lens is symmetric (front working distance ~= back focus ~= 141.85),
#       so each principal plane sits 2f' - 141.85 = 28.15 mm inside its vertex.
# Two equal thin-lens groups (f = 159.49 mm) placed symmetrically about the stop are
# solved to reproduce EFL = 85, SF = -56.85, S'F' = +56.85, H1 = 28.15 behind the
# front vertex and H2 = 28.15 ahead of the rear vertex, exactly, in air.  Because the
# surrogate is ideal it carries no real aberration -- a traced spot is defocus only.
# Drop in a Zemax wavefront / spot-radius export (as for the 150 mm 15056 lens) to
# augment it with the vendor's real OPD.
#
# The bundled vendor STEP is a mechanical overlay only (not traced).  OpenCascade
# extraction finds the first and last glass vertices at F062 (+13.2832 mm) and F064
# (-41.7169 mm), separated by 55.00010457 mm -- the datasheet Sigma d to within the
# 0.1 mm rounding of TTL -- so the model keeps the datasheet first-order values while
# placing the STEP glass surfaces on the same front and rear optical vertex datums.

STEP_PATH = "attachment/Lens/ELS-85-4.5V16K.STEP"
STEP_FRONT_GLASS_FACE_ID = "F062"
STEP_REAR_GLASS_FACE_ID = "F064"
STEP_FRONT_GLASS_VERTEX_Z_MM = 13.283194712382372
STEP_REAR_GLASS_VERTEX_Z_MM = -41.71690985733097
STEP_GLASS_VERTEX_SPAN_MM = STEP_FRONT_GLASS_VERTEX_Z_MM - STEP_REAR_GLASS_VERTEX_Z_MM
STEP_MECHANICAL_FRONT_Z_MM = 17.13214519981006
STEP_GLASS_ALIGNMENT_Z_OFFSET_MM = STEP_FRONT_GLASS_VERTEX_Z_MM - STEP_MECHANICAL_FRONT_Z_MM

EFFECTIVE_FOCAL_LENGTH = 85.0
# No explicit datasheet Sigma d; TTL (196.8, rounded to 0.1 mm) - back focus (141.85).
DATASHEET_FRONT_VERTEX_TO_REAR_VERTEX = 54.95
FRONT_VERTEX_TO_REAR_VERTEX = STEP_GLASS_VERTEX_SPAN_MM
FRONT_FOCAL_DISTANCE = -56.85
BACK_FOCAL_DISTANCE = 56.85
FRONT_PRINCIPAL_PLANE_Z = 28.15
REAR_PRINCIPAL_PLANE_Z = FRONT_VERTEX_TO_REAR_VERTEX - FRONT_PRINCIPAL_PLANE_Z

# Symmetric two-group solve (f1 = f2) reproducing the cardinals above in the
# 55.0001 mm glass span; the stop sits at the centre of symmetry.
GROUP_1_Z = 17.63852476698122
GROUP_2_Z = 37.36157980273212
STOP_Z = 27.50005228485667
GROUP_1_FOCAL_LENGTH = 159.48852476698121
GROUP_2_FOCAL_LENGTH = 159.48852476698121

GROUP_1_TO_STOP = STOP_Z - GROUP_1_Z
STOP_TO_GROUP_2 = GROUP_2_Z - STOP_Z
GROUP_2_TO_REAR = FRONT_VERTEX_TO_REAR_VERTEX - GROUP_2_Z

MIN_F_NUMBER = 4.5
STOP_DIAMETER = EFFECTIVE_FOCAL_LENGTH / MIN_F_NUMBER
MAX_SENSOR_DIAMETER = 68.0

# First-order finite-conjugate distances measured from the model's first and last
# optical vertex datums, not from the mechanical barrel shoulders.
OBJECT_TO_FRONT_VERTEX_0_5X = 226.85
REAR_VERTEX_TO_IMAGE_0_5X = 99.35
OBJECT_TO_FRONT_VERTEX_1X = 141.85
REAR_VERTEX_TO_IMAGE_1X = 141.85
OBJECT_TO_FRONT_VERTEX_2X = 99.35
REAR_VERTEX_TO_IMAGE_2X = 226.85

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
    # The vendor STEP is a MULTI-BODY assembly, so render all bodies (the full
    # ~52 mm barrel) -- the largest single connected solid is only an ~18 mm ring
    # (flag 20260629_203726). The lens optical axis is the STEP's local -X; the
    # loader's front-face="max" alignment + the glass-vertex offset below already
    # seat the front glass surface on the front optical-vertex datum (141.85) and
    # the rear glass on the rear datum (196.85), so NO 180 deg flip is needed here
    # -- unlike the PYRITE 85, whose STEP is authored along +Z.
    "lens_step_largest_component_only": False,
    "lens_step_rotation_x_deg": 0.0,
    "lens_step_rotation_y_deg": 0.0,
    "lens_step_rotation_z_deg": 0.0,
    "lens_step_axis_offset_xy": [0.0, 0.0],
    "lens_step_placement_offset_xyz": [0.0, 0.0, STEP_GLASS_ALIGNMENT_Z_OFFSET_MM],
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
        "diameter": 41.0,
        "glass": "AIR",
    },
    {
        "surface": "Thin Lens",
        "name": "Blackbox Group 1",
        "rc": GROUP_1_FOCAL_LENGTH,
        "thickness": GROUP_1_TO_STOP,
        "diameter": 37.0,
        "glass": "AIR",
    },
    {
        "surface": "Aperture",
        "name": "Aperture Stop F/4.5",
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
        "diameter": 37.0,
        "glass": "AIR",
    },
    {
        "surface": "Standard",
        "name": "Rear Optical Vertex Datum",
        "rc": 0.0,
        "thickness": REAR_VERTEX_TO_IMAGE_1X,
        "diameter": 41.0,
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
