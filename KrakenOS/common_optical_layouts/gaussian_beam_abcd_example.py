TITLE = "Gaussian Beam ABCD Example"

SETTINGS = {
    "object_mode": "Finite",
    "display_orientation": "Vertical",
    "wavelength": "0.6328",
    "ray_count": "9",
    "ray_height_factor": "0.7",
    "source_model": "Gaussian beam",
    "gaussian_waist_radius": "0.5",
    "gaussian_waist_offset": "0.0",
    "gaussian_m2": "1.0",
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
