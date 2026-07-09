"""flag_20260709_125338_765 -- Overlays > Normal to Sensor must show ONLY the sensor + its
on-detector overlays and hide everything else (LED plate, lens bodies, ray polylines, axis guide),
so the illumination heatmap fills the canvas uncluttered.

This exercises Kraken3DInspector._isolate_scene_to_sensor_plane / _restore_sensor_isolation directly
against stub VTK actors (display-free -- no renderer, no Tk, no llvmpipe segfault risk). The stub
scene mirrors the coaxial MV-150 layout: a detector + its two coplanar overlays at the sensor plane
(z=657), and four off-plane props (lens 211 mm away, LED cube, the scene-spanning optical axis, a ray
polyline). The guard asserts:
  * ISOLATE -- the detector body (by row map) and the two on-plane overlays (by proximity) stay
    visible; the four off-plane props are hidden.
  * RESTORE -- leaving the view re-shows every hidden prop and clears the restore list.
  * RE-INVOKE -- a second isolate does not double-hide (it restores first), so the restore list holds
    exactly the off-plane props once, not stale duplicates.
"""
from __future__ import annotations

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


def _check(failures: list[str], notes: list[str]) -> None:
    center = (0.0, 0.0, 657.0)
    normal = (0.0, 0.0, 1.0)
    band = max(3.0, 0.1 * 23.0)

    actors, row_actor_map, actor_by_key, by_name = _build_stub_scene()
    insp = _StubInspector(actors, row_actor_map, actor_by_key)
    hidden_count = insp._isolate_scene_to_sensor_plane(center, normal, 8, band=band)

    keep = {"detector", "heatmap", "sensor_square"}
    hide = {"lens", "led", "optical_axis", "ray"}
    for name in keep:
        if not by_name[name].GetVisibility():
            failures.append(f"ISOLATE: '{name}' should stay visible (sensor plane) but was hidden")
    for name in hide:
        if by_name[name].GetVisibility():
            failures.append(f"ISOLATE: '{name}' should be hidden (off sensor plane) but stayed visible")
    if hidden_count != len(hide):
        failures.append(f"ISOLATE: hid {hidden_count} actors, expected {len(hide)}")
    if not failures:
        notes.append(f"isolate: kept {sorted(keep)}, hid {hidden_count} off-plane props")

    # RESTORE -- every hidden prop comes back, restore list cleared.
    insp._restore_sensor_isolation()
    for name in hide:
        if not by_name[name].GetVisibility():
            failures.append(f"RESTORE: '{name}' stayed hidden after leaving the view")
    if insp.__dict__.get("_sensor_isolation_restore"):
        failures.append("RESTORE: restore list not cleared after _restore_sensor_isolation")
    if not [f for f in failures if f.startswith("RESTORE")]:
        notes.append("restore: all off-plane props re-shown, list cleared")

    # RE-INVOKE -- isolate a second time; it must restore first, so no stale double-hide.
    insp._isolate_scene_to_sensor_plane(center, normal, 8, band=band)
    again = insp._isolate_scene_to_sensor_plane(center, normal, 8, band=band)
    if again != len(hide):
        failures.append(f"RE-INVOKE: second isolate hid {again}, expected {len(hide)} (stale state?)")
    restore_list = insp.__dict__.get("_sensor_isolation_restore") or []
    if len(restore_list) != len(hide):
        failures.append(f"RE-INVOKE: restore list holds {len(restore_list)} actors, expected {len(hide)}")
    if not [f for f in failures if f.startswith("RE-INVOKE")]:
        notes.append("re-invoke: idempotent, restore list holds the 4 off-plane props once")


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    notes: list[str] = []
    _check(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    ok, messages = run_checks()
    for line in messages:
        print(("PASS " if ok else "") + line)
    print("RESULT:", "pass" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
