"""Position-aware insertion of a promoted in-path optical element into a
sequential prescription (bugs/0079).

An imported element that light passes through (a beam splitter plate, a lens, a
window) must enter the chain at the axial position where it physically sits, with
everything downstream (the lens, the image plane) left exactly where it was -- so
the simple ``Object -> element -> Lens -> Image`` trace works. The promote paths
instead appended the element at the chain *end* (after the lens) and compensated
with a large ``desp_z`` decenter, so the chain ORDER no longer matched the
geometry: rays either bent through the wrong place or vanished entirely.

This module is the pure, display-free placement core: given the current per-row
thicknesses, the element's physical front-face Z, and the element's fitted optical
surfaces (rc / glass / inter-surface gaps), it returns the spliced spec list with
the surrounding gap split so no downstream surface moves.
"""
from __future__ import annotations

from typing import Any


def vertex_positions(thicknesses: list[float]) -> list[float]:
    """Axial vertex Z of each row = running sum of the preceding thicknesses."""
    positions: list[float] = []
    running = 0.0
    for thickness in thicknesses:
        positions.append(running)
        running += float(thickness or 0.0)
    return positions


def gap_containing_z(thicknesses: list[float], target_z: float) -> int:
    """Index of the row whose gap to the next row contains ``target_z`` (so the
    element inserts just after it). Falls back to the last real gap."""
    positions = vertex_positions(thicknesses)
    target = float(target_z)
    for index in range(len(positions) - 1):
        if positions[index] <= target < positions[index + 1]:
            return index
    # Past the last vertex (or single-row) -> sit in the final gap before the end.
    return max(len(thicknesses) - 2, 0)


def plan_inpath_insertion(
    thicknesses: list[float],
    element_front_z: float,
    element_depth: float,
) -> tuple[int, float, float]:
    """Return ``(insert_index, preceding_gap, trailing_gap)`` for dropping an
    element of axial extent ``element_depth`` with its front at ``element_front_z``
    into the gap that contains it, splitting that gap so the row after it does not
    move:  ``preceding_gap + element_depth + trailing_gap == original_gap``.
    """
    if not thicknesses:
        return 0, 0.0, 0.0
    host = gap_containing_z(thicknesses, element_front_z)
    positions = vertex_positions(thicknesses)
    host_z = positions[host]
    original_gap = float(thicknesses[host] or 0.0)
    depth = max(float(element_depth), 0.0)
    if depth > original_gap:
        depth = original_gap  # never push the downstream surface
    preceding_gap = float(element_front_z) - host_z
    preceding_gap = max(0.0, min(preceding_gap, max(original_gap - depth, 0.0)))
    trailing_gap = max(original_gap - preceding_gap - depth, 0.0)
    return host + 1, preceding_gap, trailing_gap


def insert_inpath_element_into_specs(
    specs: list[dict[str, Any]],
    *,
    surfaces: list[dict[str, Any]],
    element_front_z: float,
) -> list[dict[str, Any]]:
    """Splice ``surfaces`` (the element's fitted optical surfaces, front->back, each
    a spec dict with at least ``thickness``; inter-surface ``thickness`` values are
    the glass gaps) into ``specs`` at the element's physical position.

    The host gap is split: the preceding row's thickness becomes the
    object->element distance, and the LAST inserted surface's thickness becomes the
    trailing gap to the next element, so nothing downstream moves. Inserted
    surfaces carry no axial decenter (``desp_z = 0``) -- the chain order now matches
    the geometry, so the trace no longer needs a compensating ``desp_z``.
    """
    out = [dict(spec) for spec in specs]
    plate = [dict(surf) for surf in surfaces]
    if not out or not plate:
        return out
    element_depth = sum(float(surf.get("thickness", 0.0) or 0.0) for surf in plate[:-1])
    thicknesses = [float(spec.get("thickness", 0.0) or 0.0) for spec in out]
    insert_index, preceding_gap, trailing_gap = plan_inpath_insertion(
        thicknesses, element_front_z, element_depth
    )
    host = insert_index - 1
    if 0 <= host < len(out):
        out[host] = {**out[host], "thickness": preceding_gap}
    plate[-1] = {**plate[-1], "thickness": trailing_gap}
    for surf in plate:
        surf.setdefault("desp_x", 0.0)
        surf.setdefault("desp_y", 0.0)
        surf["desp_z"] = 0.0
    out[insert_index:insert_index] = plate
    return out
