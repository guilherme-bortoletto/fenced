"""The three dimensions of a score, the total they add up to, and what is refused."""

from __future__ import annotations

import dataclasses
import itertools
from decimal import ROUND_DOWN, Decimal, localcontext

import pytest

from fenced.domain.scoring import (
    FULL_REVENUE,
    RECURRENT_AT,
    WEIGHTS,
    InvalidAmount,
    InvalidProducts,
    InvalidTable,
    NothingToScore,
    Score,
    ScoreError,
    UnknownProduct,
    margin_score,
    recurrence_score,
    revenue_score,
    score,
)

# Invented on purpose, in round numbers, so nobody reads them as a price list.
CATALOG = {"small": 1000.0, "medium": 2000.0, "large": 4000.0}
MARGINS = {"small": 0.5, "medium": 0.25, "large": 0.75}
NOT_A_NUMBER = [None, "2000", True, [], {}, object(), float("nan"), float("inf"), -1.0]
NOT_A_SEQUENCE = [None, 3, {"small": 1}, object()]
NOT_TEXT = [None, 0, True, 2.5, [], {}, object()]


def weighted(revenue: str, recurrence: str, margin: str) -> Decimal:
    """The total a reader works out from the three published parts, by hand."""
    return (
        WEIGHTS["revenue"] * Decimal(revenue)
        + WEIGHTS["recurrence"] * Decimal(recurrence)
        + WEIGHTS["margin"] * Decimal(margin)
    )


# The weights.


def test_each_weight_is_the_number_the_decision_record_argues_for():
    assert WEIGHTS == {
        "revenue": Decimal("0.5"),
        "recurrence": Decimal("0.2"),
        "margin": Decimal("0.3"),
    }
    assert sum(WEIGHTS.values()) == Decimal(1)


@pytest.mark.parametrize(
    ("dimension", "rising"),
    [
        ("revenue", [{"one": 0.0}, {"one": 1000.0}, {"one": 2500.0}, {"one": 5000.0}]),
        ("margin", [{"one": 0.0}, {"one": 0.25}, {"one": 0.6}, {"one": 1.0}]),
        ("recurrence", [[], ["one"], ["one"] * 2, ["one"] * RECURRENT_AT]),
    ],
)
def test_raising_one_dimension_never_lowers_the_total(dimension, rising):
    totals = []
    for step in rising:
        catalog = step if dimension == "revenue" else {"one": 1000.0}
        margins = step if dimension == "margin" else {"one": 0.5}
        history = step if dimension == "recurrence" else ["one", "one"]
        totals.append(score(["one"], catalog, history, margins).total)
    assert totals == sorted(totals)
    assert totals[0] < totals[-1]


# Revenue.


def test_revenue_is_what_was_asked_about_against_the_full_basket():
    assert revenue_score(["medium"], CATALOG) == Decimal("0.400")
    assert revenue_score(["small", "medium"], CATALOG) == Decimal("0.600")


def test_revenue_stops_at_one_instead_of_running_away():
    assert sum(CATALOG.values()) > FULL_REVENUE
    assert revenue_score(list(CATALOG), CATALOG) == Decimal("1.000")


def test_a_product_priced_at_the_ceiling_wins_the_dimension_on_its_own():
    # The ceiling caps a basket. What one product is worth is the catalog to decide.
    assert max(CATALOG.values()) < FULL_REVENUE
    assert revenue_score(["whole"], {"whole": FULL_REVENUE}) == Decimal("1.000")


def test_a_product_named_twice_is_one_product():
    assert revenue_score(["medium", "medium", " medium "], CATALOG) == Decimal("0.400")
    assert margin_score(["medium", "medium"], MARGINS) == Decimal("0.250")


def test_the_price_comes_from_the_catalog_and_nowhere_else():
    with pytest.raises(UnknownProduct):
        revenue_score(["a medium of everything"], CATALOG)


