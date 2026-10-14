"""The tour in the README is read back against the tree.

Each step of the tour names one path in backticks before anything else. The path has to exist,
the steps are numbered one after another from one, and no path is visited twice. The order is a
choice a person makes, so this file checks that the tour can be walked and not that it is the
right walk.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
README = "README.md"
TOUR_HEADING = "## Fifteen minute tour"
STEP = re.compile(r"^(\d+)\. `([^`]+)`")


def tour_steps(text: str) -> list[tuple[int, str]]:
    """Each step of the tour, as its number and the path it names first."""
    steps = []
    inside = False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip() == TOUR_HEADING
            continue
        found = STEP.match(line) if inside else None
        if found:
            steps.append((int(found.group(1)), found.group(2)))
    return steps


def tour_problems(root: Path) -> list[str]:
    """Where the tour cannot be walked through the tree it describes."""
    if not (root / README).is_file():
        return [f"{README} is not here, so there is no tour to walk"]
    steps = tour_steps((root / README).read_text(encoding="utf-8"))
    if not steps:
        return [f"{README} has no step under {TOUR_HEADING}"]
    found = []
    for expected, (number, path) in enumerate(steps, start=1):
        if number != expected:
            found.append(f"step {number} stands where step {expected} should")
        if not (root / path).exists():
            found.append(f"step {number} names {path}, which is not in the tree")
    paths = [path for _, path in steps]
    found += [
        f"{path} is visited more than once"
        for path in dict.fromkeys(paths)
        if paths.count(path) > 1
    ]
    return found


def test_the_tour_can_be_walked_through_this_tree():
    assert tour_problems(ROOT) == []


def plant(root: Path, steps: str) -> Path:
    """A README with a tour of these steps, and one file the tour can name."""
    (root / "here.md").write_text("here\n", encoding="utf-8")
    (root / README).write_text(f"# planted\n\n{TOUR_HEADING}\n\n{steps}\n## After\n", "utf-8")
    return root


def test_a_tour_of_files_that_exist_is_accepted(tmp_path):
    assert tour_problems(plant(tmp_path, "1. `here.md`. A file.\n")) == []


@pytest.mark.parametrize(
    ("steps", "expected"),
    [
        ("1. `here.md`. A file.\n2. `gone.md`. Not one.\n", "step 2 names gone.md"),
        ("1. `here.md`. A file.\n3. `here.md`. Again.\n", "step 3 stands where step 2"),
        ("1. `here.md`. A file.\n2. `here.md`. Again.\n", "here.md is visited more than once"),
        ("Nothing numbered.\n", "has no step"),
    ],
)
def test_a_tour_that_cannot_be_walked_is_refused(tmp_path, steps, expected):
    problems = tour_problems(plant(tmp_path, steps))
    assert any(expected in problem for problem in problems), problems


def test_a_step_after_the_tour_is_not_read_as_one(tmp_path):
    root = plant(tmp_path, "1. `here.md`. A file.\n")
    text = (root / README).read_text(encoding="utf-8") + "\n1. `gone.md`. Elsewhere.\n"
    (root / README).write_text(text, encoding="utf-8")
    assert tour_problems(root) == []
