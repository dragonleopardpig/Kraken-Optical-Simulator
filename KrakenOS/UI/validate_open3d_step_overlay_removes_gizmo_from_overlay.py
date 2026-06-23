"""Guard for bugs/0118 -- a partial STEP-overlay refresh must remove gizmo handle
actors from the gizmo OVERLAY renderer, not only the main renderer.

Regression context
------------------
Gizmo handles render only in the always-on-top overlay renderer
(`_gizmo_overlay_renderer`, bugs/0112). The partial refresh
`refresh_imported_step_overlay` tears the old overlay down via
`_remove_step_overlay_actors`, which removed each actor with the **main-only**
`_remove_renderer_view_prop`. The gizmo handles therefore orphaned in the overlay
renderer -- still visible, but with their pick-map entries cleared -- so a rotated
STEP grew a dead "ghost gizmo": you could rotate it once, then no longer select a
handle ("I can only rotate once, then no longer can select the gizmo").

Fix: `_remove_step_overlay_actors` removes each actor via
`_remove_actor_from_renderers` (main + gizmo overlay). And `_remove_actor_registration`
pops `_actor_step_translate_map` alongside `_actor_step_rotate_map`.

This guard is display-free: it drives the real
`Open3DStepOverlayRefreshService._remove_step_overlay_actors` against a fake
inspector whose two renderers record which actors they had removed, so no VTK /
embedded window is needed.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_overlay_removes_gizmo_from_overlay

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


class _FakeRenderer:
    """Records actor membership; mirrors the VTK renderer surface the removal
    helpers touch (RemoveActor / RemoveViewProp / AddActor / AddViewProp)."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.actors: set[int] = set()

    def AddActor(self, actor) -> None:
        self.actors.add(id(actor))

    def AddViewProp(self, actor) -> None:
        self.actors.add(id(actor))

    def RemoveActor(self, actor) -> None:
        self.actors.discard(id(actor))

    def RemoveViewProp(self, actor) -> None:
        self.actors.discard(id(actor))


class _FakeActor:
    def __init__(self, key: str) -> None:
        self.key = key


class _FakeInspector:
    """Minimal inspector surface for _remove_step_overlay_actors /
    _remove_actor_registration, with the two removal helpers mirroring the real
    inspector: _remove_renderer_view_prop is main-only; _remove_actor_from_renderers
    clears both layers."""

    editor = object()

    def __init__(self) -> None:
        self._renderer = _FakeRenderer("main")
        self._gizmo_overlay_renderer = _FakeRenderer("overlay")
        for name in (
            "_actor_by_key",
            "_actor_row_map",
            "_actor_ray_map",
            "_actor_step_map",
            "_actor_step_follow_map",
            "_actor_step_rotate_map",
            "_actor_step_translate_map",
            "_actor_optical_axis_map",
            "_actor_placement_move_map",
            "_actor_placement_rotate_map",
            "_actor_thickness_dimension_map",
            "_row_actor_map",
            "_ray_actor_map",
            "_step_actor_map",
            "_step_follow_actor_map",
            "_optical_axis_actor_map",
            "_thickness_dimension_actor_map",
            "_step_feature_cache",
        ):
            setattr(self, name, {})
        self._actor_step_rotate_visual_keys: set[str] = set()
        self._picked_step_label = None
        self._hover_step_actor = None
        self._hover_rotation_handle_key = None
        self._selected_step_feature = None
        self._selected_step_feature_label = None
        self._selected_step_feature_center_world = None
        self._selected_step_feature_surface_center_world = None
        self._selected_step_feature_normal_world = None

    def _actor_key(self, actor):
        return getattr(actor, "key", None)

    def _set_step_hover_outline(self, *_args, **_kwargs):
        return None

    # Mirrors the real inspector: main renderer only.
    def _remove_renderer_view_prop(self, actor) -> None:
        if self._renderer is not None and actor is not None:
            self._renderer.RemoveViewProp(actor)

    # Mirrors the real inspector: main + gizmo overlay (bugs/0112 docstring).
    def _remove_actor_from_renderers(self, actor) -> None:
        if actor is None:
            return
        for renderer in (self._renderer, self._gizmo_overlay_renderer):
            if renderer is not None:
                renderer.RemoveActor(actor)


