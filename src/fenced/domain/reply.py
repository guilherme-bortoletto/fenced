"""The reply, as a template and the typed fields that fill it.

The model never writes this text. It fills the fields of a lead, and the boundary in
`lead.py` decides whether those fields are a lead at all. Nothing it returned reaches a
reply. A reply is a template written down here, filled by fields that only the catalog,
the matching or the playbook can build.

A field carries a name, the text it renders as, and the source that built it. The name
says which of the three sources is allowed to build it, so a field that claims another
source is refused, and a name no source can build does not exist. A template that names a
field nothing supplied is refused as well, rather than rendered with a hole in it.

The last rule is about numbers. Every run of digits in the rendered text has to sit inside
the text a field produced. A price, a window and a count of products are numbers a source
answers for. A number written into the template is a number nobody answers for, and it is
refused. The check reads runs of digits and asks where each one came from, so a date and a
quantity need no rule of their own. They pass because they came from a field and not
because of the shape they are written in.

Everything here is a pure function of what is passed in. Nothing opens a file, reads a
clock or asks a service.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from fenced.domain.matching import Seller
from fenced.domain.playbook import Action, next_step, window_hours

ZERO = Decimal(0)
# A field in a template, written as its name between braces. Nothing else is a field, so a
# brace left over anywhere is a template that meant something the render cannot read.
PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")
# One run of digits. The check reads runs and not shapes, which is the whole of the rule.
DIGITS = re.compile(r"\d+")


class Source(Enum):
    """The three places a value in a reply can come from, closed the way awareness is.

    The model is not one of them. Neither is the person who wrote, whose own words are a
    lead and not a sentence this repository sends back out under its own name.
    """

    CATALOG = "catalog"
    MATCHING = "matching"
    PLAYBOOK = "playbook"


# Every field a reply has, and the one source that is allowed to build it. A reader argues
# with this table rather than with the code, and a test reads it back against the builders.
FIELDS: Mapping[str, Source] = {
    "product": Source.CATALOG,
    "price": Source.CATALOG,
    "quantity": Source.CATALOG,
    "seller": Source.MATCHING,
    "window": Source.PLAYBOOK,
}


class ReplyError(ValueError):
    """Anything the domain refuses to render."""


class InvalidTemplate(ReplyError):
    """A template that is not text, or one whose braces name no field."""


class UnknownField(ReplyError):
    """A name that is not a field a reply has, so no source could have built it."""


class MissingField(ReplyError):
    """A field the template names and nothing supplied."""


class UnusedField(ReplyError):
    """A field supplied that the template has no place for."""


class InvalidField(ReplyError):
    """A field whose own name, text or source is not what it claims to be."""


class InvalidSource(ReplyError):
    """A catalog, a list of product names or a seller that is not what a builder reads."""


class UnknownProduct(ReplyError):
    """A product name the catalog does not carry, so it has no price and no spelling."""


class UnsourcedNumber(ReplyError):
    """A number in the rendered text that came from no field, so nobody answers for it."""


def _amount(value: object, what: str) -> Decimal:
    """One number out of the catalog, as a decimal. A bool is not a number here.

    A float is read through the text it prints as, so the price a reader sees is the price
    the reply carries. An integer too large to be a float is an ordinary price and leaves
    here as one.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise InvalidSource(f"{what} is a number, not a {type(value).__name__}")
    number = Decimal(str(value)) if isinstance(value, float) else Decimal(value)
    if not number.is_finite() or number < ZERO:
        raise InvalidSource(f"{what} is {value!r}, which is not an amount")
    return number


def _row(name: object, catalog: object) -> tuple[str, Decimal]:
    """One row of the catalog, as the name it is written under and the price it carries.

    The name is read back out of the catalog rather than taken from the caller, so what a
    reply calls a product is what the catalog calls it.
    """
    if not isinstance(catalog, Mapping):
        raise InvalidSource(
            f"a catalog maps a product to a price, not a {type(catalog).__name__}"
        )
    if not isinstance(name, str) or not name.strip():
        raise InvalidSource(f"a product is named in text, and {name!r} is not a name")
    wanted = name.strip()
    for written in catalog:
        if written == wanted:
            return written, _amount(catalog[written], f"the price of {written!r}")
    raise UnknownProduct(f"{wanted!r} is not in the catalog")


