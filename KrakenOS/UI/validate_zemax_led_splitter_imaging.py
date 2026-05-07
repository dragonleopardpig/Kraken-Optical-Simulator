"""Validate the source-driven Zemax LED beam-splitter imaging fixture.

Run from the repository root:

    python -m KrakenOS.UI.validate_zemax_led_splitter_imaging
"""

from __future__ import annotations

from KrakenOS.Examples.Examp_Zemax_LED_Beam_Splitter_Imaging import summarize_trace, trace_demo
from KrakenOS.common_optical_layouts.zemax_led_beam_splitter_imaging import SETTINGS, SURFACES
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor


def main() -> None:
    system, rays = trace_demo(ray_count=21)
    records = summarize_trace(rays)
    assert SETTINGS["source_model"] == "Zemax rayfile source"
    assert SETTINGS["scene_sources"], "layout must declare an explicit physical LED source"
    assert SETTINGS["scene_sources"][0]["model"] == "Zemax rayfile source"

    diffuse_object = 3
    splitter = 1
    lens_surfaces = {4, 5}
    image = len(system.SDT) - 1
    assert SURFACES[diffuse_object]["surface"] == "Diffuse Object", "fixture should use a diffuse object target"
    diffuse_settings = SURFACES[diffuse_object].get("advanced", {}).get("DiffuseScatter", {})
    assert diffuse_settings.get("model") == "Lambertian", "diffuse object should use the built-in Lambertian model"
    assert int(diffuse_settings.get("target_surface", -1)) == splitter, "diffuse object should guide samples toward the splitter return aperture"
    useful_records = [
        record
        for record in records
        if diffuse_object in record["surfaces"]
        and splitter in record["surfaces"]
        and splitter in record["surfaces"][record["surfaces"].index(diffuse_object) + 1 :]
        and image in record["surfaces"]
        and bool(lens_surfaces.intersection(record["surfaces"]))
        and "/scatter" in str(record["path"])
    ]
    assert useful_records, (
        "expected at least one source-launched ray to reflect to the diffuse object, "
        "scatter back through the beam splitter, pass the imaging lens, and reach Image"
    )
    assert all(record["source"] == "OSRAM LSG T676 green rayfile" for record in useful_records)
    editor = _snapshot_editor(_rows_from_layout_info({"surfaces": SURFACES, "settings": SETTINGS}), SETTINGS)
    graph_records = editor._collect_nonseq_scene_graph_records()
    source_record = next(
        (
            record
            for record in graph_records
            if str(record.get("id", "")) == str(SETTINGS["scene_sources"][0]["source_id"])
            and str(record.get("kind", "")) == "Source"
        ),
        None,
    )
    assert source_record is not None, "scene graph should expose the Zemax rayfile source"
    assert ".DAT" in str(source_record.get("detail", "")), "scene graph detail should include the rayfile name"
    print(f"Zemax LED splitter imaging validation passed ({len(useful_records)} useful ray record(s)).")


if __name__ == "__main__":
    main()
