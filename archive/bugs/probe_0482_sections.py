"""bugs/0482 probe -- the four SECTIONS of the AZ85 RA-mirror scene, before and after a FOV solve.

The user's numbering, along the beam:
    Section 1  object plane -> BS (glued to the LED)
    Section 2  BS -> imaging lens
    Section 3  imaging lens -> RA mirror
    Section 4  RA mirror -> sensor          ("the 4th distance")

Prints, for each of (as loaded, after 23x23, after 30x30): the row stations/thicknesses, the
world bounds of every body that can collide (LED, lens, camera, RA mirror, BS), the four section
distances, and the two clearances that must never go negative.

Run:
    DISPLAY=:99 .devenv/state/venv/bin/python bugs/probe_0482_sections.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def _bounds(app, label):
    try:
        mesh = app._transformed_imported_step_mesh_for_label(label)
        return np.asarray(mesh.bounds, dtype=float).reshape(6)
    except Exception:
        return None


def _promoted_rows(app):
    out = {}
    for index, row in enumerate(list(getattr(app, "rows", None) or [])):
        advanced = getattr(row, "advanced", None)
        if isinstance(advanced, dict) and (
            advanced.get("StepOverlayPromotion")
            or advanced.get("OpticalSolidFaces")
            or advanced.get("Solid_3d_stl")
        ):
            try:
                out[index] = np.asarray(app._promoted_solid_world_bounds(row, row_index=index), dtype=float).reshape(6)
            except Exception:
                out[index] = None
    return out


def _qe(app):
    from types import SimpleNamespace

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    return QuickEstimationService(SimpleNamespace(editor=app))


def report(app, tag):
    print(f"\n================= {tag}")
    rows = list(app.rows)
    stations = app._row_z_positions()
    print("  row  surface        name                          thickness    station   desp_z    glass")
    for i, r in enumerate(rows):
        print(
            f"  S{i:<3} {str(getattr(r, 'surface', '')):14s} {str(getattr(r, 'name', ''))[:28]:30s} "
            f"{float(r.thickness):9.4f} {float(stations[i]):10.4f} {float(r.desp_z):9.3f}  "
            f"{str(getattr(r, 'glass', '') or ''):8s}"
        )
    promoted = _promoted_rows(app)
    print("  promoted solid world bounds:")
    for i, b in promoted.items():
        if b is not None:
            print(f"    S{i}: x[{b[0]:8.2f},{b[1]:8.2f}] y[{b[2]:7.2f},{b[3]:7.2f}] z[{b[4]:8.2f},{b[5]:8.2f}]")
    print("  STEP bodies:")
    for label in ("led", "lens", "camera"):
        b = _bounds(app, label)
        if b is not None:
            print(f"    {label:7s} x[{b[0]:8.2f},{b[1]:8.2f}] y[{b[2]:7.2f},{b[3]:7.2f}] z[{b[4]:8.2f},{b[5]:8.2f}]")
    qe = _qe(app)
    image_index = app._image_plane_row_index()
    print(f"  object gap row = {qe.object_thickness_row()}  "
          f"image gap row = {qe.image_thickness_row()}  image row = {image_index}")
    try:
        print(f"  _object_locked_redirect_row -> {qe._object_locked_redirect_row(qe.object_thickness_row())}")
    except Exception as exc:
        print(f"  _object_locked_redirect_row raised {exc!r}")
    for side in ("object", "image"):
        try:
            split = (app._folded_object_conjugate_split() if side == "object" else app._folded_image_conjugate_split())
        except Exception as exc:
            split = f"raised {exc!r}"
        print(f"  folded {side} split: {split}")
    print(f"  glued BS<->LED flag: {bool(getattr(app, '_optical_led_glued', False))}")


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    app.layout_files["bs"] = SCENE
    app.load_layout_by_name("bs")
    report(app, "AS LOADED")
    for w in (23.0, 30.0):
        ok, msg = _qe(app).fov_solve("object", "thickness", w, w, (23.04, 23.04))
        print(f"\n>>> fov_solve(object, thickness, {w}x{w}) -> {ok}: {msg}")
        report(app, f"AFTER {w:.0f}x{w:.0f}")
    try:
        app.destroy()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
