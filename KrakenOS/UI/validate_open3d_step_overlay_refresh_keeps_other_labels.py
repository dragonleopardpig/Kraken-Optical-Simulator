"""Display-free guard: a single-label STEP-overlay refresh must NOT tear down
another overlay label's actors (bug 0144).

Actor keys are VTK addresses (``actor.GetAddressAsString``), and VTK recycles a
freed actor's address for the next actor it allocates. The reverse maps
(``_actor_step_follow_map`` etc., keyed by address) are dicts that
``_add_mesh_actor`` OVERWRITES on every registration, so they always name the
LIVE owner. But the forward per-label lists (``_step_follow_actor_map[label]``)
are only pruned by ``_remove_actor_registration``; a teardown that frees an actor
by another path leaves its address lingering in the forward list. When VTK then
recycles that address for a DIFFERENT overlay label's body, the stale forward
entry now names a live foreign actor.

``_remove_step_overlay_actors("optical")`` collected its removal set partly from
that forward list, so it swept up the recycled address and tore down the live
*lens* body -- the imaging-lens STEP overlay "suddenly lost its face" for minutes
(until the next full scene refresh rebuilt every overlay).

The fix filters the removal set through ``_step_overlay_actor_owner_label``: an
actor is only torn down when its LIVE owner (per the always-fresh reverse maps)
is this label, or unclaimed. A key now owned by another label -- the recycled
collision -- is skipped.

This guard, with no rendering, pins:

  1. COLLISION -- optical's forward list holds a recycled address that the
     reverse maps say belongs to the live lens body. Refreshing "optical" removes
     the genuine optical actor but LEAVES the lens body registered + on-screen.
  2. SYMMETRY -- the same collision the other way (a recycled optical address in
     the lens forward list) is protected when refreshing "lens".
  3. NO-COLLISION baseline -- with no stale entry, refreshing "optical" still
     removes exactly optical and leaves lens untouched (removal not over-narrowed).
  4. Source wiring -- the owner-label resolver exists and the removal set is
     filtered through it.

Penta phase 133 (baseline -> 133).
"""

from __future__ import annotations

from pathlib import Path

from KrakenOS.UI.services.open3d_step_overlay_refresh import (
    Open3DStepOverlayRefreshService,
)


class _FakeActor:
    def __init__(self, key: str) -> None:
        self.key = key


class _FakeInspector:
    """Carries only the leaf state the real removal code reads/writes."""

    def __init__(self) -> None:
        self.editor = object()
        self._renderer = object()  # truthy, never called directly
        # forward per-label lists (the ones that can hold a stale address)
        self._step_actor_map: dict = {}
        self._step_follow_actor_map: dict = {}
        self._row_actor_map: dict = {}
        self._ray_actor_map: dict = {}
        self._optical_axis_actor_map: dict = {}
        self._thickness_dimension_actor_map: dict = {}
        # reverse maps (keyed by address -- always fresh / live owner)
        self._actor_by_key: dict = {}
        self._actor_row_map: dict = {}
        self._actor_ray_map: dict = {}
        self._actor_step_map: dict = {}
        self._actor_step_follow_map: dict = {}
        self._actor_step_rotate_map: dict = {}
        self._actor_step_translate_map: dict = {}
        self._actor_optical_axis_map: dict = {}
        self._actor_placement_move_map: dict = {}
        self._actor_placement_rotate_map: dict = {}
        self._actor_thickness_dimension_map: dict = {}
        self._actor_step_rotate_visual_keys: set = set()
        # scalar state touched on teardown
        self._picked_step_label = None
        self._hover_step_actor = None
        self._hover_rotation_handle_key = None
        self._selected_step_feature = None
        self._selected_step_feature_label = None
        self._selected_step_feature_center_world = None
        self._selected_step_feature_surface_center_world = None
        self._selected_step_feature_normal_world = None
        self._step_feature_cache: dict = {}
        # witness
        self.removed_from_renderers: list = []

    # --- stubbed inspector methods the removal path calls -------------------
    def _actor_key(self, actor) -> str | None:
        return None if actor is None else actor.key

    def _remove_actor_from_renderers(self, actor) -> None:
        self.removed_from_renderers.append(actor)

    def _set_step_hover_outline(self, *_args, **_kwargs) -> None:
        return None

    # --- test scaffolding ---------------------------------------------------
    def register_body(self, label: str, key: str) -> _FakeActor:
        """Mimic ``_add_mesh_actor`` for a pick+follow STEP body."""
        actor = _FakeActor(key)
        self._actor_by_key[key] = actor
        self._actor_step_map[key] = label
        self._step_actor_map.setdefault(label, []).append(key)
        self._actor_step_follow_map[key] = label
        self._step_follow_actor_map.setdefault(label, []).append(key)
        return actor


