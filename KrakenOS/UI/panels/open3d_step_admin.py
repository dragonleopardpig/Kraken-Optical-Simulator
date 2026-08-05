"""Right-docked scene component browser for the embedded Open 3D inspector."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import simpledialog, ttk
from typing import Any, Callable


class Open3DStepAdminPanel:
    """Build a CAD-style browser for Open 3D scene components."""

    CATEGORY_SPECS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
        ("display", "Display / Overlays", ()),
        ("layout", "Layout / Table Components", ()),
        ("optical", "Optical Element", ("optical",)),
        ("lens", "Imaging Lens", ("lens",)),
        ("camera_detector", "Camera / Detector", ("camera",)),
        ("led", "LED (decoration)", ("led",)),
        ("sources", "Scene Sources", ()),
    )

    def _display_toggle_specs(self):
        """(key, label, owner, var_name) for the rays + overlay display toggles
        surfaced in the browser so they hide/unhide like other elements."""
        return (
            ("rays", "Rays", self.inspector, "show_rays_var"),
            ("thickness", "Thickness dimensions", self.editor, "show_physical_distances_var"),
            ("refs", "Reference surfaces", self.inspector, "show_reference_surfaces_var"),
            ("detectors", "Detector overlays", self.inspector, "show_detector_overlays_var"),
            ("misses", "Missed-ray diagnostics", self.inspector, "show_terminal_diagnostics_var"),
        )

    def _display_var_for_key(self, key: str):
        for spec_key, _label, owner, var_name in self._display_toggle_specs():
            if spec_key == key:
                return getattr(owner, var_name, None)
        return None

    def __init__(self, inspector: Any) -> None:
        self.inspector = inspector
        self.editor = inspector.editor
        self._tree: ttk.Treeview | None = None
        self._panel_canvas: tk.Canvas | None = None
        self._panel_scrollbar: ttk.Scrollbar | None = None
        self._refreshing = False
        self._selected_item_id = ""
        self._property_vars: dict[str, tk.StringVar] = {}
        self._selection_buttons: dict[str, ttk.Button] = {}
        self._face_direction_var: tk.StringVar | None = None
        self._face_direction_combo: ttk.Combobox | None = None

    def build(self, parent: tk.Widget) -> ttk.Frame:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        # bugs/0093: vertical pane -- the browser tree (top) is height-resizable via a
        # draggable sash (the height edge now shows a resize cursor), over a scrollable
        # controls area (Import / Properties / Selected Element / STEP). The controls
        # show a vertical scrollbar + scroll on the wheel/touchpad (bound over the
        # buttons too, not just empty canvas) when they don't fit; the tree keeps its
        # own row scrollbar.
        pane = ttk.Panedwindow(parent, orient="vertical")
        pane.grid(row=0, column=0, sticky="nsew")
        self._panel_pane = pane

        tree_frame = ttk.Frame(pane)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(1, weight=1)
        header = ttk.Frame(tree_frame)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        header.columnconfigure(0, weight=1)
        ttk.Button(header, text="▶", width=2, command=self.inspector.toggle_scene_components_panel).grid(row=0, column=1, sticky="e")
        tree = ttk.Treeview(tree_frame, show="tree", selectmode="browse", height=10)
        tree.grid(row=1, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree_scroll.grid(row=1, column=1, sticky="ns")
        tree.configure(yscrollcommand=tree_scroll.set)
        tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        tree.bind("<Shift-Button-1>", self._on_tree_shift_click)
        tree.bind("<Button-3>", self._on_tree_right_click)
        tree.tag_configure("hidden", foreground="#9aa0a6")  # grey out hidden elements
        self._tree = tree
        pane.add(tree_frame, weight=3)

        controls_host = ttk.Frame(pane)
        controls_host.columnconfigure(0, weight=1)
        controls_host.rowconfigure(0, weight=1)
        canvas = tk.Canvas(controls_host, highlightthickness=0, borderwidth=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        panel_scroll = ttk.Scrollbar(controls_host, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=panel_scroll.set)
        self._panel_canvas = canvas
        self._panel_scrollbar = panel_scroll
        stack = ttk.Frame(canvas)
        stack_window = canvas.create_window((0, 0), window=stack, anchor="nw")
        stack.columnconfigure(0, weight=1)
        pane.add(controls_host, weight=2)

        def _update_panel_scroll() -> None:
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
                overflow = stack.winfo_reqheight() > canvas.winfo_height() + 1
                if overflow and not panel_scroll.grid_info():
                    panel_scroll.grid(row=0, column=1, sticky="ns")
                elif not overflow and panel_scroll.grid_info():
                    panel_scroll.grid_remove()
            except tk.TclError:
                pass

        def _on_canvas_configure(event) -> None:
            fill_height = max(int(event.height), stack.winfo_reqheight())
            canvas.itemconfigure(stack_window, width=int(event.width), height=fill_height)
            _update_panel_scroll()

        def _on_mousewheel(event) -> "str | None":
            if stack.winfo_reqheight() <= canvas.winfo_height():
                return None
            num = getattr(event, "num", 0)
            delta = getattr(event, "delta", 0)
            if num == 4 or delta > 0:
                canvas.yview_scroll(-1, "units")
            elif num == 5 or delta < 0:
                canvas.yview_scroll(1, "units")
            return "break"

        stack.bind("<Configure>", lambda _e: _update_panel_scroll())
        canvas.bind("<Configure>", _on_canvas_configure)
        self._panel_wheel_handler = _on_mousewheel

        import_frame = ttk.LabelFrame(stack, text="Import", padding=8)
        import_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        import_frame.columnconfigure(0, weight=1)
        import_frame.columnconfigure(1, weight=1)
        self._grid_button(import_frame, 0, 0, "Optical", lambda: self._import_step("optical"))
        self._grid_button(import_frame, 0, 1, "Imaging Lens", lambda: self._import_step("lens"))
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
        self._selection_buttons["native"] = self._grid_button(action_frame, 2, 0, "Native Rows", self._native_selected, columnspan=2)
        self._selection_buttons["faces"] = self._grid_button(action_frame, 3, 0, "Faces", self._faces_selected)
        self._selection_buttons["center"] = self._grid_button(action_frame, 3, 1, "Center Axis", self._center_selected)
        self._selection_buttons["normal"] = self._grid_button(action_frame, 4, 0, "Center Normal->Axis", self._normal_axis_selected, columnspan=2)
        self._selection_buttons["pick_normal"] = self._grid_button(
            action_frame,
            5,
            0,
            "Pick Normal->Axis",
            self._pick_normal_axis_selected,
            columnspan=2,
        )
        self._selection_buttons["surface_center"] = self._grid_button(
            action_frame,
            6,
            0,
            "Center Surface->Axis",
            self._surface_center_selected,
            columnspan=2,
        )
        ttk.Label(action_frame, text="Face direction").grid(row=7, column=0, sticky="w", pady=(7, 0))
        self._face_direction_var = tk.StringVar(value="")
        face_direction_combo = ttk.Combobox(
            action_frame,
            textvariable=self._face_direction_var,
            state="disabled",
            values=("Left", "Right", "Up", "Down", "Front", "Back"),
            width=10,
        )
        face_direction_combo.grid(row=7, column=1, sticky="ew", pady=(7, 0))
        face_direction_combo.bind("<<ComboboxSelected>>", self._on_face_direction_selected)
        self._face_direction_combo = face_direction_combo

        step_frame = ttk.LabelFrame(stack, text="STEP Placement", padding=8)
        step_frame.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        step_frame.columnconfigure(0, weight=1)
        step_frame.columnconfigure(1, weight=1)
        self._grid_button(step_frame, 0, 0, "Accept STEP Placement",
                          self.inspector.accept_selected_step_placement, columnspan=2)
        self._grid_button(step_frame, 1, 0, "Promote STEP Row",
                          self.inspector.promote_selected_step_to_optical_solid_row)
        self._grid_button(step_frame, 1, 1, "Clear STEP", self.inspector.clear_step_imports)

        # bugs/0093: bind the wheel on every control widget (not just the canvas) so a
        # mouse/touchpad scroll anywhere over the controls scrolls them -- a wheel
        # event is delivered to the widget under the cursor, so binding only the
        # canvas missed the buttons/frames. The tree is excluded (keeps its own).
        self._bind_wheel_to_controls(stack)

        self.refresh()
        return stack

    def _bind_wheel_to_controls(self, widget: tk.Widget) -> None:
        handler = getattr(self, "_panel_wheel_handler", None)
        canvas = getattr(self, "_panel_canvas", None)
        if handler is None:
            return
        if canvas is not None:
            for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                try:
                    canvas.bind(seq, handler)
                except Exception:
                    pass

        def _bind(node: tk.Widget) -> None:
            if node is getattr(self, "_tree", None):
                return  # the browser tree scrolls itself
            for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                try:
                    node.bind(seq, handler)
                except Exception:
                    pass
            try:
                children = node.winfo_children()
            except Exception:
                children = []
            for child in children:
                _bind(child)

        _bind(widget)

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

    def _glue_partner_suffix(self, label: str) -> str:
        """bugs/0103: a persistent "glued" indicator on the BS<->LED pair, so the
        rigid-glue state (item 3) is visible in the browser instead of only a
        transient status line. Naming the partner tells the user what THIS element
        is glued to (and which two bodies move together)."""
        try:
            if not self.editor.optical_led_glued():
                return ""
        except Exception:
            return ""
        key = str(label or "").strip().lower()
        if key == "led":
            return "  — glued to BS"
        if key == "optical":
            return "  — glued to LED"
        return ""

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
        # bugs/0364: the MV surrogate's stop row ("Aperture Stop", surface "Aperture")
        # sits BETWEEN the two Thin-Lens groups -- it belongs to the Imaging Lens, so
        # hiding that category hides the whole imaging system (the flagged "residual
        # plane"). A row that merely mentions "aperture" (the teaching scene's BS-exit
        # stop, a Standard row) keeps its Layout bucket.
        if "aperture stop" in text or str(getattr(row, "surface", "") or "").strip().lower() == "aperture":
            return "lens"
        if any(token in text for token in ("lens", "objective", "doublet", "gauss", "achromat")):
            return "lens"
        return "layout"

    def _element_key_for_row(self, row: object) -> str:
        try:
            return str(self.editor._element_key(row) or "").strip()
        except Exception:
            return str(getattr(row, "element", "") or "").strip()

    def _scene_element_block_for_row(self, rows: list[object], row_index: int) -> tuple[int, int]:
        try:
            start, end = self.editor._element_block_for_index(rows, int(row_index))
            return int(start), int(end)
        except Exception:
            pass
        key = self._element_key_for_row(rows[int(row_index)]) if 0 <= int(row_index) < len(rows) else ""
        if not key:
            return int(row_index), int(row_index)
        start = int(row_index)
        end = int(row_index)
        while start > 0 and self._element_key_for_row(rows[start - 1]) == key:
            start -= 1
        while end + 1 < len(rows) and self._element_key_for_row(rows[end + 1]) == key:
            end += 1
        return start, end

    @staticmethod
    def _element_iid(start: int, end: int) -> str:
        return f"element:{int(start)}:{int(end)}"

    @staticmethod
    def _parse_element_iid(iid: str) -> tuple[int, int] | None:
        parts = str(iid or "").split(":")
        if len(parts) != 3 or parts[0] != "element":
            return None
        try:
            start = int(parts[1])
            end = int(parts[2])
        except Exception:
            return None
        if end < start:
            start, end = end, start
        return start, end

    def _element_visible_indices(self, start: int, end: int) -> list[int]:
        visible = set(self._visible_scene_row_indices())
        rows = list(getattr(self.editor, "rows", []) or [])
        promoted = {row_index for row_index, _label, _name in self._promoted_step_rows()}
        return [
            index
            for index in range(int(start), int(end) + 1)
            if index in visible and index not in promoted and 0 <= index < len(rows)
        ]

    def _scene_component_records(self) -> list[dict[str, object]]:
        rows = list(getattr(self.editor, "rows", []) or [])
        promoted = {row_index for row_index, _label, _name in self._promoted_step_rows()}
        visible = set(self._visible_scene_row_indices())
        consumed: set[int] = set()
        records: list[dict[str, object]] = []
        for row_index in sorted(visible):
            if row_index in consumed or row_index in promoted or row_index < 0 or row_index >= len(rows):
                continue
            row = rows[row_index]
            element_key = self._element_key_for_row(row)
            start, end = self._scene_element_block_for_row(rows, row_index)
            block_indices = [
                index
                for index in range(start, end + 1)
                if index in visible and index not in promoted and 0 <= index < len(rows)
            ]
            if element_key and len(block_indices) > 1:
                first_row = rows[block_indices[0]]
                category = self._scene_row_category(block_indices[0], first_row)
                records.append(
                    {
                        "kind": "element",
                        "start": int(block_indices[0]),
                        "end": int(block_indices[-1]),
                        "category": category,
                        "name": element_key,
                        "children": list(block_indices),
                    }
                )
                consumed.update(block_indices)
                continue
            records.append(
                {
                    "kind": "scene-row",
                    "row_index": int(row_index),
                    "category": self._scene_row_category(int(row_index), row),
                    "name": self._scene_row_display_name(int(row_index), row),
                    "children": [int(row_index)],
                }
            )
            consumed.add(int(row_index))
        return records

    def _scene_source_browser_rows(self) -> list[tuple[str, str]]:
        """(source_id, name) for each scene source that draws as a first-class glyph (bugs/0283) --
        the same enabled, non-marker set the 3D glyph builder uses, so the browser row and the drawn
        object stay in lock-step."""
        rows: list[tuple[str, str]] = []
        try:
            descriptors = self.editor._drawable_scene_source_descriptors()
        except Exception:
            return []
        for source in descriptors or []:
            source_id = str(getattr(source, "source_id", "") or "")
            if not source_id:
                continue
            rows.append((source_id, str(getattr(source, "name", "") or "Scene source")))
        return rows

    def _scene_row_records(self) -> list[tuple[int, str, str]]:
        records: list[tuple[int, str, str]] = []
        rows = list(getattr(self.editor, "rows", []) or [])
        for record in self._scene_component_records():
            for row_index in list(record.get("children", []) or []):
                try:
                    row_index_int = int(row_index)
                except Exception:
                    continue
                if row_index_int < 0 or row_index_int >= len(rows):
                    continue
                records.append(
                    (
                        row_index_int,
                        self._scene_row_category(row_index_int, rows[row_index_int]),
                        self._scene_row_display_name(row_index_int, rows[row_index_int]),
                    )
                )
        return records

    def _scene_element_records(self) -> list[tuple[int, int, str, str, list[int]]]:
        records: list[tuple[int, int, str, str, list[int]]] = []
        for record in self._scene_component_records():
            if record.get("kind") != "element":
                continue
            records.append(
                (
                    int(record.get("start", 0)),
                    int(record.get("end", 0)),
                    str(record.get("category", "layout") or "layout"),
                    str(record.get("name", "") or "Element"),
                    [int(index) for index in list(record.get("children", []) or [])],
                )
            )
        return records

    def _current_browser_selection_iid(self) -> str:
        selected = str(getattr(self.editor, "_selected_step_label", "") or "").strip().lower()
        if selected and self.editor._step_path_for_label(selected) is not None:
            return f"overlay:{selected}"
        remembered = str(self._selected_item_id or "")
        current_row = None
        try:
            current_row = self.editor._current_selected_row_index()
        except Exception:
            current_row = None
        if remembered.startswith("scene-row:"):
            try:
                remembered_row = int(remembered.split(":", 1)[1])
            except Exception:
                remembered_row = None
            if remembered_row is not None and current_row == remembered_row and remembered_row in self._visible_scene_row_indices():
                return remembered
        element_span = self._parse_element_iid(remembered)
        if element_span is not None and current_row is not None:
            start, end = element_span
            if start <= int(current_row) <= end:
                return remembered
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
                rows = list(getattr(self.editor, "rows", []) or [])
                if 0 <= row_index < len(rows):
                    start, end = self._scene_element_block_for_row(rows, row_index)
                    visible_indices = self._element_visible_indices(start, end)
                    if self._element_key_for_row(rows[row_index]) and len(visible_indices) > 1:
                        return self._element_iid(visible_indices[0], visible_indices[-1])
                return f"scene-row:{row_index}"
        return ""

    def refresh(self) -> None:
        tree = self._tree
        if tree is None:
            return
        previous = self._current_browser_selection_iid() or self._selected_item_id
        # Capture each item's open state before destroying the tree so
        # that selecting an item (which triggers refresh) doesn't
        # collapse other expanded element groups. Without this every
        # click would reset all elements to "open=False" -- the
        # symptom: "when I click one sub-group, the other closes".
        previous_open_state: dict[str, bool] = {}
        try:
            stack = list(tree.get_children(""))
            while stack:
                iid = stack.pop()
                try:
                    previous_open_state[str(iid)] = bool(tree.item(iid, "open"))
                except Exception:
                    pass
                stack.extend(tree.get_children(iid))
        except Exception:
            previous_open_state = {}
        self._refreshing = True
        try:
            tree.delete(*tree.get_children(""))
            category_iids: dict[str, str] = {}
            category_counts: dict[str, int] = {}
            for key, title, _labels in self.CATEGORY_SPECS:
                iid = f"category:{key}"
                tree.insert(
                    "",
                    "end",
                    iid=iid,
                    text=title,
                    open=previous_open_state.get(iid, True),
                )
                category_iids[key] = iid
                category_counts[key] = 0
            # Display / Overlays: rays + overlay toggles as hide/unhide elements.
            for spec_key, spec_label, _owner, _var_name in self._display_toggle_specs():
                if self._display_var_for_key(spec_key) is None:
                    continue
                tree.insert(category_iids["display"], "end", iid=f"display:{spec_key}", text=spec_label,
                            tags=self._item_hidden_tag(display_key=spec_key))
                category_counts["display"] += 1
            for _key, _title, labels in self.CATEGORY_SPECS:
                for label in labels:
                    if self.editor._step_path_for_label(label) is None:
                        continue
                    category = self._category_for_label(label)
                    display = self.editor._step_overlay_display_label(label)
                    name = self._step_path_name(label)
                    text = f"{display}: {name}" if name else f"{display} STEP"
                    text += self._glue_partner_suffix(label)
                    tree.insert(category_iids[category], "end", iid=f"overlay:{label}", text=text,
                                tags=self._item_hidden_tag(label=label))
                    category_counts[category] += 1
            for row_index, label, name in self._promoted_step_rows():
                category = self._category_for_label(label)
                row_text = f"S{row_index}: {name}" + self._glue_partner_suffix(label)
                tree.insert(category_iids[category], "end", iid=f"row:{row_index}", text=row_text,
                            tags=self._item_hidden_tag(rows=[row_index]))
                category_counts[category] += 1
            rows = list(getattr(self.editor, "rows", []) or [])
            for record in self._scene_component_records():
                kind = str(record.get("kind", "") or "")
                category = str(record.get("category", "layout") or "layout")
                parent = category_iids.get(category, category_iids["layout"])
                count_key = category if category in category_counts else "layout"
                if kind == "element":
                    children = [int(index) for index in list(record.get("children", []) or [])]
                    if not children:
                        continue
                    start = int(record.get("start", children[0]))
                    end = int(record.get("end", children[-1]))
                    element_iid = self._element_iid(start, end)
                    name = str(record.get("name", "") or "Element")
                    tree.insert(
                        parent,
                        "end",
                        iid=element_iid,
                        text=f"{name} ({len(children)} surfaces)",
                        open=previous_open_state.get(element_iid, False),
                        tags=self._item_hidden_tag(rows=children),
                    )
                    category_counts[count_key] += 1
                    for row_index in children:
                        if row_index < 0 or row_index >= len(rows):
                            continue
                        row_name = self._scene_row_display_name(row_index, rows[row_index])
                        tree.insert(element_iid, "end", iid=f"scene-row:{row_index}", text=f"S{row_index}: {row_name}",
                                    tags=self._item_hidden_tag(rows=[row_index]))
                    continue
                if kind == "scene-row":
                    row_index = int(record.get("row_index", -1))
                    name = str(record.get("name", "") or f"Surface {row_index}")
                    tree.insert(parent, "end", iid=f"scene-row:{row_index}", text=f"S{row_index}: {name}",
                                tags=self._item_hidden_tag(rows=[row_index]))
                    category_counts[count_key] += 1
            # bugs/0283: scene sources (emitting LEDs etc.) as first-class rows under "Scene Sources",
            # each hide/unhide-able like a scene element.
            for source_id, source_name in self._scene_source_browser_rows():
                tree.insert(category_iids["sources"], "end", iid=f"source:{source_id}", text=source_name,
                            tags=self._item_hidden_tag(source_id=source_id))
                category_counts["sources"] += 1
            for key, parent_iid in category_iids.items():
                if category_counts.get(key, 0) <= 0:
                    tree.insert(parent_iid, "end", iid=f"empty:{key}", text="(empty)")
            # Don't restore an `overlay:<label>` selection that no longer
            # matches the editor's `_selected_step_label`. Otherwise the
            # tree's selection_set re-fires <<TreeviewSelect>> *after*
            # _refreshing flips back to False, the callback runs
            # `select_step_overlay_from_admin(label)`, and the rotation
            # handles silently reappear after a snap that cleared the
            # editor-side selection on purpose ("rotation handles pop
            # up after previous action").
            if previous and previous.startswith("overlay:"):
                label = previous.split(":", 1)[1]
                current = str(getattr(self.editor, "_selected_step_label", "") or "").strip().lower()
                if current != label:
                    previous = ""
            if previous and tree.exists(previous):
                tree.selection_set(previous)
                tree.focus(previous)
                self._selected_item_id = previous
            else:
                self._selected_item_id = ""
            # bugs/0049: keep every overlay in the canvas multi-select set
            # highlighted, not just the primary, so a browser Shift+click reads
            # back as a multi-selection after the panel rebuilds. (Runs while
            # _refreshing is True, so the <<TreeviewSelect>> guard stays armed.)
            for extra_label in set(getattr(self.inspector, "_selected_step_labels", None) or ()):
                extra_iid = f"overlay:{extra_label}"
                if extra_iid != previous and tree.exists(extra_iid):
                    try:
                        tree.selection_add(extra_iid)
                    except Exception:
                        pass
        finally:
            self._refreshing = False
        if self._selected_item_id:
            self._update_properties(self._selected_item_id)
        else:
            self._update_properties("")

    def clear_selection(self, *, update_properties: bool = True) -> None:
        """Clear the browser selection without re-selecting the previous STEP."""
        tree = self._tree
        self._selected_item_id = ""
        if tree is None:
            if update_properties:
                self._update_properties("")
            return
        self._refreshing = True
        try:
            try:
                selection = tree.selection()
                if selection:
                    tree.selection_remove(selection)
            except Exception:
                pass
            try:
                tree.focus("")
            except Exception:
                pass
        finally:
            self._refreshing = False
        if update_properties:
            self._update_properties("")

    def _on_tree_select(self, _event=None) -> None:
        if self._refreshing:
            return
        tree = self._tree
        if tree is None:
            return
        selection = tree.selection()
        if len(selection) > 1:
            # bugs/0049: a multi-overlay highlight is owned by the canvas
            # rotation-gizmo multi-select set and is re-applied during refresh.
            # A deferred <<TreeviewSelect>> from that programmatic re-highlight
            # must not collapse the set back to a single pick -- browse mode
            # never produces a multi-selection from a real user click.
            focus_iid = str(tree.focus() or selection[0])
            self._selected_item_id = focus_iid
            self._update_properties(focus_iid)
            return
        iid = str(selection[0]) if selection else ""
        if not iid or iid.startswith("category:") or iid.startswith("empty:"):
            self._selected_item_id = ""
            self._update_properties("")
            return
        if iid.startswith("display:"):
            # Rays / overlays: no 3D selection, just a hide/unhide target.
            self._selected_item_id = iid
            self._update_properties("")
            return
        if iid.startswith("source:"):
            # bugs/0283: a scene source is a hide/unhide target in the browser.
            # bugs/0426: it is ALSO now selectable -> raise its interactive MOVE gizmo (XYZ arrows) so
            # the LED can be dragged/placed like an optical element.
            self._selected_item_id = iid
            try:
                self.inspector.select_scene_source_from_admin(iid.split(":", 1)[1])
            except Exception as exc:
                self.inspector.status_var.set(f"Select source failed: {exc}")
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
        elif iid.startswith("element:"):
            span = self._parse_element_iid(iid)
            if span is None:
                self.inspector.select_scene_row_from_admin(-1)
            else:
                start, end = span
                self.inspector.select_scene_element_from_admin(start, end)
        self._update_properties(iid)

    def _on_tree_shift_click(self, event):
        """bugs/0049: Shift+click an overlay row toggles it into the rotation-
        gizmo multi-select set (mirrors the 3D canvas). Other row kinds fall
        through to the default single-select binding."""
        tree = self._tree
        if tree is None or self._refreshing:
            return None
        iid = tree.identify_row(event.y)
        if not iid or not iid.startswith("overlay:"):
            return None  # let the default binding single-select non-overlay rows
        label = iid.split(":", 1)[1]
        self.inspector.select_step_overlay_from_admin(label, additive=True)
        return "break"

    def _on_tree_right_click(self, event) -> str:
        tree = self._tree
        if tree is None:
            return "break"
        iid = tree.identify_row(event.y)
        # bugs/0284: right-clicking the Scene Sources group (its header or its "(empty)" placeholder)
        # offers the "Add Illumination Source (LED)" entry point rather than the usual no-op on a category.
        if iid in ("category:sources", "empty:sources"):
            self._show_scene_sources_context_menu(event)
            return "break"
        if not iid or iid.startswith("empty:"):
            return "break"
        if iid.startswith("category:"):
            # bugs/0361: category headers ("Optical Element", "Imaging Lens", ...) must
            # reach the 0360 group Hide/Show menu -- the old gate swallowed the click
            # SILENTLY in the router, so the group menu was dead code for them (the 0348
            # trap class: the menu probe passed while the live click never arrived).
            # Skip the selection routing, matching the sources path, so the properties
            # pane stays untouched.
            self._show_element_context_menu(event, iid)
            return "break"
        try:
            tree.selection_set(iid)
            tree.focus(iid)
        except Exception:
            pass
        self._on_tree_select()  # route the selection to the editor + properties
        self._show_element_context_menu(event, iid)
        return "break"

    def _edit_scene_source(self, source_id: str) -> None:
        """bugs/0363: open the scene-source edit dialog for a browser source row."""
        try:
            from KrakenOS.UI.panels.open3d_source_edit_dialog import (
                open_scene_source_edit_dialog,
            )

            open_scene_source_edit_dialog(self.editor, self.inspector, str(source_id))
        except Exception as exc:
            try:
                self.inspector.status_var.set(f"Edit Source failed: {exc}")
            except Exception:
                pass

    def _show_scene_sources_context_menu(self, event) -> None:
        """bugs/0284: the Scene Sources group's right-click menu. "Add Illumination Source (LED)" creates
        a first-class emitting-LED scene source; its 0283 glyph + browser row appear on the refresh."""
        tree = self._tree
        if tree is None:
            return
        menu = tk.Menu(tree, tearoff=False)
        menu.add_command(label="Scene Sources", state="disabled")
        menu.add_separator()
        # bugs/0366: the FIRST ACTIVE ENTRY of a group menu must be Hide/Show, NEVER a
        # creator. The old menu put "Add Illumination Source (LED)" exactly where every
        # other group shows "Hide", so a group-hide spree silently CREATED a source --
        # the flagged "it is not hidden plus another illumination created".
        try:
            source_children = [
                child
                for child in tree.get_children("category:sources")
                if str(child).startswith("source:")
            ]
        except Exception:
            source_children = []
        if source_children:
            menu.add_command(
                label="Hide",
                command=lambda: self._set_element_hidden_cascade(
                    "category:sources", [], None, True, None, None
                ),
            )
            menu.add_command(
                label="Show",
                command=lambda: self._set_element_hidden_cascade(
                    "category:sources", [], None, False, None, None
                ),
            )
            menu.add_separator()
        menu.add_command(
            label="Add Illumination Source (LED)", command=self._add_illumination_led_source
        )
        # bugs/0402: the left Source panel was retired into the Scene Source Manager, so the
        # Scene Sources group is now the home for the full multi-source editor -- one right-click away.
        menu.add_separator()
        menu.add_command(label="Scene Source Manager...", command=self._open_scene_source_manager)
        # bugs/0403: robust dismiss-on-click-elsewhere (plain tk_popup sticks -- the VTK window eats the grab).
        self.inspector._popup_scene_component_menu(menu, event)

    def _add_illumination_led_source(self) -> None:
        self.inspector.add_illumination_led_source()
        self.refresh()  # re-list the tree so the new Scene Sources row appears

    def _open_scene_source_manager(self, source_id: str | None = None) -> None:
        """bugs/0402: open the full Scene Source Manager (the retired Source panel's new home).
        Optionally preselect a source_id when invoked from a specific source row."""
        try:
            self.editor.open_scene_source_manager(selected_source_id=source_id)
        except Exception as exc:  # keep the browser responsive if the dialog fails to open
            self.editor.append_debug(f"Open Scene Source Manager failed: {exc}")

    def _selection_rows_and_label(self, iid: str) -> tuple[list[int], str | None]:
        rows, label, _display, _source = self._resolve_iid_target(iid)
        return rows, label

    def _resolve_iid_target(self, iid: str) -> tuple[list[int], str | None, str | None, str | None]:
        rows: list[int] = []
        label: str | None = None
        display_key: str | None = None
        source_id: str | None = None
        if iid.startswith("display:"):
            display_key = iid.split(":", 1)[1]
        elif iid.startswith("overlay:"):
            label = iid.split(":", 1)[1]
        elif iid.startswith("source:"):
            source_id = iid.split(":", 1)[1]
        elif iid.startswith("scene-row:") or iid.startswith("row:"):
            try:
                rows = [int(iid.split(":", 1)[1])]
            except Exception:
                rows = []
        elif iid.startswith("element:"):
            span = self._parse_element_iid(iid)
            if span is not None:
                rows = self._element_visible_indices(span[0], span[1])
        return rows, label, display_key, source_id

    def _element_is_hidden(self, rows: list[int], label: str | None, display_key: str | None = None,
                           source_id: str | None = None) -> bool:
        inspector = self.inspector
        if display_key is not None:
            var = self._display_var_for_key(display_key)
            return var is not None and not bool(var.get())
        if source_id is not None:
            return inspector.is_source_hidden(source_id)
        if label is not None:
            return inspector.is_step_label_hidden(label)
        return bool(rows) and all(inspector.is_scene_row_hidden(r) for r in rows)

    def _item_hidden_tag(self, rows: list[int] | None = None, label: str | None = None,
                         display_key: str | None = None, source_id: str | None = None) -> tuple[str, ...]:
        try:
            return ("hidden",) if self._element_is_hidden(rows or [], label, display_key, source_id) else ()
        except Exception:
            return ()

    def _set_element_hidden(self, rows: list[int], label: str | None, hidden: bool,
                            display_key: str | None = None, source_id: str | None = None) -> None:
        inspector = self.inspector
        if display_key is not None:
            var = self._display_var_for_key(display_key)
            if var is None:
                return
            var.set(not hidden)
            try:
                inspector._on_scene_visibility_changed()  # refresh scene to honour the toggle
            except Exception:
                pass
            inspector.status_var.set(("Hid " if hidden else "Showing ") + f"{display_key} in 3D.")
        elif source_id is not None:
            inspector.set_source_hidden(source_id, hidden)
            inspector.status_var.set(("Hid " if hidden else "Unhid ") + "the scene source.")
        elif label is not None:
            inspector.set_step_label_hidden(label, hidden)
            inspector.status_var.set(("Hid " if hidden else "Unhid ") + "the selected scene element.")
        elif rows:
            inspector.set_scene_rows_hidden(rows, hidden)
            inspector.status_var.set(("Hid " if hidden else "Unhid ") + "the selected scene element.")
        else:
            return
        # bugs/0560: the grey-out tag is computed at INSERT time by `_item_hidden_tag`, so a
        # hide that does not rebuild the tree leaves the row black while the element is gone
        # from the 3-D view -- the user's "some hidden elements are not grayed out in the right
        # panel browser". Only the display-key path refreshed (via `_on_scene_visibility_changed`);
        # `set_scene_rows_hidden` / `set_step_label_hidden` / `set_source_hidden` each update
        # their hidden set, toggle the actors and render, but none of them touch the browser.
        # Refresh here instead of in each of them: this is the ONE place every hide/unhide from
        # the browser funnels through, so a future fifth path cannot forget it.
        try:
            self.refresh()
        except Exception:
            pass
        self.refresh()  # re-tag the tree so hidden items grey out

    def _iter_descendant_iids(self, iid: str):
        """bugs/0360: every descendant iid under a tree node, depth-first."""
        tree = self._tree
        if tree is None:
            return
        try:
            stack = list(tree.get_children(iid))
        except Exception:
            return
        while stack:
            child = stack.pop()
            yield str(child)
            try:
                stack.extend(tree.get_children(child))
            except Exception:
                continue

    def _set_element_hidden_cascade(self, iid: str, rows, label, hidden: bool, display_key, source_id) -> None:
        """bugs/0360: hide/show a PARENT and every resolvable descendant in one click
        (the user's 'right click the parent Hide and all its children hide')."""
        count = 0
        if rows or label is not None or display_key is not None or source_id is not None:
            try:
                self._set_element_hidden(rows, label, hidden, display_key, source_id)
                count += 1
            except Exception:
                pass
        for child in self._iter_descendant_iids(iid):
            c_rows, c_label, c_display_key, c_source_id = self._resolve_iid_target(child)
            if not c_rows and c_label is None and c_display_key is None and c_source_id is None:
                continue
            try:
                self._set_element_hidden(c_rows, c_label, hidden, c_display_key, c_source_id)
                count += 1
            except Exception:
                continue
        self.inspector.status_var.set(
            ("Hid " if hidden else "Showing ") + f"{count} scene item(s) under this group."
        )

    def _show_element_context_menu(self, event, iid: str) -> None:
        rows, label, display_key, source_id = self._resolve_iid_target(iid)
        has_children = False
        try:
            has_children = bool(self._tree is not None and self._tree.get_children(iid))
        except Exception:
            has_children = False
        if not rows and label is None and display_key is None and source_id is None:
            if not has_children:
                return
            # bugs/0360: a pure GROUP node (parent with children, no element identity of
            # its own) -- Hide/Show cascades over every resolvable descendant.
            menu = tk.Menu(self.inspector, tearoff=False)
            group_name = ""
            try:
                group_name = str(self._tree.item(iid, "text")) if self._tree is not None else ""
            except Exception:
                group_name = ""
            menu.add_command(label=(group_name.strip() or "Group"), state="disabled")
            menu.add_separator()
            menu.add_command(
                label="Hide",
                command=lambda: self._set_element_hidden_cascade(iid, [], None, True, None, None),
            )
            menu.add_command(
                label="Show",
                command=lambda: self._set_element_hidden_cascade(iid, [], None, False, None, None),
            )
            self.inspector._popup_scene_component_menu(menu, event)  # bugs/0403: robust dismiss
            return
        hidden = self._element_is_hidden(rows, label, display_key, source_id)
        tree = self._tree
        name = ""
        try:
            name = str(tree.item(iid, "text")) if tree is not None else ""
        except Exception:
            name = ""
        menu = tk.Menu(self.inspector, tearoff=False)
        if name:
            menu.add_command(label=name.strip() or "Scene element", state="disabled")
            menu.add_separator()
        # bugs/0102: offer the SAME element-level CAD actions as the 3D-canvas
        # right-click (Promote / Glue / Resize / Unpromote / Open Face Editor /
        # Row Actions), keyed off the tree's element identity. This needs no
        # canvas face pick, so it is instant and reaches a body hidden under an
        # overlapping one -- the two reasons the user asked for it.
        added_actions = False
        try:
            service = self.inspector._face_assignment_service()
            if label is not None:
                added_actions = bool(service.append_element_context_actions(menu, step_label=label))
            elif rows:
                added_actions = bool(service.append_element_context_actions(menu, row_index=rows[0]))
        except Exception as exc:
            try:
                self.inspector.append_debug(f"Scene-tree element actions failed: {exc}")
            except Exception:
                pass
        if added_actions:
            menu.add_separator()
        if source_id is not None:
            # bugs/0537 follow-up ("right click seat still not functioning"): the seat
            # must be reachable from the place the user demonstrably works -- the
            # browser row they used to CREATE the source. Auto-resolves the housing
            # floor; no face pick involved.
            menu.add_command(
                label="Seat on the LED floor (auto)",
                command=lambda sid=source_id: self.inspector._face_assignment_service()._seat_source_on_led_floor_auto(sid),
            )
            # bugs/0363: the general 3D source element -- edit dims/aim/position in place.
            menu.add_command(
                label="Edit Source…",
                command=lambda sid=source_id: self._edit_scene_source(sid),
            )
            # bugs/0402: jump to the full Scene Source Manager (retired Source panel's home),
            # preselecting this source, for the fields Edit Source doesn't expose.
            menu.add_command(
                label="Scene Source Manager...",
                command=lambda sid=source_id: self._open_scene_source_manager(sid),
            )
            # bugs/0512: glue the emitter to the LED housing so the 0505 station slide and
            # the 0508 B assembly drag carry the illumination source too (flag_20260802_204536).
            try:
                from KrakenOS.UI.scene_source_analysis import source_spec_bool as _src_bool

                _specs = self.editor._normalize_scene_source_specs(
                    getattr(self.editor, "layout_scene_source_specs", []) or []
                )
                _spec = next(
                    (s for s in _specs if str(s.get("source_id", "") or "") == str(source_id)),
                    None,
                )
            except Exception:
                _spec = None
            if _spec is not None:
                _glued = _src_bool(_spec, "glued_to_led", False)
                menu.add_command(
                    label=("Unglue Source from LED" if _glued else "Glue Source to LED (move together)"),
                    command=lambda sid=source_id, g=_glued: self.editor.update_scene_source_spec(
                        sid,
                        {"glued_to_led": (not g)},
                        status=(
                            "Unglued the source from the LED (free-placed)."
                            if g
                            else "Glued the source to the LED -- it rides the LED/BS assembly."
                        ),
                    ),
                )
            menu.add_separator()
        # bugs/0405: the detector is the final "Image" row. Offer "remove defocus" from the browser
        # so the user does NOT have to HIDE the camera to right-click the detector occluded behind it
        # in the 3D view (flag_20260722_143106 "I need to hide the camera -> right click the detector").
        try:
            editor_rows = list(getattr(self.editor, "rows", []) or [])
            is_detector_row = any(
                0 <= int(r) < len(editor_rows)
                and str(getattr(editor_rows[int(r)], "surface", "") or "") == "Image"
                for r in (rows or [])
            )
        except Exception:
            is_detector_row = False
        if is_detector_row:
            menu.add_command(
                label="Snap detector to image plane (remove defocus)",
                command=self.inspector._snap_detector_to_image_plane,
            )
            menu.add_separator()
        show_word = "Show" if display_key is not None else "Unhide"
        if has_children:
            # bugs/0360: a PARENT element -- Hide/Show applies to it AND every child.
            if hidden:
                menu.add_command(
                    label=show_word,
                    command=lambda: self._set_element_hidden_cascade(iid, rows, label, False, display_key, source_id),
                )
            else:
                menu.add_command(
                    label="Hide",
                    command=lambda: self._set_element_hidden_cascade(iid, rows, label, True, display_key, source_id),
                )
        elif hidden:
            menu.add_command(label=show_word, command=lambda: self._set_element_hidden(rows, label, False, display_key, source_id))
        else:
            menu.add_command(label="Hide", command=lambda: self._set_element_hidden(rows, label, True, display_key, source_id))
        if display_key is None and source_id is None:  # rays / overlays / sources can't be deleted here
            menu.add_separator()
            menu.add_command(label="Delete", command=self._delete_selected)
        self.inspector._popup_scene_component_menu(menu, event)  # bugs/0403: robust dismiss

    def _current_kind_value(self) -> tuple[str, str]:
        iid = str(self._selected_item_id or "")
        if ":" not in iid:
            return "", ""
        kind, value = iid.split(":", 1)
        return kind, value

    def _selection_flags_for_iid(self, iid: str) -> dict[str, bool]:
        """bugs/0063: derive the "Selected Element" action gating purely from
        the browser iid + editor state. Both a browser-tree click and a direct
        3D-canvas pick land on the same iid, so routing the canvas pick through
        these flags lights exactly the same buttons the browser click does."""
        overlay = False
        promoted_row = False
        file_backed_row = False
        centerable_row = False
        iid = str(iid or "")
        rows = list(getattr(self.editor, "rows", []) or [])
        if iid.startswith("overlay:"):
            label = iid.split(":", 1)[1]
            overlay = self.editor._step_path_for_label(label) is not None
        elif iid.startswith("row:"):
            try:
                row_index = int(iid.split(":", 1)[1])
            except Exception:
                row_index = -1
            if 0 <= row_index < len(rows):
                promoted_row = True
                file_backed_row = True
        elif iid.startswith("scene-row:"):
            try:
                row_index = int(iid.split(":", 1)[1])
            except Exception:
                row_index = -1
            if 0 <= row_index < len(rows):
                try:
                    file_backed_row = self.editor._file_backed_stl_row_at(row_index) is not None
                except Exception:
                    file_backed_row = False
                surface = str(getattr(rows[row_index], "surface", "") or "")
                centerable_row = surface not in {"Object", "Image"}
        elif iid.startswith("element:"):
            span = self._parse_element_iid(iid)
            if span is not None:
                start, end = span
                indices = [index for index in self._element_visible_indices(start, end) if 0 <= index < len(rows)]
                centerable_row = any(
                    str(getattr(rows[index], "surface", "") or "") not in {"Object", "Image"}
                    for index in indices
                )
        return {
            "overlay": overlay,
            "promoted_row": promoted_row,
            "file_backed_row": file_backed_row,
            "centerable_row": centerable_row,
        }

    @staticmethod
    def _compute_selection_button_states(flags: dict[str, bool]) -> dict[str, bool]:
        overlay = bool(flags.get("overlay"))
        promoted_row = bool(flags.get("promoted_row"))
        file_backed_row = bool(flags.get("file_backed_row"))
        centerable_row = bool(flags.get("centerable_row"))
        return {
            "carry": overlay,
            "accept": overlay,
            "promote": overlay,
            "native": overlay,
            "delete": overlay or promoted_row,
            "faces": promoted_row or file_backed_row,
            "center": overlay or promoted_row or centerable_row,
            "normal": overlay,
            "pick_normal": overlay,
            "surface_center": overlay,
        }

    def select_from_canvas(self, iid: str) -> None:
        """bugs/0063: mirror a direct 3D-canvas pick into the browser so the
        "Selected Element" action buttons enable exactly as a browser-tree
        click does. The canvas-pick handlers set the editor/inspector selection
        and rotation gizmo but never touched this panel, so for a canvas pick
        the buttons stayed grayed while a browser click enabled them."""
        iid = str(iid or "")
        self._selected_item_id = iid
        tree = self._tree
        if tree is not None:
            self._refreshing = True
            try:
                if iid and tree.exists(iid):
                    tree.selection_set(iid)
                    tree.focus(iid)
                    try:
                        tree.see(iid)
                    except Exception:
                        pass
                else:
                    current = tree.selection()
                    if current:
                        tree.selection_remove(current)
            finally:
                self._refreshing = False
        self._update_properties(iid)

    def _update_properties(self, iid: str) -> None:
        values = {
            "name": "-",
            "kind": "-",
            "file": "-",
            "pose": "-",
            "faces": "-",
        }
        flags = self._selection_flags_for_iid(iid)
        rows = list(getattr(self.editor, "rows", []) or [])
        if iid.startswith("overlay:") and flags["overlay"]:
            label = iid.split(":", 1)[1]
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
        elif iid.startswith("row:") and flags["promoted_row"]:
            row_index = int(iid.split(":", 1)[1])
            row = rows[row_index]
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
            if 0 <= row_index < len(rows):
                row = rows[row_index]
                surface = str(getattr(row, "surface", "") or "")
                advanced = getattr(row, "advanced", {}) if not isinstance(row, dict) else row.get("advanced", {})
                face_metadata = advanced.get("OpticalSolidFaces", {}) if isinstance(advanced, dict) else {}
                assigned = len(face_metadata) if isinstance(face_metadata, dict) else 0
                values.update(
                    {
                        "name": self._scene_row_display_name(row_index, row),
                        "kind": f"Editable table row S{row_index}",
                        "file": "CAD/STL row" if flags["file_backed_row"] else "Table",
                        "pose": (
                            f"T=({float(getattr(row, 'thickness', 0.0) or 0.0):.3g}) "
                            f"D=({float(getattr(row, 'desp_x', 0.0) or 0.0):.3g},"
                            f"{float(getattr(row, 'desp_y', 0.0) or 0.0):.3g},"
                            f"{float(getattr(row, 'desp_z', 0.0) or 0.0):.3g})"
                        ),
                        "faces": f"{assigned} assigned" if flags["file_backed_row"] else str(surface or "-"),
                    }
                )
        elif iid.startswith("element:"):
            span = self._parse_element_iid(iid)
            if span is not None:
                start, end = span
                indices = self._element_visible_indices(start, end)
                valid_indices = [index for index in indices if 0 <= index < len(rows)]
                if valid_indices:
                    first_row = rows[valid_indices[0]]
                    name = self._element_key_for_row(first_row) or self._scene_row_display_name(valid_indices[0], first_row)
                    file_backed_count = 0
                    face_count = 0
                    for index in valid_indices:
                        try:
                            if self.editor._file_backed_stl_row_at(index) is not None:
                                file_backed_count += 1
                        except Exception:
                            pass
                        advanced = getattr(rows[index], "advanced", {}) if not isinstance(rows[index], dict) else rows[index].get("advanced", {})
                        face_metadata = advanced.get("OpticalSolidFaces", {}) if isinstance(advanced, dict) else {}
                        if isinstance(face_metadata, dict):
                            face_count += len(face_metadata)
                    values.update(
                        {
                            "name": str(name or "Element"),
                            "kind": f"Grouped table element S{valid_indices[0]}-S{valid_indices[-1]}",
                            "file": f"{file_backed_count} CAD/STL row(s)" if file_backed_count else "Table",
                            "pose": f"{len(valid_indices)} visible surface row(s)",
                            "faces": f"{face_count} assigned" if file_backed_count else "Grouped element",
                        }
                    )
        for key, value in values.items():
            var = self._property_vars.get(key)
            if var is not None:
                var.set(value)
        button_states = self._compute_selection_button_states(flags)
        for key, button in self._selection_buttons.items():
            try:
                button.configure(state="normal" if button_states.get(key, False) else "disabled")
            except Exception:
                pass
        if self._face_direction_combo is not None:
            try:
                self._face_direction_combo.configure(state="readonly" if flags["overlay"] else "disabled")
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
        if kind == "element":
            span = self._parse_element_iid(self._selected_item_id)
            if span is None:
                return False
            start, end = span
            return bool(self.inspector.select_scene_element_from_admin(start, end))
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

    def _native_selected(self) -> None:
        if not self._select_current_for_action():
            return
        label = str(getattr(self.editor, "_selected_step_label", "") or "").strip().lower()
        display = self.editor._step_overlay_display_label(label) if label else "STEP"
        materials = simpledialog.askstring(
            "Native STEP Materials",
            (
                f"Glass/material sequence after each native {display} surface.\n"
                "Example for a cemented achromat: BK7, F2, AIR"
            ),
            initialvalue="BK7, F2, AIR",
            parent=self.inspector,
        )
        if materials is None:
            return
        self.inspector.promote_selected_step_to_native_surface_rows(glass_sequence=materials)
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
        if kind in {"row", "scene-row", "element"}:
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
