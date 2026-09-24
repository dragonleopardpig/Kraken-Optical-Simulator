"""bugs/0363: the scene-source edit dialog -- the "general 3D source element" UX.

Right-click a source row in the Scene Components browser -> "Edit Source..." opens
this compact dialog: name, origin (mm), emit direction, emitting width/height (mm),
cone half-angle, ray count and power. Apply writes through
``update_scene_source_spec`` (the same path the seat-on-face glue uses), which
re-applies the specs via the standard row-action pipeline (rebuild + history +
status), so the glyph, illumination volume and trace all follow immediately.
"""

from __future__ import annotations

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
    # docs/design_qt_migration.md phase 3 (bugs/0885): the fields, the coaxial extras, the
    # validation and what Apply writes live in KrakenOS/UI/row_forms/source_edit.py, which the
    # Qt dialog uses too.
    from KrakenOS.UI.panels.row_form_view import render_row_form
    from KrakenOS.UI.row_forms import FormRefused
    from KrakenOS.UI.row_forms.source_edit import build_scene_source_edit_form

    try:
        form = build_scene_source_edit_form(editor, str(source_id))
    except FormRefused as exc:
        inspector.status_var.set(str(exc))
        return
    render_row_form(editor, form, wraplength=460, modal=True)
