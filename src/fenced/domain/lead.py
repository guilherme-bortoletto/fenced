"""A lead, the five levels of awareness a message can show, and the sets beside them.

The model reads free text and returns fields. This module decides whether those
fields are a lead at all, and it refuses rather than coerces. The segment and the
language are closed sets written here, the way awareness is. The products are names
as the person wrote them, and nothing here asks whether a catalog carries them. Everything here is
a pure function of what is passed in, so the rules can be read and tested with no
network, no file and no real clock.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

REQUIRED = ("name", "email", "message")
# Every field `Lead.from_fields` reads, in the order a lead carries them.
FIELDS = (*REQUIRED, "awareness", "segment", "language", "products")
# Characters that take no space and are not whitespace to `str.strip`.
INVISIBLE = "\u200b\u200c\u200d\u2060\ufeff"
SEPARATORS = re.compile(r"[\s\-_]+")


class LeadError(ValueError):
    """Anything the domain refuses to accept as a lead."""


class MissingField(LeadError):
    """A field the domain needs and did not get as text."""


class InvalidEmail(LeadError):
    """An address the domain will not try to reach."""


class UnknownAwareness(LeadError):
    """A level of awareness that is not one of the five."""


class UnknownSegment(LeadError):
    """A segment that is not one of those written in `Segment`."""


class UnknownLanguage(LeadError):
    """A language that is not one of those written in `Language`."""


class InvalidProducts(LeadError):
    """Products that are not a sequence of names written as text."""


def _closed(kind: type[Enum], value: object, what: str, refusal: type[LeadError]) -> Enum:
    """One member of a closed set out of what the model returned, or a refusal.

    Spacing, case, hyphens and underscores are forgiven, because they are spelling
    and not meaning. A value that is not in the set is not forgiven.
    """
    known = ", ".join(member.value for member in kind)
    if isinstance(value, kind):
        return value
    if not isinstance(value, str):
        raise refusal(f"{what} is one of {known}, written as text, not {type(value).__name__}")
    wanted = SEPARATORS.sub("_", value.strip().lower())
    for member in kind:
        if wanted == member.value:
            return member
    raise refusal(f"{value!r} is not one of {known}")


class Awareness(Enum):
    """The five levels, closed on purpose.

    The model picks one of these and nothing else. What to do at each level is a
    written rule in another module, not a judgement made here.
    """

    UNAWARE = "unaware"
    PROBLEM_AWARE = "problem_aware"
    SOLUTION_AWARE = "solution_aware"
    PRODUCT_AWARE = "product_aware"
    READY_TO_BUY = "ready_to_buy"

    @classmethod
    def parse(cls, value: object) -> Awareness:
        """Turn what the model returned into one of the five, or refuse it.

        Spacing, case, hyphens and underscores are forgiven, because they are
        spelling and not meaning. A sixth level is not forgiven.
        """
        return _closed(cls, value, "an awareness", UnknownAwareness)


class Segment(Enum):
    """The kind of business the person runs, closed on purpose.

    Matching reads the segment against what each seller covers. A segment outside
    this list would match no seller and would look like a routing problem when it is
    a reading problem, so it is refused here instead.
    """

    FOOD = "food"
    RETAIL = "retail"
    WHOLESALE = "wholesale"
    MANUFACTURING = "manufacturing"
    HEALTH = "health"

    @classmethod
    def parse(cls, value: object) -> Segment:
        """Turn what the model returned into one of the segments, or refuse it."""
        return _closed(cls, value, "a segment", UnknownSegment)


class Language(Enum):
    """The language the person wrote in, as its two letter code, closed on purpose.

    A reply is written in one of these and a seller speaks some of them. A language
    outside this list is one nobody here can answer in, so it is refused here rather
    than passed on as a code nobody checks.
    """

    ENGLISH = "en"
    PORTUGUESE = "pt"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"

    @classmethod
    def parse(cls, value: object) -> Language:
        """Turn what the model returned into one of the languages, or refuse it."""
        return _closed(cls, value, "a language", UnknownLanguage)


def _products(value: object) -> tuple[str, ...]:
    """The products a person named, each trimmed and each once, in the order named.

    A product is a name as the person wrote it. An empty list is a person who named
    none, which is a lead like any other. A bare string is refused rather than read
    letter by letter, and a blank or a null among the names is refused rather than
    dropped, because it says the reading went wrong.
    """
    if not isinstance(value, (list, tuple)):
        raise InvalidProducts(f"a lead names products in a list, not in a {type(value).__name__}")
    names: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise InvalidProducts(f"a product is named in text, not in a {type(item).__name__}")
        name = item.strip().strip(INVISIBLE).strip()
        if not name:
            raise InvalidProducts("a product with no name is not a product")
        if name not in names:
            names.append(name)
    return tuple(names)


def _as_text(value: object, field: str) -> str:
    """One field, as text and trimmed, or a refusal. Nothing is coerced here.

    A model that returns a null, a number or a list has not given a name, and
    turning it into the string "None" would hide that from everything downstream.
    """
    if not isinstance(value, str):
        raise MissingField(f"a lead needs a {field} written as text, not a {type(value).__name__}")
    trimmed = value.strip().strip(INVISIBLE).strip()
    if not trimmed:
        raise MissingField(f"a lead needs a {field}")
    return trimmed


def _refuse_unreachable(address: str) -> None:
    """A shallow rule on purpose. What a mail server accepts is not this domain's business.

    It refuses only what is certainly unreachable: a missing local part, a host
    without a dotted name, more than one at sign, and any space or control
    character, which is how a header gets smuggled into whatever sends the reply.
    """
    if any(character.isspace() or ord(character) < 32 for character in address):
        raise InvalidEmail(f"{address!r} carries a space or a control character")
    if address.count("@") != 1:
        raise InvalidEmail(f"{address!r} is not an address")
    local, _, host = address.partition("@")
    labels = host.split(".")
    if not local or len(labels) < 2 or not all(labels):
        raise InvalidEmail(f"{address!r} is not an address")


@dataclass(frozen=True)
class Lead:
    """What a person wrote, once the domain has agreed to call it a lead.

    The constructor is the boundary. Whatever route a lead is built by, the same
    refusals and the same trimming happen here, so there is one rule and not two.
    """

    name: str
    email: str
    message: str
    awareness: Awareness
    segment: Segment
    language: Language
    products: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in REQUIRED:
            object.__setattr__(self, field, _as_text(getattr(self, field), field))
        object.__setattr__(self, "awareness", Awareness.parse(self.awareness))
        object.__setattr__(self, "segment", Segment.parse(self.segment))
        object.__setattr__(self, "language", Language.parse(self.language))
        object.__setattr__(self, "products", _products(self.products))
        _refuse_unreachable(self.email)

    @classmethod
    def from_fields(cls, fields: Mapping[str, object]) -> Lead:
        """Build a lead from what an extractor returned, refusing anything else.

        Past this point every value has a type the rest of the domain can rely on,
        and every refusal is a `LeadError`.
        """
        if not isinstance(fields, Mapping):
            raise MissingField(f"a lead is built from a mapping, not a {type(fields).__name__}")
        missing = [name for name in FIELDS if name not in fields]
        if missing:
            raise MissingField(f"a lead needs {', '.join(missing)}")
        return cls(**{name: fields[name] for name in FIELDS})
