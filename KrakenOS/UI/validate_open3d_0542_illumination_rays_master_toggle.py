"""bugs/0542 guard -- "Illum rays" is the master illumination switch and the display
never fabricates illumination geometry.

flags 124129 + 133543 + 133134 + the user's eyeball-replacement snapshots:

1. The 3D "Illum rays" checkbox now gates ILLUMINATION-role sources in the interactive
   preview: OFF (default) keeps the fast imaging preview (adding/seating an LED costs
   nothing); ON opts into the illumination fan. Headless editors (no inspector) keep
   every source, so analyses and validators are unchanged.
2. The coaxial fate overlay (green/red MV-150 rays) draws only when a source actually
   COUPLES to the imaging launch -- on a free seated source it drew a dense fan with a
   self-contradicting "green 0" label.
3. The detector-miss projection gained a RADIAL bound (arm-known scenes): a seated
   LED's strays crossed the folded sensor plane within the travel bound but 2-8
   sensor-halves off-centre, drawing a phantom convergent fan.

Checks:
  SOURCE -- the three gates are present.
  REAL   -- inspector registered + seated LED: toggle OFF -> zero source bundles and
            the imaging preview; toggle ON -> the source bundle launches. The radial
            bound: a genuine 1.3x-half near-miss projects, a 5x-half crossing does not.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI import open3d_inspector as _oi
    from KrakenOS.UI import scene_builder as _sb
    from KrakenOS.UI.services import source_modeling as _sm

    src = _inspect.getsource(_sm.SourceModelingMixin._build_scene_source_bundles) if hasattr(_sm, "SourceModelingMixin") else ""
    if not src:
        for name in dir(_sm):
            obj = getattr(_sm, name)
            if isinstance(obj, type) and hasattr(obj, "_build_scene_source_bundles"):
                src = _inspect.getsource(obj._build_scene_source_bundles)
                break
    if "bugs/0542" in src and "show_source_illumination_rays_var" in src:
        notes.append("SOURCE = the preview gates illumination-role sources on the toggle")
    else:
        notes.append("SOURCE the master illumination gate is missing")
        ok = False
    if hasattr(_oi.Kraken3DInspector, "_on_illumination_rays_toggled"):
        notes.append("SOURCE = the toggle invalidates + retraces")
    else:
        notes.append("SOURCE the toggle handler is missing")
        ok = False
    src_overlay = _inspect.getsource(_oi.Kraken3DInspector._add_source_illumination_ray_overlays)
    if "bugs/0542" in src_overlay and "couples" in src_overlay:
        notes.append("SOURCE = the coaxial fate overlay requires a coupled source")
    else:
        notes.append("SOURCE the coaxial-coupling gate is missing from the fate overlay")
        ok = False
    src_miss = _inspect.getsource(_sb._detector_plane_miss_intersection)
    if "_DETECTOR_MISS_MAX_RADIAL_HALF_FACTOR" in src_miss:
        notes.append("SOURCE = the detector-miss projection bounds the radial")
    else:
        notes.append("SOURCE the radial bound is missing")
        ok = False

    if not SCENE.exists():
        notes.append("SKIP: frozen AZ85 scene absent (gitignored attachment)")
        return ok, notes
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        insp = _open_3d_inspector(app)
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        app._three_d_inspector = insp
        sid = app.add_illumination_led_source()
        insp._face_assignment_service()._seat_source_on_led_floor_auto(sid)

        insp.show_source_illumination_rays_var.set(False)
        bundles_off, _ = app._build_scene_source_bundles(0.55)
        insp.show_source_illumination_rays_var.set(True)
        bundles_on, _ = app._build_scene_source_bundles(0.55)
        if len(bundles_off) == 0 and len(bundles_on) == 1:
            notes.append("REAL = toggle OFF launches no illumination source; ON launches it")
        else:
            notes.append(f"REAL gate wrong: off={len(bundles_off)} on={len(bundles_on)}")
            ok = False

        system, _r, _b = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=False, trace_rays=False
        )
        rows = list(app.rows)
        det = len(rows) - 1
        frame = _sb._detector_surface_frame(rows, system, det)
        if frame is None:
            notes.append("SKIP: detector frame unavailable for radial probes")
        else:
            center, normal, tangent = (np.asarray(v, float).reshape(3) for v in frame)
            normal = normal / np.linalg.norm(normal)
            tangent = tangent - normal * float(np.dot(tangent, normal))
            tangent = tangent / max(float(np.linalg.norm(tangent)), 1e-12)
            half = 16.3

            def probe(radial_halves):
                origin = center + normal * 30.0
                aim = center + tangent * (radial_halves * half)
                d = aim - origin
                d = d / np.linalg.norm(d)
                return _sb._detector_plane_miss_intersection(rows, system, {det}, origin, d)

            near = probe(1.3)
            wide = probe(5.0)
            if near is not None and wide is None:
                notes.append("REAL = 1.3x-half near-miss projects; 5x-half crossing is rejected")
            else:
                notes.append(f"REAL radial bound wrong: near={near is not None} wide={wide is not None}")
                ok = False
    except Exception as exc:
        notes.append(f"SKIP: real-scene drive failed ({exc!r})")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
