"""Display-free guard for bugs/0355 -- the flat LED's illumination volume.

The emitting rectangle extrudes along the emit direction, folds at the optical axis
by the mirror law, and continues to the Object plane -- one faint translucent
envelope. Reflection is an ISOMETRY (the corrected coaxial_led_dark_edges physics):
the folded Object-plane footprint must stay CONGRUENT to the emitting rectangle.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_illumination_volume_overlay
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.services.illumination_volume_overlay import (
    build_illumination_volume_overlay,
)


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    # Folded: MV-150-like side LED at x=+80 emitting -X toward the axis, 74x55 rect.
    spec = build_illumination_volume_overlay(
        [80.0, 0.0, 229.6], [-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0],
        37.0, 27.5, 0.0,
    )
    if not spec or not spec.get("folded") or len(spec.get("rings", [])) != 3:
        failures.append("side emitter must fold at the axis into a 3-ring volume")
    else:
        end = np.asarray(spec["rings"][-1], dtype=float)
        if not np.allclose(end[:, 2], 0.0, atol=1e-9):
            failures.append("the folded volume must terminate ON the Object plane")
        spans = np.sort((end.max(axis=0) - end.min(axis=0))[:2])
        if not np.allclose(spans, [55.0, 74.0], atol=1e-6):
            failures.append(
                f"ISOMETRY violated: folded footprint {spans} != the 55x74 emitting rect"
            )
        mid = np.asarray(spec["rings"][1], dtype=float)
        if np.ptp(mid[:, 0]) < 1e-9:
            failures.append("the fold ring must lie on the tilted fold plane (x varies)")
        if float(spec["opacity"]) > 0.3:
            failures.append("the volume must stay faint (opacity <= 0.3)")

    # Unfolded teaching scene: emitter above the object aiming straight down.
    spec2 = build_illumination_volume_overlay(
        [0.0, 0.0, 75.0], [0.0, 0.0, -1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0],
        27.5, 37.0, 0.0,
    )
    if not spec2 or spec2.get("folded") or len(spec2.get("rings", [])) != 2:
        failures.append("an axis-aligned emitter must draw a single straight leg")
    elif not np.allclose(np.asarray(spec2["rings"][-1])[:, 2], 0.0, atol=1e-9):
        failures.append("the straight leg must terminate ON the Object plane")

    if build_illumination_volume_overlay(
        [80.0, 0.0, 229.6], [0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], 37.0, 27.5, 0.0
    ) is not None:
        failures.append("a degenerate emit direction must return None")

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService

    add_src = inspect.getsource(Kraken3DInspector._add_illumination_volume_overlays)
    for needle in (
        "_drawable_scene_source_descriptors",
        "_scene_source_glyph_basis",
        "build_illumination_volume_overlay",
        "_object_surface_plane_z",
    ):
        if needle not in add_src:
            failures.append(f"_add_illumination_volume_overlays lost its {needle} anchor")
    refresh_src = inspect.getsource(Open3DSceneRefreshService)
    if (
        "show_illumination_volume_var" not in refresh_src
        or "_add_illumination_volume_overlays" not in refresh_src
    ):
        failures.append("the refresh path does not gate the volume on its toggle")
    import KrakenOS.UI.panels.open3d_top_controls as top_controls

    if "show_illumination_volume_var" not in inspect.getsource(top_controls):
        failures.append("the Overlays menu has no Illum-volume toggle")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Illumination-volume overlay validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Illumination-volume overlay validation passed: the LED's translucent volume "
        "folds at the optical axis by the mirror law with a CONGRUENT footprint "
        "(reflection is an isometry), draws straight on unfolded scenes, and is "
        "gated on its Overlays toggle in the same frame as the source glyph."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
