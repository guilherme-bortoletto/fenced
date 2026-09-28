"""Who takes the lead, by a written rule and never by a judgement.

Three things decide whether a seller can take a lead. The segment the lead belongs
to has to be one the seller covers. The ticket has to sit inside the range the
seller works in, both ends included. The language the person wrote in has to be one
the seller speaks. All three are hard rules, and a seller who fails any of them is
not ranked lower, they are out.

Eligibility usually leaves more than one seller, and a pick that follows the order a
roster happened to arrive in is a pick no test can hold. So the eligible sellers are
put in an order written down here. The shortest segment list first, which puts a
seller who covers one segment ahead of a seller who covers six. Then the narrowest
ticket range, for the same reason. Then the name, which settles what is left, and
which is why a roster cannot carry one name twice.

That order is total, so the answer is the same for the same sellers in any order, and
the same on any machine. Nothing here opens a file, reads a clock or asks a service.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Context, Decimal, localcontext

ZERO = Decimal(0)
# The arithmetic runs in a context of this module, so a caller who has narrowed the
# decimal context of the process cannot turn two ticket ranges into one width.
CONTEXT = Context(prec=28, rounding=ROUND_HALF_UP)


class MatchError(ValueError):
    """Anything the domain refuses to match on."""


class NobodyToMatch(MatchError):
    """A roster with no seller in it, so there is nobody to pick."""


class NobodyEligible(MatchError):
    """A roster where no seller covers what the lead needs."""


class InvalidRoster(MatchError):
    """A roster that is not a sequence of sellers, or one that carries a name twice."""


class InvalidSeller(MatchError):
    """A seller whose own fields are not the shape they claim to be."""


class InvalidNeed(MatchError):
    """A segment, a ticket or a language the domain will not match on."""


def _text(value: object, field: str, refusal: type[MatchError]) -> str:
    """One field as text and trimmed, or a refusal. Nothing is coerced here.

    A null or a number is not a name, and turning either one into the text it prints
    as would hide from the pick what the caller failed to supply.
    """
    if not isinstance(value, str):
        raise refusal(f"a {field} is written in text, not in a {type(value).__name__}")
    trimmed = value.strip()
    if not trimmed:
        raise refusal(f"a {field} with nothing in it is not a {field}")
    return trimmed


def _folded(value: object, field: str, refusal: type[MatchError]) -> str:
    """One field as text, trimmed and folded, because case is spelling and not meaning.

    A segment written `Retail` and a segment written `retail` are one segment. A name
    keeps the case it was written in, and is folded only where it is compared.
    """
    return _text(value, field, refusal).casefold()


def _amount(value: object, what: str, refusal: type[MatchError]) -> Decimal:
    """One ticket amount as a decimal. A bool is not an amount here.

    A float is read through the text it prints as, so the number a reader sees is the
    number the range is checked against. An integer too large to be a float is an
    ordinary amount and leaves here as one.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise refusal(f"{what} is a number, not a {type(value).__name__}")
    number = Decimal(str(value)) if isinstance(value, float) else Decimal(value)
    if not number.is_finite() or number < ZERO:
        raise refusal(f"{what} is {value!r}, which is not an amount")
    return number


def _folded_set(value: object, plural: str, single: str) -> frozenset[str]:
    """The segments or the languages of one seller, folded, each one once.

    A bare string is refused rather than read letter by letter, because a seller who
    covers `retail` is not a seller who covers `r`, `e`, `t` and so on. A mapping is
    refused for the other half of the same reason. Reading it would keep the keys and
    drop whatever the caller wrote next to them, which is the part they meant.
    """
    if isinstance(value, (str, Mapping)) or not isinstance(value, Iterable):
        raise InvalidSeller(
            f"a seller lists {plural} in a collection, not in a {type(value).__name__}"
        )
    folded = frozenset(_folded(item, single, InvalidSeller) for item in value)
    if not folded:
        raise InvalidSeller(f"a seller who lists no {plural} takes no lead")
    return folded


