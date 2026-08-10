"""flag_20260709_125338_765 -- Overlays > Normal to Sensor must show ONLY the sensor + its
on-detector overlays and hide everything else (LED plate, lens bodies, ray polylines, axis guide),
so the illumination heatmap fills the canvas uncluttered.

This exercises Kraken3DInspector._isolate_scene_to_sensor_plane / _restore_sensor_isolation directly
against stub VTK actors (display-free -- no renderer, no Tk, no llvmpipe segfault risk). The stub
scene mirrors the coaxial MV-150 layout: a detector + its two coplanar overlays at the sensor plane
(z=657), and five off-plane props (lens 211 mm away, LED, camera, scene-spanning optical axis, and a
ray polyline). The guard asserts:
  * ISOLATE -- the detector body (by row map) and the two on-plane overlays (by proximity) stay
    visible/pickable; the five off-plane props are hidden and non-pickable.
  * RESTORE -- leaving the view re-shows every hidden prop, restores each prop's original pickability,
    and clears both restore lists.
  * INTERACTION -- cached STEP/CAD-row face rays and off-plane gizmo handles are inert; selecting an
    isolated registered STEP cannot rebuild its body or gizmo. Persistent browser hides survive restore.
  * RE-INVOKE -- a second isolate does not double-hide (it restores first), so the restore list holds
    exactly the off-plane props once, not stale duplicates.
  * RE-APPLY -- an overlay toggle rebuilds every actor fresh + visible (flag_20260709_150713_387: the
    Illumination overlay, and the follow-up "none of the overlays should re-enable other elements");
    after the rebuild the view RE-HIDES the off-plane props (any overlay), keeps the sensor, and
    renders. Leaving the view clears the intent so a later rebuild is inert, and the re-apply no-ops
    once the camera preset is no longer sensor-normal.
"""
from __future__ import annotations

import inspect

import KrakenOS.UI.open3d_inspector as inspector_module
from KrakenOS.UI.open3d_inspector import Kraken3DInspector


class _StubActor:
    def __init__(self, name: str, bounds, visible: bool = True, pickable: bool = True) -> None:
        self.name = name
        self._bounds = tuple(float(v) for v in bounds)
        self._visible = 1 if visible else 0
        self._pickable = 1 if pickable else 0

    def GetBounds(self):
        return self._bounds

    def GetVisibility(self):
        return self._visible

    def SetVisibility(self, value):
        self._visible = 1 if value else 0

    def GetPickable(self):
        return self._pickable

    def SetPickable(self, value):
        self._pickable = 1 if value else 0


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
    _reapply_sensor_isolation_if_active = Kraken3DInspector._reapply_sensor_isolation_if_active
    # bugs/0597: the re-apply now guarantees the sensor stays on screen via these helpers.
    _ensure_sensor_plane_visible = Kraken3DInspector._ensure_sensor_plane_visible
    _visible_actor_count = Kraken3DInspector._visible_actor_count
    _step_label_has_visible_body_actor = Kraken3DInspector._step_label_has_visible_body_actor
    _step_label_has_only_invisible_body_actors = (
        Kraken3DInspector._step_label_has_only_invisible_body_actors
    )
    _row_body_actor_keys = Kraken3DInspector._row_body_actor_keys
    _row_has_only_invisible_body_actors = Kraken3DInspector._row_has_only_invisible_body_actors
    _step_feature_pick_for_display_xy = Kraken3DInspector._step_feature_pick_for_display_xy
    _row_face_ray_pick_for_display_xy = Kraken3DInspector._row_face_ray_pick_for_display_xy
    is_scene_row_hidden = Kraken3DInspector.is_scene_row_hidden
    is_step_label_hidden = Kraken3DInspector.is_step_label_hidden
    _camera_preset = "sensor_normal"

    def __init__(self, actors, row_actor_map, actor_by_key, actor_row_map=None, step_actor_map=None):
        self._renderer = _StubRenderer(actors)
        self._gizmo_overlay_renderer = None
        self._row_actor_map = row_actor_map
        self._actor_by_key = actor_by_key
        self._actor_row_map = dict(actor_row_map or {})
        self._step_actor_map = dict(step_actor_map or {})
        self._actor_step_rotate_map = {}
        self._actor_step_rotate_visual_keys = set()
        self._hidden_scene_rows = set()
        self._hidden_step_labels = set()
        self._hidden_source_ids = set()
        self._render_calls = 0
        self._hover_outline_clear_calls = 0
        self._hover_status_clear_calls = 0
        self._cursor_states: list[bool] = []

    def _set_step_hover_outline(self, outline, key, *, render=True):
        if outline is None and key is None and not render:
            self._hover_outline_clear_calls += 1

    def _update_hover_status(self, text, *, display_xy=None, render=True):
        if not text and not render:
            self._hover_status_clear_calls += 1

    def _set_axis_pick_cursor(self, state):
        self._cursor_states.append(bool(state))

    def _apply_scene_element_visibility(self):
        for row_index in self._hidden_scene_rows:
            for actor_key in self._row_actor_map.get(int(row_index), []) or []:
                actor = self._actor_by_key.get(actor_key)
                if actor is not None:
                    actor.SetVisibility(False)
        for label in self._hidden_step_labels:
            for actor_key in self._step_actor_map.get(str(label), []) or []:
                actor = self._actor_by_key.get(actor_key)
                if actor is not None:
                    actor.SetVisibility(False)

    def render(self):
        # _reapply_sensor_isolation_if_active renders when it re-hides anything.
        self._render_calls += 1

    def rebuild_scene(
        self, actors, row_actor_map, actor_by_key, actor_row_map=None, step_actor_map=None
    ):
        # Mirror a refresh_scene rebuild: an overlay toggle re-creates every actor fresh + visible,
        # so the renderer collection and row/key maps point at brand-new objects.
        self._renderer = _StubRenderer(actors)
        self._row_actor_map = row_actor_map
        self._actor_by_key = actor_by_key
        self._actor_row_map = dict(actor_row_map or {})
        self._step_actor_map = dict(step_actor_map or {})


