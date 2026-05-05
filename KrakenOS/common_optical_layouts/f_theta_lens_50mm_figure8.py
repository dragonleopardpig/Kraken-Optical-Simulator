"""50 mm F-theta lens transcribed from testing/F-theta.pdf Figure 8.

The source table is a Zemax prescription for a 0.65 um, 40 degree full-field,
2 mm entrance-pupil F-theta lens.  The original glass label ``K9`` is mapped
to the bundled CDGM ``H-K9L`` catalog glass because exact ``K9`` is not present
in KrakenOS/Cat.
"""

TITLE = "F-Theta Lens 50mm Figure 8"

DESIGN_WAVELENGTH_UM = 0.65
STOP_TO_FIRST_SURFACE_MM = 7.475
STOP_DIAMETER_MM = 2.0
IMAGE_DIAMETER_MM = 34.905782
FTHETA_ELEMENT = "F-theta Figure 8 lens"

SETTINGS = {
    "layout_role": "component",
    "object_mode": "Infinity",
    "display_orientation": "Vertical",
    "wavelength": str(DESIGN_WAVELENGTH_UM),
    "ray_count": "9",
    "ray_height_factor": "0.8",
    "aperture_type": "EPD",
    "aperture_value": str(STOP_DIAMETER_MM),
    "field_type": "Angle",
    "field_value": "20.0",
    "field_count": "5",
    "layout_note": (
        "Transcribed from testing/F-theta.pdf Figure 8. "
        "K9 is mapped to CDGM H-K9L."
    ),
}


def lens_surfaces(*, element: str = FTHETA_ELEMENT, name_prefix: str = "F-theta Fig8") -> list[dict]:
    """Return only the refractive surfaces after the scan stop/galvo plane."""
    rows = [
        {
            "surface": "Standard",
            "name": "S2 ZF13 front",
            "rc": 18.755950,
            "thickness": 2.000000,
            "glass": "ZF13",
            "diameter": 7.734748,
        },
        {
            "surface": "Standard",
            "name": "S3 ZF13 back",
            "rc": 14.249837,
            "thickness": 8.000000,
            "glass": "AIR",
            "diameter": 8.149450,
        },
        {
            "surface": "Standard",
            "name": "S4 ZF13 front",
            "rc": -6.955297,
            "thickness": 1.744000,
            "glass": "ZF13",
            "diameter": 11.930440,
        },
        {
            "surface": "Standard",
            "name": "S5 ZF13 back",
            "rc": -9.014725,
            "thickness": 0.449000,
            "glass": "AIR",
            "diameter": 14.479860,
        },
        {
            "surface": "Standard",
            "name": "S6 ZF13 front",
            "rc": -34.210999,
            "thickness": 4.585000,
            "glass": "ZF13",
            "diameter": 17.896750,
        },
        {
            "surface": "Standard",
            "name": "S7 ZF13 back",
            "rc": -14.584700,
            "thickness": 51.429000,
            "glass": "AIR",
            "diameter": 19.634244,
        },
        {
            "surface": "Standard",
            "name": "S8 H-K9L front",
            "rc": 459.562173,
            "thickness": 4.983000,
            "glass": "H-K9L",
            "diameter": 34.877516,
        },
        {
            "surface": "Standard",
            "name": "S9 H-K9L back",
            "rc": -74.209251,
            "thickness": 19.467596,
            "glass": "AIR",
            "diameter": 35.266490,
        },
    ]
    prefixed: list[dict] = []
    for row in rows:
        item = dict(row)
        item["element"] = element
        item["name"] = f"{name_prefix} {item['name']}"
        prefixed.append(item)
    return prefixed


SURFACES = [
    {
        "surface": "Object",
        "name": "Object at infinity",
        "thickness": 0.0,
        "diameter": STOP_DIAMETER_MM,
        "glass": "AIR",
    },
    {
        "surface": "Aperture",
        "element": "Entrance stop",
        "name": "Entrance stop / galvo plane",
        "thickness": STOP_TO_FIRST_SURFACE_MM,
        "diameter": STOP_DIAMETER_MM,
        "glass": "AIR",
    },
    *lens_surfaces(),
    {
        "surface": "Image",
        "element": "Scan plane",
        "name": "F-theta scan plane",
        "thickness": 0.0,
        "diameter": IMAGE_DIAMETER_MM,
        "glass": "AIR",
    },
]
