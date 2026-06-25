#!/usr/bin/env python3
"""Display-free guard for bugs/0152: a thickness dimension's view-relative offset SIDE
must be re-derived for the live camera on orbit, not stay baked at the pre-orbit side
until the next scene refresh.

Why it exists (flag_20260624_203423_975 "thickness overlays changed to opposite side" +
flag_20260624_203516_116 "thickness changed back to correct side after glue BS to LED"):
  The dimension offset side = `offset_direction(segment, view, screen_up)` is computed once
  at draw time (inside `add_overlays`). On orbit, `_on_camera_interaction` ->
  `_reorient_thickness_labels_for_camera` re-derived only the LABEL billboard ANGLE
  (bugs/0128); it never re-derived the SIDE. So after orbiting, the arrow + label stayed on
  the side that was correct for the PRE-orbit camera -- the "opposite side" -- until a full
  scene refresh (e.g. gluing the BS, which calls `_refresh_open_3d_views`) re-ran
  `add_overlays` and recomputed the side ("correct again after glue"). The fix registers each
  dimension's actors + un-offset anchors (`_register_view_relative_dimension`) and, on
  EndInteractionEvent, `_reposition_dimensions_for_camera` re-derives the side and cheaply
  re-places the arrow (AddPosition) + label (SetPosition) + rebuilds the two leaders.

What it checks (binds the REAL `_reposition_dimensions_for_camera` onto a fake inspector
whose actors/camera/renderer are stubs):
  A. Orbiting from the side view to a tilted view moves the arrow by exactly
     (new_offset - old_offset), where new_offset uses the live camera's side.
  B. The label is re-placed and the two leaders are rebuilt for the new side.
  C. Idempotent: repositioning again for the SAME camera is a no-op (no further AddPosition).
  D. No leak: after many orbits the group keeps exactly 2 leaders and the actor table does
     not grow (old leader keys are dropped before new ones are added).
  E. Source contract: `_on_camera_interaction` repositions on End; the scene refresh clears
     the group registry; `_emit_span_dimension` registers the group.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_dimension_side_orbit

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.layout_editor import Kraken3DInspector
from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService as TS


def _screen_up(view_normal, world_up=(0.0, 1.0, 0.0)):
    v = np.asarray(view_normal, float)
    v = v / np.linalg.norm(v)
    u = np.asarray(world_up, float)
    u = u - v * float(np.dot(u, v))
    return u / np.linalg.norm(u)


class _Actor:
    def __init__(self):
        self.position = np.zeros(3, dtype=float)
        self.sets = 0

    def AddPosition(self, x, y, z):
        self.position = self.position + np.array([x, y, z], dtype=float)

    def SetPosition(self, x, y, z):
        self.position = np.array([x, y, z], dtype=float)
        self.sets += 1


class _FakePv:
    @staticmethod
    def Line(a, b):
        return ("line", tuple(a), tuple(b))


class _FakeSvc:
    offset_direction = staticmethod(TS.offset_direction)
    pv = _FakePv()
    DIMENSION_LEADER_LINE_WIDTH = 2.0


class _FakeInspector:
    _reposition_dimensions_for_camera = Kraken3DInspector._reposition_dimensions_for_camera

    def __init__(self, view_normal):
        self._renderer = object()
        self._view = np.asarray(view_normal, float)
        self._up = _screen_up(view_normal)
        self._actor_by_key: dict = {}
        self._removed: list = []
        self._next_key = 0
        self._view_relative_dimension_groups: list[dict] = []

    def set_camera(self, view_normal):
        self._view = np.asarray(view_normal, float)
        self._up = _screen_up(view_normal)

    # camera stubs
    def _camera_screen_world_axes(self):
        right = np.cross(self._view / np.linalg.norm(self._view), self._up)
        return right, self._up

    def _camera_view_normal(self):
        return self._view / np.linalg.norm(self._view)

    def _open3d_thickness_dimension_service(self):
        return _FakeSvc()

    # actor-table stubs
    def _add_mesh_actor(self, mesh, **kw):
        actor = _Actor()
        key = f"leader-{self._next_key}"
        self._next_key += 1
        self._actor_by_key[key] = actor
        actor._key = key
        return actor

    def _remove_actor_from_renderers(self, actor):
        self._removed.append(actor)

    def _actor_key(self, actor):
        return getattr(actor, "_key", None)


def _make_group(insp, offset):
    base_lo = np.array([0.0, 0.0, 100.0])
    base_hi = np.array([0.0, 0.0, 150.0])  # segment along +Z (optical axis)
    arrow = _Actor()
    label = _Actor()
    leaders = [insp._add_mesh_actor(None), insp._add_mesh_actor(None)]
    group = {
        "arrow": arrow, "label": label, "leaders": leaders,
        "base_lo": base_lo, "base_hi": base_hi,
        "offset": np.asarray(offset, float), "label_extra": 5.0,
    }
    insp._view_relative_dimension_groups.append(group)
    return group


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    SIDE_VIEW = [1.0, 0.0, 0.0]
    TILTED = [0.647, -0.501, -0.574]
    seg = np.array([0.0, 0.0, 50.0])
    mag = 10.0

    # Build a dimension whose side was baked for the SIDE view, then orbit to TILTED.
    insp = _FakeInspector(SIDE_VIEW)
    side0 = TS.offset_direction(seg, view_normal=np.array(SIDE_VIEW), screen_up=_screen_up(SIDE_VIEW))
    group = _make_group(insp, side0 * mag)
    insp.set_camera(TILTED)

    changed = insp._reposition_dimensions_for_camera()
    new_side = TS.offset_direction(seg, view_normal=np.array(TILTED), screen_up=_screen_up(TILTED))
    expected_offset = new_side * mag
    expected_delta = expected_offset - side0 * mag

    # A) arrow moved by exactly (new_offset - old_offset)
    if not changed or not np.allclose(group["arrow"].position, expected_delta, atol=1e-6):
        failures.append(f"A FAIL: arrow must move by {expected_delta} (got {group['arrow'].position}, changed={changed})")
    if not np.allclose(group["offset"], expected_offset, atol=1e-6):
        failures.append(f"A FAIL: stored offset must update to {expected_offset} (got {group['offset']})")

    # B) label re-placed; leaders rebuilt (2 new, old 2 removed)
    if group["label"].sets != 1:
        failures.append(f"B FAIL: label must be re-positioned once (SetPosition calls={group['label'].sets})")
    if len(group["leaders"]) != 2 or len(insp._removed) != 2:
        failures.append(f"B FAIL: must rebuild 2 leaders (have {len(group['leaders'])}, removed {len(insp._removed)})")

    # C) idempotent: same camera again -> no further move
    arrow_pos_before = group["arrow"].position.copy()
    changed2 = insp._reposition_dimensions_for_camera()
    if changed2 or not np.allclose(group["arrow"].position, arrow_pos_before, atol=1e-9):
        failures.append(f"C FAIL: repositioning for the SAME camera must be a no-op (changed={changed2})")

    # D) no leak across many orbits: leaders stay at 2, actor table doesn't grow unbounded
    insp2 = _FakeInspector(SIDE_VIEW)
    g2 = _make_group(insp2, TS.offset_direction(seg, view_normal=np.array(SIDE_VIEW), screen_up=_screen_up(SIDE_VIEW)) * mag)
    for vn in ([0.3, -0.5, -0.8], [0.9, 0.1, -0.4], [0.2, -0.9, 0.3], SIDE_VIEW, TILTED) * 4:
        insp2.set_camera(vn)
        insp2._reposition_dimensions_for_camera()
    if len(g2["leaders"]) != 2:
        failures.append(f"D FAIL: a dimension must keep exactly 2 leaders after many orbits (got {len(g2['leaders'])})")
    # actor table holds at most the 2 live leaders (+ the 2 originals are popped as replaced)
    if len(insp2._actor_by_key) > 4:
        failures.append(f"D FAIL: leader actor table grew unbounded over orbits ({len(insp2._actor_by_key)} keys)")

    # E) source contracts
    handler = inspect.getsource(Kraken3DInspector._on_camera_interaction)
    if "_reposition_dimensions_for_camera" not in handler or '"End"' not in handler and "'End'" not in handler:
        failures.append("E FAIL: _on_camera_interaction must reposition dimensions on EndInteractionEvent")
    from KrakenOS.UI.services import open3d_scene_refresh as sr
    if "_view_relative_dimension_groups" not in inspect.getsource(sr):
        failures.append("E FAIL: the scene refresh must clear _view_relative_dimension_groups")
    if "_register_view_relative_dimension" not in inspect.getsource(TS._emit_span_dimension):
        failures.append("E FAIL: _emit_span_dimension must register the view-relative dimension group")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0152 thickness dimension side must re-derive for the live camera on orbit")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] thickness dimension offset side re-derives for the live camera on orbit (bugs/0152)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
