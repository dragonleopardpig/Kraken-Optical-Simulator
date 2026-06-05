"""Display-free guard for bugs/0016 — a physically-traced ray must stay visible
up to its terminal surface; it can never silently vanish before hitting one.

Regression context
------------------
A promoted beam-splitter cube on the optical path made *every* ray disappear in
the 3D inspector (``ray_actor_count = 0`` with Show Rays on). Two compounding
defects:

1. The promotion auto-classifier hard-assigned ``Absorber/Mechanical`` to every
   face outside the largest anti-parallel pair. A beam-splitter *cube* has six
   equal-area faces, so it picked ±X as the "lens" pair and condemned the real
   ±Z entry/exit faces to a mechanical block — the rays were absorbed on the
   entry face. (Fixed: promoted faces now default to Uncoated/Transmit; the user
   authors only the special faces.)
2. The 3D ray-display filter, with *Show Clipped Rays* off, kept only paths whose
   terminal status was ``hit_detector`` (``ray_path_reaches_image_from_events``).
   Absorbed rays — and, once the cube transmits, rays that fold off the 45° face
   and *miss* the sensor (``missed_detector``) — were silently dropped, so the
   user saw nothing at all. (Fixed: ``ray_path_visible_without_clipping_from_events``
   keeps every traced ray except those that escaped the system without reaching a
   surface — and, per bugs/0018, a deliberately *folded* escaped ray such as a
   beam splitter's reflect branch stays visible too, since it is a real 2nd path
   rather than vignetting clutter.)

Invariants asserted here (all headless / display-free):

1. Predicate semantics: a ray that hit a surface — ``hit_detector``,
   ``absorbed``, ``stopped``, or ``missed_detector`` (traversed the optics but
   missed the sensor) — is visible with clipped rays OFF; only an ``escaped``
   ray (no next intersection) is hidden by default.
2. Missed-sensor rays stay visible: a fold that sends every ray off the sensor
   still draws all of them by default (pre-fix the default view showed zero).
3. A beam splitter's reflect branch is a deliberate fold, not vignetting: even
   though it leaves the system ("escaped"), it stays VISIBLE by default (bugs/0018
   — the user asked "where is the beam splitter 2nd path ray?"). Only an
   *un-folded* escaped ray (pure vignetting, no reflect/mirror/TIR/split step) is
   gated behind *Show Clipped Rays*; that case is the predicate check above.
   Nothing is ever silently dropped (clipped ON == traced paths).
4. Optional real-scene guard: the user's saved machine-vision prescription (a
   promoted beam-splitter cube) shows its rays by default once more. Skipped if
   the prescription / its CAD cache is unavailable on this machine.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
from collections import Counter
from pathlib import Path

# Headless rendering — never touch a live Wayland/X session.
os.environ.pop("WAYLAND_DISPLAY", None)
os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")

from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.scene_geometry import (
    ray_path_has_non_refractive_steering,
    ray_path_terminal_status_from_events,
    ray_path_visible_without_clipping_from_events,
)
from KrakenOS.UI.validate_random_terminal_element_ray_display import (
    BASE_SETTINGS,
    RANDOM_ELEMENT_TYPES,
    _lens_rows,
)

PRESCRIPTION = Path("attachment/machine_vision_150mm_measured_test.py")


class _FakeEvent:
    def __init__(self, reason: str = "", metadata: dict | None = None) -> None:
        self.event_kind = "terminal"
        self.termination_reason = reason
        self.event_type = ""
        self.metadata = metadata or {}


class _FakePath:
    def __init__(self, reason: str = "", metadata: dict | None = None, reaches_image: bool = False) -> None:
        self.events = [_FakeEvent(reason, metadata)]
        self.reaches_image = reaches_image


def _trace(rows, settings=None) -> dict[str, object]:
    editor = _snapshot_editor(rows, dict(settings or BASE_SETTINGS))
    _system, rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
    paths = list(getattr(bundle, "ray_paths", []) or []) if bundle is not None else []
    statuses = Counter(ray_path_terminal_status_from_events(p) or "(empty)" for p in paths)
    escaped_steered = sum(
        1
        for p in paths
        if ray_path_terminal_status_from_events(p) == "escaped"
        and ray_path_has_non_refractive_steering(p)
    )
    editor.show_clipped_rays_var.set(False)
    off = len(editor._iter_3d_scene_ray_records(rays=rays, scene_bundle=bundle))
    editor.show_clipped_rays_var.set(True)
    on = len(editor._iter_3d_scene_ray_records(rays=rays, scene_bundle=bundle))
    return {
        "paths": len(paths),
        "statuses": dict(statuses),
        "off": off,
        "on": on,
        "escaped_steered": escaped_steered,
    }


def _real_prescription_counts() -> dict[str, object] | None:
    """Trace the user's saved beam-splitter-cube scene, or None if unavailable."""
    if not PRESCRIPTION.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location("_mv0016", PRESCRIPTION)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in module.SURFACES]
        editor = _snapshot_editor(rows, dict(module.SETTINGS))
        editor.current_layout_file = PRESCRIPTION.resolve()
        editor._saved_step_native_trace_plan_cache = {}
        try:
            editor._normalize_special_rows()
        except Exception:
            pass
        _system, rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
        paths = list(getattr(bundle, "ray_paths", []) or []) if bundle is not None else []
        if not paths:
            return None
        editor.show_clipped_rays_var.set(False)
        off = len(editor._iter_3d_scene_ray_records(rays=rays, scene_bundle=bundle))
        editor.show_clipped_rays_var.set(True)
        on = len(editor._iter_3d_scene_ray_records(rays=rays, scene_bundle=bundle))
        return {"paths": len(paths), "off": off, "on": on}
    except Exception as exc:  # missing CAD cache / vendor STEP, etc.
        return {"error": repr(exc)}


