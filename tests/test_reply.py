"""The reply the model does not write, and everything the render refuses instead."""

from __future__ import annotations

import dataclasses
import re
from decimal import Decimal

import pytest

from fenced.domain.lead import Awareness, UnknownAwareness
from fenced.domain.matching import Seller
from fenced.domain.playbook import PLAYBOOK, Action, window_hours
from fenced.domain.reply import (
    FIELDS,
    PLACEHOLDER,
    TEMPLATES,
    Field,
    InvalidField,
    InvalidSource,
    InvalidTemplate,
    MissingField,
    Source,
    UnknownField,
    UnknownProduct,
    UnsourcedNumber,
    UnusedField,
    draft,
    named_fields,
    price,
    product,
    quantity,
    render,
    reply,
    seller,
    unsourced_numbers,
    window,
)

CATALOG = {"Onboarding review": Decimal("1500"), "Data cleanup": Decimal("900.50")}
PICKED = Seller(
    name="Ada",
    segments=["retail"],
    smallest_ticket=Decimal(0),
    largest_ticket=Decimal("5000"),
    languages=["english"],
)
NAMED = ["Onboarding review", "Data cleanup"]


def built() -> dict[str, Field]:
    """Every field a caller supplies, each one out of its own source."""
    return {
        "product": product("Onboarding review", CATALOG),
        "price": price("Onboarding review", CATALOG),
        "quantity": quantity(NAMED, CATALOG),
        "seller": seller(PICKED),
    }


def supplied(template: str) -> dict[str, Field]:
    """The fields that template asks a caller for, which is all of them but the window."""
    return {name: built()[name] for name in named_fields(template) if name != "window"}


# The table of templates, and what is written in them.


def test_every_action_has_a_template_and_no_template_is_anything_else():
    assert set(TEMPLATES) == set(Action)
    assert len(TEMPLATES) == 5


@pytest.mark.parametrize("action", sorted(Action, key=lambda one: one.value))
def test_a_template_names_only_fields_a_source_can_build(action):
    names = named_fields(TEMPLATES[action])
    assert names
    assert set(names) <= set(FIELDS)


@pytest.mark.parametrize("action", sorted(Action, key=lambda one: one.value))
def test_every_template_says_when_the_person_hears_back(action):
    assert "window" in named_fields(TEMPLATES[action])


@pytest.mark.parametrize("action", sorted(Action, key=lambda one: one.value))
def test_no_template_writes_a_number_of_its_own(action):
    literal = PLACEHOLDER.sub("", TEMPLATES[action])
    assert re.search(r"\d", literal) is None


def test_every_field_of_the_table_is_named_by_some_template():
    named = {name for action in Action for name in named_fields(TEMPLATES[action])}
    assert named == set(FIELDS)


# A full reply.


@pytest.mark.parametrize("level", list(Awareness))
def test_a_full_reply_renders_for_every_level_of_awareness(level):
    template = TEMPLATES[PLAYBOOK[level].action]
    text = reply(level, supplied(template))
    assert text == render(template, {**supplied(template), "window": window(level)})
    assert "{" not in text and "}" not in text
    assert PICKED.name in text
    assert str(window_hours(level)) in text


@pytest.mark.parametrize("level", list(Awareness))
def test_the_hours_in_a_reply_are_the_hours_that_level_answers_with(level):
    text = reply(level, supplied(TEMPLATES[PLAYBOOK[level].action]))
    hours = [int(run) for run in re.findall(r"\b\d+\b", text)]
    assert window_hours(level) in hours


def test_every_number_in_a_reply_is_one_a_field_produced():
    text = reply(Awareness.READY_TO_BUY, supplied(TEMPLATES[Action.HAND_TO_A_PERSON]))
    assert "1500" in text
    runs = [found.split(" at ")[0] for found in unsourced_numbers(text, [])]
    assert runs == ["1500", "2"]


