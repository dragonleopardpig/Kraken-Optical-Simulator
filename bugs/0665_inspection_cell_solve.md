# 0665 — Cell-level solve: part + defect size → camera + lens per face → stations built

**User (2026-08-30):** "proceed" on the phase-3 recommendation — a new cell should
start from numbers, not six hand-built layouts.

## Shipped — `KrakenOS/UI/services/inspection_cell_solve.py`

- `face_requirements(part, defect_mm, px_per_defect, margin, wd_min)`: per face the
  field = face dims + margin, oriented LANDSCAPE (longer side → sensor width);
  resolution = defect / px-per-defect (µm/px); opposite faces share.
- `choose_station(req, cameras, lenses)`: every registered camera × catalog lens via
  the bugs/0634 matcher, with two cell-specific rules: (1) **height-aware m** =
  min(sensor_w/fov_w, sensor_h/fov_h) so both face sides fit, judged at the field the
  camera actually sees; (2) a **fixed-magnification lens is judged at its own m** —
  its field sensor/m must cover the face — the matcher's "required m inside the band"
  test wrongly rejected a 0.75× lens whose 11.3×9.4 field covers a 10.5×8.4 face.
  Ranking: passes → fixed-magnification preferred (a defect-inspection cell wants the
  telecentric's constant scale; `prefer_fixed_magnification=False` to disable) →
  fewest failures → largest WD margin (the matcher's own order).
- `build_station_layout(choice, part, out)`: headless — import the lens folder, the
  camera folder (sensor coupled, body mounted), enable the part on the face; a
  fixed-magnification lens is already at its WD by the 0656 mount law, a variable lens
  solves the FOV to the face +5%; save the layout.
- `solve_and_build_cell(part, defect, out_dir, …)`: one layout per opposite-face
  pair + the `*.cell.json`. Dialog: *Inspection Cell → "Solve stations from the part +
  defect size"* (defect mm, px/defect, min WD, output folder) → slots filled.
- `system_matcher.CameraSpec/LensSpec` gained `folder` so a choice can be BUILT.

## Verified

Real catalog: 10×8×6 part, 20 µm defects @3 px, WD ≥ 40 → Allied Vision hr25MCX +
Edmund 15056 1× on all faces (23×23 field, 4.5 µm/px, 300 mm WD); 60×40×20 part,
0.2 mm defects, WD ≥ 100 → hr25MCX + PYRITE 4.5/90/0.3× (77×77 field, 15 µm/px,
393 mm WD). Guard `validate_open3d_0665_inspection_cell_solve` (penta phase 498):
requirements (orientation, resolution, sharing), selection on a synthetic catalog
(fixed lens covering the face passes and is preferred; a too-small fixed field fails
with the reason; variable lens at the height-aware m; the preference switch;
resolution refusal), a real station BUILD (Basler + 0.75× telecentric: camera
coupled, mount law mismatch ~0), wiring.
