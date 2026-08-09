"""Normalize numbered worked-solution entries to third-level RST headings.

Run without arguments to validate the source tree, or pass ``--write`` to
promote legacy rubrics and inconsistently adorned headings in place.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKED_SOLUTIONS = REPO_ROOT / "docs" / "source" / "knowledge_base" / "worked_exercises"

# These totals cover every numbered Exercise/Problem entry in the seven book
# collections currently published under Worked Exercise Solutions.
EXPECTED_COUNTS = {
    "fundamentals_of_photonics": 445,
    "hecht_optics_5e": 831,
    "introduction_matrix_methods_optics": 27,
    "photonics_essentials": 42,
    "siegman_lasers": 394,
    "schaum_optics": 270,
    "yariv_yeh_photonics_6e": 263,
}

TITLE_PATTERN = r"(?:Exercise|Problem) (?:\d|A\.)[^\n]+"
RUBRIC_RE = re.compile(rf"^\.\. rubric:: (?P<title>{TITLE_PATTERN})$", re.MULTILINE)
DECORATED_HEADING_RE = re.compile(
    rf"^(?P<title>{TITLE_PATTERN})\n(?P<underline>[^\w\s]{{3,}})$",
    re.MULTILINE,
)


def heading(title: str) -> str:
    """Return the canonical third-level heading for one entry title."""

    return f"{title}\n{'^' * len(title)}"


def normalize(text: str) -> str:
    """Return *text* with all recognized entries using caret headings."""

    text = RUBRIC_RE.sub(lambda match: heading(match.group("title")), text)
    return DECORATED_HEADING_RE.sub(lambda match: heading(match.group("title")), text)


def collection_name(path: Path) -> str:
    relative = path.relative_to(WORKED_SOLUTIONS)
    return relative.parts[0] if len(relative.parts) > 1 else "<root>"


def validate(paths: list[Path]) -> Counter[str]:
    """Validate canonical heading markup and return per-collection counts."""

    counts: Counter[str] = Counter()
    failures: list[str] = []

    for path in paths:
        text = path.read_text(encoding="utf-8")
        if RUBRIC_RE.search(text):
            failures.append(f"{path}: contains a legacy exercise/problem rubric")

        lines = text.splitlines()
        for line_number, line in enumerate(lines, start=1):
            if not re.fullmatch(TITLE_PATTERN, line):
                continue
            counts[collection_name(path)] += 1
            expected = "^" * len(line)
            actual = lines[line_number] if line_number < len(lines) else ""
            if actual != expected:
                failures.append(
                    f"{path}:{line_number}: expected a third-level '^' "
                    "underline matching the title length"
                )

    actual_counts = {name: counts[name] for name in EXPECTED_COUNTS}
    if actual_counts != EXPECTED_COUNTS:
        failures.append(
            f"entry inventory mismatch: found {actual_counts}, "
            f"expected {EXPECTED_COUNTS}"
        )
    unexpected = {
        name: count for name, count in counts.items() if name not in EXPECTED_COUNTS
    }
    if unexpected:
        failures.append(
            f"numbered entries found in untracked collections: {unexpected}"
        )

    if failures:
        raise SystemExit(
            "Worked-solution heading validation failed:\n- " + "\n- ".join(failures)
        )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="rewrite legacy rubrics and non-caret entry headings in place",
    )
    args = parser.parse_args()

    paths = sorted(WORKED_SOLUTIONS.rglob("*.rst"))
    changed: list[Path] = []
    if args.write:
        for path in paths:
            original = path.read_text(encoding="utf-8")
            updated = normalize(original)
            if updated != original:
                path.write_text(updated, encoding="utf-8")
                changed.append(path)

    counts = validate(paths)
    print(
        f"Validated {sum(counts.values())} numbered worked-solution headings "
        f"across {len(EXPECTED_COUNTS)} book collections; changed "
        f"{len(changed)} files."
    )


if __name__ == "__main__":
    main()
