"""What the domain accepts as a lead, and everything it refuses."""

from __future__ import annotations

import pytest

from fenced.domain.lead import (
    Awareness,
    InvalidEmail,
    Lead,
    LeadError,
    MissingField,
    UnknownAwareness,
)

FIELDS = {
    "name": "Ana Ribeiro",
    "email": "ana@example.com",
    "message": "We are opening a second unit and the spreadsheet stopped working.",
    "awareness": "problem_aware",
}


def test_a_lead_arrives_and_is_accepted():
    lead = Lead.from_fields(FIELDS)
    assert lead.name == "Ana Ribeiro"
    assert lead.email == "ana@example.com"
    assert lead.awareness is Awareness.PROBLEM_AWARE


def test_the_five_levels_are_the_whole_list():
    assert [level.value for level in Awareness] == [
        "unaware",
        "problem_aware",
        "solution_aware",
        "product_aware",
        "ready_to_buy",
    ]


@pytest.mark.parametrize("level", list(Awareness))
def test_every_level_survives_a_round_trip(level):
    assert Awareness.parse(level.value) is level
    assert Awareness.parse(level) is level


@pytest.mark.parametrize("written", ["Problem Aware", "  PROBLEM-AWARE  ", "problem_aware"])
def test_spelling_is_forgiven_because_it_is_not_meaning(written):
    assert Awareness.parse(written) is Awareness.PROBLEM_AWARE


@pytest.mark.parametrize("invented", ["very_aware", "", "5", None, 3, "problemaware"])
def test_a_sixth_level_is_refused(invented):
    with pytest.raises(UnknownAwareness):
        Awareness.parse(invented)


@pytest.mark.parametrize("field", ["name", "email", "message"])
def test_a_missing_field_is_refused(field):
    fields = {name: value for name, value in FIELDS.items() if name != field}
    with pytest.raises(MissingField):
        Lead.from_fields(fields)


@pytest.mark.parametrize("field", ["name", "email", "message"])
def test_a_blank_field_is_refused(field):
    with pytest.raises(MissingField):
        Lead.from_fields({**FIELDS, field: "   "})


def test_a_missing_awareness_is_refused():
    fields = {name: value for name, value in FIELDS.items() if name != "awareness"}
    with pytest.raises(MissingField):
        Lead.from_fields(fields)


@pytest.mark.parametrize("address", ["ana", "ana@", "@example.com", "ana@example"])
def test_an_address_that_cannot_be_reached_is_refused(address):
    with pytest.raises(InvalidEmail):
        Lead.from_fields({**FIELDS, "email": address})


def test_the_awareness_of_a_lead_is_always_a_level():
    with pytest.raises(UnknownAwareness):
        Lead(name="Ana", email="ana@example.com", message="hello", awareness="ready")


def test_every_refusal_is_one_family():
    for error in (MissingField, InvalidEmail, UnknownAwareness):
        assert issubclass(error, LeadError)
    assert issubclass(LeadError, ValueError)


def test_a_lead_does_not_change_after_it_is_accepted():
    lead = Lead.from_fields(FIELDS)
    with pytest.raises(Exception):
        lead.name = "someone else"
