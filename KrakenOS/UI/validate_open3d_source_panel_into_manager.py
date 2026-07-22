"""Guard: the left Source panel folds into the Scene Source Manager (bugs/0402).

The 2D editor's left "Source" panel is retired from the visible layout. Its role moves to the Scene
Source Manager, which now exposes the imaging-only controls the panel uniquely held -- pupil sampling
(pattern / radial / angular) and the full Gaussian-beam inputs (input mode, beam diameter, full
divergence, waist side). The Manager is reachable one right-click away on the Open 3D "Scene Sources"
group (and per-source rows keep "Edit Source..." plus a "Scene Source Manager..." jump).

The two traps this guards:
  1. The panel's Tk vars back the imaging source-0 that the trace + Pupil/field sync read. So the
     panel must still be BUILT (into a hidden frame) -- if the build call is dropped the vars vanish
     and every fallback imaging trace silently reads origin 0 / +Z. WIRING-PANEL asserts main_window
     still builds it, into a hidden (never-gridded) frame, not a visible "Source" LabelFrame.
  2. The Manager's ``form_spec`` rebuilds a spec from scratch, so a folded-in field not written there
     is DROPPED on every save (bugs/0397-class). FORM-PERSIST asserts form_spec writes all seven keys.

Display-free (no renderer / no Tk / no llvmpipe segfault): getsource wiring assertions + pure-logic
checks on the default spec + normalization.

Checks
------
* DEFAULT-SPEC  -- ``_default_scene_source_spec`` carries the 7 folded-in keys with sane values, and
  they survive ``normalize_scene_source_specs`` (so a Manager-saved source persists them).
* MANAGER-VARS  -- the Manager form declares vars + readonly comboboxes/entries for all 7 controls.
* FORM-PERSIST  -- ``form_spec`` writes all 7 keys (no silent drop on save).
* CONSTRUCTOR   -- the Manager ``__init__`` accepts the 6 new config kwargs and the factory passes
  the real PUPIL_/GAUSSIAN_ constants.
* WIRING-PANEL  -- main_window builds the Source controls into a hidden frame (``source_hidden_panel``,
  ``_build_source_panel`` still called) and no longer grids a visible ``text="Source"`` LabelFrame.
* SHORTCUT      -- the Open 3D "Scene Sources" group menu AND per-source rows offer "Scene Source
  Manager...", and per-source rows still offer "Edit Source..." (unchanged requirement).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_source_panel_into_manager

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

from KrakenOS.UI.scene_source_analysis import normalize_scene_source_specs
from KrakenOS.UI.services.source_modeling import SourceModelingMixin

_FOLDED_KEYS = (
    "pupil_pattern",
    "pupil_rad",
    "pupil_theta",
    "gaussian_input_mode",
    "gaussian_beam_diameter",
    "gaussian_full_divergence",
    "gaussian_waist_side",
)


def _check_default_spec(failures, notes):
    spec = SourceModelingMixin._default_scene_source_spec(0)
    missing = [k for k in _FOLDED_KEYS if k not in spec]
    if missing:
        failures.append(f"DEFAULT-SPEC: _default_scene_source_spec missing {missing}")
        return
    # Sane non-empty seeds (comboboxes need a real value; entries a number).
    if not str(spec["pupil_pattern"]).strip():
        failures.append("DEFAULT-SPEC: pupil_pattern default is blank")
    if not str(spec["gaussian_input_mode"]).strip() or not str(spec["gaussian_waist_side"]).strip():
        failures.append("DEFAULT-SPEC: Gaussian mode/waist-side default is blank")
    norm = normalize_scene_source_specs([spec])[0]
    if any(k not in norm for k in _FOLDED_KEYS):
        failures.append("DEFAULT-SPEC: folded-in keys do not survive normalize_scene_source_specs")
    if not [f for f in failures if f.startswith("DEFAULT-SPEC")]:
        notes.append("default-spec = 7 folded-in keys seeded + survive normalize")


def _check_manager(failures, notes):
    from KrakenOS.UI.panels import main_scene_source_manager_dialog as mod

    src = inspect.getsource(mod.MainSceneSourceManagerDialog)
    # vars declared for every folded-in control
    for key in _FOLDED_KEYS:
        if f'"{key}": tk.' not in src:
            failures.append(f"MANAGER-VARS: no form var for {key!r}")
    # visible controls (labels prove the widgets are laid out)
    for label in ("Pupil pattern", "GB input mode", "GB waist side", "Pupil radial samples"):
        if label not in src:
            failures.append(f"MANAGER-VARS: no widget labelled {label!r}")
    # form_spec must persist all keys (else a save drops them)
    for key in _FOLDED_KEYS:
        if f'spec["{key}"]' not in src:
            failures.append(f"FORM-PERSIST: form_spec never writes {key!r}")
    # constructor accepts the new config
    init_src = inspect.getsource(mod.MainSceneSourceManagerDialog.__init__)
    for kw in ("pupil_pattern_values", "gaussian_input_mode_values", "gaussian_waist_side_values"):
        if kw not in init_src:
            failures.append(f"CONSTRUCTOR: __init__ missing kwarg {kw!r}")
    if not [f for f in failures if f.startswith(("MANAGER-VARS", "FORM-PERSIST"))]:
        notes.append("manager = pupil + Gaussian controls declared, laid out, and persisted by form_spec")
    if not [f for f in failures if f.startswith("CONSTRUCTOR")]:
        notes.append("constructor = accepts the 6 folded-in config kwargs")


def _check_factory(failures, notes):
    from KrakenOS.UI.services import layout_shell_controls as mod

    src = inspect.getsource(mod)
    # the Manager factory must pass the real constants (not defaults)
    for pair in (
        "pupil_pattern_values=PUPIL_PATTERN_VALUES",
        "gaussian_input_mode_values=GAUSSIAN_INPUT_MODE_VALUES",
        "gaussian_waist_side_values=GAUSSIAN_WAIST_SIDE_VALUES",
    ):
        if pair not in src:
            failures.append(f"CONSTRUCTOR: factory does not pass {pair!r} to the Manager")
    if not [f for f in failures if f.startswith("CONSTRUCTOR") and "factory" in f]:
        notes.append("factory = passes real PUPIL_/GAUSSIAN_ value tuples to the Manager")


def _check_panel_hidden(failures, notes):
    from KrakenOS.UI.panels import main_window as mod

    src = inspect.getsource(mod)
    # panel must still be BUILT (vars) but into a hidden frame, not a visible "Source" LabelFrame
    if "self._build_source_panel(source_panel)" not in src:
        failures.append("WIRING-PANEL: main_window no longer builds the source panel (vars would vanish)")
    if "source_hidden_panel" not in src:
        failures.append("WIRING-PANEL: no hidden source frame (source_hidden_panel) -- panel not retired via the hidden-frame pattern")
    if 'ttk.LabelFrame(control_stack, text="Source"' in src:
        failures.append('WIRING-PANEL: a visible text="Source" LabelFrame is still gridded')
    if "source_panel.grid(" in src:
        failures.append("WIRING-PANEL: the source frame is still gridded (should be hidden)")
    if not [f for f in failures if f.startswith("WIRING-PANEL")]:
        notes.append("wiring-panel = Source controls built into a hidden frame; no visible Source LabelFrame")


def _check_shortcut(failures, notes):
    from KrakenOS.UI.panels import open3d_step_admin as mod

    src = inspect.getsource(mod.Open3DStepAdminPanel)
    group_menu = inspect.getsource(mod.Open3DStepAdminPanel._show_scene_sources_context_menu)
    if "Scene Source Manager..." not in group_menu:
        failures.append("SHORTCUT: the Scene Sources GROUP menu has no 'Scene Source Manager...' entry")
    if "_open_scene_source_manager" not in src or "open_scene_source_manager" not in src:
        failures.append("SHORTCUT: no _open_scene_source_manager handler wired to the editor")
    # per-source row: keeps Edit Source... AND gains the Manager jump
    if "Edit Source" not in src:
        failures.append("SHORTCUT: per-source rows lost 'Edit Source...' (must stay)")
    if src.count("Scene Source Manager...") < 2:
        failures.append("SHORTCUT: per-source rows have no 'Scene Source Manager...' jump")
    if not [f for f in failures if f.startswith("SHORTCUT")]:
        notes.append("shortcut = group + per-source 'Scene Source Manager...'; per-source keeps 'Edit Source...'")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (
        _check_default_spec,
        _check_manager,
        _check_factory,
        _check_panel_hidden,
        _check_shortcut,
    ):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_source_panel_into_manager (bugs/0402) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll source-panel-into-manager checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
