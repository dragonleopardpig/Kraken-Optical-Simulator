"""Keep the validators' input fixtures safe in git (bugs/0937).

The validators read their scenes from ``attachment/``, which git ignores and Filen syncs -- so a
scene deleted there (a Filen trash, a snapshot restore, a fresh machine) made its validators SKIP
or fail quietly. The fixtures listed in ``test_fixtures/MANIFEST.txt`` are kept, tracked, under
``test_fixtures/`` at the same relative paths:

    python tools/validator_fixtures.py --check     # missing / differing, per fixture (exit 1 if any missing)
    python tools/validator_fixtures.py --restore   # copy every MISSING fixture back into attachment/
    python tools/validator_fixtures.py --update om05a_folded.py   # adopt an intended change to a scene
    python tools/validator_fixtures.py --collect   # (re)copy every fixture that exists in attachment/

``--restore`` never overwrites a file that exists: ``attachment/`` holds the working scenes, and a
deliberate edit there is the user's. The penta gates run ``--restore`` before they start.
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATTACHMENT = ROOT / "attachment"
FIXTURES = ROOT / "test_fixtures"
MANIFEST = FIXTURES / "MANIFEST.txt"


def manifest() -> list[str]:
    lines = MANIFEST.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def status() -> list[tuple[str, str]]:
    """(path, state) per fixture: ok | missing (from attachment) | differs | untracked (no copy)."""
    rows = []
    for rel in manifest():
        kept, live = FIXTURES / rel, ATTACHMENT / rel
        if not kept.exists():
            rows.append((rel, "untracked"))
        elif not live.exists():
            rows.append((rel, "missing"))
        elif not filecmp.cmp(kept, live, shallow=False):
            rows.append((rel, "differs"))
        else:
            rows.append((rel, "ok"))
    return rows


def restore(*, quiet: bool = False) -> list[str]:
    """Copy every fixture missing from attachment/ back from test_fixtures/; returns them."""
    restored = []
    for rel, state in status():
        if state == "missing":
            target = ATTACHMENT / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(FIXTURES / rel, target)
            restored.append(rel)
    if restored and not quiet:
        print(f"[fixtures] restored {len(restored)} missing fixture(s) from test_fixtures/: {restored}")
    return restored


def copy_in(rels) -> list[str]:
    copied = []
    for rel in rels:
        live = ATTACHMENT / rel
        if live.exists():
            target = FIXTURES / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(live, target)
            copied.append(rel)
    return copied


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--restore", action="store_true")
    group.add_argument("--update", nargs="+", metavar="PATH", help="fixture path(s) relative to attachment/")
    group.add_argument("--collect", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        rows = status()
        for rel, state in rows:
            if state != "ok":
                print(f"{state:9s} {rel}")
        counts = {s: sum(1 for _r, st in rows if st == s) for s in ("ok", "differs", "missing", "untracked")}
        print(f"[fixtures] {len(rows)} fixtures: " + ", ".join(f"{n} {s}" for s, n in counts.items()))
        return 1 if counts["missing"] or counts["untracked"] else 0
    if args.restore:
        restore()
        return 0
    if args.update:
        unknown = [rel for rel in args.update if rel not in manifest()]
        if unknown:
            print(f"not in MANIFEST.txt: {unknown}")
            return 1
        print(f"[fixtures] updated {copy_in(args.update)}")
        return 0
    print(f"[fixtures] collected {len(copy_in(manifest()))} of {len(manifest())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