def _build_stub_scene():
    # Sensor plane at z=657 (the coaxial detector); normal +z; 23x23 sensor -> band max(3, 0.1*23)=3.0.
    det = _StubActor("detector", (-16.3, 16.3, -16.3, 16.3, 656.99, 657.01))       # row-mapped body
    heatmap = _StubActor(
        "heatmap", (-11.5, 11.5, -11.5, 11.5, 657.0, 657.0), pickable=False
    )                                                                                # coplanar overlay
    square = _StubActor("sensor_square", (-11.5, 11.5, -11.5, 11.5, 657.0, 657.0)) # coplanar overlay
    lens = _StubActor("lens", (-17.5, 17.5, -17.5, 17.5, 446.0, 447.0))            # 211 mm off-plane
    led = _StubActor("led", (-27.5, 27.5, -39.0, 39.0, 202.0, 257.0))             # LED/BS cube
    axis = _StubActor(
        "optical_axis", (0.0, 0.0, 0.0, 0.0, -467.0, 1186.0), pickable=False
    )                                                                                # spans the scene
    ray = _StubActor("ray", (-19.9, 19.5, -24.5, 32.8, 0.0, 657.0))               # ray polyline
    camera = _StubActor("camera", (-35.0, 35.0, -35.0, 35.0, 645.0, 720.0))       # spans plane, off-band
    actors = [det, heatmap, square, lens, led, camera, axis, ray]
    row_actor_map = {8: ["det_key"], 1: ["lens_key"]}
    actor_by_key = {
        "det_key": det,
        "lens_key": lens,
        "led_key": led,
        "camera_key": camera,
    }
    actor_row_map = {"det_key": 8, "lens_key": 1}
    step_actor_map = {"led": ["led_key"], "camera": ["camera_key"]}
    return (
        actors,
        row_actor_map,
        actor_by_key,
        actor_row_map,
        step_actor_map,
        {a.name: a for a in actors},
    )


