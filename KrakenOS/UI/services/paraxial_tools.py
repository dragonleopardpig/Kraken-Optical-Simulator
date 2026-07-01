"""Paraxial, folded-mirror, docs, and best-focus helper workflows.

These methods are UI-facing service mixin methods: they operate on editor row
state and dialogs, but the optical math and solve orchestration no longer need
to live directly in ``layout_editor.py``.
"""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
import warnings
import webbrowser

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.services.formula_help import FormulaHelpService
from KrakenOS.UI.services.row_spec_contracts import _row_specs_signature
from KrakenOS.UI.surface_table_model import SurfaceRow
from KrakenOS.UI.trace_intent import BEAM_SPLITTER_SURFACE

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCS_HTML_DIR = PROJECT_ROOT / "docs" / "build" / "html"
DOCS_SOURCE_DIR = PROJECT_ROOT / "docs" / "source"
ANALYSIS_PATH_FILTER_DEFAULT = "All paths"


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


def _build_system_from_specs(
    row_specs: list[dict],
    *,
    build: int = 0,
    setup=None,
    apply_optical_solid_output_ports: bool = True,
) -> object:
    return _layout_module()._build_system_from_specs(
        row_specs,
        build=build,
        setup=setup,
        apply_optical_solid_output_ports=apply_optical_solid_output_ports,
    )


def _short_error_message(exc: Exception, limit: int = 220) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    text = " ".join(text.split())
    if len(text) > limit:
        return text[: max(0, limit - 1)].rstrip() + "..."
    return text


def _row_is_nonseq_optical_solid(row) -> bool:
    """A non-sequential optical element with no clean paraxial form: a Beam Splitter
    surface or a promoted mesh solid (``Solid_3d_stl``). Its straight-through (transmit)
    path is, to first order, a flat refractive plate -- which is what the first-order
    reference uses so the *sequential* pupil/paraxial trace (PupilCalc, the ABCD solve)
    does not branch and throw (bugs/0094)."""
    if str(getattr(row, "surface", "") or "") == BEAM_SPLITTER_SURFACE:
        return True
    advanced = getattr(row, "advanced", None) or {}
    stl = str(advanced.get("Solid_3d_stl", "None") or "None").strip()
    return stl not in ("", "None", "none")


def _transmissive_reference_row(row) -> SurfaceRow:
    """Straight-through (transmit) first-order equivalent of a non-seq optical solid, for
    the *sequential* pupil/paraxial trace. KEEP its geometry -- the mesh ``Solid_3d_stl``
    and glass + thickness, i.e. the transmit optical path -- but STRIP the branch-inducing
    attributes (beam-splitter coating, per-face assignments, diffuse scatter, reflective
    coating) and any tilt/decenter, so the sequential trace passes straight through it
    instead of branching and throwing (bugs/0094). Keeping the mesh makes the reference
    pupil match what PupilCalc computes for the same solid WITHOUT a splitter; replacing
    it with an analytic plate drifted ~8 mm because the mesh pose != the row-thickness
    position. A ``Beam Splitter`` *surface* (no mesh) collapses to a flat refractive
    interface."""
    ref = SurfaceRow(**asdict(row))
    ref.surface = "Standard"
    ref.tilt_x = ref.tilt_y = ref.tilt_z = 0.0
    ref.desp_x = ref.desp_y = ref.desp_z = 0.0
    ref.axis_move = 0.0
    advanced = dict(ref.advanced or {})
    has_mesh = str(advanced.get("Solid_3d_stl", "None") or "None").strip() not in ("", "None", "none")
    for key in ("BeamSplitter", "OpticalSolidFaces", "Coating", "CoatingMet", "DiffuseScatter"):
        advanced.pop(key, None)
    if not has_mesh:
        ref.rc = 0.0
        ref.k = 0.0
    ref.advanced = advanced
    return ref


def _row_branch_selector(row) -> str:
    """Which beam-splitter arm a row belongs to ('' = common / pre-split / global),
    read from the element metadata (DESIGN §5b; e.g. beam_splitter_two_arm_doublets
    tags arm rows 'transmit' / 'reflect' in ``advanced.Element.branch_selector``)."""
    advanced = getattr(row, "advanced", None) or {}
    if not isinstance(advanced, dict):
        return ""
    element = advanced.get("Element")
    if isinstance(element, dict) and element.get("branch_selector"):
        return str(element.get("branch_selector") or "").strip()
    return str(advanced.get("branch_selector", "") or "").strip()


def _branch_leaf_rows(rows: list[SurfaceRow], branch_selector: str) -> list[SurfaceRow]:
    """The ordered row sequence of ONE beam-splitter arm (DESIGN §5b Phase 2).

    A two-arm splitter scene is one linear table tagged per arm: the common
    (pre-split) rows, then both arms interleaved by row order, then a global image.
    This returns the leaf's *optical path* = the common rows BEFORE the split + that
    arm's own rows. Feed it to ``_paraxial_reference_rows_for_layout(...,
    unfold_branch_tilts=True)`` (the beam splitter -> flat plate, the folded arm
    unfolded) to get that arm's first-order entrance pupil, so a per-branch launch can
    aim each arm at its own pupil. ``''``-selector rows after the arm starts (the
    global image) are excluded.
    """
    selector = str(branch_selector or "").strip()
    common: list[SurfaceRow] = []
    arm: list[SurfaceRow] = []
    for row in rows:
        bsel = _row_branch_selector(row)
        if not bsel:
            if not arm:  # only the pre-split common rows; skip the trailing global image
                common.append(row)
        elif bsel == selector:
            arm.append(row)
    # A FOLDED arm (e.g. the reflect arm bent +Y): the splitter -> first-arm-surface ENTRY
    # gap is encoded in the first arm surface's in-plane DECENTER (its distance from the
    # splitter axis), not the last common row's linear thickness -- that thickness is the
    # OTHER arm's straight-through gap. Override it so the unfolded reference carries the
    # right object->lens conjugate for THIS arm (the straight arm has zero decenter -> no
    # override). The intra-arm spacings are the arm rows' own thicknesses, already correct.
    if common and arm:
        first = arm[0]
        entry = float(np.hypot(float(getattr(first, "desp_x", 0.0)), float(getattr(first, "desp_y", 0.0))))
        if entry > 1e-6:
            anchor = SurfaceRow(**asdict(common[-1]))
            anchor.thickness = entry
            common = common[:-1] + [anchor]
    return common + arm


def _scene_branch_selectors(rows: list[SurfaceRow]) -> list[str]:
    """Distinct beam-splitter arm selectors present in a layout, in first-seen order
    (empty when the scene has no per-arm tagging)."""
    seen: list[str] = []
    for row in rows:
        bsel = _row_branch_selector(row)
        if bsel and bsel not in seen:
            seen.append(bsel)
    return seen