@dataclass(frozen=True)
class Field:
    """One value of a reply, and the source that produced the text of it.

    The constructor is the boundary. A field it cannot type does not exist, so a name the
    table does not carry is refused here, and so is a field that names a source other than
    the one allowed to build it. Whatever route a field is built by, the same refusals
    happen in this one place.
    """

    name: str
    text: str
    source: Source

    def __post_init__(self) -> None:
        known = ", ".join(sorted(FIELDS))
        if not isinstance(self.name, str) or self.name not in FIELDS:
            raise UnknownField(f"{self.name!r} is not a field of a reply, which has {known}")
        if not isinstance(self.text, str) or not self.text.strip():
            raise InvalidField(
                f"a {self.name} renders as text with something in it, and {self.text!r} does not"
            )
        allowed = FIELDS[self.name]
        if self.source is not allowed:
            raise InvalidField(
                f"a {self.name} comes from the {allowed.value} and from nowhere else, "
                f"so {self.source!r} did not produce one"
            )


def product(name: object, catalog: object) -> Field:
    """The product a reply names, which is in the text because the catalog carries it."""
    written, _ = _row(name, catalog)
    return Field(name="product", text=written, source=Source.CATALOG)


def price(name: object, catalog: object) -> Field:
    """What the catalog prices that product at. A number read in a message moves nothing."""
    _, amount = _row(name, catalog)
    return Field(name="price", text=str(amount), source=Source.CATALOG)


def quantity(wanted: object, catalog: object) -> Field:
    """How many of the products a lead named the catalog carries, each name counted once.

    A name written twice is one product named twice. A name the catalog does not carry is
    refused rather than left out of the count, because a reply that quietly counts fewer
    products than the person asked about is a reply about something else.
    """
    if isinstance(wanted, str) or not isinstance(wanted, Sequence):
        raise InvalidSource(
            f"a lead names products in a sequence, not in a {type(wanted).__name__}"
        )
    names: list[str] = []
    for value in wanted:
        written, _ = _row(value, catalog)
        if written not in names:
            names.append(written)
    if not names:
        raise InvalidSource("a lead that names no product has no quantity to render")
    return Field(name="quantity", text=str(len(names)), source=Source.CATALOG)


def seller(picked: object) -> Field:
    """The name of the seller the match picked. A reply names nobody the match did not."""
    if not isinstance(picked, Seller):
        raise InvalidSource(
            f"a seller comes from the match, and a {type(picked).__name__} is not one"
        )
    return Field(name="seller", text=picked.name, source=Source.MATCHING)


def window(awareness: object) -> Field:
    """How long the window is in hours, as the playbook writes it for that level.

    The level is parsed by the playbook, which parses it the way the boundary does, so a
    sixth level raises `UnknownAwareness` here and never reaches a reply.
    """
    return Field(name="window", text=str(window_hours(awareness)), source=Source.PLAYBOOK)


# One template for each action the playbook can name. Every one of them names the window,
# so a reply always says when the person hears back. None of them writes a number of its
# own, which a test reads back, because a number in the template is a promise no source
# made.
TEMPLATES: Mapping[Action, str] = {
    Action.NAME_THE_PROBLEM: (
        "Thanks for writing. What you described is the problem {product} is for. "
        "{seller} will write back within {window} hours with what it does "
        "and what it does not do."
    ),
    Action.ASK_WHAT_WAS_TRIED: (
        "Thanks for writing. Before we talk about {product}, {seller} will ask what you "
        "have already tried, and will write back within {window} hours."
    ),
    Action.SEND_THE_COMPARISON: (
        "Thanks for writing. You asked about {quantity} of the things we carry. {seller} "
        "will send a comparison within {window} hours, with {product} at {price} "
        "beside the rest."
    ),
    Action.OFFER_A_CALL: (
        "Thanks for writing. {product} is {price}. {seller} will offer you a call "
        "within {window} hours."
    ),
    Action.HAND_TO_A_PERSON: (
        "Thanks for writing. {product} is {price}, and {seller} has your message already. "
        "You will hear from a person within {window} hours."
    ),
}


