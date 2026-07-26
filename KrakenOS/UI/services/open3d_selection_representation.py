"""View-side projection for selection highlights.

Counterpart to Slicer's ``vtkMRMLAbstractWidgetRepresentation``: owns the
actor-styling that visualizes a ``SelectionModel`` change. The
``Kraken3DInspector`` keeps thin facade methods (``_set_*_highlight``)
that delegate here, so future widget-based selection rendering can plug
in without touching every call site.

The representation is intentionally inspector-bound (it proxies attribute
access via ``__getattr__`` / ``__setattr__``) so it can read the live
actor maps (``_actor_ray_map``, ``_actor_optical_axis_map``, ...) and
write back the picked-state fields through the SelectionModel-backed
``@property`` shims that already exist on the inspector.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class SelectionRepresentation:
    """Apply selection state to the current renderer's actors."""

    def __init__(self, inspector: Any) -> None:
        object.__setattr__(self, "_inspector", inspector)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inspector, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_inspector":
            object.__setattr__(self, name, value)
            return
        setattr(self._inspector, name, value)

    # ------------------------------------------------------------------
    # row highlight

    def apply_row_selection(self, row_indices, *, force: bool = False) -> None:
        selected_rows: set[int] = set()
        for row_index in list(row_indices or []):
            try:
                selected_rows.add(int(row_index))
            except Exception:
                continue
        picked = min(selected_rows) if selected_rows else None
        current_plural = set(getattr(self, "_picked_row_indices", set()) or set())
        current_singular = getattr(self, "_picked_row_index", None)
        # Early-return only when BOTH the plural and singular state
        # already match. The two fields can desync (anything that
        # mutates ``_picked_row_index`` without updating
        # ``_picked_row_indices`` would otherwise wedge the clear path
        # into thinking the work is done). Caught by the comprehensive
        # harness's Phase 4: a direct ``_picked_row_index = N``
        # assignment was leaving the clear path as a no-op.
        # bugs/0438: ``force`` bypasses the early-return -- after a scene rebuild the
        # MODEL still matches but every rebuilt actor is unstyled, so the matching
        # state is exactly the case that must re-style.
        plural_matches = selected_rows == current_plural
        singular_matches = current_singular == picked
        if plural_matches and singular_matches and not force:
            return
        if self._renderer is None:
            self._picked_row_index = picked
            self._picked_row_indices = set(selected_rows)
            return
        collection = self._renderer.GetActors()
        collection.InitTraversal()
        for _ in range(collection.GetNumberOfItems()):
            actor = collection.GetNextActor()
            key = self._actor_key(actor)
            if key is not None and key in self._actor_step_map:
                continue
            actor_row_index = self._actor_row_map.get(key) if key is not None else None
            try:
                actor_row_index = int(actor_row_index)
            except Exception:
                actor_row_index = None
            self._inspector._set_row_actor_selected(
                actor, bool(actor_row_index is not None and actor_row_index in selected_rows)
            )
        self._picked_row_index = picked
        self._picked_row_indices = set(selected_rows)

    # ------------------------------------------------------------------
    # ray highlight

    def apply_ray_selection(self, ray_index: int | None) -> None:
        if ray_index == self._picked_ray_index and self._ray_event_label_actors:
            return
        if self._renderer is None:
            self._picked_ray_index = ray_index
            return
        self._inspector._clear_ray_event_label_actors(render=False)
        # bugs/0223 (Fix B): rays are now MERGED per-style actors (a few instead of one
        # per ray), so an individual ray can't be recoloured in place -- draw the selected
        # ray as a bright OVERLAY actor instead.
        self._inspector._apply_ray_highlight_overlay(ray_index)
        self._inspector._add_selected_ray_event_label_actors(ray_index)
        self._picked_ray_index = ray_index

    # ------------------------------------------------------------------
    # step highlight

    def apply_step_selection(self, step_label: str | None, *, render: bool = True) -> None:
        if step_label == self._picked_step_label:
            return
        if self._renderer is None:
            self._picked_step_label = step_label
            return
        collection = self._renderer.GetActors()
        collection.InitTraversal()
        for _ in range(collection.GetNumberOfItems()):
            actor = collection.GetNextActor()
            actor_key = self._actor_key(actor)
            actor_step = self._actor_step_map.get(actor_key) if actor_key is not None else None
            if actor_step is None:
                continue
            self._inspector._set_step_actor_selected(
                actor, bool(step_label is not None and actor_step == step_label)
            )
        self._picked_step_label = step_label
        if render:
            self._inspector.render()

    def apply_step_selection_set(self, labels, *, render: bool = True) -> None:
        label_set = {
            str(label).strip().lower()
            for label in (labels or [])
            if str(label).strip()
        }
        primary = self._picked_step_label if self._picked_step_label in label_set else None
        if primary is None and label_set:
            primary = sorted(label_set)[0]
        if self._renderer is None:
            self._picked_step_label = primary
            return
        collection = self._renderer.GetActors()
        collection.InitTraversal()
        for _ in range(collection.GetNumberOfItems()):
            actor = collection.GetNextActor()
            actor_key = self._actor_key(actor)
            actor_step = self._actor_step_map.get(actor_key) if actor_key is not None else None
            if actor_step is None:
                continue
            self._inspector._set_step_actor_selected(actor, bool(actor_step in label_set))
        self._picked_step_label = primary
        if render:
            self._inspector.render()

    # ------------------------------------------------------------------
    # optical-axis highlight

    def apply_optical_axis_selection(self, axis_id: str | None) -> None:
        from KrakenOS.UI.open3d_inspector import pv  # late binding; pv may be None on import

        axis_id = str(axis_id or "").strip() or None
        if axis_id == self._picked_optical_axis_id and (
            axis_id is None or self._optical_axis_highlight_actor is not None
        ):
            return
        if self._renderer is None:
            self._picked_optical_axis_id = axis_id
            return
        self._inspector._remove_optical_axis_highlight_actor()
        selected_points = None
        collection = self._renderer.GetActors()
        collection.InitTraversal()
        for _ in range(collection.GetNumberOfItems()):
            actor = collection.GetNextActor()
            actor_key = self._actor_key(actor)
            axis_info = self._actor_optical_axis_map.get(actor_key) if actor_key is not None else None
            if not axis_info:
                continue
            current_id = str(axis_info.get("axis_id", "") or "").strip()
            prop = actor.GetProperty()
            if prop is None:
                continue
            if axis_id is not None and current_id == axis_id:
                prop.SetColor(1.0, 0.68, 0.05)
                prop.SetOpacity(1.0)
                prop.SetLineWidth(4.0)
                try:
                    selected_points = np.asarray(axis_info.get("points"), dtype=float)
                except Exception:
                    selected_points = None
            else:
                prop.SetColor(0.0, 0.43, 0.88)
                prop.SetOpacity(0.82)
                prop.SetLineWidth(3.0 if self._inspector._optical_axis_pick_mode_active() else 2.0)
        if axis_id is not None and (selected_points is None or selected_points.ndim != 2):
            for record in list(self._optical_axis_pick_records):
                if str(record.get("axis_id", "") or "").strip() != axis_id:
                    continue
                try:
                    selected_points = np.asarray(record.get("points"), dtype=float)
                except Exception:
                    selected_points = None
                break
        if (
            axis_id is not None
            and selected_points is not None
            and selected_points.ndim == 2
            and selected_points.shape[0] >= 2
            and selected_points.shape[1] >= 3
            and np.all(np.isfinite(selected_points[:, :3]))
            and pv is not None
        ):
            try:
                mesh = pv.lines_from_points(selected_points[:, :3])
                actor = self._inspector._add_mesh_actor(
                    mesh,
                    color=(1.0, 0.68, 0.05),
                    opacity=1.0,
                    line_width=7.0,
                    flat_shading=True,
                    backface_culling=False,
                )
                if actor is not None:
                    actor.PickableOff()
                    self._optical_axis_highlight_actor = actor
            except Exception as exc:
                self.editor.append_debug(f"3D optical-axis solid highlight failed: {exc}")
        self._picked_optical_axis_id = axis_id
