"""0693: eyeball render of the ROTATED om05a (production Left/Right vs Top/Bottom
station). Applies the user's RA-mirror-1 rotation through the real command, then
snapshots the swung train — the lens body must ride its surrogate rows."""
from pathlib import Path


def main():
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _save_vtk_snapshot, _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_folded.py").resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False
    editor._build_preview_system_rays_bundle(trace_rays=True)

    m1 = next(i for i, r in enumerate(editor.rows)
              if str(getattr(r, "name", "")) == "RA mirror 1 (50 mm)")
    editor.rotate_scene_row_pose_world_axis(m1, "y", -90.0)
    editor._build_preview_system_rays_bundle(trace_rays=True)

    editor.open_3d_view()
    editor.update_idletasks()
    editor.update()
    inspector = editor._three_d_inspector
    inspector.refresh_from_editor(
        sampling_mode=editor._preview_3d_sampling_mode(), force_retrace=True
    )
    _settle(editor, 1.0)
    cam = inspector._renderer.GetActiveCamera()
    # look at the rotated lens leg (rows around (-9.5, 43.3, -222..-262)) from the side
    cam.SetFocalPoint(-9.5, 43.3, -242.0)
    cam.SetPosition(180.0, 120.0, -242.0)
    cam.SetViewUp(0.0, 1.0, 0.0)
    inspector._renderer.ResetCameraClippingRange()
    _settle(editor, 0.5)
    _save_vtk_snapshot(inspector, Path("bugs") / "0693_verify_rotated_leg.png")
    print("snapshot written")
    editor.destroy()


if __name__ == "__main__":
    main()
