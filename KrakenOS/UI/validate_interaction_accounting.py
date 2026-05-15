"""Validate per-hit interaction diagnostics and power accounting.

Run from the repository root:

    python -m KrakenOS.UI.validate_interaction_accounting
"""

from __future__ import annotations

import math

import numpy as np

import KrakenOS as Kos
from KrakenOS.Examples.Examp_Beam_Splitter_50_50 import trace_demo as trace_splitter
from KrakenOS.Examples.Examp_Diffuse_Object_Cosine_Lobe_Scatter import trace as trace_cosine
from KrakenOS.Examples.Examp_Diffuse_Object_Lambertian_Scatter import trace as trace_lambertian
from KrakenOS.Examples.Examp_Diffuse_Object_Oren_Nayar_Scatter import trace as trace_oren_nayar
from KrakenOS.Examples.Examp_Diffuse_Object_pySCATMECH_Microroughness import trace as trace_pyscatmech
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.validate_branch_analysis import _load_traced_editor
from KrakenOS.common_optical_layouts.diffuse_object_cosine_lobe_scatter import SURFACES as COSINE_SURFACES
from KrakenOS.common_optical_layouts.diffuse_object_lambertian_scatter import SURFACES as LAMBERTIAN_SURFACES
from KrakenOS.common_optical_layouts.diffuse_object_oren_nayar_scatter import SURFACES as OREN_NAYAR_SURFACES
from KrakenOS.common_optical_layouts.diffuse_object_pyscatmech_microroughness import SURFACES as PYSCATMECH_SURFACES
from KrakenOS.scatter_backend import pyscatmech_status


def _entry(rays, seq_name: str, ray_index: int, *, dtype=None) -> np.ndarray:
    seq = getattr(rays, seq_name, ())
    if seq is None or ray_index >= len(seq):
        return np.empty(0, dtype=(dtype or float))
    try:
        arr = np.asarray(seq[ray_index], dtype=dtype)
    except Exception:
        arr = np.asarray(seq[ray_index])
    return arr.ravel()


def _hit_records(rays) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    total_rays = len(getattr(rays, "SURFACE", ()) or ())
    for ray_index in range(total_rays):
        surface_arr = _entry(rays, "SURFACE", ray_index, dtype=int)
        interaction_type_arr = _entry(rays, "INTERACTION_TYPE", ray_index, dtype=object)
        interaction_model_arr = _entry(rays, "INTERACTION_MODEL", ray_index, dtype=object)
        interaction_target_arr = _entry(rays, "INTERACTION_TARGET_SURFACE", ray_index, dtype=float)
        interaction_in_power_arr = _entry(rays, "INTERACTION_IN_POWER", ray_index, dtype=float)
        interaction_coeff_arr = _entry(rays, "INTERACTION_COEFF", ray_index, dtype=float)
        interaction_out_power_arr = _entry(rays, "INTERACTION_OUT_POWER", ray_index, dtype=float)
        interaction_loss_power_arr = _entry(rays, "INTERACTION_LOSS_POWER", ray_index, dtype=float)
        interaction_bulk_arr = _entry(rays, "INTERACTION_BULK", ray_index, dtype=float)
        media_transition_arr = _entry(rays, "MEDIA_TRANSITION", ray_index, dtype=object)
        media_state_method_arr = _entry(rays, "MEDIA_STATE_METHOD", ray_index, dtype=object)
        media_state_diagnostic_arr = _entry(rays, "MEDIA_STATE_DIAGNOSTIC", ray_index, dtype=object)
        s_lmn_arr = _entry(rays, "S_LMN", ray_index, dtype=float).reshape(-1, 3) if _entry(rays, "S_LMN", ray_index, dtype=float).size else np.empty((0, 3), dtype=float)
        for hit_index, surface in enumerate(surface_arr):
            normal = s_lmn_arr[hit_index] if hit_index < s_lmn_arr.shape[0] else np.full(3, np.nan, dtype=float)
            records.append(
                {
                    "ray_index": ray_index,
                    "hit_index": hit_index,
                    "surface": int(surface),
                    "interaction_type": str(interaction_type_arr[hit_index]) if hit_index < interaction_type_arr.size else "",
                    "interaction_model": str(interaction_model_arr[hit_index]) if hit_index < interaction_model_arr.size else "",
                    "interaction_target_surface": float(interaction_target_arr[hit_index]) if hit_index < interaction_target_arr.size else math.nan,
                    "interaction_in_power": float(interaction_in_power_arr[hit_index]) if hit_index < interaction_in_power_arr.size else math.nan,
                    "interaction_coeff": float(interaction_coeff_arr[hit_index]) if hit_index < interaction_coeff_arr.size else math.nan,
                    "interaction_out_power": float(interaction_out_power_arr[hit_index]) if hit_index < interaction_out_power_arr.size else math.nan,
                    "interaction_loss_power": float(interaction_loss_power_arr[hit_index]) if hit_index < interaction_loss_power_arr.size else math.nan,
                    "interaction_bulk": float(interaction_bulk_arr[hit_index]) if hit_index < interaction_bulk_arr.size else math.nan,
                    "media_transition": str(media_transition_arr[hit_index]) if hit_index < media_transition_arr.size else "",
                    "media_state_method": str(media_state_method_arr[hit_index]) if hit_index < media_state_method_arr.size else "",
                    "media_state_diagnostic": str(media_state_diagnostic_arr[hit_index]) if hit_index < media_state_diagnostic_arr.size else "",
                    "surface_normal": np.asarray(normal, dtype=float),
                }
            )
    return records


