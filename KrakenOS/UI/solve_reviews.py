"""A solve's result, shown for review before it is applied (bugs/0955).

Three table-cell solves -- the paraxial thickness solve, the folded mirror solve and the traced
best-image solve -- compute a result and ask "apply this?" in a small window: a line saying what
was solved, the numbers that went in and came out, the rule that produced them, Apply / Cancel.
What that window SAYS is the model's: it is built here from the solve's result, and the Tk window
and the Qt dialog both show it. The windows used to be three hand-built Tk functions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class SolveReview:
    """Everything the review window shows."""

    title: str
    #: one line: what was solved
    intro: str
    #: (label, value as text), in display order
    rows: tuple
    #: the rule that produced the numbers
    rule: str
    apply_label: str = "Apply"
    cancel_label: str = "Cancel"


def paraxial_solve_review(result: dict, fmt: Callable) -> SolveReview:
    """An image-distance, object-distance or single-thickness paraxial solve."""
    target = str(result["target"])
    if target == "image":
        intro = "Review the paraxial solve before applying it."
    elif target == "object":
        intro = "Review the paraxial object-distance solve before applying it."
    else:
        intro = "Solve the selected thickness while keeping the other thickness values fixed."
    rows = [
        ("EFFL [mm]", fmt(result["effl"])),
        ("Front principal plane PPA [mm]", fmt(result["ppa"])),
        ("Back principal plane PPP [mm]", fmt(result["ppp"])),
        ("Object mode", str(result["object_mode_before"])),
        ("Object distance before [mm]", fmt(result["object_distance_before"])),
        ("Image distance before [mm]", fmt(result["image_distance_before"])),
        ("Object distance from H1 [mm]", fmt(result["object_principal"])),
        ("Image distance from H2 [mm]", fmt(result["image_principal"])),
    ]
    if target == "image":
        rows.append(("Solved image gap [mm]", fmt(result["solved_distance"])))
        rows.append(("Apply to row", str(int(result["selected_row"]))))
    elif target == "object":
        rows.append(("Solved object gap [mm]", fmt(result["solved_distance"])))
        rows.append(("Object mode after", str(result["object_mode_after"])))
    else:
        rows.extend([
            ("Solve row", f"{int(result['selected_row'])} ({str(result['target_label'])})"),
            ("Start thickness [mm]", fmt(result["start_value"])),
            ("Solved thickness [mm]", fmt(result["solved_distance"])),
            ("Predicted image gap [mm]", fmt(result["predicted_image_gap"])),
            ("Residual [mm]", fmt(result["residual"])),
            ("Samples", str(int(result["sample_count"]))),
        ])
    rule = ("Thickness solve holds the other gaps fixed and re-evaluates the paraxial cardinal points."
            if target == "thickness" else "Thin-lens with principal planes: 1/f = 1/s + 1/s'")
    return SolveReview("Paraxial Solve", intro, tuple(rows), rule)


def folded_mirror_solve_review(result: dict, fmt: Callable) -> SolveReview:
    """The mirror-to-image gap of a folded system, from the straight-through image distance."""
    rows = (
        ("EFFL [mm]", fmt(result["effl"])),
        ("Front principal plane PPA [mm]", fmt(result["ppa"])),
        ("Back principal plane PPP [mm]", fmt(result["ppp"])),
        ("Object distance before [mm]", fmt(result["object_distance_before"])),
        ("Object distance from H1 [mm]", fmt(result["object_principal"])),
        ("Image distance from H2 [mm]", fmt(result["image_principal"])),
        ("Straight image gap [mm]", fmt(result["straight_image_gap"])),
        ("Gap before mirror [mm]", fmt(result["upstream_gap"])),
        ("Solved mirror thickness [mm]", fmt(result["solved_distance"])),
        ("Apply to row", str(int(result["selected_row"]))),
    )
    return SolveReview(
        "Folded Mirror Solve",
        "Estimate the mirror-to-image gap from the straight-through paraxial image distance.",
        rows,
        "Rule used: mirror thickness = straight-through image gap - gap before mirror")


def best_focus_review(result: dict, fmt: Callable) -> SolveReview:
    """A traced solve: the thickness that minimises the image-plane spot (or the output vergence)."""
    rows = [
        ("Apply to row", str(int(result["selected_row"]))),
        ("Target", str(result["target_label"])),
        ("Start value [mm]", fmt(result["start_value"])),
        ("Search lower [mm]", fmt(result["lower"])),
        ("Search upper [mm]", fmt(result["upper"])),
        ("Solved value [mm]", fmt(result["solved_distance"])),
        ("Best spot RMS [mm]", fmt(result["best_rms"])),
        ("Metric", str(result.get("metric_label", "Image-plane RMS"))),
        ("Samples", str(int(result["sample_count"]))),
    ]
    filter_text = str(result.get("filter_text", "") or "").strip()
    if filter_text:
        rows.insert(7, ("Target path", filter_text))
    return SolveReview(
        "Best Image Solve",
        "Refine the selected thickness by minimizing traced image-plane spot RMS.",
        tuple(rows),
        "This is a traced image solve, not a paraxial estimate.")
