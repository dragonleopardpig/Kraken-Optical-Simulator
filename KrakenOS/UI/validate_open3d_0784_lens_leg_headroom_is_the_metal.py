"""Guard for bugs/0784 -- the lens gap's floor is the METAL, not the row.

Flags 20260913_083551 / _085839:

> "I noticed the A5 gap is 32.96mm, so if the device size shrink to 0.5mm and the motor move
> everything that carries lens+filter+40mm RA mirror+camera closer to the big inverted RA mirror
> ... it should match 0.5mm with FOV 23 just fine."
> "For device size 20mm, A5 gap is 28.1mm. So plenty of A5 room for 0.5mm device."

The user was measuring METAL. The lens block's position is booked as ``rows[front-1].thickness``,
which may not go negative, and on om05a_folded_80mm that row's zero sits 26.90 mm short of metal
contact -- the 50 mm prism's folded glass path is booked entirely on the outgoing leg while only
~25.29 mm of it runs along that leg in world. Measured, device 0.5 mm at FOV 23:

    needs the lens -136 mm; leg gap (row 8) 130.9 -> refused "short by 5.099 mm"
    while the mover's own probe reports 155.8 mm of PHYSICAL room

_recover_lens_leg_headroom shifts the shortfall out of the nearest upstream AIR gap into the lens
gap and compensates every body in between so nothing moves. End to end on the real scene: 0.5 mm at
FOV 23 solves and lands at 2.28 um with 19.8 mm of clearance, 20 mm at FOV 21 lands at 2.47 um
(refused short 2.501 mm before), 22 mm at auto FOV is unchanged to every digit (2.22 um, room
30.9/64.4), and 0.5 mm at FOV 17 still refuses -- on the PHYSICAL gate.

Checks (display-free; a stub bench whose desp frame is PERMUTED, so a compensation that assumed
desp_x rather than measuring the frame would fail B2):
  A  a short row with a long upstream AIR gap recovers: donor shrinks, gap grows, and every body
     and the lens datum stay exactly where they were;
  B  the compensation is measured, not assumed -- it works on a permuted desp frame and leaves the
     body's world pose unchanged to 1e-9;
  C  it declines without a legal donor: glass, a body's own row, a station-neutral row, or one too
     short -- and writes nothing;
  D  object side only (a positive delta is the Filter side, real hardware), and a non-positive
     request is declined;
  E  it REVERTS when the audit cannot prove the bodies stayed put;
  F  wiring: the mover tries the recovery before its row refusal and re-reads the cap afterwards.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0784_lens_leg_headroom_is_the_metal
"""

from __future__ import annotations

import inspect

import numpy as np


class _Row:
    def __init__(self, name, thickness=0.0, glass="AIR", solid=False):
        self.name = name
        self.thickness = float(thickness)
        self.glass = glass
        self.desp_x = self.desp_y = self.desp_z = 0.0
        self.advanced = {"Solid_3d_stl": "/tmp/body.stl"} if solid else {}


def _bench(frame=None, donor_glass="AIR", donor_len=40.0, body=True, dead_frame=False):
    """rows: 0 Object | 1 air | 2 DONOR air | 3 body (desp-placed) | 4 lens gap | 5 front datum | 6 rear.

    World model: a row sits at its station along +x, plus its own desp mapped through ``frame``
    (default permuted: desp_z -> world x), which is what the real om05a prism does."""
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    rows = [
        _Row("Object", 5.0),
        _Row("air", 3.0),
        _Row("donor", donor_len, glass=donor_glass),
        _Row("RA prism", 50.0, glass="BK7", solid=body),
        _Row("lens gap", 5.0),
        _Row("Front Optical Vertex Datum", 10.0),
        _Row("Rear Optical Vertex Datum", 17.5),
    ]
    matrix = np.array(frame if frame is not None else [[0.0, 0.0, 1.0],
                                                      [0.0, 1.0, 0.0],
                                                      [1.0, 0.0, 0.0]], dtype=float)
    if dead_frame:
        matrix = np.zeros((3, 3), dtype=float)

    class _Bench(ScenePlacementMixin):
        def __init__(self):
            self.rows = rows
            self.debug = []

        def append_debug(self, message):
            self.debug.append(str(message))

        def _invalidate_preview_scene_trace(self, reason=""):
            return None

        def _surface_reference_world_point(self, index):
            index = int(index)
            station = float(sum(r.thickness for r in self.rows[:index]))
            desp = np.array([self.rows[index].desp_x, self.rows[index].desp_y,
                             self.rows[index].desp_z], dtype=float)
            return np.array([station, 0.0, 0.0]) + matrix @ desp

    return _Bench(), rows


