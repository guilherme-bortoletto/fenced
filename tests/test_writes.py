"""The write layer, as simulate, apply, undo, and an apply that fails halfway.

The store and the journal here are two small fakes kept in memory. The journal keeps every
entry as the JSON an adapter would write, so what a test reads back is what a file would
hold and not the objects the executor handed over.
"""

from __future__ import annotations

import json
import random

import pytest

from fenced.domain.lead import Awareness, Lead
from fenced.writes.executor import ApplyFailed, StalePlan, apply
from fenced.writes.journal import AlreadyUndone, StandsForNothing, UnknownEntry, undo_plan
from fenced.writes.plan import (
    TEXT_HASH,
    Change,
    DuplicateKey,
    Plan,
    PlanError,
    plan,
    record_of,
    text_hash,
)
from fenced.writes.undo import undo

MESSAGE = "We lose two afternoons a week to the same spreadsheet."


class Crm:
    """A store in memory that can be told which of its writes fail, counted from one."""

    def __init__(self, records=None, fail_on=(), log=None):
        self.records = {key: dict(value) for key, value in (records or {}).items()}
        self.fail_on = set(fail_on)
        self.writes = 0
        self.log = log if log is not None else []

    def read_lead(self, key):
        held = self.records.get(key)
        return None if held is None else dict(held)

    def _count(self, what):
        self.writes += 1
        if self.writes in self.fail_on:
            raise OSError(f"the store refused write {self.writes}")
        self.log.append(what)

    def put_lead(self, key, record):
        self._count(f"put {key}")
        self.records[key] = dict(record)

    def remove_lead(self, key):
        self._count(f"remove {key}")
        del self.records[key]


class Journal:
    """A journal in memory that keeps each entry as one line of JSON."""

    def __init__(self, lines=None, log=None, refuses=False):
        self.lines = list(lines or [])
        self.log = log if log is not None else []
        self.refuses = refuses

    def append(self, entry):
        if self.refuses:
            raise OSError("the journal refused the entry")
        self.lines.append(json.dumps(entry, sort_keys=True))
        self.log.append(f"journal {entry['entry']}")

    def entries(self):
        return [json.loads(line) for line in self.lines]


def lead(name="Ana", email="ana@example.com", message=MESSAGE, awareness="problem_aware"):
    return Lead(name=name, email=email, message=message, awareness=awareness)


def three_leads():
    return [lead(name=f"Person {n}", email=f"p{n}@example.com") for n in (1, 2, 3)]


# A record, and what it keeps of the text.


def test_a_record_keeps_the_fields_and_a_hash_of_the_text_and_never_the_text():
    record = record_of(lead())
    assert record == {
        "name": "Ana",
        "email": "ana@example.com",
        "awareness": "problem_aware",
        TEXT_HASH: text_hash(MESSAGE),
    }
    assert MESSAGE not in json.dumps(record)


def test_a_lead_is_kept_under_its_address_in_lower_case():
    planned = plan(Crm(), [lead(email="Ana@Example.com")])
    assert [change.key for change in planned.changes] == ["ana@example.com"]


def test_a_change_with_no_record_on_either_side_is_refused():
    with pytest.raises(PlanError):
        Change("ana@example.com", None, None)


def test_two_leads_that_land_on_one_key_are_refused():
    with pytest.raises(DuplicateKey):
        plan(Crm(), [lead(), lead(email="ANA@example.com")])


# Planning and simulating write nothing.


def test_planning_reads_the_store_and_writes_nothing():
    crm = Crm()
    planned = plan(crm, [lead()])
    assert crm.writes == 0
    assert planned.diff() == [
        "create ana@example.com",
        "+ awareness: problem_aware",
        "+ email: ana@example.com",
        "+ name: Ana",
        f"+ {TEXT_HASH}: {text_hash(MESSAGE)}",
    ]


def test_a_lead_the_store_already_holds_as_it_stands_plans_no_change():
    crm = Crm({"ana@example.com": record_of(lead())})
    assert plan(crm, [lead()]) == Plan()


def test_an_update_shows_what_goes_and_what_arrives():
    crm = Crm({"ana@example.com": record_of(lead())})
    planned = plan(crm, [lead(awareness=Awareness.READY_TO_BUY)])
    assert planned.diff() == [
        "update ana@example.com",
        "- awareness: problem_aware",
        "+ awareness: ready_to_buy",
        "  email: ana@example.com",
        "  name: Ana",
        f"  {TEXT_HASH}: {text_hash(MESSAGE)}",
    ]


