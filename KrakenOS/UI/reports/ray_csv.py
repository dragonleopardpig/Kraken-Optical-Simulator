"""The CSVs the ray and trace-path inspectors export (docs/design_qt_migration.md phase 4).

These two exports are not a table: each ray (or path) is flattened into ONE ROW PER HIT, under
~140 columns, and a ray with no hits still writes its own row. `Report.write_csv` cannot express
that, so the report carries a `csv_writer` and the model owns the file -- which is the point:
before this the flattening lived in the Tk dialog, so the Qt shell exported a different, much
smaller CSV for the same report.

The per-hit block is the same in both files but for `hit_branch`, which the trace-path CSV does
not need (its branch id is already a master column), so one function writes it.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from KrakenOS.UI.detector_aperture_analysis import DETECTOR_APERTURE_RECORD_STATUS_COLUMNS
from KrakenOS.UI.scene_builder import (RAY_ANALYSIS_CONTRACT_COLUMNS, RAY_EVENT_RECORD_COLUMNS,
                                       scene_bundle_ray_event_records)


#: the Ray Inspector CSV's fieldnames -- one row per hit, under the ray's own values
RAY_INSPECTOR_CSV_COLUMNS = (
    "ray_index",
    "source_ray_index",
    "source_id",
    "source_name",
    "source_role",
    "source_model",
    "source_x",
    "source_y",
    "source_z",
    "source_l",
    "source_m",
    "source_n",
    "source_power",
    "source_weight",
    "field_index",
    *RAY_ANALYSIS_CONTRACT_COLUMNS,
    "branch_id",
    "branch_path",
    "branch_power",
    "branch_phase_deg",
    "branch_jones_p_real",
    "branch_jones_p_imag",
    "branch_jones_s_real",
    "branch_jones_s_imag",
    "branch_pol_x_real",
    "branch_pol_x_imag",
    "branch_pol_y_real",
    "branch_pol_y_imag",
    "branch_pol_z_real",
    "branch_pol_z_imag",
    "branch_p_fraction",
    "branch_s_fraction",
    "branch_count",
    "status",
    "termination",
    "termination_diagnostic",
    "terminal_media",
    "terminal_index",
    "terminal_inside_volumes",
    "terminal_media_state",
    "branch_tree_diagnostic",
    "reaches_image",
    *DETECTOR_APERTURE_RECORD_STATUS_COLUMNS,
    "target_surface",
    "last_surface",
    "last_name",
    "ray_distance",
    "ray_op",
    "ray_top",
    "ray_transmission",
    "hit_step",
    "hit_event_id",
    "hit_event_kind",
    "hit_branch",
    "surface",
    "event",
    "hit_diagnostic",
    "name",
    "glass",
    "volume_id",
    "media_transition",
    "media_in",
    "media_out",
    "media_state_method",
    "media_state_diagnostic",
    "inside_volumes_before",
    "inside_volumes_after",
    "mesh_cell_id",
    "mesh_original_cell_id",
    "mesh_face_id",
    "mesh_face_match_method",
    "mesh_face_match_score",
    "mesh_face_match_warning",
    "x",
    "y",
    "z",
    "distance",
    "op",
    "l",
    "m",
    "n",
    "out_l",
    "out_m",
    "out_n",
    "normal_l",
    "normal_m",
    "normal_n",
    "gb_frame_valid",
    "gb_incidence_deg",
    "gb_k_l",
    "gb_k_m",
    "gb_k_n",
    "gb_t_l",
    "gb_t_m",
    "gb_t_n",
    "gb_s_l",
    "gb_s_m",
    "gb_s_n",
    "n0",
    "n1",
    "rp",
    "rs",
    "tp",
    "ts",
    "ttbe",
    "interaction_model",
    "interaction_target_surface",
    "interaction_in_power",
    "interaction_coeff",
    "interaction_out_power",
    "interaction_loss_power",
    "interaction_bulk",
)

#: the Trace Path Tree CSV's fieldnames
TRACE_PATH_CSV_COLUMNS = (
    "ray_index",
    "field_index",
    "branch_id",
    "branch_path",
    "parent_branch_id",
    "start_step",
    "end_step",
    "surface_path",
    "termination",
    "termination_diagnostic",
    "terminal_media",
    "terminal_index",
    "terminal_inside_volumes",
    "terminal_media_state",
    "branch_tree_diagnostic",
    "reaches_image",
    "hit_count",
    "branch_distance",
    "branch_op",
    "branch_transmission",
    "last_surface",
    "last_name",
    "hit_step",
    "hit_event_id",
    "hit_event_kind",
    "surface",
    "event",
    "hit_diagnostic",
    "name",
    "glass",
    "volume_id",
    "media_transition",
    "media_in",
    "media_out",
    "media_state_method",
    "media_state_diagnostic",
    "inside_volumes_before",
    "inside_volumes_after",
    "mesh_cell_id",
    "mesh_original_cell_id",
    "mesh_face_id",
    "mesh_face_match_method",
    "mesh_face_match_score",
    "mesh_face_match_warning",
    "x",
    "y",
    "z",
    "distance",
    "op",
    "l",
    "m",
    "n",
    "out_l",
    "out_m",
    "out_n",
    "normal_l",
    "normal_m",
    "normal_n",
    "gb_frame_valid",
    "gb_incidence_deg",
    "gb_k_l",
    "gb_k_m",
    "gb_k_n",
    "gb_t_l",
    "gb_t_m",
    "gb_t_n",
    "gb_s_l",
    "gb_s_m",
    "gb_s_n",
    "n0",
    "n1",
    "rp",
    "rs",
    "tp",
    "ts",
    "ttbe",
    "interaction_model",
    "interaction_target_surface",
    "interaction_in_power",
    "interaction_coeff",
    "interaction_out_power",
    "interaction_loss_power",
    "interaction_bulk",
)


def hit_fields(hit, *, include_branch: bool = True) -> dict:
    """One hit's own columns. `include_branch` is the single difference between the two files."""
    fields = {
        "hit_step": hit.get("step", ""),
        "hit_event_id": hit.get("event_id", ""),
        "hit_event_kind": hit.get("event_kind", ""),
        "hit_branch": hit.get("branch", ""),
        "surface": hit.get("surface", ""),
        "event": hit.get("event", ""),
        "hit_diagnostic": hit.get("diagnostic", ""),
        "name": hit.get("name", ""),
        "glass": hit.get("glass", ""),
        "volume_id": hit.get("volume_id", ""),
        "media_transition": hit.get("media_transition", ""),
        "media_in": hit.get("media_in", ""),
        "media_out": hit.get("media_out", ""),
        "media_state_method": hit.get("media_state_method", ""),
        "media_state_diagnostic": hit.get("media_state_diagnostic", ""),
        "inside_volumes_before": hit.get("inside_volumes_before", ""),
        "inside_volumes_after": hit.get("inside_volumes_after", ""),
        "mesh_cell_id": hit.get("mesh_cell_id", ""),
        "mesh_original_cell_id": hit.get("mesh_original_cell_id", ""),
        "mesh_face_id": hit.get("mesh_face_id", ""),
        "mesh_face_match_method": hit.get("mesh_face_match_method", ""),
        "mesh_face_match_score": hit.get("mesh_face_match_score", ""),
        "mesh_face_match_warning": hit.get("mesh_face_match_warning", ""),
        "x": hit.get("x", ""),
        "y": hit.get("y", ""),
        "z": hit.get("z", ""),
        "distance": hit.get("distance", ""),
        "op": hit.get("op", ""),
        "l": hit.get("l", ""),
        "m": hit.get("m", ""),
        "n": hit.get("n", ""),
        "out_l": hit.get("out_l", ""),
        "out_m": hit.get("out_m", ""),
        "out_n": hit.get("out_n", ""),
        "normal_l": hit.get("normal_l", ""),
        "normal_m": hit.get("normal_m", ""),
        "normal_n": hit.get("normal_n", ""),
        "gb_frame_valid": hit.get("gb_frame_valid", ""),
        "gb_incidence_deg": hit.get("gb_incidence_deg", ""),
        "gb_k_l": hit.get("gb_k_l", ""),
        "gb_k_m": hit.get("gb_k_m", ""),
        "gb_k_n": hit.get("gb_k_n", ""),
        "gb_t_l": hit.get("gb_t_l", ""),
        "gb_t_m": hit.get("gb_t_m", ""),
        "gb_t_n": hit.get("gb_t_n", ""),
        "gb_s_l": hit.get("gb_s_l", ""),
        "gb_s_m": hit.get("gb_s_m", ""),
        "gb_s_n": hit.get("gb_s_n", ""),
        "n0": hit.get("n0", ""),
        "n1": hit.get("n1", ""),
        "rp": hit.get("rp", ""),
        "rs": hit.get("rs", ""),
        "tp": hit.get("tp", ""),
        "ts": hit.get("ts", ""),
        "ttbe": hit.get("ttbe", ""),
        "interaction_model": hit.get("interaction_model", ""),
        "interaction_target_surface": hit.get("interaction_target_surface", ""),
        "interaction_in_power": hit.get("interaction_in_power", ""),
        "interaction_coeff": hit.get("interaction_coeff", ""),
        "interaction_out_power": hit.get("interaction_out_power", ""),
        "interaction_loss_power": hit.get("interaction_loss_power", ""),
        "interaction_bulk": hit.get("interaction_bulk", ""),
    }
    if not include_branch:
        fields.pop("hit_branch", None)
    return fields


