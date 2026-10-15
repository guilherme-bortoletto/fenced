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
from decimal import Decimal
from pathlib import Path

import pytest

from fenced.app.cli import main
from fenced.domain.lead import Awareness
from fenced.domain.matching import Need, NobodyEligible, Seller, match
from fenced.domain.reply import draft
from fenced.domain.scoring import WEIGHTS, score, ticket

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
INBOX = EXAMPLES / "messages.json"
# The four tables a run scores and matches against, passed by path so a run reads the same
# files from any folder.
TABLES = (
    "--catalog", str(EXAMPLES / "catalog.json"),
    "--margins", str(EXAMPLES / "margins.json"),
    "--history", str(EXAMPLES / "history.json"),
    "--sellers", str(EXAMPLES / "sellers.json"),
)
# Late for the two most aware leads of the examples and open for the other five.
NOW = "2026-10-06T10:00:00+00:00"
LEADS = 7


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
    return fenced("run", "--inbox", str(INBOX), "--now", NOW, *TABLES, *extra, store=store)


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


def test_a_run_prints_the_segment_the_language_and_the_products_of_each_lead(tmp_path):
    out = run(tmp_path / "store")[1]
    assert "  food, en, products none named\n" in out
    assert "  manufacturing, en, products 'Starter Kit', 'Shelf Scanner'\n" in out
    assert "  health, en, products 'Stock Counter'\n" in out
    assert "  retail, it, products 'Shelf Scanner'\n" in out


def test_every_lead_of_the_examples_names_its_fields_and_most_name_a_product(tmp_path):
    out = run(tmp_path / "store")[1]
    asked = [line for line in out.splitlines() if ", products " in line]
    assert len(asked) == LEADS
    assert sum("none named" not in line for line in asked) >= LEADS - 1


def test_a_run_prints_the_score_of_each_lead_and_the_seller_the_match_picks(tmp_path):
    out = run(tmp_path / "store")[1]
    assert (
        "message m2 from Otto Brennan <otto.brennan@example.org>\n"
        "  problem_aware, next ask_what_was_tried within 48 hours, "
        "due 2026-10-07T09:40:00+00:00, open\n"
        "  retail, en, products 'Stock Counter'\n"
        "  score revenue 0.190, recurrence 0.667, margin 0.350, total 0.3334\n"
        "  ticket 950, taken by Ada Fenwick\n"
    ) in out
    assert "  score revenue 0.550, recurrence 0.000, margin 0.385, total 0.3905\n" in out
    assert "  ticket 2750, taken by Bram Holt\n" in out
    assert "  score revenue 0.360, recurrence 1.000, margin 0.420, total 0.5060\n" in out


def test_a_lead_scoring_or_matching_refuses_prints_the_refusal_by_name(tmp_path):
    out = run(tmp_path / "store")[1]
    assert "  not scored, NothingToScore, a lead that names no product" in out
    assert "  not scored, UnknownProduct, 'Starter Kit' is not in the catalog\n" in out
    assert (
        "  ticket 950, nobody takes it, NobodyEligible, "
        "no seller covers 'health' at 950 in 'en'\n"
    ) in out
    assert (
        "  ticket 1800, nobody takes it, NobodyEligible, "
        "no seller covers 'retail' at 1800 in 'it'\n"
    ) in out


SCORE_LINE = re.compile(
    r"^  score revenue (\S+), recurrence (\S+), margin (\S+), total (\S+)$", re.MULTILINE
)


