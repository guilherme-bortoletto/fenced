"""The command line, run end to end over the examples with the fake extractor and no network.

Every test here goes through `main` with arguments, an environment and two streams of its
own, and a fixture refuses any socket, so a test that reached the network would fail rather
than pass slowly. One test runs `python -m fenced` as a process, which is the command a
reader types.
"""

from __future__ import annotations

import io
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from fenced.app.cli import main

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
INBOX = EXAMPLES / "messages.json"
# Late for the two most aware leads of the examples and open for the other three.
NOW = "2026-10-06T10:00:00+00:00"
LEADS = 5


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("a test of the command line reached for the network")

    monkeypatch.setattr(socket, "socket", refused)
    monkeypatch.setattr(socket, "create_connection", refused)


def fenced(*argv, store, environ=None):
    """Run one command and return its exit code, what it printed and what it complained of."""
    out, err = io.StringIO(), io.StringIO()
    code = main(
        [*argv, "--store", str(store)],
        environ={} if environ is None else environ,
        out=out,
        err=err,
    )
    return code, out.getvalue(), err.getvalue()


def run(store, *extra):
    return fenced("run", "--inbox", str(INBOX), "--now", NOW, *extra, store=store)


def held(store):
    """The records the store file holds, and an empty mapping when there is no file."""
    path = store / "store.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def texts():
    return [message["text"] for message in json.loads(INBOX.read_text(encoding="utf-8"))]


def test_a_run_simulates_by_default_and_writes_nothing(tmp_path):
    store = tmp_path / "store"
    code, out, err = run(store)
    assert (code, err) == (0, "")
    assert "simulated, nothing was written" in out
    assert out.count("  create ") == LEADS
    assert not store.exists()


def test_a_run_prints_each_lead_with_its_next_step_and_hands_one_back(tmp_path):
    code, out, _ = run(tmp_path / "store")
    assert code == 0
    assert "message m1 from Rita Calloway <rita@example.com>" in out
    assert "unaware, next name_the_problem within 72 hours, due 2026-10-08T08:10:00+00:00, open" in out
    assert "ready_to_buy, next hand_to_a_person within 2 hours, due 2026-10-05T17:00:00+00:00, late" in out
    assert "message m6 handed back, a lead needs email" in out


def test_the_clock_decides_which_step_is_late(tmp_path):
    early = fenced(
        "run", "--inbox", str(INBOX), "--now", "2026-10-05T15:30:00+00:00", store=tmp_path / "a"
    )[1]
    late = run(tmp_path / "b")[1]
    assert early.count(", late") == 0
    assert late.count(", late") == 2


def test_a_run_with_write_keeps_the_records_and_journals_them_as_a_run(tmp_path):
    store = tmp_path / "store"
    code, out, err = run(store, "--write")
    assert (code, err) == (0, "")
    assert "written as run 1. Undo it with: fenced undo 1" in out
    records = held(store)
    assert len(records) == LEADS
    assert records["rita@example.com"]["name"] == "Rita Calloway"
    lines = (store / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["entry"] for line in lines] == [1]


def test_neither_file_keeps_a_word_of_any_message(tmp_path):
    store = tmp_path / "store"
    run(store, "--write")
    kept = (store / "store.json").read_text(encoding="utf-8")
    kept += (store / "journal.jsonl").read_text(encoding="utf-8")
    for text in texts():
        first = text.splitlines()[0]
        assert first not in kept


def test_a_second_run_over_the_same_inbox_has_nothing_to_write(tmp_path):
    store = tmp_path / "store"
    run(store, "--write")
    code, out, _ = run(store, "--write")
    assert code == 0
    assert "nothing to write" in out
    assert len((store / "journal.jsonl").read_text(encoding="utf-8").splitlines()) == 1


def test_an_undo_is_simulated_by_default(tmp_path):
    store = tmp_path / "store"
    run(store, "--write")
    code, out, _ = fenced("undo", "1", store=store)
    assert code == 0
    assert "undo of run 1" in out
    assert out.count("  remove ") == LEADS
    assert "simulated, nothing was written" in out
    assert len(held(store)) == LEADS


