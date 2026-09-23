"""The Ray Inspector (docs/design_qt_migration.md phase 3).

The MASTER/DETAIL family: a list of rays, and the hits of whichever one is selected. Both sides
come from the model -- `ray_inspector_tables.ray_table_values` for the master rows and the
editor's own `_ray_hit_table_values` for the detail -- so the two toolkits fill their tables from
one function.

The **Trace Path Inspector** is deliberately not here. Its records are branch-tree records, not
ray records, and its Tk view is a HIERARCHY -- rays with their paths nested underneath -- which a
table cannot show. It needs a QTreeView and a tree model: the fifth dialog family, not this one.
"""
from __future__ import annotations

from KrakenOS.UI.reports.ray_tables import (
    EMPTY,
    RAY_COLUMNS,
    RAY_TITLE,
    hit_columns,
    ray_table_values,
    summary_text,
)
from KrakenOS.UI.reports.base import DetailView, Report, ReportFailed


def _detail(owner, records) -> DetailView:
    """The hits of master row ``index``, formatted by the editor's own value function."""

    def rows(index: int):
        if not 0 <= index < len(records):
            return []
        hits = records[index].get("hits", []) or []
        return [tuple(str(value) for value in owner._ray_hit_table_values(hit)) for hit in hits]

    return DetailView(columns=hit_columns(owner), rows=rows, label="Hits along the ray")


def _report(owner, records, title, label) -> Report:
    return Report(
        title=title,
        summary=summary_text(owner, len(records), label=label),
        columns=RAY_COLUMNS,
        rows=list(records),
        display_rows=[tuple(str(value) for value in ray_table_values(owner, record))
                      for record in records],
        detail=_detail(owner, list(records)),
        text="",
        status=(f"{title}: {len(records)} {label}." if records else EMPTY),
    )


def build_ray_inspector_report(owner) -> Report:
    """Every traced ray, with its hits."""
    try:
        records = list(owner._collect_ray_analysis_records())
    except Exception as exc:
        raise ReportFailed(str(exc)) from exc
    return _report(owner, records, RAY_TITLE, "rays")


build_ray_inspector_report.TITLE = RAY_TITLE