def test_every_number_printed_is_one_scoring_and_matching_produced(tmp_path):
    out = run(tmp_path / "store")[1]
    catalog = {
        row["name"]: row["price"]
        for row in json.loads((EXAMPLES / "catalog.json").read_text(encoding="utf-8"))
    }
    margins = json.loads((EXAMPLES / "margins.json").read_text(encoding="utf-8"))
    history = json.loads((EXAMPLES / "history.json").read_text(encoding="utf-8"))
    sellers = [
        Seller(**row)
        for row in json.loads((EXAMPLES / "sellers.json").read_text(encoding="utf-8"))
    ]
    blocks = re.split(r"^message ", out.split("\n\nplan for")[0], flags=re.MULTILINE)[1:]
    judged = 0
    for block in blocks:
        found = SCORE_LINE.search(block)
        if found is None:
            continue
        judged += 1
        address = re.search(r"<([^>]+)>", block).group(1)
        segment, language, named = re.search(
            r"^  (\w+), (\w+), products (.+)$", block, re.MULTILINE
        ).groups()
        products = re.findall(r"'([^']+)'", named)
        scored = score(products, catalog, history.get(address, []), margins)
        assert found.groups() == tuple(
            str(part) for part in (scored.revenue, scored.recurrence, scored.margin, scored.total)
        )
        basket = ticket(products, catalog)
        assert f"  ticket {basket}, " in block
        try:
            assert f"taken by {match(Need(segment, basket, language), sellers).name}\n" in block
        except NobodyEligible:
            assert "nobody takes it, NobodyEligible" in block
    assert judged == 5


DRAFT = re.compile(r"^  draft for (.+) to send, nothing was sent\n    (.+)$", re.MULTILINE)
NO_DRAFT = "  no draft, a reply names the seller who takes the lead and this lead has none\n"


def test_a_lead_with_a_seller_prints_its_reply_as_a_draft_nobody_sent(tmp_path):
    out = run(tmp_path / "store")[1]
    assert (
        "  ticket 950, taken by Ada Fenwick\n"
        "  draft for Ada Fenwick to send, nothing was sent\n"
        "    Thanks for writing. Before we talk about Stock Counter, Ada Fenwick will ask what "
        "you have already tried, and will write back within 48 hours.\n"
    ) in out
    assert (
        "    Thanks for writing. You asked about 2 of the things we carry. Bram Holt will send "
        "a comparison within 24 hours, with Shelf Scanner at 1800 beside the rest.\n"
    ) in out
    assert (
        "    Thanks for writing. Shelf Scanner is 1800. Ada Fenwick will offer you a call "
        "within 8 hours.\n"
    ) in out


def test_a_lead_with_no_seller_prints_no_draft_and_says_why(tmp_path):
    out = run(tmp_path / "store")[1]
    blocks = re.split(r"^message ", out.split("\n\nplan for")[0], flags=re.MULTILINE)[1:]
    for block in blocks:
        if " handed back, " in block.splitlines()[0]:
            assert "draft" not in block
        elif "taken by " in block:
            assert DRAFT.search(block) and NO_DRAFT not in block
        else:
            assert NO_DRAFT in f"{block}\n" and DRAFT.search(block) is None
    assert out.count(NO_DRAFT) == 4
    assert len(DRAFT.findall(out)) == 3


def test_every_draft_printed_is_the_one_the_reply_renders_for_that_lead(tmp_path):
    out = run(tmp_path / "store")[1]
    catalog = {
        row["name"]: row["price"]
        for row in json.loads((EXAMPLES / "catalog.json").read_text(encoding="utf-8"))
    }
    sellers = {
        row["name"]: Seller(**row)
        for row in json.loads((EXAMPLES / "sellers.json").read_text(encoding="utf-8"))
    }
    blocks = re.split(r"^message ", out.split("\n\nplan for")[0], flags=re.MULTILINE)[1:]
    drafted = 0
    for block in blocks:
        found = DRAFT.search(block)
        if found is None:
            continue
        drafted += 1
        level = re.search(r"^  (\w+), next ", block, re.MULTILINE).group(1)
        named = re.search(r"^  \w+, \w+, products (.+)$", block, re.MULTILINE).group(1)
        products = re.findall(r"'([^']+)'", named)
        assert f"taken by {found.group(1)}\n" in block
        picked = sellers[found.group(1)]
        language = re.search(r"^  \w+, (\w+), products ", block, re.MULTILINE).group(1)
        assert found.group(2) == draft(
            Awareness.parse(level), language, products, catalog, picked
        )
    assert drafted == 3


# A lead in Portuguese that names a product the catalog carries, from a shop, so a seller
# who speaks Portuguese takes it. Matching passes and only the draft is refused.
PORTUGUESE = {
    "id": "p1",
    "received_at": "2026-10-05T18:00:00+00:00",
    "text": (
        "Olá. Quanto custa o Shelf Scanner? Nossa loja não tem uma forma de contar o estoque."
        "\n\nBruno Dias\nbruno@example.org"
    ),
}


