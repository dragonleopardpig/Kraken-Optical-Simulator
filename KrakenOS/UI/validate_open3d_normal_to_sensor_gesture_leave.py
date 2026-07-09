"""flag_20260709_162334_323 -- "ISO view, all elements missing (except detector)". Leaving the
Normal-to-Sensor view via a nav-cube face/edge/corner pick or a free mouse orbit (NOT a cardinal/iso
preset button) must drop the sensor isolation, exactly as set_camera_preset already does -- otherwise
the LED plate / lens / rays / axis stay hidden and _reapply_sensor_isolation_if_active re-hides them
on every refresh, so the ISO view shows only the detector.

Both the nav-cube snap and the mouse orbit funnel through Kraken3DInspector._on_camera_interaction,
which now calls _leave_sensor_normal_on_gesture(view_dir). This guard exercises that method directly
against stub VTK actors (display-free -- no renderer, no Tk, no llvmpipe segfault). The stub scene
mirrors the coaxial MV-150 layout: a detector + two coplanar overlays at z=657 plus four off-plane
props (lens, LED cube, optical axis, ray). The guard asserts:
  * TURN-AWAY -- an off-normal sight line (the reported ISO direction (1,1,1)) leaves: the four hidden
    props re-show, the isolation intent is nulled, the preset drops to None, and returns True. A second
    call is a no-op (one-shot -- params already cleared).
  * STAY -- a face-on sight line (a pure zoom straight down the sensor normal) keeps the isolation:
    returns False, the props stay hidden, params + preset unchanged. This is why entering the view
    (camera set straight down the normal) never self-cancels.
  * PRESET-GUARD -- when the camera is no longer on the sensor_normal preset, the method is inert even
    for an off-normal view_dir (returns False).
  * NO-PARAMS -- on the sensor_normal preset but with no isolation recorded, the method no-ops (False).
"""
from __future__ import annotations

import numpy as np

from KrakenOS.UI.open3d_inspector import Kraken3DInspector


class _StubActor:
    def __init__(self, name: str, bounds, visible: bool = True) -> None:
        self.name = name
        self._bounds = tuple(float(v) for v in bounds)
        self._visible = 1 if visible else 0

    def GetBounds(self):
        return self._bounds

    def GetVisibility(self):
        return self._visible

    def SetVisibility(self, value):
        self._visible = 1 if value else 0


class _StubCollection:
    def __init__(self, actors):
        self._actors = list(actors)
        self._i = 0

    def InitTraversal(self):
        self._i = 0

    def GetNextItem(self):
        if self._i >= len(self._actors):
            return None
        actor = self._actors[self._i]
        self._i += 1
        return actor


class _StubRenderer:
    def __init__(self, actors):
        self._collection = _StubCollection(actors)

    def GetActors(self):
        return self._collection


class _StubInspector:
    # Bind the REAL methods under test onto a minimal stand-in so we exercise production logic
    # without constructing a full VTK/Tk inspector.
    _isolate_scene_to_sensor_plane = Kraken3DInspector._isolate_scene_to_sensor_plane
    _restore_sensor_isolation = Kraken3DInspector._restore_sensor_isolation
    _show_sensor_isolation_hidden = Kraken3DInspector._show_sensor_isolation_hidden
    _leave_sensor_normal_on_gesture = Kraken3DInspector._leave_sensor_normal_on_gesture
    _camera_preset = "sensor_normal"

    def __init__(self, actors, row_actor_map, actor_by_key):
        self._renderer = _StubRenderer(actors)
        self._row_actor_map = row_actor_map
        self._actor_by_key = actor_by_key


def _build_stub_scene():
    # Sensor plane at z=657 (the coaxial detector); normal +z; 23x23 sensor -> band max(3, 0.1*23)=3.0.
    det = _StubActor("detector", (-16.3, 16.3, -16.3, 16.3, 656.99, 657.01))       # row-mapped body
    heatmap = _StubActor("heatmap", (-11.5, 11.5, -11.5, 11.5, 657.0, 657.0))      # coplanar overlay
    square = _StubActor("sensor_square", (-11.5, 11.5, -11.5, 11.5, 657.0, 657.0)) # coplanar overlay
    lens = _StubActor("lens", (-17.5, 17.5, -17.5, 17.5, 446.0, 447.0))            # 211 mm off-plane
    led = _StubActor("led", (-27.5, 27.5, -39.0, 39.0, 202.0, 257.0))             # LED/BS cube
    axis = _StubActor("optical_axis", (0.0, 0.0, 0.0, 0.0, -467.0, 1186.0))        # spans the scene
    ray = _StubActor("ray", (-19.9, 19.5, -24.5, 32.8, 0.0, 657.0))               # ray polyline
    actors = [det, heatmap, square, lens, led, axis, ray]
    row_actor_map = {8: ["det_key"]}
    actor_by_key = {"det_key": det}
    return actors, row_actor_map, actor_by_key, {a.name: a for a in actors}


