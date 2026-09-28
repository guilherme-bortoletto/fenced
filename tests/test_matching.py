"""Who takes a lead, the order that settles a tie, and everything that is refused."""

from __future__ import annotations

import dataclasses
import itertools
from decimal import ROUND_DOWN, Decimal, localcontext

import pytest

from fenced.domain.matching import (
    InvalidNeed,
    InvalidRoster,
    InvalidSeller,
    MatchError,
    Need,
    NobodyEligible,
    NobodyToMatch,
    Seller,
    eligible,
    match,
    order,
)

NOT_TEXT = [None, 0, True, 2.5, [], {}, object()]
NOT_A_NUMBER = [None, "2000", True, [], {}, object(), float("nan"), float("inf"), -1.0]
NOT_A_SEQUENCE = [None, 3, {"a": 1}, object()]
# Invented on purpose, in round numbers, so nobody reads them as a real roster.
RETAIL = Need(segment="retail", ticket=2000, language="pt")


def seller(
    name: str,
    segments: tuple[str, ...] = ("retail",),
    smallest: object = 0,
    largest: object = 10000,
    languages: tuple[str, ...] = ("pt",),
) -> Seller:
    """One seller, with everything the test does not care about already filled in."""
    return Seller(
        name=name,
        segments=frozenset(segments),
        smallest_ticket=smallest,
        largest_ticket=largest,
        languages=frozenset(languages),
    )


# The three hard rules.


def test_a_seller_who_covers_all_three_takes_the_lead():
    taken = seller("Ana", segments=("retail",), smallest=1000, largest=5000, languages=("pt",))
    assert match(RETAIL, [taken]) is taken


@pytest.mark.parametrize(
    "wrong",
    [
        seller("wrong segment", segments=("wholesale",)),
        seller("wrong language", languages=("es",)),
        seller("under the range", smallest=2001, largest=9000),
        seller("over the range", smallest=100, largest=1999),
    ],
)
def test_a_seller_who_fails_one_rule_is_out_and_not_ranked_lower(wrong):
    assert eligible(RETAIL, [wrong]) == []
    with pytest.raises(NobodyEligible):
        match(RETAIL, [wrong])


@pytest.mark.parametrize(("smallest", "largest"), [(2000, 9000), (100, 2000), (2000, 2000)])
def test_both_ends_of_a_ticket_range_are_inside_it(smallest, largest):
    edge = seller("edge", smallest=smallest, largest=largest)
    assert match(RETAIL, [edge]) is edge


@pytest.mark.parametrize("ticket", [2000, 2000.0, Decimal("2000"), Decimal("2000.00")])
def test_a_ticket_is_the_number_a_reader_sees_however_it_was_written(ticket):
    only = seller("only", smallest=2000, largest=2000)
    assert match(Need(segment="retail", ticket=ticket, language="pt"), [only]) is only


@pytest.mark.parametrize(
    ("segment", "language"),
    [("Retail", "PT"), ("  retail  ", "  pt  "), ("RETAIL", "Pt")],
)
def test_case_and_spacing_are_spelling_and_not_meaning(segment, language):
    written = seller("Ana", segments=("Retail",), languages=("PT",))
    assert match(Need(segment=segment, ticket=2000, language=language), [written]) is written


# The tie, and the written order that settles it.


def test_the_seller_who_covers_fewer_segments_comes_first():
    narrow = seller("Zoe", segments=("retail",))
    wide = seller("Ana", segments=("retail", "wholesale", "public"))
    assert match(RETAIL, [wide, narrow]) is narrow
    assert eligible(RETAIL, [wide, narrow]) == [narrow, wide]


def test_a_narrower_ticket_range_breaks_a_tie_on_segments():
    narrow = seller("Zoe", smallest=1500, largest=2500)
    wide = seller("Ana", smallest=0, largest=10000)
    assert match(RETAIL, [wide, narrow]) is narrow


def test_the_name_settles_what_the_first_two_questions_left():
    ana = seller("Ana", smallest=1000, largest=3000)
    zoe = seller("Zoe", smallest=1000, largest=3000)
    assert order(ana)[:2] == order(zoe)[:2]
    assert match(RETAIL, [zoe, ana]) is ana
    assert eligible(RETAIL, [zoe, ana]) == [ana, zoe]


def test_the_name_is_read_without_its_case_so_the_order_is_the_same_either_way():
    lower = seller("ana", smallest=1000, largest=3000)
    upper = seller("Bea", smallest=1000, largest=3000)
    assert eligible(RETAIL, [upper, lower]) == [lower, upper]


def test_the_same_roster_in_any_order_picks_the_same_seller():
    roster = [
        seller("Ana", segments=("retail", "wholesale"), smallest=0, largest=10000),
        seller("Bea", segments=("retail",), smallest=1000, largest=3000),
        seller("Zoe", segments=("retail",), smallest=1000, largest=3000),
        seller("Ivo", segments=("wholesale",)),
    ]
    picks = {match(RETAIL, list(shuffled)).name for shuffled in itertools.permutations(roster)}
    assert picks == {"Bea"}


def test_the_eligible_list_is_the_working_of_the_pick():
    first = seller("Bea", segments=("retail",), smallest=1000, largest=3000)
    second = seller("Ana", segments=("retail", "wholesale"))
    out = seller("Ivo", languages=("es",))
    ranked = eligible(RETAIL, [out, second, first])
    assert ranked == [first, second]
    assert match(RETAIL, [out, second, first]) is ranked[0]


