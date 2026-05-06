TITLE = "Right-Angle Beam-Splitter Illumination"

SETTINGS = {
    "layout_role": "layout",
    "object_mode": "Finite",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "9",
    "ray_height_factor": "0.85",
    "source_model": "Collimated disk source",
    "source_radius": "4.0",
    "source_cone_angle": "0.0",
    "source_power": "1.0",
    "source_seed": "5",
    "source_x": "0.0",
    "source_y": "-80.0",
    "source_z": "45.0",
    "source_l": "0.0",
    "source_m": "1.0",
    "source_n": "0.0",
    "source_angular_weight": "Uniform solid angle",
    "field_type": "Object Height",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "12.0",
    "trace_mode": "Non-Sequential Preview",
    "nonseq_target_surface": "Auto",
    "nonseq_ns_limit": "140",
    "nonseq_energy_probability": False,
    "analysis_surface": "Auto",
    "analysis_branch_filter": "All paths",
    "detector_bins": "32",
    "spot_view_mode": "Grid",
    "analysis_modes": ["spot", "relative_illumination"],
}

BEAM_SPLITTER_SETTINGS = {
    "split_mode": "Deterministic paths",
    "reflectance": 0.5,
    "absorption": 0.0,
    "transmit_phase_deg": 0.0,
    "reflect_phase_deg": 180.0,
    "min_branch_power": 1e-3,
    "max_branch_depth": 6,
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


COMMON_SPLITTER = element_metadata("BS1", "Cube-style splitter", "Common")
OBJECT_TARGET = element_metadata(
    "OBJ_TARGET",
    "Specular object",
    "Reflect",
    parent_splitter="BS1",
    branch_selector="reflect",
    arm_distance=63.0,
)
RELAY_LENS = element_metadata(
    "RELAY_LENS",
    "Camera relay lens",
    "Transmit",
    parent_splitter="BS1",
    branch_selector="reflect->transmit",
    arm_distance=75.0,
)
CAMERA_SENSOR = element_metadata(
    "CAMERA",
    "Camera sensor",
    "Detector",
    parent_splitter="BS1",
    branch_selector="reflect->transmit",
    arm_distance=120.0,
)

SURFACES = [
    {
        "surface": "Object",
        "name": "Object reference (not the source)",
        "rc": 0.0,
        "thickness": 45.0,
        "diameter": 30.0,
        "drawing": 0.0,
        "glass": "AIR",
        "advanced": {
            "Note": (
                "This row is the object/reference geometry. Illumination comes from Source 1 at "
                "Y=-80 mm, not from the Object row."
            ),
        },
    },
    {
        "element": "Cube-style splitter",
        "surface": "Beam Splitter",
        "name": "45 deg 50/50 splitter coating",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 3.0,
        "diameter": 28.0,
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
                "The physical source enters from the side port and the reflected child path turns "
                "toward the object plane along +Z."
            ),
        },
    },
    {
        "element": "Cube-style splitter",
        "surface": "Standard",
        "name": "Splitter exit face",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 60.0,
        "diameter": 28.0,
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
            "Note": "Parallel exit face for the finite BK7 splitter body.",
        },
    },
    {
        "element": "Specular object",
        "surface": "Mirror",
        "name": "Specular object proxy",
        "rc": 0.0,
        "k": 0.0,
        "thickness": -75.0,
        "diameter": 50.0,
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
                "Specular object proxy. The illumination branch reflects here and returns to the "
                "beam splitter. Diffuse/scattering object BRDF support is future work."
            ),
        },
    },
    {
        "element": "Camera relay lens",
        "surface": "Thin Lens",
        "name": "Camera relay thin lens",
        "rc": 45.0,
        "k": 0.0,
        "thickness": -45.0,
        "diameter": 25.0,
        "tilt_x": 0.0,
        "tilt_y": 0.0,
        "tilt_z": 0.0,
        "desp_x": 0.0,
        "desp_y": 0.0,
        "desp_z": 0.0,
        "axis_move": 0.0,
        "glass": "AIR",
        "advanced": {
            "Element": RELAY_LENS,
            "Note": "Relay lens placed on the object-return branch after transmission through the splitter.",
        },
    },
    {
        "element": "Camera sensor",
        "surface": "Image",
        "name": "Camera sensor",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 0.0,
        "diameter": 24.0,
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
            "Note": "Camera/image plane reached by the object-return branch after splitter transmission.",
        },
    },
]
