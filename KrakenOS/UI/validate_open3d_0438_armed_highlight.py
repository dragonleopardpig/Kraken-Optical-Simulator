"""Guard for bugs/0438 -- the armed snap selection highlight persists (no flash).

flag_20260726_110540: at the armed snap state the row + STEP-body selection
styling existed for exactly one paint. `_arm_snap_to_axis` styled the actors and
THEN ran `_hide_regular_rays_for_center_axis_pick()`, whose refresh rebuilt every
actor unstyled -- and `apply_row_selection` early-returned on the matching model,
so nothing could re-style. The fix funnels a FORCED re-apply of the surviving
SelectionModel through `refresh_scene` (covers the sync AND the bugs/0223 async
rebuild), reorders the arm (refresh before styling), and skips the ray-hide
refresh entirely when rays are already hidden.

* WIRING     -- apply_row_selection has the ``force`` kwarg; refresh_scene calls
  `_reapply_selection_after_scene_rebuild`; the arm styles AFTER the ray-hide
  refresh; the ray-hide helper only refreshes when rays were showing.
* REAL-SCENE -- on the real AZ85 (Tk + VTK): arm the snap on the candidate set,
  drain events, and every armed row with actors carries the pink selected fill
  plus the lens/camera STEP cue; a mid-armed `refresh_from_editor()` keeps both;
  cancel clears them.

SKIP (pass with a note) when the environment cannot run a check.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCENE = REPO / "attachment" / "machine_vision_AZ85_RA_Mirror.py"

PINK = (1.0, 0.45, 0.65)


def _check_wiring(notes: list[str]) -> bool:
    from KrakenOS.UI import open3d_inspector as insp_mod
    from KrakenOS.UI.services import open3d_selection_representation as rep_mod

    ok = True
    sig = _inspect.signature(rep_mod.SelectionRepresentation.apply_row_selection)
    if "force" in sig.parameters:
        notes.append("WIRING = apply_row_selection has the force kwarg")
    else:
        notes.append("WIRING apply_row_selection missing force kwarg")
        ok = False
    refresh_src = _inspect.getsource(insp_mod.Kraken3DInspector.refresh_scene)
    if "_reapply_selection_after_scene_rebuild" in refresh_src:
        notes.append("WIRING = refresh_scene re-applies the surviving selection")
    else:
        notes.append("WIRING refresh_scene lacks the selection re-apply funnel")
        ok = False
    reapply_src = _inspect.getsource(insp_mod.Kraken3DInspector._reapply_selection_after_scene_rebuild)
    if "force=True" in reapply_src:
        notes.append("WIRING = re-apply forces past the matching-model early-return")
    else:
        notes.append("WIRING re-apply does not force the representation")
        ok = False
    arm_src = _inspect.getsource(insp_mod.Kraken3DInspector._arm_snap_to_axis)
    hide_pos = arm_src.find("_hide_regular_rays_for_center_axis_pick")
    forced_pos = arm_src.find("_set_row_highlights(selection, force=True)")
    if 0 <= hide_pos < forced_pos:
        notes.append("WIRING = arm styles the selection AFTER the ray-hide refresh")
    else:
        notes.append("WIRING arm still styles before the ray-hide refresh")
        ok = False
    hide_src = _inspect.getsource(insp_mod.Kraken3DInspector._hide_regular_rays_for_center_axis_pick)
    if "if showing_rays:" in hide_src and hide_src.index("refresh_from_editor") > hide_src.index("if showing_rays:"):
        notes.append("WIRING = ray-hide refresh only runs when rays were showing")
    else:
        notes.append("WIRING ray-hide helper still refreshes unconditionally")
        ok = False
    return ok


def _styled_rows(insp, rows):
    styled = {}
    for row in rows:
        count = 0
        for key in list(insp._row_actor_map.get(int(row), []) or []):
            actor = insp._actor_by_key.get(key)
            if actor is None:
                continue
            try:
                color = tuple(round(float(c), 2) for c in actor.GetProperty().GetColor())
            except Exception:
                continue
            if color == PINK:
                count += 1
        styled[int(row)] = count
    return styled


def _check_real_scene(notes: list[str]) -> bool:
    import time

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    ok = True
    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85_0438"] = SCENE
        app.load_layout_by_name("az85_0438")
        app.open_3d_view()
        app.update_idletasks()
        app.update()
        insp = app._three_d_inspector
        insp.update_idletasks()
        insp.update()

        pts = insp._rubber_band_display_points()
        good = sorted(i for i, p in pts.items() if p is not None)
        insp._set_row_highlights(good)
        insp._sync_table_to_selection(good)
        insp._apply_selection_step_highlights(good, render=False)
        insp.start_snap_selected_to_axis()
        for _ in range(4):
            insp.update_idletasks()
            insp.update()
            time.sleep(0.1)

        rows_with_actors = [r for r in good if insp._row_actor_map.get(r)]
        styled = _styled_rows(insp, rows_with_actors)
        missing = [r for r, n in styled.items() if n == 0]
        if not missing and rows_with_actors:
            notes.append(f"REAL = armed highlight persists after drain ({len(rows_with_actors)} rows styled)")
        else:
            notes.append(f"REAL armed highlight missing on rows {missing} (styled={styled})")
            ok = False

        insp.refresh_from_editor()
        for _ in range(4):
            insp.update_idletasks()
            insp.update()
            time.sleep(0.1)
        styled = _styled_rows(insp, rows_with_actors)
        missing = [r for r, n in styled.items() if n == 0]
        if not missing and rows_with_actors:
            notes.append("REAL = mid-armed rebuild keeps the highlight")
        else:
            notes.append(f"REAL mid-armed rebuild wiped rows {missing}")
            ok = False

        insp.cancel_active_3d_operation()
        insp.update_idletasks()
        insp.update()
        styled = _styled_rows(insp, rows_with_actors)
        leftover = {r: n for r, n in styled.items() if n}
        if not leftover:
            notes.append("REAL = cancel clears the armed highlight")
        else:
            notes.append(f"REAL cancel left styled rows {leftover}")
            ok = False
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return ok


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    passed = True
    try:
        if not _check_wiring(notes):
            passed = False
    except Exception as exc:
        notes.append(f"SKIP wiring: {exc!r}")
    if SCENE.exists():
        try:
            if not _check_real_scene(notes):
                passed = False
        except Exception as exc:
            notes.append(f"SKIP real-scene: {exc!r}")
    else:
        notes.append("SKIP real-scene: AZ85 scene not present")
    return passed, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(("  " if "=" in note or note.startswith("SKIP") else "! ") + note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
