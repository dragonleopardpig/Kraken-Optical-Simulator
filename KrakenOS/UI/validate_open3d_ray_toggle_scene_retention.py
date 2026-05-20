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
            if opacity < 0.4:
                raise AssertionError(f"{label}: promoted optical STEP actor is too transparent with rays on: opacity={opacity:.3g}.")


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
