"""Validate Zemax non-sequential Source File import support.

Run from the repository root:

    python -m KrakenOS.UI.validate_zemax_rayfile_source
"""

from __future__ import annotations

from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SOURCE_MODEL_ZEMAX_RAYFILE
from KrakenOS.UI.zemax_rayfile import find_zemax_nsc_source_files, sample_zemax_rayfile, summarize_zemax_rayfile


def main() -> None:
    zmx_path = Path("attachment/LED/rayfile_LSG_T676_20200827_Zemax/LSG_T676_20200827_sample_Zemax.zmx")
    if not zmx_path.exists():
        raise FileNotFoundError(f"Expected OSRAM sample Zemax file at {zmx_path}")

    refs = find_zemax_nsc_source_files(zmx_path)
    assert len(refs) == 2, f"expected red and green NSC_SFIL sources, got {len(refs)}"
    for ref in refs:
        summary = summarize_zemax_rayfile(ref.rayfile_path)
        assert summary.record_count == 5_000_000, f"{ref.rayfile_path.name}: unexpected record count"
        bundle = sample_zemax_rayfile(ref.rayfile_path, 7)
        assert all(len(values) == 7 for values in bundle), f"{ref.rayfile_path.name}: sample shape mismatch"

    app = KrakenLayoutEditor(headless=True)
    try:
        app.auto_save_plot_var.set(False)
        app._load_zemax_prescription_path(zmx_path)
        assert app.source_model_var.get() == SOURCE_MODEL_ZEMAX_RAYFILE
        assert [row.surface for row in app.rows] == ["Object", "Image"]
        assert len(app.layout_scene_source_specs) == 2
        assert all(spec.get("model") == SOURCE_MODEL_ZEMAX_RAYFILE for spec in app.layout_scene_source_specs)
        assert [source.model for source in app._visible_table_scene_sources()] == [SOURCE_MODEL_ZEMAX_RAYFILE, SOURCE_MODEL_ZEMAX_RAYFILE]
    finally:
        app.destroy()

    print("Zemax rayfile source import validation passed.")


if __name__ == "__main__":
    main()
