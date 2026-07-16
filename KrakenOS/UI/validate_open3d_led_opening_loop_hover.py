#!/usr/bin/env python3
"""Display-free guard for bugs/0328 -- plain hover snaps to the NEAREST closed opening
loop's rim, including an INNER hole loop of a wide face.

Context
-------
bugs/0326/0327 made the LED clear-aperture *opening* a deterministic hover target by
snapping to the auto-detected candidate face's rim (F0266 on OPT-ILS0202, the +y tray
slot).  But the recorded flag ("no improvement at all") showed the user pointing at the
central emitting SQUARE on the front (+x) panel -- which is NOT a face of its own; it is
an INNER hole loop of the wide panel face (F0053), ~144 px from F0266.  None of the five
auto-detected candidates lies on the front panel, so the per-face snap locked onto the
wrong opening and hover fell back to the whole panel.

bugs/0328 mines every closed loop from the LARGE faces (``open3d_opening_loops``), drops
each face's outer silhouette, and snaps plain hover to whichever opening rim is nearest
the cursor -- so the central square (a hole loop) is a first-class hover target, honouring
"all closed edges should be detected".

bugs/0329 -- rim proximity alone was a knife-edge: the emitting square is a WIDE opening,
so pointing at its MIDDLE (the natural gesture) sat ~98 px from any rim, missed the snap,
and hover fell through to the whole front panel (which highlights with the opening left as
a HOLE -- the user: "the face can highlight leaving the CA opening not highlighted... just
complement it").  So a CONTAINMENT fallback now snaps to the opening whose projected
polygon the cursor is inside, choosing the one whose projected centroid is nearest -- rim
proximity stays first, so 0328 is preserved exactly.

What this checks (against the real analytic mesh, no OCC, no GLX)
----------------------------------------------------------------
  A. ``opening_loops_for_mesh`` yields the central square (a ~176 mm closed loop that is
     an INNER loop of a large face) and does NOT re-expose that face's outer silhouette.
  B. ``_opening_loop_hover_feature`` returns a LINE-loop overlay (n_lines>0, n_polys==0)
     with a finite centroid/normal and an ``F%03d`` face id.
  C. ``step_feature_pick_for_display_xy`` snaps to the square when the cursor is NEAR its
     projected rim -- with NO cell_id (proving proximity, not cell, drives it).
  D. bugs/0329 interior hit: a cursor at the square CENTRE (inside the projected polygon,
     far from every rim segment) DOES snap to the square -- pointing at the open middle
     highlights the opening, not the surrounding panel.
  E. Selective: a cursor far off-body does NOT return the square feature.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_opening_loop_hover

Exit: 0 = pass (incl. a cache-absent skip), 1 = regression.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

_VTP = Path(
    "attachment/cad_cache/OPT-ILS0202-X-V1.0.2-H_1733802316_6490730.analytic.v2.vtp"
)
_STEP = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP")
# The central emitting square: a rigid-invariant ~176 mm closed loop (perimeter is
# preserved under the scene alignment, so this identifies it in either frame).
_SQUARE_PERIMETER_MM = (150.0, 210.0)
_PROJECT_SCALE = 4.0  # px per mm; makes rim-vs-hole-centre separation unambiguous


class _FakeEditor:
    def __init__(self, mesh):
        self._mesh = mesh

    def _transformed_imported_step_mesh_for_label(self, label):
        return self._mesh

    def step_clear_aperture(self, label):
        return None  # no manual override -> exercise the mined-loop path

    def _step_path_for_label(self, label):
        return str(_STEP)

    def auto_detect_step_clear_aperture_candidates(self, label):
        return []

    def _step_overlay_face_metadata(self, label):
        return {"faces": []}


class _FakeInspector:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as _I

    _opening_loop_hover_feature = _I._opening_loop_hover_feature
    _clear_aperture_opening_face_index = _I._clear_aperture_opening_face_index
    _clear_aperture_opening_edge_feature = _I._clear_aperture_opening_edge_feature
    _clear_aperture_outline = _I._clear_aperture_outline
    _hover_overlay_for_feature = staticmethod(_I._hover_overlay_for_feature)
    _edge_pick_alt_active = False
    _picker = None
    del _I

    def __init__(self, editor, project):
        self.editor = editor
        self._project = project
        self._ca_opening_face_index_cache = {}

    def _world_to_display_2d(self, point):
        return self._project(point)

    def _step_label_is_round_lens_like(self, label):
        return False

    def _coarse_step_face_ray_pick_for_display_xy(self, label, xy):
        return None  # no GLX ray pick in the display-free harness

    def _picked_feature_info_cached(self, *a, **k):
        return None


def _overlay_is_line(overlay) -> bool:
    try:
        return int(overlay.GetNumberOfLines()) > 0 and int(overlay.GetNumberOfPolys()) == 0
    except Exception:
        return False


def _plane_projector(centroid, normal, scale):
    """Orthographic projector onto a loop's own plane (so its rim projects true)."""
    n = np.asarray(normal, dtype=float).reshape(3)
    nl = float(np.linalg.norm(n))
    n = n / nl if nl > 1e-12 else np.asarray([0.0, 0.0, 1.0])
    seed = np.asarray([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.asarray([0.0, 1.0, 0.0])
    u = np.cross(n, seed)
    u = u / (np.linalg.norm(u) + 1e-12)
    v = np.cross(n, u)
    c = np.asarray(centroid, dtype=float).reshape(3)

    def project(point):
        p = np.asarray(point, dtype=float).reshape(-1)
        if p.size < 3 or not np.all(np.isfinite(p[:3])):
            return None
        d = p[:3] - c
        return np.asarray([float(np.dot(d, u)) * scale, float(np.dot(d, v)) * scale])

    return project


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []

    if not _VTP.exists():
        return True, [f"SKIP: analytic cache absent ({_VTP}); regenerate from the LED STEP to run"]

    import pyvista as pv

    from KrakenOS.UI.services.open3d_opening_loops import opening_loops_for_mesh
    from KrakenOS.UI.services.open3d_round_lens_pick import step_feature_pick_for_display_xy

    mesh = pv.read(str(_VTP))

    # A. Mined loops include the central square (an inner hole loop), no outer silhouette.
    loops = opening_loops_for_mesh(mesh)
    if not loops:
        return False, [f"FAIL(A): opening_loops_for_mesh yielded no loops on {_VTP.name}"]
    lo, hi = _SQUARE_PERIMETER_MM
    squares = [lp for lp in loops if lo <= lp.perimeter <= hi]
    if not squares:
        pers = sorted(round(lp.perimeter, 1) for lp in loops)
        return False, [f"FAIL(A): no central-square loop ({lo}-{hi} mm) among mined loops; perimeters={pers}"]
    square = squares[0]
    siblings = [lp for lp in loops if lp.face_index == square.face_index]
    outer = [lp for lp in siblings if lp.perimeter > 400.0]
    if outer:
        failures.append(
            f"FAIL(A): the square's face F{square.face_index:03d} outer silhouette "
            f"(perim {outer[0].perimeter:.0f} mm) was NOT dropped -- it would highlight the whole panel"
        )
    notes.append(
        f"square loop: face=F{square.face_index:03d} perim={square.perimeter:.1f}mm "
        f"area={square.area:.0f}mm^2 loops_total={len(loops)}"
    )

    project = _plane_projector(square.centroid, square.normal, _PROJECT_SCALE)
    editor = _FakeEditor(mesh)
    inspector = _FakeInspector(editor, project)

    # B. The loop's hover feature is a line-loop overlay with finite centroid/normal.
    feat = inspector._opening_loop_hover_feature("led", square)
    if not isinstance(feat, dict):
        failures.append("FAIL(B): _opening_loop_hover_feature returned no feature")
    else:
        triple = feat.get("feature")
        if not (isinstance(triple, tuple) and len(triple) == 3):
            failures.append("FAIL(B): feature is not a (center, overlay, normal) triple")
        else:
            center, overlay, normal = triple
            if not _overlay_is_line(overlay):
                failures.append(
                    "FAIL(B): opening overlay is not a LINE loop (n_lines>0, n_polys==0), got "
                    f"lines={getattr(overlay,'n_lines',None)} polys={getattr(overlay,'n_polys',None)}"
                )
            if not (np.asarray(center).size >= 3 and np.all(np.isfinite(np.asarray(center, float)[:3]))):
                failures.append("FAIL(B): opening centroid is not finite")
            if not str(feat.get("face_id", "")).startswith("F"):
                failures.append(f"FAIL(B): face_id {feat.get('face_id')!r} is not an 'F%03d' id")

    # Cursor positions derived from the projected rim (track the geometry, not pixels).
    rim = np.asarray(square.points, dtype=float).reshape(-1, 3)
    projected = np.asarray([project(p) for p in rim], dtype=float)
    near_xy = tuple(projected[0] + np.asarray([0.0, 6.0]))  # a few px off a rim vertex
    centre_xy = tuple(project(square.centroid))  # inside the hole, far from every rim edge
    far_xy = tuple(np.asarray(centre_xy) + np.asarray([1.0e5, 0.0]))
    square_center = np.asarray(square.centroid, dtype=float).reshape(3)

    def _is_square_hit(hit) -> bool:
        if not isinstance(hit, dict):
            return False
        sc = np.asarray(hit.get("surface_center", []), dtype=float).reshape(-1)
        return sc.size >= 3 and bool(np.allclose(sc[:3], square_center, atol=1e-3))

    # C. Proximity snap: NEAR the square rim, NO cell_id -> the square feature.
    hit = step_feature_pick_for_display_xy(inspector, "led", near_xy)
    if not _is_square_hit(hit):
        got = None if not isinstance(hit, dict) else hit.get("face_id")
        failures.append(
            "FAIL(C): a hover NEAR the projected square rim did NOT snap to the square opening "
            f"(got face_id={got!r}) -- inner-loop proximity snap dead"
        )
    elif not _overlay_is_line(hit["feature"][1]):
        failures.append("FAIL(C): near-rim pick overlay is not the rim edge line")
    else:
        notes.append("near-rim cursor (no cell_id) -> central-square rim edge (proximity snap fires)")

    # D. bugs/0329 interior hit: the hole CENTRE (inside the projected polygon, far from every
    # rim segment) DOES snap to the square -- pointing at the open middle highlights the opening,
    # not the surrounding panel ("just complement it").
    hit_c = step_feature_pick_for_display_xy(inspector, "led", centre_xy)
    if not _is_square_hit(hit_c):
        got = None if not isinstance(hit_c, dict) else hit_c.get("face_id")
        failures.append(
            "FAIL(D): a cursor at the square CENTRE did NOT snap to the square opening "
            f"(got face_id={got!r}) -- the interior-hit containment fallback is dead; hovering "
            "the open middle falls through to the whole panel instead of highlighting the opening"
        )
    elif not _overlay_is_line(hit_c["feature"][1]):
        failures.append("FAIL(D): interior-hit pick overlay is not the rim edge line")
    else:
        notes.append("hole-centre cursor (inside projected square, far from rim) -> central-square opening (containment fallback fires)")

    # E. Selective: a far off-body cursor -- neither near a rim nor inside any projected opening
    # polygon -- must NOT return the square.
    miss = step_feature_pick_for_display_xy(inspector, "led", far_xy)
    if _is_square_hit(miss):
        failures.append(
            "FAIL(E): an off-body cursor wrongly returned the square opening -- the snap is not "
            "selective (it should fire only near a rim or inside the projected opening polygon)"
        )
    else:
        got = None if not isinstance(miss, dict) else miss.get("face_id")
        notes.append(f"off-body cursor -> not the square (face_id={got!r})")

    return (not failures), failures + notes


def main() -> int:
    passed, notes = run_checks()
    hard = [n for n in notes if n.startswith("FAIL")]
    soft = [n for n in notes if not n.startswith("FAIL")]
    if hard:
        print("[FAIL] LED opening-loop hover snap (bugs/0328 rim + bugs/0329 interior)")
        for item in hard:
            print(f"  - {item}")
        return 1
    print("[PASS] LED plain hover snaps to the nearest opening loop by rim proximity, and to the "
          "opening it is hovering INSIDE when far from every rim (bugs/0328 + bugs/0329)")
    for item in soft:
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
