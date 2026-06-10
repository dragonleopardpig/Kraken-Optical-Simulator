#!/usr/bin/env python3
"""Image-snapshot regression for bugs/0046: a cemented doublet whose bond is
modelled as a real microns-thick ``___BLANK`` glass must read as TWO cemented
elements in the LIVE inspector with rays ON -- never as a third floating slab.

Why this exists on top of ``validate_cemented_doublet_body_count`` (Phase 51):
that test exercises ``_iter_3d_side_body_meshes`` in isolation, where the cement
body already leaves opacity 0. But the live scene runs through
``open3d_scene_refresh.refresh_scene``, which (with rays visible) clamps every
analytic optic body back up to >= 0.26 -- silently re-inflating the hidden cement
into a visible full-aperture slab *and* redrawing its rim outline. A property-only
test passed while the live render still showed the duplicate (exactly the
"VTK-property assertions alone missed the ghost block" failure mode). So this boots
the real inspector, turns rays ON, looks edge-on, and asserts -- at the live actor
level and in a rendered frame -- that no *filled* glass body is confined to the
sub-0.05 mm cement band, while the crown and flint bodies stay visible.

Discriminator: a glass *body* mesh carries polygon faces
(``GetNumberOfPolys() > 0``); a rim/feature-edge outline is a polyline
(0 polys). So "a visible filled body only microns thick" is the slab regression,
whereas the legitimate near-coincident cemented-interface *cap rims* (two
polylines 7.5 um apart that merge into one line edge-on) are correctly ignored.

Run (boots its own private Xvfb if DISPLAY is unset):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_cemented_doublet_body_count_snapshot

Exit: 0 = pass, 1 = regression (a thin cement slab is visible), 2 = environment
cannot render (no Xvfb) or fixture unavailable.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from KrakenOS.UI.services.three_d_scene_tools import _CEMENT_LAYER_MAX_AXIAL_THICKNESS_MM

# A body counts as "visible" above this opacity; the suppressed cement sits at 0.
_VISIBLE_OPACITY = 0.05
# A glass volume this thin (mm) along the optical axis is a cement / bond layer,
# never a free-standing element -- the same threshold the renderer fix uses.
_CEMENT_BAND_MM = _CEMENT_LAYER_MAX_AXIAL_THICKNESS_MM
# ...but a flat reference disc (Object / Image / Stop plane) has z-thickness
# EXACTLY 0; a real cement bond is microns-thick (the flagged BLANK is 7.5 um).
# Require a strictly positive floor so flat planes aren't mistaken for a slab.
_CEMENT_BAND_MIN_MM = 1e-3


def _doublet_rows():
    from KrakenOS.UI.layout_editor import SurfaceRow

    # Crown (BK7, 8 mm) + a real 7.5 um cement BLANK + flint (F2, 5 mm) -- the
    # shape of the flagged ``Doublet_4_surf_no_TDE.zmx``.
    return [
        SurfaceRow(label="0", surface="Object", element="", name="Object", thickness=100.0, diameter=20.0, glass="AIR"),
        SurfaceRow(label="1", surface="Standard", element="", name="Stop", thickness=2.0, diameter=20.0, glass="AIR", rc=0.0),
        SurfaceRow(label="2", surface="Standard", element="", name="Crown front", thickness=8.0, diameter=30.0, glass="N-BK7", rc=52.46),
        SurfaceRow(label="3", surface="Standard", element="", name="Cement", thickness=0.0075, diameter=30.0, glass="N-SF2", rc=-55.46),
        SurfaceRow(label="4", surface="Standard", element="", name="Flint front", thickness=5.0, diameter=30.0, glass="F2", rc=-55.46),
        SurfaceRow(label="5", surface="Standard", element="", name="Flint back", thickness=114.0, diameter=30.0, glass="AIR", rc=-300.0),
        SurfaceRow(label="6", surface="Image", element="", name="Image", thickness=0.0, diameter=30.0, glass="AIR"),
    ]


def _filled_body_actors(renderer):
    """Yield (z_thickness_mm, opacity) for every *filled* (polygon-bearing)
    actor in the live scene -- i.e. glass bodies, not rim/edge polylines."""
    out = []
    coll = renderer.GetViewProps()
    coll.InitTraversal()
    prop = coll.GetNextProp()
    while prop is not None:
        try:
            if prop.IsA("vtkActor"):
                mapper = prop.GetMapper()
                data = mapper.GetInput() if mapper is not None else None
                npolys = int(data.GetNumberOfPolys()) if data is not None else 0
                if npolys > 0:
                    b = np.asarray(prop.GetBounds(), dtype=float)
                    if b.size == 6 and np.all(np.isfinite(b)):
                        zthk = float(b[5] - b[4])
                        opac = float(prop.GetProperty().GetOpacity())
                        out.append((zthk, opac))
        except Exception:
            pass
        prop = coll.GetNextProp()
    return out


def _lens_glass_rows(rows) -> set[int]:
    """Indices of the rows that are glass optical faces (a real glass on either
    side) -- i.e. the lens caps that legitimately draw a rim, excluding the air
    aperture Stop and the Object/Image planes."""
    out: set[int] = set()
    for i, r in enumerate(rows):
        if str(getattr(r, "surface", "") or "") in {"Object", "Image"}:
            continue
        g = str(getattr(r, "glass", "") or "").strip().upper()
        prev_g = str(getattr(rows[i - 1], "glass", "") or "").strip().upper() if i > 0 else ""
        if (g not in {"", "AIR"}) or (prev_g not in {"", "AIR"}):
            out.add(i)
    return out


def _rim_line_zs(renderer, actor_row, lens_rows, merge_tol=0.05) -> list[float]:
    """Distinct z of the rim/edge LINE actors (no polys) that track a lens-glass
    row, merging rims within ``merge_tol`` mm -- so the two cemented-interface
    caps 7.5 um apart count as ONE vertical line. One entry per visible rim line."""
    zs: list[float] = []
    coll = renderer.GetViewProps()
    coll.InitTraversal()
    prop = coll.GetNextProp()
    while prop is not None:
        try:
            if prop.IsA("vtkActor") and actor_row.get(id(prop)) in lens_rows:
                mapper = prop.GetMapper()
                data = mapper.GetInput() if mapper is not None else None
                if data is not None and int(data.GetNumberOfLines()) > 0 and int(data.GetNumberOfPolys()) == 0:
                    b = np.asarray(prop.GetBounds(), dtype=float)
                    if b.size == 6 and (b[5] - b[4]) < 1.0:  # a flat rim, not a long ray polyline
                        zs.append(0.5 * (b[4] + b[5]))
        except Exception:
            pass
        prop = coll.GetNextProp()
    zs.sort()
    merged: list[float] = []
    for z in zs:
        if not merged or abs(z - merged[-1]) > merge_tol:
            merged.append(round(z, 4))
    return merged


def _measure(out_dir: Path, app=None, inspector=None):
    """Render the doublet rays-on edge-on and return the body metrics. Reuses a
    provided ``(app, inspector)`` when given (Phase 51 passes the shared harness
    inspector, so no second Tk root is booted); otherwise boots its own."""
    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import render_window_to_png

    if inspector is None:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

        app = KrakenLayoutEditor()
        inspector = _open_inspector(app)
    try:
        inspector.show_rays_var.set(True)  # the path that re-inflated the cement
        inspector.show_rotation_handles_var.set(False)
    except Exception:
        pass

    app.rows = _doublet_rows()
    app._sync_table()
    inspector.refresh_from_editor(force_retrace=True)
    inspector.update_idletasks()
    inspector.update()

    bodies = _filled_body_actors(inspector._renderer)
    visible = [(t, o) for (t, o) in bodies if o >= _VISIBLE_OPACITY]
    # A visible filled body whose whole axial extent is a microns-thick (but
    # strictly positive) slab == the cement bond being drawn (bugs/0046
    # regression). The strictly-positive floor excludes flat reference discs.
    visible_slabs = [
        (round(t, 5), round(o, 3))
        for (t, o) in visible
        if _CEMENT_BAND_MIN_MM <= t < _CEMENT_BAND_MM
    ]
    # The crown (~8 mm) and flint (~5 mm) bodies: visible, comfortably thick.
    visible_thick = [(round(t, 3), round(o, 3)) for (t, o) in visible if t >= 1.0]

    # Rim count: a cemented doublet must show exactly THREE vertical rim lines
    # edge-on -- crown front, the (merged 7.5 um) cemented bond, flint back --
    # matching its 2D profile. Before bugs/0046's rim fix each lens row drew BOTH
    # an optical-cap rim and a mechanical-OD body rim, so the doublet read as 5.
    actor_row: dict[int, int] = {}
    for row_idx, keys in (getattr(inspector, "_row_actor_map", {}) or {}).items():
        for key in keys:
            actor = inspector._actor_by_key.get(key)
            if actor is not None:
                actor_row[id(actor)] = int(row_idx)
    lens_rows = _lens_glass_rows(app.rows)
    rim_zs = _rim_line_zs(inspector._renderer, actor_row, lens_rows)

    # Edge-on render so the result can be eyeballed (the real proof).
    center, span = inspector._row_scene_bounds()
    center = np.asarray(center, dtype=float).reshape(3)
    span = float(span) if np.isfinite(span) and span > 1e-6 else 100.0
    cam = inspector._renderer.GetActiveCamera()
    cam.SetFocalPoint(float(center[0]), float(center[1]), float(center[2]))
    cam.SetPosition(float(center[0] - 4.0 * span), float(center[1]), float(center[2]))
    cam.SetViewUp(0.0, 1.0, 0.0)
    cam.ParallelProjectionOn()
    cam.SetParallelScale(0.32 * span)
    try:
        inspector._renderer.ResetCameraClippingRange()
    except Exception:
        pass
    inspector.update_idletasks()
    inspector.update()
    png = out_dir / "cemented_doublet_rays_on_edge_on.png"
    render_window_to_png(inspector, png)

    non_blank = False
    try:
        from PIL import Image

        arr = np.asarray(Image.open(png).convert("RGB"), dtype=float)
        non_blank = float(np.mean(np.any(arr < 250.0, axis=2))) > 0.01
    except Exception:
        non_blank = png.exists() and png.stat().st_size > 0

    return {
        "visible_slabs": visible_slabs,
        "visible_thick": visible_thick,
        "n_visible_bodies": len(visible),
        "rim_zs": rim_zs,
        "rim_count": len(rim_zs),
        "png": str(png),
        "non_blank": non_blank,
    }


def _evaluate(m) -> tuple[bool, list[str]]:
    """Turn raw live-render metrics into ``(passed, notes)``; notes prefixed
    FAIL/PASS so the comprehensive harness (Phase 51) can fold them in."""
    notes: list[str] = []
    notes.append(f"visible thick (>=1mm) bodies = {m['visible_thick']} (want crown + flint)")
    notes.append(f"visible sub-{_CEMENT_BAND_MM}mm slabs = {m['visible_slabs']} (want none)")
    notes.append(f"lens rim lines (merged) = {m['rim_zs']} (want 3: crown front, bond, flint back)")
    notes.append(f"rendered: {m['png']}")
    failures: list[str] = []
    if m["visible_slabs"]:
        failures.append(
            f"FAIL: a microns-thick cement slab is visible: {m['visible_slabs']} -- the bond layer "
            "is drawn as a standalone body in the live rays-on view (bugs/0046 regression: "
            "open3d_scene_refresh re-inflated the hidden body)"
        )
    if len(m["visible_thick"]) < 2:
        failures.append(
            f"FAIL: expected the crown and flint bodies both visible, got {m['visible_thick']} -- "
            "the fix may have over-suppressed a real element"
        )
    if m["rim_count"] != 3:
        failures.append(
            f"FAIL: doublet drew {m['rim_count']} lens rim lines {m['rim_zs']}, expected 3 "
            "(crown front, cemented bond, flint back) -- the body-drum mechanical-OD rim "
            "regression is back (bugs/0046: each lens row drew both a cap rim and a body rim, "
            "reading as 5)"
        )
    if not m["non_blank"]:
        failures.append(f"FAIL: render is blank at {m['png']}")
    notes.extend(failures)
    if not failures:
        notes.append("PASS: cemented doublet reads as two elements (no cement slab) in the live rays-on view")
    return (not failures), notes


def run_checks(app=None, inspector=None) -> tuple[bool, list[str]]:
    """Boot (or reuse) the live inspector, render the doublet rays-on edge-on, and
    assert no visible cement slab. Returns ``(passed, notes)``; SKIPs (passed=True
    with a SKIP note) when no renderer/Xvfb is available. Phase 51 passes the
    shared harness ``(app, inspector)`` so no second Tk root is created."""
    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import _ensure_display

    out_dir = Path(os.environ.get("KRAKEN_SNAPSHOT_DIR", "/tmp/kraken_cement_doublet_snapshot"))
    out_dir.mkdir(parents=True, exist_ok=True)
    # Only boot a private Xvfb when we have to build our own inspector; a shared
    # inspector (Phase 51) already lives under the harness's display.
    xvfb_proc = None
    if inspector is None:
        xvfb_proc, env_err = _ensure_display()
        if env_err is not None:
            return True, [f"SKIP: cannot render snapshot: {env_err}"]
    try:
        m = _measure(out_dir, app=app, inspector=inspector)
    except Exception as exc:  # a render crash is a real failure, not a skip
        return False, [f"FAIL: live rays-on render raised: {exc!r}"]
    finally:
        if xvfb_proc is not None:
            xvfb_proc.terminate()
            try:
                xvfb_proc.wait(timeout=5)
            except Exception:
                xvfb_proc.kill()
    return _evaluate(m)


def main() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    if not passed:
        print("[FAIL] cemented-doublet rays-on snapshot")
        return 1
    if any(n.startswith("SKIP") for n in notes):
        return 2
    print("[PASS] cemented doublet reads as two elements (no cement slab) in the live rays-on view")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
