"""bugs/0435 -- adding a beam splitter to the LED must not move ANY existing element.

flag_20260726_094845_383 (recording_20260726_095434): the one-click "Add Beam Splitter
to LED (plate)" grew every downstream station by the BS row's raw axial_reserve
(~62.5 mm for the 45-deg plate), so the PINNED second RA mirror (pose = station +
desp) and the sequential Image slid the moment the BS was added -- by an amount that
depended on the table selection (insert index). The user read it, correctly, as the
chain "shifting down".

Fix under test: the BS row is STATION-NEUTRAL (thickness 0; span kept in promotion
metadata), applied on add AND on resize (the replace re-promotes raw).

PASS criteria, per insert position (default / after-mirror / after-spacer):
  A. every PRE-EXISTING row's display-free override center+rotation is unchanged by
     the add (identity-matched rows; includes the Aperture's rotation -- the flip);
  B. every PRE-EXISTING row's BUILT-system TRANS_2A translation is unchanged;
  C. lens/camera STEP body bounds unchanged; BS row thickness == 0, glued + marked.
Then, end-to-end on the default-insert scene (the user's actual workflow):
  D. delete_optical_step_rows removes the first mirror (row count drops) and the
     0433 stay-put freeze holds every surviving element + STEP body in place.
Run: DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0435_bs_add_stay_put.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_pose_overrides

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
TOL = 1.0e-6
FAILURES: list[str] = []


def check(ok: bool, message: str) -> None:
    print(("ok " if ok else "XX ") + message)
    if not ok:
        FAILURES.append(message)


def fresh_app():
    app = KrakenLayoutEditor()
    app.layout_files["az85"] = SCENE
    app.load_layout_by_name("az85")
    return app


def world_state(app):
    """Identity-keyed world pose of every row (override map wins, else station+desp)
    + step body bounds. Display-free."""
    overrides = optical_solid_output_port_pose_overrides(None, app.rows)
    z = app._row_z_positions()
    state = []
    for i, row in enumerate(app.rows):
        ov = overrides.get(i)
        if isinstance(ov, dict):
            center = np.asarray(ov["center"], dtype=float).reshape(3)
            rotation = np.asarray(ov["rotation"], dtype=float).reshape(3, 3)
        else:
            center = np.asarray(
                (float(row.desp_x), float(row.desp_y), float(z[i]) + float(row.desp_z)), dtype=float
            )
            rotation = None
        state.append((str(getattr(row, "name", "")), center, rotation))
    steps = {}
    for label in ("lens", "camera", "led"):
        try:
            mesh = app._transformed_imported_step_mesh_for_label(label)
        except Exception:
            mesh = None
        if mesh is not None and int(getattr(mesh, "n_points", 0)) > 0:
            steps[label] = np.asarray(mesh.bounds, dtype=float).copy()
    return state, steps


def built_translations(app):
    system = app.build_system(require_solids=True, force_rebuild=True)
    out = []
    for i in range(len(app.rows)):
        try:
            t = np.asarray(system.Pr3D.TRANS_2A[i], dtype=float).reshape(4, 4)
            out.append(t[:3, 3].copy())
        except Exception:
            out.append(None)
    return out


def pre_index_for_post(j, inserted_at=None, removed_at=None, removed_count=0):
    """Map a post-mutation row index back to its pre-mutation index.
    The promote REBUILDS self.rows from the table, so object identity does not
    survive -- index mapping around the single known insertion/deletion window."""
    if inserted_at is not None:
        if j == inserted_at:
            return None  # the new BS row
        return j if j < inserted_at else j - 1
    if removed_at is not None:
        return j if j < removed_at else j + removed_count
    return j


def scenario_add(select_index, label):
    app = fresh_app()
    try:
        pre_state, pre_steps = world_state(app)
        pre_built = built_translations(app)
        if select_index is not None:
            app._select_table_indices([select_index], focus_index=select_index)
        result = app.add_beam_splitter_to_led("plate")
        check(isinstance(result, dict), f"{label}: add_beam_splitter_to_led returned a summary")
        if not isinstance(result, dict):
            return None
        bs_index = int(result["row_index"])
        post_state, post_steps = world_state(app)
        post_built = built_translations(app)

        moved = []
        for j in range(len(post_state)):
            i = pre_index_for_post(j, inserted_at=bs_index)
            if i is None or i >= len(pre_state):
                continue
            name, center, rotation = pre_state[i]
            name2, c2, r2 = post_state[j]
            if name != name2:
                moved.append(f"S{i}->S{j}: name mismatch {name!r} vs {name2!r}")
                continue
            if not np.allclose(center, c2, atol=TOL):
                moved.append(f"{name}: center {np.round(center,3)} -> {np.round(c2,3)}")
            if rotation is not None and r2 is not None and not np.allclose(rotation, r2, atol=TOL):
                moved.append(f"{name}: ROTATION changed (the aperture-flip class)")
        check(not moved, f"{label}: A. no pre-existing row moved/rotated on add" + ("; " + "; ".join(moved[:4]) if moved else ""))

        built_moved = []
        for j in range(len(post_built)):
            i = pre_index_for_post(j, inserted_at=bs_index)
            if i is None or i >= len(pre_built):
                continue
            t, t2 = pre_built[i], post_built[j]
            if t is None or t2 is None:
                continue
            if not np.allclose(t, t2, atol=1.0e-4):
                built_moved.append(f"{pre_state[i][0]}: built {np.round(t,2)} -> {np.round(t2,2)}")
        check(not built_moved, f"{label}: B. built TRANS translations unchanged" + ("; " + "; ".join(built_moved[:4]) if built_moved else ""))

        step_moved = [
            f"{k}: bounds moved" for k in pre_steps
            if k in post_steps and not np.allclose(pre_steps[k], post_steps[k], atol=1.0e-4) and k != "led"
        ]
        check(not step_moved, f"{label}: C. lens/camera STEP bodies unchanged" + ("; " + "; ".join(step_moved) if step_moved else ""))

        bs_row = app.rows[bs_index]
        check(abs(float(bs_row.thickness)) <= TOL, f"{label}: BS row is station-neutral (thickness 0, got {float(bs_row.thickness):g})")
        promo = (getattr(bs_row, "advanced", {}) or {}).get("StepOverlayPromotion") or {}
        check(bool(promo.get("beam_splitter")), f"{label}: BS row keeps the beam_splitter mark")
        check(bool(getattr(app, "_optical_led_glued", False)), f"{label}: BS is glued to the LED")
        return app
    finally:
        if select_index is not None:
            try:
                app.destroy()
            except Exception:
                pass


def main() -> int:
    # A/B/C across insert positions: default (end slot), after the mirror, after the spacer.
    scenario_add(1, "insert@2")
    scenario_add(2, "insert@3")
    app = scenario_add(None, "insert@default")
    if app is None:
        print("FAIL: default add did not complete")
        return 1
    try:
        # D. the user's actual workflow: now delete the temporary mirror -> freeze holds.
        from KrakenOS.UI.services.paraxial_tools import _row_is_promoted_mirror_fold

        pre_state, pre_steps = world_state(app)
        mirror_rows = [i for i, r in enumerate(app.rows) if _row_is_promoted_mirror_fold(r)]
        check(len(mirror_rows) >= 2, f"delete: found the two mirrors {mirror_rows}")
        n_before = len(app.rows)
        removed_at = mirror_rows[0]
        removed = app.delete_optical_step_rows([removed_at])
        check(removed >= 1 and len(app.rows) < n_before, f"delete: mirror row removed (rows {n_before} -> {len(app.rows)})")

        post_state, post_steps = world_state(app)
        removed_count = n_before - len(app.rows)
        held, moved = 0, []
        for j in range(len(post_state)):
            i = pre_index_for_post(j, removed_at=removed_at, removed_count=removed_count)
            if i is None or i >= len(pre_state):
                continue
            name, center, _rot = pre_state[i]
            name2, c2, _ = post_state[j]
            if name != name2:
                moved.append(f"S{i}->S{j}: name mismatch {name!r} vs {name2!r}")
            elif np.allclose(center, c2, atol=1.0e-4):
                held += 1
            else:
                moved.append(f"{name}: {np.round(center,2)} -> {np.round(c2,2)}")
        check(not moved and held >= 8, f"delete: 0433 freeze holds every surviving element ({held} held)" + ("; " + "; ".join(moved[:4]) if moved else ""))
        step_moved = [
            k for k in pre_steps
            if k in post_steps and not np.allclose(pre_steps[k], post_steps[k], atol=1.0e-3)
        ]
        check(not step_moved, f"delete: STEP bodies stay put ({sorted(post_steps)})" + ("; moved: " + ",".join(step_moved) if step_moved else ""))
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    print()
    if FAILURES:
        print(f"RESULT: FAIL ({len(FAILURES)} failure(s))")
        return 1
    print("RESULT: PASS -- BS add is station-neutral; add->delete workflow stays put end-to-end")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
