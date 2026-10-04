"""Quick Estimation's windows as row forms (bugs/0953; docs/design_qt_migration.md phase 5).

Three of the inspector's hand-built Tk popups -- Target FOV, the object / image plane FOV solve, and
the detector's design box -- are forms: a few numbers, a rule, and one or two verbs. Under a shell
they are shown from here, through `present_row_form`; the Tk app keeps its own windows (each is
placed by hand so it lands on screen under Wayland). What they DO is shared: every verb ends in the
inspector's own solve (`_apply_quick_estimation_fov_solve`, `set_target_fov_rect`), with the same
arguments the Tk buttons pass.

The words on screen are the Tk popups' words. The guard compares the two on a real folded scene, so
a label changed in one and not the other fails it.
"""
from __future__ import annotations

import math

from KrakenOS.UI.row_forms.base import FormAction, FormField, FormPanel, FormPreview, FormRefused, RowForm

ASPECT_NOTE = "Fill just one box — the other is derived from the sensor aspect."
NEED_ONE = "Enter a Width or a Height — the other is derived from the sensor aspect."


def read_dimension(raw, label: str) -> "float | None":
    """One box: blank is None (the other box derives it); anything else must be a positive number."""
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        value = float(text)
    except (TypeError, ValueError):
        raise FormRefused(f"{label} must be a number (or blank).") from None
    if not value > 0:
        raise FormRefused(f"{label} must be positive (or blank).")
    return value


def _size_text(value) -> str:
    return f"{value:.6g}" if value else ""


def _truthy(text) -> bool:
    return str(text or "").strip().lower() in ("1", "true", "yes", "on")


# ---- Target FOV ----------------------------------------------------------------------------------
def build_target_fov_form(inspector) -> RowForm:
    """Width x Height of the object field to image; the rectangle's diagonal is the snap target."""
    qe = inspector._quick_estimation_service()
    width0, height0 = qe.object_fov_dimensions() or (0.0, 0.0)

    def set_target(form, _host) -> str:
        values = form.values
        width = read_dimension(values.get("width"), "Width")
        height = read_dimension(values.get("height"), "Height")
        if width is None and height is None:
            raise FormRefused(NEED_ONE)
        aspect = (width0, height0) if (width0 and height0) else None
        ok, message, field_width, field_height = qe.set_target_fov_rect(width, height, aspect)
        if not ok:
            raise FormRefused(message)
        qe.update_readout()
        fill = qe.current_state().get("fill_factor")
        status = (f"Target FOV {field_width:.6g} x {field_height:.6g} mm -> {100 * fill:.1f}% of sensor. "
                  "Click Snap to FOV to fill it (or drag a distance)." if fill is not None
                  else f"Target FOV set to {field_width:.6g} x {field_height:.6g} mm.")
        inspector.status_var.set(status)
        form.state["close_after"] = True
        return status

    def clear_target(form, _host) -> str:
        qe.set_target_fov(None)
        qe.update_readout()
        status = "Target FOV cleared (FOV = fill the sensor)."
        inspector.status_var.set(status)
        form.state["close_after"] = True
        return status

    return RowForm(
        title="Target FOV — Object Field",
        row_index=-1,
        fields=(FormField("width", "Width (mm)", width=12), FormField("height", "Height (mm)", width=12)),
        values={"width": _size_text(width0), "height": _size_text(height0)},
        note="Object field to image (width x height, mm); the rectangle diagonal becomes the snap target:",
        summary="Fill just one box — the other is derived from the sensor aspect. Then click Snap to FOV "
                "to move the conjugates.",
        actions=(FormAction("set_target", "Set Target", run=set_target),
                 FormAction("clear_target", "Clear (fill sensor)", run=clear_target)),
        read_only=True,
    )


