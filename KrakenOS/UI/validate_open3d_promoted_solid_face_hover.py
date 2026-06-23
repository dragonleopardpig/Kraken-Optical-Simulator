"""Guard: a promoted optical-solid row hover-highlights each face on idle hover.

bugs/0114 ("After BS promoted, the whole body highlight pink, mouse over each
surface does not highlight it."): after promoting a beam-splitter cube to an
optical solid, hovering the body produced no per-face gold outline. The promoted
body lives in ``_actor_row_map`` (a CAD/STL row), but the idle-hover path only
ran per-face hover for ``_actor_step_map`` STEP overlays (camera/led) -- it had no
branch for a promoted row, so each face stayed un-highlightable.

Fix: the idle-hover path now mirrors Center-Row mode -- when no STEP overlay claims
the cursor it runs ``_row_face_pick_any_for_display_xy`` over the file-backed rows
and builds the per-face gold outline with ``_hover_overlay_for_row_face`` (the same
helpers Center-Row already uses for promoted solids). The promoted body keeps its
selection (pink); the gold face outline layers on top -- hover does NOT deselect.

Two parts:

* ``run_checks`` -- display-free structure + geometry assertions: the idle-hover
  wiring (the bugs/0114 branch), the helper methods exist, the row pick iterates
  file-backed rows (so a promoted solid is found), the branch preserves selection
  (no ``_set_row_highlight`` in the new block), and a planar face's outline is
  non-empty and lands ON the face plane (the gold highlight sits on the body).
* ``render_face_outline_proof`` -- a headless geometry snapshot (pyvista, no GL
  needed) proving a promoted cube-face outline coincides with the body face, plus
  an optional PNG when a GL context is available.

Penta phase 104 (baseline -> 105) runs ``run_checks`` only (no rendering).
"""

from __future__ import annotations

import inspect
import os
from pathlib import Path


def _module_source(module) -> str:
    path = inspect.getsourcefile(module) or inspect.getfile(module)
    return Path(path).read_text()


def _idle_hover_block(interaction_src: str) -> str:
    """Return the idle-hover branch source (where the bugs/0114 fix lives)."""
    marker = "bugs/0114"
    idx = interaction_src.find(marker)
    if idx < 0:
        return ""
    # The bugs/0114 comment sits just above the inserted branch; isolate the branch
    # itself by taking from its ``if step_label is None:`` to the next ``except``.
    start = interaction_src.find("if step_label is None:", idx)
    start = start if start >= 0 else idx
    end = interaction_src.find("except Exception:", start)
    end = end if end >= 0 else start + 1600
    return interaction_src[start:end]


def run_checks() -> list[tuple[str, bool, str]]:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services import open3d_interaction

    results: list[tuple[str, bool, str]] = []

    interaction_src = _module_source(open3d_interaction)
    block = _idle_hover_block(interaction_src)

    # 1) the idle-hover path wires the promoted-row per-face hover (bugs/0114),
    #    gated on no STEP overlay claiming the cursor.
    wiring_ok = (
        "bugs/0114" in interaction_src
        and "if step_label is None:" in block
        and "self._row_face_pick_any_for_display_xy((x, y))" in block
        and "self._hover_overlay_for_row_face(row_index, face)" in block
    )
    results.append(
        ("idle-hover path runs _row_face_pick_any -> _hover_overlay_for_row_face for promoted rows",
         wiring_ok, f"wired={wiring_ok}, block_len={len(block)}")
    )

    # 2) the promoted-row hover branch PRESERVES selection -- it must not clear the
    #    pink row highlight (the gold face outline layers on top of the selection).
    preserves_selection = bool(block) and "_set_row_highlight" not in block
    results.append(
        ("promoted-row hover preserves the selection (no _set_row_highlight in the new branch)",
         preserves_selection, f"no_clear={preserves_selection}")
    )

    # 3) the helper methods the fix relies on exist on the inspector.
    helpers = (
        "_row_face_pick_any_for_display_xy",
        "_hover_overlay_for_row_face",
        "_row_face_ray_pick_for_display_xy",
    )
    missing = [name for name in helpers if not callable(getattr(Kraken3DInspector, name, None))]
    results.append(
        ("inspector exposes the row-face hover helpers",
         not missing, f"missing={missing}")
    )

    # 4) the row picker iterates file-backed rows, so a promoted optical solid
    #    (which keeps its source STL path) is among the hover candidates.
    pick_src = inspect.getsource(Kraken3DInspector._row_face_pick_any_for_display_xy)
    pick_ok = (
        "_file_backed_stl_row_at(int(row_index))" in pick_src
        and "_row_face_ray_pick_for_display_xy(int(row_index)" in pick_src
        and '"row_face_pick"' in pick_src
    )
    results.append(
        ("_row_face_pick_any iterates file-backed rows and returns a row_face_pick",
         pick_ok, f"file_backed_iter={pick_ok}")
    )

    # 5) geometry: a promoted body's planar face yields a non-empty hover outline
    #    that sits ON the face plane (the gold highlight lands on the body, not
    #    floating). Uses the same static outline builder _hover_overlay_for_row_face
    #    feeds (_planar_outline_from_triangles).
    geom_ok = True
    detail5 = ""
    try:
        import numpy as np

        face_z = 246.5  # a promoted BS-cube front face, world z
        half = 39.0
        # a planar quad (the cube face) split into two triangles, all at z=face_z.
        quad = np.array(
            [
                [[-half, -half, face_z], [half, -half, face_z], [half, half, face_z]],
                [[-half, -half, face_z], [half, half, face_z], [-half, half, face_z]],
            ],
            dtype=float,
        )
        outline = Kraken3DInspector._planar_outline_from_triangles(quad, normal_world=(0.0, 0.0, 1.0))
        overlay = Kraken3DInspector._hover_overlay_for_feature(
            np.mean(quad.reshape((-1, 3)), axis=0), outline
        )
        npts = int(getattr(outline, "n_points", 0)) if outline is not None else 0
        zlo = float(outline.bounds[4]) if npts else float("nan")
        zhi = float(outline.bounds[5]) if npts else float("nan")
        on_plane = npts > 0 and abs(zlo - face_z) < 1e-3 and abs(zhi - face_z) < 1e-3
        overlay_pts = int(getattr(overlay, "n_points", 0)) if overlay is not None else 0
        geom_ok = on_plane and overlay_pts > 0
        detail5 = f"outline_pts={npts}, z=[{zlo:.3f},{zhi:.3f}] (face={face_z}), overlay_pts={overlay_pts}"
    except Exception as exc:  # pragma: no cover - pyvista import/driver dependent
        geom_ok = False
        detail5 = f"geometry check errored: {exc}"
    results.append(
        ("a promoted face's hover outline is non-empty and sits ON the face plane",
         geom_ok, detail5)
    )

    return results