def test_a_level_written_as_text_reaches_the_same_reply():
    template = TEMPLATES[PLAYBOOK[Awareness.PRODUCT_AWARE].action]
    assert reply("  PRODUCT AWARE  ", supplied(template)) == reply(
        Awareness.PRODUCT_AWARE, supplied(template)
    )


@pytest.mark.parametrize("invented", ["very_aware", "", None, 3, ["unaware"]])
def test_a_sixth_level_never_reaches_a_reply(invented):
    with pytest.raises(UnknownAwareness):
        reply(invented, {})
    with pytest.raises(UnknownAwareness):
        window(invented)


# A field the template names and nothing supplied.


def test_a_missing_field_is_refused_instead_of_rendered():
    template = TEMPLATES[Action.OFFER_A_CALL]
    fields = supplied(template)
    del fields["price"]
    with pytest.raises(MissingField):
        render(template, {**fields, "window": window(Awareness.PRODUCT_AWARE)})


def test_a_reply_with_no_field_at_all_is_refused():
    with pytest.raises(MissingField):
        reply(Awareness.READY_TO_BUY, {})


@pytest.mark.parametrize("given", [None, "product", ["product"], 3])
def test_a_reply_is_filled_from_a_mapping_and_nothing_else(given):
    with pytest.raises(MissingField):
        reply(Awareness.READY_TO_BUY, given)
    with pytest.raises(MissingField):
        render(TEMPLATES[Action.OFFER_A_CALL], given)


def test_a_field_the_template_has_no_place_for_is_refused():
    template = TEMPLATES[Action.OFFER_A_CALL]
    filled = {**supplied(template), "window": window(Awareness.PRODUCT_AWARE)}
    with pytest.raises(UnusedField):
        render(template, {**filled, "quantity": quantity(NAMED, CATALOG)})


def test_a_reply_builds_its_own_window_and_refuses_one_passed_in():
    template = TEMPLATES[Action.OFFER_A_CALL]
    with pytest.raises(UnusedField):
        reply(Awareness.PRODUCT_AWARE, {**supplied(template), "window": window(Awareness.UNAWARE)})


# A value that no source produced.


def test_a_field_that_claims_a_source_which_did_not_build_it_is_refused():
    with pytest.raises(InvalidField):
        Field(name="price", text="1500", source=Source.MATCHING)
    with pytest.raises(InvalidField):
        Field(name="seller", text="Ada", source=Source.PLAYBOOK)
    with pytest.raises(InvalidField):
        Field(name="window", text="2", source=Source.CATALOG)


@pytest.mark.parametrize("invented", ["deadline", "name", "message", "", None, 3])
def test_a_field_no_source_can_build_does_not_exist(invented):
    with pytest.raises(UnknownField):
        Field(name=invented, text="something", source=Source.CATALOG)


def test_a_template_that_names_a_field_no_source_can_build_is_refused():
    with pytest.raises(UnknownField):
        render("{seller} will write about {deadline}.", {"seller": seller(PICKED)})


@pytest.mark.parametrize("empty", ["", "   ", None, 3, Decimal("1500")])
def test_a_field_renders_as_text_with_something_in_it(empty):
    with pytest.raises(InvalidField):
        Field(name="price", text=empty, source=Source.CATALOG)


def test_a_field_filed_under_the_name_of_another_is_refused():
    with pytest.raises(InvalidField):
        render("{price} is the price.", {"price": product("Data cleanup", CATALOG)})


def test_a_value_that_is_not_a_field_at_all_is_refused():
    with pytest.raises(InvalidField):
        render("{price} is the price.", {"price": "1500"})


# A number nobody answers for.


def test_a_number_the_template_carries_is_refused():
    with pytest.raises(UnsourcedNumber):
        render("{seller} will write back within 24 hours.", {"seller": seller(PICKED)})


def test_a_number_the_template_hides_in_a_word_is_refused_as_well():
    with pytest.raises(UnsourcedNumber):
        render("{seller} will send the report for Q3.", {"seller": seller(PICKED)})