def test_simulating_is_the_default_and_touches_neither_the_store_nor_the_journal():
    crm, journal = Crm(), Journal()
    planned = plan(crm, three_leads())
    outcome = apply(planned, crm, journal)
    assert outcome.simulated is True
    assert outcome.entry is None
    assert list(outcome.diff) == planned.diff()
    assert crm.records == {}
    assert crm.writes == 0
    assert journal.lines == []


# Applying.


def test_applying_writes_the_journal_entry_before_any_record():
    log = []
    crm, journal = Crm(log=log), Journal(log=log)
    outcome = apply(plan(crm, three_leads()), crm, journal, really=True)
    assert outcome.simulated is False
    assert outcome.entry == 1
    assert log == ["journal 1", "put p1@example.com", "put p2@example.com", "put p3@example.com"]
    assert set(crm.records) == {"p1@example.com", "p2@example.com", "p3@example.com"}


def test_the_journal_keeps_the_fields_and_the_hash_and_never_the_text():
    crm, journal = Crm(), Journal()
    apply(plan(crm, [lead()]), crm, journal, really=True)
    assert journal.entries() == [
        {
            "entry": 1,
            "undoes": None,
            "put_back": False,
            "changes": [{"key": "ana@example.com", "before": None, "after": record_of(lead())}],
        }
    ]
    assert all(MESSAGE not in line for line in journal.lines)
    assert all("spreadsheet" not in line for line in journal.lines)


def test_a_journal_that_refuses_the_entry_leaves_the_store_untouched():
    crm = Crm()
    with pytest.raises(OSError):
        apply(plan(crm, three_leads()), crm, Journal(refuses=True), really=True)
    assert crm.records == {}
    assert crm.writes == 0


def test_a_plan_with_nothing_to_change_writes_no_entry():
    crm, journal = Crm(), Journal()
    outcome = apply(Plan(), crm, journal, really=True)
    assert (outcome.simulated, outcome.entry, outcome.diff) == (False, None, ())
    assert journal.lines == []


def test_a_plan_whose_store_moved_since_it_was_read_is_refused_before_anything_is_written():
    crm, journal = Crm(), Journal()
    planned = plan(crm, three_leads())
    crm.records["p2@example.com"] = {"name": "Somebody else"}
    with pytest.raises(StalePlan):
        apply(planned, crm, journal, really=True)
    assert journal.lines == []
    assert crm.records == {"p2@example.com": {"name": "Somebody else"}}


def test_a_key_that_already_holds_the_record_after_is_left_out_of_the_entry():
    crm, journal = Crm(), Journal()
    planned = plan(crm, three_leads())
    crm.records["p2@example.com"] = record_of(three_leads()[1])
    apply(planned, crm, journal, really=True)
    keys = [change["key"] for change in journal.entries()[0]["changes"]]
    assert keys == ["p1@example.com", "p3@example.com"]


# Undo.


def test_undo_puts_back_a_create_and_an_update_from_the_journal():
    crm, journal = Crm(), Journal()
    apply(plan(crm, [lead()]), crm, journal, really=True)
    before = dict(crm.records)
    apply(plan(crm, [lead(awareness="ready_to_buy")]), crm, journal, really=True)
    outcome = undo(2, crm, journal, really=True)
    assert outcome.entry == 3
    assert crm.records == before
    undo(1, crm, journal, really=True)
    assert crm.records == {}
    assert [entry["undoes"] for entry in journal.entries()] == [None, None, 2, 1]


def test_undo_is_simulated_by_default():
    crm, journal = Crm(), Journal()
    apply(plan(crm, [lead()]), crm, journal, really=True)
    outcome = undo(1, crm, journal)
    assert outcome.simulated is True
    assert outcome.diff[0] == "remove ana@example.com"
    assert set(crm.records) == {"ana@example.com"}
    assert len(journal.lines) == 1


def test_undo_reads_the_journal_alone():
    crm, journal = Crm(), Journal()
    apply(plan(crm, [lead()]), crm, journal, really=True)
    apply(plan(crm, [lead(name="Ana Lima")]), crm, journal, really=True)
    # The journal as a file would hold it, read back by a journal that never saw the apply.
    copied = Journal(lines=list(journal.lines))
    assert undo_plan(copied, 2) == Plan(
        (Change("ana@example.com", record_of(lead(name="Ana Lima")), record_of(lead())),),
        undoes=2,
    )
    undo(2, crm, copied, really=True)
    assert crm.records == {"ana@example.com": record_of(lead())}


