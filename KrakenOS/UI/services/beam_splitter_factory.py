"""Parametric beam-splitter solid generator (bugs/0319).

A one-click "Add Beam Splitter to LED" overlays a beam splitter onto an imported
LED STEP, centers it on the LED clear-aperture opening, glues it, and promotes it
to a non-sequential optical element. This module owns the *first* step: making the
BS solid parametrically, in-process, with pythonocc-core -- so a fresh clone can
regenerate it with nothing downloaded (the ``attachment/prisms/*`` vendor STEPs are
gitignored and absent on a clean checkout).

Two kinds, both canonical (centered at the origin, optical axis = +Z, the coating
plane folding the Z beam by 45 degrees):

* **cube** -- two cemented right-angle prisms sharing a *real* 45-degree diagonal
  hypotenuse face. A plain ``BRepPrimAPI_MakeBox`` has NO diagonal; the resize /
  coupling detector (``open3d_solid_resize.detect_coupling_from_faces``) expects that
  face, and the promote step auto-flags it as the BS coating. So the cube is built as
  a compound of two triangular-prism solids -- literally two cemented prisms -- whose
  shared hypotenuse is the coating plane X = Z (normal ~ (1, 0, -1)/sqrt2).
* **plate** -- a thin glass plate pre-tilted 45 degrees about the vertical (Y) axis,
  so its large-face normal folds the Z beam (normal ~ (sin45, 0, cos45)).

The written STEP is cached under ``attachment/cad_cache/beam_splitter_templates/``
(gitignored, Filen-synced) keyed on the kind + rounded parameters, and is
**regenerated from parameters whenever the cache is missing** (user: "Cache is OK as
long as user can re-generate in case the cache not found").

The geometry math (coating-face normal/point, bounding box) is pure Python and needs
no OCC, so ``beam_splitter_metadata`` is display- and OCC-free and unit-testable on
any machine; only the actual solid build + STEP write need pythonocc-core.
"""

from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass, field
from pathlib import Path

from KrakenOS.UI.services import cad_cache_paths


# Canonical optical axis for a generated template: +Z (KrakenOS convention).
_OPTICAL_AXIS = (0.0, 0.0, 1.0)
_TEMPLATE_SUBDIR = "beam_splitter_templates"


@dataclass
class BeamSplitterSolid:
    """The generated BS template and the analytic facts a caller needs to place,
    glue, and auto-flag it without re-reading the STEP.

    ``coating_normal`` / ``coating_point`` describe the 45-degree diagonal plane the
    orchestration flags as the BS coating; ``bbox_min`` / ``bbox_max`` bound the
    canonical (origin-centered) solid so the centering step can size its overlay.
    """

    path: Path
    kind: str
    params: dict
    coating_normal: tuple
    coating_point: tuple
    bbox_min: tuple
    bbox_max: tuple
    regenerated: bool = False
    notes: list = field(default_factory=list)

    @property
    def coating_tilt_deg(self) -> float:
        """Angle between the coating-face normal and the optical axis (deg)."""
        return _angle_to_axis_deg(self.coating_normal, _OPTICAL_AXIS)


# ---------------------------------------------------------------------------
# Pure-Python geometry facts (no OCC) -- unit-testable anywhere.
# ---------------------------------------------------------------------------

def _unit(vec) -> tuple:
    x, y, z = (float(v) for v in vec)
    norm = math.sqrt(x * x + y * y + z * z)
    if norm <= 1e-12:
        return (0.0, 0.0, 0.0)
    return (x / norm, y / norm, z / norm)


def _angle_to_axis_deg(normal, axis) -> float:
    n = _unit(normal)
    a = _unit(axis)
    dot = abs(n[0] * a[0] + n[1] * a[1] + n[2] * a[2])
    dot = max(0.0, min(1.0, dot))
    return math.degrees(math.acos(dot))


def _normalize_cube_params(side_mm: float) -> dict:
    side = float(side_mm)
    if not math.isfinite(side) or side <= 0.0:
        raise ValueError(f"beam-splitter cube side must be a positive length, got {side_mm!r}")
    return {"side_mm": round(side, 6)}


def _normalize_plate_params(width_mm: float, height_mm: float, thickness_mm: float, tilt_deg: float) -> dict:
    width = float(width_mm)
    height = float(height_mm)
    thickness = float(thickness_mm)
    tilt = float(tilt_deg)
    for name, value in (("width", width), ("height", height), ("thickness", thickness)):
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"beam-splitter plate {name} must be a positive length, got {value!r}")
    if not math.isfinite(tilt) or not (0.0 < tilt < 90.0):
        raise ValueError(f"beam-splitter plate tilt must be in (0, 90) deg, got {tilt_deg!r}")
    if thickness >= min(width, height):
        raise ValueError(
            f"beam-splitter plate thickness {thickness} must be thinner than its face "
            f"({width} x {height}) -- a plate is a thin box, not a cube")
    return {
        "width_mm": round(width, 6),
        "height_mm": round(height, 6),
        "thickness_mm": round(thickness, 6),
        "tilt_deg": round(tilt, 6),
    }


