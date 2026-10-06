"""Guard for bugs/0974: the UN-PROMOTED optical STEP body in the modern look, and its contrast to the
promoted prisms within it.

An "optical" STEP import is the fixture the prisms are promoted out of. In the classic palette its
un-promoted part is a saturated teal; the modern look (bugs/0966) left it so. The user, asked whether
it should take the pale glass colour: "You can make it modern look for the unpromoted STEP, but the
color should be well contrast to all the promoted prism within it."

Measured on om05a_folded, for fourteen candidate colours at the same opacity: how much DRAWING the
promoted prisms changes the pixels where they lie within the body (a CIE76 colour difference; 2 is
the least the eye notices). In the pale glass colour the prisms vanish (2.6); the classic teal 7.1;
warm and mid-dark is what pale blue stands out against -- the smoked bronze chosen scores about 11.

  P1 the look as numbers, no display: the "optical" body asked for in the classic teal is drawn in
     the modern colour with a satin material, its opacity kept inside the look's range and a hidden
     body (opacity 0) left hidden; lens, camera and LED hardware, and an "optical" body in any other
     colour, are left exactly as asked
  P2 the colour is FAR from what the promoted prisms are drawn in: from the modern glass and from
     the modern mirror by more than the classic teal is from the glass, by a clear margin; and it is
     not the hardware's slate
  Q  the Qt shell on om05a_folded, modern look on by default: the body has that colour, opacity and
     material; the real Overlays entry switches to the classic look -- the teal body -- and back; the
     lens / camera / LED bodies are the same in both
  B  the two refreshes agree: the single-body refresh draws the body exactly as the full one did
  E  display only: the import draws the same number of actors with the same points in both looks
  S  selected, the body is the selection pink; deselected, it has its own three colours back
  R  the same for a promoted prism: deselected it is the modern glass again WITH its white highlight
     (measured before this bug: (0.66, 0.83, 0.98) came back as (0.84, 0.92, 0.99), the highlight
     gone, until the next redraw -- the selection saved VTK's blended `GetColor`)
  I  by the picture, in the user's view of the fixture: drawing the promoted prisms changes the
     pixels where they lie within the body clearly; clearly more than with the body painted the
     classic teal, and several times more than with it painted the pale glass colour
  T  the Tk app: modern look off by default and the body is the classic teal; switched on, it takes
     the modern colour there too; off again, teal

om05a_folded needs the vendor STEP files, which are not in git: without them Q..T skip.
Each claim fails on its own: one that raises is reported as that claim's failure.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "UNPROMOTEDSTEP_RESULT "
SKIP_MARK = "UNPROMOTEDSTEP_SKIP "
SCENE = Path("attachment/om05a_folded.py")
QT_ENTRY = "Overlays/Modern look"
LABEL = "optical"
HARDWARE = ("lens", "camera", "led")
#: the user's view of the fixture on 2026-10-06 (flag_20261006_083955_746): from the camera to the
#: focal point, and the view's up direction
VIEW_DIRECTION = (0.7137, 0.4288, -0.5532)
VIEW_UP = (0.3345, -0.9033, -0.2686)
SELECTION_PINK = (1.0, 0.45, 0.65)


def _close(a, b, tolerance: float = 3e-3) -> bool:
    return len(a) == len(b) and all(abs(float(x) - float(y)) <= tolerance for x, y in zip(a, b))


def _r(values, digits: int = 3) -> list:
    return [round(float(value), digits) for value in values]


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def pure_checks() -> list:
    from KrakenOS.UI.services import open3d_scene_look as look

    def p1():
        teal, modern = look.CLASSIC_STEP_BODY_COLOR, look.MODERN_UNPROMOTED_STEP_COLOR
        low, high = look.MODERN_UNPROMOTED_STEP_OPACITY
        drawn = {asked: look.step_body_look(LABEL, teal, asked) for asked in (0.34, 0.46, 0.10, 0.90, 0.0)}
        opacities = {asked: (round(result.opacity, 3) if result is not None else None) for asked, result in drawn.items()}
        first = drawn[0.34]
        left_alone = {label: look.step_body_look(label, (0.30, 0.36, 0.46), 0.3) for label in HARDWARE}
        hardware_in_teal = {label: look.step_body_look(label, teal, 0.3) for label in HARDWARE}
        other_colour = look.step_body_look(LABEL, (0.9, 0.1, 0.1), 0.4)
        spelled = look.step_body_look("  Optical ", teal, 0.34)
        return (first is not None and _close(first.color, modern) and first.material == look.UNPROMOTED_STEP_MATERIAL
                and opacities == {0.34: 0.34, 0.46: 0.46, 0.10: round(low, 3), 0.90: round(high, 3), 0.0: 0.0}
                and 0.2 <= low < high <= 0.6 and all(value is None for value in left_alone.values())
                and all(value is None for value in hardware_in_teal.values()) and other_colour is None
                and spelled is not None and _close(spelled.color, modern) and not _close(modern, teal, 0.05),
                f"the {LABEL!r} body asked in the classic teal is drawn {tuple(modern)} with material "
                f"{first.material if first is not None else None}; opacity asked -> drawn {opacities} (range {low}..{high}); "
                f"hardware left alone: {sorted(k for k, v in left_alone.items() if v is None)}, also when asked in teal: "
                f"{all(value is None for value in hardware_in_teal.values())}; another colour left alone: {other_colour is None}")

    def p2():
        modern = look.MODERN_UNPROMOTED_STEP_COLOR
        to_glass = look.color_difference(modern, look.MODERN_GLASS_COLOR)
        to_mirror = look.color_difference(modern, look.MODERN_MIRROR_COLOR)
        to_slate = look.color_difference(modern, (0.30, 0.36, 0.46))
        teal_to_glass = look.color_difference(look.CLASSIC_STEP_BODY_COLOR, look.MODERN_GLASS_COLOR)
        ruler = (look.color_difference((0, 0, 0), (1, 1, 1)), look.color_difference(modern, modern),
                 abs(look.color_difference(modern, look.MODERN_GLASS_COLOR) - look.color_difference(look.MODERN_GLASS_COLOR, modern)))
        return (abs(ruler[0] - 100.0) < 0.01 and ruler[1] == 0.0 and ruler[2] < 1e-9
                and to_glass >= teal_to_glass + 15.0 and to_mirror >= teal_to_glass + 15.0 and to_slate >= 20.0,
                f"colour difference (black to white = {ruler[0]:.1f}): the body to the modern glass {to_glass:.1f}, to the "
                f"modern mirror {to_mirror:.1f} -- the classic teal is {teal_to_glass:.1f} from the glass; to the hardware's "
                f"slate {to_slate:.1f}")

    return _claims((("P1", p1), ("P2", p2)))


def _bodies(inspector, label: str) -> list:
    """The un-promoted BODY actors of an import (a promoted row's actors carry a row index)."""
    return [inspector._actor_by_key[key] for key in inspector._step_actor_map.get(label, [])
            if key not in inspector._actor_row_map and key in inspector._actor_by_key]


def _import_actors(inspector, label: str) -> list:
    """Every actor the un-promoted import draws: its body and its edges."""
    row_keys = {key for keys in (inspector.__dict__.get("_row_actor_map") or {}).values() for key in keys}
    return [inspector._actor_by_key[key] for key in inspector._step_follow_actor_map.get(label, [])
            if key not in row_keys and key not in inspector._actor_row_map and key in inspector._actor_by_key]


def _wait_for_scene(inspector, pump, seconds: float = 90.0) -> bool:
    """Pump events until the scene's elements are drawn (a load draws them a few seconds later, in
    the Tk app above all); False if they never are."""
    import time

    deadline = time.time() + seconds
    while time.time() < deadline:
        pump()
        if inspector.__dict__.get("_row_actor_map"):
            pump()
            return True
        time.sleep(0.2)
    return False


def _state(actor) -> dict:
    prop = actor.GetProperty()
    return {"diffuse": _r(prop.GetDiffuseColor()), "ambient_color": _r(prop.GetAmbientColor()),
            "specular_color": _r(prop.GetSpecularColor()), "opacity": round(float(prop.GetOpacity()), 3),
            "material": [round(float(prop.GetAmbient()), 2), round(float(prop.GetDiffuse()), 2),
                         round(float(prop.GetSpecular()), 2), round(float(prop.GetSpecularPower()), 1)],
            "phong": prop.GetInterpolationAsString() == "Phong"}


def _is_modern_body(state: dict, look) -> bool:
    low, high = look.MODERN_UNPROMOTED_STEP_OPACITY
    return (_close(state["diffuse"], look.MODERN_UNPROMOTED_STEP_COLOR) and low - 1e-6 <= state["opacity"] <= high + 1e-6
            and _close(state["material"], look.UNPROMOTED_STEP_MATERIAL, 0.02) and state["phong"]
            and _close(state["specular_color"], (1.0, 1.0, 1.0)))


def qt_runtime_checks() -> dict:
    import time

    import numpy as np
    from vtkmodules.util.numpy_support import vtk_to_numpy
    from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.services import open3d_scene_look as look

    if not SCENE.is_file():
        return {"rows": [["X", True, f"SKIP: {SCENE} is absent"]]}
    app, window = build(["guard"])
    window.resize(1500, 950)
    window.show()
    app.processEvents()
    view = window.build_scene()
    window.load_layout_path(SCENE)

    def settle(seconds: float = 0.5) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    inspector = view.inspector
    if not _wait_for_scene(inspector, lambda: settle(0.5)):
        return {"rows": [["Q", False, f"{SCENE.name}: the scene drew no element within 90 s"]]}
    settle(1.0)
    if not _bodies(inspector, LABEL):
        return {"rows": [["X", True, f"SKIP: {SCENE.name} drew no {LABEL!r} STEP body (the vendor STEP files are not in git)"]]}
    render_window, renderer = view.widget.GetRenderWindow(), inspector._renderer
    action = view.toolbar.controls.get(QT_ENTRY)

    def hardware() -> dict:
        return {label: [(_state(actor)["diffuse"], _state(actor)["opacity"]) for actor in _bodies(inspector, label)]
                for label in HARDWARE if _bodies(inspector, label)}

    def points() -> list:
        return sorted(int(actor.GetMapper().GetInput().GetNumberOfPoints()) for actor in _import_actors(inspector, LABEL))

    def claim_q():
        if action is None:
            return False, f"the 3D toolbar offers no {QT_ENTRY!r} entry"
        default = (bool(inspector.modern_look_var.get()), bool(action.isChecked()))
        modern, modern_hardware = _state(_bodies(inspector, LABEL)[0]), hardware()
        action.trigger()                                     # the real Overlays menu entry
        settle()
        classic, classic_hardware = _state(_bodies(inspector, LABEL)[0]), hardware()
        off = (bool(inspector.modern_look_var.get()), bool(action.isChecked()))
        action.trigger()
        settle()
        again = _state(_bodies(inspector, LABEL)[0])
        return (default == (True, True) and _is_modern_body(modern, look) and off == (False, False)
                and _close(classic["diffuse"], look.CLASSIC_STEP_BODY_COLOR) and not _is_modern_body(classic, look)
                and _is_modern_body(again, look) and len(modern_hardware) >= 1 and modern_hardware == classic_hardware
                and all(not _close(colour, look.MODERN_UNPROMOTED_STEP_COLOR, 0.02)
                        for bodies in modern_hardware.values() for colour, _opacity in bodies),
                f"default (switch, entry checked) {default}: the body is {modern['diffuse']} at {modern['opacity']}, material "
                f"{modern['material']}; after the real entry {off}: {classic['diffuse']} at {classic['opacity']}; switched "
                f"back, modern again: {_is_modern_body(again, look)}; the hardware bodies {sorted(modern_hardware)} are the "
                f"same in both looks: {modern_hardware == classic_hardware} ({modern_hardware})")

    def claim_b():
        full = _state(_bodies(inspector, LABEL)[0])
        before = _bodies(inspector, LABEL)[0]
        redrawn = inspector.refresh_imported_step_overlay(LABEL)
        settle()
        bodies = _bodies(inspector, LABEL)
        single = _state(bodies[0]) if bodies else {}
        return (bool(redrawn) and len(bodies) == 1 and bodies[0] is not before and single == full
                and _is_modern_body(single, look),
                f"the single-body refresh ran ({bool(redrawn)}) and made a new body actor ({bool(bodies) and bodies[0] is not before}); "
                f"it is drawn as the full refresh drew it: {single == full} ({single.get('diffuse')} at {single.get('opacity')})")

    def claim_e():
        if action is None:
            return False, f"the 3D toolbar offers no {QT_ENTRY!r} entry"
        modern_points = points()
        action.trigger()
        settle()
        classic_points = points()
        action.trigger()
        settle()
        return (modern_points == classic_points == points() and len(modern_points) >= 2 and min(modern_points) > 100,
                f"the import draws {len(modern_points)} actors with points {modern_points} in the modern look and "
                f"{classic_points} in the classic one")

    def claim_s():
        body = _bodies(inspector, LABEL)[0]
        own = _state(body)
        inspector._set_step_highlight(LABEL)
        settle(0.3)
        selected = _state(body)
        inspector._set_step_highlight(None)
        settle(0.3)
        back = _state(body)
        return (_is_modern_body(own, look) and _close(selected["diffuse"], SELECTION_PINK) and back == own,
                f"the body {own['diffuse']} selected is {selected['diffuse']} at {selected['opacity']}; deselected it has "
                f"its own colours back: {back == own} (diffuse {back['diffuse']}, highlight {back['specular_color']})")

    def claim_r():
        prism = next(actor for actor in inspector._actor_by_key.values()
                     if getattr(actor, "_kraken_file_backed_row_body", False) and actor.GetProperty().GetOpacity() > 0.05)
        row = int(inspector._actor_row_map[inspector._actor_key(prism)])
        own = _state(prism)
        inspector._set_row_highlight(row)
        settle(0.3)
        selected = _state(prism)
        inspector._set_row_highlight(None)
        settle(0.3)
        back = _state(prism)
        return (_close(own["diffuse"], look.MODERN_GLASS_COLOR) and _close(own["specular_color"], (1.0, 1.0, 1.0))
                and _close(selected["diffuse"], SELECTION_PINK) and back == own,
                f"the promoted prism of row {row}, {own['diffuse']} with highlight {own['specular_color']}, selected is "
                f"{selected['diffuse']}; deselected it is {back['diffuse']} with highlight {back['specular_color']}: its own "
                f"again {back == own}")

    def grab():
        render_window.Render()
        shot = vtkWindowToImageFilter()
        shot.SetInput(render_window)
        shot.SetInputBufferTypeToRGB()
        shot.ReadFrontBufferOff()
        shot.Update()
        image = shot.GetOutput()
        width, height, _depth = image.GetDimensions()
        return vtk_to_numpy(image.GetPointData().GetScalars()).reshape(height, width, 3).astype(float) / 255.0

    def covered(actors):
        """The pixels the actors cover: the picture with them drawn in one flat solid colour less the picture without."""
        saved = [(actor, _own(actor), actor.GetProperty().GetOpacity(), actor.GetProperty().GetLighting(), actor.GetVisibility())
                 for actor in actors]
        for actor in actors:
            actor.GetProperty().SetColor(1.0, 0.0, 1.0)
            actor.GetProperty().SetOpacity(1.0)
            actor.GetProperty().SetLighting(False)
        with_them = grab()
        for actor in actors:
            actor.SetVisibility(False)
        without = grab()
        for actor, own, opacity, lighting, visible in saved:
            _put(actor, own)
            actor.GetProperty().SetOpacity(opacity)
            actor.GetProperty().SetLighting(bool(lighting))
            actor.SetVisibility(visible)
        return np.abs(with_them - without).sum(axis=2) > 0.25

    def _own(actor):
        prop = actor.GetProperty()
        return tuple(prop.GetAmbientColor()), tuple(prop.GetDiffuseColor()), tuple(prop.GetSpecularColor())

    def _put(actor, own) -> None:
        prop = actor.GetProperty()
        prop.SetAmbientColor(*own[0])
        prop.SetDiffuseColor(*own[1])
        prop.SetSpecularColor(*own[2])

    def claim_i():
        body = _bodies(inspector, LABEL)[0]
        prisms = [actor for actor in inspector._actor_by_key.values() if getattr(actor, "_kraken_file_backed_row_body", False)]
        prism_rows = sorted({int(inspector._actor_row_map[inspector._actor_key(actor)]) for actor in prisms})
        prism_actors = [inspector._actor_by_key[key] for row in prism_rows for key in (inspector._row_actor_map.get(row) or [])
                        if key in inspector._actor_by_key]
        bounds = np.array(body.GetBounds()).reshape(3, 2)
        centre = bounds.mean(axis=1)
        reach = float(np.linalg.norm(bounds[:, 1] - bounds[:, 0]))
        camera = renderer.GetActiveCamera()
        camera.SetFocalPoint(*centre)
        camera.SetPosition(*(centre - np.array(VIEW_DIRECTION) * reach * 4.0))
        camera.SetViewUp(*VIEW_UP)
        renderer.ResetCamera(*body.GetBounds())
        renderer.ResetCameraClippingRange()
        within = covered([body]) & covered(prisms)

        def prisms_show() -> float:
            """How much DRAWING the promoted prisms changes the pixels where they lie within the body."""
            with_prisms = grab()
            for actor in prism_actors:
                actor.SetVisibility(False)
            without = grab()
            for actor in prism_actors:
                actor.SetVisibility(True)
            return look.color_difference(with_prisms[within].mean(axis=0), without[within].mean(axis=0))

        own = _own(body)
        modern = prisms_show()
        painted = {}
        for name, colour in (("the classic teal", look.CLASSIC_STEP_BODY_COLOR), ("the pale glass colour", look.MODERN_GLASS_COLOR)):
            body.GetProperty().SetAmbientColor(*colour)
            body.GetProperty().SetDiffuseColor(*colour)
            painted[name] = prisms_show()
        _put(body, own)
        teal, glass = painted["the classic teal"], painted["the pale glass colour"]
        return (len(prism_rows) >= 3 and int(within.sum()) >= 3000 and modern >= 8.0 and modern >= teal + 2.0
                and modern >= 3.0 * glass and _state(body)["diffuse"] == _r(own[1]),
                f"{len(prism_rows)} promoted prisms; {int(within.sum())} pixels where they lie within the body. Drawing "
                f"them changes those pixels by a colour difference of {modern:.1f} with the body as the modern look draws "
                f"it, {teal:.1f} with it painted the classic teal, {glass:.1f} with it painted the pale glass colour")

    rows = _claims((("Q", claim_q), ("B", claim_b), ("E", claim_e), ("S", claim_s), ("R", claim_r), ("I", claim_i)))
    return {"rows": rows}


def tk_runtime_checks() -> dict:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import open3d_scene_look as look

    if not SCENE.is_file():
        return {"rows": [["X", True, f"SKIP: {SCENE} is absent"]]}
    editor = KrakenLayoutEditor()
    editor.layout_files[SCENE.stem] = SCENE
    editor.load_layout_by_name(SCENE.stem)
    editor.open_3d_view()
    for _ in range(6):
        editor.update()
    inspector = getattr(editor, "_three_d_inspector", None)
    if inspector is None or not getattr(inspector, "available", False):
        return {"rows": [["T", True, "SKIP: the embedded 3D inspector is unavailable"]]}
    def pump() -> None:
        for _ in range(8):
            inspector.update()
            editor.update()

    if not _wait_for_scene(inspector, pump):
        return {"rows": [["T", False, f"{SCENE.name}: the Tk 3D view drew no element within 90 s"]]}
    if not _bodies(inspector, LABEL):
        return {"rows": [["X", True, f"SKIP: {SCENE.name} drew no {LABEL!r} STEP body in the Tk app (the vendor STEP files are not in git)"]]}

    def claim_t():
        def switch(on: bool) -> dict:
            inspector.modern_look_var.set(on)
            inspector._on_scene_look_changed()               # what the Overlays entry runs
            pump()
            return _state(_bodies(inspector, LABEL)[0])

        default = bool(inspector.modern_look_var.get())
        classic = _state(_bodies(inspector, LABEL)[0])
        modern, again = switch(True), switch(False)
        # (the opacity is the scene refresh's own business: 0.46 while rays are asked for, 0.34 without)
        return (default is False and _close(classic["diffuse"], look.CLASSIC_STEP_BODY_COLOR)
                and not _is_modern_body(classic, look) and _is_modern_body(modern, look)
                and _close(again["diffuse"], look.CLASSIC_STEP_BODY_COLOR) and not _is_modern_body(again, look)
                and again["material"] == classic["material"],
                f"Tk default {default}: the body is {classic['diffuse']} at {classic['opacity']}, material "
                f"{classic['material']}; with the modern look on, {modern['diffuse']} at {modern['opacity']} with material "
                f"{modern['material']}; off again, {again['diffuse']} at {again['opacity']}, material {again['material']}")

    return {"rows": _claims((("T", claim_t),))}


def _run(call: str, claim: str) -> list:
    driver = (
        "import json, os\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_unpromoted_step_look import qt_runtime_checks, tk_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a VTK/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [[claim, False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])["rows"]
        if line.startswith(SKIP_MARK):
            return [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
    return [[claim, False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    try:
        rows = pure_checks()
    except Exception as exc:
        rows = [["P", False, f"raised {type(exc).__name__}: {exc}"]]
    rows += _run("qt_runtime_checks()", "Q") + _run("tk_runtime_checks()", "T")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