def test_undo_puts_changes_back_in_the_reverse_order():
    log = []
    crm, journal = Crm(log=log), Journal(log=log)
    apply(plan(crm, three_leads()), crm, journal, really=True)
    log.clear()
    undo(1, crm, journal, really=True)
    assert log == [
        "journal 2",
        "remove p3@example.com",
        "remove p2@example.com",
        "remove p1@example.com",
    ]


def test_an_entry_is_undone_once():
    crm, journal = Crm(), Journal()
    apply(plan(crm, [lead()]), crm, journal, really=True)
    undo(1, crm, journal, really=True)
    with pytest.raises(AlreadyUndone):
        undo(1, crm, journal, really=True)


def test_an_entry_the_journal_does_not_carry_is_refused():
    with pytest.raises(UnknownEntry):
        undo(1, Crm(), Journal())


def test_undo_is_refused_when_the_record_changed_after_the_entry():
    crm, journal = Crm(), Journal()
    apply(plan(crm, [lead()]), crm, journal, really=True)
    crm.records["ana@example.com"] = {"name": "Somebody else"}
    with pytest.raises(StalePlan):
        undo(1, crm, journal, really=True)
    assert len(journal.lines) == 1


# An apply that fails halfway.


def test_an_apply_that_fails_halfway_puts_back_what_landed_and_says_so():
    crm, journal = Crm({"p1@example.com": {"name": "Old"}}, fail_on={2}), Journal()
    with pytest.raises(ApplyFailed) as failed:
        apply(plan(crm, three_leads()), crm, journal, really=True)
    assert str(failed.value) == "entry 1 stopped at change 2 of 3, and entry 2 put it back"
    assert crm.records == {"p1@example.com": {"name": "Old"}}
    entries = journal.entries()
    assert [entry["entry"] for entry in entries] == [1, 2]
    assert [len(entry["changes"]) for entry in entries] == [3, 1]
    assert (entries[1]["undoes"], entries[1]["put_back"]) == (1, True)
    assert entries[1]["changes"] == [
        {"key": "p1@example.com", "before": record_of(three_leads()[0]), "after": {"name": "Old"}}
    ]


def test_an_apply_that_fails_at_its_first_write_still_journals_that_it_was_put_back():
    crm, journal = Crm(fail_on={1}), Journal()
    with pytest.raises(ApplyFailed) as failed:
        apply(plan(crm, three_leads()), crm, journal, really=True)
    assert str(failed.value) == "entry 1 stopped at change 1 of 3, and entry 2 put it back"
    assert crm.records == {}
    assert [(entry["undoes"], entry["changes"]) for entry in journal.entries()][1] == (1, [])
    with pytest.raises(StandsForNothing):
        undo(1, crm, journal)


def test_an_undo_that_was_put_back_leaves_its_entry_to_be_undone_again():
    crm, journal = Crm(fail_on={2}), Journal()
    apply(plan(crm, [lead()]), crm, journal, really=True)
    with pytest.raises(ApplyFailed) as failed:
        undo(1, crm, journal, really=True)
    assert str(failed.value) == "entry 2 stopped at change 1 of 1, and entry 3 put it back"
    assert set(crm.records) == {"ana@example.com"}
    assert [(entry["undoes"], entry["changes"]) for entry in journal.entries()][2] == (2, [])
    with pytest.raises(StandsForNothing) as refused:
        undo(2, crm, journal, really=True)
    assert str(refused.value) == (
        "entry 2 failed and entry 3 put it back, so it stands for nothing, "
        "and trying it again is applying it again"
    )
    with pytest.raises(StandsForNothing) as refused:
        undo(3, crm, journal, really=True)
    assert str(refused.value) == (
        "entry 3 puts back entry 2 after a failed write and stands for nothing"
    )
    outcome = undo(1, crm, journal, really=True)
    assert outcome.entry == 4
    assert crm.records == {}
    with pytest.raises(AlreadyUndone) as refused:
        undo(1, crm, journal, really=True)
    assert str(refused.value) == "entry 1 is already undone by entry 4"