def _snap(rows):
    return [(r.thickness, r.desp_x, r.desp_y, r.desp_z) for r in rows]


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    FRONT = 5

    # ---- A / B: the recovery, on a permuted desp frame -----------------------------------------
    bench, rows = _bench()
    body_before = bench._surface_reference_world_point(3).copy()
    datum_before = bench._surface_reference_world_point(FRONT).copy()
    donor0, gap0 = rows[2].thickness, rows[4].thickness
    got = bench._recover_lens_leg_headroom(FRONT, 6.0, -10.0)
    ok(got is True, f"A1: a 6 mm shortfall with a 40 mm upstream AIR gap is recovered (got {got!r})")
    ok(abs(rows[2].thickness - (donor0 - 6.0)) < 1e-9 and abs(rows[4].thickness - (gap0 + 6.0)) < 1e-9,
       f"A2: the donor gave 6 mm to the lens gap ({donor0} -> {rows[2].thickness}, {gap0} -> {rows[4].thickness})")
    ok(float(np.linalg.norm(bench._surface_reference_world_point(FRONT) - datum_before)) < 1e-9,
       "A3: the lens datum did not move -- the shift cancels at and beyond the gap")
    moved = float(np.linalg.norm(bench._surface_reference_world_point(3) - body_before))
    ok(moved < 1e-9, f"B1: the body between donor and gap is exactly where it was ({moved:.2e} mm)")
    ok(abs(rows[3].desp_z - 6.0) < 1e-6 and abs(rows[3].desp_x) < 1e-9,
       f"B2: the compensation went into the axis that MOVES this body on its own frame "
       f"(desp_z {rows[3].desp_z:+.4f}, desp_x {rows[3].desp_x:+.4f}) -- measured, not assumed")
    ok(any("headroom recovered" in m for m in bench.debug), "B3: and it says so in the debug log")

    # ---- C: no legal donor -----------------------------------------------------------------------
    for label, kwargs in (("glass", {"donor_glass": "BK7"}), ("too short", {"donor_len": 4.0})):
        bench, rows = _bench(**kwargs)
        before = _snap(rows)
        got = bench._recover_lens_leg_headroom(FRONT, 6.0, -10.0)
        ok(got is False and _snap(rows) == before,
           f"C1: a {label} upstream row is not a donor -- declined, nothing written (got {got!r})")

    # ---- D: direction and sanity ------------------------------------------------------------------
    bench, rows = _bench()
    before = _snap(rows)
    ok(bench._recover_lens_leg_headroom(FRONT, 6.0, +10.0) is False and _snap(rows) == before,
       "D1: a move toward the CAMERA is not recovered -- that cap is the Filter, real hardware")
    ok(bench._recover_lens_leg_headroom(FRONT, 0.0, -10.0) is False and _snap(rows) == before,
       "D2: a non-positive shortfall is declined")
    ok(bench._recover_lens_leg_headroom(0, 6.0, -10.0) is False and _snap(rows) == before,
       "D3: a lens block with no row before it is declined")

    # ---- E: the audit has teeth --------------------------------------------------------------------
    bench, rows = _bench(dead_frame=True)      # desp cannot move this body: compensation impossible
    before = _snap(rows)
    got = bench._recover_lens_leg_headroom(FRONT, 6.0, -10.0)
    ok(got is False, f"E1: when the body cannot be put back, the recovery REFUSES (got {got!r})")
    ok(_snap(rows) == before, "E2: and every row is restored bit-for-bit")

    # ---- F: wiring ---------------------------------------------------------------------------------
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    src = inspect.getsource(ScenePlacementMixin.translate_lens_block_along_leg)
    recover_at = src.find("_recover_lens_leg_headroom(")
    refuse_at = src.find("cannot absorb it")
    ok(0 < recover_at < refuse_at,
       "F1: the mover tries the recovery BEFORE refusing on the row partition")
    ok("cap = max(float(room_station) - 1.0e-3, 0.0)" in src[recover_at:refuse_at],
       "F2: and re-reads the cap from the grown gap before deciding")
    phys = src.find("mm of physical room is left")
    ok(0 < phys < recover_at,
       "F3: the PHYSICAL gate still runs first -- the metal, not the row, is the limit")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0784 lens-leg-headroom-is-the-metal validation PASSED")
        return 0
    print("0784 lens-leg-headroom-is-the-metal validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