def _check(failures: list[str], notes: list[str]) -> None:
    center = (0.0, 0.0, 657.0)
    normal = (0.0, 0.0, 1.0)
    band = max(3.0, 0.1 * 23.0)

    actors, row_actor_map, actor_by_key, actor_row_map, step_actor_map, by_name = _build_stub_scene()
    insp = _StubInspector(actors, row_actor_map, actor_by_key, actor_row_map, step_actor_map)
    if insp._step_label_has_only_invisible_body_actors("led"):
        failures.append("PRECONDITION: visible LED STEP body was not interaction-visible")
    if insp._step_label_has_only_invisible_body_actors("camera"):
        failures.append("PRECONDITION: visible camera STEP body was not interaction-visible")
    if insp._row_has_only_invisible_body_actors(1):
        failures.append("PRECONDITION: visible CAD row body was not interaction-visible")
    hidden_count = insp._isolate_scene_to_sensor_plane(center, normal, 8, band=band)

    keep = {"detector", "heatmap", "sensor_square"}
    hide = {"lens", "led", "camera", "optical_axis", "ray"}
    original_keep_pickable = {name: by_name[name].GetPickable() for name in keep}
    for name in keep:
        if not by_name[name].GetVisibility():
            failures.append(f"ISOLATE: '{name}' should stay visible (sensor plane) but was hidden")
        if by_name[name].GetPickable() != original_keep_pickable[name]:
            failures.append(f"ISOLATE: '{name}' sensor-plane pickability changed")
    for name in hide:
        if by_name[name].GetVisibility():
            failures.append(f"ISOLATE: '{name}' should be hidden (off sensor plane) but stayed visible")
        if by_name[name].GetPickable():
            failures.append(f"ISOLATE: '{name}' should be non-pickable while hidden")
    if hidden_count != len(hide):
        failures.append(f"ISOLATE: hid {hidden_count} actors, expected {len(hide)}")
    if insp._hover_outline_clear_calls != 1 or insp._hover_status_clear_calls != 1:
        failures.append("ISOLATE: stale face hover outline/status was not cleared on entry")
    if insp._cursor_states != [False]:
        failures.append("ISOLATE: stale face-pick cursor was not reset on entry")
    if not insp._step_label_has_only_invisible_body_actors("led"):
        failures.append("ISOLATE: invisible LED STEP remains interaction-visible")
    if not insp._step_label_has_only_invisible_body_actors("camera"):
        failures.append("ISOLATE: invisible camera STEP remains interaction-visible")
    if not insp._step_label_has_visible_body_actor("led"):
        failures.append("ISOLATE: temporary hide lost the LED body registration (rebuild risk)")
    if not insp._step_label_has_visible_body_actor("camera"):
        failures.append("ISOLATE: temporary hide lost the camera body registration (rebuild risk)")
    if not insp._row_has_only_invisible_body_actors(1):
        failures.append("ISOLATE: invisible CAD row remains interaction-visible")
    if insp._row_has_only_invisible_body_actors(8):
        failures.append("ISOLATE: detector row should remain interaction-visible")
    if insp._step_feature_pick_for_display_xy("led", (100, 100)) is not None:
        failures.append("ISOLATE: cached STEP ray picker reached the invisible LED")
    if insp._step_feature_pick_for_display_xy("camera", (100, 100)) is not None:
        failures.append("ISOLATE: cached STEP ray picker reached the invisible camera")
    if insp._row_face_ray_pick_for_display_xy(1, (100, 100)) is not None:
        failures.append("ISOLATE: cached CAD-row ray picker reached the invisible row")
    if not failures:
        notes.append(f"isolate: kept {sorted(keep)}, hid {hidden_count} off-plane props")

    # RESTORE -- every hidden prop comes back, restore list cleared.
    insp._restore_sensor_isolation()
    for name in hide:
        if not by_name[name].GetVisibility():
            failures.append(f"RESTORE: '{name}' stayed hidden after leaving the view")
    for name in hide - {"optical_axis"}:
        if not by_name[name].GetPickable():
            failures.append(f"RESTORE: '{name}' did not regain its original pickability")
    if by_name["optical_axis"].GetPickable():
        failures.append("RESTORE: originally non-pickable optical axis became pickable")
    if insp._step_label_has_only_invisible_body_actors("led"):
        failures.append("RESTORE: LED STEP interaction did not return")
    if insp._step_label_has_only_invisible_body_actors("camera"):
        failures.append("RESTORE: camera STEP interaction did not return")
    if insp._row_has_only_invisible_body_actors(1):
        failures.append("RESTORE: CAD row interaction did not return")
    if insp.__dict__.get("_sensor_isolation_restore"):
        failures.append("RESTORE: restore list not cleared after _restore_sensor_isolation")
    if insp.__dict__.get("_sensor_isolation_pickable_restore"):
        failures.append("RESTORE: pickability restore list not cleared after _restore_sensor_isolation")
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
        notes.append(f"re-invoke: idempotent, restore list holds the {len(hide)} off-plane props once")


