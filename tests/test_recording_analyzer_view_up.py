"""bugs/0498 -- the recording analyzer must not warn about a legitimate camera orientation.

``_check_view_up_drift`` compared every event against a hardcoded world +Y up, so a scene viewed
from TOP (``view_up = (0, 0, -1)``, the AZ85 machine-vision default and what the nav cube reads)
tripped it on EVERY event: ``recording_20260801_204025`` produced 172 warnings for 172 events and
buried its one real line. An analyzer that reports a finding per event is not an analyzer.

Drift means the vector CHANGING under an interaction that should have kept it locked, so the check
now compares consecutive events. These hold both halves: silent on a steady orientation whatever
axis it is, and still loud on a real flip.
"""
from __future__ import annotations

from KrakenOS.UI.analyze_open3d_recording import _check_view_up_drift


def _event(timestamp_ms: float, view_up) -> dict:
    return {"timestamp_ms": timestamp_ms, "scene_state": {"camera_view_up": list(view_up)}}


def test_steady_top_view_is_silent():
    """The orientation that made the analyzer useless: -Z up, held for the whole session."""
    events = [_event(i * 10.0, (0.0, 0.0, -1.0)) for i in range(50)]
    findings: list = []
    _check_view_up_drift(events, findings)
    assert findings == [], f"a steady TOP view must not warn at all, got {len(findings)}"


def test_steady_y_up_is_silent():
    """...and so is the orientation the old check happened to hardcode."""
    events = [_event(i * 10.0, (0.0, 1.0, 0.0)) for i in range(20)]
    findings: list = []
    _check_view_up_drift(events, findings)
    assert findings == []


def test_a_flip_is_reported_once_at_the_transition():
    events = [_event(i * 10.0, (0.0, 0.0, -1.0)) for i in range(20)]
    events += [_event(200.0 + i * 10.0, (0.0, 0.0, 1.0)) for i in range(30)]
    findings: list = []
    _check_view_up_drift(events, findings)
    assert len(findings) == 1, f"one transition, one finding -- got {len(findings)}"
    assert findings[0].event_index == 20
    assert findings[0].code == "camera_view_up_drift"


def test_gradual_drift_still_reported_per_changing_event():
    events = [_event(i * 10.0, (0.0, i * 0.02, -1.0)) for i in range(6)]
    findings: list = []
    _check_view_up_drift(events, findings)
    assert [f.event_index for f in findings] == [1, 2, 3, 4, 5]


def test_malformed_view_up_is_skipped_not_crashed():
    events = [
        _event(0.0, (0.0, 0.0, -1.0)),
        {"timestamp_ms": 10.0, "scene_state": {"camera_view_up": []}},
        {"timestamp_ms": 20.0, "scene_state": {}},
        {"timestamp_ms": 30.0, "scene_state": {"camera_view_up": ["x", "y", "z"]}},
        _event(40.0, (0.0, 0.0, -1.0)),
    ]
    findings: list = []
    _check_view_up_drift(events, findings)
    assert findings == []
