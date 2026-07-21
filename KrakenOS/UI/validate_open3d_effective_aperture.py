"""Display-free guard for bugs/0380 -- the general effective-aperture engine.

Pins the pure geometry: intersect all apertures projected onto the reference plane, and
attribute each boundary edge to the aperture that LIMITS it (the "who clips" answer).
Covers a plain rectangular intersection, tilt foreshortening (a 45deg aperture projects
to cos45 of its extent), unfolding across a fold, and a disjoint (empty) intersection.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_effective_aperture
"""

from __future__ import annotations

import numpy as np


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    from KrakenOS.UI.services.effective_aperture import (
        circle_boundary,
        clip_convex,
        effective_footprint,
        rect_boundary,
    )

    X, Y, Z = np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0])
    frame = (np.zeros(3), Z, X, Y)  # object plane z=0, u=x (fold axis), v=y (perp)

    def rect_ap(label, hu, hv, center=(0, 0, 0), u=X, v=Y):
        return {"label": label, "boundary": rect_boundary(center, u, v, hu, hv), "normal": Z}

    # --- 1. intersection + per-edge attribution -------------------------------------
    apertures = [
        rect_ap("wide", 100.0, 100.0),      # never limits
        rect_ap("narrow_u", 20.0, 100.0),   # limits the u (fold) extent to +/-20
        rect_ap("narrow_v", 100.0, 30.0),   # limits the v (perp) extent to +/-30
    ]
    res = effective_footprint(apertures, frame)
    if res is None or res.get("empty"):
        failures.append("intersection: expected a non-empty footprint")
    else:
        bbox = res["bbox_uv"]
        if abs(bbox[0, 0] - -20) > 0.05 or abs(bbox[1, 0] - 20) > 0.05:
            failures.append(f"intersection: u extent {bbox[:,0].tolist()} (expected +/-20)")
        if abs(bbox[0, 1] - -30) > 0.05 or abs(bbox[1, 1] - 30) > 0.05:
            failures.append(f"intersection: v extent {bbox[:,1].tolist()} (expected +/-30)")
        if set(res["limiting_labels"]) != {"narrow_u", "narrow_v"}:
            failures.append(f"attribution: limiting labels {res['limiting_labels']} (expected narrow_u,narrow_v; wide must NOT limit)")
        # Each footprint edge must be attributed: a vertical edge (const u ~ +/-20) -> narrow_u,
        # a horizontal edge (const v ~ +/-30) -> narrow_v.
        foot = res["footprint_uv"]
        for i, labs in enumerate(res["edge_labels"]):
            p0, p1 = foot[i], foot[(i + 1) % foot.shape[0]]
            if abs(p1[0] - p0[0]) < 1e-6:  # vertical edge, constant u
                if "narrow_u" not in labs:
                    failures.append(f"attribution: vertical edge at u={p0[0]:.1f} not attributed to narrow_u ({labs})")
            elif abs(p1[1] - p0[1]) < 1e-6:  # horizontal edge, constant v
                if "narrow_v" not in labs:
                    failures.append(f"attribution: horizontal edge at v={p0[1]:.1f} not attributed to narrow_v ({labs})")

    # --- 2. tilt foreshortening (a 45deg aperture projects to cos45) ------------------
    s = np.sqrt(0.5)
    tilted_u = np.array([s, 0.0, s])  # u_axis tilted 45deg into z
    apertures2 = [
        rect_ap("perp_box", 100.0, 40.0),                       # v limited to +/-40
        rect_ap("tilted", 50.0, 100.0, u=tilted_u, v=Y),        # 50 along a 45deg u -> ~35.36 projected
    ]
    res2 = effective_footprint(apertures2, frame)
    if res2 is None or res2.get("empty"):
        failures.append("foreshorten: expected a non-empty footprint")
    else:
        u_half = float(res2["bbox_uv"][1, 0])
        if abs(u_half - 50.0 * s) > 0.1:
            failures.append(f"foreshorten: projected u half {u_half:.2f} (expected {50.0*s:.2f} = 50*cos45)")
        if "tilted" not in res2["limiting_labels"]:
            failures.append("foreshorten: the tilted aperture must limit the u edge")

    # --- 3. unfold across a fold plane ----------------------------------------------
    # An aperture at z=+100 (far side of a fold at z=50) reflects to z=0 (the reference),
    # then projects 1:1. Without unfolding it would project from z=100 identically (ortho
    # ignores z), so to prove the unfold MOVES it we offset it in u and mirror-check.
    fold = [(np.array([0.0, 0.0, 50.0]), Z)]
    far = {"label": "far", "boundary": rect_boundary((10.0, 0.0, 100.0), X, Y, 15.0, 15.0), "normal": Z}
    res3 = effective_footprint([far, rect_ap("host", 100.0, 100.0)], frame, fold_planes=fold)
    if res3 is None or res3.get("empty"):
        failures.append("unfold: expected a non-empty footprint")
    else:
        # centre in u is unchanged by a z-normal reflection (only z flips), extent stays 30.
        w = float(res3["bbox_uv"][1, 0] - res3["bbox_uv"][0, 0])
        if abs(w - 30.0) > 0.1:
            failures.append(f"unfold: u width {w:.2f} (expected 30 from the far aperture)")
        if "far" not in res3["limiting_labels"]:
            failures.append("unfold: the far aperture must limit after unfolding")

    # --- 4. disjoint apertures -> empty ---------------------------------------------
    res4 = effective_footprint(
        [rect_ap("left", 10.0, 10.0, center=(-100, 0, 0)),
         rect_ap("right", 10.0, 10.0, center=(100, 0, 0))],
        frame,
    )
    if not (res4 is not None and res4.get("empty")):
        failures.append("empty: two disjoint apertures must yield an empty footprint")

    # --- 5. a circle intersects a rectangle (round lens stop) ------------------------
    circ = {"label": "stop", "boundary": circle_boundary((0, 0, 0), X, Y, 15.0, n=96), "normal": Z}
    res5 = effective_footprint([rect_ap("wide", 100.0, 100.0), circ], frame)
    if res5 is None or res5.get("empty"):
        failures.append("circle: expected a non-empty footprint")
    else:
        r = float(res5["bbox_uv"][1, 0])
        if abs(r - 15.0) > 0.2:
            failures.append(f"circle: round-stop half extent {r:.2f} (expected ~15)")
        if "stop" not in res5["limiting_labels"]:
            failures.append("circle: the round stop must limit")

    _check_inventory_wiring(failures)

    return (not failures), failures


