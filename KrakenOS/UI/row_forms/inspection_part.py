"""The Inspection Part row form (docs/design_qt_migration.md phase 3).

The 3D part at the object plane: whether to show it, its Length x Width x Thickness, the required
FOV, and an optional STEP whose bounds size the box. Apply writes it; "Apply + Solve FOV" then
solves the field to the inspected face.

What kept this dialog off the framework until now is its PICTURE. bugs/0828 replaced an
explanatory paragraph with a drawing of the part at true proportions -- the two inspected faces
lit, the unreachable ones greyed -- plus a derivation chain where every line names its parent,
because "a dense sentence does not attach to the fields above it". That picture is model data
(`face_polygons`, `inspected_faces`, `unreachable_faces`, `field_chain`), so it is a
`FormPreview`: the model says what to draw and both toolkits draw it, redrawing on every
keystroke so the consequence of a number is visible BEFORE Apply.
"""
from __future__ import annotations

from pathlib import Path

from KrakenOS.UI.row_forms.base import FormAction, FormField, FormPreview, FormRefused, RowForm

TITLE = "Inspection Part (3D object)"
# bugs/0764 then bugs/0766: the stored keys are unchanged, only what the user reads.
#     Length    L = width_mm  (local x) -- along the top prism's LONGEST dimension
#     Width     W = depth_mm  (local z) -- along the top prism GAP (face to face)
#     Thickness T = height_mm (local y) -- the top prism's SHORT dimension
NOTE = ("The part sits at the object plane. Length runs along the prism's longest dimension, "
        "Width across the prism gap, Thickness is the short one. Green faces are inspected; "
        "grey ones cannot be reached.")
DIMENSIONS = (("width_mm", "Length L (mm)"), ("depth_mm", "Width W (mm)"),
              ("height_mm", "Thickness T (mm)"))
STEP_FILETYPES = [("STEP", "*.step *.stp *.STEP *.STP"), ("All files", "*")]
LIT = ("#2f7f3f", "#1d5f2a")
DEAD = ("#d8d8d8", "#bbbbbb")
PLAIN = ("#e9eef2", "#9fb0bd")
FACE_DRAW_ORDER = ("back", "bottom", "left", "right", "top", "front")


def model(owner):
    """The inspection-part model, wherever the caller keeps it."""
    from types import SimpleNamespace

    from KrakenOS.UI.services import inspection_part as part_module
    from KrakenOS.UI.services.inspection_field_chain import (chain_text, face_polygons,
                                                             field_chain, inspected_faces,
                                                             unreachable_faces)

    return SimpleNamespace(
        normalize=part_module.normalize_inspection_part_spec,
        face_dims=part_module.face_dims,
        step_bounds=part_module.apply_step_bounds,
        polygons=face_polygons,
        lit=inspected_faces,
        dead=unreachable_faces,
        chain=field_chain,
        chain_text=chain_text,
    )


def build_inspection_part_form(owner, *_args, **_kwargs) -> RowForm:
    """The form for the part at the object plane."""
    parts = model(owner)
    spec = parts.normalize(getattr(owner, "inspection_part_spec", None))

    form = RowForm(
        title=TITLE,
        row_index=0,
        fields=(
            FormField("enabled", "Show the 3D part at the object plane", kind="bool"),
            *(FormField(key, label, kind="number", width=12) for key, label in DIMENSIONS),
            FormField("required_fov_mm", "Required FOV (mm, blank = face +5%)", kind="text",
                      width=12),
            FormField("step_path", "Part STEP (optional)", kind="text", width=34),
        ),
        note=NOTE,
        state={"owner": owner, "parts": parts, "spec": spec},
        preview=FormPreview(width=210, height=150, shapes=_shapes, caption=_caption),
    )
    form.values = {
        "enabled": "true" if spec["enabled"] else "false",
        **{key: f"{float(spec[key]):g}" for key, _label in DIMENSIONS},
        "required_fov_mm": "",
        "step_path": str(spec.get("step_path", "") or ""),
    }
    form.summary = "Type a dimension and the picture follows; Apply writes it to the scene."

    def validate(values: dict) -> list[str]:
        try:
            _spec_from_values(form, values)
        except FormRefused as exc:
            return [str(exc)]
        return []

    def describe(values: dict) -> str:
        candidate = _spec_from_values(form, values)
        width, height = parts.face_dims(candidate, candidate["active_face"])
        return (f"L {float(candidate['width_mm']):g} x W {float(candidate['depth_mm']):g} x "
                f"T {float(candidate['height_mm']):g} mm; inspected face "
                f"{candidate['active_face']} is {width:g} x {height:g} mm")

    def apply(values: dict) -> str:
        candidate = _spec_from_values(form, values)
        owner.set_inspection_part_spec(candidate)
        form.state["spec"] = parts.normalize(owner.inspection_part_spec)
        width, height = parts.face_dims(owner.inspection_part_spec,
                                        owner.inspection_part_spec["active_face"])
        return (f"Applied. Inspected face {owner.inspection_part_spec['active_face']}: "
                f"{width:g} x {height:g} mm.")

    form.validate = validate
    form.describe = describe
    form.apply = apply
    form.actions = (
        FormAction("browse_step", "Browse Part STEP...", _browse_step),
        FormAction("solve", "Apply + Solve FOV to this face", _apply_and_solve),
    )
    return form


