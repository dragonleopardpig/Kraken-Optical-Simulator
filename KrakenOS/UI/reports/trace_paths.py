"""The Trace Path Inspector (docs/design_qt_migration.md phase 3).

A master TREE of rays and the paths beneath them, with the hits of the selected path in the detail
view. The tree itself is built by `reports/branch_tree_tables.py`; the hits come from the editor's
own `_ray_hit_table_values`, as everywhere else in this family.
"""
from __future__ import annotations

from KrakenOS.UI.reports.base import DetailView, Report, ReportFailed
from KrakenOS.UI.reports.branch_tree_tables import (
    COLUMNS,
    EMPTY,
    TITLE,
    TREE_HEADING,
    branch_tree_rows,
    summary_text,
)
from KrakenOS.UI.reports.ray_tables import hit_columns


def build_trace_path_report(owner) -> Report:
    """Every traced path, nested under the ray it came from."""
    try:
        records = list(owner._collect_branch_tree_records(
            ray_records=owner._active_ray_analysis_records()))
    except Exception as exc:
        raise ReportFailed(str(exc)) from exc

    def detail_rows(key):
        """The hits of one path -- `key` is that record's index, as the tree nodes carry it."""
        if key is None or not 0 <= int(key) < len(records):
            return []
        hits = records[int(key)].get("hits", []) or []
        return [tuple(str(value) for value in owner._ray_hit_table_values(hit)) for hit in hits]

    return Report(
        title=TITLE,
        summary=summary_text(owner, len(records)),
        columns=COLUMNS,
        rows=records,
        tree=tuple(branch_tree_rows(owner, records)),
        tree_heading=TREE_HEADING,
        detail=DetailView(columns=hit_columns(owner), rows=detail_rows,
                          label="Hits along the path"),
        status=(f"{TITLE}: {len(records)} paths." if records else EMPTY),
    )


build_trace_path_report.TITLE = TITLE