def test_a_spread_is_exact_under_a_context_the_caller_narrowed():
    wide = seller("Ana", smallest=0, largest=10000)
    narrow = seller("Bea", smallest=Decimal("1999.995"), largest=Decimal("2000.005"))
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        assert narrow.spread == Decimal("0.010")
        assert match(RETAIL, [wide, narrow]) is narrow


def test_the_same_roster_matches_the_same_and_the_roster_is_left_alone():
    roster = [seller("Ana"), seller("Bea")]
    assert match(RETAIL, roster) is match(RETAIL, roster)
    assert [one.name for one in roster] == ["Ana", "Bea"]


def test_a_seller_does_not_change_afterwards():
    only = seller("Ana")
    with pytest.raises(dataclasses.FrozenInstanceError):
        only.name = "Bea"
    with pytest.raises(dataclasses.FrozenInstanceError):
        RETAIL.ticket = Decimal(1)


# Nobody to pick, and nobody who fits.


@pytest.mark.parametrize("empty", [[], ()])
def test_a_roster_with_nobody_in_it_is_handed_back_rather_than_matched(empty):
    with pytest.raises(NobodyToMatch):
        match(RETAIL, empty)
    with pytest.raises(NobodyToMatch):
        eligible(RETAIL, empty)


def test_a_roster_where_nobody_fits_is_a_different_refusal_from_an_empty_one():
    nobody = [seller("Ana", segments=("wholesale",)), seller("Bea", languages=("es",))]
    with pytest.raises(NobodyEligible):
        match(RETAIL, nobody)
    assert eligible(RETAIL, nobody) == []


# What is refused.


def test_one_name_twice_is_refused_rather_than_picked_between():
    with pytest.raises(InvalidRoster):
        match(RETAIL, [seller("Ana"), seller("Ana")])


def test_one_name_in_two_cases_is_still_one_name():
    with pytest.raises(InvalidRoster):
        match(RETAIL, [seller("Ana"), seller("ana")])


@pytest.mark.parametrize("roster", [*NOT_A_SEQUENCE, "Ana"])
def test_a_roster_that_is_not_a_sequence_of_sellers_is_refused(roster):
    with pytest.raises(InvalidRoster):
        match(RETAIL, roster)


@pytest.mark.parametrize("stranger", [None, "Ana", 3, {"name": "Ana"}])
def test_something_in_a_roster_that_is_not_a_seller_is_refused(stranger):
    with pytest.raises(InvalidRoster):
        match(RETAIL, [seller("Ana"), stranger])


@pytest.mark.parametrize("name", [*NOT_TEXT, "", "   "])
def test_a_seller_with_no_name_written_is_refused(name):
    with pytest.raises(InvalidSeller):
        seller(name)


@pytest.mark.parametrize("listed", [*NOT_A_SEQUENCE, "retail", (), frozenset()])
def test_a_seller_whose_segments_are_not_a_collection_of_names_is_refused(listed):
    with pytest.raises(InvalidSeller):
        Seller(
            name="Ana",
            segments=listed,
            smallest_ticket=0,
            largest_ticket=10,
            languages=frozenset({"pt"}),
        )


@pytest.mark.parametrize("listed", [*NOT_A_SEQUENCE, "pt", (), frozenset()])
def test_a_seller_who_speaks_nothing_named_is_refused(listed):
    with pytest.raises(InvalidSeller):
        Seller(
            name="Ana",
            segments=frozenset({"retail"}),
            smallest_ticket=0,
            largest_ticket=10,
            languages=listed,
        )


@pytest.mark.parametrize("amount", NOT_A_NUMBER)
def test_a_ticket_end_that_is_not_an_amount_is_refused(amount):
    with pytest.raises(InvalidSeller):
        seller("Ana", smallest=amount)
    with pytest.raises(InvalidSeller):
        seller("Ana", largest=amount)


def test_a_range_that_runs_backwards_is_no_range_at_all():
    with pytest.raises(InvalidSeller):
        seller("Ana", smallest=5000, largest=1000)


def test_a_ticket_too_large_for_a_float_is_an_ordinary_amount():
    huge = 2**1024
    wide = seller("Ana", smallest=0, largest=huge)
    assert match(Need(segment="retail", ticket=huge, language="pt"), [wide]) is wide


@pytest.mark.parametrize("segment", [*NOT_TEXT, "", "   "])
def test_a_need_with_no_segment_written_is_refused(segment):
    with pytest.raises(InvalidNeed):
        Need(segment=segment, ticket=2000, language="pt")


@pytest.mark.parametrize("language", [*NOT_TEXT, "", "   "])
def test_a_need_with_no_language_written_is_refused(language):
    with pytest.raises(InvalidNeed):
        Need(segment="retail", ticket=2000, language=language)


@pytest.mark.parametrize("ticket", NOT_A_NUMBER)
def test_a_need_whose_ticket_is_not_an_amount_is_refused(ticket):
    with pytest.raises(InvalidNeed):
        Need(segment="retail", ticket=ticket, language="pt")


@pytest.mark.parametrize("need", [None, "retail", 2000, {"segment": "retail"}])
def test_a_pick_is_made_on_a_need_and_not_on_something_shaped_like_one(need):
    with pytest.raises(InvalidNeed):
        match(need, [seller("Ana")])


def test_every_refusal_is_one_family():
    for refusal in (NobodyToMatch, NobodyEligible, InvalidRoster, InvalidSeller, InvalidNeed):
        assert issubclass(refusal, MatchError)
    assert issubclass(MatchError, ValueError)
