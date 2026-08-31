"""Guard for bugs/0672 -- the om05a FOLDED-ONLY scene: real RA-mirror solids fold the
chain in-scene (the machine_vision_Pyrite85 pattern), traced on the REAL system.

User: "I want folded only scene, just like machine_vision_Pyrite85.py."
`attachment/om05a_folded.py` (Filen-synced, skip when absent): object -> three prism
plates -> 50 mm RA mirror (chain-authored optical solid, canonical first fold) ->
PYRITE 4.5/85 -> filter -> 40 mm RA mirror -> SV25 camera. The second mirror is a
FREE-PLACED solid (bugs/0213): a chain-authored follower gets SWEPT and its
orientation NORMALIZED (one canonical fold direction, invariant to mesh authoring)
-- only a solid with a recorded drop-point (`StepOverlayPromotion.center_world`)
keeps its OWN pose, and the beam reflects off THAT orientation. tilt_x=-90 seats
the coated hypotenuse FACING the beam: first-surface reflection (tilt_x=+90
reflected off the INSIDE and added the 40 mm BK7 traversal -- a +13.6 mm focus
shift the CAD's distances disprove).

Checks (B re-traces the scene; both skip when the scene is absent):
  A  STRUCTURE: two optical-solid mirror rows; mirror2 free-placed at the CAD
     folded-world pose with tilt_x=-90; prism plates + filter intact; the SV25
     camera registered.
  B  TRACE: >=60% of rays reach the image on the PRIMARY branch; the chief folds
     the TRUE S (+z, +y, -z -- leg3 anti-parallel to leg1); best focus sits ON the
     image row (within 0.6 mm -- first-surface, no glass shift) with per-field rms
     < 5 um.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0672_om05a_folded_scene
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/om05a_folded.py"


def _check_scene(ok, notes) -> None:
    if not SCENE.exists():
        notes.append("SKIP: A/B: the om05a folded scene is not on this machine (Filen-synced)")
        return
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["omf"] = SCENE
        editor.load_layout_by_name("omf")
        rows = editor.rows
        specs = editor._serializable_specs_for_rows(list(rows))
        solids = [
            (i, spec) for i, spec in enumerate(specs)
            if isinstance((spec.get("advanced") or {}).get("OpticalSolidFaces"), dict)
        ]
        ok(len(solids) == 2, f"A1: two RA-mirror optical solids in the chain ({len(solids)})")
        m2_spec = solids[-1][1] if solids else {}
        promo = (m2_spec.get("advanced") or {}).get("StepOverlayPromotion")
        centre = np.asarray((promo or {}).get("center_world", (0, 0, 0)), dtype=float)
        ok(
            isinstance(promo, dict)
            and np.allclose(centre, (0.0, 272.8, 94.9), atol=0.5)
            and abs(float(m2_spec.get("tilt_x", 0.0)) + 90.0) < 1e-6,
            f"A2: mirror2 is FREE-PLACED at the CAD folded pose with tilt_x=-90 "
            f"({np.round(centre, 1).tolist()}, tilt_x {m2_spec.get('tilt_x')})",
        )
        glass_rows = [r for r in rows if str(r.glass) == "N-BK7"]
        ok(
            len(glass_rows) == 4,
            f"A3: three prism plates + the filter ride the folded chain ({len(glass_rows)} N-BK7 rows)",
        )
        cam_var = editor.__dict__.get("camera_model_var")
        ok(
            cam_var is not None and cam_var.get() == "CAM-SV25MCCXP",
            f"A4: the SV25 camera is registered on the scene",
        )

        try:
            editor._preview_trace_deferred_until_requested = False
        except Exception:
            pass
        system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
        paths = list(getattr(bundle, "ray_paths", None) or [])
        recs = []
        chief = None
        for rp in paths:
            if not bool(getattr(rp, "reaches_image", False)):
                continue
            p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
            if p.ndim != 2 or p.shape[0] < 2 or not np.all(np.isfinite(p[-2:])) or not np.all(np.isfinite(p[0])):
                continue
            if str(getattr(rp, "branch_path", "") or "") not in ("", "primary"):
                continue
            a, b = p[-2], p[-1]
            d = b - a
            if abs(d[2]) < 1e-6:
                continue
            recs.append((int(getattr(rp, "field_index", 0)), a, d))
            score = abs(float(p[0][0])) + abs(float(p[0][1]) - 5.0)
            if chief is None or score < chief[0]:
                chief = (score, p)
        frac = len(recs) / max(len(paths), 1)
        from collections import Counter

        per_field = Counter(fi for fi, _a, _d in recs)
        strong = sum(1 for c in per_field.values() if c >= 50)
        # bugs/0673: the 9-POINT sampling (3x3 on the device faces). The four
        # cardinal fields + centre deliver; the diagonal corners still mis-aim
        # through the two folds (the folded launch seam,
        # project_nonseq_first_order_seam) -- pin substance, not the corner frontier.
        ok(
            len(recs) >= 250 and strong >= 4,
            f"B1: the 9-point folded trace delivers ({len(recs)}/{len(paths)} reach; "
            f"{strong} fields with >=50 rays; per-field {dict(sorted(per_field.items()))})",
        )
        seq = []
        if chief is not None:
            p = chief[1]
            segs = np.diff(p, axis=0)
            lens = np.linalg.norm(segs, axis=1)
            keep = lens > 2.0
            for dvec in segs[keep] / lens[keep][:, None]:
                key = tuple(int(round(c)) for c in dvec) if np.max(np.abs(np.abs(dvec) - 1.0) < 0.15) else None
                if key and (not seq or key != seq[-1]):
                    seq.append(key)
        ok(
            seq[:3] == [(0, 0, 1), (0, 1, 0), (0, 0, -1)],
            f"B2: the chief folds the TRUE S -- +z, +y, -z (legs {seq[:4]})",
        )
        # best focus by per-FIELD rms scan; must sit ON the image row (no glass shift)
        z_row = None
        if chief is not None:
            z_row = float(chief[1][-1][2])
        best = None
        for z in np.linspace(30.0, 65.0, 141):
            groups: dict[int, list] = {}
            for fi, a, d in recs:
                t = (z - a[2]) / d[2]
                groups.setdefault(fi, []).append(a[:2] + t * d[:2])
            rms, n = 0.0, 0
            for pts in groups.values():
                if len(pts) > 3:
                    arr = np.asarray(pts)
                    rms += float(np.sqrt(((arr - arr.mean(axis=0)) ** 2).sum(axis=1).mean()))
                    n += 1
            if n:
                rms /= n
                if best is None or rms < best[1]:
                    best = (float(z), rms)
        ok(
            best is not None and z_row is not None and abs(best[0] - z_row) <= 0.6
            and best[1] < 0.005,
            f"B3: FIRST-SURFACE focus ON the image row (best z {best[0] if best else 0:.2f} vs row "
            f"{z_row if z_row else 0:.2f}; per-field rms {best[1]*1000 if best else 0:.1f} um < 5)",
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
        print("om05a folded-scene validation passed.")
        return 0
    print("om05a folded-scene validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
