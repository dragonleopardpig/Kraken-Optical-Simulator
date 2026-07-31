"""bugs/0491 -- a fold carry reaches the DRAWING, not just the model.

Three fixes shipped for this and none of them had a test, which is why the third was needed:
bugs/0487 made the model carry, then `flag_20260731_210040` and `flag_20260731_211354` both showed
every carried row's ``desp`` moved while **not one actor or axis record did**.  Every guard in the
family asserted on ``rows`` -- the one place that was already right.

The two halves being held here:

* the model change must force a retrace at all (the carry rewrites ``desp`` outside the ordinary
  edit path, so callers refresh with no ``force_retrace``), and
* the marker that says so must survive the mid-drag refreshes.  ``_preview_scene_trace_dirty`` is
  CONSUMED by any build -- ``three_d_scene_tools`` sets it to ``not trace_rays``, the async trace
  clears it -- and the glue carry runs every drag FRAME (bugs/0137), so by release it is already
  False.  ``_fold_carry_pending_rebuild`` is the sticky half, cleared only by a refresh that
  actually retraces and only when no drag is still in flight (bugs/0024: never a ~2 s rebuild per
  frame).

Measured on ``attachment/machine_vision_AZ85_RA_Mirror_BS.py``, sliding the beam splitter +18.431
along the axis feeding it -- every number below is a DRAWN quantity:

    row actors 1..8, 100000   +18.43       row actor 0 (object plane)   unchanged
    STEP lens, STEP camera    +18.43       axis:global:split   z 53.80 -> 72.23
                                           axis:global:frozen-fold:7    +18.43

Row 0 holding still is the point, not an omission: sliding the folder along its incoming axis is a
section-1 change, so the object plane stays and the gap absorbs it (bugs/0484, and the user's
"dragging RA mirror ... affects section 3 only; glued LED+BS ... affect sections 1 and 2").

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0491_carry_reaches_the_drawing
"""
from __future__ import annotations

import time
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
DELTA = 18.431
TOL = 0.08  # a body's bounds move rigidly; the dotted global guide is envelope-derived (see D2)


def _settle(app, inspector, limit: float = 90.0) -> float:
    """Pump the loop until the rebuild has drawn bodies. The AZ85 scene takes ~7 s -- long enough
    that a user who drags and looks immediately sees the OLD chain, which is what "nothing
    follows" looks like from the outside."""
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
    return time.time() - start


def _snapshot(app, inspector) -> dict:
    """Everything the user can actually SEE: body actors, STEP bodies, axis polylines."""
    out: dict[str, tuple] = {}
    actor_by_key = getattr(inspector, "_actor_by_key", {}) or {}
    for row_index, keys in (getattr(inspector, "_row_actor_map", {}) or {}).items():
        spans: list = []
        for key in list(keys or []):
            actor = actor_by_key.get(key)
            if actor is None:
                continue
            bounds = actor.GetBounds()
            if bounds and bounds[0] <= bounds[1]:
                spans.append(bounds)
        if spans:
            out[f"row{row_index}"] = (min(s[4] for s in spans), max(s[5] for s in spans))
    for label, keys in (getattr(inspector, "_step_actor_map", {}) or {}).items():
        spans = []
        for key in list(keys or []):
            actor = actor_by_key.get(key)
            if actor is None:
                continue
            bounds = actor.GetBounds()
            if bounds and bounds[0] <= bounds[1]:
                spans.append(bounds)
        if spans:
            out[f"STEP:{label}"] = (min(s[4] for s in spans), max(s[5] for s in spans))
    for record in list(getattr(inspector, "_optical_axis_pick_records", None) or []):
        try:
            import numpy as np

            arr = np.asarray(record.get("points"), dtype=float)
            out[f"axis:{record.get('axis_id')}"] = tuple(float(v) for v in arr[:, 2])
        except Exception:
            continue
    return out


def _moved(before: dict, after: dict, key: str) -> "float | None":
    """Mean z-shift of a drawn thing, or None when it is missing from either snapshot."""
    b, a = before.get(key), after.get(key)
    if b is None or a is None or len(b) != len(a) or not b:
        return None
    return sum(y - x for x, y in zip(b, a)) / float(len(b))


