"""Open 3D STEP overlay import state service."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk
from typing import Any

import numpy as np

from KrakenOS.UI.services.step_overlay_labels import STEP_OVERLAY_LABEL_SET


def _parse_zemax_glass_sequence(path: Path) -> list[str]:
    """Extract glass names from a Zemax ``.zmx`` sequence file.

    The format is one block per ``SURF`` entry; a glass surface ships
    a ``GLAS`` line whose first whitespace token is the catalog name
    (``BK7``, ``N-BK7``, ``SF11``, ...). Air surfaces omit ``GLAS``
    entirely. Returns the glass-name sequence in surface order; air
    gaps are dropped so the result matches the analytic-fit ``rows -
    1`` glass-sequence expectation (one glass per interior region).
    """
    try:
        text = Path(path).read_text(errors="ignore")
    except OSError:
        return []
    names: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.upper().startswith("GLAS"):
            continue
        tokens = stripped.split()
        if len(tokens) < 2:
            continue
        name = tokens[1].strip()
        if not name or name.upper() in {"AIR", "___BLANK___"}:
            continue
        names.append(name)
    return names


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class StepOverlayImportService:
    """Own imported STEP overlay slots and reset state transitions."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def import_lens_step(
        self,
        dialog_parent: tk.Misc | None = None,
        *,
        title: str = "Import lens STEP",
        display_label: str = "Lens STEP",
        largest_component_only: bool = True,
        refresh_open_3d: bool = True,
    ) -> Path | None:
        le = _layout_module()
        path = self._ask_step_file(title, le.ATTACHMENT_DIR, parent=dialog_parent)
        if path is None:
            return None
        self._begin_history_capture()
        self.imported_lens_step_path = path
        self.lens_step_largest_component_only = bool(largest_component_only)
        self.lens_step_rotation_x_deg = 0.0
        self.lens_step_rotation_y_deg = 0.0
        self.lens_step_rotation_z_deg = 0.0
        self.lens_step_axis_offset_xy = (0.0, 0.0)
        self.lens_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self._clear_step_overlay_axis_anchor("lens")
        self._selected_step_label = "lens"
        self._cad_axis_pick_any = False
        self._open3d_trace_refresh_service().clear_step_overlay_physics_preview("lens")
        self._commit_history_capture()
        self._live_step_overlay_trace_plan_cache = {}
        self._invalidate_preview_scene_trace()
        self.status_var.set(f"{display_label} imported: {path.name}. Open or refresh 3D view.")
        if refresh_open_3d:
            self._refresh_open_3d_views()
        return path

    def _default_optical_step_import_offset(self) -> tuple[float, float, float]:
        z_values = [0.0]
        z = 0.0
        for row in list(getattr(self, "rows", []) or []):
            try:
                z += float(getattr(row, "thickness", 0.0) or 0.0)
                z_values.append(float(z))
            except Exception:
                continue
        finite = [value for value in z_values if np.isfinite(value)]
        if not finite:
            return (0.0, 0.0, 0.0)
        return (0.0, 0.0, 0.5 * (min(finite) + max(finite)))

    @staticmethod
    def _optical_prescription_sidecars(path: Path) -> tuple[Path, ...]:
        path = Path(path).expanduser()
        parent = path.parent
        if not parent.exists():
            return ()
        suffixes = {".zmx", ".seq"}
        matches: list[Path] = []
        try:
            for candidate in parent.iterdir():
                if candidate.is_file() and candidate.suffix.lower() in suffixes:
                    matches.append(candidate)
        except OSError:
            return ()
        return tuple(sorted(matches, key=lambda item: (item.suffix.lower() != ".zmx", item.name.lower())))

    def _preserve_unpromoted_step_overlay(self, label: str) -> dict[str, object] | None:
        """Promote an un-promoted STEP overlay before its import slot is reused."""
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return None
        if self._step_path_for_label(label) is None:
            return None
        try:
            result = self.promote_imported_step_to_optical_solid_row(
                label,
                open_face_editor=False,
                clear_overlay=True,
                refresh_open_3d=False,
            )
        except Exception as exc:
            self.append_debug(f"Auto-keep of the existing {label} STEP overlay failed: {exc}")
            return None
        if result is not None:
            row_index = int(result.get("row_index", -1))
            self.append_debug(
                f"Auto-promoted the existing {label.upper()} STEP overlay to optical "
                f"solid row S{row_index} so the new import does not overwrite it."
            )
        return result

    def import_optical_step(
        self,
        dialog_parent: tk.Misc | None = None,
        *,
        refresh_open_3d: bool = True,
    ) -> Path | None:
        le = _layout_module()
        path = self._ask_step_file("Import optical STEP", le.ATTACHMENT_DIR, parent=dialog_parent)
        if path is None:
            return None
        self._preserve_unpromoted_step_overlay("optical")
        self._begin_history_capture()
        self.imported_optical_step_path = path
        self.optical_step_rotation_x_deg = 0.0
        self.optical_step_rotation_y_deg = 0.0
        self.optical_step_rotation_z_deg = 0.0
        self.optical_step_axis_offset_xy = (0.0, 0.0)
        self.optical_step_placement_offset_xyz = self._default_optical_step_import_offset()
        self._clear_step_overlay_axis_anchor("optical")
        self._selected_step_label = "optical"
        self._cad_axis_pick_any = False
        self._open3d_trace_refresh_service().clear_step_overlay_physics_preview("optical")
        self._commit_history_capture()
        self._live_step_overlay_trace_plan_cache = {}
        self._invalidate_preview_scene_trace()
        sidecars = self._optical_prescription_sidecars(path)
        if sidecars:
            self.status_var.set(
                f"Optical STEP imported as CAD solid: {path.name}. STEP has no glass prescription; "
                f"import {sidecars[0].name} for designed lens focus, or promote/assign STEP material and faces."
            )
        else:
            self.status_var.set(f"Optical STEP imported: {path.name}. Carry and place it in Open 3D.")
        if refresh_open_3d:
            self._refresh_open_3d_views(step_label="optical")
        # Offer auto-promote to analytic. Runs only when the surface
        # fit cleanly recovers a front/back pair; otherwise the user
        # keeps the STL body and can promote manually. The dialog
        # carries Skip / Cancel so the existing CAD-solid workflow
        # is never forced into analytic mode.
        self._offer_auto_promote_step_to_analytic(
            "optical", path, sidecars=sidecars, dialog_parent=dialog_parent
        )
        return path

    def import_camera_step(
        self,
        dialog_parent: tk.Misc | None = None,
        *,
        refresh_open_3d: bool = True,
    ) -> Path | None:
        le = _layout_module()
        path = self._ask_step_file("Import camera STEP", le.ATTACHMENT_DIR, parent=dialog_parent)
        if path is None:
            return None
        self._begin_history_capture()
        self.imported_camera_step_path = path
        self.camera_step_rotation_x_deg = 0.0
        self.camera_step_rotation_y_deg = 0.0
        self.camera_step_rotation_z_deg = 0.0
        self.camera_step_axis_offset_xy = (0.0, 0.0)
        self.camera_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self._clear_step_overlay_axis_anchor("camera")
        self._selected_step_label = "camera"
        self._cad_axis_pick_any = False
        self._open3d_trace_refresh_service().clear_step_overlay_physics_preview("camera")
        self._commit_history_capture()
        self._live_step_overlay_trace_plan_cache = {}
        self._invalidate_preview_scene_trace()
        self.status_var.set(f"Camera STEP imported: {path.name}. Open or refresh 3D view.")
        if refresh_open_3d:
            self._refresh_open_3d_views(camera_only=True)
        return path

    def import_led_step(
        self,
        dialog_parent: tk.Misc | None = None,
        *,
        refresh_open_3d: bool = True,
    ) -> Path | None:
        le = _layout_module()
        initial_dir = le.ATTACHMENT_DIR
        path = self._ask_step_file("Import LED STEP", initial_dir, parent=dialog_parent)
        if path is None:
            return None
        initial_distance = max(float(getattr(self, "led_object_edge_distance_mm", 0.0)), 0.0)
        if initial_distance <= 0.0:
            initial_distance = self._default_led_object_edge_distance()
        edge_distance = self._ask_led_edge_distance(initial_distance, parent=dialog_parent)
        if edge_distance is None:
            self.status_var.set("LED STEP import cancelled.")
            return None
        self._begin_history_capture()
        self.imported_led_step_path = path
        self.led_step_rotation_x_deg = 0.0
        self.led_step_rotation_y_deg = 0.0
        self.led_step_rotation_z_deg = 0.0
        self.led_step_object_edge_local_z = None
        self.led_step_axis_offset_xy = (0.0, 0.0)
        self.led_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self._clear_step_overlay_axis_anchor("led")
        self._selected_step_label = "led"
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._open3d_trace_refresh_service().clear_step_overlay_physics_preview("led")
        self.led_object_edge_distance_mm = float(edge_distance)
        self._commit_history_capture()
        self._live_step_overlay_trace_plan_cache = {}
        self._invalidate_preview_scene_trace()
        self.status_var.set(
            f"LED STEP imported: {path.name}; edge distance={self.led_object_edge_distance_mm:.3g} mm."
        )
        if refresh_open_3d:
            self._refresh_open_3d_views(step_label="led")
        return path

    @staticmethod
    def _step_overlay_display_label(label: str) -> str:
        label = str(label).strip().lower()
        if label == "lens":
            return "Lens"
        return {
            "optical": "Optical",
            "led": "LED",
            "camera": "Camera",
        }.get(label, "STEP")

    def step_overlay_display_label(self, label: str) -> str:
        label = str(label).strip().lower()
        if label == "lens" and not bool(getattr(self, "lens_step_largest_component_only", True)):
            return "Optical"
        return self._step_overlay_display_label(label)

    def step_path_for_label(self, label: str) -> Path | None:
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return None
        return {
            "lens": self.imported_lens_step_path,
            "optical": self.imported_optical_step_path,
            "led": self.imported_led_step_path,
            "camera": self.imported_camera_step_path,
        }.get(label)

    def _offer_auto_promote_step_to_analytic(
        self,
        label: str,
        step_path: Path,
        *,
        sidecars: tuple[Path, ...] = (),
        dialog_parent: tk.Misc | None = None,
    ) -> None:
        """Show a confirm dialog offering analytic promotion.

        Runs the existing preview-fit pipeline; if the optical-pair
        auto-detection succeeds the dialog displays the proposed
        Rc / thickness / residual per surface plus a glass-sequence
        entry (pre-filled from a Zemax sidecar if present). Promote
        on confirm; on Skip the user keeps the STL body.
        """
        try:
            preview = self.preview_imported_step_analytic_surfaces(label)
        except Exception as exc:
            self.append_debug(
                f"Auto-promote preview unavailable for {label} STEP: {exc}"
            )
            return
        if preview is None:
            return
        rows_preview = list(preview.get("rows") or [])
        if not rows_preview:
            return
        required_glass_count = max(int(preview.get("required_glass_count", 1)), 1)
        sidecar_glasses: list[str] = []
        sidecar_source: Path | None = None
        for candidate in sidecars:
            if candidate.suffix.lower() != ".zmx":
                continue
            parsed = _parse_zemax_glass_sequence(candidate)
            if parsed:
                sidecar_glasses = parsed[:required_glass_count]
                sidecar_source = candidate
                break
        default_glass_text = ", ".join(sidecar_glasses) if sidecar_glasses else "N-BK7"
        choice = self._ask_analytic_promote_confirm(
            label,
            step_path,
            preview,
            default_glass_text=default_glass_text,
            sidecar_source=sidecar_source,
            dialog_parent=dialog_parent,
        )
        if choice is None:
            return
        try:
            self.promote_imported_step_to_analytic_surfaces(
                label,
                glass_sequence=choice,
                refresh_open_3d=True,
            )
        except Exception as exc:
            self.append_debug(f"Auto-promote of {label} STEP failed: {exc}")
            self.status_var.set(
                f"Auto-promote failed: {exc}. STEP kept as CAD body; "
                "use Faces... / Promote menu to retry."
            )

    def _ask_analytic_promote_confirm(
        self,
        label: str,
        step_path: Path,
        preview: dict[str, Any],
        *,
        default_glass_text: str,
        sidecar_source: Path | None,
        dialog_parent: tk.Misc | None,
    ) -> str | None:
        rows_preview = list(preview.get("rows") or [])
        required_glass_count = max(int(preview.get("required_glass_count", 1)), 1)
        parent = dialog_parent or self
        dialog = tk.Toplevel(parent)
        dialog.withdraw()
        dialog.title(f"Auto-promote {label.upper()} STEP to analytic")
        dialog.transient(parent)
        dialog.grab_set()
        dialog.resizable(False, False)

        header_text = (
            f"Imported STEP: {step_path.name}\n"
            f"Detected {len(rows_preview)} surface(s); proposed analytic rows:"
        )
        ttk.Label(dialog, text=header_text, justify="left").grid(
            row=0, column=0, columnspan=4, padx=12, pady=(12, 6), sticky="w"
        )

        cols = ("idx", "kind", "rc", "thickness", "residual")
        tree = ttk.Treeview(dialog, columns=cols, show="headings", height=min(len(rows_preview), 6))
        headers = (("idx", "#"), ("kind", "Fit"), ("rc", "Rc [mm]"), ("thickness", "T [mm]"), ("residual", "Res [µm]"))
        widths = {"idx": 36, "kind": 80, "rc": 110, "thickness": 100, "residual": 90}
        for col_id, col_label in headers:
            tree.heading(col_id, text=col_label)
            tree.column(col_id, width=widths.get(col_id, 80), anchor="center", stretch=False)
        for i, row in enumerate(rows_preview, start=1):
            rc = float(row.get("rc_mm", 0.0))
            kind = str(row.get("kind", ""))
            thickness = float(row.get("thickness_mm", 0.0))
            residual_um = float(row.get("residual_mm", 0.0)) * 1000.0
            rc_text = "plano" if abs(rc) < 1e-9 and kind == "plane" else f"{rc:+.3g}"
            tree.insert(
                "",
                "end",
                values=(i, kind, rc_text, f"{thickness:.3g}", f"{residual_um:.2g}"),
            )
        tree.grid(row=1, column=0, columnspan=4, padx=12, pady=(0, 8), sticky="ew")

        glass_label_text = f"Glass sequence ({required_glass_count} interior region(s), comma-separated):"
        if sidecar_source is not None:
            glass_label_text += f"\nPre-filled from sidecar {sidecar_source.name}."
        ttk.Label(dialog, text=glass_label_text, justify="left").grid(
            row=2, column=0, columnspan=4, padx=12, pady=(4, 4), sticky="w"
        )
        glass_var = tk.StringVar(value=default_glass_text)
        glass_entry = ttk.Entry(dialog, textvariable=glass_var, width=48)
        glass_entry.grid(row=3, column=0, columnspan=4, padx=12, pady=(0, 12), sticky="ew")

        result: dict[str, str] = {}

        def accept() -> None:
            text = glass_var.get().strip()
            if not text:
                self.status_var.set("Auto-promote: glass sequence is required.")
                return
            result["glass"] = text
            dialog.destroy()

        def skip() -> None:
            dialog.destroy()

        ttk.Button(dialog, text="Promote", command=accept).grid(
            row=4, column=2, padx=(4, 4), pady=(0, 12), sticky="e"
        )
        ttk.Button(dialog, text="Skip", command=skip).grid(
            row=4, column=3, padx=(4, 12), pady=(0, 12), sticky="w"
        )
        dialog.bind("<Return>", lambda _event: accept())
        dialog.bind("<Escape>", lambda _event: skip())
        try:
            self._show_centered_dialog(dialog)
        except Exception:
            dialog.deiconify()
        glass_entry.focus_set()
        self.wait_window(dialog)
        return result.get("glass")

    def clear_imported_step_overlay_state(self, label: str) -> None:
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return
        path_attrs = {
            "lens": "imported_lens_step_path",
            "optical": "imported_optical_step_path",
            "led": "imported_led_step_path",
            "camera": "imported_camera_step_path",
        }
        path_attr = path_attrs.get(label)
        if path_attr:
            setattr(self, path_attr, None)
        for axis in ("x", "y", "z"):
            attr = f"{label}_step_rotation_{axis}_deg"
            if hasattr(self, attr):
                setattr(self, attr, 0.0)
        axis_attr = f"{label}_step_axis_offset_xy"
        if hasattr(self, axis_attr):
            setattr(self, axis_attr, (0.0, 0.0))
        placement_attr = f"{label}_step_placement_offset_xyz"
        if hasattr(self, placement_attr):
            setattr(self, placement_attr, (0.0, 0.0, 0.0))
        self._live_step_overlay_trace_plan_cache = {}
        if label == "led":
            self.led_object_edge_distance_mm = 0.0
            self.led_step_object_edge_local_z = None
        if label == "lens":
            self.lens_step_largest_component_only = True
        self._clear_step_overlay_axis_anchor(label)
        self._open3d_trace_refresh_service().clear_step_overlay_physics_preview(label)
        if self._selected_step_label == label:
            self._selected_step_label = None
        self._invalidate_preview_scene_trace()
