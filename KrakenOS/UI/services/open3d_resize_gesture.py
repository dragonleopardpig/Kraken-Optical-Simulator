"""Pure planning core for the drag-a-face-to-resize gesture (bugs/0064 step 3).

The geometry kernel (``open3d_solid_resize``) already knows how to *apply* a
resize: given target extents + an anchor it scales the base mesh in native
space.  What it does not know is how to turn a **gesture** -- "the user grabbed
this face and dragged it outward by N mm" -- into the resize spec the apply path
consumes.  That translation is this module, kept pure (no Tk/VTK/editor state)
so it can be unit-tested without a renderer (the live VTK inspector SIGSEGVs
headless).

The live layer feeds in:

* ``face_normal_native`` -- the grabbed face's outward unit normal in the solid's
  **native / base-mesh frame** (the same frame the coupling axes and the stored
  ``target_extents`` live in; the interaction layer maps the world pick back to
  this frame).
* ``current_extents`` -- the solid's current per-axis sizes (the original B-rep
  extents, possibly already overridden by a prior resize).
* ``resize_axes`` -- the cached :class:`ResizeAxes` coupling roles (or ``None``
  for a plain, freely-resizable solid).
* ``outward_delta_mm`` -- how far the dragged face has moved **outward** (positive
  grows the dimension; negative shrinks it).

and gets back exactly what ``_apply_step_overlay_resize_solve`` /
``_set_step_resize_for_label`` need: ``target_extents`` (3 entries, ``None`` =
unchanged), ``anchor_axis``, ``anchor_at_max`` and the ``coupled`` metadata flag.

North-Star detail (the beam-splitter coupling): a cube splitter's 45-deg coating
stays at 45 deg only when the two diagonal-spanning axes scale by the same
factor, so dragging a *cross-section* face grows **both** coupled axes to the
same target (a square cross-section, both prisms as one); dragging the *free*
(depth) face changes only that axis.  A plain solid grows only the dragged axis.
The dragged face moves while the opposite face stays put -- so the anchor sits on
the opposite (fixed) face: ``anchor_at_max`` is ``True`` exactly when the grabbed
face is the min-coordinate face (the max face is then the one held fixed).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:  # avoid pulling numpy in at import time for this pure module
    from KrakenOS.UI.services.open3d_solid_resize import ResizeAxes

# Never let a drag shrink a solid below this along any axis -- a zero/negative
# extent would collapse the body and divide-by-zero the scale factor.
MIN_EXTENT_MM = 1.0

_AXIS_LABELS = ("X", "Y", "Z")


@dataclass(frozen=True)
class ResizeDragPlan:
    """How a grabbed face maps onto a resize, before a drag distance is known.

    ``axis`` is the native axis the dragged face is perpendicular to (the one it
    grows).  ``coupled_axes`` are the axes that scale **together** for this drag
    (two for a splitter cross-section face, one otherwise).  ``anchor_axis`` /
    ``anchor_at_max`` pin the opposite (fixed) face.  ``is_splitter`` is the
    metadata ``coupled`` flag (the solid has a detected 45-deg coating).
    """

    axis: int
    anchor_axis: int
    anchor_at_max: bool
    coupled_axes: tuple[int, ...]
    is_splitter: bool

    @property
    def couples_pair(self) -> bool:
        """True when this drag scales two axes together (a cross-section drag)."""
        return len(self.coupled_axes) > 1

    def axis_label(self, axis: int) -> str:
        return _AXIS_LABELS[int(axis)] if 0 <= int(axis) < 3 else str(axis)


def _as_floats(values: Sequence[float]) -> list[float]:
    out = [float(v) for v in list(values)[:3]]
    while len(out) < 3:
        out.append(0.0)
    return out


def dominant_axis(normal: Sequence[float]) -> int:
    """Index of the largest-magnitude component of ``normal`` (the face's axis)."""
    comps = _as_floats(normal)
    best_axis = 0
    best_mag = -1.0
    for axis in range(3):
        mag = abs(comps[axis])
        if mag > best_mag:
            best_mag = mag
            best_axis = axis
    return best_axis


def plan_face_drag(
    face_normal_native: Sequence[float],
    resize_axes: "ResizeAxes | None",
) -> ResizeDragPlan:
    """Resolve the grabbed face into a :class:`ResizeDragPlan`.

    ``resize_axes`` (or ``None``) decides whether the dragged axis couples its
    pair: dragging either coupled axis grows both (square cross-section), the
    free axis grows alone, and a plain solid grows only the dragged axis.
    """
    comps = _as_floats(face_normal_native)
    axis = dominant_axis(comps)
    # The grabbed face moves; the opposite face is held fixed.  When the grabbed
    # face is the min-coordinate face (normal points along -axis), the fixed face
    # is the max face -> anchor_at_max is True.
    anchor_at_max = comps[axis] < 0.0

    coupled_pair: tuple[int, ...] = (axis,)
    is_splitter = resize_axes is not None
    if resize_axes is not None:
        pair = tuple(int(a) for a in getattr(resize_axes, "coupled_axes", ()))
        if axis in pair and len(pair) == 2:
            coupled_pair = tuple(sorted(pair))

    return ResizeDragPlan(
        axis=axis,
        anchor_axis=axis,
        anchor_at_max=anchor_at_max,
        coupled_axes=coupled_pair,
        is_splitter=is_splitter,
    )


def new_extent_for_drag(
    current_extents: Sequence[float],
    plan: ResizeDragPlan,
    outward_delta_mm: float,
    *,
    min_extent: float = MIN_EXTENT_MM,
) -> float:
    """Target size along the dragged axis after moving the face ``outward_delta_mm``.

    Clamped to ``min_extent`` so a large inward drag can never collapse the body.
    """
    current = _as_floats(current_extents)
    base = current[plan.axis]
    return max(float(min_extent), base + float(outward_delta_mm))


def target_extents_for_extent(
    plan: ResizeDragPlan,
    new_extent: float,
) -> list[float | None]:
    """``target_extents`` (3 entries, ``None`` = unchanged) for the new size.

    Every axis in ``plan.coupled_axes`` is set to ``new_extent`` -- one axis for a
    plain/free drag, both diagonal axes for a splitter cross-section drag (which
    is how the square-cross-section coupling is realised, mirroring the popup).
    """
    targets: list[float | None] = [None, None, None]
    for axis in plan.coupled_axes:
        targets[int(axis)] = float(new_extent)
    return targets


def resolve_resize_drag(
    current_extents: Sequence[float],
    face_normal_native: Sequence[float],
    resize_axes: "ResizeAxes | None",
    outward_delta_mm: float,
    *,
    min_extent: float = MIN_EXTENT_MM,
) -> tuple[list[float | None], int, bool, bool, float]:
    """One-call planner for the live gesture's commit.

    Returns ``(target_extents, anchor_axis, anchor_at_max, coupled, new_extent)``
    -- exactly the arguments ``_apply_step_overlay_resize_solve`` takes, plus the
    new dragged-axis size for the live readout.
    """
    plan = plan_face_drag(face_normal_native, resize_axes)
    new_extent = new_extent_for_drag(
        current_extents, plan, outward_delta_mm, min_extent=min_extent
    )
    targets = target_extents_for_extent(plan, new_extent)
    return targets, plan.anchor_axis, plan.anchor_at_max, plan.is_splitter, new_extent


def readout_label(plan: ResizeDragPlan, new_extent: float) -> str:
    """Live drag readout, e.g. ``"X×Y = 55 mm"`` (coupled) or ``"Z = 78 mm"``."""
    axes = "×".join(plan.axis_label(a) for a in plan.coupled_axes)
    return f"{axes} = {float(new_extent):.4g} mm"
