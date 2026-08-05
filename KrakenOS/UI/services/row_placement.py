"""Step 1 of ``docs/design_row_placement_space.md`` — ONE answer to "what do a row's numbers mean".

``SurfaceRow.desp_x/desp_y/desp_z`` carries two incompatible meanings:

* **SEQUENTIAL** — an offset from the row's station, where the station accumulates ``thickness``
  along a nominal axis. The chain is straight and the FOLD IS APPLIED LATER (for display, and for
  the folded trace).
* **WORLD** — an absolute placement that is already final and ALREADY FOLDED. This is what the
  bugs/0433 freeze/snap bakes in, and what an axis-to-axis move leaves behind.

Nothing in the type says which is in force, so today six subsystems each infer it privately —
the sequential trace, the folded display overlay, STEP body anchoring, the solvers, branch-detector
synthesis, and the 2-D slice. Every drift between those inferences has been a bug: 0448
(drawn-vs-traced tilt), 0456 (rows vs bodies moving opposite ways), 0457-A (a row folded twice),
0457-B (a sequential trace over world-placed rows).

This module is the single place that answers the question. It is PURE and READ-ONLY: Step 1 adds
it and changes no behaviour; Step 2 re-points the consumers at it, one per commit, with
``tools/pose_audit.py`` green after each.

The invariant it exists to make expressible:

    a WORLD-placed row must never have the display fold applied to it — its numbers are already
    folded, and folding again moves it by the fold displacement a second time (measured: the AZ85
    BS scene draws its Image at -48.77 where the prescription, the camera body and the
    reached-image detector all say +2.73 — a 51.50 mm error, exactly the fold mirror's thickness).
"""
from __future__ import annotations

from typing import Any, NamedTuple

import numpy as np

SEQUENTIAL = "sequential"
WORLD = "world"

#: ``ScenePlacement`` keys that mark a row as absolutely placed. Kept in ONE list so a new
#: placement mode cannot be added to some consumers and forgotten by others (which is how
#: bugs/0447's frozen predicate and the import/export one drifted apart).
WORLD_PLACEMENT_KEYS = ("stay_put_freeze", "last_axis_to_axis_move")


class Pose(NamedTuple):
    """A row's pose. ``orientation`` is degrees (tilt x/y/z) or None when the row has no tilts.

    Orientation is carried from the start deliberately: bugs/0448 was a TILT divergence, and the
    stated goal is that what the live scene shows — position AND orientation — is what the physics
    uses. A position-only pose cannot express that.
    """

    position: np.ndarray
    orientation: "np.ndarray | None"
    space: str


def _scene_placement(row: Any) -> dict:
    advanced = getattr(row, "advanced", None)
    if not isinstance(advanced, dict):
        return {}
    placement = advanced.get("ScenePlacement")
    return placement if isinstance(placement, dict) else {}


def placement_space(row: Any) -> str:
    """``WORLD`` when this row's numbers are already absolute, else ``SEQUENTIAL``."""
    placement = _scene_placement(row)
    for key in WORLD_PLACEMENT_KEYS:
        if placement.get(key):
            return WORLD
    return SEQUENTIAL


def is_world_placed(row: Any) -> bool:
    return placement_space(row) is WORLD or placement_space(row) == WORLD


def must_not_display_fold(row: Any) -> bool:
    """True when applying the display fold to this row would fold it a SECOND time.

    This is the predicate that kills bugs/0457-A when Step 2 wires the display to it. It is
    spelled out as its own name (rather than callers writing ``is_world_placed``) so the reason
    survives at every call site.
    """
    return is_world_placed(row)


def row_tilts(row: Any) -> "np.ndarray | None":
    values = []
    for lower, upper in (("tilt_x", "TiltX"), ("tilt_y", "TiltY"), ("tilt_z", "TiltZ")):
        value = getattr(row, lower, None)
        if value is None:
            value = getattr(row, upper, None)
        if value is None:
            return None
        try:
            values.append(float(value))
        except Exception:
            return None
    return np.asarray(values, dtype=float)


