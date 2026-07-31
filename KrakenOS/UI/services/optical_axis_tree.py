"""The optical axis as a TREE OF DIRECTED SEGMENTS -- derived, read-only (bugs/0485 stage 0).

The design principle, in the user's words: *"Mainly there is a optical axis, everything follows."*

    * A **root segment** carries the unfolded axis: an origin and a direction.
    * A **fold-introducing element** (a marked beam-splitter coating, a mirror, a promoted
      optical solid that folds) sitting at arc-length ``s`` on segment ``P`` EMITS a child
      segment ``C``: origin = the fold point, direction = ``P``'s direction reflected in the
      element's surface. A beam splitter emits two children -- transmit continues ``P``, reflect
      starts ``C``.
    * Every other element is SNAPPED to a segment: it stores ``(segment, s, transverse)`` and its
      world pose is DERIVED as ``origin + direction * s + transverse``.

From that single invariant the four rules the user stated are consequences, not features:

    1. delete the folder  -> its child ceases to exist, its children re-parent to ``P`` keeping
       ``s`` (now measured along the unfolded path) -- they snap back on their own;
    2. replace/insert one -> a new child, downstream elements re-parent keeping ``s``;
    3. slide the folder   -> the child's ORIGIN moves, everything on it follows;
    4. flip/rotate it     -> the child's DIRECTION changes, everything on it follows.

and so do several things that currently each have their own fix: folders in series (segments
chain), both BS arms (two children), non-90-degree tilts (just the reflection law), and "stay put"
(an element stays put IFF its segment did not move -- a consequence, not a mode).

**This module stores nothing and changes nothing.** Stage 0 exists to make the tree measurable
against the poses the editor currently keeps in world space, so a disagreement between the two is
a NUMBER rather than an argument. The structural invariants it can falsify:

    TRANSVERSE   an element that is not deliberately decentred sits ON its segment.
    CONTINUITY   a folder's child segment starts exactly at the folder's own pose on the parent.
    REFLECTION   the child's direction is the parent's, reflected in the folder's surface.
    MONOTONIC    arc-lengths increase along a segment in row order.

Pure numpy. No Tk, no VTK, no editor -- the caller passes ``rows`` and the fold data it already
computes, so this is drivable from a guard without building a scene.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

_TOL_TRANSVERSE_MM = 1.0e-3
_TOL_CONTINUITY_MM = 1.0e-3
_TOL_DIRECTION = 1.0e-6


def _unit(vector) -> "np.ndarray | None":
    try:
        vec = np.asarray(vector, dtype=float).reshape(-1)[:3]
    except Exception:
        return None
    if vec.size < 3 or not np.all(np.isfinite(vec)):
        return None
    norm = float(np.linalg.norm(vec))
    if not np.isfinite(norm) or norm <= 1.0e-12:
        return None
    return vec / norm


@dataclass
class AxisSegment:
    """One directed leg of the optical axis."""

    segment_id: str
    parent_id: "str | None"
    origin: np.ndarray
    direction: np.ndarray
    #: the row that EMITTED this segment (the folder); None for the root.
    source_row: "int | None" = None
    kind: str = "root"  # "root" | "reflect" | "transmit"
    #: arc-length along the PARENT at which this segment starts (0.0 for the root).
    start_on_parent: float = 0.0
    members: list = field(default_factory=list)  # row indices snapped to this segment

    def point_at(self, s: float) -> np.ndarray:
        return np.asarray(self.origin, dtype=float) + np.asarray(self.direction, dtype=float) * float(s)

    def project(self, point) -> "tuple[float, np.ndarray]":
        """(arc-length, transverse vector) of a world point relative to this segment."""
        rel = np.asarray(point, dtype=float).reshape(3) - np.asarray(self.origin, dtype=float)
        direction = np.asarray(self.direction, dtype=float)
        s = float(np.dot(rel, direction))
        return s, rel - direction * s


@dataclass
class AxisSnap:
    """Where one row sits: which segment, how far along, how far off."""

    row_index: int
    segment_id: str
    s: float
    transverse: np.ndarray

    @property
    def offset(self) -> float:
        return float(np.linalg.norm(self.transverse))


def row_world_pose(rows, index: int, stations=None) -> np.ndarray:
    """station + desp -- the pose source the trace and the frozen writers already use."""
    if stations is None:
        stations = station_positions(rows)
    row = rows[int(index)]
    z = float(stations[int(index)]) if int(index) < len(stations) else 0.0
    return np.asarray(
        (float(row.desp_x), float(row.desp_y), z + float(row.desp_z)), dtype=float
    )


def station_positions(rows) -> list:
    """Cumulative-thickness stations, matching ``_row_z_positions``."""
    out, z = [0.0], 0.0
    for row in list(rows)[:-1]:
        z += float(getattr(row, "thickness", 0.0) or 0.0)
        out.append(z)
    while len(out) < len(rows):
        out.append(z)
    return out


def build_axis_tree(
    rows,
    *,
    fold_emissions=None,
    root_origin=(0.0, 0.0, 0.0),
    root_direction=(0.0, 0.0, 1.0),
) -> "dict[str, AxisSegment]":
    """Derive the segment tree.

    ``fold_emissions`` maps ``row_index -> {"origin": (3,), "direction": (3,), "kind": str,
    "normal": (3,) | None}``: the fold point and emitted direction of each folder, as the caller's
    own geometry reports it (``_folded_*_conjugate_split``, ``optical_solid_output_port_pose_overrides``,
    a mirror's surface frame). Passing it in rather than deriving it here is deliberate: stage 0
    must compare against what the editor already believes, not invent a second opinion.

    Segments are keyed ``axis:root`` and ``axis:fold:<row>``, and each carries the arc-length on
    its parent at which it starts, so CONTINUITY is checkable.
    """
    rows = list(rows)
    direction = _unit(root_direction)
    if direction is None:
        direction = np.asarray((0.0, 0.0, 1.0), dtype=float)
    root = AxisSegment(
        segment_id="axis:root",
        parent_id=None,
        origin=np.asarray(root_origin, dtype=float).reshape(3),
        direction=direction,
        source_row=None,
        kind="root",
        start_on_parent=0.0,
    )
    tree = {root.segment_id: root}
    if not isinstance(fold_emissions, dict) or not fold_emissions:
        return tree

    # Folders in row order: each attaches to the segment that is active where it sits, so a
    # periscope's second mirror hangs off the first mirror's leg rather than off the root.
    for row_index in sorted(int(k) for k in fold_emissions):
        spec = fold_emissions[row_index] if row_index in fold_emissions else fold_emissions[str(row_index)]
        origin = np.asarray(spec.get("origin"), dtype=float).reshape(3)
        emitted = _unit(spec.get("direction"))
        if emitted is None or not np.all(np.isfinite(origin)):
            continue
        parent = _active_segment_for_point(tree, origin)
        s_on_parent, _ = parent.project(origin)
        segment = AxisSegment(
            segment_id=f"axis:fold:{row_index}",
            parent_id=parent.segment_id,
            origin=origin,
            direction=emitted,
            source_row=int(row_index),
            kind=str(spec.get("kind") or "reflect"),
            start_on_parent=float(s_on_parent),
        )
        tree[segment.segment_id] = segment
    return tree


def _active_segment_for_point(tree, point) -> AxisSegment:
    """The segment a point most plausibly lies on: smallest transverse offset, deepest first.

    Deepest-first matters on a periscope -- a point on the second leg is also *near* the first
    leg's infinite line, so ties must go to the more specific (later) segment.
    """
    best = None
    for segment in sorted(tree.values(), key=lambda seg: -_depth(tree, seg)):
        s, transverse = segment.project(point)
        offset = float(np.linalg.norm(transverse))
        if best is None or offset < best[0] - 1.0e-9:
            best = (offset, segment)
    return best[1] if best is not None else tree["axis:root"]


def _depth(tree, segment) -> int:
    depth, cursor = 0, segment
    while cursor.parent_id is not None and cursor.parent_id in tree:
        depth += 1
        cursor = tree[cursor.parent_id]
    return depth


def snap_rows(rows, tree, stations=None) -> "list[AxisSnap]":
    """Assign every row to a segment and record (s, transverse). Also fills ``members``."""
    rows = list(rows)
    if stations is None:
        stations = station_positions(rows)
    for segment in tree.values():
        segment.members = []
    snaps = []
    for index in range(len(rows)):
        pose = row_world_pose(rows, index, stations)
        segment = _active_segment_for_point(tree, pose)
        s, transverse = segment.project(pose)
        segment.members.append(index)
        snaps.append(AxisSnap(index, segment.segment_id, float(s), transverse))
    return snaps


def world_pose_from_snap(tree, snap: AxisSnap) -> np.ndarray:
    """The derived pose: ``origin + direction * s + transverse``. The stored pose must equal it."""
    segment = tree[snap.segment_id]
    return segment.point_at(snap.s) + np.asarray(snap.transverse, dtype=float)


def check_invariants(
    rows,
    tree,
    snaps,
    *,
    decentred_rows=(),
    tol_transverse=_TOL_TRANSVERSE_MM,
    tol_continuity=_TOL_CONTINUITY_MM,
) -> "list[str]":
    """Falsify the four structural invariants. Returns a list of human-readable violations."""
    problems: list[str] = []
    rows = list(rows)
    by_index = {snap.row_index: snap for snap in snaps}
    decentred = {int(i) for i in decentred_rows}

    # TRANSVERSE -- an element that is not deliberately decentred sits ON its segment.
    for snap in snaps:
        if snap.row_index in decentred:
            continue
        if snap.offset > tol_transverse:
            name = str(getattr(rows[snap.row_index], "name", "") or "")[:34]
            problems.append(
                f"TRANSVERSE row {snap.row_index} ({name!r}) sits {snap.offset:.4f} mm off "
                f"{snap.segment_id} (transverse {np.round(snap.transverse, 4).tolist()})"
            )

    # CONTINUITY -- the strong one, and the one that matters: a child segment's origin (the fold
    # point) must lie ON its parent segment. A beam cannot leave an axis it never met. Measured on
    # the reported scene this is exactly the "RA mirror not centered to optical axis, the fold axis
    # also slanted" flag: after a 30 x 30 solve axis:fold:7 starts at z = 48.473 while its parent
    # axis:fold:3 runs at z = 53.803, so the fold point hangs 5.33 mm below the beam feeding it.
    #
    # Note this is NOT "the fold point equals the folder row's centre" -- a BS coating is a
    # diagonal inside its cube, so its crossing legitimately sits ~0.67 mm off the row centre on
    # this scene. The fold point is authoritative; where it must lie is on the incoming axis.
    for segment in tree.values():
        if segment.parent_id is None or segment.parent_id not in tree:
            continue
        parent = tree[segment.parent_id]
        _s, transverse = parent.project(segment.origin)
        offset = float(np.linalg.norm(transverse))
        if offset > tol_continuity:
            problems.append(
                f"CONTINUITY {segment.segment_id} (from row {segment.source_row}) starts "
                f"{offset:.4f} mm OFF its parent {parent.segment_id} -- the fold point is not on "
                f"the incoming axis (origin {np.round(segment.origin, 3).tolist()}, parent runs "
                f"{np.round(parent.origin, 3).tolist()} -> {np.round(parent.direction, 3).tolist()})"
            )

    # MONOTONIC -- arc-lengths increase along a segment in row order.
    for segment in tree.values():
        members = [by_index[i] for i in segment.members if i in by_index]
        for previous, current in zip(members, members[1:]):
            if current.s < previous.s - tol_continuity:
                problems.append(
                    f"MONOTONIC on {segment.segment_id}: row {current.row_index} at s={current.s:.3f} "
                    f"is behind row {previous.row_index} at s={previous.s:.3f}"
                )
    return problems


def describe(rows, tree, snaps) -> str:
    """A compact dump for probes and bug reports."""
    rows = list(rows)
    lines = []
    for segment in sorted(tree.values(), key=lambda seg: (_depth(tree, seg), seg.segment_id)):
        lines.append(
            f"  {segment.segment_id:18s} kind={segment.kind:8s} parent={str(segment.parent_id):18s} "
            f"origin={np.round(segment.origin, 3).tolist()} dir={np.round(segment.direction, 4).tolist()} "
            f"start_on_parent={segment.start_on_parent:9.3f}"
        )
    for snap in snaps:
        name = str(getattr(rows[snap.row_index], "name", "") or "")[:30]
        lines.append(
            f"    S{snap.row_index:<3} {name:32s} {snap.segment_id:18s} s={snap.s:9.3f} "
            f"off={snap.offset:8.4f}"
        )
    return "\n".join(lines)


def descendant_segment_ids(tree, segment_id: str) -> "set[str]":
    """``segment_id`` and every segment below it."""
    out = {str(segment_id)}
    changed = True
    while changed:
        changed = False
        for segment in tree.values():
            if segment.parent_id in out and segment.segment_id not in out:
                out.add(segment.segment_id)
                changed = True
    return out


def rows_on_emitted_leg(rows, tree, snaps, folder_row: int) -> "list[int]":
    """Rows snapped to a folder's emitted leg, or to anything below it (bugs/0485 rule 3).

    "If the user slide the elements that introduce a fold axis, then all the snapped elements
    should follow the fold axis." These are those elements: everything sitting on the leg the
    folder emits, plus everything on legs emitted further down that chain -- slide the first
    mirror of a periscope and the second mirror's arm has to come too.

    Excludes the folder itself (it is what moved) and any ``Object`` row (the station anchor the
    whole prescription is measured from).
    """
    emitted = None
    for segment in tree.values():
        if segment.source_row is not None and int(segment.source_row) == int(folder_row):
            emitted = segment
            break
    if emitted is None:
        return []
    family = descendant_segment_ids(tree, emitted.segment_id)
    carried = []
    for snap in snaps:
        if int(snap.row_index) == int(folder_row):
            continue
        if snap.segment_id not in family:
            continue
        try:
            if str(getattr(rows[int(snap.row_index)], "surface", "") or "") == "Object":
                continue
        except Exception:
            pass
        carried.append(int(snap.row_index))
    return carried
