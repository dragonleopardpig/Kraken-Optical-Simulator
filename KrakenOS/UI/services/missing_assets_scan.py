"""Scan a loaded layout for STEP / STL references whose files do not exist.

The renderer's silent fallback for missing files (analytic single-face
mesh instead of the cached body STL, repeated retries for missing source
STEPs, "planar clustering fallback" warnings) is a fertile bug-report
trap: the user sees something visibly wrong but the only signal is in
``~/.cache/krakenos/logs``. This module surfaces the missing references
so the layout-load path can prompt the user to relocate them.

Public API:

* :class:`MissingAsset` -- one record per (row, key) reference that
  failed to resolve, plus the entries for editor-instance import paths
  (``imported_*_step_path``).
* :func:`scan_missing_assets` -- pure function over a row list + editor
  state. Returns the missing list ordered by row index, then key.
* :class:`MissingResourceState` constants -- advanced-attr key that the
  renderer's placeholder path keys on after the user clicks Skip.

The scan is intentionally narrow: it inspects only ``advanced``-dict
fields that are known to point at on-disk files, plus the four
``imported_*_step_path`` editor attributes. It does *not* try to
re-resolve relative paths or guess alternate locations -- that is the
relocate dialog's job.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional


# Advanced-dict keys that, when present, point at a single on-disk path.
# Order matters: the renderer's fallback ladder walks Solid_3d_stl first
# (legacy file-backed), then StepAnalyticBodyStlPath (analytic-promote
# cached body), then the source-STEP fields. We mirror that order so the
# dialog presents the entries in the same priority a renderer would hit.
_ROW_PATH_KEYS: tuple[str, ...] = (
    "Solid_3d_stl",
    "StepAnalyticBodyStlPath",
    "OpticalSolidSourcePath",
    "StepNativeSourcePath",
)


# Keys whose value is itself a dict carrying a ``source_step_path``
# sub-key (the promote-service metadata). We probe the sub-key when the
# outer dict is present.
_ROW_PROMOTION_KEYS: tuple[str, ...] = (
    "StepAnalyticPromotion",
    "StepNativePromotion",
)


# Editor-instance attributes that hold an active import overlay path.
# ``None`` indicates "no STEP loaded for this slot" and is skipped.
_EDITOR_PATH_ATTRS: tuple[str, ...] = (
    "imported_optical_step_path",
    "imported_lens_step_path",
    "imported_camera_step_path",
    "imported_led_step_path",
)


# Advanced-attr key written into a row after the user clicks Skip in the
# dialog. The renderer keys placeholder rendering on this so the row
# draws as a visible "missing asset" marker instead of falling silently
# back to the analytic mesh. The value is a dict of the keys that were
# skipped, so a partial re-locate (e.g. the source STEP shows up but the
# body STL stays missing) still degrades cleanly.
MISSING_RESOURCE_STATE_ATTR = "MissingResourceState"


@dataclass(frozen=True)
class MissingAsset:
    """One missing file reference surfaced by :func:`scan_missing_assets`.

    ``scope`` is either ``"row"`` (a row in the loaded layout) or
    ``"editor"`` (a currently-loaded import overlay). ``row_index`` is
    -1 for editor-scope entries. ``key`` is the advanced-dict attr name
    or editor attribute name. ``expected_path`` is the absolute path
    that was probed and did not exist.
    """

    scope: str
    row_index: int
    key: str
    expected_path: Path
    label: str = ""

    def short_label(self) -> str:
        """Human-readable summary for the dialog row."""
        if self.scope == "row":
            base = f"Row {self.row_index}"
            if self.label:
                base = f"{base}  {self.label}"
            return f"{base}  [{self.key}]"
        return f"Overlay  [{self.key}]"


def _coerce_path(value: Any) -> Optional[Path]:
    if value is None:
        return None
    if isinstance(value, Path):
        return value.expanduser()
    if isinstance(value, str):
        text = value.strip()
        if not text or text.lower() == "none":
            return None
        return Path(text).expanduser()
    return None


def _row_label(row: Any, row_index: int) -> str:
    """Build a short human label for a row (name | element | surface)."""
    parts: list[str] = []
    for attr in ("name", "element"):
        value = getattr(row, attr, "")
        text = str(value or "").strip()
        if text and text not in parts:
            parts.append(text)
        if parts:
            break
    surface = str(getattr(row, "surface", "") or "").strip()
    if surface and surface not in parts:
        parts.append(surface)
    return " | ".join(parts) if parts else ""


def _row_advanced(row: Any) -> dict[str, Any]:
    advanced = getattr(row, "advanced", None)
    return advanced if isinstance(advanced, dict) else {}


def _skipped_keys_for_row(row: Any) -> frozenset[str]:
    """Return the set of keys the user has previously chosen to skip."""
    state = _row_advanced(row).get(MISSING_RESOURCE_STATE_ATTR)
    if not isinstance(state, dict):
        return frozenset()
    keys = state.get("keys")
    if not isinstance(keys, (list, tuple, set, frozenset)):
        return frozenset()
    return frozenset(str(k) for k in keys if isinstance(k, str))


def _iter_row_path_candidates(row: Any) -> Iterable[tuple[str, Path]]:
    """Yield (key, path) for every on-disk reference in row.advanced.

    Recurses into promotion sub-dicts to extract their
    ``source_step_path`` entry. Each yielded path is already expanduser'd
    but may still be relative -- callers should treat any non-existent
    path as missing without further resolution.
    """
    advanced = _row_advanced(row)
    for key in _ROW_PATH_KEYS:
        path = _coerce_path(advanced.get(key))
        if path is not None:
            yield key, path
    for key in _ROW_PROMOTION_KEYS:
        nested = advanced.get(key)
        if not isinstance(nested, dict):
            continue
        source_path = _coerce_path(nested.get("source_step_path"))
        if source_path is not None:
            # Surface as e.g. "StepAnalyticPromotion.source_step_path" so
            # the dialog can show which promotion the source belongs to.
            yield f"{key}.source_step_path", source_path


# bugs/0021: derived mesh caches that are rebuilt from a source STEP on open.
# Maps the derived-cache advanced key -> the source key it is regenerated from
# (a flat key, or "Promotion.source_step_path" nested form). When the source is
# configured on the row we do NOT flag the derived cache as a missing asset --
# the source STEP is the real dependency (flagged separately if IT is gone), and
# the cache is regenerated automatically on load or by relocating the source.
_DERIVED_CACHE_SOURCES: dict[str, str] = {
    "Solid_3d_stl": "OpticalSolidSourcePath",
    "StepAnalyticBodyStlPath": "StepAnalyticPromotion.source_step_path",
}


def _row_has_source_for_derived_key(advanced: dict[str, Any], derived_key: str) -> bool:
    source_key = _DERIVED_CACHE_SOURCES.get(derived_key)
    if not source_key:
        return False
    if "." in source_key:
        outer, _, inner = source_key.partition(".")
        nested = advanced.get(outer)
        return isinstance(nested, dict) and _coerce_path(nested.get(inner)) is not None
    return _coerce_path(advanced.get(source_key)) is not None


def any_solid_body_unresolved(rows: Iterable[Any]) -> bool:
    """True if any row references a ``Solid_3d_stl`` that cannot be resolved.

    bugs/0021: after the load/regeneration pass, the beam-splitter guards use
    this to SKIP -- rather than assert beam-splitter physics on the analytic
    single-face fallback the system-build safety-net substitutes -- when a
    promoted cube's body cache is still missing (no cache and no source STEP to
    rebuild it from on this machine). Resolves project-relative paths the same
    way the renderer does.
    """
    from KrakenOS.UI.layout_editor import _resolve_project_file_path

    for row in rows or []:
        advanced = _row_advanced(row)
        value = advanced.get("Solid_3d_stl")
        if isinstance(value, str) and value.strip() not in ("", "None"):
            try:
                if not _resolve_project_file_path(value).exists():
                    return True
            except Exception:
                return True
    return False


def scan_missing_assets(
    rows: Iterable[Any],
    *,
    editor: Any | None = None,
) -> list[MissingAsset]:
    """Walk a row list + editor state and return every missing file ref.

    ``rows`` is any iterable of ``SurfaceRow``-shaped objects (the
    scanner reads only ``.name`` / ``.element`` / ``.surface`` / ``.advanced``).
    ``editor`` is optional; when provided, the four ``imported_*_step_path``
    attributes are checked too.

    A reference is considered missing iff its resolved absolute path is
    non-empty *and* does not exist on disk. Skipping rules:

    * Keys recorded in the row's :data:`MISSING_RESOURCE_STATE_ATTR`
      ``keys`` list are skipped (the user already chose to skip them).
    * ``None`` / empty / ``"None"`` values are skipped (no reference).

    Result is ordered: editor-scope entries first (least-frequent but
    most globally consequential), then row-scope entries in row-index
    order, with intra-row keys in :data:`_ROW_PATH_KEYS` priority order.
    """
    seen: set[tuple[str, int, str, str]] = set()
    out: list[MissingAsset] = []

    def emit(scope: str, row_index: int, key: str, path: Path, label: str) -> None:
        try:
            resolved = path if path.is_absolute() else Path.cwd() / path
            resolved = resolved.resolve(strict=False)
        except Exception:
            resolved = path
        token = (scope, int(row_index), str(key), str(resolved))
        if token in seen:
            return
        seen.add(token)
        out.append(
            MissingAsset(
                scope=scope,
                row_index=row_index,
                key=key,
                expected_path=resolved,
                label=label,
            )
        )

    if editor is not None:
        for attr in _EDITOR_PATH_ATTRS:
            value = getattr(editor, attr, None)
            path = _coerce_path(value)
            if path is None:
                continue
            if path.exists():
                continue
            emit("editor", -1, attr, path, attr)

    for index, row in enumerate(rows):
        skipped = _skipped_keys_for_row(row)
        advanced = _row_advanced(row)
        label = _row_label(row, index)
        for key, path in _iter_row_path_candidates(row):
            if key in skipped:
                continue
            # bugs/0021: a derived mesh cache is regenerated from its source
            # STEP on open -- don't complain about the missing cache file when a
            # source is configured. The source (flagged below if IT is gone) is
            # the dependency the user should relocate, not the .cache artefact.
            if key in _DERIVED_CACHE_SOURCES and _row_has_source_for_derived_key(advanced, key):
                continue
            if path.exists():
                continue
            emit("row", index, key, path, label)

    return out


def relocate_advanced_path(
    row_advanced: dict[str, Any],
    key: str,
    new_path: Path,
) -> bool:
    """Write ``new_path`` back into the row's advanced dict for ``key``.

    Handles both flat keys (``StepAnalyticBodyStlPath``) and the
    promotion-nested ``StepAnalyticPromotion.source_step_path`` form
    returned by the scanner. Returns ``True`` if the dict was modified.
    """
    text = str(Path(new_path).expanduser().resolve(strict=False))
    if "." in key:
        outer, _, inner = key.partition(".")
        nested = row_advanced.get(outer)
        if not isinstance(nested, dict):
            return False
        if nested.get(inner) == text:
            return False
        nested[inner] = text
        return True
    if row_advanced.get(key) == text:
        return False
    row_advanced[key] = text
    return True


def mark_row_skipped(
    row_advanced: dict[str, Any],
    key: str,
    *,
    expected_path: Optional[Path] = None,
) -> None:
    """Record that the user chose to skip resolving ``key`` for this row.

    Subsequent scans ignore this key. The renderer's placeholder branch
    keys on the presence of any non-empty ``keys`` list under
    :data:`MISSING_RESOURCE_STATE_ATTR`, so this also triggers the red-
    wireframe-box draw path.
    """
    state = row_advanced.get(MISSING_RESOURCE_STATE_ATTR)
    if not isinstance(state, dict):
        state = {}
        row_advanced[MISSING_RESOURCE_STATE_ATTR] = state
    keys = state.get("keys")
    if not isinstance(keys, list):
        keys = []
        state["keys"] = keys
    if key not in keys:
        keys.append(key)
    skipped_paths = state.get("skipped_paths")
    if not isinstance(skipped_paths, dict):
        skipped_paths = {}
        state["skipped_paths"] = skipped_paths
    if expected_path is not None:
        skipped_paths[key] = str(expected_path)


def clear_row_skip(row_advanced: dict[str, Any], key: str) -> None:
    """Remove ``key`` from the row's skip list (after a successful relocate)."""
    state = row_advanced.get(MISSING_RESOURCE_STATE_ATTR)
    if not isinstance(state, dict):
        return
    keys = state.get("keys")
    if isinstance(keys, list) and key in keys:
        keys.remove(key)
    skipped_paths = state.get("skipped_paths")
    if isinstance(skipped_paths, dict):
        skipped_paths.pop(key, None)
    if not state.get("keys") and not state.get("skipped_paths"):
        row_advanced.pop(MISSING_RESOURCE_STATE_ATTR, None)


def row_has_missing_resource(row: Any) -> bool:
    """Return True if the row carries a non-empty skipped-keys list."""
    state = _row_advanced(row).get(MISSING_RESOURCE_STATE_ATTR)
    if not isinstance(state, dict):
        return False
    keys = state.get("keys")
    return bool(keys) if isinstance(keys, (list, tuple, set, frozenset)) else False
