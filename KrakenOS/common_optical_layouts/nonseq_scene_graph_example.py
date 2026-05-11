from pathlib import Path

TITLE = "Non-Sequential Scene Graph Example"

METAL_DIR = Path(__file__).resolve().parent.parent / "Cat"

SETTINGS = {
    "object_mode": "Infinity",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "21",
    "ray_height_factor": "0.85",
    "source_model": "Random circle source",
    "source_radius": "2.0",
    "source_cone_angle": "4.0",
    "source_power": "1.0",
    "source_seed": "31",
    "source_x": "0.0",
    "source_y": "0.0",
    "source_z": "0.0",
    "source_angular_weight": "Uniform solid angle",
    "field_type": "Angle",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "16.0",
    "trace_mode": "Non-Sequential Preview",
    "nonseq_target_surface": "Auto",
    "nonseq_ns_limit": "120",
    "nonseq_energy_probability": True,
    "spot_view_mode": "Grid",
    "analysis_modes": ["spot"],
    "metal_catalogs": [
        {"name": "Gold", "path": str(METAL_DIR / "Gold.csv"), "type": 1},
    ],
}

SURFACES = [
    {
        "surface": "Object",
        "name": "Extended source reference",
        "rc": 0.0,
        "thickness": 28.0,
        "diameter": 22.0,
        "glass": "AIR",
    },
    {
        "element": "Fold mirror",
        "surface": "Mirror",
        "name": "45 deg folding mirror",
        "rc": 0.0,
        "thickness": 24.0,
        "diameter": 24.0,
        "tilt_x": 45.0,
        "axis_move": 2.0,
        "glass": "MIRROR",
        "advanced": {
            "CoatingMet": 1,
            "Note": "Open Actions -> Non-Sequential Scene Graph to inspect the source, target, element block, mirror, and branch-producing settings.",
        },
    },
    {
        "element": "Folded lens",
        "surface": "Standard",
        "name": "Folded lens front",
        "rc": 42.0,
        "thickness": 4.0,
        "diameter": 20.0,
        "glass": "BK7",
        "advanced": {
            "AspherData": [0.0, -2.0e-6],
            "Coating": [[], [], [], []],
        },
    },
    {
        "element": "Folded lens",
        "surface": "Standard",
        "name": "Folded lens back",
        "rc": -38.0,
        "thickness": 30.0,
        "diameter": 20.0,
        "glass": "AIR",
    },
    {
        "surface": "Image",
        "name": "Non-sequential image target",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 12.0,
        "glass": "AIR",
    },
]
