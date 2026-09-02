"""0692: author the MEASURED sensor cover strips into the om05a bands.

Numbers from bugs/0692_sensor_reach_sweep.py (0696 phantom-glass fix + balance):
  arm A clean landings  z -30.25 .. -27.25  (band y -4..+4, razor per field)
  arm B clean landings  z -23.29 .. -20.18  (band, 76% uniform reach)
The strip centre is read LIVE from the Image row (the balance stamp moves it).
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

    import numpy as np
    editor._preview_trace_deferred_until_requested = False
    system, _rays, _bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    from KrakenOS.UI.services.detector_coverage_overlay import _basis

    img_row = next(i for i, r in enumerate(editor.rows) if str(r.surface) == "Image")
    centre = np.asarray(
        editor._surface_reference_world_point(img_row, system=system), dtype=float
    )
    cz = float(centre[2])
    # bugs/0697: v_lo/v_hi are authored along the DETECTOR'S OWN in-plane strip
    # axis (the overlay reconstructs it from the live pose after any rotation).
    det = next(t2 for t2 in (getattr(_bundle, "targets", []) or [])
               if bool(getattr(t2, "is_detector", False)))
    normal = np.asarray(det.normal_world, dtype=float).reshape(3)
    _iu, iv = _basis(normal)
    z_hat_v = float(iv[2])  # how world z projects onto the strip axis
    assert abs(z_hat_v) > 0.9, f"strip axis not z-aligned on the saved scene: iv={iv}"
    print(f"live sensor centre: {np.round(centre, 3)}; iv {np.round(iv, 3)}")
    bands = list(getattr(editor, "layout_object_fov_bands", []) or [])
    assert len(bands) == 2, f"expected 2 bands, found {len(bands)}"
    ABS_Z = {
        "Face A field": (-30.25, -27.25),
        "Face B field": (-23.29, -20.18),
    }
    strips = {}
    for name, (lo, hi) in ABS_Z.items():
        a, b = (lo - cz) * z_hat_v, (hi - cz) * z_hat_v
        strips[name] = {"v_lo": round(min(a, b), 3), "v_hi": round(max(a, b), 3)}
    print("strips (detector frame):", strips)
    stamped = 0
    for band in bands:
        strip = strips.get(str(band.get("name", "")))
        if strip is None:
            continue
        band["image_strip"] = {
            "center": [float(centre[0]), float(centre[1]), float(cz)],
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
