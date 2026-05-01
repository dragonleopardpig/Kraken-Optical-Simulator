TITLE = "Surface Shape Builder Example"

SETTINGS = {
    "object_mode": "Infinity",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "9",
    "ray_height_factor": "0.8",
    "source_model": "Pupil / field",
    "pupil_pattern": "Fan",
    "field_type": "Angle",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "18.0",
    "spot_view_mode": "Grid",
    "analysis_modes": ["spot"],
}

SURFACES = [
    {
        "surface": "Object",
        "name": "Object",
        "rc": 0.0,
        "thickness": 45.0,
        "diameter": 30.0,
        "glass": "AIR",
    },
    {
        "surface": "Standard",
        "name": "Shape-builder demo surface",
        "rc": 95.0,
        "thickness": 8.0,
        "diameter": 28.0,
        "glass": "BK7",
        "extra_data": {
            "kind": "extra_surface",
            "preset": "radial_sine",
            "params": [7.0, 0.012],
        },
        "uda": {
            "kind": "regular_polygon",
            "radius": 11.0,
            "sides": 6,
            "rotation_deg": 30.0,
        },
        "advanced": {
            "AspherData": [0.0, 1.0e-5, -2.0e-9],
            "Mask_Type": 2,
            "Mask_Shape": {
                "kind": "mask_shape",
                "preset": "spider",
                "arms": 4,
                "arm_width": 0.9,
                "hub_radius": 1.8,
                "extent": 30.0,
            },
            "Note": "Select this row and click Shape... to preview/edit asphere, ExtraData, UDA, mask, and optical STL path.",
        },
    },
    {
        "surface": "Standard",
        "name": "Back surface",
        "rc": -95.0,
        "thickness": 50.0,
        "diameter": 28.0,
        "glass": "AIR",
    },
    {
        "surface": "Image",
        "name": "Image",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 16.0,
        "glass": "AIR",
    },
]