# ---- the FOV solve -------------------------------------------------------------------------------
def fov_prefill(inspector, plane: str) -> "tuple[tuple[float, float], str]":
    """((width, height) to offer, where it came from). With an inspection device enabled the
    inspected FACE sets the object field, not the sensor (bugs/0829)."""
    qe = inspector._quick_estimation_service()
    if plane != "object":
        return (qe.sensor_active_dimensions() or (0.0, 0.0)), ""
    size = qe.object_fov_dimensions()
    note = ""
    try:
        from KrakenOS.UI.services.inspection_field_chain import FACE_FOV_MARGIN, explain_prefill
        from KrakenOS.UI.services.inspection_part import face_dims, normalize_inspection_part_spec

        spec = normalize_inspection_part_spec(inspector.editor.__dict__.get("inspection_part_spec"))
        if spec.get("enabled"):
            face_width, face_height = face_dims(spec, spec.get("active_face", "front"))
            if face_width > 0 and face_height > 0:
                size = (face_width * FACE_FOV_MARGIN, face_height * FACE_FOV_MARGIN)
                note = (f"from the inspected face {face_width:g} x {face_height:g} mm "
                        f"+ {(FACE_FOV_MARGIN - 1) * 100:g}% margin")
        if not note and size:
            note = explain_prefill(qe.sensor_active_dimensions() or (0.0, 0.0),
                                   inspector.editor._current_finite_paraxial_magnification())
    except Exception:
        note = ""
    return (size or (0.0, 0.0)), note


def part_picture(inspector, *, width: int = 190, height: int = 120) -> "tuple | None":
    """The inspected part at true proportions, green where it is imaged (bugs/0830); None when no
    device is enabled."""
    try:
        from KrakenOS.UI.services.inspection_field_chain import (face_polygons, inspected_faces,
                                                                 unreachable_faces)
        from KrakenOS.UI.services.inspection_part import normalize_inspection_part_spec

        editor = inspector.editor
        spec = normalize_inspection_part_spec(editor.__dict__.get("inspection_part_spec"))
        if not spec.get("enabled"):
            return None
        folded = len(editor.__dict__.get("rows", []) or []) > 12
        lit = inspected_faces(spec, folded=folded)
        dead = unreachable_faces(spec, folded=folded)
        polygons = face_polygons(spec, width_px=width, height_px=height - 24)
    except Exception:
        return None
    shapes = []
    for name in ("back", "bottom", "left", "right", "top", "front"):
        if name in lit:
            fill, outline = "#2f7f3f", "#1d5f2a"
        elif name in dead:
            fill, outline = "#d8d8d8", "#bbbbbb"
        else:
            fill, outline = "#e9eef2", "#9fb0bd"
        shapes.append({"kind": "polygon", "points": list(polygons[name]), "fill": fill, "outline": outline})
    shapes.append({"kind": "text", "x": width // 2, "y": height - 20, "text": "green = inspected",
                   "fill": "#2f7f3f", "size": 7})
    shapes.append({"kind": "text", "x": width // 2, "y": height - 9, "text": "grey = not imageable",
                   "fill": "#888888", "size": 7})
    return tuple(shapes)


def leg_labels(split: dict, kind: str) -> dict:
    """What one conjugate's two legs are called, by where they sit in the folded beam (bugs/0299);
    a frozen scene may name its own (bugs/0447)."""
    if kind == "object":
        labels = {
            "near_label": "Constrain object → mirror distance — first leg (mm):",
            "far_label": "Constrain mirror → lens front distance (mm):",
            "near_name": "object → mirror", "far_name": "mirror → lens front", "total_name": "object distance",
        }
    else:
        labels = {
            "near_label": "Constrain lens rear → mirror distance (mm):",
            "far_label": "Constrain mirror → sensor distance — last leg (mm):",
            "near_name": "lens rear → mirror", "far_name": "mirror → sensor", "total_name": "image distance",
        }
    for key in ("near_label", "far_label", "near_name", "far_name"):
        if split.get(key):
            labels[key] = str(split[key])
    return labels


def fov_split_groups(inspector, plane: str) -> list:
    """The fold-leg pin groups a plane's form offers: the object form pins the object conjugate and,
    on a two-fold, the image conjugate too (bugs/0247); the image form only the image one."""
    editor = inspector.editor
    try:
        object_split = editor._folded_object_conjugate_split()
    except Exception:
        object_split = None
    try:
        image_split = editor._folded_image_conjugate_split()
    except Exception:
        image_split = None
    groups = []
    if plane == "object":
        both = bool(object_split) and bool(image_split)
        if object_split:
            groups.append(("object", object_split, "Object-side fold" if both else ""))
        if image_split:
            groups.append(("image", image_split, "Image-side fold" if both else ""))
    elif image_split:
        groups.append(("image", image_split, ""))
    return groups


