TITLE = "Custom Surface Preset Example"

SETTINGS = {
    "object_mode": "Infinity",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "9",
    "field_type": "Angle",
    "field_value": "0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "12",
    "trace_mode": "Auto",
}

SURFACES = [
    {
        "name": "Object",
        "rc": 0.0,
        "thickness": 20.0,
        "diameter": 30.0,
        "glass": "AIR",
    },
    {
        "name": "Reference window",
        "rc": 55.134,
        "thickness": 8.0,
        "diameter": 30.0,
        "glass": "BK7",
    },
    {
        "name": "Radial sine custom sag",
        "rc": -224.69,
        "thickness": 45.0,
        "diameter": 30.0,
        "glass": "AIR",
        "extra_data": {
            "kind": "extra_surface",
            "preset": "radial_sine",
            "params": [5.0, 0.5],
        },
        "uda": {
            "kind": "regular_polygon",
            "radius": 14.0,
            "sides": 6,
            "rotation_deg": 30.0,
        },
        "advanced": {
            "Res": 1,
            "Note": "Editable/replayable ExtraData and UDA preset example.",
        },
    },
    {
        "name": "Image",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 60.0,
        "glass": "AIR",
    },
]
