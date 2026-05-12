from __future__ import annotations

from KrakenOS.UI.layout_plot_controller import (
    build_preview_trace_signature,
    max_surface_radius,
    preview_trace_signature_matches,
)
from KrakenOS.UI.surface_table_model import SurfaceRow


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _signature(**overrides):
    values = {
        "row_specs_signature": ("rows", (("Object",), ("Image",))),
        "object_mode": "Finite",
        "field_type": "Angle",
        "field_value": "14.0",
        "field_count": "3",
        "requested_trace_mode": "Auto",
        "aperture_type_label": "EPD",
        "aperture_value": "25",
        "wavelength": "0.5876",
        "ray_count": "9",
        "ray_height_factor": "1.0",
        "source_model": "Gaussian Beam",
        "pupil_pattern_label": "Hexapolar",
        "source_radius": "5",
        "source_cone_angle": "0",
        "gaussian_input_mode": "Manufacturer diameter/divergence",
        "gaussian_waist_radius": "0.5",
        "gaussian_waist_offset": "12.5",
        "gaussian_beam_diameter": "1.2",
        "gaussian_full_divergence": "0.8",
        "gaussian_waist_after_input": False,
        "gaussian_m2": "1.1",
        "pupil_rad": "0",
        "pupil_theta": "0",
        "source_power": "2",
        "source_seed": "42",
        "source_origin": ("1", "2", "3"),
        "source_direction": ("0", "0", "1"),
        "source_angular_weight": "Uniform solid angle",
        "nonseq_energy_probability": True,
        "nonseq_ns_limit": "200",
        "nonseq_target_surface_index": None,
        "full_pupil_mode": False,
    }
    values.update(overrides)
    return build_preview_trace_signature(**values)


def main() -> None:
    rows = [
        SurfaceRow(surface="Object", diameter=10.0),
        SurfaceRow(surface="Standard", diameter=80.0),
        SurfaceRow(surface="Image", diameter=4.0),
    ]
    _require(max_surface_radius(rows) == 40.0, "max surface radius did not use largest diameter")
    _require(max_surface_radius([], default=2.5) == 2.5, "max surface radius did not honor default")
    _require(max_surface_radius([object()]) == 1.0, "max surface radius did not tolerate missing diameter")

    sig = _signature()
    same_sig = _signature(field_value=14.0, source_origin=(1.0, 2.0, 3.0))
    changed_sig = _signature(field_value=15.0)
    _require(preview_trace_signature_matches(sig, same_sig), "equivalent signatures did not compare equal")
    _require(not preview_trace_signature_matches(sig, changed_sig), "changed field value did not invalidate signature")

    _require(sig[3] == 14.0 and isinstance(sig[3], float), "field value was not normalized to float")
    _require(sig[4] == 3 and isinstance(sig[4], int), "field count was not normalized to int")
    _require(sig[26] == (1.0, 2.0, 3.0), "source origin was not normalized to float tuple")
    _require(sig[29] is True and sig[-1] is False, "boolean signature fields were not normalized")

    print("Layout plot controller validation passed.")


if __name__ == "__main__":
    main()
