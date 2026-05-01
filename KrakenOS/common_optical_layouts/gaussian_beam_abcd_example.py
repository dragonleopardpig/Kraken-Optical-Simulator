TITLE = "Gaussian Beam ABCD Example"

SETTINGS = {
    "object_mode": "Finite",
    "display_orientation": "Horizontal",
    "wavelength": "0.6328",
    "ray_count": "9",
    "ray_height_factor": "0.7",
    "field_type": "Object Height",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "18.0",
    "analysis_modes": ["2d"],
}

SURFACES = [
    {
        "surface": "Object",
        "name": "Input plane",
        "rc": 0.0,
        "thickness": 80.0,
        "diameter": 20.0,
        "glass": "AIR",
    },
    {
        "surface": "Thin Lens",
        "name": "Focusing lens f=100",
        "rc": 100.0,
        "thickness": 130.0,
        "diameter": 30.0,
        "glass": "AIR",
    },
    {
        "surface": "Image",
        "name": "Readout plane",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 16.0,
        "glass": "AIR",
    },
]
