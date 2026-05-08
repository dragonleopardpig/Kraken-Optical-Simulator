"""Validate coherent-detector grouping modes."""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.layout_editor import COHERENT_SUM_MODE_VALUES
from KrakenOS.UI.validate_branch_analysis import _load_traced_editor, _preferred_output_or_terminal_filter


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value) -> None:
        self._value = value


def main() -> None:
    editor, system, _rays, wavelength = _load_traced_editor("Michelson Interferometer (Interferogram)")
    editor.coherent_sum_mode_var = _Var("By source ray")
    filter_text = _preferred_output_or_terminal_filter(editor)
    results = {}
    for mode in COHERENT_SUM_MODE_VALUES:
        editor.coherent_sum_mode_var.set(mode)
        data = editor._coherent_detector_field_data(system, wavelength, filter_text)
        assert int(data.get("sample_count", 0)) > 0, f"{mode}: expected detector samples"
        assert int(data.get("bins", 0)) >= 4, f"{mode}: expected detector bins"
        assert np.isfinite(float(data.get("peak_intensity", 0.0))) and float(data.get("peak_intensity", 0.0)) > 0.0, (
            f"{mode}: expected positive peak intensity"
        )
        results[mode] = data

    source_ray = results["By source ray"]
    assert int(source_ray.get("coherence_group_count", 0)) >= 1, "By source ray should report at least one coherence group"
    assert str(source_ray.get("coherence_mode", "")) == "By source ray"
    assert float(results["All rays coherent"]["total_coherent_power"]) > 0.0
    assert float(results["Incoherent power only"]["total_coherent_power"]) > 0.0
    print("Coherent detector mode validation passed.")


if __name__ == "__main__":
    main()
