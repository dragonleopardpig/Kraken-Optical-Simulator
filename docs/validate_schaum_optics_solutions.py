"""Validate the Schaum optics Supplementary Problem solution inventory."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from generate_schaum_optics_solutions import (
    CHAPTERS,
    render_chapter,
    render_index,
    validate_configuration,
)
from schaum_optics_worked import SOLUTIONS
from schaum_optics_worked.illustrations import PROBLEMS, TOPICS, figure_name


ROOT = Path(__file__).resolve().parents[1]
COLLECTION = (
    ROOT / "docs" / "source" / "knowledge_base" / "worked_exercises" / "schaum_optics"
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
    validate_configuration()
    failures: list[str] = []
    seen: dict[int, list[int]] = {chapter: [] for chapter in EXPECTED}
    workings: set[str] = set()

    for chapter in EXPECTED:
        matches = list(COLLECTION.glob(f"ch{chapter:02d}_*.rst"))
        if len(matches) != 1:
            failures.append(
                f"chapter {chapter}: expected one source file, found {len(matches)}"
            )
            continue

        path = matches[0]
        text = path.read_text(encoding="utf-8")
        if text != render_chapter(CHAPTERS[chapter - 1]):
            failures.append(
                f"{path}: stale generated page; rerun the solution generator"
            )
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
        if "Substitute the values or boundary conditions attached to this" in text:
            failures.append(f"{path}: still contains the old generic solution route")

    for key, (working, result, check) in SOLUTIONS.items():
        if re.findall(r"^(\d+)\. ", working, re.MULTILINE) != ["1", "2", "3"]:
            failures.append(f"Problem {key}: missing the three explicit worked steps")
        if working in workings:
            failures.append(f"Problem {key}: duplicates another problem's working")
        workings.add(working)
        if ":math:`" not in working or not result.strip() or not check.strip():
            failures.append(
                f"Problem {key}: missing mathematical working, result, or check"
            )

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
    if index != render_index():
        failures.append("index.rst: stale generated index")

    asset_dir = (
        ROOT / "docs/source/_static/knowledge_base/worked_exercises/schaum_optics"
    )
    wanted_assets = {figure_name(key) for key in set(TOPICS) | set(PROBLEMS)}
    actual_assets = {path.name for path in asset_dir.glob("*.svg")}
    if wanted_assets != actual_assets:
        failures.append(f"SVG inventory mismatch: {wanted_assets ^ actual_assets}")
    referenced_assets = set()
    for path in COLLECTION.glob("ch*.rst"):
        text = path.read_text(encoding="utf-8")
        references = re.findall(
            r"^\.\. figure:: .*/(schaum_[^/\n]+\.svg)$", text, re.MULTILINE
        )
        referenced_assets.update(references)
        if text.count("   :alt: ") != len(references):
            failures.append(f"{path}: an illustration lacks alternative text")
    if referenced_assets != wanted_assets:
        failures.append("not every expected SVG is referenced by the chapter pages")
    for filename in sorted(actual_assets):
        path = asset_dir / filename
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as error:
            failures.append(f"{path}: invalid SVG XML: {error}")
            continue
        if (
            root.tag != "{http://www.w3.org/2000/svg}svg"
            or "viewBox" not in root.attrib
        ):
            failures.append(f"{path}: missing SVG root or scalable viewBox")
        if not root.findall(".//{http://www.w3.org/2000/svg}path"):
            failures.append(f"{path}: missing vector paths")
        if root.findall(".//{http://www.w3.org/2000/svg}image"):
            failures.append(f"{path}: unexpectedly contains a raster image")
        for element in root.iter():
            for attribute, value in element.attrib.items():
                if attribute.endswith("href") and not value.startswith("#"):
                    failures.append(f"{path}: nonlocal SVG resource {value}")

    if failures:
        raise SystemExit(
            "Schaum solution validation failed:\n- " + "\n- ".join(failures)
        )

    total = sum(len(numbers) for numbers in seen.values())
    print(
        f"Validated {total} distinct Schaum worked solutions and {len(actual_assets)} SVG illustrations across 8 chapters."
    )


if __name__ == "__main__":
    main()