def _build_service_with_overlay_gizmo():
    from KrakenOS.UI.services.open3d_step_overlay_refresh import (
        Open3DStepOverlayRefreshService,
    )

    inspector = _FakeInspector()
    service = Open3DStepOverlayRefreshService(inspector)

    # A rotation arrowhead handle + a translate arrow handle for the LED. Both
    # live ONLY in the gizmo overlay renderer (overlay_on_top=True), and both are
    # followed by the 'led' label (so the teardown collects them).
    rotate = _FakeActor("rotate_led_x")
    translate = _FakeActor("translate_led_y")
    inspector._actor_by_key[rotate.key] = rotate
    inspector._actor_by_key[translate.key] = translate
    inspector._actor_step_rotate_map[rotate.key] = ("led", "x", 5.0)
    inspector._actor_step_translate_map[translate.key] = ("led", "y", 0.5)
    inspector._actor_step_follow_map[rotate.key] = "led"
    inspector._actor_step_follow_map[translate.key] = "led"
    inspector._step_follow_actor_map["led"] = [rotate.key, translate.key]
    inspector._gizmo_overlay_renderer.AddActor(rotate)
    inspector._gizmo_overlay_renderer.AddActor(translate)
    return service, inspector, rotate, translate


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    from KrakenOS.UI.services.open3d_step_overlay_refresh import (
        Open3DStepOverlayRefreshService,
    )

    # A + B. Behavioural: the teardown must clear the gizmo handles from the
    #        OVERLAY renderer and from their pick-maps.
    try:
        service, fake, rotate, translate = _build_service_with_overlay_gizmo()
        service._remove_step_overlay_actors("led")
    except Exception as exc:
        notes.append(f"FAIL: _remove_step_overlay_actors raised: {exc!r}")
        return False, notes

    if id(rotate) in fake._gizmo_overlay_renderer.actors:
        notes.append(
            "FAIL: the rotation handle was left in the gizmo overlay renderer (orphaned "
            "ghost gizmo) -- teardown only cleared the main renderer"
        )
        passed = False
    if id(translate) in fake._gizmo_overlay_renderer.actors:
        notes.append(
            "FAIL: the translate handle was left in the gizmo overlay renderer (orphaned "
            "ghost gizmo)"
        )
        passed = False
    if fake._actor_step_rotate_map:
        notes.append(
            f"FAIL: _actor_step_rotate_map still holds {fake._actor_step_rotate_map!r} "
            f"after teardown (rotation_handle_count would not clear)"
        )
        passed = False
    if fake._actor_step_translate_map:
        notes.append(
            f"FAIL: _actor_step_translate_map still holds {fake._actor_step_translate_map!r} "
            f"after teardown (sibling pop missing in _remove_actor_registration)"
        )
        passed = False

    # C. Source contract: the removal loop calls the both-renderer helper.
    try:
        src = inspect.getsource(Open3DStepOverlayRefreshService._remove_step_overlay_actors)
    except Exception as exc:
        notes.append(f"FAIL: cannot read _remove_step_overlay_actors source: {exc!r}")
        return False, notes
    if "_remove_actor_from_renderers(actor)" not in src:
        notes.append(
            "FAIL: _remove_step_overlay_actors does not call _remove_actor_from_renderers(actor) "
            "-- a main-only removal re-orphans gizmo handles in the overlay renderer"
        )
        passed = False

    # D. Source contract: the registration teardown pops the translate map.
    try:
        reg_src = inspect.getsource(Open3DStepOverlayRefreshService._remove_actor_registration)
    except Exception as exc:
        reg_src = ""
        notes.append(f"FAIL: cannot read _remove_actor_registration source: {exc!r}")
        passed = False
    if reg_src and "_actor_step_translate_map.pop(actor_key" not in reg_src:
        notes.append(
            "FAIL: _remove_actor_registration does not pop _actor_step_translate_map "
            "(sibling of the _actor_step_rotate_map pop)"
        )
        passed = False

    if verbose:
        notes.append(
            "checked: _remove_step_overlay_actors clears both gizmo handles from the overlay "
            "renderer and their pick-maps; source calls _remove_actor_from_renderers; "
            "_remove_actor_registration pops the translate map"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] bugs/0118: partial STEP refresh clears gizmo handles from the overlay renderer")
        return 0
    print("[FAIL] bugs/0118 overlay-orphan gizmo guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