def test_a_date_and_a_quantity_pass_because_they_came_from_a_field():
    text = "3 of them, ready on 2026-10-03"
    assert unsourced_numbers(text, [(0, 1), (20, 30)]) == []
    assert unsourced_numbers(text, [(20, 30)]) == ["3 at 0"]
    assert unsourced_numbers(text, [(0, 1)]) == ["2026 at 20", "10 at 25", "03 at 28"]


def test_a_number_half_inside_a_field_is_not_covered_by_it():
    assert unsourced_numbers("1500", [(0, 3)]) == ["1500 at 0"]
    assert unsourced_numbers("1500", [(0, 4)]) == []


def test_text_with_no_number_in_it_needs_no_field():
    assert unsourced_numbers("Thanks for writing.", []) == []


def test_a_claim_written_in_words_carries_no_digits_and_renders():
    """Planted against the rule, which reads runs of digits and reads nothing else.

    A price written out in words is the same claim as a price in figures with the digits
    taken out, so no run is found and the text renders. A product name a template writes
    by hand is that family too, whether or not the catalog carries the name. This is the
    limit `docs/adr/0016` names under Consequences, and it is planted here so a reader
    meets it where the rule is.
    """
    only_seller = {"seller": seller(PICKED)}
    assert (
        render("It costs forty nine euros. {seller} will write back.", only_seller)
        == "It costs forty nine euros. Ada will write back."
    )
    assert (
        render("Onboarding review is what you want. {seller} will write back.", only_seller)
        == "Onboarding review is what you want. Ada will write back."
    )
    assert (
        render("The Hyperwidget Pro suits you. {seller} will write back.", only_seller)
        == "The Hyperwidget Pro suits you. Ada will write back."
    )


# The builders read their source and take no text from anybody.


def test_a_product_is_named_the_way_the_catalog_names_it():
    field = product("  Onboarding review  ", CATALOG)
    assert field == Field(name="product", text="Onboarding review", source=Source.CATALOG)


def test_a_price_is_the_number_the_catalog_carries():
    assert price("Data cleanup", CATALOG).text == "900.50"
    assert price("Onboarding review", CATALOG).text == "1500"
    assert price("Data cleanup", {"Data cleanup": 900.5}).text == "900.5"
    assert price("Data cleanup", {"Data cleanup": 4}).text == "4"


def test_a_quantity_counts_the_products_the_catalog_carries_once_each():
    assert quantity(NAMED, CATALOG).text == "2"
    assert quantity(["Data cleanup", "Data cleanup"], CATALOG).text == "1"


def test_a_seller_in_a_reply_is_the_one_the_match_picked():
    assert seller(PICKED) == Field(name="seller", text="Ada", source=Source.MATCHING)


def test_a_window_is_the_hours_the_playbook_writes_for_that_level():
    for level in Awareness:
        assert window(level).text == str(window_hours(level))
        assert window(level).source is Source.PLAYBOOK


@pytest.mark.parametrize("missing", ["Nothing we sell", "", "  ", None, 3])
def test_a_product_the_catalog_does_not_carry_has_no_field(missing):
    refusal = UnknownProduct if isinstance(missing, str) and missing.strip() else InvalidSource
    for build in (product, price):
        with pytest.raises(refusal):
            build(missing, CATALOG)
    with pytest.raises(refusal):
        quantity([missing], CATALOG)


@pytest.mark.parametrize("broken", [None, "Onboarding review", ["Onboarding review"], 3])
def test_a_catalog_that_is_not_a_catalog_builds_nothing(broken):
    for build in (product, price):
        with pytest.raises(InvalidSource):
            build("Onboarding review", broken)


@pytest.mark.parametrize("broken", [None, "Onboarding review", 3, {"Onboarding review": 1}, []])
def test_a_quantity_reads_a_sequence_of_names_and_nothing_else(broken):
    with pytest.raises(InvalidSource):
        quantity(broken, CATALOG)


@pytest.mark.parametrize("wrong", [None, "Ada", 3, ["Ada"]])
def test_a_seller_comes_from_the_match_and_not_from_a_name(wrong):
    with pytest.raises(InvalidSource):
        seller(wrong)


