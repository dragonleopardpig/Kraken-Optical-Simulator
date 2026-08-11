"""Guard for bugs/0611 — fold elbows connect: no world-space vertex inset.

Flags 20260811_201311/201334 ("broken reflection rays at BS / at RA mirror"): the 3-D
ray mesh pulled each segment back from interior vertices by a WORLD-SPACE inset
(0.035..0.18 mm scene-scaled), so at high zoom every fold elbow rendered as two
disconnected stubs — a physics lie (the reflected ray touches the mirror AT the
vertex). Any world-space gap is zoom-false; the production inset must be ZERO. The
fake-transmission defense stays structural: segments are DISCONNECTED, so no polyline
miter join can overshoot the bend.

Checks (display-free):
  A  CONTRACT — the production inset `_ray_vertex_display_inset` returns 0.0 for any
     scene radius.
  B  MECHANISM — a mesh built with the production inset keeps interior event vertices
     EXACT (elbows connect) while segments stay disconnected (two 2-point cells).
  C  COMPAT — an explicit nonzero inset is still honored (the 4a23587e contract:
     interior vertices move, outer endpoints never do).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0611_fold_elbows_connect
"""

from __future__ import annotations

import numpy as np


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin as T

    # ---------------------------------------------------------------- A: contract
    bad = [r for r in (0.5, 10.0, 460.0, 5000.0) if T._ray_vertex_display_inset(r) != 0.0]
    if bad:
        ok = False
        notes.append(
            f"FAIL: A (bugs/0611): production inset nonzero for radius {bad} -- a "
            "world-space gap re-breaks the fold elbows at high zoom"
        )
    else:
        notes.append("PASS: A: the production vertex inset is 0 at every scene radius")

    # ---------------------------------------------------------------- B: mechanism
    elbow = np.asarray(((0.0, 0.0, -20.0), (0.0, 0.0, 0.0), (20.0, 0.0, 0.0)), dtype=float)
    mesh = T._ray_segment_mesh_for_3d_display(
        elbow, vertex_inset=T._ray_vertex_display_inset(460.0)
    )
    if mesh is None:
        notes.append("SKIP: B: pyvista unavailable -- mechanism checked via C only")
    else:
        pts = np.asarray(mesh.points, dtype=float)
        lines = np.asarray(mesh.lines, dtype=int).reshape(-1, 3)
        at_vertex = int(np.sum(np.all(np.isclose(pts, (0.0, 0.0, 0.0), atol=1e-12), axis=1)))
        if at_vertex != 2:
            ok = False
            notes.append(
                f"FAIL: B (bugs/0611): {at_vertex} mesh points sit exactly on the fold "
                "vertex (want 2: segment-1 end + segment-2 start) -- the elbow is broken again"
            )
        elif lines.shape[0] != 2 or not np.all(lines[:, 0] == 2):
            ok = False
            notes.append(
                f"FAIL: B: segments no longer disconnected ({lines.tolist()}) -- a polyline "
                "join can overshoot the bend and mimic transmission"
            )
        else:
            notes.append("PASS: B: elbow connects exactly at the vertex; segments stay disconnected")

    # ---------------------------------------------------------------- C: compat
    mesh = T._ray_segment_mesh_for_3d_display(elbow, vertex_inset=0.5)
    if mesh is None:
        notes.append("SKIP: C: pyvista unavailable")
    else:
        pts = np.asarray(mesh.points, dtype=float)
        on_vertex = int(np.sum(np.all(np.isclose(pts, (0.0, 0.0, 0.0), atol=1e-12), axis=1)))
        ends_exact = np.all(np.isclose(pts[0], (0.0, 0.0, -20.0), atol=1e-12)) and np.all(
            np.isclose(pts[-1], (20.0, 0.0, 0.0), atol=1e-12)
        )
        if on_vertex != 0 or not ends_exact:
            ok = False
            notes.append(
                f"FAIL: C (bugs/0611): explicit inset no longer honored (on_vertex={on_vertex}, "
                f"ends_exact={ends_exact}) -- the 4a23587e mechanism contract broke"
            )
        else:
            notes.append("PASS: C: an explicit inset still moves interior vertices, never the outer endpoints")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Fold-elbows-connect validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
