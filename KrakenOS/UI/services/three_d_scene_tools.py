"""3D scene preview, legacy PyVista plotter, and Open 3D bridge helpers.

This mixin owns the editor-facing 3D scene/display coordination that still
belongs to the main window rather than the embedded Open 3D inspector widget.
It keeps 3D mesh/ray geometry helpers available on ``KrakenLayoutEditor`` while
moving the bulky legacy plotter and shared 3D display logic out of
``layout_editor.py``.
"""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import tkinter as tk
from tkinter import filedialog
import warnings

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.scene_geometry import (
    SceneBundle,
    SceneTarget3D,
    SurfaceMesh3D,
    ray_path_reaches_image_from_events,
    ray_path_terminal_event,
    ray_path_terminal_metadata,
    ray_path_terminal_status_from_events,
    ray_path_visible_without_clipping_from_events,
    scene_target_active_footprint_polylines,
    scene_target_detector_miss_crosshair_polylines,
)
from KrakenOS.UI.scene_projector import (
    bounded_ray_points_for_scene_display,
    detector_planes_for_hard_stop,
    normalize_projection_plane,
    scene_display_center_radius,
)
from KrakenOS.UI.layout_plot_controller import (
    preview_trace_signature_matches,
    scene_bundle_launch_sampling_mode,
)
from KrakenOS.UI.nonseq_output_ports import (
    optical_solid_output_port_pose_overrides,
    optical_solid_output_port_runtime_transform_override,
)
from KrakenOS.UI.services.best_focus_surface import (
    best_focus_surface_faces,
    best_focus_surface_ring_polylines,
    build_best_focus_surface,
)
from KrakenOS.UI.services.distortion_grid import build_distortion_grid
from KrakenOS.UI.services.spot_field_map import build_spot_field_map
from KrakenOS.UI.services.legacy_3d_scene import Legacy3DSceneService
from KrakenOS.UI.services.missing_assets_scan import (
    MISSING_RESOURCE_STATE_ATTR,
)


def _row_has_skipped_missing_asset(advanced: dict) -> bool:
    """Return True if the row's advanced dict carries a non-empty skip list.

    Mirrors :func:`row_has_missing_resource` from the scanner module but
    reads the ``advanced`` dict that's already in scope at the call
    site, so we don't pay an attribute lookup per row per refresh.
    """
    state = advanced.get(MISSING_RESOURCE_STATE_ATTR)
    if not isinstance(state, dict):
        return False
    keys = state.get("keys")
    return bool(keys) if isinstance(keys, (list, tuple, set, frozenset)) else False
from KrakenOS.UI.services.open3d_step_state import Open3DStepStateService
from KrakenOS.UI.services.open3d_timing import open3d_timing_event, open3d_timing_span
from KrakenOS.UI.services.open3d_trace_refresh import Open3DTraceRefreshService
from KrakenOS.UI.services.offbeam_optical_solid import offbeam_neutralized_body_transform
from KrakenOS.UI.services.optical_solid_geometry import (
    _read_stl_triangle_vertices,
    _rotation_matrix_from_kraken_tilts,
)
from KrakenOS.UI.services.row_spec_contracts import _row_specs_signature
from KrakenOS.UI.services.step_overlay_labels import STEP_OVERLAY_LABELS, STEP_OVERLAY_LABEL_SET
from KrakenOS.UI.surface_table_model import SurfaceRow, surface_row_to_spec

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCREENSHOT_DIR = PROJECT_ROOT / "attachment"

# Each drawn ray is its own pickable VTK actor, so the 3D draw thins large
# bundles to a budget. The default keeps interaction snappy; the launch cone is
# the single 3D-truth pupil (bug 0041, North Star invariant #2 -- the 2D layout
# is its meridional slice) and gets a much larger budget so the full-ring cone
# (count//2 rings x az spokes per field/wavelength, e.g. 1809 rays for the
# Double Gauss 28 deg grid) draws IN FULL. Decimating it would thin the cone back
# into the uneven azimuthal spokes that read as crossing flat fans (bug 0040).
# The cone only exists while the Open 3D inspector is live (lazy trace), so the
# extra pickable actors are bounded to that window.
_RAY_DRAW_BUDGET_DEFAULT = 300
_RAY_DRAW_BUDGET_CONE = 2000

# A cemented bond / optical-contact layer (e.g. the 7.5 um "___BLANK" cement in a
# crown+flint doublet) is a real glass volume, but only microns thick. KrakenOS
# builds one BBB solid per glass-bearing surface, so that bond becomes a
# full-aperture standalone slab stacked between its neighbours -- it reads as a
# duplicated element in 3D (bugs/0046) while the 2D meridional slice collapses it
# to a sub-pixel hairline. A glass layer this thin is never a free-standing
# mechanical element, so its body is drawn invisibly (the cement optical surface
# still lives in AAA, so ray tracing is untouched). Real elements -- even thin
# field flatteners -- have centre thickness far above this; cement bonds sit at
# 5-25 um, so 50 um cleanly separates the two.
_CEMENT_LAYER_MAX_AXIAL_THICKNESS_MM = 0.05

pv = None
vtkTkRenderWindowInteractor = None
vtkCellPicker = None


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


def _load_3d_backends() -> None:
    _sync_3d_backend_globals(load=True)


def _sync_3d_backend_globals(*, load: bool = False) -> None:
    global pv, vtkTkRenderWindowInteractor, vtkCellPicker
    layout_editor_module = _layout_module()
    if load:
        layout_editor_module._load_3d_backends()
    pv = layout_editor_module.pv
    vtkTkRenderWindowInteractor = layout_editor_module.vtkTkRenderWindowInteractor
    vtkCellPicker = layout_editor_module.vtkCellPicker


def _ensure_pv() -> None:
    if pv is None:
        _sync_3d_backend_globals(load=True)


def _short_error_message(exc: Exception, limit: int = 220) -> str:
    return _layout_module()._short_error_message(exc, limit=limit)


def _wavelength_to_rgb(wavelength_nm: float) -> tuple[float, float, float]:
    return _layout_module()._wavelength_to_rgb(wavelength_nm)


def _color_to_rgb_tuple(color: object) -> tuple[float, float, float]:
    return _layout_module()._color_to_rgb_tuple(color)


