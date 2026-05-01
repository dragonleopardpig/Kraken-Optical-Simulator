TITLE = "Beam Splitter 50/50 Example"

SETTINGS = {
    "object_mode": "Infinity",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "25",
    "ray_height_factor": "0.85",
    "source_model": "Random point cone",
    "source_radius": "0.0",
    "source_cone_angle": "0.0",
    "source_power": "1.0",
    "source_seed": "3",
    "source_x": "0.0",
    "source_y": "0.0",
    "source_z": "0.0",
    "source_angular_weight": "Uniform solid angle",
    "field_type": "Angle",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "18.0",
    "trace_mode": "Non-Sequential Preview",
    "nonseq_target_surface": "Auto",
    "nonseq_ns_limit": "120",
    "nonseq_energy_probability": True,
    "spot_view_mode": "Grid",
    "analysis_modes": ["spot"],
}

BEAM_SPLITTER_SETTINGS = {
    "split_mode": "Monte Carlo coating split",
    "reflectance": 0.5,
    "absorption": 0.0,
    "transmit_phase_deg": 0.0,
    "reflect_phase_deg": 180.0,
    "min_branch_power": 1e-3,
    "max_branch_depth": 8,
}

SURFACES = [
    {
        "surface": "Object",
        "name": "Input reference",
        "rc": 0.0,
        "thickness": 45.0,
        "diameter": 30.0,
        "glass": "AIR",
    },
    {
        "element": "Splitter",
        "surface": "Beam Splitter",
        "name": "50/50 beam splitter",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 45.0,
        "diameter": 25.0,
        "tilt_x": 45.0,
        "tilt_y": 0.0,
        "tilt_z": 0.0,
        "desp_x": 0.0,
        "desp_y": 0.0,
        "desp_z": 0.0,
        "axis_move": 0.0,
        "glass": "AIR",
        "advanced": {
            "BeamSplitter": BEAM_SPLITTER_SETTINGS,
            "Note": (
                "Right-click this row -> Beam splitter settings. Current KrakenOS tracing "
                "uses NS probabilistic coating split; deterministic reflected+transmitted "
                "child branches are future core work."
            ),
        },
    },
    {
        "surface": "Image",
        "name": "Large diagnostic target",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 100.0,
        "glass": "AIR",
    },
]
