"""Add brief answers and expandable details to Fundamentals solutions."""

from __future__ import annotations

import re

from docutils import nodes


COLLECTION_PREFIX = (
    "knowledge_base/worked_exercises/fundamentals_of_photonics/ch"
)
ITEM_TITLE = re.compile(r"^(Exercise|Problem) \d+\.\d+-\d+\b")


def _leading_strong_text(node: nodes.Node) -> str:
    if not isinstance(node, nodes.paragraph) or not node.children:
        return ""
    first = node.children[0]
    return first.astext() if isinstance(first, nodes.strong) else ""


def _is_check(node: nodes.Node) -> bool:
    marker = _leading_strong_text(node)
    return marker.startswith(("Step 5", "Check.", "Checks."))


def _is_explicit_result(node: nodes.Node) -> bool:
    marker = _leading_strong_text(node)
    return "State the numbered result" in marker or marker.startswith(
        ("Numbered result.", "Numbered results.")
    )


def _brief_nodes(section: nodes.section) -> list[nodes.Node]:
    content = list(section.children[1:])
    check_index = next(
        (index for index, child in enumerate(content) if _is_check(child)),
        len(content),
    )

    result_index = next(
        (
            index
            for index, child in enumerate(content[:check_index])
            if _is_explicit_result(child)
        ),
        None,
    )
    if result_index is not None:
        explicit = [
            child
            for child in content[result_index + 1 : check_index]
            if not isinstance(child, nodes.comment)
        ]
        if explicit:
            return explicit

    candidates = content[:check_index]
    boxed_math = [
        child
        for child in candidates
        if isinstance(child, nodes.math_block) and r"\boxed" in child.astext()
    ]
    if boxed_math:
        return [boxed_math[-1]]

    displayed_math = [
        child for child in candidates if isinstance(child, nodes.math_block)
    ]
    if displayed_math:
        return [displayed_math[-1]]

    substantive = [
        child
        for child in candidates
        if isinstance(
            child,
            (nodes.paragraph, nodes.bullet_list, nodes.enumerated_list, nodes.table),
        )
        and not _leading_strong_text(child).startswith(
            (
                "Step 1",
                "Step 2",
                "Step 3",
                "Step 4",
                "Definitions and setup.",
                "Definitions and assumptions.",
                "Mathematical formulas used.",
                "Worked derivation.",
            )
        )
    ]
    return substantive[-1:] or candidates[-1:]


def _sanitized_copy(node: nodes.Node) -> nodes.Node:
    clone = node.deepcopy()
    for descendant in clone.findall(include_self=True):
        if not isinstance(descendant, nodes.Element):
            continue
        for attribute in (
            "ids",
            "names",
            "dupnames",
            "backrefs",
        ):
            if attribute in descendant:
                descendant[attribute] = []
        if isinstance(descendant, nodes.math_block):
            descendant["label"] = None
            descendant["number"] = None
    return clone


def _transform_solutions(app, doctree: nodes.document, docname: str) -> None:
    if not docname.startswith(COLLECTION_PREFIX):
        return

    for section in list(doctree.findall(nodes.section)):
        if not section.children or not isinstance(section.children[0], nodes.title):
            continue
        if not ITEM_TITLE.match(section.children[0].astext()):
            continue

        original = list(section.children[1:])
        if not original:
            continue

        brief = nodes.container(classes=["fop-brief-answer"])
        brief += nodes.paragraph(
            "", "", nodes.strong("", "Brief answer")
        )
        for answer_node in _brief_nodes(section):
            brief += _sanitized_copy(answer_node)

        detail_open = nodes.raw(
            "",
            '<details class="fop-solution-detail">'
            '<summary><span class="fop-show-label">Show detailed steps</span>'
            '<span class="fop-hide-label">Hide detailed steps</span></summary>'
            '<div class="fop-solution-detail-body">',
            format="html",
        )
        detail_close = nodes.raw("", "</div></details>", format="html")
        section.children[1:] = [brief, detail_open, *original, detail_close]
        for child in section.children[1:]:
            child.parent = section


def setup(app):
    app.connect("doctree-resolved", _transform_solutions)
    app.add_css_file(
        "knowledge_base/worked_exercises/fundamentals_of_photonics/"
        "solution_toggle.css"
    )
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
