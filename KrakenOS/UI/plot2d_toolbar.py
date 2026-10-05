"""The 2D layout plot's own controls, as data (bugs/0964).

The Tk shell builds them by hand on the plot's toolbar (`panels/main_window.py`: the 2D pane switch,
Plane, Show PP / EP / XP, Show labels, Rays, Physical Distance). The Qt shell builds the same
controls from this row with the 3D toolbar's own builder (`qt/inspector_toolbar.row_toolbar`), bound
to the SAME editor variables and commits -- so a Qt click is the Tk click, and the guard compares
the two.

The plot toolbar's buttons -- Trace Now, Update, Trace (the ray inspector), Flag bug -- are the Qt
shell's actions (ribbon, palette, keys), added beside these controls by the shell.
"""
from __future__ import annotations

from KrakenOS.UI.open3d_toolbar import Check, Choice, Row

PLOT_2D = Row("2D Plot", (
    # Tk: the "2D" check -- show or hide the layout pane (off frees the figure for analysis plots)
    Check("Layout pane", "editor.show_layout_2d_var", "editor.toggle_layout_2d"),
    Choice("Plane", "editor.display_orientation_var", ("YZ", "XZ", "XY", "All"),
           "editor._on_display_plane_changed", width=5),
    Check("Show PP / EP / XP", "editor.show_cardinals_var", "editor._on_toggle_cardinal_markers"),
    Check("Show labels", "editor.show_path_labels_var", "editor._on_toggle_path_labels"),
    Choice("Rays", "editor.ray_display_mode_var", "module:KrakenOS.UI.layout_editor.RAY_DISPLAY_VALUES",
           "editor._on_ray_display_mode_changed", width=18),
    Check("Physical Distance", "editor.show_physical_distances_var", "editor._on_toggle_physical_distances"),
))

#: the Tk plot toolbar's variable -> commit, for each control above: what a guard checks the Tk
#: shell still binds (a renamed variable or commit on either side fails there)
TK_BINDINGS = {
    "show_layout_2d_var": "toggle_layout_2d",
    "display_orientation_var": "_on_display_plane_changed",
    "show_cardinals_var": "_on_toggle_cardinal_markers",
    "show_path_labels_var": "_on_toggle_path_labels",
    "ray_display_mode_var": "_on_ray_display_mode_changed",
    "show_physical_distances_var": "_on_toggle_physical_distances",
}
