"""Validate the source-driven Zemax LED beam-splitter imaging fixture.

Run from the repository root:

    python -m KrakenOS.UI.validate_zemax_led_splitter_imaging
"""

from __future__ import annotations

from KrakenOS.Examples.Examp_Zemax_LED_Beam_Splitter_Imaging import summarize_trace, trace_demo
from KrakenOS.common_optical_layouts.zemax_led_beam_splitter_imaging import SETTINGS


def main() -> None:
    system, rays = trace_demo(ray_count=21)
    records = summarize_trace(rays)
    assert SETTINGS["source_model"] == "Zemax rayfile source"
    assert SETTINGS["scene_sources"], "layout must declare an explicit physical LED source"
    assert SETTINGS["scene_sources"][0]["model"] == "Zemax rayfile source"

    object_target = 3
    splitter = 1
    lens_surfaces = {4, 5}
    image = len(system.SDT) - 1
    useful_records = [
        record
        for record in records
        if object_target in record["surfaces"]
        and splitter in record["surfaces"]
        and image in record["surfaces"]
        and bool(lens_surfaces.intersection(record["surfaces"]))
    ]
    assert useful_records, (
        "expected at least one source-launched ray to reflect to the object target, "
        "return through the beam splitter, pass the imaging lens, and reach Image"
    )
    assert all(record["source"] == "OSRAM LSG T676 green rayfile" for record in useful_records)
    print(f"Zemax LED splitter imaging validation passed ({len(useful_records)} useful ray record(s)).")


if __name__ == "__main__":
    main()
