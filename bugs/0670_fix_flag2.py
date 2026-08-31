"""flag_20260831_144929: register the SV25 camera model on the scene (seats the body
front_to_sensor=17.6 before the sensor) + the user's lens flip (0615 doctrine).
Run BEFORE bugs/0670_set_fov54.py (camera coupling re-derives the field)."""
from pathlib import Path


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    scene = Path("attachment/om05a_two_side.py").resolve()
    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["om"] = scene
    editor.load_layout_by_name("om")
    var = editor.__dict__.get("camera_model_var")
    if var is not None:
        var.set("CAM-SV25MCCXP")
    editor.lens_step_reverse_direction = True
    editor._sync_table()
    editor._write_layout_file(scene)
    fts = editor._current_camera_front_to_sensor_mm()
    editor.destroy()
    print(f"camera model set (front_to_sensor {fts}), lens flipped")


if __name__ == "__main__":
    main()