def _seed_two_overlays() -> tuple[_FakeInspector, _FakeActor, _FakeActor]:
    insp = _FakeInspector()
    lens_actor = insp.register_body("lens", "0xLENS")
    opt_actor = insp.register_body("optical", "0xOPT")
    return insp, lens_actor, opt_actor


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    def record(name: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and bool(passed)
        status = "PASS" if passed else "FAIL"
        notes.append(f"{name} | {status}" + (f" | {detail}" if detail else ""))

    # 1) COLLISION: recycled lens address stale in optical's forward list -----
    insp, lens_actor, opt_actor = _seed_two_overlays()
    # the leak: VTK recycled "0xLENS" for the new lens body, but a freed optical
    # actor left "0xLENS" behind in optical's forward follow list.
    insp._step_follow_actor_map["optical"].append("0xLENS")
    svc = Open3DStepOverlayRefreshService(insp)
    svc._remove_step_overlay_actors("optical")
    lens_survives = (
        "0xLENS" in insp._actor_by_key
        and insp._step_actor_map.get("lens") == ["0xLENS"]
        and insp._step_follow_actor_map.get("lens") == ["0xLENS"]
        and lens_actor not in insp.removed_from_renderers
    )
    record(
        "optical refresh keeps the recycled-address lens body",
        lens_survives,
        f"in_by_key={'0xLENS' in insp._actor_by_key} "
        f"step_map_lens={insp._step_actor_map.get('lens')} "
        f"renderer_removed_lens={lens_actor in insp.removed_from_renderers}",
    )
    optical_gone = (
        "0xOPT" not in insp._actor_by_key
        and "optical" not in insp._step_actor_map
        and opt_actor in insp.removed_from_renderers
    )
    record(
        "optical refresh still removes the genuine optical body",
        optical_gone,
        f"in_by_key={'0xOPT' in insp._actor_by_key} "
        f"renderer_removed_opt={opt_actor in insp.removed_from_renderers}",
    )

    # 2) SYMMETRY: recycled optical address stale in lens's forward list ------
    insp2, lens_actor2, opt_actor2 = _seed_two_overlays()
    insp2._step_follow_actor_map["lens"].append("0xOPT")
    svc2 = Open3DStepOverlayRefreshService(insp2)
    svc2._remove_step_overlay_actors("lens")
    optical_survives = (
        "0xOPT" in insp2._actor_by_key
        and insp2._step_actor_map.get("optical") == ["0xOPT"]
        and opt_actor2 not in insp2.removed_from_renderers
    )
    record(
        "lens refresh keeps the recycled-address optical body (symmetry)",
        optical_survives,
        f"in_by_key={'0xOPT' in insp2._actor_by_key} "
        f"renderer_removed_opt={opt_actor2 in insp2.removed_from_renderers}",
    )

    # 3) NO-COLLISION baseline: removal stays label-scoped, not over-narrowed -
    insp3, lens_actor3, opt_actor3 = _seed_two_overlays()
    svc3 = Open3DStepOverlayRefreshService(insp3)
    svc3._remove_step_overlay_actors("optical")
    clean_scope = (
        "0xOPT" not in insp3._actor_by_key
        and opt_actor3 in insp3.removed_from_renderers
        and "0xLENS" in insp3._actor_by_key
        and insp3._step_actor_map.get("lens") == ["0xLENS"]
        and lens_actor3 not in insp3.removed_from_renderers
    )
    record(
        "no-collision refresh removes only optical, keeps lens",
        clean_scope,
        f"opt_removed={opt_actor3 in insp3.removed_from_renderers} "
        f"lens_kept={'0xLENS' in insp3._actor_by_key}",
    )

    # 4) source wiring -------------------------------------------------------
    src = Path(__file__).resolve().parent / "services" / "open3d_step_overlay_refresh.py"
    text = src.read_text()
    has_resolver = "def _step_overlay_actor_owner_label" in text
    has_filter = "self._step_overlay_actor_owner_label(actor_key) in (None, label)" in text
    record(
        "removal set is filtered through the live-owner resolver",
        has_resolver and has_filter,
        f"resolver={has_resolver} filter={has_filter}",
    )

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for note in notes:
        print(note)
    print(
        "[PASS] single-label STEP-overlay refresh leaves other labels' actors intact (bug 0144)"
        if ok
        else "[FAIL] STEP-overlay refresh cross-label actor-drop guard regressed"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
