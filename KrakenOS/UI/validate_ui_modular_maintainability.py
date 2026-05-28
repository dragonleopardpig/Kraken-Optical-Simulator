"""Validate the UI modular maintainability budget.

This is intentionally source-structure based. It keeps the production-readiness
refactor from regressing back into one oversized Tk file or unvalidated helper
islands.
"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

LINE_BUDGETS = {
    "KrakenOS/UI/layout_editor.py": 3500,
    "KrakenOS/UI/open3d_inspector.py": 9000,
    "KrakenOS/UI/services/layout_table_workbench.py": 6500,
    "KrakenOS/UI/services/layout_scene_projection.py": 3200,
    "KrakenOS/UI/services/optical_solid_workflow.py": 2600,
    "KrakenOS/UI/services/three_d_scene_tools.py": 3000,
}

MIN_MODULE_COUNTS = {
    "KrakenOS/UI/panels": 30,
    "KrakenOS/UI/services": 55,
    "KrakenOS/UI/widgets": 5,
}

REQUIRED_WIDGET_MODULES = (
    "KrakenOS/UI/widgets/commit_bindings.py",
    "KrakenOS/UI/widgets/commit_controls.py",
    "KrakenOS/UI/widgets/menu_controls.py",
    "KrakenOS/UI/widgets/table_cell_editor.py",
    "KrakenOS/UI/widgets/tooltips.py",
)

FAST_CONTRACT_ALIASES = (
    '"ui-install-metadata"',
    '"widget-commit-bindings"',
    '"open3d-toolbar"',
    '"open3d-live-budget"',
    '"open3d-thickness-dimensions"',
    '"open3d-step-face-direction"',
    '"open3d-lens-step-face-pick"',
    '"row-spec-contracts"',
    '"layout-literals"',
    '"cadquery-readiness"',
    '"cad-scene-cache"',
    '"step-native-reconstruction"',
)

REQUIRED_SERVICE_MODULES = (
    "KrakenOS/UI/services/advanced_surface_attrs.py",
    "KrakenOS/UI/services/row_spec_contracts.py",
    "KrakenOS/UI/services/layout_literals.py",
    "KrakenOS/UI/services/cad_cache_paths.py",
    "KrakenOS/UI/services/cad_scene_cache.py",
    "KrakenOS/UI/services/open3d_step_overlay_refresh.py",
    "KrakenOS/UI/services/step_overlay_labels.py",
    "KrakenOS/UI/services/step_native_reconstruction.py",
)


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _python_module_count(path: Path) -> int:
    return sum(1 for child in path.glob("*.py") if child.name != "__init__.py")


def main() -> int:
    failures: list[str] = []

    for relative, budget in LINE_BUDGETS.items():
        count = _line_count(PROJECT_ROOT / relative)
        if count > budget:
            failures.append(f"{relative} has {count} lines; budget is {budget}")

    for relative, minimum in MIN_MODULE_COUNTS.items():
        count = _python_module_count(PROJECT_ROOT / relative)
        if count < minimum:
            failures.append(f"{relative} has {count} modules; expected at least {minimum}")

    for relative in REQUIRED_WIDGET_MODULES:
        if not (PROJECT_ROOT / relative).is_file():
            failures.append(f"Missing required reusable widget module: {relative}")

    for relative in REQUIRED_SERVICE_MODULES:
        if not (PROJECT_ROOT / relative).is_file():
            failures.append(f"Missing required service contract module: {relative}")

    layout_source = (PROJECT_ROOT / "KrakenOS/UI/layout_editor.py").read_text(encoding="utf-8")
    if "class Kraken3DInspector" in layout_source:
        failures.append("Kraken3DInspector implementation must stay outside layout_editor.py")
    if "apply_modern_ttk_theme(self)" not in layout_source:
        failures.append("layout_editor.py must keep the dormant ttk theme adapter hook")

    theme_source = (PROJECT_ROOT / "KrakenOS/UI/modern_ttk_theme.py").read_text(encoding="utf-8")
    if 'os.getenv("KRAKEN_UI_TTK_THEME", "native")' not in theme_source:
        failures.append("ttk theme adapter must default to native/no-op until the final polish milestone")

    fast_contracts_source = (PROJECT_ROOT / "KrakenOS/UI/validate_fast_contracts.py").read_text(encoding="utf-8")
    for alias in FAST_CONTRACT_ALIASES:
        if alias not in fast_contracts_source:
            failures.append(f"Fast contract runner is missing {alias}")

    if failures:
        print("UI modular maintainability validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("UI modular maintainability validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
