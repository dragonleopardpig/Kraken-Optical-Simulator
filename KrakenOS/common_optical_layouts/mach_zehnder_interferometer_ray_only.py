TITLE = "Mach-Zehnder Interferometer (Interferogram)"

SETTINGS = {
    "object_mode": "Infinity",
    "display_orientation": "Vertical",
    "wavelength": "0.6328",
    "ray_count": "1",
    "ray_height_factor": "0.8",
    "source_model": "Collimated disk source",
    "source_radius": "2.0",
    "source_cone_angle": "0.0",
    "source_power": "1.0",
    "source_seed": "7",
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
    "aperture_value": "8.0",
    "trace_mode": "Non-Sequential Preview",
    "nonseq_target_surface": "Auto",
    "nonseq_ns_limit": "140",
    "nonseq_energy_probability": False,
    "spot_view_mode": "Grid",
    "analysis_modes": [],
    "interferometer_type": "Mach-Zehnder coherent branch diagnostic",
}

BEAM_SPLITTER_SETTINGS = {
    "split_mode": "Deterministic branches",
    "reflectance": 0.5,
    "absorption": 0.0,
    "transmit_phase_deg": 0.0,
    "reflect_phase_deg": 180.0,
    "min_branch_power": 1e-4,
    # Two splitter events: initial split at BS1 and recombination split at BS2.
    "max_branch_depth": 2,
}

INTERFEROGRAM_SETTINGS = {
    "analysis_title": "Mach-Zehnder Interferogram",
    "detector_port": "cross",
    "detector_size_mm": 12.0,
    "pixels": 256,
    "fringe_tilt_x_mrad": 1.0,
    "fringe_tilt_y_mrad": 0.0,
    "opd_offset_um": 0.0,
    "visibility": 1.0,
}


def element_metadata(
    element_id,
    element_name,
    arm_role,
    *,
    leg_id="",
    parent_splitter="BS1",
    branch_selector="",
    arm_distance=0.0,
):
    return {
        "element_id": element_id,
        "element_name": element_name,
        "leg_id": leg_id,
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


INPUT_BS = element_metadata("BS1", "Input splitter", "Common", leg_id="input", parent_splitter="")
TX_MIRROR = element_metadata(
    "M_TX",
    "Transmit-arm fold mirror",
    "Return",
    leg_id="transmit",
    branch_selector="transmit",
    arm_distance=70.0,
)
RX_MIRROR = element_metadata(
    "M_RX",
    "Reflect-arm fold mirror",
    "Return",
    leg_id="reflect",
    branch_selector="reflect",
    arm_distance=70.0,
)
OUTPUT_BS = element_metadata("BS2", "Output combiner", "Common", parent_splitter="")
DETECTOR_A = element_metadata(
    "MZ_DET_A",
    "Mach-Zehnder detector A",
    "Detector",
    leg_id="cross",
    parent_splitter="BS2",
    branch_selector="transmit",
    arm_distance=60.0,
)
DETECTOR_B = element_metadata(
    "MZ_DET_B",
    "Mach-Zehnder detector B",
    "Detector",
    leg_id="return",
    parent_splitter="BS2",
    branch_selector="reflect",
    arm_distance=60.0,
)

# Geometry in the Y/Z drawing:
# - BS1 at (Z=50, Y=0) splits +Z input into transmit (+Z) and reflect (-Y).
# - The transmit-arm mirror at (Z=120, Y=0) folds its beam downward.
# - The reflect-arm mirror at (Z=50, Y=-70) folds its beam rightward.
# - BS2 at (Z=120, Y=-70) receives both arms and splits them to two output
#   ports: cross port to the right, return port downward.
SURFACES = [
    {
        "surface": "Object",
        "name": "Input/reference",
        "rc": 0.0,
        "thickness": 50.0,
        "diameter": 18.0,
        "glass": "AIR",
        "advanced": {
            "Note": (
                "Object is a scene reference. Rays launch from the Source panel "
                "for this physical-source Mach-Zehnder preset."
            )
        },
    },
    {
        "element": "Input splitter",
        "surface": "Beam Splitter",
        "name": "BS1 input splitter",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 70.0,
        "diameter": 28.0,
        "tilt_x": -45.0,
        "glass": "AIR",
        "advanced": {
            "BeamSplitter": BEAM_SPLITTER_SETTINGS,
            "Element": INPUT_BS,
            "Note": "First 50/50 split. Reflected branch goes to the lower fold mirror.",
        },
    },
    {
        "element": "Transmit-arm fold mirror",
        "surface": "Mirror",
        "name": "Transmit-arm mirror",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 0.0,
        "diameter": 28.0,
        "tilt_x": -45.0,
        "glass": "MIRROR",
        "advanced": {"Element": TX_MIRROR},
    },
    {
        "element": "Reflect-arm fold mirror",
        "surface": "Mirror",
        "name": "Reflect-arm mirror",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 0.0,
        "diameter": 28.0,
        "tilt_x": -135.0,
        "desp_y": 70.0,
        "desp_z": -70.0,
        "glass": "MIRROR",
        "advanced": {"Element": RX_MIRROR},
    },
    {
        "element": "Output combiner",
        "surface": "Beam Splitter",
        "name": "BS2 output combiner",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 60.0,
        "diameter": 28.0,
        "tilt_x": -45.0,
        "desp_y": 70.0,
        "desp_z": 140.0,
        "glass": "AIR",
        "advanced": {
            "BeamSplitter": BEAM_SPLITTER_SETTINGS,
            "Element": OUTPUT_BS,
            "Interferogram": INTERFEROGRAM_SETTINGS,
            "Note": (
                "Second 50/50 splitter. T->R and R->T share the cross output; "
                "T->T and R->R share the return output."
            ),
        },
    },
    {
        "element": "Mach-Zehnder detector A",
        "surface": "Aperture",
        "name": "Cross output detector",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 0.0,
        "diameter": 24.0,
        "desp_y": 70.0,
        "desp_z": 150.0,
        "glass": "AIR",
        "advanced": {
            "Element": DETECTOR_A,
            "Display2D": {"show_reference_label": True},
        },
    },
    {
        "element": "Mach-Zehnder detector B",
        "surface": "Aperture",
        "name": "Return output detector",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 0.0,
        "diameter": 24.0,
        "tilt_x": -90.0,
        "desp_y": 0.0,
        "desp_z": 80.0,
        "glass": "AIR",
        "advanced": {
            "Element": DETECTOR_B,
            "Display2D": {"show_reference_label": True},
        },
    },
    {
        "surface": "Image",
        "name": "Global diagnostic image",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 1.0,
        "glass": "AIR",
        "advanced": {"Display2D": {"show_reference_plane": False, "show_reference_label": False}},
    },
]
