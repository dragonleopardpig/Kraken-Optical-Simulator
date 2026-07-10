"""Machine-vision 150 mm coaxial area-LED illumination, FOLDED (the real beam path).

This is the folded companion to ``machine_vision_150mm_coaxial_led.py``. That layout
*unfolds* the coaxial path into a straight LED -> stop -> FOV line for a clean
relative-illumination measurement. THIS layout shows the actual folded beam the user
sees on the production floor, so the 3D inspector renders rays that:

    emanate from the area LED -> reflect off the 45 deg beam-splitter diagonal ->
    travel down to the object/FOV -> diffusely scatter back up -> transmit through the
    beam splitter -> reach the MV-150 imaging lens + camera.

REAL SETUP (user, production floor)
-----------------------------------
A 55x74 mm area LED shines from the SIDE (the +X face of the 55x55x78 mm beam-splitter
cube) -> reflects off the 45 deg BS diagonal -> down to a 39x39 mm FOV -> the object
scatters back up -> through the BS -> the MV-150 imaging lens + 25 MP camera. The camera
image shows 2 DARK EDGES on the fold (X) axis and is uniform on the perp (Y) axis: the
~30 mm fold clear-aperture under-fills the 39 mm FOV while the 74 mm dimension covers it.

GEOMETRY (X-fold; matches the MV-150 test scene's +X absorber face)
-------------------------------------------------------------------
The LED sits just OUTSIDE the +X face of the BS cube (where the test scene's absorbing
face is) and emits -X into the cube. The 45 deg diagonal (normal [-0.707, 0, +0.707])
reflects -X -> -Z, sending the beam down to the object. After the diffuse double-pass the
return beam transmits straight through (+Z) to the imaging lens and image.

Because the fold happens in the X-Z plane, the LED's local extents map to the object as:
    LED local-Y (perp)        -> object Y  (perp, 74 mm, uniform)
    LED local-Z (via the fold) -> object X  (fold, 55 mm, the 2 dark edges)
So the Random rectangle source uses radius_x = 37 (perp/Y) and radius_y = 27.5 (fold/Z).

This file is a VISUALIZATION of the folded path. The dark-edge magnitude is governed by
the BS clear-aperture stop; tuning that to match the unfolded layout's 0.66 fold ratio is
a follow-up (the unfolded layout remains the quantitative relative-illumination reference).
"""

TITLE = "Machine Vision 150mm Coaxial LED (Folded)"

# Fold axis = X (the 55 mm LED over the under-filling ~30 mm fold stop -> dark edges).
# Perp axis = Y (the 74 mm LED over the 78 mm aperture -> uniform).
LED_HALF_X = 27.5   # 55 mm area LED, fold axis (maps to object X through the fold)
LED_HALF_Y = 37.0   # 74 mm area LED, perp axis (maps to object Y directly)
LED_CONE_DEG = 30.0  # directional MV area-LED cone
LED_RAY_COUNT = 60   # this is the VISUAL companion layout; the diffuse double-pass fans
                     # each launched ray into many paths, so a modest count keeps the 3D
                     # ray picture readable (the unfolded layout is the quantitative RI ref)

BS_HALF = 27.5       # 55x55x78 BS cube; the diagonal works in the X-Z plane
LED_STANDOFF = 40.0  # LED plane just outside the +X face (small gap)
BS_Z = 45.0          # beam-splitter diagonal plane along the nominal axis
OBJECT_ARM = 130.0   # BS -> object/FOV (reflected, -Z arm)
RETURN_TO_LENS = 150.0  # object -> imaging lens (transmitted return arm)
FOV_MM = 39.0

# Apertures sized to pass the 74 mm LED without spurious clipping (the limiting fold stop
# is a follow-up; see module docstring).
WIDE_DIAM = 92.0

