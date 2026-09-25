"""The Non-Sequential Scene Graph (docs/design_qt_migration.md phase 4).

What the trace actually sees: the scene-source records and the ordered SDT surface/object list,
as a hierarchy. The collector (`services/nonseq_scene_graph_records.py`) returns FLAT records
carrying `id` and `parent`, which is what a `ttk.Treeview` wants; `TreeRow` wants children, so
this nests them -- once, here, rather than in each toolkit.

Its three verbs act on the SELECTED node, so they are `ReportAction`s that take the selected key.
That key is the record's own `id` string, not its position: Set Target REBUILDS the graph and can
add a node, and an index would then point at a different node than the user had selected. The Tk
dialog keyed its rows by `id` for exactly this reason.
"""
from __future__ import annotations

from KrakenOS.UI.reports.base import (Report, ReportAction, ReportColumn, ReportFailed,
                                      ReportUpdate, TreeRow)
from KrakenOS.UI.scene_row_mapping import SOURCE_ROW_ORDER_DEFAULT, normalize_source_row_order

TITLE = "Non-Sequential Scene Graph"
TREE_HEADING = "Node"

#: (key, heading, width, anchor, stretch) exactly as the Tk dialog declared them
LAYOUT = (
    ("scene_row", "Scene Row", 86, "c", False),
    ("row", "Table Row", 76, "c", False),
    ("trace_surface", "Trace Surf", 76, "c", False),
    ("source_id", "Source ID", 120, "l", False),
    ("kind", "Kind", 116, "l", False),
    ("surface", "Surface / mode", 130, "l", False),
    ("material", "Material", 115, "l", False),
    ("features", "Features", 220, "l", True),
    ("target", "Target", 100, "l", False),
    ("detail", "Detail", 360, "l", True),
)

COLUMNS = tuple(
    ReportColumn(key, heading, numeric=False, width=width, stretch=stretch, align=align)
    for key, heading, width, align, stretch in LAYOUT
)

#: the CSV carries the tree's own wiring too, which no column shows
CSV_COLUMNS = ("id", "parent", "text", *[key for key, *_rest in LAYOUT], "row_index")


def tree_rows(records) -> tuple[TreeRow, ...]:
    """Nest the flat `id`/`parent` records. A parent that is not there leaves its child at top."""
    nodes: dict[str, TreeRow] = {}
    for record in records:
        node_id = str(record.get("id", ""))
        nodes[node_id] = TreeRow(
            label=str(record.get("text", "")),
            cells=tuple(str(record.get(key, "")) for key, *_rest in LAYOUT),
            detail_key=node_id)
    roots: list[TreeRow] = []
    for record in records:
        node = nodes[str(record.get("id", ""))]
        parent = nodes.get(str(record.get("parent", "")))
        (parent.children if parent is not None else roots).append(node)
    return tuple(roots)


def summary_text(owner, records) -> str:
    """The Tk dialog's own summary line, counted from the records."""
    target_index = owner._current_nonseq_target_surface_index()
    target_text = ("Auto image/termination target" if target_index is None
                   else f"S{target_index}: {owner.rows[target_index].name}")
    def count(kind):
        return sum(1 for record in records if str(record.get("kind", "")) == kind)
    detector_count = sum(
        1 for record in records
        if str(record.get("kind", "")) == "SceneTarget"
        and "detector" in str(record.get("features", "")).lower())
    order = normalize_source_row_order(
        getattr(owner, "layout_scene_row_order", SOURCE_ROW_ORDER_DEFAULT))
    return (
        "KrakenOS non-sequential scene = scene source records + ordered SDT surface/object list. "
        f"Scene rows={len(owner._current_scene_row_mapping().records)} ({order}) | "
        f"surface rows={len(owner.rows)} | targets={count('SceneTarget')} "
        f"({detector_count} detectors) | optical volumes={count('OpticalVolume')} | "
        f"boundary faces={count('BoundaryFace')} | target={target_text} | "
        "trace paths are shown in Trace Path Inspector.")


def record_for(records, key) -> "dict | None":
    """The record a node key stands for -- the key IS its `id`."""
    if key is None:
        return None
    node_id = str(key)
    return next((record for record in records
                 if str(record.get("id", "")) == node_id), None)


def _row_index(record) -> "int | None":
    """The table row a node stands for, or None when it stands for no row at all."""
    if record is None:
        return None
    try:
        return int(record.get("row_index"))
    except (TypeError, ValueError):
        return None


def build_nonseq_scene_graph_report(owner) -> Report:
    """The scene as the non-sequential trace sees it."""
    try:
        records = list(owner._collect_nonseq_scene_graph_records())
    except Exception as exc:
        raise ReportFailed(str(exc)) from exc

    def select_row(key) -> str:
        """Select the node's row in the surface table -- a whole ELEMENT when it is one."""
        record = record_for(records, key)
        index = _row_index(record)
        if index is None or not 0 <= index < len(owner.rows):
            return ""
        if str(record.get("id", "")).startswith("element:"):
            owner._select_table_indices(owner._element_indices_for_index(owner.rows, index),
                                        focus_index=index)
        else:
            owner._select_table_indices([index], focus_index=index)
        return f"Selected row {index}: {owner.rows[index].name}"

    def set_target(key) -> ReportUpdate:
        """Aim the non-sequential trace at the node's row, as one undoable step.

        A `ReportUpdate` rather than a status line: the graph gains a target node, so it must be
        rebuilt -- and rebuilding LAST means the verb's own message is what the status bar keeps.
        """
        index = _row_index(record_for(records, key))
        if index is None or not 0 <= index < len(owner.rows):
            return ReportUpdate(rebuild=False)
        owner._begin_history_capture()
        owner._refresh_analysis_surface_choices()
        owner.nonseq_target_surface_var.set(f"{index}: {owner.rows[index].name}")
        if hasattr(owner, "trace_mode_var"):
            owner.trace_mode_var.set("Non-Sequential Preview")
        owner._commit_history_capture()
        owner._mark_plot_update_pending()
        return ReportUpdate(
            status=f"Non-sequential target set to row {index}: {owner.rows[index].name}")

    def edit_target() -> str:
        owner.open_scene_target_editor()
        return ""

    # the Tk dialog opened on the first SURFACE node, not on the first node
    first_surface = next((str(record.get("id", "")) for record in records
                          if str(record.get("id", "")).startswith("surface:")),
                         str(records[0].get("id", "")) if records else None)

    return Report(
        title=TITLE,
        summary=summary_text(owner, records),
        columns=COLUMNS,
        rows=records,
        csv_keys=CSV_COLUMNS,
        tree=tree_rows(records),
        tree_heading=TREE_HEADING,
        initial_key=first_surface,
        actions=(
            ReportAction("Select Row", select_row, needs_selection=True, on_activate=True),
            ReportAction("Set Target", set_target, needs_selection=True),
            ReportAction("Edit Target", edit_target),
        ),
        status=(f"{TITLE}: {len(records)} nodes." if records else "No scene graph data."),
    )


build_nonseq_scene_graph_report.TITLE = TITLE
