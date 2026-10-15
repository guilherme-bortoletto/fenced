"""The adapters, each one against the port it answers and the files it keeps.

The model extractor is tested with a sender of the test's own, so the request it would make
is read and the network is never reached.
"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from fenced.adapters import llm_extractor
from fenced.adapters.clock import ClockError, FixedClock, SystemClock
from fenced.adapters.fake_extractor import FakeExtractor
from fenced.adapters.json_crm import JsonCrm
from fenced.adapters.json_files import FileError
from fenced.adapters.json_inbox import JsonInbox
from fenced.adapters.json_journal import JsonJournal
from fenced.adapters.json_tables import JsonCatalog, JsonHistory, JsonMargins, JsonRoster
from fenced.adapters.llm_extractor import (
    KEY_VARIABLE,
    MODEL_VARIABLE,
    ExtractionFailed,
    LlmExtractor,
    MissingKey,
)
from fenced.domain.lead import FIELDS, Awareness, Language, Lead, Segment
from fenced.domain.matching import Seller
from fenced.writes.executor import apply
from fenced.writes.plan import plan
from fenced.writes.undo import undo

ROOT = Path(__file__).resolve().parent.parent
KEY = "test-key-not-a-real-one"
RECORD = {"name": "Rita Calloway", "email": "rita@example.com"}


# The record store as a file.


def test_the_store_reads_nothing_and_writes_no_file_until_a_record_is_put(tmp_path):
    crm = JsonCrm(tmp_path / "store.json")
    assert crm.read_lead("rita@example.com") is None
    assert not (tmp_path / "store.json").exists()


def test_the_store_keeps_a_record_and_takes_it_away(tmp_path):
    path = tmp_path / "store" / "store.json"
    JsonCrm(path).put_lead("rita@example.com", RECORD)
    assert JsonCrm(path).read_lead("rita@example.com") == RECORD
    JsonCrm(path).remove_lead("rita@example.com")
    assert JsonCrm(path).read_lead("rita@example.com") is None
    assert json.loads(path.read_text(encoding="utf-8")) == {}
    assert [p.name for p in path.parent.iterdir()] == ["store.json"]


@pytest.mark.parametrize(
    "written",
    ["[]", '{"a": "b"}', '{"a": {"name": 1}}', "not json"],
)
def test_the_store_refuses_a_file_that_is_not_records_by_key(tmp_path, written):
    path = tmp_path / "store.json"
    path.write_text(written, encoding="utf-8")
    with pytest.raises(FileError):
        JsonCrm(path).read_lead("a")


# The journal as a file of lines.


def test_the_journal_keeps_one_line_for_each_entry_and_reads_them_back_in_order(tmp_path):
    path = tmp_path / "journal.jsonl"
    assert JsonJournal(path).entries() == []
    JsonJournal(path).append({"entry": 1, "undoes": None, "changes": []})
    JsonJournal(path).append({"entry": 2, "undoes": 1, "changes": []})
    assert [entry["entry"] for entry in JsonJournal(path).entries()] == [1, 2]
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


@pytest.mark.parametrize("line", ["not json", "[1]", '{"entry": "one"}'])
def test_the_journal_refuses_a_line_that_is_not_a_numbered_entry(tmp_path, line):
    path = tmp_path / "journal.jsonl"
    path.write_text(line + "\n", encoding="utf-8")
    with pytest.raises(FileError, match="line 1"):
        JsonJournal(path).entries()


def test_the_write_layer_applies_and_undoes_through_the_two_files(tmp_path):
    lead = Lead(
        "Rita Calloway", "rita@example.com", "We throw bread away.", "unaware", "food", "en", ()
    )
    crm, journal = JsonCrm(tmp_path / "store.json"), JsonJournal(tmp_path / "journal.jsonl")
    outcome = apply(plan(crm, [lead]), crm, journal, really=True)
    assert outcome.entry == 1
    # A fresh pair of adapters reads only what the files hold.
    crm, journal = JsonCrm(tmp_path / "store.json"), JsonJournal(tmp_path / "journal.jsonl")
    assert crm.read_lead("rita@example.com")["name"] == "Rita Calloway"
    assert undo(1, crm, journal, really=True).entry == 2
    assert JsonCrm(tmp_path / "store.json").read_lead("rita@example.com") is None


# The inbox.

MESSAGE = {"id": "m1", "received_at": "2026-10-05T08:10:00+00:00", "text": "Hello"}


def inbox(tmp_path, held):
    path = tmp_path / "inbox.json"
    path.write_text(json.dumps(held), encoding="utf-8")
    return JsonInbox(path)


def test_the_inbox_reads_the_three_fields_of_every_message(tmp_path):
    extra = dict(MESSAGE, note="left out")
    assert inbox(tmp_path, [extra]).messages() == [MESSAGE]


@pytest.mark.parametrize(
    ("held", "refusal"),
    [
        ({"id": "m1"}, "not a list"),
        (["m1"], "is not an object"),
        ([dict(MESSAGE, text="  ")], "has no text"),
        ([dict(MESSAGE, id=1)], "has no id"),
        ([MESSAGE, MESSAGE], "a second time"),
        ([dict(MESSAGE, received_at="Monday")], "not one"),
        ([dict(MESSAGE, received_at="2026-10-05T08:10:00")], "no offset"),
    ],
)
def test_the_inbox_refuses_a_message_it_cannot_count_from(tmp_path, held, refusal):
    with pytest.raises(FileError, match=refusal):
        inbox(tmp_path, held).messages()


def test_the_inbox_refuses_a_file_that_is_not_there(tmp_path):
    with pytest.raises(FileError, match="no inbox"):
        JsonInbox(tmp_path / "absent.json").messages()


# The clock.


def test_the_system_clock_says_a_moment_with_an_offset():
    assert SystemClock().now().endswith("+00:00")


def test_a_fixed_clock_says_the_moment_it_was_given():
    assert FixedClock("2026-10-06T10:00:00+02:00").now() == "2026-10-06T10:00:00+02:00"


@pytest.mark.parametrize("moment", ["2026-10-06T10:00:00", "tomorrow"])
def test_a_fixed_clock_refuses_a_moment_that_is_no_moment_in_particular(moment):
    with pytest.raises(ClockError):
        FixedClock(moment)


# The fake extractor.


@pytest.mark.parametrize(
    ("text", "awareness"),
    [
        ("We throw bread away on Fridays.", Awareness.UNAWARE),
        ("It keeps happening.", Awareness.PROBLEM_AWARE),
        ("We want to compare a few tools.", Awareness.SOLUTION_AWARE),
        ("How much is the scanner?", Awareness.PRODUCT_AWARE),
        ("We are ready to buy, and how much is it?", Awareness.READY_TO_BUY),
    ],
)
def test_the_fake_extractor_reads_the_most_aware_level_it_finds(text, awareness):
    assert FakeExtractor().extract(text)["awareness"] == awareness.value


def test_the_fake_extractor_reads_the_signature_and_the_address():
    text = "Hello, we run the bakery.\n\nRita Calloway\nWrite to rita@example.com."
    assert FakeExtractor().extract(text) == {
        "name": "Rita Calloway",
        "email": "rita@example.com",
        "awareness": "unaware",
        "segment": "food",
        "language": "en",
        "products": [],
    }


def test_the_fake_extractor_leaves_out_an_address_it_cannot_find():
    assert "email" not in FakeExtractor().extract("Call me back.\n\nTess")


@pytest.mark.parametrize(
    ("text", "segment"),
    [
        ("We run a bakery.", Segment.FOOD),
        ("Our dental practice runs out of gloves.", Segment.HEALTH),
        ("The factory floor is a mess.", Segment.MANUFACTURING),
        ("Our two warehouses never agree.", Segment.WHOLESALE),
        ("We sell from one shop.", Segment.RETAIL),
        ("The workshop is busy.", None),
        ("Nothing about a business at all.", None),
    ],
)
def test_the_fake_extractor_reads_the_segment_from_the_first_row_it_finds(text, segment):
    found = FakeExtractor().extract(text).get("segment")
    assert found == (None if segment is None else segment.value)


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("We need the scanner and the counter.", Language.ENGLISH),
        ("Abbiamo un negozio e il nostro magazzino che non torna.", Language.ITALIAN),
        ("Wir haben einen Laden und der Bestand stimmt nicht.", Language.GERMAN),
        ("Nous avons une boutique et notre stock est faux.", Language.FRENCH),
        ("Xyz qrs.", None),
    ],
)
def test_the_fake_extractor_reads_the_language_with_the_most_of_its_words(text, language):
    found = FakeExtractor().extract(text).get("language")
    assert found == (None if language is None else language.value)


def test_the_fake_extractor_reads_runs_of_capitals_as_products_and_skips_the_signature():
    text = (
        "How much is the Shelf Scanner? We also want the Starter Kit and the Shelf Scanner.\n"
        "\nNoor Haddad\nnoor@example.org"
    )
    assert FakeExtractor().extract(text)["products"] == ["Shelf Scanner", "Starter Kit"]


def test_every_example_message_is_read_into_all_six_fields_but_the_one_with_no_address():
    messages = json.loads((ROOT / "examples" / "messages.json").read_text(encoding="utf-8"))
    short = {}
    for message in messages:
        found = FakeExtractor().extract(message["text"])
        short[message["id"]] = sorted(set(FIELDS) - {"message"} - set(found))
    assert short == {message["id"]: [] for message in messages} | {"m6": ["email"]}


# The model extractor.


def answer(fields, stop_reason="end_turn"):
    return json.dumps(
        {
            "stop_reason": stop_reason,
            "content": [
                {"type": "thinking", "thinking": ""},
                {"type": "text", "text": json.dumps(fields)},
            ],
        }
    ).encode("utf-8")


class Sender:
    """A sender that keeps what it was asked and returns what it was told to."""

    def __init__(self, returned):
        self.returned = returned
        self.sent = []

    def __call__(self, url, headers, body):
        self.sent.append((url, dict(headers), json.loads(body)))
        return self.returned


@pytest.mark.parametrize("environ", [{}, {KEY_VARIABLE: ""}, {KEY_VARIABLE: "   "}])
def test_the_model_extractor_is_never_built_without_a_key(environ):
    with pytest.raises(MissingKey, match=KEY_VARIABLE):
        LlmExtractor(environ, send=Sender(b""))


def test_the_model_extractor_sends_the_key_the_prompt_and_the_schema():
    fields = {"name": "Rita Calloway", "email": "rita@example.com", "awareness": "unaware"}
    sender = Sender(answer(fields))
    found = LlmExtractor({KEY_VARIABLE: KEY}, send=sender).extract("Hello")
    assert found == fields
    [(url, headers, body)] = sender.sent
    assert url == llm_extractor.ENDPOINT
    assert headers["x-api-key"] == KEY
    assert body["model"] == llm_extractor.DEFAULT_MODEL
    assert body["system"] == llm_extractor.SYSTEM_PROMPT
    assert body["messages"] == [{"role": "user", "content": "Hello"}]
    schema = body["output_config"]["format"]["schema"]
    assert schema["properties"]["awareness"]["enum"] == [level.value for level in Awareness]
    assert KEY not in json.dumps(body)


def test_the_schema_asks_for_six_fields_and_lets_the_model_say_none_of_these():
    schema = llm_extractor.SCHEMA
    assert sorted(schema["required"]) == sorted(set(FIELDS) - {"message"})
    assert sorted(schema["properties"]) == sorted(schema["required"])
    assert schema["additionalProperties"] is False
    assert schema["properties"]["products"] == {"type": "array", "items": {"type": "string"}}
    for field, kind in (("language", Language), ("segment", Segment)):
        assert schema["properties"][field]["enum"] == [member.value for member in kind] + [""]


@pytest.mark.parametrize("member", [*Language, *Segment], ids=lambda member: member.value)
def test_the_prompt_names_every_language_and_every_segment_the_domain_accepts(member):
    assert f" {member.value} for " in llm_extractor.SYSTEM_PROMPT


def test_an_answer_with_the_six_fields_crosses_the_boundary():
    fields = {
        "name": "Giulia Ferri",
        "email": "giulia.ferri@example.com",
        "awareness": "unaware",
        "products": ["Shelf Scanner"],
        "language": "it",
        "segment": "retail",
    }
    found = LlmExtractor({KEY_VARIABLE: KEY}, send=Sender(answer(fields))).extract("Ciao")
    lead = Lead.from_fields({**found, "message": "Ciao"})
    assert (lead.language, lead.segment, lead.products) == (
        Language.ITALIAN, Segment.RETAIL, ("Shelf Scanner",)
    )


def test_the_model_can_be_changed_from_the_environment():
    sender = Sender(answer({}))
    LlmExtractor({KEY_VARIABLE: KEY, MODEL_VARIABLE: "another-model"}, send=sender).extract("Hi")
    assert sender.sent[0][2]["model"] == "another-model"


@pytest.mark.parametrize(
    "returned",
    [
        b"not json",
        b"[]",
        answer({}, stop_reason="refusal"),
        answer({}, stop_reason="max_tokens"),
        json.dumps({"stop_reason": "end_turn", "content": []}).encode("utf-8"),
        json.dumps(
            {"stop_reason": "end_turn", "content": [{"type": "text", "text": "no"}]}
        ).encode("utf-8"),
        answer(["a list"]),
    ],
)
def test_the_model_extractor_refuses_an_answer_that_is_not_three_fields(returned):
    with pytest.raises(ExtractionFailed):
        LlmExtractor({KEY_VARIABLE: KEY}, send=Sender(returned)).extract("Hello")


def test_a_refused_request_does_not_carry_the_key_into_the_error(monkeypatch):
    def refused(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url, 401, "Unauthorized", {}, io.BytesIO(KEY.encode("utf-8"))
        )

    monkeypatch.setattr(urllib.request, "urlopen", refused)
    with pytest.raises(ExtractionFailed) as failed:
        LlmExtractor({KEY_VARIABLE: KEY}).extract("Hello")
    assert str(failed.value) == "the provider answered 401 Unauthorized"
    assert failed.value.__cause__ is None


def test_a_provider_that_cannot_be_reached_is_a_refusal(monkeypatch):
    def unreachable(request, timeout):
        raise urllib.error.URLError("no route")

    monkeypatch.setattr(urllib.request, "urlopen", unreachable)
    with pytest.raises(ExtractionFailed, match="could not be reached, no route"):
        LlmExtractor({KEY_VARIABLE: KEY}).extract("Hello")


# The catalog, the margin table, the history and the roster.


def written(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_the_example_tables_are_read_through_their_ports():
    examples = ROOT / "examples"
    prices = JsonCatalog(examples / "catalog.json").prices()
    assert prices["Shelf Scanner"] == 1800
    assert set(JsonMargins(examples / "margins.json").margins()) == set(prices)
    assert JsonHistory(examples / "history.json").orders("lena@example.net") == ["Shelf Scanner"]
    sellers = JsonRoster(examples / "sellers.json").sellers()
    assert sellers and all(isinstance(seller, Seller) for seller in sellers)


def test_a_catalog_row_with_no_price_or_a_name_twice_is_refused(tmp_path):
    with pytest.raises(FileError, match="has no price"):
        JsonCatalog(written(tmp_path / "c.json", [{"name": "Kit"}])).prices()
    twice = [{"name": "Kit", "price": 1}, {"name": " Kit ", "price": 2}]
    with pytest.raises(FileError, match="row 2 of .* carries the name 'Kit' a second time"):
        JsonCatalog(written(tmp_path / "c.json", twice)).prices()


def test_a_table_that_is_not_there_is_refused_and_not_read_as_empty(tmp_path):
    for table in (
        JsonCatalog(tmp_path / "gone.json").prices,
        JsonMargins(tmp_path / "gone.json").margins,
        JsonRoster(tmp_path / "gone.json").sellers,
        lambda: JsonHistory(tmp_path / "gone.json").orders("a@example.com"),
    ):
        with pytest.raises(FileError, match="there is no"):
            table()


def test_a_table_of_the_wrong_kind_is_refused(tmp_path):
    with pytest.raises(FileError, match="holds a dict and not a list"):
        JsonCatalog(written(tmp_path / "c.json", {"Kit": 1})).prices()
    with pytest.raises(FileError, match="holds a list and not a dict"):
        JsonMargins(written(tmp_path / "m.json", [0.5])).margins()


def test_a_history_is_looked_up_by_address_in_any_case_and_is_empty_for_a_stranger(tmp_path):
    history = JsonHistory(written(tmp_path / "h.json", {"Ivo@Example.com": ["Kit", "Kit"]}))
    assert history.orders("ivo@example.com") == ["Kit", "Kit"]
    assert history.orders("IVO@EXAMPLE.COM") == ["Kit", "Kit"]
    assert history.orders("nobody@example.com") == []


def test_a_history_that_is_not_a_list_of_orders_is_refused(tmp_path):
    history = JsonHistory(written(tmp_path / "h.json", {"ivo@example.com": "Kit"}))
    with pytest.raises(FileError, match="is not a list"):
        history.orders("ivo@example.com")


def test_a_seller_the_domain_refuses_is_refused_as_a_broken_file(tmp_path):
    row = {
        "name": "Ada Fenwick",
        "segments": "retail",
        "smallest_ticket": 0,
        "largest_ticket": 10,
        "languages": ["en"],
    }
    with pytest.raises(FileError, match="'Ada Fenwick' in .* is not a seller"):
        JsonRoster(written(tmp_path / "s.json", [row])).sellers()
    del row["languages"]
    with pytest.raises(FileError, match="has no languages"):
        JsonRoster(written(tmp_path / "s.json", [row])).sellers()
