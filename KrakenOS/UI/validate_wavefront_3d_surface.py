"""Guard: the real 3D wavefront surface (PyVista/VTK) builds and renders.

The analysis panel's 2D oblique waterfall (bug 0036) mirrors the Zemax printout
but is painter's-algorithm fake-3D. ``services/wavefront_3d_view`` is the honest
counterpart: it warps the pupil OPD samples into a true z-buffered 3D surface mesh
and renders it with PyVista/VTK (already KrakenOS deps).

This display-free guard, on a synthetic circular-pupil wavefront:
  A. ``wavefront_xyz_from_samples`` round-trips ``_last_wavefront_samples`` dicts
     (the same data the analysis panel fills), dropping bad/non-finite rows.
  B. ``build_wavefront_surface`` returns a real 3D triangle mesh -- points and
     cells > 0, finite bounds, and a non-flat z-extent that matches the OPD range
     scaled by the (shallow-dome) warp factor.
  C. ``render_wavefront_surface_to_png`` renders OFF-SCREEN to a non-blank PNG
     (true hidden-surface 3D; works headless here via VTK software GL, no Xvfb).

SKIPs cleanly (still exit 0) if PyVista/VTK is unavailable on a clone.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_wavefront_3d_surface

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from KrakenOS.UI.services import wavefront_3d_view as w3d


def _synthetic_pupil() -> "tuple[np.ndarray, np.ndarray, np.ndarray]":
    n = 55
    lin = np.linspace(-1.0, 1.0, n)
    grid_x, grid_y = np.meshgrid(lin, lin)
    inside = (grid_x**2 + grid_y**2) <= 1.0
    x = grid_x[inside]
    y = grid_y[inside]
    r = np.hypot(x, y)
    theta = np.arctan2(y, x)
    opd = -(
        1.4 * (6 * r**4 - 6 * r**2 + 1)            # spherical
        + 0.9 * (3 * r**3 - 2 * r) * np.cos(theta)  # coma
        + 0.6 * r**2 * np.cos(2 * theta)            # astigmatism
    )
    return x, y, opd - float(np.mean(opd))


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    try:
        import pyvista  # noqa: F401
    except Exception as exc:  # pragma: no cover - environment dependent
        notes.append(f"SKIP: PyVista/VTK unavailable ({type(exc).__name__})")
        return passed, notes

    x, y, opd = _synthetic_pupil()

    # A. Sample dict round-trip.
    samples = [
        {"x_pupil": float(xv), "y_pupil": float(yv), "phase_waves": float(zv)}
        for xv, yv, zv in zip(x, y, opd)
    ]
    samples.append({"x_pupil": "bad", "y_pupil": 0.0, "phase_waves": 0.0})       # dropped
    samples.append({"x_pupil": np.nan, "y_pupil": 0.0, "phase_waves": 0.0})      # dropped
    sx, sy, sz = w3d.wavefront_xyz_from_samples(samples)
    if not (sx.size == sy.size == sz.size == x.size):
        notes.append(
            f"FAIL: sample round-trip kept {sx.size} of {x.size} finite rows "
            f"(bad/non-finite rows should be dropped)"
        )
        passed = False

    # B. Mesh build.
    try:
        warped, factor = w3d.build_wavefront_surface(x, y, opd)
    except Exception as exc:
        notes.append(f"FAIL: build_wavefront_surface raised {type(exc).__name__}: {exc}")
        return False, notes

    if warped.n_points <= 0 or warped.n_cells <= 0:
        notes.append(
            f"FAIL: surface has {warped.n_points} points / {warped.n_cells} cells -- not a mesh"
        )
        passed = False

    bounds = np.asarray(warped.bounds, dtype=float)
    if not np.all(np.isfinite(bounds)):
        notes.append(f"FAIL: surface bounds are not finite: {bounds.tolist()}")
        passed = False

    z_extent = float(bounds[5] - bounds[4])
    expected = float(np.ptp(opd)) * factor
    if z_extent <= 1e-6:
        notes.append(f"FAIL: surface is flat (z-extent {z_extent:.4g}) -- warp not applied")
        passed = False
    elif not (0.8 * expected <= z_extent <= 1.2 * expected):
        notes.append(
            f"FAIL: z-extent {z_extent:.4g} vs expected ~{expected:.4g} "
            f"(OPD range x warp factor {factor:.4g}); relief not as warped"
        )
        passed = False

    # C. Off-screen render to a non-blank PNG.
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "wavefront_3d.png"
        try:
            path, _factor = w3d.render_wavefront_surface_to_png(
                x, y, opd, out, title="Wavefront 3D self-test"
            )
        except Exception as exc:
            notes.append(f"FAIL: off-screen render raised {type(exc).__name__}: {exc}")
            return False, notes
        if not path.exists() or path.stat().st_size < 2000:
            notes.append("FAIL: rendered PNG missing or implausibly small")
            passed = False
        else:
            try:
                from PIL import Image

                arr = np.asarray(Image.open(path).convert("RGB"))
                # A real render has substantial non-white content (the surface).
                non_white = int(np.count_nonzero(np.any(arr < 245, axis=2)))
                frac = non_white / float(arr.shape[0] * arr.shape[1])
                if frac < 0.02:
                    notes.append(
                        f"FAIL: rendered PNG is essentially blank ({frac*100:.2f}% non-white)"
                    )
                    passed = False
                if verbose:
                    notes.append(f"render non-white fraction={frac*100:.1f}%")
            except Exception as exc:
                notes.append(f"SKIP image-content check (PIL unavailable: {type(exc).__name__})")

    # D. Subprocess payload round-trip (what the UI button hands the viewer).
    if w3d.write_wavefront_payload_npz([]) is not None:
        notes.append("FAIL: payload helper returned a path for empty samples (should be None)")
        passed = False
    payload = w3d.write_wavefront_payload_npz(samples, title="round-trip")
    if payload is None:
        notes.append("FAIL: payload helper returned None for a full sample set")
        passed = False
    else:
        try:
            loaded = np.load(payload, allow_pickle=True)
            keys = set(loaded.files)
            if not {"x", "y", "opd"} <= keys:
                notes.append(f"FAIL: payload npz missing arrays (has {sorted(keys)})")
                passed = False
            elif loaded["x"].size != x.size:
                notes.append(
                    f"FAIL: payload kept {loaded['x'].size} of {x.size} samples"
                )
                passed = False
        finally:
            try:
                payload.unlink()
            except OSError:
                pass

    if verbose:
        notes.append(
            f"points={warped.n_points}, cells={warped.n_cells}, "
            f"z_extent={z_extent:.4g}, warp_factor={factor:.4g}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] Wavefront 3D surface builds and renders (PyVista/VTK)")
        return 0
    print("[FAIL] Wavefront 3D surface guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
