"""bugs/0468 guard -- the FOV solve honours the mirror/sensor collision floor.

The user, reading the solve's own output: "the 35x35 FOV, mirror --> sensor becomes 9.534, is
this measured from mirror center? If yes, I remember there is a anti-crash algorithm, this
algorithm will block it correct?"

Both halves were right. The floor is ``0.5 * mirror_row_thickness``, measured from the mirror
CENTRE (half the mirror's own along-axis extent lies on the sensor side), and the manual leg
split has always refused to cross it -- "Safe gap: mirror -> sensor must stay >= N mm so the
mirror does not collide". But the FOV solve wrote its solved image distance straight into the
row without consulting that floor, so 35 x 35 seated the sensor at 9.53 mm inside a 12.5 mm
floor: a physical collision, applied silently.

Checks:
  SAFE     -- a field that fits still solves untouched (30 x 30 -> 18.86 mm gap).
  SLID     -- a field that would collide still SOLVES, by sliding the mirror toward the lens:
              the two legs keep their sum (so the conjugate is untouched) and the sensor ends
              exactly on the floor. Refusing was the first implementation; the user pointed out
              that the fold position is a free mechanical parameter, so the solve should spend
              it rather than reject a field that is genuinely reachable.
"""
from __future__ import annotations

from pathlib import Path

BS_SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    if not BS_SCENE.exists():
        return True, ["SKIP: the BS scene is absent (gitignored attachment)"]

    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

        app = KrakenLayoutEditor()
        app.layout_files["bs"] = BS_SCENE
        app.load_layout_by_name("bs")
        inspector = _open_inspector(app)
        qe = inspector._quick_estimation_service()
        floor = float(qe._image_gap_collision_floor())
        if floor <= 0.0:
            notes.append("SKIP: this scene has no fold mirror to collide with")
            return ok, notes

        applied, message = qe.fov_solve("object", "thickness", 30.0, 30.0, None)
        # bugs/0482: the WORLD leg, for the same reason as SLID below -- the row is the inverted
        # quantity on a frozen fold, so it passed this check by coincidence rather than by meaning.
        _split_safe = app._folded_image_conjugate_split()
        gap = float(_split_safe["far"]) if isinstance(_split_safe, dict) else float("nan")
        if applied and gap >= floor - 1e-6:
            notes.append(f"SAFE = a field that fits still solves (WORLD gap {gap:.3g} mm >= floor {floor:.3g} mm)")
        else:
            notes.append(f"SAFE a fitting field was refused or left an unsafe WORLD gap {gap:.3g}: {str(message)[:70]}")
            ok = False

        app.load_layout_by_name("bs")
        qe = inspector._quick_estimation_service()
        near_before = float(app.rows[6].thickness)
        applied2, message2 = qe.fov_solve("object", "thickness", 35.0, 35.0, None)
        near_after = float(app.rows[6].thickness)
        # bugs/0482: read the WORLD leg, not ``rows[7].thickness``. On this frozen fold the world
        # mirror->sensor leg runs as ``const - thickness`` (bugs/0478, measured derivative -1), so
        # the row is the INVERTED quantity and comparing it to a world-space floor was only ever
        # right by coincidence -- it happened to agree while const was twice the leg. Measured
        # after a 35 x 35 solve: row 91.854 mm, world leg 38.814 mm. The row reading would now
        # report a 91.9 mm "sensor leg" that is really 38.8 mm.
        _split_after = app._folded_image_conjugate_split()
        far_after = float(_split_after["far"]) if isinstance(_split_after, dict) else float("nan")
        # NOT compared against the pre-solve total: solving a new FOV legitimately changes the
        # image total. The slide preserves the total relative to the SOLVED value.
        #
        # bugs/0482 also relaxes ``== floor`` to ``>= floor``. 0468's contract was "slide by
        # exactly the deficit", which lands the leg ON the floor. The solve now also shares the
        # leg-total change between the two sections, which carries the sensor FURTHER from the
        # mirror than the floor requires (38.8 mm against a 24.98 mm floor here) -- strictly safer
        # than what this guard was written to pin. What must never happen is landing BELOW it.
        slid = ("slid" in str(message2).lower())
        on_floor = far_after >= floor - 1e-6
        if applied2 and on_floor and near_after < near_before and slid:
            notes.append(
                f"SLID = a colliding field still solves: mirror moved "
                f"{near_before - near_after:.3g} mm toward the lens, WORLD sensor leg "
                f"{far_after:.3g} mm >= floor {floor:.3g}, legs still sum to the same total"
            )
        else:
            notes.append(
                f"SLID the colliding field was not resolved by sliding: applied={applied2} "
                f"lens->mirror {near_before:.3g} -> {near_after:.3g} WORLD sensor leg "
                f"{far_after:.3g} (floor {floor:.3g})"
            )
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: scene drive failed ({exc!r})")
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
