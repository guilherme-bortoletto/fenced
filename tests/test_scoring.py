"""The three dimensions of a score, the total they add up to, and what is refused."""

from __future__ import annotations

import dataclasses

import pytest

from fenced.domain.scoring import (
    FULL_REVENUE,
    RECURRENT_AT,
    WEIGHTS,
    InvalidAmount,
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

CATALOG = {"report": 750.0, "rollout": 2500.0, "retainer": 5000.0}
MARGINS = {"report": 0.8, "rollout": 0.4, "retainer": 0.55}
NOT_A_NUMBER = [None, "2500", True, [], {}, object(), float("nan"), float("inf"), -1.0]
NOT_A_SEQUENCE = [None, 3, {"report": 1}, object()]


def test_the_weights_add_up_to_one():
    assert sorted(WEIGHTS) == ["margin", "recurrence", "revenue"]
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


# Revenue.


def test_revenue_is_what_was_asked_about_against_the_full_basket():
    assert revenue_score(["rollout"], CATALOG) == 0.5
    assert revenue_score(["report", "rollout"], CATALOG) == 0.65


def test_revenue_stops_at_one_instead_of_running_away():
    assert sum(CATALOG.values()) > FULL_REVENUE
    assert revenue_score(list(CATALOG), CATALOG) == 1.0


def test_a_product_named_twice_is_one_product():
    assert revenue_score(["rollout", "rollout", " rollout "], CATALOG) == 0.5
    assert margin_score(["rollout", "rollout"], MARGINS) == 0.4


def test_the_price_comes_from_the_catalog_and_nowhere_else():
    with pytest.raises(UnknownProduct):
        revenue_score(["a rollout of everything"], CATALOG)


@pytest.mark.parametrize("value", NOT_A_NUMBER)
def test_a_price_that_is_not_an_amount_is_refused(value):
    with pytest.raises(InvalidAmount):
        revenue_score(["report"], {"report": value})


# Recurrence.


def test_an_empty_history_scores_zero_and_so_does_a_single_order():
    assert recurrence_score([]) == 0.0
    assert recurrence_score(()) == 0.0
    assert recurrence_score(["report"]) == 0.0


def test_recurrence_counts_the_orders_past_the_first():
    assert recurrence_score(["report", "report"]) == 0.333
    assert recurrence_score(["report", "rollout", "report"]) == 0.667
    assert recurrence_score(["report"] * RECURRENT_AT) == 1.0
    assert recurrence_score(["report"] * (RECURRENT_AT + 5)) == 1.0


def test_a_past_order_of_something_no_longer_sold_still_counts():
    assert recurrence_score(["a product the catalog dropped", "report"]) == 0.333


@pytest.mark.parametrize("history", [*NOT_A_SEQUENCE, "report", ["report", 2], ["report", "  "]])
def test_a_history_that_is_not_a_list_of_written_orders_is_refused(history):
    with pytest.raises(InvalidTable):
        recurrence_score(history)


# Margin.


def test_margin_is_the_mean_of_what_the_table_says():
    assert margin_score(["report"], MARGINS) == 0.8
    assert margin_score(["report", "rollout"], MARGINS) == 0.6


@pytest.mark.parametrize("value", [*NOT_A_NUMBER, 1.5])
def test_a_margin_that_is_not_a_fraction_is_refused(value):
    with pytest.raises(InvalidAmount):
        margin_score(["report"], {"report": value})


def test_a_product_missing_from_the_margin_table_is_refused():
    with pytest.raises(UnknownProduct):
        margin_score(["retainer"], {"report": 0.8})


# The combination.


def test_the_total_is_the_three_dimensions_under_their_weights():
    result = score(["report", "rollout"], CATALOG, ["report", "report"], MARGINS)
    assert result == Score(revenue=0.65, recurrence=0.333, margin=0.6, total=0.572)
    by_hand = WEIGHTS["revenue"] * 0.65 + WEIGHTS["recurrence"] * 0.333 + WEIGHTS["margin"] * 0.6
    assert by_hand == pytest.approx(0.5716)
    assert result.total == round(by_hand, 3)


def test_the_best_lead_scores_one_and_a_first_time_buyer_loses_one_dimension():
    best = score(["retainer"], CATALOG, ["retainer"] * RECURRENT_AT, {"retainer": 1.0})
    assert best == Score(revenue=1.0, recurrence=1.0, margin=1.0, total=1.0)
    first_time = score(["retainer"], CATALOG, [], {"retainer": 1.0})
    assert first_time.recurrence == 0.0
    assert first_time.total == 1.0 - WEIGHTS["recurrence"]


def test_a_score_keeps_its_parts_and_does_not_change_afterwards():
    result = score(["report"], CATALOG, [], MARGINS)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.total = 1.0


def test_the_same_data_scores_the_same_and_the_data_is_left_alone():
    wanted = ["report", "rollout"]
    catalog = dict(CATALOG)
    history = ["report"]
    first = score(wanted, catalog, history, MARGINS)
    assert first == score(wanted, catalog, history, MARGINS)
    assert wanted == ["report", "rollout"]
    assert catalog == CATALOG
    assert history == ["report"]


# What is not scored at all.


@pytest.mark.parametrize("wanted", [[], (), [" "], ["report", ""]])
def test_a_lead_that_names_no_product_is_handed_back_rather_than_scored(wanted):
    with pytest.raises(ScoreError):
        score(wanted, CATALOG, [], MARGINS)


@pytest.mark.parametrize("wanted", [*NOT_A_SEQUENCE, "report"])
def test_a_list_of_products_that_is_not_a_list_is_refused(wanted):
    with pytest.raises(InvalidTable):
        revenue_score(wanted, CATALOG)


@pytest.mark.parametrize("table", NOT_A_SEQUENCE[:1] + [3, "report", ["report"]])
def test_a_catalog_that_is_not_a_table_is_refused(table):
    with pytest.raises(InvalidTable):
        revenue_score(["report"], table)


def test_every_refusal_is_one_family():
    for refusal in (NothingToScore, UnknownProduct, InvalidTable, InvalidAmount):
        assert issubclass(refusal, ScoreError)
    assert issubclass(ScoreError, ValueError)
