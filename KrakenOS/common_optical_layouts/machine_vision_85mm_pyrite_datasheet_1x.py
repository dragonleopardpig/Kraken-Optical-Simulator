TITLE = "Machine Vision 85 mm Pyrite (Datasheet 1X)"

# Schneider-Kreuznach PYRITE 4.5/85/0.5x-2.0x V38, ID 1072517.
# Source document used for this surrogate:
# ~/Downloads/PYRITE_45_85_05x-20x_V38_1072517_datasheet.pdf
#
# This is not the vendor prescription.  It is a paraxial blackbox equivalent
# built from the public first-order data:
#   f'eff = 85.13 mm, SF = -62.45 mm, S'F' = 63.18 mm,
#   HH' = -5.12 mm, Sigma d = 39.52 mm.
# Therefore H1 = 22.68 mm behind the first optical vertex and H2 = 17.57 mm
# behind the first optical vertex.  Two thin-lens groups near the optical
# vertex ends are solved to reproduce those cardinals exactly in air.

EFFECTIVE_FOCAL_LENGTH = 85.13
FRONT_VERTEX_TO_REAR_VERTEX = 39.52
FRONT_FOCAL_DISTANCE = -62.45
BACK_FOCAL_DISTANCE = 63.18
FRONT_PRINCIPAL_PLANE_Z = 22.68
REAR_PRINCIPAL_PLANE_Z = 17.57

GROUP_1_Z = 1.71545542
GROUP_2_Z = 38.32
STOP_Z = 22.02
GROUP_1_FOCAL_LENGTH = 150.17565687
GROUP_2_FOCAL_LENGTH = 148.63880626

GROUP_1_TO_STOP = STOP_Z - GROUP_1_Z
STOP_TO_GROUP_2 = GROUP_2_Z - STOP_Z
GROUP_2_TO_REAR = FRONT_VERTEX_TO_REAR_VERTEX - GROUP_2_Z

MIN_F_NUMBER = 4.5
STOP_DIAMETER = EFFECTIVE_FOCAL_LENGTH / MIN_F_NUMBER
MAX_SENSOR_DIAMETER = 62.5

# First-order finite-conjugate distances measured from the model's first and
# last optical vertex datums, not from the mechanical barrel shoulders.
OBJECT_TO_FRONT_VERTEX_0_5X = 232.71
REAR_VERTEX_TO_IMAGE_0_5X = 105.745
OBJECT_TO_FRONT_VERTEX_1X = 147.58
REAR_VERTEX_TO_IMAGE_1X = 148.31
OBJECT_TO_FRONT_VERTEX_2X = 105.015
REAR_VERTEX_TO_IMAGE_2X = 233.44

SETTINGS = {
    "object_mode": "Finite",
    "display_orientation": "YZ",
    "projection_display_mode": "Full 3D",
    "field_type": "Real Image Height",
    "field_value": str(MAX_SENSOR_DIAMETER * 0.5),
    "field_count": "3",
    "analysis_surface": "Auto",
    "aperture_type": "FNO",
    "aperture_value": str(MIN_F_NUMBER),
    "wavelength": "0.55",
    "ray_count": "31",
    "ray_height_factor": "0.8",
    "source_model": "Pupil / field",
    "pupil_pattern": "Meridional fan",
    "source_radius": "5.0",
    "source_cone_angle": "0.0",
    "spot_view_mode": "Grid",
    "show_cardinals": True,
    "show_physical_distances": True,
}

SURFACES = [
    {
        "surface": "Object",
        "name": "Object at 1X",
        "rc": 0.0,
        "thickness": OBJECT_TO_FRONT_VERTEX_1X,
        "diameter": MAX_SENSOR_DIAMETER,
        "glass": "AIR",
    },
    {
        "surface": "Standard",
        "name": "Front Optical Vertex Datum",
        "rc": 0.0,
        "thickness": GROUP_1_Z,
        "diameter": 41.0,
        "glass": "AIR",
    },
    {
        "surface": "Thin Lens",
        "name": "Blackbox Group 1",
        "rc": GROUP_1_FOCAL_LENGTH,
        "thickness": GROUP_1_TO_STOP,
        "diameter": 37.0,
        "glass": "AIR",
    },
    {
        "surface": "Aperture",
        "name": "Aperture Stop F/4.5",
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
        "diameter": 37.0,
        "glass": "AIR",
    },
    {
        "surface": "Standard",
        "name": "Rear Optical Vertex Datum",
        "rc": 0.0,
        "thickness": REAR_VERTEX_TO_IMAGE_1X,
        "diameter": 41.0,
        "glass": "AIR",
    },
    {
        "surface": "Image",
        "name": "Image / Sensor at 1X",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": MAX_SENSOR_DIAMETER,
        "glass": "AIR",
    },
]
