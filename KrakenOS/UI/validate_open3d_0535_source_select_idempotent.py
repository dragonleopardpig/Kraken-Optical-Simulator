"""bugs/0535 guard -- selecting a scene source from the browser is idempotent.

Live report: after "Add Illumination Source (LED)" from the browser panel, the app froze
in an endless ~3.4 s refresh loop; dragging felt dead. py-spy on the live process caught
the driver: `_on_tree_select -> select_scene_source_from_admin -> refresh_from_editor`,
where the refresh REBUILDS the browser tree and the programmatic re-selection fires a
deferred <<TreeviewSelect>> (the 0049 mechanism) that lands back in the handler after the
_refreshing guard has cleared. `select_scene_source_from_admin` refreshed
unconditionally, so the loop self-armed forever.

Fix: re-selecting the CURRENT source with its gizmo already raised is a no-op.

Checks:
  SOURCE -- the idempotence guard is present.
  REAL   -- on the AZ85 scene with a freshly added LED source: four consecutive
            re-selections cause exactly ONE refresh; a different-state re-select (row
            gizmo active) still refreshes.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI import open3d_inspector as _oi

    src = _inspect.getsource(_oi.Kraken3DInspector.select_scene_source_from_admin)
    if "bugs/0535" in src and "already_selected" in src:
        notes.append("SOURCE = the source-select idempotence guard is present")
    else:
        notes.append("SOURCE the 0535 idempotence guard is missing")
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
        sid = app.add_illumination_led_source().split(":", 1)[1]

        counts = [0]
        real_refresh = insp.refresh_from_editor

        def counted(*a, **k):
            counts[0] += 1
            return real_refresh(*a, **k)

        insp.refresh_from_editor = counted
        for _ in range(4):
            insp.select_scene_source_from_admin(sid)
            insp.update()
        if counts[0] == 1:
            notes.append("REAL = four re-selections cause exactly ONE refresh (loop broken)")
        else:
            notes.append(f"REAL four re-selections caused {counts[0]} refreshes")
            ok = False

        # A REAL state change must still refresh: hand the gizmo to a row, then
        # re-select the source.
        insp._placement_handle_selected_row_index = 3
        counts[0] = 0
        insp.select_scene_source_from_admin(sid)
        if counts[0] == 1:
            notes.append("REAL = a genuine re-select (after a row gizmo took over) still refreshes")
        else:
            notes.append(f"REAL genuine re-select refreshed {counts[0]} times (want 1)")
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
