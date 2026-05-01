TITLE = "Non-Sequential Ray Diagnostics Example"

SETTINGS = {
    "object_mode": "Infinity",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "13",
    "ray_height_factor": "0.8",
    "source_model": "Pupil / field",
    "pupil_pattern": "Cross fan",
    "field_type": "Angle",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "16.0",
    "trace_mode": "Non-Sequential Preview",
    "nonseq_target_surface": "Auto",
    "nonseq_ns_limit": "80",
    "nonseq_energy_probability": False,
    "spot_view_mode": "Grid",
    "analysis_modes": ["spot"],
}

SURFACES = [
    {
        "surface": "Object",
        "name": "Object",
        "rc": 0.0,
        "thickness": 35.0,
        "diameter": 30.0,
        "glass": "AIR",
    },
    {
        "surface": "Mirror",
        "name": "Fold mirror",
        "rc": 0.0,
        "thickness": 28.0,
        "diameter": 24.0,
        "tilt_x": 45.0,
        "axis_move": 2.0,
        "glass": "MIRROR",
        "advanced": {
            "Note": "Open Actions -> Ray Inspector, then Export CSV to inspect non-sequential hit data.",
        },
    },
    {
        "surface": "Standard",
        "name": "Folded window",
        "rc": 0.0,
        "thickness": 20.0,
        "diameter": 20.0,
        "glass": "BK7",
    },
    {
        "surface": "Image",
        "name": "Folded image",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 12.0,
        "glass": "AIR",
    },
]