@pytest.mark.parametrize("price_written", [True, None, "1500", -1, Decimal("Infinity")])
def test_a_price_the_catalog_writes_badly_is_refused(price_written):
    with pytest.raises(InvalidSource):
        price("Data cleanup", {"Data cleanup": price_written})


# The template itself.


@pytest.mark.parametrize("broken", [None, 3, "", "   ", ["{seller}"]])
def test_a_template_is_text_with_something_in_it(broken):
    with pytest.raises(InvalidTemplate):
        named_fields(broken)
    with pytest.raises(InvalidTemplate):
        render(broken, {})


@pytest.mark.parametrize(
    "broken",
    ["{seller} wrote {", "} {seller}", "{seller} and {Product}", "{seller} and {}"],
)
def test_a_brace_that_names_no_field_is_refused(broken):
    with pytest.raises(InvalidTemplate):
        named_fields(broken)


def test_the_fields_of_a_template_are_read_in_the_order_they_are_written():
    assert named_fields("{seller} sells {product} at {price} to {seller}") == (
        "seller",
        "product",
        "price",
    )
    assert named_fields("Thanks for writing.") == ()


def test_a_template_with_no_field_renders_as_it_stands():
    assert render("Thanks for writing.", {}) == "Thanks for writing."


# What a field is, once it exists.


def test_a_field_does_not_change_afterwards():
    field = seller(PICKED)
    with pytest.raises(dataclasses.FrozenInstanceError):
        field.text = "somebody else"


def test_the_table_of_fields_names_the_three_sources_and_nothing_else():
    assert set(FIELDS.values()) == set(Source)
    assert len(Source) == 3


def test_the_same_fields_render_the_same_reply_every_time():
    template = TEMPLATES[Action.SEND_THE_COMPARISON]
    first = render(template, {**supplied(template), "window": window(Awareness.SOLUTION_AWARE)})
    second = render(template, {**supplied(template), "window": window(Awareness.SOLUTION_AWARE)})
    assert first == second


# A draft, which builds the fields its template names from the lead, the catalog and the match.


@pytest.mark.parametrize("level", list(Awareness))
def test_a_draft_is_the_reply_its_template_asks_for(level):
    template = TEMPLATES[PLAYBOOK[level].action]
    assert draft(level, NAMED, CATALOG, PICKED) == reply(level, supplied(template))


def test_a_draft_names_the_first_product_the_lead_named_and_counts_them_all():
    text = draft(Awareness.SOLUTION_AWARE, list(reversed(NAMED)), CATALOG, PICKED)
    assert "You asked about 2 of the things we carry" in text
    assert "with Data cleanup at 900.50 beside the rest" in text


def test_a_draft_for_a_product_written_twice_counts_it_once():
    text = draft(Awareness.SOLUTION_AWARE, [NAMED[0], NAMED[0]], CATALOG, PICKED)
    assert "You asked about 1 of the things we carry" in text


@pytest.mark.parametrize("wanted", [[], "Data cleanup", None, {"Data cleanup": 1}])
def test_a_draft_needs_a_sequence_with_a_product_in_it(wanted):
    with pytest.raises(InvalidSource):
        draft(Awareness.PRODUCT_AWARE, wanted, CATALOG, PICKED)


def test_a_draft_refuses_a_product_the_catalog_does_not_carry():
    with pytest.raises(UnknownProduct):
        draft(Awareness.PRODUCT_AWARE, ["Gold plating"], CATALOG, PICKED)
    with pytest.raises(UnknownProduct):
        draft(Awareness.SOLUTION_AWARE, [NAMED[0], "Gold plating"], CATALOG, PICKED)


def test_a_draft_refuses_a_seller_the_match_did_not_pick():
    with pytest.raises(InvalidSource):
        draft(Awareness.PRODUCT_AWARE, NAMED, CATALOG, "Ada")


def test_a_draft_refuses_a_sixth_level():
    with pytest.raises(UnknownAwareness):
        draft("very_aware", NAMED, CATALOG, PICKED)
