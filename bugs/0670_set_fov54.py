"""FOV 54x54: field = full sensor half-height, 13 fields (two land on each 9 mm face).
Run AFTER any camera-model assignment -- the camera sync overrides field_value."""
from pathlib import Path


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    scene = Path("attachment/om05a_two_side.py").resolve()
    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["om"] = scene
    editor.load_layout_by_name("om")
    for var, value in (("field_type_var", "Real Image Height"), ("field_value_var", "11.52"),
                       ("field_count_var", "13"), ("image_diameter_mode_var", "Manual")):
        w = editor.__dict__.get(var)
        if w is not None:
            w.set(value)
    editor.rows[0].diameter = 54.0
    editor.rows[-1].diameter = 32.58
    editor._sync_table()
    editor._write_layout_file(scene)
    editor.destroy()
    print("FOV 54x54 applied: field 11.52 x 13, object disc 54, sensor Manual 32.58")


if __name__ == "__main__":
    main()