def _assert_power_accounting(records: list[dict[str, object]], *, label: str) -> None:
    checked = 0
    for record in records:
        pin = float(record.get("interaction_in_power", math.nan))
        coeff = float(record.get("interaction_coeff", math.nan))
        pout = float(record.get("interaction_out_power", math.nan))
        ploss = float(record.get("interaction_loss_power", math.nan))
        if not all(np.isfinite(value) for value in (pin, coeff, pout, ploss)):
            continue
        assert math.isclose(pout, pin * coeff, rel_tol=1e-9, abs_tol=1e-9), (
            f"{label}: expected Pout=Pin*Coeff, got Pin={pin}, Coeff={coeff}, Pout={pout}"
        )
        expected_loss = max(pin - pout, 0.0)
        assert math.isclose(ploss, expected_loss, rel_tol=1e-9, abs_tol=1e-9), (
            f"{label}: expected Loss=max(Pin-Pout,0), got Pin={pin}, Pout={pout}, Loss={ploss}"
        )
        checked += 1
    assert checked > 0, f"{label}: no finite power-accounting hits were available"


def _validate_diffuse_example(trace_fn, surfaces, expected_model: str) -> None:
    diffuse_surface = next(index for index, spec in enumerate(surfaces) if spec.get("surface") == "Diffuse Object")
    expected_target = int(
        next(spec for spec in surfaces if spec.get("surface") == "Diffuse Object")
        .get("advanced", {})
        .get("DiffuseScatter", {})
        .get("target_surface", -1)
    )
    _system, rays = trace_fn()
    hits = [record for record in _hit_records(rays) if int(record["surface"]) == diffuse_surface]
    assert hits, f"{expected_model}: no diffuse-object hits were recorded"
    assert all(str(record["interaction_type"]) == "scatter" for record in hits), (
        f"{expected_model}: diffuse-object hits must record interaction_type='scatter'"
    )
    assert all(str(record["interaction_model"]) == expected_model for record in hits), (
        f"{expected_model}: diffuse-object hits must record interaction_model={expected_model!r}"
    )
    assert all(str(record["media_state_method"]) == "scatter_no_media_change" for record in hits), (
        f"{expected_model}: scatter child hits must use shared scatter media-state method"
    )
    assert all(str(record["media_transition"]) for record in hits), (
        f"{expected_model}: scatter child hits must populate media transition"
    )
    if expected_target >= 0:
        assert all(int(record["interaction_target_surface"]) == expected_target for record in hits), (
            f"{expected_model}: expected target surface S{expected_target}"
        )
    assert all(np.isfinite(np.asarray(record["surface_normal"], dtype=float)).all() for record in hits), (
        f"{expected_model}: diffuse-object hits must include a finite surface normal"
    )
    _assert_power_accounting(hits, label=expected_model)


