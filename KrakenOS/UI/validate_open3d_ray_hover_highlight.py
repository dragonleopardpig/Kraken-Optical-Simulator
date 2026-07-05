"""Display-free guard for bugs/0225 -- in Pick-rays mode, HOVERING a traced ray must
highlight it (flag_20260705_100834: "Checked the 'Pick rays' box, mouse hover does not show
highlight of ray. Clicked on each ray, ray info window pop up." -- clicking worked, hover
gave no feedback; the hover handler had never highlighted traced rays).

The feature: the ``hover_default`` branch of ``_on_mouse_move`` resolves the hovered ray
from the picked merged actor via the live picker cell (``_ray_index_for_actor``, bugs/0223
Fix B) when ``_ray_pick_enabled()`` is on, and draws a LIGHT overlay
(``_apply_ray_hover_overlay``) -- thinner/paler than, tracked separately from, and never
disturbing the click-selection highlight (a hovered ray that IS the selection keeps only
the selection overlay).

  (A) OVERLAY LIFECYCLE (unit, real method on a stub renderer): hovering ray A adds ONE
      overlay actor; re-hovering A is a no-op (returns False -- no re-render churn);
      switching to ray B replaces it (still one actor); None clears it.
  (B) SEPARATE from the selection overlay: distinct state keys, and applying the hover
      overlay never touches the selection overlay's actor.
  (C) SCENE REBUILD clears it: ``_clear_merged_ray_state`` drops the hover overlay.
  (D) WIRED: the hover branch gates on ``_ray_pick_enabled()``, resolves via
      ``_ray_index_for_actor(actor_key)``, skips the selected ray, and renders only on
      change.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ray_hover_highlight
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_INTERACTION_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "open3d_interaction.py"
_INSPECTOR_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "open3d_inspector.py"


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _stub_inspector():
    import KrakenOS.UI.open3d_inspector as OI

    OI._load_3d_backends()
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as I

    class _Renderer:
        def __init__(self):
            self.actors = []

        def AddActor(self, actor):
            self.actors.append(actor)

    class _Stub:
        pass

    stub = _Stub()
    stub._renderer = _Renderer()
    stub._actor_by_key = {}
    stub._removed = []
    stub._actor_key = lambda actor: (stub._actor_by_key.__setitem__(f"k{id(actor)}", actor) or f"k{id(actor)}")
    stub._remove_renderer_view_prop = lambda actor: (
        stub._removed.append(actor),
        stub._renderer.actors.remove(actor) if actor in stub._renderer.actors else None,
    )

    def _add_mesh_actor(mesh, **kwargs):
        actor = OI.vtkActor()
        try:
            from vtkmodules.vtkRenderingCore import vtkPolyDataMapper

            mapper = vtkPolyDataMapper()
            mapper.SetInputData(mesh)
            actor.SetMapper(mapper)
        except Exception:
            pass
        stub._renderer.AddActor(actor)
        stub._actor_key(actor)
        return actor

    stub._add_mesh_actor = _add_mesh_actor
    stub._ray_display_points = {
        5: np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 1.0]]),
        7: np.asarray([[0.0, 1.0, 0.0], [1.0, 1.0, 0.0]]),
    }
    stub._ray_highlight_overlay_key = None
    stub._ray_hover_overlay_key = None
    stub._ray_hover_overlay_index = None
    stub._pending_ray_specs = []
    stub._merged_ray_cell_index = {}
    for name in (
        "_apply_ray_hover_overlay",
        "_apply_ray_highlight_overlay",
        "_clear_merged_ray_state",
    ):
        setattr(stub, name, getattr(I, name).__get__(stub))
    return stub


def validate_ray_hover_highlight() -> list[Check]:
    checks: list[Check] = []
    stub = _stub_inspector()

    # ============ (A) overlay lifecycle ========================================== #
    changed_a = stub._apply_ray_hover_overlay(5)
    count_after_a = len(stub._renderer.actors)
    changed_same = stub._apply_ray_hover_overlay(5)
    changed_b = stub._apply_ray_hover_overlay(7)
    count_after_b = len(stub._renderer.actors)
    changed_clear = stub._apply_ray_hover_overlay(None)
    count_after_clear = len(stub._renderer.actors)
    checks.append(Check(
        "hover overlay lifecycle: add -> no-op on same ray -> replace -> clear",
        bool(
            changed_a is True
            and count_after_a == 1
            and changed_same is False
            and changed_b is True
            and count_after_b == 1
            and changed_clear is True
            and count_after_clear == 0
            and stub._ray_hover_overlay_index is None
        ),
        f"add={changed_a}/{count_after_a} same={changed_same} replace={changed_b}/{count_after_b} "
        f"clear={changed_clear}/{count_after_clear}",
    ))

    # ============ (B) separate from the selection overlay ======================== #
    stub2 = _stub_inspector()
    stub2._apply_ray_highlight_overlay(5)  # the click-selection overlay
    selection_key = stub2._ray_highlight_overlay_key
    stub2._apply_ray_hover_overlay(7)
    hover_key = stub2._ray_hover_overlay_key
    stub2._apply_ray_hover_overlay(None)
    checks.append(Check(
        "the hover overlay is tracked separately and never disturbs the selection overlay",
        bool(
            selection_key is not None
            and hover_key is not None
            and hover_key != selection_key
            and stub2._ray_highlight_overlay_key == selection_key
            and len(stub2._renderer.actors) == 1  # the selection overlay survives the hover clear
        ),
        f"selection_key={selection_key!r} hover_key={hover_key!r} "
        f"actors_after_hover_clear={len(stub2._renderer.actors)}",
    ))

    # ============ (C) scene rebuild clears the hover overlay ===================== #
    stub3 = _stub_inspector()
    stub3._apply_ray_hover_overlay(5)
    stub3._clear_merged_ray_state()
    checks.append(Check(
        "_clear_merged_ray_state drops the hover overlay (scene rebuild)",
        bool(stub3._ray_hover_overlay_index is None and len(stub3._renderer.actors) == 0),
        f"index={stub3._ray_hover_overlay_index} actors={len(stub3._renderer.actors)}",
    ))

    # ============ (E) the passive pick-list ray pick (rev 2) ===================== #
    # flag_20260705_131522: the first cut lived after the hover_default pick, which only
    # runs during STEP-placement flows -- plain idle hovering never highlighted. Rev 2
    # resolves the ray in the PASSIVE hover path via a pick-list-restricted pick over the
    # merged ray actors; unit-test the pick + resolve + picker-state restore with a fake
    # cell picker.
    import KrakenOS.UI.open3d_inspector as OI
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as I

    stub4 = _stub_inspector()

    class _FakePicker:
        def __init__(self, actor, cell_id):
            self._actor = actor
            self._cell = int(cell_id)
            self.list_on = False
            self.list_cleared = 0
            self.added = []
            self.total_added = []  # cumulative -- InitializePickList resets `added` only

        def InitializePickList(self):
            self.list_cleared += 1
            self.added = []

        def AddPickList(self, actor):
            self.added.append(actor)
            self.total_added.append(actor)

        def PickFromListOn(self):
            self.list_on = True

        def PickFromListOff(self):
            self.list_on = False

        def Pick(self, x, y, z, renderer):
            return 1

        def GetActor(self):
            return self._actor

        def GetCellId(self):
            return self._cell

    merged_actor = OI.vtkActor()
    merged_key = stub4._actor_key(merged_actor)
    stub4._merged_ray_cell_index = {merged_key: np.asarray([4, 4, 9, 9], dtype=np.int64)}
    stub4._actor_ray_map = {merged_key: -1}
    stub4._picker = _FakePicker(merged_actor, cell_id=2)
    stub4._ray_index_for_actor = I._ray_index_for_actor.__get__(stub4)
    stub4._passive_hover_pick_ray = I._passive_hover_pick_ray.__get__(stub4)
    hovered = stub4._passive_hover_pick_ray(10, 20)
    checks.append(Check(
        "the passive pick-list ray pick resolves the hovered merged-actor ray and restores the picker",
        bool(
            hovered == 9  # cell 2 -> ray 9
            and stub4._picker.list_on is False  # PickFromListOff restored
            and stub4._picker.list_cleared >= 2  # list cleared going in AND in the finally
            and stub4._picker.total_added == [merged_actor]
        ),
        f"hovered={hovered} (expect 9) list_on={stub4._picker.list_on} "
        f"cleared={stub4._picker.list_cleared} added={len(stub4._picker.total_added)}",
    ))

    # ============ (D) wired ====================================================== #
    try:
        interaction_src = _INTERACTION_SRC.read_text(encoding="utf-8")
        inspector_src = _INSPECTOR_SRC.read_text(encoding="utf-8")
    except Exception:
        interaction_src = inspector_src = ""
    passive_block = ""
    marker = "if target_label is None and not axis_pick_any:"
    if marker in interaction_src:
        start = interaction_src.index(marker)
        passive_block = interaction_src[start : start + 12000]
    wired = (
        "hovered_ray = self._passive_hover_pick_ray(x, y)" in passive_block
        and "if self._ray_pick_enabled():" in passive_block
        and "hovered_ray == self._picked_ray_index" in passive_block
        and "hover_overlay_changed = self._apply_ray_hover_overlay(hovered_ray)" in passive_block
        and "def _passive_hover_pick_ray" in inspector_src
        and "def _apply_ray_hover_overlay" in inspector_src
        and "_apply_ray_hover_overlay(None)  # bugs/0225" in inspector_src
        # the unreachable first-cut branch (in the placement-flow hover_default section)
        # must be GONE -- one code path only
        and "hovered_ray = self._ray_index_for_actor(actor_key)" not in interaction_src
    )
    checks.append(Check(
        "the hover lives in the PASSIVE (idle) hover path (mode gate, pick-list pick, selected-ray skip); the unreachable first cut is gone",
        wired,
        f"passive_pick={'hovered_ray = self._passive_hover_pick_ray(x, y)' in passive_block} "
        f"mode_gate={'if self._ray_pick_enabled():' in passive_block} "
        f"selected_skip={'hovered_ray == self._picked_ray_index' in passive_block} "
        f"old_branch_gone={'hovered_ray = self._ray_index_for_actor(actor_key)' not in interaction_src}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_ray_hover_highlight()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_ray_hover_highlight()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Ray-hover-highlight validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
