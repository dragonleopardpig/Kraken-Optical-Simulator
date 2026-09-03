"""flag 094237 repro: swap om05a's lens for the PYRITE 5.6/80 and dump the fold
mirror 2 + front-datum placement after EVERY swap settle stage, to catch which
stage mirrors desp_x and drops the vendor frame-desp."""
import shutil
from pathlib import Path


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    work = Path("/tmp/claude-1000/-home-thinky-Projects/15653223-dbcf-4a7a-bb47-d26cbd830f16/scratchpad/om05a_swap_test.py")
    shutil.copyfile("attachment/om05a_folded.py", work)

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = work.resolve()
    editor.load_layout_by_name("p")

    def snap(tag):
        for r in editor.rows:
            n = str(getattr(r, "name", ""))
            if "RA mirror 2" in n:
                print(f"[{tag}] mirror2 desp=({r.desp_x:.2f},{r.desp_y:.2f},{r.desp_z:.2f}) "
                      f"tilt=({r.tilt_x:.4g},{r.tilt_y:.4g},{r.tilt_z:.4g})")
            if "Front Optical Vertex Datum" in n:
                print(f"[{tag}] frontdatum desp=({r.desp_x:.4g},{r.desp_y:.4g},{r.desp_z:.4g})")

    snap("before-swap")

    for name in (
        "_swap_apply_frozen_block_frame",
        "_swap_reseat_preserved_rows",
        "_swap_world_settle",
        "center_lens_body_on_surrogate_axis",
        "slide_fold_arm_along_leg",
        "refit_lens_principal_to_datasheet_wd",
    ):
        orig = getattr(editor, name)

        def wrap(orig=orig, name=name):
            def inner(*a, **k):
                out = orig(*a, **k)
                snap(f"after {name}")
                return out
            return inner

        setattr(editor, name, wrap())

    model = editor.swap_imaging_lens_from_folder(
        "attachment/Lens/PYRITE_56_80_10x_V38_1097785"
    )
    print("swap returned:", type(model).__name__ if model is not None else None)
    snap("after-swap-complete")


if __name__ == "__main__":
    main()
