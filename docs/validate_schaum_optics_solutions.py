"""Validate the Schaum optics Supplementary Problem solution inventory."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COLLECTION = (
    ROOT
    / "docs"
    / "source"
    / "knowledge_base"
    / "worked_exercises"
    / "schaum_optics"
)
EXPECTED = {
    1: range(31, 65),
    2: range(26, 48),
    3: range(31, 51),
    4: range(62, 97),
    5: range(48, 87),
    6: range(52, 92),
    7: range(52, 106),
    8: range(22, 48),
}
HEADING = re.compile(r"^Problem (\d+)\.(\d+) — .+\n(\^+)$", re.MULTILINE)


def main() -> None:
    failures: list[str] = []
    seen: dict[int, list[int]] = {chapter: [] for chapter in EXPECTED}

    for chapter in EXPECTED:
        matches = list(COLLECTION.glob(f"ch{chapter:02d}_*.rst"))
        if len(matches) != 1:
            failures.append(
                f"chapter {chapter}: expected one source file, found {len(matches)}"
            )
            continue

        path = matches[0]
        text = path.read_text(encoding="utf-8")
        for match in HEADING.finditer(text):
            heading = match.group(0).splitlines()[0]
            if len(match.group(3)) != len(heading):
                failures.append(f"{path}: underline length mismatch for {heading}")
            found_chapter = int(match.group(1))
            if found_chapter != chapter:
                failures.append(f"{path}: contains a Chapter {found_chapter} problem")
            seen[chapter].append(int(match.group(2)))

        for required in (
            "**Paraphrased task.**",
            "**Formula reference.**",
            "**Worked application.**",
            "**Result.**",
            "**Check.**",
        ):
            count = text.count(required)
            if count != len(EXPECTED[chapter]):
                failures.append(
                    f"{path}: found {count} {required} blocks, expected "
                    f"{len(EXPECTED[chapter])}"
                )
        if re.search(r"\b(?:TODO|TBD|FIXME|placeholder)\b", text, re.IGNORECASE):
            failures.append(f"{path}: contains unfinished placeholder text")

    for chapter, expected_range in EXPECTED.items():
        expected = list(expected_range)
        if seen[chapter] != expected:
            failures.append(
                f"chapter {chapter}: found {seen[chapter]}, expected {expected}"
            )

    index = (COLLECTION / "index.rst").read_text(encoding="utf-8")
    for chapter in EXPECTED:
        if f"ch{chapter:02d}_" not in index:
            failures.append(f"index.rst: Chapter {chapter} is absent from the toctree")
    if "all 270" not in index:
        failures.append("index.rst: missing the declared 270-problem inventory")

    if failures:
        raise SystemExit("Schaum solution validation failed:\n- " + "\n- ".join(failures))

    total = sum(len(numbers) for numbers in seen.values())
    print(f"Validated {total} Schaum supplementary solutions across 8 chapters.")


if __name__ == "__main__":
    main()