def _validate_pyscatmech_example() -> None:
    diffuse_surface = next(index for index, spec in enumerate(PYSCATMECH_SURFACES) if spec.get("surface") == "Diffuse Object")
    _system, rays = trace_pyscatmech()
    hits = [record for record in _hit_records(rays) if int(record["surface"]) == diffuse_surface]
    assert hits, "pySCATMECH: no diffuse-object hits were recorded"
    assert all(str(record["interaction_type"]) == "scatter" for record in hits), (
        "pySCATMECH: diffuse-object hits must record interaction_type='scatter'"
    )
    status = pyscatmech_status()
    if bool(status.get("available")):
        assert all(str(record["interaction_model"]) == "pySCATMECH:Microroughness_BRDF_Model" for record in hits), (
            f"pySCATMECH: expected live backend interaction labels, got {[record['interaction_model'] for record in hits]}"
        )
    else:
        assert all(str(record["interaction_model"]).startswith("pySCATMECH fallback") for record in hits), (
            f"pySCATMECH: expected fallback labels, got {[record['interaction_model'] for record in hits]}"
        )
    _assert_power_accounting(hits, label="pySCATMECH")


def _validate_beam_splitter_example() -> None:
    rays = trace_splitter()
    hits = _hit_records(rays)
    split_hits = [record for record in hits if str(record["interaction_type"]).startswith("split_")]
    assert split_hits, "beam splitter example: expected split_* interaction hits"
    split_types = {str(record["interaction_type"]) for record in split_hits}
    assert "split_reflect" in split_types, f"beam splitter example: missing split_reflect in {sorted(split_types)}"
    assert "split_transmit" in split_types, f"beam splitter example: missing split_transmit in {sorted(split_types)}"
    assert all(np.isfinite(np.asarray(record["surface_normal"], dtype=float)).all() for record in split_hits), (
        "beam splitter example: split hits must include finite surface normals"
    )
    assert all(str(record["media_state_method"]) for record in split_hits), (
        "beam splitter example: split child hits must populate media_state_method"
    )
    assert all(str(record["media_transition"]) for record in split_hits), (
        "beam splitter example: split child hits must populate media_transition"
    )
    _assert_power_accounting(split_hits, label="Beam splitter")


def _validate_standard_surface_media_state() -> None:
    obj = Kos.surf()
    obj.Name = "Object"
    obj.Glass = "AIR"
    obj.Thickness = 10.0
    obj.Diameter = 25.0
    obj.Drawing = 0

    entry = Kos.surf()
    entry.Name = "BK7 entry"
    entry.Rc = 0.0
    entry.Glass = "BK7"
    entry.Thickness = 5.0
    entry.Diameter = 25.0

    exit_surface = Kos.surf()
    exit_surface.Name = "AIR exit"
    exit_surface.Rc = 0.0
    exit_surface.Glass = "AIR"
    exit_surface.Thickness = 20.0
    exit_surface.Diameter = 25.0

    image = Kos.surf()
    image.Name = "Image"
    image.Glass = "AIR"
    image.Diameter = 25.0

    system = Kos.system([obj, entry, exit_surface, image], Kos.Setup())
    system.energy_probability = 0
    system.NsTrace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)

    media_records = list(zip(
        [str(value) for value in getattr(system, "MEDIA_IN", [])],
        [str(value) for value in getattr(system, "MEDIA_OUT", [])],
        [str(value) for value in getattr(system, "MEDIA_TRANSITION", [])],
        [str(value) for value in getattr(system, "MEDIA_STATE_METHOD", [])],
    ))
    expected = [
        ("AIR", "BK7", "medium_change", "ray_state_surface_medium"),
        ("BK7", "AIR", "medium_change", "ray_state_surface_medium"),
        ("AIR", "AIR", "target_termination", "ray_state_target_terminal"),
    ]
    assert media_records[:3] == expected, (
        f"standard non-STL media state should follow surface materials, got {media_records}"
    )


