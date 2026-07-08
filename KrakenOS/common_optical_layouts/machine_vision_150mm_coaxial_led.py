"""Machine-vision 150 mm coaxial area-LED illumination, unfolded, with the 2 dark edges.

REAL SETUP (user, production floor)
-----------------------------------
A 55x78 mm area LED shines from the SIDE -> reflects off the 45 deg diagonal of a
55x55x78 mm beam-splitter cube -> down to a 39x39 mm FOV -> the object reflects back up ->
through the BS -> the MV-150 imaging lens + 25 MP camera. The camera image shows 2 DARK
EDGES on one axis and is uniform on the other: the 55 mm illumination dimension under-fills
the FOV while the 78 mm dimension covers it.

WHY UNFOLDED / ON-AXIS (answers the user's Q4 "LED at the reflected position")
------------------------------------------------------------------------------
Reflecting the side LED in the 45 deg BS diagonal gives a VIRTUAL area source sitting
ON-AXIS directly above the FOV -- optically identical to the folded real LED. So this layout
models the simpler unfolded stack along +Z, which is exactly the "reflected position":

    z = 0   : 55x78 mm directional-cone area LED (SETTINGS['scene_sources'][0]), emitting +Z
    z = 75  : beam-splitter EXIT aperture -- the LIMITING STOP. Its fold-axis CLEAR APERTURE
              (~30 mm, smaller than the 55 mm face's 55*cos45 ~ 39 mm fold-foreshortened
              outline) UNDER-fills the 39 mm FOV; the perp axis stays 78 mm
    z = 130 : FOV / detector plane (39x39 mm), the relative-illumination target

WHY ONE AXIS GOES DARK (answers Q5 "simulate the 2 dark edges from relative illumination")
------------------------------------------------------------------------------------------
The dark edges are an ILLUMINATION-COVERAGE effect: the BS exit clear aperture (not the
imaging lens) is the limiting stop, so the irradiance landing on the FOV plane already
carries the 2 dark bands -- the exact quantity the "Relative illumination" analysis bins
(source rays -> target plane -> 2-D irradiance map). The fold-axis stop (~30 mm) is SMALLER
than the 39 mm FOV, so the fully-lit (umbra) patch PINCHES to ~+/-6 mm and the FOV edges fall
deep in the penumbra roll-off (edge ~ 0.66 of centre) -> the 2 dark edges. On the perp axis
the 78 mm stop exceeds the 39 mm FOV -> lit uniformly across the FOV.

The fold axis is X (the 55 mm / dark-edge axis); the perpendicular axis is Y (the 78 mm /
uniform axis). The rectangular BS-exit stop is a 4-vertex User-Defined Aperture (UDA).
"""

TITLE = "Machine Vision 150mm Coaxial LED Dark-Edge"

# Fold axis = X (the 55 mm LED over the under-filling ~30 mm fold stop -> dark edges).
# Perp axis = Y (the 78 mm LED over the 78 mm stop -> uniform).
LED_HALF_X = 27.5   # 55 mm area LED, fold axis
LED_HALF_Y = 39.0   # 78 mm area LED, perp axis
STOP_HALF_X = 15.0  # BS clear-aperture fold stop ~30 mm: UNDER-fills the 39 mm FOV
STOP_HALF_Y = 39.0  # BS exit face 78 mm on the perp axis -> covers the FOV
LED_CONE_DEG = 30.0  # directional MV area-LED cone; >24 deg keeps it stop-limited (not cone-limited)
LED_TO_STOP = 75.0  # LED plane -> BS exit aperture
STOP_TO_FOV = 55.0  # BS exit aperture -> FOV / detector
FOV_MM = 39.0
LED_RAY_COUNT = 60000

