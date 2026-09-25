"""The Trace Path Inspector (docs/design_qt_migration.md phase 3).

A master TREE of rays and the paths beneath them, with the hits of the selected path in the detail
view. The tree itself is built by `reports/branch_tree_tables.py`; the hits come from the editor's
own `_ray_hit_table_values`, as everywhere else in this family.
"""
from __future__ import annotations

from KrakenOS.UI.reports.base import DetailView, Report, ReportAction, ReportFailed
from KrakenOS.UI.reports.branch_tree_tables import (
    COLUMNS,
    EMPTY,
    RAY_KEY_PREFIX,
    TITLE,
    TREE_HEADING,
    branch_tree_rows,
    summary_text,
)
from KrakenOS.UI.reports.ray_csv import write_trace_path_csv
from KrakenOS.UI.reports.ray_tables import hit_columns


def selected_ray_index(key) -> "int | None":
    """The ray a tree key belongs to -- a ray node's own, or the ray of a path record."""
    if key is None:
        return None
    text = str(key)
    if text.startswith(RAY_KEY_PREFIX):
        try:
            return int(text[len(RAY_KEY_PREFIX):])
        except ValueError:
            return None
    return None


def build_trace_path_report(owner) -> Report:
    """Every traced path, nested under the ray it came from."""
    try:
        records = list(owner._collect_branch_tree_records(
            ray_records=owner._active_ray_analysis_records()))
    except Exception as exc:
        raise ReportFailed(str(exc)) from exc

    def _hits(hits):
        return [tuple(str(value) for value in owner._ray_hit_table_values(hit)) for hit in hits]

    def detail_rows(key):
        """The hits of one path, or of EVERY path of a ray when a ray node is selected."""
        ray_index = selected_ray_index(key)
        if ray_index is not None:
            hits = []
            for record in records:
                if int(record.get("ray_index", -1)) == ray_index:
                    hits.extend(list(record.get("hits", []) or []))
            return _hits(hits)
        if key is None or not 0 <= int(key) < len(records):
            return []
        return _hits(records[int(key)].get("hits", []) or [])

    def open_ray(key) -> str:
        """Show the selected ray in the Ray Inspector -- from a ray node or a path node."""
        ray_index = selected_ray_index(key)
        if ray_index is None:
            if key is None or not 0 <= int(key) < len(records):
                return ""
            ray_index = int(records[int(key)].get("ray_index", -1))
        if ray_index < 0:
            return ""
        owner._select_ray_inspector_ray(int(ray_index))
        return f"Ray {ray_index} shown in the Ray Inspector."

    return Report(
        title=TITLE,
        summary=summary_text(owner, len(records)),
        columns=COLUMNS,
        rows=records,
        tree=tuple(branch_tree_rows(owner, records)),
        tree_heading=TREE_HEADING,
        detail=DetailView(columns=hit_columns(owner), rows=detail_rows,
                          label="Hits along the path"),
        actions=(ReportAction("Open Ray", open_ray, needs_selection=True),),
        csv_writer=lambda path: write_trace_path_csv(owner, records, path),
        status=(f"{TITLE}: {len(records)} paths." if records else EMPTY),
    )


build_trace_path_report.TITLE = TITLE
