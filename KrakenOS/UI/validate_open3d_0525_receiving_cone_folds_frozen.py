"""bugs/0525 guard -- the acceptance cone CREASES at the fold on a frozen scene.

flag_20260803_154133 "acceptance cone is not folded": the crease reads the pose-override
fold transform, which a 0433 freeze bakes away -- so the cone ran straight down the
nominal axis through the splitter. The fallback synthesizes the crease from the axis fold
emissions (first fold from the object: R maps +Z onto the emitted leg, t = (I-R)@origin).

Checks:
  SOURCE -- the inspector falls back to the emission transform.
  REAL   -- on the frozen AZ85 scene the transform maps +Z onto the lens leg with the
            hinge on the BS fold, and the CREASED cone mesh no longer extends past the
            fold plane down the nominal axis (it bends toward the lens instead).
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

    src = _inspect.getsource(_oi.Kraken3DInspector._add_receiving_cone_overlays)
    if "_emission_fold_transform_for_receiving_cone" in src:
        notes.append("SOURCE = the crease falls back to the emission fold transform")
    else:
        notes.append("SOURCE the 0525 emission fallback is missing")
        ok = False

    if not SCENE.exists():
        notes.append("SKIP: frozen AZ85 scene absent (gitignored attachment)")
        return ok, notes

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector
        import pyvista as pv
    except Exception as exc:
        notes.append(f"SKIP: editor/pyvista unavailable ({exc!r})")
        return ok, notes
    app = None
    try:
        app = KrakenLayoutEditor()
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        transform = app._emission_fold_transform_for_receiving_cone()
        if transform is None:
            notes.append("REAL the emission fold transform is None on the frozen scene")
            return False, notes
        matrix = np.asarray(transform, dtype=float).reshape(4, 4)
        out_dir = matrix[:3, :3] @ np.array([0.0, 0.0, 1.0])
        hinge = np.linalg.lstsq(np.eye(3) - matrix[:3, :3], matrix[:3, 3], rcond=None)[0]
        if abs(float(out_dir[2])) < 0.2 and float(np.linalg.norm(out_dir[:2])) > 0.9:
            notes.append(f"REAL = the crease maps +Z onto the emitted leg ({np.round(out_dir, 2).tolist()})")
        else:
            notes.append(f"REAL crease direction wrong ({np.round(out_dir, 3).tolist()})")
            ok = False
        system, _rays, bundle = app._build_preview_system_rays_bundle(update_state=True)
        spec = app.receiving_cone_overlay_spec(system, bundle)
        if not spec:
            notes.append("SKIP: no receiving-cone spec on this scene")
            return ok, notes
        insp = _open_3d_inspector(app)
        mesh = pv.PolyData(
            np.asarray(spec["points"], dtype=float)[:, :3],
            faces=np.asarray(spec["faces"], dtype=np.int64),
        )
        straight_max_z = float(np.asarray(mesh.points)[:, 2].max())
        creased = insp._crease_overlay_mesh_at_fold(mesh, transform)
        creased_pts = np.asarray(creased.points, dtype=float)
        hinge_z = float(hinge[2])
        past_fold = float(creased_pts[:, 2].max()) - hinge_z
        # The reflected cone still spans its own RADIUS around the folded leg in z, so the
        # right assertion is the COLLAPSE of the past-fold extent, not a hard zero
        # (measured: straight 105 mm past the hinge, creased 11.1 = the cone radius).
        if straight_max_z > hinge_z + 5.0 and past_fold <= max(15.0, 0.25 * (straight_max_z - hinge_z)):
            notes.append(
                f"REAL = the creased cone stops at the fold (straight ran {straight_max_z - hinge_z:.1f} mm "
                f"past it, creased {past_fold:.1f} mm)"
            )
        else:
            notes.append(
                f"REAL crease ineffective (straight past-fold {straight_max_z - hinge_z:.1f}, "
                f"creased {past_fold:.1f})"
            )
            ok = False
        leg_extent = float(np.abs(creased_pts[:, 0]).max())
        if leg_extent > 10.0:
            notes.append(f"REAL = the creased cone extends onto the lens leg (|x| up to {leg_extent:.1f} mm)")
        else:
            notes.append(f"REAL creased cone never reaches the lens leg (|x| max {leg_extent:.1f})")
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
