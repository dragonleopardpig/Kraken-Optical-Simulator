"""Guard for bugs/0436 -- rubber-band select + snap-to-axis fixes.

Encodes the flag_20260726_095147 / _095224 session findings:

* PURE-CORE  -- `expand_rows_to_lens_block` group integrity (partial lens
  selections expand to the whole front..rear datum block, never tear it).
* WIRING     -- `_complete_rubber_band_select` routes the table sync through
  `_sync_table_to_selection` (multi-row + 3D-sync suppression) instead of the
  selection-collapsing `_select_table_row(rows[0])`; `_arm_snap_to_axis`
  carries the group-expansion + <2 guard + STEP-body cue re-light;
  `_apply_snap_rows_to_axis` has the <2 belt guard.
* REAL-SCENE -- on the real AZ85 layout (Tk + VTK): the Image row is a
  rubber-band candidate with a display point; the multi-selection survives
  the table sync; the chained variant arms with the full set; a 1-row snap
  is refused at both gates with nothing moved.

SKIP (pass with a note) when the environment cannot run a check -- the gate
must never false-block on machines without the scene/OCC/display.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCENE = REPO / "attachment" / "machine_vision_AZ85_RA_Mirror.py"


def _check_pure_core(notes: list[str]) -> bool:
    from KrakenOS.UI.open3d_inspector import expand_rows_to_lens_block

    ok = True
    cases = [
        (([3, 4], 3, 7), ([3, 4, 5, 6, 7], True), "partial block expands"),
        (([3, 4, 5, 6, 7], 3, 7), ([3, 4, 5, 6, 7], False), "full block no-op"),
        (([8, 9], 3, 7), ([8, 9], False), "outside block untouched"),
        (([4, 9], 3, 7), ([3, 4, 5, 6, 7, 9], True), "partial + image keeps image"),
        (([], 3, 7), ([], False), "empty selection no-op"),
        (([2], None, None), ([2], False), "missing datums no-op"),
    ]
    for args, want, label in cases:
        got = expand_rows_to_lens_block(*args)
        if (sorted(got[0]), bool(got[1])) == (sorted(want[0]), want[1]):
            notes.append(f"PURE-CORE = {label}")
        else:
            notes.append(f"PURE-CORE {label}: got {got}, want {want}")
            ok = False
    return ok


def _check_wiring(notes: list[str]) -> bool:
    from KrakenOS.UI import open3d_inspector as mod

    ok = True
    complete_src = _inspect.getsource(mod.Kraken3DInspector._complete_rubber_band_select)
    if "_sync_table_to_selection" in complete_src and "_select_table_row(int(rows[0]))" not in complete_src:
        notes.append("WIRING = completion syncs the table without collapsing the selection")
    else:
        notes.append("WIRING completion still uses the collapsing _select_table_row path")
        ok = False
    if "_expand_selection_rows_for_groups" in complete_src:
        notes.append("WIRING = completion expands partial lens-group selections")
    else:
        notes.append("WIRING completion lacks the lens-group expansion")
        ok = False
    arm_src = _inspect.getsource(mod.Kraken3DInspector._arm_snap_to_axis)
    # bugs/0439 updated the guard: empty selections refused, ONE row arms translate-only,
    # >=2 rigid; group expansion still applies before the count is judged.
    if (
        "len(selection) == 1" in arm_src
        and "not selection" in arm_src
        and "_expand_selection_rows_for_groups" in arm_src
    ):
        notes.append("WIRING = arm refuses empty, arms 1-row translate-only, expands groups")
    else:
        notes.append("WIRING arm lacks the 0439 guard shape / group expansion")
        ok = False
    if "_apply_selection_step_highlights" in arm_src:
        notes.append("WIRING = arm re-lights the lens/camera STEP cue after the clear")
    else:
        notes.append("WIRING arm does not re-light the STEP-body cue")
        ok = False
    apply_src = _inspect.getsource(mod.Kraken3DInspector._apply_snap_rows_to_axis)
    if "not selection" in apply_src and "translate-only" in apply_src:
        notes.append("WIRING = apply refuses empty selections (1-row passes through translate-only)")
    else:
        notes.append("WIRING apply lacks the 0439 empty-selection belt guard")
        ok = False
    return ok


def _check_real_scene(notes: list[str]) -> bool:
    import numpy as np

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.open3d_inspector import rubber_band_rows_in_rect

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        app.open_3d_view()
        app.update_idletasks()
        app.update()
        insp = app._three_d_inspector
        if insp is None or not insp.available:
            notes.append("SKIP real-scene: embedded 3D inspector unavailable")
            return True
        insp.deiconify()
        insp.update_idletasks()
        insp.update()

        ok = True
        pts = insp._rubber_band_display_points()
        good = {i: p for i, p in pts.items() if p is not None}
        image_row = next(
            (i for i in range(len(app.rows) - 1, -1, -1) if getattr(app.rows[i], "surface", None) == "Image"),
            None,
        )
        if image_row in good:
            notes.append("REAL = Image row is a rubber-band candidate with a display point")
        else:
            notes.append(f"REAL Image row missing from candidates ({sorted(good)})")
            ok = False
        if not good:
            notes.append("SKIP real-scene: no candidate display points (render inactive?)")
            return ok
        xs = [p[0] for p in good.values()]
        ys = [p[1] for p in good.values()]
        rows = rubber_band_rows_in_rect(pts, (min(xs) - 5, min(ys) - 5), (max(xs) + 5, max(ys) + 5))
        insp._set_row_highlights(rows)
        insp._sync_table_to_selection(rows)
        app.update_idletasks()
        app.update()
        if sorted(insp._picked_row_indices) == sorted(rows):
            notes.append("REAL = multi-selection survives the table sync (no {min} collapse)")
        else:
            notes.append(
                f"REAL selection collapsed: picked {sorted(insp._picked_row_indices)} vs rows {sorted(rows)}"
            )
            ok = False
        insp._rubber_band_select_mode = True
        insp._rubber_band_chain_snap = True
        orig = insp._tk_xy_to_vtk_display_xy
        insp._tk_xy_to_vtk_display_xy = lambda xy: xy
        try:
            insp._complete_rubber_band_select((min(xs) - 5, min(ys) - 5), (max(xs) + 5, max(ys) + 5))
        finally:
            insp._tk_xy_to_vtk_display_xy = orig
        armed_sel = sorted(int(i) for i in (getattr(insp, "_snap_rows_selection", []) or []))
        if getattr(insp, "_snap_rows_to_axis_pick_mode", False) and armed_sel == sorted(rows):
            notes.append("REAL = chained variant arms with the FULL selection")
        else:
            notes.append(f"REAL chained arm carried {armed_sel} (want {sorted(rows)})")
            ok = False
        # Semantics updated by bugs/0439: ONE row (outside the lens block, which would
        # expand) arms as a TRANSLATE-ONLY snap and the apply slides it onto the axis
        # at the click point, orientation kept, other rows untouched. A lens-block row
        # still expands to the whole block (group integrity, asserted above).
        lone = rows[-1]  # the mirror / trailing member -- not inside the lens block
        insp._snap_rows_to_axis_pick_mode = False
        insp._snap_rows_selection = []
        insp._arm_snap_to_axis([lone], "selected")
        if getattr(insp, "_snap_rows_to_axis_pick_mode", False) and "single element" in insp.status_var.get():
            notes.append("REAL = 1-row arm accepted as translate-only")
        else:
            notes.append(f"REAL 1-row arm state unexpected: {insp.status_var.get()[:60]}")
            ok = False
        lone_row = app.rows[lone]
        tilts_before = (float(lone_row.tilt_x), float(lone_row.tilt_y), float(lone_row.tilt_z))
        others_before = [
            (float(r.desp_x), float(r.desp_y), float(r.desp_z)) for i, r in enumerate(app.rows) if i != lone
        ]
        insp._apply_snap_rows_to_axis(
            {
                "axis_id": "axis:global:split",
                "points": np.array([(0.0, 0.0, 37.3), (100.0, 0.0, 37.3)]),
                "picked_world": np.array([60.0, 0.0, 37.3]),
            }
        )
        z_now = app._row_z_positions()
        lone_center = np.array(
            [float(lone_row.desp_x), float(lone_row.desp_y), float(z_now[lone]) + float(lone_row.desp_z)]
        )
        tilts_after = (float(lone_row.tilt_x), float(lone_row.tilt_y), float(lone_row.tilt_z))
        others_after = [
            (float(r.desp_x), float(r.desp_y), float(r.desp_z)) for i, r in enumerate(app.rows) if i != lone
        ]
        if (
            np.allclose(lone_center, (60.0, 0.0, 37.3), atol=1e-6)
            and tilts_before == tilts_after
            and others_before == others_after
            and not getattr(insp, "_snap_rows_to_axis_pick_mode", False)
        ):
            notes.append("REAL = 1-row apply translate-only onto the clicked point; others untouched")
        else:
            notes.append(f"REAL 1-row translate-only unexpected: center={lone_center.round(2).tolist()}")
            ok = False
        return ok
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    passed = True
    try:
        if not _check_pure_core(notes):
            passed = False
    except Exception as exc:
        notes.append(f"SKIP pure-core: {exc!r}")
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
