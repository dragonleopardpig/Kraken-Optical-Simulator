"""Guard for bugs/0627 — blackbox surrogates DRAW at their drawn size, trace at 2x.

flag_20260818_140218 ("loaded Apo75, swap lens to pyrite85, lens surrogate grow big"):
bugs/0624 extends surrogate-member TRACE apertures to 2x the drawn diameter so corner
pencils refract instead of bypassing. The display meshes (system.AAA discs / system.BBB
side bodies) are that same built geometry, so a bare surrogate drew its doubled discs —
hidden on the Apo75 only by its STEP barrel overlay.

Checks (display-free):
  A  CONTRACT — both display mesh iterators clip blackbox-member meshes through
     `_clip_world_mesh_to_row_radius`; the member scan mirrors the build-side scan
     (front/rear vertex datums, stop-like rows excluded).
  B  BEHAVIOUR — a synthetic doubled disc clips back to the drawn radius in the
     surface's own local frame (TRANS_2A); a mesh already at drawn size passes through
     IDENTICAL (no copy, no point loss); a degenerate clip returns the original.
  C  BEHAVIOUR — the member scan finds the rows between Front/Rear datums, excludes
     the stop, and returns empty when no datums exist (plain scenes untouched).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0627_blackbox_display_size
"""

from __future__ import annotations

import inspect

import numpy as np


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import three_d_scene_tools as tools_module

    mixin = None
    for name, cls in vars(tools_module).items():
        if isinstance(cls, type) and hasattr(cls, "_clip_world_mesh_to_row_radius"):
            mixin = cls
            break
    if mixin is None:
        return False, ["FAIL: A: no mixin with _clip_world_mesh_to_row_radius"]

    # ---------------------------------------------------------------- A: contract
    optical_src = inspect.getsource(mixin._iter_3d_optical_surface_meshes)
    side_src = inspect.getsource(mixin._iter_3d_side_body_meshes)
    missing = [
        label
        for label, src in (("surface discs", optical_src), ("side bodies", side_src))
        if "_clip_world_mesh_to_row_radius" not in src
    ]
    if missing:
        ok = False
        notes.append(
            f"FAIL: A (bugs/0627): display iterators no longer clip blackbox members "
            f"({missing}) -- a bare surrogate draws its 2x trace discs again"
        )
    else:
        notes.append("PASS: A: both display iterators clip blackbox-member meshes")

    # ---------------------------------------------------------------- B: clip behaviour
    try:
        import pyvista as pv
    except Exception as exc:
        return ok, notes + [f"SKIP: B/C: pyvista unavailable ({exc!r})"]

    class _System:
        TRANS_2A = [np.eye(4)]

    doubled = pv.Disc(inner=0.0, outer=20.0, c_res=64)  # built at 2x (drawn radius 10)
    clipped = mixin._clip_world_mesh_to_row_radius(doubled, _System(), 0, 10.0)
    radial = np.hypot(clipped.points[:, 0], clipped.points[:, 1])
    at_size = pv.Disc(inner=0.0, outer=10.0, c_res=64)
    untouched = mixin._clip_world_mesh_to_row_radius(at_size, _System(), 0, 10.0)
    if float(np.max(radial)) > 10.0 * 1.02:
        ok = False
        notes.append(
            f"FAIL: B (bugs/0627): doubled disc still reaches r={float(np.max(radial)):.2f} "
            "after the clip (drawn radius 10) -- the surrogate draws big"
        )
    elif untouched is not at_size:
        ok = False
        notes.append(
            "FAIL: B (bugs/0627): a mesh already at drawn size was copied/modified -- "
            "the no-op fast path is gone (every scene pays the clip)"
        )
    elif mixin._clip_world_mesh_to_row_radius(None, _System(), 0, 10.0) is not None:
        ok = False
        notes.append("FAIL: B (bugs/0627): a None mesh did not pass through safely")
    else:
        notes.append(
            f"PASS: B: doubled disc clips to r<=10 ({clipped.n_points} pts), "
            "at-size mesh passes through identical"
        )

    # ---------------------------------------------------------------- C: member scan
    class _Row:
        def __init__(self, name, surface="Standard"):
            self.name = name
            self.surface = surface

    class _Editor(mixin):
        def __init__(self, rows):
            self.rows = rows

    rows = [
        _Row("Object", "Object"),
        _Row("BS plate"),
        _Row("Front Vertex Datum"),
        _Row("L1"),
        _Row("Stop", "Aperture"),
        _Row("L2"),
        _Row("Rear Vertex Datum"),
        _Row("Image", "Image"),
    ]
    members = _Editor(rows)._surrogate_blackbox_member_rows()
    plain = _Editor([_Row("Object", "Object"), _Row("L1"), _Row("Image", "Image")])._surrogate_blackbox_member_rows()
    if members != {2, 3, 5, 6}:
        ok = False
        notes.append(
            f"FAIL: C (bugs/0627): member scan found {sorted(members)} != [2, 3, 5, 6] "
            "(datums + lens rows, stop excluded)"
        )
    elif plain:
        ok = False
        notes.append(f"FAIL: C (bugs/0627): a datum-less scene reported members {sorted(plain)}")
    else:
        notes.append("PASS: C: member scan matches the build-side rule, plain scenes empty")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Blackbox-display-size validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
