"""The 3D inspector's Live Controls panel as data (docs/design_qt_migration.md phase 5f, part 2).

`panels/open3d_live_controls.py` is a Tk side panel inside the inspector's own window -- withdrawn
under the Qt shell. Measured (0929): of the 28 editor variables it edits, 26 are already editable in
the Qt main window's System / Source / Trace docks (0900-0902, the same variables), so its Field /
Trace / Source sections need no second Qt home. What the panel adds is named here:

  * the header: Live Mode, Trace now, Update 2D
  * the two display variables the docks do not carry: the image-diameter mode and the camera
  * Quick Estimation: the toggle, the thirteen readouts, three actions and the two role choices
  * the Variable-thickness solve (its gap list is the solve service's, read when shown)

The readouts are MODEL values: the inspector makes one host variable per key, the Quick Estimation
service writes them, and both views bind to them. (The Tk panel used to make its own `tk.StringVar`s
and hand them to the inspector, so under Qt the readouts had nowhere to go.)
"""
from __future__ import annotations

from KrakenOS.UI.open3d_toolbar import Check, Command

HEADER = (
    Check("Live Mode", "inspector.live_mode_var", "inspector._on_live_mode_toggled"),
    Command("Trace now", "inspector._trace_live_now"),
    Command("Update 2D", "editor._manual_update_plot"),
)

#: (variable, label, choices -- a tuple, or "cameras" for the live sensor catalogue, handler)
DISPLAY_CHOICES = (
    ("image_diameter_mode_var", "Image dia", ("Auto", "Manual"), "_on_image_diameter_mode_changed"),
    ("camera_model_var", "Camera", "cameras", "_on_camera_model_changed"),
)

QUICK_ESTIMATION_TOGGLE = Check("Quick Estimation", "inspector.quick_estimation_var",
                                "inspector._toggle_quick_estimation")

#: the readout rows, in order; None is a separator
READOUTS = (
    ("object_plane", "Object Plane"),
    ("object_thickness", "Object Thickness"),
    ("image_thickness", "Image Thickness"),
    ("image_plane", "Image Plane"),
    None,
    ("focal_length", "Focal length"),
    ("working_distance", "Working distance"),
    ("magnification", "Magnification"),
    ("sensor", "Sensor (Image H)"),
    ("fov", "FOV (Object H)"),
    ("target_fov", "Target FOV / fill"),
    ("recommended_sensor", "Rec. sensor"),
    ("focus", "Focus"),
    ("branches", "Per-arm"),
)

READOUT_KEYS = tuple(row[0] for row in READOUTS if row is not None)

QUICK_ESTIMATION_ACTIONS = (
    Command("Set Target FOV…", "inspector._quick_estimation_set_target_fov"),
    Command("Snap to FOV", "inspector._quick_estimation_snap_to_fov"),
    Command("Config Table…", "inspector._show_quick_estimation_config_table"),
)

#: (quantity, short label) -- the two conjugate thicknesses whose role the user picks
QUICK_ESTIMATION_ROLES = (("object_thickness", "Obj Thk"), ("image_thickness", "Img Thk"))

SOLVES = (
    ("Solve Best Focus", "focus"),
    ("Solve Best Collimation", "collimation"),
)


def camera_choices() -> tuple:
    from KrakenOS.UI.camera_database import CAMERA_NONE_LABEL, camera_names

    return (CAMERA_NONE_LABEL, *camera_names())


def display_choices(entry) -> tuple:
    _var, _label, choices, _handler = entry
    return camera_choices() if choices == "cameras" else tuple(choices)
