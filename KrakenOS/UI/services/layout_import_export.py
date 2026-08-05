"""Layout file, Zemax, stock-lens, and export workflows.

This mixin keeps file import/export and row reconstruction workflows available
on ``KrakenLayoutEditor`` while removing the bulky persistence/import block from
``layout_editor.py``.  The methods still operate on editor state, but dialogs,
format conversion, STEP export orchestration, and example reconstruction are no
longer embedded directly in the main editor coordinator.
"""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
import io
import os
from pathlib import Path
from queue import Empty, Queue
import re
import sys
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox
import warnings

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.custom_surfaces import encode_custom_surface_value
from KrakenOS.UI.layout_library import (
    example_file_has_import_side_effects,
    example_file_is_menu_loadable,
    load_python_data as _load_python_data,
    python_code_defines_layout_data,
)
from KrakenOS.UI.panels.main_glass_catalog_browser_dialog import MainGlassCatalogBrowserDialog
from KrakenOS.UI.panels.main_lens_drawing_dialogs import MainLensDrawingDialogs
from KrakenOS.UI.panels.main_stock_lens_importer_dialog import MainStockLensImporterDialog
from KrakenOS.UI.scene_row_mapping import SOURCE_ROW_ORDER_AFTER_OBJECT
from KrakenOS.UI.services.beam_scatter_metadata import (
    BEAM_SPLITTER_ADVANCED_ATTR,
    DIFFUSE_SCATTER_ADVANCED_ATTR,
    DIFFUSE_SCATTER_DEFAULT_SETTINGS,
    _beam_splitter_coating_for_settings,
    _normalize_beam_splitter_settings,
    _normalize_diffuse_scatter_settings,
)
from KrakenOS.UI.services.cad_step_export import (
    _write_meshes_to_faceted_step,
    _write_step_with_analytic_surfaces,
    _write_step_with_cad_shapes_and_rays,
)
from KrakenOS.UI.services.catalog_metadata import (
    _available_stock_lens_catalogs,
    _catalog_surface_keys,
    _load_stock_lens_catalog,
    _stock_lens_summary,
)
from KrakenOS.UI.services.advanced_surface_attrs import (
    ADVANCED_SURFACE_ATTR_NAMES,
    EXAMPLE_SUPPORTED_SURFACE_ATTRS,
    REFLECTIVE_PROXY_SURFACES,
    _advanced_surface_attrs_from_spec,
    _canonical_advanced_surface_attr,
)
from KrakenOS.UI.services.layout_file_writer import LayoutFileWriterService
from KrakenOS.UI.services.surface_value_parsing import _coerce_bounds, _coerce_opt_flag
from KrakenOS.UI.source_trace_helpers import SOURCE_MODEL_ZEMAX_RAYFILE
from KrakenOS.UI.surface_table_model import SurfaceRow, insert_surface_rows as _surface_table_insert_surface_rows
from KrakenOS.UI.trace_intent import BEAM_SPLITTER_SURFACE, DIFFUSE_OBJECT_SURFACE, OBJECT_TARGET_SURFACE
from KrakenOS.UI.zemax_rayfile import find_zemax_nsc_source_files, summarize_zemax_rayfile
from KrakenOS.UI.zemax_wavefront import load_zemax_wavefront_map

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ATTACHMENT_DIR = PROJECT_ROOT / "attachment"
LAYOUTS_DIR = Path(__file__).resolve().parents[1] / "common_optical_layouts"
EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "Examples"
LEGACY_TESTING_DIR = PROJECT_ROOT / "testing"
SCREENSHOT_DIR = ATTACHMENT_DIR
ZEMAX_ATTACHMENT_DIR = ATTACHMENT_DIR / "zemax"


def _preferred_existing_dir(*candidates: Path | str) -> Path:
    paths = [Path(candidate).expanduser() for candidate in candidates]
    for path in paths:
        if path.exists():
            return path
    return paths[0]


ATTACHMENT_LENS_DIR = _preferred_existing_dir(ATTACHMENT_DIR / "Lens", ATTACHMENT_DIR / "lens")
ELEMENT_ADVANCED_ATTR = "Element"


class _CapturedExample(Exception):
    def __init__(self, surfaces):
        super().__init__("captured KrakenOS example")
        self.surfaces = surfaces


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


def _short_error_message(exc: Exception, limit: int = 220) -> str:
    return _layout_module()._short_error_message(exc, limit=limit)


def _promoted_body_label_and_axis(advanced: dict) -> tuple[str, tuple[float, float, float] | None]:
    """Pull the promotion step-label and optical axis from a row's advanced dict.

    Used by the bugs/0021 body-STL regeneration so a rebuilt cache reproduces
    the same label-tagged filename and (for analytic bodies) the same +Z
    re-orientation the original promote applied. Falls back to ``"optical"``
    and no axis when the metadata is absent.
    """
    label = "optical"
    optical_axis: tuple[float, float, float] | None = None
    for promo_key in ("StepOverlayPromotion", "StepAnalyticPromotion"):
        promotion = advanced.get(promo_key)
        if not isinstance(promotion, dict):
            continue
        label_value = promotion.get("step_label")
        if isinstance(label_value, str) and label_value.strip():
            label = label_value.strip().lower()
        axis_value = promotion.get("optical_axis")
        if isinstance(axis_value, (list, tuple)) and len(axis_value) == 3:
            try:
                optical_axis = (float(axis_value[0]), float(axis_value[1]), float(axis_value[2]))
            except Exception:
                optical_axis = None
    return label, optical_axis


def _shared_setup(metal_catalogs=None):
    return _layout_module()._shared_setup(metal_catalogs=metal_catalogs)


def _load_zemax_zmx_data(path: Path) -> dict:
    return _layout_module()._load_zemax_zmx_data(path)


def _stock_lens_trace_glass(glass: str, catalog_surface: dict) -> tuple[str, str | None]:
    return _layout_module()._stock_lens_trace_glass(glass, catalog_surface)


def _advanced_surface_attr_names() -> tuple[str, ...]:
    return tuple(ADVANCED_SURFACE_ATTR_NAMES)


def _example_supported_surface_attrs() -> set[str]:
    return set(EXAMPLE_SUPPORTED_SURFACE_ATTRS)


def _reflective_proxy_surfaces() -> set[str]:
    return set(REFLECTIVE_PROXY_SURFACES)


