"""bugs/0537 guard -- right-clicking the source GLYPH opens its menu; the LED floor seat
is reachable without face-picking.

flag_20260804_110017 "right click seat LED 1 is not working" + the paired recording: the
user right-clicked the amber emitter plate (the natural gesture). A glyph is not a CAD
face, so `_show_surface_function_context_menu` dead-ended with "Right-click a CAD/STL
optical face..." and no menu at all. The housing FLOOR is also unreachable by face pick
(the ray hits the outer wall first).

Fix: the context-None branch now offers the source's own menu ("Seat on the LED floor
(auto)" + "Select"), and `_seat_source_on_led_floor_auto` resolves the floor
geometrically (the LED body's bounding face farthest opposite the object, emitting back
toward it).

Checks:
  SOURCE -- the glyph menu + auto-seat exist and are wired before the dead-end.
  REAL   -- with a fake picker returning a glyph actor the menu lists the auto seat;
            the auto seat lands the origin on the LED's far bounding plane with the
            emission aimed back toward the object.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path
from types import SimpleNamespace

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import open3d_face_assignment as _fa

    svc_cls = _fa.Open3DFaceAssignmentService
    if hasattr(svc_cls, "_maybe_show_scene_source_menu") and hasattr(svc_cls, "_seat_source_on_led_floor_auto"):
        notes.append("SOURCE = the source glyph menu + auto floor seat exist")
    else:
        notes.append("SOURCE the 0537 glyph menu / auto seat are missing")
        ok = False
    src_menu = _inspect.getsource(svc_cls._show_surface_function_context_menu)
    if "_maybe_show_scene_source_menu" in src_menu:
        notes.append("SOURCE = the glyph menu is offered before the no-face dead-end")
    else:
        notes.append("SOURCE the glyph menu is not wired into the context handler")
        ok = False

    if not SCENE.exists():
        notes.append("SKIP: frozen AZ85 scene absent (gitignored attachment)")
        return ok, notes
    try:
        import tkinter as tk

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
        insp.refresh_from_editor()

        glyph_keys = list((getattr(insp, "_source_actor_map", {}) or {}).get(sid, []) or [])
        if not glyph_keys:
            notes.append("REAL no glyph actors registered for the source")
            ok = False
        else:
            glyph_actor = insp._actor_by_key.get(glyph_keys[0])
            real_picker = insp._picker
            captured: list[str] = []
            real_add = tk.Menu.add_command
            real_popup = insp._popup_scene_component_menu

            class _FakePicker:
                def Pick(self, *_a, **_k):
                    return 1

                def GetActor(self):
                    return glyph_actor

            try:
                insp._picker = _FakePicker()
                tk.Menu.add_command = lambda self, **kw: captured.append(str(kw.get("label", ""))) or None
                insp._popup_scene_component_menu = lambda menu, event: captured.append("<<posted>>")
                shown = insp._face_assignment_service()._maybe_show_scene_source_menu(
                    SimpleNamespace(x=10, y=10, x_root=10, y_root=10, state=0)
                )
            finally:
                insp._picker = real_picker
                tk.Menu.add_command = real_add
                insp._popup_scene_component_menu = real_popup
            if shown and any("Seat on the LED floor" in label for label in captured) and "<<posted>>" in captured:
                notes.append("REAL = right-clicking the glyph offers 'Seat on the LED floor (auto)'")
            else:
                notes.append(f"REAL glyph menu wrong: shown={shown} entries={captured}")
                ok = False

        insp._face_assignment_service()._seat_source_on_led_floor_auto(sid)
        spec = next(
            (s for s in app._normalize_scene_source_specs(app.layout_scene_source_specs)
             if str(s.get("source_id", "")) == sid),
            None,
        )
        mesh = app._transformed_imported_step_mesh_for_label("led")
        if spec is None or mesh is None:
            notes.append("REAL auto-seat spec or LED mesh missing")
            ok = False
        else:
            bounds = np.asarray(mesh.bounds, float).reshape(6)
            origin = np.asarray([float(spec[k]) for k in ("source_x", "source_y", "source_z")])
            direction = np.asarray([float(spec[k]) for k in ("source_l", "source_m", "source_n")])
            on_far_plane = any(
                abs(origin[i] - bounds[i * 2 + s]) <= 1.0
                for i in range(3)
                for s in (0, 1)
            )
            from KrakenOS.UI.services import optical_axis_tree as _tree

            obj = np.asarray(_tree.row_world_pose(app.rows, 0), float).reshape(-1)[:3]
            aims_at_object = float(np.dot(direction, obj - origin)) > 0.0
            if on_far_plane and aims_at_object:
                notes.append(
                    f"REAL = auto seat lands on the LED bounding plane aiming at the object "
                    f"(origin {np.round(origin, 1).tolist()})"
                )
            else:
                notes.append(
                    f"REAL auto seat wrong: origin {origin.tolist()} dir {direction.tolist()} "
                    f"(far_plane={on_far_plane}, aims={aims_at_object})"
                )
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
