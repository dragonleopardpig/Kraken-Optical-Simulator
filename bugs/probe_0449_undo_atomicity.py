"""bugs/0449 -- one user action = ONE undo step restoring a CONSISTENT boundary state.

flag_20260726_191350 ("...Undo, and Undo. Surrogate get seperated from the body"):
composite placement commands (add_beam_splitter_to_led runs import + CA-center +
seat/rotation settings + glue + promote + neutralize) executed SEVERAL service-level
_begin/_commit_history_capture pairs, so ONE click pushed several mid-command
snapshots; the first Undo restored a torn intermediate (surrogate rows at the
un-neutralized stations while the barrel settings pointed elsewhere). The session
recording (recording_20260726_191552, t=210.3s) shows exactly that state, matching
the flag.

Fix under test: a public command wraps its whole body in ``history_transaction()``;
inner service-level begin/commit pairs no-op while it is open, so ONE snapshot is
pushed at the outermost exit and the undo stack only ever holds USER-ACTION boundary
states. The snapshot CONTENT was never the problem -- ``_capture_editor_state``
already carries rows + per-label STEP settings + glue together; the COUNT was.

Run: DISPLAY=:87 .devenv/state/venv/bin/python bugs/probe_0449_undo_atomicity.py
"""
from __future__ import annotations

from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(("ok " if ok else "XX "), label, (" " + detail if detail else ""))
    if not ok:
        FAILURES.append(label)


def _boundary_state(app) -> dict:
    """Flush the pending history burst (idle callbacks) and capture the comparable
    slice of the editor state: rows + settings + layout file (selection/cell are
    UI chrome and legitimately drift)."""
    app.update()
    state = app._capture_editor_state()
    return {
        "rows": state.get("rows"),
        "settings": state.get("settings"),
        "current_layout_file": state.get("current_layout_file"),
    }


def _states_equal(a: dict, b: dict) -> tuple[bool, str]:
    if a == b:
        return True, ""
    detail = []
    if a.get("rows") != b.get("rows"):
        ra, rb = a.get("rows") or [], b.get("rows") or []
        detail.append(f"rows differ (len {len(ra)} vs {len(rb)})")
        for i, (x, y) in enumerate(zip(ra, rb)):
            if x != y:
                keys = [k for k in x if x.get(k) != y.get(k)][:4]
                detail.append(f"row{i}:{keys}")
                break
    sa, sb = a.get("settings") or {}, b.get("settings") or {}
    diff_keys = [k for k in set(sa) | set(sb) if sa.get(k) != sb.get(k)][:6]
    if diff_keys:
        detail.append(f"settings:{diff_keys}")
    return False, "; ".join(detail)