def test_an_undo_with_write_takes_the_run_back_by_its_id(tmp_path):
    store = tmp_path / "store"
    run(store, "--write")
    code, out, err = fenced("undo", "1", "--write", store=store)
    assert (code, err) == (0, "")
    assert "undone as run 2" in out
    assert held(store) == {}


def test_a_run_is_undone_once_and_its_undo_brings_it_back(tmp_path):
    store = tmp_path / "store"
    run(store, "--write")
    fenced("undo", "1", "--write", store=store)
    code, _, err = fenced("undo", "1", "--write", store=store)
    assert code == 1
    assert err == "refused, entry 1 is already undone by entry 2\n"
    assert fenced("undo", "2", "--write", store=store)[0] == 0
    assert len(held(store)) == LEADS


def test_an_undo_of_a_run_that_never_happened_is_refused(tmp_path):
    code, out, err = fenced("undo", "7", store=tmp_path / "store")
    assert (code, out) == (1, "")
    assert err == "refused, the journal carries no entry 7\n"


def test_the_model_extractor_explains_and_stops_when_the_key_is_absent(tmp_path):
    store = tmp_path / "store"
    code, out, err = fenced(
        "run", "--inbox", str(INBOX), "--extractor", "model", "--write", store=store
    )
    assert (code, out) == (2, "")
    assert "FENCED_LLM_API_KEY" in err
    assert "Nothing was read and nothing was written" in err
    assert not store.exists()


def test_a_moment_with_no_offset_is_refused_before_anything_is_read(tmp_path):
    code, out, err = fenced(
        "run", "--inbox", str(INBOX), "--now", "2026-10-06T10:00:00", store=tmp_path / "store"
    )
    assert (code, out) == (2, "")
    assert "no offset" in err


def test_an_inbox_that_is_not_one_is_refused_and_nothing_is_written(tmp_path):
    inbox = tmp_path / "inbox.json"
    inbox.write_text(json.dumps([{"id": "x", "text": "hello"}]), encoding="utf-8")
    store = tmp_path / "store"
    code, out, err = fenced("run", "--inbox", str(inbox), "--write", store=store)
    assert (code, out) == (1, "")
    assert err.startswith("refused, message 1 of ")
    assert "has no received_at written as text" in err
    assert not store.exists()


def test_python_dash_m_fenced_runs_the_same_command(tmp_path):
    environ = {
        name: value for name, value in os.environ.items() if not name.startswith("FENCED_")
    }
    environ["PYTHONPATH"] = str(ROOT / "src")
    finished = subprocess.run(
        [sys.executable, "-m", "fenced", "run", "--inbox", str(INBOX), "--now", NOW,
         "--store", str(tmp_path / "store")],
        capture_output=True,
        text=True,
        env=environ,
        cwd=tmp_path,
        timeout=60,
    )
    assert (finished.returncode, finished.stderr) == (0, "")
    assert "simulated, nothing was written" in finished.stdout


# The examples are invented, and the issue that asked for them asked for no phone number.
# A phone number is a run of seven or more digits once its spaces, dots, dashes, brackets
# and plus signs are taken out. The moment a message arrived is the one field that is
# digits by design, and it is checked as a moment instead.
PHONE = re.compile(r"\d{7,}")
PHONE_SEPARATORS = re.compile(r"[\s.()+\-]")


def strings_in(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for name, inner in value.items():
            if name != "received_at":
                yield from strings_in(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from strings_in(inner)


def test_the_examples_carry_no_phone_number():
    found = []
    for path in sorted(EXAMPLES.rglob("*.json")):
        for text in strings_in(json.loads(path.read_text(encoding="utf-8"))):
            if PHONE.search(PHONE_SEPARATORS.sub("", text)):
                found.append(f"{path.name} carries {text!r}")
    assert found == []


def test_every_address_in_the_examples_is_on_a_domain_kept_for_examples():
    addresses = re.findall(r"[^\s@]+@([^\s@]+)", INBOX.read_text(encoding="utf-8"))
    assert addresses
    assert {domain.rstrip('".,') for domain in addresses} <= {
        "example.com", "example.org", "example.net"
    }
