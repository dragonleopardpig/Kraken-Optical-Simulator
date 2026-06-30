"""Validate the auto-fold-mirror insertion (item 1).

When a user drops a fold mirror in front of an existing optical axis, every
surface after it must move onto the *reflected* branch or it stops receiving the
beam.  ``KrakenOS.UI.services.fold_insertion.plan_fold_mirror`` builds a single
sequential ``Mirror`` row (``glass="MIRROR"``, ``tilt_x=45``, ``axis_move=2``) and
splits the gap it lands in so the optical conjugate (focus) is preserved; the
KrakenOS trace then re-orients every downstream row onto the folded path for
free.  This guard checks that:

* ``plan_fold_mirror`` inserts a real reflector at the right place, with the gap
  split so the summed path length is unchanged, and sizes the mirror to clear
  the largest downstream aperture (sqrt(2) x);
* ``can_insert_fold_mirror`` refuses a placement with no downstream surface;
* a real KrakenOS sequential trace (build=0, no GL) of the planned rows folds the
  axis -- the on-axis bundle lands far off the straight Z axis on the transverse
  branch -- while the SAME system without the fold stays on axis;
* the editor mixin exposes ``insert_fold_mirror_below_index`` and the right-click
  "Insert Component Below" menu wires it up.

Like the machine-vision surrogate guards this is a STANDALONE check, not a penta
phase (it is build=0 / no-render and touches no baseline scene).
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from KrakenOS.UI.services.fold_insertion import (
    can_insert_fold_mirror,
    plan_fold_mirror,
)
from KrakenOS.UI.surface_table_model import SurfaceRow, surface_row_to_spec


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKBENCH_PATH = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "layout_table_workbench.py"
MENU_PATH = PROJECT_ROOT / "KrakenOS" / "UI" / "panels" / "main_context_menu.py"

_OBJECT_TO_LENS = 80.0
_LENS_TO_IMAGE = 100.0
_LENS_FOCAL = 60.0
_APERTURE = 40.0


def _base_rows() -> list[SurfaceRow]:
    """A trivial straight system: Object -> focusing Thin Lens -> Image."""
    return [
        SurfaceRow(surface="Object", name="Object", thickness=_OBJECT_TO_LENS, diameter=_APERTURE, glass="AIR"),
        SurfaceRow(surface="Thin Lens", name="Lens", rc=_LENS_FOCAL, thickness=_LENS_TO_IMAGE, diameter=_APERTURE, glass="AIR"),
        SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=_APERTURE, glass="AIR"),
    ]


def _mean_image_y(rows: list[SurfaceRow]) -> float | None:
    """Mean image-plane global Y from a real build=0 sequential trace, or None if
    the headless trace stack is unavailable."""
    try:
        from KrakenOS.UI.services import paraxial_tools
        import KrakenOS as Kos
    except Exception:
        return None
    try:
        specs = [surface_row_to_spec(row) for row in rows]
        system = paraxial_tools._build_system_from_specs(specs, build=0)
        keeper = Kos.raykeeper(system)
        ys: list[float] = []
        for x0, y0 in [(0.0, 0.0), (3.0, 0.0), (0.0, 3.0), (-3.0, 0.0), (0.0, -3.0)]:
            system.Trace([x0, y0, 0.0], [0.0, 0.0, 1.0], 0.55)
            keeper.push()
            _x, y, _z, _l, _m, _n = keeper.pick(-1)
            ys.append(float(y[-1]))
        if not ys:
            return None
        return float(np.mean(ys))
    except Exception:
        return None


def run_checks():
    """Return (passed, failures) without printing -- usable as a phase body."""
    base = _base_rows()
    plan = plan_fold_mirror(base, 0)
    folded = plan.apply(base)
    mirror = folded[1]

    expected_mirror_d = round(_APERTURE * math.sqrt(2.0), 3)

    workbench_src = WORKBENCH_PATH.read_text(encoding="utf-8") if WORKBENCH_PATH.exists() else ""
    menu_src = MENU_PATH.read_text(encoding="utf-8") if MENU_PATH.exists() else ""

    folded_y = _mean_image_y(folded)
    straight_y = _mean_image_y(base)

    checks = [
        ("plan inserts after the object", plan.insert_after_index == 0),
        ("folded row count is base + 1", len(folded) == len(base) + 1),
        ("inserted row is a Mirror", mirror.surface == "Mirror"),
        ("mirror is a reflector", str(mirror.glass) == "MIRROR"),
        ("mirror tilts 45 degrees", abs(abs(float(mirror.tilt_x)) - 45.0) < 1e-9),
        ("mirror folds the axis (AxisMove=2)", abs(float(mirror.axis_move) - 2.0) < 1e-9),
        ("mirror is flat (rc=0)", abs(float(mirror.rc)) < 1e-12),
        (
            "gap split preserves the path length",
            abs((plan.upstream_thickness + plan.mirror_thickness) - _OBJECT_TO_LENS) < 1e-6,
        ),
        ("upstream gap halved", abs(plan.upstream_thickness - _OBJECT_TO_LENS / 2.0) < 1e-6),
        ("upstream row thickness updated", abs(float(folded[0].thickness) - plan.upstream_thickness) < 1e-9),
        ("mirror clears the downstream aperture (sqrt2 x)", abs(float(mirror.diameter) - expected_mirror_d) < 1e-3),
        ("downstream lens follows the mirror", folded[2].surface == "Thin Lens"),
        ("image still last", folded[-1].surface == "Image"),
        ("refuses a fold with no downstream surface", not can_insert_fold_mirror(base, len(base) - 1)),
        ("accepts a fold before the image", can_insert_fold_mirror(base, 0)),
        (
            "trace folds the axis to the transverse branch",
            folded_y is not None and abs(folded_y) > 50.0,
        ),
        (
            "the same system without the fold stays on axis",
            straight_y is not None and abs(straight_y) < 1.0,
        ),
        ("editor exposes insert_fold_mirror_below_index", "def insert_fold_mirror_below_index" in workbench_src),
        ("editor uses plan_fold_mirror", "plan_fold_mirror" in workbench_src),
        ("context menu wires the fold mirror", "insert_fold_mirror_below_index" in menu_src),
    ]
    failures = [name for name, ok in checks if not ok]
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Fold-mirror insertion validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    folded_y = _mean_image_y(_base_rows() and plan_fold_mirror(_base_rows(), 0).apply(_base_rows()))
    branch = "unavailable" if folded_y is None else f"{folded_y:+.1f} mm"
    print(
        "Fold-mirror insertion validation passed: a sequential 45deg mirror is "
        "inserted with the gap split (conjugate preserved), and a real trace folds "
        f"the downstream chain onto the reflected branch (mean image Y={branch})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
