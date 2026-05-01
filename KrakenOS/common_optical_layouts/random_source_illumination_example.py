TITLE = "Random Source Illumination Example"

SETTINGS = {
    "object_mode": "Finite",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "101",
    "ray_height_factor": "0.8",
    "source_model": "Random circle source",
    "pupil_pattern": "Hexapolar",
    "source_radius": "3.0",
    "source_cone_angle": "8.0",
    "source_seed": "7",
    "field_type": "Object Height",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "18.0",
    "spot_view_mode": "Centroid",
    "analysis_modes": ["spot", "relative_illumination"],
}

SURFACES = [
    {
        "surface": "Object",
        "name": "Extended source plane",
        "rc": 0.0,
        "thickness": 55.0,
        "diameter": 8.0,
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
        "diameter": 16.0,
        "glass": "AIR",
    },
]
