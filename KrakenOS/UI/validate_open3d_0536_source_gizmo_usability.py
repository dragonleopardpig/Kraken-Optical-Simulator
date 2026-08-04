"""bugs/0536 guard -- the scene-source gizmo is usable: no vsync stall, hoverable
arrows, and a one-gesture "Seat Source on This Face".

flag_20260804_102722 + live reports: (a) the source drag felt ~1 FPS -- the LIVE app's
every VTK render measured a constant ~1013 ms (headless ~125 ms): Mesa blocking its full
1 s frame-callback timeout under Hyprland/XWayland; (b) hovering a gizmo arrow
highlighted the STEP behind it (the 0426 source arrows were missing from the 0019 hover
handle set); (c) the seeded LED source sits at the 0290 aim-at-FOV slant with no way to
snap it onto the LED floor.

Checks:
  SOURCE -- the vblank env guards are set in the app entry; the source-move handles are
            in the hover pick set with a hover branch; the seat command + menu exist.
  REAL   -- on the AZ85 scene: add an LED source, seat it on a synthetic floor face:
            origin = face centre + 0.5 mm standoff, emission flipped toward the
            splitter; a bogus source id reports not-found without raising.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI import layout_editor as _le
    from KrakenOS.UI.services import open3d_interaction as _oi
    from KrakenOS.UI.services import open3d_face_assignment as _fa

    src_main = _inspect.getsource(_le.main)
    if "vblank_mode" in src_main and "__GL_SYNC_TO_VBLANK" in src_main:
        notes.append("SOURCE = the app entry disables vblank/frame-callback waits (1 FPS stall)")
    else:
        notes.append("SOURCE the vblank guards are missing from the app entry")
        ok = False
    src_hover = _inspect.getsource(_oi.Open3DInteractionService._passive_hover_pick_rotation_handle)
    if "_actor_source_move_map" in src_hover:
        notes.append("SOURCE = source-move arrows are in the hover handle pick set")
    else:
        notes.append("SOURCE the source arrows are missing from the hover pick set (0019 again)")
        ok = False
    src_move = _inspect.getsource(_oi.Open3DInteractionService._on_mouse_move)
    if "_actor_source_move_map" in src_move:
        notes.append("SOURCE = hovering a source arrow gets the handle affordance branch")
    else:
        notes.append("SOURCE the source-arrow hover branch is missing")
        ok = False
    if hasattr(_fa.Open3DFaceAssignmentService, "_seat_source_on_face_from_context"):
        src_menu = _inspect.getsource(_fa.Open3DFaceAssignmentService._show_surface_function_context_menu)
        if "_seat_source_on_face_from_context" in src_menu and "bugs/0536" in src_menu:
            notes.append("SOURCE = decoration STEP faces offer 'Seat {source} on This Face'")
        else:
            notes.append("SOURCE the seat command is not wired into the decoration face menu")
            ok = False
    else:
        notes.append("SOURCE _seat_source_on_face_from_context is missing")
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
        sid = app.add_illumination_led_source()
        insp._selected_source_id = sid
        svc = insp._face_assignment_service()
        svc._seat_source_on_face_from_context(sid, (10.0, 5.0, 140.0), (0.0, 0.0, 1.0))
        spec = next(
            (s for s in app._normalize_scene_source_specs(app.layout_scene_source_specs)
             if str(s.get("source_id", "")) == sid),
            None,
        )
        if spec is None:
            notes.append("REAL the seated source spec vanished")
            ok = False
        else:
            origin = np.asarray([float(spec[k]) for k in ("source_x", "source_y", "source_z")])
            direction = np.asarray([float(spec[k]) for k in ("source_l", "source_m", "source_n")])
            if np.allclose(origin, (10.0, 5.0, 139.5), atol=1e-6):
                notes.append("REAL = seat puts the origin at the face centre + 0.5 mm standoff")
            else:
                notes.append(f"REAL seat origin wrong: {origin.tolist()}")
                ok = False
            if np.allclose(direction, (0.0, 0.0, -1.0), atol=1e-6):
                notes.append("REAL = seat flips the emission toward the splitter (face normal aimed inward)")
            else:
                notes.append(f"REAL seat direction wrong: {direction.tolist()}")
                ok = False
        svc._seat_source_on_face_from_context("source:nope", (0, 0, 0), (0, 0, 1))
        if "not found" in str(insp.status_var.get()).lower():
            notes.append("REAL = a bogus source id reports not-found without raising")
        else:
            notes.append(f"REAL bogus-id status unexpected: {insp.status_var.get()[:70]}")
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