def _check_reapply(failures: list[str], notes: list[str]) -> None:
    # flag_20260709_150713_387 + "none of the overlays should re-enable other elements": an overlay
    # toggle rebuilds the scene (fresh, all-visible actors), wiping the one-shot isolation. The view
    # must RE-APPLY the isolation after the rebuild, for ANY overlay, until the user leaves the view.
    center = (0.0, 0.0, 657.0)
    normal = (0.0, 0.0, 1.0)
    band = max(3.0, 0.1 * 23.0)
    keep = {"detector", "heatmap", "sensor_square"}
    hide = {"lens", "led", "camera", "optical_axis", "ray"}

    actors, row_actor_map, actor_by_key, actor_row_map, step_actor_map, _ = _build_stub_scene()
    insp = _StubInspector(actors, row_actor_map, actor_by_key, actor_row_map, step_actor_map)
    insp._isolate_scene_to_sensor_plane(center, normal, 8, band=band)

    # An overlay toggle routes through refresh_scene, which re-creates every actor fresh + visible.
    actors2, ram2, abk2, arm2, sam2, by_name2 = _build_stub_scene()
    insp.rebuild_scene(actors2, ram2, abk2, arm2, sam2)
    if any(not by_name2[n].GetVisibility() for n in hide):
        failures.append("REBUILD: a freshly rebuilt scene should start fully visible")

    insp._reapply_sensor_isolation_if_active()
    for name in keep:
        if not by_name2[name].GetVisibility():
            failures.append(f"REAPPLY: '{name}' should stay visible after re-isolation")
    for name in hide:
        if by_name2[name].GetVisibility():
            failures.append(f"REAPPLY: '{name}' should be re-hidden after a rebuild (overlay toggle)")
    if insp._render_calls < 1:
        failures.append("REAPPLY: re-hiding actors after a rebuild should trigger a render")
    if not [f for f in failures if f[:7] in ("REAPPLY", "REBUILD")]:
        notes.append(
            f"reapply: an overlay-toggle rebuild re-hides the {len(hide)} off-plane props, keeps the sensor"
        )

    # Leaving the view (set_camera_preset -> _restore) drops the intent: a later rebuild is inert.
    insp._restore_sensor_isolation()
    actors3, ram3, abk3, arm3, sam3, by_name3 = _build_stub_scene()
    insp.rebuild_scene(actors3, ram3, abk3, arm3, sam3)
    insp._reapply_sensor_isolation_if_active()
    if any(not by_name3[n].GetVisibility() for n in hide):
        failures.append("INTENT-CLEAR: after leaving the view a rebuild must NOT re-hide anything")
    if not [f for f in failures if f.startswith("INTENT-CLEAR")]:
        notes.append("intent-clear: leaving the view stops the re-apply (restore cleared the params)")

    # Preset guard: once the camera is no longer sensor-normal, reapply is inert even with params set.
    actors4, ram4, abk4, arm4, sam4, _ = _build_stub_scene()
    insp4 = _StubInspector(actors4, ram4, abk4, arm4, sam4)
    insp4._isolate_scene_to_sensor_plane(center, normal, 8, band=band)
    actors5, ram5, abk5, arm5, sam5, by_name5 = _build_stub_scene()
    insp4.rebuild_scene(actors5, ram5, abk5, arm5, sam5)
    insp4._camera_preset = "iso"
    insp4._reapply_sensor_isolation_if_active()
    if any(not by_name5[n].GetVisibility() for n in hide):
        failures.append("PRESET-GUARD: reapply must be inert when the camera left the sensor-normal preset")
    if not [f for f in failures if f.startswith("PRESET-GUARD")]:
        notes.append("preset-guard: reapply no-ops once the camera preset is no longer sensor_normal")


def _check_cached_step_pick_gate(failures: list[str], notes: list[str]) -> None:
    """Exercise the visibility choke without loading any STEP geometry."""
    actor = _StubActor("led", (-1, 1, -1, 1, -1, 1))
    inspector = _StubInspector(
        [actor], {}, {"led_key": actor}, step_actor_map={"led": ["led_key"]}
    )
    unknown = _StubInspector([], {}, {})
    sentinel = {"feature": "cached-face"}
    original = inspector_module.step_feature_pick_for_display_xy
    inspector_module.step_feature_pick_for_display_xy = lambda *_args, **_kwargs: sentinel
    try:
        if inspector._step_feature_pick_for_display_xy("led", (10, 10)) is not sentinel:
            failures.append("PICK-BEHAVIOR: visible STEP did not reach the cached face picker")
        actor.SetVisibility(False)
        if inspector._step_feature_pick_for_display_xy("led", (10, 10)) is not None:
            failures.append("PICK-BEHAVIOR: known-all-invisible STEP reached cached geometry")
        if unknown._step_feature_pick_for_display_xy("led", (10, 10)) is not sentinel:
            failures.append("PICK-BEHAVIOR: no-actor transparent/transient fallback was blocked")
    finally:
        inspector_module.step_feature_pick_for_display_xy = original
    if not [failure for failure in failures if failure.startswith("PICK-BEHAVIOR")]:
        notes.append("pick-behavior: visible/unknown STEP fallback survives; invisible registered body is inert")


