"""bugs/0806 -- the camera seats on the lens.

flag_20260917_114837 (TCL4.0X-65DI-5M swapped onto an MV-CS050): "Please check everything correct?
Especially the lens fan out at the back of the lens."

Replayed on the user's scene (Swap Imaging Lens from Folder, the SPO folder with the vendor STEP):
the swap parked the camera 2.000 mm off the lens shoulder -- flange->sensor 19.526 mm on a
17.526 mm C-mount -- so every bundle focused 2 mm in FRONT of the sensor and fanned out again
before reaching it (48 um blur, ~11 pixels), and |m| read 4.19 instead of 4.00.

Why: the post-swap auto-refocus reserves ``clearance + flange depth`` ahead of the sensor so a
camera body cannot be solved into an upstream FOLD MIRROR (bugs/0388-0392). Here the upstream row
is the lens's own Rear Optical Vertex Datum -- the mount face the camera screws onto -- and 2 mm of
"clearance" from it is a spacer nobody fitted.

A second false alarm in the same flag: "FIELD OVERFLOWS THE SENSOR ... the field is 249.3 mm" read
the 60 mm default of an inspection part that is switched OFF in this scene.

A/B: pure mixin fixtures (no display). C: the user's scene + folder replay (needs the attachment
and the datasheet toolchain -- SKIPs loudly otherwise).
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "MV-CS050-60UM_V5_TCL4.0X-65DI-5M.py"
LENS_FOLDER = PROJECT_ROOT / "attachment" / "Information" / "RD-80000" / "Drawings" / "SPO TCL4.0X-65DI-5M"
C_MOUNT_FLANGE = 17.526


def _row(name, surface="Standard", thickness=0.0):
    return SimpleNamespace(name=name, surface=surface, thickness=float(thickness))


def _lens_block(image_gap, *, mirror=False):
    rows = [
        _row("Object", "Object", 65.0),
        _row("Front Optical Vertex Datum", thickness=5.0),
        _row("Blackbox Group 1", "Thin Lens", 47.112667),
        _row("Aperture Stop", "Aperture", 85.387333),
        _row("Blackbox Group 2", "Thin Lens", 5.0),
        _row("Rear Optical Vertex Datum", thickness=image_gap),
    ]
    if mirror:
        rows[-1].thickness = 30.0
        rows.append(_row("Promoted OPTICAL STEP optical solid (RA mirror)", thickness=image_gap))
    rows.append(_row("Image / Sensor", "Image", 0.0))
    return rows


def _editor(rows, *, standoff=C_MOUNT_FLANGE):
    import KrakenOS.UI.layout_editor  # noqa: F401 -- late-binds the workbench module's globals (np, ...)
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    ed = LayoutTableWorkbenchMixin.__new__(LayoutTableWorkbenchMixin)
    ed.rows = rows
    ed._status_messages = []
    ed.status_var = SimpleNamespace(set=ed._status_messages.append, get=lambda: "")
    ed.append_debug = lambda *_a, **_k: None
    ed._current_camera_front_to_sensor_mm = lambda: standoff
    return ed


def _bundle(ends):
    paths = []
    for end in ends:
        pts = np.array([[0.0, 0.0, 0.0], [float(end[0]), float(end[1]), 225.0]])
        paths.append(SimpleNamespace(points_world=pts, termination_reason="image"))
    return SimpleNamespace(ray_paths=paths)


def _live(ok, notes) -> None:
    if not SCENE.exists() or not LENS_FOLDER.exists():
        notes.append("SKIP C: the TCL4.0X scene / vendor folder is absent (gitignored attachment)")
        return
    app = None
    quiet = contextlib.ExitStack()
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        quiet.enter_context(contextlib.redirect_stdout(io.StringIO()))
        quiet.enter_context(contextlib.redirect_stderr(io.StringIO()))
        app = KrakenLayoutEditor(headless=True)
        app._prompt_for_missing_cad_assets = lambda: None
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        model = app.swap_imaging_lens_from_folder(str(LENS_FOLDER))
        quiet.close()
        if model is None:
            notes.append("SKIP C: the folder importer could not derive this lens here "
                         f"({app.status_var.get()[:160]}) -- run inside `devenv shell`")
            return
        front, rear = app._imaging_lens_block_indices()
        stations = np.cumsum([0.0] + [float(r.thickness) for r in app.rows])
        rear_z = float(stations[rear])
        gap = float(app.rows[rear].thickness)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            camera = app._transformed_imported_step_mesh_for_label("camera")
        ok(abs(gap - C_MOUNT_FLANGE) < 1e-3,
           f"C1: after the swap the sensor sits the C-mount flange distance behind the lens shoulder "
           f"({gap:.6f} mm, want {C_MOUNT_FLANGE} +- 1 um)")
        seat = float(camera.bounds[4]) - rear_z if camera is not None else float("nan")
        ok(abs(seat) < 0.01, f"C2: the camera's front face is ON the lens shoulder ({seat:+.4f} mm)")
        ok(not str(app.__dict__.get("_swap_clearance_note", "") or ""),
           f"C3: no 'focus limited' note on a seated camera ({app.__dict__.get('_swap_clearance_note')!r})")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            app._preview_trace_deferred_until_requested = False
            app._preview_scene_trace_dirty = True
            _s, _r, bundle = app._build_preview_system_rays_bundle(update_state=True)
        by_field: dict = {}
        for path in bundle.ray_paths or []:
            pts = np.asarray(path.points_world, dtype=float)
            by_field.setdefault(tuple(np.round(pts[0, :2], 4)), []).append(pts[-1, :3])
        spots, mags = [], []
        for launch, ends in by_field.items():
            ends = np.asarray(ends)
            spots.append(float(np.sqrt(((ends[:, :2] - ends[:, :2].mean(0)) ** 2).sum(1).mean())))
            height = float(np.hypot(*launch))
            if height > 1e-6:
                mags.append(float(np.hypot(*ends[:, :2].mean(0))) / height)
        ok(bool(spots) and max(spots) < 1e-3,
           f"C4: every field focuses ON the sensor, not 2 mm ahead of it (worst RMS "
           f"{1000 * max(spots) if spots else float('nan'):.3f} um)")
        ok(bool(mags) and all(abs(m - 4.0) < 0.02 for m in mags),
           f"C5: the delivered magnification is the datasheet 4.0x ({[round(m, 4) for m in mags]})")
    except Exception as exc:
        ok(False, f"C: the live replay raised {type(exc).__name__}: {exc}")
    finally:
        quiet.close()
        if app is not None:
            with contextlib.suppress(Exception):
                app.destroy()


def run_checks(verbose: bool = False, app=None, inspector=None, live: bool = True) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    # ---- A: the camera seats on the lens flange --------------------------------------------------
    ed = _editor(_lens_block(C_MOUNT_FLANGE))
    ok(ed._camera_seats_on_lens_flange(), "A1: a camera right after the lens block mounts on its flange")
    ok(abs(ed._swap_refocus_min_gap() - C_MOUNT_FLANGE) < 1e-9,
       f"A2: the refocus floor is the flange depth alone, no spacer ({ed._swap_refocus_min_gap()})")

    ed = _editor(_lens_block(40.0))
    ed.snap_detector_to_image_plane = lambda: (setattr(ed.rows[-2], "thickness", C_MOUNT_FLANGE) or True)
    ed._swap_auto_refocus_to_best_focus()
    ok(abs(ed.rows[-2].thickness - C_MOUNT_FLANGE) < 1e-9,
       f"A3: best focus at the flange distance stays there ({ed.rows[-2].thickness})")
    ok(not str(ed.__dict__.get("_swap_clearance_note", "") or ""),
       f"A4: and nothing claims focus was limited ({ed.__dict__.get('_swap_clearance_note')!r})")

    ed = _editor(_lens_block(40.0))
    ed.snap_detector_to_image_plane = lambda: (setattr(ed.rows[-2], "thickness", 12.526) or True)
    ed._swap_auto_refocus_to_best_focus()
    ok(abs(ed.rows[-2].thickness - C_MOUNT_FLANGE) < 1e-9
       and "focus limited" in str(ed.__dict__.get("_swap_clearance_note", "") or ""),
       f"A5: a lens that wants the sensor CLOSER than the flange still stops at the seat, and says so "
       f"({ed.rows[-2].thickness}, {ed.__dict__.get('_swap_clearance_note')!r})")

    ed = _editor(_lens_block(C_MOUNT_FLANGE))
    # the inspector's drawn datum disc, overlapping the seated camera's front face
    ed._swap_upstream_display_bounds = (-13.04, 13.04, -13.04, 13.04, 207.5, 207.5)
    ed._camera_body_world_bounds = lambda: ((-14.5, 14.5, -14.5, 14.5, 207.5, 256.3), "ok")
    deficit = ed._swap_camera_body_clearance_deficit()
    ok(deficit == 0.0 and str(ed._swap_clearance_debug.get("result", "")).startswith("seat"),
       f"A6: the datum disc is a reference plane, not a body to clear ({deficit}, "
       f"{ed._swap_clearance_debug.get('result')!r})")

    # ---- B: the fold-mirror clearance is untouched --------------------------------------------------
    ed = _editor(_lens_block(C_MOUNT_FLANGE, mirror=True))
    clearance = float(ed._SWAP_REFOCUS_MIN_CLEARANCE_MM)
    ok(not ed._camera_seats_on_lens_flange()
       and abs(ed._swap_refocus_min_gap() - (clearance + C_MOUNT_FLANGE)) < 1e-9,
       f"B1: a camera after a FOLD MIRROR still reserves clearance + flange ({ed._swap_refocus_min_gap()})")
    ed = _editor(_lens_block(C_MOUNT_FLANGE), standoff=0.0)
    ok(abs(ed._swap_refocus_min_gap() - clearance) < 1e-9,
       f"B2: with no camera glued the sensor floor is unchanged ({ed._swap_refocus_min_gap()})")

    # ---- D: the overflow banner reads only a part that is switched on --------------------------------
    for enabled in (False, True):
        ed = _editor(_lens_block(C_MOUNT_FLANGE))
        ed._current_camera_sensor_active_mm = lambda: (8.4456, 7.0656)
        ed.layout_object_fov_bands = None
        ed._solve_summary_info = {"delivered_m": 4.155}
        ed.inspection_part_spec = {"enabled": enabled, "width_mm": 60.0, "height_mm": 40.0, "depth_mm": 20.0}
        info: dict = {}
        ed._annotate_sensor_overflow(info, _bundle([(0.0, 0.0), (0.0, 3.0), (0.0, -3.0)]),
                                     (0.0, 0.0, 225.0), (0.0, 0.0, 1.0))
        record = info.get("sensor_overflow") or {}
        if enabled:
            ok(abs(float(record.get("field_half_mm", 0.0)) - 0.5 * 60.0 * 4.155) < 1e-9
               and "predicted_overflow_mm" in record,
               f"D2: an ENABLED 60 mm part still predicts its overflow ({record.get('field_half_mm')})")
        else:
            ok(bool(record) and "field_half_mm" not in record and "predicted_overflow_mm" not in record,
               f"D1: a DISABLED part is no device -- no 'FIELD OVERFLOWS' prediction ({sorted(record)})")

    if live:
        _live(ok, notes)
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0806 camera-seats-on-the-lens validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
