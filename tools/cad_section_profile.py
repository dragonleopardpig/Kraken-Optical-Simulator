#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from OCC.Core.BRep import BRep_Builder
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Section
from OCC.Core.GCPnts import GCPnts_AbscissaPoint
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_SOLID
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Compound, topods
from OCC.Core.gp import gp_Dir, gp_Pln, gp_Pnt

from cad_detect_reference import detect_reference


def load_solids(step_path: Path):
    reader = STEPControl_Reader()
    status = reader.ReadFile(str(step_path))
    if status != IFSelect_RetDone:
        raise RuntimeError(f"Failed to read STEP: status={status}")
    if reader.TransferRoots() == 0:
        raise RuntimeError("STEP transfer produced no roots")
    shape = reader.OneShape()
    solids = []
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        solids.append(topods.Solid(explorer.Current()))
        explorer.Next()
    return solids


def sample_edge_points(edge, step: float) -> list[list[float]]:
    curve = BRepAdaptor_Curve(edge)
    first = float(curve.FirstParameter())
    last = float(curve.LastParameter())
    try:
        length = float(GCPnts_AbscissaPoint.Length(curve, first, last))
    except Exception:
        length = 0.0
    count = max(8, min(160, int(length / max(step, 1e-3)) + 2))
    pts: list[list[float]] = []
    for i in range(count):
        t = first + (last - first) * (i / max(count - 1, 1))
        p = curve.Value(t)
        pts.append([float(p.X()), float(p.Y()), float(p.Z())])
    return pts


def build_outer_profile(points_xyz: list[list[float]], bins: int = 220) -> list[list[float]]:
    if len(points_xyz) < 8:
        return []
    z_vals = [p[2] for p in points_xyz]
    z_min = min(z_vals)
    z_max = max(z_vals)
    if z_max <= z_min:
        return []
    top: list[list[float]] = []
    bottom: list[list[float]] = []
    for i in range(max(bins, 24)):
        lo = z_min + (z_max - z_min) * (i / bins)
        hi = z_min + (z_max - z_min) * ((i + 1) / bins)
        if i == bins - 1:
            bucket = [p for p in points_xyz if lo <= p[2] <= hi]
        else:
            bucket = [p for p in points_xyz if lo <= p[2] < hi]
        if not bucket:
            continue
        z_mid = sum(p[2] for p in bucket) / len(bucket)
        ys = sorted(p[1] for p in bucket)
        if len(ys) >= 5:
            top_y = ys[max(0, int(0.90 * (len(ys) - 1)))]
            bot_y = ys[min(len(ys) - 1, int(0.10 * (len(ys) - 1)))]
        else:
            top_y = ys[-1]
            bot_y = ys[0]
        top.append([0.0, top_y, z_mid])
        bottom.append([0.0, bot_y, z_mid])
    if len(top) < 4 or len(bottom) < 4:
        return []
    top = _smooth_profile(top, keep="upper")
    bottom = _smooth_profile(bottom, keep="lower")
    return top + list(reversed(bottom)) + [top[0]]


def _smooth_profile(profile: list[list[float]], keep: str) -> list[list[float]]:
    if len(profile) < 5:
        return profile
    window = 5
    values = [row[1] for row in profile]
    z_vals = [row[2] for row in profile]
    smoothed: list[list[float]] = []
    for idx in range(len(profile)):
        lo = max(0, idx - window)
        hi = min(len(profile), idx + window + 1)
        local = sorted(values[lo:hi])
        median = local[len(local) // 2]
        current = values[idx]
        if keep == "upper":
            y_val = min(current, median + 1.5)
        else:
            y_val = max(current, median - 1.5)
        smoothed.append([0.0, y_val, z_vals[idx]])

    filtered: list[list[float]] = [smoothed[0]]
    for row in smoothed[1:]:
        prev = filtered[-1]
        if abs(row[1] - prev[1]) < 0.25 and abs(row[2] - prev[2]) < 0.75:
            filtered[-1] = [0.0, 0.5 * (prev[1] + row[1]), row[2]]
        else:
            filtered.append(row)
    return _morphological_envelope(filtered, keep=keep)


def _morphological_envelope(profile: list[list[float]], keep: str) -> list[list[float]]:
    if len(profile) < 9:
        return profile
    z_vals = [row[2] for row in profile]
    y_vals = [row[1] for row in profile]
    out = list(y_vals)
    radius = 4
    for _ in range(2):
        expanded: list[float] = []
        for idx in range(len(out)):
            lo = max(0, idx - radius)
            hi = min(len(out), idx + radius + 1)
            window = out[lo:hi]
            expanded.append(max(window) if keep == "upper" else min(window))
        contracted: list[float] = []
        for idx in range(len(expanded)):
            lo = max(0, idx - radius)
            hi = min(len(expanded), idx + radius + 1)
            window = expanded[lo:hi]
            contracted.append(min(window) if keep == "upper" else max(window))
        out = contracted
    simplified: list[list[float]] = [[0.0, out[0], z_vals[0]]]
    for idx in range(1, len(out)):
        prev = simplified[-1]
        if abs(out[idx] - prev[1]) < 0.2 and abs(z_vals[idx] - prev[2]) < 1.0:
            simplified[-1] = [0.0, 0.5 * (prev[1] + out[idx]), z_vals[idx]]
        else:
            simplified.append([0.0, out[idx], z_vals[idx]])
    return simplified


def extract_section_profile(step_path: Path, solid_indices: list[int], sample_step: float) -> dict[str, object]:
    solids = load_solids(step_path)
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    for index in solid_indices:
        if index < 0 or index >= len(solids):
            raise RuntimeError(f"Solid index out of range: {index} (0..{len(solids)-1})")
        builder.Add(compound, solids[index])

    ref = detect_reference(step_path, solid_indices)
    ref_x = float(ref["reference_xy"][0])
    plane = gp_Pln(gp_Pnt(ref_x, 0.0, 0.0), gp_Dir(1.0, 0.0, 0.0))
    section = BRepAlgoAPI_Section(compound, plane, False)
    section.Build()
    if not section.IsDone():
        raise RuntimeError("Section build failed")

    sampled: list[list[float]] = []
    explorer = TopExp_Explorer(section.Shape(), TopAbs_EDGE)
    while explorer.More():
        edge = topods.Edge(explorer.Current())
        sampled.extend(sample_edge_points(edge, sample_step))
        explorer.Next()
    profile = build_outer_profile(sampled)
    return {
        "reference_xy": ref["reference_xy"],
        "method": "occ_section_profile",
        "sample_count": len(sampled),
        "profile_points": profile,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract a STEP YZ section profile for 2D layout overlay.")
    parser.add_argument("step_path", type=Path)
    parser.add_argument("--solids", required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--sample-step", type=float, default=0.5)
    args = parser.parse_args()

    indices = [int(part.strip()) for part in args.solids.split(",") if part.strip()]
    result = extract_section_profile(args.step_path.expanduser().resolve(), indices, float(args.sample_step))
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(args.json_out)


if __name__ == "__main__":
    main()
