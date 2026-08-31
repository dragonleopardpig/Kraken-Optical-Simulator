"""Inject the om05a display_fold_spec (0671, CAD-derived fold planes) into the
straight scene and render the folded view off-screen. Plane points sit ON the beam
path (AABB-centre points accumulate lateral error through parallel-plane pairs)."""
from pathlib import Path

R = 0.7071067811865476
SPEC = {
    "body_step": "attachment/om05a_26_1_r03_2s_lr_asm.stp",
    "arms": [
        {   # arm A: the +z device face
            "origin": [-89.3, 160.95, 30.4], "u": [1, 0, 0], "v": [0, 1, 0], "n": [0, 0, 1],
            "y_center": 5.5, "y_range": [0.5, 1e9], "aperture_half": 5.0,
            "folds": [
                {"point": [-89.3, 160.95, 35.75], "normal": [0, R, R]},
                {"point": [-89.3, 149.30, 35.75], "normal": [0, R, -R]},
                {"point": [-89.3, 149.30, 6.00], "normal": [0, R, -R]},
                {"point": [-89.3, 108.15, 1.50], "normal": [R, R, 0]},
                {"point": [183.4, 108.20, 1.50], "normal": [R, -R, 0]},
            ],
        },
        {   # arm B: the -z device face
            "origin": [-89.3, 160.95, -27.4], "u": [1, 0, 0], "v": [0, 1, 0], "n": [0, 0, -1],
            "y_center": -5.5, "y_range": [-1e9, -0.5], "aperture_half": 5.0,
            "folds": [
                {"point": [-89.3, 160.95, -32.75], "normal": [0, R, -R]},
                {"point": [-89.3, 149.30, -32.75], "normal": [0, R, R]},
                {"point": [-89.3, 149.30, -2.00], "normal": [0, R, R]},
                {"point": [-89.3, 108.15, 1.50], "normal": [R, R, 0]},
                {"point": [183.4, 108.20, 1.50], "normal": [R, -R, 0]},
            ],
        },
    ],
}


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.folded_display_compose import compose_folded_assembly_plotter

    scene = Path("attachment/om05a_two_side.py").resolve()
    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["om"] = scene
    editor.load_layout_by_name("om")
    editor.display_fold_spec = SPEC
    editor._sync_table()
    editor._write_layout_file(scene)
    print("spec injected + saved")
    plotter, report = compose_folded_assembly_plotter(editor, off_screen=True)
    print("report:", {k: v for k, v in report.items() if k != "errors"})
    plotter.close()
    editor.destroy()


if __name__ == "__main__":
    main()
