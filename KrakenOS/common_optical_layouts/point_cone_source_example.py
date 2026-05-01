TITLE = "Point Cone Source Example"

SETTINGS = {
    "object_mode": "Finite",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "121",
    "ray_height_factor": "0.8",
    "source_model": "Random point cone",
    "source_radius": "0.0",
    "source_cone_angle": "7.0",
    "source_power": "1.0",
    "source_seed": "17",
    "source_x": "0.0",
    "source_y": "0.0",
    "source_z": "0.0",
    "field_type": "Object Height",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "18.0",
    "analysis_modes": ["relative_illumination", "spot"],
}

SURFACES = [
    {
        "surface": "Object",
        "name": "Point cone emitter",
        "rc": 0.0,
        "thickness": 55.0,
        "diameter": 4.0,
        "glass": "AIR",
    },
    {
        "surface": "Standard",
        "name": "Collector front",
        "rc": 80.0,
        "thickness": 6.0,
        "diameter": 24.0,
        "glass": "BK7",
    },
    {
        "surface": "Standard",
        "name": "Collector back",
        "rc": -80.0,
        "thickness": 52.0,
        "diameter": 24.0,
        "glass": "AIR",
    },
    {
        "surface": "Image",
        "name": "Receiver",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 12.0,
        "glass": "AIR",
    },
]
