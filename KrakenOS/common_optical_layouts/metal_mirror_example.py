from pathlib import Path

TITLE = "Metal Mirror Example"

METAL_DIR = Path(__file__).resolve().parent.parent / "Cat"

SETTINGS = {
    "object_mode": "Infinity",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "7",
    "field_type": "Angle",
    "field_value": "0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "20",
    "trace_mode": "Auto",
    "analysis_modes": ["polarization"],
    "metal_catalogs": [
        {"name": "Gold", "path": str(METAL_DIR / "Gold.csv"), "type": 1},
    ],
}

SURFACES = [
    {
        "name": "Object",
        "rc": 0.0,
        "thickness": 50.0,
        "diameter": 32.0,
        "glass": "AIR",
    },
    {
        "surface": "Mirror",
        "name": "Gold mirror",
        "rc": 0.0,
        "thickness": 50.0,
        "diameter": 32.0,
        "tilt_x": 45.0,
        "axis_move": 2.0,
        "glass": "MIRROR",
        "advanced": {
            "CoatingMet": 1,
            "Note": "Uses SETTINGS['metal_catalogs'][0] = Gold.csv, so CoatingMet=1 selects Gold. Alum remains index 0.",
        },
    },
    {
        "name": "Image",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 24.0,
        "glass": "AIR",
    },
]