def prescription_pose(editor: Any, row_index: int) -> Pose:
    """The pose as the row's own numbers state it, tagged with the space they are in.

    NOTE (Step 1 scope): for a SEQUENTIAL row this is the STRAIGHT-EQUIVALENT pose — the fold has
    not been applied. Step 2 moves the fold inside this resolver so that a single call answers
    "where is this row in the world" for both spaces and a second fold becomes unrepresentable.
    Until then, callers must keep using their existing fold path for SEQUENTIAL rows and must skip
    it for WORLD rows (``must_not_display_fold``).
    """
    rows = list(getattr(editor, "rows", []) or [])
    if not (0 <= int(row_index) < len(rows)):
        raise IndexError(f"row {row_index} out of range")
    row = rows[int(row_index)]
    stations = editor._row_z_positions()
    position = np.asarray(
        [
            float(row.desp_x),
            float(row.desp_y),
            float(stations[int(row_index)]) + float(row.desp_z),
        ],
        dtype=float,
    )
    return Pose(position=position, orientation=row_tilts(row), space=placement_space(row))


def scene_placement_summary(editor: Any) -> dict:
    """``{row_index: space}`` for a whole scene — what the audit and Step 2 consume."""
    rows = list(getattr(editor, "rows", []) or [])
    return {index: placement_space(row) for index, row in enumerate(rows)}


def rotation_matrix(row: Any) -> "np.ndarray | None":
    """The row's orientation as a 3x3 world rotation, or None when it carries no tilts.

    Columns are the row's local axes in world coordinates, so ``rotation[:, 2]`` is its normal
    and ``rotation[:, 1]`` its height (bitangent) — the two a detector/plane consumer needs."""
    tilts = row_tilts(row)
    if tilts is None:
        return None
    try:
        from KrakenOS.UI.optical_solid_metadata import rotation_matrix_from_kraken_tilts

        matrix = np.asarray(
            rotation_matrix_from_kraken_tilts(*(float(v) for v in tilts)), dtype=float
        )
    except Exception:
        return None
    if matrix.shape != (3, 3) or not np.all(np.isfinite(matrix)):
        return None
    return matrix


def world_pose(editor: Any, row_index: int) -> Pose:
    """**The** resolver: where row ``row_index`` actually is, in world coordinates.

    bugs/0557 — Step 2 of ``docs/design_row_placement_space.md``, for the consumers that do not
    need the folded-display frame.

    * A **WORLD** row (the 0433 freeze / axis snap / a promoted solid) already carries its final
      placement, so its numbers ARE the answer.
    * A **SEQUENTIAL** row returns the straight-equivalent pose. The display fold is NOT applied
      here yet — that is the unfinished half of Step 2, blocked on locating the producer of the
      drawn folded geometry (two candidate sites eliminated by measurement, see the design doc).
      The ``space`` field says which you got, so a caller can never silently mistake one for the
      other, and a caller needing the fold must still apply its own.

    Why this exists: FIVE consumers have now hand-rolled "where is this row really" and each got
    it wrong on a frozen scene — the branch camera frame (0517), the FOV solve gate (0519), the
    acceptance-cone crease (0525), the lens-swap block placement (0547), and the Normal-to-Sensor
    anchor (0556, which aimed 194 mm off the sensor and drew an empty view). Every one of them
    assumed the straight axis while the row carried its placement in ``desp`` + ``tilt``."""
    return prescription_pose(editor, row_index)


def world_frame(editor: Any, row_index: int) -> "tuple[np.ndarray, np.ndarray | None, str]":
    """``(position, rotation_3x3_or_None, space)`` — :func:`world_pose` plus the orientation
    matrix, which is what a plane/detector consumer needs (normal = column 2, height = column 1).

    Keeping this beside the resolver is deliberate: a consumer that derives a normal from tilts
    by hand is exactly how bugs/0556 ended up hardcoding ``(0, 0, 1)`` for a flipped sensor."""
    pose = world_pose(editor, row_index)
    rows = list(getattr(editor, "rows", []) or [])
    row = rows[int(row_index)] if 0 <= int(row_index) < len(rows) else None
    return pose.position, (rotation_matrix(row) if row is not None else None), pose.space
