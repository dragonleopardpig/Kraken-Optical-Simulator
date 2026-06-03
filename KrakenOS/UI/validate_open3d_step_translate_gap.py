"""Validate the bug-0004 STEP move gizmo: free axial translation + live edge gap.

Display-free contracts under test (no X server needed -- the renderer, the
thickness-dimension service, and the billboard label class are faked so the
inspector logic runs in isolation):

* ``_step_overlay_axial_gap(label, axis_unit)`` is a clean, side-effect-free
  seam: it reports the signed edge-to-edge distance from a STEP overlay's near
  face to the *previous* component's far face (the one just behind it along the
  axis), ignoring components ahead of it, and returns ``None`` when the overlay
  is the first component. This is the query a future focus/collimation
  quick-solve drives while sweeping axial position.
* The live drag overlay rebuilds each motion without leaking actors and a clear
  removes every transient actor (renderer view-props + ``_actor_by_key``
  registrations) and empties the gap-actor list.
* ``_finish_step_translate_drag`` commits the *total* accumulated delta exactly
  once through ``editor.translate_step_overlay`` (additive, one history entry)
  with NO track-length clamp -- the optical axis is treated as infinite, so an
  arbitrarily large slide commits verbatim.

Run from the repository root:

    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_translate_gap
"""

from __future__ import annotations

from typing import Any

import numpy as np

import KrakenOS.UI.open3d_inspector as o3i
from KrakenOS.UI.open3d_inspector import Kraken3DInspector


class _Prop:
    def __getattr__(self, _name: str) -> Any:
        return lambda *args, **kwargs: None


class _Billboard:
    def __init__(self) -> None:
        self.text: str | None = None
        self.position: tuple[float, float, float] | None = None

    def SetInput(self, text: str) -> None:
        self.text = str(text)

    def SetPosition(self, *position: float) -> None:
        self.position = tuple(float(value) for value in position)

    def PickableOff(self) -> None:
        return None

    def GetTextProperty(self) -> _Prop:
        return _Prop()


class _Actor:
    def __init__(self, bounds: tuple[float, ...] | None = None) -> None:
        self._bounds = tuple(float(value) for value in (bounds or (0, 0, 0, 0, 0, 0)))

    def GetBounds(self) -> tuple[float, ...]:
        return self._bounds

    def GetAddressAsString(self, _hint: str) -> str:
        return f"actor-{id(self)}"


class _Renderer:
    def __init__(self) -> None:
        self.props: list[Any] = []

    def AddViewProp(self, actor: Any) -> None:
        self.props.append(actor)

    def RemoveViewProp(self, actor: Any) -> None:
        if actor in self.props:
            self.props.remove(actor)


class _PV:
    def Line(self, _start: Any, _end: Any) -> Any:
        return type("_Mesh", (), {"n_points": 2})()


class _ThicknessService:
    def __init__(self) -> None:
        self.pv = _PV()

    @staticmethod
    def offset_direction(_segment: Any) -> np.ndarray:
        return np.asarray((1.0, 0.0, 0.0), dtype=float)

    def arrow_mesh(self, _start: Any, _end: Any, *, scene_span: float) -> Any:
        del scene_span
        return type("_Mesh", (), {"n_points": 32})()


class _StatusVar:
    def __init__(self) -> None:
        self.last = ""

    def set(self, message: str) -> None:
        self.last = str(message)


class _Editor:
    def __init__(self, *, physics_requested: bool = True) -> None:
        self.translate_calls: list[dict[str, Any]] = []
        self.partial_refreshes: list[str] = []
        self.debug: list[str] = []
        self._physics_requested = bool(physics_requested)

    def append_debug(self, message: str) -> None:
        self.debug.append(str(message))

    def _step_overlay_display_label(self, label: str) -> str:
        return str(label)

    def translate_step_overlay(
        self, label: str, delta: Any, *, refresh: bool = True, record_history: bool = True
    ) -> None:
        self.translate_calls.append(
            {
                "label": str(label),
                "delta": tuple(float(value) for value in delta),
                "refresh": bool(refresh),
                "record_history": bool(record_history),
            }
        )

    def _open3d_trace_refresh_service(self) -> Any:
        physics = self._physics_requested

        class _Svc:
            def inspector_physics_requested(self, _inspector: Any) -> bool:
                return physics

        return _Svc()


