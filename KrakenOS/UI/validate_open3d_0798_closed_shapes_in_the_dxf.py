"""bugs/0798 -- the DXF's shapes must close.

User, on attachment/MV-CH120-60UM_WWK10-110CP-111V3_view.dxf: "the DXF output, there are many
unclosed edges, they are supposed to be closed shape."

Two defects, both in how the viewport export assembles its line art:

1. ``mesh_outline_strips`` unions THREE silhouettes at perturbed view directions (bugs/0650
   round 6, so a contour edge lost at one direction's tangency threshold is caught by a
   neighbour). Each tilt puts the silhouette on DIFFERENT mesh edges, so every contour arrived
   three times about 0.1 mm apart -- measured on the user's scene, 129386 mm of raw line for
   46156 mm of unique geometry.
2. ``merge_collinear_segments_2d`` then had to collapse those copies, and emitted every result
   as ``d * t + normal * mean_offset`` -- a line REBUILT on the cluster's reference direction at
   the group's mean offset. So it moved endpoints, including endpoints that were exactly
   coincident: of 2854 joinable endpoints in one real colour bucket, 13 survived. The two arms
   of a corner sit in different angle clusters, were moved independently, and no longer met.

Display-free: synthetic geometry only, no app, no VTK, no rendering.
"""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.services.dxf_viewport_export import (  # noqa: E402
    _strips_not_already_drawn,
    merge_collinear_segments_2d,
    stitch_strips_2d,
)


def _box(width: float = 50.0, height: float = 40.0) -> list[np.ndarray]:
    return [
        np.array([[0.0, 0.0], [width, 0.0]]),
        np.array([[width, 0.0], [width, height]]),
        np.array([[width, height], [0.0, height]]),
        np.array([[0.0, height], [0.0, 0.0]]),
    ]


def _with_copies(segments: list[np.ndarray], offset: float) -> list[np.ndarray]:
    """The duplicated contour a perturbed silhouette pass produces."""
    out = list(segments)
    for seg in segments:
        a, b = np.asarray(seg, float)
        d = b - a
        n = np.array([-d[1], d[0]])
        n = n / (np.linalg.norm(n) or 1.0)
        out.append(np.array([a + n * offset, b + n * offset]))
    return out


def _endpoint_set(segments) -> set[tuple[int, int]]:
    keys = set()
    for seg in segments:
        a = np.asarray(seg, float)
        for p in (a[0], a[-1]):
            keys.add((round(float(p[0]) * 1e6), round(float(p[1]) * 1e6)))
    return keys


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    # ---- A: the merge may union intervals, never INVENT a point ---------------------------
    # The pre-0798 code emitted d * t + normal * mean_offset, so a duplicate-rich cluster
    # produced coordinates that appear nowhere in its input. That is what moved corners.
    duplicated = _with_copies(_box(), 0.025)
    merged = merge_collinear_segments_2d(duplicated)
    given = _endpoint_set(duplicated)
    produced = _endpoint_set(merged)
    invented = produced - given
    ok(not invented,
       f"A: every endpoint the merge emits is one it was given "
       f"({len(produced)} out, {len(invented)} invented)")

    # a lone segment beside a near-parallel neighbour must come back as ITSELF
    pair = [np.array([[0.0, 0.0], [50.0, 0.0]]), np.array([[0.0, 0.02], [50.0, 0.0201]])]
    out = merge_collinear_segments_2d(pair)
    ok(all(not (_endpoint_set([s]) - _endpoint_set(pair)) for s in out),
       "A: a near-parallel neighbour never drags a segment onto an averaged line")

    # ---- B: the perturbed passes ADD, they do not retrace ----------------------------------
    base = [np.array([[0.0, 0.0, 0.0], [50.0, 0.0, 0.0]])]
    retrace = np.array([[0.0, 0.02, 0.0], [50.0, 0.02, 0.0]])
    elsewhere = np.array([[0.0, 25.0, 0.0], [50.0, 25.0, 0.0]])
    kept = _strips_not_already_drawn([retrace, elsewhere], base)
    ok(len(kept) == 1,
       f"B: a retraced copy is dropped and a genuinely new edge kept ({len(kept)} of 2)")
    if kept:
        ok(abs(float(np.asarray(kept[0], float)[0][1]) - 25.0) < 1e-9,
           "B: and the one kept is the edge the base pass never drew")
    ok(_strips_not_already_drawn([retrace], []) == [retrace]
       or len(_strips_not_already_drawn([retrace], [])) == 1,
       "B: with no reference drawing, everything is kept")
    # the tolerance is RELATIVE, so a tiny drawing is not over-merged
    tiny_base = [np.array([[0.0, 0.0, 0.0], [0.05, 0.0, 0.0]])]
    tiny_far = np.array([[0.0, 0.02, 0.0], [0.05, 0.02, 0.0]])
    ok(len(_strips_not_already_drawn([tiny_far], tiny_base)) == 1,
       "B: the tolerance scales with the drawing -- 0.02 mm is far on a 0.05 mm span")

    # ---- C: a shape that should close, closes ----------------------------------------------
    # The second case runs the REAL pipeline order on the real failure shape: a base pass
    # plus a perturbed pass that retraced it 0.025 mm away. The dedupe drops the retrace, so
    # the merge never has to choose between copies at a corner, and the box closes.
    base_3d = [np.hstack([s, np.zeros((2, 1))]) for s in _box()]
    copies_3d = [np.hstack([s, np.zeros((2, 1))]) for s in _with_copies(_box(), 0.025)[4:]]
    surviving_copies = _strips_not_already_drawn(copies_3d, base_3d)
    ok(not surviving_copies,
       f"C: the perturbed pass's retrace of the whole box is dropped "
       f"({len(surviving_copies)} of {len(copies_3d)} survived)")
    deduped_box = _box() + [np.asarray(k, float)[:, :2] for k in surviving_copies]
    for label, segments in (
        ("a clean box", _box()),
        ("a box the perturbed pass retraced 0.025 mm away", deduped_box),
    ):
        chains = stitch_strips_2d(merge_collinear_segments_2d(list(segments)))
        closed = [
            bool(np.allclose(np.asarray(c, float)[0], np.asarray(c, float)[-1], atol=1e-9))
            for c in chains
        ]
        ok(len(chains) == 1 and all(closed),
           f"C: {label} stitches into ONE closed chain ({len(chains)} chain(s), closed {closed})")

    # ---- D: the union still COVERS -- a lost edge is not silently dropped -------------------
    covered = _strips_not_already_drawn(
        [np.array([[10.0, 40.0, 0.0], [40.0, 40.0, 0.0]])],
        [np.array([[0.0, 0.0, 0.0], [50.0, 0.0, 0.0]])],
    )
    ok(len(covered) == 1,
       "D: a contour the base pass missed entirely is still added by the perturbed passes -- "
       "the bugs/0650 round-6 purpose survives")
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0798 closed-shape DXF validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
