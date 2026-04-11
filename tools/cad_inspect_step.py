#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GProp import GProp_GProps
from OCC.Core.GeomAbs import (
    GeomAbs_BSplineSurface,
    GeomAbs_BezierSurface,
    GeomAbs_Cone,
    GeomAbs_Cylinder,
    GeomAbs_Plane,
    GeomAbs_Sphere,
    GeomAbs_SurfaceOfExtrusion,
    GeomAbs_SurfaceOfRevolution,
    GeomAbs_Torus,
)
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_SOLID
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import topods


SURFACE_TYPE_NAMES = {
    GeomAbs_Plane: "plane",
    GeomAbs_Cylinder: "cylinder",
    GeomAbs_Cone: "cone",
    GeomAbs_Sphere: "sphere",
    GeomAbs_Torus: "torus",
    GeomAbs_BezierSurface: "bezier",
    GeomAbs_BSplineSurface: "bspline",
    GeomAbs_SurfaceOfRevolution: "revolution",
    GeomAbs_SurfaceOfExtrusion: "extrusion",
}


def shape_bounds(shape) -> list[float]:
    box = Bnd_Box()
    box.SetGap(0.0)
    brepbndlib.Add(shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return [float(xmin), float(xmax), float(ymin), float(ymax), float(zmin), float(zmax)]


def shape_volume(shape) -> float:
    props = GProp_GProps()
    try:
        brepgprop.VolumeProperties(shape, props)
    except Exception:
        return 0.0
    return float(props.Mass())


def face_type_name(face) -> str:
    try:
        adaptor = BRepAdaptor_Surface(face, True)
        return SURFACE_TYPE_NAMES.get(adaptor.GetType(), "other")
    except Exception:
        return "other"


def face_area(face) -> float:
    props = GProp_GProps()
    try:
        brepgprop.SurfaceProperties(face, props)
    except Exception:
        return 0.0
    return float(props.Mass())


def face_centroid(face) -> list[float]:
    props = GProp_GProps()
    try:
        brepgprop.SurfaceProperties(face, props)
        center = props.CentreOfMass()
        return [float(center.X()), float(center.Y()), float(center.Z())]
    except Exception:
        return [0.0, 0.0, 0.0]


def face_plane_normal(face) -> list[float] | None:
    try:
        surface = BRepAdaptor_Surface(face, True)
        if surface.GetType() != GeomAbs_Plane:
            return None
        plane = surface.Plane()
        direction = plane.Axis().Direction()
        return [float(direction.X()), float(direction.Y()), float(direction.Z())]
    except Exception:
        return None


def face_cylinder_axis(face) -> list[float] | None:
    try:
        surface = BRepAdaptor_Surface(face, True)
        if surface.GetType() != GeomAbs_Cylinder:
            return None
        axis = surface.Cylinder().Axis().Direction()
        return [float(axis.X()), float(axis.Y()), float(axis.Z())]
    except Exception:
        return None


def iter_solids(shape):
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        yield topods.Solid(explorer.Current())
        explorer.Next()


def iter_faces(shape):
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        yield topods.Face(explorer.Current())
        explorer.Next()


def summarize_step(path: Path) -> dict:
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to read STEP: status={status}")
    if reader.TransferRoots() == 0:
        raise RuntimeError("STEP transfer produced no roots")
    shape = reader.OneShape()

    solids = []
    plane_faces = []
    cylinder_faces = []
    for solid_index, solid in enumerate(iter_solids(shape)):
        bounds = shape_bounds(solid)
        volume = shape_volume(solid)
        face_counts: dict[str, int] = {}
        solid_plane_area = 0.0
        solid_cylinder_area = 0.0
        face_total = 0
        for face_index, face in enumerate(iter_faces(solid)):
            face_total += 1
            kind = face_type_name(face)
            face_counts[kind] = face_counts.get(kind, 0) + 1
            area = face_area(face)
            centroid = face_centroid(face)
            if kind == "plane":
                normal = face_plane_normal(face)
                solid_plane_area += area
                plane_faces.append(
                    {
                        "solid_index": solid_index,
                        "face_index": face_index,
                        "area": area,
                        "centroid": centroid,
                        "normal": normal,
                    }
                )
            elif kind == "cylinder":
                axis = face_cylinder_axis(face)
                solid_cylinder_area += area
                cylinder_faces.append(
                    {
                        "solid_index": solid_index,
                        "face_index": face_index,
                        "area": area,
                        "centroid": centroid,
                        "axis": axis,
                    }
                )
        solids.append(
            {
                "solid_index": solid_index,
                "volume": volume,
                "bounds": bounds,
                "extent": [bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]],
                "face_count": face_total,
                "face_types": face_counts,
                "plane_area": solid_plane_area,
                "cylinder_area": solid_cylinder_area,
            }
        )

    solids.sort(key=lambda item: item["volume"], reverse=True)
    plane_faces.sort(key=lambda item: item["area"], reverse=True)
    cylinder_faces.sort(key=lambda item: item["area"], reverse=True)

    top_planes = plane_faces[:12]
    top_cylinders = cylinder_faces[:12]
    return {
        "path": str(path),
        "bounds": shape_bounds(shape),
        "solid_count": len(solids),
        "solids_by_volume": solids[:20],
        "top_plane_faces": top_planes,
        "top_cylinder_faces": top_cylinders,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect a STEP file for CAD alignment work.")
    parser.add_argument("step_path", type=Path)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    summary = summarize_step(args.step_path.expanduser().resolve())
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
