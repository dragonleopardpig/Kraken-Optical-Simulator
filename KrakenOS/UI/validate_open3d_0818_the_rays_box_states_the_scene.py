"""Guard for bugs/0818 -- the Show Rays box states what is on screen, on EVERY path.

User: "I still see Rays ON is tick but no rays is actually on. I have to untick and tick to make it
work. I randomly open .py files."

bugs/0801 made the box match the scene and unticked it in `open_3d_view`. Two paths kept the tick:

* the 3D-session sidecar restores the SAVED overlay toggles at the START of every
  `refresh_from_editor`, so a scene whose sidecar carries ``show_rays_var: true`` -- om05a's does --
  re-ticks the box the open path had just cleared;
* loading another .py into an ALREADY-OPEN inspector never runs the open path at all.

Both leave "Rays" ticked over a bodies-only scene. The rule is now enforced at the painter, so every
entry inherits it, and it only ever turns the box OFF -- ticking it is still the deliberate request
that clears the bugs/0646 gate and traces.

Checks (display-free; the real method is driven through a shim):
  A  the box is unticked exactly when the fast-load gate is set and it reads on, with a note; it is
     never ticked ON, and a scene that is already tracing is left alone.
  B  the wiring: the painter enforces it, the open path delegates to the same implementation, the
     session restore really does re-apply show_rays_var (the root cause), and bugs/0801's
     tick-clears-the-gate is intact.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0818_the_rays_box_states_the_scene

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace


class _Var:
    """A BooleanVar stand-in that records every write (a Checkbutton `command=` callback does not
    fire on a programmatic set, which is why the painter may do this at all)."""

    def __init__(self, value: bool) -> None:
        self.value = bool(value)
        self.writes: list[bool] = []

    def get(self) -> bool:
        return self.value

    def set(self, value) -> None:
        self.value = bool(value)
        self.writes.append(bool(value))


def _sync(deferred: bool, ticked: bool):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    var = _Var(ticked)
    shim = SimpleNamespace(
        editor=SimpleNamespace(_preview_trace_deferred_until_requested=deferred),
        show_rays_var=var,
    )
    bound = Kraken3DInspector._sync_show_rays_toggle_to_scene.__get__(shim, type(shim))
    return bound(), var


def _check_rule(ok) -> None:
    note, var = _sync(deferred=True, ticked=True)
    ok(
        var.get() is False and var.writes == [False] and "Show Rays is off" in note
        and "Trace Now" in note,
        f"A1: gate set + box on -> the box goes off, once, and says why ({note.strip()[:60]!r})",
    )
    note, var = _sync(deferred=True, ticked=False)
    ok(
        var.get() is False and var.writes == [] and note == "",
        "A2: gate set + box already off -> nothing written, nothing said",
    )
    note, var = _sync(deferred=False, ticked=True)
    ok(
        var.get() is True and var.writes == [] and note == "",
        "A3: a scene that traced -- the box stays exactly as the user set it",
    )
    note, var = _sync(deferred=False, ticked=False)
    ok(
        var.get() is False and var.writes == [] and note == "",
        "A4: no gate and no tick -> still nothing; the rule never ticks the box ON",
    )
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    src = inspect.getsource(Kraken3DInspector._sync_show_rays_toggle_to_scene)
    ok(
        "var.set(False)" in src and "set(True)" not in src,
        "A5: the implementation can only turn it off (asking for rays stays the user's)",
    )


def _check_wiring(ok) -> None:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin

    paint_src = inspect.getsource(Kraken3DInspector.refresh_scene)
    ok(
        "_sync_show_rays_toggle_to_scene()" in paint_src,
        "B1: the scene painter enforces it, so every refresh entry inherits the rule",
    )
    refresh_src = inspect.getsource(Kraken3DInspector.refresh_from_editor)
    ok(
        "_maybe_restore_open3d_session_state()" in refresh_src,
        "B2: the session restore runs at the START of a refresh -- the painter has the last word",
    )
    ok(
        "show_rays_var" in list(getattr(Kraken3DInspector, "_SESSION_TOGGLE_VAR_NAMES", []) or []),
        "B3: the restored toggles really do include show_rays_var (the root cause, pinned)",
    )
    open_src = inspect.getsource(ThreeDSceneToolsMixin._pending_rays_note)
    ok(
        "_sync_show_rays_toggle_to_scene()" in open_src and "rays_var.set(False)" not in open_src,
        "B4: the open path delegates to the one implementation instead of repeating it",
    )
    toggle_src = inspect.getsource(Kraken3DInspector._on_show_rays_changed)
    ok(
        "_preview_trace_deferred_until_requested = False" in toggle_src
        and "if bool(self.show_rays_var.get())" in toggle_src,
        "B5: bugs/0801 intact -- ticking the box clears the fast-load gate and traces, "
        "unticking does not",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    _check_rule(ok)
    _check_wiring(ok)

    passed = not any(n.startswith("FAIL") for n in notes)
    if verbose:
        for n in notes:
            print(n)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Open 3D rays-box-states-the-scene validation passed.")
        return 0
    print("Open 3D rays-box-states-the-scene validation FAILED:")
    for n in notes:
        if n.startswith("FAIL"):
            print(f"- {n}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