def _validate_terminal_media_state() -> None:
    def _surface(name: str, glass: str = "AIR", thickness: float = 10.0):
        surface = Kos.surf()
        surface.Name = name
        surface.Glass = glass
        surface.Thickness = thickness
        surface.Diameter = 25.0
        surface.Drawing = 0
        return surface

    def _trace(surfaces):
        system = Kos.system(surfaces, Kos.Setup())
        system.energy_probability = 0
        system.NsTrace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
        return system

    absorber_system = _trace([
        _surface("Object", "AIR"),
        _surface("Absorber", "ABSORB"),
        _surface("Image", "AIR", 0.0),
    ])
    absorber_media = list(zip(
        [str(value) for value in getattr(absorber_system, "MEDIA_IN", [])],
        [str(value) for value in getattr(absorber_system, "MEDIA_OUT", [])],
        [str(value) for value in getattr(absorber_system, "MEDIA_TRANSITION", [])],
        [str(value) for value in getattr(absorber_system, "MEDIA_STATE_METHOD", [])],
    ))
    assert absorber_media[:1] == [("AIR", "AIR", "absorb", "ray_state_absorb_terminal")], (
        f"ABSORB terminal should preserve medium state and report absorption, got {absorber_media}"
    )
    absorber_interaction = [str(value) for value in getattr(absorber_system, "INTERACTION_TYPE", [])]
    absorber_power = [float(value) for value in getattr(absorber_system, "INTERACTION_OUT_POWER", [])]
    assert absorber_interaction[:1] == ["absorb"], (
        f"ABSORB terminal should report interaction_type='absorb', got {absorber_interaction}"
    )
    assert absorber_power and math.isclose(absorber_power[0], 0.0, abs_tol=1e-12), (
        f"ABSORB terminal should end with zero outgoing power, got {absorber_power}"
    )

    detector = _surface("Detector", "AIR")
    detector.Detector = {"kind": "area", "bins": 16}
    detector_system = _trace([
        _surface("Object", "AIR"),
        detector,
        _surface("Downstream surface", "AIR"),
        _surface("Image", "AIR", 0.0),
    ])
    detector_media = list(zip(
        [str(value) for value in getattr(detector_system, "MEDIA_IN", [])],
        [str(value) for value in getattr(detector_system, "MEDIA_OUT", [])],
        [str(value) for value in getattr(detector_system, "MEDIA_TRANSITION", [])],
        [str(value) for value in getattr(detector_system, "MEDIA_STATE_METHOD", [])],
    ))
    detector_interaction = [str(value) for value in getattr(detector_system, "INTERACTION_TYPE", [])]
    detector_surfaces = [int(value) for value in getattr(detector_system, "SURFACE", [])]
    assert detector_surfaces == [1], (
        f"detector metadata should terminate the non-sequential ray at S1, got {detector_surfaces}"
    )
    assert detector_media[:1] == [("AIR", "AIR", "detector_termination", "ray_state_detector_terminal")], (
        f"detector terminal should report detector termination, got {detector_media}"
    )
    assert detector_interaction[:1] == ["detector"], (
        f"detector terminal should report interaction_type='detector', got {detector_interaction}"
    )


def _validate_media_state_diagnostics() -> None:
    obj = Kos.surf()
    obj.Name = "Object"
    obj.Glass = "AIR"
    obj.Drawing = 0

    image = Kos.surf()
    image.Name = "Image"
    image.Glass = "AIR"
    image.Drawing = 0

    system = Kos.system([obj, image], Kos.Setup())
    initial_state = system._system__InitialNsRayState(1.0)
    inside_state = system._system__NsRayStateWith(
        initial_state,
        current_medium="BK7",
        current_index=1.5,
        inside_volumes=("volume:1",),
        method="test_inside",
    )
    _after, duplicate_entry = system._system__NsRayMediaEvent(
        inside_state,
        {
            "volume_id": "volume:1",
            "media_transition": "entry",
            "volume_material": "BK7",
            "media_state_method": "ray_state_inside_volumes",
        },
        1.5,
        1.0,
        media_out="BK7",
    )
    assert duplicate_entry["diagnostic"] == "volume_entry_already_inside:volume:1", (
        f"duplicate volume entry should be diagnosed, got {duplicate_entry}"
    )

    _after, orphan_exit = system._system__NsRayMediaEvent(
        initial_state,
        {
            "volume_id": "volume:1",
            "media_transition": "exit",
            "ambient_material": "AIR",
            "media_state_method": "ray_state_inside_volumes",
        },
        1.0,
        1.0,
        media_out="AIR",
    )
    assert orphan_exit["diagnostic"] == "volume_exit_without_entry:volume:1", (
        f"orphan volume exit should be diagnosed, got {orphan_exit}"
    )


