"""bugs/0363: the scene-source edit dialog -- the "general 3D source element" UX.

Right-click a source row in the Scene Components browser -> "Edit Source..." opens
this compact dialog: name, origin (mm), emit direction, emitting width/height (mm),
cone half-angle, ray count and power. Apply writes through
``update_scene_source_spec`` (the same path the seat-on-face glue uses), which
re-applies the specs via the standard row-action pipeline (rebuild + history +
status), so the glyph, illumination volume and trace all follow immediately.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import numpy as np


def _spec_for_source(editor, source_id: str) -> dict | None:
    try:
        specs = editor._normalize_scene_source_specs(
            getattr(editor, "layout_scene_source_specs", []) or []
        )
    except Exception:
        return None
    for spec in specs:
        if str(spec.get("source_id", "") or "") == str(source_id):
            return dict(spec)
    return None


def _vec3(spec: dict, vector_key: str, component_keys: tuple[str, str, str], default):
    value = spec.get(vector_key)
    try:
        arr = np.asarray(value, dtype=float).reshape(3)
        if np.all(np.isfinite(arr)):
            return [float(arr[0]), float(arr[1]), float(arr[2])]
    except Exception:
        pass
    out = []
    for key, fallback in zip(component_keys, default):
        try:
            out.append(float(spec.get(key, fallback)))
        except Exception:
            out.append(float(fallback))
    return out


def open_scene_source_edit_dialog(editor, inspector, source_id: str) -> None:
    spec = _spec_for_source(editor, source_id)
    if spec is None:
        inspector.status_var.set(f"Edit Source: {source_id} not found.")
        return
    origin = _vec3(spec, "origin", ("source_x", "source_y", "source_z"), (0.0, 0.0, 0.0))
    direction = _vec3(spec, "direction", ("source_l", "source_m", "source_n"), (0.0, 0.0, 1.0))

    def _flt(key, fallback):
        try:
            return float(spec.get(key, fallback))
        except Exception:
            return float(fallback)

    width = 2.0 * _flt("radius_x", _flt("radius", 5.0))
    height = 2.0 * _flt("radius_y", _flt("radius", 5.0))

    # bugs/0401: a coaxial-LED illuminator gets an extra illumination-edge PROFILE control
    # (flat-top soft edge vs uniform sharp edge, with a calibratable edge width) that drives
    # the object-plane footprint's soft edge. Only shown for a coaxial source; harmless else.
    from KrakenOS.UI.scene_source_analysis import (
        COAXIAL_EDGE_PROFILES,
        COAXIAL_ILLUMINATOR_KEY,
        coaxial_edge_penumbra_mm,
        coaxial_edge_profile_and_width,
    )
    is_coaxial = bool(spec.get(COAXIAL_ILLUMINATOR_KEY, False))
    seed_profile, seed_edge = coaxial_edge_profile_and_width(spec)

    dialog = tk.Toplevel(inspector)
    dialog.title(f"Edit Source — {spec.get('name', source_id)}")
    dialog.transient(inspector)
    frame = ttk.Frame(dialog, padding=10)
    frame.grid(row=0, column=0, sticky="nsew")

    entries: dict[str, tk.StringVar] = {}
    rows = (
        ("Name", "name", str(spec.get("name", source_id))),
        ("Origin X (mm)", "ox", f"{origin[0]:.4g}"),
        ("Origin Y (mm)", "oy", f"{origin[1]:.4g}"),
        ("Origin Z (mm)", "oz", f"{origin[2]:.4g}"),
        ("Direction L", "dl", f"{direction[0]:.6g}"),
        ("Direction M", "dm", f"{direction[1]:.6g}"),
        ("Direction N", "dn", f"{direction[2]:.6g}"),
        ("Width (mm)", "width", f"{width:.4g}"),
        ("Height (mm)", "height", f"{height:.4g}"),
        ("Cone half-angle (deg)", "cone", f"{_flt('cone_deg', 30.0):.4g}"),
        ("Ray count", "rays", str(int(_flt("ray_count", 2000)))),
        ("Power", "power", f"{_flt('power', 1.0):.4g}"),
    )
    for i, (label, key, value) in enumerate(rows):
        ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", pady=1)
        var = tk.StringVar(value=value)
        entries[key] = var
        ttk.Entry(frame, textvariable=var, width=18).grid(row=i, column=1, sticky="ew", pady=1, padx=(8, 0))

    next_row = len(rows)
    profile_var: tk.StringVar | None = None
    edge_var: tk.StringVar | None = None
    if is_coaxial:
        ttk.Label(frame, text="Illumination edge").grid(row=next_row, column=0, sticky="w", pady=(7, 1))
        profile_var = tk.StringVar(value=seed_profile)
        ttk.Combobox(
            frame, textvariable=profile_var, values=list(COAXIAL_EDGE_PROFILES),
            state="readonly", width=16,
        ).grid(row=next_row, column=1, sticky="ew", pady=(7, 1), padx=(8, 0))
        next_row += 1
        ttk.Label(frame, text="Edge width (mm)").grid(row=next_row, column=0, sticky="w", pady=1)
        edge_var = tk.StringVar(value=seed_edge)
        ttk.Entry(frame, textvariable=edge_var, width=18).grid(row=next_row, column=1, sticky="ew", pady=1, padx=(8, 0))
        next_row += 1

    status = tk.StringVar(value="")
    ttk.Label(frame, textvariable=status, foreground="#b45309").grid(
        row=next_row, column=0, columnspan=2, sticky="w", pady=(6, 0)
    )

    def _apply() -> None:
        try:
            ox, oy, oz = (float(entries[k].get()) for k in ("ox", "oy", "oz"))
            dl, dm, dn = (float(entries[k].get()) for k in ("dl", "dm", "dn"))
            w = float(entries["width"].get())
            h = float(entries["height"].get())
            cone = float(entries["cone"].get())
            rays = max(1, int(float(entries["rays"].get())))
            power = float(entries["power"].get())
        except Exception:
            status.set("Enter numeric values (direction may be any non-zero vector).")
            return
        norm = float(np.linalg.norm((dl, dm, dn)))
        if norm <= 1e-9:
            status.set("Direction must be a non-zero vector.")
            return
        if w <= 0.0 or h <= 0.0:
            status.set("Width and height must be positive.")
            return
        dl, dm, dn = dl / norm, dm / norm, dn / norm
        update = {
            "name": entries["name"].get().strip() or str(source_id),
            "origin": [ox, oy, oz],
            "direction": [dl, dm, dn],
            "source_x": ox, "source_y": oy, "source_z": oz,
            "source_l": dl, "source_m": dm, "source_n": dn,
            "radius_x": 0.5 * w, "radius_y": 0.5 * h,
            "cone_deg": cone, "ray_count": rays, "power": power,
        }
        edge_note = ""
        if is_coaxial and profile_var is not None and edge_var is not None:
            update["coaxial_edge_profile"] = profile_var.get()
            update["coaxial_penumbra_mm"] = coaxial_edge_penumbra_mm(profile_var.get(), edge_var.get())
            edge_note = f"; edge {profile_var.get()}"
        ok = editor.update_scene_source_spec(
            str(source_id),
            update,
            status=f"Updated scene source {source_id} ({w:.4g} x {h:.4g} mm{edge_note}).",
        )
        if ok:
            dialog.destroy()
        else:
            status.set("Source not found any more -- was it deleted?")

    buttons = ttk.Frame(frame)
    buttons.grid(row=next_row + 1, column=0, columnspan=2, sticky="e", pady=(10, 0))
    ttk.Button(buttons, text="Apply", command=_apply).grid(row=0, column=0, padx=(0, 6))
    ttk.Button(buttons, text="Cancel", command=dialog.destroy).grid(row=0, column=1)
    # bugs/0403: center on the usable screen so the dialog doesn't spawn at the monitor's top-left
    # corner tucked under the top panel bar (the AGS bar). _show_centered_dialog caps to the usable
    # screen and keeps the title clear of a top bar.
    try:
        editor._show_centered_dialog(dialog)
    except Exception:
        pass
    try:
        dialog.grab_set()
    except Exception:
        pass
