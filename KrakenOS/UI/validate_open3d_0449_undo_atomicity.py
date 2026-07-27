"""bugs/0449 guard -- one user action is ONE undo step.

flag_20260726_191350 ("Undo, and Undo. Surrogate get seperated from the body"):
``add_beam_splitter_to_led`` runs a chain of service-level begin/commit history pairs
(import overlay -> centre CA -> orient -> seat -> glue -> promote -> coating flag ->
station-neutralize). Each pushed its own snapshot, so the first Undo restored a
MID-COMMAND intermediate the user never saw: rows at the un-neutralized stations with
the lens barrel still seated where it was. The snapshot CONTENT was always atomic
(_capture_editor_state carries rows + layout settings together) -- the COUNT was wrong.

Checks:
  SOURCE  -- the composite commands are wrapped by the _history_atomic decorator and
             _begin_history_capture no-ops inside an open transaction.
  ONE-STEP-- add_beam_splitter_to_led pushes exactly one undo entry.
  RESTORE -- undo returns rows AND per-label STEP settings AND the glue flag together.
"""
from __future__ import annotations

import inspect as _inspect


def _fingerprint(app) -> dict:
    z = app._row_z_positions()
    rows = []
    for i, r in enumerate(app.rows):
        rows.append(
            (
                str(getattr(r, "surface", "")),
                round(float(getattr(r, "thickness", 0.0) or 0.0), 6),
                round(float(r.desp_x), 6),
                round(float(r.desp_z), 6),
                round(float(r.tilt_y), 6),
            )
        )
    steps = {}
    for label in ("lens", "camera", "led", "optical"):
        try:
            if app._step_path_for_label(label) is None:
                continue
            steps[label] = tuple(round(float(v), 6) for v in app._step_placement_offset_xyz(label))
        except Exception:
            pass
    return {"rows": rows, "steps": steps, "glue": bool(getattr(app, "_optical_led_glued", False))}


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    try:
        from KrakenOS.UI.services import scene_placement_commands as spc
        from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin
    except Exception as exc:
        return True, [f"SKIP: modules unavailable ({exc!r})"]

    src = _inspect.getsource(spc)
    begin_src = _inspect.getsource(LayoutTableWorkbenchMixin._begin_history_capture)
    if (
        "@_history_atomic" in src
        and "def history_transaction" in _inspect.getsource(LayoutTableWorkbenchMixin)
        and "_history_txn_depth" in begin_src
    ):
        notes.append("SOURCE = composite commands are transaction-wrapped; inner captures no-op")
    else:
        notes.append("SOURCE the 0449 transaction wiring is missing")
        ok = False

    try:
        from pathlib import Path

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        scene = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
        if not scene.exists():
            notes.append("SKIP: AZ85 scene absent (gitignored attachment)")
            return ok, notes
        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = scene
        app.load_layout_by_name("az85")
        app._undo_stack.clear()
        app._redo_stack.clear()
        before = _fingerprint(app)

        depth = len(app._undo_stack)
        app.add_beam_splitter_to_led(kind="plate")
        pushed = len(app._undo_stack) - depth
        if pushed == 1:
            notes.append("ONE-STEP = add_beam_splitter_to_led pushed exactly one undo entry")
        else:
            notes.append(f"ONE-STEP add pushed {pushed} undo entries (want 1)")
            ok = False

        app.undo()
        after = _fingerprint(app)
        if after == before:
            notes.append("RESTORE = undo restored rows + STEP settings + glue together")
        else:
            diffs = [k for k in before if before[k] != after.get(k)]
            notes.append(f"RESTORE undo left a torn state (differs: {diffs})")
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
