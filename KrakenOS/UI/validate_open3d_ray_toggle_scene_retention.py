"""Validate Open 3D keeps CAD/STL actors when rays are toggled on.

This is a display-backed headless smoke check. Run under a normal display or
Xvfb. It promotes a STEP prism into a row-backed optical solid, assigns every
exposed face directly through the metadata service, opens the embedded 3D
inspector, and verifies that ``Show rays`` off/on does not drop the physical
surface actors.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from KrakenOS.UI import layout_editor as le
from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRISM_42779_STEP = PROJECT_ROOT / "attachment" / "prisms" / "42779" / "step_42779.step"
VALIDATION_CACHE_DIR = Path("/tmp/kraken-open3d-ray-toggle-cache")


def _machine_vision_measured_name(app: KrakenLayoutEditor) -> str:
    app.load_layouts()
    for name in app.machine_vision_names:
        normalized = str(name).lower()
        if "150" in normalized and "measured" in normalized:
            return str(name)
    raise RuntimeError("Machine Vision 150 mm measured layout was not discovered.")


def _open_inspector(app: KrakenLayoutEditor) -> Kraken3DInspector:
    app.open_3d_view()
    app.update_idletasks()
    app.update()
    inspector = app._three_d_inspector
    if inspector is None or not inspector.available:
        reason = getattr(inspector, "unavailable_reason", "") if inspector is not None else "3D inspector did not open"
        raise RuntimeError(f"Embedded 3D inspector unavailable: {reason}")
    inspector.geometry("1280x860+80+60")
    inspector.deiconify()
    inspector.lift()
    inspector.update_idletasks()
    inspector.update()
    time.sleep(0.2)
    inspector.update()
    return inspector


def _physical_rows(app: KrakenLayoutEditor) -> set[int]:
    return {
        index
        for index, row in enumerate(app.rows)
        if str(getattr(row, "surface", "") or "") not in {"Object", "Image"}
    }


def _row_actor_rows(inspector: Kraken3DInspector) -> set[int]:
    return {
        int(row_index)
        for row_index in getattr(inspector, "_row_actor_map", {})
        if int(row_index) >= 0
    }


def _bounds_span(bounds) -> float:
    values = np.asarray(bounds, dtype=float).reshape(-1)[:6]
    if values.size != 6 or not np.all(np.isfinite(values)) or values[0] > values[1]:
        return 0.0
    return float(max(values[1] - values[0], values[3] - values[2], values[5] - values[4]))


def _combine_bounds(bounds_list: list[tuple[float, float, float, float, float, float]]):
    if not bounds_list:
        return None
    values = np.asarray(bounds_list, dtype=float)
    if values.ndim != 2 or values.shape[1] != 6:
        return None
    finite = np.all(np.isfinite(values), axis=1)
    values = values[finite]
    if values.size == 0:
        return None
    return (
        float(np.min(values[:, 0])),
        float(np.max(values[:, 1])),
        float(np.min(values[:, 2])),
        float(np.max(values[:, 3])),
        float(np.min(values[:, 4])),
        float(np.max(values[:, 5])),
    )


def _assert_render_bounds_stay_near_scene(
    inspector: Kraken3DInspector,
    physical_rows: set[int],
    *,
    label: str,
) -> None:
    renderer = getattr(inspector, "_renderer", None)
    if renderer is None:
        raise AssertionError(f"{label}: Open 3D renderer was not available.")
    row_bounds = []
    for actor_key, row_index in list(getattr(inspector, "_actor_row_map", {}).items()):
        if int(row_index) not in physical_rows:
            continue
        actor = inspector._actor_by_key.get(actor_key)
        if actor is None:
            continue
        try:
            bounds = tuple(float(value) for value in actor.GetBounds())
        except Exception:
            continue
        if len(bounds) == 6 and all(np.isfinite(bounds)):
            row_bounds.append(bounds)
    combined = _combine_bounds(row_bounds)
    if combined is None:
        raise AssertionError(f"{label}: could not compute physical row actor bounds.")
    row_span = max(_bounds_span(combined), 1.0)
    try:
        visible_span = _bounds_span(renderer.ComputeVisiblePropBounds())
    except Exception as exc:
        raise AssertionError(f"{label}: could not compute visible prop bounds: {exc}") from exc
    limit = max(row_span * 12.0, 10000.0)
    if visible_span > limit:
        raise AssertionError(
            f"{label}: ray display expanded Open 3D visible bounds too far "
            f"(visible span={visible_span:.3g}, row span={row_span:.3g}, limit={limit:.3g})."
        )


def _assert_scene_rows_visible(
    app: KrakenLayoutEditor,
    inspector: Kraken3DInspector,
    *,
    promoted_row_index: int,
    label: str,
) -> None:
    physical_rows = _physical_rows(app)
    actor_rows = _row_actor_rows(inspector)
    if promoted_row_index not in actor_rows:
        raise AssertionError(f"{label}: promoted optical STEP row S{promoted_row_index} has no Open 3D actor.")
    missing = physical_rows.difference(actor_rows)
    if missing:
        raise AssertionError(f"{label}: Open 3D row actors missing physical rows {sorted(missing)}.")
    if not getattr(inspector, "_actor_ray_map", {}) and bool(inspector.show_rays_var.get()):
        raise AssertionError(f"{label}: Show rays is on but no ray actors were rendered.")
    promoted_transparent_seen = False
    promoted_wireframe_seen = False
    for actor_key, row_index in list(getattr(inspector, "_actor_row_map", {}).items()):
        if int(row_index) not in physical_rows:
            continue
        actor = inspector._actor_by_key.get(actor_key)
        if actor is None:
            raise AssertionError(f"{label}: row actor key {actor_key!r} has no actor object.")
        try:
            culling = int(actor.GetProperty().GetBackfaceCulling())
        except Exception as exc:
            raise AssertionError(f"{label}: row actor S{int(row_index)} has no readable backface-culling state: {exc}") from exc
        if culling:
            raise AssertionError(f"{label}: row actor S{int(row_index)} is still backface culled.")
        if label == "Ray On" and int(row_index) == int(promoted_row_index):
            try:
                opacity = float(actor.GetProperty().GetOpacity())
            except Exception as exc:
                raise AssertionError(f"{label}: promoted row actor opacity is unreadable: {exc}") from exc
            if not (0.20 <= opacity <= 0.38):
                raise AssertionError(f"{label}: promoted optical STEP actor should stay transparent with rays on: opacity={opacity:.3g}.")
            promoted_transparent_seen = True
            try:
                if int(actor.GetProperty().GetRepresentation()) == 1:
                    promoted_wireframe_seen = True
            except Exception:
                pass
    if label == "Ray On" and not promoted_transparent_seen:
        raise AssertionError(f"{label}: promoted optical STEP row has no transparent ray-on body actor.")
    if label == "Ray On" and promoted_wireframe_seen:
        raise AssertionError(f"{label}: promoted optical STEP row should not switch to a ray-on wireframe actor.")
    if label == "Ray On":
        _assert_render_bounds_stay_near_scene(inspector, physical_rows, label=label)


def main() -> int:
    if not PRISM_42779_STEP.exists():
        raise RuntimeError(f"Expected STEP fixture: {PRISM_42779_STEP}")

    le.CAD_CACHE_DIR = VALIDATION_CACHE_DIR / "cad"
    le.CAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    app = KrakenLayoutEditor(headless=True)
    try:
        try:
            app.auto_save_plot_var.set(False)
        except Exception:
            pass
        app.load_layout_by_name(_machine_vision_measured_name(app), refresh=False)
        app.imported_optical_step_path = PRISM_42779_STEP
        app.optical_step_rotation_x_deg = 90.0
        app.optical_step_rotation_z_deg = 90.0
        app.select_step_component("optical")
        promoted = app.promote_imported_step_to_optical_solid_row(
            "optical",
            insert_at=1,
            open_face_editor=False,
            clear_overlay=True,
            refresh_open_3d=False,
        )
        if promoted is None:
            raise AssertionError("STEP promotion returned no result.")
        promoted_row_index = int(promoted["row_index"])
        _row, _path, metadata = app._optical_solid_face_metadata_for_row(promoted_row_index)
        face_ids = [
            str(face.get("face_id", "") or "").strip()
            for face in list(metadata.get("faces", []) or [])
            if str(face.get("face_id", "") or "").strip()
        ]
        if len(face_ids) < 2:
            raise AssertionError("Expected the promoted STEP prism to expose multiple faces.")
        for face_id in face_ids:
            app.assign_optical_solid_face_function(promoted_row_index, face_id, "Uncoated", direct_context=True)

        inspector = _open_inspector(app)
        inspector.show_rays_var.set(False)
        inspector.refresh_from_editor()
        inspector.update_idletasks()
        inspector.update()
        _assert_scene_rows_visible(app, inspector, promoted_row_index=promoted_row_index, label="Ray Off")
        if getattr(inspector, "_actor_ray_map", {}):
            raise AssertionError("Ray Off: regular ray actors are still present.")

        inspector.show_rays_var.set(True)
        inspector.refresh_from_editor()
        inspector.update_idletasks()
        inspector.update()
        _assert_scene_rows_visible(app, inspector, promoted_row_index=promoted_row_index, label="Ray On")
        status = str(inspector.status_var.get())
        if "surfaces=" not in status or "rays=" not in status:
            raise AssertionError(f"Ray On status did not report rendered surfaces and rays: {status!r}")
    finally:
        try:
            if app._three_d_inspector is not None:
                app._three_d_inspector._on_close()
        except Exception:
            pass
        app.destroy()

    print("Open 3D ray-toggle scene retention validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
