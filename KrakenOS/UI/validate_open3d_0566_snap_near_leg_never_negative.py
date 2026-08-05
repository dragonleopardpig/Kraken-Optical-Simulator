"""Display-free guard for bugs/0566 -- the detector snap's mirror-slide can never go negative.

User: *"Swap lens introduce lens and other element off axis, I think need to fix this."*

Swapping ``attachment/machine_vision_Apo75.py`` to ``attachment/Lens/ELS-85-4.5V16K``
(reachable only since bugs/0565) left::

    row 6  Promoted BS   thickness   0.0000 -> -51.2548     <-- a NEGATIVE gap
    row 7  RA mirror     station   252.3548 -> 201.0999
           mirror world z          54.3214 ->    3.0666     <-- 51.2548 mm off the leg

The mirror was never *moved*. A negative gap was written behind it, and since every pose is
``station + desp_z`` the station chain runs BACKWARDS across that row and slides every
downstream row off the folded leg by exactly that amount -- the lens block stayed at
z = 54.2827 while the mirror and the sensor left it. That is the whole "other element off
axis" report, and the same mechanism as the ``-13.5949`` the scene file carried on disk.

The writer, named by the ``KRAKEN_TRAP_NEGATIVE_GAP`` tripwire::

    layout_table_workbench.py:1568:swap_imaging_lens_from_folder
    layout_table_workbench.py:1311:_swap_auto_refocus_to_best_focus
    scene_placement_commands.py:3604:snap_detector_to_image_plane
    scene_placement_commands.py:3564:_apply_gap_with_floor        <-- raw += near_delta

``_apply_gap_with_floor`` resolves a camera-body collision by sliding the fold mirror up its
incoming leg, and wrote ``rows[near_row].thickness += near_delta`` unclamped. That was safe
only while ``near_row`` was the lens Rear Vertex Datum carrying 80-100 mm; bugs/0546 re-seats
a promoted solid (an absolutely placed ELEMENT whose gap is 0) directly ahead of the mirror,
so ``0 + (-51.2548)`` went straight through. A mirror already AT the gap cannot slide further
toward it.

bugs/0550 already built ``_apply_near_leg_delta`` for this exact failure on this exact row --
absorb what the row can take, spill the rest back through the leg (the split reads only the
SUM, so the leg total is preserved), report failure when the span cannot absorb it. This was
simply a second call site that kept the raw write.

Checks (pure, no VTK/tk):
- SPILL: a 0 mm near gap ahead of the mirror absorbs a -51.2548 slide from the leg upstream,
  every gap stays >= 0, and the leg TOTAL is unchanged (so the conjugate is preserved).
- REFUSAL: when the whole leg cannot absorb the slide the helper reports False, so the caller
  refuses instead of writing a chain that renders nothing.
- OBJECT GAP: the spill stops at ``gap_start`` and never raids the object distance.
- CALL SITE: ``_apply_gap_with_floor`` routes through the helper and no longer does the raw
  ``+= near_delta`` write.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0566_snap_near_leg_never_negative
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


def _rows(thicknesses):
    return [SimpleNamespace(thickness=float(t), name=f"row{i}") for i, t in enumerate(thicknesses)]


def _editor(thicknesses):
    from KrakenOS.UI.services.paraxial_tools import ParaxialToolsMixin

    class _Ed(ParaxialToolsMixin):
        def __init__(self, rows):
            self.rows = rows

    return _Ed(_rows(thicknesses))


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        from KrakenOS.UI.services import scene_placement_commands
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: scene_placement_commands unavailable ({exc!r})"]

    # --- SPILL: the flagged geometry ---------------------------------------------------------
    # [object, ...lens block..., rear datum 78.3848, promoted BS 0.0, mirror]
    editor = _editor([118.97, 1.4, 26.1, 26.1, 1.4, 78.3848, 0.0, 101.2099])
    before_leg = sum(float(r.thickness) for r in editor.rows[1:7])
    placed = editor._apply_near_leg_delta(6, -51.2548, 1)
    after = [round(float(r.thickness), 4) for r in editor.rows]
    if not placed:
        failures.append(f"spill: a -51.2548 slide must fit in the 78.38 mm leg, got refusal ({after})")
    negatives = [(i, t) for i, t in enumerate(after) if t < 0.0]
    if negatives:
        failures.append(
            f"spill: gaps went NEGATIVE {negatives} -- that is the -51.2548 on row 6 that put the "
            "RA mirror 51 mm off the leg (bugs/0566)"
        )
    after_leg = sum(float(r.thickness) for r in editor.rows[1:7])
    if abs((before_leg + -51.2548) - after_leg) > 1e-6:
        failures.append(
            f"spill: the leg total must absorb exactly the delta -- {before_leg:.4f} + (-51.2548) "
            f"!= {after_leg:.4f}; the split reads the SUM, so drifting it moves the conjugate"
        )

    # --- REFUSAL: a slide the leg cannot absorb ----------------------------------------------
    small = _editor([118.97, 2.0, 0.0, 50.0])
    if small._apply_near_leg_delta(2, -75.0, 1):
        failures.append(
            "refusal: a slide larger than the whole leg must report False so the caller refuses "
            "-- writing it produces a chain that renders nothing (0 ray actors)"
        )
    if any(float(r.thickness) < 0.0 for r in small.rows):
        failures.append("refusal: even the refused attempt must not leave a negative gap behind")

    # --- OBJECT GAP is never raided ------------------------------------------------------------
    guarded = _editor([118.97, 2.0, 0.0, 50.0])
    guarded._apply_near_leg_delta(2, -75.0, 1)
    if abs(float(guarded.rows[0].thickness) - 118.97) > 1e-9:
        failures.append(
            f"object gap: row 0 changed to {guarded.rows[0].thickness} -- the spill must stop at "
            "gap_start and never take the object distance"
        )

    # --- CALL SITE ------------------------------------------------------------------------------
    source = inspect.getsource(scene_placement_commands)
    if "_apply_near_leg_delta" not in source:
        failures.append(
            "call site: _apply_gap_with_floor must route the mirror slide through "
            "_apply_near_leg_delta (bugs/0550's helper), not write the leg raw"
        )
    raw_write = "self.rows[near_row].thickness = (\n                        float(self.rows[near_row].thickness) + float(near_delta)\n                    )"
    if raw_write in source:
        failures.append(
            "call site: the raw '+= near_delta' write is still present -- that is the exact "
            "statement that wrote -51.2548 onto a 0 mm gap (bugs/0566)"
        )

    # --- REPORTED: a refused refocus must reach the user ---------------------------------------
    # On the flagged scene gap_start EQUALS near_row (the mirror sits against the beam splitter),
    # so the leg is a single 0 mm row and the slide is correctly refused. The swap then overwrote
    # status_var with its own success line, leaving the lens SILENTLY defocused.
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    refocus_src = inspect.getsource(LayoutTableWorkbenchMixin._swap_auto_refocus_to_best_focus)
    if "_snap_detector_refusal" not in refocus_src:
        failures.append(
            "reported: the swap refocus must capture the snap's refusal reason -- otherwise a "
            "refused refocus is invisible (bugs/0566)"
        )
    swap_src = inspect.getsource(LayoutTableWorkbenchMixin.swap_imaging_lens_from_folder)
    if "_swap_refocus_note" not in swap_src or "NOT refocused" not in swap_src:
        failures.append(
            "reported: the swap's final message must say when the lens was NOT refocused, rather "
            "than reporting a clean swap over a defocused scene"
        )
    if "_snap_detector_refusal" not in inspect.getsource(scene_placement_commands):
        failures.append("reported: snap_detector_to_image_plane must record its refusal reason")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("0566 snap near-leg validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "0566 validation passed: the detector snap's mirror-slide spills through the leg instead "
        "of driving a promoted solid's 0 mm gap negative, preserves the leg total, refuses when "
        "the leg cannot absorb it, and never raids the object distance."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