SETTINGS = {
    "layout_role": "layout",
    "object_mode": "Finite",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "15",
    "ray_height_factor": "0.85",
    "source_model": "Random rectangle source",
    "source_radius": str(LED_HALF_Y),
    "source_cone_angle": str(LED_CONE_DEG),
    "source_power": "1.0",
    "source_seed": "7",
    "source_x": str(LED_STANDOFF),
    "source_y": "0.0",
    "source_z": str(BS_Z),
    "source_l": "-1.0",
    "source_m": "0.0",
    "source_n": "0.0",
    "source_angular_weight": "Uniform solid angle",
    "scene_row_order": "before_object",
    "scene_sources": [
        {
            "source_id": "source:coaxial-area-led-folded",
            "name": "Coaxial 55x74 area LED (side port, folded)",
            "model": "Random rectangle source",
            "role": "illumination",
            "physical": True,
            "enabled": True,
            "origin": [LED_STANDOFF, 0.0, BS_Z],
            "direction": [-1.0, 0.0, 0.0],
            "radius_x": LED_HALF_Y,   # local-X -> world Y -> object perp (74 mm)
            "radius_y": LED_HALF_X,   # local-Y -> world Z -> object fold X (55 mm)
            "radius": LED_HALF_Y,
            "cone_deg": LED_CONE_DEG,
            "ray_count": LED_RAY_COUNT,
            "power": 1.0,
            "wavelength": 0.55,
            "Note": (
                "55 mm (fold) x 74 mm (perp) area LED at the +X side port of the BS cube, "
                "emitting -X. The 45 deg diagonal folds it down (-Z) to the object; the fold "
                "maps the 55 mm dimension onto the object X axis (the 2 dark edges)."
            ),
        },
    ],
    "field_type": "Object Height",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": str(WIDE_DIAM),
    "trace_mode": "Non-Sequential Preview",
    "nonseq_target_surface": "Auto",
    "nonseq_ns_limit": "80",
    "nonseq_energy_probability": False,
    "analysis_surface": "Auto",
    "analysis_branch_filter": "All paths",
    "detector_bins": "96",
    "spot_view_mode": "Grid",
    "image_diameter_mode": "Manual",
    "ray_display_mode": "Beam-splitter paths",
    "show_clipped_rays": False,
    "show_path_labels": False,
    "show_cardinals": False,
    "analysis_modes": ["detector_map", "relative_illumination"],
}

DIFFUSE_OBJECT_SETTINGS = {
    "model": "Lambertian",
    "backend": "Built-in",
    "reflectance": 0.8,
    "sample_count": 21,
    "max_scatter_angle_deg": 90.0,
    "min_branch_power": 1e-8,
    "max_branch_depth": 4,
    "target_surface": 1,
    "target_radius_scale": 0.9,
    "polarization": "Preserve projected Jones",
}

BEAM_SPLITTER_SETTINGS = {
    "split_mode": "Deterministic paths",
    "reflectance": 0.5,
    "absorption": 0.0,
    "transmit_phase_deg": 0.0,
    "reflect_phase_deg": 180.0,
    "min_branch_power": 1e-4,
    "max_branch_depth": 8,
}


def element_metadata(
    element_id,
    element_name,
    arm_role,
    *,
    parent_splitter="",
    branch_selector="",
    arm_distance=0.0,
):
    return {
        "element_id": element_id,
        "element_name": element_name,
        "arm_role": arm_role,
        "parent_splitter": parent_splitter,
        "branch_selector": branch_selector,
        "arm_distance": arm_distance,
        "local_decenter_x": 0.0,
        "local_decenter_y": 0.0,
        "local_tilt_x": 0.0,
        "local_tilt_y": 0.0,
        "local_tilt_z": 0.0,
    }


COMMON_SPLITTER = element_metadata("BS1", "45 degree splitter", "Common")
OBJECT_TARGET = element_metadata(
    "OBJ_TARGET",
    "Coaxial FOV object",
    "Reflect",
    parent_splitter="BS1",
    branch_selector="reflect",
    arm_distance=OBJECT_ARM,
)
IMAGING_LENS = element_metadata(
    "MV150_LENS",
    "MV-150 imaging lens",
    "Transmit",
    parent_splitter="BS1",
    branch_selector="reflect->transmit",
    arm_distance=RETURN_TO_LENS,
)
CAMERA_SENSOR = element_metadata(
    "IMAGE",
    "FOV / detector plane",
    "Detector",
    parent_splitter="BS1",
    branch_selector="reflect->transmit",
    arm_distance=RETURN_TO_LENS + 80.0,
)

