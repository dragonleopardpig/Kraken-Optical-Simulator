"""Isolate the illumination overlay BUILDER from any trace (pure numpy).

Feeds synthetic detector-hit samples straight through the real
source_illumination_map_data_from_samples -> build_source_illumination_overlay pipeline with
the SENSOR window (target_model active dims = 23.04, coord='local' -> extent is exactly the
sensor, no data-footprint pad). Two fills:

  A. UNIFORM tiling the FULL sensor (+/-11.52mm). If the builder is correct this must read
     ~1.0 everywhere. If it reads radial 4-dark, the builder fabricates a vignette (real bug).
  B. UNIFORM tiling only the central +/-6.8mm (what the real imaging preview reaches). The
     region 6.8..11.52 is genuinely empty -> a correct builder SHOULD read dark there; that
     would confirm the real-scene 4-dark is a SPARSE-SAMPLE artifact (rays don't reach the rim),
     not a builder bug.

Run: .devenv/state/venv/bin/python bugs/diag_0280_builder_probe.py
"""
from __future__ import annotations

import numpy as np

from KrakenOS.UI.source_illumination_analysis import source_illumination_map_data_from_samples
from KrakenOS.UI.services.source_illumination_overlay import build_source_illumination_overlay

SENSOR = 23.04
HALF = 0.5 * SENSOR
MODEL = {"is_detector": True, "active_width_mm": SENSOR, "active_height_mm": SENSOR}
CENTER, NORMAL, TANGENT = (0.0, 0.0, 657.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)


def _fill(span_half: float, n: int = 120) -> dict:
    g = np.linspace(-span_half, span_half, n)
    gx, gy = np.meshgrid(g, g)
    return {"x": gx.ravel(), "y": gy.ravel(), "coord": "local",
            "target_surface": 8, "target_name": "Image"}


def _report(tag: str, span_half: float, bins: int = 10) -> None:
    samples = _fill(span_half)
    map_data = source_illumination_map_data_from_samples(samples, target_model=MODEL, bins=bins)
    dens = np.asarray(map_data["density"], dtype=float)
    ov = build_source_illumination_overlay(map_data, center=CENTER, normal=NORMAL, tangent=TANGENT)
    rel = np.asarray(ov["relative"], dtype=float)
    c = rel.shape[0] // 2
    centre = float(rel[c, c])
    edge = float(np.mean([rel[:, 0].mean(), rel[:, -1].mean(), rel[0, :].mean(), rel[-1, :].mean()]))
    corner = float(np.mean([rel[0, 0], rel[0, -1], rel[-1, 0], rel[-1, -1]]))
    print(f"{tag}: fill +/-{span_half:.2f}mm on {SENSOR}mm sensor, bins={bins}")
    print(f"   raw density  min={dens.min():.3f} max={dens.max():.3f} "
          f"corner={np.mean([dens[0,0],dens[0,-1],dens[-1,0],dens[-1,-1]]):.3f} "
          f"centre={dens[c,c]:.3f}")
    print(f"   relative     centre={centre:.3f} edge={edge:.3f} corner={corner:.3f}")
    print()


def main() -> int:
    print("=== BUILDER ISOLATION PROBE (sensor window, no data-footprint pad) ===\n")
    _report("A full-sensor uniform", HALF)
    _report("B central-6.8 uniform", 6.8)
    print("Interpretation:")
    print("  A ~1.0 everywhere  -> builder OK; real 4-dark is a SPARSE-SAMPLE artifact (fix the sample/coverage)")
    print("  A radial 4-dark    -> builder BUG (fabricates vignette from uniform input; fix the builder)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
