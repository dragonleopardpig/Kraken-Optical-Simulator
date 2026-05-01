TITLE = "R-Theta Pupil Diagnostic Example"

SETTINGS = {
    "object_mode": "Infinity",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "9",
    "ray_height_factor": "0.8",
    "source_model": "Pupil / field",
    "pupil_pattern": "R-theta",
    "pupil_rad": "0.72",
    "pupil_theta": "35.0",
    "field_type": "Angle",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "18.0",
    "trace_mode": "Auto",
    "spot_view_mode": "Grid",
    "analysis_modes": ["spot"],
}

SURFACES = [
    {
        "surface": "Object",
        "name": "Object",
        "rc": 0.0,
        "thickness": 40.0,
        "diameter": 30.0,
        "glass": "AIR",
    },
    {
        "surface": "Standard",
        "name": "Singlet front",
        "rc": 46.0,
        "thickness": 6.0,
        "diameter": 24.0,
        "glass": "BK7",
    },
    {
        "surface": "Standard",
        "name": "Singlet back",
        "rc": -46.0,
        "thickness": 54.0,
        "diameter": 24.0,
        "glass": "AIR",
    },
    {
        "surface": "Image",
        "name": "Image",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 10.0,
        "glass": "AIR",
    },
]
