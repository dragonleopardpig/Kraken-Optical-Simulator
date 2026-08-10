#!/usr/bin/env python3
"""Display-free guard for bugs/0248: the main 2D 'YZ full 3D' matplotlib layout must
refresh after a Quick-Estimation solve / FOV / constraint apply done inside the Open 3D
inspector, on Done-2D OR Close.

Why it exists (user report):
  "after the 55x55mm FOV [...] the 2D did not update after Done 2D or Close."

Root cause: Done-2D (``finish_stl_placement``) and Close (``_on_close``) only redraw the
main 2D when ``_stl_placement_dirty`` is set -- a perf gate first built for the STL/CAD
placement flow. Every solve/FOV/constraint apply (``_quick_estimation_snap_to_fov``,
``_open3d_run_thickness_solve``, ``_apply_quick_estimation_fov_solve``,
``_apply_design_constraints``, ``_apply_placement_constraints``) rewrites the prescription
(``editor.rows[...].thickness``) and retraces the 3D inspector via
``refresh_from_editor(force_retrace=True)``, but NONE marked the 2D dirty -- so the 2D went
stale. Fix: each success path now calls ``_mark_2d_layout_stale()`` (sets the shared gate).

What it checks (no display required) -- the REAL ``Kraken3DInspector`` methods bound to a
light fake ``self`` (fake editor + fake Quick-Estimation / solve services):
  A. Each of the five producers, on a SUCCESSFUL apply, sets ``_stl_placement_dirty``.
  B. A FAILED apply (service returns ok=False) does NOT set the flag (the 2D refresh stays
     gated on a real prescription change, not merely on the button press).
  C. ``_mark_2d_layout_stale`` sets the shared gate.
  D. Done-2D (``finish_stl_placement``) with the flag set redraws the main 2D
     (``editor.refresh_plot``) and clears the flag.
  E. Done-2D with the flag clear does NOT redraw (the perf gate still holds for a
     look-only session).
  F. Close (``_on_close``) with the flag set schedules a post-close 2D redraw; with it
     clear it schedules nothing.
  G. Source contract -- all five producers call ``_mark_2d_layout_stale()`` (guards a
     future producer from silently forgetting it).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_2d_refresh_after_solve

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types


class _Var:
    def __init__(self) -> None:
        self.value = None

    def set(self, v) -> None:
        self.value = v

    def get(self):
        return self.value


class _Editor:
    """The fake main-window editor: no-op history/sync hooks plus spies for the two
    things the fix is about -- the main 2D redraw (refresh_plot) and the deferred
    post-close redraw (after)."""

    def __init__(self) -> None:
        self.refresh_plot_calls: list[dict] = []
        self.after_calls: list[tuple] = []
        self.status_var = _Var()
        self._three_d_inspector = "sentinel"
        self._cad_axis_pick_any = True
        self._cad_axis_pick_label = "x"
        self._cad_led_object_edge_pick = True

    def _begin_history_capture(self) -> None:
        pass

    def _commit_history_capture(self) -> None:
        pass

    def _sync_table(self) -> None:
        pass

    def _sync_object_controls(self) -> None:
        pass

    def _invalidate_preview_scene_trace(self) -> None:
        pass

    def _sync_trace_state_badge(self) -> None:
        pass

    def append_debug(self, *_a) -> None:
        pass

    def refresh_plot(self, **kwargs) -> None:
        self.refresh_plot_calls.append(dict(kwargs))

    def after(self, delay, callback):
        self.after_calls.append((delay, callback))
        return "after-id"


class _QE:
    """Fake Quick-Estimation service: every apply returns ``ok`` and mutates nothing (the
    real one writes editor.rows[...].thickness; here we only need the ok/msg contract)."""

    def __init__(self, ok: bool) -> None:
        self._ok = ok
        self.readout_updates = 0

    def is_enabled(self) -> bool:
        return True

    def target_object_semi(self):
        return 5.0

    def snap_to_fov(self, *_a):
        return (self._ok, "snap msg")

    def fov_solve(self, *_a):
        return (self._ok, "fov msg")

    def apply_design(self, _pins):
        return (self._ok, "design msg")

    def apply_placement(self, _pins):
        return (self._ok, "placement msg")

    def update_readout(self) -> None:
        self.readout_updates += 1


class _Solve:
    def __init__(self, ok: bool) -> None:
        self._ok = ok

    def solve(self, _objective):
        return (self._ok, "solve msg")


def _make_self(ok: bool = True):
    """A light ``self`` carrying just what the producer + consumer methods touch, with the
    two methods under test (``_mark_2d_layout_stale``) bound REAL."""
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    s = types.SimpleNamespace()
    s.editor = _Editor()
    qe = _QE(ok)
    s._qe = qe
    s._quick_estimation_service = lambda: qe
    s._open3d_solve_service = lambda: _Solve(ok)
    s._record_dialog_command = lambda *a, **k: None
    s.refresh_from_editor = lambda **kw: None
    s.status_var = _Var()
    s.quick_estimation_var = _Var()
    s._stl_placement_dirty = False
    s._active_refresh_sampling_mode = lambda: "balanced"
    s._clear_galvo_scan_animation = lambda **k: None
    for name in (
        "_cancel_live_refresh",
        "_cancel_step_carry_hold_timer",
        "_cancel_row_carry_hold_timer",
        "_close_step_rotation_handler",
        "_close_stl_placement_handler",
        "_destroy_vtk_render_window",
        "destroy",
    ):
        setattr(s, name, lambda *a, **k: None)
    # bugs/0600: the fov-solve producer now routes its message through the compact
    # status headline; bind the REAL staticmethod so the stub survives the call
    # (its output is not under test here -- phase 456 owns the readout contract).
    s._compact_solve_status = Kraken3DInspector._compact_solve_status
    # The real methods under test:
    s._mark_2d_layout_stale = types.MethodType(Kraken3DInspector._mark_2d_layout_stale, s)
    s.finish_stl_placement = types.MethodType(Kraken3DInspector.finish_stl_placement, s)
    s._on_close = types.MethodType(Kraken3DInspector._on_close, s)
    return s


def _producers():
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as I

    return [
        ("snap_to_fov", I._quick_estimation_snap_to_fov, lambda s, f: f(s)),
        ("thickness_solve", I._open3d_run_thickness_solve, lambda s, f: f(s, "best_focus")),
        (
            "fov_solve",
            I._apply_quick_estimation_fov_solve,
            lambda s, f: f(s, "image", "width", 55.0, 55.0, None, None, None),
        ),
        ("design_constraints", I._apply_design_constraints, lambda s, f: f(s, {})),
        ("placement_constraints", I._apply_placement_constraints, lambda s, f: f(s, {})),
    ]


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # --- A: each producer marks the 2D stale on a successful apply ---------------
    for name, fn, call in _producers():
        s = _make_self(ok=True)
        call(s, fn)
        if not getattr(s, "_stl_placement_dirty", False):
            failures.append(
                f"A FAIL: {name} did not set _stl_placement_dirty on success -- the main 2D "
                "would stay stale after Done-2D/Close (bugs/0248)"
            )

    # --- B: a FAILED apply must NOT mark the 2D stale ----------------------------
    for name, fn, call in _producers():
        s = _make_self(ok=False)
        call(s, fn)
        if getattr(s, "_stl_placement_dirty", False):
            failures.append(
                f"B FAIL: {name} set _stl_placement_dirty even though the solve failed -- the "
                "refresh must gate on a real prescription change"
            )

    # --- C: _mark_2d_layout_stale sets the shared gate ---------------------------
    s = _make_self()
    s._stl_placement_dirty = False
    s._mark_2d_layout_stale()
    if s._stl_placement_dirty is not True:
        failures.append("C FAIL: _mark_2d_layout_stale did not set _stl_placement_dirty = True")

    # --- D: Done-2D with the flag set redraws the 2D and clears the flag ---------
    s = _make_self()
    s._stl_placement_dirty = True
    s.finish_stl_placement()
    if not s.editor.refresh_plot_calls:
        failures.append(
            "D FAIL: finish_stl_placement (Done-2D) did not call editor.refresh_plot when the "
            "layout was marked stale -- the 2D would not update"
        )
    if getattr(s, "_stl_placement_dirty", True) is not False:
        failures.append("D FAIL: finish_stl_placement did not clear _stl_placement_dirty after redraw")

    # --- E: Done-2D with the flag clear does NOT redraw (perf gate holds) --------
    s = _make_self()
    s._stl_placement_dirty = False
    s.finish_stl_placement()
    if s.editor.refresh_plot_calls:
        failures.append(
            "E FAIL: finish_stl_placement redrew the 2D on a clean (unchanged) session -- the "
            "perf gate must still suppress a look-only Done-2D"
        )

    # --- F: Close schedules a post-close 2D redraw iff the flag is set -----------
    s = _make_self()
    s._stl_placement_dirty = True
    s._on_close()
    if not s.editor.after_calls:
        failures.append(
            "F FAIL: _on_close (Close) did not schedule a 2D redraw when the layout was stale"
        )
    else:
        # the scheduled callback must actually redraw the 2D
        _delay, cb = s.editor.after_calls[-1]
        cb()
        if not s.editor.refresh_plot_calls:
            failures.append("F FAIL: the _on_close deferred callback did not call editor.refresh_plot")
    s = _make_self()
    s._stl_placement_dirty = False
    s._on_close()
    if s.editor.after_calls:
        failures.append(
            "F FAIL: _on_close scheduled a 2D redraw on a clean session -- Close must not refresh "
            "when nothing changed"
        )

    # --- G: source contract -- all five producers call _mark_2d_layout_stale() ---
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as I

    for name, fn, _call in _producers():
        src = inspect.getsource(fn)
        if "_mark_2d_layout_stale()" not in src:
            failures.append(
                f"G FAIL: {name} source does not call _mark_2d_layout_stale() -- a future edit "
                "dropped the 2D-stale mark"
            )
    if "_stl_placement_dirty = True" not in inspect.getsource(I._mark_2d_layout_stale):
        failures.append("G FAIL: _mark_2d_layout_stale no longer sets _stl_placement_dirty = True")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0248 2D refresh after solve/FOV/constraint")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] bugs/0248: a solve/FOV/constraint apply marks the main 2D stale, and Done-2D / "
        "Close redraw it (while a look-only session still skips the redraw)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
