"""END TO END through the real fov_solve, starting from the user's SAVED refusal scene.

GUARDED on purpose: the preview trace can use a spawn-context worker pool, and spawn re-imports
the launching script in every worker -- an unguarded probe re-runs itself once per worker."""
import sys
import time
from pathlib import Path
from types import SimpleNamespace

# measured on a FRESH load of the shipped om05a_folded.py
REF = {52.5: {7: 166.6231, 12: 23.6414, 14: 42.9155, "seat": -257.3315},
       21.0: {7: 50.2344, 12: 79.6812, 14: 103.2643, "seat": -196.9827}}


def main(scene: str) -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.inspection_part import normalize_inspection_part_spec
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    app = KrakenLayoutEditor()
    app.layout_files["r"] = Path(scene)
    app.load_layout_by_name("r")
    qe = QuickEstimationService(SimpleNamespace(editor=app))

    def state():
        out = {i: round(float(app.rows[i].thickness), 4) for i in (7, 12, 14, 23)}
        out["seat"] = round(float(app.rows[15].desp_x), 4)
        return out

    def fingerprint():
        return tuple((repr(r.thickness), repr(r.desp_x), repr(r.desp_y), repr(r.desp_z)) for r in app.rows)

    def set_device(w):
        spec = dict(normalize_inspection_part_spec(getattr(app, "inspection_part_spec", None)))
        spec.update(width_mm=w, depth_mm=w, height_mm=1.0, enabled=True, axis_offset_mm=0.0)
        app.inspection_part_spec = normalize_inspection_part_spec(spec)

    print(f"loaded {scene}: |m|={app._current_finite_paraxial_magnification():.4f}  {state()}", flush=True)
    for device, field in ((50.0, 52.5), (20.0, 21.0), (50.0, 52.5), (4.0, 4.2), (90.0, 94.5), (50.0, 52.5)):
        set_device(device)
        before, t0 = fingerprint(), time.time()
        ok, msg = qe.fov_solve("object", "thickness", field, 1.05)
        m = app._current_finite_paraxial_magnification()
        now = state()
        print(f"\n[{device:g} mm device] solve {field:g}: ok={ok}  |m|={m if m is None else round(m, 5)}  ({time.time() - t0:.0f} s)", flush=True)
        print(f"   {now}")
        ref = REF.get(field)
        if ref and ok:
            print("   vs FRESH-load solve of the same field: " + "  ".join(f"{k}: {now[k] - ref[k]:+.4f}" for k in ref))
        if not ok:
            print(f"   scene byte-identical after the refusal: {fingerprint() == before}")
            info = app.__dict__.get("_fov_solve_refusal_info") or {}
            print("   facts: " + str({k: v for k, v in info.items() if k.startswith(("stage_first", "make_room", "leg_room", "lens_move"))}))
        print(f"   msg: {str(msg)[:520]}", flush=True)
    app.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "attachment/om05a_folded_refusal.py"))
