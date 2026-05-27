"""Advanced surface attribute names and row-spec extraction helpers."""

from __future__ import annotations

from KrakenOS.UI.lens_drawing_properties import DRAWING_PROPERTIES_ATTR
from KrakenOS.UI.scene_placement import SCENE_PLACEMENT_ADVANCED_ATTR
from KrakenOS.UI.services.surface_value_parsing import _compact_surface_attr_name
from KrakenOS.UI.tolerance_constants import (
    TOLERANCE_COMPENSATORS_ADVANCED_ATTR,
    TOLERANCE_COUPLING_ADVANCED_ATTR,
    TOLERANCE_MANUFACTURING_ADVANCED_ATTR,
)
from KrakenOS.UI.trace_intent import DIFFUSE_OBJECT_SURFACE, OBJECT_TARGET_SURFACE


DETECTOR_ADVANCED_ATTR = "Detector"
SCENE_TARGET_ADVANCED_ATTR = "SceneTarget"
DRAWING_PROPERTIES_ADVANCED_ATTR = DRAWING_PROPERTIES_ATTR
REFLECTIVE_PROXY_SURFACES = {"Mirror", OBJECT_TARGET_SURFACE, DIFFUSE_OBJECT_SURFACE}

ADVANCED_SURFACE_FIELD_GROUPS = (
    (
        "Shape",
        (
            ("AspherData", "Asphere coefficients"),
            ("ZNK", "Zernike coefficients"),
            ("Cylinder_Rxy_Ratio", "Cylinder Rxy ratio"),
            ("ShiftX", "Shape shift X"),
            ("ShiftY", "Shape shift Y"),
            ("Surface_type", "Surface type"),
            ("Res", "Resolution"),
        ),
    ),
    (
        "Aperture/Mask",
        (
            ("SubAperture", "Sub-aperture [scale, y, x]"),
            ("Mask_Type", "Mask type"),
            ("Mask_Shape", "Mask shape"),
            ("Solid_3d_stl", "STL solid path/data"),
        ),
    ),
    (
        "Coating/Material",
        (
            ("Coating", "Coating table"),
            ("CoatingMet", "Metal coating mode"),
            ("BeamSplitter", "Beam splitter settings"),
            ("DiffuseScatter", "Diffuse/BRDF scatter settings"),
            ("Color", "Display color"),
            ("Nm_Pos", "Name position"),
        ),
    ),
    (
        "Diagnostics/Native",
        (
            ("Element", "Element/path metadata"),
            (DETECTOR_ADVANCED_ATTR, "Detector model settings"),
            (SCENE_TARGET_ADVANCED_ATTR, "Scene target metadata"),
            (SCENE_PLACEMENT_ADVANCED_ATTR, "3-D placement metadata"),
            (DRAWING_PROPERTIES_ADVANCED_ATTR, "2-D drawing surface properties"),
            ("Display2D", "2-D display settings"),
            ("Interferogram", "Interferogram detector settings"),
            ("OpticalSolidFaces", "CAD/STL optical face roles"),
            ("OpticalSolidSourcePath", "Original CAD/STL source path"),
            ("OpticalSolidSourceFormat", "Original CAD/STL source format"),
            ("StepOverlayPromotion", "Open 3D STEP promotion metadata"),
            ("LiveStepOverlayTrace", "Open 3D live STEP trace metadata"),
            ("Note", "Note"),
            ("Order", "Native order"),
            ("Var", "Native optimization vars"),
            ("VarBounds", "Native variable bounds"),
            (TOLERANCE_COMPENSATORS_ADVANCED_ATTR, "Tolerance compensator variable names"),
            (TOLERANCE_COUPLING_ADVANCED_ATTR, "Tolerance coupling groups"),
            (TOLERANCE_MANUFACTURING_ADVANCED_ATTR, "Tolerance manufacturing metadata"),
            ("Error_map", "Measured error map"),
            ("DerPres", "Derivative precision"),
            ("NumLabel", "Draw numeric label"),
            ("SPECIAL_SURF_FUNC", "Special surface function"),
            ("Const", "Native constants"),
        ),
    ),
)
ADVANCED_SURFACE_ATTR_NAMES = tuple(attr for _group, fields in ADVANCED_SURFACE_FIELD_GROUPS for attr, _label in fields)

ADVANCED_SURFACE_ATTR_ALIASES = {
    _compact_surface_attr_name(attr): attr for attr in ADVANCED_SURFACE_ATTR_NAMES
}
ADVANCED_SURFACE_ATTR_ALIASES.update(
    {
        "aspherdata": "AspherData",
        "aspherics": "AspherData",
        "aspher": "AspherData",
        "zernike": "ZNK",
        "znk": "ZNK",
        "subaperture": "SubAperture",
        "masktype": "Mask_Type",
        "maskshape": "Mask_Shape",
        "coatingmet": "CoatingMet",
        "beamsplitter": "BeamSplitter",
        "beam splitter": "BeamSplitter",
        "diffusescatter": "DiffuseScatter",
        "diffuse scatter": "DiffuseScatter",
        "brdf": "DiffuseScatter",
        "bsdf": "DiffuseScatter",
        "elementmetadata": "Element",
        "element metadata": "Element",
        "pathmetadata": "Element",
        "path metadata": "Element",
        "armmetadata": "Element",
        "arm metadata": "Element",
        "error map": "Error_map",
        "errormap": "Error_map",
        "solid3dstl": "Solid_3d_stl",
        "cylinderrxyratio": "Cylinder_Rxy_Ratio",
        "surfacetype": "Surface_type",
        "specialsurffunc": "SPECIAL_SURF_FUNC",
    }
)

EXAMPLE_SUPPORTED_SURFACE_ATTRS = {
    "Name",
    "Rc",
    "InDiameter",
    "k",
    "Axicon",
    "ExtraData",
    "Diff_Ord",
    "Grating_D",
    "Grating_Angle",
    "Thickness",
    "Diameter",
    "TiltX",
    "TiltY",
    "TiltZ",
    "DespX",
    "DespY",
    "DespZ",
    "AxisMove",
    "Drawing",
    "Glass",
    "Thin_Lens",
    "UDA",
    *ADVANCED_SURFACE_ATTR_NAMES,
}


def _canonical_advanced_surface_attr(value: object) -> str | None:
    return ADVANCED_SURFACE_ATTR_ALIASES.get(_compact_surface_attr_name(value))


def _advanced_surface_attrs_from_spec(spec: dict) -> dict[str, object]:
    attrs: dict[str, object] = {}
    for source_key in ("advanced", "advanced_attrs", "surface_attrs"):
        source = spec.get(source_key)
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            attr = _canonical_advanced_surface_attr(key)
            if attr is not None:
                attrs[attr] = value
    for key, value in spec.items():
        if str(key).strip().lower() == "element":
            continue
        attr = _canonical_advanced_surface_attr(key)
        if attr is not None:
            attrs[attr] = value
    return attrs
