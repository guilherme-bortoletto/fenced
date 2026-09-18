"""A score over data, in three dimensions the model never produces.

Revenue comes from the catalog, recurrence from what the person bought before, and
margin from the margin table. Each dimension is a pure function of what is passed
in. Nothing here opens a file, reads a clock or asks a service, so the same inputs
always give the same score.

A dimension is a number between zero and one, and the three are combined with
written weights that add up to one, so a total is between zero and one as well.
What to do with a total is a decision for a person and not a rule written here.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

# The weight of each dimension in the total. Written down so a reader argues with
# the numbers instead of with the code.
WEIGHTS = {"revenue": 0.5, "recurrence": 0.2, "margin": 0.3}
# The basket that already scores the whole revenue dimension. Above it there is
# nothing left to win, which is what keeps one large product from deciding alone.
FULL_REVENUE = 5000.0
# The order at which a buyer counts as settled. The first order is not a habit.
RECURRENT_AT = 4
PLACES = 3


class ScoreError(ValueError):
    """Anything the domain refuses to score."""


class NothingToScore(ScoreError):
    """A lead that names no product at all."""


class UnknownProduct(ScoreError):
    """A product name that is not in the table it was looked up in."""


class InvalidTable(ScoreError):
    """A catalog, a margin table or a history that is not the shape it claims."""


class InvalidAmount(ScoreError):
    """A price or a margin the domain will not do arithmetic with."""


def _bounded(value: float) -> float:
    """A number held between zero and one, at three decimal places.

    Rounded so a test can pin it, and so two scores that differ only in float noise
    compare equal.
    """
    return round(min(max(value, 0.0), 1.0), PLACES)


def _named(wanted: object) -> list[str]:
    """The products a lead named, each one once, in the order they were named.

    A name written twice is one product named twice, so it counts once. A name that
    is not text is refused rather than turned into text.
    """
    if isinstance(wanted, str) or not isinstance(wanted, Sequence):
        raise InvalidTable(
            f"a lead names products in a sequence, not in a {type(wanted).__name__}"
        )
    names: list[str] = []
    for value in wanted:
        if not isinstance(value, str):
            raise UnknownProduct(f"a product is named in text, not in a {type(value).__name__}")
        name = value.strip()
        if not name:
            raise UnknownProduct("a product with no name is not a product")
        if name not in names:
            names.append(name)
    if not names:
        raise NothingToScore("a lead that names no product is handed back, not scored zero")
    return names


def _looked_up(name: str, table: object, what: str) -> object:
    """One row of a table, or a refusal naming the table it was missing from."""
    if not isinstance(table, Mapping):
        raise InvalidTable(f"the {what} maps a product to a number, not a {type(table).__name__}")
    if name not in table:
        raise UnknownProduct(f"{name!r} is not in the {what}")
    return table[name]


def _amount(value: object, what: str, ceiling: float | None = None) -> float:
    """One number out of a table. A bool is not a number here, and neither is text."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidAmount(f"{what} is a number, not a {type(value).__name__}")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise InvalidAmount(f"{what} is {value!r}, which is not an amount")
    if ceiling is not None and number > ceiling:
        raise InvalidAmount(f"{what} is {value!r}, which is above {ceiling}")
    return number


def revenue_score(wanted: object, catalog: object) -> float:
    """What the lead asked about, against the basket that scores full marks.

    The prices come from the catalog and from nowhere else, so a number the model
    read in a message moves nothing.
    """
    total = 0.0
    for name in _named(wanted):
        total += _amount(_looked_up(name, catalog, "catalog"), f"the price of {name!r}")
    return _bounded(total / FULL_REVENUE)


def recurrence_score(history: object) -> float:
    """How settled the buying is, counted from the orders past the first.

    An empty history scores zero, and so does a single order, because one order is
    not yet a habit. A past order naming a product the catalog no longer carries
    still counts, because it happened.
    """
    if isinstance(history, str) or not isinstance(history, Sequence):
        raise InvalidTable(f"a history is a sequence of past orders, not a {type(history).__name__}")
    for order in history:
        if not isinstance(order, str) or not order.strip():
            raise InvalidTable(f"a past order is written as text, and {order!r} is not")
    return _bounded(max(len(history) - 1, 0) / (RECURRENT_AT - 1))


def margin_score(wanted: object, margins: object) -> float:
    """The mean margin of what the lead asked about, as the margin table has it.

    A mean and not a mean weighted by price, because weighting by price would let
    the revenue dimension count a second time under another name.
    """
    names = _named(wanted)
    total = 0.0
    for name in names:
        total += _amount(
            _looked_up(name, margins, "margin table"), f"the margin of {name!r}", ceiling=1.0
        )
    return _bounded(total / len(names))


@dataclass(frozen=True)
class Score:
    """The three dimensions and the total they add up to.

    A total on its own says a lead is worth a number and not why. The parts stay
    next to it, so the person who reads it sees which dimension carried it.
    """

    revenue: float
    recurrence: float
    margin: float
    total: float


def score(wanted: object, catalog: object, history: object, margins: object) -> Score:
    """The three dimensions and their weighted total, from data and nothing else."""
    revenue = revenue_score(wanted, catalog)
    recurrence = recurrence_score(history)
    margin = margin_score(wanted, margins)
    total = (
        WEIGHTS["revenue"] * revenue
        + WEIGHTS["recurrence"] * recurrence
        + WEIGHTS["margin"] * margin
    )
    return Score(revenue=revenue, recurrence=recurrence, margin=margin, total=_bounded(total))