@pytest.mark.parametrize("value", NOT_A_NUMBER)
def test_a_price_that_is_not_an_amount_is_refused(value):
    with pytest.raises(InvalidAmount):
        revenue_score(["small"], {"small": value})


def test_a_price_no_float_can_hold_is_a_number_and_not_an_overflow():
    assert revenue_score(["small"], {"small": 10**309}) == Decimal("1.000")
    assert revenue_score(["small"], {"small": Decimal("1e400")}) == Decimal("1.000")
    with pytest.raises(InvalidAmount):
        revenue_score(["small"], {"small": 1e400})


# The arithmetic.


def test_the_order_the_products_were_named_in_does_not_move_the_score():
    catalog = {"a": 352.23, "b": 746.07, "c": 464.20}
    margins = {"a": 0.5, "b": 0.5, "c": 0.6}
    orders = [list(order) for order in itertools.permutations(catalog)]
    assert len({revenue_score(o, catalog) for o in orders}) == 1
    assert len({margin_score(o, margins) for o in orders}) == 1
    assert len({score(o, catalog, ["a"], margins).total for o in orders}) == 1


def test_a_tie_falls_the_same_way_every_time_and_it_falls_up():
    assert revenue_score(["half"], {"half": 2.5}) == Decimal("0.001")
    assert revenue_score(["half"], {"half": 12.5}) == Decimal("0.003")
    assert margin_score(["half"], {"half": Decimal("0.0625")}) == Decimal("0.063")


def test_the_decimal_context_of_the_caller_changes_nothing():
    plain = score(["small", "medium"], CATALOG, ["small", "small"], MARGINS)
    with localcontext() as ctx:
        ctx.prec = 3
        ctx.rounding = ROUND_DOWN
        assert score(["small", "medium"], CATALOG, ["small", "small"], MARGINS) == plain


def test_a_price_written_as_a_decimal_is_read_as_the_number_it_says():
    assert revenue_score(["small"], {"small": Decimal("1000")}) == Decimal("0.200")
    assert revenue_score(["small"], {"small": 1000}) == Decimal("0.200")


# Recurrence.


def test_an_empty_history_scores_zero_and_so_does_a_single_order():
    assert recurrence_score([]) == Decimal("0.000")
    assert recurrence_score(()) == Decimal("0.000")
    assert recurrence_score(["small"]) == Decimal("0.000")


def test_recurrence_counts_the_orders_past_the_first():
    assert recurrence_score(["small", "small"]) == Decimal("0.333")
    assert recurrence_score(["small", "medium", "small"]) == Decimal("0.667")
    assert recurrence_score(["small"] * RECURRENT_AT) == Decimal("1.000")
    assert recurrence_score(["small"] * (RECURRENT_AT + 5)) == Decimal("1.000")


def test_a_past_order_of_something_no_longer_sold_still_counts():
    assert recurrence_score(["a product the catalog dropped", "small"]) == Decimal("0.333")


@pytest.mark.parametrize("history", [*NOT_A_SEQUENCE, "small"])
def test_a_history_that_is_not_a_sequence_is_refused(history):
    with pytest.raises(InvalidTable):
        recurrence_score(history)


@pytest.mark.parametrize("order", [*NOT_TEXT, "", "   "])
def test_a_past_order_that_is_not_written_text_is_refused(order):
    with pytest.raises(InvalidTable):
        recurrence_score(["small", order])


# Margin.


def test_margin_is_the_mean_of_what_the_table_says():
    assert margin_score(["small"], MARGINS) == Decimal("0.500")
    assert margin_score(["small", "medium"], MARGINS) == Decimal("0.375")


@pytest.mark.parametrize("value", [*NOT_A_NUMBER, 1.5])
def test_a_margin_that_is_not_a_fraction_is_refused(value):
    with pytest.raises(InvalidAmount):
        margin_score(["small"], {"small": value})


