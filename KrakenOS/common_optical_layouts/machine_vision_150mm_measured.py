TITLE = "Machine Vision 150 mm (Measured)"

SETTINGS = {
    "object_mode": "Finite",
    "display_orientation": "Vertical",
    "field_type": "Object Height",
    "field_value": 9.75,
    "field_count": 3,
    "analysis_surface": 3,
    "aperture_type": "EPD",
    "aperture_value": 26.8,
    "wavelength": 0.546,
}

# Same paraxial blackbox-equivalent lens group as the datasheet presets, but
# with the user's measured mechanical distances: object-to-front datum = 268 mm,
# front datum-to-sensor = 357 mm, and barrel length = 48.81 mm. This preset is
# useful for checking whether the measured camera position is in focus.

FRONT_TO_HOUSING_GROUP_1 = 1.45390219
GROUP_1_FOCAL_LENGTH = 258.76640629
GROUP_1_TO_STOP = 24.405
STOP_TO_GROUP_2 = 21.64217312
GROUP_2_FOCAL_LENGTH = 293.32901330
GROUP_2_TO_REAR = 1.308924688
STOP_DIAMETER = 19.35624

SURFACES = [
    {
        "surface": "Object",
        "name": "Object",
        "rc": 0.0,
        "thickness": 268.0,
        "diameter": 19.5,
        "glass": "AIR",
    },
    {
        "surface": "Standard",
        "name": "Lens Front Datum",
        "rc": 0.0,
        "thickness": FRONT_TO_HOUSING_GROUP_1,
        "diameter": 35.0,
        "glass": "AIR",
    },
    {
        "surface": "Thin Lens",
        "name": "Blackbox Group 1",
        "rc": GROUP_1_FOCAL_LENGTH,
        "thickness": GROUP_1_TO_STOP,
        "diameter": 26.8,
        "glass": "AIR",
    },
    {
        "surface": "Aperture",
        "name": "Aperture Stop",
        "rc": 0.0,
        "thickness": STOP_TO_GROUP_2,
        "diameter": STOP_DIAMETER,
        "glass": "AIR",
    },
    {
        "surface": "Thin Lens",
        "name": "Blackbox Group 2",
        "rc": GROUP_2_FOCAL_LENGTH,
        "thickness": GROUP_2_TO_REAR,
        "diameter": 26.8,
        "glass": "AIR",
    },
    {
        "surface": "Standard",
        "name": "Lens Rear Datum",
        "rc": 0.0,
        "thickness": 308.19,
        "diameter": 35.0,
        "glass": "AIR",
    },
    {
        "surface": "Image",
        "name": "Image",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 23.0,
        "glass": "AIR",
    },
]
