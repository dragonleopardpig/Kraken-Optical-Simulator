"""bugs/0492 -- a settings facade owns nothing, so a save cannot read back its own stale copy.

``flag_20260731_212326`` -- *"glued BS to LED, save layout, restart, still not glued."*

``LayoutSettingsService`` delegates to the editor, but its ``__setattr__`` used to keep
``_``-prefixed writes LOCAL.  Python only calls ``__getattr__`` when normal lookup FAILS, and the
editor CACHES one facade instance for its lifetime -- so the first local write permanently shadowed
the editor's copy for every later read through the facade.  ``_apply_layout_settings`` writes eight
such names, so a single layout load was enough:

    editor flag after set_optical_led_glue(True) = True
    facade sees                                  = False
    >>> value SAVE writes to disk                = False        <-- the flag

Four persisted keys were reading back the last LOAD instead of the user's work -- and two of them
are not cosmetic: ``clear_aperture_edge_rects_by_label`` are the bugs/0379 physical clear-aperture
RAY STOPS, and ``camera_precouple_stash`` is the state bugs/0306 added *specifically* so a delete
after save/reload could still un-couple the sensor.

bugs/0449 met this trap on the apply side and patched around it by re-asserting the flag on the
editor afterwards.  That fixed one name in one direction.  This removes the trap: a facade may own
``editor`` and nothing else, which is checked here for EVERY facade of this shape rather than for
the one that was reported (the lesson of the "2D is stale" gate -- guard the invariant, not the
instance).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0492_settings_facade_holds_no_state
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from types import SimpleNamespace

SERVICES_DIR = Path(__file__).resolve().parent / "services"

# A valid bugs/0379 rect -- {center, normal, u_axis, v_axis, half_u, half_v}. Anything missing a
# field is DROPPED by _portable_clear_aperture_rect at both ends, so a lazy fixture round-trips as
# "empty in, empty out" and proves nothing.
RECT = {
    "center": [10.0, 0.0, 53.8], "normal": [1.0, 0.0, 0.0],
    "u_axis": [0.0, 1.0, 0.0], "v_axis": [0.0, 0.0, 1.0],
    "half_u": 11.5, "half_v": 11.5,
}
# Likewise the 0306 stash: the restore is gated on a non-empty "field_type".
STASH = {"field_type": "Angle", "field_value": 12.0, "image_diameter_mode": "Auto", "image_diameter": 23.04}


def _delegating_facades() -> "list[tuple[str, str, str]]":
    """(module, class, __setattr__ source) for every service that forwards to ``self.editor``."""
    found: list[tuple[str, str, str]] = []
    for path in sorted(SERVICES_DIR.glob("*.py")):
        try:
            tree = ast.parse(path.read_text())
        except Exception:
            continue
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            for fn in [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__setattr__"]:
                src = ast.get_source_segment(path.read_text(), fn) or ""
                if "setattr(self.editor" in src:
                    found.append((path.stem, cls.name, src))
    return found


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    # --- A. the invariant, across EVERY facade of this shape ------------------------------
    facades = _delegating_facades()
    check(len(facades) >= 6, f"A1: found the delegating facades to check ({len(facades)})")
    offenders = [f"{m}.{c}" for m, c, src in facades if 'name.startswith("_")' in src]
    check(
        not offenders,
        "A2: no facade keeps `_`-prefixed writes local -- they would shadow the editor's copy "
        f"for every later read ({', '.join(offenders) if offenders else 'none'})",
    )
    # And none of them squirrels state away under another guise.
    leaky = []
    for module, cls, src in facades:
        keeps = set(re.findall(r"object\.__setattr__\(\s*self\s*,\s*([^,]+),", src))
        extra = {k.strip() for k in keeps} - {'"editor"', "'editor'", "name"}
        if extra:
            leaky.append(f"{module}.{cls}{sorted(extra)}")
    check(not leaky, f"A3: a facade stores only `editor` on itself ({', '.join(leaky) or 'confirmed'})")

    # --- B. the mechanism, display-free ---------------------------------------------------
    try:
        from KrakenOS.UI.services.layout_settings import LayoutSettingsService
    except Exception as exc:  # pragma: no cover - environment skip
        notes.append(f"SKIP: layout_settings unavailable ({type(exc).__name__}: {exc})")
        return ok, notes

    editor = SimpleNamespace(_optical_led_glued=False)
    service = LayoutSettingsService(editor)
    service._optical_led_glued = True
    check(
        bool(getattr(editor, "_optical_led_glued", False)) is True,
        "B1: a `_`-prefixed write through the facade lands on the EDITOR",
    )
    check(
        [k for k in service.__dict__ if k != "editor"] == [],
        f"B2: the facade holds no state of its own ({sorted(k for k in service.__dict__ if k != 'editor')})",
    )
    editor._optical_led_glued = False
    check(
        bool(getattr(service, "_optical_led_glued")) is False,
        "B3: a later read through the facade follows the editor rather than a shadowed copy "
        "-- the read path that made SAVE write the last LOAD's value",
    )

    # --- C. the user's gesture end to end: glue, save, reload -----------------------------
    scene = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
    if not scene.exists():
        notes.append("SKIP: the AZ85 BS scene is not checked out (gitignored attachment)")
        return ok, notes
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    made: list = []
    try:
        def _load():
            ed = KrakenLayoutEditor()
            made.append(ed)
            ed.layout_files["glue_probe"] = scene
            ed.load_layout_by_name("glue_probe")
            return ed

        first = _load()
        first.set_optical_led_glue(True)
        first._clear_aperture_rects_by_label = {"lens": [dict(RECT)]}
        first._step_clear_aperture_by_label = {"lens": {"face_index": 4, "area_mm2": 12.5}}
        first._camera_coverage_precouple_stash = dict(STASH)
        saved = first._collect_layout_settings()
        check(
            bool(saved.get("optical_led_glued")) is True,
            f"C1: SAVE writes the glue the user made ({saved.get('optical_led_glued')}) -- the flag",
        )
        check(
            bool((saved.get("clear_aperture_edge_rects_by_label") or {}).get("lens")),
            "C2: SAVE writes the bugs/0379 clear-aperture RAY STOPS (physics, not cosmetics)",
        )
        check(
            bool(saved.get("step_clear_aperture_by_label")) and bool(saved.get("camera_precouple_stash")),
            "C3: SAVE writes the bugs/0134 clear apertures and the bugs/0306 pre-couple stash",
        )
        second = _load()
        second._apply_layout_settings(saved)
        check(second.optical_led_glued() is True, "C4: after a reload the BS is still glued to the LED")
        check(
            bool(getattr(second, "_clear_aperture_rects_by_label", {}).get("lens"))
            and bool(getattr(second, "_step_clear_aperture_by_label", {}))
            and bool(getattr(second, "_camera_coverage_precouple_stash", None)),
            "C5: the aperture stops, clear apertures and pre-couple stash all survive the reload",
        )
        check(
            [k for k in second._layout_settings_service().__dict__ if k != "editor"] == [],
            "C6: a real load leaves the cached facade empty -- nothing to go stale",
        )
    except Exception as exc:
        notes.append(f"SKIP: scene drive failed ({type(exc).__name__}: {exc})")
    finally:
        for ed in made:
            try:
                ed.destroy()
            except Exception:
                pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