class LayoutImportExportMixin:
    def _main_glass_catalog_browser_dialog(self) -> MainGlassCatalogBrowserDialog:
        dialog = self.__dict__.get("_main_glass_catalog_browser_dialog_instance")
        if dialog is None:
            dialog = MainGlassCatalogBrowserDialog(
                self,
                shared_setup=_shared_setup,
                short_error_message=_short_error_message,
            )
            self._main_glass_catalog_browser_dialog_instance = dialog
        return dialog

    def _glass_catalog_records(self) -> list[dict[str, object]]:
        return self._main_glass_catalog_browser_dialog()._glass_catalog_records()

    def open_glass_catalog_browser(self) -> None:
        self._main_glass_catalog_browser_dialog().open_glass_catalog_browser()

    def open_mtf_from_image_dialog(self) -> None:
        """Measure MTF from a captured USAF-1951 image (KrakenOS.USAFMTF) -- the interactive
        "draw ROIs on the image" dialog: load a raster capture, drag a rectangle over each three-bar
        element, Compute to fit + plot the MTF curve, Save CSV."""
        from KrakenOS.UI.panels.mtf_from_image_dialog import open_mtf_from_image_dialog
        open_mtf_from_image_dialog(self)

    @staticmethod
    def _available_zemax_rayfile_path(path: Path) -> Path:
        path = Path(path).expanduser()
        if path.exists():
            return path
        name = path.name
        for old, new in (("_5M_", "_500k_"), ("_5M_", "_100k_"), ("_500k_", "_100k_")):
            if old in name:
                candidate = path.with_name(name.replace(old, new))
                if candidate.exists():
                    return candidate
        return path

    def _load_zemax_rayfile_source_path(self, path: Path, refs, *, source: str = "file") -> None:
        path = Path(path)
        source_specs: list[dict[str, object]] = []
        missing: list[Path] = []
        sample_count = max(1, int(self._current_ray_count() if hasattr(self, "ray_count_var") else 201))
        sample_count = max(sample_count, 201)
        first_wavelength = None
        for ref in refs:
            rayfile_path = self._available_zemax_rayfile_path(Path(ref.rayfile_path))
            if not rayfile_path.exists():
                missing.append(rayfile_path)
                continue
            summary = summarize_zemax_rayfile(rayfile_path)
            wavelength = float(ref.wavelength_um) if ref.wavelength_um is not None else float(self._current_wavelength())
            if first_wavelength is None:
                first_wavelength = wavelength
            name = rayfile_path.stem.replace("_", " ")
            source_specs.append(
                {
                    "source_id": f"source:zemax-rayfile:{len(source_specs) + 1}",
                    "name": f"Zemax Rayfile {len(source_specs) + 1}: {name}",
                    "role": "illumination",
                    "model": SOURCE_MODEL_ZEMAX_RAYFILE,
                    "enabled": True,
                    "physical": True,
                    "origin": [0.0, 0.0, 0.0],
                    "direction": [0.0, 0.0, 1.0],
                    "ray_count": sample_count,
                    "power": 1.0,
                    "wavelength": wavelength,
                    "rayfile_path": str(rayfile_path),
                    "source_zmx_path": str(path),
                    "spectrum_path": "" if ref.spectrum_path is None else str(ref.spectrum_path),
                    "record_count": int(summary.record_count),
                    "header_record_count": int(summary.header_record_count or summary.record_count),
                    "rayfile_label": summary.source_label,
                    "wavelength_min_um": ref.wavelength_min_um,
                    "wavelength_max_um": ref.wavelength_max_um,
                }
            )
        if missing or not source_specs:
            message = "\n".join(str(item) for item in missing[:4])
            if len(missing) > 4:
                message += f"\n... and {len(missing) - 4} more"
            messagebox.showerror(
                "Zemax rayfile source import failed",
                f"The Zemax non-sequential file references missing ray database file(s):\n\n{message}",
                parent=self,
            )
            self.status_var.set("Zemax rayfile import failed: missing .DAT ray database.")
            return

        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception:
            pass
        self._begin_history_capture()
        self._reset_complete_layout_runtime_state(close_viewers=True)
        self.current_layout_file = None
        self.rows = [
            SurfaceRow(surface="Object", name="Object", thickness=25.0, diameter=250.0, glass="AIR"),
            SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=250.0, glass="AIR"),
        ]
        settings = {
            "object_mode": "Finite",
            "display_orientation": "YZ",
            "wavelength": f"{float(first_wavelength or self._current_wavelength()):g}",
            "ray_count": str(sample_count),
            "source_model": SOURCE_MODEL_ZEMAX_RAYFILE,
            "source_power": "1.0",
            "source_x": "0.0",
            "source_y": "0.0",
            "source_z": "0.0",
            "source_l": "0.0",
            "source_m": "0.0",
            "source_n": "1.0",
            "scene_sources": source_specs,
            "scene_row_order": SOURCE_ROW_ORDER_AFTER_OBJECT,
            "trace_mode": "Auto",
            "nonseq_target_surface": "Auto",
            "analysis_surface": "Auto",
            "aperture_type": "EPD",
            "aperture_value": "250",
            "field_type": "Object Height",
            "field_value": "0.0",
            "field_count": "1",
        }
        self._apply_layout_settings(settings)
        self._normalize_special_rows()
        self._sync_table()
        self.layout_var.set("Common Optical Layout")
        self.machine_vision_var.set("Machine Vision Lens")
        self.example_var.set("Examples")
        self._commit_history_capture()
        self.refresh_plot(suppress_analysis=True)
        source_label = "example" if source == "example" else "file"
        total_records = sum(int(spec.get("record_count", 0) or 0) for spec in source_specs)
        self.status_var.set(
            f"Imported Zemax NSC rayfile {source_label} {path.name}: "
            f"{len(source_specs)} illumination source(s), {total_records:,} source rays available, "
            f"{sample_count} sampled rays per source."
        )

    def _load_zemax_prescription_path(self, path: Path, *, source: str = "file") -> None:
        path = Path(path)
        try:
            source_refs = find_zemax_nsc_source_files(path)
        except Exception:
            source_refs = []
        if source_refs:
            self._load_zemax_rayfile_source_path(path, source_refs, source=source)
            return
        try:
            info = _load_zemax_zmx_data(path)
        except Exception as exc:
            messagebox.showerror(
                "Zemax import failed",
                f"Could not import {path.name}.\n\n{_short_error_message(exc)}",
                parent=self,
            )
            self.status_var.set(f"Zemax import failed: {_short_error_message(exc)}")
            return

        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception:
            pass
        self._begin_history_capture()
        self.current_layout_file = None
        self.rows = self._normalized_rows_copy([self._row_from_layout_item(item) for item in info["surfaces"]])
        self._auto_assign_missing_elements(self.rows)
        self._apply_layout_settings(info.get("settings", {}))
        self._normalize_special_rows()
        # Zemax NSC imports often reference CAD geometry files that the
        # user no longer has -- prompt before the first table sync /
        # plot refresh so a relocation feeds straight into the first
        # render. Best-effort wrapped: a broken prompt must not block
        # an otherwise-successful import.
        try:
            self._prompt_for_missing_cad_assets()
        except Exception:
            pass
        self._sync_table()
        self.layout_var.set("Common Optical Layout")
        self.machine_vision_var.set("Machine Vision Lens")
        self.example_var.set("Examples")
        self._commit_history_capture()
        self.refresh_plot(suppress_analysis=True)
        source_label = "example" if source == "example" else "file"
        self.status_var.set(
            f"Imported Zemax {source_label} {path.name} ({len(self.rows)} surfaces). Save As to store a Kraken layout."
        )

    def load_zemax_example_file(self, path: Path) -> None:
        self._load_zemax_prescription_path(Path(path), source="example")

    def import_zemax_file(self) -> None:
        initial_dirs = [
            ATTACHMENT_DIR,
            ZEMAX_ATTACHMENT_DIR,
            ATTACHMENT_LENS_DIR,
            LEGACY_TESTING_DIR / "zemax",
            Path.home() / "Lens",
            Path.home(),
        ]
        initial_dir = next((candidate for candidate in initial_dirs if candidate.exists()), Path.home())
        path = filedialog.askopenfilename(
            title="Import Zemax prescription or NSC source file",
            initialdir=str(initial_dir),
            filetypes=[
                ("Zemax prescription/source", "*.zmx *.ZMX"),
                ("All files", "*"),
            ],
            parent=self,
        )
        if not path:
            return
        self._load_zemax_prescription_path(Path(path), source="file")

    def import_zemax_wavefront_map(self) -> None:
        initial_dirs = [
            ATTACHMENT_DIR,
            ATTACHMENT_LENS_DIR,
            LEGACY_TESTING_DIR,
            Path.home() / "Lens",
            Path.home(),
        ]
        initial_dir = next((path for path in initial_dirs if path.exists()), Path.home())
        path = filedialog.askopenfilename(
            title="Import Zemax Wavefront Map text export",
            initialdir=str(initial_dir),
            filetypes=[
                ("Zemax Wavefront Map text", "*.txt *.TXT"),
                ("All files", "*"),
            ],
            parent=self,
        )
        if not path:
            return
        try:
            reference = load_zemax_wavefront_map(path)
        except Exception as exc:
            messagebox.showerror(
                "Zemax Wavefront Map import failed",
                f"Could not import {Path(path).name}.\n\n{_short_error_message(exc)}",
                parent=self,
            )
            self.status_var.set(f"Zemax Wavefront Map import failed: {_short_error_message(exc)}")
            return
        self._zemax_wavefront_reference = reference
        self._last_zemax_wavefront_comparison = None
        message = (
            f"Imported Zemax Wavefront Map {Path(reference.path).name}: "
            f"{reference.shape[1]}x{reference.shape[0]}, lambda={reference.wavelength_um:.6g} um, "
            f"PV={reference.pv_waves:.6g} waves, RMS={reference.rms_waves:.6g} waves."
        )
        self.append_debug(message)
        self.status_var.set(message + " Run WFront/Update to compare.")
        self._mark_plot_update_pending()

    def clear_zemax_wavefront_reference(self) -> None:
        self._zemax_wavefront_reference = None
        self._last_zemax_wavefront_comparison = None
        self.status_var.set("Zemax Wavefront Map reference cleared.")
        self._mark_plot_update_pending()

    @staticmethod
    def _stock_lens_rows_from_catalog_item(
        part_number: str,
        catalog_item: dict,
        *,
        inverse: bool = False,
        gap_after: float = 25.0,
    ) -> list[SurfaceRow]:
        surfaces = Kos.cat2surf(catalog_item, inverse=bool(inverse), Glass="AIR")
        if not surfaces:
            raise ValueError(f"{part_number} does not contain importable optical surfaces.")
        surface_keys = [
            key
            for key in _catalog_surface_keys(catalog_item)
            if catalog_item[key].get("Diameter") not in (None, 0)
        ]
        if inverse:
            surface_keys = list(reversed(surface_keys))
        rows: list[SurfaceRow] = []
        for index, surface in enumerate(surfaces, start=1):
            surface.Name = f"{part_number} S{index}"
            row = LayoutImportExportMixin._row_from_surface(surface, 1, 3)
            row.element = str(part_number).strip()
            if row.surface in {"Object", "Image"}:
                row.surface = "Standard"
            row.name = str(surface.Name)
            source_surface = catalog_item.get(surface_keys[index - 1], {}) if index <= len(surface_keys) else {}
            trace_glass, glass_note = _stock_lens_trace_glass(row.glass, source_surface)
            if glass_note:
                row.advanced = dict(row.advanced or {})
                row.advanced["Note"] = glass_note
            row.glass = trace_glass
            rows.append(row)
        rows[-1].thickness = float(gap_after)
        rows[-1].glass = "AIR"
        note = f"Imported from stock lens catalog part {part_number}."
        if inverse:
            note += " Reversed orientation."
        rows[0].advanced = dict(rows[0].advanced or {})
        existing_note = str(rows[0].advanced.get("Note", "") or "").strip()
        rows[0].advanced["Note"] = f"{note} {existing_note}".strip()
        return rows

    def _insert_surface_rows(self, new_rows: list[SurfaceRow], insert_after: int | None = None) -> int:
        if not new_rows:
            return -1
        self.rows, insert_at = _surface_table_insert_surface_rows(
            self.rows,
            new_rows,
            insert_after=insert_after,
        )
        self._normalize_special_rows()
        self._sync_table()
        items = self.table.get_children()
        selected_items = items[insert_at : insert_at + len(new_rows)]
        if selected_items:
            self.table.selection_set(selected_items)
            self.table.focus(selected_items[0])
            self.table.see(selected_items[0])
        return insert_at

    def _main_stock_lens_importer_dialog(self) -> MainStockLensImporterDialog:
        dialog = self.__dict__.get("_main_stock_lens_importer_dialog_instance")
        if dialog is None:
            dialog = MainStockLensImporterDialog(
                self,
                available_stock_lens_catalogs=_available_stock_lens_catalogs,
                load_stock_lens_catalog=_load_stock_lens_catalog,
                stock_lens_summary=_stock_lens_summary,
                short_error_message=_short_error_message,
            )
            self._main_stock_lens_importer_dialog_instance = dialog
        return dialog

    def open_stock_lens_importer(self, *, path_placement: dict[str, object] | None = None) -> None:
        self._main_stock_lens_importer_dialog().open_stock_lens_importer(path_placement=path_placement)

    def open_layout(self) -> None:
        if ATTACHMENT_DIR.exists():
            initial_dir = ATTACHMENT_DIR
        elif LAYOUTS_DIR.exists():
            initial_dir = LAYOUTS_DIR
        else:
            initial_dir = PROJECT_ROOT
        path = filedialog.askopenfilename(
            title="Open Kraken layout",
            initialdir=str(initial_dir),
            filetypes=[("Python layout", "*.py")],
        )
        if not path:
            return
        self.current_layout_file = Path(path)
        # bugs/0375: opening a real file ties the layout to it (clears any prior
        # transient-import marker), so Save writes here and its session restores.
        self._layout_is_unsaved_import = False
        info: dict[str, object] = {"surfaces": [], "settings": {}}
        try:
            info = _load_python_data(Path(path))
            self.rows = self._normalized_rows_copy([self._row_from_layout_item(item) for item in info["surfaces"]])
            # bugs/0559: heal a negative gap saved before bugs/0550, pose-preservingly.
            _healed = self._heal_negative_gaps_on_load(self.rows)
            if _healed:
                _text = ", ".join(f"S{h['row_index']} ({h['name']}) {h['thickness']:+g} mm" for h in _healed)
                try:
                    self.append_debug(
                        f"Repaired {len(_healed)} negative gap(s) saved in this layout: {_text}. "
                        "Nothing moved (the gap is returned through desp_z); re-save to persist."
                    )
                except Exception:
                    pass
        except Exception:
            surfaces = self._extract_surfaces_from_example(Path(path))
            self.rows = self._normalized_rows_copy(
                [self._row_from_surface(surface, index, len(surfaces)) for index, surface in enumerate(surfaces)]
            )
        self._auto_assign_missing_elements(self.rows)
        self._apply_layout_settings(info.get("settings", {}))
        self._normalize_special_rows()
        # Surface missing CAD references *before* the first table sync
        # and plot refresh -- if the user relocates files in the dialog,
        # the subsequent table + plot reflect the new paths and no
        # silent fallback ever fires. The prompt itself is best-effort:
        # any failure (missing Tk display in headless tests, scanner
        # exception on a malformed row) is swallowed so a broken prompt
        # never blocks the load.
        # bugs/0021: a promoted body STL is a *derived* artefact. Before we
        # complain about it being missing, silently rebuild it from its source
        # STEP when that source is present (the usual case -- the source lives
        # in the synced attachment/ folder). The dialog then only fires for a
        # genuinely missing *source*, not a regenerable cache file.
        try:
            self._regenerate_missing_optical_solid_caches()
        except Exception:
            pass
        try:
            self._prompt_for_missing_cad_assets()
        except Exception:
            pass
        self._sync_table()
        self.refresh_plot(suppress_analysis=True)
        self._mark_saved_state()
        self.status_var.set(f"Opened {Path(path).name}. Click Update to run analysis.")

    def _portable_cache_path(self, path_text: str) -> str:
        """Return ``path_text`` relative to the project root when it lives
        under it (the synced ``attachment/`` cache), else unchanged.

        Keeps regenerated-cache references portable across machines / users:
        a project-relative ``attachment/cad_cache/...`` path resolves the same
        on every checkout, where an absolute /home/<user>/... path would not.
        """
        try:
            resolved = Path(path_text).expanduser().resolve()
            return str(resolved.relative_to(PROJECT_ROOT))
        except Exception:
            return str(path_text)

    def _regenerate_missing_optical_solid_caches(self) -> None:
        """bugs/0021: rebuild any promoted body STL whose cache file is missing
        but whose source STEP is still present, BEFORE the missing-assets scan.

        Covers both the file-backed optical solid (``Solid_3d_stl`` <-
        ``OpticalSolidSourcePath``) and the analytic-promoted body
        (``StepAnalyticBodyStlPath`` <- ``StepAnalyticPromotion.source_step_path``).
        The regenerated STL is written under the synced ``attachment/`` cache
        and the row's path is rewritten project-relative. Best-effort: any
        failure leaves the row for the safety-net analytic fallback (the system
        build neutralises a still-missing Solid_3d_stl) and the dialog.
        """
        try:
            from KrakenOS.UI.layout_editor import _resolve_project_file_path
        except Exception:
            return
        # (derived cache key, source key, source is nested under a promotion dict)
        pairs = (
            ("Solid_3d_stl", "OpticalSolidSourcePath", False),
            ("StepAnalyticBodyStlPath", "StepAnalyticPromotion.source_step_path", True),
        )
        service = None
        for row in getattr(self, "rows", []) or []:
            advanced = getattr(row, "advanced", None)
            if not isinstance(advanced, dict):
                continue
            for cache_key, source_key, nested in pairs:
                cache_value = advanced.get(cache_key)
                if not isinstance(cache_value, str) or cache_value.strip() in {"", "None"}:
                    continue
                try:
                    if _resolve_project_file_path(cache_value).exists():
                        continue  # cache present -- nothing to regenerate
                except Exception:
                    continue
                if nested:
                    outer, _, inner = source_key.partition(".")
                    nested_dict = advanced.get(outer)
                    source_value = nested_dict.get(inner) if isinstance(nested_dict, dict) else None
                else:
                    source_value = advanced.get(source_key)
                if not isinstance(source_value, str) or not source_value.strip():
                    continue
                try:
                    source_path = _resolve_project_file_path(source_value)
                except Exception:
                    continue
                if not source_path.exists():
                    continue  # source also gone -- leave it for the dialog
                label, optical_axis = _promoted_body_label_and_axis(advanced)
                if service is None:
                    try:
                        service = self._step_overlay_promotion_service()
                    except Exception:
                        return
                try:
                    new_stl = service.regenerate_promoted_body_stl_from_source(
                        source_path,
                        label=label,
                        # the file-backed Solid_3d_stl body is stored without the
                        # optical-axis re-orientation, so only pass it for the
                        # analytic body to match how each was originally written.
                        optical_axis=optical_axis if cache_key == "StepAnalyticBodyStlPath" else None,
                    )
                except Exception:
                    new_stl = None
                if not new_stl:
                    continue
                advanced[cache_key] = self._portable_cache_path(new_stl)
                try:
                    self._clear_missing_path(new_stl)
                    self._clear_missing_path(cache_value)
                except Exception:
                    pass

    def _prompt_for_missing_cad_assets(self) -> None:
        """Show the Missing CAD assets dialog if the layout has any.

        Imported lazily so headless harnesses (no Tk display) that call
        ``open_layout`` only to verify parsing don't drag in the panel
        module just to confirm the scanner found zero entries.
        """
        from KrakenOS.UI.services.missing_assets_scan import scan_missing_assets

        assets = scan_missing_assets(self.rows, editor=self)
        if not assets:
            return
        from KrakenOS.UI.panels.missing_assets_dialog import MissingAssetsDialog

        MissingAssetsDialog.run(self, editor=self, assets=assets)

    def save_layout(self) -> bool:
        self._commit_pending_table_edit()
        # bugs/0375: a fresh lens/camera import is a transient library surrogate,
        # NOT the user's own layout file -- so Save must prompt for a real file to
        # create rather than silently overwrite the auto-generated machine_vision_*.py
        # (and re-tie the session to it). Treat it like an unsaved layout.
        if self.current_layout_file is None or getattr(self, "_layout_is_unsaved_import", False):
            return self.save_layout_as()
        self._write_layout_file(self.current_layout_file)
        return True

    def save_layout_as(self) -> bool:
        self._commit_pending_table_edit()
        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        path = filedialog.asksaveasfilename(
            title="Save Kraken layout",
            initialdir=str(SCREENSHOT_DIR),
            defaultextension=".py",
            filetypes=[("Python layout", "*.py")],
        )
        if not path:
            return False
        self.current_layout_file = Path(path)
        # bugs/0375: the user has now committed the layout to their own file, so it
        # is no longer a transient import -- Save targets this file from here on.
        self._layout_is_unsaved_import = False
        self._write_layout_file(self.current_layout_file)
        self.load_layouts()
        return True

    def export_3d_step(self) -> None:
        """Export the current 3D viewer geometry as a STEP assembly."""
        worker = getattr(self, "_step_export_thread", None)
        if worker is not None and worker.is_alive():
            messagebox.showinfo(
                "3D STEP Export",
                "A STEP export is already running. Wait for it to finish before starting another export.",
                parent=self,
            )
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
            self._normalize_special_rows()
        except Exception:
            pass
        stem = "kraken_3d_assembly"
        if self.current_layout_file is not None:
            stem = f"{self.current_layout_file.stem}_3d"
        try:
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        path = filedialog.asksaveasfilename(
            title="Export 3D Assembly STEP",
            initialdir=str(SCREENSHOT_DIR),
            initialfile=f"{stem}.step",
            defaultextension=".step",
            filetypes=[
                ("STEP", "*.step"),
                ("STEP", "*.stp"),
                ("All files", "*"),
            ],
            parent=self,
        )
        if not path:
            return
        output_path = Path(path).expanduser()
        try:
            self._begin_analysis_progress("3D STEP export")
            self.status_var.set("Exporting 3D STEP...")
            self._update_analysis_progress("Building optical system", 1, 8)
            self.update_idletasks()
            capture = io.StringIO()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                with redirect_stdout(capture), redirect_stderr(capture):
                    system = self.build_system()
            captured = capture.getvalue()
            if captured:
                self.append_debug(captured)
            if self._has_imported_step_cad():
                def cad_progress(label, done, total):
                    self._update_analysis_progress(label, 1 + int(done), 8)

                cad_shapes = self._collect_native_step_export_shapes(
                    system,
                    progress_callback=cad_progress,
                )
                self._update_analysis_progress("Tracing ray envelope", 5, 8)
                ray_polylines = self._step_export_ray_polylines(system)
                dimension_polylines = self._step_export_dimension_polylines(system)
                rows_snapshot = [SurfaceRow(**asdict(row)) for row in self.rows]
                self._start_native_step_export_worker(
                    system,
                    rows_snapshot,
                    cad_shapes,
                    ray_polylines,
                    dimension_polylines,
                    output_path,
                )
                return
            else:
                # Try analytic export (revolution surfaces) first — much smaller files
                try:
                    self._update_analysis_progress("Collecting edge geometry", 2, 5)
                    edge_extras = self._collect_step_edge_and_extra_meshes(system)
                    self._update_analysis_progress("Writing analytic STEP", 4, 5)
                    analytic, faceted, tris = _write_step_with_analytic_surfaces(
                        system, self.rows, edge_extras, output_path,
                    )
                    message = (
                        f"3D STEP exported: {output_path.name} | "
                        f"analytic_surfaces={analytic}, edge_meshes={faceted}, "
                        f"edge_facets={tris}"
                    )
                except Exception as analytic_exc:
                    import traceback as _tb
                    _tb_text = ''.join(_tb.format_exception(analytic_exc))
                    print(f"[STEP] Analytic export failed:\n{_tb_text}", file=sys.stderr, flush=True)
                    self.append_debug(
                        f"Analytic STEP export failed:\n{_tb_text}\n"
                        f"Using shell-based faceted fallback."
                    )
                    self._update_analysis_progress("Collecting faceted geometry", 3, 5)
                    mesh_items = self._collect_3d_step_export_meshes(system)
                    self._update_analysis_progress("Writing faceted STEP", 4, 5)
                    mesh_count, triangle_count = _write_meshes_to_faceted_step(
                        mesh_items,
                        output_path,
                    )
                    message = (
                        f"3D STEP exported (faceted shell): {output_path.name} | "
                        f"meshes={mesh_count}, facets={triangle_count}"
                    )
            self.status_var.set(message)
            self.append_progress(message)
            self._finish_analysis_progress("3D STEP export", success=True)
        except Exception as exc:
            error = _short_error_message(exc)
            self.status_var.set(f"3D STEP export failed: {error}")
            self.append_debug(f"3D STEP export failed: {exc}")
            self._finish_analysis_progress("3D STEP export", success=False)
            messagebox.showerror(
                "3D STEP Export Error",
                f"Failed to export 3D STEP:\n\n{error}",
                parent=self,
            )

    def _start_native_step_export_worker(
        self,
        system,
        rows_snapshot: list[SurfaceRow],
        cad_shapes: list[tuple[str, object]],
        ray_polylines: list[np.ndarray],
        dimension_polylines: list[np.ndarray],
        output_path: Path,
    ) -> None:
        progress_queue: Queue = Queue()

        def worker() -> None:
            try:
                counts = _write_step_with_cad_shapes_and_rays(
                    system,
                    rows_snapshot,
                    cad_shapes,
                    ray_polylines,
                    output_path,
                    dimension_polylines=dimension_polylines,
                    progress_callback=lambda label, done, total: progress_queue.put(
                        ("progress", str(label), int(done), int(total))
                    ),
                )
                progress_queue.put(("done", counts))
            except Exception as exc:
                progress_queue.put(("error", _short_error_message(exc), traceback.format_exc()))

        thread = threading.Thread(target=worker, name="kraken-step-export", daemon=True)
        self._step_export_thread = thread
        self._step_export_queue = progress_queue
        self._step_export_output_path = output_path
        self._step_export_ray_count = len(ray_polylines)
        self.status_var.set("Writing 3D STEP in background...")
        self.append_progress(
            f"3D STEP writer started: {output_path.name} | "
            f"ray_envelopes={len(ray_polylines)}, dimension_leaders={len(dimension_polylines)}"
        )
        try:
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start(80)
        except Exception:
            pass
        self.progress_spinner_var.set("...")
        self.progress_percent_var.set("writing")
        thread.start()
        self.after(120, self._poll_native_step_export_worker)

    def _poll_native_step_export_worker(self) -> None:
        queue = getattr(self, "_step_export_queue", None)
        thread = getattr(self, "_step_export_thread", None)
        if queue is None or thread is None:
            return
        terminal_payload = None
        while True:
            try:
                payload = queue.get_nowait()
            except Empty:
                break
            if not payload:
                continue
            kind = payload[0]
            if kind == "progress":
                _kind, label, done, total = payload
                self.progress_spinner_var.set("...")
                self.progress_percent_var.set(str(label))
                if str(label) != "Writing STEP file":
                    self.append_progress(f"3D STEP export: {label} ({done}/{total})")
            elif kind in {"done", "error"}:
                terminal_payload = payload

        if terminal_payload is None:
            if thread.is_alive():
                self.after(160, self._poll_native_step_export_worker)
                return
            terminal_payload = ("error", "STEP writer exited without reporting a result", "")

        try:
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
        except Exception:
            pass
        self._step_export_thread = None
        self._step_export_queue = None

        if terminal_payload[0] == "done":
            _kind, counts = terminal_payload
            analytic_count, cad_count, ray_count, dimension_count = counts
            output_path = Path(getattr(self, "_step_export_output_path", ""))
            message = (
                f"3D STEP exported (native CAD + ray envelope): {output_path.name} | "
                f"analytic_surfaces={analytic_count}, native_steps={cad_count}, "
                f"ray_envelopes={ray_count}, dimension_leaders={dimension_count}"
            )
            self.status_var.set(message)
            self.append_progress(message)
            self._finish_analysis_progress("3D STEP export", success=True)
            return

        _kind, error, tb_text = terminal_payload
        self.status_var.set(f"3D STEP export failed: {error}")
        if tb_text:
            self.append_debug(f"3D STEP export failed:\n{tb_text}")
        self._finish_analysis_progress("3D STEP export", success=False)
        messagebox.showerror(
            "3D STEP Export Error",
            f"Failed to export 3D STEP:\n\n{error}",
            parent=self,
        )

    def _main_lens_drawing_dialogs(self) -> MainLensDrawingDialogs:
        dialog = self.__dict__.get("_main_lens_drawing_dialogs_instance")
        if dialog is None:
            dialog = MainLensDrawingDialogs(self, screenshot_dir=SCREENSHOT_DIR)
            self._main_lens_drawing_dialogs_instance = dialog
        return dialog

    def _open_lens_drawing_surface_properties_dialog(self, *, for_export: bool = False) -> bool:
        return self._main_lens_drawing_dialogs()._open_lens_drawing_surface_properties_dialog(for_export=for_export)

    def export_lens_drawing(self) -> None:
        self._main_lens_drawing_dialogs().export_lens_drawing()

    def _layout_file_writer_service(self) -> LayoutFileWriterService:
        service = self.__dict__.get("_layout_file_writer_service_instance")
        if service is None:
            service = LayoutFileWriterService(self)
            self._layout_file_writer_service_instance = service
        return service

    def _write_layout_file(self, path: Path) -> None:
        self._layout_file_writer_service()._write_layout_file(path)

    def _extract_surfaces_from_example(self, path: Path):
        original_system = Kos.system
        original_display2d = getattr(Kos, "display2d", None)
        original_display3d = getattr(Kos, "display3d", None)
        original_display2d_colab = getattr(Kos, "display2d_colab", None)
        example_dir = str(path.parent)
        previous_sys_path = list(sys.path)
        try:
            package_name = "KrakenOS.Examples" if path.parent.resolve() == EXAMPLES_DIR.resolve() else None
        except Exception:
            package_name = None

        def capture_system(surf_data, setup, build=1):
            raise _CapturedExample(list(surf_data))

        try:
            Kos.system = capture_system
            if original_display2d is not None:
                Kos.display2d = lambda *args, **kwargs: None
            if original_display3d is not None:
                Kos.display3d = lambda *args, **kwargs: None
            if original_display2d_colab is not None:
                Kos.display2d_colab = lambda *args, **kwargs: None

            namespace = {
                "__name__": "__main__",
                "__file__": str(path),
                "__package__": package_name,
            }
            code = path.read_text(encoding="utf-8", errors="ignore")
            try:
                previous_cwd = os.getcwd()
                os.chdir(path.parent)
                if example_dir not in sys.path:
                    sys.path.insert(0, example_dir)
                exec(compile(code, str(path), "exec"), namespace, namespace)
            except _CapturedExample as captured:
                return captured.surfaces
            except SystemExit as exc:
                raise ValueError(
                    f"Example {path.name} exited before defining a UI-loadable KrakenOS system."
                ) from exc
            finally:
                os.chdir(previous_cwd)
                sys.path[:] = previous_sys_path
        finally:
            Kos.system = original_system
            if original_display2d is not None:
                Kos.display2d = original_display2d
            if original_display3d is not None:
                Kos.display3d = original_display3d
            if original_display2d_colab is not None:
                Kos.display2d_colab = original_display2d_colab

        raise ValueError("No KrakenOS system definition was captured from the example.")

    @staticmethod
    def _example_file_is_menu_loadable(path: Path) -> bool:
        return example_file_is_menu_loadable(path)

    @staticmethod
    def _example_file_has_import_side_effects(code: str) -> bool:
        return example_file_has_import_side_effects(code)

    @staticmethod
    def _surface_attrs_used_in_example(path: Path) -> list[str]:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []
        surf_vars = set(re.findall(r"^(\w+)\s*=\s*Kos\.surf\(\)", text, flags=re.M))
        if not surf_vars:
            return []
        attrs = {
            attr
            for var, attr in re.findall(r"^(\w+)\.(\w+)\s*=.*$", text, flags=re.M)
            if var in surf_vars
        }
        return sorted(attrs)

    @classmethod
    def _unsupported_example_surface_attrs(cls, path: Path) -> list[str]:
        attrs = cls._surface_attrs_used_in_example(path)
        return [attr for attr in attrs if attr not in _example_supported_surface_attrs()]

    @staticmethod
    def _surface_attr_differs_from_default(surface, default_surface, attr: str) -> bool:
        value = getattr(surface, attr, None)
        default = getattr(default_surface, attr, None)
        if isinstance(value, (int, float, np.floating)) or isinstance(default, (int, float, np.floating)):
            try:
                return abs(float(value) - float(default)) > 1e-12
            except Exception:
                return str(value) != str(default)
        if isinstance(value, (list, tuple, np.ndarray)) or isinstance(default, (list, tuple, np.ndarray)):
            try:
                left = np.asarray(value, dtype=float)
                right = np.asarray(default, dtype=float)
                if left.shape != right.shape:
                    return True
                return not np.allclose(left, right, atol=1e-12, rtol=0.0)
            except Exception:
                return repr(value) != repr(default)
        return value != default

    def _active_unsupported_example_surface_attrs(self, path: Path, surfaces: list[object]) -> list[str]:
        unsupported = self._unsupported_example_surface_attrs(path)
        if not unsupported or not surfaces:
            return unsupported
        default_surface = Kos.surf()
        active = []
        for attr in unsupported:
            if any(self._surface_attr_differs_from_default(surface, default_surface, attr) for surface in surfaces):
                active.append(attr)
        return active

    def _report_example_feature_gaps(self, example_name: str, path: Path, surfaces: list[object]) -> bool:
        unsupported = self._active_unsupported_example_surface_attrs(path, surfaces)
        if not unsupported:
            self.append_debug(f"Example {example_name}: UI supports all explicit surface attributes used in the source.")
            return False
        preview = ", ".join(unsupported[:6])
        if len(unsupported) > 6:
            preview += f", +{len(unsupported) - 6} more"
        self.append_debug(
            f"Example {example_name}: unsupported or partially supported surface attributes in UI: "
            + ", ".join(unsupported)
        )
        self.status_var.set(
            f"Loaded example {example_name}. UI does not fully support: {preview}. Click Update to run analysis."
        )
        return True

    @staticmethod
    def _row_from_surface(surface, index: int, total: int) -> SurfaceRow:
        surface_type = "Standard"
        if index == 0:
            surface_type = "Object"
        elif index == total - 1:
            surface_type = "Image"
        elif getattr(surface, "Thin_Lens", 0.0) != 0:
            surface_type = "Thin Lens"
        elif getattr(surface, "Diff_Ord", 0.0) != 0:
            surface_type = "Grating"
        elif isinstance(getattr(surface, DIFFUSE_SCATTER_ADVANCED_ATTR, None), dict) and getattr(surface, DIFFUSE_SCATTER_ADVANCED_ATTR):
            surface_type = DIFFUSE_OBJECT_SURFACE
        elif hasattr(surface, BEAM_SPLITTER_ADVANCED_ATTR):
            surface_type = BEAM_SPLITTER_SURFACE
        elif str(getattr(surface, "Glass", "AIR")).upper() == "MIRROR":
            surface_type = "Mirror"

        rc_value = float(getattr(surface, "Rc", 0.0))
        if surface_type == "Thin Lens":
            rc_value = float(getattr(surface, "Thin_Lens", 0.0))
        extra_data_value = getattr(surface, "ExtraData", 0.0)
        encoded_extra_data = encode_custom_surface_value(extra_data_value)
        if encoded_extra_data is not None:
            extra_data_value = encoded_extra_data
        try:
            if np.all(np.asarray(extra_data_value, dtype=object) == 0):
                extra_data_value = 0.0
        except Exception:
            pass
        uda_value = getattr(surface, "UDA", "None")
        if uda_value is None:
            uda_value = "None"

        return SurfaceRow(
            surface=surface_type,
            name=str(getattr(surface, "Name", "") or f"Surface {index}"),
            rc=rc_value,
            k=float(getattr(surface, "k", 0.0)),
            axicon=float(getattr(surface, "Axicon", 0.0)),
            diff_ord=float(getattr(surface, "Diff_Ord", 0.0)),
            grating_d=float(getattr(surface, "Grating_D", 0.0)),
            grating_angle=float(getattr(surface, "Grating_Angle", 0.0)),
            thickness=float(getattr(surface, "Thickness", 0.0)),
            diameter=float(getattr(surface, "Diameter", 25.0)),
            in_diameter=float(getattr(surface, "InDiameter", 0.0)),
            drawing=float(getattr(surface, "Drawing", 1.0)),
            extra_data=extra_data_value,
            uda=uda_value,
            tilt_x=float(getattr(surface, "TiltX", 0.0)),
            tilt_y=float(getattr(surface, "TiltY", 0.0)),
            tilt_z=float(getattr(surface, "TiltZ", 0.0)),
            desp_x=float(getattr(surface, "DespX", 0.0)),
            desp_y=float(getattr(surface, "DespY", 0.0)),
            desp_z=float(getattr(surface, "DespZ", 0.0)),
            axis_move=float(getattr(surface, "AxisMove", 0.0)),
            glass=str(getattr(surface, "Glass", "AIR")),
            advanced={
                attr: getattr(surface, attr)
                for attr in _advanced_surface_attr_names()
                if hasattr(surface, attr)
                and LayoutImportExportMixin._surface_attr_differs_from_default(surface, Kos.surf(), attr)
            },
        )

    @staticmethod
    def _heal_negative_gaps_on_load(rows) -> list[dict]:
        """Repair a NEGATIVE gap saved into a layout, without moving anything (bugs/0559).

        A gap is a distance and may never be negative -- it makes the station chain run
        BACKWARDS across that row, and every consumer that walks stations then sees an
        inconsistent chain. bugs/0550 stopped one being CREATED, but a file already written with
        one stays broken on every load: flag_20260805_130111 loads
        ``machine_vision_Apo75.py`` and the flag still reports
        ``row 6 thickness -13.5949, station 252.3548 -> next_station 238.7598``. The visible
        symptom was the user's "can't change to FOV 55x55 and 40x40, sure not possible?" -- the
        conjugate solve was refusing an inconsistent chain, so the FOV was never the problem.

        The repair is pose-preserving by construction: zero the gap and give the same amount back
        through ``desp_z`` on every downstream row, since a pose is ``station + desp_z``
        (bugs/0526). Nothing moves -- verified drift 0.0 mm by the 0550 diagnostic, which uses
        exactly this arithmetic. Returns what was healed so the caller can say so out loud rather
        than silently rewriting the user's file."""
        healed: list[dict] = []
        for index, row in enumerate(list(rows)):
            try:
                thickness = float(getattr(row, "thickness", 0.0) or 0.0)
            except Exception:
                continue
            if thickness >= 0.0:
                continue
            healed.append(
                {
                    "row_index": int(index),
                    "name": str(getattr(row, "name", "") or ""),
                    "thickness": round(thickness, 4),
                }
            )
            row.thickness = 0.0
            for follower in rows[index + 1:]:
                try:
                    follower.desp_z = float(getattr(follower, "desp_z", 0.0) or 0.0) + thickness
                except Exception:
                    continue
        return healed

    @classmethod
    def _row_from_layout_item(cls, item: dict) -> SurfaceRow:
        return SurfaceRow(
            surface=str(item.get("surface", cls._infer_surface_type(item))),
            element=str(item.get("element", "")),
            name=str(item.get("name", "Surface")),
            optimize_rc=_coerce_opt_flag(item.get("optimize_rc", item.get("opt_rc", ""))),
            optimize_rc_bounds=_coerce_bounds(item.get("optimize_rc_bounds")),
            rc=float(item.get("rc", 0.0)),
            k=float(item.get("k", item.get("K", 0.0))),
            axicon=float(item.get("axicon", 0.0)),
            diff_ord=float(item.get("diff_ord", item.get("Diff_Ord", 0.0))),
            grating_d=float(item.get("grating_d", item.get("Grating_D", 0.0))),
            grating_angle=float(item.get("grating_angle", item.get("Grating_Angle", 0.0))),
            optimize_thickness=_coerce_opt_flag(item.get("optimize_thickness", item.get("opt_thickness", ""))),
            optimize_thickness_bounds=_coerce_bounds(item.get("optimize_thickness_bounds")),
            thickness=float(item.get("thickness", 0.0)),
            diameter=float(item.get("diameter", 25.0)),
            in_diameter=float(item.get("in_diameter", item.get("InDiameter", 0.0))),
            drawing=float(item.get("drawing", item.get("Drawing", 1.0))),
            extra_data=item.get("extra_data", item.get("ExtraData", 0.0)),
            uda=item.get("uda", item.get("UDA", "None")),
            advanced=_advanced_surface_attrs_from_spec(item),
            tilt_x=float(item.get("tilt_x", 0.0)),
            tilt_y=float(item.get("tilt_y", 0.0)),
            tilt_z=float(item.get("tilt_z", 0.0)),
            desp_x=float(item.get("desp_x", 0.0)),
            desp_y=float(item.get("desp_y", 0.0)),
            desp_z=float(item.get("desp_z", 0.0)),
            axis_move=float(item.get("axis_move", 0.0)),
            glass=str(item.get("glass", "AIR")),
        )

    @staticmethod
    def _infer_surface_type(item: dict) -> str:
        if "surface" in item:
            return str(item["surface"])
        name = str(item.get("name", "")).strip().lower()
        if name == "object":
            return "Object"
        if name == "image":
            return "Image"
        glass = str(item.get("glass", "AIR")).strip().upper()
        if abs(float(item.get("diff_ord", item.get("Diff_Ord", 0.0)))) > 1e-12:
            return "Grating"
        if glass == "MIRROR" and "object" in name and "target" in name:
            return OBJECT_TARGET_SURFACE
        advanced = item.get("advanced", item.get("advanced_attrs", item.get("surface_attrs", {})))
        if isinstance(advanced, dict) and any(_canonical_advanced_surface_attr(key) == DIFFUSE_SCATTER_ADVANCED_ATTR for key in advanced):
            return DIFFUSE_OBJECT_SURFACE
        if glass == "MIRROR":
            return "Mirror"
        if isinstance(advanced, dict) and any(_canonical_advanced_surface_attr(key) == BEAM_SPLITTER_ADVANCED_ATTR for key in advanced):
            return BEAM_SPLITTER_SURFACE
        return "Standard"

    def _normalize_special_rows(self) -> None:
        if not self.rows:
            return
        self.rows[0].element = ""
        self.rows[0].advanced = dict(self.rows[0].advanced or {})
        self.rows[0].advanced.pop(ELEMENT_ADVANCED_ATTR, None)
        self.rows[0].surface = "Object"
        if not self.rows[0].name or self.rows[0].name == "Surface":
            self.rows[0].name = "Object"
        self._clear_disabled_surface_type_fields(self.rows[0])
        final_image_is_detector = self._row_has_detector_output_metadata(self.rows[-1])
        if not final_image_is_detector:
            self.rows[-1].element = ""
        self.rows[-1].advanced = dict(self.rows[-1].advanced or {})
        if not final_image_is_detector:
            self.rows[-1].advanced.pop(ELEMENT_ADVANCED_ATTR, None)
        self.rows[-1].surface = "Image"
        if not self.rows[-1].name or self.rows[-1].name == "Surface":
            self.rows[-1].name = "Image"
        self._clear_disabled_surface_type_fields(self.rows[-1])
        for index, row in enumerate(self.rows[1:-1], start=1):
            if self._is_open3d_promoted_optical_solid_row(row):
                row.axis_move = 0.0
            if row.surface == "Aperture":
                if not row.name or row.name in {"Surface", "Standard"}:
                    row.name = "Aperture"
                row.glass = "AIR"
                row.rc = 0.0
                # bugs/0441: a frozen/snapped aperture's tilt_y/tilt_z are its BAKED
                # WORLD PLACEMENT (0433 ScenePlacement breadcrumb) -- flattening them
                # turned the drawn ring straight while its neighbours stayed on the
                # leg ("Aperture plane still flipped"). Normalize only prescription
                # apertures.
                placement = (row.advanced or {}).get("ScenePlacement")
                if not (
                    isinstance(placement, dict)
                    and (placement.get("stay_put_freeze") or placement.get("last_axis_to_axis_move"))
                ):
                    row.tilt_y = 0.0
                    row.tilt_z = 0.0
            elif row.surface in _reflective_proxy_surfaces():
                row.glass = "MIRROR"
                if row.surface == DIFFUSE_OBJECT_SURFACE:
                    advanced = dict(row.advanced or {})
                    advanced[DIFFUSE_SCATTER_ADVANCED_ATTR] = _normalize_diffuse_scatter_settings(
                        advanced.get(DIFFUSE_SCATTER_ADVANCED_ATTR, DIFFUSE_SCATTER_DEFAULT_SETTINGS)
                    )
                    row.advanced = advanced
            elif row.surface == BEAM_SPLITTER_SURFACE:
                if str(row.glass).upper() == "MIRROR":
                    row.glass = "AIR"
                advanced = dict(row.advanced or {})
                splitter_settings = _normalize_beam_splitter_settings(advanced.get(BEAM_SPLITTER_ADVANCED_ATTR))
                advanced[BEAM_SPLITTER_ADVANCED_ATTR] = splitter_settings
                advanced["Coating"] = _beam_splitter_coating_for_settings(splitter_settings, advanced.get("Coating"))
                row.advanced = advanced
            elif row.glass == "MIRROR":
                row.glass = "AIR"
            self._clear_disabled_surface_type_fields(row)
        self._apply_image_diameter_mode()

    @staticmethod
    def _flipped_name(name: str) -> str:
        placeholder_front = "__KR_FRONT__"
        placeholder_back = "__KR_BACK__"
        placeholder_left = "__KR_LEFT__"
        placeholder_right = "__KR_RIGHT__"
        placeholder_entry = "__KR_ENTRY__"
        placeholder_exit = "__KR_EXIT__"
        value = name
        value = re.sub(r"\bFront\b", placeholder_front, value, flags=re.IGNORECASE)
        value = re.sub(r"\bBack\b", placeholder_back, value, flags=re.IGNORECASE)
        value = re.sub(r"\bLeft\b", placeholder_left, value, flags=re.IGNORECASE)
        value = re.sub(r"\bRight\b", placeholder_right, value, flags=re.IGNORECASE)
        value = re.sub(r"\bEntry\b", placeholder_entry, value, flags=re.IGNORECASE)
        value = re.sub(r"\bExit\b", placeholder_exit, value, flags=re.IGNORECASE)
        value = value.replace(placeholder_front, "Back")
        value = value.replace(placeholder_back, "Front")
        value = value.replace(placeholder_left, "Right")
        value = value.replace(placeholder_right, "Left")
        value = value.replace(placeholder_entry, "Exit")
        value = value.replace(placeholder_exit, "Entry")
        return value
