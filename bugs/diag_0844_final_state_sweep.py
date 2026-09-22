"""Can a solve between two fields accept a FINAL state where the lens barrel sits in the Filter?

For every device size D (field 1.05*D, through the REAL device callback) the scene's own first
order gives, relative to the loaded rows, where the lens (a5) and the stage (seat, c1) end up. The
states are path-independent, so every (start, target) pair can be judged without solving:
  gate   the lens-first room check, judged on the INTERMEDIATE state (lens moved, stage not yet)
  travel the stage seat inside its declared arm travel
  final  lens-to-Filter and lens-to-mirror-1 clearance in the FINAL state
HAZARD = gate passes + travel ok + final collides (the booking would accept it).

Run: devenv shell -- python bugs/diag_0844_final_state_sweep.py attachment/om05a_folded.py
Measured 2026-09-22 (bugs/0844 "open, unmeasured" item): 0 hazards on om05a_folded (225 pairs)
and om05a_folded_80mm (275 pairs). Re-run it after a lens swap on a staged scene -- a longer rear
barrel or a different EFL moves every number here.
"""
import sys
from pathlib import Path
from types import SimpleNamespace


def main(scene: str) -> int:
    import numpy as np
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.inspection_part import normalize_inspection_part_spec
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    app = KrakenLayoutEditor()
    app.layout_files["s"] = Path(scene)
    app.load_layout_by_name("s")
    qe = QuickEstimationService(SimpleNamespace(editor=app))
    front, rear = app._imaging_lens_block_indices()
    a5_row, c1_row = front - 1, rear
    stage = qe._camera_focus_stage()
    arm = stage["arm"]
    seat_row = int(arm["row"])
    sign, leg = qe._camera_arm_seat_axis(stage)
    sensor = app._current_camera_sensor_active_mm()
    a5_0, c1_0 = float(app.rows[a5_row].thickness), float(app.rows[c1_row].thickness)
    seat_0 = float(app.rows[seat_row].desp_x)
    rear_room = app._lens_block_physical_room_mm(front, rear, +1.0)
    front_room = app._lens_block_physical_room_mm(front, rear, -1.0)
    over_rear = c1_0 - float(rear_room["room_phys"])
    over_front = a5_0 - float(front_room["room_phys"])
    print(f"{Path(scene).name}: lens rows {front}..{rear}  a5 {a5_0:.3f}  c1 {c1_0:.3f}  seat {seat_0:.3f} (sign {sign:+.0f}, leg measured {leg is not None})")
    print(f"   sensor {sensor}  arm travel {arm['min_mm']} .. {arm['max_mm']}")
    print(f"   overhang: rear (lens->Filter body) {over_rear:.3f} mm  [{rear_room.get('obstacle', '?')}]   front (lens->mirror 1 body) {over_front:.3f} mm  [{front_room.get('obstacle', '?')}]")

    states = {}
    for device in (3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100, 120):
        spec = dict(normalize_inspection_part_spec(getattr(app, "inspection_part_spec", None)))
        spec.update(width_mm=float(device), depth_mm=float(device), height_mm=1.0, enabled=True)
        app.set_inspection_part_spec(spec)
        field = 1.05 * device
        m = min(float(sensor[0]), float(sensor[1])) / field
        f = app._folded_conjugate_gaps_for_magnification(m)
        if not isinstance(f, dict):
            continue
        od, idl = float(f["object_delta"]), float(f["image_delta"])
        g = od + idl
        # positions relative to the loaded rows (the device edit moved only the object face)
        a5 = float(app.rows[a5_row].thickness) + od
        c1 = float(app.rows[c1_row].thickness) - od + g
        seat = float(app.rows[seat_row].desp_x) + sign * g
        states[device] = dict(field=field, m=m, a5=a5, c1=c1, seat=seat,
                              travel_ok=arm["min_mm"] - 1e-9 <= seat <= arm["max_mm"] + 1e-9,
                              final_rear=c1 - over_rear, final_front=a5 - over_front)
    print("\n   D    field    |m|      a5       c1     seat   travel  rear-clear front-clear")
    for d, s in states.items():
        print(f"   {d:<4} {s['field']:6.2f}  {s['m']:6.3f}  {s['a5']:7.2f}  {s['c1']:7.2f}  {s['seat']:8.2f}  "
              f"{'ok ' if s['travel_ok'] else 'OUT'}  {s['final_rear']:9.2f}  {s['final_front']:9.2f}")

    hazards, order_refusals, total = [], [], 0
    for d1, s1 in states.items():
        if not (s1["travel_ok"] and s1["final_rear"] >= 0 and s1["final_front"] >= 0):
            continue   # the start must be a state the machine can actually be in
        for d2, s2 in states.items():
            if d1 == d2:
                continue
            total += 1
            d = s2["a5"] - s1["a5"]
            gate = (d <= s1["c1"] - over_rear + 1e-9) if d > 0 else (-d <= s1["a5"] - over_front + 1e-9)
            final_ok = s2["final_rear"] >= -1e-9 and s2["final_front"] >= -1e-9
            if gate and s2["travel_ok"] and not final_ok:
                hazards.append((d1, d2, s1["m"] * s2["m"], s2["final_rear"], s2["final_front"]))
            if not gate and s2["travel_ok"] and final_ok:
                order_refusals.append((d1, d2))
    print(f"\n   {total} reachable-start pairs; HAZARDS (gate passes, stage in travel, FINAL collides): {len(hazards)}")
    for h in hazards[:20]:
        print(f"      D {h[0]} -> {h[1]}   m1*m2 {h[2]:.3f}   final rear clearance {h[3]:+.2f}   front {h[4]:+.2f}")
    print(f"   lens-first refusals of a feasible final state (what 0844's stage-first rescues, rear side): {len(order_refusals)}")
    feasible = [d for d, s in states.items() if s["travel_ok"] and s["final_rear"] >= 0 and s["final_front"] >= 0]
    print(f"   feasible devices: {feasible}")
    app.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
