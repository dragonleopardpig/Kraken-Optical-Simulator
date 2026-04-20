TITLE = "Machine Vision 150 mm (Datasheet 0.5X)"

SETTINGS = {
    "object_mode": "Finite",
    "display_orientation": "Vertical",
    "field_type": "Real Image Height",
    "field_value": 16.5,
    "field_count": 3,
    "analysis_surface": 3,
    "aperture_type": "EPD",
    "aperture_value": 26.8,
    "wavelength": 0.546,
}

# Same paraxial blackbox equivalent as the 1X preset, refocused to the vendor
# 0.5X conjugates. With H1 ~= 25 mm behind the front datum and H2 ~= 28 mm in
# front of the rear datum, this corresponds to s ~= 450 mm and s' ~= 225 mm for
# a 150 mm lens, i.e. about 0.5X magnification.

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
        "thickness": 425.0,
        "diameter": 66.0,
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