def _group_fields(kind: str, split: dict, header: str) -> "tuple[list, dict, set, dict]":
    """(fields, values, keys locked at the start, names) for one conjugate's two legs."""
    labels = leg_labels(split, kind)
    near_min = float(split.get("near_min", 0.0) or 0.0)
    far_min = float(split.get("far_min", 0.0) or 0.0)

    def floor(value: float) -> str:
        return f"≥ {value:.4g} mm" if value > 0 else ""       # a leg with no floor says nothing

    def sync(form, _text) -> str:
        near_on = _truthy(form.values.get(f"pin_{kind}_near"))
        far_on = _truthy(form.values.get(f"pin_{kind}_far"))
        # near + far are mutually determined (far = total - near): only one may be pinned
        form.lock(f"pin_{kind}_near", locked=far_on)
        form.lock(f"pin_{kind}_far", locked=near_on)
        form.lock(f"{kind}_near", locked=not near_on)
        form.lock(f"{kind}_far", locked=not far_on)
        return ""

    fields = []
    values = {}
    if header:
        fields.append(FormField(f"{kind}_header", "", kind="static"))
        values[f"{kind}_header"] = header
    fields += [
        FormField(f"pin_{kind}_near", labels["near_label"], kind="bool", on_change=sync),
        FormField(f"{kind}_near", f"    {labels['near_name']} (mm)", width=12, hint=floor(near_min)),
        FormField(f"pin_{kind}_far", labels["far_label"], kind="bool", on_change=sync),
        FormField(f"{kind}_far", f"    {labels['far_name']} (mm)", width=12, hint=floor(far_min)),
        FormField(f"{kind}_explain", "", kind="static"),
    ]
    values.update({
        f"pin_{kind}_near": "false", f"{kind}_near": f"{float(split['near']):.6g}",
        f"pin_{kind}_far": "false", f"{kind}_far": f"{float(split['far']):.6g}",
        f"{kind}_explain": (
            f"Slides the {kind} fold mirror along the optical axis (total {labels['total_name']} "
            f"{float(split['total']):.4g} mm stays fixed; each leg ≥ {max(near_min, far_min):.4g} mm). Tick one "
            f"leg — its sibling is then determined and grayed out."
            + "".join(f" {name}: {floor(value)}." for name, value in
                      ((labels["near_name"], near_min), (labels["far_name"], far_min)) if value > 0)),
    })
    return fields, values, {f"{kind}_near", f"{kind}_far"}, labels


def pinned_leg(values: dict, kind: str, labels: dict) -> "tuple[str, float] | None":
    """("near" | "far", distance) for the leg ticked in one group, or None."""
    for leg in ("near", "far"):
        if not _truthy(values.get(f"pin_{kind}_{leg}")):
            continue
        name = labels[f"{leg}_name"]
        raw = str(values.get(f"{kind}_{leg}") or "").strip()
        if not raw:
            raise FormRefused(f"Enter the {name} distance, or untick the box.")
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise FormRefused(f"{name} distance must be a number.") from None
        if not value > 0:
            raise FormRefused(f"{name} distance must be positive.")
        return (leg, value)
    return None


def fov_design_context(inspector, values: dict) -> dict:
    """What the object field typed above pins for the design block: the semi-DIAGONAL of the
    rectangle on show -- both boxes when both are filled (bugs/0830), else the width through the
    sensor aspect."""
    from KrakenOS.UI.services.quick_estimation import DESIGN_OBJECT_FOV_SEMI

    try:
        width = float(str(values.get("width") or "").strip() or 0.0)
    except ValueError:
        return {}
    if width <= 0:
        return {}
    try:
        height = float(str(values.get("height") or "").strip() or 0.0)
    except ValueError:
        height = 0.0
    try:
        semi = (math.hypot(width, height) / 2.0 if height > 0 else
                float(inspector._quick_estimation_service().horizontal_to_diagonal(width)) / 2.0)
    except Exception:
        return {}
    return {DESIGN_OBJECT_FOV_SEMI: semi} if semi > 0 else {}