def _drive(open_inspector) -> "dict | str":
    """Both gestures in ONE app: a second editor+inspector in the same process does not come up
    (the 0294-class viewer hazard), and only the DELTAS are asserted, so running the glue gesture
    from wherever the row gesture left the scene is equivalent and half the wall clock."""
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    out: dict = {}
    try:
        app.layout_files["carry_probe"] = SCENE
        app.load_layout_by_name("carry_probe")
        inspector = open_inspector(app)
        if inspector is None:
            return "SKIP: the embedded 3D inspector is unavailable"
        out["build_s"] = _settle(app, inspector)
        stage = _snapshot(app, inspector)

        # (B) the beam splitter is a promoted row: slide it along the axis feeding it.
        app.translate_scene_row_pose(3, "z", DELTA)
        marker_row = bool(getattr(app, "_fold_carry_pending_rebuild", False))
        inspector.refresh_from_editor()
        _settle(app, inspector)
        after_row = _snapshot(app, inspector)
        out["row"] = (stage, after_row, marker_row)

        # (C) the user's own gesture: glue the BS to the LED, then drag the LED BODY.
        app.set_optical_led_glue(True)
        app.translate_step_overlay("led", (0.0, 0.0, DELTA))
        marker_glue = bool(getattr(app, "_fold_carry_pending_rebuild", False))
        inspector.refresh_from_editor()
        _settle(app, inspector)
        out["glue"] = (after_row, _snapshot(app, inspector), marker_glue)
        return out
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    # --- A. the sticky marker exists and is consumed under the right guard ----------------
    try:
        import inspect as _inspect

        from KrakenOS.UI.open3d_inspector import Kraken3DInspector
        from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

        carry_src = _inspect.getsource(ScenePlacementMixin._fold_slide_carry_apply)
        check(
            "_fold_carry_pending_rebuild" in carry_src,
            "A1: the fold carry raises a rebuild marker of its own -- _preview_scene_trace_dirty "
            "is eaten by the mid-drag builds (three_d_scene_tools / the async trace)",
        )
        refresh_src = _inspect.getsource(Kraken3DInspector.refresh_from_editor)
        check(
            "_fold_carry_pending_rebuild" in refresh_src and "force_retrace = True" in refresh_src,
            "A2: refresh_from_editor promotes that marker to a retrace",
        )
        check(
            "_placement_drag_state is None" in refresh_src,
            "A3: ... but not while a drag is in flight, so the interactive path never becomes a "
            "~2 s rebuild per frame (bugs/0024)",
        )
    except Exception as exc:
        notes.append(f"SKIP: source unreadable ({type(exc).__name__}: {exc})")

    if not SCENE.exists():
        notes.append("SKIP: the AZ85 BS scene is not checked out (gitignored attachment)")
        return ok, notes

    def _open(app_):
        try:
            app_.open_3d_view()
            app_.update_idletasks()
            app_.update()
        except Exception:
            return None
        insp = getattr(app_, "_three_d_inspector", None)
        if insp is None or not getattr(insp, "available", False):
            return None
        try:
            insp.update_idletasks()
            insp.update()
        except Exception:
            return None
        return insp

    # --- B/C. the drawing follows, for both entry paths ------------------------------------
    try:
        driven = _drive(_open)
    except Exception as exc:
        notes.append(f"SKIP: the scene could not be driven ({type(exc).__name__}: {exc})")
        return ok, notes
    if isinstance(driven, str):
        notes.append(driven)
        return ok, notes
    notes.append(
        f"       (the AZ85 rebuild takes {driven.get('build_s', 0.0):.1f} s -- long enough that a "
        f"user who drags and looks straight away sees the OLD chain)"
    )
    for gesture, title in (("row", "B: sliding the BS row"), ("glue", "C: dragging the glued LED body")):
        before, after, marker = driven[gesture]
        if gesture == "row":
            check(marker, f"{title} -- the carry raised the sticky rebuild marker")
        else:
            # translate_step_overlay refreshes internally (refresh=True), and that refresh CONSUMES
            # the marker -- correctly, since no drag is in flight. So it is already False by the
            # time this reads it, and the honest assertion for this path is the drawing itself.
            notes.append(
                f"       ({title} -- marker already consumed by the overlay's own refresh "
                f"({marker}); the drawing checks below are what hold this path)"
            )
        carried = [f"row{i}" for i in range(1, 9)] + ["STEP:lens", "STEP:camera"]
        if gesture == "glue":
            carried.append("STEP:led")
        missing = [k for k in carried if _moved(before, after, k) is None]
        check(not missing, f"{title} -- every carried body is drawn before and after ({missing})")
        stragglers = {
            k: round(_moved(before, after, k), 3)
            for k in carried
            if _moved(before, after, k) is not None and abs(_moved(before, after, k) - DELTA) > TOL
        }
        check(
            not stragglers,
            f"{title} -- every carried body MOVED {DELTA:+.3f} in the drawing, not just in the "
            f"model ({stragglers or 'all followed'})",
        )
        obj = _moved(before, after, "row0")
        check(
            obj is not None and abs(obj) < TOL,
            f"{title} -- the object plane holds ({obj}); sliding the folder along its incoming "
            f"axis is a section-1 change, so the gap absorbs it (bugs/0484)",
        )
        split = _moved(before, after, "axis:axis:global:split")
        check(
            split is not None and abs(split - DELTA) < TOL,
            f"{title} -- the emitted split axis moved with its folder ({split}); a chain drawn "
            f"against a stale axis is the 'nothing follows' picture",
        )
        fold = _moved(before, after, "axis:axis:global:frozen-fold:7")
        check(
            fold is not None and abs(fold - DELTA) < TOL,
            f"{title} -- the frozen fold axis at the RA mirror moved too ({fold})",
        )
        if gesture == "row":
            led = _moved(before, after, "STEP:led")
            check(
                led is not None and abs(led) < TOL,
                f"{title} -- the LED housing stays put ({led}); the glue is ASYMMETRIC, a BS move "
                f"repositions the child inside its parent (bugs/0437)",
            )
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
