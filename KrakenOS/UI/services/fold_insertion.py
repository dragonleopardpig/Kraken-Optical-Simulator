"""Plan a sequential fold mirror that keeps the downstream chain functional.

When a user drops a fold mirror in front of an existing optical axis, every row
that follows must move onto the *reflected* branch or it stops receiving the
beam (the user's "all the components following will immediately not functional"
complaint).  A sequential KrakenOS ``Mirror`` row already does the repositioning
for free: the system builder forces ``AxisMove = 2.0`` on any reflector, so the
trace re-orients every following surface onto the folded path automatically
(this is the canonical ``Double Mirror Fold`` / ``Flat Mirror 45 Deg`` pattern).
The promoted *non-sequential* prism is the one that does NOT do this -- it folds
the rays in 3D but leaves the sequential table rows on the original axis.

So the fix for "reposition all following components to the reflected path" is to
insert a sequential ``Mirror`` (not a promoted solid) and split the gap it lands
in between the upstream surface and the mirror, so the summed optical path --
and therefore the conjugate / focus -- is preserved.  This module owns that pure
geometry; the Tk editor owns the table mutation and history capture.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from KrakenOS.UI.surface_table_model import (
    SurfaceRow,
    clone_surface_row,
    clone_surface_rows,
)


FOLD_MIRROR_DEFAULT_TILT_X = 45.0
FOLD_MIRROR_DEFAULT_NAME = "Fold Mirror"

# Object/Image planes are not beam-limiting apertures, so they must not drive the
# fold-mirror size (an Image "sensor" can be far larger than the working beam).
_NON_APERTURE_SURFACES = frozenset({"Object", "Image"})


@dataclass
class FoldMirrorPlan:
    """The result of :func:`plan_fold_mirror` -- a ready-to-insert mirror row and
    the gap split that keeps the conjugate unchanged."""

    mirror_row: SurfaceRow
    insert_after_index: int
    upstream_thickness: float
    mirror_thickness: float

    def apply(self, rows: list[SurfaceRow]) -> list[SurfaceRow]:
        """Return a NEW row list with the gap split and the mirror inserted.

        Mirrors exactly what the editor does in-place (set the upstream gap, then
        insert the mirror after it), so a headless trace of ``apply(rows)`` proves
        what the user will see.
        """
        out = clone_surface_rows(rows)
        out[self.insert_after_index].thickness = self.upstream_thickness
        out.insert(self.insert_after_index + 1, clone_surface_row(self.mirror_row))
        return out


def can_insert_fold_mirror(rows: list[SurfaceRow], insert_after_index: int) -> bool:
    """A fold mirror needs at least one downstream surface to reflect onto, so it
    cannot land on (or after) the last row."""
    return 0 <= insert_after_index < len(rows) - 1


def _max_downstream_aperture(rows: list[SurfaceRow], after_index: int) -> float:
    diameters = [
        float(row.diameter)
        for row in rows[after_index + 1 :]
        if row.surface not in _NON_APERTURE_SURFACES
    ]
    here = rows[after_index]
    if here.surface not in _NON_APERTURE_SURFACES:
        diameters.append(float(here.diameter))
    positive = [value for value in diameters if value > 0.0]
    return max(positive) if positive else 25.0


def plan_fold_mirror(
    rows: list[SurfaceRow],
    insert_after_index: int,
    *,
    tilt_x: float = FOLD_MIRROR_DEFAULT_TILT_X,
    name: str = FOLD_MIRROR_DEFAULT_NAME,
    split_fraction: float = 0.5,
) -> FoldMirrorPlan:
    """Plan a sequential 45-degree fold mirror inserted after ``insert_after_index``.

    The gap the mirror lands in (the upstream row's thickness) is split between
    the upstream surface and the mirror so the total path length is unchanged.
    The mirror is sized at sqrt(2) x the largest downstream clear aperture so a
    beam of that diameter clears the 45-degree reflector.
    """
    if not can_insert_fold_mirror(rows, insert_after_index):
        raise ValueError(
            "a fold mirror needs at least one downstream surface to reflect onto"
        )
    fraction = min(max(float(split_fraction), 0.0), 1.0)
    gap = float(rows[insert_after_index].thickness)
    upstream = round(gap * fraction, 6)
    mirror_thickness = round(gap - upstream, 6)
    mirror_diameter = round(_max_downstream_aperture(rows, insert_after_index) * math.sqrt(2.0), 3)
    mirror_row = SurfaceRow(
        surface="Mirror",
        name=name,
        glass="MIRROR",
        rc=0.0,
        thickness=mirror_thickness,
        diameter=mirror_diameter,
        tilt_x=float(tilt_x),
        axis_move=2.0,
        element=name,
        advanced={
            "Display2D": {"label": name},
            "Note": (
                "Sequential fold mirror: KrakenOS re-orients every row after this "
                "reflector onto the folded path (AxisMove=2), so the downstream "
                "components stay on the beam. The upstream gap was split between "
                "this mirror and the surface before it, so the optical conjugate "
                "(focus) is preserved."
            ),
        },
    )
    return FoldMirrorPlan(
        mirror_row=mirror_row,
        insert_after_index=insert_after_index,
        upstream_thickness=upstream,
        mirror_thickness=mirror_thickness,
    )
