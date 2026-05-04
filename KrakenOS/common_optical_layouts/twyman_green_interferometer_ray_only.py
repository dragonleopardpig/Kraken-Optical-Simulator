TITLE = "Twyman-Green Interferometer (Interferogram)"

SETTINGS = {
    "object_mode": "Infinity",
    "display_orientation": "Vertical",
    "wavelength": "0.6328",
    "ray_count": "1",
    "ray_height_factor": "0.8",
    "source_model": "Collimated disk source",
    "source_radius": "0.5",
    "source_cone_angle": "0.0",
    "source_power": "1.0",
    "source_seed": "11",
    "source_x": "0.0",
    "source_y": "0.0",
    "source_z": "0.0",
    "source_l": "0.0",
    "source_m": "0.0",
    "source_n": "1.0",
    "source_angular_weight": "Uniform solid angle",
    "field_type": "Angle",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "1.0",
    "trace_mode": "Non-Sequential Preview",
    "nonseq_target_surface": "Auto",
    "nonseq_ns_limit": "80",
    "nonseq_energy_probability": False,
    "spot_view_mode": "Grid",
    "analysis_modes": [],
    "interferometer_type": "Twyman-Green coherent path diagnostic",
}

BEAM_SPLITTER_SETTINGS = {
    "split_mode": "Deterministic paths",
    "reflectance": 0.5,
    "absorption": 0.0,
    "transmit_phase_deg": 0.0,
    "reflect_phase_deg": 180.0,
    "min_branch_power": 1e-4,
    "max_branch_depth": 2,
}

INTERFEROGRAM_SETTINGS = {
    "analysis_title": "Twyman-Green Interferogram",
    "detector_port": "cross",
    "detector_size_mm": 12.0,
    "pixels": 256,
    "fringe_tilt_x_mrad": 2.0,
    "fringe_tilt_y_mrad": 0.0,
    "opd_offset_um": 0.0,
    "visibility": 1.0,
}


def element_metadata(
    element_id,
    element_name,
    arm_role,
    *,
    parent_splitter="BS1",
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


COMMON_COLLIMATOR = element_metadata("TG_INPUT", "Input collimator/reference", "Common", parent_splitter="")
COMMON_SPLITTER = element_metadata("BS1", "Twyman-Green splitter", "Common", parent_splitter="")
TEST_APERTURES = element_metadata(
    "TG_TEST_AP",
    "Test path aperture pair",
    "Return",
    branch_selector="transmit",
)
REF_APERTURES = element_metadata(
    "TG_REF_AP",
    "Reference path aperture pair",
    "Return",
    branch_selector="reflect",
)
TEST_MIRROR = element_metadata(
    "TG_TEST",
    "Test optic mirror",
    "Return",
    branch_selector="transmit",
    arm_distance=80.0,
)
REFERENCE_FLAT = element_metadata(
    "TG_REF",
    "Reference flat",
    "Return",
    branch_selector="reflect",
    arm_distance=80.0,
)
DETECTOR = element_metadata(
    "TG_DET",
    "Detector path",
    "Detector",
    branch_selector="reflect",
    arm_distance=70.0,
)

# This preset intentionally follows the tested Michelson-style recombination
# geometry. In Twyman-Green terms the transmitted path is the test optic path
# and the reflected path is the reference flat path.
SURFACES = [
    {
        "surface": "Object",
        "name": "Input/source reference",
        "rc": 0.0,
        "thickness": 10.0,
        "diameter": 35.0,
        "glass": "AIR",
        "advanced": {
            "Note": (
                "Object is a reference plane. Physical rays are launched from "
                "Source settings for this Twyman-Green preset."
            )
        },
    },
    {
        "element": "Input collimator/reference",
        "surface": "Aperture",
        "name": "Input pupil stop",
        "rc": 0.0,
        "thickness": 40.0,
        "diameter": 24.0,
        "glass": "AIR",
        "advanced": {"Element": COMMON_COLLIMATOR, "Display2D": {"show_reference_label": False}},
    },
    {
        "element": "Twyman-Green splitter",
        "surface": "Beam Splitter",
        "name": "Twyman-Green splitter",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 25.0,
        "diameter": 35.0,
        "tilt_x": 45.0,
        "tilt_y": 0.0,
        "tilt_z": 0.0,
        "axis_move": 0.0,
        "glass": "AIR",
        "advanced": {
            "BeamSplitter": BEAM_SPLITTER_SETTINGS,
            "Element": COMMON_SPLITTER,
            "Note": "Splits the collimated input into test and reference paths, then recombines returning rays.",
        },
    },
    {
        "element": "Test path aperture pair",
        "surface": "Aperture",
        "name": "Test path aperture A",
        "rc": 0.0,
        "thickness": 30.0,
        "diameter": 30.0,
        "glass": "AIR",
        "advanced": {"Element": TEST_APERTURES, "Display2D": {"show_reference_label": False}},
    },
    {
        "element": "Test path aperture pair",
        "surface": "Aperture",
        "name": "Test path aperture B",
        "rc": 0.0,
        "thickness": 25.0,
        "diameter": 30.0,
        "glass": "AIR",
        "advanced": {"Element": TEST_APERTURES, "Display2D": {"show_reference_label": False}},
    },
    {
        "element": "Test optic mirror",
        "surface": "Mirror",
        "name": "Test optic mirror",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 0.0,
        "diameter": 35.0,
        "axis_move": 0.0,
        "glass": "MIRROR",
        "advanced": {
            "Element": TEST_MIRROR,
            "Note": "Replace with a curved/decentered/tilted test surface to explore Twyman-Green diagnostics.",
        },
    },
    {
        "element": "Reference path aperture pair",
        "surface": "Aperture",
        "name": "Reference path aperture A",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 30.0,
        "tilt_x": -90.0,
        "desp_y": 25.0,
        "desp_z": -80.0,
        "axis_move": 0.0,
        "glass": "AIR",
        "advanced": {"Element": REF_APERTURES, "Display2D": {"show_reference_label": False}},
    },
    {
        "element": "Reference path aperture pair",
        "surface": "Aperture",
        "name": "Reference path aperture B",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 30.0,
        "tilt_x": -90.0,
        "desp_y": 55.0,
        "desp_z": -80.0,
        "axis_move": 0.0,
        "glass": "AIR",
        "advanced": {"Element": REF_APERTURES, "Display2D": {"show_reference_label": False}},
    },
    {
        "element": "Reference flat",
        "surface": "Mirror",
        "name": "Reference flat",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 0.0,
        "diameter": 35.0,
        "tilt_x": -90.0,
        "desp_y": 80.0,
        "desp_z": -80.0,
        "axis_move": 0.0,
        "glass": "MIRROR",
        "advanced": {"Element": REFERENCE_FLAT},
    },
    {
        "surface": "Image",
        "element": "Detector path",
        "name": "Detector path / output port",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 24.0,
        "glass": "AIR",
        "advanced": {
            "Element": DETECTOR,
            "Display2D": {
                "plane_center": [50.0, -70.0],
                "plane_tangent": [1.0, 0.0],
                "branch_output_targets": {
                    "TT": [0.0, 0.0],
                    "TR": [50.0, -70.0],
                    "RT": [50.0, -70.0],
                    "RR": [0.0, 0.0],
                },
            },
            "Interferogram": INTERFEROGRAM_SETTINGS,
            "Note": (
                "Detector display plane for the cross output port. Interf analysis "
                "uses the test/reference path-average diagnostic."
            ),
        },
    },
]