def _barrel_datum_offset(app):
    """Relative z between the drawn lens barrel and the front-datum row's world z --
    the 'surrogate separated from the body' fingerprint is this offset changing."""
    try:
        front = app._lens_datum_row_index("front")
        if front is None:
            return None
        z = app._row_z_positions()
        datum_z = float(z[front]) + float(app.rows[front].desp_z)
        # The datum's world pose is station+desp ONLY once the pose is baked (0433).
        # On a LIVE-fold scene it is the fold override that places it, so read that
        # transform when present -- otherwise this compares a folded barrel against a
        # straight-axis datum and reports a phantom 77 mm "tear" on the pristine scene.
        try:
            fold = app._optical_axis_fold_world_transform_for_row(front)
        except Exception:
            fold = None
        if fold is not None:
            import numpy as _np

            datum_z = float((_np.asarray(fold, dtype=float) @ _np.array([0.0, 0.0, float(z[front]), 1.0]))[2])
        mesh = app._transformed_imported_step_mesh_for_label("lens")
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            return None
        b = mesh.bounds
        return float((b[4] + b[5]) / 2.0) - datum_z
    except Exception:
        return None


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        app.update()
        depth0 = len(app._undo_stack)
        s0 = _boundary_state(app)
        offset0 = _barrel_datum_offset(app)

        # Action 1: delete the temporary RA mirror (0433 freeze inside).
        mirror1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([mirror1])
        s1 = _boundary_state(app)
        check("action 1 (delete+freeze) pushed exactly ONE undo step",
              len(app._undo_stack) == depth0 + 1, f"depth {depth0}->{len(app._undo_stack)}")
        offset1 = _barrel_datum_offset(app)
        check("barrel stays attached to the front datum across the freeze",
              offset0 is not None and offset1 is not None and abs(offset1 - offset0) < 2.0,
              f"offset {offset0} -> {offset1}")

        # Action 2: add BS plate (the composite command from the flag).
        try:
            app._select_table_indices([1], focus_index=1)
        except Exception:
            app._select_table_row(1)
        app.update()
        depth_before_add = len(app._undo_stack)
        res1 = app.add_beam_splitter_to_led(kind="plate")
        check("add #1 returned a summary", bool(res1), str(res1)[:60])
        s2 = _boundary_state(app)
        check("action 2 (add BS #1) pushed exactly ONE undo step",
              len(app._undo_stack) == depth_before_add + 1,
              f"depth {depth_before_add}->{len(app._undo_stack)}")
        offset2 = _barrel_datum_offset(app)
        print("   [info] post-add barrel/datum offset:", offset2,
              "(live add-time tear, if any, is a separate bug -- undo must still round-trip)")

        # Action 3: add BS plate again (the user's second add).
        depth_before_add2 = len(app._undo_stack)
        res2 = app.add_beam_splitter_to_led(kind="plate")
        s3 = _boundary_state(app)
        if res2:
            check("action 3 (add BS #2) pushed exactly ONE undo step",
                  len(app._undo_stack) == depth_before_add2 + 1,
                  f"depth {depth_before_add2}->{len(app._undo_stack)}")
        else:
            print("   [info] add #2 refused gracefully; continuing with 2-step chain")

        # Undo chain: every stop must equal the recorded boundary -- never a torn
        # intermediate.
        if res2:
            app.undo()
            eq, why = _states_equal(_boundary_state(app), s2)
            check("undo #1 == post-add-#1 boundary (no mid-command state)", eq, why)
        app.undo()
        eq, why = _states_equal(_boundary_state(app), s1)
        check("undo == post-delete boundary (rows+settings+glue consistent)", eq, why)
        offset_u = _barrel_datum_offset(app)
        check("barrel attached after undo (the flag's tear is impossible)",
              offset_u is not None and offset1 is not None and abs(offset_u - offset1) < 2.0,
              f"offset {offset_u} vs {offset1}")
        app.undo()
        eq, why = _states_equal(_boundary_state(app), s0)
        check("undo == pristine boundary", eq, why)

        # Redo round-trip.
        app.redo()
        eq, why = _states_equal(_boundary_state(app), s1)
        check("redo == post-delete boundary", eq, why)
        app.redo()
        eq, why = _states_equal(_boundary_state(app), s2)
        check("redo == post-add-#1 boundary", eq, why)

        # Plain-edit control: an ordinary single mutation still = one step + exact
        # round-trip (no regression to plain table undo).
        app.update()
        depth_plain = len(app._undo_stack)
        s_before = _boundary_state(app)
        app._begin_history_capture()
        app.rows[0].thickness = float(app.rows[0].thickness) + 5.0
        app._commit_history_capture()
        app.update()
        check("plain edit pushed one step", len(app._undo_stack) == depth_plain + 1,
              f"{depth_plain}->{len(app._undo_stack)}")
        app.undo()
        eq, why = _states_equal(_boundary_state(app), s_before)
        check("plain edit round-trips", eq, why)
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if FAILURES:
        print(f"FAIL: {FAILURES}")
        return 1
    print("RESULT: PASS -- one action = one undo step; every undo lands on a consistent boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
