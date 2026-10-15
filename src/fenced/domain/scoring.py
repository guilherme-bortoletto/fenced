"""A score over data, in three dimensions the model never produces.

Revenue comes from the catalog, recurrence from what the person bought before, and
margin from the margin table. Each dimension is a pure function of what is passed
in. Nothing here opens a file, reads a clock or asks a service.

The arithmetic is decimal and not binary, for three reasons. A price is read as the
number a reader sees. Addition is exact, so the order the products were named in
cannot move a score. The tie rule is written down as half going up, instead of being
left to the rounding of the language, and it runs in a context of this module so a
caller cannot change it from outside.

A dimension is a number between zero and one at three places. The total is the
weighted sum of those three published numbers and is not rounded a second time, so
a reader who adds the parts up gets the total that was published.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Context, Decimal, localcontext

# The weight of each dimension in the total. Written down so a reader argues with
# the numbers instead of with the code, and pinned one by one in the tests.
WEIGHTS = {
    "revenue": Decimal("0.5"),
    "recurrence": Decimal("0.2"),
    "margin": Decimal("0.3"),
}
# The basket that already wins the revenue dimension. A basket worth more scores the
# same as this one, so a large order cannot run away with the total. It does not stop
# a single product from winning the dimension alone, and a catalog that prices one
# product at or above this number has decided exactly that.
FULL_REVENUE = Decimal("5000")
# The order at which a buyer counts as settled. The first order is not a habit.
RECURRENT_AT = 4
PLACES = Decimal("0.001")
ZERO = Decimal(0)
ONE = Decimal(1)
# The arithmetic runs in a context of its own. A caller who has changed the decimal
# context of the process changes nothing here, which is what makes a score the same
# number on any machine.
CONTEXT = Context(prec=28, rounding=ROUND_HALF_UP)


class ScoreError(ValueError):
    """Anything the domain refuses to score."""


class NothingToScore(ScoreError):
    """A list of products with no product in it, so there is nothing to score."""


class InvalidProducts(ScoreError):
    """What a lead named, when it is not a sequence of written product names."""


class UnknownProduct(ScoreError):
    """A product name that is not in the table it was looked up in."""


class InvalidTable(ScoreError):
    """A catalog, a margin table or a history that is not the shape it claims."""


class InvalidAmount(ScoreError):
    """A price or a margin the domain will not do arithmetic with."""


def _bounded(value: Decimal) -> Decimal:
    """A number held between zero and one, at three places, a tie going up.

    The tie rule is written here rather than left to the rounding of the language,
    because a score that lands on a half has to fall the same way every time.
    """
    return min(max(value, ZERO), ONE).quantize(PLACES, rounding=ROUND_HALF_UP)


def _named(wanted: object) -> list[str]:
    """The products a lead named, each one once, in the order they were named.

    A name written twice is one product named twice, so it counts once. The order is
    kept for the reader and not for the arithmetic, which is exact in any order.
    """
    if isinstance(wanted, str) or not isinstance(wanted, Sequence):
        raise InvalidProducts(
            f"a lead names products in a sequence, not in a {type(wanted).__name__}"
        )
    names: list[str] = []
    for value in wanted:
        if not isinstance(value, str):
            raise InvalidProducts(f"a product is named in text, not in a {type(value).__name__}")
        name = value.strip()
        if not name:
            raise InvalidProducts("a product with no name is not a product")
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


def _amount(value: object, what: str, ceiling: Decimal | None = None) -> Decimal:
    """One number out of a table, as a decimal. A bool is not a number here.

    A float is read through the text it prints as, so the price a reader sees is the
    price that is added up. An integer too large to be a float is a number like any
    other, and it leaves here as one rather than as an `OverflowError`.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise InvalidAmount(f"{what} is a number, not a {type(value).__name__}")
    number = Decimal(str(value)) if isinstance(value, float) else Decimal(value)
    if not number.is_finite() or number < ZERO:
        raise InvalidAmount(f"{what} is {value!r}, which is not an amount")
    if ceiling is not None and number > ceiling:
        raise InvalidAmount(f"{what} is {value!r}, which is above {ceiling}")
    return number


def ticket(wanted: object, catalog: object) -> Decimal:
    """What the catalog prices the products the lead asked about at, added up exactly.

    This is the ticket matching reads, and the number the revenue dimension divides.
    The prices come from the catalog and from nowhere else, so a number the model
    read in a message moves nothing.
    """
    names = _named(wanted)
    with localcontext(CONTEXT):
        total = ZERO
        for name in names:
            total += _amount(_looked_up(name, catalog, "catalog"), f"the price of {name!r}")
        return total


def revenue_score(wanted: object, catalog: object) -> Decimal:
    """The ticket, against the basket that already wins the dimension."""
    basket = ticket(wanted, catalog)
    with localcontext(CONTEXT):
        return _bounded(basket / FULL_REVENUE)


def recurrence_score(history: object) -> Decimal:
    """How settled the buying is, counted from the orders past the first.

    An empty history scores zero, and so does a single order, because one order is
    not yet a habit. A past order naming a product the catalog no longer carries
    still counts, because it happened.
    """
    if isinstance(history, str) or not isinstance(history, Sequence):
        raise InvalidTable(
            f"a history is a sequence of past orders, not a {type(history).__name__}"
        )
    for order in history:
        if not isinstance(order, str) or not order.strip():
            raise InvalidTable(f"a past order is written as text, and {order!r} is not")
    with localcontext(CONTEXT):
        return _bounded(Decimal(max(len(history) - 1, 0)) / Decimal(RECURRENT_AT - 1))


def margin_score(wanted: object, margins: object) -> Decimal:
    """The mean margin of what the lead asked about, as the margin table has it.

    A mean and not a mean weighted by price, because weighting by price would let
    the revenue dimension count a second time under another name.
    """
    names = _named(wanted)
    with localcontext(CONTEXT):
        total = ZERO
        for name in names:
            total += _amount(
                _looked_up(name, margins, "margin table"), f"the margin of {name!r}", ceiling=ONE
            )
        return _bounded(total / Decimal(len(names)))


@dataclass(frozen=True)
class Score:
    """The three dimensions and the total they add up to.

    The total is the weighted sum of the three numbers next to it, exactly, with no
    rounding of its own. A reader who multiplies the parts by the weights and adds
    them gets this total and not a number near it.

    A total on its own says a lead is worth a number and not why. The parts stay
    here, so the person who reads it sees which dimension carried it.
    """

    revenue: Decimal
    recurrence: Decimal
    margin: Decimal
    total: Decimal


def score(wanted: object, catalog: object, history: object, margins: object) -> Score:
    """The three dimensions and their weighted total, from data and nothing else."""
    revenue = revenue_score(wanted, catalog)
    recurrence = recurrence_score(history)
    margin = margin_score(wanted, margins)
    with localcontext(CONTEXT):
        total = (
            WEIGHTS["revenue"] * revenue
            + WEIGHTS["recurrence"] * recurrence
            + WEIGHTS["margin"] * margin
        )
    return Score(revenue=revenue, recurrence=recurrence, margin=margin, total=total)