_CENTER = (0.0, 0.0, 657.0)
_NORMAL = (0.0, 0.0, 1.0)
_BAND = max(3.0, 0.1 * 23.0)
_HIDE = ("lens", "led", "optical_axis", "ray")
_KEEP = ("detector", "heatmap", "sensor_square")


def _isolated_inspector():
    actors, ram, abk, by_name = _build_stub_scene()
    insp = _StubInspector(actors, ram, abk)
    insp._isolate_scene_to_sensor_plane(_CENTER, _NORMAL, 8, band=_BAND)
    return insp, by_name


def _check_turn_away(failures: list[str], notes: list[str]) -> None:
    insp, by_name = _isolated_inspector()
    # An ISO nav-cube pick: sight line (1,1,1) is well off the +z sensor normal (|cos| ~ 0.577).
    iso_dir = np.array([1.0, 1.0, 1.0]) / float(np.linalg.norm([1.0, 1.0, 1.0]))
    left = insp._leave_sensor_normal_on_gesture(iso_dir)
    if left is not True:
        failures.append(f"TURN-AWAY: off-normal ISO gesture should leave the view (got {left!r})")
    for name in _HIDE:
        if not by_name[name].GetVisibility():
            failures.append(f"TURN-AWAY: '{name}' stayed hidden after leaving via nav-cube/orbit")
    if insp.__dict__.get("_sensor_isolation_params") is not None:
        failures.append("TURN-AWAY: isolation intent not cleared after leaving (would re-hide on refresh)")
    if getattr(insp, "_camera_preset", "sensor_normal") is not None:
        failures.append("TURN-AWAY: _camera_preset should drop to None after leaving the view")
    # One-shot: a second per-frame fire is inert (params already nulled).
    if insp._leave_sensor_normal_on_gesture(iso_dir) is not False:
        failures.append("TURN-AWAY: a second gesture after leaving should be a no-op")
    if not [f for f in failures if f.startswith("TURN-AWAY")]:
        notes.append("turn-away: off-normal nav-cube/orbit re-shows the 4 props, clears intent + preset")


def _check_stay(failures: list[str], notes: list[str]) -> None:
    insp, by_name = _isolated_inspector()
    # A pure zoom stays straight down the sensor normal: sight line anti-parallel to +z (|cos| = 1).
    left = insp._leave_sensor_normal_on_gesture((0.0, 0.0, -1.0))
    if left is not False:
        failures.append(f"STAY: a face-on zoom must NOT leave the view (got {left!r})")
    for name in _HIDE:
        if by_name[name].GetVisibility():
            failures.append(f"STAY: '{name}' should stay hidden while still face-on to the sensor")
    if insp.__dict__.get("_sensor_isolation_params") is None:
        failures.append("STAY: isolation intent must persist through a face-on zoom")
    if str(getattr(insp, "_camera_preset", None)) != "sensor_normal":
        failures.append("STAY: _camera_preset must remain 'sensor_normal' through a face-on zoom")
    if not [f for f in failures if f.startswith("STAY")]:
        notes.append("stay: a pure face-on zoom keeps the isolation (intent + preset intact)")


def _check_preset_guard(failures: list[str], notes: list[str]) -> None:
    insp, _ = _isolated_inspector()
    insp._camera_preset = "iso"  # already left via a preset button; the params linger only briefly
    iso_dir = np.array([1.0, 1.0, 1.0]) / float(np.linalg.norm([1.0, 1.0, 1.0]))
    if insp._leave_sensor_normal_on_gesture(iso_dir) is not False:
        failures.append("PRESET-GUARD: must be inert when the camera is no longer sensor_normal")
    else:
        notes.append("preset-guard: no-ops once _camera_preset left 'sensor_normal'")


def _check_no_params(failures: list[str], notes: list[str]) -> None:
    actors, ram, abk, _ = _build_stub_scene()
    insp = _StubInspector(actors, ram, abk)  # sensor_normal preset but no isolation recorded
    iso_dir = np.array([1.0, 1.0, 1.0]) / float(np.linalg.norm([1.0, 1.0, 1.0]))
    if insp._leave_sensor_normal_on_gesture(iso_dir) is not False:
        failures.append("NO-PARAMS: must no-op when no sensor isolation is recorded")
    else:
        notes.append("no-params: no-ops when there is no recorded isolation to leave")


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    notes: list[str] = []
    _check_turn_away(failures, notes)
    _check_stay(failures, notes)
    _check_preset_guard(failures, notes)
    _check_no_params(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    ok, messages = run_checks()
    for line in messages:
        print(("PASS " if ok else "") + line)
    print("RESULT:", "pass" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
