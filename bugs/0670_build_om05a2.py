"""Rebuild attachment/om05a_two_side.py from scratch (0670 v2, real PYRITE 1072517).

Order matters: run this, then measure_and_refocus() TWICE, then bugs/0670_fix_flag2
(camera model + lens flip), then bugs/0670_set_fov54 LAST (a registered camera's
load sync re-derives the field, so the FOV write must come after the coupling).
The fold-view spec is injected by bugs/0670_fold_spec_om05a.py.
"""
from dataclasses import asdict
from pathlib import Path

import numpy as np

SCENE = Path("attachment/om05a_two_side.py")
LENS_FOLDER = Path("attachment/Lens/PYRITE_45_85_05x-20x_V38_1072517")

# CAD-measured object leg (face -> lens front rim): 275.4 mm total.
FACE_TO_RIM = 275.40
SEGS = [("air", 5.35), ("Outer prism 4336A", 10.5), ("air", 1.0), ("Lower prism 4337A", 15.0),
        ("air", 12.0), ("Centre prism 4338A", 18.0)]
FILTER_T = 1.0
FILTER_AFTER_REAR = 21.6


def build_layout_file():
    from KrakenOS.UI.services.machine_vision_folder_import import (
        build_surrogate_from_assets,
        render_surrogate_layout_source,
        scan_lens_folder,
    )

    model = build_surrogate_from_assets(scan_lens_folder(LENS_FOLDER), project_root=Path.cwd())
    SCENE.write_text(render_surrogate_layout_source(model), encoding="utf-8")
    print(f"real PYRITE surrogate: EFL {model.effl}, span {model.span}, discs {model.front_aperture}")


def edit_scene():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.surface_table_model import SurfaceRow

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["om"] = SCENE.resolve()
    editor.load_layout_by_name("om")

    def clone(template, **kw):
        data = asdict(template)
        data.update(kw)
        return SurfaceRow(**data)

    obj = editor.rows[0]
    glass_air = sum(t for _n, t in SEGS)
    tail = FACE_TO_RIM - glass_air
    obj.thickness = SEGS[0][1]
    obj.diameter = 22.0
    inserts = []
    for name, t in SEGS[1:]:
        glass = "AIR" if name == "air" else "N-BK7"
        inserts.append(clone(obj, surface="Standard", name=name, thickness=t, glass=glass,
                             diameter=30.0, rc=0.0, element=""))
    inserts.append(clone(obj, surface="Standard", name="to lens (unfolded RA mirror 1)",
                         thickness=tail, glass="AIR", diameter=30.0, rc=0.0, element=""))
    editor.rows[1:1] = inserts

    rear = editor.rows[-2]
    rear_gap = float(rear.thickness)
    rear.thickness = FILTER_AFTER_REAR
    filt = clone(rear, surface="Standard", name="Filter 48-926", thickness=FILTER_T,
                 glass="N-BK7", diameter=50.8, rc=0.0, element="")
    filt_exit = clone(rear, surface="Standard", name="to camera (unfolded RA mirror 2)",
                      thickness=max(rear_gap - FILTER_AFTER_REAR - FILTER_T, 40.0), glass="AIR",
                      diameter=50.8, rc=0.0, element="")
    editor.rows[-1:-1] = [filt, filt_exit]
    editor.rows[-1].diameter = 32.58
    editor.imported_camera_step_path = Path("attachment/om05a_components/camera_sv25mccxp.step").resolve()
    editor._sync_table()
    editor._write_layout_file(SCENE.resolve())
    editor.destroy()
    print("scene edited")


def measure_and_refocus():
    """0109: the image plane = the traced convergence; adjust the last air gap once."""
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    for round_i in range(2):
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["om"] = SCENE.resolve()
        editor.load_layout_by_name("om")
        try:
            editor._preview_trace_deferred_until_requested = False
        except Exception:
            pass
        system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
        rows = editor.rows
        z_img = sum(float(r.thickness) for r in rows[:-1])
        recs = []
        for rp in (getattr(bundle, "ray_paths", None) or []):
            p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
            if p.ndim == 2 and p.shape[0] >= 2 and np.all(np.isfinite(p[-2:])):
                recs.append((p[-2], p[-1], int(getattr(rp, "field_index", 0))))
        if not recs:
            editor.destroy()
            return
        zs = np.linspace(z_img - 40, z_img + 40, 801)
        best = None
        for z in zs:
            groups = {}
            for a, b, fi in recs:
                d = b - a
                if abs(d[2]) < 1e-9:
                    continue
                t = (z - a[2]) / d[2]
                groups.setdefault(fi, []).append(a[:2] + t * d[:2])
            # 0109 gotcha: group by FIELD, never by patch (that measures field spread)
            rms, n = 0.0, 0
            for pts in groups.values():
                if len(pts) > 3:
                    arr = np.asarray(pts)
                    rms += float(np.sqrt(((arr - arr.mean(axis=0)) ** 2).sum(axis=1).mean()))
                    n += 1
            if n:
                rms /= n
                if best is None or rms < best[1]:
                    best = (z, rms)
        z_best, rms_best = best
        print(f"round {round_i}: image z={z_img:.2f}, convergence z={z_best:.2f} (rms {rms_best*1000:.1f} um)")
        if round_i == 0 and abs(z_best - z_img) > 0.05:
            editor.rows[-2].thickness = float(editor.rows[-2].thickness) + (z_best - z_img)
            editor._sync_table()
            editor._write_layout_file(SCENE.resolve())
        editor.destroy()


if __name__ == "__main__":
    build_layout_file()
    edit_scene()
    measure_and_refocus()
    measure_and_refocus()
