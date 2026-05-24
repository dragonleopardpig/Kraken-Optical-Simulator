"""Ray Inspector and Trace Path Inspector dialogs."""

from __future__ import annotations

import csv
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

import numpy as np

from KrakenOS.UI.detector_aperture_analysis import DETECTOR_APERTURE_RECORD_STATUS_COLUMNS
from KrakenOS.UI.scene_builder import (
    RAY_ANALYSIS_CONTRACT_COLUMNS,
    RAY_EVENT_RECORD_COLUMNS,
    scene_bundle_ray_event_records,
)


class MainRayTraceInspectorDialogs:
    """Own ray and trace-path inspector windows while delegating trace data to the editor."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_ray_inspector(self) -> None:
        window = self._ray_inspector_window
        if window is not None and window.winfo_exists():
            self._refresh_ray_inspector()
            window.deiconify()
            window.lift()
            window.focus_force()
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title("Ray Inspector")
        window.geometry("1180x660")
        window.minsize(780, 420)
        window.transient(self.editor)
        window.protocol("WM_DELETE_WINDOW", self._close_ray_inspector)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(window, padding=(8, 8, 8, 0))
        toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Button(toolbar, text="Refresh", command=self._refresh_ray_inspector).pack(side="left")
        ttk.Button(toolbar, text="Export CSV", command=self.export_ray_inspector_csv).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Export Events CSV", command=self.export_ray_events_csv).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Close", command=self._close_ray_inspector).pack(side="left", padx=(6, 0))

        self._ray_inspector_summary_var = tk.StringVar(master=window, value="No trace data. Click Update.")
        ttk.Label(
            window,
            textvariable=self._ray_inspector_summary_var,
            padding=(8, 6, 8, 0),
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="ew")

        panes = ttk.Panedwindow(window, orient=tk.VERTICAL)
        panes.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)
        window.rowconfigure(2, weight=1)

        rays_frame = ttk.LabelFrame(panes, text="Preview rays", padding=6)
        rays_frame.columnconfigure(0, weight=1)
        rays_frame.rowconfigure(0, weight=1)
        panes.add(rays_frame, weight=2)

        hits_frame = ttk.LabelFrame(panes, text="Surface hits", padding=6)
        hits_frame.columnconfigure(0, weight=1)
        hits_frame.rowconfigure(0, weight=1)
        panes.add(hits_frame, weight=3)

        ray_columns = (
            "ray",
            "source",
            "field",
            "branch",
            "path",
            "power",
            "pfrac",
            "branches",
            "status",
            "aperture",
            "aperture_margin",
            "termination",
            "terminal_media",
            "terminal_index",
            "terminal_inside",
            "diagnostic",
            "hits",
            "last_surface",
            "target",
            "distance",
            "op",
            "tt",
        )
        ray_table = ttk.Treeview(rays_frame, columns=ray_columns, show="headings", selectmode="browse")
        ray_table.heading("ray", text="Ray")
        ray_table.heading("source", text="Source")
        ray_table.heading("field", text="Field")
        ray_table.heading("branch", text="Leaf")
        ray_table.heading("path", text="Trace path")
        ray_table.heading("power", text="Power")
        ray_table.heading("pfrac", text="P frac")
        ray_table.heading("branches", text="Paths")
        ray_table.heading("status", text="Status")
        ray_table.heading("aperture", text="Detector aperture")
        ray_table.heading("aperture_margin", text="Miss [mm]")
        ray_table.heading("termination", text="Termination")
        ray_table.heading("terminal_media", text="Terminal medium")
        ray_table.heading("terminal_index", text="Terminal n")
        ray_table.heading("terminal_inside", text="Terminal inside")
        ray_table.heading("diagnostic", text="Diagnostic")
        ray_table.heading("hits", text="Hits")
        ray_table.heading("last_surface", text="Last")
        ray_table.heading("target", text="Target")
        ray_table.heading("distance", text="Dist [mm]")
        ray_table.heading("op", text="OP [mm]")
        ray_table.heading("tt", text="TT")
        ray_table.column("ray", width=60, anchor="center", stretch=False)
        ray_table.column("source", width=120, anchor="w", stretch=False)
        ray_table.column("field", width=70, anchor="center", stretch=False)
        ray_table.column("branch", width=70, anchor="center", stretch=False)
        ray_table.column("path", width=180, anchor="w", stretch=True)
        ray_table.column("power", width=72, anchor="e", stretch=False)
        ray_table.column("pfrac", width=62, anchor="e", stretch=False)
        ray_table.column("branches", width=76, anchor="center", stretch=False)
        ray_table.column("status", width=120, anchor="w", stretch=True)
        ray_table.column("aperture", width=120, anchor="w", stretch=False)
        ray_table.column("aperture_margin", width=82, anchor="e", stretch=False)
        ray_table.column("termination", width=140, anchor="w", stretch=True)
        ray_table.column("terminal_media", width=120, anchor="w", stretch=False)
        ray_table.column("terminal_index", width=82, anchor="e", stretch=False)
        ray_table.column("terminal_inside", width=130, anchor="w", stretch=False)
        ray_table.column("diagnostic", width=180, anchor="w", stretch=True)
        ray_table.column("hits", width=60, anchor="center", stretch=False)
        ray_table.column("last_surface", width=130, anchor="w", stretch=True)
        ray_table.column("target", width=70, anchor="center", stretch=False)
        ray_table.column("distance", width=90, anchor="e", stretch=False)
        ray_table.column("op", width=90, anchor="e", stretch=False)
        ray_table.column("tt", width=70, anchor="e", stretch=False)
        ray_table.grid(row=0, column=0, sticky="nsew")
        ray_scroll = ttk.Scrollbar(rays_frame, orient="vertical", command=ray_table.yview)
        ray_scroll.grid(row=0, column=1, sticky="ns")
        ray_x_scroll = ttk.Scrollbar(rays_frame, orient="horizontal", command=ray_table.xview)
        ray_x_scroll.grid(row=1, column=0, sticky="ew")
        ray_table.configure(yscrollcommand=ray_scroll.set, xscrollcommand=ray_x_scroll.set)
        ray_table.bind("<<TreeviewSelect>>", self._populate_ray_inspector_hits, add="+")

        hit_specs = self._ray_hit_table_specs()
        hit_columns = tuple(spec[0] for spec in hit_specs)
        hit_table = ttk.Treeview(hits_frame, columns=hit_columns, show="headings", selectmode="none")
        for column, heading, width, anchor, stretch in hit_specs:
            hit_table.heading(column, text=heading)
            hit_table.column(column, width=width, anchor=anchor, stretch=stretch)
        hit_table.grid(row=0, column=0, sticky="nsew")
        hit_scroll = ttk.Scrollbar(hits_frame, orient="vertical", command=hit_table.yview)
        hit_scroll.grid(row=0, column=1, sticky="ns")
        hit_x_scroll = ttk.Scrollbar(hits_frame, orient="horizontal", command=hit_table.xview)
        hit_x_scroll.grid(row=1, column=0, sticky="ew")
        hit_table.configure(yscrollcommand=hit_scroll.set, xscrollcommand=hit_x_scroll.set)

        self._ray_inspector_window = window
        self._ray_inspector_ray_table = ray_table
        self._ray_inspector_hit_table = hit_table
        self._show_centered_dialog(window)
        self._refresh_ray_inspector()

    def _close_ray_inspector(self) -> None:
        window = self._ray_inspector_window
        self._ray_inspector_window = None
        self._ray_inspector_summary_var = None
        self._ray_inspector_ray_table = None
        self._ray_inspector_hit_table = None
        self._ray_inspector_records = []
        if window is not None and window.winfo_exists():
            window.destroy()

    def _refresh_ray_inspector_if_open(self) -> None:
        window = self._ray_inspector_window
        if window is None:
            return
        if not window.winfo_exists():
            self._close_ray_inspector()
            return
        self._refresh_ray_inspector()

    def _refresh_ray_inspector(self) -> None:
        ray_table = self._ray_inspector_ray_table
        hit_table = self._ray_inspector_hit_table
        if ray_table is None or hit_table is None:
            return
        records = self._collect_ray_analysis_records()
        self._ray_inspector_records = records
        summary = self._trace_preview_summary()
        if self._ray_inspector_summary_var is not None:
            if summary["total_rays"]:
                self._ray_inspector_summary_var.set(
                    "{requested} -> {active} | backend={backend} | rays={total} | image hits={hits}/{total} | stopped={stopped}".format(
                        requested=summary["requested"],
                        active=summary["active"],
                        family=summary["family"],
                        backend=summary["backend"],
                        total=summary["total_rays"],
                        hits=summary["image_hits"],
                        stopped=summary["stopped_rays"],
                    )
                )
                note = str(summary.get("note", "")).strip()
                if note:
                    self._ray_inspector_summary_var.set(f"{self._ray_inspector_summary_var.get()} | {note}")
            else:
                self._ray_inspector_summary_var.set("No trace data. Click Update.")

        selected = ray_table.selection()
        selected_iid = selected[0] if selected else None
        ray_table.delete(*ray_table.get_children())
        hit_table.delete(*hit_table.get_children())
        for record in records:
            ray_index = int(record["ray_index"])
            source_text = str(record.get("source_name", "") or record.get("source_id", "") or "").strip()
            if source_text:
                source_text = f"{source_text}:{int(record['source_ray_index'])}"
            else:
                source_text = str(int(record["source_ray_index"]))
            last_name = str(record["last_name"]).strip()
            last_surface = record["last_surface"]
            last_text = f"S{last_surface}" if last_surface is not None else "-"
            if last_name:
                last_text = f"{last_text}  {last_name}"
            aperture_text, aperture_margin = self._ray_detector_aperture_table_values(record)
            ray_table.insert(
                "",
                "end",
                iid=str(ray_index),
                values=(
                    ray_index,
                    source_text,
                    int(record["field_index"]),
                    int(record["branch_id"]),
                    str(record.get("branch_path", "") or ""),
                    self._format_ray_inspector_value(record.get("branch_power")),
                    self._format_ray_inspector_value(record.get("branch_p_fraction")),
                    int(record["branch_count"]),
                    str(record["status"]),
                    aperture_text,
                    aperture_margin,
                    str(record["termination"]),
                    str(record.get("terminal_media", "") or ""),
                    self._format_ray_inspector_value(record.get("terminal_index")),
                    str(record.get("terminal_inside_volumes", "") or ""),
                    str(record.get("termination_diagnostic", "") or record.get("branch_tree_diagnostic", "") or ""),
                    int(record["hit_count"]),
                    last_text,
                    self._format_ray_inspector_value(record["target_surface"]),
                    self._format_ray_inspector_value(record["distance"]),
                    self._format_ray_inspector_value(record["op"]),
                    self._format_ray_inspector_value(record["transmission"]),
                ),
            )
        if records:
            target_iid = selected_iid if selected_iid in ray_table.get_children() else str(int(records[0]["ray_index"]))
            ray_table.selection_set(target_iid)
            ray_table.focus(target_iid)
            self._populate_ray_inspector_hits()

    def _populate_ray_inspector_hits(self, _event=None) -> None:
        ray_table = self._ray_inspector_ray_table
        hit_table = self._ray_inspector_hit_table
        if ray_table is None or hit_table is None:
            return
        hit_table.delete(*hit_table.get_children())
        selected = ray_table.selection()
        if not selected:
            return
        try:
            ray_index = int(selected[0])
        except Exception:
            return
        record = None
        for candidate in self._ray_inspector_records:
            if int(candidate["ray_index"]) == ray_index:
                record = candidate
                break
        if record is None:
            return
        for hit in record.get("hits", []):
            hit_table.insert("", "end", values=self._ray_hit_table_values(hit))

    def export_ray_inspector_csv(self) -> None:
        records = list(self._ray_inspector_records or self._collect_ray_analysis_records())
        if not records:
            messagebox.showinfo("Export Ray Inspector", "No ray trace data to export. Click Update first.", parent=self.editor)
            return
        path = filedialog.asksaveasfilename(
            title="Export Ray Inspector CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self,
        )
        if not path:
            return
        columns = (
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
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for record in records:
                aperture_record = self._ray_detector_aperture_record(record)
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
                    "branch_jones_p_real": self._safe_complex(record.get("branch_jones_p", 0.0), 0.0).real,
                    "branch_jones_p_imag": self._safe_complex(record.get("branch_jones_p", 0.0), 0.0).imag,
                    "branch_jones_s_real": self._safe_complex(record.get("branch_jones_s", 0.0), 0.0).real,
                    "branch_jones_s_imag": self._safe_complex(record.get("branch_jones_s", 0.0), 0.0).imag,
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
                    writer.writerow(base)
                    continue
                for hit in hits:
                    row = dict(base)
                    row.update(
                        {
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
                    )
                    writer.writerow(row)
        self.status_var.set(f"Ray Inspector CSV exported: {Path(path).name}")

    def export_ray_events_csv(self) -> None:
        bundle = self._last_scene_bundle
        if bundle is None:
            self._collect_ray_analysis_records()
            bundle = self._last_scene_bundle
        records = scene_bundle_ray_event_records(bundle) if bundle is not None else []
        if not records:
            messagebox.showinfo("Export Ray Events", "No canonical ray-event data to export. Click Update first.", parent=self.editor)
            return
        path = filedialog.asksaveasfilename(
            title="Export Ray Events CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self,
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=RAY_EVENT_RECORD_COLUMNS)
            writer.writeheader()
            for record in records:
                writer.writerow({column: record.get(column, "") for column in RAY_EVENT_RECORD_COLUMNS})
        self.status_var.set(f"Ray Events CSV exported: {Path(path).name}")

    def open_branch_tree_inspector(self) -> None:
        window = self._branch_tree_window
        if window is not None and window.winfo_exists():
            self._refresh_branch_tree_inspector()
            window.deiconify()
            window.lift()
            window.focus_force()
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title("Trace Path Inspector")
        window.geometry("1160x680")
        window.minsize(820, 460)
        window.transient(self.editor)
        window.protocol("WM_DELETE_WINDOW", self._close_branch_tree_inspector)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)

        toolbar = ttk.Frame(window, padding=(8, 8, 8, 0))
        toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Button(toolbar, text="Refresh", command=self._refresh_branch_tree_inspector).pack(side="left")
        ttk.Button(toolbar, text="Export CSV", command=self.export_branch_tree_csv).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Open Ray", command=self._open_branch_tree_selected_ray).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Close", command=self._close_branch_tree_inspector).pack(side="left", padx=(6, 0))

        self._branch_tree_summary_var = tk.StringVar(master=window, value="No trace data. Click Update.")
        ttk.Label(
            window,
            textvariable=self._branch_tree_summary_var,
            padding=(8, 6, 8, 0),
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="ew")

        panes = ttk.Panedwindow(window, orient=tk.VERTICAL)
        panes.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)

        branch_frame = ttk.LabelFrame(panes, text="Ray / trace-path graph", padding=6)
        branch_frame.columnconfigure(0, weight=1)
        branch_frame.rowconfigure(0, weight=1)
        panes.add(branch_frame, weight=2)

        hit_frame = ttk.LabelFrame(panes, text="Selected path hits", padding=6)
        hit_frame.columnconfigure(0, weight=1)
        hit_frame.rowconfigure(0, weight=1)
        panes.add(hit_frame, weight=3)

        branch_columns = (
            "field",
            "parent",
            "steps",
            "surfaces",
            "termination",
            "terminal_media",
            "terminal_index",
            "terminal_inside",
            "diagnostic",
            "hits",
            "distance",
            "op",
            "ttbe",
        )
        branch_tree = ttk.Treeview(branch_frame, columns=branch_columns, show="tree headings", selectmode="browse")
        branch_tree.heading("#0", text="Ray / Path")
        branch_tree.heading("field", text="Field")
        branch_tree.heading("parent", text="Parent")
        branch_tree.heading("steps", text="Steps")
        branch_tree.heading("surfaces", text="Surface path")
        branch_tree.heading("termination", text="Termination")
        branch_tree.heading("terminal_media", text="Terminal medium")
        branch_tree.heading("terminal_index", text="Terminal n")
        branch_tree.heading("terminal_inside", text="Terminal inside")
        branch_tree.heading("diagnostic", text="Diagnostic")
        branch_tree.heading("hits", text="Hits")
        branch_tree.heading("distance", text="Dist [mm]")
        branch_tree.heading("op", text="OP [mm]")
        branch_tree.heading("ttbe", text="TTBE")
        branch_tree.column("#0", width=160, anchor="w", stretch=False)
        branch_tree.column("field", width=60, anchor="center", stretch=False)
        branch_tree.column("parent", width=70, anchor="center", stretch=False)
        branch_tree.column("steps", width=80, anchor="center", stretch=False)
        branch_tree.column("surfaces", width=320, anchor="w", stretch=True)
        branch_tree.column("termination", width=160, anchor="w", stretch=True)
        branch_tree.column("terminal_media", width=120, anchor="w", stretch=False)
        branch_tree.column("terminal_index", width=82, anchor="e", stretch=False)
        branch_tree.column("terminal_inside", width=130, anchor="w", stretch=False)
        branch_tree.column("diagnostic", width=240, anchor="w", stretch=True)
        branch_tree.column("hits", width=55, anchor="center", stretch=False)
        branch_tree.column("distance", width=90, anchor="e", stretch=False)
        branch_tree.column("op", width=90, anchor="e", stretch=False)
        branch_tree.column("ttbe", width=76, anchor="e", stretch=False)
        branch_tree.grid(row=0, column=0, sticky="nsew")
        branch_scroll = ttk.Scrollbar(branch_frame, orient="vertical", command=branch_tree.yview)
        branch_scroll.grid(row=0, column=1, sticky="ns")
        branch_tree.configure(yscrollcommand=branch_scroll.set)
        branch_tree.bind("<<TreeviewSelect>>", self._populate_branch_tree_hits, add="+")
        branch_tree.bind("<Double-1>", lambda _event: self._open_branch_tree_selected_ray(), add="+")

        hit_specs = self._ray_hit_table_specs()
        hit_columns = tuple(spec[0] for spec in hit_specs)
        hit_table = ttk.Treeview(hit_frame, columns=hit_columns, show="headings", selectmode="none")
        for column, heading, width, anchor, stretch in hit_specs:
            hit_table.heading(column, text=heading)
            hit_table.column(column, width=width, anchor=anchor, stretch=stretch)
        hit_table.grid(row=0, column=0, sticky="nsew")
        hit_scroll = ttk.Scrollbar(hit_frame, orient="vertical", command=hit_table.yview)
        hit_scroll.grid(row=0, column=1, sticky="ns")
        hit_x_scroll = ttk.Scrollbar(hit_frame, orient="horizontal", command=hit_table.xview)
        hit_x_scroll.grid(row=1, column=0, sticky="ew")
        hit_table.configure(yscrollcommand=hit_scroll.set, xscrollcommand=hit_x_scroll.set)

        self._branch_tree_window = window
        self._branch_tree_table = branch_tree
        self._branch_tree_hit_table = hit_table
        self._show_centered_dialog(window)
        self._refresh_branch_tree_inspector()

    def _close_branch_tree_inspector(self) -> None:
        window = self._branch_tree_window
        self._branch_tree_window = None
        self._branch_tree_summary_var = None
        self._branch_tree_table = None
        self._branch_tree_hit_table = None
        self._branch_tree_records = []
        if window is not None and window.winfo_exists():
            window.destroy()

    def _refresh_branch_tree_if_open(self) -> None:
        window = self._branch_tree_window
        if window is None:
            return
        if not window.winfo_exists():
            self._close_branch_tree_inspector()
            return
        self._refresh_branch_tree_inspector()

    def _refresh_branch_tree_inspector(self) -> None:
        tree = self._branch_tree_table
        hit_table = self._branch_tree_hit_table
        if tree is None or hit_table is None:
            return
        records = self._collect_branch_tree_records(ray_records=self._active_ray_analysis_records())
        self._branch_tree_records = records
        summary = self._trace_preview_summary()
        if self._branch_tree_summary_var is not None:
            if summary["total_rays"]:
                branch_count = len(records)
                self._branch_tree_summary_var.set(
                    "{requested} -> {active} | backend={backend} | rays={total} | paths={branches} | image hits={hits}/{total}".format(
                        requested=summary["requested"],
                        active=summary["active"],
                        backend=summary["backend"],
                        total=summary["total_rays"],
                        branches=branch_count,
                        hits=summary["image_hits"],
                    )
                )
                note = str(summary.get("note", "")).strip()
                if note:
                    self._branch_tree_summary_var.set(f"{self._branch_tree_summary_var.get()} | {note}")
            else:
                self._branch_tree_summary_var.set("No trace data. Click Update.")

        selected = tree.selection()
        selected_iid = selected[0] if selected else None
        tree.delete(*tree.get_children())
        hit_table.delete(*hit_table.get_children())
        records_by_ray: dict[int, list[dict[str, object]]] = {}
        for record in records:
            records_by_ray.setdefault(int(record["ray_index"]), []).append(record)
        first_branch_iid = None
        for ray_index in sorted(records_by_ray):
            branch_records = sorted(records_by_ray[ray_index], key=lambda item: int(item.get("branch_id", 0)))
            field_index = int(branch_records[0].get("field_index", 0)) if branch_records else 0
            ray_iid = f"ray:{ray_index}"
            tree.insert(
                "",
                "end",
                iid=ray_iid,
                text=f"Ray {ray_index}",
                values=(field_index, "-", "-", "-", "ray", "-", "-", "-", "-", len(branch_records), "-", "-", "-"),
                open=True,
            )
            branch_iids: dict[int, str] = {}
            for record in branch_records:
                branch_id = int(record.get("branch_id", 0))
                branch_iid = f"branch:{ray_index}:{branch_id}"
                branch_iids[branch_id] = branch_iid
                record["_tree_iid"] = branch_iid
                if first_branch_iid is None:
                    first_branch_iid = branch_iid
                parent_branch = record.get("parent_branch_id")
                parent_iid = ray_iid
                try:
                    parent_iid = branch_iids.get(int(parent_branch), ray_iid) if parent_branch is not None else ray_iid
                except Exception:
                    parent_iid = ray_iid
                branch_path = str(record.get("branch_path", "") or "").strip()
                branch_text = f"Path {branch_id}"
                if branch_path:
                    branch_text = f"{branch_text}: {branch_path}"
                tree.insert(
                    parent_iid,
                    "end",
                    iid=branch_iid,
                    text=branch_text,
                    values=(
                        int(record.get("field_index", 0)),
                        "-" if parent_branch is None else parent_branch,
                        f"{record.get('start_step', '')}-{record.get('end_step', '')}",
                        record.get("surface_path", ""),
                        record.get("termination", ""),
                        record.get("terminal_media", ""),
                        self._format_ray_inspector_value(record.get("terminal_index")),
                        record.get("terminal_inside_volumes", ""),
                        record.get("termination_diagnostic", "") or record.get("branch_tree_diagnostic", ""),
                        int(record.get("hit_count", 0)),
                        self._format_ray_inspector_value(record.get("distance")),
                        self._format_ray_inspector_value(record.get("op")),
                        self._format_ray_inspector_value(record.get("transmission")),
                    ),
                    open=True,
                )
        target_iid = selected_iid if selected_iid and tree.exists(selected_iid) else first_branch_iid
        if target_iid:
            tree.selection_set(target_iid)
            tree.focus(target_iid)
            tree.see(target_iid)
            self._populate_branch_tree_hits()

    def _branch_tree_record_for_iid(self, iid: str) -> dict[str, object] | None:
        if iid.startswith("branch:"):
            for record in self._branch_tree_records:
                if str(record.get("_tree_iid", "")) == iid:
                    return record
        return None

    def _branch_tree_selected_ray_index(self) -> int | None:
        tree = self._branch_tree_table
        if tree is None:
            return None
        selected = tree.selection()
        if not selected:
            return None
        iid = str(selected[0])
        try:
            if iid.startswith("ray:"):
                return int(iid.split(":", 1)[1])
            if iid.startswith("branch:"):
                return int(iid.split(":", 2)[1])
        except Exception:
            return None
        return None

    def _open_branch_tree_selected_ray(self) -> None:
        ray_index = self._branch_tree_selected_ray_index()
        if ray_index is None:
            return
        self._select_ray_inspector_ray(int(ray_index))

    def _populate_branch_tree_hits(self, _event=None) -> None:
        tree = self._branch_tree_table
        hit_table = self._branch_tree_hit_table
        if tree is None or hit_table is None:
            return
        hit_table.delete(*hit_table.get_children())
        selected = tree.selection()
        if not selected:
            return
        iid = str(selected[0])
        if iid.startswith("ray:"):
            try:
                ray_index = int(iid.split(":", 1)[1])
            except Exception:
                return
            hits: list[dict[str, object]] = []
            for record in self._branch_tree_records:
                if int(record.get("ray_index", -1)) == ray_index:
                    hits.extend(list(record.get("hits", []) or []))
        else:
            record = self._branch_tree_record_for_iid(iid)
            if record is None:
                return
            hits = list(record.get("hits", []) or [])
        for hit in hits:
            hit_table.insert("", "end", values=self._ray_hit_table_values(hit))

    def export_branch_tree_csv(self) -> None:
        records = list(self._branch_tree_records or self._collect_branch_tree_records(ray_records=self._active_ray_analysis_records()))
        if not records:
            messagebox.showinfo("Export Trace Path Tree", "No trace-path data to export. Click Update first.", parent=self.editor)
            return
        path = filedialog.asksaveasfilename(
            title="Export Trace Path Tree CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self,
        )
        if not path:
            return
        columns = (
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
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
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
                    writer.writerow(base)
                    continue
                for hit in hits:
                    row = dict(base)
                    row.update(
                        {
                            "hit_step": hit.get("step", ""),
                            "hit_event_id": hit.get("event_id", ""),
                            "hit_event_kind": hit.get("event_kind", ""),
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
                    )
                    writer.writerow(row)
        self.status_var.set(f"Trace Path Tree CSV exported: {Path(path).name}")