@dataclass(frozen=True)
class Need:
    """What a lead needs, as the three things the pick is made on.

    The three arrive from elsewhere. The segment and the language are read off the
    lead, and the ticket is what the catalog prices what the person asked about at.
    None of them is decided here.
    """

    segment: str
    ticket: Decimal
    language: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "segment", _folded(self.segment, "segment", InvalidNeed))
        object.__setattr__(self, "language", _folded(self.language, "language", InvalidNeed))
        object.__setattr__(self, "ticket", _amount(self.ticket, "a ticket", InvalidNeed))


@dataclass(frozen=True)
class Seller:
    """One seller, and the three things that say which leads they can take.

    The constructor is the boundary. Whatever route a roster is built by, the same
    refusals and the same folding happen here, so there is one rule and not two.
    """

    name: str
    segments: frozenset[str]
    smallest_ticket: Decimal
    largest_ticket: Decimal
    languages: frozenset[str]

    def __post_init__(self) -> None:
        name = _text(self.name, "name", InvalidSeller)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "segments", _folded_set(self.segments, "segments", "segment"))
        object.__setattr__(self, "languages", _folded_set(self.languages, "languages", "language"))
        for field, written in (("smallest_ticket", "smallest"), ("largest_ticket", "largest")):
            amount = _amount(
                getattr(self, field), f"the {written} ticket of {name!r}", InvalidSeller
            )
            object.__setattr__(self, field, amount)
        if self.smallest_ticket > self.largest_ticket:
            raise InvalidSeller(
                f"{self.name!r} works from {self.smallest_ticket} up to {self.largest_ticket}, "
                "which is no range at all"
            )

    def covers(self, need: Need) -> bool:
        """Whether this seller can take that lead, by the three hard rules and nothing else."""
        return (
            need.segment in self.segments
            and need.language in self.languages
            and self.smallest_ticket <= need.ticket <= self.largest_ticket
        )

    @property
    def spread(self) -> Decimal:
        """How wide the ticket range is. A narrower range is a more particular seller."""
        with localcontext(CONTEXT):
            return self.largest_ticket - self.smallest_ticket


def _roster(sellers: object) -> list[Seller]:
    """Every seller of a roster, refusing a roster that is not one.

    A name twice is refused rather than picked between, because the name is the last
    step of the order and a step that cannot settle a tie is not an order.
    """
    if isinstance(sellers, str) or not isinstance(sellers, Sequence):
        raise InvalidRoster(f"a roster is a sequence of sellers, not a {type(sellers).__name__}")
    if not sellers:
        raise NobodyToMatch("a roster with nobody in it is handed back, not matched")
    seen: dict[str, str] = {}
    for seller in sellers:
        if not isinstance(seller, Seller):
            raise InvalidRoster(
                f"a roster carries sellers, and a {type(seller).__name__} is not one"
            )
        folded = seller.name.casefold()
        if folded in seen:
            raise InvalidRoster(
                f"{seller.name!r} and {seen[folded]!r} are one name, so no rule can tell them apart"
            )
        seen[folded] = seller.name
    return list(sellers)


def order(seller: Seller) -> tuple[int, Decimal, str]:
    """Where a seller sits in the written order, as the key that puts them there.

    Read it as three questions asked in turn. How many segments does this seller
    cover, how wide is their ticket range, and what is their name. The first answer
    that differs decides, and the third one always differs.
    """
    return (len(seller.segments), seller.spread, seller.name.casefold())


def eligible(need: object, sellers: object) -> list[Seller]:
    """Every seller who can take that lead, in the written order.

    The list is the working of the pick. A person who asks why a lead went one way
    reads this and sees who else could have taken it and why they came second.
    """
    if not isinstance(need, Need):
        raise InvalidNeed(f"a pick is made on a Need, not on a {type(need).__name__}")
    return sorted((seller for seller in _roster(sellers) if seller.covers(need)), key=order)


def match(need: object, sellers: object) -> Seller:
    """The one seller who takes the lead, or a refusal saying which way it failed.

    An empty roster and a roster where nobody is eligible are two different problems,
    so they are two refusals. Read as one they both look like nobody is free, and the
    person deciding has to tell a hiring problem from a routing problem.
    """
    ranked = eligible(need, sellers)
    if not ranked:
        raise NobodyEligible(
            f"no seller covers {need.segment!r} at {need.ticket} in {need.language!r}"
        )
    return ranked[0]
