"""Right-docked scene component browser for the embedded Open 3D inspector."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any, Callable


class Open3DStepAdminPanel:
    """Build a CAD-style browser for Open 3D scene components."""

    CATEGORY_SPECS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
        ("layout", "Layout / Table Components", ()),
        ("optical", "Optical Element", ("optical",)),
        ("lens", "Imaging Lens", ("lens",)),
        ("camera_detector", "Camera / Detector", ("camera", "led")),
    )

    def __init__(self, inspector: Any) -> None:
        self.inspector = inspector
        self.editor = inspector.editor
        self._tree: ttk.Treeview | None = None
        self._refreshing = False
        self._selected_item_id = ""
        self._property_vars: dict[str, tk.StringVar] = {}
        self._selection_buttons: dict[str, ttk.Button] = {}
        self._face_direction_var: tk.StringVar | None = None
        self._face_direction_combo: ttk.Combobox | None = None

    def build(self, parent: tk.Widget) -> ttk.Frame:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        stack = ttk.Frame(parent)
        stack.grid(row=0, column=0, sticky="nsew")
        stack.columnconfigure(0, weight=1)
        stack.rowconfigure(0, weight=1)

        tree_frame = ttk.Frame(stack)
        tree_frame.grid(row=0, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse", height=12)
        tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)
        tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._tree = tree

        import_frame = ttk.LabelFrame(stack, text="Import", padding=8)
        import_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        import_frame.columnconfigure(0, weight=1)
        import_frame.columnconfigure(1, weight=1)
        self._grid_button(import_frame, 0, 0, "Optical", lambda: self._import_step("optical"))
        self._grid_button(import_frame, 0, 1, "Lens", lambda: self._import_step("lens"))
        self._grid_button(import_frame, 1, 0, "Camera", lambda: self._import_step("camera"))
        self._grid_button(import_frame, 1, 1, "LED", lambda: self._import_step("led"))

        property_frame = ttk.LabelFrame(stack, text="Properties", padding=8)
        property_frame.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        property_frame.columnconfigure(1, weight=1)
        for row, (key, label) in enumerate(
            (
                ("name", "Name"),
                ("kind", "Kind"),
                ("file", "File"),
                ("pose", "Pose"),
                ("faces", "Faces"),
            )
        ):
            ttk.Label(property_frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 6), pady=(0, 2))
            var = tk.StringVar(value="-")
            self._property_vars[key] = var
            ttk.Label(property_frame, textvariable=var, width=24).grid(row=row, column=1, sticky="ew", pady=(0, 2))

        action_frame = ttk.LabelFrame(stack, text="Selected Element", padding=8)
        action_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        action_frame.columnconfigure(0, weight=1)
        action_frame.columnconfigure(1, weight=1)
        self._selection_buttons["carry"] = self._grid_button(action_frame, 0, 0, "Carry", self._carry_selected)
        self._selection_buttons["accept"] = self._grid_button(action_frame, 0, 1, "Accept", self._accept_selected)
        self._selection_buttons["promote"] = self._grid_button(action_frame, 1, 0, "Promote", self._promote_selected)
        self._selection_buttons["delete"] = self._grid_button(action_frame, 1, 1, "Delete", self._delete_selected)
        self._selection_buttons["faces"] = self._grid_button(action_frame, 2, 0, "Faces", self._faces_selected)
        self._selection_buttons["center"] = self._grid_button(action_frame, 2, 1, "Center Axis", self._center_selected)
        self._selection_buttons["normal"] = self._grid_button(action_frame, 3, 0, "Center Normal->Axis", self._normal_axis_selected, columnspan=2)
        self._selection_buttons["pick_normal"] = self._grid_button(
            action_frame,
            4,
            0,
            "Pick Normal->Axis",
            self._pick_normal_axis_selected,
            columnspan=2,
        )
        self._selection_buttons["surface_center"] = self._grid_button(
            action_frame,
            5,
            0,
            "Center Surface->Axis",
            self._surface_center_selected,
            columnspan=2,
        )
        ttk.Label(action_frame, text="Face direction").grid(row=6, column=0, sticky="w", pady=(7, 0))
        self._face_direction_var = tk.StringVar(value="")
        face_direction_combo = ttk.Combobox(
            action_frame,
            textvariable=self._face_direction_var,
            state="disabled",
            values=("Left", "Right", "Up", "Down", "Front", "Back"),
            width=10,
        )
        face_direction_combo.grid(row=6, column=1, sticky="ew", pady=(7, 0))
        face_direction_combo.bind("<<ComboboxSelected>>", self._on_face_direction_selected)
        self._face_direction_combo = face_direction_combo

        self.refresh()
        return stack

    @staticmethod
    def _grid_button(
        parent: tk.Widget,
        row: int,
        column: int,
        text: str,
        command: Callable[[], object],
        *,
        columnspan: int = 1,
    ) -> ttk.Button:
        button = ttk.Button(parent, text=text, command=command)
        button.grid(
            row=row,
            column=column,
            columnspan=columnspan,
            sticky="ew",
            padx=(0, 3) if column == 0 and columnspan == 1 else (3, 0) if column == 1 else 0,
            pady=(5, 0),
        )
        return button

    def _category_for_label(self, label: str) -> str:
        label = str(label).strip().lower()
        for key, _title, labels in self.CATEGORY_SPECS:
            if label in labels:
                return key
        return "optical"

    def _step_path_name(self, label: str) -> str:
        path = self.editor._step_path_for_label(label)
        if path is None:
            return ""
        try:
            return Path(path).name
        except Exception:
            return str(path)

    def _promoted_step_rows(self) -> list[tuple[int, str, str]]:
        rows = list(getattr(self.editor, "rows", []) or [])
        records: list[tuple[int, str, str]] = []
        for row_index, row in enumerate(rows):
            try:
                if not self.editor._is_open3d_promoted_optical_solid_row(row):
                    continue
            except Exception:
                continue
            advanced = getattr(row, "advanced", {}) if not isinstance(row, dict) else row.get("advanced", {})
            try:
                label = str(self.editor._open3d_step_label_for_optical_solid_row(row) or "optical").strip().lower()
            except Exception:
                promotion = advanced.get("StepOverlayPromotion", {}) if isinstance(advanced, dict) else {}
                label = str(promotion.get("step_label", "optical") or "optical").strip().lower()
            if not label:
                label = "optical"
            name = str(getattr(row, "name", "") or f"S{row_index} STEP solid")
            records.append((int(row_index), label, name))
        return records

    def _visible_scene_row_indices(self) -> list[int]:
        row_actor_map = getattr(self.inspector, "_row_actor_map", {}) or {}
        indices: list[int] = []
        for key, actor_keys in dict(row_actor_map).items():
            try:
                row_index = int(key)
            except Exception:
                continue
            if actor_keys:
                indices.append(row_index)
        return sorted(set(indices))

    def _scene_row_display_name(self, row_index: int, row: object) -> str:
        surface = str(getattr(row, "surface", "") or "").strip()
        name = str(getattr(row, "name", "") or "").strip()
        element = ""
        try:
            element = str(self.editor._element_key(row) or "").strip()
        except Exception:
            element = str(getattr(row, "element", "") or "").strip()
        label = name or surface or f"Surface {int(row_index)}"
        if element and element != label:
            label = f"{element}: {label}"
        return label

    def _scene_row_category(self, row_index: int, row: object) -> str:
        try:
            if self.editor._file_backed_stl_row_at(int(row_index)) is not None:
                label = str(self.editor._open3d_step_label_for_optical_solid_row(row) or "optical")
                return self._category_for_label(label)
        except Exception:
            pass
        text = " ".join(
            str(getattr(row, attr, "") or "")
            for attr in ("surface", "name", "element", "glass")
        ).strip().lower()
        if any(token in text for token in ("camera", "detector", "sensor", "image")):
            return "camera_detector"
        if any(token in text for token in ("lens", "objective", "doublet", "gauss", "achromat")):
            return "lens"
        return "layout"

    def _scene_row_records(self) -> list[tuple[int, str, str]]:
        rows = list(getattr(self.editor, "rows", []) or [])
        promoted = {row_index for row_index, _label, _name in self._promoted_step_rows()}
        records: list[tuple[int, str, str]] = []
        for row_index in self._visible_scene_row_indices():
            if row_index in promoted or row_index < 0 or row_index >= len(rows):
                continue
            row = rows[row_index]
            records.append(
                (
                    int(row_index),
                    self._scene_row_category(int(row_index), row),
                    self._scene_row_display_name(int(row_index), row),
                )
            )
        return records

    def _current_browser_selection_iid(self) -> str:
        selected = str(getattr(self.editor, "_selected_step_label", "") or "").strip().lower()
        if selected and self.editor._step_path_for_label(selected) is not None:
            return f"overlay:{selected}"
        candidate_rows: list[object] = [getattr(self.inspector, "_picked_row_index", None)]
        try:
            candidate_rows.append(self.editor._current_selected_row_index())
        except Exception:
            pass
        rows = list(getattr(self.editor, "rows", []) or [])
        for candidate in candidate_rows:
            try:
                row_index = int(candidate)
            except Exception:
                continue
            if row_index < 0 or row_index >= len(rows):
                continue
            try:
                if self.editor._is_open3d_promoted_optical_solid_row(rows[row_index]):
                    return f"row:{row_index}"
            except Exception:
                pass
            if row_index in self._visible_scene_row_indices():
                return f"scene-row:{row_index}"
        return ""

    def refresh(self) -> None:
        tree = self._tree
        if tree is None:
            return
        previous = self._current_browser_selection_iid() or self._selected_item_id
        self._refreshing = True
        try:
            tree.delete(*tree.get_children(""))
            category_iids: dict[str, str] = {}
            category_counts: dict[str, int] = {}
            for key, title, _labels in self.CATEGORY_SPECS:
                iid = f"category:{key}"
                tree.insert("", "end", iid=iid, text=title, open=True)
                category_iids[key] = iid
                category_counts[key] = 0
            for _key, _title, labels in self.CATEGORY_SPECS:
                for label in labels:
                    if self.editor._step_path_for_label(label) is None:
                        continue
                    category = self._category_for_label(label)
                    display = self.editor._step_overlay_display_label(label)
                    name = self._step_path_name(label)
                    text = f"{display}: {name}" if name else f"{display} STEP"
                    tree.insert(category_iids[category], "end", iid=f"overlay:{label}", text=text)
                    category_counts[category] += 1
            for row_index, label, name in self._promoted_step_rows():
                category = self._category_for_label(label)
                tree.insert(category_iids[category], "end", iid=f"row:{row_index}", text=f"S{row_index}: {name}")
                category_counts[category] += 1
            for row_index, category, name in self._scene_row_records():
                parent = category_iids.get(category, category_iids["layout"])
                tree.insert(parent, "end", iid=f"scene-row:{row_index}", text=f"S{row_index}: {name}")
                category_counts[category if category in category_counts else "layout"] += 1
            for key, parent_iid in category_iids.items():
                if category_counts.get(key, 0) <= 0:
                    tree.insert(parent_iid, "end", iid=f"empty:{key}", text="(empty)")
            if previous and tree.exists(previous):
                tree.selection_set(previous)
                tree.focus(previous)
                self._selected_item_id = previous
            else:
                self._selected_item_id = ""
        finally:
            self._refreshing = False
        if self._selected_item_id:
            self._update_properties(self._selected_item_id)
        else:
            self._update_properties("")

    def _on_tree_select(self, _event=None) -> None:
        if self._refreshing:
            return
        tree = self._tree
        if tree is None:
            return
        selection = tree.selection()
        iid = str(selection[0]) if selection else ""
        if not iid or iid.startswith("category:") or iid.startswith("empty:"):
            self._selected_item_id = ""
            self._update_properties("")
            return
        if iid == self._selected_item_id and iid == self._current_browser_selection_iid():
            self._update_properties(iid)
            return
        self._selected_item_id = iid
        if iid.startswith("overlay:"):
            label = iid.split(":", 1)[1]
            self.inspector.select_step_overlay_from_admin(label)
        elif iid.startswith("row:"):
            try:
                row_index = int(iid.split(":", 1)[1])
            except Exception:
                row_index = -1
            self.inspector.select_promoted_step_row_from_admin(row_index)
        elif iid.startswith("scene-row:"):
            try:
                row_index = int(iid.split(":", 1)[1])
            except Exception:
                row_index = -1
            self.inspector.select_scene_row_from_admin(row_index)
        self._update_properties(iid)

    def _current_kind_value(self) -> tuple[str, str]:
        iid = str(self._selected_item_id or "")
        if ":" not in iid:
            return "", ""
        kind, value = iid.split(":", 1)
        return kind, value

    def _update_properties(self, iid: str) -> None:
        values = {
            "name": "-",
            "kind": "-",
            "file": "-",
            "pose": "-",
            "faces": "-",
        }
        overlay_selected = False
        promoted_row_selected = False
        file_backed_row_selected = False
        centerable_row_selected = False
        if iid.startswith("overlay:"):
            label = iid.split(":", 1)[1]
            path = self.editor._step_path_for_label(label)
            overlay_selected = path is not None
            if overlay_selected:
                display = self.editor._step_overlay_display_label(label)
                offset = self.editor._step_placement_offset_xyz(label)
                values.update(
                    {
                        "name": f"{display} STEP",
                        "kind": "Imported overlay",
                        "file": self._step_path_name(label),
                        "pose": (
                            f"R=({self.editor._step_x_rotation_deg(label):.0f},"
                            f"{self.editor._step_y_rotation_deg(label):.0f},"
                            f"{self.editor._step_roll_deg(label):.0f}) "
                            f"T=({float(offset[0]):.3g},{float(offset[1]):.3g},{float(offset[2]):.3g})"
                        ),
                        "faces": "Promote or right-click",
                    }
                )
        elif iid.startswith("row:"):
            try:
                row_index = int(iid.split(":", 1)[1])
            except Exception:
                row_index = -1
            rows = list(getattr(self.editor, "rows", []) or [])
            if 0 <= row_index < len(rows):
                row = rows[row_index]
                promoted_row_selected = True
                file_backed_row_selected = True
                advanced = getattr(row, "advanced", {}) if not isinstance(row, dict) else row.get("advanced", {})
                promotion = advanced.get("StepOverlayPromotion", {}) if isinstance(advanced, dict) else {}
                source_path = ""
                if isinstance(advanced, dict):
                    source_path = str(
                        promotion.get("source_step_path")
                        or advanced.get("OpticalSolidSourcePath")
                        or promotion.get("promoted_mesh_path")
                        or advanced.get("Solid_3d_stl")
                        or ""
                    )
                path_text = Path(source_path).name
                face_metadata = advanced.get("OpticalSolidFaces", {}) if isinstance(advanced, dict) else {}
                assigned = 0
                if isinstance(face_metadata, dict):
                    assigned = len(face_metadata)
                values.update(
                    {
                        "name": str(getattr(row, "name", "") or f"S{row_index} STEP solid"),
                        "kind": f"Promoted row S{row_index}",
                        "file": path_text or "-",
                        "pose": (
                            f"D=({float(getattr(row, 'desp_x', 0.0) or 0.0):.3g},"
                            f"{float(getattr(row, 'desp_y', 0.0) or 0.0):.3g},"
                            f"{float(getattr(row, 'desp_z', 0.0) or 0.0):.3g})"
                        ),
                        "faces": f"{assigned} assigned",
                    }
                )
        elif iid.startswith("scene-row:"):
            try:
                row_index = int(iid.split(":", 1)[1])
            except Exception:
                row_index = -1
            rows = list(getattr(self.editor, "rows", []) or [])
            if 0 <= row_index < len(rows):
                row = rows[row_index]
                try:
                    file_backed_row_selected = self.editor._file_backed_stl_row_at(row_index) is not None
                except Exception:
                    file_backed_row_selected = False
                surface = str(getattr(row, "surface", "") or "")
                centerable_row_selected = surface not in {"Object", "Image"}
                advanced = getattr(row, "advanced", {}) if not isinstance(row, dict) else row.get("advanced", {})
                face_metadata = advanced.get("OpticalSolidFaces", {}) if isinstance(advanced, dict) else {}
                assigned = len(face_metadata) if isinstance(face_metadata, dict) else 0
                values.update(
                    {
                        "name": self._scene_row_display_name(row_index, row),
                        "kind": f"Editable table row S{row_index}",
                        "file": "CAD/STL row" if file_backed_row_selected else "Table",
                        "pose": (
                            f"T=({float(getattr(row, 'thickness', 0.0) or 0.0):.3g}) "
                            f"D=({float(getattr(row, 'desp_x', 0.0) or 0.0):.3g},"
                            f"{float(getattr(row, 'desp_y', 0.0) or 0.0):.3g},"
                            f"{float(getattr(row, 'desp_z', 0.0) or 0.0):.3g})"
                        ),
                        "faces": f"{assigned} assigned" if file_backed_row_selected else str(surface or "-"),
                    }
                )
        for key, value in values.items():
            self._property_vars[key].set(value)
        button_states = {
            "carry": overlay_selected,
            "accept": overlay_selected,
            "promote": overlay_selected,
            "delete": overlay_selected or promoted_row_selected,
            "faces": promoted_row_selected or file_backed_row_selected,
            "center": overlay_selected or promoted_row_selected or centerable_row_selected,
            "normal": overlay_selected,
            "pick_normal": overlay_selected,
            "surface_center": overlay_selected,
        }
        for key, button in self._selection_buttons.items():
            try:
                button.configure(state="normal" if button_states.get(key, False) else "disabled")
            except Exception:
                pass
        if self._face_direction_combo is not None:
            try:
                self._face_direction_combo.configure(state="readonly" if overlay_selected else "disabled")
            except Exception:
                pass

    def _select_current_for_action(self) -> bool:
        kind, value = self._current_kind_value()
        if kind == "overlay":
            return bool(self.inspector.select_step_overlay_from_admin(value))
        if kind == "row":
            try:
                row_index = int(value)
            except Exception:
                return False
            return bool(self.inspector.select_promoted_step_row_from_admin(row_index))
        if kind == "scene-row":
            try:
                row_index = int(value)
            except Exception:
                return False
            return bool(self.inspector.select_scene_row_from_admin(row_index))
        return False

    def _import_step(self, label: str) -> None:
        if label == "optical":
            self.inspector.import_optical_step_overlay()
        else:
            self.inspector.import_step_overlay(label)
        self._selected_item_id = f"overlay:{label}"
        self.refresh()

    def _carry_selected(self) -> None:
        if self._select_current_for_action():
            self.inspector.start_selected_step_carry()
            self.refresh()

    def _accept_selected(self) -> None:
        if self._select_current_for_action():
            self.inspector.accept_selected_step_placement()
            self._selected_item_id = ""
            self.refresh()

    def _promote_selected(self) -> None:
        if self._select_current_for_action():
            self.inspector.promote_selected_step_to_optical_solid_row()
            self._selected_item_id = ""
            self.refresh()

    def _delete_selected(self) -> None:
        if self._select_current_for_action():
            self.inspector.delete_selected_step()
            self._selected_item_id = ""
            self.refresh()

    def _faces_selected(self) -> None:
        if self._select_current_for_action():
            self.inspector.open_selected_optical_faces()
            self.refresh()

    def _center_selected(self) -> None:
        kind, _value = self._current_kind_value()
        if not self._select_current_for_action():
            return
        if kind in {"row", "scene-row"}:
            self.inspector.start_center_row_to_ray()
        else:
            self.editor.start_any_step_axis_pick()
        self.refresh()

    def _normal_axis_selected(self) -> None:
        if self._select_current_for_action():
            self.inspector.snap_selected_step_normal_to_optical_axis()
            self.refresh()

    def _pick_normal_axis_selected(self) -> None:
        if self._select_current_for_action():
            self.inspector.snap_selected_step_pick_point_normal_to_optical_axis()
            self.refresh()

    def _surface_center_selected(self) -> None:
        if self._select_current_for_action():
            self.inspector.center_selected_step_surface_to_optical_axis()
            self.refresh()

    def _on_face_direction_selected(self, _event=None) -> None:
        var = self._face_direction_var
        direction = str(var.get() if var is not None else "").strip()
        if direction not in {"Left", "Right", "Up", "Down", "Front", "Back"}:
            return
        if not self._select_current_for_action():
            return
        self.inspector.orient_selected_step_face_to_direction(direction)
        self.refresh()
