"""Optical CAD/STL solid diagnostics as a `Report` (docs/design_qt_migration.md phase 5g, bugs/0936).

"Inspect Optical CAD/STL Solids" checks every row that carries a ``Solid_3d_stl`` mesh: can it be
traced (triangles, closed, manifold, no degenerate faces, outward winding), how big is it, and which
CAD file it came from. The Tk dialog was a text box filled inside its own method; the text is built
here now, one record per solid, and both shells render the same report -- a table of solids with
each one's full diagnostics as its detail, and the whole text for Copy.
"""
from __future__ import annotations

from KrakenOS.UI.reports.base import DetailText, Report, ReportColumn, ReportFailed

TITLE = "Optical CAD/STL Solid Diagnostics"
NO_SOLIDS = "No rows contain Solid_3d_stl."

COLUMNS = (
    ReportColumn("row", "Row", numeric=False, width=50),
    ReportColumn("name", "Name", numeric=False, width=180),
    ReportColumn("status", "Status", numeric=False, width=70),
    ReportColumn("triangles", "Triangles", width=80),
    ReportColumn("boundary_edges", "Open edges", width=80),
    ReportColumn("nonmanifold_edges", "Non-manifold", width=90),
    ReportColumn("winding", "Winding", numeric=False, width=80),
    ReportColumn("file", "Mesh file", numeric=False, width=240, stretch=True),
)


def optical_solid_diagnostic_records(owner) -> list[dict]:
    """One record per row with a ``Solid_3d_stl`` mesh, with its diagnostics text in ``text``.

    ``owner`` is the editor, or a panel that forwards to it: the rows as they stand, the scene
    graph's "is a value present" rule and the row's resolved STL path are the editor's own."""
    from KrakenOS.UI.stl_geometry import format_stl_mesh_diagnostics, inspect_stl_mesh

    records: list[dict] = []
    for index, row in enumerate(owner.rows):
        advanced = row.advanced or {}
        if not isinstance(advanced, dict) or not owner._scene_graph_value_present(advanced.get("Solid_3d_stl")):
            continue
        header = f"S{index}: {row.name or row.surface}"
        record = {"row": f"S{index}", "row_index": index, "name": str(row.name or row.surface),
                  "triangles": None, "boundary_edges": None, "nonmanifold_edges": None,
                  "winding": "", "file": ""}
        path = owner._stl_path_from_row(row)
        if path is None:
            record.update(status="CHECK", text="\n".join([
                header, "Status: CHECK",
                "This row uses an in-memory/non-file Solid_3d_stl object. File topology diagnostics are unavailable."]))
            records.append(record)
            continue
        report = inspect_stl_mesh(path)
        text = header + "\n" + format_stl_mesh_diagnostics(report)
        source_path = str(advanced.get("OpticalSolidSourcePath", "") or "").strip()
        if source_path:
            source_format = str(advanced.get("OpticalSolidSourceFormat", "") or "").strip()
            text += f"\n\nOriginal CAD source{f' ({source_format})' if source_format else ''}: {source_path}"
        # the table's Status is the text's own "Status:" line (format_stl_mesh_diagnostics' rule)
        record.update(status="READY" if report.is_trace_ready else "CHECK",
                      triangles=int(report.triangle_count), boundary_edges=int(report.boundary_edge_count),
                      nonmanifold_edges=int(report.nonmanifold_edge_count), winding=str(report.winding),
                      file=str(path), text=text)
        records.append(record)
    return records


def optical_solid_diagnostics_text(owner) -> str:
    """The whole report as text (what Copy puts on the clipboard); "" when no row has a solid."""
    return "\n\n".join(record["text"] for record in optical_solid_diagnostic_records(owner))


def build_optical_solid_diagnostics_report(owner) -> Report:
    """The diagnostics report for ``owner``'s layout; `ReportFailed` when no row has a solid."""
    records = optical_solid_diagnostic_records(owner)
    if not records:
        raise ReportFailed(NO_SOLIDS)
    ready = sum(1 for record in records if record["status"] == "READY")
    summary = f"{len(records)} optical CAD/STL solid(s): {ready} trace-ready, {len(records) - ready} to check."
    return Report(
        title=TITLE,
        summary=summary,
        columns=COLUMNS,
        rows=records,
        text="\n\n".join(record["text"] for record in records).strip() + "\n",
        detail_text=DetailText(text=lambda index: records[int(index)]["text"], label="Diagnostics",
                               empty="Select a solid to see its diagnostics.", height=14),
        status=summary,
    )


build_optical_solid_diagnostics_report.TITLE = TITLE