def ray_inspector_csv_rows(owner, records):
    """Every ray's row(s): one per hit, or one bare row when the ray never hit anything."""
    for record in records:
        aperture_record = owner._ray_detector_aperture_record(record)
        base = {
            "ray_index": record.get("ray_index", ""),
            "source_ray_index": record.get("source_ray_index", ""),
            "source_id": record.get("source_id", ""),
            "source_name": record.get("source_name", ""),
            "source_role": record.get("source_role", ""),
            "source_model": record.get("source_model", ""),
            "source_x": record.get("source_x", ""),
            "source_y": record.get("source_y", ""),
            "source_z": record.get("source_z", ""),
            "source_l": record.get("source_l", ""),
            "source_m": record.get("source_m", ""),
            "source_n": record.get("source_n", ""),
            "source_power": record.get("source_power", ""),
            "source_weight": record.get("source_weight", ""),
            "field_index": record.get("field_index", ""),
            **{
                column: record.get(column, "")
                for column in RAY_ANALYSIS_CONTRACT_COLUMNS
            },
            "branch_id": record.get("branch_id", ""),
            "branch_path": record.get("branch_path", ""),
            "branch_power": record.get("branch_power", ""),
            "branch_phase_deg": record.get("branch_phase", ""),
            "branch_jones_p_real": owner._safe_complex(record.get("branch_jones_p", 0.0), 0.0).real,
            "branch_jones_p_imag": owner._safe_complex(record.get("branch_jones_p", 0.0), 0.0).imag,
            "branch_jones_s_real": owner._safe_complex(record.get("branch_jones_s", 0.0), 0.0).real,
            "branch_jones_s_imag": owner._safe_complex(record.get("branch_jones_s", 0.0), 0.0).imag,
            "branch_pol_x_real": float(np.asarray(record.get("branch_polarization_xyz", [0, 0, 0]), dtype=np.complex128).reshape(-1)[0].real),
            "branch_pol_x_imag": float(np.asarray(record.get("branch_polarization_xyz", [0, 0, 0]), dtype=np.complex128).reshape(-1)[0].imag),
            "branch_pol_y_real": float(np.asarray(record.get("branch_polarization_xyz", [0, 0, 0]), dtype=np.complex128).reshape(-1)[1].real),
            "branch_pol_y_imag": float(np.asarray(record.get("branch_polarization_xyz", [0, 0, 0]), dtype=np.complex128).reshape(-1)[1].imag),
            "branch_pol_z_real": float(np.asarray(record.get("branch_polarization_xyz", [0, 0, 0]), dtype=np.complex128).reshape(-1)[2].real),
            "branch_pol_z_imag": float(np.asarray(record.get("branch_polarization_xyz", [0, 0, 0]), dtype=np.complex128).reshape(-1)[2].imag),
            "branch_p_fraction": record.get("branch_p_fraction", ""),
            "branch_s_fraction": record.get("branch_s_fraction", ""),
            "branch_count": record.get("branch_count", ""),
            "status": record.get("status", ""),
            "termination": record.get("termination", ""),
            "termination_diagnostic": record.get("termination_diagnostic", ""),
            "terminal_media": record.get("terminal_media", ""),
            "terminal_index": record.get("terminal_index", ""),
            "terminal_inside_volumes": record.get("terminal_inside_volumes", ""),
            "terminal_media_state": record.get("terminal_media_state", ""),
            "branch_tree_diagnostic": record.get("branch_tree_diagnostic", ""),
            "reaches_image": record.get("reaches_image", ""),
            **{
                column: aperture_record.get(column, "")
                for column in DETECTOR_APERTURE_RECORD_STATUS_COLUMNS
            },
            "target_surface": record.get("target_surface", ""),
            "last_surface": record.get("last_surface", ""),
            "last_name": record.get("last_name", ""),
            "ray_distance": record.get("distance", ""),
            "ray_op": record.get("op", ""),
            "ray_top": record.get("top", ""),
            "ray_transmission": record.get("transmission", ""),
        }
        hits = list(record.get("hits", []) or [])
        if not hits:
            yield base
            continue
        for hit in hits:
            row = dict(base)
            row.update(hit_fields(hit))
            yield row


