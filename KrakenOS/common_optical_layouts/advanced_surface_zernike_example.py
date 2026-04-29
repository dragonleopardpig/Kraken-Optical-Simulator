TITLE = "Advanced Surface Zernike Example"

SETTINGS = {
    "object_mode": "Infinity",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "11",
    "field_type": "Angle",
    "field_value": "0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "18",
    "trace_mode": "Sequential",
    "analysis_modes": ["wavefront"],
}

# `advanced` is the saved-layout sidecar for KrakenOS-native surface
# attributes that are intentionally kept out of the compact prescription table.
SURFACES = [
    {
        "name": "Object",
        "rc": 0.0,
        "thickness": 35.0,
        "diameter": 28.0,
        "glass": "AIR",
    },
    {
        "name": "Plano-convex front",
        "rc": 64.0,
        "k": -0.25,
        "thickness": 5.0,
        "diameter": 28.0,
        "glass": "BK7",
        "advanced": {
            "AspherData": [0.0, 1.2e-5, -3.5e-9],
            "SubAperture": [0.92, 0.0, 0.0],
            "Note": "Short AspherData lists are padded to KrakenOS native length.",
        },
    },
    {
        "name": "Zernike phase plate",
        "rc": 0.0,
        "thickness": 45.0,
        "diameter": 28.0,
        "glass": "AIR",
        "advanced": {
            "ZNK": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.08, -0.04, 0.03],
            "ShiftX": 0.15,
            "ShiftY": -0.10,
            "Res": 2,
            "Note": "ZNK is padded to KrakenOS native length during rebuild.",
        },
    },
    {
        "name": "Image",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 10.0,
        "glass": "AIR",
    },
]
