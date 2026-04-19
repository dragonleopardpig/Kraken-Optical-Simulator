TITLE = "Machine Vision 150 mm (Datasheet 0.5X)"

SETTINGS = {
    "object_mode": "Finite",
    "display_orientation": "Vertical",
    "field_type": "Real Image Height",
    "field_value": 16.5,
    "field_count": 3,
    "analysis_surface": 2,
    "aperture_type": "STOP",
    "aperture_value": 26.8,
    "wavelength": 0.546,
}

# 0.5X configuration using the same first-order equivalent lens group as the
# 1X preset, refocused to the vendor 0.5X conjugates.
#
# This remains a surrogate, not a decoded blackbox prescription. It exists to
# keep the UI on a ~150 mm physically consistent starting point while matching
# the published working distances more closely than the earlier invalid
# multi-doublet placeholder.

SURFACES = [
    {
        "surface": "Object",
        "name": "Object",
        "rc": 0.0,
        "thickness": 425.0,
        "diameter": 66.0,
        "glass": "AIR",
    },
    {
        "surface": "Standard",
        "name": "Lens Front",
        "rc": 114.60971480633905,
        "thickness": 24.405,
        "diameter": 35.0,
        "glass": "BK7",
    },
    {
        "surface": "Standard",
        "name": "Stop Plane",
        "rc": 0.0,
        "thickness": 24.405,
        "diameter": 26.8,
        "glass": "BK7",
    },
    {
        "surface": "Standard",
        "name": "Lens Back",
        "rc": -211.2053946277084,
        "thickness": 197.0,
        "diameter": 35.0,
        "glass": "AIR",
    },
    {
        "surface": "Image",
        "name": "Image",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 33.0,
        "glass": "AIR",
    },
]
