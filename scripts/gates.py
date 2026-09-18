"""Gates that run before a commit and before any text leaves this repository.

The six fences live in tests and run with the rest of the suite through pytest.
The text rules live here, because they also have to run on something that is not
a file in this tree, such as the body of an issue or the prompt of a scheduled run.
One of them is attribution and a session link, which nobody writes and a publishing tool
appends on its own, so the rule reads a file as it stands rather than as prose.

    python scripts/gates.py                    the whole suite and the text rules over the tree
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
import io
import json
import os
import re
import subprocess
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TEXT_RULES = (
    ("a long dash", r"[\u2014\u2013]"),
    ("a hyphen as punctuation", r"(?:^|\s)-{1,2}(?:\s|$)"),
    ("a semicolon", r";"),
)
SHELLS = ("Bash", "PowerShell")
TEST_TIMEOUT = 120
# A bullet at the start of a line, and a line that is only rule characters.
MARKER = re.compile(r"^\s*[-*+]\s+")
RULE_ACROSS = re.compile(r"^[-*_:|\s]+$")
TEXT_SUFFIXES = (".md", ".py")
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "build", "dist", ".fenced"}

# Anything that could carry work out of this machine, in any spelling a shell allows.
# Both `git` and `gh`, because `gh repo create --push` leaves just as fast as `git push`.
# The boundary is asymmetric on purpose. A hyphen after the verb means a path such as
# .git/hooks/commit-msg, which commits nothing. A hyphen before it means a flag, --push.
VERBS = "commit|push|merge|revert|cherry-pick|rebase|am"
# The verbs that write a commit. A push only moves commits that already carry an author.
AUTHORING_VERBS = "commit|merge|revert|cherry-pick|rebase|am"
REACHES_OUT = r"(?<![\w\-])g(?:it|h)(?![\w\-])[^;&|]*"
GUARDED = re.compile(rf"{REACHES_OUT}(?<!\w)(?:{VERBS})(?![\w\-])")
AUTHORING = re.compile(rf"{REACHES_OUT}(?<!\w)(?:{AUTHORING_VERBS})(?![\w\-])")
# One word of a command, with or without the quotes a shell would take off.
WORD = r"('[^']*'|\"[^\"]*\"|\S+)"
MESSAGE = re.compile(rf"-{{1,2}}m(?:essage)?[=\s]+{WORD}")
# Attribution and a link back to the run that wrote the text. Nobody types either one.
# A tool appends them after the text was written, which is after a person read it, so the
# same pattern runs over the message of a git command and over a file about to be published.
ATTRIBUTION = re.compile(
    r"co-authored-by:\s*claude"
    r"|generated (?:with|by) .{0,4}claude"
    r"|claude\.ai/"
    r"|claude\.com/claude-code",
    re.IGNORECASE,
)

# Every commit on main is authored by a GitHub noreply address. A pull request ref keeps
# its commits after a squash and after the branch is deleted, so a personal address that
# reaches a branch once stays reachable for good.
NOREPLY = re.compile(r"^[^@\s]+@users\.noreply\.github\.com$", re.IGNORECASE)
INLINE_EMAIL = re.compile(rf"-c\s+(?:user|author|committer)\.email\s*=\s*{WORD}")
ENV_EMAIL = re.compile(rf"(?<![\w.\-])(GIT_AUTHOR_EMAIL|GIT_COMMITTER_EMAIL)=\s*{WORD}")
AUTHOR_FLAG = re.compile(rf"--author[=\s]+{WORD}")
CONFIG_TIMEOUT = 20


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


def python_comments(text: str) -> list[tuple[int, str]]:
    """Numbered comment lines.

    A comment and a docstring are the text of a Python file. A string literal is data the
    program holds, and it stays data here, because a gate that names a form has to carry
    that form as a literal to refuse it anywhere else.
    """
    found = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.COMMENT:
                found.append((token.start[0], token.string))
    except (tokenize.TokenError, IndentationError) as broken:
        raise SyntaxError(str(broken)) from broken
    return found


def text_problems(name: str, text: str, terms: list[str]) -> list[str]:
    """Rule breaks in one piece of text, reported as one line each."""
    if name.endswith(".py"):
        try:
            prose = python_prose(text)
            public = sorted(set(prose + python_comments(text)))
        except SyntaxError as broken:
            return [f"{name}: will not parse, {broken}"]
    else:
        prose = markdown_prose(text)
        # Every line as it stands. Markdown prose has the links taken out of it, and a link
        # is half of what this looks for.
        public = list(enumerate(text.splitlines(), start=1))
    found = []
    for number, line in prose:
        # A bullet and a rule across the page are marks, not punctuation.
        if RULE_ACROSS.match(line.strip()):
            continue
        line = MARKER.sub("", line)
        for label, pattern in TEXT_RULES:
            if re.search(pattern, line):
                found.append(f"{name}:{number} uses {label}")
    for number, line in public:
        if ATTRIBUTION.search(line):
            found.append(f"{name}:{number} carries attribution or a session link")
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


def check_tests(root: Path) -> list[str]:
    """The whole suite, through pytest, failing closed when pytest is not there.

    The fences are part of the suite and not the whole of it. A gate that ran only
    the fence file would let a broken test in any other file reach a commit.
    """
    if importlib.util.find_spec("pytest") is None:
        return ["pytest is not installed, so the tests did not run"]
    if any(p.name == "conftest.py" for p in tracked(root)):
        return ["a conftest.py can narrow or rewrite the suite, so the gate refuses one"]
    try:
        done = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=str(root),
            capture_output=True,
            text=True,
            # PYTEST_ADDOPTS from the environment can deselect the very test that matters.
            env={**os.environ, "PYTEST_ADDOPTS": ""},
            timeout=TEST_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return [f"the tests did not finish inside {TEST_TIMEOUT} seconds, so nothing is assumed"]
    if done.returncode == 0:
        return []
    report = (done.stdout + done.stderr).strip().splitlines()
    return ["the tests did not pass"] + report[-40:]


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


def shell_word(value: str) -> str:
    """One word of a command with the quotes a shell would take off taken off."""
    value = value.strip()
    if len(value) > 1 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1]
    return value.strip()


def address_of(value: str) -> str:
    """The address in `A Name <address>`, or the word itself when there are no angles."""
    inside = re.search(r"<([^>]*)>", value)
    return (inside.group(1) if inside else value).strip()


def configured_address(root: Path) -> tuple[str, str]:
    """The address this clone commits with, and a line saying why it could not be read."""
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "config", "--get", "user.email"],
            capture_output=True,
            text=True,
            timeout=CONFIG_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as broken:
        return "", f"git could not say which address this clone commits with, {broken}"
    address = done.stdout.strip()
    if not address:
        return "", "this clone has no user.email, so who a commit would be from cannot be read"
    return address, ""


def identity_problems(command: str, root: Path) -> list[str]:
    """Addresses a commit command would write that are not a GitHub noreply address.

    An address reaches a commit four ways. Inline with `git -c user.email=`, through
    GIT_AUTHOR_EMAIL or GIT_COMMITTER_EMAIL, behind `--author`, and from the
    configuration of the clone. The configured one is read unless the command replaces
    it for the author and for the committer both, because otherwise it is still the one
    that lands on half of the commit.
    """
    if not AUTHORING.search(command):
        return []
    addresses = [shell_word(value) for value in INLINE_EMAIL.findall(command)]
    passed = {name: shell_word(value) for name, value in ENV_EMAIL.findall(command)}
    for name in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        if not passed.get(name) and os.environ.get(name):
            passed[name] = os.environ[name].strip()
    replaced = bool(addresses) or all(
        passed.get(name) for name in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL")
    )
    addresses += [value for value in passed.values() if value]
    addresses += [address_of(shell_word(value)) for value in AUTHOR_FLAG.findall(command)]
    found = []
    if not replaced:
        configured, unread = configured_address(root)
        if unread:
            found.append(unread)
        else:
            addresses.append(configured)
    for address in dict.fromkeys(addresses):
        if not NOREPLY.match(address):
            found.append(f"{address} is not a GitHub noreply address, and a commit keeps it")
    return found


def message_problems(command: str) -> list[str]:
    """Attribution in the message of a git command, which is text no file ever holds."""
    if ATTRIBUTION.search(" ".join(MESSAGE.findall(command))):
        return ["this message carries attribution, which this repository never uses"]
    return []


def run_hook(terms_file: str | None, root: Path) -> int:
    """Block the commit when anything is wrong, and block it when the check breaks."""
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        sys.stderr.write("gates: no readable payload on stdin, so the commit is blocked\n")
        return 2
    if payload.get("tool_name") not in SHELLS:
        return 0
    command = (payload.get("tool_input") or {}).get("command", "")
    if not GUARDED.search(command):
        return 0
    found = check_tests(root) + check_text([], load_terms(terms_file), root)
    found += identity_problems(command, root) + message_problems(command)
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
        found = check_tests(ROOT) + check_text([], terms, ROOT)

    if found:
        sys.stderr.write("\n".join(found) + "\n")
        return 1
    print("gates: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
