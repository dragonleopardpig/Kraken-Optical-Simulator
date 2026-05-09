TITLE = "Mixed Source/Object Imaging Template"

SETTINGS = {
    "object_mode": "Finite",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "7",
    "ray_height_factor": "0.8",
    "source_model": "Pupil / field",
    "pupil_pattern": "Meridional fan",
    "field_type": "Object Height",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "28.0",
    "trace_mode": "Non-Sequential Preview",
    "nonseq_target_surface": "Auto",
    "nonseq_ns_limit": "90",
    "analysis_surface": "Auto",
    "analysis_branch_filter": "All paths",
    "detector_bins": "32",
    "analysis_modes": ["detector_map", "relative_illumination"],
    "scene_row_order": "before_object",
    "scene_sources": [
        {
            "source_id": "source:illum",
            "name": "Independent illuminator",
            "role": "illumination",
            "model": "Collimated disk source",
            "origin": [0.0, -12.0, 0.0],
            "direction": [0.0, 0.1483404529, 0.9889363529],
            "radius": 1.5,
            "ray_count": 7,
            "power": 1.0,
            "seed": 17,
        },
    ],
}

SURFACES = [
    {
        "surface": "Object",
        "name": "Object/reference plane",
        "rc": 0.0,
        "thickness": 40.0,
        "diameter": 28.0,
        "glass": "AIR",
        "advanced": {
            "Display2D": {"label": "Object reference"},
            "Note": (
                "Reference object geometry only. The physical illuminator is declared in "
                "SETTINGS['scene_sources'] and appears as a source row before Object."
            ),
        },
    },
    {
        "surface": "Aperture",
        "name": "Object-side clear aperture",
        "rc": 0.0,
        "thickness": 40.0,
        "diameter": 28.0,
        "glass": "AIR",
        "advanced": {
            "Display2D": {"label": "Object aperture"},
            "Note": "Editable placeholder for object-side baffles, pupils, filters, or illumination stops.",
        },
    },
    {
        "surface": "Image",
        "name": "Camera detector/Image",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 28.0,
        "glass": "AIR",
        "advanced": {
            "Display2D": {"label": "Detector"},
            "Detector": {
                "kind": "area",
                "bins": 32,
                "metric": "irradiance",
            },
            "Note": (
                "Detector/Image row for source illumination maps. Add lenses, filters, or stops between "
                "the object aperture and this row to turn the template into an imaging path."
            ),
        },
    },
]