def test_a_lead_a_seller_takes_in_another_language_gets_no_draft_and_says_why(tmp_path):
    inbox = tmp_path / "inbox.json"
    inbox.write_text(json.dumps([PORTUGUESE]), encoding="utf-8")
    code, out, err = fenced(
        "run", "--inbox", str(inbox), "--now", NOW, *TABLES, store=tmp_path / "store"
    )
    assert (code, err) == (0, "")
    assert "message p1 from Bruno Dias <bruno@example.org>\n" in out
    assert "  retail, pt, products 'Shelf Scanner'\n" in out
    assert (
        "  ticket 1800, taken by Bram Holt\n"
        "  no draft, WrongLanguage, the replies are written in en and this lead wrote in pt\n"
    ) in out
    assert DRAFT.search(out) is None
    assert "Thanks for writing" not in out
    assert "plan for 1 of 1 leads" in out


def test_a_draft_is_kept_in_neither_file(tmp_path):
    store = tmp_path / "store"
    out = run(store, "--write")[1]
    drafts = [text for _, text in DRAFT.findall(out)]
    assert drafts
    kept = (store / "store.json").read_text(encoding="utf-8")
    kept += (store / "journal.jsonl").read_text(encoding="utf-8")
    assert "Thanks for writing" not in kept
    for text in drafts:
        assert text not in kept
    assert sorted(path.name for path in store.iterdir()) == ["journal.jsonl", "store.json"]


def test_each_total_printed_is_the_weighted_sum_of_the_parts_beside_it(tmp_path):
    out = run(tmp_path / "store")[1]
    found = SCORE_LINE.findall(out)
    assert found
    for revenue, recurrence, margin, total in found:
        assert Decimal(total) == (
            WEIGHTS["revenue"] * Decimal(revenue)
            + WEIGHTS["recurrence"] * Decimal(recurrence)
            + WEIGHTS["margin"] * Decimal(margin)
        )


def test_a_lead_nobody_can_take_is_still_written_and_so_is_one_never_scored(tmp_path):
    store = tmp_path / "store"
    code, out, _ = run(store, "--write")
    assert code == 0
    records = held(store)
    for address in (
        "hana.okafor@example.net",
        "giulia.ferri@example.com",
        "noor@example.org",
        "rita@example.com",
    ):
        assert address in records
    # The record keeps what it kept before. The score and the seller are printed, not stored.
    assert set(records["hana.okafor@example.net"]) == {"name", "email", "awareness", "text_sha256"}


def test_a_roster_that_carries_one_name_twice_is_refused_before_any_lead_is_printed(tmp_path):
    sellers = json.loads((EXAMPLES / "sellers.json").read_text(encoding="utf-8"))
    twice = tmp_path / "sellers.json"
    twice.write_text(json.dumps([*sellers, sellers[0]]), encoding="utf-8")
    store = tmp_path / "store"
    code, out, err = run(store, "--sellers", str(twice), "--write")
    assert (code, out) == (1, "")
    assert err.startswith("refused, row 4 of ")
    assert "carries the name 'Ada Fenwick' a second time" in err
    assert not store.exists()


def test_a_price_scoring_will_not_add_up_stops_the_run_instead_of_repeating(tmp_path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps([{"name": "Shelf Scanner", "price": "a lot"}]), "utf-8")
    store = tmp_path / "store"
    code, _, err = run(store, "--catalog", str(catalog), "--write")
    assert code == 1
    assert err == "refused, the price of 'Shelf Scanner' is a number, not a str\n"
    assert not store.exists()


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
        [sys.executable, "-m", "fenced", "run", "--inbox", str(INBOX), "--now", NOW, *TABLES,
         "--store", str(tmp_path / "store")],
        capture_output=True,
        text=True,
        env=environ,
        cwd=tmp_path,
        timeout=60,
    )
    assert (finished.returncode, finished.stderr) == (0, "")
    assert "simulated, nothing was written" in finished.stdout
    assert "  ticket 1800, taken by Ada Fenwick\n" in finished.stdout
    assert "  draft for Ada Fenwick to send, nothing was sent\n" in finished.stdout


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