def _cube_geometry(params: dict) -> dict:
    """Analytic facts for the canonical cube: the coating is the X = Z diagonal
    plane through the origin; the solid spans [-s/2, s/2] on every axis."""
    side = float(params["side_mm"])
    half = side / 2.0
    return {
        "coating_normal": _unit((1.0, 0.0, -1.0)),
        "coating_point": (0.0, 0.0, 0.0),
        "bbox_min": (-half, -half, -half),
        "bbox_max": (half, half, half),
    }


def _plate_geometry(params: dict) -> dict:
    """Analytic facts for the canonical plate: a (w x h x t) box centered at the
    origin, then rotated ``tilt`` about +Y. The large-face normal starts at +Z and
    tilts into (sin t, 0, cos t); the bbox is the rotated box's axis-aligned extent."""
    width = float(params["width_mm"])
    height = float(params["height_mm"])
    thickness = float(params["thickness_mm"])
    tilt = math.radians(float(params["tilt_deg"]))
    cos_t = math.cos(tilt)
    sin_t = math.sin(tilt)

    # Rotate the large-face normal (+Z) about +Y by tilt.
    coating_normal = _unit((sin_t, 0.0, cos_t))

    # Axis-aligned half-extent of the tilted box: X and Z mix width & thickness.
    hw = width / 2.0
    hh = height / 2.0
    ht = thickness / 2.0
    ext_x = abs(hw * cos_t) + abs(ht * sin_t)
    ext_z = abs(hw * sin_t) + abs(ht * cos_t)
    return {
        "coating_normal": coating_normal,
        "coating_point": (0.0, 0.0, 0.0),
        "bbox_min": (-ext_x, -hh, -ext_z),
        "bbox_max": (ext_x, hh, ext_z),
    }


def beam_splitter_metadata(kind: str, params: dict) -> dict:
    """Analytic geometry facts (coating plane, bbox) for a BS template -- OCC-free."""
    kind = str(kind or "").strip().lower()
    if kind == "cube":
        return _cube_geometry(params)
    if kind == "plate":
        return _plate_geometry(params)
    raise ValueError(f"unknown beam-splitter kind {kind!r} (want 'cube' or 'plate')")


# ---------------------------------------------------------------------------
# Cache paths -- read CAD_CACHE_DIR dynamically so tests can redirect it.
# ---------------------------------------------------------------------------

def _template_cache_dir() -> Path:
    return Path(cad_cache_paths.CAD_CACHE_DIR) / _TEMPLATE_SUBDIR


def _params_digest(kind: str, params: dict) -> str:
    ordered = "|".join(f"{key}={params[key]!r}" for key in sorted(params))
    payload = f"{kind}|{ordered}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def beam_splitter_cache_path(kind: str, params: dict) -> Path:
    kind = str(kind or "").strip().lower()
    return _template_cache_dir() / f"bs_{kind}_{_params_digest(kind, params)}.step"


# ---------------------------------------------------------------------------
# OCC solid construction + STEP write.
# ---------------------------------------------------------------------------

def _make_cube_shape(side_mm: float):
    """Two cemented right-angle prisms sharing the X = Z diagonal (a compound).

    The XZ square [-s/2, s/2]^2 is split by the diagonal X = Z into two right
    triangles; each is extruded along +Y by ``s`` into a right-angle prism. The
    shared hypotenuse (present once per prism, coincident) is the 45-degree coating
    plane -- exactly what a plain box lacks.
    """
    from OCC.Core.BRep import BRep_Builder
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCC.Core.TopoDS import TopoDS_Compound
    from OCC.Core.gp import gp_Pnt, gp_Vec

    side = float(side_mm)
    half = side / 2.0

    def _prism(triangle_xz):
        polygon = BRepBuilderAPI_MakePolygon()
        for x, z in triangle_xz:
            polygon.Add(gp_Pnt(float(x), -half, float(z)))
        polygon.Close()
        if not polygon.IsDone():
            raise RuntimeError("beam-splitter cube: could not build a prism cross-section")
        face = BRepBuilderAPI_MakeFace(polygon.Wire())
        if not face.IsDone():
            raise RuntimeError("beam-splitter cube: could not face a prism cross-section")
        prism = BRepPrimAPI_MakePrism(face.Face(), gp_Vec(0.0, side, 0.0))
        if not prism.IsDone():
            raise RuntimeError("beam-splitter cube: prism extrusion failed")
        return prism.Shape()

    # Triangle A: X >= Z half; Triangle B: X <= Z half. Both share the diagonal.
    prism_a = _prism([(-half, -half), (half, -half), (half, half)])
    prism_b = _prism([(-half, -half), (half, half), (-half, half)])

    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)
    builder.Add(compound, prism_a)
    builder.Add(compound, prism_b)
    return compound


