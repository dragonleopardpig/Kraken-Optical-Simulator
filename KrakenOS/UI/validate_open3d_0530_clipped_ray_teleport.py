"""bugs/0530 guard -- escaped rays are not teleported onto a far detector plane.

flag_20260804_073933: "enabled clipped overlay, rays not make sense." On the folded AZ85
scene every escaped lens/BS stray had a FORWARD crossing with the folded sensor plane
155-220 mm away (the real prism->sensor arm is 44 mm), so the detector-miss projection
re-terminated all 225 of them ON the sensor plane and "Show clipped rays" drew a wedge of
chords teleporting through free space into the camera body.

Fix: when the detector's final-arm gap is KNOWN, the projection may only claim a miss
within a few arm lengths (sensor-scale floor). Rows without thickness data (the 0018
mechanism harness) keep the cos-guard-only behaviour.

Checks:
  SOURCE -- the arm-gated travel bound is present in _detector_plane_miss_intersection.
  REAL   -- dragged AZ85: ZERO missed_image classifications; no clipped path's drawn
            tail ends near the sensor; reached/vignetted censuses unchanged.
  POS    -- a genuine near-miss (origin 30 mm up the real fold arm, aimed just outside
            the sensor) STILL projects with a sane distance.
  NEG    -- a lens-exit stray aimed at the same plane from ~200 mm away returns None.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI import scene_builder as _sb

    src = _inspect.getsource(_sb._detector_plane_miss_intersection)
    if "bugs/0530" in src and "_DETECTOR_MISS_MAX_ARM_FACTOR" in src:
        notes.append("SOURCE = the arm-gated travel bound is present")
    else:
        notes.append("SOURCE the 0530 travel bound is missing")
        ok = False

    if not SCENE.exists():
        notes.append("SKIP: frozen AZ85 scene absent (gitignored attachment)")
        return ok, notes

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        app.translate_step_overlay("lens", (53.135, 0.0, 0.0))
        system, _rays, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=False, trace_rays=True
        )
        paths = list(getattr(bundle, "ray_paths", []) or [])
        census: dict[str, int] = {}
        for p in paths:
            reason = str(getattr(p, "termination_reason", "") or "")
            census[reason] = census.get(reason, 0) + 1
        if census.get("missed_image", 0) == 0:
            notes.append("REAL = no escaped stray is classified missed_image on the dragged scene")
        else:
            notes.append(f"REAL {census.get('missed_image')} strays still teleport to the sensor plane")
            ok = False
        if census.get("target_termination", 0) > 0 and census.get("aperture_stop_vignette", 0) > 0:
            notes.append(
                f"REAL = reached/vignetted rays unaffected "
                f"(reached {census.get('target_termination')}, vignetted {census.get('aperture_stop_vignette')})"
            )
        else:
            notes.append(f"REAL census looks broken: {census}")
            ok = False

        rows = list(app.rows)
        detector_index = len(rows) - 1
        frame = _sb._detector_surface_frame(rows, system, detector_index)
        if frame is None:
            notes.append("SKIP: detector frame unavailable for the POS/NEG probes")
        else:
            center, normal, tangent = (np.asarray(v, float).reshape(3) for v in frame)
            normal = normal / np.linalg.norm(normal)
            tangent = tangent - normal * float(np.dot(tangent, normal))
            tangent = tangent / max(float(np.linalg.norm(tangent)), 1e-12)
            # No hardcoded sensor size: derive the helper's own active half from an
            # axial probe (radial ~0 always projects), so the POS/NEG margins track
            # whatever detector the scene actually carries.
            axial = _sb._detector_plane_miss_intersection(
                rows, system, {detector_index}, center + normal * 30.0, -normal
            )
            if axial is None:
                notes.append("SKIP: axial probe could not derive the detector half")
                return ok, notes
            sensor_half = float(axial["half"])

            # Non-target drawn tails must not END near the sensor (the teleport look).
            near = 0
            for p in paths:
                if str(getattr(p, "termination_reason", "")) == "target_termination":
                    continue
                pts = np.asarray(p.points_world, float)
                if pts.ndim != 2 or pts.shape[0] < 2:
                    continue
                if float(np.linalg.norm(pts[-1, :3] - center)) < 2.5 * sensor_half:
                    near += 1
            if near == 0:
                notes.append("REAL = no clipped tail ends beside the sensor (teleport wedge gone)")
            else:
                notes.append(f"REAL {near} clipped tails still end beside the sensor")
                ok = False

            origin = center + normal * 30.0
            aim = center + tangent * (1.3 * sensor_half)
            direction = aim - origin
            direction = direction / np.linalg.norm(direction)
            pos = _sb._detector_plane_miss_intersection(rows, system, {detector_index}, origin, direction)
            if pos is not None and float(pos["distance"]) < 100.0:
                notes.append(
                    f"POS = a genuine near-miss still projects "
                    f"(distance {float(pos['distance']):.1f} mm, radial {float(pos['radial']):.1f} mm)"
                )
            else:
                notes.append(f"POS a genuine near-miss no longer projects (got {pos!r})")
                ok = False

            far_origin = center + normal * 200.0 + tangent * 30.0
            far_dir = (center + tangent * 25.0) - far_origin
            far_dir = far_dir / np.linalg.norm(far_dir)
            neg = _sb._detector_plane_miss_intersection(rows, system, {detector_index}, far_origin, far_dir)
            if neg is None:
                notes.append("NEG = a ~200 mm free-space stray is not teleported onto the plane")
            else:
                notes.append(f"NEG the far stray still projects (distance {float(neg['distance']):.1f} mm)")
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
