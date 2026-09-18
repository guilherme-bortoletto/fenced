"""The identity gate, which reads a command instead of a file.

The fences read this tree. This one reads the command a hook is about to run, because
who a commit says it is from is not in any file until the commit already exists.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NOREPLY = "81657828+someone@users.noreply.github.com"
PERSONAL = "someone@example.com"
REFUSED = f"{PERSONAL} is not a GitHub noreply address, and a commit keeps it"


def load_gates():
    """The gate script, loaded by path, because scripts is not a package."""
    spec = importlib.util.spec_from_file_location("gates", ROOT / "scripts" / "gates.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gates = load_gates()


def clone(root: Path, address: str | None = None) -> Path:
    """A repository of its own, so the address under test is the one this test set."""
    subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
    if address is not None:
        subprocess.run(
            ["git", "-C", str(root), "config", "user.email", address],
            check=True,
            capture_output=True,
        )
    return root


def without_git_environment(monkeypatch):
    """The addresses git reads from the environment, taken out of this process."""
    for name in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        monkeypatch.delenv(name, raising=False)


def test_the_identity_gate_rejects_an_address_passed_inline(tmp_path, monkeypatch):
    without_git_environment(monkeypatch)
    command = f"git -c user.name=Someone -c user.email={PERSONAL} commit -m 'a step'"
    assert gates.identity_problems(command, tmp_path) == [REFUSED]


def test_the_identity_gate_accepts_a_noreply_address_passed_inline(tmp_path, monkeypatch):
    without_git_environment(monkeypatch)
    command = f"git -c user.email={NOREPLY} commit -m 'a step'"
    assert gates.identity_problems(command, tmp_path) == []


def test_the_identity_gate_rejects_an_address_behind_the_author_flag(tmp_path, monkeypatch):
    without_git_environment(monkeypatch)
    command = f"git -c user.email={NOREPLY} commit --author='A Name <{PERSONAL}>' -m 'a step'"
    assert gates.identity_problems(command, tmp_path) == [REFUSED]


def test_the_identity_gate_rejects_an_address_passed_in_the_environment(tmp_path, monkeypatch):
    without_git_environment(monkeypatch)
    command = f"GIT_AUTHOR_EMAIL={PERSONAL} GIT_COMMITTER_EMAIL={NOREPLY} git commit -m 'a step'"
    assert gates.identity_problems(command, tmp_path) == [REFUSED]


def test_the_identity_gate_rejects_an_address_already_in_the_environment(tmp_path, monkeypatch):
    without_git_environment(monkeypatch)
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", PERSONAL)
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", NOREPLY)
    assert gates.identity_problems("git commit -m 'a step'", tmp_path) == [REFUSED]


def test_the_identity_gate_reads_the_address_this_clone_is_configured_with(tmp_path, monkeypatch):
    without_git_environment(monkeypatch)
    here = clone(tmp_path, PERSONAL)
    assert gates.identity_problems("git commit -m 'a step'", here) == [REFUSED]
    subprocess.run(
        ["git", "-C", str(here), "config", "user.email", NOREPLY],
        check=True,
        capture_output=True,
    )
    assert gates.identity_problems("git commit -m 'a step'", here) == []


def test_the_identity_gate_refuses_a_commit_it_cannot_read_an_address_for(tmp_path, monkeypatch):
    without_git_environment(monkeypatch)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "none"))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", str(tmp_path / "none"))
    here = clone(tmp_path / "work")
    assert gates.identity_problems("git commit -m 'a step'", here) == [
        "this clone has no user.email, so who a commit would be from cannot be read"
    ]


def test_the_identity_gate_covers_every_verb_that_writes_a_commit(tmp_path, monkeypatch):
    without_git_environment(monkeypatch)
    for verb in ("commit", "merge", "revert", "cherry-pick", "rebase", "am"):
        command = f"git -c user.email={PERSONAL} {verb} HEAD"
        assert gates.identity_problems(command, tmp_path) == [REFUSED], verb


def test_the_identity_gate_leaves_a_push_alone(tmp_path, monkeypatch):
    without_git_environment(monkeypatch)
    assert gates.identity_problems("git push -u origin a-branch", tmp_path) == []