def _parts(template: object) -> list[tuple[str, str | None]]:
    """A template as the literal text it is made of and the field that follows each piece.

    The last piece is followed by no field. A brace left in a literal piece names nothing,
    so it is refused rather than printed, because a template nobody can read is a template
    whose reply nobody checked.
    """
    if not isinstance(template, str):
        raise InvalidTemplate(f"a template is written in text, not in a {type(template).__name__}")
    if not template.strip():
        raise InvalidTemplate("a template with nothing in it renders no reply")
    parts: list[tuple[str, str | None]] = []
    at = 0
    for found in PLACEHOLDER.finditer(template):
        parts.append((template[at : found.start()], found.group(1)))
        at = found.end()
    parts.append((template[at:], None))
    for literal, _ in parts:
        if "{" in literal or "}" in literal:
            raise InvalidTemplate(f"{literal!r} carries a brace that names no field")
    return parts


def named_fields(template: object) -> tuple[str, ...]:
    """Every field a template names, each one once, in the order it is written.

    A caller reads this to know which fields to build. It says what the template asks for
    and not whether a source can answer, which is what the render decides.
    """
    names: list[str] = []
    for _, name in _parts(template):
        if name is not None and name not in names:
            names.append(name)
    return tuple(names)


def unsourced_numbers(text: str, spans: Sequence[tuple[int, int]]) -> list[str]:
    """Every run of digits in the text that no field put there, as the run and where it is.

    A field answers for the digits inside the text it produced, wherever they sit in it and
    whatever they are written between. So a date and a quantity pass, because they came
    from a field, and not because either one has a rule here. A run that no field covers
    came from the template, and nobody answers for it.
    """
    found = []
    for run in DIGITS.finditer(text):
        covered = any(start <= run.start() and run.end() <= end for start, end in spans)
        if not covered:
            found.append(f"{run.group()} at {run.start()}")
    return found


def _filled(template: object, fields: object) -> tuple[str, list[tuple[int, int]]]:
    """The rendered text, and where in it each field put what it produced.

    Everything the template asks for has to be there, and nothing else is allowed to be,
    because a field nothing renders is either a mistake in the template or a mistake in the
    caller and both are worth stopping for.
    """
    parts = _parts(template)
    wanted = named_fields(template)
    if not isinstance(fields, Mapping):
        raise MissingField(f"a reply is filled from a mapping, not from a {type(fields).__name__}")
    known = ", ".join(sorted(FIELDS))
    for name in wanted:
        if name not in FIELDS:
            raise UnknownField(f"{name!r} is not a field of a reply, which has {known}")
        if name not in fields:
            raise MissingField(f"the template names {name!r} and nothing supplied it")
    for name in fields:
        if name not in wanted:
            raise UnusedField(f"this template names no {name!r}, so nothing would render it")
    pieces: list[str] = []
    spans: list[tuple[int, int]] = []
    at = 0
    for literal, name in parts:
        pieces.append(literal)
        at += len(literal)
        if name is None:
            continue
        value = fields[name]
        if not isinstance(value, Field):
            raise InvalidField(f"a {name} is a Field, and a {type(value).__name__} is not one")
        if value.name != name:
            raise InvalidField(
                f"the template names {name!r} and the field says it is a {value.name!r}"
            )
        pieces.append(value.text)
        spans.append((at, at + len(value.text)))
        at += len(value.text)
    return "".join(pieces), spans


def render(template: object, fields: object) -> str:
    """One template filled by the fields it names, or a refusal saying which way it failed.

    Nothing renders with a hole in it, and nothing renders carrying a number that came from
    no field.
    """
    text, spans = _filled(template, fields)
    loose = unsourced_numbers(text, spans)
    if loose:
        raise UnsourcedNumber(f"{', '.join(loose)} came from no field")
    return text


def reply(awareness: object, fields: object) -> str:
    """The reply for one lead, on the template the playbook picks for its level of awareness.

    The window is built here from the same level the template was picked by, so the hours in
    the text and the action behind them cannot disagree. A window passed in is refused
    rather than replaced, because a caller who supplies one has been told the answer twice.
    """
    step = next_step(awareness)
    if not isinstance(fields, Mapping):
        raise MissingField(f"a reply is filled from a mapping, not from a {type(fields).__name__}")
    if "window" in fields:
        raise UnusedField("a reply builds its own window, from the level of awareness it reads")
    return render(TEMPLATES[step.action], {**fields, "window": window(awareness)})