# ---- the picture ------------------------------------------------------------------------------
def _live_spec(form, values: dict):
    """The spec as TYPED, for the picture -- never the one last applied."""
    parts = form.state["parts"]
    candidate = dict(form.state["spec"])
    for key, _label in DIMENSIONS:
        candidate[key] = float(str(values.get(key, "")).strip() or 0.0)
    return parts.normalize(candidate)


def _folded(form) -> bool:
    owner = form.state["owner"]
    return bool(getattr(owner, "_folded_display_enabled", None)
                or len(getattr(owner, "rows", []) or []) > 12)


def _shapes(form, values: dict) -> tuple:
    parts = form.state["parts"]
    live = _live_spec(form, values)
    folded = _folded(form)
    lit = set(parts.lit(live, folded=folded))
    dead = set(parts.dead(live, folded=folded))
    polygons = parts.polygons(live, width_px=210, height_px=150)
    shapes = []
    for name in FACE_DRAW_ORDER:
        fill, outline = LIT if name in lit else (DEAD if name in dead else PLAIN)
        shapes.append({"kind": "polygon", "points": list(polygons[name]),
                       "fill": fill, "outline": outline})
    shapes.append({"kind": "text", "x": 105, "y": 140,
                   "text": "green = inspected   grey = unreachable",
                   "fill": "#666666", "size": 7})
    return tuple(shapes)


def _caption(form, values: dict) -> str:
    parts = form.state["parts"]
    live = _live_spec(form, values)
    try:
        fov_text = str(values.get("required_fov_mm", "")).strip()
        required = float(fov_text) if fov_text else None
    except Exception:
        required = None
    return parts.chain_text(parts.chain(live, face_dims_fn=parts.face_dims,
                                        required_fov=required))


# ---- reading and the verbs ---------------------------------------------------------------------
def _spec_from_values(form, values: dict) -> dict:
    """bugs/0768: the two DERIVED keys come from the live spec, never from a widget --
    re-submitting a stale offset is what fought the auto-centring."""
    parts = form.state["parts"]
    owner = form.state["owner"]
    live = parts.normalize(getattr(owner, "inspection_part_spec", None))
    numbers = {}
    for key, label in DIMENSIONS:
        try:
            numbers[key] = float(str(values.get(key, "")).strip() or 0.0)
        except Exception as exc:
            raise FormRefused(f"{label} expects a number.") from exc
        if numbers[key] < 0.0:
            raise FormRefused(f"{label} must be non-negative.")
    fov_text = str(values.get("required_fov_mm", "")).strip()
    if fov_text:
        try:
            if float(fov_text) <= 0.0:
                raise FormRefused("Required FOV must be a positive number, or blank.")
        except FormRefused:
            raise
        except Exception as exc:
            raise FormRefused("Required FOV must be a number, or blank.") from exc
    return parts.normalize({
        "enabled": str(values.get("enabled", "")).strip().lower() in ("1", "true", "yes", "on"),
        **numbers,
        "axis_reach_mm": live["axis_reach_mm"],
        "axis_offset_mm": live["axis_offset_mm"],
        "active_face": live["active_face"],
        "step_path": str(values.get("step_path", "")).strip(),
    })


def _browse_step(form, host) -> str:
    owner = form.state["owner"]
    parts = form.state["parts"]
    path = host.askopenfilename(title="Part STEP", filetypes=STEP_FILETYPES)
    if not path:
        return "Browse cancelled."
    form.values["step_path"] = str(path)
    try:
        mesh = owner._load_step_mesh(Path(path), largest_component=False)
        sized = parts.step_bounds({key: form.values[key] for key, _label in DIMENSIONS}, mesh)
    except Exception as exc:
        return f"Part STEP set, but its bounds could not be read: {exc}"
    for key, _label in DIMENSIONS:
        form.values[key] = f"{float(sized[key]):g}"
    form.values["enabled"] = "true"
    return (f"Dims from the STEP bounds: L {float(sized['width_mm']):g} x "
            f"W {float(sized['depth_mm']):g} x T {float(sized['height_mm']):g} mm "
            "(STEP x=Length, z=Width, y=Thickness; +z = Front face)")


def _apply_and_solve(form, _host) -> str:
    owner = form.state["owner"]
    candidate = _spec_from_values(form, dict(form.values))
    owner.set_inspection_part_spec(candidate)
    form.state["spec"] = form.state["parts"].normalize(owner.inspection_part_spec)
    fov_text = str(form.values.get("required_fov_mm", "")).strip()
    try:
        required = float(fov_text) if fov_text else None
    except Exception:
        required = None
    try:
        solved, message = owner.solve_fov_to_inspection_face(fov=required)
    except Exception as exc:
        raise FormRefused(f"FOV solve failed: {exc}") from exc
    if not solved:
        # the model's own refusal text, not a generic one
        raise FormRefused(str(message))
    return str(message)


build_inspection_part_form.TITLE = TITLE
