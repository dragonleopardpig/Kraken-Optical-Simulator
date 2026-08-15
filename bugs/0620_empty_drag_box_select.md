# 0620 — Left-drag on empty background box-selects (FEATURE, 0619 follow-up)

User: "proceed with the integration" — the deferred primary-gesture piece of
flag_20260814. The CAD default: a left-drag STARTING on empty background draws the
rubber-band selection box (one-shot; release selects, right-click then offers the
Selection menu). Nothing is lost:

- a drag starting ON scene content (bodies, rays, axes) still orbits;
- Ctrl+drag always orbits, from anywhere;
- gizmo/carry/armed-pick drags keep their priority (the press claims them first);
- armed click-to-target modes (measure, snap-to-axis, axis-to-axis move, orient
  picks, LED edge, CAD-axis picks...) are never hijacked -- the eligibility gate
  enumerates the real mode flags (verified against the source: 
  `_axis_to_axis_move_pick_mode`, `_snap_rows_to_axis_pick_mode`,
  `_measure_entity_mode`, ... -- names checked, wrong names fail OPEN).

Mechanism: at press, if no drag detector claimed the press, no carry-hold armed, no
pick mode active, and a prop-pick at the press point hits NOTHING (`_prop_picker`),
the press marks `_empty_drag_select_pending`; the first over-threshold motion that
would have orbited instead flips on the one-shot `_rubber_band_select_mode` (the
existing bugs/0433 machinery draws the box and completes on release).

Toolbar hint label updated. The 0433 "Select Elements" menu entries remain (they
also work mid-scene, where empty background may not be visible).

Guard: phase 466's F checks — source contract (press arms behind both gates, motion
activates the transient) + mechanism (empty vs prop press; eligibility blocks armed
modes). Not verifiable headless beyond that: eyeball owed in-app.
