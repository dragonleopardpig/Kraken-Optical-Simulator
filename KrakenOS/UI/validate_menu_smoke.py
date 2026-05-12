from __future__ import annotations

import argparse
import contextlib
import io
import json
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import (
    EXAMPLES_DIR,
    LAYOUTS_DIR,
    ZEMAX_TESTING_DIR,
    KrakenLayoutEditor,
    SurfaceRow,
    _available_testing_zemax_prescriptions,
    _build_system_from_specs,
    _load_python_data,
    _load_python_title,
    _load_zemax_zmx_data,
)
from KrakenOS.UI.layout_library import python_code_defines_layout_data
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.scene_projector import SceneProjector2D
from KrakenOS.UI.scene_renderer_2d import render_scene_2d, set_plot_limits

warnings.filterwarnings("ignore", message="The default value of `algorithm`.*", category=Warning)
warnings.filterwarnings("ignore", message=".*extract_surface.*", category=Warning)
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=matplotlib.MatplotlibDeprecationWarning)


@dataclass(frozen=True)
class MenuSmokeItem:
    menu: str
    label: str
    path: str


@dataclass
class MenuSmokeCheck:
    menu: str
    label: str
    ok: bool
    detail: str


_EXAMPLE_CAPTURE_EDITOR = KrakenLayoutEditor.__new__(KrakenLayoutEditor)


def _layout_menu_items() -> list[MenuSmokeItem]:
    items: list[MenuSmokeItem] = []
    for path in sorted(LAYOUTS_DIR.glob("*.py")):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        try:
            title = _load_python_title(path)
        except Exception:
            continue
        menu = "Machine Vision" if path.stem.startswith("machine_vision_") else "Layouts"
        items.append(MenuSmokeItem(menu, title, str(path)))
    return sorted(items, key=lambda item: (item.menu != "Layouts", item.label.lower()))


def _example_menu_items() -> list[MenuSmokeItem]:
    items: list[MenuSmokeItem] = []
    for path in sorted(EXAMPLES_DIR.glob("*.py")):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        if not KrakenLayoutEditor._example_file_is_menu_loadable(path):
            continue
        items.append(MenuSmokeItem("Examples", path.stem, str(path)))
    return items


def _zemax_menu_items() -> list[MenuSmokeItem]:
    return [
        MenuSmokeItem("Examples/Zemax", label, str(path))
        for label, path in sorted(_available_testing_zemax_prescriptions().items(), key=lambda item: item[0].lower())
    ]


def menu_smoke_items(*, include_zemax: bool = False) -> list[MenuSmokeItem]:
    items = [*_layout_menu_items(), *_example_menu_items()]
    if include_zemax:
        items.extend(_zemax_menu_items())
    return items


def _load_layout_rows(path: Path) -> tuple[list[SurfaceRow], dict[str, object]]:
    info = _load_python_data(path)
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
    rows = KrakenLayoutEditor._normalized_rows_copy(rows)
    KrakenLayoutEditor._auto_assign_missing_elements(rows)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    return rows, dict(settings)


def _load_example_rows(path: Path) -> tuple[list[SurfaceRow], dict[str, object]]:
    code = path.read_text(encoding="utf-8", errors="ignore")
    if python_code_defines_layout_data(code):
        return _load_layout_rows(path)
    surfaces = _EXAMPLE_CAPTURE_EDITOR._extract_surfaces_from_example(path)
    rows = [
        KrakenLayoutEditor._row_from_surface(surface, index, len(surfaces))
        for index, surface in enumerate(surfaces)
    ]
    rows = KrakenLayoutEditor._normalized_rows_copy(rows)
    KrakenLayoutEditor._auto_assign_missing_elements(rows)
    settings: dict[str, object] = {}
    if KrakenLayoutEditor._example_requests_nonsequential(code):
        settings["trace_mode"] = "Non-Sequential Preview"
    return rows, settings


def _load_zemax_rows(path: Path) -> tuple[list[SurfaceRow], dict[str, object]]:
    info = _load_zemax_zmx_data(path)
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
    rows = KrakenLayoutEditor._normalized_rows_copy(rows)
    KrakenLayoutEditor._auto_assign_missing_elements(rows)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    return rows, dict(settings)


def _load_menu_item(item: MenuSmokeItem) -> tuple[list[SurfaceRow], dict[str, object]]:
    path = Path(item.path)
    if item.menu in {"Layouts", "Machine Vision"}:
        return _load_layout_rows(path)
    if item.menu == "Examples":
        return _load_example_rows(path)
    if item.menu == "Examples/Zemax":
        return _load_zemax_rows(path)
    raise ValueError(f"Unsupported menu kind: {item.menu}")


def _max_radius(rows: list[SurfaceRow]) -> float:
    return max((max(float(row.diameter) / 2.0, 0.5) for row in rows), default=1.0)


