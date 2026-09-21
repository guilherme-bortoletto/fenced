"""The six fences of this repository.

Each fence is a plain function that returns the list of things it found wrong,
plus a test that runs it on this tree and expects that list to be empty.

They are hand written on purpose. A reader should see the rule and the test that
enforces it on one screen. When a project outgrows this, import-linter,
pytest-archon and tach do the same job with real machinery.

The last tests plant a violation and expect the fence to reject it.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PURE_PACKAGES = ("domain", "ports")
# Standard library, and still a door to the outside. A pure domain opens none of them.
# The list is written by name and grows by name, which `docs/adr/0005` explains.
DOORS_TO_THE_OUTSIDE = {
    "socket", "ssl", "http", "urllib", "ftplib", "smtplib", "poplib", "imaplib",
    "subprocess", "webbrowser", "xmlrpc", "sqlite3", "shutil", "tempfile",
    "os", "io", "pathlib", "pickle", "shelve", "dbm", "importlib", "builtins",
    "sys", "ctypes", "mmap", "fcntl", "select", "selectors", "signal", "asyncio",
    "socketserver", "multiprocessing", "logging", "zipfile", "tarfile", "gzip",
    "bz2", "lzma", "glob", "fileinput", "linecache", "configparser", "netrc",
    "platform", "getpass", "zoneinfo", "runpy", "code",
    "pkgutil", "zipimport", "modulefinder", "sysconfig", "site",
    # The raw operating system module under either name, and the user database beside it.
    "posix", "nt", "grp", "pwd",
    # A file written, compared or compiled, which is a file like any other.
    "filecmp", "compileall", "py_compile", "zipapp",
    # The terminal, which the record names outright, and the log of the machine.
    "curses", "tty", "termios", "pty", "readline", "rlcompleter", "syslog",
}
# Standard library, and a door of the other kind. What comes back is not in the arguments
# and is not the same twice, so a rule that reads one is a rule no test can pin. A clock,
# a source of randomness and a second thread of execution are the three that matter.
SOURCES_OUTSIDE_THE_ARGUMENTS = {
    "time", "datetime", "random", "secrets", "uuid", "threading",
    # A second thread of execution under its other two names, and a scheduler whose
    # default clock is the one `time` reads.
    "_thread", "concurrent", "sched",
}
NETWORK_NAMES = ("openai", "anthropic", "gemini", "httpx", "requests")
LLM_ADAPTER = Path("src/fenced/adapters/llm_extractor.py")
WRITE_CALLS = ("commit", "create_lead", "create_task")
CRM_MODULES = ("fenced.ports.crm", "fenced.adapters.json_crm")
MAY_REACH_THE_CRM = ("fenced.writes", "fenced.app", "fenced.ports", "fenced.adapters.json_crm")
PROMPT_NAMES = ("PROMPT", "SYSTEM", "INSTRUCTION")
# Names that reach anything without an import statement to read. Four of them run a name
# or a piece of text as code, `open` opens a file, and `input` and `breakpoint` reach
# whoever is at the terminal.
RUNTIME_DOORS = ("__import__", "eval", "exec", "compile", "open", "input", "breakpoint")

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "build", "dist", ".fenced"}


def python_files(folder: Path) -> list[Path]:
    """Every Python file under a folder, sorted, and empty when the folder is absent."""
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.rglob("*.py") if not set(p.parts) & SKIP_DIRS)


def tracked_files(root: Path) -> list[Path]:
    """Files git knows about plus files not added yet, because a commit is about to add them.

    The commit hook runs before `git add`, so an index only view would never see
    the file a run has just written, which is the file most worth looking at.
    """
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


def _inside(name: str, packages: tuple[str, ...]) -> bool:
    """Whether a dotted name is one of these packages or lives under one.

    A plain prefix test would put `fenced.apple` inside `fenced.app`.
    """
    return any(name == package or name.startswith(package + ".") for package in packages)


def module_parts(root: Path, path: Path) -> list[str]:
    """The dotted name of a file under src, as a list of parts."""
    parts = list(path.relative_to(root / "src").with_suffix("").parts)
    return parts[:-1] if parts and parts[-1] == "__init__" else parts


def package_parts(root: Path, path: Path) -> list[str]:
    """The package a relative import in this file counts from.

    A package init counts from the package itself and a module counts from the
    package that holds it, and both of those are the path without its last part.
    """
    return list(path.relative_to(root / "src").with_suffix("").parts)[:-1]


def imported_names(root: Path, path: Path, tree: ast.AST) -> list[str]:
    """Everything this file imports, with relative imports resolved to full names."""
    here = package_parts(root, path)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = here[: max(0, len(here) - node.level + 1)] if node.level else []
            tail = (node.module or "").split(".") if node.module else []
            full = ".".join(base + tail)
            names += [f"{full}.{alias.name}" for alias in node.names]
    return names


# Fence 1. Business rules stay testable offline.


def impure_imports(root: Path) -> list[str]:
    """Imports in domain and ports that leave the pure core or open a door outward.

    A door is a name that answers from outside the arguments. Some of them reach outside
    the process, such as a file or a socket. Some of them answer differently on the same
    call, such as a clock or a source of randomness. Both kinds are refused, because a
    rule that reads either one stops being a rule a test can pin.

    A name in `RUNTIME_DOORS` reaches without an import statement to read, so those are
    refused by name as well.
    """
    found = []
    for package in PURE_PACKAGES:
        for path in python_files(root / "src" / "fenced" / package):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            where = path.relative_to(root).as_posix()
            for node in ast.walk(tree):
                called = getattr(node, "func", None)
                if isinstance(node, ast.Call) and isinstance(called, ast.Name):
                    if called.id in RUNTIME_DOORS:
                        found.append(f"{where}:{node.lineno} calls {called.id}")
            for name in imported_names(root, path, tree):
                parts = name.split(".")
                if parts[0] in DOORS_TO_THE_OUTSIDE:
                    found.append(f"{where} imports {name}, which reaches outside")
                elif parts[0] in SOURCES_OUTSIDE_THE_ARGUMENTS:
                    found.append(
                        f"{where} imports {name}, which answers from outside the arguments"
                    )
                elif parts[0] == "fenced":
                    if parts[1:2] and parts[1] not in PURE_PACKAGES:
                        found.append(f"{where} imports {name}, which is not pure")
                elif parts[0] not in sys.stdlib_module_names:
                    found.append(f"{where} imports {name}")
    return found


def test_domain_and_ports_import_only_the_standard_library():
    assert impure_imports(ROOT) == []


# Fence 2. Changing the model must not mean starting over.


def network_names_outside_the_adapter(root: Path) -> list[str]:
    """Provider and client names anywhere in src or examples other than the one adapter.

    A text search and not an import search, because a provider that arrives as a
    string in a url, a header or a data file counts just the same.
    """
    allowed = root / LLM_ADAPTER
    found = []
    for folder in ("src", "examples"):
        base = root / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or set(path.parts) & SKIP_DIRS or path == allowed:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for name in NETWORK_NAMES:
                if re.search(rf"\b{name}\b", text):
                    found.append(f"{path.relative_to(root).as_posix()} names {name}")
    return found


def test_only_one_adapter_knows_which_model_answers():
    assert network_names_outside_the_adapter(ROOT) == []


# Fence 3. A write keeps its plan, its journal and its undo.


def writes_outside_the_writes_package(root: Path) -> list[str]:
    """A record persisted, or the record store reached at all, from the wrong place.

    The call check catches the plain case. The import check catches the case where
    the call was renamed, aliased or reached through getattr, which the first one
    cannot see.

    Any call named commit counts, a database commit included. That is wide on
    purpose, and the place to put a legitimate one is the writes package.
    """
    guarded = root / "src" / "fenced" / "writes"
    found = []
    for path in python_files(root / "src"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        where = path.relative_to(root).as_posix()
        if not _inside(".".join(module_parts(root, path)), MAY_REACH_THE_CRM):
            for name in imported_names(root, path, tree):
                if _inside(name, CRM_MODULES):
                    found.append(f"{where} imports {name}")
        if guarded in path.parents:
            continue
        for node in ast.walk(tree):
            called = getattr(node, "func", None)
            if isinstance(node, ast.Call) and isinstance(called, ast.Attribute):
                if called.attr in WRITE_CALLS:
                    found.append(f"{where}:{node.lineno} calls {called.attr}")
    return found


def test_nothing_persists_a_record_outside_the_writes_package():
    assert writes_outside_the_writes_package(ROOT) == []


# Fence 4. The prompt must not carry what the domain owns.


def domain_data_in_prompts(root: Path) -> list[str]:
    """Money, products and people inside a prompt, or a prompt assembled at run time.

    A prompt built by interpolation cannot be read here at all, which is why it is
    refused instead of skipped.

    The money shape also matches a version number such as 3.12, so a prompt cannot
    mention one. That is accepted rather than made clever.
    """
    owned = []
    for name in ("catalog.json", "sellers.json"):
        path = root / "examples" / name
        if path.is_file():
            rows = json.loads(path.read_text(encoding="utf-8"))
            owned += [str(row["name"]) for row in rows if "name" in row]
    found = []
    for path in python_files(root / "src"):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if not isinstance(node, ast.Assign):
                continue
            named = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if not any(word in n for n in named for word in PROMPT_NAMES):
                continue
            where = f"{path.relative_to(root).as_posix()}:{node.lineno}"
            if not isinstance(node.value, ast.Constant):
                found.append(f"{where} is assembled at run time")
                continue
            text = node.value.value
            if not isinstance(text, str):
                continue
            if re.search(r"[$€£]|\b\d+[.,]\d{2}\b", text):
                found.append(f"{where} carries a price")
            found += [f"{where} carries {value}" for value in owned if value in text]
    return found


def test_the_prompt_never_carries_a_price_a_product_or_a_seller():
    assert domain_data_in_prompts(ROOT) == []


# Fence 5. A decision stays decided.


def adr_problems(root: Path) -> list[str]:
    """Decision records missing a status, a date or a line in the index."""
    folder = root / "docs" / "adr"
    index = folder / "README.md"
    listed = index.read_text(encoding="utf-8") if index.is_file() else ""
    records = sorted(folder.glob("[0-9]*.md")) if folder.is_dir() else []
    found = [] if records else ["there is no decision record to check"]
    for path in records:
        text = path.read_text(encoding="utf-8")
        status = r"^Status: (proposed|accepted|rejected|superseded|deprecated)$"
        if not re.search(status, text, re.MULTILINE):
            found.append(f"{path.name} has no status")
        if not re.search(r"^Date: \d{4}-\d{2}-\d{2}$", text, re.MULTILINE):
            found.append(f"{path.name} has no date")
        if path.name not in listed:
            found.append(f"{path.name} is not in the index")
    for link in re.findall(r"\]\(([^)]+\.md)\)", listed):
        if not (folder / link).is_file():
            found.append(f"the index points at {link}, which is not here")
    return found


def test_every_decision_record_has_a_status_a_date_and_an_index_line():
    assert adr_problems(ROOT) == []


# Fence 6. Nothing shaped like a credential ever enters the tree.

SECRET_PATTERNS = {
    "a model provider key": r"sk-(?:[A-Za-z0-9]+-)*[A-Za-z0-9]{16,}",
    "a google key": r"AIza[0-9A-Za-z_\-]{20,}",
    "a google client secret": r"GOCSPX-[0-9A-Za-z_\-]{10,}",
    "a github token": r"gh[pousr]_[A-Za-z0-9]{20,}",
    "a fine grained github token": r"github_pat_[0-9A-Za-z_]{20,}",
    "a payment key": r"[sr]k_(?:live|test)_[0-9A-Za-z]{10,}",
    "an aws key id": r"AKIA[0-9A-Z]{16}",
    "a slack token": r"xox[abopsr]-[0-9A-Za-z\-]{10,}",
    "a private key block": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "a json web token": r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}",
    "a password inside a url": r"://[^/\s:@]+:[^/\s@]+@",
    "a long base64 run": r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{60,}={0,2}(?![A-Za-z0-9+/])",
}
# A pinned action is a hex run after an at sign, and a workflow is made of those.
LONG_HEX = r"(?<![0-9a-fA-F])(?<!@)[0-9a-fA-F]{40,}(?![0-9a-fA-F])"


def secrets_in_the_tree(root: Path) -> list[str]:
    """Anything shaped like a credential, and any environment file under version control."""
    found = []
    for path in tracked_files(root):
        name = path.relative_to(root).as_posix()
        if name == ".env" or name.endswith("/.env") or re.search(r"(^|/)\.env\.(?!example$)", name):
            found.append(f"{name} is under version control")
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        patterns = dict(SECRET_PATTERNS)
        if not name.startswith(".github/workflows/"):
            patterns["a long hex run"] = LONG_HEX
        for label, pattern in patterns.items():
            hit = re.search(pattern, text)
            if hit:
                line = text[: hit.start()].count("\n") + 1
                found.append(f"{name}:{line} looks like {label}")
    return found


def test_no_secret_lives_in_this_tree():
    assert secrets_in_the_tree(ROOT) == []


# A fence whose folder is absent passes on nothing, so the shape is a rule of its own.


def test_the_tree_has_the_shape_the_fences_assume():
    wanted = ("src/fenced", "tests", "docs/adr", "scripts", ".github/workflows")
    assert [p for p in wanted if not (ROOT / p).is_dir()] == []


def test_the_import_fence_rejects_a_planted_import(tmp_path):
    planted = tmp_path / "src" / "fenced" / "domain"
    planted.mkdir(parents=True)
    planted.joinpath("lead.py").write_text("import requests\n", encoding="utf-8")
    assert impure_imports(tmp_path) == ["src/fenced/domain/lead.py imports requests"]


def test_the_import_fence_rejects_a_relative_escape_and_a_standard_library_door(tmp_path):
    planted = tmp_path / "src" / "fenced" / "domain"
    planted.mkdir(parents=True)
    planted.joinpath("lead.py").write_text(
        "import socket\nfrom ..adapters.json_crm import JsonCrm\n", encoding="utf-8"
    )
    assert impure_imports(tmp_path) == [
        "src/fenced/domain/lead.py imports socket, which reaches outside",
        "src/fenced/domain/lead.py imports fenced.adapters.json_crm.JsonCrm, which is not pure",
    ]


def test_the_import_fence_reads_a_relative_import_in_a_package_init(tmp_path):
    package = tmp_path / "src" / "fenced" / "domain"
    package.mkdir(parents=True)
    package.joinpath("__init__.py").write_text(
        "from . import lead\nfrom .lead import Lead\n", encoding="utf-8"
    )
    package.joinpath("lead.py").write_text("Lead = object\n", encoding="utf-8")
    assert impure_imports(tmp_path) == []


def test_the_import_fence_rejects_an_import_written_so_it_cannot_be_seen(tmp_path):
    planted = tmp_path / "src" / "fenced" / "ports"
    planted.mkdir(parents=True)
    planted.joinpath("crm.py").write_text(
        "import importlib\n\n\ndef reach():\n    return __import__('socket')\n", encoding="utf-8"
    )
    assert impure_imports(tmp_path) == [
        "src/fenced/ports/crm.py:5 calls __import__",
        "src/fenced/ports/crm.py imports importlib, which reaches outside",
    ]


def test_the_import_fence_rejects_reaching_anything_without_an_import(tmp_path):
    planted = tmp_path / "src" / "fenced" / "domain"
    planted.mkdir(parents=True)
    planted.joinpath("lead.py").write_text(
        "import builtins\n\n\ndef reach():\n    return eval('1')\n", encoding="utf-8"
    )
    assert impure_imports(tmp_path) == [
        "src/fenced/domain/lead.py:5 calls eval",
        "src/fenced/domain/lead.py imports builtins, which reaches outside",
    ]


def test_the_import_fence_rejects_a_bare_open_in_both_pure_packages(tmp_path):
    for package in PURE_PACKAGES:
        planted = tmp_path / "src" / "fenced" / package
        planted.mkdir(parents=True)
        planted.joinpath("reader.py").write_text(
            "def read(path):\n    return open(path).read()\n", encoding="utf-8"
        )
        assert impure_imports(tmp_path) == [
            f"src/fenced/{package}/reader.py:2 calls open"
        ]
        planted.joinpath("reader.py").unlink()


def test_the_import_fence_rejects_a_clock_and_a_source_of_randomness(tmp_path):
    planted = tmp_path / "src" / "fenced" / "domain"
    planted.mkdir(parents=True)
    planted.joinpath("recency.py").write_text(
        "import datetime\nimport random\nfrom ctypes import CDLL\n", encoding="utf-8"
    )
    assert impure_imports(tmp_path) == [
        "src/fenced/domain/recency.py imports datetime, which answers from outside the arguments",
        "src/fenced/domain/recency.py imports random, which answers from outside the arguments",
        "src/fenced/domain/recency.py imports ctypes.CDLL, which reaches outside",
    ]


def test_the_import_fence_rejects_every_way_to_import_a_module_by_name(tmp_path):
    planted = tmp_path / "src" / "fenced" / "domain"
    planted.mkdir(parents=True)
    for name in ("importlib", "runpy", "pkgutil", "zipimport", "modulefinder"):
        planted.joinpath("lead.py").write_text(f"import {name}\n", encoding="utf-8")
        assert impure_imports(tmp_path) == [
            f"src/fenced/domain/lead.py imports {name}, which reaches outside"
        ], f"{name} slipped through"


def test_the_import_fence_rejects_reading_the_install_layout(tmp_path):
    planted = tmp_path / "src" / "fenced" / "ports"
    planted.mkdir(parents=True)
    for name in ("sysconfig", "site"):
        planted.joinpath("crm.py").write_text(f"import {name}\n", encoding="utf-8")
        assert impure_imports(tmp_path) == [
            f"src/fenced/ports/crm.py imports {name}, which reaches outside"
        ], f"{name} slipped through"


def test_the_import_fence_rejects_the_terminal_and_a_second_thread_of_execution(tmp_path):
    """The names issue 28 planted, which the record calls doors and the list did not carry."""
    planted = tmp_path / "src" / "fenced" / "domain"
    planted.mkdir(parents=True)
    outside = ("curses", "tty", "termios", "pty", "syslog", "compileall", "py_compile", "zipapp")
    reasons = {name: "reaches outside" for name in outside}
    reasons["concurrent"] = "answers from outside the arguments"
    for name, reason in sorted(reasons.items()):
        planted.joinpath("lead.py").write_text(f"import {name}\n", encoding="utf-8")
        assert impure_imports(tmp_path) == [
            f"src/fenced/domain/lead.py imports {name}, which {reason}"
        ], f"{name} slipped through"


def test_the_import_fence_rejects_every_module_it_calls_a_door(tmp_path):
    planted = tmp_path / "src" / "fenced" / "domain"
    planted.mkdir(parents=True)
    reasons = {name: "reaches outside" for name in DOORS_TO_THE_OUTSIDE}
    reasons |= {
        name: "answers from outside the arguments" for name in SOURCES_OUTSIDE_THE_ARGUMENTS
    }
    for name, reason in sorted(reasons.items()):
        planted.joinpath("lead.py").write_text(f"import {name}\n", encoding="utf-8")
        assert impure_imports(tmp_path) == [
            f"src/fenced/domain/lead.py imports {name}, which {reason}"
        ], f"{name} slipped through"


def test_the_import_fence_rejects_every_name_it_calls_a_runtime_door(tmp_path):
    planted = tmp_path / "src" / "fenced" / "ports"
    planted.mkdir(parents=True)
    for name in RUNTIME_DOORS:
        planted.joinpath("crm.py").write_text(
            f"def reach(what):\n    return {name}(what)\n", encoding="utf-8"
        )
        assert impure_imports(tmp_path) == [
            f"src/fenced/ports/crm.py:2 calls {name}"
        ], f"{name} slipped through"


def test_the_import_fence_still_admits_the_arithmetic_the_domain_is_made_of(tmp_path):
    planted = tmp_path / "src" / "fenced" / "domain"
    planted.mkdir(parents=True)
    planted.joinpath("scoring.py").write_text(
        "import re\nfrom collections.abc import Mapping\nfrom dataclasses import dataclass\n"
        "from decimal import Decimal\nfrom enum import Enum\nfrom fractions import Fraction\n",
        encoding="utf-8",
    )
    assert impure_imports(tmp_path) == []


def test_a_package_whose_name_merely_starts_the_same_is_not_inside_it(tmp_path):
    planted = tmp_path / "src" / "fenced" / "apple"
    planted.mkdir(parents=True)
    planted.joinpath("core.py").write_text("from fenced.ports.crm import Crm\n", encoding="utf-8")
    assert writes_outside_the_writes_package(tmp_path) == [
        "src/fenced/apple/core.py imports fenced.ports.crm.Crm"
    ]


def test_the_write_fence_rejects_a_record_store_reached_by_another_name(tmp_path):
    allowed = tmp_path / "src" / "fenced" / "app"
    allowed.mkdir(parents=True)
    allowed.joinpath("cli.py").write_text("from fenced.ports.crm import Crm\n", encoding="utf-8")
    refused = tmp_path / "src" / "fenced" / "domain"
    refused.mkdir(parents=True)
    refused.joinpath("lead.py").write_text(
        "from fenced.adapters import json_crm\n", encoding="utf-8"
    )
    assert writes_outside_the_writes_package(tmp_path) == [
        "src/fenced/domain/lead.py imports fenced.adapters.json_crm"
    ]


def test_the_prompt_fence_rejects_a_prompt_built_at_run_time(tmp_path):
    planted = tmp_path / "src" / "fenced" / "adapters"
    planted.mkdir(parents=True)
    planted.joinpath("llm_extractor.py").write_text(
        'PROMPT = f"the price is {price}"\n', encoding="utf-8"
    )
    assert domain_data_in_prompts(tmp_path) == [
        "src/fenced/adapters/llm_extractor.py:1 is assembled at run time"
    ]


def test_the_secret_fence_rejects_assembled_credentials(tmp_path):
    # Assembled at run time on purpose. A real looking literal in this file would
    # be stopped by push protection before anyone could read the test.
    shapes = ["sk-" + "A1b2C3d4" * 4, "sk-ant-api03-" + "A1b2C3d4" * 4, "github_pat_" + "A1" * 12]
    for shape in shapes:
        tmp_path.joinpath("notes.md").write_text(f"key: {shape}\n", encoding="utf-8")
        assert secrets_in_the_tree(tmp_path), f"{shape[:6]} slipped through"


def test_the_secret_fence_rejects_a_versioned_environment_file(tmp_path):
    tmp_path.joinpath(".env").write_text("FENCED_LLM_API_KEY=\n", encoding="utf-8")
    assert secrets_in_the_tree(tmp_path) == [".env is under version control"]


def test_the_provider_fence_rejects_a_name_outside_the_adapter(tmp_path):
    planted = tmp_path / "src" / "fenced" / "domain"
    planted.mkdir(parents=True)
    planted.joinpath("lead.py").write_text('MODEL = "openai"\n', encoding="utf-8")
    assert network_names_outside_the_adapter(tmp_path) == [
        "src/fenced/domain/lead.py names openai"
    ]


def test_the_decision_fence_rejects_a_missing_status_and_a_broken_index(tmp_path):
    folder = tmp_path / "docs" / "adr"
    folder.mkdir(parents=True)
    folder.joinpath("0001-a-decision.md").write_text(
        "# 1. A decision\n\nDate: 2026-09-14\n", encoding="utf-8"
    )
    folder.joinpath("README.md").write_text(
        "| [0001 a decision](0001-a-decision.md) |\n| [0002 gone](0002-gone.md) |\n",
        encoding="utf-8",
    )
    assert adr_problems(tmp_path) == [
        "0001-a-decision.md has no status",
        "the index points at 0002-gone.md, which is not here",
    ]
