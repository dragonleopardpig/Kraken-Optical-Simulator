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

    return (not failures), failures


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
