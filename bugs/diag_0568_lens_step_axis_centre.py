"""Diagnostic: where does the lens-STEP overlay's transverse centre come from?

Flag ``flag_20260805_203837_379`` -- "swap a lens, Lens STEP is not centered to
optical axis, I think because of the screw."  Measured from the flag: the lens
overlay's world bbox centre sits 5.696 mm off the BS-reflect leg (z 49.663 vs
axis 55.359) while its OTHER transverse direction is dead on (y 0.001).

This dumps the OCC cylinder inventory of the lens STEP, replays
``_step_primary_cylinder_axis_frame``'s clustering, and reports the transverse
distance between

    * the clustered ("optical axis") point that ``_cad_mesh_aligned_to_optical_axis``
      uses as the lateral anchor, and
    * the mesh bbox midpoint / a robust barrel-centre estimate.

Run:
    .devenv/state/venv/bin/python bugs/diag_0568_lens_step_axis_centre.py [STEP ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_STEPS = (
    PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_45_85_05x-20x_V38_1072517" / "1072517_00165969_001.stp",
    PROJECT_ROOT / "attachment" / "Lens" / "0703-005-000-40-EXC" / "0703-005-000-40_PA_a_STEP.stp",
)


def cylinder_inventory(path: Path):
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.GeomAbs import GeomAbs_Cylinder
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.Bnd import Bnd_Box

    try:
        from OCC.Core.BRepBndLib import brepbndlib

        _bbox_add = brepbndlib.Add
    except Exception:  # pragma: no cover - OCC version shim
        from OCC.Core.BRepBndLib import brepbndlib_Add as _bbox_add

    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != 1:
        raise RuntimeError(f"cannot read {path}")
    reader.TransferRoots()
    shape = reader.OneShape()
    box = Bnd_Box()
    _bbox_add(shape, box)
    bx0, by0, bz0, bx1, by1, bz1 = box.Get()
    body_center = np.array([(bx0 + bx1) * 0.5, (by0 + by1) * 0.5, (bz0 + bz1) * 0.5])
    body_diag = float(np.linalg.norm([bx1 - bx0, by1 - by0, bz1 - bz0]))

    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    rows = []
    while explorer.More():
        surface = BRepAdaptor_Surface(explorer.Current())
        if surface.GetType() == GeomAbs_Cylinder:
            cyl = surface.Cylinder()
            d = cyl.Axis().Direction()
            vec = np.array([d.X(), d.Y(), d.Z()], dtype=float)
            loc = cyl.Axis().Location()
            raw = np.array([loc.X(), loc.Y(), loc.Z()], dtype=float)
            norm = float(np.linalg.norm(vec))
            radius = float(cyl.Radius())
            if (
                norm > 1e-12
                and np.isfinite(radius)
                and radius > 1.0
                and radius <= max(1.5 * body_diag, 10.0)
                and np.all(np.isfinite(raw))
            ):
                unit = vec / norm
                near = raw + float(np.dot(body_center - raw, unit)) * unit
                rows.append((radius, unit, near))
        explorer.Next()
    return rows, body_center, body_diag, (bx0, by0, bz0, bx1, by1, bz1)


def cluster(axes, body_diag):
    """Replay of _step_primary_cylinder_axis_frame's grouping (seed-anchored)."""
    groups = []
    for radius, unit, near_point in axes:
        placed = False
        for group in groups:
            group_dir = group["dir"]
            oriented = unit if float(np.dot(group_dir, unit)) >= 0.0 else -unit
            if abs(float(np.dot(group_dir, oriented))) < 0.985:
                continue
            delta = near_point - group["point"]
            perp = float(np.linalg.norm(delta - float(np.dot(delta, group_dir)) * group_dir))
            if perp > max(2.0, 0.15 * body_diag):
                continue
            group["weight"] += radius
            group["dir_sum"] += radius * oriented
            group["point_sum"] += radius * near_point
            group["members"].append((radius, near_point, perp))
            placed = True
            break
        if not placed:
            groups.append(
                {
                    "dir": unit,
                    "point": near_point,
                    "weight": radius,
                    "dir_sum": radius * unit,
                    "point_sum": radius * near_point,
                    "members": [(radius, near_point, 0.0)],
                }
            )
    return groups


def transverse_basis(axis):
    reference = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(reference, axis))) > 0.9:
        reference = np.array([0.0, 1.0, 0.0])
    u = np.cross(reference, axis)
    u /= max(float(np.linalg.norm(u)), 1e-12)
    v = np.cross(axis, u)
    v /= max(float(np.linalg.norm(v)), 1e-12)
    return u, v