def render_face_outline_proof(png_path: str | None = None) -> tuple[bool, str]:
    """Prove a promoted cube face yields a hover outline coincident with the body.

    Geometry proof (headless with pyvista, no GL needed): build a cube-face quad at
    z and assert the planar outline encloses the face footprint and lies on the
    plane. Writes a PNG when a GL context is available.
    """
    import numpy as np
    import pyvista as pv

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    face_z = 246.5
    half = 39.0
    quad = np.array(
        [
            [[-half, -half, face_z], [half, -half, face_z], [half, half, face_z]],
            [[-half, -half, face_z], [half, half, face_z], [-half, half, face_z]],
        ],
        dtype=float,
    )
    body_face = pv.Plane(center=(0, 0, face_z), direction=(0, 0, 1), i_size=2 * half, j_size=2 * half)
    outline = Kraken3DInspector._planar_outline_from_triangles(quad, normal_world=(0.0, 0.0, 1.0))

    npts = int(getattr(outline, "n_points", 0)) if outline is not None else 0
    z_gap = (
        max(abs(float(outline.bounds[4]) - face_z), abs(float(outline.bounds[5]) - face_z))
        if npts
        else float("inf")
    )
    span_x = (float(outline.bounds[1]) - float(outline.bounds[0])) if npts else 0.0
    span_y = (float(outline.bounds[3]) - float(outline.bounds[2])) if npts else 0.0
    encloses = abs(span_x - 2 * half) < 1.0 and abs(span_y - 2 * half) < 1.0
    passed = npts > 0 and z_gap < 1e-3 and encloses

    if png_path and os.environ.get("DISPLAY"):
        try:
            pl = pv.Plotter(off_screen=True, window_size=(360, 360))
            pl.add_mesh(body_face, color=(0.55, 0.7, 0.85), opacity=0.4)
            pl.add_mesh(pv.wrap(outline), color=(0.95, 0.78, 0.05), line_width=4)
            pl.view_xy()
            pl.screenshot(str(png_path))
            pl.close()
        except Exception:
            pass

    detail = f"outline_pts={npts}, z_gap={z_gap:.4f} mm, span=({span_x:.2f},{span_y:.2f}) (face {2*half:.0f} mm)"
    return passed, detail


def main() -> int:
    results = run_checks()
    ok = True
    for name, passed, det in results:
        print(f"{name} | {'PASS' if passed else 'FAIL'} | {det}")
        ok = ok and passed

    try:
        png = os.environ.get("KRAKEN_PROMOTED_FACE_HOVER_PNG") or "/tmp/promoted_solid_face_hover.png"
        passed, det = render_face_outline_proof(png)
        print(f"render proof: promoted face outline lands on the body | {'PASS' if passed else 'FAIL'} | {det}")
        ok = ok and passed
    except Exception as exc:  # pragma: no cover - pyvista/driver dependent
        print(f"render proof skipped (no usable pyvista/GL): {exc}")

    print("[PASS] promoted optical-solid row hover-highlights each face" if ok
          else "[FAIL] promoted optical-solid face hover regressed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
