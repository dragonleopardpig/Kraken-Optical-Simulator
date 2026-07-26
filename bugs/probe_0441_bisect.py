"""bugs/0441: bisect WHICH internal step of add_beam_splitter_to_led zeroes the
frozen Aperture row's tilts (monkeypatch tilt-dumps around the add's collaborators)."""
from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor


def ap_tilt(app):
    for r in app.rows:
        if str(getattr(r, "surface", "")) == "Aperture":
            return (round(float(r.tilt_x), 2), round(float(r.tilt_y), 2), round(float(r.tilt_z), 2))
    return None


def wrap(app, name):
    original = getattr(app, name, None)
    if not callable(original):
        print(f"  (no {name})")
        return
    def wrapped(*args, **kwargs):
        before = ap_tilt(app)
        result = original(*args, **kwargs)
        after = ap_tilt(app)
        mark = "  <-- ZEROED HERE" if before != after else ""
        print(f"  {name}: {before} -> {after}{mark}", flush=True)
        return result
    setattr(app, name, wrapped)


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
        app.load_layout_by_name("az85")
        m1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([m1])
        print("post-freeze aperture tilt:", ap_tilt(app))
        for name in (
            "import_optical_step",
            "set_step_clear_aperture",
            "auto_set_step_clear_aperture",
            "center_clear_aperture_on_optical_axis",
            "promote_imported_step_to_optical_solid_row",
            "set_optical_led_glue",
            "_flag_beam_splitter_coating_face",
            "_set_step_rotation_deg_tuple",
            "_set_step_placement_offset_xyz",
            "_neutralize_bs_row_station_footprint",
            "_normalize_special_rows",
            "_sync_table",
            "_commit_pending_table_edit",
        ):
            wrap(app, name)
        app.add_beam_splitter_to_led(kind="plate")
        print("post-add aperture tilt:", ap_tilt(app))
    finally:
        app.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
