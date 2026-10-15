"""What the domain accepts as a lead, and everything it refuses."""

from __future__ import annotations

import dataclasses

import pytest

from fenced.domain.lead import (
    Awareness,
    InvalidEmail,
    InvalidProducts,
    Language,
    Lead,
    LeadError,
    MissingField,
    Segment,
    UnknownAwareness,
    UnknownLanguage,
    UnknownSegment,
)

FIELDS = {
    "name": "Ana Ribeiro",
    "email": "ana@example.com",
    "message": "We are opening a second unit and the spreadsheet stopped working.",
    "awareness": "problem_aware",
    "segment": "retail",
    "language": "pt",
    "products": ["Shelf Scanner"],
}
# The three new fields, given to the constructor where a test builds a lead directly.
REST = {"segment": "food", "language": "en", "products": ()}
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


@pytest.mark.parametrize("field", ["awareness", "segment", "language", "products"])
def test_a_missing_awareness_segment_language_or_list_of_products_is_refused(field):
    fields = {name: value for name, value in FIELDS.items() if name != field}
    with pytest.raises(MissingField, match=field):
        Lead.from_fields(fields)


def test_a_lead_carries_its_segment_its_language_and_its_products():
    lead = Lead.from_fields(FIELDS)
    assert lead.segment is Segment.RETAIL
    assert lead.language is Language.PORTUGUESE
    assert lead.products == ("Shelf Scanner",)


def test_the_segments_and_the_languages_are_the_whole_lists():
    assert [segment.value for segment in Segment] == [
        "food", "retail", "wholesale", "manufacturing", "health"
    ]
    assert [language.value for language in Language] == ["en", "pt", "es", "fr", "de", "it"]


@pytest.mark.parametrize(
    ("field", "written", "expected"),
    [
        ("segment", "  Retail ", Segment.RETAIL),
        ("segment", "HEALTH", Segment.HEALTH),
        ("segment", Segment.FOOD, Segment.FOOD),
        ("language", " PT ", Language.PORTUGUESE),
        ("language", Language.ITALIAN, Language.ITALIAN),
    ],
)
def test_case_and_spacing_are_forgiven_in_a_segment_and_a_language(field, written, expected):
    assert getattr(Lead.from_fields({**FIELDS, field: written}), field) is expected


@pytest.mark.parametrize(
    ("field", "invented", "refusal"),
    [
        ("segment", "", UnknownSegment),
        ("segment", "hospitality", UnknownSegment),
        ("segment", "retail store", UnknownSegment),
        ("segment", "Retail, food", UnknownSegment),
        ("language", "", UnknownLanguage),
        ("language", "english", UnknownLanguage),
        ("language", "nl", UnknownLanguage),
        ("language", "pt-BR", UnknownLanguage),
    ],
)
def test_a_segment_or_a_language_outside_the_set_is_refused(field, invented, refusal):
    with pytest.raises(refusal, match="is not one of"):
        Lead.from_fields({**FIELDS, field: invented})


@pytest.mark.parametrize("field", ["segment", "language"])
@pytest.mark.parametrize("value", NOT_TEXT)
def test_a_segment_or_a_language_that_is_not_text_is_refused(field, value):
    with pytest.raises((UnknownSegment, UnknownLanguage), match="written as text"):
        Lead.from_fields({**FIELDS, field: value})


def test_a_person_who_names_no_product_is_still_a_lead():
    assert Lead.from_fields({**FIELDS, "products": []}).products == ()


def test_products_are_trimmed_and_kept_once_in_the_order_they_were_named():
    named = ["  Starter Kit ", "Shelf Scanner", "Starter Kit", "starter kit"]
    lead = Lead.from_fields({**FIELDS, "products": named})
    assert lead.products == ("Starter Kit", "Shelf Scanner", "starter kit")


@pytest.mark.parametrize(
    "products",
    [
        "Shelf Scanner",
        None,
        {"Shelf Scanner": 1},
        {"Shelf Scanner"},
        ["Shelf Scanner", None],
        ["Shelf Scanner", 3],
        ["Shelf Scanner", "   "],
        ["\u200b"],
    ],
)
def test_products_that_are_not_a_list_of_names_are_refused_rather_than_coerced(products):
    with pytest.raises(InvalidProducts):
        Lead.from_fields({**FIELDS, "products": products})


@pytest.mark.parametrize("given", [None, 42, "name email message awareness", ["name"]])
def test_something_that_is_not_a_mapping_is_refused_as_a_lead_error(given):
    with pytest.raises(LeadError):
        Lead.from_fields(given)


def test_surrounding_space_is_trimmed_on_the_way_in():
    lead = Lead.from_fields({**FIELDS, "name": "  Ana Ribeiro  ", "email": " ana@example.com "})
    assert lead.name == "Ana Ribeiro"
    assert lead.email == "ana@example.com"


def test_the_constructor_is_the_same_boundary_as_the_mapping():
    direct = Lead(
        name="  Ana  ", email="ana@example.com", message=" hello ", awareness="unaware", **REST
    )
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
        Lead(name="Ana", email="ana@example.com", message="hello", awareness="ready", **REST)


def test_every_refusal_is_one_family():
    for error in (
        MissingField,
        InvalidEmail,
        UnknownAwareness,
        UnknownSegment,
        UnknownLanguage,
        InvalidProducts,
    ):
        assert issubclass(error, LeadError)
    assert issubclass(LeadError, ValueError)


@pytest.mark.parametrize(
    "field", ["name", "email", "message", "awareness", "segment", "language", "products"]
)
def test_a_lead_does_not_change_after_it_is_accepted(field):
    lead = Lead.from_fields(FIELDS)
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(lead, field, "something else")
    with pytest.raises(dataclasses.FrozenInstanceError):
        delattr(lead, field)
