"""Display-free guard for bugs/0382 -- a flag bundle records WHICH scene it was on.

The flag payload captured build / cursor / scene_state but not the loaded layout, so a
flagged bug could not say what file was open ("the recording didn't record what file I
loaded"). ``_flag_layout_identity`` now captures the layout file when set AND the STEP
overlay source paths as a fallback -- so even when ``current_layout_file`` is cleared (an
inserted surrogate / unsaved import) the lens STEP still pins the scene (e.g. ELS-85 ->
the AZ85 RA-mirror scene).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_flag_layout_identity
"""

from __future__ import annotations

import types


class _FakeEditor:
    def __init__(self, layout_file, step_paths, unsaved=False):
        self.current_layout_file = layout_file
        self._layout_is_unsaved_import = unsaved
        self._paths = step_paths

    def _step_path_for_label(self, label):
        return self._paths.get(label)


def _identity(editor):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    insp = Kraken3DInspector.__new__(Kraken3DInspector)
    insp.editor = editor
    return Kraken3DInspector._flag_layout_identity(insp)


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    paths = {
        "lens": "attachment/Lens/ELS-85-4.5V16K/ELS-85-4.5V16K.STEP",
        "camera": "attachment/Cameras/hr25MCX/3D_CAD_HR25xCXP.STEP",
        "led": "attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP",
    }

    # 1. layout file set -> file + name captured, plus the step paths.
    ident = _identity(_FakeEditor("attachment/machine_vision_AZ85_RA_Mirror.py", paths))
    if ident.get("name") != "machine_vision_AZ85_RA_Mirror.py":
        failures.append(f"file set: name not captured ({ident.get('name')!r})")
    if "file" not in ident:
        failures.append("file set: the layout file path must be captured")
    if ident.get("step_paths", {}).get("lens") != paths["lens"]:
        failures.append("file set: the lens STEP path must be captured")

    # 2. layout file None (inserted / cleared) -> step paths STILL identify the scene.
    ident = _identity(_FakeEditor(None, paths))
    if "file" in ident:
        failures.append("file None: must not fabricate a file entry")
    if ident.get("step_paths", {}).get("lens") != paths["lens"]:
        failures.append("file None: the lens STEP path must still pin the scene (the AZ85 flag case)")

    # 3. nothing loaded -> empty-ish but no crash.
    ident = _identity(_FakeEditor(None, {}))
    if ident.get("step_paths"):
        failures.append("empty: no step paths should be reported when none exist")

    # 4. a broken editor never takes the flag write down.
    broken = types.SimpleNamespace()  # no attrs / methods at all
    try:
        _identity(broken)
    except Exception as exc:
        failures.append(f"robustness: _flag_layout_identity raised on a bare editor ({exc!r})")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Flag layout-identity validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Flag layout-identity validation passed: a flag records the layout file when set "
        "and the STEP overlay paths as a fallback (so ELS-85 pins the AZ85 scene even with "
        "no layout file), and never crashes the flag write."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
