TITLE = "Michelson Interferometer (Ray Only)"

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
    "source_seed": "1",
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
    "interferometer_type": "Michelson ray-only",
}

BEAM_SPLITTER_SETTINGS = {
    "split_mode": "Deterministic branches",
    "reflectance": 0.5,
    "absorption": 0.0,
    "transmit_phase_deg": 0.0,
    "reflect_phase_deg": 180.0,
    "min_branch_power": 1e-4,
    # Two splitter events: initial split, then return/recombination split.
    "max_branch_depth": 2,
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


COMMON_SPLITTER = element_metadata("BS1", "Michelson splitter", "Common", parent_splitter="")
TRANSMIT_MIRROR = element_metadata(
    "M_TX",
    "Transmit return mirror",
    "Return",
    branch_selector="transmit",
    arm_distance=80.0,
)
REFLECT_MIRROR = element_metadata(
    "M_RX",
    "Reflect return mirror",
    "Return",
    branch_selector="reflect",
    arm_distance=80.0,
)

# Geometry:
# - Source is an independent physical source at (0, 0, 0), direction +Z.
# - The Object row is only a reference/scene datum, not the ray launch source.
# - The 45 degree splitter is at z=50 mm.
# - The transmitted arm mirror is at z=130 mm.
# - The reflected arm mirror is at y=80 mm, z=50 mm.
#
# This layout validates branch splitting and return/recombination paths. It is
# not a coherent fringe renderer; use the Branch Tree and Ray Inspector to
# inspect the four recombined ray-only paths. The source is intentionally a
# single chief ray so the 2-D plot reads like a Michelson schematic; increase
# Ray count and Source radius when checking bundles/aperture clipping.
SURFACES = [
    {
        "surface": "Object",
        "name": "Input/reference",
        "rc": 0.0,
        "thickness": 50.0,
        "diameter": 35.0,
        "glass": "AIR",
        "advanced": {
            "Note": (
                "Object is a separate reference plane. Physical rays are launched "
                "from Source settings, not from this row."
            )
        },
    },
    {
        "element": "Michelson splitter",
        "surface": "Beam Splitter",
        "name": "Michelson splitter",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 80.0,
        "diameter": 35.0,
        "tilt_x": 45.0,
        "tilt_y": 0.0,
        "tilt_z": 0.0,
        "axis_move": 0.0,
        "glass": "AIR",
        "advanced": {
            "BeamSplitter": BEAM_SPLITTER_SETTINGS,
            "Element": COMMON_SPLITTER,
            "Note": "First pass splits the source; second pass creates the ray-only recombination branches.",
        },
    },
    {
        "element": "Transmit return mirror",
        "surface": "Mirror",
        "name": "Transmit return mirror",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 0.0,
        "diameter": 35.0,
        "axis_move": 0.0,
        "glass": "MIRROR",
        "advanced": {"Element": TRANSMIT_MIRROR},
    },
    {
        "element": "Reflect return mirror",
        "surface": "Mirror",
        "name": "Reflect return mirror",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 0.0,
        "diameter": 35.0,
        "tilt_x": -90.0,
        "desp_y": 80.0,
        "desp_z": -80.0,
        "axis_move": 0.0,
        "glass": "MIRROR",
        "advanced": {"Element": REFLECT_MIRROR},
    },
    {
        "surface": "Image",
        "name": "Output/reference",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 35.0,
        "glass": "AIR",
        "advanced": {
            "Display2D": {"show_reference_plane": False, "show_reference_label": False},
            "Note": "Reference frame for 2-D plotting. Recombined ray-only branches terminate as output-port rays."
        },
    },
]
