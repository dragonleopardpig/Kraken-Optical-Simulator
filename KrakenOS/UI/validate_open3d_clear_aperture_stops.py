"""Display-free guard for bugs/0379 -- user-specified physical clear-aperture (CA) stops.

A decoration STEP overlay (coaxial LED, camera, mount) carries real CA openings the trace
ignores. This pins the geometry primitive: an aperture built from PICKED EDGES -- a closed
window loop, three sides of an open opening, or two opposite mount edges -- all yield the
SAME rectangle at its true plane, and rays missing the opening are vignetted.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_clear_aperture_stops
"""

from __future__ import annotations

import numpy as np


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    from KrakenOS.UI.services.clear_aperture_stops import (
        filter_illumination_records,
        ray_passes_apertures,
        rect_from_edges,
    )

    # A 51 x 51.5 mm rectangle in the z=100 plane, centred at (10, -5, 100).
    cx, cy, cz, hu, hv = 10.0, -5.0, 100.0, 25.5, 25.75
    C = {
        "TL": (cx - hu, cy + hv, cz), "TR": (cx + hu, cy + hv, cz),
        "BR": (cx + hu, cy - hv, cz), "BL": (cx - hu, cy - hv, cz),
    }

    def edge(a, b, n=8):
        return np.linspace(np.array(C[a]), np.array(C[b]), n)

    def _rect_ok(rect, tag):
        if rect is None:
            failures.append(f"{tag}: rect_from_edges returned None")
            return
        halves = sorted([rect["half_u"], rect["half_v"]])
        if abs(halves[0] - 25.5) > 0.05 or abs(halves[1] - 25.75) > 0.05:
            failures.append(f"{tag}: wrong extent {halves} (expected ~25.5 x 25.75)")
        if np.linalg.norm(np.asarray(rect["center"]) - [cx, cy, cz]) > 0.05:
            failures.append(f"{tag}: wrong centre {rect['center']} (expected {[cx, cy, cz]})")

    _rect_ok(rect_from_edges([edge("TL", "TR"), edge("TR", "BR"), edge("BR", "BL"), edge("BL", "TL")]), "closed loop")
    _rect_ok(rect_from_edges([edge("TL", "TR"), edge("TR", "BR"), edge("BR", "BL")]), "3 edges")
    _rect_ok(rect_from_edges([edge("TL", "TR"), edge("BR", "BL")]), "2 opposite edges")
    if rect_from_edges([np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])]) is not None:
        failures.append("a single collinear edge (< a rectangle) must return None")

    # --- RAY STOP -----------------------------------------------------------------
    ca = rect_from_edges([edge("TL", "TR"), edge("TR", "BR"), edge("BR", "BL")])
    thru = np.array([[10, -5, 0], [10, -5, 200]])          # through the centre
    miss = np.array([[100, -5, 0], [100, -5, 200]])        # far outside the opening
    if not ray_passes_apertures(thru, [ca]):
        failures.append("a ray through the opening centre must pass")
    if ray_passes_apertures(miss, [ca]):
        failures.append("a ray crossing the plane outside the opening must be blocked")
    # a ray that never reaches the CA plane is not blocked by it
    away = np.array([[10, -5, 300], [10, -5, 400]])
    if not ray_passes_apertures(away, [ca]):
        failures.append("a ray that never reaches the CA plane must not be blocked")

    # --- FILTER -------------------------------------------------------------------
    recs = [
        {"traced_polyline_world": thru.tolist()},
        {"traced_polyline_world": np.array([[10, 10, 0], [10, 10, 200]]).tolist()},  # inside
        {"traced_polyline_world": miss.tolist()},                                     # outside
        {"traced_polyline_world": np.array([[10, 100, 0], [10, 100, 200]]).tolist()},# outside
        {"no_polyline": True},                                                        # kept (nothing to test)
    ]
    kept = filter_illumination_records(recs, [ca])
    if len(kept) != 3:
        failures.append(f"filter kept {len(kept)} records, expected 3 (2 miss the opening, 1 has no polyline)")
    if filter_illumination_records(recs, []) != recs:
        failures.append("no CAs -> the records must pass through unchanged")

    _check_face_store_ray_stop(failures)
    _check_persistence_round_trip(failures)

    return (not failures), failures