def _render_2d(editor: KrakenLayoutEditor, system, rays, max_radius: float) -> int:
    bundle = editor._last_scene_bundle
    if bundle is None:
        bundle = editor._build_scene_bundle(system, rays, max_radius)
        editor._last_scene_bundle = bundle
    projected = SceneProjector2D(editor._current_display_orientation()).project_bundle(bundle)
    editor._refresh_auto_leg_graph(projected)
    projected = editor._filter_projected_scene_for_arm_view(projected)
    projected = editor._filter_projected_scene_for_ray_display(projected)
    fig = plt.figure(figsize=(8, 4.5))
    try:
        ax = fig.add_subplot(111)
        editor.figure = fig
        editor.ax = ax
        render_projected = editor._projected_scene_for_layout_render(projected)
        render_scene_2d(
            render_projected,
            ax,
            show_clipped_rays=bool(editor.show_clipped_rays_var.get()),
            show_labels=bool(editor._current_show_path_labels()),
            ray_count_hint=max(1, int(editor._preview_field_ray_count)),
        )
        scan_bounds = editor._draw_folded_scan_overlay(max_radius, system=system)
        tolerance_bounds = editor._draw_pose_tolerance_overlay(max_radius, wavelength=float(editor._current_wavelength()))
        plot_bounds = editor._combined_plot_bounds(projected.bounds, scan_bounds, tolerance_bounds)
        set_plot_limits(
            ax,
            plot_bounds,
            max_radius=max_radius,
            has_off_axis=bundle.has_off_axis,
            orientation=editor._current_display_orientation(),
            use_drawn_data=not scan_bounds.is_empty or not tolerance_bounds.is_empty,
        )
        editor._draw_arm_labels(projected)
        fig.canvas.draw()
        return len(ax.lines) + len(ax.collections) + len(ax.patches) + len(ax.texts)
    finally:
        plt.close(fig)


def _actor_count(plotter) -> int:
    try:
        return int(plotter.renderer.GetActors().GetNumberOfItems())
    except Exception:
        return 0


def _ray_count(rays) -> int:
    try:
        return len(getattr(rays, "CC", []) or [])
    except Exception:
        try:
            return len(getattr(rays, "SURFACE", []) or [])
        except Exception:
            return 0


def _smoke_one(item: MenuSmokeItem, *, check_3d: bool = True) -> MenuSmokeCheck:
    rows, settings = _load_menu_item(item)
    if len(rows) < 2:
        return MenuSmokeCheck(item.menu, item.label, False, f"loaded {len(rows)} row(s)")
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = Path(item.path)
    editor._normalize_special_rows()
    rows = editor.rows
    max_radius = _max_radius(rows)
    system = _build_system_from_specs(
        editor._serializable_specs_for_rows(rows),
        build=1 if KrakenLayoutEditor._rows_require_geometry_build(rows) else 0,
    )
    wavelength = float(editor._current_wavelength())
    rays = Kos.raykeeper(system)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    editor.last_system = system
    editor.last_rays = rays
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    editor._last_scene_bundle = editor._build_scene_bundle(system, rays, max_radius)
    artists = _render_2d(editor, system, rays, max_radius)
    if artists <= 0:
        return MenuSmokeCheck(item.menu, item.label, False, "2D render produced no visible artists")
    actor_count = 0
    if check_3d:
        plotter = None
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                plotter = editor._build_clean_legacy_3d_plotter(system, rays)
            actor_count = _actor_count(plotter)
        finally:
            if plotter is not None:
                try:
                    plotter.close()
                except Exception:
                    pass
        if actor_count <= 0:
            return MenuSmokeCheck(item.menu, item.label, False, f"3D render produced no actors; 2D artists={artists}")
    ray_count = _ray_count(rays)
    return MenuSmokeCheck(
        item.menu,
        item.label,
        True,
        f"rows={len(rows)}, rays={ray_count}, 2D_artists={artists}, 3D_actors={actor_count if check_3d else 'skipped'}",
    )


def validate_menu_smoke(
    *,
    include_zemax: bool = False,
    check_3d: bool = True,
    limit: int | None = None,
) -> list[MenuSmokeCheck]:
    checks: list[MenuSmokeCheck] = []
    items = menu_smoke_items(include_zemax=include_zemax)
    if limit is not None:
        items = items[: max(0, int(limit))]
    for item in items:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                checks.append(_smoke_one(item, check_3d=check_3d))
        except Exception as exc:
            checks.append(MenuSmokeCheck(item.menu, item.label, False, str(exc)))
    return checks


def _print_table(checks: list[MenuSmokeCheck]) -> None:
    print("KrakenOS UI menu smoke validation")
    print("menu | label | status | detail")
    print("--- | --- | --- | ---")
    for check in checks:
        print(f"{check.menu} | {check.label} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Headless smoke-test menu-backed Layouts, Machine Vision layouts, and Examples in 2D and offscreen 3D."
    )
    parser.add_argument("--include-zemax", action="store_true", help=f"Also test .zmx files under {ZEMAX_TESTING_DIR}.")
    parser.add_argument("--no-3d", action="store_true", help="Only test load and 2D rendering.")
    parser.add_argument("--limit", type=int, default=None, help="Only test the first N menu items.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_menu_smoke(
        include_zemax=bool(args.include_zemax),
        check_3d=not bool(args.no_3d),
        limit=args.limit,
    )
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if checks and all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
