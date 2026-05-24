"""Scene Source Manager dialog."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

import numpy as np


class MainSceneSourceManagerDialog:
    """Own the Scene Source Manager while delegating source state to the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        source_model_values: tuple[str, ...],
        source_model_default: str,
        source_direction_preset_values: tuple[str, ...],
        source_angular_weight_default: str,
        source_angular_weight_values: tuple[str, ...],
        source_row_order_default: str,
        source_row_order_before_object: str,
        source_row_order_after_object: str,
        normalize_source_row_order: Callable[[object], str],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "source_model_values", tuple(source_model_values))
        object.__setattr__(self, "source_model_default", source_model_default)
        object.__setattr__(self, "source_direction_preset_values", tuple(source_direction_preset_values))
        object.__setattr__(self, "source_angular_weight_default", source_angular_weight_default)
        object.__setattr__(self, "source_angular_weight_values", tuple(source_angular_weight_values))
        object.__setattr__(self, "source_row_order_default", source_row_order_default)
        object.__setattr__(self, "source_row_order_before_object", source_row_order_before_object)
        object.__setattr__(self, "source_row_order_after_object", source_row_order_after_object)
        object.__setattr__(self, "normalize_source_row_order", normalize_source_row_order)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "source_model_values",
            "source_model_default",
            "source_direction_preset_values",
            "source_angular_weight_default",
            "source_angular_weight_values",
            "source_row_order_default",
            "source_row_order_before_object",
            "source_row_order_after_object",
            "normalize_source_row_order",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_scene_source_manager(
        self,
        selected_source_id: str | None = None,
        *,
        aim_row_index: int | None = None,
        aim_face_id: str = "",
    ) -> None:
        specs = [
            dict(spec)
            for spec in self._normalize_scene_source_specs(getattr(self, "layout_scene_source_specs", []))
        ]
        if not specs:
            specs = [self._scene_source_spec_from_current_panel()]
        specs = self._dedupe_scene_source_ids(specs)
        current_index = 0
        if selected_source_id:
            for index, spec in enumerate(specs):
                if str(spec.get("source_id", "")) == str(selected_source_id):
                    current_index = index
                    break

        window = tk.Toplevel(self.editor)
        window.title("Scene Source Manager")
        window.transient(self.editor)
        window.geometry("980x680")
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)

        root = ttk.Frame(window, padding=12)
        root.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(1, weight=1)

        intro = ttk.Label(
            root,
            text=(
                "Scene sources are source records, not KrakenOS surface rows. Physical emitter models launch independent "
                "illumination; Pupil / field is a nonphysical reference that stays synchronized with the left Source panel."
            ),
            wraplength=900,
            foreground="#475569",
        )
        intro.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        left = ttk.Frame(root)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        columns = ("id", "name", "model", "rays", "origin", "direction")
        tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse", height=12)
        headings = {
            "id": "ID",
            "name": "Name",
            "model": "Model",
            "rays": "Rays",
            "origin": "Origin XYZ",
            "direction": "Direction LMN",
        }
        widths = {"id": 110, "name": 150, "model": 150, "rays": 60, "origin": 145, "direction": 145}
        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(column, width=widths[column], anchor="w", stretch=column in {"name", "origin", "direction"})
        tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(left, orient="vertical", command=tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=tree_scroll.set)

        button_row = ttk.Frame(left)
        button_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        row_order_var = tk.StringVar(
            value=self.normalize_source_row_order(getattr(self, "layout_scene_row_order", self.source_row_order_default))
        )
        row_order_frame = ttk.LabelFrame(left, text="Visible row order", padding=8)
        row_order_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Radiobutton(
            row_order_frame,
            text="Object, Source(s), Image",
            variable=row_order_var,
            value=self.source_row_order_after_object,
        ).pack(anchor="w")
        ttk.Radiobutton(
            row_order_frame,
            text="Source(s), Object, Image",
            variable=row_order_var,
            value=self.source_row_order_before_object,
        ).pack(anchor="w")

        form = ttk.LabelFrame(root, text="Selected Source", padding=10)
        form.grid(row=1, column=1, sticky="nsew")
        for column in range(4):
            form.columnconfigure(column, weight=1)

        vars: dict[str, tk.Variable] = {
            "enabled": tk.BooleanVar(master=window, value=True),
            "physical": tk.BooleanVar(master=window, value=True),
            "source_id": tk.StringVar(master=window, value="source:0"),
            "name": tk.StringVar(master=window, value="Source 1"),
            "role": tk.StringVar(master=window, value="illumination"),
            "model": tk.StringVar(master=window, value="Collimated disk source"),
            "ray_count": tk.StringVar(master=window, value="5"),
            "power": tk.StringVar(master=window, value="1.0"),
            "wavelength": tk.StringVar(master=window, value=str(self._current_wavelength())),
            "radius": tk.StringVar(master=window, value="1.0"),
            "cone_deg": tk.StringVar(master=window, value="0.0"),
            "seed": tk.StringVar(master=window, value="1"),
            "source_x": tk.StringVar(master=window, value="0.0"),
            "source_y": tk.StringVar(master=window, value="0.0"),
            "source_z": tk.StringVar(master=window, value="0.0"),
            "source_l": tk.StringVar(master=window, value="0.0"),
            "source_m": tk.StringVar(master=window, value="0.0"),
            "source_n": tk.StringVar(master=window, value="1.0"),
            "angular_weight": tk.StringVar(master=window, value=self.source_angular_weight_default),
            "waist_radius": tk.StringVar(master=window, value="0.5"),
            "waist_offset": tk.StringVar(master=window, value="0.0"),
            "m2": tk.StringVar(master=window, value="1.0"),
        }
        direction_preset_var = tk.StringVar(master=window, value="Horizontal +Z (right)")
        aim_target_choices = self._scene_source_aim_target_choices()
        requested_target_choice = ""
        if aim_row_index is not None:
            try:
                requested_target_choice = self._scene_source_target_choice_for(int(aim_row_index), aim_face_id)
            except Exception:
                requested_target_choice = ""
        aim_target_var = tk.StringVar(
            master=window,
            value=requested_target_choice or (aim_target_choices[-1] if aim_target_choices else ""),
        )
        placement_standoff_var = tk.StringVar(master=window, value="50.0")

        def label_entry(row: int, column: int, key: str, label: str, *, width: int = 12) -> None:
            ttk.Label(form, text=label).grid(row=row, column=column, sticky="w", pady=(0, 2), padx=(0 if column == 0 else 8, 0))
            ttk.Entry(form, textvariable=vars[key], width=width).grid(
                row=row + 1,
                column=column,
                sticky="ew",
                pady=(0, 8),
                padx=(0 if column == 0 else 8, 0),
            )

        ttk.Checkbutton(form, text="Enabled", variable=vars["enabled"]).grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Checkbutton(form, text="Physical emitter", variable=vars["physical"]).grid(row=0, column=1, sticky="w", pady=(0, 8), padx=(8, 0))
        ttk.Label(form, text="Model").grid(row=0, column=2, sticky="w", pady=(0, 2), padx=(8, 0))
        model_menu = ttk.Combobox(form, textvariable=vars["model"], values=self.source_model_values, state="readonly", width=18)
        model_menu.grid(row=1, column=2, columnspan=2, sticky="ew", pady=(0, 8), padx=(8, 0))

        label_entry(2, 0, "source_id", "Source ID", width=16)
        label_entry(2, 1, "name", "Name", width=18)
        label_entry(2, 2, "role", "Role", width=16)
        label_entry(2, 3, "ray_count", "Ray count")
        label_entry(4, 0, "power", "Power")
        label_entry(4, 1, "wavelength", "Wavelength [um]")
        label_entry(4, 2, "radius", "Radius [mm]")
        label_entry(4, 3, "cone_deg", "Cone half-angle [deg]")
        label_entry(6, 0, "source_x", "Source X [mm]")
        label_entry(6, 1, "source_y", "Source Y [mm]")
        label_entry(6, 2, "source_z", "Source Z [mm]")
        label_entry(6, 3, "seed", "Random seed")
        label_entry(8, 0, "source_l", "Direction L")
        label_entry(8, 1, "source_m", "Direction M")
        label_entry(8, 2, "source_n", "Direction N")

        ttk.Label(form, text="Angular weight").grid(row=8, column=3, sticky="w", pady=(0, 2), padx=(8, 0))
        angular_menu = ttk.Combobox(
            form,
            textvariable=vars["angular_weight"],
            values=self.source_angular_weight_values,
            state="readonly",
            width=18,
        )
        angular_menu.grid(row=9, column=3, sticky="ew", pady=(0, 8), padx=(8, 0))

        ttk.Label(form, text="Direction preset").grid(row=10, column=0, sticky="w", pady=(0, 2))
        direction_preset_menu = ttk.Combobox(
            form,
            textvariable=direction_preset_var,
            values=self.source_direction_preset_values,
            state="readonly",
            width=20,
        )
        direction_preset_menu.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(form, text="Aim direction at row").grid(row=12, column=0, sticky="w", pady=(0, 2))
        aim_target_menu = ttk.Combobox(
            form,
            textvariable=aim_target_var,
            values=aim_target_choices,
            state="readonly",
            width=28,
        )
        aim_target_menu.grid(row=13, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        ttk.Button(form, text="Aim Direction At Row", command=lambda: aim_direction_at_row()).grid(
            row=13,
            column=3,
            sticky="ew",
            pady=(0, 8),
            padx=(8, 0),
        )

        ttk.Label(form, text="Placement standoff [mm]").grid(row=14, column=0, sticky="w", pady=(0, 2))
        ttk.Entry(form, textvariable=placement_standoff_var, width=12).grid(
            row=15,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )
        ttk.Button(form, text="Place Origin At Standoff", command=lambda: place_origin_at_standoff()).grid(
            row=15,
            column=1,
            columnspan=3,
            sticky="ew",
            pady=(0, 8),
            padx=(8, 0),
        )

        label_entry(16, 0, "waist_radius", "GB waist [mm]")
        label_entry(16, 1, "waist_offset", "GB waist offset [mm]")
        label_entry(16, 2, "m2", "GB M2")

        validation_var = tk.StringVar(master=window, value="")
        ttk.Label(form, textvariable=validation_var, foreground="#475569", wraplength=420).grid(
            row=18,
            column=0,
            columnspan=4,
            sticky="ew",
            pady=(4, 0),
        )

        def _fmt(value: object, default: str = "0") -> str:
            if value is None:
                return default
            return str(value)

        def selected_index() -> int | None:
            selected = tree.selection()
            if not selected:
                return None
            try:
                return int(str(selected[0]).split("_", 1)[1])
            except Exception:
                return None

        def refresh_tree(select_index: int | None = None) -> None:
            tree.delete(*tree.get_children())
            for index, spec in enumerate(specs):
                source = self._scene_source_from_spec(spec, index, wavelength=self._current_wavelength())
                ox, oy, oz = np.asarray(source.origin, dtype=float).reshape(-1)[:3]
                dl, dm, dn = np.asarray(source.direction, dtype=float).reshape(-1)[:3]
                iid = f"source_{index}"
                tree.insert(
                    "",
                    "end",
                    iid=iid,
                    values=(
                        source.source_id,
                        source.name,
                        source.model,
                        str(source.ray_count),
                        f"{ox:.4g}, {oy:.4g}, {oz:.4g}",
                        f"{dl:.4g}, {dm:.4g}, {dn:.4g}",
                    ),
                )
            if specs:
                index = min(max(0, int(select_index if select_index is not None else 0)), len(specs) - 1)
                iid = f"source_{index}"
                tree.selection_set(iid)
                tree.focus(iid)
                tree.see(iid)
                load_form(index)

        def load_form(index: int) -> None:
            if not (0 <= index < len(specs)):
                return
            spec = dict(specs[index])
            defaults = self._default_scene_source_spec(index)
            form_values = dict(defaults)
            form_values.update(spec)

            def vector_for_form(vector_keys, component_keys, default_values) -> np.ndarray:
                if all(key in spec for key in component_keys):
                    return np.asarray(
                        [
                            self._source_spec_float(spec, key, float(default_values[component_index]))
                            for component_index, key in enumerate(component_keys)
                        ],
                        dtype=float,
                    )
                return self._source_spec_vector(form_values, vector_keys, component_keys, default_values)

            origin = vector_for_form(
                ("origin", "source_xyz", "xyz"),
                ("source_x", "source_y", "source_z"),
                (defaults["source_x"], defaults["source_y"], defaults["source_z"]),
            )
            direction = vector_for_form(
                ("direction", "source_lmn", "lmn"),
                ("source_l", "source_m", "source_n"),
                (defaults["source_l"], defaults["source_m"], defaults["source_n"]),
            )
            for key, value in (
                ("source_x", origin[0]),
                ("source_y", origin[1]),
                ("source_z", origin[2]),
                ("source_l", direction[0]),
                ("source_m", direction[1]),
                ("source_n", direction[2]),
            ):
                form_values[key] = float(value)
            for key in vars:
                if key in {"enabled", "physical"}:
                    value = form_values.get(key, True)
                    if isinstance(value, str):
                        bool_value = value.strip().lower() not in {"0", "false", "no", "off", "disabled"}
                    else:
                        bool_value = bool(value)
                    vars[key].set(bool_value)
                else:
                    vars[key].set(_fmt(form_values.get(key, "")))
            model = str(vars["model"].get()).strip()
            if model not in self.source_model_values:
                vars["model"].set("Collimated disk source")
            angular = str(vars["angular_weight"].get()).strip()
            if angular not in self.source_angular_weight_values:
                vars["angular_weight"].set(self.source_angular_weight_default)
            direction_preset_var.set(
                self._source_direction_preset_label(
                    (
                        vars["source_l"].get(),
                        vars["source_m"].get(),
                        vars["source_n"].get(),
                    )
                )
            )
            validation_var.set(f"Editing {spec.get('source_id', f'source:{index}')} - click Save Source before Apply.")

        def sync_model_reference_state(_event=None) -> None:
            model = str(vars["model"].get()).strip()
            if model == self.source_model_default:
                vars["physical"].set(False)
                vars["role"].set("pupil_field_reference")
            elif str(vars["role"].get()).strip() in {"", "pupil_field_reference"}:
                vars["physical"].set(True)
                vars["role"].set("illumination")

        def sync_direction_preset_from_form() -> None:
            direction_preset_var.set(
                self._source_direction_preset_label(
                    (
                        vars["source_l"].get(),
                        vars["source_m"].get(),
                        vars["source_n"].get(),
                    )
                )
            )

        def apply_direction_preset(_event=None) -> None:
            vector = self._source_direction_preset_vector(direction_preset_var.get())
            if vector is None:
                return
            for key, value in (
                ("source_l", vector[0]),
                ("source_m", vector[1]),
                ("source_n", vector[2]),
            ):
                vars[key].set(self._format_source_direction_component(float(value)))
            validation_var.set(
                "Direction preset applied: "
                f"LMN=({float(vector[0]):.4g}, {float(vector[1]):.4g}, {float(vector[2]):.4g}). "
                "Click Save Source before Apply."
            )

        direction_preset_menu.bind("<<ComboboxSelected>>", apply_direction_preset)
        model_menu.bind("<<ComboboxSelected>>", sync_model_reference_state)
        for key in ("source_l", "source_m", "source_n"):
            vars[key].trace_add("write", lambda *_args: sync_direction_preset_from_form())

        def parse_float(key: str, label: str, *, minimum: float | None = None) -> float:
            try:
                value = float(str(vars[key].get()).strip())
            except Exception as exc:
                raise ValueError(f"{label} expects a number.") from exc
            if not np.isfinite(value):
                raise ValueError(f"{label} must be finite.")
            if minimum is not None and value < minimum:
                raise ValueError(f"{label} must be >= {minimum:g}.")
            return float(value)

        def parse_int(key: str, label: str, *, minimum: int = 1) -> int:
            value = int(round(parse_float(key, label, minimum=float(minimum))))
            return max(int(minimum), value)

        def parse_standoff() -> float:
            try:
                value = float(str(placement_standoff_var.get()).strip())
            except Exception as exc:
                raise ValueError("Placement standoff expects a number.") from exc
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError("Placement standoff must be a positive number.")
            return float(value)

        def selected_aim_target() -> tuple[int, str]:
            text = str(aim_target_var.get() or "").strip()
            if not text:
                raise ValueError("Choose a target row for source aiming.")
            prefix = text.split(":", 1)[0].strip()
            row_text, _sep, face_id = prefix.partition("/")
            try:
                row_index = int(row_text)
            except Exception as exc:
                raise ValueError("Choose a valid target row for source aiming.") from exc
            if not (0 <= row_index < len(self.rows)):
                raise ValueError("Target row is out of range.")
            return row_index, str(face_id or "").strip()

        def aim_direction_at_row() -> None:
            try:
                row_index, face_id = selected_aim_target()
                result = self.scene_source_direction_to_row(
                    {
                        "source_x": parse_float("source_x", "Source X"),
                        "source_y": parse_float("source_y", "Source Y"),
                        "source_z": parse_float("source_z", "Source Z"),
                    },
                    row_index,
                    face_id=face_id,
                )
            except Exception as exc:
                validation_var.set(_short_error_message(exc))
                return
            for key in ("source_l", "source_m", "source_n"):
                vars[key].set(self._format_source_direction_component(float(result[key])))
            sync_direction_preset_from_form()
            target = result.get("target_point", (0.0, 0.0, 0.0))
            tx, ty, tz = np.asarray(target, dtype=float).reshape(3)
            validation_var.set(
                "Aimed source at {target_label}: "
                "target=({tx:.4g}, {ty:.4g}, {tz:.4g}) mm, distance={distance:.4g} mm. "
                "Click Save Source before Apply.".format(
                    target_label=str(result.get("target_label", result.get("row_name", ""))),
                    tx=float(tx),
                    ty=float(ty),
                    tz=float(tz),
                    distance=float(result.get("distance_mm", 0.0)),
                )
            )

        def place_origin_at_standoff() -> None:
            try:
                row_index, face_id = selected_aim_target()
                result = self.scene_source_place_at_row_standoff(
                    {
                        "source_l": parse_float("source_l", "Direction L"),
                        "source_m": parse_float("source_m", "Direction M"),
                        "source_n": parse_float("source_n", "Direction N"),
                    },
                    row_index,
                    parse_standoff(),
                    face_id=face_id,
                )
            except Exception as exc:
                validation_var.set(_short_error_message(exc))
                return
            for key in ("source_x", "source_y", "source_z", "source_l", "source_m", "source_n"):
                vars[key].set(self._format_source_direction_component(float(result[key])))
            sync_direction_preset_from_form()
            target = result.get("target_point", (0.0, 0.0, 0.0))
            tx, ty, tz = np.asarray(target, dtype=float).reshape(3)
            validation_var.set(
                "Placed source {distance:.4g} mm before {target_label}: "
                "target=({tx:.4g}, {ty:.4g}, {tz:.4g}) mm. "
                "Click Save Source before Apply.".format(
                    distance=float(result.get("distance_mm", 0.0)),
                    target_label=str(result.get("target_label", result.get("row_name", ""))),
                    tx=float(tx),
                    ty=float(ty),
                    tz=float(tz),
                )
            )

        def form_spec() -> dict[str, object]:
            source_id = str(vars["source_id"].get()).strip()
            if not source_id:
                raise ValueError("Source ID cannot be empty.")
            model = str(vars["model"].get()).strip()
            if model not in self.source_model_values:
                raise ValueError("Choose a valid source model.")
            radius = parse_float("radius", "Radius", minimum=0.0)
            cone_deg = min(parse_float("cone_deg", "Cone half-angle", minimum=0.0), 89.9)
            physical = bool(vars["physical"].get())
            role = str(vars["role"].get()).strip()
            if model == self.source_model_default:
                physical = False
                role = "pupil_field_reference"
            elif not role or role == "pupil_field_reference":
                role = "illumination"
            dl = parse_float("source_l", "Direction L")
            dm = parse_float("source_m", "Direction M")
            dn = parse_float("source_n", "Direction N")
            if float(np.linalg.norm([dl, dm, dn])) <= 1e-12:
                raise ValueError("Direction vector cannot be zero.")
            spec = {
                "source_id": source_id,
                "name": str(vars["name"].get()).strip() or source_id,
                "enabled": bool(vars["enabled"].get()),
                "physical": physical,
                "role": role,
                "model": model,
                "ray_count": parse_int("ray_count", "Ray count", minimum=1),
                "power": parse_float("power", "Power", minimum=0.0),
                "wavelength": parse_float("wavelength", "Wavelength", minimum=1e-12),
                "radius": radius,
                "cone_deg": cone_deg,
                "seed": parse_int("seed", "Random seed", minimum=0),
                "source_x": parse_float("source_x", "Source X"),
                "source_y": parse_float("source_y", "Source Y"),
                "source_z": parse_float("source_z", "Source Z"),
                "source_l": dl,
                "source_m": dm,
                "source_n": dn,
                "angular_weight": str(vars["angular_weight"].get()).strip() or self.source_angular_weight_default,
                "waist_radius": parse_float("waist_radius", "GB waist", minimum=1e-12),
                "waist_offset": parse_float("waist_offset", "GB waist offset"),
                "m2": parse_float("m2", "GB M2", minimum=1e-12),
            }
            if spec["angular_weight"] not in self.source_angular_weight_values:
                spec["angular_weight"] = self.source_angular_weight_default
            return {str(key): self._scene_source_setting_value(value) for key, value in spec.items()}

        def save_current_source() -> bool:
            index = selected_index()
            if index is None or not (0 <= index < len(specs)):
                return True
            try:
                spec = form_spec()
            except Exception as exc:
                validation_var.set(_short_error_message(exc))
                return False
            other_ids = {
                str(item.get("source_id", ""))
                for other_index, item in enumerate(specs)
                if other_index != index
            }
            if str(spec.get("source_id", "")) in other_ids:
                validation_var.set("Source ID must be unique.")
                return False
            specs[index] = spec
            refresh_tree(index)
            validation_var.set(f"Saved {spec['source_id']} in the manager. Click Apply to update the layout.")
            return True

        def add_source() -> None:
            if not save_current_source():
                return
            specs.append(self._default_scene_source_spec(len(specs)))
            refresh_tree(len(specs) - 1)

        def add_from_panel() -> None:
            if not save_current_source():
                return
            source_id = f"source:{len(specs)}"
            specs.append(self._scene_source_spec_from_current_panel(source_id=source_id, name=f"Source {len(specs) + 1}"))
            refresh_tree(len(specs) - 1)

        def duplicate_source() -> None:
            index = selected_index()
            if index is None or not (0 <= index < len(specs)) or not save_current_source():
                return
            duplicate = dict(specs[index])
            duplicate["source_id"] = f"{duplicate.get('source_id', f'source:{index}')}_copy"
            duplicate["name"] = f"{duplicate.get('name', f'Source {index + 1}')} Copy"
            specs.insert(index + 1, duplicate)
            deduped = self._dedupe_scene_source_ids(specs)
            specs[:] = deduped
            refresh_tree(index + 1)

        def delete_source() -> None:
            index = selected_index()
            if index is None or not (0 <= index < len(specs)):
                return
            del specs[index]
            refresh_tree(min(index, len(specs) - 1) if specs else None)

        def clear_to_panel() -> None:
            self._set_scene_source_specs(
                [],
                row_order=row_order_var.get(),
                record_history=True,
                status="Scene sources cleared; using the Source panel fallback. Click Update.",
            )
            window.destroy()

        def apply_sources() -> None:
            if not save_current_source():
                return
            self._set_scene_source_specs(
                specs,
                row_order=row_order_var.get(),
                record_history=True,
                status=f"Applied {len(specs)} scene source(s). Click Update.",
            )
            window.destroy()

        ttk.Button(button_row, text="Add", command=add_source).pack(side="left")
        ttk.Button(button_row, text="Add From Source Panel", command=add_from_panel).pack(side="left", padx=(6, 0))
        ttk.Button(button_row, text="Duplicate", command=duplicate_source).pack(side="left", padx=(6, 0))
        ttk.Button(button_row, text="Delete", command=delete_source).pack(side="left", padx=(6, 0))

        footer = ttk.Frame(root)
        footer.grid(row=2, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(footer, text="Use Source Panel Only", command=clear_to_panel).pack(side="left", padx=(0, 10))
        ttk.Button(footer, text="Save Source", command=save_current_source).pack(side="left", padx=(0, 10))
        ttk.Button(footer, text="Apply", command=apply_sources).pack(side="left")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="left", padx=(8, 0))

        tree.bind("<<TreeviewSelect>>", lambda _event: load_form(selected_index() or 0))
        refresh_tree(current_index)
        self._show_centered_dialog(window)