def _make_plate_shape(width_mm: float, height_mm: float, thickness_mm: float, tilt_deg: float):
    """A thin (w x h x t) box centered at the origin, rotated ``tilt`` about +Y."""
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCC.Core.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf

    width = float(width_mm)
    height = float(height_mm)
    thickness = float(thickness_mm)
    corner = gp_Pnt(-width / 2.0, -height / 2.0, -thickness / 2.0)
    # BRepPrimAPI_MakeBox.IsDone() stays False until Build(); the produced Shape is
    # the reliable check.
    box_shape = BRepPrimAPI_MakeBox(corner, width, height, thickness).Shape()
    if box_shape.IsNull():
        raise RuntimeError("beam-splitter plate: box construction failed")

    trsf = gp_Trsf()
    trsf.SetRotation(gp_Ax1(gp_Pnt(0.0, 0.0, 0.0), gp_Dir(0.0, 1.0, 0.0)), math.radians(float(tilt_deg)))
    transformed = BRepBuilderAPI_Transform(box_shape, trsf, True)
    if not transformed.IsDone():
        raise RuntimeError("beam-splitter plate: 45-degree tilt failed")
    return transformed.Shape()


def _write_shape_step(shape, target_path: Path) -> None:
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.Interface import Interface_Static
    from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer

    target_path = Path(target_path).expanduser()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    writer = STEPControl_Writer()
    try:
        Interface_Static.SetCVal("write.step.unit", "MM")
    except Exception:
        pass
    # OCC's transfer/write chatters on stdout/stderr; mute it like the other exporters.
    stdout_fd = stderr_fd = None
    try:
        stdout_fd = os.dup(1)
        stderr_fd = os.dup(2)
        with open(os.devnull, "w", encoding="utf-8") as devnull:
            os.dup2(devnull.fileno(), 1)
            os.dup2(devnull.fileno(), 2)
            writer.Transfer(shape, STEPControl_AsIs)
            status = writer.Write(str(target_path))
    except Exception:
        writer.Transfer(shape, STEPControl_AsIs)
        status = writer.Write(str(target_path))
    finally:
        for src_fd, dst_fd in ((stdout_fd, 1), (stderr_fd, 2)):
            if src_fd is None:
                continue
            try:
                os.dup2(int(src_fd), dst_fd)
                os.close(int(src_fd))
            except Exception:
                pass
    if status != IFSelect_RetDone or not target_path.exists() or target_path.stat().st_size <= 0:
        raise RuntimeError(f"beam-splitter STEP writer failed for {target_path}")


def _build_shape(kind: str, params: dict):
    if kind == "cube":
        return _make_cube_shape(params["side_mm"])
    if kind == "plate":
        return _make_plate_shape(
            params["width_mm"], params["height_mm"], params["thickness_mm"], params["tilt_deg"]
        )
    raise ValueError(f"unknown beam-splitter kind {kind!r} (want 'cube' or 'plate')")


def _solid_from(kind: str, params: dict, *, force: bool) -> BeamSplitterSolid:
    geometry = beam_splitter_metadata(kind, params)
    path = beam_splitter_cache_path(kind, params)
    notes: list = []
    regenerated = False
    if force or not path.exists() or path.stat().st_size <= 0:
        shape = _build_shape(kind, params)
        _write_shape_step(shape, path)
        regenerated = True
        notes.append(f"generated {kind} template -> {path.name}")
    else:
        notes.append(f"reused cached {kind} template <- {path.name}")
    return BeamSplitterSolid(
        path=path,
        kind=kind,
        params=dict(params),
        coating_normal=geometry["coating_normal"],
        coating_point=geometry["coating_point"],
        bbox_min=geometry["bbox_min"],
        bbox_max=geometry["bbox_max"],
        regenerated=regenerated,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------

def beam_splitter_cube_step(side_mm: float, *, force: bool = False) -> BeamSplitterSolid:
    """Generate (or reuse) a cube BS template of the given side; regen if missing."""
    return _solid_from("cube", _normalize_cube_params(side_mm), force=force)


def beam_splitter_plate_step(
    width_mm: float,
    height_mm: float,
    thickness_mm: float,
    *,
    tilt_deg: float = 45.0,
    force: bool = False,
) -> BeamSplitterSolid:
    """Generate (or reuse) a tilted-plate BS template; regen if missing."""
    return _solid_from(
        "plate", _normalize_plate_params(width_mm, height_mm, thickness_mm, tilt_deg), force=force
    )


def generate_beam_splitter(kind: str, *, force: bool = False, **dimensions) -> BeamSplitterSolid:
    """Kind-dispatched entry point for the orchestration layer.

    ``kind="cube"`` needs ``side_mm``; ``kind="plate"`` needs ``width_mm``,
    ``height_mm``, ``thickness_mm`` (+ optional ``tilt_deg``).
    """
    kind = str(kind or "").strip().lower()
    if kind == "cube":
        return beam_splitter_cube_step(dimensions["side_mm"], force=force)
    if kind == "plate":
        return beam_splitter_plate_step(
            dimensions["width_mm"],
            dimensions["height_mm"],
            dimensions["thickness_mm"],
            tilt_deg=float(dimensions.get("tilt_deg", 45.0)),
            force=force,
        )
    raise ValueError(f"unknown beam-splitter kind {kind!r} (want 'cube' or 'plate')")
