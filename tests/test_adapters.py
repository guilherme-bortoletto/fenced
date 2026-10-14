"""The adapters, each one against the port it answers and the files it keeps.

The model extractor is tested with a sender of the test's own, so the request it would make
is read and the network is never reached.
"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pytest

from fenced.adapters import llm_extractor
from fenced.adapters.clock import ClockError, FixedClock, SystemClock
from fenced.adapters.fake_extractor import FakeExtractor
from fenced.adapters.json_crm import JsonCrm
from fenced.adapters.json_files import FileError
from fenced.adapters.json_inbox import JsonInbox
from fenced.adapters.json_journal import JsonJournal
from fenced.adapters.llm_extractor import (
    KEY_VARIABLE,
    MODEL_VARIABLE,
    ExtractionFailed,
    LlmExtractor,
    MissingKey,
)
from fenced.domain.lead import Awareness, Lead
from fenced.writes.executor import apply
from fenced.writes.plan import plan
from fenced.writes.undo import undo

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
    lead = Lead("Rita Calloway", "rita@example.com", "We throw bread away.", "unaware")
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
    text = "Hello.\n\nRita Calloway\nWrite to rita@example.com."
    assert FakeExtractor().extract(text) == {
        "name": "Rita Calloway",
        "email": "rita@example.com",
        "awareness": "unaware",
    }


def test_the_fake_extractor_leaves_out_an_address_it_cannot_find():
    assert "email" not in FakeExtractor().extract("Call me back.\n\nTess")


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