class ThreeDSceneToolsMixin:
    def open_3d_view(self) -> None:
        try:
            _load_3d_backends()
            if vtkTkRenderWindowInteractor is not None:
                try:
                    if self._three_d_inspector is None or not self._three_d_inspector.winfo_exists():
                        self._three_d_inspector = Kraken3DInspector(self)
                    if self._three_d_inspector.available:
                        self._three_d_inspector.deiconify()
                        self._three_d_inspector.lift()
                        self._three_d_inspector.focus_force()
                        if self._start_open3d_step_cache_warmup(self._three_d_inspector):
                            return
                        self._three_d_inspector.refresh_from_editor()
                        self.status_var.set("Opened Kraken 3D inspector")
                        self.append_debug("Opened Kraken 3D inspector")
                        return
                    reason = self._three_d_inspector.unavailable_reason or "VTK/Tk unavailable"
                    try:
                        self._three_d_inspector.destroy()
                    except Exception:
                        pass
                    self._three_d_inspector = None
                    self.append_debug(f"Embedded 3D inspector unavailable: {reason}. Falling back to legacy PyVista viewer.")
                except Exception as exc:
                    self.append_debug(f"Embedded 3D inspector failed: {exc}. Falling back to legacy PyVista viewer.")
                    if self._three_d_inspector is not None:
                        try:
                            self._three_d_inspector.destroy()
                        except Exception:
                            pass
                        self._three_d_inspector = None

            self._close_legacy_3d_plotter()
            current = self._current_preview_scene_trace()
            if current is not None:
                system, rays, scene_bundle = current
            else:
                system, rays, scene_bundle = self._build_preview_system_rays_bundle(
                    sampling_mode=self._preview_2d_sampling_mode(),
                    update_state=False,
                )
            plotter = self._build_legacy_3d_plotter(system, rays, scene_bundle=scene_bundle)
            plotter.show(auto_close=False, interactive=True, interactive_update=True)
            self._legacy_3d_plotter = plotter
            self._schedule_legacy_3d_poll()
            self.status_var.set("Opened legacy Kraken 3D view")
            self.append_debug("Opened legacy Kraken 3D view")
        except Exception as exc:
            self.append_debug(f"3D view error: {exc}")
            self.status_var.set(f"3D view failed: {exc}")

    def _open3d_step_cache_warmup_specs(self) -> list[tuple[str, Path, bool]]:
        specs: list[tuple[str, Path, bool]] = []
        for label, attr, largest in (
            ("lens", "imported_lens_step_path", bool(getattr(self, "lens_step_largest_component_only", True))),
            ("camera", "imported_camera_step_path", False),
            ("optical", "imported_optical_step_path", False),
            ("led", "imported_led_step_path", False),
        ):
            path = getattr(self, attr, None)
            if path is None:
                continue
            try:
                source_path = Path(path).expanduser()
            except Exception:
                continue
            if source_path.suffix.lower() not in {".step", ".stp"} or not source_path.exists():
                continue
            if self._open3d_step_display_cache_ready(label, source_path, largest_component=bool(largest)):
                continue
            specs.append((label, source_path, bool(largest)))
        return specs

    def _open3d_step_display_cache_ready(self, label: str, source_path: Path, *, largest_component: bool) -> bool:
        try:
            from KrakenOS.UI.services.layout_polyline_display import (
                _cached_analytic_cad_mesh_path,
                _cached_step_axis_path,
            )

            mesh_cache = _cached_analytic_cad_mesh_path(
                Path(source_path),
                largest_component=bool(largest_component),
            )
            if not mesh_cache.exists() or mesh_cache.stat().st_size <= 0:
                return False
            if str(label or "").strip().lower() == "lens":
                axis_cache = _cached_step_axis_path(Path(source_path))
                if not axis_cache.exists() or axis_cache.stat().st_size <= 0:
                    return False
            return True
        except Exception:
            return False

    def _start_open3d_step_cache_warmup(self, inspector) -> bool:
        specs = self._open3d_step_cache_warmup_specs()
        if not specs:
            return False
        process = getattr(self, "_open3d_step_cache_warmup_process", None)
        if process is not None and process.poll() is None:
            try:
                inspector.status_var.set("Open 3D is warming STEP display cache...")
                self.status_var.set("Open 3D is warming STEP display cache...")
            except Exception:
                pass
            return True
        if bool(getattr(self, "_open3d_step_cache_warmup_pending", False)):
            try:
                inspector.status_var.set("Open 3D is preparing STEP display cache warm-up...")
                self.status_var.set("Open 3D is preparing STEP display cache warm-up...")
            except Exception:
                pass
            return True

        names = ", ".join(f"{label}:{path.name}" for label, path, _largest in specs)
        try:
            inspector.status_var.set(f"Open 3D warming STEP display cache outside the UI process: {names}")
            self.status_var.set(f"Open 3D warming STEP display cache outside the UI process: {names}")
            self.update_idletasks()
        except Exception:
            pass
        self._open3d_step_cache_warmup_pending = True
        try:
            self.after(50, lambda: self._launch_open3d_step_cache_warmup(inspector, specs, names))
        except Exception:
            self._launch_open3d_step_cache_warmup(inspector, specs, names)
        return True

    def _launch_open3d_step_cache_warmup(self, inspector, specs: list[tuple[str, Path, bool]], names: str) -> None:
        self._open3d_step_cache_warmup_pending = False
        process = getattr(self, "_open3d_step_cache_warmup_process", None)
        if process is not None and process.poll() is None:
            return
        command = [
            sys.executable,
            "-m",
            "KrakenOS.UI.warm_open3d_step_cache",
        ]
        for label, path, largest in specs:
            command.extend(
                (
                    "--spec",
                    json.dumps(
                        {
                            "label": str(label),
                            "path": str(path),
                            "largest_component": bool(largest),
                            "warm_axis": str(label).strip().lower() == "lens",
                        },
                        separators=(",", ":"),
                    ),
                )
            )
        try:
            process = subprocess.Popen(
                command,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as exc:
            self.append_debug(f"Open 3D STEP cache subprocess failed to start: {exc}")
            return
        self._open3d_step_cache_warmup_process = process
        self._open3d_step_cache_warmup_started = time.perf_counter()
        self._poll_open3d_step_cache_warmup(inspector, names)

    def _poll_open3d_step_cache_warmup(self, inspector, names: str) -> None:
        process = getattr(self, "_open3d_step_cache_warmup_process", None)
        if process is None:
            return
        started = float(getattr(self, "_open3d_step_cache_warmup_started", time.perf_counter()))
        if process.poll() is None:
            elapsed = time.perf_counter() - started
            status = f"Open 3D warming STEP display cache outside the UI process ({elapsed:.1f}s): {names}"
            try:
                inspector.status_var.set(status)
                self.status_var.set(status)
            except Exception:
                pass
            try:
                self.after(250, lambda: self._poll_open3d_step_cache_warmup(inspector, names))
            except Exception:
                pass
            return
        try:
            stdout, stderr = process.communicate(timeout=0.1)
        except Exception:
            stdout, stderr = "", ""
        self._open3d_step_cache_warmup_process = None
        elapsed = time.perf_counter() - started
        if stderr.strip():
            self.append_debug("Open 3D STEP cache warm-up stderr: " + stderr.strip()[-1200:])
        summary = self._open3d_step_cache_warmup_summary(stdout)
        ok = process.returncode == 0 and bool(summary.get("ok", False))
        if ok:
            count = len(summary.get("results", []) or [])
            status = f"Open 3D STEP cache warm-up completed in {elapsed:.1f}s ({count} file(s))."
        else:
            status = f"Open 3D STEP cache warm-up completed with warnings in {elapsed:.1f}s."
            errors = list(summary.get("errors", []) or [])
            if errors:
                self.append_debug("Open 3D STEP cache warm-up warnings: " + "; ".join(str(error) for error in errors))
        try:
            inspector.status_var.set(status)
            self.status_var.set(status)
            if inspector.winfo_exists() and bool(getattr(inspector, "available", False)):
                inspector.refresh_from_editor()
                self.status_var.set("Opened Kraken 3D inspector")
                self.append_debug("Opened Kraken 3D inspector after STEP cache warm-up")
        except Exception as exc:
            self.append_debug(f"Open 3D refresh after STEP cache warm-up failed: {exc}")

    @staticmethod
    def _open3d_step_cache_warmup_summary(stdout: str) -> dict[str, object]:
        for line in reversed(str(stdout or "").splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except Exception:
                continue
            if isinstance(value, dict):
                return value
        return {"ok": False, "errors": ["warm-up subprocess produced no JSON summary"]}

    def _schedule_legacy_3d_poll(self) -> None:
        if self._legacy_3d_after_id is not None:
            return
        try:
            self._legacy_3d_after_id = self.after(20, self._poll_legacy_3d_plotter)
        except Exception:
            self._legacy_3d_after_id = None

    def _poll_legacy_3d_plotter(self) -> None:
        self._legacy_3d_after_id = None
        plotter = self._legacy_3d_plotter
        if plotter is None:
            return
        if bool(getattr(plotter, "_closed", False)):
            self._legacy_3d_plotter = None
            self.status_var.set("Closed legacy Kraken 3D view")
            return
        try:
            plotter.update(stime=1, force_redraw=True)
        except Exception as exc:
            self.append_debug(f"Legacy 3D update failed: {exc}")
            self._close_legacy_3d_plotter()
            self.status_var.set(f"3D view closed: {_short_error_message(exc)}")
            return
        self._schedule_legacy_3d_poll()

    def _close_legacy_3d_plotter(self) -> None:
        if self._legacy_3d_after_id is not None:
            try:
                self.after_cancel(self._legacy_3d_after_id)
            except Exception:
                pass
            self._legacy_3d_after_id = None
        plotter = self._legacy_3d_plotter
        self._legacy_3d_plotter = None
        if plotter is None:
            return
        stl_placement_dirty = bool(getattr(plotter, "_kraken_stl_placement_dirty", False))
        # VTK's GLX teardown segfaults on Wayland / XWayland, so hide the
        # window and detach references instead of calling plotter.close().
        try:
            iren = getattr(plotter, "iren", None)
            if iren is not None:
                iren.terminate_app()
        except Exception:
            pass
        try:
            rw = getattr(plotter, "render_window", None)
            if rw is not None:
                rw.SetShowWindow(False)
        except Exception:
            pass
        if stl_placement_dirty:
            def refresh_2d_after_legacy_close() -> None:
                try:
                    self.refresh_plot(suppress_analysis=True)
                except Exception as exc:
                    self.status_var.set(f"CAD/STL placement saved; 2D refresh failed: {_short_error_message(exc)}")
                    self.append_debug(f"Legacy CAD/STL placement close refresh failed: {exc}")

            try:
                self.after(50, refresh_2d_after_legacy_close)
                self.status_var.set("Legacy 3D CAD/STL placement closed; refreshing 2D layout.")
            except Exception as exc:
                self.append_debug(f"Legacy CAD/STL placement close refresh failed: {exc}")

    def _build_preview_system_rays_bundle(
        self,
        *,
        sampling_mode: str | None = None,
        update_state: bool = True,
        include_live_step_overlays: bool = False,
    ):
        preview_start = time.perf_counter()
        wavelength = self._current_wavelength()
        capture = io.StringIO()
        active_rows = self.rows
        live_step_records: list[dict[str, object]] = []
        status = "ok"
        mode = sampling_mode
        open3d_timing_event(
            "preview_system_rays_bundle_start",
            sampling_mode=str(sampling_mode or ""),
            update_state=bool(update_state),
            include_live_step_overlays=bool(include_live_step_overlays),
            row_count=len(self.rows),
        )
        original_rows: list[SurfaceRow] | None = None
        scene_bundle = None
        saved_native_records: list[dict[str, object]] = []
        try:
            if include_live_step_overlays:
                with open3d_timing_span(
                    "preview_live_step_overlay_rows",
                    row_count=len(self.rows),
                ):
                    active_rows, live_step_records = self._live_step_overlay_trace_rows()
            else:
                self._last_live_step_overlay_trace_rows = None
                self._last_live_step_overlay_trace_records = []
                self._last_live_step_overlay_scene_bundle = None
            with open3d_timing_span(
                "preview_saved_step_native_rows",
                row_count=len(active_rows),
            ):
                active_rows, saved_native_records = self._saved_promoted_step_native_trace_rows(active_rows)
            if active_rows is not self.rows:
                original_rows = self.rows
                self.rows = active_rows
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                with redirect_stdout(capture), redirect_stderr(capture):
                    with open3d_timing_span(
                        "preview_build_system",
                        row_count=len(self.rows),
                        require_solids=True,
                        force_rebuild=bool(live_step_records or saved_native_records),
                        live_step_records=len(live_step_records),
                        saved_native_records=len(saved_native_records),
                    ):
                        system = self.build_system(
                            require_solids=True,
                            force_rebuild=bool(live_step_records or saved_native_records),
                        )
                    rays = Kos.raykeeper(system)
                    max_radius = max((max(row.diameter / 2.0, 0.5) for row in self.rows), default=1.0)
                    if mode is None:
                        mode = self._preview_scene_sampling_mode()
                    with open3d_timing_span(
                        "preview_trace_rays",
                        sampling_mode=str(mode or ""),
                        row_count=len(self.rows),
                        wavelength_um=float(wavelength),
                    ):
                        self._trace_preview_rays(
                            system,
                            rays,
                            wavelength,
                            max_radius,
                            sampling_mode=mode,
                        )
            ray_path_count = len(getattr(rays, "CC", []) or [])
            with open3d_timing_span(
                "preview_build_scene_bundle",
                sampling_mode=str(mode or ""),
                row_count=len(self.rows),
                ray_path_count=int(ray_path_count),
            ):
                scene_bundle = self._build_scene_bundle(system, rays, max_radius)
            if include_live_step_overlays:
                self._last_live_step_overlay_trace_rows = list(self.rows)
                self._last_live_step_overlay_trace_records = list(live_step_records)
                self._last_live_step_overlay_scene_bundle = scene_bundle
            if saved_native_records:
                self._last_saved_step_native_trace_rows = list(self.rows)
                self._last_saved_step_native_trace_records = list(saved_native_records)
                self._last_saved_step_native_scene_bundle = scene_bundle
            else:
                self._last_saved_step_native_trace_rows = None
                self._last_saved_step_native_trace_records = []
                self._last_saved_step_native_scene_bundle = None
        except Exception:
            status = "error"
            raise
        finally:
            if original_rows is not None:
                self.rows = original_rows
            open3d_timing_event(
                "preview_system_rays_bundle_done",
                duration_ms=round(float((time.perf_counter() - preview_start) * 1000.0), 3),
                status=status,
                sampling_mode=str(mode or sampling_mode or ""),
                update_state=bool(update_state),
                include_live_step_overlays=bool(include_live_step_overlays),
                live_step_records=len(live_step_records),
                saved_native_records=len(saved_native_records),
                ray_path_count=len(getattr(locals().get("rays", None), "CC", []) or []),
            )
        self.append_debug(capture.getvalue())
        if update_state and not include_live_step_overlays:
            self.last_system = system
            self.last_rays = rays
            self._last_preview_trace_signature = self._preview_trace_signature()
            self._last_scene_bundle = scene_bundle
            self._last_scene_trace_sampling_mode = mode
            self._preview_scene_trace_dirty = False
        return system, rays, scene_bundle

    @staticmethod
    def _saved_step_source_path_for_row(row: SurfaceRow) -> Path | None:
        advanced = row.advanced if isinstance(getattr(row, "advanced", None), dict) else {}
        source = str(advanced.get("OpticalSolidSourcePath", "") or "").strip()
        if not source:
            promotion = advanced.get("StepOverlayPromotion", {})
            if isinstance(promotion, dict):
                source = str(promotion.get("source_step_path", "") or "").strip()
        if not source:
            return None
        try:
            path = Path(source).expanduser()
        except Exception:
            return None
        if path.suffix.lower() not in {".step", ".stp"}:
            return None
        return path

    @staticmethod
    def _step_source_key(value: object) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        try:
            return str(Path(text).expanduser().resolve())
        except Exception:
            try:
                return str(Path(text).expanduser())
            except Exception:
                return text

    def _promoted_step_source_keys_for_rows(self, rows: list[SurfaceRow] | None = None) -> set[str]:
        keys: set[str] = set()
        for row in list(rows if rows is not None else self.rows):
            advanced = row.advanced if isinstance(getattr(row, "advanced", None), dict) else {}
            candidates: list[object] = [advanced.get("OpticalSolidSourcePath")]
            promotion = advanced.get("StepOverlayPromotion")
            if isinstance(promotion, dict):
                candidates.append(promotion.get("source_step_path"))
            placement = advanced.get("ScenePlacement")
            if isinstance(placement, dict):
                candidates.append(placement.get("promotion_source_step_path"))
            for candidate in candidates:
                key = self._step_source_key(candidate)
                if key:
                    keys.add(key)
        return keys

    def _step_overlay_matches_promoted_row(
        self,
        label: str,
        promoted_source_keys: set[str] | None = None,
    ) -> bool:
        source_path = self._step_path_for_label(str(label or "").strip().lower())
        key = self._step_source_key(source_path)
        if not key:
            return False
        keys = promoted_source_keys if promoted_source_keys is not None else self._promoted_step_source_keys_for_rows()
        return key in keys

    @staticmethod
    def _saved_step_native_center_world(row: SurfaceRow, z_station: float) -> np.ndarray:
        # bugs/0012: the world centre of a promoted optical-solid row follows its
        # *live* row pose -- world (x, y, z) = (desp_x, desp_y, z_station + desp_z).
        # ``StepOverlayPromotion.center_world`` is only the promotion-time snapshot
        # of that (the two are equal at promotion: e.g. desp_z=-87.5, z_station=100,
        # center_world.z=12.5). Returning the cached snapshot froze the body, so
        # dragging the placement Move handle updated desp / the gap overlay but the
        # body never moved -- it reverted to the cached centre on release. Use the
        # live pose (which is this function's own historical fallback); fall back
        # to the cache only if the live pose is unusable.
        live = np.asarray(
            (
                float(getattr(row, "desp_x", 0.0) or 0.0),
                float(getattr(row, "desp_y", 0.0) or 0.0),
                float(z_station) + float(getattr(row, "desp_z", 0.0) or 0.0),
            ),
            dtype=float,
        )
        if np.all(np.isfinite(live)):
            return live
        advanced = row.advanced if isinstance(getattr(row, "advanced", None), dict) else {}
        promotion = advanced.get("StepOverlayPromotion", {})
        if isinstance(promotion, dict):
            try:
                center = np.asarray(promotion.get("center_world", ()), dtype=float).reshape(-1)[:3]
            except Exception:
                center = np.asarray([], dtype=float)
            if center.size >= 3 and np.all(np.isfinite(center[:3])):
                return center[:3]
        return live

    @staticmethod
    def _native_reconstruction_center_z(reconstruction) -> float:
        try:
            z_values = sorted(
                float(fit.vertex_z_mm)
                for fit in list(getattr(reconstruction, "surface_fits", ()) or ())
                if np.isfinite(float(fit.vertex_z_mm))
            )
        except Exception:
            z_values = []
        if not z_values:
            return 0.0
        return 0.5 * max(float(z_values[-1] - z_values[0]), 0.0)

    @staticmethod
    def _saved_step_native_material_sequence(row: SurfaceRow, surface_count: int) -> tuple[str, ...]:
        count = max(int(surface_count), 0)
        if count <= 0:
            return ()
        material = str(getattr(row, "glass", "") or "").strip().upper()
        if not material or material == "AIR":
            material = "BK7"
        if count == 1:
            return ("AIR",)
        return tuple(material for _ in range(count - 1)) + ("AIR",)

    def _saved_promoted_step_native_trace_plan(
        self,
        row: SurfaceRow,
        *,
        source_path: Path,
        source_row_index: int,
        output_row_index: int,
        z_station: float,
    ) -> dict[str, object] | None:
        advanced = row.advanced if isinstance(getattr(row, "advanced", None), dict) else {}
        if not str(advanced.get("Solid_3d_stl", "") or "").strip():
            return None
        try:
            stat_key = (int(source_path.stat().st_mtime_ns), int(source_path.stat().st_size))
        except Exception:
            stat_key = (0, 0)
        cache_key = (
            str(source_path.resolve()),
            stat_key,
            str(getattr(row, "glass", "") or ""),
            round(float(getattr(row, "thickness", 0.0) or 0.0), 9),
            tuple(round(float(getattr(row, attr, 0.0) or 0.0), 9) for attr in ("tilt_x", "tilt_y", "tilt_z")),
            tuple(round(float(getattr(row, attr, 0.0) or 0.0), 9) for attr in ("desp_x", "desp_y", "desp_z")),
            int(output_row_index),
            round(float(z_station), 9),
        )
        cache = getattr(self, "_saved_step_native_trace_plan_cache", {}) or {}
        cached = cache.get(cache_key)
        if isinstance(cached, dict):
            rows = cached.get("rows")
            if isinstance(rows, (list, tuple)) and rows:
                copied_rows = [SurfaceRow(**asdict(item)) for item in rows if isinstance(item, SurfaceRow)]
                if copied_rows:
                    return {**cached, "rows": copied_rows, "cache_hit": True}
        try:
            from KrakenOS.UI.services.step_native_reconstruction import reconstruct_step_native_surfaces

            probe = reconstruct_step_native_surfaces(source_path)
            try:
                surface_count = len(list(probe.component_rows()))
            except Exception:
                surface_count = len(list(getattr(probe, "surface_fits", ()) or ()))
            material_sequence = self._saved_step_native_material_sequence(row, surface_count)
            if not material_sequence:
                return None
            reconstruction = reconstruct_step_native_surfaces(source_path, glass_sequence=material_sequence)
            if not bool(getattr(reconstruction, "trace_ready", False)):
                return None
            native_rows = [SurfaceRow(**asdict(item)) for item in list(reconstruction.component_rows())]
        except Exception as exc:
            try:
                self.append_debug(f"Saved STEP native trace skipped for S{source_row_index}: {_short_error_message(exc)}")
            except Exception:
                pass
            return None
        if not native_rows:
            return None
        original_track = max(float(getattr(row, "thickness", 0.0) or 0.0), 0.0)
        native_track = sum(max(float(getattr(item, "thickness", 0.0) or 0.0), 0.0) for item in native_rows)
        if original_track > native_track and native_rows:
            native_rows[-1].thickness = float(getattr(native_rows[-1], "thickness", 0.0) or 0.0) + (original_track - native_track)
        center_world = self._saved_step_native_center_world(row, z_station)
        native_center_z = self._native_reconstruction_center_z(reconstruction)
        row_indices = list(range(int(output_row_index), int(output_row_index) + len(native_rows)))
        for offset, native_row in enumerate(native_rows):
            native_row.element = str(getattr(row, "element", "") or "STEP native trace")
            native_row.name = f"Trace-native {Path(source_path).stem} S{offset + 1}: {native_row.name}"
            native_row.tilt_x = float(getattr(row, "tilt_x", 0.0) or 0.0)
            native_row.tilt_y = float(getattr(row, "tilt_y", 0.0) or 0.0)
            native_row.tilt_z = float(getattr(row, "tilt_z", 0.0) or 0.0)
            native_row.desp_x = float(center_world[0])
            native_row.desp_y = float(center_world[1])
            native_row.desp_z = float(center_world[2] - float(z_station) - float(native_center_z))
            native_row.axis_move = 0.0
            native_row.advanced = dict(native_row.advanced or {})
            native_row.advanced["StepNativePromotion"] = {
                "step_label": "optical",
                "source_step_path": str(source_path.resolve()),
                "source_saved_row_index": int(source_row_index),
                "row_index_offset": int(offset),
                "row_indices": row_indices,
                "material_sequence": list(material_sequence),
                "row_coordinates": "native_reconstructed_prescription_from_saved_step_row",
                "trace_ready": True,
                "trace_only": True,
            }
        plan = {
            "source_row_index": int(source_row_index),
            "row_index": int(output_row_index),
            "row_indices": row_indices,
            "rows": [SurfaceRow(**asdict(item)) for item in native_rows],
            "source_step_path": str(source_path.resolve()),
            "trace_backend": "saved_step_native_analytic_rows",
            "material_sequence": material_sequence,
        }
        cache[cache_key] = {**plan, "rows": [SurfaceRow(**asdict(item)) for item in native_rows]}
        while len(cache) > 8:
            try:
                cache.pop(next(iter(cache)))
            except Exception:
                break
        self._saved_step_native_trace_plan_cache = cache
        return plan

    def _saved_promoted_step_native_trace_rows(
        self,
        rows: list[SurfaceRow],
    ) -> tuple[list[SurfaceRow], list[dict[str, object]]]:
        output: list[SurfaceRow] = []
        records: list[dict[str, object]] = []
        z_station = 0.0
        changed = False
        for source_index, row in enumerate(list(rows or [])):
            source_path = self._saved_step_source_path_for_row(row)
            plan = None
            if source_path is not None:
                plan = self._saved_promoted_step_native_trace_plan(
                    row,
                    source_path=source_path,
                    source_row_index=int(source_index),
                    output_row_index=len(output),
                    z_station=float(z_station),
                )
            if isinstance(plan, dict):
                native_rows = [
                    SurfaceRow(**asdict(item))
                    for item in list(plan.get("rows", []) or [])
                    if isinstance(item, SurfaceRow)
                ]
                if native_rows:
                    output.extend(native_rows)
                    records.append({key: value for key, value in plan.items() if key != "rows"})
                    z_station += sum(float(getattr(item, "thickness", 0.0) or 0.0) for item in native_rows)
                    changed = True
                    continue
            output.append(row)
            z_station += float(getattr(row, "thickness", 0.0) or 0.0)
        if not changed:
            return rows, []
        return output, records

    def _live_step_overlay_trace_rows(self) -> tuple[list[SurfaceRow], list[dict[str, object]]]:
        if self._step_path_for_label("optical") is None:
            return self.rows, []
        base_rows = [SurfaceRow(**asdict(row)) for row in self.rows]
        cache_key = self._live_step_overlay_trace_cache_key("optical", base_rows)
        cached_plan = self._cached_live_step_overlay_trace_plan(cache_key)
        if cached_plan is not None:
            rows = cached_plan.get("rows")
            if isinstance(rows, (list, tuple)) and rows:
                row_index = int(cached_plan.get("row_index", len(base_rows)))
                insert_at = max(1, min(row_index, len(base_rows)))
                for offset, row in enumerate(rows):
                    if isinstance(row, SurfaceRow):
                        base_rows.insert(insert_at + offset, SurfaceRow(**asdict(row)))
                return base_rows, [cached_plan]
            row = cached_plan.get("row")
            if isinstance(row, SurfaceRow):
                row_index = int(cached_plan.get("row_index", len(base_rows)))
                base_rows.insert(max(1, min(row_index, len(base_rows))), SurfaceRow(**asdict(row)))
                return base_rows, [cached_plan]
        original_rows = self.rows
        try:
            self.rows = base_rows
            plan = self._step_overlay_optical_solid_row_plan(
                "optical",
                cache_subdir="live_step_overlays",
                transient_live_trace=True,
                use_current_selection=False,
                quiet=True,
            )
            if plan is None:
                return original_rows, []
            rows = plan.get("rows")
            if isinstance(rows, (list, tuple)) and rows:
                row_index = int(plan.get("row_index", len(base_rows)))
                insert_at = max(1, min(row_index, len(base_rows)))
                inserted = 0
                for offset, row in enumerate(rows):
                    if isinstance(row, SurfaceRow):
                        base_rows.insert(insert_at + offset, SurfaceRow(**asdict(row)))
                        inserted += 1
                if inserted:
                    self._remember_live_step_overlay_trace_plan(cache_key, plan)
                    return base_rows, [plan]
                return original_rows, []
            row = plan.get("row")
            if not isinstance(row, SurfaceRow):
                return original_rows, []
            row_index = int(plan.get("row_index", len(base_rows)))
            base_rows.insert(max(1, min(row_index, len(base_rows))), SurfaceRow(**asdict(row)))
            self._remember_live_step_overlay_trace_plan(cache_key, plan)
            return base_rows, [plan]
        finally:
            self.rows = original_rows

    def _live_step_overlay_trace_cache_key(self, label: str, rows: list[SurfaceRow]) -> object | None:
        label = str(label).strip().lower()
        source_path = self._step_path_for_label(label)
        if source_path is None:
            return None
        try:
            row_signature = _row_specs_signature(self._serializable_specs_for_rows(rows))
        except Exception:
            row_signature = tuple(
                (
                    str(getattr(row, "surface", "") or ""),
                    float(getattr(row, "thickness", 0.0) or 0.0),
                    float(getattr(row, "diameter", 0.0) or 0.0),
                    float(getattr(row, "desp_x", 0.0) or 0.0),
                    float(getattr(row, "desp_y", 0.0) or 0.0),
                    float(getattr(row, "desp_z", 0.0) or 0.0),
                )
                for row in rows
            )
        return (
            label,
            str(Path(source_path).resolve()),
            float(self._step_x_rotation_deg(label)),
            float(self._step_y_rotation_deg(label)),
            float(self._step_roll_deg(label)),
            tuple(float(value) for value in self._step_axis_offset_xy(label)),
            tuple(float(value) for value in self._step_placement_offset_xyz(label)),
            bool(getattr(self, "lens_step_largest_component_only", True)) if label == "lens" else None,
            row_signature,
        )

    def _cached_live_step_overlay_trace_plan(self, cache_key: object | None) -> dict[str, object] | None:
        if cache_key is None:
            return None
        cache = getattr(self, "_live_step_overlay_trace_plan_cache", {}) or {}
        cached = cache.get(cache_key)
        if not isinstance(cached, dict):
            return None
        row = cached.get("row")
        if not isinstance(row, SurfaceRow):
            return None
        copied = dict(cached)
        copied["row"] = SurfaceRow(**asdict(row))
        copied["cache_hit"] = True
        return copied

    def _remember_live_step_overlay_trace_plan(self, cache_key: object | None, plan: dict[str, object]) -> None:
        if cache_key is None or not isinstance(plan, dict):
            return
        row = plan.get("row")
        if not isinstance(row, SurfaceRow):
            return
        cache = dict(getattr(self, "_live_step_overlay_trace_plan_cache", {}) or {})
        cached = dict(plan)
        cached["row"] = SurfaceRow(**asdict(row))
        cache[cache_key] = cached
        while len(cache) > 4:
            try:
                cache.pop(next(iter(cache)))
            except Exception:
                break
        self._live_step_overlay_trace_plan_cache = cache

    def _preview_render_rows(self, scene_bundle: SceneBundle | None = None) -> list[SurfaceRow]:
        if (
            scene_bundle is not None
            and scene_bundle is self.__dict__.get("_last_live_step_overlay_scene_bundle")
        ):
            rows = self.__dict__.get("_last_live_step_overlay_trace_rows")
            if rows:
                return list(rows)
        if (
            scene_bundle is not None
            and scene_bundle is self.__dict__.get("_last_saved_step_native_scene_bundle")
        ):
            # Saved STEP native reconstruction is a trace-only substitution.
            # The editable/display row remains the promoted file-backed STEP
            # row, otherwise Open 3D draws hidden analytic rows as extra
            # bodies and placement handles operate on shifted row indices.
            return list(self.rows)
        return list(self.rows)

    def _preview_render_row_names(self, scene_bundle: SceneBundle | None = None) -> list[str]:
        return [str(getattr(row, "name", "") or "") for row in self._preview_render_rows(scene_bundle)]

    def _preview_scene_sampling_mode(self) -> str:
        """Sampling mode for the shared traced scene used by 2D and Open 3D."""
        if self._is_full_pupil_mode():
            return "full_pupil"
        try:
            trace_state = self._resolved_trace_mode(system=self.__dict__.get("last_system"))
        except Exception:
            trace_state = {}
        if bool(trace_state.get("use_nonseq")) or bool(trace_state.get("use_folded")):
            return "world_envelope"
        return "display_slice"

    def _open3d_inspector_is_live(self) -> bool:
        """True when an Open 3D inspector window is currently open.

        Reads the instance ``__dict__`` directly: a plain ``getattr`` falls
        through Tk's ``__getattr__`` and recurses on stripped snapshot editors
        (validators) that never initialise ``_three_d_inspector``.
        """
        inspector = self.__dict__.get("_three_d_inspector")
        if inspector is None:
            return False
        try:
            return bool(inspector.winfo_exists())
        except Exception:
            return False

    def _preview_2d_sampling_mode(self) -> str:
        """Sampling mode for editable 2D projections.

        North Star invariant #2: the 2D layout is a slice of the traced 3D data,
        not a separate simulation. When Open 3D is live we trace the single
        ``world_cone`` (the 3D truth) and the 2D pane is its X=0 meridional slice
        (see ``_should_filter_projection_slice``); the cone is built to contain a
        uniform meridional fan, so the sliced 2D is pixel-identical to the flat
        fan. With no Open 3D window we trace only that fan (``world_envelope``) --
        lazily, since nothing draws the off-meridian rays. Either way the 2D shows
        the same meridional fan.
        """
        if self._is_full_pupil_mode():
            return "full_pupil"
        if self._open3d_inspector_is_live() and self._preview_3d_sampling_mode() == "world_cone":
            return "world_cone"
        return "world_envelope"

    def _preview_3d_sampling_mode(self) -> str:
        """Sampling mode for Open 3D.

        Sequential, non-folded scenes launch a 3D cone (the meridional fan
        revolved about the optical axis) so the 3D view reads as a cone; the 2D
        layout is the X=0 meridional slice of this same cone bundle (North Star
        invariant #2), not a separate trace. Nonsequential / folded scenes keep
        the area-filling ``world_envelope`` so branched paths retain sagittal
        width. A filled full-pupil trace still wins when explicitly requested.
        """
        if self._is_full_pupil_mode():
            return "full_pupil"
        if self._launch_pupil_prefers_meridional_fan():
            return "world_cone"
        return "world_envelope"

    def _current_preview_scene_trace(self):
        if bool(getattr(self, "_preview_scene_trace_dirty", False)):
            return None
        if self.last_system is None or self.last_rays is None or self._last_scene_bundle is None:
            return None
        if not preview_trace_signature_matches(self._last_preview_trace_signature, self._preview_trace_signature()):
            return None
        # Two-arm display-fold: a load-time analysis refresh (refresh_plot) caches the raw
        # non-folded bundle in _last_scene_bundle. Reusing it for Open 3D shows the OLD rays
        # until a manual Trace Now. If this is a >=2-imaging-arm splitter scene but the cached
        # bundle carries no folded ('twoarm/...') paths, force a fresh build so the fold shows
        # on open without the user clicking Trace Now.
        try:
            if len(self._imaging_branch_leaves()) >= 2:
                cached_paths = getattr(self._last_scene_bundle, "ray_paths", []) or []
                if not any(
                    str(getattr(path, "branch_path", "") or "").startswith("twoarm/")
                    for path in cached_paths
                ):
                    return None
        except Exception:
            pass
        return self.last_system, self.last_rays, self._last_scene_bundle

    def _build_preview_system_and_rays(self):
        system, rays, _scene_bundle = self._build_preview_system_rays_bundle(update_state=True)
        return system, rays

    def _folded_preview_mirror_mesh_for_row(
        self,
        row_index: int,
        row: SurfaceRow,
        *,
        system=None,
    ):
        """Return a 3-D mirror mesh congruent with folded-preview ray geometry."""
        _ensure_pv()
        if pv is None or row.surface != "Mirror":
            return None
        try:
            folded_geometry = self._current_folded_surface_geometry(system=system)
        except Exception:
            folded_geometry = None
        if folded_geometry is None:
            return None
        try:
            _point, _direction, _max_half, _extent_points, elements = folded_geometry
        except Exception:
            return None
        mirror_tangent = None
        center = None
        for element_index, element in enumerate(list(elements or []), start=1):
            if element_index != int(row_index):
                continue
            try:
                surface_type, element_center = element[0], element[1]
            except Exception:
                return None
            if surface_type != "Mirror":
                return None
            center = np.asarray(element_center, dtype=float).reshape(-1)[:2]
            mirror_tangent = element[4] if len(element) > 4 else None
            break
        if center is None or center.size < 2 or not np.all(np.isfinite(center[:2])):
            return None
        tangent = np.asarray(mirror_tangent, dtype=float).reshape(-1)[:2] if mirror_tangent is not None else None
        if tangent is None or tangent.size < 2 or not np.all(np.isfinite(tangent[:2])):
            angle = np.deg2rad(self._mirror_display_slant_deg_for_rows(self.rows, int(row_index)))
            tangent = np.asarray((np.cos(angle), np.sin(angle)), dtype=float)
        norm = float(np.linalg.norm(tangent))
        if norm <= 1e-12:
            return None
        tangent = tangent / norm
        try:
            half_line = max(float(row.diameter) * 0.5, 0.5)
        except Exception:
            half_line = 0.5
        try:
            half_width = max(min(float(row.diameter) * 0.5, half_line), 0.5)
        except Exception:
            half_width = half_line
        p0 = center[:2] - tangent * half_line
        p1 = center[:2] + tangent * half_line
        points = np.asarray(
            (
                (-half_width, p0[1], p0[0]),
                (half_width, p0[1], p0[0]),
                (half_width, p1[1], p1[0]),
                (-half_width, p1[1], p1[0]),
            ),
            dtype=float,
        )
        faces = np.asarray((4, 0, 1, 2, 3), dtype=np.int64)
        try:
            return pv.PolyData(points, faces)
        except Exception:
            return None

    def _iter_3d_optical_surface_meshes(
        self,
        system,
        *,
        include_reference_surfaces: bool,
    ) -> list[SurfaceMesh3D]:
        transforms = getattr(system, "TRANS_2A", None)
        surfaces = getattr(system, "AAA", None)
        if transforms is None or surfaces is None:
            return []
        surface_descriptors = getattr(system, "SDT_0", None)
        try:
            surface_count = len(surface_descriptors)
        except Exception:
            surface_count = 0
        block_count = min(len(self.rows), getattr(surfaces, "n_blocks", 0), len(transforms), surface_count)
        mesh_items: list[SurfaceMesh3D] = []
        pose_overrides = optical_solid_output_port_pose_overrides(system, self.rows)
        # 0113: in a two-arm splitter fold, the per-arm fold detectors sit at the PHYSICAL focus and
        # supersede the scene's prescription Detector/Image surfaces. Skip their clear-aperture DISKS
        # (drawn here, separate from the surface_curves suppressed in 0110/0112) so no no-correction
        # "image plane in front" is drawn at the prescription focus -- the user's flag.
        try:
            _two_arm_fold = len(self._imaging_branch_leaves()) >= 2
        except Exception:
            _two_arm_fold = False
        for index in range(block_count):
            row = self.rows[index]
            if _two_arm_fold:
                _name = str(getattr(row, "name", "") or "").strip().lower()
                _surf = str(getattr(row, "surface", "") or "").strip().lower()
                if _surf == "image" or "detector" in _name:
                    continue
            if not include_reference_surfaces and row.surface in {"Object", "Image"}:
                continue
            row_transform = optical_solid_output_port_runtime_transform_override(system, self.rows, index)
            mesh = None
            advanced = row.advanced if isinstance(row.advanced, dict) else {}
            if advanced.get("InPathTrailingSpacer"):
                # bugs/0093: the in-path gap-carrier (bugs/0079) keeps the solid's
                # large diameter so the trace never clips, but it is a bookkeeping AIR
                # gap, NOT a physical surface -- don't draw its big flat clear-aperture
                # disk at the cube's transmit output ("why is there a big circle?").
                continue
            # User explicitly skipped a missing CAD asset in the
            # Missing-assets dialog: emit a visible placeholder instead
            # of falling through to the silent analytic single-face
            # fallback. The placeholder is a red wireframe box sized
            # from the row's aperture diameter so the row's position is
            # still meaningful in the scene; the renderer keys off
            # ``is_missing_placeholder`` and draws no glassy body / rim
            # outline for it.
            if _row_has_skipped_missing_asset(advanced):
                placeholder = ThreeDSceneToolsMixin._missing_asset_placeholder_mesh(
                    row, transforms[index] if 0 <= index < len(transforms) else None
                )
                if placeholder is not None:
                    mesh_items.append(
                        SurfaceMesh3D(
                            row_index=index,
                            kind="missing_asset",
                            row=row,
                            surface=surface_descriptors[index] if 0 <= index < surface_count else None,
                            mesh=placeholder,
                            color=(0.92, 0.18, 0.22),
                            opacity=0.18,
                            is_body=True,
                            is_missing_placeholder=True,
                        )
                    )
                continue
            # Trailing surface of an analytic-promoted lens whose
            # front row owns the STEP body STL: skip entirely. The
            # body mesh already includes this curved face; drawing
            # KrakenOS's rotationally-symmetric analytic cap on top
            # of a plano-cyl rectangular body would show a sphere
            # poking through. Set by promote service.
            if advanced.get("StepAnalyticBodyOmitMesh"):
                continue
            file_backed_optical_solid = self._scene_graph_value_present(advanced.get("Solid_3d_stl"))
            if row.surface == "Mirror":
                mesh = self._folded_preview_mirror_mesh_for_row(index, row, system=system)
            if mesh is None and (file_backed_optical_solid or index in pose_overrides):
                mesh = ThreeDSceneToolsMixin._runtime_trace_surface_mesh(system, index)
            if row_transform is None:
                row_transform = transforms[index]
            # A parked uncoated solid is dropped from the optical trace
            # (bugs/0065), so its build transform is on-axis; redraw the DISPLAY
            # body at its decentered station instead of letting it snap onto the
            # optical axis the instant it is promoted (bugs/0067). No-op for a
            # coated splitter, whose build keeps its decenter. Trace untouched.
            built_surfaces = getattr(system, "SDT", None)
            if (
                row_transform is not None
                and built_surfaces is not None
                and 0 <= index < len(built_surfaces)
            ):
                redecentered = offbeam_neutralized_body_transform(
                    row_transform,
                    surface_row_to_spec(row),
                    getattr(built_surfaces[index], "DespX", 0.0),
                    getattr(built_surfaces[index], "DespY", 0.0),
                )
                if redecentered is not None:
                    row_transform = redecentered
            if file_backed_optical_solid and row_transform is not None and mesh is None:
                solid_mesh = self._stl_mesh_with_world_transform(row, row_transform)
                if solid_mesh is not None and int(getattr(solid_mesh, "n_points", 0)) > 0:
                    mesh = solid_mesh
            # Analytic-promoted lens body: the promote service caches
            # the imported STEP overlay's mesh as STL and stores the
            # path here. Using the actual STEP geometry instead of
            # KrakenOS's rotationally-symmetric analytic mesh makes
            # plano-cylindrical lenses render as their true
            # rectangular shape, not as round discs. Trace ignores
            # this key -- refraction still uses Rc / k /
            # Cylinder_Rxy_Ratio.
            analytic_body_stl = advanced.get("StepAnalyticBodyStlPath") if isinstance(advanced, dict) else None
            if mesh is None and analytic_body_stl and row_transform is not None:
                body_mesh = self._stl_mesh_from_path_with_world_transform(
                    str(analytic_body_stl), row_transform
                )
                if body_mesh is not None and int(getattr(body_mesh, "n_points", 0)) > 0:
                    mesh = body_mesh
            if mesh is None:
                mesh = Kraken3DInspector._mesh_with_transform(surfaces[index], row_transform)
            if mesh is None and row_transform is not None:
                mesh = self._stl_mesh_with_world_transform(row, row_transform)
            if mesh is None or int(getattr(mesh, "n_points", 0)) == 0:
                continue
            mesh = ThreeDSceneToolsMixin._reference_mesh_with_row_diameter(mesh, row)
            surface = surface_descriptors[index]
            mesh_color = (0.10, 0.62, 0.72) if file_backed_optical_solid else Kraken3DInspector._surface_color(surface)
            # Default-opacity tuning: file-backed legacy STL bodies
            # stay at 0.30 (their own glassy treatment lives in the
            # scene-refresh clamp), mirrors near-opaque, all other
            # Standard analytic caps drop to ~0.35 so the glassy
            # Phong highlight reads as see-through glass rather
            # than a painted disc. Object/Image planes are not
            # caps; the reference-mesh fallback keeps them visible
            # via their own paths.
            mesh_opacity = 0.30 if file_backed_optical_solid else (0.88 if row.surface == "Mirror" else 0.35)
            mesh_items.append(
                SurfaceMesh3D(
                    row_index=index,
                    kind=str(row.surface or "standard").lower().replace(" ", "_"),
                    row=row,
                    surface=surface,
                    mesh=mesh,
                    color=mesh_color,
                    opacity=mesh_opacity,
                    is_stop=self._legacy_3d_is_stop_plane(row),
                    is_body=bool(file_backed_optical_solid),
                )
            )
        return mesh_items

    @staticmethod
    def _runtime_trace_surface_mesh(system, row_index: int) -> pv.DataSet | None:
        _ensure_pv()
        if pv is None or system is None:
            return None
        meshes = getattr(system, "EEE", None)
        try:
            if meshes is None or not (0 <= int(row_index) < len(meshes)):
                return None
            mesh = pv.wrap(meshes[int(row_index)])
        except Exception:
            return None
        try:
            mesh = mesh.extract_surface(algorithm="dataset_surface")
        except Exception:
            pass
        try:
            mesh = mesh.copy(deep=True)
        except Exception:
            return None
        try:
            pts = np.asarray(mesh.points, dtype=float)
        except Exception:
            return None
        if pts.ndim != 2 or pts.shape[0] < 1 or not np.any(np.all(np.isfinite(pts[:, :3]), axis=1)):
            return None
        return mesh

    @staticmethod
    def _reference_mesh_with_row_diameter(mesh, row: SurfaceRow):
        _ensure_pv()
        if pv is None or mesh is None:
            return mesh
        surface = str(getattr(row, "surface", "") or "").strip()
        if surface not in {"Object", "Image"}:
            return mesh
        try:
            target_radius = max(float(getattr(row, "diameter", 0.0) or 0.0) * 0.5, 0.0)
        except Exception:
            return mesh
        if target_radius <= 1e-12:
            return mesh
        try:
            scaled = mesh.copy(deep=True)
            pts = np.asarray(scaled.points, dtype=float)
        except Exception:
            return mesh
        if pts.ndim != 2 or pts.shape[0] < 1 or pts.shape[1] < 3:
            return mesh
        finite = np.all(np.isfinite(pts[:, :3]), axis=1)
        if not np.any(finite):
            return mesh
        center = np.mean(pts[finite, :3], axis=0)
        radii = np.linalg.norm(pts[finite, :3] - center, axis=1)
        current_radius = float(np.max(radii)) if radii.size else 0.0
        if current_radius <= 1e-12:
            return mesh
        pts[:, :3] = center + (pts[:, :3] - center) * (target_radius / current_radius)
        try:
            scaled.points = pts
            return scaled
        except Exception:
            return mesh

    @staticmethod
    def _missing_asset_placeholder_mesh(row: SurfaceRow, transform):
        """Return a red wireframe box sized from the row's aperture.

        Drawn for rows where the user clicked Skip in the Missing-assets
        dialog. The point is to make the broken row visibly different
        from a normal lens: the renderer wraps this mesh in a red edge
        outline (no glassy body, no rim circle) so it reads as "this
        row references a CAD file that is not on disk" at a glance.
        """
        _ensure_pv()
        if pv is None:
            return None
        try:
            diameter = float(getattr(row, "diameter", 0.0) or 0.0)
        except Exception:
            diameter = 0.0
        radius = max(diameter * 0.5, 1.0)  # never less than 1 mm so the
                                            # marker stays visible even
                                            # for tiny apertures
        try:
            thickness = float(getattr(row, "thickness", 0.0) or 0.0)
        except Exception:
            thickness = 0.0
        # A small but non-zero axial depth: even an Object/Image plane
        # gets a flat-ish marker rather than a degenerate box.
        depth = max(abs(thickness) * 0.5, radius * 0.20, 1.0)
        try:
            box = pv.Box(
                bounds=(
                    -radius, radius,
                    -radius, radius,
                    -depth, depth,
                )
            )
        except Exception:
            return None
        if transform is None:
            return box
        try:
            matrix = np.asarray(transform, dtype=float).reshape(4, 4)
        except Exception:
            return box
        try:
            pts = np.asarray(box.points, dtype=float)
            local_h = np.column_stack((pts, np.ones(pts.shape[0], dtype=float)))
            box.points = (matrix @ local_h.T).T[:, :3]
        except Exception:
            return None
        return box

    # ------------------------------------------------------------------
    # Negative-existence cache for STEP / STL paths.
    #
    # Without this, a missing file gets probed up to 18 times per scene
    # refresh (every analytic-fit lookup, every face metadata pass,
    # every body STL load). Each probe is a ``Path.exists`` syscall plus
    # a Python exception construction -- individually fast but cumulative
    # enough to feel in the live log when 5 rows reference missing
    # files. The cache is keyed on the resolved absolute path string
    # and expires after a short TTL so the user can drop the file back
    # in mid-session and the renderer recovers without a restart.
    # ------------------------------------------------------------------

    # 60 s is long enough that the negative cache covers a full
    # interactive editing burst (open layout → orbit → toggle rays →
    # edit a row) without re-paying any probe. The Missing-assets
    # dialog explicitly calls ``_clear_missing_path`` after a successful
    # relocate so the renderer picks up the new file immediately, with
    # no need to wait for the TTL.
    _MISSING_PATH_CACHE_TTL_S: float = 60.0

    def _path_is_missing_cached(self, path) -> bool:
        """Return True if ``path`` was seen missing within the TTL."""
        if path is None:
            return False
        try:
            key = str(path)
        except Exception:
            return False
        cache = self.__dict__.setdefault("_missing_path_cache", {})
        import time as _time

        last_miss = cache.get(key)
        if last_miss is None:
            return False
        if (_time.monotonic() - float(last_miss)) > self._MISSING_PATH_CACHE_TTL_S:
            cache.pop(key, None)
            return False
        return True

    def _record_missing_path(self, path) -> None:
        if path is None:
            return
        try:
            key = str(path)
        except Exception:
            return
        cache = self.__dict__.setdefault("_missing_path_cache", {})
        import time as _time

        cache[key] = _time.monotonic()

    def _clear_missing_path(self, path) -> None:
        """Forget a cached miss (call after a successful relocate)."""
        if path is None:
            return
        try:
            key = str(path)
        except Exception:
            return
        cache = self.__dict__.get("_missing_path_cache")
        if isinstance(cache, dict):
            cache.pop(key, None)

    def _stl_mesh_from_path_with_world_transform(
        self,
        path: str,
        transform: np.ndarray,
    ) -> pv.DataSet | None:
        """Load STL at ``path`` and return a pv.PolyData in world coords.

        Used by the analytic-promote rendering branch -- the cached
        STEP body STL is loaded once per render frame and transformed
        by the row's tilt + desp matrix so the body appears in the
        right world position.
        """
        _ensure_pv()
        if pv is None:
            return None
        # Negative cache short-circuit: if we already saw this path
        # missing within the TTL, don't re-stat it. This is the path
        # the analytic-promote body STL goes through, which used to get
        # probed once per row per refresh per session.
        if self._path_is_missing_cached(path):
            return None
        try:
            _fmt, triangles = _read_stl_triangle_vertices(path)
            triangles = np.asarray(triangles, dtype=float)
            if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or triangles.shape[0] == 0:
                return None
            points = triangles.reshape((-1, 3))
            local_h = np.column_stack(
                (
                    points[:, 0],
                    points[:, 1],
                    points[:, 2],
                    np.ones(points.shape[0], dtype=float),
                )
            )
            matrix = np.asarray(transform, dtype=float).reshape(4, 4)
            world = (matrix @ local_h.T).T[:, :3]
            faces = np.column_stack(
                (
                    np.full(triangles.shape[0], 3, dtype=np.int64),
                    np.arange(points.shape[0], dtype=np.int64).reshape((-1, 3)),
                )
            ).ravel()
            return pv.PolyData(world, faces)
        except FileNotFoundError:
            self._record_missing_path(path)
            return None
        except Exception:
            return None

    def _stl_mesh_with_world_transform(self, row: SurfaceRow, transform: np.ndarray) -> pv.DataSet | None:
        _ensure_pv()
        if pv is None:
            return None
        path = self._stl_path_from_row(row)
        if path is None:
            return None
        try:
            _fmt, triangles = _read_stl_triangle_vertices(path)
            triangles = np.asarray(triangles, dtype=float)
            if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or triangles.shape[0] == 0:
                return None
            points = triangles.reshape((-1, 3))
            local_h = np.column_stack(
                (
                    points[:, 0],
                    points[:, 1],
                    points[:, 2],
                    np.ones(points.shape[0], dtype=float),
                )
            )
            matrix = np.asarray(transform, dtype=float).reshape(4, 4)
            world = (matrix @ local_h.T).T[:, :3]
            faces = np.column_stack(
                (
                    np.full(triangles.shape[0], 3, dtype=np.int64),
                    np.arange(points.shape[0], dtype=np.int64).reshape((-1, 3)),
                )
            ).ravel()
            return pv.PolyData(world, faces)
        except Exception:
            return None

    @staticmethod
    def _file_backed_row_display_transform(row: SurfaceRow, z_station: float) -> np.ndarray:
        matrix = np.eye(4, dtype=float)
        try:
            matrix[:3, :3] = np.asarray(
                _rotation_matrix_from_kraken_tilts(
                    float(getattr(row, "tilt_x", 0.0) or 0.0),
                    float(getattr(row, "tilt_y", 0.0) or 0.0),
                    float(getattr(row, "tilt_z", 0.0) or 0.0),
                ),
                dtype=float,
            )
        except Exception:
            matrix[:3, :3] = np.eye(3, dtype=float)
        try:
            center = ThreeDSceneToolsMixin._saved_step_native_center_world(row, float(z_station))
        except Exception:
            center = np.asarray(
                (
                    float(getattr(row, "desp_x", 0.0) or 0.0),
                    float(getattr(row, "desp_y", 0.0) or 0.0),
                    float(z_station) + float(getattr(row, "desp_z", 0.0) or 0.0),
                ),
                dtype=float,
            )
        matrix[:3, 3] = np.asarray(center, dtype=float).reshape(-1)[:3]
        return matrix

    def _saved_step_native_display_surface_meshes(
        self,
        *,
        include_reference_surfaces: bool,
    ) -> list[SurfaceMesh3D]:
        _ensure_pv()
        if pv is None:
            return []
        mesh_items: list[SurfaceMesh3D] = []
        try:
            z_positions = list(self._row_z_positions())
        except Exception:
            z_positions = []
        for row_index, row in enumerate(list(self.rows or [])):
            if not include_reference_surfaces and row.surface in {"Object", "Image"}:
                continue
            advanced = row.advanced if isinstance(row.advanced, dict) else {}
            if not self._scene_graph_value_present(advanced.get("Solid_3d_stl")):
                continue
            z_station = float(z_positions[row_index]) if row_index < len(z_positions) else 0.0
            transform = self._file_backed_row_display_transform(row, z_station)
            mesh = self._stl_mesh_with_world_transform(row, transform)
            if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
                continue
            mesh_items.append(
                SurfaceMesh3D(
                    row_index=int(row_index),
                    kind=str(row.surface or "standard").lower().replace(" ", "_"),
                    row=row,
                    surface=None,
                    mesh=mesh,
                    color=(0.10, 0.62, 0.72),
                    opacity=0.30,
                    is_stop=self._legacy_3d_is_stop_plane(row),
                    is_body=False,
                )
            )
        return mesh_items

    def _iter_3d_side_body_meshes(
        self,
        system,
        *,
        include_reference_surfaces: bool,
    ) -> list[SurfaceMesh3D]:
        _ensure_pv()
        surface_descriptors = getattr(system, "SDT_0", None)
        try:
            surface_count = len(surface_descriptors)
        except Exception:
            surface_count = 0
        mesh_items: list[SurfaceMesh3D] = []
        side_index = 0
        for row_index in getattr(system, "side_number", []):
            try:
                row_index_int = int(row_index)
            except Exception:
                side_index += 1
                continue
            if row_index_int >= len(self.rows) or row_index_int >= surface_count:
                side_index += 1
                continue
            row = self.rows[row_index_int]
            if not include_reference_surfaces and row.surface in {"Object", "Image"}:
                side_index += 1
                continue
            advanced = row.advanced if isinstance(row.advanced, dict) else {}
            if self._geometry_value_present(advanced.get("Solid_3d_stl")):
                side_index += 1
                continue
            try:
                body = pv.wrap(system.BBB[side_index]).extract_surface(algorithm="dataset_surface").copy(deep=True)
            except Exception:
                side_index += 1
                continue
            side_index += 1
            if int(getattr(body, "n_points", 0)) == 0:
                continue
            surface = surface_descriptors[row_index_int]
            # Analytic-promoted STEP lens already shows its actual
            # body mesh via StepAnalyticBodyStlPath (front row) and
            # suppresses the trailing analytic cap. KrakenOS's
            # auto-revolved BBB body would draw a rotational
            # cylinder/torus over the rectangular STEP body, giving
            # a ring-around-the-plate look on plano-cyl lenses.
            # Render the BBB body at opacity 0 in that case: the
            # downstream actor still exists (so _row_actor_map
            # centroid queries -- e.g. Phase 6 of the harness --
            # keep working) but it is visually invisible.
            body_opacity = 0.18
            if advanced.get("StepAnalyticBodyStlPath") or advanced.get("StepAnalyticBodyOmitMesh"):
                body_opacity = 0.0
            # Microns-thick cement/optical-contact bond: keep the actor (so
            # _row_actor_map centroid queries still resolve) but draw it
            # invisibly, so a cemented doublet reads as two cemented elements
            # in 3D instead of a duplicated slab (bugs/0046). See the constant.
            layer_thickness_mm = abs(float(getattr(row, "thickness", 0.0) or 0.0))
            if layer_thickness_mm < _CEMENT_LAYER_MAX_AXIAL_THICKNESS_MM:
                body_opacity = 0.0
            mesh_items.append(
                SurfaceMesh3D(
                    row_index=row_index_int,
                    kind=f"{str(row.surface or 'standard').lower().replace(' ', '_')}_solid",
                    row=row,
                    surface=surface,
                    mesh=body,
                    color=Kraken3DInspector._surface_color(surface),
                    opacity=body_opacity,
                    is_stop=self._legacy_3d_is_stop_plane(row),
                    is_body=True,
                )
            )
        return mesh_items

    def _iter_3d_surface_meshes(
        self,
        system,
        *,
        include_reference_surfaces: bool,
    ) -> list[SurfaceMesh3D]:
        return [
            *self._iter_3d_optical_surface_meshes(system, include_reference_surfaces=include_reference_surfaces),
            *self._iter_3d_side_body_meshes(system, include_reference_surfaces=include_reference_surfaces),
        ]

    def _scene_surface_meshes(
        self,
        system,
        scene_bundle: SceneBundle | None = None,
        *,
        include_reference_surfaces: bool,
    ) -> list[SurfaceMesh3D]:
        bundle = scene_bundle if scene_bundle is not None else self._last_scene_bundle
        if (
            bundle is not None
            and bundle is self.__dict__.get("_last_saved_step_native_scene_bundle")
        ):
            mesh_items = self._saved_step_native_display_surface_meshes(
                include_reference_surfaces=include_reference_surfaces,
            )
            if mesh_items:
                return mesh_items
        mesh_items = list(getattr(bundle, "surface_meshes", []) or []) if bundle is not None else []
        if not mesh_items and system is not None:
            mesh_items = self._iter_3d_surface_meshes(system, include_reference_surfaces=True)
            if bundle is not None:
                bundle.surface_meshes = list(mesh_items)
        if include_reference_surfaces:
            return mesh_items
        return [
            mesh_item
            for mesh_item in mesh_items
            if getattr(mesh_item.row, "surface", "") not in {"Object", "Image"}
        ]

    def _build_legacy_3d_plotter(self, system, rays, *, scene_bundle: SceneBundle | None = None):
        _load_3d_backends()
        if pv is None:
            raise RuntimeError("PyVista is required for legacy 3D view")
        plotter = pv.Plotter(shape=(1, 1), title="KrakenOS 3D", notebook=False)
        plotter.set_background("white", top="white")
        plotter.enable_anti_aliasing()
        try:
            plotter.render_window.SetStereoTypeToFake()
            plotter.render_window.StereoRenderOff()
            plotter.render_window.StereoCapableWindowOff()
        except Exception:
            pass
        plotter.add_axes(line_width=3)
        plotter.show_grid(font_size=6, color="black", n_xlabels=2, n_ylabels=2, n_zlabels=2, fmt="%.0f", bold=False)
        scene_bundle = scene_bundle if scene_bundle is not None else self._last_scene_bundle
        scene_info = self._populate_legacy_3d_plotter_scene(
            plotter,
            system,
            rays,
            scene_bundle=scene_bundle,
            add_clip_plane=False,
            add_labels=True,
        )
        self._configure_legacy_3d_plotter(
            plotter,
            ray_actors=scene_info["ray_actors"],
            mirror_actors=scene_info["mirror_actors"],
            lens_actors=scene_info["lens_actors"],
            helper_actors=scene_info["helper_actors"],
        )
        self._enable_legacy_3d_close_handling(plotter)
        setattr(plotter, "_kraken_scene", scene_info)
        setattr(plotter, "_kraken_scene_bundle", scene_bundle)
        setattr(plotter, "_kraken_system", system)
        setattr(plotter, "_kraken_rays", rays)
        return plotter

    def _legacy_3d_scene_service(self) -> Legacy3DSceneService:
        service = self.__dict__.get("_legacy_3d_scene_service_instance")
        if service is None:
            service = Legacy3DSceneService(self)
            self._legacy_3d_scene_service_instance = service
        return service

    def _populate_legacy_3d_plotter_scene(
        self,
        plotter,
        system,
        rays,
        *,
        scene_bundle: SceneBundle | None = None,
        add_clip_plane: bool,
        add_labels: bool,
    ) -> dict[str, list]:
        return self._legacy_3d_scene_service()._populate_legacy_3d_plotter_scene(
            plotter,
            system,
            rays,
            scene_bundle=scene_bundle,
            add_clip_plane=add_clip_plane,
            add_labels=add_labels,
        )

    def _build_clean_legacy_3d_plotter(self, system, rays):
        _load_3d_backends()
        if pv is None:
            raise RuntimeError("PyVista is required for 3D screenshot export")
        plotter = pv.Plotter(off_screen=True, window_size=(2200, 1400), notebook=False)
        plotter.set_background("white", top="white")
        plotter.enable_anti_aliasing()
        try:
            plotter.render_window.SetStereoTypeToFake()
            plotter.render_window.StereoRenderOff()
            plotter.render_window.StereoCapableWindowOff()
        except Exception:
            pass
        plotter.add_axes(line_width=3)
        plotter.show_grid(font_size=6, color="black", n_xlabels=2, n_ylabels=2, n_zlabels=2, fmt="%.0f", bold=False)
        scene_bundle = self._last_scene_bundle
        scene_info = self._populate_legacy_3d_plotter_scene(
            plotter,
            system,
            rays,
            scene_bundle=scene_bundle,
            add_clip_plane=False,
            add_labels=False,
        )
        setattr(plotter, "_kraken_scene", scene_info)
        setattr(plotter, "_kraken_scene_bundle", scene_bundle)
        return plotter

    @staticmethod
    def _legacy_3d_is_stop_plane(row: SurfaceRow) -> bool:
        name = (row.name or "").strip().lower()
        return "stop" in name or "aperture" in name

    @staticmethod
    def _legacy_3d_stop_ring_mesh(mesh, row: SurfaceRow):
        _ensure_pv()
        try:
            pts = np.asarray(mesh.points, dtype=float)
        except Exception:
            return None
        if pts.size == 0:
            return None
        center = np.mean(pts, axis=0)
        centered = pts - center
        try:
            _u, _s, vh = np.linalg.svd(centered, full_matrices=False)
            normal = np.asarray(vh[-1], dtype=float)
        except Exception:
            normal = np.array([0.0, 0.0, 1.0], dtype=float)
        norm = max(float(np.linalg.norm(normal)), 1e-12)
        normal = normal / norm
        outer = max(float(row.diameter) * 0.5, 0.5)
        inner = max(outer * 0.82, outer - 0.8)
        if inner >= outer:
            inner = outer * 0.9
        try:
            return pv.Disc(center=center, inner=inner, outer=outer, normal=normal, r_res=1, c_res=96)
        except Exception:
            return None

    def _legacy_3d_ray_radius(self, system, rays) -> float:
        try:
            bounds = np.asarray(system.AAA.bounds, dtype=float)
        except Exception:
            bounds = np.array([0.0, 100.0, -25.0, 25.0, -25.0, 25.0], dtype=float)
        span = max(
            float(bounds[1] - bounds[0]) if bounds.size >= 2 else 0.0,
            float(bounds[3] - bounds[2]) if bounds.size >= 4 else 0.0,
            float(bounds[5] - bounds[4]) if bounds.size >= 6 else 0.0,
            1.0,
        )
        ray_count = max(len(getattr(rays, "CC", [])), 1)
        return max(span * 0.0009 / max(np.sqrt(ray_count), 1.0), 0.05)

    def _physical_dimension_values(self) -> tuple[float, float, float, float, float] | None:
        if not self.rows or len(self.rows) < 3:
            return None
        housing_front_z = self._lens_front_datum_z()
        object_z = 0.0
        image_z = self._current_image_plane_z()
        camera_front_z = image_z - self._current_camera_front_to_sensor_mm()
        if not all(np.isfinite(value) for value in (object_z, housing_front_z, camera_front_z)):
            return None
        return (
            float(object_z),
            float(housing_front_z),
            float(camera_front_z),
            abs(float(housing_front_z - object_z)),
            abs(float(camera_front_z - housing_front_z)),
        )

    def _add_legacy_3d_physical_dimensions(self, plotter, helper_actors: list) -> None:
        self._legacy_3d_scene_service()._add_legacy_3d_physical_dimensions(plotter, helper_actors)

    def _iter_3d_display_rays(self, rays):
        return [(wave, path) for _index, wave, path in self._iter_3d_display_ray_items(rays)]

    def _iter_3d_display_ray_items(self, rays):
        waves = list(getattr(rays, "RayWave", []))
        paths = list(getattr(rays, "CC", []))
        total = min(len(waves), len(paths))
        if total <= 0:
            return []
        waves = waves[:total]
        paths = paths[:total]
        if total <= 300:
            return [(index, waves[index], paths[index]) for index in range(total)]
        step = max(total // 300, 1)
        return [(index, waves[index], paths[index]) for index in range(0, total, step)]

    def _iter_3d_scene_ray_items(
        self,
        rays=None,
        scene_bundle: SceneBundle | None = None,
    ) -> list[tuple[int, tuple[float, float, float], np.ndarray]]:
        return [
            (ray_index, color, points)
            for ray_index, color, points, _terminal_status in self._iter_3d_scene_ray_records(rays, scene_bundle)
        ]

    def _iter_3d_scene_ray_records(
        self,
        rays=None,
        scene_bundle: SceneBundle | None = None,
    ) -> list[tuple[int, tuple[float, float, float], np.ndarray, str]]:
        bundle = scene_bundle if scene_bundle is not None else self._last_scene_bundle
        scene_paths = list(getattr(bundle, "ray_paths", []) or []) if bundle is not None else []
        if scene_paths:
            live_step_preview = (
                bundle is self.__dict__.get("_last_live_step_overlay_scene_bundle")
                and any(
                    bool(record.get("transient_live_trace", False))
                    for record in list(getattr(self, "_last_live_step_overlay_trace_records", []) or [])
                    if isinstance(record, dict)
                )
            )
            show_clipped_rays = bool(self.show_clipped_rays_var.get())
            if not show_clipped_rays and not live_step_preview:
                visible_paths = [path for path in scene_paths if ray_path_visible_without_clipping_from_events(path)]
                # bugs/0022: when the filter would hide EVERY ray, don't blank
                # the trace. Moving an element off the beam (e.g. shifting the
                # beam-splitter cube sideways) can make every path escape without
                # reaching a surface AND without a reflective fold to keep it
                # visible -- the on-axis beam now misses the (port-followed)
                # detector. The user still expects to see where the beam goes, so
                # only suppress clipped rays when at least one survives (the
                # bug-0016 mixed case: hide strays among rays that DO land).
                scene_paths = visible_paths if visible_paths else scene_paths
            total = len(scene_paths)
            draw_budget = (
                _RAY_DRAW_BUDGET_CONE
                if scene_bundle_launch_sampling_mode(bundle) == "world_cone"
                else _RAY_DRAW_BUDGET_DEFAULT
            )
            step = max(total // draw_budget, 1) if total > draw_budget else 1
            rendered: list[tuple[int, tuple[float, float, float], np.ndarray, str]] = []
            for fallback_index, path in enumerate(scene_paths[0:total:step]):
                points = np.asarray(path.points_world, dtype=float)
                if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
                    continue
                path_color = str(getattr(path, "color", "") or "").strip()
                if path_color:
                    color = _color_to_rgb_tuple(path_color)
                else:
                    wavelength = getattr(path, "wavelength", None)
                    if wavelength is not None:
                        color = tuple(_wavelength_to_rgb(float(wavelength) * 1000.0))
                    else:
                        color = _color_to_rgb_tuple("#39FF14")
                try:
                    ray_index = int(getattr(path, "ray_index"))
                except Exception:
                    ray_index = int(fallback_index * step)
                terminal_status = ray_path_terminal_status_from_events(path)
                if live_step_preview and not show_clipped_rays:
                    points = self._trim_transient_step_terminal_tail_for_display(
                        points,
                        path,
                        terminal_status=terminal_status,
                    )
                    if points.ndim != 2 or points.shape[0] < 2:
                        continue
                rendered.append((ray_index, color, points[:, :3], terminal_status))
            return rendered

        fallback_rays = rays if rays is not None else self.last_rays
        return [
            (int(ray_index), tuple(_wavelength_to_rgb(float(wave) * 1000.0)), np.asarray(ray_pts, dtype=float), "")
            for ray_index, wave, ray_pts in self._iter_3d_display_ray_items(fallback_rays)
        ]

    @staticmethod
    def _scene_center_radius_from_bounds(bounds) -> tuple[np.ndarray, float]:
        try:
            values = np.asarray(bounds, dtype=float).reshape(-1)[:6]
        except Exception:
            values = np.asarray([], dtype=float)
        if values.size != 6 or not np.all(np.isfinite(values)) or values[0] > values[1]:
            return np.zeros(3, dtype=float), 1.0
        center = np.array(
            [
                0.5 * (values[0] + values[1]),
                0.5 * (values[2] + values[3]),
                0.5 * (values[4] + values[5]),
            ],
            dtype=float,
        )
        radius = max(values[1] - values[0], values[3] - values[2], values[5] - values[4], 1.0)
        return center, float(radius)

    @staticmethod
    def _trim_transient_step_terminal_tail_for_display(
        points,
        path,
        *,
        terminal_status: str = "",
    ) -> np.ndarray:
        try:
            pts = np.asarray(points, dtype=float)
        except Exception:
            return np.empty((0, 3), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
            return np.empty((0, 3), dtype=float)
        pts = np.array(pts[:, :3], dtype=float, copy=True)
        finite = np.all(np.isfinite(pts), axis=1)
        if not np.all(finite):
            pts = pts[finite]
        if pts.shape[0] < 2:
            return np.empty((0, 3), dtype=float)
        status = str(terminal_status or "").strip().lower()
        if status not in {"escaped", "missed_detector"}:
            return pts
        last_surface_point = None
        for event in reversed(list(getattr(path, "events", []) or [])):
            if str(getattr(event, "event_kind", "") or "").strip().lower() == "terminal":
                continue
            try:
                candidate = np.asarray(getattr(event, "point_world", ()), dtype=float).reshape(-1)[:3]
            except Exception:
                candidate = np.asarray([], dtype=float)
            if candidate.size == 3 and np.all(np.isfinite(candidate)):
                last_surface_point = candidate
                break
        if last_surface_point is not None:
            distances = np.linalg.norm(pts[:, :3] - last_surface_point[:3], axis=1)
            if distances.size:
                index = int(np.argmin(distances))
                if float(distances[index]) <= 1.0e-6 and index >= 1:
                    return pts[: index + 1]
        if pts.shape[0] > 2:
            return pts[:-1]
        return pts

    @staticmethod
    def _scene_ray_path_by_index(scene_bundle: SceneBundle | None) -> dict[int, object]:
        if scene_bundle is None:
            return {}
        paths: dict[int, object] = {}
        for path in list(getattr(scene_bundle, "ray_paths", []) or []):
            try:
                paths[int(getattr(path, "ray_index"))] = path
            except Exception:
                continue
        return paths

    @staticmethod
    def _missed_detector_target_for_path(scene_bundle: SceneBundle | None, path: object | None) -> SceneTarget3D | None:
        if scene_bundle is None or path is None:
            return None
        if ray_path_terminal_status_from_events(path) != "missed_detector":
            return None
        metadata = ray_path_terminal_metadata(path)
        surface = metadata.get("detector_miss_surface")
        if surface in (None, ""):
            event = ray_path_terminal_event(path)
            if event is not None:
                surface = getattr(event, "surface_id", None)
        try:
            surface_index = int(surface)
        except Exception:
            return None
        for target in list(getattr(scene_bundle, "targets", []) or []):
            trace_surface = getattr(target, "trace_surface", None)
            try:
                if trace_surface is not None and int(trace_surface) == surface_index:
                    return target
            except Exception:
                continue
        return None

    @staticmethod
    def _terminal_display_direction_for_path(path: object | None) -> np.ndarray | None:
        if path is None:
            return None
        event = ray_path_terminal_event(path)
        if event is not None:
            for attribute in ("outgoing_direction", "incoming_direction"):
                direction = ThreeDSceneToolsMixin._unit_3d_vector_or_none(getattr(event, attribute, None))
                if direction is not None:
                    return direction
        try:
            points = np.asarray(getattr(path, "points_world", []), dtype=float)
        except Exception:
            return None
        if points.ndim == 2 and points.shape[0] >= 2 and points.shape[1] >= 3:
            return ThreeDSceneToolsMixin._unit_3d_vector_or_none(points[-1, :3] - points[-2, :3])
        return None

    @staticmethod
    def _unit_3d_vector_or_none(value) -> np.ndarray | None:
        try:
            vector = np.asarray(value, dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        if vector.size < 3 or not np.all(np.isfinite(vector[:3])):
            return None
        norm = float(np.linalg.norm(vector[:3]))
        if not np.isfinite(norm) or norm <= 1.0e-12:
            return None
        return vector[:3] / norm

    @staticmethod
    def _target_frame_axes_for_display(target: SceneTarget3D | None) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
        if target is None:
            return None
        try:
            center = np.asarray(getattr(target, "center_world", ()), dtype=float).reshape(-1)[:3]
            normal = np.asarray(getattr(target, "normal_world", ()), dtype=float).reshape(-1)[:3]
            tangent = np.asarray(getattr(target, "tangent_world", ()), dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        if (
            center.size < 3
            or normal.size < 3
            or tangent.size < 3
            or not np.all(np.isfinite(center[:3]))
            or not np.all(np.isfinite(normal[:3]))
            or not np.all(np.isfinite(tangent[:3]))
        ):
            return None
        normal_norm = float(np.linalg.norm(normal[:3]))
        if not np.isfinite(normal_norm) or normal_norm <= 1.0e-12:
            return None
        normal = normal[:3] / normal_norm
        tangent = tangent[:3] - normal * float(np.dot(tangent[:3], normal))
        tangent_norm = float(np.linalg.norm(tangent))
        if not np.isfinite(tangent_norm) or tangent_norm <= 1.0e-12:
            for candidate in (
                np.asarray((1.0, 0.0, 0.0), dtype=float),
                np.asarray((0.0, 1.0, 0.0), dtype=float),
                np.asarray((0.0, 0.0, 1.0), dtype=float),
            ):
                tangent = candidate - normal * float(np.dot(candidate, normal))
                tangent_norm = float(np.linalg.norm(tangent))
                if np.isfinite(tangent_norm) and tangent_norm > 1.0e-12:
                    break
        if not np.isfinite(tangent_norm) or tangent_norm <= 1.0e-12:
            return None
        tangent = tangent / tangent_norm
        bitangent = np.cross(normal, tangent)
        bitangent_norm = float(np.linalg.norm(bitangent))
        if not np.isfinite(bitangent_norm) or bitangent_norm <= 1.0e-12:
            return None
        return center[:3], tangent, bitangent / bitangent_norm

    @staticmethod
    def _target_active_dimensions_for_display(target: SceneTarget3D | None) -> tuple[float, float] | None:
        if target is None:
            return None
        try:
            diameter = max(float(getattr(target, "diameter", 0.0) or 0.0), 0.0)
        except Exception:
            diameter = 0.0
        try:
            width = max(float(getattr(target, "active_width_mm", 0.0) or 0.0), 0.0)
        except Exception:
            width = 0.0
        try:
            height = max(float(getattr(target, "active_height_mm", 0.0) or 0.0), 0.0)
        except Exception:
            height = 0.0
        if width <= 1.0e-12:
            width = diameter
        if height <= 1.0e-12:
            height = diameter
        if width <= 1.0e-12 or height <= 1.0e-12:
            return None
        return float(width), float(height)

    @staticmethod
    def _display_detector_miss_limit(target: SceneTarget3D | None, radius: float) -> float:
        try:
            scene_radius = float(radius)
        except Exception:
            scene_radius = 1.0
        if not np.isfinite(scene_radius) or scene_radius <= 0.0:
            scene_radius = 1.0
        dimensions = ThreeDSceneToolsMixin._target_active_dimensions_for_display(target)
        aperture_span = max(dimensions) if dimensions is not None else 1.0
        scene_limit = max(25.0, min(scene_radius * 0.35, 250.0))
        return float(max(aperture_span * 1.25, scene_limit))

    @staticmethod
    def _display_detector_miss_point_on_plane(
        point,
        target: SceneTarget3D | None,
        radius: float,
    ) -> tuple[np.ndarray | None, bool]:
        try:
            terminal = np.asarray(point, dtype=float).reshape(-1)[:3]
        except Exception:
            return None, False
        if terminal.size < 3 or not np.all(np.isfinite(terminal[:3])):
            return None, False
        axes = ThreeDSceneToolsMixin._target_frame_axes_for_display(target)
        if axes is None:
            return terminal[:3], False
        center, tangent, bitangent = axes
        rel = terminal[:3] - center
        u = float(np.dot(rel, tangent))
        v = float(np.dot(rel, bitangent))
        limit = ThreeDSceneToolsMixin._display_detector_miss_limit(target, radius)
        radial = float(np.hypot(u, v))
        capped = False
        if np.isfinite(radial) and radial > limit > 0.0:
            scale = limit / radial
            u *= scale
            v *= scale
            capped = True
        display_point = center + tangent * u + bitangent * v
        if not np.allclose(display_point, terminal[:3], rtol=0.0, atol=1.0e-9):
            capped = True
        return display_point, capped

    @staticmethod
    def _detector_miss_crosshair_polylines_for_display(
        path: object,
        target: SceneTarget3D | None,
        *,
        display_center=None,
        display_radius: float = 1.0,
        cap_to_scene: bool = False,
    ) -> list[np.ndarray]:
        if not bool(cap_to_scene):
            return scene_target_detector_miss_crosshair_polylines(path, target)
        if ray_path_terminal_status_from_events(path) != "missed_detector":
            return []
        event = ray_path_terminal_event(path)
        if event is None:
            return []
        point, _capped = ThreeDSceneToolsMixin._display_detector_miss_point_on_plane(
            getattr(event, "point_world", None),
            target,
            display_radius,
        )
        axes = ThreeDSceneToolsMixin._target_frame_axes_for_display(target)
        dimensions = ThreeDSceneToolsMixin._target_active_dimensions_for_display(target)
        if point is None or axes is None or dimensions is None:
            return []
        _center, tangent, bitangent = axes
        width, height = dimensions
        arm = max(min(float(min(width, height)) * 0.18, float(max(width, height)) * 0.35), 0.35)
        return [
            np.vstack((point - tangent * arm, point + tangent * arm)),
            np.vstack((point - bitangent * arm, point + bitangent * arm)),
        ]

    @staticmethod
    def _bounded_3d_ray_points_for_display(
        points,
        center,
        radius: float,
        *,
        terminal_status: str = "",
        terminal_target: SceneTarget3D | None = None,
        terminal_direction=None,
        detector_planes=None,
    ) -> tuple[np.ndarray, bool]:
        return bounded_ray_points_for_scene_display(
            points,
            center,
            radius,
            terminal_status=terminal_status,
            terminal_target=terminal_target,
            terminal_direction=terminal_direction,
            detector_planes=detector_planes,
        )

    @staticmethod
    def _detector_planes_for_hard_stop(scene_bundle, radius: float):
        """Detector planes that hard-stop the drawn 3D ray polylines (bugs/0088)."""
        if scene_bundle is None:
            return []
        try:
            return detector_planes_for_hard_stop(scene_bundle, float(radius))
        except Exception:
            return []

    @staticmethod
    def _ray_vertex_display_inset(radius: float) -> float:
        try:
            scene_radius = float(radius)
        except Exception:
            scene_radius = 1.0
        if not np.isfinite(scene_radius) or scene_radius <= 0.0:
            scene_radius = 1.0
        return float(max(min(scene_radius * 0.0015, 0.18), 0.035))

    @staticmethod
    def _ray_segment_mesh_for_3d_display(points, *, vertex_inset: float = 0.0):
        """Build disconnected VTK line segments for physical ray events.

        Rendering a reflected ray as one connected polyline can let the line
        join/cap project through a mirror-hit vertex and mimic transmission.
        Open 3D should draw each physical segment independently.
        """
        if pv is None:
            try:
                _load_3d_backends()
            except Exception:
                pass
        if pv is None:
            return None
        try:
            pts = np.asarray(points, dtype=float)
        except Exception:
            return None
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
            return None
        finite = np.all(np.isfinite(pts[:, :3]), axis=1)
        pts = pts[finite, :3]
        if pts.shape[0] < 2:
            return None
        try:
            inset = max(float(vertex_inset), 0.0)
        except Exception:
            inset = 0.0
        out_points: list[np.ndarray] = []
        lines: list[int] = []
        last_segment_index = pts.shape[0] - 2
        for segment_index, (start, end) in enumerate(zip(pts[:-1], pts[1:])):
            start = np.asarray(start, dtype=float)
            end = np.asarray(end, dtype=float)
            delta = end - start
            length = float(np.linalg.norm(delta))
            if not np.isfinite(length) or length <= 1.0e-12:
                continue
            a = start.copy()
            b = end.copy()
            local_inset = min(inset, length * 0.20)
            if local_inset > 0.0:
                unit = delta / length
                if segment_index > 0:
                    a = a + unit * local_inset
                if segment_index < last_segment_index:
                    b = b - unit * local_inset
            if float(np.linalg.norm(b - a)) <= 1.0e-12:
                continue
            base = len(out_points)
            out_points.extend((a, b))
            lines.extend((2, base, base + 1))
        if not out_points:
            return None
        try:
            mesh = pv.PolyData(np.asarray(out_points, dtype=float))
            mesh.lines = np.asarray(lines, dtype=np.int64)
            return mesh
        except Exception:
            return None

    @staticmethod
    def _should_draw_3d_terminal_endpoint(
        terminal_status: str,
        *,
        show_terminal_diagnostics: bool = False,
    ) -> bool:
        status = str(terminal_status or "").strip().lower()
        if status == "hit_detector":
            return bool(show_terminal_diagnostics)
        if status in {"absorbed", "stopped"}:
            return bool(show_terminal_diagnostics)
        return False

    @staticmethod
    def _ray_terminal_3d_style(
        color: tuple[float, float, float],
        terminal_status: str,
    ) -> dict[str, object]:
        status = str(terminal_status or "").strip().lower()
        status_colors = {
            "hit_detector": (0.02, 0.48, 0.35),
            "missed_detector": (0.98, 0.45, 0.05),
            "absorbed": (0.35, 0.11, 0.55),
            "escaped": (0.36, 0.42, 0.50),
            "stopped": (0.66, 0.66, 0.66),
        }
        # Escaped rays are ordinary physical exits from the modeled scene. Keep
        # their source/wavelength color so prism output bundles do not look like
        # a different class of ray; reserve full-line diagnostic recoloring for
        # absorption and true stop conditions. "Stopped" rays are *genuine*
        # aperture vignetting (field corners the first element clips); draw them
        # as a thin grey stub so they read as expected vignetting rather than a
        # prominent dark-red error. Their opacity has to stay high enough to
        # actually read against the 3D scene -- the 2D layout shows these clipped
        # stubs plainly, so the Open 3D view must match.
        diagnostic_line_color = status_colors.get(status, color) if status in {"absorbed", "stopped"} else color
        return {
            "line_color": diagnostic_line_color,
            "line_opacity": (
                0.80 if status == "escaped"
                else 0.74 if status == "missed_detector"
                else 0.55 if status == "stopped"
                else 0.88
            ),
            "line_width": 1.5 if status == "missed_detector" else 0.9 if status == "stopped" else 1.0,
            "endpoint_color": status_colors.get(status, color),
            "endpoint_scale": 4.2 if status == "missed_detector" else 1.4 if status == "stopped" else 2.8,
        }

    def _scene_detector_overlay_specs(
        self,
        scene_bundle: SceneBundle | None,
        *,
        include_footprints: bool = True,
        include_miss_crosshairs: bool = True,
        cap_miss_crosshairs_to_scene: bool = False,
        display_center=None,
        display_radius: float = 1.0,
    ) -> list[dict[str, object]]:
        if scene_bundle is None:
            return []
        specs: list[dict[str, object]] = []
        targets = list(getattr(scene_bundle, "targets", []) or [])
        if bool(include_footprints):
            for target in targets:
                try:
                    row_index = int(getattr(target, "row_index", -1))
                except Exception:
                    row_index = -1
                for index, points in enumerate(scene_target_active_footprint_polylines(target)):
                    specs.append(
                        {
                            "kind": "detector_active_footprint" if index == 0 else "detector_active_center",
                            "row_index": row_index,
                            "points": np.asarray(points, dtype=float),
                            "color": (0.98, 0.45, 0.05),
                            "opacity": 0.92 if index == 0 else 0.72,
                            "line_width": 2.2 if index == 0 else 1.2,
                            "pickable": index == 0,
                        }
                    )

        if bool(include_miss_crosshairs):
            targets_by_surface = {}
            for target in targets:
                trace_surface = getattr(target, "trace_surface", None)
                if trace_surface is None:
                    continue
                try:
                    targets_by_surface[int(trace_surface)] = target
                except Exception:
                    continue
            for path in list(getattr(scene_bundle, "ray_paths", []) or []):
                metadata = ray_path_terminal_metadata(path)
                surface = metadata.get("detector_miss_surface")
                event = ray_path_terminal_event(path)
                if surface in (None, "") and event is not None:
                    surface = getattr(event, "surface_id", None)
                try:
                    target = targets_by_surface.get(int(surface))
                except Exception:
                    target = None
                if target is None:
                    continue
                try:
                    row_index = int(getattr(target, "row_index", -1))
                except Exception:
                    row_index = -1
                for points in self._detector_miss_crosshair_polylines_for_display(
                    path,
                    target,
                    display_center=display_center,
                    display_radius=display_radius,
                    cap_to_scene=bool(cap_miss_crosshairs_to_scene),
                ):
                    specs.append(
                        {
                            "kind": "detector_miss_crosshair",
                            "row_index": row_index,
                            "points": np.asarray(points, dtype=float),
                            "color": (0.92, 0.25, 0.05),
                            "opacity": 0.98,
                            "line_width": 2.4,
                            "pickable": False,
                        }
                    )
        return specs

    # ------------------------------------------------------------------
    # Curved best-focus surface overlay (3D field-curvature visualization, idea #2)

    def _best_focus_surface_anchor_target(self, scene_bundle: SceneBundle | None):
        """Pick the flat image-plane target the curved best-focus surface floats over.

        First deliverable = the centered, single-image-plane case: the primary
        sequential image (the highest real-row target). A scene with beam-splitter
        branch detectors (each arm images its own field) is SKIPPED for now -- a
        per-branch best-focus surface is a follow-up.
        """
        if scene_bundle is None:
            return None
        anchor = None
        anchor_row = -1
        has_branch_detector = False
        for target in list(getattr(scene_bundle, "targets", []) or []):
            metadata = getattr(target, "metadata", None)
            source = str(metadata.get("target_source", "")) if isinstance(metadata, dict) else ""
            if source == "branch_detector":
                has_branch_detector = True
                continue
            try:
                row_index = int(getattr(target, "row_index", -1))
            except Exception:
                row_index = -1
            if row_index >= 100000:  # synthetic branch-detector row
                continue
            if row_index >= anchor_row:
                anchor_row = row_index
                anchor = target
        if has_branch_detector:
            return None
        return anchor

    @staticmethod
    def _best_focus_surface_radius(target) -> float:
        """Rim radius for the surface = the image / detector half-extent."""
        width = float(getattr(target, "active_width_mm", 0.0) or 0.0)
        height = float(getattr(target, "active_height_mm", 0.0) or 0.0)
        if width > 1e-6 and height > 1e-6:
            return 0.5 * min(width, height)
        diameter = float(getattr(target, "diameter", 0.0) or 0.0)
        if diameter > 1e-6:
            return 0.5 * diameter
        return 0.0

    def best_focus_surface_overlay_spec(self, system, scene_bundle, *, wavelength=None):
        """Build the translucent curved best-focus surface spec, or None.

        Lazy + cached by the preview-trace signature: the field-curvature scan
        (`_sample_field_curvature_distortion`) traces dense meridional/sagittal fans,
        so it must NOT recompute on every render-only refresh (the bugs/0166 overlay
        toggles re-render the cached scene). Returns None for branch / fieldless /
        sizeless scenes so nothing draws there.
        """
        if system is None or scene_bundle is None:
            return None
        target = self._best_focus_surface_anchor_target(scene_bundle)
        if target is None:
            return None
        if wavelength is None:
            try:
                wavelength = float(self._current_wavelength())
            except Exception:
                return None
        override = self._field_aberration_exaggeration_value()
        try:
            signature = (
                self._preview_trace_signature(),
                round(float(wavelength), 6),
                int(getattr(target, "row_index", -1)),
                None if override is None else round(float(override), 4),
            )
        except Exception:
            signature = None
        cache = self.__dict__.get("_best_focus_surface_cache")
        if signature is not None and isinstance(cache, tuple) and len(cache) == 2 and cache[0] == signature:
            return cache[1]
        spec = self._compute_best_focus_surface_spec(system, target, float(wavelength), override)
        if signature is not None:
            self._best_focus_surface_cache = (signature, spec)
        return spec

    def _image_circle_radius_value(self):
        """The drawn image-circle radius (``field_image_radius``), so the best-focus bowl
        and distortion grid can size their rim to COINCIDE with it. The traced chief rays
        land ~1% inside (the distortion, which the warped grid shows); the user expects the
        bowl edge to sit on the image circle, not as a separate smaller ring."""
        try:
            radius = float(self._field_metrics_summary().get("field_image_radius", 0.0))
            return radius if np.isfinite(radius) and radius > 1e-6 else None
        except Exception:
            return None

    def _field_aberration_exaggeration_value(self):
        """User-set field-aberration exaggeration for the best-focus/distortion overlays:
        a positive float, or None for the auto factor. Lets the user trade visibility
        (auto magnifies the sub-mm aberrations) against true scale (×1, where the bowl
        coincides with the flat image circle -- no apparent 'detachment')."""
        value = getattr(self, "_field_aberration_exaggeration", None)
        try:
            return float(value) if value is not None and float(value) > 0.0 else None
        except Exception:
            return None

    def _compute_best_focus_surface_spec(self, system, target, wavelength: float, exaggeration=None):
        try:
            # The field-curvature scan lives on the composed AnalysisPlotService
            # (reached via the editor's accessor), not directly on the editor.
            sampled = self._analysis_plot_service()._sample_field_curvature_distortion(system, wavelength)
        except Exception as exc:  # pragma: no cover - defensive
            try:
                self.append_debug(f"Best-focus surface: field-curvature scan failed: {exc}")
            except Exception:
                pass
            return None
        if not sampled:
            return None
        axis_results, _field_type, field_limit = sampled
        y_result = axis_results.get("Y") if isinstance(axis_results, dict) else None
        x_result = axis_results.get("X") if isinstance(axis_results, dict) else None
        if not isinstance(y_result, dict) or not isinstance(x_result, dict):
            return None
        # Size the rings to the REAL chief-ray image height per field (where the rays
        # actually land on the detector) -- the user flagged that the bowl built from
        # the lens clear-aperture diameter ran past where the rays land. Falls back to
        # the field grid only if the scan didn't export image heights.
        image_heights = y_result.get("image_height")
        if image_heights is None:
            fields = np.asarray(y_result.get("fields"), dtype=float)
            flim = float(field_limit) if float(field_limit) > 1e-9 else (float(np.max(np.abs(fields))) or 1.0)
            image_heights = (np.abs(fields) / flim) * float(self._best_focus_surface_radius(target))
        # Rim -> the image-circle radius so the bowl coincides with the drawn image circle.
        image_heights = np.asarray(image_heights, dtype=float)
        fir = self._image_circle_radius_value()
        peak = float(np.max(np.abs(image_heights))) if image_heights.size else 0.0
        if fir is not None and peak > 1e-9:
            image_heights = image_heights * (fir / peak)
        spec = build_best_focus_surface(
            image_heights,
            y_result.get("focus"),
            x_result.get("focus"),
            center=np.asarray(getattr(target, "center_world"), dtype=float),
            normal=np.asarray(getattr(target, "normal_world"), dtype=float),
            tangent=np.asarray(getattr(target, "tangent_world"), dtype=float),
            exaggeration=exaggeration,
        )
        if spec is not None:
            spec["faces"] = best_focus_surface_faces(spec["n_rings"], spec["n_az"])
            spec["ring_polylines"] = best_focus_surface_ring_polylines(spec)
        return spec

    # ------------------------------------------------------------------
    # Distortion grid-warp overlay (3D field-distortion viz, idea #2 / 2nd half)

    def distortion_grid_overlay_spec(self, system, scene_bundle, *, wavelength=None, lift_onto_best_focus=False):
        """Build the rectilinear-vs-warped distortion grid spec, or None.

        Same lazy + signature-cached contract as ``best_focus_surface_overlay_spec``
        (the field scan is expensive; the bugs/0166 overlay toggles re-render the cached
        scene). Anchors on the primary sequential image plane; branch / fieldless /
        sizeless scenes return None. When ``lift_onto_best_focus`` (the user has the
        Focus-surf overlay on too) the warped grid is laid onto the curved best-focus
        bowl -- the "distorted bowl".
        """
        if system is None or scene_bundle is None:
            return None
        target = self._best_focus_surface_anchor_target(scene_bundle)
        if target is None:
            return None
        if wavelength is None:
            try:
                wavelength = float(self._current_wavelength())
            except Exception:
                return None
        override = self._field_aberration_exaggeration_value()
        try:
            signature = (
                self._preview_trace_signature(),
                round(float(wavelength), 6),
                int(getattr(target, "row_index", -1)),
                bool(lift_onto_best_focus),
                None if override is None else round(float(override), 4),
            )
        except Exception:
            signature = None
        cache = self.__dict__.get("_distortion_grid_cache")
        if signature is not None and isinstance(cache, tuple) and len(cache) == 2 and cache[0] == signature:
            return cache[1]
        bf_spec = self.best_focus_surface_overlay_spec(system, scene_bundle) if lift_onto_best_focus else None
        spec = self._compute_distortion_grid_spec(system, target, float(wavelength), bf_spec, override)
        if signature is not None:
            self._distortion_grid_cache = (signature, spec)
        return spec

    def _compute_distortion_grid_spec(self, system, target, wavelength: float, bf_spec=None, exaggeration=None):
        try:
            sampled = self._analysis_plot_service()._sample_field_curvature_distortion(system, wavelength)
        except Exception as exc:  # pragma: no cover - defensive
            try:
                self.append_debug(f"Distortion grid: field scan failed: {exc}")
            except Exception:
                pass
            return None
        if not sampled:
            return None
        axis_results, _field_type, _field_limit = sampled
        y_result = axis_results.get("Y") if isinstance(axis_results, dict) else None
        if not isinstance(y_result, dict):
            return None
        real = np.asarray(y_result.get("image_height"), dtype=float).reshape(-1)
        distortion = np.asarray(y_result.get("distortion"), dtype=float).reshape(-1)
        if real.size < 2 or distortion.size != real.size:
            return None
        # ideal (paraxial, undistorted) height = real / (1 + distortion%/100).
        with np.errstate(divide="ignore", invalid="ignore"):
            ideal = real / (1.0 + distortion / 100.0)
        if not np.all(np.isfinite(ideal)):
            return None
        # Scale the rectilinear (ideal) grid to the image-circle radius so the reference
        # grid coincides with the drawn image circle; the warped real grid then shows the
        # real image landing ~1% inside (the distortion). Uniform scale preserves the warp.
        fir = self._image_circle_radius_value()
        peak = float(np.max(np.abs(ideal))) if ideal.size else 0.0
        if fir is not None and peak > 1e-9:
            grid_scale = fir / peak
            ideal = ideal * grid_scale
            real = real * grid_scale
        # When the best-focus surface is also on, lay the warped grid onto the bowl
        # (its already-exaggerated axial offsets) -> the "distorted bowl".
        lift_radii = bf_spec.get("ring_radii") if isinstance(bf_spec, dict) else None
        lift_dz = bf_spec.get("display_dz") if isinstance(bf_spec, dict) else None
        return build_distortion_grid(
            ideal,
            real,
            center=np.asarray(getattr(target, "center_world"), dtype=float),
            normal=np.asarray(getattr(target, "normal_world"), dtype=float),
            tangent=np.asarray(getattr(target, "tangent_world"), dtype=float),
            exaggeration=exaggeration,
            lift_radii=lift_radii,
            lift_dz=lift_dz,
        )

    # ------------------------------------------------------------------
    # Tangential / sagittal best-focus surfaces (astigmatism in 3D, idea #2a)

    # Tangential = amber, sagittal = blue; their separation is the astigmatism.
    _ASTIGMATISM_TANGENTIAL_COLOR = (0.96, 0.58, 0.14)
    _ASTIGMATISM_SAGITTAL_COLOR = (0.20, 0.58, 0.92)

    def astigmatism_surfaces_overlay_spec(self, system, scene_bundle, *, wavelength=None):
        """Build the separate tangential + sagittal best-focus surfaces, or None. Their
        gap is the astigmatism. Same lazy + signature-cached, image-plane-anchored
        contract as the medial best-focus bowl."""
        if system is None or scene_bundle is None:
            return None
        target = self._best_focus_surface_anchor_target(scene_bundle)
        if target is None:
            return None
        if wavelength is None:
            try:
                wavelength = float(self._current_wavelength())
            except Exception:
                return None
        override = self._field_aberration_exaggeration_value()
        try:
            signature = (
                self._preview_trace_signature(),
                round(float(wavelength), 6),
                int(getattr(target, "row_index", -1)),
                None if override is None else round(float(override), 4),
                "astigmatism",
            )
        except Exception:
            signature = None
        cache = self.__dict__.get("_astigmatism_surfaces_cache")
        if signature is not None and isinstance(cache, tuple) and len(cache) == 2 and cache[0] == signature:
            return cache[1]
        spec = self._compute_astigmatism_surfaces_spec(system, target, float(wavelength), override)
        if signature is not None:
            self._astigmatism_surfaces_cache = (signature, spec)
        return spec

    def _compute_astigmatism_surfaces_spec(self, system, target, wavelength: float, exaggeration=None):
        try:
            sampled = self._analysis_plot_service()._sample_field_curvature_distortion(system, wavelength)
        except Exception:
            return None
        if not sampled:
            return None
        axis_results, _field_type, _field_limit = sampled
        y_result = axis_results.get("Y") if isinstance(axis_results, dict) else None
        x_result = axis_results.get("X") if isinstance(axis_results, dict) else None
        if not isinstance(y_result, dict) or not isinstance(x_result, dict):
            return None
        image_heights = y_result.get("image_height")
        if image_heights is None:
            return None
        image_heights = np.asarray(image_heights, dtype=float)
        fir = self._image_circle_radius_value()
        peak = float(np.max(np.abs(image_heights))) if image_heights.size else 0.0
        if fir is not None and peak > 1e-9:
            image_heights = image_heights * (fir / peak)
        focus_t = np.asarray(y_result.get("focus"), dtype=float).reshape(-1)
        focus_s = np.asarray(x_result.get("focus"), dtype=float).reshape(-1)
        if focus_t.size < 2 or focus_s.size != focus_t.size:
            return None
        center = np.asarray(getattr(target, "center_world"), dtype=float)
        normal = np.asarray(getattr(target, "normal_world"), dtype=float)
        tangent = np.asarray(getattr(target, "tangent_world"), dtype=float)
        # The medial surface fixes the SHARED exaggeration so the T and S bowls (and the
        # medial bowl, if also shown) are all magnified by the same factor -> their gap is
        # the astigmatism at the true relative scale.
        medial_spec = build_best_focus_surface(
            image_heights, focus_t, focus_s, center=center, normal=normal, tangent=tangent,
            exaggeration=exaggeration,
        )
        if medial_spec is None:
            return None
        factor = float(medial_spec["exaggeration"])
        surfaces = {}
        for key, focus, color in (
            ("tangential", focus_t, self._ASTIGMATISM_TANGENTIAL_COLOR),
            ("sagittal", focus_s, self._ASTIGMATISM_SAGITTAL_COLOR),
        ):
            sub = build_best_focus_surface(
                image_heights, focus, focus, center=center, normal=normal, tangent=tangent,
                exaggeration=factor, color=color,
            )
            if sub is None:
                return None
            sub["faces"] = best_focus_surface_faces(sub["n_rings"], sub["n_az"])
            sub["ring_polylines"] = best_focus_surface_ring_polylines(sub)
            surfaces[key] = sub
        return {
            "kind": "astigmatism_surfaces",
            "tangential": surfaces["tangential"],
            "sagittal": surfaces["sagittal"],
            "max_astigmatism_mm": float(np.max(np.abs(focus_t - focus_s))),
            "exaggeration": factor,
            "center": center,
            "normal": np.asarray(medial_spec["normal"], dtype=float),
        }

    # ------------------------------------------------------------------
    # Spot RMS field map (3D spot-quality viz, idea #1/#3 foundation)

    def spot_field_map_overlay_spec(self, system, scene_bundle, *, wavelength=None):
        """Build the per-field RMS-circle spot map on the detector, or None. Same lazy +
        signature-cached, image-plane-anchored contract as the other field overlays."""
        if system is None or scene_bundle is None:
            return None
        target = self._best_focus_surface_anchor_target(scene_bundle)
        if target is None:
            return None
        if wavelength is None:
            try:
                wavelength = float(self._current_wavelength())
            except Exception:
                return None
        override = self._field_aberration_exaggeration_value()
        try:
            signature = (
                self._preview_trace_signature(),
                round(float(wavelength), 6),
                int(getattr(target, "row_index", -1)),
                None if override is None else round(float(override), 4),
                "spotmap",
            )
        except Exception:
            signature = None
        cache = self.__dict__.get("_spot_field_map_cache")
        if signature is not None and isinstance(cache, tuple) and len(cache) == 2 and cache[0] == signature:
            return cache[1]
        spec = self._compute_spot_field_map_spec(system, target, float(wavelength), override)
        if signature is not None:
            self._spot_field_map_cache = (signature, spec)
        return spec

    def _compute_spot_field_map_spec(self, system, target, wavelength: float, exaggeration=None):
        from contextlib import redirect_stderr, redirect_stdout

        field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
        try:
            field_max = float(self._current_field_angle_deg() if field_type == "angle" else self._current_field_height())
        except Exception:
            field_max = 0.0
        if field_max <= 1e-9:
            field_max = 5.0 if field_type == "angle" else 0.5
        # Hexapolar ring count: 1+3S(S+1) rays/field, so keep S modest -- ~217 rays is
        # ample for an RMS and 13 fields stay cheap (vs the editor ray-count, which with
        # a 2D pupil would be tens of thousands of rays).
        sample_count = 8
        fractions = np.linspace(-1.0, 1.0, 5)
        chief_u: list[float] = []
        chief_v: list[float] = []
        rms: list[float] = []
        scatter: list = []  # per field: the ray intercepts relative to the chief (the spot shape)
        capture = io.StringIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with redirect_stdout(capture), redirect_stderr(capture):
                for fy in fractions:
                    for fx in fractions:
                        if fx * fx + fy * fy > 1.0 + 1e-9:
                            continue  # keep the round field
                        try:
                            x, y, _z, _l, _m, _n, _w = self._build_geometric_image_samples_full(
                                system, wavelength, sample_count=sample_count, pattern="hexapolar",
                                surface_index=self._analysis_surface_index(),
                                aperture_type=self._current_aperture_type(),
                                aperture_value=self._current_aperture_value(),
                                field_type=field_type, field_x=float(fx * field_max), field_y=float(fy * field_max),
                                require_2d_pupil=True,  # 2D pupil so the RMS is a real spot, not a fan
                            )
                        except Exception:
                            continue  # one bad field must not kill the whole map
                        x = np.asarray(x, dtype=float)
                        y = np.asarray(y, dtype=float)
                        if x.size < 3 or y.size != x.size:
                            continue
                        cu = float(np.mean(x))
                        cv = float(np.mean(y))
                        spot_rms = float(np.sqrt(np.mean((x - cu) ** 2 + (y - cv) ** 2)))
                        if np.isfinite(cu) and np.isfinite(cv) and np.isfinite(spot_rms):
                            chief_u.append(cu)
                            chief_v.append(cv)
                            rms.append(spot_rms)
                            scatter.append(np.column_stack((x - cu, y - cv)))
        if len(chief_u) < 2:
            return None
        return build_spot_field_map(
            chief_u, chief_v, rms,
            center=np.asarray(getattr(target, "center_world"), dtype=float),
            normal=np.asarray(getattr(target, "normal_world"), dtype=float),
            tangent=np.asarray(getattr(target, "tangent_world"), dtype=float),
            image_radius=self._image_circle_radius_value(),
            magnification=exaggeration,
            scatter=scatter,
        )

    def _iter_3d_scene_rays(
        self,
        rays=None,
        scene_bundle: SceneBundle | None = None,
    ) -> list[tuple[tuple[float, float, float], np.ndarray]]:
        return [(color, points) for _ray_index, color, points in self._iter_3d_scene_ray_items(rays, scene_bundle)]

    def _configure_legacy_3d_plotter(
        self,
        plotter,
        *,
        ray_actors=None,
        mirror_actors=None,
        lens_actors=None,
        helper_actors=None,
    ) -> None:
        self._legacy_3d_scene_service()._configure_legacy_3d_plotter(
            plotter,
            ray_actors=ray_actors,
            mirror_actors=mirror_actors,
            lens_actors=lens_actors,
            helper_actors=helper_actors,
        )

    def _add_legacy_stl_placement_controls(self, plotter, positions: dict[str, object]) -> None:
        controls = (
            ("Fit+Z", lambda _state: self._legacy_3d_stl_fit_axis(plotter, "+Z")),
            ("Fit+X", lambda _state: self._legacy_3d_stl_fit_axis(plotter, "+X")),
            ("Fit+Y", lambda _state: self._legacy_3d_stl_fit_axis(plotter, "+Y")),
            ("X-90", lambda _state: self._legacy_3d_stl_rotate(plotter, "x", -90.0)),
            ("X+90", lambda _state: self._legacy_3d_stl_rotate(plotter, "x", 90.0)),
            ("Y-90", lambda _state: self._legacy_3d_stl_rotate(plotter, "y", -90.0)),
            ("Y+90", lambda _state: self._legacy_3d_stl_rotate(plotter, "y", 90.0)),
            ("Center", lambda _state: self._legacy_3d_stl_center_xy(plotter)),
            ("Front", lambda _state: self._legacy_3d_stl_front_on_row(plotter)),
            ("Done2D", lambda _state: self._legacy_3d_finish_stl_placement(plotter)),
        )
        for label, callback in controls:
            if label not in positions:
                continue
            self._add_legacy_3d_action_button(
                plotter,
                label=label,
                position=positions[label],
                callback=callback,
                color="#0891b2" if label != "Done2D" else "#0f766e",
            )

    def _legacy_3d_start_stl_placement(self, plotter, row_index: int) -> None:
        if plotter is None:
            return
        try:
            row_index = int(row_index)
        except Exception:
            self.status_var.set("Select an optical CAD/STL row first.")
            return
        if self._file_backed_stl_row_at(row_index) is None:
            self.status_var.set("Selected row is not a file-backed optical CAD/STL solid.")
            return
        setattr(plotter, "_kraken_stl_placement_row", row_index)
        self._select_table_row(row_index)
        self._legacy_3d_set_selected_row(plotter, row_index)
        self.status_var.set(f"Legacy 3D CAD/STL placement target S{row_index}. Use the placement buttons, then Done2D or close.")

    def _legacy_3d_active_stl_row(self, plotter) -> int | None:
        if plotter is None:
            self.status_var.set("Open 3D view before CAD/STL placement.")
            return None
        for candidate in (
            getattr(plotter, "_kraken_stl_placement_row", None),
            getattr(plotter, "_kraken_selected_row", None),
            self._current_selected_row_index(),
        ):
            if candidate is None:
                continue
            try:
                row_index = int(candidate)
            except Exception:
                continue
            if self._file_backed_stl_row_at(row_index) is not None:
                setattr(plotter, "_kraken_stl_placement_row", row_index)
                return row_index
        self.status_var.set("Select an optical CAD/STL row before using placement controls.")
        return None

    def _legacy_3d_stl_fit_axis(self, plotter, axis: str) -> None:
        row_index = self._legacy_3d_active_stl_row(plotter)
        if row_index is None:
            return
        try:
            self.apply_stl_axis_fit(row_index, axis)
            self._legacy_3d_update_stl_row_actor(plotter, row_index)
            self.status_var.set(f"STL S{row_index}: fitted {axis} to layout +Z.")
        except Exception as exc:
            self.status_var.set(f"STL fit failed: {_short_error_message(exc)}")
            self.append_debug(f"Legacy STL fit failed: {exc}")

    def _legacy_3d_stl_rotate(self, plotter, axis: str, delta_deg: float) -> None:
        row_index = self._legacy_3d_active_stl_row(plotter)
        if row_index is None:
            return
        try:
            self.rotate_stl_row_pose(row_index, axis, delta_deg)
            self._legacy_3d_update_stl_row_actor(plotter, row_index)
            self.status_var.set(f"STL S{row_index}: rotated {axis.upper()} {float(delta_deg):+.0f} deg.")
        except Exception as exc:
            self.status_var.set(f"STL rotation failed: {_short_error_message(exc)}")
            self.append_debug(f"Legacy STL rotation failed: {exc}")

    def _legacy_3d_stl_center_xy(self, plotter) -> None:
        row_index = self._legacy_3d_active_stl_row(plotter)
        if row_index is None:
            return
        try:
            self.center_stl_row_xy(row_index)
            self._legacy_3d_update_stl_row_actor(plotter, row_index)
            self.status_var.set(f"STL S{row_index}: centered X/Y.")
        except Exception as exc:
            self.status_var.set(f"STL centering failed: {_short_error_message(exc)}")
            self.append_debug(f"Legacy STL centering failed: {exc}")

    def _legacy_3d_stl_front_on_row(self, plotter) -> None:
        row_index = self._legacy_3d_active_stl_row(plotter)
        if row_index is None:
            return
        try:
            self.place_stl_row_front_on_station(row_index)
            self._legacy_3d_update_stl_row_actor(plotter, row_index)
            self.status_var.set(f"STL S{row_index}: min Z placed on row plane.")
        except Exception as exc:
            self.status_var.set(f"STL front placement failed: {_short_error_message(exc)}")
            self.append_debug(f"Legacy STL front placement failed: {exc}")

    def _legacy_3d_finish_stl_placement(self, plotter) -> None:
        if plotter is not None:
            setattr(plotter, "_kraken_stl_placement_dirty", False)
        try:
            self.refresh_plot(suppress_analysis=True)
            self.status_var.set("CAD/STL placement applied to 2D layout.")
        except Exception as exc:
            self.status_var.set(f"CAD/STL placement saved; 2D refresh failed: {_short_error_message(exc)}")
            self.append_debug(f"Legacy STL Done2D failed: {exc}")

    def _legacy_3d_update_stl_row_actor(self, plotter, row_index: int) -> None:
        _ensure_pv()
        if plotter is None or pv is None:
            return
        selected = self._file_backed_stl_row_at(row_index)
        if selected is None:
            raise RuntimeError("Selected row is not a file-backed optical STL solid")
        row, path = selected
        mesh = pv.read(path).extract_surface(algorithm="dataset_surface").copy(deep=True)
        pts = np.asarray(mesh.points, dtype=float)
        if pts.ndim != 2 or pts.shape[0] == 0 or pts.shape[1] < 3:
            raise RuntimeError("STL mesh has no previewable points")
        rotation = _rotation_matrix_from_kraken_tilts(row.tilt_x, row.tilt_y, row.tilt_z)
        transformed = pts[:, :3] @ rotation.T
        transformed[:, 0] += float(row.desp_x)
        transformed[:, 1] += float(row.desp_y)
        transformed[:, 2] += self._stl_row_z_station(row_index) + float(row.desp_z)
        mesh.points = transformed

        scene_info = dict(getattr(plotter, "_kraken_scene", {}) or {})
        row_actor_map = scene_info.setdefault("row_actor_map", {})
        actor_row_map = scene_info.setdefault("actor_row_map", {})
        for actor in list(row_actor_map.get(int(row_index), []) or []):
            try:
                actor_key = Kraken3DInspector._actor_key(actor)
                if actor_key is not None:
                    actor_row_map.pop(actor_key, None)
                plotter.remove_actor(actor, render=False)
            except Exception:
                try:
                    actor.SetVisibility(False)
                except Exception:
                    pass

        new_actors = []
        actor = plotter.add_mesh(
            mesh,
            color="#0ccfe8",
            opacity=0.68,
            smooth_shading=True,
            show_edges=False,
            pickable=True,
        )
        self._legacy_3d_register_row_actor(actor, int(row_index), actor_row_map, new_actors)
        try:
            edges = mesh.extract_feature_edges(
                feature_angle=15,
                boundary_edges=True,
                feature_edges=True,
                manifold_edges=False,
            )
            if int(getattr(edges, "n_points", 0)) > 0:
                edge_actor = plotter.add_mesh(edges, color="#1f2937", line_width=1.0, pickable=False)
                self._legacy_3d_register_row_actor(edge_actor, int(row_index), actor_row_map, new_actors)
        except Exception:
            pass
        row_actor_map[int(row_index)] = new_actors
        setattr(plotter, "_kraken_scene", scene_info)
        setattr(plotter, "_kraken_stl_placement_row", int(row_index))
        setattr(plotter, "_kraken_stl_placement_dirty", True)
        setattr(plotter, "_kraken_selected_row", None)
        self._legacy_3d_set_selected_row(plotter, int(row_index))
        try:
            plotter.render()
        except Exception:
            pass

    @staticmethod
    def _legacy_3d_register_row_actor(actor, row_index: int, actor_row_map: dict, row_actors: list) -> None:
        if actor is None:
            return
        try:
            actor.SetPickable(True)
        except Exception:
            pass
        actor_key = Kraken3DInspector._actor_key(actor)
        if actor_key is not None:
            actor_row_map[actor_key] = int(row_index)
        try:
            prop = actor.GetProperty()
            if prop is not None:
                actor._kraken_base_style = {
                    "edge_visibility": int(prop.GetEdgeVisibility()),
                    "line_width": float(prop.GetLineWidth()),
                    "edge_color": tuple(float(v) for v in prop.GetEdgeColor()),
                    "opacity": float(prop.GetOpacity()),
                    "ambient": float(prop.GetAmbient()),
                    "diffuse": float(prop.GetDiffuse()),
                }
        except Exception:
            pass
        row_actors.append(actor)

    @staticmethod
    def _legacy_3d_control_positions(plotter) -> dict[str, object]:
        try:
            width = int(plotter.window_size[0])
        except Exception:
            width = 1200
        # Use the full lower edge and reserve a left gutter for category names.
        category_x = 18
        start_x = 118 if width >= 900 else 96
        right_margin = 110
        rows = [
            ("View", ["Save", "Close", "Iso", "YZ", "XZ", "Top", "Bottom", "Home"], "#334155"),
            ("Show/CAD", ["Rays", "Mirrors", "Lenses", "Helpers", "Full Pupil", "Lens CAD", "LED CAD", "Cam CAD"], "#0f766e"),
            (
                "STEP",
                ["X -90", "X +90", "Y -90", "Y +90", "Z -90", "Z +90", "Center STEP", "Obj-LED", "Clear Axis"],
                "#7c3aed",
            ),
            ("STL", ["Fit+Z", "Fit+X", "Fit+Y", "X-90", "X+90", "Y-90", "Y+90", "Center", "CenterRay", "Front", "Done2D"], "#0891b2"),
        ]
        y_positions = [12, 50, 88, 126]
        positions: dict[str, object] = {"__categories__": []}
        usable = max(width - start_x - right_margin, 480)
        for (category, row, color), y_pos in zip(rows, y_positions):
            positions["__categories__"].append((category, (category_x, y_pos + 4), color))
            step_x = max(int(usable / max(len(row) - 1, 1)), 96)
            for index, label in enumerate(row):
                positions[label] = (start_x + int(index * step_x), y_pos)
        return positions

    def _enable_legacy_3d_close_handling(self, plotter) -> None:
        def request_close(*_args):
            try:
                self.after(0, self._close_legacy_3d_plotter)
            except Exception:
                self._close_legacy_3d_plotter()

        try:
            if getattr(plotter, "iren", None) is not None:
                plotter.iren.add_observer("ExitEvent", request_close)
        except Exception as exc:
            self.append_debug(f"Legacy 3D close observer unavailable: {exc}")
        try:
            if getattr(plotter, "render_window", None) is not None:
                plotter.render_window.AddObserver("DeleteEvent", request_close)
        except Exception:
            pass

    def _enable_legacy_3d_picking(self, plotter) -> None:
        if vtkCellPicker is None or getattr(plotter, "iren", None) is None:
            return
        try:
            picker = vtkCellPicker()
            picker.SetTolerance(0.0015)
            setattr(plotter, "_kraken_picker", picker)
            setattr(plotter, "_kraken_selected_row", None)
            setattr(plotter, "_kraken_selected_ray", None)
            setattr(plotter, "_kraken_center_row_to_ray_mode", False)
            setattr(plotter, "_kraken_center_row_to_ray_index", None)
            plotter.iren.add_observer(
                "LeftButtonPressEvent",
                lambda *_args: self._legacy_3d_pick_click(plotter),
            )
            plotter.iren.add_observer(
                "MouseMoveEvent",
                lambda *_args: self._legacy_3d_hover_move(plotter),
            )
        except Exception as exc:
            self.append_debug(f"Legacy 3D picking unavailable: {exc}")

    def _legacy_3d_hover_move(self, plotter) -> None:
        requested_label = self._cad_axis_pick_label
        axis_pick_any = bool(getattr(self, "_cad_axis_pick_any", False))
        led_edge_pick = bool(getattr(self, "_cad_led_object_edge_pick", False))
        target_label = "led" if led_edge_pick else requested_label
        if target_label is None and not axis_pick_any:
            self._legacy_3d_set_step_hover_outline(plotter, None, None)
            self._legacy_3d_set_cursor(plotter, False)
            return
        picker = getattr(plotter, "_kraken_picker", None)
        if picker is None or getattr(plotter, "iren", None) is None:
            return
        try:
            x, y = plotter.iren.get_event_position()
            renderer = plotter.iren.get_poked_renderer(x, y)
            if renderer is None:
                renderer = getattr(plotter, "renderer", None)
            if renderer is None:
                return
            picker.Pick(x, y, 0.0, renderer)
            actor = picker.GetActor()
        except Exception:
            actor = None
        actor_key = Kraken3DInspector._actor_key(actor)
        scene_info = dict(getattr(plotter, "_kraken_scene", {}) or {})
        step_label = scene_info.get("cad_step_actor_map", {}).get(actor_key) if actor_key is not None else None
        if step_label is not None and (axis_pick_any or step_label == target_label):
            try:
                cell_id = int(picker.GetCellId())
            except Exception:
                cell_id = -1
            hover_key = (actor_key, cell_id)
            outline = None
            if hover_key != getattr(plotter, "_kraken_step_hover_key", None):
                feature = Kraken3DInspector._picked_feature_info(actor, picker)
                outline = Kraken3DInspector._hover_overlay_for_feature(feature[0], feature[1]) if feature is not None else None
            self._legacy_3d_set_step_hover_outline(plotter, outline, hover_key)
            self._legacy_3d_set_cursor(plotter, True)
            if led_edge_pick:
                self.status_var.set("Click orange LED edge used for Object-to-LED distance.")
            elif axis_pick_any:
                self.status_var.set(f"Click orange {step_label} feature to center it on the optical axis.")
            else:
                self.status_var.set(f"Click orange {step_label} feature to center it on the optical axis.")
            return
        self._legacy_3d_set_step_hover_outline(plotter, None, None)
        self._legacy_3d_set_cursor(plotter, False)

    def _legacy_3d_set_step_hover_outline(self, plotter, outline_mesh, hover_key) -> None:
        if hover_key is not None and hover_key == getattr(plotter, "_kraken_step_hover_key", None):
            return
        previous = getattr(plotter, "_kraken_step_hover_outline_actor", None)
        if previous is not None:
            try:
                plotter.remove_actor(previous, render=False)
            except Exception:
                try:
                    previous.SetVisibility(False)
                except Exception:
                    pass
        setattr(plotter, "_kraken_step_hover_outline_actor", None)
        setattr(plotter, "_kraken_step_hover_key", hover_key)
        if outline_mesh is not None and int(getattr(outline_mesh, "n_points", 0)) > 0:
            try:
                actor = plotter.add_mesh(
                    outline_mesh,
                    color="#ff2d00",
                    line_width=9.0,
                    opacity=1.0,
                    lighting=False,
                    ambient=1.0,
                    render_lines_as_tubes=True,
                    pickable=False,
                )
                try:
                    actor.SetPickable(False)
                except Exception:
                    pass
                setattr(plotter, "_kraken_step_hover_outline_actor", actor)
            except Exception as exc:
                self.append_debug(f"3D STEP hover outline failed: {exc}")
        try:
            plotter.render()
        except Exception:
            pass

    @staticmethod
    def _legacy_3d_set_cursor(plotter, hand: bool) -> None:
        try:
            if getattr(plotter, "iren", None) is not None and getattr(plotter.iren, "interactor", None) is not None:
                cursor = 9 if hand else 0
                plotter.iren.interactor.SetCurrentCursor(cursor)
                try:
                    render_window = plotter.iren.interactor.GetRenderWindow()
                    if render_window is not None:
                        render_window.SetCurrentCursor(cursor)
                except Exception:
                    pass
        except Exception:
            pass

    def _legacy_3d_pick_click(self, plotter) -> None:
        picker = getattr(plotter, "_kraken_picker", None)
        if picker is None or getattr(plotter, "iren", None) is None:
            return
        try:
            x, y = plotter.iren.get_event_position()
            renderer = plotter.iren.get_poked_renderer(x, y)
            if renderer is None:
                renderer = getattr(plotter, "renderer", None)
            if renderer is None:
                return
            picker.Pick(x, y, 0.0, renderer)
            actor = picker.GetActor()
        except Exception as exc:
            self.append_debug(f"Legacy 3D pick failed: {exc}")
            return
        actor_key = Kraken3DInspector._actor_key(actor)
        scene_info = dict(getattr(plotter, "_kraken_scene", {}) or {})
        step_label = scene_info.get("cad_step_actor_map", {}).get(actor_key) if actor_key is not None else None
        axis_pick_any = bool(getattr(self, "_cad_axis_pick_any", False))
        if step_label is not None:
            if self._cad_led_object_edge_pick:
                if step_label != "led":
                    self.status_var.set("Pick an edge on the LED STEP for Object-to-LED distance.")
                    return
                feature = Kraken3DInspector._picked_feature_info(actor, picker)
                if feature is None:
                    try:
                        center = np.asarray(picker.GetPickPosition(), dtype=float)
                    except Exception:
                        center = None
                else:
                    center = feature[0]
                if center is None or center.size < 3 or not np.all(np.isfinite(center[:3])):
                    self.status_var.set("Could not detect LED object-edge center.")
                    return
                self._legacy_3d_set_step_hover_outline(plotter, None, None)
                self._legacy_3d_set_cursor(plotter, False)
                self.apply_led_object_edge_pick(center[:3])
                return
            requested_label = self._cad_axis_pick_label
            if requested_label is None and not axis_pick_any:
                self.select_step_component(step_label)
                self._legacy_3d_set_selected_step(plotter, step_label)
                return
            if requested_label is not None and requested_label != step_label:
                self.status_var.set(f"CAD STEP picked: {step_label}. Center mode is armed for {str(requested_label).upper()}.")
                return
            feature = Kraken3DInspector._picked_feature_info(actor, picker)
            if feature is None:
                try:
                    center = np.asarray(picker.GetPickPosition(), dtype=float)
                except Exception:
                    center = None
            else:
                center = feature[0]
            if center is None or center.size < 3 or not np.all(np.isfinite(center[:3])):
                self.status_var.set(f"Could not detect {step_label} feature center.")
                return
            self._legacy_3d_set_step_hover_outline(plotter, None, None)
            self._legacy_3d_set_cursor(plotter, False)
            self._cad_axis_pick_any = False
            self.apply_step_axis_pick(step_label, center[:3])
            return
        row_index = scene_info.get("actor_row_map", {}).get(actor_key) if actor_key is not None else None
        ray_index = scene_info.get("actor_ray_map", {}).get(actor_key) if actor_key is not None else None
        requested_label = self._cad_axis_pick_label
        surface_target_label = requested_label
        if surface_target_label is None and axis_pick_any:
            selected_label = getattr(self, "_selected_step_label", None)
            if selected_label in STEP_OVERLAY_LABEL_SET and self._step_path_for_label(str(selected_label)) is not None:
                surface_target_label = str(selected_label)
        if surface_target_label is not None and row_index is not None:
            if bool(getattr(self, "_cad_led_object_edge_pick", False)):
                self.status_var.set("Pick an edge on the LED STEP for Object-to-LED distance.")
                return
            try:
                result = self.center_step_axis_on_surface(str(surface_target_label), int(row_index))
            except Exception as exc:
                self.status_var.set(f"Axis {str(surface_target_label).upper()} failed: {_short_error_message(exc)}")
                self.append_debug(f"Legacy 3D STEP surface-axis pick failed: {exc}")
                return
            self._legacy_3d_set_step_hover_outline(plotter, None, None)
            self._legacy_3d_set_cursor(plotter, False)
            self._legacy_3d_set_selected_row(plotter, int(row_index))
            self._legacy_3d_set_selected_ray(plotter, None)
            row_name = self.rows[int(row_index)].name if 0 <= int(row_index) < len(self.rows) else "Surface"
            if result is not None:
                target = result.get("target", (float("nan"), float("nan"), float("nan")))
                self.status_var.set(
                    f"{str(surface_target_label).upper()} STEP axis centered on S{int(row_index)}: {row_name} "
                    f"at X/Y=({float(target[0]):.6g}, {float(target[1]):.6g}) mm."
                )
            return
        if axis_pick_any and row_index is not None:
            self.status_var.set("Center STEP Axis: click a STEP feature, or select a STEP component before clicking a KrakenOS surface.")
            return
        if ray_index is not None:
            if bool(getattr(plotter, "_kraken_center_row_to_ray_mode", False)):
                self._legacy_3d_apply_center_row_to_ray(plotter, int(ray_index))
                return
            self._legacy_3d_set_selected_row(plotter, None)
            self._legacy_3d_set_selected_ray(plotter, int(ray_index))
            self._select_ray_inspector_ray(int(ray_index))
            self.status_var.set(self._ray_terminal_hint_text(int(ray_index), label=f"3D selected ray {int(ray_index)} in Ray Inspector"))
            return
        if row_index is None:
            self._legacy_3d_set_selected_row(plotter, None)
            self._legacy_3d_set_selected_ray(plotter, None)
            self.status_var.set("3D view ready")
            return
        self._legacy_3d_set_selected_row(plotter, int(row_index))
        self._legacy_3d_set_selected_ray(plotter, None)
        self._select_table_row(int(row_index))
        row_name = self.rows[int(row_index)].name if 0 <= int(row_index) < len(self.rows) else "Surface"
        if bool(getattr(plotter, "_kraken_center_row_to_ray_mode", False)):
            if 0 <= int(row_index) < len(self.rows) and self.rows[int(row_index)].surface in {"Object", "Image"}:
                self.status_var.set("CenterRay: choose a physical surface/CAD row, not Object/Image.")
                return
            setattr(plotter, "_kraken_center_row_to_ray_index", int(row_index))
            self.status_var.set(f"CenterRay: selected S{int(row_index)}: {row_name}. Now click the target ray.")
            return
        if self._file_backed_stl_row_at(int(row_index)) is not None:
            setattr(plotter, "_kraken_stl_placement_row", int(row_index))
            self.status_var.set(f"3D selected CAD/STL row {int(row_index)}: {row_name}. Use the placement buttons, then Done2D or close.")
        else:
            self.status_var.set(f"3D selected row {int(row_index)}: {row_name}")

    def _legacy_3d_start_center_row_to_ray(self, plotter) -> None:
        if plotter is None:
            return
        row_index = getattr(plotter, "_kraken_selected_row", None)
        if row_index is None:
            row_index = self._current_selected_row_index()
        setattr(plotter, "_kraken_center_row_to_ray_mode", True)
        if row_index is not None:
            try:
                row_index = int(row_index)
            except Exception:
                row_index = None
        if row_index is not None and 0 <= row_index < len(self.rows) and self.rows[row_index].surface not in {"Object", "Image"}:
            setattr(plotter, "_kraken_center_row_to_ray_index", row_index)
            self._legacy_3d_set_selected_row(plotter, row_index)
            self.status_var.set(f"CenterRay: selected S{row_index}. Click the ray that should pass through its center.")
            return
        setattr(plotter, "_kraken_center_row_to_ray_index", None)
        self.status_var.set("CenterRay: click the surface/CAD row to move, then click the target ray.")

    def _legacy_3d_apply_center_row_to_ray(self, plotter, ray_index: int) -> None:
        row_index = getattr(plotter, "_kraken_center_row_to_ray_index", None)
        if row_index is None:
            self.status_var.set("CenterRay: click a surface/CAD row first, then click the target ray.")
            return
        try:
            row_index = int(row_index)
            ray_index = int(ray_index)
            result = self.center_surface_row_on_ray(row_index, ray_index)
        except Exception as exc:
            self.status_var.set(f"CenterRay failed: {_short_error_message(exc)}")
            self.append_debug(f"Legacy CenterRay failed: {exc}")
            return
        setattr(plotter, "_kraken_center_row_to_ray_mode", False)
        setattr(plotter, "_kraken_center_row_to_ray_index", None)
        try:
            if self._file_backed_stl_row_at(row_index) is not None:
                self._legacy_3d_update_stl_row_actor(plotter, row_index)
            self._legacy_3d_replace_rays(plotter)
            self._legacy_3d_set_selected_row(plotter, row_index)
            self._legacy_3d_set_selected_ray(plotter, ray_index)
        except Exception as exc:
            self.append_debug(f"Legacy CenterRay refresh failed: {exc}")
        target = result.get("target", (float("nan"), float("nan"), float("nan")))
        self.status_var.set(
            "Centered S{row} on ray {ray} at ({x:.6g}, {y:.6g}, {z:.6g}) mm. "
            "Click Done2D or Update to refresh 2D.".format(
                row=row_index,
                ray=ray_index,
                x=float(target[0]),
                y=float(target[1]),
                z=float(target[2]),
            )
        )

    def _legacy_3d_set_selected_row(self, plotter, row_index: int | None) -> None:
        current = getattr(plotter, "_kraken_selected_row", None)
        if current == row_index:
            return
        scene_info = dict(getattr(plotter, "_kraken_scene", {}) or {})
        row_actor_map = dict(scene_info.get("row_actor_map", {}) or {})
        if current is not None:
            for actor in row_actor_map.get(int(current), []):
                self._legacy_3d_set_actor_highlight(actor, False)
        if row_index is not None:
            for actor in row_actor_map.get(int(row_index), []):
                self._legacy_3d_set_actor_highlight(actor, True)
        setattr(plotter, "_kraken_selected_row", row_index)
        try:
            plotter.render()
        except Exception:
            pass

    def _legacy_3d_set_selected_ray(self, plotter, ray_index: int | None) -> None:
        current = getattr(plotter, "_kraken_selected_ray", None)
        if current == ray_index:
            return
        scene_info = dict(getattr(plotter, "_kraken_scene", {}) or {})
        ray_actor_map = dict(scene_info.get("ray_actor_map", {}) or {})
        if current is not None:
            for actor in ray_actor_map.get(int(current), []):
                Kraken3DInspector._set_ray_actor_selected(actor, False)
        if ray_index is not None:
            for actor in ray_actor_map.get(int(ray_index), []):
                Kraken3DInspector._set_ray_actor_selected(actor, True)
        setattr(plotter, "_kraken_selected_ray", ray_index)
        try:
            plotter.render()
        except Exception:
            pass

    def _legacy_3d_set_selected_step(self, plotter, label: str | None) -> None:
        label = str(label).strip().lower() if label is not None else None
        if label not in STEP_OVERLAY_LABEL_SET:
            label = None
        current = getattr(plotter, "_kraken_selected_step", None)
        if current == label:
            return
        scene_info = dict(getattr(plotter, "_kraken_scene", {}) or {})
        cad_step_actors = dict(scene_info.get("cad_step_actors", {}) or {})
        if current is not None:
            for _kind, actor in list(cad_step_actors.get(current, []) or []):
                Kraken3DInspector._set_step_actor_selected(actor, False)
        if label is not None:
            for _kind, actor in list(cad_step_actors.get(label, []) or []):
                Kraken3DInspector._set_step_actor_selected(actor, True)
        setattr(plotter, "_kraken_selected_step", label)
        try:
            plotter.render()
        except Exception:
            pass

    @staticmethod
    def _legacy_3d_set_actor_highlight(actor, selected: bool) -> None:
        if actor is None:
            return
        try:
            prop = actor.GetProperty()
        except Exception:
            return
        if prop is None:
            return
        base = getattr(actor, "_kraken_base_style", None)
        if not isinstance(base, dict):
            try:
                base = {
                    "edge_visibility": int(prop.GetEdgeVisibility()),
                    "line_width": float(prop.GetLineWidth()),
                    "edge_color": tuple(float(v) for v in prop.GetEdgeColor()),
                    "opacity": float(prop.GetOpacity()),
                    "ambient": float(prop.GetAmbient()),
                    "diffuse": float(prop.GetDiffuse()),
                }
                actor._kraken_base_style = base
            except Exception:
                base = {}
        if selected:
            try:
                prop.SetEdgeVisibility(1)
                prop.SetEdgeColor(1.0, 0.45, 0.05)
                prop.SetLineWidth(max(float(base.get("line_width", 1.0)), 2.5))
                prop.SetOpacity(min(max(float(base.get("opacity", 1.0)), 0.3) + 0.08, 1.0))
                prop.SetAmbient(max(float(base.get("ambient", 0.0)), 0.18))
            except Exception:
                return
            return
        try:
            prop.SetEdgeVisibility(int(base.get("edge_visibility", 0)))
            edge_color = tuple(base.get("edge_color", (0.0, 0.0, 0.0)))
            if len(edge_color) == 3:
                prop.SetEdgeColor(*edge_color)
            prop.SetLineWidth(float(base.get("line_width", 1.0)))
            prop.SetOpacity(float(base.get("opacity", 1.0)))
            prop.SetAmbient(float(base.get("ambient", 0.0)))
            prop.SetDiffuse(float(base.get("diffuse", 1.0)))
        except Exception:
            pass

    def _add_legacy_3d_action_button(
        self,
        plotter,
        *,
        label: str,
        position: tuple[int, int],
        callback,
        value: bool = False,
        color: str = "#2563eb",
    ) -> None:
        plotter.add_checkbox_button_widget(
            callback,
            value=value,
            position=position,
            size=22,
            border_size=3,
            color_on=color,
            color_off=color,
            background_color="white",
        )
        plotter.add_text(
            label,
            position=(position[0] + 28, position[1] + 1),
            font_size=9,
            color="black",
        )

    def _legacy_3d_set_actor_visibility(self, actors, visible: bool, plotter, group: str | None = None) -> None:
        if group:
            state = dict(getattr(plotter, "_kraken_visibility", {}) or {})
            state[group] = bool(visible)
            setattr(plotter, "_kraken_visibility", state)
        for actor in actors:
            try:
                actor.SetVisibility(bool(visible))
            except Exception:
                continue
        plotter.render()

    def _legacy_3d_set_scene_actor_visibility(self, plotter, actor_key: str, visible: bool, group: str) -> None:
        scene_info = dict(getattr(plotter, "_kraken_scene", {}) or {})
        self._legacy_3d_set_actor_visibility(scene_info.get(actor_key, []) or [], visible, plotter, group)

    def _legacy_3d_set_step_visibility(self, plotter, label: str, visible: bool) -> None:
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return
        state = dict(getattr(plotter, "_kraken_visibility", {}) or {})
        state[f"step_{label}"] = bool(visible)
        setattr(plotter, "_kraken_visibility", state)
        scene_info = dict(getattr(plotter, "_kraken_scene", {}) or {})
        actors = list(scene_info.get("cad_step_actors", {}).get(label, []) or [])
        for _kind, actor in actors:
            try:
                actor.SetVisibility(bool(visible))
            except Exception:
                continue
        if not visible and self._selected_step_label == label:
            self._legacy_3d_set_selected_step(plotter, None)
            self._selected_step_label = None
        self.status_var.set(f"{label.upper()} STEP {'shown' if visible else 'hidden'}.")
        try:
            plotter.render()
        except Exception:
            pass

    def _legacy_3d_toggle_full_pupil(self, plotter, state: bool) -> None:
        """Toggle full-pupil ray mode and retrace.

        Only the ray actors are swapped — buttons / lens / mirror actors stay
        put. Rebuilding the entire scene used to stack a fresh Full Pupil
        checkbox on top of the previous one each click, which made the toggle
        appear to be one-way (ON → ON → ON…).
        """
        # PyVista fires the callback on widget creation with the initial value.
        # Skip the no-op so we don't retrace on startup.
        if bool(state) == self._is_full_pupil_mode():
            return
        self.emit_full_ray_var.set(bool(state))
        try:
            self._legacy_3d_replace_rays(plotter)
        except Exception as exc:
            self.append_debug(f"Full Pupil refresh failed: {exc}")

    def _legacy_3d_replace_rays(self, plotter) -> None:
        """Rebuild only the ray actors in the existing 3D scene, in place."""
        scene_info = getattr(plotter, "_kraken_scene", None)
        if not isinstance(scene_info, dict):
            scene_info = {}
            setattr(plotter, "_kraken_scene", scene_info)
        ray_actors = scene_info.setdefault("ray_actors", [])
        for actor in list(ray_actors):
            try:
                plotter.renderer.RemoveActor(actor)
            except Exception:
                pass
        ray_actors.clear()
        scene_info["actor_ray_map"] = {}
        scene_info["ray_actor_map"] = {}
        setattr(plotter, "_kraken_selected_ray", None)
        system, rays = self._build_preview_system_and_rays()
        scene_bundle = self._last_scene_bundle
        setattr(plotter, "_kraken_system", system)
        setattr(plotter, "_kraken_rays", rays)
        setattr(plotter, "_kraken_scene_bundle", scene_bundle)
        rays_visible = bool(dict(getattr(plotter, "_kraken_visibility", {}) or {}).get("rays", True))
        ray_radius = self._legacy_3d_ray_radius(system, rays)
        if scene_bundle is not None:
            ray_center, ray_scene_radius = scene_display_center_radius(scene_bundle)
        else:
            ray_center, ray_scene_radius = self._scene_center_radius_from_bounds(plotter.bounds)
        paths_by_ray_index = self._scene_ray_path_by_index(scene_bundle)
        suppressed_endpoint_count = 0
        for ray_index, color, ray_pts, terminal_status in self._iter_3d_scene_ray_records(rays, scene_bundle):
            ray_path = paths_by_ray_index.get(int(ray_index))
            terminal_target = self._missed_detector_target_for_path(scene_bundle, ray_path)
            terminal_direction = self._terminal_display_direction_for_path(ray_path)
            display_ray_pts, _was_bounded = self._bounded_3d_ray_points_for_display(
                ray_pts,
                ray_center,
                ray_scene_radius,
                terminal_status=terminal_status,
                terminal_target=terminal_target,
                terminal_direction=terminal_direction,
            )
            line = self._ray_segment_mesh_for_3d_display(
                display_ray_pts,
                vertex_inset=self._ray_vertex_display_inset(ray_scene_radius),
            )
            if line is None:
                continue
            if int(getattr(line, "n_points", 0)) < 2:
                continue
            style = ThreeDSceneToolsMixin._ray_terminal_3d_style(color, terminal_status)
            actor = plotter.add_mesh(
                line,
                color=style["line_color"],
                opacity=float(style["line_opacity"]),
                line_width=float(style["line_width"]),
                pickable=True,
            )
            actor_key = Kraken3DInspector._actor_key(actor)
            if actor_key is not None:
                scene_info["actor_ray_map"][actor_key] = int(ray_index)
                scene_info["ray_actor_map"].setdefault(int(ray_index), []).append(actor)
            try:
                actor.SetPickable(True)
                prop = actor.GetProperty()
                if prop is not None:
                    actor._kraken_ray_select_style = {
                        "color": tuple(float(v) for v in prop.GetColor()),
                        "line_width": float(prop.GetLineWidth()),
                        "opacity": float(prop.GetOpacity()),
                        "ambient": float(prop.GetAmbient()),
                        "diffuse": float(prop.GetDiffuse()),
                    }
            except Exception:
                pass
            try:
                actor.SetVisibility(rays_visible)
            except Exception:
                pass
            ray_actors.append(actor)
            if not self._should_draw_3d_terminal_endpoint(
                terminal_status,
                show_terminal_diagnostics=bool(self.show_terminal_diagnostics_var.get()),
            ):
                suppressed_endpoint_count += 1
                continue
            try:
                endpoint = np.asarray(display_ray_pts[-1], dtype=float).reshape(-1)[:3]
                if endpoint.size >= 3 and np.all(np.isfinite(endpoint)):
                    marker = pv.Sphere(
                        radius=max(float(ray_radius) * float(style["endpoint_scale"]), 0.08),
                        center=tuple(endpoint[:3]),
                        theta_resolution=16 if terminal_status == "missed_detector" else 12,
                        phi_resolution=10 if terminal_status == "missed_detector" else 8,
                    )
                    marker_actor = plotter.add_mesh(
                        marker,
                        color=style["endpoint_color"],
                        opacity=0.96,
                        smooth_shading=False,
                        pickable=True,
                    )
                    marker_key = Kraken3DInspector._actor_key(marker_actor)
                    if marker_key is not None:
                        scene_info["actor_ray_map"][marker_key] = int(ray_index)
                        scene_info["ray_actor_map"].setdefault(int(ray_index), []).append(marker_actor)
                    try:
                        marker_actor.SetVisibility(rays_visible)
                    except Exception:
                        pass
                    ray_actors.append(marker_actor)
            except Exception:
                pass
        if suppressed_endpoint_count:
            self.append_debug(f"Legacy 3D suppressed {suppressed_endpoint_count} non-physical escaped/missed terminal endpoint markers.")
        try:
            plotter.render()
        except Exception:
            pass

    def _save_legacy_3d_screenshot(self, plotter) -> None:
        try:
            default_name = f"kraken_3d_{time.strftime('%Y%m%d_%H%M%S')}.png"
            try:
                SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            selected_path = filedialog.asksaveasfilename(
                parent=self,
                title="Save 3D view as PNG",
                initialdir=str(SCREENSHOT_DIR),
                initialfile=default_name,
                defaultextension=".png",
                filetypes=[("PNG image", "*.png")],
            )
            if not selected_path:
                self.status_var.set("3D PNG save cancelled")
                return
            image_path = Path(selected_path)
            system = getattr(plotter, "_kraken_system", None)
            rays = getattr(plotter, "_kraken_rays", None)
            scene_bundle = getattr(plotter, "_kraken_scene_bundle", None)
            if system is None or rays is None:
                raise RuntimeError("3D scene data unavailable for clean screenshot")
            self._last_scene_bundle = scene_bundle if isinstance(scene_bundle, SceneBundle) else self._last_scene_bundle
            clean_plotter = self._build_clean_legacy_3d_plotter(system, rays)
            clean_scene = dict(getattr(clean_plotter, "_kraken_scene", {}) or {})
            visibility = dict(getattr(plotter, "_kraken_visibility", {}) or {})
            if not visibility.get("rays", True):
                self._legacy_3d_set_actor_visibility(clean_scene.get("ray_actors", []), False, clean_plotter)
            if not visibility.get("mirrors", True):
                self._legacy_3d_set_actor_visibility(clean_scene.get("mirror_actors", []), False, clean_plotter)
            if not visibility.get("lenses", True):
                self._legacy_3d_set_actor_visibility(clean_scene.get("lens_actors", []), False, clean_plotter)
            if not visibility.get("helpers", True):
                self._legacy_3d_set_actor_visibility(clean_scene.get("helper_actors", []), False, clean_plotter)
            try:
                clean_plotter.camera_position = plotter.camera_position
                clean_plotter.camera.parallel_projection = bool(plotter.camera.parallel_projection)
                clean_plotter.camera.parallel_scale = float(plotter.camera.parallel_scale)
            except Exception:
                self._set_legacy_3d_camera(clean_plotter, "iso")
            clean_plotter.screenshot(str(image_path))
            try:
                rw = getattr(clean_plotter, "render_window", None)
                if rw is not None:
                    rw.Finalize()
                clean_plotter.close()
            except Exception:
                pass
            self.status_var.set(f"Saved 3D PNG: {image_path.name}")
            self.append_progress(f"Saved 3D PNG: {image_path}")
        except Exception as exc:
            self.append_debug(f"3D screenshot failed: {exc}")
            self.status_var.set(f"3D screenshot failed: {_short_error_message(exc)}")

    @staticmethod
    def _legacy_3d_camera_preset_from_display_orientation(orientation: str) -> str:
        plane = normalize_projection_plane(orientation)
        if plane == "XZ":
            return "xz"
        if plane == "XY":
            return "top"
        return "yz"

    @staticmethod
    def _set_legacy_3d_camera(plotter, preset: str) -> None:
        cx, cy, cz = plotter.center
        bounds = np.asarray(plotter.bounds, dtype=float)
        span_x = float(bounds[1] - bounds[0]) if bounds.size >= 2 else 0.0
        span_y = float(bounds[3] - bounds[2]) if bounds.size >= 4 else 0.0
        span_z = float(bounds[5] - bounds[4]) if bounds.size >= 6 else 0.0
        span = max(span_x, span_y, span_z, 1.0)
        distance = max(span * 2.6, 180.0)
        try:
            width, height = plotter.window_size
            aspect = max(float(width) / max(float(height), 1.0), 0.1)
        except Exception:
            aspect = 1.4

        def orthographic_scale(horizontal_span: float, vertical_span: float) -> float:
            horizontal_scale = float(horizontal_span) / (2.0 * aspect)
            vertical_scale = float(vertical_span) * 0.5
            return max(horizontal_scale, vertical_scale, 1.0) * 1.08

        if preset == "yz":
            position = (cx - distance, cy, cz)
            view_up = (0.0, 1.0, 0.0)
            parallel_scale = orthographic_scale(span_z, span_y)
        elif preset == "top":
            # Exact top view. This used to conflict only because VTK binds the numeric `3` key to stereo.
            position = (cx, cy, cz + distance)
            view_up = (0.0, 1.0, 0.0)
            parallel_scale = orthographic_scale(span_x, span_y)
        elif preset == "bottom":
            position = (cx, cy, cz - distance)
            view_up = (0.0, 1.0, 0.0)
            parallel_scale = orthographic_scale(span_x, span_y)
        elif preset == "xz":
            position = (cx, cy + distance, cz)
            view_up = (1.0, 0.0, 0.0)
            parallel_scale = orthographic_scale(span_z, span_x)
        else:
            position = (cx - distance, cy + distance * 0.55, cz + distance * 0.75)
            view_up = (0.0, 1.0, 0.0)
            parallel_scale = None
        plotter.camera_position = [position, (cx, cy, cz), view_up]
        try:
            plotter.camera.parallel_projection = parallel_scale is not None
            if parallel_scale is not None:
                plotter.camera.parallel_scale = float(parallel_scale)
        except Exception:
            pass
        plotter.reset_camera_clipping_range()
        plotter.set_background("white", top="white")
        plotter.render()

    def _open3d_trace_refresh_service(self) -> Open3DTraceRefreshService:
        service = getattr(self, "_open3d_trace_refresh_service_instance", None)
        if service is None:
            service = Open3DTraceRefreshService(self)
            self._open3d_trace_refresh_service_instance = service
        return service

    def _open3d_step_state_service(self) -> Open3DStepStateService:
        service = getattr(self, "_open3d_step_state_service_instance", None)
        if service is None:
            service = Open3DStepStateService(self, valid_labels=STEP_OVERLAY_LABEL_SET)
            self._open3d_step_state_service_instance = service
        return service

    def _refresh_3d_inspector_if_open(self, *, system=None, rays=None, scene_bundle: SceneBundle | None = None) -> None:
        try:
            self._open3d_trace_refresh_service().sync_open_inspector(
                system=system,
                rays=rays,
                scene_bundle=scene_bundle,
                reset_camera=False,
            )
        except Exception as exc:
            self.append_debug(f"3D inspector sync failed: {exc}")
