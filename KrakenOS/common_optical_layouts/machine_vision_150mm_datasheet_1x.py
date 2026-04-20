TITLE = "Machine Vision 150 mm (Datasheet 1X)"

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

# Vendor blackbox truth from 15056_BB_BB.zmx / ~/results:
#   EFL = 149.9929 mm, EPD = 26.8 mm, image fields = 0 / 10 / 16.5 mm.
#   1X physical conjugates: object to front datum = 275 mm, rear datum to
#   image = 272 mm, front-to-rear mechanical length = 48.81 mm.
#
# This is not a decoded blackbox prescription. It is a paraxial blackbox
# equivalent: two ideal thin-lens groups inside the measured barrel, tuned so
# the first-order cardinals match the Zemax blackbox closely:
#   EFL ~= 149.993 mm, H1 ~= 25.0 mm behind the front datum,
#   H2 ~= 28.0 mm in front of the rear datum.
# That makes the 1X conjugate close to 2F while keeping the displayed lens
# dimensions and working distances consistent with the vendor data.

FRONT_TO_HOUSING_GROUP_1 = 1.45390219
GROUP_1_FOCAL_LENGTH = 258.76640629
GROUP_1_TO_STOP = 24.405
STOP_TO_GROUP_2 = 21.64217312
GROUP_2_FOCAL_LENGTH = 293.32901330
GROUP_2_TO_REAR = 1.308924688
STOP_DIAMETER = 19.35624  # Zemax stop radius 9.67812 mm.

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