SETTINGS = {
    "layout_role": "layout",
    "object_mode": "Finite",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "15",
    "ray_height_factor": "0.85",
    "source_model": "Random rectangle source",
    "source_radius": str(LED_HALF_Y),
    "source_cone_angle": str(LED_CONE_DEG),
    "source_power": "1.0",
    "source_seed": "7",
    "source_x": "0.0",
    "source_y": "0.0",
    "source_z": "0.0",
    "source_l": "0.0",
    "source_m": "0.0",
    "source_n": "1.0",
    "source_angular_weight": "Uniform solid angle",
    "scene_row_order": "before_object",
    "scene_sources": [
        {
            "source_id": "source:coaxial-area-led",
            "name": "Coaxial 55x78 area LED (reflected/unfolded)",
            "model": "Random rectangle source",
            "role": "illumination",
            "physical": True,
            "enabled": True,
            "origin": [0.0, 0.0, 0.0],
            "direction": [0.0, 0.0, 1.0],
            "radius_x": LED_HALF_X,
            "radius_y": LED_HALF_Y,
            "radius": LED_HALF_Y,
            "cone_deg": LED_CONE_DEG,
            "ray_count": LED_RAY_COUNT,
            "power": 1.0,
            "wavelength": 0.55,
            "Note": (
                "55 mm (X, fold) x 78 mm (Y, perp) area LED at the BS-reflected on-axis position. "
                "The 55 mm dimension overfills the ~30 mm fold clear-aperture stop, which itself "
                "under-fills the 39 mm FOV -> the 2 dark edges."
            ),
        },
    ],
    "field_type": "Object Height",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": str(2.0 * STOP_HALF_Y),
    "trace_mode": "Non-Sequential Preview",
    "nonseq_target_surface": "Auto",
    "nonseq_ns_limit": "40",
    "nonseq_energy_probability": False,
    "analysis_surface": "Auto",
    "analysis_branch_filter": "All paths",
    "detector_bins": "96",
    "spot_view_mode": "Grid",
    "image_diameter_mode": "Manual",
    "analysis_modes": ["detector_map", "relative_illumination"],
}

SURFACES = [
    {
        "surface": "Object",
        "name": "Virtual LED plane (reference, not the launch source)",
        "rc": 0.0,
        "thickness": LED_TO_STOP,
        "diameter": 2.0 * max(LED_HALF_X, LED_HALF_Y),
        "drawing": 0.0,
        "glass": "AIR",
        "advanced": {
            "Display2D": {"show_reference_plane": False},
            "Note": (
                "Rays are launched by SETTINGS['scene_sources'][0], the 55x78 coaxial area LED at "
                "this plane. The Object row is reference geometry only."
            ),
        },
    },
    {
        "surface": "Standard",
        "name": "Beam-splitter exit aperture (55x55x78 cube, fold clear-aperture 30x78)",
        "rc": 0.0,
        "k": 0.0,
        "thickness": STOP_TO_FOV,
        "diameter": 2.2 * max(STOP_HALF_X, STOP_HALF_Y),
        "tilt_x": 0.0,
        "tilt_y": 0.0,
        "tilt_z": 0.0,
        "desp_x": 0.0,
        "desp_y": 0.0,
        "desp_z": 0.0,
        "axis_move": 0.0,
        "glass": "AIR",
        "uda": {
            "kind": "rectangle",
            "half_x": STOP_HALF_X,
            "half_y": STOP_HALF_Y,
        },
        "advanced": {
            "Display2D": {"label": "BS exit stop 30x78"},
            "Note": (
                "The LIMITING illumination stop: the BS clear aperture is ~30 mm on the fold (X) "
                "axis -- smaller than the 39 mm FOV, so it UNDER-fills it -- and 78 mm on the perp "
                "(Y) axis. Rectangular UDA. This aperture produces the 2 dark edges, NOT the imaging lens."
            ),
        },
    },
    {
        "surface": "Image",
        "name": "FOV / detector plane (39x39 mm)",
        "rc": 0.0,
        "k": 0.0,
        "thickness": 0.0,
        "diameter": 2.0 * FOV_MM,
        "tilt_x": 0.0,
        "tilt_y": 0.0,
        "tilt_z": 0.0,
        "desp_x": 0.0,
        "desp_y": 0.0,
        "desp_z": 0.0,
        "axis_move": 0.0,
        "glass": "AIR",
        "advanced": {
            "Display2D": {"label": "FOV 39x39"},
            # The detector active area = the 39x39 FOV (this unfolded plane IS the sensor). Declaring
            # it makes the relative-illumination map / heatmap span the sensor rectangle the Monitor
            # shows (+/-19.5 mm) instead of the 78 mm display diameter, so the dark edges land AT the
            # sensor edge. The physical trace aperture stays the surface diameter -- this only sets
            # the analysis/heatmap window.
            "Detector": {"active_width_mm": FOV_MM, "active_height_mm": FOV_MM},
            "Note": (
                "Relative-illumination target. The 39x39 mm FOV is +/-19.5 mm; the fold (X) edges sit "
                "in the penumbra roll-off (dark edges) while the perp (Y) edges stay uniformly lit."
            ),
        },
    },
]
