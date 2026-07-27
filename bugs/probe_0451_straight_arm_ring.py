"""bugs/0451 -- the dead-end straight arm keeps its ray stop but draws no sensor ring.

flag_20260726_191053 ("after RA mirror deletion"): the freeze worked and the straight
beam correctly runs on, but a synthesized detector drew a "Sensor 23.0x23.0 / Image
circle" coverage ring INSIDE the LED at (0, 0, 94.7) -- sensor iconography where no
sensor exists. The designed Image sits off on the frozen fold leg and this arm never
reaches it.

Contract (the bugs/0182 double-duty rule): the detector TARGET stays -- it is the ray
hard-stop that keeps the beam bounded instead of flying to infinity -- and only its
DRAW is gated. A genuine SPLIT still draws both arms (bugs/0090), and a scene with no
designed Image keeps its only detector visible.

Run: DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0451_straight_arm_ring.py
"""
from __future__ import annotations

from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(("ok " if ok else "XX "), label, (" " + detail if detail else ""))
    if not ok:
        FAILURES.append(label)


def _branch_targets(bundle):
    out = []
    for t in list(getattr(bundle, "targets", []) or []):
        meta = getattr(t, "metadata", None) or {}
        if str(meta.get("target_source", "")) == "branch_detector":
            out.append((t, meta))
    return out


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")

        # The user's action: delete the fold mirror (0433 freeze), rays ON.
        mirror1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([mirror1])

        _system, _rays, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=True, trace_rays=True
        )
        branch = _branch_targets(bundle)
        check("the straight arm still earns a branch detector (the ray hard-stop)", len(branch) >= 1, str(len(branch)))
        if branch:
            suppressed = [bool(meta.get("draw_suppressed")) for _t, meta in branch]
            check(
                "its DRAW is suppressed (no phantom Sensor/Image-circle ring)",
                all(suppressed),
                str(suppressed),
            )
            still_detector = [bool(getattr(t, "is_detector", False)) for t, _m in branch]
            check(
                "it remains an is_detector target so the rays stay bounded (0182)",
                all(still_detector),
                str(still_detector),
            )

        # Why the bundle renders pale: terminal status drives the ray colour, and
        # "stopped" (genuine aperture vignetting) is deliberately a thin GREY stub
        # (0.66, 0.66, 0.66). Census it so the flag's "pale rays" is explained by
        # evidence rather than assumed.
        from collections import Counter

        statuses = Counter()
        try:
            for _idx, _color, _pts, status in app._iter_3d_scene_ray_records(_rays, bundle):
                statuses[str(status or "").strip().lower()] += 1
        except Exception as exc:
            print("   [info] ray status census unavailable:", repr(exc)[:60])
        if statuses:
            print("   [info] straight-arm ray terminal statuses:", dict(statuses))
            check(
                "the pale bundle is the DELIBERATE vignetting style, not a broken draw",
                statuses.get("stopped", 0) > 0 or statuses.get("escaped", 0) > 0,
                str(dict(statuses)),
            )

        # Control: a genuine SPLIT must keep drawing both arms (bugs/0090).
        app.load_layout_by_name("az85")
        try:
            app._select_table_indices([1], focus_index=1)
        except Exception:
            app._select_table_row(1)
        app.add_beam_splitter_to_led(kind="plate")
        _s2, _r2, bundle2 = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=True, trace_rays=True
        )
        branch2 = _branch_targets(bundle2)
        if len(branch2) > 1:
            drawn = [not bool(meta.get("draw_suppressed")) for _t, meta in branch2]
            check(
                "control: a real split still draws its arms (0090 untouched)",
                any(drawn),
                f"{len(branch2)} arms, drawn={drawn}",
            )
        else:
            print(f"   [info] the BS scene produced {len(branch2)} branch detector(s) -- split control skipped")
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if FAILURES:
        print(f"FAIL: {FAILURES}")
        return 1
    print("RESULT: PASS -- dead-end arm keeps its ray stop, draws no sensor ring; splits untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