def trace_path_csv_rows(owner, records):
    """Every path's row(s), the same way."""
    for record in records:
        base = {
            "ray_index": record.get("ray_index", ""),
            "field_index": record.get("field_index", ""),
            "branch_id": record.get("branch_id", ""),
            "branch_path": record.get("branch_path", ""),
            "parent_branch_id": record.get("parent_branch_id", ""),
            "start_step": record.get("start_step", ""),
            "end_step": record.get("end_step", ""),
            "surface_path": record.get("surface_path", ""),
            "termination": record.get("termination", ""),
            "termination_diagnostic": record.get("termination_diagnostic", ""),
            "terminal_media": record.get("terminal_media", ""),
            "terminal_index": record.get("terminal_index", ""),
            "terminal_inside_volumes": record.get("terminal_inside_volumes", ""),
            "terminal_media_state": record.get("terminal_media_state", ""),
            "branch_tree_diagnostic": record.get("branch_tree_diagnostic", ""),
            "reaches_image": record.get("reaches_image", ""),
            "hit_count": record.get("hit_count", ""),
            "branch_distance": record.get("distance", ""),
            "branch_op": record.get("op", ""),
            "branch_transmission": record.get("transmission", ""),
            "last_surface": record.get("last_surface", ""),
            "last_name": record.get("last_name", ""),
        }
        hits = list(record.get("hits", []) or [])
        if not hits:
            yield base
            continue
        for hit in hits:
            row = dict(base)
            row.update(hit_fields(hit, include_branch=False))
            yield row


def _write(path, columns, rows) -> Path:
    """Write `rows` under `columns`.

    No ``extrasaction="ignore"``, on purpose: a row carrying a key these columns do not declare
    is a mismatch between the two, and DictWriter saying so is the whole value of finding out.
    """
    path = Path(path)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def write_ray_inspector_csv(owner, records, path) -> Path:
    return _write(path, RAY_INSPECTOR_CSV_COLUMNS, ray_inspector_csv_rows(owner, records))


def write_trace_path_csv(owner, records, path) -> Path:
    return _write(path, TRACE_PATH_CSV_COLUMNS, trace_path_csv_rows(owner, records))


def ray_event_records(owner) -> list:
    """The canonical ray-event records, tracing first if the scene bundle is not there yet."""
    bundle = owner._last_scene_bundle
    if bundle is None:
        owner._collect_ray_analysis_records()
        bundle = owner._last_scene_bundle
    return list(scene_bundle_ray_event_records(bundle)) if bundle is not None else []


def write_ray_events_csv(records, path) -> Path:
    return _write(path, RAY_EVENT_RECORD_COLUMNS,
                  ({column: record.get(column, "") for column in RAY_EVENT_RECORD_COLUMNS}
                   for record in records))
