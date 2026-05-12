from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.auto_leg_graph import (
    auto_leg_point_key,
    build_auto_leg_entries_from_projected,
    leg_geometry_from_points,
)
from KrakenOS.UI.scene_geometry import ProjectedRay2D, ProjectedScene2D
from KrakenOS.UI.surface_table_model import SurfaceRow


@dataclass
class AutoLegGraphCheck:
    check: str
    ok: bool
    detail: str


def _check(check: str, condition: bool, detail: str) -> AutoLegGraphCheck:
    return AutoLegGraphCheck(check=check, ok=bool(condition), detail=str(detail))


def validate_auto_leg_graph() -> list[AutoLegGraphCheck]:
    rows = [
        SurfaceRow(surface="Object", name="Source"),
        SurfaceRow(surface="Beam Splitter", name="BS1"),
        SurfaceRow(surface="Mirror", name="Reflect Mirror"),
        SurfaceRow(surface="Image", name="Transmit Detector"),
    ]
    projected = ProjectedScene2D(
        rays=[
            ProjectedRay2D(
                ray_index=0,
                points_2d=np.asarray([[0.0, 0.0], [10.0, 0.0], [10.0, 20.0]], dtype=float),
                surface_ids=np.asarray([1, 2], dtype=int),
                branch_label="reflect",
                branch_path="R",
            ),
            ProjectedRay2D(
                ray_index=1,
                points_2d=np.asarray([[0.0, 0.0], [10.0, 0.0], [30.0, 0.0]], dtype=float),
                surface_ids=np.asarray([1, 3], dtype=int),
                branch_label="transmit",
                branch_path="T",
            ),
        ]
    )
    entries = build_auto_leg_entries_from_projected(projected, rows)
    labels = [str(entry.get("short_label", "")) for entry in entries]
    details = [str(entry.get("detail", "")) for entry in entries]
    context_sets = [set(entry.get("context_indices", set()) or set()) for entry in entries]
    surface_sets = [set(entry.get("surface_indices", set()) or set()) for entry in entries]
    geometry = [entry.get("segments") for entry in entries]
    return [
        _check(
            "stable point key quantizes projected coordinates",
            auto_leg_point_key(np.asarray([10.02, -0.01]), tolerance=0.25) == "40,0",
            f"key={auto_leg_point_key(np.asarray([10.02, -0.01]), tolerance=0.25)}",
        ),
        _check(
            "branch rays collapse shared source-to-splitter segment into one leg",
            len(entries) == 3 and labels == ["Path 1", "Path 2", "Path 3"],
            f"count={len(entries)}, labels={labels}",
        ),
        _check(
            "automatic leg details expose user-facing endpoints",
            any("Input to BS1" in detail for detail in details)
            and any("BS1 to Transmit Detector" in detail for detail in details)
            and any("BS1 to Reflect Mirror" in detail for detail in details),
            f"details={details}",
        ),
        _check(
            "context indices include graph endpoints while surface indices keep placed elements",
            {0, 1} in context_sets and {1, 2} in context_sets and {1, 3} in context_sets and {2} in surface_sets and {3} in surface_sets,
            f"context={context_sets}, surfaces={surface_sets}",
        ),
        _check(
            "automatic legs carry reusable geometry for label placement",
            all(isinstance(item, dict) and item.get("segments") for item in geometry),
            f"geometry_count={sum(1 for item in geometry if isinstance(item, dict) and item.get('segments'))}/{len(geometry)}",
        ),
        _check(
            "standalone leg geometry rejects degenerate paths",
            leg_geometry_from_points([np.asarray([1.0, 1.0]), np.asarray([1.0, 1.0])]) is None,
            "degenerate=None",
        ),
    ]


def main() -> int:
    checks = validate_auto_leg_graph()
    print("KrakenOS auto leg graph validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
