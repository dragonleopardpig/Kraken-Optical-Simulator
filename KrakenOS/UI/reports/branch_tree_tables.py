"""The Trace Path Inspector's tree (docs/design_qt_migration.md phase 3).

The fifth dialog family: a HIERARCHY. Every traced ray is a node, and the paths it split into
hang underneath it -- nested again when one path branched from another. A table cannot show that,
which is why the Ray Inspector's port (bugs/0867) deliberately left this dialog alone.

Toolkit-free: this builds the nodes, and each toolkit renders them (a ttk.Treeview with
`show="tree headings"`, a QTreeView with a standard item model).
"""
from __future__ import annotations

from KrakenOS.UI.reports.base import ReportColumn, TreeRow

TITLE = "Trace Path Inspector"
EMPTY = "No trace data. Click Update."
TREE_HEADING = "Ray / Path"
#: a tree key that means "every path of this ray", not one record
RAY_KEY_PREFIX = "ray:"

#: (key, heading, width, anchor) exactly as the Tk branch tree declares them
LAYOUT = (
    ("field", "Field", 60, "center"),
    ("parent", "Parent", 70, "center"),
    ("steps", "Steps", 80, "center"),
    ("surfaces", "Surface path", 320, "w"),
    ("termination", "Termination", 160, "w"),
    ("terminal_media", "Terminal medium", 120, "w"),
    ("terminal_index", "Terminal n", 82, "e"),
    ("terminal_inside", "Terminal inside", 130, "w"),
    ("diagnostic", "Diagnostic", 240, "w"),
    ("hits", "Hits", 55, "center"),
    ("distance", "Dist [mm]", 90, "e"),
    ("op", "OP [mm]", 90, "e"),
    ("ttbe", "TTBE", 76, "e"),
)
STRETCH = {"surfaces", "termination", "diagnostic"}

COLUMNS = tuple(
    ReportColumn(key, heading, numeric=anchor != "w", width=width, stretch=key in STRETCH,
                 align={"w": "l", "center": "c", "e": "r"}.get(anchor, ""))
    for key, heading, width, anchor in LAYOUT
)


def branch_cells(owner, record) -> tuple[str, ...]:
    """A path node's cells, exactly as the Tk branch tree inserts them."""
    show = owner._format_ray_inspector_value
    parent_branch = record.get("parent_branch_id")
    return tuple(str(value) for value in (
        int(record.get("field_index", 0)),
        "-" if parent_branch is None else parent_branch,
        f"{record.get('start_step', '')}-{record.get('end_step', '')}",
        record.get("surface_path", ""),
        record.get("termination", ""),
        record.get("terminal_media", ""),
        show(record.get("terminal_index")),
        record.get("terminal_inside_volumes", ""),
        record.get("termination_diagnostic", "") or record.get("branch_tree_diagnostic", ""),
        int(record.get("hit_count", 0)),
        show(record.get("distance")),
        show(record.get("op")),
        show(record.get("transmission")),
    ))


def ray_cells(branch_count: int, field_index: int) -> tuple[str, ...]:
    """A ray node carries only its field and how many paths hang under it."""
    return tuple(str(value) for value in (
        field_index, "-", "-", "-", "ray", "-", "-", "-", "-", branch_count, "-", "-", "-"))


def branch_label(record) -> str:
    branch_id = int(record.get("branch_id", 0))
    path = str(record.get("branch_path", "") or "").strip()
    return f"Path {branch_id}: {path}" if path else f"Path {branch_id}"


def branch_tree_rows(owner, records) -> list[TreeRow]:
    """Rays, with their paths nested underneath -- a path under its PARENT path when it has one.

    `detail_key` on a path node is that record's index in ``records``, which is what the detail
    view is asked for. A RAY node carries ``"ray:<index>"``: it has no hits of its own, but the
    Tk dialog has always shown every hit of every path beneath it when one is selected, so the
    key says which ray to gather rather than leaving the detail empty.
    """
    by_ray: dict[int, list[int]] = {}
    for index, record in enumerate(records):
        by_ray.setdefault(int(record["ray_index"]), []).append(index)

    rows: list[TreeRow] = []
    for ray_index in sorted(by_ray):
        indices = sorted(by_ray[ray_index], key=lambda i: int(records[i].get("branch_id", 0)))
        field_index = int(records[indices[0]].get("field_index", 0)) if indices else 0
        ray_row = TreeRow(label=f"Ray {ray_index}",
                          cells=ray_cells(len(indices), field_index),
                          detail_key=f"{RAY_KEY_PREFIX}{ray_index}")
        nodes: dict[int, TreeRow] = {}
        for index in indices:
            record = records[index]
            node = TreeRow(label=branch_label(record), cells=branch_cells(owner, record),
                           detail_key=index)
            nodes[int(record.get("branch_id", 0))] = node
            parent_branch = record.get("parent_branch_id")
            parent = None
            if parent_branch is not None:
                try:
                    parent = nodes.get(int(parent_branch))
                except (TypeError, ValueError):
                    parent = None
            (parent.children if parent is not None else ray_row.children).append(node)
        rows.append(ray_row)
    return rows


def summary_text(owner, path_count: int) -> str:
    """The Tk trace-path inspector's own summary line."""
    summary = owner._trace_preview_summary()
    if not summary["total_rays"]:
        return EMPTY
    text = ("{requested} -> {active} | backend={backend} | rays={total} | paths={branches} | "
            "image hits={hits}/{total}").format(
        requested=summary["requested"], active=summary["active"],
        backend=summary["backend"], total=summary["total_rays"], branches=path_count,
        hits=summary["image_hits"])
    note = str(summary.get("note", "")).strip()
    return f"{text} | {note}" if note else text
