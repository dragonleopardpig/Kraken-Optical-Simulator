"""Guard for bugs/0670 -- the om05a two-side split-field station: one chain, two
device faces, one camera.

User (2026-08-31): "The reason I needed a 3D object rather than 2D plane is that I
need to inspect object opposite 2-side" -- the om05a assembly (Prism Assembly + RA
mirror + MV85 imaging lens + filter + RA mirror + 25MP camera). Unfolding its five
folds yields ONE sequential chain (0297: one shared first order): the two opposite
device end faces sit SIDE BY SIDE in one object plane (the CAD's equal path lengths
guarantee one conjugate), pass the three prism glasses as plates, the MV85 (EFL 85;
object->H = f(1+1/|m|) = 280.0 -- the lens's own designation), the 48-926 filter, and
land on opposite halves of the one sensor. The folds are geometry, not prescription;
the focus is the TRACED convergence (0109), which the build measured to land 3.4 mm
past the no-glass conjugate -- matching t(1-1/n)*m^2 + filter to 0.2 mm.

Checks (scene checks skip when the attachment scene is absent -- it is Filen-synced,
not git-tracked):
  A  PRESCRIPTION: the scene carries the three prism plates + the filter as N-BK7
     glass, the 25MP sensor diagonal, discs within the lens barrel, and the CAD
     component STEPs wired for display.
  B  TRACE (the physics pins): per-FIELD rms at the sensor < 5 um (in focus); the
     traced magnification matches 85/195 within 2%; the two face patches land on
     OPPOSITE sensor halves, inside the sensor.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0670_om05a_split_field
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/om05a_two_side.py"


def _check_scene(ok, notes) -> None:
    if not SCENE.exists():
        notes.append("SKIP: A/B: the om05a scene is not on this machine (Filen-synced)")
        return
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["om"] = SCENE
        editor.load_layout_by_name("om")
        rows = editor.rows
        glass_rows = [r for r in rows if str(r.glass).upper() not in ("AIR", "MIRROR", "")]
        prisms = [r for r in glass_rows if "prism" in str(r.name).lower()]
        filters = [r for r in glass_rows if "filter" in str(r.name).lower()]
        ok(
            len(prisms) == 3 and all(str(r.glass) == "N-BK7" for r in prisms)
            and len(filters) == 1 and abs(float(filters[0].thickness) - 1.0) < 1e-6,
            f"A1: three N-BK7 prism plates + the 1 mm filter are in the chain "
            f"({[str(r.name) for r in prisms + filters]})",
        )
        ok(
            abs(float(rows[-1].diameter) - 32.58) < 0.05,
            f"A2: the image row is the 25MP sensor diagonal ({float(rows[-1].diameter):.2f})",
        )
        discs = [float(r.diameter) for r in rows if "Datum" in str(r.name) or "Group" in str(r.name)]
        ok(
            discs and max(discs) <= 48.6,
            f"A3: surrogate discs stay within the MV85 barrel (max {max(discs):.2f} <= 48.6, bugs/0668)",
        )
        cam = str(getattr(editor, "imported_camera_step_path", "") or "")
        lens = str(getattr(editor, "imported_lens_step_path", "") or "")
        ok(
            "camera_sv25mccxp" in cam and "lens_mv85_280" in lens,
            "A4: the extracted CAD bodies (camera + lens) are wired for display",
        )

        # B: trace physics
        try:
            editor._preview_trace_deferred_until_requested = False
        except Exception:
            pass
        system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
        z_img = sum(float(r.thickness) for r in rows[:-1])
        groups: dict[int, list[np.ndarray]] = {}
        for rp in (getattr(bundle, "ray_paths", None) or []):
            p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
            if p.ndim != 2 or p.shape[0] < 2 or not np.all(np.isfinite(p[-2:])):
                continue
            a, b = p[-2], p[-1]
            d = b - a
            if abs(d[2]) < 1e-9:
                continue
            t = (z_img - a[2]) / d[2]
            groups.setdefault(int(getattr(rp, "field_index", 0)), []).append(a[:2] + t * d[:2])
        cents = {}
        rms_all = []
        for fi, pts in groups.items():
            arr = np.asarray(pts)
            if len(arr) < 4:
                continue
            cents[fi] = arr.mean(axis=0)
            rms_all.append(float(np.sqrt(((arr - arr.mean(axis=0)) ** 2).sum(axis=1).mean())))
        ok(
            rms_all and max(rms_all) < 0.005,
            f"B1: every field is IN FOCUS at the sensor (worst per-field rms "
            f"{max(rms_all) * 1000 if rms_all else float('nan'):.1f} um < 5)",
        )
        ys = sorted(c[1] for c in cents.values())
        m_expected = 85.0 / 195.0
        y_max = max(abs(y) for y in ys)
        # outermost field = 4.4 mm image height by the scene's field_value
        ok(
            abs(y_max - 4.4) / 4.4 < 0.02,
            f"B2: the traced magnification matches the 280 mm conjugate "
            f"(edge field lands at {y_max:.3f} mm vs 4.400; m = {m_expected:.4f})",
        )
        pos = [y for y in ys if y > 0.4]
        neg = [y for y in ys if y < -0.4]
        ok(
            len(pos) >= 2 and len(neg) >= 2 and y_max < 11.52,
            f"B3: the two device faces land on OPPOSITE sensor halves, inside the sensor "
            f"(+{min(pos) if pos else 0:.1f}..+{max(pos) if pos else 0:.1f} / "
            f"{max(neg) if neg else 0:.1f}..{min(neg) if neg else 0:.1f} mm; half-diag 11.52 x sqrt2)",
        )
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    try:
        _check_scene(ok, notes)
    except Exception as exc:  # pragma: no cover - environment
        notes.append(f"FAIL: guard raised ({type(exc).__name__}: {exc})")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("om05a split-field validation passed.")
        return 0
    print("om05a split-field validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
