TITLE = "Machine Vision 150 mm (Datasheet 1X)"

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

# Vendor blackbox truth available from ~/15056*:
#   - EFL = 149.9929 mm
#   - object distance = 275 mm
#   - last surface to image = 272 mm
#   - entrance pupil diameter = 26.8 mm
#   - fields = 0 / 10 / 16.5 mm (real image height)
#
# The .ZBB internals are proprietary, so this preset is intentionally a
# first-order equivalent thick-lens surrogate rather than a guessed multi-doublet.
# It reuses the measured-equivalent lens group, but is refocused to the vendor 1X
# conjugates so the UI starts from a physically defensible ~150 mm model instead
# of the earlier incorrect ~30 mm placeholder.

SURFACES = [
    {
        "surface": "Object",
        "name": "Object",
        "rc": 0.0,
        "thickness": 275.0,
        "diameter": 33.0,
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
        "thickness": 272.0,
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
