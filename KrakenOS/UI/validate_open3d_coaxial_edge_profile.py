"""Guard: the coaxial-illuminator edge-profile selector (bugs/0401).

The "Edit Source..." dialog on a COAXIAL LED illuminator gains an *Illumination edge* control:
a profile (``Flat-top, soft edge`` vs ``Uniform, sharp edge``) plus a calibratable *Edge width
(mm)*. It maps onto the existing ``coaxial_penumbra_mm`` spec key that the kernel's raised-cosine
roll-off (``source_object_coupling._aperture_soft_edge``) already consumes -- so the user can dial
the soft edge (e.g. the ~2 mm-per-side dark edge on MV-150) without any new kernel path.

This guard is display-free (no renderer / no Tk / no llvmpipe segfault): it drives the REAL
``update_scene_source_spec`` through its editable-key whitelist against a minimal stub, exercises the
forward/inverse mapping + the descriptor coupling, and asserts the dialog wiring via
``inspect.getsource``.

The one trap this guards (same class as bugs/0397's dropped BS marker): ``update_scene_source_spec``
only lets keys in ``SCENE_SOURCE_EDITABLE_KEYS`` through, so an un-whitelisted ``coaxial_edge_profile``
/ ``coaxial_penumbra_mm`` would be SILENTLY dropped on apply -- the control would look wired yet never
persist. WHITELIST asserts both keys survive an actual update while a junk key is still dropped.

Checks
------
* MAP        -- (profile, edge-width text) -> ``coaxial_penumbra_mm``: soft+Auto/blank/garbage -> 0.0
  (kernel auto); soft+number -> that width; sharp -> a sub-bin 0.01 (hard step), ignoring width.
* SEED       -- inverse: a stored spec re-seeds (profile, width) for the dialog; explicit
  ``coaxial_edge_profile`` wins, else inferred from ``coaxial_penumbra_mm``.
* DESCRIPTOR -- the stored penumbra reaches ``coaxial_illuminator_descriptor``: soft+auto -> None
  (kernel ~6%), soft+2 -> 2.0, sharp -> 0.01.
* WHITELIST  -- a real ``update_scene_source_spec`` persists BOTH new keys (and refreshes them on a
  second edit) while a non-editable junk key is dropped.
* WIRING     -- the dialog seeds from ``coaxial_edge_profile_and_width``, writes both keys via
  ``coaxial_edge_penumbra_mm`` gated on ``is_coaxial``; the whitelist tuple lists both keys.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_coaxial_edge_profile

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

from KrakenOS.UI.scene_source_analysis import (
    COAXIAL_EDGE_PROFILE_SHARP,
    COAXIAL_EDGE_PROFILE_SOFT,
    COAXIAL_EDGE_PROFILES,
    COAXIAL_ILLUMINATOR_KEY,
    coaxial_edge_penumbra_mm,
    coaxial_edge_profile_and_width,
    coaxial_illuminator_descriptor,
    dedupe_scene_source_ids,
    normalize_scene_source_specs,
)
from KrakenOS.UI.services.source_modeling import SourceModelingMixin

_SHARP = 0.01


class _StubSourceEditor:
    """Drive the real ``update_scene_source_spec`` (whitelist + normalize) display-free."""

    update_scene_source_spec = SourceModelingMixin.update_scene_source_spec
    SCENE_SOURCE_EDITABLE_KEYS = SourceModelingMixin.SCENE_SOURCE_EDITABLE_KEYS
    _dedupe_scene_source_ids = staticmethod(dedupe_scene_source_ids)

    def __init__(self, specs):
        self.layout_scene_source_specs = list(specs or [])
        self._last_status = ""

    def _normalize_scene_source_specs(self, value):
        return normalize_scene_source_specs(value)

    def _apply_scene_source_row_action_specs(self, specs, *, record_history=True, status=""):
        # Mirror _set_scene_source_specs' effect only (normalize + dedupe) -- no Tk / plot.
        self.layout_scene_source_specs = self._dedupe_scene_source_ids(
            self._normalize_scene_source_specs(specs)
        )
        self._last_status = status


def _coaxial_spec(profile, edge_text, source_id="source:led-1"):
    return {
        "source_id": source_id,
        "name": "Coaxial LED",
        "model": "Random rectangle source",
        "physical": True,
        "enabled": True,
        COAXIAL_ILLUMINATOR_KEY: True,
        "coaxial_aperture_fold_mm": 39.0,
        "coaxial_aperture_perp_mm": 39.0,
        "coaxial_edge_profile": profile,
        "coaxial_penumbra_mm": coaxial_edge_penumbra_mm(profile, edge_text),
    }


def _check_map(failures, notes):
    cases = [
        (COAXIAL_EDGE_PROFILE_SOFT, "Auto", 0.0),
        (COAXIAL_EDGE_PROFILE_SOFT, "", 0.0),
        (COAXIAL_EDGE_PROFILE_SOFT, "2.0", 2.0),
        (COAXIAL_EDGE_PROFILE_SOFT, "garbage", 0.0),
        (COAXIAL_EDGE_PROFILE_SOFT, "-3", 0.0),  # non-positive -> auto
        (COAXIAL_EDGE_PROFILE_SHARP, "Auto", _SHARP),
        (COAXIAL_EDGE_PROFILE_SHARP, "5", _SHARP),  # sharp ignores width
    ]
    for prof, txt, want in cases:
        got = coaxial_edge_penumbra_mm(prof, txt)
        if abs(got - want) > 1e-9:
            failures.append(f"MAP: ({prof!r}, {txt!r}) -> {got}, expected {want}")
    if not [f for f in failures if f.startswith("MAP")]:
        notes.append("map: soft+Auto/blank/bad->0 (auto), soft+num->num, sharp->0.01 hard step")


def _check_seed(failures, notes):
    # Explicit profile wins and round-trips the width.
    cases = [
        (COAXIAL_EDGE_PROFILE_SOFT, "Auto", (COAXIAL_EDGE_PROFILE_SOFT, "Auto")),
        (COAXIAL_EDGE_PROFILE_SOFT, "2.0", (COAXIAL_EDGE_PROFILE_SOFT, "2")),
        (COAXIAL_EDGE_PROFILE_SHARP, "Auto", (COAXIAL_EDGE_PROFILE_SHARP, "Auto")),
    ]
    for prof, txt, want in cases:
        got = coaxial_edge_profile_and_width(_coaxial_spec(prof, txt))
        if got != want:
            failures.append(f"SEED: spec({prof!r},{txt!r}) re-seeds {got}, expected {want}")
    # Inference with NO explicit profile: a real penumbra -> Soft(width); a sub-bin -> Sharp; unset -> Soft/Auto.
    inferred = coaxial_edge_profile_and_width(
        {COAXIAL_ILLUMINATOR_KEY: True, "coaxial_penumbra_mm": 2.5}
    )
    if inferred != (COAXIAL_EDGE_PROFILE_SOFT, "2.5"):
        failures.append(f"SEED: infer 2.5 -> {inferred}, expected soft/2.5")
    inferred_sharp = coaxial_edge_profile_and_width(
        {COAXIAL_ILLUMINATOR_KEY: True, "coaxial_penumbra_mm": _SHARP}
    )
    if inferred_sharp != (COAXIAL_EDGE_PROFILE_SHARP, "Auto"):
        failures.append(f"SEED: infer 0.01 -> {inferred_sharp}, expected sharp/Auto")
    inferred_none = coaxial_edge_profile_and_width({COAXIAL_ILLUMINATOR_KEY: True})
    if inferred_none != (COAXIAL_EDGE_PROFILE_SOFT, "Auto"):
        failures.append(f"SEED: infer unset -> {inferred_none}, expected soft/Auto")
    if not [f for f in failures if f.startswith("SEED")]:
        notes.append("seed: explicit profile wins + width round-trip; else inferred from penumbra")


def _check_descriptor(failures, notes):
    # The stored penumbra reaches the kernel-facing descriptor exactly.
    d_auto = coaxial_illuminator_descriptor(_coaxial_spec(COAXIAL_EDGE_PROFILE_SOFT, "Auto"))
    if d_auto is None or d_auto.get("penumbra_mm") is not None:
        failures.append(f"DESCRIPTOR: soft+Auto should give penumbra None (kernel auto), got {d_auto}")
    d_num = coaxial_illuminator_descriptor(_coaxial_spec(COAXIAL_EDGE_PROFILE_SOFT, "2.0"))
    if d_num is None or abs(float(d_num.get("penumbra_mm")) - 2.0) > 1e-9:
        failures.append(f"DESCRIPTOR: soft+2.0 should give penumbra 2.0, got {d_num}")
    d_sharp = coaxial_illuminator_descriptor(_coaxial_spec(COAXIAL_EDGE_PROFILE_SHARP, "Auto"))
    if d_sharp is None or abs(float(d_sharp.get("penumbra_mm")) - _SHARP) > 1e-9:
        failures.append(f"DESCRIPTOR: sharp should give penumbra {_SHARP}, got {d_sharp}")
    if not [f for f in failures if f.startswith("DESCRIPTOR")]:
        notes.append("descriptor: soft+auto->None, soft+2->2.0, sharp->0.01 reach the kernel reader")


def _check_whitelist(failures, notes):
    # The REAL update path must persist BOTH keys (the 0397-class whitelist trap) and refresh them.
    editor = _StubSourceEditor([_coaxial_spec(COAXIAL_EDGE_PROFILE_SOFT, "Auto")])
    ok = editor.update_scene_source_spec(
        "source:led-1",
        {
            "coaxial_edge_profile": COAXIAL_EDGE_PROFILE_SOFT,
            "coaxial_penumbra_mm": 2.0,
            "not_an_editable_key": 123,  # must be dropped
        },
    )
    if not ok:
        failures.append("WHITELIST: update_scene_source_spec returned False for a known source")
        return
    spec = editor.layout_scene_source_specs[0]
    if str(spec.get("coaxial_edge_profile")) != COAXIAL_EDGE_PROFILE_SOFT:
        failures.append(f"WHITELIST: coaxial_edge_profile dropped on update (got {spec.get('coaxial_edge_profile')!r})")
    if abs(float(spec.get("coaxial_penumbra_mm", -1)) - 2.0) > 1e-9:
        failures.append(f"WHITELIST: coaxial_penumbra_mm dropped/wrong (got {spec.get('coaxial_penumbra_mm')!r})")
    if "not_an_editable_key" in spec:
        failures.append("WHITELIST: a non-editable key leaked through the whitelist")
    # Second edit -> Sharp: the descriptor must now read the hard step (proves it refreshes, not append-once).
    editor.update_scene_source_spec(
        "source:led-1",
        {"coaxial_edge_profile": COAXIAL_EDGE_PROFILE_SHARP, "coaxial_penumbra_mm": _SHARP},
    )
    d = coaxial_illuminator_descriptor(editor.layout_scene_source_specs[0])
    if d is None or abs(float(d.get("penumbra_mm")) - _SHARP) > 1e-9:
        failures.append(f"WHITELIST: second edit to Sharp did not take (descriptor {d})")
    if not [f for f in failures if f.startswith("WHITELIST")]:
        notes.append("whitelist: update persists+refreshes both coaxial edge keys; junk key dropped")


def _check_wiring(failures, notes):
    from KrakenOS.UI.panels import open3d_source_edit_dialog as dlg

    src = inspect.getsource(dlg.open_scene_source_edit_dialog)
    for token in (
        "coaxial_edge_profile_and_width",  # seed
        "coaxial_edge_penumbra_mm",        # apply
        "COAXIAL_EDGE_PROFILES",           # combobox values
        "is_coaxial",                      # gate
        "coaxial_edge_profile",            # written key
        "coaxial_penumbra_mm",             # written key
    ):
        if token not in src:
            failures.append(f"WIRING: dialog missing {token!r}")
    # Both keys must be in the editable whitelist or the apply silently no-ops.
    for key in ("coaxial_edge_profile", "coaxial_penumbra_mm"):
        if key not in SourceModelingMixin.SCENE_SOURCE_EDITABLE_KEYS:
            failures.append(f"WIRING: {key!r} missing from SCENE_SOURCE_EDITABLE_KEYS")
    if len(COAXIAL_EDGE_PROFILES) != 2:
        failures.append(f"WIRING: expected 2 edge profiles, got {COAXIAL_EDGE_PROFILES}")
    if not [f for f in failures if f.startswith("WIRING")]:
        notes.append("wiring: dialog gated on is_coaxial seeds+writes both keys; both whitelisted")


def run_checks() -> "tuple[bool, list[str]]":
    """Penta entry point: ``(passed, notes)``. Info notes carry ``=`` so the harness'
    failure-count metric (``n for n in notes if '=' not in n``) only tallies real failures."""
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_map, _check_seed, _check_descriptor, _check_whitelist, _check_wiring):
        try:
            check(failures, notes)
        except Exception as exc:  # a crash is a failure, not a stack trace
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    # Info notes must contain '=' so the penta detail metric never miscounts them as failures.
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_coaxial_edge_profile (bugs/0401) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll coaxial edge-profile checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
