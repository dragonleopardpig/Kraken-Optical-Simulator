"""Display-free contract for bugs/0009: the persistent thickness overlay must
not "skip" an imported optical lens and measure straight through to the next
analytic surface.

The live drag readout (``Kraken3DInspector._step_overlay_axial_gap``) already
treats the imported overlay as a physical body and reports the edge-to-edge gap
to the element before it -- the user confirmed that measurement is correct. The
persistent overlay (``Open3DThicknessDimensionService.add_overlays``) instead
walked analytic rows only, so an Object(z=0)->Image(z=100) chain with a lens at
z=44..55 painted one ``S0 Thickness = 100 mm`` arrow right across the lens
(flag ``flag_20260603_133340_743``).

The fix carves each row->row span at any overlay that sits between the two
surfaces (``split_span_at_overlays`` / ``_overlay_axial_spans_within``) and draws
a physical edge-gap dimension on each clear side instead. It also bumps the
shared dimension line thickness (``DIMENSION_TUBE_RADIUS_FACTOR`` /
``DIMENSION_LEADER_LINE_WIDTH``), which both the persistent overlay and the live
drag readout consume, so both distances read thicker. The rendered-pixel
guarantee lives in ``validate_open3d_thickness_overlay_skips_lens_snapshot`` and
Phase 16 of the comprehensive validator.

Run from the repository root:

    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_thickness_overlay_skips_lens
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.layout_editor import Kraken3DInspector
from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService


def _legacy_tube_radius(scene_span: float, length: float, factor: float, floor: float) -> float:
    head = min(max(float(scene_span) * 0.018, 0.75), max(length * 0.28, 0.75))
    radius = max(head * 0.20, 0.12)
    return max(radius * factor, floor)


class _FakeInspector:
    """Minimal inspector seam for the span/extent helpers."""

    def __init__(self, extents: dict[str, dict[str, float]]) -> None:
        self.editor = object()
        self._extents = extents
        self._step_actor_map = {label: [label] for label in extents}

    def _axial_extent_from_actor_keys(self, actor_keys, axis):
        keys = list(actor_keys or [])
        if not keys:
            return None
        extent = self._extents.get(keys[0])
        if extent is None:
            return None
        return {
            "axis": np.asarray(axis, dtype=float).reshape(3),
            "proj_min": float(extent["proj_min"]),
            "proj_max": float(extent["proj_max"]),
            "proj_center": float(extent.get("proj_center", 0.5 * (extent["proj_min"] + extent["proj_max"]))),
        }


def _near(a: float, b: float, tol: float = 1e-5) -> bool:
    return abs(float(a) - float(b)) <= tol


def _checks() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    split = Open3DThicknessDimensionService.split_span_at_overlays

    # 1. No overlay between the surfaces -> the original single row->row span.
    no_overlay = split(0.0, 100.0, [])
    checks.append(
        (
            "no overlay keeps a single row->row span",
            no_overlay == [(0.0, 100.0)],
            f"expected [(0.0, 100.0)], got {no_overlay!r}",
        )
    )

    # 2. The flag scene: a lens at z=44.12..55.70 between Object(0) and Image(100)
    #    must split into the two physical gaps, never one arrow across the lens.
    gaps = split(0.0, 100.0, [(44.12319, 55.70319)])
    ok_split = (
        len(gaps) == 2
        and _near(gaps[0][0], 0.0)
        and _near(gaps[0][1], 44.12319)
        and _near(gaps[1][0], 55.70319)
        and _near(gaps[1][1], 100.0)
    )
    checks.append(
        (
            "lens between surfaces splits into two physical gaps",
            ok_split,
            f"expected [(0,44.12319),(55.70319,100)], got {gaps!r}",
        )
    )
    # The near gap must equal the live readout's 'gap = 44.12 mm'.
    checks.append(
        (
            "near gap matches the live edge-gap readout (44.12 mm)",
            len(gaps) == 2 and _near(gaps[0][1] - gaps[0][0], 44.12319),
            f"near gap was {gaps[0][1] - gaps[0][0] if gaps else float('nan')!r}, expected 44.12319",
        )
    )

    # 3. An overlay covering the whole span must not erase the dimension.
    cover = split(0.0, 100.0, [(-5.0, 120.0)])
    checks.append(
        (
            "overlay covering the span falls back to the full span",
            cover == [(0.0, 100.0)],
            f"expected fallback [(0.0, 100.0)], got {cover!r}",
        )
    )

    # 4. Two intervening bodies -> three clear gaps.
    triple = split(0.0, 100.0, [(20.0, 30.0), (60.0, 70.0)])
    checks.append(
        (
            "two intervening bodies yield three gaps",
            triple == [(0.0, 20.0), (30.0, 60.0), (70.0, 100.0)],
            f"expected three gaps, got {triple!r}",
        )
    )

    # 5. _overlay_axial_spans_within only keeps bodies whose center is strictly
    #    between the two surfaces (clamped), not ones at/outside the surfaces.
    service = Open3DThicknessDimensionService(
        inspector=_FakeInspector(
            {
                "optical": {"proj_min": 44.12319, "proj_max": 55.70319},  # between -> keep
                "downstream": {"proj_min": 130.0, "proj_max": 150.0},      # beyond Image -> drop
                "on_object": {"proj_min": -1.0, "proj_max": 1.0},          # centered on Object -> drop
            }
        ),
        pv_module=None,
        billboard_text_actor_cls=None,
    )
    spans = service._overlay_axial_spans_within(np.asarray((0.0, 0.0, 1.0)), 0.0, 100.0)
    keep_ok = (
        len(spans) == 1
        and _near(spans[0][0], 44.12319)
        and _near(spans[0][1], 55.70319)
    )
    checks.append(
        (
            "only bodies between the surfaces are carved out",
            keep_ok,
            f"expected one span (44.12319, 55.70319), got {spans!r}",
        )
    )

    # 6. Line thickness bumped for BOTH distances (shared knobs).
    checks.append(
        (
            "dimension tube radius factor increased",
            Open3DThicknessDimensionService.DIMENSION_TUBE_RADIUS_FACTOR >= 0.30,
            f"tube factor too thin: {Open3DThicknessDimensionService.DIMENSION_TUBE_RADIUS_FACTOR!r}",
        )
    )
    checks.append(
        (
            "dimension leader line width increased",
            Open3DThicknessDimensionService.DIMENSION_LEADER_LINE_WIDTH >= 2.0,
            f"leader width too thin: {Open3DThicknessDimensionService.DIMENSION_LEADER_LINE_WIDTH!r}",
        )
    )
    new_tube = _legacy_tube_radius(
        230.0,
        100.0,
        Open3DThicknessDimensionService.DIMENSION_TUBE_RADIUS_FACTOR,
        Open3DThicknessDimensionService.DIMENSION_TUBE_RADIUS_FLOOR,
    )
    old_tube = _legacy_tube_radius(230.0, 100.0, 0.18, 0.025)
    checks.append(
        (
            "rendered dimension shaft is materially thicker than before",
            new_tube > old_tube * 1.3,
            f"new tube radius {new_tube:.4f} not thicker than legacy {old_tube:.4f}",
        )
    )

    # 7. Source-couple so a refactor can't quietly drop the lens-awareness or the
    #    shared thickness knob from either distance.
    overlay_src = inspect.getsource(Open3DThicknessDimensionService.add_overlays)
    checks.append(
        (
            "add_overlays carves the span at overlays",
            "split_span_at_overlays" in overlay_src and "_emit_span_dimension" in overlay_src,
            "add_overlays no longer splits the row span at imported overlays",
        )
    )
    emit_src = inspect.getsource(Open3DThicknessDimensionService._emit_span_dimension)
    checks.append(
        (
            "persistent leaders use the shared thickness constant",
            "DIMENSION_LEADER_LINE_WIDTH" in emit_src,
            "persistent dimension leaders no longer use DIMENSION_LEADER_LINE_WIDTH",
        )
    )
    live_src = inspect.getsource(Kraken3DInspector._draw_step_translate_gap_overlay)
    checks.append(
        (
            "live drag readout shares the thickness knobs",
            "DIMENSION_LEADER_LINE_WIDTH" in live_src and "arrow_mesh" in live_src,
            "live drag readout no longer shares the dimension thickness knobs",
        )
    )

    return checks


def main() -> int:
    checks = _checks()
    failed = [(name, detail) for name, ok, detail in checks if not ok]
    if failed:
        print("Open 3D thickness-overlay-skips-lens validation failed:")
        for name, detail in failed:
            print(f"- {name}: {detail}")
        return 1
    print(f"Open 3D thickness-overlay-skips-lens validation passed ({len(checks)} checks).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
