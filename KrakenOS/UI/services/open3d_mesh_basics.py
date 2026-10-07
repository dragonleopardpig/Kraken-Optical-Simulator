"""Mesh helpers of the 3D scene that need no window (bugs/0982).

They were static methods of the 3D inspector, a Tk window class until phase 7e of the Qt migration.
The scene tools used them through that class, which made importing the service load tkinter.
"""
from __future__ import annotations

import numpy as np


def mesh_with_transform(poly, transform):
    """`poly` as a surface mesh of its own (a deep copy), or None when it has no points or cannot be
    wrapped. ``transform`` is NOT applied: Kraken's SYSTEM.AAA blocks are already in display/world
    coordinates. TRANS_2A is for tracing into local surface coordinates; applying it here doubles
    the axial positions and moves optical markers away from imported STEP hardware."""
    try:
        import pyvista as pv

        mesh = pv.wrap(poly)
    except Exception:
        return None
    try:
        mesh = mesh.extract_surface(algorithm="dataset_surface")
    except Exception:
        pass
    try:
        mesh = mesh.copy(deep=True)
    except Exception:
        return None
    try:
        pts = np.asarray(mesh.points, dtype=float)
    except Exception:
        return None
    if pts.size == 0:
        return None
    return mesh