SURFACES = [
    {
        "surface": "Object",
        "name": "Virtual LED reference row (not launch source)",
        "rc": 0.0,
        "thickness": BS_Z,
        "diameter": WIDE_DIAM,
        "drawing": 0.0,
        "glass": "AIR",
        "advanced": {
            "Display2D": {"show_reference_plane": False},
            "Note": (
                "Rays are launched by SETTINGS['scene_sources'][0], the 55x74 coaxial area LED at "
                "the +X side port. The Object row is reference geometry only."
            ),
        },
    },
    {
        "element": "45 degree splitter",
        "surface": "Beam Splitter",
        "name": "Beam-splitter 45 deg diagonal (X-fold)",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 3.0,
        "diameter": WIDE_DIAM,
        "tilt_x": 0.0,
        "tilt_y": -45.0,
        "tilt_z": 0.0,
        "desp_x": 0.0,
        "desp_y": 0.0,
        "desp_z": 0.0,
        "axis_move": 0.0,
        "glass": "BK7",
        "advanced": {
            "BeamSplitter": BEAM_SPLITTER_SETTINGS,
            "Element": COMMON_SPLITTER,
            "Note": (
                "LED rays arrive from the +X side port. The reflected child branch turns down (-Z) "
                "toward the object; the return branch transmits through toward the imaging lens."
            ),
        },
    },
    {
        "element": "45 degree splitter",
        "surface": "Standard",
        "name": "Splitter rear exit face",
        "rc": 0.0,
        "k": 0.0,
        "thickness": -OBJECT_ARM,
        "diameter": WIDE_DIAM,
        "tilt_x": 0.0,
        "tilt_y": -45.0,
        "tilt_z": 0.0,
        "desp_x": 0.0,
        "desp_y": 0.0,
        "desp_z": 0.0,
        "axis_move": 0.0,
        "glass": "AIR",
        "advanced": {
            "Element": COMMON_SPLITTER,
            "Note": "Parallel rear face of the finite BK7 splitter body.",
        },
    },
    {
        "element": "Coaxial FOV object",
        "surface": "Diffuse Object",
        "name": "FOV object (39x39 mm), diffuse return",
        "rc": 0.0,
        "k": 0.0,
        "thickness": RETURN_TO_LENS,
        "diameter": WIDE_DIAM,
        "tilt_x": 0.0,
        "tilt_y": 0.0,
        "tilt_z": 0.0,
        "desp_x": 0.0,
        "desp_y": 0.0,
        "desp_z": 0.0,
        "axis_move": 0.0,
        "glass": "MIRROR",
        "advanced": {
            "Element": OBJECT_TARGET,
            "DiffuseScatter": DIFFUSE_OBJECT_SETTINGS,
            "Display2D": {"label": "FOV object"},
            "Note": (
                "Built-in Lambertian diffuse boundary at the 39x39 mm FOV. Guided target sampling "
                "aims scattered child rays back toward the splitter return aperture so the coaxial "
                "return path can be analyzed."
            ),
        },
    },
    {
        "element": "MV-150 imaging lens",
        "surface": "Standard",
        "name": "Imaging lens front",
        "rc": 150.0,
        "k": 0.0,
        "thickness": 10.0,
        "diameter": WIDE_DIAM,
        "tilt_x": 0.0,
        "tilt_y": 0.0,
        "tilt_z": 0.0,
        "desp_x": 0.0,
        "desp_y": 0.0,
        "desp_z": 0.0,
        "axis_move": 0.0,
        "glass": "BK7",
        "advanced": {
            "Element": IMAGING_LENS,
            "Note": "Simple BK7 imaging lens on the transmitted return branch (MV-150 surrogate stand-in).",
        },
    },
    {
        "element": "MV-150 imaging lens",
        "surface": "Standard",
        "name": "Imaging lens back",
        "rc": -150.0,
        "k": 0.0,
        "thickness": 80.0,
        "diameter": WIDE_DIAM,
        "tilt_x": 0.0,
        "tilt_y": 0.0,
        "tilt_z": 0.0,
        "desp_x": 0.0,
        "desp_y": 0.0,
        "desp_z": 0.0,
        "axis_move": 0.0,
        "glass": "AIR",
        "advanced": {
            "Element": IMAGING_LENS,
            "Note": "Back face of the return-path imaging lens.",
        },
    },
    {
        "element": "FOV / detector plane",
        "surface": "Image",
        "name": "FOV / detector plane (39x39 mm)",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 0.0,
        "diameter": 2.0 * FOV_MM,
        "tilt_x": 0.0,
        "tilt_y": 0.0,
        "tilt_z": 0.0,
        "desp_x": 0.0,
        "desp_y": 0.0,
        "desp_z": 0.0,
        "axis_move": 0.0,
        "glass": "AIR",
        "advanced": {
            "Element": CAMERA_SENSOR,
            # Declare the 39x39 mm active sensor (mirrors the unfolded layout). Without it the
            # relative-illumination heatmap spans the 78 mm (2xFOV) catch diameter -- a square
            # beyond the image circle whose symmetric dark border hides the fold/perp asymmetry
            # (flag_20260709_093800_013). Explicit dims pin the heatmap to the +/-19.5 mm sensor the
            # Monitor shows, so the fold dark edges land AT the sensor edge. Trace aperture is
            # unchanged (still the surface diameter); this only sets the analysis/heatmap window.
            "Detector": {"active_width_mm": FOV_MM, "active_height_mm": FOV_MM},
            "Note": "Detector/image plane for the branch that returns from the object and transmits through the splitter.",
        },
    },
]