def _validate_branch_termination_metadata() -> None:
    obj = Kos.surf()
    obj.Name = "Object"
    obj.Glass = "AIR"
    obj.Drawing = 0

    image = Kos.surf()
    image.Name = "Image"
    image.Glass = "AIR"
    image.Drawing = 0

    system = Kos.system([obj, image], Kos.Setup())
    rays = Kos.raykeeper(system)
    tree_diagnostic = "branch_result_limit_reached:limit=1, queued=2, recorded=1"
    rays._push_trace_snapshot(
        {
            "RAY": [[0.0, 0.0, 0.0], [0.0, 0.0, 50.0]],
            "SURFACE": [],
            "branch_id": 7,
            "branch_path": "synthetic/reflect",
            "branch_termination_reason": "no_next_intersection",
            "branch_termination_diagnostic": "synthetic branch miss",
            "branch_tree_diagnostic": tree_diagnostic,
            "val": 0,
            "tt": 0.0,
            "Wave": 0.55,
        }
    )
    assert str(np.asarray(rays.BRANCH_TERMINATION_REASON[0]).reshape(-1)[0]) == "no_next_intersection", (
        "raykeeper should preserve branch termination reason"
    )
    assert str(np.asarray(rays.BRANCH_TERMINATION_DIAGNOSTIC[0]).reshape(-1)[0]) == "synthetic branch miss", (
        "raykeeper should preserve branch termination diagnostics"
    )
    assert str(np.asarray(rays.BRANCH_TREE_DIAGNOSTIC[0]).reshape(-1)[0]) == tree_diagnostic, (
        "raykeeper should preserve branch-tree truncation diagnostics"
    )


def _validate_headless_ui_records() -> None:
    for layout_title, expected_event, expected_model in (
        ("Diffuse Object Lambertian Scatter", "scatter", "Lambertian"),
        ("Diffuse Object Oren-Nayar Scatter", "scatter", "Oren-Nayar"),
        ("Diffuse Object pySCATMECH Microroughness", "scatter", "pySCATMECH"),
        ("Beam Splitter Two Path Doublets", "split_reflect", ""),
    ):
        app, _system, _rays, _wavelength = _load_traced_editor(layout_title)
        records = app._collect_ray_inspector_records()
        assert records, f"{layout_title}: headless Ray Inspector returned no records"
        hits = [hit for record in records for hit in list(record.get("hits", []) or [])]
        assert hits, f"{layout_title}: headless Ray Inspector returned no hit rows"
        matching = [hit for hit in hits if str(hit.get("event", "")) == expected_event]
        if not matching and expected_event == "split_reflect":
            matching = [hit for hit in hits if str(hit.get("event", "")).startswith("split_")]
        assert matching, f"{layout_title}: expected hit event {expected_event!r} in Ray Inspector"
        assert all("normal_l" in hit and "interaction_out_power" in hit for hit in matching), (
            f"{layout_title}: Ray Inspector hits must expose normal and power columns"
        )
        assert all("media_state_diagnostic" in hit for hit in matching), (
            f"{layout_title}: Ray Inspector hits must expose media-state diagnostics"
        )
        if expected_model:
            if expected_model == "pySCATMECH":
                assert any(
                    str(hit.get("interaction_model", "")).startswith("pySCATMECH")
                    for hit in matching
                ), f"{layout_title}: expected pySCATMECH interaction labels in Ray Inspector"
            else:
                assert any(str(hit.get("interaction_model", "")) == expected_model for hit in matching), (
                    f"{layout_title}: expected interaction_model={expected_model!r} in Ray Inspector"
                )


def main() -> None:
    _validate_diffuse_example(trace_lambertian, LAMBERTIAN_SURFACES, "Lambertian")
    _validate_diffuse_example(trace_cosine, COSINE_SURFACES, "Cosine Lobe")
    _validate_diffuse_example(trace_oren_nayar, OREN_NAYAR_SURFACES, "Oren-Nayar")
    _validate_pyscatmech_example()
    _validate_beam_splitter_example()
    _validate_standard_surface_media_state()
    _validate_terminal_media_state()
    _validate_media_state_diagnostics()
    _validate_branch_termination_metadata()
    _validate_headless_ui_records()
    print("Interaction accounting validation passed.")


if __name__ == "__main__":
    main()