def test_a_product_missing_from_the_margin_table_is_refused():
    with pytest.raises(UnknownProduct):
        margin_score(["large"], {"small": 0.5})


# The combination.


def test_the_total_is_the_three_dimensions_under_their_weights():
    result = score(["small", "medium"], CATALOG, ["small", "small"], MARGINS)
    assert result == Score(
        revenue=Decimal("0.600"),
        recurrence=Decimal("0.333"),
        margin=Decimal("0.375"),
        total=Decimal("0.4791"),
    )


@pytest.mark.parametrize(
    ("wanted", "history"),
    [
        (["small"], []),
        (["small", "medium"], ["small", "small"]),
        (["large"], ["a", "b", "c"]),
        (["small", "medium", "large"], ["a"] * RECURRENT_AT),
    ],
)
def test_the_published_parts_add_up_to_the_published_total(wanted, history):
    result = score(wanted, CATALOG, history, MARGINS)
    assert result.total == weighted(result.revenue, result.recurrence, result.margin)


def test_the_best_lead_scores_one_and_a_first_time_buyer_loses_one_dimension():
    whole = {"medium": 2000.0, "large": 4000.0}
    best = score(["medium", "large"], whole, ["large"] * RECURRENT_AT, {"medium": 1.0, "large": 1.0})
    assert best == Score(
        revenue=Decimal("1.000"),
        recurrence=Decimal("1.000"),
        margin=Decimal("1.000"),
        total=Decimal("1.0000"),
    )
    first_time = score(["medium", "large"], whole, [], {"medium": 1.0, "large": 1.0})
    assert first_time.recurrence == Decimal("0.000")
    assert first_time.total == Decimal(1) - WEIGHTS["recurrence"]


def test_a_score_keeps_its_parts_and_does_not_change_afterwards():
    result = score(["small"], CATALOG, [], MARGINS)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.total = Decimal(1)


def test_the_same_data_scores_the_same_and_the_data_is_left_alone():
    wanted = ["small", "medium"]
    catalog = dict(CATALOG)
    history = ["small"]
    first = score(wanted, catalog, history, MARGINS)
    assert first == score(wanted, catalog, history, MARGINS)
    assert wanted == ["small", "medium"]
    assert catalog == CATALOG
    assert history == ["small"]


# What is not scored at all.


@pytest.mark.parametrize("wanted", [[], ()])
def test_a_lead_that_names_no_product_is_handed_back_rather_than_scored(wanted):
    with pytest.raises(NothingToScore):
        score(wanted, CATALOG, [], MARGINS)
    with pytest.raises(NothingToScore):
        revenue_score(wanted, CATALOG)
    with pytest.raises(NothingToScore):
        margin_score(wanted, MARGINS)


@pytest.mark.parametrize("name", [*NOT_TEXT, "", "   "])
def test_a_product_name_that_is_not_written_text_is_refused(name):
    with pytest.raises(InvalidProducts):
        revenue_score(["small", name], CATALOG)
    with pytest.raises(InvalidProducts):
        margin_score(["small", name], MARGINS)


@pytest.mark.parametrize("wanted", [*NOT_A_SEQUENCE, "small"])
def test_a_list_of_products_that_is_not_a_list_is_refused(wanted):
    with pytest.raises(InvalidProducts):
        revenue_score(wanted, CATALOG)


@pytest.mark.parametrize("table", [None, 3, "small", ["small"]])
def test_a_catalog_that_is_not_a_table_is_refused(table):
    with pytest.raises(InvalidTable):
        revenue_score(["small"], table)
    with pytest.raises(InvalidTable):
        margin_score(["small"], table)


def test_every_refusal_is_one_family():
    for refusal in (NothingToScore, InvalidProducts, UnknownProduct, InvalidTable, InvalidAmount):
        assert issubclass(refusal, ScoreError)
    assert issubclass(ScoreError, ValueError)
