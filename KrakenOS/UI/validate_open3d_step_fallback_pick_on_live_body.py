#!/usr/bin/env python3
"""Display-free regression for bugs/0085: the camera-ray STEP face fallback pick
must land on the LIVE rendered body, not on stranded pose-baked metadata.

The fallback (`_step_feature_pick_any_for_display_xy`) deliberately fires even
when VTK reports no actor under the cursor, so a translucent prism's far/internal
faces stay selectable. It reads pose-baked face metadata, NOT the rendered actor.

The bug (flag_20260617_201859_454): a beam-splitter overlay is a live-trace
optical element. Toggling Show Rays folds it into the non-sequential trace, which
places it on the optical axis -- the DISPLAY snaps back to y=0 -- but the user's
manual drag offset stays in the face metadata. The fallback pick then resolves a
face at the off-axis metadata pose, lighting a gold "ghost" selection highlight
floating above the on-axis body (key `(None, 'passive', 'S001/F004')`).

The fix gates the fallback hit against the live rendered body's world bounds:
a hit clearly outside the drawn body is rejected (ghost), a hit on/inside the
body (incl. a translucent far face) is kept, and when no live body or hit point
can be resolved the pick is kept (coverage never silently lost).

This calls the real ``Kraken3DInspector`` guard helpers with a lightweight stub
self (no Xvfb, no VTK render) so it runs in any environment.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_fallback_pick_on_live_body

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import types
from types import SimpleNamespace


class _FakeActor:
    def __init__(self, bounds):
        self._bounds = tuple(float(v) for v in bounds)

    def GetBounds(self):
        return self._bounds


def _stub(step_actor_map, actor_by_key):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    stub = SimpleNamespace(_step_actor_map=step_actor_map, _actor_by_key=actor_by_key)
    stub._live_step_body_world_bounds = types.MethodType(
        Kraken3DInspector._live_step_body_world_bounds, stub
    )
    stub._step_fallback_hit_on_live_body = types.MethodType(
        Kraken3DInspector._step_fallback_hit_on_live_body, stub
    )
    return stub


def _through(point_world):
    # Mimics FaceRayPick: only ``point_world`` is read by the guard.
    return SimpleNamespace(point_world=tuple(float(v) for v in point_world))


# A 50 mm beam-splitter cube rendered ON the optical axis (the snapped-back pose).
ON_AXIS = (-25.0, 25.0, -25.0, 25.0, 144.26, 194.26)


def run_checks() -> tuple[bool, list[str]]:
    """Exercise the bugs/0085 live-body gate. Returns (passed, notes).

    Display-free: drives the real ``Kraken3DInspector`` guard helpers against a
    lightweight stub self, so it doubles as the penta-harness phase body.
    """
    failures: list[str] = []

    # 1) Live body bounds resolve from the rendered step actor.
    stub = _stub({"optical": ["k0"]}, {"k0": _FakeActor(ON_AXIS)})
    bounds = stub._live_step_body_world_bounds("optical")
    if bounds is None or abs(bounds[3] - 25.0) > 1e-6:
        failures.append(f"FAIL: live body bounds wrong: {bounds}")

    # 2) GHOST: metadata hit at the dragged-off pose (y=31.2), body on-axis -> reject.
    ghost_fp = {"through_pick": _through((0.0, 31.2, 166.0)), "surface_center": (0.0, 31.2, 166.0)}
    ghost_feature = ((0.0, 31.2, 166.0), object())
    if stub._step_fallback_hit_on_live_body("optical", ghost_fp, ghost_feature):
        failures.append("FAIL: ghost hit at y=31.2 above the on-axis body was NOT rejected")

    # 3) ON-BODY: hit on the rendered body face -> keep.
    on_fp = {"through_pick": _through((0.0, 0.0, 166.0)), "surface_center": (0.0, 0.0, 166.0)}
    on_feature = ((0.0, 0.0, 166.0), object())
    if not stub._step_fallback_hit_on_live_body("optical", on_fp, on_feature):
        failures.append("FAIL: legitimate hit on the on-axis body was rejected")

    # 3b) INTERNAL far face (translucent prism) just inside the body -> keep.
    far_fp = {"through_pick": _through((-24.0, 10.0, 150.0)), "surface_center": None}
    far_feature = ((-24.0, 10.0, 150.0), object())
    if not stub._step_fallback_hit_on_live_body("optical", far_fp, far_feature):
        failures.append("FAIL: translucent internal far-face hit inside the body was rejected")

    # 3c) Surface-edge hit exactly on the bound + the hover view-offset nudge -> keep.
    edge_fp = {"through_pick": _through((-25.001, 0.0, 166.0)), "surface_center": None}
    edge_feature = ((-25.001, 0.0, 166.0), object())
    if not stub._step_fallback_hit_on_live_body("optical", edge_fp, edge_feature):
        failures.append("FAIL: surface-edge hit on the body bound was rejected (margin too tight)")

    # 4) No live body drawn -> never reject (transparent-back-face coverage preserved).
    empty = _stub({}, {})
    if not empty._step_fallback_hit_on_live_body("optical", ghost_fp, ghost_feature):
        failures.append("FAIL: pick rejected with no live body -> coverage fallback broken")

    # 4b) Body genuinely off-axis (synced drag, Show Rays off): hit at y=31.2 with
    #     body ALSO at y=31.2 -> keep (only the desynced ghost must be rejected).
    off_axis = (-25.0, 25.0, 6.2, 56.2, 144.26, 194.26)
    synced = _stub({"optical": ["k1"]}, {"k1": _FakeActor(off_axis)})
    if not synced._step_fallback_hit_on_live_body("optical", ghost_fp, ghost_feature):
        failures.append("FAIL: synced off-axis drag (body+hit both at y=31.2) was wrongly rejected")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0085 fallback pick / live body gate")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] fallback STEP face pick stays on the live rendered body (bugs/0085)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
