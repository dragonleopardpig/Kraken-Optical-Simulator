TITLE = "Native Variable Breadth Example"

SETTINGS = {
    "object_mode": "Infinity",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "15",
    "ray_height_factor": "0.8",
    "source_model": "Pupil / field",
    "pupil_pattern": "Hexapolar",
    "field_type": "Angle",
    "field_value": "3.0",
    "field_count": "3",
    "aperture_type": "EPD",
    "aperture_value": "20.0",
    "analysis_modes": ["spot"],
    "selected_operands": ["Spot RMS"],
    "operands": {
        "Spot RMS": {"weight": "1", "target": "0", "wavelength": "0.55", "field": "3.0", "surface": "Auto"},
    },
}

SURFACES = [
    {
        "surface": "Object",
        "name": "Object",
        "rc": 0.0,
        "thickness": 45.0,
        "diameter": 30.0,
        "glass": "AIR",
    },
    {
        "surface": "Standard",
        "name": "Conic / tilt variable surface",
        "rc": 70.0,
        "k": -0.4,
        "thickness": 7.0,
        "diameter": 28.0,
        "tilt_x": 1.0,
        "glass": "BK7",
        "advanced": {
            "Var": ["k", "TiltX"],
            "VarBounds": {"k": (-1.5, 0.5), "TiltX": (-3.0, 3.0)},
            "Note": "Right-click K or Tilt X to toggle/bound these native variables.",
        },
    },
    {
        "surface": "Standard",
        "name": "Back surface",
        "rc": -70.0,
        "thickness": 55.0,
        "diameter": 28.0,
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
