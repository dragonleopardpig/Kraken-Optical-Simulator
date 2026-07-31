"""bugs/0493 -- a Live-Mode drag redraws the carried leg when the gesture ends.

``flag_20260731_222802`` -- *"glued BS + LED dragged down, no elements follow."* -- on `141abba7`,
the build whose bugs/0491 guard passes. That guard drives the PROGRAMMATIC apis
(``translate_scene_row_pose`` / ``translate_step_overlay``) and everything follows. The user drives
the gizmo, and with Live Mode on that is a different story:

1. ``_flush_pending_placement_drag_for_live`` commits the accumulated offset MID-drag and zeroes
   ``pending_translate_mm`` (bugs/0024, so the live trace reflects the dragged pose).
2. That commit runs the fold carry, which moves the whole emitted leg in the model and raises
   ``_fold_carry_pending_rebuild``.
3. ``_refresh_live_preview_scene`` mid-drag refreshes RAYS ONLY -- "the bodies/handles don't change
   (the dragged one tracks the cursor via its cheap actor transform)". True when bugs/0024 wrote
   it; false once a carry started moving OTHER bodies.
4. On release ``_finish_placement_drag`` finds no tail (``pending`` is 0) and returns **without
   calling refresh_from_editor at all**. Nothing consumes the marker, and the drawing never
   catches up.

Reproduced headlessly and measured -- the model carried while every drawn thing stood still:

    MODEL row3 / row5 / row7 desp_z   +13.681        (the whole leg, not just promoted rows)
    row actors 0..8, 100000            unchanged
    STEP lens / camera / led           unchanged
    axis:global:split                  still z 53.80
    marker still pending at the end    True

which is flag_20260731_222802 exactly; 88 s and a second drag later
``flag_20260731_222930`` was still showing the same stale chain, so this is not a slow rebuild.

Note for anyone reading the flags: ``state.json`` records ``desp`` only for rows carrying a
``StepOverlayPromotion`` (``open3d_event_recorder.py``), and rows 3 and 7 are the only promoted
rows in this scene. Rows 1,2,4,5,6,8 have no model field in the snapshot at all -- so "only the
promoted rows moved" is an artifact of what the recorder dumps, NOT of the carry. Everything else
in a snapshot (``row_actor_bounds``, ``step_actor_bounds``, ``optical_axis_records``) is drawn
state.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0493_live_drag_release_redraws
"""
from __future__ import annotations

import time
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
DELTA = 13.681  # the delta flag_20260731_222802 recorded
TOL = 0.08
HOLD_S = 12.0  # a real drag holds the button long enough for queued refreshes to fire rays-only


def _settle(app, inspector, limit: float = 90.0) -> None:
    start = time.time()
    while time.time() - start < limit:
        inspector.update_idletasks()
        inspector.update()
        app.update()
        if getattr(inspector, "_row_actor_map", {}) or {}:
            break
        time.sleep(0.25)
    for _ in range(8):
        inspector.update_idletasks()
        inspector.update()
        app.update()
        time.sleep(0.25)


def _snapshot(inspector) -> dict:
    out: dict[str, tuple] = {}
    actor_by_key = getattr(inspector, "_actor_by_key", {}) or {}

    def _span(keys):
        zs: list[float] = []
        for key in list(keys or []):
            actor = actor_by_key.get(key)
            if actor is None:
                continue
            bounds = actor.GetBounds()
            if bounds and bounds[0] <= bounds[1]:
                zs.extend((bounds[4], bounds[5]))
        return (min(zs), max(zs)) if zs else None

    for row_index, keys in (getattr(inspector, "_row_actor_map", {}) or {}).items():
        span = _span(keys)
        if span:
            out[f"row{row_index}"] = span
    for label, keys in (getattr(inspector, "_step_actor_map", {}) or {}).items():
        span = _span(keys)
        if span:
            out[f"STEP:{label}"] = span
    for record in list(getattr(inspector, "_optical_axis_pick_records", None) or []):
        try:
            import numpy as np

            out[f"axis:{record.get('axis_id')}"] = tuple(
                float(v) for v in np.asarray(record.get("points"), dtype=float)[:, 2]
            )
        except Exception:
            continue
    return out


