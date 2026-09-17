#!/usr/bin/env python3
"""bugs/0438 — the armed snap selection highlight must PERSIST, not flash.

flag_20260726_110540_269 ("rubberband selection + optical snap clicked: the selected
optical element highlight with flashes only", armed mode, picked [3..9] full): the
0436 fix kept the MODEL intact, but `_arm_snap_to_axis` applied the row + STEP body
styling and THEN called `_hide_regular_rays_for_center_axis_pick()`, whose
unconditional `refresh_from_editor()` rebuilds every actor. The scene refresh never
re-applies selection styling, and a later `_set_row_highlights(same set)` would
early-return because the SelectionModel already matches — so the pink/red styling
existed for exactly one paint (the flash) and the armed phase showed no highlight.
The same wipe re-occurs whenever a rebuild lands DURING the armed phase (e.g. the
bugs/0223 async trace applying late), so the durable fix re-applies the surviving
SelectionModel after EVERY scene rebuild (refresh_scene funnel — the same spot that
re-applies sensor isolation and the pending session camera), with a `force` flag to
bypass apply_row_selection's early-return on matching state.

Checks:
  1. PRE-CONDITION documented: arming runs a scene rebuild (rays hidden refresh).
  2. After arming + full event drain, every armed row that has actors shows >= 1
     actor with the pink selected fill, and the lens/camera STEP bodies carry the
     step-selected styling (the camera body is the Image row's only visual).
  3. A mid-armed-phase refresh_from_editor() does not wipe the styling either.
  4. Cancel (Esc path) restores: no styled actors remain.

Run:  DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0438_armed_highlight.py
(Needs an X display; start `Xvfb :N -screen 0 1600x1000x24` when headless.)
"""
from __future__ import annotations

import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCENE = REPO / "attachment" / "machine_vision_AZ85_RA_Mirror.py"

PINK = (1.0, 0.45, 0.65)


def _styled_rows(insp, rows) -> dict[int, int]:
    """row -> count of its actors currently carrying the pink selected fill."""
    styled: dict[int, int] = {}
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


def _styled_step_labels(insp) -> set[str]:
    labels: set[str] = set()
    for label, keys in dict(getattr(insp, "_step_actor_map", {}) or {}).items():
        for key in list(keys or []):
            actor = insp._actor_by_key.get(key)
            if actor is None:
                continue
            base = getattr(actor, "_kraken_step_select_style", None)
            if not isinstance(base, dict):
                continue
            try:
                color = tuple(round(float(c), 3) for c in actor.GetProperty().GetColor())
                base_color = tuple(round(float(c), 3) for c in base.get("color", ()))
            except Exception:
                continue
            if color and color != base_color:
                labels.add(str(label))
                break
    return labels


def _drain(widget, cycles: int = 4, sleep_s: float = 0.15) -> None:
    for _ in range(cycles):
        widget.update_idletasks()
        widget.update()
        time.sleep(sleep_s)


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(("ok  " if ok else "XX  ") + name + ("  " + detail if detail else ""))
        if not ok:
            failures.append(name)

    if not SCENE.exists():
        print("SKIP: scene missing:", SCENE)
        return 0

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        app.open_3d_view()
        app.update_idletasks()
        app.update()
        insp = app._three_d_inspector
        insp.geometry("1280x860+80+60")
        insp.deiconify()
        insp.lift()
        _drain(insp, cycles=2)

        pts = insp._rubber_band_display_points()
        good = sorted(i for i, p in pts.items() if p is not None)
        check("candidates available", len(good) >= 4, str(good))

        # --- arm the snap on the full candidate set (the user's chained flow tail) ---
        insp._set_row_highlights(good)
        insp._sync_table_to_selection(good)
        insp._apply_selection_step_highlights(good, render=False)
        insp.start_snap_selected_to_axis()
        _drain(insp)

        check("snap armed", bool(getattr(insp, "_snap_rows_to_axis_pick_mode", False)))
        armed = sorted(int(i) for i in (getattr(insp, "_snap_rows_selection", []) or []))
        check("armed selection intact", armed == good or set(good) <= set(armed), str(armed))

        rows_with_actors = [r for r in armed if insp._row_actor_map.get(r)]
        styled = _styled_rows(insp, rows_with_actors)
        missing = [r for r, n in styled.items() if n == 0]
        check(
            "armed row highlight PERSISTS after event drain (the 0438 flash)",
            not missing,
            f"styled={styled}",
        )
        step_labels = _styled_step_labels(insp)
        check(
            "armed lens/camera STEP body cue persists",
            {"lens", "camera"} <= step_labels,
            str(sorted(step_labels)),
        )

        # --- a rebuild landing DURING the armed phase must not wipe either ---
        insp.refresh_from_editor()
        _drain(insp)
        styled = _styled_rows(insp, rows_with_actors)
        missing = [r for r, n in styled.items() if n == 0]
        check("mid-armed refresh keeps the row highlight", not missing, f"styled={styled}")
        step_labels = _styled_step_labels(insp)
        check(
            "mid-armed refresh keeps the STEP cue",
            {"lens", "camera"} <= step_labels,
            str(sorted(step_labels)),
        )

        # --- cancel restores a clean scene ---
        insp.cancel_active_3d_operation()
        _drain(insp, cycles=2)
        styled = _styled_rows(insp, rows_with_actors)
        leftover = {r: n for r, n in styled.items() if n}
        check("cancel clears the armed highlight", not leftover, str(leftover))
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    print()
    if failures:
        print(f"RESULT: FAIL ({len(failures)}): " + "; ".join(failures))
        return 1
    print("RESULT: PASS — armed snap highlight persists through rebuilds until cancel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
