"""END TO END through the real fov_solve: the user's 50 mm -> 20 mm -> 50 mm path on
attachment/om05a_folded.py (or a saved scene given on the command line).

GUARDED on purpose: the preview trace can use a spawn-context worker pool, and spawn re-imports
the launching script in every worker -- an unguarded probe re-runs itself once per worker.

The device size goes through the REAL ``set_inspection_part_spec`` (bugs/0846): it moves the
object row with the device face (20 mm puts face A at z=-15, 50 mm at z=0). The first version
of this script assigned ``inspection_part_spec`` directly, so its 21 mm solves ran against the
50 mm device's object face and disagreed with the app by 15 mm -- which briefly read as a 24%
field-fill correction in the app. It was the harness."""
import sys
import time
from pathlib import Path
from types import SimpleNamespace

# 52.5: a FRESH load of the shipped om05a_folded.py (50 mm device). 21: the user's own live
# 20 mm solve, flag_20260921_162616 -- the geometry om05a_folded_refusal.py was saved with.
REF = {52.5: {7: 166.6231, 12: 23.6414, 14: 42.9155, "seat": -257.3315},
       21.0: {7: 35.2344, 12: 79.6812, 14: 118.2643, "seat": -181.9827}}


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
        spec.update(width_mm=w, depth_mm=w, height_mm=1.0, enabled=True)
        app.set_inspection_part_spec(spec)   # the real callback: it moves the object face

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
        if ok:
            from KrakenOS.UI.services.detector_coverage_overlay import format_focus_summary_lines

            summary = app.__dict__.get("_solve_summary_info")
            print(f"   summary: {summary}")
            for line in format_focus_summary_lines(None, summary):
                print(f"   banner| {line}")
    app.destroy()
    return 0


if __name__ == "__main__":
    # Default: the shipped scene, the user's own path (50 mm -> 20 mm -> 50 mm). Pass a saved
    # scene to start from it instead.
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "attachment/om05a_folded.py"))
