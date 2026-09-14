"""Gates that run before a commit and before any text leaves this repository.

The six fences live in tests and run through pytest. The text rules live here,
because they also have to run on something that is not a file in this tree, such
as the body of an issue or the prompt of a scheduled run.

    python scripts/gates.py                    fences and text rules over the whole tree
    python scripts/gates.py --text             text rules over every tracked text file
    python scripts/gates.py --text FILE        text rules over one file
    python scripts/gates.py --hook             read a PreToolUse payload on stdin
    python scripts/gates.py --text FILE --terms-file PATH

A terms file is a private list of words that must never reach a public place, one
regular expression per line. It is never part of this repository and never has to
be, because naming what you are hiding in the place you are hiding it from is not
a gate. Point at it from outside with --terms-file, or with FENCED_TERMS_FILE so
that no path belonging to one machine is written down here.

Every failure mode ends in a refusal. A gate that cannot run is a gate that failed.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TEXT_RULES = (
    ("a dash used as punctuation", r"[—–]"),
    ("a semicolon", r";"),
)
TEXT_SUFFIXES = (".md", ".py")
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "build", "dist", ".fenced"}

# Anything that could carry work out of this machine, in any spelling a shell allows.
# Both `git` and `gh`, because `gh repo create --push` leaves just as fast as `git push`.
# The boundary is asymmetric on purpose. A hyphen after the verb means a path such as
# .git/hooks/commit-msg, which commits nothing. A hyphen before it means a flag, --push.
GUARDED = re.compile(r"(?<![\w\-])g(?:it|h)(?![\w\-])[^;&|]*(?<!\w)(commit|push)(?![\w\-])")
MESSAGE = re.compile(r"-{1,2}m(?:essage)?[=\s]+('[^']*'|\"[^\"]*\"|\S+)")
ATTRIBUTION = re.compile(
    r"co-authored-by:\s*claude|generated with .{0,4}claude|claude\.ai/|claude\.com/claude-code",
    re.IGNORECASE,
)


def tracked(root: Path) -> list[Path]:
    """Files git knows about plus files not added yet, since the hook runs before `git add`."""
    names = []
    for extra in ([], ["--others", "--exclude-standard"]):
        try:
            listed = subprocess.run(
                ["git", "-C", str(root), "ls-files", "-z", *extra],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
            names += [n for n in listed.split("\x00") if n]
        except (OSError, subprocess.CalledProcessError):
            names = []
            break
    if names:
        return sorted({root / n for n in names})
    return sorted(
        p
        for p in root.rglob("*")
        if p.is_file() and not set(p.relative_to(root).parts) & SKIP_DIRS
    )


def markdown_prose(text: str) -> list[tuple[int, str]]:
    """Numbered Markdown lines with code, links and comments taken out."""
    text = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.DOTALL)
    prose = []
    inside_code = False
    for number, line in enumerate(text.splitlines(), start=1):
        if re.match(r"^\s*(```|~~~)", line):
            inside_code = not inside_code
            continue
        if inside_code:
            continue
        line = re.sub(r"`[^`]*`", "", line)
        line = re.sub(r"\]\([^)]*\)", "]", line)
        line = re.sub(r"<[^>]*>", "", line)
        prose.append((number, line))
    return prose


def python_prose(text: str) -> list[tuple[int, str]]:
    """Numbered docstring lines. Code is free to use whatever punctuation it needs."""
    tree = ast.parse(text)
    holders = [tree] + [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    prose = []
    for holder in holders:
        body = getattr(holder, "body", [])
        if not body:
            continue
        first = body[0]
        if not isinstance(first, ast.Expr) or not isinstance(first.value, ast.Constant):
            continue
        if not isinstance(first.value.value, str):
            continue
        for offset, line in enumerate(first.value.value.splitlines()):
            prose.append((first.lineno + offset, line))
    return prose


def text_problems(name: str, text: str, terms: list[str]) -> list[str]:
    """Rule breaks in one piece of text, reported as one line each."""
    if name.endswith(".py"):
        try:
            prose = python_prose(text)
        except SyntaxError as broken:
            return [f"{name}: will not parse, {broken}"]
    else:
        prose = markdown_prose(text)
    found = []
    for number, line in prose:
        for label, pattern in TEXT_RULES:
            if re.search(pattern, line):
                found.append(f"{name}:{number} uses {label}")
    for term in terms:
        for number, line in enumerate(text.splitlines(), start=1):
            if re.search(term, line, re.IGNORECASE):
                found.append(f"{name}:{number} matches the private term {term}")
    return found


def check_text(paths: list[Path], terms: list[str], root: Path) -> list[str]:
    """Text rules over the given files, or over every tracked text file."""
    if not paths:
        paths = [p for p in tracked(root) if p.suffix in TEXT_SUFFIXES]
    found = []
    for path in paths:
        try:
            name = path.relative_to(root).as_posix()
        except ValueError:
            name = path.as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as unreadable:
            found.append(f"{name}: could not be read, {unreadable}")
            continue
        found += text_problems(name, text, terms)
    return found


def check_fences(root: Path) -> list[str]:
    """The six fences, through pytest, failing closed when pytest is not there."""
    if importlib.util.find_spec("pytest") is None:
        return ["pytest is not installed, so the fences did not run"]
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_fences.py", "-q"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    if done.returncode == 0:
        return []
    report = (done.stdout + done.stderr).strip().splitlines()
    return ["the fences did not pass"] + report[-40:]


def load_terms(path: str | None) -> list[str]:
    """One regular expression per line, blank lines and comments ignored.

    The path comes from the command line or from FENCED_TERMS_FILE, never from a
    file in here.
    """
    path = path or os.environ.get("FENCED_TERMS_FILE")
    if not path:
        return []
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def run_hook(terms_file: str | None, root: Path) -> int:
    """Block the commit when anything is wrong, and block it when the check breaks."""
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        sys.stderr.write("gates: no readable payload on stdin, so the commit is blocked\n")
        return 2
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command", "")
    if not GUARDED.search(command):
        return 0
    found = check_fences(root) + check_text([], load_terms(terms_file), root)
    if ATTRIBUTION.search(" ".join(MESSAGE.findall(command))):
        found.append("this message carries attribution, which this repository never uses")
    if not found:
        return 0
    sys.stderr.write("gates: blocked\n" + "\n".join(found) + "\n")
    return 2


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run the gates of this repository.")
    parser.add_argument("--hook", action="store_true", help="read a PreToolUse payload on stdin")
    parser.add_argument("--text", nargs="*", metavar="FILE", help="text rules only")
    parser.add_argument("--terms-file", metavar="PATH", help="a private list of terms to refuse")
    args = parser.parse_args(argv)

    if args.hook:
        try:
            return run_hook(args.terms_file, ROOT)
        except Exception as broken:
            sys.stderr.write(f"gates: the check itself broke, so this is blocked, {broken}\n")
            return 2

    try:
        terms = load_terms(args.terms_file)
    except (OSError, ValueError) as unreadable:
        sys.stderr.write(f"gates: the terms file could not be read, {unreadable}\n")
        return 1

    if args.text is not None:
        found = check_text([Path(p) for p in args.text], terms, ROOT)
    else:
        found = check_fences(ROOT) + check_text([], terms, ROOT)

    if found:
        sys.stderr.write("\n".join(found) + "\n")
        return 1
    print("gates: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
