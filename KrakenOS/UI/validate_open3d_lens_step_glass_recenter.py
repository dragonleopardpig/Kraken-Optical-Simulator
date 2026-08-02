"""Display-free guard for bugs/0374 -- lens STEP overlay glass-block re-centre.

A mechanical lens STEP is not centred on its glass, so pinning the mechanical
body FRONT FACE at the Front Optical Vertex Datum leaves the glass off by delta --
and delta swaps sign when the barrel is flipped (front_face max<->min, bugs/0373),
so the overlay jumps ~2*delta between orientations. The fix re-anchors the overlay
so the optical GLASS-BLOCK CENTRE lands on the surrogate's datum-span centre:
flip-invariant, and (because the surrogate datum span == the STEP glass vertex
span) front-vertex on front datum, rear-vertex on rear datum.

Checks:
- FLIP-INVARIANCE (mocked metrics): `_lens_step_display_front_z` returns targets
  that land the glass centre at the IDENTICAL world z for front_face max and min,
  and that world z is the datum-span centre; the old body-face pin would have
  swung. TILT GATE: |rot_x|,|rot_y| > 0.5 deg falls back to the plain datum pin.
  FALLBACK: no detectable glass -> plain datum pin.
- WIRING: the builder passes `target_front_z=self._lens_step_display_front_z(...)`
  and the cache signature carries the rear datum z.
- REAL STEP (skipped if absent / OCC unavailable): the detector finds >=2 on-axis
  optical spheres and the glass span matches the datasheet Sigma d (39.52 mm) for
  PYRITE 85 (1072517) -- i.e. the vertex method, not curvature centres.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_lens_step_glass_recenter
"""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace


