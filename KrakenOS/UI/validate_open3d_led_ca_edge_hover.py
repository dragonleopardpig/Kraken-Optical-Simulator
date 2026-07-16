#!/usr/bin/env python3
"""Display-free guard for bugs/0326 -- plain hover snaps to the LED clear-aperture
opening's RIM EDGE.

Context
-------
The general per-cell face/edge hover pick was brittle on the vendor LED
(OPT-ILS0202): the pixel-varying cell pick made "only a few can be selected",
whole-face highlights read as a "phantom edge", and the Alt-edge mode was flaky
live.  Rather than keep fighting the fuzzy pick, the clear-aperture *opening* is a
deterministic, always-reliable target: ``led_clear_aperture_detect`` finds it
(F267 on this LED), so plain hover over the opening should highlight its rim EDGE
directly -- no Alt, no per-pixel ambiguity -- and a click inherits that highlight
(WYSIWYG), because the click re-picks through the same feature path.

What this checks (against the real analytic mesh, no OCC, no GLX)
----------------------------------------------------------------
  A. ``_clear_aperture_opening_edge_feature("led", F)`` returns a feature whose
     overlay is a LINE loop (the rim edge: n_lines > 0, n_polys == 0), with a
     finite centroid/normal and face_id ``F%03d``.
  B. The shared ``step_feature_pick_for_display_xy`` SHORT-CIRCUITS to that edge
     feature when the picked cell lands on the opening face group.
  C. The short-circuit is SELECTIVE: a cell on a different face group does NOT
     return the clear-aperture edge feature.

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
    other_cells = np.where((values >= 0) & (values != _CA_FACE_INDEX))[0]
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

    # B. Full pick short-circuits on an opening cell.
    hit = step_feature_pick_for_display_xy(
        inspector, "led", (0.0, 0.0), cell_id=int(opening_cells[0])
    )
    if not isinstance(hit, dict) or hit.get("face_id") != f"F{_CA_FACE_INDEX:03d}":
        failures.append(
            "FAIL(B): a hover on the opening cell did NOT short-circuit to the clear-aperture edge "
            f"(got {None if hit is None else hit.get('face_id')!r})"
        )
    elif not _overlay_is_line(hit["feature"][1]):
        failures.append("FAIL(B): opening-cell pick overlay is not the rim edge line")
    else:
        notes.append("opening-cell pick -> clear-aperture rim edge (short-circuit fires)")

    # C. Selective: a non-opening cell must NOT return the clear-aperture edge.
    if other_cells.size:
        miss = step_feature_pick_for_display_xy(
            inspector, "led", (0.0, 0.0), cell_id=int(other_cells[0])
        )
        miss_id = None if not isinstance(miss, dict) else miss.get("face_id")
        if miss_id == f"F{_CA_FACE_INDEX:03d}":
            failures.append(
                "FAIL(C): a hover on a NON-opening cell wrongly returned the clear-aperture edge -- "
                "the short-circuit is not selective"
            )
        else:
            notes.append(f"non-opening cell -> not the CA edge (face_id={miss_id!r})")

    return (not failures), failures + notes


def main() -> int:
    passed, notes = run_checks()
    hard = [n for n in notes if n.startswith("FAIL")]
    soft = [n for n in notes if not n.startswith("FAIL")]
    if hard:
        print("[FAIL] LED clear-aperture opening edge hover (bugs/0326)")
        for item in hard:
            print(f"  - {item}")
        return 1
    print("[PASS] LED clear-aperture opening edge is a deterministic plain-hover target (bugs/0326)")
    for item in soft:
        print(f"  - {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