def _check_persistence_round_trip(failures: list[str]) -> None:
    """A stored edge-picked CA rectangle must survive save/reload (bugs/0379). Exercises
    the exact serialize helper + restore filter the layout snapshot/restore blocks use,
    so a rect round-trips and a malformed entry is dropped rather than corrupting the
    layout file. (The full GUI _collect/_apply need Tk vars; this pins the data path.)"""
    try:
        from KrakenOS.UI.services.clear_aperture_stops import rect_from_edges
        from KrakenOS.UI.services.layout_settings import _portable_clear_aperture_rect
    except Exception as exc:
        failures.append(f"persistence: import failed ({exc!r})")
        return

    cx, cy, cz, hu, hv = 10.0, -5.0, 100.0, 25.5, 25.75
    corners = {
        "TL": (cx - hu, cy + hv, cz), "TR": (cx + hu, cy + hv, cz),
        "BR": (cx + hu, cy - hv, cz), "BL": (cx - hu, cy - hv, cz),
    }

    def edge(a, b):
        return np.linspace(np.array(corners[a]), np.array(corners[b]), 8)

    rect = rect_from_edges([edge("TL", "TR"), edge("TR", "BR"), edge("BR", "BL")])
    # Serialize as _collect_layout_settings does; restore as _apply_layout_settings does.
    saved = {"led": [_portable_clear_aperture_rect(rect), _portable_clear_aperture_rect({"bad": 1})]}
    restored: dict = {}
    for k, v in saved.items():
        kept = [r for r in (_portable_clear_aperture_rect(item) for item in v) if r]
        if kept:
            restored[str(k).strip().lower()] = kept
    if list(restored.keys()) != ["led"] or len(restored["led"]) != 1:
        failures.append(f"persistence: round-trip kept {restored!r}, expected one 'led' rect (malformed dropped)")
        return
    got = restored["led"][0]
    halves = sorted([got["half_u"], got["half_v"]])
    if abs(halves[0] - 25.5) > 0.05 or abs(halves[1] - 25.75) > 0.05:
        failures.append(f"persistence: restored extent {halves} (expected ~25.5 x 25.75)")


def _check_face_store_ray_stop(failures: list[str]) -> None:
    """The EXISTING face-based CA (bugs/0134 'pick window face') must become a REAL ray
    stop: its recorded window face -> world outline -> rectangle, unified with any
    edge-picked rects in ``_clear_aperture_stop_rects``. Needs pyvista for a synthetic
    analytic mesh; skipped (not failed) when unavailable so the pure geometry contract
    above still runs everywhere."""
    try:
        import pyvista as pv  # noqa: F401
        from KrakenOS.UI.services.open3d_face_index_edges import (
            FACE_INDEX_CELL_DATA,
            face_outline_from_face_indices,
        )
        from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin
        from KrakenOS.UI.services.clear_aperture_stops import rect_from_edges
    except Exception:
        return  # pyvista/VTK not importable in this environment -- skip cleanly.

    # A 51 x 51.5 window face (2 triangles, face 0) in z=100, centred (10, -5, 100).
    cx, cy, cz, hu, hv = 10.0, -5.0, 100.0, 25.5, 25.75
    pts = np.array(
        [[cx - hu, cy - hv, cz], [cx + hu, cy - hv, cz],
         [cx + hu, cy + hv, cz], [cx - hu, cy + hv, cz]], dtype=float
    )
    mesh = pv.PolyData(pts, np.hstack([[3, 0, 1, 2], [3, 0, 2, 3]]))
    mesh.cell_data[FACE_INDEX_CELL_DATA] = np.array([0, 0], dtype=np.int64)

    outline = face_outline_from_face_indices(mesh, (0,))
    if outline is None or np.asarray(outline.points).shape[0] < 3:
        failures.append("face-store: window-face outline did not resolve")
        return
    rect = rect_from_edges([np.asarray(outline.points)])
    if rect is None:
        failures.append("face-store: rect_from_edges(outline) returned None")
        return
    halves = sorted([rect["half_u"], rect["half_v"]])
    if abs(halves[0] - 25.5) > 0.05 or abs(halves[1] - 25.75) > 0.05:
        failures.append(f"face-store: window-face rect extent {halves} (expected ~25.5 x 25.75)")

    class _FakeEditor(ThreeDSceneToolsMixin):
        def __init__(self):
            self._step_clear_aperture_by_label = {"led": {"face_index": 0, "area_mm2": 2626.0}}
            self._clear_aperture_rects_by_label = {
                "led": [{"center": [0, 0, 50], "normal": [0, 0, 1],
                         "u_axis": [1, 0, 0], "v_axis": [0, 1, 0],
                         "half_u": 27.0, "half_v": 37.0}]
            }

        def _clear_aperture_store(self):
            return self._step_clear_aperture_by_label

        def _transformed_imported_step_mesh_for_label(self, label):
            return mesh

    editor = _FakeEditor()
    rects = editor._clear_aperture_stop_rects()
    if len(rects) != 2:
        failures.append(
            f"unified stop rects = {len(rects)}, expected 2 (1 picked face + 1 edge rect)"
        )
    # The face-derived stop must vignette a ray that misses the window.
    from KrakenOS.UI.services.clear_aperture_stops import ray_passes_apertures

    face_rect = editor._clear_aperture_rect_from_face_record("led", {"face_index": 0})
    if face_rect is not None:
        thru = np.array([[cx, cy, 0.0], [cx, cy, 200.0]])
        miss = np.array([[cx + 200.0, cy, 0.0], [cx + 200.0, cy, 200.0]])
        if not ray_passes_apertures(thru, [face_rect]):
            failures.append("face-store: a ray through the window centre must pass")
        if ray_passes_apertures(miss, [face_rect]):
            failures.append("face-store: a ray missing the window must be vignetted")


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Clear-aperture-stops validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Clear-aperture-stops validation passed: a CA rectangle built from a closed loop, "
        "3 edges, or 2 opposite edges is the same opening at its true plane; rays missing "
        "the opening are vignetted; records with no polyline (and the no-CA case) pass through."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