def _make_inspector(*, with_renderer: bool, physics_requested: bool = True) -> Kraken3DInspector:
    insp = Kraken3DInspector.__new__(Kraken3DInspector)
    insp.editor = _Editor(physics_requested=physics_requested)
    insp.status_var = _StatusVar()
    insp._renderer = _Renderer() if with_renderer else None
    insp._step_translate_gap_actors = []
    insp._step_actor_map = {}
    insp._row_actor_map = {}
    insp._actor_by_key = {}
    service = _ThicknessService()
    insp._open3d_thickness_dimension_service = lambda: service  # type: ignore[method-assign]
    insp._row_scene_bounds = lambda: (np.zeros(3), 100.0)  # type: ignore[method-assign]
    insp.render = lambda: None  # type: ignore[method-assign]
    insp.refresh_imported_step_overlay = lambda label, **kw: insp.editor.partial_refreshes.append(str(label)) or True  # type: ignore[method-assign]

    def _add_mesh_actor(_mesh: Any, **_kwargs: Any) -> _Actor:
        actor = _Actor()
        key = insp._actor_key(actor)
        if key is not None:
            insp._actor_by_key[key] = actor
        return actor

    insp._add_mesh_actor = _add_mesh_actor  # type: ignore[method-assign]
    return insp


def _check_gap_math() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    insp = _make_inspector(with_renderer=False)
    insp._step_actor_map = {"lens": ["lens0"]}
    insp._row_actor_map = {0: ["row0"], 1: ["row1"]}
    insp._actor_by_key = {
        "lens0": _Actor((-4.0, 4.0, -2.5, 2.5, 20.0, 30.0)),
        "row0": _Actor((-5.0, 5.0, -3.0, 3.0, 0.0, 10.0)),    # behind the lens
        "row1": _Actor((-5.0, 5.0, -3.0, 3.0, 40.0, 50.0)),   # ahead of the lens
    }
    gap = insp._step_overlay_axial_gap("lens")
    ok = gap is not None
    checks.append(("default Z-axis gap resolves", ok, repr(gap)))
    if ok:
        near, far, gap_mm = gap
        checks.append(("gap is edge-to-edge (z_min - prev z_max)", abs(gap_mm - 10.0) < 1e-9, f"gap_mm={gap_mm}"))
        checks.append(("near point sits on the lens near face", abs(float(near[2]) - 20.0) < 1e-9, repr(tuple(near))))
        checks.append(("far point sits on the previous far face", abs(float(far[2]) - 10.0) < 1e-9, repr(tuple(far))))
        checks.append(
            ("previous = component behind, never ahead", abs(float(far[2]) - 10.0) < 1e-9 and float(far[2]) < float(near[2]), repr(tuple(far))),
        )

    # No component behind -> None (the lens is the first element).
    insp._row_actor_map = {1: ["row1"]}
    checks.append(("no previous component -> None", insp._step_overlay_axial_gap("lens") is None, "expected None"))

    # Explicit axis passthrough matches the default Z behavior.
    insp._row_actor_map = {0: ["row0"]}
    gap2 = insp._step_overlay_axial_gap("lens", (0.0, 0.0, 1.0))
    checks.append(("explicit axis_unit matches default", gap2 is not None and abs(gap2[2] - 10.0) < 1e-9, repr(gap2)))

    # Unknown label -> None, no raise.
    checks.append(("unknown label -> None", insp._step_overlay_axial_gap("nope") is None, "expected None"))
    return checks


