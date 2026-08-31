"""bugs/0669 -- the cell IN the live 3D canvas.

User (2026-08-31): "I see you put the 6-sided object in 2D menu and launch a separate
3D window. Can't we do everything to existing 3D canvas?"

The separate Inspection Cell window (0664) composes six station chains around the
part.  This service brings that composition INTO the live Open 3D canvas as GHOSTS:
each OTHER station is loaded headlessly, its scene actors are harvested from a
throw-away off-screen plotter (the 0664 transplant pattern) and re-parented into the
live renderer -- translucent, non-pickable context -- under the rigid transform that
carries its face onto the live scene's part.  The live station stays fully editable;
switching stations (0667 right-click axis -> Create/Open) swaps which face is live
and which are ghosts, all in ONE window.

Frames: the LIVE scene sits in its own station frame (object plane = the part's
active face).  A ghost's actors are authored in ITS station frame; `load_station`
gives T_ghost (ghost station -> part-centred cell frame), the live pose gives T_live
(live station -> cell frame), so the ghost lands in live-world coordinates under
T_live^-1 @ T_ghost.  Both transforms use the LIVE part spec's dimensions -- the live
editor is the authority on the part (display follows the physics).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI.services.inspection_cell import (
    CELL_SUFFIX,
    _vtk_matrix,
    cell_part_frames,
    load_cell,
    load_station,
    station_frame_transform,
)

vtk_matrix = _vtk_matrix


def find_cell_for_layout(layout_path: str | Path) -> dict[str, Any] | None:
    """The cell spec whose stations reference this layout: scan the ``*.cell.json``
    files beside it (0667 writes the cell next to the stations it creates)."""
    try:
        layout = Path(str(layout_path)).expanduser().resolve()
    except Exception:
        return None
    if not layout.name:
        return None
    try:
        candidates = sorted(layout.parent.glob(f"*{CELL_SUFFIX}"))
    except Exception:
        return None
    for path in candidates:
        try:
            cell = load_cell(path)
        except Exception:
            continue
        for entry in (cell.get("stations") or {}).values():
            lay = str((entry or {}).get("layout") or "")
            if not lay:
                continue
            try:
                if Path(lay).expanduser().resolve() == layout:
                    return cell
            except Exception:
                continue
    return None


def build_ghost_station(face: str, layout: str | Path, part_spec: dict[str, Any]) -> dict[str, Any]:
    """Load ONE station headlessly and harvest its scene actors for transplant.

    The actors are composed into a throw-away off-screen plotter by the SAME legacy
    populator the live canvas uses, the per-station helper axes are dropped (the
    0663 extent lesson), and the actors are detached so they survive the plotter's
    close -- the caller re-parents them into the live renderer."""
    import pyvista as pv

    layout = Path(str(layout)).expanduser()
    mtime = layout.stat().st_mtime
    station = load_station(layout, face, part_spec)
    plotter = pv.Plotter(off_screen=True)
    actors: list[Any] = []
    try:
        info = station.editor._populate_legacy_3d_plotter_scene(
            plotter, station.system, station.rays,
            scene_bundle=station.bundle, add_clip_plane=False, add_labels=False,
        ) or {}
        for helper in list(info.get("helper_actors") or []):
            try:
                plotter.remove_actor(helper, render=False)
            except Exception:
                pass
        actors = list(plotter.renderer.actors.values())
        for actor in actors:
            try:
                plotter.renderer.RemoveActor(actor)
            except Exception:
                pass
    finally:
        try:
            station.editor.destroy()
        except Exception:
            pass
        try:
            plotter.close()
        except Exception:
            pass
    return {
        "face": str(face),
        "layout": str(layout),
        "mtime": mtime,
        "actors": actors,
        "transform_cell": np.asarray(station.transform, dtype=float),
    }


def ghost_world_transform(
    live_obj_point, live_obj_axis, active_face: str, part_spec: dict[str, Any], transform_cell
) -> np.ndarray:
    """Live-world placement of a ghost: T_live^-1 @ T_ghost (both station->cell)."""
    fr = cell_part_frames(part_spec)[str(active_face)]
    T_live = station_frame_transform(live_obj_point, live_obj_axis, fr["center"], fr["normal"], fr["u"])
    return np.linalg.inv(T_live) @ np.asarray(transform_cell, dtype=float)
