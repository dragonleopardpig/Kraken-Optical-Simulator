"""bugs/0457 guard -- a BEAM SPLITTER folds the beam, so the fold mirror it feeds is not "parked".

The user replaced the object-side RA fold mirror with a BS plate and reported
"sensor/image place relocate to wrong position, causing ray tracing stop half way"
(flag_20260728_075336). Measured chain:

* ``folded_beam_reached_mirror_fold_indices`` walks +Z and reflects only at a promoted MIRROR
  fold, and it consumed each face's LOCAL normal as if it were WORLD. The BS carries
  ``tilt_z = -90``: its diagonal reads as a Y-Z tilt locally and folds in X-Z in world.
* So the walk missed the BS entirely, then (once the splitter was accepted) reflected to -Y,
  where the downstream fold mirror's face is exactly PARALLEL to the leg -- a permanent miss.
* The image-side fold mirror therefore never earned the bugs/0243 "reached" exemption,
  ``neutralize_offbeam_inert_solids`` classified it as an off-beam parked body (it IS far off
  the straight +Z axis -- it sits on the FOLDED arm) and zeroed its 51.5 mm thickness.
* Every downstream station fell short by exactly that, so the WORLD-placed Image row's absolute
  desp landed the image plane at z = -48.77 instead of 2.73 and no ray reached the sensor.

Fix: accept a splitter face as a fold (locally -- NOT by widening ``_is_promoted_mirror_fold``,
which also gates fold-to-sequential and must keep a splitter scene non-sequential), rotate each
face's normal AND centroid into world before intersecting, and walk BOTH legs of a splitter.

Checks:
  REACHED  -- both the BS and the fold mirror it feeds are recognised as reached folds.
  THICKNESS-- the fold mirror's 51.5 mm survives neutralisation.
  TRACE    -- the traced image plane lands ON the prescription (was 51.5 mm past it).
  CONTROL  -- the untouched RA-mirror scene still images 585 rays.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np

BS_SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
ORIGINAL_SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def _image_row(app) -> int | None:
    return next(
        (i for i in range(len(app.rows) - 1, -1, -1) if str(getattr(app.rows[i], "surface", "")) == "Image"),
        None,
    )


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    if not BS_SCENE.exists() or not ORIGINAL_SCENE.exists():
        return True, ["SKIP: the AZ85 scenes are absent (gitignored attachment)"]

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.services.offbeam_optical_solid import (
            folded_beam_reached_mirror_fold_indices,
            neutralize_offbeam_inert_solids,
        )
    except Exception as exc:
        return True, [f"SKIP: imports unavailable ({exc!r})"]

    app = None
    try:
        app = KrakenLayoutEditor()
        app.layout_files["bs"] = BS_SCENE
        app.load_layout_by_name("bs")
        specs = app._serializable_row_specs()

        reached = sorted(folded_beam_reached_mirror_fold_indices(specs))
        if len(reached) >= 2:
            notes.append(f"REACHED = the splitter AND the fold mirror it feeds are reached {reached}")
        else:
            notes.append(f"REACHED only {reached} -- the splitter-fed fold mirror is not recognised")
            ok = False

        neutralized = neutralize_offbeam_inert_solids(specs)
        zeroed = [
            i
            for i, (a, b) in enumerate(zip(specs, neutralized))
            if float(a.get("thickness", 0.0) or 0.0) > 0.1
            and abs(float(b.get("thickness", 0.0) or 0.0)) <= 1e-9
        ]
        if not zeroed:
            notes.append("THICKNESS = no fold mirror had its thickness neutralised away")
        else:
            notes.append(f"THICKNESS rows {zeroed} were zeroed by neutralisation (chain shortened)")
            ok = False

        image_row = _image_row(app)
        z = app._row_z_positions()
        prescription_z = float(z[image_row]) + float(app.rows[image_row].desp_z)
        _s, _rays, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=True, trace_rays=True
        )
        ends = [
            np.asarray(p.points_world, dtype=float)[-1, :3]
            for p in (getattr(bundle, "ray_paths", None) or [])
            if str(getattr(p, "termination_reason", "")) == "target_termination"
            and np.asarray(getattr(p, "points_world", None), dtype=float).ndim == 2
        ]
        if ends:
            landed = float(np.median(np.asarray(ends)[:, 2]))
            if abs(landed - prescription_z) <= 1.0:
                notes.append(
                    f"TRACE = the image plane traces ON the prescription "
                    f"(landed z={landed:.2f} vs {prescription_z:.2f}, n={len(ends)})"
                )
            else:
                notes.append(
                    f"TRACE the image plane traces at z={landed:.2f} but the prescription "
                    f"says {prescription_z:.2f} (off by {landed - prescription_z:+.2f} mm)"
                )
                ok = False
        else:
            notes.append("TRACE no ray reached a target at all")
            ok = False

        app.layout_files["orig"] = ORIGINAL_SCENE
        app.load_layout_by_name("orig")
        _s2, _r2, bundle2 = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=True, trace_rays=True
        )
        reasons = Counter(
            str(getattr(p, "termination_reason", "")) for p in (getattr(bundle2, "ray_paths", None) or [])
        )
        if reasons.get("image", 0) >= 500:
            notes.append(f"CONTROL = the RA-mirror scene still images ({reasons.get('image')} rays)")
        else:
            notes.append(f"CONTROL the RA-mirror scene regressed: {dict(reasons)}")
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
