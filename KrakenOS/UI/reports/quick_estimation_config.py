"""Quick Estimation's configuration table (bugs/0953; docs/design_qt_migration.md phase 3).

Sixteen focused conjugates of the scene's lens: the object distance swept from 1.25 f to 5 f, the
image distance solved for focus at each, with the magnification, field of view and working distance
that result. The sweep moves the two real thickness rows and puts them back; both the Tk window
and the shell's report dialog show what `conjugate_records` returns.
"""
from __future__ import annotations

from KrakenOS.UI.reports.base import Report, ReportColumn, ReportFailed

TITLE = "Quick Estimation — configuration table"
COLUMNS = (
    ReportColumn("object_distance", "Object dist [mm]", width=120, align="c"),
    ReportColumn("image_distance", "Image dist [mm]", width=120, align="c"),
    ReportColumn("magnification", "Mag |m|", width=120, align="c"),
    ReportColumn("fov_full", "FOV full [mm]", width=120, align="c"),
    ReportColumn("working_distance", "Working dist [mm]", width=120, align="c"),
    ReportColumn("real_image", "Real image?", numeric=False, width=120, align="c"),
)
STEPS = 16


def conjugate_records(inspector) -> "tuple[float, float, list]":
    """(focal length, sensor semi-height, one record per conjugate). Raises `ReportFailed` when the
    scene has no usable lens + sensor; returns no records when it has no object / image gap."""
    import numpy as np

    qe = inspector._quick_estimation_service()
    focal = qe.focal_length()
    sensor = qe._sensor_semi()
    if not focal or not sensor:
        raise ReportFailed("Configuration table needs a valid lens + sensor.")
    rows = inspector.editor.rows
    obj_row = qe.object_thickness_row()
    img_row = qe.image_thickness_row()
    if obj_row is None or img_row is None:
        return float(focal), float(sensor), []
    saved = (float(rows[obj_row].thickness), float(rows[img_row].thickness))
    records = []
    try:
        for distance in np.linspace(focal * 1.25, focal * 5.0, STEPS):
            rows[obj_row].thickness = float(distance)
            qe.solve_dependent(obj_row)
            state = qe.current_state()
            records.append({
                "object_distance": float(distance),
                "image_distance": state.get("image_distance"),
                "magnification": state.get("magnification"),
                "fov_full": state.get("fov_full"),
                "working_distance": state.get("working_distance"),
                "real_image": not state.get("forbidden"),
            })
    finally:
        rows[obj_row].thickness, rows[img_row].thickness = saved
        try:
            qe.update_readout()
        except Exception:
            pass
    return float(focal), float(sensor), records


def summary_text(focal: float, sensor: float) -> str:
    return (f"Fixed lens f={focal:.4g} mm, sensor semi-height {sensor:.4g} mm. "
            "Each row is a focused conjugate; drag toward the one you want.")


def display_row(record: dict) -> tuple:
    """One record as the table shows it -- the cells of both views."""
    def number(value, digits: int) -> str:
        return f"{value:.{digits}g}" if value is not None else "--"

    magnification = record.get("magnification")
    return (
        number(record.get("object_distance"), 5),
        number(record.get("image_distance"), 5),
        f"{abs(magnification):.4g}" if magnification is not None else "--",
        number(record.get("fov_full"), 5),
        number(record.get("working_distance"), 5),
        "yes" if record.get("real_image") else "NO (WD<FL)",
    )


def build_quick_estimation_config_report(inspector) -> Report:
    focal, sensor, records = conjugate_records(inspector)
    return Report(
        title=TITLE,
        summary=summary_text(focal, sensor),
        columns=COLUMNS,
        rows=records,
        display_rows=[display_row(record) for record in records],
        status=f"Configuration table: {len(records)} focused conjugates of the f={focal:.4g} mm lens.",
    )