def report(path: Path) -> None:
    print("=" * 100)
    print(path)
    axes, body_center, body_diag, bounds = cylinder_inventory(path)
    print(f"  body bbox      = {tuple(round(v, 3) for v in bounds)}")
    print(f"  body centre    = {np.round(body_center, 3).tolist()}   diag {body_diag:.2f} mm")
    print(f"  qualifying cylinders = {len(axes)}   (cluster tol perp <= {max(2.0, 0.15*body_diag):.2f} mm)")

    groups = cluster(axes, body_diag)
    groups_sorted = sorted(groups, key=lambda g: -g["weight"])
    print(f"  clusters = {len(groups)}")
    for i, g in enumerate(groups_sorted[:6]):
        axis = g["dir_sum"] / max(float(np.linalg.norm(g["dir_sum"])), 1e-12)
        point = g["point_sum"] / g["weight"]
        radii = sorted({round(r, 3) for r, _, _ in g["members"]})
        perps = [p for _, _, p in g["members"]]
        print(
            f"   [{i}] weight {g['weight']:9.1f}  n={len(g['members']):4d}  "
            f"axis={np.round(axis,4).tolist()}  point={np.round(point,3).tolist()}"
        )
        print(
            f"        member radii {radii[:8]}{' ...' if len(radii) > 8 else ''}  "
            f"perp spread max {max(perps):.3f} mm"
        )

    best = max(groups, key=lambda g: g["weight"])
    axis = best["dir_sum"] / float(np.linalg.norm(best["dir_sum"]))
    point = best["point_sum"] / best["weight"]
    u, v = transverse_basis(axis)

    # Where is the barrel really?  Use the qualifying cylinders that are TRULY
    # coaxial with the winning cluster (perp <= 0.05 mm through the widest one).
    widest = max(best["members"], key=lambda m: m[0])
    coax = [
        (r, p)
        for (r, p, _perp) in best["members"]
        if float(np.linalg.norm((p - widest[1]) - float(np.dot(p - widest[1], axis)) * axis)) <= 0.05
    ]
    coax_weight = sum(r for r, _ in coax)
    coax_point = sum((r * p for r, p in coax), np.zeros(3)) / max(coax_weight, 1e-12)

    def tp(p):
        d = p - body_center
        return np.array([float(d @ u), float(d @ v)])

    print()
    print(f"  WINNING cluster axis  = {np.round(axis, 6).tolist()}")
    print(f"  anchor point (shipped)= {np.round(point, 4).tolist()}   transverse {np.round(tp(point), 4).tolist()}")
    print(
        f"  strictly-coaxial mean = {np.round(coax_point, 4).tolist()}   transverse "
        f"{np.round(tp(coax_point), 4).tolist()}   "
        f"({len(coax)}/{len(best['members'])} members, weight {coax_weight:.1f}/{best['weight']:.1f})"
    )
    drift = float(np.linalg.norm(tp(point) - tp(coax_point)))
    print(f"  >>> anchor drift off the true barrel axis = {drift:.4f} mm")

    # Off-cluster members, i.e. the parallel-but-not-coaxial faces (screw bosses)
    off = [
        (r, p, float(np.linalg.norm((p - widest[1]) - float(np.dot(p - widest[1], axis)) * axis)))
        for (r, p, _perp) in best["members"]
    ]
    off = [o for o in off if o[2] > 0.05]
    if off:
        print(f"  parallel-but-OFF-axis members merged into the barrel cluster: {len(off)}")
        by_r = sorted(off, key=lambda o: -o[0])[:10]
        for r, p, d in by_r:
            print(f"      radius {r:8.3f}  offset {d:8.3f} mm  point {np.round(p,2).tolist()}")
        print(f"      merged weight {sum(o[0] for o in off):.1f} of {best['weight']:.1f}")

    # Mesh check -- bbox midpoint vs the anchor, in the transverse plane.
    try:
        from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin

        insp = object.__new__(LayoutPolylineDisplayMixin)
        insp.append_debug = lambda *a, **k: None
        insp._external_cad_mesh_cache = {}
        mesh = insp._load_step_mesh(path, largest_component=True, allow_slow_import=True)
        pts = np.asarray(mesh.points, dtype=float)
        centered = pts - pts.mean(axis=0)
        work = np.column_stack([centered @ u, centered @ v, centered @ axis])
        wmin, wmax = work.min(axis=0), work.max(axis=0)
        body_mid = 0.5 * (wmin[:2] + wmax[:2])
        anchor = np.array([float((point - pts.mean(axis=0)) @ u), float((point - pts.mean(axis=0)) @ v)])
        coax_anchor = np.array(
            [float((coax_point - pts.mean(axis=0)) @ u), float((coax_point - pts.mean(axis=0)) @ v)]
        )
        print()
        print(f"  mesh points {pts.shape[0]}  transverse extent u {wmax[0]-wmin[0]:.3f}  v {wmax[1]-wmin[1]:.3f}")
        print(f"  bbox midpoint (fallback centring) = {np.round(body_mid, 4).tolist()}")
        print(f"  shipped anchor                    = {np.round(anchor, 4).tolist()}"
              f"   |anchor - bbox mid| = {float(np.linalg.norm(anchor - body_mid)):.4f} mm")
        print(f"  strictly-coaxial anchor           = {np.round(coax_anchor, 4).tolist()}"
              f"   |coax - bbox mid| = {float(np.linalg.norm(coax_anchor - body_mid)):.4f} mm")
        for name, c in (("shipped", anchor), ("coaxial", coax_anchor), ("bboxmid", body_mid)):
            du = work[:, 0] - c[0]
            dv = work[:, 1] - c[1]
            r = np.hypot(du, dv)
            print(
                f"    centred on {name}: max radius {r.max():.3f} mm; "
                f"u span [{du.min():.3f},{du.max():.3f}] v span [{dv.min():.3f},{dv.max():.3f}]"
            )
    except Exception as exc:  # pragma: no cover - mesh conversion optional
        print(f"  (mesh check skipped: {type(exc).__name__}: {exc})")


def main() -> int:
    targets = [Path(a) for a in sys.argv[1:]] or [p for p in DEFAULT_STEPS if p.exists()]
    for path in targets:
        if not path.exists():
            print(f"SKIP (absent): {path}")
            continue
        report(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