def test_an_apply_whose_putting_back_fails_too_hands_both_entries_to_a_person():
    crm, journal = Crm(fail_on={3, 4}), Journal()
    with pytest.raises(ApplyFailed) as failed:
        apply(plan(crm, three_leads()), crm, journal, really=True)
    assert "stopped at change 3 of 3" in str(failed.value)
    assert "a person reads both" in str(failed.value)
    assert [entry["undoes"] for entry in journal.entries()] == [None, 1]
    assert set(crm.records) == {"p1@example.com", "p2@example.com"}


def test_a_failed_apply_that_was_put_back_is_tried_again_by_applying_it_again():
    crm, journal = Crm(fail_on={2}), Journal()
    planned = plan(crm, three_leads())
    with pytest.raises(ApplyFailed) as failed:
        apply(planned, crm, journal, really=True)
    assert str(failed.value) == "entry 1 stopped at change 2 of 3, and entry 2 put it back"
    assert [len(entry["changes"]) for entry in journal.entries()] == [3, 1]
    assert crm.records == {}
    for number in (1, 2):
        with pytest.raises(StandsForNothing):
            undo(number, crm, journal, really=True)
    outcome = apply(planned, crm, journal, really=True)
    assert outcome.entry == 3
    assert crm.records == {each.email: record_of(each) for each in three_leads()}
    undo(3, crm, journal, really=True)
    assert crm.records == {}


def test_an_entry_comes_back_by_undoing_its_undo_and_is_undone_once_on_the_ordinary_path():
    crm, journal = Crm(), Journal()
    apply(plan(crm, [lead()]), crm, journal, really=True)
    held = dict(crm.records)
    undo(1, crm, journal, really=True)
    assert crm.records == {}
    undo(2, crm, journal, really=True)
    assert crm.records == held
    undo(3, crm, journal, really=True)
    assert crm.records == {}
    with pytest.raises(AlreadyUndone) as refused:
        undo(2, crm, journal, really=True)
    assert str(refused.value) == "entry 2 is already undone by entry 3"
    outcome = undo(4, crm, journal, really=True)
    assert outcome.entry == 5
    assert crm.records == held
    assert [entry["undoes"] for entry in journal.entries()] == [None, 1, 2, 3, 4]


# A random walk of undos against a store that fails at random.


class FlakyCrm(Crm):
    """A store whose every write fails with the same chance, drawn from a seeded source."""

    def __init__(self, chance, source):
        super().__init__()
        self.chance = chance
        self.source = source

    def _count(self, what):
        self.writes += 1
        if self.source.random() < self.chance:
            raise OSError(f"the store refused write {self.writes}")
        self.log.append(what)


def stands(entries, number):
    """Whether one entry stands, read off the line of undos by hand.

    A put back and the attempt it put back stand for nothing. Every other entry stands
    until an entry that counts undoes it, and an undo stands in the same way.
    """
    put_back = {entry["undoes"] for entry in entries if entry["put_back"]}
    counting = [
        entry for entry in entries if not entry["put_back"] and entry["entry"] not in put_back
    ]
    if all(entry["entry"] != number for entry in counting):
        return False
    undoers = [entry["entry"] for entry in counting if entry["undoes"] == number]
    assert len(undoers) <= 1, f"entry {number} is undone by {undoers}"
    return not undoers or not stands(entries, undoers[0])


SEEDS = range(200)
CHANCES = (0.0, 0.15, 0.3)


@pytest.mark.parametrize("chance", CHANCES)
def test_a_random_walk_of_undos_leaves_the_store_where_the_line_of_undos_says(chance):
    for seed in SEEDS:
        source = random.Random(seed)
        crm, journal = FlakyCrm(chance, source), Journal()
        leads = three_leads() + [lead()]
        chosen = leads[: source.randint(1, 4)]
        held = {each.email: record_of(each) for each in chosen}
        steps = [lambda: apply(plan(crm, chosen), crm, journal, really=True)]
        for _ in range(15):
            steps.append(
                lambda: undo(source.randint(1, len(journal.lines)), crm, journal, really=True)
            )
        for step in steps:
            try:
                step()
            except (AlreadyUndone, StandsForNothing):
                pass
            except ApplyFailed as failed:
                if "a person reads both" in str(failed):
                    break
            expected = held if stands(journal.entries(), 1) else {}
            assert crm.records == expected, f"seed {seed}, journal {journal.entries()}"