class ParaxialToolsMixin:
    def _paraxial_solve_target_for_cell(self, row_index: int, field: str) -> str | None:
        return None

    def _paraxial_variable_thickness_target_for_cell(self, row_index: int, field: str) -> str | None:
        if field != "thickness" or not self.rows:
            return None
        if row_index == len(self.rows) - 1:
            return None
        if not (0 <= row_index < len(self.rows)):
            return None
        row = self.rows[row_index]
        if row.surface not in {"Object", "Standard", "Thin Lens", "Aperture", "Mirror"}:
            return None
        try:
            self._paraxial_reference_rows_for_layout()
        except Exception:
            return None
        return "thickness"

    def _folded_mirror_solve_target_for_cell(self, row_index: int, field: str) -> str | None:
        if field != "thickness" or not (0 <= row_index < len(self.rows)):
            return None
        row = self.rows[row_index]
        if row.surface != "Mirror":
            return None
        try:
            self._folded_mirror_prefix_rows(row_index)
        except Exception:
            return None
        return "mirror"

    def _best_focus_solve_target_for_cell(self, row_index: int, field: str) -> str | None:
        if field != "thickness" or not (0 <= row_index < len(self.rows)):
            return None
        row = self.rows[row_index]
        if row.surface in {"Object", "Image"}:
            return None
        return "thickness"

    def _best_focus_metric_mode_for_rows(self, rows: list[SurfaceRow]) -> str:
        has_simple_mirror = False
        for row in rows[1:-1]:
            advanced = dict(row.advanced or {})
            if self._scene_graph_value_present(advanced.get("Solid_3d_stl")):
                return "ray_trace"
            if row.surface in {BEAM_SPLITTER_SURFACE, "Grating"}:
                return "ray_trace"
            if any(
                abs(value) > 1e-9
                for value in (
                    row.tilt_x,
                    row.tilt_y,
                    row.tilt_z,
                    row.desp_x,
                    row.desp_y,
                    row.desp_z,
                    row.axis_move,
                )
            ):
                return "ray_trace"
            if row.surface == "Mirror":
                has_simple_mirror = True
        return "folded_preview" if has_simple_mirror else "sequential"

    @staticmethod
    def _best_focus_metric_label(mode: str) -> str:
        labels = {
            "ray_trace": "Ray-traced image-plane RMS",
            "folded_preview": "Folded preview image-plane RMS",
            "sequential": "Sequential image-plane RMS",
        }
        return labels.get(str(mode or "").strip(), "Image-plane RMS")

    def _is_centered_refractive_layout(self) -> bool:
        if len(self.rows) < 3:
            return False
        for row in self.rows[1:-1]:
            if row.surface not in {"Standard", "Thin Lens"}:
                return False
            if any(
                abs(value) > 1e-9
                for value in (
                    row.tilt_x,
                    row.tilt_y,
                    row.tilt_z,
                    row.desp_x,
                    row.desp_y,
                    row.desp_z,
                    row.axis_move,
                )
            ):
                return False
        return True

    def _paraxial_reference_rows_for_layout(
        self,
        rows: list[SurfaceRow] | None = None,
        *,
        unfold_branch_tilts: bool = False,
    ) -> tuple[list[SurfaceRow], int]:
        source_rows = self.rows if rows is None else rows
        if len(source_rows) < 3:
            raise RuntimeError("Not enough surfaces for paraxial solve")
        reference_rows = [SurfaceRow(**asdict(source_rows[0]))]
        last_source_index: int | None = None
        for index, row in enumerate(source_rows[1:], start=1):
            if row.surface == "Image":
                if index >= len(source_rows) - 1:
                    break  # the terminal image -- stop here
                # bugs/0100: an INTERMEDIATE Image plane (e.g. the detector plane a promoted-cube
                # promotion inserts right after the solid) has no paraxial power. Breaking on it
                # excluded the downstream LENS from the reference, so the entrance pupil landed at the
                # cube and the world bundle aimed there ("beam focuses at the splitter"). Merge its gap
                # into the previous kept plane and keep going so the lens stays in the reference.
                reference_rows[-1].thickness += max(float(row.thickness), 0.0)
                continue
            if row.surface == "Mirror":
                # Mirrors fold the path but have no paraxial power.  Merge their
                # path length into the previous kept plane so centered ABCD
                # solves still see the equivalent unfolded air gap.
                reference_rows[-1].thickness += max(float(row.thickness), 0.0)
                continue
            if _row_is_nonseq_optical_solid(row):
                # bugs/0094: a beam splitter / promoted mesh solid has no clean paraxial
                # form and makes the sequential pupil/paraxial trace branch and throw.
                # Replace it with its transmissive flat-plate equivalent (the
                # straight-through first-order path) so first-order code traces a clean
                # centered system.  (The reflect arm / per-branch references are the
                # general target in bugs/DESIGN_nonseq_first_order_reference.md §5b.)
                reference_rows.append(_transmissive_reference_row(row))
                last_source_index = index
                continue
            if row.surface not in {"Standard", "Thin Lens", "Aperture"}:
                raise RuntimeError("Paraxial solve supports centered refractive systems plus folding mirrors only")
            tilted = any(
                abs(value) > 1e-9
                for value in (
                    row.tilt_x,
                    row.tilt_y,
                    row.tilt_z,
                    row.desp_x,
                    row.desp_y,
                    row.desp_z,
                    row.axis_move,
                )
            )
            if tilted and not unfold_branch_tilts:
                raise RuntimeError("Paraxial solve supports centered refractive systems plus folding mirrors only")
            kept = SurfaceRow(**asdict(row))
            if tilted:
                # DESIGN §5b (Phase 2): a per-leaf branch reference UNFOLDS the arm.
                # A beam splitter sends the reflect arm off-axis (the rows carry
                # tilt/decenter to sit on the folded path), but the first-order
                # entrance pupil is an AXIAL property independent of the fold
                # direction, and the row thickness already is the unfolded gap. Zero
                # the fold so the centered ABCD / PupilCalc sees a straight chain.
                kept.tilt_x = kept.tilt_y = kept.tilt_z = 0.0
                kept.desp_x = kept.desp_y = kept.desp_z = 0.0
                kept.axis_move = 0.0
            reference_rows.append(kept)
            last_source_index = index
        if last_source_index is None:
            raise RuntimeError("No optical block available for paraxial solve")
        image_row = SurfaceRow(**asdict(source_rows[-1]))
        image_row.surface = "Image"
        image_row.name = image_row.name or "Image"
        image_row.thickness = 0.0
        # The terminal Image of a centered reference must itself be centered. When the
        # last leaf row is a FOLDED arm's detector (tilt_x=-90 etc.), copying it left the
        # Image tilted -> the sequential PupilCalc test trace hit a tilted image plane and
        # returned no rays (DESIGN §5b: this broke the reflect arm's per-branch pupil).
        image_row.tilt_x = image_row.tilt_y = image_row.tilt_z = 0.0
        image_row.desp_x = image_row.desp_y = image_row.desp_z = 0.0
        image_row.axis_move = 0.0
        reference_rows.append(image_row)
        return reference_rows, int(last_source_index)

    def _layout_needs_paraxial_reference(self, rows: list[SurfaceRow] | None = None) -> bool:
        """True when the layout has a non-sequential element (folding mirror, beam
        splitter, or promoted mesh solid) that the sequential first-order code cannot
        trace directly -- so first-order consumers (pupil, paraxial solve, cardinals)
        must build the transmissive reference instead of tracing the live system
        (bugs/0094)."""
        source = self.rows if rows is None else rows
        return any(
            getattr(row, "surface", "") == "Mirror" or _row_is_nonseq_optical_solid(row)
            for row in source
        )

    def _folded_optical_solid_straight_equivalent_rows(self) -> list[SurfaceRow] | None:
        """Straight sequential equivalent of a layout whose promoted mesh solid FOLDS the
        optical axis (the AZ85 right-angle mesh mirror). Folding is a RIGID transform, so the
        unfolded straight system has IDENTICAL first-order conjugates, magnification and best
        focus -- but the sequential paraxial solve trips its centered-refractive guard on the
        solid's placement decenter, and the real-ray PupilCalc branches/throws on the mesh's
        90-degree internal reflection. Replace each promoted mesh optical solid with its flat
        sequential plate (same axial thickness + glass, mesh/faces/placement stripped, its
        curvature/decenter/tilt zeroed), preserving row count and every air gap so the result
        stays in the detector's cumulative-z frame. Returns ``None`` for layouts with no
        rotating fold: a straight-through beam-splitter cube keeps its mesh (bugs/0173) and
        every unfolded / sequential layout is untouched."""
        rows = list(getattr(self, "rows", []) or [])
        if len(rows) < 3:
            return None
        fold = getattr(self, "_optical_axis_fold_world_transform_for_row", None)
        if not callable(fold):
            return None
        has_rotating_fold = False
        for index in range(len(rows)):
            try:
                transform = fold(index)
            except Exception:
                transform = None
            if transform is None:
                continue
            try:
                rotation = np.asarray(transform, dtype=float).reshape(4, 4)[:3, :3]
            except Exception:
                continue
            if np.all(np.isfinite(rotation)) and not np.allclose(rotation, np.eye(3), atol=1e-6):
                has_rotating_fold = True
                break
        if not has_rotating_fold:
            return None
        equivalent: list[SurfaceRow] = []
        replaced = False
        for row in rows:
            if _row_is_nonseq_optical_solid(row):
                flat = SurfaceRow(**asdict(row))
                flat.surface = "Standard"
                flat.rc = 0.0
                flat.tilt_x = flat.tilt_y = flat.tilt_z = 0.0
                flat.desp_x = flat.desp_y = flat.desp_z = 0.0
                flat.axis_move = 0.0
                advanced = dict(flat.advanced or {})
                for key in (
                    "Solid_3d_stl",
                    "OpticalSolidFaces",
                    "StepOverlayPromotion",
                    "OpticalSolidSourceFormat",
                    "OpticalSolidSourcePath",
                    "ScenePlacement",
                    "BeamSplitter",
                    "Coating",
                    "CoatingMet",
                    "DiffuseScatter",
                ):
                    advanced.pop(key, None)
                flat.advanced = advanced
                equivalent.append(flat)
                replaced = True
            else:
                equivalent.append(SurfaceRow(**asdict(row)))
        return equivalent if replaced else None

    def _with_rows_swapped(self, rows: list[SurfaceRow], compute):
        """Run ``compute()`` with ``self.rows`` temporarily swapped to ``rows`` (restored in a
        finally), so first-order helpers that read ``self.rows`` internally (the analysis
        surface index, aperture, cache) all see the same straight sequential equivalent. Used
        to evaluate a folded layout through its unfolded flat-plate equivalent."""
        saved = self.rows
        try:
            self.rows = rows
            return compute()
        finally:
            self.rows = saved

    def _paraxial_total_image_gap(
        self,
        rows: list[SurfaceRow] | None = None,
    ) -> tuple[float, int, list[SurfaceRow]]:
        source_rows = self.rows if rows is None else rows
        reference_rows, last_source_index = self._paraxial_reference_rows_for_layout(source_rows)
        total_gap = 0.0
        for row in source_rows[last_source_index:]:
            total_gap += max(float(row.thickness), 0.0)
        return float(total_gap), int(last_source_index), reference_rows

    def _paraxial_total_object_gap(self, rows: list[SurfaceRow] | None = None) -> tuple[float, int]:
        source_rows = self.rows if rows is None else rows
        for index, row in enumerate(source_rows[1:], start=1):
            if row.surface in {"Standard", "Thin Lens", "Aperture"}:
                total_gap = sum(max(float(item.thickness), 0.0) for item in source_rows[:index])
                return float(total_gap), int(index)
            if row.surface == "Image":
                break
        raise RuntimeError("No optical block available for paraxial solve")


    def _cleanup_current_popup_menu(self) -> None:
        menu = self.popup_menu
        if menu is not None:
            try:
                menu.grab_release()
            except tk.TclError:
                pass
            try:
                menu.destroy()
            except tk.TclError:
                pass
            self.popup_menu = None
        self.current_menu_row_id = None
        self.current_menu_field = None

    @staticmethod
    def _event_inside_widget_root_bounds(event: tk.Event, widget: tk.Widget) -> bool:
        try:
            x_root = int(event.x_root)
            y_root = int(event.y_root)
            widget.update_idletasks()
            widget_x = int(widget.winfo_rootx())
            widget_y = int(widget.winfo_rooty())
            widget_w = max(int(widget.winfo_width()), 1)
            widget_h = max(int(widget.winfo_height()), 1)
        except Exception:
            return False
        return widget_x <= x_root < widget_x + widget_w and widget_y <= y_root < widget_y + widget_h

    def _dismiss_popup_menu_event(self, event: tk.Event | None = None) -> None:
        if self.popup_menu is None:
            return
        if event is not None:
            widget = getattr(event, "widget", None)
            if isinstance(widget, tk.Menu) and self._event_inside_widget_root_bounds(event, widget):
                return
        self._cleanup_current_popup_menu()

    def _center_dialog_over_main_window(self, dialog: tk.Toplevel) -> None:
        dialog.update_idletasks()
        parent_x = self.winfo_rootx()
        parent_y = self.winfo_rooty()
        parent_w = max(self.winfo_width(), 1)
        parent_h = max(self.winfo_height(), 1)
        dialog_w = max(dialog.winfo_width(), 1)
        dialog_h = max(dialog.winfo_height(), 1)
        pos_x = parent_x + max((parent_w - dialog_w) // 2, 0)
        pos_y = parent_y + max((parent_h - dialog_h) // 2, 0)
        dialog.geometry(f"+{pos_x}+{pos_y}")

    @staticmethod
    def _center_dialog_on_screen(dialog: tk.Toplevel) -> None:
        def place_dialog() -> None:
            if not dialog.winfo_exists():
                return
            dialog.update_idletasks()
            dialog_w = max(dialog.winfo_width(), dialog.winfo_reqwidth(), 1)
            dialog_h = max(dialog.winfo_height(), dialog.winfo_reqheight(), 1)
            screen_w = max(dialog.winfo_screenwidth(), 1)
            screen_h = max(dialog.winfo_screenheight(), 1)
            pos_x = max((screen_w - dialog_w) // 2, 0)
            pos_y = max((screen_h - dialog_h) // 2, 0)
            dialog.geometry(f"+{pos_x}+{pos_y}")

        place_dialog()
        dialog.after_idle(place_dialog)
        dialog.after(80, place_dialog)

    def show_formula_help(self) -> None:
        try:
            html_doc = self._build_formula_help_html()
            cache_dir = Path.home() / ".cache" / "krakenos"
            cache_dir.mkdir(parents=True, exist_ok=True)
            help_path = cache_dir / "optics_formula_sheet.html"
            help_path.write_text(html_doc, encoding="utf-8")
            self._formula_help_path = help_path
            opened = webbrowser.open_new_tab(help_path.as_uri())
            if not opened:
                fallback = self._open_document_with_system_viewer(help_path)
                if not fallback:
                    raise RuntimeError("No browser opener available.")
            self.status_var.set(f"Opened optics help: {help_path}")
        except Exception as exc:
            self.append_debug(f"Help page open failed: {exc}")
            self.status_var.set(f"Help page failed: {_short_error_message(exc)}")

    def _open_sphinx_docs_page(self, page: str, label: str | None = None, section: str = "manual") -> None:
        """Open a built Sphinx HTML page; fall back to the source RST."""
        label = label or page
        html_path = DOCS_HTML_DIR / section / f"{page}.html"
        rst_path = DOCS_SOURCE_DIR / section / f"{page}.rst"
        target: Path | None = None
        if html_path.exists():
            target = html_path
        elif rst_path.exists():
            messagebox.showinfo(
                "Documentation",
                f"The built HTML for '{label}' was not found at\n  {html_path}\n\n"
                "Showing the source RST instead. To build the HTML once:\n\n"
                "  cd docs && sphinx-build -E -b html source build/html",
                parent=self,
            )
            target = rst_path
        else:
            messagebox.showwarning(
                "Documentation",
                f"Docs page '{label}' was not found.\n\nLooked for:\n  {html_path}\n  {rst_path}",
                parent=self,
            )
            return
        try:
            opened = webbrowser.open_new_tab(target.as_uri())
            if not opened:
                fallback = self._open_document_with_system_viewer(target)
                if not fallback:
                    raise RuntimeError("No browser opener available.")
            self.status_var.set(f"Opened docs: {target}")
        except Exception as exc:
            self.append_debug(f"Docs open failed for {label}: {exc}")
            self.status_var.set(f"Docs failed: {_short_error_message(exc)}")

    def show_rules_of_thumb(self) -> None:
        self._open_sphinx_docs_page("rules_of_thumb", "Rules of Thumb", section="knowledge_base")

    def show_cardinal_points_docs(self) -> None:
        self._open_sphinx_docs_page("cardinal_points", "Cardinal Points", section="knowledge_base")

    def show_analysis_tools_docs(self) -> None:
        self._open_sphinx_docs_page("analysis_tools", "Analysis Tools")

    def show_gaussian_beams_docs(self) -> None:
        self._open_sphinx_docs_page("gaussian_beams", "Gaussian Beams")

    def show_pupil_patterns_docs(self) -> None:
        self._open_sphinx_docs_page("pupil_patterns", "Pupil Patterns")

    def show_manual_index(self) -> None:
        self._open_sphinx_docs_page("index", "Manual Index")

    def open_paraxial_calculator(self) -> None:
        self._main_paraxial_analysis_dialogs().open_paraxial_calculator()


    @staticmethod
    def _open_document_with_system_viewer(document_path: Path) -> bool:
        try:
            if os.name == "nt":
                os.startfile(str(document_path))  # type: ignore[attr-defined]
                return True
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(document_path)])
                return True
            if shutil.which("xdg-open"):
                subprocess.Popen(["xdg-open", str(document_path)])
                return True
            if shutil.which("gio"):
                subprocess.Popen(["gio", "open", str(document_path)])
                return True
        except Exception:
            return False
        return False

    def _formula_help_service(self) -> FormulaHelpService:
        service = self.__dict__.get("_formula_help_service_instance")
        if service is None:
            service = FormulaHelpService(self, docs_html_dir=DOCS_HTML_DIR, docs_source_dir=DOCS_SOURCE_DIR)
            self._formula_help_service_instance = service
        return service

    def _build_formula_help_html(self) -> str:
        return self._formula_help_service().build_formula_help_html()

    def _exact_paraxial_solution_for_rows(
        self,
        solve_rows: list[SurfaceRow],
        wavelength: float | None = None,
    ) -> tuple[float, float, float, float, float, float, float]:
        if len(solve_rows) < 3:
            raise RuntimeError("Not enough surfaces for paraxial solve")
        rows_copy = [SurfaceRow(**asdict(row)) for row in solve_rows]
        optical_rows = rows_copy[1:-1]
        if not optical_rows:
            raise RuntimeError("No optical block available for paraxial solve")
        unsupported: list[str] = []
        for row in optical_rows:
            if row.surface not in {"Standard", "Thin Lens", "Aperture"}:
                unsupported.append(row.name or row.surface)
                continue
            if any(
                abs(value) > 1e-9
                for value in (
                    row.tilt_x,
                    row.tilt_y,
                    row.tilt_z,
                    row.desp_x,
                    row.desp_y,
                    row.desp_z,
                    row.axis_move,
                )
            ):
                unsupported.append(row.name or row.surface)
        if unsupported:
            raise RuntimeError("Paraxial solve supports centered refractive systems only")
        rows_copy[0].thickness = 0.0
        rows_copy[-2].thickness = 0.0
        rows_copy[-1].thickness = 0.0
        solve_specs = self._serializable_specs_for_rows(rows_copy)
        solve_wavelength = self._current_wavelength() if wavelength is None else float(wavelength)
        signature = (_row_specs_signature(solve_specs), float(solve_wavelength))
        cached_signature = self.__dict__.get("_paraxial_cache_signature")
        cached_solution = self.__dict__.get("_paraxial_cache_result")
        if cached_signature == signature and cached_solution is not None:
            return cached_solution
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            with io.StringIO() as stdout_buf, io.StringIO() as stderr_buf:
                with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                    # bugs/0166: paraxial-only solve (Parax); never NS-traces the
                    # meshes, so skip the output-port overrides' per-branch force-mesh.
                    solve_system = _build_system_from_specs(
                        solve_specs, build=0, apply_optical_solid_output_ports=False
                    )
                    _, _, _, a, b, c, d, effl, ppa, ppp, *_rest = solve_system.Parax(solve_wavelength)
        result = (float(a), float(b), float(c), float(d), float(effl), float(ppa), float(ppp))
        self._paraxial_cache_signature = signature
        self._paraxial_cache_result = result
        return result

    def _exact_paraxial_cardinals(self, wavelength: float | None = None) -> tuple[float, float, float]:
        if len(self.rows) < 3:
            raise RuntimeError("Not enough surfaces for paraxial solve")
        solve_rows = self.rows
        if any(row.surface == "Mirror" for row in self.rows):
            solve_rows, _last_source_index = self._paraxial_reference_rows_for_layout(self.rows)
        _a, _b, _c, _d, effl, ppa, ppp = self._exact_paraxial_solution_for_rows(solve_rows, wavelength)
        return float(effl), float(ppa), float(ppp)

    @staticmethod
    def _surface_vertex_z(rows: list[SurfaceRow], row_index: int) -> float:
        z_pos = 0.0
        for index, row in enumerate(rows):
            if index == row_index:
                return float(z_pos)
            z_pos += float(row.thickness)
        return float(z_pos)

    def _paraxial_vertex_zs(self, rows: list[SurfaceRow] | None = None) -> tuple[float, float]:
        source_rows = self.rows if rows is None else rows
        optical_indices = [
            index
            for index, row in enumerate(source_rows)
            if row.surface not in {"Object", "Image"}
        ]
        if not optical_indices:
            raise RuntimeError("No optical block available for paraxial vertex locations")
        return (
            self._surface_vertex_z(source_rows, optical_indices[0]),
            self._surface_vertex_z(source_rows, optical_indices[-1]),
        )

    def _paraxial_two_f_gaps(self) -> tuple[float, float, float, float, float]:
        effl, ppa, ppp = self._exact_paraxial_cardinals()
        if not np.isfinite(effl) or abs(effl) <= 1e-12:
            raise RuntimeError("Paraxial solve failed: invalid effective focal length")
        two_f = 2.0 * effl
        object_gap = two_f - ppa
        image_gap = two_f + ppp
        return float(effl), float(ppa), float(ppp), float(object_gap), float(image_gap)

    @staticmethod
    def _format_paraxial_value(value: float | str) -> str:
        if isinstance(value, str):
            return value
        if not np.isfinite(value):
            return "Infinity"
        return f"{float(value):.6g}"

    def _exact_paraxial_cardinals_for_rows(
        self,
        solve_rows: list[SurfaceRow],
        wavelength: float | None = None,
    ) -> tuple[float, float, float]:
        _a, _b, _c, _d, effl, ppa, ppp = self._exact_paraxial_solution_for_rows(solve_rows, wavelength)
        return float(effl), float(ppa), float(ppp)

    def _compute_image_gap_from_paraxial_solution(
        self,
        a: float,
        b: float,
        c: float,
        d: float,
        object_distance: float,
        object_mode: str,
    ) -> float:
        if object_mode == "Infinity":
            if abs(a) <= 1e-12:
                raise RuntimeError("Paraxial image is at infinity for the current system")
            return float(-c / a)
        denominator = float(a + (b * object_distance))
        if abs(denominator) <= 1e-12:
            raise RuntimeError("Paraxial image is at infinity for the current object distance")
        return float(-(c + (d * object_distance)) / denominator)

    def _compute_object_gap_from_paraxial_solution(
        self,
        a: float,
        b: float,
        c: float,
        d: float,
        image_distance: float,
    ) -> float:
        denominator = float(d + (b * image_distance))
        if abs(denominator) <= 1e-12:
            raise RuntimeError("Paraxial object is at infinity for the current image distance")
        return float(-(c + (a * image_distance)) / denominator)

    def _compute_paraxial_solve_result(self, target: str) -> dict[str, float | str]:
        equivalent = self._folded_optical_solid_straight_equivalent_rows()
        if equivalent is not None:
            # bugs/0195: a promoted mesh mirror folds the axis 90deg; its placement decenter trips
            # the centered-refractive guard in _exact_paraxial_solution_for_rows. Folding is rigid,
            # so solve the unfolded flat-plate equivalent (same cumulative-z frame -> the object /
            # image distances and the in-focus check stay in the detector frame).
            return self._with_rows_swapped(equivalent, lambda: self._compute_paraxial_solve_result(target))
        a, b, c, d, effl, ppa, ppp = self._exact_paraxial_solution_for_rows(self.rows)
        if not np.isfinite(effl) or abs(effl) <= 1e-12:
            raise RuntimeError("Paraxial solve failed: invalid effective focal length")
        result: dict[str, float | str] = {
            "target": target,
            "effl": float(effl),
            "ppa": float(ppa),
            "ppp": float(ppp),
            "object_mode_before": self._current_object_mode(),
            "object_distance_before": float(self.rows[0].thickness) if self.rows else 0.0,
            "image_distance_before": float(self._current_image_distance()),
        }
        if target == "image":
            object_distance = float(self.rows[0].thickness) if self.rows else 0.0
            solved_distance = self._compute_image_gap_from_paraxial_solution(
                a,
                b,
                c,
                d,
                object_distance,
                self._current_object_mode(),
            )
            result["object_principal"] = (
                "Infinity" if self._current_object_mode() == "Infinity" else float(object_distance + ppa)
            )
            result["image_principal"] = float(solved_distance - ppp)
            result["solved_distance"] = float(solved_distance)
            result["message"] = f"Paraxial solve: image distance -> {float(solved_distance):.6g} mm | EFFL={effl:.6g} mm"
            result["selected_row"] = max(0, len(self.rows) - 2)
            result["object_mode_after"] = result["object_mode_before"]
            return result

        image_distance = self._current_image_distance()
        solved_distance = self._compute_object_gap_from_paraxial_solution(a, b, c, d, image_distance)
        if not np.isfinite(solved_distance) or abs(solved_distance) > 1e9:
            solved_distance = float("inf")
            object_principal = float("inf")
            object_mode_after = "Infinity"
            message = f"Paraxial solve: object at infinity | EFFL={effl:.6g} mm"
        else:
            object_principal = float(solved_distance + ppa)
            object_mode_after = "Infinity" if (not np.isfinite(solved_distance) or abs(solved_distance) > 1e9) else "Finite"
            if object_mode_after == "Infinity":
                message = f"Paraxial solve: object at infinity | EFFL={effl:.6g} mm"
            else:
                message = f"Paraxial solve: object distance -> {float(solved_distance):.6g} mm | EFFL={effl:.6g} mm"
        result["image_principal"] = float(image_distance - ppp)
        result["object_principal"] = object_principal
        result["solved_distance"] = solved_distance
        result["message"] = message
        result["selected_row"] = 0
        result["object_mode_after"] = object_mode_after
        return result

    def _paraxial_variable_thickness_details(
        self,
        row_index: int,
        candidate: float,
    ) -> dict[str, float | str]:
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError("Paraxial thickness solve target is out of range")
        rows_trial = [SurfaceRow(**asdict(row)) for row in self.rows]
        rows_trial[row_index].thickness = max(float(candidate), 0.0)
        total_image_gap, _last_source_index, reference_rows = self._paraxial_total_image_gap(rows_trial)
        a, b, c, d, effl, ppa, ppp = self._exact_paraxial_solution_for_rows(reference_rows)
        object_distance, _first_source_index = self._paraxial_total_object_gap(rows_trial)
        predicted_image_gap = self._compute_image_gap_from_paraxial_solution(
            a,
            b,
            c,
            d,
            object_distance,
            self._current_object_mode(),
        )
        current_total_gap, _base_last_source_index, _base_reference_rows = self._paraxial_total_image_gap(self.rows)
        return {
            "effl": float(effl),
            "ppa": float(ppa),
            "ppp": float(ppp),
            "object_distance_before": float(self._paraxial_total_object_gap(self.rows)[0]),
            "image_distance_before": float(current_total_gap),
            "object_principal": ("Infinity" if self._current_object_mode() == "Infinity" else float(object_distance + ppa)),
            "image_principal": float(predicted_image_gap - ppp),
            "predicted_image_gap": float(predicted_image_gap),
            "fixed_image_gap": float(total_image_gap),
            "residual": float(predicted_image_gap - total_image_gap),
            "candidate": max(float(candidate), 0.0),
        }

    def _compute_paraxial_variable_thickness_result(self, row_index: int) -> dict[str, float | str]:
        if self._paraxial_variable_thickness_target_for_cell(row_index, "thickness") is None:
            raise RuntimeError("Paraxial variable-thickness solve is not available for this row")
        row = self.rows[row_index]
        start_value = max(float(row.thickness), 0.0)
        total_image_gap, last_source_index, reference_rows = self._paraxial_total_image_gap(self.rows)
        current_image_distance = float(total_image_gap)
        base_span = max(10.0, abs(start_value) * 0.5, abs(current_image_distance) * 0.25)
        lower = max(0.0, start_value - base_span)
        upper = start_value + base_span
        best_details: dict[str, float | str] | None = None
        best_abs = float("inf")
        bracket: tuple[float, float] | None = None
        bracket_details: tuple[dict[str, float | str], dict[str, float | str]] | None = None
        valid_samples = 0

        if row_index >= last_source_index:
            a, b, c, d, effl, ppa, ppp = self._exact_paraxial_solution_for_rows(reference_rows)
            predicted_image_gap = self._compute_image_gap_from_paraxial_solution(
                a,
                b,
                c,
                d,
                self._paraxial_total_object_gap(self.rows)[0],
                self._current_object_mode(),
            )
            other_fixed_gap = 0.0
            for index, source_row in enumerate(self.rows[last_source_index:], start=last_source_index):
                if index == row_index:
                    continue
                other_fixed_gap += max(float(source_row.thickness), 0.0)
            candidate = max(0.0, float(predicted_image_gap - other_fixed_gap))
            best_details = self._paraxial_variable_thickness_details(row_index, candidate)
            best_abs = abs(float(best_details["residual"]))
            valid_samples = 1
        else:
            for _ in range(3):
                candidates = np.linspace(lower, upper, 7)
                samples: list[tuple[float, dict[str, float | str]]] = []
                for candidate in candidates:
                    try:
                        details = self._paraxial_variable_thickness_details(row_index, float(candidate))
                    except Exception:
                        continue
                    valid_samples += 1
                    residual = float(details["residual"])
                    abs_residual = abs(residual)
                    if abs_residual < best_abs:
                        best_abs = abs_residual
                        best_details = details
                    samples.append((float(candidate), details))
                for (_c0, d0), (_c1, d1) in zip(samples, samples[1:]):
                    r0 = float(d0["residual"])
                    r1 = float(d1["residual"])
                    if r0 == 0.0:
                        best_details = d0
                        bracket = None
                        break
                    if r0 * r1 <= 0.0:
                        bracket = (float(d0["candidate"]), float(d1["candidate"]))
                        bracket_details = (d0, d1)
                        break
                if bracket is not None or (best_details is not None and float(best_details["residual"]) == 0.0):
                    break
                span = max(upper - lower, 1.0)
                lower = max(0.0, lower - span)
                upper = upper + span

        if best_details is None or valid_samples == 0:
            raise RuntimeError("Paraxial thickness solve failed to evaluate any valid paraxial states")

        if row_index < last_source_index and bracket is None and best_abs > 1e-6:
            raise RuntimeError("No non-negative thickness satisfies paraxial focus while the other gaps stay fixed")

        if row_index < last_source_index and bracket is not None and bracket_details is not None:
            left, right = bracket
            left_details, right_details = bracket_details
            for _ in range(16):
                mid = 0.5 * (left + right)
                mid_details = self._paraxial_variable_thickness_details(row_index, mid)
                mid_residual = float(mid_details["residual"])
                if abs(mid_residual) < best_abs:
                    best_abs = abs(mid_residual)
                    best_details = mid_details
                if abs(mid_residual) <= 1e-9:
                    best_details = mid_details
                    break
                left_residual = float(left_details["residual"])
                if left_residual * mid_residual <= 0.0:
                    right = mid
                    right_details = mid_details
                else:
                    left = mid
                    left_details = mid_details

        assert best_details is not None
        solved_distance = float(best_details["candidate"])
        residual = float(best_details["residual"])
        return {
            "target": "thickness",
            "selected_row": row_index,
            "target_label": row.name or row.surface,
            "start_value": float(row.thickness),
            "solved_distance": solved_distance,
            "effl": float(best_details["effl"]),
            "ppa": float(best_details["ppa"]),
            "ppp": float(best_details["ppp"]),
            "object_mode_before": self._current_object_mode(),
            "object_distance_before": float(best_details["object_distance_before"]),
            "image_distance_before": float(best_details["image_distance_before"]),
            "object_principal": best_details["object_principal"],
            "image_principal": best_details["image_principal"],
            "predicted_image_gap": float(best_details["predicted_image_gap"]),
            "residual": residual,
            "sample_count": int(valid_samples),
            "message": (
                f"Paraxial solve: row {row_index} {row.name or row.surface} thickness -> "
                f"{solved_distance:.6g} mm | residual={residual:.6g} mm"
            ),
        }

    def _compute_image_gap_from_cardinals(
        self,
        effl: float,
        ppa: float,
        ppp: float,
        object_distance: float,
        object_mode: str,
    ) -> tuple[float, float | str, float]:
        if object_mode == "Infinity":
            solved_distance = float(effl + ppp)
            return solved_distance, "Infinity", float(effl)
        object_principal = float(object_distance + ppa)
        if abs(object_principal) <= 1e-12:
            raise RuntimeError("Object is located on the front principal plane")
        power_balance = (1.0 / float(effl)) - (1.0 / object_principal)
        if abs(power_balance) <= 1e-12:
            raise RuntimeError("Paraxial image is at infinity for the current object distance")
        image_principal = 1.0 / power_balance
        solved_distance = float(image_principal + ppp)
        return solved_distance, float(object_principal), float(image_principal)

    def _folded_mirror_prefix_rows(self, mirror_row_index: int) -> list[SurfaceRow]:
        if not (0 <= mirror_row_index < len(self.rows)):
            raise RuntimeError("Mirror row out of range")
        if self.rows[mirror_row_index].surface != "Mirror":
            raise RuntimeError("Selected row is not a mirror")
        if mirror_row_index < 2:
            raise RuntimeError("Need at least one refractive surface before the mirror")
        prefix_rows = [SurfaceRow(**asdict(row)) for row in self.rows[:mirror_row_index]]
        if len(prefix_rows) < 2:
            raise RuntimeError("Need refractive content before the mirror")
        image_row = SurfaceRow(**asdict(self.rows[-1]))
        image_row.surface = "Image"
        image_row.name = image_row.name or "Image"
        image_row.thickness = 0.0
        prefix_rows.append(image_row)
        for row in prefix_rows[1:-1]:
            if row.surface not in {"Standard", "Thin Lens"}:
                raise RuntimeError("Folded paraxial estimate requires centered refractive surfaces before the mirror")
            if any(
                abs(value) > 1e-9
                for value in (
                    row.tilt_x,
                    row.tilt_y,
                    row.tilt_z,
                    row.desp_x,
                    row.desp_y,
                    row.desp_z,
                    row.axis_move,
                )
            ):
                raise RuntimeError("Folded paraxial estimate requires centered refractive surfaces before the mirror")
        return prefix_rows

    def _compute_folded_mirror_solve_result(self, mirror_row_index: int) -> dict[str, float | str]:
        prefix_rows = self._folded_mirror_prefix_rows(mirror_row_index)
        a, b, c, d, effl, ppa, ppp = self._exact_paraxial_solution_for_rows(prefix_rows)
        if not np.isfinite(effl) or abs(effl) <= 1e-12:
            raise RuntimeError("Paraxial solve failed: invalid effective focal length")
        object_distance = float(prefix_rows[0].thickness) if prefix_rows else 0.0
        total_image_gap = self._compute_image_gap_from_paraxial_solution(
            a,
            b,
            c,
            d,
            object_distance,
            self._current_object_mode(),
        )
        upstream_gap = float(self.rows[mirror_row_index - 1].thickness)
        solved_distance = float(total_image_gap - upstream_gap)
        return {
            "target": "mirror",
            "selected_row": mirror_row_index,
            "effl": float(effl),
            "ppa": float(ppa),
            "ppp": float(ppp),
            "object_distance_before": float(self.rows[0].thickness) if self.rows else 0.0,
            "object_principal": ("Infinity" if self._current_object_mode() == "Infinity" else float(object_distance + ppa)),
            "image_principal": float(total_image_gap - ppp),
            "straight_image_gap": float(total_image_gap),
            "upstream_gap": float(upstream_gap),
            "solved_distance": solved_distance,
            "message": (
                f"Folded paraxial solve: mirror thickness -> {solved_distance:.6g} mm "
                f"(straight image gap {total_image_gap:.6g} mm, upstream {upstream_gap:.6g} mm)"
            ),
        }

    def _show_paraxial_solve_dialog(self, result: dict[str, float | str]) -> bool:
        return self._main_paraxial_analysis_dialogs()._show_paraxial_solve_dialog(result)

    def _show_folded_mirror_solve_dialog(self, result: dict[str, float | str]) -> bool:
        return self._main_paraxial_analysis_dialogs()._show_folded_mirror_solve_dialog(result)

    def _show_best_focus_dialog(self, result: dict[str, float | str]) -> bool:
        return self._main_paraxial_analysis_dialogs()._show_best_focus_dialog(result)

    def _apply_paraxial_two_f(self, mode: str) -> None:
        effl, _ppa, _ppp, object_gap, image_gap = self._paraxial_two_f_gaps()
        self._begin_history_capture()
        if mode in {"object", "pair"}:
            self.object_mode_var.set("Finite")
            self.rows[0].thickness = object_gap
        if mode in {"image", "pair"}:
            self.rows[max(0, len(self.rows) - 2)].thickness = image_gap
        self._normalize_special_rows()
        self._sync_table()
        selected_row = 0 if mode == "object" else max(0, len(self.rows) - 2)
        self._select_table_row(selected_row)
        self._commit_history_capture()
        self.refresh_plot()
        if mode == "pair":
            message = (
                f"Paraxial 2F setup applied | EFFL={effl:.6g} mm | "
                f"object={object_gap:.6g} mm | image={image_gap:.6g} mm"
            )
        elif mode == "object":
            message = f"Paraxial 2F object gap -> {object_gap:.6g} mm | EFFL={effl:.6g} mm"
        else:
            message = f"Paraxial 2F image gap -> {image_gap:.6g} mm | EFFL={effl:.6g} mm"
        self.status_var.set(message)
        self.append_progress(message)

    def set_current_object_to_two_f(self) -> None:
        try:
            self._apply_paraxial_two_f("object")
        except Exception as exc:
            error = _short_error_message(exc)
            messagebox.showerror("Paraxial 2F", error)
            self.append_debug(f"Paraxial 2F object failed: {exc}")
            self.status_var.set(f"Paraxial 2F object failed: {error}")
        finally:
            self._cleanup_current_popup_menu()

    def set_current_image_to_two_f(self) -> None:
        try:
            self._apply_paraxial_two_f("image")
        except Exception as exc:
            error = _short_error_message(exc)
            messagebox.showerror("Paraxial 2F", error)
            self.append_debug(f"Paraxial 2F image failed: {exc}")
            self.status_var.set(f"Paraxial 2F image failed: {error}")
        finally:
            self._cleanup_current_popup_menu()

    def set_current_two_f_pair(self) -> None:
        try:
            self._apply_paraxial_two_f("pair")
        except Exception as exc:
            error = _short_error_message(exc)
            messagebox.showerror("Paraxial 2F", error)
            self.append_debug(f"Paraxial 2F pair failed: {exc}")
            self.status_var.set(f"Paraxial 2F pair failed: {error}")
        finally:
            self._cleanup_current_popup_menu()

    def solve_current_paraxial_distance(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        row_index = self._table_item_row_index(self.current_menu_row_id)
        if row_index is None:
            return
        target = self._paraxial_solve_target_for_cell(row_index, self.current_menu_field)
        try:
            if target is None:
                raise RuntimeError("Paraxial solve is only available for object/image distance cells")
            result = self._compute_paraxial_solve_result(target)
            if not self._show_paraxial_solve_dialog(result):
                self.status_var.set("Paraxial solve cancelled")
                return
            selected_row = int(result["selected_row"])
            solved_distance = result["solved_distance"]
            self._begin_history_capture()
            if target == "image":
                self.rows[selected_row].thickness = float(solved_distance)
            else:
                object_mode_after = str(result["object_mode_after"])
                self.object_mode_var.set(object_mode_after)
                if object_mode_after == "Finite":
                    self.rows[0].thickness = float(solved_distance)
            message = str(result["message"])
            self._normalize_special_rows()
            if target == "image" and self._sync_object_diameter_from_manual_image():
                message += f" | object diameter -> {self.rows[0].diameter:.6g} mm"
            self._sync_table()
            self._select_table_row(selected_row)
            self._commit_history_capture()
            self.refresh_plot()
            self.status_var.set(message)
            self.append_progress(message)
        except Exception as exc:
            error = _short_error_message(exc)
            messagebox.showerror("Paraxial Solve", error)
            self.append_debug(f"Paraxial solve failed: {exc}")
            self.status_var.set(f"Paraxial solve failed: {error}")
        finally:
            self._cleanup_current_popup_menu()

    def solve_current_paraxial_variable_thickness(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        row_index = self._table_item_row_index(self.current_menu_row_id)
        if row_index is None:
            return
        try:
            if self._paraxial_variable_thickness_target_for_cell(row_index, self.current_menu_field) is None:
                raise RuntimeError("Paraxial variable-thickness solve is only available on centered refractive thickness cells")
            result = self._compute_paraxial_variable_thickness_result(row_index)
            if not self._show_paraxial_solve_dialog(result):
                self.status_var.set("Paraxial solve cancelled")
                return
            selected_row = int(result["selected_row"])
            self._begin_history_capture()
            self.rows[selected_row].thickness = float(result["solved_distance"])
            self._normalize_special_rows()
            self._sync_table()
            self._select_table_row(selected_row)
            self._commit_history_capture()
            self.refresh_plot()
            message = str(result["message"])
            self.status_var.set(message)
            self.append_progress(message)
        except Exception as exc:
            error = _short_error_message(exc)
            messagebox.showerror("Paraxial Solve", error)
            self.append_debug(f"Paraxial variable-thickness solve failed: {exc}")
            self.status_var.set(f"Paraxial solve failed: {error}")
        finally:
            self._cleanup_current_popup_menu()

    def _traced_image_spot_rms_for_rows(
        self,
        rows: list[SurfaceRow],
        wavelength: float,
        sample_count: int,
        *,
        build_runtime: bool = False,
    ) -> float:
        system = _build_system_from_specs(self._serializable_specs_for_rows(rows), build=(1 if build_runtime else 0))
        analysis_rays = self._build_analysis_rays(system, wavelength, sample_count=sample_count)
        X, Y, Z, L, M, N = self._pick_image_plane_data(analysis_rays)
        if np.asarray(X).size == 0:
            raise RuntimeError("No image-plane ray data")
        rms, _cenX, _cenY = Kos.RMS(X, Y, Z, L, M, N)
        if not np.isfinite(rms):
            raise RuntimeError("Invalid spot RMS")
        return float(rms)

    @staticmethod
    def _weighted_detector_spot_rms(samples: dict[str, object]) -> float:
        x_values = np.asarray(samples.get("x", np.asarray([])), dtype=float)
        y_values = np.asarray(samples.get("y", np.asarray([])), dtype=float)
        weights = np.asarray(samples.get("weights", np.asarray([])), dtype=float)
        if x_values.size == 0 or y_values.size == 0:
            raise RuntimeError("No detector hit data for best-image solve target")
        if weights.size == x_values.size and float(np.sum(np.maximum(weights, 0.0))) > 0.0:
            use_weights = np.maximum(weights, 0.0)
            center_x = float(np.average(x_values, weights=use_weights))
            center_y = float(np.average(y_values, weights=use_weights))
            radii_sq = (x_values - center_x) ** 2 + (y_values - center_y) ** 2
            return float(np.sqrt(np.average(radii_sq, weights=use_weights)))
        center_x = float(np.mean(x_values))
        center_y = float(np.mean(y_values))
        radii_sq = (x_values - center_x) ** 2 + (y_values - center_y) ** 2
        return float(np.sqrt(np.mean(radii_sq)))

    def _best_image_filter_for_ray_records(self, ray_records: list[dict[str, object]]) -> str:
        records = self._branch_throughput_records_for_ray_records(ray_records)
        choices = self._branch_throughput_filter_choices(records)
        current = self._current_analysis_branch_filter()
        if current in choices and current != ANALYSIS_PATH_FILTER_DEFAULT:
            return current
        preferred = (
            "Output: Detector output port",
            "Output: Cross output detector",
            "Output: Return output detector",
        )
        for value in preferred:
            if value in choices:
                return value
        terminals = [choice for choice in choices if choice.startswith("Terminal:") and "Detector" in choice]
        if terminals:
            return terminals[0]
        return current if current in choices else ANALYSIS_PATH_FILTER_DEFAULT

    def _preview_image_spot_rms_for_rows(self, rows: list[SurfaceRow], wavelength: float) -> float:
        system = _build_system_from_specs(self._serializable_specs_for_rows(rows), build=1)
        rays = Kos.raykeeper(system)
        max_radius = max((max(float(row.diameter) * 0.5, 0.5) for row in rows), default=1.0)
        field_bundle_count_before = int(getattr(self, "_preview_field_bundle_count", 1))
        ray_count_before = int(getattr(self, "_preview_field_ray_count", 1))
        self._trace_preview_rays(
            system,
            rays,
            wavelength,
            max_radius,
            sampling_mode=self._preview_scene_sampling_mode(),
        )
        scene_bundle = self._build_scene_bundle(system, rays, max_radius)
        try:
            records = self._collect_ray_analysis_records(scene_bundle=scene_bundle)
            filter_text = self._best_image_filter_for_ray_records(records)
            samples = self._branch_detector_spot_samples(
                system,
                filter_text,
                require_detector=True,
                ray_records=records,
            )
            rms = self._weighted_detector_spot_rms(samples)
            if not np.isfinite(rms):
                raise RuntimeError("Invalid detector RMS")
            self._best_image_last_filter_text = filter_text
            return float(rms)
        finally:
            self._preview_field_bundle_count = field_bundle_count_before
            self._preview_field_ray_count = ray_count_before

    def _real_ray_best_focus_shift_for_rows(self, rows=None, wavelength=None):
        """Axial shift (mm) from the detector to REAL-RAY on-axis best focus, for layouts the
        paraxial image-plane conjugate can't handle (a 3D solid / beam-splitter cube in the
        path). Builds the mesh system, traces the on-axis 2D spot, and returns the shift that
        minimises it (rays are straight in image space). ``None`` on failure -- the one-click
        Snap then reports it cleanly."""
        import io
        from contextlib import redirect_stderr, redirect_stdout

        if rows is None:
            equivalent = self._folded_optical_solid_straight_equivalent_rows()
            if equivalent is not None:
                # bugs/0194: keeping the promoted mesh mirror makes PupilCalc branch/throw on its
                # 90deg internal reflection. Folding is rigid, so trace the unfolded flat-plate
                # equivalent (swap self.rows so the analysis-surface/aperture helpers agree). The
                # minimising axial shift is the same in the detector's cumulative-z frame.
                return self._with_rows_swapped(
                    equivalent,
                    lambda: self._real_ray_best_focus_shift_for_rows(equivalent, wavelength),
                )
        rows = list(rows if rows is not None else getattr(self, "rows", []) or [])
        if len(rows) < 3:
            return None
        try:
            if wavelength is None:
                wavelength = float(self._current_wavelength())
            field_type = "angle" if self._current_object_mode() == "Infinity" else "height"
            capture = io.StringIO()
            with redirect_stdout(capture), redirect_stderr(capture):
                system = _build_system_from_specs(self._serializable_specs_for_rows(rows), build=1)
                x, y, _z, l_dir, m_dir, n_dir, _w = self._build_geometric_image_samples_full(
                    system, float(wavelength), sample_count=10, pattern="hexapolar",
                    surface_index=self._analysis_surface_index(),
                    aperture_type=self._current_aperture_type(),
                    aperture_value=self._current_aperture_value(),
                    field_type=field_type, field_x=0.0, field_y=0.0, require_2d_pupil=True,
                )
            x = np.asarray(x, dtype=float)
            y = np.asarray(y, dtype=float)
            if x.size < 4:
                return None
            return self._spot_best_focus_shift(
                x, y, np.asarray(l_dir, dtype=float), np.asarray(m_dir, dtype=float), np.asarray(n_dir, dtype=float)
            )
        except Exception:
            return None

    def _spot_rms_for_rows(self, rows: list[SurfaceRow], wavelength: float, sample_count: int) -> float:
        metric_mode = self._best_focus_metric_mode_for_rows(rows)
        if metric_mode == "folded_preview":
            return self._folded_preview_spot_rms_for_rows(rows)
        if metric_mode == "ray_trace":
            return self._preview_image_spot_rms_for_rows(rows, wavelength)
        return self._traced_image_spot_rms_for_rows(
            rows,
            wavelength,
            sample_count,
        )

    def _best_focus_search_interval(self, row_index: int) -> tuple[float, float]:
        current_value = max(float(self.rows[row_index].thickness), 0.0)
        lower = max(0.0, current_value - max(5.0, abs(current_value) * 0.35))
        upper = current_value + max(5.0, abs(current_value) * 0.35)
        if self.rows[row_index].surface == "Mirror":
            try:
                estimate = float(self._compute_folded_mirror_solve_result(row_index)["solved_distance"])
                center = max(0.0, estimate)
                span = max(5.0, abs(estimate - current_value), abs(estimate) * 0.25)
                lower = max(0.0, center - span)
                upper = center + span
            except Exception:
                pass
        if upper <= lower:
            upper = lower + 1.0
        return float(lower), float(upper)

    def _compute_best_focus_result(self, row_index: int) -> dict[str, float | str]:
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError("Best-focus target is out of range")
        row = self.rows[row_index]
        if row.surface == "Object" or row.surface == "Image":
            raise RuntimeError("Best-focus solve is not available for this row")
        wavelength = self._current_wavelength()
        metric_mode = self._best_focus_metric_mode_for_rows(self.rows)
        metric_label = self._best_focus_metric_label(metric_mode)
        sample_count = (
            max(1, self._current_ray_count())
            if metric_mode == "ray_trace"
            else max(5, min(11, self._current_ray_count()))
        )
        lower, upper = self._best_focus_search_interval(row_index)
        status_label = "Best image solve"
        max_bracket_expansions = 6
        expansion_candidates_per_pass = 9
        total_iterations = 17 + (max_bracket_expansions * expansion_candidates_per_pass) + 11 + 11
        iteration_done = 0
        best_filter_text = ""
        self._set_analysis_parallel_status(status_label, 1, False)
        self._begin_analysis_progress(status_label)
        completed = False
        self.append_progress(
            f"Best image solve | row {row_index} {row.name or row.surface} | range [{lower:.6g}, {upper:.6g}] mm | metric={metric_label}"
        )
        try:
            best_value = None
            best_rms = None
            metric_cache: dict[float, tuple[float, str]] = {}

            def _evaluate_candidate(candidate: float) -> tuple[float, str]:
                nonlocal iteration_done
                candidate_value = max(0.0, float(candidate))
                cache_key = round(candidate_value, 12)
                cached = metric_cache.get(cache_key)
                if cached is not None:
                    return cached
                rows_trial = [SurfaceRow(**asdict(item)) for item in self.rows]
                rows_trial[row_index].thickness = candidate_value
                rms_value = self._spot_rms_for_rows(rows_trial, wavelength, sample_count)
                candidate_filter_value = str(getattr(self, "_best_image_last_filter_text", "") or "").strip()
                cached = (float(rms_value), candidate_filter_value)
                metric_cache[cache_key] = cached
                iteration_done += 1
                self._update_analysis_progress(status_label, iteration_done, total_iterations)
                return cached

            def _track_best(candidate: float, rms: float, candidate_filter: str) -> None:
                nonlocal best_rms, best_value, best_filter_text
                if best_rms is None or rms < best_rms:
                    best_rms = float(rms)
                    best_value = float(candidate)
                    best_filter_text = candidate_filter

            interval_lower = float(lower)
            interval_upper = float(upper)
            candidates = np.linspace(interval_lower, interval_upper, 17)
            candidate_rms: list[float] = []
            for candidate in candidates:
                rms, candidate_filter = _evaluate_candidate(float(candidate))
                candidate_rms.append(float(rms))
                _track_best(float(candidate), float(rms), candidate_filter)

            if best_value is None or best_rms is None:
                raise RuntimeError("Best-focus search failed")

            expansion_count = 0
            while len(candidate_rms) >= 2 and expansion_count < max_bracket_expansions:
                best_index = int(np.argmin(np.asarray(candidate_rms, dtype=float)))
                expand_upper = (
                    best_index == (len(candidate_rms) - 1)
                    and candidate_rms[-1] <= candidate_rms[-2]
                )
                expand_lower = (
                    best_index == 0
                    and interval_lower > 0.0
                    and candidate_rms[0] <= candidate_rms[1]
                )
                if not expand_upper and not expand_lower:
                    break
                span = max(interval_upper - interval_lower, 1.0)
                if expand_upper:
                    new_lower = interval_upper
                    new_upper = interval_upper + (span * 2.0)
                else:
                    new_upper = interval_lower
                    new_lower = max(0.0, interval_lower - (span * 2.0))
                    if abs(new_upper - new_lower) <= 1e-12:
                        break
                interval_lower = float(new_lower)
                interval_upper = float(new_upper)
                self.append_progress(
                    f"Best image solve expanding search to [{interval_lower:.6g}, {interval_upper:.6g}] mm"
                )
                candidates = np.linspace(interval_lower, interval_upper, expansion_candidates_per_pass)
                candidate_rms = []
                for candidate in candidates:
                    rms, candidate_filter = _evaluate_candidate(float(candidate))
                    candidate_rms.append(float(rms))
                    _track_best(float(candidate), float(rms), candidate_filter)
                expansion_count += 1

            step = float(candidates[1] - candidates[0]) if len(candidates) > 1 else max(1.0, interval_upper - interval_lower)
            center = best_value
            for _ in range(2):
                local_lower = max(0.0, center - step)
                local_upper = center + step
                local_candidates = np.linspace(local_lower, local_upper, 11)
                for candidate in local_candidates:
                    rms, candidate_filter = _evaluate_candidate(float(candidate))
                    _track_best(float(candidate), float(rms), candidate_filter)
                center = best_value
                step *= 0.35

            completed = True
            return {
                "selected_row": row_index,
                "target_label": row.name or row.surface,
                "start_value": float(self.rows[row_index].thickness),
                "lower": lower,
                "upper": upper,
                "solved_distance": float(best_value),
                "best_rms": float(best_rms),
                "sample_count": int(sample_count),
                "metric_mode": metric_mode,
                "metric_label": metric_label,
                "filter_text": best_filter_text,
                "message": (
                    f"Best image solve: row {row_index} {row.name or row.surface} thickness -> "
                    f"{float(best_value):.6g} mm | spot RMS={float(best_rms):.6g} mm | metric={metric_label}"
                    + (f" | target={best_filter_text}" if best_filter_text else "")
                ),
            }
        finally:
            self._finish_analysis_progress(status_label, completed)

    def _collimation_output_vergence_for_rows(
        self, rows: list[SurfaceRow], wavelength: float | None = None
    ) -> float:
        """Magnitude of the paraxial output ray vergence ``|1/s'|`` (1/mm) for the
        current object distance. Collimated output => image at infinity => 0.

        Uses the system ABCD (the optical block, independent of the object/back
        gaps) and the current object distance applied analytically, so the merit
        is smooth and deterministic. A real-ray angular spread was tried first
        but vignettes to noise at large defocus -- the paraxial vergence has a
        clean zero exactly at collimation. Centered refractive systems only
        (raises for mirrors/tilts via the paraxial solver)."""
        object_mode = self._current_object_mode()
        a, b, c, d, _effl, _ppa, _ppp = self._exact_paraxial_solution_for_rows(rows, wavelength)
        if object_mode == "Infinity":
            numerator = abs(float(a))
            denominator = abs(float(c))
        else:
            object_distance = float(rows[0].thickness)
            numerator = abs(float(a) + float(b) * object_distance)
            denominator = abs(float(c) + float(d) * object_distance)
        if denominator <= 1e-12:
            # image distance ~ 0 (extreme convergence): vergence is enormous.
            return float("inf") if numerator > 1e-12 else 0.0
        value = float(numerator / denominator)
        if not np.isfinite(value):
            raise RuntimeError("Invalid collimation vergence")
        return value

    def _collimation_search_interval(self, row_index: int) -> tuple[float, float]:
        """A generous, focal-length-aware bracket for the collimation solve. The
        vergence vertex (collimated point) sits near the front focal distance for
        the object gap, which can be far from the current value, so the interval
        spans 0 .. current + max(current, 2.5*|EFL|)."""
        current = max(float(self.rows[row_index].thickness), 0.0)
        span = max(current, 50.0)
        try:
            effl = abs(float(self._exact_paraxial_cardinals()[0]))
            if np.isfinite(effl):
                span = max(span, 2.5 * effl)
        except Exception:
            pass
        return 0.0, float(current + span)

    def _compute_best_collimation_result(self, row_index: int) -> dict[str, float | str]:
        """Solve a thickness for best collimation: minimise the paraxial output
        vergence ``|1/s'|``. Mirrors the best-focus search shape (coarse scan +
        local refine) but with the vergence metric; operates on ``self.rows`` and
        returns the solved distance without mutating the layout. The metric is a
        cheap closed-form paraxial eval (no ray tracing), so the search is fast
        and noise-free."""
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError("Best-collimation target is out of range")
        row = self.rows[row_index]
        # Unlike best focus, the object gap (row 0) IS the canonical collimation
        # variable -- moving the source toward the focal point parallelises the
        # exit beam -- so only the terminal image gap is rejected.
        if row.surface == "Image":
            raise RuntimeError("Best-collimation solve is not available for the image row")
        wavelength = self._current_wavelength()
        lower, upper = self._collimation_search_interval(row_index)
        metric_label = "output vergence |1/s'| (1/mm)"
        status_label = "Best collimation solve"
        total_iterations = 21 + 11 + 11 + 11
        iteration_done = 0
        metric_cache: dict[float, float] = {}
        self._set_analysis_parallel_status(status_label, 1, False)
        self._begin_analysis_progress(status_label)
        completed = False
        self.append_progress(
            f"Best collimation solve | row {row_index} {row.name or row.surface} | "
            f"range [{lower:.6g}, {upper:.6g}] mm | metric={metric_label}"
        )
        try:
            def _evaluate_candidate(candidate: float) -> float:
                nonlocal iteration_done
                candidate_value = max(0.0, float(candidate))
                cache_key = round(candidate_value, 12)
                cached = metric_cache.get(cache_key)
                if cached is not None:
                    return cached
                rows_trial = [SurfaceRow(**asdict(item)) for item in self.rows]
                rows_trial[row_index].thickness = candidate_value
                value = self._collimation_output_vergence_for_rows(rows_trial, wavelength)
                metric_cache[cache_key] = float(value)
                iteration_done += 1
                self._update_analysis_progress(status_label, iteration_done, total_iterations)
                return float(value)

            best_value: float | None = None
            best_metric: float | None = None

            def _track_best(candidate: float, metric: float) -> None:
                nonlocal best_value, best_metric
                if best_metric is None or metric < best_metric:
                    best_metric = float(metric)
                    best_value = float(candidate)

            for candidate in np.linspace(float(lower), float(upper), 21):
                _track_best(float(candidate), _evaluate_candidate(float(candidate)))

            if best_value is None or best_metric is None:
                raise RuntimeError("Best-collimation search failed")

            step = float(upper - lower) / 20.0 if upper > lower else 1.0
            center = best_value
            for _ in range(3):
                local_lower = max(0.0, center - step)
                local_upper = center + step
                for candidate in np.linspace(local_lower, local_upper, 11):
                    _track_best(float(candidate), _evaluate_candidate(float(candidate)))
                center = best_value
                step *= 0.35

            completed = True
            return {
                "selected_row": row_index,
                "target_label": row.name or row.surface,
                "start_value": float(self.rows[row_index].thickness),
                "lower": float(lower),
                "upper": float(upper),
                "solved_distance": float(best_value),
                "best_metric": float(best_metric),
                "metric_label": metric_label,
                "message": (
                    f"Best collimation solve: row {row_index} {row.name or row.surface} thickness -> "
                    f"{float(best_value):.6g} mm | output vergence={float(best_metric):.6g} /mm"
                ),
            }
        finally:
            self._finish_analysis_progress(status_label, completed)

    def solve_current_folded_mirror_distance(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        row_index = self._table_item_row_index(self.current_menu_row_id)
        if row_index is None:
            return
        try:
            if self._folded_mirror_solve_target_for_cell(row_index, self.current_menu_field) is None:
                raise RuntimeError("Folded paraxial mirror solve is only available on mirror thickness cells")
            result = self._compute_folded_mirror_solve_result(row_index)
            if not self._show_folded_mirror_solve_dialog(result):
                self.status_var.set("Folded mirror solve cancelled")
                return
            selected_row = int(result["selected_row"])
            self._begin_history_capture()
            self.rows[selected_row].thickness = float(result["solved_distance"])
            self._normalize_special_rows()
            self._sync_table()
            self._select_table_row(selected_row)
            self._commit_history_capture()
            self.refresh_plot()
            message = str(result["message"])
            self.status_var.set(message)
            self.append_progress(message)
        except Exception as exc:
            error = _short_error_message(exc)
            messagebox.showerror("Folded Mirror Solve", error)
            self.append_debug(f"Folded mirror solve failed: {exc}")
            self.status_var.set(f"Folded mirror solve failed: {error}")
        finally:
            self._cleanup_current_popup_menu()

    def solve_current_best_focus_distance(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        row_index = self._table_item_row_index(self.current_menu_row_id)
        if row_index is None:
            return
        try:
            if self._best_focus_solve_target_for_cell(row_index, self.current_menu_field) is None:
                raise RuntimeError("Best-image solve is only available on non-terminal thickness cells")
            result = self._compute_best_focus_result(row_index)
            if not self._show_best_focus_dialog(result):
                self.status_var.set("Best image solve cancelled")
                return
            selected_row = int(result["selected_row"])
            self._begin_history_capture()
            self.rows[selected_row].thickness = float(result["solved_distance"])
            self._normalize_special_rows()
            self._sync_table()
            self._select_table_row(selected_row)
            self._commit_history_capture()
            self.refresh_plot()
            message = str(result["message"])
            self.status_var.set(message)
            self.append_progress(message)
        except Exception as exc:
            error = _short_error_message(exc)
            messagebox.showerror("Best Image Solve", error)
            self.append_debug(f"Best image solve failed: {exc}")
            self.status_var.set(f"Best image solve failed: {error}")
        finally:
            self._cleanup_current_popup_menu()
