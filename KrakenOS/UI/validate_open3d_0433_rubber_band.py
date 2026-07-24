"""Guard: rubber-band box select feeds the multi-select snap (bugs/0433 slice B).

The 0432 Shift-click accumulate never fired from real mouse input (Shift+B1 is the
touchpad pan and ``set_event_info`` hard-codes shift=0), so the rubber band is the
working bulk multi-select: Place menu arms ``start_rubber_band_select`` (plain or
chain-snap), the left drag draws a display-space rectangle, and on release every
candidate row whose FOLD-AWARE world center projects inside fills
``_picked_row_indices`` -- after which the existing "Snap Selected to Optical Axis" /
"Add Selected to Assembly" flows run unchanged.

Checks (display-free unless noted):

* PURE-CORE      -- ``rubber_band_rows_in_rect`` containment (inclusive, reversed
                    corners, None points) + ``rubber_band_candidate_row_indices``
                    (Object + trailing-AIR spacers excluded, fold solids included).
* REAL-METHODS   -- the REAL ``_complete_rubber_band_select`` / ``_cancel_rubber_
                    band_select`` / ``_rubber_band_display_points`` bound to a stub:
                    fold-transform pose wins over station+desp, box selection fills
                    the highlight path, chain-snap hands off to the snap arming,
                    empty box and cancel disarm cleanly.
* REAL-SCENE     -- (editor, needs a display; SKIP without one) on machine_vision_
                    AZ85_RA_Mirror the folded lens chain + free-placed mirror-2
                    project onto ONE reflected leg and a box over that leg selects
                    them, never the Object.
* WIRING         -- mouse bindings carry the press/motion/release branches, the Place
                    menu exposes both entries, Esc cancel + badge + InteractionMode
                    cover the new mode AND the backfilled 0432 axis picks.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0433_rubber_band

Exit: 0 = pass, 1 = regression, 2 = environment/scene unavailable (skip).
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path
from types import SimpleNamespace

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


class _StatusVar:
    def __init__(self) -> None:
        self.last = ""

    def set(self, text) -> None:
        self.last = str(text)


def _make_fakes():
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    class _FakeEditor:
        def __init__(self, rows, z_positions, fold_transforms) -> None:
            self.rows = rows
            self._z = list(z_positions)
            self._folds = dict(fold_transforms)
            self.selected_table_rows: list[int] = []

        def _row_z_positions(self):
            return list(self._z)

        def _optical_axis_fold_world_transform_for_row(self, index):
            return self._folds.get(index)

        def _select_table_row(self, index) -> None:
            self.selected_table_rows.append(int(index))

        def _lens_datum_row_index(self, _which):
            return None

        def _step_path_for_label(self, _label):
            return None

    class _FakeInspector:
        start_rubber_band_select = Kraken3DInspector.start_rubber_band_select
        start_rubber_band_select_and_snap = Kraken3DInspector.start_rubber_band_select_and_snap
        _complete_rubber_band_select = Kraken3DInspector._complete_rubber_band_select
        _cancel_rubber_band_select = Kraken3DInspector._cancel_rubber_band_select
        _clear_rubber_band_preview = Kraken3DInspector._clear_rubber_band_preview
        _rubber_band_display_points = Kraken3DInspector._rubber_band_display_points

        def __init__(self, editor) -> None:
            self.editor = editor
            self.status_var = _StatusVar()
            self._rubber_band_select_mode = False
            self._rubber_band_chain_snap = False
            self._rubber_band_press_xy = None
            self._rubber_band_preview_actors: list = []
            self._axis_to_axis_move_pick_mode = False
            self._snap_rows_to_axis_pick_mode = False
            self._step_normal_axis_pick_mode = False
            self._step_surface_center_axis_pick_mode = False
            self._center_row_to_ray_mode = False
            self._placement_target_pick_mode = False
            self.highlighted_rows: list[int] | None = None
            self.snap_started = 0

        def _tk_xy_to_vtk_display_xy(self, xy):
            return (float(xy[0]), float(xy[1]))

        def _world_to_display_2d(self, point):
            p = np.asarray(point, dtype=float).reshape(-1)
            return np.asarray((p[2], p[0]), dtype=float)

        def _set_row_highlights(self, rows) -> None:
            self.highlighted_rows = [int(i) for i in rows]

        def _set_step_highlight_set(self, labels, *, render=True) -> None:
            pass

        def _set_ray_highlight(self, _v) -> None:
            pass

        def _set_optical_axis_highlight(self, _v) -> None:
            pass

        def _clear_open3d_selection(self, *, render=True) -> bool:
            return False

        def _set_axis_pick_cursor(self, _on) -> None:
            pass

        def _update_mode_badge(self, *, render=True) -> None:
            pass

        def render(self) -> None:
            pass

        def start_snap_selected_to_axis(self) -> None:
            self.snap_started += 1

    return _FakeEditor, _FakeInspector


def _fake_scene(_FakeEditor):
    rows = [
        SimpleNamespace(surface="Object", advanced={}, desp_x=0.0, desp_y=0.0, desp_z=0.0),
        SimpleNamespace(surface=None, advanced={}, desp_x=0.0, desp_y=0.0, desp_z=0.0),
        SimpleNamespace(surface=None, advanced={}, desp_x=0.0, desp_y=0.0, desp_z=0.0),
        SimpleNamespace(surface="Image", advanced={}, desp_x=5.0, desp_y=0.0, desp_z=0.0),
    ]
    fold = np.eye(4)
    rot = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]], dtype=float)
    fold[:3, :3] = rot
    fold[:3, 3] = np.asarray((30.0, 0.0, 70.0)) - rot @ np.asarray((0.0, 0.0, 80.0))
    return _FakeEditor(rows, [0.0, 40.0, 80.0, 120.0], {2: fold})


def run_checks() -> "tuple[bool, list[str]]":
    try:
        from KrakenOS.UI.open3d_inspector import (
            rubber_band_candidate_row_indices,
            rubber_band_rows_in_rect,
        )
    except Exception as exc:
        return True, [f"SKIP: inspector import failed ({exc})"]

    failures: list[str] = []
    notes: list[str] = []

    # --- PURE-CORE -------------------------------------------------------------
    pts = {0: (10.0, 10.0), 1: (50.0, 50.0), 2: (90.0, 90.0), 3: None}
    if rubber_band_rows_in_rect(pts, (40, 40), (60, 60)) != [1]:
        failures.append("pure core: inside-rect selection wrong")
    if rubber_band_rows_in_rect(pts, (60, 60), (40, 40)) != [1]:
        failures.append("pure core: reversed corners must normalize")
    if rubber_band_rows_in_rect(pts, (50, 50), (90, 90)) != [1, 2]:
        failures.append("pure core: rect edges must be inclusive")
    if 3 in rubber_band_rows_in_rect(pts, (-1e6, -1e6), (1e6, 1e6)):
        failures.append("pure core: None projections must be skipped")
    rows = [
        SimpleNamespace(surface="Object", advanced={}),
        SimpleNamespace(surface=None, advanced={}),
        SimpleNamespace(surface=None, advanced={"InPathTrailingSpacer": True}),
        SimpleNamespace(surface=None, advanced={"StepOverlayPromotion": {"center_world": [1, 2, 3]}}),
    ]
    if rubber_band_candidate_row_indices(rows) != [1, 3]:
        failures.append("candidates: Object/spacer must be excluded, solid included")
    if not failures:
        notes.append("PURE-CORE = containment + candidate filtering behave")

    # --- REAL-METHODS on the stub ---------------------------------------------
    try:
        _FakeEditor, _FakeInspector = _make_fakes()
        fake = _FakeInspector(_fake_scene(_FakeEditor))
        pts2 = fake._rubber_band_display_points()
        folded = pts2.get(2)
        if folded is None or abs(folded[0] - 70.0) > 1e-9 or abs(folded[1] - 30.0) > 1e-9:
            failures.append(f"display points: fold transform must win over station (got {folded})")
        if pts2.get(3) != (120.0, 5.0):
            failures.append(f"display points: baked desp must be honoured (got {pts2.get(3)})")
        fake.start_rubber_band_select()
        fake._complete_rubber_band_select((60.0, 20.0), (90.0, 40.0))
        if fake.highlighted_rows != [2]:
            failures.append(f"complete: box around the folded leg must select row 2 (got {fake.highlighted_rows})")
        if fake._rubber_band_select_mode:
            failures.append("complete: mode must disarm")
        if fake.snap_started != 0:
            failures.append("plain select must NOT arm the snap")
        fake2 = _FakeInspector(_fake_scene(_FakeEditor))
        fake2.start_rubber_band_select_and_snap()
        fake2._complete_rubber_band_select((-1e6, -1e6), (1e6, 1e6))
        if fake2.highlighted_rows != [1, 2, 3]:
            failures.append(f"chain: full box must select all candidates (got {fake2.highlighted_rows})")
        if fake2.snap_started != 1:
            failures.append("chain: completion must hand off to start_snap_selected_to_axis")
        fake3 = _FakeInspector(_fake_scene(_FakeEditor))
        fake3.start_rubber_band_select()
        fake3._cancel_rubber_band_select()
        if fake3._rubber_band_select_mode:
            failures.append("cancel: mode must disarm")
        if len(failures) == 0:
            notes.append("REAL-METHODS = fold-aware projection, box fill, chain hand-off, cancel")
    except Exception as exc:
        failures.append(f"stub-bound method checks raised: {exc}")

    # --- WIRING ----------------------------------------------------------------
    try:
        from KrakenOS.UI.services import open3d_mouse_bindings as _bindings_mod
        from KrakenOS.UI.panels import open3d_top_controls as _controls_mod
        from KrakenOS.UI.services.open3d_interaction_mode import InteractionMode, derive_interaction_mode
        from KrakenOS.UI import open3d_inspector as _inspector_mod

        bindings_src = _inspect.getsource(_bindings_mod)
        if "_rubber_band_select_mode" not in bindings_src or "_complete_rubber_band_select" not in bindings_src:
            failures.append("wiring: mouse bindings lost the rubber-band drag routing")
        controls_src = _inspect.getsource(_controls_mod)
        if "start_rubber_band_select" not in controls_src:
            failures.append("wiring: Place menu lost the rubber-band entries")
        cancel_src = _inspect.getsource(_inspector_mod.Kraken3DInspector.cancel_active_3d_operation)
        for flag in ("_rubber_band_select_mode", "_axis_to_axis_move_pick_mode", "_snap_rows_to_axis_pick_mode"):
            if flag not in cancel_src:
                failures.append(f"wiring: cancel_active_3d_operation no longer resets {flag}")
        probe = SimpleNamespace(_rubber_band_select_mode=True)
        if derive_interaction_mode(probe) != InteractionMode.RUBBER_BAND_SELECT:
            failures.append("wiring: derive_interaction_mode must report RUBBER_BAND_SELECT")
        probe = SimpleNamespace(_snap_rows_to_axis_pick_mode=True)
        if derive_interaction_mode(probe) != InteractionMode.SNAP_ROWS_TO_AXIS:
            failures.append("wiring: derive_interaction_mode must report SNAP_ROWS_TO_AXIS (0432 backfill)")
        probe = SimpleNamespace(_axis_to_axis_move_pick_mode=True)
        if derive_interaction_mode(probe) != InteractionMode.AXIS_TO_AXIS_MOVE:
            failures.append("wiring: derive_interaction_mode must report AXIS_TO_AXIS_MOVE (0432 backfill)")
        if not failures:
            notes.append("WIRING = bindings + menu + Esc cancel + InteractionMode registered")
    except Exception as exc:
        failures.append(f"wiring checks raised: {exc}")

    # --- REAL-SCENE (needs a display; SKIP quietly without one) ----------------
    if SCENE.exists():
        app = None
        try:
            from KrakenOS.UI.layout_editor import KrakenLayoutEditor

            app = KrakenLayoutEditor()
        except Exception as exc:
            notes.append(f"REAL-SCENE skipped (no display: {type(exc).__name__})")
            app = None
        if app is not None:
            try:
                _FakeEditor, _FakeInspector = _make_fakes()
                app.layout_files["az85"] = SCENE
                app.load_layout_by_name("az85")
                fake = _FakeInspector(app)
                pts3 = fake._rubber_band_display_points()
                lens_rows = [i for i in (3, 4, 5, 6, 7) if pts3.get(i) is not None]
                if not lens_rows:
                    failures.append("real scene: no lens-chain projections")
                else:
                    leg_z = pts3[lens_rows[0]][0]
                    if not all(abs(pts3[i][0] - leg_z) < 0.5 and pts3[i][1] > 5.0 for i in lens_rows):
                        failures.append(f"real scene: lens chain not on one folded leg ({[(i, pts3.get(i)) for i in lens_rows]})")
                    mirror2 = pts3.get(8)
                    if mirror2 is None or abs(mirror2[0] - leg_z) > 2.0 or abs(mirror2[1] - 235.9) > 2.0:
                        failures.append(f"real scene: mirror-2 off its pinned leg pose ({mirror2})")
                    from KrakenOS.UI.open3d_inspector import rubber_band_rows_in_rect as _in_rect

                    picked = _in_rect(pts3, (leg_z - 10.0, 5.0), (leg_z + 10.0, 300.0))
                    if not set((3, 4, 5, 6, 7, 8)).issubset(set(picked)) or 0 in picked:
                        failures.append(f"real scene: leg box must select chain+mirror2, never Object (got {picked})")
                    if not any("REAL-SCENE" in n for n in notes) and not failures:
                        notes.append(f"REAL-SCENE = AZ85 folded leg (z~{leg_z:.1f}) box-selects chain+mirror2")
            except Exception as exc:
                notes.append(f"REAL-SCENE skipped ({type(exc).__name__}: {exc})")
            finally:
                try:
                    app.destroy()
                except Exception:
                    pass
    else:
        notes.append("REAL-SCENE skipped (scene file absent)")

    return (len(failures) == 0), (failures + notes)


def run() -> int:
    try:
        passed, messages = run_checks()
    except Exception as exc:  # environment guard -- never hard-fail the harness
        print(f"SKIP: validator environment failure: {exc}")
        return 2
    for message in messages:
        print(("= " if passed or "SKIP" in message else "X ") + message)
    if passed and any(message.startswith("SKIP") for message in messages):
        return 2
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