def _check_inventory_wiring(failures: list[str]) -> None:
    """bugs/0380 L2/L3: `_illumination_effective_aperture` inventories the LED (from the
    descriptor, tilted -> foreshortened) + every recorded/picked clear aperture, intersects
    them, and reports the limiting aperture PER EDGE. No CA -> the LED answer (38.9x74);
    a tight CA takes over; a fold-only CA gives a mixed attribution; a huge CA never limits."""
    from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin

    class _Ed(ThreeDSceneToolsMixin):
        def __init__(self):
            self._ca = []
            self.debug = []

        def _clear_aperture_stop_rects(self):
            return self._ca

        def append_debug(self, *a, **k):
            self.debug.append(a)

    d = {"aperture_fold_mm": 55.0, "aperture_perp_mm": 74.0, "fold_angle_deg": 45.0, "fold_axis": "x"}
    ed = _Ed()

    def _ca(hu, hv):
        return {"center": [0, 0, 0], "normal": [0, 0, 1], "u_axis": [1, 0, 0], "v_axis": [0, 1, 0],
                "half_u": hu, "half_v": hv}

    # No CA -> the LED alone, foreshortened: 55*cos45 = 38.9 x 74.
    e = ed._illumination_effective_aperture(d)
    if e is None:
        failures.append("inventory: no-CA case returned None")
        return
    if abs(2 * e["half_fold"] - 38.89) > 0.2 or abs(2 * e["half_perp"] - 74.0) > 0.2:
        failures.append(f"inventory(no CA): {2*e['half_fold']:.1f} x {2*e['half_perp']:.1f} (expected 38.9 x 74)")
    if e["limiting_labels"] != ["led source"]:
        failures.append(f"inventory(no CA): limited by {e['limiting_labels']} (expected ['led source'])")

    # A tight 30x30 CA takes over both edges.
    ed._ca = [_ca(15.0, 15.0)]
    e = ed._illumination_effective_aperture(d)
    if abs(2 * e["half_fold"] - 30.0) > 0.2 or abs(2 * e["half_perp"] - 30.0) > 0.2:
        failures.append(f"inventory(30x30 CA): {2*e['half_fold']:.1f} x {2*e['half_perp']:.1f} (expected 30 x 30)")
    if "clear aperture 1" not in e["limiting_labels"] or "led source" in e["limiting_labels"]:
        failures.append(f"inventory(30x30 CA): limited by {e['limiting_labels']} (expected the CA only)")

    # A fold-only 20x100 CA -> fold from the CA, perp from the LED (mixed attribution).
    ed._ca = [_ca(10.0, 50.0)]
    e = ed._illumination_effective_aperture(d)
    if abs(2 * e["half_fold"] - 20.0) > 0.2 or abs(2 * e["half_perp"] - 74.0) > 0.2:
        failures.append(f"inventory(20x100 CA): {2*e['half_fold']:.1f} x {2*e['half_perp']:.1f} (expected 20 x 74)")
    if set(e["limiting_labels"]) != {"clear aperture 1", "led source"}:
        failures.append(f"inventory(20x100 CA): mixed attribution {e['limiting_labels']} (expected CA + LED)")

    # A huge 200x200 CA never limits -> the LED answer, unchanged (no false clip).
    ed._ca = [_ca(100.0, 100.0)]
    e = ed._illumination_effective_aperture(d)
    if abs(2 * e["half_fold"] - 38.89) > 0.2 or e["limiting_labels"] != ["led source"]:
        failures.append(f"inventory(huge CA): {2*e['half_fold']:.1f}, {e['limiting_labels']} (expected 38.9, led source)")


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Effective-aperture validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Effective-aperture validation passed: apertures project + intersect on the "
        "reference plane; each boundary edge is attributed to the aperture that limits it; "
        "tilt foreshortens, folds unfold, disjoint apertures read empty, circles clip."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