def run_checks(*, trials: int = 12, seed: int = 20260605) -> tuple[bool, list[str]]:
    notes: list[str] = []
    passed = True

    def _check(ok: bool, message: str) -> None:
        nonlocal passed
        notes.append(("PASS " if ok else "FAIL ") + message)
        if not ok:
            passed = False

    # 1. Predicate semantics — surfaces keep the ray; only escape hides it.
    semantics = {
        "hit_detector": (_FakePath(metadata={"reaches_image": True}), True),
        "absorbed": (_FakePath("absorb"), True),
        "stopped": (_FakePath("stop_clip"), True),
        "missed_detector": (_FakePath("missed_image"), True),
        "escaped": (_FakePath("no_next_intersection"), False),
    }
    for label, (path, expected) in semantics.items():
        status = ray_path_terminal_status_from_events(path)
        visible = ray_path_visible_without_clipping_from_events(path)
        _check(status == label, f"status maps {label!r} (got {status!r})")
        _check(visible is expected, f"{label} visible-by-default == {expected} (got {visible})")

    # Sanity: a clean lens shows its rays by default and drops nothing.
    base = _trace(_lens_rows())
    _check(base["off"] > 0, f"clean lens displays rays by default (off={base['off']})")
    _check(base["on"] == base["paths"] > 0, f"clean lens: no silent drop (on={base['on']} paths={base['paths']})")

    # 2. A fold (mirror mid-path) sends every ray off the sensor -> missed_detector,
    #    yet all of them stay visible by default. Pre-fix the default view showed 0.
    folded = _trace(_lens_rows("Mirror", 2))
    _check(
        "missed_detector" in folded["statuses"] and "hit_detector" not in folded["statuses"],
        f"fold yields missed-sensor rays (statuses={folded['statuses']})",
    )
    _check(
        folded["off"] == folded["paths"] > 0,
        f"missed-sensor rays stay visible by default (off={folded['off']} paths={folded['paths']})",
    )

    # 3. Beam splitter: BOTH branches are real light paths. The transmit branch
    #    reaches the sensor; the reflect branch is a deliberate fold that leaves
    #    the system ("escaped"). A fold is not vignetting clutter, so per bugs/0018
    #    ("where is the beam splitter 2nd path ray?") it stays VISIBLE by default —
    #    only an *un-folded* escaped ray (pure vignetting) is gated behind Show
    #    Clipped Rays, and that case is the predicate check in section 1.
    bs = _trace(_lens_rows("Beam Splitter", 4))
    _check(
        bs["statuses"].get("escaped", 0) > 0 and bs["statuses"].get("hit_detector", 0) > 0,
        f"beam splitter yields transmit + escaped branches (statuses={bs['statuses']})",
    )
    _check(
        bs["escaped_steered"] == bs["statuses"].get("escaped", 0) > 0,
        f"reflect branch is detected as a deliberate fold (escaped_steered={bs['escaped_steered']} "
        f"escaped={bs['statuses'].get('escaped', 0)})",
    )
    _check(
        0 < bs["off"] == bs["on"] == bs["paths"],
        f"folded reflect branch stays visible by default, never dropped "
        f"(off={bs['off']} on={bs['on']} paths={bs['paths']})",
    )

    # 4. No silent drop across a random-element sweep: every traced ray is
    #    displayable (clipped on == traced paths), regardless of element/position.
    import random

    rng = random.Random(seed)
    positions = list(range(1, 5))
    for trial in range(trials):
        element = rng.choice(RANDOM_ELEMENT_TYPES)
        at_index = rng.choice(positions)
        counts = _trace(_lens_rows(element, at_index))
        _check(
            counts["on"] == counts["paths"] > 0,
            f"trial {trial}: {element}@S{at_index} no silent drop (on={counts['on']} paths={counts['paths']})",
        )

    # 5. Optional: the user's real saved beam-splitter-cube scene shows rays again.
    real = _real_prescription_counts()
    if real is None:
        notes.append("SKIP real prescription unavailable (no CAD cache) — synthetic guards cover the fix")
    elif "error" in real:
        notes.append(f"SKIP real prescription failed to load: {real['error']}")
    else:
        _check(
            real["off"] > 0 and real["on"] == real["paths"] > 0,
            f"real machine-vision cube shows rays by default (off={real['off']} on={real['on']} paths={real['paths']})",
        )

    return passed, notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20260605)
    args = parser.parse_args()
    passed, notes = run_checks(trials=args.trials, seed=args.seed)
    for note in notes:
        print(note)
    print("RESULT:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