def _moved(before: dict, after: dict, key: str) -> "float | None":
    b, a = before.get(key), after.get(key)
    if b is None or a is None or len(b) != len(a) or not b:
        return None
    return sum(y - x for x, y in zip(b, a)) / float(len(b))


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    # --- A. every release branch funnels through the flush ---------------------------------
    try:
        import inspect as _inspect

        from KrakenOS.UI.open3d_inspector import Kraken3DInspector
        from KrakenOS.UI.services import open3d_mouse_bindings

        bindings_src = _inspect.getsource(open3d_mouse_bindings)
        check(
            "_flush_fold_carry_rebuild_after_drag" in bindings_src and "finally:" in bindings_src,
            "A1: left_release wraps its branches in try/finally and flushes the carry rebuild -- "
            "the eight `return \"break\"` exits cannot each be trusted to do it",
        )
        check(
            "def _left_release_body(event):" in bindings_src,
            "A2: the branch chain lives in _left_release_body, so a NEW branch is covered by "
            "construction (this family has been fixed one entry point at a time four times)",
        )
        flush_src = _inspect.getsource(Kraken3DInspector._flush_fold_carry_rebuild_after_drag)
        check(
            "_fold_carry_pending_rebuild" in flush_src,
            "A3: the flush is keyed on the sticky carry marker, so a drag that carried nothing "
            "keeps its interactive cost (bugs/0024)",
        )
        check(
            "_placement_drag_state" in flush_src and "_step_translate_drag_state" in flush_src,
            "A4: ... and never fires while any drag is still in flight",
        )
    except Exception as exc:
        notes.append(f"SKIP: source unreadable ({type(exc).__name__}: {exc})")

    if not SCENE.exists():
        notes.append("SKIP: the AZ85 BS scene is not checked out (gitignored attachment)")
        return ok, notes

    # --- B. the live gesture, end to end ---------------------------------------------------
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    try:
        editor.layout_files["live_drag_probe"] = SCENE
        editor.load_layout_by_name("live_drag_probe")
        editor.open_3d_view()
        editor.update_idletasks()
        editor.update()
        insp = getattr(editor, "_three_d_inspector", None)
        if insp is None or not getattr(insp, "available", False):
            notes.append("SKIP: the embedded 3D inspector is unavailable")
            return ok, notes
        _settle(editor, insp)
        before = _snapshot(insp)

        insp.live_mode_var.set(True)
        check(bool(insp._live_mode_enabled()), "B1: Live Mode is on -- the mode the flag was taken in")

        # Press on row 3's Z translate handle and drag: the state the gizmo builds.
        state = {
            "kind": "translate", "row_index": 3, "axis": "z", "signed_step": 1.0,
            "display_direction": (0.0, 1.0), "pixel_accumulator": 0.0,
            "applied_steps": 1, "pending_translate_mm": DELTA,
        }
        insp._placement_drag_state = state
        insp._refresh_live_preview_scene("placement drag")
        check(
            abs(float(state["pending_translate_mm"])) <= 1e-9,
            f"B2: the live flush commits the offset MID-drag and zeroes the tail "
            f"({state['pending_translate_mm']}) -- which is what makes the release skip its refresh",
        )
        check(
            bool(getattr(editor, "_fold_carry_pending_rebuild", False)),
            "B3: that mid-drag commit carried the leg and raised the rebuild marker",
        )
        # Hold the button: every queued refresh fires while the drag state is set, i.e. rays-only.
        held = time.time()
        while time.time() - held < HOLD_S:
            insp.update_idletasks()
            insp.update()
            editor.update()
            time.sleep(0.1)
        mid = _snapshot(insp)
        check(
            abs(_moved(before, mid, "row7") or 0.0) < TOL,
            "B4: mid-drag the carried bodies are deliberately NOT redrawn (bugs/0024 keeps the "
            "drag interactive) -- so the release is the only chance to catch up",
        )

        # Release: mouse_bindings clears the drag state, dispatches the finish, then flushes.
        insp._placement_drag_state = None
        insp._finish_placement_drag(state)
        insp._flush_fold_carry_rebuild_after_drag()
        _settle(editor, insp)
        after = _snapshot(insp)

        carried = [f"row{i}" for i in range(1, 9)] + ["STEP:lens", "STEP:camera"]
        stragglers = {
            k: round(_moved(before, after, k), 3)
            for k in carried
            if _moved(before, after, k) is None or abs(_moved(before, after, k) - DELTA) > TOL
        }
        check(
            not stragglers,
            f"B5: after the release every carried body has MOVED {DELTA:+.3f} in the drawing "
            f"({stragglers or 'all followed'}) -- the flag's defect",
        )
        split = _moved(before, after, "axis:axis:global:split")
        check(
            split is not None and abs(split - DELTA) < TOL,
            f"B6: the emitted split axis followed its folder ({split}); the flag had it pinned at "
            f"z 53.80 through two drags",
        )
        obj = _moved(before, after, "row0")
        check(
            obj is not None and abs(obj) < TOL,
            f"B7: the object plane holds ({obj}) -- sliding the folder along its incoming axis is "
            f"a section-1 change (bugs/0484)",
        )
        led = _moved(before, after, "STEP:led")
        check(
            led is not None and abs(led) < TOL,
            f"B8: the LED housing stays put ({led}); dragging the BS repositions the child inside "
            f"its parent (bugs/0437)",
        )
        check(
            not bool(getattr(editor, "_fold_carry_pending_rebuild", False)),
            "B9: the marker is consumed, so the next refresh is not forced to redo this work",
        )
    except Exception as exc:
        notes.append(f"SKIP: the live drag could not be driven ({type(exc).__name__}: {exc})")
    finally:
        try:
            editor.destroy()
        except Exception:
            pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
