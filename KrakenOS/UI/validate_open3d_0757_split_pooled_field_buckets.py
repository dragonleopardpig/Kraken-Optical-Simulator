"""Guard for bugs/0757 -- a bucket that pools several field points is not a field group.

After a camera-stage solve on om05a the two arms disagreed absurdly about where the image
forms, while carrying identical magnification to six digits:

    A ('source:0', 3)      106 rays   offset  +0.0235   waist    0.805 um
    A ('source:0', 4)      106 rays   offset  -0.0200   waist    0.055 um
    A ('source:0', 5)      106 rays   offset  +0.0235   waist    0.804 um
    B ('source:faceB', 8)  318 rays   offset -95.3514   waist 3865.294 um

Arm A arrived as three field groups; the mirrored second arm (bugs/0696) arrived as ONE index
carrying all 318 rays from three distinct field points. bugs/0728 groups by field precisely
because "a least-squares waist over the whole bundle would minimise the IMAGE SIZE, not the
blur" -- so arm B's "waist" was the image height, and it drew the focus plane 95 mm out.

The fix does not depend on an upstream index that can collapse: the decomposition is recovered
from the rays themselves, by launch position.

Checks (display-free, pure):
  A  a pooled bucket splits into one group per launch point, with ends/dirs/polylines/launches
     kept in step;
  B  a genuine single-field bucket is left exactly as it was;
  C  a continuum of launch points (a random-area emitter) is NOT split, so bugs/0728's pooled
     fallback still covers it;
  D  a split that would leave only one well-sampled group is declined;
  E  the production measurement runs it before anything measures a waist.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0757_split_pooled_field_buckets
"""

from __future__ import annotations

import inspect

import numpy as np


def _bucket(launch_points, per_point):
    """(buckets, polylines, launches) for one key whose rays launch from the given points."""
    ends, dirs, polys, launches = [], [], [], []
    for p_index, point in enumerate(launch_points):
        for k in range(per_point):
            ends.append(np.array([float(p_index), float(k), 0.0]))
            dirs.append(np.array([0.0, 0.0, 1.0]))
            polys.append(np.array([[0.0, 0.0, -10.0], [float(p_index), float(k), 0.0]]))
            launches.append(np.asarray(point, dtype=float))
    key = ("source:x", 8)
    return {key: (ends, dirs)}, {key: polys}, {key: launches}, key


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    split = LayoutTableWorkbenchMixin._split_pooled_field_buckets

    class Stub:
        pass

    stub = Stub()

    # ---- A: the om05a shape -- three field points pooled under one index -------------------
    points = [(0.0, 0.0, 0.0), (0.0, 0.0, -25.0), (0.0, 0.0, -50.0)]
    b, p, l, key = _bucket(points, 106)
    nb, np_, nl = split(stub, b, p, l)
    ok(len(nb) == 3, f"A1: the pooled bucket splits into one group per launch point ({len(nb)})")
    ok(
        all(len(v[0]) == 106 for v in nb.values()),
        f"A2: each group keeps its own 106 rays ({sorted(len(v[0]) for v in nb.values())})",
    )
    ok(
        all(len(np_[k]) == len(nb[k][0]) and len(nl[k]) == len(nb[k][0]) for k in nb),
        "A3: polylines and launch points stay in step with the rays (the walk indexes them "
        "together, so a mismatch would draw the wrong ray)",
    )
    ok(
        all(len({tuple(np.round(q, 3)) for q in nl[k]}) == 1 for k in nb),
        "A4: every ray in a split group really does share one launch point",
    )
    ok(
        sum(len(v[0]) for v in nb.values()) == 318,
        "A5: no ray is lost or duplicated by the split",
    )

    # ---- B: a genuine single-field bucket is untouched ---------------------------------------
    b, p, l, key = _bucket([(0.0, 0.0, 0.0)], 106)
    nb, _np, _nl = split(stub, b, p, l)
    ok(
        len(nb) == 1 and key in nb and len(nb[key][0]) == 106,
        "B1: one launch point -> the bucket is returned unchanged, same key",
    )

    # ---- C: a continuum must NOT be split ----------------------------------------------------
    continuum = [(0.0, 0.0, -0.001 * k) for k in range(300)]
    b, p, l, key = _bucket(continuum, 1)
    nb, _np, _nl = split(stub, b, p, l)
    ok(
        len(nb) == 1 and key in nb and len(nb[key][0]) == 300,
        f"C1: a random-area emitter (300 distinct launch points) is left pooled ({len(nb)}), so "
        f"bugs/0728's fallback still handles it",
    )

    # ---- D: don't split into noise ------------------------------------------------------------
    b, p, l, key = _bucket([(0.0, 0.0, 0.0)] * 1, 100)
    for pt in [(0.0, 0.0, -50.0)]:
        b[key][0].append(np.array([9.0, 0.0, 0.0]))
        b[key][1].append(np.array([0.0, 0.0, 1.0]))
        p[key].append(np.array([[0.0, 0.0, -10.0], [9.0, 0.0, 0.0]]))
        l[key].append(np.asarray(pt, dtype=float))
    nb, _np, _nl = split(stub, b, p, l)
    ok(
        len(nb) == 1,
        f"D1: 100 rays at one point plus a single stray is NOT split -- one well-sampled group "
        f"is not a decomposition ({len(nb)})",
    )

    # ---- E: wired into the real measurement -----------------------------------------------------
    measure = inspect.getsource(LayoutTableWorkbenchMixin._measure_focused_image_plane)
    ok(
        "self._split_pooled_field_buckets(" in measure,
        "E1: the production measurement calls it",
    )
    ok(
        measure.find("_split_pooled_field_buckets") < measure.find("_focus_image_partitions"),
        "E2: and runs it BEFORE the images are partitioned and any waist is measured",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0757 split-pooled-field-buckets validation PASSED")
        return 0
    print("0757 split-pooled-field-buckets validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