def _check_overlay_lifecycle() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    saved_billboard = o3i.vtkBillboardTextActor3D
    o3i.vtkBillboardTextActor3D = _Billboard
    try:
        insp = _make_inspector(with_renderer=True)
        insp._step_actor_map = {"lens": ["lens0"]}
        insp._row_actor_map = {0: ["row0"]}
        insp._actor_by_key = {
            "lens0": _Actor((-4.0, 4.0, -2.5, 2.5, 20.0, 30.0)),
            "row0": _Actor((-5.0, 5.0, -3.0, 3.0, 0.0, 10.0)),
        }
        baseline_keys = set(insp._actor_by_key)
        state = {"label": "lens", "axis": "z", "axis_unit": np.asarray((0.0, 0.0, 1.0), dtype=float), "applied_delta_mm": 2.5}

        insp._update_step_translate_drag_overlay(state)
        first_count = len(insp._step_translate_gap_actors)
        new_mesh_keys = set(insp._actor_by_key) - baseline_keys
        checks.append(("motion draws gap actors", first_count >= 2, f"count={first_count}"))
        checks.append(("gap mesh actors register in _actor_by_key", len(new_mesh_keys) >= 1, repr(new_mesh_keys)))
        checks.append(("billboard label added to renderer", len(insp._renderer.props) >= 1, str(len(insp._renderer.props))))
        checks.append(("status reports the live edge gap", "edge gap to previous = 10" in insp.status_var.last, insp.status_var.last))

        insp._update_step_translate_drag_overlay(state)
        checks.append(("rebuild keeps a stable actor count", len(insp._step_translate_gap_actors) == first_count, str(len(insp._step_translate_gap_actors))))
        checks.append(("rebuild unregisters the stale mesh actors", set(insp._actor_by_key).isdisjoint(new_mesh_keys), repr(set(insp._actor_by_key) - baseline_keys)))

        insp._clear_step_translate_drag_overlay()
        checks.append(("clear empties the gap-actor list", insp._step_translate_gap_actors == [], repr(insp._step_translate_gap_actors)))
        checks.append(("clear restores _actor_by_key to baseline", set(insp._actor_by_key) == baseline_keys, repr(set(insp._actor_by_key))))
        checks.append(("clear removes the billboard from the renderer", insp._renderer.props == [], repr(insp._renderer.props)))

        # No component behind -> plain move status, no transient actors.
        insp._row_actor_map = {}
        insp.status_var.last = ""
        insp._update_step_translate_drag_overlay(state)
        checks.append(("no-previous draws nothing", insp._step_translate_gap_actors == [], repr(insp._step_translate_gap_actors)))
        checks.append(
            ("no-previous falls back to plain move status", "move:" in insp.status_var.last and "edge gap" not in insp.status_var.last, insp.status_var.last),
        )
    finally:
        o3i.vtkBillboardTextActor3D = saved_billboard
    return checks


def _check_free_translation_commit() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    # A large accumulated delta must commit verbatim (no track-length clamp).
    insp = _make_inspector(with_renderer=True, physics_requested=True)
    state = {"label": "lens", "axis": "z", "axis_unit": np.asarray((0.0, 0.0, 1.0), dtype=float), "applied_delta_mm": 250.0}
    insp._finish_step_translate_drag(state)
    calls = insp.editor.translate_calls
    checks.append(("commit happens exactly once", len(calls) == 1, repr(calls)))
    if calls:
        call = calls[0]
        checks.append(("commit carries the full accumulated delta (no clamp)", abs(call["delta"][2] - 250.0) < 1e-9, repr(call["delta"])))
        checks.append(("commit leaves the lateral axes untouched", abs(call["delta"][0]) < 1e-9 and abs(call["delta"][1]) < 1e-9, repr(call["delta"])))
        checks.append(("commit records a single history entry", call["record_history"] is True, repr(call)))
        checks.append(("commit refreshes when physics is requested", call["refresh"] is True, repr(call)))
    checks.append(("physics-requested commit skips the partial-refresh fallback", insp.editor.partial_refreshes == [], repr(insp.editor.partial_refreshes)))

    # A zero-delta release commits nothing (just reports no movement).
    insp_zero = _make_inspector(with_renderer=True, physics_requested=True)
    insp_zero._finish_step_translate_drag({"label": "lens", "axis": "z", "axis_unit": np.asarray((0.0, 0.0, 1.0)), "applied_delta_mm": 0.0})
    checks.append(("zero-delta release does not commit", insp_zero.editor.translate_calls == [], repr(insp_zero.editor.translate_calls)))
    checks.append(("zero-delta release reports no movement", "no movement" in insp_zero.status_var.last, insp_zero.status_var.last))

    # When physics is NOT requested, the release issues a partial overlay refresh.
    insp_np = _make_inspector(with_renderer=True, physics_requested=False)
    insp_np._finish_step_translate_drag({"label": "lens", "axis": "z", "axis_unit": np.asarray((0.0, 0.0, 1.0)), "applied_delta_mm": 7.0})
    checks.append(("non-physics commit still happens once", len(insp_np.editor.translate_calls) == 1, repr(insp_np.editor.translate_calls)))
    checks.append(("non-physics commit triggers a partial overlay refresh", insp_np.editor.partial_refreshes == ["lens"], repr(insp_np.editor.partial_refreshes)))
    return checks


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    checks.extend(_check_gap_math())
    checks.extend(_check_overlay_lifecycle())
    checks.extend(_check_free_translation_commit())

    failed = [(name, detail) for name, ok, detail in checks if not ok]
    if failed:
        print("Open 3D STEP translate gap validation failed:")
        for name, detail in failed:
            print(f"- {name}: {detail}")
        return 1
    print(f"Open 3D STEP translate gap validation passed ({len(checks)} checks).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
