"""What the domain accepts as a lead, and everything it refuses."""

from __future__ import annotations

import dataclasses

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
NOT_TEXT = [None, 0, True, [], {}, 3.5, object()]
REQUIRED_FIELDS = ["name", "email", "message"]


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


@pytest.mark.parametrize(
    "written", ["Problem Aware", "  PROBLEM-AWARE  ", "problem  aware", "problem_aware"]
)
def test_spelling_is_forgiven_because_it_is_not_meaning(written):
    assert Awareness.parse(written) is Awareness.PROBLEM_AWARE


@pytest.mark.parametrize("invented", ["very_aware", "", "5", "problemaware", "aware"])
def test_a_sixth_level_is_refused(invented):
    with pytest.raises(UnknownAwareness):
        Awareness.parse(invented)


@pytest.mark.parametrize("value", NOT_TEXT)
def test_an_awareness_that_is_not_text_is_refused_and_says_so(value):
    with pytest.raises(UnknownAwareness, match="written as text"):
        Awareness.parse(value)


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_a_missing_field_is_refused(field):
    fields = {name: value for name, value in FIELDS.items() if name != field}
    with pytest.raises(MissingField):
        Lead.from_fields(fields)


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
@pytest.mark.parametrize("blank", ["", "   ", "\t\n", "\u200b", "  \ufeff "])
def test_a_blank_field_is_refused(field, blank):
    with pytest.raises(MissingField):
        Lead.from_fields({**FIELDS, field: blank})


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
@pytest.mark.parametrize("value", NOT_TEXT)
def test_a_field_that_is_not_text_is_refused_rather_than_stringified(field, value):
    with pytest.raises(MissingField):
        Lead.from_fields({**FIELDS, field: value})


def test_a_missing_awareness_is_refused():
    fields = {name: value for name, value in FIELDS.items() if name != "awareness"}
    with pytest.raises(MissingField):
        Lead.from_fields(fields)


@pytest.mark.parametrize("given", [None, 42, "name email message awareness", ["name"]])
def test_something_that_is_not_a_mapping_is_refused_as_a_lead_error(given):
    with pytest.raises(LeadError):
        Lead.from_fields(given)


def test_surrounding_space_is_trimmed_on_the_way_in():
    lead = Lead.from_fields({**FIELDS, "name": "  Ana Ribeiro  ", "email": " ana@example.com "})
    assert lead.name == "Ana Ribeiro"
    assert lead.email == "ana@example.com"


def test_the_constructor_is_the_same_boundary_as_the_mapping():
    direct = Lead(name="  Ana  ", email="ana@example.com", message=" hello ", awareness="unaware")
    assert direct.name == "Ana"
    assert direct.message == "hello"
    assert direct.awareness is Awareness.UNAWARE


@pytest.mark.parametrize(
    "address",
    [
        "ana",
        "ana@",
        "@example.com",
        "ana@example",
        "ana@example.",
        "ana@.com",
        "a@b@example.com",
        "ana@example.com>\r\nbcc: someone@example.org",
        "ana example@example.com",
    ],
)
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


@pytest.mark.parametrize("field", ["name", "email", "message", "awareness"])
def test_a_lead_does_not_change_after_it_is_accepted(field):
    lead = Lead.from_fields(FIELDS)
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(lead, field, "something else")
    with pytest.raises(dataclasses.FrozenInstanceError):
        delattr(lead, field)