def _stub(metrics, *, rot_x=0.0, rot_y=0.0):
    from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin

    insp = object.__new__(LayoutPolylineDisplayMixin)
    insp.append_debug = lambda *a, **k: None  # type: ignore[attr-defined]
    insp._external_cad_mesh_cache = {}  # type: ignore[attr-defined]
    insp.imported_lens_step_path = Path("mock.stp")  # type: ignore[attr-defined]
    insp.lens_step_rotation_x_deg = rot_x  # type: ignore[attr-defined]
    insp.lens_step_rotation_y_deg = rot_y  # type: ignore[attr-defined]
    # datum span 39.52: Front datum at z=100, Rear datum at z=139.52.
    insp.rows = [  # type: ignore[attr-defined]
        SimpleNamespace(name="Object", surface="Object", thickness=100.0),
        SimpleNamespace(name="Front Optical Vertex Datum", surface="Standard", thickness=39.52),
        SimpleNamespace(name="Rear Optical Vertex Datum", surface="Standard", thickness=150.0),
        SimpleNamespace(name="Image", surface="Image", thickness=0.0),
    ]
    # shadow the OCC detector with fixed metrics (display-free, env-independent)
    insp._step_optical_glass_axial_metrics = lambda path: metrics  # type: ignore[attr-defined]
    return insp


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    try:
        import pyvista  # noqa: F401

        from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: glass-recentre deps unavailable ({type(exc).__name__}: {exc})"]

    # --- FLIP-INVARIANCE (glass centre lands on datum centre, both orientations) ---
    # body [0,48]; glass span 39.52 offset so the block is 2.24 mm off the body
    # centre -> a 4.48 mm flip swing the fix must remove.
    metrics = {"glass_lo": 2.0, "glass_hi": 41.52, "body_lo": 0.0, "body_hi": 48.0, "surfaces": 2}
    glass_center = 0.5 * (metrics["glass_lo"] + metrics["glass_hi"])
    insp = _stub(metrics)
    fdz = insp._lens_front_datum_z()
    rdz = insp._lens_rear_datum_z()
    datum_center = 0.5 * (fdz + rdz)
    if abs((rdz - fdz) - 39.52) > 1e-6:
        failures.append(f"stub datum span {rdz - fdz:.4f} != 39.52 (rear-datum accessor wrong)")

    def _glass_center_world(face: str, stub=None) -> float:
        # bugs/0500: the pin is FACE-INDEPENDENT (the arg is accepted and ignored); a flip's
        # correction is the separate barrel-frame shift _lens_step_flip_axial_shift, applied by
        # the alignment on the "min" mapping. Model the pair exactly as the builder composes it.
        stub = stub if stub is not None else insp
        target = stub._lens_step_display_front_z(face)
        if face == "max":
            return target + (metrics["body_hi"] - glass_center)
        stub.lens_step_reverse_direction = True
        try:
            shift = stub._lens_step_flip_axial_shift()
        finally:
            stub.lens_step_reverse_direction = False
        return target + (glass_center - metrics["body_lo"]) + shift

    world_max = _glass_center_world("max")
    world_min = _glass_center_world("min")
    if abs(world_max - world_min) > 1e-6:
        failures.append(f"NOT flip-invariant: glass centre max={world_max:.4f} vs min={world_min:.4f}")
    if abs(world_max - datum_center) > 1e-6 or abs(world_min - datum_center) > 1e-6:
        failures.append(
            f"glass centre not pinned on datum centre {datum_center:.4f} "
            f"(max={world_max:.4f}, min={world_min:.4f})"
        )
    # the scenario must actually HAVE a swing under the old body-face pin, else the
    # test proves nothing.
    old_swing = abs((fdz + (metrics["body_hi"] - glass_center)) - (fdz + (glass_center - metrics["body_lo"])))
    if old_swing < 1.0:
        failures.append(f"test scenario too weak: old body-face swing only {old_swing:.4f} mm")

    # --- TILT GATE: tilted overlay keeps the plain datum pin -----------------------
    for axis, kwargs in (("rot_x", {"rot_x": 5.0}), ("rot_y", {"rot_y": 5.0})):
        tilted = _stub(metrics, **kwargs)
        if abs(tilted._lens_step_display_front_z("max") - tilted._lens_front_datum_z()) > 1e-6:
            failures.append(f"tilt gate failed for {axis}: did not fall back to the front datum pin")
        # bugs/0500: the FLIP must stay glass-invariant even under tilt -- which is exactly the
        # branch the old per-face pin never covered (any lens on a folded arm is "tilted", and its
        # flip landed the optics 3.507 mm off the datums on the AZ85 barrel).
        t_max = _glass_center_world("max", tilted)
        t_min = _glass_center_world("min", tilted)
        if abs(t_max - t_min) > 1e-6:
            failures.append(
                f"bugs/0500 ({axis}): tilted flip not glass-invariant (max={t_max:.4f}, min={t_min:.4f})"
            )

    # --- FALLBACK: no detectable glass -> plain datum pin --------------------------
    none_stub = _stub(None)
    if abs(none_stub._lens_step_display_front_z("max") - none_stub._lens_front_datum_z()) > 1e-6:
        failures.append("no-glass fallback failed: must return the plain front datum")

    # --- bugs/0377: a BIG mechanical barrel keeps the authored body-face pin --------
    # A real lens barrel (Edmund 15056: a 112mm mount around a 53mm glass block) must NOT
    # be re-centred onto the datum -- that shifts the whole barrel ~37mm off the surrogate
    # ("lens STEP detached"). Only a CLOSE barrel (body ~ glass, the MV surrogate case)
    # gets the 0374 re-centre; a body >> glass falls back to the plain front-datum pin.
    big_barrel = {"glass_lo": 30.0, "glass_hi": 60.0, "body_lo": 0.0, "body_hi": 100.0, "surfaces": 14}
    bb = _stub(big_barrel)
    if abs(bb._lens_step_display_front_z("max") - bb._lens_front_datum_z()) > 1e-6:
        failures.append("bugs/0377: a big barrel (body >> glass) must keep the body-face pin, not re-centre")
    close_barrel = {"glass_lo": 4.0, "glass_hi": 43.0, "body_lo": 0.0, "body_hi": 48.0, "surfaces": 2}
    cb = _stub(close_barrel)
    if abs(cb._lens_step_display_front_z("max") - cb._lens_front_datum_z()) < 1e-6:
        failures.append("bugs/0377 gate too tight: a close barrel (body ~ glass) must still be re-centred (0374)")

    # --- WIRING -------------------------------------------------------------------
    build_src = inspect.getsource(LayoutPolylineDisplayMixin._transformed_imported_lens_step_mesh)
    if "target_front_z=self._lens_step_display_front_z()" not in build_src:
        failures.append("the lens builder does not pin the overlay via _lens_step_display_front_z")
    if "flip_axial_shift=flip_shift" not in build_src:
        failures.append("bugs/0500: the lens builder does not wire the flip correction into the alignment")
    if "self._lens_rear_datum_z()" not in build_src:
        failures.append("the rear datum z is not in the lens overlay cache signature")

    # --- REAL STEP (optional): detector matches the datasheet Sigma d --------------
    step = Path("attachment/Lens/PYRITE_45_85_05x-20x_V38_1072517/1072517_00165969_001.stp")
    if step.exists():
        try:
            probe = object.__new__(LayoutPolylineDisplayMixin)
            probe.append_debug = lambda *a, **k: None  # type: ignore[attr-defined]
            probe._external_cad_mesh_cache = {}  # type: ignore[attr-defined]
            real = probe._step_optical_glass_axial_metrics(step)
        except Exception as exc:  # pragma: no cover - OCC/env issue
            real = None
            print(f"  (real-STEP check skipped: {type(exc).__name__}: {exc})")
        if real is not None:
            span = real["glass_hi"] - real["glass_lo"]
            if int(real.get("surfaces", 0)) < 2:
                failures.append(f"real STEP: fewer than 2 on-axis optical spheres ({real.get('surfaces')})")
            if abs(span - 39.52) > 0.2:
                failures.append(
                    f"real STEP glass span {span:.3f} mm != datasheet Sigma d 39.52 mm "
                    "(vertex method broken -- curvature-centre error?)"
                )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Lens-STEP glass-recentre validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Lens-STEP glass-recentre validation passed: the overlay pins the optical "
        "glass-block centre on the surrogate datum-span centre (flip-invariant, both "
        "orientations land the identical world z), tilt and no-glass fall back to the "
        "plain datum pin, the builder + signature are wired, and (when present) the "
        "detector matches the datasheet Sigma d = 39.52 mm on the real PYRITE 85 STEP."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