def build_fov_solve_form(inspector, plane: str) -> RowForm:
    """Type a plane's field width x height, then solve for the thicknesses or for the sensor size;
    on a folded scene, optionally pin one leg of a fold in the same solve."""
    plane = "object" if str(plane) == "object" else "image"
    title = "Object Plane — Field of View (FOV)" if plane == "object" else "Image Plane — Sensor Size"
    prompt = ("Object field to image (width x height, mm):" if plane == "object"
              else "Image / sensor size (width x height, mm):")
    (width0, height0), prefill_note = fov_prefill(inspector, plane)
    fields = [FormField("width", "Width (mm)", width=12), FormField("height", "Height (mm)", width=12),
              FormField("prefill", "", kind="static")]
    values = {"width": _size_text(width0), "height": _size_text(height0),
              "prefill": f"Pre-filled {prefill_note}." if prefill_note else ASPECT_NOTE}
    locked: set = set()
    groups = []
    for kind, split, header in fov_split_groups(inspector, plane):
        group_fields, group_values, group_locked, labels = _group_fields(kind, split, header)
        fields += group_fields
        values.update(group_values)
        locked |= group_locked
        groups.append((kind, labels))

    def solve(mode: str):
        def run(form, _host) -> str:
            typed = form.values
            width = read_dimension(typed.get("width"), "Width")
            height = read_dimension(typed.get("height"), "Height")
            if width is None and height is None:
                raise FormRefused(NEED_ONE)
            legs = {kind: pinned_leg(typed, kind, labels) for kind, labels in groups}
            if plane == "object":
                segment, image_segment = legs.get("object"), legs.get("image")
            else:
                segment, image_segment = legs.get("image"), None
            aspect = (width0, height0) if (width0 and height0) else None
            form.state["close_after"] = True
            inspector._apply_quick_estimation_fov_solve(plane, mode, width, height, aspect,
                                                        segment=segment, image_segment=image_segment)
            return str(inspector.status_var.get())
        return run

    picture = part_picture(inspector) if plane == "object" else None
    form = RowForm(
        title=title,
        row_index=-1,
        fields=tuple(fields),
        values=values,
        note=prompt,
        actions=(FormAction("solve_thickness", "Solve for Thickness", run=solve("thickness")),
                 FormAction("solve_sensor", "Solve for Image/Sensor Size", run=solve("sensor"))),
        read_only=True,
        locked=locked,
        preview=(FormPreview(width=190, height=120, shapes=lambda _form, _values: picture)
                 if picture else None),
        # the object plane already fixes the object field, so the FOV is pinned from the boxes
        # above; the user adds one length and the EFL solves. The image form is the sensor-sizing
        # tool and has no such block.
        panels=((FormPanel("design_constraints", owner=inspector, title="Design a lens for this field",
                           mode="design",
                           context=lambda _form, typed: fov_design_context(inspector, typed)),)
                if plane == "object" else ()),
    )
    form.state["groups"] = groups
    return form


# ---- the detector's design box -----------------------------------------------------------------
def detector_design_context(inspector) -> dict:
    """A detector sits at the image side, so the image distance is pinned from the current image
    gap; the user adds one more known and the EFL solves."""
    from KrakenOS.UI.services.quick_estimation import DESIGN_IMAGE_DISTANCE

    try:
        image_row = inspector._quick_estimation_service().image_thickness_row()
        if image_row is None:
            return {}
        thickness = float(inspector.editor.rows[image_row].thickness)
    except Exception:
        return {}
    return {DESIGN_IMAGE_DISTANCE: thickness} if thickness > 0 else {}


def build_detector_design_form(inspector) -> RowForm:
    """"What lens do I need?" for one arm. Advisory: it never moves the layout by itself."""
    return RowForm(
        title="Detector — Design Lens (Quick Estimation)",
        row_index=-1,
        note="Pin first-order knowns; solve for the lens (EFL).\nAdvisory -- does not move the layout.",
        read_only=True,
        panels=(FormPanel("design_constraints", owner=inspector, mode="placement",
                          context=lambda _form, _typed: detector_design_context(inspector)),),
    )
