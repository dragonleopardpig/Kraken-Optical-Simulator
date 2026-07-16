#!/usr/bin/env python3
"""Display-free guard for bugs/0326+0327 -- plain hover snaps to the LED
clear-aperture opening's RIM EDGE by SCREEN proximity to its closed loop.

Context
-------
The general per-cell face/edge hover pick was brittle on the vendor LED
(OPT-ILS0202): the pixel-varying cell pick made "only a few can be selected",
whole-face highlights read as a "phantom edge", and the Alt-edge mode was flaky
live.  Rather than keep fighting the fuzzy pick, the clear-aperture *opening* is a
deterministic, always-reliable target: ``led_clear_aperture_detect`` finds it
(F267 on this LED).

bugs/0326 gated the snap on the picked CELL landing on the opening face, but the
opening is a see-through hole in a WIDE frame -- a ray under the cursor falls
THROUGH the window onto recessed features behind it (the flag resolved F005, a
sliver ~17 mm back), so the cell gate never fired ("still can't highlight the CA
opening").  bugs/0327 fixes this: the rim is one deterministic CLOSED edge loop,
so select it by SCREEN proximity to that loop -- a big forgiving target that fires
wherever the cursor is near the rim, independent of ``cell_id`` / whatever the ray
hits behind it.  A click inherits that highlight (WYSIWYG), because the click
re-picks through the same feature path.

What this checks (against the real analytic mesh, no OCC, no GLX)
----------------------------------------------------------------
  A. ``_clear_aperture_opening_edge_feature("led", F)`` returns a feature whose
     overlay is a LINE loop (the rim edge: n_lines > 0, n_polys == 0), with a
     finite centroid/normal and face_id ``F%03d``.
  B. The shared ``step_feature_pick_for_display_xy`` snaps to that rim-edge
     feature when the cursor is NEAR the projected rim loop -- with NO ``cell_id``
     supplied (proving the snap is proximity-driven, not cell-driven).
  C. The snap is SELECTIVE: a cursor at the projected HOLE CENTRE (inside the
     see-through opening, far from every rim segment) and a cursor far off-body do
     NOT return the clear-aperture edge feature.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_ca_edge_hover

Exit: 0 = pass (incl. a cache-absent skip), 1 = regression.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

_VTP = Path(
    "attachment/cad_cache/OPT-ILS0202-X-V1.0.2-H_1733802316_6490730.analytic.v2.vtp"
)
_STEP = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP")
_CA_FACE_INDEX = 266  # F267 opening (see validate_open3d_led_clear_aperture_detect)
# The opening normal is +y, so a synthetic "camera" that drops the y axis projects
# the rim to its true ring shape in display space; the scale just makes the
# rim-vs-hole-centre pixel separation unambiguous for the proximity tolerance.
_PROJECT_SCALE = 4.0


def _face_centroid_normal(mesh, face_index, values):
    import pyvista as pv

    surface = pv.wrap(mesh)
    keep = np.where(values == int(face_index))[0]
    v = []
    for cid in keep:
        cell = surface.get_cell(int(cid))
        p = np.asarray(cell.points, dtype=float)
        if p.shape[0] >= 3:
            v.append(p[:3])
    if not v:
        return np.zeros(3), np.asarray([0.0, 0.0, 1.0])
    tris = np.asarray(v, dtype=float)
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
    cross = np.cross(v1 - v0, v2 - v0)
    areas = 0.5 * np.linalg.norm(cross, axis=1)
    total = float(areas.sum()) or 1.0
    centroid = (tris.mean(axis=1) * areas[:, None]).sum(axis=0) / total
    n = cross.sum(axis=0)
    nl = float(np.linalg.norm(n))
    normal = n / nl if nl > 1e-12 else np.asarray([0.0, 0.0, 1.0])
    return centroid, normal


class _FakeEditor:
    def __init__(self, mesh, values):
        self._mesh = mesh
        self._values = values

    def _transformed_imported_step_mesh_for_label(self, label):
        return self._mesh

    def step_clear_aperture(self, label):
        return None  # no manual override -> exercise the auto path

    def _step_path_for_label(self, label):
        return str(_STEP)

    def auto_detect_step_clear_aperture_candidates(self, label):
        class _Cand:
            face_index = _CA_FACE_INDEX
            area_mm2 = 700.0

        return [_Cand()]

    def clear_aperture_face_index_for_display_cell(self, label, cell_id):
        from KrakenOS.UI.services.open3d_face_index_edges import (
            face_index_for_display_cell,
        )

        return face_index_for_display_cell(self._mesh, int(cell_id))

    def _step_overlay_fine_face_centroid_normal(self, label, face_index):
        c, n = _face_centroid_normal(self._mesh, int(face_index), self._values)
        return np.asarray(c), np.asarray(n), 1.0

    def _step_overlay_face_metadata(self, label):
        return {"faces": []}


class _FakeInspector:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as _I

    _clear_aperture_opening_face_index = _I._clear_aperture_opening_face_index
    _clear_aperture_opening_edge_feature = _I._clear_aperture_opening_edge_feature
    _clear_aperture_outline = _I._clear_aperture_outline
    _hover_overlay_for_feature = staticmethod(_I._hover_overlay_for_feature)
    _edge_pick_alt_active = False
    _picker = None
    del _I

    def __init__(self, editor):
        self.editor = editor
        self._ca_opening_face_index_cache = {}

    def _world_to_display_2d(self, point):
        # Synthetic orthographic camera looking down the opening's +y normal.
        p = np.asarray(point, dtype=float).reshape(-1)
        if p.size < 3 or not np.all(np.isfinite(p[:3])):
            return None
        return np.asarray([p[0] * _PROJECT_SCALE, p[2] * _PROJECT_SCALE], dtype=float)

    def _step_label_is_round_lens_like(self, label):
        return False

    def _coarse_step_face_ray_pick_for_display_xy(self, label, xy):
        return None

    def _picked_feature_info_cached(self, *a, **k):
        return None


def _overlay_is_line(overlay) -> bool:
    # Mirror the render decision in _set_step_hover_outline_impl, which keys on
    # vtkPolyData.GetNumberOfPolys() -- polys => translucent FILL, lines-only =>
    # gold EDGE tubes. The rim edge must be lines-only so it renders as an EDGE.
    try:
        return int(overlay.GetNumberOfLines()) > 0 and int(overlay.GetNumberOfPolys()) == 0
    except Exception:
        return False


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []

    if not _VTP.exists():
        return True, [f"SKIP: analytic cache absent ({_VTP}); regenerate from the LED STEP to run"]

    import pyvista as pv

    from KrakenOS.UI.services.open3d_face_index_edges import _cell_face_index_values
    from KrakenOS.UI.services.open3d_round_lens_pick import step_feature_pick_for_display_xy

    mesh = pv.read(str(_VTP))
    surface = pv.wrap(mesh)
    n_cells = int(surface.n_cells)
    values = np.asarray(_cell_face_index_values(surface, n_cells), dtype=int)

    opening_cells = np.where(values == _CA_FACE_INDEX)[0]
    if opening_cells.size == 0:
        return False, [f"FAIL: no cells with face index {_CA_FACE_INDEX} in {_VTP.name}"]

    editor = _FakeEditor(mesh, values)
    inspector = _FakeInspector(editor)

    # A. Direct edge-feature builder.
    feat = inspector._clear_aperture_opening_edge_feature("led", _CA_FACE_INDEX)
    if not isinstance(feat, dict):
        failures.append("FAIL(A): _clear_aperture_opening_edge_feature returned no feature")
    else:
        if feat.get("face_id") != f"F{_CA_FACE_INDEX:03d}":
            failures.append(f"FAIL(A): face_id {feat.get('face_id')!r} != 'F{_CA_FACE_INDEX:03d}'")
        triple = feat.get("feature")
        if not (isinstance(triple, tuple) and len(triple) == 3):
            failures.append("FAIL(A): feature is not a (center, overlay, normal) triple")
        else:
            center, overlay, normal = triple
            if not _overlay_is_line(overlay):
                failures.append(
                    "FAIL(A): opening overlay is not a LINE loop -- the rim EDGE must render as an "
                    "edge (n_lines>0, n_polys==0), got "
                    f"lines={getattr(overlay,'n_lines',None)} polys={getattr(overlay,'n_polys',None)}"
                )
            if not (np.asarray(center).size >= 3 and np.all(np.isfinite(np.asarray(center, float)[:3]))):
                failures.append("FAIL(A): opening centroid is not finite")
            if not (np.asarray(normal).size >= 3 and np.all(np.isfinite(np.asarray(normal, float)[:3]))):
                failures.append("FAIL(A): opening normal is not finite")
            notes.append(
                f"opening edge: face_id={feat.get('face_id')} "
                f"lines={int(overlay.GetNumberOfLines())} polys={int(overlay.GetNumberOfPolys())}"
            )

    # Derive cursor positions from the projected rim loop (the same outline the
    # pick path builds), so the test tracks the real geometry, not magic pixels.
    outline = inspector._clear_aperture_outline("led", _CA_FACE_INDEX)
    rim_pts = np.asarray(outline.points, dtype=float).reshape((-1, 3))
    projected = np.asarray(
        [inspector._world_to_display_2d(p) for p in rim_pts], dtype=float
    )
    rim_center_xy = projected.mean(axis=0)
    # A cursor a few px off an actual rim vertex -- NEAR the loop; no cell_id given.
    near_xy = tuple(projected[0] + np.asarray([0.0, 6.0]))
    # The projected hole centre: inside the see-through opening, far from every rim
    # segment -- exactly where the flagged ray fell THROUGH onto a recessed face.
    center_xy = tuple(rim_center_xy)
    far_xy = tuple(rim_center_xy + np.asarray([1.0e5, 0.0]))

    # B. Proximity snap: NEAR the rim, with NO cell_id supplied (proximity, not cell).
    hit = step_feature_pick_for_display_xy(inspector, "led", near_xy)
    if not isinstance(hit, dict) or hit.get("face_id") != f"F{_CA_FACE_INDEX:03d}":
        failures.append(
            "FAIL(B): a hover NEAR the projected rim loop did NOT snap to the clear-aperture edge "
            f"(got {None if hit is None else hit.get('face_id')!r}) -- proximity trigger dead"
        )
    elif not _overlay_is_line(hit["feature"][1]):
        failures.append("FAIL(B): near-rim pick overlay is not the rim edge line")
    else:
        notes.append("near-rim cursor (no cell_id) -> clear-aperture rim edge (proximity snap fires)")

    # C. Selective: the hole centre and a far cursor must NOT return the CA edge.
    for tag, xy in (("hole-centre", center_xy), ("off-body", far_xy)):
        miss = step_feature_pick_for_display_xy(inspector, "led", xy)
        miss_id = None if not isinstance(miss, dict) else miss.get("face_id")
        if miss_id == f"F{_CA_FACE_INDEX:03d}":
            failures.append(
                f"FAIL(C): a {tag} cursor wrongly returned the clear-aperture edge -- the proximity "
                "snap is not selective (it should fire only near the rim)"
            )
        else:
            notes.append(f"{tag} cursor -> not the CA edge (face_id={miss_id!r})")

    return (not failures), failures + notes


def main() -> int:
    passed, notes = run_checks()
    hard = [n for n in notes if n.startswith("FAIL")]
    soft = [n for n in notes if not n.startswith("FAIL")]
    if hard:
        print("[FAIL] LED clear-aperture opening edge hover (bugs/0326+0327)")
        for item in hard:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] LED clear-aperture opening edge snaps on screen-proximity to its rim loop "
        "(bugs/0326+0327)"
    )
    for item in soft:
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
