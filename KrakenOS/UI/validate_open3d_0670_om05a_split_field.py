"""Guard for bugs/0670 -- the om05a two-side split-field station: one chain, two
device faces, one camera.

User (2026-08-31): "The reason I needed a 3D object rather than 2D plane is that I
need to inspect object opposite 2-side" -- the om05a assembly (Prism Assembly + RA
mirror + MV85 imaging lens + filter + RA mirror + 25MP camera). Unfolding its five
folds yields ONE sequential chain (0297: one shared first order): the two opposite
device end faces sit SIDE BY SIDE in one object plane (the CAD's equal path lengths
guarantee one conjugate), pass the three prism glasses as plates, the REAL PYRITE
4.5/85 0.5x-2.0x V38 (1072517, user-identified; exact two-group from its datasheet
SF/S'F'/span), the 48-926 filter, and land on opposite halves of the one sensor.
The folds are geometry, not prescription; the focus is the TRACED convergence
(0109). The measured |m| 0.430 = an effective glass-corrected conjugate of 283 mm --
the assembly lens's own "LEN-MV85-280" designation recovered from CAD + physics.

Checks (scene checks skip when the attachment scene is absent -- it is Filen-synced,
not git-tracked):
  A  PRESCRIPTION: the scene carries the three prism plates + the filter as N-BK7
     glass, the 25MP sensor diagonal, discs within the lens barrel, and the CAD
     component STEPs wired for display.
  B  TRACE (the physics pins): per-FIELD rms at the sensor < 5 um (in focus); the
     MEASURED |m| recovers the 280 mm designation within 12 mm; a real INVERTED
     image with the two face patches on OPPOSITE sensor halves, inside the sensor.

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
            "camera_sv25mccxp" in cam and "1072517" in lens,
            f"A4: the real CAD bodies are wired (camera SV25 + PYRITE 1072517 barrel)",
        )

        # B: trace physics
        try:
            editor._preview_trace_deferred_until_requested = False
        except Exception:
            pass
        system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
        z_img = sum(float(r.thickness) for r in rows[:-1])
        groups: dict[int, list] = {}
        for rp in (getattr(bundle, "ray_paths", None) or []):
            p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
            if p.ndim != 2 or p.shape[0] < 2 or not np.all(np.isfinite(p[-2:])) or not np.all(np.isfinite(p[0])):
                continue
            a, b = p[-2], p[-1]
            d = b - a
            if abs(d[2]) < 1e-9:
                continue
            t = (z_img - a[2]) / d[2]
            groups.setdefault(int(getattr(rp, "field_index", 0)), []).append((float(p[0][1]), a[:2] + t * d[:2]))
        cents = {}
        obj_y = {}
        rms_all = []
        for fi, recs in groups.items():
            arr = np.asarray([r[1] for r in recs])
            if len(arr) < 4:
                continue
            cents[fi] = arr.mean(axis=0)
            obj_y[fi] = float(np.mean([r[0] for r in recs]))
            rms_all.append(float(np.sqrt(((arr - arr.mean(axis=0)) ** 2).sum(axis=1).mean())))
        ok(
            rms_all and max(rms_all) < 0.005,
            f"B1: every field is IN FOCUS at the sensor (worst per-field rms "
            f"{max(rms_all) * 1000 if rms_all else float('nan'):.1f} um < 5)",
        )
        ms = [abs(cents[fi][1] / obj_y[fi]) for fi in cents if abs(obj_y[fi]) > 1.0]
        m_meas = float(np.mean(ms)) if ms else float("nan")
        conj = 85.13 * (1.0 + 1.0 / m_meas) if ms else float("nan")
        fov = 23.04 / m_meas if ms else float("nan")
        ok(
            ms and 0.41 <= m_meas <= 0.45 and abs(conj - 280.0) <= 12.0 and abs(fov - 54.0) <= 1.0,
            f"B2: the MEASURED magnification recovers the lens's designation and the user's FOV "
            f"(|m| {m_meas:.4f}, conjugate {conj:.1f} mm ~ LEN-MV85-280, FOV {fov:.1f} ~ 54 x 54)",
        )
        inverted = all(cents[fi][1] * obj_y[fi] < 0 for fi in cents if abs(obj_y[fi]) > 1.0)
        ys = sorted(c[1] for c in cents.values())
        y_max = max(abs(y) for y in ys)
        pos = [y for y in ys if y > 0.4]
        neg = [y for y in ys if y < -0.4]
        # A REGISTERED camera re-couples the field on every load to its image-circle
        # half-diagonal (16.29) -- the app's own coverage convention; pin that circle.
        ok(
            inverted and len(pos) >= 2 and len(neg) >= 2 and y_max <= 16.4,
            f"B3: a REAL inverted image; the coupled camera's coverage fills the image circle and "
            f"the two faces land on OPPOSITE halves "
            f"(+{min(pos) if pos else 0:.1f}..+{max(pos) if pos else 0:.1f} / "
            f"{max(neg) if neg else 0:.1f}..{min(neg) if neg else 0:.1f} mm; half-diag 16.29)",
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
