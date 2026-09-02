"""0692: author the MEASURED sensor cover strips into the om05a bands.

Numbers from bugs/0692_sensor_reach_sweep.py (0695 vendor-true rebuild):
  arm A clean landings  z -30.14 .. -27.27  (object y -4..+3, ZERO per-field spread)
  arm B clean landings  z -23.69 .. -18.36  (~1.6 mm blur pending the 0696 launcher)
Sensor row centre [-272.65, -1.2, -26.4], die 23.04 x 23.04 in world x/z.
The coverage overlay draws each strip's two dashed edges (user: "draw 2 dotted
line edge at the Sensor to indicate actual cover area").
"""
from pathlib import Path

SCENE = Path("attachment/om05a_folded.py")


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = SCENE.resolve()
    editor.load_layout_by_name("p")

    bands = list(getattr(editor, "layout_object_fov_bands", []) or [])
    assert len(bands) == 2, f"expected 2 bands, found {len(bands)}"
    strips = {
        "Face A field": {"v_lo": -3.74, "v_hi": -0.87},
        "Face B field": {"v_lo": 2.71, "v_hi": 8.04},
    }
    stamped = 0
    for band in bands:
        strip = strips.get(str(band.get("name", "")))
        if strip is None:
            continue
        band["image_strip"] = {
            "center": [-272.65, -1.2, -26.4],
            "axis_v": [0.0, 0.0, 1.0],
            "half_width": 11.52,
            "v_lo": strip["v_lo"],
            "v_hi": strip["v_hi"],
        }
        stamped += 1
    assert stamped == 2, f"stamped {stamped} of 2 strips"
    editor.layout_object_fov_bands = bands
    editor._sync_table()
    editor._write_layout_file(SCENE.resolve())
    editor.destroy()
    print("stamped", stamped, "image strips into", SCENE)


if __name__ == "__main__":
    main()
