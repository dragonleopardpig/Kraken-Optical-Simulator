"""Guard for bugs/0352: image analyses survive a non-imaging BS branch.

The MV-150 cube preview has two synthetic branch detectors: a reflected leaf
focused beside the cube (``focus_source='converging_rays'``) and the transmitted
leaf that terminates on the prescription Image plane
(``focus_source='reached_image'``).  The image-analysis anchor used to return
``None`` as soon as *any* branch detector existed, which disabled Focus surface,
Distortion, Astigmatism, Spot map, and Pixel grid together.  Illumination uses a
different anchor resolver, so it was the only Analysis Overlay left working in
``recording_20260719_095137.json``.

This guard checks the pure selector policy and, when the user's gitignored MV-150
fixture is present, builds that exact scene and proves all five analysis specs are
again non-empty on its unique reached-Image branch.

Run::

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python -m \
        KrakenOS.UI.validate_open3d_analysis_overlays_reached_image_branch
"""

from __future__ import annotations

import os

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/kraken-mpl")

from pathlib import Path
from types import SimpleNamespace

from KrakenOS.UI.layout_editor import _load_python_data
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin


_MV150 = Path(__file__).resolve().parents[2] / "attachment" / "machine_vision_150mm_test.py"


def _target(
    target_id: str,
    row_index: int,
    *,
    source: str = "table_row",
    focus_source: str = "",
    surface: str = "Image",
    is_detector: bool = True,
    draw_suppressed: bool = False,
):
    metadata = {"target_source": source}
    if focus_source:
        metadata["focus_source"] = focus_source
    if draw_suppressed:
        metadata["draw_suppressed"] = True
    return SimpleNamespace(
        target_id=target_id,
        row_index=row_index,
        surface=surface,
        is_detector=is_detector,
        metadata=metadata,
    )


def _anchor(targets):
    bundle = SimpleNamespace(targets=list(targets))
    return ThreeDSceneToolsMixin._best_focus_surface_anchor_target(SimpleNamespace(), bundle)


def _check_policy(failures: list[str], notes: list[str]) -> None:
    obj = _target("object", 0, surface="Object", is_detector=False)
    stop = _target("stop", 5, surface="Aperture Stop", is_detector=False)
    canonical = _target("image", 8)
    reflect = _target(
        "reflect",
        100000,
        source="branch_detector",
        focus_source="converging_rays",
        surface="",
    )
    reached = _target(
        "transmit",
        100001,
        source="branch_detector",
        focus_source="reached_image",
        surface="",
    )

    selected = _anchor([obj, stop, canonical, reflect, reached])
    if selected is not canonical:
        failures.append("POLICY: a canonical Image detector must outrank synthetic branches")

    selected = _anchor([obj, stop, reflect, reached])
    if selected is not reached:
        failures.append("POLICY: the unique reached-image branch was not selected")

    if _anchor([obj, stop, reflect]) is not None:
        failures.append("POLICY: a converging/parked non-imaging branch became an analysis anchor")

    reached_2 = _target(
        "second-image-arm",
        100002,
        source="branch_detector",
        focus_source="reached_image",
        surface="",
    )
    if _anchor([obj, stop, reached, reached_2]) is not None:
        failures.append("POLICY: multiple reached-image arms must stay ambiguous until an arm is selected")

    suppressed = _target(
        "suppressed-image-arm",
        100003,
        source="branch_detector",
        focus_source="reached_image",
        surface="",
        draw_suppressed=True,
    )
    if _anchor([obj, stop, suppressed]) is not None:
        failures.append("POLICY: a draw-suppressed reached-image branch became an analysis anchor")

    if not failures:
        notes.append("policy: canonical detector preferred; one reached-image branch accepted; ambiguous arms rejected")


def _check_real_mv150(failures: list[str], notes: list[str]) -> None:
    if not _MV150.exists():
        notes.append("real MV-150: SKIP gitignored attachment/machine_vision_150mm_test.py is absent")
        return

    info = _load_python_data(_MV150)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(_rows_from_layout_info(info), settings)
    editor.tk = object()
    editor.current_layout_file = str(_MV150)
    editor._normalize_special_rows()
    system, _rays, bundle = editor._build_preview_system_rays_bundle(
        sampling_mode="world_envelope",
        update_state=True,
        include_live_step_overlays=False,
    )

    branch_targets = [
        target
        for target in list(getattr(bundle, "targets", []) or [])
        if str((getattr(target, "metadata", {}) or {}).get("target_source", "")) == "branch_detector"
    ]
    reached = [
        target
        for target in branch_targets
        if str((getattr(target, "metadata", {}) or {}).get("focus_source", "")) == "reached_image"
        and not bool((getattr(target, "metadata", {}) or {}).get("draw_suppressed", False))
    ]
    anchor = editor._best_focus_surface_anchor_target(bundle)
    if len(reached) != 1:
        failures.append(f"REAL: expected one usable reached-image branch, found {len(reached)}")
        return
    if anchor is not reached[0]:
        failures.append("REAL: MV-150 analysis anchor is not its transmitted reached-Image detector")
        return

    # One expensive field scan is enough for Focus, Distortion, and Astigmatism.
    # Feed its immutable result back to those three public spec builders so this
    # regression remains strong without tracing the identical scan three times.
    wavelength = float(editor._current_wavelength())
    analysis_service = editor._analysis_plot_service()
    sampled = analysis_service._sample_field_curvature_distortion(system, wavelength)
    original_scan = analysis_service._sample_field_curvature_distortion
    analysis_service._sample_field_curvature_distortion = lambda *_args, **_kwargs: sampled
    try:
        specs = {
            "Focus surf": editor.best_focus_surface_overlay_spec(system, bundle, wavelength=wavelength),
            "Distortion": editor.distortion_grid_overlay_spec(system, bundle, wavelength=wavelength),
            "Astigmatism": editor.astigmatism_surfaces_overlay_spec(system, bundle, wavelength=wavelength),
            "Spot map": editor.spot_field_map_overlay_spec(system, bundle, wavelength=wavelength),
            "Pixel grid": editor.pixel_grid_overlay_spec(system, bundle, wavelength=wavelength),
        }
    finally:
        analysis_service._sample_field_curvature_distortion = original_scan

    missing = [name for name, spec in specs.items() if not spec]
    if missing:
        failures.append(f"REAL: MV-150 analysis specs still empty: {', '.join(missing)}")
        return
    notes.append(
        "real MV-150: unique S1/transmit reached-Image target restores Focus, Distortion, "
        "Astigmatism, Spot map, and Pixel grid"
    )


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    notes: list[str] = []
    _check_policy(failures, notes)
    _check_real_mv150(failures, notes)
    return (not failures), failures + notes


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    print("[PASS] reached-Image branch keeps all image analysis overlays" if passed else "[FAIL] reached-Image analysis overlays")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
