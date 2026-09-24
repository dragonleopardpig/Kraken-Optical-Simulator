"""Validate coherent-detector grouping modes."""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.coherent_detector_analysis import COHERENT_SUM_MODE_VALUES
from KrakenOS.UI.validate_branch_analysis import _load_traced_editor, _preferred_output_or_terminal_filter


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value) -> None:
        self._value = value


def run_checks() -> tuple[bool, list[str]]:
    """Penta-harness entry point (bugs/0877): this guard is a registered phase now.

    `main()` asserts rather than collecting, so turn the first failed assertion into the note.
    """
    import contextlib
    import io

    stream = io.StringIO()
    try:
        with contextlib.redirect_stdout(stream):
            main()
    except AssertionError as exc:
        return False, [f"FAIL coherent detector modes: {exc}"]
    notes = [("= " + line) for line in stream.getvalue().splitlines() if line.strip()]
    return True, notes or ["= every coherent sum mode reports detector samples"]


def main() -> None:
    editor, system, rays, wavelength = _load_traced_editor("Michelson Interferometer (Interferogram)")
    editor.coherent_sum_mode_var = _Var("By source ray")
    # bugs/0877: derive the filter from the DENSE retrace's records. Without them the
    # helper reads the editor's stale single-arm records, where the recombined detector
    # path does not exist yet, and refuses with "No detector output or terminal path
    # filter found" on a scene whose detector is working perfectly.
    filter_text = _preferred_output_or_terminal_filter(
        editor,
        ray_records=editor._ray_analysis_records_for_trace(system=system, rays=rays),
    )
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
