#!/usr/bin/env python3
"""Reproduce the user's 150mm machine-vision 1X datasheet scene (two thin-lens
groups, finite object) and trace it WITH vs WITHOUT a 50mm BK7 plate before the
lens, to find where the transmit beam really focuses (recording 231705: rays
diverge after promoting the cube before the lens).

Run: .devenv/state/venv/bin/python bugs/diag_1x_cube.py
"""
from __future__ import annotations
import numpy as np
import KrakenOS as Kos
from KrakenOS.TraceEvents import trace_event_to_record
from KrakenOS.common_optical_layouts.machine_vision_150mm_datasheet_1x import SURFACES

WL = 0.546
EPD = 26.8
FRONT_DATUM_Z = 275.0  # object -> front datum


def _closest_approach(o, d):
    M = np.zeros((3, 3)); b = np.zeros(3); I = np.eye(3)
    for oo, dd in zip(o, d):
        dd = dd / np.linalg.norm(dd); proj = I - np.outer(dd, dd)
        M += proj; b += proj @ oo
    return np.linalg.solve(M, b)


def _specs(with_plate: bool):
    s = [dict(x) for x in SURFACES]
    if not with_plate:
        return s
    # split the object->front-datum gap (275) around a 50mm BK7 plate at z=100..150
    s[0] = dict(s[0], thickness=100.0)                                   # object -> plate front
    pf = {"surface": "Standard", "name": "plate front", "rc": 0.0, "thickness": 50.0, "diameter": 50.0, "glass": "BK7"}
    pb = {"surface": "Standard", "name": "plate back", "rc": 0.0, "thickness": FRONT_DATUM_Z - 100.0 - 50.0, "diameter": 50.0, "glass": "AIR"}
    return [s[0], pf, pb] + s[1:]


def _focus(with_plate: bool):
    from KrakenOS.UI.layout_editor import _build_system_from_specs
    import contextlib, io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        system = _build_system_from_specs(_specs(with_plate))
        system.energy_probability = 0
        rays = Kos.raykeeper(system)
        # on-axis finite object at z=0, marginal rays filling the EPD at the front datum
        for x in np.linspace(-EPD / 2, EPD / 2, 9):
            for y in np.linspace(-EPD / 2, EPD / 2, 9):
                d = np.array([x / FRONT_DATUM_Z, y / FRONT_DATUM_Z, 1.0])
                system.NsTrace([0.0, 0.0, 0.0], [float(d[0]), float(d[1]), float(d[2])], WL)
                rays.push()
    origins, dirs = [], []
    for ev in getattr(rays, "TRACE_EVENTS", []):
        recs = [trace_event_to_record(e) for e in (ev or [])]
        pts = [np.asarray(r.get("point_world"), float) for r in recs
               if np.all(np.isfinite(np.asarray(r.get("point_world"), float)))]
        dd = []
        for p in pts:
            if not dd or np.linalg.norm(p - dd[-1]) > 1e-6:
                dd.append(p)
        if len(dd) < 2:
            continue
        v = dd[-1] - dd[-2]
        if np.linalg.norm(v) < 1e-9:
            continue
        origins.append(dd[-2]); dirs.append(v / np.linalg.norm(v))
    if len(origins) < 2:
        return None, len(origins)
    return float(_closest_approach(np.asarray(origins), np.asarray(dirs))[2]), len(origins)


def main():
    f0, n0 = _focus(False)
    fp, n1 = _focus(True)
    print(f"NO plate  : {n0} exit rays, transmit converges at z = {f0:.2f}  (image is at 595.8)")
    print(f"WITH plate: {n1} exit rays, transmit converges at z = {fp:.2f}")
    if f0 and fp:
        print(f"\nplate shifted focus {fp - f0:+.2f} mm  (plane-parallel-plate t(1-1/n) = +{50*(1-1/1.5168):.2f})")
        print("=> " + ("FURTHER (push back) -- correct physics" if fp > f0 else f"CLOSER (pulled FORWARD {f0-fp:.1f}mm) -- BUG reproduced"))


if __name__ == "__main__":
    raise SystemExit(main())
