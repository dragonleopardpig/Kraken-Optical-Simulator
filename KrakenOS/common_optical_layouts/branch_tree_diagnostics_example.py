TITLE = "Branch Tree Diagnostics Example"

SETTINGS = {
    "object_mode": "Infinity",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "17",
    "ray_height_factor": "0.85",
    "source_model": "Pupil / field",
    "pupil_pattern": "Cross fan",
    "field_type": "Angle",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "18.0",
    "trace_mode": "Non-Sequential Preview",
    "nonseq_target_surface": "Auto",
    "nonseq_ns_limit": "90",
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
        "name": "Branch mirror",
        "rc": 0.0,
        "thickness": 30.0,
        "diameter": 24.0,
        "tilt_x": 45.0,
        "axis_move": 2.0,
        "glass": "MIRROR",
        "advanced": {
            "Note": "Use Actions -> Branch Tree Inspector to view branch parent links, hit ranges, and CSV export.",
        },
    },
    {
        "surface": "Standard",
        "name": "Folded diagnostic plate",
        "rc": 0.0,
        "thickness": 22.0,
        "diameter": 22.0,
        "glass": "BK7",
    },
    {
        "surface": "Image",
        "name": "Folded image",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 14.0,
        "glass": "AIR",
    },
]
