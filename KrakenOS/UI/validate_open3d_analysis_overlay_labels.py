"""Display-free guard: the image-plane analysis overlays share ONE expanding label.

Turning on several image-plane analysis overlays at once (best-focus surface, distortion
grid, astigmatism surfaces, spot RMS map, camera pixel grid) used to draw a SEPARATE
billboard near the detector top for each one -- so with two or more enabled the labels
overlapped into an unreadable pile (flag_20260629_085625_442; user: "the texts labels
overlap ... just group them in one label, expand it if more analysis are shown").

The fix routes every overlay's label text through a shared collector
(``_queue_analysis_overlay_label``) instead of each drawing its own billboard, and renders
ONE combined billboard (``_add_grouped_analysis_overlay_label``) anchored at the image-plane
top-right corner that grows downward as more overlays are enabled.

This guard pins (headless, no Tk/VTK):

  * FUNCTIONAL: reset clears the collector; queue appends in order, locks the anchor basis to
    the FIRST overlay, and skips empty text; the combined drawer is a safe no-op (returns 0,
    never raises) when there is no renderer -- even with sections queued.
  * SOURCE CONTRACT: the combined drawer joins the sections (``"\n\n".join``) into a SINGLE
    ``vtkBillboardTextActor3D`` and corner-anchors via the camera screen axes; each of the five
    overlay methods queues its label and NO LONGER creates its own billboard; the scene refresh
    resets the collector before the overlays and draws the combined label after.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_analysis_overlay_labels

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect

from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService

_OVERLAY_METHODS = (
    "_add_best_focus_surface_overlays",
    "_add_distortion_grid_overlays",
    "_add_astigmatism_surfaces_overlays",
    "_add_spot_field_map_overlays",
    "_add_pixel_grid_overlays",
)


class _Stub:
    """Minimal stand-in: the collector helpers touch only plain attributes + numpy."""

    _renderer = None


def _check_functional(failures: list[str]) -> None:
    stub = _Stub()
    Kraken3DInspector._reset_analysis_overlay_labels(stub)
    if stub._analysis_overlay_label_sections != []:
        failures.append("FUNCTIONAL: reset did not clear the label sections to an empty list")
    if stub._analysis_overlay_label_center is not None or stub._analysis_overlay_label_normal is not None:
        failures.append("FUNCTIONAL: reset did not clear the anchor basis")

    # Queue accumulates in order; the FIRST overlay's center/normal fixes the shared anchor.
    Kraken3DInspector._queue_analysis_overlay_label(stub, "Alpha", center=[0.0, 0.0, 1.0], normal=[0.0, 0.0, 2.0])
    Kraken3DInspector._queue_analysis_overlay_label(stub, "Beta", center=[9.0, 9.0, 9.0], normal=[9.0, 9.0, 9.0])
    Kraken3DInspector._queue_analysis_overlay_label(stub, "")  # empty must be skipped
    Kraken3DInspector._queue_analysis_overlay_label(stub, None)  # None must be skipped
    if stub._analysis_overlay_label_sections != ["Alpha", "Beta"]:
        failures.append(f"FUNCTIONAL: queue did not accumulate in order / skip empties ({stub._analysis_overlay_label_sections!r})")
    if list(stub._analysis_overlay_label_center) != [0.0, 0.0, 1.0]:
        failures.append("FUNCTIONAL: anchor center should lock to the FIRST queued overlay")
    if list(stub._analysis_overlay_label_normal) != [0.0, 0.0, 2.0]:
        failures.append("FUNCTIONAL: anchor normal should lock to the FIRST queued overlay")

    # The combined drawer is a safe no-op when there is no renderer -- even with sections queued.
    try:
        drawn = Kraken3DInspector._add_grouped_analysis_overlay_label(stub)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"FUNCTIONAL: combined drawer raised with no renderer ({exc!r})")
        drawn = -1
    if drawn != 0:
        failures.append("FUNCTIONAL: combined drawer should return 0 (drew nothing) with no renderer")

    # Queue auto-initialises even if reset was somehow skipped (defensive path).
    fresh = _Stub()
    Kraken3DInspector._queue_analysis_overlay_label(fresh, "Solo", center=[1.0, 0.0, 0.0], normal=[1.0, 0.0, 0.0])
    if getattr(fresh, "_analysis_overlay_label_sections", None) != ["Solo"]:
        failures.append("FUNCTIONAL: queue must auto-initialise the collector when reset was not called")


def _check_source_contract(failures: list[str]) -> None:
    drawer_src = inspect.getsource(Kraken3DInspector._add_grouped_analysis_overlay_label)
    if '"\\n\\n".join(' not in drawer_src:
        failures.append("CONTRACT: combined drawer must join the queued sections into one block")
    if drawer_src.count("vtkBillboardTextActor3D()") != 1:
        failures.append("CONTRACT: combined drawer must create exactly ONE billboard")
    if "_camera_screen_world_axes(" not in drawer_src:
        failures.append("CONTRACT: combined drawer must corner-anchor via the camera screen axes")

    for name in _OVERLAY_METHODS:
        src = inspect.getsource(getattr(Kraken3DInspector, name))
        if "_queue_analysis_overlay_label(" not in src:
            failures.append(f"CONTRACT: {name} must queue its label into the shared legend")
        if "vtkBillboardTextActor3D" in src:
            failures.append(f"CONTRACT: {name} must NOT draw its own billboard (group into one label)")

    refresh_src = inspect.getsource(Open3DSceneRefreshService.refresh_scene)
    if "_reset_analysis_overlay_labels(" not in refresh_src:
        failures.append("CONTRACT: refresh_scene must reset the label collector before the overlays")
    if "_add_grouped_analysis_overlay_label(" not in refresh_src:
        failures.append("CONTRACT: refresh_scene must draw the combined label after the overlays")
    if (
        "_reset_analysis_overlay_labels(" in refresh_src
        and "_add_grouped_analysis_overlay_label(" in refresh_src
        and refresh_src.index("_reset_analysis_overlay_labels(") > refresh_src.index("_add_grouped_analysis_overlay_label(")
    ):
        failures.append("CONTRACT: refresh_scene must reset BEFORE it draws the combined label")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    _check_functional(failures)
    _check_source_contract(failures)
    return (not failures), failures


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    if not passed:
        print("[FAIL] analysis overlays share one expanding label")
        return 1
    print("[PASS] image-plane analysis overlays group into one expanding label")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
