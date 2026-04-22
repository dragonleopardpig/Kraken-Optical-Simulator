TITLE = "Machine Vision 150 mm (Measured 1X)"

SETTINGS = {
    "object_mode": "Finite",
    "display_orientation": "Vertical",
    "field_type": "Real Image Height",
    "field_value": 11.52,
    "field_count": 3,
    "image_diameter_mode": "Manual",
    "camera_model": "Allied Vision hr25MCX",
    "camera_step_path": "~/cameras/3D_CAD_HR25xCXP.STEP",
    "camera_step_rotation_z_deg": 0.0,
    "lens_step_path": "~/15056/15056.STEP",
    "analysis_surface": 3,
    "aperture_type": "FNO",
    "aperture_value": 5.6,
    "wavelength": 0.546,
}

# Measured 1X experiment setup:
#   object-to-front housing datum = 268 mm
#   front housing datum-to-sensor = 357 mm
#   camera front-to-sensor register = 11.48 mm
#   Allied Vision hr25MCX active sensor = 23.04 x 23.04 mm
#   barrel length = 48.81 mm
#
# The vendor Zemax blackbox is a focus-state model, not a complete mechanical
# prescription. The datasheet preset is therefore a separate blackbox-equivalent
# focus state. For the measured setup, the two ideal group focal lengths below
# are refit so the paraxial solve returns the measured rear-datum-to-sensor
# distance of 308.19 mm. This gives EFL ~= 156.51 mm, which is reasonable focus
# breathing for a nominal 150 mm machine-vision lens near 1X.

FRONT_TO_HOUSING_GROUP_1 = 1.45390219
GROUP_1_FOCAL_LENGTH = 272.10667374
GROUP_1_TO_STOP = 24.405
STOP_TO_GROUP_2 = 21.64217312
GROUP_2_FOCAL_LENGTH = 306.07721324
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
        "diameter": 23.04,
        "glass": "AIR",
    },
]