def _check_persistent_hide_survives_restore(failures: list[str], notes: list[str]) -> None:
    center = (0.0, 0.0, 657.0)
    actors, row_actor_map, actor_by_key, actor_row_map, step_actor_map, by_name = _build_stub_scene()
    inspector = _StubInspector(
        actors, row_actor_map, actor_by_key, actor_row_map, step_actor_map
    )
    inspector._isolate_scene_to_sensor_plane(center, (0.0, 0.0, 1.0), 8, band=3.0)
    # Mirror browser actions made while the temporary isolation is active.
    inspector._hidden_step_labels.add("camera")
    inspector._hidden_scene_rows.add(1)
    inspector._restore_sensor_isolation()
    if by_name["camera"].GetVisibility():
        failures.append("PERSISTENT-HIDE: restoring sensor isolation re-showed hidden camera STEP")
    if by_name["lens"].GetVisibility():
        failures.append("PERSISTENT-HIDE: restoring sensor isolation re-showed hidden CAD row")
    if not by_name["led"].GetVisibility():
        failures.append("PERSISTENT-HIDE: restore failed to re-show a non-persistently-hidden LED")
    if not [failure for failure in failures if failure.startswith("PERSISTENT-HIDE")]:
        notes.append("persistent-hide: browser-hidden STEP/row stay hidden when sensor isolation restores")


def _check_gizmo_layer_isolated(failures: list[str], notes: list[str]) -> None:
    actors, row_actor_map, actor_by_key, actor_row_map, step_actor_map, _ = _build_stub_scene()
    inspector = _StubInspector(
        actors, row_actor_map, actor_by_key, actor_row_map, step_actor_map
    )
    gizmo = _StubActor("led_move_handle", (-2, 2, -2, 2, 198, 206))
    inspector._gizmo_overlay_renderer = _StubRenderer([gizmo])
    hidden = inspector._isolate_scene_to_sensor_plane(
        (0.0, 0.0, 657.0), (0.0, 0.0, 1.0), 8, band=3.0
    )
    if gizmo.GetVisibility() or gizmo.GetPickable():
        failures.append("GIZMO-LAYER: off-plane move/rotate handle remained visible or pickable")
    if hidden != 6:
        failures.append(f"GIZMO-LAYER: isolated {hidden} props, expected five main + one gizmo")
    inspector._restore_sensor_isolation()
    if not gizmo.GetVisibility() or not gizmo.GetPickable():
        failures.append("GIZMO-LAYER: move/rotate handle state did not restore")
    if not [failure for failure in failures if failure.startswith("GIZMO-LAYER")]:
        notes.append("gizmo-layer: off-plane handles hide with bodies and restore exactly")


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    notes: list[str] = []
    _check(failures, notes)
    _check_reapply(failures, notes)
    _check_cached_step_pick_gate(failures, notes)
    _check_persistent_hide_survives_restore(failures, notes)
    _check_gizmo_layer_isolated(failures, notes)
    step_pick_source = inspect.getsource(Kraken3DInspector._step_feature_pick_for_display_xy)
    if "_step_label_has_only_invisible_body_actors" not in step_pick_source:
        failures.append("PICK-GATE: cached STEP picker ignores live actor visibility")
    row_pick_source = inspect.getsource(Kraken3DInspector._row_face_ray_pick_for_display_xy)
    if "_row_has_only_invisible_body_actors" not in row_pick_source:
        failures.append("PICK-GATE: cached CAD-row picker ignores live actor visibility")
    reconcile_source = inspect.getsource(Kraken3DInspector._reconcile_step_rotation_handles)
    ensure_source = inspect.getsource(Kraken3DInspector._ensure_step_rotation_handles_for_label)
    if "_step_label_has_only_invisible_body_actors" not in reconcile_source + ensure_source:
        failures.append("PICK-GATE: isolated STEP can rebuild a visible move/rotate gizmo")
    if not [failure for failure in failures if failure.startswith("PICK-GATE")]:
        notes.append(
            "pick-gate: cached STEP/CAD-row rays and gizmos reject known-all-invisible bodies"
        )
    return (not failures), (failures + notes)


def main() -> int:
    ok, messages = run_checks()
    for line in messages:
        print(("PASS " if ok else "") + line)
    print("RESULT:", "pass" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
