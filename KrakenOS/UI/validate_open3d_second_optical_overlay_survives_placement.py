"""bugs/0210 -- a re-imported optical STEP that duplicates an already-promoted
part (e.g. a SECOND RA fold mirror of the same STEP file) must keep drawing
after it is placed, instead of "disappearing".

Root cause: the scene refresh skips any STEP overlay whose source FILE matches a
promoted row (``_step_overlay_matches_promoted_row`` -> ``continue`` at
``open3d_scene_refresh`` line ~988). That gate exists to suppress the persisted
save/reload "ghost" (commit 95615f05). But a LIVE re-import of the same part is a
distinct instance the user is placing -- it shares the promoted row's file yet is
not that row's leftover overlay. The gate false-positived on it, so once the
carry ended (drop) the refresh collapsed it onto the promoted solid and it
vanished (flag flag_20260703_073100_231: "imported RA mirror disappear after
random placed"; the recording shows ``step_actor_counts`` losing ``optical``
between the press and the release while its pose survives).

Fix: a fresh duplicate import flags the overlay as an independent live instance
(``_mark_step_overlay_independent_instance``); ``_step_overlay_matches_promoted_row``
returns False for a flagged label so it keeps drawing. The flag is runtime-only,
so the persisted reload ghost (never freshly imported) still matches by file and
stays suppressed -- the 95615f05 contract is preserved.

Display-free: exercises the exact gate the draw loop consults (the ``continue``
in the refresh), plus the import-time decision and its clear.

Run:  python -m KrakenOS.UI.validate_open3d_second_optical_overlay_survives_placement
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
_REFRESH_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "open3d_scene_refresh.py"


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _import_time_flag_decision(editor, path: Path) -> None:
    """Mirror the two lines added to ``import_optical_step`` (bugs/0210)."""
    editor.imported_optical_step_path = path
    if editor._step_source_key(path) in editor._promoted_step_source_keys_for_rows():
        editor._mark_step_overlay_independent_instance("optical")
    else:
        editor._clear_step_overlay_independent_instance("optical")


def validate_second_optical_overlay_survives_placement() -> list[Check]:
    checks: list[Check] = []
    editor = _build_editor(_AZ85)

    row1 = editor.rows[1]
    advanced = row1.advanced if isinstance(getattr(row1, "advanced", None), dict) else {}
    ra_path_str = str(advanced.get("OpticalSolidSourcePath") or "")
    promoted = editor._promoted_step_source_keys_for_rows(editor.rows)
    ra_path = Path(ra_path_str) if ra_path_str else None

    checks.append(
        Check(
            "AZ85 row 1 is a promoted optical solid with a recorded STEP source path",
            ra_path is not None
            and editor._step_source_key(ra_path) in promoted,
            f"source={ra_path_str!r}, promoted_keys={len(promoted)}",
        )
    )
    if ra_path is None:
        return checks

    # 1) RELOAD GHOST: a promoted-matching overlay path with NO live import flag
    #    must stay SUPPRESSED (the 95615f05 contract, unchanged).
    editor._clear_step_overlay_independent_instance("optical")
    editor.imported_optical_step_path = ra_path
    ghost_suppressed = editor._step_overlay_matches_promoted_row("optical")
    checks.append(
        Check(
            "persisted reload ghost (same file, not freshly imported) stays suppressed",
            ghost_suppressed is True,
            f"matches_promoted_row={ghost_suppressed} (expect True)",
        )
    )

    # 2) LIVE 2nd IMPORT of the same part: the import-time decision flags it, so
    #    the gate no longer suppresses it -> it keeps drawing. THE FIX.
    _import_time_flag_decision(editor, ra_path)
    flagged = editor._step_overlay_is_independent_instance("optical")
    drawn = editor._step_overlay_matches_promoted_row("optical") is False
    checks.append(
        Check(
            "live re-import of an already-promoted part is flagged independent and keeps drawing",
            flagged is True and drawn,
            f"independent={flagged}, matches_promoted_row={not drawn} (expect independent=True, matches=False)",
        )
    )

    # 3) NON-VACUOUS / causal: the flag is exactly what flips the gate. Clearing
    #    it (what promote / clear_imported_step_overlay_state does) restores the
    #    suppression, proving the pre-fix code path drops the overlay.
    editor._clear_step_overlay_independent_instance("optical")
    reverts = editor._step_overlay_matches_promoted_row("optical") is True
    checks.append(
        Check(
            "clearing the independent flag reverts to suppression (proves pre-fix drop is real)",
            reverts,
            f"matches_promoted_row_after_clear={reverts} (expect True)",
        )
    )

    # 4) A DIFFERENT part (not a promoted duplicate) is never flagged and draws
    #    on its own merits -- the fix is inert outside the duplicate case.
    other = PROJECT_ROOT / "attachment" / "Lens" / "15056" / "15056.STEP"
    _import_time_flag_decision(editor, other)
    other_flagged = editor._step_overlay_is_independent_instance("optical")
    other_drawn = editor._step_overlay_matches_promoted_row("optical") is False
    checks.append(
        Check(
            "a non-duplicate optical import is not flagged and still draws",
            other_flagged is False and other_drawn,
            f"independent={other_flagged}, draws={other_drawn} (expect independent=False, draws=True)",
        )
    )

    # 5) LABEL SCOPING: only "optical" ever carries the flag; the decoration
    #    labels (lens/led/camera) keep their exact reload-ghost behaviour, so
    #    validate_open3d_saved_step_native_trace's "lens" contract is untouched.
    lens_flagged = editor._step_overlay_is_independent_instance("lens")
    checks.append(
        Check(
            "decoration labels are never flagged independent (reload-ghost contract intact)",
            lens_flagged is False,
            f"lens_independent={lens_flagged} (expect False)",
        )
    )

    # 6) The draw loop actually consults this gate (the gate is not vestigial):
    #    the refresh skips a promoted-matching overlay with ``continue``.
    try:
        refresh_src = _REFRESH_SRC.read_text(encoding="utf-8")
    except Exception:
        refresh_src = ""
    gate_wired = "_step_overlay_matches_promoted_row(label, promoted_step_source_keys)" in refresh_src
    checks.append(
        Check(
            "scene refresh draw loop gates the overlay body on _step_overlay_matches_promoted_row",
            gate_wired,
            f"gate present in open3d_scene_refresh.py={gate_wired}",
        )
    )

    return checks


def run_checks() -> tuple[bool, list[str]]:
    """Penta-phase entry point: ``(passed, notes)`` where notes are the failures."""
    checks = validate_second_optical_overlay_survives_placement()
    failures = [f"{check.check} | {check.detail}" for check in checks if not check.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_second_optical_overlay_survives_placement()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{status}: {check.check} | {check.detail}")
    if failed:
        raise SystemExit(1)
    print("Second optical overlay survives placement validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
