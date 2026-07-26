#!/usr/bin/env python3
"""bugs/0433 slice B probe: rubber-band box select.

Display-free checks of the pure containment core + the REAL inspector completion
methods bound to a stub (validate_open3d_measure_edge_pick.py's _Fake pattern), plus
an optional real-scene fold-aware projection check on machine_vision_AZ85_RA_Mirror
(needs a display; run under ``xvfb-run -a``).

Run:
    xvfb-run -a .devenv/state/venv/bin/python bugs/probe_0433_rubber_band_core.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from KrakenOS.UI.open3d_inspector import (  # noqa: E402
    Kraken3DInspector,
    rubber_band_candidate_row_indices,
    rubber_band_rows_in_rect,
)

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'ok' if ok else 'XX'}] {name}" + (f" -- {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


# ---------------------------------------------------------------- pure core
def test_pure_core() -> None:
    print("[1] pure containment core")
    pts = {0: (10.0, 10.0), 1: (50.0, 50.0), 2: (90.0, 90.0), 3: None, 4: (50.0, 200.0)}
    check("inside", rubber_band_rows_in_rect(pts, (40, 40), (60, 60)) == [1])
    check("all", rubber_band_rows_in_rect(pts, (0, 0), (100, 100)) == [0, 1, 2])
    check("reversed corners", rubber_band_rows_in_rect(pts, (60, 60), (40, 40)) == [1])
    check("edge inclusive", rubber_band_rows_in_rect(pts, (50, 50), (90, 90)) == [1, 2])
    check("none-point skipped", 3 not in rubber_band_rows_in_rect(pts, (-1e6, -1e6), (1e6, 1e6)))
    check("empty dict", rubber_band_rows_in_rect({}, (0, 0), (100, 100)) == [])
    check("degenerate rect", rubber_band_rows_in_rect(pts, (50, 50), (50, 50)) == [1])

    rows = [
        SimpleNamespace(surface="Object", advanced={}),
        SimpleNamespace(surface=None, advanced={}),
        SimpleNamespace(surface=None, advanced={"InPathTrailingSpacer": True}),
        SimpleNamespace(surface=None, advanced={"StepOverlayPromotion": {"center_world": [1, 2, 3]}}),
        SimpleNamespace(surface="Image", advanced=None),
    ]
    got = rubber_band_candidate_row_indices(rows)
    check("object excluded / spacer excluded / solid+image included", got == [1, 3, 4], f"got {got}")


# ------------------------------------------------- real methods on a stub
class _StatusVar:
    def __init__(self) -> None:
        self.last = ""

    def set(self, text) -> None:
        self.last = str(text)


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
    """Binds the REAL 0433 methods; only renderer/highlight plumbing is stubbed."""

    start_rubber_band_select = Kraken3DInspector.start_rubber_band_select
    start_rubber_band_select_and_snap = Kraken3DInspector.start_rubber_band_select_and_snap
    _complete_rubber_band_select = Kraken3DInspector._complete_rubber_band_select
    _cancel_rubber_band_select = Kraken3DInspector._cancel_rubber_band_select
    _clear_rubber_band_preview = Kraken3DInspector._clear_rubber_band_preview
    _rubber_band_display_points = Kraken3DInspector._rubber_band_display_points
    # bugs/0436: completion now expands lens-group selections, syncs the table
    # without collapsing the multi-selection, and re-lights the STEP-body cue.
    _expand_selection_rows_for_groups = Kraken3DInspector._expand_selection_rows_for_groups
    _selection_step_highlight_labels = Kraken3DInspector._selection_step_highlight_labels
    _apply_selection_step_highlights = Kraken3DInspector._apply_selection_step_highlights
    _sync_table_to_selection = Kraken3DInspector._sync_table_to_selection
    _release_table_selection_sync_suppression = (
        Kraken3DInspector._release_table_selection_sync_suppression
    )

    def after_idle(self, callback, *args):
        callback(*args)
        return None

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
        self.step_highlights: list[str] | None = None
        self.snap_started = 0
        self.render_calls = 0

    # display-space stubs: identity Tk->display, world (x,y,z) -> display (z, x)
    def _tk_xy_to_vtk_display_xy(self, xy):
        return (float(xy[0]), float(xy[1]))

    def _world_to_display_2d(self, point):
        p = np.asarray(point, dtype=float).reshape(-1)
        return np.asarray((p[2], p[0]), dtype=float)

    def _set_row_highlights(self, rows) -> None:
        self.highlighted_rows = [int(i) for i in rows]

    def _set_step_highlight_set(self, labels, *, render=True) -> None:
        self.step_highlights = list(labels)

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
        self.render_calls += 1

    def start_snap_selected_to_axis(self) -> None:
        self.snap_started += 1


def _fake_scene():
    """4 rows: Object at z=0; row1 straight at z=40; row2 FOLDED (station z=80 ->
    world (30, 0, 70) via a fold transform); row3 straight with baked desp x=5, z=120."""
    rows = [
        SimpleNamespace(surface="Object", advanced={}, desp_x=0.0, desp_y=0.0, desp_z=0.0),
        SimpleNamespace(surface=None, advanced={}, desp_x=0.0, desp_y=0.0, desp_z=0.0),
        SimpleNamespace(surface=None, advanced={}, desp_x=0.0, desp_y=0.0, desp_z=0.0),
        SimpleNamespace(surface="Image", advanced={}, desp_x=5.0, desp_y=0.0, desp_z=0.0),
    ]
    fold = np.eye(4)
    # F(v) = C + R @ (v - S) with S=(0,0,80), C=(30,0,70), R = +Z->+X quarter turn about Y
    rot = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]], dtype=float)
    fold[:3, :3] = rot
    fold[:3, 3] = np.asarray((30.0, 0.0, 70.0)) - rot @ np.asarray((0.0, 0.0, 80.0))
    return _FakeEditor(rows, [0.0, 40.0, 80.0, 120.0], {2: fold})


def test_stub_bound_methods() -> None:
    print("[2] real completion methods on the stub")
    editor = _fake_scene()
    fake = _FakeInspector(editor)

    pts = fake._rubber_band_display_points()
    check("object excluded from candidates", 0 not in pts)
    check("straight row projects at station", pts[1] == (40.0, 0.0), f"got {pts.get(1)}")
    folded = pts.get(2)
    check(
        "folded row projects at FOLD pose (70, 30), not station (80, 0)",
        folded is not None and abs(folded[0] - 70.0) < 1e-9 and abs(folded[1] - 30.0) < 1e-9,
        f"got {folded}",
    )
    check("baked-desp row includes desp", pts[3] == (120.0, 5.0), f"got {pts.get(3)}")

    # arm + complete: box around the folded leg only (display x=z in [60,90], y=x in [20,40])
    fake.start_rubber_band_select()
    check("armed", fake._rubber_band_select_mode is True)
    fake._complete_rubber_band_select((60.0, 20.0), (90.0, 40.0))
    check("folded row selected by box", fake.highlighted_rows == [2], f"got {fake.highlighted_rows}")
    check("mode disarmed after complete", fake._rubber_band_select_mode is False)
    check("table synced", editor.selected_table_rows[-1:] == [2])
    check("no chain snap by default", fake.snap_started == 0)

    # chained variant: box everything -> snap arming fires
    fake2 = _FakeInspector(_fake_scene())
    fake2.start_rubber_band_select_and_snap()
    check("chain intent stored", fake2._rubber_band_chain_snap is True)
    fake2._complete_rubber_band_select((-1e6, -1e6), (1e6, 1e6))
    check("all candidates selected", fake2.highlighted_rows == [1, 2, 3], f"got {fake2.highlighted_rows}")
    check("chain hands off to start_snap_selected_to_axis", fake2.snap_started == 1)

    # empty box -> no selection, status explains
    fake3 = _FakeInspector(_fake_scene())
    fake3.start_rubber_band_select()
    fake3._complete_rubber_band_select((-500.0, -500.0), (-400.0, -400.0))
    check("empty box selects nothing", fake3.highlighted_rows is None)
    check("empty box status", "no elements" in fake3.status_var.last, fake3.status_var.last)

    # cancel path
    fake4 = _FakeInspector(_fake_scene())
    fake4.start_rubber_band_select()
    fake4._cancel_rubber_band_select()
    check("cancel disarms", fake4._rubber_band_select_mode is False)


# ------------------------------------------------- real AZ85 scene (needs display)
def test_real_scene() -> None:
    print("[3] real AZ85 scene fold-aware projection (xvfb)")
    scene = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
    if not scene.exists():
        print("  [--] scene missing, skipped")
        return
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
    except Exception as exc:
        print(f"  [--] no display / editor unavailable, skipped ({exc})")
        return
    try:
        app.layout_files["az85"] = scene
        app.load_layout_by_name("az85")
        fake = _FakeInspector(app)
        pts = fake._rubber_band_display_points()
        check("candidates exclude object row 0", 0 not in pts)
        check("candidates exclude spacer row 2", 2 not in pts)
        # display stub maps world (x,y,z) -> (z, x). The folded +X leg keeps one world z
        # (the fold-vertex height; ~53 on this scene) for the whole lens chain, with x
        # marching outward -- derive the leg height from row 3 instead of hardcoding it.
        lens_rows = [i for i in (3, 4, 5, 6, 7) if i in pts and pts[i] is not None]
        leg_z = pts[lens_rows[0]][0] if lens_rows else float("nan")
        ok = bool(lens_rows) and all(abs(pts[i][0] - leg_z) < 0.5 and pts[i][1] > 5.0 for i in lens_rows)
        check(
            "lens chain projects on ONE folded leg, off the straight axis",
            ok,
            f"leg_z={leg_z:.2f} {[(i, pts.get(i)) for i in (3, 4, 5, 6, 7)]}",
        )
        mirror2 = pts.get(8)
        check(
            "free-placed mirror-2 on the same leg at x~235.9",
            mirror2 is not None and abs(mirror2[0] - leg_z) < 2.0 and abs(mirror2[1] - 235.9) < 2.0,
            f"got {mirror2}",
        )
        # a box spanning the folded leg must capture the lens chain + mirror-2 (+ the
        # Image row if it sits past mirror-2 on this leg's span), never the Object
        rows = rubber_band_rows_in_rect(pts, (leg_z - 10.0, 5.0), (leg_z + 10.0, 300.0))
        check(
            "box over the folded leg selects chain+mirror2, never the object",
            set((3, 4, 5, 6, 7, 8)).issubset(set(rows)) and 0 not in rows,
            f"got {rows}",
        )
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def main() -> int:
    test_pure_core()
    test_stub_bound_methods()
    test_real_scene()
    print(f"RESULT: {'PASS' if not FAILURES else 'FAIL'} ({len(FAILURES)} failure(s))")
    for name in FAILURES:
        print(f"  failed: {name}")
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    raise SystemExit(main())
