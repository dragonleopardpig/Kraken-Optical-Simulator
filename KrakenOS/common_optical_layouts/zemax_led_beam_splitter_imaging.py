TITLE = "Zemax LED Beam-Splitter Imaging"

OSRAM_LED_GREEN_100K = (
    "attachment/LED/rayfile_LSG_T676_20200827_Zemax/"
    "rayfile_LSG_T676_green_100k_20200827_Zemax.DAT"
)

SETTINGS = {
    "layout_role": "layout",
    "object_mode": "Finite",
    "display_orientation": "Vertical",
    "wavelength": "0.568",
    "ray_count": "41",
    "ray_height_factor": "0.85",
    "source_model": "Zemax rayfile source",
    "source_power": "1.0",
    "source_x": "0.0",
    "source_y": "45.0",
    "source_z": "45.0",
    "source_l": "0.0",
    "source_m": "-1.0",
    "source_n": "0.0",
    "scene_row_order": "before_object",
    "scene_sources": [
        {
            "source_id": "source:osram-led-green",
            "name": "OSRAM LSG T676 green rayfile",
            "model": "Zemax rayfile source",
            "role": "illumination",
            "physical": True,
            "enabled": True,
            "origin": [0.0, 45.0, 45.0],
            "direction": [0.0, -1.0, 0.0],
            "ray_count": 41,
            "power": 1.0,
            "wavelength": 0.568,
            "rayfile_path": OSRAM_LED_GREEN_100K,
            "record_count": 100000,
            "rayfile_label": "OSRAM OS ZEMAX RAYSET",
            "Note": "Vendor Zemax Source File rays. Local +Z emission is rotated downward from the top port.",
        },
    ],
    "field_type": "Object Height",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "100.0",
    "trace_mode": "Non-Sequential Preview",
    "nonseq_target_surface": "Auto",
    "nonseq_ns_limit": "80",
    "nonseq_energy_probability": False,
    "analysis_surface": "Auto",
    "analysis_branch_filter": "All paths",
    "detector_bins": "48",
    "spot_view_mode": "Grid",
    "image_diameter_mode": "Manual",
    "show_clipped_rays": False,
    "show_path_labels": False,
    "analysis_modes": ["detector_map", "relative_illumination"],
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
    "OBJ_PROXY",
    "Left object proxy",
    "Reflect",
    parent_splitter="BS1",
    branch_selector="reflect",
    arm_distance=60.0,
)
IMAGING_LENS = element_metadata(
    "IMG_LENS",
    "Return-path imaging lens",
    "Transmit",
    parent_splitter="BS1",
    branch_selector="reflect->transmit",
    arm_distance=90.0,
)
CAMERA_SENSOR = element_metadata(
    "IMAGE",
    "Image plane",
    "Detector",
    parent_splitter="BS1",
    branch_selector="reflect->transmit",
    arm_distance=160.0,
)

SURFACES = [
    {
        "surface": "Object",
        "name": "Object reference row (not launch source)",
        "rc": 0.0,
        "thickness": 45.0,
        "diameter": 100.0,
        "drawing": 0.0,
        "glass": "AIR",
        "advanced": {
            "Note": (
                "The ray bundle is launched by SETTINGS['scene_sources'][0], an OSRAM Zemax rayfile LED. "
                "The Object row is reference geometry only."
            ),
        },
    },
    {
        "element": "45 degree splitter",
        "surface": "Beam Splitter",
        "name": "45 deg 50/50 splitter coating",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 3.0,
        "diameter": 100.0,
        "tilt_x": 45.0,
        "tilt_y": 0.0,
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
                "LED rays arrive from the top port. The useful reflected child branch turns left "
                "toward the object proxy; the return branch transmits through this splitter toward the lens."
            ),
        },
    },
    {
        "element": "45 degree splitter",
        "surface": "Standard",
        "name": "Splitter rear exit face",
        "rc": 0.0,
        "k": 0.0,
        "thickness": -60.0,
        "diameter": 100.0,
        "tilt_x": 45.0,
        "tilt_y": 0.0,
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
        "element": "Left object proxy",
        "surface": "Mirror",
        "name": "Left-side specular object proxy",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 87.0,
        "diameter": 120.0,
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
            "Note": (
                "Specular object proxy for this first source/object split example. "
                "A diffuse object BRDF/scatter model is still future work."
            ),
        },
    },
    {
        "element": "Return-path imaging lens",
        "surface": "Standard",
        "name": "Imaging lens front",
        "rc": 40.0,
        "k": 0.0,
        "thickness": 6.0,
        "diameter": 80.0,
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
            "Note": "Simple BK7 biconvex lens on the object-return transmitted branch.",
        },
    },
    {
        "element": "Return-path imaging lens",
        "surface": "Standard",
        "name": "Imaging lens back",
        "rc": -40.0,
        "k": 0.0,
        "thickness": 64.0,
        "diameter": 80.0,
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
        "element": "Image plane",
        "surface": "Image",
        "name": "Image plane",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 0.0,
        "diameter": 100.0,
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
            "Note": "Detector/image plane for the branch that returns from the object and transmits through the splitter.",
        },
    },
]
