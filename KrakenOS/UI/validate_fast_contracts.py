"""Run the fast UI/non-sequential contract validation set.

This runner is intentionally narrower than the full visual/CAD smoke suite. It
groups checks that avoid X displays, screenshot capture, and external STEP
fixtures so normal code changes can get a quick first-pass signal before the
targeted heavy diagnostics run.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ValidationTarget:
    alias: str
    module: str
    args: tuple[str, ...] = ()
    reason: str = ""

    @property
    def command(self) -> list[str]:
        return [sys.executable, "-m", self.module, *self.args]


FAST_TARGETS: tuple[ValidationTarget, ...] = (
    ValidationTarget(
        "plot-controller",
        "KrakenOS.UI.validate_layout_plot_controller",
        reason="2D projection/controller contracts without opening a display.",
    ),
    ValidationTarget(
        "open3d-live",
        "KrakenOS.UI.validate_open3d_live_mode",
        reason="Open 3D Live Mode integration by source-level contract checks.",
    ),
    ValidationTarget(
        "open3d-live-budget",
        "KrakenOS.UI.validate_open3d_live_performance_budget",
        reason="Open 3D Live Mode debounce, cancellation, pending-retry, and delay-clamp budgets.",
    ),
    ValidationTarget(
        "open3d-live-transient-step",
        "KrakenOS.UI.validate_open3d_live_transient_step",
        reason="Transient STEP live-trace routing without VTK screenshot capture.",
    ),
    ValidationTarget(
        "open3d-promoted-step-refresh",
        "KrakenOS.UI.validate_open3d_promoted_step_refresh",
        reason="First-open/sync retrace policy for saved row-backed STEP optical solids.",
    ),
    ValidationTarget(
        "open3d-step-state",
        "KrakenOS.UI.validate_open3d_step_state_service",
        reason="STEP selection, carry, delete, and promotion service logic.",
    ),
    ValidationTarget(
        "open3d-toolbar",
        "KrakenOS.UI.validate_open3d_toolbar_layout",
        reason="Toolbar grouping and camera/control layout contract.",
    ),
    ValidationTarget(
        "open3d-thickness-dimensions",
        "KrakenOS.UI.validate_open3d_thickness_dimensions",
        reason="Open 3D table-Thickness edit and drag service contracts without VTK/Tk.",
    ),
    ValidationTarget(
        "open3d-step-face-direction",
        "KrakenOS.UI.validate_open3d_step_face_direction",
        reason="STEP face-direction controls and service boundary contract.",
    ),
    ValidationTarget(
        "open3d-lens-step-face-pick",
        "KrakenOS.UI.validate_open3d_lens_step_face_pick",
        reason="Round achromat-like STEP bodies pick a grouped optical face and do not expose raw STL triangles when selected.",
    ),
    ValidationTarget(
        "five-penta-with-lens-layout",
        "KrakenOS.UI.validate_five_penta_with_lens_layout",
        reason="Saved five-penta cascade with imported lens STEP stays loadable and keeps row-backed optical-solid metadata.",
    ),
    ValidationTarget(
        "widget-commit-bindings",
        "KrakenOS.UI.validate_widget_commit_bindings",
        reason="Reusable Tk entry/combobox commit binding contracts without opening a display.",
    ),
    ValidationTarget(
        "ui-install-metadata",
        "KrakenOS.UI.validate_ui_install_metadata",
        reason="Public kraken-os[ui] optional dependency metadata stays aligned across packaging files.",
    ),
    ValidationTarget(
        "optimization-controls",
        "KrakenOS.UI.validate_optimization_controls",
        reason="Optimization panel uses one stateful Start/Stop button and preflights the backend on start.",
    ),
    ValidationTarget(
        "ui-modular-maintainability",
        "KrakenOS.UI.validate_ui_modular_maintainability",
        reason="Source-structure budgets keep the UI split across coordinator, panels, widgets, services, and validators.",
    ),
    ValidationTarget(
        "row-spec-contracts",
        "KrakenOS.UI.validate_row_spec_contracts",
        reason="Row-spec signatures and scalar-trace decisions live outside layout_editor.py.",
    ),
    ValidationTarget(
        "layout-literals",
        "KrakenOS.UI.validate_layout_literal_contracts",
        reason="Saved-layout literal serialization lives outside layout_editor.py.",
    ),
    ValidationTarget(
        "cadquery-readiness",
        "KrakenOS.UI.validate_cadquery_readiness",
        reason="CAD/STEP service boundaries are clean enough to start the CadQuery/OCP study.",
    ),
    ValidationTarget(
        "cad-scene-cache",
        "KrakenOS.UI.validate_cad_scene_cache",
        reason="Open 3D STEP hover/pick paths reuse cached CAD triangle and face-outline artifacts.",
    ),
    ValidationTarget(
        "open3d-action-timing",
        "KrakenOS.UI.validate_open3d_action_timing",
        reason="Open 3D import, refresh, render, pick, and selection actions emit structured timing diagnostics.",
    ),
    ValidationTarget(
        "open3d-axis-guides",
        "KrakenOS.UI.validate_open3d_optical_axis_guides",
        reason="Centered sequential scenes keep one global optical axis; off-axis scenes keep traced guides.",
    ),
    ValidationTarget(
        "step-carry-lightweight",
        "KrakenOS.UI.validate_step_carry_lightweight",
        reason="No-rebuild STEP carry persistence path.",
    ),
    ValidationTarget(
        "step-overlay-import",
        "KrakenOS.UI.validate_step_overlay_import_service",
        reason="Imported STEP slot/reset state service behavior.",
    ),
    ValidationTarget(
        "lens-drawing-properties",
        "KrakenOS.UI.validate_lens_drawing_properties",
        reason="Fabrication drawing property model without PDF rendering.",
    ),
    ValidationTarget(
        "terminal-bounds",
        "KrakenOS.UI.validate_scene_projection_terminal_bounds",
        reason="Shared 2D/Open 3D terminal ray capping and direction contracts.",
    ),
    ValidationTarget(
        "folded-mirror-projection",
        "KrakenOS.UI.validate_folded_mirror_projection_parity",
        reason="Folded mirror 2D/Open 3D surface geometry parity.",
    ),
    ValidationTarget(
        "folded-scanner-display",
        "KrakenOS.UI.validate_folded_scanner_display_contract",
        reason="Folded galvo/F-theta YZ display keeps rays behind optics and hides unfurled detector footprints.",
    ),
    ValidationTarget(
        "selected-ray-labels",
        "KrakenOS.UI.validate_selected_ray_event_labels",
        reason="Ray event labels and inspector-facing selection records.",
    ),
    ValidationTarget(
        "ray-event-direction-sign",
        "KrakenOS.UI.validate_ray_event_direction_sign",
        reason="RayKeeper event direction sign regression around reflections.",
    ),
    ValidationTarget(
        "nonseq-physics-hardening",
        "KrakenOS.UI.validate_nonseq_physics_hardening",
        reason="Scalar Snell and near-hit tolerance hardening checks.",
    ),
    ValidationTarget(
        "infinity-field-launch",
        "KrakenOS.UI.validate_infinity_field_launch",
        reason="Infinity-object field-angle bundles are stop-centered parallel launches.",
    ),
    ValidationTarget(
        "source-object-split",
        "KrakenOS.UI.validate_source_object_split",
        reason="Source/object scene-entity split contract.",
    ),
    ValidationTarget(
        "scene-source-row-contract",
        "KrakenOS.UI.validate_scene_source_row_contract",
        reason="Scene/source row metadata preservation contract.",
    ),
    ValidationTarget(
        "face-assignment-sampling",
        "KrakenOS.UI.validate_open3d_face_assignment_sampling_stability",
        args=("--focused",),
        reason="Fixture-free Open 3D sampling preservation checks.",
    ),
    ValidationTarget(
        "launch-origin-within-object-aperture",
        "KrakenOS.UI.validate_launch_origin_within_object_aperture",
        reason="Finite-object world-envelope launches must never originate "
        "outside the configured object aperture (North Star #4).",
    ),
)


def _targets_by_alias() -> dict[str, ValidationTarget]:
    return {target.alias: target for target in FAST_TARGETS}


def _selected_targets(aliases: list[str] | None) -> tuple[ValidationTarget, ...]:
    if not aliases:
        return FAST_TARGETS
    lookup = _targets_by_alias()
    unknown = [alias for alias in aliases if alias not in lookup]
    if unknown:
        known = ", ".join(sorted(lookup))
        raise ValueError(f"Unknown validation target(s): {', '.join(unknown)}. Known targets: {known}")
    return tuple(lookup[alias] for alias in aliases)


def _print_target_list() -> None:
    for target in FAST_TARGETS:
        suffix = f" {' '.join(target.args)}" if target.args else ""
        print(f"{target.alias:32} python -m {target.module}{suffix}")
        if target.reason:
            print(f"{'':32} {target.reason}")


def _call_target_main(target: ValidationTarget) -> int:
    module = importlib.import_module(target.module)
    main_func = getattr(module, "main", None)
    if main_func is None:
        raise RuntimeError(f"{target.module} does not expose a main() function.")
    if target.args:
        signature = inspect.signature(main_func)
        if len(signature.parameters) == 0:
            raise RuntimeError(f"{target.module}.main() does not accept arguments: {target.args!r}")
        result = main_func(list(target.args))
    else:
        result = main_func()
    if result is None:
        return 0
    return int(result)


def _run_target_in_process(target: ValidationTarget) -> tuple[bool, float]:
    command_text = f"in-process: python -m {target.module}"
    if target.args:
        command_text = f"{command_text} {' '.join(target.args)}"
    print(f"\n=== {target.alias} ===", flush=True)
    print(command_text, flush=True)
    start = time.perf_counter()
    try:
        return_code = _call_target_main(target)
    except Exception as exc:
        elapsed = time.perf_counter() - start
        print(f"FAIL {target.alias} ({elapsed:.2f}s, {exc.__class__.__name__}: {exc})")
        return False, elapsed
    elapsed = time.perf_counter() - start
    if return_code == 0:
        print(f"PASS {target.alias} ({elapsed:.2f}s)")
        return True, elapsed
    print(f"FAIL {target.alias} ({elapsed:.2f}s, exit {return_code})")
    return False, elapsed


def _run_target_subprocess(target: ValidationTarget) -> tuple[bool, float]:
    command_text = " ".join(target.command)
    print(f"\n=== {target.alias} ===", flush=True)
    print(command_text, flush=True)
    start = time.perf_counter()
    completed = subprocess.run(target.command, cwd=PROJECT_ROOT)
    elapsed = time.perf_counter() - start
    if completed.returncode == 0:
        print(f"PASS {target.alias} ({elapsed:.2f}s)")
        return True, elapsed
    print(f"FAIL {target.alias} ({elapsed:.2f}s, exit {completed.returncode})")
    return False, elapsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the fast, fixture-light Kraken UI validation contracts. "
            "Use the display-backed capture/smoke scripts separately for CAD and screenshot regressions."
        )
    )
    parser.add_argument("--list", action="store_true", help="List fast validation targets without running them.")
    parser.add_argument(
        "--only",
        action="append",
        default=None,
        metavar="ALIAS",
        help="Run only one target alias. Repeat for multiple aliases.",
    )
    parser.add_argument(
        "--subprocess",
        action="store_true",
        help="Run each target in a separate Python process for isolation. Slower, but useful while debugging.",
    )
    args = parser.parse_args(argv)

    if args.list:
        _print_target_list()
        return 0

    try:
        targets = _selected_targets(args.only)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    os.chdir(PROJECT_ROOT)
    failures: list[str] = []
    total_start = time.perf_counter()
    timings: list[tuple[str, float]] = []
    for target in targets:
        if args.subprocess:
            ok, elapsed = _run_target_subprocess(target)
        else:
            ok, elapsed = _run_target_in_process(target)
        timings.append((target.alias, elapsed))
        if not ok:
            failures.append(target.alias)

    total_elapsed = time.perf_counter() - total_start
    print("\n=== Fast Contract Summary ===")
    for alias, elapsed in timings:
        status = "FAIL" if alias in failures else "PASS"
        print(f"{status:4} {alias:32} {elapsed:.2f}s")
    print(f"Total: {total_elapsed:.2f}s")

    if failures:
        print(f"Failed targets: {', '.join(failures)}", file=sys.stderr)
        return 1
    print("Fast UI/non-sequential contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
