"""Validate selected-ray face/action labels for 2-D and 3-D diagnostics."""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.layout_plot_controller import (
    projected_ray_event_label_items,
    projected_ray_events_for_segment,
    ray_event_display_label,
)
from KrakenOS.UI.scene_geometry import ProjectedRay2D, ProjectedRayEvent2D


class Event:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)


def main() -> None:
    reflect = Event(event_kind="surface", event_type="reflection", surface_id=5, mesh_face_id="F003")
    transmit = Event(event_kind="surface", event_type="refraction", surface_id=6, mesh_face_id="F006")
    terminal = ProjectedRayEvent2D(
        event_kind="terminal",
        event_type="",
        surface_id=7,
        mesh_face_id="F007",
        point_index=2,
        point_2d=np.asarray([2.0, 1.0]),
        terminal_status="missed_detector",
    )
    assert ray_event_display_label(reflect) == "F003 Reflect"
    assert ray_event_display_label(transmit) == "F006 Transmit"
    assert ray_event_display_label(terminal) == "F007 Miss"

    ray = ProjectedRay2D(
        ray_index=3,
        points_2d=np.asarray([[0.0, 0.0], [1.0, 0.0], [2.0, 1.0]], dtype=float),
        events_2d=[
            ProjectedRayEvent2D(
                event_kind="surface",
                event_type="reflection",
                surface_id=5,
                mesh_face_id="F003",
                point_index=1,
                point_2d=np.asarray([1.0, 0.0]),
            ),
            terminal,
        ],
    )
    labels = [label for label, _point, _kind in projected_ray_event_label_items(ray)]
    assert labels == ["F003 Reflect", "F007 Miss"]

    copied = projected_ray_events_for_segment(
        ray,
        1,
        2,
        np.asarray([[10.0, 0.0], [20.0, 2.0]], dtype=float),
    )
    assert [event.mesh_face_id for event in copied] == ["F003", "F007"]
    assert [ray_event_display_label(event) for event in copied] == ["F003 Reflect", "F007 Miss"]
    print("selected ray event labels: ok")


if __name__ == "__main__":
    main()
