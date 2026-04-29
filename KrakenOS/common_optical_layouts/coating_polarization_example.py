TITLE = "Coating Polarization Example"

SETTINGS = {
    "object_mode": "Infinity",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "9",
    "field_type": "Angle",
    "field_value": "0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "14",
    "trace_mode": "Auto",
    "analysis_modes": ["polarization"],
}

# KrakenOS coating table format:
#   Coating = [R, A, W, THETA]
# R and A are angle-by-wavelength tables. T is inferred as 1 - R - A.
# W is wavelength in microns. THETA is incidence angle in degrees.
AR_COATING = [
    [[0.010, 0.008, 0.011], [0.018, 0.014, 0.020]],
    [[0.000, 0.000, 0.000], [0.000, 0.000, 0.000]],
    [0.45, 0.55, 0.65],
    [0, 45],
]

MIRROR_COATING = [
    [[0.940, 0.960, 0.950], [0.920, 0.940, 0.930]],
    [[0.010, 0.010, 0.010], [0.015, 0.015, 0.015]],
    [0.45, 0.55, 0.65],
    [0, 45],
]

SURFACES = [
    {
        "name": "Object",
        "rc": 0.0,
        "thickness": 25.0,
        "diameter": 24.0,
        "glass": "AIR",
    },
    {
        "name": "AR front",
        "rc": 52.0,
        "thickness": 6.0,
        "diameter": 24.0,
        "glass": "BK7",
        "advanced": {
            "Coating": AR_COATING,
            "CoatingMet": 0,
            "Note": "Use Pol analysis to inspect TP/TS/RP/RS/TTBE.",
        },
    },
    {
        "name": "AR back",
        "rc": -52.0,
        "thickness": 38.0,
        "diameter": 24.0,
        "glass": "AIR",
        "advanced": {
            "Coating": AR_COATING,
            "CoatingMet": 0,
        },
    },
    {
        "surface": "Mirror",
        "name": "Protected mirror",
        "rc": 0.0,
        "thickness": 25.0,
        "diameter": 24.0,
        "tilt_x": 45.0,
        "axis_move": 2.0,
        "glass": "MIRROR",
        "advanced": {
            "Coating": MIRROR_COATING,
            "CoatingMet": 0,
            "Note": "A 45 degree fold places the image on the reflected branch; mirror throughput appears in TTBE and cumulative TT.",
        },
    },
    {
        "name": "Image",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 12.0,
        "glass": "AIR",
    },
]
