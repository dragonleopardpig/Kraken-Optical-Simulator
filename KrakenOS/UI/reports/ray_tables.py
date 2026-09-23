"""The ray inspector's tables (docs/design_qt_migration.md phase 3).

Inside the reports package on purpose: it declares `ReportColumn`s, and a module OUTSIDE the
package that imports `reports.base` makes a cycle -- importing it first runs the package's
__init__, which imports the builder, which imports this module while it is still initialising.

The fourth dialog family: MASTER/DETAIL -- a list of rays, and the hits of whichever ray is
selected. The detail side was already shared (`_ray_hit_table_specs` / `_ray_hit_table_values` on
the editor); the master side was formatted inline inside the Tk refresh, and is extracted here so
both toolkits fill their tables from one function.
"""
from __future__ import annotations

from KrakenOS.UI.reports.base import ReportColumn

RAY_TITLE = "Ray Inspector"
PATH_TITLE = "Trace Path Inspector"
EMPTY = "No trace data. Click Update."

#: (key, heading, width, anchor) exactly as the Tk ray table declares them
RAY_LAYOUT = (
    ("ray", "Ray", 60, "center"), ("source", "Source", 120, "w"),
    ("field", "Field", 70, "center"), ("branch", "Leaf", 70, "center"),
    ("path", "Trace path", 180, "w"), ("power", "Power", 72, "e"),
    ("pfrac", "P frac", 62, "e"), ("branches", "Paths", 76, "center"),
    ("status", "Status", 120, "w"), ("aperture", "Detector aperture", 120, "w"),
    ("aperture_margin", "Miss [mm]", 82, "e"), ("termination", "Termination", 140, "w"),
    ("terminal_media", "Terminal media", 120, "w"), ("terminal_index", "n", 82, "e"),
    ("terminal_inside", "Inside", 130, "w"), ("diagnostic", "Diagnostic", 180, "w"),
    ("hits", "Hits", 60, "center"), ("last_surface", "Last surface", 130, "w"),
    ("target", "Target", 70, "center"), ("distance", "Distance", 90, "e"),
    ("op", "OP [mm]", 90, "e"), ("tt", "TT", 70, "e"),
)

STRETCH = {"path", "status", "termination", "diagnostic", "last_surface"}


def _columns(layout) -> tuple[ReportColumn, ...]:
    return tuple(
        ReportColumn(key, heading, numeric=anchor != "w", width=width,
                     stretch=key in STRETCH,
                     align={"w": "l", "center": "c", "e": "r"}.get(anchor, ""))
        for key, heading, width, anchor in layout
    )


RAY_COLUMNS = _columns(RAY_LAYOUT)


def source_text(record) -> str:
    """"name:index" when the ray came from a named source, else just the index."""
    name = str(record.get("source_name", "") or record.get("source_id", "") or "").strip()
    return (f"{name}:{int(record['source_ray_index'])}" if name
            else str(int(record["source_ray_index"])))


def last_surface_text(record) -> str:
    surface = record["last_surface"]
    text = f"S{surface}" if surface is not None else "-"
    name = str(record["last_name"]).strip()
    return f"{text}  {name}" if name else text


def ray_table_values(owner, record) -> tuple:
    """One master row, exactly as the Tk ray table inserts it."""
    show = owner._format_ray_inspector_value
    aperture_text, aperture_margin = owner._ray_detector_aperture_table_values(record)
    return (
        int(record["ray_index"]),
        source_text(record),
        int(record["field_index"]),
        int(record["branch_id"]),
        str(record.get("branch_path", "") or ""),
        show(record.get("branch_power")),
        show(record.get("branch_p_fraction")),
        int(record["branch_count"]),
        str(record["status"]),
        aperture_text,
        aperture_margin,
        str(record["termination"]),
        str(record.get("terminal_media", "") or ""),
        show(record.get("terminal_index")),
        str(record.get("terminal_inside_volumes", "") or ""),
        str(record.get("termination_diagnostic", "")
            or record.get("branch_tree_diagnostic", "") or ""),
        int(record["hit_count"]),
        last_surface_text(record),
        show(record["target_surface"]),
        show(record["distance"]),
        show(record["op"]),
        show(record["transmission"]),
    )


def hit_columns(owner) -> tuple[ReportColumn, ...]:
    """The detail table's columns, from the editor's own specs: (key, heading, width, anchor,
    stretch)."""
    return tuple(
        ReportColumn(str(key), str(heading), numeric=anchor != "w", width=int(width),
                     stretch=bool(stretch),
                     align={"w": "l", "center": "c", "e": "r"}.get(str(anchor), ""))
        for key, heading, width, anchor, stretch in owner._ray_hit_table_specs()
    )


def summary_text(owner, record_count: int, *, label: str = "rays") -> str:
    """The Tk ray inspector's own summary line, from the editor's trace preview summary."""
    summary = owner._trace_preview_summary()
    if not summary["total_rays"]:
        return EMPTY
    text = ("{requested} -> {active} | backend={backend} | rays={total} | "
            "image hits={hits}/{total} | stopped={stopped}").format(
        requested=summary["requested"], active=summary["active"],
        backend=summary["backend"], total=summary["total_rays"],
        hits=summary["image_hits"], stopped=summary["stopped_rays"])
    note = str(summary.get("note", "")).strip()
    return f"{text} | {note}" if note else text
