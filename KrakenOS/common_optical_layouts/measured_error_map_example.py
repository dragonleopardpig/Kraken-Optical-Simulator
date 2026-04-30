TITLE = "Measured Error Map Example"

SETTINGS = {
    "object_mode": "Infinity",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "17",
    "field_type": "Angle",
    "field_value": "0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "18",
    "trace_mode": "Sequential",
    "analysis_modes": ["spot", "wavefront"],
}

import numpy as np


def _synthetic_measured_map():
    """Return KrakenOS Error_map = [X, Y, Z, SPACE] in millimetres."""
    pitch = 2.0
    axis = np.arange(-12.0, 12.0 + pitch, pitch)
    x_grid, y_grid = np.meshgrid(axis, axis)
    radius = np.hypot(x_grid, y_grid) / 12.0
    aperture = radius <= 1.0

    # A small low-order measured departure: defocus + astigmatism + ripple.
    z_grid = (
        1.0e-6
        + 2.5e-4 * (2.0 * radius**2 - 1.0)
        + 1.2e-4 * ((x_grid / 12.0) ** 2 - (y_grid / 12.0) ** 2)
        + 4.0e-5 * np.sin(2.0 * np.pi * x_grid / 8.0) * np.cos(2.0 * np.pi * y_grid / 10.0)
    )

    return [
        x_grid[aperture].ravel().tolist(),
        y_grid[aperture].ravel().tolist(),
        z_grid[aperture].ravel().tolist(),
        pitch,
    ]


SURFACES = [
    {
        "surface": "Object",
        "name": "Object",
        "rc": 0.0,
        "thickness": 80.0,
        "diameter": 28.0,
        "glass": "AIR",
    },
    {
        "surface": "Standard",
        "name": "Measured lens front",
        "rc": 120.0,
        "thickness": 5.0,
        "diameter": 28.0,
        "glass": "BK7",
        "advanced": {
            "Error_map": _synthetic_measured_map(),
            "Note": "Synthetic measured sag map in mm; use Error Map... to import/clear/replace it.",
        },
    },
    {
        "surface": "Standard",
        "name": "Lens back",
        "rc": -120.0,
        "thickness": 78.0,
        "diameter": 28.0,
        "glass": "AIR",
    },
    {
        "surface": "Image",
        "name": "Image",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 12.0,
        "glass": "AIR",
    },
]
